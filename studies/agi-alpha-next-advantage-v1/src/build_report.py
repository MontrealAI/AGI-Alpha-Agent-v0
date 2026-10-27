# SPDX-License-Identifier: Apache-2.0
"""Build exact-data scientific figures, paper tables and bilingual companion data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/next-advantage-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/figures"
COLORS = {
    "beta": "#58677a",
    "v1": "#54a39a",
    "v2": "#006b63",
    "composed": "#006b63",
    "shuffled": "#b9794b",
    "beta_plus": "#a0a8b0",
}
LABELS = {
    "beta": "Beta portfolio",
    "v1": "Productive v1",
    "v2": "Gym v2",
    "composed": "v2 + risk ranking",
    "shuffled": "Reversed weights",
    "beta_plus": "Expanded grid",
}
LABELS_FR = {
    "beta": "Portefeuille Bêta",
    "v1": "v1 issue du travail productif",
    "v2": "v2 du Gym",
    "composed": "v2 + classement par risque",
    "shuffled": "Poids inversés",
    "beta_plus": "Grille élargie",
}
POLICY_LABELS = {
    "beta": "Beta / initial offer",
    "private": "Private retention",
    "shared": "Shared retention",
    "shared_gym": "Shared + optional Gym",
    "opportunity": "Shared + new offering",
    "beta_open": "Beta / both offers",
    "private_open": "Private / both offers",
    "library": "Ordinary library",
    "beta_upgrade": "Expanded-grid Beta",
    "opportunity_upgrade": "Shared / expanded-grid Beta",
    "surplus_expansion": "Surplus-funded capacity",
}
SCENARIO_LABELS = {
    "central": "Central assumptions",
    "thin_demand": "Thin demand",
    "costly_delivery": "6x delivery / R&D cost",
    "adverse_market": "Adverse market",
    "congested": "Congested demand",
    "fast_obsolescence": "14-day obsolescence",
    "fragile_learning": "Fragile learning / transfer",
}


def read(path: str) -> Any:
    return json.loads((ROOT / path).read_text())


def save(fig: Any, name: str) -> None:
    fig.savefig(OUT / (name + ".pdf"), bbox_inches="tight")
    fig.savefig(OUT / (name + ".png"), dpi=170, bbox_inches="tight")
    plt.close(fig)


def tex_escape(s: str) -> str:
    for a, b in (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")):
        s = s.replace(a, b)
    return s


def paired(cal: dict[str, Any], offer: str, a: str, b: str) -> dict[str, Any]:
    one = {r["case_id"]: r["objective"] for r in cal["offerings"][offer][a]["confirmation_records"]}
    two = {r["case_id"]: r["objective"] for r in cal["offerings"][offer][b]["confirmation_records"]}
    values = np.array([1 - one[k] / two[k] for k in sorted(one)])
    rng = np.random.default_rng(921)
    boot = np.mean(rng.choice(values, (5000, len(values))), axis=1)
    return {
        "mean": float(values.mean()),
        "ci": [float(x) for x in np.quantile(boot, [0.025, 0.975])],
        "wins": int(np.sum(values > 1e-10)),
        "ties": int(np.sum(np.abs(values) <= 1e-10)),
        "losses": int(np.sum(values < -1e-10)),
    }


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#243647",
            "text.color": "#172d3b",
            "axes.edgecolor": "#bac2c7",
            "pdf.fonttype": 42,
        }
    )
    summary = read("evidence/numerical/summary.json")
    cal = read("evidence/numerical/economic_calibration.json")
    economic = read("evidence/economics/economic_results.json")
    frontier = read("evidence/numerical/quality_frontier.json")
    cfg = read("config/economics.json")
    metrics: dict[str, Any] = {"numerical": {}, "economic": {}}

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.8), layout="constrained")
    comparisons = [
        ("v1", "beta", "Productive v1 / Beta"),
        ("v2", "beta", "Gym v2 / Beta"),
        ("v2", "v1", "Gym increment / v1"),
        ("v2", "shuffled", "Learned / reversed weights"),
    ]
    for ax, offer in zip(axes, ("nominal", "robust")):
        for i, (a, b, label) in enumerate(comparisons):
            if offer == "robust" and a == "v2":
                a = "composed"
            result = paired(cal, offer, a, b)
            metrics["numerical"][offer + ":" + a + ":" + b] = result
            ax.errorbar(
                result["mean"] * 100,
                i,
                xerr=[[100 * (result["mean"] - result["ci"][0])], [100 * (result["ci"][1] - result["mean"])]],
                fmt="o",
                color=COLORS[a],
                capsize=4,
                ms=6,
            )
            ax.text(result["ci"][1] * 100 + 0.5, i, f"{result['mean'] * 100:.2f}%", va="center", fontsize=8)
        ax.axvline(0, color="#bac2c7", lw=1)
        ax.set(
            yticks=range(4),
            yticklabels=[c[2] for c in comparisons],
            xlabel="Mean objective reduction (%)",
            title="Nominal schedule" if offer == "nominal" else "Risk-aware schedule",
            xlim=(-1, 15),
        )
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.18)
    save(fig, "causal-comparisons")

    candidates = read("evidence/numerical/all_learning_candidates.json")
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.5), layout="constrained")
    for version in ("v1", "v2"):
        records = [r for r in candidates if r["version"] == version]
        generations = sorted({r["generation"] for r in records})
        first = min(r["loss"] for r in records if r["generation"] == generations[0])
        minimum = []
        for g in generations:
            minimum.append(min(r["loss"] for r in records if r["generation"] <= g) / first)
        axes[0].plot(np.array(generations) + 1, minimum, "o-", label=version, color=COLORS[version])
    axes[0].set(
        title="Actual parameter search", xlabel="Generation", ylabel="Best training loss / first-generation best"
    )
    axes[0].legend(frameon=False)
    strata = ("producer", "recipient", "scale", "shift")
    for offset, mode in ((-0.18, "v1"), (0.18, "v2")):
        values = [100 * summary["confirmation"]["nominal"][mode]["strata"][s]["mean_gain_vs_beta"] for s in strata]
        axes[1].bar(np.arange(4) + offset, values, 0.34, color=COLORS[mode], label=LABELS[mode])
    axes[1].set(
        xticks=range(4),
        xticklabels=["Producer", "Recipient B", "Larger", "Shifted"],
        ylabel="Objective reduction vs Beta (%)",
        title="Fresh nominal transfer: 20 cases per stratum",
    )
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.18)
    save(fig, "learning-transfer")

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.5), layout="constrained")
    for ax, offer in zip(axes, ("nominal", "robust")):
        for mode in ("beta", "v1", "v2" if offer == "nominal" else "composed"):
            rows = sorted(
                [
                    r
                    for r in frontier["rows"]
                    if r["split"] == "confirmation"
                    and r["stratum"] == "all"
                    and r["offering"] == offer
                    and r["mode"] == mode
                ],
                key=lambda r: r["improvement_target"],
            )
            ax.plot(
                [r["improvement_target"] * 100 for r in rows],
                [r["acceptance_rate"] * 100 for r in rows],
                "o-",
                color=COLORS[mode],
                label=LABELS[mode],
            )
        ax.set(
            xlabel="Required improvement over EDD incumbent (%)",
            ylabel="Fresh cases meeting target (%)",
            title="Nominal quality frontier" if offer == "nominal" else "Robust quality frontier",
            ylim=(0, 105),
        )
        ax.grid(alpha=0.18)
        ax.legend(frameon=False, loc="lower left")
    save(fig, "quality-frontier")

    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    ax.set(xlim=(0, 10.5), ylim=(0, 4.6))
    ax.axis("off")
    nodes = [
        (0.1, 2.9, "Productive campaign", "8 delivered synthetic cases\n512 parameter evaluations\nA: counted once"),
        (3.7, 2.9, "Executable v1", "7 learned dispatch weights\nVersioned, reloadable bytes\nNot a prose summary"),
        (7.3, 2.9, "Optional Gym v2", "24 diverse practice cases\n2,880 evaluations\nAll 184 candidates retained"),
        (0.1, 0.5, "Fresh recipient B", "40 jobs / 4 machines\n20 unseen recipient cases\n9.96% nominal mean gain"),
        (
            3.7,
            0.5,
            "Risk-aware offering",
            "Same hard constraints\nFresh duration scenarios\nCompetent Beta also eligible",
        ),
        (
            7.3,
            0.5,
            "Enterprise decision",
            "Deliver / retain / train / share\nLaunch / defer / retire / stop\nMarkets explicitly simulated",
        ),
    ]
    for x, y, title, body in nodes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                3.0,
                1.55,
                boxstyle="round,pad=0.05,rounding_size=.07",
                facecolor="#eef6f4",
                edgecolor="#7facaa",
                lw=0.8,
            )
        )
        ax.text(x + 0.15, y + 1.22, title, weight="bold", fontsize=10)
        ax.text(x + 0.15, y + 0.9, body, fontsize=9, va="top", linespacing=1.5)
    for start, end in (
        ((3.15, 3.7), (3.62, 3.7)),
        ((6.75, 3.7), (7.22, 3.7)),
        ((3.15, 1.3), (3.62, 1.3)),
        ((6.75, 1.3), (7.22, 1.3)),
    ):
        ax.annotate("", end, start, arrowprops={"arrowstyle": "->", "color": "#006b63", "lw": 1.4})
    ax.annotate(
        "",
        (1.6, 2.1),
        (8.8, 2.85),
        arrowprops={"arrowstyle": "->", "color": "#b9794b", "connectionstyle": "arc3,rad=0.15"},
    )
    ax.text(4.5, 2.3, "Serialized policy transfer; synthetic identities", fontsize=8.5, ha="center", color="#975a35")
    save(fig, "productive-lineage")

    hero = read("evidence/numerical/confirmation/recipient-51001.json")
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 4.8), sharex=True, layout="constrained")
    fam_colors = ["#006b63", "#54a39a", "#b9794b", "#6e7e91", "#b8a26e", "#a0b8c8"]
    for ax, key, label in zip(
        axes, ("nominal/beta", "nominal/v2"), ("Fresh recipient: Beta portfolio", "Same mission: loaded v2 policy")
    ):
        result = hero["results"][key]
        sol = result.get("solve", result)
        schedule = sol.get("schedule", result.get("schedule"))
        if schedule is None:
            raise ValueError("Unrecognized delivered-schedule schema")
        for j in schedule["jobs"]:
            color = fam_colors[hero["instance"]["family"][j["job"]] % len(fam_colors)]
            ax.broken_barh(
                [(j["start"], j["finish"] - j["start"])],
                (j["machine"] - 0.32, 0.64),
                facecolors=color,
                edgecolors="white",
                linewidth=0.35,
            )
        ax.set(yticks=range(4), yticklabels=["M1", "M2", "M3", "M4"], title=label)
        ax.grid(axis="x", alpha=0.15)
    axes[-1].set_xlabel("Synthetic processing-time units; colours identify setup families")
    save(fig, "delivered-schedules")

    summaries = {(r["scenario"], r["policy"]): r for r in economic["summaries"]}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.1), layout="constrained")
    policies = ("beta", "private", "shared", "shared_gym", "beta_open", "opportunity")
    for ax, scenario in zip(axes, ("central", "adverse_market")):
        values = [summaries[scenario, p]["profit_usd"]["mean"] / 1000 for p in policies]
        error = [1.96 * summaries[scenario, p]["profit_usd"]["se"] / 1000 for p in policies]
        ax.barh(range(len(policies)), values, xerr=error, color=["#58677a"] * 4 + ["#b9794b", "#006b63"], capsize=3)
        ax.set(
            yticks=range(len(policies)),
            yticklabels=[POLICY_LABELS[p] for p in policies],
            xlabel="90-day modeled accrued profit (thousand USD)",
            title=SCENARIO_LABELS[scenario],
        )
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.18)
    save(fig, "enterprise-comparisons")

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9), layout="constrained")
    demands = sorted({r["daily_expected_leads"] for r in economic["frontier"]})
    costs = sorted({r["cost_scale"] for r in economic["frontier"]})
    for ax, policy in zip(axes, ("beta_open", "opportunity")):
        values = np.array(
            [
                [
                    next(
                        r["mean_profit_usd"] / 1000
                        for r in economic["frontier"]
                        if r["policy"] == policy and r["daily_expected_leads"] == demand and r["cost_scale"] == cost
                    )
                    for demand in demands
                ]
                for cost in costs
            ]
        )
        im = ax.imshow(values, aspect="auto", cmap="BrBG", vmin=-20, vmax=max(values.max(), 1))
        for y in range(len(costs)):
            for x in range(len(demands)):
                ax.text(
                    x,
                    y,
                    f"{values[y, x]:.0f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if values[y, x] > 500 or values[y, x] < 125 else "#172d3b",
                )
        ax.set(
            xticks=range(len(demands)),
            xticklabels=[f"{d:.2g}" for d in demands],
            yticks=range(len(costs)),
            yticklabels=[f"{c:g}x" for c in costs],
            xlabel="Assumed qualified leads / day",
            ylabel="Marginal delivery and R&D cost multiplier",
            title=POLICY_LABELS[policy],
        )
        fig.colorbar(im, ax=ax, shrink=0.7, label="Modeled profit (USD thousands)")
    save(fig, "commercial-frontier")

    supplement = read("evidence/expansion_frontier.json")
    compute = read("evidence/compute_economics.json")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), layout="constrained")
    for setting, label, color in (
        ("executed_portfolio", "Fixed-budget Beta", "#006b63"),
        ("hypothetical_best_capability_catchup", "Hypothetical Beta catch-up", "#b9794b"),
    ):
        rows = sorted(
            [
                r
                for r in supplement["paired_comparisons"]
                if r["market"] == "central"
                and r["beta_setting"] == setting
                and r["intervention"] == "opportunity"
                and r["control"] == "beta_open"
            ],
            key=lambda r: r["tier"],
        )
        x = [r["tier"] * 100 for r in rows]
        axes[0].plot(x, [r["mean_profit_difference_usd"] / 1000 for r in rows], "o-", color=color, label=label)
        axes[0].fill_between(
            x,
            [r["paired_mc_95"][0] / 1000 for r in rows],
            [r["paired_mc_95"][1] / 1000 for r in rows],
            color=color,
            alpha=0.12,
        )
    axes[0].set(
        xlabel="Secondary quality target (%)",
        ylabel="Incremental 90-day modeled profit (USD thousands)",
        title="Learning value depends on the alternative",
    )
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].axhline(0, color="#aaa", lw=0.8)
    for j, control in enumerate(("beta48", "beta144")):
        rows = [
            next(
                r
                for r in compute["paired_comparisons"]
                if r["tier"] == 0.3 and r["offer"] == offer and r["control"] == control
            )
            for offer in ("nominal", "robust")
        ]
        x = np.arange(2) + (-0.16 if j == 0 else 0.16)
        y = [r["increment_per_booked_job_usd"] for r in rows]
        axes[1].bar(x, y, 0.29, color="#54a39a" if j == 0 else "#b9794b", label="Learned vs " + control)
    axes[1].set(
        xticks=[0, 1],
        xticklabels=["Nominal", "Robust"],
        ylabel="Conditional contribution / booked job (USD)",
        title="Fresh 12-case / 30% quality contract",
    )
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].axhline(0, color="#aaa", lw=0.8)
    save(fig, "investment-boundary")

    econ_rows = []
    for r in economic["summaries"]:
        def mean(key: str) -> float:
            return float(r[key]["mean"])
        econ_rows.append(
            {
                "scenario": r["scenario"],
                "policy": r["policy"],
                "replicates": r["n"],
                "collections": mean("collections_usd"),
                "expenses": mean("expenses_usd"),
                "profit": mean("profit_usd"),
                "profit_ci_low": mean("profit_usd") - 1.96 * r["profit_usd"]["se"],
                "profit_ci_high": mean("profit_usd") + 1.96 * r["profit_usd"]["se"],
                "available_funds": mean("available_usd"),
                "loss_probability": r["loss_probability"],
                "accepted_jobs": mean("technical_throughput"),
                "new_offering_jobs": r["mean_accepted"]["robust"],
                "cost_a": r["mean_by_bucket"]["A"],
                "cost_b": r["mean_by_bucket"]["B"],
                "cost_c": r["mean_by_bucket"]["C"],
                "cash_profit": mean("cash_profit_usd"),
                "receivables": mean("receivables_usd"),
                "earned_revenue": mean("collections_usd") + mean("receivables_usd"),
                "ending_cash": cfg["capital_usd"] + mean("cash_profit_usd"),
                "seed_capital": cfg["capital_usd"],
                "obligations": 0,
                "reserves": cfg["reserve_usd"],
            }
        )
    numerical_rows = []
    for offer in ("nominal", "robust"):
        for mode in ("beta", "v1", "v2" if offer == "nominal" else "composed", "shuffled", "beta_plus"):
            row = summary["confirmation"][offer][mode]
            records = cal["offerings"][offer][mode]["confirmation_records"]
            numerical_rows.append(
                {
                    "id": offer + "_" + mode,
                    "label": {
                        "en": f"{offer.title()} / {LABELS[mode]}",
                        "fr": f"{'Nominal' if offer == 'nominal' else 'Robuste'} / {LABELS_FR[mode]}",
                    },
                    "n": row["n"],
                    "accepted": row["accepted"],
                    "acceptance_rate": row["acceptance_rate"],
                    "objective_mean": float(np.mean([r["objective"] for r in records])),
                    "runtime_s": row["mean_solve_seconds"],
                    "notes": {
                        "en": f"{row['mean_paired_gain_vs_beta'] * 100:.2f}% mean reduction versus matched Beta",
                        "fr": f"Réduction moyenne de {row['mean_paired_gain_vs_beta'] * 100:.2f} % par rapport à Bêta comparable",
                    },
                }
            )
    source_urls = [
        ("Official Astra model configuration", "https://developers.openai.com/api/docs/models/gpt-6-astra"),
        ("Official Terra model configuration", "https://developers.openai.com/api/docs/models/gpt-6.1-terra"),
        (
            "AFG Québec 2026 professional fee guideline",
            "https://afg.quebec/wp-content/uploads/2026/01/AFG_Bareme_des_honoraires_2026.pdf",
        ),
        (
            "Arinti scheduling consulting offer",
            "https://marketplace.microsoft.com/fr-fr/marketplace/consulting-services/arinti.production-scheduling-optimization",
        ),
        ("PyJobShop primary research", "https://arxiv.org/abs/2502.13483"),
        (
            "Existing owner coordination",
            "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6441643134",
        ),
    ]
    source_fr = [
        "Configuration officielle du modèle Astra",
        "Configuration officielle du modèle Terra",
        "Barème des honoraires professionnels 2026 de l’AFG Québec",
        "Offre de conseil en ordonnancement d’Arinti",
        "Recherche originale PyJobShop",
        "Coordination avec les responsables existants",
    ]
    data = {
        "title": "The Enterprise That Invents Its Next Advantage",
        "meta": {
            "date": "2026-10-27",
            "source_commit": "80b345828f34fd8a6e592977dd17ef37141305f4",
            "run_id": "next-advantage-v1",
            "currency": "USD",
            "status": {
                "en": "Executed numerical study; conditional enterprise simulation; live qualification remains open",
                "fr": "Étude numérique exécutée; entreprise simulée sous hypothèses; qualification réelle à établir",
            },
            "artifacts": [
                {
                    "label": {"en": "Research paper (PDF)", "fr": "Article de recherche (PDF)"},
                    "href": "../paper/enterprise-next-advantage.pdf",
                },
                {
                    "label": {"en": "LaTeX source", "fr": "Source LaTeX"},
                    "href": "../paper/enterprise-next-advantage.tex",
                },
                {
                    "label": {"en": "Evidence manifest", "fr": "Manifeste des preuves"},
                    "href": "../evidence_manifest.json",
                },
            ],
            "commands": [
                "python src/numerical.py",
                "python src/economics.py",
                "python src/native_integration.py --input evidence/economics/native_input.json --output evidence/native-account --self-test",
                "python src/build_report.py",
                "python web/build_web.py --strict",
            ],
        },
        "summary": {
            "en": "Useful experience produced an executable specialist that improved fresh schedules. Additional Gym practice helped modestly. Cheap generic search could catch up, and a more profitable service portfolio did not require the specialist. The commercial question is which improvement a buyer values enough to fund.",
            "fr": "L’expérience productive a produit un spécialiste exécutable améliorant de nouveaux horaires. L’entraînement supplémentaire a apporté un gain modeste. Une recherche générique peu coûteuse pouvait le rattraper, et un portefeuille de services plus rentable n’exigeait pas ce spécialiste. La question commerciale est de savoir quelle amélioration un client est prêt à financer.",
        },
        "numerical": {
            "description": {
                "en": "80 fresh cases, 32–64 jobs, 3–4 machines. No live frontier calls or customer sales. Technical acceptance is separate from buyer acceptance.",
                "fr": "80 nouveaux cas, 32 à 64 tâches, 3 à 4 machines. Aucun appel direct à un modèle de pointe ni vente réelle. L’acceptation technique est distincte de celle du client.",
            },
            "rows": numerical_rows,
            "metric": {
                "en": "Normalized scheduling objective; lower is better",
                "fr": "Objectif d’ordonnancement normalisé; une valeur plus faible est préférable",
            },
            "lower_is_better": True,
        },
        "economics": {
            "scenarios": [
                {
                    "id": k,
                    "label": {
                        "en": v,
                        "fr": {
                            "central": "Hypothèses centrales",
                            "thin_demand": "Faible demande",
                            "costly_delivery": "Coûts multipliés par 6",
                            "adverse_market": "Marché défavorable",
                            "congested": "Demande saturant la capacité",
                            "fast_obsolescence": "Obsolescence en 14 jours",
                            "fragile_learning": "Apprentissage et transfert fragiles",
                        }[k],
                    },
                    "description": {
                        "en": "Conditional modeled market; not observed demand.",
                        "fr": "Marché modélisé sous hypothèses; demande non observée.",
                    },
                }
                for k, v in SCENARIO_LABELS.items()
            ],
            "policies": [
                {
                    "id": k,
                    "label": {
                        "en": v,
                        "fr": {
                            "beta": "Bêta / offre initiale",
                            "private": "Conservation privée",
                            "shared": "Conservation partagée",
                            "shared_gym": "Partage et Gym facultatif",
                            "opportunity": "Partage et nouvelle offre",
                            "beta_open": "Bêta / deux offres",
                            "private_open": "Privé / deux offres",
                            "library": "Bibliothèque ordinaire",
                            "beta_upgrade": "Bêta à grille élargie",
                            "opportunity_upgrade": "Partage / Bêta à grille élargie",
                            "surplus_expansion": "Capacité financée par l’excédent",
                        }[k],
                    },
                    "description": {
                        "en": "Frozen finite decision policy; training and investment are optional.",
                        "fr": "Politique de décision finie et figée; entraînement et investissement facultatifs.",
                    },
                }
                for k, v in POLICY_LABELS.items()
            ],
            "summary": econ_rows,
        },
        "lineage": [
            {
                "id": "work",
                "step": "01",
                "label": {"en": "Eight productive jobs", "fr": "Huit missions productives"},
                "description": {
                    "en": "Saved inputs, schedules and independent verdicts; v1 training counted once in delivery.",
                    "fr": "Entrées, horaires et verdicts indépendants conservés; apprentissage v1 compté une fois dans la livraison.",
                },
                "status": {"en": "Executed; sales simulated", "fr": "Exécuté; ventes simulées"},
                "artifacts": [
                    {
                        "label": {"en": "Origin deliveries", "fr": "Livrables d’origine"},
                        "href": "../evidence/numerical/productive_deliveries.json",
                    }
                ],
            },
            {
                "id": "learn",
                "step": "02",
                "label": {"en": "v1 → optional v2", "fr": "v1 → v2 facultative"},
                "description": {
                    "en": "Seven learned parameters; 512 productive and 2,880 Gym evaluations. Unsuccessful candidates retained.",
                    "fr": "Sept paramètres appris; 512 évaluations productives et 2 880 au Gym. Candidats infructueux conservés.",
                },
                "status": {"en": "Actual numerical learning", "fr": "Apprentissage numérique réel"},
                "artifacts": [
                    {"label": {"en": "Policy v2", "fr": "Politique v2"}, "href": "../evidence/numerical/policy_v2.json"}
                ],
            },
            {
                "id": "transfer",
                "step": "03",
                "label": {"en": "Fresh recipient", "fr": "Nouveau destinataire"},
                "description": {
                    "en": "Agent B reloads executable policy bytes on a fresh 40-job mission; identities are synthetic.",
                    "fr": "L’agent B recharge la politique sur une mission inédite de 40 tâches; les identités sont synthétiques.",
                },
                "status": {"en": "Executed local transfer", "fr": "Transfert local exécuté"},
                "artifacts": [
                    {
                        "label": {"en": "Fresh mission", "fr": "Nouvelle mission"},
                        "href": "../evidence/numerical/confirmation/recipient-51001.json",
                    }
                ],
            },
            {
                "id": "offer",
                "step": "04",
                "label": {"en": "Risk-aware offering", "fr": "Offre intégrant le risque"},
                "description": {
                    "en": "Compose dispatch and uncertainty replay. Beta can also offer this service; unique product creation is not established.",
                    "fr": "Combiner l’ordonnancement et les scénarios d’incertitude. Bêta peut aussi proposer ce service; une création exclusive n’est pas démontrée.",
                },
                "status": {
                    "en": "Technical execution; economics conditional",
                    "fr": "Exécution technique; économie conditionnelle",
                },
                "artifacts": [
                    {
                        "label": {"en": "Matched enterprises", "fr": "Entreprises comparables"},
                        "href": "../evidence/economics/economic_results.json",
                    }
                ],
            },
        ],
        "findings": [
            {
                "en": "Gym v2 reduces the nominal objective by 9.04% versus the bounded Beta portfolio; productive v1 already supplies most of the gain.",
                "fr": "La politique v2 réduit l’objectif nominal de 9,04 % face au portefeuille Bêta borné; v1 fournit déjà l’essentiel du gain.",
            },
            {
                "en": "A threefold generic search budget can erase the average nominal advantage. Learning is an option whose complete cost must beat that alternative.",
                "fr": "Un budget de recherche générique triplé peut effacer l’avantage nominal moyen. Le coût complet de l’apprentissage doit donc battre cette solution.",
            },
            {
                "en": "The ordinary library and graph-labeled policy have identical content, permissions and results. No graph-specific premium is claimed.",
                "fr": "La bibliothèque ordinaire et la politique de graphe ont les mêmes contenus, droits et résultats. Aucun avantage spécifique du graphe n’est revendiqué.",
            },
            {
                "en": "Native signatures, journal and cost accounting execute; the current protected runtime correctly refuses arbitrary scheduling-capsule admission.",
                "fr": "Les signatures, le journal et la comptabilité natifs sont exécutés; le runtime protégé refuse correctement l’admission arbitraire d’une capsule d’ordonnancement.",
            },
        ],
        "operator_findings": [
            {
                "en": "Begin with a bounded schedule-design package using customer-approved inputs and a fixed independent acceptance contract. Test willingness to pay before forecasting revenue.",
                "fr": "Commencer par un mandat d’ordonnancement borné, avec données approuvées et acceptation indépendante fixée. Tester la volonté de payer avant toute prévision de revenus.",
            },
            {
                "en": "Compare retained v1, optional Gym and additional generic search at complete cost. Launch the robust service only after a buyer values its deliverable and its demand survives a paid pilot.",
                "fr": "Comparer v1, le Gym facultatif et la recherche générique au coût complet. Lancer le service robuste seulement après validation du besoin par un pilote payant.",
            },
        ],
        "sources": [
            {"title": {"en": title, "fr": source_fr[i]}, "url": url} for i, (title, url) in enumerate(source_urls)
        ],
    }
    data["findings"].append(
        {
            "en": "A separately frozen 12-case check gives Beta144 11/12 successes at the 30% quality tier, versus 10/12 for learned48, in both offerings. At this tier, cheaper training cannot repair the negative operating contribution relative to the stronger ordinary alternative.",
            "fr": "Un contrôle distinct sur 12 cas donne à Bêta144 11 réussites sur 12 au seuil de qualité de 30 %, contre 10 sur 12 pour la politique apprise à 48 candidats, dans les deux offres. À ce seuil, un entraînement moins coûteux ne corrige pas la contribution d’exploitation négative face à la solution ordinaire renforcée.",
        }
    )
    data["meta"]["artifacts"].extend(
        [
            {
                "label": {"en": "Fresh stronger-Beta evidence", "fr": "Preuves inédites sur Bêta renforcé"},
                "href": "../evidence/numerical/beta144_confirmation/summary.json",
            },
            {
                "label": {"en": "Program cost sensitivity", "fr": "Sensibilité au coût du programme"},
                "href": "../evidence/compute_economics.json",
            },
        ]
    )
    data["lineage"][1]["artifacts"].extend(
        [
            {
                "label": {"en": "Productive policy v1", "fr": "Politique productive v1"},
                "href": "../evidence/numerical/policy_v1.json",
            },
            {
                "label": {"en": "All learning candidates", "fr": "Tous les candidats d’apprentissage"},
                "href": "../evidence/numerical/all_learning_candidates.json",
            },
        ]
    )
    for row in numerical_rows:
        row["notes"]["fr"] = row["notes"]["fr"].replace(".", ",")
    (ROOT / "evidence/report_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "evidence/report_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    lines = []
    for r in numerical_rows:
        lines.append(
            f"{tex_escape(r['label']['en'])} & {r['accepted']}/{r['n']} & {r['objective_mean']:.3f} & {r['runtime_s']:.3f} \\"
        )
    (ROOT / "paper/numerical-table.tex").write_text("\n".join(line + chr(92) for line in lines) + "\n")
    lines = []
    for p in ("beta", "private", "shared", "shared_gym", "beta_open", "opportunity"):
        r = summaries["central", p]
        lines.append(
            f"{tex_escape(POLICY_LABELS[p])} & {r['collections_usd']['mean']:,.0f} & {r['expenses_usd']['mean']:,.0f} & {r['profit_usd']['mean']:,.0f} & {r['available_usd']['mean']:,.0f} \\"
        )
    (ROOT / "paper/economic-table.tex").write_text("\n".join(line + chr(92) for line in lines) + "\n")
    print("Scientific figures, exact-data tables and bilingual report data generated")


if __name__ == "__main__":
    build()
