# SPDX-License-Identifier: Apache-2.0
"""Describe archived, already completed market outcomes. Never runs a simulator."""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


STUDY = Path(__file__).resolve().parents[1]
RESULTS = STUDY / "market/results/primary-01"
OUT = STUDY / "analysis"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signs(values):
    return {
        "negative": sum(v is not None and v < 0 for v in values),
        "zero": sum(v is not None and v == 0 for v in values),
        "positive": sum(v is not None and v > 0 for v in values),
        "unidentified": sum(v is None for v in values),
    }


def counts(rows, arm):
    fields = ["modeledConstructionAttempted", "admitted",
              "secondInvestmentPaidFromGeneratedResources", "secondFailedIntegration",
              "directSecondCostRepayment", "insolvent"]
    return {
        "worlds": len(rows),
        **{k: sum(bool(r["arms"][arm][k]) for r in rows) for k in fields},
        "conditionalFinancialGatePasses": sum(
            r["qualification"][arm]["conditionalModeledFinancialGatePassed"] for r in rows),
        "worldsWithSecondUses": sum(r["arms"][arm]["secondInvocations"] > 0 for r in rows),
        "secondInvocations": sum(r["arms"][arm]["secondInvocations"] for r in rows),
        "projectInclusiveDifferenceSigns": signs(
            [r["causal"][f"{arm}_minus_A_projectInclusiveProfitCents"] for r in rows]),
    }


def bills(run):
    total = Counter()
    for b in run["histories"]["bills"]:
        total[b["category"]] += b["amountCents"]
    return dict(total)


def positive_detail(w):
    paired = w["paired"]
    a, b = paired["arms"]["A"], paired["arms"]["B"]
    aj = {j["id"]: j for j in a["histories"]["jobs"] if j["provider"] == "enterprise"}
    bj = {j["id"]: j for j in b["histories"]["jobs"] if j["provider"] == "enterprise"}
    gained = [bj[k] for k in bj.keys() - aj.keys()]
    lost = [aj[k] for k in aj.keys() - bj.keys()]
    gained.sort(key=lambda j: (j["week"], j["id"]))
    lost.sort(key=lambda j: (j["week"], j["id"]))
    ac = {x["mission"]: x for x in a["histories"]["buyerChoices"]}
    bc = {x["mission"]: x for x in b["histories"]["buyerChoices"]}
    changed_choices = [
        {"mission": k, "week": ac[k]["week"], "A": ac[k]["choice"], "B": bc[k]["choice"]}
        for k in ac if ac[k]["choice"] != bc[k]["choice"]
    ]
    ab, bb = bills(a), bills(b)
    cost_difference = {k: bb.get(k, 0) - ab.get(k, 0) for k in sorted(set(ab) | set(bb))}
    collections_difference = b["summary"]["grossCollectionsCents"] - a["summary"]["grossCollectionsCents"]
    delta = paired["causal"]["B_minus_A_projectInclusiveProfitCents"]
    assert collections_difference - sum(cost_difference.values()) == delta
    if w["seed"] == 8009:
        mechanism = (
            "The week-26 construction pause removes the enterprise offer. Under the same keyed logit draw, "
            "buyer-10 chooses DIY instead of AI, and buyer-5 chooses the human instead of the enterprise. "
            "Subsequent provider beliefs, switching history and finite procurement choices diverge: "
            "buyer-10 generates five additional enterprise sales and buyer-5 two fewer, for net three. "
            "No initial quality failure is avoided in this case. The gain is a path-dependent pause/choice "
            "realization, not an executed improvement in unit delivery cost or quality."
        )
    else:
        mechanism = (
            "The week-26 pause diverts buyer-1 to the human. In A, w26-buyer-1 is a rejected enterprise "
            "delivery; B therefore avoids that failed delivery and its adverse enterprise feedback. "
            "Later choices differ: B gains accepted enterprise jobs at weeks 34 and 36, and a rejected "
            "enterprise job at week 37. Total rejected jobs remain five in both arms; net accepted jobs "
            "increase by two. The quality rule is unchanged by the second asset. This is a path-dependent "
            "pause/feedback realization, not demonstrated capability quality improvement."
        )
    return {
        "groupId": w["groupId"], "seed": w["seed"], "basis": "POST-OUTCOME EXPLANATION OF SAVED REALIZATION",
        "incrementalProjectProfitCents": delta,
        "BMinusCProjectProfitCents": paired["causal"]["B_minus_C_projectInclusiveProfitCents"],
        "collectionsDifferenceCents": collections_difference,
        "billedCostDifferencesCents": cost_difference,
        "A": {"summary": a["summary"], "billsByCategoryCents": ab},
        "B": {"summary": b["summary"], "billsByCategoryCents": bb},
        "secondDecision": b["secondInvestment"]["decisions"][0],
        "secondInvocations": b["secondInvestment"]["actualAssetInvocationsInModel"],
        "directAvoidedDeliveryCostCents": b["secondInvestment"]["directAvoidedDeliveryCostCents"],
        "directRepayment": b["secondInvestment"]["directCostRepayment"],
        "qualification": paired["qualification"],
        "subcentComputeEffect": b["secondInvestment"]["subcentComputeEffect"],
        "gainedEnterpriseJobs": gained, "lostEnterpriseJobs": lost,
        "changedBuyerChoices": changed_choices,
        "interpretation": mechanism,
        "causalLimit": (
            "This difference is caused by the modeled intervention, including its pause, conditional on "
            "the frozen simulator and seed. It is not an economically justified ex ante investment or "
            "evidence that this capability improves the production method. No pause-only ablation was "
            "registered or run; the explanation follows the archived sequence and unchanged effect parameters."
        ),
    }


