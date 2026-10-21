// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as workspace from './workspace.mjs';
import * as history from './discovery-lab-history.mjs';
import * as runtime from './discovery-lab.mjs';
import * as contract from './discovery-lab-contract.mjs';
import * as protocol from '../../docs/assets/successor/engine.mjs';

const sources = {modelDigest: '1'.repeat(64), sourceDigest: '2'.repeat(64), evaluatorDigest: '3'.repeat(64)};
const copy = value => JSON.parse(contract.canonical(value));
async function completed(elapsedMs = 1) {
    let value = await workspace.createWorkspace();
    const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sources);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const result = runtime.runCampaign(start.charter);
    const verification = history.verifyForRecording(start.charter, result);
    return workspace.recordDiscoveryEvent(value, 'lab-completed',
        await history.completedPayload(start.attempt, result, elapsedMs, verification.verificationResources));
}
async function rehash(value) {
    let previous = null;
    for (const event of value.events) {
        event.previous = previous;
        event.digest = await protocol.digest('capability-event', {missionId: value.missionId,
            sequence: event.sequence, kind: event.kind, previous, payload: event.payload});
        previous = event.digest;
    }
    return value;
}
function graphFrozen(value) {
    if (!value || typeof value !== 'object') return true;
    return Object.isFrozen(value) && Object.values(value).every(graphFrozen);
}

test('a frozen per-phase charter reserves both construction and explicit complete verification before work', async () => {
    const value = await completed();
    const start = value.events[1].payload;
    const finish = value.events[2].payload;
    for (const key of ['acquisitions', 'search', 'checking', 'installations']) {
        assert.equal(start.reservation[key], 2 * start.charter.budget[key]);
        assert.ok(finish.result.resources[key] + finish.recordedVerification[key] <= start.reservation[key]);
    }
    assert.equal(start.reservation.workerCapacity, start.charter.workerCapacity);
    assert.equal(start.reservation.storageBytes, history.REPORT_RESERVE_BYTES);
    const forged = copy(value);
    for (const key of Object.keys(forged.events[1].payload.reservation)) forged.events[1].payload.reservation[key] = 0;
    await rehash(forged);
    await assert.rejects(workspace.inspectWorkspace(forged), /reservation/i);
});

test('failed new semantic evidence is metered while false metadata reuses proof without inventing replay', async () => {
    const value = await completed();
    for (const [index, alter] of [
        next => { next.events[2].payload.result.resources.search = 0; },
        next => { next.events[2].payload.recordedVerification.search = 0; }
    ].entries()) {
        const forged = copy(value);
        alter(forged);
        forged.events[2].payload.resultDigest = await contract.payloadDigest(forged.events[2].payload.result);
        await rehash(forged);
        const before = history.auditSnapshot();
        await assert.rejects(workspace.inspectWorkspace(forged));
        const after = history.auditSnapshot();
        if (index === 0) {
            assert.equal(after.inspections, before.inspections + 1);
            assert.ok(after.resources.search > (before.resources.search || 0));
            assert.ok(after.resources.checking > (before.resources.checking || 0));
        } else {
            assert.equal(after.inspections, before.inspections);
            assert.equal(after.cachedInspections, before.cachedInspections + 1);
            assert.deepEqual(after.resources, before.resources);
        }
    }
});

test('immutable object and exact-content reuse stay historical and divergent imported evidence is rechecked', async () => {
    const value = await completed();
    const first = await workspace.inspectWorkspace(value);
    assert.ok(graphFrozen(value));
    assert.ok(graphFrozen(first));
    const before = history.auditSnapshot();
    const second = await workspace.inspectWorkspace(value);
    assert.strictEqual(first, second);
    assert.deepEqual(history.auditSnapshot(), before);
    assert.throws(() => { first.discovery.campaigns[0].result.resources.search = 0; }, TypeError);
    assert.throws(() => { value.events[2].payload.result.resources.search = 0; }, TypeError);
    const imported = await workspace.parseWorkspace(contract.canonical(value));
    assert.notStrictEqual(imported, value);
    assert.equal(history.auditSnapshot().inspections, before.inspections);
    assert.equal(history.auditSnapshot().cachedInspections, before.cachedInspections + 1);
    assert.ok(graphFrozen(imported));
    const importedInspection = await workspace.inspectWorkspace(imported);
    assert.equal(importedInspection.discovery.campaigns[0].historicalEvidenceOnly, true);
    assert.deepEqual(imported.authority, []);
    const parsedAudit = history.auditSnapshot();
    await workspace.inspectWorkspace(imported);
    assert.deepEqual(history.auditSnapshot(), parsedAudit);
});

