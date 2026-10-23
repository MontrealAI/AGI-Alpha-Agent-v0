// SPDX-License-Identifier: Apache-2.0
import {mkdir, readFile, writeFile, readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import * as workspace from '../successor-capability/workspace.mjs';
import * as controller from './controller.mjs';
import {defaultCharter, auditSnapshot} from './protocol.mjs';
import {runCapitalConfirmation, syntheticCapitalExample, capitalControls} from './capital.mjs';
import {exportDiscoveryDocket, verifyDiscoveryDocket} from '../successor-capability/discovery-lab-docket.mjs';

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== '--output') throw Error('Usage: node examples/autonomous-enterprises/reproduce.mjs --output EMPTY_DIRECTORY');
const out = resolve(args[1]);
await mkdir(out, {recursive: true});
if ((await readdir(out)).length) throw Error('Refusing to overwrite a nonempty evidence directory.');
const began = performance.now(), manifest = JSON.parse(await readFile(resolve(root, 'docs/successor/capabilities/sources.json'), 'utf8'));
const actualSources = {};
for (const [path, expected] of Object.entries(manifest.sources)) {
    const actual = createHash('sha256').update(await readFile(resolve(root, path))).digest('hex');
    if (actual !== expected) throw Error('Generated source identity differs: ' + path);
    actualSources[path] = actual;
}
const source = {constructor: actualSources['examples/autonomous-enterprises/foundry.mjs'],
    checker: actualSources['examples/autonomous-enterprises/checker.mjs'], closure: manifest.sourceHash};
let value = await controller.start(await workspace.createWorkspace({...workspace.DEFAULT_BRIEF,
    title: 'Autonomous Enterprises · independent deterministic confirmation'}, null), defaultCharter(source));
for (let step = 0; step < 11; step++) {
    const inspection = await controller.state(value);
    if (!inspection.current) break;
    console.log(step, inspection.current.state);
    value = inspection.current.state === 'INVOCATION_RESERVED' ? await controller.invokeReserved(value, source)
        : await controller.next(value, {seed: 20261021, expectedSource: source});
    await writeFile(resolve(out, 'workspace.json'), workspace.canonical(value) + '\n');
}
const inspected = await controller.state(value), row = inspected.history.at(-1);
if (row.state !== 'SUCCESSOR_ACCEPTED_LOCAL') throw Error('The complete local journey did not qualify: ' + row.state);
const docket = await exportDiscoveryDocket(value);
await writeFile(resolve(out, 'evidence-docket.json'), docket + '\n');
const verifiedDocket = await verifyDiscoveryDocket(docket);
const confirmation = runCapitalConfirmation({cases: 72, seed: 20261021});
const files = {'foundry.json': row.bundle, 'capital-confirmation.json': confirmation,
    'synthetic-capital.json': syntheticCapitalExample(), 'mathematical-controls.json': capitalControls(),
    'session-replay-account.json': auditSnapshot(), 'summary.json': {schema: 'autonomous-enterprise-local-confirmation/v1',
        reproduction: 'INDEPENDENT_REIMPLEMENTATION', node: process.version, platform: process.platform,
        workingTreeBase: execFileSync('git', ['rev-parse', 'HEAD'], {cwd: root, encoding: 'utf8'}).trim(),
        sourceClosure: manifest.sourceHash, sources: actualSources, selectedCounts: row.bundle.counts,
        observedConstruction: row.bundle.observedWorkLedger, capitalCounts: confirmation.counts,
        futureTreatments: row.future.runs.length, futureStates: row.future.runs.map(run => run.state),
        successor: row.state, completeLineageWork: row.successor.lineageWork, verifiedDocket,
        elapsedMs: Math.ceil(performance.now() - began), hosted: 'NOT_RUN', installedEnterpriseReceivers: 'NOT_RUN',
        currentChain: 'NOT_RUN', realTaskPilot: 'NOT_RUN', settlement: 'SIMULATED_ONLY', authority: []}};
for (const [name, item] of Object.entries(files)) await writeFile(resolve(out, name), JSON.stringify(item, null, 2) + '\n');
const checksums = [];
for (const name of (await readdir(out)).sort()) checksums.push(createHash('sha256').update(await readFile(resolve(out, name))).digest('hex') + '  ' + name);
await writeFile(resolve(out, 'SHA256SUMS'), checksums.join('\n') + '\n');
console.log(JSON.stringify({state: row.state, counts: row.bundle.counts, evidence: out, verifiedDocket}));
