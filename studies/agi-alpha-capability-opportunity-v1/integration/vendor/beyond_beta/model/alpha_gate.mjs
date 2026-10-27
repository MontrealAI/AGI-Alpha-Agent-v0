// SPDX-License-Identifier: Apache-2.0
/**
 * Pure economic Alpha assessment over OBSERVED paired test outcomes.
 * This is modeled conditional evidence, not empirical frontier execution.
 * No latent correctness, productive-state, future-demand or identity-authority
 * field is consumed. Graph admission performs its own pin/authority checks.
 */
import {contentDigest} from '../graph/encoding.mjs';

// One-sided 95% Student-t quantiles, df 1..23. A normal 1.645 bound is too
// optimistic for the small, deliberately bounded fresh-probe budget.
const T95=[null,6.313751515,2.919985580,2.353363435,2.131846786,2.015048373,
  1.943180281,1.894578605,1.859548038,1.833112933,1.812461123,1.795884819,
  1.782287556,1.770933396,1.761310136,1.753050356,1.745883676,1.739606726,
  1.734063607,1.729132812,1.724718243,1.720742903,1.717144374,1.713871528];
export const ALPHA_GATE_POLICY=Object.freeze({
  confidenceLevel:.95,minimumPairedTrials:6,maximumPairedTrials:24,
  minimumNetCents:1,systematicRiskReserveCentsPerUse:0,
});
const BINDING_KEYS=['candidateId','candidateVersion','candidateDigest','betaVersion',
  'policyVersion','scopeDigest','environmentDigest','comparisonUniverseDigest'];
const sum=xs=>xs.reduce((s,x)=>s+x,0);
const money=x=>Number.isSafeInteger(x)&&x>=0;
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const nonempty=x=>typeof x==='string'&&x.length>0;
const net=x=>x?.netMissionValueCents??x?.netUtilityCents;

/**
 * lifecycleCostCents EXCLUDES evaluationCostCents; both are deducted once.
 * Paired row: {probeId, clusterId?, fresh:true, baseline:{netMissionValueCents},
 * candidate:{netMissionValueCents}}. If multiple observations share a mission
 * cluster, that cluster contributes one mean delta, not extra independent n.
 * Caller pays for all probes, including both arms and rejected candidates.
 */
