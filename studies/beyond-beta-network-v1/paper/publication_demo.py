# SPDX-License-Identifier: Apache-2.0
"""Translate canonical result records into an offline EN/FR evidence viewer."""
from __future__ import annotations

import json
import math
from collections import defaultdict

SCENARIOS=("conservative","central","favorable")
ARM_LABELS={
 "enterprise":("Selected enterprise","Entreprise sélectionnée"),
 "beta":("Selected Beta only","Bêta seul sélectionné"),
 "network":("Selected network Alpha","Alpha en réseau sélectionné"),
 "same-price-beta":("Beta at network price","Bêta au prix du réseau"),
 "local":("Local Alpha counterfactual","Comparaison Alpha local"),
 "no-paid-learning":("No paid-work learning","Sans apprentissage du travail payé"),
 "no-separate-research":("No separate research C","Sans recherche distincte C"),
}
STRESS_LABELS={
 "humanReference":("Matched human-team price","Prix de l’équipe humaine comparable"),
 "buyerValueMedian":("Median buyer value","Valeur médiane pour l’acheteur"),
 "prospectsMonthly":("Monthly prospective buyers","Acheteurs potentiels par mois"),
 "trustMax":("Maximum trust burden","Coût maximal du manque de confiance"),
 "initialCompletionBelief":("Perceived AI completion probability","Probabilité perçue d’achèvement IA"),
 "humanCompletionBelief":("Perceived human completion probability","Probabilité perçue d’achèvement humain"),
 "commonError":("Shared interpretation failure","Erreur d’interprétation commune"),
 "initialError":("Initial error probability","Probabilité d’erreur initiale"),
 "semanticDetection":("Semantic error detection","Détection des erreurs sémantiques"),
 "improvementProbability":("Candidate improvement probability","Probabilité d’amélioration du candidat"),
 "tokenMultiplier":("Token-resource multiplier","Multiplicateur des ressources en jetons"),
 "computeMultiplier":("Compute-resource multiplier","Multiplicateur des ressources de calcul"),
 "collectionDelayWeeks":("Collection delay, weeks","Délai d’encaissement, semaines"),
 "assetConstructionMultiplier":("Optional research workload multiplier","Multiplicateur de travail de recherche facultative"),
 "assetProductiveProbability":("Candidate productive-state probability","Probabilité de productivité du candidat"),
 "assetTransferSuccess":("Transfer success probability","Probabilité de réussite du transfert"),
 "assetLifetimeWeeks":("Useful lifetime, weeks","Durée utile, semaines"),
 "assetMaintenanceWeekly":("Weekly asset upkeep","Entretien hebdomadaire de la capacité"),
 "bundleEffect":("Bundle resource factor (lower costs less)","Facteur de ressources de l’ensemble (bas = moins coûteux)"),
 "familyScreenIncrement":("Additional mechanical-screen sensitivity","Sensibilité supplémentaire du filtrage mécanique"),
 "betaBundleAbsorption":("Bundle advantage absorbed by Beta","Avantage de l’ensemble absorbé par Bêta"),
 "betaUpgradeWeek":("Hypothetical Beta upgrade week","Semaine d’amélioration hypothétique de Bêta"),
 "betaUpgradeResourceFactor":("Future Beta resource factor","Facteur de ressources du futur Bêta"),
 "copyHazardWeekly":("Weekly copying/overlap hazard","Risque hebdomadaire de copie ou chevauchement"),
 "assetTransferCost":("Adaptation allowance per transfer","Allocation d’adaptation par transfert"),
 "alphaProbeCount":("Fresh paired Alpha probes","Épreuves Alpha inédites appariées"),
 "alphaSystematicRiskReserveCentsPerUse":("Systematic-risk deduction per use","Déduction de risque systématique par usage"),
 "paidLearningProbability":("Candidate emergence per accepted job","Émergence d’un candidat par travail accepté"),
 "rightsClearedProbability":("Reusable-rights clearance probability","Probabilité de droits réutilisables établis"),
 "retentionCostMultiplier":("Additional retention workload multiplier","Multiplicateur du travail supplémentaire de conservation"),
 "forecastBetaErosionWeekly":("Forecast weekly Alpha erosion from Beta","Érosion hebdomadaire prévue d’Alpha par Bêta"),
 "acquisitionCostPerProspect":("Acquisition cost per prospect","Coût d’acquisition par prospect"),
 "seedCapital":("Initial seed capital","Capital initial"),
 "concurrency":("Concurrent workflow slots","Places de travail simultanées"),
 "inputQuotaWeekly":("Weekly input-token quota","Quota hebdomadaire de jetons d’entrée"),
 "outputQuotaWeekly":("Weekly output-token quota","Quota hebdomadaire de jetons de sortie"),
 "cpuHoursWeekly":("Weekly solver CPU-hours","Heures CPU de solveur par semaine"),
 "validatorHoursWeekly":("Weekly validator CPU-hours","Heures CPU de validation par semaine"),
 "workflowLatencyMultiplier":("Workflow duration factor","Facteur de durée du travail"),
 "deadlineMultiplier":("AI turnaround-window factor","Facteur de délai de livraison IA"),
 "setupCost":("Setup expense","Dépense de mise en place"),
}


def bi(en,fr=None):return {"en":en,"fr":fr if fr is not None else en}
def usd(v):return ("−" if v<0 else "")+"$"+f"{abs(v):,.2f}"
def read(root,path):return json.loads((root/path).read_text())


