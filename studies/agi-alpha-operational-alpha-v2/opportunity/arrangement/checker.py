# SPDX-License-Identifier: Apache-2.0
"""Exact small joint-arrangement checker with reserved escrow and dated acceptance."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
from fractions import Fraction
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MODES = ("post_acceptance", "refundable_escrow", "accepted_milestone_escrow")


def exact(value: Fraction | int) -> dict[str, int]:
    f = Fraction(value)
    return {"numerator": f.numerator, "denominator": f.denominator}


def money(value: Fraction | int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise ValueError("cash entries require integer cents or exact integral Fraction")
    number = Fraction(value)
    if number.denominator != 1 or number < 0:
        raise ValueError("cash entries must be nonnegative integer cents")
    return number.numerator


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def scenarios(ids: list[str]) -> list[dict[str, Any]]:
    return [
        {"id": "success", "weight": "3/5", "common_ok": True},
        {"id": "common_failure", "weight": "1/5", "common_ok": False},
        {"id": "withdrawal", "weight": "1/20", "common_ok": True, "withdraw": [ids[0]]},
        {"id": "partial_acceptance", "weight": "1/20", "common_ok": True, "fail": [ids[-1]]},
        {"id": "payer_default", "weight": "1/20", "common_ok": True, "default": [ids[-1]]},
        {"id": "late_refund", "weight": "1/20", "common_ok": True, "refund": [ids[0]]},
    ]


def simulate(plan: dict[str, Any], inputs: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    participants = {p["id"]: p for p in inputs["participants"]}
    ids = plan["participants"]
    if not ids or len(set(ids)) != len(ids) or any(i not in participants for i in ids):
        raise ValueError("nonempty distinct known participant subset required")
    mode = plan["finance"]
    if mode not in MODES:
        raise ValueError("unknown payment mode")
    technical = plan["technical"]
    saving = Fraction(inputs["adaptation_saving"])
    if not 0 <= saving <= 1:
        raise ValueError("assumed saving must lie between zero and one")
    if not 0 <= Fraction(inputs["common_fraction"]) <= 1:
        raise ValueError("common milestone fraction must lie between zero and one")
    coordinated = plan["coordinated"]
    if not coordinated and len(ids) > 1:
        raise ValueError("restricted singleton benchmark cannot bind multiple buyers")
    if mode == "accepted_milestone_escrow" and (not technical or not inputs["common_independently_useful"]):
        raise ValueError("unearned or nonuseful common milestone cannot fund delivery")
    q = money(plan["price_cents"])
    common_q = money(q * Fraction(inputs["common_fraction"])) if mode == "accepted_milestone_escrow" else 0
    delay = int(world.get("delay", 0))
    if delay < 0 or delay > 20:
        raise ValueError("bounded nonnegative payment delay required")
    events: list[dict[str, Any]] = []
    paid = {i: 0 for i in ids}
    values = {i: 0 for i in ids}
    costs = {"A": 0, "B": 0, "C": 0}
    earned = refunds = collected = 0
    escrow_balances = {i: 0 for i in ids}
    sequence = 0

    def emit(
        day: int,
        kind: str,
        amount: int,
        *,
        buyer: str | None = None,
        group: str | None = None,
        cash: int = 0,
        liability: int = 0,
        reserve: int = 0,
        earned_delta: int = 0,
    ) -> None:
        nonlocal sequence
        amount = money(amount)
        sequence += 1
        events.append(
            {
                "day": day,
                "order": sequence,
                "kind": kind,
                "amount_cents": amount,
                "buyer": buyer,
                "group": group,
                "cash_delta_cents": cash,
                "escrow_delta_cents": liability,
                "support_reserve_delta_cents": reserve,
                "earned_delta_cents": earned_delta,
            }
        )

    def charge(day: int, amount: int, group: str, description: str) -> None:
        amount = money(amount)
        costs[group] += amount
        emit(day, description, amount, group=group, cash=-amount)

    def accept(day: int, buyer: str, amount: int, milestone: str) -> None:
        nonlocal earned, collected
        earned += amount
        emit(day, "accepted-" + milestone, amount, buyer=buyer, earned_delta=amount)
        if mode == "post_acceptance":
            if buyer not in world.get("default", []):
                collected += amount
                paid[buyer] += amount
                emit(day + delay, "earned-receipt", amount, buyer=buyer, cash=amount)
            else:
                emit(day + delay, "unpaid-accepted-invoice", amount, buyer=buyer)
        else:
            if escrow_balances[buyer] < amount:
                raise AssertionError("release exceeds funded escrow")
            escrow_balances[buyer] -= amount
            collected += amount
            paid[buyer] += amount
            emit(day + delay, "escrow-release-after-acceptance", amount, buyer=buyer, liability=-amount)

    def refund_unearned(day: int, buyer: str) -> None:
        amount = escrow_balances[buyer]
        escrow_balances[buyer] = 0
        if amount:
            emit(day, "unearned-escrow-return", amount, buyer=buyer, cash=-amount, liability=-amount)

    if mode != "post_acceptance":
        for buyer in ids:
            escrow_balances[buyer] = q
            emit(0, "refundable-deposit", q, buyer=buyer, cash=q, liability=q)
    charge(0, inputs["coordination_cents"] if coordinated and len(ids) > 1 else 0, "A", "contract-coordination")
    charge(0, inputs["exploration_C_cents"], "C", "optional-extra-exploration")
    charge(1, inputs["core_cents"] if technical else 0, "A", "required-common-construction-once")
    active = [i for i in ids if i not in world.get("withdraw", [])]
    for buyer in ids:
        if buyer not in active:
            refund_unearned(2, buyer)
    if not world["common_ok"]:
        for buyer in active:
            refund_unearned(3, buyer)
        charge(3, inputs.get("common_failure_support_cents", 0), "A", "common-failure-support")
    else:
        if technical:
            charge(3, inputs["retention_B_cents"], "B", "additional-retention-only")
        for index, buyer in enumerate(active):
            p = participants[buyer]
            if technical and inputs["common_independently_useful"]:
                values[buyer] += p["common_value_cents"]
            if common_q:
                accept(3, buyer, common_q, "independently-useful-common-milestone")
            cost = Fraction(p["adaptation_cents"])
            if technical:
                cost *= 1 - Fraction(inputs["adaptation_saving"])
            charge(
                4 if inputs.get("batch_adaptations", False) else 4 + index,
                money(cost),
                "A",
                "mission-adaptation-" + buyer,
            )
            due = 6 if inputs.get("batch_adaptations", False) else 5 + index
            if buyer in world.get("fail", []):
                refund_unearned(due, buyer)
                charge(due + 1, p["support_cents"], "A", "failed-mission-support-" + buyer)
            else:
                values[buyer] += p["mission_value_cents"]
                accept(due, buyer, q - common_q, "mission")
                reserve = p["support_cents"]
                emit(due, "support-reserve", reserve, buyer=buyer, reserve=reserve)
                if buyer in world.get("refund", []):
                    amount = paid[buyer] - (common_q if common_q else 0)
                    values[buyer] -= p["mission_value_cents"]
                    paid[buyer] -= amount
                    collected -= amount
                    refunds += amount
                    earned -= q - common_q
                    emit(
                        due + delay + 10,
                        "accepted-mission-refund",
                        amount,
                        buyer=buyer,
                        cash=-amount,
                        earned_delta=-(q - common_q),
                    )
                    charge(due + delay + 10, reserve, "A", "refund-support-" + buyer)
                emit(due + delay + 15, "support-reserve-release", reserve, buyer=buyer, reserve=-reserve)
            if buyer not in world.get("fail", []):
                route = inputs.get("per_accepted_route_cents", 0)
                charge(due + delay + 1, route, "A", "accepted-route-" + buyer)
    events.sort(key=lambda e: (e["day"], e["order"]))
    relative_cash = escrow = support = 0
    protected = inputs["protected_reserve_cents"]
    required = protected
    for event in events:
        relative_cash += event["cash_delta_cents"]
        escrow += event["escrow_delta_cents"]
        support += event["support_reserve_delta_cents"]
        if escrow < 0 or support < 0:
            raise AssertionError("negative reserved liability")
        available = relative_cash - escrow - support - protected
        required = max(required, -available)
        event.update(
            cash_before_opening_cents=relative_cash,
            escrow_liability_cents=escrow,
            support_reserve_cents=support,
            available_before_opening_cents=available,
            cash_with_declared_opening_cents=inputs["opening_cash_cents"] + relative_cash,
            available_with_declared_opening_cents=inputs["opening_cash_cents"] + available,
        )
    if escrow or support:
        raise AssertionError("unsettled escrow or support reserve")
    total = sum(costs.values())
    if relative_cash != collected - total:
        raise AssertionError("escrow principal treated as earned cash or cost duplicated")
    return {
        "scenario": world["id"],
        "costs_cents": costs,
        "total_cost_cents": total,
        "net_earned_collections_cents": collected,
        "recognized_revenue_cents": earned,
        "unpaid_or_defaulted_receivables_cents": earned - collected,
        "earned_refunds_cents": refunds,
        "contribution_cents": relative_cash,
        "opening_cash_cents": inputs["opening_cash_cents"],
        "closing_cash_cents": inputs["opening_cash_cents"] + relative_cash,
        "closing_available_funds_cents": inputs["opening_cash_cents"] + relative_cash - protected,
        "required_opening_cash_cents": required,
        "protected_reserve_cents": protected,
        "final_escrow_liability_cents": escrow,
        "final_support_reserve_cents": support,
        "buyer_net_value_cents": {i: values[i] - paid[i] for i in ids},
        "buyer_payment_cents": paid,
        "events": events,
    }


def evaluate(
    plan: dict[str, Any], inputs: dict[str, Any], worlds: list[dict[str, Any]] | None = None, ledgers: bool = False
) -> dict[str, Any]:
    worlds = worlds if worlds is not None else scenarios(plan["participants"])
    weights = [Fraction(w["weight"]) for w in worlds]
    if any(w < 0 for w in weights) or sum(weights) != 1:
        raise ValueError("explicit nonnegative scenario weights must total one")
    runs = [simulate(plan, inputs, w) for w in worlds]
    expectation = sum((weight * run["contribution_cents"] for weight, run in zip(weights, runs)), Fraction(0))
    expected_buyers = {
        i: sum((w * r["buyer_net_value_cents"][i] for w, r in zip(weights, runs)), Fraction(0))
        for i in plan["participants"]
    }
    people = {p["id"]: p for p in inputs["participants"]}
    participates = all(expected_buyers[i] >= people[i]["outside_surplus_cents"] for i in expected_buyers)
    required = max(r["required_opening_cash_cents"] for r in runs)
    financed = required <= inputs["opening_cash_cents"]
    rights = inputs["hypothetical_rights_cleared"]
    success = next((r for r in runs if r["scenario"] == "success"), None)
    reason = []
    if expectation <= 0:
        reason.append("nonpositive-supplied-weight-contribution")
    if not participates:
        reason.append("participant-outside-option-not-met")
    if not financed:
        reason.append("declared-prefix-cash-not-funded")
    if not rights:
        reason.append("rights-not-cleared")
    result = {
        "plan": plan,
        "conditional_admissible": not reason,
        "actual_business_qualification": "NOT_ESTABLISHED_UNMEASURED_COSTS_VALUES_AND_COMMITMENTS",
        "reasons": reason,
        "expected_contribution_cents": exact(expectation),
        "success_contribution_cents": success["contribution_cents"] if success else None,
        "worst_scenario_contribution_cents": min(r["contribution_cents"] for r in runs),
        "required_opening_cash_cents": required,
        "opening_cash_cents": inputs["opening_cash_cents"],
        "protected_reserve_cents": inputs["protected_reserve_cents"],
        "expected_participant_net_value_cents": {i: exact(v) for i, v in expected_buyers.items()},
        "expected_participant_surplus_above_outside_cents": {
            i: exact(v - people[i]["outside_surplus_cents"]) for i, v in expected_buyers.items()
        },
        "scenario_summaries": [{k: v for k, v in r.items() if k != "events"} for r in runs],
    }
    if ledgers:
        result["ledgers"] = runs
    return result


def enumerate_plans(
    inputs: dict[str, Any], prices: list[int], technical: bool | None, coordinated: bool | None
) -> list[dict[str, Any]]:
    ids = [p["id"] for p in inputs["participants"]]
    plans = []
    for t in [False, True] if technical is None else [technical]:
        for c in [False, True] if coordinated is None else [coordinated]:
            for n in range(1, len(ids) + 1 if c else 2):
                for subset in itertools.combinations(ids, n):
                    for price in prices:
                        for mode in MODES:
                            if mode == "accepted_milestone_escrow" and (
                                not t or not inputs["common_independently_useful"]
                            ):
                                continue
                            plans.append(
                                {
                                    "technical": t,
                                    "coordinated": c,
                                    "participants": list(subset),
                                    "price_cents": price,
                                    "finance": mode,
                                }
                            )
    return plans


def select(
    inputs: dict[str, Any], prices: list[int], technical: bool | None, coordinated: bool | None
) -> dict[str, Any]:
    checked = [evaluate(p, inputs) for p in enumerate_plans(inputs, prices, technical, coordinated)]
    viable = [r for r in checked if r["conditional_admissible"]]
    if viable:
        selected = max(
            viable,
            key=lambda r: (
                Fraction(**r["expected_contribution_cents"]),
                -r["required_opening_cash_cents"],
                -len(r["plan"]["participants"]),
                json.dumps(r["plan"], sort_keys=True),
            ),
        )
        action = "conditional-package"
    else:
        selected = None
        action = "hold"
    return {
        "action": action,
        "selected": selected,
        "candidates": len(checked),
        "accepted_candidates": len(viable),
        "all_candidates": checked,
        "search_limit": "declared uniform prices, three buyers, no unrestricted contract search",
    }


def diagnostic_inputs(protocol: dict[str, Any], core: int, saving: str, useful: bool) -> dict[str, Any]:
    return {
        "participants": [
            {
                "id": p["id"],
                "mission_value_cents": p["mission_value_cents"],
                "outside_surplus_cents": p["outside_surplus_cents"],
                "adaptation_cents": p["baseline_adaptation_cents"],
                "support_cents": p["support_cents"],
                "common_value_cents": protocol["diagnostic_common_value_cents_if_explicitly_useful"] if useful else 0,
            }
            for p in protocol["diagnostic_participants"]
        ],
        "core_cents": core,
        "adaptation_saving": saving,
        "common_independently_useful": useful,
        "common_fraction": protocol["common_milestone_fraction"],
        "coordination_cents": protocol["coordination_cost_cents"],
        "retention_B_cents": protocol["extra_retention_B_cents"],
        "exploration_C_cents": protocol["optional_exploration_C_cents"],
        "opening_cash_cents": protocol["opening_cash_cap_cents"],
        "protected_reserve_cents": protocol["protected_reserve_cents"],
        "hypothetical_rights_cleared": True,
        "evidence_label": "arbitrary diagnostic supplied conditions, not estimated S3 prices/costs/values",
    }


def freeze(out: Path) -> None:
    if (out / "FREEZE.json").exists():
        raise ValueError("refusing to overwrite arrangement freeze")
    protocol = json.loads((HERE / "PROTOCOL.json").read_text())
    rows = []
    reference = None
    for core, saving, useful in itertools.product(
        protocol["core_cost_grid_cents"],
        protocol["adaptation_saving_sensitivity"],
        protocol["independent_milestone_usefulness_sensitivity"],
    ):
        inputs = diagnostic_inputs(protocol, core, saving, useful)
        for label, t, c in [
            ("neither", False, False),
            ("technical_only", True, False),
            ("coordination_only", False, True),
            ("both", True, True),
            ("unrestricted_conventional", None, None),
        ]:
            result = select(inputs, protocol["price_grid_cents"], t, c)
            row = {
                "core_cents": core,
                "assumed_saving": saving,
                "assumed_useful_common_milestone": useful,
                "configuration": label,
                **result,
            }
            rows.append(row)
            if core == 30000 and saving == "0" and not useful and label == "unrestricted_conventional":
                reference = {"inputs": inputs, "selection": result["selected"]}
    if reference is None:
        raise AssertionError("missing diagnostic reference")
    dump(out / "conditional_frontier.json", rows)
    dump(out / "reference_selection.json", reference)
    dump(
        out / "FREEZE.json",
        {
            "schema": protocol["schema"],
            "source_sha256": sha(Path(__file__)),
            "protocol_sha256": sha(HERE / "PROTOCOL.json"),
            "frontier_sha256": sha(out / "conditional_frontier.json"),
            "reference_sha256": sha(out / "reference_selection.json"),
            "fresh_cases": protocol["fresh_stress"],
            "actual_commitments": 0,
            "warning": "Parameter sweep is conditional analysis, not prevalence or measured opportunity value.",
        },
    )
    print(json.dumps({"freeze_sha256": sha(out / "FREEZE.json"), "reference": reference["selection"]}, indent=2))


def stress(out: Path) -> None:
    frozen = json.loads((out / "FREEZE.json").read_text())
    if frozen["source_sha256"] != sha(Path(__file__)) or frozen["protocol_sha256"] != sha(HERE / "PROTOCOL.json"):
        raise ValueError("frozen source/protocol changed")
    if frozen["reference_sha256"] != sha(out / "reference_selection.json"):
        raise ValueError("selected plan changed")
    if (out / "fresh_stress.json").exists():
        raise ValueError("refusing to overwrite fresh stress")
    reference = json.loads((out / "reference_selection.json").read_text())
    selection = reference["selection"]
    if selection is None:
        raise ValueError("reference selected HOLD; no policy to stress")
    plan = selection["plan"]
    ids = plan["participants"]
    rng = random.Random(frozen["fresh_cases"]["seed"])
    results = []
    for index in range(frozen["fresh_cases"]["cases"]):
        world = {
            "id": f"fresh-{index:02}",
            "common_ok": rng.randrange(5) != 0,
            "withdraw": [i for i in ids if rng.randrange(9) == 0],
            "fail": [i for i in ids if rng.randrange(7) == 0],
            "default": [i for i in ids if rng.randrange(8) == 0],
            "refund": [i for i in ids if rng.randrange(10) == 0],
            "delay": rng.choice([0, 3, 10, 20]),
        }
        result = simulate(plan, reference["inputs"], world)
        result["funded_with_declared_opening"] = (
            result["required_opening_cash_cents"] <= reference["inputs"]["opening_cash_cents"]
        )
        results.append({"world": world, "result": result})
    dump(out / "fresh_stress.json", results)
    dump(
        out / "FRESH_COMPLETE.json",
        {
            "freeze_sha256": sha(out / "FREEZE.json"),
            "cases": len(results),
            "negative_contribution_cases": sum(r["result"]["contribution_cents"] < 0 for r in results),
            "cash_infeasible_cases": sum(not r["result"]["funded_with_declared_opening"] for r in results),
            "results_sha256": sha(out / "fresh_stress.json"),
            "scope": "fresh synthetic combinations; no empirical market or model validation",
        },
    )
    print((out / "FRESH_COMPLETE.json").read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "stress"])
    parser.add_argument("--out", type=Path, default=HERE / "results")
    args = parser.parse_args()
    (freeze if args.action == "freeze" else stress)(args.out)


if __name__ == "__main__":
    main()
