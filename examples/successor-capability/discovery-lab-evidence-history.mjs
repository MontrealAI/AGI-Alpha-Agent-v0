// SPDX-License-Identifier: Apache-2.0
// Evidence is appended to the existing mission chain; imports grant no authority.
import * as contract from './discovery-lab-contract.mjs';
import * as future from './discovery-lab-future.mjs';
import {validateRealTaskRecord} from './discovery-lab-real-task.mjs';
import {makeReceiverContext, inspectReceiverReceipt} from './discovery-lab-receipts.mjs';
const copy = value => JSON.parse(contract.canonical(value));
const same = (a, b) => contract.canonical(a) === contract.canonical(b);
const need = (condition, message) => { if (!condition) throw Error(message); };
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
export const EVIDENCE_KINDS = Object.freeze(['future-freeze', 'future-task-bank', 'future-run-reserved',
    'future-run-stopped', 'future-evaluation', 'real-task-contract', 'receiver-receipt']);
export async function evidencePayload(campaignDigest, kind, record) {
    record = copy(record);
    need(EVIDENCE_KINDS.includes(kind), 'Unsupported attached evidence kind.');
    return {campaignDigest, kind, record, recordDigest: await contract.payloadDigest(record)};
}
export async function freezeRecord(campaign) {
    campaign = copy(campaign);
    const ancestors = [];
    for (let item = campaign.parent; item; item = item.parent) ancestors.unshift({charter: item.charter, result: item.result});
    return future.freezeCapability({bindings: campaign.bindings, charter: campaign.charter, result: campaign.result, ancestors});
}
export function freezeReference(capsule) {
    capsule = copy(capsule);
    need(capsule.status === 'frozen', 'Only an accepted frozen capability can enter the future-task protocol.');
    return {schema: 'discovery-lab-freeze-reference/v1', freezeDigest: capsule.digest, authority: false};
}
export async function inspectEvidence(state, event, context, chargeReplay = () => {}) {
    const payload = copy(event.payload);
    need(exact(payload, ['campaignDigest', 'kind', 'record', 'recordDigest'])
        && EVIDENCE_KINDS.includes(payload.kind)
        && payload.recordDigest === await contract.payloadDigest(payload.record), 'Attached evidence framing changed.');
    const campaign = state.campaigns.find(item => item.campaignDigest === payload.campaignDigest);
    need(campaign && campaign.bindings.missionId === context.missionId && campaign.state === 'accepted'
        && campaign.lineageQualified !== false && !state.active, 'Evidence needs an accepted completed campaign in this mission.');
    const attachments = state.attachments;
    need(!attachments.some(item => item.recordDigest === payload.recordDigest), 'Duplicate evidence cannot be charged or admitted twice.');
    let capsule = null, resolvedReservation = null, receipt = null;
    if (payload.kind === 'future-freeze') {
        try { capsule = await freezeRecord(campaign); }
        catch (error) { if (error.verificationResources || error.admissionReplay) chargeReplay(error.verificationResources || error.admissionReplay); throw error; }
        chargeReplay(capsule.admissionReplay);
        need(same(payload.record, freezeReference(capsule)), 'Frozen executable, evaluator, environment or obligations changed.');
        need(!attachments.some(item => item.kind === 'future-freeze' && item.campaignDigest === campaign.campaignDigest),
            'This campaign is already frozen for future tasks.');
    } else if (payload.kind === 'future-task-bank') {
        const frozen = attachments.find(item => item.kind === 'future-freeze'
            && item.campaignDigest === campaign.campaignDigest && item.record.freezeDigest === payload.record.freezeDigest);
        need(frozen, 'Freeze must be recorded before future task specifications.');
        capsule = frozen.capsule;
        need(!attachments.some(item => item.kind === 'future-task-bank' && item.campaignDigest === campaign.campaignDigest),
            'The complete future task bank is committed once before any treatment runs.');
        need(same(payload.record, await future.commitFutureTasks(capsule, payload.record.tasks)), 'Task bank commitment changed.');
    } else if (payload.kind === 'future-run-reserved') {
        const record = payload.record;
        const bank = attachments.find(item => item.kind === 'future-task-bank'
            && item.campaignDigest === campaign.campaignDigest && item.record.digest === record.taskBankDigest);
        need(bank && exact(record, ['schema', 'taskBankDigest', 'perTaskWorkLimit', 'attempt'])
            && record.schema === 'discovery-lab-future-reservation/v1'
            && Number.isSafeInteger(record.perTaskWorkLimit) && record.perTaskWorkLimit >= 0
            && !Object.is(record.perTaskWorkLimit, -0) && record.perTaskWorkLimit <= 10000000
            && /^future-[0-9a-f-]{36}$/.test(record.attempt), 'Future execution needs a bounded committed-bank reservation.');
        need(!attachments.some(item => item.kind === 'future-run-reserved' && item.record.attempt === record.attempt)
            && !attachments.some(item => item.kind === 'future-run-reserved' && item.campaignDigest === campaign.campaignDigest
                && !item.resolution)
            && !attachments.some(item => item.kind === 'future-evaluation' && item.campaignDigest === campaign.campaignDigest),
        'Retain or explicitly stop the earlier future reservation before more work.');
        capsule = bank.capsule;
    } else if (payload.kind === 'future-run-stopped') {
        const record = payload.record;
        const reserved = attachments.find(item => item.kind === 'future-run-reserved'
            && item.campaignDigest === campaign.campaignDigest && item.recordDigest === record.reservationDigest && !item.resolution);
        need(reserved && exact(record, ['schema', 'reservationDigest', 'reason', 'spent'])
            && record.schema === 'discovery-lab-future-stop/v1' && typeof record.reason === 'string'
            && record.reason.trim() && record.reason.length <= 1000 && record.spent === 'unknown-reservation-retained',
        'Future interruption must retain its unknown spent work and reservation.');
        resolvedReservation = reserved;
    } else if (payload.kind === 'future-evaluation') {
        const bank = attachments.find(item => item.kind === 'future-task-bank'
            && item.campaignDigest === campaign.campaignDigest && item.record.digest === payload.record.taskBankDigest);
        need(bank, 'Evaluation requires the earlier committed complete future task bank.');
        const reserved = attachments.find(item => item.kind === 'future-run-reserved'
            && item.campaignDigest === campaign.campaignDigest && !item.resolution);
        need(reserved && reserved.record.taskBankDigest === payload.record.taskBankDigest
            && reserved.record.perTaskWorkLimit === payload.record.perTaskWorkLimit,
        'Persist the exact task-bank execution reservation before running any alternative.');
        need(!attachments.some(item => item.kind === 'future-evaluation' && item.campaignDigest === campaign.campaignDigest),
            'A completed protocol cannot be replaced by a later favorable rerun. Start a separately identified successor.');
        try {
            const checked = await future.verifyFutureEvaluation(bank.capsule, bank.record, payload.record);
            chargeReplay(checked.verificationResources);
        } catch (error) {
            if (error.verificationResources || error.admissionReplay) chargeReplay(error.verificationResources || error.admissionReplay);
            throw error;
        }
        capsule = bank.capsule;
        resolvedReservation = reserved;
    } else if (payload.kind === 'receiver-receipt') {
        receipt = await inspectReceiverReceipt(payload.record, makeReceiverContext(campaign));
        const prior = attachments.filter(item => item.kind === 'receiver-receipt');
        need(!prior.some(item => item.receipt.receiptId === receipt.receiptId),
            'Duplicate semantic receipt cannot be admitted or charged twice.');
        // Fleet retains the original typed work reference; this consistency
        // guard does not create another commission or reserve its currency.
        const conflict = prior.find(item => item.receipt.commission.id === receipt.commission.id
            && item.receipt.commission.route === receipt.commission.route
            && !same(item.receipt.commission, receipt.commission));
        need(!conflict, receipt.inspectionKind === 'fleet-local-review' || conflict?.receipt.inspectionKind === 'fleet-local-review'
            ? 'Contradictory original work reference: Fleet review cannot change its retained request branch or obligations.'
            : 'A logical commission route cannot silently change currency or obligations.');
    } else {
        const record = await validateRealTaskRecord(payload.record,
            {workspaceHead: event.previous, missionId: context.missionId, campaignDigest: campaign.campaignDigest});
        const ancestors = [];
        for (let item = campaign.parent; item; item = item.parent) ancestors.unshift({charter: item.charter, result: item.result});
        need(same(record.bindings, campaign.bindings)
            && same(record.workRequest.payload, {schema: 'discovery-lab-review-payload/v1', charter: campaign.charter,
                result: campaign.result, ancestors})
            && same(record.inputArtifacts, campaign.artifacts.slice(0, contract.STAGES.indexOf(record.workRequest.stage))
                .map(item => item.digest)),
        'Real-task preparation must retain the exact campaign and source request.');
    }
    attachments.push({...payload, eventDigest: event.digest, capsule, receipt, authority: false,
        replayScope: 'Local replay is additional inspection work; wall time, organizational review and energy remain unmeasured.'});
    if (resolvedReservation) resolvedReservation.resolution = {kind: payload.kind, eventDigest: event.digest};
    return state;
}
