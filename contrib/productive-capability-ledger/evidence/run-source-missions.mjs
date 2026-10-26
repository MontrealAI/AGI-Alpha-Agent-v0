// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {createHash, webcrypto} from 'node:crypto';
import {readFile, writeFile, mkdir, realpath} from 'node:fs/promises';
import {dirname, resolve, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import * as guide from '../../../examples/ti-guide/guide.mjs';

globalThis.crypto ??= webcrypto;
const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../../..');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const canonical = guide.canonical;
const emit = async (path, value) => writeFile(path, JSON.stringify(value, null, 2) + '\n');
const started = new Date().toISOString(), wall = performance.now(), cpu = process.cpuUsage();
const dependencies = ['examples/ti-guide/guide.mjs', 'examples/successor-alpha/engine.mjs', 'examples/successor-alpha/research.mjs'];
const identity = {};
for (const path of dependencies) {
    identity[path] = sha(await readFile(resolve(root, path)));
    assert.equal(identity[path], sha(execFileSync('git', ['show', 'HEAD:' + path], {cwd: root})));
}
const methodIdentity = sha(canonical(identity));
const sourceCommit = execFileSync('git', ['rev-parse', 'HEAD'], {cwd: root, encoding: 'utf8'}).trim();
const missions = [
    ['guide-source-assurance', 'docs/try/sources.json'],
    ['transformational-source-assurance', 'docs/transformational-intelligence/sources.json'],
];
const reports = [];
for (const [index, [name, manifestPath]] of missions.entries()) {
    const missionStart = performance.now(), missionCpu = process.cpuUsage();
    const directory = resolve(here, name);
    await mkdir(directory, {recursive: true});
    const manifestBytes = await readFile(resolve(root, manifestPath));
    assert.equal(sha(manifestBytes), sha(execFileSync('git', ['show', 'HEAD:' + manifestPath], {cwd: root})));
    const manifest = JSON.parse(manifestBytes.toString('utf8'));
    assert.equal(typeof manifest.sources, 'object');
    const expected = [['path', 'sha256']], actual = [['path', 'sha256']], sourceRows = [];
    for (const [path, digest] of Object.entries(manifest.sources).sort(([a], [b]) => a.localeCompare(b))) {
        assert.match(path, /^[A-Za-z0-9_./-]+$/);
        assert.match(digest, /^[0-9a-f]{64}$/);
        const full = await realpath(resolve(root, path));
        assert(!relative(root, full).startsWith('..' + sep) && relative(root, full) !== '..');
        const bytes = await readFile(full), observed = sha(bytes);
        assert.equal(observed, sha(execFileSync('git', ['show', 'HEAD:' + path], {cwd: root})));
        expected.push([path, digest]); actual.push([path, observed]);
        sourceRows.push({path, expectedSha256: digest, observedSha256: observed, bytes: bytes.length});
    }
    const input = {leftCsv: guide.safeCsv(expected), rightCsv: guide.safeCsv(actual), leftKey: 'path', rightKey: 'path'};
    const phases = [];
    const result = await guide.compute(input, stage => phases.push(stage));
    const workspace = guide.makeWorkspace(input, result, {approach: 'grouped', sourceHash: methodIdentity,
        runId: name + '-' + sourceCommit.slice(0, 12), createdAt: started, language: 'en'});
    assert.deepEqual(await guide.restoreWorkspace(JSON.stringify(workspace), methodIdentity), workspace);
    assert.equal(result.metrics.leftRows, sourceRows.length); assert.equal(result.metrics.rightRows, sourceRows.length);
    const changed = sourceRows.filter(row => row.expectedSha256 !== row.observedSha256);
    assert.deepEqual(result.differences.map(row => row.key).sort(), changed.map(row => row.path).sort());
    assert.equal(result.metrics.unmatchedRows, 0);
    await writeFile(resolve(directory, 'declared-inventory.csv'), input.leftCsv);
    await writeFile(resolve(directory, 'observed-inventory.csv'), input.rightCsv);
    await writeFile(resolve(directory, 'differences.csv'), guide.fullDifferencesCsv(result));
    await writeFile(resolve(directory, 'action-plan.csv'), guide.actionPlanCsv(result));
    await emit(resolve(directory, 'result.json'), result);
    await emit(resolve(directory, 'workspace.json'), workspace);
    const report = {schema: 'productive-capability-source-mission/v1', mission: name, sourceCommit, sourceManifest: manifestPath,
        sourceManifestSha256: sha(manifestBytes), inputIdentity: {left: result.leftIdentity, right: result.rightIdentity},
        retainedMethod: {path: dependencies[0], dependencySha256: identity, methodIdentity, primaryMissionInvocation: index + 1,
            implementationChanged: false, reuse: index === 0 ? 'existing released executable' : 'same exact executable on different 24-source inventory'},
        inputClassification: 'fresh extraction from current committed public repository source; not authored sample or synthetic defect',
        rows: sourceRows, metrics: result.metrics, accepted: true, checked: ['manifest entries and actual file SHA-256',
            'exact key/field differences', 'complete input identities', 'workspace recomputation', 'zero authority'], phases,
        observed: {wallMilliseconds: performance.now() - missionStart, processCpuMicroseconds: process.cpuUsage(missionCpu)},
        unknownCosts: ['model-assisted engineering and review', 'human attention', 'setup and integration', 'hardware and electricity',
            'verification outside this process', 'maintenance and business overhead'],
        interpretation: 'No source drift found in this manifest scope. Empty action plan is a checked result, not automatic source approval or absence of defects.',
        authority: 'none', connectedExecution: 'NOT RUN; actual existing guide module executed locally in Node'};
    await emit(resolve(directory, 'receipt.json'), report); reports.push(report);
}
assert.notEqual(reports[0].inputIdentity.left.sha256, reports[1].inputIdentity.left.sha256);
assert.equal(reports[0].retainedMethod.methodIdentity, reports[1].retainedMethod.methodIdentity);
const report = {schema: 'productive-capability-source-mission-series/v1', startedAt: started, sourceCommit,
    missions: reports.map(({mission, metrics, accepted, inputIdentity, retainedMethod}) => ({mission, metrics, accepted, inputIdentity, retainedMethod})),
    observed: {wholeProcessToReportWallMilliseconds: performance.now() - wall, processCpuMicroseconds: process.cpuUsage(cpu)},
    acceptedDeliverables: 2, primaryGuideInvocations: 2, totalGuideComputeInvocations: 4, workspaceRecomputations: 2,
    sourceFilesInspected: reports.reduce((n, r) => n + r.rows.length, 0),
    capabilityExpansion: 'not established; same source-assurance workflow applied to a different current source closure',
    contribution: 'Reusable unchanged comparison implementation verified both current source inventories; no defect or method promotion was manufactured.',
    economics: {completeAgentCost: null, traditionalHumanTime: null, customerPriceCollected: null, surplus: null,
        unknownsAreNotZero: true, note: 'Process timings are partial observed execution components, not full Agent costs or human-work savings.'},
    restrictions: ['no network', 'no credential or journal access', 'no connected executor', 'no source modification', 'no transactions']};
await emit(resolve(here, 'source-missions-report.json'), report);
console.log(JSON.stringify({acceptedDeliverables: report.acceptedDeliverables, sourceFilesInspected: report.sourceFilesInspected,
    methodIdentity, sourceCommit, report: relative(root, resolve(here, 'source-missions-report.json'))}));
