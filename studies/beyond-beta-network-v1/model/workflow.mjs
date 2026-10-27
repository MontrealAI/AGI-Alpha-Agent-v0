// SPDX-License-Identifier: Apache-2.0
/**
 * MODELED, fully automated workflow. No live API calls or human labor.
 * Rates: official OpenAI documentation checked 2026-10-26.
 * All budgets, probabilities, latency and asset effects are explored assumptions.
 * rng(label) must be a stable keyed U[0,1) draw, so paired arms share uncertainty.
 */
export const DEFAULT_WORKFLOW_CONFIG = Object.freeze({
  betaVersion:'gpt-6-astra+gpt-6.1-terra/2026-10-26',betaResourceFactor:1,betaBundleAbsorption:0,
  tokenMultiplier: 1, computeMultiplier: 1, commonError: 0.03,
  initialError: 0.18, semanticErrorFraction: 0.25, semanticDetection: 0.90, mechanicalDetection: 0.995,
  correctionSuccess: 0.70, maxRetries: 2, improvementProbability: 0.12,
  workflowLatencyMultiplier: 1, cpuPricePerHour: 0.12,
  candidatesPerJob: 12, candidateSearchCpuHours: 20,
  candidateValidatorCpuHours: 0.20, finalValidatorCpuHours: 0.50,
  cacheReadFraction: 0.20, cacheWriteFraction: 0.05,
  inputTokensPerModelHour: 2_000_000, outputTokensPerModelHour: 80_000,
  evaluationParallelism: 8, maxInputTokensPerCall: 200_000,
  webSearchPrice: 0.01, fileSearchPrice: 0.0025,
  containerBlockPrice: 0.12, containerBlockMinutes: 20,
  storagePricePerGbDay: 0.10, storageGbDaysPerJob: 0.10,
  // A+B alter specified reconstruction/search/validation resources only.
  bundleResourceEffect: 1, bundleComplexResourceFactor: 0.40,
  bundleStandardResourceFactor: 0.75, singleAssetOverhead: 0.10,
  baselineScreenSensitivity:0.65,betaAbsorbableScreenIncrement:0.15,familyScreenIncrement:0.15,cheapScreenFalsePositive:0.01,
  cheapScreenCpuFraction: 0.10,
  // Certificate does not automatically prove semantic interpretation.
  certificateMechanicalDetection: 0.995,
  reviewTrials: 96, reviewTrialCpuHours: 0.25,
  reviewInvalidProbability: 0.05, reviewCaseCoverage: 0.25, reviewDetection: 0.98,
  reviewEarlyAbort: true,
  campaignInputPerWorkUnit:5000,campaignOutputPerWorkUnit:900,
  campaignCPUPerWorkUnit:1.2,campaignServiceHoursPerWorkUnit:0.012,
  campaignValidationFraction:0.30,assetConstructionMultiplier:1,
  constructionSearchCallsPerWorkUnit:0.01,constructionFileCallsPerWorkUnit:0.05,
  constructionInputPerTrial:100_000,constructionTrialsPerContainerBlock:4,
  constructionStorageGbDaysPerWorkUnit:0.01,
});

export const ROLE_BUDGETS = Object.freeze({
  intake: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 100_000, output: 16_000 },
  producer: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 100_000, output: 20_000 },
  candidateCritic: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 40_000, output: 5_000 },
  semanticCritic: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 80_000, output: 20_000 },
  improvementEvaluator: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 80_000, output: 16_000 },
  correction: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 120_000, output: 24_000 },
  revalidation: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 60_000, output: 12_000 },
  recovery: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 90_000, output: 18_000 },
  executor: { model: 'gpt-6.1-terra', mode: 'standard', effort: 'max', input: 20_000, output: 3_000 },
  packaging: { model: 'gpt-6.1-terra', mode: 'standard', effort: 'max', input: 60_000, output: 12_000 },
  capabilityEvaluator: { model: 'gpt-6-astra', mode: 'pro', effort: 'max', input: 160_000, output: 32_000 },
});

