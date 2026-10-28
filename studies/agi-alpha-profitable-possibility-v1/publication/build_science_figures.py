# SPDX-License-Identifier: Apache-2.0
"""Render scientific publication inputs from preserved measurements only.

This builder runs no counting, sampling, matrix-action, or timing experiment.
It reads the frozen confirmation and the separately preserved diagnostics.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "agi-alpha-science-matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

PUBLICATION = Path(__file__).resolve().parent
STUDY = PUBLICATION.parent
CONFIRMATION = STUDY / "results" / "confirmation_v2"
FIGURES = PUBLICATION / "figures"
INK = "#102824"
TEAL = "#166D61"
AMBER = "#B96C2E"
MUTED = "#52665F"
GRID = "#DBE2DE"
PAPER = "#F5F3EC"


def read_json(path: Path) -> Any:
    """Read a retained scientific evidence file without modifying it."""
    return json.loads(path.read_text())


def style() -> None:
    """Use the paper's restrained palette and vector text."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.labelcolor": INK, "axes.edgecolor": GRID,
        "text.color": INK, "xtick.color": MUTED, "ytick.color": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.titleweight": "bold",
        "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.facecolor": "white", "axes.facecolor": "white",
    })


def save_vector(fig: Any, filename: str) -> None:
    """Write a reproducible vector PDF and release the figure."""
    fig.savefig(FIGURES / filename, bbox_inches="tight", pad_inches=0.08,
                metadata={"Creator": "AGI ALPHA scientific evidence builder",
                          "CreationDate": None, "ModDate": None})
    plt.close(fig)


def performance_figure(performance: list[dict[str, Any]]) -> None:
    """Plot every frozen larger case, keeping the timeout visibly censored."""
    fig, ax = plt.subplots(figsize=(7.0, 4.15))
    fig.subplots_adjust(left=0.20, right=0.96, bottom=0.15, top=0.83)
    for i, record in enumerate(performance):
        y = len(performance) - 1 - i
        compiler = record["methods"]["compiler"]["seconds"]
        reference = record["methods"]["orbit"]
        complete = reference["status"] == "complete"
        conventional = reference["seconds"]
        ax.plot([compiler, conventional], [y, y], color=GRID, linewidth=1.5,
                linestyle="-" if complete else "--", zorder=1)
        ax.scatter(compiler, y + 0.10, color=TEAL, s=31, zorder=4)
        ax.scatter(conventional, y - 0.10, color=AMBER, s=37,
                   marker="D" if complete else ">", zorder=4)
        if not complete:
            ax.annotate("30 s timeout", (conventional, y - 0.10), xytext=(-7, 9),
                        textcoords="offset points", ha="right", va="bottom", color=AMBER, fontsize=8)
    for border in (2.5, 5.5, 8.5):
        ax.axhline(border, color=GRID, linewidth=0.65)
    labels = [f"{r['problem']['name'].split('_')[1]} columns / v{r['problem']['name'][-1]}"
              for r in performance]
    ax.set_yticks(range(len(performance)), labels=list(reversed(labels)))
    ax.tick_params(axis="y", length=0, pad=8)
    ax.set_xscale("log")
    ax.set_xlim(0.004, 60)
    ax.set_ylim(-0.85, 11.65)
    ax.set_xticks([0.01, 0.1, 1, 10])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:g}"))
    ax.set_xlabel("Elapsed seconds (logarithmic scale)", labelpad=8)
    ax.grid(axis="x", color=GRID, linewidth=0.65, zorder=0)
    fig.suptitle("Frozen larger-case construction and count times", x=0.02,
                 y=1.01, ha="left", fontsize=12, fontweight="bold")
    handles = [Line2D([], [], marker="o", color=TEAL, linestyle="", label="Compiler: graph construction"),
               Line2D([], [], marker="D", color=AMBER, linestyle="", label="Conventional DP: count")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.025, 1.02),
              ncol=2, frameon=False, fontsize=8.3, handletextpad=0.4, columnspacing=1.2)
    save_vector(fig, "scientific_performance.pdf")


