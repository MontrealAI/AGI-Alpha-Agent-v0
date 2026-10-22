// SPDX-License-Identifier: Apache-2.0
// Installed semantic adapter for local review; never supplied by a request or evaluated from text.
import * as runtime from './discovery-lab.mjs';
import * as contract from './discovery-lab-contract.mjs';
import * as artifacts from './discovery-lab-artifacts.mjs';
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const zero = () => Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 0]));
function add(target, source) {
    for (const [key, value] of Object.entries(source)) {
        target[key] = ['memoryBytes', 'workerCapacity'].includes(key) ? Math.max(target[key], value) : target[key] + value;
    }
}
export function resourceVector(resources, elapsedMs = 0) {
    return contract.validateResources({acquisitions: resources.acquisitions, search: resources.search,
        checking: resources.checking, memoryBytes: resources.memoryWords * 8,
        storageBytes: resources.storageBytes, workerCapacity: resources.workerSlots,
        installations: resources.installations, elapsedMs});
}
/**
 * Checking includes one declared fixed inspection charge, not measured primitive instructions.
 * Memory includes four encoded UTF-8 footprints per owned canonical snapshot (text, encoding,
 * immutable copy and validation copy), plus finite verifier words. This is not VM heap usage.
 * Elapsed is a measured soft deadline checked before/between synchronous replays and at return;
 * it does not preempt a running replay. Every refusal retains known current-attempt charges.
 */
