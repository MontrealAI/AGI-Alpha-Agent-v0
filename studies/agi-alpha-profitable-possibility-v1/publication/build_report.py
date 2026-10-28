# SPDX-License-Identifier: Apache-2.0
"""Regenerate manuscript inputs and vector figures from retained evidence.

This script performs no confirmation experiment and does not alter frozen methods.
Run from any working directory. Requires matplotlib and numpy for figures only.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

PUBLICATION = Path(__file__).resolve().parent
ROOT = PUBLICATION.parent
FIGURES = PUBLICATION / "figures"
FIGURES.mkdir(exist_ok=True)
INK, TEAL, AMBER, PALE, MUTED = "#102824", "#166D61", "#B96C2E", "#F5F3EC", "#52665F"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
    "axes.spines.right": False, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": "#B8C6BF",
    "savefig.facecolor": "white", "pdf.fonttype": 42, "axes.titleweight": "bold",
})


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text())


def successor_section() -> None:
    records = read_json("results/confirmation_v2/successor.json")
    fig, axes = plt.subplots(1, 2, figsize=(6.7, 2.9), constrained_layout=True)
    for ax, record in zip(axes, records):
        n = len(record["problem"]["cols"])
        parts = [record["asset_read_parse_seconds"], record["asset_validation_seconds"],
                 record["inherited_query_seconds"]]
        for value, bottom, color, label in zip(
            parts, [0, parts[0], parts[0] + parts[1]],
            ["#86B6AA", TEAL, AMBER], ["Read + parse", "Validate", "Evaluate"]
        ):
            ax.bar(0, value, bottom=bottom, width=.54, color=color, label=label)
        ax.bar(1, record["direct_all_statistics_seconds"], width=.54,
               color=INK, label="Fresh conventional")
        ax.set_xticks([0, 1], ["Cold inheritance", "Fresh construction"])
        ax.set_ylabel("Elapsed seconds")
        ax.set_title(f"4 × {n} capacity world", loc="left")
        ymax = max(record["cold_inherited_query_seconds"], record["direct_all_statistics_seconds"])
        ax.set_ylim(0, ymax * 1.24)
        for x, value in enumerate([record["cold_inherited_query_seconds"],
                                   record["direct_all_statistics_seconds"]]):
            ax.text(x, value + ymax * .04, f"{value:.3f}s", ha="center", fontsize=10)
        ax.grid(axis="y", alpha=.15)
        ax.set_axisbelow(True)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, loc="outside lower center", frameon=False,
               fontsize=8)
    fig.savefig(FIGURES / "successor_transfer.pdf", bbox_inches="tight")
    plt.close(fig)

    rows = []
    for record in records:
        n = len(record["problem"]["cols"])
        targets = {x["target"]: x for x in record["targets"]}
        rows.append(
            f"$4\\times {n}$ & {int(record['predecessor_count']):,} & "
            f"{record['inherited_query_seconds']:.4f} & "
            f"{record['cold_inherited_query_seconds']:.4f} & "
            f"{record['direct_all_statistics_seconds']:.4f} & "
            f"{targets[0]['direct_reference_seconds']:.4f} \\\\"
        )
    counts = []
    for record in records:
        n = len(record["problem"]["cols"])
        for target in record["targets"]:
            counts.append(
                f"$4\\times {n}$ & {target['target']} & {int(target['count']):,} & "
                f"{target['conditional_generation_seconds']:.4f} & "
                f"{target['accepted']} \\\\"
            )
    text = r"""\subsection{Measured successor results}
The two successor problems have 14 and 18 columns, distinct from the 8, 12, 16,
and 20-column performance problems. They follow the same synthetic construction
family; they do not establish transfer to a new industrial domain. Both exact
concentration distributions agree with the independently implemented conventional
semiring dynamic program.

\begin{table}[htbp]
\centering\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lrrrrr@{}}
\toprule
Problem & Fiber size & Warm & Cold & Fresh, all $K$ & Fresh, $K=0$\\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\caption{Executed successor count queries; times are local seconds. Warm evaluates
the retained graph. Cold adds read, parse, and validation. Fresh all-$K$ computes
the same complete distribution from the request. Fresh $K=0$ computes only that
target, using the binary-cap equivalence. The target column is a different,
narrower contract, not an all-statistics speed comparison.}
\label{tab:successor}
\end{table}

