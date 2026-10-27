#!/usr/bin/env python3
"""Measure supplied integer-label support under physical affine pushforwards.

Inputs are never segmented, resampled, relabeled, or repaired. Source coordinates
are voxel centers in source_axes order; mapped coordinates are target_axes order.
Both spacing and origin are converted to micrometers before using the affine.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

UNIT_UM = {"micrometer": 1.0, "nanometer": 0.001,
           "millimeter": 1000.0, "meter": 1000000.0}
SUPPORTED_METRICS = {"label_count", "native_measure", "mapped_measure",
                     "native_centroid", "mapped_centroid", "voxel_count"}


def decision(case_id, status, reason):
    return {"case_id": case_id, "status": status, "reason": reason}


def solve_case(case, input_dir):
    case_id = case["case_id"]
    contract = json.loads((input_dir / case["contract"]).read_text())
    array_path = input_dir / case["array"]
    observed_hash = hashlib.sha256(array_path.read_bytes()).hexdigest()
    expected_hash = contract.get("source_sha256")
    if observed_hash != expected_hash:
        return decision(case_id, "REJECT", "Source SHA-256 mismatch: contract expects "
                        + str(expected_hash) + "; actual array file SHA-256 is "
                        + observed_hash + ". Source identity must be corrected before measurement.")
    array = np.load(array_path, allow_pickle=False)
    if array.ndim not in (2, 3) or not np.issubdtype(array.dtype, np.integer):
        return decision(case_id, "REJECT", "Only 2D or 3D integer label arrays are supported.")
    d = array.ndim
    if contract.get("schema") != "microscopy-moments/v1":
        return decision(case_id, "HOLD", "Unknown contract schema; its semantics require clarification.")
    if contract.get("object_definition") != "label_id":
        return decision(case_id, "HOLD", "Object definition is not explicitly one region per nonzero label ID.")
    if contract.get("coverage") != "provided_label_support":
        return decision(case_id, "HOLD", "Requested coverage is "
                        + str(contract.get("coverage"))
                        + "; complete biological objects cannot be inferred from the supplied label support. "
                          "Clarify coverage or supply the required biological evidence.")
    if contract.get("map_semantics") != "geometric_pushforward":
        return decision(case_id, "HOLD", "Map semantics are not explicitly geometric_pushforward.")
    metrics = contract.get("metrics")
    if not isinstance(metrics, list) or not all(isinstance(m, str) for m in metrics):
        return decision(case_id, "HOLD", "Requested metrics are missing or ambiguous.")
    unsupported = sorted(set(metrics) - SUPPORTED_METRICS)
    if unsupported:
        return decision(case_id, "HOLD", "Unsupported requested metrics: "
                        + ", ".join(unsupported)
                        + ". The supplied arrays contain labels, not measured intensities; "
                          "mean intensity cannot be inferred. Supply intensity data and its measurement "
                          "contract, or explicitly revise the mission to geometric metrics.")
    for key in ("source_axes", "target_axes"):
        axes = contract.get(key)
        if (not isinstance(axes, list) or len(axes) != d
                or not all(isinstance(a, str) and a in ("x", "y", "z") for a in axes)
                or len(set(axes)) != d):
            return decision(case_id, "HOLD", key + " must explicitly identify each spatial axis once.")
    units = contract.get("units")
    if not isinstance(units, list) or len(units) != d or any(u not in UNIT_UM for u in units):
        return decision(case_id, "HOLD", "Per-axis physical units are missing or unsupported.")
    try:
        spacing = np.asarray(contract["spacing"], dtype=np.float64)
        origin = np.asarray(contract["origin"], dtype=np.float64)
        affine = np.asarray(contract["affine"], dtype=np.float64)
    except (KeyError, TypeError, ValueError):
        return decision(case_id, "HOLD", "Numeric source calibration or affine is missing or malformed.")
    if spacing.shape != (d,) or origin.shape != (d,):
        return decision(case_id, "HOLD", "Calibration dimensions do not match the array.")
    if not np.isfinite(spacing).all() or not np.isfinite(origin).all() or (spacing <= 0).any():
        return decision(case_id, "HOLD", "Calibration must have finite origin and finite positive spacing.")
    if affine.shape != (d + 1, d + 1) or not np.isfinite(affine).all():
        return decision(case_id, "REJECT", "Transform must be a finite homogeneous affine of matching dimension.")
    if not np.array_equal(affine[-1], np.r_[np.zeros(d), 1.0]):
        return decision(case_id, "REJECT", "Homogeneous transform has a non-affine final row "
                        + json.dumps(affine[-1].tolist())
                        + "; projective or other non-affine transforms are outside the stated scope. "
                          "The final row cannot be silently discarded.")
    scale = np.asarray([UNIT_UM[u] for u in units], dtype=np.float64)
    spacing_um, origin_um = spacing * scale, origin * scale
    linear, translation = affine[:d, :d], affine[:d, d]
    determinant = float(np.linalg.det(linear))
    if not np.isfinite(determinant) or determinant == 0:
        return decision(case_id, "HOLD", "Singular or numerically invalid affine requires a convention "
                        "for the mapped centroid of zero-dimensional-measure support.")
    native_voxel_measure = float(np.prod(spacing_um))
    objects = []
    for value in np.unique(array):
        if value == 0:
            continue
        indices = np.argwhere(array == value)
        voxel_count = int(indices.shape[0])
        native_centroid = origin_um + indices.mean(axis=0) * spacing_um
        mapped_centroid = linear @ native_centroid + translation
        native_measure = voxel_count * native_voxel_measure
        objects.append({"label_id": int(value), "voxel_count": voxel_count,
                        "native_measure": float(native_measure),
                        "mapped_measure": float(native_measure * abs(determinant)),
                        "native_centroid_um": native_centroid.tolist(),
                        "mapped_centroid_um": mapped_centroid.tolist()})
    return {"case_id": case_id, "status": "ACCEPT", "label_count": len(objects), "objects": objects}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=Path(__file__).parent.parent / "inputs")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("answers.json"))
    args = parser.parse_args()
    cases = json.loads((args.inputs / "cases.json").read_text())
    answers = [solve_case(case, args.inputs) for case in cases]
    args.output.write_text(json.dumps(answers, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "cases": len(answers),
                      "statuses": {s: sum(a["status"] == s for a in answers)
                                   for s in ("ACCEPT", "HOLD", "REJECT")}}))


if __name__ == "__main__":
    main()