export const AUXILIARY_BUDGETS = Object.freeze({
  quote_intake:{roles:{intake:0.25},searchCpuHours:0,validatorCpuHours:0.02,webSearch:0,fileSearch:4,containerBlocks:1},
  investment_evaluation:{roles:{capabilityEvaluator:4,candidateCritic:4,semanticCritic:1,executor:1},searchCpuHours:8,validatorCpuHours:2,webSearch:12,fileSearch:12,containerBlocks:2},
  transfer_adaptation:{roles:{producer:4,candidateCritic:4,semanticCritic:1,revalidation:2,executor:4,packaging:1},searchCpuHours:16,validatorCpuHours:4,webSearch:4,fileSearch:12,containerBlocks:2},
  revalidation:{roles:{revalidation:2,semanticCritic:1,improvementEvaluator:1,executor:2},searchCpuHours:0,validatorCpuHours:4,webSearch:2,fileSearch:8,containerBlocks:1},
  maintenance:{roles:{candidateCritic:0.5,revalidation:0.25,executor:0.5},searchCpuHours:0.5,validatorCpuHours:0.5,webSearch:0,fileSearch:4,containerBlocks:1},
  recovery:{roles:{recovery:1,candidateCritic:1,executor:2,packaging:0.5},searchCpuHours:4,validatorCpuHours:2,webSearch:2,fileSearch:8,containerBlocks:2},
});

export const CONSTRUCTION_ALLOCATION = Object.freeze([
  {role:'construction_hypothesis_design',share:0.15},
  {role:'construction_candidates',share:0.35},
  {role:'construction_failed_design_correction',share:0.20},
  {role:'construction_critic',share:0.10},
  {role:'construction_migration_integration',share:0.10},
  {role:'construction_internal_revalidation',share:0.10},
]);

// Classification of already-charged customer work. This does not add a bill or
// assert that every inventive job leaves a reusable capability.
export const PAID_JOB_COST_COMPONENTS=Object.freeze({
  problemFormulation:['intake'],
  candidateConstructionAndLearning:['producer','candidateCritic','executor','correction'],
  verificationAndRevalidation:['semanticCritic','improvementEvaluator','revalidation'],
  packagingAndRecovery:['packaging','recovery'],
  computeToolsAndStorage:['solverCompute','webSearch','fileSearch','sandboxOrchestration','storage'],
});
export function paidJobCostComponents(plan){
  if(!Number.isSafeInteger(plan?.costCents)||!plan.costDetailsCents)throw Error('A priced customer-job plan is required');
  const assigned=new Set(),componentsCents={};
  for(const [name,fields]of Object.entries(PAID_JOB_COST_COMPONENTS)){
    componentsCents[name]=fields.reduce((sum,key)=>{assigned.add(key);return sum+(plan.costDetailsCents[key]??0);},0);
  }
  const unclassifiedCents=Object.entries(plan.costDetailsCents).filter(([key])=>!assigned.has(key)).reduce((sum,[,amount])=>sum+amount,0);
  const classifiedTotalCents=Object.values(componentsCents).reduce((sum,x)=>sum+x,0)+unclassifiedCents;
  if(classifiedTotalCents!==plan.costCents)throw Error('Customer-job cost classification does not reconcile');
  return {componentsCents,unclassifiedCents,totalCents:classifiedTotalCents,
    alreadyChargedInCustomerJob:true,additionalChargeCents:0,
    learningScope:'Customer-scoped modeled formulation, candidate search, criticism, correction and execution',
    reusableAlphaGuaranteed:false,retentionGeneralizationAndNetworkAdmissionIncluded:false};
}

