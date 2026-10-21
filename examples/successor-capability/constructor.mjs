// SPDX-License-Identifier: Apache-2.0
/** Finite, cost-ordered construction over public apparatus semantics only. */
import * as runtime from './typed-runtime.mjs';
import * as checker from './independent-checker.mjs';

export const CONSTRUCTOR_VERSION = 'out-evolve-constructor/v1';
export const SEARCH_SCHEMA = 'out-evolve-search/v1';
export const SEARCH_TOKEN_SCHEMA = 'out-evolve-search-token/v1';
export const MAX_SEARCH_TOKEN_BYTES = 2000000;
export const DEFAULT_BUDGET = Object.freeze({maxStates: 20000, maxProgramSize: 12,
    maxCost: 1000000, maxMemoryStates: 20000, dominance: true});
const trusted = new WeakMap();
const checkpointVersions = new WeakMap();
const freshTokens = new WeakMap();
const clone = value => JSON.parse(JSON.stringify(value));
const equal = (a, b) => canonical(a) === canonical(b);
const reject = message => { throw new TypeError(message); };

function trustCheckpoint(checkpoint) {
    const fingerprint = canonical(checkpoint);
    if (trusted.get(checkpoint) !== fingerprint) {
        trusted.set(checkpoint, fingerprint);
        checkpointVersions.set(checkpoint, {});
    }
    return checkpoint;
}

export function canonical(value) {
    const active = new Set();
    let count = 0;
    const visit = (item, depth) => {
        if (++count > 2000000 || depth > 64) reject('Search data exceeds structural bounds.');
        if (item === null || typeof item === 'boolean' || typeof item === 'string') return JSON.stringify(item);
        if (typeof item === 'number') {
            if (!Number.isFinite(item) || Object.is(item, -0)) reject('Unsafe search numeric value.');
            return JSON.stringify(item);
        }
        if (!item || typeof item !== 'object' || active.has(item)) reject('Search requires finite plain JSON.');
        active.add(item);
        let result;
        if (Array.isArray(item)) {
            if (Object.getPrototypeOf(item) !== Array.prototype || Reflect.ownKeys(item).length !== item.length + 1) {
                reject('Search array has additional or missing fields.');
            }
            result = '[' + Array.from({length: item.length}, (_, index) => {
                const descriptor = Object.getOwnPropertyDescriptor(item, String(index));
                if (!descriptor || !Object.hasOwn(descriptor, 'value') || !descriptor.enumerable) {
                    reject('Search array accessor rejected.');
                }
                return visit(descriptor.value, depth + 1);
            }).join(',') + ']';
        } else {
            if (Object.getPrototypeOf(item) !== Object.prototype) reject('Search requires plain objects.');
            if (Reflect.ownKeys(item).length !== Object.keys(item).length) reject('Search has hidden object fields.');
            result = '{' + Object.keys(item).sort().map(key => {
                const d = Object.getOwnPropertyDescriptor(item, key);
                if (!d || !Object.hasOwn(d, 'value') || !d.enumerable) reject('Search data accessor rejected.');
                return JSON.stringify(key) + ':' + visit(item[key], depth + 1);
            }).join(',') + '}';
        }
        active.delete(item);
        return result;
    };
    return visit(value, 0);
}

function budget(input = {}) {
    const allowed = [...Object.keys(DEFAULT_BUDGET), 'parent'];
    for (const key of Object.keys(input)) if (!allowed.includes(key)) reject(`Unsupported constructor option: ${key}`);
    const result = {...DEFAULT_BUDGET};
    for (const key of Object.keys(result)) if (Object.hasOwn(input, key)) result[key] = input[key];
    for (const [key, max] of [['maxStates', 100000], ['maxProgramSize', 32],
        ['maxCost', 1000000000], ['maxMemoryStates', 100000]]) {
        if (!Number.isSafeInteger(result[key]) || result[key] < 1 || result[key] > max) reject(`Invalid ${key}.`);
    }
    if (typeof result.dominance !== 'boolean') reject('Invalid dominance flag.');
    return result;
}

