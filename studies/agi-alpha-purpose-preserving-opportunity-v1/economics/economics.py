# SPDX-License-Identifier: Apache-2.0
"""Conditional cash and accrual accounting; no empirical demand or capability claims."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


def cents(value: float | int) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def usd(value: int) -> float:
    return value / 100


class Ledger:
    def __init__(self, capital: float, reserve: float, refund_fraction: float, label: str):
        self.capital = cents(capital)
        self.base_reserve = cents(reserve)
        self.refund_fraction = refund_fraction
        self.label = label
        self.accounts = dict(cash=0, revenue=0, expense=0, deferred=0, receivable=0)
        self.rows: list[dict[str, Any]] = []
        self.post(-10, "owner_capital_not_revenue", "financing", cash=capital)

    def post(self, day: int, event: str, bucket: str, **changes: float) -> None:
        delta = {key: cents(changes.get(key, 0)) for key in self.accounts}
        for key in self.accounts:
            self.accounts[key] += delta[key]
        a = self.accounts
        if a["cash"] + a["receivable"] - a["deferred"] != self.capital + a["revenue"] - a["expense"]:
            raise AssertionError("cash/accrual conservation failed")
        if a["deferred"] < 0 or a["receivable"] < 0:
            raise AssertionError("negative contractual liability or receivable")
        reserve = self.base_reserve + round(a["deferred"] * self.refund_fraction)
        row = dict(evaluation=self.label, day=day, event=event, bucket=bucket)
        row.update({f"{key}_delta_usd": usd(value) for key, value in delta.items()})
        row.update({f"{key}_usd": usd(value) for key, value in a.items()})
        row.update(refund_obligation_usd=usd(a["deferred"]), reserve_usd=usd(reserve))
        row["available_funds_usd"] = usd(a["cash"] - reserve)
        self.rows.append(row)

    def summary(self) -> dict[str, Any]:
        a = self.accounts
        minimum_available = min(row["available_funds_usd"] for row in self.rows)
        costs = {
            k: round(sum(r["expense_delta_usd"] for r in self.rows if r["bucket"] == k), 2) for k in ("A", "B", "C")
        }
        collections = sum(max(r["cash_delta_usd"], 0) for r in self.rows if r["bucket"] == "customer")
        refunds = -sum(min(r["cash_delta_usd"], 0) for r in self.rows if r["event"] == "refund")
        return dict(
            earned_revenue_usd=usd(a["revenue"]),
            accrued_profit_usd=usd(a["revenue"] - a["expense"]),
            costs_usd=costs,
            gross_collections_usd=round(collections, 2),
            refunds_usd=round(refunds, 2),
            net_collections_usd=round(collections - refunds, 2),
            ending_cash_usd=usd(a["cash"]),
            ending_receivable_usd=usd(a["receivable"]),
            refund_obligation_usd=usd(a["deferred"]),
            ending_reserve_usd=self.rows[-1]["reserve_usd"],
            available_funds_usd=self.rows[-1]["available_funds_usd"],
            minimum_available_funds_usd=minimum_available,
            minimum_initial_capital_usd=round(usd(self.capital) - minimum_available, 2),
            prefunding_shortfall_usd=round(max(0, -minimum_available), 2),
        )


def service_case(
    inputs: dict[str, Any], config: str, world: dict[str, Any], price: float, deposit_fraction: float
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    s, w, acceptance = inputs["service"], inputs["service"]["workflows"][config], inputs["external_acceptance"]
    label = f"{config}|{price}|{deposit_fraction}|{world['id']}"
    ledger = Ledger(s["starting_capital_usd"], s["operating_reserve_usd"], s["refund_reserve_fraction"], label)
    for bucket, key in (("B", "B_assessment_usd"), ("C", "C_optional_development_usd")):
        if w[key]:
            ledger.post(-2, key, bucket, cash=-w[key], expense=w[key])
    ordered = (
        price <= min(world["willingness_to_pay_usd"], s["outside_option_price_usd"])
        and deposit_fraction <= world["max_deposit"]
    )
    outcome, accepted = world["outcome"], False
    if ordered:
        deposit = usd(cents(price * deposit_fraction))
        ledger.post(0, "refundable_deposit", "customer", cash=deposit, deferred=deposit)
        labor = w["work_hours"] * s["human_hourly_rate_usd"]
        fraction = 0.25 if outcome == "withdrawal" else 1.0
        cost = usd(cents((labor + w["model_service_usd"]) * fraction))
        ledger.post(2, "paid_job_including_learning_subset", "A", cash=-cost, expense=cost)
        if w["B_serving_usd"]:
            ledger.post(2, "capability_serving", "B", cash=-w["B_serving_usd"], expense=w["B_serving_usd"])
        if outcome == "retry":
            extra = s["retry_correction_usd"]
            ledger.post(5, "correction", "A", cash=-extra, expense=extra)
        delivery = s["delivery_day"] + (20 if outcome == "late" else 0)
        accepted = (
            acceptance["technical_report_accepted"] is True
            and outcome in ("success", "retry", "default")
            and delivery <= acceptance["deadline_days"]
            and acceptance["customer_effort_hours"] <= acceptance["customer_effort_limit_hours"]
        )
        if accepted:
            ledger.post(
                delivery,
                "independently_accepted_report_assumed",
                "customer",
                revenue=price,
                deferred=-deposit,
                receivable=price - deposit,
            )
            if outcome == "default":
                ledger.post(
                    s["collection_day"],
                    "uncollected_balance_writeoff",
                    "A",
                    receivable=-(price - deposit),
                    expense=price - deposit,
                )
            else:
                ledger.post(
                    s["collection_day"],
                    "balance_collected",
                    "customer",
                    cash=price - deposit,
                    receivable=-(price - deposit),
                )
        else:
            extra = s["support_on_failure_usd"]
            ledger.post(8, "failure_or_withdrawal_support", "A", cash=-extra, expense=extra)
            ledger.post(s["refund_day"], "refund", "customer", cash=-deposit, deferred=-deposit)
    result = dict(
        configuration=config,
        world=world["id"],
        outcome=outcome,
        ordered=ordered,
        accepted_original_obligation=accepted,
        price_usd=price,
        deposit_fraction=deposit_fraction,
        evidence_class="simulated_conditional_on_assumed_inputs",
        **ledger.summary(),
    )
    return result, ledger.rows


def aggregate(cases: list[dict[str, Any]], worlds: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {w["id"]: w["weight"] for w in worlds}

    def expected(key: str) -> float:
        return round(float(sum(weights[c["world"]] * c[key] for c in cases)), 4)

    return dict(
        expected_earned_revenue_usd=expected("earned_revenue_usd"),
        expected_full_contribution_usd=expected("accrued_profit_usd"),
        expected_net_collections_usd=expected("net_collections_usd"),
        expected_accepted_outcomes=expected("accepted_original_obligation"),
        expected_costs_usd={
            k: round(sum(weights[c["world"]] * c["costs_usd"][k] for c in cases), 4) for k in ("A", "B", "C")
        },
        required_initial_capital_usd=max(c["minimum_initial_capital_usd"] for c in cases),
        worst_prefunding_shortfall_usd=max(c["prefunding_shortfall_usd"] for c in cases),
    )


def choose_offer(inputs: dict[str, Any], config: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    s, offers = inputs["service"], []
    for price in s["price_candidates_usd"]:
        for deposit in s["deposit_candidates"]:
            results = [service_case(inputs, config, world, price, deposit) for world in inputs["worlds"]]
            cases = [r[0] for r in results]
            offers.append(
                dict(
                    price_usd=price,
                    deposit_fraction=deposit,
                    cases=cases,
                    ledger=[row for result in results for row in result[1]],
                    **aggregate(cases, inputs["worlds"]),
                )
            )
    best = sorted(offers, key=lambda o: (-o["expected_full_contribution_usd"], o["price_usd"], o["deposit_fraction"]))[
        0
    ]
    reasons = []
    if best["expected_full_contribution_usd"] <= 0:
        reasons.append("nonpositive_expected_full_contribution")
    if best["worst_prefunding_shortfall_usd"] > 0:
        reasons.append("insufficient_prefunding_under_declared_reserve_policy")
    rows = best.pop("ledger")
    best.update(
        configuration=config,
        conditional_decision="stop" if reasons else "eligible_only_if_assumptions_hold",
        stop_reasons=reasons,
        offer_count=len(offers),
        actual_sales=0,
        retained_gain_assigned=False,
        assumptions_validated=False,
    )
    return best, rows


def construction_case(
    inputs: dict[str, Any], evidence: bool, participation: bool, world: dict[str, Any]
) -> dict[str, Any]:
    j, s = inputs["joint_construction"], inputs["service"]
    blockers = []
    if not evidence:
        blockers.extend(["provenance_rights_yield_unverified"])
    if not participation:
        blockers.append("no_confirmed_conditional_participation")
    if world["outcome"] == "withdrawal":
        blockers.append("withdrawal_before_build_invalidates_commitments")
    if world["id"] == "buyer_declines":
        blockers.append("nonparticipation")
    price = j["buyer_count"] * j["price_per_buyer_usd"]
    if j["price_per_buyer_usd"] > min(j["buyer_value_usd"], j["buyer_outside_option_usd"]):
        blockers.append("price_exceeds_value_or_outside_option")
    ledger = Ledger(
        j["starting_capital_usd"],
        s["operating_reserve_usd"],
        s["refund_reserve_fraction"],
        f"construction|{int(evidence)}{int(participation)}|{world['id']}",
    )
    accepted = False
    if evidence and participation:
        cost = j["coordination_A_usd"]
        ledger.post(-2, "prospective_coordination", "A", cash=-cost, expense=cost)
    if not blockers:
        deposit = price * j["deposit_fraction"]
        ledger.post(0, "conditional_refundable_deposits", "customer", cash=deposit, deferred=deposit)
        cost = j["construction_A_usd"]
        ledger.post(30, "prospective_shared_construction_required_for_job", "A", cash=-cost, expense=cost)
        if world["outcome"] == "retry":
            cost = j["retry_A_usd"]
            ledger.post(400, "production_correction", "A", cash=-cost, expense=cost)
        delivery = j["delivery_A_per_buyer_usd"] * j["buyer_count"]
        ledger.post(700, "prospective_lot_delivery", "A", cash=-delivery, expense=delivery)
        accepted = world["outcome"] in ("success", "retry", "default")
        if accepted:
            ledger.post(
                730,
                "hypothetical_accepted_lots_not_ecological_outcomes",
                "customer",
                revenue=price,
                deferred=-deposit,
                receivable=price - deposit,
            )
            if world["outcome"] == "default":
                ledger.post(
                    760, "uncollected_balance_writeoff", "A", expense=price - deposit, receivable=-(price - deposit)
                )
            else:
                ledger.post(760, "balance_collected", "customer", cash=price - deposit, receivable=-(price - deposit))
        else:
            cost = j["failure_support_A_usd"]
            ledger.post(740, "production_failure_support", "A", cash=-cost, expense=cost)
            ledger.post(760, "refund", "customer", cash=-deposit, deferred=-deposit)
    return dict(
        world=world["id"],
        evidence_assumed_sufficient=evidence,
        participation_assumed_confirmed=participation,
        blockers=blockers,
        accepted_original_obligation=accepted,
        **ledger.summary(),
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if rows:
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def run(inputs_path: Path, output: Path) -> dict[str, Any]:
    raw = inputs_path.read_bytes()
    inputs = json.loads(raw)
    if abs(sum(w["weight"] for w in inputs["worlds"]) - 1) > 1e-9:
        raise ValueError("world weights must sum to one")
    for workflow in inputs["service"]["workflows"].values():
        if not 0 <= workflow["paid_job_learning_hours_included"] <= workflow["work_hours"]:
            raise ValueError("paid-job learning must be a subset of delivery effort")
    service, ledger, comparisons = {}, [], []
    for config in ("H", "U", "E", "E+"):
        selected, rows = choose_offer(inputs, config)
        service[config] = selected
        ledger.extend(rows)
        comparisons.append(
            {
                key: selected[key]
                for key in (
                    "configuration",
                    "price_usd",
                    "deposit_fraction",
                    "expected_earned_revenue_usd",
                    "expected_net_collections_usd",
                    "expected_full_contribution_usd",
                    "required_initial_capital_usd",
                    "worst_prefunding_shortfall_usd",
                    "conditional_decision",
                )
            }
        )
    mechanism = {}
    for evidence, participation, name in (
        (False, False, "neither"),
        (True, False, "technical_only"),
        (False, True, "arrangement_only"),
        (True, True, "combined"),
    ):
        cases = [construction_case(inputs, evidence, participation, world) for world in inputs["worlds"]]
        summary = aggregate(cases, inputs["worlds"])
        summary.update(
            cases=cases,
            decision="blocked_actual_evidence_and_participation_missing",
            causal_claim=False,
            independent_ecological_acceptance=False,
        )
        mechanism[name] = summary
    evaluations = 4 * len(inputs["service"]["price_candidates_usd"]) * len(
        inputs["service"]["deposit_candidates"]
    ) * len(inputs["worlds"]) + 4 * len(inputs["worlds"])
    if evaluations > inputs["policy"]["maximum_evaluations"]:
        raise ValueError("declared evaluation budget exceeded")
    result = dict(
        schema="agialpha.conditional-economics-results.v1",
        input_sha256=hashlib.sha256(raw).hexdigest(),
        evidence_class="simulated",
        actual=inputs["actual"],
        actual_economic_feasibility="unknown",
        human_reference=inputs["service"]["H_reference"],
        service=service,
        construction=mechanism,
        equal_information_expert_result=mechanism["combined"],
        equal_information_tie=True,
        empirical_operational_alpha="not_measured",
        empirical_learned_alpha="not_measured",
        evaluations=evaluations,
        no_ecological_success_or_market_price_claim=True,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_csv(output / "transactions.csv", ledger)
    write_csv(output / "configuration_comparison.csv", comparisons)
    nominal = [r for r in ledger if r["evaluation"].startswith("E|") and r["evaluation"].endswith("|accepted")]
    write_csv(output / "cash_curve.csv", nominal)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=Path(__file__).with_name("inputs.json"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results"))
    args = parser.parse_args()
    report = run(args.inputs, args.output)
    print(
        json.dumps(
            {
                "evaluations": report["evaluations"],
                "service": {
                    k: {
                        field: v[field]
                        for field in ("price_usd", "expected_full_contribution_usd", "conditional_decision")
                    }
                    for k, v in report["service"].items()
                },
                "actual": report["actual"],
            },
            indent=2,
        )
    )
