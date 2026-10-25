# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parent / "scientific"
role = sys.argv[1] if len(sys.argv) == 2 else None
start = time.perf_counter()
cpu = time.process_time()
if role == "checker":
    sys.path.insert(0, str(root / "review"))
    from check import check
elif role == "specialist":
    sys.path.insert(0, str(root / "companion"))
    from specialist import solve
    from native_repair import solve as solve_repair
else:
    raise ValueError("FIXED_ROLE_REQUIRED")
startup = {"wall_seconds": time.perf_counter() - start, "cpu_seconds": time.process_time() - cpu}
raw = sys.stdin.buffer.read(262145)
if len(raw) > 262144:
    raise ValueError("INPUT_LIMIT")
x = json.loads(raw)
start = time.perf_counter()
cpu = time.process_time()
try:
    result = (
        check(x)
        if role == "checker"
        else (
            solve_repair(x["task"], time_limit=2.0)
            if x["mode"] == "repair"
            else solve(x["task"], upper_bound=x.get("upper_bound"), time_limit=2.0, mode=x["mode"])
        )
    )
    output = {"ok": True, "result": result}
except Exception as e:
    output = {"ok": False, "error": type(e).__name__ + ": " + str(e)}
output["startup"] = startup
output["call_wall_seconds"] = time.perf_counter() - start
output["call_cpu_seconds"] = time.process_time() - cpu
print(json.dumps(output, allow_nan=False, separators=(",", ":")), flush=True)
