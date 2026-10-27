// SPDX-License-Identifier: Apache-2.0
// Offline reproducible policy search, independent confirmation and paired stresses.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {createGzip} from 'node:zlib';
import {once} from 'node:events';
import {BASE,SCENARIOS,POLICIES,RETAIN_POLICIES,TRAIN_SEEDS,CONFIRM_SEEDS,STRESS_SEEDS,SENSITIVITIES,AGENTS,ASSETS,JOB_CLASSES} from './config.mjs';
import {simulate} from './simulator.mjs';
import {mean,quantile,summarize,paired,distribution,frequency} from './statistics.mjs';
import {auditRun,auditPaired} from '../tests/economics_audit.mjs';
import {orderedPool} from './pool.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const hash=x=>createHash('sha256').update(x).digest('hex');
const read=f=>JSON.parse(fs.readFileSync(path.join(ROOT,f),'utf8'));
const write=(f,x)=>{const p=path.join(ROOT,f);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,JSON.stringify(x,null,2)+'\n');};
const args=process.argv.slice(2),command=args[0];
function files(dir){return fs.readdirSync(path.join(ROOT,dir),{withFileTypes:true}).flatMap(d=>d.isDirectory()?files(`${dir}/${d.name}`):[`${dir}/${d.name}`]);}
function assertAbsent(p){if(fs.existsSync(path.join(ROOT,p)))throw Error(`Refusing to overwrite ${p}`);}
function verifyFreeze(){const F=read('protocol/freeze.json');for(const [p,h]of Object.entries(F.sourceHashes))if(hash(fs.readFileSync(path.join(ROOT,p)))!==h)throw Error(`Frozen source changed: ${p}`);return F;}
function protocol(){return {schema:'beyond-beta-protocol/v1',createdAt:new Date().toISOString(),
 evidence:'Modeled study; all economic events simulated',questions:['Beta economics relative to matched human-team work','Incremental net Alpha','Network availability and optional adoption','Moving-Beta erosion','Optional productive investment'],
 hypotheses:{H1:'Some scoped Beta service configurations earn positive complete-cost profit below a matched human reference.',
  H2:'A complementary representation/certificate bundle retained from paid delivery can add net value after incremental extraction, assessment and upkeep, without charging its source job twice.',
  H3:'Network availability creates additional value only when non-equivalent recipients have enough applicable fresh demand.',
  H4:'Moving Beta can erase advantage and rationally trigger revalidation, retirement or restraint.',
  H5:'A retained experiment protocol may lower the cost of fresh invention campaigns; descendant job volume alone is not evidence.'},
 objective:{score:'mean discounted accrued profit + 0.25 * mean of worst 10% discounted accrued profits',
  trainingConstraint:'Modeled insolvency frequency <=5%; if no policy satisfies, select lowest observed insolvency then highest score and report violation',
  components:'Cash, full profit, useful outcomes, retained capabilities and errors reported separately. No mandatory investment count.',
  tieBreak:'Higher score, then lower insolvency, then lexical policy ID'},
 selection:{seeds:TRAIN_SEEDS,policyCount:POLICIES.length+RETAIN_POLICIES.length,policies:[...POLICIES,...RETAIN_POLICIES],
  perScenario:['enterprise: best of all policies','network: best investment-enabled policy; may rationally make no investment','beta: best no-investment policy']},
 confirmation:{seeds:CONFIRM_SEEDS,arms:['enterprise','beta','network','same-price-beta','local','no-bundle','representation-only','certificate-only','no-alpha-effect','static-beta','no-paid-learning','no-separate-research'],
  pairedContrasts:[['network','same-price-beta'],['network','local'],['network','no-bundle'],['network','no-alpha-effect'],['network','static-beta'],['enterprise','beta'],['network','no-paid-learning'],['network','no-separate-research']],
  statisticalUnit:'Independent network/world seed. Descendant jobs and repeated policy histories are not independent invention campaigns.',
  intervals:'Empirical5th/95th percentiles; normal Monte Carlo mean interval; Wilson binomial interval. These do not measure epistemic parameter uncertainty.'},
 scenarios:SCENARIOS,sensitivity:{seeds:STRESS_SEEDS,oneFactors:SENSITIVITIES,policy:'Frozen central network selection',paired:'same-price-beta'},
 scale:{selectionSeeds:Array.from({length:12},(_,i)=>1035000+i),confirmationSeeds:Array.from({length:12},(_,i)=>1060000+i),selectionObjective:'Same downside-adjusted discounted-profit objective, separately per demand level; hardware choice locked before fresh capacity confirmation.',prospectsMonthly:[12,48,144],concurrency:[1,3,8],quotaMultiplier:[1,4],policy:'Frozen favorable network selection',baseScenario:'favorable',
  note:'Compute/quotas are equal across each paired network/Beta comparison. Higher-capacity conditions are separate counterfactual scenarios, not demonstrated entitlements.'},
 nullControls:['zero customer demand','zero improvement probability','zero productive construction probability','no Alpha resource or certificate advantage','full Beta absorption'],
 assumptions:{paidLearning:'A job pays for its own formulation, search, learning and correction. B contains only additional retention and reuse. Optional C research is separately chosen and charged. Prospective Alpha excludes already-accounted source-job A; consolidated profit keeps A+B+C.',
  fullyAutomated:true,routineProviderHumanHours:0,actualSales:0,actualFrontierExecution:0,actualGraphDeployment:false,
  pricing:'Buyer prices and human references are contingent on acceptance in this matched modeled contract; published GSA rates do not establish those contract terms.',
  beta:'Current official Astra Pro max and Terra max; strong ordinary solvers, context, automated critique/correction and generic cheap checks in every arm.',
  roles:'Models support authorized roles; neither model choice nor identity grants a new right.',
  movingBeta:'Hypothetical version after stated week, not an announced future model. Job model tokens and search compute improve; independent validator CPU and fixed ancillary budgets do not automatically shrink.',
  revalidation:'All stale/version-changed/retired records fail closed; fresh paid paired probes are required. An already executing or queued job may be quarantined, with actual costs and conservative capacity reservation retained.',
  nodeValue:'Graph size/downloads do not enter buyer utility or investment benefits.',
  historicalCosts:'A declared historical research allowance is charged without representing unknown actual past expenses.',
  tariffHorizon:'Current documented tariffs and rate anchors are held nominally fixed over two modeled years; future prices are not claimed documented.'},
 agents:AGENTS,assets:ASSETS,jobs:JOB_CLASSES,
 preservation:'Earlier studies and unrun designs are preserved separately. Generic verified accounting, resource budgeting and exact upstream authority/commitment primitives are reused; no earlier workload or result criterion is inherited.'};}
