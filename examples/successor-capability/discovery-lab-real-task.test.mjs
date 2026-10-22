// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as adapter from './discovery-lab-real-task.mjs';
const request = JSON.parse(fs.readFileSync(new URL('./fixtures/discovery-lab-request.json', import.meta.url)));
const h = value => value.repeat(64);
const resources = {acquisitions:100, search:100, checking:100, memoryBytes:1_000_000, storageBytes:1_000_000,
    workerCapacity:1, installations:1, elapsedMs:1000};
const context = {workspaceHead:h('a'), missionId:request.missionId, campaignDigest:h('b'),
    adapterSources:{adapterSourceDigest:h('c'), checkerSourceDigest:h('d')}};
async function planned() {
    return adapter.createRealTaskRecord({...context, workRequest:request, publicSource:'https://example.org/public/numerical-spec',
        specification:{multiplier:'3', offset:'-1', maxBatchRows:16}, resourceLimits:resources});
}
async function frozen() {
    return adapter.freezeRealTaskArtifact(await planned(), {moduleUtf8:'export const transform = values => values.map(x => String(BigInt(x)*3n-1n));',
        environmentDigest:h('e'), trace:[]});
}
async function bank() { return adapter.commitRealTaskBank(await frozen(), [{id:'next-1', inputs:['2','2','-3']}, {id:'next-2', inputs:['0','5']}]); }
function observed(record, taskId, outputs, resourceUsed = {...resources, checking:0, elapsedMs:1, acquisitions:0, search:0, memoryBytes:0, storageBytes:0, installations:0, workerCapacity:0}) {
    return {taskId, artifactFreezeDigest:record.artifact.freezeDigest, outputs, trace:[], resourceUsed};
}
test('proposal reuses typed request and mission source bindings but remains NOT_RUN', async () => {
    const record = await planned();
    assert.equal(record.operationalState, 'NOT_RUN'); assert.equal(record.authority, 'none');
    assert.deepEqual(record.bindings, Object.fromEntries(Object.keys(record.bindings).map(key => [key, request[key]])));
    assert.equal((await adapter.validateRealTaskRecord(record, context)).workspaceHead, context.workspaceHead);
    await assert.rejects(adapter.validateRealTaskRecord(record, {...context, workspaceHead:h('f')}), /head changed/);
});
test('producer packet has no future tasks, expected outputs or imported executable selection', async () => {
    const record = await bank(), packet = await adapter.realTaskProducerPacket(record);
    assert.equal(packet.expectedOutputs, undefined); assert.equal(packet.taskBank, undefined); assert.equal(packet.artifact, undefined);
    assert.equal(packet.deliverable.preserve, 'order-and-duplicates'); assert.ok(Object.isFrozen(packet.specification));
});
test('freeze precedes one committed task bank and captures exact source bytes without execution', async () => {
    await assert.rejects(adapter.commitRealTaskBank(await planned(), [{id:'x', inputs:['1']}]), /Freeze artifact/);
    const record = await bank(); assert.equal(record.artifact.qualification, 'captured-bytes-only; executable-not-invoked');
    await assert.rejects(adapter.freezeRealTaskArtifact(record, {}), /already frozen/);
    await assert.rejects(adapter.commitRealTaskBank(record, [{id:'other', inputs:['3']}]), /Freeze artifact/);
    const altered = structuredClone(record); altered.artifact.moduleUtf8 += ' ';
    await assert.rejects(adapter.validateRealTaskRecord(altered, context), /bytes\/context changed/);
});
test('same frozen artifact binds two later tasks and retains failed result before success', async () => {
    let record = await bank();
    record = await adapter.checkRealTaskOutput(record, observed(record, 'next-1', ['5','4','-10']));
    record = await adapter.checkRealTaskOutput(record, observed(record, 'next-2', ['-1','14']));
    assert.deepEqual(record.checks.map(item => item.status), ['rejected','reference-output-matched']);
    assert.equal(record.operationalState, 'NOT_RUN');
    assert.equal(record.checks[0].artifactFreezeDigest, record.checks[1].artifactFreezeDigest);
    await assert.rejects(adapter.checkRealTaskOutput(record, observed(record, 'next-1', ['5','5','-10'])), /duplicate result/);
    assert.equal((await adapter.validateRealTaskRecord(JSON.parse(JSON.stringify(record)), context)).checks.length, 2);
});
test('resource excess stays inconclusive and declared runtime cost never becomes a measurement', async () => {
    const record = await bank();
    const result = await adapter.checkRealTaskOutput(record, observed(record, 'next-1', ['5','5','-10'], {...resources, elapsedMs:1001}));
    assert.equal(result.checks[0].status, 'inconclusive');
    assert.match(result.checks[0].resourceAccounting, /not-measured-runtime-cost/);
});
test('wrong artifact, wrong route authority, negative costs and forged check statuses reject', async () => {
    const record = await bank();
    await assert.rejects(adapter.checkRealTaskOutput(record, {...observed(record, 'next-1', ['5','5','-10']), artifactFreezeDigest:h('f')}), /substituted/);
    await assert.rejects(adapter.checkRealTaskOutput(record, observed(record, 'next-1', ['5','5','-10'], {...resources, checking:-1})), /resource vector/);
    const promoted = structuredClone(record); promoted.operationalState = 'accepted';
    await assert.rejects(adapter.validateRealTaskRecord(promoted, context), /authority is refused/);
    const checked = structuredClone(await adapter.checkRealTaskOutput(record, observed(record, 'next-1', ['5','4','-10'])));
    checked.checks[0].status = 'reference-output-matched';
    await assert.rejects(adapter.validateRealTaskRecord(checked, context), /status changed/);
});
test('malformed integer inputs, duplicate tasks, oversized source and accessor traps reject', async () => {
    const record = await frozen();
    await assert.rejects(adapter.commitRealTaskBank(record, [{id:'x', inputs:['01']}]), /future public-software/);
    await assert.rejects(adapter.commitRealTaskBank(record, [{id:'x', inputs:['1']}, {id:'x', inputs:['2']}]), /Duplicate/);
    await assert.rejects(adapter.freezeRealTaskArtifact(await planned(), {moduleUtf8:'x'.repeat(128001), environmentDigest:h('e'), trace:[]}), /Bounded source/);
    let calls = 0; const trapped = {get moduleUtf8(){ calls++; return 'x'; }, environmentDigest:h('e'), trace:[]};
    await assert.rejects(adapter.freezeRealTaskArtifact(await planned(), trapped), /Accessor/); assert.equal(calls, 0);
});
test('caller mutation during digest suspension cannot replace captured producer requirements', async () => {
    const spec = {multiplier:'3', offset:'-1', maxBatchRows:16};
    const pending = adapter.createRealTaskRecord({...context, workRequest:request, publicSource:'https://example.org/public/numerical-spec',
        specification:spec, resourceLimits:resources}); spec.multiplier = '999';
    assert.equal((await pending).specification.multiplier, '3');
});

