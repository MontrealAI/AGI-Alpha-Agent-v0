"""Fresh-process readback and standard-library ZIP integrity check for this pilot."""
import argparse
import hashlib
import json
from pathlib import Path
import traceback
import zipfile

import numpy as np
import zarr

parser = argparse.ArgumentParser()
parser.add_argument("--path", required=True)
parser.add_argument("--kind", choices=["zip", "local"], required=True)
parser.add_argument("--direct", action="store_true")
args = parser.parse_args()
path = Path(args.path)
result = {"zip_integrity": None, "array_read": False, "value_match": False}
if args.kind == "zip":
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            result["zip_integrity"] = bad is None
            result["first_bad_member"] = bad
            result["zip_entries"] = archive.namelist()
    except Exception as exc:
        result["zip_integrity"] = False
        result["zip_error"] = f"{type(exc).__name__}: {exc}"
try:
    store = (zarr.storage.ZipStore(str(path), mode="r", read_only=True) if args.kind == "zip"
             else zarr.storage.LocalStore(str(path), read_only=True))
    try:
        array = zarr.open_array(store=store, mode="r") if args.direct else zarr.open_group(store=store, mode="r")["data"]
        observed = np.asarray(array[:])
        expected = np.arange(20, dtype=np.int64) if args.direct else np.zeros((1,), dtype=np.float32)
        result.update(array_read=True, shape=list(observed.shape), dtype=str(observed.dtype),
                      values=observed.tolist(), value_match=bool(observed.dtype == expected.dtype and np.array_equal(observed, expected)),
                      value_sha256=hashlib.sha256(observed.tobytes()).hexdigest())
    finally:
        store.close()
except Exception as exc:
    result["read_error"] = f"{type(exc).__name__}: {exc}"
    result["read_traceback"] = traceback.format_exc()
result["accepted"] = result["array_read"] and result["value_match"] and result["zip_integrity"] is not False
print(json.dumps(result, sort_keys=True))
