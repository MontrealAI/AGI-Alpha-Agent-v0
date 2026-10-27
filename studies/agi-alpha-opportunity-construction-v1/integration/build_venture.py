# SPDX-License-Identifier: Apache-2.0
"""Bind the selected reserve-pool study to its public research venture package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

STUDY = Path(__file__).resolve().parents[1]


def build(technical_summary: Path | None = None) -> dict[str, Any]:
    """Retain the actual selection and exact public source references without inventing results."""
    selected = json.loads((STUDY / "discovery/selected_opportunity.json").read_text())
    protocol = json.loads((STUDY / "config/technical_protocol.json").read_text(), parse_float=str)
    paths = [
        "config/discovery_initial_packet.json",
        "config/discovery_protocol.json",
        "config/discovery_round2_packet.json",
        "discovery/ordinary_search.json",
        "discovery/expert_search.json",
        "discovery/ordinary_search_round2.json",
        "discovery/expert_search_round2.json",
        "discovery/independent_candidate_review.json",
        "discovery/cross_round_synthesis_review.json",
        "discovery/selected_opportunity.json",
        "config/technical_protocol.json",
        "src/mpc_worker.py",
        "integration/query_authority.py",
        "integration/query_authority_controls.py",
        "integration/native_source_manifest.json",
    ]
    technical: dict[str, Any] = {
        "status": "pending_fresh_confirmation",
        "interpretation": "An actual local MPyC worker has been constructed. Fresh origin and successor outcomes are not asserted by this provisional package.",
        "protocol": protocol,
        "technical_result": None,
    }
    if technical_summary is not None:
        summary = technical_summary.resolve()
        if not summary.is_relative_to(STUDY) or not summary.is_file():
            raise ValueError("Technical summary must be an existing public file within this study")
        paths.append(summary.relative_to(STUDY).as_posix())
        technical["status"] = "public_result_record_attached"
        technical["interpretation"] = (
            "The supplied public technical summary is retained exactly in meaning; numeric decimals are explicit strings for the native Nova parser. Its own result labels and limitations govern every claim."
        )
        technical["technical_result"] = json.loads(summary.read_text(), parse_float=str)
        paths.extend(
            [
                "config/capability_descriptor.json",
                "evidence/technical_freeze.json",
                "integration/artifacts/authority-controls-01/controls.json",
                "integration/artifacts/recipient-access-01.json",
            ]
        )
    provenance = [
        {"path": name, "sha256": hashlib.sha256((STUDY / name).read_bytes()).hexdigest()} for name in sorted(set(paths))
    ]
    return {
        "schema": "agialpha.opportunity-construction.venture.v1",
        "title": "Confidential pre-emergency reserve-pool feasibility",
        "evidence_scope": "offline-research",
        "publication_safe": True,
        "protocol_amounts": "unfunded-encoding-only",
        "opportunity": {
            "selected_opportunity": selected,
            "technical_construction": technical,
            "query_arrangement": {
                "owner_inputs": "Three simulated owners each retain two padded asset slots. Only their own worker reads their synthetic private owner file.",
                "public_function": "For every authorized simultaneous-claim scenario, some eligible injective allocation exists after applying availability and owner withholding. The required allocation may differ across scenarios.",
                "origin": "The complete 21-scenario singleton and pair family over six public demand locations.",
                "successor": "The complete 41-scenario family including triples, with fresh input meaning and separate explicit authority.",
                "output_consent": "One aggregate bit per independent world, with declared public dimensions, scenario family, identities and communication/timing metadata. A bit can reveal private information when combined with side information.",
                "batch_boundary": "A research batch may explicitly authorize 120 independent synthetic worlds and 120 bits. The prospective bounded offering has one world and one bit per authorized epoch.",
                "authority": "Current local signed controller grant, exact source/input commitment, expiry, nonce and atomic scope/epoch reservation. Simulated identities do not establish live ENS, independent organizations or real owner consent.",
            },
            "commercial_evidence": {
                "status": "modeled_economics_separate_pending_final_record",
                "actual_customer_collections_usd": "0",
                "actual_complete_research_cost_usd": None,
                "unknown_cost_treatment": "Unknown research and hosted-model expenditure is not silently set to zero.",
                "protocol_amount_boundary": "The package's minimum token bounties and no-funding MARK arithmetic are encoding fixtures; they are not service prices, financing, earned revenue or profitable delivery.",
            },
            "supplied_protocol_terms": {
                "bounty": "100 base units per job is the existing FusionPlan schema minimum and is unfunded. No USD conversion is assumed.",
                "duration": "Seven days is a research package encoding allowance, not a measured or sold service-level promise.",
                "price_weight": "5,000 basis points is an explicit unused protocol placeholder, not an optimized commercial policy.",
            },
            "component_boundary": "Hosted blind-search records and the cross-round construction establish discovery provenance. Insight schema handling, Nova encryption and FusionPlan commitments preserve records; they do not establish discovery quality, scientific acceptance or commercial value.",
        },
        "fusion_plan_jobs": [
            {
                "goal": "Evaluate confidential reserve feasibility for the complete frozen singleton and pair scenario family.",
                "successMetric": "Every authorized independent world agrees with the separate injective-allocation oracle. Preserve all 21 scenarios and owner withholding. Open only the authorized aggregate bit per world. Report mismatches, refusals and execution costs.",
                "bounty": "100",
                "duration": 604800,
                "priceWeight": 5000,
            },
            {
                "goal": "Recheck the larger singleton, pair and triple mission and obtain fresh authority before successor execution.",
                "successMetric": "Use all 41 declared scenarios and fresh worlds. The old scope or epoch grant must fail. After separate current authorization, preserve complete oracle comparisons, ordinary-library parity and every failed case.",
                "bounty": "100",
                "duration": 604800,
                "priceWeight": 5000,
            },
            {
                "goal": "Assess a bounded planning-certificate offering for the same confidential reserve-pool computation.",
                "successMetric": "Separate willingness to pay, service price, demand, complete costs, contribution, operating profit, cash and obligations. Include failure, verification, support and financing uncertainty. No protocol funds or prior-study profits count as earned revenue.",
                "bounty": "100",
                "duration": 604800,
                "priceWeight": 5000,
            },
        ],
        "mark_curve_fixture": {
            "scope": "unfunded-integer-arithmetic-only",
            "usd_equivalent": None,
            "supply": "0",
            "count": "0",
            "base": "0",
            "slope": "0",
        },
        "provenance_files": provenance,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technical-summary", type=Path)
    parser.add_argument("--output", type=Path, default=STUDY / "config/venture.json")
    arguments = parser.parse_args()
    venture = build(arguments.technical_summary)
    arguments.output.write_text(json.dumps(venture, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "path": str(arguments.output),
                "technical_status": venture["opportunity"]["technical_construction"]["status"],
                "provenance_files": len(venture["provenance_files"]),
            }
        )
    )
