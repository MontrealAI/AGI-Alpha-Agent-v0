// SPDX-License-Identifier: Apache-2.0
// Public-software adapter contract. This module never evaluates imported source.
import {canonical, payloadDigest, validateWorkRequest, validateBindings, validateResources, BINDING_KEYS} from './discovery-lab-contract.mjs';
export const REAL_TASK_SCHEMA = 'successor-discovery-real-task/v1';
export const REAL_TASK_FAMILY = 'public-integer-affine-module/v1';
const copy = value => JSON.parse(canonical(value));
const need = (condition, message) => { if (!condition) throw Error(message); };
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const same = (left, right) => canonical(left) === canonical(right);
const integer = value => typeof value === 'string' && /^(?:0|-?[1-9][0-9]{0,31})$/.test(value);
const outputInteger = value => typeof value === 'string' && /^(?:0|-?[1-9][0-9]{0,63})$/.test(value);
const zero = () => ({acquisitions:0, search:0, checking:0, memoryBytes:0, storageBytes:0,
    workerCapacity:0, installations:0, elapsedMs:0});
const byteLength = value => new TextEncoder().encode(value).length;
function cumulative(checks, observation, checkerCharge) {
    const totals = Object.fromEntries(Object.keys(zero()).map(key => [key, 0n]));
    for (const item of [...checks, {observation, checkerCharge}]) {
        for (const key of Object.keys(totals)) totals[key] += BigInt(item.observation.resourceUsed[key]) + BigInt(item.checkerCharge[key]);
    }
    return Object.fromEntries(Object.entries(totals).map(([key, value]) => [key, value.toString()]));
}
const withinTotals = (totals, limits) => Object.keys(limits).every(key => BigInt(totals[key]) <= BigInt(limits[key]));
function proposalIdentity(record) {
    return Object.fromEntries(['schema', 'family', 'missionId', 'originHead', 'campaignDigest', 'bindings', 'workRequestDigest',
        'inputArtifacts', 'publicSource', 'dataScope', 'specification', 'resourceLimits', 'adapterSources']
        .map(key => [key, record[key]]));
}
function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
}
function trace(value) {
    need(Array.isArray(value) && value.length <= 64, 'Bounded observable trace required.');
    for (const [index, item] of value.entries()) {
        need(exact(item, ['sequence', 'action', 'inputDigest', 'outputDigest', 'summary'])
            && item.sequence === index && ['read-public-source', 'write-artifact', 'tool-call', 'intervention'].includes(item.action)
            && hash(item.inputDigest) && hash(item.outputDigest) && typeof item.summary === 'string'
            && item.summary.length > 0 && item.summary.length <= 500, 'Invalid observable tool trace.');
    }
}
function publicURL(value) {
    need(typeof value === 'string' && value.length <= 2048, 'Bounded public source URL required.');
    const url = new URL(value);
    need(url.protocol === 'https:' && url.href === value && !url.username && !url.password && !url.hash,
        'An exact HTTPS public-source reference is required.');
}
function specification(value) {
    need(exact(value, ['multiplier', 'offset', 'maxBatchRows']) && integer(value.multiplier) && integer(value.offset)
        && Number.isSafeInteger(value.maxBatchRows) && value.maxBatchRows > 0 && value.maxBatchRows <= 256,
        'Invalid bounded integer-affine specification.');
}
function sources(value) {
    need(exact(value, ['adapterSourceDigest', 'checkerSourceDigest'])
        && hash(value.adapterSourceDigest) && hash(value.checkerSourceDigest), 'Exact adapter/checker source identities required.');
}
function task(value, maxRows) {
    need(exact(value, ['id', 'inputs']) && typeof value.id === 'string' && /^[A-Za-z0-9_.:-]{1,128}$/.test(value.id)
        && Array.isArray(value.inputs) && value.inputs.length > 0 && value.inputs.length <= maxRows
        && value.inputs.every(integer), 'Invalid future public-software input.');
}

