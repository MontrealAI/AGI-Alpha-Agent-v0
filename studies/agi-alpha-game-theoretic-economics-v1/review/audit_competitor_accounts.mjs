// SPDX-License-Identifier: Apache-2.0
// Independent accounting reconstruction. Imports no economic simulator code.
import {createReadStream,readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createGunzip} from 'node:zlib';
import {createInterface} from 'node:readline';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..'),market=resolve(root,'market');
const output=process.argv[2]??resolve(root,'review/competitor-account-outcome-audit.json');
if(existsSync(output))throw Error('Refusing to overwrite a previous audit receipt; choose a new output path.');
const results=resolve(market,'reporting/results-01');
const source=JSON.parse(readFileSync(resolve(market,'reporting/source-manifest.json')));
const completion=JSON.parse(readFileSync(resolve(results,'completion.json')));
const sha=s=>createHash('sha256').update(s).digest('hex');
const digest=async p=>{const h=createHash('sha256');for await(const b of createReadStream(p))h.update(b);return h.digest('hex');};
const lines=p=>createInterface({input:createReadStream(p).pipe(createGunzip()),crlfDelay:Infinity});
const sum=a=>a.reduce((s,x)=>s+x,0),checks={},totals={},firstFailures=[];
let failedAssertions=0,context='source custody';
function ck(ok,name,detail){checks[name]=(checks[name]??0)+1;if(!ok){failedAssertions++;if(firstFailures.length<50)firstFailures.push({context,check:name,detail});}}
function eq(a,b,name){ck(a===b,name,a===b?undefined:{actual:a,expected:b});}
function add(key,n=1){totals[key]=(totals[key]??0)+n;}
function byWeek(rows,week,value){const m=new Map();for(const r of rows){const w=week(r);m.set(w,(m.get(w)??0)+value(r));}return m;}

eq(completion.complete,true,'reporting export completed');
eq(completion.newEconomicScenarios,0,'no new economic scenario counted');
eq(completion.observedCustomerCollectionsCents,0,'no observed collections');
eq(completion.actualFinancialTransactions,0,'no actual transaction');
eq(await digest(resolve(market,'reporting/source-manifest.json')),completion.sourceManifestSHA256,'completion binds reporting source manifest');
for(const f of source.files)eq(await digest(resolve(market,f.path)),f.sha256,'reporting source file digest');
const originalSource=readFileSync(resolve(market,'src/market.mjs'),'utf8');
eq(readFileSync(resolve(market,'reporting/market-expose.mjs'),'utf8'),originalSource.replace('    competitorSummary:Object.fromEntries','    competitorAccounts:competitors,\n    competitorSummary:Object.fromEntries'),'single return-property instrumentation only');

