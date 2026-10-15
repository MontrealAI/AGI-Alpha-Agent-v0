// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import {parseBounded} from '../../docs/assets/successor/engine.mjs';
import {importManagerCycle,inspectContinuity,advanceContinuity,LIMIT} from './continuity.mjs';
function read(file){if(fs.statSync(file).size>LIMIT)throw Error('CONTINUITY_INPUT_SIZE');return fs.readFileSync(file,'utf8');}
async function main(){
  const [action,input,managerCheckout,alphaBaselineCheckout,...rest]=process.argv.slice(2),options={managerCheckout,alphaBaselineCheckout};let raw,output;
  if(action==='import'&&rest.length===5){const [spec,cycleId,missionId,ack,dest]=rest;if(ack!=='--new-public-data-cycle')throw Error('Explicit new-cycle selection required');output=dest;raw=await importManagerCycle(read(input),{spec:parseBounded(read(spec)),cycleId,missionId,acknowledgement:'new-public-data-cycle'},options);}
  else if(action==='run'&&rest.length===1){output=rest[0];raw=await advanceContinuity(read(input),options);}
  else if(action==='inspect'&&rest.length===0){const {project,continuity,managerSummary}=await inspectContinuity(read(input),options);console.log(JSON.stringify({projectId:project.projectId,cycles:project.cycles.length,alphaCheckpoints:continuity.history.length,managerCheckpoints:managerSummary.checkpoints,authority:'none',qualification:'not-evaluated',settlement:'not-connected'},null,2));return;}
  else throw Error('Usage: import TRANSFER MANAGER_CHECKOUT ALPHA_BASELINE SPEC CYCLE_ID MISSION_ID --new-public-data-cycle OUTPUT; run FILE MANAGER_CHECKOUT ALPHA_BASELINE OUTPUT; inspect FILE MANAGER_CHECKOUT ALPHA_BASELINE');
  fs.writeFileSync(output,raw,{flag:'wx',mode:0o600});console.log('Saved verified history; no authority, funding or protected evaluation granted.');
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
