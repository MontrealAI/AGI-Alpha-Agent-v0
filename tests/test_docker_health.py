# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import subprocess
import time

import pytest

from alpha_factory_v1 import __version__

if not shutil.which("docker"):
    pytest.skip("docker not available", allow_module_level=True)

try:
    subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
except subprocess.SubprocessError:
    pytest.skip("docker daemon not available", allow_module_level=True)


@pytest.mark.e2e
@pytest.mark.parametrize("profile", ["shared", "quickstart"])
def test_container_healthcheck(profile: str) -> None:
    tag = f"af-health-test-{profile}"
    dockerfile = (
        os.path.join("alpha_factory_v1", "Dockerfile") if profile == "shared" else "docker/quickstart/Dockerfile"
    )
    subprocess.run(["docker", "build", "-t", tag, "-f", dockerfile, "."], check=True, timeout=600)
    cid = (
        subprocess.check_output(
            [
                "docker",
                "run",
                "-d",
                "--network",
                "none",
                "-e",
                "API_TOKEN=container-health-test-only",
                "-e",
                "NEO4J_PASSWORD=container-health-test-only",
                "-e",
                "ALPHA_ENABLED_AGENTS=ping",
                "-e",
                "OPENAI_AGENTS_DISABLE_TRACING=true",
                "-e",
                "HF_HUB_OFFLINE=1",
                "-e",
                "TRANSFORMERS_OFFLINE=1",
                "-e",
                "NO_DISCLAIMER=1",
                tag,
            ]
        )
        .decode()
        .strip()
    )
    try:
        status = "starting"
        for _ in range(60):
            inspect = subprocess.check_output(
                ["docker", "inspect", "-f", "{{.State.Health.Status}}", cid],
                text=True,
            ).strip()
            status = inspect
            if status == "healthy":
                break
            time.sleep(2)
        if status != "healthy":
            logs = subprocess.check_output(["docker", "logs", cid], stderr=subprocess.STDOUT, text=True)
            pytest.fail(f"Legacy container status={status}: {logs}")
        # Verify that health belongs to the actual orchestrator, and both
        # historical companion services are also running without public network.
        probe = (
            "import json, urllib.request as u; "
            "r=u.Request('http://127.0.0.1:8000/agents', "
            "headers={'Authorization':'Bearer container-health-test-only'}); "
            "assert json.load(u.urlopen(r)) == ['ping']; "
        )
        if profile == "shared":
            probe += (
                "assert u.urlopen('http://127.0.0.1:3000/').status == 200; "
                "assert json.load(u.urlopen('http://127.0.0.1:8001/healthz')) == 'ok'"
            )
        else:
            probe += "import os; assert os.getuid() == 10001; assert os.access('/data', os.W_OK)"
            version = subprocess.check_output(
                ["docker", "exec", cid, "alpha-factory", "--version"], text=True, timeout=30
            )
            assert version.strip() == __version__
        subprocess.run(["docker", "exec", cid, "python", "-c", probe], check=True, timeout=30)
    finally:
        subprocess.run(["docker", "rm", "-f", cid], check=False)
        subprocess.run(["docker", "rmi", tag], check=False)
