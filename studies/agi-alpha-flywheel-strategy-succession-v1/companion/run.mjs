// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import {createMissionStream} from './stream.mjs';
import {demoConfiguration,developmentConfiguration} from './scenarios.mjs';
import {createChecker} from './checker-client.mjs';
import {SOURCE_HASH,SOURCE_STATUS} from './binding.mjs';
import {verifySource} from './verify-source.mjs';

const args=process.argv.slice(2),arg=name=>{const i=args.indexOf(name);return i>=0?args[i+1]:null;};
verifySource({requireFrozen:args.includes('--confirm')});
const output=path.resolve(arg('--out')??'release-strategy-run');
const resume=args.includes('--resume'),supplied=arg('--config');
let config=supplied?JSON.parse(fs.readFileSync(supplied,'utf8')):args.includes('--development')?developmentConfiguration(Number(arg('--seed')??32001),{missions:Number(arg('--missions')??9)}):demoConfiguration({diagnostic:args.includes('--diagnostic')});
if(arg('--mode'))config.policy.mode=arg('--mode');
if(arg('--budget'))config.policy.totalWork=Number(arg('--budget'));
if(arg('--stage-budget'))config.policy.discoveryWork=Number(arg('--stage-budget'));
config.policy.actor='experiment-driver';
fs.mkdirSync(output,{recursive:true});fs.mkdirSync(path.join(output,'packs'),{recursive:true});
const checkpointPath=path.join(output,'checkpoint.json'),guardPath=path.join(output,'recovery-guard.json');
if(!resume&&fs.existsSync(checkpointPath))throw Error('OUTPUT_ALREADY_HAS_CHECKPOINT: use a new output or explicit --resume');
const atomic=(file,value)=>{const temporary=file+'.pending';fs.writeFileSync(temporary,JSON.stringify(value)+'\n');fs.renameSync(temporary,file);};
if(!resume)atomic(path.join(output,'configuration.json'),config);
let packNumber=fs.readdirSync(path.join(output,'packs')).length;
const checker=createChecker({python:arg('--python')??'python'}),wallStart=performance.now(),cpuStart=process.cpuUsage();
let stream;
const storage={async load(){return fs.existsSync(checkpointPath)?JSON.parse(fs.readFileSync(checkpointPath,'utf8')):null;},
 async save(snapshot){atomic(checkpointPath,snapshot);if(arg('--crash-at')==='intent'&&snapshot.pending)process.exit(23);if(arg('--crash-at')==='accepted'&&snapshot.cursor>=1)process.exit(24);},
 async loadGuard(){return fs.existsSync(guardPath)?JSON.parse(fs.readFileSync(guardPath,'utf8')):null;},async saveGuard(guard){atomic(guardPath,guard);}};
stream=createMissionStream({...config,storage,check:checker.check,
 onEvent(event){fs.appendFileSync(path.join(output,'events.jsonl'),JSON.stringify(event)+'\n');if(arg('--stop-after')&&event.kind==='RESULT'&&event.index+1>=Number(arg('--stop-after')))stream.stop('USER_STOP');},
 async onPack(pack,metadata){const file=`${String(packNumber++).padStart(5,'0')}-${metadata.phase}.json`;atomic(path.join(output,'packs',file),pack);},
 async onRecord(record){fs.appendFileSync(path.join(output,'raw-results.jsonl'),JSON.stringify(record)+'\n');}});
try{
 if(resume)await stream.load();
 const snapshot=await stream.start({resume,requestId:arg('--request-id')??'one-explicit-start'});
 const cpu=process.cpuUsage(cpuStart),summary={schema:'release-stream-summary/v1',source_hash:SOURCE_HASH,source_status:SOURCE_STATUS,
  mode:config.policy.mode,status:snapshot.status,reason:snapshot.reason,offered:config.tasks.length,attempted:snapshot.missions.length,
  valid:snapshot.missions.filter(m=>m.valid).length,qualified:snapshot.missions.filter(m=>m.qualified).length,work:snapshot.work,budget:config.policy.totalWork,
  assets:snapshot.assets.map(a=>({digest:a.digest,stage:a.stage,active:a.active,gate:a.gate.decision})),
  discovery:snapshot.discoveries.map(d=>({stage:d.stage,candidate:d.search?.candidate?.digest??null,decision:d.gate?.decision??d.decision??'NO_COMPLETE_CANDIDATE',acquisition:d.acquisition})),
  wall_ms:performance.now()-wallStart,node_cpu_ms:(cpu.user+cpu.system)/1000,python_cpu_ms:null,storage_bytes:snapshot.storage_bytes,
  interventions:snapshot.interventions,monetary_cost:null,engineering_labor_cost:null,
  note:'Measured Node CPU excludes the separate Python checker process; its deterministic operations are charged. Authoring, human commissioning and machine ownership costs are not priced.'};
 atomic(path.join(output,'summary.json'),summary);console.log(JSON.stringify(summary));
}finally{await checker.close();}
