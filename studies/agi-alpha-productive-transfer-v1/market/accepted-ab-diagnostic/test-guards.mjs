// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {inspectAcceptedAB,conditionalAB} from './accepted-ab.mjs';
import {inspectProduction} from '../transfer-adapter.mjs';

const read=name=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const production=read('./production-accepted-ab.json'),copy=x=>structuredClone(x);
const control={id:'synthetic-guard-not-registered-outcome',basis:'EXPLICIT_CONDITIONAL_ASSUMPTIONS',
 class:'exploratory-accepted-ab-no-benefit',financing:'operating-surplus',
 shared:{weeks:12,buyers:4,arrivalProbability:1,supportedFraction:1,initialCashCents:100000,
  reserveCents:20000,initialSetupCents:0,weeklyOverheadCents:0,customerReviewMinutes:0,integrationCents:0,
  switchingCents:0,initialTrust:1,skepticalShare:0,humanQuality:0.5,diyQuality:0.5,aiQuality:0.5,
  successProbability:1,overloadPenalty:0,pricingPolicy:'fixed',initialPriceCents:2000,
  providerMinutesPerWeek:1000,investmentEarliestWeek:2,paymentDelayWeeks:0,paymentProbability:1,
  usefulnessMultiplier:10,competitorStrategy:'fixed',humanSlotsPerWeek:0,aiSlotsPerWeek:0},
 costs:{A:{completeRecurringCostCents:500,completeConstructionCostCents:0,maintenancePerWeekCents:0,assumedIntakeMinutes:0},
  B:{completeRecurringCostCents:500,completeConstructionCostCents:10000,maintenancePerWeekCents:50,assumedIntakeMinutes:0}}};

test('actual A/B all-four acceptance is distinct from held three-arm campaign',()=>{
 const a=inspectAcceptedAB(production);assert.equal(a.status,'COMPLETE_AB_ACCEPTED_WORK');
 assert.equal(a.economicDecision,'IDENTIFICATION_HOLD');assert.equal(a.unknownMonetaryComponents.length,4);
 assert.notEqual(inspectProduction(read('../production-followup.json')).status,'COMPLETE_EQUIVALENT_ACCEPTED_WORK');
});
test('different schema, narrowed mission set and C2 cannot enter A/B diagnostic',()=>{
 assert.throws(()=>inspectAcceptedAB(read('../production-followup.json')));
 const p=copy(production);p.missions=p.missions.filter(x=>x!=='F03');assert.throws(()=>inspectAcceptedAB(p));
 const q=copy(production);q.arms.C=q.arms.B;assert.throws(()=>inspectAcceptedAB(q));
});
test('audit failure or scope-only acceptance cannot be projected as complete',()=>{
 const p=copy(production);p.independentAcceptance.rows[0].completeHandoffAccepted=false;
 assert.throws(()=>inspectAcceptedAB(p));
 const q=copy(production);q.independentAcceptance.scope='inventory-only';assert.throws(()=>inspectAcceptedAB(q));
});
test('unknown dollars are explicit and exact tested B asset cannot be swapped',()=>{
 const p=copy(production);delete p.arms.B.completeRecurringCostCents;assert.throws(()=>inspectAcceptedAB(p));
 const q=copy(production);q.arms.B.asset.sha256='f'.repeat(64);assert.throws(()=>inspectAcceptedAB(q));
});
test('synthetic guard refuses unequal cost, effort premium, free activation and seed funding',()=>{
 for(const mutate of [s=>s.costs.B.completeRecurringCostCents=1,s=>s.costs.A.assumedIntakeMinutes=1,
  s=>s.shared.assetResidualMinutes=1,s=>s.financing='seed-funded']){
  const s=copy(control);mutate(s);assert.throws(()=>conditionalAB(production,s,10421));
 }
});
test('synthetic profitable market still refuses zero-saving B and preserves exact decision identity',()=>{
 const p=conditionalAB(production,control,10421);
 assert.ok(p.arms.A.summary.enterpriseAccepted>0);assert.ok(p.arms.B.histories.investmentDecisions.length>0);
 assert.equal(p.arms.B.histories.investments.length,0);assert.deepEqual(p.arms.A.summary,p.arms.B.summary);
 assert.equal(p.differences.B_minus_A_profitCents,0);
 for(const d of p.arms.B.histories.investmentDecisions){
  assert.equal(d.asset.sha256,production.acceptedAsset.sha256);
  assert.equal(d.expectedIncrementalSavingPerUseCents,0);assert.equal(d.action,'retain-incumbent');
 }
});
test('synthetic delayed-cash and failure controls never earn rejection revenue or force construction',()=>{
 const s=copy(control);s.shared.successProbability=0;s.shared.paymentDelayWeeks=20;
 const p=conditionalAB(production,s,10422);
 for(const arm of ['A','B']){
  const r=p.arms[arm];assert.equal(r.histories.investments.length,0);
  const rejected=r.histories.jobs.filter(j=>j.provider==='enterprise'&&!j.accepted);
  assert.ok(rejected.length);assert.ok(rejected.every(j=>!j.invoiceCreated&&j.deliveryCostCents>0));
  assert.ok(r.histories.cash.every(e=>e.cashAfterCents>=0));
 }
});
test('stage resource measurements never create a B capacity premium',()=>{
 const p=copy(production);p.arms.B.resources.wallSecondsPerAccepted=0.00001;
 const result=conditionalAB(p,control,10423);
 assert.equal(result.arms.B.config.activeMechanicalWallSeconds,result.arms.A.config.measuredMechanicalWallSeconds);
 assert.equal(result.arms.B.config.assetResidualMinutes,result.arms.A.config.ordinaryFinalizationMinutes);
});
