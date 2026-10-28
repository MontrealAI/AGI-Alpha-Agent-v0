# SPDX-License-Identifier: Apache-2.0
"""Assemble reviewable claim records from archived executed evidence.

This does not run experiments, select commercial assumptions, or grant authority.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def read(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text())


def write(relative: str, value: Any) -> None:
    (ROOT / relative).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    scientific = read("results/confirmation_v2/scientific_summary.json")
    economics = read("economics/confirmation-v2/SUMMARY.json")
    protocols = read("configs/scientific_protocol_v2.json")
    for name, digest in protocols["source_sha256"].items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"Frozen scientific method changed: {name}")
    base = {r["policy"]: r for r in economics["confirmation"] if r["scenario"] == "base"}
    qualified = base["qualified_instrument_449"]
    gate = base["commitment_gated_449"]
    claims = [
        {"id": "I-correctness", "class": "measured", "status": "passed_in_declared_envelope",
         "claim": "Finite exact counts, rank/unrank, and concentration-conditioned outputs pass the frozen tiny-case oracle.",
         "values": {k: scientific["small"][k] for k in ["cases", "exhaustive_bijections", "conditioned_output_checks", "all_match"]},
         "evidence": ["results/confirmation_v2/confirmation.json", "configs/scientific_protocol_v2.json"],
         "limits": "Authored synthetic cases; internal independent implementation, not external peer review or a general performance proof."},
        {"id": "I-production", "class": "measured", "status": "constructed",
         "claim": "Twelve larger synthetic cases completed, with 100 accepted tables per case.",
         "values": {"larger_cases": len(scientific["performance"]), "accepted_tables": 1200,
                    "independent_counts_during_confirmation": 11,
                    "independent_counts_after_adapted_ordering_challenge": 1},
         "evidence": ["results/confirmation_v2/performance.json", "alternatives/ordering/ordering_results.json"],
         "limits": "Do not rewrite the confirmation as twelve contemporaneously corroborated counts. Timings are single local observations."},
        {"id": "I-useful-delivery", "class": "measured", "status": "accepted_computationally",
         "claim": "The separate example delivers 1,000 tables plus the reusable 20,322-world instrument.",
         "evidence": ["results/delivery_example/receipt.json", "results/delivery_example/delivery_acceptance.json"],
         "limits": "Not a paying customer or a new confirmation sample."},
        {"id": "I-novelty", "class": "unestablished", "status": "not_qualified",
         "claim": "Consequential algorithmic novelty or general superiority over the strongest prior art is not established.",
         "evidence": ["scientific_review.md", "results/confirmation_v2/published_comparator.json",
                      "alternatives/ordering/ordering_review.md"],
         "limits": "Miller-Harrison prior art supplies counting, symmetry, and count-guided uniform sampling. A row-order repair removes the conspicuous apparent time-budget advantage."},
        {"id": "II-unit-contribution", "class": "simulated", "status": "positive_under_assumptions",
         "claim": "The USD449 qualified-instrument policy has positive contribution per retained accepted order.",
         "values": {"mean_usd": qualified["mean_contribution_per_net_accepted_order_cents"] / 100},
         "evidence": ["economics/confirmation-v2/SUMMARY.json"],
         "limits": "Mean of per-world ratios; excludes fixed costs. Price, buyer behavior and demand are assumptions."},
        {"id": "II-enterprise", "class": "simulated", "status": "failed",
         "claim": "Complete-cost enterprise profit and sustained operation fail in the fresh worlds.",
         "values": {"mean_base_project_profit_usd": qualified["mean_aftertax_project_profit_cents"] / 100,
                    "loss_frequency": qualified["loss_frequency"],
                    "full_horizon_operation_frequency": qualified["full_horizon_operation_frequency"],
                    "mean_cash_end_usd": qualified["mean_cash_end_cents"] / 100},
         "evidence": ["economics/confirmation-v2/SUMMARY.json", "ECONOMICS.md"],
         "limits": "Synthetic participants. Early closure preserves reserves; zero insolvency is not sustainable cash generation. Historical research cost is unmeasured."},
        {"id": "II-revision", "class": "simulated", "status": "loss_contained_no_enterprise",
         "claim": "Paid contingent-cohort search lowers loss but never launches in the base confirmation.",
         "values": {"base_worlds": gate["worlds"], "launch_frequency": gate["launch_frequency"],
                    "mean_project_profit_usd": gate["mean_aftertax_project_profit_cents"] / 100,
                    "conditional_on_launch_mean_profit": gate["conditional_on_launch_mean_profit_cents"]},
         "evidence": ["economics_config_revision.json", "economics/confirmation-v2/SUMMARY.json"],
         "limits": "No launch-conditioned profit exists; null is not zero profit. No commitment is real."},
        {"id": "II-real-money", "class": "measured_execution_scope", "status": "none",
         "claim": "No real customer, contract, purchase, outreach, or receipt was executed.",
         "values": {"actual_customers": 0, "actual_revenue_usd": 0,
                    "actual_complete_cost_usd": None, "actual_profit_usd": None},
         "evidence": ["results/delivery_example/receipt.json", "economics/confirmation-v2/SUMMARY.json"],
         "limits": "Actual session/API and historical labor cost are unavailable, not assumed zero."},
        {"id": "III-inheritance", "class": "measured", "status": "useful_but_no_comparative_advantage",
         "claim": "The inherited instrument produces 400 fresh conditioned outputs, but cold all-statistics reuse is slower than fresh conventional construction in both sizes.",
         "values": [{"columns": len(r["problem"]["cols"]), "cold_seconds": r["cold_inherited_query_seconds"],
                     "fresh_seconds": r["direct_all_statistics_seconds"],
                     "same_asset_conventional_match": r["same_asset_conventional_match"]}
                    for r in scientific["successor"]],
         "evidence": ["results/confirmation_v2/successor.json"],
         "limits": "Same-asset control reuses the same code; independent conventional distribution computation is a separate control. No economic transfer revenue assumed."},
        {"id": "alternative-matrix-action", "class": "measured", "status": "not_qualified",
         "claim": "The matrix-action alternative produces valid numerical outputs, but stronger available bounds remove its proposed new advantage.",
         "values": {"cases": 144, "wins_against_strong_portfolio": 0, "ties": 92, "losses": 52},
         "evidence": ["alternatives/matrix_action/matrix_probe_assessment.json",
                      "alternatives/matrix_action/negative_assessment.md"],
         "limits": "Comparison to a numerical reference is not a full floating-point error certificate. The October complete matrix-valued theorem is not required by this scalar-function workload."},
        {"id": "frontier-causality", "class": "unestablished", "status": "not_tested",
         "claim": "No controlled evidence attributes a new practical advantage to the latest model release.",
         "evidence": ["research/sources.json", "research/findings.md"],
         "limits": "Vendor prices and benchmarks are source facts, not our invoice or an old/new-model comparison."},
    ]
    write("claim_register.json", {"schema": "agi-alpha-claim-register-v1", "date": "2026-10-28",
                                  "flagship_qualified": False, "claims": claims})

    tasks = []
    for record in scientific["performance"]:
        tasks.append({"task": record["problem"]["name"], "acceptance": "exact count plus 100 feasible generated tables",
                      "budget": {"seconds_per_count_method": 30, "states": 100000, "transitions": 1500000},
                      "measured_methods": record["methods"],
                      "global_novelty": False, "commercial_demand_observed": False,
                      "interpretation": "A comparator budget crossing is relative to the named implementation; see adapted row-order challenge for capacity_20_variant_2."})
    write("opportunity_frontier.json", {
        "schema": "agi-alpha-opportunity-frontier-v1", "scope": "bounded synthetic computational contracts",
        "consequential_frontier_expansion_established": False, "economic_compounding_established": False,
        "tasks": tasks, "successor_evidence": "results/confirmation_v2/successor.json",
        "commercial_evidence": "economics/confirmation-v2/SUMMARY.json",
        "post_confirmation_challenge": "alternatives/ordering/ordering_review.md"})
    write("nova_seed.json", {
        "schema": "agi-alpha-exploratory-nova-seed-v1", "program": "AGI ALPHA",
        "candidate": "Exact bounded-world instruments", "admitted": False, "launch_authorized": False,
        "productive_future": "Scientific and engineering workflows construct affordable families of feasible worlds and condition them on new questions.",
        "kernel": "Future-cap-signature count graph with labeled multiplicities and exact rank intervals.",
        "essential_product": "Executable exact ensemble and reusable generation instrument, not only advice about sampling.",
        "available_asset": "kernel.py and product/index.html",
        "claims": "claim_register.json", "complete_economics": "economics/confirmation-v2/SUMMARY.json",
        "reasons_not_admitted": ["Substantive novelty over conventional methods unestablished",
                                 "All tested active-launch histories lose money",
                                 "Cold successor reuse loses to fresh conventional construction",
                                 "No observed willingness to pay or billion-dollar reachable market"],
        "real_financial_authority": "none", "actual_revenue_usd": 0})
    write("fusion_plan.json", {
        "schema": "agi-alpha-execution-record-v1", "date": "2026-10-28", "status": "executed_not_qualified",
        "author": "Vincent Boucher, President of MONTREAL.AI",
        "repository_base": "12770c22b4a9f90f2013bbfb64242f912ba5071e",
        "completed": ["Dated frontier and prior-art review", "Separate bounded kernel and conventional comparators",
                      "Loader repair before completed confirmation", "Frozen scientific v2 execution",
                      "Stateful economic campaign, rejection, controlled revision, fresh confirmation",
                      "Fresh successor queries with cold costs and equal-asset control",
                      "Matrix-action alternative execution and stronger-prior-art rejection",
                      "Charged post-confirmation row-order challenge", "Bilingual offline product and Chromium acceptance",
                      "1,000-table complete example delivery", "LaTeX manuscript and reproducibility assembly"],
        "preserved_failures": ["results/science_v1_disposition.json", "archive/science_v1/",
                               "economics/confirmation-v1/", "economics/AUDIT_COUNT_CORRECTION.json",
                               "alternatives/matrix_action/negative_assessment.md"],
        "result": "Retain the research instrument and evidence; no qualified profitable flagship.",
        "next_evidence_needed": ["A productive advantage surviving strong conventional controls",
                                 "Observed accepted demand at complete-cost prices",
                                 "A successor advantage after complete transfer and maintenance costs"],
        "canonical_deployment": False, "merge_or_release_claim": False,
        "real_commercial_actions": [], "actual_revenue_usd": 0})
    print("Verified frozen scientific hashes and assembled four evidence records.")


if __name__ == "__main__":
    main()
