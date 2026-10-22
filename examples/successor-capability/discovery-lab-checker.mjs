// SPDX-License-Identifier: Apache-2.0
/** Separate finite semantic checks; no producer transitions or validators are imported. */
const KINDS = Object.freeze(['learn', 'think', 'design', 'strategise', 'execute', 'evolve']);
const stable = value => Array.isArray(value) ? '[' + value.map(stable).join(',') + ']'
    : value && typeof value === 'object' ? '{' + Object.keys(value).sort()
        .map(key => JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}' : JSON.stringify(value);
const same = (a, b) => stable(a) === stable(b);
const integer = (value, lower, upper) => Number.isSafeInteger(value) && !Object.is(value, -0)
    && value >= lower && value <= upper;
const keys = (value, expected) => value !== null && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join('\0') === [...expected].sort().join('\0');
const need = (condition, message) => { if (!condition) throw Error(message); };

function bounded(value, work) {
    const pending = [[value, 0]];
    let nodes = 0;
    while (pending.length) {
        const [item, depth] = pending.pop();
        work.tick();
        need(++nodes <= 100_000 && depth <= 32, 'Finite input bounds exceeded.');
        if (item === null || typeof item === 'boolean') continue;
        if (typeof item === 'number') {
            need(Number.isFinite(item) && !Object.is(item, -0), 'Non-finite or negative-zero data.');
        } else if (typeof item === 'string') need(item.length <= 100_000, 'Oversized text.');
        else {
            need(typeof item === 'object', 'Only finite data programs are admitted.');
            need(Object.getPrototypeOf(item) === Object.prototype || Array.isArray(item), 'Non-plain data.');
            need(Object.getOwnPropertySymbols(item).length === 0, 'Symbol data is unsupported.');
            for (const [name, descriptor] of Object.entries(Object.getOwnPropertyDescriptors(item))) {
                if (Array.isArray(item) && name === 'length') continue;
                need(Object.hasOwn(descriptor, 'value') && descriptor.enumerable, 'Accessor data is unsupported.');
                pending.push([descriptor.value, depth + 1]);
            }
        }
    }
}

class CheckingExhausted extends Error {}
function meter(limit) {
    let checks = 0;
    return {tick: (n = 1) => {
        if (checks + n > limit) {
            checks = limit;
            throw new CheckingExhausted('checking budget exhausted');
        }
        checks += n;
    }, count: () => checks};
}

const bit = (mask, index) => (mask >> index) & 1;
function response(charter, mask) {
    return 2 + 2 * bit(mask, 0) + 2 * bit(mask, 1) + 4 * bit(mask, 2)
        + (charter.controls === 4 ? 6 * bit(mask, 3) : 0) + 3 * bit(mask, 0) * bit(mask, 1)
        + (charter.hiddenCoupling ? 5 * bit(mask, 0) * bit(mask, 1) * bit(mask, 2) : 0);
}
const drift = (charter, time) => time + (charter.actualDrift === 'quadratic' ? time * time : 0);
function floorRatio(a, b) {
    need(b > 0n, 'Invalid rational denominator.');
    const value = a / b;
    return Number(a < 0n && a % b !== 0n ? value - 1n : value);
}
const ceilRatio = (a, b) => -floorRatio(-a, b);

