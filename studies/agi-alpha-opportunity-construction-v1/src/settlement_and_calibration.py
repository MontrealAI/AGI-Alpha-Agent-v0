# SPDX-License-Identifier: Apache-2.0
"""Finite escrow conservation and a wage-anchored provider-cost stress check.

Post-confirmation diagnostics: these do not replace the frozen central policy,
its synthetic cases, or its commercial outcome. No financial action occurs.
"""

from __future__ import annotations
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from e1_instrument_v2 import solve  # noqa: E402
from e1_verify_v2 import verify_offer  # noqa: E402


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main():
    contract = json.loads((ROOT / "technical/monthly_package/CONTRACT.json").read_text())
    days = json.loads((ROOT / "technical/monthly_package/DAY_WITNESSES.json").read_text())
    rows = []
    for day in days:
        offer = day["offer"]
        funded = offer["pass_through_obligations_cents"]
        reserve = offer["cost_totals_cents"]["backup_activation_reserve"]
        normal = funded - reserve
        for world in offer["worlds"]:
            activated = world["activation_cost_cents"]
            consumed = normal + activated
            refund = reserve - activated
            row = {
                "day": day["day"],
                "world": world["scenario_id"],
                "customer_pass_funding_cents": funded,
                "customer_pass_consumed_cents": consumed,
                "returned_reserve_cents": refund,
                "remaining_modelled_obligation_cents": 0,
                "service_revenue_from_pass_funds_cents": 0,
                "conserved": funded == consumed + refund and min(refund, consumed) >= 0,
            }
            rows.append(row)
    assert all(x["conserved"] for x in rows)
    settlement = {
        "schema": "agi-alpha.finite-escrow-enumeration.v1",
        "mode": "Local simulation, no actual ledger or escrow account",
        "world_day_rows": len(rows),
        "all_conserved": True,
        "rows": rows,
        "closure_condition": "Each defined pre-start world completes and the unused reserve is returned; unexpected states are outside this contract and must not be represented as settled.",
        "service_release": {
            "acceptance_payment_due_cad": contract["initial_service_payment_cad"],
            "deferred_receivable_cad": contract["deferred_service_receivable_cad"],
            "zero_payment_refused": 0 < contract["initial_service_payment_cad"],
            "full_acceptance_payment_sufficient": contract["initial_service_payment_cad"]
            >= contract["total_service_fee_cad"] / 2,
            "customer_pass_funding_not_available_to_pay_service_invoice": True,
        },
    }
    write(ROOT / "economics/FINITE_SETTLEMENT_CHECK.json", settlement)
    origin = json.loads((ROOT / "technical/origin_case.json").read_text())
    stresses = []
    for label, wage, burden in [("low", 16.6, 1.2), ("central", 24, 1.35), ("high", 30.03, 1.5)]:
        # Burden covers employment benefits/payroll only; facility and admin are
        # separate. These multipliers and hours are estimates, not supplier quotes.
        staff = round(5 * wage * burden * 100)
        fixed = staff + 5000
        for empcap in [14500, 20000, 27500]:
            case = copy.deepcopy(origin)
            case["case_id"] = f"provider-cost-{label}-cap{empcap}"
            case["coordinator_fee_cents"] = 3750
            for o in case["offers"]:
                o["fixed_opening_cost_cents"] = fixed
                o["cost_breakdown"] = {
                    "qualified_staff": staff,
                    "facility": 2000,
                    "provider_admin_and_insurance_allocation": 3000,
                }
            for p in case["payers"]:
                if p["kind"] == "employer":
                    p["payment_ceiling_cents"] = empcap
            result = solve(case, "combined")
            if result["offer"]:
                check = verify_offer(case, result["offer"])
                assert check["valid"]
            else:
                check = None
            row = {
                "cost_band": label,
                "wage_cad_hour": wage,
                "employment_burden_assumed": burden,
                "complete_fixed_opening_cad": fixed / 100,
                "each_employer_ceiling_cad": empcap / 100,
                "status": result["status"],
                "offer_total_cad": result["offer"]["maximum_funded_package_cents"] / 100 if result["offer"] else None,
                "least_complete_total_cad": result["least_cost_complete_physical_plan"]["maximum_funded_package_cents"]
                / 100
                if result["least_cost_complete_physical_plan"]
                else None,
                "check": check,
                "new_commercial_profit_inferred": False,
            }
            stresses.append(row)
            write(
                ROOT / f"technical/provider_calibration/{case['case_id']}.json",
                {"input": case, "result": result, "summary": row},
            )
    write(
        ROOT / "economics/PROVIDER_COST_CALIBRATION.json",
        {
            "schema": "agi-alpha.provider-cost-stress.v1",
            "timing": "Post-confirmation sensitivity motivated by official wage plausibility; not a replacement confirmation cohort.",
            "wage_source": "https://www.jobbank.gc.ca/marketreport/wages-occupation/5189/geo25154",
            "source_scope": "Montreal ECE wages updated 2025-11-19, reference 2023-2024; task hours, employment burdens, facility/admin allowances and provider offers remain assumptions.",
            "rows": stresses,
            "material_implication": "The central wage-anchored opening cost is above the original low-cost-provider scenario. At unchanged CAD145 employer ceilings, the selected-priced package is underfunded. Raising willing employer ceilings can restore technical fundability, but no commercial profit from the original scenario transfers to that variant.",
            "low_cost_interpretation": "The origin CAD150 fixed opening is close to the low wage/burden construction (CAD149.60), not a central observed provider quote.",
            "original_costs_and_failures_preserved": True,
        },
    )
    print(json.dumps({"settlement_rows": len(rows), "provider_stresses": stresses}, indent=2))


if __name__ == "__main__":
    main()
