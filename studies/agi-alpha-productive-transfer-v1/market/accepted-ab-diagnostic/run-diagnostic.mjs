// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync,existsSync,appendFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';

const base=dirname(fileURLToPath(import.meta.url)),study=resolve(base,'../..');
const args=process.argv.slice(2),get=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const freezePath=resolve(get('--freeze',resolve(base,'freeze.json')));
const output=resolve(get('--output',resolve(base,'results')));
const hash=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
const freeze=read(freezePath);
assert(freeze.status==='FROZEN_BEFORE_AB_DIAGNOSTIC_OUTCOMES'&&freeze.approvedBy==='root',
 'Concrete protocol and source freeze must be approved by root before diagnostic outcomes');
assert(Array.isArray(freeze.files),'Frozen file closure is required');
const required=[freeze.production,freeze.protocol,freeze.scenarios,'market/accepted-ab-diagnostic/run-diagnostic.mjs',
 'market/accepted-ab-diagnostic/accepted-ab.mjs','market/accepted-ab-diagnostic/audit-diagnostic.py',
 'market/market-transfer-core.mjs','market/inherited/market/canonical/shadow-ledger.mjs',
 'market/inherited/market/canonical/automated-costs.mjs','market/production-followup.json',
 'results/independent-followup-audit/summary.json','protocol/asset-B.json',
 'market/transfer-protocol.json','market/transfer-scenarios.json'];
assert(required.every(p=>typeof p==='string'&&freeze.files.some(f=>f.path===p)),'Incomplete frozen source/input closure');
assert(new Set(freeze.files.map(f=>f.path)).size===freeze.files.length,'Repeated frozen paths');
for(const f of freeze.files){
 const p=resolve(study,f.path);assert(p.startsWith(study+'/'),'Frozen paths must remain inside the contribution');
 assert(hash(p)===f.sha256,`Frozen file changed: ${f.path}`);
}
const production=read(resolve(study,freeze.production)),protocol=read(resolve(study,freeze.protocol));
const scenarios=read(resolve(study,freeze.scenarios));
assert(hash(resolve(study,freeze.production))===protocol.production.sha256,'Protocol production identity mismatch');
assert(hash(resolve(study,freeze.scenarios))===protocol.scenarioSHA256,'Protocol scenario identity mismatch');
assert(protocol.seedFirst===3001&&protocol.seedCount===8&&protocol.scenarioCount===24,'Exactly the registered fresh paired seeds and 24 cells are required');
assert(scenarios.length===24&&new Set(scenarios.map(s=>s.id)).size===24,'All 24 unique prespecified cells are required');
const originalScenarios=read(resolve(study,'market/transfer-scenarios.json'));
const originals=originalScenarios.filter(s=>s.class==='primary-no-unmeasured-benefit');
assert(originalScenarios.length===166&&originals.length===24,'Original blocked design must remain intact');
for(const s of scenarios){
 const original=originals.find(x=>x.id===s.inheritedScenarioId);
 assert(original&&JSON.stringify(original.shared)===JSON.stringify(s.shared),'No post-outcome stress tuning');
 for(const a of ['A','B'])assert(JSON.stringify(original.costs[a])===JSON.stringify(s.costs[a]),'No after-outcome cost tuning');
}
const audit=read(resolve(study,production.independentAcceptance.path));
assert(hash(resolve(study,production.independentAcceptance.path))===production.independentAcceptance.receiptSHA256,'Independent audit identity mismatch');
assert(audit.verifierSha256===production.independentAcceptance.verifierSHA256,'Verifier identity mismatch');
for(const row of production.independentAcceptance.rows){
 const original=audit.rows.find(r=>r.arm===row.arm&&r.task===row.task);
 assert(original&&Object.entries(row).every(([k,v])=>JSON.stringify(original[k])===JSON.stringify(v)),'Projected acceptance differs from independent audit');
}
const asset=read(resolve(study,production.acceptedAsset.path));
assert(hash(resolve(study,production.acceptedAsset.path))===production.acceptedAsset.sha256,'Exact B manifest changed');
assert(asset.id===production.acceptedAsset.id&&asset.label==='B'&&asset.completeAcceptedJobs===4&&asset.attemptedJobs===4,'Exact complete tested B asset required');
for(const f of asset.sourceClosure)assert(freeze.files.some(x=>x.path===f.path&&x.sha256===f.sha256),'Entire tested B source closure must be frozen');
const {conditionalAB,inspectAcceptedAB}=await import('./accepted-ab.mjs');
const economicIdentification=inspectAcceptedAB(production);
assert(economicIdentification.status==='COMPLETE_AB_ACCEPTED_WORK','Complete A/B acceptance required');
assert(!existsSync(output),'Refusing to overwrite preserved diagnostic outcomes');
mkdirSync(output,{recursive:true});
writeFileSync(resolve(output,'freeze-used.json'),readFileSync(freezePath));
writeFileSync(resolve(output,'economic-identification.json'),JSON.stringify(economicIdentification,null,2)+'\n');
const wall=performance.now(),cpu=process.cpuUsage(),summaries=[];
const stats=xs=>{const n=xs.length,mean=xs.reduce((a,b)=>a+b,0)/n;
 return {n,mean,minimum:Math.min(...xs),maximum:Math.max(...xs)};};
