#!/usr/bin/env python3
"""Assemble fresh BeyondBeta inputs only; never execute economic outcomes."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--freeze',action='store_true',help='Write the final frozen protocol after prospective review; an already frozen protocol cannot be overwritten by this generator.')
args=parser.parse_args()
existing=ROOT/'protocol.json'
if existing.exists() and json.loads(existing.read_text()).get('status')=='FROZEN_BEFORE_OUTCOMES':
    raise SystemExit('Refusing to overwrite a frozen BeyondBeta protocol. Preserve it and use a separately registered study revision.')
proposal_path=ROOT/'calibration'/'numeric-proposal.json'
p=json.loads(proposal_path.read_text())

def resource(old):
    return {k:old[k] for k in ('astraInput','astraOutput','terraInput','terraOutput','cpuHours','modelHours','storageGbDays')}|{
        'requests':old['requestsA']+old['requestsT'],
        'tools':old['webSearch']
    }

mapping={
 'intake':'scope','specify':'specification','implement':'implementation',
 'prove':'proof','verify':'independentAudit','repair':'correction',
 'package':'package','support':'support','discovery':'discover',
 'alphaConstruct':'constructContracts','alphaConstructComposition':'constructComposition',
 'alphaConstructRevalidation':'constructRevalidation','alphaAssess':'candidateEvaluation',
 'alphaQualify':'qualification','alphaJoint':'jointQualification','alphaPublish':'admissionPublication',
 'gapProbe':'recipientGapProbe','adapt':'adaptation','revalidate':'freshVersionRevalidation',
 'maintain':'assetMaintenance','ops':'weeklyOperations','setup':'setup','history':'openingResearchAllowance'
}
out={
 'schema':'beyond-beta-protocol/v1','status':'FROZEN_BEFORE_OUTCOMES' if args.freeze else 'PROPOSED_BEFORE_OUTCOMES','createdDate':'2026-10-26',
 'offering':p['offering'],'evidence':p['actualEvidence'],
 'evidenceBoundary':'All quantities except explicitly sourced current wages/prices are fresh assumptions. No current frontier benchmark score is converted into acceptance, effect, effort or revenue. No old study workload, hours, fee or asset budget is inherited.',
 'rates':{'astraInput':10,'astraOutput':50,'terraInput':1,'terraOutput':5,'cpuHour':.36,'tools':.01,'storageGbDay':.012,'modelHour':0,'requestFee':0},
 'rateUnits':{'astraInput':'USD per million tokens','astraOutput':'USD per million aggregate output/reasoning tokens','terraInput':'USD per million tokens','terraOutput':'USD per million aggregate output/reasoning tokens','cpuHour':'USD per4GB proof-container-hour','tools':'USD per paid web-search call; local proof/compiler calls are accounted through container time','storageGbDay':'Assumed generic persistence allowance, not a quote','modelHour':'Capacity/latency only; no duplicated token billing'},
 'bundles':{new:resource(p['resourceBundles'][old]) for new,old in mapping.items()},
 'bundleProvenance':mapping,
 'resourceRules':p['resourceInterpretation']|{'deliveryStages':['intake','specify','implement','prove','verify','package','support'],'repairStages':['repair','prove','verify'],'maxRepairs':2,'proofAndVerificationSeparate':'Prove is theorem/invariant construction; verify is the independent acceptance audit. A retained proof-generation asset cannot silently delete independent validation.','maximumPerRequestInputTokens':260000,'maximumPerRequestOutputTokens':120000,'localToolCallCountsPreservedInProposal':True},
 'profiles':p['profiles'],'humanReference':p['humanReference'],'jobTypes':p['jobMix'],
 'skills':{
   'contracts':{'title':'Scoped contract representation','constructBundle':'alphaConstruct','qualificationBundle':'alphaQualify','affectedStages':['specify'],'maximumStageReduction':.55,'minimumMotivatingAcceptedJobs':2,'requires':[],'hypothesis':p['capabilities']['contracts']['hypothesis']},
   'composition':{'title':'Proof and adapter composition','constructBundle':'alphaConstructComposition','qualificationBundle':'alphaQualify','jointQualificationBundle':'alphaJoint','affectedStages':['prove'],'maximumStageReduction':.60,'minimumMotivatingAcceptedJobs':3,'requires':['applicable_contracts_or_equivalent_beta_contracts'],'hypothesis':p['capabilities']['composition']['hypothesis']},
   'revalidation':{'title':'Dependency-aware revalidation procedure','constructBundle':'alphaConstructRevalidation','qualificationBundle':'alphaQualify','affectedStages':['revalidate'],'maximumStageReduction':.45,'minimumMotivatingAcceptedJobs':4,'minimumObservedChanges':1,'requires':[],'hypothesis':p['capabilities']['revalidation']['hypothesis']}
 },
 'network':p['admission']|{'agentCount':6,'agents':p['agents'],'mandatoryPublicationBundle':'alphaPublish','optionalUse':True,'discoveryBundle':'discovery','probeBundle':'gapProbe','adaptBundle':'adapt','graphClaim':'No unearned graph advantage; registry and graph have identical admitted inventory and metadata. Primary network availability is mandatory. Private-only arm is an explicitly named ablation.'},
 'capacity':p['capacity'],'buyers':p['market'],'company':p['company'],
 'policies':{'priceGridUsd':p['pricing']['absoluteUsdChoices'],'adaptivePrice':True,'investmentRules':['never','positiveExpectedNetValue','riskAdjustedPositiveNetValue'],'fundingRules':['seed-permitted','operating-only'],'humanDiscountRequired':False,'noInvestmentAllowed':True,'zeroBusinessAllowed':True,'objective':p['pricing']['objective'],'priceEvidence':'All prices and buyer values are assumptions, not sourced quotes or observed willingness to pay.','fixedPriceBinding':'The policy builder must use the supplied priceUSD from priceGridUsd without substituting a human-price fraction or an outcome-dependent price. Adaptive pricing is a separately declared rule.','forecastMaximumWeeks':40,'forecastBoundary':'Prospective investment forecasts are limited to the next40 weeks and the remaining mission horizon; an asset forecast must also respect its remaining declared useful life. No future realized job, price, quality or cash outcome is visible to the decision.'},
 'betaVersions':p['baselineVersions'],'betaVersionBasis':p['baselineVersionBasis'],
 'scenarios':p['scenarios']+[
   {'id':'high-repeat','overrides':{'opportunityMultiplier':6}},
   {'id':'slow-beta','overrides':{'versionWeeks':[0,52,104]}},
   {'id':'high-repeat-slow-beta','overrides':{'opportunityMultiplier':6,'versionWeeks':[0,52,104]}},
   {'id':'diverse-hard','overrides':{'composedShare':.65}},
   {'id':'quota-tight','overrides':{'quotaMultiplier':.002}},
   {'id':'short-alpha-life','overrides':{'assetLifetimeWeeks':12}}
 ],
 'experiment':{
   'weeks':72,'trainingSeeds':list(range(1,9)),
   'trainingProfiles':['reference','burdensome','efficient'],'trainingProfileWeights':{'reference':.5,'burdensome':.25,'efficient':.25},
   'trainingScenarios':['reference','high-repeat'],'trainingScenarioWeights':{'reference':.75,'high-repeat':.25},
   'trainingPriceRules':6,'trainingInvestmentRules':3,'trainingFundingRules':2,
   'trainingPoliciesBeforeDuplicatePruning':36,'trainingWorldsPerPolicy':48,'trainingHistories':1728,
   'duplicatePolicyRule':'Any removal of duplicated never-invest funding variants must be declared before execution;1728 is the full unpruned grid.',
   'selectionRule':'Select best Beta, best optional Alpha and overall winner separately from the same training grid before confirmation. Maximize weighted complete operating value among cash-valid policies whose training false-pass fraction is no greater than0.025; break exact ties by declared grid order. The overall winner may be Beta. An optional Alpha policy may decline every investment; no asset is forced.',
   'trainingSelections':{
     'bestBeta':{'eligibleInvestmentRules':['never'],'purpose':'Independently select the strongest ordinary-delivery pricing rule.'},
     'bestOptionalAlpha':{'eligibleInvestmentRules':['positiveExpectedNetValue','riskAdjustedPositiveNetValue'],'purpose':'Select pricing, optional retention and funding jointly, while allowing all investment gates to decline.'},
     'overallWinner':{'eligibleInvestmentRules':['never','positiveExpectedNetValue','riskAdjustedPositiveNetValue'],'purpose':'Identify the preferred complete policy without requiring an Alpha winner.'},
     'eligibility':'All three selections use the same complete-value objective, cash validity, false-pass bound and grid-order tie break. An empty eligible subset is reported as unqualified, never silently replaced by a failed policy.'
   },
   'confirmationSeeds':list(range(1001,1041)),
   'confirmationProfilesBySeedRule':'Cycle reference, burdensome, efficient by(seed-1001)%3, identically in each scenario and arm. This gives14/13/13 worlds per profile per scenario, not40 per profile.',
   'confirmationArms':['moving-beta-only','private-alpha-availability-ablation','network-alpha','network-alpha-frozen-beta','frozen-beta-only','trained-beta'],
   'confirmationScenarios':19,'confirmationPairedWorlds':760,'confirmationHistories':4560,
   'confirmationPolicyBinding':{
     'mechanismArms':['moving-beta-only','private-alpha-availability-ablation','network-alpha','network-alpha-frozen-beta','frozen-beta-only'],
     'mechanismPricing':'Use the pricing controller selected for bestOptionalAlpha in all five mechanism arms. Beta-only arms disable investment; Alpha arms retain the selected optional rule and funding choice, subject to their named mechanism restrictions.',
     'adaptivePricingInterpretation':'The controller and its preselected parameters are matched. If adaptive, each arm responds only to its own available history, so realized prices may differ; no arm receives another arm\'s future realized prices.',
     'trained-beta':'Use independently selected bestBeta pricing with moving Beta and no retained Alpha investment.',
     'overallRecommendation':'Report overallWinner separately. Continue the prespecified optional-Alpha comparison even when ordinary Beta wins training; this does not authorize or force an investment.'
   },
   'movingBetaEstimand':'Compare(network-alpha minus moving-beta-only) with(network-alpha-frozen-beta minus frozen-beta-only) under paired exogenous draws. This distinguishes incremental Alpha value under the moving and frozen frontiers; absolute totals also include baseline improvements.',
   'wholePolicyEstimand':'Compare network-alpha with trained-beta under paired exogenous draws to estimate the complete selected-policy difference, including independently optimized ordinary-delivery pricing. Report this separately from the five matched-controller mechanism arms.',
   'sameExogenousDraws':True,'sameComputeForAllArms':True,
   'mandatoryPrimaryAvailability':'network-alpha publishes every admitted asset; private-alpha is a research ablation, never the claimed primary system.',
   'demonstrationPreselection':{'scenario':'reference','seed':1001,'arm':'network-alpha'},
   'allCellsReported':True,'noEconomicOutcomesRun':True
 },
 'sourceFiles':['calibration/sources.json','calibration/market-screen.json','calibration/SCREENING.md','calibration/numeric-proposal.json'],
 'remainingPreFreezeDecisions':['Exact buyer outside-option utility and Beta offer implementation','Independent truth/qualification implementation','Cash/reserve/obligation invariants','Graph staleness and revalidation implementation'],
 'sourceProposalSha256':hashlib.sha256(proposal_path.read_bytes()).hexdigest(),
 'generatorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
}
out['humanReference'].update({
 'humanServiceHours':180,'hoursByProfile':{'reference':180,'burdensome':64,'efficient':488},
 'businessLoadingFraction':.20,
 'businessLoadingBasis':'Fresh explicit20% scenario allowance for project administration, business risk and unpriced overhead; not a quoted fee or a measured market margin. This is separate from employee benefit loading.',
 'formula':'(humanServiceHoursForProfile*loadedHourlyProxy + matchedNonAiProofContainerHours*0.36)*1.20',
 'matchedCompute':'Use the same scoped nominal non-AI proof/checker/container resource allowance for the matched job; human reference includes no model/API tokens.',
 'servicePriceEvidence':'Cost-derived hypothetical human outside offer, not a verified human-only consulting fee. Actual willingness to pay remains unknown.',
 'hoursStressInterpretation':'The64/180/488 figures are task-level judgement anchors, not measured quantiles or empirical confidence limits.'
})
out['enginePolicyDefaults']={
 'humanServiceHours':180,'humanServiceHoursLow':64,'humanServiceHoursHigh':488,
 'humanBusinessLoadingFraction':.20,
 'scope':'Human outside-option calculation only. No Alpha effect, producer resource envelope or quality probability changed.'
}
out['engineDefaults']={
 'initialPrecision':.985,'priorWeight':6,'initialDelivery':.85,
 'humanDeliveryDays':20,'humanQuality':.985,'valueDecayWeekly':.015,
 'unsupportedProbability':.06,'clarificationProbability':.12,'clarificationSuccess':.85,
 'commonReferenceBlind':.20,'qualityEligibilityFalsePassMax':.025,
 'maxGraphEvidenceAgeWeeks':12,'netAlphaUncertaintyMultiplier':2,
 'maxCostAllocationUses':200,'graphAdmissionAcceptanceBps':9500
}
out['engineDefaultsProvenance']='Fresh task-level scenario assumptions fixed before outcomes, not measured current-model performance, sourced buyer behavior or a benchmark-score conversion.'
for agent in out['network']['agents']:
    agent['competenceOffset']=0
out['bundles']['alphaExtract']={
 'astraInput':500000,'astraOutput':120000,'terraInput':300000,'terraOutput':60000,
 'cpuHours':20,'requests':12,'modelHours':1.5,'storageGbDays':15,'tools':2
}
out['bundleProvenance']['alphaExtract']='Fresh additional extraction/generalization allowance after already-paid delivery learning; assumed, not observed.'
out['engineDesign']={
 'status':'PROPOSED_BEFORE_OUTCOMES',
 'paidJobLearningPrimary':True,'paidJobCandidateProbability':.30,'rightsClearedProbability':.90,'paidCandidateUsefulPrior':.65,
 'optionalDeliberateResearchEnabled':True,'minimumJobsForSeparateResearch':6,'separateResearchReviewIntervalWeeks':8,
 'newCompletedJobsBeforeReassessment':8,
 'qualificationContextSizeInterval':[.6,1.4],'paidRevalidationFamilyProbability':.25,'trustAcceptedStep':.01,'trustDetectedFaultStep':-.20,
 'maximumAdmittedAssetResourceHarmFraction':.20,'campaignWallTimeLimitSeconds':1800,
 'qualificationContextFractionByProfile':{'reference':.25,'burdensome':1,'efficient':.10},
 'qualificationCheckFraction':.25,'riskAdjustedBenefitFraction':.70,
 'postponeValueFraction':.60,'postponeWeeks':8,'postponeCostUsd':200,
 'candidateOrigin':'Paid delivery already includes substantive specification, implementation and proof reasoning. A candidate can emerge from completed useful work; emergence is not admission or value.',
 'ledgerA':'Delivery and learning/experimentation undertaken to complete a customer job. Charged once, including rejected attempts and repairs.',
 'ledgerB':'Only additional extraction/generalization, fresh qualification, packaging, publication, discovery, functional-gap checks, adaptation, revalidation and upkeep. Origin A costs are provenance only and are not amortized into prospective Alpha.',
 'ledgerC':'Optional separate deliberate research and the explicitly assumed opening research allowance. Actual historical study cost remains unknown. C is never automatically charged to each paid-job candidate.',
 'qualificationDesign':'24 fresh protected stage contexts execute the candidate and competent Beta affected stage plus independently informative checks, with one shared mission scaffold. Context resource fractions are explicit assumptions; modeled effect transfers to the specified full-job stage, not to independent verification or all work. Cost/effect normalization and the unchanged whole-mission contract remain visible in evidence. Resource-intensive qualification is retained in the burdensome profile.',
 'assumptionStatus':'Every exact emergence, rights, usefulness, assay fraction, postponement and risk parameter here is an unmeasured task-level scenario assumption, not an external benchmark conversion.',
 'capacity':'Six equal workers share fixed weekly model/proof-container budgets and total token/request quotas. Delivery and qualification validation consume another worker. Public maximum retries, fresh paired comparator executions and possible harmful resource changes are reserved before hidden outcomes are drawn. Weekly fluid quota planning is a bound, not a measured minute-by-minute provider trace. Unused retry reservations are conservatively not resold; resource-cost savings do not themselves prove greater throughput.',
 'heterogeneity':'No role expertise probability bonus is applied. All competenceOffset values are zero; worker differences come from initial functional overlap, job scope and acquired evidence/history.',
 'probeTiming':'Functional probes and adaptation outcomes stay task-local until paid work completes. Concurrent tasks either execute their own paid probes or use only previously completed cache entries.',
 'compositionInputs':'The already-paid Beta specification stage can construct applicable contracts. A proof-composition skill need not have a retained contract predecessor. When it uses a retained dependency, that exact version is independently qualified and guarded.',
 'qualificationComparatorTiming':'Freeze the current Beta and available inventory at the costed qualification decision. Every relevant paired comparator receives stage execution and independent checking resources. If that context changes before completion, retain the paid failed attempt and refuse admission; do not silently add unpriced fresh trials.',
 'revalidationBoundary':'A fresh revalidation forecast is limited by the asset remaining useful life and mission horizon. Invalid admitted helpers are allowed to fail observed checking or be falsely accepted; hidden correctness never grants a free safe fallback.',
 'marginalUpkeepRule':'Before new maintenance or stale-asset revalidation, estimate additional resource savings using only observed qualified effect, current overlap/available alternatives and recent publicly accepted reuse frequency. Bound benefits by remaining asset/mission life, the40-week forecast window and the next proof-valid interval. Subtract new assay/revalidation or maintenance work, additional upkeep and distribution only; original delivery A and prior retention B are sunk and excluded. Spend only if this marginal estimate is positive and current funding/capacity suffice; otherwise retire. Each decision retains forecast and cash-event/hold checkpoint. This bounded heuristic is not a global optimizer.',
 'ordinaryBaselineReservations':'Beta without eligible current assets reserves ordinary delivery and maximum repairs only. Alpha-specific preparation/harm slack is added only for currently discoverable, operationally current assets of the assigned worker, using public metadata before hidden outcomes.',
 'operatingOnlyTransferRule':'The operating-only policy reserves the ordinary job obligation first; incremental B preparation is bounded conservatively by earned funds remaining after the full public job reservation. It cannot consume seed merely because the A job is partly seed-funded.',
 'latentInformation':'Policy sees only completed public feedback, paid functional probes, qualification observations and declared priors. Hidden validity/effect/oracle truth is retained for research scoring only.',
 'pricing':'Five supplied absolute USD prices plus an adaptive controller. The adaptive controller tries unobserved grid prices in fixed order, then maximizes expected contribution using only its own past quote/conversion counts with a Beta(1,1) smoothing prior. Buyer private value, threshold, trust and budget are not supplied to pricing. Human and network prices are payable conditional on accepted delivery. Decline has zero utility and wins ties. Quality eligibility and trust utility discount are distinct.',
 'proposalCaching':'New paid-job candidates are retained as records. Costed assessment may be repeated after eight additional publicly accepted jobs or a Beta epoch change; this is a prospective information-refresh rule, not an immutable one-proposal quota.',
 'settlementRunoff':'No new business after week72. Declared feedback, payment/default, refunds and warranty windows run to settlement, with fixed business overhead during runoff. Support production resource is included in delivery. Horizon cash and terminal settled cash/profit are both reported.',
 'assetValueReporting':'Individual direct resource savings are diagnostic. Whole retention/research program net subtracts all B/C attempts, including declines and failures; paired whole-enterprise profit additionally captures foregone sales, price history and capacity effects. No positive direct asset alone establishes a full compounding claim.',
 'assetResourceScope':'Contracts change specification resources; composition changes proof-construction resources; revalidation changes only dependency-revalidation preparation. Independent final verification is preserved.',
 'actualEvidence':'Local simulation and cryptographic fixture checks execute. Actual model calls, commercial receipts and professionally accepted software deliveries remain zero; actual complete research cost is null.'
}
out['policies']['retentionSourceRule']='Primary optional decision retains learning already produced in a paid job. Separate deliberate research is a distinct optional C decision, not a mandatory stand-alone build charge on each candidate.'
out['mechanismScalePanel']={
 'status':'PRESPECIFIED_BEFORE_ANY_OUTCOMES',
 'originalScenarioCount':13,'originalScenariosUnchanged':True,
 'addedScenarios':['high-repeat','slow-beta','high-repeat-slow-beta','diverse-hard','quota-tight','short-alpha-life'],
 'purpose':'Estimate reuse/erosion/heterogeneity/capacity boundaries while preserving every original adverse condition.',
 'demandBoundary':'High-repeat is an assumed sixfold arrival stress, not evidence of actual customers or demand. Report break-even workload against independently uncertain recurrence.',
 'assetCostBoundary':'Small modeled construction costs do not prove cheap actual invention. Report complete failed research and sensitivity to unmeasured construction, discovery, qualification and maintenance costs; do not tune gains to recover an investment.'
}
for name,b in out['bundles'].items():
    assert len(b)==9 and all(isinstance(v,(int,float)) and v>=0 for v in b.values()),name
assert out['scenarios'][:13]==p['scenarios']
assert out['experiment']['trainingHistories']==6*3*2*3*2*8
assert out['experiment']['confirmationHistories']==len(out['scenarios'])*40*6
destination=ROOT/'protocol.json'
destination.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'path':str(destination),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'bundles':len(out['bundles']),'outcomesRun':False}))
