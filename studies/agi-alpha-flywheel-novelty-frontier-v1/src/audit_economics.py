# SPDX-License-Identifier: Apache-2.0
"""Portable, independent Decimal audit of frozen economics outputs.

Run from the study directory:
  python src/audit_economics.py --output /tmp/economics-audit-replay.json

This persisted implementation reconstructs the documented checks in the earlier
inline audit. The original inline command was not retained; this is not a claim
of byte-identical recovery. It does not import or execute economics.py, modify
the frozen study, retune a policy, or establish validity of economic assumptions.
The output is created exclusively and an existing output is never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZERO = Decimal(0)
ONE = Decimal(1)
TOLERANCE = Decimal("0.000001")


def read(path: Path):
    return json.loads(path.read_text(), parse_float=Decimal)


def dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Checks:
    def __init__(self):
        self.count = 0
        self.maximum = ZERO

    def equal(self, actual, expected, name):
        error = abs(dec(actual) - dec(expected))
        self.count += 1
        self.maximum = max(self.maximum, error)
        if error > TOLERANCE:
            raise AssertionError(f"{name}: error {error} exceeds {TOLERANCE}")


def cash_replay(row, cfg, amendment):
    """Rebuild the aggregate monthly cash schedule using Decimal arithmetic."""
    periods = cfg["months"]
    revenue = dec(row["gross_recognized_revenue"])
    production = dec(row["production_cost"])
    acquisition = dec(row["acquisition"])
    overhead = dec(row["overhead"])
    warranty = dec(row["warranty_expense"])
    reserve = dec(row["warranty_cash_reserve"])
    deposit = Decimal("0.2") if row["payment_policy"] == "deposit20_discount5" else ZERO
    credit_loss = dec(cfg["credit_loss_fraction"])
    paid_now = dec(amendment["warranty_payment_fraction_during_delivery"])
    monthly_rate = dec(cfg["finance_annual_rate"]) / 12
    cash = debt = interest = peak = ZERO
    for index in range(periods + 1):
        charge = debt * monthly_rate
        interest += charge
        cash -= charge
        # The previous production month's non-deposit invoice is collected.
        if index > 0:
            cash += revenue / periods * (ONE - deposit) * (ONE - credit_loss)
        if index < periods:
            cash += revenue / periods * deposit
            cash -= (production + overhead + warranty * paid_now) / periods
            if index == 0:
                cash -= acquisition
            restricted = reserve * (index + 1) / periods
            liability = warranty * (ONE - paid_now) * (index + 1) / periods
        else:
            cash -= warranty * (ONE - paid_now)
            restricted, liability = reserve, ZERO
        free = cash - restricted - liability
        if free < ZERO:
            debt -= free
            cash -= free
        else:
            repayment = min(debt, free)
            debt -= repayment
            cash -= repayment
        peak = max(peak, debt)
    return {"cash_after_runoff": cash, "credit_debt_after_runoff": debt,
            "finance_expense": interest, "peak_revolving_credit": peak,
            "available_after_reserve_and_debt": cash - reserve - debt}


def audit(study_root: Path, results_dir: Path) -> dict:
    cfg_path = study_root / "config/economics.json"
    amendment_path = study_root / "results/economics-amendment-v1.json"
    source_path = study_root / "src/economics.py"
    cfg, amendment = read(cfg_path), read(amendment_path)
    result = read(results_dir / "economics-results.json")
    worlds_path = results_dir / "economics-worlds.json"
    worlds = read(worlds_path)["worlds"]
    freeze = read(results_dir / "economics-policy-freeze.json")
    prior_path = results_dir / "economics-independent-audit.json"
    prior = read(prior_path) if prior_path.exists() else None
    partial_path = results_dir / "economics-worlds-failed-write.json"
    hashes = {"config": sha(cfg_path), "amendment": sha(amendment_path), "source": sha(source_path)}
    assert hashes == freeze["hashes"] == result["hashes"], "Frozen inputs changed"
    assert freeze == result["freeze"], "Reported freeze differs from saved freeze"
    assert set(worlds) == set(cfg["scenario"]) == set(result["results"]), "Missing scenario"
    assert sum(dec(v) for v in cfg["cost_components"].values()) == ONE
    core, extra = Checks(), Checks()
    total_worlds = 0
    physical_hours_unchanged = True
    summary = {}
    with localcontext() as context:
        context.prec = 50
        for scenario, rows in worlds.items():
            assert len(rows) == cfg["confirmation_worlds"]
            assert [r["world_id"] for r in rows] == list(range(cfg["confirmation_worlds"]))
            total_worlds += len(rows)
            s = cfg["scenario"][scenario]
            reported = result["results"][scenario]
            selected = freeze["selected"][scenario]
            profits = []
            for r in rows:
                prefix = f"{scenario}/{r['world_id']}"
                revenue, profit = dec(r["gross_recognized_revenue"]), dec(r["qualified_annual_operating_profit"])
                expenses = sum(dec(r[k]) for k in ("production_cost", "acquisition", "overhead", "warranty_expense", "credit_loss", "finance_expense"))
                core.equal(revenue, dec(r["effective_price"]) * r["units"], prefix + "/sales")
                core.equal(profit, revenue - expenses, prefix + "/profit")
                core.equal(dec(r["cash_after_runoff"]) - dec(r["credit_debt_after_runoff"]), profit, prefix + "/cash-net-debt")
                for component, fraction in cfg["cost_components"].items():
                    core.equal(r["cost_components"][component], dec(r["production_cost"]) * dec(fraction), prefix + "/" + component)
                core.equal(r["warranty_expense"], revenue * dec(amendment["expected_warranty_expense_fraction_of_sales"]), prefix + "/warranty-expense")
                core.equal(r["warranty_cash_reserve"], revenue * dec(cfg["warranty_reserve_fraction_of_sales"]), prefix + "/warranty-reserve")
                core.equal(dec(r["collections"]) + dec(r["credit_loss"]), revenue, prefix + "/collections")
                assert 0 <= r["units"] <= cfg["annual_capacity"], prefix + "/capacity"
                assert dec(r["customer_surplus_after_outside_option_price_and_prepayment"]) >= -TOLERANCE
                assert r["payment_policy"] == selected["policy"] and r["listed_price"] == selected["price"]
                assert isinstance(r["physically_qualified_sample"], bool)
                extra.equal(sum(dec(v) for v in r["cost_components"].values()), r["production_cost"], prefix + "/components-total")
                deposit = Decimal("0.2") if r["payment_policy"] == "deposit20_discount5" else ZERO
                extra.equal(r["effective_price"], dec(r["listed_price"]) * (Decimal("0.95") if deposit else ONE), prefix + "/policy-price")
                extra.equal(r["credit_loss"], revenue * (ONE - deposit) * dec(cfg["credit_loss_fraction"]), prefix + "/credit-loss")
                for key, expected in cash_replay(r, cfg, amendment).items():
                    extra.equal(r[key], expected, prefix + "/replayed-" + key)
                profits.append(profit)
            mean_profit = sum(profits) / len(profits)
            extra.equal(reported["conditional_qualified_operation"]["qualified_annual_operating_profit"]["mean"], mean_profit, scenario + "/mean-profit")
            assert reported["all_active_worlds_retained"] == len(rows)
            assert reported["sampled_physical_failures"] == sum(not r["physically_qualified_sample"] for r in rows)
            for path in reported["research_pathways"]:
                rd = path["rd"]
                band = rd["band"]
                reduction = rd["engineering_hour_reduction_assumed"]
                hours = dec(cfg["human_engineering_hours"][band]) * (ONE - dec(reduction or 0))
                wage = dec(cfg["wage_cad_hour"][band]) * dec(cfg["loaded_multiplier"][band]) / dec(cfg["fx_cad_per_usd"])
                engineering = hours * wage
                physical = dec(cfg["physical_test_hours"][band]) * dec(cfg["technician_usd_hour"][band])
                external = dec(cfg["prototype_tooling_external_tests_usd"][band])
                inference_cfg = cfg["inference_plan"]
                inference = ZERO if reduction is None else sum((dec(inference_cfg["input_mtokens"]) * dec(inference_cfg["input_usd_per_mtoken"]), dec(inference_cfg["output_mtokens"]) * dec(inference_cfg["output_usd_per_mtoken"]), dec(inference_cfg["tool_compute_usd"])))
                direct = engineering + physical + external + inference
                finance = direct * dec(cfg["finance_annual_rate"]) * dec(amendment["development_months"][band]) / 24
                originating = direct + finance
                label = scenario + "/" + path["configuration"] + "/" + band
                core.equal(rd["A_originating_research_total"], originating, label + "/A")
                core.equal(path["expected_predevelopment_profit"], dec(s["qualified_device_probability"]) * mean_profit - originating, label + "/expected-project")
                for key, value in {"engineering_hours": hours, "loaded_engineer_usd_hour": wage, "engineering_cost": engineering, "physical_test_cost": physical, "external_prototype_tooling_tests": external, "inference_tools": inference, "research_finance": finance}.items():
                    extra.equal(rd[key], value, label + "/" + key)
                physical_hours_unchanged &= rd["physical_test_hours"] == cfg["physical_test_hours"][band]
                assert not rd["paid_customer_learning"]
            summary[scenario] = {"worlds": len(rows), "qualified_operating_profit_mean": float(mean_profit), "physical_failure_samples": reported["sampled_physical_failures"], "actual_decision": result["actual_decision"]}
    assert physical_hours_unchanged
    actual = result["actual"]
    assert actual == cfg["actual"]
    assert all(actual[k] == 0 for k in ("buyers", "deliveries", "recognized_revenue", "collections", "token_receipts"))
    assert actual["physical_qualification"] is False and actual["attributable_full_session_cost"] is None
    partial_matches = worlds_path.read_bytes().startswith(partial_path.read_bytes()) if partial_path.exists() else None
    assert partial_matches is not False
    comparison = None
    if prior:
        comparison = {
            "passed_matches": prior["passed"] is True,
            "core_numeric_check_count_matches": core.count == prior["checks"],
            "world_count_matches": total_worlds == prior["worlds"],
            "max_abs_error_usd_matches": core.maximum == dec(prior["max_abs_error_usd"]),
            "full_worlds_hash_matches": sha(worlds_path) == prior["full_worlds_sha256"],
            "partial_hash_matches": sha(partial_path) == prior["original_partial_sha256"] if partial_path.exists() else None,
            "same_physical_work_result": physical_hours_unchanged == prior["physical_test_hours_unchanged_in_every_E_sensitivity"],
        }
        # A reconstructed numerical path need not have an identical rounding
        # residual. Preserve that difference instead of forcing a false match.
        exact_rounding_match = comparison.pop("max_abs_error_usd_matches")
        assert all(value is not False for value in comparison.values()), f"Persisted reconstruction differs from original key audit outcomes: {comparison}"
        comparison["max_abs_error_usd_matches_exactly"] = exact_rounding_match
        comparison["both_max_errors_below_original_tolerance"] = core.maximum < TOLERANCE and dec(prior["max_abs_error_usd"]) < TOLERANCE
        comparison["max_abs_error_usd_difference"] = float(core.maximum - dec(prior["max_abs_error_usd"]))
    return {
        "schema": "agi-alpha.economics.independent-arithmetic-audit.v2",
        "method": "Persisted reconstruction of documented original inline Decimal checks, plus independent monthly cash replay; same team, not external replication",
        "source_provenance": "Original inline command text was not persisted. This implementation is reconstructed and is not asserted byte-identical to that command.",
        "passed": True, "checks": core.count, "additional_numeric_checks": extra.count,
        "worlds": total_worlds, "max_abs_error_usd": float(core.maximum),
        "additional_checks_max_abs_error_usd": float(extra.maximum), "tolerance_usd": float(TOLERANCE),
        "physical_test_hours_unchanged_in_every_E_sensitivity": physical_hours_unchanged,
        "sample_denominators_preserved": True,
        "failed_write_prefix_matches_unchanged_replay": partial_matches,
        "original_partial_sha256": sha(partial_path) if partial_path.exists() else None,
        "full_worlds_sha256": sha(worlds_path), "frozen_input_hashes": hashes,
        "audit_source_sha256": sha(Path(__file__)),
        "original_report_sha256": sha(prior_path) if prior else None,
        "comparison_with_original_report": comparison,
        "warranty_expense_and_cash_reserve_checked_separately": True,
        "actual_collections": actual["collections"], "actual_full_cost_known": False,
        "scenario_summary": summary,
        "evidence_boundary": "Arithmetic agreement checks implementation consistency. It does not calibrate qualification q, buyer demand, physical feasibility, cost completeness, or within-month cash timing."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=ROOT)
    parser.add_argument("--results-dir", type=Path, help="Defaults to STUDY_ROOT/results")
    parser.add_argument("--output", type=Path, required=True, help="New report path; must not already exist")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("--output already exists; choose a new path to preserve the original report")
    report = audit(args.study_root, args.results_dir or args.study_root / "results")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "passed": report["passed"], "core_checks": report["checks"], "additional_checks": report["additional_numeric_checks"], "comparison_with_original_report": report["comparison_with_original_report"]}, indent=2))


if __name__ == "__main__":
    main()
