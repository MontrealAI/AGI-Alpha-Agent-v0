// SPDX-License-Identifier: Apache-2.0
import {simulate,defaultConfig} from './market-transfer-core.mjs';

const assert=(ok,message)=>{if(!ok)throw Error(message);};
const arms=['A','B','C'];
const noPremium=['successProbability','customerReviewMinutes','integrationCents','initialTrust',
 'skepticalShare','supportedFraction','enterpriseDays','enterpriseSlotsPerWeek'];
const validMoney=n=>Number.isSafeInteger(n)&&n>=0&&n<=1_000_000_000;

export function inspectProduction(production){
 assert(production?.schema==='agi-alpha-intake-transfer-production/v1','Expected explicit source-intake production record');
 assert(Array.isArray(production.missions)&&production.missions.length>0,'Actual distinct missions required');
 assert(new Set(production.missions).size===production.missions.length,'Duplicate representations cannot be customer jobs');
 assert(typeof production.evidenceSHA256==='string'&&/^[a-f0-9]{64}$/.test(production.evidenceSHA256),'Frozen production evidence identity required');
 const expected=new Set(production.missions),unknown=[];
 for(const arm of arms){
  const a=production.arms?.[arm];assert(a,`Missing arm ${arm}`);
  assert(Array.isArray(a.acceptedMissionIds)&&Array.isArray(a.attemptedMissionIds),`Actual outcome records required for ${arm}`);
  assert(new Set(a.attemptedMissionIds).size===a.attemptedMissionIds.length,`Duplicate mission identities ${arm}`);
  assert(a.attemptedMissionIds.every(x=>expected.has(x)),`Unregistered mission ${arm}`);
  assert(a.acceptedMissionIds.every(x=>a.attemptedMissionIds.includes(x)),`Acceptance without attempt ${arm}`);
  assert(new Set(a.acceptedMissionIds).size===a.acceptedMissionIds.length,`Repeated acceptance ${arm}`);
  assert(['complete-workflow','known-process-lower-bound'].includes(a.resources?.scope),`Explicit resource scope required ${arm}`);
  for(const k of ['cpuSecondsPerAccepted','wallSecondsPerAccepted'])assert(Number.isFinite(a.resources[k])&&a.resources[k]>=0,`Measured resource ${k} required ${arm}`);
  for(const k of ['completeRecurringCostCents','completeConstructionCostCents']){
   assert(a[k]===null||validMoney(a[k]),`Unknown monetary component must be null, not omitted ${arm}.${k}`);
   if(a[k]===null)unknown.push(`${arm}.${k}`);
  }
  if(arm!=='A')assert(a.asset&&typeof a.asset.path==='string'&&typeof a.asset.id==='string'&&
   /^[a-f0-9]{64}$/.test(a.asset.sha256),`Exact constructed tested asset identity required ${arm}`);
 }
 const common=production.missions.filter(id=>arms.every(a=>production.arms[a].acceptedMissionIds.includes(id)));
 const full=common.length===production.missions.length&&arms.every(a=>common.length===production.arms[a].acceptedMissionIds.length);
 const evidence=production.completeAcceptanceEvidence;
 const complete=evidence?.status==='PASS'&&evidence?.scope==='complete-useful-deliverable'&&
  evidence.independentlyVerified===true&&/^[a-f0-9]{64}$/.test(evidence.receiptSHA256)&&
  /^[a-f0-9]{64}$/.test(evidence.verifierSHA256);
 return {status:complete?(full?'COMPLETE_EQUIVALENT_ACCEPTED_WORK':'NOT_YET_EQUIVALENT_COMPLETE_WORK'):
  'COMPLETE_DELIVERABLE_ACCEPTANCE_NOT_VERIFIED',
  commonAcceptedMissionIds:common,distinctMissions:production.missions.length,unknownMonetaryComponents:unknown,
  completeDeliverableAcceptanceVerified:complete,
  measuredFullCostsIdentified:unknown.length===0,
  mechanicalComplete:arms.every(a=>production.arms[a].resources.scope==='complete-workflow'),
  boundary:'Internal acceptance and active researcher actions are not field quality, human minutes, purchases, or collections.'};
}

