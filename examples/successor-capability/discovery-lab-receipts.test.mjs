// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as contract from './discovery-lab-contract.mjs';
import * as runtime from './discovery-lab.mjs';
import * as history from './discovery-lab-history.mjs';
import * as artifacts from './discovery-lab-artifacts.mjs';
import * as receipts from './discovery-lab-receipts.mjs';
async function campaign() {
    const charter = runtime.DEFAULT_CHARTER, result = runtime.runCampaign(charter);
    const bindings = {missionId: 'capability-' + crypto.randomUUID(), revision: 1,
        purposeDigest: await contract.payloadDigest({purpose: charter.purpose}),
        charterDigest: await contract.payloadDigest(charter),
        modelDigest: '1'.repeat(64), sourceDigest: '2'.repeat(64), evaluatorDigest: '3'.repeat(64)};
    return {attempt: 'lab-' + crypto.randomUUID(), campaignDigest: await contract.payloadDigest({bindings, result}),
        resultDigest: await contract.payloadDigest(result), state: result.state, lineageQualified: true,
        charter, result, bindings, artifacts: await artifacts.makeArtifacts(bindings, result), parent: null};
}
const vector = () => Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 0]));
const receiverSource = {repository: 'MontrealAI/AGIJobManager', commit: 'a'.repeat(40), tree: 'b'.repeat(40),
    adapterSha256: 'c'.repeat(64), contractSha256: 'd'.repeat(64)};
async function modeledReceipt(record, route = 'USDC', stage = 'evolve', branch = null) {
    // A transport fixture, explicitly not proof of native/source-authenticated execution.
    const limits = Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 100_000_000]));
    const request = await history.workRequest(record, route, limits);
    request.stage = stage; request.inputArtifacts = record.artifacts.slice(0, contract.STAGES.indexOf(stage)).map(item => item.digest);
    if (branch !== null) request.commission.branch = branch;
    const original = JSON.stringify(request);
    const native = vector(); native.checking = 10_000;
    for (let parent = record; parent; parent = parent.parent) {
        for (const key of ['acquisitions', 'search', 'checking', 'storageBytes', 'installations']) native[key] += parent.result.resources[key];
        native.memoryBytes = Math.max(native.memoryBytes, parent.result.resources.memoryWords * 8);
        native.workerCapacity = Math.max(native.workerCapacity, parent.result.resources.workerSlots);
    }
    const receiver = {...vector(), checking: 10_000, elapsedMs: 1};
    const reserved = {...receiver, memoryBytes: 1_000_000, storageBytes: 500_000};
    const source = {...receiverSource, repository: route === 'USDC' ? 'MontrealAI/AGIJobManager' : 'MontrealAI/AGIJobsv0'};
    const receipt = {schema: (route === 'USDC' ? 'agijobmanager' : 'agijobsv0') + '/discovery-lab-admission/v1',
        state: 'local-checked', original, requestSha256: await receipts.rawReceiptDigest(original), bindings: record.bindings,
        commission: request.commission, stage: request.stage, inputArtifacts: request.inputArtifacts,
        payloadDigest: request.payloadDigest, source: {adapterSha256: source.adapterSha256, contractSha256: source.contractSha256},
        checker: {report: {accepted: true, resourceUsed: native, reasons: []}, withinResourceEnvelope: true, nativeWithinResourceEnvelope: true},
        resources: {units: 'transport-fixture; not native execution evidence', receiverUsed: receiver, checkerUsed: native,
            totalUsed: vector(), receiverReservation: reserved,
            nativeLimits: Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, limits[key] - reserved[key]])), reservationAvailable: true},
        reason: null, lifecycle: {commission: 'DRAFT_NOT_SUBMITTED', reservedBaseUnits: '0', execution: 'unprovisioned',
            review: 'separate-review-required', settlement: 'not-connected'}, capabilityAcceptance: 'not-granted-by-import', authority: 'none'};
    const encode = () => JSON.stringify(receipt);
    for (let index = 0; index < 12; index++) {
        receiver.storageBytes = new TextEncoder().encode(encode()).length;
        receiver.memoryBytes = new TextEncoder().encode(original).length + receiver.storageBytes;
        for (const key of contract.RESOURCE_KEYS) receipt.resources.totalUsed[key] = receiver[key] + native[key];
    }
    return {raw: encode(), source};
}
test('pure receipt inspection binds replayed context while retaining unattested content identity', async () => {
    const record = await campaign(), wrapper = await modeledReceipt(record), context = receipts.makeReceiverContext(record);
    const checked = await receipts.inspectReceiverReceipt(wrapper, context, {expectedReceiverSources: [wrapper.source]});
    assert.equal(checked.state, 'local-checked'); assert.equal(checked.authority, 'none');
    assert.equal(checked.authenticity, 'not-attested');
    await assert.rejects(receipts.inspectReceiverReceipt(wrapper, {...context, bindings: {...context.bindings, sourceDigest: 'f'.repeat(64)}}), /campaign/);
    await assert.rejects(receipts.inspectReceiverReceipt(wrapper, context, {expectedReceiverSources: []}), /installed source/);
});
test('semantic identity survives receipt reframing while exact raw digest preserves original bytes', async () => {
    const record = await campaign(), wrapper = await modeledReceipt(record), context = receipts.makeReceiverContext(record);
    const first = await receipts.inspectReceiverReceipt(wrapper, context);
    const second = await receipts.inspectReceiverReceipt({...wrapper, raw: JSON.stringify(JSON.parse(wrapper.raw), null, 2)}, context);
    assert.equal(first.receiptId, second.receiptId); assert.notEqual(first.receiptDigest, second.receiptDigest);
    const learn = await receipts.inspectReceiverReceipt(await modeledReceipt(record, 'USDC', 'learn'), context);
    assert.notEqual(first.receiptId, learn.receiptId);
});
test('pure context and receipt frames are owned before digest suspension and getters never execute', async () => {
    const record = await campaign(), wrapper = await modeledReceipt(record), context = receipts.makeReceiverContext(record);
    const pending = receipts.inspectReceiverReceipt(wrapper, context);
    wrapper.source.adapterSha256 = 'f'.repeat(64); context.bindings.sourceDigest = 'f'.repeat(64);
    assert.equal((await pending).state, 'local-checked');
    let reads = 0;
    const trap = {...record}; Object.defineProperty(trap, 'charter', {enumerable: true, get() {reads++; return record.charter;}});
    assert.throws(() => receipts.makeReceiverContext(trap), /inert own data/); assert.equal(reads, 0);
    const rawTrap = {source: receiverSource}; Object.defineProperty(rawTrap, 'raw', {enumerable: true, get() {reads++; return '{}';}});
    await assert.rejects(receipts.inspectReceiverReceipt(rawTrap, receipts.makeReceiverContext(record)), /Accessor/);
    assert.equal(reads, 0);
});
test('pure context refuses cycles and imported authority rather than executing supplied bytes', async () => {
    const record = await campaign(); record.parent = record;
    assert.throws(() => receipts.makeReceiverContext(record), /cyclic/); record.parent = null;
    const wrapper = await modeledReceipt(record), altered = JSON.parse(wrapper.raw); altered.authority = 'settle';
    wrapper.raw = JSON.stringify(altered);
    await assert.rejects(receipts.inspectReceiverReceipt(wrapper, receipts.makeReceiverContext(record)));
});