test('full input/coefficient range admits correct64digit outputs', async () => {
    const value = '9'.repeat(32);
    let record = await adapter.createRealTaskRecord({...context, workRequest:request, publicSource:'https://example.org/public/numerical-spec',
        specification:{multiplier:value, offset:value, maxBatchRows:16}, resourceLimits:resources});
    record = await adapter.freezeRealTaskArtifact(record, {moduleUtf8:'export const transform = null;', environmentDigest:h('e'), trace:[]});
    record = await adapter.commitRealTaskBank(record, [{id:'wide', inputs:[value]}]);
    record = await adapter.checkRealTaskOutput(record, observed(record, 'wide', [String(BigInt(value)*BigInt(value)+BigInt(value))]));
    assert.equal(record.checks[0].status, 'reference-output-matched');
});
test('bank budget includes earlier failed observations and checker work without numeric overflow', async () => {
    let record = await bank();
    record = await adapter.checkRealTaskOutput(record, observed(record, 'next-1', ['5','4','-10'], {...resources, checking:60, elapsedMs:1, memoryBytes:0}));
    assert.equal(record.checks[0].status, 'rejected');
    record = await adapter.checkRealTaskOutput(record, observed(record, 'next-2', ['-1','14'], {...resources, checking:40, elapsedMs:1, memoryBytes:0}));
    assert.equal(record.checks[1].status, 'inconclusive');
    assert.equal(record.checks[1].cumulativeReportedAndCheckerUnitsExact.checking, '105');
});
test('original typed request cannot be substituted even with copied outer bindings', async () => {
    const record = structuredClone(await planned()); record.workRequest.payloadDigest = h('f');
    await assert.rejects(adapter.validateRealTaskRecord(record, context), /commitment mismatch/);
});

test('top-level proposal and installed-context getters are refused before property reads', async () => {
    let calls = 0;
    const input = {get workRequest(){ calls++; return request; }, workspaceHead:context.workspaceHead, campaignDigest:context.campaignDigest,
        publicSource:'https://example.org/public/numerical-spec', specification:{multiplier:'3', offset:'-1', maxBatchRows:16},
        resourceLimits:resources, adapterSources:context.adapterSources};
    await assert.rejects(adapter.createRealTaskRecord(input), /Accessor/); assert.equal(calls, 0);
    await assert.rejects(adapter.validateRealTaskRecord(await planned(), {get workspaceHead(){calls++; return context.workspaceHead;}}), /Accessor/);
    assert.equal(calls, 0);
});