function emptyAST(apparatus) {
    return {schema: 'out-evolve-ast/v1', installations: [],
        prepare: {op: 'sequence', steps: []}, scope: clone(apparatus.scope)};
}

function instructionCount(ast) { return ast.installations.length + ast.prepare.steps.length; }
function programKey(ast) { return canonical(ast); }
function pathCost(apparatus, ast, inherited) {
    const ids = [...ast.installations, ...ast.prepare.steps.map(step => step.id)];
    return ids.reduce((total, id) => total + (inherited.includes(id) ? 0
        : apparatus.primitives.find(primitive => primitive.id === id).cost), 0);
}

/** Sum every frozen construction once; ancestor fields must reproduce the embedded chain. */
export function lineageConstructionCost(input) {
    canonical(input);
    function total(pkg) {
        if (!pkg || !Number.isSafeInteger(pkg.costLedger?.total) || pkg.costLedger.total < 0
            || !pkg.parentAssets || !Number.isSafeInteger(pkg.parentAssets.ancestorCost)
            || pkg.parentAssets.ancestorCost < 0) reject('Invalid parent lineage cost ledger.');
        const parent = pkg.search?.parentSource ?? pkg.search?.checkpoint?.inheritance?.parent ?? null;
        const ancestorCost = parent ? total(parent) : 0;
        if (pkg.parentAssets.ancestorCost !== ancestorCost
            || (pkg.parentAssets.parentDigest || null) !== (parent?.digest || null)) {
            reject('Parent cumulative ancestor cost does not reproduce its lineage.');
        }
        const cumulative = ancestorCost + pkg.costLedger.total;
        if (!Number.isSafeInteger(cumulative)) reject('Cumulative lineage cost overflow.');
        return cumulative;
    }
    return total(input);
}

function matchingParent(apparatus, parent) {
    if (!parent) return {parentDigest: null, assets: [], ancestorCost: 0, parent: null};
    canonical(parent);
    if (!parent.apparatus || !parent.ast || !parent.certificate || typeof parent.digest !== 'string') {
        reject('Parent capability is missing executable evidence.');
    }
    const proof = checker.verify(parent.apparatus, parent.ast, parent.certificate);
    if (!proof.ok) reject('Parent capability does not independently qualify.');
    if (!equal(parent.apparatus.channels, apparatus.channels) || !equal(parent.apparatus.edges, apparatus.edges)
        || parent.apparatus.tolerance !== apparatus.tolerance) reject('Stale parent apparatus contract.');
    for (const id of parent.ast.installations) {
        const before = parent.apparatus.primitives.find(primitive => primitive.id === id);
        const after = apparatus.primitives.find(primitive => primitive.id === id);
        if (!before || !after || !equal(before, after)) reject('Stale parent installation semantics.');
    }
    const assets = [];
    // A valid parent orders each installation after its guards. Removing an unsupported
    // installation also removes its dependent installations, without changing semantics.
    for (const id of parent.ast.installations) {
        const primitive = apparatus.primitives.find(item => item.id === id);
        if (apparatus.scope.every(scope => primitive.support.scopes.includes(scope))
            && primitive.requires.every(required => assets.includes(required))) assets.push(id);
    }
    const ancestorCost = lineageConstructionCost(parent);
    return {parentDigest: parent.digest, assets, ancestorCost, parent: clone(parent)};
}

function initialCheckpoint(apparatus, options, inheritance) {
    runtime.validateApparatus(apparatus);
    const ast = emptyAST(apparatus);
    ast.installations = [...inheritance.assets];
    let state = runtime.initialState(apparatus);
    for (const id of ast.installations) state = runtime.step(apparatus, state, id);
    const node = {ast, state, cost: 0, serial: 0, phase: 'install'};
    const checkpoint = {schema: SEARCH_SCHEMA, constructorVersion: CONSTRUCTOR_VERSION,
        apparatus: clone(apparatus), options: clone(options), inheritance: clone(inheritance),
        status: 'searching', reason: 'Search is bounded and in progress.', expanded: 0,
        generated: 1, nextSerial: 1, queue: [node], seen: {}, attempts: [], frontier: [],
        controls: [], controlStop: null,
        work: {synthesis: 0, qualification: inheritance.parent ? 1 : 0, rejectedTransitions: 0, budgetPruned: 0,
            unsuccessfulCandidates: 0, deduplicated: 0}, result: null};
    remember(checkpoint, node);
    trustCheckpoint(checkpoint);
    return checkpoint;
}

