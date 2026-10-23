// SPDX-License-Identifier: Apache-2.0
// Literal source identities are test context declarations, not installed-release byte custody.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as workspace from '../successor-capability/workspace.mjs';
import {canonical, payloadDigest} from '../successor-capability/discovery-lab-contract.mjs';
import {DOCKET_PATHS} from '../successor-capability/discovery-lab-docket.mjs';
import * as controller from './controller.mjs';
import {defaultCharter} from './protocol.mjs';
import * as native from './native-contract.mjs';

const copy = value => JSON.parse(canonical(value));
const charterSource = {constructor: '1'.repeat(64), checker: '2'.repeat(64), closure: '3'.repeat(64)};
const source = {repository: 'MontrealAI/AGI-Alpha-Agent-v0', commit: '4'.repeat(40), ...charterSource};
const limits = {checkingUnits: 1_000_000, elapsedMs: 30_000, memoryBytes: 32_000_000};
const inspectionId = 'inspection-native-test-1', logicalCommissionId = 'enterprise-commission-test-1';
async function frozenMission() {
    const charter = {...defaultCharter(charterSource), maxN: 2, constructionLimit: 100_000,
        perTaskLimit: 100_000, taskLimit: 1};
    let value = await controller.start(await workspace.createWorkspace(), charter);
    for (let i = 0; i < 2; i++) value = await controller.next(value, {expectedSource: charterSource});
    return value;
}
const frozenPromise = frozenMission();
async function contextFor(value, routeId = 'manager-usdc') {
    const inspected = await workspace.inspectWorkspace(value), row = inspected.enterprises.attempts.at(-1);
    return {schema: native.CONTEXT_SCHEMA, source: copy(source), inspectionId, logicalCommissionId,
        route: native.routeFor(routeId), limits: copy(limits), binding: {missionId: value.missionId,
            revision: value.revision, eventHead: inspected.head,
            eventPrefixDigest: await payloadDigest({missionId: value.missionId, revision: value.revision,
                eventDigests: value.events.map(event => event.digest)}),
            attempt: row.attempt, state: row.state, freezeDigest: row.freeze.digest,
            artifactDigests: row.successor?.retainedArtifactDigests || row.freeze.artifactDigests,
            invocationId: row.invocation?.invocationId || null}};
}
async function exported(value, routeId = 'manager-usdc') {
    const inspected = await workspace.inspectWorkspace(value);
    return native.createNativeExport(value, {attempt: inspected.enterprises.attempts.at(-1).attempt,
        inspectionId, logicalCommissionId, route: routeId, source, limits});
}

test('actual frozen mission and canonical thirteen-section docket pass fixed-source native inspection', async () => {
    const value = await frozenPromise, before = canonical(value);
    const {request, docket} = await exported(value), context = await contextFor(value);
    const result = await native.inspectNativeRequest(request, context, {docket});
    assert.equal(result.state, 'ACCEPTED_LOCAL_INSPECTION'); assert.equal(result.accepted, true);
    assert.deepEqual(Object.keys(JSON.parse(docket).files).sort(), [...DOCKET_PATHS].sort());
    assert.equal(result.requestDigest, await payloadDigest(request));
    assert.equal(result.docketDigest, await native.rawDigest(docket));
    assert.equal(result.resourceUsed.checkingUnits, native.NATIVE_ADMISSION_UNITS + result.work.knownReplayWork);
    assert(result.work.knownReplayWork > 0); assert(result.resourceUsed.memoryBytes > 0);
    assert.equal(result.work.unknownPartialReplay, false);
    assert.deepEqual(result.authority, []); assert.equal(result.externalSubmission, 'NOT_SUBMITTED');
    assert.equal(result.settlement, 'NOT_RUN'); assert.equal(result.reconciliation, 'RECEIVER_HISTORY_COMMIT_REQUIRED');
    assert.equal(canonical(value), before);
});

test('currency routes are zero-cap alternatives of one logical commission and Fleet is separate review', async () => {
    const value = await frozenPromise; const records = [];
    for (const routeId of ['manager-usdc', 'jobs-agialpha', 'fleet-check']) {
        const {request, docket} = await exported(value, routeId), context = await contextFor(value, routeId);
        const result = await native.inspectNativeRequest(request, context, {docket});
        assert.equal(result.accepted, true); assert.equal(request.logicalCommissionId, logicalCommissionId);
        assert.equal(request.route.capBaseUnits, '0'); assert.deepEqual(result.authority, []);
        records.push({request, result});
    }
    assert.deepEqual(records.map(record => record.request.route.currency), ['USDC6', 'AGIALPHA18', 'NONE']);
    assert.deepEqual(records.map(record => record.request.route.decimals), [6, 18, 0]);
    assert.equal(new Set(records.map(record => record.result.reconciliationKey)).size, 3);
    assert.equal(records[2].request.route.kind, 'execution-review');
    assert.equal(records[2].request.route.tokenAddress, null);
});

