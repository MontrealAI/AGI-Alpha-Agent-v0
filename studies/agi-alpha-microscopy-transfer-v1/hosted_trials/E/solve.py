"""Measure the supplied label support and its explicit physical affine image.

Scope: 2D/3D integer labels; zero background; each other signed ID is one
region; supported physical units; verified exact source bytes; explicitly
provided support; geometric affine pushforward. Centroids are in the listed
source/target axis orders. No permutation or half-voxel shift is added.

Native measure = count * product(spacing in micrometers).
Mapped measure = native measure * abs(det(affine linear block)).
Native centroid = origin_um + spacing_um * mean(source indices).
Mapped centroid = linear block @ native centroid + translation.
"""
from pathlib import Path
from io import BytesIO
from decimal import Decimal, localcontext
from itertools import permutations
import datetime
import hashlib
import json
import math
import time

import numpy as np


INPUT = Path(__file__).resolve().parent.parent / "inputs"
OUTPUT = Path(__file__).resolve().parent
UNITS = {"micrometer": 1.0, "nanometer": 0.001}
METRICS = {"label_count", "native_measure", "mapped_measure",
           "native_centroid", "mapped_centroid"}


def evaluate(case_id, array, contract, digest):
    def refuse(status, reason):
        return {"case_id": case_id, "status": status, "reason": reason}

    if contract.get("source_sha256") != digest:
        return refuse("REJECT", "Source SHA-256 mismatch: the supplied array file "
                      "does not match the contract's required source identity.")
    if contract.get("schema") != "microscopy-moments/v1":
        return refuse("HOLD", "Unknown contract schema; measurement meaning is unverified.")
    dim = array.ndim
    if dim not in (2, 3) or not np.issubdtype(array.dtype, np.integer):
        return refuse("REJECT", "Only 2D/3D integer label arrays are supported.")
    if contract.get("object_definition") != "label_id":
        return refuse("HOLD", "Object identity is not explicitly defined by label ID.")
    if contract.get("coverage") != "provided_label_support":
        return refuse("HOLD", "The requested complete biological objects cannot be "
                      "established from supplied label support; completeness evidence is absent.")
    if contract.get("map_semantics") != "geometric_pushforward":
        return refuse("HOLD", "Map meaning is not the supported geometric pushforward.")
    requested = contract.get("metrics")
    if not isinstance(requested, list) or not all(isinstance(x, str) for x in requested):
        return refuse("HOLD", "Requested metrics are not explicitly identified.")
    unsupported = sorted(set(requested) - METRICS)
    if unsupported:
        return refuse("HOLD", "Unsupported requested metrics: " + ", ".join(unsupported)
                      + ". Label support supplies no intensity observations; those metrics "
                      "cannot be inferred or silently omitted from an accepted mission.")
    for key in ("source_axes", "target_axes"):
        axes = contract.get(key)
        if (not isinstance(axes, list) or len(axes) != dim or
                any(not isinstance(x, str) for x in axes) or len(set(axes)) != dim):
            return refuse("HOLD", "Missing or ambiguous " + key + " order.")
    units = contract.get("units")
    if not isinstance(units, list) or len(units) != dim or any(u not in UNITS for u in units):
        return refuse("HOLD", "Missing or unsupported source physical units.")
    try:
        spacing = np.asarray(contract["spacing"], dtype=np.float64)
        origin = np.asarray(contract["origin"], dtype=np.float64)
        affine = np.asarray(contract["affine"], dtype=np.float64)
    except (KeyError, TypeError, ValueError):
        return refuse("REJECT", "Calibration or transform is missing or malformed.")
    if (spacing.shape != (dim,) or origin.shape != (dim,) or
            not np.isfinite(spacing).all() or not np.isfinite(origin).all() or
            not (spacing > 0).all()):
        return refuse("REJECT", "Calibration must have finite origin and positive finite spacing.")
    if affine.shape != (dim + 1, dim + 1) or not np.isfinite(affine).all():
        return refuse("REJECT", "Transform must be a finite homogeneous affine matrix.")
    if not np.array_equal(affine[-1], np.r_[np.zeros(dim), 1.0]):
        return refuse("REJECT", "The last homogeneous row is not [0,...,0,1]; "
                      "the supplied transform is non-affine and outside the requested scope.")
    scales = np.asarray([UNITS[u] for u in units])
    spacing_um = spacing * scales
    origin_um = origin * scales
    linear, translation = affine[:dim, :dim], affine[:dim, dim]
    determinant = float(np.linalg.det(linear))
    if not math.isfinite(determinant) or determinant == 0:
        return refuse("HOLD", "The affine map is singular or numerically invalid; "
                      "a full-dimensional mapped region centroid is unsupported.")
    voxel_measure = float(np.prod(spacing_um))
    objects = []
    for label in np.unique(array):
        if label == 0:
            continue
        indices = np.argwhere(array == label)
        count = int(len(indices))
        native_centroid = origin_um + spacing_um * indices.mean(axis=0)
        native_measure = count * voxel_measure
        objects.append({
            "label_id": int(label), "voxel_count": count,
            "native_measure": native_measure,
            "mapped_measure": native_measure * abs(determinant),
            "native_centroid_um": native_centroid.tolist(),
            "mapped_centroid_um": (linear @ native_centroid + translation).tolist(),
        })
    return {"case_id": case_id, "status": "ACCEPT", "label_count": len(objects),
            "objects": objects}


