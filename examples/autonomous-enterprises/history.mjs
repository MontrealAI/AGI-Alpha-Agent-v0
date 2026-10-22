// SPDX-License-Identifier: Apache-2.0
import {copy, same, need, exact, hash, integer, validateCharter, makeFreeze, makeTaskBank,
    digest, completeConstructionWork, chargeReplay, additionalCheckingWork, noteFailedReplay} from './protocol.mjs';
import {qualifyArtifact, verifyBundle} from './checker.mjs';
import {verifyFuture} from './future.mjs';
import {TREATMENTS} from './future.mjs';

export const EVENT_KINDS = Object.freeze(['enterprise-started', 'enterprise-constructed', 'enterprise-frozen',
    'enterprise-tasks', 'enterprise-run-reserved', 'enterprise-invoked', 'enterprise-settled',
    'enterprise-successor-reserved', 'enterprise-successor', 'enterprise-budget-refused', 'enterprise-stopped']);
export function emptyState() { return {attempts: [], active: null}; }
export async function inspectEvent(state, event, context) {
    const payload = copy(event.payload);
    if (event.kind === 'enterprise-started') {
        need(exact(payload, ['attempt', 'charter']) && /^enterprise-[0-9a-f-]{36}$/.test(payload.attempt)
            && !state.active && !state.attempts.some(row => row.attempt === payload.attempt
                || row.unresolvedReservation || row.unknownSpent || row.state === 'INVOCATION_RESERVED'),
        'An enterprise attempt needs a unique identity and no unresolved predecessor.');
        const charter = validateCharter(payload.charter);
        const row = {attempt: payload.attempt, charter, missionId: context.missionId, version: context.version,
            state: 'RESERVED', events: [event.digest], reservation: charter.constructionLimit,
            actualConstructionWork: null, unknownSpent: true, authority: []};
        state.attempts.push(row); state.active = row; return state;
    }
    const row = state.active;
    need(row && payload.attempt === row.attempt && row.version === context.version,
        'Enterprise event has no current mission/version-bound reservation.');
    if (event.kind === 'enterprise-constructed') {
        need(exact(payload, ['attempt', 'bundle']) && row.state === 'RESERVED', 'Construct exactly once after reserving.');
        let proof;
        try { proof = await verifyBundle(payload.bundle); }
        catch (error) { noteFailedReplay(); throw error; }
        const work = completeConstructionWork(payload.bundle);
        chargeReplay('bundleReplayWork', proof.currentReplayWork);
        need(proof.currentReplayWork <= row.charter.admissionLimit, 'Current construction admission allowance exceeded.');
        need(payload.bundle.maxN === row.charter.maxN, 'Construction dimension differs from the charter.');
        row.bundle = payload.bundle; row.bundleProof = proof; row.actualConstructionWork = work;
        row.unknownSpent = false; row.state = 'ACCEPTED_CONSTRUCTION'; row.acceptedAt = event.digest;
        if (work > row.charter.constructionLimit) {
            row.state = 'INCONCLUSIVE'; row.reason = 'Construction allowance exceeded; all receipts retained.';
            state.active = null;
        }
    } else if (event.kind === 'enterprise-frozen') {
        need(exact(payload, ['attempt', 'freeze']) && row.state === 'ACCEPTED_CONSTRUCTION', 'Accept before freezing.');
        need(same(payload.freeze, await makeFreeze(row.charter, row.bundle, row.acceptedAt)),
            'Executable, checker, source, environment or obligations changed at freeze.');
        row.freeze = payload.freeze; row.state = 'FROZEN';
    } else if (event.kind === 'enterprise-tasks') {
        need(exact(payload, ['attempt', 'bank']) && row.state === 'FROZEN', 'Freeze before generating future inputs.');
        need(same(payload.bank, await makeTaskBank(row.freeze, payload.bank.seed, row.charter.maxN,
            row.charter.taskLimit)), 'Future task bank differs from its post-freeze commitment.');
        row.bank = payload.bank; row.state = 'TASKS_COMMITTED';
    } else if (event.kind === 'enterprise-run-reserved') {
        need(exact(payload, ['attempt', 'invocationId', 'bankDigest', 'workLimit', 'totalTreatmentReservation',
            'currentAdmissionReserve', 'verificationReplayReserve']) && row.state === 'TASKS_COMMITTED'
            && /^invocation-[0-9a-f-]{36}$/.test(payload.invocationId) && payload.bankDigest === row.bank.digest
            && payload.workLimit === row.charter.perTaskLimit
            && payload.totalTreatmentReservation === row.bank.tasks.length * TREATMENTS.length * payload.workLimit
            && payload.currentAdmissionReserve === completeConstructionWork(row.bundle)
            && payload.verificationReplayReserve === payload.totalTreatmentReservation + payload.currentAdmissionReserve
            && payload.verificationReplayReserve <= row.charter.admissionLimit,
        'Reserve every treatment and current verification, separately from construction.');
        row.invocation = payload; row.state = 'INVOCATION_RESERVED'; row.futureSpent = 'unknown-reservation-retained';
    } else if (event.kind === 'enterprise-invoked') {
        need(exact(payload, ['attempt', 'invocationId', 'report']) && row.state === 'INVOCATION_RESERVED'
            && payload.invocationId === row.invocation.invocationId
            && payload.report.perTaskLimit === row.invocation.workLimit, 'Invocation does not match its reservation.');
        try { row.futureProof = await verifyFuture(row.bundle, row.freeze, row.bank, payload.report); }
        catch (error) { noteFailedReplay(); throw error; }
        need(row.futureProof.currentReplayWork <= row.charter.admissionLimit, 'Current future verification allowance exceeded.');
        row.future = payload.report; row.futureSpent = payload.report.lineage.knownFutureTreatmentWork
            + payload.report.currentBundleAdmissionWork;
        row.state = 'INVOCATION_RECONCILED';
    } else if (event.kind === 'enterprise-settled') {
        need(exact(payload, ['attempt', 'settlement']) && row.state === 'INVOCATION_RECONCILED'
            && same(payload.settlement, {status: 'SIMULATED_ONLY', currency: 'none', collectedCash: '0',
                externalSubmission: 'NOT_SUBMITTED', obligations: [],
                recordedWork: row.actualConstructionWork + row.futureSpent}),
        'Only explicit local simulated work reconciliation is provisioned.');
        row.settlement = payload.settlement; row.state = 'READY_FOR_SUCCESSOR';
    } else if (event.kind === 'enterprise-successor-reserved') {
        need(exact(payload, ['attempt', 'parentFreezeDigest', 'constructionReservation'])
            && row.state === 'READY_FOR_SUCCESSOR' && payload.parentFreezeDigest === row.freeze.digest
            && payload.constructionReservation === row.charter.constructionLimit
            && row.future.runs.every(run => run.state === 'ACCEPTED'),
        'Reserve the changed-kernel construction only after every retained future outcome qualifies.');
        row.successorReservation = payload; row.state = 'SUCCESSOR_RESERVED'; row.successorSpent = 'unknown-reservation-retained';
    } else if (event.kind === 'enterprise-successor') {
        need(exact(payload, ['attempt', 'construction', 'parentFreezeDigest']) && row.state === 'SUCCESSOR_RESERVED'
            && payload.parentFreezeDigest === row.freeze.digest, 'Successor needs the accepted frozen parent and reconciled obligations.');
        need(row.future.runs.every(run => run.state === 'ACCEPTED'), 'A rejected or inconclusive comparison remains visible; successor acceptance is held.');
        const child = payload.construction;
        need(child.state === 'ACCEPTED' && child.envelope.artifact.kind === 'inverse', 'Construct a checked successor inverse.');
        const kernel = Array.from({length: row.charter.maxN}, (_, i) => String(i ? 1 : row.charter.maxN + 3));
        need(same(child.envelope.artifact.ast.kernel, kernel), 'Successor must implement the declared changed kernel.');
        const convolution = row.bundle.convolution.envelope.digest;
        need(child.envelope.digest === await digest(child.envelope.artifact), 'Successor executable bytes changed.');
        const checked = await qualifyArtifact(child.envelope.artifact, row.bundle.envelopes,
            {reference: 'inherited', convolutionDigest: convolution});
        chargeReplay('successorReplayWork', checked.totalWork + additionalCheckingWork(checked));
        need(checked.totalWork + additionalCheckingWork(checked) <= row.charter.admissionLimit,
            'Current successor admission allowance exceeded.');
        need(checked.accepted && same(checked, child.verification)
            && child.constructionWork === row.bundle.transforms.at(-1).envelope.artifact.operatingWork + row.charter.maxN
            && child.totalWork === child.constructionWork + checked.totalWork
            , 'Successor qualification or work receipts changed.');
        const observedSuccessorWork = child.totalWork + additionalCheckingWork(child.verification);
        row.successorSpent = observedSuccessorWork;
        row.successor = {construction: child, parentFreezeDigest: row.freeze.digest,
            observedSuccessorWork, lineageWork: row.actualConstructionWork + row.futureSpent + observedSuccessorWork,
            retainedArtifactDigests: [...row.freeze.artifactDigests, child.envelope.digest],
            oldObligations: 'Original artifact bytes and complete certificates retained; changed-kernel inverse checked separately',
            externalApproval: false};
        row.state = observedSuccessorWork > row.charter.constructionLimit ? 'INCONCLUSIVE' : 'SUCCESSOR_ACCEPTED_LOCAL';
        if (row.state === 'INCONCLUSIVE') row.reason = 'Successor allowance exceeded; its receipts and all previous outcomes remain retained.';
        state.active = null;
    } else if (event.kind === 'enterprise-budget-refused') {
        const bound = Math.ceil(2_000_000 * (row.charter.maxN / 32) ** 2);
        need(exact(payload, ['attempt', 'reservationBound']) && row.state === 'RESERVED'
            && payload.reservationBound === bound && row.charter.constructionLimit < bound,
        'Release an unused reservation only for an established preflight budget refusal.');
        row.state = 'INCONCLUSIVE'; row.reason = 'Conservative construction allowance unavailable; no production started.';
        row.unknownSpent = false; row.actualConstructionWork = 0; row.unresolvedReservation = false; state.active = null;
    } else if (event.kind === 'enterprise-stopped') {
        need(exact(payload, ['attempt', 'reason', 'outcome']) && typeof payload.reason === 'string'
            && payload.reason.trim() && payload.reason.length <= 1000
            && ['INCONCLUSIVE', 'REJECTED', 'CANCELLED'].includes(payload.outcome), 'Retain a bounded explicit stop reason.');
        row.stoppedFrom = row.state; row.state = payload.outcome; row.reason = payload.reason;
        row.unresolvedReservation = row.unknownSpent || row.futureSpent === 'unknown-reservation-retained'
            || row.successorSpent === 'unknown-reservation-retained'; state.active = null;
    } else throw Error('Unsupported enterprise event.');
    row.events.push(event.digest); return state;
}
export function summary(state) {
    return copy({attempts: state.attempts.map(row => ({attempt: row.attempt, state: row.state,
        missionId: row.missionId, constructionWork: row.actualConstructionWork,
        freezeDigest: row.freeze?.digest || null, future: row.future?.runs.map(run => ({task: run.taskId,
            treatment: run.treatment, state: run.state, path: run.path, work: run.totalWork || 0})) || [],
        successor: row.successor || null, unknownSpent: row.unknownSpent,
        unresolvedReservation: row.unresolvedReservation || row.state === 'INVOCATION_RESERVED',
        reason: row.reason || null})), activeAttempt: state.active?.attempt || null,
        operationalPilot: 'NOT_RUN', settlement: 'SIMULATED_ONLY', authority: []});
}
