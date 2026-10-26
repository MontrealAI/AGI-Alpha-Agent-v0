# SPDX-License-Identifier: Apache-2.0
"""Render descriptive evidence from immutable observed receipts; no new experiments."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def read(name: str) -> Any:
    return json.loads((ROOT / name).read_text())


def write(name: str, text: str) -> None:
    (PAPER / name).write_text(text.strip() + "\n")


def main() -> None:
    campaign = read("outputs/primary/campaign.json")
    calibration = read("outputs/primary/calibration.json")
    gtfs = read("discovery/gtfs/output/release-packet.json")
    rows = []
    for item in campaign["records"]:
        if item["arm"] == "B":
            pair = " $\\rightarrow$ ".join(item["pair"])
            if item["accepted"]:
                a = item["acceptance"]
                rows.append(
                    f"{pair} & {a['oldNodes']:,} / {a['newNodes']:,} & " f"{a['changes']:,} & 4 / 4 scoped pass \\\\"
                )
            else:
                rows.append(f"{pair} & -- & -- & Source path 404; 0 / 4 delivered \\\\")
    write(
        "delivery-results.tex",
        r"""
\begin{table}[htbp]\small
\caption{All six locked API questions, including blocked deliveries. Counts are structural facts, not customer incidents.}
\begin{tabularx}{\linewidth}{@{}p{0.28\linewidth}p{0.18\linewidth}p{0.12\linewidth}Y@{}}
\toprule Question & Old / new nodes & Changes & Four-arm disposition\\ \midrule
"""
        + "\n".join(rows)
        + r"""
\bottomrule\end{tabularx}
\end{table}

The primary delivered three distinct dossiers, accepted in all four arms: 12 accepted arm/question
outputs out of 24 planned. Three other questions were blocked by two locked source-path 404s.
On available inputs, conditional technical acceptance was 12/12. The intent-to-deliver fraction
was 12/24. These denominators answer different questions and are both retained.

The REM packet covers 26 October--1 November 2026, in GTFS local service dates. Its original
feed version is 20260520, with declared coverage through 31 December 2026. It contains three
routes, 1,081 trip templates and 19,069 stop-time rows. The supported calendar expansion yields
443 scheduled trip instances on each weekday, 323 on Saturday and 315 on Sunday: 2,853 in
total. There are 21 route/date cells and seven daily groups in one delivery.

The canonical MobilityData validator 8.0.1 reports zero errors, 1,565 warnings and one informational
notice. Eighty-six independent SQLite reconciliation checks pass. The disposition is
\textbf{SCOPED STRUCTURAL PASS}, with warnings retained for interpretation. This permits
structural ingestion of the supplied snapshot within the declared scope; it does not certify
real-time service or independently verify the timetable against actual operations.
The external Java/Python stages and actual Workbench aggregation have 21.558 measured command
wall seconds and 23.718 CPU seconds in total, excluding unmetered authoring and attention.
The Workbench aggregation command contributes 0.115 wall seconds and 0.123 CPU seconds.
""",
    )
    cpu_rows = []
    labels = {
        "A": "Retained conventional",
        "B": "Workbench full",
        "C": "Incremental registry",
        "D": "Incremental graph",
    }
    for arm in "ABCD":
        a = calibration["arms"][arm]
        cpu_rows.append(
            f"{arm}: {labels[arm]} & {a['accepted']} / {a['cases']} & "
            f"{a['totalCpuSecondsIncludingFailures']:.6f} & "
            f"{a['cpuSecondsPerAcceptedIncludingFailures']:.6f} \\\\"
        )
    write(
        "comparison-results.tex",
        r"""
\begin{table}[htbp]\small
\caption{Primary executed service resources. Includes production, independent verification and packaging; shared retrieval is reported separately.}
\begin{tabularx}{\linewidth}{@{}Yrrr@{}}
\toprule Arm & Accepted / planned & Total CPU s & CPU s / accepted\\ \midrule
"""
        + "\n".join(cpu_rows)
        + rf"""
