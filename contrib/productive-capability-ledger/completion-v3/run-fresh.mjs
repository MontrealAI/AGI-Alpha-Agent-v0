// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {makePlan,runPlan} from '../automation-v1/run-mission.mjs';

const here=dirname(fileURLToPath(import.meta.url)),sourceRef='443246db37b30b83f4b9c8a854ceb226601e0155';
const protocol=JSON.parse(await readFile(join(here,'PROTOCOL.json'),'utf8'));
assert.equal(createHash('sha256').update(await readFile(join(here,'../automation-v1/run-mission.mjs'))).digest('hex'),protocol.candidateRunnerSha256);
const planned=await makePlan({manifestPath:'contrib/productive-capability-ledger/completion-v3/previous-published-source.json',
  sourceRef,runId:'reviewed-source-change',maxAttempts:4,maxTotalSeconds:80});
await writeFile(join(here,'approved-plan.json'),JSON.stringify(planned,null,2)+'\n',{flag:'wx'});
const options={approvalDigest:planned.approvalDigest,outputRoot:join(here,'runs')};
await runPlan(planned.plan,{...options,stopAfter:'execution'});
const result=await runPlan(planned.plan,options),reconnected=await runPlan(planned.plan,options);
const acceptance=JSON.parse(await readFile(join(here,'runs',planned.plan.runId,'acceptance.json')));
assert.equal(result.accepted,true);assert.equal(reconnected.reconnected,true);
assert.deepEqual(acceptance.changedPaths,protocol.expectedChangedPaths);
await writeFile(join(here,'fresh-outcomes.json'),JSON.stringify({attemptedRequests:1,acceptedLocalRequests:1,
  sourceRef,baselineRef:protocol.baselineCommit,sourceRows:planned.plan.sourceCount,changedPaths:acceptance.changedPaths,
  interpretation:'Three intended source-version changes, not alleged vulnerabilities or autonomous improvement.',
  completeReservation:result.authorization,reconnectReservation:reconnected.authorization,
  reconnectObservations:reconnected.reconnectObservations,connectedExecution:'NOT RUN',
  fullMonetaryCost:{value:null,basis:'unknown',reference:'Actual full service/development/upkeep and input acquisition prices unmeasured.'}},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({attemptedRequests:1,acceptedLocalRequests:1,sourceRows:planned.plan.sourceCount,changedPaths:acceptance.changedPaths}));
