// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as models from './apparatus.mjs';
import * as runtime from './typed-runtime.mjs';
import * as construction from './constructor.mjs';
import * as packages from './capability-package.mjs';

test('three public topologies produce distinct generated executable behavior', () => {
    const plans = [];
    for (const topology of models.TOPOLOGIES) {
        const model = models.apparatus(topology), result = construction.construct(model);
        assert.equal(result.status, 'qualified');
        assert.equal(runtime.qualify(model, result.program).ok, true);
        assert.equal(result.attempts.length, result.checkpoint.expanded);
        assert.ok(result.attempts.some(attempt => !attempt.qualified));
        assert.ok(result.ledger.synthesis > result.checkpoint.expanded);
        plans.push(JSON.stringify(result.program));
    }
    assert.equal(new Set(plans).size, 3);
});

test('installation cost and guard changes affect composition rather than choose a fixed winner', () => {
    const model = models.apparatus('shielded');
    model.primitives.find(primitive => primitive.id === 'route-residual').cost = 1;
    const result = construction.construct(model);
    assert.equal(result.status, 'qualified');
    assert.deepEqual(result.program.installations, ['route-residual']);
    assert.deepEqual(result.program.prepare.steps, []);
    const route = model.primitives.find(primitive => primitive.id === 'route-residual');
    route.requires = ['sense-residual'];
    const guarded = construction.construct(model);
    assert.equal(guarded.status, 'qualified');
    assert.ok(guarded.program.installations.includes('protect-residual'));
});

test('cancel export resume preserves exact search, failures and costs', () => {
    const model = models.apparatus();
    const checkpoint = construction.createSearch(model);
    construction.advanceSearch(checkpoint, {steps: 4});
    construction.advanceSearch(checkpoint, {cancel: true});
    const count = checkpoint.attempts.length;
    const reloaded = construction.importSearchCheckpoint(JSON.parse(JSON.stringify(checkpoint)));
    const resumed = construction.advanceSearch(reloaded, {steps: 10000});
    const fresh = construction.construct(model);
    assert.equal(resumed.status, 'qualified');
    assert.deepEqual(resumed.program, fresh.program);
    assert.deepEqual(resumed.ledger, fresh.ledger);
    assert.ok(resumed.attempts.length > count);
    assert.deepEqual(resumed.checkpoint.controls.map(control => control.kind), ['cancel', 'resume']);
});

test('state, memory, total work and wall-clock stops cannot masquerade as qualification', () => {
    const model = models.apparatus();
    for (const options of [{maxStates: 1}, {maxMemoryStates: 1}, {maxCost: 1}]) {
        const result = construction.construct(model, options);
        assert.equal(result.status, 'exhausted');
        assert.match(result.reason, /No qualifying construction found within budget/);
        assert.equal(result.program, null);
        assert.equal(construction.importSearchCheckpoint(result.checkpoint).status, 'exhausted');
    }
    const result = construction.advanceSearch(construction.createSearch(model), {timeLimitMs: 0});
    assert.equal(result.status, 'exhausted');
    assert.match(result.reason, /execution timeout/);
});

test('parsed checkpoint edits and unsafe custom data are rejected', () => {
    const result = construction.construct(models.apparatus());
    const tampered = structuredClone(result.checkpoint);
    tampered.work.synthesis--;
    assert.throws(() => construction.importSearchCheckpoint(tampered), /does not reproduce/);
    assert.throws(() => construction.createSearch(models.apparatus(), {hiddenLaw: [1, 2]}), /Unsupported/);
    assert.throws(() => construction.canonical({limit: Infinity}), /numeric/);
    const values = [1];
    Object.defineProperty(values, '0', {get() { throw Error('Getter must never execute.'); }, enumerable: true});
    assert.throws(() => construction.canonical(values), /accessor/);
});

test('frozen import recomputes semantic replay, failures and full costs after rehashed tampering', async () => {
    const model = models.apparatus(), result = construction.construct(model);
    const pkg = await packages.freezeCapability(model, result);
    assert.deepEqual(await packages.importCapability(pkg), pkg);
    assert.equal(pkg.search.checkpoint.schema, construction.SEARCH_TOKEN_SCHEMA);
    assert.equal(Object.hasOwn(pkg.search.checkpoint, 'queue'), false);
    assert.equal(Object.hasOwn(pkg.search.checkpoint, 'attempts'), false);
    assert.equal(pkg.search.parentSource, null);
    assert.ok(pkg.costLedger.total > 2 * result.ledger.total);
    assert.ok(packages.verificationCostCapability(pkg) > result.ledger.synthesis);
    for (const field of ['cost', 'failure']) {
        const bad = structuredClone(pkg);
        if (field === 'cost') { bad.costLedger.synthesis--; bad.costLedger.total--; }
        else bad.search.attempts[0].qualified = true;
        bad.digest = await packages.digestCapability(bad);
        await assert.rejects(packages.importCapability(bad), /reproduce|tampering/);
    }
    const nearBoundary = construction.construct(model, {maxCost: 500});
    assert.equal(nearBoundary.status, 'qualified');
    await assert.rejects(packages.freezeCapability(model, nearBoundary), /No qualifying construction found within budget/);
});

