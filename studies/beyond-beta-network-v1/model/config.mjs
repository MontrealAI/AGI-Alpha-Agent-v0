// SPDX-License-Identifier: Apache-2.0
// Beyond Beta: independently specified assumptions, frozen before policy search.
// Sources anchor tariffs and human rates, not probabilities, demand or skill effects.
export const BASE={
  id:'central',weeks:104,runoffWeeks:24,currency:'USD',seedCapital:50000,
  historicalResearchAllowance:5000,setupCost:12000,overheadMonthly:950,
  operatorSubscriptionMonthly:200,runoffOverheadMonthly:200,
  humanReference:28668.40,humanQuality:.97,humanDeliveryWeeks:4,
  prospectsMonthly:12,marketSpread:.45,buyerValueMedian:50000,buyerValueSpread:.7,
  trustMax:8000,switchingCost:1500,buyerDelayCostWeekly:350,
  initialPerceivedQuality:.86,initialCompletionBelief:.60,humanCompletionBelief:.70,
  priorReputationWeight:20,reputationFeedback:.65,businessLossBeyondValue:8000,
  repeatProbability:.35,repeatSwitchFactor:.35,commodityShare:.15,scopeSupport:.85,
  acquisitionCostPerProspect:150,collectionDelayWeeks:4,badDebt:.03,paymentFee:.025,
  refundDelayWeeks:6,customerErrorDetection:.75,lateErrorDetection:.90,
  taxReserve:.23,refundReserve:.10,minimumCashReserve:8000,
  concurrency:3,hoursWeekly:168,inputQuotaWeekly:12000000,outputQuotaWeekly:3000000,
  cpuHoursWeekly:3000,validatorHoursWeekly:1200,queueLimit:18,queueWaitLimit:4,
  tokenMultiplier:1,computeMultiplier:1,workflowLatencyMultiplier:1,cpuPricePerHour:.0493704,
  commonError:.07,initialError:.25,semanticDetection:.65,mechanicalDetection:.97,
  correctionSuccess:.75,maxRetries:2,improvementProbability:.14,improvableFraction:.65,
  bundleEffect:.45,singleCapabilityOverhead:0,assetConstructionMultiplier:4,
  assetProductiveProbability:.60,assetFalseAdmission:.08,assetFalseRejection:.06,
  assetLifetimeWeeks:65,assetMaintenanceWeekly:24,assetRevalidationWeeks:13,
  assetRevocationDetection:.80,assetTransferCost:220,assetTransferSuccess:.80,
  copyHazardWeekly:.003,discoveryEveryWeeks:4,minimumObservedProspects:8,
  campaignInputPerWorkUnit:5000,campaignOutputPerWorkUnit:900,
  campaignCPUPerWorkUnit:1.2,campaignServiceHoursPerWorkUnit:.012,campaignValidationFraction:.30,
  assetMaxAttempts:2,assetRetryWait:20,forecastHaircut:.65,forecastWindow:20,
  discountRateAnnual:.10,earlyAbandonWeeks:24,meanAssetBelief:.60,winddownCost:1000,
  baselineScreenSensitivity:.65,familyScreenIncrement:.15,cheapScreenCpuFraction:.10,
  materialErrorDamage:0,
  // Version1 is observed public model documentation; Version2 is a hypothetical future path.
  betaVersion:'beta-2026-10-26',betaUpgradeWeek:52,betaUpgradeResourceFactor:.80,
  betaBundleAbsorption:.50,betaExperimentAbsorption:.50,betaUpgradeQualityGain:0,
  alphaProbeCount:12,alphaRevalidationProbeCount:6,alphaConfidenceZ:1.645,
  alphaEvidenceWeeks:13,alphaPublicationCost:35,alphaAccessCostPerUse:2,
  alphaDistributionCostPerMember:8,alphaMinimumNetCents:1,
  alphaSystematicRiskReserveCentsPerUse:0,
  paidLearningProbability:.30,rightsClearedProbability:.85,retentionCostMultiplier:1,
  forecastBetaErosionWeekly:.005,capacityControlMonthlyPerAdditionalSlot:35,
};
export const SCENARIOS=[
  {...BASE,id:'conservative',humanReference:14334.20,prospectsMonthly:4,buyerValueMedian:22000,
   trustMax:12000,initialPerceivedQuality:.76,commonError:.14,initialError:.38,
   improvementProbability:.07,correctionSuccess:.60,tokenMultiplier:2,computeMultiplier:2,
   collectionDelayWeeks:8,badDebt:.06,assetProductiveProbability:.35,assetTransferSuccess:.55,
   assetLifetimeWeeks:39,assetConstructionMultiplier:12,betaUpgradeWeek:26,betaBundleAbsorption:1,
   betaExperimentAbsorption:1,betaUpgradeResourceFactor:.65,paidLearningProbability:.12,rightsClearedProbability:.60,retentionCostMultiplier:3},
  {...BASE},
  {...BASE,id:'favorable',humanReference:57336.80,prospectsMonthly:24,buyerValueMedian:90000,
   trustMax:5000,initialPerceivedQuality:.92,commonError:.035,initialError:.16,
   improvementProbability:.24,collectionDelayWeeks:2,badDebt:.01,assetProductiveProbability:.80,
   assetTransferSuccess:.90,assetLifetimeWeeks:78,assetConstructionMultiplier:2,
   betaUpgradeWeek:78,betaBundleAbsorption:.25,betaExperimentAbsorption:.25,betaUpgradeResourceFactor:.90,
   paidLearningProbability:.50,rightsClearedProbability:.95,retentionCostMultiplier:.60},
];
export const JOB_CLASSES=[
 {id:'kernel',name:'Executable scheduling or batching policy with held-out evaluation',complexity:1,humanFactor:1,valueFactor:1,share:.40,deadline:3},
 {id:'coupled',name:'Coupled planning policy with linked constraint families',complexity:2.4,humanFactor:1.8,valueFactor:1.5,share:.40,deadline:3},
 {id:'rolling',name:'Rolling-horizon policy under scenario uncertainty',complexity:4,humanFactor:2.8,valueFactor:2,share:.20,deadline:4},
];
export const AGENTS=[
 {id:'atlas.agent.agi.eth',weight:.40,baseline:{representation:false,certificate:false,experiment:false}},
 {id:'lyra.agent.agi.eth',weight:.30,baseline:{representation:true,certificate:true,experiment:false}},
 {id:'orion.agent.agi.eth',weight:.30,baseline:{representation:false,certificate:false,experiment:true}},
];
export const ASSETS={
 representation:{name:'Typed constraint-lifting representation',workUnits:3600,researchWorkUnits:3600,retentionWorkUnits:80,buildWeeks:4,kind:'representation',prerequisites:[]},
 certificate:{name:'Original-domain certificate carrier',workUnits:4900,researchWorkUnits:4900,retentionWorkUnits:120,buildWeeks:5,kind:'certificate',prerequisites:[]},
 experiment:{name:'Family-specific counterexample experiment protocol',workUnits:2600,researchWorkUnits:2600,retentionWorkUnits:60,buildWeeks:3,kind:'experiment',prerequisites:[]},
};
export const PRICE_RATIOS=[.35,.50,.65,.80,.95];
export const POLICIES=PRICE_RATIOS.flatMap(priceRatio=>[0,.10].flatMap(scarcity=>[1.25,2].flatMap(hurdle=>[1,1.5].map(reserveFactor=>({
 id:`p${priceRatio}-s${scarcity}-h${hurdle}-r${reserveFactor}`,priceRatio,scarcity,hurdle,reserveFactor,
 allowInvestment:true,allowBundles:true,allowMeta:true,allowSharing:true,allowSeparateResearch:true,
})))));
export const RETAIN_POLICIES=PRICE_RATIOS.map(priceRatio=>({id:`beta-p${priceRatio}`,priceRatio,scarcity:0,hurdle:1e9,reserveFactor:1,
 allowInvestment:false,allowBundles:false,allowMeta:false,allowSharing:false,allowSeparateResearch:false}));
