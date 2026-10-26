"""Read-only audit of preserved primary outputs; does not execute any solver.

Writes receipts to audit-final/ unless --output-dir is provided.  Numerical
verification is a replay on the original preserved vectors, not a replacement
primary run or an additional case.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audit-final"
ARMS = "ABCD"
FAMILIES = ("forward", "inverse", "design")


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reverify-preserved-vectors", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUT,
                        help="Directory for the new audit receipt (default: audit-final/).")
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    primary = ROOT / "evidence/primary"
    if not (primary / "summary.json").exists():
        raise SystemExit("PRIMARY_NOT_COMPLETE: summary.json is required before audit")
    started = time.perf_counter()
    issues, checks, historical_path_mappings = [], Counter(), []

    def check(ok, code, detail=None):
        checks[code] += 1
        if not ok:
            issues.append({"code": code, "detail": detail})

    def file_identity(base, record, code):
        p = base / record["path"]
        check(p.exists() and sha(p) == record["sha256"] and p.stat().st_size == record["bytes"], code, record["path"])

    freeze_path = ROOT / "protocol/production-freeze.json"
    freeze = read(freeze_path)
    for f in freeze["files"]:
        file_identity(ROOT, f, "production_source_identity")
    runtime = read(ROOT / "protocol/runtime-source.json")
    for f in runtime["files"]:
        file_identity(ROOT, f, "runtime_source_identity")
    # Workbench's sourceHash is SHA256(JSON.stringify(parsed manifest)), not
    # the hash of the indented manifest file and not sorted-key canonical JSON.
    runtime_hash = hashlib.sha256(json.dumps(runtime, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    corpus_root = ROOT / "workloads/primary"
    corpus = read(corpus_root / "cohort-manifest.json")
    check(corpus["source_freeze_sha256"] == sha(freeze_path), "corpus_binds_source_freeze")
    check(corpus["chain_count"] == 12 and corpus["stage_count"] == 36 and corpus["arm_stage_maximum"] == 144, "corpus_census")
    for f in corpus["files"]:
        file_identity(corpus_root, f, "corpus_file_identity")
    summary = read(primary / "summary.json")
    records = [json.loads(line) for line in (primary / "records.jsonl").read_text().splitlines() if line]
    required = {(f"P{i:02d}", family, arm) for i in range(1, 13) for family in FAMILIES for arm in ARMS}
    keys = [(r["chain"], r["family"], r["arm"]) for r in records]
    check(len(keys) == 144 and len(set(keys)) == 144 and set(keys) == required, "all_144_planned_rows_once")
    by_key = dict(zip(keys, records))
    check(summary["chains"] == 12 and summary["planned_stages"] == 36, "summary_planned_units")
    check(summary["observed_collections"] == 0 and summary["identity"] == "FIXTURE_ONLY" and summary["live_authentication"] == "NOT RUN", "research_identity_and_receipts")
    expected_order = []
    for stage, family in enumerate(FAMILIES):
        for index in range(12):
            order = ARMS[(index + stage) % 4:] + ARMS[:(index + stage) % 4]
            expected_order.extend((f"P{index+1:02d}", family, arm) for arm in order)
    check(keys == expected_order, "predeclared_latin_execution_order")

    seal_path = primary / "inverse-outcomes-seal.json"
    seal = read(seal_path)["inverse_outcomes"]
    seal_keys = [(r["task_id"], r["arm"]) for r in seal]
    expected_seal = {(f"P{i:02d}-INVERSE", arm) for i in range(1, 13) for arm in ARMS}
    check(len(seal_keys) == 48 and len(set(seal_keys)) == 48 and set(seal_keys) == expected_seal, "sealed_inverse_census")
    for item in seal:
        if (item["task_id"], item["arm"]) not in expected_seal:
            continue
        # Historical receipts may preserve the original absolute workspace.
        # Never open that external path after extraction.  Only map the exact
        # predeclared chain/arm result suffix into this companion's study root.
        # The receipt and every original file hash remain unchanged.
        original = Path(item["result_path"])
        expected_relative = Path("evidence/primary") / item["task_id"].split("-")[0] / "inverse" / item["arm"] / "result.json"
        expected_path = ROOT / expected_relative
        if original.is_absolute():
            suffix_matches = ".." not in original.parts and tuple(original.parts[-len(expected_relative.parts):]) == expected_relative.parts
        else:
            suffix_matches = ".." not in original.parts and (
                original == expected_relative or
                (seal_path.parent / original).resolve() == expected_path.resolve()
            )
        check(suffix_matches, "historical_absolute_path_has_declared_suffix", item["task_id"] + ":" + item["arm"])
        check(suffix_matches and sha(expected_path) == item["sha256"], "sealed_inverse_output_identity", item["task_id"] + ":" + item["arm"])
        if original.is_absolute():
            historical_path_mappings.append({"receipt_path": str(original), "local_relative_path": str(expected_relative), "mapping": "EXACT_DECLARED_SUFFIX_ONLY_NO_EXTERNAL_PATH_ACCESS"})
    release_path = corpus_root / "design-release.json"
    release = read(release_path)
    check(release["inverse_seal_sha256"] == sha(seal_path) and release["sealed_inverse_outcomes"] == 48 and release["truth_substitution_allowed"] is False, "design_released_after_complete_seal")
    for path in sorted((corpus_root / "sealed-design").rglob("*.json")):
        released = corpus_root / "design-released" / path.relative_to(corpus_root / "sealed-design")
        check(sha(path) == sha(released), "released_design_matches_frozen_template", str(path.relative_to(ROOT)))

    numerical = []
    if args.reverify_preserved_vectors:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT / "workloads"))
        from verifier import verify
    arrays = {}
    native_count = 0
    for row in records:
        key = (row["chain"], row["family"], row["arm"])
        label = ":".join(key)
        directory = ROOT / row["output"]
        task_path = ROOT / row["task_path"]
        task = read(task_path)
        check(sha(task_path) == row["task_sha256"] and task["id"] == row["id"], "executed_task_identity", label)
        check(row["cohort"] == "primary" and task["split"] == "primary", "primary_labels", label)
        check(task["network"]["node_count"] == row["node_count"], "recorded_node_count", label)
        if row.get("not_executed"):
            check(row["accepted"] is False and row["elapsed_seconds"] == 0 and row["cpu_seconds"] == 0, "unexecuted_is_not_accepted", label)
            if row["family"] == "design" and row.get("blocked") == "UPSTREAM_INVERSE_NOT_ACCEPTED":
                check(by_key[(row["chain"], "inverse", row["arm"])]["accepted"] is False, "failed_inverse_blocks_downstream", label)
            continue
        execution = read(directory / "execution.json")
        for field, value in execution.items():
            check(row.get(field) == value, "execution_receipt_matches_ledger", label + ":" + field)
        verification = read(directory / "verification.json") if (directory / "verification.json").exists() else {}
        pack = read(directory / "pack.json") if (directory / "pack.json").exists() else {}
        inspection = read(directory / "inspection.json") if (directory / "inspection.json").exists() else {}
        evaluation = pack.get("evaluation", {})
        boundary = evaluation.get("admission") == "HOLD" and evaluation.get("authority") == [] and evaluation.get("settlement") == "NOT_CONNECTED"
        accepted = row["exit_code"] == 0 and row["elapsed_seconds"] <= 60 and verification.get("accepted") is True and boundary and inspection.get("activeAuthority") == []
        check(accepted == row["accepted"], "complete_outcome_acceptance_recalculated", label)
        check(row["native_boundary_preserved"] == boundary, "native_boundary_receipt", label)
        check(row["complete_budget_respected"] == (row["elapsed_seconds"] <= 60), "complete_60_second_budget_receipt", label)
        check(row["verification"] == verification and row["native_inspection"] == inspection, "verification_inspection_ledger_matches", label)
        if pack:
            native_count += 1
            check(boundary and inspection.get("activeAuthority") == [], "native_hold_empty_authority", label)
            evidence = pack["result"]["evidence"]
            check(evidence["sourceHash"] == runtime_hash, "native_runtime_manifest_hash", label)
            check(evidence["jobSha256"] == row["task_sha256"] and evidence["oracleSha256"] == row["oracle_sha256"], "native_pack_input_hashes", label)
            check(evidence["verificationSha256"] == sha(directory / "verification.json"), "native_verification_hash", label)
            check(evidence["identity"] == "FIXTURE_ONLY" and evidence["liveAuthentication"] == "NOT RUN" and evidence["actualCustomerAcceptance"] is False, "native_fixture_scope", label)
        oracle_path = corpus_root / ("design-released" if row["family"] == "design" else "forward-inverse") / "oracles" / (row["id"] + ".json")
        check(sha(oracle_path) == row["oracle_sha256"], "oracle_identity", label)
        parent_task = parent_result = None
        if row["family"] == "design":
            parent = by_key[(row["chain"], "inverse", row["arm"])]
            parent_task = read(ROOT / parent["task_path"])
            parent_result = read(ROOT / parent["output"] / "result.json")
            parent_acceptance = read(ROOT / parent["output"] / "verification.json")
            template = read(corpus_root / "design-released/tasks" / (row["id"] + ".json"))
            materialization = task["lineage"]["materialization"]
            for field, item in (("template_sha256", template), ("parent_task_sha256", parent_task), ("parent_result_sha256", parent_result), ("parent_acceptance_sha256", parent_acceptance)):
                check(materialization[field] == canonical_sha(item), "actual_parent_design_hash", label + ":" + field)
            check(parent["accepted"] is True and parent_acceptance["accepted"] is True, "only_accepted_parent_can_materialize_design", label)
            check(materialization["inherited_parameters"] == parent_result["parameters"], "actual_parent_parameters_inherited", label)
            expected = deepcopy(parent_task["network"])
            for group, multiplier in zip(parent_task["parameters"]["groups"], parent_result["parameters"]):
                for edge in group:
                    expected["edges"][edge][2] *= float(multiplier)
            check(expected == task["network"], "design_coefficients_equal_actual_inverse_fit", label)
        if (directory / "result.json").exists():
            result = read(directory / "result.json")
            if "result_sha256" not in row:
                # The campaign seals an explicit placeholder after an inverse
                # process failure without a produced result.  Its seal hash
                # was checked above; it is not a solver output or a success.
                check(row["accepted"] is False and row["family"] == "inverse" and result.get("status") == "not_completed", "inverse_failure_placeholder_only", label)
                continue
            check(sha(directory / "result.json") == row["result_sha256"], "preserved_result_identity", label)
            if pack:
                check(pack["result"]["evidence"]["resultSha256"] == row["result_sha256"], "native_result_hash", label)
            arrays[key] = {name: result[name] for name in ("states", "parameters", "prediction_states", "allocation") if name in result}
            if args.reverify_preserved_vectors:
                report = verify(task, result, read(oracle_path), parent_task=parent_task, parent_result=parent_result)
                numerical.append({"chain": key[0], "family": key[1], "arm": key[2], "report": report})
                if "accepted" in verification:
                    check(report["accepted"] == verification["accepted"], "preserved_vector_verification_agrees", label)
        if row["arm"] in "BC" and (directory / "selection.json").exists():
            selection = read(directory / "selection.json")
            check(selection["ok"] is True and selection["executionAuthorized"] is True and selection["liveAuthentication"] == "NOT RUN", "scoped_local_selection", label)
            check(selection["authorization"]["jobSha256"] == row["task_sha256"], "selection_binds_actual_job", label)
            check(selection["strategy"] == ("registry" if row["arm"] == "B" else "graph"), "registered_retrieval_arm", label)
    independent_summary = {}
    for arm in ARMS:
        rows = [r for r in records if r["arm"] == arm]
        independent_summary[arm] = {
            "stage_count": len(rows), "accepted_stages": sum(r["accepted"] for r in rows),
            "accepted_chains": sum(all(by_key[(f"P{i:02d}", f, arm)]["accepted"] for f in FAMILIES) for i in range(1, 13)),
            "not_executed": sum(bool(r.get("not_executed")) for r in rows),
            "cpu_seconds": sum(r["cpu_seconds"] for r in rows),
            "elapsed_seconds": sum(r["elapsed_seconds"] for r in rows),
            "maximum_complete_elapsed_seconds": max(r["elapsed_seconds"] for r in rows),
            "accepted_by_family": {f: sum(r["accepted"] for r in rows if r["family"] == f) for f in FAMILIES},
        }
        for name, value in summary["arms"][arm].items():
            expected = independent_summary[arm][name]
            check(math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-9) if isinstance(value, float) else value == expected, "summary_reconciles_with_all_rows", arm + ":" + name)
    identical_bc = []
    for i in range(1, 13):
        for family in FAMILIES:
            chain = f"P{i:02d}"
            b, c = arrays.get((chain, family, "B")), arrays.get((chain, family, "C"))
            identical_bc.append({"chain": chain, "family": family, "both_present": b is not None and c is not None, "numeric_arrays_identical": b is not None and b == c})
    for f in freeze["files"]:
        file_identity(ROOT, f, "production_source_identity_after_audit")
    report = {
        "schema": "capability-advantage-independent-primary-audit/v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_freeze_sha256": sha(freeze_path), "frozen_file_count": len(freeze["files"]),
        "primary_summary_sha256": sha(primary / "summary.json"), "primary_records_sha256": sha(primary / "records.jsonl"),
        "status": "PASS" if not issues else "DEFECTS_FOUND", "issues": issues, "checks": dict(checks),
        "independent_summary": independent_summary, "native_packs_inspected": native_count,
        "historical_absolute_path_mappings": historical_path_mappings,
        "bc_numeric_equality": identical_bc,
        "numerical_reverification": "ORIGINAL_PRESERVED_VECTORS_ONLY" if args.reverify_preserved_vectors else "ORIGINAL_INDEPENDENT_VERDICT_RECEIPTS_ONLY",
        "numerical_reports": numerical, "audit_elapsed_seconds": time.perf_counter() - started,
        "limits": ["No solver rerun, new case, primary repair or market cohort performed.",
                   "The twelve connected chains are independent workload units; 144 stages are not 144 independent agents or jobs.",
                   "Frozen file identity and native checkpoint records were checked; this is not a forensic history of every filesystem operation.",
                   "Numerical acceptance is bounded synthetic software evidence, not observed customer value or physical deployment qualification."],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "primary-reconciliation.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "issues": issues, "arms": independent_summary,
                      "bc_identical": sum(r["numeric_arrays_identical"] for r in identical_bc),
                      "native_packs": native_count, "preserved_vectors_reverified": len(numerical),
                      "audit_elapsed_seconds": report["audit_elapsed_seconds"]}, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
