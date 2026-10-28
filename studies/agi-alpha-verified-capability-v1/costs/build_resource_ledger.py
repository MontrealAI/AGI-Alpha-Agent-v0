# SPDX-License-Identifier: Apache-2.0
"""Create an additive resource reference index; never invent an actual invoice."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def identity(relative):
    data = (ROOT / relative).read_bytes()
    return {"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def references(patterns):
    paths = set()
    for pattern in patterns:
        paths.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern)
                     if p.is_file() and "__pycache__" not in p.parts)
    return [identity(p) for p in sorted(paths)]


def record(identifier, phase, action, patterns, **known):
    return {"id": identifier, "phase": phase, "action": action,
            "actor": "assistant research team; same-session separated reviewers",
            "status": "recorded", "wall_seconds": None, "cpu_seconds": None,
            "count": None, "count_unit": None, "model_calls": None,
            "authoring_or_review_model_tokens": None,
            "active_human_minutes": None, "actual_all_in_expense_usd": None,
            "included_in_partial_compute_subtotal": False,
            "sources": references(patterns), **known}


def main():
    production = load("evidence/production-summary.json")
    market = load("evidence/market-primary/execution.json")
    costs = load("market/cost-assumptions.json")
    inherited_path = "heritage/second-investment/costs/research-resource-ledger.json"
    records = [
        record("inherited-history", "prior work", "Preserve all earlier research and its resource index without charging inherited construction twice",
               [inherited_path, "heritage/inherited-manifest.json", "heritage/preserved-results-manifest.json", "heritage/earlier-results/source-manifest.json"]),
        record("foundations-and-authority", "discovery and construction", "Inspect original papers, current source, owners and ENS rules; implement separately scoped fixture authority and typed commitments",
               ["heritage/foundations/*receipt*.json", "heritage/foundations/source-manifest.json", "src/authority.mjs", "src/commitments.mjs", "resources/authority-final.txt", "resources/commitments-final.txt"],
               count=80, count_unit="authority and commitment software controls, not fresh missions",
               live_identity_enforcement="NOT_RUN", credentials_created=0, onchain_transactions=0,
               note="Live registry/signing cost is unknown and live verification was not performed. Fixture checks are a measured subset of execution, not proof of authenticated live authority."),
        record("construction-rejected-and-repair", "construction and criticism", "Construct executable graph/registry sidecar, reject weak-registry design and repair substantive adversarial findings; retain failed candidates and unsuccessful probes",
               ["history/**/*", "review/*graph*.json", "review/*probe*.json", "review/preconfirmation-findings.json", "review/independent-campaign-review.json", "evidence/development/*qualification*.json", "evidence/development/measurement-wrapper-01/qualification.json", "evidence/development/foundation-review-certificate-copy/review-receipt.json"],
               note="Criticism, no-finding probes, corrections and checker failures are not free. Their complete model/tool/attention cost is unknown. Receipts and revisions overlap and must not be summed as independent runs."),
        record("inputs-and-composition-admission", "validation and admission", "Prepare archived exact wheels and new substantive questions; independently verify the combined workflow before fixture-scoped admission",
               ["protocol/mission-design.json", "evidence/development/mission-input-identities-01.json", "evidence/catalog/*.json", "evidence/asset-admission.json", "market/asset-bindings.json", "protocol/asset-*.json"],
               count=2, count_unit="source-bound composed assets B and C using equivalent four skills",
               note="Component validity is not composition validity. One admission dossier supports two matched selection mechanisms. Repeated selected-wheel links are not separately purchased or reconstructed assets."),
        record("reuse-and-market-controls", "software verification", "Exercise refusal, availability, freshness, revocation, tampering, relationship ablations and existing-ledger adapter invariants",
               ["evidence/reuse-controls.json", "market/validation/*", "resources/reuse-final.txt", "resources/market-final.txt"],
               count=None, note="42 reuse/ablation controls and20 market controls have different units from research outcomes and do not increase the transfer sample."),
        record("frozen-production", "executed fresh work", "One balanced four-arm campaign on15primary compositions and3separate designed root stresses",
               ["protocol/production-freeze.json", "protocol/arm-order.json", "evidence/production-summary.json", "resources/production-primary.*"],
               wall_seconds=production["elapsed_seconds"] - sum(r["elapsed_seconds"] for r in production["duplicate_requests"]),
               cpu_seconds=sum(a["cpu_seconds_total"] for a in production["arms"].values()),
               count=72, count_unit="arm evaluations on18distinct substantive missions", model_calls=0,
               included_in_partial_compute_subtotal=True,
               note="Inclusive parent, driver and waited-child CPU, setup and shared allocations counted once. Per-stage verifier, proof, hashing, retrieval, composition, tool and nested receipts are already included. Includes research custody overhead. Node startup wall and final serialization are incomplete; no inference or human attention is priced."),
        record("unchanged-request-confirmations", "cache reuse", "Recheck exact frozen sources, inputs, packet bytes and current policy for four unchanged requests",
               ["evidence/production-summary.json"],
               wall_seconds=sum(r["elapsed_seconds"] for r in production["duplicate_requests"]),
               cpu_seconds=sum(r["cpu_seconds"] for r in production["duplicate_requests"]),
               count=4, count_unit="cache confirmations; zero new completed jobs", model_calls=0,
               included_in_partial_compute_subtotal=True,
               note="Separate from fresh-transfer calibration. No repeated pip resolution or new substantive mission is credited."),
        record("frozen-market", "modeled economic continuation", "Execute exactly48predeclared cells and24paired seeds through the unchanged inherited market and canonical accounting",
               ["protocol/market-design.json", "protocol/market-freeze.json", "evidence/market-primary/execution.json", "evidence/market-primary/effect-calibration.json", "evidence/market-primary/summary.json", "resources/market-primary.*"],
               wall_seconds=market["resources"]["wallSeconds"], cpu_seconds=market["resources"]["cpuSeconds"],
               count=1152, count_unit="paired modeled worlds;3456enterprise histories", model_calls=0,
               included_in_partial_compute_subtotal=True,
               note="This is simulator execution cost, separate from the simulated enterprise costs inside its histories. Final result writing and hashing after the resource sample are not fully measured."),
        record("independent-outcome-reconciliation", "post-outcome verification", "Recompute stored certificate semantics, input and packet integrity, ledger identities and favorable/negative paths without rerunning the experiment",
               ["review/*reconciliation*.json", "review/positive-world-inspection.json"],
               note="Checker01failures are preserved as reviewer defects and corrected in new receipts; candidate and frozen outcomes remain unchanged. No new research sample is created."),
        record("publication-and-demonstration", "communication and reproducibility", "Build EN/FR artifact, figures, LaTeX/PDF, archive, manifests and source-only review contribution",
               ["paper/*receipt*.json", "demo/*receipt*.json", "demo/review/*.json"],
               note="Complete authoring, model calls, tools, browser checking, archive/persistence and publication cost is unknown. Later closing work is recorded in a dated supplement, not silently excluded or credited as benefit."),
    ]
    selected = [r for r in records if r["included_in_partial_compute_subtotal"]]
    scenario = {}
    for name, profile in costs["profiles"].items():
        multiplier = profile["multiplier"]
        scenario[name] = {arm: None if multiplier is None else sum(int(row["referenceCents"][arm] * multiplier + .5) for row in costs["rows"])
                          for arm in ["B", "C"]}
    result = {
        "schema": "agi-alpha-research-resource-accounting/v1",
        "snapshot_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": "verified-capability-accounting-01",
        "status": "OBSERVED_RESOURCE_REFERENCE_INDEX_WITH_UNKNOWN_ACTUAL_TOTAL_COST",
        "scope": "Additive reference index using the existing research-accounting schema; neither a replacement financial ledger nor a monetary invoice. All earlier artifacts remain immutable.",
        "previous_snapshot": identity(inherited_path),
        "actual_money": {"observed_customer_collections_usd": 0, "observed_new_paid_commitments_usd": 0,
                         "complete_starting_research_capital_usd": None, "complete_research_expense_usd": None,
                         "model_inference_and_tool_service_invoice_usd": None, "active_human_minutes": None,
                         "ongoing_upkeep_usd": None,
                         "note": "Zero observed collections is not zero research cost. No realized enterprise surplus, paid pilot or actual commercial return is established."},
        "model_money_separate": {"classification": "SIMULATED_SCENARIO_NOT_ACTUAL_PAYMENT", "seed_usd": 1000, "reserve_usd": 200,
                                 "historical_opening_cost_usd": 361.52, "first_asset_adoption_usd": 32.69,
                                 "second_oneoff_cents": scenario,
                                 "reference_weekly_cents": {"B": 25, "C": 40},
                                 "actual_complete_cost_usd": None,
                                 "source_identities": references(["market/cost-assumptions.json", "market/inherited/PROVENANCE.json", "market/inherited/upstream/canonical/*.mjs", "protocol/market-design.json", "protocol/market-freeze.json"]),
                                 "note": "Low/reference/high allocations are complete-category assumptions, not invoices or empirical bounds. The inherited first-asset history is charged once; research already constructed outside the simulated firm is deducted once from complete project profit, never relabeled enterprise cash. Missing costs remain null."},
        "distinct_action_counts": {"new_source_bound_composed_assets": 2, "component_skills_available_to_B_and_C": 4,
                                   "relationship_rows_available_to_B_and_C": 4, "fresh_primary_questions": 15,
                                   "separate_designed_stress_questions": 3, "fresh_arm_evaluations": 72,
                                   "unchanged_request_confirmations": 4, "new_jobs_from_unchanged_requests": 0,
                                   "market_campaigns": 1, "paired_market_worlds": 1152, "modeled_enterprise_histories": 3456,
                                   "new_customer_orders": 0,
                                   "warning": "Different and overlapping units; do not sum into a workload or independent sample count."},
        "partial_observed_compute_subtotal": {
            "label": "PARTIAL_OBSERVED_COMPUTE_ONLY_NOT_TOTAL_RESEARCH_COST",
            "records": [r["id"] for r in selected],
            "nonoverlapping_selected_intervals": True,
            "wall_seconds_sum": sum(r["wall_seconds"] for r in selected),
            "inclusive_cpu_seconds_sum": sum(r["cpu_seconds"] for r in selected),
            "monetary_value_usd": None,
            "excludes": "All construction/rejected work/criticism/model calls/tool service invoices/source acquisition/authoring/attention and additional checks not included in selected inclusive receipts; unmeasured startup/final serialization. Do not add nested timings or other agents' overlapping windows."},
        "accounting_rules": [
            "Unknown actual money, model calls/tokens or labor stays null, never zero.",
            "Zero model calls applies only to executed deterministic production and simulation, not this research/engineering effort.",
            "Discovery, failed criticism, rejected candidates, repair, validation, identity, indexing, proofs, retrieval, composition, revalidation, storage and maintenance remain accounted-for categories even when their actual prices are unknown.",
            "Measured inclusive execution is marginal production evidence; recurring scenarios and fully loaded costs are separate.",
            "No double counting asset construction across production, investment and historical ledgers.",
            "Finite resource envelopes were declared before outcomes; no new capital or future borrowing is introduced.",
            "Post-outcome publication and checking do not change frozen outcomes or create customer demand.",
            "Final packaging, persistence and publication after this snapshot require a dated closing supplement outside the immutable archive."],
        "records": records,
    }
    destination = ROOT / "costs/research-resource-ledger.json"
    with destination.open("x") as output:
        output.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"path": str(destination), "sha256": identity(str(destination.relative_to(ROOT)))["sha256"],
                      "selected_cpu_seconds": result["partial_observed_compute_subtotal"]["inclusive_cpu_seconds_sum"],
                      "actual_complete_cost": None}))


if __name__ == "__main__":
    main()