function checkLearn(charter, program, inputs, work) {
    need(inputs.length === 0, 'Measurement construction cannot have stage dependencies.');
    need(keys(program, ['degree', 'times', 'signs', 'weights', 'referenceAmplitude', 'gainInterval',
        'calibrationRaw', 'queryRows', 'errorBound']), 'Unsupported measurement program fields.');
    need(['linear', 'quadratic'].includes(charter.driftScope)
        && ['linear', 'quadratic'].includes(charter.actualDrift)
        && typeof charter.hiddenCoupling === 'boolean', 'Unsupported supplied sensor semantics.');
    const degree = charter.driftScope === 'quadratic' ? 2 : 1;
    need(program.degree === degree, 'Declared drift scope differs from its program.');
    need(charter.actualDrift !== 'quadratic' || degree === 2, 'Actual drift exceeds the declared polynomial scope.');
    need(integer(charter.controls, 3, 4) && integer(charter.noise, 0, 1)
        && integer(charter.accuracy, 0, 24), 'Unsupported measurement charter.');
    need(Array.isArray(charter.observations) && charter.observations.includes('contrast')
        && charter.observations.includes('reference'), 'The measurement program needs both contrast and reference permission.');
    const size = degree + 2;
    need(Array.isArray(program.times) && program.times.length === size
        && program.times.every(value => integer(value, 0, 8))
        && new Set(program.times).size === size
        && program.times.every((value, index) => index === 0 || value > program.times[index - 1]),
    'Sampling times are not a bounded increasing program.');
    need(Array.isArray(program.signs) && program.signs.length === size && program.signs[0] === 1
        && program.signs.every(value => value === 1 || value === -1), 'Invalid polarity schedule.');
    need(keys(program.weights, ['numerators', 'denominator'])
        && Array.isArray(program.weights.numerators) && program.weights.numerators.length === size
        && program.weights.numerators.every(value => integer(value, -1_000_000, 1_000_000))
        && integer(program.weights.denominator, 1, 1_000_000), 'Invalid rational correction weights.');
    const nums = program.weights.numerators.map(BigInt), denominator = BigInt(program.weights.denominator);
    let signal = 0n;
    for (let index = 0; index < size; index++) {
        signal += nums[index] * BigInt(program.signs[index]); work.tick();
    }
    need(signal === denominator, 'The corrected signal is not normalized.');
    for (let power = 0; power <= degree; power++) {
        let moment = 0n;
        for (let index = 0; index < size; index++) {
            moment += nums[index] * BigInt(program.times[index]) ** BigInt(power); work.tick();
        }
        need(moment === 0n, 'The correction does not cancel every admitted drift moment.');
    }
    need([4, 8, 16].includes(program.referenceAmplitude), 'Unsupported supplied reference amplitude.');
    const amplitude = BigInt(program.referenceAmplitude);
    const expectedRaw = value => program.times.map((time, index) =>
        program.signs[index] * 2 * value + 3 + drift(charter, time));
    const calibration = expectedRaw(program.referenceAmplitude);
    need(same(program.calibrationRaw, calibration), 'Raw reference evidence does not execute the supplied sensor.');
    let contrast = 0n, absolute = 0n;
    for (let index = 0; index < size; index++) {
        contrast += nums[index] * BigInt(calibration[index]);
        absolute += nums[index] < 0n ? -nums[index] : nums[index]; work.tick();
    }
    const error = BigInt(charter.noise) * absolute;
    const lower = contrast - error, upper = contrast + error, gainDenominator = denominator * amplitude;
    need(lower > 0n && keys(program.gainInterval, ['lower', 'upper', 'denominator'])
        && program.gainInterval.lower === Number(lower) && program.gainInterval.upper === Number(upper)
        && program.gainInterval.denominator === Number(gainDenominator), 'The gain interval is missing or inconsistent.');
    need(Array.isArray(program.queryRows) && program.queryRows.length === 2 ** charter.controls,
        'The complete observation/context relation is required.');
    for (let mask = 0; mask < 2 ** charter.controls; mask++) {
        const row = program.queryRows[mask], raw = expectedRaw(response(charter, mask));
        need(keys(row, ['mask', 'raw', 'interval']) && row.mask === mask && same(row.raw, raw),
            'Query evidence is missing, reordered or stale.');
        let z = 0n;
        for (let index = 0; index < size; index++) { z += nums[index] * BigInt(raw[index]); work.tick(); }
        const quotients = [[(z - error) * amplitude, lower], [(z - error) * amplitude, upper],
            [(z + error) * amplitude, lower], [(z + error) * amplitude, upper]];
        const lo = Math.min(...quotients.map(([a, b]) => floorRatio(a, b)));
        const hi = Math.max(...quotients.map(([a, b]) => ceilRatio(a, b)));
        need(same(row.interval, [lo, hi]), 'Interval ambiguity was changed or erased.');
        need(lo <= response(charter, mask) && hi >= response(charter, mask), 'The true supplied response escaped its interval.');
        work.tick(6);
    }
    const bound = ceilRatio((24n + amplitude) * error, lower);
    need(program.errorBound === bound && bound <= charter.accuracy, 'The certified worst-case error exceeds the charter.');
}

function moved(mask, operation, controls) {
    const flips = {'flip-x': 0, 'flip-y': 1, 'flip-z': 2, 'flip-w': 3};
    if (Object.hasOwn(flips, operation)) {
        need(flips[operation] < controls, 'An operation addresses an absent control.');
        return mask ^ (1 << flips[operation]);
    }
    need(operation === 'mix', 'Unsupported reasoning operation.');
    return mask ^ (bit(mask, 0) !== bit(mask, 2) ? 5 : 0);
}

