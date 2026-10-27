# SPDX-License-Identifier: Apache-2.0
"""Bind executed frozen results to publication tables, figures and the offline demo.

This adapter performs arithmetic and presentation only. It neither reruns the
scientific simulator nor changes its selected policies or assumptions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from statistics import mean

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
DEMO = ROOT / "demo"
SCENARIOS = ("conservative", "central", "favorable")
LABEL = {"conservative": "Conservative", "central": "Central", "favorable": "Favorable"}
ARM = {
    "enterprise": ("Selected enterprise", "Entreprise sélectionnée"),
    "beta": ("Selected Beta only", "Bêta seul sélectionné"),
    "network": ("Selected network Alpha", "Alpha en réseau sélectionné"),
    "same-price-beta": ("Beta at network price", "Bêta au prix du réseau"),
    "local": ("Local Alpha counterfactual", "Comparaison Alpha local"),
    "no-paid-learning": ("No paid-work learning", "Sans apprentissage du travail payé"),
    "no-separate-research": ("No separate research C", "Sans recherche distincte C"),
}


def load(path):
    return json.loads((ROOT / path).read_text())


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bilingual(en, fr=None):
    return {"en": en, "fr": fr if fr is not None else en}


def usd(value, digits=0):
    if value is None:
        return "not defined"
    return ("−" if value < 0 else "") + "$" + f"{abs(value):,.{digits}f}"


def pct(value, digits=1):
    return "not defined" if value is None else f"{100 * value:.{digits}f}%"


def div(a, b):
    return a / b if b else None


def q(values, fraction):
    v = sorted(x for x in values if x is not None and math.isfinite(x))
    return v[math.floor((len(v) - 1) * fraction)] if v else None


def columns(*items):
    return [{"key": k, "label": label, **({"kind": kind} if kind else {})} for k, label, kind in items]


def distribution(scenario, arm, key):
    return CONF["scenarios"][scenario]["arms"][arm][key]


def contrast(scenario, comparator="same-price-beta", key="profitCents"):
    return CONF["scenarios"][scenario]["contrasts"]["network_minus_" + comparator]["differences"][key]


def rows(scenario, arm):
    return [r for r in CONF["rows"] if r["scenario"] == scenario and r["arm"] == arm]


def pool(scenario, arm):
    rr = rows(scenario, arm)
    n = len(rr)
    useful = sum(r["usefulAccepted"] for r in rr)
    expense = sum(r["costsCents"] for r in rr)
    net = sum(r["collectionsCents"] - r["refundsCents"] for r in rr)
    a = sum(r["A_jobCostCents"] for r in rr)
    all_costs = sum(r["A_jobCostCents"] + r["B_retentionReuseCostCents"] + r["C_optionalResearchCostCents"] + r["commonBusinessCostCents"] + r["historicalAllowanceCostCents"] for r in rr)
    assert all_costs == expense, (scenario, arm, "A/B/C partition")
    assert net - expense == sum(r["profitCents"] for r in rr), (scenario, arm, "profit reconciliation")
    assert all(r["sourceJobDevelopmentRechargedCents"] == 0 for r in rr)
    assert all(r["actualJobs"] == 0 and r["actualCollectionsUSD"] == 0 for r in rr)
    human = div(sum((r["usefulMeanHumanPriceCents"] or 0) * r["usefulAccepted"] for r in rr), useful)
    price = div(sum((r["usefulMeanOfferedPriceCents"] or 0) * r["usefulAccepted"] for r in rr), useful)
    margin = div(net - a, useful)
    # A transparent conditional threshold, not a fresh workload simulation.
    threshold = math.ceil(((expense - a) / n) / margin) if margin and margin > 0 else None
    contacts = sum(r["contacted"] for r in rr)
    ai = sum(r["aiChoices"] for r in rr)
    useful_per_ai = div(useful, ai)
    min_adoption = div(threshold, (contacts / n) * useful_per_ai) if threshold is not None and useful_per_ai else None
    return {
        "worlds": n, "useful_total": useful, "human": None if human is None else human / 100,
        "price": None if price is None else price / 100, "cost": None if not useful else expense / useful / 100,
        "a_per_useful": None if not useful else a / useful / 100,
        "net_per_useful": None if not useful else net / useful / 100,
        "adoption": div(ai, contacts), "acceptance": div(useful, sum(r["attemptedJobs"] for r in rr)),
        "loss": sum(r["profitCents"] < 0 for r in rr) / n,
        "insolvency": sum(bool(r["insolvent"]) for r in rr) / n,
        "conditional_break_even_useful": threshold, "conditional_min_adoption": min_adoption,
        "accounting": {
            "a_paid_work": a / n / 100,
            "b_retention": sum(r["B_retentionReuseCostCents"] for r in rr) / n / 100,
            "c_optional_research": sum(r["C_optionalResearchCostCents"] for r in rr) / n / 100,
            "common_business": sum(r["commonBusinessCostCents"] + r["historicalAllowanceCostCents"] for r in rr) / n / 100,
            "total_resource_cost": expense / n / 100, "net_collections": net / n / 100, "a_recharged": 0,
            "note": bilingual(
                f"Mean USD per independent world over the complete service and runoff horizon (n={n}). Common costs include the separately disclosed historical allowance. Every failed job, rejected retention and unpaid accrued resource bill remains charged. Refunds reduce collections. These means are not a median-world path.",
                f"Moyennes en USD par monde indépendant sur le service et la liquidation (n={n}). Les frais communs incluent l’allocation historique déclarée séparément. Échecs, conservations rejetées et dépenses engagées impayées restent comptés. Les remboursements réduisent les encaissements. Ces moyennes ne constituent pas un parcours médian."),
        },
    }


def paper_tables(data):
    t = data["tables"]
    main_rows, accounting_rows, price_rows, investment_rows, network_rows, moving_rows, threshold_rows = [], [], [], [], [], [], []
    for s in SCENARIOS:
        for arm in ("enterprise", "network"):
            p = METRICS[s][arm]
            d = distribution(s, arm, "profitCents")
            main_rows.append({"case": LABEL[s] + " / " + {"enterprise": "enterprise", "beta": "Beta", "network": "network"}[arm], "human": p["human"], "price": p["price"], "cost": p["cost"], "profit": d["median"] / 100, "loss": p["loss"], "insolvency": p["insolvency"]})
            selected = SELECT["selected"][s][arm]
            policy = selected["policy"]
            price_rows.append({"case": LABEL[s] + " / " + arm, "ratio": policy["priceRatio"], "scarcity": policy["scarcity"], "hurdle": policy["hurdle"] if policy["allowInvestment"] else None, "reserve": policy["reserveFactor"], "adoption": p["adoption"]})
        p = METRICS[s]["network"]
        ac = p["accounting"]
        accounting_rows.append({"case": LABEL[s], **{k: ac[k] / 1000 for k in ("a_paid_work", "b_retention", "c_optional_research", "common_business", "total_resource_cost", "net_collections")}})
        means = lambda k: distribution(s, "network", k)["mean"]
        investment_rows.append({"case": LABEL[s], "candidates": means("paidOriginCandidates"), "rights": means("rightsClearedCandidates"), "b": means("retentionCampaigns"), "c": means("separateResearchCampaigns"), "admissions": means("paidOriginAdmissions"), "false": means("alphaFalseAdmissions")})
        for comparator in ("same-price-beta", "local", "no-paid-learning", "no-separate-research"):
            d = contrast(s, comparator)
            useful = contrast(s, comparator, "usefulAccepted")
            precision=2 if max(abs(v) for v in d["meanMC95"])/100<100 else 0
            network_rows.append({"case": LABEL[s] + " / " + comparator, "mean": d["mean"] / 100, "interval": f"[{usd(d['meanMC95'][0]/100,precision)}, {usd(d['meanMC95'][1]/100,precision)}]", "useful": useful["mean"], "positive": CONF["scenarios"][s]["contrasts"]["network_minus_"+comparator]["positiveProfitDifference"]["rate"]})
        d = contrast(s, "static-beta")
        moving_rows.append({"case": LABEL[s], "upgrade": CONFIG[s]["betaUpgradeWeek"], "absorbed": CONFIG[s]["betaBundleAbsorption"], "retired": means("alphaRetired"), "mean": d["mean"] / 100, "interval": f"[{usd(d['meanMC95'][0]/100)}, {usd(d['meanMC95'][1]/100)}]"})
        threshold_rows.append({"case": LABEL[s], "net": p["net_per_useful"], "a": p["a_per_useful"], "workload": p["conditional_break_even_useful"], "adoption": p["conditional_min_adoption"]})
    t["primary"] = {"caption": "Fresh confirmation. Matched prices and full cost use the identical useful-delivery cohort; profit and loss are world-level distributions. USD, profit before tax.", "columns": columns(("case","Scenario / arm",None),("human","Human","money"),("price","Bid","money"),("cost","Full cost","money"),("profit","Median profit","money"),("loss","Loss","percent"),("insolvency","Insolvent","percent")), "rows": main_rows, "note": "Selected enterprise equals selected Beta exactly in every scenario. Full cost pools all accrued resource expense, including worlds with zero useful outcomes, over useful outcomes. Each arm has 128 independent confirmation worlds; repeated jobs are not independent worlds. The conservative cohort contains only three useful deliveries across those worlds."}
    t["accounting"] = {"caption":"Network-arm accounting, mean thousands of USD per world over the full horizon. A is charged once; B and C are additional.","columns":columns(("case","Scenario",None),("net_collections","Net collected","number"),("a_paid_work","A","number"),("b_retention","B","number"),("c_optional_research","C","number"),("common_business","Common","number"),("total_resource_cost","Total cost","number")),"rows":accounting_rows,"note":"Common includes the historical allowance; refunds reduce collections. Total cost reconciles A+B+C+common exactly before displayed rounding. No source-job development expense is recharged at retention."}
    t["pricing"] = {"caption":"Policies selected only on development worlds, then held fixed for confirmation. Price is a choice, not a fixed discount.","columns":columns(("case","Scenario / arm",None),("ratio","Base H ratio","number"),("scarcity","Scarcity","number"),("hurdle","B/C hurdle","number"),("reserve","Reserve factor","number"),("adoption","AI choice","percent")),"rows":price_rows,"note":"Base ratio applies to the matched task price; scarcity can change the actual quote. AI choice is contacted-prospect choice before support/capacity filtering. Published service rates do not calibrate adoption. An absent B/C hurdle indicates the no-investment policy."}
    t["investment"] = {"caption":"Paid-work learning and admission in the network arm, means per independent world. Candidates and apparent admissions are not guaranteed productive Alpha.","columns":columns(("case","Scenario",None),("candidates","Candidates","number"),("rights","Rights clear","number"),("b","B attempts","number"),("c","C attempts","number"),("admissions","Paid admissions","number"),("false","Latent invalid","number")),"rows":investment_rows}
    t["network"] = {"caption":"Paired network-minus-counterfactual effects on identical independent world seeds. Means and Monte Carlo 95% intervals; no parameter-uncertainty claim.","columns":columns(("case","Scenario / comparator",None),("mean","Mean profit gain","money"),("interval","MC95 interval",None),("useful","Useful gain","number"),("positive","Positive profit","percent")),"rows":network_rows,"widths":[.24,.16,.26,.10,.10],"long":True,"note":"Same-price Beta tests the retention-enabled policy at the same quote policy; local tests mandatory network availability. No asset was acquired in primary confirmation. No-paid-learning removes candidate emergence from paid jobs. No-separate-research removes optional C. Enterprise-versus-separately-selected Beta is a different price-and-investment policy comparison."}
    t["moving_beta"] = {"caption":"Moving Beta: assumed upgrade and observed modeled retirement, with network-minus-static total profit effect.","columns":columns(("case","Scenario",None),("upgrade","Upgrade week","number"),("absorbed","Bundle absorbed","percent"),("retired","Retired mean","number"),("mean","Mean total effect","money"),("interval","MC95 interval",None)),"rows":moving_rows,"widths":[.13,.10,.11,.10,.16,.22],"note":"With no acquired Alpha in primary confirmation, this contrast measures ordinary delivery and policy effects of the assumed Beta upgrade. It does not establish economic survival or erosion of an acquired stock. Upgrade capability and timing are assumptions, not announced model releases."}
    t["threshold"] = {"caption":"Conditional network break-even arithmetic at executed case mix and conversion/cost ratios. These are thresholds, not fresh demand reruns.","columns":columns(("case","Scenario",None),("net","Net receipt/useful","money"),("a","A expense/useful","money"),("workload","Required useful","number"),("adoption","Required AI choice","percent")),"rows":threshold_rows,"note":"Required useful = ceiling(mean non-A expense / observed net receipt less A expense per useful). Non-A spending is held fixed. Required AI choice additionally holds contacted workload and useful conversion fixed. Demand, congestion and acceptance can change when those assumptions change."}
    reviewed_path=ROOT/"results/analysis/confirmed_break_even.json"
    if reviewed_path.exists():
        reviewed=json.loads(reviewed_path.read_text())
        assert reviewed["confirmationSHA256"]==sha(ROOT/"results/confirmation.json")
        assert reviewed["policyHistoriesReconciled"]==CONF["policyHistories"]
        threshold_rows=[]
        for s in ("central","favorable"):
            z=reviewed["thresholds"][s]["enterprise"]
            threshold_rows.append({"case":LABEL[s],"floor":z["minimumMeanAcceptedPriceUSDAtFixedMix"]["median"],"ceiling":z["maximumCompleteCostPerAcceptedUSDAtCurrentReceipts"]["median"],"count":z["minimumAcceptedAtFixedProspectExposure"]["median"],"adoption":z["minimumQualifiedBuyerAcceptanceAtFixedExposure"]["median"]})
        t["threshold"]={"caption":"Independently reconciled financial break-even, selected enterprise. Medians across worlds with finite thresholds, holding realized task mix, exposure, behavior and collection ratios fixed.","columns":columns(("case","Scenario",None),("floor","Required price","money"),("ceiling","Max complete cost","money"),("count","Accepted count","number"),("adoption","Qualified AI choice","percent")),"rows":threshold_rows,"note":"Counts cover the complete 104-week service horizon at fixed prospect exposure, not a monthly requirement. Financial acceptance is the apparent acceptance that generates invoices; later refunds remain charged. Main outcome-cost tables instead use useful ground-truth outcomes. One central world and 125 conservative worlds have no accepted work and no finite price threshold. The other three conservative worlds require a median $54,924.89 versus $12,900.78 offered; all conservative worlds lose money. Do not infer conservative viability from selected survivors. Qualified means scope-supported contacted offers; its denominator differs from all-prospect adoption. No demand or pricing response is rerun."}
    meta_rows = [{"campaigns":x["futureCampaigns"],"baseline":x["baselineCompleteCostPerUsefulCents"]/100,"retained":x["retainedCompleteCostPerUsefulCents"]/100,"saving":x["expectedNetResourceSavingCents"]/100,"quota":max(x["maximumFractionOfLifetimeCapacity"].values()),"feasible":"Yes" if x["necessaryCapacityBoundSatisfied"] else "No"} for x in META["amortization"]]
    t["campaign"]={"caption":"Separate fresh-campaign experiment: full optional-C lifecycle amortization, conditional on the supplied useful screen. USD per useful capability and total resource saving.","columns":columns(("campaigns","Future campaigns","number"),("baseline","Beta cost/useful","money"),("retained","With C/useful","money"),("saving","Net resource saving","money"),("quota","Max quota factor","number"),("feasible","Capacity bound",None)),"rows":meta_rows,"note":"The asset lifecycle is charged in full. A necessary aggregate quota bound is not a sufficient scheduler guarantee. These are independent modeled invention campaigns, not descendant jobs, sales or evidence of arbitrary new algorithm discovery."}
    fixed_stresses={"humanReference":7167.1,"buyerValueMedian":15000,"prospectsMonthly":0,"commonError":.2,"tokenMultiplier":50,"collectionDelayWeeks":12,"assetProductiveProbability":0,"retentionCostMultiplier":25,"paidLearningProbability":0,"rightsClearedProbability":.25,"betaBundleAbsorption":1,"assetLifetimeWeeks":13,"validatorHoursWeekly":300,"seedCapital":20000}
    stress_rows=[]
    names={"humanReference":"Human reference, USD", "buyerValueMedian":"Buyer value, USD", "prospectsMonthly":"Prospects/month", "commonError":"Common error probability", "tokenMultiplier":"Token-resource factor", "collectionDelayWeeks":"Collection delay, weeks", "assetProductiveProbability":"Productive-candidate probability", "retentionCostMultiplier":"B resource factor", "paidLearningProbability":"Paid-candidate probability", "rightsClearedProbability":"Rights-clearance probability", "betaBundleAbsorption":"Beta bundle absorption", "assetLifetimeWeeks":"Useful life, weeks", "validatorHoursWeekly":"Validator CPU-hours/week", "seedCapital":"Seed capital, USD"}
    for case in SENS["cases"]:
        if fixed_stresses.get(case["parameter"])==case["value"]:
            z=case["summary"];d=z["contrast"]["differences"]["profitCents"]
            stress_rows.append({"case":names[case["parameter"]]+" = "+f"{case['value']:g}","profit":z["network"]["profitCents"]["median"]/100,"insolvent":z["network"]["insolvent"]["rate"],"gain":d["mean"]/100})
    t["sensitivity"]={"caption":"Selected predeclared adverse or null stresses, central network policy held fixed; 20 fresh paired worlds per condition.","columns":columns(("case","Changed assumption",None),("profit","Median profit","money"),("insolvent","Insolvent","percent"),("gain","Mean gain vs Beta","money")),"rows":stress_rows,"note":"Selection of displayed rows is by a fixed parameter/value list in the publication adapter, not by favorable outcomes. All executed cases, including positive and negative findings, remain in results/sensitivity.json. The same 20 seeds are paired across settings; rows are not pooled as independent replications."}
    t["policy"]={"caption":"Frozen design and independent data separation.","columns":columns(("item","Design element",None),("value","Specification",None)),"widths":[.27,.65],"rows":[{"item":"Horizon","value":"104 service weeks plus 24 runoff weeks; three heterogeneous agents; identical aggregate resources within each pair."},{"item":"Development","value":f"{len(PROTOCOL['selection']['seeds'])} world seeds per scenario. Original 45-policy screen; pre-confirmation symmetry amendment gives 40 network and 20 Beta policies (60 unique). Score = mean discounted accrued profit + 0.25 × worst-decile mean."},{"item":"Risk constraint","value":PROTOCOL["objective"]["trainingConstraint"]},{"item":"Confirmation","value":f"{len(PROTOCOL['confirmation']['seeds'])} disjoint seeds per scenario; twelve prespecified policy/ablation histories per world."},{"item":"Sensitivity","value":f"{len(SENS['cases'])} one-factor cases, {len(PROTOCOL['sensitivity']['seeds'])} paired fresh seeds each; selected central network policy held fixed."},{"item":"Capacity","value":"18 development capacity conditions, 12 seeds each; hardware choice locked per demand level before 12 new confirmation seeds. Training and holdout rows are not pooled."},{"item":"Fresh invention","value":f"{META['campaigns']} independent {META['candidatesPerCampaign']}-candidate campaigns with exact zero-increment control."}]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--tables-only",action="store_true")
    parser.add_argument("--finalize",action="store_true",help="Only after the explicit narrative review file is complete.")
    args=parser.parse_args()
    global CONF,SELECT,PROTOCOL,CONFIG,META,SENS,SCALE,METRICS
    F=load("protocol/freeze.json")
    for name,digest in F["sourceHashes"].items():
        assert sha(ROOT/name)==digest, "Frozen source changed: "+name
    PROTOCOL=load("protocol/protocol.json")
    SELECT=load("protocol/selected_policies.json")
    CONF=load("results/confirmation.json")
    META=load("results/meta/summary.json")
    SENS=load("results/sensitivity.json")
    SCALE=load("results/scale.json")
    assert CONF["protocolSHA256"]==sha(ROOT/"protocol/freeze.json")
    assert CONF["selectionSHA256"]==sha(ROOT/"protocol/selected_policies.json")
    assert CONF["audit"]["passed"]
    if (ROOT/"protocol/beta_symmetry_amendment.json").exists():
        assert SELECT["amendmentSHA256"]==sha(ROOT/"protocol/beta_symmetry_amendment.json")
        assert SELECT["expandedBetaTrainingSHA256"]==sha(ROOT/"results/beta_symmetry_training.json")
    CONFIG={x["id"]:x for x in PROTOCOL["scenarios"]}
    METRICS={s:{a:pool(s,a) for a in CONF["scenarios"][s]["arms"]} for s in SCENARIOS}
    source={p:sha(ROOT/p) for p in ("protocol/freeze.json","protocol/selected_policies.json","results/confirmation.json","results/meta/summary.json","results/sensitivity.json","results/scale.json")}
    for p in ("results/analysis/confirmed_break_even.json","results/analysis/development_witness.json","results/analysis/development_witness_thresholds.json","results/analysis/meta_readout.json","results/analysis/sensitivity_readout.json"):
        if (ROOT/p).exists():source[p]=sha(ROOT/p)
    if (ROOT/"protocol/beta_symmetry_amendment.json").exists():
        source.update({p:sha(ROOT/p) for p in ("protocol/beta_symmetry_amendment.json","protocol/initial_selected_policies.json","results/beta_symmetry_training.json")})
    save(PAPER/"publication_metrics.json",{"sourceHashes":source,"metrics":METRICS,"generatedBy":"paper/bind_results.py","noScientificRerun":True})
    data=json.loads((PAPER/"paper_data.json").read_text())
    paper_tables(data)
    if (ROOT/"protocol/beta_symmetry_amendment.json").exists():
        source.update({p:sha(ROOT/p) for p in ("protocol/beta_symmetry_amendment.json","protocol/initial_selected_policies.json","results/beta_symmetry_training.json")})
        data["tables"]["policy"]["rows"].insert(2,{"item":"Pre-confirmation fairness amendment","value":"Original 45-policy screen preserved. Beta expanded to the same price, scarcity and reserve choices: 20 Beta plus 40 network policies, 60 unique policies. Network winners and all model parameters unchanged; final selection locked before untouched confirmation seeds."})
    data["source_binding"]["results"]=source
    narrative_path=PAPER/"narrative_overrides.json"
    if narrative_path.exists():
        data["narrative"].update(json.loads(narrative_path.read_text()))
    if args.finalize:
        from build_paper import NARRATIVE
        assert all(data["narrative"].get(k) for k in NARRATIVE), "Complete explicit narrative review before finalization."
        data["status"]="bound_to_frozen_results"
        data["version"]="1.0 · modeled confirmation"
    if not args.tables_only:
        figure_specs={
          "Economics":("economics","Matched useful-outcome prices and full resource cost, alongside independent-world profit distributions. Full cost includes failed and zero-useful worlds; profit is not a subtraction of unpaired medians."),
          "Investment":("investment","Mean A/B/C/common expense and candidate-to-retention counts. Paid development is charged once. Apparent admission remains distinct from latent productive value."),
          "Network":("network","Paired total economic effects on fresh confirmation worlds. Same-price Beta tests the retention-enabled policy; local tests network availability. No asset was acquired in primary confirmation. Intervals are conditional Monte Carlo mean intervals."),
          "Campaign":("campaign","The separate experiment protocol reduces variable evaluation expense but fails full lifecycle recovery under the registered lifetime and quota assumptions. Campaign volume is not customer demand."),
          "Sensitivity":("sensitivity","Prespecified fragility cases and fresh capacity holdouts. The 12-world capacity intervals remain broad and do not establish a low-risk scale guarantee."),
        }
        data["figures"]={k:{"path":"paper/figures/"+name+".pdf","width":1,"caption":caption} for k,(name,caption) in figure_specs.items()}
    save(PAPER/"paper_data.json",data)
    if not args.tables_only:
        from publication_visuals import make_figures
        make_figures(ROOT,PROTOCOL,CONF,SELECT,META,SENS,SCALE,METRICS)
        from publication_demo import make_demo
        save(DEMO/"demo_data.json",make_demo(ROOT,PROTOCOL,CONF,SELECT,META,SENS,SCALE,METRICS))
    print("Bound verified result arithmetic; narrative review and final status remain explicit.")


if __name__=="__main__":
    main()
