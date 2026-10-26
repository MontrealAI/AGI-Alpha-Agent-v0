"""Stream and reconcile preserved market artifacts without executing the model."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
ECON = ROOT / "economics"
RESULTS = ECON / "results-primary"
OUT = ROOT / "audit-final"
OPENING_RD = "upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing"
ARMS = "ABCD"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-7)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def cents(x):
    return max(0, math.floor(x + 0.5))


def distribution(values):
    a = sorted(values)
    n = len(a)
    mean = sum(a) / n
    se = math.sqrt(sum((x - mean) ** 2 for x in a) / max(1, n - 1) / n)
    def q(p):
        i = (n - 1) * p
        j = math.floor(i)
        return a[j] + (a[min(j + 1, n - 1)] - a[j]) * (i - j)
    return {"n": n, "mean": mean, "min": a[0], "p05": q(.05), "median": q(.5), "p95": q(.95), "max": a[-1],
            "negative": sum(x < 0 for x in a), "zero": sum(x == 0 for x in a), "positive": sum(x > 0 for x in a),
            "conditional_monte_carlo_mean_interval": [mean - 1.96 * se, mean + 1.96 * se]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUT,
                        help="Directory for the new audit receipt (default: audit-final/).")
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    begin = time.perf_counter()
    checks, failures, issues = Counter(), Counter(), []
    def check(ok, code, context=None):
        checks[code] += 1
        if not ok:
            failures[code] += 1
            if len(issues) < 100:
                issues.append({"code": code, "context": context})
    protocol = read(ECON / "market-protocol.json")
    freeze = read(ECON / "market-freeze.json")
    completion = read(RESULTS / "completion.json")
    calibration = read(ECON / "calibration.json")
    def freeze_check(code):
        for entry in freeze["files"]:
            p = ECON / entry["path"]
            check(p.exists() and p.stat().st_size == entry["bytes"] and sha(p) == entry["sha256"], code, entry["path"])
    freeze_check("market_frozen_source_identity")
    check(len(freeze["files"]) == 17, "seventeen_frozen_sources")
    for name, field in (("calibration.json", "calibration_sha256"), ("market-protocol.json", "protocol_sha256"), ("market-freeze.json", "source_freeze_sha256")):
        check(sha(ECON / name) == completion[field], "completion_binds_frozen_inputs", name)
    check(completion["status"] == "COMPLETE" and completion["actual_customer_collections_cents"] == 0, "complete_and_actual_revenue_zero")
    check(completion["wall_seconds"] <= protocol["limits"]["wall_seconds"] and completion["cpu_seconds"] <= protocol["limits"]["cpu_seconds"], "frozen_campaign_resource_envelope")
    check(freeze["market_outcomes_inspected"] is False and protocol["market_outcomes_inspected"] is False, "prospective_market_freeze_labels")
    conditions = {c["id"]: c for c in protocol["conditions"]}
    schedules = {s["id"]: s for s in protocol["schedules"]}
    families = {f["id"]: f for f in calibration["families"]}
    trials = {(f["id"], t["task_id"]): t for f in calibration["families"] for t in f["trials"]}
    for f in calibration["families"]:
        for trial in f["trials"]:
            check(trial["before"] == {"accepted": None, "cpu_seconds": None, "basis": "NOT_RUN"}, "raw_prior_remains_unknown", trial["task_id"])
            for arm, row in trial["methods"].items():
                receipt = row["record_source"]
                check(sha(ROOT / receipt["path"]) == receipt["sha256"], "calibration_execution_receipt_hash", trial["task_id"] + arm)
                actual = read(ROOT / receipt["path"])
                check(all(equal(row[k], actual[k]) for k in ("accepted", "cpu_seconds", "elapsed_seconds", "exit_code", "task_sha256", "result_sha256")), "calibration_retains_complete_arm_outcomes", trial["task_id"] + arm)
    for item in calibration["resource_allocation"]:
        check(equal(sum(f["resources"]["by_arm"][item["arm"]][item["category"]]["seconds"] for f in families.values()), item["total_seconds"]), "constructor_interval_allocated_once", item["arm"] + item["category"])
    check(calibration["actual_total_cost_cents"] is None and calibration["actual_customer_collections_cents"] == 0, "calibration_actual_cost_unknown")

    compact_rows = read(RESULTS / "compact-worlds.json")
    key = lambda row: (row["condition_id"], row.get("schedule_id", row.get("cost_schedule")), row["seed"])
    compact = {key(r): r for r in compact_rows}
    required = {(condition, schedule, seed) for condition in conditions for schedule in schedules for seed in protocol["seeds"]}
    check(len(compact_rows) == len(compact) == len(required) == 2304 and set(compact) == required, "compact_full_predeclared_census")
    summary = read(RESULTS / "summary.json")
    groups = {(r["condition_id"], r["schedule_id"]): r for r in summary["conditions"]}
    check(len(groups) == len(summary["conditions"]) == 144, "all_144_cell_summaries")
    check(summary["unknown_actual_cost_boundary"]["actual_total_cost_cents"] is None and summary["unknown_actual_cost_boundary"]["affirmative_investment"] is False, "no_unknown_cost_success_promotion")
    stats = Counter()
    extrema = {"minimum_cash_cents": math.inf, "minimum_generated_available_cents": math.inf, "maximum_unpaid_obligations_cents": 0}
    bundle_rows = []
    adverse_examples = {}
    seen = set()
    finance_controls = 0

    def build_categories(family_id, arm, condition, schedule):
        r = families[family_id]["resources"]["by_arm"][arm]
        retrieval = 0
        if family_id == "G1" and arm in "BC":
            retrieval = calibration["retrieval"]["registry_build" if arm == "B" else "graph_build"]["seconds"]
        rate = schedule["resource_hourly_cents"]
        return {"discovery": cents(schedule["discovery_minutes_per_build"] * rate / 60),
                "construction": cents((r["construction"]["seconds"] * condition["reconstruction_factor"] + retrieval) * rate / 3600),
                "failedCandidates": cents(r["failedCandidates"]["seconds"] * rate / 3600),
                "validation": cents(r["validation"]["seconds"] * rate / 3600),
                "integration": cents(r["integration"]["seconds"] * rate / 3600),
                "modelAndTools": schedule["model_tools_cents_per_build"],
                "residualAttention": cents(schedule["audit_minutes_per_build"] * schedule["attention_hourly_cents"] / 60),
                "maintenance": 0, "revalidation": 0}

    def audit_run(run, label, arm, condition, schedule, control=False):
        h, s = run["histories"], run["summary"]
        bills, invoices, events, jobs = h["bills"], h["invoices"], h["cash"], h["jobs"]
        bill_map, invoice_map = {b["id"]: b for b in bills}, {i["id"]: i for i in invoices}
        job_map = {j["id"]: j for j in jobs}
        check(len(bill_map) == len(bills) and len(invoice_map) == len(invoices) and len(job_map) == len(jobs), "ledger_unique_ids", label)
        cash = protocol["original_seed_cents"]
        collected = 0
        paid = 0
        cash_by_week, collection_by_week, accrued_by_week, paid_by_week, pending_by_week = (defaultdict(int) for _ in range(5))
        event_refs = Counter()
        first_collection = next((i for i, e in enumerate(events) if e["type"] == "simulated_collection"), len(events))
        for index, e in enumerate(events):
            amount = e["amountCents"]
            check(isinstance(amount, int) and abs(amount) < 2**53, "finite_integer_cash_event", label)
            cash += amount
            cash_by_week[e["week"]] += amount
            event_refs[e["reference"]] += 1
            check(cash == e["cashAfterCents"] and cash >= 0, "cash_event_running_balance_nonnegative", label)
            if e["type"] == "simulated_collection":
                collected += amount
                collection_by_week[e["week"]] += amount
                invoice = invoice_map.get(e["reference"], {})
                check(invoice.get("status") == "collected" and invoice.get("amountCents") == amount and invoice.get("collectedWeek") == e["week"], "collection_has_exact_invoice", label)
            else:
                paid -= amount
                b = bill_map.get(e["reference"], {})
                check(e["type"] in ("expense_payment", "refund") and b.get("paid") is True and b.get("amountCents") == -amount and b.get("paidWeek") == e["week"], "expense_has_exact_paid_bill", label)
        check(all(v == 1 for v in event_refs.values()), "no_duplicate_cash_transfers", label)
        opening_paid = 0
        job_bills = defaultdict(int)
        for b in bills:
            check(isinstance(b["amountCents"], int) and b["amountCents"] > 0, "positive_finite_bill", label)
            accrued_by_week[b["week"]] += b["amountCents"]
            if b["paid"]:
                paid_by_week[b["paidWeek"]] += b["amountCents"]
                check(event_refs[b["id"]] == 1, "paid_bill_has_one_cash_event", label)
            else:
                check(event_refs[b["id"]] == 0, "unpaid_bill_creates_no_cash_payment", label)
            if b["reference"] == OPENING_RD and b["week"] == 0 and b.get("paidWeek") == 0:
                matching = [i for i, e in enumerate(events) if e["reference"] == b["id"] and e["type"] == "expense_payment"]
                if matching and matching[0] < first_collection:
                    opening_paid += b["amountCents"]
            ref = b["reference"].split(":")[0]
            if ref in job_map:
                job_bills[ref] += b["amountCents"]
        check(opening_paid <= protocol["original_seed_cents"], "opening_history_paid_from_finite_seed", label)
        check(paid == sum(b["amountCents"] for b in bills if b["paid"]), "paid_costs_reconcile", label)
        for invoice in invoices:
            j = job_map.get(invoice["mission"], {})
            check(j.get("accepted") is True and j.get("week") == invoice["week"] and invoice["amountCents"] == condition["posted_price_cents"], "only_accepted_work_is_invoiced", label)
            check(invoice["dueWeek"] == invoice["week"] + condition["payment_delay_weeks"], "declared_receipt_delay", label)
            pending_by_week[invoice["week"]] += invoice["amountCents"]
            if invoice["status"] in ("collected", "defaulted"):
                pending_by_week[invoice.get("collectedWeek", invoice["dueWeek"])] -= invoice["amountCents"]
            check(invoice["status"] in ("collected", "defaulted", "pending"), "invoice_status_valid", label)
            check(event_refs[invoice["id"]] == (1 if invoice["status"] == "collected" else 0), "uncollected_invoice_is_not_cash", label)
        accrued = sum(b["amountCents"] for b in bills)
        unpaid = accrued - paid
        receivable = sum(i["amountCents"] for i in invoices if i["status"] == "pending")
        check(s["cash_cents"] == cash and s["collected_cents"] == collected and s["accrued_costs_cents"] == accrued, "summary_cash_receipts_and_costs", label)
        check(s["profit_cents"] == collected + receivable - accrued == cash + receivable - unpaid - protocol["original_seed_cents"], "economic_profit_complete_obligations", label)
        check(s["attempts"] == len(jobs) and s["accepted"] == sum(j["accepted"] for j in jobs) and s["rejected"] == sum(not j["accepted"] for j in jobs), "accepted_failed_job_census", label)
        check(len(invoices) == s["accepted"], "one_invoice_per_accepted_job", label)
        current_cash, current_collected, current_accrued, current_paid, current_pending = protocol["original_seed_cents"], 0, 0, 0, 0
        check([b["week"] for b in h["balances"]] == list(range(52 + condition["payment_delay_weeks"] + 3)), "complete_balance_horizon", label)
        for balance in h["balances"]:
            w = balance["week"]
            current_cash += cash_by_week[w]
            current_collected += collection_by_week[w]
            current_accrued += accrued_by_week[w]
            current_paid += paid_by_week[w]
            current_pending += pending_by_week[w]
            obligations = current_accrued - current_paid
            cb = current_cash - obligations - protocol["reserve_cents"]
            gb = current_collected - current_accrued + opening_paid
            expected_funds = {"availableCents": max(0, min(cb, gb)), "cashCents": current_cash, "unpaidObligationsCents": obligations,
                              "reserveCents": protocol["reserve_cents"], "collectedCents": current_collected, "allAccruedCostsCents": current_accrued,
                              "seedPaidOpeningHistoryCents": opening_paid, "cashBoundCents": cb, "generatedBoundCents": gb}
            check(balance["generated"] == expected_funds and balance["cash_cents"] == current_cash and balance["obligations_cents"] == obligations and balance["receivables_cents"] == current_pending and balance["accrued_costs_cents"] == current_accrued, "weekly_cash_obligation_reserve_and_generated_funds", label)
            extrema["minimum_cash_cents"] = min(extrema["minimum_cash_cents"], current_cash)
            extrema["minimum_generated_available_cents"] = min(extrema["minimum_generated_available_cents"], expected_funds["availableCents"])
            extrema["maximum_unpaid_obligations_cents"] = max(extrema["maximum_unpaid_obligations_cents"], obligations)
        check(s["generated_available_cents"] == h["balances"][-1]["generated"]["availableCents"], "terminal_generated_funds", label)
        for view in ("cash", "economic"):
            canonical = run["canonical"][view]
            check(canonical["summary"]["observed"]["revenue"] == 0 and canonical["summary"]["observed"]["fullCost"] is None, "canonical_actual_unknown_and_no_simulated_revenue", label)
            check(all(e.get("basis") != "observed" or e.get("amountMinor") == 0 for e in canonical["ledger"]["events"]), "no_positive_observed_ledger_event", label)
        econ = run["canonical"]["economic"]["summary"]["scenario"]
        liquidity = run["canonical"]["cash"]["summary"]["scenario"]
        check(econ["fullCost"] == accrued and econ["operatingMargin"] == s["profit_cents"] and econ["revenue"] == collected + receivable, "canonical_accrual_projection", label)
        check(liquidity["fullCost"] == paid and liquidity["revenue"] == collected and liquidity["unpaidObligations"] == unpaid and liquidity["reserve"] == protocol["reserve_cents"] and liquidity["afterReserves"] == cash - protocol["original_seed_cents"] - unpaid - protocol["reserve_cents"], "canonical_cash_projection", label)

        by_week_constructed = defaultdict(int)
        constructed = []
        for d in h["decisions"]:
            w = d["week"]
            pre_bills = [b for b in bills if b["week"] < w or (b["week"] == w and (b["category"] in ("business", "maintenance") or b["reference"] == OPENING_RD))]
            pre_accrued = sum(b["amountCents"] for b in pre_bills) + by_week_constructed[w]
            pre_paid = sum(b["amountCents"] for b in pre_bills if b["paid"] and b["paidWeek"] <= w) + by_week_constructed[w]
            pre_collected = sum(amount for week, amount in collection_by_week.items() if week <= w)
            pre_cash = protocol["original_seed_cents"] + pre_collected - pre_paid
            pre_unpaid = pre_accrued - pre_paid
            cb = pre_cash - pre_unpaid - protocol["reserve_cents"]
            gb = pre_collected - pre_accrued + opening_paid
            funds = {"availableCents": max(0, min(cb, gb)), "cashCents": pre_cash, "unpaidObligationsCents": pre_unpaid,
                     "reserveCents": protocol["reserve_cents"], "collectedCents": pre_collected, "allAccruedCostsCents": pre_accrued,
                     "seedPaidOpeningHistoryCents": opening_paid, "cashBoundCents": cb, "generatedBoundCents": gb}
            check(d["generated_resources"] == funds, "decision_funds_from_prior_and_current_collected_ledger", label + ":" + d["family"])
            expected_available = max(0, cb) if d["family"] == "G1" else funds["availableCents"]
            check(d["available_cents"] == expected_available, "seed_and_operating_generated_sources_separate", label)
            categories = build_categories(d["family"], arm, condition, schedule)
            check(d["fixed_cost"]["categories"] == categories and d["fixed_cost"]["total_cents"] == sum(categories.values()), "complete_construction_category_costs", label)
            horizon = min(condition["useful_life_weeks"], 52 - w - 1)
            recent = sum(o["family"] == d["family"] and max(0, w - 8) <= o["week"] < w for o in h["buyerChoices"])
            forecast = math.floor(recent / max(1, min(8, w)) * horizon * .5)
            check(d["forecast_uses"] == forecast, "investment_forecast_uses_only_prior_opportunities", label)
            should_build = d["forecast_net_cents"] > 0 and expected_available >= d["fixed_cost"]["total_cents"] and d["contribution_policy"]["willing_to_contribute"]
            check((d["action"] == "construct") == should_build, "construction_admission_gate_exact", label)
            if d["action"] == "construct":
                constructed.append(d)
                cost = d["fixed_cost"]["total_cents"]
                check(pre_cash - cost - pre_unpaid >= protocol["reserve_cents"] and expected_available >= cost, "construction_preserves_obligations_and_one_reserve", label)
                check(d["funding"] == ("seed" if d["family"] == "G1" else "operating-generated"), "later_capability_funding_label", label)
                by_week_constructed[w] += cost
        check(len({d["family"] for d in constructed}) == len(constructed), "shared_construction_charged_once_per_asset", label)
        if control:
            check(all(d["family"] == "G1" for d in constructed), "no_later_asset_in_finance_control", label)
        n_proto = ["G1"] if control else ["G1", "G2", "G3"]
        prototype_total = sum(sum(build_categories(f, arm, condition, schedule).values()) for f in n_proto)
        financed = sum(d["fixed_cost"]["total_cents"] for d in constructed)
        check(s["completed_prototype_cost_cents"] == prototype_total and s["enterprise_financed_prototype_cost_cents"] == financed and s["outside_enterprise_prototype_cost_cents"] == prototype_total - financed, "all_completed_prototypes_accounted_once", label)
        check(s["project_inclusive_profit_cents"] == s["profit_cents"] - (prototype_total - financed), "full_project_cost_includes_outside_prototypes", label)
        check(s["prospective_deployment_profit_cents"] == s["profit_cents"] + schedule["historical_research_cents"], "prospective_and_historical_profit_distinguished", label)
        if not control:
            check(len(run["completed_prototype_costs"]) == 3, "three_executed_prototypes_kept_in_history", label)
            for p in run["completed_prototype_costs"]:
                expected = build_categories(p["family"], arm, condition, schedule)
                check(p["categories"] == expected and p["total_cents"] == sum(expected.values()), "prototype_cost_record_matches_frozen_calibration", label)
        cumulative_compute = 0.0
        charged_compute = 0
        reconstruction_charges = set()
        acquired = set()
        attention = cents(schedule["residual_minutes_per_job"] * schedule["attention_hourly_cents"] / 60)
        for j in jobs:
            t = trials[(j["family"], j["trial_id"])]
            method = t["methods"][j["method"]]
            raw = method["cpu_seconds"] * schedule["compute_hourly_cents"] / 3600
            cumulative_compute += raw
            charge = math.ceil(cumulative_compute) - charged_compute
            charged_compute += charge
            check(equal(j["compute_unrounded_cents"], raw) and j["compute_charged_cents"] == charge, "fractional_compute_carried_once", label)
            check(j["accepted"] == (method["accepted"] and not j["stale"] and not j["acquisition_failed"]), "delivery_failure_cost_and_acceptance_retained", label)
            check(j["simulated_price_cents"] == (condition["posted_price_cents"] if j["accepted"] else 0), "rejected_job_no_revenue", label)
            fixed = j["cost_cents"] - charge - attention
            identifier = (j["recipient"], j["family"])
            if j["route"].endswith("reconstruction"):
                method_arm = "A" if j["route"] == "independent-reconstruction" else "D"
                full = sum(build_categories(j["family"], method_arm, condition, schedule).values())
                check(fixed in (0, full), "independent_construction_uses_complete_cost", label)
                if fixed:
                    rk = identifier + (method_arm,)
                    check(rk not in reconstruction_charges, "independent_reconstruction_retained_after_first_charge", label)
                    reconstruction_charges.add(rk)
            elif j["route"] in ("validated-acquisition", "conventional-service"):
                check(fixed == (0 if identifier in acquired else condition["integration_cents"]), "acquisition_charged_until_retained_success", label)
                if j["accepted"]:
                    acquired.add(identifier)
                if not j["accepted"]:
                    check(j["actual_asset_value_cents"] == -j["cost_cents"], "failed_shared_work_debits_full_asset_value", label)
            check(j["cost_cents"] == job_bills[j["id"]] and fixed >= 0, "complete_job_cost_matches_all_bills", label)
        residual = sum(j["compute_unrounded_cents"] - j["compute_charged_cents"] for j in jobs)
        check(charged_compute == math.ceil(cumulative_compute) and -1 < residual <= 1e-10 and equal(s["subcent_compute_rounding_residual_cents"], residual), "aggregate_compute_rounding_bound", label)
        check(equal(s["project_inclusive_unrounded_compute_profit_cents"], s["project_inclusive_profit_cents"] - residual), "unrounded_project_profit_reconciles", label)
        for transfer in h["transfers"]:
            j = job_map[transfer["id"]]
            independent = transfer["best_independent_cost_cents"]
            net = (independent if transfer["accepted"] and independent is not None else 0) - j["cost_cents"]
            check(equal(j["actual_asset_value_cents"], net) and equal(transfer["recipient_net_cents"], None if independent is None else net), "transfer_complete_outcome_net_value", label)
            check(transfer["global_unsupported_capability_claim"] is False and transfer["all_observed_alternatives_failed"] is False, "successful_reconstruction_prevents_unsupported_claim", label)
        check(s["useful_transfers"] == sum(t["accepted"] and ((t["recipient_net_cents"] or 0) > 0 or t["all_observed_alternatives_failed"]) for t in h["transfers"]), "useful_transfer_census", label)
        check(all(t["internal_transfer_net_enterprise_value_cents"] == 0 for t in h["contributionAllocations"]), "internal_rewards_do_not_create_enterprise_value", label)
        if not control:
            check(run["actual_collections_cents"] == 0 and run["actual_full_cost_cents"] is None and run["actual_full_history_return_cents"] is None and s["actually_executed_network_agents"] == 0, "simulated_economy_not_actual_commerce", label)
            check(set(run["assets"]) == {d["family"] for d in constructed}, "constructed_asset_census", label)
            for family, asset in run["assets"].items():
                used = [j for j in jobs if j["family"] == family and j["route"] in ("validated-acquisition", "conventional-service")]
                upkeep = sum(b["amountCents"] for b in bills if b["category"] == "maintenance" and b["reference"] == f"capability:{family}:maintenance/revalidation")
                check(asset["uses"] == len(used) and equal(asset["avoided"], sum(j["actual_asset_value_cents"] for j in used)) and asset["upkeep"] == upkeep, "asset_value_includes_every_use_failure_and_upkeep", label + family)
                d = next(d for d in constructed if d["family"] == family)
                check(asset["cost"] == d["fixed_cost"]["total_cents"] and asset["funding"] == d["funding"] and asset["failed"] == d["failed"], "asset_cost_and_funding_match_paid_construction", label + family)
            stats[f"{arm}_loss_worlds"] += s["project_inclusive_profit_cents"] < 0
            stats[f"{arm}_zero_acceptance_worlds"] += s["accepted"] == 0
            stats[f"{arm}_insolvent_worlds"] += s["insolvency"]
            stats[f"{arm}_no_shared_asset_worlds"] += not run["assets"]
            stats[f"{arm}_failed_shared_jobs"] += sum(j["route"] == "validated-acquisition" and not j["accepted"] for j in jobs)
            if s["project_inclusive_profit_cents"] < 0:
                adverse_examples.setdefault("loss", {"world": label, "profit_cents": s["project_inclusive_profit_cents"]})
            if condition["demand_multiplier"] == 0:
                check(not jobs and not invoices and collected == 0 and s["project_inclusive_profit_cents"] < 0, "zero_demand_losses_preserved", label)
                stats["zero_demand_primary_histories"] += 1
                adverse_examples.setdefault("zero_demand", {"world": label, "profit_cents": s["project_inclusive_profit_cents"]})

    with gzip.open(RESULTS / "complete-worlds.jsonl.gz", "rt") as stream:
        for count, line in enumerate(stream, 1):
            world = json.loads(line)
            k = key(world)
            check(k in required and k not in seen, "complete_world_census_no_duplicates", str(k))
            seen.add(k)
            compact_row = compact[k]
            condition, schedule = conditions[k[0]], schedules[k[1]]
            check(world["actual_success_claim_allowed"] is False, "world_actual_success_not_claimed", str(k))
            check(equal(compact_row["arms"], {a: world["arms"][a]["summary"] for a in ARMS}) and equal(compact_row["differences"], world["differences"]) and equal(compact_row["succession"], world["succession"]), "compact_matches_complete_world_exactly", str(k))
            for arm in ARMS:
                run = world["arms"][arm]
                check(run["condition"] == condition and run["seed"] == k[2] and run["arm"] == arm and run["cost_schedule"] == k[1], "arm_world_identity", str(k) + arm)
                audit_run(run, str(k) + ":" + arm, arm, condition, schedule)
                check(compact_row["later_investment_counts"][arm] == sum(f != "G1" for f in run["assets"]), "compact_later_investment_count", str(k) + arm)
            for left, right in (("B", "A"), ("C", "B"), ("C", "D"), ("B", "D")):
                for suffix, field in (("cents", "profit_cents"), ("project_cents", "project_inclusive_profit_cents"), ("unrounded_compute_project_cents", "project_inclusive_unrounded_compute_profit_cents")):
                    expected = world["arms"][left]["summary"][field] - world["arms"][right]["summary"][field]
                    check(equal(world["differences"][f"{left}_minus_{right}_{suffix}"], expected), "paired_differences_reconcile", str(k))
            for arm in "BC":
                run, control, result = world["arms"][arm], world["finance_controls"][arm], world["succession"][arm]
                later = [p for p in run["completed_prototype_costs"] if p["family"] != "G1"]
                assets = {f: a for f, a in run["assets"].items() if f != "G1"}
                if assets:
                    finance_controls += 1
                    check(control["basis"] == "SAME_WORLD_COUNTERFACTUAL_NO_LATER_SHARED_CAPABILITY" and "histories" in control, "required_full_finance_control_retained", str(k) + arm)
                    audit_run(control, str(k) + ":" + arm + ":NO_LATER_CONTROL", arm, condition, schedule, control=True)
                    incremental = run["summary"]["project_inclusive_profit_cents"] - control["summary"]["project_inclusive_profit_cents"]
                    incremental_unrounded = run["summary"]["project_inclusive_unrounded_compute_profit_cents"] - control["summary"]["project_inclusive_unrounded_compute_profit_cents"]
                else:
                    check(control["basis"] == "NO_LATER_ADOPTION_IDENTICAL_OPERATIONS_PLUS_OUTSIDE_RESEARCH_COST" and control["operational_histories_identical"] is True, "no_adoption_control_keeps_outside_research_cost", str(k) + arm)
                    incremental = incremental_unrounded = -sum(p["total_cents"] for p in later)
                check(equal(control["incremental_project_profit_cents"], incremental) and equal(control["incremental_unrounded_compute_project_profit_cents"], incremental_unrounded) and equal(compact_row["finance_differences"][arm], incremental), "finance_control_complete_project_difference", str(k) + arm)
                complete_cost = sum(p["total_cents"] for p in later)
                paid = sum(a["cost"] for a in assets.values())
                financed = bool(later) and paid == complete_cost and all(run["assets"].get(p["family"], {}).get("funding") == "operating-generated" for p in later)
                direct = sum(a["avoided"] - a["upkeep"] for a in assets.values()) - complete_cost
                uses = sum(a["uses"] for a in assets.values())
                qualifies = financed and uses > 0 and direct >= 0 and all(not a["failed"] for a in assets.values()) and incremental > 0 and incremental_unrounded > 0
                expected = {"qualifies": qualifies, "all_bundle_prototype_costs_funded_from_operations": financed,
                            "full_bundle_cost_cents": complete_cost, "enterprise_paid_bundle_cost_cents": paid,
                            "direct_bundle_net_cents": direct, "actual_modeled_bundle_uses": uses, "incremental_project_profit_cents": incremental}
                check(all(equal(result[field], value) for field, value in expected.items()) and result["scope"] == "G2_G3_LATER_INVESTMENT_BUNDLE_ONLY" and result["individual_generation_qualification"] == "NOT_ESTABLISHED_BY_THIS_CONTROL", "exact_complete_bundle_success_gate", str(k) + arm)
                stats[f"{arm}_qualifying_bundle_worlds"] += qualifies
                stats[f"{arm}_later_investment_worlds"] += bool(assets)
                if assets:
                    bundle_rows.append({"condition": k[0], "schedule": k[1], "seed": k[2], "arm": arm, "later_assets": sorted(assets), **expected})
            for arm in "AD":
                check(world["succession"][arm]["qualifies"] is False and world["succession"][arm]["scope"] == "NOT_EVALUATED", "no_individual_or_uncontrolled_succession_claim", str(k) + arm)
            if count % 384 == 0:
                print(json.dumps({"worlds_reconciled": count, "failures": sum(failures.values()), "elapsed_seconds": time.perf_counter() - begin}), flush=True)
    check(seen == required and len(seen) == completion["worlds"] == 2304 and len(seen) * 4 == completion["primary_histories"] == 9216, "all_complete_worlds_and_histories_retained")
    check(finance_controls == completion["additional_same_world_finance_controls"] == 46, "all_46_additional_controls_retained")
    for (condition_id, schedule_id), reported in groups.items():
        rows = [compact[(condition_id, schedule_id, seed)] for seed in protocol["seeds"]]
        check(reported["condition"] == conditions[condition_id], "summary_condition_identity", condition_id)
        for metric in rows[0]["differences"]:
            check(equal(reported["differences"][metric], distribution([r["differences"][metric] for r in rows])), "all_paired_summary_statistics_recomputed", condition_id + schedule_id + metric)
        for arm in ARMS:
            for metric, field in (("profit", "profit_cents"), ("project_profit", "project_inclusive_profit_cents"), ("accepted", "accepted"), ("collections", "collected_cents"), ("transfers", "useful_transfers")):
                check(equal(reported["arms"][arm][metric], distribution([r["arms"][arm][field] for r in rows])), "all_arm_summary_statistics_recomputed", condition_id + schedule_id + arm + metric)
            check(reported["arms"][arm]["funded_later_capabilities"] == sum(r["later_investment_counts"][arm] for r in rows) and reported["arms"][arm]["qualifying_later_bundle_worlds"] == sum(r["succession"][arm]["qualifies"] for r in rows), "summary_financing_counts_recomputed", condition_id + schedule_id + arm)
    with (RESULTS / "paired-results.csv").open() as stream:
        csv_rows = list(csv.DictReader(stream))
    check(len(csv_rows) == 2304, "paired_csv_complete")
    for row in csv_rows:
        c = compact[(row["condition_id"], row["schedule_id"], int(row["seed"]))]
        check(all(equal(float(value), c["differences"][field]) for field, value in row.items() if field not in ("condition_id", "schedule_id", "seed")), "paired_csv_matches_frozen_world", row["condition_id"])
    freeze_check("market_frozen_source_identity_after_audit")
    report = {"schema": "capability-advantage-independent-market-output-audit/v1", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "PASS" if not failures else "DEFECTS_FOUND", "failure_counts": dict(failures), "first_issues": issues,
              "total_checks": sum(checks.values()), "checks": dict(checks), "worlds": len(seen), "primary_histories": len(seen) * 4,
              "additional_finance_controls": finance_controls, "source_freeze_sha256": sha(ECON / "market-freeze.json"),
              "completion_sha256": sha(RESULTS / "completion.json"), "compact_sha256": sha(RESULTS / "compact-worlds.json"),
              "complete_worlds_gzip_sha256": sha(RESULTS / "complete-worlds.jsonl.gz"), "source_files": len(freeze["files"]),
              "outcome_counts": dict(stats), "ledger_extrema": extrema, "preserved_adverse_examples": adverse_examples,
              "later_bundle_diagnostics": bundle_rows, "audit_elapsed_seconds": time.perf_counter() - begin,
              "scope": "Arithmetic and artifact reconciliation only. No market model, solver, random sampling or new cohort executed.",
              "limits": ["Counts describe the fixed sensitivity panel; they are not estimated empirical market probabilities.",
                         "All market money and larger populations remain simulated. Actual collections are zero and full actual cost unknown.",
                         "The retained later-investment control qualifies only the full G2+G3 bundle, not either component alone.",
                         "Floating-point arithmetic is compared to 1e-7 cents absolute tolerance; integer money and stored cash identities are exact."]}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "market-reconciliation.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "failure_counts", "first_issues", "total_checks", "worlds", "primary_histories", "additional_finance_controls", "outcome_counts", "ledger_extrema", "audit_elapsed_seconds")}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
