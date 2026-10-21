// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as workspace from './workspace.mjs';
import {digest} from '../../docs/assets/successor/engine.mjs';

const copy = value => JSON.parse(JSON.stringify(value));
async function full() {
    let value = await workspace.createWorkspace(workspace.DEFAULT_BRIEF, workspace.defaultExperiment());
    value = await workspace.recordEvaluation(value, 'development');
    return workspace.recordEvaluation(value, 'heldout');
}
async function rehash(value) {
    let previous = null;
    for (const event of value.events) {
        event.previous = previous;
        const body = {missionId: value.missionId, sequence: event.sequence, kind: event.kind,
            previous, payload: event.payload};
        event.digest = await digest('capability-event', body);
        previous = event.digest;
    }
    return value;
}

test('construct, evaluate, reuse, successor, serialize and reopen without replacing evidence', async () => {
    const original = await full(), exactHistory = workspace.canonical(original.events);
    const first = await workspace.inspectWorkspace(original);
    assert.equal(first.latest.development.report.verdict, 'pass');
    assert.equal(first.latest.heldout.report.verdict, 'pass');
    assert.equal(first.latest.heldout.exposure.status, 'fresh-within-record-not-protected');
    const brief = {...workspace.DEFAULT_BRIEF, restrictiveAssumption: 'A changed proposed use requires new qualification.'};
    let next = await workspace.addSuccessor(original, brief, workspace.defaultExperiment(), 'Test the changed assumption.');
    const fresh = await workspace.inspectWorkspace(next);
    assert.equal(fresh.latest.development, null);
    assert.equal(fresh.latest.heldout, null);
    assert.equal(fresh.latest.briefAcceptance, 'not-evaluated');
    assert.equal(fresh.latest.inheritedEvidence, 'historical-only');
    assert.equal(workspace.canonical(next.events.slice(0, original.events.length)), exactHistory);
    next = await workspace.recordEvaluation(next, 'development');
    next = await workspace.recordEvaluation(next, 'heldout');
    const replayed = await workspace.parseWorkspace(workspace.canonical(next));
    assert.deepEqual(replayed, next);
    const inspected = await workspace.inspectWorkspace(replayed);
    assert.equal(inspected.latest.heldout.exposure.status, 'previously-exposed-not-heldout');
    assert.ok(inspected.latest.heldout.exposure.repeatedMasks.length > 0);
    assert.equal(inspected.versions[0].heldout.exposure.status, 'fresh-within-record-not-protected');
    assert.deepEqual(original, await workspace.parseWorkspace(workspace.canonical(original)));
});

test('blue-sky architecture stays a proposal rather than faking execution', async () => {
    const brief = {...workspace.DEFAULT_BRIEF, title: 'Adaptive manufacturing architecture',
        proposedConstruction: 'Proposed modular platform for multiple manufacturing families.',
        constructionKind: 'productive-architecture', valueHypothesis: 'Hypothesis only: untested value.'};
    const value = await workspace.createWorkspace(brief, null);
    assert.equal((await workspace.inspectWorkspace(value)).latest.experiment, null);
    await assert.rejects(workspace.recordEvaluation(value, 'development'), /no implemented evaluator/);
    assert.equal(value.events.length, 1);
});

test('explicit incompatible world retains computed failure with unchanged objective', async () => {
    const config = workspace.defaultExperiment();
    config.world.degree = 3;
    let value = await workspace.createWorkspace(workspace.DEFAULT_BRIEF, config);
    const frozen = value.events[0].payload.frozenDigest;
    value = await workspace.recordEvaluation(value, 'development');
    value = await workspace.recordEvaluation(value, 'heldout');
    const latest = (await workspace.inspectWorkspace(value)).latest;
    assert.equal(latest.heldout.report.verdict, 'fail');
    assert.ok(latest.heldout.report.failure_reasons.length > 0);
    assert.equal(latest.frozenDigest, frozen);
    assert.equal(latest.briefAcceptance, 'not-evaluated');
});

