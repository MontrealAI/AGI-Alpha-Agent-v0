# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
TRIAL = ROOT / "hosted_trials"


def gold(case: dict) -> dict:
    c = json.loads((TRIAL / "inputs" / case["contract"]).read_text())
    array = np.load(TRIAL / "inputs" / case["array"], allow_pickle=False)
    factor = np.asarray([{"micrometer": 1, "nanometer": 0.001}[x] for x in c["units"]])
    spacing, origin = np.asarray(c["spacing"]) * factor, np.asarray(c["origin"]) * factor
    transform = np.asarray(c["affine"])
    objects = []
    for label in np.unique(array):
        if label == 0:
            continue
        locations = np.argwhere(array == label)
        source = locations * spacing + origin
        target = source @ transform[:-1, :-1].T + transform[:-1, -1]
        native = len(locations) * math.prod(spacing)
        mapped = native * abs(float(np.linalg.det(transform[:-1, :-1])))
        objects.append({"label_id": int(label), "voxel_count": len(locations),
                        "native_measure": native, "mapped_measure": mapped,
                        "native_centroid_um": source.mean(axis=0).tolist(),
                        "mapped_centroid_um": target.mean(axis=0).tolist()})
    return {"label_count": len(objects), "objects": objects}


def compare(expected: dict, got: dict) -> dict:
    if got.get("status") != "ACCEPT" or got.get("label_count") != expected["label_count"]:
        return {"passed": False, "reason": "acceptance/count mismatch"}
    actual = got.get("objects", [])
    objects = {o["label_id"]: o for o in actual}
    if len(objects) != len(actual) or set(objects) != {o["label_id"] for o in expected["objects"]}:
        return {"passed": False, "reason": "label identity mismatch"}
    measure_error, centroid_error = 0.0, 0.0
    for e in expected["objects"]:
        o = objects[e["label_id"]]
        if o.get("voxel_count") != e["voxel_count"]:
            return {"passed": False, "reason": "voxel count mismatch"}
        for field in ["native_measure", "mapped_measure"]:
            value = float(o[field])
            if not math.isfinite(value):
                return {"passed": False, "reason": "nonfinite measure"}
            measure_error = max(measure_error, abs(value - e[field]) / e[field])
        for field in ["native_centroid_um", "mapped_centroid_um"]:
            value = np.asarray(o[field], dtype=float)
            if value.shape != np.asarray(e[field]).shape or not np.all(np.isfinite(value)):
                return {"passed": False, "reason": "nonfinite/invalid centroid"}
            centroid_error = max(centroid_error, float(np.max(np.abs(value - e[field]))))
    return {"passed": measure_error <= 1e-9 and centroid_error <= 1e-8,
            "max_relative_measure_error": measure_error, "max_absolute_centroid_error_um": centroid_error}


def main() -> None:
    commitment = json.loads((TRIAL / "pretrial_commitment.json").read_text())
    for relative, expected in commitment["inputs"].items():
        assert hashlib.sha256((TRIAL / relative).read_bytes()).hexdigest() == expected, relative
    cases = json.loads((TRIAL / "inputs/cases.json").read_text())
    expected = {case["case_id"]: gold(case) for case in cases if case["case_id"] < 8}
    summary = {"design": "one fresh same-model worker per arm; same authored tasks, tools and ceilings",
               "independence": "common external scorer within the same AI-assisted team; not external validation",
               "limits": "one run per arm; no randomization, token/compute equality or complete-cost telemetry",
               "operational_alpha_quality_established": False, "retained_incremental_quality_established": False,
               "complete_cost_advantage_established": False, "arms": {}}
    for arm in ["U", "E", "Eplus"]:
        p = TRIAL / arm / "answers.json"
        answers = json.loads(p.read_text())
        keyed = {a["case_id"]: a for a in answers}
        assert len(keyed) == len(answers) == len(cases)
        assert set(keyed) == set(range(12))
        scored = []
        for case in cases:
            i = case["case_id"]
            a = keyed[i]
            if i < 8:
                score = compare(expected[i], a)
            else:
                score = {"passed": a.get("status") in ("HOLD", "REJECT") and bool(a.get("reason")),
                         "reason": "appropriate declared scope/source refusal"}
            scored.append({"case_id": i, **score})
        summary["arms"][arm] = {"passed": sum(x["passed"] for x in scored), "total": 12,
                                "answer_sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "cases": scored}
    (TRIAL / "scoring.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({arm: {"passed": row["passed"], "total": row["total"]}
                      for arm, row in summary["arms"].items()}))


if __name__ == "__main__":
    main()
