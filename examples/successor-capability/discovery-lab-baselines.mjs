// SPDX-License-Identifier: Apache-2.0
/** Separately enumerated finite controls. No producer compiler or transition is imported. */
import {checkStage} from './discovery-lab-checker.mjs';

const clone = value => JSON.parse(JSON.stringify(value));
const stable = value => Array.isArray(value) ? '[' + value.map(stable).join(',') + ']'
    : value && typeof value === 'object' ? '{' + Object.keys(value).sort()
        .map(key => JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}' : JSON.stringify(value);
const same = (a, b) => stable(a) === stable(b);
const zero = () => ({search: 0, checking: 0, acquisitions: 0, installations: 0});
const signChanges = signs => signs.slice(1).filter((value, index) => value !== signs[index]).length;
const bit = (mask, index) => (mask >> index) & 1;
const countBits = value => { let total = 0; for (; value; value &= value - 1) total++; return total; };

function determinant(matrix, tick) {
    tick('search');
    if (matrix.length === 1) return matrix[0][0];
    let value = 0;
    for (let column = 0; column < matrix.length; column++) {
        const minor = matrix.slice(1).map(row => row.filter((_, index) => index !== column));
        value += (column % 2 ? -1 : 1) * matrix[0][column] * determinant(minor, tick);
    }
    return value;
}

function measurementReference(charter, tick) {
    const degree = charter.driftScope === 'quadratic' ? 2 : 1;
    const grids = degree === 1 ? [[0, 1, 2], [0, 2, 4]] : [[0, 1, 2, 3], [0, 1, 3, 4]];
    const candidates = [];
    for (const times of grids) for (let pattern = 0; pattern < 2 ** (times.length - 1); pattern++) {
        const signs = times.map((_, index) => index === 0 || !(pattern & (1 << (index - 1))) ? 1 : -1);
        const matrix = [signs, ...Array.from({length: degree + 1}, (_, power) => times.map(time => time ** power))];
        let denominator = determinant(matrix, tick);
        if (!denominator) continue;
        let numerators = times.map((_, column) => determinant(matrix.map((row, index) =>
            row.map((value, current) => current === column ? Number(index === 0) : value)), tick));
        if (denominator < 0) { denominator = -denominator; numerators = numerators.map(value => -value); }
        const absolute = numerators.reduce((total, value) => total + Math.abs(value), 0);
        for (const amplitude of [4, 8, 16]) {
            tick('search');
            const contrast = signs.reduce((total, value, index) => {
                tick('acquisitions');
                const time = times[index];
                const drift = 3 + time + (charter.actualDrift === 'quadratic' ? time * time : 0);
                return total + numerators[index] * (2 * value * amplitude + drift);
            }, 0);
            const error = charter.noise * absolute, lower = contrast - error;
            const bound = lower <= 0 ? Infinity : Math.ceil((24 + amplitude) * error / lower);
            const recurring = times.length + signChanges(signs) + times.at(-1);
            const cold = recurring + amplitude / 4;
            const permitted = charter.observations.includes('contrast') && charter.observations.includes('reference');
            candidates.push({times, signs, numerators, denominator, amplitude, bound, cold, recurring,
                horizon: cold + charter.intendedUses * recurring,
                accepted: permitted && lower > 0 && bound <= charter.accuracy
                    && (degree === 2 || charter.actualDrift === 'linear')});
        }
    }
    const accepted = candidates.filter(value => value.accepted).sort((a, b) => a.horizon - b.horizon);
    return {candidates, best: accepted[0] || null};
}

