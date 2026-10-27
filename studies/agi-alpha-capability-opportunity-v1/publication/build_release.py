# SPDX-License-Identifier: Apache-2.0
"""Build and verify local research-release assets; never publish, commit, or contact a service."""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
import os
import posixpath
import re
import stat
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

STUDY = Path(__file__).resolve().parent.parent
STUDY_ID = "agi-alpha-capability-opportunity-v1"
REPOSITORY = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0"
RELEASE_TAG = "study-capability-creates-opportunity-v1-2026-10-27"
FROZEN_MAIN = "80b345828f34fd8a6e592977dd17ef37141305f4"
FROZEN_LIFECYCLE = "2727262caa52766a78916f2ed81f5afaf668edce"
ZIP_TIME = (2026, 10, 27, 0, 0, 0)
INNER_MANIFEST = "RESEARCH_MANIFEST.json"
COMPLETE_ZIP = "AGI_Alpha_Complete_Research.zip"
LATEX_ZIP = "AGI_Alpha_LaTeX_Source.zip"
PDF_ASSETS = {
    "paper/paper.pdf": "AGI_Alpha_When_Capability_Creates_Opportunity.pdf",
    "paper/executive-brief.pdf": "Executive_Brief.pdf",
    "paper/evidence-companion.pdf": "Evidence_Companion.pdf",
}
HTML_ASSETS = {
    "paper/paper.html": "Browser_Edition.html",
    "browser/index.html": "English_French_Demonstration.html",
    "paper/evidence-companion.html": "Evidence_Companion.html",
    "paper/executive-brief.html": "Executive_Brief.html",
}
SKIP_DIRECTORIES = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    ".ipynb_checkpoints",
    "tmp",
    "temp",
    "temporary",
}
PUBLICATION_OUTPUTS = {"artifacts", "output", "outputs", "releases", "release", "dist", "build", "_build"}
SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".aux",
    ".log",
    ".out",
    ".toc",
    ".fls",
    ".fdb_latexmk",
    ".blg",
    ".bcf",
    ".xdv",
    ".buildlog",
    ".tmp",
    ".temp",
    ".swp",
    ".swo",
    ".bak",
}
HREF = re.compile(r"(?P<prefix>\bhref\s*=\s*)(?P<quote>['\"])(?P<value>.*?)(?P=quote)", re.I | re.S)
TEX_REFERENCE = re.compile(r"\\(input|include|includegraphics|bibliography)\s*(?:\[[^\]]*\])?\s*\{([^{}]+)\}")


def encoded_json(value: Any) -> bytes:
    """Use stable UTF-8 JSON without local timestamps or workspace paths."""
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    """Return a lowercase SHA-256 content identity."""
    return hashlib.sha256(data).hexdigest()


def omitted(relative: PurePosixPath) -> bool:
    """Exclude transient tools, compilation intermediates and prior release outputs."""
    if any(part in SKIP_DIRECTORIES for part in relative.parts):
        return True
    if relative.parts[:1] == ("publication",) and any(part in PUBLICATION_OUTPUTS for part in relative.parts[1:]):
        return True
    name = relative.name.lower()
    return (
        name == ".ds_store"
        or name.endswith("~")
        or relative.suffix.lower() in SKIP_SUFFIXES
        or name.endswith((".synctex.gz", ".run.xml", ".build.log"))
        or name.startswith("buildlog")
    )


def collect(output: Path) -> tuple[dict[str, bytes], list[str]]:
    """Snapshot ordinary study files and reject symlink indirection."""
    payloads: dict[str, bytes] = {}
    exclusions: list[str] = []
    for directory, subdirs, filenames in os.walk(STUDY, followlinks=False):
        current = Path(directory)
        kept = []
        for name in sorted(subdirs):
            child = current / name
            relative = PurePosixPath(child.relative_to(STUDY).as_posix())
            if child.resolve() == output or omitted(relative):
                exclusions.append(relative.as_posix() + "/")
                continue
            if child.is_symlink():
                raise ValueError("A study directory is a symlink: " + relative.as_posix())
            kept.append(name)
        subdirs[:] = kept
        for name in sorted(filenames):
            path = current / name
            relative = PurePosixPath(path.relative_to(STUDY).as_posix())
            if omitted(relative):
                exclusions.append(relative.as_posix())
                continue
            if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
                raise ValueError("A study payload is not an ordinary file: " + relative.as_posix())
            if relative.as_posix() == INNER_MANIFEST:
                raise ValueError("Reserved archive manifest already exists in the study root")
            payloads[relative.as_posix()] = path.read_bytes()
    for required in ["README.md", "source_audit.md", "paper/paper.tex", *PDF_ASSETS, *HTML_ASSETS]:
        if required not in payloads:
            raise ValueError("Missing required final study artifact: " + required)
    return dict(sorted(payloads.items())), sorted(exclusions)


