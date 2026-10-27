// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {planJob,reserveJob,planCampaignReview,planAuxiliary,planConstruction,paidJobCostComponents,DEFAULT_WORKFLOW_CONFIG,AUXILIARY_BUDGETS} from './workflow.mjs';

const good={initialError:0,commonError:0,improvementProbability:1,cheapScreenFalsePositive:0};
const job={id:'synthetic-control',complexity:2.4,scopeSupported:true};
const rng=()=>0.5;
const base=planJob(good,job,{},rng);
assert.equal(base.status.code,'improved');
assert.equal(base.status.retries,0);
assert.equal(base.accounting.reasoningIncludedInOutput,true);
assert.equal(base.costCents,Object.values(base.costDetailsCents).reduce((a,b)=>a+b,0));
assert.equal(base.tokens.input,base.tokens.uncachedInput+base.tokens.cachedInput+base.tokens.cacheWrite);
assert.ok(Number.isInteger(base.costCents));
assert.ok(!JSON.stringify(base).toLowerCase().includes('human'));
const paidComponents=paidJobCostComponents(base);
assert.equal(paidComponents.totalCents,base.costCents);assert.equal(paidComponents.unclassifiedCents,0);
assert.equal(paidComponents.additionalChargeCents,0);
assert.ok(paidComponents.componentsCents.candidateConstructionAndLearning>0);
assert.equal(paidComponents.reusableAlphaGuaranteed,false);

const singles=planJob(good,job,{representation:1},rng);
const bundle=planJob(good,job,{representation:1,certificate:1},rng);
assert.equal(singles.costCents,base.costCents,'competent Beta ignores an unhelpful isolated component');
assert.ok(bundle.resources.cpuHours<base.resources.cpuHours);
assert.deepEqual(bundle.status,base.status,'resource bundle has no intrinsic quality bonus');
const zero=planJob({...good,bundleResourceEffect:0},job,{representation:1,certificate:1},rng);
assert.equal(zero.costCents,base.costCents,'zero resource effect is a real null');
for(const complexity of [1,2.4,4]){
  const j={...job,complexity};
  const a=planJob({...DEFAULT_WORKFLOW_CONFIG,...good,bundleEffect:1},j,{representation:1,certificate:1},rng);
  const b=planJob(good,j,{},rng);
  assert.equal(a.costCents,b.costCents,'study bundleEffect alias has a genuine null');
}

const blind=planJob({...good,commonError:1},job,{},rng);
assert.equal(blind.status.code,'invalid_pass');
assert.equal(blind.status.abstained,false,'no clairvoyant abstention on undetected interpretation failure');
assert.equal(blind.diagnostics.undetectedMaterialError,true);
assert.equal(blind.costDetailsCents.recovery,undefined,'unknown error does not trigger clairvoyant recovery');

const noGain=planJob({...good,improvementProbability:0},job,{},rng);
assert.equal(noGain.status.code,'no_improvement');
assert.equal(noGain.status.feasible,true,'known solver is retained');
assert.equal(noGain.status.retries,2);

const bad={...good,initialError:1,mechanicalDetection:1,correctionSuccess:0,improvementProbability:0,baselineScreenSensitivity:0.65,familyScreenIncrement:0.15};
const badRng=k=>k==='initial-semantic-error'?0.9:k.endsWith('-cheap-screen')?0.7:0.5;
const unscreened=planJob(bad,job,{},badRng);
const screened=planJob(bad,job,{experiment:1},badRng);
assert.ok(screened.resources.cpuHours<unscreened.resources.cpuHours,'CPU savings arise from actual detected invalid candidates');
assert.ok(screened.diagnostics.screenedInvalid>0);
const screenNull=planJob({...bad,familyScreenIncrement:0},job,{experiment:1},badRng);
assert.equal(screenNull.costCents,unscreened.costCents,'zero family-specific information is an exact resource null');
assert.deepEqual(screenNull.status,unscreened.status);
const absorbedScreenConfig={...bad,betaBundleAbsorption:0,betaExperimentAbsorption:1};
assert.equal(planJob(absorbedScreenConfig,job,{experiment:1},badRng).costCents,
 planJob(absorbedScreenConfig,job,{},badRng).costCents,'screen absorption has its own Beta path');
const retainedScreenConfig={...bad,betaBundleAbsorption:1,betaExperimentAbsorption:0};
assert.ok(planJob(retainedScreenConfig,job,{experiment:1},badRng).costCents<
 planJob(retainedScreenConfig,job,{},badRng).costCents,'bundle absorption need not erase family screen');