function policyReference(charter, tick) {
    const feasible = (route, world) => route === 'bypass'
        || route === 'L' && world !== 'left' && world !== 'both'
        || route === 'R' && world !== 'right' && world !== 'both';
    const cost = route => (route === 'bypass' ? 5 : 1) + (charter.checkpoints.includes('sterile') ? 2 : 0);
    const result = [];
    for (const observation of ['none', 'coarse', 'full']) {
        if (observation !== 'none' && !charter.observations.includes(observation)) continue;
        const groups = observation === 'none' ? [charter.faultHypotheses]
            : observation === 'full' ? charter.faultHypotheses.map(world => [world])
                : [['clear', 'left'], ['right', 'both']].map(group => charter.faultHypotheses
                    .filter(world => group.includes(world))).filter(group => group.length);
        const observationCost = observation === 'none' ? 0 : observation === 'coarse' ? 1 : 2;
        let best = null, examined = 0;
        const visit = (index, routes) => {
            if (index < groups.length) {
                for (const route of ['L', 'R', 'bypass']) {
                    tick('search');
                    let admitted = true;
                    for (const world of groups[index]) { tick('checking'); if (!feasible(route, world)) admitted = false; }
                    if (admitted) visit(index + 1, [...routes, route]);
                }
                return;
            }
            examined++; tick('search');
            const numerator = groups.reduce((total, group, current) => total
                + group.length * (observationCost + cost(routes[current])), 0);
            if (!best || numerator < best.expectedCost.numerator) {
                best = {observation, expectedCost: {numerator, denominator: charter.faultHypotheses.length},
                    leaves: groups.map((worlds, current) => ({worlds: clone(worlds), route: routes[current],
                        visits: ['source', 'safety', ...(charter.checkpoints.includes('sterile') ? ['sterile'] : []),
                            routes[current] === 'L' ? 'left' : routes[current] === 'R' ? 'right' : 'bypass', 'sink'],
                        constructionActions: charter.checkpoints.includes('sterile') ? ['install-sterile-checkpoint'] : [],
                        checkpoints: clone(charter.checkpoints), cost: cost(routes[current])})),
                    reservations: {vacancy: 'right', installations: 1}};
            }
        };
        visit(0, []);
        result.push({observation, program: best, combinations: examined});
    }
    return result;
}

function fullProfiles(program, tick) {
    const names = program.variables, boundary = names.indexOf('c'), best = [null, null];
    if (boundary < 0 || names.length > 12) throw Error('Unsupported independent profile domain.');
    for (let mask = 0; mask < 2 ** names.length; mask++) {
        tick('search');
        const assignment = Object.fromEntries(names.map((name, index) => [name, bit(mask, index)]));
        let value = 0, feasible = true;
        for (const factor of program.factors) {
            let row = null;
            for (const candidate of factor.table) {
                tick('checking');
                if (factor.scope.every((name, index) => assignment[name] === candidate.values[index])) { row = candidate; break; }
            }
            if (!row) throw Error('A complete factor assignment is missing.');
            if (row.cost === null) { feasible = false; break; }
            value += row.cost;
        }
        const slot = assignment.c;
        if (feasible && (!best[slot] || value < best[slot].value
            || value === best[slot].value && stable(assignment) < stable(best[slot].witness))) {
            best[slot] = {boundary: slot, value, witness: assignment};
        }
    }
    return best;
}

function platformReference(charter, tick) {
    const candidates = [];
    for (const operation of [null, 'isolate', 'reference', 'modularize']) {
        const table = [];
        for (let mask = 0; mask < 2 ** charter.controls; mask++) {
            tick('search');
            const useful = 2 + 2 * bit(mask, 0) + 2 * bit(mask, 1) + 4 * bit(mask, 2)
                + (charter.controls === 4 ? 6 * bit(mask, 3) : 0);
            table.push(useful + (!operation ? 3 * bit(mask, 0) * bit(mask, 1) : 0)
                + (charter.hiddenCoupling ? 5 * bit(mask, 0) * bit(mask, 1) * bit(mask, 2) : 0));
        }
        const coefficients = [];
        for (let mask = 0; mask < table.length; mask++) {
            let value = 0;
            for (let subset = mask; ; subset = (subset - 1) & mask) {
                tick('checking');
                value += (countBits(mask) - countBits(subset)) % 2 ? -table[subset] : table[subset];
                if (!subset) break;
            }
            coefficients.push(value);
        }
        const degree = Math.max(0, ...coefficients.map((value, mask) => value ? countBits(mask) : 0));
        const cold = operation === 'isolate' ? 2 : operation === 'modularize' ? 4 : 0;
        const recurring = operation === 'reference' ? 1 : 0;
        candidates.push({operation, degree, cold, recurring, responseTable: table, coefficients,
            horizon: cold + charter.intendedUses * recurring, accepted: degree <= 1});
    }
    return candidates;
}

