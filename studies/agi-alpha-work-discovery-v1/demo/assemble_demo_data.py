# SPDX-License-Identifier: Apache-2.0
"""Assemble all declared market cells without selecting a favorable outcome."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parents[1]
DEMO = BASE / "demo"
ECONOMICS = BASE / "outputs" / "economics-primary"
SEED_CENTS = 100_000
RESERVE_CENTS = 20_000


def bilingual(en: str, fr: str) -> dict[str, str]:
    return {"en": en, "fr": fr}


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def usd(cents: int | float) -> str:
    return f"USD {cents / 100:,.2f}"


def main() -> None:
    data = load(DEMO / "frozen-data-nonmarket.json")
    paper = load(ECONOMICS / "paper-summary.json")
    summary = load(ECONOMICS / "summary.json")
    columns = load(ECONOMICS / "weekly-schema.json")["columns"]
    histories: dict[tuple[str, int, str], list[list[Any]]] = {}
    with (ECONOMICS / "weekly-histories.ndjson").open() as stream:
        for line in stream:
            history = json.loads(line)
            key = history["cell"], history["seed"], history["policy"]
            assert key not in histories
            histories[key] = history["rows"]
    assert len(paper["cells"]) == 24 and len(histories) == 1536
    assert summary["worlds"] == 384 and summary["policiesPerWorld"] == 4
    assert paper["actualCollectionsCents"] == 0
    worlds = {(cell, seed) for cell, seed, _ in histories}
    # All policies remain at A because their investment gates never pass.
    assert all(histories[cell, seed, "A"] == histories[cell, seed, arm] for cell, seed in worlds for arm in "BCD")
    costs = {item["costBundle"]: item for item in paper["unitCostScenarios"]}
    scenarios = []
    checked_rows = 0
    for index, cell in enumerate(paper["cells"], 1):
        stats = cell["policies"]["A"]
        assert all(cell["policies"][arm] == stats for arm in "BCD")
        assert all(
            stats[key] == 0 for key in ("positiveOperatingSeeds", "firstInvestmentSeeds", "secondInvestmentSeeds")
        )
        opening = sum(costs[cell["costBundle"]]["openingItemsCents"].values())
        rows = [dict(zip(columns, row, strict=True)) for row in histories[cell["id"], 1, "A"]]
        assert len(rows) == 52
        ledger = [
            {
                "period": bilingual("Opening", "Ouverture"),
                "collectionsUsd": 0,
                "deliveryAndBusinessUsd": opening / 100,
                "accruedOperatingCostUsd": 0,
                "investmentUsd": 0,
                "reservesAndObligationsUsd": RESERVE_CENTS / 100,
                "cashUsd": (SEED_CENTS - opening) / 100,
                "availableUsd": 0,
            }
        ]
        for row in rows:
            paid = opening + row["operatingCostCents"] - row["unpaidCents"]
            assert row["cashCents"] == SEED_CENTS + row["simulatedCollectionsCents"] - paid - row["investmentCents"]
            earned = max(0, row["simulatedCollectionsCents"] - row["operatingCostCents"] - row["investmentCents"])
            available = max(0, min(row["cashCents"] - RESERVE_CENTS - row["unpaidCents"], earned))
            assert available == row["availableInvestmentCents"]
            ledger.append(
                {
                    "period": bilingual(f"Week {row['week']}", f"Semaine {row['week']}"),
                    "collectionsUsd": row["simulatedCollectionsCents"] / 100,
                    "deliveryAndBusinessUsd": paid / 100,
                    "accruedOperatingCostUsd": row["operatingCostCents"] / 100,
                    "investmentUsd": row["investmentCents"] / 100,
                    "reservesAndObligationsUsd": (RESERVE_CENTS + row["unpaidCents"]) / 100,
                    "cashUsd": row["cashCents"] / 100,
                    "availableUsd": available / 100,
                }
            )
            checked_rows += 1
        last = rows[-1]
        accepted = sum(row["accepted"] for row in rows)
        mean_jobs = stats["acceptedJobs"]["mean"]
        mean_collections = stats["simulatedCollectionsCents"]["mean"]
        mean_operating = stats["simulatedOperatingProfitCents"]["mean"]
        mean_project = stats["simulatedProjectProfitCents"]["mean"]
        demand_fr = {"low": "faible", "reference": "de référence", "high": "forte"}[cell["demand"]]
        cost_fr = {"low": "faibles", "reference": "de référence"}[cell["costBundle"]]
        competitor_fr = {"strong": "plus efficace", "equal": "équivalent"}[cell["competitorStrength"]]
        tariff = costs[cell["costBundle"]]["tariff"]["priceCents"]
        conclusion_en = (
            f"Across 16 seeds: {mean_jobs:g} accepted jobs on average, {usd(mean_collections)} simulated collections, "
            f"{usd(mean_operating)} operating result and {usd(mean_project)} project result. "
            f"No positive operating result or funded investment; insolvency in {stats['insolvencySeeds']}/16 seeds. "
            f"The ledger below uses fixed seed 1: {accepted} accepted jobs. Policies A/B/C/D have identical histories "
            "because all stay with the retained conventional capability A."
        )
        conclusion_fr = (
            f"Sur 16 graines : {mean_jobs:g} travaux acceptés en moyenne, {usd(mean_collections)} de recettes simulées, "
            f"{usd(mean_operating)} de résultat d’exploitation et {usd(mean_project)} de résultat du projet. "
            f"Aucun résultat d’exploitation positif ni investissement financé ; insolvabilité dans {stats['insolvencySeeds']}/16 graines. "
            f"Le registre ci-dessous utilise la graine fixe 1 : {accepted} travaux acceptés. Les historiques A/B/C/D sont identiques, "
            "car toutes les politiques conservent la capacité conventionnelle A."
        )
        assumptions_en = (
            f"This cell assumes {cell['demand']} demand ({cell['arrivalProbability']:g} weekly probability for each of 24 buyers), "
            f"{cell['integrationMinutes']} customer integration minutes, a {cell['competitorStrength']} competitor and "
            f"the {cell['costBundle']} cost bundle. The fixed tariff is {usd(tariff)} per accepted job; "
            f"historical discovery, failed discovery, inference and ordinary setup total {usd(opening)} at opening. "
            "These are sensitivity assumptions, not observed demand, willingness to pay or a quoted service price. "
            "Human-only durations of 5/15/45 minutes and residual attention are modeled; the hourly wage anchor is "
            "USD 135,980 / assumed 2,080 hours = USD 65.375, excluding benefits. Source availability 0.5 is a scenario "
            "condition from the six frozen questions, not a population estimate. Competitors can copy and cut prices "
            "in week 20. Invoice delay/default, accrued unpaid bills and a USD 200 reserve are retained. "
            "The chart shows cash remaining from the USD 1,000 seed separately from operating-earned investable funds. "
            "Table amounts are cumulative except balances, reserve and unpaid obligations; costs paid include opening costs. "
            "Cash = seed + collections − noninvestment costs paid − investments. Receivables are not collections. "
            "Available investment is limited both by cash after reserve/obligations and by operating earnings."
        )
        assumptions_fr = (
            f"Cette cellule suppose une demande {demand_fr} (probabilité hebdomadaire {cell['arrivalProbability']:g} pour chacun "
            f"des 24 acheteurs), {cell['integrationMinutes']} minutes d’intégration client, un concurrent {competitor_fr} "
            f"et des coûts {cost_fr}. Le tarif fixe est de {usd(tariff)} par travail accepté ; recherche historique, "
            f"essais infructueux, inférence et mise en place totalisent {usd(opening)} à l’ouverture. "
            "Ce sont des hypothèses de sensibilité, pas une demande observée, une disposition à payer mesurée ou un devis. "
            "Les durées humaines de 5/15/45 minutes et l’attention résiduelle sont modélisées ; le salaire horaire de référence "
            "est de 135 980 USD / 2 080 heures supposées = 65,375 USD, hors avantages sociaux. La disponibilité des sources "
            "de 0,5 est une condition du scénario issue des six questions gelées, pas une estimation de population. "
            "Les concurrents peuvent copier et réduire leurs prix en semaine 20. Retards et défauts de paiement, factures "
            "impayées et réserve de 200 USD sont conservés. Le graphique distingue le capital initial restant des fonds "
            "à investir issus de l’exploitation. Le tableau est cumulatif, sauf soldes, réserve et obligations ; les coûts "
            "payés comprennent l’ouverture. Trésorerie = capital initial + recettes − coûts payés hors investissements "
            "− investissements. Les créances ne sont pas des recettes. Les fonds à investir sont limités par la liquidité "
            "après réserve et obligations, ainsi que par les bénéfices d’exploitation."
        )
        scenarios.append(
            {
                "id": cell["id"],
                "label": bilingual(
                    f"{index:02d} · {cell['demand']} demand · {cell['integrationMinutes']} min · {cell['competitorStrength']} rival · {cell['costBundle']} cost",
                    f"{index:02d} · demande {demand_fr} · {cell['integrationMinutes']} min · rival {competitor_fr} · coûts {cost_fr}",
                ),
                "conclusion": bilingual(conclusion_en, conclusion_fr),
                "assumptions": bilingual(assumptions_en, assumptions_fr),
                "seedCapitalUsd": SEED_CENTS / 100,
                "reserveUsd": RESERVE_CENTS / 100,
                "collectionsUsd": last["simulatedCollectionsCents"] / 100,
                "operatingSurplusUsd": (last["simulatedCollectionsCents"] - last["operatingCostCents"]) / 100,
                "closingCashUsd": last["cashCents"] / 100,
                "capabilityInvestmentUsd": last["investmentCents"] / 100,
                "availableFundsUsd": last["availableInvestmentCents"] / 100,
                "ledger": ledger,
                "allSeedSummary": stats,
                "fixedLedgerSeed": 1,
                "links": [
                    {
                        "label": bilingual(
                            "All 24 cells and 16-seed summaries", "24 cellules et synthèses sur 16 graines"
                        ),
                        "href": "../outputs/economics-primary/paper-summary.json",
                    },
                    {
                        "label": bilingual(
                            "All simulated weekly histories", "Tous les historiques hebdomadaires simulés"
                        ),
                        "href": "../outputs/economics-primary/weekly-histories.ndjson",
                    },
                    {
                        "label": bilingual("Frozen assumptions and rules", "Hypothèses et règles gelées"),
                        "href": "../src/economics/protocol.mjs",
                    },
                ],
            }
        )
    data["cash"] = {
        "overview": bilingual(
            "All 24 declared cells are available below, in protocol order. Across 384 worlds and 1,536 counterfactual enterprise histories, "
            "none produced a positive operating result or funded a first or second capability investment. Actual collections: USD 0. "
            "These are outcomes under declared assumptions, not estimates of the entire commercial opportunity.",
            "Les 24 cellules déclarées sont disponibles ci-dessous, dans l’ordre du protocole. Sur 384 mondes et 1 536 historiques "
            "d’entreprises contrefactuelles, aucun résultat d’exploitation positif ni premier ou deuxième investissement en capacité "
            "n’a été obtenu. Recettes réelles : 0 USD. Ces résultats dépendent des hypothèses déclarées ; ils n’estiment pas toute l’opportunité commerciale.",
        ),
        "scenarios": scenarios,
    }
    data["conclusion"] = bilingual(
        "Useful scoped work delivered; the tested flywheel did not close.",
        "Du travail utile livré dans un périmètre défini ; la boucle testée ne s’est pas refermée.",
    )
    data["conclusionScope"] = bilingual(
        "Accepted public-data outputs and reusable implementations. No demonstrated capability scarcity, profitable modeled succession or realized paid demand.",
        "Livrables publics acceptés et implémentations réutilisables. Rareté des capacités, succession rentable modélisée et demande payante réelle non démontrées.",
    )
    data["sources"].append(
        {
            "label": bilingual(
                "Economic outcomes and unknown actual costs", "Résultats économiques et coûts réels inconnus"
            ),
            "href": "../outputs/economics-primary/paper-summary.json",
        }
    )
    (DEMO / "frozen-data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    sources = [
        "demo/frozen-data-nonmarket.json",
        "outputs/economics-primary/paper-summary.json",
        "outputs/economics-primary/summary.json",
        "outputs/economics-primary/weekly-schema.json",
        "outputs/economics-primary/weekly-histories.ndjson",
        "src/economics/protocol.mjs",
    ]
    receipt = {
        "assembledUtc": datetime.now(timezone.utc).isoformat(),
        "script": "assemble_demo_data.py",
        "selectionRule": "Every declared cell in protocol order; ledger seed 1 and policy A fixed for all cells, plus full 16-seed summary.",
        "cells": len(scenarios),
        "worlds": len(worlds),
        "histories": len(histories),
        "policyHistoryEquality": "All 384 paired worlds have byte-equivalent decoded rows across A/B/C/D.",
        "selectedWeeklyCashConservationChecks": checked_rows,
        "selectedWeeklyAvailableFundsChecks": checked_rows,
        "openingRows": len(scenarios),
        "actualCollectionsUsd": 0,
        "transformation": "Integer cents converted to dollars only for display; paid costs = opening + accrued operating costs − unpaid obligations.",
        "sourceSha256": {name: hashlib.sha256((BASE / name).read_bytes()).hexdigest() for name in sources},
        "outputSha256": hashlib.sha256((DEMO / "frozen-data.json").read_bytes()).hexdigest(),
    }
    (DEMO / "data-provenance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"cells": len(scenarios), "cashChecks": checked_rows, "histories": len(histories)}))


if __name__ == "__main__":
    main()
