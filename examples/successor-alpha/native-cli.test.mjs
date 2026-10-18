// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, writeFile, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createJoinMission, runJoinExperiment } from './engine.mjs';
import { createProject, appendCycle, serializeProject } from './project.mjs';
import { createNativeHandoff, inspectNativeReturn, importNativeReturn, inspectContinuity } from './continuity.mjs';
import { computeInstalledSourceHash } from './native-cli.mjs';

const cli = fileURLToPath(new URL('./native-cli.mjs', import.meta.url));
const sourceHash = await computeInstalledSourceHash();
const mission = createJoinMission({ leftCsv: 'sku,name\nA,left\nA,same\nB,missing\n',
    rightCsv: 'key,name\nA,same\nA,right\nC,missing\n', leftKey: 'sku', rightKey: 'key' });
const project = appendCycle(createProject({ name: 'Host catalog Ω' }),
    { mission, result: await runJoinExperiment(mission), sourceHash });
const options = { route: 'AGIALPHA', sourceHash, rights: { dataClass: 'synthetic',
    source: 'Synthetic CLI test fixture', license: 'Apache-2.0' }, owner: 'local-owner', reviewMinutes: 10 };
const handoff = await createNativeHandoff(project, options);
const run = (input, output) => spawnSync(process.execPath, [cli, input, output],
    { encoding: 'utf8', timeout: 15000, maxBuffer: 1000000, cwd: tmpdir() });
async function temporary(work) {
    const directory = await mkdtemp(join(tmpdir(), 'alpha-native-cli-'));
    try { await work(directory); } finally { await rm(directory, { recursive: true, force: true }); }
}
async function absent(path) {
    await assert.rejects(readFile(path), error => error.code === 'ENOENT');
}

test('actual Node host process runs a saved handoff outside the checkout and imports its exact catalog return', async () => {
    await temporary(async directory => {
        const input = join(directory, 'handoff.json'), output = join(directory, 'return.json');
        await writeFile(input, handoff);
        const outcome = run(input, output);
        assert.equal(outcome.status, 0, outcome.stderr); assert.equal(outcome.error, undefined);
        const summary = JSON.parse(outcome.stdout);
        assert.equal(summary.execution, 'installed-local-node');
        assert.equal(summary.sourceHash, sourceHash); assert.equal(summary.projectId, project.id);
        assert.equal(summary.cycleId, project.cycles[0].id); assert.equal(summary.independentlyQualified, false);
        const returned = await readFile(output, 'utf8');
        const checked = await inspectNativeReturn(handoff, returned);
        assert.equal(checked.pack.result.summary.matchedPairs, 4);
        assert.equal(checked.pack.result.summary.unmatchedLeft, 1);
        assert.equal(checked.pack.result.summary.unmatchedRight, 1);
        assert.equal(checked.pack.result.summary.conflicts, 3);
        assert.equal(checked.handoff.project.raw, serializeProject(project));
        const exact = JSON.parse(checked.files.find(file => file.name === 'exact-result.json').content);
        for (const strategy of exact.result.strategies) {
            assert.deepEqual(strategy.pairs, [[0, 0], [0, 1], [1, 0], [1, 1]]);
        }
        const record = await importNativeReturn(project, handoff, returned, { sourceHash });
        const continuity = await inspectContinuity(record);
        assert.equal(continuity.project.id, project.id);
        assert.equal(continuity.continuity.returns[0].returnRaw, returned);
        assert.equal(continuity.continuity.snapshots[0].raw, serializeProject(project));
        assert.deepEqual(await readdir(directory), ['handoff.json', 'return.json']);
        assert.equal(checked.independentReview, false); assert.equal(checked.runAuthorized, false);
    });
});

test('host process refuses a stale source commitment and creates no output', async () => {
    await temporary(async directory => {
        const input = join(directory, 'stale-handoff.json'), output = join(directory, 'absent.json');
        await writeFile(input, await createNativeHandoff(project, { ...options, sourceHash: '0'.repeat(64) }));
        const outcome = run(input, output);
        assert.notEqual(outcome.status, 0); assert.match(outcome.stderr, /SOURCE_DRIFT/);
        await absent(output);
    });
});

test('existing output survives both successful-input and malformed-input attempts unchanged', async () => {
    await temporary(async directory => {
        const input = join(directory, 'handoff.json'), output = join(directory, 'kept.json');
        await writeFile(input, handoff); await writeFile(output, 'keep these original bytes\n');
        for (const content of [handoff, '{}']) {
            await writeFile(input, content);
            const outcome = run(input, output);
            assert.notEqual(outcome.status, 0); assert.match(outcome.stderr, /already exists/);
            assert.equal(await readFile(output, 'utf8'), 'keep these original bytes\n');
        }
        assert.deepEqual(await readdir(directory), ['handoff.json', 'kept.json']);
    });
});

test('oversized, malformed UTF-8 and directory inputs fail without publishing a return', async () => {
    await temporary(async directory => {
        const input = join(directory, 'input.json'), output = join(directory, 'absent.json');
        for (const content of [Buffer.alloc(2_000_001, 32), Buffer.from([0xc3, 0x28])]) {
            await writeFile(input, content);
            const outcome = run(input, output);
            assert.notEqual(outcome.status, 0); assert.equal(outcome.error, undefined);
            await absent(output);
        }
        const outcome = run(directory, output);
        assert.notEqual(outcome.status, 0); assert.match(outcome.stderr, /regular UTF-8 file/);
        await absent(output);
    });
});

test('FIFO input is refused promptly without a writer or output', { skip: process.platform === 'win32' }, async () => {
    await temporary(async directory => {
        const input = join(directory, 'waiting.fifo'), output = join(directory, 'absent.json');
        const mkfifo = spawnSync('mkfifo', [input], { encoding: 'utf8', timeout: 1000 });
        assert.equal(mkfifo.status, 0, mkfifo.stderr);
        const outcome = spawnSync(process.execPath, [cli, input, output],
            { encoding: 'utf8', timeout: 3000, maxBuffer: 1000000 });
        assert.notEqual(outcome.status, 0); assert.equal(outcome.error, undefined);
        assert.match(outcome.stderr, /regular UTF-8 file/); await absent(output);
    });
});
