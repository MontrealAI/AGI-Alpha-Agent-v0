// SPDX-License-Identifier: Apache-2.0
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {scenarioWorld, planAllocation, compileAllocation} from '../../research/src/engine_adapter.mjs';
import {expertSchedule, evaluateSchedule} from '../../research/src/independent_evaluator.mjs';

const started = performance.now(), cpuStart = process.cpuUsage();
async function caseAt(epoch) {
  const world = scenarioWorld(1, epoch, 'ordinary');
  const verified = await planAllocation(world.mission);
  const clone = await planAllocation(structuredClone(world.mission));
  const expert = expertSchedule(world.mission);
  if (verified.status !== 'COMPLETE' || clone.status !== 'COMPLETE') throw Error('Development case incomplete');
  if (verified.objective !== clone.objective || verified.objective !== expert.objective) throw Error('Matched comparison disagrees');
  return {world, modelDigest:verified.modelDigest, modelBytes:Buffer.byteLength(JSON.stringify(compileAllocation(world.mission))), verified, completeClone:clone, expert, evaluated:{verified:evaluateSchedule(world,verified.plan), completeClone:evaluateSchedule(world,clone.plan), expert:evaluateSchedule(world,expert.plan)}};
}
const original = await caseAt(0);
const freshScope = await caseAt(1);
const sources = {};
for (const p of ['../../research/src/engine_adapter.mjs', '../../research/src/independent_evaluator.mjs']) {
  const file = fileURLToPath(new URL(p, import.meta.url));
  sources[p] = createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}
process.stdout.write(JSON.stringify({schema:'nova-seeds.dispatcher-development-case/v1', scope:'One synthetic development seed, two epochs with fresh mission identity and evidence; not confirmation outcomes', node:process.version, ...original, freshScope, sourceSha256:sources, costs:{wallMs:performance.now()-started, cpuMicros:process.cpuUsage(cpuStart), hostContention:'Confirmation worker may run concurrently; timings are one local run, not isolated performance estimates', boundary:'Module import/startup and final serialization are outside this timer'}},null,2)+'\n');
