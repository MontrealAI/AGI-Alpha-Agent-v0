# SPDX-License-Identifier: Apache-2.0
"""Authored probes, not utility records, physical tests or buyer requirements."""

from __future__ import annotations

import hashlib
import random
from typing import Any

from .engine import ProductionBrief


def case(domain: str, seed: int) -> ProductionBrief:
    """Generate a new finite brief without storing a successful answer."""
    rng = random.Random(seed)
    obligations = ["original-interface", "independent-acceptance", "no-inferred-authority"]

    def recipe(
        identity: str,
        consumes: dict[str, int],
        produces: dict[str, int],
        requires: list[str],
        provides: list[str],
        cost: int,
        seconds: int,
        proposed: bool = False,
    ) -> dict[str, Any]:
        return {
            "recipe_id": identity,
            "description": f"Authored {domain} model operation {identity}; no external action",
            "consumes": consumes,
            "produces": produces,
            "requires": requires,
            "provides": provides,
            "preserves": obligations,
            "permission": "research-cleared",
            "permission_basis": "Only local computation over public authored inputs is cleared; real actions are untested",
            "origin": "proposed-construction" if proposed else "conventional",
            "estimated_cost_micro_usd": cost * 1_000_000,
            "seconds": seconds,
            "sources": ["authored"],
            "acceptance": "Independent replay must conserve declared inputs and meet every original output and budget",
            "failure": "Invalid source meaning, missing real approval, physical mismatch or scarce input reused",
        }

    if domain == "transformer":
        a, b = rng.randint(1, 4), rng.randint(1, 4)
        resources = ["material", "raw-a", "raw-b", "usable-a", "usable-b"]
        stock = {"material": a + b}
        required = {"usable-a": a, "usable-b": b}
        recipes = [
            recipe("measure-a", {}, {}, [], ["interface-a"], 250, 300),
            recipe("measure-b", {}, {}, [], ["interface-b"], 250, 300),
            recipe("common-design", {}, {}, ["interface-a", "interface-b"], ["shared-spec"], 1_000, 600, True),
            recipe(
                "shared-batch",
                {"material": a + b},
                {"raw-a": a, "raw-b": b},
                ["shared-spec"],
                [],
                800 * (a + b),
                600,
                True,
            ),
            recipe(
                "conventional-batch",
                {"material": a + b},
                {"raw-a": a, "raw-b": b},
                ["interface-a", "interface-b"],
                [],
                1_500 * (a + b),
                1_200,
            ),
            recipe("accept-a", {"raw-a": a}, {"usable-a": a}, ["interface-a"], [], 200, 300),
            recipe("accept-b", {"raw-b": b}, {"usable-b": b}, ["interface-b"], [], 200, 300),
        ]
        purpose = (
            "Find a conditional joint batch serving two declared interface classes without reusing shared material"
        )
        constraint = (
            "Shared manufacturing inputs, two site interfaces and an independently checked acceptance condition"
        )
        cost_cap = rng.choice([2_000, 8_000, 15_000]) * 1_000_000
    elif domain == "metrology":
        n = rng.randint(3, 7)
        resources = ["blank", "coupon", "destructive-result", "validation-packet"]
        stock = {"blank": n}
        required = {"validation-packet": 1}
        recipes = [
            recipe("make-coupons", {"blank": n}, {"coupon": n}, [], ["build-trace"], 300 * n, 600),
            recipe(
                "image-interior", {"coupon": n}, {"coupon": n}, ["build-trace"], ["internal-measurements"], 600, 600
            ),
            recipe(
                "destructive-test",
                {"coupon": 3},
                {"destructive-result": 3},
                ["build-trace"],
                ["mechanical-measurements"],
                900,
                900,
            ),
            recipe(
                "fit-joint-model",
                {},
                {},
                ["internal-measurements", "mechanical-measurements"],
                ["joint-model"],
                400,
                600,
                True,
            ),
            recipe(
                "fresh-geometry-check",
                {"coupon": 2, "destructive-result": 3},
                {"validation-packet": 1},
                ["joint-model"],
                [],
                700,
                600,
                True,
            ),
            recipe("conventional-laboratory", {"blank": n}, {"validation-packet": 1}, [], [], 8_000, 7_200),
            recipe("reject-without-measurement", {}, {"validation-packet": 1}, ["unavailable-truth-oracle"], [], 1, 1),
        ]
        purpose = "Construct a measurement sequence that leaves fresh material for validation after destructive testing"
        constraint = "The same finite coupons cannot support two destructive uses; internal and mechanical observations complement"
        cost_cap = rng.choice([2_000, 6_000, 12_000]) * 1_000_000
    else:
        raise ValueError("unknown authored case domain")
    # Vary eligibility, numerical budgets and ordering on prospective cases.
    if seed % 7 == 0:
        recipes[rng.randrange(len(recipes))]["permission"] = "denied"
    if seed % 11 == 0:
        recipes[rng.randrange(len(recipes))]["permission"] = "required"
    rng.shuffle(recipes)
    raw = {
        "brief_id": f"{domain}-{seed}",
        "beneficiary": "A hypothetical consenting utility consortium"
        if domain == "transformer"
        else "A hypothetical AM metrology team",
        "useful_outcome": purpose,
        "binding_constraint": constraint,
        "input_mode": "authored-simulation",
        "resources": [
            {
                "resource_id": r,
                "unit": "declared discrete item",
                "meaning": f"Authored {r}; no physical interchangeability or qualification established",
            }
            for r in resources
        ],
        "stock": stock,
        "capabilities": [],
        "required_stock": required,
        "required_capabilities": [],
        "obligations": obligations,
        "recipes": recipes,
        "sources": [
            {
                "source_id": "authored",
                "uri": "urn:agi-alpha:authored-model:production-frontier/v1",
                "sha256": hashlib.sha256(f"{domain}:{seed}:authored".encode()).hexdigest(),
                "kind": "authored-assumption",
                "supports": "Only the provenance label of authored parameters",
                "does_not_establish": "Utility specifications, laboratory physics, access rights, prices or paid demand",
            }
        ],
        "cost_cap_micro_usd": cost_cap,
        "seconds_cap": rng.choice([3_600, 10_800]),
        "limitations": [
            "Finite sequential single-use batches; no scheduling concurrency, stochastic yields or real production",
            "Original relationships are represented as declarations and have not been independently translated from engineering source",
            "All quantities, durations, costs, buyer identities and recipe performance are authored assumptions",
        ],
    }
    return ProductionBrief.model_validate(raw)
