# SPDX-License-Identifier: Apache-2.0
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle
from matplotlib.ticker import PercentFormatter

PURPLE = "#301356"
VIOLET = "#8051C9"
LAVENDER = "#B79AE1"
GREEN = "#2F8B78"
AMBER = "#B67A26"
INK = "#302B3B"
MUTED = "#6A6375"
PALE = "#F5F1FA"
PALE_GREEN = "#EDF6F3"
PALE_AMBER = "#FBF3E7"
GRID = "#DDD7E5"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "savefig.dpi": 300, "hatch.linewidth": 0.6,
})


def read_json(path):
    return json.loads(path.read_text())


def heading(fig, title, subtitle):
    fig.text(0.045, 0.949, title, fontsize=15, weight="bold", color=PURPLE, va="top")
    fig.text(0.045, 0.881, subtitle, fontsize=9.5, color=MUTED, va="top")


def footer(fig, text, y=0.037):
    fig.text(0.045, y, text, fontsize=8.0, color=MUTED, va="bottom", linespacing=1.45)


def save_figure(fig, out, stem):
    for extension in ("pdf", "svg", "png"):
        metadata = {"Creator": "AGI ALPHA study: reproducible matplotlib figure"}
        if extension == "pdf":
            metadata.update({"CreationDate": None, "ModDate": None})
        elif extension == "svg":
            metadata.update({"Date": None})
        fig.savefig(out / f"{stem}.{extension}", metadata=metadata)
    plt.close(fig)


def draw_recovery(exploration, transfer, out):
    data = []
    for n in (4, 5, 6):
        if n == 4:
            schemes = exploration["single_erasure_results"]
            pair = schemes["pairwise"]
            parity = schemes["pairwise_plus_xor"]
            values = (pair["unique_recoveries"], pair["cases"], parity["unique_recoveries"], parity["cases"])
        else:
            result = next(row for row in transfer["results"] if row["n"] == n)
            pair = result["schemes"]["pairwise"]["erasures"]["1"]
            parity = result["schemes"]["pairwise_plus_xor"]["erasures"]["1"]
            values = (pair["unique"], pair["cases"], parity["unique"], parity["cases"])
            assert result["schemes"]["pairwise_plus_xor"]["ordinary_identical_information_library_ties"] == parity["cases"]
        data.append({"n": n, "pair_unique": values[0], "pair_cases": values[1], "parity_unique": values[2], "parity_cases": values[3]})
    fig = plt.figure(figsize=(6.7, 4.35))
    heading(fig, "Exact recovery after one erased readout", "All event orders and all erased positions; abstract binary records")
    legend = [Patch(color=VIOLET, label="Pairwise record"), Patch(color=GREEN, label="Standard parity repair"),
              Line2D([0], [0], marker="D", markersize=5.5, markerfacecolor="white", markeredgecolor=PURPLE,
                     linestyle="none", label="Library tie: 5-6 events")]
    fig.legend(handles=legend, loc="upper left", bbox_to_anchor=(0.045, 0.827), ncol=3, frameon=False,
               fontsize=8.4, handlelength=1.2, handletextpad=0.55, columnspacing=1.25)
    ax = fig.add_axes((0.175, 0.205, 0.76, 0.565))
    ax.set_xlim(0, 113)
    ax.set_ylim(-0.53, 2.56)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.grid(axis="x", color=GRID, linewidth=0.65)
    ax.tick_params(axis="both", length=0, labelsize=9)
    ax.set_yticks([2, 1, 0], ["4 events\nExploratory", "5 events\nNew size", "6 events\nNew size"])
    for row, center in zip(data, (2, 1, 0)):
        pair_pct = 100 * row["pair_unique"] / row["pair_cases"]
        parity_pct = 100 * row["parity_unique"] / row["parity_cases"]
        yp, yc = center + 0.18, center - 0.18
        ax.barh(yp, pair_pct, height=0.27, color=VIOLET, zorder=3)
        ax.barh(yc, parity_pct, height=0.27, color=GREEN, zorder=3)
        ax.text(3.0, yp, f"{pair_pct:.1f}%", color="white", va="center", weight="bold", fontsize=9)
        ax.text(pair_pct + 2.3, yp, f'{row["pair_unique"]:,}/{row["pair_cases"]:,}', color=VIOLET, va="center", fontsize=8.7)
        ax.text(3.0, yc, "100%", color="white", va="center", weight="bold", fontsize=9)
        ax.text(71, yc, f'{row["parity_unique"]:,}/{row["parity_cases"]:,}', color="white", va="center", ha="center", fontsize=8.7)
        if row["n"] > 4:
            ax.plot(100, yc, marker="D", markersize=6.1, markerfacecolor="white", markeredgecolor=PURPLE, markeredgewidth=1.2, zorder=5)
    ax.set_xlabel("Unique recoveries / all one-erasure cases", fontsize=9.2, labelpad=8)
    footer(fig, "Parity adds one stored bit; its erased position is included in the denominator.\nThe repair is conventional coding. These are finite computations, not physical-device tests.")
    save_figure(fig, out, "figure-1-erasure-recovery")
    return data


