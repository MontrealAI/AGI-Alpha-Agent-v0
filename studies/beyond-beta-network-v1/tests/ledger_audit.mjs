// SPDX-License-Identifier: Apache-2.0
// Independent accounting controls. Synthetic fixtures are not scientific outcomes.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {simulate} from '../model/simulator.mjs';
import {BASE,ASSETS} from '../model/config.mjs';

const total=rows=>rows.reduce((a,b)=>a+b,0);
const money=value=>Math.round(value*100);
const numId=value=>Number(String(value).match(/\d+$/)?.[0]??NaN);
const near=(actual,expected,message)=>assert.ok(Math.abs(actual-expected)<=1e-6*Math.max(1,Math.abs(expected)),`${message}: ${actual} versus ${expected}`);
const integer=(value,message,nonnegative=true)=>{
  assert.ok(Number.isSafeInteger(value),`${message}: safe integer required`);
  if(nonnegative)assert.ok(value>=0,`${message}: nonnegative required`);
};

/** Reconstruct cash and obligations from independent ledger entries, not summary formula calls. */
export function auditRun(run){
  assert.ok(run?.histories&&run?.config&&run?.policy&&run?.summary,'Full retained simulation required');
  const {histories:h,summary:s,config:c,policy:p}=run;
  const seed=money(c.seedCapital),horizon=c.weeks+c.runoffWeeks;
  const bills=new Map(),payments=new Map(),receipts=new Map(),cashIds=new Set();
  let cash=seed,minimum=seed,previousWeek=-1;
  for(const b of h.bills){
    assert.ok(!bills.has(b.id),'Duplicate bill identity');bills.set(b.id,b);
    integer(b.amountCents,`Bill ${b.id}`);integer(b.week,'Bill week');
    assert.ok(b.week<horizon,'Bill outside finite horizon');
    assert.ok(['delivery','business','capability','maintenance','refund'].includes(b.category),'Unknown accounting category');
    assert.equal(typeof b.paid,'boolean');
    if(b.paid){integer(b.paidWeek,'Payment week');assert.ok(b.paidWeek>=b.week,'Payment predates obligation');}
    else assert.equal(b.paidWeek,null,'Unpaid bill has a payment date');
  }
  for(const e of h.cash){
    integer(e.week,'Cash event week');integer(e.amountCents,'Signed cash event',false);
    assert.ok(e.week>=previousWeek&&e.week<horizon,'Cash events must be chronological within horizon');previousWeek=e.week;
    assert.ok(!cashIds.has(e.id),'Duplicate cash event');cashIds.add(e.id);
    assert.ok(['expense_payment','refund_payment','simulated_collection'].includes(e.type),'Unexplained capital or revenue injection');
    if(e.type==='simulated_collection'){
      assert.ok(e.amountCents>=0,'Negative customer collection');assert.ok(!receipts.has(e.reference),'Invoice collected twice');receipts.set(e.reference,e);
    }else{
      const b=bills.get(e.reference);assert.ok(b,'Payment without a recorded obligation');
      assert.ok(!payments.has(b.id),'Obligation paid twice');payments.set(b.id,e);
      assert.equal(e.amountCents,-b.amountCents,'Payment differs from bill');
      assert.equal(e.week,b.paidWeek);assert.equal(b.paid,true);
      assert.equal(e.type,b.category==='refund'?'refund_payment':'expense_payment','Refund must not be resource expense');
    }
    cash+=e.amountCents;assert.ok(cash>=0,'Cash becomes negative');minimum=Math.min(minimum,cash);
    assert.equal(e.cashAfterCents,cash,'Event-level cash conservation');
  }
  for(const b of bills.values())assert.equal(b.paid,payments.has(b.id),'Bill payment flag disagrees with cash ledger');
  const expenses=total(h.bills.filter(b=>b.category!=='refund').map(b=>b.amountCents));
  const refundObligations=total(h.bills.filter(b=>b.category==='refund').map(b=>b.amountCents));
  const collected=total([...receipts.values()].map(e=>e.amountCents));
  const resourcePaid=0-total(h.cash.filter(e=>e.type==='expense_payment').map(e=>e.amountCents));
  const refundPaid=0-total(h.cash.filter(e=>e.type==='refund_payment').map(e=>e.amountCents));
  const unpaid=total(h.bills.filter(b=>!b.paid).map(b=>b.amountCents));
  assert.equal(s.costsCents,expenses,'All resource costs accrued exactly once');
  assert.equal(s.refundsCents,refundObligations,'Refunds are contra-revenue, including unpaid refund obligations');
  assert.equal(s.collectionsCents,collected);assert.equal(s.unpaidCents,unpaid);
  assert.equal(s.terminalCashCents,cash);assert.equal(s.minCashCents,minimum);
  assert.equal(cash,seed+collected-resourcePaid-refundPaid,'Finite cash identity');
  assert.equal(s.profitCents,collected-refundObligations-expenses,'Complete accrued profit');
  assert.equal(s.profitCents,cash-seed-unpaid,'Profit equals net assets less external seed');
  assert.equal(run.canonical.scenario.operatingMargin,s.profitCents,'Unchanged canonical ledger reconciles');
  assert.equal(run.canonical.observed.revenue,null,'Simulation cannot create observed receipts');
  assert.equal(run.evidence,'ASSUMED_OR_EXPLORED');assert.equal(s.actualJobs,0);assert.equal(s.actualCollectionsUSD,0);

  const jobs=new Map(h.jobs.map(j=>[j.id,j]));assert.equal(jobs.size,h.jobs.length,'Duplicate job identity');
  assert.equal(s.attemptedJobs,h.jobs.length,'Every admitted job completes within the finite horizon');
  assert.equal(s.accepted,h.jobs.filter(j=>j.accepted).length);
  assert.equal(s.usefulAccepted,h.jobs.filter(j=>j.useful).length);
  assert.equal(s.latentAcceptedErrors,h.jobs.filter(j=>j.accepted&&j.falsePass).length);
  const invoices=new Map(h.invoices.map(i=>[i.id,i]));assert.equal(invoices.size,h.invoices.length,'Duplicate invoice');
  assert.equal(h.invoices.length,s.accepted,'Exactly one invoice per accepted deliverable');
  assert.equal(s.invoicedCents,total(h.invoices.map(i=>i.amountCents)));
  for(const i of h.invoices){
    const j=jobs.get(i.jobId);assert.ok(j?.accepted,'Invoice requires accepted completed work');
    assert.equal(i.week,j.finishWeek);assert.equal(i.amountCents,j.priceCents);integer(i.dueWeek,'Invoice due week');
    assert.equal(i.dueWeek,i.week+c.collectionDelayWeeks,'Documented collection delay');
    assert.ok(i.dueWeek<horizon,'Every invoice due date must fit runoff');
    const receipt=receipts.get(i.id);assert.equal(Boolean(receipt),!i.badDebt,'Every due non-default invoice is collected exactly once');
    if(receipt){assert.equal(receipt.week,i.dueWeek,'Cash precedes neither due date nor accepted delivery');assert.equal(receipt.amountCents,i.amountCents);assert.equal(i.collectedWeek,receipt.week);}
    else assert.equal(i.collectedWeek,null,'Default cannot have a collection date');
    const refunds=h.bills.filter(b=>b.category==='refund'&&b.reference===i.id);
    assert.equal(refunds.length,i.refunded?1:0,'Refund state and obligation disagree');
    if(i.refunded){assert.ok(receipt,'Refund without collected cash');assert.ok(i.falsePass,'Refund is only modeled for material error');
      assert.equal(refunds[0].amountCents,i.amountCents);assert.equal(refunds[0].week,receipt.week+c.refundDelayWeeks);}
    const fees=h.bills.filter(b=>b.reference===`payment-processing:${i.id}`);
    assert.equal(fees.length,receipt?1:0,'Processing fee without collection or omitted collection fee');
    if(receipt)assert.equal(fees[0].amountCents,Math.round(i.amountCents*c.paymentFee));
  }
  for(const id of receipts.keys())assert.ok(invoices.has(id),'Collection without invoice');
  for(const b of h.bills.filter(b=>b.category==='refund'))assert.ok(invoices.has(b.reference),'Refund payable without invoice');

  assert.equal(h.balances.length,horizon,'One balance for every active and runoff week');
  for(const b of h.balances){
    const events=h.cash.filter(e=>e.week<=b.week),obligations=h.bills.filter(x=>x.week<=b.week);
    const collectedToDate=total(events.filter(e=>e.type==='simulated_collection').map(e=>e.amountCents));
    const refundsToDate=total(obligations.filter(x=>x.category==='refund').map(x=>x.amountCents));
    const costsToDate=total(obligations.filter(x=>x.category!=='refund').map(x=>x.amountCents));
    const cashToDate=seed+total(events.map(e=>e.amountCents));
    const unpaidToDate=total(obligations.filter(x=>!x.paid||x.paidWeek>b.week).map(x=>x.amountCents));
    assert.equal(b.cashCents,cashToDate,'Weekly cash reconciles');assert.equal(b.unpaidCents,unpaidToDate,'Weekly obligations reconcile');
    assert.equal(b.collectionsCents,collectedToDate);assert.equal(b.refundsCents,refundsToDate);assert.equal(b.accruedCostsCents,costsToDate);
    assert.equal(b.paidResourceCostsCents,0-total(events.filter(e=>e.type==='expense_payment').map(e=>e.amountCents)));
    const profit=collectedToDate-refundsToDate-costsToDate;assert.equal(b.fullCostProfitCents,profit);
    for(const k of ['reservedExecutionCents','maintenanceEarmarkCents','reservesCents','availableCents','earnedAvailableCents'])integer(b[k],`Balance ${k}`);
    const unsettledJobs=h.jobs.filter(j=>j.offerWeek<=b.week&&j.finishWeek>b.week);
    const unsettledReviews=h.campaigns.filter(a=>a.week<=b.week&&a.booking.finish>b.week);
    const reviewReserve=total(unsettledReviews.map(a=>run.assets.find(x=>x.id===a.id)?.reviewReserveCents??a.review.reservedCostCents));
    const expectedCommitment=total(unsettledJobs.map(j=>j.reservedCashCents??j.plan.reservedCostCents+money(315)))+reviewReserve;
    assert.equal(b.reservedExecutionCents,expectedCommitment,'Every unfinished job and independent review remains cash-reserved');
    const recentCollectionAmount=total(h.invoices.filter(i=>i.collectedWeek!==null&&i.collectedWeek<=b.week&&i.collectedWeek>b.week-c.refundDelayWeeks).map(i=>i.amountCents));
    const reserveFloor=money(c.minimumCashReserve*p.reserveFactor)+Math.round(Math.max(0,profit)*c.taxReserve)+Math.round(recentCollectionAmount*c.refundReserve);
    assert.ok(b.reservesCents>=reserveFloor,'Minimum liquidity, tax and unresolved-refund reserves are protected');
    const liquid=Math.max(0,cashToDate-unpaidToDate-b.reservedExecutionCents-b.maintenanceEarmarkCents-b.reservesCents);
    assert.equal(b.availableCents,liquid,'Available cash deducts obligations and all stated reserves');
    const unexpensedEarnedReview=total(unsettledReviews.map(a=>Math.max(0,a.earnedFundedCents-a.construction.costCents)));
    assert.ok(b.earnedAvailableCents<=Math.max(0,Math.min(liquid,profit-unexpensedEarnedReview)),
      'Seed, future receipts and already allocated review earnings cannot become newly available earned surplus');
  }
  const last=h.balances.at(-1);assert.equal(last.reservedExecutionCents,0,'No unfinished paid execution commitment');
  assert.equal(s.availableCents,last.availableCents);assert.equal(s.earnedAvailableCents,last.earnedAvailableCents);

  for(const j of h.jobs){
    assert.ok(j.startWeek>=j.offerWeek&&j.finishWeek>j.startWeek,'Job lifecycle chronology');
    assert.equal(j.queueWeeks,j.startWeek-j.offerWeek);assert.equal(j.reservationDurationWeeks,j.finishWeek-j.startWeek);
    const deadline=h.offers.find(o=>o.id===j.id)?.deadline;assert.ok(j.finishWeek-j.offerWeek<=deadline,'Quoted deadline includes queue and execution');
    assert.equal(j.costCents,total(h.bills.filter(b=>b.category==='delivery'&&b.reference===j.id).map(b=>b.amountCents)));
    for(const k of ['input','output','cpu','validation','hours'])assert.ok(j.resources[k]<=j.reservedResources[k]+1e-7,`Job ${j.id} exceeds blind reserved ${k}`);
    assert.ok(j.plan.costCents<=j.plan.reservedCostCents,'Cost reservation covers retries and recovery');
  }
  const limits={slots:c.concurrency,input:c.inputQuotaWeekly,output:c.outputQuotaWeekly,cpu:c.cpuHoursWeekly,validation:c.validatorHoursWeekly,hours:c.concurrency*c.hoursWeekly};
  assert.equal(h.capacity.length,horizon);
  for(const row of h.capacity)for(const [k,limit] of Object.entries(limits))assert.ok(row[k]>=0&&row[k]<=limit+1e-6,`Weekly ${k} quota/concurrency exceeded`);
  if(Array.isArray(h.auxiliary)){
    const reconstructed=Array.from({length:horizon},()=>({slots:0,input:0,output:0,cpu:0,validation:0,hours:0}));
    const addBooking=(start,finish,resources)=>{assert.ok(finish<=horizon);for(let w=start;w<finish;w++){
      reconstructed[w].slots++;for(const k of Object.keys(resources))reconstructed[w][k]+=resources[k]/(finish-start);
    }};
    for(const j of h.jobs)addBooking(j.startWeek,j.finishWeek,j.reservedResources);
    for(const a of h.campaigns)addBooking(a.booking.start,a.booking.finish,a.booking.resources);
    for(const a of h.auxiliary){
      const b=bills.get(a.billId);assert.ok(b,'Ancillary operation has no expense');assert.equal(b.amountCents,a.costCents);
      assert.equal(b.week,a.week);assert.equal(b.reference,a.reference);
      for(const k of Object.keys(a.resources))reconstructed[a.week][k]+=a.resources[k];
    }
    for(const row of h.capacity)for(const k of Object.keys(limits))near(row[k],reconstructed[row.week][k],`Complete independent ${k} flow ledger at week ${row.week}`);
  }

  assert.equal(s.investmentCampaigns,h.campaigns.length);
  assert.equal(s.earnedFundedInvestmentCents,total(h.campaigns.map(a=>a.earnedFundedCents)));
  assert.equal(s.seedFundedInvestmentCents,total(h.campaigns.map(a=>a.seedFundedCents)));
  for(const a of h.campaigns){
    const d=a.forecast;assert.ok(d.invested&&d.decision==='invest','Campaign has no selected decision');
    assert.ok(d.affordable&&d.capacityAvailable,'Unaffordable or unscheduled construction');
    assert.ok(d.forecastBenefitCents>d.completeCostCents*p.hurdle,'Controller forced an investment below its hurdle');
    assert.ok(d.availableBeforeCents>=d.completeCostCents,'Investment consumes future receipts or committed cash');
    assert.ok(a.earnedFundedCents<=d.earnedAvailableBeforeCents,'Seed mislabeled earned funding');
    assert.equal(a.earnedFundedCents+a.seedFundedCents,a.constructionCents,'Construction funding must reconcile');
    assert.equal(a.construction.diagnostics.baseWorkUnits,total(a.keys.map(k=>ASSETS[k].workUnits)),'Declared construction work is not dropped after failure');
    assert.equal(a.construction.diagnostics.allFailedTrialsIncluded,true);
    assert.equal(a.construction.costCents,total(Object.values(a.construction.costDetailsCents)),'Construction resource charges are complete');
    assert.equal(a.constructionCents,a.construction.costCents+a.review.costCents,'Construction and independent review are both charged');
    assert.ok(a.constructionCents<=d.buildCents,'Construction exceeds approved budget');
    assert.equal(a.fullTrialBudget,96);assert.ok(a.independentTrials>=1&&a.independentTrials<=96);
    assert.equal(a.actualJobEvents,0,'Simulated campaign cannot claim actual jobs');
    const constructionBills=h.bills.filter(b=>b.category==='capability'&&(b.reference===a.id||b.reference===`independent-review:${a.id}`));
    assert.equal(total(constructionBills.map(b=>b.amountCents)),a.constructionCents,'Construction ledger differs from campaign charge');
    const reviewBills=constructionBills.filter(b=>b.reference===`independent-review:${a.id}`);
    assert.equal(reviewBills.length,1);assert.equal(reviewBills[0].week,a.booking.finish,'Review expense is observable only on review completion');
    assert.ok(a.booking.finish>a.booking.start&&a.booking.start>=a.week,'Construction precedes readiness');
    const firstBill=constructionBills[0];
    if(firstBill&&Number.isFinite(numId(firstBill.id))){
      const previousCash=h.cash.filter(e=>numId(e.id)<numId(firstBill.id));
      assert.equal(d.financialSnapshot.cashCents,seed+total(previousCash.map(e=>e.amountCents)),'Decision snapshot uses cash available before construction');
      const previousBills=h.bills.filter(b=>numId(b.id)<numId(firstBill.id));
      const prevProfit=total(previousCash.filter(e=>e.type==='simulated_collection').map(e=>e.amountCents))-total(previousBills.map(b=>b.amountCents));
      assert.ok(d.earnedAvailableBeforeCents<=Math.max(0,prevProfit),'Earned funding depends only on prior collections and accrued costs');
      const unexpensedEarnedAllocation=total(h.campaigns.filter(x=>x.week<a.week&&x.booking.finish>a.week)
        .map(x=>Math.max(0,x.earnedFundedCents-x.construction.costCents)));
      assert.ok(d.earnedAvailableBeforeCents<=Math.max(0,prevProfit-unexpensedEarnedAllocation),'Uncompleted review cannot allocate the same earned surplus twice');
    }
  }
  return {passed:true,seed:run.seed,scenario:c.id,policy:p.id,histories:1,bills:h.bills.length,cashEvents:h.cash.length,
    invoices:h.invoices.length,jobs:h.jobs.length,campaigns:h.campaigns.length,balances:h.balances.length,
    actualJobs:0,actualCollectionsUSD:0,observedCanonicalRevenue:null};
}

