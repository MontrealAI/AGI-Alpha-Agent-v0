"""Three remaining qualification attempts, each with an outer 30-second deadline."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
label = sys.argv[1]
assert label in ("reported", "current")
python = root / f"venv_{label}" / "bin" / "python"
for mode, directory in [("reported_default", "reported_default_attempt2"), ("local_control", "local_control"), ("direct_create_control", "direct_create_control")]:
    out = root / "results" / label / directory
    command = [str(python), str(root / "run_case.py"), "--mode", mode, "--out", str(out)]
    started = time.monotonic()
    with (root / "logs" / f"{label}_{directory}.log").open("w") as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                 env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
        try:
            code = child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            code = child.wait(timeout=3)
            out.mkdir(parents=True, exist_ok=True)
            (out / "result.json").write_text(json.dumps({"schema":"pilot-timeout/v1", "environment":label,
                "mode":mode, "outcome":"execution_timeout", "scientific_verdict":None, "elapsed_seconds":time.monotonic()-started},indent=2)+"\n")
    print(json.dumps({"environment":label,"case":directory,"exit_code":code,"elapsed_seconds":time.monotonic()-started}),flush=True)