function checkThink(charter, program, inputs, work) {
    need(inputs.length === 1 && inputs[0].kind === 'learn', 'The representation needs current measurement evidence.');
    need(keys(program, ['encoder', 'blocks', 'decoder', 'updates']), 'Unsupported representation program fields.');
    const states = 2 ** charter.controls;
    need(Array.isArray(program.blocks) && program.blocks.length >= 1 && program.blocks.length <= states
        && integer(charter.memory, 1, 32) && program.blocks.length <= charter.memory,
    'The resident representation exceeds its declared memory.');
    const labels = program.blocks.length;
    need(Array.isArray(program.encoder) && program.encoder.length === states
        && program.encoder.every(value => integer(value, 0, labels - 1)), 'The encoder is incomplete.');
    need(Array.isArray(program.decoder) && program.decoder.length === labels, 'The contextual decoder is incomplete.');
    need(Array.isArray(charter.operations) && new Set(charter.operations).size === charter.operations.length
        && charter.operations.length <= 5 && keys(program.updates, charter.operations), 'Unsupported operation/update interface.');
    const seen = new Set();
    for (let label = 0; label < labels; label++) {
        const block = program.blocks[label];
        need(Array.isArray(block) && block.length >= 1 && block.length <= states
            && block.every(value => integer(value, 0, states - 1)), 'Invalid representation fiber.');
        for (const mask of block) {
            need(!seen.has(mask) && program.encoder[mask] === label, 'The encoder and fibers disagree.');
            need(same(program.decoder[label], inputs[0].program.queryRows[mask].interval),
                'The decoder changed its measured interval context.');
            seen.add(mask); work.tick(2);
        }
    }
    need(seen.size === states, 'The representation omits source states.');
    for (const operation of charter.operations) {
        const table = program.updates[operation];
        need(Array.isArray(table) && table.length === labels
            && table.every(value => integer(value, 0, labels - 1)), 'The updater table is incomplete.');
        for (let mask = 0; mask < states; mask++) {
            need(table[program.encoder[mask]] === program.encoder[moved(mask, operation, charter.controls)],
                'An answer-preserving summary cannot execute this update.');
            work.tick();
        }
    }
}

function checkDesign(charter, program, inputs, work) {
    need(inputs.length === 2, 'The realization needs the accepted encoder, decoder and updater.');
    need(keys(program, ['compiled', 'serviceTable', 'footprint', 'workerLimit', 'workersBefore', 'workersAfter',
        'transition', 'vacancy', 'staging']), 'Unsupported service realization fields.');
    const representation = inputs[1].program, groups = representation.blocks.length;
    const operations = charter.operations.length ? charter.operations : ['identity'];
    const updaters = charter.operations.length ? representation.updates
        : {identity: Array.from({length: groups}, (_, index) => index)};
    need(keys(program.compiled, ['decoder', 'updaters', 'operations'])
        && same(program.compiled.decoder, representation.decoder)
        && same(program.compiled.updaters, updaters) && same(program.compiled.operations, operations),
    'The compiled services are not the accepted contextual decoder and updater.');
    need(Array.isArray(program.serviceTable) && program.serviceTable.length === groups * groups,
        'The joint kernel omits independently varying service inputs.');
    for (let a = 0; a < groups; a++) for (let b = 0; b < groups; b++) {
        need(same(program.serviceTable[groups * a + b],
            [a, b, representation.decoder[a][0], representation.decoder[a][1], ...operations.map(operation => updaters[operation][b])]),
            'The joint program fails a complete independent-input service case.');
        work.tick();
    }
    let footprint = representation.decoder.length * 2 + 4;
    for (const table of Object.values(updaters)) { footprint += table.length; work.tick(table.length); }
    need(integer(charter.workerCapacity, 2, 4) && ['right', 'wrong', 'staged'].includes(charter.topology),
        'Unsupported worker topology.');
    need(program.footprint === footprint && program.workerLimit === charter.memory * 8
        && footprint <= program.workerLimit, 'The emitted decoder/updater and joint program exceed the worker envelope.');
    const before = Array.from({length: charter.workerCapacity}, (_, index) =>
        ({location: index === 0 ? 'left' : index === 1 ? 'right' : 'aux', services: [index]}));
    const packedAt = charter.topology === 'right' ? 'left' : 'right';
    const packed = before.map(worker => ({location: worker.location,
        services: worker.location === packedAt ? [0, 1]
            : worker.location === (packedAt === 'left' ? 'right' : 'left') ? [] : worker.services}));
    const after = charter.topology !== 'staged' ? packed : before.map(worker => ({location: worker.location,
        services: worker.location === 'left' ? [0, 1] : worker.location === 'right' ? [] : worker.services}));
    const phases = charter.topology === 'staged' ? [before, packed, after] : [before, after];
    need(same(program.workersBefore, before) && same(program.workersAfter, after)
        && same(program.transition, phases) && program.staging === (charter.topology === 'staged'),
    'The release route is not reachable through the supplied atomic handovers.');
    for (const phase of program.transition) {
        need(phase.length === charter.workerCapacity, 'A transition silently introduced worker capacity.');
        const active = [];
        for (const worker of phase) {
            need(keys(worker, ['location', 'services']) && Array.isArray(worker.services) && worker.services.length <= 2,
                'A worker exceeds the simultaneous service limit.');
            active.push(...worker.services); work.tick(worker.services.length + 1);
        }
        active.sort((a, b) => a - b);
        need(same(active, Array.from({length: charter.workerCapacity}, (_, index) => index)),
            'A required service was dropped or duplicated during the handover.');
    }
    const finalVacancies = after.filter(worker => worker.services.length === 0);
    need(finalVacancies.length === 1 && program.vacancy === finalVacancies[0].location,
        'Released capacity is claimed at the wrong location.');
}

