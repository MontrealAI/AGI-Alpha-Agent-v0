// SPDX-License-Identifier: Apache-2.0
// Ordinary state, resource, freeze and lineage controls from a separate source reviewer.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as controller from './controller.mjs';
import * as workspace from '../successor-capability/workspace.mjs';
import {defaultCharter, same} from './protocol.mjs';

const source = {constructor: '1'.repeat(64), checker: '2'.repeat(64), closure: '3'.repeat(64)};
const charter = () => ({...defaultCharter(source), maxN: 2, constructionLimit: 100_000, perTaskLimit: 100_000});
async function begun() { return controller.start(await workspace.createWorkspace(), charter()); }
async function advance(value, count) {
    for (let i = 0; i < count; i++) value = await controller.next(value, {expectedSource: source, seed: 20261021});
    return value;
}

test('enterprise construction, acceptance, freeze and task commitment append to the original mission', async () => {
    let value = await begun();
    const original = workspace.canonical(value.events.slice(0, 1));
    value = await advance(value, 3);
    assert.equal(workspace.canonical(value.events.slice(0, 1)), original);
    const checked = await controller.state(value), row = checked.current;
    assert.equal(row.state, 'TASKS_COMMITTED');
    assert.deepEqual(value.events.slice(-3).map(e => e.kind),
        ['enterprise-constructed', 'enterprise-frozen', 'enterprise-tasks']);
    assert.equal(row.freeze.acceptedAt, value.events.find(e => e.kind === 'enterprise-constructed').digest);
    assert.equal(row.bank.freezeDigest, row.freeze.digest);
    assert.equal(row.freeze.expectedOutputs, 'not-included');
    assert.equal(row.actualConstructionWork, row.bundle.observedWorkLedger.totalCountedCampaignWork);
    assert.equal(row.bundleProof.verified, true);
    assert.equal(row.bank.tasks.length, row.charter.taskLimit);
    const saved = await workspace.parseWorkspace(workspace.canonical(value));
    const reopened = await controller.state(saved);
    assert.ok(same(reopened.current.bank, row.bank));
    assert.ok(same(reopened.current.freeze, row.freeze));
});

test('persisted invocation reservation reports uncertain execution and next does not silently repeat it', async () => {
    const value = await advance(await begun(), 4);
    const {current, next} = await controller.state(value);
    assert.equal(current.state, 'INVOCATION_RESERVED');
    assert.equal(next, 'RECONCILE_UNCERTAIN_EXECUTION');
    await assert.rejects(controller.next(value, {expectedSource: source}), /uncertain|reconcil|not.*retry/i);
    assert.equal(value.events.at(-1).kind, 'enterprise-run-reserved');
});

test('source changes hold continuation without rewriting previously accepted construction', async () => {
    const value = await advance(await begun(), 1), bytes = workspace.canonical(value);
    await assert.rejects(controller.next(value, {expectedSource: {...source, closure: '4'.repeat(64)}}), /source/i);
    assert.equal(workspace.canonical(value), bytes);
});

test('cancelled unknown construction retains its reservation and blocks same-mission reentry', async () => {
    const value = await controller.stop(await begun(), 'Interrupted before any measured outcome was reconciled.');
    const stopped = await controller.state(value), row = stopped.history.at(-1);
    assert.equal(row.state, 'CANCELLED'); assert.equal(row.unknownSpent, true);
    assert.equal(row.unresolvedReservation, true);
    await assert.rejects(controller.start(value, charter()), /unresolved|reconcil|reservation|spent/i);
});

test('cancelled unknown invocation remains unresolved across save and reopen', async () => {
    const reserved = await advance(await begun(), 4);
    const stopped = await controller.stop(reserved, 'Interrupted invocation needs exact-result reconciliation.');
    const saved = await workspace.parseWorkspace(workspace.canonical(stopped));
    const row = (await controller.state(saved)).history.at(-1);
    assert.equal(row.state, 'CANCELLED'); assert.equal(row.futureSpent, 'unknown-reservation-retained');
    assert.equal(row.unresolvedReservation, true);
    await assert.rejects(controller.start(saved, charter()), /unresolved|reconcil|reservation|spent/i);
});

test('construction execution has one live lease and recovered reservations require explicit reconciliation', async () => {
    const reserved = await begun();
    const recovered = await workspace.parseWorkspace(workspace.canonical(reserved));
    await assert.rejects(controller.next(recovered, {expectedSource: source}), /uncertain|reconcil|recovered|reservation/i);
    const constructed = await controller.next(reserved, {expectedSource: source});
    assert.equal((await controller.state(constructed)).current.state, 'ACCEPTED_CONSTRUCTION');
    await assert.rejects(controller.next(reserved, {expectedSource: source}), /uncertain|reconcil|recovered|reservation/i);
});