const RATE = {
  'gpt-6-astra': { input: 10, cachedInput: 1, cacheWrite: 12.5, output: 50 },
  'gpt-6.1-terra': { input: 1, cachedInput: 0.05, cacheWrite: 1.25, output: 5 },
};
const clamp = (x, lo=0, hi=1) => Math.max(lo, Math.min(hi, Number(x)));
const cents = x => Math.round(x * 100);
const normalize = c => {
  const out={ ...DEFAULT_WORKFLOW_CONFIG, ...c };
  if(c?.betaExperimentAbsorption===undefined)out.betaExperimentAbsorption=out.betaBundleAbsorption;
  // Study-config aliases. A factor of1 is a genuine null in every job class.
  if(c?.bundleEffect!==undefined){
    out.bundleComplexResourceFactor=c.bundleEffect;
    out.bundleStandardResourceFactor=1-(1-c.bundleEffect)*(1-DEFAULT_WORKFLOW_CONFIG.bundleStandardResourceFactor)/(1-DEFAULT_WORKFLOW_CONFIG.bundleComplexResourceFactor);
  }
  if(c?.singleCapabilityOverhead!==undefined)out.singleAssetOverhead=c.singleCapabilityOverhead;
  if(c?.cheapScreenSensitivity!==undefined&&c.familyScreenIncrement===undefined)out.familyScreenIncrement=Math.max(0,c.cheapScreenSensitivity-out.baselineScreenSensitivity);
  return out;
};
const draw = (rng, key) => { const x=rng(key); if (!(x>=0 && x<1)) throw new Error(`Invalid keyed draw ${key}`); return x; };

const RESERVATION_CACHE_LIMIT=4096;
const reservationCache=new Map();
let configFingerprints=new WeakMap(),reservationCacheCounters={requests:0,hits:0,misses:0,bypasses:0};
const freezeReservation=x=>{
  if(x&&typeof x==='object'&&!Object.isFrozen(x)){
    for(const value of Object.values(x))freezeReservation(value);Object.freeze(x);
  }
  return x;
};
function configFingerprint(config){
  if(!config||typeof config!=='object')return null;
  const keys=Object.keys(config),old=configFingerprints.get(config);
  // The snapshot check preserves exact behavior if a caller mutates a plain
  // configuration. Nonprimitive inputs bypass the cache rather than relying
  // on a stale shallow fingerprint or JSON's lossy function/NaN conversion.
  if(old&&keys.length===old.keys.length&&keys.every((k,i)=>k===old.keys[i]&&Object.is(config[k],old.values[i])))return old;
  const values=keys.map(k=>config[k]);
  if(values.some(x=>x!==null&&x!==undefined&&!['string','boolean','number'].includes(typeof x))||
     values.some(x=>typeof x==='number'&&(!Number.isFinite(x)||Object.is(x,-0))))return null;
  const normalized=normalize(config),entry={keys,values,normalized,key:JSON.stringify(normalized)};
  configFingerprints.set(config,entry);return entry;
}
export function clearReservationCache(){reservationCache.clear();configFingerprints=new WeakMap();
  reservationCacheCounters={requests:0,hits:0,misses:0,bypasses:0};}
export function reservationCacheStats(){return {...reservationCacheCounters,size:reservationCache.size,limit:RESERVATION_CACHE_LIMIT};}

function assetFactor(c, job, assets) {
  const a=Boolean(assets.representation), b=Boolean(assets.certificate);
  if (a && b) {
    const target=job.complexity>1 ? c.bundleComplexResourceFactor : c.bundleStandardResourceFactor;
    return Math.max(0.01, 1+clamp(c.bundleResourceEffect)*(1-clamp(c.betaBundleAbsorption))*(target-1));
  }
  // Competent Beta may ignore an unhelpful isolated component.
  return 1;
}

