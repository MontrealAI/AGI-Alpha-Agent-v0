// SPDX-License-Identifier: Apache-2.0
/** Finite deterministic nuisance-channel interpreter. Certificates concern this model only. */
export const RUNTIME_VERSION = 'out-evolve-runtime/v1';
export const AST_SCHEMA = 'out-evolve-ast/v1';
const clone = value => JSON.parse(JSON.stringify(value));
const fail = message => { throw Error(message); };
const id = value => typeof value === 'string' && /^[a-z][a-z0-9-]{0,79}$/.test(value);
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const integer = (value, max = 1_000_000) => Number.isSafeInteger(value) && !Object.is(value, -0)
    && value >= 0 && value <= max;
const gain = value => !Object.is(value, -0) && [0, 0.5, 1].includes(value);
const setOf = (values, allowed) => Array.isArray(values) && values.length > 0 && values.length <= allowed.length
    && new Set(values).size === values.length && values.every(value => allowed.includes(value));

function dataOnly(input) {
    const seen = new WeakSet(); let nodes = 0;
    function inspect(value, depth) {
        if (++nodes > 20_000 || depth > 32) fail('Input exceeds finite data bounds.');
        if (value === null || typeof value === 'boolean') return;
        if (typeof value === 'string') {
            if (value.length > 10_000) fail('Input string exceeds data bound.');
            return;
        }
        if (typeof value === 'number') {
            if (!Number.isFinite(value) || Object.is(value, -0)) fail('Invalid finite numeric data.');
            return;
        }
        if (typeof value !== 'object' || seen.has(value)) fail('Only finite JSON data trees are accepted.');
        const prototype = Object.getPrototypeOf(value);
        if (prototype !== Object.prototype && prototype !== Array.prototype) fail('Unsupported data prototype.');
        if (Object.getOwnPropertySymbols(value).length) fail('Symbol data is unsupported.');
        seen.add(value);
        for (const [key, descriptor] of Object.entries(Object.getOwnPropertyDescriptors(value))) {
            if (key === 'length' && Array.isArray(value)) continue;
            if (!Object.hasOwn(descriptor, 'value') || !descriptor.enumerable) fail('Accessor data is unsupported.');
            inspect(descriptor.value, depth + 1);
        }
        seen.delete(value);
    }
    inspect(input, 0);
}

