# SPDX-License-Identifier: Apache-2.0
"""Build and verify deterministic, bounded study and LaTeX delivery archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "agi-alpha-shared-observation-v1/"
MANIFEST = "publication/package-manifest.json"
EXCLUDED_DIRECTORIES = {
    "reproduction",
    "__pycache__",
    ".git",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
TEX_INTERMEDIATES = {".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk"}
COPIES = (
    "paper/AGI_Alpha_Flywheel.pdf",
    "paper/Executive_Brief.pdf",
    "paper/Evidence_Companion.pdf",
    "paper/AGI_Alpha_Flywheel.html",
    "docs/English_French_Demonstration.html",
    "paper/AGI_Alpha_Flywheel.tex",
)


def sha(data: bytes) -> str:
    """Hash exact delivered bytes."""
    return hashlib.sha256(data).hexdigest()


def encoded(value: Any) -> bytes:
    """Serialize deterministic manifest bytes."""
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def ordinary(path: Path) -> bytes:
    """Refuse links and nonfiles before reading a package member."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"ordinary file required: {path.name}")
    return path.read_bytes()


def write(path: Path, content: bytes) -> None:
    """Replace an ordinary output atomically without following a target symlink."""
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"ordinary output required: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".package-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def inventory() -> dict[str, bytes]:
    """Collect this study only, excluding reconstructible workspaces and build caches."""
    result = {}
    for folder, directories, filenames in os.walk(ROOT, followlinks=False):
        base = Path(folder)
        for name in directories:
            if (base / name).is_symlink():
                raise ValueError("symlink directory refused: " + str((base / name).relative_to(ROOT)))
        directories[:] = sorted(name for name in directories if name not in EXCLUDED_DIRECTORIES)
        for name in sorted(filenames):
            path = base / name
            relative = path.relative_to(ROOT).as_posix()
            if path.is_symlink():
                raise ValueError("symlink file refused: " + relative)
            if name == ".env" or name.startswith(".env.") or name in {"credentials.json", "id_rsa", "id_ed25519"}:
                raise ValueError("credential-like file must not enter a research archive: " + relative)
            if relative == MANIFEST or path.suffix in {".pyc", ".pyo"}:
                continue
            if relative.startswith("paper/") and (path.suffix in TEX_INTERMEDIATES or name.endswith(".synctex.gz")):
                continue
            result[relative] = ordinary(path)
    return dict(sorted(result.items()))


def verify_qa(files: dict[str, bytes]) -> None:
    """Require the final PDF and browser receipts to bind the exact packaged bytes."""
    pdf = json.loads(files["evidence/pdf-qa.json"])
    for row in pdf["artifacts"]:
        if row["result"] != "pass" or sha(files[row["path"]]) != row["sha256"]:
            raise ValueError("PDF evidence no longer matches: " + row["path"])
    for name in ["evidence/reader-qa.json", "evidence/demo-qa.json"]:
        record = json.loads(files[name])
        if record["passed"] != record["total"] or sha(files[record["artifact"]]) != record["artifact_sha256"]:
            raise ValueError("browser evidence no longer matches: " + name)


def rows(files: dict[str, bytes]) -> list[dict[str, Any]]:
    """Create a per-file identity inventory."""
    return [{"path": path, "bytes": len(data), "sha256": sha(data)} for path, data in sorted(files.items())]


def archive(target: Path, files: dict[str, bytes]) -> dict[str, Any]:
    """Create fixed-metadata ZIP_STORED bytes and verify CRC, content and restoration."""
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError("ordinary archive output required")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".archive-", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as bundle:
            for name, content in sorted(files.items()):
                member = PREFIX + name
                parts = PurePosixPath(member).parts
                if PurePosixPath(member).is_absolute() or ".." in parts or "\\" in member:
                    raise ValueError("unsafe archive member")
                item = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
                item.create_system = 3
                item.external_attr = 0o100644 << 16
                item.compress_type = zipfile.ZIP_STORED
                bundle.writestr(item, content)
        restored = 0
        with zipfile.ZipFile(temporary) as bundle, tempfile.TemporaryDirectory(prefix="agi-package-restore-") as folder:
            expected_names = [PREFIX + name for name in sorted(files)]
            if bundle.namelist() != expected_names or bundle.testzip() is not None:
                raise ValueError("archive member inventory or CRC verification failed")
            for name, expected in sorted(files.items()):
                content = bundle.read(PREFIX + name)
                if content != expected:
                    raise ValueError("archive content mismatch: " + name)
                destination = Path(folder) / PREFIX / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
                if sha(ordinary(destination)) != sha(expected):
                    raise ValueError("restored content mismatch: " + name)
                restored += 1
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    content = ordinary(target)
    return {
        "path": target.name,
        "bytes": len(content),
        "sha256": sha(content),
        "members": len(files),
        "crc_verified": True,
        "all_contents_verified": True,
        "restored_files_verified": restored,
        "format": "ZIP_STORED; sorted names; 1980-01-01 timestamp; ordinary 0644 files; no symlinks",
    }