export function createSearch(apparatus, options = {}) {
    canonical(apparatus);
    canonical(options);
    return initialCheckpoint(apparatus, budget(options), matchingParent(apparatus, options.parent));
}

function behaviorKey(node) {
    const {cost, steps, ...semantics} = node.state;
    return canonical({phase: node.phase, semantics});
}

function remember(checkpoint, node) {
    if (!checkpoint.options.dominance) return true;
    const key = behaviorKey(node), count = instructionCount(node.ast);
    const prior = checkpoint.seen[key] || [];
    if (prior.some(item => item.cost <= node.cost && item.length <= count)) {
        checkpoint.work.deduplicated += 1;
        return false;
    }
    checkpoint.seen[key] = prior.filter(item => !(node.cost <= item.cost && count <= item.length));
    checkpoint.seen[key].push({cost: node.cost, length: count});
    return true;
}

function sortQueue(queue) {
    queue.sort((a, b) => a.cost - b.cost || instructionCount(a.ast) - instructionCount(b.ast)
        || a.serial - b.serial);
}

function spent(checkpoint) { return checkpoint.work.synthesis + checkpoint.work.qualification; }
function memoryUnits(checkpoint) {
    return checkpoint.queue.length + Object.values(checkpoint.seen).reduce((sum, points) => sum + points.length, 0)
        + checkpoint.attempts.length + checkpoint.controls.length + checkpoint.frontier.length;
}
function stop(checkpoint, reason) {
    checkpoint.status = 'exhausted';
    checkpoint.reason = `No qualifying construction found within budget: ${reason}.`;
}

function expand(checkpoint) {
    const {apparatus, options} = checkpoint;
    if (memoryUnits(checkpoint) > options.maxMemoryStates) { stop(checkpoint, 'retained-state memory limit'); return; }
    if (checkpoint.expanded >= options.maxStates) { stop(checkpoint, 'state limit'); return; }
    if (!checkpoint.queue.length) {
        if (checkpoint.work.budgetPruned) { stop(checkpoint, 'total modeled cost pruned pending branches'); return; }
        checkpoint.status = 'infeasible';
        checkpoint.reason = 'No construction exists in the declared finite program space and bounds.';
        return;
    }
    sortQueue(checkpoint.queue);
    const node = checkpoint.queue.shift();
    const evaluationCost = 1 + instructionCount(node.ast);
    if (spent(checkpoint) + evaluationCost + 1 > options.maxCost) { stop(checkpoint, 'total modeled cost'); return; }
    checkpoint.expanded += 1;
    checkpoint.work.synthesis += evaluationCost;
    checkpoint.work.qualification += 1;
    let report;
    try { report = runtime.qualify(apparatus, node.ast); }
    catch (error) { report = {ok: false, reason: error.message}; }
    const cost = node.cost + spent(checkpoint);
    const attempt = {index: checkpoint.expanded, program: programKey(node.ast),
        programCost: node.cost, synthesisToDate: spent(checkpoint), qualified: false, reason: report.reason || ''};
    checkpoint.attempts.push(attempt);
    if (report.ok && cost <= options.maxCost) {
        const independent = checker.verify(apparatus, node.ast, report.certificate);
        checkpoint.work.qualification += 1;
        if (!independent.ok) reject('Runtime and independent checker disagree; construction rejected.');
        if (node.cost + spent(checkpoint) > options.maxCost) { stop(checkpoint, 'independent qualification cost'); return; }
        attempt.qualified = true;
        checkpoint.status = 'qualified';
        checkpoint.reason = 'Generated program independently qualifies in the supplied synthetic model.';
        checkpoint.result = {program: clone(node.ast), certificate: clone(report.certificate),
            report: clone(report), programCost: node.cost};
        checkpoint.frontier.push({installationCost: node.ast.installations.reduce((total, id) => total
            + (checkpoint.inheritance.assets.includes(id) ? 0
                : apparatus.primitives.find(primitive => primitive.id === id).cost), 0),
        operationCost: node.ast.prepare.steps.reduce((total, step) => total
            + apparatus.primitives.find(primitive => primitive.id === step.id).cost, 0),
        program: clone(node.ast), status: 'first-qualified-uniform-cost-point'});
        return;
    }
    checkpoint.work.unsuccessfulCandidates += 1;
    if (instructionCount(node.ast) >= options.maxProgramSize) return;
    for (const primitive of apparatus.primitives) {
        if (primitive.phase === 'install' && (node.phase !== 'install'
            || node.ast.installations.includes(primitive.id))) continue;
        if (spent(checkpoint) + 1 > options.maxCost) { stop(checkpoint, 'candidate transition work'); return; }
        checkpoint.work.synthesis += 1;
        const ast = clone(node.ast);
        if (primitive.phase === 'install') ast.installations.push(primitive.id);
        else ast.prepare.steps.push({op: 'primitive', id: primitive.id});
        let state;
        try { state = runtime.step(apparatus, node.state, primitive.id); }
        catch { checkpoint.work.rejectedTransitions += 1; continue; }
        const child = {ast, state, cost: pathCost(apparatus, ast, checkpoint.inheritance.assets),
            serial: checkpoint.nextSerial++, phase: primitive.phase === 'install' ? 'install' : 'prepare'};
        if (child.cost + spent(checkpoint) > options.maxCost) { checkpoint.work.budgetPruned += 1; continue; }
        if (!remember(checkpoint, child)) continue;
        if (memoryUnits(checkpoint) + 1 > options.maxMemoryStates) {
            stop(checkpoint, 'memory-state limit'); return;
        }
        checkpoint.queue.push(child);
        checkpoint.generated += 1;
    }
}