function auditFirm(f,id,record,run){
  const c=run.config,h=run.histories,jobs=h.jobs.filter(j=>j.provider===id),jobMap=new Map(jobs.map(j=>[j.id,j]));
  const invoices=f.invoices,bills=f.bills,cash=f.cashEvents,invoiceMap=new Map(invoices.map(i=>[i.id,i])),billMap=new Map(bills.map(b=>[b.id,b]));
  const invoicesByMission=new Map(),deliveryByMission=new Map();
  for(const i of invoices)invoicesByMission.set(i.mission,(invoicesByMission.get(i.mission)??0)+1);
  for(const b of bills)if(b.category==='delivery')deliveryByMission.set(b.reference,(deliveryByMission.get(b.reference)??0)+b.amountCents);
  eq(f.id,id,'competitor identity');eq(f.openingCashCents,c.competitorInitialCashCents,'declared finite opening cash');
  eq(f.balanceHistory.length,0,'native empty balance history preserved');
  eq(jobMap.size,jobs.length,'unique competitor delivery identity');
  eq(invoiceMap.size,invoices.length,'unique competitor invoice identity');
  eq(billMap.size,bills.length,'unique competitor liability identity');
  eq(f.attempts,jobs.length,'competitor attempts from delivered jobs');
  eq(f.accepted,jobs.filter(j=>j.accepted).length,'competitor acceptance count');
  eq(f.rejected,jobs.filter(j=>!j.accepted).length,'competitor rejection count');
  eq(f.latentFailures,jobs.filter(j=>j.accepted&&!j.qualityGood).length,'competitor latent quality failures');
  const accrued=sum(bills.map(b=>b.amountCents)),paid=sum(bills.filter(b=>b.paid).map(b=>b.amountCents));
  const gross=sum(invoices.map(i=>i.amountCents)),collected=sum(invoices.filter(i=>i.status==='collected').map(i=>i.amountCents)),
    defaults=sum(invoices.filter(i=>i.status==='defaulted').map(i=>i.amountCents)),pending=sum(invoices.filter(i=>i.status==='pending').map(i=>i.amountCents));
  eq(sum(Object.values(f.costs)),accrued,'competitor accrued costs reconstructed');
  eq(sum(Object.values(f.paidCosts)),paid,'competitor paid costs reconstructed');
  for(const [category,value]of Object.entries(f.costs))eq(value,sum(bills.filter(b=>b.category===category).map(b=>b.amountCents)),'competitor expense category reconciles');
  for(const [category,value]of Object.entries(f.paidCosts))eq(value,sum(bills.filter(b=>b.category===category&&b.paid).map(b=>b.amountCents)),'competitor paid expense category reconciles');
  eq(f.grossInvoicesCents,gross,'competitor gross invoicing');eq(f.grossCollectionsCents,collected,'competitor gross collection');eq(f.writtenOffCents,defaults,'competitor writeoffs');
  eq(gross,collected+defaults+pending,'competitor receivable conservation');
  let balance=f.openingCashCents,lastWeek=-1;const paidIndex=new Map(),collectedOnce=new Set();
  for(let n=0;n<cash.length;n++){
    const e=cash[n];ck(Number.isSafeInteger(e.amountCents),'integer competitor cash event');ck(e.week>=lastWeek,'chronological competitor cash events');lastWeek=e.week;
    balance+=e.amountCents;eq(balance,e.cashAfterCents,'competitor cash after every event');ck(balance>=0,'competitor cannot spend negative cash');
    if(e.type==='simulated_collection'){
      const i=invoiceMap.get(e.reference);ck(!!i,'collection references competitor invoice');ck(!collectedOnce.has(e.reference),'competitor invoice collected once');collectedOnce.add(e.reference);
      if(i){eq(e.amountCents,i.amountCents,'competitor collection equals invoice');eq(i.status,'collected','competitor collected status');eq(i.collectedWeek,e.week,'competitor collection week');ck(e.week>=i.dueWeek,'competitor collection not before due');}
    }else{
      const b=billMap.get(e.reference);ck(!!b,'payment references competitor bill');ck(!paidIndex.has(e.reference),'competitor bill paid once');paidIndex.set(e.reference,n);
      if(b){eq(e.amountCents,-b.amountCents,'competitor payment equals bill');eq(b.paid,true,'competitor liability paid flag');eq(b.paidWeek,e.week,'competitor payment week');ck(e.week>=b.dueWeek,'competitor bill not paid before due');}
    }
  }
  eq(balance,f.cashCents,'competitor final cash from events');eq(balance,f.openingCashCents+collected-paid,'competitor independent cash equation');
  eq(balance+pending-(accrued-paid)-f.openingCashCents,gross-defaults-accrued,'competitor equity excludes opening capital');
  const finalSummary=run.competitorSummary[id];
  for(const [key,value]of Object.entries({cashCents:balance,accepted:f.accepted,insolvent:f.insolvent,collectionsCents:collected,accruedCostCents:accrued}))eq(finalSummary[key],value,'supplement agrees with original competitor summary');
  for(const i of invoices){
    const j=jobMap.get(i.mission);ck(!!j,'competitor invoice references its own delivered mission');
    if(j){eq(j.accepted,true,'rejected competitor work never earns acceptance invoice');eq(j.invoiceCreated,true,'competitor accepted invoice flag');eq(j.priceCents,i.amountCents,'competitor invoice equals agreed price');eq(j.week,i.week,'competitor invoice issued on delivery');}
  }
  for(const j of jobs){
    eq(invoicesByMission.get(j.id)??0,j.accepted?1:0,'exactly accepted competitor jobs invoice');
    eq(deliveryByMission.get(j.id)??0,j.deliveryCostCents,'competitor job delivery-cost liability');
    if(f.insolvent)ck(j.week<=f.insolventWeek,'no competitor delivery after known insolvency week');
  }
  for(const [week,count]of byWeek(jobs,j=>j.week,()=>1))ck(count<=(id==='human'?c.humanSlotsPerWeek:c.aiSlotsPerWeek),'competitor weekly capacity binds',{week,count});
  for(const b of bills){
    ck(Number.isSafeInteger(b.amountCents)&&b.amountCents>=0,'nonnegative integer competitor liability');ck(b.dueWeek>=b.week,'competitor liability due after accrual');
    if(b.category==='refund'){
      const i=invoiceMap.get(b.reference);ck(!!i,'competitor refund references invoice');
      if(i){eq(i.status,'collected','refund requires collected invoice');eq(i.refund,true,'refund obligation was declared');eq(b.amountCents,i.amountCents,'refund is full contractual amount');eq(b.week,i.collectedWeek,'refund accrues at collection');eq(b.dueWeek,b.week+c.refundDelayWeeks,'refund due timing');}
    }
  }
  const automation=h.competitorActions.filter(x=>x.provider===id&&x.action==='adopt-automation');
  const cap=bills.filter(b=>b.category==='capability');eq(cap.length,automation.filter(x=>x.costCents>0).length,'competitor automation has exact liability count');
  for(const b of cap){
    const bi=bills.indexOf(b),ei=paidIndex.get(b.id);ck(ei!==undefined,'competitor automation paid before effect');
    if(ei!==undefined){
      const e=cash[ei],before=e.cashAfterCents-e.amountCents;
      const priorUnpaid=sum(bills.slice(0,bi).filter(x=>!paidIndex.has(x.id)||paidIndex.get(x.id)>ei).map(x=>x.amountCents));
      ck(before-priorUnpaid>=b.amountCents,'competitor automation affordable after preexisting obligations');
      eq(b.amountCents,c.competitorImitationCostCents,'competitor automation declared cost');
      eq(automation.filter(x=>x.week===b.week&&x.costCents===b.amountCents).length,1,'competitor automation action matches paid bill');
    }
  }
  const maps={cash:byWeek(cash,x=>x.week,x=>x.amountCents),collections:byWeek(cash.filter(x=>x.type==='simulated_collection'),x=>x.week,x=>x.amountCents),
    accrued:byWeek(bills,x=>x.week,x=>x.amountCents),paid:byWeek(bills.filter(x=>x.paid),x=>x.paidWeek,x=>x.amountCents),
    due:byWeek(bills,x=>x.dueWeek,x=>x.amountCents),issued:byWeek(invoices,x=>x.week,x=>x.amountCents),
    writtenOff:byWeek(invoices.filter(x=>x.status==='defaulted'),x=>x.dueWeek,x=>x.amountCents)};
  const running=Object.fromEntries(Object.keys(maps).map(k=>[k,0])),weekly=record.reconstructedWeeklyBalances[id];
  eq(weekly.length,h.balances.length,'competitor reconstruction horizon equals original');
  let end;
  for(let n=0;n<weekly.length;n++){
    const got=weekly[n],week=h.balances[n].week;eq(got.week,week,'same end-of-week reconstruction identity');
    for(const k of Object.keys(maps))running[k]+=maps[k].get(week)??0;
    const cashNow=f.openingCashCents+running.cash,obligations=running.accrued-running.paid,receivables=running.issued-running.collections-running.writtenOff;
    end={week,cashCents:cashNow,receivablesCents:receivables,obligationsCents:obligations,
      overdueObligationsCents:running.due-running.paid,accruedCostsCents:running.accrued,paidCostsCents:running.paid,
      grossInvoicesCents:running.issued,grossCollectionsCents:running.collections,writtenOffCents:running.writtenOff,
      cashLessExistingObligationsCents:cashNow-obligations,accruedProfitExcludingOpeningCashCents:running.issued-running.writtenOff-running.accrued,
      insolvent:f.insolvent&&f.insolventWeek<=week};
    for(const [k,value]of Object.entries(end))eq(got[k],value,'independent weekly competitor balance reconstruction');
    if(end.overdueObligationsCents>0)eq(end.insolvent,true,'overdue unpaid competitor obligation triggers insolvency');
  }
  for(const [k,value]of Object.entries(end))eq(record.finalAccounting[id][k],value,'final competitor account equals final reconstruction');
  add('competitorFirmAccounts');add('competitorInvoices',invoices.length);add('competitorBills',bills.length);add('competitorCashEvents',cash.length);add('competitorAutomationEvents',automation.length);add('reconstructedCompetitorWeeks',weekly.length);
}