/** Bind a separate operational proposal to the existing typed request and mission history. */
export async function createRealTaskRecord(input) {
    // Capture the outer argument too; destructuring must not invoke accessor data.
    input = copy(input);
    const keys = ['workRequest', 'workspaceHead', 'campaignDigest', 'publicSource', 'specification', 'resourceLimits', 'adapterSources'];
    if (Object.hasOwn(input, 'missionId')) keys.push('missionId');
    need(exact(input, keys), 'Unsupported real-task proposal fields.');
    const request = await validateWorkRequest(input.workRequest);
    publicURL(input.publicSource); specification(input.specification); sources(input.adapterSources);
    need(hash(input.workspaceHead) && hash(input.campaignDigest), 'Existing mission head and campaign identity required.');
    const record = {schema:REAL_TASK_SCHEMA, family:REAL_TASK_FAMILY, missionId:request.missionId,
        workspaceHead:input.workspaceHead, originHead:input.workspaceHead, campaignDigest:input.campaignDigest,
        bindings:Object.fromEntries(BINDING_KEYS.map(key => [key, request[key]])),
        workRequest:request, workRequestDigest:await payloadDigest(request), inputArtifacts:[...request.inputArtifacts],
        publicSource:input.publicSource, dataScope:'public-nonpersonal-owner-declared',
        specification:input.specification, resourceLimits:validateResources(input.resourceLimits), adapterSources:input.adapterSources,
        artifact:null, taskBank:null, checks:[], operationalState:'NOT_RUN',
        operationalAcceptance:'qualified-model-tool-runtime-and-independent-operator-required',
        settlement:'not-performed', authority:'none'};
    record.proposalDigest = await payloadDigest(proposalIdentity(record));
    return freeze(await validateRealTaskRecord(record, input));
}

/** Producer input contains requirements, never evaluation answers or the future task bank. */
export async function realTaskProducerPacket(record) {
    record = await validateRealTaskRecord(record, record);
    return freeze({schema:'successor-discovery-real-task-producer/v1', family:record.family,
        bindings:record.bindings, workRequestDigest:record.workRequestDigest, proposalDigest:record.proposalDigest,
        publicSource:record.publicSource, specification:record.specification,
        deliverable:{format:'utf8-es-module', exportName:'transform', input:'array-of-canonical-decimal-integer-strings',
            output:'same-length-array-of-canonical-decimal-integer-strings', preserve:'order-and-duplicates',
            arithmetic:'exact-integer; output[i] = input[i] * multiplier + offset'},
        resourceLimits:record.resourceLimits, authority:'none'});
}

/** Capture executable bytes but never import/eval them. A digest is not runtime qualification. */
export async function freezeRealTaskArtifact(record, artifact) {
    const current = copy(record), captured = copy(artifact);
    await validateRealTaskRecord(current, current);
    need(current.artifact === null && current.taskBank === null, 'Artifact already frozen; use a new history-bound proposal.');
    need(exact(captured, ['moduleUtf8', 'environmentDigest', 'trace']) && typeof captured.moduleUtf8 === 'string'
        && byteLength(captured.moduleUtf8) > 0 && byteLength(captured.moduleUtf8) <= 128_000
        && hash(captured.environmentDigest), 'Bounded source bytes and frozen environment required.');
    trace(captured.trace);
    current.artifact = {...captured, proposalDigest:current.proposalDigest, moduleDigest:await payloadDigest({moduleUtf8:captured.moduleUtf8}),
        specificationDigest:await payloadDigest(current.specification),
        checkerSourceDigest:current.adapterSources.checkerSourceDigest,
        qualification:'captured-bytes-only; executable-not-invoked'};
    current.artifact.freezeDigest = await payloadDigest(current.artifact);
    return freeze(await validateRealTaskRecord(current, current));
}

/** Commit the entire future task bank after artifact freeze, before any output checks. */
export async function commitRealTaskBank(record, tasks) {
    const current = copy(record), captured = copy(tasks);
    await validateRealTaskRecord(current, current);
    need(current.artifact && current.taskBank === null && current.checks.length === 0,
        'Freeze artifact before supplying one complete future task bank.');
    need(Array.isArray(captured) && captured.length > 0 && captured.length <= 16,
        'Between one and sixteen future tasks required.');
    captured.forEach(item => task(item, current.specification.maxBatchRows));
    need(new Set(captured.map(item => item.id)).size === captured.length, 'Duplicate future task identifier.');
    const bank = {artifactFreezeDigest:current.artifact.freezeDigest, tasks:captured,
        scope:'public-protocol-inputs; not-secret-external-benchmark'};
    current.taskBank = {...bank, digest:await payloadDigest(bank)};
    return freeze(await validateRealTaskRecord(current, current));
}