function account(c) {
  const roles={}, detail={}, tokens={input:0,uncachedInput:0,cachedInput:0,cacheWrite:0,output:0};
  let searchCpuHours=0, validatorCpuHours=0;
  function role(name, units=1, budgetOverride=null) {
    if (!(units>=0)) throw new Error('Negative role units');
    const b=budgetOverride??ROLE_BUDGETS[name], r=RATE[b.model];
    const input=Math.ceil(b.input*units*c.tokenMultiplier*c.betaResourceFactor), output=Math.ceil(b.output*units*c.tokenMultiplier*c.betaResourceFactor);
    const cachedInput=Math.floor(input*clamp(c.cacheReadFraction));
    const cacheWrite=Math.floor(input*clamp(c.cacheWriteFraction,0,1-clamp(c.cacheReadFraction)));
    const uncachedInput=input-cachedInput-cacheWrite;
    // Explicitly split all aggregated role work into short-context requests.
    const calls=Math.max(input || output ? 1:0,Math.ceil(input/Math.min(272_000,c.maxInputTokensPerCall)),Math.ceil(output/128_000));
    const costCents=cents((uncachedInput*r.input+cachedInput*r.cachedInput+cacheWrite*r.cacheWrite+output*r.output)/1e6);
    const prev=roles[name]??{model:b.model,mode:b.mode,effort:b.effort,calls:0,input:0,uncachedInput:0,cachedInput:0,cacheWrite:0,output:0,costCents:0};
    for(const k of ['calls','input','uncachedInput','cachedInput','cacheWrite','output','costCents']) prev[k]+={calls,input,uncachedInput,cachedInput,cacheWrite,output,costCents}[k];
    roles[name]=prev;
    for(const k of Object.keys(tokens)) tokens[k]+={input,uncachedInput,cachedInput,cacheWrite,output}[k];
    detail[name]=(detail[name]??0)+costCents;
  }
  function cpu(search, validation) {searchCpuHours+=search*c.computeMultiplier*c.betaResourceFactor;validatorCpuHours+=validation*c.computeMultiplier;}
  function finish({candidateExecutions=0,scale=1,toolCounts=null,storageGbDays=null}={}) {
    // Tool counts are explicit assumptions; CPU time is billed separately from model tokens.
    const toolCalls=toolCounts?{...toolCounts,containerBlockMinutes:c.containerBlockMinutes}:{webSearch:Math.ceil(6*scale),fileSearch:Math.ceil(8*scale),containerBlocks:Math.ceil(candidateExecutions/4)+Math.ceil(scale),containerBlockMinutes:c.containerBlockMinutes};
    detail.solverCompute=cents((searchCpuHours+validatorCpuHours)*c.cpuPricePerHour);
    detail.webSearch=cents(toolCalls.webSearch*c.webSearchPrice);
    detail.fileSearch=cents(toolCalls.fileSearch*c.fileSearchPrice);
    detail.sandboxOrchestration=cents(toolCalls.containerBlocks*c.containerBlockPrice);
    detail.storage=cents((storageGbDays??c.storageGbDaysPerJob*scale)*c.storagePricePerGbDay);
    const serviceHours=c.workflowLatencyMultiplier*(tokens.input/c.inputTokensPerModelHour+tokens.output/c.outputTokensPerModelHour+(searchCpuHours+validatorCpuHours)/c.evaluationParallelism);
    return {costCents:Object.values(detail).reduce((a,b)=>a+b,0),costDetailsCents:detail,roleUsage:roles,tokens,toolCalls,
      resources:{serviceHours,searchCpuHours,validatorCpuHours,cpuHours:searchCpuHours+validatorCpuHours},
      accounting:{currency:'USD',monetaryUnit:'integer_cents',reasoningIncludedInOutput:true,proInternalWorkIncluded:true,shortContextRequestSplittingAssumed:true,cpuSeparateFromSandboxOrchestration:true,
        betaVersion:c.betaVersion,betaResourceFactor:c.betaResourceFactor,betaBundleAbsorption:c.betaBundleAbsorption,betaUpgradeEffectsAreAssumed:true}};
  }
  return {role,cpu,finish};
}