function directResponse(charter, mask) {
    return 2 + 2 * bit(mask, 0) + 2 * bit(mask, 1) + 4 * bit(mask, 2)
        + (charter.controls === 4 ? 6 * bit(mask, 3) : 0) + 3 * bit(mask, 0) * bit(mask, 1)
        + (charter.hiddenCoupling ? 5 * bit(mask, 0) * bit(mask, 1) * bit(mask, 2) : 0);
}
function directRead(charter, candidate, value, tick) {
    return candidate.times.map((time, index) => {
        tick('acquisitions');
        return 2 * candidate.signs[index] * value + 3 + time
            + (charter.actualDrift === 'quadratic' ? time * time : 0);
    });
}
function measuredProgram(charter, candidate, tick) {
    const error = charter.noise * candidate.numerators.reduce((n, value) => n + Math.abs(value), 0);
    const calibrationRaw = directRead(charter, candidate, candidate.amplitude, tick);
    const weighted = values => values.reduce((n, value, index) => n + value * candidate.numerators[index], 0);
    const center = weighted(calibrationRaw), lower = center - error, upper = center + error;
    const queryRows = [];
    for (let mask = 0; mask < 2 ** charter.controls; mask++) {
        tick('search');
        const raw = directRead(charter, candidate, directResponse(charter, mask), tick), z = weighted(raw);
        const corners = [(z - error) * candidate.amplitude / lower, (z - error) * candidate.amplitude / upper,
            (z + error) * candidate.amplitude / lower, (z + error) * candidate.amplitude / upper];
        queryRows.push({mask, raw, interval: [Math.floor(Math.min(...corners)), Math.ceil(Math.max(...corners))]});
    }
    return {degree: charter.driftScope === 'quadratic' ? 2 : 1, times: candidate.times, signs: candidate.signs,
        weights: {numerators: candidate.numerators, denominator: candidate.denominator},
        referenceAmplitude: candidate.amplitude, gainInterval: {lower, upper, denominator: candidate.denominator * candidate.amplitude},
        calibrationRaw, queryRows, errorBound: candidate.bound};
}
function transform(mask, operation) {
    return operation === 'mix' ? (mask & ~5) | bit(mask, 0) << 2 | bit(mask, 2)
        : mask ^ (1 << {'flip-x': 0, 'flip-y': 1, 'flip-z': 2, 'flip-w': 3}[operation]);
}
function reasoningProgram(charter, observation, tick) {
    const n = observation.queryRows.length;
    const conflicts = Array.from({length: n}, () => Array(n).fill(false));
    for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) {
        tick('search'); conflicts[a][b] = !same(observation.queryRows[a].interval, observation.queryRows[b].interval);
    }
    let changed = true;
    while (changed) {
        changed = false;
        for (const operation of charter.operations) for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) {
            tick('search');
            if (!conflicts[a][b] && conflicts[transform(a, operation)][transform(b, operation)]) {
                conflicts[a][b] = true; changed = true;
            }
        }
    }
    const blocks = [], encoder = [];
    for (let state = 0; state < n; state++) {
        let label = blocks.findIndex(block => !conflicts[state][block[0]]);
        if (label < 0) { label = blocks.length; blocks.push([]); }
        blocks[label].push(state); encoder.push(label); tick('search');
    }
    return {encoder, blocks, decoder: blocks.map(block => clone(observation.queryRows[block[0]].interval)),
        updates: Object.fromEntries(charter.operations.map(operation => [operation,
            blocks.map(block => encoder[transform(block[0], operation)])]))};
}
function realizationProgram(charter, reasoning, tick) {
    const groups = reasoning.blocks.length, operations = charter.operations.length ? [...charter.operations] : ['identity'];
    const compiled = {decoder: clone(reasoning.decoder), operations,
        updaters: Object.fromEntries(operations.map(operation => [operation,
            operation === 'identity' ? Array.from({length: groups}, (_, i) => i) : clone(reasoning.updates[operation])]))};
    const serviceTable = [];
    for (let a = 0; a < groups; a++) for (let b = 0; b < groups; b++) {
        tick('search'); serviceTable.push([a, b, ...compiled.decoder[a], ...operations.map(operation => compiled.updaters[operation][b])]);
    }
    const footprint = 2 * groups + Object.values(compiled.updaters).reduce((n, value) => n + value.length, 0) + 4;
    const before = Array.from({length: charter.workerCapacity}, (_, index) =>
        ({location: index === 0 ? 'left' : index === 1 ? 'right' : 'aux', services: [index]}));
    const host = charter.topology === 'right' ? 'left' : 'right';
    const packed = before.map(worker => ({location: worker.location,
        services: worker.location === host ? [0, 1] : ['left', 'right'].includes(worker.location) ? [] : worker.services}));
    const after = charter.topology === 'staged' ? before.map(worker => ({location: worker.location,
        services: worker.location === 'left' ? [0, 1] : worker.location === 'right' ? [] : worker.services})) : packed;
    return {compiled, serviceTable, footprint, workerLimit: charter.memory * 8, workersBefore: before,
        workersAfter: after, transition: charter.topology === 'staged' ? [before, packed, after] : [before, after],
        vacancy: charter.topology === 'wrong' ? 'left' : 'right', staging: charter.topology === 'staged'};
}
function completionProgram(charter, design, policy, tick) {
    const denominator = policy.expectedCost.denominator, sterile = charter.checkpoints.includes('sterile');
    const base = policy.expectedCost.numerator - (sterile ? 2 * denominator : 0);
    const observationCost = policy.observation === 'none' ? 0 : policy.observation === 'coarse' ? 1 : 2;
    const specs = [['prepare', ['a'], a => 2 * a * denominator],
        ['reference', ['b'], b => b * charter.intendedUses * denominator],
        ['capacity', ['a', 'b'], (a, b) => a + b === 1 ? 0 : null],
        ['route', ['r', 'c'], (r, c) => (r ? (observationCost + 5) * denominator : base) + 2 * c * denominator],
        ['checkpoint', ['b', 'c'], (b, c) => c && !b ? null : 0]];
    const factors = specs.map(([id, scope, cost]) => ({id, scope,
        table: Array.from({length: 2 ** scope.length}, (_, mask) => {
            tick('search'); const values = scope.map((_, index) => bit(mask, index));
            return {values, cost: cost(...values)};
        })}));
    const program = {variables: ['a', 'b', 'r', 'c'], factors};
    const componentSpecs = [
        {id: 'installation', private: ['a', 'b'], boundary: ['c'], factorIds: ['prepare', 'reference', 'capacity', 'checkpoint']},
        {id: 'routing', private: ['r'], boundary: ['c'], factorIds: ['route']}
    ];
    const components = componentSpecs.map(spec => ({...spec, profiles: fullProfiles({variables: [...spec.private, 'c'],
        factors: factors.filter(factor => spec.factorIds.includes(factor.id))}, tick)}));
    const profiles = fullProfiles(program, tick), currentBoundary = Number(sterile), witness = profiles[currentBoundary].witness;
    const routeWitness = {observation: policy.observation, leaves: policy.leaves.map(leaf => witness.r === 0 ? clone(leaf)
        : {...clone(leaf), route: 'bypass', visits: ['source', 'safety', ...(sterile ? ['sterile'] : []), 'bypass', 'sink'],
            cost: 5 + 2 * currentBoundary})};
    return {...program, components, profiles, bindings: {checkpoint: sterile ? 'sterile' : 'safety', policy: clone(policy),
        availableActions: ['isolate', 'reference'], vacancy: design.vacancy, workerSlots: policy.reservations.installations,
        denominator, intendedUses: charter.intendedUses, compiledServices: clone(design.compiled), residentWords: design.footprint},
    witness, currentBoundary, reusedFactors: [], routeWitness,
    reuseContracts: components.map(component => ({component: component.id, status: 'rebuilt', completeProfileEqual: false, propagation: 'cold'})),
    installations: {actions: [witness.a ? 'isolate' : 'reference'],
        placement: design.vacancy, scopeControls: charter.controls}};
}

