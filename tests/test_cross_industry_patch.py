# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import subprocess
from pathlib import Path
import yaml


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _run_script(tmp_path: Path) -> dict:
    script = Path("alpha_factory_v1/demos/cross_industry_alpha_factory/deploy_alpha_factory_cross_industry_demo.sh")
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services: {}\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        """#!/usr/bin/env bash
if [ "$1" = "info" ] || [ "$1" = "compose" ]; then exit 0; fi
if [ "$1" = "run" ]; then
  while [ "$1" != "ghcr.io/mikefarah/yq:4.44.1" ] && [ $# -gt 0 ]; do shift; done
  shift
  yq "$@"
  exit $?
fi
exit 0
"""
    )
    docker_stub.chmod(0o755)

    for cmd in ["git", "curl", "openssl", "ssh-keygen", "cosign", "rekor", "k6", "locust"]:
        _write_executable(bin_dir / cmd, "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
            "COMPOSE_FILE": str(compose),
            "PROJECT_DIR": str(tmp_path),
            "SKIP_BENCH": "1",
            "SKIP_DEPLOY": "1",
        }
    )

    subprocess.run(["bash", str(script)], check=True, env=env, timeout=10)
    bak = tmp_path / "AGI-Alpha-Agent-v0" / "alpha_factory_v1" / ".env.bak"
    if bak.exists():
        bak.unlink()
    first = yaml.safe_load(compose.read_text())
    subprocess.run(["bash", str(script)], check=True, env=env, timeout=10)
    if bak.exists():
        bak.unlink()
    second = yaml.safe_load(compose.read_text())
    return {"first": first, "second": second}


def test_cross_industry_script_idempotent(tmp_path: Path) -> None:
    result = _run_script(tmp_path)
    first_services = result["first"].get("services", {})
    second_services = result["second"].get("services", {})
    assert first_services == second_services
    assert len(second_services) == len(set(second_services))
