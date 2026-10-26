// SPDX-License-Identifier: Apache-2.0
// Separate, explicitly A/B-only diagnostic. The three-arm adapter is unchanged.
import {simulate,defaultConfig} from '../market-transfer-core.mjs';

const assert=(ok,message)=>{if(!ok)throw Error(message);};
const hex=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const money=x=>Number.isSafeInteger(x)&&x>=0&&x<=1_000_000_000;
const sameSet=(a,b)=>Array.isArray(a)&&a.length===b.length&&new Set(a).size===a.length&&a.every(x=>b.includes(x));
export const REGISTERED_MISSIONS=Object.freeze(['F01','F02','F03','F04']);
export const DIAGNOSTIC_CLASS='exploratory-accepted-ab-no-benefit';

export function inspectAcceptedAB(production){
 assert(production?.schema==='agi-alpha-accepted-ab-diagnostic-production/v1','Explicit separate A/B production schema required');
 assert(sameSet(production.missions,REGISTERED_MISSIONS),'All four original fresh missions are required; no favorable subset');
 assert(sameSet(Object.keys(production.arms||{}),['A','B']),'This diagnostic contains A and B only; C2 remains unqualified');
 assert(hex(production.evidenceSHA256)&&hex(production.sourceThreeArmBridge?.sha256),'Production source identities required');
 assert(production.sourceThreeArmBridge.campaignStatus==='GATED_UNEXECUTED'&&
  production.sourceThreeArmBridge.completeAcceptanceStatus==='FAIL','Preserve the failed three-arm campaign');
 const e=production.independentAcceptance;
 assert(e?.scope==='complete-useful-deliverable'&&e.independentlyVerified===true&&
  hex(e.receiptSHA256)&&hex(e.verifierSHA256),'Independent complete-deliverable evidence required');
 assert(e.identitiesAccepted===true&&e.workbenchAccepted===true,'Frozen production and runtime identities must pass');
 assert(Array.isArray(e.rows)&&e.rows.length===8,'Exactly eight A/B mission-level audit rows required');
 assert(new Set(e.rows.map(r=>`${r.arm}:${r.task}`)).size===8,'Audit rows must be unique');
 const unknown=[];
 let complete=true;
 for(const arm of ['A','B']){
  const a=production.arms[arm];
  assert(sameSet(a.attemptedMissionIds,REGISTERED_MISSIONS),'Entire registered mission set must be attempted');
  assert(Array.isArray(a.acceptedMissionIds)&&new Set(a.acceptedMissionIds).size===a.acceptedMissionIds.length&&
   a.acceptedMissionIds.every(id=>REGISTERED_MISSIONS.includes(id)),'Valid distinct acceptance records required');
  const rows=e.rows.filter(r=>r.arm===arm);
  assert(sameSet(rows.map(r=>r.task),REGISTERED_MISSIONS),'Audit must cover every registered mission for each arm');
  const accepted=rows.filter(r=>r.completeHandoffAccepted===true&&r.inventoryAccepted===true&&
   r.omittedCalls===0&&r.spuriousCalls===0&&r.wrongTargetCalls===0&&Array.isArray(r.materialErrors)&&r.materialErrors.length===0).map(r=>r.task);
  assert(sameSet(a.acceptedMissionIds,accepted),'Claimed acceptance must agree with independent complete audit rows');
  complete=complete&&sameSet(accepted,REGISTERED_MISSIONS);
  assert(['known-process-lower-bound','complete-workflow'].includes(a.resources?.scope),'Resource scope must remain explicit');
  for(const k of ['cpuSecondsPerAccepted','wallSecondsPerAccepted'])assert(Number.isFinite(a.resources[k])&&a.resources[k]>=0,'Physical process measurements required');
  for(const k of ['completeRecurringCostCents','completeConstructionCostCents']){
   assert(a[k]===null||money(a[k]),`Unknown money must be null, not missing: ${arm}.${k}`);
   if(a[k]===null)unknown.push(`${arm}.${k}`);
  }
 }
 const asset=production.arms.B.asset;
 assert(asset&&typeof asset.id==='string'&&typeof asset.path==='string'&&hex(asset.sha256),'Exact accepted B asset identity required');
 assert(asset.id===production.acceptedAsset?.id&&asset.sha256===production.acceptedAsset?.sha256&&
  asset.path===production.acceptedAsset?.path,'Financed asset must match the accepted tested B manifest');
 assert(production.observedCustomerCollectionsCents===0&&production.actualFinancialAction===false,'No actual collections or transactions are supplied');
 return {schema:'agi-alpha-accepted-ab-inspection/v1',status:complete?'COMPLETE_AB_ACCEPTED_WORK':'HOLD_INCOMPLETE_AB_ACCEPTANCE',
  economicDecision:complete?(unknown.length?'IDENTIFICATION_HOLD':'COSTS_IDENTIFIED_MARKET_VALIDATION_SEPARATE'):'HOLD_INCOMPLETE_AB_ACCEPTANCE',
  distinctMissions:4,commonAcceptedMissionIds:REGISTERED_MISSIONS.filter(id=>['A','B'].every(a=>production.arms[a].acceptedMissionIds.includes(id))),
  unknownMonetaryComponents:unknown,measuredFullCostsIdentified:unknown.length===0,
  originalThreeArmCampaignStatus:'GATED_UNEXECUTED',excludedComparator:'C2 failed complete acceptance on F03; no C2 financial curve or zero-model discount.',
  observedCustomerCollectionsCents:0,actualFinancialAction:false,
  acceptanceQualification:production.acceptanceQualification,
  boundary:'Four complete customer handoffs under the frozen checker qualify this A/B diagnostic. This does not claim every auxiliary Workbench link was valid at trial time, field reliability, customer demand, human effort savings, billing or superiority over a strong fully qualified conventional provider.'};
}