async function inspectCampaign(payload, options, sources) {
    const start = performance.now();
    const resourceUsed = zero();
    resourceUsed.checking = contract.DISCOVERY_LAB_INSPECTION_CHECKS;
    let effective = null, snapshotMemory = 0, replayStarted = false;
    const own = value => {
        const text = contract.canonical(value);
        snapshotMemory += 4 * new TextEncoder().encode(text).length;
        resourceUsed.memoryBytes = snapshotMemory;
        return JSON.parse(text);
    };
    const finish = (accepted, reasons) => {
        const result = {accepted, resourceUsed, reasons: [...reasons]};
        resourceUsed.elapsedMs = Math.max(0, Math.ceil(performance.now() - start));
        if (effective) {
            if (effective.elapsedMs === 0 || resourceUsed.elapsedMs > effective.elapsedMs) {
                result.accepted = false;
                if (!result.reasons.includes('ELAPSED_REPLAY_CHECK_INCOMPLETE')) result.reasons.push('ELAPSED_REPLAY_CHECK_INCOMPLETE');
            }
            if (contract.RESOURCE_KEYS.some(key => key !== 'elapsedMs' && resourceUsed[key] > effective[key])) {
                result.accepted = false; result.reasons.push('INSPECTION_RESOURCE_BUDGET_EXHAUSTED');
            }
        }
        return result;
    };
    const addReplay = resources => {
        const used = resourceVector(resources);
        used.memoryBytes += snapshotMemory;
        add(resourceUsed, used);
    };
    try {
        let {request, limits} = options;
        // Capture all caller-owned data synchronously before the first digest await.
        effective = contract.validateResources(own(limits));
        if (effective.elapsedMs === 0 || resourceUsed.checking > effective.checking
            || resourceUsed.memoryBytes > effective.memoryBytes) {
            return finish(false, ['INSPECTION_PREFLIGHT_CHECK_INCOMPLETE']);
        }
        const ownedRequest = own(request), ownedPayload = own(payload);
        if (resourceUsed.memoryBytes > effective.memoryBytes) return finish(false, ['INSPECTION_PREFLIGHT_CHECK_INCOMPLETE']);
        request = await contract.validateWorkRequest(ownedRequest);
        payload = ownedPayload;
        if (contract.RESOURCE_KEYS.some(key => effective[key] > request.resourceLimits[key])) {
            return finish(false, ['EFFECTIVE_LIMITS_EXCEED_COMMITMENT']);
        }
        if (contract.canonical(payload) !== contract.canonical(request.payload)) {
            return finish(false, ['PAYLOAD_COMMITMENT_MISMATCH']);
        }
        if (!['modelDigest', 'sourceDigest', 'evaluatorDigest'].every(key => sources[key] === request[key])) {
            return finish(false, ['INSTALLED_SOURCE_MISMATCH']);
        }
        if (!exact(payload, ['schema', 'charter', 'result', 'ancestors'])
            || payload.schema !== 'discovery-lab-review-payload/v1'
            || !Array.isArray(payload.ancestors) || payload.ancestors.length > 7) {
            return finish(false, ['UNSUPPORTED_CAMPAIGN_PAYLOAD']);
        }
        if (await contract.payloadDigest(payload.charter) !== request.charterDigest
            || await contract.payloadDigest({purpose: payload.charter.purpose}) !== request.purposeDigest) {
            return finish(false, ['CHARTER_PURPOSE_BINDING_MISMATCH']);
        }
        const stageIndex = contract.STAGES.indexOf(request.stage);
        const bound = Object.fromEntries(contract.BINDING_KEYS.map(key => [key, request[key]]));
        const currentArtifacts = own(await artifacts.makeArtifacts(bound, payload.result));
        const artifactDigests = currentArtifacts.slice(0, stageIndex).map(artifact => artifact.digest);
        if (contract.canonical(artifactDigests) !== contract.canonical(request.inputArtifacts)) {
            return finish(false, ['INPUT_ARTIFACT_BINDING_MISMATCH']);
        }
        const chain = [...payload.ancestors, {charter: payload.charter, result: payload.result}];
        const required = zero();
        required.checking = contract.DISCOVERY_LAB_INSPECTION_CHECKS;
        required.memoryBytes = snapshotMemory + 500_000;
        for (const item of chain) {
            if (!exact(item, ['charter', 'result'])) return finish(false, ['INVALID_ANCESTOR']);
            const charter = runtime.validateCharter(item.charter);
            for (const key of ['acquisitions', 'search', 'checking', 'installations']) required[key] += charter.budget[key];
            required.storageBytes += runtime.REPORT_RESERVE_BYTES;
            required.workerCapacity = Math.max(required.workerCapacity, charter.workerCapacity);
        }
        if (contract.RESOURCE_KEYS.some(key => key !== 'elapsedMs' && required[key] > effective[key])) {
            return finish(false, ['CONSERVATIVE_REPLAY_CHECK_INCOMPLETE']);
        }
        if (Math.ceil(performance.now() - start) >= effective.elapsedMs) {
            return finish(false, ['ELAPSED_REPLAY_CHECK_INCOMPLETE']);
        }
        let parent = null;
        for (const [index, item] of chain.entries()) {
            if (index > 0 && Math.ceil(performance.now() - start) >= effective.elapsedMs) {
                return finish(false, ['ELAPSED_REPLAY_CHECK_INCOMPLETE']);
            }
            replayStarted = true;
            const verdict = runtime.verifyCampaign(item.charter, item.result, {parent});
            addReplay(verdict.verificationResources);
            if (!verdict.verified) return finish(false, ['ANCESTRY_CHECK_INCOMPLETE']);
            if (index !== chain.length - 1 && !verdict.accepted) return finish(false, ['ANCESTOR_NOT_ACCEPTED']);
            parent = item.result;
        }
        const stage = payload.result.stages.find(value => value.kind === request.stage);
        const reasons = stage?.status === 'inconclusive' || stage?.status === 'paused' && payload.result.state === 'inconclusive'
            ? ['CAMPAIGN_SEARCH_TRUNCATED'] : stage?.status === 'accepted' ? [] : ['CURRENT_STAGE_REJECTED'];
        return finish(stage?.status === 'accepted' && reasons.length === 0, reasons);
    } catch (error) {
        // Only trusted finite replay can supply work counters; no diagnostic getter is invoked.
        const descriptor = replayStarted && Object.getOwnPropertyDescriptor(error, 'verificationResources');
        if (descriptor && Object.hasOwn(descriptor, 'value')) addReplay(descriptor.value);
        return finish(false, [replayStarted ? 'FINITE_EVIDENCE_REJECTED' : 'INVALID_WORK_REQUEST']);
    }
}

/** The host pins these identities from installed bytes, never from an imported request. */
export function createInspector(installedSources) {
    installedSources = JSON.parse(contract.canonical(installedSources));
    if (!exact(installedSources, ['modelDigest', 'sourceDigest', 'evaluatorDigest'])
        || !Object.values(installedSources).every(value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value))) {
        throw Error('Installed Discovery Lab source identities are required.');
    }
    const sources = Object.freeze({...installedSources});
    return (payload, options) => inspectCampaign(payload, options, sources);
}
