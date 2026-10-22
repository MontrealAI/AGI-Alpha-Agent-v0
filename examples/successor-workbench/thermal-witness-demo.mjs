// SPDX-License-Identifier: Apache-2.0
import { createHash } from 'node:crypto';
import { open, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';

const root = new URL('../../', import.meta.url);
const manifestPath = 'alpha_factory_v1/core/runtime/successor/workbench_sources.json';
const newSources = ['thermal-witness.mjs', 'thermal-witness-reference.mjs', 'thermal-witness-fixtures.mjs',
  'thermal-witness-demo.mjs'].map(name => 'examples/successor-workbench/' + name);
const hash = value => createHash('sha256').update(value).digest('hex');
async function captureSources() {
  const raw = await readFile(new URL(manifestPath, root)), manifest = JSON.parse(raw.toString('utf8'));
  if (manifest.schema !== 'successor-workbench-source/v1' || !/^[a-f0-9]{64}$/.test(manifest.sourceHash) ||
      !manifest.sources || typeof manifest.sources !== 'object') throw Error('WORKBENCH_SOURCE_MANIFEST');
  const sources = {};
  for (const path of [...Object.keys(manifest.sources), manifestPath, ...newSources].sort()) {
    if (!/^[A-Za-z0-9_./-]+$/.test(path) || path.startsWith('/') || path.split('/').includes('..')) {
      throw Error('SOURCE_PATH');
    }
    const digest = hash(await readFile(new URL(path, root)));
    if (Object.hasOwn(manifest.sources, path) && digest !== manifest.sources[path]) throw Error('WORKBENCH_SOURCE_MISMATCH: ' + path);
    sources[path] = digest;
  }
  return { schema: 'thermal-workbench-source/v1', workbenchSourceHash: manifest.sourceHash,
    nodeVersion: process.version, sources, authentication: 'LOCAL_SOURCE_SNAPSHOT_NOT_RELEASE_ATTESTATION' };
}
async function readInput(path) {
  const handle = await open(path, constants.O_RDONLY | (constants.O_NONBLOCK ?? 0));
  try {
    const stat = await handle.stat();
    if (!stat.isFile()) throw Error('INPUT_REGULAR_FILE_REQUIRED');
    if (stat.size > 2000000) throw Error('INPUT_TOO_LARGE');
    const buffer = Buffer.alloc(2000001);
    let used = 0;
    while (used < buffer.length) {
      const read = await handle.read(buffer, used, buffer.length - used, used);
      if (read.bytesRead === 0) break;
      used += read.bytesRead;
    }
    if (used > 2000000) throw Error('INPUT_TOO_LARGE');
    return buffer.subarray(0, used).toString('utf8');
  } finally { await handle.close(); }
}
const args = process.argv.slice(2), mode = args[0] || 'foundry';
if (!['foundry', 'delivered-heat', 'heat-capacity', 'heat-recovery', '--input'].includes(mode) ||
    (mode === '--input' ? args.length !== 2 : args.length > 1)) {
  throw Error('Usage: node thermal-witness-demo.mjs [foundry|delivered-heat|heat-capacity|heat-recovery|--input FILE]');
}
const source = await captureSources();
const [{ createWorkbench, example }, { parseBounded },
  { thermalWitnessAdapter, thermalExample }, { foundryWitnessFixture }] = await Promise.all([
  import('./engine.mjs'), import('../../docs/assets/successor/engine.mjs'),
  import('./thermal-witness.mjs'), import('./thermal-witness-fixtures.mjs'),
]);
const inputs = mode === '--input' ? parseBounded(await readInput(args[1]))
  : mode === 'foundry' ? foundryWitnessFixture().input : thermalExample(mode);
const sourceHash = hash(JSON.stringify(source));
const runtime = createWorkbench([thermalWitnessAdapter]);
const spec = { ...example(), family: 'thermal-witness', name: 'Witnessed thermal measurement',
  rights: { dataClass: 'synthetic', source: 'Declared simulated measurement fixture', license: 'Apache-2.0' }, inputs };
const pack = await runtime.run(spec, { sourceHash });
await runtime.inspectPack(pack);
if (JSON.stringify(source) !== JSON.stringify(await captureSources())) throw Error('SOURCE_CHANGED_DURING_DEMO');
process.stdout.write(JSON.stringify({ schema: 'thermal-workbench-demo/v1', source, pack }, null, 2) + '\n');
