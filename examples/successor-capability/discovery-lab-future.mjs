// SPDX-License-Identifier: Apache-2.0
// Frozen Discovery Lab capability on separately supplied, publicly committed future tasks.
import {canonical, payloadDigest, validateBindings} from './discovery-lab-contract.mjs';
import {runCampaign, verifyCampaign, suppliedResponse} from './discovery-lab.mjs';
import {checkFutureOutput} from './discovery-lab-future-checker.mjs';

export const FUTURE_SCHEMA = 'discovery-lab-future-evaluation/v1';
export const FUTURE_PROTOCOL = Object.freeze({schema: 'discovery-lab-future-protocol/v1',
    taskFamilies: Object.freeze(['screen', 'inverse', 'select']),
    treatments: Object.freeze(['frozen-capability', 'capability-removed', 'construction-from-scratch', 'competent-static',
        'unrestricted-same-primitive', 'stale-capability-control', 'poisoned-capability-control']),
    ordering: Object.freeze(['verify-construction', 'freeze-executable-environment-obligations-evaluator', 'commit-future-bank', 'invoke', 'check']),
    workUnits: 'Logical work = acquisitions + search + checking + installations, each weight 1; not CPU instructions or money.',
    taskSelection: 'Commit the entire supplied bank before any arm runs; retain all tasks and treatments.',
    scope: 'Public synthetic protocol holdouts over a finite supplied model, not secret external benchmarks.'});
const snapshot = input => JSON.parse(canonical(input));
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const need = (condition, message) => { if (!condition) throw Error(message); };
const integer = (value, max) => Number.isSafeInteger(value) && value >= 0 && value <= max && !Object.is(value, -0);
const zero = () => ({acquisitions: 0, search: 0, checking: 0, installations: 0});
const work = costs => Object.values(costs).reduce((total, amount) => total + amount, 0);
const logical = resources => Object.fromEntries(Object.keys(zero()).map(key => [key, resources[key] || 0]));
const add = (left, right) => Object.fromEntries(Object.keys(zero()).map(key => [key, left[key] + right[key]]));
const immutable = value => {
    if (value && typeof value === 'object') { Object.values(value).forEach(immutable); Object.freeze(value); }
    return value;
};
const frozen = new WeakMap(), committedBanks = new WeakMap();
class Exhausted extends Error {}
function accountant(limit) {
    const costs = zero();
    return {costs, charge(key, amount = 1) {
        if (work(costs) + amount > limit) throw new Exhausted('Matched per-task logical work allowance exhausted.');
        costs[key] += amount;
    }};
}

/** The only construction argument is the retained A campaign; future task specifications are absent. */
export async function freezeCapability(input) {
    input = snapshot(input);
    need(exact(input, ['bindings', 'charter', 'result', 'ancestors']) && Array.isArray(input.ancestors)
        && input.ancestors.length <= 8, 'A complete bounded construction record is required.');
    const bindings = validateBindings(input.bindings), replay = zero();
    let parent = null;
    for (const record of [...input.ancestors, {charter: input.charter, result: input.result}]) {
        need(exact(record, ['charter', 'result']), 'Malformed ancestor replay record.');
        let check;
        try { check = verifyCampaign(record.charter, record.result, {parent}); }
        catch (error) {
            const refusal = Error(error.message);
            refusal.admissionReplay = add(replay, logical(error.verificationResources || zero()));
            refusal.costScope = 'Completed ancestor replay plus any verification work reported by the failed campaign replay.';
            throw refusal;
        }
        Object.assign(replay, add(replay, logical(check.verificationResources)));
        parent = record.result;
    }
    if (bindings.charterDigest !== await payloadDigest(input.charter)
        || bindings.purposeDigest !== await payloadDigest({purpose: input.charter.purpose})) {
        const refusal = Error('Frozen source bindings do not identify this construction charter and purpose.');
        refusal.admissionReplay = snapshot(replay); throw refusal;
    }
    const refusal = input.result.state !== 'accepted' ? 'The candidate was not accepted; predecessor remains available.'
        : input.result.stages[0].program.errorBound !== 0 ? 'This exact-answer protocol does not admit noisy capabilities.' : null;
    if (refusal) return immutable({schema: 'discovery-lab-future-freeze-refusal/v1', status: 'rejected', reason: refusal,
        bindings, resultDigest: await payloadDigest(input.result), construction: logical(input.result.lineage.cumulative),
        admissionReplay: replay, authority: false});
    const reference = input.result.comparisons.find(record => record.name === 'Unrestricted same-primitive finite reference');
    need(reference?.status === 'accepted' && reference.witness?.at(-1)?.kind === 'evolve',
        'A currently accepted unrestricted same-primitive witness is required.');
    const body = {schema: 'discovery-lab-frozen-future-capability/v1', status: 'frozen', bindings, protocol: snapshot(FUTURE_PROTOCOL),
        campaign: input, admissionReplay: replay, construction: logical(input.result.lineage.cumulative),
        executable: snapshot(input.result.stages.at(-1).program),
        unrestrictedExecutable: snapshot(reference.witness.at(-1).program), unrestrictedConstruction: logical(reference.measuredWork),
        environment: {controls: input.charter.controls, regime: input.charter.hiddenCoupling ? 'coupled' : 'linear'},
        obligations: {operations: input.charter.operations, checkpoints: input.charter.checkpoints},
        resultDigest: await payloadDigest(input.result), authority: false};
    const capsule = immutable({...body, digest: await payloadDigest(body)});
    frozen.set(capsule, capsule.digest);
    return capsule;
}

