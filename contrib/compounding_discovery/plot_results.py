# SPDX-License-Identifier: Apache-2.0
"""Export source-bound chronological curves for the research handoff."""

from __future__ import annotations
import argparse, csv, json
from fractions import Fraction
from pathlib import Path
from typing import Any


def plot(source: Path, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summary = json.loads(source.read_text())
    panels = summary["learning"]["checkpoints"]
    rows = []
    output.mkdir(parents=True, exist_ok=False)
    for cycle, value in sorted(panels.items(), key=lambda pair: int(pair[0])):
        for system, cell in value["systems"].items():
            rows.append(
                {
                    "cycle": int(cycle),
                    "system": system,
                    "accepted": cell["accepted"],
                    "n": cell["n"],
                    "accepted_pct": 100 * cell["accepted"] / cell["n"],
                    "mean_marginal_cpu_cost_micro_usd": 1e6 * float(Fraction(cell["mean_marginal_cost_usd"])),
                    "mean_solver_calls": cell["mean_solver_calls"],
                    "mean_operations": cell["mean_operations"],
                    "lifecycle_cost_usd": float(Fraction(cell["known_lifecycle_cost_usd"])),
                }
            )
    with (output / "learning-curves.csv").open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    colors = {"cumulative": "#1b6483", "frozen": "#b36331", "reset": "#726596", "retrieval": "#32806b"}
    marks = {"cumulative": ("o", "-"), "frozen": ("s", "--"), "reset": ("^", ":"), "retrieval": ("x", "-.")}
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7), layout="constrained")
    metrics = [
        ("accepted_pct", "Accepted model certificates (%)"),
        ("mean_marginal_cpu_cost_micro_usd", "Mean modeled CPU cost (microUSD)"),
        ("mean_solver_calls", "Mean LP solver calls"),
    ]
    for system in colors:
        selected = [r for r in rows if r["system"] == system]
        for ax, (metric, label) in zip(axes, metrics):
            marker, style = marks[system]
            ax.plot(
                [r["cycle"] for r in selected],
                [r[metric] for r in selected],
                label=system.capitalize(),
                color=colors[system],
                marker=marker,
                linestyle=style,
                linewidth=1.7,
                markersize=5,
                alpha=0.88,
            )
            ax.set_ylabel(label)
            ax.set_xlabel("Completed learning cycles")
            ax.set_xticks([r["cycle"] for r in selected])
            ax.grid(axis="y", alpha=0.2)
            ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylim(0, 105)
    axes[1].set_ylim(bottom=0)
    axes[2].set_ylim(bottom=0)
    axes[0].legend(fontsize=8, loc="lower left")
    fig.suptitle("Chronological learning on fresh parameter panels of one public route instance", fontsize=12)
    fig.savefig(output / "learning-curves.png", dpi=180)
    fig.savefig(output / "learning-curves.pdf")
    plt.close(fig)
    (output / "caption.txt").write_text(
        "Four chronological systems receive paired fresh operator updates in common difficulty strata. The same final independent model checker applies throughout. Repeated seeds share task clusters. CPU charges use the declared simulated USD0.10/hour rate and exclude common AI development costs shown in the lifecycle ledger. These are known-public-model parameter panels, not empirical transport or cross-domain generalization. Exact CSV values and paired uncertainty analyses are retained in the source summary.\n"
    )
    (output / "source.json").write_text(
        json.dumps({"summary": str(source), "source_freeze": summary["source_freeze"], "n_rows": len(rows)}, indent=2)
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("summary", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    plot(a.summary, a.output)
