# SPDX-License-Identifier: Apache-2.0
"""Independent read-only reconciliation of the separately registered secondary transfer."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("study", type=Path)
    args = parser.parse_args()
    study: Path = args.study.resolve()
    sys.path.insert(0, str(study / "src"))
    from production_campaign import now, save, sha, verify_freeze

    start_at, start_cpu, start_wall = now(), time.process_time(), time.perf_counter()
    campaign_path = study / "outputs/secondary-transfer/campaign.json"
    campaign = json.loads(campaign_path.read_text())
    protocol = json.loads((study / "protocol/secondary-transfer.json").read_text())
    source_check = verify_freeze(
        study, study / "protocol/production-freeze.json", campaign["finalSourceCheck"]["parentCheck"]["sha256"]
    )
    assert sha((study / "inputs/acquired/manifest.json").read_bytes()) == campaign["inputManifestSha256"]
    assert len(campaign["records"]) == len(protocol["transfer_pairs"]) * 4
    assert len({record["id"] for record in campaign["records"]}) == len(campaign["records"])
    pair_results: list[dict[str, Any]] = []

    def donor_dossier(directory: Path) -> dict[str, Any]:
        direct = directory / "response-dossier.json"
        index = directory / "response-dossier-index.json"
        assert direct.exists() != index.exists()
        if direct.exists():
            result: dict[str, Any] = json.loads(direct.read_text())
            return result
        manifest = json.loads(index.read_text())
        joined = "".join((directory / name).read_text() for name in manifest["parts"])
        assert sha(joined.encode()) == manifest["digest"]
        return dict(json.loads(joined))

    def independent_tuples(changes: list[dict[str, Any]]) -> dict[str, Any]:
        values = {}
        for row in changes:
            key = json.dumps(row["key"], ensure_ascii=False, separators=(",", ":"))
            assert key not in values
            before, after = row["before"], row["after"]
            values[key] = [
                row["kind"],
                before["facts"] if before else None,
                after["facts"] if after else None,
                before["sourcePointer"] if before else None,
                after["sourcePointer"] if after else None,
                before["refChain"] if before else [],
                after["refChain"] if after else [],
            ]
        return values

    for number, pair in enumerate(protocol["transfer_pairs"]):
        rows = [record for record in campaign["records"] if record["pair"] == pair]
        rotation = "ABCD"[number % 4 :] + "ABCD"[: number % 4]
        assert "".join(record["arm"] for record in sorted(rows, key=lambda record: record["order"])) == rotation
        assert len(rows) == 4
        accepted = [record for record in rows if record["accepted"]]
        if not accepted:
            assert all(record["status"] == "INPUT_ACQUISITION_FAILED" and record["processes"] == [] for record in rows)
            pair_results.append(
                {"pair": pair, "status": "SOURCE_BLOCKED_ALL_FOUR_ARMS", "attemptedExecutableDeliveries": 0}
            )
            continue
        assert len(accepted) == 4
        conventional = next(record for record in rows if record["arm"] == "A")
        a = json.loads((study / "outputs/secondary-transfer" / conventional["id"] / "service/dossier.json").read_text())
        expected = independent_tuples(a["changes"])
        for record in rows:
            assert record["acceptance"]["accepted"] is True
            assert len(record["processes"]) == 2
            assert all(process["exit"] == 0 and not process["timedOut"] for process in record["processes"])
            assert record["cpuSeconds"] >= sum(process["cpuSeconds"] for process in record["processes"])
            if record["arm"] == "A":
                continue
            b = donor_dossier(study / "outputs/secondary-transfer" / record["id"] / "service")
            actual = {}
            for row in b["changes"]:
                assert row["key"] not in actual
                actual[row["key"]] = [
                    row["kind"],
                    row["oldFacts"],
                    row["newFacts"],
                    row["oldPointer"],
                    row["newPointer"],
                    row["oldRefChain"],
                    row["newRefChain"],
                ]
            assert actual == expected
            assert b["counts"]["old"]["nodes"] == len(a["before"]["rows"])
            assert b["counts"]["new"]["nodes"] == len(a["after"]["rows"])
            assert b["counts"]["old"]["responses"] == len(a["before"]["responses"])
            assert b["counts"]["new"]["responses"] == len(a["after"]["responses"])
        pair_results.append(
            {
                "pair": pair,
                "status": "EXACT_FOUR_ARM_SCOPED_FACT_AND_PROVENANCE_MATCH",
                "changes": len(expected),
                "beforeNodes": len(a["before"]["rows"]),
                "afterNodes": len(a["after"]["rows"]),
                "wholeRuntimeCompatibility": "UNASSESSED",
            }
        )
    resource = {}
    for arm in "ABCD":
        rows = [record for record in campaign["records"] if record["arm"] == arm]
        accepted_count = sum(record["accepted"] for record in rows)
        cpu = sum(record["cpuSeconds"] for record in rows)
        resource[arm] = {
            "planned": len(rows),
            "accepted": accepted_count,
            "conditionalAccepted": accepted_count,
            "conditionalAttempted": sum(bool(record["processes"]) for record in rows),
            "cpuSecondsAllCases": cpu,
            "cpuSecondsPerAcceptedIncludingFailures": cpu / accepted_count,
            "sharedAcquisitionCpuSeconds": sum(record["sharedAcquisitionCpuSeconds"] for record in rows),
        }
    secondary_manifest = study / "protocol/secondary-transfer-freeze.json"
    secondary_identity = (study / "protocol/secondary-transfer-freeze.sha256").read_text().split()[0]
    secondary_check = verify_freeze(study, secondary_manifest, secondary_identity)
    recipient_root = study / "comparators/recipient"
    recipient_summary_path = recipient_root / "secondary-transfer/summary.json"
    recipient_summary = json.loads(recipient_summary_path.read_text())
    recipient_receipt = json.loads(
        (recipient_root / "secondary-transfer/shared-raw-swagger-validation-receipt.json").read_text()
    )
    assert recipient_summary["status"] == "HOLD_INPUT_VALIDATION_FAILED"
    assert recipient_summary["efficacyAttemptsPerArm"] == 0
    assert recipient_summary["efficacyRetries"] == 0
    assert all(
        not row["executed"] and row["status"] == "NOT_RUN_INPUT_VALIDATION_FAILED" for row in recipient_summary["arms"]
    )
    assert recipient_receipt["exitCode"] != 0
    assert "UnpackedSize" in recipient_receipt["stderr"]
    recipient_source_checks = {}
    for name, field in [("pretransfer-freeze.json", "source_and_evidence_sha256"), ("transfer-freeze.json", "files")]:
        frozen = json.loads((recipient_root / name).read_text())
        for relative, expected_sha256 in frozen[field].items():
            assert sha((recipient_root / relative).read_bytes()) == expected_sha256
        recipient_source_checks[name] = {
            "sha256": sha((recipient_root / name).read_bytes()),
            "boundFilesVerified": len(frozen[field]),
        }
    report = {
        "schema": "independent-secondary-review/v1",
        "status": "PASS_SCOPED_RECONCILIATION",
        "startedAt": start_at,
        "completedAt": now(),
        "campaignSha256": sha(campaign_path.read_bytes()),
        "reviewSourceSha256": sha(Path(__file__).read_bytes()),
        "frozenSourceCheck": source_check,
        "secondarySourceCheck": secondary_check,
        "plannedRecords": len(campaign["records"]),
        "pairResults": pair_results,
        "arms": resource,
        "recipient": {
            "status": "HOLD_INPUT_VALIDATION_FAILED",
            "efficacy": "NOT_RUN_NO_PRE_POST_PERFORMANCE_OR_CAPABILITY_COMPARISON",
            "summarySha256": sha(recipient_summary_path.read_bytes()),
            "sourceChecks": recipient_source_checks,
            "observedSharedValidationWallSeconds": recipient_receipt["wallSeconds"],
            "observedSharedValidationCpuSeconds": recipient_receipt["cpuSeconds"],
            "costAllocation": "One shared failed validation attempt, not three hypothetical executions; no monetary or human zero inferred.",
            "scope": "Recipient's frozen input qualification is stricter than the four-arm structural acceptance. The failure cannot establish recipient inferiority or donor improvement. Specific diagnostic adjudication remains separately attributed to the recipient's standards review.",
        },
        "acquisitionCostQualification": "The secondary campaign reused already acquired inputs. Its sharedAcquisition fields allocate historical acquisition for attribution or prospective standalone costing; these are not new acquisition execution and must not be added again to consolidated historical cost.",
        "concurrencyQualification": "Root reported browser QA during 21:20:06–21:20:17 UTC, overlapping the secondary service interval 21:20:06–21:20:13 UTC. Host-load effects are unquantified. Per-child CPU remains scoped to the measured processes, but neither wall nor CPU differences establish a replicated speed advantage. No rerun was performed.",
        "independentAcceptance": "Every available output previously passed the unchanged frozen independent oracle; this additional read-only review reconciles all tuple facts, changed-node provenance and full inventory counts between the four arms, without rerunning producers.",
        "limitations": [
            "Exploratory content-different successor only; excluded from primary economic calibration. Original identical and blocked transfer cases remain unchanged.",
            "Correlated historical versions and one execution per arm do not estimate population reliability or speed variance.",
            "Structural schema agreement is not live Docker compatibility or buyer acceptance.",
            "No paid demand, complete monetary cost or measured human-only time is established.",
        ],
        "auditCpuSeconds": time.process_time() - start_cpu,
        "auditWallSeconds": time.perf_counter() - start_wall,
        "auditCostClassification": "Additional research validation, separate from already measured secondary service execution.",
    }
    save(study / "evidence/independent-secondary-review.json", report)
    (study / "evidence/review_secondary.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
