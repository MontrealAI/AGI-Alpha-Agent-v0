// SPDX-License-Identifier: Apache-2.0
/** A bounded supplied-semantics discovery workcell. No network or spending. */
import { checkStage, checkQueries } from './discovery-lab-checker.mjs';
import { compareCampaign } from './discovery-lab-baselines.mjs';
import { parseBounded, canonical as boundedCanonical } from './discovery-lab-contract.mjs';

export const RUNTIME_VERSION = 'discovery-lab-runtime/v1';
export const REPORT_RESERVE_BYTES = 200000;
export const ARTIFACT_KINDS = Object.freeze(['learn', 'think', 'design', 'strategise', 'execute', 'evolve']);
export const DEFAULT_CHARTER = Object.freeze({
    schema: 'discovery-lab-charter/v1', purpose: 'qualified-finite-discovery-platform', controls: 3,
    accuracy: 1, intendedUses: 12, observations: ['contrast', 'reference', 'coarse', 'full'],
    operations: ['flip-z'], memory: 8, workerCapacity: 3, topology: 'right',
    faultHypotheses: ['clear', 'left', 'right', 'both'], checkpoints: ['safety'],
    noise: 0, driftScope: 'linear', actualDrift: 'linear', hiddenCoupling: false,
    budget: {acquisitions: 2000, search: 1000000, checking: 1000000, storageBytes: 500000, installations: 20}
});
const copy = value => JSON.parse(JSON.stringify(value));
const stable = value => Array.isArray(value) ? '[' + value.map(stable).join(',') + ']'
    : value && typeof value === 'object' ? '{' + Object.keys(value).sort()
        .map(key => JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}' : JSON.stringify(value);
const equal = (a, b) => stable(a) === stable(b);
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join(',') === [...keys].sort().join(',');
const integer = (value, lo, hi) => Number.isSafeInteger(value) && !Object.is(value, -0) && value >= lo && value <= hi;
const fail = message => { throw Error(message); };
const bytes = value => new TextEncoder().encode(stable(value)).length;
const fields = Object.keys(DEFAULT_CHARTER);
const trustedCampaigns = new WeakMap();
const uniqueList = (value, choices, required = false) => Array.isArray(value) && value.length <= choices.length
    && (!required || value.length > 0) && new Set(value).size === value.length && value.every(x => choices.includes(x));

export function validateCharter(input) {
    input = JSON.parse(boundedCanonical(input));
    if (!exact(input, fields) || input.schema !== DEFAULT_CHARTER.schema || input.purpose !== DEFAULT_CHARTER.purpose
        || ![3, 4].includes(input.controls) || !integer(input.accuracy, 0, 8)
        || !integer(input.intendedUses, 1, 100) || !integer(input.memory, 1, 16)
        || !integer(input.workerCapacity, 2, 4) || ![0, 1].includes(input.noise)
        || !['right', 'wrong', 'staged'].includes(input.topology)
        || !['linear', 'quadratic'].includes(input.driftScope) || !['linear', 'quadratic'].includes(input.actualDrift)
        || typeof input.hiddenCoupling !== 'boolean'
        || !uniqueList(input.observations, ['contrast', 'reference', 'coarse', 'full'])
        || !uniqueList(input.operations, ['flip-x', 'flip-y', 'flip-z', 'flip-w', 'mix'])
        || input.controls === 3 && input.operations.includes('flip-w')
        || !uniqueList(input.faultHypotheses, ['clear', 'left', 'right', 'both'], true)
        || !uniqueList(input.checkpoints, ['safety', 'sterile'], true) || !input.checkpoints.includes('safety')
        || !exact(input.budget, ['acquisitions', 'search', 'checking', 'storageBytes', 'installations'])
        || !integer(input.budget.acquisitions, 0, 10000) || !integer(input.budget.search, 0, 1000000)
        || !integer(input.budget.checking, 0, 1000000) || !integer(input.budget.storageBytes, 1024, 2000000)
        || !integer(input.budget.installations, 0, 100)) fail('Unsupported finite discovery charter.');
    return input;
}

export function parseCharter(text) { return validateCharter(parseBounded(text)); }

export function suppliedResponse(mask, controls, hiddenCoupling = false) {
    const x = mask & 1, y = mask >> 1 & 1, z = mask >> 2 & 1, w = mask >> 3 & 1;
    return 2 + 2 * x + 2 * y + 4 * z + (controls === 4 ? 6 * w : 0) + 3 * x * y
        + (hiddenCoupling ? 5 * x * y * z : 0);
}
const productive = (mask, n) => suppliedResponse(mask, n) - 3 * (mask & 1) * (mask >> 1 & 1);
const action = (mask, operation) => operation === 'mix'
    ? (mask & ~5) | (mask & 1) << 2 | (mask >> 2 & 1)
    : mask ^ (1 << ['flip-x', 'flip-y', 'flip-z', 'flip-w'].indexOf(operation));
