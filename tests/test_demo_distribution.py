# SPDX-License-Identifier: Apache-2.0
"""Run every finite offline example from the actual wheel outside the checkout."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def test_wheel_retains_sample_bytes_and_runs_every_offline_demo(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    built = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(tmp_path / "wheels"),
            str(root),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert built.returncode == 0, built.stdout[-4000:] + built.stderr[-4000:]
    installed = tmp_path / "installed"
    with zipfile.ZipFile(next((tmp_path / "wheels").glob("*.whl"))) as wheel:
        for sample in (root / "alpha_factory_v1/demos").glob("*/offline_samples/*.csv"):
            assert wheel.read(sample.relative_to(root).as_posix()) == sample.read_bytes()
        for scenario in (root / "data/sector_shock_10").glob("*.json"):
            bundled = f"alpha_factory_v1/demos/alpha_agi_insight_v1/data/sector_shock_10/{scenario.name}"
            assert wheel.read(bundled) == scenario.read_bytes()
        wheel.extractall(installed)
    guard = tmp_path / "guard"
    guard.mkdir()
    attempted = tmp_path / "network-attempt.txt"
    (guard / "sitecustomize.py").write_text(
        "import socket\nfrom pathlib import Path\nfrom traceback import format_stack\n"
        "def blocked(*args, **kwargs):\n"
        f"    with Path({str(attempted)!r}).open('a') as log:\n"
        "        log.write(''.join(format_stack(limit=32)) + '\\n')\n"
        "    raise RuntimeError('offline wheel acceptance forbids network access')\n"
        "socket.create_connection = blocked\nsocket.getaddrinfo = blocked\n"
        "socket.socket.connect = blocked\nsocket.socket.connect_ex = blocked\n"
        "socket.socket.sendto = blocked\n"
    )
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(installed), str(guard)]),
        "PYTHONSAFEPATH": "1",
        "NO_DISCLAIMER": "1",
        "OPENAI_API_KEY": "offline-demo-must-not-use-this",
        "ANTHROPIC_API_KEY": "offline-demo-must-not-use-this",
        "NEO4J_URI": "bolt://offline-demo.invalid:7687",
        "PGHOST": "offline-demo.invalid",
    }
    # Exercise a normal user launch even when the surrounding suite disables integrations.
    environment.pop("PYTEST_CURRENT_TEST", None)
    environment.pop("PYTEST_NET_OFF", None)
    probe = subprocess.run(
        [sys.executable, "-P", "-c", "import alpha_factory_v1; print(alpha_factory_v1.__file__)"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert probe.returncode == 0 and Path(probe.stdout.strip()).is_relative_to(installed)
    assert not attempted.exists(), attempted.read_text()
    entries = json.loads((installed / "alpha_factory_v1/demos/catalog.json").read_text())["entries"]
    finite = [entry for entry in entries if entry["smoke"]]
    assert len(entries) == 26 and len(finite) == 14
    for entry in finite:
        result = subprocess.run(
            [
                sys.executable,
                "-P",
                "-m",
                "alpha_factory_v1.demos",
                "run",
                entry["id"],
                "--output-dir",
                str(tmp_path / "runs" / entry["id"]),
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert result.returncode == 0, f"{entry['id']}: {result.stdout}\n{result.stderr}"
        assert "offline data missing" not in result.stdout
        assert not attempted.exists(), f"{entry['id']} attempted network access:\n{attempted.read_text()}"
