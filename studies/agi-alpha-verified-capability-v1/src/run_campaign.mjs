// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync,existsSync,readdirSync,statSync,realpathSync,lstatSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createFixtureResolver} from './authority.mjs';
import {createSelector} from './selection.mjs';
import {canonicalize} from './commitments.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const load=relative=>JSON.parse(readFileSync(path.join(ROOT,relative),'utf8'));
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const save=(relative,value)=>{const full=path.resolve(ROOT,relative);if(!full.startsWith(ROOT+path.sep))throw Error('STUDY_PATH_REQUIRED');mkdirSync(path.dirname(full),{recursive:true});writeFileSync(full,JSON.stringify(value,null,2)+'\n',{flag:'wx'});};
const cpuSeconds=usage=>(usage.user+usage.system)/1e6;
const enumerate=directory=>readdirSync(path.join(ROOT,directory)).sort().flatMap(name=>{const relative=directory+'/'+name;return statSync(path.join(ROOT,relative)).isDirectory()?(name==='__pycache__'?[]:enumerate(relative)):[relative];});

export function requiredFreezePaths() {
  const fixed=['protocol/research-design.json','protocol/mission-design.json','protocol/arm-order.json','protocol/asset-B.json','protocol/asset-C.json','protocol/acceptance-contract.json','protocol/market-design.json','market/cost-assumptions.json','market/adapter.mjs','market/run-campaign.mjs','market/asset-bindings.json','evidence/asset-admission.json','evidence/development/mission-input-identities-01.json'];
  const catalogue=load('evidence/catalog/catalog.json');
  const evidence=catalogue.forest.classes.evidence.records.flatMap(row=>row.record.files?.map(x=>x.path)||[]);
  return [...new Set([...fixed,...enumerate('src'),...enumerate('production'),...enumerate('native'),...enumerate('fixtures'),...enumerate('market/inherited'),...enumerate('inputs/missions-v1'),...enumerate('inputs/wheels'),...enumerate('evidence/catalog'),...evidence])].sort();
}

function validateFreeze(freeze,{full=false}={}) {
  if(freeze.schema!=='agi-alpha-verified-capability-production-freeze/v1'||freeze.freshOutcomesInspected!==false)throw Error('PRODUCTION_FREEZE_REQUIRED');
  if(!Array.isArray(freeze.files)||new Set(freeze.files.map(x=>x.path)).size!==freeze.files.length)throw Error('DUPLICATE_OR_MISSING_FREEZE_FILES');
  const included=new Set(freeze.files.map(x=>x.path));
  for(const required of requiredFreezePaths())if(!included.has(required))throw Error('INCOMPLETE_FREEZE:'+required);
  let count=0,bytes=0;
  for(const item of freeze.files){
    const wheel=item.path.startsWith('inputs/wheels/')&&item.path.endsWith('.whl');
    if((item.kind==='wheel')!==wheel)throw Error('FREEZE_KIND_MISMATCH');
    if(!full&&wheel)continue;
    const p=path.resolve(ROOT,item.path);if(!p.startsWith(ROOT+path.sep))throw Error('FREEZE_PATH');
    if(!realpathSync(p).startsWith(ROOT+path.sep))throw Error('FREEZE_REALPATH');
    for(let cur=p;cur!==ROOT;cur=path.dirname(cur))if(lstatSync(cur).isSymbolicLink())throw Error('FREEZE_SYMLINK');
    const raw=readFileSync(p);if(hash(raw)!==item.sha256||raw.length!==item.bytes)throw Error('FROZEN_SOURCE_OR_INPUT_CHANGED:'+item.path);
    count++;bytes+=raw.length;
  }
  return {files:count,bytes};
}

