// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import * as workspace from './workspace.mjs';
import * as history from './discovery-lab-history.mjs';
import * as runtime from './discovery-lab.mjs';
import * as contract from './discovery-lab-contract.mjs';
import {createInspector} from './discovery-lab-inspector.mjs';

const oldSources = {modelDigest: '1'.repeat(64), sourceDigest: '2'.repeat(64), evaluatorDigest: '3'.repeat(64)};
const currentSources = {...oldSources, sourceDigest: '4'.repeat(64)};
const stronger = () => ({...structuredClone(runtime.DEFAULT_CHARTER), controls: 4, memory: 16,
    operations: ['flip-z', 'flip-w']});
const limits = {acquisitions: 10000, search: 10000000, checking: 10000000,
    memoryBytes: 10000000, storageBytes: 4000000, workerCapacity: 4, installations: 100, elapsedMs: 120000};

async function finish(value, start) {
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const active = (await workspace.inspectWorkspace(value)).discovery.active;
    const result = runtime.runCampaign(start.charter, {parent: active.parent?.result || null});
    const verification = history.verifyForRecording(start.charter, result, active.parent?.result || null);
    value = await workspace.recordDiscoveryEvent(value, 'lab-completed',
        await history.completedPayload(start.attempt, result, 1, verification.verificationResources));
    return {value, record: (await workspace.inspectWorkspace(value)).discovery.campaigns.at(-1)};
}
async function duplicateResults() {
    let value = await workspace.createWorkspace();
    for (const sources of [oldSources, currentSources]) {
        const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sources);
        value = (await finish(value, start)).value;
    }
    const records = (await workspace.inspectWorkspace(value)).discovery.campaigns;
    assert.equal(records[0].resultDigest, records[1].resultDigest);
    return {value, records};
}
function bridgeHarness(value, inspection) {
    const context = vm.createContext({
        ready: true, current: value, inspected: inspection, storedRevision: 0, pending: null,
        store: null, dirty: false, successorEditing: false, busy: false,
        DISCOVERY_SOURCES: currentSources, capability: workspace, discoveryLab: runtime,
        discoveryHistory: {...history, workRequest: (record, route, envelope) =>
            history.workRequest(record, route, JSON.parse(JSON.stringify(envelope)))},
        canonical: contract.canonical, rawDraft: () => ({}), defaultExperimentText: () => '{}',
        clearError() {}, controls() {}, render() {}, fillBrief() {}, renderVersions() {},
        localStorage: {setItem() {}}, $: () => ({checked: true}), performance,
        mountDiscoveryLab: () => ({refresh() {}}),
        persist: async next => {
            context.current = next;
            context.inspected = await workspace.inspectWorkspace(next);
            context.storedRevision++;
        },
    });
    vm.runInContext(readFileSync(new URL('../../scripts/templates/successor-capability/discovery-lab-bridge.js', import.meta.url), 'utf8'), context);
    return context;
}

test('identical numeric results keep distinct source-bound completion identities and exact selection', async () => {
    const {value, records} = await duplicateResults();
    assert.notEqual(records[0].campaignDigest, records[1].campaignDigest);
    assert.equal(records[0].campaignDigest, value.events[2].digest);
    assert.equal(records[1].campaignDigest, value.events[4].digest);
    assert.strictEqual(history.selectCampaign(records, records[1]), records[1]);
    const staleSelection = {...records[1], bindings: records[0].bindings};
    assert.throws(() => history.selectCampaign(records, staleSelection), /absent or changed/);
    await assert.rejects(history.startPayload(value, stronger(), currentSources, records[1].resultDigest),
        /Ambiguous result digest/);
    const start = await history.startPayload(value, stronger(), currentSources, records[1].campaignDigest);
    const started = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const active = (await workspace.inspectWorkspace(started)).discovery.active;
    assert.equal(active.parent.attempt, records[1].attempt);
    assert.deepEqual(active.parent.bindings, records[1].bindings);
});

