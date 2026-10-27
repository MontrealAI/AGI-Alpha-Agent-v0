# SPDX-License-Identifier: Apache-2.0
"""Package the additive study without mutating historical or frozen evidence.

Large exact records are supplied through the independently verified restoration
closure. Temporary compiler/cache files and locally inspected page renders are
not distribution payload. Scientific figure PDF/PNG files remain included.
"""

from pathlib import Path
import hashlib
import json
import zipfile

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
PUB = STUDY / "publication"
BUNDLE = PUB / "AGI_ALPHA_FLYWHEEL_v4_reproducible_bundle.zip"
MANIFEST = PUB / "PAYLOAD_MANIFEST.json"
DELIVERABLES = PUB / "DELIVERABLES.json"
CACHE_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
               "venv_current", "venv_reported"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def selected_files() -> list[Path]:
    """Only exact restoration omissions; do not silently follow global ignores."""
    omissions = {line[1:] for line in (STUDY / ".gitignore").read_text().splitlines()
                 if line.startswith("/") and not line.endswith("/")}
    selected = []
    for path in sorted(STUDY.rglob("*")):
        if not path.is_file() or any(part in CACHE_PARTS for part in path.parts):
            continue
        if path.is_symlink():
            raise ValueError("Symlink outside ordinary-file distribution policy")
        name = path.relative_to(STUDY).as_posix()
        if name in omissions or path in {BUNDLE, MANIFEST, DELIVERABLES}:
            continue
        if path.suffix in {".aux", ".out", ".toc", ".pyc", ".fls", ".fdb_latexmk"}:
            continue
        if name.startswith("publication/") and path.suffix == ".log":
            continue
        if name.startswith("publication/qa/") and path.suffix == ".png":
            continue
        if name == "publication/figures/01_actual_geometry.svg":
            continue
        if name.startswith("publication/PUBLICATION_RECEIPT"):
            continue
        selected.append(path)
    return selected


def record(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": path.relative_to(REPO).as_posix(), "bytes": len(raw),
            "sha256": digest(raw),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def main() -> None:
    files = selected_files()
    records = [record(path) for path in files]
    generated_html = {"AGI_ALPHA_FLYWHEEL_v4.html", "demo.html"}
    bundle_files = [path for path in files if not (
        path.is_relative_to(PUB) and
        (path.suffix in {".pdf", ".png", ".svg"} or path.name in generated_html))]
    bundle_names = {path.relative_to(REPO).as_posix() for path in bundle_files}
    bundle_records = [item for item in records if item["path"] in bundle_names]
    manifest = {
        "schema": "additive-study-distribution/v1", "edition": "v4",
        "parent_commit": "231834269599d85e49cfe1ca9917a1a874522d44",
        "runtime_commit": "80b345828f34fd8a6e592977dd17ef37141305f4",
        "scope": "Research source and evidence; not software release qualification",
        "files": records,
        "bundle_file_paths": sorted(bundle_names),
        "bundle_scope": "Implementation, exact data, manuscript/build sources and evidence. Compiled publication PDFs, figures, screenshots and standalone HTML are separate repository downloads; their identities remain in this full distribution manifest.",
        "manifest_and_container_excluded_from_own_hash_closure": True,
        "omissions": "Exact raw records listed in .gitignore restore losslessly; caches, TeX intermediates and QA page PNGs omitted; large geometry SVG regenerates from make_figures.py while its PDF and PNG are included. No original scientific record is deleted.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    readme = (
        "AGI ALPHA FLYWHEEL — When Capability Creates Opportunity\n"
        "Additive research edition v4 — Vincent Boucher, President of MONTREAL.AI\n\n"
        "This archive contains the new study only. Preserve or clone the parent\n"
        "repository commit 231834269599d85e49cfe1ca9917a1a874522d44, then overlay\n"
        "the studies/ directory without replacing different existing files.\n"
        "Read studies/agi-alpha-opportunity-discovery-v4/README.md and\n"
        "REPRODUCIBILITY.md. Run prepare_reproduction.py to restore exact historical\n"
        "and compressed evidence before numerical reproduction.\n\n"
        "Compiled PDFs, figures and standalone HTML are separate downloads\n"
        "in the same repository publication directory. This ZIP preserves\n"
        "their manuscript/build sources and all implementation/data evidence.\n"
        "Those reading editions need no experiment dependencies. Publication\n"
        "reveals the former protected evaluation; future claims need fresh tests.\n"
        "Actual earned customer revenue is zero. Markets and finance are modeled.\n"
    ).encode()
    with zipfile.ZipFile(BUNDLE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in bundle_files + [MANIFEST]:
            info = zipfile.ZipInfo(path.relative_to(REPO).as_posix(), (2026, 10, 27, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("BUNDLE_README.txt", (2026, 10, 27, 0, 0, 0))
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, readme)
    with zipfile.ZipFile(BUNDLE) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive CRC validation failed")
        for item in bundle_records:
            if digest(archive.read(item["path"])) != item["sha256"]:
                raise ValueError("Archive identity mismatch: " + item["path"])
    names = ["AGI_ALPHA_FLYWHEEL_v4.pdf", "AGI_ALPHA_FLYWHEEL_v4.tex",
             "AGI_ALPHA_FLYWHEEL_v4_Executive_Brief.pdf",
             "AGI_ALPHA_FLYWHEEL_v4_Evidence_Companion.pdf",
             "AGI_ALPHA_FLYWHEEL_v4.html", "demo.html", "PAPER.md",
             "PAYLOAD_MANIFEST.json", BUNDLE.name]
    DELIVERABLES.write_text(json.dumps({
        "schema": "research-deliverable-identities/v1", "edition": "v4",
        "files": [record(PUB / name) for name in names],
        "bundle_verified_payload_files": len(bundle_records),
        "all_archive_payload_hashes_match": True,
        "publication": "Dedicated unmerged research branch; canonical release and site qualification remain separate"
    }, indent=2) + "\n")
    print(json.dumps({"files": len(records), "payload_bytes": sum(x["bytes"] for x in records),
                      "bundle": record(BUNDLE)}, indent=2))


if __name__ == "__main__":
    main()