/** Arms may differ endogenously; the sampled external opportunity stream is paired. */
export function auditPaired(...runs){
  assert.ok(runs.length>=2,'Two or more retained arms required');
  const first=runs[0];
  for(const run of runs.slice(1)){
    assert.equal(run.seed,first.seed);assert.deepEqual(run.config,first.config,'Paired arms require identical exogenous conditions');
    assert.equal(run.summary.potentialProspects,first.summary.potentialProspects);
    const reference=new Map(first.histories.offers.map(o=>[o.id,o]));
    for(const o of run.histories.offers){const p=reference.get(o.id);if(!p)continue;
      for(const k of ['week','classId','complexity','humanPriceCents','valueCents','deadline','agent','scopeSupported','repeat','commodity','improvable','trustCents','urgency'])assert.equal(o[k],p[k],`Paired exogenous field ${k}`);}
  }
  return {passed:true,arms:runs.length,seed:first.seed,externalStream:'paired',endogenousPurchasesAndWorkloadMayDiffer:true};
}

export const TEST_POLICY={id:'synthetic-retain',priceRatio:.4,scarcity:0,hurdle:1.1,reserveFactor:1,allowInvestment:false,allowBundles:false,allowMeta:false,allowSharing:false};
export const TEST_CONFIG={...BASE,id:'synthetic-control',weeks:12,seedCapital:100000,copyHazardWeekly:0,
  prospectsMonthly:20,marketSpread:0,buyerValueMedian:300000,buyerValueSpread:0,humanReference:100000,
  trustMax:0,switchingCost:0,initialPerceivedQuality:.98,priorReputationWeight:20,reputationFeedback:0,
  humanQuality:.97,initialCompletionBelief:.98,humanCompletionBelief:.98,
  scopeSupport:1,commodityShare:0,improvableFraction:1,initialError:0,commonError:0,
  improvementProbability:1,customerErrorDetection:1,lateErrorDetection:1,badDebt:0,concurrency:12,
  inputQuotaWeekly:150000000,outputQuotaWeekly:30000000,cpuHoursWeekly:20000,validatorHoursWeekly:5000,
  earlyAbandonWeeks:1000};

