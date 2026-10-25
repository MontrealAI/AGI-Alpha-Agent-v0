#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Stage a complete, additive public source payload; dry-run planning is the default.

No network or GitHub mutation occurs. --build requires the final PDF and the
terminal confirmation marker. Frozen scientific/browser bytes are only copied.
Raw evidence is grouped by budget/treatment and kept with exact member hashes.
The complete private user-delivery archive is a different artifact selection.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
import zipfile

from extract_evidence import SCHEMA, MAX_ARCHIVE_BYTES, MAX_EXPANDED_BYTES, MAX_MEMBER_BYTES, validate_archives

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "studies/agi-alpha-flywheel-strategy-succession-v1"
FREEZE_SHA = "6d0308707f3909fd18d086a950d237835dafd9ab6cfa9a559846715f46613827"
SOURCE_SHA = "7e5a1dd2dcf7eb00ec055f1858d5dd722cc950f15f33314bb94c456c753845a7"
RUN = Path("results/confirmation-v1")
ARCHIVE_TARGET_BYTES = 4 * 1024 * 1024
GZIP_SCAN_LIMIT = 256_000_000
PRIVATE_PATTERNS = (
    re.compile(rb"https?://(?:www[.])?chatgpt[.]com/library[?][^\s\"<>]+", re.I),
    re.compile(b"oai-" + b"library://", re.I),
    re.compile(b"library-" + b"file:", re.I),
    re.compile(rb"(?:file-inline-)?libfile_[A-Za-z0-9_-]{8,}", re.I),
    re.compile(rb'"library_file_id"\s*:\s*"[^"\n]+"', re.I),
    re.compile(rb"https?://[^\s\"<>]+(?:X-Amz-Signature=|[?&]sig=)[^\s\"<>]+", re.I),
)
ROOT_FILES = ("LICENSE", "requirements.txt", "package.json", "protocol/STUDY_FREEZE.json", "REPRODUCE.md")
AUDIT_FILES = (
    "CURRENT_SOURCE_AUDIT.md", "foundation-references.bib", "WORKBENCH_MANIFEST.json",
    "INTERFACE_MANIFEST.json", "RUNTIME_SOURCE_MANIFEST.json", "FOUNDATIONS_SOURCE_MANIFEST.json",
    "PUBLIC_SOURCE_DOWNLOADS.json", "CATALOG_HASH_VERIFICATION.json",
    "CONTRACT_SOURCE_MANIFEST.json",
)
HISTORY_FILES = (
    "HISTORICAL_STRATEGY_LAB_AUDIT.md", "HISTORICAL_VERIFICATION.json", "HISTORICAL_EVIDENCE_STATUS.json",
    "audit_original.py", "historical_sources.bib", "original-manifest-verification.json",
    "current-integrity-verification.json", "current-independent-audit.log", "current-test-results-tail.txt",
)
PUBLICATION_FILES = (
    "prepare_public_payload.py", "extract_evidence.py", "test_public_payload.py", "PUBLIC_PAYLOAD_GUIDE.md",
    "ADDITIVE_HANDOFF.md", "CURRENT_OWNER_SNAPSHOT.json", "OWNER_COMMENTS.json", "PATH_INVENTORY.json",
    "POLICY_SOURCE_VERIFICATION.json", "STUDIES_NAMESPACE_CHECK.json", "HANDOFF_VALIDATION.json",
    "INTERVENTIONS_PUBLIC.json", "CUSTODY_PUBLIC.json",
    "qa_actual_recorded.mjs", "FINAL_RECORDED_QA.json",
    "PAYLOAD_TOOL_QA.json", "PUBLIC_PROJECTIONS.json",
    "SOURCE_EVIDENCE_SPLIT.md",
    "build_verification.py", "build_docket.py", "PACKAGED_LATEX_REBUILD.json", "FINAL_FOUR_READBACK.json",
)
SKIP_PARTS = {"__pycache__", "node_modules", ".venv", ".git", "readback", "frozen-readback", "qa-extracted"}
SKIP_SUFFIXES = {".pyc", ".aux", ".out", ".toc", ".bbl", ".blg", ".stdout", ".tmp", ".pending"}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def eligible(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return not any(part in SKIP_PARTS for part in relative.parts) and path.suffix not in SKIP_SUFFIXES


def ordinary(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"Only ordinary source/data files are allowed: {path.name}")


def scan_private(path: Path) -> None:
    """Refuse locator bytes; never silently rewrite a frozen or evidentiary file."""
    ordinary(path)
    open_stream = gzip.open if path.suffix == ".gz" else Path.open
    total = 0
    tail = b""
    with open_stream(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            total += len(chunk)
            if path.suffix == ".gz" and total > GZIP_SCAN_LIMIT:
                raise ValueError(f"Gzip scan bound exceeded: {path.name}")
            block = tail + chunk
            if any(pattern.search(block) for pattern in PRIVATE_PATTERNS):
                raise ValueError(f"Private provider/Library locator refused in {path}; supply an explicit public projection")
            tail = block[-4096:]


def verify_freeze(root: Path) -> dict:
    path = root / "protocol/STUDY_FREEZE.json"
    if sha_file(path) != FREEZE_SHA:
        raise ValueError("The prospective study freeze does not match this edition")
    freeze = json.loads(path.read_text())
    if len(freeze["files"]) != 52:
        raise ValueError("Unexpected frozen scientific file count")
    for name, identity in freeze["files"].items():
        source = root / name
        ordinary(source)
        if source.stat().st_size != identity["bytes"] or sha_file(source) != identity["sha256"]:
            raise ValueError(f"Frozen source changed: {name}")
    return freeze


def select_files(root: Path, freeze: dict) -> tuple[set[Path], dict[str, list[Path]]]:
    loose = {root / name for name in freeze["files"]}
    loose.update(root / name for name in ROOT_FILES if (root / name).is_file())
    for folder in ("companion", "browser", "review", "operations", "analysis", "protocol"):
        for path in (root / folder).glob("*"):
            if path.is_file() and eligible(path, root) and path.suffix not in {".log"}:
                if folder == "browser" and path.suffix == ".png":
                    continue
                if folder == "browser" and (path.name.startswith("qa-") or path.name == "BROWSER_LOGIC_LOCK_CANDIDATE.json"):
                    continue
                loose.add(path)
    for path in (root / "paper").rglob("*"):
        if not path.is_file() or not eligible(path, root):
            continue
        if path.name.startswith("layout-review") or path.name == "cover-review.png":
            continue
        if path.suffix in {".tex", ".bib", ".pdf", ".svg", ".py", ".sh", ".json", ".md"}:
            loose.add(path)
    for name in AUDIT_FILES:
        path = root / "audit" / name
        if path.is_file():
            loose.add(path)
    for name in HISTORY_FILES:
        path = root / "history" / name
        projection = root / "publication/public-projections/history" / name
        if projection.is_file():
            path = projection
        if path.is_file():
            loose.add(path)
    for path in (root / "history/current-exact-replay").glob("*"):
        if path.is_file() and eligible(path, root):
            loose.add(path)
    for name in PUBLICATION_FILES:
        path = root / "publication" / name
        if path.is_file():
            loose.add(path)
    for path in (root / "publication/retrieval").rglob("*"):
        if path.is_file():
            loose.add(path)
    for path in (root / "publication/verification").rglob("*"):
        if path.is_file() and path.suffix in {".png", ".json"}:
            if path.suffix != ".png" or path.parent == root / "publication/verification":
                loose.add(path)
    for path in (root / "publication/pdf-qa").rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md"}:
            loose.add(path)
    for name in ("EVIDENCE_DOCKET.json", "EVIDENCE_DOCKET.md", "VERIFICATION.json"):
        public = root / "publication" / (Path(name).stem + "_PUBLIC" + Path(name).suffix)
        candidate = public if public.is_file() else root / name
        if candidate.is_file():
            loose.add(candidate)
    for name in ("INTERVENTIONS_COMPLETE.json", "PUBLIC_FREEZE_COMMENT.json", "FREEZE_CUSTODY.json",
                 "FROZEN_CHECKPOINT_READBACK.json", "EXECUTED_CHECKPOINT_READBACK.json"):
        source = root / "coordination" / name
        projected = root / "publication/public-projections/coordination" / name
        candidate = projected if projected.is_file() else source
        if candidate.is_file():
            loose.add(candidate)
    for path in (root / "review/results").glob("*"):
        if path.is_file() and eligible(path, root):
            loose.add(path)
    for path in (root / "operations/load-results").glob("*.json"):
        loose.add(path)
    for name in ("development/operating-faults-final/fault-results.json",):
        if (root / name).is_file():
            loose.add(root / name)

    groups = defaultdict(list)
    for path in (root / RUN).rglob("*"):
        if not path.is_file() or not eligible(path, root):
            continue
        relative = path.relative_to(root / RUN)
        if relative.parts[0] == "main" and len(relative.parts) >= 4:
            budget = relative.parts[2].rsplit("-", 1)[-1]
            if budget not in {"250000", "1000000", "2000000"}:
                raise ValueError("Unexpected main evidence budget")
            groups[f"main-budget-{budget}"].append(path)
        elif relative.parts[0] == "diagnostic" and len(relative.parts) >= 4:
            _arm, treatment, budget = relative.parts[2].rsplit("-", 2)
            if treatment not in {"inherited", "removed", "rebuild", "equivalent"} or budget != "5000000":
                raise ValueError("Unexpected diagnostic treatment/budget")
            groups[f"diagnostic-{treatment}-{budget}"].append(path)
        elif relative.parts[0] == "inputs":
            groups["confirmation-inputs"].append(path)
        elif relative.as_posix() == "trials.jsonl":
            groups["trial-summary"].append(path)
        else:
            loose.add(path)
    for folder, label in (("development", "development"), ("browser/development-failures", "browser-failures"),
                          ("review/results", "challenge-raw"), ("operations/load-results", "finite-load")):
        for path in (root / folder).rglob("*"):
            if path.is_file() and eligible(path, root) and path not in loose:
                groups[label].append(path)
    for path in (root / "browser").glob("screenshot-*.png"):
        groups["browser-qa-images"].append(path)
    for path in (root / "publication/verification").rglob("*.png"):
        if path.parent != root / "publication/verification":
            groups["browser-qa-images"].append(path)
    return loose, dict(groups)


def stage_name(source: Path, root: Path) -> str:
    relative = source.relative_to(root).as_posix()
    public_prefix = "publication/public-projections/"
    if relative.startswith(public_prefix):
        return relative[len(public_prefix):]
    if source.parent == root / "publication" and source.name in {
        "EVIDENCE_DOCKET_PUBLIC.json", "EVIDENCE_DOCKET_PUBLIC.md", "VERIFICATION_PUBLIC.json",
    }:
        return source.name.replace("_PUBLIC", "")
    return relative


def check_terminal(root: Path) -> None:
    required = ["paper/AGI_ALPHA_FLYWHEEL_Strategy_Succession.pdf", str(RUN / "RUN_COMPLETE.json"),
                str(RUN / "SUMMARY.json"), str(RUN / "NATIVE_REFERENCE.json"), "VERIFICATION.json"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise ValueError("Final paper/terminal run required before --build: " + ", ".join(missing))
    if not (root / required[0]).read_bytes().startswith(b"%PDF-"):
        raise ValueError("Authoritative paper is not a PDF")
    start = json.loads((root / RUN / "RUN_START.json").read_text())
    complete = json.loads((root / RUN / "RUN_COMPLETE.json").read_text())
    if start.get("run_mode") != "CONFIRMATION" or start.get("source_hash") != SOURCE_SHA:
        raise ValueError("Unexpected original run identity")
    if start.get("top_freeze_sha256") != FREEZE_SHA or complete.get("source_hash") != SOURCE_SHA:
        raise ValueError("Terminal run does not bind the declared freeze/source")
    if not complete.get("completed_utc"):
        raise ValueError("Run completion timestamp is absent")
    verification = json.loads((root / "VERIFICATION.json").read_text())
    paper = verification.get("paper", {})
    if (paper.get("author_pdf_sha256") != sha_file(root / required[0])
            or not paper.get("all_final_pages_rendered_and_visually_inspected")
            or not paper.get("all_checks_pass")
            or not paper.get("packaged_source_rebuild_byte_identical")):
        raise ValueError("Final paper verification/rebuild does not bind this author PDF")


def chunks(paths: list[Path]) -> list[list[Path]]:
    result = []
    batch = []
    size = 0
    for path in sorted(paths):
        count = path.stat().st_size
        if count > ARCHIVE_TARGET_BYTES:
            raise ValueError(f"Raw evidence member exceeds the 4 MiB input shard bound: {path.name}")
        if batch and size + count > ARCHIVE_TARGET_BYTES:
            result.append(batch)
            batch, size = [], 0
        batch.append(path)
        size += count
    if batch:
        result.append(batch)
    return result


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 24, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_STORED if name.endswith(".gz") else zipfile.ZIP_DEFLATED
    return info


def write_archive(path: Path, sources: list[Path], root: Path, identities: dict[str, dict]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    members = []
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for source in sorted(sources):
            name = source.relative_to(root).as_posix()
            data = source.read_bytes()
            expected = identities[name]
            if len(data) != expected["bytes"] or sha_bytes(data) != expected["sha256"]:
                raise ValueError(f"Evidence changed after preflight: {name}")
            zipped.writestr(zip_info(name), data)
            members.append({"path": name, **expected})
        manifest = "".join(f"{row['sha256']}  {row['path']}\n" for row in sorted(members, key=lambda row: row["path"]))
        zipped.writestr(zip_info("SHA256SUMS.txt"), manifest.encode())
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds the safe extractor's compressed-size bound")
    return {"path": "evidence/archives/" + path.name, "sha256": sha_file(path), "bytes": path.stat().st_size,
            "member_count": len(members), "payload_bytes": sum(row["bytes"] for row in members),
            "manifest_sha256": sha_bytes(manifest.encode()), "members": members}


PUBLIC_README = """# AGI ALPHA FLYWHEEL — Strategy as a Productive Asset

Open `browser/index.html` and select **Plan this mission**. The complete offline browser computes and checks a
fresh release schedule without an account, installation, server, wallet or API key. The bounded six-mission mode
runs actual discovery and selective admission. Correctness-only construction diagnostics are explicitly separate.

This additive source tree contains the editable implementation, complete prospective protocol/checkers, author
PDF/LaTeX/vector figures, original result summaries, public audit records and compressed raw evidence. It uses
the unchanged released AGI ALPHA v1.42.0 `createWorkbench` closure. It is not an installed-runtime or hosted-service
qualification and changes none of the original Harness/Fleet restrictions or earlier paper editions.

Read `paper/AGI_ALPHA_FLYWHEEL_Strategy_Succession.pdf` for the actual findings and limitations. Read
`results/confirmation-v1/SUMMARY.json` and the evidence docket for the recorded study. Recorded results are
separate from the live browser computation. Browser/interpreted work units, native CPU/wall time and unknown
human/monetary costs are reported separately. No commercial growth or self-acceleration is presumed.

## Reproduce and inspect

```sh
python3 scripts/freeze_study.py
python3 publication/extract_evidence.py --check-only
python3 publication/extract_evidence.py
```

The extractor validates archives, member hashes, bounded paths and existing targets before writing. It refuses
different existing bytes, traversal, symlinks and unexpected files; identical evidence is retained. It writes only
the declared raw-data prefixes and executes no archived code. Keep the destination free from concurrent edits.
Extraction restores exact original paths needed for raw analysis and development-exposure scans. See
`REPRODUCE.md` for the pinned environment, fresh run, paper build and separate historical replay instructions.

All 52 frozen scientific/browser files plus the freeze record are present byte-identically. Provider transfer
helpers, private Library locators, original user DOCX/ZIP files, local environments and extracted predecessor
duplicates are excluded from this public source tree. Historical identity/audit records identify the separate
original archive needed for historical replay. The complete private user-delivery archive is a different package.

`PUBLIC_PAYLOAD_MANIFEST.json` identifies every payload file except itself; `SHA256SUMS.txt` verifies the payload
except itself and that final manifest. Each raw archive also has a complete member manifest. Public custody
summaries, where included, are explicit projections of separately retained full
receipts. A source PR, local hash or stored history is not publication approval, production authority or an agent
that continues operating after its browser/process closes.
"""


def build(root: Path, output: Path, loose: set[Path], groups: dict[str, list[Path]],
          evidence_output: Path | None = None) -> dict:
    check_terminal(root)
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a nonexistent isolated output directory; existing payloads are never overwritten")
    if evidence_output is not None:
        if evidence_output.exists() or evidence_output.is_symlink():
            raise ValueError("Separate evidence output must also be a nonexistent directory")
        if output == evidence_output or output in evidence_output.parents or evidence_output in output.parents:
            raise ValueError("Source and evidence outputs must be disjoint directories")
    all_sources = loose | {path for paths in groups.values() for path in paths}
    identities = {}
    for source in sorted(all_sources):
        scan_private(source)
        relative = source.relative_to(root).as_posix()
        identities[relative] = {"sha256": sha_file(source), "bytes": source.stat().st_size}
    raw_size = sum(identities[path.relative_to(root).as_posix()]["bytes"] for paths in groups.values() for path in paths)
    if raw_size > MAX_EXPANDED_BYTES:
        raise ValueError("Raw evidence exceeds the extractor's aggregate bound; prepare an explicit bounded revision")

    output.mkdir(parents=True, exist_ok=False)
    stage = output / NAMESPACE
    stage.mkdir(parents=True)
    archive_store = stage
    if evidence_output is not None:
        evidence_output.mkdir(parents=True, exist_ok=False)
        archive_store = evidence_output
    projections = []
    try:
        for source in sorted(loose):
            relative = stage_name(source, root)
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            original = identities[source.relative_to(root).as_posix()]
            if sha_bytes(data) != original["sha256"] or len(data) != original["bytes"]:
                raise ValueError("Source changed after public-payload preflight")
            if relative == "REPRODUCE.md":
                note = ("# Public source-tree packaging note\n\nBefore raw-data analysis or a fresh confirmatory rerun, run "
                        "`python3 publication/extract_evidence.py`. The exact original raw paths are archived by "
                        "budget/treatment. The historical original ZIP and user DOCX are not included in this "
                        "public tree; section 8 requires the separately identified original archive. The complete "
                        "private user-delivery archive has a different inventory. The research instructions below "
                        "retain their original scope.\n\n---\n\n")
                if evidence_output is not None:
                    note = ("# Public source-tree packaging note\n\nThis draft source tree contains the runnable "
                            "implementation, author paper, summaries and exact archive index. The raw ZIP shards "
                            "are delivered separately; a public release is not claimed. The complete user package "
                            "retains original raw paths. To restore this source tree from the separate evidence "
                            "handoff, run `python3 publication/extract_evidence.py --archive-root PATH_TO_EVIDENCE`. "
                            "That directory must contain `evidence/archives/` matching the included index. Do this "
                            "before original-raw analysis or a fresh run intended to repeat the full development "
                            "exposure scan. The first browser mission and source verification work without these "
                            "archives. The historical original ZIP and user DOCX are excluded from this public "
                            "tree; section 8 needs the separately identified historical archive. The research "
                            "instructions below retain their original scope.\n\n---\n\n")
                data = note.encode() + data
                projections.append({"target": relative, "source": source.relative_to(root).as_posix(),
                                    "source_sha256": original["sha256"], "change": "Explicit public-packaging preface only"})
            elif source.name in {"EVIDENCE_DOCKET_PUBLIC.json", "EVIDENCE_DOCKET_PUBLIC.md", "VERIFICATION_PUBLIC.json"}:
                projections.append({"target": relative, "source": source.relative_to(root).as_posix(),
                                    "source_sha256": original["sha256"],
                                    "change": "Explicit pre-authored public projection, copied without modification"})
            elif source.relative_to(root).as_posix().startswith("publication/public-projections/"):
                projections.append({"target": relative, "source": source.relative_to(root).as_posix(),
                                    "source_sha256": original["sha256"],
                                    "change": "Explicit public projection; original identity and exact omissions in publication/PUBLIC_PROJECTIONS.json"})
            with target.open("xb") as stream:
                stream.write(data)
            target.chmod(0o755 if target.suffix == ".sh" else 0o644)
        readme = PUBLIC_README
        if evidence_output is not None:
            readme = readme.replace("public audit records and compressed raw evidence", "public audit records and an exact index of separately handed-off raw evidence")
            readme = readme.replace("## Reproduce and inspect\n", "## Reproduce and inspect\n\nRaw ZIP shards are **not included in this source PR**. The complete user-delivery package retains their original "
                                    "data. A separate public research-release handoff is prepared for the existing coordinator; "
                                    "no public download is claimed here. After obtaining and extracting that exact evidence "
                                    "package, replace `PATH_TO_EVIDENCE` below with its root. The browser and source check work "
                                    "without raw archives; raw auditing and the complete development-exposure replay require them.\n")
            readme = readme.replace("python3 publication/extract_evidence.py --check-only", "python3 publication/extract_evidence.py --archive-root PATH_TO_EVIDENCE --check-only")
            readme = readme.replace("python3 publication/extract_evidence.py\n", "python3 publication/extract_evidence.py --archive-root PATH_TO_EVIDENCE\n")
        (stage / "README.md").write_text(readme, encoding="utf-8")
        archives = []
        for group, paths in sorted(groups.items()):
            for index, batch in enumerate(chunks(paths), 1):
                name = f"{group}-{index:02d}.zip"
                archives.append(write_archive(archive_store / "evidence/archives" / name, batch, root, identities))
        index = {"schema": SCHEMA, "source_hash": SOURCE_SHA, "freeze_sha256": FREEZE_SHA,
                 "archive_timestamp": "Fixed 2026-10-24 solely for deterministic container metadata",
                 "archives": archives}
        index_data = json.dumps(index, indent=2) + "\n"
        (stage / "evidence").mkdir(parents=True, exist_ok=True)
        (stage / "evidence/ARCHIVE_INDEX.json").write_text(index_data)
        availability = {"schema": "strategy-succession-raw-availability/v1",
                        "status": "SEPARATE_HANDOFF_NOT_PUBLICLY_RELEASED" if evidence_output is not None else "ARCHIVES_INCLUDED",
                        "archives_in_this_source_tree": evidence_output is None,
                        "archive_index_sha256": sha_bytes(index_data.encode()), "archives": len(archives),
                        "raw_input_bytes": raw_size, "public_download_url": None,
                        "scope": "Exact manifest is not evidence of a public asset; the existing owner must verify any later download."}
        (stage / "evidence/AVAILABILITY.json").write_text(json.dumps(availability, indent=2) + "\n")
        if evidence_output is not None:
            (archive_store / "evidence/ARCHIVE_INDEX.json").write_text(index_data)
            (archive_store / "README.md").write_text(
                "# AGI ALPHA Strategy Succession: raw evidence handoff\n\n"
                "Prepared for the existing research-release coordinator. This directory is not a published release. "
                "The source PR carries the identical archive index and the safe extraction helper. From that study "
                "root, run `python3 publication/extract_evidence.py --archive-root PATH_TO_THIS_DIRECTORY --check-only`, "
                "then omit `--check-only` to restore exact raw paths. No code is executed during extraction. "
                "The original full user package independently retains these raw data. The public handoff excludes "
                "private transport locators and original user uploads.\n")
            handoff_files = [{"path": path.relative_to(archive_store).as_posix(), "sha256": sha_file(path),
                              "bytes": path.stat().st_size} for path in sorted(archive_store.rglob("*")) if path.is_file()]
            (archive_store / "RAW_HANDOFF_MANIFEST.json").write_text(json.dumps({
                "schema": "strategy-succession-public-raw-handoff/v1", "status": "PREPARED_NOT_RELEASED",
                "source_hash": SOURCE_SHA, "freeze_sha256": FREEZE_SHA,
                "archive_index_sha256": availability["archive_index_sha256"], "files": handoff_files,
                "scope": "All handoff files except this manifest. No public URL, publication approval or live service inferred."
            }, indent=2) + "\n")
        validate_archives(stage, index, archive_root=archive_store)
        checksum_rows = []
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                checksum_rows.append(f"{sha_file(path)}  {path.relative_to(stage).as_posix()}\n")
        (stage / "SHA256SUMS.txt").write_text("".join(checksum_rows))
        records = []
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                relative = path.relative_to(stage).as_posix()
                records.append({"path": relative, "repo_path": NAMESPACE + "/" + relative,
                                "sha256": sha_file(path), "bytes": path.stat().st_size,
                                "mode": "100755" if path.suffix == ".sh" else "100644"})
        manifest = {"schema": "agi-alpha-strategy-public-source-payload/v1", "status": "STAGED_AND_VERIFIED_NOT_PUBLISHED",
                    "namespace": NAMESPACE, "source_hash": SOURCE_SHA, "freeze_sha256": FREEZE_SHA,
                    "frozen_file_count": 52, "archives_verified": len(archives), "raw_payload_bytes": raw_size,
                    "raw_availability": availability,
                    "projections": projections, "files": records,
                    "manifest_scope": "All staged payload files except this manifest itself. No external write or deployment.",
                    "excluded": ["private provider/Library metadata", "original user DOCX/ZIP", "transfer helpers",
                                 "local environments/caches", "extracted predecessor duplicates"]}
        (stage / "PUBLIC_PAYLOAD_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return {"status": manifest["status"], "output": str(output), "namespace": NAMESPACE,
                "payload_files_including_manifest": len(records) + 1, "archives": len(archives),
                "separate_evidence_output": str(evidence_output) if evidence_output is not None else None,
                "manifest_sha256": sha_file(stage / "PUBLIC_PAYLOAD_MANIFEST.json")}
    except Exception as error:
        (output / "BUILD_FAILED.json").write_text(json.dumps({"status": "FAILED_NOT_ELIGIBLE_FOR_UPLOAD", "error": str(error)}) + "\n")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build", action="store_true", help="Actually stage/compress after final PDF and terminal run")
    parser.add_argument("--evidence-output", type=Path,
                        help="Optional disjoint output for raw ZIP shards; source PR retains exact index and availability disclosure")
    parser.add_argument("--plan-output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    freeze = verify_freeze(root)
    loose, groups = select_files(root, freeze)
    grouped = {}
    for name, paths in sorted(groups.items()):
        batches = chunks(paths)
        grouped[name] = {"files": len(paths), "bytes": sum(path.stat().st_size for path in paths),
                         "shards": len(batches),
                         "largest_input_shard_bytes": max((sum(path.stat().st_size for path in batch)
                                                          for batch in batches), default=0)}
    plan = {"schema": "agi-alpha-strategy-public-payload-plan/v1", "mode": "BUILD" if args.build else "DRY_RUN",
            "namespace": NAMESPACE, "loose_files": [stage_name(path, root) for path in sorted(loose)],
            "loose_input_bytes": sum(path.stat().st_size for path in loose),
            "raw_groups": grouped,
            "raw_input_bytes": sum(row["bytes"] for row in grouped.values()),
            "raw_files": sum(row["files"] for row in grouped.values()),
            "planned_archive_count": sum(row["shards"] for row in grouped.values()),
            "input_shard_limit_bytes": ARCHIVE_TARGET_BYTES,
            "compressed_size": "Unknown until actual build; existing .gz members are stored without recompression",
            "raw_destination": "SEPARATE_OWNER_HANDOFF" if args.evidence_output else "INCLUDED_IN_SOURCE_PAYLOAD",
            "no_compression_in_dry_run": True, "frozen_files_verified": 52}
    if args.plan_output:
        args.plan_output.write_text(json.dumps(plan, indent=2) + "\n")
    if args.build:
        result = build(root, args.output.resolve(), loose, groups,
                       evidence_output=args.evidence_output.resolve() if args.evidence_output else None)
    else:
        result = {"mode": "DRY_RUN", "loose_files": len(loose), "loose_input_bytes": plan["loose_input_bytes"],
                  "raw_groups": plan["raw_groups"], "raw_files": plan["raw_files"],
                  "raw_input_bytes": plan["raw_input_bytes"], "planned_archives": plan["planned_archive_count"],
                  "frozen_files_verified": 52, "output_not_created": True}
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
