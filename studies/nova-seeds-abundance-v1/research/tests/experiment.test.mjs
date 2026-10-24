// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {scenarioWorld,planAllocation,planningFeasible,validateMission,SCENARIOS} from '../src/engine_adapter.mjs';
import {expertSchedule,evaluateSchedule} from '../src/independent_evaluator.mjs';
import {inspectCompletion} from '../vendor/alpha/examples/successor-capability/out-execute/engine.mjs';

test('Every disclosed finite geometry agrees with independent exact enumeration',async()=>{
  for(const scenario of SCENARIOS){
    const world=scenarioWorld(2,0,scenario),result=await planAllocation(world.mission,{evidenceRepeats:1});
    assert.equal(result.status,'COMPLETE');assert.equal(result.objective,expertSchedule(world.mission).objective);
    assert.equal(evaluateSchedule(world,result.plan).valid,true);
  }
});
test('Fresh mission scope is separate from inherited source and policy',()=>{
  const world=scenarioWorld(1,0,'ordinary');assert.equal(world.mission.seed,undefined);assert.equal(world.mission.epoch,undefined);assert.equal(world.mission.scenario,undefined);assert.equal(world.mission.id.includes('ordinary'),false);
  const changed=structuredClone(world.mission);changed.authority.missionId='wrong-mission';assert.throws(()=>validateMission(changed));
});
test('Validity is inclusive and physical capacity remains binding',()=>{
  const world=scenarioWorld(1,0,'ordinary');assert.equal(planningFeasible(world.mission,[1,0,0],[3,0,0,0]),true);
  world.mission.jobs[0].ttl=1;assert.equal(planningFeasible(world.mission,[1,0,0],[3,0,0,0]),false);
  assert.equal(planningFeasible(world.mission,[1,0,1],[1,3,0,0]),true);assert.equal(planningFeasible(world.mission,[1,0,0],[1,1,0,0]),false);
});
test('Native proof is checkable and changing its witness is rejected',async()=>{
  const world=scenarioWorld(1,0,'ordinary'),result=await planAllocation(world.mission,{retainProof:true});
  const forged=structuredClone(result.completion);forged.artifact.j0=(forged.artifact.j0+1)%4;
  await assert.rejects(inspectCompletion(forged));
});
test('Accepted nominal proof can coexist with failed physical outcomes; delayed QC can help',async()=>{
  const world=scenarioWorld(1,0,'measurement-drift'),native=await planAllocation(world.mission),actual=evaluateSchedule(world,native.plan);
  assert.equal(actual.valid,true);assert.equal(actual.failures,2);
  const adaptive=expertSchedule(world.mission,{predictedBias:world.bias.map(value=>value-world.bias[0])});
  const updated=evaluateSchedule(world,adaptive.plan);assert.equal(updated.valid,true);assert.ok(updated.utility>actual.utility);assert.equal(updated.failures,0);
});