/** Independent exact arithmetic checker; outputs remain unproven runtime observations. */
export async function checkRealTaskOutput(record, observation) {
    const current = copy(record), captured = copy(observation);
    await validateRealTaskRecord(current, current);
    need(current.taskBank && exact(captured, ['taskId', 'artifactFreezeDigest', 'outputs', 'trace', 'resourceUsed']),
        'Frozen task bank and complete observable result required.');
    need(captured.artifactFreezeDigest === current.artifact.freezeDigest, 'Stale or substituted executable artifact.');
    const selected = current.taskBank.tasks.find(item => item.id === captured.taskId);
    need(selected && !current.checks.some(item => item.taskId === captured.taskId), 'Absent task or duplicate result.');
    trace(captured.trace); validateResources(captured.resourceUsed);
    need(Array.isArray(captured.outputs) && captured.outputs.length === selected.inputs.length
        && captured.outputs.every(outputInteger), 'Bounded exact integer output required.');
    const multiplier = BigInt(current.specification.multiplier), offset = BigInt(current.specification.offset);
    // Expected values exist only inside this checker, never in the producer packet.
    const correct = selected.inputs.every((value, index) => BigInt(captured.outputs[index]) === BigInt(value) * multiplier + offset);
    const checkerCharge = {...zero(), checking:selected.inputs.length, memoryBytes:byteLength(canonical(captured))};
    const totals = cumulative(current.checks, captured, checkerCharge);
    const within = withinTotals(totals, current.resourceLimits);
    const check = {taskId:selected.id, proposalDigest:current.proposalDigest, artifactFreezeDigest:current.artifact.freezeDigest,
        taskBankDigest:current.taskBank.digest, observation:captured,
        status:!within ? 'inconclusive' : correct ? 'reference-output-matched' : 'rejected',
        verificationScope:'deterministic-contract-check; source-execution-and-observation-provenance-not-established',
        resourceAccounting:'reported-observation-untrusted; not-measured-runtime-cost',
        checkerCharge, cumulativeReportedAndCheckerUnitsExact:totals,
        budgetAccounting:'cumulative-reported-observations-plus-declared-checks; not-operational-pilot-cost',
        authority:'none'};
    check.digest = await payloadDigest(check);
    current.checks.push(check);
    return freeze(await validateRealTaskRecord(current, current));
}