test('tampering, rehashed unsupported claims and wrong-version evidence are refused', async () => {
    const value = await full();
    for (const mutate of [
        v => { v.events[1].payload.report.verdict = 'commercially-validated'; },
        v => { v.events[2].payload.frozenDigest = '0'.repeat(64); },
        v => { v.events[2].payload.number = 2; },
        v => { v.events[2].payload.report.real_revenue = 1000000; },
        v => { v.events[1].payload.construction.model.coefficients[0].coefficient += 1; },
        v => { v.events[0].payload.specification.brief.objective = 'Relaxed objective'; },
        v => { v.events[2].payload.exposure.status = 'independently-protected'; }
    ]) {
        const changed = copy(value);
        mutate(changed);
        await assert.rejects(workspace.inspectWorkspace(await rehash(changed)));
    }
    const altered = copy(value);
    altered.events[0].payload.reason = 'Rewritten history';
    await assert.rejects(workspace.inspectWorkspace(altered), /binding mismatch/);
});

test('no imported permission, route, payment, code or unsupported evidence fields', async () => {
    const value = await full();
    for (const override of [{authority: ['execute']}, {paymentRoute: 'USDC'}, {paymentRoute: 'AGIALPHA'},
        {approvedSpending: 10}, {execute: 'some supplied code'}]) {
        await assert.rejects(workspace.inspectWorkspace({...value, ...override}));
    }
    assert.deepEqual(value.authority, []);
    assert.equal(value.paymentRoute, 'none');
    assert.equal((await workspace.inspectWorkspace(value)).latest.economicOutcome, 'not-evaluated');
});

test('phase gating, bounds, duplicate input and inherited retuning status', async () => {
    let value = await workspace.createWorkspace(workspace.DEFAULT_BRIEF, workspace.defaultExperiment());
    await assert.rejects(workspace.recordEvaluation(value, 'heldout'), /before held-out/);
    await assert.rejects(workspace.recordEvaluation(value, 'execute-mainnet'), /Unsupported/);
    await assert.rejects(workspace.addSuccessor(value, workspace.DEFAULT_BRIEF, workspace.defaultExperiment(), 'Same'),
        /explicit change/);
    await assert.rejects(workspace.createWorkspace({...workspace.DEFAULT_BRIEF, objective: ''}));
    await assert.rejects(workspace.createWorkspace({...workspace.DEFAULT_BRIEF, unexpected: true}));
    await assert.rejects(workspace.parseWorkspace('{"schema":1,"schema":2}'), /Duplicate/);
    await assert.rejects(workspace.parseWorkspace('x'.repeat(2_000_001)), /2 MB/);
    value = await workspace.recordEvaluation(value, 'development');
    await assert.rejects(workspace.recordEvaluation(value, 'development'), /already contains/);
    for (let number = 2; number <= workspace.LIMITS.versions; number++) {
        value = await workspace.addSuccessor(value, {...workspace.DEFAULT_BRIEF, title: `Version ${number}`}, null,
            'An untested proposed extension.');
    }
    await assert.rejects(workspace.addSuccessor(value, workspace.DEFAULT_BRIEF, null, 'Too many'), /capacity/);
    assert.equal((await workspace.inspectWorkspace(value)).versions.length, 8);
});

test('syntactic world changes and equivalent changed-seed worlds cannot reset case exposure', async () => {
    const original = await full();
    const prior = (await workspace.inspectWorkspace(original)).latest;
    const constant = prior.development.construction.model.coefficients.find(term => term.mask === 0).coefficient;
    for (const config of [
        {...workspace.defaultExperiment(), world: {...workspace.defaultExperiment().world,
            overrides: [{mask: 0, coefficient: constant}]}},
        {...workspace.defaultExperiment(), seed: 555, world: {...workspace.defaultExperiment().world,
            overrides: prior.development.construction.model.coefficients}}
    ]) {
        let next = await workspace.addSuccessor(original, workspace.DEFAULT_BRIEF, config, 'Equivalent representation.');
        next = await workspace.recordEvaluation(next, 'development');
        next = await workspace.recordEvaluation(next, 'heldout');
        const latest = (await workspace.inspectWorkspace(next)).latest;
        assert.deepEqual(latest.heldout.report.comparisons, prior.heldout.report.comparisons);
        assert.equal(latest.heldout.exposure.status, 'previously-exposed-not-heldout');
        assert.deepEqual(latest.heldout.exposure.repeatedMasks, latest.heldout.report.evaluation_masks);
        assert.equal(latest.heldout.exposure.policy, 'conservative-mask-history');
    }
});

