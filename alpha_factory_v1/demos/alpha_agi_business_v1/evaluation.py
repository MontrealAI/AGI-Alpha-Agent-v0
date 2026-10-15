# SPDX-License-Identifier: Apache-2.0
"""Bounded supplied-assumption evaluation. No incorporation, orders or compliance certification."""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

from alpha_factory_v1.demos.alpha_agi_business_3_v1.enterprise import digest, read_json


def _number(value: Any, label: str, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    if not minimum <= value <= 1e12 or not math.isfinite(value):
        raise ValueError(f"{label} is outside the supported bounds")
    return float(value)


def evaluate(state: dict) -> dict[str, dict]:
    """Rank net supplied benefits under capital/loss constraints; summarize supplied positions.

    Required: budget, max_loss, opportunities [{id,cost,benefit,worst_loss}].
    Optional: positions [{id,quantity,price}], company {name,jurisdiction},
    evidence_ids [str]. Scores and holdings are supplied assumptions, not verified facts.
    """
    if not isinstance(state, dict) or set(state) - {
        "budget",
        "max_loss",
        "opportunities",
        "positions",
        "company",
        "evidence_ids",
    }:
        raise ValueError("unknown business input fields")
    budget = _number(state.get("budget"), "budget")
    limit = _number(state.get("max_loss"), "max_loss")
    opportunities = state.get("opportunities")
    if not isinstance(opportunities, list) or not 1 <= len(opportunities) <= 100:
        raise ValueError("provide 1 to 100 opportunities")
    rows = []
    seen = set()
    for item in opportunities:
        if not isinstance(item, dict) or set(item) != {"id", "cost", "benefit", "worst_loss"}:
            raise ValueError("opportunity requires id, cost, benefit, worst_loss")
        ident = item["id"]
        if not isinstance(ident, str) or not ident.strip() or len(ident) > 160 or ident in seen:
            raise ValueError("opportunity ids must be unique nonempty strings of at most 160 characters")
        seen.add(ident)
        cost, benefit, loss = (_number(item[key], key) for key in ("cost", "benefit", "worst_loss"))
        reasons = []
        if cost > budget:
            reasons.append("over_budget")
        if loss > limit:
            reasons.append("loss_limit_exceeded")
        if benefit <= cost:
            reasons.append("nonpositive_net_benefit")
        rows.append(
            {
                "id": ident,
                "net_benefit": benefit - cost,
                "cost": cost,
                "worst_loss": loss,
                "eligible": not reasons,
                "reasons": reasons,
            }
        )
    rows.sort(key=lambda row: (-row["net_benefit"], row["id"]))
    eligible = [row for row in rows if row["eligible"]]
    selected = eligible[0] if eligible else None
    positions = state.get("positions", [])
    if not isinstance(positions, list) or len(positions) > 100:
        raise ValueError("positions must be a list of at most 100 supplied positions")
    values = []
    position_ids = set()
    for position in positions:
        if not isinstance(position, dict) or set(position) != {"id", "quantity", "price"}:
            raise ValueError("position requires id, quantity, price")
        ident = position["id"]
        if not isinstance(ident, str) or not ident.strip() or len(ident) > 160 or ident in position_ids:
            raise ValueError("position ids must be unique nonempty strings of at most 160 characters")
        position_ids.add(ident)
        values.append(_number(position["quantity"], "quantity", -1e12) * _number(position["price"], "price"))
    company = state.get("company", {})
    if not isinstance(company, dict) or set(company) - {"name", "jurisdiction"}:
        raise ValueError("company accepts name and jurisdiction only")
    if any(not isinstance(v, str) or not v.strip() or len(v) > 160 for v in company.values()):
        raise ValueError("company fields must be nonempty text of at most 160 characters")
    evidence = state.get("evidence_ids", [])
    if (
        not isinstance(evidence, list)
        or len(evidence) > 100
        or any(not isinstance(v, str) or not v.strip() or len(v) > 160 for v in evidence)
    ):
        raise ValueError("evidence_ids must contain bounded nonempty strings")
    common = {
        "mode": "supplied_assumption_evaluation",
        "input_id": digest(state),
        "evidence_ids": evidence,
        "external_actions_performed": False,
    }
    payloads = {
        "business": {
            "status": "manual_review_required",
            "company": company,
            "missing_fields": [key for key in ("name", "jurisdiction") if key not in company],
            "next_steps": ["Review jurisdiction and legal structure", "Obtain authorized filing and official receipt"],
            "incorporated": False,
        },
        "execution": {
            "status": "proposal_only" if selected else "no_eligible_proposal",
            "selected": selected,
            "ranked_candidates": rows,
            "orders_submitted": 0,
        },
        "risk": {
            "status": "assumptions_evaluated",
            "max_loss": limit,
            "candidate_breaches": [row["id"] for row in rows if row["worst_loss"] > limit],
            "selected_worst_loss": selected["worst_loss"] if selected else None,
        },
        "compliance": {
            "status": "manual_review_required",
            "certified": False,
            "jurisdiction": company.get("jurisdiction"),
            "unverified_evidence_count": len(evidence),
            "checks_pending": ["legal authority", "licensing", "counterparty review", "execution authorization"],
        },
        "portfolio": {
            "status": "supplied_positions_evaluated",
            "position_count": len(values),
            "net_value": sum(values),
            "gross_value": sum(abs(v) for v in values),
            "source": "user_supplied_unverified_positions",
        },
    }
    return {topic: {**common, **payload} for topic, payload in payloads.items()}


def service_payload(topic: str) -> dict:
    """Read bounded JSON per cycle; invalid/missing data can never produce success."""
    path = os.getenv("ALPHA_BUSINESS_STATE_FILE")
    if not path:
        return {
            "mode": "supplied_assumption_evaluation",
            "status": "input_required",
            "external_actions_performed": False,
            "required_input": "ALPHA_BUSINESS_STATE_FILE",
        }
    try:
        return evaluate(read_json(Path(path)))[topic]
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        return {
            "mode": "supplied_assumption_evaluation",
            "status": "invalid_input",
            "external_actions_performed": False,
            "error": str(exc),
        }


def main() -> None:
    """Evaluate a supplied JSON file without launching the service or any provider."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(read_json(args.input))
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
