// SPDX-License-Identifier: Apache-2.0
// Ordinary fixed witness, Discovery and enterprise histories share one bounded mission record.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as workspace from '../successor-capability/workspace.mjs';
import * as discovery from '../successor-capability/discovery-lab-history.mjs';
import * as discoveryRuntime from '../successor-capability/discovery-lab.mjs';
import * as controller from './controller.mjs';
import {defaultCharter, makeTaskBank} from './protocol.mjs';
import {digest} from '../../docs/assets/successor/engine.mjs';

const source = {constructor: '1'.repeat(64), checker: '2'.repeat(64), closure: '3'.repeat(64)};
const discoverySource = {modelDigest: '4'.repeat(64), sourceDigest: '5'.repeat(64), evaluatorDigest: '6'.repeat(64)};
const charter = {...defaultCharter(source), maxN: 2, constructionLimit: 100_000, perTaskLimit: 100_000, taskLimit: 1};
const blocked = /active enterprise attempt/i;
const original = () => workspace.createWorkspace(workspace.DEFAULT_BRIEF, workspace.defaultExperiment());
const owned = value => JSON.parse(workspace.canonical(value));
async function frozen(input = null) {
    let value = await controller.start(input || await original(), charter);
    for (let i = 0; i < 2; i++) value = await controller.next(value, {expectedSource: source});
    assert.equal((await controller.state(value)).current.state, 'FROZEN');
    return value;
}
async function discoveryStart(value) {
    return discovery.startPayload(value, discoveryRuntime.DEFAULT_CHARTER, discoverySource);
}
async function appendRecorded(value, kind, payload) {
    const next = owned(value), event = {sequence: next.events.length, kind,
        previous: next.events.at(-1).digest, payload};
    next.schema = discovery.EXTENDED_SCHEMA;
    event.digest = await digest('capability-event', {missionId: next.missionId, ...event});
    next.events.push(event); next.revision = next.events.length - 1;
    return next;
}
async function legacyLabPair(value) {
    const payload = await discoveryStart(value);
    value = await appendRecorded(value, 'lab-started', payload);
    return appendRecorded(value, 'lab-stopped', discovery.stoppedPayload(payload.attempt,
        'Retain a valid historical stopped Discovery reservation.'));
}
async function complete(value) {
    value = await controller.next(value, {expectedSource: source, seed: 77});
    value = await controller.next(value, {expectedSource: source});
    value = await controller.invokeReserved(value, source);
    for (let i = 0; i < 3; i++) value = await controller.next(value, {expectedSource: source});
    assert.equal((await controller.state(value)).history.at(-1).state, 'SUCCESSOR_ACCEPTED_LOCAL');
    return value;
}

test('unrelated witness and lab appends cannot consume the slots needed to reconcile a reserved invocation', async t => {
    const start = await frozen(); let value = start, unrelatedAppends = 0;
    for (const phase of ['development', 'heldout']) {
        try { value = await workspace.recordEvaluation(value, phase); unrelatedAppends++; }
        catch (error) { assert.match(error.message, blocked); }
    }
    for (let i = 0; i < 8; i++) {
        const payload = await discoveryStart(value);
        try { value = await workspace.recordDiscoveryEvent(value, 'lab-started', payload); unrelatedAppends++; }
        catch (error) { assert.match(error.message, blocked); break; }
        value = await workspace.recordDiscoveryEvent(value, 'lab-stopped',
            discovery.stoppedPayload(payload.attempt, 'Explicitly stopped ordinary Discovery reservation.'));
        unrelatedAppends++;
    }
    value = await controller.next(value, {expectedSource: source, seed: 77});
    value = await controller.next(value, {expectedSource: source});
    const reserved = value; let invocationError = null;
    try { value = await controller.invokeReserved(reserved, source); }
    catch (error) { invocationError = error.message; }
    t.diagnostic(JSON.stringify({unrelatedAppends, eventCountAtReservation: reserved.events.length,
        stateAfterAttempt: (await controller.state(value)).current.state, invocationError}));
    assert.equal(unrelatedAppends, 0, 'Unrelated history consumed reserved enterprise capacity.');
    assert.equal(invocationError, null, 'A checked invocation must retain room to append its result.');
    assert.equal((await controller.state(value)).current.state, 'INVOCATION_RECONCILED');
    assert.equal(workspace.canonical(value.events.slice(0, start.events.length)), workspace.canonical(start.events));
});

