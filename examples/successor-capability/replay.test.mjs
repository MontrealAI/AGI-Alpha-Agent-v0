// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const script = fileURLToPath(new URL('./replay.mjs', import.meta.url));

// These deliberately small fixtures exercise retained-history capacity, not previous evaluation claims.
function historyFixtures(count) {
    return Array.from({length: count}, (_, sequence) => ({sequence,
        report: {exposedCaseIds: ['retained-capacity-fixture-' + sequence]}, fixture: 'capacity-boundary'}));
}

function replay(output, seed) {
    return spawnSync(process.execPath, [script, output, String(seed)],
        {encoding: 'utf8', timeout: 120000, maxBuffer: 1024 * 1024});
}

async function outputBytes(output) {
    const files = (await readdir(output)).sort();
    return Object.fromEntries(await Promise.all(files.map(async name => [name, await readFile(join(output, name))])));
}

test('a full replay history rejects before evaluation and preserves every existing output byte', async () => {
    const output = await mkdtemp(join(tmpdir(), 'out-evolve-full-history-'));
    try {
        await writeFile(join(output, 'history.json'), JSON.stringify(historyFixtures(100)) + '\n');
        await writeFile(join(output, 'evaluation.json'), 'retained evaluation evidence\n');
        await writeFile(join(output, 'shielded-capability.json'), 'retained package evidence\n');
        const before = await outputBytes(output);
        // This invalid evaluation seed would fail differently if the expensive evaluation were reached.
        const result = replay(output, -1);
        assert.equal(result.error, undefined);
        assert.equal(result.status, 1);
        assert.match(result.stderr, /Replay history capacity reached \(100 reports\)/);
        assert.match(result.stderr, /new output directory to preserve prior evidence/);
        assert.equal(result.stdout, '');
        assert.deepEqual(await outputBytes(output), before);
    } finally {
        await rm(output, {recursive: true, force: true});
    }
});

test('the final available replay slot retains all 99 prior entries and refuses a 101st report', async () => {
    const output = await mkdtemp(join(tmpdir(), 'out-evolve-last-history-slot-'));
    try {
        const retained = historyFixtures(99);
        await writeFile(join(output, 'history.json'), JSON.stringify(retained) + '\n');
        const result = replay(output, 312);
        assert.equal(result.error, undefined);
        assert.equal(result.status, 0, result.stderr);
        assert.equal(JSON.parse(result.stdout).status, 'PASS');
        const history = JSON.parse(await readFile(join(output, 'history.json'), 'utf8'));
        assert.equal(history.length, 100);
        assert.deepEqual(history.slice(0, 99), retained);
        assert.equal(history[99].sequence, 99);
        assert.equal(history[99].report.status, 'PASS');
        assert.ok(Object.keys(history[99].sourceDigests).includes('replay.mjs'));
        const before = await outputBytes(output);
        const full = replay(output, -1);
        assert.equal(full.status, 1);
        assert.match(full.stderr, /Replay history capacity reached/);
        assert.deepEqual(await outputBytes(output), before);
    } finally {
        await rm(output, {recursive: true, force: true});
    }
});