def challenge_figure(ordering: dict[str, Any], assessment: dict[str, Any]) -> None:
    """Show the search cost and the second candidate's stronger comparison."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.0, 2.72),
                                     gridspec_kw={"width_ratios": [1.0, 1.05]})
    fig.subplots_adjust(left=0.16, right=0.98, bottom=0.22, top=0.78, wspace=0.85)
    summary = ordering["summary"]
    times = [summary["compiler_confirmation_seconds"], summary["best_execution"]["seconds"],
             summary["original_conventional_confirmation_status"]["seconds"],
             summary["total_search_wall_seconds"]]
    labels = ["Compiler", "Best order", "Reference*", "All 24 orders"]
    colors = [TEAL, AMBER, "#D5B99E", MUTED]
    for i, (value, color) in enumerate(zip(times, colors)):
        y = 3-i
        left.plot([0.8, value], [y, y], color=color, linewidth=6, solid_capstyle="butt")
        left.scatter(value, y, color=color, marker=">" if i == 2 else "o", s=23, zorder=3)
        label = f"{value:.2f}" + ("*" if i == 2 else "")
        left.annotate(label, (value, y), xytext=(5, 0), textcoords="offset points",
                      va="center", fontsize=8, color=INK)
    left.set_yticks(range(4), labels=list(reversed(labels)))
    left.tick_params(axis="y", length=0, pad=5)
    left.set_xscale("log")
    left.set_xlim(0.8, 160)
    left.set_ylim(-0.6, 3.6)
    left.set_xticks([1, 10, 100], labels=["1", "10", "100"])
    left.set_xlabel("Seconds; different cost scopes", fontsize=8.2)
    left.grid(axis="x", color=GRID, linewidth=0.65)
    left.set_title("Ordering challenge", loc="left", fontsize=10.5, pad=20)
    left.text(0, 1.03, "*Timeout; search cost is fully charged", transform=left.transAxes,
              color=MUTED, fontsize=7.5)
    portfolio = assessment["strong_conventional_portfolio"]
    values = [portfolio["candidate_degree_wins"], portfolio["candidate_degree_ties"],
              portfolio["candidate_degree_losses"]]
    for i, (value, color) in enumerate(zip(values, [TEAL, "#A7BBB4", AMBER])):
        y = 2-i
        right.barh(y, value, color=color, height=0.52)
        right.text(value+3, y, str(value), va="center", fontsize=9, fontweight="bold")
    right.set_yticks([0, 1, 2], labels=["More products", "Same products", "Fewer products"])
    right.tick_params(axis="y", length=0, pad=5)
    right.set_xlim(0, 110)
    right.set_ylim(-0.55, 2.55)
    right.set_xticks([0, 50, 100])
    right.set_xlabel("Cases versus conventional portfolio", fontsize=8.2)
    right.grid(axis="x", color=GRID, linewidth=0.65)
    right.set_axisbelow(True)
    right.set_title("Matrix-action alternative", loc="left", fontsize=10.5, pad=20)
    right.text(0, 1.03, "144 cases; lower product count is better", transform=right.transAxes,
               color=MUTED, fontsize=7.5)
    save_vector(fig, "scientific_challenges.pdf")


TEX_TEMPLATE = r"""% SPDX-License-Identifier: Apache-2.0
% Generated by publication/build_science_figures.py; no experiments are run.
% Frozen inputs: results/confirmation_v2/{confirmation,performance,published_comparator}.json
% Post-confirmation inputs: alternatives/ordering/ordering_results.json
% Alternative inputs: alternatives/matrix_action/matrix_probe_{results,assessment}.json
% External sources: cite keys miller, exact, lorist, davidson, openaiMatrix.
\subsection{Exact agreement and accepted production}

The corrected confirmation completed \textbf{@SMALL@ tiny instances}, including
\textbf{@BIJECTIONS@ exhaustive table bijections} and \textbf{@CONDITIONED@ conditioned-output checks}.
Every tiny-instance count agreed with the independent enumerator. Enumerated feasible
tables were compared with the compiler's entire ranked family, including rank/unrank
inverses. These are finite exhaustive checks on the declared cases; they do not replace
the argument that multiplicity-weighted decoding samples the intended labeled law.

The larger campaign completed \textbf{@LARGE@ synthetic requests} and delivered
\textbf{@OUTPUTS@ accepted tables}: 100 independently cell-checked outputs per request.
Construction took @MINSECONDS@--@MAXSECONDS@ seconds in the recorded executions.
The strongest independently written conventional counter completed @CORROBORATED@ of
the @LARGE@ cases during confirmation, with matching counts in each. Its last case
timed out. The remaining count was corroborated only in the subsequent ordering
diagnostic described below; it is not retroactively counted as an independent result
of the frozen confirmation.