for(const scenario of scenarios){
 const rows=[];
 for(let k=0;k<protocol.seedCount;k++){
  const pair=conditionalAB(production,scenario,protocol.seedFirst+k);rows.push(pair);
  appendFileSync(resolve(output,'all-paired-histories.jsonl.gz'),gzipSync(JSON.stringify(pair)+'\n',{level:6,mtime:0}));
  for(const [arm,r] of Object.entries(pair.arms))appendFileSync(resolve(output,'outcomes.jsonl'),JSON.stringify({scenario:scenario.id,
   class:scenario.class,seed:r.seed,arm,...r.summary,differences:pair.differences})+'\n');
 }
 summaries.push({scenario:scenario.id,class:scenario.class,assumptions:scenario,
  arms:Object.fromEntries(['A','B'].map(a=>[a,{profitCents:stats(rows.map(p=>p.arms[a].summary.profitCents)),
   accepted:stats(rows.map(p=>p.arms[a].summary.enterpriseAccepted)),
   investments:rows.filter(p=>p.arms[a].summary.investmentWeek!==null).length,
   earnedFundedInvestments:rows.filter(p=>p.arms[a].histories.investments.some(i=>i.funding==='operating-surplus')).length,
   profitableWorlds:rows.filter(p=>p.arms[a].summary.profitCents>0).length,
   directRepaymentWorlds:rows.filter(p=>p.arms[a].summary.directCostPayback).length}])),
  differences:{B_minus_A_profitCents:stats(rows.map(p=>p.differences.B_minus_A_profitCents))}});
 process.stdout.write(JSON.stringify({completedScenario:scenario.id,seeds:rows.length})+'\n');
}
const cpuEnd=process.cpuUsage(cpu);
writeFileSync(resolve(output,'summary.json'),JSON.stringify({schema:'agi-alpha-accepted-ab-diagnostic-summary/v1',
 freezeSHA256:hash(freezePath),scenarioCount:24,seedCount:8,pairedWorlds:192,enterpriseHistories:384,
 economicIdentification,summaries,originalThreeArmCampaignStatus:'GATED_UNEXECUTED',
 interpretation:'Exploratory implementation/accounting negative control after accepted A/B production. Zero benefit is an assumed structural condition, not a measured treatment effect. Real complete costs and demand remain unidentified.',
 observedCustomerCollectionsCents:0,actualFinancialAction:false},null,2)+'\n');
writeFileSync(resolve(output,'completion.json'),JSON.stringify({completed:true,freezeSHA256:hash(freezePath),
 summarySHA256:hash(resolve(output,'summary.json')),historiesSHA256:hash(resolve(output,'all-paired-histories.jsonl.gz')),
 processWallSeconds:(performance.now()-wall)/1000,processCpuSeconds:(cpuEnd.user+cpuEnd.system)/1e6,
 monetaryModelCostCents:null,monetaryCostExplanation:'No complete billing record; process activity time is not a wage bill.'},null,2)+'\n');
