# SPDX-License-Identifier: Apache-2.0
"""Build the paper, brief, figures and self-contained browser editions."""

from __future__ import annotations

import base64
import csv
import html
import json
import os
import re
import subprocess
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/paid-progress-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from economics import plant_and_evsi

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "publication"
OUT = ROOT / "output"
PURPLE, LILAC, INK, RED = "#402068", "#9C7CB8", "#272234", "#A94F5F"


def figures() -> None:
    """Render exact study plots, preserving scenario and evidence labels."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "savefig.facecolor": "white",
        }
    )
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    boxes = [
        (0.2, 3.15, "Useful digital\nmilestone", False),
        (3.55, 3.15, "Accepted work\nand collected fee", False),
        (6.9, 3.15, "Complete costs\nand available funds", False),
        (0.2, 0.55, "Evidence and\nremaining uncertainty", False),
        (3.55, 0.55, "Stop, defer,\npivot or continue", False),
        (6.9, 0.55, "Next worthwhile\nconstruction", True),
    ]
    for x, y, label, future in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                2.85,
                1.0,
                boxstyle="round,pad=0.08,rounding_size=0.08",
                facecolor="#F4EFF8" if y < 2 else PURPLE,
                edgecolor=PURPLE,
                linestyle="--" if future else "-",
                linewidth=1.4,
            )
        )
        ax.text(x + 1.425, y + 0.5, label, ha="center", va="center", fontsize=10.5, color=PURPLE if y < 2 else "white")
    for y in [3.65, 1.05]:
        for x in [3.05, 6.4]:
            ax.add_patch(
                FancyArrowPatch((x, y), (x + 0.43, y), arrowstyle="-|>", mutation_scale=14, color=LILAC, lw=1.5)
            )
    for x in [1.62, 8.33]:
        ax.add_patch(FancyArrowPatch((x, 3.05), (x, 1.7), arrowstyle="-|>", mutation_scale=14, color=LILAC, lw=1.5))
    ax.text(4.98, 4.65, "DELIVERY ENGINE", ha="center", fontweight="bold", color=PURPLE, fontsize=12)
    ax.text(4.98, 2.15, "OPPORTUNITY ENGINE", ha="center", fontweight="bold", color=PURPLE, fontsize=12)
    ax.text(
        4.98,
        0.05,
        "Provider fees   •   Customer decision value   •   Future venture rights",
        ha="center",
        fontsize=9,
        color="#75677F",
    )
    fig.savefig(ROOT / "figures/two_engines.png", dpi=180, bbox_inches="tight")
    fig.savefig(ROOT / "figures/two_engines.pdf", bbox_inches="tight")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    names = ["Stated annual\nsavings", "Cash operating\ncost", "Cash\nmargin", "Depreciation", "Accounting\nmargin"]
    values = [82000, 28630, 53370, 18000, 35370]
    ax.bar(names, np.array(values) / 1000, color=[LILAC, RED, PURPLE, "#B7A8C4", PURPLE], width=0.62)
    for i, v in enumerate(values):
        ax.text(i, v / 1000 + 1.5, f"€{v:,.0f}", ha="center", fontsize=10)
    ax.set_ylabel("Historical EUR thousands / year")
    ax.set_ylim(0, 95)
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/case_economics.png", dpi=180)
    fig.savefig(ROOT / "figures/case_economics.pdf")
    plt.close(fig)
    rows = list(csv.DictReader((ROOT / "results/complete/economics_worlds.csv").open()))
    scenarios = ["conservative", "central", "favorable"]
    vals = [
        np.array([float(r["full_project_profit_usd"]) for r in rows if r["scenario"] == s]) / 1000 for s in scenarios
    ]
    fig, ax = plt.subplots(figsize=(8.5, 4))
    bp = ax.boxplot(
        vals,
        labels=["Conservative", "Central", "Favorable"],
        whis=(5, 95),
        patch_artist=True,
        boxprops={"edgecolor": PURPLE},
        medianprops={"color": "white", "linewidth": 2},
        flierprops={"marker": ".", "markersize": 3, "alpha": 0.4, "markeredgecolor": RED},
    )
    for patch, color in zip(bp["boxes"], [RED, PURPLE, LILAC]):
        patch.set_facecolor(color)
    ax.axhline(0, color="#777", linewidth=1, linestyle="--")
    ax.scatter([1, 2, 3], [x.mean() for x in vals], color="#16111D", marker="D", s=27, zorder=5, label="Mean")
    ax.set_ylabel("Full-project profit, US$ thousands")
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Complete-cost replay • 256 histories per scenario", fontsize=11, color=PURPLE)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/profit_distribution.png", dpi=180)
    fig.savefig(ROOT / "figures/profit_distribution.pdf")
    plt.close(fig)
    config = json.loads((ROOT / "inputs/economics.json").read_text())
    fig, ax = plt.subplots(figsize=(8.5, 3.9))
    priors = np.linspace(0.2, 0.8, 121)
    for perf, color in zip([0.65, 0.8, 0.95], ["#AC94BD", PURPLE, "#247F86"]):
        net = [plant_and_evsi(config, float(p), perf, perf)["net_evsi_eur"] / 1000 for p in priors]
        ax.plot(priors, net, color=color, label=f"Sensitivity = specificity = {perf:.2f}", lw=2)
    ax.axhline(0, color="#777", ls="--", lw=1)
    ax.fill_between(priors, -10, 0, color="#F9EDEF")
    ax.set_xlabel("Hypothetical prior probability of viable plant operation")
    ax.set_ylabel("Net information value, EUR thousands")
    ax.set_xlim(0.2, 0.8)
    ax.set_ylim(-10, 62)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/information_value.png", dpi=180)
    fig.savefig(ROOT / "figures/information_value.pdf")
    plt.close(fig)


def embedded_html(source: Path, target: Path, title: str) -> None:
    """Create a no-network reading edition with embedded figures and CSS."""
    subprocess.run(
        [
            "pandoc",
            str(source.name),
            "--standalone",
            "--citeproc",
            "--toc",
            "--toc-depth=2",
            "--mathml",
            "--metadata",
            f"pagetitle={title}",
            "-o",
            str(target),
        ],
        cwd=PUB,
        check=True,
    )
    value = target.read_text()
    value = value.replace("</head>", "<style>" + (PUB / "reader.css").read_text() + "</style></head>")

    def img(match: re.Match[str]) -> str:
        relative = match.group(1)
        path = (PUB / relative).resolve()
        if path.exists() and path.suffix == ".png":
            return 'src="data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode() + '"'
        return match.group(0)

    value = re.sub(r'src="([^"]+)"', img, value)
    value = value.replace(
        "<body>", '<body><div class="badge">✦ ∞ Pinned research review edition • No actual sales</div>'
    )
    target.write_text(value)


def github_reader() -> None:
    """Resolve references and remove typesetting commands for public GitHub reading."""
    source = re.sub(r"^\\(?:clearpage|Needspace\{[^\n]*\})\s*$", "", (PUB / "manuscript.md").read_text(), flags=re.M)
    result = subprocess.run(
        ["pandoc", "--from=markdown", "--to=gfm", "--citeproc", "--wrap=none", "--metadata=link-citations:false"],
        input=source,
        cwd=PUB,
        text=True,
        capture_output=True,
        check=True,
    )
    header = """# 🌌♾️ AGI ALPHA FLYWHEEL — When Capability Creates Opportunity

