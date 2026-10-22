// SPDX-License-Identifier: Apache-2.0
/** Ordinary owned path fixtures for the finite campaign CLI's output boundary. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, existsSync, symlinkSync, rmSync, realpathSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const repository = realpathSync(fileURLToPath(new URL('../../', import.meta.url)));
const cli = fileURLToPath(new URL('./discovery-lab-reproduce.mjs', import.meta.url));
function fixture(callback) {
    const external = mkdtempSync(join(tmpdir(), 'discovery-output-'));
    const internal = mkdtempSync(join(repository, 'discovery-output-fixture-'));
    try { callback({external, internal}); }
    finally { rmSync(external, {recursive: true, force: true}); rmSync(internal, {recursive: true, force: true}); }
}
function directoryLink(target, link) { symlinkSync(target, link, process.platform === 'win32' ? 'junction' : 'dir'); }
function run(output, options = {}) {
    return spawnSync(process.execPath, [cli, '--output', output], {encoding: 'utf8', timeout: 120000, ...options});
}
function refused(result) {
    assert.equal(result.error, undefined);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /outside this repository|ENOENT/);
}

test('existing external output alias and its missing nested children cannot enter the repository', () => fixture(({external, internal}) => {
    const alias = join(external, 'alias'); directoryLink(internal, alias);
    for (const output of [alias, join(alias, 'missing', 'nested')]) refused(run(output));
    assert.deepEqual(readdirSync(internal), []);
}));

test('real repository root and an internal name beginning with two dots remain inside', () => fixture(({external, internal}) => {
    refused(run(repository)); refused(run(internal));
    const dotted = mkdtempSync(join(repository, '..discovery-output-'));
    try { refused(run(dotted)); assert.deepEqual(readdirSync(dotted), []); }
    finally { rmSync(dotted, {recursive: true, force: true}); }
    assert.deepEqual(readdirSync(external), []);
}));

test('a reports directory alias into the repository refuses before any write', () => fixture(({external, internal}) => {
    const output = join(external, 'output'); mkdirSync(output); directoryLink(internal, join(output, 'reports'));
    refused(run(output)); assert.deepEqual(readdirSync(internal), []);
    assert.deepEqual(readdirSync(output), ['reports']);
}));

test('launching through a checkout alias compares the canonical real repository root', () => fixture(({external, internal}) => {
    const alias = join(external, 'checkout'); directoryLink(repository, alias);
    const aliasedCli = join(alias, 'examples', 'successor-capability', 'discovery-lab-reproduce.mjs');
    const result = spawnSync(process.execPath, ['--preserve-symlinks-main', aliasedCli, '--output',
        join(alias, relative(repository, internal), 'new')], {encoding: 'utf8', timeout: 120000});
    refused(result); assert.deepEqual(readdirSync(internal), []);
}));

const ids = ['accepted-default', 'noisy-one-use', 'noisy-twelve-uses', 'undeclared-quadratic-drift',
    'quadratic-reconstruction', 'non-updatable-memory', 'wrong-location', 'staging-enabled',
    'hidden-private-coupling', 'exhausted-search', 'stronger-checkpoint', 'stronger-four-control-successor',
    'route-before-change', 'equal-profiles-current-route', 'lineage-generation-two', 'lineage-generation-three'];
for (const name of [...ids.map(id => 'reports/' + id + '.json'), 'summary.json', 'elapsed-receipts.json']) {
    test(`fixed destination ${name} cannot follow a file link into the repository`, () => fixture(({external, internal}) => {
        const output = join(external, 'output'); mkdirSync(join(output, 'reports'), {recursive: true});
        const retained = join(internal, 'retained.json'); writeFileSync(retained, '{"retained":true}\n');
        symlinkSync(retained, join(output, name), 'file');
        refused(run(output)); assert.equal(readFileSync(retained, 'utf8'), '{"retained":true}\n');
        assert.deepEqual(readdirSync(output).sort(), name.startsWith('reports/') ? ['reports'] : [name, 'reports'].sort());
        assert.deepEqual(readdirSync(join(output, 'reports')), name.startsWith('reports/') ? [name.slice(8)] : []);
    }));
}

test('dangling output and fixed-file links fail before creation or writes', () => fixture(({external, internal}) => {
    const dangling = join(external, 'dangling'); directoryLink(join(internal, 'absent'), dangling);
    refused(run(join(dangling, 'nested'))); assert.deepEqual(readdirSync(internal), []);
    const output = join(external, 'output'); mkdirSync(output);
    symlinkSync(join(internal, 'absent.json'), join(output, 'summary.json'), 'file');
    refused(run(output)); assert.deepEqual(readdirSync(output), ['summary.json']);
    assert.deepEqual(readdirSync(internal), []);
}));

test('ordinary relative missing nested external output retains the complete finite bank', () => fixture(({external, internal}) => {
    const output = join(external, 'new', 'nested');
    const result = run(relative(repository, output), {cwd: repository});
    assert.equal(result.error, undefined); assert.equal(result.status, 0, result.stderr);
    const summary = JSON.parse(readFileSync(join(output, 'summary.json'), 'utf8'));
    assert.equal(summary.count, 16); assert.deepEqual(summary.records.map(row => row.id), ids);
    assert.deepEqual(readdirSync(join(output, 'reports')).sort(), ids.map(id => id + '.json').sort());
    assert.equal(JSON.parse(readFileSync(join(output, 'elapsed-receipts.json'), 'utf8')).receipts.length, 16);
    assert.deepEqual(readdirSync(internal), []);
}));

test('a real external directory alias remains a supported output root', () => fixture(({external}) => {
    const actual = join(external, 'actual'); mkdirSync(actual);
    const alias = join(external, 'alias'); directoryLink(actual, alias);
    const result = run(join(alias, 'new', 'nested'));
    assert.equal(result.error, undefined); assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).evidenceDirectory, resolve(actual, 'new', 'nested'));
    assert.equal(existsSync(join(actual, 'new', 'nested', 'summary.json')), true);
}));
