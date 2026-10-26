// SPDX-License-Identifier: Apache-2.0
import {planMission, calculateInvestment} from '../canonical/shadow-ledger.mjs';

export const SCHEMA = 'agi-alpha-strategic-market/v1';
export const ASSETS = Object.freeze({
  B: {id:'useful-work-v2-retained-producer', path:'src/package_component.py',
    sha256:'0b4eb1ae2392176ff61ef91b7da0d13df3c6400ee0b3e317439238881adc182d'},
  C: {id:'useful-work-v2-conventional-producer', path:'src/conventional_package.py',
    sha256:'cd28579ecf72eba5bdfffa6b3b5483aaaa960322989d2a2369da5431062207ba'}
});
export const defaultConfig = Object.freeze({
  id:'reference-assumptions', weeks:52, buyers:12, arrivalProbability:0.25, supportedFraction:0.75,
  initialCashCents:100000, reserveCents:20000, initialSetupCents:5000, weeklyOverheadCents:200,
  paymentDelayWeeks:2, paymentProbability:0.98, expenseDelayWeeks:0, refundProbability:0.75,
  refundDelayWeeks:1, choiceModel:'deterministic', logitScaleCents:1200,
  hourlyProviderCents:6538, hourlyBuyerCents:[3000,5014,6538], humanHourlyCents:3000,
  humanMinutes:[30,60,90], usefulnessMultiplier:1.25, errorLossCents:10000,
  customerReviewMinutes:8, diyEffortFraction:0.65, aiReviewMinutes:15, humanReviewMinutes:6,
  integrationCents:1000, switchingCents:500, delayCostCentsPerDay:250,
  buyerProcurementBudgetCents:50000, outcomeFeedbackDelayWeeks:1,
  commonResidualMinutes:2, ordinaryFinalizationMinutes:10, assetResidualMinutes:0,
  computeAndToolCents:25, failureCorrectionMultiplier:1.5, successProbability:0.95,
  qualityShockWeek:99, qualityShockFactor:1, overloadPenalty:0.08,
  humanQuality:0.97, diyQuality:0.95, aiQuality:0.90, initialTrust:0.90, skepticalShare:0.25,
  enterpriseSlotsPerWeek:4, providerMinutesPerWeek:120, humanSlotsPerWeek:4, aiSlotsPerWeek:6,
  measuredMechanicalWallSeconds:16.79944029399985, measuredMechanicalCpuSeconds:2.53920892,
  machineWallSecondsPerWeek:3600, machineCpuSecondsPerWeek:3600,
  enterpriseDays:1, humanDays:2, diyDays:0.5, aiDays:0.5,
  initialPriceCents:4000, priceGridCents:[500,1000,2000,4000,8000], pricingPolicy:'empirical-grid',
  aiInitialPriceCents:2000, aiCostCents:800, humanMarkup:1.2, competitorStrategy:'responsive',
  competitorInitialCashCents:50000, competitorImitationCostCents:20000, competitorImitationAfterWeeks:12,
  competitorCostReduction:0.25, competitorPriceFloorCents:500,
  constructionHours:4, constructionHourlyCents:6538, authoringCostCents:10000,
  investmentCostBasis:'full-history', adoptionHours:0.5, adoptionInferenceCents:0,
  historicalCostTiming:'opening', engineeringHoursPerWeek:4,
  failedConstructionShare:0.20, assetMaintenanceCentsPerWeek:50, assetFailureProbability:0,
  investmentEarliestWeek:8, investmentForecastDiscount:0.5, investmentFunding:'operating-surplus',
  expectedPassThrough:0.25, churnProbability:0.25, churnDurationWeeks:8,
  stopAfterInsolvency:true, nextAsset:null,
  allMoneyIsAssumed:true
});

const clamp=(x,lo,hi)=>Math.max(lo,Math.min(hi,x));
const round=x=>Math.max(0,Math.round(x));
const sum=xs=>xs.reduce((a,b)=>a+b,0);
const assert=(condition,message)=>{if(!condition)throw Error(message);};
const costs=['delivery','business','capability','maintenance','refund'];

export function randomDraw(seed,...keys){
  let h=(seed>>>0)^2166136261;
  for(const char of keys.join('|')){h^=char.charCodeAt(0);h=Math.imul(h,16777619);}
  h^=h>>>16;h=Math.imul(h,0x7feb352d);h^=h>>>15;h=Math.imul(h,0x846ca68b);h^=h>>>16;
  return ((h>>>0)+0.5)/4294967296;
}