test('a passing reuse phase never erases failed development acceptance', async () => {
    const config = workspace.defaultExperiment();
    config.input_count = 4;
    config.world.degree = 3;
    config.world.overrides = Array.from({length: 15}, (_, mask) => ({mask,
        coefficient: mask === 11 ? 1 : mask === 14 ? -1 : 0}));
    let value = await workspace.createWorkspace(workspace.DEFAULT_BRIEF, config);
    value = await workspace.recordEvaluation(value, 'development');
    assert.equal((await workspace.inspectWorkspace(value)).latest.witnessAcceptance, 'fail');
    value = await workspace.recordEvaluation(value, 'heldout');
    const latest = (await workspace.inspectWorkspace(value)).latest;
    assert.equal(latest.development.report.verdict, 'fail');
    assert.equal(latest.heldout.report.verdict, 'pass');
    assert.equal(latest.witnessAcceptance, 'fail');
});

test('editor parsing rejects duplicate keys and floats before model validation', () => {
    assert.deepEqual(workspace.parseExperiment(JSON.stringify(workspace.defaultExperiment())), workspace.defaultExperiment());
    assert.throws(() => workspace.parseExperiment('{"seed":1,"seed":2}'), /Duplicate/);
    const text = JSON.stringify(workspace.defaultExperiment()).replace('"seed":17', '"seed":1.5');
    assert.throws(() => workspace.parseExperiment(text), /integer/);
});

test('v1 inspection retains one history frame when caller edits during digest awaits', async () => {
    const input = await workspace.createWorkspace(), original = copy(input);
    const pending = workspace.inspectWorkspace(input);
    input.events[0].payload.reason = 'Changed during digest';
    const inspection = await pending;
    assert.equal(inspection.latest.reason, original.events[0].payload.reason);
    assert.equal(Object.isFrozen(input), false);
    await assert.rejects(workspace.inspectWorkspace(copy(input)), /binding mismatch/);
    const reopened = await workspace.parseWorkspace(workspace.canonical(original));
    assert.deepEqual(reopened, original);
    assert.equal(Object.isFrozen(reopened), false);
});

test('workspace inspection uses captured descriptor fields without original property reads', async () => {
    const original = await workspace.createWorkspace(); let reads = 0;
    const input = new Proxy(original, {get() { reads++; throw Error('Original workspace property read'); }});
    const inspection = await workspace.inspectWorkspace(input);
    assert.equal(inspection.latest.reason, original.events[0].payload.reason);
    assert.equal(reads, 0);
});

test('unsupported fields in the captured workspace frame cannot disappear before semantic checks', async () => {
    const original = await workspace.createWorkspace(); let scans = 0;
    const input = new Proxy({...original, externalAuthority: true}, {
        ownKeys(value) {
            return ++scans === 1 ? Reflect.ownKeys(value) : Reflect.ownKeys(value).filter(key => key !== 'externalAuthority');
        }
    });
    await assert.rejects(workspace.inspectWorkspace(input), /Unsupported capability workspace/);
    assert.equal(scans, 1);
});

for (const operation of ['successor', 'evaluation']) {
    test(`${operation} appends only to the checked captured v1 history prefix`, async () => {
        const input = await workspace.createWorkspace(workspace.DEFAULT_BRIEF, workspace.defaultExperiment());
        const original = copy(input);
        const pending = operation === 'successor'
            ? workspace.addSuccessor(input, {...workspace.DEFAULT_BRIEF, title: 'Changed proposal'}, null, 'New scope')
            : workspace.recordEvaluation(input, 'development');
        input.events[0].payload.reason = 'Caller changed the checked prefix';
        const next = await pending;
        assert.deepEqual(next.events.slice(0, original.events.length), original.events);
        assert.equal(Object.isFrozen(next), false);
        assert.equal((await workspace.inspectWorkspace(next)).head, next.events.at(-1).digest);
    });
}
