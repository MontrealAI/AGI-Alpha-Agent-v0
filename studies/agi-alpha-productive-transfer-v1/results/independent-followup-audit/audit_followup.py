# SPDX-License-Identifier: Apache-2.0
"""Summarize independently reviewed sealed follow-up outputs; no arm reruns."""
from pathlib import Path
import datetime as dt
import hashlib
import json
from collections import Counter

STUDY = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CORPUS = STUDY / "acceptance-followup"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open("x") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    expected = {
        "protocol/followup-candidate-freeze.json": "dd4b5446f08851d12a6409783448cfad18179267830d004e1cc53bbb3e543f05",
        "protocol/followup-execution-freeze.json": "1c90ec554574ca5a2f6be8d9e4b251924b40dce51d4a8df5e29de0f3659a0924",
        "protocol/followup-input-freeze.json": "f2e4f453a445c084418dbcb9dd76f8c646870af29d80f9bd04089689c3648950",
        "results/followup/campaign.json": "118c1a938bd7feeacb18baf20214a3250476c24e1d492cf3179aa7f720916870",
    }
    identities = {"schema": "alpha-transfer-followup-independent-identities/v1", "manifests": [], "files": [], "sourceBlobs": []}
    for name, expected_hash in expected.items():
        identities["manifests"].append({"path": name, "sha256": sha(STUDY / name), "accepted": sha(STUDY / name) == expected_hash})
    oracle_freeze = CORPUS / "TASK_ORACLE_FREEZE.json"
    identities["manifests"].append({"path": "acceptance-followup/TASK_ORACLE_FREEZE.json", "sha256": sha(oracle_freeze),
                                    "accepted": sha(oracle_freeze) == "ec3ed14ee561d86df0bce2574be5be1684167635e2a681318a6541b5302e72cb"})
    campaign = read(STUDY / "results/followup/campaign.json")
    for base, name, field in [(CORPUS, "TASK_ORACLE_FREEZE.json", "source_files"),
                              (STUDY, "protocol/followup-candidate-freeze.json", "files"),
                              (STUDY, "protocol/followup-execution-freeze.json", "files"),
                              (STUDY, "results/followup/campaign.json", "payloads"),
                              (STUDY / "vendor/native", "SOURCE.json", "files"),
                              (STUDY / "vendor/product", "source-snapshot.json", "files")]:
        for row in read(base / name)[field]:
            p = base / row["path"]
            identities["files"].append({"manifest": name, "path": row["path"],
                                        "accepted": p.stat().st_size == row["bytes"] and sha(p) == row["sha256"]})
    for row in read(CORPUS / "source-identities-final.json"):
        p = CORPUS / row["file"]
        data = p.read_bytes()
        git_hash = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        identities["sourceBlobs"].append({"file": row["file"], "accepted": git_hash == row["git_blob"] and sha(p) == row["sha256"]})
    identities["accepted"] = all(row["accepted"] for group in ["manifests", "files", "sourceBlobs"] for row in identities[group])
    save("identities.json", identities)
    if not identities["accepted"]:
        raise ValueError("sealed identity mismatch")
    attempts = {(r["mission"], r["arm"]): r for r in campaign["attempts"]}
    assert len(attempts) == len(campaign["attempts"]) == 12
    inputs = {r["id"]: r for r in read(STUDY / "protocol/followup-input-freeze.json")["tasks"]}
    rows, workbench = [], []
    for tid in ["F01", "F02", "F03", "F04"]:
        raw = read(CORPUS / "tasks" / (tid + ".json"))
        input_row = inputs[tid]
        assert (STUDY / input_row["path"]).read_bytes() == (CORPUS / "tasks" / (tid + ".json")).read_bytes()
        oracle = read(CORPUS / "oracle" / (tid + ".json"))
        required_keys = {(r["line"], r["column"], r["callee"]) for r in oracle["calls"]}
        for arm in "ABC":
            folder = STUDY / "results/followup" / tid / arm
            review_path = HERE / "reviews" / f"{tid}-{arm}.json"
            review = read(review_path)
            result = read(folder / "delivery/result.json")
            inventory = read(folder / "delivery/call-inventory.json")
            receipt_path = folder / "delivery/receipt.json"
            receipt = read(receipt_path)
            pack = read(folder / "workbench-pack.json")
            inspection = read(folder / "workbench-inspection.json")
            attempt = attempts[tid, arm]
            meter_path = STUDY / attempt["resourceReceipt"]
            meter = read(meter_path)
            required_counts = Counter(row["status"] for row in inventory if (row["line"], row["column"], row["callee"]) in required_keys)
            observed_counts = Counter(row["status"] for row in inventory)
            defect_calls = {tuple(d["call"]) for d in review["materialErrors"] if d["kind"] in ["EXTRANEOUS_CALL", "SPURIOUS_HANDOFF_CALL"]}
            missing_calls = {tuple(d["call"]) for d in review["materialErrors"] if d["kind"] in ["OMITTED_DEPENDENCY_CALL", "OMITTED_HANDOFF_CALL"]}
            wrong_targets = {tuple(d["call"]) for d in review["materialErrors"] if d["kind"] in ["WRONG_TARGET", "HANDOFF_TARGET_EVIDENCE"]}
            row = {"task": tid, "arm": arm, "inventoryAccepted": review["inventoryAccepted"],
                   "completeHandoffAccepted": review["completeHandoffAccepted"],
                   "requiredCalls": len(required_keys), "submittedCalls": len(inventory),
                   "requiredCallStatusCounts": dict(required_counts), "allSubmittedStatusCounts": dict(observed_counts),
                   "omittedCalls": len(missing_calls), "spuriousCalls": len(defect_calls), "wrongTargetCalls": len(wrong_targets),
                   "spuriousCallLocations": [list(v) for v in sorted(defect_calls)],
                   "materialErrors": review["materialErrors"], "nextAction": result["nextAction"],
                   "bilingualReportsPresent": all((folder / "delivery" / ("report-" + lang + ".md")).is_file() for lang in ["en", "fr"]),
                   "runtimeMappingsVerified": sum(r.get("mappingVerified") is True for r in inventory),
                   "resultSha256": sha(folder / "delivery/result.json"), "deliveryReceiptSha256": sha(receipt_path),
                   "resourceReceiptSha256": sha(meter_path), "independentReviewSha256": sha(review_path),
                   "measuredLocalWallNs": meter["wallNs"], "completeMoneyUsd": None, "actualCollectionsUsd": 0,
                   "actualCustomerAcceptance": "not observed"}
            rows.append(row)
            checks = {
                "onceOnly": attempt["attempt"] == 1 and attempt["retried"] is False and attempt["exitCode"] == 0,
                "workbenchInvoked": meter["command"][0] == "node" and Path(meter["command"][1]).resolve() == STUDY / "src/workbench_v2.mjs",
                "meterSuccessful": meter["exitCode"] == 0 and meter["timedOut"] is False,
                "inputBound": sha(STUDY / input_row["path"]) == input_row["sha256"] == attempt["inputSha256"] == pack["spec"]["inputs"]["sourceTaskSha256"],
                "proposalBound": attempt["proposalSha256"] == pack["spec"]["inputs"]["proposalSha256"],
                "resultBound": row["resultSha256"] == attempt["resultSha256"] == receipt["resultSha256"] == pack["result"]["evidence"]["resultSha256"],
                "sourceClosure": pack["frozen"]["sourceHash"] == read(CORPUS / "candidate-binding.json")["expectedWorkbenchSourceHash"],
                "holdAuthority": pack["evaluation"]["admission"] == "HOLD" and pack["evaluation"]["authority"] == [],
                "noProofOrSettlement": inspection["activeProof"] == [] and inspection["activeAuthority"] == [] and pack["evaluation"]["settlement"] == "NOT_CONNECTED",
                "noApprovalOrCollections": result["productionApproved"] is False and result["actualCollectionsUsd"] == 0,
            }
            workbench.append({"task": tid, "arm": arm, "checks": checks, "accepted": all(checks.values())})
    save("workbench-audit.json", {"schema": "alpha-transfer-independent-followup-workbench/v1", "runs": workbench,
          "accepted": all(r["accepted"] for r in workbench), "primaryReruns": 0,
          "method": "Sealed meter command, source/hash identity and pack audit; no upstream code or primary mission rerun."})
    by_arm = {}
    for arm in "ABC":
        selected = [r for r in rows if r["arm"] == arm]
        counts = Counter()
        for row in selected:
            counts.update(row["requiredCallStatusCounts"])
        by_arm[arm] = {"jobs": 4, "inventoryAccepted": sum(r["inventoryAccepted"] for r in selected),
                       "completeHandoffAccepted": sum(r["completeHandoffAccepted"] for r in selected),
                       "requiredCalls": sum(r["requiredCalls"] for r in selected), "submittedCalls": sum(r["submittedCalls"] for r in selected),
                       "requiredCallStatusCounts": dict(counts), "omittedCalls": sum(r["omittedCalls"] for r in selected),
                       "spuriousCalls": sum(r["spuriousCalls"] for r in selected), "wrongTargetCalls": sum(r["wrongTargetCalls"] for r in selected),
                       "runtimeMappingsVerified": sum(r["runtimeMappingsVerified"] for r in selected)}
    summary = {"schema": "alpha-transfer-independent-followup-audit/v1", "auditedAt": dt.datetime.now(dt.UTC).isoformat(),
               "campaignSha256": expected["results/followup/campaign.json"], "oracleFreezeSha256": sha(oracle_freeze),
               "verifierSha256": sha(CORPUS / "oracle/evaluate_handoff.py"), "inventoryVerifierSha256": sha(CORPUS / "oracle/evaluate_inventory.py"),
               "identitiesAccepted": True, "workbenchAccepted": all(r["accepted"] for r in workbench),
               "rows": rows, "byArm": by_arm, "mutations": {"candidate": 0, "oracle": 0, "primaryOutputs": 0},
               "primaryReruns": 0, "stoppingRule": "No further candidate correction or outcome reselection in this follow-up.",
               "interpretation": "A/B provide four complete scoped handoffs; C2 three. All agree on required conditional bindings/unresolved scope. C2 over-includes two NumPy data-method calls in F03; no unsafe approval or wrong target. No improved full monetary return is identified.",
               "marketBridge": {"fullFourJobEquivalentAcceptanceABC2": False, "equivalentAcceptedTaskIdsABC2": ["F01", "F02", "F04"],
                                "ABEquivalentAcceptedTaskIds": ["F01", "F02", "F03", "F04"], "observedAcceptanceRateIsMarketReliability": False,
                                "customerEffortReductionIdentified": False, "marginalCostReductionIdentified": False,
                                "completeInvestmentMoneyIdentified": False, "actualCollectionsUsd": 0,
                                "financialConclusion": "IDENTIFICATION_HOLD", "freshTaskPopulationInference": "Not supported by four purposive historical jobs."}}
    save("summary.json", summary)
    print(json.dumps({"summarySha256": sha(HERE / "summary.json"), "verifierSha256": summary["verifierSha256"],
                      "byArm": by_arm, "workbenchAccepted": summary["workbenchAccepted"]}, indent=2))


if __name__ == "__main__":
    main()