export function validateConfig(supplied){
  assert(supplied&&typeof supplied==='object'&&!Array.isArray(supplied),'Configuration must be an object');
  const c={...defaultConfig,...supplied};
  for(const k of Object.keys(supplied))assert(Object.hasOwn(defaultConfig,k),`Unknown configuration: ${k}`);
  for(const [k,v]of Object.entries(defaultConfig))if(v!==null&&!Array.isArray(v))
    assert(typeof c[k]===typeof v,`Explicit ${typeof v} required: ${k}; unknown costs cannot be zero-filled`);
  for(const [k,v] of Object.entries(c))if(typeof v==='number')assert(Number.isFinite(v)&&v>=0,`Invalid ${k}`);
  for(const [k,v]of Object.entries(c))if(k.endsWith('Cents')&&typeof defaultConfig[k]==='number')
    assert(Number.isSafeInteger(v)&&v<=1_000_000_000,`Safe integer cents required: ${k}`);
  for(const k of ['weeks','buyers','enterpriseSlotsPerWeek','humanSlotsPerWeek','aiSlotsPerWeek','paymentDelayWeeks','expenseDelayWeeks',
    'refundDelayWeeks','qualityShockWeek','competitorImitationAfterWeeks','investmentEarliestWeek','churnDurationWeeks'])
    assert(Number.isSafeInteger(c[k]),`Integer required: ${k}`);
  assert(c.weeks>=1&&c.weeks<=104&&c.buyers>=1&&c.buyers<=40,'Finite market limits exceeded');
  for(const k of ['arrivalProbability','supportedFraction','paymentProbability','refundProbability','successProbability','humanQuality',
    'diyQuality','aiQuality','initialTrust','skepticalShare','assetFailureProbability','churnProbability','investmentForecastDiscount',
    'expectedPassThrough','competitorCostReduction','qualityShockFactor'])assert(c[k]<=1,`Probability exceeds one: ${k}`);
  assert(['deterministic','logit'].includes(c.choiceModel),'Unknown buyer model');
  assert(['empirical-grid','fixed','cost-pass-through'].includes(c.pricingPolicy),'Unknown price policy');
  assert(['responsive','fixed','undercut'].includes(c.competitorStrategy),'Unknown competitor policy');
  assert(['operating-surplus','seed-funded'].includes(c.investmentFunding),'Unknown investment funding');
  assert(['full-history','adoption-only'].includes(c.investmentCostBasis),'Unknown investment cost basis');
  assert(['at-adoption','opening'].includes(c.historicalCostTiming),'Unknown historical cost timing');
  assert(Number.isInteger(c.outcomeFeedbackDelayWeeks)&&c.outcomeFeedbackDelayWeeks>=1,'Feedback requires at least one week');
  assert(c.allMoneyIsAssumed===true,'Market monetary values must remain explicit assumptions');
  assert(c.failureCorrectionMultiplier>=1,'Failed work cannot receive a discount by construction');
  assert(c.engineeringHoursPerWeek>0,'Positive finite adoption engineering capacity required');
  assert(c.stopAfterInsolvency===true,'Only irreversible stopping on insolvency is supported');
  assert(c.nextAsset===null||c.nextAsset?.tested===true,'Unexecuted successor cannot be an investment');
  for(const k of ['hourlyBuyerCents','humanMinutes','priceGridCents'])assert(Array.isArray(c[k])&&c[k].length>0&&
    c[k].length<=20&&c[k].every(x=>Number.isFinite(x)&&x>=0),`Invalid ${k}`);
  for(const k of ['hourlyBuyerCents','priceGridCents'])assert(c[k].every(x=>Number.isSafeInteger(x)&&x<=1_000_000_000),
    `Integer monetary array required: ${k}`);
  return c;
}

export function pruneDominated(offers){
  return offers.filter(a=>!offers.some(b=>b.id!==a.id&&
    b.quality>=a.quality&&b.priceCents<=a.priceCents&&b.effortCents<=a.effortCents&&
    b.delayCents<=a.delayCents&&b.switchCents<=a.switchCents&&
    (b.quality>a.quality||b.priceCents<a.priceCents||b.effortCents<a.effortCents||
      b.delayCents<a.delayCents||b.switchCents<a.switchCents)));
}

export function chooseBuyer(offers,buyer,c,u){
  const eligible=pruneDominated(offers).map(o=>({...o,utilityCents:o.quality*buyer.valueCents-o.priceCents-
    o.effortCents-o.delayCents-o.switchCents-(1-o.quality)*buyer.errorLossCents}));
  const viable=eligible.filter(x=>x.utilityCents>0);
  if(!viable.length)return {choice:'defer',utilityCents:0,offers:eligible};
  if(c.choiceModel==='deterministic'){
    viable.sort((a,b)=>b.utilityCents-a.utilityCents||a.id.localeCompare(b.id));
    return {choice:viable[0].id,utilityCents:viable[0].utilityCents,offers:eligible};
  }
  const scale=Math.max(1,c.logitScaleCents), maximum=Math.max(0,...viable.map(x=>x.utilityCents));
  const options=[{id:'defer',utilityCents:0},...viable];
  const weights=options.map(x=>Math.exp(clamp((x.utilityCents-maximum)/scale,-700,0)));
  let location=u*sum(weights);
  for(let i=0;i<options.length;i++){location-=weights[i];if(location<=0)return {choice:options[i].id,
    utilityCents:options[i].utilityCents,offers:eligible};}
  return {choice:options.at(-1).id,utilityCents:options.at(-1).utilityCents,offers:eligible};
}

