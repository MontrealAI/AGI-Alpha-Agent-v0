// SPDX-License-Identifier: Apache-2.0
/** Append-only capability-development records. No execution or payment authority. */
import * as protocol from '../../docs/assets/successor/engine.mjs';
import * as witness from './witness.mjs';
import * as discoveryHistory from './discovery-lab-history.mjs';

export const SCHEMA = 'successor-capability-workspace/v1';
export const LIMITS = Object.freeze({versions: 8, events: 24, bytes: 2_000_000});
export const canonical = protocol.canonical;
export const defaultExperiment = witness.defaultExperiment;
export const DEFAULT_BRIEF = Object.freeze({
    title: 'A reusable measurement instrument',
    unmetNeed: 'Explore many possible configurations without repeating a full response census for every decision.',
    problemFamily: 'Configuration response prediction, feasible-design screening and ranking candidate designs.',
    restrictiveAssumption: 'Each new configuration requires an unrelated full measurement.',
    constructionKind: 'instrument',
    proposedConstruction: 'Construct a calibrated low-interaction representation of a synthetic binary response system.',
    objective: 'Preserve exact responses and the resulting decisions within the declared synthetic function class.',
    constraints: 'Public synthetic inputs only; fixed bounded integer arithmetic; no model, network or payment calls.',
    constructionPlan: 'Declare the class, calibrate the basis, freeze the instrument, then check unused configurations.',
    acceptanceEvidence: 'All compared responses and downstream decisions must agree exactly. Retain any mismatch.',
    reusePlan: 'Reuse the frozen coefficients for a distinct threshold-screening and ranking task without recalibration.',
    scopeAssumptions: 'The synthetic world must respect the declared interaction-order bound. Physical qualification is absent.',
    beneficiariesHypothesis: 'Hypothesis: experimental teams with repeated configuration decisions. No customers established.',
    valueHypothesis: 'Unknown. A smaller calibration catalogue is not evidence of accepted value or superior engineering.',
    costHypothesis: 'Unknown monetary cost. Count abstract calibration observations and reuse queries separately.',
    financingHypothesis: 'Unknown construction funding, working capital and timing; no budget or purchase is approved.',
    adoptionEvidence: 'None. Voluntary adoption, contracts, revenue and profitability remain unestablished.'
});
const BRIEF_KEYS = Object.keys(DEFAULT_BRIEF);
const clone = value => JSON.parse(canonical(value));
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const fail = message => { throw Error(message); };
const equal = (left, right) => canonical(left) === canonical(right);
const idPattern = /^capability-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const verifiedExtendedWorkspaces = new WeakMap();
function freezeGraph(value) {
    if (value && typeof value === 'object') {
        for (const child of Object.values(value)) freezeGraph(child);
        if (!Object.isFrozen(value)) Object.freeze(value);
    }
    return value;
}

export function validateBrief(brief) {
    if (!exact(brief, BRIEF_KEYS)) fail('Unsupported capability brief fields.');
    for (const key of BRIEF_KEYS) {
        if (typeof brief[key] !== 'string' || !brief[key].trim()
            || brief[key].length > (key === 'title' ? 160 : 2000)) {
            fail(`Provide ${key} within its text limit.`);
        }
    }
    if (!['instrument', 'representation', 'experimental-architecture', 'productive-architecture', 'other']
        .includes(brief.constructionKind)) fail('Unsupported construction kind.');
    return clone(brief);
}

function specification(brief, experiment) {
    return {
        brief: validateBrief(brief), experiment: experiment === null ? null : witness.validateExperiment(experiment),
        witnessVersion: witness.WITNESS_VERSION,
        evidenceScope: 'synthetic-witness-only', briefAcceptance: 'not-evaluated',
        economicOutcome: 'not-evaluated', externalAuthority: false
    };
}

function exposureFor(versions, version, phase, report) {
    // Conservative across successors: syntactic or semantic world changes cannot reset case exposure.
    const priorMasks = new Set();
    for (const prior of versions) {
        if (!prior.experiment) continue;
        for (const name of ['development', 'heldout']) {
            const record = prior[name];
            if (!record) continue;
            for (const mask of record.construction.calibration.inputs) priorMasks.add(mask);
            for (const mask of record.report.evaluation_masks) priorMasks.add(mask);
        }
    }
    const repeatedMasks = report.evaluation_masks.filter(mask => priorMasks.has(mask));
    return {status: repeatedMasks.length ? 'previously-exposed-not-heldout' : 'fresh-within-record-not-protected',
        repeatedMasks, phase, policy: 'conservative-mask-history', publiclyInspectable: true,
        retuningDisclosed: versions.length > 1};
}

