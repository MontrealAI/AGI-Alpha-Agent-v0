// SPDX-License-Identifier: Apache-2.0
import {readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pairedSimulation} from './inherited/market/src/market.mjs';

const source='/workspace/scratch/da407bff0020/study/market';
const cases=[['primary','results/primary-01','stress-reference-assumptions',1001],
 ['primary','results/primary-01','primary-m0-h0.5-deterministic',1001],
 ['diagnostic','policy-diagnostic/results-01','policy-p2000-i0-a0.5-m10-logit-adoption-seed',2001]];
const rows=[];
for(const [kind,dir,id,seed] of cases){
 const cfg=JSON.parse(readFileSync(`${source}/${dir}/configurations.json`,'utf8')).find(x=>x.id===id);
 const old=readFileSync(`${source}/${dir}/outcomes.jsonl`,'utf8').trim().split('\n').map(x=>JSON.parse(x)).filter(x=>x.scenario===id&&x.seed===seed);
 const pair=pairedSimulation(cfg,seed,{includeOffers:true});
 for(const arm of ['A','B','C']){
  const recorded=old.find(x=>x.arm===arm),r=pair.arms[arm];
  const same=Object.keys(r.summary).every(k=>JSON.stringify(r.summary[k])===JSON.stringify(recorded[k]));
  if(!same)throw Error(`Immutable replay differs ${id} ${arm}`);
  const priceCensus={};
  for(const p of r.histories.prices){const k=p.enterpriseCents;priceCensus[k]??={weeks:0,offered:0,won:0};priceCensus[k].weeks++;priceCensus[k].offered+=p.offersSeen;priceCensus[k].won+=p.won;}
  const choices={};for(const c of r.histories.buyerChoices)choices[c.choice]=(choices[c.choice]||0)+1;
  rows.push({kind,scenario:id,seed,arm,summary_matches_preserved:true,summary:r.summary,priceCensus,choices});
 }
}
writeFileSync(new URL('./replay-audit.json',import.meta.url),JSON.stringify({schema:'agi-alpha-prior-source-replay/v1',executedUTC:new Date().toISOString(),coreSHA256:createHash('sha256').update(readFileSync(new URL('./inherited/market/src/market.mjs',import.meta.url))).digest('hex'),status:'PASS',cases:rows,interpretation:'Exact previously declared worlds replayed. No new production missions, independent market evidence, or confirmatory trials.'},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:'PASS',exactArmReplays:rows.length}));