def known_case_check():
    contract = {
        "source_sha256": "analytic", "schema": "microscopy-moments/v1",
        "source_axes": ["y", "x"], "target_axes": ["x", "y"],
        "spacing": [2000, 0.5], "origin": [1000, -1],
        "units": ["nanometer", "micrometer"], "object_definition": "label_id",
        "coverage": "provided_label_support", "map_semantics": "geometric_pushforward",
        "metrics": sorted(METRICS), "affine": [[-2, 1, 4], [0, 3, -5], [0, 0, 1]],
    }
    array = np.array([[0, -3, -3], [5, 0, 0]], dtype=np.int16)
    result = evaluate("analytic", array, contract, "analytic")
    assert result["status"] == "ACCEPT" and result["label_count"] == 2
    for actual, expected in zip(result["objects"], [
        (-3, 2, 2, 12, [1, -0.25], [1.75, -5.75]),
        (5, 1, 1, 6, [3, -1], [-3, -8]),
    ]):
        label, count, native, mapped, nc, mc = expected
        assert actual["label_id"] == label and actual["voxel_count"] == count
        assert math.isclose(actual["native_measure"], native, rel_tol=1e-12)
        assert math.isclose(actual["mapped_measure"], mapped, rel_tol=1e-12)
        np.testing.assert_allclose(actual["native_centroid_um"], nc, rtol=0, atol=1e-12)
        np.testing.assert_allclose(actual["mapped_centroid_um"], mc, rtol=0, atol=1e-12)
    empty = evaluate("empty", np.zeros((2, 3), dtype=np.int16), contract, "analytic")
    assert empty["status"] == "ACCEPT" and empty["label_count"] == 0 and empty["objects"] == []


def independent_check(array, contract, answer):
    """Use 60-digit Decimal arithmetic, explicit determinant and exact index sums."""
    with localcontext() as ctx:
        ctx.prec = 60
        d = array.ndim
        scale = [Decimal("0.001") if u == "nanometer" else Decimal(1)
                 for u in contract["units"]]
        spacing = [Decimal(str(x)) * k for x, k in zip(contract["spacing"], scale)]
        origin = [Decimal(str(x)) * k for x, k in zip(contract["origin"], scale)]
        affine = [[Decimal(str(x)) for x in row] for row in contract["affine"]]
        determinant = Decimal(0)
        for p in permutations(range(d)):
            inversions = sum(p[i] > p[j] for i in range(d) for j in range(i + 1, d))
            determinant += (-1 if inversions % 2 else 1) * math.prod(affine[i][p[i]] for i in range(d))
        ids = sorted(int(x) for x in np.unique(array) if x != 0)
        assert answer["label_count"] == len(ids)
        assert [o["label_id"] for o in answer["objects"]] == ids
        max_relative_measure_error = 0.0
        max_absolute_centroid_error_um = 0.0
        for obj in answer["objects"]:
            coords = np.argwhere(array == obj["label_id"])
            n = len(coords)
            assert obj["voxel_count"] == n
            native = Decimal(n) * math.prod(spacing)
            mapped = native * abs(determinant)
            nc = [origin[j] + spacing[j] * Decimal(sum(int(row[j]) for row in coords)) / Decimal(n)
                  for j in range(d)]
            mc = [sum(affine[i][j] * nc[j] for j in range(d)) + affine[i][d] for i in range(d)]
            for field, expected in [("native_measure", native), ("mapped_measure", mapped)]:
                error = abs(Decimal(str(obj[field])) - expected) / abs(expected)
                assert error <= Decimal("1e-9"), (field, error)
                max_relative_measure_error = max(max_relative_measure_error, float(error))
            for field, expected in [("native_centroid_um", nc), ("mapped_centroid_um", mc)]:
                for actual, value in zip(obj[field], expected):
                    error = abs(Decimal(str(actual)) - value)
                    assert error <= Decimal("1e-8"), (field, error)
                    max_absolute_centroid_error_um = max(max_absolute_centroid_error_um, float(error))
        return {"max_relative_measure_error": max_relative_measure_error,
                "max_absolute_centroid_error_um": max_absolute_centroid_error_um}


