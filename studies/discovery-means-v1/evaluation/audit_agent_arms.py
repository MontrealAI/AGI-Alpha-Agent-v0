# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).parent
    spec = importlib.util.spec_from_file_location("independent_evaluation", root / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = json.loads((root / "task_manifest.json").read_text())
    blinded = json.loads((root / "blinded_tasks.json").read_text())
    original = {c["case_id"]: c for c in manifest["cases"]}
    assert len(blinded) == len(original) and len({c["case_id"] for c in blinded}) == len(original)
    for case in blinded:
        assert module.clean_case(case) == module.clean_case(original[case["case_id"]])
    oracle = {r["case_id"]: r["oracle"] for r in json.loads((root / "results.json").read_text())["rows"]}
    arms = []
    for name, filename, usagefile in (("fresh_hosted_generalist", "generalist_outputs.json", "generalist_usage_receipt.json"),
                                     ("fresh_hosted_prompt_guided", "prompt_outputs.json", "prompt_usage.json")):
        path = root / filename
        reports = json.loads(path.read_text())
        ids = [r.get("case_id") for r in reports]
        denominator_valid = len(reports) == len(original) and set(ids) == set(original) and len(set(ids)) == len(ids)
        rows = []
        for report in reports:
            case_id = report["case_id"]
            expected = oracle[case_id]
            status_matches = report["status"] == ("feasible" if expected["status"] == "optimal" else "infeasible")
            audit = module.audit_policy(module.clean_case(original[case_id]), report.get("policy")) if report["status"] == "feasible" else None
            cost_matches = report.get("worst_cost") == expected["worst_cost"]
            correct = status_matches and cost_matches and (audit is None or audit["accepted"] and audit["worst_cost"] == expected["worst_cost"])
            rows.append({"case_id": case_id, "status_matches": status_matches, "cost_matches": cost_matches,
                         "certificate_audit": audit, "correct": bool(correct)})
        usage = json.loads((root / usagefile).read_text())
        input_sha = hashlib.sha256((root / "blinded_tasks.json").read_bytes()).hexdigest()
        arms.append({"arm": name, "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "usage_receipt_sha256": hashlib.sha256((root / usagefile).read_bytes()).hexdigest(),
                     "input_hash_agrees": usage.get("input_sha256") == input_sha,
                     "denominator_valid": denominator_valid, "rows": rows,
                     "summary": {"cases": len(original), "correct": sum(r["correct"] for r in rows),
                                 "feasible_valid_certificates": sum(bool(r["certificate_audit"] and r["certificate_audit"]["accepted"]) for r in rows)}})
    result = {"scope": "Exploratory fresh hosted-session controls using only blinded24case inputs and self-authored ordinary Python. Same tool availability/caps; no inherited instrument executable. Same-team access statements are not external isolation proof. Named exact model, hidden reasoning tokens, monetary costs and repeated-run performance unverified.",
              "blinded_inputs_equal_original": True, "arms": arms,
              "interpretation": "Both hosted arms independently construct a competent exact conventional solution. Equal correctness and worst-cost results do not establish superiority for the new instrument or prompt guidance. Named frontier-API/cost-adjusted comparison remains unqualified.",
              "primary_source_and_policy_retuned": False}
    out = root / "agent_comparison.json"
    if out.exists():
        raise SystemExit("refusing to overwrite agent comparison")
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({x["arm"]: x["summary"] for x in arms}))


if __name__ == "__main__":
    main()
