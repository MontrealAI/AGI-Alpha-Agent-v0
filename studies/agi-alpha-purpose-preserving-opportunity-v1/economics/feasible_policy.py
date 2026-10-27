# SPDX-License-Identifier: Apache-2.0
"""Choose a complete enumerated plan only after independent gates and cash feasibility.

This is a conditional decision rule, not evidence verification, a market simulator,
continuous price optimization, production authority, or an observation of profit.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
INPUT_SCHEMA = "agialpha.feasible-policy-input.v1"
BUCKETS = ("A", "B", "C")
GATES = ("readiness", "acceptance")


class InvalidInput(ValueError):
    """Required evidence or financial input is missing, unknown or malformed."""


def nonempty(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise InvalidInput(f"{name}: a nonempty string is required")
    return value


def number(value: Any, name: str, *, nonnegative: bool = False) -> Decimal:
    if type(value) not in (int, float):
        raise InvalidInput(f"{name}: a known JSON number is required; booleans are not numbers")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise InvalidInput(f"{name}: invalid number") from exc
    if not result.is_finite() or (nonnegative and result < 0):
        raise InvalidInput(f"{name}: number must be finite" + (" and nonnegative" if nonnegative else ""))
    return result


def object_value(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name}: an object is required")
    return value


def list_value(value: Any, name: str, *, allow_empty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise InvalidInput(f"{name}: a {'possibly empty' if allow_empty else 'nonempty'} list is required")
    return value


def world_weights(data: dict[str, Any]) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for raw in list_value(data.get("worlds"), "worlds"):
        world = object_value(raw, "world")
        identifier = nonempty(world.get("id"), "world.id")
        if identifier in result:
            raise InvalidInput("world IDs must be unique")
        probability = number(world.get("probability"), "world.probability", nonnegative=True)
        if probability > 1:
            raise InvalidInput("world.probability exceeds one")
        result[identifier] = probability
    if sum(result.values(), Decimal(0)) != 1:
        raise InvalidInput("shared world probabilities must sum exactly to one; no normalization is performed")
    return result


def gate_reasons(alternative: dict[str, Any], proposer: str) -> list[str]:
    reasons = []
    evidence = object_value(alternative.get("independent_evidence"), "independent_evidence")
    for name in GATES:
        gate = object_value(evidence.get(name), f"independent_evidence.{name}")
        if gate.get("passed") is not True:
            reasons.append(f"{name}_not_passed_or_unknown")
        if gate.get("independent") is not True:
            reasons.append(f"{name}_independence_not_established")
        attestor = nonempty(gate.get("attestor"), f"{name}.attestor")
        nonempty(gate.get("reference"), f"{name}.reference")
        nonempty(gate.get("scope"), f"{name}.scope")
        if attestor == proposer:
            reasons.append(f"{name}_self_attested_by_proposer")
    return reasons


def evaluate_alternative(raw: Any, weights: dict[str, Decimal], opening_cash: Decimal) -> dict[str, Any]:
    """Require all costs and all declared cash prefixes before assigning eligibility."""
    identifier = raw.get("id") if isinstance(raw, dict) else None
    result: dict[str, Any] = {
        "id": identifier,
        "eligible": False,
        "reasons": [],
        "expected_complete_contribution_usd": None,
        "minimum_available_funds_usd": None,
        "worlds": [],
    }
    try:
        alternative = object_value(raw, "alternative")
        identifier = nonempty(alternative.get("id"), "alternative.id")
        proposer = nonempty(alternative.get("proposer"), "proposer")
        configuration = nonempty(alternative.get("configuration"), "configuration")
        production_plan = nonempty(alternative.get("production_plan"), "production_plan")
        retention_choice = nonempty(alternative.get("retention_choice"), "retention_choice")
        development_choice = nonempty(alternative.get("development_choice"), "development_choice")
        price = number(alternative.get("price_usd"), "price_usd", nonnegative=True)
        deposit = number(alternative.get("deposit_fraction"), "deposit_fraction", nonnegative=True)
        if deposit > 1:
            raise InvalidInput("deposit_fraction exceeds one")
        reasons = gate_reasons(alternative, proposer)
        scenarios = list_value(alternative.get("scenarios"), "scenarios")
        seen: set[str] = set()
        expected = Decimal(0)
        minimum_available: Decimal | None = None
        world_results = []
        for raw_scenario in scenarios:
            scenario = object_value(raw_scenario, "scenario")
            world_id = nonempty(scenario.get("world_id"), "scenario.world_id")
            if world_id in seen or world_id not in weights:
                raise InvalidInput("scenario IDs must be unique and belong to the shared world set")
            seen.add(world_id)
            if scenario.get("costs_complete") is not True:
                reasons.append(f"{world_id}:complete_costs_not_established")
            if scenario.get("cash_path_complete") is not True:
                reasons.append(f"{world_id}:complete_cash_path_not_established")
            revenue = number(scenario.get("earned_revenue_usd"), "earned_revenue_usd", nonnegative=True)
            costs = object_value(scenario.get("costs"), "costs")
            total_monetary_cost = Decimal(0)
            total_opportunity_cost = Decimal(0)
            for bucket in BUCKETS:
                cost = object_value(costs.get(bucket), f"costs.{bucket}")
                total_monetary_cost += number(
                    cost.get("monetary_expense_usd"), f"{bucket}.monetary_expense_usd", nonnegative=True
                )
                total_opportunity_cost += number(
                    cost.get("opportunity_cost_usd"), f"{bucket}.opportunity_cost_usd", nonnegative=True
                )
            contribution = revenue - total_monetary_cost - total_opportunity_cost
            expected += weights[world_id] * contribution
            world_minimum: Decimal | None = None
            for index, raw_prefix in enumerate(list_value(scenario.get("cash_path"), "cash_path")):
                prefix = object_value(raw_prefix, "cash prefix")
                nonempty(prefix.get("label"), "cash prefix label")
                cash = number(prefix.get("cash_balance_usd"), "cash_balance_usd")
                if index == 0 and cash != opening_cash:
                    raise InvalidInput("first cash prefix must equal declared opening cash")
                restrictions = number(
                    prefix.get("restricted_for_obligations_usd"), "restricted_for_obligations_usd", nonnegative=True
                )
                reserve = number(prefix.get("operating_reserve_usd"), "operating_reserve_usd", nonnegative=True)
                available = cash - restrictions - reserve
                world_minimum = available if world_minimum is None else min(world_minimum, available)
            if world_minimum is None:
                raise InvalidInput("cash path is empty")
            minimum_available = world_minimum if minimum_available is None else min(minimum_available, world_minimum)
            if world_minimum < 0:
                reasons.append(f"{world_id}:liquidity_failure")
            world_results.append(
                {
                    "world_id": world_id,
                    "complete_contribution_usd": str(contribution),
                    "monetary_expense_usd": str(total_monetary_cost),
                    "opportunity_cost_usd": str(total_opportunity_cost),
                    "minimum_available_funds_usd": str(world_minimum),
                }
            )
        if seen != set(weights):
            raise InvalidInput("every alternative must include exactly the shared world set")
        if expected <= 0:
            reasons.append("nonpositive_expected_complete_contribution")
        result.update(
            id=identifier,
            configuration=configuration,
            production_plan=production_plan,
            retention_choice=retention_choice,
            development_choice=development_choice,
            price_usd=str(price),
            deposit_fraction=str(deposit),
            eligible=not reasons,
            reasons=sorted(set(reasons)),
            expected_complete_contribution_usd=str(expected),
            minimum_available_funds_usd=str(minimum_available),
            worlds=world_results,
        )
    except InvalidInput as exc:
        result["reasons"] = ["unknown_or_invalid_required_input: " + str(exc)]
    return result


def select(data: Any) -> dict[str, Any]:
    payload = object_value(data, "input")
    if payload.get("schema") != INPUT_SCHEMA:
        raise InvalidInput("unsupported input schema")
    information_set = nonempty(payload.get("information_set_id"), "information_set_id")
    weight_status = nonempty(payload.get("world_weights_evidence"), "world_weights_evidence")
    opening_cash = number(payload.get("opening_cash_usd"), "opening_cash_usd", nonnegative=True)
    weights = world_weights(payload)
    alternatives = list_value(payload.get("alternatives"), "alternatives")
    identifiers = [nonempty(object_value(a, "alternative").get("id"), "alternative.id") for a in alternatives]
    if len(set(identifiers)) != len(identifiers):
        raise InvalidInput("alternative IDs must be unique")
    evaluated = [evaluate_alternative(alternative, weights, opening_cash) for alternative in alternatives]
    eligible = [alternative for alternative in evaluated if alternative["eligible"]]
    ranked = sorted(
        eligible,
        key=lambda a: (
            -Decimal(a["expected_complete_contribution_usd"]),
            Decimal(a["price_usd"]),
            a["id"],
        ),
    )
    return {
        "schema": "agialpha.feasible-policy-output.v1",
        "policy_version": VERSION,
        "information_set_id": information_set,
        "world_weights_evidence": weight_status,
        "opening_cash_usd": str(opening_cash),
        "decision": "conditional_selection" if ranked else "stop",
        "selected_id": ranked[0]["id"] if ranked else None,
        "eligible_ranking": [alternative["id"] for alternative in ranked],
        "alternatives": evaluated,
        "selection_rule": "eligibility first; highest positive complete expected contribution; ties lower price then ID",
        "external_evidence_verified_by_this_code": False,
        "actual_profit_established": False,
        "production_authorized": False,
        "scope": "finite supplied alternatives and declared worlds; no unknown values filled or assumptions validated",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = select(json.loads(args.inputs.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"decision": output["decision"], "selected_id": output["selected_id"]}))


if __name__ == "__main__":
    main()
