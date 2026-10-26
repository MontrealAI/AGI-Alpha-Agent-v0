# SPDX-License-Identifier: Apache-2.0
"""Post-campaign read-only audit of preserved source and delivery custody.

This is a publication audit, not a new behavioral evaluator. It reads completed
records and hashes their bound files; it never imports workers or executes probes.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
FREEZE = "f417768b69a6729000d5ce9d10393bfac7eec45b7ce448a0d61c711a6662530c"
REGISTRY = "af4c684a8487a4583f77fea054b39b2eb4c1dbc4ef2795d727f5e089eaa713a7"
DRIVER = "a0391dd8031ffce9c1df5ca6e18123f757286d892bcc8f7ca8dc1f2cf0b621fd"
CHECKS = []
HASHES = {}


def digest(path):
    path = Path(path).resolve()
    if path not in HASHES:
        HASHES[path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return HASHES[path]


def read(path):
    return json.loads(Path(path).read_text())


def check(condition, code, context):
    CHECKS.append({"code": code, "context": context, "passed": bool(condition)})


def identity(row, context):
    path = Path(row["path"])
    check(path.is_file() and path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
          "bound-byte-identity", context + ":" + str(path))


def receipt(path, allowed_exits, context):
    data = read(path)
    check(data.get("schema") == "alpha-measured-command/v1", "receipt-schema", context)
    check(data.get("command_started") is True and data.get("timed_out") is False
          and data.get("inputs_unchanged") is True and data.get("missing_outputs") == []
          and not data.get("launcher_error") and type(data.get("exit_code")) is int
          and data["exit_code"] in allowed_exits, "receipt-complete-execution", context)
    check(data.get("input_identities_before") == data.get("input_identities_after"),
          "receipt-before-after-equality", context)
    check(bool(data.get("input_identities_before")) and bool(data.get("output_identities")),
          "receipt-nonempty-input-output-bindings", context)
    for field in ("input_identities_before", "input_identities_after", "output_identities"):
        for row in data.get(field, []):
            identity(row, context + ":" + field)
    for field in ("stdout", "stderr"):
        check(isinstance(data.get(field), dict), "receipt-output-log-present", context + ":" + field)
        if isinstance(data.get(field), dict):
            identity(data[field], context + ":" + field)
    return data


def native_source_hash():
    names = ["src/manual_probe.py", "src/verify_component.py", "src/measured_run.py",
             "src/run_pair.py", "src/package_component.py", "src/conventional_probe.py",
             "src/conventional_package.py", "src/delivery.py", "src/workbench.mjs",
             "protocol/component-contract.json", "protocol/component-projections.json", "native/SOURCE.json"]
    entries = [[name, digest(ROOT / name)] for name in names]
    for row in read(ROOT / "native/SOURCE.json")["files"]:
        path = ROOT / "native" / row["path"]
        check(digest(path) == row["sha256"] and path.stat().st_size == row["bytes"],
              "native-original-source-identity", row["path"])
        entries.append(["native/" + row["path"], digest(path)])
    raw = json.dumps(entries, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def audit_one(mission, arm, index, entry, contract, native_hash):
    context = mission + "/" + arm
    first_check = len(CHECKS)
    directory = ROOT / "results/confirmation" / mission / arm
    terminal = read(directory / "terminal.json")
    job_path = ROOT / entry["path"]
    job = read(job_path)
    check(digest(job_path) == entry["sha256"], "registered-job-hash", context)
    check(terminal["mission_id"] == mission and terminal["arm"] == arm and terminal["sequence"] == index,
          "terminal-registered-order", context)
    check(terminal["job_sha256"] == entry["sha256"], "terminal-job-identity", context)
    packet = directory / ("package" if arm == "manual" else "delivery/package")
    pair_root = directory / ("pair" if arm == "manual" else "delivery/pair")
    decision = read(packet / "decision.json")
    pair = read(pair_root / "pair.json")
    check(terminal["decision_sha256"] == digest(packet / "decision.json"), "terminal-decision-hash", context)
    check(terminal["decision"] == decision["decision"] and decision["mission_id"] == mission
          and decision["phase"] == "confirmation" and decision["job_sha256"] == entry["sha256"],
          "decision-registration-and-terminal-agreement", context)
    check(pair["custody_complete"] is True and pair["job_sha256"] == entry["sha256"]
          and digest(pair_root / "job.json") == entry["sha256"], "pair-job-custody", context)
    expected_worker = "src/conventional_probe.py" if arm == "conventional" else "src/manual_probe.py"
    check(pair["worker_path"] == expected_worker and pair["worker_sha256"] == digest(ROOT / expected_worker),
          "pair-frozen-worker", context)
    check(not decision.get("custody_errors", []) and not decision.get("custody_failures", []),
          "decision-no-custody-failures", context)
    for row in pair.get("artifacts", []):
        identity({**row, "path": str(pair_root / row["path"])}, context + ":pair-inventory")
    manifest = read(packet / "artifact-manifest.json")
    paths = [row["path"] for row in manifest["files"]]
    check(len(paths) > 20 and len(paths) == len(set(paths)), "package-inventory-unique-nonempty", context)
    for row in manifest["files"]:
        path = packet / row["path"]
        check(not Path(row["path"]).is_absolute() and ".." not in Path(row["path"]).parts
              and not path.is_symlink() and path.resolve().is_relative_to(packet), "package-safe-path", context)
        identity({**row, "path": str(path)}, context + ":package-inventory")
    mandatory = {"decision.json", "reproduce.txt", "proposed-component-lock.patch", "requirement-results.json",
                 "evidence/component-contract.json", "evidence/component-projections.json", "evidence/job.json",
                 "evidence/pair.json", "evidence/verify_component.py"}
    check(mandatory.issubset(paths), "package-required-common-evidence", context)
    check(({"README.md", "README.fr.md"}.issubset(paths)
           or {"report-en.html", "report-fr.html"}.issubset(paths)), "package-bilingual-files", context)
    allowed_extra = {"artifact-manifest.json", "assembly-receipt.json"}
    actual_files = {str(path.relative_to(packet)) for path in packet.rglob("*") if path.is_file()}
    check(actual_files - set(paths) <= allowed_extra, "package-unlisted-files-explained", context)
    for row in decision.get("evidence", []):
        identity({"path": row["source"], "sha256": row["sha256"], "bytes": row["bytes"]},
                 context + ":copied-source")
        identity({"path": str(packet / row["package_path"]), "sha256": row["sha256"], "bytes": row["bytes"]},
                 context + ":copied-evidence")
    contract_ids = [row["id"] for row in contract["cases"]]
    verifications = {}
    for side in ("before", "after"):
        label = context + ":" + side
        env = ROOT / job[side]["environment"]
        observed_path = pair_root / (side + "-observations.json")
        verified_path = pair_root / (side + "-verification.json")
        observed, verified = read(observed_path), read(verified_path)
        verifications[side] = verified
        execution = receipt(pair_root / (side + "-execution.json"), {0, 1}, label + ":worker")
        verification = receipt(pair_root / (side + "-verification-execution.json"), {0, 2}, label + ":verifier")
        check(str(ROOT / expected_worker) in execution["command"], "execution-worker-command", label)
        check(str(ROOT / "src/verify_component.py") in verification["command"], "execution-verifier-command", label)
        check(verified["observations_sha256"] == digest(observed_path)
              and verified["environment_manifest_sha256"] == digest(env / "preparation.json")
              and verified["contract_sha256"] == digest(ROOT / "protocol/component-contract.json")
              and verified["projection_profiles_sha256"] == digest(ROOT / "protocol/component-projections.json")
              and verified["projection_id"] == "native-fastapi-bridge-v2"
              and verified["native_import_route"] is True, "verification-bound-original-inputs", label)
        check(observed["versions"] == verified["environment_versions"] == job[side]["expected_versions"],
              "executed-registered-environment-versions", label)
        case_ids = [row["id"] for row in verified["cases"]]
        check(len(case_ids) == len(set(case_ids)) and set(case_ids) == set(contract_ids),
              "all-required-cases-exactly-once", label)
        counted = collections.Counter(row["status"] for row in verified["cases"])
        check(all(verified["counts"].get(key) == counted.get(key, 0)
                  for key in ("PASS", "BEHAVIOR_MISMATCH", "INCOMPLETE")), "case-count-consistency", label)
        check(not verified["global_incomplete"], "no-global-incomplete", label)
        for suffix, original in [("observations.json", observed_path), ("verification.json", verified_path),
                                 ("execution.json", pair_root / (side + "-execution.json")),
                                 ("verification-execution.json", pair_root / (side + "-verification-execution.json")),
                                 ("environment.json", env / "preparation.json")]:
            check(digest(packet / "evidence" / (side + "-" + suffix)) == digest(original),
                  "packet-exact-evidence-copy", label + ":" + suffix)
        check(digest(packet / "evidence" / (side + ".lock")) == digest(env / "requirements.lock"),
              "packet-exact-lock-copy", label)
    before, after = verifications["before"], verifications["after"]
    expected_decision = ("INCOMPLETE_HOLD" if before["status"] != "PRESERVED_WITHIN_COMPONENT_CONTRACT" else
                         "SCOPED_COMPONENT_PRESERVED" if after["status"] == "PRESERVED_WITHIN_COMPONENT_CONTRACT" else
                         "COMPONENT_REGRESSION" if after["status"] == "BEHAVIOR_MISMATCH" else "INCOMPLETE_HOLD")
    check(decision["decision"] == expected_decision, "decision-follows-frozen-status-rule", context)
    requirement_results = read(packet / "requirement-results.json")
    if arm == "retained":
        rows = {row["id"]: row for row in requirement_results}
        check(len(rows) == len(requirement_results) and set(rows) == set(contract_ids),
              "published-retained-requirement-ids", context)
        for side in ("before", "after"):
            check(all(rows[row["id"]][side] == row["status"] for row in verifications[side]["cases"]),
                  "published-requirement-results-match-verifier", context + ":" + side)
        check(all(rows[row["id"]]["after_errors"] == row["errors"] for row in after["cases"]),
              "published-retained-mismatch-detail", context)
    else:
        check(all(requirement_results[side] == verifications[side]["cases"] for side in ("before", "after")),
              "published-requirement-results-match-verifier", context)
    patch_names = {"manual": ("baseline-component.lock", "proposed-component.lock"),
                   "retained": ("before-component.lock", "proposed-component.lock"),
                   "conventional": ("before/component.lock", "proposed/component.lock")}
    patch = "".join(difflib.unified_diff(
        (ROOT / job["before"]["environment"] / "requirements.lock").read_text().splitlines(True),
        (ROOT / job["after"]["environment"] / "requirements.lock").read_text().splitlines(True),
        fromfile=patch_names[arm][0], tofile=patch_names[arm][1]))
    check((packet / "proposed-component-lock.patch").read_text() == patch, "patch-exact-declared-lock-difference", context)
    if arm == "manual":
        enclosing = receipt(ROOT / terminal["finalization_receipt"], {0}, context + ":enclosing-finalization")
        finalization = read(directory / "manual-finalization.json")
        check(finalization["decision"] == decision["decision"]
              and finalization["request_sha256"] == digest(directory / "manual-review-request.json")
              and terminal["manual_finalizations"] == 1, "explicit-researcher-finalization-bound", context)
    else:
        enclosing = receipt(ROOT / terminal["external_receipt"], {0}, context + ":enclosing-native-run")
        delivery, pack, inspection = (read(directory / relative)
                                     for relative in ("delivery/delivery.json", "pack.json", "inspection.json"))
        check(delivery["accepted"] is True and delivery["pair_custody_complete"] is True
              and delivery["decision"] == decision["decision"]
              and delivery["decision_sha256"] == digest(packet / "decision.json")
              and not delivery.get("error"), "native-delivery-complete-and-bound", context)
        check(pack["frozen"]["sourceHash"] == native_hash and pack["frozen"]["authority"] == [],
              "native-complete-source-identity-and-no-authority", context)
        check(pack["evaluation"]["admission"] == "HOLD" and pack["evaluation"]["authority"] == []
              and pack["evaluation"]["settlement"] == "NOT_CONNECTED", "native-held-admission", context)
        check(inspection["authentication"] == "UNAUTHENTICATED_HISTORICAL_IMPORT"
              and inspection["activeProof"] == [] and inspection["activeAuthority"] == [],
              "native-inspection-no-active-authority", context)
        check(pack["result"]["decision"] == inspection["history"]["decision"] == decision["decision"]
              and pack["result"]["evidence"]["jobSha256"] == entry["sha256"]
              and pack["result"]["evidence"]["packageDecisionSha256"] == digest(packet / "decision.json"),
              "native-pack-decision-and-job-agreement", context)
        check(inspection["history"]["releaseDigest"] == pack["releaseDigest"]
              and inspection["history"]["missionDigest"] == pack["frozen"]["missionDigest"],
              "native-inspection-pack-agreement", context)
        artifacts = {row["name"]: row for row in pack["result"]["artifacts"]}
        check(len(artifacts) == len(pack["result"]["artifacts"]) == 5,
              "native-artifact-identities-unique", context)
        check(json.loads(artifacts["component-decision.json"]["content"]) == decision
              and json.loads(artifacts["delivery-resources.json"]["content"]) == delivery
              and json.loads(artifacts["requirement-results.json"]["content"]) == requirement_results
              and artifacts["component-lock.patch"]["content"] == patch
              and json.loads(artifacts["complete-package-reference.json"]["content"])["manifestSha256"]
              == digest(packet / "artifact-manifest.json"), "native-embedded-artifact-byte-content-agreement", context)
        if (packet / "assembly-receipt.json").exists():
            assembly = read(packet / "assembly-receipt.json")
            check(assembly["manifest_sha256"] == digest(packet / "artifact-manifest.json")
                  and assembly["assembler_sha256"] == digest(ROOT / "src/package_component.py")
                  and assembly["files_verified"] == len(paths), "retained-assembly-receipt-binding", context)
    check(enclosing.get("complete_success") is True, "enclosing-meter-complete-success", context)
    issues = [row for row in CHECKS[first_check:] if not row["passed"]]
    accepted = expected_decision in {"SCOPED_COMPONENT_PRESERVED", "COMPONENT_REGRESSION"} and not issues
    check(terminal["accepted"] == accepted, "terminal-independent-custody-audit-agreement", context)
    return {"mission_id": mission, "arm": arm, "sequence": index, "terminal_accepted": terminal["accepted"],
            "audit_accepted": accepted, "decision": decision["decision"], "package_manifest_files": len(paths),
            "before_counts": before["counts"], "after_counts": after["counts"], "issues": issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results/review-controls/postcampaign-custody-v3")
    args = parser.parse_args()
    start, cpu = time.perf_counter(), time.process_time()
    campaign_path = ROOT / "results/confirmation/campaign.json"
    if not campaign_path.is_file():
        raise ValueError("COMPLETED_CAMPAIGN_REQUIRED")
    out = args.out.resolve()
    if not out.is_relative_to(ROOT):
        raise ValueError("STUDY_LOCAL_AUDIT_OUTPUT_REQUIRED")
    out.mkdir(parents=True, exist_ok=False)
    campaign = read(campaign_path)
    freeze = read(ROOT / "protocol/source-freeze.json")
    check(digest(ROOT / "protocol/source-freeze.json") == FREEZE, "source-freeze-identity", "campaign")
    check(digest(ROOT / "data/confirmation-inputs/mission-registry.json") == REGISTRY
          == campaign["registry_sha256"], "separate-registry-identity", "campaign")
    check(digest(ROOT / "analysis/run_campaign.py") == DRIVER == campaign["driver_sha256"],
          "sealed-invocation-driver-identity", "campaign")
    for row in freeze["files"]:
        check(digest(ROOT / row["path"]) == row["sha256"] and (ROOT / row["path"]).stat().st_size == row["bytes"],
              "frozen-file-unchanged", row["path"])
    native_hash = native_source_hash()
    protocol = read(ROOT / "protocol/primary-protocol.json")
    expected = [(row["mission"], arm) for row in protocol["mission_order"] for arm in row["arms"]]
    actual = [(row["mission_id"], row["arm"]) for row in campaign["results"]]
    check(expected == actual and len(actual) == 18 and len(set(actual)) == 18,
          "complete-balanced-prespecified-order", "campaign")
    registry = read(ROOT / "data/confirmation-inputs/mission-registry.json")["missions"]
    contract = read(ROOT / "protocol/component-contract.json")
    evaluations = [audit_one(mission, arm, index, registry[mission], contract, native_hash)
                   for index, (mission, arm) in enumerate(expected, 1)]
    for row in freeze["files"]:
        raw = (ROOT / row["path"]).read_bytes()
        check(hashlib.sha256(raw).hexdigest() == row["sha256"] and len(raw) == row["bytes"],
              "frozen-file-unchanged-after-audit", row["path"])
    failures = [row for row in CHECKS if not row["passed"]]
    result = {"schema": "postcampaign-source-custody-review/v1",
              "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "campaign_sha256": digest(campaign_path), "auditor_sha256": digest(Path(__file__)),
              "freeze_sha256": FREEZE, "frozen_source_files_checked": len(freeze["files"]),
              "native_source_identity": native_hash, "unique_missions": len({row[0] for row in expected}),
              "evaluations": evaluations, "checks": CHECKS, "failed_checks": failures,
              "passed": not failures, "audit_accepted_evaluations": sum(row["audit_accepted"] for row in evaluations),
              "native_held_runs_reviewed": sum(row["arm"] != "manual" for row in evaluations),
              "terminal_disagreements": [row for row in evaluations if row["audit_accepted"] != row["terminal_accepted"]],
              "wall_seconds": time.perf_counter() - start, "process_cpu_seconds": time.process_time() - cpu,
              "consumer_executions": 0, "new_primary_missions": 0, "frozen_files_modified": False,
              "inference_usd": None, "money_usd": None,
              "limits": ["This audit checks recorded custody and publication consistency without re-executing behavior.",
                        "It supplies no external customer acceptance, hostile-recorder attestation, operator authority or economic admission.",
                        "Complete replay requires the common companion source/dependency closure, not only a per-mission packet."]}
    (out / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    with (ROOT / "metering/source_audit.jsonl").open("a") as output:
        output.write(json.dumps({"event": "completed_primary_source_custody_audit", "utc": result["reviewed_at"],
                                "report": str((out / "review.json").relative_to(ROOT)), "passed": result["passed"],
                                "wall_seconds": result["wall_seconds"], "process_cpu_seconds": result["process_cpu_seconds"],
                                "consumer_executions": 0, "inference_usd": None, "money_usd": None}) + "\n")
    print(json.dumps({key: result[key] for key in ("passed", "audit_accepted_evaluations", "unique_missions",
                                                 "native_held_runs_reviewed", "terminal_disagreements", "failed_checks")}))


if __name__ == "__main__":
    main()