\bottomrule\end{{tabularx}}
\end{{table}}

The complete primary campaign used {campaign['cpuSeconds']:.6f} CPU seconds and
{campaign['wallSeconds']:.6f} elapsed seconds. Its driver overhead was
{campaign['driverOverheadCpuSeconds']:.6f} CPU seconds, allocated separately from the table.
The all-input acquisition session used 4.806423 CPU seconds and 7.387453 elapsed seconds.
Source availability, normalized bytes, licenses and failed URLs are preserved in the input manifest.
"""
        + r"""

\begin{figure}[htbp]\centering
\includegraphics[width=0.9\linewidth]{figures/primary-cpu.pdf}
\caption{Each dot is one accepted primary question; bars are their mean. Complete compared delivery
includes independent verification and packaging. Three blocked questions per arm remain in the
intent-to-deliver denominator but do not become zero-duration successful jobs. One pass per case
does not establish a latency distribution. Shared acquisition and research costs are separate.}
\end{figure}

All four arms agree on the exact changed fact tuples and source provenance. The conventional
builder is faster in every available primary question. Incremental reuse does not improve the
primary average over the full Workbench index. The graph mean is slightly below the registry mean
in this single run, but it creates no additional accepted work and supplies no independently
identified planning advantage. Both remain slower than the conventional builder.

The public-tool supplement strengthens the alternative. After validated Swagger2-to-OpenAPI
conversion, oasdiff 1.34.1 reports 102, 5 and 0 breaking findings and 365, 9 and 77 changelog
items on the three available pairs. Its broader request/response/media coverage is not the same
acceptance task as the structural dossier. Raw Swagger2 supplied to the OpenAPI3 validation contract produced 15, 1 and 0
findings despite 103--105 validation errors; default exit zero therefore did not establish a
valid result. A YAML parser failure on v20 was preserved, then a separately labeled follow-up
used the existing frozen normalized JSON. All 27 supplemental commands, including invalid and
failed attempts, used 6.280 seconds wall and 8.923 CPU seconds. No primary producer was rerun.
""",
    )
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )
    fig, ax = plt.subplots(figsize=(7.6, 3.3), layout="constrained")
    colors = ["#283f69", "#7564b6", "#b68b43", "#428e8d"]
    means = []
    for i, arm in enumerate("ABCD"):
        values = [r["cpuSeconds"] for r in campaign["records"] if r["arm"] == arm and r["accepted"]]
        mean = sum(values) / len(values)
        means.append(mean)
        ax.bar(i, mean, color=colors[i], alpha=0.85, width=0.6)
        ax.scatter([i - 0.12, i, i + 0.12], values, color="#17213b", s=25, zorder=3)
        ax.text(i, max(values) + 0.09, f"{mean:.3f}", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(range(4), ["A\nConventional", "B\nFull index", "C\nRegistry", "D\nGraph"])
    ax.set_ylabel("CPU seconds per accepted question")
    ax.set_ylim(0, max(means) * 1.35)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    (PAPER / "figures").mkdir(exist_ok=True)
    fig.savefig(PAPER / "figures/primary-cpu.pdf")
    fig.savefig(PAPER / "figures/primary-cpu.png", dpi=180)
    plt.close(fig)
    observed = {
        "primary": calibration,
        "gtfsTotalScheduledTripInstances": sum(x["scheduled_trips"] for x in gtfs["daily_service"]),
        "sourceQualification": campaign["sourceQualification"],
        "primaryCpuSeconds": campaign["cpuSeconds"],
        "primaryWallSeconds": campaign["wallSeconds"],
        "actualCollectionsUsd": 0,
        "actualFullCostUsd": None,
        "humanOnlyDurationObserved": False,
    }
    (PAPER / "observed-summary.json").write_text(json.dumps(observed, indent=2) + "\n")


if __name__ == "__main__":
    main()
