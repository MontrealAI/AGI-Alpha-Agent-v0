// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {apparatus} from './apparatus.mjs';
import {createSearch, advanceSearch, construct, exportSearchCheckpoint} from './constructor.mjs';
import {freezeCapability, digestCapability} from './capability-package.mjs';
import {createOutEvolveWorkspace, appendOutEvolveEvent, inspectOutEvolveWorkspace,
    requireHistoryContinuation, searchHistoryCapacity, WORKSPACE_LIMITS} from './out-evolve-workspace.mjs';

test('uppercase failed and inconclusive evidence survives a later qualifying package and reload', async () => {
    let history = createOutEvolveWorkspace('out-evolve-history-test');
    history = await appendOutEvolveEvent(history, 'reuse', {status: 'FAIL', cases: [{status: 'FAIL', actual: 0, expected: 1}]});
    history = await appendOutEvolveEvent(history, 'reuse', {status: 'INCONCLUSIVE', cases: []});
    const app = apparatus('shielded');
    const pkg = await freezeCapability(app, construct(app));
    history = await appendOutEvolveEvent(history, 'package-frozen', {status: 'qualified', package: pkg});
    const checked = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.equal(checked.failed, 1);
    assert.equal(checked.inconclusive, 1);
    assert.equal(checked.packageCount, 1);
    assert.equal(checked.evidenceStatus, 'retained-failure');
    assert.equal(checked.latestPackage.digest, pkg.digest);
    assert.equal(checked.workspace.events[0].payload.cases[0].actual, 0);
});

test('cancelled search reloads and resumes its deterministic frontier and accumulated work', async () => {
    let history = createOutEvolveWorkspace('out-evolve-cancel-test');
    const checkpoint = createSearch(apparatus('referenced'));
    const started = await appendOutEvolveEvent(history, 'search-started', {status: 'searching', checkpoint});
    let result = advanceSearch(checkpoint, {steps: 5});
    result = advanceSearch(result.checkpoint, {cancel: true});
    history = await appendOutEvolveEvent(started, 'search-stopped', {status: result.status, checkpoint: result.checkpoint});
    const restored = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.equal(restored.checkpoint.status, 'cancelled');
    assert.equal(restored.checkpoint.expanded, 5);
    const resumed = advanceSearch(restored.checkpoint, {steps: 1000});
    assert.equal(resumed.status, 'qualified');
    assert.ok(resumed.ledger.synthesis >= result.ledger.synthesis);
    assert.deepEqual(resumed.program, construct(apparatus('referenced')).program);
    assert.equal(history.events[1].payload.status, 'cancelled');
    assert.equal(started.events[0].payload.checkpoint.expanded, 0);
});

test('imports reject changed events and executable claims even when package digest is recomputed', async () => {
    let history = createOutEvolveWorkspace('out-evolve-tamper-test');
    history = await appendOutEvolveEvent(history, 'failure', {message: 'Retain original failure.', status: 'FAIL'});
    const changed = structuredClone(history);
    changed.events[0].payload.message = 'Pretend this passed.';
    await assert.rejects(inspectOutEvolveWorkspace(changed), /digest mismatch/);
    const app = apparatus('shielded');
    const pkg = await freezeCapability(app, construct(app));
    pkg.ast.prepare.steps = [{op: 'primitive', id: 'erase-product'}];
    pkg.digest = await digestCapability(pkg);
    await assert.rejects(appendOutEvolveEvent(history, 'package-frozen', {package: pkg, status: 'qualified'}));
    assert.equal(history.events.length, 1);
});

test('tampered checkpoint and mismatched status cannot enter append-only history', async () => {
    const history = createOutEvolveWorkspace('out-evolve-invalid-checkpoint');
    const checkpoint = createSearch(apparatus());
    checkpoint.work.synthesis = 0.5;
    await assert.rejects(appendOutEvolveEvent(history, 'search-started', {status: 'searching', checkpoint}), /tampering rejected/);
    await assert.rejects(appendOutEvolveEvent(history, 'search-stopped', {
        status: 'qualified', checkpoint: createSearch(apparatus())
    }), /status differs/);
});

test('history admits fractional model data while rejecting authority and malformed briefs', async () => {
    let history = createOutEvolveWorkspace('out-evolve-finite-test');
    history = await appendOutEvolveEvent(history, 'comparison', {status: 'COMPLETED', amortizedPerUse: 1.25});
    assert.equal((await inspectOutEvolveWorkspace(history)).workspace.events[0].payload.amortizedPerUse, 1.25);
    const changed = structuredClone(history); changed.authority = ['network'];
    await assert.rejects(inspectOutEvolveWorkspace(changed), /authority/);
    await assert.rejects(appendOutEvolveEvent(history, 'brief', {purpose: 'x', constraints: 'y', budget: 1.5, apparatus: apparatus()}));
    await assert.rejects(appendOutEvolveEvent(history, 'comparison', {status: 'COMPLETED', total: Infinity}));
});

