# SPDX-License-Identifier: Apache-2.0
"""Aggregate a sealed confirmation with the unchanged independent checker."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reconciliation_check import check

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FREEZE_HASH = "3f41122d1e89e8a42916816bd0aca90905b7b7edfd43ec552b6898c9531c09ae"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--seal", required=True)
    parser.add_argument("--seal-sha256", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", default="evidence/reconciliation-independent-audit.json")
    parser.add_argument("--economic-input", default="economics/reconciliation-production-input.json")
    args = parser.parse_args()
    source_path = ROOT / "protocol/reconciliation-source-freeze.json"
    require(digest(source_path) == SOURCE_FREEZE_HASH, "Second source-freeze identity changed")
    source = read(source_path)
    for file in source["files"]:
        require(digest(ROOT / file["path"]) == file["sha256"], "Frozen source changed: " + file["path"])
    seal_path = ROOT / args.seal
    require(digest(seal_path) == args.seal_sha256, "Prediction seal identity changed")
    seal, release, corpus = read(seal_path), read(ROOT / args.release), read(ROOT / args.corpus)
    require(len(corpus["cases"]) == source["expected_fresh_cases"], "Confirmation case count differs from frozen scope")
    require(release["prediction_seal_sha256"] == args.seal_sha256, "Keys not released against this prediction seal")
    require(release["corpus_freeze_sha256"] == digest(ROOT / args.corpus), "Key release corpus mismatch")
    for file in seal["files"]:
        require(digest(ROOT / file["path"]) == file["sha256"], "Sealed prediction changed: " + file["path"])
    evidence = ROOT / args.evidence
    analysis_records = read(evidence / "records.json")
    native_records = read(evidence / "native-records.json")["records"]
    analysis = {(row["case_id"], row["method"]): row for row in analysis_records}
    native = {(row["case_id"], row["method"]): row for row in native_records}
    require(len(analysis) == len(analysis_records), "Duplicate Python production record")
    require(len(native) == len(native_records), "Duplicate native production record")
    evaluations, costs = [], []
    scoring_start = time.perf_counter()
    for item in corpus["cases"]:
        input_path, key_path = ROOT / item["input_path"], ROOT / item["key_path"]
        require(digest(input_path) == item["input_sha256"], "Frozen case changed")
        require(digest(key_path) == item["key_sha256"], "Frozen annotation changed")
        case, key = read(input_path), read(key_path)
        require(case["case_id"] == item["case_id"] == key["case_id"], "Case identity mismatch")
        for method in ["characters", "lines"]:
            packet_path = evidence / case["case_id"] / method / "packet.json"
            packet = read(packet_path)
            require(packet["method"] == method, "Production method identity mismatch")
            row = check(case, packet)
            row["stratum"] = item["stratum"]
            row["key_source_hash_match"] = packet["source_hashes"] == key["input_hashes"]
            row["key_amendment_identity_match"] = sorted(x["id"] for x in case["amendments"]) == sorted(
                key["required_amendment_ids"]
            )
            require(
                row["key_source_hash_match"] and row["key_amendment_identity_match"],
                "Independent identity key mismatch",
            )
            require(key["legal_semantics_assessed"] is False, "Unsupported legal key")
            identity = (case["case_id"], method)
            produced, packaged = analysis[identity], native[identity]
            require(produced["packet_sha256"] == digest(packet_path), "Production receipt packet mismatch")
            row["runtime_seconds"] = produced["seconds"] + packaged["elapsed_seconds"]
            row["cpu_seconds"] = produced["cpu_seconds"] + packaged["cpu_seconds"]
            evaluations.append(row)
            costs.append(
                {
                    "case_id": case["case_id"],
                    "method": method,
                    "accepted_deterministic": row["accepted_independent"],
                    "runtime_seconds": row["runtime_seconds"],
                    "cpu_seconds": row["cpu_seconds"],
                    "attempts": 1,
                    "professional_acceptance": "unknown",
                    "professional_review_minutes": None,
                    "observed_collections_cents": 0,
                    "packet_sha256": digest(packet_path),
                }
            )
    scoring_seconds = time.perf_counter() - scoring_start
    expected = len(corpus["cases"]) * 2
    require(
        len(evaluations) == len(analysis_records) == len(native_records) == expected, "Incomplete production inventory"
    )
    summaries = {}
    for method in ["characters", "lines"]:
        rows = [row for row in evaluations if row["method"] == method]
        sums = {
            field: sum(row[field] for row in rows)
            for field in [
                "valid_spans",
                "operations",
                "changed_operations",
                "original_codepoints",
                "revised_codepoints",
                "unchanged_codepoints",
                "highlighted_original_codepoints",
                "highlighted_revised_codepoints",
                "amendments_preserved",
                "runtime_seconds",
                "cpu_seconds",
            ]
        }
        summaries[method] = {
            "cases": len(rows),
            "accepted_independent": sum(row["accepted_independent"] for row in rows),
            **sums,
            "mean_runtime_seconds": statistics.mean(row["runtime_seconds"] for row in rows),
            "median_runtime_seconds": statistics.median(row["runtime_seconds"] for row in rows),
            "weighted_preserved_context_ratio": {
                version: sums["unchanged_codepoints"] / sums[version + "_codepoints"]
                if sums[version + "_codepoints"]
                else 1.0
                for version in ["original", "revised"]
            },
            "professional_acceptance": "unknown",
            "localization_assessed": False,
        }
    result = {
        "schema": "independent-reconciliation-confirmation-audit/v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source_freeze_sha256": SOURCE_FREEZE_HASH,
        "corpus_freeze_sha256": digest(ROOT / args.corpus),
        "prediction_seal_sha256": args.seal_sha256,
        "source_files_verified": len(source["files"]),
        "prediction_files_verified": len(seal["files"]),
        "source_or_prediction_changes": 0,
        "summary": summaries,
        "subsequent_independent_scoring_seconds": scoring_seconds,
        "records": evaluations,
        "limits": [
            "Acceptance proves exact conservation under the frozen checker, not useful localization, preserved meaning or professional acceptance.",
            "Production time sums recorded Python generation/verification/HTML/write and native read/package/write; independent scoring is separate.",
            "Handling, professional review, integration, support, maintenance and historical authoring costs remain unmeasured.",
            "Both methods are ordinary standard-library comparisons; no newly retained capability, human advantage or commercial superiority is established.",
            "All cases are fresh synthetic research cases; no actual customer recurrence, invoice or collection is observed.",
        ],
    }
    (ROOT / args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (ROOT / args.economic_input).write_text(
        json.dumps(
            {
                "schema": "reconciliation-measured-production/v1",
                "basis": "Mechanically checked fresh synthetic production; professional and commercial acceptance unassessed.",
                "records": costs,
                "prediction_seal_sha256": args.seal_sha256,
                "observed_collections_cents": 0,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"summary": summaries, "output": args.output, "economic_input": args.economic_input}))


if __name__ == "__main__":
    main()
