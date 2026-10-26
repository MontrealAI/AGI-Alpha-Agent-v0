// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {simulate,pairedSimulation,chooseBuyer,pruneDominated,randomDraw,defaultConfig} from '../src/market.mjs';

const control={weeks:12,buyers:4,arrivalProbability:1,supportedFraction:1,initialCashCents:100000,
  reserveCents:0,initialSetupCents:0,weeklyOverheadCents:0,customerReviewMinutes:0,integrationCents:0,
  switchingCents:0,initialTrust:1,skepticalShare:0,humanQuality:0.5,diyQuality:0.5,aiQuality:0.5,
  successProbability:1,overloadPenalty:0,pricingPolicy:'fixed',initialPriceCents:2000,
  commonResidualMinutes:0,ordinaryFinalizationMinutes:10,providerMinutesPerWeek:1000,
  investmentEarliestWeek:2,constructionHours:0,authoringCostCents:0,adoptionHours:0.01,
  assetMaintenanceCentsPerWeek:0,paymentDelayWeeks:0,paymentProbability:1,
  usefulnessMultiplier:10,competitorStrategy:'fixed',humanSlotsPerWeek:0,aiSlotsPerWeek:0};

test('strictly dominated offers cannot survive either buyer model',()=>{
  const good={id:'diy',quality:1,priceCents:0,effortCents:0,delayCents:0,switchCents:0};
  const bad={...good,id:'enterprise',quality:0.9,priceCents:100};
  assert.deepEqual(pruneDominated([good,bad]).map(x=>x.id),['diy']);
  for(const model of ['deterministic','logit'])for(let i=0;i<100;i++){
    const x=chooseBuyer([good,bad],{valueCents:10000,errorLossCents:1000},{...defaultConfig,choiceModel:model},i/100);
    assert.notEqual(x.choice,'enterprise');
  }
});
test('negative utility always defers',()=>{
  const o={id:'enterprise',quality:0,priceCents:100,effortCents:100,delayCents:100,switchCents:100};
  for(const model of ['deterministic','logit'])assert.equal(chooseBuyer([o],{valueCents:0,errorLossCents:100},
    {...defaultConfig,choiceModel:model},0.5).choice,'defer');
});
test('zero demand makes zero invoices, collections, and investments',()=>{
  const r=simulate({...control,arrivalProbability:0},19,'B');
  assert.equal(r.summary.enterpriseAttempts,0);assert.equal(r.summary.grossCollectionsCents,0);
  assert.equal(r.histories.investments.length,0);assert.equal(r.observedCustomerCollectionsCents,0);
});
test('identically enabled B and C tie exactly under semantic common draws',()=>{
  const p=pairedSimulation(control,19);
  assert.deepEqual(p.arms.B.summary,p.arms.C.summary);assert.equal(p.causal.B_minus_C_profitCents,0);
  assert.ok(p.arms.B.histories.investments.length>0);
});
test('seed cash does not count as earned surplus',()=>{
  const r=simulate({...control,paymentDelayWeeks:20,weeks:10},19,'B');
  assert.equal(r.histories.investments.length,0);
});
test('zero cost saving never justifies investment',()=>{
  const r=simulate({...control,ordinaryFinalizationMinutes:0},19,'B');
  assert.equal(r.histories.investments.length,0);
});
test('free perfect zero-effort DIY wins against nonfree offerings',()=>{
  const r=simulate({...control,diyQuality:1,diyEffortFraction:0,diyDays:0},19,'B');
  assert.equal(r.summary.enterpriseAttempts,0);
});
test('zero-delay collection occurs in delivery week',()=>{
  const r=simulate(control,19,'A');assert.ok(r.histories.invoices.length>0);
  assert.ok(r.histories.invoices.every(x=>x.collectedWeek===x.week));
});
test('mechanical budget prevents unsupported throughput',()=>{
  const r=simulate({...control,machineWallSecondsPerWeek:0},19,'A');
  assert.equal(r.summary.enterpriseAttempts,0);
});
test('rejected work creates no invoice and consumes charged costs',()=>{
  const r=simulate({...control,successProbability:0},19,'A');
  const rejected=r.histories.jobs.filter(x=>x.provider==='enterprise'&&!x.accepted);
  assert.ok(rejected.length>0);assert.ok(rejected.every(x=>!x.invoiceCreated&&x.deliveryCostCents>0));
});
test('cash and accrual state reconciles to canonical projections',()=>{
  const r=simulate({...control,paymentDelayWeeks:4,expenseDelayWeeks:2,paymentProbability:0.7,successProbability:0.8},19,'B');
  assert.equal(r.canonical.cash.summary.observed.revenue,0);
  assert.equal(r.summary.finalCashCents,r.config.initialCashCents+r.histories.cash.reduce((n,x)=>n+x.amountCents,0));
  assert.equal(r.summary.accruedCostsCents-r.summary.paidCostsCents,r.summary.obligationsCents);
  assert.ok(r.histories.balances.every(x=>x.cashCents>=0));
});
test('keyed draws remain stable regardless of call order',()=>{
  const x=randomDraw(123,'quality',7,2,'enterprise');randomDraw(999,'unrelated');
  assert.equal(randomDraw(123,'quality',7,2,'enterprise'),x);
});
test('unsupported configuration and hypothetical successor are refused',()=>{
  assert.throws(()=>simulate({weeks:-1}));assert.throws(()=>simulate({nextAsset:{tested:false}}));
  assert.throws(()=>simulate({stopAfterInsolvency:false}));
  assert.throws(()=>simulate({constructionHours:null}));assert.throws(()=>simulate({authoringCostCents:null}));
  assert.throws(()=>simulate({constructionHours:'4'}));
});
test('direct cost repayment includes upkeep',()=>{
  const r=simulate({...control,assetMaintenanceCentsPerWeek:10},19,'B');
  assert.equal(r.exactAssetDirectCostRepayment.fixedCost,r.summary.assetFullCostAndUpkeepCents);
  assert.equal(r.exactAssetDirectCostRepayment.netBenefit,r.summary.directNetSavingCents);
});