const gcd = (a, b) => b ? gcd(b, a % b) : Math.abs(a);
const lcm = (a, b) => Math.abs(a * b) / gcd(a, b);
function contrast(times, signs) {
    const products = times.map(t => times.filter(s => s !== t).reduce((v, s) => v * (t - s), 1));
    const denominator = products.reduce((d, x) => lcm(d, x), 1);
    let numerators = products.map(x => denominator / x);
    let scale = numerators.reduce((sum, x, i) => sum + x * signs[i], 0);
    if (!scale) return null;
    if (scale < 0) { numerators = numerators.map(x => -x); scale = -scale; }
    const factor = numerators.reduce((d, x) => gcd(d, x), scale);
    return {numerators: numerators.map(x => x / factor), denominator: scale / factor};
}
const sum = values => values.reduce((a, b) => a + b, 0);
const weighted = (raw, weights) => sum(raw.map((value, i) => value * weights.numerators[i]));
const rawReadings = (response, times, signs, charter) => times.map((t, i) =>
    signs[i] * 2 * response + 3 + t + (charter.actualDrift === 'quadratic' ? t * t : 0));
function interval(z, weights, gain, noise) {
    const error = noise * sum(weights.numerators.map(Math.abs));
    const values = [];
    for (const endpoint of [z - error, z + error]) for (const g of [gain.lower, gain.upper]) {
        values.push(endpoint * gain.denominator / (weights.denominator * g));
    }
    return [Math.floor(Math.min(...values)), Math.ceil(Math.max(...values))];
}
const ZERO = () => ({acquisitions: 0, search: 0, checking: 0, memoryWords: 0, storageBytes: 0,
    workerSlots: 0, installations: 0});
class Exhausted extends Error {}
function accountant(charter) {
    const resources = ZERO();
    return {resources, attempts: [], charge(key, amount = 1) {
        const limit = charter.budget[key];
        if (limit !== undefined && resources[key] + amount > limit) throw new Exhausted(`${key} budget exhausted`);
        resources[key] += amount;
    }, peak(key, amount) { resources[key] = Math.max(resources[key], amount); }};
}
const snapshot = ledger => copy(ledger.resources);
const delta = (before, after) => Object.fromEntries(Object.keys(before).map(key => [key, after[key] - before[key]]));
const operationCost = operations => operations.includes('reference') ? {install: 0, recurring: 1}
    : operations.includes('isolate') ? {install: 2, recurring: 0}
        : operations.includes('modularize') ? {install: 4, recurring: 0} : {install: 0, recurring: 0};

function learn(charter, inputs, ledger) {
    if (!charter.observations.includes('contrast') || !charter.observations.includes('reference')) {
        return {reason: 'The charter does not permit contrast and reference acquisition.', candidates: []};
    }
    const degree = charter.driftScope === 'linear' ? 1 : 2;
    const grids = degree === 1 ? [[0, 1, 2], [0, 2, 4]] : [[0, 1, 2, 3], [0, 1, 3, 4]];
    const candidates = []; ledger.attempts = candidates;
    let selected = null;
    for (const times of grids) for (let pattern = 0; pattern < 1 << (times.length - 1); pattern++) {
        ledger.charge('search');
        const signs = times.map((_, i) => i === 0 || !(pattern >> (i - 1) & 1) ? 1 : -1);
        const weights = contrast(times, signs);
        if (!weights) { candidates.push({times, signs, status: 'rejected', reason: 'No signal-preserving contrast.'}); continue; }
        for (const referenceAmplitude of [4, 8, 16]) {
            ledger.charge('search');
            ledger.charge('acquisitions', times.length);
            const calibrationRaw = rawReadings(referenceAmplitude, times, signs, charter);
            const center = weighted(calibrationRaw, weights), error = charter.noise * sum(weights.numerators.map(Math.abs));
            const gainInterval = {lower: center - error, upper: center + error,
                denominator: weights.denominator * referenceAmplitude};
            const errorBound = gainInterval.lower <= 0 ? 1000000
                : Math.ceil((24 * error + error * referenceAmplitude) / gainInterval.lower);
            const recurringCost = times.length + sum(signs.slice(1).map((s, i) => s !== signs[i] ? 1 : 0)) + times.at(-1);
            const constructionCost = recurringCost + referenceAmplitude / 4;
            const total = constructionCost + charter.intendedUses * recurringCost;
            const valid = gainInterval.lower > 0 && errorBound <= charter.accuracy
                && (degree === 2 || charter.actualDrift === 'linear');
            candidates.push({times, signs, referenceAmplitude, errorBound, constructionCost, recurringCost, total,
                status: valid ? 'candidate' : 'rejected', reason: valid ? 'Bounded contrast candidate.' : 'Error or drift scope exceeds charter.'});
            if (valid && (!selected || total < selected.total)) {
                selected = {degree, times, signs, weights, referenceAmplitude, gainInterval, calibrationRaw,
                    errorBound, constructionCost, recurringCost, total};
            }
        }
    }
    if (!selected) return {reason: 'No searched schedule meets the declared error and drift scope.', candidates};
    const queryRows = [];
    for (let mask = 0; mask < 1 << charter.controls; mask++) {
        ledger.charge('search'); ledger.charge('acquisitions', selected.times.length);
        const raw = rawReadings(suppliedResponse(mask, charter.controls, charter.hiddenCoupling), selected.times, selected.signs, charter);
        queryRows.push({mask, raw, interval: interval(weighted(raw, selected.weights), selected.weights,
            selected.gainInterval, charter.noise)});
    }
    const {constructionCost, recurringCost, total, ...program} = selected;
    return {program: {...program, queryRows}, candidates,
        evidence: {constructionCost, recurringCost, horizonCost: total, comparedSchedules: candidates.length,
            uncertainty: charter.noise ? 'Conservative integer intervals remain ambiguous.' : 'Exact only within the supplied zero-noise finite model.'}};
}

