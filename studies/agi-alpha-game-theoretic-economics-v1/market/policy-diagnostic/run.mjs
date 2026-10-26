// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync,existsSync,appendFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {pairedSimulation,defaultConfig} from '../src/market.mjs';

const root=dirname(fileURLToPath(import.meta.url)),market=resolve(root,'..');
const args=process.argv.slice(2),get=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const out=resolve(get('--output',resolve(root,'results-01'))),freezePath=resolve(root,'freeze.json');
const sha=b=>createHash('sha256').update(b).digest('hex');
if(!existsSync(freezePath))throw Error('Reviewed pre-outcome policy freeze required');
const freeze=JSON.parse(readFileSync(freezePath,'utf8'));
for(const f of freeze.files)if(sha(readFileSync(resolve(market,f.path)))!==f.sha256)throw Error(`Frozen file changed: ${f.path}`);
if(existsSync(out))throw Error('Refusing to overwrite prior output');mkdirSync(out,{recursive:true});
const protocol=JSON.parse(readFileSync(resolve(root,'protocol.json'),'utf8')),configurations=[];
const priorRows=readFileSync(resolve(market,'exploratory/results-01/outcomes.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
const prior=new Map(priorRows.map(x=>[`${x.scenario}|${x.seed}|${x.arm}`,x]));
for(const price of protocol.grid.targetPriceCents)for(const integration of protocol.grid.integrationCents)
  for(const arrival of protocol.grid.arrivalProbability)for(const minutes of protocol.grid.ordinaryFinalizationMinutes)
    for(const choice of protocol.grid.choiceModel)for(const regime of protocol.grid.regimes){const {id,...funding}=regime;
      configurations.push({config:{id:`policy-p${price}-i${integration}-a${arrival}-m${minutes}-${choice}-${id}`,
        initialPriceCents:price,pricingPolicy:'fixed',integrationCents:integration,arrivalProbability:arrival,
        ordinaryFinalizationMinutes:minutes,choiceModel:choice,...funding},
      priorId:`explore-i${integration}-a${arrival}-m${minutes}-${choice}-${id}`});}
if(configurations.length!==protocol.total_configurations)throw Error('Configuration count mismatch');
writeFileSync(resolve(out,'configurations.json'),JSON.stringify(configurations.map(x=>({...defaultConfig,...x.config})),null,2)+'\n');
const seeds=Array.from({length:protocol.seeds.count},(_,i)=>protocol.seeds.first+i),summaries=[];
const stats=values=>{const mean=values.reduce((a,b)=>a+b,0)/values.length,
  sd=Math.sqrt(values.reduce((a,b)=>a+(b-mean)**2,0)/Math.max(1,values.length-1)),sorted=[...values].sort((a,b)=>a-b);
  return {n:values.length,mean,sd,meanInterval95:[mean-1.96*sd/Math.sqrt(values.length),mean+1.96*sd/Math.sqrt(values.length)],
    minimum:sorted[0],median:sorted[Math.floor((sorted.length-1)*.5)],maximum:sorted.at(-1)};};
const priceRange=values=>values.length?{minimumCents:Math.min(...values),maximumCents:Math.max(...values)}:null;
for(const {config,priorId}of configurations){
  const rows=[];
  for(const seed of seeds){const paired=pairedSimulation(config,seed);
    const capital=paired.arms.B.histories.bills.filter(x=>x.category==='capability').reduce((n,x)=>n+x.amountCents,0);
    const comparison=Object.fromEntries(['A','B','C'].map(arm=>{
      const baseline=prior.get(`${priorId}|${seed}|${arm}`);if(!baseline)throw Error('Matching heuristic world missing');
      if(baseline.opportunities!==paired.arms[arm].summary.opportunities||
        baseline.supportedOpportunities!==paired.arms[arm].summary.supportedOpportunities)throw Error('External common draws differ');
      return [arm,paired.arms[arm].summary.profitCents-baseline.profitCents];}));
    const posted=Object.fromEntries(['A','B','C'].map(arm=>[arm,{
      computedWeeklyQuotes:priceRange(paired.arms[arm].histories.prices.map(x=>x.enterpriseCents)),
      offeredQuotes:priceRange(paired.arms[arm].histories.prices.filter(x=>x.offersSeen>0).map(x=>x.enterpriseCents)),
      offeredBeforeAdoption:priceRange(paired.arms[arm].histories.prices.filter(x=>x.offersSeen>0&&!x.assetActive).map(x=>x.enterpriseCents)),
      offeredAfterAdoption:priceRange(paired.arms[arm].histories.prices.filter(x=>x.offersSeen>0&&x.assetActive).map(x=>x.enterpriseCents)),
      acceptedDeliveryPrices:priceRange(paired.arms[arm].histories.jobs.filter(x=>x.provider==='enterprise'&&x.accepted).map(x=>x.priceCents)),
      acceptedBeforeAdoption:priceRange(paired.arms[arm].histories.jobs.filter(x=>x.provider==='enterprise'&&x.accepted&&!x.assetUsed).map(x=>x.priceCents)),
      acceptedAfterAdoption:priceRange(paired.arms[arm].histories.jobs.filter(x=>x.provider==='enterprise'&&x.accepted&&x.assetUsed).map(x=>x.priceCents))}]));
    paired.policyDiagnostic={status:'POST_EXPLORATORY_NOT_CONFIRMATION',priorHeuristicScenario:priorId,
      targetPriceCents:config.initialPriceCents,priceRanges:posted,
      priceRangeScope:'All simulated: computed quotes may be unseen; offered quotes require offersSeen>0; accepted-delivery prices require accepted enterprise jobs.',
      policyMinusHeuristicProfitCents:comparison,
      B_oneoffCapabilityIncurredCents:capital,B_fixedPathMaximumOneoffCostCents:paired.causal.B_minus_A_profitCents+capital};
    appendFileSync(resolve(out,'complete-runs.jsonl.gz'),gzipSync(JSON.stringify(paired)+'\n',{level:6,mtime:0}));
    rows.push(paired);
    for(const [arm,run]of Object.entries(paired.arms))appendFileSync(resolve(out,'outcomes.jsonl'),JSON.stringify({scenario:config.id,
      seed,arm,...run.summary,causal:paired.causal,policyDiagnostic:paired.policyDiagnostic})+'\n');
  }
  const arms=Object.fromEntries(['A','B','C'].map(arm=>[arm,{
    profitCents:stats(rows.map(x=>x.arms[arm].summary.profitCents)),accepted:stats(rows.map(x=>x.arms[arm].summary.enterpriseAccepted)),
    collectionsCents:stats(rows.map(x=>x.arms[arm].summary.grossCollectionsCents)),
    finalCashCents:stats(rows.map(x=>x.arms[arm].summary.finalCashCents)),
    policyMinusHeuristicProfitCents:stats(rows.map(x=>x.policyDiagnostic.policyMinusHeuristicProfitCents[arm])),
    computedWeeklyQuoteRange:priceRange(rows.flatMap(x=>x.arms[arm].histories.prices.map(p=>p.enterpriseCents))),
    actualOfferedQuoteRange:priceRange(rows.flatMap(x=>x.arms[arm].histories.prices.filter(p=>p.offersSeen>0).map(p=>p.enterpriseCents))),
    actualBeforeAdoptionQuoteRange:priceRange(rows.flatMap(x=>x.arms[arm].histories.prices.filter(p=>p.offersSeen>0&&!p.assetActive).map(p=>p.enterpriseCents))),
    actualAfterAdoptionQuoteRange:priceRange(rows.flatMap(x=>x.arms[arm].histories.prices.filter(p=>p.offersSeen>0&&p.assetActive).map(p=>p.enterpriseCents))),
    acceptedDeliveryPriceRange:priceRange(rows.flatMap(x=>x.arms[arm].histories.jobs.filter(p=>p.provider==='enterprise'&&p.accepted).map(p=>p.priceCents))),
    investmentRate:rows.filter(x=>x.arms[arm].summary.investmentWeek!==null).length/rows.length,
    insolvencyRate:rows.filter(x=>x.arms[arm].summary.insolvent).length/rows.length,
    viableRate:rows.filter(x=>x.arms[arm].summary.profitCents>0&&!x.arms[arm].summary.insolvent&&x.arms[arm].summary.obligationsCents===0).length/rows.length,
    directRepaymentRate:rows.filter(x=>x.arms[arm].summary.directCostPayback).length/rows.length
  }]));
  summaries.push({scenario:config.id,config:{...defaultConfig,...config},priorHeuristicScenario:priorId,arms,
    causal:Object.fromEntries(['B_minus_A_profitCents','C_minus_A_profitCents','B_minus_C_profitCents'].map(k=>[k,stats(rows.map(x=>x.causal[k]))])),
    pathFixedMaximumOneoffCostCents:stats(rows.map(x=>x.policyDiagnostic.B_fixedPathMaximumOneoffCostCents)),
    B_C_exact_ties:rows.every(x=>x.causal.B_C_behaviorallyIdentical),
    B_positive_incremental_rate:rows.filter(x=>x.causal.B_minus_A_profitCents>0).length/rows.length,
    B_negative_incremental_rate:rows.filter(x=>x.causal.B_minus_A_profitCents<0).length/rows.length});
  process.stdout.write(JSON.stringify({scenario:config.id,finished:rows.length})+'\n');
}
writeFileSync(resolve(out,'summary.json'),JSON.stringify({schema:'agi-alpha-fixed-target-diagnostic-summary/v1',
  status:'POST_EXPLORATORY_POLICY_DIAGNOSTIC',freezeSHA256:sha(readFileSync(freezePath)),seeds,scenarios:summaries,
  allPriorResultsPreserved:true,intervals:'Conditional reused-seed Monte Carlo intervals; not independent confirmation or policy optimality.'},null,2)+'\n');
writeFileSync(resolve(out,'completion.json'),JSON.stringify({completed:true,configurations:configurations.length,seeds:seeds.length,
  pairedWorlds:configurations.length*seeds.length,enterpriseRuns:configurations.length*seeds.length*3,
  completeRunsSHA256:sha(readFileSync(resolve(out,'complete-runs.jsonl.gz'))),summarySHA256:sha(readFileSync(resolve(out,'summary.json'))),
  originalCoreSHA256:sha(readFileSync(resolve(market,'src/market.mjs'))),observedCollectionsCents:0,actualTransactions:0},null,2)+'\n');
