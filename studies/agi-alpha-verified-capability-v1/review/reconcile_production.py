#!/usr/bin/env python3
"""Reconcile frozen production artifacts without rerunning pip or production.

Usage: python review/reconcile_production.py --root . --output review/production-reconciliation-NEW.json
Requires the recorded native marker environment for the unchanged verifier.
The first archived review receipt contains checker defects; receipt 02 supersedes it.
Only newly measured verifier CPU/wall fields are excluded from semantic equality.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", default="review/production-reconciliation-NEW.json")
    args = parser.parse_args()
    root = args.root.resolve()
    output = (root / args.output).resolve()
    if not output.is_relative_to(root) or output.exists():
        raise SystemExit("Use a fresh output path inside the study; prior evidence is immutable.")
    sys.path.insert(0, str(root / "src"))
    from acceptance import reverify, mission_key

    started, cpu_started = time.perf_counter(), time.process_time()
    failures, rows_verified = [], []
    checks = 0

    def load(path):
        return json.loads(Path(path).read_text())

    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def check(ok, label, where=None):
        nonlocal checks
        checks += 1
        if not ok:
            failures.append({"check": label, "where": where})

    def close(a, b):
        return math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-8)

    def stable_certificate(certificate):
        copied = json.loads(json.dumps(certificate))
        copied["verifier"].pop("cpu_seconds", None)
        copied["verifier"].pop("wall_seconds", None)
        return copied

    summary = load(root / "evidence/production-summary.json")
    freeze = load(root / "protocol/production-freeze.json")
    manifest = load(root / "inputs/missions-v1/manifest.json")
    audit = load(root / "evidence/development/mission-input-identities-01.json")
    catalog = load(root / "evidence/catalog/catalog.json")
    bindings = load(root / "market/asset-bindings.json")
    orders = load(root / "protocol/arm-order.json")["orders"]
    jobs = [job for job in manifest["jobs"] if job["group"] != "development"]
    by_id = {job["id"]: job for job in jobs}
    keys = {row["id"]: row["semantic_mission_key"] for row in audit["rows"]}
    check(summary == load(root / "evidence/production-primary/summary.json"), "canonical summary")
    check(sha(root / "protocol/production-freeze.json") == summary["freeze_sha256"], "freeze identity")
    check(len(freeze["files"]) == len({x["path"] for x in freeze["files"]}) == 193, "193 frozen files")
    for entry in freeze["files"]:
        path = root / entry["path"]
        check(path.resolve().is_relative_to(root) and not path.is_symlink()
              and sha(path) == entry["sha256"] and path.stat().st_size == entry["bytes"],
              "frozen file identity", entry["path"])
    check(sum(x["bytes"] for x in freeze["files"]) == summary["initial_guard"]["bytes"]
          == summary["final_guard"]["bytes"], "frozen byte count")
    check(summary["raw_evaluations"] == 72 and summary["unique_substantive_missions"] == 18
          and summary["primary_composition_missions"] == 15 and summary["designed_stress_missions"] == 3,
          "registered denominators")
    check(len(by_id) == 18 and len({keys[j["id"]] for j in jobs}) == 18, "distinct substantive questions")
    for job in jobs:
        check(sha(root / job["job"]) == job["job_sha256"]
              and mission_key(root / job["job"]) == keys[job["id"]], "job and semantic identity", job["id"])
    check(len(orders) == 18 and all(sorted(order) == list("ABCD") for order in orders), "four-arm orders")
    for arm in "ABCD":
        for position in range(4):
            check(sum(order[position] == arm for order in orders) in {4, 5}, "position balance", f"{arm}:{position}")

    semantics = collections.defaultdict(dict)
    totals, packet_paths, completeness = {}, [], []
    payload_files, archive_entries = 0, 0
    for arm in "ABCD":
        arm_data = summary["arms"][arm]
        rows, tool_count = arm_data["per_mission"], 0
        check(len(rows) == 18 and {row["id"] for row in rows} == set(by_id), "complete arm", arm)
        check(sum(row["cohort"] == "primary" for row in rows) == 15
              and sum(row["cohort"] == "stress" for row in rows) == 3, "cohort partition", arm)
        for row in rows:
            label, failures_before, checks_before = f"{arm}:{row['id']}", len(failures), checks
            try:
                job = by_id[row["id"]]
                index = next(i for i, item in enumerate(jobs) if item["id"] == job["id"])
                packet_path = root / row["packet_path"]
                packet_paths.append(row["packet_path"])
                base = packet_path.parent
                out = (root / row["selection_path"]).parent
                packet = load(packet_path)
                measurement = load(out / "production/measurement.json")
                selection_receipt = load(out / "selection.json")
                selection = selection_receipt["selection"]
                check(load(out / "outcome.json") == row and row["arm"] == arm
                      and row["order"] == orders[index], "outcome custody and order", label)
                check(row["cohort"] == ("primary" if job["group"] == "primary-composition" else "stress"),
                      "cohort binding", label)
                check(sha(packet_path) == row["packet_sha256"] and packet["job_id"] == job["id"]
                      and packet["job_sha256"] == job["job_sha256"], "packet and job binding", label)
                check(packet["mission_key"] == row["mission_key"] == keys[job["id"]]
                      and packet["route"] == ("direct" if arm == "D" else "native"), "key and route", label)
                check(measurement == row["production"] and measurement["returncode"] == row["operation"]["code"] == 0
                      and row["returned_packet_identity_matches"], "measurement and return gate", label)
                check(packet["accepted"] is True and row["accepted"] is True
                      and packet["decision"] == row["decision"], "accepted decision", label)
                source = load(base / "source-identity.json")
                aggregate = hashlib.sha256(json.dumps(source["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                check(source["sha256"] == packet["source_sha256"] == aggregate
                      == "33f3075afca390d4e26dd8cac6094242aa9f692e381a8f7b02dae0d3f8b47e06", "source aggregate", label)
                for entry in source["files"]:
                    check(sha(root / entry["path"]) == entry["sha256"], "executed source file", label + ":" + entry["path"])
                result_path = base / "execution/delivery/result.json"
                certificate_path = base / "execution/verification.json"
                certificate = load(certificate_path)
                recomputed = reverify(root / job["job"], result_path)
                check(packet["certificate"] == certificate and packet["evidence_ids"]["certificate"] == sha(certificate_path)
                      and packet["evidence_ids"]["result"] == sha(result_path)
                      and packet["evidence_ids"]["job"] == sha(root / job["job"]), "certificate evidence custody", label)
                check(stable_certificate(recomputed) == stable_certificate(certificate), "independent metadata semantics", label)
                witnesses = certificate["substantiated_witnesses"]
                check(certificate["status"] == "COMPLETE" and certificate["verdict"] == row["decision"]
                      and isinstance(witnesses, list) and ((len(witnesses) > 0) == (certificate["verdict"] == "CONFLICT")),
                      "substantiated acceptance", label)
                semantics[job["id"]][arm] = {key: certificate.get(key) for key in
                    ["status", "verdict", "independent_metadata_verdict", "dependency_edges", "substantiated_witnesses", "errors", "scope"]}
                check(packet["authority"] == [] and packet["financial_action"] is False
                      and packet["actual_collections"] == 0 and packet["application_qualified"] is False, "scope boundary", label)
                check(packet["tools"]["model_calls"] == packet["tools"]["network_requests"] == packet["tools"]["retries"] == 0,
                      "zero model network retry calls", label)
                payload = load(base / "payload-manifest.json")
                check(sha(base / "payload-manifest.json") == packet["output_manifest_sha256"], "payload manifest", label)
                names = set()
                for entry in payload["files"]:
                    path = base / entry["path"]
                    names.add(entry["path"])
                    payload_files += 1
                    check(path.resolve().is_relative_to(base) and sha(path) == entry["sha256"]
                          and path.stat().st_size == entry["bytes"], "payload file", label + ":" + entry["path"])
                archive_path = base / packet["packet_zip"]["path"]
                check(sha(archive_path) == packet["packet_zip"]["sha256"]
                      and archive_path.stat().st_size == packet["packet_zip"]["bytes"], "ZIP identity", label)
                with zipfile.ZipFile(archive_path) as archive:
                    check(set(archive.namelist()) == names | {"payload-manifest.json"} and archive.testzip() is None,
                          "ZIP inventory and CRC", label)
                    for name in archive.namelist():
                        archive_entries += 1
                        check(archive.read(name) == (base / name).read_bytes(), "archive entry", label + ":" + name)
                for language in ["en", "fr"]:
                    report = (base / f"report.{language}.md").read_text()
                    check(packet["decision"] in report and packet["mission_key"] in report
                          and packet["job_sha256"] in report and len(report) > 200, "bound bilingual report", label + ":" + language)
                if arm != "D":
                    pack, inspection = load(base / "execution/pack.json"), load(base / "execution/inspection.json")
                    check(pack["evaluation"] == {"scope": "PUBLIC_LOCAL_EXECUTION", "independentProof": False,
                          "admission": "HOLD", "authority": [], "settlement": "NOT_CONNECTED"}, "native HOLD", label)
                    check(inspection["activeProof"] == [] and inspection["activeAuthority"] == []
                          and inspection["authentication"] == "UNAUTHENTICATED_HISTORICAL_IMPORT", "no native authority", label)
                if arm in "BC":
                    check(selection and selection["ok"] and selection["selected"] ==
                          ["lock-preflight@1", "metadata-verifier@1", "native-workbench@1", "decision-delivery@1"], "full selected recipe", label)
                    check(selection["strategy"] == ("registry" if arm == "B" else "graph") and row["selection_used"]
                          and row["asset_id"] == selection_receipt["asset_id"] == bindings["assets"][arm]["id"], "actual asset usage", label)
                    check(row["graph_state"] == catalog["root"]["graphRoot"]
                          and selection["counters"] == row["selection_counters"], "root and counters", label)
                    check(all(item["authority"]["ok"] for item in selection["trace"] if item["kind"] == "skill")
                          and all(item["authorization"]["ok"] for item in selection["trace"] if item["kind"] == "root"),
                          "distinct fixture authority", label)
                else:
                    check(selection is None and row["asset_id"] is None and row["selection_used"] is False, "no graph attribution", label)
                check(close(measurement["cpu_seconds"], measurement["child_cpu_seconds"] + measurement["measurement_driver_cpu_seconds"])
                      and close(row["cpu_seconds"], row["parent_cpu_seconds"] + measurement["cpu_seconds"]), "CPU arithmetic", label)
                check(row["elapsed_seconds"] >= measurement["wall_seconds"]
                      and row["cpu_seconds"] >= row["selection_cpu_seconds"], "timing nesting", label)
                check(row["child_cpu_known"] and measurement["descendant_cpu_complete"]
                      and row["unmeasured_child_cost"] is None, "known CPU receipt", label)
                completeness.append(row["child_cpu_known"])
                guard = row["experimental_custody_overhead"]
                check(guard["included_in_totals"] and guard["cpu_seconds"] <= row["parent_cpu_seconds"] + 1e-9
                      and guard["elapsed_seconds"] <= row["elapsed_seconds"], "experimental guard allocation", label)
                tool_count += packet["tools"]["pip_resolutions"] + packet["tools"]["metadata_verifications"] + (
                    selection["counters"]["proof_checks"] + selection["counters"]["attestation_checks"] if selection else 0)
                rows_verified.append({"arm": arm, "id": job["id"], "cohort": row["cohort"], "decision": row["decision"],
                    "checks": checks - checks_before, "passed": len(failures) == failures_before, "packet_sha256": row["packet_sha256"]})
            except Exception as error:
                failures.append({"check": "checker exception", "where": label, "details": type(error).__name__ + ": " + str(error)})
                rows_verified.append({"arm": arm, "id": row["id"], "passed": False})
        init = arm_data["initialization"]
        cpu = sum(row["cpu_seconds"] for row in rows) + init["common_allocated_cpu"] + init["final_shared_cpu"] + (
            init["selector"]["cpu_seconds"] if init["selector"] else 0)
        wall = sum(row["elapsed_seconds"] for row in rows) + init["common_allocated_wall"] + init["final_shared_wall"] + (
            init["selector"]["elapsed_seconds"] if init["selector"] else 0)
        check(close(arm_data["cpu_seconds_total"], cpu) and close(arm_data["elapsed_seconds_total"], wall), "arm allocated costs", arm)
        check(arm_data["accepted_count"] == sum(row["accepted"] for row in rows) == 18
              and arm_data["tools_total"] == tool_count, "accepted and declared check counts", arm)
        primary = [row for row in rows if row["cohort"] == "primary"]
        totals[arm] = {"accepted": 18, "primary_consistent": sum(row["decision"] == "CONSISTENT" for row in primary),
            "primary_conflict": sum(row["decision"] == "CONFLICT" for row in primary), "total_cpu_seconds": cpu,
            "total_elapsed_seconds": wall, "declared_tool_checks": tool_count,
            "primary_mean_cpu_seconds_with_uniform_shared_allocation": sum(row["cpu_seconds"] for row in primary) / 15
                + (cpu - sum(row["cpu_seconds"] for row in rows)) / 18,
            "primary_mean_elapsed_seconds_with_uniform_shared_allocation": sum(row["elapsed_seconds"] for row in primary) / 15
                + (wall - sum(row["elapsed_seconds"] for row in rows)) / 18}
    for job_id, values in semantics.items():
        check(len(values) == 4 and all(value == values["A"] for value in values.values()), "four-arm semantic equality", job_id)
    check(len(packet_paths) == len(set(packet_paths)) == 72, "72 distinct packets")
    check(len(summary["duplicate_requests"]) == 4, "four cache confirmations")
    for receipt in summary["duplicate_requests"]:
        arm = receipt["arm"]
        check(receipt == load(root / f"evidence/production-primary/cache-{arm}.json") and receipt["cache_confirmation"]
              and receipt["new_completed_jobs"] == 0 and receipt["pip_resolutions"] == 0
              and receipt["mission_key"] == keys[jobs[0]["id"]] and summary["arms"][arm]["cache_confirmations"] == 1,
              "cache adds no jobs", arm)
        check(receipt["source_guard"] == summary["initial_guard"], "complete cache custody", arm)
    check(summary["quality_equivalence"] and len(semantics) == 18 and len(completeness) == 72
          and all(completeness) and summary["execution_costs_known"], "summary claims")
    wall_gap = summary["elapsed_seconds"] - sum(arm["elapsed_seconds_total"] for arm in summary["arms"].values()) - sum(
        receipt["elapsed_seconds"] for receipt in summary["duplicate_requests"])
    check(wall_gap >= 0 and "Final summary serialization" in summary["unmeasured_process_wall"], "disclosed post-sample wall")
    report = {"schema": "agi-alpha-independent-production-reconciliation/v1", "status": "PASS" if not failures else "FINDINGS",
        "source_freeze_sha256": summary["freeze_sha256"], "source_files_verified": len(freeze["files"]),
        "production_summary_sha256": sha(root / "evidence/production-summary.json"), "checks": checks,
        "failed_checks": len(failures), "failures": failures, "packets_reconciled": len(rows_verified),
        "passed_packets": sum(row["passed"] for row in rows_verified), "payload_files_verified": payload_files,
        "archive_entries_verified": archive_entries, "arms": totals, "rows": rows_verified,
        "unallocated_post_sample_wall_seconds": wall_gap, "source_sha256": sha(Path(__file__)),
        "review_resources": {"elapsed_seconds": time.perf_counter() - started, "cpu_seconds": time.process_time() - cpu_started,
            "metadata_reverifications": 72, "new_pip_executions": 0, "model_calls_in_script": 0, "network_requests": 0},
        "scope": "Artifact reconciliation and stored-pip evidence verification only; no production or simulator rerun.",
        "limitations": ["Same-session review, not external certification.", "Full monetary research, human and upkeep cost remains unknown.",
            "Verifier CPU/wall is newly measured and is excluded from semantic certificate equality; all other certificate fields are checked.",
            "Declared tool total is the specified pip+metadata+inclusion+attestation check sum."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "checks": checks, "failed_checks": len(failures), "output": str(output)}))
    raise SystemExit(0 if not failures else 2)


if __name__ == "__main__":
    main()