/** Automated ancillary work, with no hidden labor or claim of a passed test. */
export function planAuxiliary(config,kind,{scale=1}={}) {
  const c=normalize(config),spec=AUXILIARY_BUDGETS[kind];
  if(!spec)throw new Error(`Unknown auxiliary kind: ${kind}`);
  if(!(scale>0&&Number.isFinite(scale)))throw new Error('Invalid auxiliary scale');
  const a=account(c);for(const [role,units]of Object.entries(spec.roles))a.role(role,units*scale);
  a.cpu(spec.searchCpuHours*scale,spec.validatorCpuHours*scale);
  const toolCounts={webSearch:Math.ceil(spec.webSearch*scale),fileSearch:Math.ceil(spec.fileSearch*scale),containerBlocks:Math.ceil(spec.containerBlocks*scale)};
  const actual=a.finish({scale,toolCounts});
  return {...actual,reservedResources:{...actual.resources},reservedTokens:{...actual.tokens},reservedCostCents:actual.costCents,
    diagnostics:{auxiliaryKind:kind,scale,modeled:true,evidenceCategory:'Assumed or explored',claimsValidationResult:false,claimsExecutionAuthority:false,
      distinction:kind==='quote_intake'?'Pre-contract qualification; separate from post-contract formalization':'Budgeted automated ancillary operation'}};
}

/**
 * Complete construction work, including unsuccessful search, expressed in work
 * units rather than dollars. All allocations are hypothetical resource counts.
 * Final independent held-out review is priced separately by planCampaignReview.
 */
export function planConstruction(config,{workUnits,keys=[]}={}) {
  const c=normalize(config);
  if(!(workUnits>=0&&Number.isFinite(workUnits)))throw new Error('Invalid construction work units');
  const effectiveWorkUnits=workUnits*c.assetConstructionMultiplier;
  if(!(effectiveWorkUnits>=0&&Number.isFinite(effectiveWorkUnits)))throw new Error('Invalid construction scaling');
  const input=Math.ceil(effectiveWorkUnits*c.campaignInputPerWorkUnit*c.tokenMultiplier);
  const output=Math.ceil(effectiveWorkUnits*c.campaignOutputPerWorkUnit*c.tokenMultiplier);
  // Counts are scaled once, then partitioned exactly into named work stages.
  const a=account({...c,tokenMultiplier:1});let inputAllocated=0,outputAllocated=0;
  for(let i=0;i<CONSTRUCTION_ALLOCATION.length;i++){
    const spec=CONSTRUCTION_ALLOCATION[i],last=i===CONSTRUCTION_ALLOCATION.length-1;
    const stageInput=last?input-inputAllocated:Math.floor(input*spec.share);
    const stageOutput=last?output-outputAllocated:Math.floor(output*spec.share);
    inputAllocated+=stageInput;outputAllocated+=stageOutput;
    a.role(spec.role,1,{model:'gpt-6-astra',mode:'pro',effort:'max',input:stageInput,output:stageOutput});
  }
  const rawCpu=effectiveWorkUnits*c.campaignCPUPerWorkUnit,validationFraction=clamp(c.campaignValidationFraction);
  a.cpu(rawCpu*(1-validationFraction),rawCpu*validationFraction);
  const trials=Math.ceil(effectiveWorkUnits*c.campaignInputPerWorkUnit/c.constructionInputPerTrial);
  const toolCounts={webSearch:Math.ceil(effectiveWorkUnits*c.constructionSearchCallsPerWorkUnit),
    fileSearch:Math.ceil(effectiveWorkUnits*c.constructionFileCallsPerWorkUnit),
    containerBlocks:Math.ceil(trials/c.constructionTrialsPerContainerBlock)};
  const storageGbDays=effectiveWorkUnits*c.constructionStorageGbDaysPerWorkUnit;
  const actual=a.finish({scale:effectiveWorkUnits,toolCounts,storageGbDays});
  const tokenHours=actual.tokens.input/c.inputTokensPerModelHour+actual.tokens.output/c.outputTokensPerModelHour;
  const declaredHours=effectiveWorkUnits*c.campaignServiceHoursPerWorkUnit*c.tokenMultiplier*c.betaResourceFactor;
  actual.resources.serviceHours=c.workflowLatencyMultiplier*Math.max(tokenHours,declaredHours);
  return {...actual,reservedResources:{...actual.resources},reservedTokens:{...actual.tokens},reservedCostCents:actual.costCents,
    diagnostics:{modeled:true,evidenceCategory:'Assumed or explored',keys,baseWorkUnits:workUnits,effectiveWorkUnits,
      nominalCandidateTrials:trials,allFailedTrialsIncluded:true,resourceAllocation:CONSTRUCTION_ALLOCATION,
      fixedDollarBudget:false,unallocatedResidualCents:0,contingencyExpenseCents:0,
      finalIndependentReviewIncluded:false,storageGbDays,
      serviceOccupancyRule:'Maximum of declared occupied service time and token-processing estimate; solver CPU is separately flow-booked',
      claimsSuccessfulInvention:false,claimsValidationResult:false,claimsExecutionAuthority:false}};
}