const allGoodWithScreen=planJob(good,job,{experiment:1},rng);
assert.equal(allGoodWithScreen.resources.cpuHours,base.resources.cpuHours,'no flat screen saving on valid candidates');

const scope=planJob(good,{...job,scopeSupported:false},{},rng);
assert.equal(scope.status.code,'out_of_scope');
assert.equal(scope.diagnostics.candidates,0);

for(const complexity of [1,2.4,4])for(const config of [good,bad,{...good,commonError:1},{...good,tokenMultiplier:2.3,computeMultiplier:3,workflowLatencyMultiplier:2}])for(const assets of [{},{representation:1},{representation:1,certificate:1},{experiment:1}]){
  const j={...job,complexity};const actual=planJob(config,j,assets,rng);const reserved=reserveJob(config,j,assets);
  assert.ok(actual.costCents<=reserved.costCents);
  for(const k of ['serviceHours','cpuHours','searchCpuHours','validatorCpuHours'])assert.ok(actual.resources[k]<=reserved.resources[k]+1e-8,`reservation ${k}`);
  for(const k of Object.keys(actual.tokens))assert.ok(actual.tokens[k]<=reserved.tokens[k]);
}

const rejected=planCampaignReview({commonError:0,reviewCaseCoverage:1,reviewDetection:1},{id:'independent-invalid',valid:false},{},rng);
assert.equal(rejected.status.rejected,true);assert.equal(rejected.diagnostics.heldOutTrials,1);
const passed=planCampaignReview({commonError:0},{id:'independent-valid',valid:true},{},rng);
assert.equal(passed.diagnostics.heldOutTrials,96);assert.equal(passed.status.accepted,true);
assert.ok(rejected.costCents<passed.costCents);
assert.ok(passed.costCents<=passed.reservedCostCents);
const quote=planAuxiliary({},'quote_intake');
assert.equal(quote.tokens.input,25000);assert.equal(quote.tokens.output,4000);
const expensiveQuote=planAuxiliary({tokenMultiplier:10},'quote_intake');
assert.equal(expensiveQuote.tokens.input,250000);
assert.ok(expensiveQuote.costCents>quote.costCents);
for(const kind of Object.keys(AUXILIARY_BUDGETS)){
  const aux=planAuxiliary({},kind,{scale:2.4});
  assert.equal(aux.costCents,Object.values(aux.costDetailsCents).reduce((a,b)=>a+b,0));
  assert.equal(aux.reservedCostCents,aux.costCents);
  assert.equal(aux.diagnostics.claimsValidationResult,false);
  assert.ok(aux.resources.serviceHours>0);
}
const construction=planConstruction({cpuPricePerHour:0.0493704},{workUnits:3600,keys:['representation']});
assert.equal(construction.tokens.input,18_000_000);assert.equal(construction.tokens.output,3_240_000);
assert.equal(construction.resources.cpuHours,4320);
assert.equal(construction.costCents,Object.values(construction.costDetailsCents).reduce((a,b)=>a+b,0));
assert.equal(construction.diagnostics.unallocatedResidualCents,0);
assert.equal(construction.diagnostics.finalIndependentReviewIncluded,false);
const scaled=planConstruction({assetConstructionMultiplier:2,tokenMultiplier:3,computeMultiplier:4},{workUnits:3600});
assert.equal(scaled.tokens.input,construction.tokens.input*6);
assert.equal(scaled.resources.cpuHours,construction.resources.cpuHours*8);
assert.equal(scaled.tokens.input,scaled.tokens.uncachedInput+scaled.tokens.cachedInput+scaled.tokens.cacheWrite);
for(const complexity of [1,2.4,4]){
  const j={...job,complexity},c={...good,betaBundleAbsorption:1};
  const beta=planJob(c,j,{},rng),absorbed=planJob(c,j,{representation:1,certificate:1,experiment:1},rng);
  assert.equal(beta.costCents,absorbed.costCents,'full Beta absorption removes incremental resource gain');
  assert.deepEqual(beta.status,absorbed.status);
}
const upgraded=planConstruction({betaResourceFactor:0.5,cpuPricePerHour:0.0493704},{workUnits:3600});
assert.equal(upgraded.tokens.input,construction.tokens.input/2);
assert.equal(upgraded.resources.searchCpuHours,construction.resources.searchCpuHours/2);
assert.equal(upgraded.resources.validatorCpuHours,construction.resources.validatorCpuHours);
console.log('workflow controls passed: accounting, resource-only bundle, blind failure, bounded retry, genuine screening, scope, reservation, held-out review');