function ledger(checkpoint) {
    const ast = checkpoint.result?.program;
    const installations = ast ? ast.installations.filter(id => !checkpoint.inheritance.assets.includes(id)) : [];
    const installation = installations.reduce((sum, id) => sum
        + checkpoint.apparatus.primitives.find(primitive => primitive.id === id).cost, 0);
    const operation = ast ? ast.prepare.steps.reduce((sum, step) => sum
        + checkpoint.apparatus.primitives.find(primitive => primitive.id === step.id).cost, 0) : 0;
    const values = {unit: 'abstract-model-work', synthesis: checkpoint.work.synthesis,
        unsuccessfulCandidates: checkpoint.work.unsuccessfulCandidates,
        unsuccessfulCandidatesAccounting: 'Count only; all attempted execution work is charged in synthesis.',
        tuning: 0, installation, calibration: 0, qualification: checkpoint.work.qualification,
        operation, maintenance: 0};
    values.total = values.synthesis + values.tuning + values.installation + values.calibration
        + values.qualification + values.operation + values.maintenance;
    return values;
}

function resultFor(checkpoint) {
    trustCheckpoint(checkpoint);
    return {status: checkpoint.status, checkpoint, program: checkpoint.result?.program || null,
        certificate: checkpoint.result?.certificate || null, ledger: ledger(checkpoint),
        attempts: checkpoint.attempts, frontier: checkpoint.frontier, reason: checkpoint.reason};
}

