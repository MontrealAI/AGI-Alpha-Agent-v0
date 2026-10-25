// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, readdir, stat, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { parseCsv, verifyExperiment } from './engine.mjs';
import { inspectProject } from './project.mjs';

const directory = dirname(fileURLToPath(import.meta.url));
const cli = join(directory, 'cli.mjs');
const invoke = args => spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8', timeout: 15000 });
const absent = async path => assert.rejects(stat(path), error => error.code === 'ENOENT');

async function temporary(run) {
    const root = await mkdtemp(join(tmpdir(), 'successor-alpha-cli-'));
    try { await run(root); } finally { await rm(root, { recursive: true, force: true }); }
}

test('example CLI writes real CSVs, exact evidence, report, native project, and runnable tool', async () => temporary(async root => {
    const out = join(root, 'first');
    const result = invoke(['--example', '--out', out]);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /120 × 360 source rows, 120 matched pairs/);
    assert.deepEqual((await readdir(out)).sort(), ['comparison.json', 'conflicts.csv', 'exact-result.json', 'joined.csv',
        'project.json', 'report.html', 'successor-tool.mjs', 'unmatched-left.csv', 'unmatched-right.csv']);
    const exact = JSON.parse(await readFile(join(out, 'exact-result.json'), 'utf8'));
    assert.equal(verifyExperiment(exact.mission, exact.result).valid, true);
    const native = inspectProject(await readFile(join(out, 'project.json'), 'utf8'));
    assert.equal(native.cycles.length, 1);
    assert.equal(native.qualification, 'not_independently_qualified');
    assert.equal(native.cycles[0].sourceHash.length, 64);
    assert.equal(parseCsv(await readFile(join(out, 'joined.csv'), 'utf8')).rows.length, 120);
    assert.match(await readFile(join(out, 'report.html'), 'utf8'), /independent qualification/);
    const repeat = invoke(['--example', '--out', out]);
    assert.equal(repeat.status, 1); assert.match(repeat.stderr, /already exists/);
}));

test('custom CSV CLI preserves duplicate joins and exports actual discrepancies', async () => temporary(async root => {
    const left = join(root, 'left.csv'), right = join(root, 'right.csv'), out = join(root, 'joined');
    await writeFile(left, 'sku,title\na,Alpha\na,Second\nleft,Only left\n');
    await writeFile(right, 'key,title\na,Alpha\na,Different\nright,Only right\n');
    const result = invoke(['--left', left, '--right', right, '--left-key', 'sku', '--right-key', 'key', '--out', out]);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(parseCsv(await readFile(join(out, 'joined.csv'), 'utf8')).rows.length, 4);
    assert.equal(parseCsv(await readFile(join(out, 'conflicts.csv'), 'utf8')).rows.length, 3);
    assert.equal(parseCsv(await readFile(join(out, 'unmatched-left.csv'), 'utf8')).rows[0][0], 'left');
    assert.equal(parseCsv(await readFile(join(out, 'unmatched-right.csv'), 'utf8')).rows[0][0], 'right');
}));

test('generated standalone tool runs changed CSV inputs without repository modules', async () => temporary(async root => {
    const first = join(root, 'first');
    assert.equal(invoke(['--example', '--out', first]).status, 0);
    const left = join(root, 'new-left.csv'), right = join(root, 'new-right.csv'), second = join(root, 'second');
    await writeFile(left, 'record,value\nB,new\nC,left-only\n');
    await writeFile(right, 'catalog,value\nB,changed\nD,right-only\n');
    const run = spawnSync(process.execPath, [join(first, 'successor-tool.mjs'), left, right, 'record', 'catalog', second],
        { encoding: 'utf8', cwd: root, timeout: 15000 });
    assert.equal(run.status, 0, run.stderr);
    const exact = JSON.parse(await readFile(join(second, 'exact-result.json'), 'utf8'));
    assert.equal(verifyExperiment(exact.mission, exact.result).valid, true);
    assert.deepEqual(parseCsv(await readFile(join(second, 'joined.csv'), 'utf8')).rows, [['B', 'new', 'B', 'changed']]);
    const repeat = spawnSync(process.execPath, [join(first, 'successor-tool.mjs'), left, right, 'record', 'catalog', second],
        { encoding: 'utf8', timeout: 15000 });
    assert.notEqual(repeat.status, 0);
}));

test('malformed CSV, invalid UTF-8, missing keys, and oversized files create no output', async () => temporary(async root => {
    const left = join(root, 'left.csv'), right = join(root, 'right.csv');
    await writeFile(right, 'id\na\n');
    const cases = [Buffer.from('id\n"unclosed'), Buffer.from([0x69, 0x64, 0x0a, 0xff]),
        Buffer.from('other\na\n'), Buffer.alloc(200001, 0x61)];
    for (let index = 0; index < cases.length; index += 1) {
        const out = join(root, `bad-${index}`);
        await writeFile(left, cases[index]);
        const result = invoke(['--left', left, '--right', right, '--left-key', 'id', '--right-key', 'id', '--out', out]);
        assert.equal(result.status, 1, `case ${index}: ${result.stderr}`);
        await absent(out);
    }
}));

test('strict CLI rejects unknown, repeated, mixed, incomplete options and directories as inputs', async () => temporary(async root => {
    for (const args of [[], ['--surprise'], ['--example', '--out', join(root, 'a'), '--out', join(root, 'b')],
        ['--example', '--left', 'file', '--out', join(root, 'a')], ['--left', 'file', '--out', join(root, 'a')],
        ['--example', '--out'], ['--help', '--example']]) assert.equal(invoke(args).status, 1);
    const out = join(root, 'directory-input');
    const result = invoke(['--left', root, '--right', root, '--left-key', 'id', '--right-key', 'id', '--out', out]);
    assert.equal(result.status, 1); await absent(out);
    assert.equal(invoke(['--help']).status, 0);
}));