test('public witness and Discovery preflights refuse active enterprise work without changing its history', async () => {
    const value = await frozen(), before = workspace.canonical(value);
    await assert.rejects(workspace.recordEvaluation(value, 'development'), blocked);
    await assert.rejects(workspace.recordDiscoveryEvent(value, 'lab-started', await discoveryStart(value)), blocked);
    const checked = await workspace.inspectWorkspace(value);
    assert.equal(checked.latest.development, null); assert.equal(checked.discovery.active, null);
    assert.equal(checked.enterprises.active.state, 'FROZEN'); assert.equal(workspace.canonical(value), before);
});

test('a valid historical witness and lab interleaving remains readable and can finish with one recovery slot', async () => {
    const base = await original(), evaluated = await workspace.recordEvaluation(base, 'development');
    const value = await frozen(base), payload = evaluated.events.at(-1).payload;
    let legacy = await appendRecorded(value, 'evaluation', payload);
    for (let i = 0; i < 6; i++) legacy = await legacyLabPair(legacy);
    const encoded = workspace.canonical(legacy), restored = await workspace.parseWorkspace(encoded);
    assert.equal(workspace.canonical(restored), encoded);
    assert.equal(workspace.LIMITS.events - restored.events.length, 7);
    const completed = await complete(restored), checked = await workspace.inspectWorkspace(completed);
    assert.equal(completed.events.length, 23); assert.equal(checked.discovery.attempts.length, 6);
    assert.equal(checked.latest.development.report.verdict, 'pass');
    assert.equal(workspace.canonical(completed.events.slice(0, restored.events.length)), workspace.canonical(restored.events));
});

test('a historical active Discovery reservation remains readable and can stop after the enterprise stops', async () => {
    const value = await frozen(), payload = await discoveryStart(value);
    const appended = await appendRecorded(value, 'lab-started', payload);
    const restored = await workspace.parseWorkspace(workspace.canonical(appended));
    assert.equal((await workspace.inspectWorkspace(restored)).discovery.active.attempt, payload.attempt);
    const stopped = await controller.stop(restored, 'Keep the historical Discovery reservation readable.');
    const labStopped = await workspace.recordDiscoveryEvent(stopped, 'lab-stopped',
        discovery.stoppedPayload(payload.attempt, 'Stop the historical Discovery reservation.'));
    const checked = await workspace.inspectWorkspace(labStopped);
    assert.equal(checked.enterprises.active, null); assert.equal(checked.discovery.active, null);
    assert.equal(workspace.canonical(labStopped.events.slice(0, restored.events.length)), workspace.canonical(restored.events));
});

test('an imported near-capacity frozen history refuses continuation before future work and retains its stop slot', async () => {
    const base = await original(), evaluated = await workspace.recordEvaluation(base, 'development');
    let legacy = await appendRecorded(await frozen(base), 'evaluation', evaluated.events.at(-1).payload);
    for (let i = 0; i < 9; i++) legacy = await legacyLabPair(legacy);
    const encoded = workspace.canonical(legacy), restored = await workspace.parseWorkspace(encoded);
    const prefix = workspace.canonical(restored.events);
    assert.equal(restored.events.length, 23); assert.equal(workspace.canonical(restored), encoded);
    await assert.rejects(controller.next(restored, {expectedSource: source, seed: 77}), /history.*space|history.*capacity/i);
    const checked = await controller.state(restored);
    assert.equal(checked.current.state, 'FROZEN'); assert.equal(checked.current.bank, undefined);
    assert.equal(checked.current.invocation, undefined); assert.equal(workspace.canonical(restored.events), prefix);
    const stopped = await controller.stop(restored, 'Stop with the retained final history slot.');
    assert.equal(stopped.events.length, workspace.LIMITS.events);
    assert.equal(workspace.canonical(stopped.events.slice(0, restored.events.length)), prefix);
    assert.equal((await controller.state(stopped)).history.at(-1).state, 'CANCELLED');
});