export function conditionalAB(production,scenario,seed){
 const identification=inspectAcceptedAB(production);
 assert(identification.status==='COMPLETE_AB_ACCEPTED_WORK','Complete A/B acceptance for all four missions is required');
 assert(scenario&&typeof scenario.id==='string'&&scenario.basis==='EXPLICIT_CONDITIONAL_ASSUMPTIONS'&&
  scenario.class===DIAGNOSTIC_CLASS,'Explicit separately labelled exploratory A/B scenario required');
 assert(scenario.financing==='operating-surplus','Only currently collected operating surplus may fund this diagnostic');
 assert(Number.isSafeInteger(seed)&&seed>=1,'Positive paired semantic seed required');
 assert(sameSet(Object.keys(scenario.costs||{}),['A','B']),'Exactly A/B cost assumptions required; C2 is excluded');
 const permitted=['completeRecurringCostCents','completeConstructionCostCents','maintenancePerWeekCents','assumedIntakeMinutes'];
 for(const arm of ['A','B']){
  const cost=scenario.costs[arm];
  assert(sameSet(Object.keys(cost),permitted),'No extra arm-specific quality, effort, capacity or cost fields');
  for(const k of permitted.filter(x=>x!=='assumedIntakeMinutes'))assert(money(cost[k]),`Explicit nonnegative conditional cents required: ${arm}.${k}`);
  assert(cost.assumedIntakeMinutes===0,'No unmeasured operator-minute benefit may be asserted');
 }
 assert(scenario.costs.A.completeRecurringCostCents===scenario.costs.B.completeRecurringCostCents,'A and B must have the same assumed complete nominal cost');
 assert(scenario.costs.A.completeConstructionCostCents===0&&scenario.costs.A.maintenancePerWeekCents===0,'A has no new asset construction or maintenance');
 const shared={...defaultConfig,...scenario.shared};
 assert(shared.nextAsset===null,'No separately tested next capability is available');
 for(const k of ['activeComputeAndToolCents','activeMechanicalWallSeconds','activeMechanicalCpuSeconds',
  'ordinaryFinalizationMinutes','assetResidualMinutes','commonResidualMinutes','hourlyProviderCents',
  'measuredMechanicalWallSeconds','measuredMechanicalCpuSeconds','constructionHours','constructionHourlyCents',
  'authoringCostCents','adoptionHours','adoptionInferenceCents','investmentCostBasis','investmentFunding'])
  assert(!Object.hasOwn(scenario.shared||{},k),`Protected capability/cost mapping cannot be overridden: ${k}`);
 const rows={};
 for(const arm of ['A','B']){
  const cost=scenario.costs[arm];
  const c={...shared,id:scenario.id,ordinaryFinalizationMinutes:0,assetResidualMinutes:0,commonResidualMinutes:0,
   hourlyProviderCents:0,computeAndToolCents:scenario.costs.A.completeRecurringCostCents,
   activeComputeAndToolCents:cost.completeRecurringCostCents,constructionHours:0,constructionHourlyCents:0,
   authoringCostCents:cost.completeConstructionCostCents,adoptionHours:0,adoptionInferenceCents:0,
   assetMaintenanceCentsPerWeek:cost.maintenancePerWeekCents,investmentCostBasis:'prospective-reconstruction',
   investmentFunding:'operating-surplus',activeMechanicalWallSeconds:defaultConfig.measuredMechanicalWallSeconds,
   activeMechanicalCpuSeconds:defaultConfig.measuredMechanicalCpuSeconds};
  rows[arm]=simulate(c,seed,arm,{asset:arm==='B'?production.arms.B.asset:undefined,
   productionEvidence:`Accepted A/B diagnostic; evidence ${production.evidenceSHA256}; independent audit ${production.independentAcceptance.receiptSHA256}; all four fresh missions. No monetized, field-quality, effort or capacity advantage is identified.`});
 }
 return {schema:'agi-alpha-accepted-ab-diagnostic-pair/v1',scenario:scenario.id,class:DIAGNOSTIC_CLASS,seed,
  basis:'EXPLORATORY_CONDITIONAL_SIMULATION',sourceProductionSHA256:production.evidenceSHA256,
  economicIdentification:identification,exactAsset:production.arms.B.asset,arms:rows,
  differences:{B_minus_A_profitCents:rows.B.summary.profitCents-rows.A.summary.profitCents},
  costBoundary:'Equal complete nominal A/B attempt cost is an explicit scenario, not an estimate or zero-imputed bill. It includes routine labor/model/tool/verification. The retained failure multiplier separately charges failed-work correction. The B construction envelope includes discovery, failed builds, authoring, integration and shared allocation exactly once.',
  financeBoundary:'The exact tested B source is offered for prospective reconstruction only after a worthwhile earned-cash decision. Actual research construction occurred outside this model and was not funded by simulated collections.',
  mechanicalBoundary:'Stage timings remain evidence only. Common inherited machine budgets and equal operator minutes create no B capacity premium.',
  inferenceBoundary:'With identical assumed operating benefit, zero saving is algebraic. Simulations test implementation/accounting consistency across strategic stresses; they are not independent estimates of an absent empirical treatment effect.',
  originalThreeArmCampaignStatus:'GATED_UNEXECUTED',observedCustomerCollectionsCents:0,actualFinancialAction:false};
}