function think(charter, inputs, ledger) {
    const observations = inputs[0].program.queryRows.map(row => row.interval);
    let encoder = observations.map((row, index) => observations.findIndex(candidate => equal(row, candidate)));
    let changed = true;
    while (changed) {
        const signatures = observations.map((row, mask) => {
            ledger.charge('search');
            return stable([row, charter.operations.map(operation => encoder[action(mask, operation)])]);
        });
        const next = signatures.map(signature => signatures.indexOf(signature));
        changed = !equal(next, encoder); encoder = next;
    }
    const labels = [...new Set(encoder)], renaming = new Map(labels.map((label, i) => [label, i]));
    encoder = encoder.map(label => renaming.get(label));
    const blocks = labels.map((_, group) => encoder.flatMap((value, mask) => value === group ? [mask] : []));
    const decoder = blocks.map(block => observations[block[0]]);
    const updates = Object.fromEntries(charter.operations.map(operation => [operation,
        blocks.map(block => encoder[action(block[0], operation)])]));
    ledger.peak('memoryWords', blocks.length + sum(Object.values(updates).map(table => table.length)));
    return {program: {encoder, blocks, decoder, updates}, candidates: [],
        evidence: {retiredLabels: 2 * encoder.length, fullStateLabels: encoder.length,
            executableLabels: blocks.length, staticLabels: new Set(observations.map(stable)).size,
            memoryLimit: charter.memory, independentStateOperationCases: encoder.length * (charter.operations.length + 1)}};
}

function design(charter, inputs, ledger) {
    const representation = inputs[1].program, serviceTable = [];
    const groups = representation.blocks.length, operations = charter.operations.length ? [...charter.operations] : ['identity'];
    const compiled = {decoder: copy(representation.decoder), operations,
        updaters: Object.fromEntries(operations.map(operation => [operation, operation === 'identity'
            ? Array.from({length: groups}, (_, i) => i) : copy(representation.updates[operation])]))};
    for (let a = 0; a < groups; a++) for (let b = 0; b < groups; b++) {
        ledger.charge('search');
        serviceTable.push([a, b, ...compiled.decoder[a], ...operations.map(operation => compiled.updaters[operation][b])]);
    }
    const footprint = representation.decoder.length * 2
        + sum(Object.values(compiled.updaters).map(table => table.length)) + 4;
    const workersBefore = Array.from({length: charter.workerCapacity}, (_, i) =>
        ({location: i === 0 ? 'left' : i === 1 ? 'right' : 'aux', services: [i]}));
    const vacancy = charter.topology === 'right' ? 'right' : 'left';
    const packed = workersBefore.map(worker => ({location: worker.location,
        services: worker.location === (vacancy === 'right' ? 'left' : 'right') ? [0, 1]
            : worker.location === vacancy ? [] : worker.services}));
    const transition = [copy(workersBefore), copy(packed)];
    let workersAfter = packed;
    if (charter.topology === 'staged') {
        workersAfter = packed.map(worker => ({location: worker.location,
            services: worker.location === 'left' ? [0, 1] : worker.location === 'right' ? [] : worker.services}));
        transition.push(copy(workersAfter)); ledger.charge('installations');
    }
    ledger.charge('installations'); ledger.peak('workerSlots', charter.workerCapacity); ledger.peak('memoryWords', footprint);
    return {program: {compiled, serviceTable, footprint, workerLimit: charter.memory * 8,
        workersBefore, workersAfter, transition, vacancy: charter.topology === 'wrong' ? 'left' : 'right',
        staging: charter.topology === 'staged'}, candidates: [],
        evidence: {beforeOccupied: charter.workerCapacity, afterOccupied: charter.workerCapacity - 1,
            serviceCases: serviceTable.length, independentlyVaryingInputs: true,
            equalSavingWrongLocation: 'The same packing in the wrong location cannot supply the installation.'}};
}

function routeCost(route, checkpoints) { return (route === 'bypass' ? 5 : 1) + (checkpoints.includes('sterile') ? 2 : 0); }
const available = (route, world) => route === 'bypass' || route === 'L' && !['left', 'both'].includes(world)
    || route === 'R' && !['right', 'both'].includes(world);
