#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the study's PDF/LaTeX documents and self-contained browser reader."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


PAPER = Path(__file__).resolve().parent
DOCUMENTS = (
    ("manuscript.md", "AGI_Alpha_Flywheel"),
    ("executive_brief.md", "Executive_Brief"),
    ("evidence_companion.md", "Evidence_Companion"),
)


def run(command: list[str], cwd: Path) -> None:
    """Run a build command, retaining the full diagnostic in a local log."""
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{command[0]} failed:\n{result.stdout[-6000:]}\n{result.stderr[-3000:]}")


def build_pdf(source: str, stem: str) -> None:
    """Convert canonical Markdown to inspectable LaTeX and a PDF."""
    run(
        [
            "pandoc",
            source,
            "--from=markdown",
            "--to=latex",
            "--standalone",
            "--no-highlight",
            "--template=template.tex",
            "--lua-filter=path_wrap.lua",
            "--citeproc",
            "--bibliography=references.bib",
            "--number-sections",
            "--resource-path=.",
            "-o",
            f"{stem}.tex",
        ],
        PAPER,
    )
    for _ in range(2):
        run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex"], PAPER)
    log = (PAPER / f"{stem}.log").read_text(errors="replace")
    issues = [line for line in log.splitlines() if "Overfull" in line or "Missing character:" in line]
    if issues:
        raise RuntimeError(f"Layout diagnostics require review for {stem}:\n" + "\n".join(issues))


def build_reader() -> None:
    """Render the same manuscript, embedding every figure and stylesheet."""
    markdown = (PAPER / "manuscript.md").read_text()
    for name in (PAPER / "figures").glob("*.png"):
        markdown = markdown.replace(f"figures/{name.stem}.pdf", f"figures/{name.name}")
    with tempfile.TemporaryDirectory(prefix="agi-reader-") as directory:
        source = Path(directory) / "reader.md"
        source.write_text(markdown)
        run(
            [
                "pandoc",
                str(source),
                "--from=markdown",
                "--to=html5",
                "--standalone",
                "--template=reader.template.html",
                "--css=reader.css",
                "--embed-resources",
                "--mathml",
                "--toc",
                "--toc-depth=2",
                "--number-sections",
                "--citeproc",
                "--bibliography=references.bib",
                "--resource-path=.",
                "-o",
                "AGI_Alpha_Flywheel.html",
            ],
            PAPER,
        )


def main() -> None:
    """Build selected documents and record their content identities."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reader-only", action="store_true")
    args = parser.parse_args()
    os.environ.setdefault("SOURCE_DATE_EPOCH", "1793102400")
    if not args.reader_only:
        for source, stem in DOCUMENTS:
            build_pdf(source, stem)
    build_reader()
    paths = [PAPER / "AGI_Alpha_Flywheel.html"]
    if not args.reader_only:
        paths += [PAPER / f"{stem}.{suffix}" for _, stem in DOCUMENTS for suffix in ("tex", "pdf")]
    receipt = {
        "schema": "shared-observation-document-build/v1",
        "scope": "Document build only; semantic and visual review are separate evidence.",
        "artifacts": {
            str(path.relative_to(PAPER)): {
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in paths
        },
    }
    (PAPER / "document-build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