/** Shape/hash checks cannot promote an imported attachment into operational acceptance. */
export async function validateRealTaskRecord(record, context = {}) {
    record = copy(record);
    const {workspaceHead, missionId, campaignDigest, adapterSources} = copy(context);
    need(exact(record, ['schema', 'family', 'missionId', 'workspaceHead', 'originHead', 'campaignDigest', 'bindings', 'workRequest', 'workRequestDigest',
        'inputArtifacts', 'publicSource', 'dataScope', 'specification', 'resourceLimits', 'adapterSources',
        'artifact', 'taskBank', 'checks', 'proposalDigest', 'operationalState', 'operationalAcceptance', 'settlement', 'authority'])
        && record.schema === REAL_TASK_SCHEMA && record.family === REAL_TASK_FAMILY, 'Unsupported real-task contract.');
    const request = await validateWorkRequest(record.workRequest);
    need(record.workRequestDigest === await payloadDigest(request)
        && same(record.bindings, Object.fromEntries(BINDING_KEYS.map(key => [key, request[key]])))
        && same(record.inputArtifacts, request.inputArtifacts), 'Original typed work request changed.');
    need(hash(record.originHead) && record.workspaceHead === record.originHead, 'Real-task proposal origin changed; reanchoring is not provisioned.');
    need(record.proposalDigest === await payloadDigest(proposalIdentity(record)), 'Real-task proposal identity changed.');
    validateBindings(record.bindings); validateResources(record.resourceLimits); specification(record.specification);
    sources(record.adapterSources); publicURL(record.publicSource);
    need(record.missionId === record.bindings.missionId && hash(record.workspaceHead) && hash(record.campaignDigest)
        && hash(record.workRequestDigest) && Array.isArray(record.inputArtifacts) && record.inputArtifacts.length <= 6
        && record.inputArtifacts.every(hash) && new Set(record.inputArtifacts).size === record.inputArtifacts.length,
        'Real-task mission/source binding mismatch.');
    need(workspaceHead === undefined || record.workspaceHead === workspaceHead, 'Real-task workspace head changed.');
    need(missionId === undefined || record.missionId === missionId, 'Real-task mission changed.');
    need(campaignDigest === undefined || record.campaignDigest === campaignDigest, 'Real-task campaign changed.');
    need(adapterSources === undefined || same(record.adapterSources, adapterSources), 'Real-task installed source changed.');
    need(record.dataScope === 'public-nonpersonal-owner-declared' && record.operationalState === 'NOT_RUN'
        && record.operationalAcceptance === 'qualified-model-tool-runtime-and-independent-operator-required'
        && record.settlement === 'not-performed' && record.authority === 'none', 'Imported operational authority is refused.');
    const artifact = record.artifact;
    if (artifact !== null) {
        need(exact(artifact, ['moduleUtf8', 'environmentDigest', 'trace', 'proposalDigest', 'moduleDigest', 'specificationDigest',
            'checkerSourceDigest', 'qualification', 'freezeDigest']) && typeof artifact.moduleUtf8 === 'string'
            && byteLength(artifact.moduleUtf8) > 0 && byteLength(artifact.moduleUtf8) <= 128_000 && hash(artifact.environmentDigest),
            'Invalid frozen public-software artifact.');
        trace(artifact.trace);
        need(artifact.proposalDigest === record.proposalDigest && artifact.moduleDigest === await payloadDigest({moduleUtf8:artifact.moduleUtf8})
            && artifact.specificationDigest === await payloadDigest(record.specification)
            && artifact.checkerSourceDigest === record.adapterSources.checkerSourceDigest
            && artifact.qualification === 'captured-bytes-only; executable-not-invoked', 'Frozen artifact bytes/context changed.');
        const {freezeDigest, ...frozen} = artifact;
        need(freezeDigest === await payloadDigest(frozen), 'Artifact freeze commitment mismatch.');
    }
    if (record.taskBank !== null) {
        const bank = record.taskBank;
        need(artifact && exact(bank, ['artifactFreezeDigest', 'tasks', 'scope', 'digest'])
            && bank.artifactFreezeDigest === artifact.freezeDigest && Array.isArray(bank.tasks)
            && bank.tasks.length > 0 && bank.tasks.length <= 16
            && bank.scope === 'public-protocol-inputs; not-secret-external-benchmark', 'Invalid future task commitment.');
        bank.tasks.forEach(item => task(item, record.specification.maxBatchRows));
        need(new Set(bank.tasks.map(item => item.id)).size === bank.tasks.length, 'Duplicate future task identifier.');
        const {digest, ...committed} = bank;
        need(digest === await payloadDigest(committed), 'Future task bank changed.');
    }
    need(Array.isArray(record.checks) && record.checks.length <= 16, 'Bounded check history required.');
    const checkedTasks = new Set();
    for (const check of record.checks) {
        need(record.taskBank && exact(check, ['taskId', 'proposalDigest', 'artifactFreezeDigest', 'taskBankDigest', 'observation', 'status',
            'verificationScope', 'resourceAccounting', 'checkerCharge', 'cumulativeReportedAndCheckerUnitsExact', 'budgetAccounting', 'authority', 'digest'])
            && !checkedTasks.has(check.taskId) && check.proposalDigest === record.proposalDigest && check.artifactFreezeDigest === artifact.freezeDigest
            && check.taskBankDigest === record.taskBank.digest && check.authority === 'none', 'Invalid or duplicate output check.');
        const selected = record.taskBank.tasks.find(item => item.id === check.taskId), observation = check.observation;
        need(selected && exact(observation, ['taskId', 'artifactFreezeDigest', 'outputs', 'trace', 'resourceUsed'])
            && observation.taskId === check.taskId && observation.artifactFreezeDigest === artifact.freezeDigest
            && Array.isArray(observation.outputs) && observation.outputs.length === selected.inputs.length
            && observation.outputs.every(outputInteger), 'Output check does not bind actual task inputs.');
        trace(observation.trace); validateResources(observation.resourceUsed); validateResources(check.checkerCharge);
        const expectedCharge = {...zero(), checking:selected.inputs.length, memoryBytes:byteLength(canonical(observation))};
        const priorChecks = record.checks.slice(0, checkedTasks.size);
        const totals = cumulative(priorChecks, observation, expectedCharge);
        const within = withinTotals(totals, record.resourceLimits);
        const correct = selected.inputs.every((value, index) => BigInt(observation.outputs[index])
            === BigInt(value) * BigInt(record.specification.multiplier) + BigInt(record.specification.offset));
        need(check.status === (!within ? 'inconclusive' : correct ? 'reference-output-matched' : 'rejected')
            && check.verificationScope === 'deterministic-contract-check; source-execution-and-observation-provenance-not-established'
            && check.resourceAccounting === 'reported-observation-untrusted; not-measured-runtime-cost'
            && same(check.checkerCharge, expectedCharge) && same(check.cumulativeReportedAndCheckerUnitsExact, totals)
            && check.budgetAccounting === 'cumulative-reported-observations-plus-declared-checks; not-operational-pilot-cost',
            'Imported output/check/cost status changed.');
        const {digest, ...report} = check;
        need(digest === await payloadDigest(report), 'Output check digest mismatch.');
        checkedTasks.add(check.taskId);
    }
    return record;
}
