// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {assessAlpha} from './alpha_gate.mjs';
const bindings={candidateId:'c',candidateVersion:'1',candidateDigest:'candidate',
 betaVersion:'beta-v1',policyVersion:'policy-v1',scopeDigest:'scope',environmentDigest:'environment',
 comparisonUniverseDigest:'inventory',evaluatedAt:0,expiresAt:13,prerequisitePins:[]};
const rows=(difference=1000,n=24)=>Array.from({length:n},(_,i)=>({probeId:`p${i}`,fresh:true,
 baseline:{netMissionValueCents:100},candidate:{netMissionValueCents:100+difference}}));
const input={bindings,pairedTrials:rows(),lifecycleCostCents:1000,evaluationCostCents:2000,
 forecastEligibleUses:10,correctnessChecksPassed:true};
const positive=assessAlpha(input);
assert.equal(positive.verdict,'admit');assert.equal(positive.assessedLowerBoundNetCents,7000);
assert.equal(positive.completeLifecycleCostCents,3000);assert.equal(positive.pairedTrials,24);
assert.equal(positive.independentClusters,24);assert.ok(positive.criticalValue>1.645);
// Exact null, even free construction/evaluation, is not Alpha.
assert.equal(assessAlpha({...input,pairedTrials:rows(0),lifecycleCostCents:0,evaluationCostCents:0}).verdict,'reject');
assert.equal(assessAlpha({...input,alreadyAvailable:true}).verdict,'reject');
assert.equal(assessAlpha({...input,correctnessChecksPassed:false}).verdict,'reject');
assert.equal(assessAlpha({...input,evaluationCostCents:20000}).verdict,'reject');
// Replicated recipients of one held-out mission do not create 24 independent tests.
assert.equal(assessAlpha({...input,pairedTrials:rows().map(x=>({...x,clusterId:'one-mission'}))}).verdict,'insufficient-evidence');
assert.equal(assessAlpha({...input,pairedTrials:rows(1000,25)}).verdict,'insufficient-evidence');
assert.equal(assessAlpha({...input,pairedTrials:rows().map(x=>({...x,fresh:false}))}).verdict,'insufficient-evidence');
assert.equal(assessAlpha({...input,bindings:{...bindings,comparisonUniverseDigest:''}}).verdict,'insufficient-evidence');
assert.equal(assessAlpha({...input,bindings:{...bindings,expiresAt:0}}).verdict,'insufficient-evidence');
// Large spread can fail the paired bound despite a positive raw mean.
const noisy=rows().map((r,i)=>({...r,candidate:{netMissionValueCents:i===0?100000:100}}));
assert.equal(assessAlpha({...input,pairedTrials:noisy}).verdict,'reject');
// Latent truth fields cannot alter observed-evidence decisions or report digests.
const poisoned=rows().map(r=>({...r,actualProductive:false,latentCorrectness:false,
 futureDemand:1e9,candidate:{...r.candidate,actualCorrect:false}}));
assert.deepEqual(assessAlpha({...input,pairedTrials:poisoned}),positive);
// Shared semantic bias can therefore yield an apparently positive modeled gate.
assert.equal(assessAlpha({...input,pairedTrials:poisoned}).verdict,'admit');
// Exact observed evidence is bound; changing a single measured delta changes it.
assert.notEqual(assessAlpha({...input,pairedTrials:rows(999)}).observedPairsDigest,positive.observedPairsDigest);
assert.throws(()=>assessAlpha({...input,evaluationCostCents:2.5}),/integer cents/);
assert.throws(()=>assessAlpha({...input,policy:{confidenceLevel:.9}}),/95%/);
console.log('Alpha gate controls passed: exact null, full costs, bindings, dependence and no latent-truth lookahead.');