function freeze(){assertAbsent('protocol/freeze.json');write('protocol/protocol.json',protocol());
 const selected=[...files('model'),...files('graph'),...files('upstream'),...files('tests'),...files('evidence').filter(f=>/\.(json|md)$/.test(f)),
  ...files('protocol').filter(f=>!/freeze/.test(f))].filter(f=>!f.endsWith('.log'));
 const sourceHashes=Object.fromEntries([...new Set(selected)].sort().map(f=>[f,hash(fs.readFileSync(path.join(ROOT,f)))]));
 const F={schema:'beyond-beta-freeze/v1',frozenAt:new Date().toISOString(),sourceHashes,registeredScientificSeedsExecuted:0,
  priorChecks:'Only labeled synthetic software-control seeds; no training/confirmation seed inspected before this freeze.'};
 write('protocol/freeze.json',F);const sha=hash(fs.readFileSync(path.join(ROOT,'protocol/freeze.json')));
 fs.writeFileSync(path.join(ROOT,'protocol/freeze.sha256'),`${sha}  freeze.json\n`);console.log(JSON.stringify({freezeSHA256:sha,files:selected.length}));}
function score(rows){const x=rows.map(r=>r.discountedAccrualProfitCents).sort((a,b)=>a-b),tail=x.slice(0,Math.max(1,Math.ceil(x.length*.1))),risk=rows.filter(r=>r.insolvent).length/rows.length;
 return {scoreCents:mean(x)+.25*mean(tail),meanDiscountedProfitCents:mean(x),cvar10Cents:mean(tail),insolvencyRate:risk,eligible:risk<=.05};}
