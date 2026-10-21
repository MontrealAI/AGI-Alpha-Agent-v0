// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {apparatus, expandApparatus} from './apparatus.mjs';
import {compile, qualify, measure} from './typed-runtime.mjs';
import {verify} from './independent-checker.mjs';
import {construct, createSearch, advanceSearch, importSearchCheckpoint, exportSearchCheckpoint} from './constructor.mjs';
import {freezeCapability, importCapability, digestCapability} from './capability-package.mjs';
import {evaluateFrozenReuse, proveRecurringObstruction} from './evaluation.mjs';

const copy = value => JSON.parse(JSON.stringify(value));
const ast = (installations = [], steps = [], scope = ['standard']) => ({schema: 'out-evolve-ast/v1',
    installations, prepare: {op: 'sequence', steps: steps.map(id => ({op: 'primitive', id}))}, scope});
function tiny() {
    const app = apparatus('shielded');
    app.channels = app.channels.filter(channel => channel.id === 'residual');
    app.edges = app.edges.filter(edge => edge.id === 'residual-readout');
    app.primitives = app.primitives.filter(primitive => ['protect-residual', 'flush-residual',
        'halve-residual', 'route-residual', 'erase-product'].includes(primitive.id));
    app.limits.maxInstructions = 6;
    return app;
}
const limits = {maxProgramSize: 4, maxStates: 20000, maxMemoryStates: 20000, maxCost: 1000000};
function independentlyRejected(app, program, certificate) {
    try { return !verify(app, program, certificate).ok; } catch { return true; }
}

test('independent: sound dominance agrees with exhaustive tiny-space construction under changed costs', () => {
    for (const [shield, route] of [[4, 20], [9, 2], [1, 7], [3, 4], [8, 8], [2, 3]]) {
        const app = tiny();
        app.primitives.find(item => item.id === 'protect-residual').cost = shield;
        app.primitives.find(item => item.id === 'route-residual').cost = route;
        const pruned = construct(app, limits);
        const exhaustive = construct(app, {...limits, dominance: false});
        assert.equal(pruned.status, 'qualified');
        assert.equal(exhaustive.status, 'qualified');
        const executionCost = result => result.ledger.installation + result.ledger.operation;
        assert.equal(executionCost(pruned), executionCost(exhaustive), `${shield},${route}`);
        assert.equal(executionCost(pruned), Math.min(shield + 1, route));
        assert.equal(verify(app, pruned.program, pruned.certificate).ok, true);
    }
});

test('independent: initially clean repeated attenuation fails the recurring error contract', () => {
    const app = tiny();
    app.channels[0].initial = 0;
    app.tolerance = 3;
    const program = ast([], ['halve-residual']);
    const first = measure(app, program, 42, {cycle: 0});
    const later = measure(app, program, 42, {cycle: 12});
    assert.ok(Math.abs(first.error) <= app.tolerance);
    assert.ok(Math.abs(later.error) > app.tolerance);
    const report = qualify(app, program);
    assert.equal(report.ok, false);
    assert.equal(report.errorBound, 4);
    assert.equal(independentlyRejected(app, program, report.certificate), true);
});

test('independent: an undealt-with graph coupling invalidates a previously sufficient program', () => {
    const app = tiny();
    const program = ast(['protect-residual'], ['flush-residual']);
    assert.equal(qualify(app, program).ok, true);
    app.channels.push({id: 'hidden', initial: 2, drift: 1, cap: 8, scopes: ['standard']});
    app.edges.push({id: 'hidden-residual', from: 'hidden', to: 'residual', gain: 1});
    const report = qualify(app, program);
    assert.equal(report.ok, false);
    assert.equal(report.certificate.coefficients.hidden, 1);
    assert.equal(independentlyRejected(app, program, report.certificate), true);
});

test('independent: destruction cannot trade productive state for qualification', () => {
    const app = tiny();
    const program = ast(['protect-residual'], ['flush-residual', 'erase-product']);
    const report = qualify(app, program);
    assert.equal(report.errorBound, 0);
    assert.equal(report.preserved, false);
    assert.equal(report.ok, false);
    assert.equal(independentlyRejected(app, program, report.certificate), true);
    assert.throws(() => measure(app, program, 42));
});

test('independent: malformed AST, unsupported graph and undeclared effects are rejected', () => {
    const app = tiny();
    const base = ast();
    for (const count of [0, -1, 1.5, Infinity, 33]) {
        assert.throws(() => compile(app, {...base,
            prepare: {op: 'repeat', count, body: {op: 'primitive', id: 'halve-residual'}}}));
    }
    assert.throws(() => compile(app, {...base, prepare: {op: 'eval', source: '42'}}));
    const cycle = copy(app);
    cycle.edges.push({id: 'self-cycle', from: 'residual', to: 'residual', gain: 1});
    assert.throws(() => compile(cycle, base));
    const effects = copy(app);
    effects.primitives[0].effects.push('productive');
    assert.throws(() => compile(effects, base));
});

