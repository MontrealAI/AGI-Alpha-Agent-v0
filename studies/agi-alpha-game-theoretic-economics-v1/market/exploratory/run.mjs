// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync,existsSync,appendFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {pairedSimulation,scenarios,defaultConfig} from '../src/market.mjs';

const root=dirname(fileURLToPath(import.meta.url)),market=resolve(root,'..');
const args=process.argv.slice(2),get=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const out=resolve(get('--output',resolve(root,'results-01'))),freezePath=resolve(root,'freeze.json');
const sha=b=>createHash('sha256').update(b).digest('hex');
if(!existsSync(freezePath))throw Error('Pre-outcome exploratory freeze required');
const freeze=JSON.parse(readFileSync(freezePath,'utf8'));
for(const f of freeze.files)if(sha(readFileSync(resolve(market,f.path)))!==f.sha256)throw Error(`Frozen file changed: ${f.path}`);
if(existsSync(out))throw Error('Refusing to overwrite prior output');mkdirSync(out,{recursive:true});
const protocol=JSON.parse(readFileSync(resolve(root,'protocol.json'),'utf8')),configurations=[];
for(const integration of protocol.grid.integrationCents)for(const arrival of protocol.grid.arrivalProbability)
  for(const minutes of protocol.grid.ordinaryFinalizationMinutes)for(const choice of protocol.grid.choiceModel)
    for(const regime of protocol.grid.regimes){const {id,...funding}=regime;
      configurations.push({id:`explore-i${integration}-a${arrival}-m${minutes}-${choice}-${id}`,
        integrationCents:integration,arrivalProbability:arrival,ordinaryFinalizationMinutes:minutes,choiceModel:choice,...funding});}
for(const stressId of protocol.corners.stress_scenario_ids)for(const regimeId of protocol.corners.regime_ids){
  const {id,...funding}=protocol.grid.regimes.find(x=>x.id===regimeId),stress=scenarios.find(x=>x.id===stressId);
  configurations.push({...stress,...funding,id:`corner-${stressId}-${id}`,integrationCents:protocol.corners.integrationCents,
    ordinaryFinalizationMinutes:protocol.corners.ordinaryFinalizationMinutes,arrivalProbability:protocol.corners.arrivalProbability,
    choiceModel:protocol.corners.choiceModel});
}
if(configurations.length!==protocol.total_configurations)throw Error('Configuration count mismatch');
writeFileSync(resolve(out,'configurations.json'),JSON.stringify(configurations.map(x=>({...defaultConfig,...x})),null,2)+'\n');
const seeds=Array.from({length:protocol.seeds.count},(_,i)=>protocol.seeds.first+i),summaries=[];
const stats=values=>{const mean=values.reduce((a,b)=>a+b,0)/values.length,
  sd=Math.sqrt(values.reduce((a,b)=>a+(b-mean)**2,0)/Math.max(1,values.length-1)),sorted=[...values].sort((a,b)=>a-b);
  return {n:values.length,mean,sd,meanInterval95:[mean-1.96*sd/Math.sqrt(values.length),mean+1.96*sd/Math.sqrt(values.length)],
    minimum:sorted[0],median:sorted[Math.floor((sorted.length-1)*.5)],maximum:sorted.at(-1)};};
for(const config of configurations){
  const rows=[];
  for(const seed of seeds){const paired=pairedSimulation(config,seed);
    const capital=paired.arms.B.histories.bills.filter(x=>x.category==='capability').reduce((n,x)=>n+x.amountCents,0);
    paired.exploratory={status:'POSTPRIMARY_EXPLORATORY',B_oneoffCapabilityIncurredCents:capital,
      B_fixedPathMaximumOneoffCostCents:paired.causal.B_minus_A_profitCents+capital,
      thresholdScope:'Fixed realized path only; K changes can change policy, funding, timing and demand. Not a global break-even bound.'};
    appendFileSync(resolve(out,'complete-runs.jsonl.gz'),gzipSync(JSON.stringify(paired)+'\n',{level:6,mtime:0}));
    rows.push(paired);
    for(const [arm,run]of Object.entries(paired.arms))appendFileSync(resolve(out,'outcomes.jsonl'),JSON.stringify({scenario:config.id,
      seed,arm,...run.summary,causal:paired.causal,exploratory:paired.exploratory})+'\n');
  }
  const arms=Object.fromEntries(['A','B','C'].map(arm=>[arm,{
    profitCents:stats(rows.map(x=>x.arms[arm].summary.profitCents)),accepted:stats(rows.map(x=>x.arms[arm].summary.enterpriseAccepted)),
    collectionsCents:stats(rows.map(x=>x.arms[arm].summary.grossCollectionsCents)),
    finalCashCents:stats(rows.map(x=>x.arms[arm].summary.finalCashCents)),
    investmentRate:rows.filter(x=>x.arms[arm].summary.investmentWeek!==null).length/rows.length,
    insolvencyRate:rows.filter(x=>x.arms[arm].summary.insolvent).length/rows.length,
    viableRate:rows.filter(x=>x.arms[arm].summary.profitCents>0&&!x.arms[arm].summary.insolvent&&x.arms[arm].summary.obligationsCents===0).length/rows.length,
    directRepaymentRate:rows.filter(x=>x.arms[arm].summary.directCostPayback).length/rows.length
  }]));
  summaries.push({scenario:config.id,config:{...defaultConfig,...config},arms,
    causal:Object.fromEntries(['B_minus_A_profitCents','C_minus_A_profitCents','B_minus_C_profitCents'].map(k=>[k,stats(rows.map(x=>x.causal[k]))])),
    pathFixedMaximumOneoffCostCents:stats(rows.map(x=>x.exploratory.B_fixedPathMaximumOneoffCostCents)),
    B_C_exact_ties:rows.every(x=>x.causal.B_C_behaviorallyIdentical),
    B_positive_incremental_rate:rows.filter(x=>x.causal.B_minus_A_profitCents>0).length/rows.length,
    B_negative_incremental_rate:rows.filter(x=>x.causal.B_minus_A_profitCents<0).length/rows.length});
  process.stdout.write(JSON.stringify({scenario:config.id,finished:rows.length})+'\n');
}
writeFileSync(resolve(out,'summary.json'),JSON.stringify({schema:'agi-alpha-exploratory-market-summary/v1',
  status:'POSTPRIMARY_EXPLORATORY_NOT_CONFIRMATION',freezeSHA256:sha(readFileSync(freezePath)),seeds,scenarios:summaries,
  originalPrimaryPreserved:true,intervals:'Conditional Monte Carlo intervals only, not empirical confidence in profitability.'},null,2)+'\n');
writeFileSync(resolve(out,'completion.json'),JSON.stringify({completed:true,configurations:configurations.length,seeds:seeds.length,
  pairedWorlds:configurations.length*seeds.length,enterpriseRuns:configurations.length*seeds.length*3,
  completeRunsSHA256:sha(readFileSync(resolve(out,'complete-runs.jsonl.gz'))),summarySHA256:sha(readFileSync(resolve(out,'summary.json'))),
  originalCoreSHA256:sha(readFileSync(resolve(market,'src/market.mjs'))),observedCollectionsCents:0,actualTransactions:0},null,2)+'\n');