def scope() -> dict[str, Any]:
    """Keep research distribution distinct from software, security and business qualification."""
    return {
        "edition": "Experimental research prerelease; not the software release or a Pages deployment",
        "technical": "Executed synthetic learning, transfer and finite-task verification",
        "economics": "Conditional enterprise simulation; prices, demand and collections are not customer sales",
        "actual_customer_collections_usd": 0,
        "live_frontier_benchmark_calls": 0,
        "live_ens_authentications": 0,
        "production_admission": "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE",
        "jobs_governance_settlement_changed": False,
        "public_download_verification": "Not performed by this offline packager; publication owner must verify downloads",
    }


def file_records(payloads: dict[str, bytes]) -> list[dict[str, Any]]:
    """Bind every relative payload path to bytes and content hash."""
    return [{"path": path, "bytes": len(data), "sha256": sha256(data)} for path, data in sorted(payloads.items())]


def source_metadata(commit: str) -> dict[str, Any]:
    """Record the exact caller-declared source without pretending to fetch it."""
    return {
        "repository": REPOSITORY,
        "declared_source_commit": commit,
        "declared_source_url": f"{REPOSITORY}/tree/{commit}/studies/{STUDY_ID}",
        "source_commit_verification": "Caller-supplied identity; offline packaging does not verify remote Git state",
        "frozen_main_commit": FROZEN_MAIN,
        "frozen_research_lifecycle_commit": FROZEN_LIFECYCLE,
    }


def archive_manifest(payloads: dict[str, bytes], commit: str, kind: str) -> dict[str, Any]:
    """Create a manifest hashing all archive contents except the manifest itself."""
    return {
        "schema": "agi-alpha-capability-opportunity-research-archive/v1",
        "study": STUDY_ID,
        "title": "AGI ALPHA FLYWHEEL — When Capability Creates Opportunity",
        "author": "Vincent Boucher, President of MONTREAL.AI",
        "edition_date": "2026-10-27",
        "archive_kind": kind,
        "archive_root": STUDY_ID,
        "source": source_metadata(commit),
        "scope": scope(),
        "rights": "New source Apache-2.0; original upstream license files preserved",
        "hash_exclusion": "Only RESEARCH_MANIFEST.json is excluded from its own payload hash list",
        "payload_count": len(payloads),
        "payload_bytes": sum(map(len, payloads.values())),
        "files": file_records(payloads),
    }