test('one reserved invocation reconciles once and keeps complete lineage through successor acceptance', async () => {
    const reserved = await advance(await begun(), 4);
    const recovered = await workspace.parseWorkspace(workspace.canonical(reserved));
    await assert.rejects(controller.invokeReserved(recovered, source), /reconcil|recovered|retry/i);
    let value = await controller.invokeReserved(reserved, source);
    await assert.rejects(controller.invokeReserved(reserved, source), /reconcil|attempt|retry/i);
    const invoked = (await controller.state(value)).current;
    assert.equal(invoked.state, 'INVOCATION_RECONCILED');
    assert.equal(invoked.future.runs.length, 15);
    assert.ok(invoked.future.runs.every(run => run.state === 'ACCEPTED'));
    assert.ok(invoked.futureSpent >= invoked.future.runs.reduce((total, run) => total + (run.totalWork || 0), 0));
    value = await advance(value, 3);
    const done = await controller.state(value), row = done.history.at(-1);
    assert.equal(done.current, null);
    assert.equal(row.state, 'SUCCESSOR_ACCEPTED_LOCAL');
    assert.ok(row.successor.lineageWork >= row.actualConstructionWork + row.futureSpent + row.successor.construction.totalWork);
    assert.equal(row.settlement.status, 'SIMULATED_ONLY');
    assert.equal(row.successor.externalApproval, false);
    assert.equal(row.successor.parentFreezeDigest, row.freeze.digest);
});

test('successor construction needs its persisted one-shot reservation and recovered work is never retried', async () => {
    const invocation = await advance(await begun(), 4);
    const invoked = await controller.invokeReserved(invocation, source);
    const reserved = await advance(invoked, 2);
    const current = (await controller.state(reserved)).current;
    assert.equal(current.state, 'SUCCESSOR_RESERVED');
    assert.equal(current.successorSpent, 'unknown-reservation-retained');
    assert.equal(current.successorReservation.parentFreezeDigest, current.freeze.digest);
    const recovered = await workspace.parseWorkspace(workspace.canonical(reserved));
    await assert.rejects(controller.next(recovered, {expectedSource: source}), /reconcil|recovered|retry/i);
    const completed = await controller.next(reserved, {expectedSource: source});
    assert.equal((await controller.state(completed)).history.at(-1).state, 'SUCCESSOR_ACCEPTED_LOCAL');
    await assert.rejects(controller.next(reserved, {expectedSource: source}), /reconcil|recovered|retry/i);
    assert.equal(workspace.canonical(completed.events.slice(0, reserved.events.length)), workspace.canonical(reserved.events));
});

test('cancelled successor reservation retains unknown spent work and blocks another attempt', async () => {
    const invocation = await advance(await begun(), 4);
    const reserved = await advance(await controller.invokeReserved(invocation, source), 2);
    const stopped = await controller.stop(reserved, 'Uncertain successor construction needs explicit reconciliation.');
    const row = (await controller.state(stopped)).history.at(-1);
    assert.equal(row.state, 'CANCELLED'); assert.equal(row.successorSpent, 'unknown-reservation-retained');
    assert.equal(row.unresolvedReservation, true);
    await assert.rejects(controller.start(stopped, charter()), /unresolved|reconcil|reservation|spent/i);
});

test('future preflight never starts a treatment that lacks its complete per-arm allowance', async () => {
    let value = await controller.start(await workspace.createWorkspace(), {...charter(), perTaskLimit: 0});
    value = await advance(value, 4);
    value = await controller.invokeReserved(value, source);
    const invoked = (await controller.state(value)).current;
    assert.equal(invoked.future.runs.length, 15);
    assert.ok(invoked.future.runs.every(run => run.state === 'INCONCLUSIVE' && run.path === 'not-started'
        && run.constructionWork === 0 && run.arithmetic === 0 && run.output === null));
    assert.equal(invoked.future.lineage.knownFutureTreatmentWork, 0);
    assert.equal(invoked.futureSpent, invoked.future.currentBundleAdmissionWork);
    value = await advance(value, 2);
    const stopped = (await controller.state(value)).history.at(-1);
    assert.equal(stopped.state, 'REJECTED');
    assert.equal(stopped.successor, undefined);
});