test('wrong chain, token, role, cap and extra authority cannot enter the native route', async () => {
    const value = await frozenPromise, original = await exported(value), context = await contextFor(value);
    for (const change of [request => { request.route.chainId = 5; },
        request => { request.route.tokenAddress = native.routeFor('jobs-agialpha').tokenAddress; },
        request => { request.route.currency = 'AGIALPHA18'; }, request => { request.route.kind = 'submit'; },
        request => { request.route.capBaseUnits = '1'; }, request => { request.authority = ['submit']; },
        request => { request.executionApproved = true; }]) {
        const request = copy(original.request); change(request);
        const result = await native.inspectNativeRequest(request, context, {docket: original.docket});
        assert.equal(result.accepted, false); assert.equal(result.state, 'REJECTED');
        assert.deepEqual(result.authority, []); assert.equal(result.externalSubmission, 'NOT_SUBMITTED');
    }
});

test('stale mission, event prefix, inspection, route or source is refused against independently retained context', async () => {
    const value = await frozenPromise, {request, docket} = await exported(value), installed = await contextFor(value);
    for (const change of [context => { context.binding.eventHead = '9'.repeat(64); },
        context => { context.binding.eventPrefixDigest = '9'.repeat(64); },
        context => { context.binding.missionId = 'capability-' + '0'.repeat(36); },
        context => { context.inspectionId = 'different-inspection'; },
        context => { context.logicalCommissionId = 'different-commission'; },
        context => { context.route = native.routeFor('jobs-agialpha'); },
        context => { context.source.commit = '9'.repeat(40); }]) {
        const context = copy(installed); change(context);
        const result = await native.inspectNativeRequest(request, context, {docket});
        assert.equal(result.accepted, false); assert.equal(result.state, 'REJECTED');
    }
});

test('matching imported declarations cannot replace actual frozen evidence or checked source in history', async () => {
    const value = await frozenPromise, original = await exported(value), installed = await contextFor(value);
    for (const field of ['freezeDigest', 'artifactDigests']) {
        const request = copy(original.request), context = copy(installed);
        const replacement = field === 'artifactDigests' ? ['9'.repeat(64), ...request.binding.artifactDigests.slice(1)] : '9'.repeat(64);
        request.binding[field] = replacement; context.binding[field] = replacement;
        const result = await native.inspectNativeRequest(request, context, {docket: original.docket});
        assert.equal(result.accepted, false); assert.equal(result.state, 'INCONCLUSIVE');
        assert.equal(result.work.unknownPartialReplay, true);
    }
    const request = copy(original.request), context = copy(installed);
    request.source.constructor = '9'.repeat(64); context.source.constructor = request.source.constructor;
    assert.equal((await native.inspectNativeRequest(request, context, {docket: original.docket})).accepted, false);
});

test('changed docket bytes or changed payload never reuse another history commitment', async () => {
    const value = await frozenPromise, original = await exported(value), context = await contextFor(value);
    const changedDocket = original.docket + '\n';
    assert.equal((await native.inspectNativeRequest(original.request, context, {docket: changedDocket})).accepted, false);
    const request = copy(original.request), second = await frozenMission();
    request.payload.workspace = second; request.payloadDigest = await payloadDigest(request.payload);
    const result = await native.inspectNativeRequest(request, context, {docket: original.docket});
    assert.equal(result.accepted, false); assert.equal(result.state, 'REJECTED');
});

test('reserved uncertain execution remains inconclusive with its known history and unknown spending retained', async () => {
    let value = await frozenPromise;
    value = await controller.next(value, {expectedSource: charterSource, seed: 5});
    value = await controller.next(value, {expectedSource: charterSource});
    const saved = await workspace.parseWorkspace(canonical(value));
    const {request, docket} = await exported(saved), context = await contextFor(saved);
    assert.equal(request.binding.state, 'INVOCATION_RESERVED');
    const result = await native.inspectNativeRequest(request, context, {docket});
    assert.equal(result.state, 'INCONCLUSIVE'); assert.equal(result.accepted, false);
    assert.equal(result.historicalState.unresolvedReservation, true);
    assert.equal(result.historicalState.futureSpent, 'unknown-reservation-retained');
    assert.equal(result.work.unknownPartialReplay, false); assert(result.work.knownReplayWork > 0);
    assert(result.reasons.includes('HISTORICAL_STATE_REQUIRES_RECONCILIATION'));
});