def main():
    started = time.perf_counter()
    known_case_check()
    cases = json.loads((INPUT / "cases.json").read_text())
    answers, audit = [], []
    for case in cases:
        raw = (INPUT / case["array"]).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        array = np.load(BytesIO(raw), allow_pickle=False)
        contract = json.loads((INPUT / case["contract"]).read_text())
        answer = evaluate(case["case_id"], array, contract, digest)
        evidence = {"case_id": case["case_id"], "array_shape": list(array.shape),
                    "array_dtype": str(array.dtype), "source_sha256_observed": digest,
                    "source_sha256_matches": digest == contract["source_sha256"],
                    "status": answer["status"]}
        if answer["status"] == "ACCEPT":
            evidence["verification"] = independent_check(array, contract, answer)
        answers.append(answer)
        audit.append(evidence)
    expected = {**{i: "ACCEPT" for i in range(8)}, 8: "HOLD", 9: "REJECT", 10: "REJECT", 11: "HOLD"}
    assert {a["case_id"]: a["status"] for a in answers} == expected
    assert len(answers) == len(cases) and len({a["case_id"] for a in answers}) == len(cases)
    (OUTPUT / "answers.json").write_text(json.dumps(answers, indent=2, allow_nan=False) + "\n")
    receipt = {
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "configuration": "E: independent worker with supplied expert_workflow.txt rubric",
        "tools_observed": [
            {"invocation": 1, "tool": "exec_command", "work": "Read TASK.md, cases.json, expert_workflow.txt and list input files."},
            {"invocation": 2, "tool": "exec_command", "work": "Inspect every actual array and contract; compute exact file SHA-256 and label counts."},
            {"invocation": 3, "tool": "apply_patch", "work": "Save solve.py with scope checks, calculation, analytic validation and Decimal cross-check."},
            {"invocation": 4, "tool": "exec_command", "work": "Run solve.py; write answers.json and receipt.json; reload and inspect delivered file summaries."},
        ],
        "underlying_tool_invocations": 4,
        "functions_exec_orchestration_calls": 4,
        "corrections": [],
        "correction_note": "No failed run, code correction, input correction, or silently altered contract was needed.",
        "validation": {"known_case": "Passed analytic mixed-unit 2D example with negative label, reflection, shear, translation, axis-order change, and empty support.",
                       "actual_cases": "All accepted objects independently checked with 60-digit Decimal arithmetic against the stated tolerances.",
                       "scope_review": "All 12 actual missions inspected; four incompatible requests refused.",
                       "case_audit": audit},
        "execution_elapsed_seconds": time.perf_counter() - started,
        "costs": {"token_count": None, "billing_cost": None,
                  "availability": "Token counts and billing unavailable; no estimates invented.",
                  "full_worker_wall_time_seconds": None,
                  "wall_time_note": "Only script execution duration was measured; full worker latency was not instrumented."},
        "read_scope": ["assigned inputs", "expert_workflow.txt", "assigned E output", "installed Python and NumPy dependencies"],
        "network_used": False, "subagents_used": False,
        "output_files": ["answers.json", "solve.py", "receipt.json"],
    }
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    # Re-read serialized deliverables so successful completion includes the actual files.
    saved = json.loads((OUTPUT / "answers.json").read_text())
    saved_receipt = json.loads((OUTPUT / "receipt.json").read_text())
    assert saved == answers and saved_receipt["validation"]["case_audit"] == audit
    print(json.dumps({"files": [str(OUTPUT / name) for name in receipt["output_files"]],
                      "statuses": [{"case_id": a["case_id"], "status": a["status"],
                                    "label_count": a.get("label_count")} for a in saved],
                      "accepted_objects": sum(len(a.get("objects", [])) for a in saved),
                      "max_relative_measure_error": max((e.get("verification", {}).get("max_relative_measure_error", 0) for e in audit)),
                      "max_absolute_centroid_error_um": max((e.get("verification", {}).get("max_absolute_centroid_error_um", 0) for e in audit)),
                      "execution_elapsed_seconds": saved_receipt["execution_elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
