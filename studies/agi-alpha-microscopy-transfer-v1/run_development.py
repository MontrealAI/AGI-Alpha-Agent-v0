# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import microscopy_transfer as instrument
from conventional_reference import common_grid, compare, conventional_moments


def main() -> None:
    out = ROOT / "development"
    out.mkdir(exist_ok=True)
    source = ROOT / "data/development/idr0062/native_labels.npy"
    labels = np.load(source, allow_pickle=False)
    contract = json.loads((ROOT / "data/development/contract.json").read_text())
    angle = 0.37
    a = np.eye(4)
    a[:3, :3] = [[1.0, 0.12, 0.0], [0.0, np.cos(angle), -np.sin(angle)], [0.0, np.sin(angle), np.cos(angle)]]
    a[:3, 3] = [4.25, -7.4, 11.2]
    contract["affine"] = a.tolist()
    contract["mission_id"] = "development-geometric-transfer"
    path = out / "mapped-contract.json"
    path.write_text(json.dumps(contract, indent=2) + "\n")
    started = time.perf_counter()
    retained = instrument.run(source, path)
    retained_elapsed = time.perf_counter() - started
    (out / "mapped-instrument.json").write_text(json.dumps(retained, indent=2) + "\n")
    started = time.perf_counter()
    direct = conventional_moments(labels, np.asarray(contract["spacing"]), np.asarray(contract["origin"]), a)
    direct_elapsed = time.perf_counter() - started
    (out / "mapped-conventional.json").write_text(json.dumps(direct, indent=2) + "\n")
    rows = []
    for step in (0.75, 1.5, 3.0):
        started = time.perf_counter()
        raster, spacing, origin = common_grid(
            labels, np.asarray(contract["spacing"]), np.asarray(contract["origin"]), a, step
        )
        measured = conventional_moments(raster, spacing, origin, np.eye(4))
        comparison = compare(direct, measured)
        rows.append(
            {
                "target_step_um": step,
                "shape": list(raster.shape),
                "target_voxels": int(raster.size),
                "elapsed_seconds": time.perf_counter() - started,
                **comparison,
            }
        )
    record = {
        "phase": "development",
        "source_image": "idr0062A/6001240",
        "source_shape": list(labels.shape),
        "source_sha256": instrument.digest_file(source),
        "labels": retained["label_count"],
        "boundary_labels": sum(x["touches_source_boundary"] for x in retained["objects"]),
        "instrument_vs_conventional": compare(direct, retained),
        "instrument_elapsed_seconds": retained_elapsed,
        "conventional_elapsed_seconds": direct_elapsed,
        "raster_diagnostics": rows,
        "interpretation": "Raster is a diagnostic alternative, not model U; conventional analytical control is primary.",
    }
    (out / "development-summary.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
