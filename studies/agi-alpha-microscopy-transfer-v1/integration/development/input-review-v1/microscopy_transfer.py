# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

VERSION = "microscopy-moments/v1"
UNIT_TO_UM = {
    "micrometer": 1.0,
    "um": 1.0,
    "nanometer": 0.001,
    "nm": 0.001,
    "millimeter": 1000.0,
    "mm": 1000.0,
    "meter": 1e6,
    "m": 1e6,
}
METRICS = {"label_count", "native_measure", "mapped_measure", "native_centroid", "mapped_centroid"}
FIELDS = {
    "schema",
    "mission_id",
    "source_sha256",
    "source_axes",
    "spacing",
    "units",
    "origin",
    "object_definition",
    "coverage",
    "map_semantics",
    "affine",
    "target_axes",
    "metrics",
}


class MissionError(ValueError):
    def __init__(self, reason: str, status: str = "HOLD") -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def numeric_vector(value: Any, d: int, field: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != d:
        raise MissionError(f"{field}: expected {d} entries", "REJECT")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in value):
        raise MissionError(f"{field}: numeric entries required", "REJECT")
    array = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise MissionError(f"{field}: finite entries required", "REJECT")
    return array


def validate_contract(contract: dict[str, Any], labels: np.ndarray, source_sha256: str) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise MissionError("contract must be an object", "REJECT")
    if set(contract) != FIELDS:
        raise MissionError("contract fields missing or unsupported: " + str(sorted(set(contract) ^ FIELDS)))
    if contract["schema"] != VERSION:
        raise MissionError("unsupported contract version")
    if not isinstance(contract["mission_id"], str) or not contract["mission_id"].strip():
        raise MissionError("mission_id must be nonempty", "REJECT")
    if contract["source_sha256"] != source_sha256:
        raise MissionError("source bytes do not match mission", "REJECT")
    if labels.ndim not in (2, 3) or not all(labels.shape):
        raise MissionError("only nonempty 2D/3D spatial label arrays are supported")
    if labels.dtype.kind not in "iu":
        raise MissionError("integer label IDs required", "REJECT")
    d = labels.ndim
    axes, target_axes = contract["source_axes"], contract["target_axes"]
    for name, value in (("source_axes", axes), ("target_axes", target_axes)):
        if not isinstance(value, list) or len(value) != d or any(x not in ("x", "y", "z") for x in value):
            raise MissionError(f"{name}: explicit spatial axis names required", "REJECT")
        if len(set(value)) != d:
            raise MissionError(f"{name}: duplicate axis", "REJECT")
    if set(axes) != set(target_axes):
        raise MissionError("source and target spatial axes differ")
    if contract["object_definition"] != "label_id":
        raise MissionError("only supplied label identity is supported; connected components are a new mission")
    if contract["coverage"] != "provided_label_support":
        raise MissionError("complete biological objects cannot be certified from supplied label support")
    if contract["map_semantics"] != "geometric_pushforward":
        raise MissionError("mapping meaning must explicitly be geometric_pushforward")
    metrics = contract["metrics"]
    if not isinstance(metrics, list) or not metrics or any(not isinstance(x, str) or x not in METRICS for x in metrics):
        raise MissionError("requested metric is unsupported")
    if len(metrics) != len(set(metrics)):
        raise MissionError("duplicate requested metric", "REJECT")
    units = contract["units"]
    if (
        not isinstance(units, list)
        or len(units) != d
        or any(not isinstance(x, str) or x not in UNIT_TO_UM for x in units)
    ):
        raise MissionError("each source axis needs a supported length unit")
    scales = np.asarray([UNIT_TO_UM[x] for x in units], dtype=np.float64)
    spacing = numeric_vector(contract["spacing"], d, "spacing") * scales
    origin = numeric_vector(contract["origin"], d, "origin") * scales
    if np.any(spacing <= 0) or not np.all(np.isfinite(spacing)) or not np.all(np.isfinite(origin)):
        raise MissionError("converted spacing/origin invalid", "REJECT")
    affine_list = contract["affine"]
    if not isinstance(affine_list, list) or len(affine_list) != d + 1:
        raise MissionError("affine must be homogeneous (d+1) by (d+1)", "REJECT")
    affine = np.stack([numeric_vector(row, d + 1, "affine") for row in affine_list])
    expected = np.zeros(d + 1)
    expected[-1] = 1.0
    if not np.array_equal(affine[-1], expected):
        raise MissionError("projective/non-affine mappings need a different instrument")
    linear, translation = affine[:-1, :-1], affine[:-1, -1]
    singular = np.linalg.svd(linear, compute_uv=False)
    if singular[-1] <= 0 or singular[0] / singular[-1] > 1e12:
        raise MissionError("singular or numerically unstable map")
    determinant = abs(float(np.linalg.det(linear)))
    voxel_measure = float(np.prod(spacing))
    if not np.isfinite(determinant) or determinant == 0 or not np.isfinite(voxel_measure) or voxel_measure == 0:
        raise MissionError("measure scaling overflows or underflows", "REJECT")
    return {
        "spacing": spacing,
        "origin": origin,
        "linear": linear,
        "translation": translation,
        "determinant": determinant,
        "voxel_measure": voxel_measure,
    }