for(const stage of completion.stages){
  context=stage.stage;
  const registered=source.stages.find(x=>x.id===stage.stage);
  eq(await digest(resolve(market,registered.originalArchive)),registered.originalArchiveSHA256,'original archive unchanged');
  eq(stage.originalArchiveSHA256,registered.originalArchiveSHA256,'stage original archive binding');
  eq(await digest(resolve(results,stage.supplement)),stage.supplementSHA256,'competitor supplement digest');
  const supplier=lines(resolve(results,stage.supplement))[Symbol.asyncIterator](),originalHash=createHash('sha256');
  let pairs=0,arms=0;
  for await(const line of lines(resolve(market,registered.originalArchive))){
    if(!line)continue;const original=JSON.parse(line);originalHash.update(line+'\n');pairs++;
    for(const arm of ['A','B','C']){
      const next=await supplier.next();ck(!next.done,'supplement row exists for every original arm');if(next.done)break;
      const row=JSON.parse(next.value),run=original.arms[arm];arms++;context=`${stage.stage}:${original.config.id}:${original.seed}:${arm}`;
      eq(row.stage,stage.stage,'supplement campaign identity');eq(row.scenario,original.config.id,'supplement scenario identity');eq(row.seed,original.seed,'supplement seed identity');eq(row.arm,arm,'supplement arm identity');
      eq(row.basis,'SIMULATED_REPORTING_ONLY','supplement remains simulated');eq(row.financialAuthority,'NONE','supplement grants no financial authority');eq(row.observedCustomerCollectionsCents,0,'competitor observed collections stay zero');
      eq(row.originalArchiveSHA256,registered.originalArchiveSHA256,'row archive binding');eq(row.originalPairedLineSHA256,sha(line),'original paired bytes independently hashed');
      eq(row.originalArmSHA256,sha(JSON.stringify(run)),'original arm independently hashed');eq(row.replayedArmSHA256,row.originalArmSHA256,'replayed original arm identity');eq(row.allOriginalFieldsMatchExactly,true,'all original fields equality flag');
      eq(Object.keys(row.competitors).sort().join(','),'ai,human','exact modeled competitor set');
      for(const id of ['human','ai'])auditFirm(row.competitors[id],id,row,run);
      add('enterpriseArmsMatched');
    }
    if(pairs%500===0)process.stdout.write(JSON.stringify({stage:stage.stage,auditedPairedWorlds:pairs,competitorAccounts:totals.competitorFirmAccounts,failedAssertions})+'\n');
  }
  context=stage.stage;eq((await supplier.next()).done,true,'no extra competitor supplement row');
  eq(pairs,registered.pairedWorlds,'complete paired-world count');eq(arms,registered.enterpriseRuns,'complete original-arm count');
  const originalDigest=originalHash.digest('hex');eq(originalDigest,stage.originalUncompressedJSONSHA256,'original uncompressed digest independently reconstructed');eq(originalDigest,stage.replayedUncompressedJSONSHA256,'every serialized original paired byte preserved');
  add('originalPairedWorldsMatched',pairs);
}
context='completion';eq(totals.originalPairedWorldsMatched,6480,'all original paired worlds');eq(totals.enterpriseArmsMatched,19440,'all original enterprise arms');eq(totals.competitorFirmAccounts,38880,'all human and AI competitor accounts');
const report={schema:'agi-alpha-independent-competitor-account-audit/v1',executedAt:new Date().toISOString(),
  reviewer:'Same-session independent economic reviewer; not organizationally independent.',passed:failedAssertions===0,failedAssertions,firstFailures,
  completionSHA256:await digest(resolve(results,'completion.json')),sourceManifestSHA256:await digest(resolve(market,'reporting/source-manifest.json')),
  originalCoreSHA256:await digest(resolve(market,'src/market.mjs')),counts:totals,checks,
  supplements:completion.stages.map(s=>({stage:s.stage,path:s.supplement,sha256:s.supplementSHA256})),
  originalCampaignsPreserved:true,newEconomicScenarios:0,observedCustomerCollectionsCents:0,
  scope:'Reporting-only recovery of native competitor accounting state from exact same-world replays. Original paired bytes and arm hashes independently verified; all competitor cash events, invoices, bills, automation affordability and separately reconstructed weekly balances reconciled.',
  limitation:'Derived weekly balances are post-hoc accounting reconstructions, not newly observed native history. This audit does not validate external buyer demand, monetary assumptions or field reliability.'};
writeFileSync(output,JSON.stringify(report,null,2)+'\n');
process.stdout.write(JSON.stringify({passed:report.passed,failedAssertions,counts:totals,completionSHA256:report.completionSHA256,firstFailures:firstFailures.slice(0,5)},null,2)+'\n');
process.exitCode=failedAssertions?1:0;