test('a dense mission with exactly eleven free slots completes and retains terminal witness activity', async () => {
    let base = await original();
    for (let version = 1; version <= 4; version++) {
        base = await workspace.recordEvaluation(base, 'development');
        base = await workspace.recordEvaluation(base, 'heldout');
        base = await workspace.addSuccessor(base, {...workspace.DEFAULT_BRIEF, title: `Ordinary proposal ${version + 1}`},
            workspace.defaultExperiment(), 'An explicit ordinary proposal change.');
    }
    assert.equal(base.events.length, 13); assert.equal(workspace.LIMITS.events - base.events.length, 11);
    const value = await frozen(base), before = workspace.canonical(value.events);
    await assert.rejects(workspace.recordEvaluation(value, 'development'), blocked);
    await assert.rejects(workspace.recordDiscoveryEvent(value, 'lab-started', await discoveryStart(value)), blocked);
    let completed = await complete(value);
    assert.equal(completed.events.length, 22);
    assert.equal(workspace.canonical(completed.events.slice(0, value.events.length)), before);
    completed = await workspace.recordEvaluation(completed, 'development');
    completed = await workspace.recordEvaluation(completed, 'heldout');
    const saved = await workspace.parseWorkspace(workspace.canonical(completed));
    assert.equal(saved.events.length, workspace.LIMITS.events);
    assert.equal((await workspace.inspectWorkspace(saved)).latest.witnessAcceptance, 'pass');
});

test('stopping a frozen attempt releases its active append guard and preserves all earlier records', async () => {
    const value = await frozen(); let stopped = await controller.stop(value, 'Stop before another ordinary campaign.');
    const before = workspace.canonical(stopped.events);
    stopped = await workspace.recordEvaluation(stopped, 'development');
    const start = await discoveryStart(stopped);
    stopped = await workspace.recordDiscoveryEvent(stopped, 'lab-started', start);
    stopped = await workspace.recordDiscoveryEvent(stopped, 'lab-stopped', discovery.stoppedPayload(start.attempt,
        'Explicit stopped legacy Discovery attempt.'));
    const inspected = await workspace.inspectWorkspace(stopped);
    assert.equal(inspected.enterprises.active, null); assert.equal(inspected.discovery.active, null);
    assert.equal(inspected.enterprises.attempts.at(-1).unknownSpent, false);
    assert.equal(workspace.canonical(stopped.events.slice(0, JSON.parse(before).length)), before);
});

test('terminal unknown enterprise reservations remain visible when unrelated witness history resumes', async () => {
    const reserved = await controller.start(await original(), charter);
    const stopped = await controller.stop(reserved, 'Retain the unknown construction reservation.');
    const evaluated = await workspace.recordEvaluation(stopped, 'development');
    const inspected = await workspace.inspectWorkspace(evaluated);
    assert.equal(inspected.enterprises.active, null);
    assert.equal(inspected.enterprises.attempts.at(-1).unknownSpent, true);
    assert.equal(inspected.enterprises.attempts.at(-1).unresolvedReservation, true);
    await assert.rejects(controller.start(evaluated, charter), /unknown|unresolved|reconcil|spent/i);
});

test('a legacy mission with no enterprise still records its ordinary witness and Discovery lifecycle', async () => {
    let value = await workspace.recordEvaluation(await original(), 'development');
    value = await workspace.recordEvaluation(value, 'heldout');
    const start = await discoveryStart(value);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    value = await workspace.recordDiscoveryEvent(value, 'lab-stopped', discovery.stoppedPayload(start.attempt,
        'A normal independent Discovery stop.'));
    const inspected = await workspace.inspectWorkspace(value);
    assert.equal(inspected.latest.witnessAcceptance, 'pass');
    assert.equal(inspected.discovery.attempts.length, 1); assert.equal(inspected.discovery.active, null);
    assert.equal(inspected.enterprises, undefined);
});

