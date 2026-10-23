// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { createCompiler } from './compiler.mjs';
import { digitalFault, mixtureAssay } from './domains.mjs';
import { executeObservations, runSyntheticJourney } from './execution.mjs';
const sourceHash = 'e'.repeat(64);

for (const [name, builder] of [['digital fault', digitalFault], ['mixture assay', mixtureAssay]]) {
  test(name + ' executes new active-channel acquisitions and correct decisions for every declared world', async () => {
    const problem = builder(), compiler = createCompiler();
    for (const world of problem.worlds) {
      const report = await runSyntheticJourney(problem, { worldId: world.id }, { sourceHash, compiler });
      assert.equal(report.operationalState, 'SYNTHETIC_DELIVERY_MATCHED');
      assert.equal(report.execution.result.decision, world.goal);
      assert.equal(report.mode, 'NEWLY_EXECUTED_SYNTHETIC');
      assert.equal(report.evaluator.matched, true);
      assert.equal(report.acceptedCapability, false);
      assert.deepEqual(report.authority, []);
      assert.equal(report.costs.computeCost, null);
      const program = report.pack.result.evidence.construction.program;
      assert.equal(report.costs.acquisitionDeclaredUnits, program.totalCost);
      assert.equal(report.execution.workbenchPackDigest, report.pack.integrityDigest);
      assert.equal(report.evaluator.acquisition.raw.length, program.experiments.length);
      report.evaluator.acquisition.raw.forEach((row, index) => {
        const experiment = program.experiments[index];
        assert.deepEqual(row.activeChannels, experiment.weights.flatMap((weight, i) => weight ? [i] : []));
        assert.equal(row.values.length, row.activeChannels.length);
        assert.equal(row.chargedCost, experiment.cost);
      });
    }
  });
}

test('out-of-envelope observations fail explicitly without evaluator truth', async () => {
  const report = await runSyntheticJourney(digitalFault(), { worldId: 'xor' }, { sourceHash });
  const impossible = report.execution.observations.map(() => 1000000000);
  const result = await executeObservations(report.pack, impossible);
  assert.equal(result.result.status, 'OUT_OF_SCOPE');
  assert.equal(result.result.decision, null);
  assert.equal(result.acceptedCapability, false);
});

test('compilation refusal cannot be presented as operational delivery', async () => {
  const report = await runSyntheticJourney(digitalFault(), { worldId: 'xor' }, { sourceHash, budget: 1 });
  assert.equal(report.operationalState, 'CONSTRUCTION_REFUSED');
  assert.equal(report.execution, null);
  assert.equal(report.evaluator, null);
  assert.equal(report.costs.acquisitionDeclaredUnits, 0);
  assert.equal(report.pack.result.decision, 'INCONCLUSIVE');
});

test('tampered source pack is refused before standalone observation decoding', async () => {
  const report = await runSyntheticJourney(digitalFault(), { worldId: 'xor' }, { sourceHash });
  report.pack.spec.inputs.problem.missionBudget += 1;
  await assert.rejects(executeObservations(report.pack, report.execution.observations), /INTEGRITY|BINDING|scope/);
});

test('Stop after compilation prevents acquisition and delivery', async () => {
  const controller = new AbortController();
  await assert.rejects(runSyntheticJourney(digitalFault(), { worldId: 'xor' }, {
    sourceHash, signal: controller.signal,
    onCheckpoint: async phase => { if (phase === 'acquire new synthetic readings') controller.abort(); },
  }), /CANCELLED/);
});

test('evaluator configuration is bounded before compilation', async () => {
  for (const evaluator of [
    { worldId: 'xor', errorSign: 2 },
    { worldId: 'xor', nuisanceScale: 10001 },
    { worldId: 'xor', authority: 'execute' },
  ]) await assert.rejects(runSyntheticJourney(digitalFault(), evaluator, { sourceHash }), /EVALUATOR/);
});
