// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { mkdtempSync, writeFileSync, rmSync, copyFileSync, readFileSync } from 'node:fs';
import { tmpdir, devNull } from 'node:os';
import { join } from 'node:path';
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
  assert.equal(result.passed, 51);
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

function inputCommand(path) {
  const entry = fileURLToPath(new URL('./thermal-witness-demo.mjs', import.meta.url));
  return spawnSync(process.execPath, [entry, '--input', path],
    { encoding: 'utf8', timeout: 10000, maxBuffer: 2000000 });
}
function rejectedInput(path, pattern) {
  const result = inputCommand(path);
  assert.equal(result.error, undefined);
  assert.equal(result.signal, null);
  assert.ok(Number.isInteger(result.status) && result.status > 0);
  assert.match(result.stderr, pattern);
  assert.equal(result.stdout, '');
}
test('input file accepts regular JSON and rejects directories and oversized bytes', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'thermal-input-'));
  try {
    const file = join(directory, 'measurement.json');
    writeFileSync(file, JSON.stringify(thermalExample()));
    const valid = inputCommand(file);
    assert.equal(valid.error, undefined);
    assert.equal(valid.signal, null);
    assert.equal(valid.status, 0, valid.stderr);
    const output = JSON.parse(valid.stdout);
    assert.equal(output.pack.result.decision, 'CONDITIONAL_BOUNDS_MET');
    await runtime.inspectPack(output.pack);
    rejectedInput(directory, /INPUT_REGULAR_FILE_REQUIRED|EISDIR/);
    writeFileSync(file, Buffer.alloc(2000001, 32));
    rejectedInput(file, /INPUT_TOO_LARGE/);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});
test('input FIFO without a writer is rejected without waiting',
  { skip: process.platform === 'win32' ? 'POSIX FIFO fixture is unavailable on Windows' : false }, () => {
    const directory = mkdtempSync(join(tmpdir(), 'thermal-fifo-'));
    try {
      const fifo = join(directory, 'measurement.fifo');
      const made = spawnSync('mkfifo', [fifo], { encoding: 'utf8', timeout: 5000, maxBuffer: 4096 });
      assert.equal(made.error, undefined);
      assert.equal(made.signal, null);
      assert.equal(made.status, 0, made.stderr);
      rejectedInput(fifo, /INPUT_REGULAR_FILE_REQUIRED/);
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });

test('packaged native worker is self-contained and registers all three thermal missions', () => {
  const directory = mkdtempSync(join(tmpdir(), 'thermal-native-'));
  const shipped = fileURLToPath(new URL('../../alpha_factory_v1/core/runtime/successor/workbench_worker.mjs', import.meta.url));
  const manifest = JSON.parse(readFileSync(new URL('../../alpha_factory_v1/core/runtime/successor/workbench_sources.json', import.meta.url), 'utf8'));
  const worker = join(directory, 'worker.mjs');
  try {
    copyFileSync(shipped, worker);
    const invoke = request => {
      const result = spawnSync(process.execPath, [worker], { cwd: directory, input: JSON.stringify(request),
        encoding: 'utf8', timeout: 30000, maxBuffer: 2000000 });
      assert.equal(result.error, undefined);
      assert.equal(result.signal, null);
      assert.equal(result.status, 0, result.stderr);
      return JSON.parse(result.stdout);
    };
    const registry = invoke({ operation: 'registry' });
    assert.equal(registry.sourceHash, manifest.sourceHash);
    for (const family of ['reliability', 'performance', 'documentation', 'public-data', 'numerical', 'thermal-witness']) {
      assert.equal(registry.families.filter(item => item.id === family).length, 1);
    }
    const native = invoke({ operation: 'example', family: 'thermal-witness' });
    assert.equal(native.family, 'thermal-witness');
    for (const family of ['delivered-heat', 'heat-capacity', 'heat-recovery']) {
      const spec = { ...native, inputs: thermalExample(family) };
      const planned = invoke({ operation: 'plan', spec });
      assert.equal(planned.executionOrder.length, 7);
      assert.equal(planned.authorityCreated, 'NONE');
      const pack = invoke({ operation: 'run', spec });
      assert.equal(pack.frozen.sourceHash, manifest.sourceHash);
      assert.equal(pack.result.decision, 'CONDITIONAL_BOUNDS_MET');
      assert.equal(pack.result.summary.acceptedCapability, false);
      assert.equal(pack.evaluation.admission, 'HOLD');
      assert.equal(pack.evaluation.settlement, 'NOT_CONNECTED');
      const restored = invoke({ operation: 'inspect', pack });
      assert.deepEqual(restored.activeAuthority, []);
      assert.deepEqual(restored.activeProof, []);
    }
    const foundry = invoke({ operation: 'run', spec: { ...native, inputs: foundryWitnessFixture().input } });
    assert.equal(foundry.result.evidence.intervalsProcessed, 720);
    assert.equal(foundry.result.evidence.quantity.low, '4943354615');
    assert.equal(foundry.result.evidence.quantity.high, '5129056527');
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

test('native Python journal preserves identity, reviews and source-bound recovery', t => {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const python = process.platform === 'win32' ? 'python' : 'python3';
  const result = spawnSync(python, ['-m', 'pytest', '--noconftest', '-c', devNull, '-p', 'no:cacheprovider',
    'tests/runtime/test_successor_workbench.py', 'tests/runtime/test_successor_workbench_generation.py', '-v'],
    { cwd: root, encoding: 'utf8', timeout: 180000, maxBuffer: 2000000,
      env: { ...process.env, PYTHONPATH: root, PYTEST_DISABLE_PLUGIN_AUTOLOAD: '1', PYTHONDONTWRITEBYTECODE: '1' } });
  assert.equal(result.error, undefined, 'Native acceptance requires the documented Python/runtime setup');
  assert.equal(result.signal, null);
  assert.equal(result.status, 0, result.stdout + '\n' + result.stderr);
  t.diagnostic(result.stdout.trim());
});
