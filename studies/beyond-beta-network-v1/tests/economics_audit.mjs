// SPDX-License-Identifier: Apache-2.0
// Independent reconstruction of recorded financial and resource events.
import assert from 'node:assert/strict';
const sum=a=>a.reduce((s,x)=>s+x,0);
const close=(a,b,m)=>assert.ok(Math.abs(a-b)<1e-6*Math.max(1,Math.abs(b)),`${m}: ${a} != ${b}`);
export function auditRun(run){
 const {histories:h,summary:s,config:C,policy:P}=run;
 const seed=Math.round(C.seedCapital*100),horizon=C.weeks+C.runoffWeeks;
 const bills=new Map(h.bills.map(b=>[b.id,b])),invoices=new Map(h.invoices.map(i=>[i.id,i]));
 assert.equal(bills.size,h.bills.length);assert.equal(invoices.size,h.invoices.length);
 const payment=new Map(),collection=new Map();let cash=seed,last=-1;
 const weekly=Array.from({length:horizon},()=>({cash:0,cost:0,refund:0,collected:0,paidCost:0,unpaid:0}));
 for(const b of bills.values()){
  assert.ok(Number.isSafeInteger(b.amountCents)&&b.amountCents>=0);
  assert.ok(b.week>=0&&b.week<horizon);
  weekly[b.week][b.category==='refund'?'refund':'cost']+=b.amountCents;
  weekly[b.week].unpaid+=b.amountCents;
  if(b.paid)weekly[b.paidWeek].unpaid-=b.amountCents;
 }
 for(const e of h.cash){
  assert.ok(Number.isSafeInteger(e.amountCents));assert.ok(e.week>=last);last=e.week;
  if(e.type==='simulated_collection'){
   const i=invoices.get(e.reference);assert.ok(i&&!i.badDebt&&!collection.has(i.id));
   assert.equal(e.amountCents,i.amountCents);assert.equal(e.week,i.dueWeek);collection.set(i.id,e);
   weekly[e.week].collected+=e.amountCents;
  }else{
   const b=bills.get(e.reference);assert.ok(b&&!payment.has(b.id)&&b.paid);
   assert.equal(e.amountCents,-b.amountCents);assert.equal(e.week,b.paidWeek);
   assert.equal(e.type,b.category==='refund'?'refund_payment':'expense_payment');payment.set(b.id,e);
   if(b.category!=='refund')weekly[e.week].paidCost+=b.amountCents;
  }
  cash+=e.amountCents;assert.ok(cash>=0);assert.equal(e.cashAfterCents,cash);weekly[e.week].cash+=e.amountCents;
 }
 for(const b of bills.values())assert.equal(b.paid,payment.has(b.id));
 for(const i of invoices.values()){
  const j=h.jobs.find(j=>j.id===i.jobId);assert.ok(j?.accepted);assert.equal(i.week,j.finishWeek);
  assert.equal(i.dueWeek,i.week+C.collectionDelayWeeks);assert.equal(i.amountCents,j.priceCents);
  assert.equal(collection.has(i.id),!i.badDebt);
  const refunds=h.bills.filter(b=>b.category==='refund'&&b.reference===i.id);
  assert.equal(refunds.length,i.refunded?1:0);
  if(i.refunded){assert.ok(i.falsePass&&collection.has(i.id));assert.equal(refunds[0].week,i.dueWeek+C.refundDelayWeeks);}
 }
 let acc={cash:seed,cost:0,refund:0,collected:0,paidCost:0,unpaid:0};
 for(let w=0;w<horizon;w++){
  for(const k of Object.keys(acc))acc[k]+=weekly[w][k];const b=h.balances[w];assert.equal(b.week,w);
  assert.equal(b.cashCents,acc.cash);assert.equal(b.accruedCostsCents,acc.cost);assert.equal(b.refundsCents,acc.refund);
  assert.equal(b.collectionsCents,acc.collected);assert.equal(b.paidResourceCostsCents,acc.paidCost);assert.equal(b.unpaidCents,acc.unpaid);
  const profit=acc.collected-acc.refund-acc.cost;assert.equal(b.fullCostProfitCents,profit);
  const jobs=sum(h.jobs.filter(j=>j.offerWeek<=w&&w<j.finishWeek).map(j=>j.reservedCashCents));
  const campaigns=sum(h.campaigns.filter(a=>a.week<=w&&w<a.booking.finish).map(a=>a.review.reservedCostCents));
  const revalidations=sum(h.revalidations.filter(a=>a.week<=w&&w<a.finishWeek).map(a=>a.reservedCostCents));
  assert.equal(b.reservedExecutionCents,jobs+campaigns+revalidations,'All unfinished work has cash committed');
  const protectedCents=b.reservesCents+b.maintenanceEarmarkCents+b.reservedExecutionCents;
  assert.equal(b.availableCents,Math.max(0,acc.cash-acc.unpaid-protectedCents));
  assert.equal(b.earnedAvailableCents,Math.max(0,Math.min(b.availableCents,profit-protectedCents)));
  assert.ok(b.reservesCents>=Math.round(C.minimumCashReserve*P.reserveFactor*100));
 }
 assert.equal(s.terminalCashCents,cash);assert.equal(s.collectionsCents,acc.collected);assert.equal(s.costsCents,acc.cost);
 assert.equal(s.refundsCents,acc.refund);assert.equal(s.unpaidCents,acc.unpaid);
 assert.equal(s.profitCents,acc.collected-acc.refund-acc.cost);assert.equal(s.profitCents,cash-seed-acc.unpaid);
 assert.equal(s.A_jobCostCents+s.B_retentionReuseCostCents+s.C_optionalResearchCostCents+s.commonBusinessCostCents+s.historicalAllowanceCostCents,s.costsCents,'A+B+C+common+historical costs are mutually exclusive and exhaustive');
 assert.equal(s.sourceJobDevelopmentRechargedCents,0,'Paid learning may not be charged twice');
 assert.equal(run.canonical.scenario.operatingMargin,s.profitCents);assert.equal(run.canonical.observed.revenue,null);
 assert.equal(s.actualJobs,0);assert.equal(s.actualCollectionsUSD,0);assert.equal(s.automatedProviderHumanHours,0);
 assert.equal(s.attemptedJobs,h.jobs.length);assert.equal(s.accepted,h.jobs.filter(j=>j.accepted).length);
 assert.equal(s.usefulAccepted,h.jobs.filter(j=>j.useful).length);
 const capacity=Array.from({length:horizon+32},()=>({slots:0,input:0,output:0,cpu:0,validation:0,hours:0}));
 function add(b){for(let w=b.start;w<b.finish;w++){capacity[w].slots++;for(const k of ['input','output','cpu','validation','hours'])capacity[w][k]+=b.resources[k]/b.duration;}}
 for(const j of h.jobs){
  add({start:j.startWeek,finish:j.finishWeek,duration:j.reservationDurationWeeks,resources:j.reservedResources});
  for(const k of ['input','output','cpu','validation','hours'])assert.ok(j.resources[k]<=j.reservedResources[k]+1e-6,`Realized job exceeds blind ${k} reservation`);
  assert.ok(j.costCents<=j.reservedCashCents,'Complete delivery exceeds committed bill');
 }
 for(const a of h.campaigns){
  add(a.booking);assert.ok(a.forecast.affordable&&a.forecast.capacityAvailable&&a.forecast.invested);
  assert.ok(a.forecast.completeCostCents<=a.forecast.financialSnapshot.availableCents,'Investment spends future or reserved cash');
  assert.ok(a.earnedFundedCents<=a.forecast.earnedAvailableBeforeCents);
  assert.equal(a.earnedFundedCents+a.seedFundedCents,a.constructionCents);
  assert.equal(a.jobCostRechargedCents,0);
  assert.equal(a.review.assessment.completeLifecycleCostCents,a.forecast.completeCostCents-a.review.reservedCostCents+a.review.costCents,'Remaining incremental Alpha hurdle reconciles without source-job A');
  if(a.sourceKind==='B_paid_job_retention'){
   const j=h.jobs.find(j=>j.id===a.originJobId),i=h.invoices.find(i=>i.id===a.originInvoiceId);
   assert.ok(j?.accepted&&i?.collectedWeek!==null&&i.collectedWeek<=a.week,'Retention requires an observable collected paid job');
   assert.equal(a.jobDevelopmentAlreadyChargedCents,j.costCents);
   assert.ok(!h.bills.some(b=>b.category==='refund'&&b.reference===i.id&&b.week<=a.week),'A known refunded job cannot be selected as paid learning');
   assert.equal(bills.get(a.constructionBillId).lane,'B_retention_reuse');
  }else assert.equal(bills.get(a.constructionBillId).lane,'C_optional_research');
 }
 for(const a of h.revalidations)add(a.booking);
 for(const a of h.auxiliary)for(const k of ['input','output','cpu','validation','hours'])capacity[a.week][k]+=a.resources[k];
 const limits={slots:C.concurrency,input:C.inputQuotaWeekly,output:C.outputQuotaWeekly,cpu:C.cpuHoursWeekly,
  validation:C.validatorHoursWeekly,hours:C.concurrency*C.hoursWeekly};
 for(const w of h.capacity)for(const k of Object.keys(limits)){
  close(w[k],capacity[w.week][k],`Resource flow ${k} week${w.week}`);
  assert.ok(w[k]<=limits[k]+1e-6,`Quota exceeded ${k}`);
 }
 for(const e of h.network.filter(e=>e.type==='modeled-admission'||e.type==='modeled-revalidation')){
  const a=h.alphaAssessments.find(a=>a.assetId===e.id&&a.week===e.week);
  assert.ok(a&&a.verdict==='admit'&&a.lowerLifetimeNetCents>0&&a.correctnessChecksPassed);
  assert.equal(a.betaVersion,e.betaVersion);
  if(e.type==='modeled-admission')assert.equal(e.availableTo.length,3,'Admitted shareable Alpha must be available to all network members');
 }
 return {passed:true,cashEvents:h.cash.length,bills:h.bills.length,jobs:h.jobs.length,campaigns:h.campaigns.length,revalidations:h.revalidations.length};
}

export function auditPaired(a,b){
 assert.equal(a.seed,b.seed);assert.equal(a.summary.potentialProspects,b.summary.potentialProspects);
 for(const k of ['seedCapital','concurrency','inputQuotaWeekly','outputQuotaWeekly','cpuHoursWeekly','validatorHoursWeekly'])assert.equal(a.config[k],b.config[k],`Unequal paired resource ${k}`);
 return true;
}
