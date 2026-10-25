# SPDX-License-Identifier: Apache-2.0
"""Editable vector figures for the strategy-succession edition."""
from pathlib import Path
from datetime import datetime, timezone
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "svg.fonttype": "none", "svg.hashsalt": "agi-alpha-strategy-succession-v1", "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False})
INK, PURPLE, TEAL, GOLD = "#1C2536", "#5A31A0", "#007A78", "#A17E2C"
MUTED, PALE, ROSE = "#5D6577", "#F6F3FA", "#A64E61"


def save(fig, name):
    for ext in ("pdf", "svg"):
        metadata = {"Creator": "AGI ALPHA Strategy Succession figure source"}
        if ext == "pdf":
            metadata.update(CreationDate=datetime(2026,10,24,tzinfo=timezone.utc),
                            ModDate=datetime(2026,10,24,tzinfo=timezone.utc))
        else:
            metadata["Date"] = "2026-10-24T00:00:00Z"
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", pad_inches=.07,
                    metadata=metadata)
    plt.close(fig)


def canvas(w=10, h=5):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set(xlim=(0, 10), ylim=(0, h))
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, detail, color=PURPLE, face=PALE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.06,rounding_size=.10",
                               linewidth=1.1, edgecolor=color, facecolor=face))
    ax.text(x+.16, y+h-.25, title, ha="left", va="center", color=color,
            fontsize=11, fontweight="bold")
    ax.text(x+.16, y+h-.54, detail, ha="left", va="top", color=INK,
            fontsize=9.2, linespacing=1.5)


def arrow(ax, a, b, color=PURPLE, curved=0, dashed=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13,
                                linewidth=1.4, color=color,
                                linestyle="--" if dashed else "-",
                                connectionstyle=f"arc3,rad={curved}"))


def loop():
    fig, ax = canvas(10, 4.85)
    ax.text(.1, 4.66, "A mission can leave a method", color=INK,
            fontsize=15, fontweight="bold")
    ax.text(.1, 4.30, "The next result still needs a current check. Every attempt carries a cost.",
            fontsize=10, color=MUTED)
    box(ax, .15, 2.64, 2.75, 1.15, "01  Useful mission", "Jobs · crew · dependencies\nDeadline and permitted scope")
    box(ax, 3.63, 2.64, 2.75, 1.15, "02  Verified result", "Fresh schedule, checked again\nEvidence remains inspectable", TEAL)
    box(ax, 7.10, 2.64, 2.75, 1.15, "03  Bounded discovery", "Search fixed strategy language\nCharge search and checking")
    box(ax, 7.10, .85, 2.75, 1.15, "04  Two gates", "Correct and applicable?\nWorth keeping after full cost?", GOLD)
    box(ax, 3.63, .85, 2.75, 1.15, "05  Selective retention", "Keep useful executable means\nHold, retire or keep incumbent", TEAL)
    box(ax, .15, .85, 2.75, 1.15, "06  Fresh requirement", "Use or construct a successor\nTest inherited contribution")
    for a, b in [((2.98, 3.20), (3.55, 3.20)), ((6.46, 3.20), (7.02, 3.20)),
                 ((8.48, 2.57), (8.48, 2.08)), ((7.02, 1.42), (6.46, 1.42)),
                 ((3.55, 1.42), (2.98, 1.42)), ((1.52, 2.08), (1.52, 2.57))]:
        arrow(ax, a, b)
    ax.text(5, .28, "FIXED OUTSIDE THE CANDIDATE: purpose · evaluation · resource limits · authority",
            ha="center", fontsize=9, fontweight="bold", color=MUTED)
    save(fig, "mission-capability-loop")


def lineage():
    fig, ax = canvas(10, 4.65)
    ax.text(.1, 4.48, "Three different jobs for an inherited strategy", color=INK,
            fontsize=15, fontweight="bold")
    box(ax, .12, 1.77, 2.85, 1.90, "G1  Dispatch", "Ranks ready jobs\n\nRetains a bounded feature rule\nOutput: a feasible schedule", PURPLE)
    box(ax, 3.58, 1.77, 2.85, 1.90, "G2  Lookahead", "Tries the next decision\n\nRuns parent to finish suffixes\nOutput: a selected next action", TEAL)
    box(ax, 7.04, 1.77, 2.85, 1.90, "G3  Repair", "Preserves committed work\n\nMay use inherited suffix planner\nStable branch can skip parent", GOLD)
    arrow(ax, (3.04, 2.70), (3.50, 2.70))
    arrow(ax, (6.50, 2.70), (6.96, 2.70), TEAL)
    ax.text(5, 1.28, "TEST ACTUAL EXECUTION, NOT ONLY A PARENT POINTER", ha="center",
            color=MUTED, fontweight="bold", fontsize=9)
    ax.text(5, .89, "Remove the parent  ·  Rebuild it  ·  Supply an equivalent replacement", ha="center", fontsize=10, color=INK)
    ax.text(5, .45, "A correctly constructed child can still fail the investment gate.", ha="center",
            color=ROSE, fontweight="bold", fontsize=10)
    save(fig, "generation-lineage")