export function validateApparatus(input) {
    dataOnly(input);
    if (!exact(input, ['schema', 'id', 'channels', 'edges', 'scope', 'tolerance', 'primitives', 'limits'])
        || input.schema !== 'out-evolve-apparatus/v1' || !id(input.id)
        || !setOf(input.scope, ['standard', 'reservoir']) || !integer(input.tolerance)
        || !Array.isArray(input.channels) || !input.channels.length || input.channels.length > 8
        || !Array.isArray(input.edges) || input.edges.length > 24
        || !Array.isArray(input.primitives) || !input.primitives.length || input.primitives.length > 64) {
        fail('Malformed apparatus contract.');
    }
    const channels = new Set();
    for (const channel of input.channels) {
        if (!exact(channel, ['id', 'initial', 'drift', 'cap', 'scopes']) || !id(channel.id)
            || channel.id === 'readout' || channel.id === 'productive' || channels.has(channel.id)
            || !integer(channel.cap) || !integer(channel.initial, channel.cap)
            || !integer(channel.drift, channel.cap) || !setOf(channel.scopes, ['standard', 'reservoir'])) {
            fail('Malformed nuisance state or support scope.');
        }
        channels.add(channel.id);
    }
    const edges = new Set();
    const adjacency = Object.fromEntries([...channels].map(key => [key, []]));
    for (const edge of input.edges) {
        if (!exact(edge, ['id', 'from', 'to', 'gain']) || !id(edge.id) || edges.has(edge.id)
            || !channels.has(edge.from) || (!channels.has(edge.to) && edge.to !== 'readout')
            || !gain(edge.gain)) fail('Malformed apparatus graph or bounded gain.');
        edges.add(edge.id);
        if (edge.to !== 'readout') adjacency[edge.from].push(edge.to);
    }
    const visiting = new Set(), visited = new Set();
    function visit(key) {
        if (visiting.has(key)) fail('Cyclic apparatus graph.');
        if (visited.has(key)) return;
        visiting.add(key); adjacency[key].forEach(visit); visiting.delete(key); visited.add(key);
    }
    [...channels].forEach(visit);
    const primitives = new Set(input.primitives.map(item => item.id));
    if (primitives.size !== input.primitives.length) fail('Duplicate primitive.');
    const effects = {shield: ['installed'], route: ['installed'], sensor: ['installed'],
        attenuate: ['nuisance', 'transfer'], reference: ['observations'], destroy: ['productive']};
    for (const primitive of input.primitives) {
        if (!exact(primitive, ['id', 'phase', 'kind', 'target', 'gain', 'cost', 'requires', 'effects', 'support'])
            || !id(primitive.id) || !Object.hasOwn(effects, primitive.kind) || !integer(primitive.cost)
            || !gain(primitive.gain) || !Array.isArray(primitive.requires)
            || primitive.requires.length > 16 || new Set(primitive.requires).size !== primitive.requires.length
            || !primitive.requires.every(key => primitives.has(key))
            || JSON.stringify(primitive.effects) !== JSON.stringify(effects[primitive.kind])
            || !exact(primitive.support, ['scopes', 'boundedGain'])
            || !setOf(primitive.support.scopes, ['standard', 'reservoir'])
            || primitive.support.boundedGain !== primitive.gain) fail('Undeclared primitive semantics or effects.');
        const install = ['shield', 'route', 'sensor'].includes(primitive.kind);
        if (primitive.phase !== (install ? 'install' : 'prepare')
            || (primitive.kind === 'route' ? !edges.has(primitive.target)
                : primitive.kind === 'destroy' ? primitive.target !== 'productive' : !channels.has(primitive.target))
            || (primitive.kind !== 'attenuate' && primitive.kind !== 'destroy' && primitive.gain !== 1)
            || (primitive.kind === 'destroy' && primitive.gain !== 0)) fail('Invalid primitive target or phase.');
        for (const requirement of primitive.requires) {
            if (input.primitives.find(item => item.id === requirement).phase !== 'install') {
                fail('Guards must refer to installations.');
            }
        }
        if (primitive.kind === 'reference' && !primitive.requires.some(key => {
            const sensor = input.primitives.find(item => item.id === key);
            return sensor.kind === 'sensor' && sensor.target === primitive.target;
        })) fail('Reference requires a matching synchronous nuisance sensor.');
    }
    if (!exact(input.limits, ['maxInstructions', 'maxRepeat', 'maxCost', 'maxCycles'])
        || !integer(input.limits.maxInstructions, 64) || input.limits.maxInstructions < 1
        || !integer(input.limits.maxRepeat, 32) || input.limits.maxRepeat < 1
        || !integer(input.limits.maxCost) || !integer(input.limits.maxCycles, 4096)
        || input.limits.maxCycles < 1) fail('Unsafe interpreter resource limits.');
    return clone(input);
}

export function compile(input, ast) {
    dataOnly(ast);
    const apparatus = validateApparatus(input);
    if (!exact(ast, ['schema', 'installations', 'prepare', 'scope']) || ast.schema !== AST_SCHEMA
        || !Array.isArray(ast.installations) || ast.installations.length > apparatus.limits.maxInstructions
        || new Set(ast.installations).size !== ast.installations.length
        || !setOf(ast.scope, ['standard', 'reservoir'])) fail('Malformed typed AST.');
    const catalogue = new Map(apparatus.primitives.map(item => [item.id, item]));
    const flattened = [];
    let nodes = 0;
    function walk(node, depth = 0) {
        if (++nodes > 256 || depth > 8) fail('AST structure exceeds resource bounds.');
        if (exact(node, ['op', 'id']) && node.op === 'primitive') {
            const primitive = catalogue.get(node.id);
            if (!primitive || primitive.phase !== 'prepare') fail('Unsupported prepare primitive.');
            flattened.push(node.id);
        } else if (exact(node, ['op', 'steps']) && node.op === 'sequence' && Array.isArray(node.steps)
            && node.steps.length <= apparatus.limits.maxInstructions) node.steps.forEach(item => walk(item, depth + 1));
        else if (exact(node, ['op', 'count', 'body']) && node.op === 'repeat'
            && integer(node.count, apparatus.limits.maxRepeat) && node.count > 0) {
            for (let index = 0; index < node.count; index++) walk(node.body, depth + 1);
        } else fail('Malformed or unbounded AST instruction.');
        if (flattened.length + ast.installations.length > apparatus.limits.maxInstructions) {
            fail('Program exceeds instruction bound.');
        }
    }
    for (const key of ast.installations) {
        if (!catalogue.has(key) || catalogue.get(key).phase !== 'install') fail('Unsupported installation.');
    }
    walk(ast.prepare);
    return {schema: AST_SCHEMA, runtime: RUNTIME_VERSION, installations: [...ast.installations],
        steps: flattened, scope: [...ast.scope]};
}

