// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {simulate as original} from './inherited/market/src/market.mjs';
import {simulate as adapted} from './market-transfer-core.mjs';
import {inspectProduction,identificationDecision,conditionalPair,repaymentThreshold} from './transfer-adapter.mjs';

const fixture={schema:'agi-alpha-intake-transfer-production/v1',missions:['synthetic-control'],evidenceSHA256:'e'.repeat(64),
 completeAcceptanceEvidence:{status:'PASS',scope:'complete-useful-deliverable',independentlyVerified:true,
  receiptSHA256:'a'.repeat(64),verifierSHA256:'d'.repeat(64)},
 arms:Object.fromEntries(['A','B','C'].map(a=>[a,{attemptedMissionIds:['synthetic-control'],acceptedMissionIds:['synthetic-control'],
  completeRecurringCostCents:null,completeConstructionCostCents:null,
  resources:{scope:'known-process-lower-bound',cpuSecondsPerAccepted:1,wallSecondsPerAccepted:2},
  asset:a==='A'?null:{id:`synthetic-control-${a}`,path:`synthetic-${a}.json`,sha256:a==='B'?'b'.repeat(64):'c'.repeat(64)}}]))};
const clone=x=>structuredClone(x);
const control={weeks:12,buyers:4,arrivalProbability:1,supportedFraction:1,initialCashCents:100000,
 reserveCents:0,initialSetupCents:0,weeklyOverheadCents:0,customerReviewMinutes:0,integrationCents:0,
 switchingCents:0,initialTrust:1,skepticalShare:0,humanQuality:0.5,diyQuality:0.5,aiQuality:0.5,
 successProbability:1,overloadPenalty:0,pricingPolicy:'fixed',initialPriceCents:2000,
 providerMinutesPerWeek:1000,investmentEarliestWeek:2,assetMaintenanceCentsPerWeek:0,
 paymentDelayWeeks:0,paymentProbability:1,usefulnessMultiplier:10,competitorStrategy:'fixed',humanSlotsPerWeek:0,aiSlotsPerWeek:0};
const caseFor=(saving=false)=>({id:'synthetic-control-not-production',basis:'EXPLICIT_CONDITIONAL_ASSUMPTIONS',
 class:'primary-no-unmeasured-benefit',financing:'operating-surplus',shared:control,
 costs:Object.fromEntries(['A','B','C'].map(a=>[a,{completeRecurringCostCents:a==='A'?1000:saving?100:1000,
  completeConstructionCostCents:a==='A'?0:500,maintenancePerWeekCents:0,assumedIntakeMinutes:0}]))});

