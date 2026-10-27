// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {reserveAlpha,planAlpha,resourceOf} from './alpha_probe.mjs';
const C={initialError:0,commonError:0,assetFalseAdmission:0,improvementProbability:1,
 improvableFraction:1,cheapScreenFalsePositive:0,maxRetries:0,candidatesPerJob:2,
 inputQuotaWeekly:1e9,outputQuotaWeekly:1e9,cpuHoursWeekly:1e9,validatorHoursWeekly:1e9,
 hoursWeekly:168,badDebt:0,paymentFee:0,alphaAccessCostPerUse:0,
 alphaProbeCount:6,alphaEvidenceWeeks:13,alphaMinimumNetCents:1};
const offers=[{id:'past-only',agent:0,classId:'coupled',complexity:2.4,scopeSupported:true,
 choice:'ai',deadline:20,priceCents:1000000}];
const available=()=>({representation:false,certificate:false,experiment:false});
const keys=['representation','certificate'];
const bindings={candidateVersion:'1',candidateDigest:'candidate',policyVersion:'policy',
 scopeDigest:'scope',environmentDigest:'environment',comparisonUniverseDigest:'inventory',prerequisitePins:[]};
const bound=reserveAlpha(C,{keys,offers,available});
const input={id:'synthetic-alpha',keys,offers,available,productive:true,
 lifecycleCostCents:bound.costCents+100,forecastEligibleUses:1000,
 betaVersion:'synthetic-beta',week:0,expiryWeek:65,assessmentBindings:bindings};
const result=planAlpha(C,input,()=>.5);
assert.equal(result.status.accepted,true);
assert.equal(result.assessment.lifecycleCostCents,100);
assert.equal(result.assessment.evaluationCostCents,result.costCents);
assert.equal(result.assessment.completeLifecycleCostCents,100+result.costCents);
assert.ok(result.costCents<=result.reservedCostCents);
for(const [k,v]of Object.entries(resourceOf(result,false)))assert.ok(v<=resourceOf(result,true)[k]+1e-8,`Alpha reservation ${k}`);
const nullKeys=[],nullBound=reserveAlpha(C,{keys:nullKeys,offers,available});
const nullResult=planAlpha(C,{...input,keys:nullKeys,lifecycleCostCents:nullBound.costCents+100},()=>.5);
assert.equal(nullResult.status.accepted,false,'full paired evaluation cost and a zero effect reject');
assert.equal(planAlpha(C,{...input,assessmentBindings:{}},()=>.5).assessment.verdict,'insufficient-evidence');
assert.throws(()=>planAlpha(C,{...input,lifecycleCostCents:bound.costCents-1},()=>.5),/blind assessment reservation/);
// A common external check does not reward baseline's own mechanical false pass.
const mechanical={...C,initialError:.5,semanticErrorFraction:0,mechanicalDetection:.2,
 certificateMechanicalDetection:.9,baselineScreenSensitivity:0,familyScreenIncrement:0,
 reviewCaseCoverage:1,reviewDetection:1,alphaMissionHoldoutTrials:6};
const mechanicalKeys=['certificate'],mechanicalBound=reserveAlpha(mechanical,{keys:mechanicalKeys,offers,available});
const checkRng=label=>label.endsWith('candidate-0-mechanical')?.1:label.endsWith('-mechanical')?.9:.5;
const safer=planAlpha(mechanical,{...input,keys:mechanicalKeys,
 lifecycleCostCents:mechanicalBound.costCents+100},checkRng);
assert.equal(safer.assessment.pairedFreshMissions[0].baseline.internallyObservedPass,true);
assert.equal(safer.assessment.pairedFreshMissions[0].baseline.observedPass,false);
assert.equal(safer.assessment.pairedFreshMissions[0].candidate.observedPass,true);
assert.equal(safer.status.accepted,true);
assert.ok(safer.missionChecks.length>0);assert.ok(safer.costCents<=safer.reservedCostCents);
// Separate revalidations cannot reuse a misleadingly identical probe-ID digest.
const later=planAlpha(C,{...input,week:1},()=>.5);
assert.notEqual(later.assessment.probeIdsDigest,result.assessment.probeIdsDigest);
console.log('Alpha probe integration controls passed: actual evaluation billing, conservative reservation and exact-null rejection.');