export const TRAIN_SEEDS=Array.from({length:24},(_,i)=>1010000+i);
export const CONFIRM_SEEDS=Array.from({length:128},(_,i)=>1020000+i);
export const STRESS_SEEDS=Array.from({length:20},(_,i)=>1030000+i);
export const SENSITIVITIES=[
 ['humanReference',[7167.10,14334.20,28668.40,57336.80]],
 ['buyerValueMedian',[15000,30000,50000,90000]],['prospectsMonthly',[0,2,4,8,12,24,48]],
 ['trustMax',[2000,8000,20000]],['initialCompletionBelief',[.35,.60,.85]],['humanCompletionBelief',[.4,.7,1]],
 ['commonError',[.02,.07,.20]],['initialError',[.15,.25,.45]],['semanticDetection',[.30,.65,.90]],
 ['improvementProbability',[0,.02,.07,.14,.30]],['tokenMultiplier',[1,10,50]],['computeMultiplier',[1,10,50]],
 ['collectionDelayWeeks',[0,4,8,12]],['assetConstructionMultiplier',[1,4,12,40]],
 ['assetProductiveProbability',[0,.3,.6,.9]],['assetTransferSuccess',[.3,.8,1]],
 ['assetLifetimeWeeks',[13,39,65,104]],['assetMaintenanceWeekly',[0,24,120]],
 ['bundleEffect',[.45,.75,1]],['familyScreenIncrement',[0,.15,.30]],
 ['betaBundleAbsorption',[0,.5,1]],['betaUpgradeWeek',[26,52,104]],
 ['betaUpgradeResourceFactor',[.5,.8,1]],['copyHazardWeekly',[0,.003,.03]],
 ['assetTransferCost',[0,220,1500]],['alphaProbeCount',[6,12,24]],
 ['alphaSystematicRiskReserveCentsPerUse',[0,10000,100000]],
 ['paidLearningProbability',[0,.1,.3,.6,1]],['rightsClearedProbability',[.25,.85,1]],['retentionCostMultiplier',[.25,1,5,25]],
 ['forecastBetaErosionWeekly',[0,.005,.02]],
 ['acquisitionCostPerProspect',[0,150,1000]],['seedCapital',[20000,50000,100000]],
 ['concurrency',[1,3,8]],['inputQuotaWeekly',[3000000,12000000,48000000]],
 ['outputQuotaWeekly',[750000,3000000,12000000]],['cpuHoursWeekly',[750,3000,12000]],
 ['validatorHoursWeekly',[300,1200,4800]],['workflowLatencyMultiplier',[1,3]],
 ['deadlineMultiplier',[1,2]],['setupCost',[0,12000,40000]],
];