def money(cents):
    if cents is None:
        return "unidentified"
    return f"{'−' if cents < 0 else ''}${abs(cents) / 100:,.2f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--positive-extract", type=Path,
                        help="Optional previously extracted full archive records; no simulation is performed.")
    args = parser.parse_args()
    summary = read(RESULTS / "summary.json")
    completion = read(RESULTS / "completion.json")
    protocol = read(STUDY / "market/campaign-protocol.json")
    effect = read(STUDY / "market/effect-profile.json")
    costs = read(STUDY / "market/cost-profiles.json")
    representatives = read(RESULTS / "predeclared-representatives.json")
    rows = [json.loads(line) for line in (RESULTS / "compact-worlds.jsonl").read_text().splitlines()]
    groups = summary["groups"]
    assert completion["complete"] and len(rows) == 1920 and len(groups) == 80
    positives = {(r["groupId"], r["seed"]) for r in rows
                 if r["causal"]["B_minus_A_projectInclusiveProfitCents"] is not None
                 and r["causal"]["B_minus_A_projectInclusiveProfitCents"] > 0}
    if args.positive_extract:
        found = read(args.positive_extract)
    else:
        found = []
        with gzip.open(RESULTS / "complete-paired-worlds.jsonl.gz", "rt") as stream:
            for line in stream:
                w = json.loads(line)
                if (w["groupId"], w["seed"]) in positives:
                    found.append(w)
                    if len(found) == len(positives):
                        break
    assert {(w["groupId"], w["seed"]) for w in found} == positives
    assert all(w["sourceFreezeSHA256"] == summary["sourceFreezeSHA256"] for w in found)
    ref = next(g for g in groups if g["groupId"] == "reference__reference__completed-research-replay")
    by_profile_policy = []
    for policy in ["adaptive", "completed-research-replay"]:
        for cost in ["low", "reference", "high", "actual-unknown"]:
            subset = [r for r in rows if r["policyId"] == policy and r["costProfileId"] == cost]
            by_profile_policy.append({"policyId": policy, "costProfileId": cost,
                                      "B": counts(subset, "B"), "C": counts(subset, "C")})
    representative_details = []
    for w in representatives["worlds"]:
        a, b = w["paired"]["arms"]["A"], w["paired"]["arms"]["B"]
        s = b["secondInvestment"]
        representative_details.append({
            "groupId": w["groupId"], "seed": w["seed"], "selectedBeforeOutcomes": True,
            "AFullHistoryProfitCents": a["summary"]["profitCents"],
            "AProspectiveProfitExcludingOnlySeedPaidHistoricalRDCents": a["summary"]["profitCents"] + 36152,
            "BEnterpriseProfitCents": b["summary"]["profitCents"],
            "BProjectInclusiveProfitCents": s["projectProfitAfterCompletedPrototypeCostsCents"],
            "fundingBeforeFirstDecision": s["decisions"][0]["beforeSearch"],
            "firstDecision": s["decisions"][0],
            "actualFirstPaidSecondCheckpoint": s["initialCheckpoint"],
            "declaredCompleteOneoffCostCents": s["declaredCompletePrototypeOneoffCostCents"],
            "secondCostsInEnterpriseCents": s["completeRealizedSecondCostsCents"],
            "outsideEnterprisePrototypeCostCents": s["outsideEnterprisePrototypeCostCents"],
            "maintenanceCents": s["maintenanceAccruedCents"],
            "secondUses": s["actualAssetInvocationsInModel"],
            "subcentComputeEffect": s["subcentComputeEffect"],
            "terminalCashCents": b["summary"]["finalCashCents"],
            "terminalUnpaidObligationsCents": b["summary"]["obligationsCents"],
        })
    selected_low = next(x for x in representative_details
                        if x["groupId"] == "reference__low__completed-research-replay")
    assert selected_low["secondUses"] == 15 and selected_low["maintenanceCents"] == 150
    conditions = []
    for condition in protocol["conditions"]:
        gs = {g["policyId"]: g for g in groups
              if g["conditionId"] == condition["id"] and g["costProfileId"] == "reference"}
        conditions.append({
            "condition": condition,
            "referenceCost": {p: {
                "BMinusAProjectInclusiveCents": g["causal"]["B_minus_A_projectInclusiveProfitCents"],
                "BCounts": g["arms"]["B"]["counts"],
                "BMinusAEnterpriseCents": g["causal"]["B_minus_A_profitCents"],
                "BMinusAAccepted": g["causal"]["B_minus_A_accepted"],
            } for p, g in gs.items()},
        })
    all_groups = [{
        "groupId": g["groupId"], "conditionId": g["conditionId"],
        "costProfileId": g["costProfileId"], "policyId": g["policyId"],
        "completedSeeds": g["completedSeeds"],
        "arms": {a: {k: g["arms"][a][k] for k in [
            "enterpriseProfitCents", "projectInclusiveProfitCents", "finalCashCents", "collectionsCents",
            "accepted", "attempts", "refundsCents", "secondCostsInEnterpriseCents",
            "outsideEnterprisePrototypeCostCents", "secondInvocations", "counts"]} for a in ["A", "B", "C"]},
        "causal": g["causal"],
    } for g in groups]
    source_paths = ["market/campaign-freeze.json", "market/campaign-protocol.json", "market/cost-profiles.json",
                    "market/effect-profile.json", "market/continuation.mjs", "market/run-campaign.mjs",
                    "market/upstream/src/market.mjs", "market/results/primary-01/completion.json",
                    "market/results/primary-01/summary.json", "market/results/primary-01/compact-worlds.jsonl",
                    "market/results/primary-01/predeclared-representatives.json",
                    "review/market-results-independent-review.json", "review/seed8001-hand-reconciliation.json",
                    "analysis/build_market_findings.py"]
    report = {
        "schema": "agi-alpha-second-investment-market-findings/v1",
        "createdUTC": datetime.now(timezone.utc).isoformat(),
        "analysisType": "DESCRIPTIVE ANALYSIS OF FROZEN, COMPLETED OUTCOMES; NO SIMULATOR EXECUTION",
        "sourceFreezeSHA256": summary["sourceFreezeSHA256"],
        "sources": [{"path": p, "sha256": digest(STUDY / p)} for p in source_paths],
        "archive": {"path": "market/results/primary-01/complete-paired-worlds.jsonl.gz",
                    "rawSHA256": completion["completePairedWorldsRawSHA256"],
                    "gzipSHA256": completion["completePairedWorldsGzipSHA256"],
                    "hashBasis": "Recorded campaign completion; independent saved-archive audit is separate."},
        "result": "NO_QUALIFYING_SECOND_INVESTMENT_IN_REGISTERED_MODEL",
        "actualCustomerCollectionsCents": 0, "actualFinancialTransactions": 0,
        "population": {"pairedWorlds": len(rows), "enterpriseHistories": 3 * len(rows),
                       "groups": len(groups), "conditions": len(protocol["conditions"]),
                       "freshSeeds": protocol["seeds"], "productionHorizonWeeks": 52,
                       "pricedWorlds": 1872, "actualCostUnidentifiedWorlds": 48,
                       "independenceWarning": "Same 24 seeds recur across conditions/profiles/policies. Grid shares are not market probabilities.",
                       "settlementTail": "Only existing collections, refunds and bills settle after week 51; no new demand extends the 52-week production horizon."},
        "global": {
            "B": counts(rows, "B"), "C": counts(rows, "C"),
            "groupMeanProjectDifferenceSigns": signs([g["causal"]["B_minus_A_projectInclusiveProfitCents"]["mean"] for g in groups]),
            "BMinusCEnterpriseProfitSigns": signs([r["causal"]["B_minus_C_profitCents"] for r in rows]),
            "BMinusCProjectProfitSigns": signs([r["causal"]["B_minus_C_projectInclusiveProfitCents"] for r in rows]),
            "maximumAbsoluteSubcentResidualUSD": {
                a: max(r["arms"][a]["subcentComputeMaximumAbsoluteResidualUSD"] for r in rows)
                for a in ["B", "C"]},
            "zeroCapabilityDeliverySavingInAllWorlds": all(r["arms"][a]["directAvoidedSecondCostCents"] == 0 for r in rows for a in ["B", "C"]),
        },
        "byCostProfileAndPolicy": by_profile_policy,
        "reference": {
            "basis": "Inherited favorable conditional reference, not fitted to these outcomes.",
            "AFullHistoryProfitCents": ref["arms"]["A"]["enterpriseProfitCents"],
            "ASeedPaidHistoricalRDScenarioCents": 36152,
            "AProspectiveProfitMeanCentsExcludingOnlyOpeningHistoricalRD": ref["arms"]["A"]["enterpriseProfitCents"]["mean"] + 36152,
            "prospectiveInterpretation": "Accounting decomposition of the same finite archived histories; includes first adoption, delivery, overhead and upkeep. No second simulation, no restored cash and no second-asset credit for first-asset savings.",
            "ACollectionsMeanCents": ref["arms"]["A"]["collectionsCents"]["mean"],
            "AAcceptedMean": ref["arms"]["A"]["accepted"]["mean"],
            "referenceCostReplay": ref,
            "referenceCostFundedSeeds": [{"seed": r["seed"],
                                           "generatedCentsAtDecision": r["arms"]["B"]["firstSecondDecision"]["beforeSearch"]["availableCents"],
                                           "uses": r["arms"]["B"]["secondInvocations"],
                                           "BMinusAProjectCents": r["causal"]["B_minus_A_projectInclusiveProfitCents"]}
                                          for r in rows if r["groupId"] == ref["groupId"] and r["arms"]["B"]["modeledConstructionAttempted"]],
        },
        "referenceCostByAll13Conditions": conditions,
        "preselectedSeed8001": representative_details,
        "positiveRealizations": [positive_detail(w) for w in found],
        "breakEven": {
            "classification": "ANALYTICAL NECESSARY CONDITION; NOT A NEW MARKET SCENARIO OR OUTCOME RUN",
            "directRepaymentCondition": "N * evidenced seller benefit per use >= complete oneoff cost + upkeep; foregone contribution, extra delivery costs and other burdens increase the requirement.",
            "zeroSupportedMarginalGain": "At zero supported positive marginal delivery benefit, no finite positive-cost workload repays by the capability delivery-saving channel. Negative subcent CPU effects strengthen this conclusion. Incidental buyer-path gains in two saved realizations do not establish a repeatable productive benefit.",
            "workloadSource": "Preselected reference/low/completed-research-replay/seed8001: 15 modeled second uses during weeks27-51, with no new demand after week51.",
            "referenceCounterfactual": {"completeOneoffUSD": 103.85, "upkeepUSDFor25ActiveWeeks": 6.25,
                                        "minimumBenefitPerUseUSD": 110.10 / 15,
                                        "status": "Reference cost is unaffordable in this seed at week26; 15 uses are borrowed only as a disclosed analytical workload from the funded low-profile replay. No reference investment is claimed."},
            "lowExecutedReplay": {"completeOneoffUSD": 25.97, "upkeepUSDFor25ActiveWeeks": 1.50,
                                  "minimumBenefitPerUseUSD": 27.47 / 15,
                                  "actualSupportedDeliveryBenefitUSD": 0,
                                  "actualPairedProjectLossCents": 2747},
            "assumedResidualLaborComparison": {
                "minutesPerUse": 2, "hourlyUSD": 65.38,
                "maximumLaborSavingPerUseUSDIfAllResidualLaborDisappeared": 2 * 65.38 / 60,
                "referenceRequiredMinutesPerUse": (110.10 / 15) / (65.38 / 60),
                "lowRequiredMinutesPerUse": (27.47 / 15) / (65.38 / 60),
                "lowFractionOfAssumedResidualLabor": (27.47 / 15) / (2 * 65.38 / 60),
                "warning": "Two minutes is an inherited unmeasured labor assumption, not a measured ceiling or demonstrated saving. The existing first asset already removed its separate assumed ten-minute finalization burden. The $0.25 tool cost is not assumed eliminated."},
            "missingObservation": "Measure a repeatable incremental seller benefit against the strong incumbent on fresh independently accepted complete outcomes, measure complete construction/integration/upkeep tariffs, and show enough observed recurrence within the finite useful life. For the low illustrative 15-use case, even the optimistic necessary threshold requires more than $1.8313 per use before downtime; no such benefit was measured. For the reference threshold, eliminating the entire assumed two residual minutes would be insufficient.",
        },
        "costInterpretation": {
            "actualMonetaryCostIdentified": False,
            "scenarioProfiles": costs,
            "actualUnknownCase": "All eight oneoff categories and maintenance are null. It blocks unconditional affordability and profitability; null is never zero.",
            "adaptiveVsResearchProvenance": "Adaptive policy pays affordable search once and declines construction. Because the prototype was actually constructed during research, its remaining cost is disclosed outside enterprise cash and subtracted once for project-inclusive profit. This does not claim the adaptive enterprise constructed it or that research was operating-funded.",
            "completedReplay": "If complete costs fit current generated resources, the replay debits them to the same ledger and simulates the constructed asset. With zero forecast productive benefit it is a funded but financially unqualified research attempt. Otherwise it stays unfunded, with outside research cost retained.",
            "seedVsSurplus": "Seed cash, the $500 scenario commitment cap, future uncollected invoices, buyer savings, token value and enterprise valuation are not operating-generated funding. Historical opening research remains full-history cost; it is not debited again at the second checkpoint.",
        },
        "effectProvenance": effect,
        "all80Groups": all_groups,
        "limits": [
            "Calibrated strategic simulation and conditional financial accounting, not actual market receipts or an equilibrium proof.",
            "No price, demand, quality, human-effort, customer-effort or throughput improvement was assigned merely because the second capability exists.",
            "B and C tie at the cent ledger; their signed measured CPU effects differ and are retained below one cent.",
            "Nominal Monte Carlo mean intervals in the source are conditional on each scenario, unadjusted across the 80 groups, and do not quantify real-market demand or tariff uncertainty.",
            "The two positive realized project differences are preserved; no post-outcome optimization or new pause-only trial was run.",
        ],
    }
    (OUT / "market-findings.json").write_text(json.dumps(report, indent=2) + "\n")
    md = [
        "# Saved market campaign findings — The Second Investment", "",
        "**No second investment qualifies in the registered model.** The completed campaign contains 1,920 paired worlds and 5,760 enterprise histories in 80 groups. B and C each have 114 operating-funded research replays, zero financially admitted second investments, zero direct second-cost repayments and zero complete financial-gate passes. There are 1,870 negative and two positive project-inclusive differences among the 1,872 priced worlds; the other 48 are unidentified because actual complete costs are unknown. Every one of the 78 priced group means is negative. These are grid counts, not estimated market probabilities. [Saved summary](../market/results/primary-01/summary.json) · [Completion receipt](../market/results/primary-01/completion.json).", "",
        "This report only reads saved outcomes. It changes no frozen source, input or economic result. The signed CPU effects remain small costs: the maximum omitted cent-ledger residual is $0.00230112 for B and $0.00036448 for C over any saved history. B and C tie in cent-denominated enterprise results in all 1,920 worlds and project-inclusive results in all 1,872 priced worlds. [Compact histories](../market/results/primary-01/compact-worlds.jsonl) · [Effects](../market/effect-profile.json). The separate [saved-archive audit](../review/market-results-independent-review.json) reconciles all 5,760 histories and 80 group summaries.", "",
        "## Same enterprise, three separate economic questions", "",
        "All new arms inherit the same strong first-asset enterprise. In the reference condition, A averages **−$149.73125 full-history profit** on $560 modeled collections and 28.75 accepted modeled outcomes. Adding back only its assumed $361.52 opening historical research cost gives **$211.78875 prospective profit** on the same histories. This decomposition restores no cash and credits no first-asset saving to the second asset. Full-history A profit is negative in 22 of 24 seeds; its 5th/50th/95th percentiles are −$351.467, −$124.41 and $13.4495. [Reference distributions](../market/results/primary-01/summary.json).", "",
        "The new oneoff allocations are $25.97/$103.85/$415.40 for low/reference/high, including prior discovery, new discovery, rejected candidates, construction, verification, integration, researcher contribution and model/tools. Maintenance is separate. These are declared scenarios, not observed invoices or empirical cost bounds. All actual categories remain unidentified. Search is charged once; completed research not financed by the enterprise remains an explicit outside research cost in project-inclusive profit. This adds no enterprise cash. [Cost profiles](../market/cost-profiles.json) · [Accounting implementation](../market/continuation.mjs).", "",
        "## Reference condition: full-cost replay distributions", "",
        "The replay checks affordability at week 26. Funding a research attempt does not establish that its benefits justify the expense. Values below are B minus A project-inclusive profit; C is identical at cent precision. Each row has 24 seeds.", "",
        "| Complete oneoff profile | Funded attempts | Mean difference | 5th percentile | Median | 95th percentile | Worst / best |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for cost in ["low", "reference", "high", "actual-unknown"]:
        g = next(g for g in groups if g["groupId"] == f"reference__{cost}__completed-research-replay")
        d = g["causal"]["B_minus_A_projectInclusiveProfitCents"]
        n = g["arms"]["B"]["counts"]["secondInvestmentPaidFromGeneratedResources"]
        md.append(f"| {cost} | {n}/24 | {money(d['mean'])} | {money(d['p05'])} | {money(d['median'])} | {money(d['p95'])} | {money(d['min'])} / {money(d['max'])} |")
    md.extend([
        "", "Reference-cost replay mean difference is −$107.559583… (exactly −$2,581.43 divided by 24); its unadjusted conditional Monte Carlo mean interval is [−$113.4509890, −$101.6681777]. Funded seeds are 8012, 8017 and 8021, with 13, 16 and 28 uses; their differences are −$92.53, −$145.24 and −$162.81. The adaptive branch makes no investment: each priced reference-condition project difference equals the completed prototype's full oneoff allocation (−$25.97/−$103.85/−$415.40), with any non-enterprise research cost explicitly retained. [All distributions and funded seeds](market-findings.json).", "",
        "## All 13 registered conditions, reference cost", "",
        "Each completed-research replay cell has 24 seeds. Every adaptive cell declines construction and has a −$103.85 project-inclusive difference. The identical adaptive value reflects the already completed research cost allocation, not a claim that a declining enterprise constructed a new asset.", "",
        "| Condition | Funded replays | Mean project difference | 5th percentile | Best |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in conditions:
        x = row["referenceCost"]["completed-research-replay"]
        d = x["BMinusAProjectInclusiveCents"]
        md.append(f"| {row['condition']['id']} | {x['BCounts']['secondInvestmentPaidFromGeneratedResources']}/24 | {money(d['mean'])} | {money(d['p05'])} | {money(d['max'])} |")
    md.extend([
        "", "The full 80-group distributions, all parameters and both policy views are preserved in [market-findings.json](market-findings.json), with exact source hashes. The finite experiment was not extended after these outcomes.", "",
        "## The preselected financing example and repayment threshold", "",
        "Seed 8001 starts with $1,000, including the modeled first asset's seed-financed history. At week 26 it has collected $340, accrued $618.78, holds $721.22 cash with zero unpaid obligations and a $200 reserve, and has **$82.74 of generated resources** after recognizing the seed-paid $361.52 opening history. Its low replay pays $25.97, leaving $56.77 of generated funds immediately after construction. It activates at week 27, serves 15 modeled uses, pays $1.50 upkeep and produces zero direct saving: B's full-history profit is −$65.20 against A's −$37.73, a −$27.47 difference. The reference $103.85 replay is **unaffordable** at this checkpoint: it has zero uses and its entire research cost remains outside enterprise cash. [Preselected full ledgers](../market/results/primary-01/predeclared-representatives.json).", "",
        "A necessary direct repayment condition is `uses × evidenced benefit per use ≥ complete oneoff cost + upkeep`, before downtime and other opportunity costs. At zero supported positive delivery benefit, no finite workload repays a positive cost through this channel. Using the preselected low replay's 15-use workload only as a disclosed analytical comparison, reference costs would require ($103.85 + $6.25)/15 = **$7.34 per use**; low costs require ($25.97 + $1.50)/15 = **$1.831333 per use**. This does not turn the unaffordable reference case into an executed investment.", "",
        "The incumbent has an inherited **assumption** of two remaining provider minutes, worth $2.179333 per use at $65.38/hour. It is not measured labor or a measured cap. Even eliminating all of that assumed residual labor on 15 uses yields $32.69, below the reference $110.10 total. Low-cost repayment would require about 1.68064 minutes (84.03% of the assumed residual) saved per use before downtime; no such saving was measured. The separate $0.25 tool cost is not assumed eliminated. The smallest missing evidence is a repeatable incremental seller benefit against the strong incumbent, complete measured costs, and enough credible recurrence within the same finite useful life. [Threshold derivation and caveats](market-findings.json) · [Inherited assumptions](../market/upstream/src/market.mjs).", "",
        "## The two positive realized differences are retained", "",
        "**Price $16, low cost, seed 8009: +$13.24.** The week-26 pause removes the enterprise offer. Buyer 10 changes from AI to DIY under the same logit draw, then later buys five more enterprise outcomes; buyer 5 buys two fewer. Net collections rise $48.00, delivery costs rise $7.29, and the second asset costs $25.97 plus $1.50 upkeep: $48.00 − $7.29 − $25.97 − $1.50 = $13.24. No initial bad-quality outcome is avoided here. This is a path-dependent pause/choice/feedback result.", "",
        "**Quality shock, low cost, seed 8017: +$7.67.** The pause diverts buyer 1's week-26 job to a human, avoiding A's rejected enterprise delivery and its adverse feedback. Later buyer choices yield two more accepted enterprise jobs (and the same total of five rejections). Collections rise $40.00, delivery costs rise $4.86, and second costs are $27.47: $40.00 − $4.86 − $27.47 = $7.67. The second asset does not change the quality rule.", "",
        "Both are genuine positive differences for these modeled intervention realizations. Both have zero direct asset saving, negative ex ante forecast, no financial admission, false direct repayment and false complete qualification; C earns exactly the same differences. No pause-only ablation was registered or run. The explanation follows the saved mission, feedback and choice traces; it does not establish a repeatable production-method gain. [Exact positive-case traces and arithmetic](market-findings.json) · [Full archived worlds](../market/results/primary-01/complete-paired-worlds.jsonl.gz).", "",
        "## Claim boundary", "",
        "This supports a completed, negative second-investment experiment: useful source assets were tested separately, the finite model sometimes had enough generated cash for a research attempt, and the tested second capability failed the registered complete-cost repayment standard. Actual complete research cost remains unidentified. Simulated collections are not commercial receipts; no actual customer collection or financial transaction occurred. The evidence establishes neither distinctive B-over-C improvement, a market equilibrium, unlimited growth nor self-acceleration.", "",
        "Reproduction: `python3 analysis/build_market_findings.py` reads the existing campaign archive and regenerates these two analysis files. It imports and executes no simulator. The mechanism diagnosis is post-outcome analysis, separately labeled from the preregistered campaign.", "",
    ])
    (OUT / "market-findings.md").write_text("\n".join(md))
    print(json.dumps({"created": ["analysis/market-findings.json", "analysis/market-findings.md"],
                      "groups": len(groups), "worlds": len(rows), "positiveRealizations": len(found),
                      "newSimulations": 0, "sourceEdits": 0}))


if __name__ == "__main__":
    main()
