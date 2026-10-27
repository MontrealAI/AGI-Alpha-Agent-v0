# SPDX-License-Identifier: Apache-2.0
"""Render conditional economics directly from the frozen confirmation report."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

PURPLE = "#301356"
VIOLET = "#8051C9"
LAVENDER = "#B79AE1"
INK = "#302B3B"
MUTED = "#6A6375"
PALE = "#F5F1FA"
GRID = "#DDD7E5"
STEM = "figure-4-conditional-economics"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "svg.hashsalt": "agi-alpha-conditional-economics-v1",
    "figure.facecolor": "white", "savefig.facecolor": "white", "savefig.dpi": 300,
})


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def money(value: float) -> str:
    return ("−" if value < 0 else "") + f"${abs(value):,.2f}"


def extract_data(report: dict, config: dict) -> tuple[list[dict], dict, dict]:
    rd = report["freeze"]["research_cost_primary"]
    assert rd["band"] == "central" and rd["engineering_hour_reduction_assumed"] == 0
    assert config["months"] == 12
    assert report["currency"] == config["currency"] == "USD"
    assert config["actual"]["collections"] == 0
    rows = []
    durations = {}
    for name in ("conservative", "central", "favorable"):
        result = report["results"][name]
        operating = result["conditional_qualified_operation"]["qualified_annual_operating_profit"]
        q = result["qualification_probability_assumed"]
        assert q == config["scenario"][name]["qualified_device_probability"]
        assert operating["worlds"] == report["worlds_per_scenario"] == 512
        project = result["conditional_predevelopment_E0_central"]
        assert math.isclose(project, q * operating["mean"] - rd["A_originating_research_total"], abs_tol=1e-8)
        rows.append({
            "scenario": name,
            "qualification_probability_assumed": q,
            "mean_operating_profit_after_assumed_qualification_usd": operating["mean"],
            "expected_project_profit_usd": project,
            "operating_label": money(operating["mean"]),
            "project_label": money(project),
            "fixed_policy": result["frozen_policy"]["policy"],
            "fixed_list_price_usd": result["frozen_policy"]["price"],
        })
        for pathway in result["research_pathways"]:
            if pathway["configuration"] == "E_no_benefit":
                band = pathway["rd"]["band"]
                duration = pathway["rd"]["duration_months_assumed"]
                assert band not in durations or durations[band] == duration
                durations[band] = duration
    assert durations == {"low": 3, "central": 9, "high": 18}
    assert rd["duration_months_assumed"] == durations["central"]
    return rows, rd, durations


def draw_figure(rows: list[dict], rd: dict, out: Path) -> None:
    fig = plt.figure(figsize=(6.7, 5.05))
    fig.text(0.045, 0.953, "Conditional economics across three scenarios", fontsize=14.6,
             weight="bold", color=PURPLE, va="top")
    fig.text(0.045, 0.893, "12 production months after assumed physical qualification", fontsize=9.6,
             color=MUTED, va="top")
    fig.legend(handles=[Patch(color=VIOLET, label="Operating profit if qualified"),
                        Patch(color=PURPLE, label="Expected project profit")],
               loc="upper left", bbox_to_anchor=(0.045, 0.855), ncol=2, frameon=False,
               fontsize=9.0, handlelength=1.25, handletextpad=0.55, columnspacing=1.7)
    ax = fig.add_axes((0.230, 0.290, 0.510, 0.470))
    ax.set_xlim(-205000, 450000)
    ax.set_ylim(-0.59, 2.56)
    ax.set_axisbelow(True)
    ax.set_xticks([-200000, 0, 200000, 400000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1000:,.0f}".replace("-", "−")))
    ax.grid(axis="x", color=GRID, linewidth=0.7)
    ax.axvline(0, color=MUTED, linewidth=1.1, zorder=2)
    ax.tick_params(axis="both", length=0, labelsize=8.6)
    ax.tick_params(axis="y", pad=9)
    ax.set_yticks([2, 1, 0], [f"{row['scenario'].capitalize()}\nq = {row['qualification_probability_assumed']:.2f}"
                              for row in rows], fontsize=9.0, linespacing=1.5)
    ax.set_xlabel("USD thousands", fontsize=9.0, labelpad=8)
    fig.text(0.785, 0.785, "MEAN / EXPECTED USD", fontsize=7.9, color=MUTED, va="center")
    for row, center in zip(rows, (2, 1, 0)):
        for key, label, offset, color in (
            ("mean_operating_profit_after_assumed_qualification_usd", "operating_label", 0.18, VIOLET),
            ("expected_project_profit_usd", "project_label", -0.18, PURPLE),
        ):
            y = center + offset
            ax.barh(y, row[key], height=0.27, color=color, zorder=3)
            ax.text(1.088, y, row[label], transform=ax.get_yaxis_transform(), color=color,
                    fontsize=9.0, weight="bold", va="center", ha="left", clip_on=False)
    fig.text(0.045, 0.174,
             f"Project = q × mean operation − A; central A = {money(rd['A_originating_research_total'])}.",
             fontsize=8.2, color=INK, va="top")
    fig.text(0.045, 0.133,
             "R&D: 9 months here; low/high duration scenarios are 3/18 months.",
             fontsize=8.2, color=MUTED, va="top")
    fig.text(0.045, 0.092,
             "Constructed scenarios; q is uncalibrated. No actual collections.",
             fontsize=8.2, color=MUTED, va="top")
    fig.text(0.045, 0.051,
             "Customer value, demand, physical success and costs remain unvalidated.",
             fontsize=8.2, color=MUTED, va="top")
    for extension in ("png", "svg", "pdf"):
        metadata = {"Creator": "AGI ALPHA study: frozen-results economics figure"}
        if extension == "pdf":
            metadata.update({"CreationDate": None, "ModDate": None})
        elif extension == "svg":
            metadata["Date"] = None
        fig.savefig(out / f"{STEM}.{extension}", metadata=metadata)
    plt.close(fig)


def main() -> None:
    study = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=study / "results/economics-results.json")
    parser.add_argument("--config", type=Path, default=study / "config/economics.json")
    parser.add_argument("--output-dir", type=Path, default=study / "figures")
    args = parser.parse_args()
    report = json.loads(args.results.read_text())
    config = json.loads(args.config.read_text())
    assert file_hash(args.config) == report["hashes"]["config"]
    rows, rd, durations = extract_data(report, config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    draw_figure(rows, rd, args.output_dir)
    caption = (
        "Conditional economics of the proposed four-event chronology device under three constructed scenarios. "
        "Light-purple bars show mean operating profit during twelve production months after assumed physical "
        "qualification; dark-purple bars show q times that operating mean less the central originating development "
        "cost of $141,792.30. The central development pathway assumes nine months and no AI engineering-hour saving; "
        "the low/high development-duration alternatives are three/eighteen months. Qualification probabilities "
        "q = 0.25, 0.50 and 0.75 are uncalibrated assumptions. The fixed policies are evaluated on 512 confirmation "
        "worlds per scenario. Project values are probability-weighted expectations, not the sampled project-profit "
        "mean or annualized returns. Labels show the frozen numerical means and expectations to the nearest cent; "
        "that display precision does not establish empirical accuracy. Customer value, demand, physical success "
        "and cost adequacy remain unvalidated. Actual collections are zero and the actual decision remains HOLD."
    )
    alt = (
        "Paired horizontal bars compare conservative, central and favorable scenarios. Conditional annual operating "
        "means are minus $73,910.25, plus $20,979.00 and plus $417,868.10. Expected project results after central "
        "development cost are minus $160,269.86, minus $131,302.80 and plus $171,608.78. All are constructed scenarios."
    )
    sources = {}
    for label, path in (("frozen_results", args.results), ("frozen_config", args.config)):
        try:
            display_path = path.resolve().relative_to(study).as_posix()
        except ValueError:
            display_path = str(path.resolve())
        sources[label] = {"path": display_path, "sha256": file_hash(path)}
    manifest = {
        "id": 4, "stem": STEM, "generator": "src/build_economics_figure.py",
        "generator_sha256": file_hash(Path(__file__)),
        "width_inches": 6.7, "height_inches": 5.05, "png_dpi": 300,
        "palette": {"operating": VIOLET, "project": PURPLE, "grid": GRID},
        "source_files": sources, "caption": caption, "alt": alt, "data": rows,
        "qualification_probability_source": "Uncalibrated constructed scenario assumptions, not finite-model pass rates.",
        "primary_originating_research_cost_usd": rd["A_originating_research_total"],
        "research_duration_months_assumed": durations,
        "production_months": config["months"], "worlds_per_scenario": report["worlds_per_scenario"],
        "actual_collections_usd": config["actual"]["collections"],
        "actual_decision": report["actual_decision"],
        "outputs": [{"path": f"figures/{STEM}.{extension}",
                     "sha256": file_hash(args.output_dir / f"{STEM}.{extension}")}
                    for extension in ("png", "svg", "pdf")],
    }
    (args.output_dir / "economics-caption-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"figure": STEM, "data": rows, "source_files": sources}, indent=2))


if __name__ == "__main__":
    main()
