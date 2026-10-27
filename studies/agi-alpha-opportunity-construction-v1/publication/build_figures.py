# SPDX-License-Identifier: Apache-2.0
"""Generate exact-data, publication figures; no generative imagery or invented points."""

from pathlib import Path
import json
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)
BG = "#170b28"
INK = "#f4effc"
MUTED = "#c8b7de"
PURPLE = "#a983f0"
TEAL = "#61d5c4"
CORAL = "#f29b9b"
GREY = "#43344f"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 15,
        "axes.labelsize": 11,
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "savefig.facecolor": BG,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": "#68547e",
        "grid.color": "#463454",
    }
)


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight", pad_inches=0.22)
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)


def flow():
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.4)
    ax.axis("off")
    boxes = [
        (0.2, 3.35, 2.7, 1.35, "Roster options", "Two employers\nConsenting workers\nProduction quotas"),
        (0.2, 0.6, 2.7, 1.35, "Care offers", "Qualified capacity\nFull commute coverage\nFinite backup"),
        (
            3.6,
            1.95,
            2.8,
            1.5,
            "Joint construction",
            "Enumerate + verify\nAllocate every obligation\nReject infeasible cases",
        ),
        (
            7.05,
            3.35,
            2.7,
            1.35,
            "Funded commitment",
            "Parent and employer caps\nProvider + worker funds\nReserve and refunds",
        ),
        (
            7.05,
            0.6,
            2.7,
            1.35,
            "Reviewable outcome",
            "One complete care cohort\nIndependent checks\nSeparate authority grants",
        ),
    ]
    for x, y, w, h, title, body in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=.12,rounding_size=.12",
                facecolor="#2d1846",
                edgecolor="#78569c",
                linewidth=1.2,
            )
        )
        ax.text(x + 0.14, y + h - 0.17, title, weight="bold", fontsize=12, va="top", color=TEAL if x > 6 else INK)
        ax.text(x + 0.14, y + h - 0.52, body, fontsize=10.7, va="top", linespacing=1.5, color=MUTED)
    for start, end in [
        ((2.98, 3.9), (3.5, 3)),
        ((2.98, 1.35), (3.5, 2.4)),
        ((6.5, 3), (6.95, 3.9)),
        ((6.5, 2.4), (6.95, 1.35)),
    ]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, linewidth=1.6, color=PURPLE))
    ax.text(0.15, 5.1, "Roster flexibility becomes an input to care capacity", fontsize=17, weight="bold")
    ax.text(
        0.15,
        0.1,
        "A commitment instrument, not permission to operate childcare. Synthetic construction; all parties must grant authority separately.",
        fontsize=9,
        color=MUTED,
    )
    save(fig, "01_connected_arrangement")