function execute(job,out,route) {
  return new Promise(resolve=>{
    const args=[path.join(ROOT,'src/measure_production.py'),'--job',path.join(ROOT,job),'--out',path.join(ROOT,out),'--route',route];
    const child=spawn('python3',args,{cwd:ROOT,stdio:['ignore','pipe','pipe']});let stdout='',stderr='';
    const timer=setTimeout(()=>{
      try{const group=load(out+'/process-group.json');if(group.parent_pid===child.pid&&Number.isSafeInteger(group.child_group_pid)&&group.child_group_pid>1)process.kill(-group.child_group_pid,'SIGKILL');}catch{}
      child.kill('SIGKILL');
    },200000);
    child.stdout.on('data',raw=>{stdout+=raw;if(stdout.length>3000000)child.kill('SIGKILL');});child.stderr.on('data',raw=>{stderr=(stderr+raw).slice(-12000);});
    child.on('error',error=>{clearTimeout(timer);resolve({code:-1,stdout,stderr:String(error)});});
    child.on('close',code=>{clearTimeout(timer);resolve({code,stdout,stderr});});
  });
}

export async function runCampaign({freezePath='protocol/production-freeze.json',output='evidence/production-primary'}={}) {
  if(existsSync(path.join(ROOT,output)))throw Error('PRESERVE_EXISTING_CAMPAIGN');
  const began=new Date().toISOString(),started=performance.now(),freeze=load(freezePath),initial=validateFreeze(freeze,{full:true});
  const catalog=load('evidence/catalog/catalog.json'),resolver=createFixtureResolver(load('fixtures/authority.json'));
  const selectors={B:createSelector(catalog,resolver,{strategy:'registry'}),C:createSelector(catalog,resolver,{strategy:'graph'})};
  const jobs=load('inputs/missions-v1/manifest.json').jobs.filter(x=>x.group!=='development'),orders=load('protocol/arm-order.json').orders;
  if(jobs.length!==18||orders.length!==18)throw Error('REGISTERED_COHORT_REQUIRED');
  if(jobs.filter(x=>x.group==='primary-composition').length!==15||jobs.filter(x=>x.group==='designed-root-stress').length!==3||new Set(jobs.map(x=>x.id)).size!==18||new Set(jobs.map(x=>x.job)).size!==18)throw Error('INVALID_COHORT_DENOMINATOR');
  const identityAudit=load('evidence/development/mission-input-identities-01.json');
  const semanticKeys=jobs.map(job=>{const row=identityAudit.rows.find(x=>x.id===job.id&&x.job_sha256===job.job_sha256&&x.group===job.group);if(!row?.manifest_matches)throw Error('UNAUDITED_MISSION_IDENTITY');return row.semantic_mission_key;});
  if(new Set(semanticKeys).size!==18)throw Error('DUPLICATED_SUBSTANTIVE_MISSION');
  if(orders.some(order=>typeof order!=='string'||[...order].sort().join('')!=='ABCD'))throw Error('INVALID_ARM_PERMUTATION');
  for(const arm of 'ABCD')for(let position=0;position<4;position++){const count=orders.filter(order=>order[position]===arm).length;if(count<4||count>5)throw Error('UNBALANCED_ARM_ORDER');}
  const bindings=load('market/asset-bindings.json');
  const startupCPU=cpuSeconds(process.cpuUsage()),startupWall=(performance.now()-started)/1000;
  const setupSpecific=selectors.B.construction.cpu_seconds+selectors.C.construction.cpu_seconds;
  const sharedCPU=Math.max(0,startupCPU-setupSpecific)/4,sharedWall=Math.max(0,startupWall-selectors.B.construction.elapsed_seconds-selectors.C.construction.elapsed_seconds)/4;
  const arms=Object.fromEntries([... 'ABCD'].map(arm=>[arm,{label:arm,mission_count:18,primary_count:15,stress_count:3,accepted_count:0,elapsed_seconds_total:sharedWall+(selectors[arm]?.construction.elapsed_seconds||0),cpu_seconds_total:sharedCPU+(selectors[arm]?.construction.cpu_seconds||0),tools_total:0,cache_confirmations:0,per_mission:[],initialization:{common_allocated_cpu:sharedCPU,common_allocated_wall:sharedWall,selector:selectors[arm]?.construction||null}}]));
  const raw=[];
  for(let i=0;i<jobs.length;i++)for(const arm of orders[i]){
    const job=jobs[i],relative=`${output}/${String(i+1).padStart(2,'0')}-${job.id}/${arm}`,begin=performance.now(),cpu=process.cpuUsage();
    const guardStart=performance.now(),guardCPU=process.cpuUsage(),priorGuard=validateFreeze(freeze);
    let guardWall=(performance.now()-guardStart)/1000,guardCpuSeconds=cpuSeconds(process.cpuUsage(guardCPU));
    const selection=selectors[arm]?.select(catalog.context)||null;
    const selected=selection?selection.ok&&selection.selected.at(-1)===catalog.targetSkill:true;
    const asset=arm==='B'||arm==='C'?(selected?bindings.assets[arm].id:null):null;
    save(relative+'/selection.json',{arm,selection,asset_id:asset,source_guard:priorGuard,fallback:!selected});
    const adjacentStart=performance.now(),adjacentCPU=process.cpuUsage();validateFreeze(freeze);
    guardWall+=(performance.now()-adjacentStart)/1000;guardCpuSeconds+=cpuSeconds(process.cpuUsage(adjacentCPU));
    const operation=await execute(job.job,relative+'/production',arm==='D'?'direct':'native');
    let packet=null,measurement=null;
    try{packet=load(relative+'/production/payload/packet.json');measurement=load(relative+'/production/measurement.json');}catch{}
    const postStart=performance.now(),postCPU=process.cpuUsage(),postGuard=validateFreeze(freeze);
    guardWall+=(performance.now()-postStart)/1000;guardCpuSeconds+=cpuSeconds(process.cpuUsage(postCPU));
    const usage=process.cpuUsage(cpu),elapsed=(performance.now()-begin)/1000,totalCPU=cpuSeconds(usage)+(measurement?.cpu_seconds||0);
    const packetMatches=packet?.job_id===job.id&&packet?.job_sha256===job.job_sha256&&packet?.mission_key===semanticKeys[i]&&packet?.route===(arm==='D'?'direct':'native')&&measurement?.returncode===operation.code;
    const row={id:job.id,cohort:job.group==='primary-composition'?'primary':'stress',families:job.families,arm,order:orders[i],accepted:packet?.accepted===true&&operation.code===0&&packetMatches,
      decision:packet?.decision||'INCOMPLETE',elapsed_seconds:elapsed,cpu_seconds:totalCPU,asset_id:asset,selection_used:Boolean(selection&&selected),selection_counters:selection?.counters||null,
      selection_elapsed_seconds:selection?.elapsed_seconds||0,selection_cpu_seconds:selection?.cpu_seconds||0,graph_state:selection?catalog.root.graphRoot:null,
      packet_path:relative+'/production/payload/packet.json',selection_path:relative+'/selection.json',packet_zip_path:relative+'/production/payload/decision-packet.zip',
      packet_sha256:packet?hash(readFileSync(path.join(ROOT,relative+'/production/payload/packet.json'))):null,mission_key:packet?.mission_key||null,
      production:measurement,tools:packet?.tools||null,operation:{code:operation.code,stderr:operation.stderr},guards:{before:priorGuard,after:postGuard},
      returned_packet_identity_matches:packetMatches,parent_cpu_seconds:cpuSeconds(usage),child_cpu_known:measurement!==null&&measurement.descendant_cpu_complete===true,unmeasured_child_cost:measurement===null||measurement.descendant_cpu_complete!==true?'UNKNOWN_NOT_ZERO':null,
      experimental_custody_overhead:{elapsed_seconds:guardWall,cpu_seconds:guardCpuSeconds,included_in_totals:true,interpretation:'Repeated registered source/protocol/input custody for research; report separately from deployment service latency.'},
      application_qualified:false,customer_acceptance_observed:false,actual_collections:0};
    save(relative+'/outcome.json',row);raw.push(row);arms[arm].per_mission.push(row);arms[arm].accepted_count+=Number(row.accepted);arms[arm].elapsed_seconds_total+=elapsed;arms[arm].cpu_seconds_total+=totalCPU;
    arms[arm].tools_total+=(packet?.tools?.pip_resolutions||0)+(packet?.tools?.metadata_verifications||0)+(selection?.counters?.proof_checks||0)+(selection?.counters?.attestation_checks||0);
    process.stdout.write(JSON.stringify({mission:i+1,arm,accepted:row.accepted,decision:row.decision,seconds:Number(elapsed.toFixed(4))})+'\n');
  }
  const confirmations=[];
  for(const arm of 'ABCD'){
    const begin=performance.now(),cpu=process.cpuUsage(),guard=validateFreeze(freeze,{full:true}),selection=selectors[arm]?.select(catalog.context)||null;
    const first=arms[arm].per_mission[0],packet=load(first.packet_path),currentJob=readFileSync(path.join(ROOT,jobs[0].job));
    const confirm=first.accepted&&hash(currentJob)===jobs[0].job_sha256&&hash(readFileSync(path.join(ROOT,first.packet_path)))===first.packet_sha256&&(!selection||selection.ok);
    const receipt={arm,mission_id:jobs[0].id,mission_key:packet.mission_key,cache_confirmation:confirm,new_completed_jobs:0,pip_resolutions:0,verification:'Frozen source, all wheel/input identities, cached packet bytes and current selection policy rechecked.',source_guard:guard,
      selection,elapsed_seconds:(performance.now()-begin)/1000,cpu_seconds:cpuSeconds(process.cpuUsage(cpu))};
    confirmations.push(receipt);arms[arm].cache_confirmations+=Number(confirm);save(output+'/cache-'+arm+'.json',receipt);
  }
  const finalGuard=validateFreeze(freeze,{full:true});
  const accountedParentCPU=startupCPU+raw.reduce((s,x)=>s+x.parent_cpu_seconds,0)+confirmations.reduce((s,x)=>s+x.cpu_seconds,0);
  const residualParentCPU=Math.max(0,cpuSeconds(process.cpuUsage())-accountedParentCPU);
  const accountedWall=startupWall+raw.reduce((s,x)=>s+x.elapsed_seconds,0)+confirmations.reduce((s,x)=>s+x.elapsed_seconds,0);
  const residualWall=Math.max(0,(performance.now()-started)/1000-accountedWall);
  for(const arm of 'ABCD'){arms[arm].cpu_seconds_total+=residualParentCPU/4;arms[arm].elapsed_seconds_total+=residualWall/4;arms[arm].initialization.final_shared_cpu=residualParentCPU/4;arms[arm].initialization.final_shared_wall=residualWall/4;}
  const summary={schema:'agi-alpha-verified-capability-production-summary/v1',started_at:began,completed_at:new Date().toISOString(),freeze_sha256:hash(readFileSync(path.join(ROOT,freezePath))),
    arms,raw_evaluations:raw.length,unique_substantive_missions:18,primary_composition_missions:15,designed_stress_missions:3,duplicate_requests:confirmations,
    duplicate_costs_separate_from_fresh_calibration:true,elapsed_seconds:(performance.now()-started)/1000,initial_guard:initial,final_guard:finalGuard,
    quality_equivalence:jobs.every(job=>{const group=raw.filter(x=>x.id===job.id);return group.length===4&&group.every(x=>x.accepted)&&new Set(group.map(x=>x.decision)).size===1;}),
    execution_costs_known:raw.every(row=>row.child_cpu_known),unmeasured_process_wall:'Node module/process startup before campaign clock; startup CPU included. Final summary serialization after final sampling.',
    cost_boundary:'Complete measured execution includes selector and source/input custody plus producer startup/descendants/report packaging. Shared process initialization equally allocated; selector initialization allocated to its arm. Cache confirmations separate, no new jobs. Actual complete authoring/inference/attention/upkeep costs unknown.',
    runtime:{node:process.version,platform:process.platform,architecture:process.arch},live_identity_enforcement:'NOT_RUN',customer_acceptance:null,actual_collections:0,settlement_connected:false};
  save(output+'/summary.json',summary);save('evidence/production-summary.json',summary);return summary;
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
  if(!process.argv.includes('--run'))throw Error('Explicit --run required after registered freeze');
  const take=(key,fallback)=>{const at=process.argv.indexOf(key);return at<0?fallback:process.argv[at+1];};
  const result=await runCampaign({freezePath:take('--freeze','protocol/production-freeze.json'),output:take('--output','evidence/production-primary')});
  console.log(JSON.stringify({done:true,quality_equivalence:result.quality_equivalence,arms:Object.fromEntries(Object.entries(result.arms).map(([k,v])=>[k,{accepted:v.accepted_count,cpu:v.cpu_seconds_total,elapsed:v.elapsed_seconds_total}]))}));
}