test('importing an earlier same-identity history cannot erase its failures', async () => {
    const earlier = createOutEvolveWorkspace('out-evolve-no-rollback');
    const later = await appendOutEvolveEvent(earlier, 'failure', {status: 'FAIL', message: 'Still failed.'});
    assert.throws(() => requireHistoryContinuation(later, earlier), /discard or replace/);
    requireHistoryContinuation(earlier, later);
    requireHistoryContinuation(later, createOutEvolveWorkspace('out-evolve-separate-history'));
});

function dustyApparatus() {
    const app = apparatus('shielded');
    for (const suffix of ['a', 'b', 'c']) {
        const name = `dust-${suffix}`;
        app.channels.push({...app.channels[0], id: name});
        app.edges.push({id: `${name}-readout`, from: name, to: 'readout', gain: 1});
        for (const original of app.primitives.slice(0, 2)) {
            app.primitives.push({...original, id: `${original.kind}-${name}`, target: name});
        }
    }
    return app;
}

test('long recovery history stores compact candidate replay rather than cumulative queue and attempt copies', async () => {
    let history = createOutEvolveWorkspace('out-evolve-compact-recovery');
    let checkpoint = createSearch(dustyApparatus(), {maxStates: 1000, maxMemoryStates: 20000, maxCost: 1000000});
    history = await appendOutEvolveEvent(history, 'search-started', {status: checkpoint.status, checkpoint});
    for (let chunk = 0; chunk < 24; chunk++) {
        const result = advanceSearch(checkpoint, {steps: 16});
        checkpoint = result.checkpoint;
        assert.equal(result.status, 'searching');
        history = await appendOutEvolveEvent(history, 'search-stopped', {status: result.status,
            checkpoint: exportSearchCheckpoint(checkpoint), ledger: result.ledger,
            attempts: result.attempts, frontier: result.frontier});
        assert.equal(Object.hasOwn(history.events.at(-1).payload, 'attempts'), false);
        assert.equal(Object.hasOwn(history.events.at(-1).payload, 'frontier'), false);
    }
    const cancelled = advanceSearch(checkpoint, {cancel: true});
    history = await appendOutEvolveEvent(history, 'search-stopped', {status: cancelled.status,
        checkpoint: exportSearchCheckpoint(cancelled.checkpoint), ledger: cancelled.ledger});
    assert.ok(checkpoint.expanded > 336);
    assert.ok(JSON.stringify(history).length < 300000);
    const restored = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.deepEqual(restored.checkpoint.work, checkpoint.work);
    assert.deepEqual(restored.checkpoint.attempts, checkpoint.attempts);
    assert.deepEqual(restored.checkpoint.queue, checkpoint.queue);
    const actual = advanceSearch(restored.checkpoint, {steps: 16});
    const expected = advanceSearch(checkpoint, {steps: 16});
    assert.deepEqual(actual.ledger, expected.ledger);
    assert.deepEqual(actual.program, expected.program);
});

test('workspace reserves terminal evidence and a final unfinished checkpoint before more constructor work', async () => {
    let history = createOutEvolveWorkspace('out-evolve-terminal-reserve');
    const checkpoint = createSearch(apparatus('shielded'), {maxStates: 2000, maxMemoryStates: 2000});
    assert.equal(searchHistoryCapacity(history, checkpoint).canAdvance, true);
    for (let index = 0; index < WORKSPACE_LIMITS.events - 2; index++) {
        history = await appendOutEvolveEvent(history, 'comparison', {status: 'COMPLETED', sequence: index});
    }
    const capacity = searchHistoryCapacity(history, checkpoint);
    assert.equal(capacity.canAdvance, false);
    assert.equal(capacity.remainingEvents, 2);
    assert.ok(capacity.terminalEvidenceReserve > 65536);
    history = await appendOutEvolveEvent(history, 'search-paused', {status: 'INCONCLUSIVE',
        checkpoint: exportSearchCheckpoint(checkpoint), reason: 'History capacity reached before further work.'});
    const restored = await inspectOutEvolveWorkspace(history);
    assert.equal(restored.inconclusive, 1);
    assert.equal(restored.checkpoint.expanded, 0);
    assert.deepEqual(restored.checkpoint.work, checkpoint.work);
    assert.ok(history.events.length <= WORKSPACE_LIMITS.events);
    let byteBound = createOutEvolveWorkspace('out-evolve-byte-reserve');
    byteBound = await appendOutEvolveEvent(byteBound, 'comparison', {status: 'COMPLETED', note: 'x'.repeat(4500000)});
    const bytes = searchHistoryCapacity(byteBound, checkpoint);
    assert.ok(bytes.remainingEvents > 3);
    assert.equal(bytes.canAdvance, false);
    byteBound = await appendOutEvolveEvent(byteBound, 'search-paused', {status: 'INCONCLUSIVE',
        checkpoint: exportSearchCheckpoint(checkpoint), reason: 'Terminal evidence space reserved before execution.'});
    assert.equal((await inspectOutEvolveWorkspace(byteBound)).checkpoint.expanded, 0);
    assert.ok(JSON.stringify(byteBound).length < WORKSPACE_LIMITS.bytes);
});
