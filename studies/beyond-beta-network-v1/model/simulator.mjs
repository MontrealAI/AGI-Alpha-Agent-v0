// SPDX-License-Identifier: Apache-2.0
// New prospective research driver. No live models, customer work or transactions.
import {createHash} from 'node:crypto';
import {BASE,JOB_CLASSES,AGENTS,ASSETS} from './config.mjs';
import {planJob,reserveJob,planCampaignReview,planAuxiliary,planConstruction,paidJobCostComponents} from './workflow.mjs';
import {reserveAlpha,planAlpha,aggregatePlans} from './alpha_probe.mjs';
import {createModeledNetwork} from '../graph/simulation_adapter.mjs';
import {SCHEMA,replayLedger} from '../upstream/canonical/shadow-ledger.mjs';

export const cents=x=>Math.round(x*100);
const sum=a=>a.reduce((s,x)=>s+x,0),clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
export function random(seed,...labels){
  const str=[seed,...labels].join('|');let h=2166136261;
  for(let i=0;i<str.length;i++)h=Math.imul(h^str.charCodeAt(i),16777619);
  h^=h>>>16;h=Math.imul(h,0x7feb352d);h^=h>>>15;h=Math.imul(h,0x846ca68b);h^=h>>>16;
  return (h>>>0)/4294967296;
}
const normal=(seed,...p)=>Math.sqrt(-2*Math.log(Math.max(1e-12,random(seed,...p,'u'))))*Math.cos(2*Math.PI*random(seed,...p,'v'));
function poisson(lambda,seed,...p){let k=0,t=1;const stop=Math.exp(-lambda);do{t*=random(seed,...p,k++);}while(t>stop&&k<500);return k-1;}
function choose(rows,u,key='share'){let s=0;return rows.find(r=>(s+=r[key])>u)??rows.at(-1);}
const percentile=(a,p)=>{const b=a.filter(Number.isFinite).sort((x,y)=>x-y);return b.length?b[Math.floor((b.length-1)*p)]:null;};
const blankCaps=()=>({representation:false,certificate:false,experiment:false,recourse:false});

export function generateWorld(C,seed){
  const market=Math.exp(C.marketSpread*normal(seed,'market')-C.marketSpread**2/2);
  const weeks=[];let id=0;
  for(let w=0;w<C.weeks;w++){
    const downturn=(w>=40&&w<56&&random(seed,'downturn')<.25)?.55:1;
    const count=poisson(C.prospectsMonthly*12/52*market*downturn,seed,'arrivals',w);
    const rows=[];
    for(let i=0;i<count;i++){
      const jid=`j${id++}`,t=choose(JOB_CLASSES,random(seed,jid,'class'));
      const a=choose(AGENTS,random(seed,jid,'agent'),'weight');
      const value=C.buyerValueMedian*t.valueFactor*Math.exp(C.buyerValueSpread*normal(seed,jid,'value'));
      rows.push({id:jid,week:w,classId:t.id,complexity:t.complexity,
        humanPriceCents:cents(C.humanReference*t.humanFactor),valueCents:cents(value),
        deadline:Math.max(1,Math.round(t.deadline*(C.deadlineMultiplier??1))),agent:AGENTS.indexOf(a),
        scopeSupported:random(seed,jid,'scope')<C.scopeSupport,
        repeat:random(seed,jid,'repeat')<C.repeatProbability,
        commodity:random(seed,jid,'commodity')<C.commodityShare,
        improvable:random(seed,jid,'improvable')<(C.improvableFraction??.65),
        trustCents:cents(C.trustMax*random(seed,jid,'trust')),urgency:random(seed,jid,'urgency')});
    }
    weeks.push(rows);
  }
  return {seed,market,weeks,potentialProspects:id};
}

export function buyerChoice(C,j,priceCents,perceivedQuality,quotedWeeks,completionBelief=C.initialCompletionBelief){
  const V=j.commodity?Math.min(j.valueCents,cents(2500)):j.valueCents;
  const loss=cents(C.businessLossBeyondValue);
  const switchCost=cents(C.switchingCost*(j.repeat?C.repeatSwitchFactor:1));
  const humanDelay=cents(C.buyerDelayCostWeekly*C.humanDeliveryWeeks*j.urgency);
  const aiDelay=cents(C.buyerDelayCostWeekly*quotedWeeks*j.urgency);
  // Matched contingent-acceptance convention: price is due only on an accepted artifact.
  // Completion and conditional material correctness are separate beliefs; lost value is not charged twice.
  const ai=completionBelief*(perceivedQuality*V-priceCents)-switchCost-j.trustCents-(1-completionBelief*perceivedQuality)*loss-aiDelay;
  const human=C.humanCompletionBelief*(C.humanQuality*V-j.humanPriceCents)-(1-C.humanCompletionBelief*C.humanQuality)*loss-humanDelay;
  const postpone=.05*(1-j.urgency)*V-cents(300);
  const values={ai,human,postpone,decline:0};
  const choice=Object.keys(values).sort((a,b)=>values[b]-values[a]||['human','postpone','decline','ai'].indexOf(a)-['human','postpone','decline','ai'].indexOf(b))[0];
  return {choice,utilitiesCents:values,perceivedQuality,completionBelief,lossCents:loss};
}

function resourceOf(plan,reserved=true){
  const r=reserved?(plan.reservedResources??plan.resources):plan.resources;
  const t=reserved?(plan.reservedTokens??plan.tokens):plan.tokens;
  return {input:t.input,output:t.output,cpu:r.cpuHours,validation:r.validatorCpuHours,hours:r.serviceHours};
}