function strategise(charter, inputs, ledger) {
    if (inputs[2].program.vacancy !== 'right') return {reason: 'Released capacity is at the wrong location; staging is not permitted.', candidates: []};
    const candidates = []; ledger.attempts = candidates;
    for (const observation of ['none', 'coarse', 'full']) {
        if (observation !== 'none' && !charter.observations.includes(observation)) continue;
        const groups = observation === 'none' ? [charter.faultHypotheses]
            : observation === 'full' ? charter.faultHypotheses.map(world => [world])
                : [charter.faultHypotheses.filter(world => ['clear', 'left'].includes(world)),
                    charter.faultHypotheses.filter(world => ['right', 'both'].includes(world))].filter(group => group.length);
        const leaves = [];
        for (const worlds of groups) {
            const routes = ['L', 'R', 'bypass'].filter(route => {
                ledger.charge('search', worlds.length); return worlds.every(world => available(route, world));
            }).sort((a, b) => routeCost(a, charter.checkpoints) - routeCost(b, charter.checkpoints) || a.localeCompare(b));
            const route = routes[0];
            const sterile = charter.checkpoints.includes('sterile');
            const visits = ['source', 'safety', ...(sterile ? ['sterile'] : []), route === 'L' ? 'left' : route === 'R' ? 'right' : 'bypass', 'sink'];
            leaves.push({worlds: copy(worlds), route, visits, constructionActions: sterile ? ['install-sterile-checkpoint'] : [],
                checkpoints: copy(charter.checkpoints), cost: routeCost(route, charter.checkpoints)});
        }
        const observationCost = observation === 'none' ? 0 : observation === 'coarse' ? 1 : 2;
        const expectedCost = {numerator: sum(leaves.map(leaf => leaf.worlds.length * (observationCost + leaf.cost))),
            denominator: charter.faultHypotheses.length};
        candidates.push({observation, leaves, expectedCost, reservations: {vacancy: 'right', installations: 1}});
    }
    candidates.sort((a, b) => a.expectedCost.numerator - b.expectedCost.numerator
        || ['coarse', 'none', 'full'].indexOf(a.observation) - ['coarse', 'none', 'full'].indexOf(b.observation));
    ledger.charge('installations', charter.checkpoints.includes('sterile') ? 3 : 1);
    return {program: candidates[0], candidates, evidence: {worldsChecked: charter.faultHypotheses.length,
        residualBeliefs: candidates[0].leaves.map(leaf => leaf.worlds), optimalAmongSuppliedObservationGrammar: true,
        objective: 'Expected cost under the explicitly supplied uniform finite world distribution.'}};
}

