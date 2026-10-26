import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {simulate, pairedSimulation, chooseBuyer, pruneDominated, validateConfig, defaultConfig} from '../market/src/market.mjs';

const sourcePath=new URL('../market/src/market.mjs',import.meta.url);
const sha256=crypto.createHash('sha256').update(fs.readFileSync(sourcePath)).digest('hex');
const results=[];
const sum=values=>values.reduce((a,b)=>a+b,0);
const test=(name,run)=>{try{run();results.push({name,pass:true});}catch(e){results.push({name,pass:false,error:e.message});}};
const control={id:'independent-audit-control',weeks:4,buyers:1,arrivalProbability:1,supportedFraction:1,
  initialCashCents:100000,reserveCents:0,initialSetupCents:0,weeklyOverheadCents:0,
  paymentDelayWeeks:1,paymentProbability:1,expenseDelayWeeks:0,refundDelayWeeks:1,
  hourlyProviderCents:6000,hourlyBuyerCents:[6000],humanMinutes:[60],usefulnessMultiplier:10,
  customerReviewMinutes:0,diyEffortFraction:1,diyQuality:0,humanSlotsPerWeek:0,aiSlotsPerWeek:0,
  initialTrust:1,skepticalShare:0,integrationCents:0,switchingCents:0,delayCostCentsPerDay:0,
  successProbability:1,overloadPenalty:0,computeAndToolCents:0,
  commonResidualMinutes:2,ordinaryFinalizationMinutes:10,assetResidualMinutes:0,
  pricingPolicy:'fixed',initialPriceCents:2000,constructionHours:0,authoringCostCents:0,
  adoptionHours:0,adoptionInferenceCents:0,
  assetMaintenanceCentsPerWeek:0,investmentEarliestWeek:1,investmentForecastDiscount:1,
  expectedPassThrough:0,competitorStrategy:'fixed',allMoneyIsAssumed:true};
const run=(overrides={},arm='B')=>simulate({...control,...overrides},714195,arm,{includeOffers:true});
const buyer={valueCents:10000,errorLossCents:10000};
const offer=(id,p=1000,q=1,e=0,d=0,s=0)=>({id,priceCents:p,quality:q,effortCents:e,delayCents:d,switchCents:s});

function auditAccounting(r){
  const h=r.histories,s=r.summary;
  assert.equal(r.config.initialCashCents+sum(h.cash.map(e=>e.amountCents)),s.finalCashCents);
  assert.equal(sum(h.bills.map(b=>b.amountCents)),s.accruedCostsCents);
  assert.equal(sum(h.bills.filter(b=>b.paid).map(b=>b.amountCents)),s.paidCostsCents);
  assert.equal(sum(h.bills.filter(b=>!b.paid).map(b=>b.amountCents)),s.obligationsCents);
  assert.equal(sum(h.invoices.map(i=>i.amountCents)),s.grossInvoicesCents);
  assert.equal(sum(h.invoices.filter(i=>i.status==='collected').map(i=>i.amountCents)),s.grossCollectionsCents);
  assert.equal(sum(h.invoices.filter(i=>i.status==='defaulted').map(i=>i.amountCents)),s.writtenOffCents);
  const pending=sum(h.invoices.filter(i=>i.status==='pending').map(i=>i.amountCents));
  assert.equal(s.finalCashCents+pending-s.obligationsCents-r.config.initialCashCents,s.profitCents);
  const jobs=new Map(h.jobs.map(j=>[j.id,j]));
  assert.equal(jobs.size,h.jobs.length);
  for(const i of h.invoices){assert.equal(jobs.get(i.mission)?.provider,'enterprise');assert.equal(jobs.get(i.mission)?.accepted,true);}
  const paid=new Set();
  for(const e of h.cash.filter(e=>e.amountCents<0)){assert(!paid.has(e.reference));paid.add(e.reference);}
  let cash=r.config.initialCashCents;
  for(const e of h.cash){cash+=e.amountCents;assert.equal(e.cashAfterCents,cash);assert(cash>=0);}
  for(const b of h.balances){assert.equal(b.cashCents-r.config.initialCashCents,b.cumulativeCollectionsCents-b.paidCostsCents);}
  for(const i of h.investments)assert(i.availableCashCents>=i.fullCostCents);
  for(const projection of [r.canonical.economic,r.canonical.cash]){
    assert.equal(projection.summary.observed.revenue,0);
    const money=projection.ledger.events.filter(e=>e.type==='revenue');
    assert(money.every(e=>e.category!=='collected'||e.amountMinor===0));
  }
}