def measure(labels: np.ndarray, contract: dict[str, Any], source_sha256: str) -> dict[str, Any]:
    started = time.perf_counter()
    checked = validate_contract(contract, labels, source_sha256)
    ids, counts = np.unique(labels, return_counts=True)
    positive = ids != 0
    ids, counts = ids[positive], counts[positive]
    if len(ids) > 10000:
        raise MissionError("more than 10000 labels exceeds this version's scoped budget")
    objects = []
    for label, count in zip(ids, counts, strict=True):
        coordinates = np.nonzero(labels == label)
        index_centroid = np.asarray([float(x.sum(dtype=np.float64)) / int(count) for x in coordinates])
        native_centroid = checked["origin"] + index_centroid * checked["spacing"]
        mapped_centroid = checked["linear"] @ native_centroid + checked["translation"]
        native_measure = int(count) * checked["voxel_measure"]
        mapped_measure = native_measure * checked["determinant"]
        if not np.all(np.isfinite(mapped_centroid)) or not np.isfinite(mapped_measure) or mapped_measure <= 0:
            raise MissionError("result overflows or underflows numeric scope", "REJECT")
        boundary = any(np.any(axis == 0) or np.any(axis == labels.shape[i] - 1) for i, axis in enumerate(coordinates))
        objects.append(
            {
                "label_id": int(label),
                "voxel_count": int(count),
                "native_measure": native_measure,
                "mapped_measure": mapped_measure,
                "native_centroid_um": native_centroid.tolist(),
                "mapped_centroid_um": mapped_centroid.tolist(),
                "touches_source_boundary": bool(boundary),
            }
        )
    contract_bytes = json.dumps(contract, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {
        "status": "ACCEPT",
        "version": VERSION,
        "mission_id": contract["mission_id"],
        "source_sha256": source_sha256,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "shape": list(labels.shape),
        "dtype": str(labels.dtype),
        "source_axes": contract["source_axes"],
        "target_axes": contract["target_axes"],
        "coordinate_unit": "micrometer",
        "measure_unit": f"micrometer^{labels.ndim}",
        "label_count": len(objects),
        "objects": objects,
        "jacobian_absolute_determinant": checked["determinant"],
        "scope": "geometric measurements of supplied label support; no biological or registration validity",
        "elapsed_seconds": time.perf_counter() - started,
    }


def run(labels_path: Path, contract_path: Path) -> dict[str, Any]:
    mission_id = None
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        if isinstance(contract, dict):
            mission_id = contract.get("mission_id")
        with labels_path.open("rb") as source:
            snapshot = source.read(1024 * 1024 * 1024 + 1)
        if len(snapshot) > 1024 * 1024 * 1024:
            raise MissionError("source file exceeds 1 GiB scope")
        source_sha256 = hashlib.sha256(snapshot).hexdigest()
        labels = np.load(io.BytesIO(snapshot), allow_pickle=False)
        if not isinstance(labels, np.ndarray):
            raise MissionError("one .npy array is required; archives are unsupported", "REJECT")
        return measure(labels, contract, source_sha256)
    except MissionError as exc:
        return {"status": exc.status, "version": VERSION, "mission_id": mission_id, "reason": exc.reason}
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        return {
            "status": "REJECT",
            "version": VERSION,
            "mission_id": mission_id,
            "reason": f"input cannot be interpreted: {type(exc).__name__}: {exc}",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Exact affine moments of supplied microscopy label support")
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.labels, args.contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"status": result["status"], "mission_id": result["mission_id"], "output": str(args.output)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