function checkStrategise(charter, program, inputs, work) {
    need(inputs.length === 3 && inputs[2].program.vacancy === 'right',
        'The policy requires a genuinely reachable installation vacancy.');
    need(keys(program, ['observation', 'leaves', 'expectedCost', 'reservations']), 'Unsupported conditional policy fields.');
    need(['none', 'coarse', 'full'].includes(program.observation)
        && (program.observation === 'none' || charter.observations.includes(program.observation)),
    'The selected diagnostic observation is not permitted.');
    const worlds = charter.faultHypotheses;
    need(Array.isArray(worlds) && worlds.length >= 1 && worlds.length <= 4
        && new Set(worlds).size === worlds.length
        && worlds.every(world => ['clear', 'left', 'right', 'both'].includes(world)), 'The fault hypothesis set is unsupported.');
    need(Array.isArray(charter.checkpoints) && charter.checkpoints.length <= 2
        && new Set(charter.checkpoints).size === charter.checkpoints.length
        && charter.checkpoints.every(checkpoint => ['safety', 'sterile'].includes(checkpoint)),
    'The required checkpoint interface is unsupported.');
    const groups = [];
    if (program.observation === 'none') groups.push(worlds);
    else if (program.observation === 'full') groups.push(...worlds.map(world => [world]));
    else {
        for (const partition of [['clear', 'left'], ['right', 'both']]) {
            const group = worlds.filter(world => partition.includes(world));
            if (group.length) groups.push(group);
        }
    }
    need(Array.isArray(program.leaves) && program.leaves.length === groups.length, 'The observation policy omits branches.');
    const seen = new Set();
    let costSum = (program.observation === 'coarse' ? 1 : program.observation === 'full' ? 2 : 0) * worlds.length;
    for (const leaf of program.leaves) {
        need(keys(leaf, ['worlds', 'route', 'visits', 'constructionActions', 'checkpoints', 'cost']) && Array.isArray(leaf.worlds)
            && leaf.worlds.length >= 1 && new Set(leaf.worlds).size === leaf.worlds.length,
        'Malformed residual belief.');
        const groupIndex = groups.findIndex(group => same([...group].sort(), [...leaf.worlds].sort()));
        need(groupIndex >= 0 && !seen.has(groupIndex), 'The residual belief contradicts its observation.');
        seen.add(groupIndex);
        need(['L', 'R', 'bypass'].includes(leaf.route) && same(leaf.checkpoints, charter.checkpoints),
            'A mandatory processing checkpoint was omitted.');
        const sterile = charter.checkpoints.includes('sterile');
        const visits = ['source', 'safety', ...(sterile ? ['sterile'] : []),
            leaf.route === 'L' ? 'left' : leaf.route === 'R' ? 'right' : 'bypass', 'sink'];
        need(same(leaf.visits, visits)
            && same(leaf.constructionActions, sterile ? ['install-sterile-checkpoint'] : []),
        'The route omits an actual checkpoint visit or its construction action.');
        for (const world of leaf.worlds) {
            need(leaf.route === 'bypass' || leaf.route === 'L' && !['left', 'both'].includes(world)
                || leaf.route === 'R' && !['right', 'both'].includes(world),
            'The same route fails in a remaining fault world.');
            work.tick();
        }
        const routeCost = (leaf.route === 'bypass' ? 5 : 1) + (charter.checkpoints.includes('sterile') ? 2 : 0);
        need(leaf.cost === routeCost, 'Route/checkpoint work was not fully charged.');
        costSum += leaf.worlds.length * routeCost; work.tick();
    }
    need(keys(program.expectedCost, ['numerator', 'denominator'])
        && integer(program.expectedCost.numerator, 0, 1000) && integer(program.expectedCost.denominator, 1, 64)
        && program.expectedCost.numerator * worlds.length === costSum * program.expectedCost.denominator,
    'The expected policy cost differs from its complete branch account.');
    need(keys(program.reservations, ['vacancy', 'installations']) && program.reservations.vacancy === 'right'
        && program.reservations.installations === 1, 'The installation reservation is incompatible.');
}