def draw_adjacent_swap(exploration, out):
    edges = exploration["parameters"]["complete_edges"]
    words = ("ABCD", "BACD")
    code = []
    for word in words:
        bits = [int(word.index(a) < word.index(b)) for a, b in edges]
        code.append(bits + [sum(bits) % 2])
    assert sum(a != b for a, b in zip(code[0][:-1], code[1][:-1])) == 1
    witness = next(row for row in exploration["cases"] if row["scheme"] == "pairwise" and row["history"] == "ABCD" and row["erased_index"] == 0)
    assert witness["recovery_set"] == ["ABCD", "BACD"]
    fig = plt.figure(figsize=(6.7, 4.15))
    heading(fig, "One adjacent swap defeats a pairwise readout", "Only the AB relation changes; a conventional XOR bit supplies extra information")
    ax = fig.add_axes((0.04, 0.22, 0.92, 0.59))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    xs = [0.295 + i * 0.085 for i in range(6)] + [0.905]
    headers = ["".join(edge) for edge in edges] + ["XOR"]
    ax.text(0.01, 0.94, "History", fontsize=9, color=MUTED)
    ax.text(0.53, 0.995, "PAIRWISE COMPARISONS", fontsize=8, color=MUTED, ha="center")
    ax.text(xs[-1], 0.995, "EXTRA BIT", fontsize=8, color=GREEN, ha="center")
    for x, label in zip(xs, headers):
        ax.text(x, 0.94, label, fontsize=9, color=GREEN if label == "XOR" else MUTED, ha="center")
    rows = [("A B C D", code[0], False), ("B A C D", code[1], False),
            ("A B C D", [None] + code[0][1:], True), ("B A C D", [None] + code[1][1:], True)]
    for (label, bits, erased), y in zip(rows, (0.79, 0.60, 0.29, 0.10)):
        ax.text(0.01, y, label, fontfamily="DejaVu Sans Mono", fontsize=11, va="center", color=PURPLE)
        for i, (x, bit) in enumerate(zip(xs, bits)):
            face = PALE_GREEN if i == 6 else PALE_AMBER if i == 0 else PALE
            edge = GREEN if i == 6 else AMBER if i == 0 else "white"
            ax.add_patch(Rectangle((x - 0.033, y - 0.068), 0.066, 0.136, facecolor=face, edgecolor=edge, linewidth=0.7))
            ax.text(x, y, "?" if bit is None else str(bit), ha="center", va="center", fontsize=12,
                    color=GREEN if i == 6 else AMBER if i == 0 else INK, weight="bold")
    ax.plot([0.00, 0.98], [0.458, 0.458], color=GRID, linewidth=0.8)
    ax.text(0.01, 0.445, "AB erased", va="top", color=AMBER, fontsize=8.8, weight="bold")
    ax.text(0.55, 0.445, "The six pairwise entries are now identical", va="top", ha="center", color=MUTED, fontsize=8.2)
    fig.text(0.045, 0.157, "Pairwise record: {ABCD, BACD}", fontsize=9, color=AMBER, weight="bold")
    fig.text(0.565, 0.157, "+ XOR: unique recovery", fontsize=9, color=GREEN, weight="bold")
    footer(fig, "Known erasure, four single-use events. An added coded bit is not a demonstrated mechanical part.\nOne parity bit detects one wrong bit; it cannot generally correct that unmarked error.", y=0.035)
    save_figure(fig, out, "figure-2-adjacent-swap")
    return {"edges": edges, "histories": list(words), "codewords_with_parity": code, "erased_comparator": "AB"}


