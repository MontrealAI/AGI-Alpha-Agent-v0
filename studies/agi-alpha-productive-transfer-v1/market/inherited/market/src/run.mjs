// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync,existsSync,appendFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {pairedSimulation,scenarios,defaultConfig} from './market.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2),get=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const out=resolve(get('--output',resolve(root,'results','primary')));
const freezePath=resolve(get('--freeze',resolve(root,'protocol','freeze.json')));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
if(!existsSync(freezePath))throw Error('A reviewed pre-outcome freeze is required');
const freeze=JSON.parse(readFileSync(freezePath,'utf8'));
for(const f of freeze.files)if(sha(readFileSync(resolve(root,f.path)))!==f.sha256)throw Error(`Frozen source changed: ${f.path}`);
if(existsSync(out))throw Error('Refusing to overwrite a previous result directory');
mkdirSync(out,{recursive:true});
const protocol=JSON.parse(readFileSync(resolve(root,'protocol/protocol.json'),'utf8'));
const configurations=[];
for(const minutes of protocol.primary_grid.ordinaryFinalizationMinutes)
  for(const hours of protocol.primary_grid.constructionHours)
    for(const choice of protocol.primary_grid.choiceModel)configurations.push({id:`primary-m${minutes}-h${hours}-${choice}`,
      ordinaryFinalizationMinutes:minutes,constructionHours:hours,choiceModel:choice});
for(const minutes of protocol.adoption_grid.ordinaryFinalizationMinutes)
  for(const hours of protocol.adoption_grid.adoptionHours)
    for(const choice of protocol.adoption_grid.choiceModel)configurations.push({id:`adoption-grid-m${minutes}-h${hours}-${choice}`,
      ordinaryFinalizationMinutes:minutes,adoptionHours:hours,choiceModel:choice,investmentCostBasis:'adoption-only'});
for(const scenario of scenarios)configurations.push({...scenario,id:`stress-${scenario.id}`});
for(const scenario of scenarios.filter(x=>['reference-assumptions','low-demand','cheap-ai','slow-collections'].includes(x.id)))
  configurations.push({...scenario,id:`adoption-${scenario.id}`,investmentCostBasis:'adoption-only'});
writeFileSync(resolve(out,'configurations.json'),JSON.stringify(configurations.map(c=>({...defaultConfig,...c})),null,2)+'\n');
const seeds=Array.from({length:protocol.primary_grid.seeds.count},(_,i)=>protocol.primary_grid.seeds.first+i);
const summaries=[];
const stats=values=>{const mean=values.reduce((a,b)=>a+b,0)/values.length;
  const sd=Math.sqrt(values.reduce((a,b)=>a+(b-mean)**2,0)/Math.max(1,values.length-1));
  const sorted=[...values].sort((a,b)=>a-b),pct=p=>sorted[Math.floor((sorted.length-1)*p)];
  return {n:values.length,mean,sd,meanInterval95:[mean-1.96*sd/Math.sqrt(values.length),mean+1.96*sd/Math.sqrt(values.length)],
    minimum:sorted[0],p05:pct(.05),median:pct(.5),p95:pct(.95),maximum:sorted.at(-1)};};
for(const config of configurations){
  const rows=[];
  for(const seed of seeds){
    const paired=pairedSimulation(config,seed);
    appendFileSync(resolve(out,'complete-runs.jsonl.gz'),gzipSync(JSON.stringify(paired)+'\n',{level:6,mtime:0}));
    rows.push(paired);
    for(const [arm,run]of Object.entries(paired.arms))appendFileSync(resolve(out,'outcomes.jsonl'),JSON.stringify({scenario:config.id,
      seed,arm,...run.summary,causal:paired.causal})+'\n');
  }
  const arms=Object.fromEntries(['A','B','C'].map(arm=>[arm,{
    profitCents:stats(rows.map(r=>r.arms[arm].summary.profitCents)),
    accepted:stats(rows.map(r=>r.arms[arm].summary.enterpriseAccepted)),
    collectionsCents:stats(rows.map(r=>r.arms[arm].summary.grossCollectionsCents)),
    finalCashCents:stats(rows.map(r=>r.arms[arm].summary.finalCashCents)),
    investmentRate:rows.filter(r=>r.arms[arm].summary.investmentWeek!==null).length/rows.length,
    insolvencyRate:rows.filter(r=>r.arms[arm].summary.insolvent).length/rows.length,
    viableRate:rows.filter(r=>r.arms[arm].summary.profitCents>0&&!r.arms[arm].summary.insolvent&&r.arms[arm].summary.obligationsCents===0).length/rows.length,
    directRepaymentRate:rows.filter(r=>r.arms[arm].summary.directCostPayback).length/rows.length
  }]));
  const summary={scenario:config.id,config:{...defaultConfig,...config},arms,
    causal:Object.fromEntries(['B_minus_A_profitCents','C_minus_A_profitCents','B_minus_C_profitCents'].map(k=>[k,stats(rows.map(r=>r.causal[k]))])),
    B_C_exact_ties:rows.every(r=>r.causal.B_C_behaviorallyIdentical),
    B_positive_incremental_rate:rows.filter(r=>r.causal.B_minus_A_profitCents>0).length/rows.length,
    B_negative_incremental_rate:rows.filter(r=>r.causal.B_minus_A_profitCents<0).length/rows.length};
  summaries.push(summary);
  process.stdout.write(JSON.stringify({scenario:config.id,finished:rows.length})+'\n');
}
writeFileSync(resolve(out,'summary.json'),JSON.stringify({schema:'agi-alpha-market-campaign-summary/v1',
  freezeSHA256:sha(readFileSync(freezePath)),seeds,scenarios:summaries,
  intervals:'Conditional Monte Carlo intervals only; not empirical confidence in profitability.'},null,2)+'\n');
writeFileSync(resolve(out,'completion.json'),JSON.stringify({completed:true,pairedWorlds:configurations.length*seeds.length,
  enterpriseRuns:configurations.length*seeds.length*3,configurations:configurations.length,seeds:seeds.length,
  completeRunsSHA256:sha(readFileSync(resolve(out,'complete-runs.jsonl.gz'))),summarySHA256:sha(readFileSync(resolve(out,'summary.json'))),
  observedCollectionsCents:0,actualTransactions:0},null,2)+'\n');