def origin():
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(2)
    bottom = np.zeros(2)
    parts = [
        ("Primary care", [320, 170], PURPLE),
        ("Standby", [40, 20], "#cbafff"),
        ("Backup reserve", [320, 170], GREY),
        ("Worker changes", [0, 20], TEAL),
        ("Service fee", [25, 25], "#f0d48b"),
    ]
    for label, vals, color in parts:
        bars = ax.bar(x, vals, bottom=bottom, width=0.52, label=label, color=color, edgecolor=BG, linewidth=1.5)
        if label == "Backup reserve":
            for bar in bars:
                bar.set_hatch("///")
                bar.set_edgecolor("#aa96be")
        for i, v in enumerate(vals):
            if v >= 35:
                ax.text(
                    i,
                    bottom[i] + v / 2,
                    f"{v}",
                    ha="center",
                    va="center",
                    fontsize=12,
                    color=BG if label == "Primary care" else INK,
                    weight="bold",
                )
        bottom += vals
    ax.axhline(450, color=CORAL, linestyle="--", linewidth=1.5)
    ax.text(1.3, 458, "CAD450 total\npayer ceilings", color=CORAL, fontsize=10, va="bottom")
    for i, v in enumerate(bottom):
        ax.text(i, v + 15, f"CAD{v:.0f}", ha="center", fontsize=17, weight="bold")
    ax.set_xticks(x, ["Fixed work rosters\nComplete but underfunded", "Joint permitted rosters\nComplete and fundable"])
    ax.set_ylim(0, 810)
    ax.set_xlim(-0.6, 1.85)
    ax.set_ylabel("Maximum daily commitment (CAD)")
    ax.set_title("The same purpose, a different feasible arrangement", loc="left", pad=18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    fig.text(
        0.125,
        0.005,
        "CAD300 lower commitment = CAD150 lower normal spending + CAD150 less refundable reserve. No service revenue is earned in this experiment.",
        color=MUTED,
        fontsize=9,
    )
    save(fig, "02_origin_funding")


def boundary():
    d = json.loads((ROOT / "technical/boundary_summary.json").read_text())
    xs = [80, 145, 210, 275]
    ys = [80, 150, 220, 290]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.5), sharey=True)
    for ax, mode, title in zip(
        axes, ["locked", "employer_A_only", "both_employers"], ["No roster flexibility", "Employer A only", "Both employers"]
    ):
        matrix = np.zeros((4, 4))
        for row in d["cases"]:
            g = row["case_generation"]
            if (
                g.get("kind") != "prospectively_frozen_followup_grid"
                or g["roster_permissions"] != mode
                or not g["backup_available"]
            ):
                continue
            a = ys.index(g["fixed_opening_quote_cents"] // 100)
            b = xs.index(g["employer_ceiling_cents"] // 100)
            matrix[a, b] = (
                2 if row["new_complete_package_vs_fixed"] else 1 if row["statuses"]["combined"] == "offered" else 0
            )
        ax.imshow(matrix, cmap=ListedColormap([GREY, PURPLE, TEAL]), vmin=0, vmax=2, origin="lower", aspect="auto")
        for i in range(4):
            for j in range(4):
                ax.text(
                    j,
                    i,
                    ["×", "●", "+"][int(matrix[i, j])],
                    ha="center",
                    va="center",
                    fontsize=18,
                    color=INK if matrix[i, j] == 0 else BG,
                )
        ax.set_xticks(range(4), xs)
        ax.set_yticks(range(4), ys)
        ax.set_title(title, fontsize=12)
        ax.set_xlabel("Each employer ceiling / day (CAD)")
    axes[0].set_ylabel("Fixed opening cost per block (CAD)")
    fig.suptitle("A feasible region, not a market-frequency estimate", x=0.06, ha="left", fontsize=17, weight="bold")
    fig.text(
        0.06,
        0.015,
        "× Refused     ● Already feasible with fixed rosters     + Newly feasible with joint rosters. All 16 backup-withdrawn controls refuse.",
        fontsize=10,
        color=MUTED,
    )
    fig.tight_layout(rect=[0, 0.08, 1, 0.91])
    save(fig, "03_feasible_region")


def commercial():
    d = json.loads((ROOT / "economics_v2/COMMERCIAL_RESULT.json").read_text())
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, gridspec_kw={"height_ratios": [2.1, 1]})
    rows = d["policy_family_confirmation"]
    for defer, color, label in [(0, PURPLE, "All at acceptance"), (0.5, TEAL, "Half at acceptance, half at 30 days")]:
        rr = [x for x in rows if x["policy"]["deferred_fraction"] == defer]
        prices = [x["policy"]["price_cad"] for x in rr]
        means = [x["means"]["operating_profit_cad"] for x in rr]
        axes[0].plot(prices, means, "o-", color=color, label=label, linewidth=2)
        axes[1].plot(prices, [x["means"]["accepted"] for x in rr], "o-", color=color, linewidth=2)
    rr = [x for x in rows if x["policy"]["deferred_fraction"] == 0.5]
    axes[0].fill_between(
        [x["policy"]["price_cad"] for x in rr],
        [x["profit_p05_cad"] for x in rr],
        [x["profit_p95_cad"] for x in rr],
        alpha=0.13,
        color=TEAL,
        label="5th–95th world percentiles, half deferred",
    )
    axes[0].axhline(0, color=MUTED, linewidth=0.8)
    axes[0].set_ylabel("Annual operating profit (CAD)")
    axes[0].set_title("Price changes participation, volume and available cash", loc="left", pad=17)
    axes[0].legend(frameon=False, fontsize=9, loc="upper right")
    axes[1].set_ylabel("Accepted packages")
    axes[1].set_xlabel("20-day coordination package service fee (CAD)")
    axes[1].set_xticks([250, 500, 750, 1000, 1250, 1500])
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.35)
    fig.text(
        0.12,
        0.005,
        "Fresh 1,800 simulated worlds; selected policy frozen before evaluation. Provider/worker funding is separate. These are conditional modeled outcomes.",
        fontsize=9,
        color=MUTED,
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    save(fig, "04_price_and_participation")


def sensitivity():
    d = {r["name"]: r for r in json.loads((ROOT / "economics_v2/SENSITIVITY.json").read_text())}
    broad = json.loads((ROOT / "economics_v2/BROAD_UNCERTAINTY.json").read_text())
    pairs = [
        ("Central low-provider-cost scenario", d["central"]),
        ("Broad uncertainty prior", broad),
        ("4 qualified leads / month", d["leads4"]),
        ("8 qualified leads / month", d["leads8"]),
        ("Acquisition CAD60 / lead", d["acquisition60"]),
        ("Half employer value", d["half_value"]),
        ("40% technical eligibility", d["eligibility40"]),
        ("75% semantic acceptance", d["quality75"]),
        ("Triple complete delivery cost", d["cost3x"]),
        ("15% provider absence", d["backup15"]),
    ]
    fig, ax = plt.subplots(figsize=(10, 6))
    yy = np.arange(len(pairs))
    v = [x[1]["means"]["operating_profit_cad"] for x in pairs]
    ax.barh(yy, v, color=[TEAL if x > 0 else CORAL for x in v], height=0.58)
    for y, x in zip(yy, v):
        ax.text(x + (90 if x > 0 else -90), y, f"{x:+,.0f}", va="center", ha="left" if x > 0 else "right", fontsize=10)
    ax.set_yticks(yy, [x[0] for x in pairs])
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, linewidth=0.8)
    ax.set_xlim(-3100, 6500)
    ax.set_xlabel("Mean annual operating profit (CAD)")
    ax.set_title("The commercial condition is narrow and inspectable", loc="left", pad=18)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(
        0.12,
        0.005,
        "Policy remains CAD750, half deferred. Except the broad prior, one assumption changes at a time on paired worlds. Actual collections: CAD0.",
        fontsize=9,
        color=MUTED,
    )
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    save(fig, "05_commercial_sensitivity")


if __name__ == "__main__":
    flow()
    origin()
    boundary()
    commercial()
    sensitivity()