test('actual reconciled future invocation is inspected without changing or settling its mission', async () => {
    let value = await frozenPromise;
    value = await controller.next(value, {expectedSource: charterSource, seed: 12});
    value = await controller.next(value, {expectedSource: charterSource});
    value = await controller.invokeReserved(value, charterSource);
    const {request, docket} = await exported(value), context = await contextFor(value), before = canonical(value);
    const result = await native.inspectNativeRequest(request, context, {docket});
    assert.equal(result.accepted, true); assert.equal(result.binding.state, 'INVOCATION_RECONCILED');
    assert.equal(result.binding.invocationId, request.binding.invocationId);
    assert.equal(typeof result.historicalState.futureSpent, 'number');
    assert.equal(result.settlement, 'NOT_RUN'); assert.equal(canonical(value), before);
});

test('effective receiver budgets cannot exceed commitment and exhausted admission remains inconclusive', async () => {
    const value = await frozenPromise, {request, docket} = await exported(value), context = await contextFor(value);
    const larger = {...limits, checkingUnits: limits.checkingUnits + 1};
    assert.equal((await native.inspectNativeRequest(request, context, {docket, effectiveLimits: larger})).accepted, false);
    const noWork = {...limits, checkingUnits: native.NATIVE_ADMISSION_UNITS - 1};
    const result = await native.inspectNativeRequest(request, context, {docket, effectiveLimits: noWork});
    assert.equal(result.state, 'INCONCLUSIVE'); assert.equal(result.work.knownReplayWork, 0);
    assert.equal(result.work.admissionUnits, native.NATIVE_ADMISSION_UNITS);
    const noTime = await native.inspectNativeRequest(request, context, {docket, effectiveLimits: {...limits, elapsedMs: 0}});
    assert.equal(noTime.state, 'INCONCLUSIVE'); assert.equal(noTime.work.knownReplayWork, 0);
});

test('only finite closed native frames and limits are admitted', async () => {
    assert.throws(() => native.validateRoute({...native.routeFor('fleet-check'), authority: ['execute']}));
    assert.throws(() => native.validateLimits({...limits, checkingUnits: -1}));
    assert.throws(() => native.validateLimits({...limits, unbounded: true}));
    const value = await frozenPromise, {request, docket} = await exported(value), context = await contextFor(value);
    const result = await native.inspectNativeRequest(request, {...context, executionApproved: true}, {docket});
    assert.equal(result.accepted, false); assert.equal(result.state, 'REJECTED');
    const unstarted = await workspace.createWorkspace();
    await assert.rejects(exported(unstarted));
});

test('only four native inspections retain frames; excess work is known unstarted and releases no authority', async () => {
    const value = await frozenPromise, {request, docket} = await exported(value), context = await contextFor(value);
    assert.equal(native.MAX_NATIVE_INSPECTIONS, 4);
    const pending = Array.from({length: native.MAX_NATIVE_INSPECTIONS + 1},
        () => native.inspectNativeRequest(request, context, {docket}));
    const results = await Promise.all(pending), excess = results.at(-1);
    assert(results.slice(0, -1).every(result => result.accepted));
    assert.equal(excess.state, 'INCONCLUSIVE');
    assert.deepEqual(excess.reasons, ['NATIVE_INSPECTION_QUEUE_FULL_NOT_STARTED']);
    assert.equal(excess.work.knownReplayWork, 0); assert.equal(excess.work.unknownPartialReplay, false);
    assert.equal(excess.work.admissionUnits, native.NATIVE_ADMISSION_UNITS);
    assert.equal(excess.resourceUsed.memoryBytes, 0); assert.equal(excess.binding, null);
    assert.equal(excess.source, null); assert.equal(excess.requestDigest, null); assert.deepEqual(excess.authority, []);
    assert.match(excess.work.measurement, /not measured peak VM heap/);
    assert.match(excess.work.measurement, /not preempted/);
    assert.equal((await native.inspectNativeRequest(request, context, {docket})).accepted, true);
});