function buyerState(seed,index,c){
  const rate=c.hourlyBuyerCents[Math.floor(randomDraw(seed,'type-rate',index)*c.hourlyBuyerCents.length)];
  const minutes=c.humanMinutes[Math.floor(randomDraw(seed,'type-minutes',index)*c.humanMinutes.length)];
  const skeptical=randomDraw(seed,'type-trust',index)<c.skepticalShare;
  const q=clamp(c.initialTrust-(skeptical?0.15:0),0.01,0.999);
  const prior=provider=>({successes:provider==='human'?c.humanQuality*10:provider==='diy'?c.diyQuality*10:q*10,total:10});
  return {id:`buyer-${index}`,index,rate,minutes,valueCents:round(rate*minutes/60*c.usefulnessMultiplier),
    errorLossCents:round(c.errorLossCents*(0.5+randomDraw(seed,'type-error',index))),lastProvider:null,
    beliefs:Object.fromEntries(['enterprise','human','ai','diy'].map(p=>[p,prior(p)])),bannedUntil:{},missions:0,
    procurementBudgetCents:round(c.buyerProcurementBudgetCents*(0.5+randomDraw(seed,'buyer-budget',index))),
    committedProcurementCents:0};
}

function createFirm(id,opening){return {id,openingCashCents:opening,cashCents:opening,invoices:[],bills:[],cashEvents:[],
  balanceHistory:[],costs:Object.fromEntries(costs.map(x=>[x,0])),paidCosts:Object.fromEntries(costs.map(x=>[x,0])),
  grossInvoicesCents:0,grossCollectionsCents:0,writtenOffCents:0,cancelledInvoicesCents:0,
  insolvent:false,insolventWeek:null,attempts:0,accepted:0,rejected:0,latentFailures:0,
  previousSales:0,investments:[],assetActive:false,assetPending:false,assetAvailableWeek:null,assetFailure:false,assetUses:0};}
function unpaid(f){return sum(f.bills.filter(x=>!x.paid).map(x=>x.amountCents));}
function receivable(f){return sum(f.invoices.filter(x=>x.status==='pending').map(x=>x.amountCents));}
function expense(f,week,category,amount,due=week,reference='scenario expense'){
  amount=round(amount);if(amount===0)return;
  f.costs[category]+=amount;
  f.bills.push({id:`${f.id}-bill-${f.bills.length}`,week,dueWeek:due,category,amountCents:amount,paid:false,reference});
}
function payBills(f,week,c){
  for(const b of f.bills.filter(x=>!x.paid&&x.dueWeek<=week).sort((a,b)=>a.dueWeek-b.dueWeek||a.id.localeCompare(b.id))){
    if(f.cashCents<b.amountCents){f.insolvent=true;f.insolventWeek??=week;continue;}
    f.cashCents-=b.amountCents;f.paidCosts[b.category]+=b.amountCents;b.paid=true;b.paidWeek=week;
    f.cashEvents.push({week,type:b.category==='refund'?'refund':'expense_payment',amountCents:-b.amountCents,
      cashAfterCents:f.cashCents,reference:b.id});
  }
  assert(f.cashCents>=0,'Cash budget violation');
}
function collect(f,week,c){
  for(const invoice of f.invoices.filter(x=>x.status==='pending'&&x.dueWeek<=week)){
    if(!invoice.pays){invoice.status='defaulted';f.writtenOffCents+=invoice.amountCents;continue;}
    invoice.status='collected';invoice.collectedWeek=week;f.cashCents+=invoice.amountCents;
    f.grossCollectionsCents+=invoice.amountCents;
    f.cashEvents.push({week,type:'simulated_collection',amountCents:invoice.amountCents,
      cashAfterCents:f.cashCents,reference:invoice.id});
    if(invoice.refund)expense(f,week,'refund',invoice.amountCents,week+c.refundDelayWeeks,invoice.id);
  }
}
function liquidity(f,c){return f.cashCents-unpaid(f)-c.reserveCents;}
function operatingSurplus(f,c){return Math.min(liquidity(f,c),f.grossCollectionsCents-
  sum(Object.values(f.costs))-c.reserveCents);}