export function identificationDecision(production){
 const audit=inspectProduction(production);
 return {...audit,economicDecision:audit.status!=='COMPLETE_EQUIVALENT_ACCEPTED_WORK'?'HOLD_INCOMPLETE_EQUIVALENCE':
  audit.measuredFullCostsIdentified?'COSTS_IDENTIFIED_MARKET_VALIDATION_SEPARATE':'IDENTIFICATION_HOLD',
  observedCustomerCollectionsCents:0,actualFinancialAction:false,
  reason:audit.unknownMonetaryComponents.length?'Complete recurring/construction costs are unknown; no numerical default is substituted. Explicit conditional scenarios remain possible.':
   'Observed cost does not itself establish demand, adoption, complete investment payback, or field reliability.'};
}

export function conditionalPair(production,scenario,seed){
 const audit=inspectProduction(production);
 assert(audit.status==='COMPLETE_EQUIVALENT_ACCEPTED_WORK','Equivalent complete useful deliverables for the entire registered set require independent acceptance before economic comparison');
 assert(scenario&&typeof scenario.id==='string'&&scenario.basis==='EXPLICIT_CONDITIONAL_ASSUMPTIONS','Conditional scenario label required');
 assert(['primary-no-unmeasured-benefit','conditional-model-cost-sensitivity','exploratory-effort-sensitivity'].includes(scenario.class),'Separate primary and conditional class required');
 assert(scenario.costs&&scenario.costs.A&&scenario.costs.B&&scenario.costs.C,'All arm cost assumptions must be explicit');
 assert(Number.isSafeInteger(seed)&&seed>=1,'Positive semantic scenario seed required');
 if(scenario.class==='conditional-model-cost-sensitivity'){
  assert(audit.commonAcceptedMissionIds.length===production.missions.length,'Full registered scope must be independently accepted; no post-outcome narrowing');
  const d=production.executedStepDistinction;
  assert(d?.A==='MODEL_OR_CURATOR'&&d?.B==='MODEL_EXTRACTION'&&d?.C==='NO_RUNTIME_MODEL'&&
   d.independentAcceptedScopeEquivalent===true&&/^[a-f0-9]{64}$/.test(d.evidenceSHA256),
   'Observed model-stage distinction and independent equivalent-scope evidence required');
 }
 const shared={...defaultConfig,...scenario.shared};
 assert(shared.nextAsset===null,'A second untested asset cannot be financed');
 assert(scenario.financing==='operating-surplus'||scenario.financing==='seed-funded','Explicit source of modeled financing required');
 const baseline=production.arms.A.resources;
 const rows={};
 for(const arm of arms){
  const cost=scenario.costs[arm];
  for(const k of ['completeRecurringCostCents','completeConstructionCostCents','maintenancePerWeekCents'])assert(validMoney(cost[k]),`Explicit finite ${arm}.${k} required`);
  assert(Number.isFinite(cost.assumedIntakeMinutes)&&cost.assumedIntakeMinutes>=0,`Assumed attention capacity must be explicit ${arm}`);
  if(scenario.class!=='exploratory-effort-sensitivity')assert(cost.assumedIntakeMinutes===0,'Registered comparison permits no unmeasured attention benefit');
  if(arm==='A')assert(cost.completeConstructionCostCents===0,'Incumbent has no new asset construction charge');
  assert(!cost.quality&&!cost.customerMinutes&&!cost.integrationDiscount,'No automatic quality/effort/integration premium');
  const active=production.arms[arm].resources;
  const c={...shared,id:scenario.id,ordinaryFinalizationMinutes:scenario.costs.A.assumedIntakeMinutes,
   assetResidualMinutes:cost.assumedIntakeMinutes,commonResidualMinutes:0,hourlyProviderCents:0,
   computeAndToolCents:scenario.costs.A.completeRecurringCostCents,activeComputeAndToolCents:cost.completeRecurringCostCents,
   constructionHours:0,constructionHourlyCents:0,authoringCostCents:cost.completeConstructionCostCents,
   adoptionHours:0,adoptionInferenceCents:0,assetMaintenanceCentsPerWeek:cost.maintenancePerWeekCents,
   investmentCostBasis:'prospective-reconstruction',investmentFunding:scenario.financing,
   measuredMechanicalWallSeconds:baseline.wallSecondsPerAccepted,measuredMechanicalCpuSeconds:baseline.cpuSecondsPerAccepted,
   activeMechanicalWallSeconds:audit.mechanicalComplete?active.wallSecondsPerAccepted:baseline.wallSecondsPerAccepted,
   activeMechanicalCpuSeconds:audit.mechanicalComplete?active.cpuSecondsPerAccepted:baseline.cpuSecondsPerAccepted};
  rows[arm]=simulate(c,seed,arm,{asset:arm==='A'?undefined:production.arms[arm].asset,
   productionEvidence:`SOURCE-INTAKE production ${production.evidenceSHA256}; ${audit.commonAcceptedMissionIds.length} unique internally accepted common missions. No field quality, demand, customer effort or billing inference.`});
 }
 for(const key of noPremium)assert(arms.every(a=>rows[a].config[key]===rows.A.config[key]),`Unsubstantiated arm-specific premium ${key}`);
 return {schema:'agi-alpha-transfer-market-pair/v1',scenario:scenario.id,class:scenario.class,seed,
  basis:'SIMULATED_CONDITIONAL',sourceProductionSHA256:production.evidenceSHA256,economicIdentification:identificationDecision(production),
  exactAssets:{B:production.arms.B.asset,C:production.arms.C.asset},arms:rows,
  differences:{B_minus_A_profitCents:rows.B.summary.profitCents-rows.A.summary.profitCents,
   C_minus_A_profitCents:rows.C.summary.profitCents-rows.A.summary.profitCents,
   B_minus_C_profitCents:rows.B.summary.profitCents-rows.C.summary.profitCents},
  financeBoundary:'All prospective reconstruction charges represent an explicit full-cost scenario for the exact tested asset; actual authoring occurred outside the simulation and was not funded by these collections.',
  costBoundary:'Recurring cost scenarios cover the complete nominal attempt, including labor/model/tools/routine verification. The retained failure multiplier separately charges correction on failed work; do not pre-amortize that correction again into the nominal input. Assumed intake minutes constrain capacity only; no additional wage charge or elapsed-agent-time wage conversion occurs.',
  scopeBoundary:audit.mechanicalComplete?'Complete mechanical measurements affect finite capacity only; conversion into money remains an explicit scenario.':'Stage-only process measurements cannot grant a comparative capacity benefit. Full workflow and inference costs remain unknown.',
  noSecondAsset:'No separately constructed and tested successor is supplied; residual resources retain reserves.',
  observedCustomerCollectionsCents:0,actualFinancialAction:false};
}

export function repaymentThreshold({incrementalCostPerAcceptedCents,investmentCostCents,maintenanceCents=0}){
 assert(Number.isFinite(incrementalCostPerAcceptedCents)&&validMoney(investmentCostCents)&&validMoney(maintenanceCents),'Explicit finite threshold inputs required');
 if(incrementalCostPerAcceptedCents<=0)return {acceptedJobsRequired:null,status:'NO_POSITIVE_PER_JOB_SAVING'};
 return {acceptedJobsRequired:Math.ceil((investmentCostCents+maintenanceCents)/incrementalCostPerAcceptedCents),
  status:'CONDITIONAL_ARITHMETIC_THRESHOLD',boundary:'Equivalent accepted jobs only; excludes market allocation, price response, cash timing and foregone service. Use paired histories for commercial effect.'};
}
