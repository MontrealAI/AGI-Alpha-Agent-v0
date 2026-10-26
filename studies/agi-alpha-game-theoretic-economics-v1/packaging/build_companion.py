# SPDX-License-Identifier: Apache-2.0
"""Package recorded research without rerunning or rewriting any experiment.

The production selection is immutable. Other study files are selected at build
time so the final paper, figures and later review receipts can be added first.
Only the Python standard library is required. No network operation is performed.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import shutil
import stat
import sys
import time
import uuid
import zipfile


STUDY = Path(__file__).resolve().parents[1]
SEALED_PATH = "production/FINAL_PRODUCTION_MANIFEST.json"
SEALED_SHA256 = "031ac7a8098fc57267c552dda68963680291b3635a9132a4c9030025d04beb39"
SEALED_COUNT = 1498
ARCHIVE_MANIFEST = "COMPANION_MANIFEST.json"
DEFAULT_ROOT = "AGI_ALPHA_Game_Theoretic_Companion"
CHUNK = 1024 * 1024

REQUIRED_RECORDED = (
    "production/joint-freeze.json",
    "production/joint-summary.json",
    "production/joint-results-audit.json",
    "production/README.md",
    "production/instantiate_replay.py",
    "market/src/market.mjs",
    "market/tests/test_market.mjs",
    "market/protocol/freeze.json",
    "market/protocol/parameter-manifest.json",
    "market/results/primary-01/complete-runs.jsonl.gz",
    "market/results/primary-01/completion.json",
    "market/exploratory/results-01/complete-runs.jsonl.gz",
    "market/exploratory/results-01/completion.json",
    "market/policy-diagnostic/results-01/complete-runs.jsonl.gz",
    "market/policy-diagnostic/results-01/completion.json",
    "calibration/source-manifest.json",
    "protocol/claim-criteria.json",
    "review/frozen-outcome-audit.json",
    "review/exploratory-outcome-audit.json",
    "review/policy-diagnostic-outcome-audit.json",
    "market/reporting/results-01/completion.json",
    "review/competitor-account-outcome-audit.json",
    "market/deployment-robustness/results-01/completion.json",
    "market/deployment-robustness/results-01/complete-runs.jsonl.gz",
    "market/deployment-robustness/results-01/summary.json",
    "market/deployment-robustness/freeze.json",
    "review/deployment-robustness-outcome-audit.json",
    "review/second-capability-gate.json",
    "review/SECOND_CAPABILITY_GATE.md",
    "review/production-relocation/receipt.json",
    "review/demo-qa/result.json",
    "deliverables/AGI_ALPHA_Game_Theoretic_Laboratory.html",
    "vendor/product/LICENSE",
    "vendor/product/contrib/upgrade_decision/NOTICES.md",
    "vendor/useful-work-v2/canonical/LICENSE.Alpha",
)

SKIP_PARTS = {
    "venv", ".venv", "__pycache__", "node_modules", ".git", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", "tmp", "temp", "extraction-check",
    "extracted", "extraction", "verification-extract", "library-upload",
}
TEXT_SUFFIXES = {
    ".py", ".mjs", ".js", ".cjs", ".html", ".md", ".json", ".jsonl",
    ".txt", ".tex", ".bib", ".csv", ".log", ".toml", ".yaml", ".yml",
}
SECRET_MARKERS = (
    ("GitHub credential", re.compile(rb"(?:github_pat_[A-Za-z0-9_]{40,}|gh[pousr]_[A-Za-z0-9]{30,})")),
    ("private key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("signed download credential", re.compile(rb"(?i)(?:x-amz-signature=|x-goog-signature=|[?&]sig=)[A-Za-z0-9%+/]{30,}")),
)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            h.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": h.hexdigest()}


def relative_path(value):
    """Accept one ordinary portable relative path, never traversal or aliases."""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("Invalid portable path")
    parts = value.split("/")
    if any(p in ("", ".", "..") or ":" in p for p in parts):
        raise ValueError(f"Nonportable path: {value}")
    p = PurePosixPath(value)
    if p.is_absolute():
        raise ValueError(f"Absolute payload path: {value}")
    return value


def ordinary_file(relative):
    relative_path(relative)
    p = STUDY / relative
    for q in (p, *p.parents):
        if q == STUDY.parent:
            break
        if q.is_symlink():
            raise ValueError(f"Symlink is not a payload: {relative}")
    if not p.is_file() or not stat.S_ISREG(p.stat().st_mode):
        raise FileNotFoundError(f"Missing regular input: {relative}")
    return p


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def write_new_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def outside_study(value, label):
    p = Path(value).expanduser().absolute()
    resolved = p.resolve()
    if resolved == STUDY or STUDY in resolved.parents:
        raise ValueError(f"{label} must be outside the selected study tree")
    if p.exists() or p.is_symlink():
        raise FileExistsError(f"{label} must be new: {p}")
    return p


def excluded(relative, directory=False):
    parts = PurePosixPath(relative).parts
    if any(p in SKIP_PARTS for p in parts):
        return "Disposable environment, cache, temporary or extraction duplicate"
    if any(p.startswith(".") for p in parts):
        return "Hidden workspace/configuration file"
    name = parts[-1].lower()
    if name.endswith((".pyc", ".pyo", ".partial", ".aux", ".toc", ".out", ".fls", ".fdb_latexmk", ".synctex.gz")):
        return "Regenerable cache or intermediate"
    if name in {"credentials", "credentials.json", "secrets.json", ".env"}:
        return "Credentials are not research payloads"
    if any(s in name for s in ("upload-helper", "upload_helper", "library-helper", "library_helper", "transfer-helper", "transfer_helper")):
        return "Environment-specific storage transfer helper"
    if relative.startswith("review/demo-qa/"):
        if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return "Browser screenshot; semantic QA records retained"
        if name.endswith(".zip"):
            return "Downloaded duplicate of sealed production packet"
    if not directory and name.endswith((".zip", ".tar", ".tar.gz", ".tgz", ".7z")):
        return "Unsealed archive or previous companion; sealed production ZIPs retained"
    return None


def check_credentials(path, relative):
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return
    # Scan only high-confidence credential shapes. Scientific provenance and
    # public commit URLs are retained, including original absolute path receipts.
    tail = b""
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            body = tail + chunk
            for label, pattern in SECRET_MARKERS:
                if pattern.search(body):
                    raise ValueError(f"Potential {label} in {relative}; no secret is printed")
            tail = body[-512:]


def collect_inputs():
    sealed_file = ordinary_file(SEALED_PATH)
    if digest(sealed_file)["sha256"] != SEALED_SHA256:
        raise ValueError("Sealed production manifest identity changed")
    sealed = json.loads(sealed_file.read_text())
    entries = sealed["files"]
    if len(entries) != SEALED_COUNT:
        raise ValueError("Sealed production file count changed")
    selected = {}
    for row in entries:
        relative = relative_path(row["path"])
        if relative in selected:
            raise ValueError(f"Duplicate sealed input: {relative}")
        actual = digest(ordinary_file(relative))
        if actual != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            raise ValueError(f"Sealed production input changed: {relative}")
        selected[relative] = {"path": relative, **actual, "sealed_production": True}
    selected[SEALED_PATH] = {"path": SEALED_PATH, **digest(sealed_file), "sealed_production": True}
    omissions = [
        {"path": "production/", "reason": "Exactly the sealed manifest selection; original artifacts are not modified"},
        {"path": "vendor/", "reason": "Exactly the sealed manifest selection; disposable virtual environments are excluded"},
    ]
    for base, dirs, files in os.walk(STUDY, followlinks=False):
        base_path = Path(base)
        keep = []
        for name in sorted(dirs):
            q = base_path / name
            relative = q.relative_to(STUDY).as_posix()
            if base_path == STUDY and name in ("production", "vendor"):
                continue
            reason = excluded(relative, directory=True)
            if reason:
                omissions.append({"path": relative + "/", "reason": reason})
            elif q.is_symlink():
                raise ValueError(f"Symlink directory is not portable: {relative}")
            else:
                keep.append(name)
        dirs[:] = keep
        for name in sorted(files):
            q = base_path / name
            relative = q.relative_to(STUDY).as_posix()
            reason = excluded(relative)
            if reason:
                omissions.append({"path": relative, "reason": reason})
                continue
            if relative == ARCHIVE_MANIFEST:
                raise ValueError("A previous generated companion manifest is present in source root")
            ordinary_file(relative)
            selected[relative] = {"path": relative, **digest(q), "sealed_production": False}
    for relative in selected:
        check_credentials(STUDY / relative, relative)
    return [selected[p] for p in sorted(selected)], omissions


def check_requirements(files, paper=None, latex=None, final=False):
    paths = {row["path"] for row in files}
    identities = {row["path"]: row for row in files}
    required = list(REQUIRED_RECORDED)
    if final:
        required.append("README.md")
        required.extend((relative_path(paper), relative_path(latex)))
        if not paper.lower().endswith(".pdf") or not latex.lower().endswith(".tex"):
            raise ValueError("Final paper must be .pdf and LaTeX source must be .tex")
        if not any(p in paths for p in ("LICENSE", "LICENSE.txt", "LICENSE.md")):
            raise ValueError("Final study root must include its LICENSE; upstream notices are separately preserved")
        required.extend(tex_dependencies(latex, paths))
    missing = [p for p in required if p not in paths]
    if missing and final:
        raise FileNotFoundError("Required final inputs missing: " + ", ".join(missing))
    wheels = [p for p in paths if p.startswith("vendor/useful-work-v2/joint-study/inputs/wheels/") and p.endswith(".whl")]
    if len(wheels) != 16:
        raise ValueError("The sixteen-wheel offline production input closure is incomplete")
    audits = {
        "market/results/primary-01": ("review/frozen-outcome-audit.json", "market/protocol/freeze.json"),
        "market/exploratory/results-01": ("review/exploratory-outcome-audit.json", "market/exploratory/freeze.json"),
        "market/policy-diagnostic/results-01": ("review/policy-diagnostic-outcome-audit.json", "market/policy-diagnostic/freeze.json"),
    }
    for directory, (audit_path, freeze_path) in audits.items():
        if freeze_path in paths:
            verify_bound_manifest(freeze_path, "market", identities)
        marker = directory + "/completion.json"
        if marker not in paths:
            continue
        completed = json.loads((STUDY / marker).read_text())
        if completed.get("completed") is not True:
            raise ValueError(f"Campaign is not completed: {directory}")
        for name, key in (("complete-runs.jsonl.gz", "completeRunsSHA256"), ("summary.json", "summarySHA256")):
            if directory + "/" + name not in identities or key not in completed or identities[directory + "/" + name]["sha256"] != completed[key]:
                raise ValueError(f"Recorded campaign digest differs: {directory}/{name}")
        if audit_path in paths:
            audit = json.loads((STUDY / audit_path).read_text())
            passing_audit(audit, audit_path)
            for key in ("completeRunsSHA256", "summarySHA256"):
                if audit.get(key) != completed.get(key):
                    raise ValueError(f"Review does not match completed campaign: {audit_path}")
            if audit.get("freezeSHA256") != identities.get(freeze_path, {}).get("sha256"):
                raise ValueError(f"Review freeze differs: {audit_path}")
            if audit.get("marketSourceSHA256") != identities["market/src/market.mjs"]["sha256"]:
                raise ValueError(f"Reviewed market source differs: {audit_path}")
    reporting_path = "market/reporting/results-01/completion.json"
    if reporting_path in paths:
        verify_bound_manifest("market/reporting/source-manifest.json", "market", identities)
        reporting = json.loads((STUDY / reporting_path).read_text())
        for key, value in {"complete": True, "pairedExactMatches": 6480,
                           "armExactMatches": 19440, "competitorFirmAccounts": 38880,
                           "newEconomicScenarios": 0,
                           "originalFrozenSourcesAndArchivesUnchanged": True}.items():
            if reporting.get(key) != value:
                raise ValueError(f"Reporting completion is invalid: {key}")
        if reporting.get("sourceManifestSHA256") != identities.get("market/reporting/source-manifest.json", {}).get("sha256"):
            raise ValueError("Reporting source-manifest digest differs")
        if len(reporting.get("stages", [])) != 3:
            raise ValueError("Reporting supplement must contain three completed stages")
        for stage in reporting["stages"]:
            supplement = "market/reporting/results-01/" + relative_path(stage["supplement"])
            selected = identities.get(supplement, {})
            if selected.get("sha256") != stage["supplementSHA256"] or selected.get("bytes") != stage["supplementBytes"]:
                raise ValueError(f"Reporting supplement digest/size differs: {supplement}")
        audit_path = "review/competitor-account-outcome-audit.json"
        if audit_path in paths:
            audit = json.loads((STUDY / audit_path).read_text())
            passing_audit(audit, audit_path)
            if audit.get("completionSHA256") != identities[reporting_path]["sha256"]:
                raise ValueError("Reporting audit does not bind the final completion marker")
    extension_path = "market/deployment-robustness/results-01/completion.json"
    if extension_path in paths:
        verify_bound_manifest("market/deployment-robustness/freeze.json", "market", identities)
        extension = json.loads((STUDY / extension_path).read_text())
        expected = {"completed": True, "configurations": 128, "seeds": 24,
                    "pairedWorlds": 3072, "enterpriseRuns": 9216,
                    "competitorFirmAccounts": 18432, "mode": "ORIGINAL_BOUNDED_RESEARCH",
                    "newEconomicScenarios": 128,
                    "actualSecondInvestments": 0, "unpricedIncrementalDiscoveryCostCents": None,
                    "observedCollectionsCents": 0, "actualTransactions": 0,
                    "budgetsSatisfied": True, "cutoffSatisfied": True}
        for key, value in expected.items():
            if key not in extension or extension[key] != value:
                raise ValueError(f"Bounded extension completion is invalid: {key}")
        directory = "market/deployment-robustness/results-01/"
        freeze_digest = identities.get("market/deployment-robustness/freeze.json", {}).get("sha256")
        if not freeze_digest or extension.get("freezeSHA256") != freeze_digest:
            raise ValueError("Bounded extension does not bind its selected frozen design")
        for name, key in (("complete-runs.jsonl.gz", "completeRunsSHA256"), ("summary.json", "summarySHA256")):
            if directory + name not in identities or key not in extension or identities[directory + name]["sha256"] != extension[key]:
                raise ValueError(f"Bounded extension digest differs: {directory}{name}")
        audit_path = "review/deployment-robustness-outcome-audit.json"
        if audit_path in paths:
            audit = json.loads((STUDY / audit_path).read_text())
            passing_audit(audit, audit_path)
            if audit.get("completionSHA256") != identities[extension_path]["sha256"]:
                raise ValueError("Bounded extension audit does not bind its final completion marker")
            if audit.get("freezeSHA256") != freeze_digest:
                raise ValueError("Bounded extension audit does not bind its frozen design")
            for key in ("completeRunsSHA256", "summarySHA256"):
                if audit.get(key) != extension[key]:
                    raise ValueError(f"Bounded extension audit digest differs: {key}")
    return missing


def passing_audit(audit, path):
    if audit.get("passed") is not True or audit.get("failedAssertions") != 0 or audit.get("firstFailures") != []:
        raise ValueError(f"Required final review is not passing without failures: {path}")


def verify_bound_manifest(manifest_path, base, identities):
    """Bind each frozen source/input, including declared ../review references."""
    manifest = json.loads((STUDY / manifest_path).read_text())
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Missing bound input inventory: {manifest_path}")
    seen = set()
    for row in rows:
        target = (STUDY / base / row["path"]).resolve()
        if STUDY not in target.parents:
            raise ValueError(f"Bound input escapes study root: {manifest_path}")
        relative = target.relative_to(STUDY).as_posix()
        if relative in seen:
            raise ValueError(f"Duplicate bound input: {manifest_path}: {relative}")
        seen.add(relative)
        current = identities.get(relative)
        if current is None or current["sha256"] != row["sha256"]:
            raise ValueError(f"Missing or changed bound input: {manifest_path}: {relative}")
        if "bytes" in row and row["bytes"] != current["bytes"]:
            raise ValueError(f"Bound input size differs: {manifest_path}: {relative}")


def tex_dependencies(latex, selected):
    """Check this paper's literal local inputs/figures, recursively, before ZIP."""
    checked, assets = set(), set()
    pending = [ordinary_file(relative_path(latex))]
    expression = re.compile(r"\\(input|include|includegraphics|bibliography|addbibresource)\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
    while pending:
        source = pending.pop()
        if source in checked:
            continue
        checked.add(source)
        text = re.sub(r"(?<!\\)%[^\n]*", "", source.read_text())
        for command, value in expression.findall(text):
            if any(c in value for c in ("\\", "#", "$")):
                raise ValueError(f"Dynamic TeX asset requires explicit review in {source.name}")
            values = value.split(",") if command == "bibliography" else [value]
            for name in values:
                raw = source.parent / name.strip()
                choices = [raw]
                if not raw.suffix:
                    extensions = (".tex",) if command in ("input", "include") else ((".bib",) if command in ("bibliography", "addbibresource") else (".pdf", ".png", ".jpg", ".jpeg", ".eps"))
                    choices = [raw.with_suffix(suffix) for suffix in extensions]
                candidates = [p.resolve() for p in choices if p.is_file()]
                if not candidates:
                    raise FileNotFoundError(f"Missing paper asset {name!r} referenced by {source.name}")
                chosen = candidates[0]
                if STUDY not in chosen.parents:
                    raise ValueError(f"Paper asset escapes study root: {name}")
                relative = chosen.relative_to(STUDY).as_posix()
                ordinary_file(relative)
                if relative not in selected:
                    raise ValueError(f"Paper asset excluded from companion: {relative}")
                assets.add(relative)
                if command in ("input", "include"):
                    pending.append(chosen)
    return sorted(assets)


@contextmanager
def phase(receipt, name):
    start_wall = time.monotonic()
    start_cpu = time.process_time()
    row = {"name": name, "started_at": utcnow()}
    receipt["phases"].append(row)
    try:
        yield
    finally:
        row.update({"wall_seconds": time.monotonic() - start_wall,
                    "process_cpu_seconds": time.process_time() - start_cpu})


def new_receipt(kind):
    return {"schema": "agialpha-companion-custody/v1", "operation": kind,
            "started_at": utcnow(), "command": sys.argv,
            "status": "running", "phases": [], "new_primary_missions": 0,
            "new_customer_jobs": 0, "network_requests": 0,
            "runtime_model_calls": 0, "money_usd": None,
            "authoring_inference_cost_usd": None, "active_human_minutes": None,
            "resource_scope": "Local packaging/verification process only; phases partition wall and process CPU; no inference, labor or all-in monetary claim"}


def finish_receipt(receipt, start_wall, start_cpu):
    receipt.update({"finished_at": utcnow(),
                    "wall_seconds": time.monotonic() - start_wall,
                    "process_cpu_seconds": time.process_time() - start_cpu,
                    "peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})


def verify_archive(archive, extraction, receipt):
    if extraction.exists() or extraction.is_symlink():
        raise FileExistsError("Full extraction must use a new directory")
    with zipfile.ZipFile(archive, "r") as zf:
        infos = zf.infolist()  # Requires a complete, readable central directory.
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP member")
        roots = {relative_path(name).split("/")[0] for name in names}
        if len(roots) != 1:
            raise ValueError("ZIP must have exactly one portable root directory")
        root = next(iter(roots))
        manifest_name = root + "/" + ARCHIVE_MANIFEST
        manifest_bytes = zf.read(manifest_name)
        manifest = json.loads(manifest_bytes)
        if manifest.get("archive_root") != root:
            raise ValueError("Archive root does not match manifest")
        rows = manifest["files"]
        paths = [relative_path(row["path"]) for row in rows]
        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate manifest payload")
        expected_names = {root + "/" + p for p in paths} | {manifest_name}
        if set(names) != expected_names:
            raise ValueError("ZIP central directory differs from manifest")
        for info in infos:
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_ISLNK(mode):
                raise ValueError("Only ordinary files are permitted in this archive")
            if mode and not stat.S_ISREG(mode):
                raise ValueError("ZIP contains a non-regular member")
        for row in rows:
            if not isinstance(row["bytes"], int) or row["bytes"] < 0:
                raise ValueError("Invalid payload size")
            if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
                raise ValueError("Invalid payload SHA-256")
            if zf.getinfo(root + "/" + row["path"]).file_size != row["bytes"]:
                raise ValueError("Central-directory payload size mismatch")
        with phase(receipt, "zip_crc_test"):
            bad = zf.testzip()
            if bad is not None:
                raise ValueError(f"ZIP CRC failure: {bad}")
        with phase(receipt, "actual_full_extraction"):
            extraction.mkdir(parents=True, exist_ok=False)
            for info in infos:
                destination = extraction.joinpath(*PurePosixPath(info.filename).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as source, destination.open("xb") as target:
                    shutil.copyfileobj(source, target, CHUNK)
                os.chmod(destination, (info.external_attr >> 16) & 0o777)
        with phase(receipt, "every_extracted_payload_sha256"):
            extracted_root = extraction / root
            for row in rows:
                actual = digest(extracted_root / row["path"])
                if actual != {"bytes": row["bytes"], "sha256": row["sha256"]}:
                    raise ValueError(f"Extracted payload hash mismatch: {row['path']}")
            if (extracted_root / ARCHIVE_MANIFEST).read_bytes() != manifest_bytes:
                raise ValueError("Extracted manifest bytes changed")
        with phase(receipt, "sealed_production_closure_in_extracted_archive"):
            sealed_path = extracted_root / SEALED_PATH
            if digest(sealed_path)["sha256"] != SEALED_SHA256:
                raise ValueError("Extracted production manifest does not match the sealed original")
            sealed = json.loads(sealed_path.read_text())
            if len(sealed["files"]) != SEALED_COUNT:
                raise ValueError("Extracted production closure count differs")
            by_path = {row["path"]: row for row in rows}
            for original in sealed["files"]:
                current = by_path.get(original["path"])
                if current is None or any(current[k] != original[k] for k in ("sha256", "bytes")):
                    raise ValueError(f"Omitted or changed sealed input: {original['path']}")
    return {"complete_central_directory": True, "crc_test_passed": True,
            "full_extraction_completed": True, "every_payload_hash_verified": True,
            "payload_files": len(rows), "zip_members": len(infos),
            "payload_bytes": sum(row["bytes"] for row in rows),
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "production_manifest_sha256": SEALED_SHA256,
            "sealed_production_files_verified": SEALED_COUNT,
            "extraction_directory": str(extraction), "archive_root": root}


def build(args):
    output = outside_study(args.output, "Archive output")
    extraction = outside_study(args.verification_dir, "Verification directory")
    receipt_path = outside_study(args.receipt, "Receipt")
    if len({output, extraction, receipt_path}) != 3:
        raise ValueError("Archive, extraction and receipt paths must be distinct")
    if extraction in output.parents or extraction in receipt_path.parents:
        raise ValueError("Output and receipt cannot be inside the future extraction directory")
    root = relative_path(args.archive_root)
    if "/" in root:
        raise ValueError("Archive root must be one directory name")
    receipt = new_receipt("build-and-fully-verify")
    start_wall, start_cpu = time.monotonic(), time.process_time()
    temporary = output.with_name(output.name + ".building-" + uuid.uuid4().hex)
    try:
        with phase(receipt, "source_selection_and_sealed_production_verification"):
            files, omissions = collect_inputs()
            check_requirements(files, args.paper, args.latex, final=True)
        manifest = {
            "schema": "agialpha-game-theoretic-companion/v1", "created_at": utcnow(),
            "archive_root": root,
            "production_manifest": {"path": SEALED_PATH, "sha256": SEALED_SHA256, "files": SEALED_COUNT},
            "files": files, "exclusions": omissions,
            "scope": "Complete selected new-study closure; prior-study custody limitations remain as originally disclosed. Not a complete archive of all preceding publications.",
            "portability": "Paths in this inventory are relative. Original provenance bytes, including historical absolute paths, are preserved rather than rewritten.",
            "external_system_prerequisites": ["CPython 3.12 Linux x86-64 with venv/ensurepip/pip", "Node.js (recorded 24.22.1)", "Optional figure rebuild: matplotlib 3.10.8 and NumPy 2.3.5 (recorded; not vendored)", "Optional paper rebuild: documented TeX distribution/packages", "Optional browser QA: Playwright and Chromium, not vendored"],
            "verification_receipt": "A separate sibling receipt records final ZIP SHA-256, CRC, complete extraction and payload hashes; it is outside the archive to avoid a circular hash.",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with phase(receipt, "write_and_close_complete_zip"):
            with temporary.open("xb") as stream:
                with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
                    for row in files:
                        path = ordinary_file(row["path"])
                        info = zipfile.ZipInfo(root + "/" + row["path"], date_time=(2026, 10, 26, 0, 0, 0))
                        info.create_system = 3
                        mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                        info.external_attr = (stat.S_IFREG | mode) << 16
                        info.compress_type = zipfile.ZIP_STORED if path.suffix.lower() in {".gz", ".whl", ".zip", ".pdf", ".png"} else zipfile.ZIP_DEFLATED
                        actual_hash, actual_size = hashlib.sha256(), 0
                        with path.open("rb") as source, zf.open(info, "w", force_zip64=True) as destination:
                            for chunk in iter(lambda: source.read(CHUNK), b""):
                                destination.write(chunk)
                                actual_hash.update(chunk)
                                actual_size += len(chunk)
                        if actual_size != row["bytes"] or actual_hash.hexdigest() != row["sha256"]:
                            raise ValueError(f"Input changed while packaging: {row['path']}")
                    info = zipfile.ZipInfo(root + "/" + ARCHIVE_MANIFEST, date_time=(2026, 10, 26, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    zf.writestr(info, json_bytes(manifest))
                stream.flush()
                os.fsync(stream.fileno())
        receipt["verification"] = verify_archive(temporary, extraction, receipt)
        with phase(receipt, "source_inventory_recheck_after_extraction"):
            after_files, after_omissions = collect_inputs()
            if after_files != files or after_omissions != omissions:
                raise ValueError("Source selection changed during packaging; no final archive is published")
        with phase(receipt, "final_archive_sha256"):
            receipt["archive"] = {"path": str(output), **digest(temporary)}
        # Hard-link creation is atomic and refuses to replace an existing output.
        os.link(temporary, output)
        temporary.unlink()
        receipt["status"] = "passed"
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc),
                              "partial_archive": str(temporary) if temporary.exists() else None}
        raise
    finally:
        finish_receipt(receipt, start_wall, start_cpu)
        write_new_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "archive": receipt["archive"],
                      "receipt": str(receipt_path), "verification": receipt["verification"]}))


def verify(args):
    archive = Path(args.archive).expanduser().resolve()
    if not archive.is_file():
        raise FileNotFoundError("Archive does not exist")
    extraction = outside_study(args.verification_dir, "Verification directory")
    receipt_path = outside_study(args.receipt, "Receipt")
    if receipt_path == extraction or extraction in receipt_path.parents or extraction in archive.parents:
        raise ValueError("Archive and receipt cannot be in the new extraction directory")
    receipt = new_receipt("verify-existing-archive")
    start_wall, start_cpu = time.monotonic(), time.process_time()
    try:
        receipt["archive"] = {"path": str(archive), **digest(archive)}
        receipt["verification"] = verify_archive(archive, extraction, receipt)
        if digest(archive) != {k: receipt["archive"][k] for k in ("bytes", "sha256")}:
            raise ValueError("Archive changed during verification")
        receipt["status"] = "passed"
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        finish_receipt(receipt, start_wall, start_cpu)
        write_new_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path),
                      "verification": receipt["verification"]}))


