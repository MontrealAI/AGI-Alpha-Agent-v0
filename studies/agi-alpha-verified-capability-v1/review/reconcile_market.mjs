#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Stream and reconcile stored worlds. This script never imports or runs the simulator.
// node review/reconcile_market.mjs --root . --output review/market-reconciliation-NEW.json
import {readFileSync,writeFileSync,existsSync,createReadStream,realpathSync,lstatSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createGunzip} from 'node:zlib';
import {createInterface} from 'node:readline';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const args=process.argv.slice(2),arg=(name,fallback)=>{const at=args.indexOf(name);return at<0?fallback:args[at+1];};
const ROOT=path.resolve(arg('--root',path.dirname(fileURLToPath(import.meta.url))+'/..'));
const output=path.resolve(ROOT,arg('--output','review/market-reconciliation-NEW.json'));
if(!output.startsWith(ROOT+path.sep)||existsSync(output))throw Error('FRESH_REVIEW_OUTPUT_INSIDE_STUDY_REQUIRED');
const started=performance.now(),cpuStarted=process.cpuUsage();
const load=p=>JSON.parse(readFileSync(path.join(ROOT,p),'utf8'));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const fileSHA=p=>sha(readFileSync(path.join(ROOT,p)));
const canonical=value=>JSON.stringify(value,(_key,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
const same=(a,b)=>canonical(a)===canonical(b),sum=values=>values.reduce((a,b)=>a+b,0);
let checks=0;const failures=[];
function check(ok,label,where=null,details=null){checks++;if(!ok)failures.push({check:label,where,details});}
function equivalent(a,b){
  if(typeof a==='number'&&typeof b==='number')return Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<=1e-8+Math.max(Math.abs(a),Math.abs(b))*1e-10;
  if(a===null||b===null||typeof a!=='object'||typeof b!=='object')return a===b;
  const ak=Object.keys(a).sort(),bk=Object.keys(b).sort();
  return same(ak,bk)&&ak.every(k=>equivalent(a[k],b[k]));
}
function distribution(values){
  const x=values.filter(v=>typeof v==='number'&&Number.isFinite(v)).sort((a,b)=>a-b),n=x.length;
  const mean=n?sum(x)/n:null;
  const q=p=>{if(!n)return null;const i=(n-1)*p;return x[Math.floor(i)]+(x[Math.ceil(i)]-x[Math.floor(i)])*(i%1);};
  const half=n>1?1.96*Math.sqrt(sum(x.map(v=>(v-mean)**2))/(n-1)/n):null;
  return {n,missing:values.length-n,mean,min:n?x[0]:null,p05:q(.05),median:q(.5),p95:q(.95),max:n?x.at(-1):null,
    negative:x.filter(v=>v<0).length,zero:x.filter(v=>v===0).length,positive:x.filter(v=>v>0).length,
    meanMC95Low:half===null?null:mean-half,meanMC95High:half===null?null:mean+half};
}
function funding(snapshot,where){
  check(snapshot.cashBoundCents===snapshot.cashCents-snapshot.unpaidObligationsCents-snapshot.reserveCents
    &&snapshot.generatedBoundCents===snapshot.collectedCents-snapshot.allAccruedCostsCents+snapshot.seedPaidOpeningHistoryCents
    &&snapshot.availableCents===Math.max(0,Math.min(snapshot.cashBoundCents,snapshot.generatedBoundCents)),
    'generated resources exclude seed balance and future receipts',where);
}
function prefix(run,beforeWeek){
  return Object.fromEntries(['cash','balances','invoices','bills','buyerChoices','jobs','investmentDecisions','investments','competitorActions','prices']
    .map(key=>[key,run.histories[key].filter(row=>row.week<beforeWeek).map(row=>{
      const copy=JSON.parse(JSON.stringify(row));if(key==='invoices'){delete copy.status;delete copy.collectedWeek;}
      if(key==='bills'&&copy.paidWeek>=beforeWeek){copy.paid=false;delete copy.paidWeek;}return copy;
    })]));
}
const summary=load('evidence/market-primary/summary.json'),execution=load('evidence/market-primary/execution.json');
const design=load('protocol/market-design.json'),freeze=load('protocol/market-freeze.json');
const production=load('evidence/production-summary.json'),calibration=load('evidence/market-primary/effect-calibration.json');
const bindings=load('market/asset-bindings.json'),admission=load('evidence/asset-admission.json'),costs=load('market/cost-assumptions.json');
const freezeHash=fileSHA('protocol/market-freeze.json');
check(summary.complete&&execution.complete&&execution.failure===null,'complete campaign');
check(freezeHash===summary.sourceFreezeSHA256&&freezeHash===execution.sourceFreezeSHA256,'market freeze custody');
check(freezeHash==='6faac0619fd656918db7a22e6ba2966f813abfacec7892eafaf22fdd32f1eec7','registered market edition');
check(freeze.marketOutcomesInspected===false&&freeze.productionFreezeSHA256===production.freeze_sha256,'pre-outcome source/production link');
check(freeze.files.length===194&&new Set(freeze.files.map(x=>x.path)).size===194,'194 distinct frozen market files');
for(const item of freeze.files){
  const full=path.resolve(ROOT,item.path),raw=readFileSync(full);
  check(realpathSync(full).startsWith(ROOT+path.sep)&&!lstatSync(full).isSymbolicLink()&&sha(raw)===item.sha256&&raw.length===item.bytes,'exact frozen market file',item.path);
}
check(execution.resources.wallSeconds<=180&&execution.resources.cpuSeconds<=180&&execution.noAutomaticRerun,'finite original campaign budget');
check(summary.actualCustomerCollectionsCents===0&&summary.actualTransactions===0&&summary.actualFullyLoadedCost===null
  &&summary.globalGraphAdoptionOverDirectD===null&&execution.observedReceipts===0&&execution.transactions===0,'actual money and global claims remain unidentified');
check(calibration.productionSHA256===fileSHA('evidence/production-summary.json'),'calibration bound to actual production');
const assetHashes={};
const primaryMean=arm=>{const a=production.arms[arm],primary=a.per_mission.filter(r=>r.cohort==='primary');return sum(primary.map(r=>r.cpu_seconds))/15+(a.cpu_seconds_total-sum(a.per_mission.map(r=>r.cpu_seconds)))/18;};
for(const arm of ['B','C']){
  const asset=bindings.assets[arm];
  for(const file of asset.files)check(fileSHA(file.path)===file.sha256,'actual asset source closure',arm+':'+file.path);
  assetHashes[arm]=sha(canonical(asset.files.map(({path,sha256})=>({path,sha256})).sort((a,b)=>a.path.localeCompare(b.path))));
  check(fileSHA(asset.admission_evidence_path)===asset.admission_evidence_sha256
    &&admission.admissions.some(r=>r.asset_id===asset.id&&r.source_manifest_sha256===assetHashes[arm]&&r.decision==='ADMIT'&&r.mode==='FIXTURE_ONLY'),
    'source-bound actual admission',arm);
  const effect=calibration.effects[arm],saving=primaryMean('A')-primaryMean(arm),microcents=Math.round(saving/3600*100000000);
  check(effect.assetSHA256===assetHashes[arm]&&effect.id===asset.id&&effect.acceptanceEvidenceSHA256===asset.admission_evidence_sha256,'calibrated asset identity',arm);
  check(equivalent(effect.measuredCpuSecondsSavedPerMission,saving)&&effect.unroundedComputeSavingsMicrocentsPerJob===microcents
    &&equivalent(effect.exactConditionalComputeCentsSavedPerMission,saving/3600*100)
    &&effect.primaryObservations===15&&effect.designedStressObservationsNotUsedForCalibration===3,'primary-only measured CPU calibration',arm);
  check(effect.effects.providerMinutesSaved===0&&effect.effects.customerReviewMinutesSaved===0
    &&effect.effects.computeAndToolCentsSaved===(Math.trunc(microcents/1000000)||0)&&effect.actualCompleteMonetaryCost===null,'no unmeasured human/trust/price benefit',arm);
  check(production.arms[arm].per_mission.every(r=>r.accepted&&r.asset_id===asset.id),'actual admitted asset used in fresh production',arm);
}
const compact=readFileSync(path.join(ROOT,'evidence/market-primary/compact-worlds.jsonl'),'utf8').trim().split('\n').map(line=>JSON.parse(line));
const compactByKey=new Map(compact.map(row=>[row.cell+'|'+row.seed,row]));
check(compact.length===1152&&compactByKey.size===1152,'1152 distinct compact paired worlds');
const expectedKeys=new Set();
for(const condition of design.conditions)for(const policy of design.policies)for(const profile of design.costProfileIds)for(const seed of design.seeds)
  expectedKeys.add(`${condition.id}__${policy.id}__${profile}|${seed}`);
check(expectedKeys.size===1152&&[...expectedKeys].every(key=>compactByKey.has(key)),'complete frozen cell/seed inventory');
const grouped=new Map(summary.cells.map(cell=>[cell.id,[]])),worldReceipts=[],rawHash=createHash('sha256');
let worlds=0,histories=0,cashEvents=0,balanceRows=0,oneoffCharges=0,modeledUses=0;
const totals={B:{attempted:0,admitted:0,operatingFunded:0,qualified:0,used:0},C:{attempted:0,admitted:0,operatingFunded:0,qualified:0,used:0}};
for await(const line of createInterface({input:createReadStream(path.join(ROOT,'evidence/market-primary/complete-worlds.jsonl.gz')).pipe(createGunzip()),crlfDelay:Infinity})){
  rawHash.update(line+'\n');const world=JSON.parse(line),key=world.cell+'|'+world.seed,small=compactByKey.get(key),before=failures.length;
  worlds++;check(expectedKeys.delete(key),'raw world registered once',key);
  check(Boolean(small)&&world.sourceFreezeSHA256===freezeHash&&world.seed===small.seed
    &&world.condition===small.condition&&world.policy===small.policy&&world.costProfile===small.costProfile,'raw/compact world custody',key);
  const paired=world.paired,arms=paired.arms,condition=design.conditions.find(c=>c.id===world.condition),policy=design.policies.find(p=>p.id===world.policy);
  check(paired.seed===world.seed&&paired.basis==='SIMULATED'&&paired.commonPrefixExact,'paired world identity',key);
  check(same(prefix(arms.A,paired.commonPrefixBeforeWeek),prefix(arms.B,paired.commonPrefixBeforeWeek))
    &&same(prefix(arms.A,paired.commonPrefixBeforeWeek),prefix(arms.C,paired.commonPrefixBeforeWeek)),'actual common preinvestment history',key);
  const project={A:arms.A.summary.profitCents};
  for(const arm of ['A','B','C']){
    histories++;const run=arms[arm],s=run.summary,h=run.histories,c=run.config,x=run.secondInvestment,short=small.arms[arm],where=key+'|'+arm;
    check(c.weeks===52&&c.initialCashCents===100000&&c.reserveCents===20000&&run.observedCustomerCollectionsCents===0&&s.actualRevenueCents===0,'finite original capital and no real receipts',where);
    check(Object.entries(condition.marketOverrides).every(([k,v])=>same(c[k],v)),'registered market condition',where);
    let cash=c.initialCashCents;const billMap=new Map(h.bills.map(b=>[b.id,b])),invoiceMap=new Map(h.invoices.map(i=>[i.id,i]));
    const seenReferences=new Set();
    for(const e of h.cash){
      cashEvents++;cash+=e.amountCents;check(Number.isSafeInteger(e.amountCents)&&cash===e.cashAfterCents&&cash>=0,'each cash transition',where);
      const token=e.type+'|'+e.reference;check(!seenReferences.has(token),'cash event not duplicated',where);seenReferences.add(token);
      if(e.type==='simulated_collection'){
        const invoice=invoiceMap.get(e.reference);check(invoice?.status==='collected'&&invoice.amountCents===e.amountCents&&invoice.collectedWeek===e.week,'collection has actual simulated invoice',where);
      }else{
        const bill=billMap.get(e.reference);check(['expense_payment','refund'].includes(e.type)&&bill?.paid&&bill.amountCents===-e.amountCents&&bill.paidWeek===e.week,'outflow has paid bill; no hidden capital',where);
      }
    }
    const accrued=sum(h.bills.map(b=>b.amountCents)),paid=sum(h.bills.filter(b=>b.paid).map(b=>b.amountCents)),unpaid=accrued-paid;
    const collected=sum(h.invoices.filter(i=>i.status==='collected').map(i=>i.amountCents)),receivable=sum(h.invoices.filter(i=>i.status==='pending').map(i=>i.amountCents));
    check(cash===s.finalCashCents&&cash===c.initialCashCents+collected-paid&&accrued===s.accruedCostsCents&&paid===s.paidCostsCents
      &&unpaid===s.obligationsCents&&collected===s.grossCollectionsCents,'terminal cash bills collections obligations',where);
    check(s.grossInvoicesCents===sum(h.invoices.map(i=>i.amountCents))&&s.writtenOffCents===sum(h.invoices.filter(i=>i.status==='defaulted').map(i=>i.amountCents))
      &&s.refundsCents===sum(h.bills.filter(b=>b.category==='refund').map(b=>b.amountCents)),'invoices writeoffs refunds',where);
    check(s.profitCents===cash+receivable-unpaid-c.initialCashCents&&s.availableOperatingSurplusCents===Math.min(cash-unpaid-c.reserveCents,collected-accrued-c.reserveCents),'profit and incumbent reserve accounting',where);
    for(const balance of h.balances){
      balanceRows++;const week=balance.week,events=h.cash.filter(e=>e.week<=week),bills=h.bills.filter(b=>b.week<=week);
      const bCash=c.initialCashCents+sum(events.map(e=>e.amountCents)),bAccrued=sum(bills.map(b=>b.amountCents));
      const bPaid=sum(bills.filter(b=>b.paid&&b.paidWeek<=week).map(b=>b.amountCents)),bUnpaid=bAccrued-bPaid;
      const bCollected=sum(events.filter(e=>e.type==='simulated_collection').map(e=>e.amountCents));
      check(balance.cashCents===bCash&&balance.accruedCostsCents===bAccrued&&balance.paidCostsCents===bPaid
        &&balance.obligationsCents===bUnpaid&&balance.cumulativeCollectionsCents===bCollected&&balance.reserveCents===c.reserveCents
        &&balance.availableCashCents===bCash-bUnpaid-c.reserveCents&&balance.earnedAvailableCents===Math.min(bCash-bUnpaid-c.reserveCents,bCollected-bAccrued-c.reserveCents),'each weekly balance and reserve stock',where+':'+week);
    }
    const jobs=h.jobs.filter(j=>j.provider==='enterprise');
    check(jobs.length===s.enterpriseAttempts&&jobs.filter(j=>j.accepted).length===s.enterpriseAccepted
      &&jobs.filter(j=>!j.accepted).length===s.enterpriseRejected&&h.jobs.every(j=>j.accepted||!j.invoiceCreated),'accepted jobs and rejected work receipts',where);
    for(const kind of ['cash','economic'])check(run.canonical[kind].summary.observed.revenue===0,'canonical observed revenue remains zero',where+':'+kind);
    check(run.canonical.economic.summary.scenario.operatingMargin===s.profitCents
      &&run.canonical.cash.summary.scenario.afterReserves===cash-c.initialCashCents-unpaid-c.reserveCents,'canonical ledger projections reconcile',where);
    const basic={accepted:s.enterpriseAccepted,attempts:s.enterpriseAttempts,rejected:s.enterpriseRejected,enterpriseProfitCents:s.profitCents,
      finalCashCents:s.finalCashCents,collectionsCents:s.grossCollectionsCents,obligationsCents:s.obligationsCents,refundsCents:s.refundsCents,reserveCents:c.reserveCents,insolvent:s.insolvent};
    check(Object.entries(basic).every(([k,v])=>same(short[k],v))&&short.actualCustomerCollectionsCents===0&&short.globalAdoptionOverDirectD===null,'compact monetary and outcome projection',where);
    if(arm==='A'){
      check(!x&&short.projectInclusiveProfitCents===s.profitCents&&short.actualAssetInvocations===0&&short.completeOneoffCents===0,'retain incumbent control',where);continue;
    }
    const profile=x.profile,asset=bindings.assets[arm],effect=calibration.effects[arm],multiplier=costs.profiles[world.costProfile].multiplier;
    check(profile.assetSHA256===assetHashes[arm]&&profile.id===asset.id&&profile.acceptanceEvidenceSHA256===asset.admission_evidence_sha256
      &&profile.tested&&profile.researchPrototypeConstructed&&profile.policy===policy.policy,'funded asset is actual admitted executed asset',where);
    check(same(profile.effects,effect.effects)&&profile.unroundedComputeSavingsMicrocentsPerJob===effect.unroundedComputeSavingsMicrocentsPerJob,'only measured incremental effects supplied',where);
    const categories=['priorDiscovery','discovery','rejectedCandidates','construction','verification','integration','researcherContribution','modelAndTools'];
    for(const category of categories){
      const expected=multiplier===null?null:sum(costs.rows.filter(r=>r.canonicalCategory===category).map(r=>Math.round(r.referenceCents[arm]*multiplier)));
      check(profile.costs[category].amountCents===expected&&profile.costs[category].basis===(multiplier===null?'unknown':'scenario'),'complete cost allocation',where+':'+category);
    }
    const upkeep=multiplier===null?null:Math.max(condition.profileOverrides.weeklyMaintenanceFloorCents||0,sum(costs.weeklyRows.map(r=>Math.round(r.referenceCents[arm]*multiplier))));
    check(profile.costs.weeklyMaintenance.amountCents===upkeep,'recurring maintenance stress allocation',where);
    const known=multiplier!==null,declared=known?sum(categories.map(k=>profile.costs[k].amountCents)):null;
    const paidOneoff=sum(Object.values(x.costsPaidByCategoryCents)),secondBills=h.bills.filter(b=>b.reference.startsWith('second:'+assetHashes[arm]+':'));
    for(const category of categories){
      const bills=secondBills.filter(b=>b.reference==='second:'+assetHashes[arm]+':'+category),amount=x.costsPaidByCategoryCents[category];
      check(bills.length===(amount>0?1:0)&&sum(bills.map(b=>b.amountCents))===(amount||0)&&bills.every(b=>b.paid),'oneoff category charged exactly once',where+':'+category);oneoffCharges+=bills.length;
    }
    const maintenanceBills=secondBills.filter(b=>b.reference.endsWith(':maintenance'));
    check(sum(maintenanceBills.map(b=>b.amountCents))===x.maintenanceAccruedCents
      &&x.completeRealizedSecondCostsCents===paidOneoff+x.maintenanceAccruedCents,'complete actual modeled second costs',where);
    check(x.completeCostProfilePriced===known&&x.declaredCompletePrototypeOneoffCostCents===declared
      &&x.outsideEnterprisePrototypeCostCents===(known?declared-paidOneoff:null)
      &&x.completedResearchCostCountedExactlyOnce===(known?true:null),'research contribution counted once, unknown stays null',where);
    project[arm]=known?s.profitCents-x.outsideEnterprisePrototypeCostCents:null;
    check(x.projectProfitAfterCompletedPrototypeCostsCents===project[arm]&&short.projectInclusiveProfitCents===project[arm],'project inclusive profit includes outside research',where);
    for(const decision of x.decisions){
      funding(decision.beforeSearch,where+':beforeSearch');if(decision.afterSearch)funding(decision.afterSearch,where+':afterSearch');
      if(decision.afterConstruction)funding(decision.afterConstruction,where+':afterConstruction');
      if(['invest-second-capability','operating-funded-unqualified-research-attempt'].includes(decision.action)){
        check(decision.afterSearch.availableCents>=decision.remainingConstructionCents&&decision.afterSearch.cashBoundCents>=decision.remainingConstructionCents,'construction paid from already generated resources',where);
        if(decision.action==='invest-second-capability')check(decision.expectedCompleteCostNetBenefitCents>0&&decision.financiallyAdmitted,'worthwhile investment gate',where);
      }
    }
    funding(x.terminalFunding,where+':terminal');
    const openingBills=h.bills.filter(b=>b.category==='capability'&&b.reference==='upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing'&&b.week===0&&b.paid&&b.paidWeek===0);
    const opening=sum(openingBills.map(b=>b.amountCents));
    check(x.terminalFunding.cashCents===cash&&x.terminalFunding.collectedCents===collected&&x.terminalFunding.allAccruedCostsCents===accrued
      &&x.terminalFunding.unpaidObligationsCents===unpaid&&x.terminalFunding.reserveCents===c.reserveCents
      &&x.terminalFunding.seedPaidOpeningHistoryCents===opening&&opening<=c.initialCashCents,'terminal funding reconstructs actual modeled books',where);
    const used=jobs.filter(j=>j.secondAssetSHA256===assetHashes[arm]);modeledUses+=used.length;
    check(used.length===x.actualAssetInvocationsInModel&&used.every(j=>j.secondAssetUsed===asset.id&&j.week>=x.availableWeek&&j.week<x.expiresWeek)
      &&(!x.failedIntegration||used.length===0),'same asset invoked only during validated useful lifetime',where);
    check(x.investmentPaidFromGeneratedResources===Boolean(x.modeledConstructionAttempted&&x.decisions.some(d=>['invest-second-capability','operating-funded-unqualified-research-attempt'].includes(d.action))),'funded attempt definition',where);
    const baseUnit=Math.round((c.commonResidualMinutes+c.assetResidualMinutes)*c.hourlyProviderCents/60)+c.computeAndToolCents;
    const secondUnit=Math.round((c.commonResidualMinutes+c.assetResidualMinutes-profile.effects.providerMinutesSaved)*c.hourlyProviderCents/60)+c.computeAndToolCents-profile.effects.computeAndToolCentsSaved;
    const direct=sum(used.map(j=>{const factor=j.qualityGood?1:c.failureCorrectionMultiplier;return Math.round(baseUnit*factor)-Math.round(secondUnit*factor);}));
    check(x.directAvoidedDeliveryCostCents===direct&&x.directNetBenefitCents===direct-x.completeRealizedSecondCostsCents
      &&x.directCostRepayment===Boolean(x.modeledConstructionAttempted&&used.length>0&&direct>0&&direct>=x.completeRealizedSecondCostsCents),'direct complete cost repayment',where);
    const residuals=used.map(j=>{const factor=j.qualityGood?1:c.failureCorrectionMultiplier,centSaving=Math.round((secondUnit+profile.effects.computeAndToolCentsSaved)*factor)-Math.round(secondUnit*factor);return profile.unroundedComputeSavingsMicrocentsPerJob*factor-centSaving*1000000;});
    check(equivalent(x.subcentComputeEffect.netSavingsNotRepresentedByCentLedgerMicrocents,sum(residuals))
      &&equivalent(x.subcentComputeEffect.maximumAbsoluteUnrepresentedUSD,sum(residuals.map(Math.abs))/100000000),'signed subcent residual retained',where);
    const mapped={completeCostsKnown:known,completeOneoffCents:declared,secondCostsPaidCents:x.completeRealizedSecondCostsCents,
      outsideResearchCostCents:x.outsideEnterprisePrototypeCostCents,maintenanceCents:x.maintenanceAccruedCents,
      attempted:x.modeledConstructionAttempted,financiallyAdmitted:x.financiallyAdmitted,fundedFromGeneratedResources:x.investmentPaidFromGeneratedResources,
      actualAssetInvocations:x.actualAssetInvocationsInModel,directAvoidedCostCents:direct,directCostRepayment:x.directCostRepayment,
      assetSHA256:assetHashes[arm],fundingCheckpoint:x.initialCheckpoint,terminalGeneratedResourcesCents:x.terminalFunding.availableCents,
      prototypeCostCountedOnce:x.completedResearchCostCountedExactlyOnce,firstDecision:x.decisions[0]??null,
      commitmentDecision:x.decisions.find(d=>['invest-second-capability','operating-funded-unqualified-research-attempt'].includes(d.action))??null,
      subcentComputeResidualMicrocents:x.subcentComputeEffect.netSavingsNotRepresentedByCentLedgerMicrocents,
      subcentComputeAbsoluteResidualUSD:x.subcentComputeEffect.maximumAbsoluteUnrepresentedUSD};
    check(Object.entries(mapped).every(([k,v])=>same(short[k],v)),'compact second-investment source projection',where);
    const forecast=x.decisions.find(d=>Object.hasOwn(d,'forecastUses'));
    const thresholdInputs=[declared,forecast?.forecastMaintenanceCents??null,forecast?.expectedForgoneContributionCents??null,
      forecast?.forecastUses??null,effect.exactConditionalComputeCentsSavedPerMission];
    let threshold=null,thresholdStatus='UNKNOWN_COMPLETE_COST_OR_WORKLOAD';
    if(thresholdInputs.every(v=>v!==null&&Number.isFinite(v))){
      if(forecast.forecastUses<=0)thresholdStatus='NO_FORECAST_WORKLOAD';
      else{
        thresholdStatus='HYPOTHETICAL_UNMEASURED_THRESHOLD';
        threshold=Math.max(0,(declared+forecast.forecastMaintenanceCents+forecast.expectedForgoneContributionCents
          -forecast.forecastUses*effect.exactConditionalComputeCentsSavedPerMission*(1-c.expectedPassThrough))
          /(forecast.forecastUses*c.hourlyProviderCents/3600*(1-c.expectedPassThrough)));
      }
    }
    check(equivalent(short.hypotheticalHumanBreakEven.secondsPerUse,threshold)&&short.hypotheticalHumanBreakEven.status===thresholdStatus,
      'hypothetical threshold is arithmetic sensitivity only',where);
    const qualified=Boolean(x.invested&&known&&x.investmentPaidFromGeneratedResources&&used.length>0&&x.directCostRepayment&&project[arm]!==null&&project[arm]-project.A>0);
    check(paired.qualification[arm].conditionalModeledFinancialGatePassed===qualified
      &&paired.qualification[arm].projectInclusiveIncrementCents===(project[arm]===null?null:project[arm]-project.A),'no success inferred from funding or graph growth alone',where);
    totals[arm].attempted+=Number(x.modeledConstructionAttempted);totals[arm].admitted+=Number(x.financiallyAdmitted);
    totals[arm].operatingFunded+=Number(x.investmentPaidFromGeneratedResources);totals[arm].qualified+=Number(qualified);totals[arm].used+=used.length;
  }
  const causal={B_minus_A_profitCents:arms.B.summary.profitCents-arms.A.summary.profitCents,C_minus_A_profitCents:arms.C.summary.profitCents-arms.A.summary.profitCents,
    B_minus_C_profitCents:arms.B.summary.profitCents-arms.C.summary.profitCents,
    B_minus_A_projectInclusiveProfitCents:project.B===null?null:project.B-project.A,C_minus_A_projectInclusiveProfitCents:project.C===null?null:project.C-project.A,
    B_minus_C_projectInclusiveProfitCents:project.B===null||project.C===null?null:project.B-project.C,
    B_minus_A_accepted:arms.B.summary.enterpriseAccepted-arms.A.summary.enterpriseAccepted,C_minus_A_accepted:arms.C.summary.enterpriseAccepted-arms.A.summary.enterpriseAccepted};
  check(same(causal,paired.causal)&&same({...causal,C_minus_B_projectInclusiveProfitCents:causal.B_minus_C_projectInclusiveProfitCents===null?null:-causal.B_minus_C_projectInclusiveProfitCents},small.causal)
    &&same(paired.qualification,small.qualification),'all paired causal projections and qualification preserved',key);
  grouped.get(world.cell).push(small);worldReceipts.push({cell:world.cell,seed:world.seed,passed:failures.length===before});
}
check(worlds===1152&&histories===3456&&expectedKeys.size===0&&execution.completedWorlds===worlds&&summary.completedWorlds===worlds,'all complete raw histories retained');
check(rawHash.digest('hex')===execution.rawWorldsSHA256&&fileSHA('evidence/market-primary/complete-worlds.jsonl.gz')===execution.compressedWorldsSHA256,'raw and compressed archive identities');
const numericFields=['accepted','attempts','rejected','enterpriseProfitCents','projectInclusiveProfitCents','finalCashCents','collectionsCents','obligationsCents','completeOneoffCents','secondCostsPaidCents','outsideResearchCostCents','maintenanceCents','actualAssetInvocations','directAvoidedCostCents','terminalGeneratedResourcesCents','subcentComputeResidualMicrocents','subcentComputeAbsoluteResidualUSD'];
for(const cell of summary.cells){
  const rows=grouped.get(cell.id);check(rows.length===24&&cell.completedWorlds===24,'24 paired seeds per cell',cell.id);
  for(const arm of ['A','B','C']){
    for(const field of numericFields)check(equivalent(distribution(rows.map(r=>r.arms[arm][field])),cell.arms[arm][field]),'independent cell distribution',cell.id+'|'+arm+'|'+field);
    check(equivalent(distribution(rows.map(r=>r.arms[arm].hypotheticalHumanBreakEven.secondsPerUse)),cell.arms[arm].hypotheticalHumanSecondsForRepayment),'hypothetical threshold distribution stays separate',cell.id+'|'+arm);
    for(const field of ['insolvent','attempted','financiallyAdmitted','fundedFromGeneratedResources','directCostRepayment'])
      check(cell.arms[arm].counts[field]===rows.filter(r=>r.arms[arm][field]).length,'cell event count',cell.id+'|'+arm+'|'+field);
    check(cell.arms[arm].conditionalNativeFinancialGatePasses===(arm==='A'?0:rows.filter(r=>r.qualification[arm].conditionalModeledFinancialGatePassed).length),'cell qualifying investment count',cell.id+'|'+arm);
  }
  for(const field of Object.keys(cell.causal))check(equivalent(distribution(rows.map(r=>r.causal[field])),cell.causal[field]),'paired cell difference distribution',cell.id+'|'+field);
}
const cpu=process.cpuUsage(cpuStarted);
const report={schema:'agi-alpha-independent-market-reconciliation/v1',status:failures.length?'FINDINGS':'PASS',source_freeze_sha256:freezeHash,
  script_sha256:sha(readFileSync(fileURLToPath(import.meta.url))),checks,failed_checks:failures.length,failures,
  paired_worlds:worlds,enterprise_histories:histories,passed_worlds:worldReceipts.filter(r=>r.passed).length,source_files_verified:freeze.files.length,
  cash_events_reconciled:cashEvents,balance_rows_reconciled:balanceRows,second_oneoff_bills_reconciled:oneoffCharges,modeled_second_asset_uses:modeledUses,
  investment_results:totals,worlds:worldReceipts,review_resources:{elapsed_seconds:(performance.now()-started)/1000,cpu_seconds:(cpu.user+cpu.system)/1e6,
    simulator_executions:0,new_production_executions:0,model_calls_in_script:0,network_requests:0,actual_collections:0},
  scope:'Independent streaming arithmetic/source/custody audit of all frozen market histories, compact records and cell summaries. Simulator never imported or rerun.',
  limitations:['Same-session independent review, not observed market validation or external peer review.','All modeled money stays separate from actual zero collections. Complete actual cost and global adoption over direct D remain unknown.',
    'Cash transitions, weekly stocks, canonical projections and investment records are reconciled; this does not establish that buyer or competitor behavioral assumptions match a real market.']};
writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:report.status,checks,failed_checks:failures.length,paired_worlds:worlds,enterprise_histories:histories,investment_results:totals,resources:report.review_resources,output}));
if(failures.length)process.exitCode=2;
