// SPDX-License-Identifier: Apache-2.0
// Recipient integration of a supplied module, after independent source freeze.
// CLI: node transfer.mjs old.json new.json full|incremental output.json
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { buildIndex, compareIndexes, updateIndex } from '../../src/schema_inventory.mjs';

const [oldPath, newPath, mode, outputPath] = process.argv.slice(2);
if (!oldPath || !newPath || !outputPath || !['full', 'incremental'].includes(mode)) {
  throw Error('USAGE: node transfer.mjs old.json new.json full|incremental output.json');
}
const started = performance.now();
const cpuStart = process.cpuUsage();
const [oldBytes, newBytes, donorBytes, wrapperBytes] = await Promise.all([
  readFile(oldPath), readFile(newPath),
  readFile(new URL('../../src/schema_inventory.mjs', import.meta.url)),
  readFile(new URL('./transfer.mjs', import.meta.url)),
]);
const hash = value => createHash('sha256').update(value).digest('hex');
const oldDocument = JSON.parse(oldBytes), newDocument = JSON.parse(newBytes);
const oldIndex = await buildIndex(oldDocument);
const oldBuilt = performance.now();
const acquired = mode === 'incremental'
  ? await updateIndex(oldDocument, newDocument, oldIndex)
  : { index: await buildIndex(newDocument), work: { reusedResponses: 0, mode: 'full' } };
const newBuilt = performance.now();
const dossier = compareIndexes(oldIndex, acquired.index);
const cpu = process.cpuUsage(cpuStart);
const output = {
  recipient: 'independently reconstructed capable agent',
  stage: 'posttransfer supplied module; local execution only',
  mode, dossier,
  execution: {
    oldBuildSeconds: (oldBuilt - started) / 1000,
    newBuildSeconds: (newBuilt - oldBuilt) / 1000,
    wallSecondsBeforePackaging: (performance.now() - started) / 1000,
    cpuSecondsBeforePackaging: (cpu.user + cpu.system) / 1000000,
    work: acquired.work,
    costScope: 'Includes old index construction on every CLI run; no saved old-index cost omitted. Complete process/packaging receipt is recorded externally.',
  },
  identities: {
    oldFileSha256: hash(oldBytes), newFileSha256: hash(newBytes),
    donorModuleSha256: hash(donorBytes), wrapperSha256: hash(wrapperBytes),
  },
  limitations: [
    'No behavior, whole-API compatibility, paid demand or live authenticated skill admission is demonstrated.',
    'Transfer does not establish a previously absent response inventory capability; the recipient already constructed one.',
    'Current module supports extra grammar, but this experiment compares the frozen Swagger 2 question only.',
  ],
};
await writeFile(outputPath, `${JSON.stringify(output, null, 2)}\n`);
console.log(JSON.stringify({ mode, changes: dossier.counts.changes, oldNodes: dossier.counts.old.nodes, newNodes: dossier.counts.new.nodes, ...acquired.work }));
