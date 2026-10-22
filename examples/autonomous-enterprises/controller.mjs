// SPDX-License-Identifier: Apache-2.0
import * as workspace from '../successor-capability/workspace.mjs';
import {copy, need, same, validateCharter, makeFreeze, makeTaskBank, completeConstructionWork} from './protocol.mjs';
import {buildFoundry, constructInverse} from './foundry.mjs';
import {qualifyArtifact} from './checker.mjs';
import {evaluateFuture, TREATMENTS} from './future.mjs';
const constructionLeases = new WeakSet(), invocationLeases = new WeakSet(), successorLeases = new WeakSet();

export async function start(workspaceInput, charterInput) {
    const charter = validateCharter(charterInput), value = copy(workspaceInput);
    const inspected = await workspace.inspectWorkspace(value);
    need(!inspected.enterprises?.active, 'Reconcile the earlier enterprise reservation first.');
    need(!inspected.enterprises?.attempts.some(row => row.unresolvedReservation || row.unknownSpent
        || row.state === 'INVOCATION_RESERVED'), 'Unknown historical spent work must be reconciled before another attempt in this mission.');
    need(workspace.LIMITS.events - value.events.length >= 11, 'Reserve history space for construction, future tasks and recovery.');
    const result = await workspace.recordEnterpriseEvent(value, 'enterprise-started',
        {attempt: 'enterprise-' + crypto.randomUUID(), charter});
    constructionLeases.add(result); return result;
}
export async function state(value) {
    const checked = await workspace.inspectWorkspace(value), current = checked.enterprises?.active;
    const stages = {RESERVED: 'construct', ACCEPTED_CONSTRUCTION: 'freeze', FROZEN: 'supply-future-tasks',
        TASKS_COMMITTED: 'reserve-invocation', INVOCATION_RESERVED: 'RECONCILE_UNCERTAIN_EXECUTION',
        INVOCATION_RECONCILED: 'reconcile-simulated-work', READY_FOR_SUCCESSOR: 'reserve-successor',
        SUCCESSOR_RESERVED: 'construct-successor'};
    return {current, next: current ? stages[current.state] : 'STOPPED', history: checked.enterprises?.attempts || [],
        externalAuthority: false};
}
export async function next(valueInput, optionsInput = {}) {
    const value = copy(valueInput), options = copy(optionsInput);
    const {seed = 20261021, expectedSource} = options;
    const inputSource = copy(expectedSource);
    const inspected = await state(value), current = inspected.current;
    need(current, 'No active bounded enterprise attempt.');
    need(same(current.charter.source, inputSource), 'Installed source changed; keep history and requalify before continuation.');
    const payload = {attempt: current.attempt};
    if (inspected.next === 'construct') {
        need(constructionLeases.has(valueInput), 'Recovered construction is uncertain; retain and reconcile its reservation instead of retrying.');
        constructionLeases.delete(valueInput);
        const completeReservation = Math.ceil(2_000_000 * (current.charter.maxN / 32) ** 2);
        if (current.charter.constructionLimit < completeReservation) {
            return workspace.recordEnterpriseEvent(value, 'enterprise-budget-refused', {attempt: current.attempt,
                reservationBound: completeReservation});
        }
        const bundle = await buildFoundry({qualifyArtifact, maxN: current.charter.maxN});
        return workspace.recordEnterpriseEvent(value, 'enterprise-constructed', {...payload, bundle});
    }
    if (inspected.next === 'freeze') return workspace.recordEnterpriseEvent(value, 'enterprise-frozen', {...payload,
        freeze: await makeFreeze(current.charter, current.bundle, current.acceptedAt)});
    if (inspected.next === 'supply-future-tasks') return workspace.recordEnterpriseEvent(value, 'enterprise-tasks', {...payload,
        bank: await makeTaskBank(current.freeze, seed, current.charter.maxN, current.charter.taskLimit)});
    if (inspected.next === 'reserve-invocation') {
        const totalTreatmentReservation = current.bank.tasks.length * TREATMENTS.length * current.charter.perTaskLimit;
        const currentAdmissionReserve = completeConstructionWork(current.bundle);
        const result = await workspace.recordEnterpriseEvent(value, 'enterprise-run-reserved', {...payload,
            invocationId: 'invocation-' + crypto.randomUUID(), bankDigest: current.bank.digest, workLimit: current.charter.perTaskLimit,
            totalTreatmentReservation, currentAdmissionReserve,
            verificationReplayReserve: totalTreatmentReservation + currentAdmissionReserve});
        invocationLeases.add(result); return result;
    }
    if (inspected.next === 'reconcile-simulated-work') return workspace.recordEnterpriseEvent(value, 'enterprise-settled', {...payload,
        settlement: {status: 'SIMULATED_ONLY', currency: 'none', collectedCash: '0', externalSubmission: 'NOT_SUBMITTED',
            obligations: [], recordedWork: current.actualConstructionWork + current.futureSpent}});
    if (inspected.next === 'reserve-successor') {
        if (!current.future.runs.every(run => run.state === 'ACCEPTED')) {
            return workspace.recordEnterpriseEvent(value, 'enterprise-stopped', {attempt: current.attempt,
                reason: 'Rejected or inconclusive comparison retains all earlier outcomes and holds successor construction.', outcome: 'REJECTED'});
        }
        const result = await workspace.recordEnterpriseEvent(value, 'enterprise-successor-reserved', {attempt: current.attempt,
            parentFreezeDigest: current.freeze.digest, constructionReservation: current.charter.constructionLimit});
        successorLeases.add(result); return result;
    }
    if (inspected.next === 'construct-successor') {
        need(successorLeases.has(valueInput), 'Recovered successor construction needs reconciliation; no automatic retry.');
        successorLeases.delete(valueInput);
        const n = current.charter.maxN;
        const construction = await constructInverse(current.bundle.transforms.at(-1).envelope,
            current.bundle.envelopes, qualifyArtifact, {reference: 'inherited',
                convolutionDigest: current.bundle.convolution.envelope.digest,
                kernel: Array.from({length: n}, (_, i) => String(i ? 1 : n + 3))});
        return workspace.recordEnterpriseEvent(value, 'enterprise-successor', {...payload,
            construction, parentFreezeDigest: current.freeze.digest});
    }
    throw Error('Execution outcome is uncertain. Import its exact result or explicitly stop; it will not be retried automatically.');
}
export async function invokeReserved(valueInput, expectedSource) {
    need(invocationLeases.has(valueInput), 'This recovered or already attempted invocation requires exact-result reconciliation; no automatic retry.');
    invocationLeases.delete(valueInput);
    const value = copy(valueInput), source = copy(expectedSource), {current} = await state(value);
    need(current?.state === 'INVOCATION_RESERVED' && same(source, current.charter.source),
        'An exact persisted current-source invocation reservation is required.');
    const report = await evaluateFuture(current.bundle, current.freeze, current.bank, current.charter.perTaskLimit);
    return workspace.recordEnterpriseEvent(value, 'enterprise-invoked', {attempt: current.attempt,
        invocationId: current.invocation.invocationId, report});
}
export async function stop(valueInput, reason) {
    const value = copy(valueInput), {current} = await state(value);
    need(current, 'No active attempt to stop.');
    return workspace.recordEnterpriseEvent(value, 'enterprise-stopped', {attempt: current.attempt,
        reason, outcome: 'CANCELLED'});
}
