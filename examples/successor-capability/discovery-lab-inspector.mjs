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
/** Conservative bounds are checked before semantic work; absence of allowance is inconclusive. */
async function inspectCampaign(payload, {request, limits}, sources) {
    const start = performance.now();
    const resourceUsed = zero();
    contract.canonical(payload);
    contract.validateResources(limits);
    if (!['modelDigest', 'sourceDigest', 'evaluatorDigest'].every(key => sources[key] === request[key])) {
        return {accepted: false, resourceUsed, reasons: ['INSTALLED_SOURCE_MISMATCH']};
    }
    if (!exact(payload, ['schema', 'charter', 'result', 'ancestors'])
        || payload.schema !== 'discovery-lab-review-payload/v1'
        || !Array.isArray(payload.ancestors) || payload.ancestors.length > 7) {
        return {accepted: false, resourceUsed, reasons: ['UNSUPPORTED_CAMPAIGN_PAYLOAD']};
    }
    if (await contract.payloadDigest(payload.charter) !== request.charterDigest
        || await contract.payloadDigest({purpose: payload.charter.purpose}) !== request.purposeDigest) {
        return {accepted: false, resourceUsed, reasons: ['CHARTER_PURPOSE_BINDING_MISMATCH']};
    }
    const stageIndex = contract.STAGES.indexOf(request.stage);
    const bound = Object.fromEntries(contract.BINDING_KEYS.map(key => [key, request[key]]));
    const artifactDigests = (await artifacts.makeArtifacts(bound, payload.result))
        .slice(0, stageIndex).map(artifact => artifact.digest);
    if (contract.canonical(artifactDigests) !== contract.canonical(request.inputArtifacts)) {
        return {accepted: false, resourceUsed, reasons: ['INPUT_ARTIFACT_BINDING_MISMATCH']};
    }
    const chain = [...payload.ancestors, {charter: payload.charter, result: payload.result}];
    const required = zero();
    for (const item of chain) {
        if (!exact(item, ['charter', 'result'])) return {accepted: false, resourceUsed, reasons: ['INVALID_ANCESTOR']};
        const charter = runtime.validateCharter(item.charter);
        for (const key of ['acquisitions', 'search', 'checking', 'installations']) required[key] += charter.budget[key];
        required.storageBytes += runtime.REPORT_RESERVE_BYTES;
        required.memoryBytes = Math.max(required.memoryBytes, 500_000);
        required.workerCapacity = Math.max(required.workerCapacity, charter.workerCapacity);
    }
    if (contract.RESOURCE_KEYS.some(key => key !== 'elapsedMs' && required[key] > limits[key])) {
        return {accepted: false, resourceUsed, reasons: ['CONSERVATIVE_REPLAY_CHECK_INCOMPLETE']};
    }
    let parent = null;
    try {
        for (const item of chain) {
            const verdict = runtime.verifyCampaign(item.charter, item.result, {parent});
            if (!verdict.verified) return {accepted: false, resourceUsed, reasons: ['ANCESTRY_CHECK_INCOMPLETE']};
            add(resourceUsed, resourceVector(verdict.verificationResources));
            if (item !== chain.at(-1) && !verdict.accepted) {
                return {accepted: false, resourceUsed, reasons: ['ANCESTOR_NOT_ACCEPTED']};
            }
            parent = item.result;
        }
        const stage = payload.result.stages.find(value => value.kind === request.stage);
        const reasons = stage?.status === 'inconclusive' || stage?.status === 'paused' && payload.result.state === 'inconclusive'
            ? ['CAMPAIGN_SEARCH_TRUNCATED'] : stage?.status === 'accepted' ? [] : ['CURRENT_STAGE_REJECTED'];
        resourceUsed.elapsedMs = Math.ceil(performance.now() - start);
        return {accepted: stage?.status === 'accepted' && reasons.length === 0, resourceUsed, reasons};
    } catch (error) {
        if (error.verificationResources) add(resourceUsed, resourceVector(error.verificationResources));
        resourceUsed.elapsedMs = Math.ceil(performance.now() - start);
        return {accepted: false, resourceUsed, reasons: ['FINITE_EVIDENCE_REJECTED']};
    }
}

/** The host pins these identities from installed bytes, never from an imported request. */
export function createInspector(installedSources) {
    contract.canonical(installedSources);
    if (!exact(installedSources, ['modelDigest', 'sourceDigest', 'evaluatorDigest'])
        || !Object.values(installedSources).every(value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value))) {
        throw Error('Installed Discovery Lab source identities are required.');
    }
    const sources = Object.freeze({...installedSources});
    return (payload, options) => inspectCampaign(payload, options, sources);
}