function validateTasks(tasks, controls) {
    need(Array.isArray(tasks) && tasks.length >= 1 && tasks.length <= 12, 'Commit one to twelve finite future tasks.');
    need(new Set(tasks.map(task => task.id)).size === tasks.length, 'Future task IDs must be unique.');
    for (const task of tasks) need(exact(task, ['id', 'kind', 'parameter', 'maxActiveControls', 'regime'])
        && typeof task.id === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/.test(task.id)
        && FUTURE_PROTOCOL.taskFamilies.includes(task.kind) && integer(task.parameter, 100)
        && integer(task.maxActiveControls, controls) && ['linear', 'coupled'].includes(task.regime),
    'Unsupported future task; expected answers are not an input field.');
    return tasks;
}

export async function commitFutureTasks(capsule, input) {
    need(frozen.has(capsule), 'Freeze and verify construction before supplying future tasks.');
    const tasks = validateTasks(snapshot(input), capsule.environment.controls);
    const body = {schema: 'discovery-lab-future-task-bank/v1', freezeDigest: frozen.get(capsule),
        protocolDigest: await payloadDigest(FUTURE_PROTOCOL), tasks, scope: FUTURE_PROTOCOL.scope};
    const bank = immutable({...body, digest: await payloadDigest(body)});
    committedBanks.set(bank, capsule.digest);
    return bank;
}

/** Public deterministic task generation happens after freezing; it is not a protected benchmark. */
export async function publicFutureBank(capsule, seed = 1) {
    need(frozen.has(capsule), 'Freeze and verify construction before generating future tasks.');
    need(integer(seed, 0xffffffff), 'A public unsigned 32-bit seed is required.');
    let state = seed;
    const random = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state; };
    return commitFutureTasks(capsule, Array.from({length: 6}, (_, index) => ({id: `future-${seed}-${index}`,
        kind: ['screen', 'inverse', 'select'][index % 3], parameter: 3 + random() % 13,
        maxActiveControls: random() % (capsule.environment.controls + 1), regime: index === 5 ? 'coupled' : 'linear'})));
}

function solve(task, controls, read, charge) {
    const rows = [];
    for (let mask = 0; mask < 2 ** controls; mask++) {
        charge('search'); rows.push({mask, value: read(mask)});
    }
    let selected;
    if (task.kind === 'select') {
        const eligible = rows.filter(row => { charge('search'); return row.mask.toString(2).replaceAll('0', '').length <= task.maxActiveControls; });
        let best = -1;
        for (const row of eligible) { charge('search'); best = Math.max(best, row.value); }
        selected = eligible.filter(row => { charge('search'); return row.value === best; }).map(row => row.mask);
    } else selected = rows.filter(row => { charge('search'); return task.kind === 'screen'
        ? row.value >= task.parameter : row.value === task.parameter; }).map(row => row.mask);
    return {rows, selected};
}

