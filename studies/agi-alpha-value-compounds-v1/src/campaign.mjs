// SPDX-License-Identifier: Apache-2.0
import {createSession,assetIdentity} from './workbench.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const directory=path.resolve(process.argv[2]||path.join(ROOT,'results/confirmation'));
await mkdir(directory,{recursive:false});
const registry=JSON.parse(await readFile(path.join(ROOT,'data/missions.json'),'utf8'));
const missions=Object.entries(registry.missions).filter(([,m])=>m.role==='held-out-historical-confirmation').map(([id])=>id);
if(missions.length!==12)throw Error('TWELVE_REGISTERED_TRANSITIONS_REQUIRED');
const arms=['incumbent','retained','conventional'],rows=[],sourceHash=await assetIdentity();
const started=new Date().toISOString();
for(let repetition=0;repetition<3;repetition++){
  const base=path.join(directory,'repeat-'+(repetition+1));await mkdir(base);
  const session=await createSession(path.join(base,'evidence'),path.join(base,'cache'));
  try{
    for(let index=0;index<missions.length;index++){
      const order=arms.map((_,j)=>arms[(j+index+repetition)%3]);
      for(const arm of order){
        const mission=missions[index],t=process.hrtime.bigint();
        try{
          const {pack,inspected}=await session.run(mission,arm);const file=path.join(base,mission+'-'+arm+'-pack.json');await writeFile(file,JSON.stringify(pack)+'\n');
          const packet=JSON.parse(pack.result.artifacts.find(a=>a.name==='upgrade-packet.json').content);
          const row={mission,arm,repetition:repetition+1,role:'timing-replicate-not-new-job',decision:pack.result.decision,summary:pack.result.summary,workbench_elapsed_ms:pack.economics.elapsedMilliseconds,whole_call_ns:Number(process.hrtime.bigint()-t),cpu_ns:packet.resources.cpu_ns,analysis_wall_ns:packet.resources.wall_ns,resources:packet.resources,pack:path.relative(ROOT,file),full_evidence:packet.full_evidence,authentication:inspected.authentication,consumer_coverage:packet.consumer_coverage,candidate_coverage:packet.candidate_coverage,functions:packet.summary?.functions||null,native_refusals:packet.summary?.native_source_refusals??null};
          rows.push(row);console.log(JSON.stringify({mission,arm,repetition:repetition+1,decision:row.decision,elapsed_ms:row.workbench_elapsed_ms,...row.summary}));
        }catch(error){rows.push({mission,arm,repetition:repetition+1,error:String(error),whole_call_ns:Number(process.hrtime.bigint()-t)});await writeFile(path.join(directory,'failure.json'),JSON.stringify({started,sourceHash,rows},null,2));throw error;}
        await writeFile(path.join(directory,'runs.json'),JSON.stringify({schema:'upgrade-campaign/v1',started,sourceHash,unique_registered_transitions:missions.length,timing_repetitions_are_jobs:false,rows},null,2)+'\n');
      }
    }
  }finally{session.close();}
}
await writeFile(path.join(directory,'COMPLETED.json'),JSON.stringify({started,completed:new Date().toISOString(),sourceHash,transitions:missions.length,executions:rows.length,actual_paid_jobs:0,all_operator_authority:[],runtime_model_calls:0},null,2)+'\n');