/** Single arithmetic implementation shared by cached and uncached controls. */
function calculateReservation(c,job,capabilities){
  const scale=Math.max(0.1,job.complexity??1),f=assetFactor(c,{...job,complexity:scale},capabilities);
  const a=account(c);a.role('intake',scale);
  if(job.scopeSupported===false){a.role('recovery',scale);return a.finish({scale,candidateExecutions:0});}
  const n=Math.max(1,Math.ceil(job.candidateCount??c.candidatesPerJob*scale)), attempts=1+Math.floor(clamp(c.maxRetries,0,2));
  for(let i=0;i<attempts;i++)a.role('semanticCritic',scale);
  for(let i=0;i<n*attempts;i++){a.role('producer',f);a.role('candidateCritic',f);a.role('executor');a.cpu(c.candidateSearchCpuHours*f,c.candidateValidatorCpuHours*f);}
  for(let i=1;i<attempts;i++){a.role('correction',scale*f);a.role('revalidation',scale*f);}
  a.role('improvementEvaluator',scale);a.role('packaging',scale);a.role('recovery',scale);
  a.cpu(0,c.finalValidatorCpuHours*scale);
  return a.finish({candidateExecutions:n*attempts,scale});
}

/** Blind upper reservation: never calls rng or inspects realized correctness/fitness. */
export function reserveJobUncached(config,job,capabilities={}){
  return calculateReservation(normalize(config),job,capabilities);
}
export function reserveJob(config,job,capabilities={}){
  reservationCacheCounters.requests++;
  const fingerprint=configFingerprint(config),complexity=job.complexity??1,candidateCount=job.candidateCount??null;
  const primitiveJobValue=x=>['number','string','boolean'].includes(typeof x)&&Number.isFinite(Number(x));
  if(!fingerprint||!primitiveJobValue(complexity)||candidateCount!==null&&!primitiveJobValue(candidateCount)){
    reservationCacheCounters.bypasses++;return freezeReservation(reserveJobUncached(config,job,capabilities));
  }
  // Job identity and future draws never influence a blind reservation.
  const key=fingerprint.key+'|'+JSON.stringify([complexity,candidateCount,job.scopeSupported===false,
    Boolean(capabilities.representation),Boolean(capabilities.certificate),Boolean(capabilities.experiment),Boolean(capabilities.recourse)]);
  if(reservationCache.has(key)){
    reservationCacheCounters.hits++;const value=reservationCache.get(key);
    reservationCache.delete(key);reservationCache.set(key,value);return value;
  }
  reservationCacheCounters.misses++;
  const result=freezeReservation(calculateReservation(fingerprint.normalized,job,capabilities));
  if(reservationCache.size>=RESERVATION_CACHE_LIMIT)reservationCache.delete(reservationCache.keys().next().value);
  reservationCache.set(key,result);return result;
}