async function eventDigest(missionId, event) {
    return protocol.digest('capability-event', {missionId, sequence: event.sequence, kind: event.kind,
        previous: event.previous, payload: event.payload});
}

/** Retain one private frame for both semantic inspection and subsequent checked appends. */
async function inspectOwnedWorkspace(input) {
    const original = input;
    const fingerprint = discoveryHistory.validateHistoryData(input);
    const cached = verifiedExtendedWorkspaces.get(original);
    if (cached?.fingerprint === fingerprint) return cached;
    input = JSON.parse(fingerprint);
    if (input?.schema === discoveryHistory.EXTENDED_SCHEMA) freezeGraph(input);
    if (!exact(input, ['schema', 'missionId', 'revision', 'events', 'authority', 'paymentRoute'])
        || ![SCHEMA, discoveryHistory.EXTENDED_SCHEMA].includes(input.schema)
        || typeof input.missionId !== 'string' || !idPattern.test(input.missionId)
        || !Array.isArray(input.events) || input.events.length < 1 || input.events.length > LIMITS.events
        || input.revision !== input.events.length - 1 || !equal(input.authority, []) || input.paymentRoute !== 'none') {
        fail('Unsupported capability workspace or authority.');
    }
    const versions = [];
    const discovery = discoveryHistory.emptyDiscoveryState();
    let previous = null;
    for (const [sequence, event] of input.events.entries()) {
        if (!exact(event, ['sequence', 'kind', 'previous', 'payload', 'digest'])
            || event.sequence !== sequence || event.previous !== previous
            || event.digest !== await eventDigest(input.missionId, event)) fail('Capability history binding mismatch.');
        const payload = event.payload;
        if (event.kind === 'version') {
            if (!exact(payload, ['number', 'parent', 'reason', 'specification', 'frozenDigest'])
                || payload.number !== versions.length + 1 || versions.length >= LIMITS.versions
                || payload.parent !== (versions.length ? versions.at(-1).frozenDigest : null)
                || typeof payload.reason !== 'string' || !payload.reason.trim() || payload.reason.length > 2000) {
                fail('Invalid successor version lineage.');
            }
            const spec = payload.specification;
            if (!exact(spec, ['brief', 'experiment', 'witnessVersion', 'evidenceScope', 'briefAcceptance',
                'economicOutcome', 'externalAuthority'])
                || !equal(spec, specification(spec.brief, spec.experiment))) fail('Incompatible capability specification.');
            const frozenDigest = await protocol.digest('capability-specification', spec);
            if (payload.frozenDigest !== frozenDigest) fail('Frozen objective or construction changed.');
            versions.push({number: payload.number, parent: payload.parent, reason: payload.reason,
                brief: clone(spec.brief), experiment: clone(spec.experiment), frozenDigest,
                development: null, heldout: null, inheritedEvidence: 'historical-only',
                briefAcceptance: 'not-evaluated', economicOutcome: 'not-evaluated', witnessAcceptance: 'not-evaluated'});
        } else if (event.kind === 'evaluation') {
            const version = versions.at(-1);
            if (!version || !exact(payload, ['number', 'phase', 'frozenDigest', 'construction', 'report', 'exposure'])
                || payload.number !== version.number || payload.frozenDigest !== version.frozenDigest
                || !['development', 'heldout'].includes(payload.phase) || version[payload.phase]
                || version.experiment === null || (payload.phase === 'heldout' && !version.development)) {
                fail('Evaluation does not belong to the active frozen capability.');
            }
            const construction = payload.phase === 'development'
                ? witness.construct(version.experiment) : version.development.construction;
            if (!equal(payload.construction, construction)) fail('Construction does not match the frozen instrument.');
            const report = witness.evaluateConstruction(version.experiment, construction, payload.phase);
            if (!equal(payload.report, report)) fail('Unsupported evaluation claim or incompatible evidence.');
            if (!equal(payload.exposure, exposureFor(versions, version, payload.phase, report))) {
                fail('Prior exposure cannot be relabeled as held-out evidence.');
            }
            version[payload.phase] = clone(payload);
            version.witnessAcceptance = [version.development, version.heldout].some(record => record?.report.verdict === 'fail')
                ? 'fail' : version.development && version.heldout ? 'pass' : 'incomplete';
        } else if (discoveryHistory.EVENT_KINDS.includes(event.kind)
            && input.schema === discoveryHistory.EXTENDED_SCHEMA) {
            if (!versions.length) fail('Discovery Lab needs a frozen capability version.');
            await discoveryHistory.inspectDiscoveryEvent(discovery, event,
                {missionId: input.missionId, version: versions.at(-1).number});
        } else fail('Unsupported capability event.');
        previous = event.digest;
    }
    if (!versions.length) fail('Capability version is missing.');
    const inspection = {versions, latest: versions.at(-1), head: previous, discovery};
    const checked = {fingerprint, workspace: input, inspection};
    if (input.schema === discoveryHistory.EXTENDED_SCHEMA) {
        freezeGraph(inspection);
        verifiedExtendedWorkspaces.set(original, checked);
        verifiedExtendedWorkspaces.set(input, checked);
    }
    return checked;
}