\begin{figure}[htbp]
\centering
\includegraphics[width=\linewidth]{figures/successor_transfer.pdf}
\caption{Inheritance is useful in memory, but cold validation dominates these
transfers. Fresh conventional construction is faster for the same all-statistics
query on both held-out sizes. Predecessor construction and export are excluded
from these bars and reported separately below; adding them further increases
the full life-cycle cost of inheritance.}
\label{fig:successor}
\end{figure}

The 14-column asset has 504 states and 12,245 edges; the 18-column asset has
1,316 states and 76,943 edges. Their serialized JSON sizes are 1,339,844 and
8,512,360 bytes, compressed to 87,169 and 577,818 bytes. Predecessor construction
takes 0.1238 and 0.9237 seconds; export takes a further 0.1885 and 1.1112 seconds.
These costs are paid before the cold-query measurements. The complete construction,
export, and cold-query paths therefore take approximately 0.5954 and 4.2917 seconds.
No remote-network transfer or multi-year storage cost was measured.

\begin{table}[htbp]
\centering\small
\begin{tabular}{@{}lrrrr@{}}
\toprule
Problem & $K$ & Exact conditioned count & Generation seconds & Accepted tables\\
\midrule
""" + "\n".join(counts) + r"""
\bottomrule
\end{tabular}
\caption{Fresh conditioned outputs generated from the inherited instrument.
Generation time is additional to obtaining the distribution and loading the asset.
Each of the 400 saved tables passes the original margins, caps, and requested
concentration check. These are computational acceptances, not customer acceptances.}
\end{table}

At 18 columns, only about $1.43\times10^{-5}$ of the uniform fiber has $K=0$.
That makes blind rejection unattractive, but the exact binary-cap simplification
computes its count in 0.0085 seconds. The separate target-specific comparator
measures counting, not generation of 100 outputs; no sample-generation speedup
over that comparator is asserted. The all-statistics comparison has the same
output contract on both sides.

The equal-inheritance control gives a conventional caller the same code and
artifact and obtains identical seeded conditioned outputs (20 at $K=1$ per
problem). This is an asset-availability control, not a second independent
implementation. It rejects exclusive ownership of the reuse benefit. The
independent full-distribution implementation supplies the separate numerical
correctness challenge.

\begin{evidencebox}
\textbf{Successor disposition.} Four hundred accepted conditioned worlds are
new outputs, and the instrument supplies a working productive inheritance.
The measured cold cost exceeds fresh conventional construction in both cases,
and conventional access to the same asset matches the result. Superior
transferred capability, an AI-specific advantage, and economically self-financing
succession are not established.
\end{evidencebox}
"""
    (PUBLICATION / "generated_successor.tex").write_text(text)


def instrument_figure() -> None:
    tables = read_json("results/delivery_example/tables.json")
    request = read_json("examples/capacity_4x8.json")
    caps = np.asarray(request["caps"])
    fig, axes = plt.subplots(1, 4, figsize=(6.7, 1.8), constrained_layout=True)
    cmap = ListedColormap(["#F5F3EC", "#86B6AA", "#166D61"])
    for k, (ax, table) in enumerate(zip(axes, tables)):
        array = np.array(table)
        ax.imshow(array, cmap=cmap, vmin=0, vmax=2, aspect="equal")
        for i in range(array.shape[0]):
            for j in range(array.shape[1]):
                if caps[i, j] == 0:
                    ax.text(j, i, "×", ha="center", va="center", color="#9EABA5", fontsize=9)
                else:
                    ax.text(j, i, str(array[i, j]), ha="center", va="center",
                            color="white" if array[i, j] == 2 else INK, fontsize=8)
        ax.set_title(f"Delivered table {k + 1}", loc="left", fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.savefig(FIGURES / "instrument_worlds.pdf", bbox_inches="tight")
    plt.close(fig)


def auxiliary_inputs() -> None:
    summary = read_json("results/confirmation_v2/scientific_summary.json")
    (PUBLICATION / "generated_macros.tex").write_text(
        "% Generated by build_report.py from frozen confirmation_v2 results.\n"
        f"\\newcommand{{\\SmallCases}}{{{summary['small']['cases']}}}\n"
        f"\\newcommand{{\\Bijections}}{{{summary['small']['exhaustive_bijections']}}}\n"
        f"\\newcommand{{\\PerformanceCases}}{{{len(summary['performance'])}}}\n"
    )
    text = r"""All paths below are relative to