export function validateAST(apparatus, ast) {
    compile(apparatus, ast);
    return clone(ast);
}

export function initialState(input, scope = input.scope) {
    const apparatus = validateApparatus(input);
    if (!setOf(scope, ['standard', 'reservoir'])) fail('Invalid state scope.');
    return {bounds: Object.fromEntries(apparatus.channels.map(item => [item.id, item.initial])),
        transfer: Object.fromEntries(apparatus.channels.map(item => [item.id, 1])), installed: [], references: [],
        productive: 1, cost: 0, steps: 0, scope: [...scope]};
}

export function step(input, prior, primitiveId) {
    const primitive = input.primitives.find(item => item.id === primitiveId);
    if (!primitive) fail('Unknown primitive.');
    if (!primitive.requires.every(key => prior.installed.includes(key))) fail('Primitive guard not satisfied.');
    if (!prior.scope.every(key => primitive.support.scopes.includes(key))) fail('Primitive outside support envelope.');
    const state = clone(prior);
    if (primitive.phase === 'install' && state.installed.includes(primitiveId)) fail('Installation already present.');
    state.cost += primitive.cost; state.steps++;
    if (!integer(state.cost, input.limits.maxCost) || state.steps > input.limits.maxInstructions) {
        fail('Interpreter resource overflow.');
    }
    if (primitive.phase === 'install') state.installed.push(primitiveId);
    else if (primitive.kind === 'attenuate') {
        state.bounds[primitive.target] *= primitive.gain;
        state.transfer[primitive.target] *= primitive.gain;
    } else if (primitive.kind === 'reference') {
        if (!state.references.includes(primitive.target)) state.references.push(primitive.target);
    } else if (primitive.kind === 'destroy') state.productive = 0;
    state.installed.sort(); state.references.sort();
    return state;
}

export function semanticKey(input, state) {
    return JSON.stringify({bounds: state.bounds, transfer: state.transfer, installed: state.installed,
        references: state.references, productive: state.productive, scope: state.scope});
}

export function prepare(input, ast) {
    const program = compile(input, ast);
    let state = initialState(input, program.scope);
    for (const key of [...program.installations, ...program.steps]) state = step(input, state, key);
    return state;
}

function pathWeights(apparatus, state) {
    const routed = new Set(apparatus.primitives.filter(item => item.kind === 'route'
        && state.installed.includes(item.id)).map(item => item.target));
    const cache = new Map([['readout', 1]]);
    function weight(key) {
        if (!cache.has(key)) cache.set(key, apparatus.edges.filter(edge => edge.from === key && !routed.has(edge.id))
            .reduce((total, edge) => total + edge.gain * weight(edge.to), 0));
        return cache.get(key);
    }
    return Object.fromEntries(apparatus.channels.map(item => [item.id, weight(item.id)]));
}

function recurringEnvelope(channel, a, d) {
    if (a === 0) return {first: d, invariant: d};
    if (a === 1) return {first: Math.min(channel.cap, channel.initial + d),
        invariant: d ? channel.cap : channel.initial};
    const denominator = 1n << BigInt(-Math.log2(a));
    const ceil = (numerator, divisor) => Number((numerator + divisor - 1n) / divisor);
    const first = Math.min(channel.cap, ceil(BigInt(channel.initial) + BigInt(d) * denominator, denominator));
    const steady = Math.min(channel.cap, ceil(BigInt(d) * denominator, denominator - 1n));
    return {first, invariant: Math.max(first, steady)};
}