function constructionRoutes(c){
  const history=round(c.constructionHours*c.constructionHourlyCents)+c.authoringCostCents;
  const adoption=round(c.adoptionHours*c.constructionHourlyCents)+c.adoptionInferenceCents;
  const reconstruct=history+adoption;
  return {historicalFullCostCents:history,adoptExistingCents:adoption,reconstructCents:reconstruct,
    selectedRoute:'adopt-existing',selectedProspectiveCostCents:adoption,
    chargedCents:c.investmentCostBasis==='full-history'&&c.historicalCostTiming==='at-adoption'?history+adoption:adoption};
}
function constructionCost(c){return constructionRoutes(c).chargedCents;}
function providerMinutes(c,active){return c.commonResidualMinutes+(active?c.assetResidualMinutes:c.ordinaryFinalizationMinutes);}
function unitCost(c,active){return round(providerMinutes(c,active)*c.hourlyProviderCents/60)+c.computeAndToolCents;}
function invest(f,week,c,seed,arm,recentAccepted,decisions){
  if(arm==='A'||f.assetActive||f.assetPending||f.assetFailure||f.insolvent||week<c.investmentEarliestWeek)return;
  const full=constructionCost(c),pauseWeeks=Math.max(1,Math.ceil(c.adoptionHours/c.engineeringHoursPerWeek));
  const remaining=Math.max(0,c.weeks-week-pauseWeeks);
  const forecast=Math.floor(recentAccepted/Math.max(1,Math.min(8,week))*remaining*c.investmentForecastDiscount);
  const saving=Math.floor((unitCost(c,false)-unitCost(c,true))*(1-c.expectedPassThrough));
  const totalMaintenance=round(remaining*c.assetMaintenanceCentsPerWeek);
  const recentInvoices=f.invoices.filter(x=>x.week>=Math.max(0,week-8)&&x.week<week);
  const meanInvoice=recentInvoices.length?sum(recentInvoices.map(x=>x.amountCents))/recentInvoices.length:0;
  const lostContribution=round(recentAccepted/Math.max(1,Math.min(8,week))*pauseWeeks*
    Math.max(0,meanInvoice*c.paymentProbability-unitCost(c,false)*c.failureCorrectionMultiplier));
  const expected=forecast*saving-totalMaintenance-full-lostContribution;
  const available=c.investmentFunding==='operating-surplus'?operatingSurplus(f,c):liquidity(f,c);
  const canInvest=expected>0&&available>=full&&saving>0;
  const row={week,arm,action:canInvest?'invest':'retain-incumbent',asset:ASSETS[arm],
    availableCashCents:available,fullCostCents:full,remainingUsesForecast:forecast,
    expectedIncrementalSavingPerUseCents:saving,expectedNetBenefitCents:expected,
    expectedForegoneContributionCents:lostContribution,productiveWeeksAfterAdoption:remaining,servicePauseWeeks:pauseWeeks,
    observedPriorAccepted:recentAccepted,funding:c.investmentFunding,
    costBasis:c.investmentCostBasis,routes:constructionRoutes(c),
    reasons:canInvest?[]:[...(expected<=0?['expected full-cost repayment not positive']:[]),
      ...(available<full?['insufficient currently available funding']:[]),...(saving<=0?['no positive task saving']:[])]};
  decisions.push(row);
  if(!canInvest)return;
  expense(f,week,'capability',full,week,ASSETS[arm].sha256);payBills(f,week,c);
  f.assetFailure=randomDraw(seed,'asset-integration-failure',week)<c.assetFailureProbability;
  f.assetAvailableWeek=week+pauseWeeks;
  f.assetPending=!f.assetFailure;
  f.investments.push({...row,success:!f.assetFailure,paidInFull:true,availableWeek:f.assetAvailableWeek,
    servicePauseWeeks:f.assetAvailableWeek-week,
    failuresIncludedCents:round(full*c.failedConstructionShare),
    constructionEvidence:'Actual source and finite-scope tests; monetary construction and authoring amounts are scenario assumptions.'});
}

function selectPrice(c,week,firm,priceStats,previous){
  const cost=unitCost(c,firm.assetActive),floor=cost+100;
  if(c.pricingPolicy==='fixed')return Math.max(floor,c.initialPriceCents);
  if(c.pricingPolicy==='cost-pass-through')return Math.max(floor,
    c.initialPriceCents-round((unitCost(c,false)-cost)*c.expectedPassThrough));
  const viable=c.priceGridCents.filter(x=>x>=floor);
  if(!viable.length)return floor;
  const tried=viable.find(x=>(priceStats[x]?.seen||0)===0);
  if(tried!==undefined)return tried;
  const opportunities=sum(Object.values(priceStats).map(x=>x.seen));
  return viable.map(price=>{const h=priceStats[price],p=(h.won+1)/(h.seen+5);
    const exploration=Math.sqrt(2*Math.log(opportunities+2)/(h.seen+1));
    return {price,score:(p+0.15*exploration)*(price-cost)};})
    .sort((a,b)=>b.score-a.score||a.price-b.price)[0].price;
}

