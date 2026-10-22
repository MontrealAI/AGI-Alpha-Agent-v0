// SPDX-License-Identifier: Apache-2.0
import {MODEL_SCHEMA, SEMANTICS, clone} from './model.mjs';
export function containment(flipped = false) {
    return {schema: MODEL_SCHEMA, semantics: SEMANTICS,
        variables: ['b', 'x', 'y'].map(id => ({id, domain: [0, 1]})),
        factors: [{id: 'outside', scope: ['b'], costs: [1, 4]},
            {id: 'first', scope: ['b', 'x'], costs: flipped ? [3, 0, 0, 3] : [0, 3, 3, 0]},
            {id: 'second', scope: ['b', 'y'], costs: [0, 2, 2, 0]}]};
}
export function scalarCounterexample(flipped = false) {
    return {schema: MODEL_SCHEMA, semantics: SEMANTICS,
        variables: ['b', 'x'].map(id => ({id, domain: [0, 1]})),
        factors: [{id: 'pin', scope: ['b'], costs: [0, null]},
            {id: 'component', scope: ['b', 'x'], costs: flipped ? [2, 3, 0, 1] : [0, 1, 2, 3]}]};
}
export function interactingPaths(colors = 3) {
    const domain = Array.from({length: colors}, (_, i) => i);
    return {schema: MODEL_SCHEMA, semantics: SEMANTICS,
        variables: ['u', 'a', 'v', 'b', 'c'].map(id => ({id, domain})),
        factors: [['u', 'a'], ['a', 'v'], ['u', 'b'], ['b', 'c'], ['c', 'v']].map((scope, i) => ({
            id: `edge${i}`, scope, costs: domain.flatMap(a => domain.map(b => a === b ? null : 0))}))};
}
// Explicit xorshift32 protocol, not the unavailable manuscript companion's Python RNG.
export function random(seed) {
    let state = seed >>> 0;
    return limit => { state ^= state << 13; state ^= state >>> 17; state ^= state << 5; return (state >>> 0) % limit; };
}
export function weightedStream(seed, updates = 8) {
    const next = random(seed), domain = [0, 1, 2];
    const ids = ['b0', 'b1', ...Array.from({length: 3}, (_, i) => [`m${i}x0`, `m${i}x1`]).flat()];
    const scopes = ids.map(id => [id]); scopes.push(['b0', 'b1']);
    for (let i = 0; i < 3; i++) {
        scopes.push([`m${i}x0`, `m${i}x1`]);
        for (const id of [`m${i}x0`, `m${i}x1`]) for (const b of ['b0', 'b1']) scopes.push([b, id]);
    }
    const model = {schema: MODEL_SCHEMA, semantics: SEMANTICS, variables: ids.map(id => ({id, domain})),
        factors: scopes.map((scope, i) => ({id: `factor${String(i).padStart(3, '0')}`, scope,
            costs: Array.from({length: 3 ** scope.length}, () => scope.length === 1 ? next(6) : next(10) === 0 ? null : next(5))}))};
    const snapshots = [clone(model)], revise = random(seed + 1000000);
    for (let i = 0; i < updates; i++) {
        const factor = model.factors[revise(model.factors.length)], entry = revise(factor.costs.length);
        const values = [null, 0, 1, 2, 3, 4, 5].filter(value => value !== factor.costs[entry]);
        factor.costs[entry] = values[revise(values.length)]; snapshots.push(clone(model));
    }
    return snapshots;
}