function attempt(capsule, task, treatment, limit) {
    const ledger = accountant(limit), charter = capsule.campaign.charter, controls = charter.controls;
    const trace = [], record = {treatment, taskId: task.id, status: 'inconclusive', output: null, checker: null,
        costs: ledger.costs, invocations: trace, reason: null};
    try {
        ledger.charge('checking');
        let table = null, read;
        if (treatment === 'poisoned-capability-control') {
            const poisoned = snapshot(capsule); poisoned.executable.responseTable[0]++;
            need(!frozen.has(poisoned), 'The control must not share accepted capability custody.');
            trace.push({action: 'refuse-replacement', freezeDigest: capsule.digest, reason: 'Replacement has no verified frozen custody.'});
            record.status = 'rejected'; record.reason = 'Poisoned replacement was refused before invocation.';
            return record;
        }
        if (treatment === 'frozen-capability' && task.regime !== capsule.environment.regime) {
            record.status = 'rejected'; record.reason = 'Changed regime is outside the frozen capability admission scope.';
            trace.push({action: 'refuse-stale-regime', freezeDigest: capsule.digest});
            return record;
        }
        if (treatment === 'construction-from-scratch') {
            // Reserve the full declared construction envelope before running a synchronous bounded campaign.
            const reservation = work(logical(charter.budget)) + 32 * 2 ** controls + 1;
            if (reservation > limit - work(ledger.costs)) throw new Exhausted('Full scratch-construction reservation exceeds the matched allowance.');
            const rebuilt = runCampaign({...charter, hiddenCoupling: task.regime === 'coupled'});
            for (const key of Object.keys(ledger.costs)) ledger.charge(key, rebuilt.resources[key]);
            trace.push({action: 'construct-from-scratch', state: rebuilt.state, resources: rebuilt.resources});
            if (rebuilt.state !== 'accepted') { record.status = rebuilt.state; record.reason = rebuilt.failure; return record; }
            table = rebuilt.stages.at(-1).program.responseTable;
        } else if (treatment === 'unrestricted-same-primitive') table = capsule.unrestrictedExecutable.responseTable;
        else if (['frozen-capability', 'stale-capability-control'].includes(treatment)) table = capsule.executable.responseTable;
        if (table) {
            trace.push({action: 'invoke-frozen-response-table', freezeDigest: capsule.digest,
                executable: treatment === 'unrestricted-same-primitive' ? 'independently-enumerated-unrestricted' : 'accepted-evolve-program',
                admissionBypassed: treatment === 'stale-capability-control'});
            read = mask => { ledger.charge('search'); return table[mask]; };
        } else if (treatment === 'capability-removed') {
            trace.push({action: 'invoke-supplied-simulator-without-capability', retainedTable: false});
            read = mask => {
                ledger.charge('acquisitions'); ledger.charge('search', 8);
                return suppliedResponse(mask, controls, task.regime === 'coupled') - 3 * (mask & 1) * (mask >> 1 & 1);
            };
        } else {
            trace.push({action: 'invoke-competent-fixed-formula', retainedTable: false});
            read = mask => {
                let value = 2;
                for (let index = 0; index < controls; index++) { ledger.charge('search'); value += (mask >> index & 1) * [2, 2, 4, 6][index]; }
                if (task.regime === 'coupled') { ledger.charge('search', 3); value += 5 * (mask & 1) * (mask >> 1 & 1) * (mask >> 2 & 1); }
                return value;
            };
        }
        record.output = solve(task, controls, read, ledger.charge);
        record.checker = checkFutureOutput(charter, task, record.output, ledger.charge);
        record.status = record.checker.accepted ? 'accepted' : 'rejected'; record.reason = record.checker.reason;
    } catch (error) {
        if (!(error instanceof Exhausted)) throw error;
        record.status = 'inconclusive'; record.reason = error.message;
    }
    return record;
}