function offersFor(buyer,c,week,enterprise,competitors,price,used,providerUsed){
  const offers=[];
  const add=(id,posted,effortMinutes,days)=>{
    if((buyer.bannedUntil[id]||0)>week)return;
    if(posted>buyer.procurementBudgetCents-buyer.committedProcurementCents)return;
    const belief=buyer.beliefs[id];
    offers.push({id,priceCents:round(posted),quality:clamp(belief.successes/belief.total,0,1),
      effortCents:round(effortMinutes*buyer.rate/60),delayCents:round(days*c.delayCostCentsPerDay),
      switchCents:buyer.lastProvider===id?0:round((buyer.lastProvider?c.switchingCents:0)+(id==='enterprise'?c.integrationCents:0))});
  };
  if(!enterprise.insolvent&&!enterprise.assetPending&&used.enterprise<c.enterpriseSlotsPerWeek&&
    (used.enterprise+1)*c.measuredMechanicalWallSeconds<=c.machineWallSecondsPerWeek&&
    (used.enterprise+1)*c.measuredMechanicalCpuSeconds<=c.machineCpuSecondsPerWeek&&
    providerUsed+providerMinutes(c,enterprise.assetActive)<=c.providerMinutesPerWeek&&
    liquidity(enterprise,c)>=unitCost(c,enterprise.assetActive)*c.failureCorrectionMultiplier)
    add('enterprise',price,c.customerReviewMinutes,c.enterpriseDays);
  if(!competitors.human.insolvent&&used.human<c.humanSlotsPerWeek&&competitors.human.cashCents-unpaid(competitors.human)>=
    round(buyer.minutes*c.humanHourlyCents/60*c.failureCorrectionMultiplier))
    add('human',buyer.minutes*c.humanHourlyCents/60*competitors.human.markup,c.humanReviewMinutes,c.humanDays);
  if(!competitors.ai.insolvent&&used.ai<c.aiSlotsPerWeek&&competitors.ai.cashCents-unpaid(competitors.ai)>=
    round(competitors.ai.unitCostCents*c.failureCorrectionMultiplier))
    add('ai',competitors.ai.priceCents,c.aiReviewMinutes,c.aiDays);
  add('diy',0,buyer.minutes*c.diyEffortFraction,c.diyDays);
  return offers;
}

function competitorResponse(competitors,enterprise,week,c,posted,events){
  if(c.competitorStrategy==='fixed')return;
  const ai=competitors.ai,human=competitors.human;
  if(!ai.imitated&&week>=c.competitorImitationAfterWeeks&&enterprise.accepted>=4&&
      ai.cashCents-unpaid(ai)>=c.competitorImitationCostCents){
    expense(ai,week,'capability',c.competitorImitationCostCents,week,'assumed conventional automation adoption');
    payBills(ai,week,c);ai.imitated=true;ai.unitCostCents=round(ai.unitCostCents*(1-c.competitorCostReduction));
    events.push({week,provider:'ai',action:'adopt-automation',costCents:c.competitorImitationCostCents,
      basis:'scenario competitor action; not an actually built AGI ALPHA successor'});
  }
  const floor=Math.max(c.competitorPriceFloorCents,ai.unitCostCents+100),old=ai.priceCents;
  if(c.competitorStrategy==='undercut')ai.priceCents=Math.max(floor,round(posted*0.8));
  else if(ai.previousSales===0)ai.priceCents=Math.max(floor,round(ai.priceCents*0.85));
  else if(ai.previousSales>=c.aiSlotsPerWeek)ai.priceCents=round(ai.priceCents*1.1);
  else ai.priceCents=Math.max(floor,Math.min(ai.priceCents,round(posted*0.95)));
  if(human.previousSales===0)human.markup=Math.max(1.02,human.markup-0.03);
  if(old!==ai.priceCents)events.push({week,provider:'ai',action:'change-posted-price',beforeCents:old,afterCents:ai.priceCents});
}

function canonicalProjection(f,c){
  const reference='SIMULATION ONLY. Market cash events are nonauthoritative. Canonical observed collections remain zero.';
  const operating=sum(costs.filter(k=>k!=='capability').map(k=>f.costs[k]));
  const paid=sum(costs.filter(k=>k!=='capability').map(k=>f.paidCosts[k]));
  const economic=planMission({missionId:'simulated-enterprise-economic',reference,currency:'USD',acceptance:'accepted',
    totalCollectedCents:0,priceAssumptionCents:f.grossCollectionsCents+receivable(f),
    totalOperatingCostCents:operating,operatingCostsComplete:true,capabilityCostCents:f.costs.capability,
    reserveCents:0,obligationCents:0,costBasis:'assumed',reinvestmentBps:0});
  const cash=planMission({missionId:'simulated-enterprise-liquidity',reference,currency:'USD',acceptance:'accepted',
    totalCollectedCents:0,priceAssumptionCents:f.grossCollectionsCents,
    totalOperatingCostCents:paid,operatingCostsComplete:true,capabilityCostCents:f.paidCosts.capability,
    reserveCents:c.reserveCents,obligationCents:unpaid(f),costBasis:'assumed',reinvestmentBps:0});
  assert(cash.summary.observed.revenue===0,'Simulation contaminated observed collections');
  assert(cash.summary.scenario.afterReserves===f.cashCents-f.openingCashCents-unpaid(f)-c.reserveCents,
    'Canonical cash projection does not reconcile');
  assert(economic.summary.scenario.operatingMargin===f.cashCents+receivable(f)-unpaid(f)-f.openingCashCents,
    'Canonical economic projection does not reconcile');
  return {basis:'SIMULATED',economic,cash,
    treatment:'Canonical price assumption holds modeled collections/receivables, never observed revenue. Refunds are explicit adjustment costs. Accrued economic costs and paid-cash/obligations are separate projections.'};
}

