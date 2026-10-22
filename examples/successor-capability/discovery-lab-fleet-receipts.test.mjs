// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as contract from './discovery-lab-contract.mjs';
import * as runtime from './discovery-lab.mjs';
import * as history from './discovery-lab-history.mjs';
import * as workspace from './workspace.mjs';
import * as evidence from './discovery-lab-evidence-history.mjs';
import * as docket from './discovery-lab-docket.mjs';
import * as receipts from './discovery-lab-receipts.mjs';
const source = {repository: 'MontrealAI/AGI-Fleet-Linux', commit: 'a'.repeat(40), tree: 'b'.repeat(40),
    adapterSha256: 'c'.repeat(64), contractSha256: 'd'.repeat(64)};
const sources = {modelDigest: '1'.repeat(64), sourceDigest: '2'.repeat(64), evaluatorDigest: '3'.repeat(64)};
const copy = value => JSON.parse(contract.canonical(value));
const bytes = value => new TextEncoder().encode(value).length;
const zero = () => Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 0]));
async function initial(input = null, charter = runtime.DEFAULT_CHARTER, parentDigest = null) {
    let value = input || await workspace.createWorkspace();
    const start = await history.startPayload(value, charter, sources, parentDigest);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const active = (await workspace.inspectWorkspace(value)).discovery.active;
    const result = runtime.runCampaign(charter, {parent: active.parent?.result || null});
    const checked = runtime.verifyCampaign(charter, result, {parent: active.parent?.result || null});
    value = await workspace.recordDiscoveryEvent(value, 'lab-completed',
        await history.completedPayload(start.attempt, result, 1, checked.verificationResources));
    return {value, record: (await workspace.inspectWorkspace(value)).discovery.campaigns.at(-1)};
}
const append = (value, campaign, wrapper) => evidence.evidencePayload(campaign.campaignDigest, 'receiver-receipt', wrapper)
    .then(payload => workspace.recordDiscoveryEvent(value, 'lab-evidence-attached', payload));