test('a shallow-frozen caller stays untouched while inspection and returned v2 frames are deeply frozen', async () => {
    const value = copy(await completed());
    Object.freeze(value);
    const inspection = await workspace.inspectWorkspace(value);
    assert.equal(Object.isFrozen(value.events), false, 'Inspection must not freeze caller-owned descendants.');
    assert.ok(graphFrozen(inspection));
    const reopened = await workspace.parseWorkspace(contract.canonical(value));
    assert.ok(graphFrozen(reopened));
});

test('mutable v2 inspection binds its first frame and never caches a later caller edit under it', async () => {
    const input = copy(await completed()), originalReason = input.events[0].payload.reason;
    const pending = workspace.inspectWorkspace(input);
    input.events[0].payload.reason = 'Changed while the old digest was suspended';
    const first = await pending;
    assert.equal(first.versions[0].reason, originalReason);
    assert.ok(graphFrozen(first));
    assert.equal(Object.isFrozen(input), false);
    await assert.rejects(workspace.inspectWorkspace(copy(input)), /binding mismatch/);
    await assert.rejects(workspace.inspectWorkspace(input), /binding mismatch/);
    input.events[0].payload.reason = originalReason;
    assert.strictEqual(await workspace.inspectWorkspace(input), first);
});

test('a valid changed caller fingerprint misses its old cache and then warms its new frame', async () => {
    const input = copy(await completed()), first = await workspace.inspectWorkspace(input);
    assert.strictEqual(await workspace.inspectWorkspace(input), first);
    const next = await workspace.addSuccessor(input, {...workspace.DEFAULT_BRIEF, title: 'Next proposal'}, null, 'Changed');
    Object.assign(input, copy(next));
    const second = await workspace.inspectWorkspace(input);
    assert.notStrictEqual(second, first);
    assert.equal(second.versions.length, 2);
    assert.strictEqual(await workspace.inspectWorkspace(input), second);
    assert.ok(graphFrozen(second));
});

test('Discovery event append adopts the checked owned prefix and returns a frozen v2 frame', async () => {
    const input = await workspace.createWorkspace(), original = copy(input);
    const start = await history.startPayload(input, runtime.DEFAULT_CHARTER, sources);
    const pending = workspace.recordDiscoveryEvent(input, 'lab-started', start);
    input.events[0].payload.reason = 'Caller changed the checked prefix';
    const next = await pending;
    assert.deepEqual(next.events.slice(0, original.events.length), original.events);
    assert.ok(graphFrozen(next));
    const inspection = await workspace.inspectWorkspace(next);
    assert.strictEqual(await workspace.inspectWorkspace(next), inspection);
    const reopened = await workspace.parseWorkspace(contract.canonical(next));
    assert.ok(graphFrozen(reopened));
    assert.equal((await workspace.inspectWorkspace(reopened)).discovery.active.attempt, start.attempt);
});

test('all eleven campaigns admitted by the event limit retain checked content without implicit replay thrashing', async () => {
    let value = await workspace.createWorkspace();
    for (let horizon = 1; horizon <= 11; horizon++) {
        assert.equal(history.historyCapacity(value).canRun, true);
        const charter = {...copy(runtime.DEFAULT_CHARTER), intendedUses: horizon};
        const start = await history.startPayload(value, charter, sources);
        value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
        const result = runtime.runCampaign(charter);
        assert.equal(result.state, 'accepted');
        const verification = history.verifyForRecording(charter, result);
        const before = history.auditSnapshot();
        value = await workspace.recordDiscoveryEvent(value, 'lab-completed',
            await history.completedPayload(start.attempt, result, 1, verification.verificationResources));
        const after = history.auditSnapshot();
        assert.equal(after.inspections, before.inspections,
            `Campaign ${horizon} must not redo a phase already explicitly verified for recording.`);
        assert.ok(after.cacheBytesPeak <= 8_000_000);
    }
    assert.equal(value.events.length, 23);
    assert.equal((await workspace.inspectWorkspace(value)).discovery.campaigns.length, 11);
    assert.equal(history.historyCapacity(value).canRun, false);
});