## The Paid-Progress Option: An Industrial Water-Reuse Study

**Vincent Boucher — President of MONTREAL.AI**  
27 October 2026 · Pinned research review edition

[Paper PDF](../output/AGI_ALPHA_FLYWHEEL_Paid_Progress.pdf) · [Complete offline browser edition](../output/AGI_ALPHA_FLYWHEEL_Browser_Edition.html) · [Executable study](../downloads/AGI_ALPHA_FLYWHEEL_Study.zip)

"""
    (PUB / "reading_edition.md").write_text(header + result.stdout)


def compile_pdf(source: str, basename: str) -> None:
    """Retain standalone LaTeX and compile twice for stable navigation."""
    tex = PUB / (basename + ".tex")
    options = (
        ["--number-sections", "--toc", "--toc-depth=2", "-H", "cover.tex"]
        if source == "manuscript.md"
        else ["-H", "brief_cover.tex"]
    )
    subprocess.run(
        ["pandoc", source, "--standalone", "--citeproc", *options, "-H", "style.tex", "-o", str(tex)],
        cwd=PUB,
        check=True,
    )
    for _ in range(2):
        with (OUT / (basename + "_build.log")).open("w") as log:
            subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(OUT), str(tex)],
                cwd=PUB,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )


def main() -> None:
    """Build all user-facing publication formats from one complete manuscript."""
    OUT.mkdir(exist_ok=True)
    figures()
    compile_pdf("manuscript.md", "AGI_ALPHA_FLYWHEEL_Paid_Progress")
    compile_pdf("executive_brief.md", "AGI_ALPHA_FLYWHEEL_Executive_Brief")
    embedded_html(
        PUB / "manuscript.md",
        OUT / "AGI_ALPHA_FLYWHEEL_Browser_Edition.html",
        "AGI ALPHA FLYWHEEL — The Paid-Progress Option",
    )
    embedded_html(
        PUB / "executive_brief.md",
        OUT / "AGI_ALPHA_FLYWHEEL_Executive_Brief.html",
        "AGI ALPHA FLYWHEEL — Executive Brief",
    )
    github_reader()
    d = json.loads((ROOT / "evidence/published_delivery.json").read_text())
    css = (PUB / "reader.css").read_text()
    pack = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Reuse Investment Gate Pack — Public-case delivery</title><style>{css}</style></head><body><header><div class="badge">Executed digital milestone</div><h1>Reuse Investment Gate Pack</h1><p class="subtitle">Published industrial case • 27 October 2026</p><p>Decision: <strong>DEFER</strong>. Obtain a buyer process specification, representative operating evidence and complete costs before the next plant commitment.</p></header><main><h2>What the buyer receives</h2><p>A source-linked input record, an executable screen, cash and accounting reconciliation, explicit evidence gaps and the next measurement requirements. This sample uses public aggregate observations, not a commissioned buyer's confidential site data.</p><table><thead><tr><th>Quantity</th><th>Result</th></tr></thead><tbody><tr><td>Annual cash margin from stated costs</td><td>EUR53,370</td></tr><tr><td>Annual accounting margin</td><td>EUR35,370</td></tr><tr><td>Simple payback before omitted costs</td><td>3.3727 years</td></tr><tr><td>Conditional NPV at12%, ten years</td><td>EUR121,552.40</td></tr><tr><td>Actual customer acceptance or collections</td><td>None</td></tr></tbody></table><h2>Evidence and next measurements</h2><p>The output below names the unresolved requirements and binds the source and verifier. A discharge criterion is not a buyer's end-use specification. No plant design or operating permission is issued.</p><pre>{html.escape(json.dumps(d, indent=2))}</pre><h2>Source and reproduction</h2><p>Marjana Simonič(2021), <a href="https://doi.org/10.3390/membranes11120976">Reverse Osmosis Treatment of Wastewater for Reuse as Process Water—A Case Study</a>, CC BY4.0. The delivered arithmetic and decision screen are this study's work.</p><pre>python src/deliver.py inputs/published_case.json --output evidence/published_delivery.json</pre><p>Original numeric failures and post-confirmation recovery are preserved in the companion. Review edition; no canonical release or actual transaction is asserted.</p></main></body></html>"""
    (OUT / "Reuse_Investment_Gate_Pack.html").write_text(pack)
    print(
        json.dumps(
            {"pdfs": [str(p) for p in OUT.glob("*.pdf")], "html": [str(p) for p in OUT.glob("*.html")]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
