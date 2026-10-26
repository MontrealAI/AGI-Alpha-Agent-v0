# SPDX-License-Identifier: Apache-2.0
"""Generate scientific figures directly from frozen recorded evidence."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "publication" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
PURPLE, TEAL, GREY, GOLD = "#713EAD", "#18776F", "#8B8494", "#BC852A"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
    "axes.labelsize": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#B3A8BD", "axes.labelcolor": "#282031", "text.color": "#282031",
    "xtick.color": "#50475B", "ytick.color": "#50475B", "figure.facecolor": "white",
    "axes.facecolor": "#FCFAFF", "savefig.bbox": "tight", "pdf.fonttype": 42,
})
records = []


def load(rel):
    path = ROOT / rel
    records.append({"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return json.loads(path.read_text())


def save(fig, name):
    fig.savefig(OUT / (name + ".pdf"))
    fig.savefig(OUT / (name + ".png"), dpi=160)
    plt.close(fig)


def main():
    production = load("production/joint-summary.json")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.45), layout="constrained")
    names = ["manual", "retained", "conventional"]
    for ax, key, title in zip(axes, ["mechanical_wall_seconds", "local_cpu_seconds"],
                              ["Mechanical wall time per assessment", "Inclusive local CPU per assessment"]):
        for i, (arm, color) in enumerate(zip(names, [GREY, PURPLE, TEAL])):
            vals = [x[key] for x in production["per_mission"] if x["arm"] == arm]
            ax.scatter(i + np.linspace(-.1, .1, len(vals)), vals, color=color, s=28, zorder=3)
            ax.hlines(np.mean(vals), i - .22, i + .22, color=color, lw=2.3)
        ax.set_xticks(range(3), ["A · ordinary", "B · retained", "C · conventional"])
        ax.set_ylabel("Seconds (observed)")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.grid(axis="y", alpha=.2)
        ax.set_ylim(bottom=0)
    save(fig, "production")

    primary = load("market/results/primary-01/summary.json")
    rows = [r for r in primary["scenarios"] if r["scenario"].startswith("primary-")]
    hours = sorted({r["config"]["constructionHours"] for r in rows})
    minutes = sorted({r["config"]["ordinaryFinalizationMinutes"] for r in rows})
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), layout="constrained")
    matrices = []
    for choice in ["deterministic", "logit"]:
        matrices.append(np.array([[next(r["causal"]["B_minus_A_profitCents"]["mean"] / 100 for r in rows
            if r["config"]["choiceModel"] == choice and r["config"]["constructionHours"] == h
            and r["config"]["ordinaryFinalizationMinutes"] == m) for m in minutes] for h in hours]))
    low = min(float(a.min()) for a in matrices)
    for ax, choice, matrix in zip(axes, ["Deterministic buyers", "Logit buyers"], matrices):
        im = ax.imshow(matrix, cmap="PuRd_r", vmin=low, vmax=0, aspect="auto")
        for (i, j), val in np.ndenumerate(matrix):
            ax.text(j, i, "\u0024" + f"{val:,.0f}", ha="center", va="center",
                    color="white" if val < low * .6 else "#231137", fontsize=9)
        ax.set_xticks(range(len(minutes)), minutes)
        ax.set_yticks(range(len(hours)), [f"{h:g} h" for h in hours])
        ax.set_xlabel("Assumed finalization minutes avoided")
        ax.set_ylabel("Assumed historical construction")
        ax.set_title(choice, loc="left", fontweight="bold")
    fig.colorbar(im, ax=axes, shrink=.8, label="Mean B − A / simulated USD", pad=.02)
    save(fig, "primary")

    exploration = load("market/exploratory/results-01/summary.json")
    regimes = ["full-earned", "adoption-earned", "full-seed", "adoption-seed"]
    labels = ["History + earned", "Adoption + earned", "History + seed", "Adoption + seed"]
    integrations = [0, 1000, 5000]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), layout="constrained")
    for ax, arrival in zip(axes, [.25, .5]):
        for regime, label, color, marker in zip(regimes, labels, [PURPLE, TEAL, GREY, GOLD], ["o","s","^","D"]):
            selected = [next(r for r in exploration["scenarios"]
                if r["scenario"] == f"explore-i{i}-a{arrival}-m10-logit-{regime}") for i in integrations]
            y = [r["arms"]["B"]["profitCents"]["mean"] / 100 for r in selected]
            ax.plot([0, 10, 50], y, marker=marker, lw=1.5, color=color, label=label)
        ax.axhline(0, color="#544B62", lw=.7)
        ax.set_title(f"Arrival {arrival:g} per buyer/week", loc="left", fontweight="bold")
        ax.set_xlabel("Assumed integration cost / USD")
        ax.set_ylabel("Mean B profit / simulated USD")
        ax.set_xticks([0, 10, 50])
        ax.grid(axis="y", alpha=.2)
    axes[1].legend(fontsize=7.5, loc="lower right")
    save(fig, "exploration")

    policy_path = ROOT / "market/policy-diagnostic/results-01/summary.json"
    if policy_path.exists():
        policy = load("market/policy-diagnostic/results-01/summary.json")
        prices = [500, 1000, 2000, 4000, 8000]
        fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.3), layout="constrained", sharex=True)
        for col, integration in enumerate([0, 1000]):
            for regime, label, color, marker in zip(regimes, labels, [PURPLE, TEAL, GREY, GOLD], ["o","s","^","D"]):
                selected = [next(r for r in policy["scenarios"] if r["scenario"] ==
                    f"policy-p{p}-i{integration}-a0.5-m10-logit-{regime}") for p in prices]
                for row, getter in enumerate([
                    lambda r: r["arms"]["B"]["profitCents"],
                    lambda r: r["causal"]["B_minus_A_profitCents"]]):
                    ys = [getter(r)["mean"] / 100 for r in selected]
                    axes[row, col].plot(range(5), ys, marker=marker, color=color, lw=1.5, label=label)
            for row in range(2):
                ax = axes[row, col]
                ax.axhline(0, color="#544B62", lw=.7)
                ax.grid(axis="y", alpha=.2)
                ax.set_xticks(range(5), ["$5", "$10", "$20", "$40", "$80"])
                ax.set_ylabel(["Mean B profit / USD", "Mean B − A / USD"][row])
            axes[0, col].set_title(f"Integration USD {integration/100:g}", loc="left", fontweight="bold")
            axes[1, col].set_xlabel("Fixed target price, subject to cost floor")
        axes[0,1].legend(fontsize=7.3, loc="best")
        save(fig, "policy")

        representative = {}
        source = ROOT / "market/policy-diagnostic/results-01/complete-runs.jsonl.gz"
        with gzip.open(source, "rt") as f:
            for line in f:
                obj = json.loads(line)
                for regime in regimes:
                    if obj["seed"] == 2001 and obj["config"]["id"] == f"policy-p2000-i0-a0.5-m10-logit-{regime}":
                        representative[regime] = obj
                if len(representative) == 4:
                    break
        fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.0), layout="constrained", sharex=True)
        for ax, regime, label in zip(axes.flat, regimes, labels):
            obj = representative[regime]
            for arm, color in zip(["A","B","C"], [GREY, PURPLE, TEAL]):
                balances = obj["arms"][arm]["histories"]["balances"]
                ax.plot([b["week"] for b in balances], [b["cashCents"]/100 for b in balances],
                        label=arm, color=color, lw=1.6, linestyle="--" if arm == "C" else "-")
            ax.axhline(200, color=GOLD, linestyle=":", lw=1, label="Reserve")
            b = obj["arms"]["B"]
            if b["summary"]["investmentWeek"] is not None:
                ax.axvline(b["summary"]["investmentWeek"], color=PURPLE, linestyle=":", lw=.9)
            ax.set_title(label, loc="left", fontweight="bold")
            ax.set_xlabel("Modeled week (collection drain included)")
            ax.set_ylabel("Cash / simulated USD")
            ax.grid(alpha=.15)
        axes.flat[0].legend(ncols=4, fontsize=7, loc="best")
        save(fig, "history")
        (ROOT/"publication"/"representative-histories.json").write_text(json.dumps({
            "basis":"SIMULATED_PREDECLARED_ILLUSTRATION_NOT_BEST_CASE",
            "selection": "Target20, integration0, arrival.5, minutes10, logit, seed2001, all regimes",
            "histories": representative}, indent=2) + "\n")
        fields = ["scenario", "price_target_usd", "integration_usd", "arrival", "choice",
                  "cost_basis", "funding", "B_mean_profit_usd", "B_profit_low95", "B_profit_high95",
                  "B_minus_A_mean_usd", "B_minus_A_low95", "B_minus_A_high95",
                  "B_adoption_rate", "B_profitable_rate", "B_direct_repayment_rate"]
        with (ROOT/"publication"/"policy-complete-table.csv").open("w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=fields); writer.writeheader()
            for r in policy["scenarios"]:
                c=r["config"]; p=r["arms"]["B"]["profitCents"]; d=r["causal"]["B_minus_A_profitCents"]
                writer.writerow(dict(zip(fields, [r["scenario"], c["initialPriceCents"]/100,
                    c["integrationCents"]/100, c["arrivalProbability"], c["choiceModel"],
                    c["investmentCostBasis"], c["investmentFunding"], p["mean"]/100,
                    *[v/100 for v in p["meanInterval95"]],d["mean"]/100,
                    *[v/100 for v in d["meanInterval95"]], r["arms"]["B"]["investmentRate"],
                    r["arms"]["B"]["viableRate"], r["arms"]["B"]["directRepaymentRate"]])))
    manifest = {"schema":"game-market-publication-figure-sources/v1", "inputs":records,
                "files":[{"file":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in sorted(OUT.iterdir()) if p.suffix in {".pdf",".png"}]}
    (ROOT/"publication"/"figure-manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps({"figures":len(manifest["files"]), "source_records":len(records)}))


if __name__ == "__main__":
    main()