def example_origin(run,protocol,selection_note):
    history=run["histories"]
    paid=next((c for c in history["campaigns"] if c["sourceKind"]=="B_paid_job_retention" and c["admitted"]),None)
    if paid is None:paid=next((c for c in history["campaigns"] if c["sourceKind"]=="B_paid_job_retention"),None)
    raw=next((c for c in history["paidCandidates"] if paid and c["originJobId"]==paid["originJobId"]),None)
    first_proposal=next((d for d in history["decisions"] if d["sourceKind"]=="B_paid_job_retention"),None)
    if raw is None and first_proposal:
        raw=next((c for c in history["paidCandidates"] if c["id"]==first_proposal["rawCandidateId"]),None)
    if raw is None:raw=next(iter(history["paidCandidates"]),None)
    proposal=next((d for d in history["decisions"] if raw and d.get("rawCandidateId")==raw["id"]),None)
    job=next((j for j in history["jobs"] if j["id"]==(raw or {}).get("originJobId")),None)
    if job is None:job=next((j for j in history["jobs"] if j["accepted"]),next(iter(history["jobs"]),None))
    if job is None:
        empty=bi("No delivery or candidate occurred in this recorded world.","Aucune livraison ni aucun candidat dans ce monde enregistré.")
        return {"id":f"seed {run['seed']}","agent":"","title":empty,**{k:empty for k in ("paid_outcome","beta_work","restriction","candidate","already_paid","additional_retention","optional_research","evidence","admission")}}
    invoice=next((i for i in history["invoices"] if i["jobId"]==job["id"]),None)
    collected=invoice is not None and invoice["collectedWeek"] is not None
    classes={j["id"]:j["name"] for j in protocol["jobs"]}
    source=f"{run['config']['id']} / {run['arm']} / seed {run['seed']} / {job['id']}"
    collection_en=(f"Quoted {usd(job['priceCents']/100)}; collected in week {invoice['collectedWeek']}" if collected else f"Quoted {usd(job['priceCents']/100)}; no collection recorded")
    collection_fr=(f"Prix {usd(job['priceCents']/100)} ; encaissé en semaine {invoice['collectedWeek']}" if collected else f"Prix {usd(job['priceCents']/100)} ; aucun encaissement enregistré")
    if invoice and invoice["refunded"]:collection_en+="; subsequently refunded";collection_fr+=" ; remboursé ensuite"
    no_candidate=bi("No reusable candidate emerged in this job.","Aucun candidat réutilisable n’est issu de ce travail.")
    candidate=bi(" + ".join(raw["keys"])+("; rights cleared" if raw["rightsCleared"] else "; sharing rights not cleared")," + ".join(raw["keys"])+(" ; droits vérifiés" if raw["rightsCleared"] else " ; droits de partage non établis")) if raw else no_candidate
    if paid:
        assessment=paid["review"]["assessment"]
        cost=paid["constructionCents"]/100;budget=paid["forecast"]["completeCostCents"]/100
        retention=bi(f"Initial retention plus paid assessment {usd(cost)}, committed in week {paid['week']}; complete forward B/C budget {usd(budget)}. Source-job A is recharged $0.",f"Conservation initiale et évaluation payée {usd(cost)}, engagées en semaine {paid['week']} ; budget B/C prospectif complet {usd(budget)}. A facturé à nouveau : 0 $.")
        evidence=bi(f"{assessment['independentClusters']} fresh paired mission clusters; assessed lifetime lower net bound {usd(assessment['lowerLifetimeNetCents']/100)}. Model-conditional evidence, not an empirical frontier trial.",f"{assessment['independentClusters']} groupes de missions inédites appariées ; borne nette de durée évaluée {usd(assessment['lowerLifetimeNetCents']/100)}. Preuve conditionnelle au modèle, pas essai empirique d’un modèle de pointe.")
        admission=bi(f"Recorded admission: {bool(paid['admitted'])}. Latent productive state in the simulator: {bool(paid['productive'])}. Admission and truth can disagree.",f"Admission enregistrée : {bool(paid['admitted'])}. État productif latent dans le simulateur : {bool(paid['productive'])}. Admission et vérité peuvent diverger.")
    elif proposal:
        extraction=proposal["construction"]["costCents"]/100
        assessment_reserve=(proposal["buildCents"]-proposal["construction"]["costCents"])/100
        retention=bi(f"First recorded proposal for this paid candidate, week {proposal['week']}: extraction/generalization {usd(extraction)}, initial assessment reserve {usd(assessment_reserve)}, complete remaining B budget {usd(proposal['completeCostCents']/100)}. Available cash {usd(proposal['availableBeforeCents']/100)}. No B amount was committed; A recharged $0.",f"Première proposition enregistrée pour ce candidat payé, semaine {proposal['week']} : extraction/généralisation {usd(extraction)}, réserve d’évaluation initiale {usd(assessment_reserve)}, budget B restant complet {usd(proposal['completeCostCents']/100)}. Fonds disponibles {usd(proposal['availableBeforeCents']/100)}. Aucun B engagé ; A refacturé : 0 $.")
        evidence=bi(f"No paid Alpha assessment occurred. The proposal forecasts gross benefit {usd(proposal['forecastGrossBenefitCents']/100)}, displaced-delivery contribution {usd(proposal['forecastDisplacementCostCents']/100)} and net value after all remaining cost {usd(proposal['forecastNetCents']/100)}. These are the controller's modeled forecasts, not realized asset gains.",f"Aucune évaluation Alpha payée. La proposition prévoit un avantage brut {usd(proposal['forecastGrossBenefitCents']/100)}, une contribution de livraison déplacée {usd(proposal['forecastDisplacementCostCents']/100)} et une valeur nette après coûts restants {usd(proposal['forecastNetCents']/100)}. Prévisions modélisées du contrôleur, pas gains d’actif réalisés.")
        admission=bi(f"Decision: {proposal['decision']}. The proposal stopped before validation/admission; affordability alone does not justify retention. No peer benefit is imputed.",f"Décision : {'conserver les fonds' if proposal['decision']=='retain-cash' else proposal['decision']}. Arrêt avant validation/admission ; disposer des fonds ne suffit pas à justifier la conservation. Aucun bénéfice d’un autre agent n’est imputé.")
    else:
        retention=bi("No retention campaign was selected for this job's candidate; no extra development is imputed.","Aucune campagne de conservation sélectionnée pour ce candidat ; aucun développement supplémentaire n’est imputé.")
        evidence=bi("No paid Alpha assessment for this candidate in the recorded path.","Aucune évaluation Alpha payée pour ce candidat dans ce parcours.")
        admission=bi("Not admitted from this job. Hold, deferral and rejection are valid outcomes.","Aucune admission issue de ce travail. Conservation des fonds, report et rejet sont des résultats valides.")
    return {"id":source,"agent":job["agent"],"title":bi(classes[job["classId"]],{"kernel":"Politique de planification avec évaluation inédite","coupled":"Politique couplée et contraintes liées","rolling":"Politique à horizon glissant sous incertitude"}[job["classId"]]),
      "paid_outcome":bi(collection_en+". "+selection_note["en"],collection_fr+". "+selection_note["fr"]),
      "beta_work":bi("Competent frontier reasoning, established solvers, formulation, candidate search, critique, correction and a common original-constraint check; no routine human provider review.","Raisonnement de pointe compétent, solveurs établis, formulation, recherche, critique, correction et vérification des contraintes initiales ; aucun contrôle humain habituel du fournisseur."),
      "restriction":bi("Reconstruct a purpose-preserving optimization policy within the declared task and resource window. New physical or unstated requirements remain outside scope.","Reconstruire une politique d’optimisation préservant l’objectif dans le périmètre et les ressources déclarés. Les exigences physiques ou non énoncées restent hors périmètre."),
      "candidate":candidate,"already_paid":bi(f"A job resources: {usd(job['costCents']/100)}. This includes the learning/development used for delivery; candidate emergence adds zero charge.",f"Ressources A : {usd(job['costCents']/100)}. Apprentissage et développement nécessaires à la livraison inclus ; l’émergence du candidat n’ajoute aucun coût."),
      "additional_retention":retention,"optional_research":bi("No C charge is required merely because this job left a candidate. Separately selected C projects remain in the enterprise ledger.","Aucun coût C n’est requis du seul fait qu’un candidat est apparu. Les projets C distincts sélectionnés restent dans la comptabilité de l’entreprise."),"evidence":evidence,"admission":admission}