test('versioned core preserves original economics under historical default inputs',()=>{
 for(const c of [{},{...control},{...control,paymentDelayWeeks:10},{...control,successProbability:0},{...control,initialCashCents:10}])
  for(const a of ['A','B','C']){
   const before=original(c,422,a),after=adapted(c,422,a);
   assert.deepEqual(after.summary,before.summary);assert.deepEqual(after.histories,before.histories);
  }
});
test('unknown total costs cause identification HOLD, never zero imputation',()=>{
 const d=identificationDecision(fixture);assert.equal(d.economicDecision,'IDENTIFICATION_HOLD');assert.equal(d.unknownMonetaryComponents.length,6);
 const bad=clone(fixture);delete bad.arms.B.completeRecurringCostCents;assert.throws(()=>inspectProduction(bad));
});
test('repeated assertions cannot become independent jobs',()=>{
 const bad=clone(fixture);bad.missions.push('synthetic-control');assert.throws(()=>inspectProduction(bad));
});
test('incomplete baseline is an explicit equivalence hold',()=>{
 const bad=clone(fixture);bad.arms.A.acceptedMissionIds=[];
 assert.equal(identificationDecision(bad).economicDecision,'HOLD_INCOMPLETE_EQUIVALENCE');
 assert.throws(()=>conditionalPair(bad,caseFor(),422));
});
test('zero measured economic change with positive construction cost does not justify investment',()=>{
 const p=conditionalPair(fixture,caseFor(),422);for(const a of ['A','B','C'])assert.equal(p.arms[a].histories.investments.length,0);
 assert.equal(p.differences.B_minus_A_profitCents,0);assert.equal(p.differences.B_minus_C_profitCents,0);
});
test('synthetic positive savings finance exact stated asset after collections, not before',()=>{
 const p=conditionalPair(fixture,caseFor(true),422);
 assert.ok(p.arms.B.histories.investments.length>0);
 for(const a of ['B','C']){
  assert.equal(p.arms[a].histories.investments[0].asset.sha256,fixture.arms[a].asset.sha256);
  for(const j of p.arms[a].histories.jobs.filter(j=>j.assetUsed))assert.equal(j.sourceAssetSHA256,fixture.arms[a].asset.sha256);
 }
 assert.equal(p.differences.B_minus_C_profitCents,0);
});
test('seed capital and uncollected invoices do not finance earned-only construction',()=>{
 const c=caseFor(true);c.shared={...control,paymentDelayWeeks:20};
 const p=conditionalPair(fixture,c,422);assert.equal(p.arms.B.histories.investments.length,0);
});
test('unaffordable complete reconstruction remains refused',()=>{
 const c=caseFor(true);c.costs.B.completeConstructionCostCents=100000000;
 const p=conditionalPair(fixture,c,422);assert.equal(p.arms.B.histories.investments.length,0);
});
test('primary cannot assert unmeasured curator labor savings',()=>{
 const c=caseFor();c.costs.A.assumedIntakeMinutes=2;assert.throws(()=>conditionalPair(fixture,c,422));
});
test('stage timing cannot create workflow-capacity enhancement',()=>{
 const x=clone(fixture);x.arms.B.resources.cpuSecondsPerAccepted=0.0001;
 const p=conditionalPair(x,caseFor(true),422);assert.equal(p.arms.B.config.activeMechanicalCpuSeconds,p.arms.A.config.measuredMechanicalCpuSeconds);
});
test('rejected synthetic deliverables retain costs and never gain invoices',()=>{
 const c=caseFor(true);c.shared={...control,successProbability:0};const p=conditionalPair(fixture,c,422);
 const rejected=p.arms.A.histories.jobs.filter(x=>x.provider==='enterprise'&&!x.accepted);
 assert.ok(rejected.length);assert.ok(rejected.every(x=>!x.invoiceCreated&&x.deliveryCostCents>0));
});
test('equivalent-work threshold does not claim market financing',()=>{
 assert.equal(repaymentThreshold({incrementalCostPerAcceptedCents:0,investmentCostCents:100}).acceptedJobsRequired,null);
 assert.equal(repaymentThreshold({incrementalCostPerAcceptedCents:10,investmentCostCents:100,maintenanceCents:5}).acceptedJobsRequired,11);
});
test('conditional zero-model treatment requires executed stage evidence',()=>{
 const c=caseFor(true);c.class='conditional-model-cost-sensitivity';
 assert.throws(()=>conditionalPair(fixture,c,422));
 const p=clone(fixture);p.executedStepDistinction={A:'MODEL_OR_CURATOR',B:'MODEL_EXTRACTION',C:'NO_RUNTIME_MODEL',
  independentAcceptedScopeEquivalent:true,evidenceSHA256:'d'.repeat(64)};
 const result=conditionalPair(p,c,422);assert.equal(result.observedCustomerCollectionsCents,0);
});
test('conditional comparison cannot quietly narrow to a favorable common subset',()=>{
 const p=clone(fixture);p.missions.push('unaccepted-synthetic-control');
 p.executedStepDistinction={A:'MODEL_OR_CURATOR',B:'MODEL_EXTRACTION',C:'NO_RUNTIME_MODEL',
  independentAcceptedScopeEquivalent:true,evidenceSHA256:'d'.repeat(64)};
 const c=caseFor(true);c.class='conditional-model-cost-sensitivity';
 assert.throws(()=>conditionalPair(p,c,422),/entire registered set/);
});
test('scope-only diagnostics cannot be represented as useful complete acceptance',()=>{
 const p=clone(fixture);p.completeAcceptanceEvidence.scope='call-inventory-only';
 assert.equal(identificationDecision(p).economicDecision,'HOLD_INCOMPLETE_EQUIVALENCE');
 assert.throws(()=>conditionalPair(p,caseFor(),422));
});
test('unverified or failed complete packages remain held even when IDs match',()=>{
 for(const status of ['FAIL','PENDING']){
  const p=clone(fixture);p.completeAcceptanceEvidence.status=status;
  assert.equal(inspectProduction(p).status,'COMPLETE_DELIVERABLE_ACCEPTANCE_NOT_VERIFIED');
  assert.throws(()=>conditionalPair(p,caseFor(),422));
 }
});