export function qualify(input, ast) {
    const apparatus = validateApparatus(input), state = prepare(apparatus, ast), program = compile(apparatus, ast);
    const weights = pathWeights(apparatus, state);
    const envelopes = {}, coefficients = {}, recurrence = {};
    for (const channel of apparatus.channels) {
        const shielded = apparatus.primitives.some(item => item.kind === 'shield' && item.target === channel.id
            && state.installed.includes(item.id));
        const a = state.transfer[channel.id], d = shielded ? 0 : channel.drift;
        const {first, invariant} = recurringEnvelope(channel, a, d);
        envelopes[channel.id] = invariant;
        coefficients[channel.id] = state.references.includes(channel.id) ? 0 : weights[channel.id];
        recurrence[channel.id] = {gain: a, recurringDisturbance: d, cap: channel.cap, first, invariant: envelopes[channel.id]};
    }
    const errors = Object.fromEntries(ast.scope.map(operation => [operation, apparatus.channels
        .filter(channel => channel.scopes.includes(operation))
        .reduce((sum, channel) => sum + envelopes[channel.id] * coefficients[channel.id], 0)]));
    const errorBound = Math.max(...Object.values(errors));
    const preserved = state.productive === 1;
    const scopeValid = JSON.stringify([...ast.scope].sort()) === JSON.stringify([...apparatus.scope].sort());
    const ok = preserved && scopeValid && Number.isFinite(errorBound) && errorBound <= apparatus.tolerance;
    const certificate = {schema: 'out-evolve-certificate/v1', runtime: RUNTIME_VERSION,
        modelOnly: true, productiveGain: state.productive, requiredProductiveGain: 1,
        scope: [...ast.scope], envelopes, coefficients, recurrence, errors, errorBound,
        structuralSupport: Object.keys(coefficients).filter(key => coefficients[key] !== 0),
        futureLanguage: 'repeat(prepare;operation;paired-reference;measure), all declared operations',
        inputDomain: 'bounded independent nuisance sources; nonnegative DAG gains; exact dyadic interpreter',
        precision: 'exact rational ceilings for conservative integer recurrence envelopes; no physical certificate'};
    const installation = program.installations.reduce((sum, key) =>
        sum + apparatus.primitives.find(item => item.id === key).cost, 0);
    const preparation = program.steps.reduce((sum, key) =>
        sum + apparatus.primitives.find(item => item.id === key).cost, 0);
    const calibration = program.steps.reduce((sum, key) => {
        const primitive = apparatus.primitives.find(item => item.id === key);
        return sum + (primitive.kind === 'reference' ? primitive.cost : 0);
    }, 0);
    return {ok, preserved, errorBound, tolerance: apparatus.tolerance, cost: state.cost, scope: [...ast.scope],
        costs: {installation, preparation, calibration, measurement: 1, maintenance: 0,
            operationPerUse: preparation + 1, calibrationIncludedInPreparation: true},
        certificate, reason: !preserved ? 'Productive-state preservation failed.' : !scopeValid
            ? 'Package scope differs from required apparatus scope.' : !ok
                ? 'Recurring nuisance exceeds required output quality.' : 'Qualified within the supplied synthetic model.'};
}

export function measure(input, ast, signal, options = {}) {
    dataOnly(options);
    if (!options || typeof options !== 'object' || Array.isArray(options)
        || Object.keys(options).some(key => !['operation', 'cycle', 'sign'].includes(key))) {
        fail('Unsupported measurement options.');
    }
    const apparatus = validateApparatus(input), report = qualify(apparatus, ast), state = prepare(apparatus, ast);
    const operation = options.operation ?? 'standard', cycle = options.cycle ?? 0, sign = options.sign ?? 1;
    if (!ast.scope.includes(operation) || !apparatus.scope.includes(operation)) fail('Operation outside qualified scope.');
    if (!Number.isFinite(signal) || Object.is(signal, -0) || Math.abs(signal) > 1_000_000
        || !integer(cycle, apparatus.limits.maxCycles)
        || ![-1, 1].includes(sign)) fail('Invalid measurement input or execution bound.');
    if (state.productive !== 1) fail('Destructive program cannot measure the required product.');
    const bounds = {};
    for (const channel of apparatus.channels) {
        const recurrence = report.certificate.recurrence[channel.id];
        let value = channel.initial;
        for (let round = 0; round <= cycle; round++) {
            value = Math.min(channel.cap, recurrence.gain * value + recurrence.recurringDisturbance);
        }
        bounds[channel.id] = value;
    }
    const rawError = apparatus.channels.filter(channel => channel.scopes.includes(operation))
        .reduce((total, channel) => total + bounds[channel.id] * report.certificate.coefficients[channel.id], 0);
    const error = rawError === 0 ? 0 : sign * rawError;
    const prepareCost = compile(apparatus, ast).steps.reduce((sum, key) =>
        sum + apparatus.primitives.find(item => item.id === key).cost, 0);
    return {value: signal + error, error, productive: signal, cost: prepareCost + 1,
        errorBound: report.certificate.errors[operation], bounds, operation, cycle,
        semantics: 'worst-aligned bounded nuisance; paired reference samples nuisance only'};
}