test('cash, receivable, cost and invoice identities reconcile',()=>auditAccounting(run()));
test('zero arrivals generate no invoices or receipts',()=>{const r=run({arrivalProbability:0});auditAccounting(r);assert.equal(r.summary.grossInvoicesCents,0);assert.equal(r.summary.grossCollectionsCents,0);assert.equal(r.summary.investmentWeek,null);});
test('zero supported scope generates no sale',()=>{const r=run({supportedFraction:0});assert.equal(r.summary.enterpriseAttempts,0);assert.equal(r.summary.grossInvoicesCents,0);});
test('zero buyer value permits deferral',()=>{for(const choiceModel of ['deterministic','logit'])assert.equal(chooseBuyer([offer('enterprise')],{valueCents:0,errorLossCents:10000},{...defaultConfig,choiceModel},0.5).choice,'defer');});
test('strictly dominated offer removed before either choice model',()=>{const offers=[offer('expensive',1001),offer('cheap',1000)];assert.deepEqual(pruneDominated(offers).map(o=>o.id),['cheap']);for(const choiceModel of ['deterministic','logit'])for(const u of [0,0.1,0.5,0.9,0.999999])assert.notEqual(chooseBuyer(offers,buyer,{...defaultConfig,choiceModel},u).choice,'expensive');});
test('free competent equal-effort offer dominates positive-price equivalent',()=>{const r=run({diyQuality:1,diyEffortFraction:0,diyDays:0});assert.equal(r.summary.enterpriseAttempts,0);});
test('matched B/C resources, policies and draws give exact numeric tie',()=>{const r=pairedSimulation(control,714195);assert.deepEqual(r.arms.B.summary,r.arms.C.summary);assert.equal(r.causal.B_minus_C_profitCents,0);});
test('zero capability effect is not financed',()=>{const r=run({ordinaryFinalizationMinutes:0,assetResidualMinutes:0});assert.equal(r.summary.investmentWeek,null);assert.equal(r.summary.assetUses,0);});
test('zero capacity creates no enterprise invoice',()=>{const r=run({enterpriseSlotsPerWeek:0});assert.equal(r.summary.enterpriseAttempts,0);assert.equal(r.summary.grossInvoicesCents,0);});
test('uncollected invoices cannot finance operating-surplus investment',()=>{const r=run({paymentDelayWeeks:20,initialCashCents:1000000,constructionHours:0.01,investmentFunding:'operating-surplus'});assert.equal(r.summary.investmentWeek,null);});
test('defaulted invoices leave costs and no revenue',()=>{const r=run({paymentProbability:0});auditAccounting(r);assert.equal(r.summary.grossCollectionsCents,0);assert.equal(r.summary.profitCents,-r.summary.accruedCostsCents);});
test('rejected deliveries do not issue accepted invoices',()=>{const r=run({successProbability:0,buyers:4,weeks:8,initialTrust:1,churnProbability:0,refundProbability:1});auditAccounting(r);for(const j of r.histories.jobs.filter(j=>j.provider==='enterprise'&&!j.accepted))assert.equal(j.invoiceCreated,false);});
test('zero-week collections execute at invoice week',()=>{const r=run({paymentDelayWeeks:0});assert(r.histories.invoices.length>0);for(const i of r.histories.invoices.filter(i=>i.status==='collected'))assert.equal(i.collectedWeek,i.week);});
test('accepted-work investment forecasts exclude rejected attempts',()=>{const r=run({successProbability:0.4,weeks:20,buyers:4,churnProbability:0,initialTrust:1});for(const d of r.histories.investmentDecisions){const actual=r.histories.jobs.filter(j=>j.provider==='enterprise'&&j.accepted&&j.week<d.week&&j.week>=Math.max(0,d.week-8)).length;assert.equal(d.observedPriorAccepted,actual);}});
test('direct lifetime repayment charges reported upkeep',()=>{const r=run({assetMaintenanceCentsPerWeek:1});assert(r.summary.assetUses>0);assert.equal(r.exactAssetDirectCostRepayment.lifetimeCost,r.summary.assetFullCostAndUpkeepCents);});
test('zero buyer pass-through leaves posted price unchanged after investment',()=>{const r=run({pricingPolicy:'cost-pass-through',expectedPassThrough:0});assert(r.summary.assetUses>0);for(const p of r.histories.prices.filter(p=>p.assetActive))assert.equal(p.enterpriseCents,control.initialPriceCents);});
test('full buyer pass-through reduces price by full unit saving',()=>{const r=run({pricingPolicy:'cost-pass-through',expectedPassThrough:1,constructionHours:0,authoringCostCents:0,investmentFunding:'seed-funded'});if(r.summary.assetUses===0){assert(r.histories.investmentDecisions.every(d=>d.expectedIncrementalSavingPerUseCents===0));return;}throw Error('investment funded without retained monetary saving requires a distinct declared objective');});
test('unknown numeric costs are rejected, never coerced to free',()=>{for(const key of ['constructionHours','authoringCostCents','adoptionHours','adoptionInferenceCents','commonResidualMinutes'])for(const value of [null,'0',false])assert.throws(()=>validateConfig({[key]:value}),`${key}=${value}`);});
test('zero procurement budget excludes paid providers',()=>{const r=run({buyerProcurementBudgetCents:0});assert.equal(r.summary.enterpriseAttempts,0);assert(r.histories.buyerProcurement.every(b=>b.committedCents===0));});
test('buyer commitments never exceed finite procurement budgets',()=>{const r=run({buyerProcurementBudgetCents:4000,weeks:20,buyers:4});for(const b of r.histories.buyerProcurement){assert(b.committedCents<=b.budgetCents);const committed=sum(r.histories.jobs.filter(j=>j.buyer===b.id&&j.invoiceCreated).map(j=>j.priceCents));assert.equal(committed,b.committedCents);}});
test('quality information is unavailable until feedback is due',()=>{const r=run({weeks:5,successProbability:0,outcomeFeedbackDelayWeeks:3,churnProbability:0,errorLossCents:0});const byWeek=new Map(r.histories.buyerChoices.map(c=>[c.week,c.offers?.find(o=>o.id==='enterprise')?.quality]));assert.equal(byWeek.get(1),byWeek.get(0));assert.equal(byWeek.get(2),byWeek.get(0));assert(byWeek.get(3)<byWeek.get(0));});
test('upfront historical expense precedes operating collections and can exhaust seed',()=>{const r=run({historicalCostTiming:'opening',investmentCostBasis:'full-history',constructionHours:10,authoringCostCents:0,initialCashCents:100});auditAccounting(r);assert.equal(r.summary.enterpriseAttempts,0);assert.equal(r.summary.grossCollectionsCents,0);assert.equal(r.summary.insolvent,true);assert.equal(r.summary.assetUses,0);assert(r.summary.obligationsCents>0);});
test('failed-delivery direct savings use the same cost multiplier',()=>{const r=run({weeks:20,qualityShockWeek:3,qualityShockFactor:0.5,churnProbability:0});assert(r.summary.assetUses>0);const ordinary=Math.round((r.config.commonResidualMinutes+r.config.ordinaryFinalizationMinutes)*r.config.hourlyProviderCents/60)+r.config.computeAndToolCents;const calculated=sum(r.histories.jobs.filter(j=>j.provider==='enterprise'&&j.assetUsed).map(j=>Math.round(ordinary*(j.qualityGood?1:r.config.failureCorrectionMultiplier))-j.deliveryCostCents));assert.equal(r.summary.directAvoidedCostCents,calculated);});
test('expenses with delay longer than collections are drained before final state',()=>{const r=run({expenseDelayWeeks:20,paymentDelayWeeks:1});auditAccounting(r);assert(r.histories.bills.length>0);assert(r.histories.bills.every(b=>b.paid));assert.equal(r.summary.obligationsCents,0);});
test('adoption service pause prevents delivery and premature asset use',()=>{const r=run({weeks:12,constructionHourlyCents:0,adoptionHours:8,engineeringHoursPerWeek:4});const i=r.histories.investments[0];assert(i);assert.equal(i.availableWeek-i.week,2);assert(r.histories.jobs.filter(j=>j.provider==='enterprise').every(j=>j.week<i.week||j.week>=i.availableWeek));assert(r.histories.jobs.filter(j=>j.assetUsed).every(j=>j.week>=i.availableWeek));assert(r.summary.assetUses>0);});
test('known zero post-adoption production horizon prevents investment',()=>{const r=run({weeks:2,investmentEarliestWeek:1,adoptionHours:0});assert.equal(r.summary.investmentWeek,null);});

const report={schema:'agi-alpha-independent-control-audit/v1',sourceSHA256:sha256,primaryOutcomesInspected:false,
  scope:'Synthetic controls only; no primary scenario sweep or production confirmation outcomes inspected',
  executedAt:new Date().toISOString(),passed:results.filter(x=>x.pass).length,failed:results.filter(x=>!x.pass).length,results};
const out=process.argv[2];
if(out)fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
process.exitCode=report.failed?1:0;