export function planJob(config, job, capabilities={}, rng) {
  if(typeof rng!=='function') throw new Error('planJob requires a stable rng(label) function');
  const c=normalize(config), scale=Math.max(0.1,job.complexity??1), f=assetFactor(c,{...job,complexity:scale},capabilities);
  const reservation=reserveJob(c,job,capabilities), a=account(c);a.role('intake',scale);
  if(job.scopeSupported===false){
    a.role('recovery',scale);const actual=a.finish({scale});
    return {...actual,reservedResources:reservation.resources,reservedCostCents:reservation.costCents,reservedTokens:reservation.tokens,
      status:{code:'out_of_scope',correct:false,feasible:false,improved:false,detected:false,retries:0,abstained:true},
      diagnostics:{jobId:job.id,commonBlindspot:false,independentlyMachineChecked:false,candidates:0,baselineSolverAvailable:true,scopeSupported:false}};
  }
  const n=Math.max(1,Math.ceil(job.candidateCount??c.candidatesPerJob*scale)), maxAttempts=1+Math.floor(clamp(c.maxRetries,0,2));
  const commonBlindspot=draw(rng,'common-specification-blindspot')<clamp(c.commonError);
  let semanticWrong=commonBlindspot || draw(rng,'initial-semantic-error')<clamp(c.initialError*c.semanticErrorFraction);
  let selected=null,attempts=0,executions=0,invalidCandidates=0,screenedInvalid=0,screenedValid=0,detectedErrors=0,observedSemanticWarning=false;
  const rows=[];
  for(let attempt=0;attempt<maxAttempts;attempt++) {
    attempts++;a.role('semanticCritic',scale);
    if(attempt){a.role('correction',scale*f);a.role('revalidation',scale*f);if(!commonBlindspot&&draw(rng,`correction-semantic-${attempt}`)<clamp(c.correctionSuccess)) semanticWrong=false;}
    const semanticDetected=semanticWrong&&!commonBlindspot&&draw(rng,`semantic-detection-${attempt}`)<clamp(c.semanticDetection);
    observedSemanticWarning=semanticDetected;
    for(let k=0;k<n;k++) {
      const key=`attempt-${attempt}-candidate-${k}`;executions++;
      a.role('producer',f);a.role('candidateCritic',f);a.role('executor');
      const mechanicalWrong=draw(rng,`${key}-mechanical`)<clamp(c.initialError*(attempt?1-clamp(c.correctionSuccess):1));
      const invalid=mechanicalWrong||semanticWrong;if(invalid)invalidCandidates++;
      const claimedImprovement=draw(rng,`${key}-improves`)<clamp(c.improvementProbability);
      // The cheap test can detect mechanical invalidity, not an unknown wrong charter.
      const absorption=clamp(c.betaBundleAbsorption),screenAbsorption=clamp(c.betaExperimentAbsorption);
      const screenSensitivity=clamp(c.baselineScreenSensitivity+screenAbsorption*c.betaAbsorbableScreenIncrement+(capabilities.experiment?(1-screenAbsorption)*c.familyScreenIncrement:0));
      const cheapReject=draw(rng,`${key}-cheap-screen`)<(mechanicalWrong?screenSensitivity:clamp(c.cheapScreenFalsePositive));
      if(cheapReject){if(mechanicalWrong)screenedInvalid++;else screenedValid++;}
      const spend=cheapReject?clamp(c.cheapScreenCpuFraction):1;
      a.cpu(c.candidateSearchCpuHours*f*spend,c.candidateValidatorCpuHours*f*spend);
      const certificateIncrement=Math.max(0,c.certificateMechanicalDetection-c.mechanicalDetection);
      const coverage=c.mechanicalDetection+absorption*certificateIncrement+(capabilities.certificate?(1-absorption)*certificateIncrement:0);
      const mechanicalDetected=!cheapReject&&mechanicalWrong&&draw(rng,`${key}-machine-detection`)<clamp(coverage);
      const detected=cheapReject||mechanicalDetected||semanticDetected;
      if(detected)detectedErrors++;
      rows.push({attempt,candidate:k,mechanicalWrong,semanticWrong,claimedImprovement,cheapReject,mechanicalDetected,semanticDetected});
      // A false pass may be selected; validity is not used to pick or rank a candidate.
      if(!detected&&claimedImprovement&&!selected)selected={mechanicalWrong,semanticWrong,attempt,candidate:k};
    }
    if(selected)break;
  }
  a.role('improvementEvaluator',scale);a.role('packaging',scale);a.cpu(0,c.finalValidatorCpuHours*scale);
  const abstained=!selected&&observedSemanticWarning;
  // Known competent solver remains available when search finds no improvement.
  const correct=selected?!selected.mechanicalWrong&&!selected.semanticWrong:!semanticWrong;
  const feasible=correct&&!abstained;
  const improved=Boolean(selected)&&correct&&!abstained;
  const undetectedMaterialError=!abstained&&!correct;
  if(!selected||abstained)a.role('recovery',scale);
  const actual=a.finish({candidateExecutions:executions,scale});
  const code=abstained?'abstained':undetectedMaterialError?'invalid_pass':improved?'improved':'no_improvement';
  return {...actual,reservedResources:reservation.resources,reservedCostCents:reservation.costCents,reservedTokens:reservation.tokens,
    status:{code,correct,feasible,improved,detected:detectedErrors>0,retries:attempts-1,abstained},
    diagnostics:{jobId:job.id,commonBlindspot,semanticWrong,independentlyMachineChecked:true,semanticTruthProved:false,undetectedMaterialError,
      attempts,candidates:executions,invalidCandidates,screenedInvalid,screenedValid,detectedErrors,selected,baselineSolverAvailable:true,
      observedCheapRejections:rows.filter(r=>r.cheapReject).length,
      observedPostScreenMechanicalFailures:rows.filter(r=>r.mechanicalDetected).length,
      baselineScreenSensitivity:clamp(c.baselineScreenSensitivity+clamp(c.betaExperimentAbsorption)*c.betaAbsorbableScreenIncrement),familyScreenIncrement:capabilities.experiment?(1-clamp(c.betaExperimentAbsorption))*c.familyScreenIncrement:0,
      resourceFactor:f,qualityBonus:0,mechanisms:{representation:Boolean(capabilities.representation),certificate:Boolean(capabilities.certificate),experiment:Boolean(capabilities.experiment)},candidateHistory:rows}};
}