test('successor inherits compatible installations, requalifies both scopes and retains cumulative costs', async () => {
    const model = models.apparatus(), parent = await packages.freezeCapability(model, construction.construct(model));
    const expanded = models.expandApparatus(model);
    assert.equal(runtime.qualify(expanded, parent.ast).ok, false);
    const search = construction.construct(expanded, {parent});
    assert.equal(search.status, 'qualified');
    const child = await packages.freezeCapability(expanded, search, {parent});
    await packages.importCapability(child);
    assert.equal(child.search.checkpoint.schema, construction.SEARCH_TOKEN_SCHEMA);
    assert.equal(child.search.parentSource.digest, parent.digest);
    assert.equal(Object.hasOwn(child.search.checkpoint.inheritance, 'parent'), false);
    assert.deepEqual(child.scope, ['standard', 'reservoir']);
    assert.deepEqual(child.parentAssets.installations, parent.ast.installations);
    assert.deepEqual(child.parentAssets.observations, []);
    assert.equal(child.parentAssets.ancestorCost, parent.costLedger.total);
    const changed = structuredClone(expanded);
    changed.edges[0].gain = 0.5;
    assert.throws(() => construction.construct(changed, {parent}), /Stale parent/);
});

test('compact recovery reconstructs a thousand-state cancelled search without duplicating queues or failures', () => {
    const model = models.apparatus();
    for (let index = 0; index < 3; index++) {
        const id = `dust-${index}`;
        model.channels.push({id, initial: 8, drift: 2, cap: 16, scopes: ['standard', 'reservoir']});
        model.edges.push({id: `${id}-readout`, from: id, to: 'readout', gain: 1});
        for (const source of ['protect-residual', 'flush-residual']) {
            const primitive = structuredClone(model.primitives.find(item => item.id === source));
            primitive.id = source.replace('residual', id); primitive.target = id;
            model.primitives.push(primitive);
        }
    }
    const checkpoint = construction.createSearch(model, {maxStates: 5000, maxMemoryStates: 100000});
    construction.advanceSearch(checkpoint, {steps: 1000, timeLimitMs: 60000});
    assert.equal(checkpoint.expanded, 1000);
    construction.advanceSearch(checkpoint, {cancel: true});
    const token = construction.exportSearchCheckpoint(checkpoint);
    assert.equal(construction.importSearchCheckpoint(token), checkpoint);
    assert.ok(JSON.stringify(token).length < 10000);
    assert.ok(JSON.stringify(checkpoint).length > 1000000);
    assert.equal(Object.hasOwn(token, 'queue'), false);
    assert.equal(Object.hasOwn(token, 'attempts'), false);
    const restored = construction.importSearchCheckpoint(JSON.parse(JSON.stringify(token)));
    assert.deepEqual(restored, checkpoint);
    const resumed = construction.advanceSearch(restored, {steps: 16, timeLimitMs: 60000});
    const continued = construction.advanceSearch(checkpoint, {steps: 16, timeLimitMs: 60000});
    assert.deepEqual(resumed.checkpoint, continued.checkpoint);
    assert.deepEqual(resumed.ledger, continued.ledger);
    const tampered = structuredClone(token);
    tampered.summary.work.synthesis--;
    assert.throws(() => construction.importSearchCheckpoint(tampered), /does not reproduce/);
    const overflow = structuredClone(token);
    overflow.expanded = overflow.options.maxStates + 1;
    assert.throws(() => construction.importSearchCheckpoint(overflow), /frozen replay limits/);
});

test('compact child checkpoints resolve parent assets once and reject missing or changed context', async () => {
    const model = models.apparatus();
    const parent = await packages.freezeCapability(model, construction.construct(model));
    const checkpoint = construction.createSearch(models.expandApparatus(model), {parent});
    construction.advanceSearch(checkpoint, {steps: 3});
    construction.advanceSearch(checkpoint, {cancel: true});
    const token = JSON.parse(JSON.stringify(construction.compactSearchCheckpoint(checkpoint)));
    assert.equal(Object.hasOwn(token.inheritance, 'parent'), false);
    assert.equal(token.inheritance.parentDigest, parent.digest);
    assert.throws(() => construction.importSearchCheckpoint(token), /parent asset binding/);
    const restored = construction.importSearchCheckpoint(token, {parent});
    assert.deepEqual(restored, checkpoint);
    assert.equal(construction.advanceSearch(restored, {steps: 1000}).status, 'qualified');
    const wrong = structuredClone(parent); wrong.digest = '0'.repeat(64);
    assert.throws(() => construction.importSearchCheckpoint(token, {parent: wrong}), /parent asset binding/);
});
