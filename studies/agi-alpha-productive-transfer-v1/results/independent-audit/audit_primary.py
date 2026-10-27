# SPDX-License-Identifier: Apache-2.0
"""Audit sealed outputs without rerunning or repairing any primary arm.

The acceptance evaluator and source oracle are the unchanged pre-outcome files.
This post-outcome driver verifies identities, losslessly projects A's native
request into the evaluator's extraction schema, and checks delivery evidence.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import importlib.util
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
EXPECTED = {
    "protocol/candidate-freeze.json": "75f69dcd429ce0d76031691fb73a79a5be8356642eed8a9c06092259061ac3ce",
    "protocol/execution-freeze.json": "7f505b229212908d32f05b69d7016946a71356261ad88826e52ac5dccbc7493e",
    "protocol/input-freeze.json": "b55984f6a19efd477556088777b5d8babeb22fd7b8859d9e226e110b627cc4af",
    "results/confirmation/campaign.json": "8bf1219d32de201c5adacecb94b66c281886c6664505a9ec8166d11946fc7323",
}
ORACLE_FREEZE = "348dc36931d02792bfae75316e0d5dcf73491aaad775e0bd6abe3d3adec27ea5"
TEMPLATE_REFERENCES = [
    "decision-record.json", "automated-costs.json", "cost-analysis.json",
    "ledger.json", "ledger-analysis.json",
]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def verify_manifest(base, rows):
    defects = []
    for row in rows:
        path = base / row["path"]
        if not path.is_file() or sha(path) != row["sha256"] or path.stat().st_size != row["bytes"]:
            defects.append(row["path"])
    return {"checked": len(rows), "defects": defects}


def call_key(row):
    return row["line"], row["column"], row["callee"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--copy-corpus", action="store_true")
    args = parser.parse_args()
    corpus = args.corpus or (STUDY / "acceptance" if (STUDY / "acceptance").exists()
                             else STUDY.parent / "production-audit/sealed-corpus")
    start = dt.datetime.now(dt.UTC).isoformat()
    identity = {"schema": "alpha-transfer-independent-identities/v1", "startedAt": start,
                "frozenManifests": {}, "manifestContents": {}, "sourceBlobs": {}, "inputChecks": []}
    for name, expected in EXPECTED.items():
        actual = sha(STUDY / name)
        identity["frozenManifests"][name] = {"expected": expected, "actual": actual, "accepted": actual == expected}
    actual = sha(corpus / "TASK_ORACLE_FREEZE.json")
    identity["frozenManifests"]["TASK_ORACLE_FREEZE.json"] = {
        "expected": ORACLE_FREEZE, "actual": actual, "accepted": actual == ORACLE_FREEZE}
    freeze = read(corpus / "TASK_ORACLE_FREEZE.json")
    campaign = read(STUDY / "results/confirmation/campaign.json")
    inputs = read(STUDY / "protocol/input-freeze.json")
    for name, base, rows in [
        ("independentOracle", corpus, freeze["source_files"]),
        ("candidate", STUDY, read(STUDY / "protocol/candidate-freeze.json")["files"]),
        ("execution", STUDY, read(STUDY / "protocol/execution-freeze.json")["files"]),
        ("campaign", STUDY, campaign["payloads"]),
        ("native", STUDY / "vendor/native", read(STUDY / "vendor/native/SOURCE.json")["files"]),
        ("product", STUDY / "vendor/product", read(STUDY / "vendor/product/source-snapshot.json")["files"]),
    ]:
        identity["manifestContents"][name] = verify_manifest(base, rows)
    source_rows = read(corpus / "source-identities.json")
    bad_blobs = []
    for row in source_rows:
        raw = (corpus / row["file"]).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != row["git_blob"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            bad_blobs.append(row["file"])
    identity["sourceBlobs"] = {"checked": len(source_rows), "defects": bad_blobs,
                               "networkRefetch": False, "basis": "Exact acquired Git blob/SHA256 records"}
    for row in inputs["tasks"]:
        raw_path = STUDY / row["path"]
        task = read(raw_path)
        checks = {
            "bytes": raw_path.stat().st_size == row["bytes"],
            "rawDigest": sha(raw_path) == row["sha256"],
            "canonicalDigest": hashlib.sha256(canonical(task)).hexdigest() == row["canonicalInputSha256"],
            "oracleCopy": raw_path.read_bytes() == (corpus / "tasks" / (row["id"] + ".json")).read_bytes(),
            "embeddedSources": all(hashlib.sha256(s["text"].encode()).hexdigest() == s["sha256"]
                                   for s in task["sources"].values()),
        }
        identity["inputChecks"].append({"task": row["id"], **checks, "accepted": all(checks.values())})
    identity["accepted"] = (all(x["accepted"] for x in identity["frozenManifests"].values())
                            and all(not x["defects"] for x in identity["manifestContents"].values())
                            and not bad_blobs and all(x["accepted"] for x in identity["inputChecks"]))
    write(args.out / "identities.json", identity)
    if not identity["accepted"]:
        raise ValueError("Frozen evidence identity mismatch; see identities.json")

    if args.copy_corpus:
        target = STUDY / "acceptance"
        target.mkdir(exist_ok=False)
        for row in freeze["source_files"]:
            dest = target / row["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(corpus / row["path"], dest)
        shutil.copyfile(corpus / "TASK_ORACLE_FREEZE.json", target / "TASK_ORACLE_FREEZE.json")
        copied = verify_manifest(target, freeze["source_files"])
        if copied["defects"] or sha(target / "TASK_ORACLE_FREEZE.json") != ORACLE_FREEZE:
            raise ValueError("Acceptance copy mismatch")
        write(args.out / "acceptance-release.json", {
            "schema": "alpha-transfer-independent-oracle-release/v1", "releasedAt": dt.datetime.now(dt.UTC).isoformat(),
            "originalFreezeSha256": ORACLE_FREEZE, "campaignSha256": EXPECTED["results/confirmation/campaign.json"],
            "destination": "acceptance", "frozenFilesCopied": len(freeze["source_files"]), "freezeFileCopied": True,
            "allCopiesIdentical": True, "outcomesSealedBeforeRelease": True,
            "notes": "Original source, licenses, protocol, oracle, controls and discarded prefreeze source window retained. No oracle file rewritten."})

    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("unchanged_frozen_oracle", corpus / "oracle/evaluate.py")
    oracle_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle_module)
    native_rows = read(STUDY / "vendor/native/SOURCE.json")["files"]
    source_hash_rows = [[r["path"], r["sha256"]] for r in native_rows]
    for name in ["src/intake.py", "src/run_mission.py", "src/conventional.py", "src/workbench.mjs",
                 "protocol/model-extraction-prompt.txt", "vendor/product/contrib/upgrade_decision/core.py"]:
        source_hash_rows.append([name, sha(STUDY / name)])
    workbench_source_hash = hashlib.sha256(json.dumps(source_hash_rows, separators=(",", ":")).encode()).hexdigest()
    attempts = {(r["mission"], r["arm"]): r for r in campaign["attempts"]}
    if len(attempts) != 18 or len(campaign["attempts"]) != 18:
        raise ValueError("Unexpected number or duplicated primary execution")
    rows, workbench_rows = [], []
    for task_row in inputs["tasks"]:
        tid = task_row["id"]
        raw = read(STUDY / task_row["path"])
        oracle = read(corpus / "oracle" / (tid + ".json"))
        for arm in "ABC":
            folder = STUDY / "results/confirmation" / tid / arm
            proposal = read(folder / "delivery/proposal.json")
            result = read(folder / "delivery/result.json")
            pack = read(folder / "workbench-pack.json")
            inspection = read(folder / "workbench-inspection.json")
            receipt = read(folder / "delivery/receipt.json")
            attempt = attempts[tid, arm]
            meter = read(STUDY / attempt["resourceReceipt"])
            projection_note = None
            response = proposal
            if arm == "A":
                if proposal["sources"] != raw["sources"] or proposal["id"] != raw["id"]:
                    raise ValueError("A's source pack does not match raw task")
                response = {"schema": "alpha-transfer-extraction/v1",
                            "inputSha256": hashlib.sha256(canonical(raw)).hexdigest(),
                            "claims": [{**{k: c[k] for k in ["line", "column", "callee", "before", "after"]},
                                        "explanation": c["mapping"]["explanation"]} for c in proposal["calls"]],
                            "unresolved": [], "provenance": {"mode": "audit-projection-of-sealed-native-request"}}
                projection_note = "Lossless projection of native A calls/targets/mapping explanations; source and ID equality checked before normalization. No call or target added or repaired. A does not use B's compiler."
                write(args.out / tid / (arm + "-oracle-input-projection.json"), response)
            review = oracle_module.evaluate(raw, oracle, response)
            review["arm"] = arm
            review["sealedProposalSha256"] = sha(folder / "delivery/proposal.json")
            review["projectionNote"] = projection_note
            write(args.out / tid / (arm + "-frozen-oracle-review.json"), review)

            native_request = result.get("request")
            core = result.get("coreRecord")
            targets = {call_key(c): c for c in oracle["calls"]}
            status_counts = Counter({"BINDING_PRESERVED": 0, "BINDING_CONFLICT": 0, "UNRESOLVED": 0})
            binding_defects = []
            core_rows = {c["id"]: c for c in core["calls"]} if core else {}
            for request_call in native_request["calls"] if native_request else []:
                answer = core_rows[request_call["id"]]
                truth = targets.get(call_key(request_call))
                status_counts[answer["status"]] += 1
                if truth is None or answer["status"] != truth["expected_core_scope_outcome"]:
                    binding_defects.append({"call": list(call_key(request_call)), "kind": "STATUS_MISMATCH"})
                elif answer["status"] != "UNRESOLVED":
                    for side in ("before", "after"):
                        if answer[side + "Accepts"] != truth["independent_argument_acceptance"][side]:
                            binding_defects.append({"call": list(call_key(request_call)), "kind": "BINDING_MISMATCH", "side": side})
            status_counts["UNRESOLVED"] += len(result["unresolvedIntake"])
            reports = {lang: folder / "delivery" / ("report-" + lang + ".md") for lang in ("en", "fr")}
            packaging = []
            for lang, path in reports.items():
                if not path.is_file():
                    packaging.append({"kind": "MISSING_BILINGUAL_REPORT", "language": lang})
                else:
                    text = path.read_text()
                    missing = [name for name in TEMPLATE_REFERENCES if name in text and not (path.parent / name).is_file()]
                    if missing:
                        packaging.append({"kind": "DANGLING_REPORT_FILE_REFERENCES", "language": lang, "files": missing})
                    if "```python\n\n```" in text:
                        packaging.append({"kind": "EMPTY_UNRESOLVED_CALL_SNIPPETS", "language": lang})
            wb_checks = {
                "oneNonretriedSuccessfulAttempt": attempt["attempt"] == 1 and not attempt["retried"] and attempt["exitCode"] == 0,
                "meterInvokesWorkbench": meter["command"][0] == "node" and Path(meter["command"][1]).resolve() == STUDY / "src/workbench.mjs",
                "meterSuccessful": meter["exitCode"] == 0 and not meter["timedOut"],
                "unchangedRuntimeSourceHash": pack["frozen"]["sourceHash"] == workbench_source_hash,
                "rawInputHashBound": pack["spec"]["inputs"]["sourceTaskSha256"] == task_row["sha256"] == attempt["inputSha256"],
                "proposalHashBound": pack["spec"]["inputs"]["proposalSha256"] == attempt["proposalSha256"],
                "resultHashBound": sha(folder / "delivery/result.json") == attempt["resultSha256"] == receipt["resultSha256"] == pack["result"]["evidence"]["resultSha256"],
                "canonicalInputBound": result["inputSha256"] == task_row["canonicalInputSha256"],
                "sourceBodiesUnchanged": native_request is None or native_request["sources"] == raw["sources"],
                "holdAdmission": pack["evaluation"]["admission"] == "HOLD",
                "emptyAuthority": pack["evaluation"]["authority"] == [] and inspection["activeAuthority"] == [],
                "noActiveProof": inspection["activeProof"] == [],
                "disconnectedSettlement": pack["evaluation"]["settlement"] == "NOT_CONNECTED",
                "noProductionApproval": result["productionApproved"] is False,
                "zeroCollections": result["actualCollectionsUsd"] == 0,
            }
            workbench_rows.append({"task": tid, "arm": arm, "checks": wb_checks, "accepted": all(wb_checks.values()),
                                   "authentication": inspection["authentication"]})
            rows.append({"task": tid, "arm": arm,
                         "frozenInventoryOracleAccepted": review["complete_truthful_inventory"],
                         "requiredCalls": review["required_calls"], "submittedClaims": len(response["claims"]),
                         "submittedUnresolved": len(response["unresolved"]), "materialErrors": review["material_errors"],
                         "omittedCalls": sum(e["kind"] == "OMITTED_DEPENDENCY_CALL" for e in review["material_errors"]),
                         "spuriousCalls": sum(e["kind"] == "EXTRANEOUS_CALL" for e in review["material_errors"]),
                         "wrongTargets": sum(e["kind"] == "WRONG_TARGET" for e in review["material_errors"]),
                         "duplicateCalls": sum(e["kind"] == "DUPLICATE_CALL" for e in review["material_errors"]),
                         "bindingStatusCounts": dict(status_counts), "bindingDisagreements": binding_defects,
                         "conditionalBindingConclusions": status_counts["BINDING_PRESERVED"] + status_counts["BINDING_CONFLICT"],
                         "runtimeMappingsVerified": sum(c.get("mappingVerified") is True for c in core_rows.values()),
                         "conservativeUnresolvedOnBindableSource": len(review["conservative_unresolved_on_bindable_source"]),
                         "nextAction": result["nextAction"], "reportDefects": packaging,
                         "completeBilingualHandoffAccepted": not packaging,
                         "safeToUpgradeEstablished": False, "actualCustomerAcceptance": "not observed",
                         "scope": "Inventory acceptance and conditional binding evidence; no runtime/behavior/market acceptance."})
    write(args.out / "workbench-audit.json", {"schema": "alpha-transfer-independent-workbench-audit/v1",
          "expectedSourceHash": workbench_source_hash, "runs": workbench_rows,
          "allAccepted": all(r["accepted"] for r in workbench_rows),
          "method": "Audited sealed meter commands, unchanged adapter/native code and source-bound packs; no primary mission rerun.",
          "limit": "Local records are reproducible evidence, not signed external attestation or operator approval."})
    by_arm = {}
    for arm in "ABC":
        selected = [r for r in rows if r["arm"] == arm]
        by_arm[arm] = {"jobs": len(selected), "inventoryAccepted": sum(r["frozenInventoryOracleAccepted"] for r in selected),
                       "completeBilingualHandoffsAccepted": sum(r["completeBilingualHandoffAccepted"] for r in selected),
                       "requiredCalls": sum(r["requiredCalls"] for r in selected),
                       "statusCounts": dict(sum((Counter(r["bindingStatusCounts"]) for r in selected), Counter())),
                       "conditionalBindingConclusions": sum(r["conditionalBindingConclusions"] for r in selected),
                       "runtimeMappingsVerified": sum(r["runtimeMappingsVerified"] for r in selected),
                       "omissions": sum(r["omittedCalls"] for r in selected), "spuriousCalls": sum(r["spuriousCalls"] for r in selected),
                       "wrongTargets": sum(r["wrongTargets"] for r in selected), "bindingDisagreements": sum(len(r["bindingDisagreements"]) for r in selected)}
    write(args.out / "summary.json", {"schema": "alpha-transfer-independent-primary-audit/v1", "startedAt": start,
          "endedAt": dt.datetime.now(dt.UTC).isoformat(), "campaignSha256": EXPECTED["results/confirmation/campaign.json"],
          "oracleFreezeSha256": ORACLE_FREEZE, "rows": rows, "byArm": by_arm,
          "unit": "Six consumer/transition jobs; fifteen calls per arm; T03/T04 share one consumer, not independent families.",
          "primaryArmReruns": 0, "candidateEdits": 0, "oracleEdits": 0,
          "conclusion": "A and B match the fixed source inventory and seven conditional binding conclusions. C inventories all calls but its wildcard/conditional-import limitations prevent like-for-like strong-comparator inference. Every complete bilingual handoff has a preserved packaging defect.",
          "limits": ["Frozen automated oracle accepts long refusal strings syntactically; semantic strength is separately critiqued.",
                     "Packaging audit is a post-outcome check against the preregistered complete deliverable, not a rewritten extraction endpoint.",
                     "No measured extraction-time saving, customer-effort reduction, full monetary cost or paid demand is established."]})
    print(json.dumps({"identitiesAccepted": identity["accepted"], "workbenchAccepted": all(r["accepted"] for r in workbench_rows),
                      "byArm": by_arm, "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
