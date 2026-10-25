// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {makePlan,runPlan} from '../automation-v1/run-mission.mjs';

let raw='';
for await(const piece of process.stdin){raw+=piece;assert(Buffer.byteLength(raw)<=131072,'Bounded input required.');}
const request=JSON.parse(raw);
if(request.operation==='plan') {
  assert.deepEqual(Object.keys(request).sort(),['operation','options']);
  process.stdout.write(JSON.stringify(await makePlan(request.options)));
} else {
  assert.deepEqual(Object.keys(request).sort(),['approvalDigest','operation','outputRoot','plan']);
  assert.equal(request.operation,'run');
  const result=await runPlan(request.plan,{approvalDigest:request.approvalDigest,outputRoot:request.outputRoot});
  const complete=JSON.parse(await readFile(result.directory+'/COMPLETE.json','utf8'));
  assert.equal(complete.accepted,true);
  process.stdout.write(JSON.stringify({accepted:true,runId:complete.runId,sourceRef:complete.sourceRef,
    approvalDigest:complete.approvalDigest,methodIdentity:complete.methodIdentity,reconnected:result.reconnected}));
}
