# SPDX-License-Identifier: Apache-2.0
"""Editable vector figures describing the design, without fabricated result data."""

from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).parent / "figures"
ROOT.mkdir(exist_ok=True)
C = {"ink": "#1C2536", "muted": "#5D6577", "purple": "#5A31A0", "paper": "#F6F3FA",
     "teal": "#007A78", "gold": "#A27B25", "rose": "#A64E61", "white": "#FFFFFF"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "pdf.fonttype": 42,
                     "svg.fonttype": "none", "svg.hashsalt": "agialpha-earned-turn-methods-04"})
STAMP = datetime(2026, 10, 24, tzinfo=timezone.utc)


def canvas(height):
    fig, ax = plt.subplots(figsize=(9, height))
    ax.set(xlim=(0, 9), ylim=(0, height))
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def box(ax, x, y, w, h, title, body="", color="purple", fill="paper", size=12):
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                          facecolor=C[fill], edgecolor=C[color], linewidth=1.3)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h - .24, title, ha="center", va="center", fontsize=13,
            fontweight="bold", color=C[color])
    if body:
        ax.text(x + w / 2, y + (h - .31) / 2, body, ha="center", va="center", fontsize=size,
                linespacing=1.32, color=C["ink"])


def arrow(ax, a, b, color="purple", dash=False, rad=0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=15,
                                color=C[color], linewidth=1.5,
                                linestyle="--" if dash else "-", connectionstyle=f"arc3,rad={rad}"))


def save(fig, stem):
    fig.savefig(ROOT / (stem + ".pdf"), metadata={"CreationDate": STAMP, "ModDate": STAMP,
                "Title": stem.replace("-", " "), "Author": "Vincent Boucher · MONTREAL.AI"})
    fig.savefig(ROOT / (stem + ".svg"), metadata={"Date": STAMP.isoformat(), "Creator": "AGI ALPHA Earned Turn"})
    plt.close(fig)


def loop():
    fig, ax = canvas(4.65)
    for x, title, body in [(.3, "SERVE", "A worthwhile mission\nwith bounded resources"),
                            (3.2, "VERIFY", "Fresh output check\nand complete cost"),
                            (6.1, "RETAIN", "Applicable method\nwith exact provenance")]:
        box(ax, x, 3.15, 2.6, 1.15, title, body, "teal" if title == "SERVE" else "purple")
    for x, title, body in [(.3, "CONSTRUCT", "Next distinct capability\nusing funded means"),
                            (3.2, "COMPARE", "Strong alternatives\nnet benefit and capacity"),
                            (6.1, "REUSE", "Changed fresh mission\nnew applicability check")]:
        box(ax, x, 1.15, 2.6, 1.15, title, body, "gold" if title == "CONSTRUCT" else "purple")
    arrow(ax, (2.93, 3.73), (3.15, 3.73))
    arrow(ax, (5.83, 3.73), (6.05, 3.73))
    arrow(ax, (7.4, 3.1), (7.4, 2.35))
    arrow(ax, (6.05, 1.73), (5.85, 1.73))
    arrow(ax, (3.15, 1.73), (2.95, 1.73), "gold")
    arrow(ax, (1.6, 2.35), (1.6, 3.1), "gold")
    ax.text(4.5, 2.72, "Every arrow needs an operation and evidence.", ha="center", fontsize=13, color=C["muted"])
    arrow(ax, (4.5, 1.1), (4.5, .65), "rose")
    ax.text(4.5, .35, "RETAIN INCUMBENT   ·   DEFER   ·   RETIRE   ·   STOP", ha="center",
            va="center", fontsize=12, color=C["rose"], fontweight="bold")
    save(fig, "mission-capability-loop")


def lineage():
    fig, ax = canvas(4.85)
    box(ax, .3, 3.3, 2.4, 1.15, "MISSION A", "Checked response\nNative factor byproduct", "teal")
    box(ax, 3.3, 3.3, 2.4, 1.15, "PARENT F", "solve(load)\nSame accepted operator")
    box(ax, 6.3, 3.3, 2.4, 1.15, "FRESH B", "New loads, new checks\nActual accepted B08", "teal")
    box(ax, 3.3, .8, 2.4, 1.4, "SUCCESSOR H", "W = F(U)\nNew operator A + UUᵀ\nPredecessor receipt bound")
    box(ax, 6.3, .8, 2.4, 1.4, "FRESH D", "Changed-network loads\nH invokes F again\nNew independent checks", "teal")
    box(ax, .3, .8, 2.4, 1.4, "INTERVENTIONS", "Remove / reconstruct\nEquivalent parent\nStrong direct solution", "rose")
    arrow(ax, (2.75, 3.88), (3.25, 3.88))
    arrow(ax, (5.75, 3.88), (6.25, 3.88))
    arrow(ax, (4.5, 3.25), (4.5, 2.25))
    ax.text(3.28, 2.72, "Parent actually\ncomputes basis", ha="center", fontsize=11.5, color=C["purple"])
    arrow(ax, (7.5, 3.25), (5.75, 2.1), "teal")
    ax.text(7.55, 2.67, "Accepted flows\nselect the change", ha="center", fontsize=11.5, color=C["teal"],
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 2})
    arrow(ax, (5.75, 1.5), (6.25, 1.5))
    arrow(ax, (2.75, 1.5), (3.25, 1.5), "rose", True)
    ax.text(4.5, .3, "An ancestry pointer is insufficient: construction calls and fresh delivery calls are recorded separately.",
            ha="center", fontsize=11.5, color=C["muted"])
    save(fig, "causal-lineage")


