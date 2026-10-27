# SPDX-License-Identifier: Apache-2.0
"""Build the implementation paper from current source-bound executed evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build() -> None:
    packet = ROOT / "scripts/templates/alpha-flywheel/enterprise-evidence.json"
    raw = packet.read_bytes()
    report = json.loads(raw)
    for name, expected in report["sources"].items():
        path = ROOT / name
        if (
            path.is_symlink()
            or not path.is_relative_to(ROOT)
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError("paper source differs from recorded experiment: " + name)
    doc = (ROOT / "docs/agent/ENTERPRISE_NEXT_ADVANTAGE.md").read_text()
    methods = doc.split("## What was implemented\n", 1)[1].split("## Executed study and findings\n", 1)[0]
    results = doc.split("## Executed study and findings\n", 1)[1].split("## Reproduce and inspect\n", 1)[0]
    limits = doc.split("## Failure recovery and release boundary\n", 1)[1].split("## Français\n", 1)[0]
    path = report["technical_path"]
    fresh = path["fresh_evaluation"]["cases"]
    accepted = sum(r["v2"]["verification"]["accepted_finite_result"] for r in fresh)
    v1_work = sum(r["v1"]["logical_units"] for r in fresh)
    v2_work = sum(r["v2"]["logical_units"] for r in fresh)
    less = sum(r["v2"]["logical_units"] < r["v1"]["logical_units"] for r in fresh)
    body = f"""FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.

## Abstract

We connect versioned offerings and bounded enterprise decisions to an existing
reasoning/tool executor, optional workflow-learning Gym, protected capability
service and disjoint cost ledger. An internal engineering artifact is executed
and independently checked. The frozen workflow is tested on {len(fresh)} fresh
finite problems. The system preserves the economically defensible negative result:
admission is rejected, additional investment is declined, and an adjacent offering
remains a hypothesis. A separate fictional-authority episode tests actual protected
loading and invocation. Neither episode establishes live frontier-model advantage,
actual customer demand, complete-cost profit or sustained compounding.

## Observed milestone record

| Milestone | Recorded outcome |
|---|---|
| Internal useful delivery | Executed; finite independent acceptance |
| Optional Gym | Completed; executable v1 to v2 change |
| Fresh technical transfer | {accepted}/{len(fresh)} accepted; less search work on {less} |
| Logical search-work totals | v1: {v1_work:,}; v2: {v2_work:,} |
| Net Alpha admission | Rejected; competent frontier Beta unmeasured |
| Commercial authorization | Withheld; demand unmeasured |
| Next decision / adjacent offering | Hold funds / hypothesis |
| Actual provider calls / collections | 0 / USD 0 |
| Complete actual cost / profit | Unknown / not established |

Logical work is an algorithm diagnostic, not money, total CPU, verification cost
or customer value. Fictional accounting amounts are excluded from actual profit.

## Implementation and decision method

{methods}

## Executed comparisons and economics

{results}

## Failure boundaries and remaining qualification

{limits}

## Reproducible companion

The source companion contains the signed lifecycle contracts, recorder, independent
finite checker, directed regressions, bilingual evidence inspector and operator
guide. Run `PYTHONPATH=. python scripts/record_enterprise_flywheel.py --output NEW.json`
from a development checkout; outputs never overwrite prior evidence. Then build
this paper using `python scripts/build_enterprise_paper.py`. Every recorded runtime,
recorder and fixture source hash must match before the paper builder proceeds.
The original general-executor and specialist packets preserve their own historical
source identities and scopes. Future model or tool changes require new qualification.

Evidence packet SHA-256:

`{hashlib.sha256(raw).hexdigest()}`

Operator contracts are in `docs/agent/ENTERPRISE_NEXT_ADVANTAGE.md`.
"""
    header = r"""
\usepackage{xcolor}
\definecolor{alpha}{HTML}{613BB2}
\usepackage{titlesec}
\titleformat{\section}{\Large\bfseries\color{alpha}}{\thesection}{0.6em}{}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small AGI ALPHA FLYWHEEL}
\fancyhead[R]{\small Implementation and results}
\fancyfoot[L]{\small Vincent Boucher | MONTREAL.AI}
\fancyfoot[R]{\thepage}
\setlength{\headheight}{15pt}
\emergencystretch=3em
"""
    output = ROOT / "docs/papers"
    output.mkdir(exist_ok=True)
    stem = "agi-alpha-enterprise-implementation-v1"
    with tempfile.TemporaryDirectory(prefix="enterprise-paper-") as temporary:
        work = Path(temporary)
        (work / "paper.md").write_text(body)
        (work / "header.tex").write_text(header)
        subprocess.run(
            [
                "pandoc",
                str(work / "paper.md"),
                "--standalone",
                "--to=latex",
                "--top-level-division=section",
                "--metadata",
                "title=AGI ALPHA FLYWHEEL: The Enterprise That Invents Its Next Advantage",
                "--metadata",
                "author=Vincent Boucher",
                "--metadata",
                "date=27 October 2026",
                "-V",
                "mainfont=DejaVu Serif",
                "-V",
                "sansfont=DejaVu Sans",
                "-V",
                "monofont=DejaVu Sans Mono",
                "-V",
                "fontsize=10pt",
                "-V",
                "geometry:margin=0.85in",
                "-V",
                "colorlinks=true",
                "-V",
                "urlcolor=alpha",
                "--include-in-header",
                str(work / "header.tex"),
                "--output",
                str(work / "paper.tex"),
            ],
            check=True,
        )
        tex = (
            (work / "paper.tex")
            .read_text()
            .replace(r"\author{Vincent Boucher}", r"\author{Vincent Boucher\\President of MONTREAL.AI}")
        )
        (work / "paper.tex").write_text(tex)
        environment = {**os.environ, "SOURCE_DATE_EPOCH": "1793059200"}
        for _ in range(2):
            compiled = subprocess.run(
                ["xelatex", "-halt-on-error", "-interaction=nonstopmode", "paper.tex"],
                cwd=work,
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if compiled.returncode:
                raise RuntimeError(compiled.stdout.decode(errors="replace")[-5000:])
        shutil.copyfile(work / "paper.tex", output / (stem + ".tex"))
        shutil.copyfile(work / "paper.pdf", output / (stem + ".pdf"))
        print(
            json.dumps(
                {
                    "paper": str(output / (stem + ".pdf")),
                    "accepted": accepted,
                    "fresh": len(fresh),
                    "v1_logical_work": v1_work,
                    "v2_logical_work": v2_work,
                }
            )
        )


if __name__ == "__main__":
    build()