function compileFactor(id, scope, cost, ledger) {
    const table = [];
    for (let mask = 0; mask < 1 << scope.length; mask++) {
        ledger.charge('search'); const values = scope.map((_, i) => mask >> i & 1);
        table.push({values, cost: cost(...values)});
    }
    return {id, scope, table};
}
function execute(charter, inputs, ledger, parent) {
    const policy = copy(inputs[3].program), denominator = policy.expectedCost.denominator;
    const bindings = {checkpoint: charter.checkpoints.includes('sterile') ? 'sterile' : 'safety', policy,
        availableActions: ['isolate', 'reference'], vacancy: inputs[2].program.vacancy,
        workerSlots: policy.reservations.installations, denominator, intendedUses: charter.intendedUses,
        compiledServices: copy(inputs[2].program.compiled), residentWords: inputs[2].program.footprint};
    const old = parent?.stages?.find(stage => stage.kind === 'execute' && stage.status === 'accepted')?.program;
    const reusedFactors = [], reuseContracts = [], components = [];
    ledger.attempts = [];
    const relevant = (id, source) => id === 'route' ? {policy: source.policy}
        : id === 'reference' ? {intendedUses: source.intendedUses, availableActions: source.availableActions, denominator: source.denominator}
            : {availableActions: source.availableActions, vacancy: source.vacancy, workerSlots: source.workerSlots, denominator: source.denominator};
    const make = (id, scope, cost) => {
        const retained = old && !charter.hiddenCoupling && equal(relevant(id, old.bindings), relevant(id, bindings))
            && old.factors.find(factor => factor.id === id && equal(factor.scope, scope));
        if (retained) { ledger.charge('search'); reusedFactors.push(id); return copy(retained); }
        return compileFactor(id, scope, cost, ledger);
    };
    const baseRoute = policy.expectedCost.numerator - (bindings.checkpoint === 'sterile' ? 2 * denominator : 0);
    const observationCost = policy.observation === 'none' ? 0 : policy.observation === 'coarse' ? 1 : 2;
    const factors = [make('prepare', ['a'], a => 2 * a * denominator),
        make('reference', ['b'], b => b * charter.intendedUses * denominator),
        make('capacity', ['a', 'b'], (a, b) => a + b === 1 ? 0 : null),
        make('route', ['r', 'c'], (r, c) => (r ? (observationCost + 5) * denominator : baseRoute) + 2 * c * denominator),
        make('checkpoint', ['b', 'c'], (b, c) => c && !b ? null : 0)];
    const componentSpecs = [
        {id: 'installation', private: ['a', 'b'], boundary: ['c'], factorIds: ['prepare', 'reference', 'capacity', 'checkpoint']},
        {id: 'routing', private: ['r'], boundary: ['c'], factorIds: ['route']}
    ];
    for (const spec of componentSpecs) {
        const localFactors = factors.filter(factor => spec.factorIds.includes(factor.id));
        const prior = old?.components?.find(component => component.id === spec.id);
        const sameInterface = prior && equal(prior.private, spec.private) && equal(prior.boundary, spec.boundary)
            && equal(prior.factorIds, spec.factorIds);
        const bindingsEqual = sameInterface && spec.factorIds.every(id => equal(relevant(id, old.bindings), relevant(id, bindings)));
        const rowsEqual = bindingsEqual && localFactors.every(factor =>
            equal(factor, old.factors.find(candidate => candidate.id === factor.id)));
        let profiles;
        if (rowsEqual && !charter.hiddenCoupling) {
            ledger.charge('search', prior.profiles.length); profiles = copy(prior.profiles);
        } else {
            profiles = [];
            for (let c = 0; c < 2; c++) {
                let best = null;
                for (let mask = 0; mask < 1 << spec.private.length; mask++) {
                    ledger.charge('search');
                    const witness = Object.fromEntries([...spec.private.map((name, index) => [name, mask >> index & 1]), ['c', c]]);
                    let value = 0, feasible = true;
                    for (const factor of localFactors) {
                        ledger.charge('search');
                        const row = factor.table.find(row => factor.scope.every((name, index) => witness[name] === row.values[index]));
                        if (row.cost === null) { feasible = false; break; }
                        value += row.cost;
                    }
                    if (feasible && (!best || value < best.value || value === best.value && stable(witness) < stable(best.witness))) {
                        best = {boundary: c, value, witness};
                    }
                }
                profiles.push(best); ledger.attempts.push({component: spec.id, boundary: c, status: 'candidate', value: best.value});
            }
        }
        let profileEqual = Boolean(sameInterface);
        if (sameInterface) for (let boundary = 0; boundary < 2; boundary++) {
            ledger.charge('search');
            if (profiles[boundary].value !== prior.profiles[boundary].value) profileEqual = false;
        }
        components.push({...spec, profiles});
        reuseContracts.push({component: spec.id, status: rowsEqual ? 'retained' : 'rebuilt',
            completeProfileEqual: profileEqual, propagation: !old ? 'cold' : profileEqual ? 'stopped' : 'continued'});
    }
    const stopOptimization = Boolean(old && reuseContracts.every(record => record.completeProfileEqual));
    const profiles = [0, 1].map(c => {
        ledger.charge('search');
        const installation = components[0].profiles[c], routing = components[1].profiles[c];
        const witness = {a: installation.witness.a, b: installation.witness.b, r: routing.witness.r, c};
        return {boundary: c, value: stopOptimization ? old.profiles[c].value : installation.value + routing.value, witness};
    });
    const currentBoundary = bindings.checkpoint === 'sterile' ? 1 : 0, witness = profiles[currentBoundary].witness;
    const installations = {actions: [witness.a ? 'isolate' : 'reference'], placement: bindings.vacancy,
        scopeControls: charter.controls};
    const routeWitness = {observation: policy.observation, leaves: policy.leaves.map(leaf => witness.r === 0 ? copy(leaf)
        : {...copy(leaf), route: 'bypass', visits: ['source', 'safety', ...(currentBoundary ? ['sterile'] : []), 'bypass', 'sink'],
            cost: 5 + 2 * currentBoundary})};
    ledger.charge('installations', witness.a ? 2 : 0);
    ledger.peak('memoryWords', inputs[2].program.footprint + 4 * components.length);
    return {program: {variables: ['a', 'b', 'r', 'c'], factors, components, profiles, bindings,
        witness, currentBoundary, reusedFactors, installations, routeWitness, reuseContracts}, candidates: copy(ledger.attempts),
        evidence: {completeBoundaryCases: profiles.length, retainedComponents: reusedFactors,
            currentWitnessMaterialized: true, relevantBindingsCompared: true,
            scalarOnlyReuse: false, completeProfilePropagationStopped: stopOptimization,
            localWitnessesReconstructed: true,
            executableDependency: 'Independent installation and routing modules share only the complete checkpoint boundary. Current local witnesses compose into current executable actions.'}};
}

