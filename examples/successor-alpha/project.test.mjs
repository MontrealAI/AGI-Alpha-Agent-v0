// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, readFile, writeFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { canonical } from '../../docs/assets/successor/engine.mjs';
import { createSampleMission, createJoinMission, runJoinExperiment, buildArtifacts } from './engine.mjs';
import {
    VERSION, configure, createProject, inspectProject, serializeProject, appendCycle,
    planOpportunity, addOpportunity, estimateValue, prepareHandoff, buildReport, buildCapability,
} from './project.mjs';

const deployment = JSON.parse(await readFile(new URL('./deployment.json', import.meta.url), 'utf8'));
const engineSource = await readFile(new URL('./engine.mjs', import.meta.url), 'utf8');
const mission = createSampleMission({ leftRows: 4, rightRows: 9 });
const result = await runJoinExperiment(mission);
const sourceHash = 'a'.repeat(64);
const opportunity = () => ({ goal: 'Reconcile permitted catalogs.', currentApproach: 'Review every matching row.',
    alternative: 'Use an existing database join.', target: 'Preserve every exact matching pair.',
    evidence: 'Supplied synthetic example; no customer measurements.', budget: 'Owner decision pending.' });
const fixture = () => appendCycle(createProject({ name: 'Catalog Ω', goal: 'Inspect the catalog differences.' }),
    { mission, result, sourceHash });
configure({ engineSource, deployment });

test('valid project round trip retains exact work while qualification and authority remain empty', () => {
    const original = fixture(), bytes = serializeProject(original), restored = inspectProject(bytes);
    assert.equal(restored.schema, VERSION);
    assert.equal(serializeProject(restored), bytes);
    assert.equal(canonical(restored.cycles[0].mission), canonical(mission));
    assert.equal(canonical(restored.cycles[0].result), canonical(result));
    assert.equal(restored.qualification, 'not_independently_qualified');
    assert.equal(restored.authority, 'none');
    assert.equal(restored.cycles[0].origin, 'local_engineering_run');
});

test('append snapshots inputs without replacing the existing retained project', () => {
    const original = createProject(), suppliedMission = structuredClone(mission), suppliedResult = structuredClone(result);
    const next = appendCycle(original, { mission: suppliedMission, result: suppliedResult, sourceHash });
    suppliedMission.left.rows[0][0] = 'changed'; suppliedResult.strategies[0].pairs.length = 0;
    assert.equal(original.revision, 0); assert.equal(original.cycles.length, 0);
    assert.equal(next.revision, 1);
    assert.equal(canonical(next.cycles[0].mission), canonical(mission));
    assert.equal(canonical(next.cycles[0].result), canonical(result));
});

test('imports reject forged result counts, omitted pairs, changed observations and authority escalation', () => {
    for (const mutate of [
        p => { p.authority = 'production'; },
        p => { p.qualification = 'specialist_asi'; },
        p => { p.cycles[0].origin = 'independent_protected_evaluation'; },
        p => { p.cycles[0].result.assessment.externalAuthority = true; },
        p => { p.cycles[0].result.assessment.independentReview = 'passed'; },
        p => { p.cycles[0].result.assessment.superiorityClaim = true; },
        p => { p.cycles[0].result.strategies[0].pairs.pop(); },
        p => { p.cycles[0].result.strategies[1].metrics.logicalOperations += 1; },
        p => { p.cycles[0].result.reconciliation.matchedPairs += 1; },
        p => { p.cycles[0].result.measurementNotes[0] = 'Customer value independently established.'; },
    ]) {
        const changed = structuredClone(fixture()); mutate(changed);
        assert.throws(() => inspectProject(changed));
    }
});