function checkExecute(charter, program, inputs, work) {
    need(inputs.length === 4, 'Execution contracts need the accepted workcell and policy.');
    need(keys(program, ['variables', 'factors', 'components', 'profiles', 'bindings', 'witness', 'routeWitness',
        'currentBoundary', 'reusedFactors', 'reuseContracts', 'installations'])
        && same(program.variables, ['a', 'b', 'r', 'c']), 'Unsupported completion contract fields.');
    const denominator = inputs[3].program.expectedCost.denominator;
    const basePolicyNumerator = inputs[3].program.expectedCost.numerator
        - (charter.checkpoints.includes('sterile') ? 2 * denominator : 0);
    const observationCost = inputs[3].program.observation === 'none' ? 0
        : inputs[3].program.observation === 'coarse' ? 1 : 2;
    const bypassPolicyNumerator = (observationCost + 5) * denominator;
    need(keys(program.bindings, ['checkpoint', 'policy', 'availableActions', 'vacancy', 'workerSlots',
        'denominator', 'intendedUses', 'compiledServices', 'residentWords'])
        && program.bindings.checkpoint === (charter.checkpoints.includes('sterile') ? 'sterile' : 'safety')
        && same(program.bindings.policy, inputs[3].program)
        && same(program.bindings.availableActions, ['isolate', 'reference'])
        && program.bindings.vacancy === 'right' && inputs[2].program.vacancy === 'right'
        && program.bindings.workerSlots === 1 && inputs[3].program.reservations.installations === 1
        && program.bindings.denominator === denominator && program.bindings.intendedUses === charter.intendedUses
        && same(program.bindings.compiledServices, inputs[2].program.compiled)
        && program.bindings.residentWords === inputs[2].program.footprint,
    'The completion contract uses a stale interface, resource reservation or policy.');
    const expectedFactors = {
        prepare: {scope: ['a'], cost: a => 2 * a * denominator},
        reference: {scope: ['b'], cost: b => b * charter.intendedUses * denominator},
        capacity: {scope: ['a', 'b'], cost: (a, b) => a + b === 1 ? 0 : null},
        route: {scope: ['r', 'c'], cost: (r, c) => (r === 0 ? basePolicyNumerator : bypassPolicyNumerator) + 2 * c * denominator},
        checkpoint: {scope: ['b', 'c'], cost: (b, c) => c === 1 && b === 0 ? null : 0}
    };
    need(Array.isArray(program.factors) && program.factors.length === Object.keys(expectedFactors).length,
        'A declared factor was omitted or duplicated.');
    const byId = new Map();
    for (const factor of program.factors) {
        need(keys(factor, ['id', 'scope', 'table']) && Object.hasOwn(expectedFactors, factor.id)
            && !byId.has(factor.id) && Array.isArray(factor.scope)
            && same(factor.scope, expectedFactors[factor.id].scope)
            && Array.isArray(factor.table) && factor.table.length === 2 ** factor.scope.length,
        'A factor scope is missing, duplicated or crosses hidden private components.');
        const assignments = new Set();
        for (const row of factor.table) {
            need(keys(row, ['values', 'cost']) && Array.isArray(row.values)
                && row.values.length === factor.scope.length && row.values.every(value => value === 0 || value === 1)
                && (row.cost === null || integer(row.cost, 0, 1000)), 'An explicit factor table row is invalid.');
            const code = row.values.join('');
            need(!assignments.has(code), 'A factor assignment is duplicated.');
            need(row.cost === expectedFactors[factor.id].cost(...row.values),
                'A factor cost does not execute the actual policy, horizon or resource constraint.');
            assignments.add(code); work.tick();
        }
        byId.set(factor.id, factor);
    }
    const factorCost = (assignment, ids = null) => {
        let total = 0;
        for (const factor of program.factors) {
            if (ids && !ids.includes(factor.id)) continue;
            const row = factor.table.find(entry => factor.scope.every((name, index) => assignment[name] === entry.values[index]));
            need(Boolean(row), 'The contract omits an admissible assignment.');
            work.tick();
            if (row.cost === null) return null;
            total += row.cost;
        }
        return total;
    };
    const trueCost = assignment => assignment.a + assignment.b !== 1 || assignment.c === 1 && assignment.b === 0 ? null
        : 2 * assignment.a * denominator + assignment.b * charter.intendedUses * denominator
            + (assignment.r === 0 ? basePolicyNumerator : bypassPolicyNumerator) + 2 * assignment.c * denominator
            + (charter.hiddenCoupling ? 5 * assignment.a * assignment.r * denominator : 0);
    const minima = [null, null], witnesses = [null, null];
    for (let c = 0; c <= 1; c++) for (let a = 0; a <= 1; a++) for (let b = 0; b <= 1; b++) for (let r = 0; r <= 1; r++) {
        const assignment = {a, b, r, c}, value = factorCost(assignment);
        need(value === trueCost(assignment), 'Complete supplied scopes do not represent the true current cost system.');
        if (value !== null && (minima[c] === null || value < minima[c])) {
            minima[c] = value; witnesses[c] = assignment;
        }
        work.tick();
    }
    const plans = {
        installation: {private: ['a', 'b'], factorIds: ['prepare', 'reference', 'capacity', 'checkpoint']},
        routing: {private: ['r'], factorIds: ['route']}
    };
    need(Array.isArray(program.components) && program.components.length === 2,
        'The complete modular boundary contracts are missing.');
    const components = new Map(), ownedFactors = new Set();
    for (const component of program.components) {
        need(keys(component, ['id', 'private', 'boundary', 'factorIds', 'profiles'])
            && Object.hasOwn(plans, component.id) && !components.has(component.id),
        'A boundary component is missing, duplicated or unsupported.');
        const plan = plans[component.id];
        need(same(component.private, plan.private) && same(component.boundary, ['c'])
            && Array.isArray(component.factorIds) && same([...component.factorIds].sort(), [...plan.factorIds].sort())
            && Array.isArray(component.profiles) && component.profiles.length === 2,
        'Private variables, factor ownership or the complete boundary domain changed.');
        for (const id of component.factorIds) {
            need(!ownedFactors.has(id) && byId.get(id).scope.every(name => name === 'c' || component.private.includes(name)),
                'A factor is duplicated or crosses distinct private modules.');
            ownedFactors.add(id); work.tick();
        }
        for (let c = 0; c <= 1; c++) {
            let best = null;
            for (let mask = 0; mask < 2 ** component.private.length; mask++) {
                const assignment = Object.fromEntries(component.private.map((name, index) =>
                    [name, bit(mask, component.private.length - 1 - index)]));
                assignment.c = c;
                const value = factorCost(assignment, component.factorIds);
                if (value !== null && (!best || value < best.value)) best = {boundary: c, value, witness: assignment};
                work.tick();
            }
            need(same(component.profiles[c], best), 'A local complete boundary row or its current attaining witness is wrong.');
        }
        components.set(component.id, component);
    }
    need(ownedFactors.size === byId.size, 'A factor escaped the modular decomposition.');
    need(Array.isArray(program.profiles) && program.profiles.length === 2, 'The complete boundary value profile is missing.');
    for (let boundary = 0; boundary <= 1; boundary++) {
        const row = program.profiles[boundary];
        need(keys(row, ['boundary', 'value', 'witness']) && row.boundary === boundary
            && row.value === minima[boundary] && same(row.witness, witnesses[boundary]),
        'A full boundary entry or attaining current witness is wrong.');
        const installation = components.get('installation').profiles[boundary];
        const routing = components.get('routing').profiles[boundary];
        need(row.value === installation.value + routing.value
            && same(row.witness, {...installation.witness, r: routing.witness.r}),
        'The current global completion does not compose the full checked boundary contracts.');
        work.tick();
    }
    const current = charter.checkpoints.includes('sterile') ? 1 : 0;
    need(program.currentBoundary === current && same(program.witness, witnesses[current]),
        'The old answer was reused instead of materializing the current boundary witness.');
    need(Array.isArray(program.reusedFactors) && new Set(program.reusedFactors).size === program.reusedFactors.length
        && program.reusedFactors.every(id => byId.has(id)), 'Unsupported reused factor claim.');
    need(Array.isArray(program.reuseContracts) && program.reuseContracts.length === 2,
        'The component propagation decisions are missing.');
    const decisions = new Set();
    for (const decision of program.reuseContracts) {
        need(keys(decision, ['component', 'status', 'completeProfileEqual', 'propagation'])
            && components.has(decision.component) && !decisions.has(decision.component)
            && ['retained', 'rebuilt'].includes(decision.status) && typeof decision.completeProfileEqual === 'boolean'
            && ['stopped', 'continued', 'cold'].includes(decision.propagation),
        'The component reuse or propagation declaration is unsupported.');
        decisions.add(decision.component); work.tick();
    }
    const policy = inputs[3].program;
    const routeLeaves = witnesses[current].r === 0 ? policy.leaves : policy.leaves.map(leaf => ({...leaf,
        route: 'bypass', cost: 5 + 2 * current,
        visits: ['source', 'safety', ...(current ? ['sterile'] : []), 'bypass', 'sink']}));
    need(keys(program.routeWitness, ['observation', 'leaves']) && program.routeWitness.observation === policy.observation
        && same(program.routeWitness.leaves, routeLeaves),
    'The current routing witness was not rematerialized from the accepted policy and boundary choice.');
    need(keys(program.installations, ['actions', 'placement', 'scopeControls'])
        && same(program.installations.actions, [witnesses[current].a === 1 ? 'isolate' : 'reference'])
        && program.installations.placement === 'right' && program.installations.scopeControls === charter.controls,
    'The installed capability does not realize the current accepted completion witness.');
}