function coefficientsFor(table, ledger) {
    const coefficients = [...table];
    for (let bit = 1; bit < table.length; bit <<= 1) for (let mask = 0; mask < table.length; mask++) {
        ledger.charge('search'); if (mask & bit) coefficients[mask] -= coefficients[mask ^ bit];
    }
    return coefficients;
}
const popcount = mask => mask.toString(2).split('1').length - 1;
function evolve(charter, inputs, ledger) {
    const candidates = []; ledger.attempts = candidates;
    for (const operations of [[], ['isolate'], ['reference'], ['modularize']]) {
        const responseTable = [];
        for (let mask = 0; mask < 1 << charter.controls; mask++) {
            ledger.charge('search');
            let response = suppliedResponse(mask, charter.controls, charter.hiddenCoupling);
            if (operations.length) response -= 3 * (mask & 1) * (mask >> 1 & 1);
            responseTable.push(response);
        }
        const coefficients = coefficientsFor(responseTable, ledger);
        const degree = Math.max(0, ...coefficients.flatMap((value, mask) => value ? [popcount(mask)] : []));
        const costs = operationCost(operations), horizonCost = costs.install + charter.intendedUses * costs.recurring;
        const installed = equal(operations, inputs[4].program.installations.actions)
            && inputs[4].program.installations.placement === 'right';
        candidates.push({operations, responseTable, coefficients, degree, costs, horizonCost,
            status: degree <= 1 && installed ? 'candidate' : 'rejected',
            reason: installed ? 'Installed current completion witness.' : 'This operation is not installed by the accepted execution witness.'});
    }
    const qualified = candidates.filter(candidate => candidate.status === 'candidate')
        .sort((a, b) => a.horizonCost - b.horizonCost || stable(a.operations).localeCompare(stable(b.operations)));
    if (!qualified.length) return {reason: 'Full semantic checks retain an interaction outside the supported first-order platform.', candidates};
    const selected = qualified[0];
    return {program: {operations: selected.operations, responseTable: selected.responseTable,
        coefficients: selected.coefficients, degree: 1, scopeControls: charter.controls,
        freezeOrder: 'before-query-evaluation'}, candidates,
        evidence: {fullDomainCases: selected.responseTable.length, higherOrderCoefficientsChecked: true,
            horizonCost: selected.horizonCost, frozenBeforeQueries: true,
            semantics: 'Supplied operation effects remove the declared nuisance; no physical claim or curve-fit proof.'}};
}

const builders = {learn, think, design, strategise, execute, evolve};
const scopes = {
    learn: 'Supplied positive gain, declared polynomial drift, bounded additive read error and finite control domain.',
    think: 'Every control state, its conservative measurement interval and every permitted operation.',
    design: 'Every independent two-service input and every installation transition phase.',
    strategise: 'All residual fault worlds, permitted tests, routes and mandatory checkpoints.',
    execute: 'Complete finite factor scopes, both boundary values, current policy bindings and current witness.',
    evolve: 'Declared operation grammar, full response domain and every interaction coefficient.'
};
const assumptions = ['Public supplied synthetic semantics; not a protected holdout or a physical materials experiment.',
    'No credentials, external executor, currency payment, signing or authority are created.'];

function queryFamily(charter, program, error, ledger) {
    const intervals = program.responseTable.map(value => { ledger.charge('search'); return [value - error, value + error]; });
    const screening = intervals.map(([lo, hi], mask) => { ledger.charge('search'); return {mask,
        outcome: lo >= 8 ? 'accepted' : hi < 8 ? 'rejected' : 'ambiguous'}; });
    const inverseDesign = {target: 8, definite: [], possible: []};
    intervals.forEach(([lo, hi], mask) => {
        ledger.charge('search');
        if (lo === 8 && hi === 8) inverseDesign.definite.push(mask);
        if (lo <= 8 && hi >= 8) inverseDesign.possible.push(mask);
    });
    const eligible = intervals.flatMap((range, mask) => { ledger.charge('search'); return popcount(mask) <= 2 ? [{mask, range}] : []; });
    const bestLower = Math.max(...eligible.map(row => { ledger.charge('search'); return row.range[0]; }));
    const candidates = eligible.filter(row => { ledger.charge('search'); return row.range[1] >= bestLower; })
        .map(row => { ledger.charge('search'); return row.mask; });
    const exactMaximum = Math.max(...eligible.map(row => { ledger.charge('search'); return program.responseTable[row.mask]; }));
    const optimal = eligible.filter(row => { ledger.charge('search'); return program.responseTable[row.mask] === exactMaximum; })
        .map(row => { ledger.charge('search'); return row.mask; });
    return {thresholdScreening: {threshold: 8, results: screening}, inverseDesign,
        constrainedSelection: {maximumActiveControls: 2, candidates, suppliedModelOptima: optimal,
            uncertainty: error === 0 ? 'exact-within-supplied-model' : 'interval-ambiguity-retained'},
        intervals, queriesAfterFreeze: true};
}

