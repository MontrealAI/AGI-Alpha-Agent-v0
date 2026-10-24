// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { createCompiler, executeProgram } from './compiler.mjs';
import { createDiscoverabilityAdapter, createDiscoverabilityWorkbench, discoverabilityMission } from './workbench-adapter.mjs';
import { inspectPack } from '../successor-workbench/engine.mjs';
import { canonical, parseBounded } from '../../docs/assets/successor/engine.mjs';

const testSourceHash = 'd'.repeat(64);
const sourceOptions = () => ({ sourceHash: testSourceHash });
const problem = () => ({
  schema: 'discoverability.problem.v1', id: 'adapter-test',
  worlds: [
    { id: 'nominal', goal: 'no-action', signal: [0, 0] },
    { id: 'fault', goal: 'investigate', signal: [4, 0] },
  ],
  channels: [
    { id: 'a', cost: 1, noise: 0 },
    { id: 'b', cost: 1, noise: 0 },
  ],
  nuisance: [[1], [1]], grammar: { maxSupport: 2, weightLimit: 1, maxL1: 2 },
  missionBudget: 2,
});

test('new construction uses the existing source-bound workbench and seven inert Jobs packages', async () => {
  const runtime = createDiscoverabilityWorkbench(), mission = discoverabilityMission(problem());
  const pack = await runtime.run(mission, sourceOptions());
  assert.equal(pack.result.evidence.construction.status, 'COMPILED');
  assert.equal(pack.result.decision, 'REVIEW_REQUIRED');
  assert.equal(pack.result.summary.acceptedCapability, false);
  assert.equal(pack.compilation.graph.nodes.length, 7);
  assert.equal(pack.compilation.budgetReservations.reservedBaseUnits, '0');
  assert.equal(pack.evaluation.admission, 'HOLD');
  assert.equal(pack.evaluation.settlement, 'NOT_CONNECTED');
  assert.equal(pack.economics.computeCost, null);
  assert.equal(pack.economics.humanMinutes, null);
  assert.equal(pack.frozen.sourceHash, testSourceHash);
  assert.equal(pack.result.artifacts.length, 3);
});

test('import verifies current installed adapter and clears all active proof and authority', async () => {
  const runtime = createDiscoverabilityWorkbench();
  const pack = await runtime.run(discoverabilityMission(problem()), sourceOptions());
  const restored = await runtime.inspectPack(parseBounded(canonical(pack)));
  assert.equal(restored.authentication, 'UNAUTHENTICATED_HISTORICAL_IMPORT');
  assert.deepEqual(restored.activeProof, []);
  assert.deepEqual(restored.activeAuthority, []);
  await assert.rejects(inspectPack(pack), /UNSUPPORTED/);
});

test('altered instrument bytes fail package integrity', async () => {
  const runtime = createDiscoverabilityWorkbench();
  const pack = await runtime.run(discoverabilityMission(problem()), sourceOptions());
  pack.result.artifacts[0].content += ' ';
  await assert.rejects(runtime.inspectPack(pack), /INTEGRITY/);
});

test('budget and unknown field checks run before compilation', () => {
  const adapter = createDiscoverabilityAdapter();
  for (const budget of [0, -1, 1.5, 2000001, Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => adapter.validate({ problem: problem(), budget }), /BUDGET/);
  }
  assert.throws(() => adapter.validate({ problem: problem(), budget: 1000, authority: 'execute' }), /SCHEMA/);
  assert.throws(() => adapter.validate({ problem: problem(), budget: 1000, '': 0 }), /SCHEMA/);
  let reads = 0;
  const accessor = { problem: problem(), get budget() { reads += 1; return 1000; } };
  assert.throws(() => adapter.validate(accessor), /SCHEMA/);
  assert.equal(reads, 0);
});

