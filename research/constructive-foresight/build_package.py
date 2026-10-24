# SPDX-License-Identifier: Apache-2.0
"""Package and reopen every research payload with exact size and SHA-256 checks."""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP_SUFFIXES = {".pyc", ".aux", ".log", ".fls", ".fdb_latexmk", ".out", ".xdv", ".blg"}
SKIP_FILES = {"MANIFEST.json", "publication/validation-http.json"}


def payloads() -> list[Path]:
    found = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if not path.is_file() or any(p in {"__pycache__", ".git"} for p in rel.parts):
            continue
        if path.suffix in SKIP_SUFFIXES or str(rel) in SKIP_FILES or rel.parts[:2] == ("publication", "assets"):
            continue
        if path.name.startswith("AGI_ALPHA_Constructive_Foresight_Complete_Source"):
            continue
        found.append(path)
    return sorted(found)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New ZIP path outside this research tree")
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(ROOT):
        raise ValueError("Choose a new output path outside the research tree")
    files = payloads()
    manifest = {"schema": "writer9-complete-research-manifest/v1",
                "canonical_pdf": "paper/paper.pdf",
                "scope": "Complete research source, fixed public inputs, retained evidence, paper and passive publication handoff",
                "excluded_reproducible_work": "Python/TeX caches; duplicate publication/assets downloads; self-referential external HTTP/ZIP delivery validation",
                "payloads": {str(p.relative_to(ROOT)): {"bytes": p.stat().st_size,
                             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}}
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    (ROOT / "MANIFEST.json").write_bytes(manifest_bytes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, str(path.relative_to(ROOT)))
        archive.writestr("MANIFEST.json", manifest_bytes)
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(manifest["payloads"]) | {"MANIFEST.json"}
        for name, entry in manifest["payloads"].items():
            data = archive.read(name)
            assert len(data) == entry["bytes"] and hashlib.sha256(data).hexdigest() == entry["sha256"], name
    print(json.dumps({"path": str(args.output.resolve()), "bytes": args.output.stat().st_size,
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                      "payloads": len(files), "all_payloads_reopened_and_verified": True}, indent=2))


if __name__ == "__main__":
    main()
