// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createWorkbench, example, inspectPack } from './engine.mjs';
import { canonical } from '../../docs/assets/successor/engine.mjs';
import { thermalWitnessAdapter, thermalExample, executeThermal, validateThermalInput } from './thermal-witness.mjs';
import { foundryWitnessFixture } from './thermal-witness-fixtures.mjs';
import { runThermalCases } from './thermal-witness-cases.mjs';

const sourceHash = 'a'.repeat(64); // Synthetic test identity; the executable demo hashes the actual source closure.
const runtime = createWorkbench([thermalWitnessAdapter]);
const mission = inputs => ({ ...example(), family: 'thermal-witness', inputs });

test('thermal numerical, scientific-reference and refusal cases', async () => {
  const result = await runThermalCases({ thermalExample, executeThermal, validateThermalInput, foundryWitnessFixture });
  assert.equal(result.passed, 42);
});
test('three thermal quantities run through the existing workbench with inert recovery', async () => {
  for (const family of ['delivered-heat', 'heat-capacity', 'heat-recovery']) {
    const pack = await runtime.run(mission(thermalExample(family)), { sourceHash });
    assert.equal(pack.result.decision, 'CONDITIONAL_BOUNDS_MET');
    assert.equal(pack.evaluation.admission, 'HOLD');
    assert.equal(pack.evaluation.independentProof, false);
    assert.equal(pack.evaluation.settlement, 'NOT_CONNECTED');
    assert.equal(pack.result.summary.acceptedCapability, false);
    assert.equal(pack.economics.providerSpendBaseUnits, '0');
    const restored = await runtime.inspectPack(JSON.parse(canonical(pack)));
    assert.deepEqual(restored.activeAuthority, []);
    assert.deepEqual(restored.activeProof, []);
    assert.equal(restored.authentication, 'UNAUTHENTICATED_HISTORICAL_IMPORT');
    await assert.rejects(inspectPack(pack), /UNSUPPORTED/);
  }
});
test('full witnessed Foundry acquisition crosses the actual canonical and artifact boundaries', async () => {
  const { input } = foundryWitnessFixture();
  const pack = await runtime.run(mission(input), { sourceHash });
  assert.equal(pack.result.evidence.intervalsProcessed, 720);
  assert.equal(pack.result.evidence.quantity.low, '4943354615');
  assert.equal(pack.result.evidence.quantity.high, '5129056527');
  assert.equal((await runtime.inspectPack(JSON.parse(canonical(pack)))).spec.inputs.measurement.intervals.length, 720);
  assert.ok(!canonical(pack.spec).includes('trueSecondaryHeatJ'));
  assert.ok(!canonical(pack.spec).includes('multipliers'));
});
test('altered observations and artifact bytes fail existing pack integrity', async () => {
  const pack = await runtime.run(mission(thermalExample()), { sourceHash });
  const changedInput = JSON.parse(canonical(pack));
  changedInput.spec.inputs.measurement.intervals[0].volumeNL++;
  await assert.rejects(runtime.inspectPack(changedInput), /PACK_INTEGRITY/);
  const changedArtifact = JSON.parse(canonical(pack));
  changedArtifact.result.artifacts[0].content += ' ';
  await assert.rejects(runtime.inspectPack(changedArtifact), /PACK_INTEGRITY/);
});
test('new observation and downstream requirement receive distinct mission commitments', async () => {
  const parent = await runtime.run(mission(thermalExample()), { sourceHash });
  const successor = await runtime.run(mission(thermalExample('heat-capacity')), { sourceHash });
  assert.notEqual(parent.frozen.missionDigest, successor.frozen.missionDigest);
  assert.equal(successor.evaluation.admission, 'HOLD');
  assert.equal(successor.chronicle[0].inheritedAuthority, false);
  assert.equal(successor.chronicle[0].inheritedProof, false);
});
test('one-command local demo verifies actual source closure and emits a valid workbench pack', async () => {
  const entry = fileURLToPath(new URL('./thermal-witness-demo.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [entry, 'foundry'], { encoding: 'utf8', timeout: 30000, maxBuffer: 2000000 });
  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.equal(output.schema, 'thermal-workbench-demo/v1');
  assert.match(output.pack.frozen.sourceHash, /^[a-f0-9]{64}$/);
  assert.ok(output.source.sources['examples/successor-workbench/thermal-witness.mjs']);
  assert.ok(output.source.sources['examples/build-successor/vendor/agijobs/compiler.mjs']);
  await runtime.inspectPack(output.pack);
});