def variable_contribution(run,agent):
    h=run["histories"];jobs=[j for j in h["jobs"] if j["agent"]==agent];ids={j["id"] for j in jobs}
    invoices=[i for i in h["invoices"] if i["jobId"] in ids]
    receipt=sum(i["amountCents"] for i in invoices if i["collectedWeek"] is not None and not i["refunded"])
    invoice_refs={"payment-processing:"+i["id"] for i in invoices}
    fee=sum(b["amountCents"] for b in h["bills"] if b["reference"] in invoice_refs)
    adaptation=sum(t["costCents"] for t in h["transfers"] if t["agent"]==agent)
    return (receipt-fee-sum(j["costCents"] for j in jobs)-adaptation)/100


def trajectory(run,baseline,protocol):
    h=run["histories"];assets=run["assets"];events=[];caps=[]
    for campaign in h["campaigns"]:
        source="B" if campaign["sourceKind"]=="B_paid_job_retention" else "C + B"
        events.append({"week":campaign["week"],"title":bi(source+" commitment", "Engagement "+source),"description":bi(f"{campaign['id']}; initial construction/retention and assessment {usd(campaign['constructionCents']/100)}; available before decision {usd(campaign['forecast']['availableBeforeCents']/100)}; already-paid A recharged $0.",f"{campaign['id']} ; construction/conservation initiale et évaluation {usd(campaign['constructionCents']/100)} ; disponible avant décision {usd(campaign['forecast']['availableBeforeCents']/100)} ; A refacturé : 0 $."),"amount":campaign["constructionCents"]/100})
        caps.append({"title":bi(" + ".join(campaign["keys"])),"description":bi(f"{source} origin. Complete prospective remaining lifecycle budget, including reserved fresh assessment and upkeep; actual expenses are in the A/B/C enterprise panel. Admission here is historical; current eligibility depends on the selected Beta-phase panel.",f"Origine {source}. Budget prospectif complet du cycle restant, évaluation inédite réservée et entretien inclus ; les dépenses effectives figurent dans A/B/C. L’admission indiquée est historique ; l’admissibilité courante dépend du panneau de phase Bêta."),"status":bi("HISTORICAL MODELED ADMISSION" if campaign["admitted"] else "MODELED REJECTED","ADMISSION MODÉLISÉE HISTORIQUE" if campaign["admitted"] else "REJET MODÉLISÉ"),"available":bool(campaign["admitted"]),"complete_cost":campaign["forecast"]["completeCostCents"]/100,"cost_label":bi("Complete forward B/C budget: ","Budget B/C prospectif complet : "),"falsifier":bi("Fresh paired advantage fails to cover remaining cost, rights or purpose bridge fails, transfer adds no value, or advancing Beta removes the advantage.","L’avantage apparié inédit ne couvre pas les coûts restants, droits ou lien avec l’objectif échouent, transfert sans valeur ou Bêta efface l’avantage.")})
        if campaign.get("originInvoiceId"):
            invoice=next(i for i in h["invoices"] if i["id"]==campaign["originInvoiceId"])
            events.append({"week":invoice["collectedWeek"],"title":bi("Source job collected","Travail source encaissé"),"description":bi(invoice["id"]+"; collection precedes the retention commitment.",invoice["id"]+" ; encaissement antérieur à l’engagement de conservation."),"amount":invoice["amountCents"]/100})
    if not caps:
        proposal=next((d for d in h["decisions"] if d["sourceKind"]=="B_paid_job_retention"),None)
        if proposal:
            caps.append({"title":bi(" + ".join(proposal["keys"])),"description":bi(f"First paid-candidate proposal in the recorded world, from {proposal['originJobId']}. Extraction alone costs {usd(proposal['construction']['costCents']/100)}; paid confirmation, upkeep and displaced delivery must also be justified. Forecast net value {usd(proposal['forecastNetCents']/100)}. No retention expense was committed.",f"Première proposition issue d’un travail payé de ce monde, {proposal['originJobId']}. Extraction seule : {usd(proposal['construction']['costCents']/100)} ; confirmation, entretien et livraison déplacée doivent aussi être justifiés. Valeur nette prévue {usd(proposal['forecastNetCents']/100)}. Aucune conservation engagée."),"status":bi("RETAIN CASH · BEFORE VALIDATION","CONSERVER LES FONDS · AVANT VALIDATION"),"available":False,"complete_cost":proposal["completeCostCents"]/100,"cost_label":bi("Proposed remaining B budget, not spent: ","Budget B restant proposé, non dépensé : "),"falsifier":bi("The controller's forecast does not cover complete remaining cost and displaced useful work. This is an economic rejection, not an observed frontier-model failure.","La prévision ne couvre pas les coûts restants et le travail utile déplacé. Rejet économique, pas échec observé d’un modèle de pointe.")})
            events.append({"week":proposal["week"],"title":bi("Retain cash before Alpha assessment","Conserver les fonds avant l’évaluation Alpha"),"description":bi(f"Proposed B budget {usd(proposal['completeCostCents']/100)} versus available cash {usd(proposal['availableBeforeCents']/100)}; forward net {usd(proposal['forecastNetCents']/100)}. Committed expense: $0.",f"Budget B proposé {usd(proposal['completeCostCents']/100)}, fonds disponibles {usd(proposal['availableBeforeCents']/100)} ; valeur nette prévue {usd(proposal['forecastNetCents']/100)}. Dépense engagée : 0 $."),"amount":0})
    if not events:events=[{"week":run["config"]["weeks"],"title":bi("No B/C campaign chosen","Aucune campagne B/C choisie"),"description":bi("This recorded policy retained cash or continued delivery without a capability commitment.","Cette politique a conservé les fonds ou poursuivi les livraisons sans engager de capacité."),"amount":0}]
    events.sort(key=lambda e:e["week"])
    cash=[{"week":b["week"],"cash":b["cashCents"]/100,"available":b["availableCents"]/100,"investment_spend":sum(x["amountCents"] for x in h["bills"] if x.get("lane") in ("B_retention_reuse","C_optional_research") and x["paid"] and x["paidWeek"]<=b["week"])/100} for b in h["balances"]]
    recipients=[]
    for agent in protocol["agents"]:
        aid=agent["id"];jobs=[j for j in h["jobs"] if j["agent"]==aid];transfers=[t for t in h["transfers"] if t["agent"]==aid]
        equivalent=[k for k,v in agent["baseline"].items() if v]
        recipients.append({"id":aid,"baseline":bi("Expert Beta, strong ordinary solvers; additional initial equivalents: "+(", ".join(equivalent) or "none declared")+".","Bêta expert et solveurs ordinaires solides ; équivalents supplémentaires initiaux : "+(", ".join(equivalent) or "aucun déclaré")+"."),"availability":bi("All admitted shareable network capabilities are discoverable subject to current rights, scope and freshness.","Toute capacité partageable admise est découvrable sous réserve des droits, du périmètre et de la fraîcheur."),"adoption":bi(f"{len(transfers)} paid adaptation attempts; {sum(t['success'] for t in transfers)} successful. Use is optional.",f"{len(transfers)} tentatives d’adaptation payées ; {sum(t['success'] for t in transfers)} réussies. Usage facultatif."),"fresh_useful":sum(j["useful"] for j in jobs),"incremental_gain":variable_contribution(run,aid)-variable_contribution(baseline,aid),"adaptation_cost":sum(t["costCents"] for t in transfers)/100})
    phases=[];upgrade=run["config"]["betaUpgradeWeek"]
    for week in sorted(set([0,max(0,upgrade-1),min(upgrade,run["config"]["weeks"]-1),run["config"]["weeks"]-1])):
        retired={e["id"] for e in h["network"] if e["week"]<=week and e["type"]=="retired"}
        version=next((e["betaVersion"] for e in reversed(h["network"]) if e["week"]<=week and e["type"]=="hypothetical-beta-upgrade"),run["config"]["betaVersion"])
        current={}
        for e in h["alphaAssessments"]:
            if e["week"]<=week:current[e["assetId"]]=e
        admitted_ids={e["id"] for e in h["network"] if e["week"]<=week and e["type"] in ("modeled-admission","modeled-revalidation")}
        eligible=sum(e["verdict"]=="admit" and e["betaVersion"]==version and e["expiresAt"]>week and aid not in retired and aid in admitted_ids for aid,e in current.items())
        b=next(x for x in h["balances"] if x["week"]==week);bb=next(x for x in baseline["histories"]["balances"] if x["week"]==week)
        phases.append({"week":week,"label":bi(f"Week {week}",f"Semaine {week}"),"baseline":bi(version),"admitted_eligible":eligible,"retired":len(retired),"incremental_gain":(b["fullCostProfitCents"]-bb["fullCostProfitCents"])/100,"note":bi(f"Recorded paired cumulative profit difference versus same-price Beta in seed {run['seed']}; a trajectory snapshot, not an average or a pure asset-decay estimate.",f"Différence cumulée de bénéfice face à Bêta au même prix, graine {run['seed']} ; instantané du parcours, ni moyenne ni estimation pure de l’érosion d’actif.")})
    return {"events":events,"cash_timeline":cash,"capabilities":caps,"recipients":recipients,"beta_phases":phases,
      "ledger_note":bi(f"Prespecified first confirmation seed {run['seed']}, {run['config']['id']} / {run['arm']}. Not a median path. Cumulative B/C cash spending includes paid capability, assessment, transfer and upkeep expenses in those lanes; accrued unpaid obligations remain in full profit.",f"Première graine de confirmation prédéclarée {run['seed']}, {run['config']['id']} / {run['arm']}. Pas un parcours médian. Les dépenses B/C cumulées incluent capacités, évaluations, transferts et entretien payés dans ces catégories ; les engagements impayés restent dans le bénéfice complet."),
      "network_note":bi(f"Recipient figures describe seed {run['seed']} versus its same-price Beta pair. This path records {sum(c['admitted'] for c in h['campaigns'])} admissions; ordinary deliveries alone are not peer-Alpha benefit. Incremental gain here is collections less refunds, payment fees, direct job expense and recipient adaptation—not fully allocated enterprise profit. Shared B/C, acquisition, overhead and historical expense are charged once in the enterprise panel. Causal network value uses the full network-minus-local contrast in the paper.",f"Chiffres par destinataire pour la graine {run['seed']} face à Bêta au même prix. Ce parcours enregistre {sum(c['admitted'] for c in h['campaigns'])} admissions ; les livraisons ordinaires ne prouvent pas un bénéfice Alpha chez autrui. Le gain est encaissements moins remboursements, frais de paiement, coût direct des travaux et adaptation ; ce n’est pas le bénéfice entièrement alloué. B/C partagés, acquisition, frais fixes et historique sont comptés une fois pour l’entreprise. La valeur causale du réseau utilise réseau moins local dans l’article.")}