function checkPlatformShape(charter, program) {
    need(keys(program, ['operations', 'responseTable', 'coefficients', 'degree', 'scopeControls', 'freezeOrder']),
        'Unsupported structural construction fields.');
    need(Array.isArray(program.operations) && program.operations.length <= 3
        && new Set(program.operations).size === program.operations.length
        && program.operations.every(operation => ['isolate', 'reference', 'modularize'].includes(operation)),
    'The platform construction exceeds its supplied grammar.');
    need(program.scopeControls === charter.controls && program.degree === 1
        && program.freezeOrder === 'before-query-evaluation', 'The platform scope or procedural freeze changed.');
}

function checkPlatformSemantics(charter, program, work) {
    const states = 2 ** charter.controls;
    need(Array.isArray(program.responseTable) && program.responseTable.length === states
        && Array.isArray(program.coefficients) && program.coefficients.length === states,
    'Structural qualification requires the complete finite response cube.');
    for (let mask = 0; mask < states; mask++) {
        const expected = response(charter, mask) - (program.operations.length ? 3 * bit(mask, 0) * bit(mask, 1) : 0);
        need(program.responseTable[mask] === expected, 'The response table is not the semantics of the installed construction.');
        work.tick();
    }
    for (let mask = 0; mask < states; mask++) {
        let coefficient = 0;
        const countBits = value => {
            let total = 0;
            for (let index = 0; index < charter.controls; index++) { total += bit(value, index); work.tick(); }
            return total;
        };
        const degree = countBits(mask);
        for (let subset = mask; ; subset = (subset - 1) & mask) {
            coefficient += (degree - countBits(subset)) % 2 ? -program.responseTable[subset] : program.responseTable[subset];
            work.tick();
            if (subset === 0) break;
        }
        need(program.coefficients[mask] === coefficient, 'A claimed interaction coefficient does not match full-cube semantics.');
        need(degree <= program.degree || coefficient === 0, 'A hidden higher-order interaction violates the claimed structure.');
    }
}

