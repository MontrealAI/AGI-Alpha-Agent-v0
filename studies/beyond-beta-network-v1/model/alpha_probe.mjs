// SPDX-License-Identifier: Apache-2.0
// Paired modeled mission probes. Neither model agreement nor a correctness pass is Alpha.
import {planJob,reserveJob,planCampaignReview} from './workflow.mjs';
import {assessAlpha} from './alpha_gate.mjs';

const sum=a=>a.reduce((s,x)=>s+x,0);
const clamp=x=>Math.max(0,Math.min(1,x));
const cents=x=>Math.round(x*100);
export function resourceOf(p,reserved=false){
 const r=reserved?(p.reservedResources??p.resources):p.resources;
 const t=reserved?(p.reservedTokens??p.tokens):p.tokens;
 return {input:t.input,output:t.output,cpu:r.cpuHours,validation:r.validatorCpuHours,hours:r.serviceHours};
}
export function aggregatePlans(plans,reserved=false){
 const rows=plans.map(p=>resourceOf(p,reserved));
 const r=Object.fromEntries(['input','output','cpu','validation','hours'].map(k=>[k,sum(rows.map(x=>x[k]))]));
 const costCents=sum(plans.map(p=>reserved?(p.reservedCostCents??p.costCents):p.costCents));
 return {costCents,tokens:{input:r.input,output:r.output},resources:{cpuHours:r.cpu,validatorCpuHours:r.validation,serviceHours:r.hours}};
}
function fits(p,j,C){const r=resourceOf(p,true);return Math.max(1,Math.ceil(r.input/C.inputQuotaWeekly),
 Math.ceil(r.output/C.outputQuotaWeekly),Math.ceil(r.cpu/C.cpuHoursWeekly),Math.ceil(r.validation/C.validatorHoursWeekly),
 Math.ceil(r.hours/C.hoursWeekly))<=j.deadline;}
function acceptedObservation(p){return p.status.code==='improved'||(p.status.code==='invalid_pass'&&p.diagnostics.selected!==null);}
const reservedPlan=p=>({...p,costCents:p.reservedCostCents??p.costCents,
 tokens:p.reservedTokens??p.tokens,resources:p.reservedResources??p.resources});
