// SPDX-License-Identifier: Apache-2.0
/** Independent contract replay. Deliberately imports no runtime transitions or validators. */
const reject = message => { throw Error(`Independent checker: ${message}`); };
const objectKeys = (value, keys) => value !== null && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join(',') === [...keys].sort().join(',');
const number = (value, max = 1_000_000) => typeof value === 'number' && Number.isSafeInteger(value)
    && !Object.is(value, -0) && value >= 0 && value <= max;
const identifier = value => typeof value === 'string' && /^[a-z][a-z0-9-]{0,79}$/.test(value);
const scopes = value => Array.isArray(value) && value.length >= 1 && value.length <= 2
    && new Set(value).size === value.length && value.every(key => key === 'standard' || key === 'reservoir');
const gains = value => !Object.is(value, -0) && (value === 0 || value === 0.5 || value === 1);
const stable = value => {
    if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort()
        .map(key => JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}';
    return JSON.stringify(value);
};

export function verify(apparatus, ast, claimedCertificate) {
    const pending = [[apparatus, 0], [ast, 0]];
    if (claimedCertificate !== undefined) pending.push([claimedCertificate, 0]);
    let dataCount = 0;
    while (pending.length) {
        const [value, depth] = pending.pop();
        if (++dataCount > 20_000 || depth > 32) reject('finite data bounds exceeded');
        if (value === null || typeof value === 'boolean') continue;
        if (typeof value === 'number') {
            if (!Number.isFinite(value) || Object.is(value, -0)) reject('invalid numeric data');
        } else if (typeof value === 'string') {
            if (value.length > 10_000) reject('oversized string');
        } else if (typeof value === 'object') {
            const prototype = Object.getPrototypeOf(value);
            if (prototype !== Object.prototype && prototype !== Array.prototype
                || Object.getOwnPropertySymbols(value).length) reject('unsupported data object');
            for (const [key, descriptor] of Object.entries(Object.getOwnPropertyDescriptors(value))) {
                if (key === 'length' && Array.isArray(value)) continue;
                if (!Object.hasOwn(descriptor, 'value') || !descriptor.enumerable) reject('accessor data');
                pending.push([descriptor.value, depth + 1]);
            }
        } else reject('unsupported data value');
    }
    if (!objectKeys(apparatus, ['schema', 'id', 'channels', 'edges', 'scope', 'tolerance', 'primitives', 'limits'])
        || apparatus.schema !== 'out-evolve-apparatus/v1' || !identifier(apparatus.id) || !scopes(apparatus.scope)
        || !number(apparatus.tolerance) || !Array.isArray(apparatus.channels) || !apparatus.channels.length
        || apparatus.channels.length > 8 || !Array.isArray(apparatus.edges) || apparatus.edges.length > 24
        || !Array.isArray(apparatus.primitives) || !apparatus.primitives.length || apparatus.primitives.length > 64) {
        reject('malformed apparatus');
    }
    const channels = {}, edgeIDs = new Set(), catalogue = {};
    for (const entry of apparatus.channels) {
        if (!objectKeys(entry, ['id', 'initial', 'drift', 'cap', 'scopes']) || !identifier(entry.id)
            || ['readout', 'productive'].includes(entry.id) || Object.hasOwn(channels, entry.id)
            || !number(entry.cap) || !number(entry.initial, entry.cap) || !number(entry.drift, entry.cap)
            || !scopes(entry.scopes)) reject('invalid channel declaration');
        channels[entry.id] = entry;
    }
    const graph = Object.fromEntries(Object.keys(channels).map(key => [key, []]));
    for (const edge of apparatus.edges) {
        if (!objectKeys(edge, ['id', 'from', 'to', 'gain']) || !identifier(edge.id) || edgeIDs.has(edge.id)
            || !Object.hasOwn(channels, edge.from) || (edge.to !== 'readout' && !Object.hasOwn(channels, edge.to))
            || !gains(edge.gain)) reject('invalid edge declaration');
        edgeIDs.add(edge.id); graph[edge.from].push(edge);
    }
    const ordered = [], marked = new Map();
    const visit = key => {
        if (marked.get(key) === 1) reject('cyclic graph');
        if (marked.get(key) === 2) return;
        marked.set(key, 1);
        for (const edge of graph[key]) if (edge.to !== 'readout') visit(edge.to);
        marked.set(key, 2); ordered.push(key);
    };
    Object.keys(channels).forEach(visit);
    const effectLists = {shield: ['installed'], route: ['installed'], sensor: ['installed'],
        attenuate: ['nuisance', 'transfer'], reference: ['observations'], destroy: ['productive']};
    for (const primitive of apparatus.primitives) {
        if (!objectKeys(primitive, ['id', 'phase', 'kind', 'target', 'gain', 'cost', 'requires', 'effects', 'support'])
            || !identifier(primitive.id) || Object.hasOwn(catalogue, primitive.id)
            || !Object.hasOwn(effectLists, primitive.kind) || !number(primitive.cost) || !gains(primitive.gain)
            || !Array.isArray(primitive.requires) || primitive.requires.length > 16
            || new Set(primitive.requires).size !== primitive.requires.length
            || stable(primitive.effects) !== stable(effectLists[primitive.kind])
            || !objectKeys(primitive.support, ['scopes', 'boundedGain']) || !scopes(primitive.support.scopes)
            || primitive.support.boundedGain !== primitive.gain) reject('invalid primitive declaration');
        const isInstall = ['shield', 'route', 'sensor'].includes(primitive.kind);
        if (primitive.phase !== (isInstall ? 'install' : 'prepare')
            || (primitive.kind === 'route' ? !edgeIDs.has(primitive.target) : primitive.kind === 'destroy'
                ? primitive.target !== 'productive' : !Object.hasOwn(channels, primitive.target))
            || (!['attenuate', 'destroy'].includes(primitive.kind) && primitive.gain !== 1)
            || (primitive.kind === 'destroy' && primitive.gain !== 0)) reject('unsupported primitive semantics');
        catalogue[primitive.id] = primitive;
    }
    for (const primitive of apparatus.primitives) {
        if (!primitive.requires.every(key => Object.hasOwn(catalogue, key) && catalogue[key].phase === 'install')) {
            reject('invalid guard');
        }
        if (primitive.kind === 'reference' && !primitive.requires.some(key =>
            catalogue[key].kind === 'sensor' && catalogue[key].target === primitive.target)) reject('missing sensor guard');
    }
    const limits = apparatus.limits;
    if (!objectKeys(limits, ['maxInstructions', 'maxRepeat', 'maxCost', 'maxCycles'])
        || !number(limits.maxInstructions, 64) || limits.maxInstructions < 1
        || !number(limits.maxRepeat, 32) || limits.maxRepeat < 1 || !number(limits.maxCost)
        || !number(limits.maxCycles, 4096) || limits.maxCycles < 1) reject('unsafe resource limits');
    if (!objectKeys(ast, ['schema', 'installations', 'prepare', 'scope']) || ast.schema !== 'out-evolve-ast/v1'
        || !scopes(ast.scope) || !Array.isArray(ast.installations)
        || ast.installations.length > limits.maxInstructions
        || new Set(ast.installations).size !== ast.installations.length) reject('malformed AST');
    const execution = []; let visits = 0;
    const flatten = (node, depth) => {
        if (++visits > 256 || depth > 8) reject('AST bounds exceeded');
        if (objectKeys(node, ['op', 'id']) && node.op === 'primitive') {
            if (!Object.hasOwn(catalogue, node.id) || catalogue[node.id].phase !== 'prepare') reject('unsupported operation');
            execution.push(node.id);
        } else if (objectKeys(node, ['op', 'steps']) && node.op === 'sequence' && Array.isArray(node.steps)
            && node.steps.length <= limits.maxInstructions) {
            for (const child of node.steps) flatten(child, depth + 1);
        } else if (objectKeys(node, ['op', 'count', 'body']) && node.op === 'repeat'
            && number(node.count, limits.maxRepeat) && node.count > 0) {
            for (let count = 0; count < node.count; count++) flatten(node.body, depth + 1);
        } else reject('unbounded or unknown AST operation');
        if (execution.length + ast.installations.length > limits.maxInstructions) reject('instruction limit exceeded');
    };
    flatten(ast.prepare, 0);
    const installed = new Set(), referenced = new Set(), contractions = Object.fromEntries(
        Object.keys(channels).map(key => [key, 0]));
    let productive = 1, cost = 0, installation = 0, preparation = 0, calibration = 0;
    const interpret = (key, phase) => {
        const primitive = catalogue[key];
        if (!primitive || primitive.phase !== phase || !primitive.requires.every(required => installed.has(required))
            || !ast.scope.every(scope => primitive.support.scopes.includes(scope))) reject('operation guard failed');
        cost += primitive.cost;
        if (!number(cost, limits.maxCost)) reject('resource overflow');
        if (phase === 'install') {
            if (installed.has(key)) reject('duplicate installation');
            installed.add(key); installation += primitive.cost;
        } else {
            preparation += primitive.cost;
            if (primitive.kind === 'attenuate') {
                if (primitive.gain === 0) contractions[primitive.target] = Infinity;
                else if (primitive.gain === 0.5) contractions[primitive.target]++;
            } else if (primitive.kind === 'reference') {
                referenced.add(primitive.target); calibration += primitive.cost;
            } else if (primitive.kind === 'destroy') productive = 0;
        }
    };
    for (const key of ast.installations) interpret(key, 'install');
    for (const key of execution) interpret(key, 'prepare');
    const closed = new Set([...installed].map(key => catalogue[key]).filter(item => item.kind === 'route')
        .map(item => item.target));
    const transferToOutput = {readout: 1};
    for (const key of ordered) transferToOutput[key] = graph[key].reduce((sum, edge) =>
        sum + (closed.has(edge.id) ? 0 : edge.gain * transferToOutput[edge.to]), 0);
    const envelopes = {}, coefficients = {}, recurrence = {};
    const ceilingRatio = (numerator, denominator) => {
        const quotient = numerator / denominator;
        return Number(quotient + (numerator % denominator === 0n ? 0n : 1n));
    };
    for (const [key, channel] of Object.entries(channels)) {
        const protectedChannel = [...installed].some(name => catalogue[name].kind === 'shield'
            && catalogue[name].target === key);
        const drift = protectedChannel ? 0 : channel.drift, exponent = contractions[key];
        const contraction = exponent === Infinity ? 0 : 2 ** -exponent;
        let first, invariant;
        if (exponent === Infinity) first = invariant = drift;
        else if (exponent === 0) {
            first = Math.min(channel.cap, channel.initial + drift);
            invariant = drift === 0 ? channel.initial : channel.cap;
        } else {
            const scale = 2n ** BigInt(exponent), d = BigInt(drift);
            first = Math.min(channel.cap, ceilingRatio(BigInt(channel.initial) + d * scale, scale));
            invariant = Math.max(first, Math.min(channel.cap, ceilingRatio(d * scale, scale - 1n)));
        }
        envelopes[key] = invariant;
        coefficients[key] = referenced.has(key) ? 0 : transferToOutput[key];
        recurrence[key] = {gain: contraction, recurringDisturbance: drift, cap: channel.cap, first, invariant};
    }
    const errors = {};
    for (const operation of ast.scope) {
        errors[operation] = Object.values(channels).reduce((sum, channel) => sum
            + (channel.scopes.includes(operation) ? envelopes[channel.id] * coefficients[channel.id] : 0), 0);
    }
    const errorBound = Math.max(...Object.values(errors)), preserved = productive === 1;
    const scopeValid = stable([...ast.scope].sort()) === stable([...apparatus.scope].sort());
    const ok = preserved && scopeValid && Number.isFinite(errorBound) && errorBound <= apparatus.tolerance;
    const certificate = {schema: 'out-evolve-certificate/v1', runtime: 'out-evolve-runtime/v1',
        modelOnly: true, productiveGain: productive, requiredProductiveGain: 1, scope: [...ast.scope],
        envelopes, coefficients, recurrence, errors, errorBound,
        structuralSupport: Object.keys(coefficients).filter(key => coefficients[key] !== 0),
        futureLanguage: 'repeat(prepare;operation;paired-reference;measure), all declared operations',
        inputDomain: 'bounded independent nuisance sources; nonnegative DAG gains; exact dyadic interpreter',
        precision: 'exact rational ceilings for conservative integer recurrence envelopes; no physical certificate'};
    if (claimedCertificate !== undefined && stable(claimedCertificate) !== stable(certificate)) {
        reject('supplied preservation certificate does not match semantic replay');
    }
    return {ok, preserved, errorBound, tolerance: apparatus.tolerance, cost, scope: [...ast.scope],
        costs: {installation, preparation, calibration, measurement: 1, maintenance: 0,
            operationPerUse: preparation + 1, calibrationIncludedInPreparation: true}, certificate,
        reason: !preserved ? 'Productive-state preservation failed.' : !scopeValid
            ? 'Package scope differs from required apparatus scope.' : !ok
                ? 'Recurring nuisance exceeds required output quality.' : 'Qualified within the supplied synthetic model.'};
}