function replayCheckpoint(input) {
    if (!Number.isSafeInteger(input.expanded) || input.expanded < 0 || input.expanded > 100000) {
        reject('Invalid checkpoint expansion count.');
    }
    const options = budget(input.options);
    if (input.expanded > options.maxStates || !Array.isArray(input.controls)
        || input.controls.length > options.maxMemoryStates) reject('Checkpoint exceeds frozen replay limits.');
    let previousControl = -1;
    for (const control of input.controls) {
        if (!control || Object.keys(control).length !== 2 || !['cancel', 'resume'].includes(control.kind)
            || !Number.isSafeInteger(control.at) || control.at < 0
            || control.at < previousControl || control.at > input.expanded) {
            reject('Invalid search control history.');
        }
        previousControl = control.at;
    }
    if (!equal(input.inheritance, matchingParent(input.apparatus, input.inheritance?.parent))) {
        reject('Checkpoint parent assets do not reproduce independent compatibility.');
    }
    const replay = initialCheckpoint(input.apparatus, options, input.inheritance);
    let control = 0;
    const started = globalThis.performance.now();
    function restoreControls() {
        while (input.controls[control]?.at === replay.expanded) {
            const next = input.controls[control++];
            if (next.kind === 'resume') {
                if (replay.status !== 'cancelled') reject('Checkpoint resumes a search that was not cancelled.');
                replay.status = 'searching'; replay.reason = 'Search is bounded and in progress.';
            } else {
                if (!['searching', 'cancelled'].includes(replay.status)) reject('Checkpoint cancels a terminal search.');
                replay.status = 'cancelled'; replay.reason = 'Search cancelled; evidence and remaining work retained.';
            }
            replay.controls.push(clone(next));
        }
    }
    while (replay.expanded < input.expanded) {
        if (globalThis.performance.now() - started > 60000) reject('Checkpoint reconstruction exceeded the execution limit.');
        restoreControls();
        if (replay.status !== 'searching') reject('Cancelled checkpoint advanced without a recorded resume.');
        expand(replay);
        if (replay.status !== 'searching' && replay.expanded !== input.expanded) reject('Impossible search checkpoint.');
    }
    restoreControls();
    if (control !== input.controls.length) reject('Invalid search control history.');
    const last = replay.controls.at(-1);
    if (input.status === 'cancelled' && last?.kind === 'cancel' && last.at === replay.expanded) {
        replay.status = 'cancelled'; replay.reason = 'Search cancelled; evidence and remaining work retained.';
    } else if (input.status === 'exhausted' && ['cancel', 'resume'].includes(input.controlStop)
        && memoryUnits(replay) + 1 > replay.options.maxMemoryStates) {
        replay.controlStop = input.controlStop;
        stop(replay, 'retained-history memory limit');
    } else if (input.status === 'exhausted' && input.reason.includes('execution timeout')) {
        stop(replay, 'execution timeout');
    } else if (input.status !== replay.status && replay.status === 'searching') {
        expand(replay);
    }
    return replay;
}

function validateCheckpoint(input) {
    canonical(input);
    if (!input || input.schema !== SEARCH_SCHEMA || input.constructorVersion !== CONSTRUCTOR_VERSION) {
        reject('Unsupported constructor checkpoint.');
    }
    const replay = replayCheckpoint(input);
    if (!equal(input, replay)) reject('Checkpoint does not reproduce deterministic search; tampering rejected.');
    trustCheckpoint(input);
    return input;
}

function searchToken(input) {
    const {parent, ...inheritance} = input.inheritance;
    return {schema: SEARCH_TOKEN_SCHEMA, constructorVersion: CONSTRUCTOR_VERSION, runtimeVersion: runtime.RUNTIME_VERSION,
        apparatus: clone(input.apparatus), options: clone(input.options), inheritance: clone(inheritance),
        expanded: input.expanded, controls: clone(input.controls), controlStop: input.controlStop,
        status: input.status, reason: input.reason,
        summary: {generated: input.generated, nextSerial: input.nextSerial, work: clone(input.work)}};
}

export function compactSearchCheckpoint(input) {
    const checkpoint = trusted.get(input) === canonical(input) ? input : validateCheckpoint(input);
    const token = searchToken(checkpoint);
    if (new TextEncoder().encode(canonical(token)).length > MAX_SEARCH_TOKEN_BYTES) {
        reject('Compact checkpoint exceeds the bounded recovery token size.');
    }
    freshTokens.set(token, {checkpoint, version: checkpointVersions.get(checkpoint), fingerprint: canonical(token)});
    return token;
}

export function exportSearchCheckpoint(input) { return compactSearchCheckpoint(input); }

