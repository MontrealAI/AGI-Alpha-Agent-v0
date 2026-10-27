# SPDX-License-Identifier: Apache-2.0
"""Assemble the complete artifact and compact public source without changing evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
STUDY_REL = Path("studies/agi-alpha-operational-alpha-v2")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def included(path: Path) -> bool:
    rel = path.relative_to(STUDY)
    if any(p.startswith(".") or p == "__pycache__" for p in rel.parts):
        return False
    if path.suffix in {".pyc", ".aux", ".out", ".toc", ".fls", ".fdb_latexmk"}:
        return False
    if rel.parts[0] == "validation" and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        return False
    if path.name == "reader_expanded.tex" or (rel.parts[0] == "paper" and path.suffix == ".log"):
        return False
    return path.is_file()


def record(path: Path, root: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "git_blob_sha": hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest(),
    }


def archive(source: Path, output: Path) -> None:
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=(2026, 10, 27, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                info.compress_type = (
                    zipfile.ZIP_STORED if path.suffix in {".gz", ".zip", ".pdf", ".png"} else zipfile.ZIP_DEFLATED
                )
                z.writestr(info, path.read_bytes(), compresslevel=9)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--deliverables", type=Path, required=True)
    args = parser.parse_args()
    stage, deliverables = args.stage.resolve(), args.deliverables.resolve()
    if stage.exists() or deliverables.exists():
        raise ValueError("Use new staging and deliverable directories; existing artifacts are never replaced")
    full, compact = stage / "full", stage / "compact"
    full.mkdir(parents=True)
    compact.mkdir()
    deliverables.mkdir(parents=True)
    omitted = {
        x["path"]
        for x in json.loads((STUDY / "packaging/public_data_manifest.json").read_text())["omitted_from_compact_source"]
    }
    for path in sorted(STUDY.rglob("*")):
        if not included(path):
            continue
        relative = path.relative_to(STUDY)
        dest = full / STUDY_REL / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        if relative.as_posix() not in omitted:
            public = compact / STUDY_REL / relative
            public.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, public)
    closure = json.loads((STUDY / "validation/full_edition_review.sources.json").read_text())
    prefix = Path(closure["prior_integration_directory"])
    for item in closure["prior_integration_files"]:
        src = REPO / prefix / item["path"]
        assert sha(src) == item["sha256"]
        dst = full / prefix / item["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    for name in ("docs/Invent_the_Economy.tex", "LICENSE"):
        dst = full / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, dst)
    start = """# AGI ALPHA FLYWHEEL — additive research edition 2.1.0

Vincent Boucher — President of MONTREAL.AI

Open studies/agi-alpha-operational-alpha-v2/README.md for the complete edition.
All original recorded data are included. No API, wallet or live identity is needed to replay.

```sh
cd studies/agi-alpha-operational-alpha-v2
python reproduce_all.py --report validation/my_replay.json
```

The paper, three-page executive brief, ten-page evidence companion, LaTeX source,
complete English/French demonstration and full offline HTML reader are inside paper/ and browser/.
The source closure includes only the study's required prior native files, not the whole repository.
The original study README and reproduction guides explain limits, dependencies and source rights.
"""
    (full / "START_HERE.md").write_text(start)
    manifest = {
        "edition": "2.1.0",
        "scope": "Complete recorded research artifact; no live-operation qualification",
        "files": [record(p, full) for p in sorted(full.rglob("*")) if p.is_file()],
    }
    (full / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    public = {
        "edition": "2.1.0",
        "parent_commit": "231834269599d85e49cfe1ca9917a1a874522d44",
        "parent_tree": "213f7fdd552f894ebd454fb154e351f3f1bb982a",
        "omitted_generated_data": sorted(omitted),
        "files": [record(p, compact) for p in sorted(compact.rglob("*")) if p.is_file()],
    }
    (stage / "public_manifest.json").write_text(json.dumps(public, indent=2) + "\n")
    output = deliverables / "AGI_ALPHA_FLYWHEEL_Reproducible_Edition_2_1_0.zip"
    archive(full, output)
    latex = stage / "latex"
    latex.mkdir()
    for path in (STUDY / "paper").rglob("*"):
        if path.is_file() and (path.suffix in {".tex", ".py"} or path.parent.name == "figures"):
            dest = latex / path.relative_to(STUDY / "paper")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
    (latex / "README.txt").write_text(
        "Compile paper.tex, executive_brief.tex and evidence_companion.tex with pdflatex twice.\nAll required generated tables and figures are included. Full evidence and table-generation inputs are in the reproducible edition archive.\nThe preserved pre-opportunity draft is retained under history/.\n"
    )
    archive(latex, deliverables / "AGI_ALPHA_FLYWHEEL_LaTeX_2_1_0.zip")
    outputs = {
        "paper/paper.pdf": "AGI_ALPHA_FLYWHEEL_2_1_0.pdf",
        "paper/executive_brief.pdf": "AGI_ALPHA_FLYWHEEL_Executive_Brief_2_1_0.pdf",
        "paper/evidence_companion.pdf": "AGI_ALPHA_FLYWHEEL_Evidence_Companion_2_1_0.pdf",
        "browser/index.html": "AGI_ALPHA_FLYWHEEL_Demonstration_EN_FR_2_1_0.html",
        "paper/Browser_Edition.html": "AGI_ALPHA_FLYWHEEL_Browser_Edition_2_1_0.html",
    }
    for src, dst in outputs.items():
        shutil.copyfile(STUDY / src, deliverables / dst)
    artifact_manifest = {
        "edition": "2.1.0",
        "files": [record(p, deliverables) for p in sorted(deliverables.iterdir()) if p.is_file()],
    }
    (deliverables / "AGI_ALPHA_FLYWHEEL_SHA256_2_1_0.json").write_text(json.dumps(artifact_manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "full_files": len(manifest["files"]),
                "public_files": len(public["files"]),
                "public_bytes": sum(x["bytes"] for x in public["files"]),
                "full_archive_bytes": output.stat().st_size,
                "deliverables": str(deliverables),
                "stage": str(stage),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