export function simulate(supplied={},seed=1,arm='B',options={}){
  assert(['A','B','C'].includes(arm),'Unknown arm');
  const c=validateConfig(supplied),buyers=Array.from({length:c.buyers},(_,i)=>buyerState(seed,i,c));
  const f=createFirm('enterprise',c.initialCashCents);
  const competitors={human:{...createFirm('human',c.competitorInitialCashCents),markup:c.humanMarkup},
    ai:{...createFirm('ai',c.competitorInitialCashCents),priceCents:c.aiInitialPriceCents,unitCostCents:c.aiCostCents,imitated:false}};
  const decisions=[],jobs=[],buyerChoices=[],competition=[],prices=[],priceStats={},weeklySales=[],feedback=[];
  if(arm!=='A'&&c.investmentCostBasis==='full-history'&&c.historicalCostTiming==='opening')
    expense(f,0,'capability',constructionRoutes(c).historicalFullCostCents,0,
      'upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing');
  expense(f,0,'business',c.initialSetupCents,0,'assumed shared setup/discovery; common to all arms');
  payBills(f,0,c);
  let priorPrice=c.initialPriceCents,opportunities=0,supported=0,declined=0,providerUsed=0;
  const finalWeek=c.weeks+Math.max(c.paymentDelayWeeks+c.refundDelayWeeks,c.expenseDelayWeeks)+1;
  for(let week=0;week<=finalWeek;week++){
    if(f.assetPending&&week>=f.assetAvailableWeek&&!f.insolvent){f.assetPending=false;f.assetActive=true;}
    for(const signal of feedback.filter(x=>!x.observed&&x.dueWeek<=week)){
      signal.observed=true;const b=buyers[signal.buyerIndex],belief=b.beliefs[signal.provider];
      belief.successes+=signal.good?1:0;belief.total++;
      if(signal.churn)b.bannedUntil[signal.provider]=week+c.churnDurationWeeks;
    }
    for(const firm of [f,...Object.values(competitors)]){collect(firm,week,c);payBills(firm,week,c);}
    if(week<c.weeks){
      if(!f.insolvent)expense(f,week,'business',c.weeklyOverheadCents,week+c.expenseDelayWeeks,'assumed recurring service overhead');
      if(f.assetActive&&!f.insolvent)expense(f,week,'maintenance',c.assetMaintenanceCentsPerWeek,week+c.expenseDelayWeeks,
        'assumed actual-asset upkeep');
      payBills(f,week,c);
      const priorAccepted=sum(weeklySales.slice(Math.max(0,week-8),week));
      invest(f,week,c,seed,arm,priorAccepted,decisions);
      const price=selectPrice(c,week,f,priceStats,priorPrice);priorPrice=price;
      competitorResponse(competitors,f,week,c,price,competition);
      const used={enterprise:0,human:0,ai:0,diy:0};providerUsed=0;
      let enterpriseSeen=0,enterpriseWon=0,enterpriseAccepted=0;
      const ordered=[...buyers].sort((a,b)=>randomDraw(seed,'order',week,a.index)-randomDraw(seed,'order',week,b.index));
      for(const b of ordered){
        if(randomDraw(seed,'arrival',week,b.index)>=c.arrivalProbability)continue;
        opportunities++;b.missions++;
        if(randomDraw(seed,'scope',week,b.index)>=c.supportedFraction){
          buyerChoices.push({week,buyer:b.id,mission:`w${week}-${b.id}`,choice:'unsupported',basis:'simulated new changed-input opportunity'});continue;
        }
        supported++;
        const offers=offersFor(b,c,week,f,competitors,price,used,providerUsed);
        const hasEnterprise=offers.some(o=>o.id==='enterprise');if(hasEnterprise)enterpriseSeen++;
        const picked=chooseBuyer(offers,b,c,randomDraw(seed,'choice',week,b.index));
        buyerChoices.push({week,buyer:b.id,mission:`w${week}-${b.id}`,choice:picked.choice,
          utilityCents:Math.round(picked.utilityCents),...(options.includeOffers?{offers:picked.offers}:{}),
          basis:'simulated buyer action, not observed demand'});
        if(picked.choice==='defer'){declined++;continue;}
        const p=picked.choice,o=offers.find(x=>x.id===p);used[p]++;
        if(p==='enterprise'){enterpriseWon++;providerUsed+=providerMinutes(c,f.assetActive);}
        b.lastProvider=p;
        const shock=week>=c.qualityShockWeek?c.qualityShockFactor:1;
        const saturation=p==='enterprise'?Math.max(0,(used.enterprise-1)/Math.max(1,c.enterpriseSlotsPerWeek-1)):0;
        const quality=clamp((p==='enterprise'?c.successProbability:p==='human'?c.humanQuality:p==='ai'?c.aiQuality:c.diyQuality)*
          (p==='enterprise'?shock:1)-(p==='enterprise'?c.overloadPenalty*saturation:0),0,1);
        const good=randomDraw(seed,'quality',week,b.index,p)<quality;
        const detected=!good&&randomDraw(seed,'detect',week,b.index,p)<0.8;
        const accepted=!detected;
        if(p==='enterprise'&&accepted)enterpriseAccepted++;
        feedback.push({dueWeek:week+c.outcomeFeedbackDelayWeeks,buyerIndex:b.index,provider:p,good,observed:false,
          churn:!good&&randomDraw(seed,'churn',week,b.index,p)<c.churnProbability,
          basis:'Assumed post-delivery quality feedback; unavailable to buyer before dueWeek.'});
        const firm=p==='enterprise'?f:competitors[p];
        let paidCost=0;
        if(firm){
          firm.attempts++;accepted?firm.accepted++:firm.rejected++;if(!good&&accepted)firm.latentFailures++;
          const cost=p==='enterprise'?unitCost(c,f.assetActive):p==='human'?round(b.minutes*c.humanHourlyCents/60):competitors.ai.unitCostCents;
          paidCost=round(cost*(good?1:c.failureCorrectionMultiplier));
          expense(firm,week,'delivery',paidCost,week+c.expenseDelayWeeks,`w${week}-${b.id}`);
          if(p==='enterprise'&&f.assetActive)f.assetUses++;
          payBills(firm,week,c);
          if(accepted){
            b.committedProcurementCents+=o.priceCents;
            const invoice={id:`${firm.id}-invoice-${firm.invoices.length}`,mission:`w${week}-${b.id}`,week,
              dueWeek:week+c.paymentDelayWeeks,amountCents:o.priceCents,status:'pending',
              pays:randomDraw(seed,'payment',week,b.index,p)<c.paymentProbability,
              refund:!good&&randomDraw(seed,'refund',week,b.index,p)<c.refundProbability};
            firm.invoices.push(invoice);firm.grossInvoicesCents+=invoice.amountCents;
            if(c.paymentDelayWeeks===0){collect(firm,week,c);payBills(firm,week,c);}
          }
        }
        jobs.push({id:`w${week}-${b.id}`,week,buyer:b.id,provider:p,accepted,qualityGood:good,
          priceCents:o.priceCents,deliveryCostCents:paidCost,invoiceCreated:!!firm&&accepted,
          assetUsed:p==='enterprise'&&f.assetActive?ASSETS[arm]?.id:null,
          sourceAssetSHA256:p==='enterprise'&&f.assetActive?ASSETS[arm]?.sha256:null,
          probabilityAssumption:quality,basis:'simulated; constrained to measured supported scope'});
      }
      if(!priceStats[price])priceStats[price]={seen:0,won:0};
      priceStats[price].seen+=enterpriseSeen;priceStats[price].won+=enterpriseWon;
      weeklySales.push(enterpriseAccepted);
      for(const [id,firm]of Object.entries(competitors))firm.previousSales=used[id];
      prices.push({week,enterpriseCents:price,aiCents:competitors.ai.priceCents,humanMarkup:competitors.human.markup,
        offersSeen:enterpriseSeen,won:enterpriseWon,assetActive:f.assetActive});
    }
    f.balanceHistory.push({week,cashCents:f.cashCents,receivablesCents:receivable(f),obligationsCents:unpaid(f),
      reserveCents:c.reserveCents,availableCashCents:liquidity(f,c),earnedAvailableCents:operatingSurplus(f,c),
      cumulativeCollectionsCents:f.grossCollectionsCents,accruedCostsCents:sum(Object.values(f.costs)),
      paidCostsCents:sum(Object.values(f.paidCosts)),assetActive:f.assetActive,insolvent:f.insolvent});
  }
  const canonical=canonicalProjection(f,c),profit=canonical.economic.summary.scenario.operatingMargin;
  const directSaving=sum(jobs.filter(j=>j.provider==='enterprise'&&j.assetUsed).map(j=>
    round(unitCost(c,false)*(j.qualityGood?1:c.failureCorrectionMultiplier))-j.deliveryCostCents));
  const exactAssetCosts=f.costs.capability+f.costs.maintenance;
  const repayment=calculateInvestment({constructionCostMinor:exactAssetCosts,failedConstructionCostMinor:0,
    maintenancePerReuseMinor:0,expectedSavingPerReuseMinor:directSaving,remainingReuses:1});
  repayment.accountingUnit='One entire realized invocation cohort, including correction costs; not one production mission';
  repayment.actualInvocations=f.assetUses;
  repayment.jobBreakEvenReuses=null;
  const next={action:'retain-reserves',testedSuccessorPresent:c.nextAsset!==null,
    reason:c.nextAsset===null?'No separately constructed and tested worthwhile successor is supplied. Balance growth is not capability growth.':
      'Candidate successor supplied but requires separately frozen causal benefit evidence; not automatically purchased.',
    availableFromOperationsCents:operatingSurplus(f,c),actualFinancialAction:false};
  const cashReconstructed=f.openingCashCents+sum(f.cashEvents.map(x=>x.amountCents));
  assert(cashReconstructed===f.cashCents,'Cash history does not reconcile');
  assert(jobs.every(j=>j.accepted||!j.invoiceCreated),'Rejected task earned revenue');
  assert(f.investments.every(x=>x.availableCashCents>=x.fullCostCents),'Unaffordable investment');
  return {schema:SCHEMA,config:c,seed,arm,basis:'SIMULATED',observedCustomerCollectionsCents:0,
    productionEvidence:'Inherited6/6 and new joint-tuple4/4 scoped assessments each arm; no field-reliability estimate inferred.',
    summary:{opportunities,supportedOpportunities:supported,declined,enterpriseAttempts:f.attempts,
      enterpriseAccepted:f.accepted,enterpriseRejected:f.rejected,latentFailures:f.latentFailures,
      grossInvoicesCents:f.grossInvoicesCents,grossCollectionsCents:f.grossCollectionsCents,
      writtenOffCents:f.writtenOffCents,refundsCents:f.costs.refund,accruedCostsCents:sum(Object.values(f.costs)),
      paidCostsCents:sum(Object.values(f.paidCosts)),finalCashCents:f.cashCents,obligationsCents:unpaid(f),
      profitCents:profit,availableOperatingSurplusCents:operatingSurplus(f,c),insolvent:f.insolvent,
      insolvencyWeek:f.insolventWeek,investmentWeek:f.investments[0]?.week??null,assetActive:f.assetActive,
      failedInvestment:f.assetFailure,assetUses:f.assetUses,directAvoidedCostCents:directSaving,
      assetFullCostAndUpkeepCents:exactAssetCosts,directNetSavingCents:directSaving-exactAssetCosts,
      investmentCostBasis:c.investmentCostBasis,historicalCostRepaidClaimAllowed:c.investmentCostBasis==='full-history',
      directCostPayback:f.assetUses>0&&directSaving>=exactAssetCosts,actualRevenueCents:0},
    histories:{cash:f.cashEvents,balances:f.balanceHistory,invoices:f.invoices,bills:f.bills,buyerChoices,jobs,
      buyerProcurement:buyers.map(b=>({id:b.id,budgetCents:b.procurementBudgetCents,committedCents:b.committedProcurementCents})),feedback,
      investmentDecisions:decisions,investments:f.investments,competitorActions:competition,prices},
    competitorSummary:Object.fromEntries(Object.entries(competitors).map(([id,x])=>[id,{cashCents:x.cashCents,
      accepted:x.accepted,insolvent:x.insolvent,collectionsCents:x.grossCollectionsCents,accruedCostCents:sum(Object.values(x.costs))}])),
    exactAssetDirectCostRepayment:repayment,nextInvestment:next,canonical,
    limitations:['Behavioral repeated procurement simulation; no Nash equilibrium or optimal policy claim.',
      'Market value, effort, construction/inference costs, reliability, demand and payment behavior are assumption ranges.',
      'Primary uncertainty intervals summarize simulated worlds, not confidence in external profitability.',
      'No transaction, token financing, protocol settlement or operating authority is created.']};
}