/** Recompute all admitted synthetic evidence, not just its hash. Imports grant no trust. */
export async function inspectWorkspace(input) {
    return (await inspectOwnedWorkspace(input)).inspection;
}

async function append(workspace, kind, payload) {
    if (workspace.events.length >= LIMITS.events) fail('History capacity reached; preserve this complete workspace.');
    const next = clone(workspace), event = {sequence: next.events.length, kind,
        previous: next.events.at(-1)?.digest || null, payload: clone(payload)};
    event.digest = await eventDigest(next.missionId, event);
    next.events.push(event);
    next.revision = next.events.length - 1;
    return (await inspectOwnedWorkspace(next)).workspace;
}

async function versionPayload(number, parent, brief, experiment, reason) {
    const spec = specification(brief, experiment);
    return {number, parent, reason, specification: spec,
        frozenDigest: await protocol.digest('capability-specification', spec)};
}

export async function createWorkspace(brief = DEFAULT_BRIEF, experiment = null) {
    const workspace = {schema: SCHEMA, missionId: 'capability-' + crypto.randomUUID(), revision: -1,
        events: [], authority: [], paymentRoute: 'none'};
    return append(workspace, 'version', await versionPayload(1, null, brief, experiment, 'Initial frozen proposal'));
}

export async function addSuccessor(workspace, brief, experiment, reason) {
    brief = JSON.parse(discoveryHistory.validateHistoryData(brief));
    experiment = JSON.parse(discoveryHistory.validateHistoryData(experiment));
    const {workspace: owned, inspection: {latest, versions}} = await inspectOwnedWorkspace(workspace);
    if (versions.length >= LIMITS.versions) fail('Version capacity reached; preserve this complete workspace.');
    if (equal(latest.brief, brief) && equal(latest.experiment, experiment)) {
        fail('A successor needs an explicit change to the proposal or experiment; prior evidence stays historical.');
    }
    return append(owned, 'version', await versionPayload(latest.number + 1, latest.frozenDigest,
        brief, experiment, reason));
}

export async function recordEvaluation(workspace, phase) {
    const {workspace: owned, inspection: {latest, versions}} = await inspectOwnedWorkspace(workspace);
    if (!['development', 'heldout'].includes(phase)) fail('Unsupported evaluation phase.');
    if (latest.experiment === null) fail('This proposal has no implemented evaluator. No capability has been executed.');
    if (latest[phase]) fail('This version already contains that evaluation. Retuning requires a new successor.');
    if (phase === 'heldout' && !latest.development) fail('Construct and evaluate development before held-out reuse.');
    const construction = phase === 'development'
        ? witness.construct(latest.experiment) : latest.development.construction;
    const report = witness.evaluateConstruction(latest.experiment, construction, phase);
    return append(owned, 'evaluation', {number: latest.number, phase, frozenDigest: latest.frozenDigest,
        construction, report, exposure: exposureFor(versions, latest, phase, report)});
}

export function parseExperiment(text) {
    return witness.validateExperiment(clone(protocol.parseBounded(text)));
}

export async function parseWorkspace(text) {
    const value = clone(protocol.parseBounded(text));
    const {workspace: owned} = await inspectOwnedWorkspace(value);
    return owned.schema === discoveryHistory.EXTENDED_SCHEMA ? owned : clone(owned);
}

/** Add a checked event to the existing hash chain; prior v1 events retain exact bytes. */
export async function recordDiscoveryEvent(workspace, kind, payload) {
    payload = JSON.parse(discoveryHistory.validateHistoryData(payload));
    const {workspace: owned} = await inspectOwnedWorkspace(workspace);
    if (!discoveryHistory.EVENT_KINDS.includes(kind)) fail('Unsupported Discovery Lab event.');
    const next = clone(owned);
    next.schema = discoveryHistory.EXTENDED_SCHEMA;
    return append(next, kind, payload);
}
