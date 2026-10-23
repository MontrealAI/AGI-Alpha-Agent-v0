// SPDX-License-Identifier: Apache-2.0
import {parentPort} from 'node:worker_threads';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {solve,createWorkspace} from '../enterprise/compiler.mjs';
import {reference,stable} from './checker.mjs';
import {createQualifier} from './qualifier.mjs';
const q=await createQualifier(path.join(path.dirname(fileURLToPath(import.meta.url)),'../enterprise'));
parentPort.postMessage({ready:true});
parentPort.on('message',async ({id,mission,failFirst,attempt})=>{
  const start=performance.now();
  if(failFirst&&attempt===0){parentPort.postMessage({id,error:'INJECTED_TRANSIENT_BEFORE_COMPUTE',elapsedMs:0});return;}
  try{
    const candidate=solve(mission,{workspace:createWorkspace({id:'load-local'})});
    const expected=reference(mission);let accepted=false,qualification=null;
    if(candidate.status==='complete'&&candidate.delivery.status==='ready'){
      qualification=await q.qualify(mission.kind);
      const groups=candidate.rows.map(r=>({group:r.group,total:Number(r.amount)}));
      accepted=expected.accepted&&stable({groups,total:groups.reduce((s,r)=>s+r.total,0)})===stable(expected.output);
    }
    parentPort.postMessage({id,status:candidate.status,accepted,correct:expected.accepted?accepted:!accepted,expectedValid:expected.accepted,elapsedMs:performance.now()-start,operations:candidate.metrics.operations,hashBytes:candidate.metrics.hashBytes,qualification:qualification?.counts??null,currentProof:null,authority:[]});
  }catch(error){parentPort.postMessage({id,error:error.message,elapsedMs:performance.now()-start});}
});
