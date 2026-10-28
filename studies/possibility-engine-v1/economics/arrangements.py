# SPDX-License-Identifier: Apache-2.0
"""Conditional coordination and scale thresholds; no market evidence is implied."""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def analyze() -> dict[str, Any]:
    """Compare exactly the same three-sponsor arrangement under conventional delivery."""
    c = json.loads((ROOT / "assumptions.json").read_text())
    j = c["joint"]
    shared = j["shared_integration_hours"] * j["rate"]
    per = j["per_sponsor_hours"] * j["rate"]
    coordination = j["coordination_hours"] * j["rate"]
    sponsor_price = j["price_total_cents"] / 100 / j["sponsors"]
    fixed = sum(hours * rate for _, hours, rate in c["startup"])
    fixed += sum(
        c[x] / 100
        for x in (
            "startup_inference_cents",
            "startup_compute_cents",
            "startup_tools_cents",
        )
    )
    rows = []
    for n in range(1, 13):
        revenue = sponsor_price * n
        costs = shared + coordination + per * n
        rows.append(
            {
                "sponsors": n,
                "revenue_usd": revenue,
                "variable_cost_usd": costs,
                "contribution_usd": revenue - costs,
                "full_project_return_usd": revenue - costs - fixed,
                "conventional_same_arrangement_return_usd": revenue - costs - fixed,
            }
        )
    rates = []
    for consent in (0.4, 0.7, 0.9):
        unanimous = consent ** j["sponsors"]
        success_cost = shared + coordination + per * j["sponsors"]
        contribution = j["price_total_cents"] / 100 - success_cost
        rates.append(
            {
                "individual_rights_consent": consent,
                "independent_unanimity": unanimous,
                "contribution_per_attempt_usd": unanimous * contribution
                - (1 - unanimous) * coordination,
                "shared_refusal_stress_unanimity": unanimous * 0.6,
                "correlated_contribution_per_attempt_usd": unanimous
                * 0.6
                * contribution
                - (1 - unanimous * 0.6) * coordination,
            }
        )
    scales = []
    for net_value in (500, 2500, 10000):
        packs = 1_000_000_000 / net_value
        annual = packs / 10
        accounts = annual / 4
        scales.append(
            {
                "net_incremental_beneficiary_value_per_pack_usd": net_value,
                "ten_year_packs_required": packs,
                "active_accounts_at_four_packs_per_year": accounts,
                "annual_deliveries_required": annual,
                "teams_at_24_packs_per_year": annual / 24,
                "verification_hours_per_year_at_four_per_pack": annual * 4,
            }
        )
    pilot = []
    for p in (0.2, 0.5, 0.7):
        for benefit in (8000, 16000, 24000):
            pilot.append(
                {
                    "success_probability_assumed": p,
                    "conditional_incremental_value_usd": benefit,
                    "experiment_cost_usd": 4000,
                    "expected_incremental_net_usd": p * benefit - 4000,
                }
            )
    return {
        "simulation": True,
        "costs_usd": {
            "shared_startup_once": fixed,
            "shared_integration": shared,
            "coordination": coordination,
            "per_sponsor_validation": per,
            "price_per_sponsor": sponsor_price,
        },
        "sponsor_rows": rows,
        "rights_and_coordination_sensitivity": rates,
        "scale_thresholds": scales,
        "pilot_thresholds": pilot,
        "pilot_probability_is_assumption_not_inferred": True,
        "physical_port_build_costs_excluded_from_software_scope": True,
        "joint_contract_condition": "All sponsors consent before release; otherwise refund all restricted pledges",
        "reuse_rights": "Share generic software with consent; keep private model data with each sponsor",
        "free_riding": "Open-source later availability creates a waiting equilibrium; no guaranteed commitment",
        "participation": "Each joins only if incremental benefit exceeds price, privacy and coordination costs",
        "commercial_demand_or_billion_dollar_scale_established": False,
    }


if __name__ == "__main__":
    result = analyze()
    (ROOT / "arrangement_analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["costs_usd"]))
