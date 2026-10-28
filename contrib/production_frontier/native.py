# SPDX-License-Identifier: Apache-2.0
"""Unsaved research proposals in the existing Opportunity schema, never grants."""

from __future__ import annotations

from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_discovery import Opportunity
from alpha_factory_v1.core.runtime.successor.flywheel_frontier import FrontierConnector
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.transformation import DiscoveryRequest
from alpha_factory_v1.core.runtime.successor.trust import SignedEnvelope

from .engine import ConstructionPolicy, ProductionBrief, construct


def proposal(brief: ProductionBrief) -> Opportunity:
    """Construct an unsaved proposal; referenced records still require real custody."""
    report = construct(brief)
    ref = {
        "journal_key": "@production-frontier-proposal:" + brief.brief_id,
        "record_digest": digest("production-frontier-research-artifact/v1", report),
    }
    ingredients = [
        {
            "ingredient_id": r.recipe_id,
            "description": r.description,
            "origin": "constructed" if r.origin == "proposed-construction" else "established-method",
            "evidence": [ref],
            "limitations": "Authored recipe semantics and prices; local witness conformance is not engineering acceptance",
        }
        for r in brief.recipes
    ]
    return Opportunity.model_validate(
        {
            "opportunity_id": brief.brief_id,
            "version": 1,
            "purpose": {
                "useful_purpose": brief.useful_outcome,
                "deliverable": "Exact-input conditional construction, conventional comparison and ablation witnesses",
                "acceptance_criteria": [
                    "Conserve every declared resource",
                    "Meet original outputs and obligations",
                    "Recheck all real-world semantics, grants and buyer acceptance independently",
                ],
                "input_semantics": "Finite typed stock and single-use recipes with explicit costs, evidence and permission declarations",
                "output_semantics": "A research witness only, no production or qualification authority",
                "scope": "Finite sequential declared-model simulation",
            },
            "needs": [
                {
                    "need_id": "need-" + brief.brief_id,
                    "beneficiary": brief.beneficiary,
                    "independently_motivated_purpose": brief.useful_outcome,
                    "outside_option": "Competent conventional engineer/laboratory and exhaustive search of the same finite grammar",
                    "evidence": [ref],
                    "evidence_kind": "synthetic",
                    "demand_uncertainty": "No authorized buyer brief, quotation or purchase; public context is not buyer demand",
                }
            ],
            "limiting_assumptions": brief.limitations,
            "shared_structure_hypothesis": brief.binding_constraint,
            "formulations": [
                {
                    "formulation_id": "joint-construction",
                    "approach": "Backward dependency search joined to resource-conserving forward construction",
                    "material_difference": "Quantitative stock and complementary capability requirements replace monotone availability labels",
                    "assumptions": brief.limitations,
                    "dependencies": [r.recipe_id for r in brief.recipes],
                    "uncertainty": "Recipe truth, buyer value and field performance unverified",
                },
                {
                    "formulation_id": "conventional-control",
                    "approach": "Conventional exhaustive enumeration with independent witness replay under identical inputs",
                    "material_difference": "Different search implementation; the same information and recipes are available",
                    "assumptions": brief.limitations,
                    "dependencies": [r.recipe_id for r in brief.recipes],
                    "uncertainty": "A finite tie does not establish field or discovery advantage",
                },
            ],
            "ingredients": ingredients,
            "unresolved_questions": [
                "Do independently reviewed real requirements fit this finite model without losing essential relationships?",
                "Does a supplier-confirmed shared arrangement improve an actual buyer's outside option?",
            ],
            "mode": "simulation",
        }
    )


class LiveAdapter:
    """Use the one existing frontier authorization boundary, with no fallback."""

    def __init__(self, connector: FrontierConnector | None = None) -> None:
        if connector is not None and type(connector) is not FrontierConnector:
            raise TypeError("live execution requires the existing exact FrontierConnector")
        self.connector = connector

    def status(self) -> dict[str, Any]:
        if self.connector is None:
            return {
                "adapter": "existing-authorized-frontier",
                "ready_for_signed_permit": False,
                "blockers": [
                    "No current approved FrontierConnector, signed mission, quota, tariff or liability tuple supplied"
                ],
                "simulated_fallback": False,
            }
        return {"adapter": "existing-authorized-frontier", **self.connector.status(), "simulated_fallback": False}

    def run(self, request: DiscoveryRequest, signed: SignedEnvelope) -> dict[str, Any]:
        if self.connector is None:
            raise ValueError("live frontier access unavailable; simulation requires a separate explicit call")
        return self.connector.run(request, signed)


def simulate(brief: ProductionBrief, policy: ConstructionPolicy | None = None) -> dict[str, Any]:
    """An explicit authored-model adapter, never calibrated frontier performance."""
    return construct(brief, policy)
