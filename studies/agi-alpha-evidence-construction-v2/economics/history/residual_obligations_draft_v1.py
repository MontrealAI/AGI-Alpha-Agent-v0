# SPDX-License-Identifier: Apache-2.0
"""Separate uncertain verification effort from a mandatory review requirement."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Freeze a small additional sensitivity before calculating it."""
    plan_path = ROOT / "residual-obligations-plan.json"
    if not plan_path.exists():
        plan = {"schema": "residual-obligations-plan/v1", "frozen_utc": datetime.now(timezone.utc).isoformat(),
                "purpose": "The main illustrative25-minute verification input is not a required human-review minimum",
                "verification_minutes": [0, 10, 25, 60], "labor_rate_usd_hour": 125,
                "quality_condition": "All source semantics, uncertainty and provenance obligations still satisfied; no cost level grants acceptance",
                "zero_case": "Conditional complete automation of these obligations, not an observed capability",
                "reference_E_other_delivery_minutes": 65, "reference_Eplus_other_delivery_minutes": 45,
                "support_minutes": 6, "quote_usd": 325, "nonlabor_usd": 11,
                "source": "Explicit parameter sensitivity, not human-time observations or retrospective recovered profit"}
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    plan = json.loads(plan_path.read_text())
    rows = []
    for review in plan["verification_minutes"]:
        for name, other in [("E", 65), ("E+", 45)]:
            minutes = other + review + 6
            cost = minutes * 125 / 60 + 11
            rows.append({"configuration": name, "verification_minutes_assumed": review,
                         "total_provider_minutes_assumed": minutes, "complete_variable_cost_usd_assumed": round(cost, 2),
                         "contribution_before_B_C_and_shared_construction_usd": round(325 - cost, 2),
                         "urgent60_minute_labor_condition": minutes <= 60,
                         "quality_proven_by_this_calculation": False})
    result = {"schema": "residual-obligations-results/v1", "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
              "rows": rows, "actual_required_human_minutes": None,
              "interpretation": "Cost uncertain obligations once; automate where qualified. A retained tool cannot waive source-meaning acceptance."}
    (ROOT / "residual-obligations-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