/** Joint direct enumeration of the declared finite campaign grammar, with no producer candidate imports. */
function campaignReference(charter, measurements, policies, platforms, tick, qualify) {
    let best = null, combinations = 0, qualified = 0;
    const rejected = [];
    for (const measurement of measurements.candidates.filter(value => value.accepted)) {
        const observation = measuredProgram(charter, measurement, tick);
        const reasoning = reasoningProgram(charter, observation, tick);
        if (reasoning.blocks.length > charter.memory) continue;
        const design = realizationProgram(charter, reasoning, tick);
        if (design.footprint > design.workerLimit || design.vacancy !== 'right' || charter.hiddenCoupling) continue;
        for (const policy of policies.filter(value => value.program)) {
            const completion = completionProgram(charter, design, policy.program, tick);
            const action = completion.installations.actions[0];
            const platform = platforms.find(value => value.accepted && value.operation === action);
            tick('search'); combinations++;
            if (!platform) continue;
            const numerator = measurement.horizon * completion.bindings.denominator
                + completion.profiles[completion.currentBoundary].value
                + (charter.topology === 'staged' ? 2 : 1) * completion.bindings.denominator;
            const denominator = completion.bindings.denominator;
            const evolution = {operations: [action], responseTable: platform.responseTable,
                coefficients: platform.coefficients, degree: 1, scopeControls: charter.controls,
                freezeOrder: 'before-query-evaluation'};
            const programs = [observation, reasoning, design, policy.program, completion, evolution];
            try { qualify(programs); qualified++; }
            catch (error) {
                if (error.name !== 'BaselineRejected') throw error;
                rejected.push({candidate: combinations, reason: String(error.message)});
                continue;
            }
            if (best && numerator * best.objective.denominator >= best.objective.numerator * denominator) continue;
            best = {objective: {numerator, denominator}, measurementHorizon: measurement.horizon,
                policyExpectedCost: clone(policy.program.expectedCost),
                programs};
        }
    }
    return {best, combinations, qualified, rejected};
}