export function pairedSimulation(config,seed=1,options={}){
  const arms=Object.fromEntries(['A','B','C'].map(arm=>[arm,simulate(config,seed,arm,options)]));
  return {schema:'agi-alpha-market-paired/v1',seed,config:arms.A.config,arms,
    causal:{B_minus_A_profitCents:arms.B.summary.profitCents-arms.A.summary.profitCents,
      C_minus_A_profitCents:arms.C.summary.profitCents-arms.A.summary.profitCents,
      B_minus_C_profitCents:arms.B.summary.profitCents-arms.C.summary.profitCents,
      B_minus_A_finalCashCents:arms.B.summary.finalCashCents-arms.A.summary.finalCashCents,
      B_C_behaviorallyIdentical:JSON.stringify(arms.B.summary)===JSON.stringify(arms.C.summary)}};
}

export const scenarios = [
  {id:'reference-assumptions'},
  {id:'zero-demand',arrivalProbability:0},
  {id:'low-demand',arrivalProbability:0.10},
  {id:'cheap-human',humanHourlyCents:2000,humanMarkup:1.02},
  {id:'cheap-ai',aiInitialPriceCents:500,aiCostCents:100,aiQuality:0.97,aiReviewMinutes:8},
  {id:'price-war',competitorStrategy:'undercut',competitorCostReduction:0.75,competitorImitationCostCents:1000},
  {id:'slow-collections',paymentDelayWeeks:13,paymentProbability:0.85},
  {id:'dissatisfied-buyers',successProbability:0.80,churnProbability:0.75,refundProbability:1},
  {id:'switching-barriers',integrationCents:5000,switchingCents:5000},
  {id:'quality-shock',qualityShockWeek:26,qualityShockFactor:0.70},
  {id:'high-maintenance',assetMaintenanceCentsPerWeek:2000},
  {id:'failed-improvement',assetFailureProbability:1,constructionHours:0.5,authoringCostCents:0},
  {id:'zero-attention-benefit',ordinaryFinalizationMinutes:0,assetResidualMinutes:0},
  {id:'free-perfect-diy',diyEffortFraction:0,diyQuality:1,diyDays:0,switchingCents:0,integrationCents:0},
  {id:'skeptical-buyers',initialTrust:0.70,skepticalShare:1},
  {id:'logit-choice',choiceModel:'logit'},
  {id:'cash-constrained',initialCashCents:30000,paymentDelayWeeks:13,weeklyOverheadCents:1000},
  {id:'full-price-pass-through',pricingPolicy:'cost-pass-through',expectedPassThrough:0.95},
  {id:'retrospective-cost-allocation',historicalCostTiming:'at-adoption'}
];
