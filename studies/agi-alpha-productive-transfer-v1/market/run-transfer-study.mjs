// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync,existsSync,appendFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';

const base=dirname(fileURLToPath(import.meta.url));
const args=process.argv.slice(2),get=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const freezePath=resolve(get('--freeze',resolve(base,'transfer-freeze.json')));
const output=resolve(get('--output',resolve(base,'transfer-results')));
const hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const freeze=JSON.parse(readFileSync(freezePath,'utf8'));
if(freeze.status!=='FROZEN_BEFORE_MARKET_OUTCOMES')throw Error('Pre-outcome source/protocol/input freeze required');
const required=[freeze.production,freeze.protocol,freeze.scenarios,'run-transfer-study.mjs','transfer-adapter.mjs',
 'market-transfer-core.mjs','inherited/market/canonical/shadow-ledger.mjs','inherited/market/canonical/automated-costs.mjs'];
if(required.some(p=>typeof p!=='string'||!freeze.files.some(f=>f.path===p)))throw Error('Incomplete frozen source/input closure');
for(const f of freeze.files){
 const p=resolve(base,f.path);if(!p.startsWith(base+'/'))throw Error('Freeze path outside package');
 if(hash(p)!==f.sha256)throw Error(`Frozen identity changed: ${f.path}`);
}
if(existsSync(output))throw Error('Refusing to overwrite preserved outcomes');
const {conditionalPair,identificationDecision}=await import('./transfer-adapter.mjs');
const production=JSON.parse(readFileSync(resolve(base,freeze.production),'utf8'));
const protocol=JSON.parse(readFileSync(resolve(base,freeze.protocol),'utf8'));
const scenarios=JSON.parse(readFileSync(resolve(base,freeze.scenarios),'utf8'));
if(!Number.isSafeInteger(protocol.seedFirst)||!Number.isSafeInteger(protocol.seedCount)||protocol.seedCount<1||protocol.seedCount>64)throw Error('Bounded declared seed protocol required');
if(scenarios.length>256||scenarios.length<1||new Set(scenarios.map(s=>s.id)).size!==scenarios.length)throw Error('Unique bounded scenarios required');
mkdirSync(output,{recursive:true});
const start=performance.now(),cpu=process.cpuUsage();
const economicIdentification=identificationDecision(production);
writeFileSync(resolve(output,'economic-identification.json'),JSON.stringify(economicIdentification,null,2)+'\n');
const summaries=[];
for(const scenario of scenarios){
 const rows=[];
 for(let k=0;k<protocol.seedCount;k++){
  const result=conditionalPair(production,scenario,protocol.seedFirst+k);
  appendFileSync(resolve(output,'all-paired-histories.jsonl.gz'),gzipSync(JSON.stringify(result)+'\n',{level:6,mtime:0}));
  rows.push(result);
  for(const [arm,r]of Object.entries(result.arms))appendFileSync(resolve(output,'outcomes.jsonl'),JSON.stringify({scenario:scenario.id,
   class:scenario.class,seed:r.seed,arm,...r.summary,differences:result.differences})+'\n');
 }
 const stats=xs=>{const n=xs.length,mean=xs.reduce((a,b)=>a+b,0)/n,sd=Math.sqrt(xs.reduce((a,b)=>a+(b-mean)**2,0)/Math.max(1,n-1));
  return {n,mean,minimum:Math.min(...xs),maximum:Math.max(...xs),conditionalMonteCarloInterval95:[mean-1.96*sd/Math.sqrt(n),mean+1.96*sd/Math.sqrt(n)]};};
 summaries.push({scenario:scenario.id,class:scenario.class,assumptions:scenario,
  arms:Object.fromEntries(['A','B','C'].map(a=>[a,{profitCents:stats(rows.map(x=>x.arms[a].summary.profitCents)),
   accepted:stats(rows.map(x=>x.arms[a].summary.enterpriseAccepted)),
   investments:rows.filter(x=>x.arms[a].summary.investmentWeek!==null).length,
   earnedFundedInvestments:rows.filter(x=>x.arms[a].histories.investments.some(i=>i.funding==='operating-surplus')).length,
   profitableWorlds:rows.filter(x=>x.arms[a].summary.profitCents>0).length,
   directRepaymentWorlds:rows.filter(x=>x.arms[a].summary.directCostPayback).length}])),
  differences:Object.fromEntries(['B_minus_A_profitCents','C_minus_A_profitCents','B_minus_C_profitCents'].map(k=>[k,stats(rows.map(x=>x.differences[k]))]))});
 process.stdout.write(JSON.stringify({completedScenario:scenario.id,seeds:rows.length})+'\n');
}
const endCpu=process.cpuUsage(cpu);
writeFileSync(resolve(output,'summary.json'),JSON.stringify({schema:'agi-alpha-intake-transfer-market-summary/v1',freezeSHA256:hash(freezePath),
 scenarioCount:scenarios.length,seedCount:protocol.seedCount,pairedWorlds:scenarios.length*protocol.seedCount,
 enterpriseHistories:scenarios.length*protocol.seedCount*3,economicIdentification,summaries,
 basis:'Conditional simulation only; interval excludes uncertainty in model identification. No empirical customers, collected money or solved equilibrium.',
 observedCustomerCollectionsCents:0,actualFinancialAction:false},null,2)+'\n');
writeFileSync(resolve(output,'completion.json'),JSON.stringify({completed:true,freezeSHA256:hash(freezePath),
 summarySHA256:hash(resolve(output,'summary.json')),historiesSHA256:hash(resolve(output,'all-paired-histories.jsonl.gz')),
 processWallSeconds:(performance.now()-start)/1000,processCpuSeconds:(endCpu.user+endCpu.system)/1000000,
 monetaryModelCostCents:null,monetaryCostExplanation:'No billing record; process timing is not a wage bill.'},null,2)+'\n');
