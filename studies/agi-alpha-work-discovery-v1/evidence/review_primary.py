# SPDX-License-Identifier: Apache-2.0
"""Independent read-only reconciliation of frozen primary result records."""
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
    campaign_path = study / "outputs/primary/campaign.json"
    campaign = json.loads(campaign_path.read_text())
    protocol = json.loads((study / "protocol/production.json").read_text())
    source_check = verify_freeze(
        study, study / "protocol/production-freeze.json", campaign["finalSourceCheck"]["sha256"]
    )
    assert sha((study / "inputs/acquired/manifest.json").read_bytes()) == campaign["inputManifestSha256"]
    assert len(campaign["records"]) == len(protocol["primary_pairs"]) * 4
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

    for number, pair in enumerate(protocol["primary_pairs"]):
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
        a = json.loads((study / "outputs/primary" / conventional["id"] / "service/dossier.json").read_text())
        expected = independent_tuples(a["changes"])
        for record in rows:
            assert record["acceptance"]["accepted"] is True
            assert len(record["processes"]) == 2
            assert all(process["exit"] == 0 and not process["timedOut"] for process in record["processes"])
            assert record["cpuSeconds"] >= sum(process["cpuSeconds"] for process in record["processes"])
            if record["arm"] == "A":
                continue
            b = donor_dossier(study / "outputs/primary" / record["id"] / "service")
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
    report = {
        "schema": "independent-primary-review/v1",
        "status": "PASS_SCOPED_RECONCILIATION",
        "startedAt": start_at,
        "completedAt": now(),
        "campaignSha256": sha(campaign_path.read_bytes()),
        "reviewSourceSha256": sha(Path(__file__).read_bytes()),
        "frozenSourceCheck": source_check,
        "plannedRecords": len(campaign["records"]),
        "pairResults": pair_results,
        "arms": resource,
        "independentAcceptance": "Every available output previously passed the frozen independent oracle; this additional read-only review reconciles all tuple facts, changed-node provenance and full inventory counts between the four arms, without rerunning producers.",
        "limitations": [
            "Three unavailable source questions remain in the denominator; no replacements.",
            "Correlated historical versions and one execution per arm do not estimate population reliability or speed variance.",
            "Structural schema agreement is not live Docker compatibility or buyer acceptance.",
            "No paid demand, complete monetary cost or measured human-only time is established.",
        ],
        "auditCpuSeconds": time.process_time() - start_cpu,
        "auditWallSeconds": time.perf_counter() - start_wall,
        "auditCostClassification": "Additional research validation, separate from already measured primary service execution.",
    }
    save(study / "evidence/independent-primary-review.json", report)
    (study / "evidence/review_primary.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