export function simulate(config,policy,seed,{retain=true,ablation='none'}={}){
  const C={...BASE,...config},P={...policy};
  if(ablation==='no-investment'||ablation==='beta-only')P.allowInvestment=false;
  if(ablation==='no-bundle')P.allowBundles=false;
  if(ablation==='no-meta')P.allowMeta=false;
  if(ablation==='no-separate-research')P.allowSeparateResearch=false;
  if(ablation==='no-sharing'||ablation==='alpha-local')P.allowSharing=false;
  if(ablation==='static-beta')C.betaUpgradeWeek=C.weeks+1;
  if(ablation==='no-alpha-effect'){C.bundleEffect=1;C.familyScreenIncrement=0;C.certificateMechanicalDetection=C.mechanicalDetection;}
  let W={...C,betaResourceFactor:1,betaBundleAbsorption:0,betaExperimentAbsorption:0},betaVersion=C.betaVersion;
  const digest=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
  const network=createModeledNetwork({members:AGENTS.map(a=>a.id),betaVersion,
    policyVersion:'beyond-beta-alpha-policy-v1',scopeDigest:digest('optimization-prototype-v1'),
    environmentDigest:digest({workflow:'beyond-beta-workflow-v1',cpu:C.cpuHoursWeekly,input:C.inputQuotaWeekly,output:C.outputQuotaWeekly})});
  const forbiddenAssets=new Set(ablation==='representation-only'?['certificate','experiment','recourse']:
    ablation==='certificate-only'?['representation','experiment','recourse']:[]);
  const world=generateWorld(C,seed),horizon=C.weeks+C.runoffWeeks;
  const histories={cash:[],bills:[],invoices:[],balances:[],jobs:[],offers:[],decisions:[],campaigns:[],transfers:[],capacity:[],events:[],auxiliary:[],alphaAssessments:[],revalidations:[],network:[],paidCandidates:[],failureMemory:[]};
  const slots=Array.from({length:horizon+32},()=>({slots:0,input:0,output:0,cpu:0,validation:0,hours:0}));
  const limits={slots:C.concurrency,input:C.inputQuotaWeekly,output:C.outputQuotaWeekly,
    cpu:C.cpuHoursWeekly,validation:C.validatorHoursWeekly,hours:C.concurrency*C.hoursWeekly};
  let cash=cents(C.seedCapital),accrued=0,paid=0,collections=0,refunds=0,unpaid=0,commitment=0;
  let minCash=cash,insolvent=false,stoppedWeek=null,stopReason=null,seq=0,goodReports=0,badReports=0,
    completedReports=0,acceptedReports=0;
  const pending=[],assets=[],known=AGENTS.map(a=>({...a.baseline})),knownUntil=AGENTS.map(()=>({})),
    copyAvailable=AGENTS.map(()=>({})),attempts={},lastAttempt={},priorOffers=[];
  const total={potentialProspects:world.potentialProspects,contacted:0,aiChoices:0,humanChoices:0,postponed:0,declined:0,
    outOfScope:0,capacityRefusals:0,liquidityRefusals:0,marketThrottled:0,attemptedJobs:0,usefulAccepted:0,
    accepted:0,baselineOnly:0,abstained:0,materialErrors:0,latentAcceptedErrors:0,retries:0,newlyFeasible:0,
    invoicedCents:0,customerSavingsCents:0,successfulCampaigns:0,failedCampaigns:0,revocations:0,
    automatedProviderHumanHours:0,discoveryEvaluations:0,waitDecisions:0,abandonedCandidates:0,transfers:0,
    transferFailures:0,independentlyValidatedCampaigns:0,alphaRejected:0,alphaRetired:0,networkAvailableRecords:0,
    automatedRecoveries:0,unresolvedRecoveries:0,quarantinedJobs:0,betaVersionChanges:0};
  const activeAssets=w=>assets.filter(a=>a.admitted&&a.readyWeek<=w&&w<a.expiryWeek&&!a.revoked&&!a.suspended&&a.betaVersion===betaVersion);
  const maintenancePlan=planAuxiliary(C,'maintenance'),revalidationPlan=planAuxiliary(C,'revalidation');
  const transferPlan=planAuxiliary(C,'transfer_adaptation');
  const maintenanceEarmark=w=>sum(assets.filter(a=>!a.revoked&&w<a.expiryWeek&&(w<a.readyWeek||a.admitted)).map(a=>{
    let amount=0;
    for(let t=Math.max(w,a.readyWeek);t<a.expiryWeek;t++){
      if(t>(a.lastMaintenanceWeek??-1))amount+=a.maintenanceCents;
      if(t>a.readyWeek&&(t-a.readyWeek)%C.assetRevalidationWeeks===0&&t>(a.lastRevalidationWeek??-1))amount+=a.revalidationReserveCents??revalidationPlan.costCents;
    }
    return amount;
  }));
  const netProfit=()=>collections-refunds-accrued;
  const reserves=w=>cents(C.minimumCashReserve*P.reserveFactor)+Math.round(Math.max(0,netProfit())*C.taxReserve)+
    Math.round(sum(histories.invoices.filter(i=>i.collectedWeek!==null&&i.collectedWeek>w-6).map(i=>i.amountCents))*C.refundReserve);
  function funds(w){const obligations=unpaid,protectedCents=reserves(w)+maintenanceEarmark(w)+commitment;
    const liquid=Math.max(0,cash-obligations-protectedCents);
    return {cashCents:cash,unpaidCents:unpaid,reservedExecutionCents:commitment,maintenanceEarmarkCents:maintenanceEarmark(w),
      reservesCents:reserves(w),availableCents:liquid,
      earnedAvailableCents:Math.max(0,Math.min(liquid,netProfit()-protectedCents))};}
  function cashEvent(week,type,amountCents,reference){cash+=amountCents;if(cash<0)throw Error('Negative cash');
    minCash=Math.min(minCash,cash);histories.cash.push({id:`cash${seq++}`,week,type,amountCents,reference,cashAfterCents:cash});}
  function bill(week,amountCents,category,reference,lane=null){if(!Number.isSafeInteger(amountCents)||amountCents<0)throw Error('Invalid bill');
    const b={id:`bill${seq++}`,week,amountCents,category,reference,lane:lane??(category==='delivery'?'A_paid_job':category==='maintenance'?'B_retention_reuse':category==='capability'?'B_retention_reuse':'common_business'),paid:false,paidWeek:null};
    histories.bills.push(b);accrued+=amountCents;
    if(cash-commitment>=amountCents){b.paid=true;b.paidWeek=week;paid+=amountCents;cashEvent(week,'expense_payment',-amountCents,b.id);}else{unpaid+=amountCents;insolvent=true;}
    return b;
  }
  function payUnpaid(w){for(const b of histories.bills.filter(b=>!b.paid))if(cash-commitment>=b.amountCents){
    b.paid=true;b.paidWeek=w;unpaid-=b.amountCents;if(b.category!=='refund')paid+=b.amountCents;
    cashEvent(w,b.category==='refund'?'refund_payment':'expense_payment',-b.amountCents,b.id);}}
  function capsFor(ai,w,throughWeek=w,excludeId=null){const result={...known[ai]};
    for(const k of Object.keys(result))if(knownUntil[ai][k]!==undefined&&knownUntil[ai][k]<=throughWeek)result[k]=false;
    for(const a of activeAssets(w))if(a.id!==excludeId&&a.recipients.includes(ai)&&a.expiryWeek>throughWeek&&
      network.available({id:a.id,member:AGENTS[ai].id,week:w})&&
      (a.lastRevalidationWeek??a.readyWeek)+C.assetRevalidationWeeks>throughWeek)for(const k of a.keys)result[k]=true;
    if(ablation==='no-representation')result.representation=known[ai].representation;
    if(ablation==='no-certificate')result.certificate=known[ai].certificate;
    return result;}
  function booking(resource,w,deadline,apply=false,minDuration=1){
    const duration=Math.max(minDuration,1,...Object.keys(resource).map(k=>Math.ceil(resource[k]/(k==='hours'?C.hoursWeekly:limits[k]))));
    if(duration>deadline)return null;
    for(let start=w;start+duration<=Math.min(horizon,w+deadline);start++){
      let fits=true;for(let t=start;t<start+duration;t++){
        if(slots[t].slots+1>limits.slots)fits=false;
        for(const k of Object.keys(resource))if(slots[t][k]+resource[k]/duration>limits[k]+1e-7)fits=false;
      }
      if(fits){if(apply)for(let t=start;t<start+duration;t++){slots[t].slots++;for(const k of Object.keys(resource))slots[t][k]+=resource[k]/duration;}
        return {start,finish:start+duration,duration,queueWeeks:start-w,resources:resource};}
    }
    return null;
  }
  function auxiliary(plan,w,kind,reference,category='business',extraCents=0,releaseOwnEarmarkCents=0){
    const r=resourceOf(plan,false),f=funds(w);
    if(f.availableCents+releaseOwnEarmarkCents<plan.costCents+extraCents||cash-commitment<plan.costCents+extraCents)return null;
    if(Object.keys(r).some(k=>slots[w][k]+r[k]>limits[k]+1e-7))return null;
    for(const k of Object.keys(r))slots[w][k]+=r[k];
    const b=bill(w,plan.costCents+extraCents,category,reference);
    histories.auxiliary.push({week:w,kind,reference,resources:r,costCents:b.amountCents,billId:b.id,plan});
    return b;
  }
  function priceFor(j,w){const occupied=slots[w].slots/C.concurrency;
    const ratio=clamp(P.priceRatio+P.scarcity*(occupied-.5),.25,1);
    return {ratio,priceCents:Math.round(j.humanPriceCents*ratio)};}
  function qualityBelief(){const empirical=(goodReports+C.initialPerceivedQuality*C.priorReputationWeight)/(goodReports+badReports+C.priorReputationWeight);
    return clamp(C.initialPerceivedQuality*(1-C.reputationFeedback)+empirical*C.reputationFeedback,.4,.98);}
  function completionBelief(){return clamp((acceptedReports+C.initialCompletionBelief*C.priorReputationWeight)/(completedReports+C.priorReputationWeight),.02,.98);}
  function transferValue(keys,ai,w,life){
    const before=capsFor(ai,w),after={...before};for(const k of keys)after[k]=true;
    const rows=priorOffers.filter(o=>o.agent===ai&&o.choice==='ai'&&o.week>=w-C.forecastWindow);
    const observedWeeks=Math.max(4,Math.min(w,C.forecastWindow));
    const forecastReuse=rows.length/observedWeeks*life;let benefit=0;
    for(const o of rows){const old=reserveJob(W,o,before),next=reserveJob(W,o,after);
      benefit+=Math.max(0,old.costCents-next.costCents)*.6;
      const ro=resourceOf(old),rn=resourceOf(next);
      if(o.capacityRefused&&Object.keys(ro).some(k=>rn[k]<ro[k]-1e-7))benefit+=Math.max(0,o.priceCents-next.costCents)*.1;
    }
    return {forecastReuse,expectedBenefitCents:Math.round(benefit/observedWeeks*life*C.assetTransferSuccess*C.forecastHaircut)};
  }
  function trialResource(build,review){
    const a=resourceOf(build,false),b=resourceOf(review,true);
    return Object.fromEntries(Object.keys(a).map(k=>[k,a[k]+b[k]]));
  }
  function considerInvestment(w){
    if(!P.allowInvestment||w%C.discoveryEveryWeeks||w<4||stoppedWeek!==null)return;
    const originJob=histories.jobs.at(-1);if(!originJob)return;
    const lastOwner=AGENTS.findIndex(a=>a.id===originJob.agent);
    const allRecent=priorOffers.filter(o=>o.week>=w-C.forecastWindow);
    if(priorOffers.length<C.minimumObservedProspects)return;
    const evaluation=planAuxiliary(W,'investment_evaluation',{scale:1});
    if(!auxiliary(evaluation,w,'investment_evaluation','automated-invention-search-and-allocation','capability'))return;
    total.discoveryEvaluations++;
    const candidates=Object.keys(ASSETS).filter(k=>!forbiddenAssets.has(k)&&(P.allowMeta||k!=='experiment')&&
      !assets.some(a=>a.keys.includes(k)&&a.expiryWeek>w&&!a.revoked)&&(attempts[k]??0)<C.assetMaxAttempts&&
      (lastAttempt[k]===undefined||w-lastAttempt[k]>=C.assetRetryWait));
    const groups=P.allowSeparateResearch?candidates.map(k=>({keys:[k],sourceKind:'C_optional_research',raw:null})):[];
    if(P.allowSeparateResearch&&P.allowBundles&&candidates.includes('representation')&&candidates.includes('certificate'))groups.push({keys:['representation','certificate'],sourceKind:'C_optional_research',raw:null});
    const eligibleRaw=histories.paidCandidates.filter(raw=>!raw.attempted&&raw.rightsCleared&&
      raw.keys.every(k=>!forbiddenAssets.has(k)&&(P.allowMeta||k!=='experiment'))&&(P.allowBundles||raw.keys.length===1)&&
      !assets.some(a=>!a.revoked&&a.expiryWeek>w&&a.keys.some(k=>raw.keys.includes(k)))&&
      histories.invoices.some(i=>i.id===raw.invoiceId&&i.collectedWeek!==null&&i.collectedWeek<=w&&!i.refunded));
    // One observable, oldest paid artifact per declared capability family; no selection on latent productivity.
    const familySeen=new Set();for(const raw of eligibleRaw){const family=raw.keys.join('+');if(familySeen.has(family))continue;familySeen.add(family);groups.push({keys:raw.keys,sourceKind:'B_paid_job_retention',raw});}
    const reviews=[];
    for(const action of groups){
      const {keys,sourceKind,raw}=action,owner=raw?.owner??lastOwner;
      const recent=allRecent.filter(o=>P.allowSharing||o.agent===owner);
      const workUnits=sum(keys.map(k=>sourceKind==='B_paid_job_retention'?ASSETS[k].retentionWorkUnits:ASSETS[k].researchWorkUnits));
      const construction=planConstruction(sourceKind==='B_paid_job_retention'?{...W,assetConstructionMultiplier:C.retentionCostMultiplier}:W,{workUnits,keys});
      const alphaBound=reserveAlpha(W,{keys,offers:recent,available:ai=>capsFor(ai,w)});
      if(alphaBound.probeCases.length<6)continue;
      const revalidationBound=reserveAlpha(W,{keys,offers:recent,available:ai=>capsFor(ai,w),count:C.alphaRevalidationProbeCount});
      const resource=trialResource(construction,alphaBound);
      const d=Math.max(sourceKind==='B_paid_job_retention'?1:Math.max(...keys.map(k=>ASSETS[k].buildWeeks)),...Object.keys(resource).map(k=>Math.ceil(resource[k]/(k==='hours'?C.hoursWeekly:limits[k]))));
      const b=booking(resource,w,Math.min(C.weeks-w,Math.max(d+4,8)),false,d);
      const life=Math.min(C.assetLifetimeWeeks,C.weeks-(b?.finish??w+d));if(life<=4)continue;
      const buildCents=construction.costCents+alphaBound.reservedCostCents;
      const upkeep=life*(cents(C.assetMaintenanceWeekly*keys.length)+maintenancePlan.costCents)+Math.floor(life/C.assetRevalidationWeeks)*revalidationBound.reservedCostCents;
      const eligible=recent.filter(o=>o.choice==='ai'&&o.scopeSupported);
      const seen=Math.max(4,Math.min(w,C.forecastWindow));
      let benefit=0,newOffers=0,savings=0;
      for(const o of eligible){
        const before=capsFor(o.agent,w),after={...before};for(const k of keys)after[k]=true;
        const b0=reserveJob(W,o,before),a0=reserveJob(W,o,after),r0=resourceOf(b0),r1=resourceOf(a0);
        const oldDuration=Math.max(1,...Object.keys(r0).map(k=>Math.ceil(r0[k]/(k==='hours'?C.hoursWeekly:limits[k]))));
        const newDuration=Math.max(1,...Object.keys(r1).map(k=>Math.ceil(r1[k]/(k==='hours'?C.hoursWeekly:limits[k]))));
        const saving=Math.max(0,b0.costCents-a0.costCents)*.60;
        savings+=saving;benefit+=saving;
        if(oldDuration>o.deadline&&newDuration<=o.deadline){newOffers++;benefit+=Math.max(0,o.priceCents-a0.costCents-cents(150))*.50;}
        else if(o.capacityRefused&&newDuration<oldDuration)benefit+=Math.max(0,o.priceCents-a0.costCents-cents(150))*.15;
      }
      if(keys.includes('experiment'))for(const j of histories.jobs.filter(j=>j.finishWeek>=w-C.forecastWindow)){
        const diag=j.plan.diagnostics,rate=(diag.observedPostScreenMechanicalFailures??0)/Math.max(1,diag.candidates);
        const prune=clamp(rate*C.familyScreenIncrement*(1-W.betaExperimentAbsorption)/Math.max(.01,1-C.baselineScreenSensitivity));
        benefit+=cents(j.plan.resources.searchCpuHours*prune*(1-C.cheapScreenCpuFraction)*C.cpuPricePerHour);
      }
      const transfer=P.allowSharing?AGENTS[owner].weight+(1-AGENTS[owner].weight)*C.assetTransferSuccess:1;
      const overlapDecay=Math.exp(-(C.copyHazardWeekly+C.forecastBetaErosionWeekly)*life/2);
      const grossBenefit=Math.round(benefit/seen*life*C.forecastHaircut*C.meanAssetBelief*transfer*overlapDecay);
      const recentJobs=histories.jobs.filter(j=>j.finishWeek>=w-C.forecastWindow);
      const weeklyContribution=Math.max(0,sum(recentJobs.map(j=>(j.accepted?j.priceCents*(1-C.badDebt)*(1-C.paymentFee)*qualityBelief():0)-j.costCents))/seen);
      const recentCapacity=histories.capacity.filter(r=>r.week>=w-C.forecastWindow);
      const utilization=recentCapacity.length?Math.max(...Object.keys(limits).map(k=>sum(recentCapacity.map(r=>r[k]))/(recentCapacity.length*limits[k]))):0;
      const buildPressure=Math.max(1/C.concurrency,...Object.keys(resource).map(k=>resource[k]/(d*limits[k])));
      const displacement=clamp((buildPressure-(1-utilization))/Math.max(.1,utilization));
      const opportunityCost=Math.round(weeklyContribution*d*displacement);
      const expectedBenefit=grossBenefit-opportunityCost;
      const transferReserve=P.allowSharing?(cents(C.assetTransferCost)+transferPlan.costCents)*(AGENTS.length-1):0;
      const publicationReserve=cents(C.alphaPublicationCost+C.alphaDistributionCostPerMember*(P.allowSharing?AGENTS.length:1));
      const completeCost=buildCents+upkeep+transferReserve+publicationReserve;
      const snapshot=funds(w);
      reviews.push({week:w,keys,owner,sourceKind,rawCandidateId:raw?.id??null,originJobId:raw?.originJobId??originJob.id,
        originInvoiceId:raw?.invoiceId??null,jobDevelopmentAlreadyChargedCents:raw?.originJobCostCents??0,buildCents,upkeepCents:upkeep,
        transferReserveCents:transferReserve,publicationReserveCents:publicationReserve,completeCostCents:completeCost,
        forecastBenefitCents:expectedBenefit,forecastGrossBenefitCents:grossBenefit,forecastDisplacementCostCents:opportunityCost,
        forecastNetCents:expectedBenefit-completeCost,forecastObservedProspects:recent.length,
        forecastNewOfferObservations:newOffers,forecastSavingsCents:savings,forecastLifeWeeks:life,
        forecastEligibleUses:eligible.length/seen*life*C.forecastHaircut,
        benefitCostRatio:completeCost?expectedBenefit/completeCost:0,availableBeforeCents:snapshot.availableCents,
        earnedAvailableBeforeCents:snapshot.earnedAvailableCents,financialSnapshot:snapshot,
        affordable:snapshot.availableCents>=completeCost,capacityAvailable:Boolean(b),booking:b,
        workUnits,construction,resource,alphaBound,revalidationReserveCents:revalidationBound.reservedCostCents,
        invested:false,decision:'wait'});
    }
    reviews.sort((a,b)=>b.forecastNetCents-a.forecastNetCents||a.completeCostCents-b.completeCostCents);
    const best=reviews.find(r=>r.benefitCostRatio>P.hurdle&&r.affordable&&r.capacityAvailable);
    for(const r of reviews){if(r===best){r.invested=true;r.decision='invest';}else if(r.forecastNetCents<=0)r.decision='retain-cash';else r.decision='defer';histories.decisions.push(r);}
    if(!best){total.waitDecisions++;return;}
    const keys=best.keys,raw=histories.paidCandidates.find(r=>r.id===best.rawCandidateId),id=raw?`retained-${raw.id}`:`research-${keys.join('+')}-${Math.max(...keys.map(k=>attempts[k]??0))+1}`;
    if(raw)raw.attempted=true;
    if(!raw)for(const k of keys){attempts[k]=(attempts[k]??0)+1;lastAttempt[k]=w;}
    const productive=raw?raw.latentProductive:random(seed,id,'productive')<C.assetProductiveProbability;
    const recent=allRecent.filter(o=>P.allowSharing||o.agent===best.owner);
    const booked=booking(best.resource,w,Math.min(C.weeks-w,Math.max(best.booking.duration+4,8)),true,best.booking.duration);
    if(!booked)throw Error('Investment lost checked capacity');
    const expiryWeek=Math.min(C.weeks,booked.finish+C.assetLifetimeWeeks);
    const review=planAlpha(W,{id,keys,offers:recent,available:ai=>capsFor(ai,w),productive,
      lifecycleCostCents:best.completeCostCents,forecastEligibleUses:best.forecastEligibleUses,
      betaVersion,week:booked.finish,expiryWeek,
      assessmentBindings:network.assessmentBindings({id,keys,owner:AGENTS[best.owner].id,betaVersion,
        comparisonUniverse:AGENTS.map((a,i)=>({id:a.id,capabilities:capsFor(i,w)})),
        week:booked.finish,expiryWeek:Math.min(expiryWeek,booked.finish+C.alphaEvidenceWeeks),assetExpiryWeek:expiryWeek})
    },label=>random(seed,id,'alpha-evidence',label));
    const admitted=review.status.accepted&&random(seed,id,'false-rejection')>=C.assetFalseRejection;
    const constructionCents=best.construction.costCents+review.costCents;
    const constructionBill=bill(w,best.construction.costCents,'capability',id,raw?'B_retention_reuse':'C_optional_research');
    commitment+=review.reservedCostCents;
    const earnedFunded=Math.min(constructionCents,best.earnedAvailableBeforeCents);
    const a={id,keys,owner:best.owner,sourceKind:best.sourceKind,originJobId:best.originJobId,originInvoiceId:best.originInvoiceId,
      jobDevelopmentAlreadyChargedCents:best.jobDevelopmentAlreadyChargedCents,investWeek:w,readyWeek:booked.finish,expiryWeek,
      productive,admitted:false,plannedAdmission:admitted,recipients:[],availableTo:[],revoked:false,suspended:false,
      constructionCents,betaVersion,assessment:review.assessment,
      maintenanceCents:cents(C.assetMaintenanceWeekly*keys.length)+maintenancePlan.costCents,
      earnedFundedCents:earnedFunded,seedFundedCents:constructionCents-earnedFunded,uses:0,actualSavingsCents:0,
      maintenancePaidCents:0,lastMaintenanceWeek:null,lastRevalidationWeek:null,revokedWeek:null,
      reviewReserveCents:review.reservedCostCents,reviewCostCents:review.costCents,
      revalidationReserveCents:best.revalidationReserveCents,publicationReserveCents:best.publicationReserveCents};
    assets.push(a);histories.campaigns.push({id,keys,owner:best.owner,sourceKind:best.sourceKind,originJobId:best.originJobId,originInvoiceId:best.originInvoiceId,
      jobDevelopmentAlreadyChargedCents:best.jobDevelopmentAlreadyChargedCents,jobCostRechargedCents:0,week:w,
      productive,admitted,constructionCents,earnedFundedCents:earnedFunded,seedFundedCents:constructionCents-earnedFunded,
      independentTrials:review.diagnostics.heldOutTrials,fullTrialBudget:96,review,construction:best.construction,
      constructionBillId:constructionBill.id,reviewCostObservableWeek:booked.finish,booking:booked,forecast:best});
    pending.push({type:'asset-ready',week:booked.finish,id});
  }

  function retireAsset(a,reason,w){
    if(a.revoked)return;a.revoked=true;a.suspended=false;a.revokedWeek=w;a.retirementReason=reason;
    total.revocations++;total.alphaRetired++;
    network.retire(a.id,reason,w);
    histories.network.push({week:w,type:'retired',id:a.id,reason,betaVersion});
  }
  function recovery(w,reference){
    const plan=planAuxiliary(W,'recovery');
    if(auxiliary(plan,w,'bounded-recovery',reference,'delivery')){total.automatedRecoveries++;return true;}
    total.unresolvedRecoveries++;histories.events.push({week:w,type:'recovery-abstention',reference,reason:'bounded-cash-or-capacity'});return false;
  }
  function adoptAvailable(a,w){
    if(!a.admitted||a.revoked||a.suspended)return;
    for(let ai=0;ai<AGENTS.length;ai++){
      if((!P.allowSharing&&ai!==a.owner)||a.recipients.includes(ai))continue;
      if(!network.available({id:a.id,member:AGENTS[ai].id,week:w}))continue;
      const before=capsFor(ai,w,w,a.id),missing=a.keys.some(k=>!before[k]);
      if(!missing)continue;
      const v=transferValue(a.keys,ai,w,a.expiryWeek-w);
      const cost=cents(C.assetTransferCost)+transferPlan.costCents;
      if(v.expectedBenefitCents<=cost||!auxiliary(transferPlan,w,'transfer_adaptation',`adapt:${a.id}:${ai}:${w}`,'capability',cents(C.assetTransferCost)))continue;
      const success=random(seed,a.id,'transfer',ai,w)<C.assetTransferSuccess;
      histories.transfers.push({week:w,asset:a.id,agent:AGENTS[ai].id,equivalentBefore:false,availableBefore:true,
        forecastReuse:v.forecastReuse,expectedBenefitCents:v.expectedBenefitCents,costCents:cost,success});
      total.transfers++;if(success)a.recipients.push(ai);else total.transferFailures++;
    }
  }
  function scheduleRevalidation(a,w,reason){
    if(a.pendingRevalidation||a.revoked||w>=a.expiryWeek)return;
    a.suspended=true;
    const recent=priorOffers.filter(o=>o.week>=w-C.forecastWindow&&(P.allowSharing||o.agent===a.owner));
    const available=ai=>capsFor(ai,w,w,a.id);
    const bound=reserveAlpha(W,{keys:a.keys,offers:recent,available,count:C.alphaRevalidationProbeCount});
    const r=resourceOf(bound),book=booking(r,w,Math.min(C.assetRevalidationWeeks,a.expiryWeek-w),false);
    const own=a.revalidationReserveCents;
    if(bound.probeCases.length<6||!book||funds(w).availableCents+own<bound.reservedCostCents||cash-commitment<bound.reservedCostCents){
      retireAsset(a,'revalidation-not-affordable-or-feasible',w);return;
    }
    const life=a.expiryWeek-book.finish;
    if(life<=0){retireAsset(a,'useful-lifetime-ended',w);return;}
    const futureUpkeep=life*a.maintenanceCents+Math.floor(life/C.assetRevalidationWeeks)*bound.reservedCostCents;
    const forecastEligibleUses=recent.filter(o=>o.choice==='ai'&&o.scopeSupported).length/Math.max(4,Math.min(w,C.forecastWindow))*life*C.forecastHaircut;
    const id=a.id,review=planAlpha(W,{id,keys:a.keys,offers:recent,available,count:C.alphaRevalidationProbeCount,
      productive:a.productive,lifecycleCostCents:bound.reservedCostCents+futureUpkeep,forecastEligibleUses,
      betaVersion,week:book.finish,expiryWeek:a.expiryWeek,
      assessmentBindings:network.assessmentBindings({id,keys:a.keys,owner:AGENTS[a.owner].id,betaVersion,
        comparisonUniverse:AGENTS.map((ag,i)=>({id:ag.id,capabilities:available(i)})),week:book.finish,
        expiryWeek:Math.min(a.expiryWeek,book.finish+C.alphaEvidenceWeeks),assetExpiryWeek:a.expiryWeek})
    },label=>random(seed,id,'revalidation',w,label));
    booking(r,w,Math.min(C.assetRevalidationWeeks,a.expiryWeek-w),true);
    commitment+=bound.reservedCostCents;
    a.pendingRevalidation=true;a.lastRevalidationWeek=w;
    const row={id:`${id}:revalidation:${w}`,assetId:id,week:w,finishWeek:book.finish,reason,betaVersion,
      reservedCostCents:bound.reservedCostCents,costCents:review.costCents,booking:book,review};
    histories.revalidations.push(row);pending.push({type:'asset-revalidated',week:book.finish,id:row.id});
  }

  bill(0,cents(C.historicalResearchAllowance),'capability','declared-historical-research-allowance-not-observed-spending','historical_allowance');
  bill(0,cents(C.setupCost),'business','automated-factory-setup-and-initial-capability-inventory');
  for(let w=0;w<horizon;w++){
    if(w===C.betaUpgradeWeek){
      betaVersion=`${C.betaVersion}-hypothetical-upgrade`;
      W={...C,betaVersion,betaResourceFactor:C.betaUpgradeResourceFactor,betaBundleAbsorption:C.betaBundleAbsorption,betaExperimentAbsorption:C.betaExperimentAbsorption};
      network.advanceBeta(betaVersion,w);total.betaVersionChanges++;
      histories.network.push({week:w,type:'hypothetical-beta-upgrade',betaVersion,resourceFactor:W.betaResourceFactor,bundleAbsorption:W.betaBundleAbsorption});
      for(const a of assets.filter(a=>a.admitted&&!a.revoked&&a.expiryWeek>w))a.suspended=true;
    }
    // Collections and due completions are available before this week's new decisions.
    for(let eventIndex=0;eventIndex<pending.length;eventIndex++){
      const e=pending[eventIndex];if(e.week!==w||e.processed)continue;e.processed=true;
      if(e.type==='collection'){
        const invoice=histories.invoices.find(i=>i.id===e.id);
        if(!invoice.badDebt){collections+=invoice.amountCents;invoice.collectedWeek=w;cashEvent(w,'simulated_collection',invoice.amountCents,invoice.id);
          bill(w,Math.round(invoice.amountCents*C.paymentFee),'business',`payment-processing:${invoice.id}`);
          if(invoice.falsePass&&random(seed,invoice.jobId,'late-detection')<C.lateErrorDetection)pending.push({type:'refund',week:w+C.refundDelayWeeks,id:invoice.id});}
      }else if(e.type==='refund'){
        const invoice=histories.invoices.find(i=>i.id===e.id);invoice.refunded=true;refunds+=invoice.amountCents;badReports++;goodReports=Math.max(0,goodReports-1);
        // Refunds are contra-revenue; a separate refund payable is retained if cash is exhausted.
        const b={id:`refund${seq++}`,week:w,amountCents:invoice.amountCents,category:'refund',reference:invoice.id,paid:false,paidWeek:null};
        histories.bills.push(b);if(cash-commitment>=b.amountCents){b.paid=true;b.paidWeek=w;cashEvent(w,'refund_payment',-b.amountCents,b.id);}else{unpaid+=b.amountCents;insolvent=true;}
        recovery(w,`late-material-error:${invoice.jobId}`);
      }else if(e.type==='asset-ready'){
        const a=assets.find(a=>a.id===e.id);commitment-=a.reviewReserveCents;
        bill(w,a.reviewCostCents,'capability',`independent-alpha-assessment:${a.id}`);
        total.independentlyValidatedCampaigns++;
        histories.alphaAssessments.push({assetId:a.id,week:w,kind:'initial',...a.assessment});
        a.admitted=a.plannedAdmission&&a.betaVersion===betaVersion;
        if(a.admitted){
          const admitted=network.admit({id:a.id,keys:a.keys,owner:AGENTS[a.owner].id,assessment:a.assessment,readyWeek:w,expiryWeek:a.expiryWeek,comparisonUniverse:AGENTS.map((ag,i)=>({id:ag.id,capabilities:capsFor(i,w,w,a.id)}))});
          if(!admitted)a.admitted=false;
        }
        if(a.admitted){
          total.successfulCampaigns++;total.networkAvailableRecords++;a.recipients=[a.owner];a.availableTo=AGENTS.map(ag=>ag.id);
          a.lastRevalidationWeek=w;
          bill(w,a.publicationReserveCents,'capability',`network-publication-and-distribution:${a.id}`);
          histories.network.push({week:w,type:'modeled-admission',id:a.id,availableTo:a.availableTo,
            originJobId:a.originJobId,alphaLowerBoundCents:a.assessment.lowerLifetimeNetCents,betaVersion});
          adoptAvailable(a,w);
        }else{
          total.failedCampaigns++;total.abandonedCandidates++;total.alphaRejected++;
          histories.failureMemory.push({week:w,id:a.id,reason:'candidate-did-not-clear-current-alpha-gate',admitted:false});
          a.revoked=true;a.revokedWeek=w;a.retirementReason=a.betaVersion!==betaVersion?'stale-beta-at-completion':'alpha-assessment-rejected';
          histories.network.push({week:w,type:'candidate-rejected',id:a.id,reason:a.retirementReason,assessmentVerdict:a.assessment.verdict});
        }
      }else if(e.type==='asset-revalidated'){
        const r=histories.revalidations.find(r=>r.id===e.id),a=assets.find(a=>a.id===r.assetId);
        commitment-=r.reservedCostCents;bill(w,r.costCents,'maintenance',r.id);
        a.maintenancePaidCents+=r.costCents;a.pendingRevalidation=false;
        histories.alphaAssessments.push({assetId:a.id,week:w,kind:'revalidation',...r.review.assessment});
        if(!a.revoked&&r.betaVersion===betaVersion&&r.review.status.accepted&&
          network.revalidate({id:a.id,keys:a.keys,owner:AGENTS[a.owner].id,assessment:r.review.assessment,readyWeek:w,expiryWeek:a.expiryWeek,comparisonUniverse:AGENTS.map((ag,i)=>({id:ag.id,capabilities:capsFor(i,w,w,a.id)}))})){
          a.suspended=false;a.betaVersion=betaVersion;a.lastRevalidationWeek=w;a.assessment=r.review.assessment;
          a.revalidationReserveCents=r.reservedCostCents;
          histories.network.push({week:w,type:'modeled-revalidation',id:a.id,betaVersion,alphaLowerBoundCents:a.assessment.lowerLifetimeNetCents});
        }else retireAsset(a,'net-alpha-no-longer-supported',w);
      }else if(e.type==='job-start'){
        const task=pending.find(x=>x.type==='job'&&x.job.id===e.jobId);
        task.startChecked=true;
        task.cancelledBeforeStart=task.appliedAssetIds.some(id=>{
          const a=assets.find(a=>a.id===id);
          return a.revoked||a.suspended||a.betaVersion!==betaVersion||!network.available({id,member:AGENTS[task.job.agent].id,week:w});
        });
        if(task.cancelledBeforeStart){histories.events.push({week:w,type:'queued-reuse-rejected',jobId:e.jobId});recovery(w,`stale-queued-reuse:${e.jobId}`);}
      }else if(e.type==='job'){
        commitment-=e.reservedCents;const j=e.job;
        const plan=e.cancelledBeforeStart?{costCents:0,costDetailsCents:{},tokens:{input:0,output:0},resources:{cpuHours:0,searchCpuHours:0,validatorCpuHours:0,serviceHours:0},
          status:{code:'cancelled-stale-reuse',retries:0,abstained:true},diagnostics:{selected:null,candidates:0,observedPostScreenMechanicalFailures:0}}:e.plan;
        completedReports++;
        let accepted=plan.status.code==='improved'||(plan.status.code==='invalid_pass'&&plan.diagnostics.selected!==null);
        const falsePass=plan.status.code==='invalid_pass';
        const observedError=falsePass&&random(seed,j.id,'buyer-detection')<C.customerErrorDetection;
        if(observedError){accepted=false;badReports++;}
        const quarantined=e.appliedAssetIds.some(id=>{const a=assets.find(a=>a.id===id);return a.revoked||a.suspended||a.betaVersion!==betaVersion||!network.available({id,member:AGENTS[j.agent].id,week:w});});
        if(quarantined){accepted=false;total.quarantinedJobs++;}
        if(random(seed,j.id,'administrative-rejection')<.02)accepted=false;
        const support=cents(90+(accepted?45:0)+(observedError?180:0)+e.appliedAssetIds.length*C.alphaAccessCostPerUse);
        bill(w,plan.costCents+support,'delivery',j.id);
        if(observedError)recovery(w,`observed-error:${j.id}`);if(quarantined)recovery(w,`revoked-skill:${j.id}`);
        total.retries+=plan.status.retries;if(falsePass)total.materialErrors++;
        if(plan.status.abstained)total.abstained++;if(plan.status.code==='no_improvement')total.baselineOnly++;
        if(accepted){total.accepted++;acceptedReports++;goodReports++;if(falsePass)total.latentAcceptedErrors++;else total.usefulAccepted++;
          const invoice={id:`invoice-${j.id}`,jobId:j.id,week:w,amountCents:e.priceCents,dueWeek:w+C.collectionDelayWeeks,
            badDebt:random(seed,j.id,'default')<C.badDebt,collectedWeek:null,refunded:false,falsePass};
          histories.invoices.push(invoice);pending.push({type:'collection',week:invoice.dueWeek,id:invoice.id});
          total.invoicedCents+=e.priceCents;total.customerSavingsCents+=j.humanPriceCents-e.priceCents;
        }
        for(const id of e.appliedAssetIds){const a=assets.find(a=>a.id===id);a.uses++;
          // Resource savings are attributed against the same seeded workflow without newly acquired assets.
          a.actualSavingsCents+=Math.round((e.baselineCostCents-plan.costCents)/Math.max(1,e.appliedAssets));}
        histories.jobs.push({id:j.id,classId:j.classId,agent:AGENTS[j.agent].id,offerWeek:j.week,startWeek:e.booking.start,
          finishWeek:w,priceCents:e.priceCents,humanPriceCents:j.humanPriceCents,accepted,useful:accepted&&!falsePass,falsePass,
          resources:resourceOf(plan,false),reservedResources:e.booking.resources,queueWeeks:e.booking.queueWeeks,
          reservationDurationWeeks:e.booking.duration,reservedCashCents:e.reservedCents,costCents:plan.costCents+support,observedError,plan,capabilities:e.caps,
          appliedAssetIds:e.appliedAssetIds,
          baselineCostCents:e.baselineCostCents,newlyFeasible:e.newlyFeasible,betaVersion:e.betaVersion,quarantined,cancelledBeforeStart:Boolean(e.cancelledBeforeStart),
          paidJobComponents:{...paidJobCostComponents(plan),supportAndAccessCents:support,completePaidJobCostCents:plan.costCents+support}});
        if(accepted&&ablation!=='no-paid-learning'&&random(seed,j.id,'retained-candidate-emerges')<C.paidLearningProbability){
          const selector=random(seed,j.id,'candidate-family');
          const keys=j.classId==='kernel'?(selector<.70?['experiment']:['representation']):(selector<.70?['representation','certificate']:['certificate']);
          const rightsCleared=random(seed,j.id,'rights-cleared')<C.rightsClearedProbability;
          const raw={id:`paid-${j.id}`,originJobId:j.id,invoiceId:`invoice-${j.id}`,owner:j.agent,keys,week:w,
            originJobCostCents:plan.costCents+support,alreadyChargedToJob:true,additionalChargeAtEmergenceCents:0,
            rightsCleared,attempted:false,latentProductive:random(seed,j.id,'raw-candidate-productivity')<C.assetProductiveProbability*(falsePass?.25:1),
            status:rightsCleared?'unvalidated-candidate':'rights-restricted',semanticTruthUsedForRetentionChoice:false};
          histories.paidCandidates.push(raw);
          if(!rightsCleared)histories.failureMemory.push({week:w,id:raw.id,reason:'sharing-rights-not-cleared',admitted:false});
        }
      }
    }
    payUnpaid(w);
    for(const a of assets.filter(a=>a.admitted&&!a.revoked&&a.readyWeek<=w&&w<a.expiryWeek)){
      if(a.suspended||a.betaVersion!==betaVersion||(w-(a.lastRevalidationWeek??a.readyWeek))>=C.assetRevalidationWeeks){
        scheduleRevalidation(a,w,a.betaVersion!==betaVersion?'moving-beta':'freshness');
      }
      if(a.revoked)continue;
      const mb=auxiliary(maintenancePlan,w,'maintenance',a.id,'maintenance',cents(C.assetMaintenanceWeekly*a.keys.length),a.maintenanceCents);
      if(!mb){retireAsset(a,'maintenance-capacity-or-cash-unavailable',w);continue;}
      a.lastMaintenanceWeek=w;a.maintenancePaidCents+=mb.amountCents;
      if(!a.suspended&&w%4===0)adoptAvailable(a,w);
    }
    for(let ai=0;ai<AGENTS.length;ai++)for(const k of Object.keys(ASSETS)){
      if(knownUntil[ai][k]!==undefined&&knownUntil[ai][k]<=w)known[ai][k]=false;
      if(forbiddenAssets.has(k)||(k==='experiment'&&!P.allowMeta))continue;
      if(!known[ai][k]&&random(seed,'copy',ai,k,w)<C.copyHazardWeekly)copyAvailable[ai][k]=true;
      if(known[ai][k]||!copyAvailable[ai][k]||w>=C.weeks)continue;
      const life=Math.min(C.assetLifetimeWeeks,C.weeks-w),v=transferValue([k],ai,w,life);
      if(v.expectedBenefitCents<=cents(C.assetTransferCost)+transferPlan.costCents)continue;
      if(auxiliary(transferPlan,w,'copy_adaptation',`copy-adapt:${ai}:${k}`,'maintenance',cents(C.assetTransferCost))){
        const success=random(seed,'public-method-adaptation',ai,k,w)<C.assetTransferSuccess;
        if(success){known[ai][k]=true;knownUntil[ai][k]=w+life;for(const a of assets.filter(a=>a.admitted&&!a.revoked))a.suspended=true;}
        histories.events.push({week:w,type:'optional-public-method-adoption',agent:AGENTS[ai].id,skill:k,success,...v,expiresWeek:w+life});}
    }
    if(w<C.weeks&&stoppedWeek===null){
      bill(w,cents((C.overheadMonthly-C.operatorSubscriptionMonthly+Math.max(0,C.concurrency-3)*C.capacityControlMonthlyPerAdditionalSlot)*12/52),'business','automated-recurring-operation-excluding-subscription');
      bill(w,cents(C.operatorSubscriptionMonthly*12/52),'business','allocated-operator-subscription-not-API-usage');
      if(insolvent){stoppedWeek=w;stopReason='cash-shortfall';}
      if(w>=C.earlyAbandonWeeks&&total.accepted===0&&total.contacted>=8){stoppedWeek=w;stopReason='no-observed-commercial-traction';bill(w,cents(C.winddownCost),'business','orderly-winddown');}
      if(stoppedWeek===null){
        considerInvestment(w);
        for(const j of world.weeks[w]){
          const intake=planAuxiliary(C,'quote_intake',{scale:j.complexity});
          if(!auxiliary(intake,w,'quote_intake',`automated-intake-and-acquisition:${j.id}`,'business',cents(C.acquisitionCostPerProspect))){total.marketThrottled++;continue;}
          total.contacted++;
          const caps=capsFor(j.agent,w,w+j.deadline),reservation=reserveJob(W,j,caps),resource=resourceOf(reservation);
          const book=booking(resource,w,j.deadline);
          const quote=priceFor(j,w),choice=buyerChoice(C,j,quote.priceCents,qualityBelief(),book?book.finish-w:j.deadline,completionBelief());
          total[{ai:'aiChoices',human:'humanChoices',postpone:'postponed',decline:'declined'}[choice.choice]]++;
          const offer={...j,choice:choice.choice,priceCents:quote.priceCents,priceRatio:quote.ratio,
            perceivedQuality:choice.perceivedQuality,completionBelief:choice.completionBelief,capacityRefused:choice.choice==='ai'&&!book};
          priorOffers.push(offer);histories.offers.push({...offer,utilitiesCents:choice.utilitiesCents});
          if(!j.scopeSupported){total.outOfScope++;continue;}if(choice.choice!=='ai')continue;
          if(!book){total.capacityRefusals++;continue;}
          const reservedCents=reservation.costCents+cents(315);
          if(funds(w).availableCents<reservedCents){total.liquidityRefusals++;continue;}
          const pendingJobs=pending.filter(e=>e.type==='job'&&e.week>w).length;
          if(pendingJobs>=C.queueLimit){total.capacityRefusals++;continue;}
          const actualConfig={...W,improvementProbability:j.improvable?C.improvementProbability/Math.sqrt(j.complexity):0};
          const applied=activeAssets(w).filter(a=>a.recipients.includes(j.agent)&&a.expiryWeek>w+j.deadline&&
            (a.lastRevalidationWeek??a.readyWeek)+C.assetRevalidationWeeks>w+j.deadline);
          if(applied.some(a=>!a.productive))actualConfig.commonError=Math.max(actualConfig.commonError,.35);
          const plan=planJob(actualConfig,j,caps,label=>random(seed,j.id,'workflow',label));
          const baseCaps={...known[j.agent]};for(const k of Object.keys(baseCaps))if(knownUntil[j.agent][k]!==undefined&&knownUntil[j.agent][k]<=w+j.deadline)baseCaps[k]=false;
          const base=planJob({...W,improvementProbability:actualConfig.improvementProbability},j,baseCaps,label=>random(seed,j.id,'workflow',label));
          const baseBook=booking(resourceOf(reserveJob(W,j,baseCaps)),w,j.deadline);
          const booked=booking(resource,w,j.deadline,true);if(!booked)throw Error('Job lost its checked capacity');
          const newlyFeasible=!baseBook;total.newlyFeasible+=Number(newlyFeasible);total.attemptedJobs++;
          commitment+=reservedCents;
          if(booked.start>w)pending.push({type:'job-start',week:booked.start,jobId:j.id});
          pending.push({type:'job',week:booked.finish,job:j,plan,booking:booked,priceCents:quote.priceCents,
            reservedCents,caps,baselineCostCents:base.costCents,appliedAssets:applied.length,
            appliedAssetIds:applied.map(a=>a.id),newlyFeasible,betaVersion});
        }
      }
    }else if(w>=C.weeks)bill(w,cents(C.runoffOverheadMonthly*12/52),'business','runoff-support-and-recovery');
    const f=funds(w);histories.balances.push({week:w,...f,collectionsCents:collections,refundsCents:refunds,
      accruedCostsCents:accrued,paidResourceCostsCents:paid,fullCostProfitCents:netProfit(),stopped:stoppedWeek!==null});
    histories.capacity.push({week:w,...slots[w]});
    if(cash!==cents(C.seedCapital)+sum(histories.cash.map(e=>e.amountCents)))throw Error('Weekly cash conservation');
  }
  if(pending.some(e=>!e.processed))throw Error('Runoff does not cover all due events and obligations');
  const terminal=funds(horizon-1),resourceBills=histories.bills.filter(b=>b.category!=='refund');
  const summary={scenario:C.id,policy:P.id,seed,ablation,...total,
    profitCents:netProfit(),collectionsCents:collections,refundsCents:refunds,costsCents:accrued,
    terminalCashCents:cash,availableCents:terminal.availableCents,earnedAvailableCents:terminal.earnedAvailableCents,
    unpaidCents:unpaid,minCashCents:minCash,insolvent,stoppedWeek,stopReason,
    investmentCampaigns:histories.campaigns.length,
    paidOriginCandidates:histories.paidCandidates.length,rightsClearedCandidates:histories.paidCandidates.filter(r=>r.rightsCleared).length,
    retentionCampaigns:histories.campaigns.filter(c=>c.sourceKind==='B_paid_job_retention').length,
    separateResearchCampaigns:histories.campaigns.filter(c=>c.sourceKind==='C_optional_research').length,
    paidOriginAdmissions:assets.filter(a=>a.admitted&&a.sourceKind==='B_paid_job_retention').length,
    sourceJobDevelopmentRechargedCents:0,
    A_jobCostCents:sum(resourceBills.filter(b=>b.lane==='A_paid_job').map(b=>b.amountCents)),
    B_retentionReuseCostCents:sum(resourceBills.filter(b=>b.lane==='B_retention_reuse').map(b=>b.amountCents)),
    C_optionalResearchCostCents:sum(resourceBills.filter(b=>b.lane==='C_optional_research').map(b=>b.amountCents)),
    commonBusinessCostCents:sum(resourceBills.filter(b=>b.lane==='common_business').map(b=>b.amountCents)),
    historicalAllowanceCostCents:sum(resourceBills.filter(b=>b.lane==='historical_allowance').map(b=>b.amountCents)),productiveCampaigns:histories.campaigns.filter(x=>x.productive&&x.admitted).length,
    retainedCapabilities:sum(activeAssets(C.weeks-1).filter(a=>network.available({id:a.id,member:AGENTS[a.owner].id,week:C.weeks-1})).map(a=>a.keys.length)),
    alphaUses:sum(assets.map(a=>a.uses)),alphaPeerUses:histories.jobs.filter(j=>j.appliedAssetIds.some(id=>AGENTS[assets.find(a=>a.id===id).owner].id!==j.agent)).length,
    alphaFalseAdmissions:assets.filter(a=>a.admitted&&!a.productive).length,
    activeAlphaRecords:activeAssets(C.weeks-1).length,
    cancelledBeforeStart:histories.jobs.filter(j=>j.cancelledBeforeStart).length,
    genuinelyExecutedJobs:histories.jobs.filter(j=>!j.cancelledBeforeStart).length,
    alphaAssessmentCostCents:sum(histories.campaigns.map(a=>a.review.costCents))+sum(histories.revalidations.map(a=>a.costCents)),
    totalRAndDCents:sum(resourceBills.filter(b=>b.category==='capability').map(b=>b.amountCents)),
    totalMaintenanceCents:sum(resourceBills.filter(b=>b.category==='maintenance').map(b=>b.amountCents)),
    peerUsefulOutcomes:histories.jobs.filter(j=>j.useful&&j.appliedAssetIds.some(id=>AGENTS[assets.find(a=>a.id===id).owner].id!==j.agent)).length,
    earnedFundedInvestmentCents:sum(assets.map(a=>a.earnedFundedCents)),seedFundedInvestmentCents:sum(assets.map(a=>a.seedFundedCents)),
    fullCostPerUsefulCents:total.usefulAccepted?accrued/total.usefulAccepted:null,
    marginalCostPerUsefulCents:total.usefulAccepted?sum(resourceBills.filter(b=>b.category==='delivery').map(b=>b.amountCents))/total.usefulAccepted:null,
    acceptedPerMonth:total.usefulAccepted/(C.weeks*12/52),automatedShare:total.usefulAccepted?1:null,
    queueP95Weeks:percentile(histories.jobs.map(j=>j.queueWeeks),.95),
    reservationLatencyMedianWeeks:percentile(histories.jobs.map(j=>j.reservationDurationWeeks+j.queueWeeks),.5),
    actualServiceMedianHours:percentile(histories.jobs.map(j=>j.resources.hours),.5),
    inputUtilization:sum(histories.capacity.slice(0,C.weeks).map(r=>r.input))/(C.weeks*C.inputQuotaWeekly),
    outputUtilization:sum(histories.capacity.slice(0,C.weeks).map(r=>r.output))/(C.weeks*C.outputQuotaWeekly),
    cpuUtilization:sum(histories.capacity.slice(0,C.weeks).map(r=>r.cpu))/(C.weeks*C.cpuHoursWeekly),
    validatorUtilization:sum(histories.capacity.slice(0,C.weeks).map(r=>r.validation))/(C.weeks*C.validatorHoursWeekly),
    concurrencyUtilization:sum(histories.capacity.slice(0,C.weeks).map(r=>r.slots))/(C.weeks*C.concurrency),
    meanOfferedPriceRatio:histories.offers.length?sum(histories.offers.map(o=>o.priceRatio))/histories.offers.length:null,
    escapedErrorShare:total.accepted?total.latentAcceptedErrors/total.accepted:null,
    actualJobs:0,actualCollectionsUSD:0,automatedIntake:true,routineHumanReview:false,
    discountedNetCashCents:sum(histories.cash.map(e=>e.amountCents/((1+C.discountRateAnnual)**(e.week/52)))),
    discountedAccrualProfitCents:sum(histories.cash.filter(e=>e.type==='simulated_collection').map(e=>e.amountCents/((1+C.discountRateAnnual)**(e.week/52))))-
      sum(histories.bills.map(e=>e.amountCents/((1+C.discountRateAnnual)**(e.week/52)))),
    usefulMeanHumanPriceCents:total.usefulAccepted?sum(histories.jobs.filter(j=>j.useful).map(j=>j.humanPriceCents))/total.usefulAccepted:null,
    usefulMeanOfferedPriceCents:total.usefulAccepted?sum(histories.jobs.filter(j=>j.useful).map(j=>j.priceCents))/total.usefulAccepted:null,
    newlyFeasibleUseful:histories.jobs.filter(j=>j.useful&&j.newlyFeasible).length,
    modeledPaidUsefulCustomerSavingsCents:sum(histories.jobs.filter(j=>j.useful&&histories.invoices.some(i=>i.jobId===j.id&&i.collectedWeek!==null&&!i.refunded)).map(j=>j.humanPriceCents-j.priceCents))};
  const events=[{id:'venture:mission',type:'mission',missionId:'venture',reference:'Simulated venture aggregate; no actual job',acceptance:'accepted'},
    {id:'venture:revenue',type:'revenue',missionId:'venture',category:'price',basis:'assumed',amountMinor:collections-refunds,reference:'Modeled collections net of refunds; never observed revenue'},
    ...['delivery','business','capability','maintenance'].map(category=>({id:`venture:${category}`,type:'cost',missionId:'venture',category,basis:'assumed',
      amountMinor:sum(resourceBills.filter(b=>b.category===category).map(b=>b.amountCents)),reference:'Complete modeled accrued resource cost'})),
    {id:'venture:reserve',type:'reserve',missionId:'venture',category:'reliability',basis:'assumed',amountMinor:terminal.reservesCents+terminal.maintenanceEarmarkCents,reference:'Protected modeled reserves'},
    {id:'venture:unpaid',type:'obligation',missionId:'venture',category:'unpaid',basis:'assumed',amountMinor:0,reference:'Unpaid resource costs already accrued; actual liquidity separately subtracts unpaid obligations'}];
  const canonical=replayLedger({schema:SCHEMA,currency:C.currency,events},{reinvestmentBps:0});
  if(canonical.scenario.operatingMargin!==summary.profitCents||canonical.observed.revenue!==null)throw Error('Canonical accounting mismatch');
  if(accrued!==sum(resourceBills.map(b=>b.amountCents)))throw Error('Accrual mismatch');
  if(commitment!==0)throw Error('Unreleased execution commitment');
  return retain?{schema:'beyond-beta-network-simulation/v1',network:network.snapshot({includeCiphertext:false}),evidence:'ASSUMED_OR_EXPLORED',config:C,policy:P,seed,ablation,summary,assets,histories,canonical}:
    {summary,assets};
}