def make_demo(root,protocol,conf,selected,meta,sens,scale,metrics):
    result={"status":"bound_to_frozen_results","headline":bi("Paid-work learning is an opportunity, not a guaranteed asset. Read commercial profit, incremental Alpha and fresh-campaign effectiveness separately.","L’apprentissage du travail rémunéré est une possibilité, pas un actif garanti. Rentabilité commerciale, Alpha supplémentaire et efficacité d’invention restent distincts."),"freeze_note":"Frozen evidence date 2026-10-26 · "+conf["protocolSHA256"],"scenarios":[],"sensitivities":[],"sources":[]}
    configs={x["id"]:x for x in protocol["scenarios"]}
    for s in SCENARIOS:
        c=configs[s];view={"id":s,"worlds":len(protocol["confirmation"]["seeds"]),"human_price":c["humanReference"],"seed":c["seedCapital"],"selected_policy":"enterprise","policies":[],"pricing":[]}
        # The development ratio profile is separately labeled. It is never a new pricing optimization in the browser.
        training=read(root,"results/training.json");group=defaultdict(list)
        policy_map={p["id"]:p for p in protocol["selection"]["policies"]}
        if (root/"protocol/beta_symmetry_amendment.json").exists():
            amendment=read(root,"protocol/beta_symmetry_amendment.json");extra=read(root,"results/beta_symmetry_training.json")
            training["rows"]=[r for r in training["rows"] if policy_map[r["policy"]]["allowInvestment"]]+extra["rows"]
            policy_map={p["id"]:p for p in [*[p for p in policy_map.values() if p["allowInvestment"]],*amendment["betaPolicies"]]}
        for rr in training["rows"]:
            if rr["scenario"]==s:group[rr["policy"]].append(rr)
        for ratio in sorted({p["priceRatio"] for p in policy_map.values()}):
            options=[]
            for pid,rr in group.items():
                if policy_map[pid]["priceRatio"]!=ratio or not policy_map[pid]["allowInvestment"]:continue
                z=sorted(x["discountedAccrualProfitCents"] for x in rr);risk=sum(x["insolvent"] for x in rr)/len(rr);score=sum(z)/len(z)+.25*sum(z[:math.ceil(.1*len(z))])/math.ceil(.1*len(z))
                options.append((pid,rr,risk,score))
            feasible=[o for o in options if o[2]<=.05];best=sorted(feasible,key=lambda z:(-z[3],z[2],z[0]))[0] if feasible else sorted(options,key=lambda z:(z[2],-z[3],z[0]))[0]
            pid,rr,risk,score=best;view["pricing"].append({"fraction":ratio,"useful":sum(x["usefulAccepted"] for x in rr)/len(rr),"profit":sum(x["profitCents"] for x in rr)/len(rr)/100,"insolvency":risk,"selected":ratio==selected["selected"][s]["network"]["policy"]["priceRatio"]})
        for arm,label in ARM_LABELS.items():
            d=conf["scenarios"][s]["arms"][arm];p=metrics[s][arm];run=read(root,f"results/examples/{s}_{arm}.json");base=read(root,f"results/examples/{s}_same-price-beta.json")
            witness_file=root/f"results/examples/{s}_first_paid_alpha.json"
            witness=json.loads(witness_file.read_text()) if arm=="network" and witness_file.exists() else run
            witness_note=bi("First recorded paid-origin admission, selected as a descriptive witness rather than a typical result.","Première admission enregistrée issue d’un travail payé, témoin descriptif et non résultat typique.") if witness is not run else bi("Prespecified first confirmation world, not selected for success.","Premier monde de confirmation prédéclaré, non choisi pour sa réussite.")
            paired_mean=conf["scenarios"][s]["contrasts"]["network_minus_same-price-beta"]["differences"]["profitCents"]["mean"]/100 if arm=="network" else sum(x["profitCents"] for x in conf["rows"] if x["scenario"]==s and x["arm"]==arm)/d["runs"]/100-conf["scenarios"][s]["arms"]["same-price-beta"]["profitCents"]["mean"]/100
            r={"id":arm,"label":bi(*label),"arm":"beta" if arm in ("beta","same-price-beta") else "local" if arm=="local" else "network","baseline_version":c["betaVersion"],"human_price":p["human"],"offer_price":p["price"],"complete_cost":p["cost"],"available_cash":d["availableCents"]["median"]/100,"adoption":p["adoption"],"acceptance":p["acceptance"],"throughput":d["acceptedPerMonth"]["mean"],"profit":{k:d["profitCents"][k]/100 for k in ("p05","p95")},"loss_probability":p["loss"],"insolvency":p["insolvency"],"useful":d["usefulAccepted"]["mean"],"new_scope_useful":d["newlyFeasibleUseful"]["mean"],"paired_gain":paired_mean,"human_review_hours":0,"queue_p95":d.get("queueP95Weeks",{}).get("median"),"capacity_refusals":d["capacityRefusals"]["mean"],"accounting":p["accounting"],"origin_job":example_origin(witness,protocol,witness_note)}
            r["profit"]["p50"]=d["profitCents"]["median"]/100
            r["offer_note"]=bi("Actual modeled bids averaged over the same useful-delivery cohort as the human reference. Demand and contingent acceptance terms are assumptions.","Offres modélisées moyennes sur le même ensemble de livraisons utiles que la référence humaine. Demande et paiement conditionnel sont supposés.")
            if not p["useful_total"]:
                r["human_price"]=c["humanReference"]
                r["offer_price"]=c["humanReference"]*run["policy"]["priceRatio"]
                r["offer_note"]=bi("No useful delivery cohort occurred. The displayed reference and bid are the base-class human estimate and policy starting bid, before scarcity adjustment. Complete cost per useful delivery is undefined; all incurred expenses remain in profit/loss.","Aucun ensemble de livraisons utiles. Référence et offre affichées : estimation humaine de base et prix initial de la politique, avant ajustement de capacité. Coût complet par livraison utile indéfini ; toutes les dépenses restent dans le bénéfice ou la perte.")
            if arm=="enterprise" and not run["policy"]["allowInvestment"]:
                r["arm"]="beta"
            r["headline"]=bi(f"{label[0]}: median fully allocated pre-tax profit {usd(r['profit']['p50'])}; {d['usefulAccepted']['mean']:.1f} useful outcomes per world on average. All outcomes are modeled.",f"{label[1]} : bénéfice complet médian avant impôt {usd(r['profit']['p50'])} ; {d['usefulAccepted']['mean']:.1f} résultats utiles moyens par monde. Tous les résultats sont modélisés.")
            r["quota_note"]=bi(f"Assumed {c['concurrency']} concurrent slots, {c['inputQuotaWeekly']/1e6:g}M input / {c['outputQuotaWeekly']/1e6:g}M output tokens per week, {c['cpuHoursWeekly']} solver and {c['validatorHoursWeekly']} validator CPU-hours/week. Conservative reserved quotas are distinct from billed usage.",f"Hypothèses : {c['concurrency']} places simultanées, {c['inputQuotaWeekly']/1e6:g} M jetons d’entrée / {c['outputQuotaWeekly']/1e6:g} M de sortie par semaine, {c['cpuHoursWeekly']} heures CPU solveur et {c['validatorHoursWeekly']} validation. Quotas réservés distincts de l’usage facturé.")
            r["alpha"]={"candidates":d["paidOriginCandidates"]["mean"],"admitted":d["successfulCampaigns"]["mean"],"false_admissions":d["alphaFalseAdmissions"]["mean"],"retired":d["alphaRetired"]["mean"],"network_available":len(protocol["agents"]),"baseline_note":bi("Lifecycle counts are means per independent world. Paid candidates can fail rights, assessment or transfer. Eligible membership is not an observed deployment.","Les cycles de vie sont des moyennes par monde. Droits, évaluation ou transfert peuvent échouer. L’admissibilité n’est pas un déploiement observé.")}
            r["lifecycle_note"]=bi("Local software controls pass 41/41; economic Alpha checks and authenticated identities are modeled fixtures. Every reuse rechecks current scope, version, dependencies and revocation. Failure memory and protected evaluators are separated from reusable positive Alpha.","Les contrôles logiciels locaux réussissent 41/41 ; Alpha économique et identités authentifiées restent des fixtures modélisées. Chaque usage revérifie périmètre, version, dépendances et révocation. Mémoire d’échec et évaluateurs protégés restent séparés de l’Alpha positif réutilisable.")
            r.update(trajectory(run,base,protocol))
            mm=meta["arms"]["retained_family_screen"]
            r["campaigns"]={"count":meta["campaigns"],"useful_probability":mm["usefulRate"],"cost_per_useful":meta["amortization"][2]["retainedCompleteCostPerUsefulCents"]/100}
            r["learning_note"]=bi(f"Separate prespecified central mechanism experiment, unchanged by the scenario/arm control: {meta['campaigns']} independent campaigns. Mean variable saving {usd(meta['pairedVariableCostSavingCents']['mean']/100)}; complete optional research lifecycle {usd(meta['assetLifecycle']['costCents']/100)}. Displayed complete cost/useful amortizes over 16 future campaigns. Resource payback needs {meta['projectedBreakEvenCampaigns']} campaigns; finite lifetime quotas bind before that. No profitable self-acceleration is established.",f"Expérience centrale distincte prédéclarée, inchangée par le scénario ou la comparaison : {meta['campaigns']} campagnes indépendantes. Économie variable moyenne {usd(meta['pairedVariableCostSavingCents']['mean']/100)} ; cycle de vie complet de recherche {usd(meta['assetLifecycle']['costCents']/100)}. Coût complet par capacité amorti sur 16 campagnes futures. Remboursement des ressources à {meta['projectedBreakEvenCampaigns']} campagnes ; quotas de durée contraignants avant ce seuil. Aucune auto-accélération rentable établie.")
            view["policies"].append(r)
        result["scenarios"].append(view)
    groups=defaultdict(list)
    for case in sens["cases"]:groups[case["parameter"]].append(case)
    for parameter,cases in groups.items():
        labels=STRESS_LABELS[parameter]
        def value_label(value):
            if parameter=="alphaSystematicRiskReserveCentsPerUse":return usd(value/100)
            if parameter in {"humanReference","buyerValueMedian","trustMax","assetMaintenanceWeekly","assetTransferCost","acquisitionCostPerProspect","seedCapital","setupCost"}:return usd(value)
            return f"{value:,}"
        result["sensitivities"].append({"title":bi(*labels),"note":bi("Executed central-policy one-factor stress only; other scenarios are not independently rerun by this selector. Twenty fresh paired worlds per condition.","Variation exécutée sur la politique centrale seulement ; ce sélecteur ne relance pas les autres scénarios. Vingt mondes inédits appariés par condition."),"rows":[{"scenario":"central","label":bi(value_label(c["value"])),"profit":c["summary"]["network"]["profitCents"]["median"]/100,"insolvency":c["summary"]["network"]["insolvent"]["rate"]} for c in cases]})
    sources=[("Official model configuration","Configuration officielle des modèles","https://developers.openai.com/api/docs/guides/latest-model","Reported current capability/access; task success remains assumed.","Capacités et accès documentés ; succès de la tâche supposé."),("Official API pricing","Tarifs API officiels","https://developers.openai.com/api/docs/pricing","Checked 26 October 2026; subscription and API usage are separate.","Vérifié le 26 octobre 2026 ; abonnement et API séparés."),("Matched human service rates","Tarifs humains comparables","https://www.gsaadvantage.gov/ref_text/GS07F0011V/GS07F0011V_GSAMass_Supply_Schedule_TC_05062026.pdf","Reported US ceiling rates; 168 central hours and contingent terms are assumptions.","Tarifs plafonds américains publiés ; 168 heures centrales et conditions contingentes supposées."),("Evolution of Heuristics","Évolution d’heuristiques","https://arxiv.org/html/2401.02051v3","Independent mechanism evidence, not Astra acceptance calibration.","Preuve indépendante du mécanisme, pas calibration d’acceptation Astra."),("Transformational Intelligence","Intelligence transformationnelle","https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/docs/Transformational_Intelligence.pdf","Purpose, formulation and fresh-campaign distinctions.","Distinctions entre objectif, formulation et campagnes inédites."),("Gym, Specialist ASI and Successor Ω","Gym, Specialist ASI et Successor Ω","https://github.com/MontrealAI/MontrealAI.github.io/blob/a9cc143bc05495405ac63b0e2645c425d66410b8/GoalOS_Gym_Specialist_ASI_Successor_Omega_v2_1_0_US_LETTER.pdf","Design source; synthetic examples and illustrative price bands excluded from calibration.","Source conceptuelle ; exemples synthétiques et prix illustratifs exclus de la calibration."),("Frozen protocol coordination record","Coordination du protocole figé","https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429820934","Protocol frozen before scientific runs; complete files accompany the paper.","Protocole figé avant les essais scientifiques ; fichiers complets joints à l’article.")]
    result["sources"]=[{"title":bi(a,b),"url":url,"note":bi(en,fr)} for a,b,url,en,fr in sources]
    witness_path=root/"results/analysis/development_witness.json"
    if witness_path.exists():
        w=json.loads(witness_path.read_text());c=w["campaigns"][0];j=c["sourcePaidJob"];b=c["paidRetention"];a=c["observedAssessment"];t=c["transfers"][0];z=c["attribution"]
        assert w["exactReplay"]["allRecordedSummaryFieldsEqual"] and w["exactReplay"]["bothArmsAudited"]
        result["development_witness"]={"identity":f"{w['case']} · seed {w['seed']} · {c['asset']['id']}","note":bi("Selected after observing the capacity-development grid; one independent world, unchanged by the confirmation scenario controls. It is not a typical outcome or fresh confirmation. All 36 fresh capacity condition/world evaluations (12 shared fresh seeds) had zero admissions and zero peer reuse.","Sélection après observation de la grille de développement ; un monde indépendant, inchangé par les contrôles de confirmation. Ni résultat typique ni confirmation inédite. Les 36 évaluations inédites condition/monde (12 graines partagées) ont eu zéro admission et zéro réutilisation par autrui."),"stages":[
            {"title":bi("1 · Customer-funded work A","1 · Travail A financé par le client"),"text":bi(f"{j['agent']} delivers {j['id']}, a rolling policy. Matched human-team estimate {usd(j['humanPriceCents']/100)}; modeled invoice {usd(j['priceCents']/100)}, collected week {j['invoice']['collectedWeek']}. Direct A expense {usd(j['costCents']/100)} includes learning; common business expense is separate.",f"{j['agent']} livre {j['id']}, politique à horizon glissant. Référence humaine {usd(j['humanPriceCents']/100)} ; facture modélisée {usd(j['priceCents']/100)}, encaissée semaine {j['invoice']['collectedWeek']}. Coût direct A {usd(j['costCents']/100)}, apprentissage inclus ; frais communs séparés.")},
            {"title":bi("2 · A candidate, then additional B","2 · Un candidat, puis B supplémentaire"),"text":bi(f"A representation/certificate bundle emerges with reusable rights. Week {b['week']}: extraction {usd(b['constructionCents']/100)} plus eventual assessment {usd(b['assessmentActualCents']/100)}, funded from prior surplus. Already-paid A is recharged $0; optional C is $0.",f"Un ensemble représentation/certificat émerge avec droits réutilisables. Semaine {b['week']} : extraction {usd(b['constructionCents']/100)} et évaluation ultérieure {usd(b['assessmentActualCents']/100)}, financées par surplus antérieur. A refacturé : 0 $ ; C facultatif : 0 $. ")},
            {"title":bi("3 · Capacity and fresh assessment","3 · Capacité et évaluation inédite"),"text":bi(f"The assumed serial blind maximum booking occupies {b['capacityBooking']['duration']} weeks, through week {b['readyWeek']}. {a['independentClusters']} paired mission clusters yield an assessed lifetime lower net bound {usd(a['lowerLifetimeNetCents']/100)}. This conditional forecast is not realized return.",f"La réservation sérielle maximale préalable supposée dure {b['capacityBooking']['duration']} semaines, jusqu’à la semaine {b['readyWeek']}. {a['independentClusters']} groupes de missions appariées donnent une borne nette de durée {usd(a['lowerLifetimeNetCents']/100)}. Prévision conditionnelle, pas rendement réalisé.")},
            {"title":bi("4 · Admission and optional adoption","4 · Admission et adoption facultative"),"text":bi(f"Week {a['week']}: simulated admission and availability to all three eligible members. Orion lacked the equivalent bundle and adapts it in week {t['week']} for {usd(t['costCents']/100)}. Technical productivity is true only inside this simulation; its positive economic admission forecast is a false positive ex post.",f"Semaine {a['week']} : admission simulée, accès aux trois membres admissibles. Orion ne possédait pas l’ensemble équivalent et l’adapte semaine {t['week']} pour {usd(t['costCents']/100)}. La productivité technique est vraie seulement dans cette simulation ; la prévision économique d’admission est un faux positif a posteriori.")},
            {"title":bi("5 · Useful peer work, then retirement","5 · Travail utile chez autrui, puis retrait"),"text":bi(f"{z['usefulPeerUseJobs']} useful peer jobs among {w['summaries']['network']['alphaPeerUses']} peer attempts; {w['summaries']['network']['alphaUses']} total uses. At week 53 the asset is retired when fresh revalidation is unavailable. This precedes its hypothetical Beta upgrade at week 78; it is a freshness/capacity failure, not observed frontier-driven erosion.",f"{z['usefulPeerUseJobs']} travaux utiles chez autrui sur {w['summaries']['network']['alphaPeerUses']} tentatives ; {w['summaries']['network']['alphaUses']} usages totaux. Retrait semaine 53 faute de revalidation inédite disponible. Cela précède la mise à jour Bêta hypothétique de semaine 78 : échec de fraîcheur/capacité, pas érosion observée par progrès de la frontière.")},
            {"title":bi("6 · Preserve the negative complete return","6 · Conserver le rendement complet négatif"),"text":bi(f"Paired workflow saving {usd(z['grossWorkflowResourceSavingCents']/100)}, referenced B {usd(z['assetReferencedBExpensesCents']/100)} and access {usd(z['incrementalAccessCostCents']/100)} leave {usd(z['grossWorkflowSavingMinusAccessAndReferencedBExpensesCents']/100)} before shared discovery. Useful reuse alone did not repay retention.",f"Économie appariée {usd(z['grossWorkflowResourceSavingCents']/100)}, B référencé {usd(z['assetReferencedBExpensesCents']/100)} et accès {usd(z['incrementalAccessCostCents']/100)} donnent {usd(z['grossWorkflowSavingMinusAccessAndReferencedBExpensesCents']/100)} avant découverte partagée. La réutilisation utile n’a pas remboursé la conservation.")}
        ],"result":bi(f"Whole-policy network minus same-price Beta: {usd(w['fullSignedEnterpriseDifference']['profitCents']/100)} in pre-tax profit and {w['fullSignedEnterpriseDifference']['usefulOutcomes']} useful outcomes. This selected trace demonstrates the implemented lifecycle and a failed economic return; it is not evidence of a profitable network flywheel.",f"Politique réseau moins Bêta au même prix : {usd(w['fullSignedEnterpriseDifference']['profitCents']/100)} de bénéfice avant impôt et {w['fullSignedEnterpriseDifference']['usefulOutcomes']} résultats utiles. Ce parcours sélectionné montre le cycle implémenté et un rendement économique négatif ; il ne prouve pas une boucle de réseau rentable.")}
    return result