\path{studies/agi-alpha-profitable-possibility-v1/} in the pinned repository.
The standalone package preserves this study's directory layout.

\begin{longtable}{@{}P{0.37\linewidth}P{0.57\linewidth}@{}}
\toprule
Artifact & Purpose and boundary\\
\midrule
\endhead
\path{kernel.py}; \path{examples/} & Executable bounded count, rank, generation,
serialization, and successor operations. Core requires standard Python only.\\
\path{independent_reference.py}; \path{vendor/} & Independently written cell and
orbit comparators, original-author binary source, license, and provenance.\\
\path{configs/}; \path{archive/science_v1/} & Frozen protocols and source bytes
for the incomplete initial campaign. The completed v2 hashes bind current methods.\\
\path{results/confirmation_v2/} & Exact confirmation inputs, results, timings,
compressed inherited instruments, and 400 conditioned output tables.\\
\path{results/delivery_example/} & A separate complete 1,000-table delivery,
portable instrument, zero-revenue receipt, and independent cell acceptance record.\\
\path{results/browser_acceptance.json} & Chromium execution, responsive and
bilingual checks, downloads, finite-case bijections, and final copy-check chronology.\\
\path{economy.py}; \path{economics/} & Stateful simulated commerce; frozen
source/configuration, per-world summaries, monthly cent ledgers, decisions,
sensitivity, Decimal audits, and preserved errata.\\
\path{alternatives/} & Actual matrix-function outputs and prior-art challenge;
post-confirmation row-order diagnostic including the full charged search.\\
\path{product/index.html} & Standalone English/French local product; live
computation and exports, no external resources, real checkout, or hosting dependency.\\
\path{claim_register.json}; \path{opportunity_frontier.json} & Claim-to-evidence
map and budget-relative task ledger. Unestablished proofs remain unestablished.\\
\path{nova_seed.json}; \path{fusion_plan.json} & Exploratory candidate record
and completed execution record; neither grants launch or financial authority.\\
\path{research/}; \path{environment.json} & Verified source catalogue and
environment metadata. Timings are observations, not portable guarantees.\\
\path{publication/} & Complete LaTeX, generated section inputs, vector figures,
generation scripts, and compiled PDF.\\
\path{README.md}; \path{MANIFEST.sha256} & Full reproduction commands and
file digests. The manifest excludes itself and transient build caches.\\
\bottomrule
\end{longtable}

The original confirmation ledgers are retained without replacing their values.
The independent Decimal audit correction changes the performed-check counter,
not the economic histories. Reproduction must use a new output directory.
The original scientific protocol intentionally refuses execution against revised
method hashes; its archived source is supplied for inspection.

The core sampler, scientific harness, and economic simulation use the Python
standard library. Figure generation uses NumPy and Matplotlib; the alternative
matrix probe also uses SciPy. Browser automation uses Playwright and Chromium.
Opening the standalone HTML requires none of those build dependencies. The PDF
uses XeLaTeX with Nimbus Roman, Nimbus Sans, and DejaVu Sans Mono, with standard
TeX packages declared in the source. The environment record supplies the tested
versions without claiming that other versions are equivalent.
"""
    (PUBLICATION / "generated_artifacts.tex").write_text(text)


def main() -> None:
    successor_section()
    instrument_figure()
    auxiliary_inputs()
    print("Generated successor section, artifact map, macros, and two vector figures.")


if __name__ == "__main__":
    main()