def ledger():
    fig, ax = canvas(4.9)
    box(ax, .35, 3.3, 3.5, 1.15, "SERVICE", "Externally endowed allowance\nPromised useful work", "teal")
    box(ax, 5.15, 3.3, 3.5, 1.15, "IMPROVEMENT", "Separate external research allowance\nFailed research stays charged", "purple")
    box(ax, .35, 1.15, 3.5, 1.15, "EARNED ACCOUNT", "Starts at zero\nBounded released service capacity", "gold")
    box(ax, 5.15, 1.15, 3.5, 1.15, "NEXT CONSTRUCTION", "Explicit reservation and actual charge\nSuccessor checked before use", "gold")
    arrow(ax, (2.1, 3.25), (2.1, 2.35), "teal")
    ax.text(2.1, 2.8, "Accepted service only", ha="center", va="center", fontsize=12,
            color=C["teal"], bbox={"facecolor": "white", "edgecolor": "none", "pad": 2})
    arrow(ax, (3.9, 1.73), (5.1, 1.73), "gold")
    ax.text(4.5, 2.15, "Fund", ha="center", fontsize=12, color=C["gold"])
    ax.text(6.9, 2.78, "No borrowing from\nthe service account", ha="center", fontsize=12, color=C["rose"])
    ax.text(4.5, .62, "TRANSFERS CONSERVE ENDOWMENT.  SAVING NEEDS A MATCHED MEASUREMENT.",
            ha="center", fontsize=11.5, fontweight="bold", color=C["ink"])
    ax.text(4.5, .23, "CPU capacity ≠ money   ·   Unused allowance ≠ demonstrated incremental benefit", ha="center",
            fontsize=11.5, color=C["muted"])
    save(fig, "resource-ledger")


def authority():
    fig, ax = canvas(3.95)
    data = [(.3, "WORLD", "Network and loads\nCurrent operator\nFixed purpose", "teal"),
            (2.5, "POLICY", "Executable methods\nComparison rules\nResource limits", "gold"),
            (4.7, "PROOF", "Fresh check\nExact source/input\nScoped evidence", "purple"),
            (6.9, "AUTHORITY", "Local study scope\nExpiry and STOP\nNo production grant", "rose")]
    for x, title, body, color in data:
        box(ax, x, 1.85, 1.8, 1.7, title, body, color, size=11.5)
    ax.text(4.5, 1.38, "Descendants receive applicable artifacts and historical evidence.",
            ha="center", fontsize=13, fontweight="bold", color=C["ink"])
    ax.text(4.5, .9, "Current qualification is rechecked.  Operational authority stays separately controlled.",
            ha="center", fontsize=12, color=C["muted"])
    ax.plot([.5, 8.5], [.52, .52], color=C["purple"], alpha=.4, lw=1)
    ax.text(4.5, .23, "Upstream workbench: institutional HOLD  ·  active proof [ ]  ·  authority [ ]  ·  settlement disconnected",
            ha="center", fontsize=11, color=C["purple"])
    save(fig, "proof-authority-boundary")


def recovery():
    fig, ax = canvas(5.55)
    ax.text(.35, 5.22, "OBSERVED STATE", fontsize=12, fontweight="bold", color=C["muted"])
    ax.text(4.8, 5.22, "PERMITTED RESPONSE", fontsize=12, fontweight="bold", color=C["muted"])
    rows = [
        (4.22, "Durable result; acknowledgement lost", "Return the same receipt", "No second execution or charge", "teal"),
        (3.25, "Pending reservation after interruption", "Quarantine the request", "Charge reserved ceiling; lost CPU unknown", "gold"),
        (2.28, "Stale source, dependency or receipt", "Refuse admission", "Preserve evidence and recorded costs", "rose"),
        (1.31, "STOP, expiry or exhausted allowance", "Hold further work", "Explicit resume cannot extend authority", "rose"),
        (.34, "Rejected descendant; rollback requested", "Select applicable incumbent", "Keep history; never readmit by restore", "purple"),
    ]
    for y, observed, response, explanation, color in rows:
        ax.add_patch(FancyBboxPatch((.3, y), 3.85, .77,
                     boxstyle="round,pad=0.02,rounding_size=0.08", facecolor=C["paper"],
                     edgecolor=C[color], linewidth=1.05))
        ax.text(2.225, y + .385, observed, fontsize=12, ha="center", va="center", color=C["ink"])
        arrow(ax, (4.2, y + .385), (4.68, y + .385), color)
        ax.text(4.83, y + .51, response, fontsize=12.5, fontweight="bold", color=C[color])
        ax.text(4.83, y + .17, explanation, fontsize=11.2, color=C["muted"])
    save(fig, "failure-recovery-map")


if __name__ == "__main__":
    loop()
    lineage()
    ledger()
    authority()
    recovery()
