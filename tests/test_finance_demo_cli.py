# SPDX-License-Identifier: Apache-2.0
"""Verify the finance demo shell script runs."""

from __future__ import annotations

import os
import json
import subprocess
from pathlib import Path


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def test_finance_demo_cli(tmp_path: Path) -> None:
    script = Path("alpha_factory_v1/demos/finance_alpha/deploy_alpha_factory_demo.sh")
    assert script.exists(), script

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    _write_executable(
        bin_dir / "docker",
        """#!/usr/bin/env bash
if [ "$1" = "image" ]; then exit 0; fi
if [ "$1" = "pull" ]; then exit 0; fi
if [ "$1" = "run" ]; then echo cid123; exit 0; fi
if [ "$1" = "logs" ]; then exit 0; fi
if [ "$1" = "stop" ]; then exit 0; fi
exit 0
""",
    )
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\necho '{}'\n")
    _write_executable(bin_dir / "jq", "#!/usr/bin/env bash\ncat >/dev/null\n")
    _write_executable(bin_dir / "lsof", "#!/usr/bin/env bash\nexit 1\n")
    _write_executable(bin_dir / "sleep", '#!/usr/bin/env bash\n[ "$1" = "3600" ] && exit 1\nexit 0\n')

    env = os.environ.copy()
    env.update({"PATH": f"{bin_dir}:{env.get('PATH', '')}", "PORT_API": "8010", "STRATEGY": "btc_gld"})

    result = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env, timeout=20)

    assert result.returncode == 0, result.stderr
    assert "Demo complete!" in result.stdout


def test_legacy_dotenv_is_literal_and_environment_wins(tmp_path: Path) -> None:
    source = Path("alpha_factory_v1/demos/finance_alpha/deploy_alpha_factory_demo.sh")
    script = tmp_path / "deploy.sh"
    script.write_bytes(source.read_bytes())
    marker = tmp_path / "must-not-exist"
    value = f"$(touch {marker})"
    (tmp_path / ".env").write_text(f"FIN_CYCLE_SECONDS={value}\nPORT_API=08010\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "docker",
        """#!/usr/bin/env python3
import json, os, sys
if sys.argv[1] == 'run':
    with open(os.environ['FINANCE_TEST_ARGS'], 'w') as output:
        json.dump(sys.argv[1:], output)
    print('cid123')
""",
    )
    for name, body in {"curl": "echo '{}'", "jq": "cat >/dev/null", "sleep": "exit 1", "python": "exit 0"}.items():
        _write_executable(bin_dir / name, f"#!/usr/bin/env bash\n{body}\n")
    args_file = tmp_path / "args.json"
    env = os.environ.copy()
    env.pop("FIN_CYCLE_SECONDS", None)
    env.update(
        PATH=f"{bin_dir}:{env.get('PATH', '')}",
        PORT_API="08011",
        TRACE_WS_PORT="8088",
        FINANCE_TEST_ARGS=str(args_file),
    )
    result = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env, timeout=20)
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    arguments = json.loads(args_file.read_text())
    assert f"FIN_CYCLE_SECONDS={value}" in arguments
    assert "127.0.0.1:8011:8000" in arguments
    assert "127.0.0.1:8088:8088" in arguments
    assert "FIN_BROKER_MODE=paper" in arguments
    env["TRACE_WS_PORT"] = "8011"
    result = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env, timeout=20)
    assert result.returncode == 2
    assert "distinct ports" in result.stderr
