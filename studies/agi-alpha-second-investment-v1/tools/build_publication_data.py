#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Derive publication tables and figures from sealed outcomes, without simulation."""
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "publication"
PURPLE, TEAL, NAVY = "#7046c7", "#087f8c", "#162238"


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main():
    PUB.mkdir(exist_ok=True)
    (PUB / "figures").mkdir(exist_ok=True)
    production = read("results/production-summary.json")
    campaign = read("results/confirmation-01/campaign.json")
    market = read("market/results/primary-01/summary.json")
    assert market["complete"] and market["completedWorlds"] == 1920
    protocol = read("market/campaign-protocol.json")
    costs = read("market/cost-profiles.json")
    representatives = read("market/results/primary-01/predeclared-representatives.json")
    worlds = [json.loads(line) for line in (ROOT / "market/results/primary-01/compact-worlds.jsonl").read_text().splitlines()]
    priced = [w for w in worlds if w["costProfileId"] != "actual-unknown"]
    positives = [w for w in priced if w["causal"]["B_minus_A_projectInclusiveProfitCents"] > 0]
    reference = {g["costProfileId"] + "/" + g["policyId"]: g for g in market["groups"] if g["conditionId"] == "reference"}
    totals = {
        "paired_worlds": len(worlds), "priced_worlds": len(priced), "unknown_worlds": len(worlds) - len(priced),
        "B_gate_passes": sum(w["qualification"]["B"]["conditionalModeledFinancialGatePassed"] for w in worlds),
        "B_funded_attempts": sum(w["arms"]["B"]["secondInvestmentPaidFromGeneratedResources"] for w in worlds),
        "B_negative_project_deltas": sum(w["causal"]["B_minus_A_projectInclusiveProfitCents"] < 0 for w in priced),
        "B_positive_project_deltas": len(positives),
        "BC_cent_ledger_ties": sum(w["causal"]["B_minus_C_projectInclusiveProfitCents"] == 0 for w in priced),
        "B_failed_integrations": sum(w["arms"]["B"]["secondFailedIntegration"] for w in worlds),
        "B_largest_subcent_residual_usd": max(w["arms"]["B"]["subcentComputeMaximumAbsoluteResidualUSD"] or 0 for w in worlds),
        "actual_customer_receipts_usd": 0,
    }
    representative_rows = []
    for world in representatives["worlds"]:
        paired = world["paired"]
        a, b = paired["arms"]["A"], paired["arms"]["B"]
        x = b["secondInvestment"]
        decision = x["decisions"][0] if x["decisions"] else None
        representative_rows.append({
            "cost_profile": world["costProfileId"], "policy": world["policyId"], "seed": world["seed"],
            "A": a["summary"], "B": b["summary"], "B_second": x,
            "first_decision": decision, "causal": paired["causal"], "qualification": paired["qualification"],
            "A_balances": a["histories"]["balances"], "B_balances": b["histories"]["balances"],
            "A_cash": a["histories"]["cash"], "B_cash": b["histories"]["cash"],
            "A_bills": a["histories"]["bills"], "B_bills": b["histories"]["bills"],
            "A_invoices": a["histories"]["invoices"], "B_invoices": b["histories"]["invoices"],
        })
    data = {"schema": "agi-alpha-second-investment-publication-data/v1", "basis": "Derived sealed evidence, no new simulation",
            "production": production, "production_rows": campaign["rows"], "totals": totals,
            "market_groups": market["groups"], "protocol": protocol, "costs": costs,
            "representatives": representative_rows,
            "positive_path_cases": [{"condition": w["conditionId"], "cost_profile": w["costProfileId"],
                                     "policy": w["policyId"], "seed": w["seed"], "causal": w["causal"],
                                     "qualification": w["qualification"]} for w in positives],
            "source_files": {name: digest(ROOT / name) for name in ["results/confirmation-01/campaign.json",
                "market/results/primary-01/summary.json", "market/campaign-freeze.json", "market/effect-profile.json"]}}
    save_json(PUB / "publication-data.json", data)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.labelcolor": NAVY, "text.color": NAVY,
                         "xtick.color": NAVY, "ytick.color": NAVY, "axes.edgecolor": "#d4d9e3",
                         "figure.facecolor": "white", "savefig.facecolor": "white", "pdf.fonttype": 42})
    families = list(dict.fromkeys(r["family"] for r in campaign["rows"]))
    labels = ["Cryptography", "Eth-account", "Prometheus", "Pydantic\nsettings", "PyYAML", "Uvicorn"]
    fig, ax = plt.subplots(figsize=(8.0, 3.45), layout="constrained")
    for arm, color, marker, offset in [("A", NAVY, "o", -.12), ("B", PURPLE, "s", 0), ("C", TEAL, "^", .12)]:
        values = [next(r["complete_service_wall_seconds"] for r in campaign["rows"] if r["family"] == f and r["arm"] == arm) for f in families]
        ax.plot(np.arange(6) + offset, values, color=color, marker=marker, linewidth=1.2,
                label=f"{arm}: mean {production['arms'][arm]['wall_mean_seconds']:.3f} s")
    ax.set(xticks=range(6), xticklabels=labels, ylim=(0, 1.65), ylabel="Complete service time (seconds)")
    ax.grid(axis="y", color="#edf0f5", linewidth=.8)
    ax.legend(loc="lower left", frameon=False, ncols=3)
    fig.savefig(PUB / "figures/production.pdf"); fig.savefig(PUB / "figures/production.png", dpi=180); plt.close(fig)

    low = next(r for r in representative_rows if r["cost_profile"] == "low" and r["policy"] == "completed-research-replay")
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.4), layout="constrained")
    for arm, color, ls in [("A", NAVY, "-"), ("B", PURPLE, "--")]:
        values = low[f"{arm}_balances"]
        weeks = [x["week"] for x in values]
        axes[0].plot(weeks, [x["cashCents"] / 100 for x in values], color=color, ls=ls, label=arm)
        available = [max(0, min(x["cashCents"] - x["obligationsCents"] - 20000,
                               x["cumulativeCollectionsCents"] - x["accruedCostsCents"] + 36152)) / 100 for x in values]
        axes[1].plot(weeks, available, color=color, ls=ls, label=arm)
    for ax in axes:
        ax.axvline(26, color="#9ba5b6", linewidth=.9)
        ax.axvspan(52, 55, color="#f0eef6")
        ax.set(xlabel="Model week", xlim=(0, 55))
        ax.grid(axis="y", color="#edf0f5", linewidth=.8)
    axes[0].axhline(200, color=TEAL, linewidth=1, label="$200 reserve")
    axes[0].set_ylabel("Enterprise cash (modeled USD)"); axes[0].set_ylim(0, 1100)
    axes[1].set_ylabel("Generated funds (modeled USD)")
    axes[0].legend(loc="lower left", ncols=3, frameon=False)
    axes[1].annotate("Decision: $82.74\nLow cost: $25.97", xy=(26, 82.74), xytext=(5, 170),
                     fontsize=9, arrowprops={"arrowstyle": "-", "color": "#8b93a5"})
    fig.savefig(PUB / "figures/finite-ledger.pdf"); fig.savefig(PUB / "figures/finite-ledger.png", dpi=180); plt.close(fig)

    condition_labels = ["Inherited reference", "Half the reference recurrence", "One fifth of recurrence", "No demand",
                        "$2.50 buyer integration", "$5 buyer integration", "13-week collections", "Cheaper capable AI",
                        "$16 posted price", "Competitor undercutting", "20% integration failure", "$2/week upkeep", "Quality shock"]
    groups = [g for g in market["groups"] if g["costProfileId"] == "reference" and g["policyId"] == "completed-research-replay"]
    fig, ax = plt.subplots(figsize=(8.2, 4.8), layout="constrained")
    for i, group in enumerate(groups):
        dist = group["causal"]["B_minus_A_projectInclusiveProfitCents"]
        ax.plot([dist["p05"] / 100, dist["p95"] / 100], [i, i], color=PURPLE, linewidth=2.3)
        ax.scatter(dist["mean"] / 100, i, color=NAVY, s=25, zorder=3)
    ax.axvline(0, color=TEAL, linewidth=1.2)
    ax.set(yticks=range(13), yticklabels=condition_labels,
           xlabel="B minus A, project-inclusive profit (modeled USD)")
    ax.invert_yaxis(); ax.grid(axis="x", color="#edf0f5", linewidth=.8)
    ax.text(.98, .02, "Point: mean · line: 5th–95th percentiles\n24 frozen seeds per condition; $103.85 cost profile",
            ha="right", va="bottom", transform=ax.transAxes, fontsize=8.5)
    fig.savefig(PUB / "figures/robustness.pdf"); fig.savefig(PUB / "figures/robustness.png", dpi=180); plt.close(fig)

    rows_tex = []
    for cost in ["low", "reference", "high"]:
        group = reference[cost + "/completed-research-replay"]
        dist = group["causal"]["B_minus_A_projectInclusiveProfitCents"]
        counts = group["arms"]["B"]["counts"]
        row = f"{cost.title()} & {costs['profiles'][cost]['totalOneoffCents']/100:.2f} & {counts['secondInvestmentPaidFromGeneratedResources']}/24 & {dist['mean']/100:.2f} & {dist['p05']/100:.2f} & {dist['p95']/100:.2f} & 0/24 \\\\"
        rows_tex.append(row)
    (PUB / "reference-results.tex").write_text("\n".join(rows_tex) + "\n")
    all_rows = []
    for group, label in zip(groups, condition_labels):
        dist = group["causal"]["B_minus_A_projectInclusiveProfitCents"]
        label = label.replace("$", r"\$").replace("%", r"\%")
        all_rows.append(f"{label} & {group['arms']['B']['counts']['secondInvestmentPaidFromGeneratedResources']}/24 & {dist['mean']/100:.2f} & {dist['p05']/100:.2f} & {dist['p95']/100:.2f} \\\\")
    (PUB / "robustness-results.tex").write_text("\n".join(all_rows) + "\n")
    save_json(PUB / "publication-build-receipt.json", {"schema": "publication-data-build/v1", "new_simulated_worlds": 0,
              "source_files": data["source_files"], "totals": totals,
              "outputs": {str(p.relative_to(PUB)): digest(p) for p in sorted((PUB / "figures").iterdir())}})
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