function checkEvolve(charter, program, inputs, work) {
    need(inputs.length === 5, 'The successor platform needs the accepted executable capability.');
    checkPlatformShape(charter, program);
    const installed = inputs[4].program.installations;
    need(same(program.operations, installed.actions) && installed.placement === 'right'
        && installed.scopeControls === charter.controls,
    'The platform construction is not the installed current execution capability.');
    checkPlatformSemantics(charter, program, work);
}

/** Independently check the query family from the frozen platform and certified sensor bound. */
export function checkQueries(charter, evolveProgram, learnProgram, queryResults, options = {}) {
    const descriptor = options && typeof options === 'object'
        ? Object.getOwnPropertyDescriptor(options, 'maxChecks') : null;
    const limit = descriptor && Object.hasOwn(descriptor, 'value') ? descriptor.value : 1_000_000;
    const work = meter(integer(limit, 0, 1_000_000) ? limit : 0);
    try {
        need((keys(options, []) || keys(options, ['maxChecks']) && descriptor && Object.hasOwn(descriptor, 'value'))
            && integer(limit, 0, 1_000_000), 'Unsupported checker budget.');
        bounded({charter, evolveProgram, learnProgram, queryResults}, work);
        checkLearn(charter, learnProgram, [], work);
        checkPlatformShape(charter, evolveProgram);
        checkPlatformSemantics(charter, evolveProgram, work);
        need(keys(queryResults, ['thresholdScreening', 'inverseDesign', 'constrainedSelection', 'intervals',
            'queriesAfterFreeze']) && queryResults.queriesAfterFreeze === true,
        'The downstream query report is missing or precedes the procedural freeze.');
        const states = 2 ** charter.controls, error = learnProgram.errorBound;
        need(Array.isArray(queryResults.intervals) && queryResults.intervals.length === states,
            'The downstream uncertainty intervals are incomplete.');
        const screening = [], definite = [], possible = [], eligible = [];
        for (let mask = 0; mask < states; mask++) {
            work.tick();
            const value = evolveProgram.responseTable[mask], low = value - error, high = value + error;
            need(same(queryResults.intervals[mask], [low, high]),
                'A downstream interval erased or changed the certified sensor uncertainty.');
            screening.push({mask, outcome: low >= 8 ? 'accepted' : high < 8 ? 'rejected' : 'ambiguous'});
            if (low === 8 && high === 8) definite.push(mask);
            if (low <= 8 && high >= 8) possible.push(mask);
            let active = 0;
            for (let index = 0; index < charter.controls; index++) { work.tick(); active += bit(mask, index); }
            if (active <= 2) eligible.push({mask, low, high, value});
        }
        need(keys(queryResults.thresholdScreening, ['threshold', 'results'])
            && queryResults.thresholdScreening.threshold === 8
            && same(queryResults.thresholdScreening.results, screening),
        'Threshold screening contradicts the current interval evidence.');
        need(keys(queryResults.inverseDesign, ['target', 'definite', 'possible'])
            && queryResults.inverseDesign.target === 8 && same(queryResults.inverseDesign.definite, definite)
            && same(queryResults.inverseDesign.possible, possible),
        'Inverse-design certainty or possible solutions were changed.');
        let bestLower = null, exactMaximum = null;
        for (const row of eligible) {
            work.tick();
            if (bestLower === null || row.low > bestLower) bestLower = row.low;
            if (exactMaximum === null || row.value > exactMaximum) exactMaximum = row.value;
        }
        const candidates = [], optima = [];
        for (const row of eligible) {
            work.tick();
            if (row.high >= bestLower) candidates.push(row.mask);
            if (row.value === exactMaximum) optima.push(row.mask);
        }
        need(keys(queryResults.constrainedSelection, ['maximumActiveControls', 'candidates', 'suppliedModelOptima',
            'uncertainty']) && queryResults.constrainedSelection.maximumActiveControls === 2
            && same(queryResults.constrainedSelection.candidates, candidates)
            && same(queryResults.constrainedSelection.suppliedModelOptima, optima)
            && queryResults.constrainedSelection.uncertainty === (error === 0 ? 'exact-within-supplied-model' : 'interval-ambiguity-retained'),
        'Constrained selection lost a valid tie, admitted an impossible candidate or erased ambiguity.');
        return {accepted: true, checks: work.count(), reason: 'Every frozen-platform downstream query passed independent finite checking.'};
    } catch (error) {
        if (error instanceof CheckingExhausted) {
            return {accepted: false, inconclusive: true, checks: work.count(), reason: error.message};
        }
        return {accepted: false, checks: work.count(), reason: String(error.message || error)};
    }
}