test('the public enterprise appender refuses a new reservation without all continuation and recovery slots', async () => {
    let value = await original();
    for (let i = 0; i < 11; i++) value = await legacyLabPair(value);
    value = await workspace.parseWorkspace(workspace.canonical(value));
    const before = workspace.canonical(value);
    assert.equal(value.events.length, 23);
    await assert.rejects(workspace.recordEnterpriseEvent(value, 'enterprise-started',
        {attempt: 'enterprise-' + crypto.randomUUID(), charter}), /history.*space|history.*capacity/i);
    assert.equal(workspace.canonical(value), before);
    assert.equal((await workspace.inspectWorkspace(value)).enterprises, undefined);
});

test('the public enterprise appender shares the eleven-slot admission boundary and retains Stop', async () => {
    let value = await original();
    for (let i = 0; i < 6; i++) value = await legacyLabPair(value);
    assert.equal(workspace.LIMITS.events - value.events.length, 11);
    const prefix = workspace.canonical(value.events);
    const started = await workspace.recordEnterpriseEvent(value, 'enterprise-started',
        {attempt: 'enterprise-' + crypto.randomUUID(), charter});
    assert.equal((await controller.state(started)).current.state, 'RESERVED');
    const stopped = await controller.stop(started, 'Stop the directly recorded reservation without inventing execution.');
    assert.equal((await controller.state(stopped)).current, null);
    assert.equal((await controller.state(stopped)).history.at(-1).state, 'CANCELLED');
    assert.equal(workspace.canonical(stopped.events.slice(0, value.events.length)), prefix);
    value = await workspace.recordEvaluation(value, 'development');
    assert.equal(workspace.LIMITS.events - value.events.length, 10);
    await assert.rejects(workspace.recordEnterpriseEvent(value, 'enterprise-started',
        {attempt: 'enterprise-' + crypto.randomUUID(), charter}), /history.*space|history.*capacity/i);
});

test('a historical near-capacity reservation remains readable and can consume its final Stop slot', async () => {
    let value = await workspace.recordEvaluation(await original(), 'development');
    for (let i = 0; i < 10; i++) value = await legacyLabPair(value);
    value = await appendRecorded(value, 'enterprise-started', {attempt: 'enterprise-' + crypto.randomUUID(), charter});
    const encoded = workspace.canonical(value), restored = await workspace.parseWorkspace(encoded);
    assert.equal(restored.events.length, 23); assert.equal(workspace.canonical(restored), encoded);
    const stopped = await controller.stop(restored, 'Keep the original reservation and explicitly stop at capacity.');
    assert.equal(stopped.events.length, 24);
    assert.equal(workspace.canonical(stopped.events.slice(0, restored.events.length)), workspace.canonical(restored.events));
    assert.equal((await controller.state(stopped)).history.at(-1).unknownSpent, true);
});

test('direct enterprise continuations cannot consume the last recovery slot of a historical frozen attempt', async () => {
    const base = await original(), evaluated = await workspace.recordEvaluation(base, 'development');
    let value = await appendRecorded(await frozen(base), 'evaluation', evaluated.events.at(-1).payload);
    for (let i = 0; i < 9; i++) value = await legacyLabPair(value);
    const restored = await workspace.parseWorkspace(workspace.canonical(value));
    const {current} = await controller.state(restored), before = workspace.canonical(restored);
    assert.equal(restored.events.length, 23);
    const bank = await makeTaskBank(current.freeze, 77, current.charter.maxN, current.charter.taskLimit);
    await assert.rejects(workspace.recordEnterpriseEvent(restored, 'enterprise-tasks',
        {attempt: current.attempt, bank}), /history.*space|history.*capacity/i);
    assert.equal(workspace.canonical(restored), before);
    const stopped = await controller.stop(restored, 'Retain the final Stop slot after refusing direct continuation.');
    assert.equal(stopped.events.length, 24); assert.equal((await controller.state(stopped)).current, null);
});