test('independent: cancellation and serialized resume preserve work and reproduce the uninterrupted result', () => {
    const app = tiny();
    const checkpoint = createSearch(app, limits);
    advanceSearch(checkpoint, {steps: 2, timeLimitMs: 60000});
    const before = copy(checkpoint);
    const cancelled = advanceSearch(checkpoint, {cancel: true});
    assert.equal(cancelled.status, 'cancelled');
    assert.equal(checkpoint.expanded, before.expanded);
    assert.deepEqual(checkpoint.attempts, before.attempts);
    const restored = importSearchCheckpoint(copy(checkpoint));
    const resumed = advanceSearch(restored, {steps: 20000, timeLimitMs: 60000});
    const direct = construct(app, limits);
    assert.equal(resumed.status, direct.status);
    assert.deepEqual(resumed.program, direct.program);
    assert.deepEqual(resumed.ledger, direct.ledger);
    assert.deepEqual(resumed.attempts, direct.attempts);
    const corrupt = copy(checkpoint);
    corrupt.work.synthesis = 0;
    assert.throws(() => importSearchCheckpoint(corrupt));
});

test('independent: semantically invalid package is rejected even after recomputing its outer digest', async () => {
    const app = tiny();
    const result = construct(app, limits);
    const pkg = await freezeCapability(app, result);
    const altered = copy(pkg);
    altered.ast.prepare.steps.push({op: 'primitive', id: 'erase-product'});
    altered.digest = await digestCapability(altered);
    await assert.rejects(() => importCapability(altered));
    const forgedCertificate = copy(pkg);
    forgedCertificate.certificate.productiveGain = 0;
    forgedCertificate.digest = await digestCapability(forgedCertificate);
    await assert.rejects(() => importCapability(forgedCertificate));
});

test('independent: rehashing reduced costs or erased unsuccessful search evidence cannot establish trust', async () => {
    const app = tiny();
    const pkg = await freezeCapability(app, construct(app, limits));
    const discounted = copy(pkg);
    for (const key of ['synthesis', 'tuning', 'installation', 'calibration', 'qualification', 'operation', 'maintenance', 'total']) {
        discounted.costLedger[key] = 0;
    }
    discounted.digest = await digestCapability(discounted);
    await assert.rejects(() => importCapability(discounted));
    const erased = copy(pkg);
    erased.search.attempts = [];
    erased.search.expanded = 0;
    erased.digest = await digestCapability(erased);
    await assert.rejects(() => importCapability(erased));
});


test('independent: previously exposed final truth remains regression after package identity changes', async () => {
    const app = tiny();
    const firstPackage = await freezeCapability(app, construct(app, limits));
    const first = await evaluateFrozenReuse(firstPackage, {seed: 731});
    const renamed = copy(app);
    renamed.id += '-renamed';
    const secondPackage = await freezeCapability(renamed, construct(renamed, limits));
    assert.notEqual(firstPackage.digest, secondPackage.digest);
    const second = await evaluateFrozenReuse(secondPackage, {seed: 731, exposedCaseIds: first.exposedCaseIds});
    assert.equal(first.status, 'PASS');
    assert.equal(second.status, 'PASS');
    assert.equal(second.packageDigestBefore, second.packageDigestAfter);
    assert.equal(second.cases.length, 3);
    assert.ok(second.cases.every(item => item.exposure === 'previously-exposed-regression'));
});

test('independent: budget-excluded branches never become an impossibility claim', () => {
    const result = construct(tiny(), {...limits, maxCost: 2});
    assert.equal(result.status, 'exhausted');
    assert.match(result.reason, /No qualifying construction found within budget/);
});


test('independent: compact recovery reconstructs all attempts and rejects edited work summaries', () => {
    const app = tiny();
    const checkpoint = createSearch(app, limits);
    advanceSearch(checkpoint, {steps: 3, timeLimitMs: 60000});
    advanceSearch(checkpoint, {cancel: true});
    const compact = exportSearchCheckpoint(checkpoint);
    assert.equal(Object.hasOwn(compact, 'queue'), false);
    assert.equal(Object.hasOwn(compact, 'attempts'), false);
    const restored = importSearchCheckpoint(copy(compact));
    assert.deepEqual(restored, checkpoint);
    const forged = copy(compact);
    forged.summary.work.synthesis -= 1;
    assert.throws(() => importSearchCheckpoint(forged));
});

test('independent: inherited compact recovery requires the exact independently valid parent context', async () => {
    const app = apparatus('shielded');
    const parent = await freezeCapability(app, construct(app));
    const expanded = expandApparatus(app);
    const child = createSearch(expanded, {...limits, maxProgramSize: 8, parent});
    advanceSearch(child, {steps: 2, timeLimitMs: 60000});
    advanceSearch(child, {cancel: true});
    const compact = exportSearchCheckpoint(child);
    assert.throws(() => importSearchCheckpoint(copy(compact)));
    const restored = importSearchCheckpoint(copy(compact), {parent});
    assert.deepEqual(restored, child);
    const resumed = advanceSearch(restored, {steps: 20000, timeLimitMs: 60000});
    const direct = construct(expanded, {...limits, maxProgramSize: 8, parent});
    assert.equal(resumed.status, 'qualified');
    assert.deepEqual(resumed.program, direct.program);
    assert.deepEqual(resumed.ledger, direct.ledger);
});

test('independent: recurring obstruction agrees with exhaustive impossibility and does not reject an escape route', () => {
    const app = tiny();
    app.primitives = app.primitives.filter(primitive => !['shield', 'route'].includes(primitive.kind));
    const proof = proveRecurringObstruction(app);
    assert.ok(proof);
    assert.equal(proof.channel, 'residual');
    assert.equal(proof.strictLowerBound, 2);
    assert.equal(construct(app, {...limits, dominance: false}).status, 'infeasible');
    app.primitives.push(copy(tiny().primitives.find(primitive => primitive.kind === 'route')));
    assert.equal(proveRecurringObstruction(app), null);
    assert.equal(construct(app, limits).status, 'qualified');
});