test('an elapsed-time overrun preserves finite evidence but cannot become an accepted successor parent', async () => {
    const value = await completed(120_001);
    const record = (await workspace.inspectWorkspace(value)).discovery.campaigns[0];
    assert.equal(record.result.state, 'accepted');
    assert.equal(record.state, 'inconclusive');
    assert.match(record.wrapperOutcome, /time cap exceeded/i);
    assert.match(record.elapsedReceipt.scope, /self-reported/i);
    const charter = {...copy(runtime.DEFAULT_CHARTER), controls: 4, memory: 16, operations: ['flip-z', 'flip-w']};
    const start = await history.startPayload(value, charter, sources, record.resultDigest);
    await assert.rejects(workspace.recordDiscoveryEvent(value, 'lab-started', start), /Accepted parent is absent/);
});

function restorationHarness(pauseAt) {
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    const old = {missionId: 'older-saved-workspace', revision: 0, events: []};
    let fills = 0;
    const context = vm.createContext({
        ready: true, current: null, pending: null, storedRevision: null, inspected: null,
        dirty: true, successorEditing: false, busy: false,
        draft: {brief: {title: 'Initial draft'}, witnessEnabled: false, experimentText: '{}', successorReason: ''},
        capability: {DEFAULT_BRIEF: {title: 'Initial draft'}}, defaultExperimentText: () => '{}',
        canonical: value => JSON.stringify(value), rawDraft: () => context.draft,
        store: {get: () => pauseAt === 'get' ? gate : Promise.resolve({})},
        localStorage: {getItem: () => old.missionId},
        inspectStored: async () => {
            if (pauseAt === 'inspection') await gate;
            return {workspace: old, inspection: {latest: {brief: {}, experiment: null}, discovery: {attempts: []}}, revision: 0};
        },
        fillBrief: () => { fills++; }, renderVersions: () => {}, render: () => {},
        discoveryLab: {}, discoveryHistory: {historyCapacity: () => ({canRun: true}), auditSnapshot: () => ({})},
        mountDiscoveryLab: () => ({refresh() {}}), document: {getElementById() {}}, crypto: globalThis.crypto, performance,
    });
    vm.runInContext(readFileSync(new URL('../../scripts/templates/successor-capability/discovery-lab-bridge.js', import.meta.url), 'utf8'), context);
    return {context, release, fills: () => fills};
}

test('delayed restore cannot replace a newly opened workspace at either asynchronous boundary', async () => {
    for (const pauseAt of ['get', 'inspection']) {
        const harness = restorationHarness(pauseAt);
        const pending = vm.runInContext('discoveryBridge.state()', harness.context);
        await Promise.resolve(); await Promise.resolve();
        harness.context.current = {missionId: 'newly-opened-by-user', revision: 0, events: []};
        harness.release({});
        await pending;
        assert.equal(harness.context.current.missionId, 'newly-opened-by-user');
        assert.equal(harness.fills(), 0);
    }
});

test('delayed restore preserves newly edited unsaved proposal text', async () => {
    const harness = restorationHarness('inspection');
    const pending = vm.runInContext('discoveryBridge.state()', harness.context);
    await Promise.resolve(); await Promise.resolve();
    harness.context.draft = {brief: {title: 'Unsaved user edit'}, witnessEnabled: false, experimentText: '{}', successorReason: ''};
    harness.release({});
    await pending;
    assert.equal(harness.context.current, null);
    assert.equal(harness.context.draft.brief.title, 'Unsaved user edit');
    assert.equal(harness.fills(), 0);
});

test('an unsaved original proposal cannot be silently replaced by first lab construction', async () => {
    const harness = restorationHarness('get');
    harness.context.store = null;
    const initial = await vm.runInContext('discoveryBridge.state()', harness.context);
    assert.equal(initial.locked, false);
    harness.context.draft.brief.title = 'Unsaved original proposal';
    const changed = await vm.runInContext('discoveryBridge.state()', harness.context);
    assert.equal(changed.locked, true);
    assert.match(changed.reason, /unsaved edits/i);
    await assert.rejects(vm.runInContext('discoveryBridge.run({}, {})', harness.context), /unsaved edits/i);
    assert.equal(harness.context.current, null);
    assert.equal(harness.context.draft.brief.title, 'Unsaved original proposal');
});