\begin{figure}[H]
\centering
\includegraphics[width=\linewidth]{figures/scientific_performance.pdf}
\caption{All twelve larger cases from the corrected frozen campaign. Variants change
the margins and, for v2, add forbidden cells. Circles measure graph construction;
diamonds measure independent conventional counting. The right-pointing marker is a
30-second timeout, not a completed count. These are single executions, not repeated
performance estimates. Source: the frozen \texttt{performance.json} record.}
\label{fig:scientific-performance}
\end{figure}

\begin{table}[H]
\centering\small
\begin{tabular}{@{}rrrrr@{}}
\toprule
Columns & Exact labeled tables & Graph states & Compiler (s) & Conventional (s)\\
\midrule
@TABLE_ROWS@
\bottomrule
\end{tabular}
\caption{The four regular v0 controls, with four rows and column totals of two.
Both symmetry-aware implementations return the displayed counts. Large family size
is an output property; it does not by itself demonstrate algorithmic novelty.}
\label{tab:scientific-regular}
\end{table}

The simpler labeled-cell counter completed the three eight-column cases and reached
its state budget on the other nine. This comparison supports the usefulness of
column symmetry on these inputs. The independent orbit counter uses the same known
structural principle and is the more consequential conventional comparison.

\subsection{A published counterexample and a charged ordering repair}

The published $13\times17$ Darwin-finch binary-margin problem provides an external
check on the scope of the implementation. The authors' actual EXACT source, with
documented Python-3 compatibility edits, returned
\(67\,149\,106\,137\,567\,626\) in \textbf{@AUTHOR_SECONDS@ seconds}.
The new bounded compiler refused at its declared state/transition budget after
@REFUSAL_SECONDS@ seconds. This is a successful conventional computation on a task
the constructed implementation did not complete. The published software's binary
scope is respected; unsupported arbitrary-cap tasks are not scored as incorrect
outputs~\cite{miller,exact}.

The final larger confirmation case initially appeared more favorable: the compiler
completed construction in @ORPHAN_COMPILER@ seconds while the conventional reference
timed out at 30 seconds. A separate post-confirmation challenge copied that reference
and changed only its row-order parameter. All 24 row permutations received the same
3.5-second execution budget. Eight finished, all returning
\(37\,877\,767\,916\); sixteen timed out. The best order took
\textbf{@BEST_ORDER@ seconds}, and the ascending-row-sum permutation took @ASCENDING@ seconds.
Thus an ordinary ordering change reaches the compiler's recorded construction scale
on this observed case, without a new recurrence or pruning rule.

The entire diagnostic cost \textbf{@SEARCH_COST@ seconds}, including unsuccessful
attempts. That search cost cannot be replaced by the winning attempt's runtime in a
first-use comparison. No general ordering policy was selected, and this adaptation
is not a fresh held-out result. The comparator returns a count; the compiler also
constructs a reusable transition graph. The small timing differences therefore do
not establish robust superiority in either direction.

\subsection{A second production route, executed and rejected}

The investigation also constructed an actual polynomial-action operator for
\(e^A v\), motivated by the sharp complete Crouzeix bound reported in OpenAI
family 325~\cite{openaiMatrix}. It executed @MATRIX_CASES@ matrix/tolerance cases over
48 matrices: Jordan, symmetric diffusion, and two nonnormal convection-diffusion
families, at dimensions 16--128 and absolute tolerances $10^{-6}$, $10^{-10}$,
and $10^{-12}$. All produced vectors met their thresholds against a numerical
\texttt{expm} reference. Representative inputs, outputs, and reference vectors are
preserved, so this was a production probe rather than a certificate-only proposal.

The proposed theorem dependency fails a stronger prior-art check. The scalar
Crouzeix constant two needed by \(e^A v\) was already public in August 2026;
the newly complete matrix-valued scope is unused here~\cite{lorist}.
More decisively, this implementation encloses the numerical range in a disk.
The classical numerical-radius dilation and Okubo--Ando result already make that
disk a \emph{complete} 2-spectral set. Consequently the entire constant-two
polynomial program is also an existing conventional construction, with the same
degree, recurrence, and output~\cite{davidson}.

\begin{figure}[H]
\centering
\includegraphics[width=\linewidth]{figures/scientific_challenges.pdf}
\caption{Two challenges after the frozen confirmation. Left: the ordering diagnostic
separates the winning conventional execution from the charged 24-order search;
the 30-second reference point is the original censored confirmation result.
Right: the executable matrix-action candidate uses fewer, equal, or more products
than a conventional portfolio containing the identical classical disk bound,
operator-norm bounds, normal-matrix bounds, and Jordan nilpotency. The portfolio
comparison is by degree, not a measured optimal portfolio runtime.}
\label{fig:scientific-challenges}
\end{figure}

