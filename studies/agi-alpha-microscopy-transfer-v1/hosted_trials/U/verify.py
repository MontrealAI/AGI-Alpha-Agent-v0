#!/usr/bin/env python3
"""Independent high-precision verification of the actual delivered measurements.

Uses Decimal and explicit determinant expansion, per-voxel physical coordinates,
and per-voxel affine transformation rather than the solver's mean-index shortcut.
"""
import hashlib
import itertools
import json
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np


def main():
    out = Path(__file__).parent
    inp = out.parent / "inputs"
    cases = json.loads((inp / "cases.json").read_text())
    answers = json.loads((out / "answers.json").read_text())
    assert len(answers) == len(cases) == 12
    assert [a["case_id"] for a in answers] == [c["case_id"] for c in cases]
    factors = {"micrometer": Decimal(1), "nanometer": Decimal("0.001")}
    max_measure_relative_error = Decimal(0)
    max_centroid_absolute_error = Decimal(0)
    checked_objects = 0
    with localcontext() as context:
        context.prec = 70
        for case, answer in zip(cases, answers):
            contract = json.loads((inp / case["contract"]).read_text(), parse_float=Decimal)
            path = inp / case["array"]
            array = np.load(path, allow_pickle=False)
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if answer["status"] != "ACCEPT":
                assert answer["reason"]
                if case["case_id"] == 8:
                    assert "mean_intensity" in contract["metrics"] and answer["status"] == "HOLD"
                elif case["case_id"] == 9:
                    assert contract["affine"][-1][0] != 0 and answer["status"] == "REJECT"
                elif case["case_id"] == 10:
                    assert contract["source_sha256"] != actual_hash and answer["status"] == "REJECT"
                elif case["case_id"] == 11:
                    assert contract["coverage"] == "complete_biological_objects" and answer["status"] == "HOLD"
                else:
                    raise AssertionError("Unexpected nonaccepted mission")
                continue
            assert contract["source_sha256"] == actual_hash
            d = array.ndim
            spacing = [Decimal(x) * factors[u] for x, u in zip(contract["spacing"], contract["units"])]
            origin = [Decimal(x) * factors[u] for x, u in zip(contract["origin"], contract["units"])]
            affine = [[Decimal(x) for x in row] for row in contract["affine"]]
            determinant = Decimal(0)
            for permutation in itertools.permutations(range(d)):
                inversions = sum(permutation[i] > permutation[j] for i in range(d) for j in range(i + 1, d))
                term = Decimal(-1 if inversions % 2 else 1)
                for row in range(d):
                    term *= affine[row][permutation[row]]
                determinant += term
            voxel_measure = Decimal(1)
            for step in spacing:
                voxel_measure *= step
            labels = sorted(int(x) for x in np.unique(array) if x != 0)
            assert answer["label_count"] == len(labels)
            assert [o["label_id"] for o in answer["objects"]] == labels
            for obj in answer["objects"]:
                indices = np.argwhere(array == obj["label_id"]).tolist()
                n = len(indices)
                assert obj["voxel_count"] == n
                native_points = [[origin[j] + Decimal(index[j]) * spacing[j] for j in range(d)] for index in indices]
                mapped_points = [[sum(affine[i][j] * p[j] for j in range(d)) + affine[i][d] for i in range(d)] for p in native_points]
                expected_native = [sum(p[j] for p in native_points) / n for j in range(d)]
                expected_mapped = [sum(p[j] for p in mapped_points) / n for j in range(d)]
                measures = {"native_measure": n * voxel_measure,
                            "mapped_measure": n * voxel_measure * abs(determinant)}
                for key, expected in measures.items():
                    relative_error = abs(Decimal(str(obj[key])) - expected) / abs(expected)
                    assert relative_error <= Decimal("1e-9"), (case["case_id"], key, relative_error)
                    max_measure_relative_error = max(max_measure_relative_error, relative_error)
                for key, expected in (("native_centroid_um", expected_native), ("mapped_centroid_um", expected_mapped)):
                    assert len(obj[key]) == d
                    for actual, target in zip(obj[key], expected):
                        absolute_error = abs(Decimal(str(actual)) - target)
                        assert absolute_error <= Decimal("1e-8"), (case["case_id"], key, absolute_error)
                        max_centroid_absolute_error = max(max_centroid_absolute_error, absolute_error)
                checked_objects += 1
        assert answers[7] == {"case_id": 7, "status": "ACCEPT", "label_count": 0, "objects": []}
        assert answers[6]["objects"][0]["label_id"] == -3
        assert answers[5]["objects"][1]["voxel_count"] == 1
    result = {"status": "PASS", "cases_checked": len(cases), "accepted_objects_checked": checked_objects,
              "max_measure_relative_error": str(max_measure_relative_error),
              "max_centroid_absolute_error_um": str(max_centroid_absolute_error),
              "relative_measure_tolerance": "1e-9", "absolute_centroid_tolerance_um": "1e-8",
              "method": "70-digit Decimal, explicit determinant expansion and per-voxel affine means"}
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
