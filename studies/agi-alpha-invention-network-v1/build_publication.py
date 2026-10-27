# SPDX-License-Identifier: Apache-2.0
"""Build the research PDFs and self-contained browser editions from verified results."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT / "paper"


def run(command: list[str], *, cwd: Path, log: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    log.write_text(result.stdout + result.stderr)
    if result.returncode:
        print((result.stdout + result.stderr)[-6000:])
        raise RuntimeError(f"Build failed: {command[0]} ({result.returncode})")


def main() -> None:
    if "PENDING" in (PAPER / "results_generated.tex").read_text():
        raise ValueError("Refusing to build a paper with unresolved results")
    for source, name in [("paper.tex", "The_Network_That_Learns_to_Invent"), ("brief.tex", "Executive_Brief")]:
        run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-jobname=" + name, source],
            cwd=PAPER,
            log=ROOT / "evidence" / (name + "_build.log"),
        )
    source = (PAPER / "paper.tex").read_text()
    for n in range(1, 8):
        for figure in (PAPER / "figures").glob(f"figure{n}_*.pdf"):
            source = source.replace(figure.name, figure.with_suffix(".png").name)
    (PAPER / "paper_web.tex").write_text(source)
    command = [
        "pandoc",
        "paper_web.tex",
        "--from=latex",
        "--to=html5",
        "--standalone",
        "--embed-resources",
        "--mathml",
        "--metadata=lang:en",
        "--toc",
        "--citeproc",
        "--bibliography=../sources/sources.bib",
        "--css=web.css",
        "--metadata=title:The Network That Learns to Invent",
        "--output=../demo/paper.html",
    ]
    run(command, cwd=PAPER, log=ROOT / "evidence/paper_html_build.log")
    if (ROOT / "evidence_companion.md").exists():
        run(
            [
                "pandoc",
                "evidence_companion.md",
                "--from=gfm",
                "--to=html5",
                "--standalone",
                "--embed-resources",
                "--toc",
                "--metadata=lang:en",
                "--css=paper/web.css",
                "--metadata=title:Evidence Companion",
                "--output=demo/evidence.html",
            ],
            cwd=ROOT,
            log=ROOT / "evidence/companion_html_build.log",
        )
    print(
        json.dumps(
            {
                "pdfs": [str(PAPER / "The_Network_That_Learns_to_Invent.pdf"), str(PAPER / "Executive_Brief.pdf")],
                "browser_editions": ["demo/paper.html", "demo/evidence.html"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