def boundaries():
    fig, ax = canvas(10, 4.75)
    ax.text(.1, 4.55, "Inheritance carries means, not current permission", color=INK,
            fontsize=15, fontweight="bold")
    box(ax, .15, 2.10, 4.20, 1.67, "Permitted inheritance", "Executable strategy and declared scope\nSource and parent digests\nHistorical observations and counterexamples\nRetention history", PURPLE)
    box(ax, 5.15, 2.10, 4.70, 1.67, "Current mission boundary", "WORLD: fresh jobs, calendar, deadline and locks\nPOLICY: exact applicable candidate\nPROOF and AUTHORITY start empty", TEAL)
    arrow(ax, (4.45, 2.91), (5.05, 2.91))
    box(ax, 5.15, .36, 4.70, 1.10, "External to candidate search", "Fixed checker + budget + source binding\nCurrent scoped permission, expiry and STOP", GOLD)
    arrow(ax, (7.50, 1.57), (7.50, 2.01), GOLD)
    ax.text(.20, 1.26, "Imported success is historical evidence.\nIt cannot authorize a new action or\nsubstitute for a new result check.",
            color=MUTED, fontsize=10, linespacing=1.5, va="top")
    save(fig, "proof-authority-boundary")


def regression_costs():
    fig, ax = plt.subplots(figsize=(9.4, 3.6))
    labels = ["No early assets", "Retained counterexamples", "Conventional same assets"]
    checking = [105994, 53721, 53721]
    acquisition = [0, 41785, 41785]
    retrieval = [0, 27177, 27177]
    y = [2, 1, 0]
    ax.barh(y, checking, color=PURPLE, height=.52, label="Checking")
    ax.barh(y, acquisition, left=checking, color=TEAL, height=.52, label="Acquire + retain")
    left = [a+b for a,b in zip(checking, acquisition)]
    ax.barh(y, retrieval, left=left, color=GOLD, height=.52, label="Retrieve")
    for yi, a, b, c in zip(y, checking, acquisition, retrieval):
        ax.text(a+b+c+2000, yi, f"{a+b+c:,}", va="center", fontsize=10, fontweight="bold", color=INK)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 144000)
    ax.set_xticks([0, 40000, 80000, 120000], ["0", "40,000", "80,000", "120,000"])
    ax.set_xlabel("Separate probe reference units · first batch, all acquisition charged", fontsize=10)
    ax.set_title("Earlier rejection is real. First-batch payback is absent.", loc="left", pad=18,
                 color=INK, fontsize=14, fontweight="bold")
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(.5, -.28), frameon=False, fontsize=9)
    ax.grid(axis="x", alpha=.13)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=9)
    fig.tight_layout()
    save(fig, "regression-costs")


def recovery():
    fig, ax = canvas(10, 5.2)
    ax.text(.1, 5.0, "Recover an accepted result; charge uncertain work", color=INK,
            fontsize=14, fontweight="bold")
    box(ax, .15, 3.12, 2.75, 1.12, "1  Durable intent", "Reserve bounded execution\nRecord source and request ID")
    box(ax, 3.63, 3.12, 2.75, 1.12, "2  Execute + check", "Fresh independent acceptance\nSave a ready result", TEAL)
    box(ax, 7.10, 3.12, 2.75, 1.12, "3  Commit receipt", "Advance cursor once\nPreserve cumulative cost")
    arrow(ax, (2.98, 3.67), (3.55, 3.67))
    arrow(ax, (6.46, 3.67), (7.02, 3.67))
    box(ax, .15, 1.21, 2.75, 1.18, "Interrupted intent", "Charge reserved ceiling\nRe-execution may be needed", GOLD)
    box(ax, 3.63, 1.21, 2.75, 1.18, "Lost acknowledgement", "Recheck saved result\nAvoid duplicate acceptance", TEAL)
    box(ax, 7.10, 1.21, 2.75, 1.18, "Invalid or stale state", "Reject / retain incumbent\nNo inherited authority", ROSE)
    arrow(ax, (1.52, 3.04), (1.52, 2.47), GOLD)
    arrow(ax, (5, 3.04), (5, 2.47), TEAL)
    arrow(ax, (8.48, 3.04), (8.48, 2.47), ROSE)
    ax.text(5, .57, "STOP · expiry · scope · wall deadline · work limit are checked at boundaries", ha="center",
            color=MUTED, fontsize=10)
    ax.text(5, .17, "A local freshness guard is not a cryptographic defense against a host administrator.", ha="center",
            color=MUTED, fontsize=9)
    save(fig, "failure-recovery-map")


if __name__ == "__main__":
    loop()
    lineage()
    boundaries()
    regression_costs()
    recovery()
