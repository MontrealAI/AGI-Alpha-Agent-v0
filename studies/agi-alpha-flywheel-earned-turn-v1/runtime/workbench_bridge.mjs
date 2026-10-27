// SPDX-License-Identifier: Apache-2.0
import {createInterface} from 'node:readline';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {createWorkbench} from './vendor/examples/successor-workbench/engine.mjs';
import {parseBounded} from './vendor/docs/assets/successor/engine.mjs';

const manifest=JSON.parse(await readFile(new URL('./vendor/WORKBENCH_MANIFEST.json',import.meta.url),'utf8'));
for(const file of manifest.files){
  const bytes=await readFile(new URL('./vendor/'+file.path,import.meta.url));
  if(bytes.length!==file.bytes||createHash('sha256').update(bytes).digest('hex')!==file.sha256)throw Error('VENDOR_SOURCE_MISMATCH');
}
const write=value=>process.stdout.write(JSON.stringify(value)+'\n');
const exact=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|');
const safeId=value=>typeof value==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(value);
let active=null;
const seen=new Set();
const adapter={
  manifest:{id:'earned-turn-numerical',version:1,en:'Verify a reusable numerical instrument',fr:'Vérifier un instrument numérique réutilisable',
    scope:'Bounded public or synthetic numerical analysis dispatched to the fixed local research callback; no native service or operational authority.',artifact:'numerical-result.json'},
  validate(input){
    if(!exact(input,['mission_id','purpose','payload_json'])||!safeId(input.mission_id)||typeof input.purpose!=='string'||!input.purpose.trim()||input.purpose.length>1000||
      typeof input.payload_json!=='string'||Buffer.byteLength(input.payload_json)>120000)throw Error('NUMERICAL_INPUT_SCOPE');
    const parsed=JSON.parse(input.payload_json);
    if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))throw Error('NUMERICAL_INPUT_OBJECT');
  },
  async execute(input,checkpoint){
    await checkpoint('Out-Execute');
    if(!active||active.id!==input.mission_id)throw Error('CALLBACK_BINDING');
    const response=await new Promise((resolve,reject)=>{
      active.resolve=resolve;active.reject=reject;
      write({kind:'execute',id:input.mission_id,payload_json:input.payload_json});
    });
    await checkpoint('Out-Evolve');
    if(typeof response.report_json!=='string'||Buffer.byteLength(response.report_json)>190000)throw Error('REPORT_LIMIT');
    const report=JSON.parse(response.report_json);
    if(typeof report.valid!=='boolean'||typeof report.qualified!=='boolean'||report.qualified&&!report.valid||typeof report.summary!=='string'||report.summary.length>2000)throw Error('REPORT_SCOPE');
    return {decision:report.valid?(report.qualified?'QUALIFIED_LOCAL_RESULT':'VALID_TARGET_NOT_MET'):'REFUSED',
      summary:{mission_id:input.mission_id,valid:report.valid,qualified:report.qualified,description:report.summary},
      evidence:{input_sha256:createHash('sha256').update(input.payload_json).digest('hex'),
        report_sha256:createHash('sha256').update(response.report_json).digest('hex'),
        executor:'Fixed local Python callback, dispatched by this source-installed workbench adapter',
        independent_final_proof:false,active_proof:[],active_authority:[]},
      artifacts:[{name:'numerical-result.json',type:'application/json',content:response.report_json+'\n'}],
      limits:['Local source execution; neither maintained native CampaignOperation nor an authenticated hosted executor.',
        'Numerical checks and research admission remain separately scoped; the upstream institutional admission stays HOLD.',
        'The callback is trusted packaged developer code. Report integrity alone does not prove numerical truth.',
        'No credentials, payment, contract invocation or operational authority.']};
  }
};
const runtime=createWorkbench([adapter]);
async function run(message){
  const state=active,started=performance.now(),cpu=process.cpuUsage();
  try{
    if(!/^[a-f0-9]{64}$/.test(message.source_hash||''))throw Error('SOURCE_IDENTITY_REQUIRED');
    const spec={schema:'successor-workbench/v1',family:adapter.manifest.id,name:'AGI ALPHA · Earned Turn',language:'en',owner:'local-research-owner',
      rights:{dataClass:'synthetic',source:'Bounded numerical study inputs; source and provenance in exact mission JSON',license:'Apache-2.0'},reviewMinutes:10,
      inputs:{mission_id:message.id,purpose:message.purpose,payload_json:message.payload_json}};
    const pack=await runtime.run(spec,{sourceHash:message.source_hash,signal:state.controller.signal,
      onProgress:phase=>write({kind:'phase',id:message.id,phase})});
    const inspection=await runtime.inspectPack(pack);
    const elapsed=process.cpuUsage(cpu);
    write({kind:'complete',id:message.id,pack,inspection,wall_ms:performance.now()-started,node_cpu_us:elapsed.user+elapsed.system});
  }catch(error){
    const elapsed=process.cpuUsage(cpu);
    write({kind:'failed',id:message.id,error:String(error.message||error),wall_ms:performance.now()-started,node_cpu_us:elapsed.user+elapsed.system});
  }finally{if(active===state)active=null;}
}
const rl=createInterface({input:process.stdin,crlfDelay:Infinity});
write({kind:'ready',runtime:'released-alpha-workbench-v1.42.0',vendor_files:manifest.files.length,node:process.version,
  authentication:'LOCAL_UNAUTHENTICATED_SOURCE_EXECUTION',production_authority:[]});
for await(const line of rl){
  try{
    if(Buffer.byteLength(line)>500000)throw Error('TRANSPORT_LIMIT');
    const message=JSON.parse(line);
    if(message.kind==='run'){
      if(active)throw Error('BUSY');
      if(!safeId(message.id)||seen.has(message.id))throw Error('DUPLICATE_OR_INVALID_REQUEST');
      seen.add(message.id);active={id:message.id,controller:new AbortController(),resolve:null,reject:null};
      run(message);
    }else if(message.kind==='result'){
      if(!active||message.id!==active.id||!active.resolve)throw Error('UNEXPECTED_RESULT');
      const resolve=active.resolve;active.resolve=null;resolve(message);
    }else if(message.kind==='cancel'){
      if(active&&message.id===active.id){active.controller.abort();if(active.reject){active.reject(Error('CANCELLED'));active.resolve=null;active.reject=null;}}
    }else if(message.kind==='inspect'){
      const inspection=await runtime.inspectPack(parseBounded(message.pack_json));
      write({kind:'inspected',id:message.id,inspection});
    }else if(message.kind==='close'){
      if(active)throw Error('BUSY');rl.close();break;
    }else throw Error('TRANSPORT_KIND');
  }catch(error){write({kind:'protocol_error',error:String(error.message||error)});}
}
if(active?.reject)active.reject(Error('TRANSPORT_CLOSED'));
