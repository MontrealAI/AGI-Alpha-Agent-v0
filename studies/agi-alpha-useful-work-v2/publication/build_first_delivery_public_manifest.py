# SPDX-License-Identifier: Apache-2.0
"""Build the explicit text-only first-delivery handoff for an additive draft."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "studies/agi-alpha-useful-work-v2/"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    direct = [
        "protocol/intent-charter.json", "protocol/component-contract.json",
        "protocol/component-contract-rationale.md", "protocol/component-projections.json",
        "protocol/verifier-control-record-v2.json", "data/consumer/api.py", "data/consumer/models.py",
        "discovery/test_api_boundary.py", "discovery/requirements/requirements-agent.lock",
        "discovery/release-metadata/fastapi-0.141.1.json",
        "discovery/release-metadata/pydantic-settings-2.15.0.json",
        "discovery/handoff-source-snapshot.json", "discovery/environment-scope-correction.json",
        "discovery/environment-builder-lint.json", "discovery/environment-preparation.md",
        "discovery/first-delivery-review.json", "data/development-baseline-bridge-plan.json",
        "data/development-target-plan.json", "curation/prepare_environment.py",
        "curation/assemble_first_delivery.py", "src/manual_probe.py", "src/verify_component.py",
        "src/measured_run.py", "publication/replay_first_delivery.py",
        "publication/current-consumer-identities.json", "publication/wheel-metadata-index.json",
        "publication/first-delivery-correction.diff", "publication/publish-gates.md",
        "publication/replay-review.json", "publication/attributable-cost-index.json",
        "data/development-baseline-bridge-environment-attempt-1-failed/preparation.json",
    ]
    sources = [(ROOT / name, name) for name in direct]
    sources += [(ROOT / "publication/README-source-handoff.md", "README.md"),
                (ROOT / "native/LICENSE.Alpha", "LICENSE.Alpha")]
    for name in ("results/development/first-delivery", "results/development/first-delivery-corrected",
                 "publication/wheel-metadata"):
        sources.extend((path, str(path.relative_to(ROOT))) for path in sorted((ROOT / name).rglob("*")) if path.is_file())
    rows = []
    for path, relative in sources:
        if path.suffix.lower() in {".pdf", ".docx", ".whl", ".zip", ".pyc"}:
            raise ValueError("NON_TEXT_OR_PRIVATE_SOURCE_IN_HANDOFF")
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        if "\0" in text or any(token in text for token in ("file-inline-libfile_", "oai-library://", "LIBRARY_FILE_ID")):
            raise ValueError("PRIVATE_IDENTIFIER_OR_BINARY_IN_HANDOFF")
        rows.append({"source": str(path), "public_path": PREFIX + relative,
                     "sha256": sha(raw), "bytes": len(raw), "encoding": "utf-8"})
    rows.sort(key=lambda row: row["public_path"])
    if len({row["public_path"] for row in rows}) != len(rows):
        raise ValueError("DUPLICATE_PUBLIC_PATH")
    index = {"schema": "first-delivery-source-handoff-index/v1", "namespace": PREFIX,
             "status": "Prepared local source-only owner handoff; not pushed or live publication",
             "files": [{"path": row["public_path"][len(PREFIX):], "sha256": row["sha256"], "bytes": row["bytes"]}
                       for row in rows],
             "self_binding": "This index is bound by the external publication manifest and eventual Git tree.",
             "scope": "Corrected and historical first-development packets plus required text source and metadata; no binaries.",
             "primary_confirmation": "Not included or executed by this handoff"}
    index_path = ROOT / "publication/source-handoff-artifact-index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    raw = index_path.read_bytes()
    rows.append({"source": str(index_path), "public_path": PREFIX + str(index_path.relative_to(ROOT)),
                 "sha256": sha(raw), "bytes": len(raw), "encoding": "utf-8"})
    rows.sort(key=lambda row: row["public_path"])
    snapshot = json.loads((ROOT / "discovery/handoff-source-snapshot.json").read_text())
    manifest = {"schema": "first-delivery-additive-public-manifest/v1", "repository": "MontrealAI/AGI-Alpha-Agent-v0",
                "branch": "research/agi-alpha-useful-work-v2-20261026", "namespace": PREFIX,
                "observed_base_commit": snapshot["current_main"], "observed_base_tree": snapshot["current_tree"],
                "must_reread_base_before_push": True, "remote_mutations_performed": 0,
                "files": rows, "file_count": len(rows), "total_bytes": sum(row["bytes"] for row in rows),
                "outer_index_sha256": sha(raw), "binary_count": 0, "private_guidance_document_count": 0}
    target = ROOT / "publication/first-delivery-public-manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"manifest": str(target), "sha256": sha(target.read_bytes()),
                      "files": len(rows), "total_bytes": manifest["total_bytes"],
                      "outer_index_sha256": manifest["outer_index_sha256"]}))


if __name__ == "__main__":
    main()