def write_archive(path: Path, payloads: dict[str, bytes], commit: str, kind: str) -> dict[str, Any]:
    """Write deterministic ZIP metadata, then verify CRC and every decompressed byte."""
    manifest_bytes = encoded_json(archive_manifest(payloads, commit, kind))
    contents = {**payloads, INNER_MANIFEST: manifest_bytes}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        for relative, data in sorted(contents.items()):
            info = zipfile.ZipInfo(STUDY_ID + "/" + relative, date_time=ZIP_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        expected = {STUDY_ID + "/" + name for name in contents}
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("Archive member coverage failed: " + path.name)
        bad = archive.testzip()
        if bad is not None:
            raise ValueError("Archive CRC failed: " + bad)
        for relative, original in contents.items():
            restored = archive.read(STUDY_ID + "/" + relative)
            if restored != original:
                raise ValueError("Archive bytes changed: " + relative)
        restored_manifest = json.loads(archive.read(STUDY_ID + "/" + INNER_MANIFEST))
        for record in restored_manifest["files"]:
            data = archive.read(STUDY_ID + "/" + record["path"])
            if len(data) != record["bytes"] or sha256(data) != record["sha256"]:
                raise ValueError("Archive manifest digest failed: " + record["path"])
    return {
        "asset": path.name,
        "members": len(contents),
        "payload_hashes_verified": len(payloads),
        "manifest_bytes_verified": True,
        "crc_verified": True,
        "all_original_bytes_preserved": True,
    }


def latex_payloads(all_payloads: dict[str, bytes], commit: str) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Include compile inputs and the recorded data needed by publication builders."""
    selected: dict[str, bytes] = {}
    for path, data in all_payloads.items():
        p = PurePosixPath(path)
        if p.parts[:1] != ("paper",):
            continue
        if p.suffix in {".tex", ".bib", ".sty", ".cls", ".py"} or (
            p.parts[:2] == ("paper", "figures") and p.suffix in {".pdf", ".png", ".svg", ".eps"}
        ):
            selected[path] = data
    # The existing generators use literal study-relative inputs plus the six ledger paths.
    for path, data in list(selected.items()):
        if path.endswith(".py"):
            for node in ast.walk(ast.parse(data.decode("utf-8"))):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in all_payloads:
                    selected[node.value] = all_payloads[node.value]
    for path, data in all_payloads.items():
        if path.startswith("economics/results/ledger_") and path.endswith("_seed0.json"):
            selected[path] = data
    resolved = []
    for path, data in list(selected.items()):
        if not path.endswith(".tex"):
            continue
        text = re.sub(r"(?<!\\)%[^\n]*", "", data.decode("utf-8"))
        for command, reference in TEX_REFERENCE.findall(text):
            references = reference.split(",") if command == "bibliography" else [reference]
            for item in references:
                if "\\" in item or "#" in item:
                    raise ValueError("Dynamic LaTeX input needs explicit packaging support: " + item)
                extensions = [""]
                if not PurePosixPath(item).suffix:
                    extensions = (
                        [".pdf", ".png", ".eps"]
                        if command == "includegraphics"
                        else [".bib" if command == "bibliography" else ".tex"]
                    )
                candidates = [posixpath.normpath("paper/" + item + ext) for ext in extensions]
                found = next((candidate for candidate in candidates if candidate in selected), None)
                if found is None:
                    raise ValueError(f"Missing LaTeX input in source archive: {path}: {item}")
                resolved.append({"document": path, "command": command, "input": found})
    instructions = f"""# LaTeX source archive

Vincent Boucher — President of MONTREAL.AI
AGI ALPHA FLYWHEEL — When Capability Creates Opportunity

Declared source: {commit}
This is an experimental research source package, not software or production qualification.
All included original files are byte-exact. RESEARCH_MANIFEST.json binds every payload except itself.
The complete companion contains the full implementation, frozen policies and every research result.

From this archive's study root:

    python paper/build_report.py
    python paper/build_figures.py
    python paper/build_html.py

The recorded publication inputs and representative ledgers are included. Figure generation requires
NumPy and Matplotlib. LaTeX/HTML prerequisites are stated in the builders and original sources.
Alternatively, compile the supplied generated inputs directly from the paper directory:

    pdflatex -interaction=nonstopmode -halt-on-error paper.tex
    pdflatex -interaction=nonstopmode -halt-on-error paper.tex
    pdflatex -interaction=nonstopmode -halt-on-error executive-brief.tex
    pdflatex -interaction=nonstopmode -halt-on-error evidence-companion.tex

The packager checks all explicit input/include/figure/bibliography references. This is a source-input
check, not PDF visual QA. Actual scientific and economic limitations remain in the paper.
"""
    selected["LATEX_README.md"] = instructions.encode("utf-8")
    return dict(sorted(selected.items())), {
        "explicit_references_checked": len(resolved),
        "references": resolved,
        "builder_data_inputs": sorted(p for p in selected if not p.startswith("paper/")),
    }


class StandaloneHTML(HTMLParser):
    """Rewrite relative hyperlinks without altering embedded images or scripts."""

    def __init__(self, source_path: str, payloads: dict[str, bytes], commit: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source_path = source_path
        self.payloads = payloads
        self.commit = commit
        self.parts: list[str] = []
        self.rewrites: list[dict[str, str]] = []

    def link(self, raw: str) -> str:
        """Map local editions to release assets and evidence to exact source paths."""
        value = html.unescape(raw)
        parsed = urlsplit(value)
        if not value or parsed.scheme or parsed.netloc or not parsed.path:
            return raw
        if parsed.path.startswith("/"):
            raise ValueError("Root-relative hyperlink cannot be resolved offline: " + value)
        target = posixpath.normpath(posixpath.join(posixpath.dirname(self.source_path), unquote(parsed.path)))
        if target == ".." or target.startswith("../") or target not in self.payloads:
            raise ValueError("Missing or out-of-study hyperlink: " + self.source_path + " -> " + value)
        assets = {**PDF_ASSETS, **HTML_ASSETS}
        if target in assets:
            url = f"{REPOSITORY}/releases/download/{RELEASE_TAG}/{quote(assets[target])}"
        else:
            url = f"{REPOSITORY}/blob/{self.commit}/studies/{STUDY_ID}/{quote(target, safe='/')}"
        destination = urlsplit(url)
        url = urlunsplit((destination.scheme, destination.netloc, destination.path, parsed.query, parsed.fragment))
        self.rewrites.append({"original": value, "target": url})
        return html.escape(url, quote=True)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text()
        if raw is None:
            raise ValueError("Missing original HTML start tag")
        if any(name.lower() == "href" for name, _ in attrs):
            if HREF.search(raw) is None:
                raise ValueError("Unquoted href requires explicit support")
            raw = HREF.sub(
                lambda match: match["prefix"] + match["quote"] + self.link(match["value"]) + match["quote"], raw
            )
        for name, value in attrs:
            if name.lower() == "src" and value:
                parsed = urlsplit(value)
                if not parsed.scheme and not parsed.netloc:
                    raise ValueError("Standalone HTML still has a relative resource: " + value)
        self.parts.append(raw)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        self.parts.append("</" + tag + ">")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append("&" + name + ";")

    def handle_charref(self, name: str) -> None:
        self.parts.append("&#" + name + ";")

    def handle_comment(self, data: str) -> None:
        self.parts.append("<!--" + data + "-->")

    def handle_decl(self, decl: str) -> None:
        self.parts.append("<!" + decl + ">")

    def handle_pi(self, data: str) -> None:
        self.parts.append("<?" + data + ">")


def rewrite_html(source: str, data: bytes, payloads: dict[str, bytes], commit: str) -> tuple[bytes, dict[str, Any]]:
    """Build a standalone copy and check it contains no unresolved local hyperlink."""
    parser = StandaloneHTML(source, payloads, commit)
    parser.feed(data.decode("utf-8"))
    parser.close()
    result = "".join(parser.parts).encode("utf-8")
    verifier = StandaloneHTML(source, payloads, commit)
    verifier.feed(result.decode("utf-8"))
    verifier.close()
    if verifier.rewrites:
        raise ValueError("A relative hyperlink survived standalone rewriting")
    return result, {
        "original_study_path": source,
        "original_sha256": sha256(data),
        "standalone_sha256": sha256(result),
        "rewritten_hyperlinks": parser.rewrites,
        "relative_hyperlinks_remaining": 0,
        "remote_targets_download_verified": False,
    }


def asset_records(output: Path, names: list[str]) -> list[dict[str, Any]]:
    """Describe emitted assets without writing absolute local paths into metadata."""
    return [
        {
            "name": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha256((output / name).read_bytes()),
            "planned_url": f"{REPOSITORY}/releases/download/{RELEASE_TAG}/{quote(name)}",
        }
        for name in sorted(names)
    ]


def write_release_metadata(output: Path, names: list[str], commit: str) -> None:
    """Keep a directed digest structure: SHA256SUMS hashes metadata, never vice versa."""
    manifest = {
        "schema": "agi-alpha-capability-opportunity-research-release/v1",
        "tag": RELEASE_TAG,
        "publication_state": "PREPARED_LOCALLY_NOT_PUBLISHED",
        "planned_release_url": f"{REPOSITORY}/releases/tag/{RELEASE_TAG}",
        "source": source_metadata(commit),
        "scope": scope(),
        "assets": asset_records(output, names),
        "metadata_assets": [
            {"name": "release-manifest.json", "role": "This manifest; its digest is in SHA256SUMS"},
            {"name": "SHA256SUMS", "role": "Outer SHA-256 index covering every emitted file except itself"},
        ],
        "digest_structure": "ZIP manifests hash all payloads except themselves. This metadata hashes release payloads and PACKAGE_VALIDATION.json. SHA256SUMS hashes every output except itself, including this metadata. Circular metadata digests are intentionally not invented.",
    }
    (output / "release-manifest.json").write_bytes(encoded_json(manifest))
    all_names = sorted([*names, "release-manifest.json"])
    checksums = "".join(sha256((output / name).read_bytes()) + "  " + name + "\n" for name in all_names)
    (output / "SHA256SUMS").write_text(checksums, encoding="utf-8")


def verify_checksums(output: Path) -> int:
    """Verify complete outer-index coverage, without excluding validation or metadata."""
    names = []
    for line in (output / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        names.append(name)
        if PurePosixPath(name).name != name or sha256((output / name).read_bytes()) != expected:
            raise ValueError("Release checksum failed: " + name)
    actual = {path.name for path in output.iterdir() if path.is_file() and path.name != "SHA256SUMS"}
    if len(names) != len(set(names)) or set(names) != actual:
        raise ValueError("Outer checksum index omitted or duplicated an asset")
    return len(names)


def build(output: Path, commit: str) -> dict[str, Any]:
    """Produce a complete, locally verified research package without external writes."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("--source-commit must be an exact lowercase 40-character Git commit SHA")
    if not output.is_absolute():
        raise ValueError("--output must be an absolute directory path")
    output = output.resolve()
    if output == STUDY or STUDY.is_relative_to(output):
        raise ValueError("Output cannot be the study directory or its ancestor")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output must be absent or empty; earlier packages are never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    payloads, exclusions = collect(output)
    latex, latex_checks = latex_payloads(payloads, commit)
    archives = [
        write_archive(output / COMPLETE_ZIP, payloads, commit, "complete-research"),
        write_archive(output / LATEX_ZIP, latex, commit, "latex-and-publication-inputs"),
    ]
    for source, target in PDF_ASSETS.items():
        data = payloads[source]
        if not data.startswith(b"%PDF-"):
            raise ValueError("Expected a completed PDF: " + source)
        (output / target).write_bytes(data)
    html_checks = []
    for source, target in HTML_ASSETS.items():
        data, check = rewrite_html(source, payloads[source], payloads, commit)
        (output / target).write_bytes(data)
        html_checks.append({"asset": target, **check})
    changed = [
        path
        for path, original in payloads.items()
        if not (STUDY / path).is_file() or (STUDY / path).read_bytes() != original
    ]
    if changed:
        raise ValueError("Study files changed during packaging: " + ", ".join(changed))
    names = [COMPLETE_ZIP, LATEX_ZIP, *PDF_ASSETS.values(), *HTML_ASSETS.values(), "PACKAGE_VALIDATION.json"]
    validation = {
        "schema": "agi-alpha-capability-opportunity-package-validation/v1",
        "declared_source_commit": commit,
        "all_local_checks_passed": True,
        "archives": archives,
        "latex_inputs": latex_checks,
        "standalone_html": html_checks,
        "source_snapshot_unchanged": True,
        "complete_payload_files": len(payloads),
        "complete_payload_bytes": sum(map(len, payloads.values())),
        "excluded_transient_paths": exclusions,
        "pdf_visual_qa_performed_by_packager": False,
        "source_commit_remote_verification_performed": False,
        "public_asset_download_verification_performed": False,
        "outer_checksum_index": "Pending final construction",
        "publication_or_commit_performed": False,
    }
    (output / "PACKAGE_VALIDATION.json").write_bytes(encoded_json(validation))
    write_release_metadata(output, names, commit)
    verified = verify_checksums(output)
    validation["outer_checksum_index"] = "Every emitted asset except SHA256SUMS itself was verified"
    validation["outer_checksum_entries_verified"] = verified
    (output / "PACKAGE_VALIDATION.json").write_bytes(encoded_json(validation))
    write_release_metadata(output, names, commit)
    if verify_checksums(output) != verified:
        raise ValueError("Final checksum coverage changed")
    return {
        "all_local_checks_passed": True,
        "declared_source_commit": commit,
        "release_tag": RELEASE_TAG,
        "emitted_files": verified + 1,
        "complete_payload_files": len(payloads),
        "complete_payload_bytes": sum(map(len, payloads.values())),
        "archives": archives,
        "published": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.output, arguments.source_commit), indent=2, sort_keys=True))
