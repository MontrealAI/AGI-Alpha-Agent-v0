# SPDX-License-Identifier: Apache-2.0
"""Read-only independent arithmetic replay of recorded economic outcomes.

No model, random-number generator, producer or scenario runner is imported.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import time
from collections import defaultdict
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any, Callable


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-7)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("study", type=Path)
    args = parser.parse_args()
    study: Path = args.study.resolve()
    directory = study / "outputs/economics-primary"
    start_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    completion = load(directory / "completion.json")
    frozen = load(directory / "freeze.json")
    protocol = load(directory / "protocol.json")
    calibration = load(directory / "calibration.json")
    check(completion["status"] == "COMPLETE_SIMULATION_ONLY", "completion scope")
    check(digest(directory / "freeze.json") == completion["freezeSha256"], "freeze digest")
    check(digest(directory / "calibration.json") == completion["calibrationSha256"], "calibration digest")
    check(digest(study / frozen["calibration"]["path"]) == frozen["calibration"]["sha256"], "original calibration")
    for row in frozen["sourceFiles"]:
        path = study / row["path"]
        check(digest(path) == row["sha256"] and path.stat().st_size == row["bytes"], "frozen source " + row["path"])
    for row in calibration["evidence"]:
        check(digest(study / row["path"]) == row["sha256"], "calibration evidence " + row["path"])
    check(completion["actualCollectionsCents"] == completion["tokenEarningsCents"] == 0, "actual receipts")
    check(completion["actualPaidDemandEstablished"] is False, "paid demand scope")
    columns = load(directory / "weekly-schema.json")["columns"]
    records = [json.loads(line) for line in (directory / "policy-summaries.ndjson").read_text().splitlines()]
    histories = [json.loads(line) for line in (directory / "weekly-histories.ndjson").read_text().splitlines()]
    keyed = {(row["cell"]["id"], row["seed"], row["policy"]): row for row in records}
    check(len(keyed) == len(records) == len(histories) == 1536, "complete unique policy denominator")
    check(completion["worlds"] == 384 and completion["policyExecutions"] == 1536, "completion denominator")
    hkeyed: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    wage = Decimal(str(protocol["rates"]["wageUSDPerHour"]))

    def labor(minutes: float) -> int:
        value = Decimal(str(minutes)) * wage * 100 / 60
        return int(value.to_integral_value(rounding=ROUND_CEILING))

    def maintenance(capability: str, cost: dict[str, Any]) -> float:
        if capability == "A":
            return 0.0
        minutes = float(cost["investment1"]["maintenanceMinutesPerReuse"])
        if capability in ("C", "D"):
            minutes += float(cost["investment2"]["maintenanceMinutesPerReuse"])
        if capability == "D":
            minutes += float(cost["graphExtra"]["maintenanceMinutesPerReuse"])
        return minutes

    week_count = gate_count = funded_count = 0
    for history in histories:
        key = (history["cell"], history["seed"], history["policy"])
        check(key not in hkeyed and key in keyed, "history identity")
        summary = keyed[key]
        rows = [dict(zip(columns, row, strict=True)) for row in history["rows"]]
        hkeyed[key] = rows
        check(len(rows) == protocol["campaign"]["weeks"] == 52, "history horizon")
        cost = protocol["costBundles"][summary["cell"]["costBundle"]]
        opening_items = {
            "historical_discovery": labor(cost["historicalDiscoveryMinutes"]),
            "historical_failed_discovery": labor(cost["historicalFailedDiscoveryMinutes"]),
            "historical_inference": cost["historicalInferenceCents"],
            "ordinary_setup": labor(cost["setupMinutes"]) + cost["setupOtherCents"],
        }
        opening = sum(opening_items.values())
        seed = protocol["capital"]["initialSeedCents"]
        reserve = protocol["capital"]["reserveCents"]
        check(opening <= seed, "observed opening fully funded; alternate opening replay required")
        cash = seed - opening
        collected = invoiced = defaulted = operating = paid = invested = 0
        bills: list[list[int]] = []
        categories: dict[str, int] = defaultdict(int, opening_items)
        insolvency: int | None = None
        onboarding_count = 0
        gate_by_week = {row["week"]: row for row in summary["investmentChecks"]}
        check(len(gate_by_week) == len(summary["investmentChecks"]), "duplicate decision week")
        funded_by_week = {row["admittedWeek"]: row for row in summary["investments"]}
        for number, row in enumerate(rows, 1):
            week_count += 1
            prefix = f"{key}:week{number}:"
            check(row["week"] == number, prefix + "week sequence")
            for field in (
                "cashCents",
                "simulatedCollectionsCents",
                "operatingCostCents",
                "unpaidCents",
                "receivableCents",
                "investmentCents",
            ):
                check(isinstance(row[field], int) and row[field] >= 0, prefix + field)
            due_count = (
                rows[number - 1 - protocol["market"]["paymentDelayWeeks"]]["accepted"]
                if number > protocol["market"]["paymentDelayWeeks"]
                else 0
            )
            delta_collection = row["simulatedCollectionsCents"] - collected
            check(0 <= delta_collection <= due_count * summary["tariff"]["priceCents"], prefix + "collection timing")
            check(delta_collection % summary["tariff"]["priceCents"] == 0, prefix + "collection unit")
            collected += delta_collection
            defaulted += due_count * summary["tariff"]["priceCents"] - delta_collection
            cash += delta_collection
            for bill in bills:
                if bill[0] <= number:
                    payment = min(cash, bill[1])
                    cash -= payment
                    bill[1] -= payment
                    paid += payment
            if any(due <= number and amount for due, amount in bills) and insolvency is None:
                insolvency = number
            check(row["insolvencyWeek"] == insolvency, prefix + "insolvency timing")
            is_open = insolvency is None
            fixed_minutes = cost["weeklyBusinessMinutes"] + cost["weeklyBaseMaintenanceMinutes"] if is_open else 0
            week_items: dict[str, int] = {}
            if is_open:
                week_items.update(
                    business=labor(cost["weeklyBusinessMinutes"]),
                    base_maintenance=labor(cost["weeklyBaseMaintenanceMinutes"]),
                    tools=cost["weeklyToolCents"],
                )
            fixed_cents = sum(week_items.values())
            before_gate_available = max(
                0,
                min(
                    cash - reserve - sum(bill[1] for bill in bills) - fixed_cents,
                    collected - operating - fixed_cents - invested,
                ),
            )
            if number in gate_by_week:
                gate_count += 1
                gate = gate_by_week[number]
                check(
                    gate["availableCents"] == before_gate_available,
                    prefix + "gate funds excluding seed/reserves/obligations",
                )
                check(gate["id"] == "investment1", prefix + "observed first-gate scope")
                budget = cost["investment1"]
                fixed_investment = (
                    sum(
                        labor(budget[field])
                        for field in (
                            "constructionMinutes",
                            "failedConstructionMinutes",
                            "validationMinutes",
                            "integrationMinutes",
                        )
                    )
                    + budget["inferenceCents"]
                )
                check(gate["fixedCostCents"] == fixed_investment, prefix + "complete investment cost")
                delta_cpu = (
                    calibration["arms"]["A"]["cpuSecondsAvailableMean"]
                    - calibration["arms"]["B"]["cpuSecondsAvailableMean"]
                )
                saving = math.trunc(delta_cpu * protocol["rates"]["cpuUSDPerHour"] * 1_000_000 / 3600)
                lifetime = min(protocol["investment"]["usefulLifeWeeks"], 53 - number)
                lookback = rows[max(0, number - 1 - protocol["investment"]["forecastLookbackWeeks"]) : number - 1]
                expected_uses = (
                    math.floor(
                        sum(item["attempts"] for item in lookback)
                        / len(lookback)
                        * protocol["investment"]["forecastReuseDiscount"]
                        * lifetime
                    )
                    if lookback
                    else 0
                )
                incremental_maintenance = labor(budget["maintenanceMinutesPerReuse"]) * 10000
                net = expected_uses * (saving - incremental_maintenance) - fixed_investment * 10000
                check(gate["expectedSavingMicroUSDPerReuse"] == saving, prefix + "signed CPU credit")
                check(
                    gate["expectedReuses"] == expected_uses and gate["remainingWeeks"] == lifetime,
                    prefix + "finite forecast",
                )
                check(
                    gate["incrementalMaintenanceMicroUSDPerReuse"] == incremental_maintenance,
                    prefix + "rounded maintenance",
                )
                check(gate["canonical"]["netBenefit"] == net, prefix + "net benefit")
                check(gate["weeklyCashRoundingProvisionMicroUSD"] == lifetime * 10000, prefix + "cash rounding")
                check(gate["conservativeNetBenefitMicroUSD"] == net - lifetime * 10000, prefix + "conservative net")
                check(saving < 0 and gate["qualifies"] is False, prefix + "negative investment rejected")
                check("NONPOSITIVE_MEASURED_CPU_SAVING" in gate["reasons"], prefix + "rejection reason")
                check(
                    gate["credit"]["assumedAttentionSavingsCents"]
                    == gate["credit"]["assumedDemandPremiumCents"]
                    == gate["credit"]["assumedQualityPremiumCents"]
                    == gate["credit"]["comparatorReconstructionCostCents"]
                    == 0,
                    prefix + "no invented value",
                )
            if number in funded_by_week:
                funded_count += 1
                raise AssertionError(prefix + "unexpected funded path requires independent funded-event replay")
            check(
                row["investmentCents"] == invested == 0 and row["investmentId"] is None and row["capability"] == "A",
                prefix + "retained initial capability",
            )
            check(row["accepted"] + row["rejected"] == row["orders"], prefix + "order disposition")
            available_orders = row["orders"] - row["inputBlocked"]
            check(
                0 <= row["accepted"] <= row["attempts"] <= protocol["market"]["maxAttempts"] * available_orders,
                prefix + "no source retry",
            )
            check(
                row["inputBlocked"] <= row["rejected"] and row["inputBlocked"] <= row["unavailableOpportunities"],
                prefix + "source rejection",
            )
            check(row["enterpriseChoices"] == row["orders"] + row["capacityRefusals"], prefix + "choice disposition")
            check(
                sum(
                    row[field] for field in ("enterpriseChoices", "diyChoices", "aiChoices", "humanChoices", "declines")
                )
                == row["arrivals"],
                prefix + "all choices",
            )
            check(row["attempts"] - row["failedAttempts"] == row["accepted"], prefix + "attempt acceptance")
            if not is_open:
                check(row["orders"] == 0 and row["providerMinutes"] == 0, prefix + "insolvent operations stopped")
            maintenance_minutes = maintenance(row["capability"], cost)
            expected_attention_without_onboarding = (
                fixed_minutes
                + available_orders * cost["supportMinutesPerOrder"]
                + row["attempts"] * (cost["residualMinutesPerAttempt"] + maintenance_minutes)
                + (row["failedAttempts"] + row["inputBlocked"])
                * protocol["market"]["correctionMinutesPerRejectedAttempt"]
            )
            onboarding_minutes = row["providerMinutes"] - expected_attention_without_onboarding
            onboard = round(onboarding_minutes / cost["providerOnboardingMinutes"])
            check(
                close(onboarding_minutes, onboard * cost["providerOnboardingMinutes"])
                and 0 <= onboard <= available_orders,
                prefix + "onboarding attention",
            )
            onboarding_count += onboard
            check(onboarding_count <= protocol["market"]["buyers"], prefix + "bounded onboarding")
            if available_orders:
                week_items["onboarding_support"] = onboard * labor(
                    cost["providerOnboardingMinutes"] + cost["supportMinutesPerOrder"]
                ) + (available_orders - onboard) * labor(cost["supportMinutesPerOrder"])
            if row["attempts"]:
                week_items["delivery_attention"] = row["attempts"] * labor(cost["residualMinutesPerAttempt"])
                week_items["capability_maintenance"] = row["attempts"] * labor(maintenance_minutes)
            if row["failedAttempts"]:
                week_items["rejection_correction"] = row["failedAttempts"] * labor(
                    protocol["market"]["correctionMinutesPerRejectedAttempt"]
                )
            if row["inputBlocked"]:
                week_items["source_unavailable_triage"] = row["inputBlocked"] * labor(
                    protocol["market"]["correctionMinutesPerRejectedAttempt"]
                )
            if row["orders"]:
                week_items["compute"] = math.ceil(row["cpuSeconds"] * protocol["rates"]["cpuUSDPerHour"] * 100 / 3600)
            accrued = sum(week_items.values())
            operating += accrued
            if accrued:
                bills.append([number + protocol["market"]["expenseDelayWeeks"], accrued])
            for category, amount in week_items.items():
                categories[category] += amount
            check(row["operatingCostCents"] == operating, prefix + "complete recurring accrual")
            check(row["cashCents"] == cash, prefix + "finite cash replay")
            outstanding = sum(bill[1] for bill in bills)
            check(row["unpaidCents"] == outstanding == operating - paid, prefix + "obligation replay")
            expected_available = max(0, min(cash - reserve - outstanding, collected - operating - invested))
            check(row["availableInvestmentCents"] == expected_available, prefix + "closing available funds")
            invoiced += row["accepted"] * summary["tariff"]["priceCents"]
            check(
                row["receivableCents"] == invoiced - collected - defaulted, prefix + "invoice/receivable reconciliation"
            )
            check(
                close(row["cpuSeconds"], 0) or row["cpuSeconds"] <= protocol["market"]["machineCPUSecondsPerWeek"],
                prefix + "CPU capacity",
            )
            check(
                row["wallSeconds"] <= protocol["market"]["machineWallSecondsPerWeek"]
                and row["providerMinutes"] <= protocol["market"]["providerAttentionMinutesPerWeek"],
                prefix + "wall/attention capacity",
            )
        closing = summary["closing"]
        expected_closing = {
            "cashCents": cash,
            "seedCents": seed,
            "actualCollectionsCents": 0,
            "simulatedCollectionsCents": collected,
            "invoicedCents": invoiced,
            "receivableCents": invoiced - collected - defaulted,
            "defaultedCents": defaulted,
            "openingCostCents": opening,
            "openingPaidCents": opening,
            "operatingCostCents": operating,
            "operatingPaidCents": paid,
            "unpaidCents": operating - paid,
            "reserveCents": reserve,
            "investmentCents": invested,
            "availableInvestmentCents": rows[-1]["availableInvestmentCents"],
            "operatingSurplusCents": collected - operating,
            "fullCostAfterInvestmentCents": opening + operating + invested,
            "historicalRecoveryCents": collected - operating - invested - opening,
            "insolvencyWeek": insolvency,
        }
        check(closing == expected_closing, str(key) + " closing exact")
        check(dict(categories) == summary["costItemsCents"], str(key) + " every cost category")
        for field, total in summary["totals"].items():
            check(close(sum(row[field] for row in rows), total), str(key) + " total " + field)
        check(
            summary["earnedOrdinaryOperatingSurplus"] == (collected > operating and insolvency is None),
            str(key) + " surplus flag",
        )
        check(
            summary["recoveredHistoricalAndInvestmentCosts"]
            == (collected >= operating + invested + opening and insolvency is None),
            str(key) + " historical recovery flag",
        )
        check(
            summary["modeledSelfFinancingSuccession"] is False and summary["investments"] == [],
            str(key) + " no funded succession",
        )
        check(
            summary["actualFullCostCents"] is None
            and summary["actualOperatingProfitCents"] is None
            and summary["actualCollectionsCents"] == 0,
            str(key) + " unknown actual cost retained",
        )
    check(week_count == 79872, "full weekly denominator")
    grouped = load(directory / "summary.json")
    for group in grouped["groups"]:
        selected = [row for row in records if row["cell"]["id"] == group["cell"] and row["policy"] == group["policy"]]
        check(len(selected) == group["seeds"] == 16, "group seed denominator")
        for field, test_field in [
            ("positiveOrdinarySurplusCount", "earnedOrdinaryOperatingSurplus"),
            ("recoveredFullHistoryCount", "recoveredHistoricalAndInvestmentCosts"),
            ("repaidSuccessionCount", "modeledSelfFinancingSuccession"),
        ]:
            check(group[field] == sum(row[test_field] for row in selected), "group " + field)
        check(group["firstInvestmentCount"] == group["secondInvestmentCount"] == 0, "group investment")
        check(
            group["insolvencyCount"] == sum(row["closing"]["insolvencyWeek"] is not None for row in selected),
            "group insolvency",
        )
        fields: dict[str, Callable[[dict[str, Any]], Any]] = {
            "acceptedJobs": lambda row: row["totals"]["accepted"],
            "simulatedCollectionsCents": lambda row: row["closing"]["simulatedCollectionsCents"],
            "operatingSurplusCents": lambda row: row["closing"]["operatingSurplusCents"],
            "fullCostRecoveryCents": lambda row: row["closing"]["historicalRecoveryCents"],
            "closingCashCents": lambda row: row["closing"]["cashCents"],
        }
        for field, getter in fields.items():
            values = [getter(row) for row in selected]
            check(
                group[field]["minimum"] == min(values)
                and group[field]["maximum"] == max(values)
                and close(group[field]["mean"], sum(values) / 16),
                "group distribution " + field,
            )
    paired_worlds = 0
    for cell, seed in sorted({(row["cell"]["id"], row["seed"]) for row in records}):
        paired_worlds += 1
        initial = hkeyed[(cell, seed, "A")]
        for arm in ("B", "C", "D"):
            check(hkeyed[(cell, seed, arm)] == initial, "paired policies remain A without funded investment")
    for pairing in grouped["paired"]:
        check(len(pairing["differences"]) == 16, "paired difference denominator")
        for row in pairing["differences"]:
            check(
                all(value == 0 for field, value in row.items() if field != "seed"),
                "paired financial/acceptance differences",
            )
    outputs = [
        "completion.json",
        "freeze.json",
        "calibration.json",
        "protocol.json",
        "weekly-schema.json",
        "weekly-histories.ndjson",
        "policy-summaries.ndjson",
        "summary.json",
        "diagnostics.json",
        "paper-summary.json",
    ]
    observed = {
        "worlds": paired_worlds,
        "policyExecutions": len(records),
        "weeklyRecordsReplayed": week_count,
        "investmentDecisionsRecomputed": gate_count,
        "fundedInvestments": funded_count,
        "positiveOrdinarySurplusPolicyRuns": sum(row["earnedOrdinaryOperatingSurplus"] for row in records),
        "historicalRecoveryPolicyRuns": sum(row["recoveredHistoricalAndInvestmentCosts"] for row in records),
        "insolventPolicyRuns": sum(row["closing"]["insolvencyWeek"] is not None for row in records),
        "modeledSelfFinancingSuccessions": sum(row["modeledSelfFinancingSuccession"] for row in records),
        "simulatedAcceptedJobsAcrossCounterfactualRuns": sum(row["totals"]["accepted"] for row in records),
    }
    report = {
        "schema": "independent-economic-results-review/v1",
        "status": "PASS_RECORDED_ARITHMETIC_AND_SCOPE",
        "reviewer": "/root/api_baseline",
        "startedAt": start_at,
        "completedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "authentication": "Self-declared local independent review with SHA-256 byte bindings; no live ENS identity or cryptographic validator signature asserted.",
        "method": "Independent Python replay of all recorded weekly cash flows, invoice timing, defaults, due obligations, itemized operating charges, reserve/seed constraints, finite first-investment gates, closing ledgers, grouped statistics and paired policies. No producer, random generator or economic scenario function imported or executed.",
        "observed": observed,
        "inputSha256": {name: digest(directory / name) for name in outputs},
        "reviewSourceSha256": digest(Path(__file__)),
        "claims": {
            "actualCollectionsCents": 0,
            "actualPaidDemandEstablished": False,
            "actualCompleteCostKnown": False,
            "fundedBranchObserved": False,
            "realizedCommercialSuccess": False,
        },
        "qualifications": [
            "The 1536 policies are paired counterfactuals in 384 assumed worlds, not independent businesses or actual customers; do not add their collections as enterprise revenue.",
            "No investment was funded; funded-event behavior is supported by synthetic controls and source review, not by an observed successful succession.",
            "The 3/6 availability input is a scenario condition from the frozen intended cases, not a market-frequency estimate.",
            "Labor, demand, prices, payment/default behavior, maintenance and useful life remain declared assumptions. Human-only savings, paid demand and complete actual study cost remain unestablished.",
            "Secondary transfer and public-tool follow-ups are excluded from this primary economic calibration.",
        ],
        "reviewCpuSeconds": time.process_time() - start_cpu,
        "reviewWallSeconds": time.perf_counter() - start_wall,
        "costClassification": "Additional independent research validation; actual inference/labor dollars remain unknown.",
    }
    destination = study / "evidence/independent-economic-results-review.json"
    with destination.open("x") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    (study / "evidence/audit_economics.py").write_bytes(Path(__file__).read_bytes())
    (study / "evidence/independent-economic-results-review.sha256").write_text(
        digest(destination) + "  independent-economic-results-review.json\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