export function importCompactSearchCheckpoint(input, {parent = null} = {}) {
    const serialized = canonical(input);
    const fresh = freshTokens.get(input);
    if (fresh && fresh.fingerprint === serialized && checkpointVersions.get(fresh.checkpoint) === fresh.version
        && trusted.get(fresh.checkpoint) === canonical(fresh.checkpoint)
        && (fresh.checkpoint.inheritance.parentDigest || null) === (parent?.digest || null)) {
        return fresh.checkpoint;
    }
    const keys = ['schema', 'constructorVersion', 'runtimeVersion', 'apparatus', 'options', 'inheritance',
        'expanded', 'controls', 'controlStop', 'status', 'reason', 'summary'];
    if (new TextEncoder().encode(serialized).length > MAX_SEARCH_TOKEN_BYTES || !input
        || Object.keys(input).length !== keys.length || !keys.every(key => Object.hasOwn(input, key))
        || input.schema !== SEARCH_TOKEN_SCHEMA || input.constructorVersion !== CONSTRUCTOR_VERSION
        || input.runtimeVersion !== runtime.RUNTIME_VERSION) reject('Unsupported compact search checkpoint.');
    const inheritance = matchingParent(input.apparatus, parent);
    const {parent: ignoredParent, ...scopedAssets} = inheritance;
    if (!equal(input.inheritance, scopedAssets)) reject('Compact checkpoint parent asset binding mismatch.');
    const replay = replayCheckpoint({...clone(input), inheritance});
    if (!equal(input, searchToken(replay))) reject('Compact checkpoint does not reproduce deterministic work and status.');
    trustCheckpoint(replay);
    return replay;
}

export function importSearchCheckpoint(input, context = {}) {
    canonical(input);
    return input?.schema === SEARCH_TOKEN_SCHEMA ? importCompactSearchCheckpoint(input, context)
        : validateCheckpoint(clone(input));
}

export function advanceSearch(input, {steps = 256, cancel = false, timeLimitMs = 1000, now = () => Date.now()} = {}) {
    const checkpoint = trusted.get(input) === canonical(input) ? input : validateCheckpoint(input);
    if (!Number.isSafeInteger(steps) || steps < 0 || steps > 100001
        || !Number.isSafeInteger(timeLimitMs) || timeLimitMs < 0 || timeLimitMs > 60000
        || typeof cancel !== 'boolean' || typeof now !== 'function') reject('Invalid search execution bounds.');
    if (['qualified', 'exhausted', 'infeasible'].includes(checkpoint.status)) return resultFor(checkpoint);
    if (cancel) {
        if (memoryUnits(checkpoint) + 1 > checkpoint.options.maxMemoryStates) {
            checkpoint.controlStop = 'cancel';
            stop(checkpoint, 'retained-history memory limit'); return resultFor(checkpoint);
        }
        checkpoint.controls.push({kind: 'cancel', at: checkpoint.expanded});
        checkpoint.status = 'cancelled';
        checkpoint.reason = 'Search cancelled; evidence and remaining work retained.';
        return resultFor(checkpoint);
    }
    if (checkpoint.status === 'cancelled') {
        if (memoryUnits(checkpoint) + 1 > checkpoint.options.maxMemoryStates) {
            checkpoint.controlStop = 'resume';
            stop(checkpoint, 'retained-history memory limit'); return resultFor(checkpoint);
        }
        checkpoint.controls.push({kind: 'resume', at: checkpoint.expanded});
        checkpoint.status = 'searching'; checkpoint.reason = 'Search is bounded and in progress.';
    }
    const started = now();
    for (let count = 0; count < steps && checkpoint.status === 'searching'; count += 1) {
        if (now() - started >= timeLimitMs) { stop(checkpoint, 'execution timeout'); break; }
        expand(checkpoint);
    }
    return resultFor(checkpoint);
}

export function construct(apparatus, options = {}) {
    const checkpoint = createSearch(apparatus, options);
    return advanceSearch(checkpoint, {steps: checkpoint.options.maxStates + 1, timeLimitMs: 60000});
}