/** Every record states its actual finite scope. No whole-architecture optimality is inferred. */
export function compareCampaign(charter, stages, {parent = null, charge = () => {}, remaining = () => 1000000} = {}) {
    const records = [];
    const stage = kind => stages.find(value => value.kind === kind && value.status === 'accepted');
    let activeCounts = zero();
    const tick = (kind, amount = 1) => { charge(kind, amount); activeCounts[kind] += amount; };
    const run = (name, fn) => {
        activeCounts = zero();
        try { records.push({name, ...fn(), measuredWork: clone(activeCounts)}); }
        catch (error) {
            records.push({name, status: error.name === 'BaselineRejected' ? 'rejected' : 'inconclusive',
                reason: String(error.message || error), measuredWork: clone(activeCounts)});
            if (/budget exhausted|check budget|work budget/i.test(String(error.message))) return false;
        }
        return true;
    };
    const verify = (kind, program, inputs) => {
        const result = checkStage(kind, charter, program, inputs, {maxChecks: Math.max(0, Math.min(1000000, remaining('checking')))});
        tick('checking', result.checks);
        if (!result.accepted) {
            const error = Error(result.reason);
            error.name = result.inconclusive ? 'BaselineIncomplete' : 'BaselineRejected';
            throw error;
        }
        return result;
    };
    let measurement = null, policies = null, platforms = null;
    if (!run('Unrestricted same-primitive finite reference', () => {
        measurement = measurementReference(charter, tick);
        policies = policyReference(charter, tick);
        platforms = platformReference(charter, tick);
        const chainFor = programs => programs.map((program, index) => ({kind:
            ['learn', 'think', 'design', 'strategise', 'execute', 'evolve'][index], status: 'accepted', program}));
        const joint = campaignReference(charter, measurement, policies, platforms, tick, programs => {
            const chain = chainFor(programs);
            verify('evolve', chain[5].program, chain.slice(0, 5));
        });
        if (!joint.best) return {status: 'rejected', reason: 'No complete admitted campaign in the independently enumerated finite grammar.',
            scope: 'Complete supplied measurement, canonical representation, realization, policy, installation and response grammars. No claim outside these supplied semantics.'};
        const chain = chainFor(joint.best.programs);
        const primary = stage('execute');
        const primaryObjective = primary ? {numerator: stages[0].evidence.horizonCost * primary.program.bindings.denominator
            + primary.program.profiles[primary.program.currentBoundary].value
            + (charter.topology === 'staged' ? 2 : 1) * primary.program.bindings.denominator,
        denominator: primary.program.bindings.denominator} : null;
        const difference = primaryObjective ? joint.best.objective.numerator * primaryObjective.denominator
            - primaryObjective.numerator * joint.best.objective.denominator : null;
        return {status: 'accepted', relation: difference === 0 ? 'tie' : difference < 0 ? 'reference-cheaper' : 'reference-more-expensive',
            scope: 'Joint direct construction and current independent acceptance across the complete declared finite campaign grammar. Not a global architecture optimum outside that grammar.',
            measurementCandidates: measurement.candidates.length, policyCombinations: policies.reduce((n, value) => n + value.combinations, 0),
            platformCandidates: platforms.length, completeCampaignCandidates: joint.combinations,
            independentlyQualifiedCampaigns: joint.qualified, rejectedCampaigns: joint.rejected,
            objective: joint.best.objective, primaryObjective,
            objectiveUnits: 'Declared acquisition-program horizon price plus uniform-world completion/installation price; search/checking resources are reported separately.',
            measurementHorizon: joint.best.measurementHorizon, policyExpectedCost: joint.best.policyExpectedCost,
            witness: chain.map(value => ({kind: value.kind, program: value.program}))};
    })) return records;
    if (!run('Fixed architecture with more search', () => {
        if (!stage('learn')) return {status: 'unsupported', reason: 'No qualified measurement interface exists.'};
        const measured = measurement || measurementReference(charter, tick);
        const best = measured.best;
        if (!best) return {status: 'rejected', reason: 'Every enumerated fixed measurement candidate fails its error or permission contract.'};
        const count = 2 ** charter.controls;
        let responseChecksum = 0;
        for (let use = 0; use < charter.intendedUses; use++) for (let mask = 0; mask < count; mask++) {
            tick('search');
            const raw = directRead(charter, best, directResponse(charter, mask), tick);
            const corrected = raw.reduce((n, value, index) => n + value * best.numerators[index], 0)
                / (2 * best.denominator);
            tick('checking');
            if (corrected !== directResponse(charter, mask)) throw Error('Direct fixed-architecture response failed current semantic replay.');
            responseChecksum += corrected;
        }
        return {status: 'accepted', retainedStructure: false, measuredConfigurations: count * charter.intendedUses,
            responseChecksum,
            scope: 'Direct full finite-response replay at every use; same qualified measurement access, no installed interaction simplification.'};
    })) return records;
    if (!run('Full-state reasoning', () => {
        const learned = stage('learn');
        if (!learned) return {status: 'unsupported', reason: 'No accepted observation relation.'};
        const n = 2 ** charter.controls, operations = {};
        for (const operation of charter.operations) {
            const flips = {'flip-x': 0, 'flip-y': 1, 'flip-z': 2, 'flip-w': 3};
            operations[operation] = Array.from({length: n}, (_, mask) => {
                tick('search');
                return operation === 'mix' ? (mask & ~5) | bit(mask, 0) << 2 | bit(mask, 2)
                    : mask ^ (1 << flips[operation]);
            });
        }
        const program = {encoder: Array.from({length: n}, (_, index) => index),
            blocks: Array.from({length: n}, (_, index) => [index]),
            decoder: learned.program.queryRows.map(row => clone(row.interval)), updates: operations};
        const result = checkStage('think', charter, program, stages.slice(0, 1),
            {maxChecks: Math.max(0, Math.min(1000000, remaining('checking')))});
        tick('checking', result.checks);
        return {status: result.accepted ? 'accepted' : result.inconclusive ? 'inconclusive' : 'rejected',
            labels: n, candidateLabels: stage('think')?.program.blocks.length ?? null,
            reason: result.reason, scope: 'Actual identity encoder, contextual interval decoder and direct operation tables.'};
    })) return records;
    if (!run('Separate service realization', () => {
        const design = stage('design');
        if (!design) return {status: 'unsupported', reason: 'No qualified current service realization.'};
        let vacancies = 0, services = 0;
        for (const worker of design.program.workersBefore) { tick('checking'); services += worker.services.length; if (!worker.services.length) vacancies++; }
        return {status: vacancies ? 'accepted' : 'rejected', vacancies, requiredServices: services,
            reason: vacancies ? 'An actual separate worker is free.' : 'Complete initial occupancy has no permitted empty installation destination.',
            scope: 'Current separate realization and fixed admitted worker topology.'};
    })) return records;
    for (const observation of ['full', 'none']) {
        if (!run(observation === 'full' ? 'Full diagnosis' : 'No-diagnosis construction', () => {
            const candidate = (policies || policyReference(charter, tick)).find(value => value.observation === observation);
            if (!candidate?.program || !stage('design')) return {status: 'unsupported', reason: 'Required observation or reachable capacity is unavailable.'};
            verify('strategise', candidate.program, stages.slice(0, 3));
            return {status: 'accepted', expectedCost: candidate.program.expectedCost,
                completePolicyCombinations: candidate.combinations, scope: 'Every residual world and admitted route combination enumerated independently.'};
        })) return records;
    }
    for (const incremental of [false, true]) {
        if (!run(incremental ? 'Equally capable incremental contracts' : 'Full recomputation', () => {
            const execution = stage('execute');
            if (!execution) return {status: 'unsupported', reason: 'No accepted finite factor contract.'};
            const old = parent?.stages?.find(value => value.kind === 'execute' && value.status === 'accepted')?.program;
            const relevant = (id, bindings) => id === 'route' ? {policy: bindings.policy, denominator: bindings.denominator}
                : id === 'reference' ? {intendedUses: bindings.intendedUses, availableActions: bindings.availableActions,
                    denominator: bindings.denominator}
                    : {availableActions: bindings.availableActions, vacancy: bindings.vacancy,
                        workerSlots: bindings.workerSlots, denominator: bindings.denominator};
            const retained = incremental && old ? execution.program.factors.filter(factor => {
                tick('checking');
                return same(relevant(factor.id, old.bindings), relevant(factor.id, execution.program.bindings))
                    && old.factors.some(previous => previous.id === factor.id && same(previous, factor));
            }).map(factor => factor.id) : [];
            const reuseContracts = [];
            const components = execution.program.components.map(component => {
                const previous = old?.components.find(value => value.id === component.id);
                const retainedComponent = incremental && previous && component.factorIds.every(id => retained.includes(id))
                    && same(previous.private, component.private) && same(previous.boundary, component.boundary);
                const profiles = retainedComponent ? clone(previous.profiles)
                    : fullProfiles({variables: [...component.private, 'c'], factors: execution.program.factors
                        .filter(factor => component.factorIds.includes(factor.id))}, tick);
                const profileEqual = Boolean(previous && same(previous.profiles.map(row => row.value), profiles.map(row => row.value)));
                reuseContracts.push({component: component.id, status: retainedComponent ? 'retained' : 'rebuilt',
                    completeProfileEqual: profileEqual, propagation: !old ? 'cold' : profileEqual ? 'stopped' : 'continued'});
                return {...clone(component), profiles};
            });
            const stop = incremental && old && reuseContracts.every(value => value.completeProfileEqual);
            const profiles = stop ? [0, 1].map(boundary => {
                tick('checking');
                const witness = Object.fromEntries([...execution.program.variables.filter(name => name !== 'c').map(name =>
                    [name, components.find(component => component.private.includes(name)).profiles[boundary].witness[name]]), ['c', boundary]]);
                return {boundary, value: old.profiles[boundary].value, witness};
            }) : fullProfiles(execution.program, tick);
            const program = {...clone(execution.program), components, reuseContracts, profiles,
                witness: profiles[execution.program.currentBoundary]?.witness, reusedFactors: retained};
            verify('execute', program, stages.slice(0, 4));
            return {status: 'accepted', retainedContracts: retained,
                completeBoundaryProfiles: profiles, scope: 'Complete source-bound factor tables, every finite binary assignment and current whole-artifact acceptance.'};
        })) return records;
    }
    if (!run('Fixed complete certificate', () => {
        const old = parent?.stages?.find(value => value.kind === 'evolve' && value.status === 'accepted');
        if (!old || !same(parent.charter, charter)) return {status: 'unsupported', reason: 'Exact unchanged source and charter are required for this fixed certificate.'};
        verify('evolve', old.program, parent.stages.slice(0, 5));
        return {status: 'accepted', scope: 'Actual retained complete certificate with fresh source-bound finite checks; no compilation replay.'};
    })) return records;
    run('Successor from scratch', () => {
        const reference = records.find(value => value.name === 'Unrestricted same-primitive finite reference');
        if (reference?.status !== 'accepted' || !reference.witness) {
            return {status: 'unsupported', reason: 'The independent complete cold campaign has no qualified witness.'};
        }
        tick('checking');
        return {status: 'accepted', inheritedAssets: [], objective: clone(reference.objective),
            evidenceRef: reference.name, sharedMeasuredWork: clone(reference.measuredWork),
            costAccounting: 'The source-bound cold campaign was already executed in the reference row and is charged there exactly once. This row performs no duplicate replay.',
            scope: 'Complete independently constructed six-stage cold campaign using the current charter and no parent assets, including current semantic qualification. The fixed finite grammar remains the comparison boundary.'};
    });
    return records;
}
