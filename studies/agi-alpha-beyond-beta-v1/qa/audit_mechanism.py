#!/usr/bin/env python3
"""Independent QA for the formal mechanism; not extra primary observations."""
from pathlib import Path
import hashlib
import importlib.util
import itertools
import json
import random

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiment" / "foundry.py"

def run():
    spec = importlib.util.spec_from_file_location("foundry_review", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rng = random.Random(894371)
    counts = dict(instances=0, candidates=0, correct_rejections=0,
                  correct_acceptances=0, infeasible_abstentions=0, producer_optima=0)
    failures = []
    for case in range(96):
        n, k = rng.randint(1, 5), rng.randint(1, 4)
        instance = {
            "costs": [[rng.randint(-9, 9) for _ in range(k)] for _ in range(n)],
            "capacities": [rng.randint(0, n) for _ in range(k)],
            "allowed": [[rng.random() > .45 for _ in range(k)] for _ in range(n)],
        }
        assignments = list(itertools.product(range(k), repeat=n))
        feasible = [
            a for a in assignments
            if all(a.count(j) <= instance["capacities"][j] for j in range(k))
            and all(instance["allowed"][i][j] for i, j in enumerate(a))
        ]
        best = min((sum(instance["costs"][i][j] for i, j in enumerate(a))
                    for a in feasible), default=None)
        produced = module.produce(instance)
        if best is None:
            if produced["status"] != "abstain":
                failures.append({"case": case, "type": "infeasible_producer"})
            counts["infeasible_abstentions"] += 1
        else:
            if produced["status"] != "candidate" or produced["cost"] != best:
                failures.append({"case": case, "type": "producer"})
            counts["producer_optima"] += 1
        for assignment in assignments:
            cost = sum(instance["costs"][i][j] for i, j in enumerate(assignment))
            expected = assignment in feasible and cost == best
            got = module.validate(
                instance, {"assignment": list(assignment), "cost": cost}
            )["accepted"]
            counts["candidates"] += 1
            if got != expected:
                failures.append({"case": case, "assignment": assignment,
                                 "expected": expected, "actual": got})
            elif got:
                counts["correct_acceptances"] += 1
            else:
                counts["correct_rejections"] += 1
        counts["instances"] += 1
    return {
        "status": "PASS" if not failures else "FAIL",
        "test_type": "Independent post-protocol scientific QA; not additional primary research observations",
        "seed": 894371,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "method": "Exhaustive independent feasibility/objective oracle for every assignment on 96 randomly drawn 1–5 job / 1–4 resource instances, including asymmetric/zero capacities, negative costs and infeasible eligibility. Tests all feasible suboptimal assignments, not just producer outputs.",
        "counts": counts,
        "failures": failures,
    }

if __name__ == "__main__":
    result = run()
    (ROOT / "qa" / "mechanism_independent_audit.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