/** Independent held-out capability test campaign; never descendant-job evidence. */
export function planCampaignReview(config, campaign={}, capabilities={}, rng) {
  const c=normalize(config), n=Math.max(1,Math.ceil(campaign.trials??c.reviewTrials)), a=account(c), reserve=account(c);
  for(const x of [a,reserve]){x.role('capabilityEvaluator');x.role('semanticCritic');x.role('packaging');}
  let tested=0,rejected=false,invalidTests=0;
  const commonBlindspot=draw(rng,'review-common-blindspot')<clamp(c.commonError);
  const latentInvalid=campaign.valid===false || (campaign.valid!==true && draw(rng,'review-latent-invalid')<clamp(campaign.invalidProbability??c.reviewInvalidProbability));
  for(let k=0;k<n;k++){
    tested++;a.role('candidateCritic',0.1);a.cpu(0,c.reviewTrialCpuHours);
    const invalid=latentInvalid&&draw(rng,`review-trial-${k}-invalid`)<clamp(c.reviewCaseCoverage);
    if(invalid)invalidTests++;
    if(invalid&&!commonBlindspot&&draw(rng,`review-trial-${k}-detect`)<clamp(c.reviewDetection)){rejected=true;if(c.reviewEarlyAbort)break;}
  }
  for(let k=0;k<n;k++){reserve.role('candidateCritic',0.1);reserve.cpu(0,c.reviewTrialCpuHours);}
  // Recovery/rejection reporting is reserved in every campaign and charged when used.
  reserve.role('recovery');if(rejected)a.role('recovery');
  const actual=a.finish({candidateExecutions:tested}), bound=reserve.finish({candidateExecutions:n});
  return {...actual,reservedResources:bound.resources,reservedCostCents:bound.costCents,reservedTokens:bound.tokens,
    status:{code:rejected?'rejected':'passed',accepted:!rejected,rejected},
    diagnostics:{campaignId:campaign.id,independentCampaign:true,heldOutTrials:tested,trialBudget:n,invalidTests,latentInvalid,commonBlindspot,
      independentMachineChecks:true,semanticTruthProved:false,truthUsedForAdmission:false,capabilitiesUsedForValidation:false}};
}

