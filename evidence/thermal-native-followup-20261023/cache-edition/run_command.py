# SPDX-License-Identifier: Apache-2.0
"""Retain exact local preparation commands and their unabridged outputs."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
label, cwd, *argv = sys.argv[1:]
if not label.replace("-", "").replace("_", "").isalnum() or not argv:
    raise SystemExit("Expected safe label, working directory, and command arguments")
environment = {
    "PATH": "/workspace/scratch/5d02e86cc826/thermal-toolchain/node-v22.17.1-linux-x64/bin:"
    "/workspace/scratch/5d02e86cc826/thermal-python/bin:/usr/local/bin:/usr/bin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "TMPDIR": "/tmp",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONNOUSERSITE": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "PYTEST_NET_OFF": "1",
}
public_environment = dict(environment)
proxy_names = []
if label.startswith(("fetch-", "checkout-", "merge-")):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        if name in os.environ:
            environment[name] = os.environ[name]
            proxy_names.append(name)
start = dt.datetime.now(dt.timezone.utc).isoformat()
result = subprocess.run(argv, cwd=cwd, env=environment, capture_output=True, check=False)
end = dt.datetime.now(dt.timezone.utc).isoformat()
stdout_path, stderr_path = LOGS / (label + ".stdout"), LOGS / (label + ".stderr")
for path, body in ((stdout_path, result.stdout), (stderr_path, result.stderr)):
    with path.open("xb") as stream:
        stream.write(body)
record = {
    "label": label, "startedAt": start, "endedAt": end, "cwd": cwd, "argv": argv,
    "environment": public_environment, "networkProxyVariablesForwarded": proxy_names, "exit": result.returncode,
    "stdout": str(stdout_path.relative_to(ROOT)), "stderr": str(stderr_path.relative_to(ROOT)),
}
with (ROOT / "commands.jsonl").open("a") as stream:
    stream.write(json.dumps(record, sort_keys=True) + "\n")
print(json.dumps(record, sort_keys=True))
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
raise SystemExit(result.returncode)