def plan(args):
    output = outside_study(args.out, "Plan output")
    files, omissions = collect_inputs()
    missing = check_requirements(files)
    write_new_json(output, {"schema": "agialpha-companion-preflight-plan/v1",
                           "created_at": utcnow(), "files": files,
                           "excluded": omissions, "missing_recorded_inputs": missing,
                           "final_build_additionally_requires": ["README.md", "LICENSE", "--paper existing.pdf", "--latex existing.tex"],
                           "archive_created": False})
    print(json.dumps({"plan": str(output), "selected_files": len(files),
                      "raw_bytes": sum(row["bytes"] for row in files),
                      "missing_recorded_inputs": missing, "archive_created": False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("plan", help="Inspect and hash selected inputs; create no archive")
    p.add_argument("--out", required=True)
    p.set_defaults(func=plan)
    p = sub.add_parser("build", help="Create a new final ZIP and fully extract/verify it")
    p.add_argument("--output", required=True)
    p.add_argument("--verification-dir", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--paper", required=True, help="PDF path relative to study root")
    p.add_argument("--latex", required=True, help="TeX path relative to study root")
    p.add_argument("--archive-root", default=DEFAULT_ROOT)
    p.set_defaults(func=build)
    p = sub.add_parser("verify", help="Fully extract and verify an existing final ZIP")
    p.add_argument("--archive", required=True)
    p.add_argument("--verification-dir", required=True)
    p.add_argument("--receipt", required=True)
    p.set_defaults(func=verify)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
