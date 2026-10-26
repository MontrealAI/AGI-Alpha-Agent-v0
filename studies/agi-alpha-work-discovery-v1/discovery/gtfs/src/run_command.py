# SPDX-License-Identifier: Apache-2.0
import datetime
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

label, *command = sys.argv[1:]
root = Path(__file__).resolve().parents[1]
start = datetime.datetime.now(datetime.UTC).isoformat()
before = resource.getrusage(resource.RUSAGE_CHILDREN)
clock = time.monotonic()
with (root / "commands" / f"{label}.stdout.txt").open("wb") as out, (root / "commands" / f"{label}.stderr.txt").open(
    "wb"
) as err:
    try:
        result = subprocess.run(command, cwd=root, stdout=out, stderr=err, timeout=58, check=False)
        status = result.returncode
        expired = False
    except subprocess.TimeoutExpired:
        status = 124
        expired = True
elapsed = time.monotonic() - clock
after = resource.getrusage(resource.RUSAGE_CHILDREN)
record = {
    "label": label,
    "command": command,
    "started_utc": start,
    "elapsed_seconds": elapsed,
    "user_cpu_seconds": after.ru_utime - before.ru_utime,
    "system_cpu_seconds": after.ru_stime - before.ru_stime,
    "max_rss_kib": after.ru_maxrss,
    "exit_status": status,
    "timeout": expired,
    "timeout_seconds": 58,
}
(root / "commands" / f"{label}.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
raise SystemExit(status)
