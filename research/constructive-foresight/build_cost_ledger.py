# SPDX-License-Identifier: Apache-2.0
"""Reconstruct research costs from retained measurements, never from assumed work."""
import csv
import gzip
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


def evidence(path):
    return {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def child_cpu(record):
    if "child_cpu_seconds" in record:
        return float(record["child_cpu_seconds"])
    return float(record["child_user_cpu_seconds"]) + float(record["child_system_cpu_seconds"])


entries = []
for phase in ("calibration", "confirmation"):
    path = f"results/{phase}/summary.json"
    record = read(path)
    entries.append({
        "id": "numerical-" + phase, "scope_complete": True,
        "scope": "Numerical phase body, including ingestion, batches, generation, retained output and CG diagnostics.",
        "wall_seconds": record["wall_seconds"], "cpu_seconds": record["cpu_seconds"],
        "excluded": "Interpreter startup/shutdown and final summary serialization after the timing sample.",
        "batches": record["executed_batches"], "evidence": [evidence(path)],
    })
external_records = [
    ("native-initial-and-restoration-demo", "evidence/native-demo-001-process.json"),
    ("decision-calibration", "evidence/decision-calibration-invocation.json"),
    ("decision-confirmation", "evidence/decision-confirmation-invocation.json"),
    ("independent-numerical-audit-v1", "evidence/independent-numerical-audit-cost.json"),
    ("independent-numerical-audit-v2", "evidence/independent-numerical-audit-v2-cost.json"),
    ("independent-decision-audit", "evidence/independent-decision-audit-cost.json"),
]
if (ROOT / "evidence/numerical-controls-process.json").exists():
    external_records.append(("post-confirmation-numerical-controls", "evidence/numerical-controls-process.json"))
for label, path in external_records:
    record = read(path)
    entries.append({
        "id": label, "scope_complete": True,
        "scope": "Externally measured whole child process, including startup/shutdown and waited descendants.",
        "wall_seconds": float(record["wall_seconds"]), "cpu_seconds": child_cpu(record),
        "excluded": "Authoring, review and other processes outside this invocation.",
        "evidence": [evidence(path)],
    })
development = [
    json.loads(line) for line in (ROOT / "results/development/batches.jsonl").read_text().splitlines()
]
entries.append({
    "id": "numerical-development-retained-batches", "scope_complete": False,
    "scope": "Retained36batch intervals only; lower bound for the failed-summary engineering phase.",
    "wall_seconds": math.fsum(row["total_seconds"] for row in development),
    "cpu_seconds": math.fsum(row["cpu_seconds"] for row in development),
    "full_phase_wall_seconds": None, "full_phase_cpu_seconds": None,
    "excluded": "Unretained phase overhead and CG diagnostic measurements; summary serialization failed.",
    "evidence": [evidence("results/development/summary.json"),
                 evidence("results/development/batches.jsonl"), evidence("amendments/A03_engineering_serialization.json")],
})
for label in ("harness-engineering-003", "harness-negative-001"):
    path = f"evidence/{label}/native-receipt.json"
    record = read(path)
    entries.append({
        "id": label, "scope_complete": False,
        "scope": "Measured native run_harness body; lower bound for the complete engineering process.",
        "wall_seconds": float(record["elapsed_seconds"]), "cpu_seconds": float(record["cpu_seconds"]),
        "excluded": "Startup/shutdown, later receipt serialization and any separate bridge invocation.",
        "handler_counts": record["handler_counts"], "evidence": [evidence(path)],
    })
for label in ("decision", "decision-v2"):
    summary_path = f"engineering/{label}/decision_summary.json"
    rows_path = f"engineering/{label}/decision_observations.csv.gz"
    record = read(summary_path)
    with gzip.open(ROOT / rows_path, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    preparation = float(record["preparation_cpu_seconds"])
    controller = math.fsum(float(row["decision_cpu_seconds"]) for row in rows)
    evaluator = math.fsum(float(row.get("offline_evaluator_cpu_seconds", 0)) for row in rows)
    entries.append({
        "id": "engineering-" + label, "scope_complete": False,
        "scope": "Disjoint model-preparation CPU once plus controller/offline-evaluator CPU; process lower bound.",
        "wall_seconds": math.fsum(float(row["decision_wall_seconds"]) for row in rows),
        "cpu_seconds": preparation + controller + evaluator,
        "components": {"model_preparation_cpu_once": preparation, "controller_cpu": controller,
                       "offline_evaluator_cpu": evaluator},
        "excluded": "World generation, simulation outside policy timers, summarization, serialization and startup/shutdown.",
        "evidence": [evidence(summary_path), evidence(rows_path)],
    })
complete = [entry for entry in entries if entry["scope_complete"]]
partial = [entry for entry in entries if not entry["scope_complete"]]
totals = {
    "complete_named_scope_wall_work_seconds": math.fsum(e["wall_seconds"] for e in complete),
    "complete_named_scope_cpu_seconds": math.fsum(e["cpu_seconds"] for e in complete),
    "additional_documented_partial_scope_wall_work_seconds": math.fsum(e["wall_seconds"] for e in partial),
    "additional_documented_partial_scope_cpu_seconds": math.fsum(e["cpu_seconds"] for e in partial),
    "documented_wall_work_lower_bound_seconds": math.fsum(e["wall_seconds"] for e in entries),
    "documented_cpu_lower_bound_seconds": math.fsum(e["cpu_seconds"] for e in entries),
    "complete_study_wall_seconds": None, "complete_study_cpu_seconds": None, "complete_study_monetary_cost": None,
    "interpretation": "Named disjoint work scopes. Parallel wall intervals are work sums, not session latency. Unknown costs are not zero.",
}
failures = [
    {"id": "native-proof-enum-failure", "expected": False, "wall_seconds": None, "cpu_seconds": None,
     "evidence": evidence("evidence/harness-engineering-001/FAILURE.json")},
    {"id": "native-proof-decimal-failure", "expected": False, "wall_seconds": None, "cpu_seconds": None,
     "evidence": evidence("evidence/harness-engineering-002/FAILURE.json")},
    {"id": "development-summary-serialization", "expected": False,
     "cost_accounting": "Included retained batch lower bound; remaining cost unknown.",
     "evidence": evidence("amendments/A03_engineering_serialization.json")},
    {"id": "GNU-time-launcher-unavailable", "expected": False, "wall_seconds": None, "cpu_seconds": None,
     "cost_accounting": "Exited127 before audit execution; fallback audit measured separately.",
     "evidence": evidence("evidence/independent-numerical-audit-cost.json")},
    {"id": "pattern-only-matrix-candidate-rejected", "expected": False, "wall_seconds": None, "cpu_seconds": None,
     "evidence": evidence("data/rejected_source.json")},
    {"id": "intentional-corrupt-solution-refusal", "expected": True,
     "cost_accounting": "Already included in harness-negative-001; not added again.",
     "evidence": evidence("evidence/harness-negative-001/native-receipt.json")},
]
unknown = [
    "Authoring inference token counts and provider charges, including agent and subagent reasoning",
    "Source/literature searches, information acquisition and failed download attempts",
    "Engineering labor and supervision, including failed native proof construction",
    "Human review, required external review and beneficiary acceptance effort",
    "Future maintenance and opportunity costs",
    "Figure generation, typesetting, page inspection, publication and packaging outside listed processes",
    "Unretained development overhead and process startup/shutdown outside numerical phase timers",
    "Additional unmetered read-only analysis, primary-stratum arithmetic review and ledger construction",
]
accounting = [
    "Numerical phase totals include factorization, preflight, solve, validation, RHS formation, metadata, orchestration and retained CG diagnostics; never add their subcomponents again.",
    "rhs_generation_shared_seconds repeats in every row of a matrix/block. Count it once in a component audit, never once per row and never on top of phase totals.",
    "The external native-demo timer includes initial proof, restored proof, numerical checking, Node bridge, dispatch and actual restoration; all internal segment timers are nested evidence only.",
    "Decision process timers include actual fitting, policy calculation, simulation, bootstrap and output. Per-policy preparation allocations and simulated compute fields are not additional actual spending.",
    "Simulation failed_compute_seconds and late_numerical_wall_seconds are subsets of charged work, not extra charges.",
    "Independent numerical audits v1/v2 are separate actual inspections and both are included; neither re-runs a solver.",
]
diagnostics = []
for phase in ("calibration", "confirmation"):
    for row in read(f"results/{phase}/summary.json")["cg_diagnostics"]:
        diagnostics.append({
            "phase": phase, "matrix": row["matrix"], "solver_info": row.get("info"),
            "overall_qualified": row.get("overall_qualified", row.get("qualified") and row.get("qualified_solver_exit")),
            "wall_seconds": row["elapsed_seconds"], "cpu_seconds": row["cpu_seconds"],
            "inclusion": f"Inside numerical-{phase}; diagnostic only; not added again.",
        })
decision_summary = read("results/decision-confirmation/decision_summary.json")
ledger = {
    "schema": "writer9-research-cost-ledger/v1", "created_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Recorded research through numerical/decision studies, native restoration and named audits; not a complete session bill.",
    "units": {"wall_seconds": "Measured wall intervals summed as work, not end-to-end session duration.",
              "cpu_seconds": "Measured process or child CPU within the named scope.",
              "assumed_seconds": "Counterfactual service, information and alternative-cost inputs, not extra real CPU consumed.",
              "money": "No conversion from seconds or mission credits to currency."},
    "entries": entries, "totals": totals, "failures_and_negative_controls": failures,
    "cg_diagnostics_already_included": diagnostics, "no_double_counting": accounting,
    "unknown_costs": [{"category": text, "native_quantity": None, "monetary_value": None} for text in unknown],
    "native_quantities": {
        "matrix_archives_bytes": sum((ROOT / "data" / r["file"]).stat().st_size for r in read("data/manifest.json")["matrices"]),
        "numerical_engineering_batches": 36, "numerical_calibration_batches": 288,
        "numerical_confirmation_batches": 432, "confirmation_logged_rhs_checks": 3024,
        "independently_recomputed_confirmation_columns": 24, "simulated_confirmation_rows": 32256,
        "simulated_paired_worlds": 4608, "inference_calls_inside_executable_study": 0,
        "authoring_inference_calls": None, "onchain_transactions_submitted": 0, "gas_paid_native_units": 0,
    },
    "model_costs": {
        "evidence_class": "Assumed counterfactual values using measured numerical runtime samples.",
        "clock_seconds": decision_summary["clock_seconds"], "request_credit": 1.0,
        "cost_credit_per_clock_unit": 1.0, "monetary_conversion": None,
        "linear_service_assumption": "q=16 per-RHS runtime applied to assumed request counts; independently resampled stage costs.",
        "preparation_rule": "Full fitted-model preparation CPU allocated to each hypothetical independently deployed model-using policy over4608worlds; no claim of additional actual fit runs.",
        "unobserved": ["customer demand", "adoption", "competition", "imitation", "request value", "future maintenance"],
    },
    "cash_and_value": {
        "recorded_paid_commitments": 0, "recorded_financial_transactions": 0, "recorded_payment_receipts": 0,
        "complete_cash_spend_usd": None, "recognized_external_revenue_usd": 0,
        "note": "No recorded purchase/payment does not establish that hosted inference, labor or infrastructure was free.",
        "full_cost_mission_alpha_established": False,
    },
}
(ROOT / "COST_LEDGER.json").write_text(json.dumps(ledger, indent=2, allow_nan=False) + "\n")
lines = [
    "# Cost ledger", "",
    "This ledger reconstructs recorded research costs. **Full study cost is unknown.** Authoring inference, labor, review, maintenance and opportunity costs remain null. No profit or monetary Mission Alpha follows from the measured compute intervals.", "",
    "## Recorded scopes", "",
    "| Scope | Wall work (s) | CPU (s) | Coverage |", "|---|---:|---:|---|",
]
for entry in entries:
    coverage = "Complete named timer scope" if entry["scope_complete"] else "Partial measurement; lower bound"
    lines.append(f"| {entry['id']} | {entry['wall_seconds']:.6f} | {entry['cpu_seconds']:.6f} | {coverage} |")
lines += [
    "",
    f"Complete named timer scopes total **{totals['complete_named_scope_wall_work_seconds']:.6f} wall-work seconds** and **{totals['complete_named_scope_cpu_seconds']:.6f} CPU seconds**. Adding documented, disjoint partial measurements gives lower bounds of **{totals['documented_wall_work_lower_bound_seconds']:.6f} wall-work seconds** and **{totals['documented_cpu_lower_bound_seconds']:.6f} CPU seconds**. These are work sums, not the elapsed session duration.",
    "",
    "The numerical phase timers exclude startup/shutdown and final summary serialization. The development run completed36batches and then failed serializing environment metadata; only batch costs are recoverable. Its full phase cost and diagnostic outcomes remain unavailable. The two failed native proof constructions also lack complete timing records.",
    "",
    "The native initial-and-restoration demo uses its full external **6.551944s wall /6.427498s CPU** measurement. Initial and restored checks, dispatch, Node bridge and restoration segments are already inside that timer.",
    "",
    "## No double counting", "",
]
lines += ["- " + text for text in accounting]
lines += ["", "## Unknown costs", ""]
lines += ["- " + text + ": **null; unmeasured**." for text in unknown]
lines += [
    "",
    "## Measured work versus modeled value", "",
    f"The decision model uses a single **{decision_summary['clock_seconds']:.12f}s clock unit**, one assumed credit per qualified on-time request, and one assumed cost credit per clock unit. Service-time resampling, information cost and competitor build shares describe model counterfactuals. They are not additional measured CPU consumption, customer spending or currency.",
    "",
    "Per-policy preparation allocations represent independently deploying each hypothetical policy. Actual research spending includes the model fit once in each measured process. Failure and late-work columns identify subsets already charged.",
    "",
    "Retained failures include both native proof-construction errors, the development summary error, missing GNU-time launcher, rejected pattern-only matrix, intentional corrupted solution and every retained CG diagnostic. Expected refusals and simulated late requests are not observed customer failures.",
    "",
    "No paid commitment, financial transaction, on-chain transaction or payment receipt was recorded for this study. Complete cash spending is unknown because authoring inference and infrastructure are not invoiced here. Recognized external revenue is zero; external beneficiary acceptance and full-cost Mission Alpha are unestablished.",
    "",
    "Every included measurement's file and SHA-256 appear in [COST_LEDGER.json](COST_LEDGER.json). Rebuild the snapshot by running python build_cost_ledger.py. Scientific outcomes are read only.",
]
(ROOT / "COST_LEDGER.md").write_text("\n".join(lines) + "\n")
print(json.dumps({"entries": len(entries), "totals": totals}))