Against the weaker general multiplier $1+\sqrt2$, substituting two saved one
matrix-vector product in 18 cases: @OLD_PRODUCTS@ products became @NEW_PRODUCTS@,
an aggregate reduction of @PRODUCT_SAVING@\%. Against the stronger conventional
portfolio, the candidate had \textbf{0 lower-degree cases, 92 ties, and 52 higher-degree
cases}. These results do not qualify a new productive operator. The recorded error
bound controls analytical truncation only; ordinary floating-point evaluation and
a numerical reference do not provide total roundoff certification. This route was
therefore rejected as the next flagship rather than promoted on its tighter bound.

{\small\color{muted}Evidence files: the frozen confirmation directory; the
byte-preserved dossiers in \path{alternatives/ordering/} and
\path{alternatives/matrix_action/}. Figure generation reads those records and runs
no new scientific experiment.}
"""


def build_text(small: dict[str, Any], performance: list[dict[str, Any]], published: dict[str, Any],
               ordering: dict[str, Any], matrix: dict[str, Any]) -> None:
    """Build the TeX input with numeric values taken from the retained results."""
    times = [r["methods"]["compiler"]["seconds"] for r in performance]
    table_rows = []
    for record in performance:
        if not record["problem"]["name"].endswith("_0"):
            continue
        compiled = record["methods"]["compiler"]
        count = f"{int(compiled['count']):,}".replace(",", r"\,")
        table_rows.append(
            f"{len(record['problem']['cols'])} & ${count}$ & {compiled['states']:,} & "
            f"{compiled['seconds']:.4f} & {record['methods']['orbit']['seconds']:.4f}" + r"\\"
        )
    order_summary = ordering["summary"]
    ascending = next(r for r in ordering["attempts"] if r["order"] == [3, 0, 1, 2])
    products = matrix["summary"]["new_vs_2017_total_matvecs"]
    substitutions = {
        "SMALL": str(small["cases"]), "BIJECTIONS": str(small["exhaustive_bijections"]),
        "CONDITIONED": str(small["conditioned_output_checks"]), "LARGE": str(len(performance)),
        "OUTPUTS": f"{sum(r['methods']['compiler']['accepted'] for r in performance):,}",
        "MINSECONDS": f"{min(times):.4f}", "MAXSECONDS": f"{max(times):.4f}",
        "CORROBORATED": str(sum(r["methods"]["orbit"]["status"] == "complete" for r in performance)),
        "TABLE_ROWS": "\n".join(table_rows), "AUTHOR_SECONDS": f"{published['authors_seconds']:.5f}",
        "REFUSAL_SECONDS": f"{published['compiler']['seconds']:.2f}",
        "ORPHAN_COMPILER": f"{order_summary['compiler_confirmation_seconds']:.3f}",
        "BEST_ORDER": f"{order_summary['best_execution']['seconds']:.3f}",
        "ASCENDING": f"{ascending['seconds']:.3f}",
        "SEARCH_COST": f"{order_summary['total_search_wall_seconds']:.3f}",
        "MATRIX_CASES": str(matrix["summary"]["cases"]),
        "OLD_PRODUCTS": f"{products['old']:,}", "NEW_PRODUCTS": f"{products['new']:,}",
        "PRODUCT_SAVING": f"{100*(products['old']-products['new'])/products['old']:.2f}",
    }
    text = TEX_TEMPLATE
    for key, value in substitutions.items():
        text = text.replace(f"@{key}@", value)
    (PUBLICATION / "generated_science.tex").write_text(text)


def main() -> None:
    """Produce two figures and the requested three-page-scale scientific input."""
    style()
    FIGURES.mkdir(parents=True, exist_ok=True)
    small = read_json(CONFIRMATION / "confirmation.json")
    performance = read_json(CONFIRMATION / "performance.json")
    published = read_json(CONFIRMATION / "published_comparator.json")
    ordering = read_json(STUDY / "alternatives" / "ordering" / "ordering_results.json")
    matrix_base = STUDY / "alternatives" / "matrix_action"
    matrix = read_json(matrix_base / "matrix_probe_results.json")
    assessment = read_json(matrix_base / "matrix_probe_assessment.json")
    performance_figure(performance)
    challenge_figure(ordering, assessment)
    build_text(small, performance, published, ordering, matrix)
    print("Rendered scientific_performance.pdf, scientific_challenges.pdf, and generated_science.tex")


if __name__ == "__main__":
    main()
