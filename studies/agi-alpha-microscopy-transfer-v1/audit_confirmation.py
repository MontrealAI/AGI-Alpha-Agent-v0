"""Re-score preserved outputs without executing or changing the frozen instrument."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from confirmation_reference import compare


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=ROOT / "confirmation/results/frozen-v1")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    records = []
    for mission in sorted((args.results / "compatible").iterdir()):
        reference = json.loads((mission / "coordinate-reference.json").read_text())
        for arm, filename in [
            ("recovered", "received-result.json"),
            ("ordinary_library", "ordinary-library-result.json"),
            ("conventional", "conventional-analytical.json"),
        ]:
            actual = json.loads((mission / filename).read_text())
            records.append({"task_id": mission.name, "arm": arm, **compare(actual, reference)})
    # A post-run comparator audit found a potential NaN masking issue in Python max().
    # The archived first-run comparator is preserved; this targeted guard cannot improve a score.
    example = json.loads(next((args.results / "compatible").glob("*/coordinate-reference.json")).read_text())
    probes = {}
    for field in ["native_measure", "mapped_measure", "native_centroid_um", "mapped_centroid_um"]:
        probe = copy.deepcopy(example)
        if isinstance(probe["objects"][0][field], list):
            probe["objects"][0][field][0] = float("nan")
        else:
            probe["objects"][0][field] = float("nan")
        probes[field] = compare(probe, example)
    report = {
        "method": "Post-run stricter audit of preserved outputs; no instrument invocation or outcome replacement.",
        "comparator_sha256": hashlib.sha256((ROOT / "confirmation_reference.py").read_bytes()).hexdigest(),
        "initial_comparator_sha256": hashlib.sha256(
            (args.results / "evaluator-source/confirmation_reference.py").read_bytes()).hexdigest(),
        "counts": {arm: sum(r["passed"] for r in records if r["arm"] == arm)
                   for arm in ["recovered", "ordinary_library", "conventional"]},
        "records": records,
        "nan_rejection_probes": probes,
        "all_nan_probes_refused": all(not p["passed"] for p in probes.values()),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