function encode(envelope, receipt, nativeStorage) {
    // Actual Fleet finalize() charges canonical receipt bytes, independently of wire formatting.
    for (let index = 0; index < 12; index++) receipt.resourceUsed.storageBytes = nativeStorage + bytes(contract.canonical(receipt));
    envelope.receiptRaw = JSON.stringify(receipt);
    return {raw: JSON.stringify(envelope), source: {...source}};
}
async function modeled(record, {route = 'USDC', stage = 'evolve', prefix = 'full', branch = null} = {}) {
    // Structural transport fixture, never presented as native or installed execution proof.
    const limits = Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 100_000_000]));
    const request = await history.workRequest(record, route, limits);
    request.stage = stage; request.inputArtifacts = record.artifacts.slice(0, contract.STAGES.indexOf(stage)).map(item => item.digest);
    if (branch !== null) request.commission.branch = branch;
    const original = JSON.stringify(request), native = zero();
    if (prefix !== 'none') native.checking = 10_000;
    if (prefix === 'full') for (let parent = record; parent; parent = parent.parent) {
        for (const key of ['acquisitions', 'search', 'checking', 'storageBytes', 'installations']) native[key] += parent.result.resources[key];
        native.memoryBytes = Math.max(native.memoryBytes, parent.result.resources.memoryWords * 8);
        native.workerCapacity = Math.max(native.workerCapacity, parent.result.resources.workerSlots);
    }
    const receipt = {schema: 'agi-fleet/discovery-review/v1',
        state: prefix === 'full' ? 'accepted-local-review' : prefix === 'none' ? 'unprovisioned' : 'inconclusive',
        reasons: prefix === 'full' ? [] : prefix === 'none' ? ['DISCOVERY_EXECUTOR_UNPROVISIONED'] : ['CONSERVATIVE_REPLAY_CHECK_INCOMPLETE'],
        missionId: request.missionId, revision: request.revision, stage, requestDigest: await receipts.rawReceiptDigest(original),
        payloadDigest: request.payloadDigest, sourceDigest: request.sourceDigest, evaluatorDigest: request.evaluatorDigest,
        commission: request.commission, executorId: prefix === 'none' ? null : 'fixture-local-review',
        runtimeDigest: prefix === 'none' ? null : 'e'.repeat(64), executionMode: 'synthetic-local',
        scope: 'bounded-synthetic-semantic-review',
        resourceUsed: {...native, checking: native.checking + 1, memoryBytes: bytes(original) + native.memoryBytes + 1000, elapsedMs: 1},
        resourceAccounting: prefix === 'none' ? 'admission-only-known-input-and-receipt-bytes' : 'reported-model-work-plus-input-and-receipt-bytes',
        authority: 'none', remoteExecution: 'unprovisioned', settlement: 'not-connected', organizationalIndependence: false, protectedHoldout: false};
    return encode({schema: 'agi-fleet/discovery-review-return/v1', original, receiptRaw: ''}, receipt, native.storageBytes);
}
function edited(wrapper, edit) {
    const envelope = JSON.parse(wrapper.raw), receipt = JSON.parse(envelope.receiptRaw);
    const nativeStorage = receipt.resourceUsed.storageBytes - bytes(contract.canonical(receipt));
    edit(receipt, envelope); return encode(envelope, receipt, nativeStorage);
}
test('Fleet structural return binds exact typed request and retains distinct native receipt bytes', async () => {
    const {record} = await initial(), wrapper = await modeled(record), context = receipts.makeReceiverContext(record);
    const checked = await receipts.inspectReceiverReceipt(wrapper, context, {expectedReceiverSources: [source]});
    assert.equal(checked.inspectionKind, 'fleet-local-review'); assert.equal(checked.state, 'accepted-local-review');
    assert.equal(checked.authority, 'none'); assert.equal(checked.authenticity, 'not-attested');
    assert.deepEqual(await receipts.receiptRequestBindings(wrapper), record.bindings);
    assert.equal(checked.nativeReceiptDigest, await receipts.rawReceiptDigest(JSON.parse(wrapper.raw).receiptRaw));
    assert.notEqual(checked.nativeReceiptDigest, checked.receiptDigest);
    await assert.rejects(receipts.inspectReceiverReceipt(wrapper, context, {expectedReceiverSources: []}), /installed source/);
    await assert.rejects(receipts.inspectReceiverReceipt({...wrapper, source: {...source, repository: 'MontrealAI/AGIJobManager'}}, context), /source identity/);
    await assert.rejects(receipts.inspectReceiverReceipt(wrapper, {...context, bindings: {...context.bindings, revision: 9}}), /qualified campaign/);
});
test('Fleet semantic identity survives receipt/request framing, elapsed/memory and free runtime declarations', async () => {
    const {record} = await initial(), wrapper = await modeled(record), context = receipts.makeReceiverContext(record);
    const original = await receipts.inspectReceiverReceipt(wrapper, context);
    const variants = [
        edited(wrapper, receipt => {receipt.executorId = 'another-declared-executor';}),
        edited(wrapper, receipt => {receipt.runtimeDigest = 'f'.repeat(64);}),
        edited(wrapper, receipt => {receipt.resourceUsed.elapsedMs += 9;}),
        edited(wrapper, receipt => {receipt.resourceUsed.memoryBytes += 91;}),
        edited(wrapper, receipt => {receipt.state = 'inconclusive'; receipt.reasons = ['ELAPSED_REPLAY_CHECK_INCOMPLETE'];})
    ];
    const envelope = JSON.parse(wrapper.raw); envelope.receiptRaw = JSON.stringify(JSON.parse(envelope.receiptRaw), null, 2);
    variants.push({raw: JSON.stringify(envelope, null, 2), source});
    const reframe = JSON.parse(wrapper.raw), native = JSON.parse(reframe.receiptRaw);
    reframe.original = JSON.stringify(Object.fromEntries(Object.entries(JSON.parse(reframe.original)).reverse()), null, 2);
    native.requestDigest = await receipts.rawReceiptDigest(reframe.original);
    native.resourceUsed.memoryBytes += bytes(reframe.original);
    variants.push(encode(reframe, native, native.resourceUsed.storageBytes - bytes(contract.canonical(JSON.parse(envelope.receiptRaw)))));
    for (const variant of variants) {
        const checked = await receipts.inspectReceiverReceipt(variant, context);
        assert.equal(checked.receiptId, original.receiptId); assert.notEqual(checked.receiptDigest, original.receiptDigest);
    }
});
test('Fleet omitted work, swapped request, forged state/authority and malformed envelope are refused', async () => {
    const {record} = await initial(), wrapper = await modeled(record), context = receipts.makeReceiverContext(record);
    const changes = [
        receipt => {receipt.resourceUsed.checking--;},
        receipt => {receipt.resourceUsed.acquisitions++;},
        receipt => {receipt.requestDigest = '0'.repeat(64);},
        receipt => {receipt.commission.currency = 'AGIALPHA18';},
        receipt => {receipt.organizationalIndependence = true;},
        receipt => {receipt.remoteExecution = 'executed';},
        receipt => {receipt.authority = 'promote';},
        receipt => {receipt.state = 'rejected-local-review'; receipt.reasons = ['CURRENT_STAGE_REJECTED'];},
        receipt => {receipt.protectedHoldout = true;}
    ];
    for (const change of changes) await assert.rejects(receipts.inspectReceiverReceipt(edited(wrapper, change), context));
    const another = await initial(), swapped = JSON.parse(wrapper.raw);
    swapped.original = JSON.stringify(await history.workRequest(another.record, 'USDC', Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 100000000]))));
    await assert.rejects(receipts.inspectReceiverReceipt({raw: JSON.stringify(swapped), source}, context), /qualified campaign/);
    await assert.rejects(receipts.inspectReceiverReceipt({raw: JSON.stringify({...JSON.parse(wrapper.raw), extra: true}), source}, context), /envelope/);
});
test('Fleet admission failure and interrupted prefixes retain distinct costs and cannot forge completion', async () => {
    const {record} = await initial(), context = receipts.makeReceiverContext(record);
    const wrappers = await Promise.all(['none', 'inspection', 'full'].map(prefix => modeled(record, {prefix})));
    const checked = await Promise.all(wrappers.map(wrapper => receipts.inspectReceiverReceipt(wrapper, context)));
    assert.equal(new Set(checked.map(item => item.receiptId)).size, 3);
    assert.deepEqual(checked.map(item => item.resources.checking), [1, 10001, record.result.resources.checking + 10001]);
    await assert.rejects(receipts.inspectReceiverReceipt(edited(wrappers[1], receipt => {
        receipt.state = 'accepted-local-review'; receipt.reasons = [];
    }), context), /complete finite acceptance/);
    await assert.rejects(receipts.inspectReceiverReceipt(edited(wrappers[0], receipt => {
        receipt.state = 'inconclusive'; receipt.reasons = ['ELAPSED_REPLAY_CHECK_INCOMPLETE'];
        receipt.resourceAccounting = 'reported-model-work-plus-input-and-receipt-bytes';
    }), context), /inspection charge/);
    const overrun = edited(wrappers[0], receipt => {receipt.resourceUsed.elapsedMs = 100000001;});
    await assert.rejects(receipts.inspectReceiverReceipt(overrun, context), /over-budget/);
    const retained = edited(overrun, receipt => {
        receipt.state = 'inconclusive'; receipt.reasons = ['DISCOVERY_REVIEW_BUDGET_EXHAUSTED'];
    });
    assert.equal((await receipts.inspectReceiverReceipt(retained, context)).state, 'inconclusive');
});
test('Fleet shares the mission chain, disjoint costs and byte-identical docket after reopen', async () => {
    let {value, record} = await initial(); const wrapper = await modeled(record);
    value = await append(value, record, wrapper);
    const frozen = contract.canonical(value), first = await docket.createDiscoveryDocket(value);
    const reopened = await workspace.parseWorkspace(frozen), second = await docket.createDiscoveryDocket(reopened);
    assert.equal(contract.canonical(first), contract.canonical(second));
    const costs = JSON.parse(first.files['08_cost_ledgers/costs.json']);
    assert.deepEqual(costs.commissions, []); assert.deepEqual(costs.receiverInspectionByRoute, {});
    assert.equal(costs.fleetLocalReviewObservations.checking, record.result.resources.checking + 10001);
    assert.equal(costs.totalComplete, false);
    const raw = JSON.parse(first.files['05_agialpha_runs/run.json']);
    assert.equal(raw.workspace.events.at(-1).payload.record.raw, wrapper.raw);
    await assert.rejects(append(value, record, edited(wrapper, receipt => {receipt.executorId = 'other-declaration';})), /Duplicate semantic/);
    const attached = await docket.emptyDocketAttachments(value); attached.receipts.push(wrapper);
    await assert.rejects(docket.createDiscoveryDocket(value, attached), /repeats a semantic receipt/);
    assert.equal(contract.canonical(value), frozen);
});
test('Fleet captures inert input/context before awaits and rejects accessors without invoking them', async () => {
    const {record} = await initial(), wrapper = await modeled(record), context = receipts.makeReceiverContext(record);
    const mutable = copy(wrapper), expected = await receipts.inspectReceiverReceipt(wrapper, context);
    const pending = receipts.inspectReceiverReceipt(mutable, context); mutable.raw = '{}';
    assert.deepEqual(await pending, expected);
    let calls = 0; const hostile = {...wrapper};
    Object.defineProperty(hostile, 'raw', {enumerable: true, get() {calls++; return wrapper.raw;}});
    await assert.rejects(receipts.inspectReceiverReceipt(hostile, context), /Accessor/); assert.equal(calls, 0);
    await assert.rejects(receipts.inspectReceiverReceipt({...wrapper, source: Object.create(source)}, context), /Unsupported JSON/);
});
test('Fleet preserves the original typed work reference without creating a commission or new route', async () => {
    let {value, record} = await initial(); const first = await modeled(record);
    value = await append(value, record, first);
    const original = await docket.exportDiscoveryDocket(value), conflicting = await modeled(record, {branch: 'contradictory-original-branch'});
    await assert.rejects(append(value, record, conflicting), /Contradictory original work reference/);
    const outside = await docket.emptyDocketAttachments(value); outside.receipts = [conflicting];
    await assert.rejects(docket.createDiscoveryDocket(value, outside), /Contradictory original work reference/);
    assert.equal(await docket.exportDiscoveryDocket(value), original);
    const costs = JSON.parse(JSON.parse(original).files['08_cost_ledgers/costs.json']);
    assert.deepEqual(costs.commissions, []); assert.deepEqual(costs.receiverInspectionByRoute, {});
    assert.equal(costs.currenciesCombined, false); assert.equal(value.authority.length, 0);
});
