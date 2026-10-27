# SPDX-License-Identifier: Apache-2.0
"""Build publication figures from preserved observations and labeled assumptions."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
NAVY, TEAL, CORAL, GREY = "#152b45", "#138a8a", "#c36345", "#627481"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": NAVY,
        "text.color": NAVY,
        "axes.titleweight": "bold",
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def workflow() -> None:
    data = json.loads((ROOT / "results/workflow_assay.json").read_text())
    arms = ["U", "E", "E+"]
    first = [
        next(r["elapsed_seconds"] for r in data["rows"] if r["condition"] == a and r["packet"] == "A") for a in arms
    ]
    second = [
        next(r["elapsed_seconds"] for r in data["rows"] if r["condition"] == a and r["packet"] == "B") for a in arms
    ]
    fig, ax = plt.subplots(figsize=(8.2, 3.2), layout="constrained")
    x = np.arange(3)
    ax.barh(x, first, color=NAVY, label="A · first packet")
    ax.barh(x, second, left=first, color=TEAL, label="B · fresh mission, own work retained")
    for i, (a, b) in enumerate(zip(first, second, strict=True)):
        ax.text(a / 2, i, f"{a:.1f} s", color="white", ha="center", va="center")
        ax.text(a + b / 2, i, f"{b:.1f} s", color="white", ha="center", va="center")
        ax.text(a + b + 2, i, "24/24 correct", va="center", fontsize=9)
    ax.set_yticks(x, ["U · direct use", "E · expert procedure", "E+ · procedure + artifact"])
    ax.invert_yaxis()
    ax.set_xlim(0, 193)
    ax.set_xlabel("Recorded execution elapsed seconds · not labor time or a bill")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), frameon=False, ncol=2, fontsize=9)
    ax.grid(axis="x", alpha=0.12)
    ax.set_axisbelow(True)
    save(fig, "workflow")


def witness() -> None:
    data = json.loads((ROOT / "results/information_loss_witness.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.0), sharey=True, layout="constrained")
    for ax, key, title in zip(
        axes, ["a", "b"], ["Charter A · documented flowers", "Charter B · documented nectar"], strict=True
    ):
        seasons = ["early", "mid", "late"]
        xs = np.arange(3)
        source = [data[key]["source_coverage"][s]["count"] for s in seasons]
        supply = [data[key]["supply_coverage"][s]["count"] for s in seasons]
        ax.bar(xs - 0.18, source, width=0.34, color=NAVY, label="Source coverage")
        ax.bar(xs + 0.18, supply, width=0.34, color=TEAL, label="Qualified lot coverage")
        ax.axhline(3, color=CORAL, linestyle="--", label="Required minimum")
        for i, (s, q) in enumerate(zip(source, supply, strict=True)):
            ax.text(i - 0.18, s + 0.12, str(s), ha="center", fontsize=9)
            ax.text(i + 0.18, q + 0.12, str(q), ha="center", fontsize=9)
        ax.set_xticks(xs, ["Early", "Mid", "Late"])
        ax.set_ylim(0, 6.0)
        ax.set_title(title, fontsize=11)
        ax.grid(axis="y", alpha=0.12)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Distinct documented taxa")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False, fontsize=9)
    save(fig, "witness")


def cash() -> None:
    with (ROOT / "economics/results/cash_curve.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    day = [float(r["day"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8.2, 3.3), layout="constrained")
    for key, label, color in [
        ("cash_usd", "Cash", NAVY),
        ("reserve_usd", "Refund + operating reserve", CORAL),
        ("available_funds_usd", "Available funds", TEAL),
    ]:
        ax.step(day, [float(r[key]) for r in rows], where="post", color=color, label=label, linewidth=2)
        ax.scatter(day, [float(r[key]) for r in rows], color=color, s=18)
    ax.set_xticks(day, ["Capital\nDay −10", "Deposit\nDay 0", "Cost\nDay 2", "Accepted\nDay 7", "Collected\nDay 14"])
    ax.set_ylabel("USD · entirely assumed illustration")
    ax.set_ylim(0, 650)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3, frameon=False, fontsize=9)
    ax.grid(alpha=0.12)
    ax.text(2, 102, "$75 available\nafter paying A", color=TEAL, fontsize=9, ha="center")
    save(fig, "cash")


def retention() -> None:
    n = np.arange(0, 101)
    fig, ax = plt.subplots(figsize=(8.2, 3.5), layout="constrained")
    for gross, color in [(1, GREY), (3, CORAL), (5, TEAL), (10, NAVY)]:
        ax.plot(n, n * (gross - 2) - 100, color=color, label=f"Assumed gross benefit ${gross}/reuse", linewidth=2)
    ax.axhline(0, color=GREY, linewidth=0.8)
    ax.fill_between(n, -210, 0, color=CORAL, alpha=0.07)
    ax.set_xlabel("Fresh qualifying reuses · demand is not observed")
    ax.set_ylabel("Incremental value, USD · assumptions")
    ax.set_ylim(-210, 720)
    ax.set_xlim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.grid(alpha=0.12)
    ax.text(98, -160, "STOP region", ha="right", color=CORAL)
    save(fig, "retention")


if __name__ == "__main__":
    workflow()
    witness()
    cash()
    retention()
