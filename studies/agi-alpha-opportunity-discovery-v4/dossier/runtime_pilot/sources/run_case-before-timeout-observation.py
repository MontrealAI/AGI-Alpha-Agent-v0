"""A bounded public-reproducer qualification, not a repair or general instrument."""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import warnings

import dask
import dask.array as da
import numpy as np
import zarr

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["reported_default", "reported_synchronous", "local_control", "direct_create_control"], required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
kind = "local" if args.mode == "local_control" else "zip"
direct = args.mode == "direct_create_control"
path = args.out / ("artifact.zarr" if kind == "local" else "artifact.zip")
result = {
    "schema": "bounded-zipstore-qualification/v1", "mode": args.mode,
    "source": "https://github.com/zarr-developers/zarr-python/issues/3516",
    "researcher_work": "execution wrapper, logs and independent-process readback; no proposed fix",
    "python": sys.version, "platform": platform.platform(),
    "versions": {name: importlib.metadata.version(name) for name in ("zarr", "dask", "numpy", "numcodecs")},
    "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ("run_case.py", "verify_store.py")},
    "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "write_returned": False, "close_returned": False,
    "source_deviation": "Python 3.12.14, rather than reported Python 3.11; exact reported array/write path retained",
}
started = time.perf_counter()
store = None
with warnings.catch_warnings(record=True) as captured:
    warnings.simplefilter("always")
    try:
        store = (zarr.storage.ZipStore(str(path), mode="w", read_only=False) if kind == "zip"
                 else zarr.storage.LocalStore(str(path), read_only=False))
        if direct:
            # Existing workaround from the issue: this creates a root array, not a group/data layout.
            zarr.create_array(store=store, data=da.arange(20))
            result["source_deviation"] += "; direct control reproduces published 20-element root-array workaround"
        else:
            data = da.zeros((1,), dtype=np.float32)
            group = zarr.open_group(store=store, mode="w")
            destination = group.create_array(name="data", shape=data.shape, dtype=data.dtype, overwrite=True)
            if args.mode == "reported_synchronous":
                with dask.config.set(scheduler="synchronous"):
                    da.to_zarr(data, destination)
            else:
                da.to_zarr(data, destination)
        result["write_returned"] = True
    except Exception as exc:
        result["write_error"] = f"{type(exc).__name__}: {exc}"
        result["write_traceback"] = traceback.format_exc()
    finally:
        if store is not None:
            try:
                store.close()
                result["close_returned"] = True
            except Exception as exc:
                result["close_error"] = f"{type(exc).__name__}: {exc}"
    result["warnings"] = [{"category": row.category.__name__, "message": str(row.message)} for row in captured]
result["write_and_close_seconds"] = time.perf_counter() - started
command = [sys.executable, str(ROOT / "verify_store.py"), "--path", str(path), "--kind", kind]
if direct:
    command.append("--direct")
readback = subprocess.run(command, capture_output=True, text=True, timeout=30)
(args.out / "readback.stdout").write_text(readback.stdout)
(args.out / "readback.stderr").write_text(readback.stderr)
result["readback_exit_code"] = readback.returncode
result["readback"] = json.loads(readback.stdout) if readback.returncode == 0 else None
result["accepted"] = bool(result["write_returned"] and result["close_returned"] and result["readback"] and result["readback"]["accepted"])
files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
result["artifacts"] = [{"path": str(p.relative_to(args.out)), "bytes": p.stat().st_size,
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
result["elapsed_seconds"] = time.perf_counter() - started
(args.out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"mode": args.mode, "versions": result["versions"], "write_returned": result["write_returned"],
                  "accepted": result["accepted"], "zip_integrity": result["readback"].get("zip_integrity") if result["readback"] else None,
                  "read_error": result["readback"].get("read_error") if result["readback"] else None}, sort_keys=True))