export function selfTestLedger(){
  const results=[],failures=[];
  const files=['model/config.mjs','model/workflow.mjs','model/simulator.mjs','tests/ledger_audit.mjs','upstream/canonical/shadow-ledger.mjs'];
  const hashSources=()=>Object.fromEntries(files.map(path=>[path,createHash('sha256').update(readFileSync(new URL(`../${path}`,import.meta.url))).digest('hex')]));
  const sourceHashesBefore=hashSources();
  const test=(name,fn)=>{try{const detail=fn();results.push({name,passed:true,...detail});}catch(e){results.push({name,passed:false,error:e.message});failures.push({name,error:e.message});}};
  const run=(config={},policy=TEST_POLICY,seed=42)=>simulate({...TEST_CONFIG,...config},policy,seed);
  test('zero-demand-keeps-complete-business-costs',()=>{const r=run({prospectsMonthly:0});const detail=auditRun(r);
    assert.equal(r.summary.collectionsCents,0);assert.equal(r.summary.attemptedJobs,0);assert.equal(r.summary.investmentCampaigns,0);
    assert.ok(r.summary.costsCents>=money(BASE.setupCost+BASE.historicalResearchAllowance));assert.equal(r.summary.profitCents,-r.summary.costsCents);return detail;});
  test('total-bad-debt-is-not-revenue',()=>{const r=run({badDebt:1});const detail=auditRun(r);assert.ok(r.summary.accepted>0);
    assert.equal(r.summary.collectionsCents,0);assert.ok(r.summary.invoicedCents>0);assert.equal(r.summary.earnedAvailableCents,0);return detail;});
  test('zero-delay-collections-settle-on-completion',()=>{const r=run({collectionDelayWeeks:0});const detail=auditRun(r);
    assert.ok(r.histories.invoices.length>0);assert.ok(r.histories.invoices.every(i=>i.collectedWeek===i.week));return detail;});
  test('twelve-week-delays-remain-finite',()=>{const r=run({collectionDelayWeeks:12});const detail=auditRun(r);
    assert.ok(r.histories.invoices.length>0);assert.equal(r.histories.balances.slice(0,12).at(-1).collectionsCents,0);return detail;});
  test('long-collection-and-refund-tail-is-complete',()=>{
    const r=run({commonError:1,customerErrorDetection:0,collectionDelayWeeks:12,refundDelayWeeks:6});const detail=auditRun(r);
    assert.ok(r.summary.collectionsCents>0);assert.equal(r.summary.refundsCents,r.summary.collectionsCents);return detail;
  });
  test('full-refund-is-contra-revenue-once',()=>{const r=run({commonError:1,customerErrorDetection:0,collectionDelayWeeks:0,refundDelayWeeks:0});const detail=auditRun(r);
    assert.ok(r.summary.collectionsCents>0);assert.equal(r.summary.refundsCents,r.summary.collectionsCents);assert.equal(r.summary.profitCents,-r.summary.costsCents);return detail;});
  test('unpaid-refund-is-preserved-without-double-expensing',()=>{
    const r=run({weeks:16,seedCapital:1000,historicalResearchAllowance:0,setupCost:0,overheadMonthly:0,
      operatorSubscriptionMonthly:0,runoffOverheadMonthly:0,minimumCashReserve:0,acquisitionCostPerProspect:0,
      prospectsMonthly:100,humanReference:2000,commonError:1,customerErrorDetection:0,
      collectionDelayWeeks:0,refundDelayWeeks:6});const detail=auditRun(r);
    assert.ok(r.histories.bills.some(b=>b.category==='refund'&&(!b.paid||b.paidWeek>b.week)),
      'Fixture must record an unpaid or deferred refund obligation');
    assert.ok(r.summary.insolvent);assert.equal(r.summary.profitCents,-r.summary.costsCents);return detail;
  });
  test('undetected-error-cannot-change-spend-or-reputation',()=>{
    const config={customerErrorDetection:0,lateErrorDetection:0,initialError:0,improvementProbability:1,reputationFeedback:1,initialPerceivedQuality:.87};
    const a=run({...config,commonError:0}),b=run({...config,commonError:1});auditRun(a);auditRun(b);
    assert.ok(b.summary.latentAcceptedErrors>0,'Fixture must exercise undetected errors');assert.equal(b.summary.refundsCents,0);
    const observed=r=>r.histories.offers.map(o=>({id:o.id,choice:o.choice,perceivedQuality:o.perceivedQuality}));
    assert.deepEqual(observed(a),observed(b),'Reputation learns undiscovered validity');
    assert.deepEqual(a.histories.balances,b.histories.balances,'Unobserved correctness changes incurred spend');
    return {pairedUndetectedErrors:b.summary.latentAcceptedErrors};
  });
  test('seed-shortfall-becomes-obligation-not-negative-cash',()=>{const r=run({seedCapital:100,prospectsMonthly:0});const detail=auditRun(r);
    assert.ok(r.summary.insolvent);assert.ok(r.summary.unpaidCents>0);assert.equal(r.summary.earnedAvailableCents,0);return detail;});
  test('reserved-jobs-cannot-spend-the-same-cash',()=>{const r=run({seedCapital:1000,historicalResearchAllowance:0,setupCost:0,overheadMonthly:0,
    operatorSubscriptionMonthly:0,runoffOverheadMonthly:0,minimumCashReserve:0,acquisitionCostPerProspect:0,prospectsMonthly:150,collectionDelayWeeks:12});
    const detail=auditRun(r);assert.ok(r.summary.liquidityRefusals>0);assert.ok(r.summary.attemptedJobs>0);
    for(const b of r.histories.balances)assert.ok(b.cashCents>=b.reservedExecutionCents,'Cash protects all admitted work');return detail;});
  test('zero-resource-effect-retains-cash',()=>{const p={...TEST_POLICY,id:'synthetic-null-investment',allowInvestment:true,allowBundles:true,allowMeta:true};
    const r=run({weeks:28,bundleEffect:1,singleCapabilityOverhead:0,minimumObservedProspects:1},p);const detail=auditRun(r);
    assert.ok(r.summary.discoveryEvaluations>0);assert.equal(r.summary.investmentCampaigns,0);return detail;});
  const investPolicy={...TEST_POLICY,id:'synthetic-investment',allowInvestment:true,allowBundles:true,allowMeta:true,allowSharing:true};
  const construction={weeks:28,assetConstructionMultiplier:.05,assetLifetimeWeeks:12,assetProductiveProbability:0,assetFalseAdmission:0,
    assetFalseRejection:0,reviewCaseCoverage:1,reviewDetection:1,assetTransferCost:0,minimumObservedProspects:1,assetRetryWait:8,
    assetMaintenanceWeekly:0,assetRevalidationCost:0,forecastHaircut:1,meanAssetBelief:1};
  test('failed-independent-search-still-pays-construction',()=>{const r=run(construction,investPolicy,7);const detail=auditRun(r);
    assert.ok(r.summary.investmentCampaigns>0,'Synthetic fixture must exercise a campaign');assert.equal(r.summary.successfulCampaigns,0);
    assert.ok(r.summary.failedCampaigns>0);assert.ok(r.histories.campaigns.every(a=>a.independentTrials===1));return detail;});
  test('maintenance-can-spend-its-own-earmark',()=>{
    const r=run({...construction,assetProductiveProbability:1,assetMaintenanceWeekly:18,seedCapital:5000,
      badDebt:1,historicalResearchAllowance:0,setupCost:0,overheadMonthly:0,operatorSubscriptionMonthly:0,
      runoffOverheadMonthly:0,minimumCashReserve:0,acquisitionCostPerProspect:0,hoursWeekly:1000,
      inputQuotaWeekly:1e9,outputQuotaWeekly:2e8,cpuHoursWeekly:1e6,validatorHoursWeekly:1e5},
      {...investPolicy,allowSharing:false},7);const detail=auditRun(r);
    assert.ok(r.summary.investmentCampaigns>0,'Fixture must fund a capability');
    assert.ok(r.summary.liquidityRefusals+r.summary.marketThrottled>0,'Fixture must exhaust unreserved delivery cash');
    assert.ok(r.assets.every(a=>!a.revoked),'Already earmarked upkeep must remain spendable after free cash is exhausted');
    return detail;
  });
  test('unaffordable-construction-does-not-use-future-demand',()=>{const r=run({...construction,assetConstructionMultiplier:100,seedCapital:35000},investPolicy,7);const detail=auditRun(r);
    assert.equal(r.summary.investmentCampaigns,0);return detail;});
  test('unobserved-review-outcome-cannot-change-earlier-cash',()=>{const a=run(construction,investPolicy,7),b=run({...construction,assetProductiveProbability:1},investPolicy,7);
    auditRun(a);auditRun(b);assert.ok(a.histories.campaigns.length&&b.histories.campaigns.length,'Fixture must reach construction');
    const before=Math.min(a.histories.campaigns[0].booking.finish,b.histories.campaigns[0].booking.finish);
    assert.deepEqual(a.histories.balances.filter(x=>x.week<before),b.histories.balances.filter(x=>x.week<before),'Controller saw uncompleted validation outcome in spendable cash');
    return {beforeObservableWeek:before,campaigns:2};});
  test('paired-ablation-keeps-external-opportunities',()=>{const a=run(construction,investPolicy,7);
    const b=simulate({...TEST_CONFIG,...construction},investPolicy,7,{ablation:'no-investment'});auditRun(a);auditRun(b);return auditPaired(a,b);});
  const sourceHashes=hashSources();
  return {schema:'transformational-venture-ledger-controls/v1',evidence:'OBSERVED_SOFTWARE_CONTROLS_ONLY',createdAt:new Date().toISOString(),
    sourceHashesBefore,sourceHashes,sourceFilesUnchangedDuringControls:JSON.stringify(sourceHashesBefore)===JSON.stringify(sourceHashes),
    controls:results.length,passed:results.length-failures.length,failed:failures.length,results,
    noScientificSelection:true,noLiveModelsOrCustomerWork:true,actualJobs:0,actualCollectionsUSD:0};
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
  const result=selfTestLedger();console.log(JSON.stringify(result,null,2));
  if(result.failed||!result.sourceFilesUnchangedDuringControls)process.exitCode=1;
}
