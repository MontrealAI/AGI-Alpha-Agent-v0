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


MIN_DOCKER_DISK_GB = float(os.getenv("MIN_DOCKER_DISK_GB", "8"))


def _ensure_disk_space() -> None:
    usage = shutil.disk_usage(".")
    free_gb = usage.free / (1024**3)
    if free_gb < MIN_DOCKER_DISK_GB:
        pytest.skip(f"Skipping Docker build due to low disk space ({free_gb:.1f} GiB free)")


@pytest.mark.e2e
def test_container_healthcheck() -> None:
    _ensure_disk_space()
    tag = "af-health-test"
    dockerfile = os.path.join("alpha_factory_v1", "Dockerfile")
    subprocess.run(["docker", "build", "-t", tag, "-f", dockerfile, "."], check=True)
    cid = subprocess.check_output(["docker", "run", "-d", tag]).decode().strip()
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
        assert status == "healthy"
    finally:
        subprocess.run(["docker", "rm", "-f", cid], check=False)
        subprocess.run(["docker", "rmi", tag], check=False)
