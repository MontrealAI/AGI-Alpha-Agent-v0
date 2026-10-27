# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
NAVY, TEAL, GOLD, RED, GRAY = "#142c42", "#007f81", "#d3953a", "#aa4c46", "#516271"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": NAVY,
        "text.color": NAVY,
        "xtick.color": GRAY,
        "ytick.color": GRAY,
        "axes.titleweight": "bold",
        "savefig.facecolor": "white",
    }
)


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    dev = json.loads((ROOT / "development/development-summary.json").read_text())
    original = json.loads((ROOT / "development/original-frame.json").read_text())
    mapped = json.loads((ROOT / "development/mapped-instrument.json").read_text())
    array_path = ROOT / "data/development/idr0062/native_labels.npy"
    if array_path.exists():
        array = np.load(array_path, mmap_mode="r")
    else:
        array = np.load(io.BytesIO(gzip.decompress(array_path.with_suffix(".npy.gz").read_bytes())))
    colors = plt.colormaps["turbo"](np.linspace(0.04, 0.94, 62))
    colors[0] = [0.04, 0.085, 0.13, 1]
    fig, ax = plt.subplots(1, 2, figsize=(10.2, 4.0), gridspec_kw={"width_ratios": [1, 1.2]})
    ax[0].imshow(
        array[118],
        cmap=ListedColormap(colors),
        vmin=0,
        vmax=61,
        origin="lower",
        extent=[-0.18, 97.49, -0.18, 98.93],
        interpolation="nearest",
    )
    ax[0].set(xlabel="Native x (µm)", ylabel="Native y (µm)", title="A published segmentation")
    centers = np.asarray([x["native_centroid_um"] for x in original["objects"]])
    transformed = np.asarray([x["mapped_centroid_um"] for x in mapped["objects"]])
    ids = np.asarray([x["label_id"] for x in original["objects"]])
    for p, q in zip(centers, transformed):
        ax[1].plot([p[2], q[2]], [p[1], q[1]], color="#bac8cd", lw=0.7, zorder=0)
    ax[1].scatter(centers[:, 2], centers[:, 1], s=18, facecolors="none", edgecolors=GRAY, label="Native centroid")
    ax[1].scatter(
        transformed[:, 2],
        transformed[:, 1],
        c=ids,
        cmap=ListedColormap(colors),
        vmin=0,
        vmax=61,
        s=22,
        label="Mapped centroid",
    )
    ax[1].set(xlabel="x / target x (µm)", ylabel="y / target y (µm)", title="61 identities, an explicit new frame")
    ax[1].legend(frameon=False, fontsize=8, loc="upper left")
    ax[1].set_aspect("equal", adjustable="datalim")
    fig.tight_layout(w_pad=2)
    save(fig, "measurement_story")

    fig, ax = plt.subplots(1, 2, figsize=(10.2, 3.3))
    rows = dev["raster_diagnostics"]
    x = np.arange(3)
    ax[0].bar(
        x - 0.17, [r["median_relative_measure_error"] * 100 for r in rows], 0.32, color=TEAL, label="Median region"
    )
    ax[0].bar(x + 0.17, [r["max_relative_measure_error"] * 100 for r in rows], 0.32, color=GOLD, label="Worst region")
    ax[0].set(
        xticks=x,
        xticklabels=[str(r["target_step_um"]) for r in rows],
        xlabel="Target raster spacing (µm)",
        ylabel="Absolute relative volume error (%)",
        title="Rasterization changes the queried support",
    )
    ax[0].legend(frameon=False, fontsize=8)
    ax[1].bar(x, [r["labels_over_one_percent"] for r in rows], color=[TEAL, GOLD, RED], width=0.5)
    ax[1].set(
        xticks=x,
        xticklabels=[str(r["target_step_um"]) for r in rows],
        xlabel="Target raster spacing (µm)",
        ylabel="Regions exceeding 1% error (of 61)",
        ylim=(0, 64),
        title="Physical-space methods agree",
    )
    ax[1].text(
        0.04,
        0.94,
        "Conventional analytical control = retained instrument\nMaximum centroid difference: 1.42 × 10⁻¹⁴ µm",
        transform=ax[1].transAxes,
        va="top",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "#d6dfe4", "boxstyle": "round,pad=.5"},
    )
    fig.tight_layout(w_pad=2)
    save(fig, "raster_diagnostic")

    econ = json.loads((ROOT / "economics/results/results.json").read_text())
    primary = econ["scenarios"]["primary_zero_gain"]
    routes = ["established", "technical_only", "coordination_only", "combined"]
    values = [primary[r + "/E"]["mean_economic_surplus"] for r in routes]
    fig, ax = plt.subplots(1, 2, figsize=(10.2, 3.7), gridspec_kw={"width_ratios": [1, 1.1]})
    labels = ["Established\nexpert service", "Adapter\nonly", "Coordination\nonly", "Combined"]
    bars = ax[0].bar(np.arange(4), values, color=[TEAL, "#8daeb5", "#8daeb5", "#8daeb5"], width=0.58)
    for bar, v in zip(bars, values):
        ax[0].text(bar.get_x() + bar.get_width() / 2, v + 13, f"{v:.0f}", ha="center", fontsize=9)
    ax[0].set(
        xticks=np.arange(4),
        xticklabels=labels,
        ylabel="Mean simulated economic surplus (CAD)",
        ylim=(0, 750),
        title="Conditional service viability",
    )
    scenarios = [
        "primary_zero_gain",
        "conditional_half_hour_reuse",
        "conditional_one_hour_reuse",
        "false_admission_negative_transfer",
    ]
    delta = [econ["scenarios"][s]["established/paired_increment"]["mean"] for s in scenarios]
    ax[1].barh(np.arange(4), delta, color=[GRAY, GOLD, TEAL, RED], height=0.58)
    ax[1].axvline(0, color=NAVY, lw=0.8)
    ax[1].set(
        yticks=np.arange(4),
        yticklabels=["No gain", "+30 min saved", "+60 min saved", "−30 min / false admission"],
        xlabel="E+ minus E mean simulated surplus (CAD)",
        title="Retention must earn its additional cost",
    )
    ax[1].invert_yaxis()
    ax[1].set_xlim(-155, 60)
    for i, v in enumerate(delta):
        ax[1].text(
            v + (4 if v >= 0 or v < -50 else -4),
            i,
            f"{v:+.2f}",
            ha="left" if v >= 0 or v < -50 else "right",
            va="center",
            fontsize=8,
            color="white" if v < -50 else NAVY,
        )
    fig.tight_layout(w_pad=2.3)
    save(fig, "conditional_economics")

    fig, ax = plt.subplots(figsize=(7.8, 3.5))
    n = np.arange(1, 17)
    threshold = 75 / (65 * n) * 60
    ax.plot(n, threshold, color=TEAL, lw=2.4)
    ax.scatter([2, 4, 8], 75 / (65 * np.array([2, 4, 8])) * 60, color=TEAL, s=45)
    for k in [2, 4, 8]:
        t = 75 / (65 * k) * 60
        ax.annotate(f"{t:.1f} min", (k, t), xytext=(8, 12), textcoords="offset points", fontsize=9)
    ax.set(
        xlabel="Realized eligible reuses",
        ylabel="Avoidable staff minutes saved per reuse",
        xlim=(0.7, 16.4),
        ylim=(0, 82),
        xticks=[1, 2, 4, 6, 8, 10, 12, 14, 16],
        title="The next experiment has a decision threshold",
    )
    ax.text(
        0.97,
        0.9,
        "CAD75 extra assessment + retention + upkeep\nCAD65/hour avoidable cash labor\nAssumptions; no saving measured",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        bbox={"facecolor": "#f0f6f7", "edgecolor": "none", "boxstyle": "round,pad=.6"},
    )
    fig.tight_layout()
    save(fig, "retention_threshold")


if __name__ == "__main__":
    main()