def main() -> None:
    """Package already qualified artifacts without rebuilding or publishing them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Delivery folder outside the study source tree.")
    args = parser.parse_args()
    if args.output.is_symlink():
        parser.error("output directory may not be a symlink")
    output = args.output.resolve()
    if output == ROOT or output.is_relative_to(ROOT):
        parser.error("deliveries must be outside the study to prevent recursive inclusion")
    output.mkdir(parents=True, exist_ok=True)
    files = inventory()
    verify_qa(files)
    latex = {
        name: content
        for name, content in files.items()
        if name == "LICENSE"
        or (
            name.startswith("paper/")
            and (
                name.startswith("paper/figures/")
                or Path(name).suffix in {".tex", ".md", ".bib", ".lua", ".css", ".py"}
                or name == "paper/reader.template.html"
            )
        )
    }
    latex_manifest = {
        "schema": "shared-observation-latex-manifest/v1",
        "files": rows(latex),
        "self_reference": "MANIFEST.json is excluded from its own file list.",
        "requirements": "paper/FONT_REQUIREMENTS.md",
        "production_publication": False,
    }
    latex["MANIFEST.json"] = encoded(latex_manifest)
    manifest = {
        "schema": "shared-observation-package-manifest/v1",
        "study": "agi-alpha-shared-observation-v1",
        "files": rows(files),
        "self_reference": MANIFEST + " is included in the archive but excluded from this list.",
        "excluded": ["isolated reproduction workspaces", "caches", "LaTeX intermediates"],
        "retained": [
            "original failed trials",
            "compact reproduction receipts and command logs",
            "original source licenses",
        ],
        "latex_source_members": sorted(latex),
        "production_publication": False,
    }
    manifest_bytes = encoded(manifest)
    write(ROOT / MANIFEST, manifest_bytes)
    research = {**files, MANIFEST: manifest_bytes}
    reports = [
        archive(output / "AGI_Alpha_Flywheel_Research_Package.zip", research),
        archive(output / "AGI_Alpha_Flywheel_LaTeX.zip", latex),
    ]
    delivered = [report["path"] for report in reports]
    for name in COPIES:
        write(output / name, files[name])
        if ordinary(output / name) != files[name]:
            raise ValueError("copied deliverable differs: " + name)
        delivered.append(name)
    landing = """# AGI ALPHA FLYWHEEL — When Capability Creates Opportunity

## Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work

**Vincent Boucher — President of MONTREAL.AI**

Prepared research edition: executed finite synthetic model, modeled commercial assumptions, actual customer collections **$0**. The illustrative origin contributes **+$22.83** in expectation; **0/48** fresh offers launch under the frozen commercial policy; the combined modeled campaign contributes **−$323.17** before optional retention or R&D. These are not realized profits or a market sample.

- [Full paper — PDF](paper/AGI_Alpha_Flywheel.pdf)
- [Executive brief — PDF](paper/Executive_Brief.pdf)
- [Evidence companion — PDF](paper/Evidence_Companion.pdf)
- [Full browser edition](paper/AGI_Alpha_Flywheel.html)
- [English/French demonstration](docs/English_French_Demonstration.html)
- [Main LaTeX file](paper/AGI_Alpha_Flywheel.tex)
- [Complete research package](AGI_Alpha_Flywheel_Research_Package.zip)
- [LaTeX source bundle with figures and build requirements](AGI_Alpha_Flywheel_LaTeX.zip)
- [Checksums](SHA256SUMS)
- [Archive verification](package-verification.json)

The browser editions embed their display content. Extract the complete research ZIP for source navigation, original inputs, evidence and reproduction. It contains the full study README and a bounded replay command. Extract the LaTeX ZIP for the figure assets needed to compile the separate `.tex` file. The source-bundle font requirements identify the original environment-specific font location.

The complete package preserves failed experiments, fixture identity labels, source provenance and AI-assistance disclosures. Neither these files nor their verified archives establish live customer acceptance, production authority, a deployment or a stable published URL. The exact frozen compiler retains three known strict-mypy findings; full repository release qualification is pending.
"""
    write(output / "README.md", landing.encode())
    delivered.append("README.md")
    changed = [name for name, content in files.items() if ordinary(ROOT / name) != content]
    if changed:
        raise ValueError("source changed during packaging: " + ", ".join(changed))
    verification = {
        "schema": "shared-observation-package-verification/v1",
        "archives": reports,
        "source_files_excluding_manifest": len(files),
        "study_manifest": "publication/package-manifest.json",
        "source_unchanged_during_packaging": True,
        "copied_deliverables_verified": list(COPIES),
        "publication": "NOT_PERFORMED",
        "scope": "Archive integrity and byte restoration only; no new scientific or release-gate claim.",
    }
    write(output / "package-verification.json", encoded(verification))
    delivered.append("package-verification.json")
    sums = "".join(f"{sha(ordinary(output / name))}  {name}\n" for name in sorted(delivered))
    write(output / "SHA256SUMS", sums.encode())
    print(
        json.dumps(
            {
                "archives": reports,
                "source_files": len(files),
                "loose_outputs": sorted(delivered),
                "checksums": "SHA256SUMS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