test('model ambiguity is retained as a rejected finite construction', async () => {
  const p = problem(); p.worlds[1].signal = [0, 0];
  const pack = await createDiscoverabilityWorkbench().run(discoverabilityMission(p), sourceOptions());
  assert.equal(pack.result.evidence.construction.status, 'UNIDENTIFIABLE_WITHIN_GRAMMAR');
  assert.equal(pack.result.decision, 'REJECTED_WITHIN_GRAMMAR');
  assert.equal(pack.evaluation.admission, 'HOLD');
});

test('touching error intervals do not become an identified decision', async () => {
  const p = problem(); p.worlds[1].signal = [2, 0]; p.channels[0].noise = 1;
  const pack = await createDiscoverabilityWorkbench().run(discoverabilityMission(p), sourceOptions());
  assert.equal(pack.result.evidence.construction.status, 'UNIDENTIFIABLE_WITHIN_GRAMMAR');
  assert.equal(pack.result.summary.acceptedCapability, false);
});

test('proved acquisition cost over the mission allowance remains a refusal', async () => {
  const p = problem(); p.missionBudget = 1;
  const pack = await createDiscoverabilityWorkbench().run(discoverabilityMission(p), sourceOptions());
  assert.equal(pack.result.evidence.construction.status, 'OVER_MISSION_BUDGET');
  assert.equal(pack.result.decision, 'REJECTED_OVER_MISSION_BUDGET');
  assert.equal(pack.evaluation.admission, 'HOLD');
});

test('exhausted construction retains an inconclusive result rather than a negative theorem', async () => {
  const pack = await createDiscoverabilityWorkbench().run(discoverabilityMission(problem(), { budget: 1 }), sourceOptions());
  assert.equal(pack.result.evidence.construction.status, 'BUDGET_EXHAUSTED');
  assert.equal(pack.result.decision, 'INCONCLUSIVE');
  assert.ok(pack.result.summary.workUsed <= pack.result.summary.workLimit);
});

test('Stop interrupts before returning a construction result', async () => {
  const controller = new AbortController(); controller.abort();
  await assert.rejects(createDiscoverabilityWorkbench().run(discoverabilityMission(problem()), {
    ...sourceOptions(), signal: controller.signal,
  }), /CANCELLED/);
});

test('an explicit retained compiler discloses before and after reuse statistics', async () => {
  const runtime = createDiscoverabilityWorkbench({ compiler: createCompiler({ strategy: 'cached' }) });
  const mission = discoverabilityMission(problem());
  const first = await runtime.run(mission, sourceOptions());
  const second = await runtime.run(mission, sourceOptions());
  assert.equal(canonical(first.result.evidence.compilerStatsAfter), canonical(second.result.evidence.compilerStatsBefore));
  assert.equal(first.result.evidence.construction.status, second.result.evidence.construction.status);
  assert.equal(first.frozen.missionDigest, second.frozen.missionDigest);
});

test('the exported instrument decodes observations without receiving evaluator truth', async () => {
  const p = problem(), pack = await createDiscoverabilityWorkbench().run(discoverabilityMission(p), sourceOptions());
  const instrument = pack.result.evidence.construction.program;
  const observations = instrument.experiments.map(experiment => experiment.responses.find(row => row.world === 'fault').center);
  const result = executeProgram(p, instrument, observations);
  assert.equal(result.status, 'DECIDED');
  assert.equal(result.decision, 'investigate');
});

test('different declared calibration changes the mission commitment', async () => {
  const runtime = createDiscoverabilityWorkbench(), p = problem();
  const first = await runtime.run(discoverabilityMission(p), sourceOptions());
  p.channels[0].noise = 1;
  const changed = await runtime.run(discoverabilityMission(p), sourceOptions());
  assert.notEqual(first.frozen.missionDigest, changed.frozen.missionDigest);
});

test('complete package stays inside the inherited integer-only transport', async () => {
  const pack = await createDiscoverabilityWorkbench().run(discoverabilityMission(problem()), sourceOptions());
  const raw = canonical(pack), restored = parseBounded(raw);
  assert.equal(canonical(restored), raw);
  assert.ok(new TextEncoder().encode(raw).length < 2000000);
});
