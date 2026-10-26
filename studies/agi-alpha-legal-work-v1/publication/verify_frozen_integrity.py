# SPDX-License-Identifier: Apache-2.0
"""Read-only frozen-evidence verification; output is a separate audit receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ANCHORS = {
    "protocol/production-freeze.json": "7b4b0afed9861ed59d53e146d7b2d63b2ffb22a999d878344cb761000d6ad85b",
    "protocol/corpus-freeze.json": "e81fbb667c6877c9fb88f45ddcdf9918ceb30479188ed931a19f977188c2bfc2",
    "protocol/prediction-seal.json": "08e4ffb331dfed4177f0926ae19c4b0e2afd0af33454006258cba7566cc94622",
    "protocol/key-release.json": "598a1560fe5f7e311c16c0328a9367ee88e58116d8a70ba688d175280045853e",
    "protocol/reconciliation-source-freeze.json": "3f41122d1e89e8a42916816bd0aca90905b7b7edfd43ec552b6898c9531c09ae",
    "protocol/reconciliation-corpus-freeze.json": "086a97337176a991715a3adbe59a2f30da4df6875ebf217d36c4089e9d2c2df5",
    "protocol/reconciliation-prediction-seal.json": "6e048513e1b4773e0651bf22ed8aee1c407a16302d97757434681e76c15ed5d0",
    "protocol/reconciliation-key-release.json": "f68e26be5058321133d61e61b26c854793ec1e70af354b16dd62f3c10ba7871f",
    "evaluation/source-freeze.json": "c4f5d21ecf057707dd33e753eade2f93003ed2f4c1576f99e36cbcd355ee6c52",
    "evaluation/reconciliation-source-freeze.json": "e73fb354a001754eccc46ab57b1b3718a3ccd942226dfd54840e62edb4eb3b30",
    "evaluation/history/independent-before-shared-integrity-review/source-freeze.json": "f7e8b3e757f60fc71d04ec9f0449eb307d06c3ea985f92d4596704161790fc51",
    "economics/source-freeze.json": "e441adeafc444247159dc849158ff6adf4cbaabcddc445aaa45307733aa82e7a",
    "economics/secondary-source-freeze.json": "ebd4ea2679e43dd60ada1dec45f9e103de8c5f8fdfd3d8009ada9bea6d3290e1",
    "economics/history/model-v1/source-freeze.json": "0475d13807a510ad1f4d7a75ac73472b0d5e77f801f08ab8e4cf9044c8efc578",
    "economics/results/primary-v2/results-freeze.json": "059164d92544d45801fea6f025a6f87d0e7169cf1759ac02d7e95154f8db1c9e",
}


def audit() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    cached: dict[str, tuple[str, int]] = {}

    def identity(relative: str) -> tuple[str, int]:
        if relative not in cached:
            data = (ROOT / relative).read_bytes()
            cached[relative] = hashlib.sha256(data).hexdigest(), len(data)
        return cached[relative]

    def read(relative: str) -> Any:
        return json.loads((ROOT / relative).read_text())

    def verify(label: str, relative: str, expected: str, size: int | None = None) -> None:
        try:
            digest, actual_size = identity(relative)
            valid = digest == expected and (size is None or size == actual_size)
            row = {
                "label": label,
                "path": relative,
                "sha256": digest,
                "expected_sha256": expected,
                "bytes": actual_size,
                "expected_bytes": size,
                "matches": valid,
            }
        except FileNotFoundError:
            row = {"label": label, "path": relative, "matches": False, "error": "MISSING_FILE"}
        records.append(row)
        if not row["matches"]:
            issues.append(row)

    specifications = [
        ("protocol/production-freeze.json", "", "files"),
        ("protocol/prediction-seal.json", "", "files"),
        ("protocol/reconciliation-source-freeze.json", "", "files"),
        ("protocol/reconciliation-prediction-seal.json", "", "files"),
        ("evaluation/source-freeze.json", "evaluation", "files"),
        ("evaluation/reconciliation-source-freeze.json", "", "files"),
        (
            "evaluation/history/independent-before-shared-integrity-review/source-freeze.json",
            "evaluation/history/independent-before-shared-integrity-review",
            "files",
        ),
        ("economics/source-freeze.json", "economics", "files"),
        ("economics/history/model-v1/source-freeze.json", "economics/history/model-v1", "files"),
        ("economics/results/primary-v2/results-freeze.json", "", "files"),
        ("economics/results/reconciliation/results-freeze.json", "", "files"),
        ("graph/source-freeze.json", "graph", "files"),
        ("graph/history/instrumentation-v1/source-freeze.json", "graph", "files"),
        ("graph/source-provenance.json", "graph", "files"),
        ("graph/inherited/assets/production-freeze.json", "", "files"),
        ("heritage/alpha-source-manifest.json", "heritage/alpha", "files"),
        ("economics/inherited-manifest.json", "economics", "source_files"),
        ("economics/history/model-v1/inherited-manifest.json", "economics/history/model-v1", "source_files"),
    ]
    for manifest, base, key in specifications:
        data = read(manifest)
        before = len(records)
        for entry in data[key]:
            relative = str(Path(base) / entry["path"])
            if manifest == "graph/history/instrumentation-v1/source-freeze.json" and entry["path"] == "legal-graph.mjs":
                relative = "graph/history/instrumentation-v1/legal-graph.mjs"
            verify(manifest, relative, entry["sha256"], entry.get("bytes"))
        manifests.append(
            {
                "path": manifest,
                "sha256": identity(manifest)[0],
                "file_references_verified": len(records) - before,
                "all_references_match": all(r["matches"] for r in records[before:]),
            }
        )
    for manifest, author in [
        ("protocol/corpus-freeze.json", "evaluation/private-keys/author_corpus.py"),
        ("protocol/reconciliation-corpus-freeze.json", "evaluation/private-keys/author_reconciliation.py"),
    ]:
        data, before = read(manifest), len(records)
        for entry in data["cases"]:
            verify(manifest, entry["input_path"], entry["input_sha256"])
            verify(manifest, entry["key_path"], entry["key_sha256"])
        verify(manifest, author, data["authoring_file_sha256"])
        manifests.append(
            {
                "path": manifest,
                "sha256": identity(manifest)[0],
                "cases": len(data["cases"]),
                "file_references_verified": len(records) - before,
                "all_references_match": all(r["matches"] for r in records[before:]),
            }
        )
    second = read("economics/secondary-source-freeze.json")
    verify(
        "economics/secondary-source-freeze.json", second["source_file"], second["source_sha256"], second["source_bytes"]
    )
    for relative, expected in ANCHORS.items():
        verify("PREVIOUSLY_RECORDED_MANIFEST_IDENTITY", relative, expected)
    link_specifications = [
        ("protocol/corpus-freeze.json", "production_freeze_sha256", "protocol/production-freeze.json"),
        ("protocol/prediction-seal.json", "production_freeze_sha256", "protocol/production-freeze.json"),
        ("protocol/prediction-seal.json", "corpus_freeze_sha256", "protocol/corpus-freeze.json"),
        ("protocol/key-release.json", "production_freeze_sha256", "protocol/production-freeze.json"),
        ("protocol/key-release.json", "corpus_freeze_sha256", "protocol/corpus-freeze.json"),
        ("protocol/key-release.json", "prediction_seal_sha256", "protocol/prediction-seal.json"),
        (
            "protocol/reconciliation-source-freeze.json",
            "first_source_freeze_preserved",
            "protocol/production-freeze.json",
        ),
        (
            "protocol/reconciliation-corpus-freeze.json",
            "source_freeze_sha256",
            "protocol/reconciliation-source-freeze.json",
        ),
        ("protocol/reconciliation-corpus-freeze.json", "plan_sha256", "protocol/reconciliation-corpus-plan.json"),
        (
            "protocol/reconciliation-prediction-seal.json",
            "source_freeze_sha256",
            "protocol/reconciliation-source-freeze.json",
        ),
        (
            "protocol/reconciliation-prediction-seal.json",
            "corpus_freeze_sha256",
            "protocol/reconciliation-corpus-freeze.json",
        ),
        (
            "protocol/reconciliation-key-release.json",
            "source_freeze_sha256",
            "protocol/reconciliation-source-freeze.json",
        ),
        (
            "protocol/reconciliation-key-release.json",
            "corpus_freeze_sha256",
            "protocol/reconciliation-corpus-freeze.json",
        ),
        (
            "protocol/reconciliation-key-release.json",
            "prediction_seal_sha256",
            "protocol/reconciliation-prediction-seal.json",
        ),
        ("economics/results/primary-v2/results-freeze.json", "source_freeze_sha256", "economics/source-freeze.json"),
        ("economics/results/primary-v2/input-provenance.json", "productionSHA256", "economics/production-input.json"),
        ("economics/results/primary-v2/input-provenance.json", "sourceSHA256", "economics/legal-market.mjs"),
        ("economics/results/primary-v2/input-provenance.json", "parametersSHA256", "economics/parameters.json"),
        (
            "economics/results/reconciliation/input-provenance.json",
            "inputSHA256",
            "economics/reconciliation-production-input.json",
        ),
        ("economics/results/reconciliation/input-provenance.json", "sourceSHA256", "economics/secondary-unit.mjs"),
    ]
    for manifest, key, target in link_specifications:
        verify(manifest + ":" + key, target, read(manifest)[key])
    chronology = []
    for prefix, source_name in [("", "production-freeze"), ("reconciliation-", "reconciliation-source-freeze")]:
        items = [
            ("protocol/" + source_name + ".json", "frozen_at"),
            ("protocol/" + prefix + "corpus-freeze.json", "created_at_utc"),
            ("protocol/" + prefix + "prediction-seal.json", "sealed_at"),
            ("protocol/" + prefix + "key-release.json", "released_at_utc"),
        ]
        times = [datetime.fromisoformat(read(name)[key]) for name, key in items]
        ordered = all(a < b for a, b in pairwise(times))
        chronology.append(
            {"cohort": prefix or "first", "strict_order": ordered, "timestamps": [x.isoformat() for x in times]}
        )
        if not ordered:
            issues.append({"label": "CUSTODY_CHRONOLOGY", "cohort": prefix})
    prior = read("publication/independent-claims-review.json")
    publications = [
        {
            **entry,
            "current_sha256": identity(entry["path"])[0],
            "unchanged_since_claims_review": identity(entry["path"])[0] == entry["sha256"],
        }
        for entry in prior["reviewed_files"]
    ]
    for entry in prior["evidence_files"]:
        verify("PRIOR_CLAIMS_REVIEW_EVIDENCE", entry["path"], entry["sha256"])
    demo_payload = {
        "primary": read("evidence/production-summary.json")["acceptance"]["primary"],
        "reconciliation": read("evidence/reconciliation-independent-audit.json"),
        "packets": [
            read(str(p.relative_to(ROOT))) for p in sorted((ROOT / "evidence/reconciliation").glob("*/*/packet.json"))
        ],
        "thresholds": read("economics/results/reconciliation/unit-thresholds.json")["demandThresholds"],
        "assumptions": read("economics/results/reconciliation/unit-thresholds.json")["assumptions"],
    }
    expected_demo = (
        (ROOT / "demo/template.html")
        .read_text()
        .replace("__EVIDENCE_JSON__", json.dumps(demo_payload, ensure_ascii=False).replace("<", "\\u003c"))
    )
    verify(
        "GENERATED_DEMO_EXACT_SOURCE_AND_EVIDENCE_BINDING",
        "demo/AGI_ALPHA_Legal_Work_Demo.html",
        hashlib.sha256(expected_demo.encode()).hexdigest(),
    )
    incremental_review = read("publication/final-claims-addendum.json")
    for entry in incremental_review["files"]:
        verify("INCREMENTAL_MANUAL_CLAIMS_REVIEW_IDENTITY", entry["path"], entry["sha256"])
    incremental_review_sha256 = identity("publication/final-claims-addendum.json")[0]
    return {
        "schema": "independent-final-integrity-audit/v1",
        "audited_at": datetime.now(UTC).isoformat(),
        "all_verified_references_match": not issues,
        "file_reference_checks": len(records),
        "unique_files_hashed": len(cached),
        "previously_recorded_manifest_identities_checked": len(ANCHORS),
        "manifests": manifests,
        "chronology": chronology,
        "publication_files_since_prior_claims_review": publications,
        "incremental_manual_claims_review": {
            "path": "publication/final-claims-addendum.json",
            "sha256": incremental_review_sha256,
            "result": incremental_review["result"],
            "new_factual_contradictions": incremental_review["new_factual_contradictions"],
        },
        "issues": issues,
        "checks": records,
        "historical_resolution_rule": "Historical D and economics v1 files use their preserved directories. Historical graph instrumentation uses its preserved legal-graph.mjs; unchanged dependencies remain in graph/ and must match the historical hashes. No replacement is selected by searching for a matching digest.",
        "limits": [
            "Hashes and declared timestamps are local research custody evidence, not signed external identity or an independent trusted timestamp.",
            "Vendored source bytes are checked against retained manifests; this audit does not re-fetch remote repositories or authenticate a live ENS account.",
            "No production, economic campaign or efficacy experiment is rerun by this integrity audit.",
            "Publication hash changes require the accompanying manual incremental claim review; exact generated demo binding is independently checked.",
            "Rendered PDF/browser visual acceptance and final ZIP extraction/replay are separate checks.",
            "No frozen source, case, key, prediction or economic result is changed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="publication/final-integrity-audit.json")
    args = parser.parse_args()
    result = audit()
    target = ROOT / args.output
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in [
                    "all_verified_references_match",
                    "file_reference_checks",
                    "unique_files_hashed",
                    "issues",
                    "publication_files_since_prior_claims_review",
                ]
            }
        )
    )
    if not result["all_verified_references_match"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
