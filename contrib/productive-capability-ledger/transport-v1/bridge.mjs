// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {makePlan,runPlan} from '../automation-v1/run-mission.mjs';
import {AUTOMATED_COST_SCHEMA,AUTOMATED_STAGES,evaluateAutomatedCosts} from '../../../examples/successor-alpha/automated-costs.mjs';

let raw='';
for await(const piece of process.stdin){raw+=piece;assert(Buffer.byteLength(raw)<=131072,'Bounded input required.');}
const request=JSON.parse(raw);
if(request.operation==='plan') {
  assert.deepEqual(Object.keys(request).sort(),['operation','options']);
  process.stdout.write(JSON.stringify(await makePlan(request.options)));
} else {
  assert.deepEqual(Object.keys(request).sort(),['approvalDigest','attemptNumber','operation','outputRoot','plan']);
  assert.equal(request.operation,'run');
  assert(Number.isSafeInteger(request.attemptNumber)&&request.attemptNumber>=1&&request.attemptNumber<=request.plan.maxAttempts);
  const result=await runPlan(request.plan,{approvalDigest:request.approvalDigest,outputRoot:request.outputRoot});
  const complete=JSON.parse(await readFile(join(request.outputRoot,request.plan.runId,'COMPLETE.json'),'utf8'));
  assert.equal(complete.accepted,true);
  const fact=(value,basis,reference)=>({value,basis,reference}),unknown=reference=>fact(null,'unknown',reference);
  const accounting={schema:AUTOMATED_COST_SCHEMA,offeringId:'connected-public-source-assurance',currency:'USD',
    scenarios:['base','conservative','stress'].map(name=>({name,
      capacityRequestsPerMonth:unknown('Production volume is not measured by internal qualification.'),
      utilizationBps:unknown('Production utilization unknown.'),
      acceptanceBps:fact(10000,'measured','One independently accepted deterministic qualification mission; not a future success rate or customer acceptance.'),
      attemptsPerRequestPpm:fact(request.attemptNumber*1000000,'measured','All durable outer precharged attempts for this one mission, including interrupted work.'),
      operations:[...AUTOMATED_STAGES.map(stage=>({id:'source-'+stage,stage,frequency:'accepted',
        unitsPerOccurrencePpm:fact(complete.stages.find(s=>s.stage===stage).wallMicroseconds.value,'measured','Retained completed stage wall microseconds; interrupted and parent work separate.'),
        unitCostMicros:unknown('Complete resource price unknown.'),implementation:'implemented'})),
        {id:'uncommitted-and-parent-work',stage:'recovery',frequency:'attempt',unitsPerOccurrencePpm:unknown('Uncommitted work and parent transport/journal/source hashing are not erased.'),unitCostMicros:unknown('Inclusive host price unknown.'),implementation:'implemented'}],
      residual:[{id:'exception-attention',stage:'recovery',exceptionsPerRequestPpm:unknown('Operational exception frequency unknown.'),minutesPerException:unknown('Residual attention unknown.'),hourlyCostMicros:unknown('Attention cost unknown.')}],
      monthly:[{id:'attributable-upkeep',kind:'maintenance',amountMicros:unknown('Recurring upkeep unknown.'),allocationBps:unknown('Offering allocation unknown.')}],
      investments:[{id:'development-and-setup',kind:'development',amountMicros:unknown('Construction, failures, setup and authoring costs unknown.'),allocationBps:unknown('Attributable share unknown.'),amortizationMonths:unknown('Useful life unknown.')}],
      humanBaseline:{minutesPerAccepted:unknown('Matched competent human task duration unknown.'),hourlyCostMicros:unknown('Use a separately sourced offering model.')}}))};
  process.stdout.write(JSON.stringify({accounting,costSummary:evaluateAutomatedCosts(accounting),accepted:true,runId:complete.runId,sourceRef:complete.sourceRef,
    approvalDigest:complete.approvalDigest,methodIdentity:complete.methodIdentity,reconnected:result.reconnected}));
}
