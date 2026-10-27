# SPDX-License-Identifier: Apache-2.0
"""Plot the measured finite-context outcome without extending its scope of assurance."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "technical/robust/results/crossing_deliverable.json"
OUT = ROOT / "paper/figures"
NAVY = "#142B3A"
TEAL = "#087E8B"
GOLD = "#B39758"
MUTED = "#506273"
PALE = "#EDF4F4"


def main() -> None:
    data = json.loads(SOURCE.read_text())
    responses = np.asarray(data["actual_verified_responses"])
    controls = np.asarray(data["chosen_controls"])
    result = data["acceptance"]
    assert len(responses) == 16 and np.sum(responses >= 0) == 12
    assert result["accepted"] and result["oracle_calls"] == 40
    assert np.isclose(np.mean(responses), result["verified_mean"])
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":11, "text.color":NAVY,
                         "axes.labelcolor":NAVY, "xtick.color":MUTED, "ytick.color":MUTED,
                         "axes.edgecolor":"#CCD6DB", "pdf.fonttype":42, "savefig.facecolor":"white"})
    fig = plt.figure(figsize=(11.8, 5.4), facecolor="white")
    gs = fig.add_gridspec(2, 2, width_ratios=[2.45, 1.05], height_ratios=[1.4, 1.0],
                          left=0.065, right=0.97, top=0.79, bottom=0.20, wspace=0.25, hspace=0.30)
    ax = fig.add_subplot(gs[:, 0])
    x = np.arange(1, 17)
    ax.bar(x, responses, color=[TEAL if y >= 0 else GOLD for y in responses], width=0.73,
           edgecolor="white", linewidth=0.5, zorder=3)
    ax.axhline(0, color=NAVY, linewidth=1.1, zorder=2)
    ax.axhline(np.mean(responses), color=TEAL, linestyle=(0, (3, 3)), linewidth=1.1, zorder=2)
    ax.set_ylim(-1.28, 1.52)
    ax.set_xlim(0.3, 16.7)
    ax.set_xticks(x)
    ax.set_yticks([-1.0, -0.5, 0, 0.5, 1.0, 1.5])
    ax.set_xlabel("Declared environmental context", labelpad=8)
    ax.set_ylabel("Observed response (synthetic units)", labelpad=8)
    ax.yaxis.grid(True, color="#E5EBEE", linewidth=0.65, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=9.5, length=0, pad=6)
    ax.tick_params(axis="y", labelsize=9.5, length=0, pad=6)
    ax.legend(handles=[Patch(facecolor=TEAL,label="Nonnegative: 12"),Patch(facecolor=GOLD,label="Negative: 4"),
                       Line2D([0],[0],color=TEAL,linestyle=(0,(3,3)),label="Mean")],
              frameon=False, loc="upper left", ncol=3, fontsize=10, handlelength=1.0, columnspacing=1.5)

    metrics = fig.add_subplot(gs[0, 1])
    metrics.axis("off")
    metrics.text(0, 1.00, "ACTUAL ACCEPTANCE", fontsize=10, fontweight="bold", color=TEAL, va="top")
    entries = [("Mean response", f"{np.mean(responses):.6f}", "required ≥ 0.4"),
               ("Coverage", "12 / 16", "required ≥ 12 nonnegative"),
               ("Known control cost", f"{result['chosen_plan_cost']:.5f}", "required ≤ 1.2")]
    for y, (label, value, condition) in zip([0.74, 0.42, 0.10], entries):
        metrics.text(0, y, label, fontsize=10, color=MUTED, va="center")
        metrics.text(1, y, value, fontsize=14, fontweight="bold", ha="right", va="center")
        metrics.text(1, y-0.13, condition, fontsize=9, color=MUTED, ha="right", va="center")

    control_ax = fig.add_subplot(gs[1, 1])
    positions = np.arange(5)
    control_ax.barh(positions, controls, height=0.48, color=NAVY, alpha=0.85)
    control_ax.axvline(0, color="#B8C8CE", lw=0.7)
    control_ax.set_yticks(positions, [f"u{i+1}" for i in positions])
    control_ax.set_xlim(-1, 1)
    control_ax.set_xticks([-1, 0, 1])
    control_ax.invert_yaxis()
    control_ax.spines[["top", "right", "left"]].set_visible(False)
    control_ax.tick_params(axis="both", length=0, labelsize=9)
    control_ax.set_title("One control vector for all 16 contexts", fontsize=10, loc="left", color=MUTED, pad=8)
    for y, value in zip(positions, controls):
        control_ax.text(0.99, y, f"{value:+.3f}", ha="right", va="center", fontsize=9,
                        bbox={"facecolor":"white", "edgecolor":"none", "pad":0.8})

    fig.text(0.065, 0.94, "Post-hoc illustrative accepted task", fontsize=18, fontweight="bold", color=NAVY)
    fig.text(0.065, 0.885, f"{data['task_id']}  |  40 total simulator calls, including all 16 final context checks",
             fontsize=11, color=MUTED)
    fig.text(0.065, 0.07, "All four ordinary configurations failed at the same 40-call budget on this task.",
             fontsize=10, color=NAVY)
    fig.text(0.065, 0.025, "One disclosed synthetic witness; finite-context acceptance does not establish robustness to noise or unseen environments.",
             fontsize=9, color=MUTED)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "witness.pdf", bbox_inches="tight", pad_inches=0.14)
    fig.savefig(OUT / "witness.png", dpi=220, bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)
    print(json.dumps({"pdf":str(OUT / "witness.pdf"),"png":str(OUT / "witness.png"),"mean":float(np.mean(responses))}))


if __name__ == "__main__":
    main()