export function assessAlpha({bindings={},pairedTrials=[],lifecycleCostCents,
  evaluationCostCents,forecastEligibleUses,alreadyAvailable=false,
  correctnessChecksPassed=false,policy={}}={}) {
  const p={...ALPHA_GATE_POLICY,...policy};
  if(p.confidenceLevel!==.95)throw Error('Alpha gate supports registered one-sided 95% t bounds only');
  if(!money(lifecycleCostCents)||!money(evaluationCostCents))throw Error('Alpha lifecycle and evaluation costs must be nonnegative integer cents');
  if(!finite(forecastEligibleUses)||forecastEligibleUses<0)throw Error('Invalid prior-data forecast of eligible uses');
  if(!Number.isInteger(p.minimumPairedTrials)||p.minimumPairedTrials<2||p.minimumPairedTrials>24||
     !Number.isInteger(p.maximumPairedTrials)||p.maximumPairedTrials>24||p.maximumPairedTrials<p.minimumPairedTrials)
    throw Error('Invalid bounded Alpha probe policy');
  if(!money(p.minimumNetCents)||!finite(p.systematicRiskReserveCentsPerUse)||p.systematicRiskReserveCentsPerUse<0)
    throw Error('Invalid Alpha value/risk threshold');
  if(!Array.isArray(pairedTrials))throw Error('Alpha evidence must be an array');
  const reasons=[],missing=BINDING_KEYS.filter(k=>!nonempty(bindings[k]));
  if(missing.length)reasons.push(`missing-bindings:${missing.join(',')}`);
  if(!Number.isSafeInteger(bindings.evaluatedAt)||bindings.evaluatedAt<0||
     !Number.isSafeInteger(bindings.expiresAt)||bindings.expiresAt<=bindings.evaluatedAt)reasons.push('invalid-evidence-time');
  const prerequisites=bindings.prerequisitePins;
  if(!Array.isArray(prerequisites)||prerequisites.some(x=>!nonempty(x?.id)||!nonempty(x?.version)||!nonempty(x?.digest)))
    reasons.push('invalid-prerequisite-pins');
  const ids=[],clusters=new Map();let allFresh=true,malformed=false;
  for(let i=0;i<pairedTrials.length;i++){
    const r=pairedTrials[i],id=String(r.probeId??r.probe??''),cluster=String(r.clusterId??id);
    const a=net(r.baseline),b=net(r.candidate);
    ids.push(id);allFresh&&=r.fresh===true||r.disjointFromOperatingJobs===true;
    if(!id||!cluster||!Number.isSafeInteger(a)||!Number.isSafeInteger(b)||!Number.isSafeInteger(b-a)){malformed=true;continue;}
    if(!clusters.has(cluster))clusters.set(cluster,[]);
    clusters.get(cluster).push(b-a);
  }
  if(new Set(ids).size!==ids.length)reasons.push('duplicate-probe-ids');
  if(malformed)reasons.push('malformed-observed-pair');
  if(!allFresh||pairedTrials.length===0)reasons.push('fresh-evidence-required');
  if(pairedTrials.length>p.maximumPairedTrials)reasons.push('probe-budget-exceeded');
  const deltas=[...clusters.values()].map(x=>sum(x)/x.length),n=deltas.length;
  if(n<p.minimumPairedTrials)reasons.push('insufficient-independent-clusters');
  // All JSON numbers remain finite. Missing evidence cannot masquerade as a
  // precise zero; its interval is null and verdict insufficient-evidence.
  const mean=n?sum(deltas)/n:null;
  const variance=n>1?sum(deltas.map(x=>(x-mean)**2))/(n-1):null;
  const se=variance===null?null:Math.sqrt(variance/n);
  const critical=n>=2&&n<=24?T95[n-1]:null;
  const lower=critical===null||se===null?null:mean-critical*se-p.systematicRiskReserveCentsPerUse;
  const projected=lower===null?-(lifecycleCostCents+evaluationCostCents):
    Math.floor(lower*forecastEligibleUses-lifecycleCostCents-evaluationCostCents);
  if(!Number.isSafeInteger(projected))throw Error('Alpha projection exceeds safe integer range');
  let verdict='insufficient-evidence';
  if(!reasons.length){
    if(alreadyAvailable)reasons.push('equivalent-capability-already-available');
    if(!correctnessChecksPassed)reasons.push('independent-checks-failed');
    if(!(lower>0))reasons.push('nonpositive-lower-per-use-advantage');
    if(projected<Math.max(1,p.minimumNetCents))reasons.push('nonpositive-or-insufficient-complete-net-alpha');
    verdict=reasons.length?'reject':'admit';
  }
  const report={schema:'modeled-alpha-assessment/v2',evidenceCategory:'Assumed or explored',
    ...Object.fromEntries(BINDING_KEYS.map(k=>[k,bindings[k]??''])),
    evaluatedAt:bindings.evaluatedAt??-1,expiresAt:bindings.expiresAt??-1,
    prerequisitePins:Array.isArray(prerequisites)?prerequisites:[],
    verdict,reasons,pairedTrials:pairedTrials.length,independentClusters:n,
    freshTests:allFresh&&pairedTrials.length>0,alreadyAvailable:Boolean(alreadyAvailable),
    probeIdsDigest:contentDigest(ids,'beyond-beta-alpha-probe-ids'),
    observedPairsDigest:contentDigest(pairedTrials.map((r,i)=>({probeId:ids[i],clusterId:String(r.clusterId??ids[i]),
      baselineNetMissionValueCents:net(r.baseline)??null,candidateNetMissionValueCents:net(r.candidate)??null,
      fresh:r.fresh===true||r.disjointFromOperatingJobs===true})),'beyond-beta-alpha-observed-pairs'),
    assessedLowerBoundNetCents:projected,lifecycleCostCents,evaluationCostCents,
    completeLifecycleCostCents:lifecycleCostCents+evaluationCostCents,
    forecastEligibleUses,correctnessChecksPassed:Boolean(correctnessChecksPassed),
    meanDeltaCents:mean,standardErrorCents:se,lowerDeltaCents:lower,
    lowerLifetimeNetCents:projected,confidenceLevel:.95,criticalValue:critical,
    systematicRiskReserveCentsPerUse:p.systematicRiskReserveCentsPerUse,
    method:'One-sided 95% Student-t lower bound over independent paired mission-cluster mean deltas, conditional on modeled observations',
    empiricalOperationalValidation:false,truthUsedForAdmission:false,
    limitations:['A small-sample t interval is an approximation for the modeled delta distribution, not a distribution-free guarantee.',
      'The interval does not bound systematic semantic errors shared by producers and evaluators.',
      'Forecast uses, modeled resource effects, quality and test coverage remain assumptions; actual evaluation expense is charged in both arms.',
      'This report carries no identity, admission, retrieval, composition or execution authority.']};
  return report;
}
