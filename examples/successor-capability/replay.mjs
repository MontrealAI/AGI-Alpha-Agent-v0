// SPDX-License-Identifier: Apache-2.0
/** Run: node examples/successor-capability/replay.mjs /absolute/output/directory [uint32-seed] */
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { runEvaluation } from './evaluation.mjs';
import { importCapability, verificationCostCapability } from './capability-package.mjs';

if (process.argv[2] === '--verify') {
    if (!process.argv[3] || process.argv.length > 4) throw Error('Usage: replay.mjs --verify /absolute/capability.json');
    const pkg = await importCapability(JSON.parse(await readFile(resolve(process.argv[3]), 'utf8')));
    console.log(JSON.stringify({status: 'VERIFIED', digest: pkg.digest, scope: pkg.scope,
        fixtureCount: pkg.replayFixtures.length, modelOnly: pkg.certificate.modelOnly,
        verificationCost: verificationCostCapability(pkg), costUnit: 'abstract-model-work'}));
} else {

const output = resolve(process.argv[2] || 'out-evolve-evidence');
const seed = process.argv[3] === undefined ? undefined : Number(process.argv[3]);
const here = dirname(fileURLToPath(import.meta.url));
const sourceFiles = ['apparatus.mjs', 'typed-runtime.mjs', 'independent-checker.mjs', 'constructor.mjs',
    'capability-package.mjs', 'evaluation.mjs', 'replay.mjs'];
const sources = {};
for (const name of sourceFiles) sources[name] = createHash('sha256').update(await readFile(resolve(here, name))).digest('hex');
const constructorDigest = createHash('sha256').update(JSON.stringify(sources)).digest('hex');
let history = [];
try {
    history = JSON.parse(await readFile(resolve(output, 'history.json'), 'utf8'));
    if (!Array.isArray(history) || history.length > 100) throw Error('Replay history limit exceeded.');
    if (history.length === 100) {
        throw Error('Replay history capacity reached (100 reports). '
            + 'Use a new output directory to preserve prior evidence.');
    }
} catch (error) {
    if (error.code !== 'ENOENT') throw error;
}
const exposedCaseIds = [...new Set(history.flatMap(item => item.report.exposedCaseIds || []))];
const report = await runEvaluation({seed, constructorDigest, exposedCaseIds});
await mkdir(output, {recursive: true});
history.push({sequence: history.length, report, sourceDigests: sources});
await writeFile(resolve(output, 'history.json'), JSON.stringify(history, null, 2) + '\n');
await writeFile(resolve(output, 'evaluation.json'), JSON.stringify({...report, sourceDigests: sources}, null, 2) + '\n');
for (const item of report.topologies) if (item.package) {
    await writeFile(resolve(output, item.topology + '-capability.json'), JSON.stringify(item.package, null, 2) + '\n');
}
if (report.successor?.package) {
    await writeFile(resolve(output, 'successor-capability.json'), JSON.stringify(report.successor.package, null, 2) + '\n');
}
console.log(JSON.stringify({status: report.status, distinctPrograms: report.behaviorallyDistinctPrograms,
    topologyResults: report.topologies.map(item => ({topology: item.topology, status: item.status})),
    successor: report.successor?.status, constructorGeneralization: report.generalization.status, output}));
if (report.status !== 'PASS') process.exitCode = 1;
}
