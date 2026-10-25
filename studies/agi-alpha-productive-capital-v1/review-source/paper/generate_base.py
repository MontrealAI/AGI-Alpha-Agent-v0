# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import json, hashlib
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
GEN = PAPER / "generated"
FIG = PAPER / "figures"
GEN.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)


def put(name, text):
    (GEN / name).write_text(text + "\n")


def tex(x):
    return str(x).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def main():
    s = json.loads((ROOT / "outputs/summary.json").read_text())
    rows = s["joint_rows"]
    by = {(r["cycle"], r["arm"]): r for r in rows}
    _freeze = json.loads((ROOT / "protocol/experiment-FREEZE.json").read_text())
    fh = hashlib.sha256((ROOT / "protocol/experiment-FREEZE.json").read_bytes()).hexdigest()
    put("numbers.tex", r"\newcommand{\StudyRuns}{72}\newcommand{\FamilyChecks}{216}")
    put(
        "experiment_design.tex",
        r"""\begin{table}[H]\small
\begin{tabularx}{\linewidth}{p{.24\linewidth}X}\toprule Design element & Prespecified content \\\midrule
Projects & SDK release, research publication and operations handoff; each with simple and complex strata. \\
Inputs & 14 exact public source snapshots. Declared dependencies, durations, resource calendars and revisions are synthetic. \\
Complexity & Simple: 8 components and 6 jobs. Complex: 14 components and 12 jobs. \\
Cycles & Initial production; stable replay; fresh source/duration revision; fresh edge/calendar change and repair. \\
Alternatives & Full rebuild, predecessor/child flywheel and independently written conventional dependency-key caching. Existing Alpha portfolio and native specialists remain available. \\
Counts & Six project instances $\times$ four cycles $\times$ three arms = 72 joint executions, each with three deliverable checks (216 checks). These are not 216 independent jobs. \\
Bounds & 18 components, 18 planning jobs, 128 slots, 4 crew; 2-second native solves, 30-second Node process timeout. \\
Freeze & 38 files; 25 October 2026, 14:14:23 UTC. Full identities and subsequent correction boundary are in the companion. \\\bottomrule\end{tabularx}
\caption{One controlled connected-production experiment, with stable and fresh slices.}
\end{table}""",
    )
    put(
        "architecture_figure.tex",
        r"""\begin{figure}[H]\centering
\begin{tikzpicture}[every node/.style={font=\small,align=center},box/.style={draw=purple,fill=lavender,rounded corners=2mm,text width=4.3cm,minimum height=1.0cm},arr/.style={->,thick,color=purple}]
\node[box] (mission) at (0,0) {Mission specification\\Scope, sources, acceptance};
\node[box] (delivery) at (6,0) {Alpha / SUCCESSOR\\Workbench delivery};
\node[box] (retained) at (6,-2) {Retained artifacts\\Parent index + child};
\node[box] (ledger) at (0,-2) {Conserved cash ledger\\Proceeds, costs, reserves};
\node[box] (invest) at (0,-4) {Investment admission\\Fundability + value};
\node[box] (next) at (6,-4) {Subsequent production\\Stable and fresh slices};
\draw[arr] (mission)--(delivery);\draw[arr] (delivery)--(retained);\draw[arr] (delivery.south west)--(ledger.north east);
\draw[arr] (ledger)--(invest);\draw[arr] (retained)--(next);\draw[arr] (invest)--(next);
\draw[arr] (next.east)--++(.65,0)|-(delivery.east);
\end{tikzpicture}
\caption{Implemented local artifact links and a separately modeled financial link. Manager, Jobs and Fleet retain their distinct settlement/admission boundaries; no transaction or external execution is implied by the diagram.}
\end{figure}""",
    )
    cpu_f = sum(by[c, "flywheel"]["total_cpu_ms"] for c in [2, 3])
    cpu_c = sum(by[c, "conventional_cache"]["total_cpu_ms"] for c in [2, 3])
    stable_reduction = 100 * (1 - by[1, "flywheel"]["total_cpu_ms"] / by[1, "full_rebuild"]["total_cpu_ms"])
    text = r"""The original frozen campaign recorded 72/72 joint results accepted by its declared oracle, corresponding to 216/216 family acceptance checks. Within each treatment, each class has 24 accepted outputs across six projects and four cycles. No retries were needed on these supported inputs; four separately counted refusal controls rejected cyclic dependencies, missing evidence, private data and job-count overflow. There were 24 observed parent invocations and 12 child invocations. These counters establish use, not economic benefit.

The stable repeat reduced six-project CPU from \textbf{2.271 seconds} for full rebuild to \textbf{0.845 seconds} for the flywheel, while conventional caching used \textbf{0.822 seconds}. On the two fresh-change cycles, flywheel and conventional caching each rebuilt only \textbf{18 of 132 source cards} and reused 114. Their total CPU was \textbf{4.069} and \textbf{4.033 seconds}, respectively. The flywheel was approximately \textbf{0.9\% slower} on this recorded fresh slice. Six local instances do not establish a population timing difference; they establish no demonstrated superiority over the strong incumbent.

\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/production.pdf}
\caption{Recorded native research. CPU includes the joint local pipeline, native/portfolio planning, checks and persisted artifacts; it is not complete Agent cost. The source-card reduction is also achieved by ordinary caching. Each point summarizes six controlled projects.}\end{figure}

\begin{table}[H]\small\centering\begin{tabular}{lrrr}\toprule Cycle & Full rebuild CPU (s) & Flywheel CPU (s) & Cache CPU (s)\\\midrule
"""
    for c, label in enumerate(["Initial", "Stable repeat", "Source/duration change", "Dependency/calendar repair"]):
        text += (
            f"{label} & "
            + " & ".join(
                f"{by[c,a]['total_cpu_ms']/1000:.3f}" for a in ["full_rebuild", "flywheel", "conventional_cache"]
            )
            + r" \\"
            + "\n"
        )
    text += r"""\bottomrule\end{tabular}\caption{Observed joint CPU; one cost belongs to three deliverables and is not counted three times.}\end{table}

Child descriptor construction across six bindings consumed 0.421 seconds wall time and 0.466 seconds CPU in addition to service execution. These measurements cover authored-algorithm binding and checking, not the human/model effort that designed or corrected the algorithm. Original initialization, developmental failures and refused inputs are retained separately.

\subsection{Post-freeze defects and the corrective edition}
Independent-role adversarial review after the original freeze found stale path-only metadata, cross-project predecessor reuse, inadequately checked construction origin and inconsistent deletion handling. The original oracle also failed some tampered metadata/digest probes. Those controls were outside the original fixed-inventory confirmation inputs. The original acceptance totals are preserved with that scope; they do not qualify arbitrary changed projects. A separately frozen corrective adapter and fresh edge evaluation are reported below. No historical result was overwritten or promoted to the new source identity.

\input{generated/corrective_results.tex}

The new change-impact and cross-artifact certificate is a real implemented interface. The strong conventional alternatives can produce the same deliverables under the declared bounds. Consequently, \textbf{previously impractical work becoming feasible under the same budgets is not established}. Discovery-process improvement and self-acceleration are also not established."""
    wall = ", ".join(f"{by[c,'flywheel']['median_wall_ms']:.1f}" for c in range(4))
    text = text.replace(
        "Child descriptor construction across six bindings",
        "Observed median local wall times for a joint flywheel request were "
        + wall
        + " milliseconds for the initial, stable, source-change and dependency-change cycles, respectively. They exclude unmetered authoring, human review, customer communication and the unavailable live executor path. No active human-minute measurement is available.\n\nChild descriptor construction across six bindings",
    )
    put("production_results.tex", text)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": "#42344f",
            "xtick.color": "#42344f",
            "ytick.color": "#42344f",
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    fig, axs = plt.subplots(1, 2, figsize=(10.7, 3.65))
    colors = {"full_rebuild": "#92909b", "flywheel": "#693bb1", "conventional_cache": "#177b69"}
    labels = {"full_rebuild": "Full rebuild", "flywheel": "Flywheel", "conventional_cache": "Conventional cache"}
    for a in colors:
        axs[0].plot(
            range(4),
            [by[c, a]["total_cpu_ms"] / 1000 for c in range(4)],
            marker="o",
            label=labels[a],
            color=colors[a],
            lw=2,
        )
        axs[1].plot(
            range(4),
            [by[c, a]["built_items"] for c in range(4)],
            marker="o",
            label=labels[a],
            color=colors[a],
            lw=2,
            ls="--" if a == "conventional_cache" else "-",
        )
    for ax in axs:
        ax.set_xticks(range(4), ["Initial", "Stable", "Fresh 1", "Fresh 2"])
        ax.grid(axis="y", alpha=0.18)
        ax.set_axisbelow(True)
    axs[0].set_ylabel("Total CPU across six projects (seconds)")
    axs[0].set_title("Whole local request cost", loc="left", fontweight="bold")
    axs[1].set_ylabel("Source cards rebuilt across six projects")
    axs[1].set_title("A reuse gain shared by the incumbent", loc="left", fontweight="bold")
    axs[1].set_ylim(-4, 72)
    axs[0].legend(loc="lower center", bbox_to_anchor=(1.1, 1.04), ncol=3, frameon=False, fontsize=9)
    fig.tight_layout()
    for ext in ["pdf", "svg", "png"]:
        fig.savefig(FIG / f"production.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    rates = [
        ("Software / assurance", 135980, "93.40"),
        ("Operations / planning", 88940, "61.09"),
        ("Technical writing / dossier", 90390, "62.09"),
        ("Clerical reconciliation (scope)", 50670, "34.80"),
    ]
    t = (
        r"\begin{table}[H]\small\centering\begin{tabular}{lrrr}\toprule Occupation / use & Annual wage (USD) & Wage/hour & Loaded scenario/hour\\\midrule"
        + "\n"
    )
    for n, w, loaded_rate in rates:
        t += f"{n} & {w:,.0f} & {w/2080:,.2f} & {loaded_rate}" + r" \\" + "\n"
    t += r"\bottomrule\end{tabular}\caption{Sourced May 2025 U.S. medians; calculated hourly anchors use 2,080 hours and the estimated benefit factor $46.89/32.82$. No task duration is inferred.}\end{table}"
    put("human_rates.tex", t)
    base = (ROOT / "research/sources_human.bib").read_text()
    base = base.replace("—", "--").replace("–", "--")
    refs = {
        "alpha_source": (
            "AGI ALPHA current source checkpoint",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/f836f06e8351e64db1da770e16e304b5feb01f28",
        ),
        "coordination": (
            "SUCCESSOR operating and publication coordination, issue 4850",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850",
        ),
        "transformational": (
            "Transformational Intelligence: Learning to Change the Game",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/docs/Transformational_Intelligence.tex",
        ),
        "manager_source": (
            "AGI Job Manager: USDC payout split",
            "https://github.com/MontrealAI/AGIJobManager/blob/5d5670df9dbbc79da115e0a44b71989f34df58c1/docs/USDC_PAYOUT_SPLIT.md",
        ),
        "jobs_source": (
            "AGI Jobs v0: settlement implementation",
            "https://github.com/MontrealAI/AGIJobsv0/blob/bc4abbd5c28f3672275b13300e40ea26c820b8ee/contracts/v2/implementation/JobRegistryBase.sol",
        ),
        "fleet_source": (
            "AGI Fleet Linux: source-bound successor project handoff",
            "https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/fleet/packages/AGI_Agent/successor/project.mjs",
        ),
        "strategy_history": (
            "Strategy Laboratory: preserved historical source audit",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/studies/agi-alpha-flywheel-strategy-succession-v1/history/HISTORICAL_STRATEGY_LAB_AUDIT.md",
        ),
        "strategy_results": (
            "Strategy Succession: preserved confirmation summary",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/studies/agi-alpha-flywheel-strategy-succession-v1/results/confirmation-v1/SUMMARY.json",
        ),
        "strategy_worker": (
            "Strategy engineering worker: scope, construction and retained losses",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/contrib/strategy_succession/worker/README.md",
        ),
        "alpha_contracts": (
            "Alpha Ascension five-contract source",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/f836f06e8351e64db1da770e16e304b5feb01f28/contracts/ascension",
        ),
        "alpha_deployment": (
            "Current mainnet deployment: operator-evidence projection and retained holds",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/f836f06e8351e64db1da770e16e304b5feb01f28/docs/agent/CURRENT_MAINNET_DEPLOYMENT.md",
        ),
    }
    for k, (title, url) in refs.items():
        base += (
            "\n@misc{"
            + k
            + ",\n author={{MONTREAL.AI}},\n title={"
            + title
            + "},\n year={2026},\n howpublished={\\url{"
            + url
            + "}},\n note={Inspected 25 October 2026; exact source identity retained in companion}\n}\n"
        )
    (PAPER / "references.bib").write_text(base)
    print(
        json.dumps(
            {
                "written": "base paper inputs",
                "fresh_cpu_ratio": cpu_f / cpu_c,
                "stable_rebuild_reduction_percent": stable_reduction,
                "protocol_sha256": fh,
            }
        )
    )


if __name__ == "__main__":
    main()