def draw_confluence(confluence, out):
    words = ("AB", "BA", "C", "ABA", "BAB")
    states = {word: confluence["witnesses"]["4"][word]["states"][0] for word in words}
    assert states == {"AB": "1110", "BA": "1101", "C": "1111", "ABA": "1111", "BAB": "1111"}
    nominal = sum(row["audit"]["state_field_cases"] for row in confluence["models"])
    nominal_disagreements = sum(row["audit"]["monotone_control_mismatch"] for row in confluence["models"])
    perturbed = confluence["tolerance"]["state_field_cases"]
    perturbed_disagreements = confluence["tolerance"]["monotone_control_mismatch"]
    assert nominal_disagreements == perturbed_disagreements == 0
    fig = plt.figure(figsize=(6.7, 4.8))
    heading(fig, "Convergent switching preserves a limited history", "Four-bit settled-input model: different event histories can share an endpoint")
    ax = fig.add_axes((0.045, 0.29, 0.91, 0.535))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.96, "INPUT HISTORY", color=MUTED, fontsize=8.2)
    ax.text(0.43, 0.96, "FINAL STATE", color=MUTED, fontsize=8.2, ha="center")
    ax.text(0.68, 0.96, "READOUT LIMIT", color=MUTED, fontsize=8.2)
    xs = [0.31, 0.39, 0.47, 0.55]
    for x, label in zip(xs, ("x", "y", "z", "w")):
        ax.text(x, 0.90, label, ha="center", color=MUTED, fontsize=8.6)
    ys = [0.78, 0.62, 0.40, 0.24, 0.08]
    ax.add_patch(FancyBboxPatch((0.005, 0.005), 0.975, 0.47, boxstyle="round,pad=0.012,rounding_size=0.013", facecolor=PALE_AMBER, edgecolor="none"))
    for word, y in zip(words, ys):
        ax.text(0.02, y, word, fontfamily="DejaVu Sans Mono", fontsize=13, weight="bold", va="center", color=PURPLE)
        for x, bit in zip(xs, states[word]):
            fill = VIOLET if bit == "1" else PALE
            ax.add_patch(Rectangle((x - 0.031, y - 0.057), 0.062, 0.114, facecolor=fill, edgecolor=LAVENDER, linewidth=0.65))
            ax.text(x, y, bit, ha="center", va="center", fontsize=11, color="white" if bit == "1" else PURPLE, weight="bold")
    ax.text(0.68, ys[0], "A-before-B only", fontsize=9, va="center", color=GREEN)
    ax.text(0.68, ys[1], "B-before-A only", fontsize=9, va="center", color=GREEN)
    ax.plot([0.63, 0.63], [0.045, 0.435], color=AMBER, linewidth=1.3)
    ax.text(0.68, 0.33, "HISTORY COLLISION", fontsize=8.9, va="center", weight="bold", color=AMBER)
    ax.text(0.68, 0.21, "C, ABA and BAB\nall end at 1111", fontsize=9, va="center", color=INK, linespacing=1.55)
    fig.text(0.045, 0.219, "Conventional monotone closure: identical endpoints", fontsize=10, weight="bold", color=GREEN)
    fig.text(0.045, 0.175, f"0 disagreements across {nominal:,} nominal and {perturbed:,} perturbed state/field cases", fontsize=9, color=INK)
    footer(fig, "C means both input fields held together until settling. It is not uniquely identified by 1111.\nFinite threshold model; no fabricated device, measured timing or physical-reliability claim.", y=0.040)
    save_figure(fig, out, "figure-3-confluence-collisions")
    return {"states": states, "nominal_cases": nominal, "perturbed_cases": perturbed, "conventional_control_disagreements": 0}


