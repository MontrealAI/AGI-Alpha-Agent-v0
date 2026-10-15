# SPDX-License-Identifier: Apache-2.0
"""Exercise finite shell and notebook entry points without provider setup."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/alpha_agi_business_2_v1"
NOTEBOOK = DEMO / "colab_alpha_agi_business_2_demo.ipynb"


def cells():
    data = json.loads(NOTEBOOK.read_text())
    return ["".join(c["source"]) for c in data["cells"] if c["cell_type"] == "code"]


def test_shell_requires_explicit_input_and_preserves_caller_paths(tmp_path):
    env = {**os.environ, "PYTHON": sys.executable, "PYTHONDONTWRITEBYTECODE": "1"}
    script = DEMO / "run_business_2_demo.sh"
    result = subprocess.run(["bash", str(script)], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    example = subprocess.run(
        ["bash", str(script), "--example"], cwd=tmp_path, env=env, capture_output=True, text=True, check=True
    )
    scenario = tmp_path / "my scenario.json"
    scenario.write_bytes((DEMO / "example.json").read_bytes())
    supplied = subprocess.run(
        ["bash", str(script), "--input", scenario.name],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(example.stdout) == json.loads(supplied.stdout)
    scenario.write_bytes(b'{"schema":"x","schema":"y"}')
    invalid = subprocess.run(
        ["bash", str(script), "--input", scenario.name], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert invalid.returncode == 2 and not invalid.stdout


def test_notebook_computes_and_recovers_without_network(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("unexpected network access"))
    namespace = {}
    for index, source in enumerate(cells()):
        exec(compile(source, f"business-notebook-{index}", "exec"), namespace)
    assert namespace["report"] == namespace["recomputed"]
    raw = json.loads(namespace["raw_input_path"].read_bytes())
    assert namespace["bounded_evaluate"](raw) == namespace["report"]
    path = namespace["evidence_path"]
    original = path.read_bytes()
    namespace["scenario"]["policy"]["effortHours"] += 1
    with pytest.raises(ValueError, match="rerun"):
        exec(cells()[3], namespace)
    namespace["scenario"]["policy"]["effortHours"] -= 1
    with pytest.raises(FileExistsError):
        exec(cells()[3], namespace)
    assert path.read_bytes() == original
    forged = json.loads(original)
    forged["report"] = {"productionApproved": True}
    path.write_text(json.dumps(forged))
    exec(cells()[4], namespace)
    assert namespace["recomputed"] == namespace["report"]
    for bad in [b'{"schema":"x","schema":"y"}', b'{"input":"\xff"}', b"\xef\xbb\xbf{}"]:
        path.write_bytes(bad)
        with pytest.raises((ValueError, UnicodeError)):
            exec(cells()[4], namespace)


def test_notebook_has_no_retained_outputs_or_shell_cells():
    for cell in json.loads(NOTEBOOK.read_text())["cells"]:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is None and cell["outputs"] == []
            source = "".join(cell["source"])
            compile(source, "business-notebook", "exec")
            assert "subprocess" not in source and "getpass" not in source
