# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import subprocess
import time

import pytest

if not shutil.which("docker"):
    pytest.skip("docker not available", allow_module_level=True)

try:
    subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
except subprocess.SubprocessError:
    pytest.skip("docker daemon not available", allow_module_level=True)


@pytest.mark.e2e
def test_container_healthcheck() -> None:
    tag = "af-health-test"
    dockerfile = os.path.join("alpha_factory_v1", "Dockerfile")
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
            "assert u.urlopen('http://127.0.0.1:3000/').status == 200; "
            "assert json.load(u.urlopen('http://127.0.0.1:8001/healthz')) == 'ok'"
        )
        subprocess.run(["docker", "exec", cid, "python", "-c", probe], check=True, timeout=30)
    finally:
        subprocess.run(["docker", "rm", "-f", cid], check=False)
        subprocess.run(["docker", "rmi", tag], check=False)