test('actual campaign preparation attaches to the existing mission and survives reload without operational promotion', async () => {
    const [workspace, history, evidence, runtime, contract] = await Promise.all([
        import('./workspace.mjs'), import('./discovery-lab-history.mjs'), import('./discovery-lab-evidence-history.mjs'),
        import('./discovery-lab.mjs'), import('./discovery-lab-contract.mjs')]);
    let value = await workspace.createWorkspace();
    const sourceBindings = {modelDigest:h('1'), sourceDigest:h('2'), evaluatorDigest:h('3')};
    const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sourceBindings);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const result = runtime.runCampaign(start.charter), verification = history.verifyForRecording(start.charter, result);
    value = await workspace.recordDiscoveryEvent(value, 'lab-completed',
        await history.completedPayload(start.attempt, result, 1, verification.verificationResources));
    const campaign = (await workspace.inspectWorkspace(value)).discovery.campaigns[0];
    const typedRequest = await history.workRequest(campaign, 'AGIALPHA', history.reservationFor(start.charter));
    const record = await adapter.createRealTaskRecord({workRequest:typedRequest, workspaceHead:value.events.at(-1).digest,
        campaignDigest:campaign.campaignDigest, publicSource:'https://example.org/public/numerical-spec',
        specification:{multiplier:'3', offset:'-1', maxBatchRows:16}, resourceLimits:resources, adapterSources:context.adapterSources});
    const original = contract.canonical(value);
    const attached = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(campaign.campaignDigest, 'real-task-contract', record));
    const reopened = await workspace.parseWorkspace(contract.canonical(attached));
    const view = await workspace.inspectWorkspace(reopened);
    assert.equal(view.discovery.attachments.length, 1);
    assert.equal(view.discovery.attachments[0].record.operationalState, 'NOT_RUN');
    assert.equal(view.discovery.attachments[0].authority, false);
    assert.equal(contract.canonical(value), original);
    const swapped = structuredClone(record); swapped.workRequest.payload.result.state = 'rejected';
    swapped.workRequest.payloadDigest = await contract.payloadDigest(swapped.workRequest.payload);
    swapped.workRequestDigest = await contract.payloadDigest(swapped.workRequest);
    const reframed = await adapter.createRealTaskRecord({workRequest:swapped.workRequest, workspaceHead:swapped.workspaceHead,
        campaignDigest:swapped.campaignDigest, publicSource:swapped.publicSource, specification:swapped.specification,
        resourceLimits:swapped.resourceLimits, adapterSources:swapped.adapterSources});
    await assert.rejects(workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(campaign.campaignDigest, 'real-task-contract', reframed)), /exact campaign/);
});

test('identical observations from independent campaigns retain distinct stable proposal and cost identities', async () => {
    let first = await bank();
    first = await adapter.checkRealTaskOutput(first, observed(first, 'next-1', ['5','5','-10']));
    let second = await adapter.createRealTaskRecord({...context, campaignDigest:h('e'), workRequest:request, publicSource:'https://example.org/public/numerical-spec',
        specification:{multiplier:'3', offset:'-1', maxBatchRows:16}, resourceLimits:resources});
    second = await adapter.freezeRealTaskArtifact(second, {moduleUtf8:first.artifact.moduleUtf8, environmentDigest:h('e'), trace:[]});
    second = await adapter.commitRealTaskBank(second, [{id:'next-1', inputs:['2','2','-3']}, {id:'next-2', inputs:['0','5']}]);
    second = await adapter.checkRealTaskOutput(second, observed(second, 'next-1', ['5','5','-10']));
    assert.notEqual(first.proposalDigest, second.proposalDigest);
    assert.notEqual(first.artifact.freezeDigest, second.artifact.freezeDigest);
    assert.notEqual(first.checks[0].digest, second.checks[0].digest);
    const reanchored = structuredClone(first); reanchored.workspaceHead = h('f');
    await assert.rejects(adapter.validateRealTaskRecord(reanchored, {...context, workspaceHead:h('f')}), /origin changed/);
});

test('fresh proposals for the same campaign at separate original history heads have independent identities', async () => {
    const first = await planned();
    const second = await adapter.createRealTaskRecord({...context, workspaceHead:h('f'), workRequest:request, publicSource:first.publicSource,
        specification:first.specification, resourceLimits:resources});
    assert.equal(first.campaignDigest, second.campaignDigest);
    assert.notEqual(first.originHead, second.originHead); assert.notEqual(first.proposalDigest, second.proposalDigest);
    const artifact = {moduleUtf8:'export const transform = null;', environmentDigest:h('e'), trace:[]};
    let left = await adapter.freezeRealTaskArtifact(first, artifact), right = await adapter.freezeRealTaskArtifact(second, artifact);
    assert.notEqual(left.artifact.freezeDigest, right.artifact.freezeDigest);
    left = await adapter.commitRealTaskBank(left, [{id:'same-task', inputs:['1']}]);
    right = await adapter.commitRealTaskBank(right, [{id:'same-task', inputs:['1']}]);
    left = await adapter.checkRealTaskOutput(left, observed(left, 'same-task', ['2']));
    right = await adapter.checkRealTaskOutput(right, observed(right, 'same-task', ['2']));
    assert.notEqual(left.checks[0].digest, right.checks[0].digest);
    assert.equal(left.checks[0].checkerCharge.checking + right.checks[0].checkerCharge.checking, 2);
});
