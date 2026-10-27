# SPDX-License-Identifier: Apache-2.0
"""Post-confirmation diagnostic for the information-value inclusion condition."""

from __future__ import annotations

import json
from pathlib import Path

from reference import TOL, load, q, reference, risk


def main() -> int:
    """Verify the analytic sufficient condition against all accepted finite plans."""
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "evaluation/protected/cases/manifest.json").read_text())
    rows = []
    for entry in manifest["cases"]:
        mission, digest = load(root / "evaluation/protected/cases" / entry["filename"])
        result = reference(mission, digest)
        if not result["observation_accepted"]:
            continue
        for op, answer in zip(mission["operators"], result["operators"], strict=True):
            if answer["baseline_action"] is None:
                continue
            action = next(a for a in op["actions"] if a["id"] == answer["baseline_action"])
            exclusions = []
            for branch in answer["branches"]:
                if not branch["reachable"]:
                    continue
                reasons = []
                if q(branch["observed_at_hours"]) > q(action["latest_start_hours"]) + TOL:
                    reasons.append("timing")
                if risk(action, [q(x) for x in branch["posterior"]]) > q(op["risk_limit"]) + TOL:
                    reasons.append("posterior-risk")
                if branch["id"] == "__timeout__" and action["id"] != op["fallback_action"]:
                    reasons.append("mandated-timeout-action")
                if reasons:
                    exclusions.append({"branch": branch["id"], "reasons": reasons})
            holds = not exclusions
            value = answer["value_of_information"]
            rows.append(
                {
                    "case_id": mission["mission_id"],
                    "category": entry["category"],
                    "operator_id": op["id"],
                    "prior_action_retained_in_every_branch": holds,
                    "information_value": value,
                    "exclusions": exclusions,
                    "sufficient_bound_satisfied": not holds or value >= -1e-8,
                }
            )
    negative_cases = {}
    for row in rows:
        if row["information_value"] < -1e-8:
            negative_cases.setdefault(row["case_id"], set()).update(
                reason for item in row["exclusions"] for reason in item["reasons"]
            )
    summary = {
        "schema": "shared-observation-information-bound/v1",
        "phase": "post-confirmation analytical diagnostic; no policy changes",
        "accepted_operator_count": len(rows),
        "inclusion_holds_count": sum(row["prior_action_retained_in_every_branch"] for row in rows),
        "inclusion_bound_violation_count": sum(not row["sufficient_bound_satisfied"] for row in rows),
        "negative_case_count": len(negative_cases),
        "negative_cases": {key: sorted(value) for key, value in negative_cases.items()},
        "rows": rows,
    }
    output = root / "evaluation/information-bound-check.json"
    if output.exists():
        raise ValueError("refusing to overwrite the analytical diagnostic")
    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, indent=2))
    return 0 if summary["inclusion_bound_violation_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