def main():
    study = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--order-dir", type=Path, default=study / "discovery" / "order-memory")
    parser.add_argument("--confluence-dir", type=Path, default=study / "experiments" / "confluence")
    parser.add_argument("--output-dir", type=Path, default=study / "figures")
    args = parser.parse_args()
    paths = {"order_exploration": args.order_dir / "mechanical_memory_probe.json",
             "order_transfer": args.order_dir / "transfer_validation" / "transfer_results.json",
             "confluence": args.confluence_dir / "results.json"}
    inputs = {key: read_json(path) for key, path in paths.items()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    d1 = draw_recovery(inputs["order_exploration"], inputs["order_transfer"], args.output_dir)
    d2 = draw_adjacent_swap(inputs["order_exploration"], args.output_dir)
    d3 = draw_confluence(inputs["confluence"], args.output_dir)
    figures = [
        {"id": 1, "stem": "figure-1-erasure-recovery", "width_inches": 6.7, "height_inches": 4.35,
         "caption": "Exact recovery in abstract event-order records. For every permutation and single erased position, complete pairwise records uniquely recover 72/144, 720/1,200 and 7,200/10,800 cases at four, five and six events. Appending a standard XOR parity bit recovers 168/168, 1,320/1,320 and 11,520/11,520 cases. Each coded denominator includes the added parity position. Diamond markers at five and six events show the exact tie with an ordinary library carrying identical information. Sizes five and six were executed after the local configuration freeze, as implementation checks of a known formula. No physical device or superiority over classical coding is established.",
         "alt": "Horizontal bars show pairwise recovery of 50%, 60% and 66.7% at four, five and six events. Conventional parity recovery is 100% at each size, and the identical-information library ties at five and six events.", "data": d1},
        {"id": 2, "stem": "figure-2-adjacent-swap", "width_inches": 6.7, "height_inches": 4.15,
         "caption": "The adjacent-swap ambiguity and its conventional repair. Histories ABCD and BACD differ only in their AB pairwise relation. Erasing that relation makes the six pairwise readouts identical, so both histories remain admissible. Their separately stored XOR bits differ and recover the missing relation. For n events, m=n(n-1)/2 pairwise bits plus one parity bit suffice for one known erasure; the restricted pairwise-copy class requires 2m bits. This is an abstract information comparison, not an equal-resource physical-device claim: gates, couplings, ancillas and fabrication costs are unmeasured. One parity bit detects a single unmarked substitution but cannot generally correct it.",
         "alt": "Two event histories have identical five unaffected pairwise bits. Their AB bit differs, then becomes unknown after erasure. The additional XOR bit remains zero versus one and distinguishes the histories.", "data": d2},
        {"id": 3, "stem": "figure-3-confluence-collisions", "width_inches": 6.7, "height_inches": 4.8,
         "caption": "What the four-bit confluence model does and does not record. AB and BA settle at 1110 and 1101, while C, ABA and BAB all settle at 1111. C denotes simultaneous held input fields until settling; it is not a general overlap class. The collision prevents a complete-history or unique-simultaneity claim. The conventional monotone-closure control matches the proposed endpoints in all 140 nominal and 71,680 perturbed all-state/held-field cases. These are executed finite-model checks rather than independent physical trials. Internal update-order convergence and external event-order sensitivity coexist through established positive-feedback latching; the result does not establish a substantive advance beyond identified prior art.",
         "alt": "A bit-state table shows AB mapping to 1110 and BA to 1101. An amber collision band shows C, ABA and BAB all mapping to 1111. A footer states exact agreement with conventional monotone closure.", "data": d3},
    ]
    sources = {}
    for key, path in paths.items():
        try:
            label = path.resolve().relative_to(study).as_posix()
        except ValueError:
            label = path.name
        sources[key] = {"path": label, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {"generator": "src/build_figures.py", "formats": ["pdf", "svg", "png"], "png_dpi": 300,
                "palette": [PURPLE, VIOLET, LAVENDER, GREEN, AMBER], "source_files": sources, "figures": figures}
    (args.output_dir / "caption_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"output_dir": str(args.output_dir), "figure_count": len(figures), "formats": manifest["formats"],
                      "source_files": sources}, indent=2))


if __name__ == "__main__":
    main()