test('historical timings remain unverified observations rather than recomputed proof', () => {
    const historical = structuredClone(fixture());
    const recorded = historical.cycles[0].result.strategies[0].metrics.elapsedMicros;
    const restored = inspectProject(historical);
    assert.equal(restored.cycles[0].result.strategies[0].metrics.elapsedMicros, recorded);
    assert.equal(restored.qualification, 'not_independently_qualified');
    assert.equal(restored.authority, 'none');
    for (const invalid of [-1, -0, 1.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
        const changed = structuredClone(historical);
        changed.cycles[0].result.strategies[0].metrics.elapsedMicros = invalid;
        assert.throws(() => inspectProject(changed));
    }
});

test('strict imports reject duplicate JSON keys, floats, excess bytes and out-of-scope fields', () => {
    const p = createProject(), serialized = serializeProject(p);
    assert.throws(() => inspectProject(serialized.replace('"revision":0', '"revision":0,"revision":0')), /Duplicate/);
    assert.throws(() => inspectProject(serialized.replace('"revision":0', '"revision":0.5')));
    assert.throws(() => inspectProject(' '.repeat(2000001)));
    for (const modify of [
        p => { p.execute = 'arbitrary supplied code'; },
        p => { p.grants = []; },
        p => { p.cycles[0].trustedKey = 'self-supplied'; },
        p => { p.cycles[0].mission.network = true; },
        p => { p.cycles[0].result.authority = 'production'; },
    ]) {
        const changed = structuredClone(fixture()); modify(changed);
        assert.throws(() => inspectProject(changed));
    }
});

test('cycles have distinct identities and capacity errors preserve all six retained cycles', () => {
    let p = createProject();
    for (let index = 0; index < 6; index += 1) p = appendCycle(p, { mission, result, sourceHash });
    assert.equal(new Set(p.cycles.map(c => c.id)).size, 6);
    const before = serializeProject(p);
    assert.throws(() => appendCycle(p, { mission, result, sourceHash }), /six/);
    assert.equal(serializeProject(p), before);
    const duplicate = structuredClone(p); duplicate.cycles[1].id = duplicate.cycles[0].id;
    assert.throws(() => inspectProject(duplicate), /Duplicate/);
});

test('project and cycle identifiers must be canonical UUIDs', () => {
    for (const change of [
        p => { p.id = '-'.repeat(36); },
        p => { p.cycles[0].id = 'a'.repeat(36); },
    ]) {
        const changed = structuredClone(fixture()); change(changed);
        assert.throws(() => inspectProject(changed));
    }
});

test('project and cycle dates reject impossible calendar days', () => {
    for (const change of [
        p => { p.createdAt = '2026-02-30T12:00:00.000Z'; },
        p => { p.cycles[0].createdAt = '2026-02-30T12:00:00.000Z'; },
    ]) {
        const changed = structuredClone(fixture()); change(changed);
        assert.throws(() => inspectProject(changed));
    }
});

test('opportunity notebook retains typed hypotheses without measurement or authorization claims', () => {
    const note = planOpportunity(opportunity());
    assert.equal(note.state, 'hypothesis'); assert.equal(note.independentReview, 'not_commissioned');
    assert.equal(note.authority, 'none');
    const p = addOpportunity(createProject(), opportunity());
    assert.equal(p.opportunities.length, 1);
    assert.equal(serializeProject(inspectProject(serializeProject(p))), serializeProject(p));
    const changed = structuredClone(p); changed.opportunities[0].state = 'proven';
    assert.throws(() => inspectProject(changed));
    for (const invalid of [true, 42, ['supplied text'], { evidence: 'supplied text' }]) {
        assert.throws(() => planOpportunity({ ...opportunity(), evidence: invalid }));
    }
    assert.throws(() => planOpportunity({ ...opportunity(), realizedValueMeasured: true }));
});

test('opportunity capacity rejection retains every prior hypothesis', () => {
    let p = createProject();
    for (let index = 0; index < 12; index += 1) p = addOpportunity(p, opportunity());
    const before = serializeProject(p);
    assert.throws(() => addOpportunity(p, opportunity()), /Export/);
    assert.equal(serializeProject(p), before);
});

test('economics preserve assumptions, adverse results, and zero-benefit break-even uncertainty', () => {
    const inputs = { beforeMinutes: 60, afterMinutes: 30, runsPerMonth: 10, hourlyValueCents: 4000, setupCents: 5000 };
    const estimate = estimateValue(inputs);
    assert.deepEqual(estimate.inputs, inputs);
    assert.equal(estimate.monthlyCents, 20000); assert.equal(estimate.netFirstMonthCents, 15000);
    assert.equal(estimate.breakEvenMonths, 1);
    assert.equal(estimate.status, 'user_supplied_assumptions'); assert.equal(estimate.realizedValueMeasured, false);
    const loss = estimateValue({ ...inputs, afterMinutes: 90 });
    assert.equal(loss.monthlyCents, -20000); assert.equal(loss.breakEvenMonths, null);
    const zero = estimateValue({ ...inputs, afterMinutes: 60 });
    assert.equal(zero.monthlyCents, 0); assert.equal(zero.breakEvenMonths, null);
});

test('economics reject nonfinite, fractional, coerced and unsupported inputs', () => {
    const inputs = { beforeMinutes: 60, afterMinutes: 30, runsPerMonth: 10, hourlyValueCents: 4000 };
    for (const invalid of [Infinity, NaN, -1, 0.5, '60', true, 1000001]) {
        assert.throws(() => estimateValue({ ...inputs, beforeMinutes: invalid }));
    }
    assert.throws(() => estimateValue({ ...inputs, realizedValueMeasured: true }));
});

test('economics round exact cent arithmetic without unsafe intermediate multiplication', () => {
    const estimate = estimateValue({ beforeMinutes: 999999, afterMinutes: 0,
        runsPerMonth: 999896, hourlyValueCents: 99991 });
    assert.equal(estimate.monthlyCents, 1666341682589984);
    const loss = estimateValue({ beforeMinutes: 0, afterMinutes: 1, runsPerMonth: 1, hourlyValueCents: 30 });
    assert.equal(Object.is(loss.monthlyCents, -0), false);
    assert.doesNotThrow(() => canonical(loss));
});

test('commissioning handoffs keep USDC and AGIALPHA separate, unfunded and unprivileged', () => {
    const p = fixture(), usdc = prepareHandoff(p, 'USDC'), token = prepareHandoff(p, 'AGIALPHA');
    assert.equal(usdc.route, 'USDC'); assert.equal(usdc.market, 'AGIJobManager'); assert.equal(usdc.deployment, null);
    assert.equal(token.route, 'AGIALPHA');
    assert.equal(canonical(token.deployment), canonical(deployment));
    for (const brief of [usdc, token]) {
        assert.equal(brief.state, 'unfunded_draft'); assert.equal(brief.authority, 'none');
        assert.equal(brief.qualification, 'not_independently_qualified'); assert.equal(brief.transactionPrepared, false);
        assert.equal(brief.sourceCycles[0].id, p.cycles[0].id);
    }
    assert.throws(() => prepareHandoff(p, 'automatic_conversion'));
});

test('a returned handoff cannot mutate the configured deployment used by later handoffs', () => {
    configure({ engineSource, deployment });
    const first = prepareHandoff(createProject(), 'AGIALPHA');
    first.deployment.runtimeAuthorized = true;
    first.deployment.contracts.NovaSeed.address = '0x' + 'f'.repeat(40);
    const second = prepareHandoff(createProject(), 'AGIALPHA');
    assert.equal(canonical(second.deployment), canonical(deployment));
    configure({ engineSource, deployment });
});

test('HTML report escapes supplied display fields while retaining its local evidence scope', () => {
    const attack = '<img src=x onerror=alert(1)><script>alert(2)</script>';
    const html = buildReport(mission, result, { name: attack, goal: attack, language: 'fr' });
    assert.ok(!html.includes('<img')); assert.ok(!html.includes('<script>'));
    assert.ok(html.includes('&lt;img')); assert.ok(html.includes('qualification indépendante'));
    assert.ok(html.includes('default-src \'none\''));
});

test('report and executable-tool exports reject forged result scope before rendering or writing', () => {
    for (const change of [
        r => { r.reconciliation.matchedPairs = '<img src=x onerror=alert(1)>'; },
        r => { r.assessment.externalAuthority = true; },
        r => { r.measurementNotes = ['Independent proof and realized value established.']; },
    ]) {
        const changed = structuredClone(result); change(changed);
        assert.throws(() => buildReport(mission, changed));
        assert.throws(() => buildCapability(mission, changed));
    }
});


test('exported standalone capability reads every short-read chunk and preserves complete CSV semantics', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'successor-alpha-export-short-read-'));
    try {
        const leftCsv = 'id,name\nA,"First, continued"\nB,Café\nC,Third\n';
        const rightCsv = 'id,name\nA,"First, continued"\nB,Changed\nD,Fourth\n';
        const fullMission = createJoinMission({ leftCsv, rightCsv, leftKey: 'id', rightKey: 'id' });
        const fullResult = await runJoinExperiment(fullMission);
        const expected = buildArtifacts(fullMission, fullResult);
        const left = join(directory, 'left.csv'), right = join(directory, 'right.csv');
        const tool = join(directory, 'standalone-tool.mjs'), shim = join(directory, 'short-read.mjs');
        const output = join(directory, 'output'), log = join(directory, 'read-counts.txt');
        await writeFile(left, leftCsv); await writeFile(right, rightCsv);
        await writeFile(tool, buildCapability(mission, result));
        await writeFile(shim, `
import fs from 'node:fs/promises';
import { syncBuiltinESMExports } from 'node:module';
const open = fs.open, fileStat = fs.stat;
if (process.env.SUCCESSOR_UNDERREPORT_SIZE) fs.stat = async (...args) => {
    const info = await fileStat(...args); info.size = 8; return info;
};
fs.open = async (...args) => {
    const handle = await open(...args);
    const read = handle.read.bind(handle), stat = handle.stat.bind(handle);
    if (process.env.SUCCESSOR_UNDERREPORT_SIZE) handle.stat = async () => {
        const info = await stat(); info.size = 8; return info;
    };
    handle.read = async (buffer, offset, length, position) => {
        const chunk = await read(buffer, offset, Math.min(length, Number(process.env.SUCCESSOR_SHORT_READ_CHUNK || 8)), position);
        await fs.appendFile(process.env.SUCCESSOR_SHORT_READ_LOG, String(chunk.bytesRead) + '\\n');
        return chunk;
    };
    return handle;
};
syncBuiltinESMExports();
`);
        const execution = spawnSync(process.execPath, ['--import', shim, tool, left, right, 'id', 'id', output], {
            cwd: directory, encoding: 'utf8', timeout: 15000,
            env: { ...process.env, SUCCESSOR_SHORT_READ_LOG: log },
        });
        assert.equal(execution.status, 0, execution.stderr);
        const counts = (await readFile(log, 'utf8')).trim().split('\n').map(Number);
        assert.ok(counts.length > 4, 'both CSVs must require multiple reads');
        assert.ok(counts.every(count => count >= 0 && count <= 8));
        assert.equal(counts.filter(count => count === 0).length, 2, 'both reads must continue through EOF');
        const retained = JSON.parse(await readFile(join(output, 'exact-result.json'), 'utf8'));
        assert.equal(canonical(retained.mission), canonical(fullMission));
        assert.deepEqual(retained.result.reconciliation, fullResult.reconciliation);
        for (const [file, key] of Object.entries({ 'joined.csv': 'joinedCsv', 'unmatched-left.csv': 'unmatchedLeftCsv',
            'unmatched-right.csv': 'unmatchedRightCsv', 'conflicts.csv': 'conflictsCsv' })) {
            assert.equal(await readFile(join(output, file), 'utf8'), expected[key]);
        }
        await writeFile(left, 'id,name\n' + 'x'.repeat(200000));
        const oversized = spawnSync(process.execPath, ['--import', shim, tool, left, right, 'id', 'id',
            join(directory, 'oversized-output')], {
            cwd: directory, encoding: 'utf8', timeout: 15000,
            env: { ...process.env, SUCCESSOR_SHORT_READ_LOG: log, SUCCESSOR_SHORT_READ_CHUNK: '8192',
                SUCCESSOR_UNDERREPORT_SIZE: '1' },
        });
        assert.notEqual(oversized.status, 0);
        assert.match(oversized.stderr, /200 KB/);
    } finally { await rm(directory, { recursive: true, force: true }); }
});


test('exported standalone capability rejects a FIFO before any blocking open', { skip: process.platform === 'win32' }, async () => {
    const directory = await mkdtemp(join(tmpdir(), 'successor-alpha-export-fifo-'));
    try {
        const fifo = join(directory, 'input.csv'), right = join(directory, 'right.csv');
        const tool = join(directory, 'standalone-tool.mjs'), output = join(directory, 'output');
        const created = spawnSync('mkfifo', [fifo], { encoding: 'utf8', timeout: 5000 });
        assert.equal(created.status, 0, created.stderr || created.error?.message);
        await writeFile(right, 'id,name\nA,First\n');
        await writeFile(tool, buildCapability(mission, result));
        const execution = spawnSync(process.execPath, [tool, fifo, right, 'id', 'id', output], {
            cwd: directory, encoding: 'utf8', timeout: 5000,
        });
        assert.equal(execution.error, undefined, 'a FIFO must be rejected without timing out');
        assert.notEqual(execution.status, 0);
        assert.match(execution.stderr, /regular CSV file/);
        await assert.rejects(stat(output), { code: 'ENOENT' });
    } finally { await rm(directory, { recursive: true, force: true }); }
});