export function invalidationFor(before, after) {
    validateCharter(before); validateCharter(after);
    const changed = fields.filter(key => !equal(before[key], after[key]));
    if (!changed.length) return {changed, earliest: null, invalidated: []};
    const dependencies = {
        controls: 'learn', accuracy: 'learn', intendedUses: 'learn', observations: 'learn', noise: 'learn',
        driftScope: 'learn', actualDrift: 'learn', hiddenCoupling: 'learn', operations: 'think', memory: 'think',
        workerCapacity: 'design', topology: 'design', faultHypotheses: 'strategise', checkpoints: 'strategise', budget: 'learn'
    };
    const earliestIndex = Math.min(...changed.map(key => ARTIFACT_KINDS.indexOf(dependencies[key] || 'learn')));
    return {changed, earliest: ARTIFACT_KINDS[earliestIndex], invalidated: ARTIFACT_KINDS.slice(earliestIndex)};
}

/** Search and qualification are distinct; any truncated attempt is inconclusive. */
export function runCampaign(input, options = {}) {
    const charter = validateCharter(input), originalParent = options.parent || null;
    const parentFrame = originalParent ? boundedCanonical(originalParent) : null;
    if (originalParent && trustedCampaigns.get(originalParent) !== parentFrame) {
        fail('Verify the intact parent in its retained history before successor reuse.');
    }
    const parent = originalParent ? JSON.parse(parentFrame) : null;
    if (parent && (parent.schema !== 'discovery-lab-campaign/v1' || parent.state !== 'accepted')) {
        fail('A successor requires an accepted parent campaign within its original scope.');
    }
    const ledger = accountant(charter), stages = [];
    let state = charter.budget.storageBytes >= REPORT_RESERVE_BYTES ? 'accepted' : 'inconclusive';
    let failure = state === 'inconclusive' ? 'Storage reservation is insufficient before work begins.' : null;
    for (const kind of ARTIFACT_KINDS) {
        const before = snapshot(ledger);
        if (state !== 'accepted') {
            stages.push({kind, status: 'paused', inputs: stages.filter(stage => stage.status === 'accepted').map(stage => stage.kind),
                scope: scopes[kind], assumptions: copy(assumptions), program: null, evidence: null,
                checker: null, cost: ZERO(), attempts: [], reason: 'An upstream stage has no accepted current artifact.'});
            continue;
        }
        let artifact; ledger.attempts = [];
        try {
            const built = builders[kind](charter, stages, ledger, parent);
            if (!built.program) {
                state = 'rejected';
                artifact = {program: null, evidence: built.evidence || null, checker: null,
                    attempts: built.candidates || [], reason: built.reason, status: 'rejected'};
            } else {
                const checker = checkStage(kind, charter, built.program, stages,
                    {maxChecks: charter.budget.checking - ledger.resources.checking});
                ledger.charge('checking', checker.checks);
                state = checker.inconclusive ? 'inconclusive' : checker.accepted ? 'accepted' : 'rejected';
                if (checker.inconclusive) failure = checker.reason;
                artifact = {program: built.program, evidence: built.evidence || null, checker,
                    attempts: built.candidates || [], reason: checker.reason, status: state};
            }
        } catch (error) {
            if (!(error instanceof Exhausted)) throw error;
            state = 'inconclusive'; failure = error.message;
            artifact = {program: null, evidence: null, checker: null, attempts: copy(ledger.attempts), reason: error.message, status: 'inconclusive'};
        }
        const record = {kind, inputs: stages.filter(stage => stage.status === 'accepted').map(stage => stage.kind),
            scope: scopes[kind], assumptions: copy(assumptions), ...artifact, cost: delta(before, ledger.resources)};
        stages.push(record);
        const storage = bytes({charter, stages}); ledger.peak('storageBytes', storage);
        record.cost.storageBytes = ledger.resources.storageBytes - before.storageBytes;
        if (storage > charter.budget.storageBytes) {
            state = 'inconclusive'; failure = 'storageBytes budget exhausted';
            record.status = 'inconclusive'; record.reason = failure;
        }
    }
    let queryResults = null, queryChecker = null;
    if (state === 'accepted') {
        const before = snapshot(ledger);
        try {
            queryResults = queryFamily(charter, stages[5].program, stages[0].program.errorBound, ledger);
            queryChecker = checkQueries(charter, stages[5].program, stages[0].program, queryResults,
                {maxChecks: charter.budget.checking - ledger.resources.checking});
            ledger.charge('checking', queryChecker.checks);
            if (!queryChecker.accepted) {
                state = queryChecker.inconclusive ? 'inconclusive' : 'rejected'; failure = queryChecker.reason;
            }
        } catch (error) {
            if (!(error instanceof Exhausted)) throw error;
            state = 'inconclusive'; failure = error.message;
        }
        stages[5].cost = Object.fromEntries(Object.keys(before).map(key =>
            [key, stages[5].cost[key] + ledger.resources[key] - before[key]]));
    }
    const invalidations = parent ? invalidationFor(parent.charter, charter) : {changed: [], earliest: null, invalidated: []};
    const retained = parent && state === 'accepted' ? stages[4].program.reusedFactors : [];
    const oldSlice = parent && state === 'accepted' && parent.charter.controls <= charter.controls
        ? parent.stages[5].program.responseTable.every((value, mask) => value === stages[5].program.responseTable[mask]) : false;
    if (parent && state === 'accepted' && (!oldSlice
        || parent.charter.controls < charter.controls && parent.charter.operations.some(operation => !charter.operations.includes(operation)))) {
        state = 'rejected'; failure = 'The successor failed to preserve the accepted predecessor purpose on its original domain and operations.';
        stages[5].status = 'rejected'; stages[5].reason = failure; queryResults = null;
    }
    let comparisons = [];
    if (state === 'accepted') {
        const before = snapshot(ledger);
        comparisons = compareCampaign(charter, stages, {parent,
            charge: (key, amount = 1) => ledger.charge(key, amount),
            remaining: key => (charter.budget[key] ?? 1000000) - ledger.resources[key]});
        for (const key of Object.keys(before)) stages[5].cost[key] += ledger.resources[key] - before[key];
        if (comparisons.some(record => record.status === 'inconclusive') || comparisons.length < 10) {
            state = 'inconclusive'; failure = 'A required finite comparator did not complete within its declared scope and budget.';
        }
    }
    const resources = snapshot(ledger);
    const cumulative = Object.fromEntries(Object.keys(resources).map(key => [key,
        ['memoryWords', 'workerSlots'].includes(key) ? Math.max(parent?.lineage?.cumulative?.[key] || 0, resources[key])
            : (parent?.lineage?.cumulative?.[key] || 0) + resources[key]]));
    const report = {schema: 'discovery-lab-campaign/v1', runtime: RUNTIME_VERSION, charter, state, failure, stages,
        comparisons, resources, invalidations,
        reuse: {retainedFactors: retained, priorPurposePreservedOnOldSlice: Boolean(oldSlice),
            acceptedPredecessorPreserved: Boolean(parent), claim: 'Current witnesses and acceptance were performed; retained assets do not confer authority.'},
        queryResults, queryChecker, lineage: {generation: (parent?.lineage?.generation || 0) + 1,
            incremental: resources, cumulative, accounting: 'Parent cumulative costs plus only this campaign work; no inherited cost is charged twice.'},
        resourceReservation: {storageBytes: REPORT_RESERVE_BYTES, status: charter.budget.storageBytes >= REPORT_RESERVE_BYTES ? 'reserved-before-work' : 'refused-before-work'},
        resourceUnits: {acquisitions: 'simulator raw readouts', search: 'counted producer loop and compiler steps',
            checking: 'independent checker data nodes and finite semantic cases', memoryWords: 'peak abstract resident words',
            storageBytes: 'UTF-8 report evidence bytes', workerSlots: 'peak occupied virtual worker slots',
            installations: 'declared construction installation units', elapsedTime: 'Measured separately by the caller; not inferred from logical work.'},
        executionMode: 'free-local-synthetic-replay', currencyCaps: {USDC: '0', AGIALPHA: '0'}, externalExecution: 'unprovisioned'};
    for (let iteration = 0; iteration < 8; iteration++) {
        const actualBytes = bytes(report), difference = actualBytes - resources.storageBytes;
        if (!difference) break;
        resources.storageBytes = actualBytes;
        stages.at(-1).cost.storageBytes += difference;
        cumulative.storageBytes = (parent?.lineage?.cumulative?.storageBytes || 0) + actualBytes;
    }
    trustedCampaigns.set(report, boundedCanonical(report));
    return report;
}

