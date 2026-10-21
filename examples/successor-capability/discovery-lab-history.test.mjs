// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as workspace from './workspace.mjs';
import * as history from './discovery-lab-history.mjs';
import * as runtime from './discovery-lab.mjs';
import * as contract from './discovery-lab-contract.mjs';
import * as protocol from '../../docs/assets/successor/engine.mjs';
import {createInspector} from './discovery-lab-inspector.mjs';
const sources = {modelDigest: '1'.repeat(64), sourceDigest: '2'.repeat(64), evaluatorDigest: '3'.repeat(64)};
const copy = value => JSON.parse(contract.canonical(value));
async function campaign(input = null, charter = runtime.DEFAULT_CHARTER, parentDigest = null) {
    let value = input || await workspace.createWorkspace();
    const start = await history.startPayload(value, charter, sources, parentDigest);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const state = await workspace.inspectWorkspace(value);
    const parent = state.discovery.active.parent?.result || null;
    const result = runtime.runCampaign(charter, {parent});
    const verification = runtime.verifyCampaign(charter, result, {parent});
    value = await workspace.recordDiscoveryEvent(value, 'lab-completed',
        await history.completedPayload(start.attempt, result, 1, verification.verificationResources));
    const inspection = await workspace.inspectWorkspace(value);
    return {value, record: inspection.discovery.campaigns.at(-1)};
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
test('v2 extends the original exact chain and preserves prior v1 events and evidence', async () => {
    const old = await workspace.createWorkspace();
    const {value, record} = await campaign(old);
    assert.equal(old.schema, 'successor-capability-workspace/v1');
    assert.equal(value.schema, 'successor-capability-workspace/v2');
    assert.deepEqual(value.events[0], old.events[0]);
    assert.equal(record.state, 'accepted');
    assert.deepEqual(record.recordedVerification, record.result.resources);
    assert.deepEqual(await workspace.parseWorkspace(contract.canonical(value)), value);
    assert.ok(history.auditSnapshot().inspections > 0);
});
test('honest rejected and budget-inconclusive results survive later accepted campaigns', async () => {
    const low = {...copy(runtime.DEFAULT_CHARTER), budget: {...runtime.DEFAULT_CHARTER.budget, search: 0}};
    const first = await campaign(null, low);
    const bad = {...copy(runtime.DEFAULT_CHARTER), memory: 1};
    const second = await campaign(first.value, bad);
    const third = await campaign(second.value);
    const inspection = await workspace.inspectWorkspace(third.value);
    assert.deepEqual(inspection.discovery.campaigns.map(record => record.state), ['inconclusive', 'rejected', 'accepted']);
    assert.deepEqual(third.value.events.slice(0, first.value.events.length), first.value.events);
});
test('a stronger successor reopens with intact verified ancestry and all ancestor costs', async () => {
    const parent = await campaign();
    const charter = {...copy(runtime.DEFAULT_CHARTER), controls: 4, memory: 16, operations: ['flip-z', 'flip-w']};
    const child = await campaign(parent.value, charter, parent.record.resultDigest);
    const reopened = await workspace.parseWorkspace(contract.canonical(child.value));
    const record = (await workspace.inspectWorkspace(reopened)).discovery.campaigns.at(-1);
    assert.equal(record.result.state, 'accepted');
    assert.equal(record.parent.resultDigest, parent.record.resultDigest);
    assert.equal(record.result.lineage.generation, 2);
    assert.ok(record.result.lineage.cumulative.acquisitions > record.result.resources.acquisitions);
    assert.equal(record.result.reuse.priorPurposePreservedOnOldSlice, true);
});
test('rehashing forged terminal acceptance, cost, verification or source-purpose bindings does not qualify', async () => {
    const {value} = await campaign();
    for (const change of [
        v => { v.events[2].payload.result.resources.acquisitions = 0; },
        v => { v.events[2].payload.recordedVerification.search = 0; },
        v => { v.events[1].payload.bindings.charterDigest = '9'.repeat(64); },
        v => { v.events[1].payload.parentDigest = '9'.repeat(64); },
        v => { v.schema = 'successor-capability-workspace/v1'; },
        v => { v.events[2].payload.extra = true; }
    ]) {
        const altered = copy(value); change(altered);
        if (altered.events[2].payload.result) {
            altered.events[2].payload.resultDigest = await contract.payloadDigest(altered.events[2].payload.result);
        }
        await rehash(altered);
        await assert.rejects(workspace.inspectWorkspace(altered));
    }
});
test('interruption retains the reservation without inventing zero spent work or a completion', async () => {
    let value = await workspace.createWorkspace();
    const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sources);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const interrupted = await workspace.parseWorkspace(contract.canonical(value));
    assert.equal((await workspace.inspectWorkspace(interrupted)).discovery.active.state, 'searching');
    value = await workspace.recordDiscoveryEvent(interrupted, 'lab-stopped',
        history.stoppedPayload(start.attempt, 'Explicit recovery after interruption.'));
    const checked = await workspace.inspectWorkspace(value);
    assert.equal(checked.discovery.active, null);
    assert.equal(checked.discovery.attempts[0].state, 'paused');
    assert.equal(checked.discovery.attempts[0].resourceDisposition, 'reservation-retained-spent-work-unknown');
    assert.equal(checked.discovery.campaigns.length, 0);
    assert.equal(history.historyCapacity({...value, events: Array(22).fill(value.events[0])}).canRun, false);
});
test('strict direct-object inspection rejects an accessor before invoking it', async () => {
    const value = await workspace.createWorkspace(); let calls = 0;
    Object.defineProperty(value, 'authority', {enumerable: true, get() { calls++; return []; }});
    await assert.rejects(workspace.inspectWorkspace(value)); assert.equal(calls, 0);
});
test('real installed semantic adapter admits a frozen draft and rejects changed artifacts and forged evidence', async () => {
    const {record} = await campaign();
    const limits = {acquisitions: 10000, search: 10000000, checking: 10000000,
        memoryBytes: 8000000, storageBytes: 1000000, workerCapacity: 4, installations: 100, elapsedMs: 120000};
    const request = await history.workRequest(record, 'USDC', limits);
    const inspect = createInspector(sources);
    const accepted = await inspect(request.payload, {request, limits});
    assert.equal(accepted.accepted, true); assert.ok(accepted.resourceUsed.acquisitions > 0);
    const swapped = {...request, inputArtifacts: []};
    assert.deepEqual((await inspect(request.payload, {request: swapped, limits})).reasons, ['INPUT_ARTIFACT_BINDING_MISMATCH']);
    const forged = copy(request.payload); forged.result.resources.search = 0;
    const forgedRequest = {...request, payload: forged, payloadDigest: await contract.payloadDigest(forged)};
    const refused = await inspect(forged, {request: forgedRequest, limits});
    assert.equal(refused.accepted, false); assert.ok(refused.resourceUsed.search > 0);
    const exhausted = await inspect(request.payload, {request, limits: {...limits, checking: 0}});
    assert.equal(exhausted.accepted, false); assert.match(exhausted.reasons[0], /CHECK_INCOMPLETE$/);
    assert.equal(exhausted.resourceUsed.search, 0);
    const wrongSource = await inspect(request.payload, {request: {...request, sourceDigest: 'f'.repeat(64)}, limits});
    assert.deepEqual(wrongSource.reasons, ['INSTALLED_SOURCE_MISMATCH']);
});