/** Every committed task runs under every declared treatment; expected answers reach only the checker. */
export async function evaluateFutureTasks(capsule, bank, options = {}) {
    options = snapshot(options);
    need(exact(options, []) || exact(options, ['perTaskWorkLimit']), 'Unsupported future evaluation options.');
    const limit = options.perTaskWorkLimit ?? 3_000_000;
    need(integer(limit, 10_000_000), 'Unsupported matched work allowance.');
    need(frozen.has(capsule) && committedBanks.has(bank) && committedBanks.get(bank) === frozen.get(capsule),
        'The verified frozen capability and subsequent task commitment must retain custody.');
    const runs = bank.tasks.flatMap(task => FUTURE_PROTOCOL.treatments.map(treatment => attempt(capsule, task, treatment, limit)));
    const summaries = FUTURE_PROTOCOL.treatments.map(treatment => {
        const selected = runs.filter(run => run.treatment === treatment);
        const recurring = selected.reduce((costs, run) => add(costs, run.costs), zero());
        const cold = treatment === 'frozen-capability' || treatment === 'stale-capability-control'
            ? add(capsule.construction, capsule.admissionReplay)
            : treatment === 'unrestricted-same-primitive' ? capsule.unrestrictedConstruction : zero();
        const total = add(cold, recurring);
        return {treatment, completed: selected.filter(run => run.status === 'accepted').length,
            rejected: selected.filter(run => run.status === 'rejected').length,
            inconclusive: selected.filter(run => run.status === 'inconclusive').length,
            cold, recurring, total, amortizedWork: {numerator: work(total), denominator: bank.tasks.length}};
    });
    const relations = bank.tasks.map(task => {
        const selected = runs.filter(run => run.taskId === task.id);
        const treatment = selected.find(run => run.treatment === 'frozen-capability');
        return {taskId: task.id, comparisons: selected.filter(run => ['competent-static', 'unrestricted-same-primitive',
            'capability-removed', 'construction-from-scratch'].includes(run.treatment)).map(run => ({treatment: run.treatment,
            relation: treatment.status !== 'accepted' || run.status !== 'accepted' ? 'not-comparable'
                : work(treatment.costs) === work(run.costs) ? 'warm-tie'
                    : work(treatment.costs) < work(run.costs) ? 'frozen-warm-cheaper' : 'baseline-warm-cheaper'}))};
    });
    const body = {schema: FUTURE_SCHEMA, freezeDigest: capsule.digest, taskBankDigest: bank.digest,
        protocol: snapshot(FUTURE_PROTOCOL), perTaskWorkLimit: limit, runs, summaries, relations,
        accounting: {construction: 'Complete declared lineage construction, including original campaign comparisons and failed search.',
            checking: 'Admission replay and every future checker are charged; scratch construction includes its own checks and comparisons.',
            review: 'Human/organizational review, external coordination and operational-pilot costs are unmeasured, not zero.',
            memoryAndStorage: 'Original campaign peak memory/storage retained in frozen campaign; future report byte count measured separately by caller.',
            unknownCosts: ['organizational-review', 'external-coordination', 'energy', 'external-execution'],
            promotion: 'No imported result or local comparison authorizes promotion or settlement.'}, authority: false};
    return immutable({...body, digest: await payloadDigest(body)});
}

export async function verifyFutureEvaluation(capsule, bank, result) {
    capsule = snapshot(capsule); bank = snapshot(bank);
    result = snapshot(result);
    let admitted;
    try { admitted = await freezeCapability(capsule.campaign); }
    catch (error) {
        const refusal = Error(error.message);
        refusal.verificationResources = snapshot(error.admissionReplay || zero());
        throw refusal;
    }
    let verificationResources = snapshot(admitted.admissionReplay);
    const requireReplay = (condition, message) => {
        if (!condition) {
            const refusal = Error(message); refusal.verificationResources = snapshot(verificationResources); throw refusal;
        }
    };
    requireReplay(canonical(admitted) === canonical(capsule), 'Frozen executable, source, obligations or admission costs do not replay.');
    try {
        const admittedBank = await commitFutureTasks(admitted, bank.tasks);
        requireReplay(canonical(admittedBank) === canonical(bank), 'Future task bank or freeze ordering commitment does not replay.');
        const replay = await evaluateFutureTasks(admitted, admittedBank, {perTaskWorkLimit: result.perTaskWorkLimit});
        verificationResources = add(verificationResources, replay.runs.reduce((costs, run) => add(costs, run.costs), zero()));
        requireReplay(canonical(result) === canonical(replay), 'Future evaluation outcomes, costs, traces or commitments do not replay.');
        return {verified: true, authority: false, verificationResources, scope: FUTURE_PROTOCOL.scope};
    } catch (error) {
        const refusal = Error(error.message); refusal.verificationResources = snapshot(verificationResources); throw refusal;
    }
}