function select(scored,kind){let pool=scored.filter(x=>kind==='network'?x.policy.allowInvestment:kind==='beta'?!x.policy.allowInvestment:true);
 const feasible=pool.filter(x=>x.eligible),constraintSatisfied=feasible.length>0;
 if(constraintSatisfied)pool=feasible;else{const low=Math.min(...pool.map(x=>x.insolvencyRate));pool=pool.filter(x=>x.insolvencyRate===low);}
 pool.sort((a,b)=>b.scoreCents-a.scoreCents||a.insolvencyRate-b.insolvencyRate||a.policy.id.localeCompare(b.policy.id));
 return {...pool[0],constraintSatisfied,selectionKind:kind};}
function csv(rows){const keys=[...new Set(rows.flatMap(x=>Object.keys(x)))];const cell=v=>{const s=v===null||v===undefined?'':String(v);return /[\n,\"]/.test(s)?`"${s.replaceAll('"','""')}"`:s;};return keys.join(',')+'\n'+rows.map(r=>keys.map(k=>cell(r[k])).join(',')).join('\n')+'\n';}
async function train(){verifyFreeze();assertAbsent('results/training.json');const records=[],selected={},scores={};
 const tasks=SCENARIOS.flatMap(C=>[...POLICIES,...RETAIN_POLICIES].map(P=>({kind:'train',C,P,seeds:TRAIN_SEEDS})));
 await orderedPool(tasks,async(out,task,index)=>{records.push(...out.rows);(scores[task.C.id]??=[]).push({policy:task.P,...score(out.rows),outcomes:summarize(out.rows)});
  if(index%15===0)console.log(JSON.stringify({trainingPolicy:index+1,total:tasks.length}));});
 for(const C of SCENARIOS){selected[C.id]=Object.fromEntries(['enterprise','network','beta'].map(k=>[k,select(scores[C.id],k)]));
 console.log(JSON.stringify({trainingScenario:C.id,selected:Object.fromEntries(Object.entries(selected[C.id]).map(([k,v])=>[k,v.policy.id]))}));}
 write('results/training.json',{frozenProtocolSHA:hash(fs.readFileSync(path.join(ROOT,'protocol/freeze.json'))),independentSeeds:TRAIN_SEEDS,selected,rows:records});
 fs.writeFileSync(path.join(ROOT,'results/training.csv'),csv(records));
 const selection={schema:'beyond-beta-policy-selection/v1',selectedAt:new Date().toISOString(),trainingSHA256:hash(fs.readFileSync(path.join(ROOT,'results/training.json'))),
  protocolSHA256:hash(fs.readFileSync(path.join(ROOT,'protocol/freeze.json'))),selected,confirmationSeedsInspected:0};
 write('protocol/selected_policies.json',selection);console.log(JSON.stringify({selectionSHA256:hash(fs.readFileSync(path.join(ROOT,'protocol/selected_policies.json')))}));}

function planArms(C,S){const n=S.network.policy;return [
 ['enterprise',S.enterprise.policy,'none'],['beta',S.beta.policy,'beta-only'],['network',n,'none'],['same-price-beta',n,'beta-only'],
 ['local',n,'alpha-local'],['no-bundle',n,'no-bundle'],['representation-only',n,'representation-only'],['certificate-only',n,'certificate-only'],
 ['no-alpha-effect',n,'no-alpha-effect'],['static-beta',n,'static-beta'],['no-paid-learning',n,'no-paid-learning'],['no-separate-research',n,'no-separate-research']];}
function compactPlan(p){if(!p)return p;const {roleUsage,...out}=p;
 if(out.diagnostics){const {candidateHistory,...d}=out.diagnostics;out.diagnostics=d;}
 if(out.probeCases)delete out.probeCases;return out;}
function compactRun(run){const h=run.histories;
 for(const j of h.jobs)j.plan=compactPlan(j.plan);
 for(const a of h.auxiliary)a.plan=compactPlan(a.plan);
 for(const d of h.decisions){delete d.alphaBound;d.construction=compactPlan(d.construction);}
 for(const a of h.campaigns){a.construction=compactPlan(a.construction);a.review.review=compactPlan(a.review.review);}
 for(const a of h.revalidations)a.review.review=compactPlan(a.review.review);
 return run;}
async function writer(file){assertAbsent(file);const stream=fs.createWriteStream(path.join(ROOT,file)),gz=createGzip({level:6});gz.pipe(stream);
 return {async add(x){if(!gz.write(JSON.stringify(x)+'\n'))await once(gz,'drain');},async close(){gz.end();await once(stream,'close');return {bytes:fs.statSync(path.join(ROOT,file)).size,sha256:hash(fs.readFileSync(path.join(ROOT,file)))};}};}
async function confirm(){const F=verifyFreeze(),selection=read('protocol/selected_policies.json');assertAbsent('results/confirmation.json');
 const ledger=await writer('results/confirmation_ledgers.jsonl.gz'),rows=[],audit={runs:0,bills:0,cashEvents:0,jobs:0,campaigns:0,revalidations:0,passed:true};
 const tasks=SCENARIOS.flatMap(C=>CONFIRM_SEEDS.map(seed=>({kind:'confirm',C,seed,arms:planArms(C,selection.selected[C.id])})));
 await orderedPool(tasks,async(out,task,index)=>{for(const {run,audit:checked}of out.runs){const arm=run.arm,seed=run.seed,C=task.C;
   for(const k of ['bills','cashEvents','jobs','campaigns','revalidations'])audit[k]+=checked[k];audit.runs++;
   rows.push({...run.summary});
   if(seed===CONFIRM_SEEDS[0])write(`results/examples/${C.id}_${arm}.json`,run);
   if(arm==='network'&&run.summary.peerUsefulOutcomes>0&&!fs.existsSync(path.join(ROOT,`results/examples/${C.id}_first_peer_reuse.json`)))write(`results/examples/${C.id}_first_peer_reuse.json`,run);
   if(arm==='network'&&run.summary.paidOriginAdmissions>0&&!fs.existsSync(path.join(ROOT,`results/examples/${C.id}_first_paid_alpha.json`)))write(`results/examples/${C.id}_first_paid_alpha.json`,run);
   await ledger.add(run);
  }if(index%24===0)console.log(JSON.stringify({confirmedWorlds:index+1,total:tasks.length,runs:audit.runs}));});
 const archive=await ledger.close(),scenarios={};
 for(const C of SCENARIOS){const r=rows.filter(x=>x.scenario===C.id);scenarios[C.id]={arms:Object.fromEntries([...new Set(r.map(x=>x.arm))].map(arm=>[arm,summarize(r.filter(x=>x.arm===arm))])),
  contrasts:Object.fromEntries(read('protocol/protocol.json').confirmation.pairedContrasts.map(([a,b])=>[`${a}_minus_${b}`,paired(r,a,b)]))};}
 const result={schema:'beyond-beta-confirmation/v1',protocolSHA256:hash(fs.readFileSync(path.join(ROOT,'protocol/freeze.json'))),selectionSHA256:hash(fs.readFileSync(path.join(ROOT,'protocol/selected_policies.json'))),
  independentWorlds:CONFIRM_SEEDS.length*SCENARIOS.length,policyHistories:rows.length,scenarios,rows,ledgerArchive:archive,audit};
 write('results/confirmation.json',result);fs.writeFileSync(path.join(ROOT,'results/confirmation.csv'),csv(rows));write('results/confirmation_audit.json',audit);
 console.log(JSON.stringify({confirmationComplete:true,...audit,archive}));}
async function stress(kind){verifyFreeze();const S=read('protocol/selected_policies.json').selected;const out=`results/${kind}.json`;assertAbsent(out);
 const rows=[],cases=[];
 if(kind==='sensitivity')for(const [parameter,values]of SENSITIVITIES)for(const value of values)cases.push({id:`${parameter}=${value}`,C:{...BASE,[parameter]:value},parameter,value,seeds:STRESS_SEEDS,P:S.central.network.policy});
 else for(const leads of [12,48,144])for(const slots of [1,3,8])for(const q of [1,4]){
  const f=SCENARIOS.find(c=>c.id==='favorable');cases.push({id:`L${leads}C${slots}Q${q}`,C:{...f,prospectsMonthly:leads,concurrency:slots,inputQuotaWeekly:f.inputQuotaWeekly*q,
   outputQuotaWeekly:f.outputQuotaWeekly*q,cpuHoursWeekly:f.cpuHoursWeekly*q,validatorHoursWeekly:f.validatorHoursWeekly*q},parameter:'scale',value:`${leads}/${slots}/${q}`,seeds:Array.from({length:12},(_,i)=>1035000+i),P:S.favorable.network.policy});}
 const ledger=await writer(`results/${kind}_ledgers.jsonl.gz`);let audits=0;
 const tasks=cases.flatMap(x=>x.seeds.map(seed=>({kind:'stress',C:x.C,seed,case:x.id,parameter:x.parameter,value:x.value,
  arms:[['network',x.P,'none'],['same-price-beta',x.P,'beta-only']]})));
 await orderedPool(tasks,async(result,task,index)=>{for(const {run}of result.runs){audits++;rows.push(run.summary);await ledger.add(run);}
  if(index%100===0)console.log(JSON.stringify({[kind]:task.case,worlds:index+1,total:tasks.length,auditedRuns:audits}));});
 let capacitySelection=null,capacityHoldoutRows=[];
 if(kind==='scale'){
  capacitySelection={selectedAt:new Date().toISOString(),confirmationSeedsInspected:0,selections:{}};
  for(const leads of [12,48,144]){
   const candidates=cases.filter(x=>x.C.prospectsMonthly===leads).map(x=>({case:x.id,config:x.C,...score(rows.filter(r=>r.case===x.id&&r.arm==='network'))}));
   const feasible=candidates.filter(x=>x.eligible),pool=feasible.length?feasible:candidates.filter(x=>x.insolvencyRate===Math.min(...candidates.map(y=>y.insolvencyRate)));
   pool.sort((a,b)=>b.scoreCents-a.scoreCents||a.case.localeCompare(b.case));capacitySelection.selections[leads]={...pool[0],constraintSatisfied:feasible.length>0};
  }
  write('protocol/selected_capacity.json',capacitySelection);
  const holdoutTasks=Object.values(capacitySelection.selections).flatMap(x=>Array.from({length:12},(_,i)=>({kind:'stress',C:x.config,seed:1060000+i,
    case:x.case,parameter:'capacity-holdout',value:x.config.prospectsMonthly,arms:[['network',S.favorable.network.policy,'none'],['same-price-beta',S.favorable.network.policy,'beta-only']]})));
  await orderedPool(holdoutTasks,async(result)=>{for(const {run}of result.runs){audits++;capacityHoldoutRows.push(run.summary);await ledger.add(run);}});
  for(const [leads,selection]of Object.entries(capacitySelection.selections)){
    const h=capacityHoldoutRows.filter(r=>r.case===selection.case);selection.holdout={network:summarize(h.filter(r=>r.arm==='network')),
     beta:summarize(h.filter(r=>r.arm==='same-price-beta')),contrast:paired(h,'network','same-price-beta')};
  }
 }
 for(const x of cases){const local=rows.filter(r=>r.case===x.id);x.summary={network:summarize(local.filter(r=>r.arm==='network')),
  beta:summarize(local.filter(r=>r.arm==='same-price-beta')),contrast:paired(local,'network','same-price-beta')};delete x.seeds;delete x.P;}

 const archive=await ledger.close();write(out,{schema:`beyond-beta-${kind}/v1`,cases,rows,capacitySelection,capacityHoldoutRows,auditedRuns:audits,archive});
 fs.writeFileSync(path.join(ROOT,`results/${kind}.csv`),csv(rows));console.log(JSON.stringify({[kind]:'complete',cases:cases.length,runs:audits,archive}));}

if(command==='freeze')freeze();else if(command==='train')await train();else if(command==='confirm')await confirm();
else if(command==='sensitivity'||command==='scale')await stress(command);else throw Error('Use freeze, train, confirm, sensitivity, or scale');