test('actual bridge source guard and exported commission select the chosen duplicate-result attempt', async () => {
    const {value, records} = await duplicateResults();
    const context = bridgeHarness(value, await workspace.inspectWorkspace(value));
    context.selected = records[1];
    const request = await vm.runInContext("discoveryBridge.workRequest(selected, 'USDC')", context);
    assert.equal(request.commission.id, records[1].attempt);
    assert.deepEqual(Object.fromEntries(contract.BINDING_KEYS.map(key => [key, request[key]])), records[1].bindings);
    assert.deepEqual(request.inputArtifacts, records[1].artifacts.slice(0, 5).map(item => item.digest));
    context.selected = records[0];
    await assert.rejects(vm.runInContext("discoveryBridge.workRequest(selected, 'USDC')", context),
        /currently installed/);
    context.charter = stronger();
    await assert.rejects(vm.runInContext('discoveryBridge.run(charter, {parent: selected})', context),
        /not currently qualified/);
    assert.equal(context.current.events.length, value.events.length);
    context.selected = records[1];
    const child = await vm.runInContext('discoveryBridge.run(charter, {parent: selected})', context);
    assert.equal(child.parent.attempt, records[1].attempt);
    assert.equal(child.parent.campaignDigest, records[1].campaignDigest);
    assert.equal(context.current.events.at(-2).payload.parentDigest, records[1].campaignDigest);
    context.selected = child;
    const exported = await vm.runInContext("discoveryBridge.workRequest(selected, 'USDC')", context);
    assert.equal(exported.sourceDigest, currentSources.sourceDigest);
    assert.equal(exported.commission.id, child.attempt);
    assert.equal(exported.payload.ancestors.length, 1);
    assert.deepEqual(exported.payload.ancestors[0].result, records[1].result);
    assert.equal(exported.payload.result.lineage.generation, 2);
    assert.equal((await createInspector(currentSources)(exported.payload, {request: exported,
        limits: exported.resourceLimits})).accepted, true);
});

test('legacy v2 duplicate-result ancestry remains byte-identical and readable but cannot authorize new reuse', async () => {
    const {value, records} = await duplicateResults();
    const start = await history.startPayload(value, stronger(), currentSources, records[1].campaignDigest);
    const legacy = await finish(value, {...start, parentDigest: records[0].resultDigest});
    const original = contract.canonical(legacy.value);
    const reopened = await workspace.parseWorkspace(original);
    assert.equal(contract.canonical(reopened), original);
    const record = (await workspace.inspectWorkspace(reopened)).discovery.campaigns.at(-1);
    assert.equal(record.result.state, 'accepted');
    assert.equal(record.parent.attempt, records[0].attempt);
    assert.equal(record.lineageQualified, false);
    assert.ok(record.lineageIssues.includes('AMBIGUOUS_LEGACY_PARENT'));
    assert.ok(record.lineageIssues.includes('PARENT_SOURCE_MISMATCH'));
    assert.throws(() => history.selectCampaign([record], record), /unresolved parent lineage/);
    await assert.rejects(history.workRequest(record, 'USDC', limits), /resource-qualified campaign/);
    const next = await history.startPayload(reopened, stronger(), currentSources, record.campaignDigest);
    await assert.rejects(workspace.recordDiscoveryEvent(reopened, 'lab-started', next), /current source lineage/);
});

test('unique legacy result references normalize without rewriting old records and stale explicit parents fail closed', async () => {
    let value = await workspace.createWorkspace();
    const first = await finish(value, await history.startPayload(value, runtime.DEFAULT_CHARTER, oldSources));
    value = first.value;
    const before = contract.canonical(value);
    const start = await history.startPayload(value, stronger(), oldSources, first.record.resultDigest);
    assert.equal(start.parentDigest, first.record.campaignDigest);
    assert.equal(contract.canonical(value), before);
    const compatible = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    assert.equal((await workspace.inspectWorkspace(compatible)).discovery.active.parent.attempt, first.record.attempt);
    const stale = await history.startPayload(value, stronger(), currentSources, first.record.campaignDigest);
    await assert.rejects(workspace.recordDiscoveryEvent(value, 'lab-started', stale), /current source lineage/);
});