const inspectionLimits = () => ({acquisitions: 10000, search: 10000000, checking: 10000000,
    memoryBytes: 8000000, storageBytes: 4000000, workerCapacity: 4, installations: 100, elapsedMs: 120000});
test('installed inspector validates all six complete envelopes with smaller sufficient effective limits', async () => {
    const {record} = await campaign();
    const limits = inspectionLimits();
    const remaining = {...limits, acquisitions: 9900, search: 9999900, checking: 9999900,
        memoryBytes: 7000000, storageBytes: 3000000, workerCapacity: 3, installations: 90, elapsedMs: 119000};
    const inspect = createInspector(sources);
    for (const [index, stage] of contract.STAGES.entries()) {
        const request = await history.workRequest(record, index % 2 ? 'AGIALPHA' : 'USDC', limits);
        request.stage = stage; request.inputArtifacts = record.artifacts.slice(0, index).map(value => value.digest);
        const result = await inspect(request.payload, {request, limits: remaining});
        assert.equal(result.accepted, true, stage);
        assert.ok(result.resourceUsed.search > 0); assert.ok(result.resourceUsed.memoryBytes > 0);
        assert.ok(result.resourceUsed.elapsedMs >= 0);
    }
});
test('installed inspector refuses malformed complete requests before finite replay', async () => {
    const {record} = await campaign(); const limits = inspectionLimits();
    const original = await history.workRequest(record, 'USDC', limits); const inspect = createInspector(sources);
    for (const change of [
        value => { value.schema = 'other/v1'; },
        value => { delete value.schema; },
        value => { value.authority = 'submitted'; },
        value => { value.executionMode = 'external'; },
        value => { value.commission.status = 'SUBMITTED'; },
        value => { value.commission.capBaseUnits = '1'; },
        value => { value.commission.currency = 'AGIALPHA18'; },
        value => { value.payloadDigest = '0'.repeat(64); },
        value => { value.resourceLimits.checking = Number.MAX_SAFE_INTEGER + 1; }
    ]) {
        const request = copy(original); change(request);
        const result = await inspect(original.payload, {request, limits});
        assert.equal(result.accepted, false);
        assert.equal(result.resourceUsed.search, 0);
    }
});
test('installed inspector binds the separately inspected payload to the validated commitment', async () => {
    const {record} = await campaign(); const limits = inspectionLimits();
    const request = await history.workRequest(record, 'USDC', limits); const inspect = createInspector(sources);
    const substituted = copy(request); substituted.payload.result.resources.search = 0;
    substituted.payloadDigest = await contract.payloadDigest(substituted.payload);
    await contract.validateWorkRequest(substituted);
    const result = await inspect(request.payload, {request: substituted, limits});
    assert.equal(result.accepted, false); assert.equal(result.resourceUsed.search, 0);
    assert.deepEqual(result.reasons, ['PAYLOAD_COMMITMENT_MISMATCH']);
});
test('installed inspector refuses every effective dimension above the committed envelope', async () => {
    const {record} = await campaign(); const limits = inspectionLimits();
    const request = await history.workRequest(record, 'USDC', limits); const inspect = createInspector(sources);
    for (const key of contract.RESOURCE_KEYS) {
        const result = await inspect(request.payload, {request, limits: {...limits, [key]: limits[key] + 1}});
        assert.equal(result.accepted, false, key); assert.equal(result.resourceUsed.search, 0, key);
        assert.deepEqual(result.reasons, ['EFFECTIVE_LIMITS_EXCEED_COMMITMENT']);
    }
});
test('installed inspector captures request payload and remaining limits before digest awaits', async () => {
    const {record} = await campaign(); const limits = inspectionLimits();
    const request = await history.workRequest(record, 'USDC', limits); const payload = copy(request.payload);
    const inspect = createInspector(sources); const pending = inspect(payload, {request, limits});
    request.executionMode = 'external'; request.payload.result.resources.search = 0;
    payload.result.resources.search = 0; limits.checking = 0;
    const result = await pending;
    assert.equal(result.accepted, true); assert.ok(result.resourceUsed.search > 0);
    const later = await inspect(payload, {request, limits: inspectionLimits()});
    assert.equal(later.accepted, false); assert.equal(later.resourceUsed.search, 0);
});
test('zero elapsed allowance refuses before replay even when the trusted clock has not advanced', async t => {
    const {record} = await campaign(); const limits = {...inspectionLimits(), elapsedMs: 0};
    const request = await history.workRequest(record, 'USDC', limits);
    t.mock.method(performance, 'now', () => 0);
    const result = await createInspector(sources)(request.payload, {request, limits});
    assert.equal(result.accepted, false); assert.equal(result.resourceUsed.search, 0);
    assert.ok(result.resourceUsed.checking > 0); assert.ok(result.resourceUsed.memoryBytes > 0);
    assert.match(result.reasons.at(-1), /CHECK_INCOMPLETE$/);
});
test('elapsed overrun after replay remains incomplete and retains actual finite work', async t => {
    const {record} = await campaign(); const limits = {...inspectionLimits(), elapsedMs: 100};
    const request = await history.workRequest(record, 'USDC', limits); let samples = 0;
    // Start and pre-replay observations fit; the completion observation exceeds the allowance.
    t.mock.method(performance, 'now', () => ++samples <= 2 ? 0 : 101);
    const result = await createInspector(sources)(request.payload, {request, limits});
    assert.equal(result.accepted, false); assert.equal(result.resourceUsed.elapsedMs, 101);
    assert.ok(result.resourceUsed.search > 0); assert.ok(result.resourceUsed.acquisitions > 0);
    assert.match(result.reasons.at(-1), /CHECK_INCOMPLETE$/);
});
test('invalid finite evidence keeps verification and elapsed costs after the soft deadline', async t => {
    const {record} = await campaign(); const limits = {...inspectionLimits(), elapsedMs: 100};
    const request = await history.workRequest(record, 'USDC', limits);
    request.payload.result.resources.search = 0; request.payloadDigest = await contract.payloadDigest(request.payload);
    let samples = 0; t.mock.method(performance, 'now', () => ++samples <= 2 ? 0 : 101);
    const result = await createInspector(sources)(request.payload, {request, limits});
    assert.equal(result.accepted, false); assert.equal(result.resourceUsed.elapsedMs, 101);
    assert.ok(result.resourceUsed.search > 0); assert.ok(result.resourceUsed.checking > 0);
    assert.ok(result.reasons.includes('FINITE_EVIDENCE_REJECTED'));
    assert.match(result.reasons.at(-1), /CHECK_INCOMPLETE$/);
});

