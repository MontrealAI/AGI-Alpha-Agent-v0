// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {makePlan,runPlan} from '../automation-v1/run-mission.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const protocol=JSON.parse(await readFile(join(here,'PROTOCOL.json'),'utf8'));
const runner=await readFile(join(here,'../automation-v1/run-mission.mjs'));
assert.equal(createHash('sha256').update(runner).digest('hex'),protocol.candidate_runner_sha256);
await mkdir(join(here,'plans'),{recursive:true});
const outcomes=[];
for(const [index,manifestPath] of protocol.fresh_manifest_scopes.entries()) {
  const planned=await makePlan({manifestPath,sourceRef:protocol.source_commit,runId:'completion-scope-'+(index+1),
    maxAttempts:4,maxTotalSeconds:80});
  await writeFile(join(here,'plans',planned.plan.runId+'.json'),JSON.stringify(planned,null,2)+'\n',{flag:'wx'});
  const options={approvalDigest:planned.approvalDigest,outputRoot:join(here,'runs')};
  if(index===1)await runPlan(planned.plan,{...options,stopAfter:'preparation'});
  const delivered=await runPlan(planned.plan,options),reconnected=await runPlan(planned.plan,options);
  assert.equal(delivered.accepted,true);assert.equal(reconnected.reconnected,true);
  outcomes.push({runId:planned.plan.runId,manifestPath,sourceCount:planned.plan.sourceCount,
    accepted:delivered.accepted,changedPaths:JSON.parse(await readFile(join(here,'runs',planned.plan.runId,'acceptance.json'))).changedPaths,
    processMode:'local-node-api',connectedExecution:'NOT RUN',
    completeOrdinal:delivered.authorization.ordinal,reconnectOrdinal:reconnected.authorization.ordinal,
    reconnectObservations:reconnected.reconnectObservations,
    fullMonetaryCost:{value:null,basis:'unknown',reference:'No measured hardware, attributable engineering/upkeep or transport price.'}});
}
await writeFile(join(here,'fresh-outcomes.json'),JSON.stringify({attemptedRequests:3,acceptedRequests:outcomes.filter(row=>row.accepted).length,
  checkpointsAndRechecksAreJobs:false,outcomes},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({attemptedRequests:3,acceptedRequests:outcomes.filter(row=>row.accepted).length,sourceRows:outcomes.reduce((n,row)=>n+row.sourceCount,0)}));
