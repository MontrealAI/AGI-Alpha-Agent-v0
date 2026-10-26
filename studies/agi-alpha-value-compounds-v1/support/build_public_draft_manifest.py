# SPDX-License-Identifier: Apache-2.0
"""Prepare a text-only additive source handoff; never writes to GitHub."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "studies/agi-alpha-value-compounds-v1/"
FORBIDDEN_SUFFIXES = {".pdf", ".zip", ".whl", ".pyc", ".png", ".jpg", ".jpeg", ".so", ".woff", ".woff2"}
FIXED = [
    "protocol.json", "native/SOURCE.json", "data/missions.json", "data/confirmation-missions.json",
    "data/confirmation/source-custody.json", "data/confirmation-registry-integration.json",
    "data/development/manifest.json", "data/confirmation-licenses/manifest.json",
    "discovery/final-freeze.json", "discovery/confirmation-metadata-v3.json",
    "discovery/confirmation-metadata-v2.json", "discovery/confirmation-metadata.json",
    "discovery/protocol-v1-preserved.json", "discovery/protocol-v2-preserved.json",
    "discovery/source-audit.md", "discovery/final-status.json", "discovery/source-file-identities.json", "discovery/urllib3-dependency-evidence.json",
    "discovery/opportunity-review.md", "discovery/commercial-screen.md", "discovery/conventional-method.md",
    "discovery/consumer-methods.md", "discovery/economics.md", "discovery/call-compatibility-review.md",
    "discovery/candidate-development-01.json", "discovery/candidate-development-02.json",
    "discovery/final-frozen-tests.log", "discovery/candidate-development-final-v3.log",
    "discovery/workbench-negative-controls.json", "discovery/publication-path.md",
    "results/summary.json", "results/outcomes.csv", "results/candidate-rejection.json", "results/final-admission.json",
    "results/provisional-admission.json", "results/native-refusal-summary.json", "results/confirmation/runs.json",
    "results/analysis-summary.log", "results/ablation-summary.log",
    "publication/confirmation-failure-analysis.md", "publication/confirmation-failure-analysis-v1.md",
    "publication/primary-independent-review.md", "publication/independent-product-review.md",
    "publication/independent-product-review.json", "publication/methods-draft.tex",
    "publication/economics-review.md", "publication/overlay-final-closure.md",
    "support/README-reproduction.md", "support/requirements-replay.lock", "support/dependency-manifest.json",
    "support/completeness.json", "support/verification/manifest.json",
    "support/verification/failed-run-01/FAILED.json", "support/verification/successful-run-02/summary.json",
    "support/verification/successful-run-02/environment.json", "support/verification/successful-run-02/operations.json",
]
GLOBS = ["src/*.py", "src/*.mjs", "src/*.md", "tests/*.py", "tests/*.mjs", "curation/*.py",
         "support/*.py", "analysis/*.py", "discovery/canonical/*.mjs", "results/economics/*.json", "metering/*.jsonl", "metering/*.json"]


def identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--readme", type=Path, required=True)
    p.add_argument("--tex", type=Path, required=True)
    p.add_argument("--demo", type=Path, required=True)
    p.add_argument("--pdf", type=Path, required=True)
    p.add_argument("--companion", type=Path, required=True)
    p.add_argument("--base-commit", required=True)
    p.add_argument("--base-tree", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if not all(re.fullmatch(r"[0-9a-f]{40}", x) for x in (args.base_commit, args.base_tree)):
        raise ValueError("EXACT_BASE_REQUIRED")
    if args.out.exists():
        raise ValueError("OUTPUT_EXISTS")
    freeze = json.loads((ROOT / "discovery/final-freeze.json").read_text())
    for path, expected in freeze["files"].items():
        if identity((ROOT / path).read_bytes())["sha256"] != expected["sha256"]:
            raise ValueError("FROZEN_SOURCE_CHANGED: " + path)
    sources = {path: ROOT / path for path in FIXED}
    for pattern in GLOBS:
        for path in ROOT.glob(pattern):
            sources[path.relative_to(ROOT).as_posix()] = path
    native = json.loads((ROOT / "native/SOURCE.json").read_text())
    for row in native["files"]:
        sources["native/" + row["path"]] = ROOT / "native" / row["path"]
    for path in (ROOT / "licenses").rglob("*"):
        if path.is_file():
            sources[path.relative_to(ROOT).as_posix()] = path
    sources.update({"README.md": args.readme, "paper.tex": args.tex, "demo/index.html": args.demo})
    rows = []
    for relative, path in sorted(sources.items()):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError("TEXT_SOURCE_REQUIRED: " + str(path))
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        if "\0" in text:
            raise ValueError("BINARY_CONTENT: " + str(path))
        if relative == "paper.tex" and re.search(r"\\(?:input|include|includegraphics|bibliography|addbibresource)\s*(?:\[[^]]*\])?\s*\{", text):
            raise ValueError("PAPER_TEX_HAS_EXTERNAL_INPUT; verify a standalone edition before handoff")
        try:
            local = path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            local = str(path.resolve())
        rows.append({"source": local, "public_path": PREFIX + relative,
                     "mode": "100644", "type": "blob", "encoding": "utf-8", **identity(raw)})
    binary_deliverables = []
    for label, path, magic in [("paper_pdf", args.pdf, b"%PDF-"), ("complete_offline_companion", args.companion, b"PK")]:
        if path.is_symlink() or not path.is_file():
            raise ValueError("DELIVERABLE_NOT_REGULAR")
        raw = path.read_bytes()
        if not raw.startswith(magic):
            raise ValueError("DELIVERABLE_TYPE")
        binary_deliverables.append({"role": label, "filename": path.name, **identity(raw),
                                    "public_uploaded": False, "distribution": "User-provided downloadable artifact; owner-qualified public publication pending"})
    sidecar = args.out.with_name(args.out.stem + "-deliverables.json")
    if sidecar.exists():
        raise ValueError("DELIVERABLE_INDEX_EXISTS")
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps({"schema": "value-compounds-publication-artifacts/v1",
                                  "artifacts": binary_deliverables, "public_download_urls": [],
                                  "status": "Public binary publication pending existing owner qualification"}, indent=2) + "\n")
    try:
        sidecar_source = sidecar.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        sidecar_source = str(sidecar.resolve())
    rows.append({"source": sidecar_source, "public_path": PREFIX + "ARTIFACTS.json",
                 "mode": "100644", "type": "blob", "encoding": "utf-8", **identity(sidecar.read_bytes())})
    result = {"schema": "value-compounds-additive-text-draft/v1", "repository": "MontrealAI/AGI-Alpha-Agent-v0",
              "base_commit": args.base_commit, "base_tree": args.base_tree, "namespace": PREFIX,
              "publication_status": "DRAFT_SOURCE_ONLY_NOT_RELEASED_OR_LIVE", "paper_only_classification": False,
              "files": rows, "file_count": len(rows), "text_bytes": sum(x["bytes"] for x in rows),
              "binary_deliverables_excluded_from_git_draft": binary_deliverables,
              "excluded_full_companion_categories": ["wheel binaries", "fetched source snapshot bodies", "full raw run evidence", "reconstructable caches", "PDF", "ZIP"],
              "completeness_statement": "Reviewable source/evidence index; this text-only Git draft is not the complete offline package. Obtain the exact-hash companion to run offline.",
              "remote_actions_performed": 0, "main_updates_authorized_by_manifest": False,
              "frozen_experiment_commit": native["commit"], "freeze_manifest_sha256": identity((ROOT / "discovery/final-freeze.json").read_bytes())["sha256"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"files": len(rows), "text_bytes": result["text_bytes"], "path": str(args.out),
                      "sha256": identity(args.out.read_bytes())["sha256"], "remote_mutations": 0}))


if __name__ == "__main__":
    main()