/** Check a generated stage against the supplied finite charter and its actual input artifacts. */
export function checkStage(kind, charter, program, inputs = [], options = {}) {
    const descriptor = options && typeof options === 'object'
        ? Object.getOwnPropertyDescriptor(options, 'maxChecks') : null;
    const limit = descriptor && Object.hasOwn(descriptor, 'value') ? descriptor.value : 1_000_000;
    const work = meter(integer(limit, 0, 1_000_000) ? limit : 0);
    try {
        need((keys(options, []) || keys(options, ['maxChecks']) && descriptor && Object.hasOwn(descriptor, 'value'))
            && integer(limit, 0, 1_000_000), 'Unsupported checker budget.');
        bounded({charter, program, inputs}, work);
        need(KINDS.includes(kind), 'Unsupported stage discriminator.');
        need(program && typeof program === 'object' && !Array.isArray(program), 'Executable data program is missing.');
        need(Array.isArray(inputs) && inputs.length <= 5, 'Invalid stage inputs.');
        const implementations = {learn: checkLearn, think: checkThink, design: checkDesign, strategise: checkStrategise,
            execute: checkExecute, evolve: checkEvolve};
        const index = KINDS.indexOf(kind);
        need(inputs.length === index, 'The complete ordered dependency chain is required.');
        for (let prior = 0; prior < index; prior++) {
            const artifact = inputs[prior];
            need(artifact.kind === KINDS[prior] && artifact.status === 'accepted', 'A required input artifact is not currently accepted.');
            need(Object.hasOwn(implementations, artifact.kind), 'A required input checker is not installed.');
            implementations[artifact.kind](charter, artifact.program, inputs.slice(0, prior), work);
        }
        need(Object.hasOwn(implementations, kind), 'A required stage checker is not installed.');
        implementations[kind](charter, program, inputs, work);
        return {accepted: true, checks: work.count(), reason: 'Every finite semantic obligation passed.'};
    } catch (error) {
        if (error instanceof CheckingExhausted) {
            return {accepted: false, inconclusive: true, checks: work.count(), reason: error.message};
        }
        return {accepted: false, checks: work.count(), reason: String(error.message || error)};
    }
}