test('framing refusals preserve the fixed native charge and known encoded snapshots', async () => {
    const {record} = await campaign(); const limits = inspectionLimits();
    const request = await history.workRequest(record, 'USDC', limits); const inspect = createInspector(sources);
    const invalid = {...request, executionMode: 'external'};
    const source = {...request, sourceDigest: 'f'.repeat(64)};
    for (const [candidate, remaining] of [[invalid, limits], [source, limits],
        [request, {...limits, checking: contract.DISCOVERY_LAB_INSPECTION_CHECKS - 1}],
        [request, {...limits, additional: 1}]]) {
        const result = await inspect(request.payload, {request: candidate, limits: remaining});
        assert.equal(result.accepted, false); assert.equal(result.resourceUsed.search, 0);
        assert.equal(result.resourceUsed.checking, contract.DISCOVERY_LAB_INSPECTION_CHECKS);
        assert.ok(result.resourceUsed.memoryBytes > 0); assert.ok(result.resourceUsed.elapsedMs >= 0);
    }
});
test('native checking overhead is reserved before replay instead of borrowing charter capacity', async () => {
    const {record} = await campaign();
    const limits = {...inspectionLimits(), checking: runtime.DEFAULT_CHARTER.budget.checking + contract.DISCOVERY_LAB_INSPECTION_CHECKS};
    const request = await history.workRequest(record, 'USDC', limits); const inspect = createInspector(sources);
    const incomplete = await inspect(request.payload, {request,
        limits: {...limits, checking: limits.checking - contract.DISCOVERY_LAB_INSPECTION_CHECKS}});
    assert.equal(incomplete.accepted, false); assert.equal(incomplete.resourceUsed.search, 0);
    assert.equal(incomplete.resourceUsed.checking, contract.DISCOVERY_LAB_INSPECTION_CHECKS);
    assert.match(incomplete.reasons[0], /CHECK_INCOMPLETE$/);
    const accepted = await inspect(request.payload, {request, limits});
    assert.equal(accepted.accepted, true);
    assert.ok(accepted.resourceUsed.checking > contract.DISCOVERY_LAB_INSPECTION_CHECKS);
});
test('elapsed deadline already exhausted at preflight does not begin finite replay', async t => {
    const {record} = await campaign(); const limits = {...inspectionLimits(), elapsedMs: 100};
    const request = await history.workRequest(record, 'USDC', limits); let samples = 0;
    t.mock.method(performance, 'now', () => ++samples === 1 ? 0 : 101);
    const result = await createInspector(sources)(request.payload, {request, limits});
    assert.equal(result.accepted, false); assert.equal(result.resourceUsed.search, 0);
    assert.equal(result.resourceUsed.elapsedMs, 101);
    assert.equal(result.resourceUsed.checking, contract.DISCOVERY_LAB_INSPECTION_CHECKS);
    assert.match(result.reasons.at(-1), /CHECK_INCOMPLETE$/);
});

test('context acquisition failures retain native framing charge without diagnostic getters', async () => {
    let diagnosticReads = 0;
    const failure = new Error('Opaque host context');
    Object.defineProperty(failure, 'verificationResources', {get() { diagnosticReads++; throw Error('Do not read'); }});
    Object.freeze(failure);
    const opaque = {};
    Object.defineProperty(opaque, 'request', {get() { throw failure; }});
    for (const options of [null, opaque]) {
        const result = await createInspector(sources)({}, options);
        assert.equal(result.accepted, false);
        assert.equal(result.resourceUsed.checking, contract.DISCOVERY_LAB_INSPECTION_CHECKS);
        assert.equal(result.resourceUsed.search, 0); assert.ok(result.resourceUsed.elapsedMs >= 0);
    }
    assert.equal(diagnosticReads, 0);
});