/** Independent certificate checks plus deterministic result reconstruction. */
export function verifyCampaign(charter, result, options = {}) {
    const current = validateCharter(charter), originalResult = result;
    const resultFrame = boundedCanonical(result);
    result = JSON.parse(resultFrame);
    if (!result || result.schema !== 'discovery-lab-campaign/v1' || !equal(result.charter, current)) {
        fail('Campaign does not belong to this exact charter.');
    }
    if (options.limits) {
        const caps = options.limits;
        const required = {...current.budget, storageBytes: REPORT_RESERVE_BYTES};
        const insufficient = ['acquisitions', 'search', 'checking', 'storageBytes', 'installations']
            .some(key => !integer(caps[key], 0, 1000000000) || caps[key] < required[key]);
        if (insufficient) return {verified: false, accepted: false, state: 'CHECK_INCOMPLETE',
            verificationResources: ZERO(), checks: 0, replaySearch: 0, authority: false,
            reason: 'Conservative replay reservation exceeds the supplied inspection envelope; no replay began.'};
    }
    const reconstructed = runCampaign(current, options);
    if (!equal(result, reconstructed)) {
        const error = Error('Campaign evidence, costs, state or dependencies do not reconstruct.');
        error.verificationResources = copy(reconstructed.resources);
        throw error;
    }
    trustedCampaigns.set(originalResult, resultFrame);
    return {verified: true, accepted: result.state === 'accepted', state: result.state,
        verificationResources: copy(reconstructed.resources),
        checks: result.resources.checking, replaySearch: result.resources.search,
        authority: false, acceptanceScope: 'Current supplied finite model only; imported evidence grants no external authority.'};
}