function cases(config,offers,count,available){
 const eligible=offers.filter(o=>o.scopeSupported&&o.choice==='ai');
 if(!eligible.length)return [];
 return Array.from({length:count},(_,i)=>{
  const o=eligible[Math.floor(i*eligible.length/count)%eligible.length];
  return {job:{...o,id:`fresh-probe-${i}`,scopeSupported:true},before:{...available(o.agent)},priceCents:o.priceCents};
 });
}
export function reserveAlpha(C,{keys,offers,available,count=C.alphaProbeCount}){
 const rows=cases(C,offers,count,available),plans=[];
 const missionBound=reservedPlan(planCampaignReview(C,{id:'blind-mission-holdout',valid:true,
  trials:C.alphaMissionHoldoutTrials??12},{},()=>.99));
 for(const x of rows){const after={...x.before};for(const k of keys)after[k]=true;
  plans.push(reserveJob(C,x.job,x.before),reserveJob(C,x.job,after),missionBound,missionBound);}
 const review=planCampaignReview({...C,commonError:Math.max(C.commonError,C.assetFalseAdmission)},
  {id:'reserved',valid:true,trials:96},{},()=>.99);
 plans.push(reservedPlan(review));
 const bound=aggregatePlans(plans);
 return {...bound,reservedCostCents:bound.costCents,reservedTokens:bound.tokens,reservedResources:bound.resources,
  probeCases:rows,independentMachineTrialBudget:96+rows.length*2*(C.alphaMissionHoldoutTrials??12),
  capabilityMachineTrialBudget:96,missionHoldoutTrialsPerArm:C.alphaMissionHoldoutTrials??12};
}
export function planAlpha(C,{id,keys,offers,available,count=C.alphaProbeCount,productive,lifecycleCostCents,
 forecastEligibleUses,betaVersion,week,expiryWeek,scope='optimization-prototype-v1',
 assessmentBindings={},alreadyAvailable=false},rng){
 const bound=reserveAlpha(C,{keys,offers,available,count}),rows=bound.probeCases,plans=[],paired=[],missionChecks=[];
 const review=planCampaignReview({...C,commonError:Math.max(C.commonError,C.assetFalseAdmission)},
  {id,valid:productive,trials:96},{},label=>rng(`correctness:${label}`));
 for(let i=0;i<rows.length;i++){
  const x=rows[i],after={...x.before};for(const k of keys)after[k]=true;
  const opportunity=rng(`probe:${i}:opportunity`)<C.improvableFraction;
  const wc={...C,improvementProbability:opportunity?C.improvementProbability/Math.sqrt(x.job.complexity):0};
  const candidateConfig=productive?wc:{...wc,commonError:Math.max(wc.commonError,.35)};
  const a=planJob(wc,x.job,x.before,label=>rng(`probe:${i}:${label}`));
  const b=planJob(candidateConfig,x.job,after,label=>rng(`probe:${i}:${label}`));
  plans.push(a,b);
  // A common held-out mechanical endpoint judges both outputs. Arm-specific
  // internal checks alone would reward a false pass or penalize safer refusal.
  // Mechanical truth only generates the test observation. Semantic intent is
  // not proved, and a shared faulty interpretation can blind both evaluators.
  const check=(p,arm)=>{
    if(!acceptedObservation(p))return null;
    const result=planCampaignReview(wc,{id:`${id}:evaluation:${week}:probe:${i}:${arm}`,
      valid:!p.diagnostics.selected?.mechanicalWrong,trials:C.alphaMissionHoldoutTrials??12},{},
      label=>label==='review-common-blindspot'?rng(`probe:${i}:common-specification-blindspot`):rng(`probe:${i}:common-mission-holdout:${label}`));
    plans.push(result);missionChecks.push({probe:i,arm,costCents:result.costCents,
      costDetailsCents:result.costDetailsCents,tokens:result.tokens,resources:result.resources,
      observedPass:result.status.accepted,heldOutTrials:result.diagnostics.heldOutTrials,
      semanticTruthProved:false});
    return result;
  };
  const holdoutA=check(a,'baseline'),holdoutB=check(b,'candidate');
  // The gate consumes these observations, not latent correctness or receipts.
  const feasibleA=fits(a,x.job,C),feasibleB=fits(b,x.job,C);
  const passA=Boolean(holdoutA?.status.accepted),passB=Boolean(holdoutB?.status.accepted);
  const expectedReceipt=Math.round(x.priceCents*(1-C.badDebt)*(1-C.paymentFee));
  const netA=feasibleA?(passA?expectedReceipt:0)-a.costCents-cents(135):0;
  const netB=feasibleB?(passB?expectedReceipt:0)-b.costCents-cents(135)-cents(C.alphaAccessCostPerUse):0;
  paired.push({probe:i,probeId:`${id}:beta:${betaVersion}:evaluation:${week}:fresh-probe-${i}`,fresh:true,agent:x.job.agent,classId:x.job.classId,betaVersion,baselineCapabilities:x.before,candidateCapabilities:after,
   baseline:{feasible:feasibleA,internallyObservedPass:acceptedObservation(a),observedPass:passA,
     costCents:a.costCents,holdoutCostCents:holdoutA?.costCents??0,netMissionValueCents:netA},
   candidate:{feasible:feasibleB,internallyObservedPass:acceptedObservation(b),observedPass:passB,
     costCents:b.costCents,holdoutCostCents:holdoutB?.costCents??0,netMissionValueCents:netB},
   deltaCents:netB-netA,truthNotUsedForGate:true,disjointFromOperatingJobs:true});
 }
 plans.push(review);const actual=aggregatePlans(plans),n=paired.length;
 // Caller includes the blind assessment reservation in the complete lifecycle
 // hurdle. Replace that reservation by the actual paid paired-test expense,
 // instead of counting it twice or treating the tests as free evidence.
 if(!Number.isSafeInteger(lifecycleCostCents)||lifecycleCostCents<bound.costCents)
  throw Error('planAlpha lifecycleCostCents must include the full blind assessment reservation');
 const bindings={candidateId:id,betaVersion,evaluatedAt:week,
  expiresAt:Math.min(expiryWeek,week+C.alphaEvidenceWeeks),...assessmentBindings};
 const assessment={...assessAlpha({bindings,pairedTrials:paired,
  lifecycleCostCents:lifecycleCostCents-bound.costCents,evaluationCostCents:actual.costCents,
  forecastEligibleUses,alreadyAvailable,correctnessChecksPassed:review.status.accepted,
  policy:{minimumPairedTrials:6,maximumPairedTrials:24,minimumNetCents:C.alphaMinimumNetCents??1,
   systematicRiskReserveCentsPerUse:C.alphaSystematicRiskReserveCentsPerUse??0}}),
  scope,week,expiresWeek:bindings.expiresAt,pairedProbes:n,pairedFreshMissions:paired,
  lifecycleIncludingReservedEvaluationCents:lifecycleCostCents,
  reservedEvaluationCostCents:bound.costCents,
  caveat:'The bound is conditional on the modeled observations. Shared semantic blind spots can invalidate an apparently positive result.'};
 return {...actual,reservedCostCents:bound.costCents,reservedTokens:bound.tokens,reservedResources:bound.resources,
  status:{accepted:assessment.verdict==='admit',code:assessment.verdict},assessment,review,missionChecks,
  diagnostics:{heldOutTrials:review.diagnostics.heldOutTrials,
   missionHeldOutTrials:sum(missionChecks.map(x=>x.heldOutTrials)),
   independentMachineTrialBudget:bound.independentMachineTrialBudget,
   missionHoldoutTrialsPerArm:C.alphaMissionHoldoutTrials??12,probeCount:n,
   commonEndpointForBothArms:true,truthUsedForAdmission:false,semanticTruthProved:false}};
}
