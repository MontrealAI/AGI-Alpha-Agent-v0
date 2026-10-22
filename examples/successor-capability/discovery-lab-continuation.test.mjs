// SPDX-License-Identifier: Apache-2.0
// UI command-boundary regression fixtures; no browser or external-runtime acceptance claim.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as workspace from './workspace.mjs';
import * as history from './discovery-lab-history.mjs';
import * as evidence from './discovery-lab-evidence-history.mjs';
import * as future from './discovery-lab-future.mjs';
import * as runtime from './discovery-lab.mjs';
import * as contract from './discovery-lab-contract.mjs';
const sources = {modelDigest: '1'.repeat(64), sourceDigest: '2'.repeat(64), evaluatorDigest: '3'.repeat(64)};
async function fixture() {
    let value = await workspace.createWorkspace();
    const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sources);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const result = runtime.runCampaign(start.charter), check = runtime.verifyCampaign(start.charter, result);
    value = await workspace.recordDiscoveryEvent(value, 'lab-completed',
        await history.completedPayload(start.attempt, result, 1, check.verificationResources));
    const campaign = (await workspace.inspectWorkspace(value)).discovery.campaigns[0];
    const capsule = await evidence.freezeRecord(campaign), bank = await future.publicFutureBank(capsule, 8);
    for (const [kind, record] of [['future-freeze', evidence.freezeReference(capsule)], ['future-task-bank', bank]]) {
        value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
            await evidence.evidencePayload(campaign.campaignDigest, kind, record));
    }
    return value;
}
async function mount(value, {failCompletion = false, delayedRestore = false} = {}) {
    const nodes = new Map(), exports = [], handlers = new Map(), stateListeners = new Set();
    function element(id = '') {
        const node = {id, value: id === 'lab-future-budget' ? '50' : id === 'lab-future-seed' ? '8' : 'USDC',
            hidden: false, disabled: false, textContent: '', listeners: new Map(),
            addEventListener(kind, callback) { this.listeners.set(kind, callback); },
            after(...added) { for (const item of added) nodes.set(item.id, item); }};
        return node;
    }
    const get = id => { if (!nodes.has(id)) nodes.set(id, element(id)); return nodes.get(id); };
    let invocations = 0;
    const context = vm.createContext({console, crypto, ready: true, current: delayedRestore ? null : value,
        storedRevision: delayedRestore ? null : 0,
        inspected: delayedRestore ? null : await workspace.inspectWorkspace(value), busy: false, pending: null, dirty: false, successorEditing: false,
        document: {getElementById: get, createElement: () => element()},
        window: {addEventListener: (kind, callback) => handlers.set(kind, callback)},
        discoveryHistory: history, discoveryEvidence: {...evidence, evidencePayload(campaignDigest, kind, record) {
            return evidence.evidencePayload(campaignDigest, kind, JSON.parse(JSON.stringify(record)));
        }}, discoveryContract: contract,
        discoveryFuture: {...future, async evaluateFutureTasks(capsule, bank, options) {
            invocations++; return future.evaluateFutureTasks(capsule, bank, JSON.parse(JSON.stringify(options)));
        }},
        discoveryDeployments: {async loadDeploymentInventory() { return {}; }, deploymentSummary() { return {operationallyReady: false}; }},
        DEPLOYMENT_INVENTORY: {}, DISCOVERY_SOURCES: sources, discoveryBridge: {subscribe(callback) { stateListeners.add(callback); }, async state() {
            await Promise.resolve();
            if (delayedRestore) {
                context.current = value; context.inspected = await workspace.inspectWorkspace(value); context.storedRevision = 0;
                for (const listener of stateListeners) listener();
            }
            return {};
        }},
        canonical: contract.canonical, render() {}, download: (text, filename) => exports.push({text, filename}),
        capability: {...workspace, async recordDiscoveryEvent(base, kind, payload) {
            if (failCompletion && payload.kind === 'future-evaluation') throw Error('Unexpected history append failure');
            return workspace.recordDiscoveryEvent(base, kind, payload);
        }},
        async persist(next, revision, base) {
            assert.equal(context.current, base); assert.equal(context.storedRevision, revision);
            context.current = next; context.inspected = await workspace.inspectWorkspace(next); context.storedRevision++;
        }});
    vm.runInContext(readFileSync(new URL('../../scripts/templates/successor-capability/discovery-lab-continuation.js', import.meta.url), 'utf8'), context);
    await Promise.resolve();
    return {context, get, exports, handlers, invocations: () => invocations,
        async click(id) {
            get(id).listeners.get('click')();
            const end = performance.now() + 10000;
            while (context.busy) {
                if (performance.now() > end) throw Error('UI fixture failed to settle.');
                await new Promise(resolve => setTimeout(resolve, 5));
            }
        }};
}
test('a valid23-event mission cannot launch a future run without terminal event capacity', async () => {
    let value = await fixture();
    for (let index = 0; index < 9; index++) {
        const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sources);
        value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
        value = await workspace.recordDiscoveryEvent(value, 'lab-stopped', history.stoppedPayload(start.attempt, 'Retained interrupted fixture'));
    }
    assert.equal(value.events.length, 23);
    const before = contract.canonical(value), ui = await mount(value);
    assert.equal(ui.get('lab-run-future').disabled, true);
    await ui.click('lab-run-future');
    assert.equal(ui.invocations(), 0);
    assert.equal(contract.canonical(ui.context.current), before);
    assert.match(ui.get('lab-future-status').textContent, /reserve|capacity/i);
});
test('unexpected completion append failure retains exact computed evidence and unknown reservation recovery', async () => {
    const ui = await mount(await fixture(), {failCompletion: true});
    await ui.click('lab-run-future');
    assert.equal(ui.invocations(), 1);
    const attachments = ui.context.inspected.discovery.attachments;
    assert.equal(attachments.at(-1).kind, 'future-run-stopped');
    assert.equal(attachments.at(-1).record.spent, 'unknown-reservation-retained');
    assert.equal(ui.get('lab-future-recovery-export').hidden, false);
    assert.equal(ui.get('lab-run-future').disabled, true);
    let prevented = false;
    ui.handlers.get('beforeunload')({preventDefault() { prevented = true; }});
    assert.equal(prevented, true);
    await ui.click('lab-future-recovery-export');
    const saved = JSON.parse(ui.exports[0].text);
    assert.equal(saved.schema, 'discovery-lab-future-result-recovery/v1');
    assert.equal(saved.result.runs.length, 42);
    const freeze = attachments.find(item => item.kind === 'future-freeze');
    assert.equal((await future.verifyFutureEvaluation(freeze.capsule, saved.taskBank, saved.result)).verified, true);
    assert.equal(ui.get('lab-future-recovery-confirm').disabled, false);
});
test('a valid22-event mission reserves exactly two terminal slots and saves the complete comparison', async () => {
    let value = await fixture();
    for (let index = 0; index < 8; index++) {
        const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sources);
        value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
        value = await workspace.recordDiscoveryEvent(value, 'lab-stopped', history.stoppedPayload(start.attempt, 'Retained prior interruption'));
    }
    value = await workspace.addSuccessor(value, {...workspace.DEFAULT_BRIEF, title: 'Capacity boundary continuation'}, null,
        'Preserve the prior lab while recording a new explicit proposal.');
    assert.equal(value.events.length, 22);
    const ui = await mount(value);
    assert.equal(ui.get('lab-run-future').disabled, false);
    await ui.click('lab-run-future');
    assert.equal(ui.invocations(), 1);
    assert.equal(ui.context.current.events.length, 24);
    assert.equal(ui.context.inspected.discovery.attachments.at(-1).kind, 'future-evaluation');
    assert.equal(ui.get('lab-future-recovery-export').hidden, true);
});
test('saved mission restored after render refreshes continuation controls without restarting work', async () => {
    const ui = await mount(await fixture(), {delayedRestore: true});
    assert.equal(ui.get('lab-run-future').disabled, true);
    await ui.context.discoveryBridge.state();
    assert.equal(ui.get('lab-run-future').disabled, false);
    assert.equal(ui.invocations(), 0);
});
