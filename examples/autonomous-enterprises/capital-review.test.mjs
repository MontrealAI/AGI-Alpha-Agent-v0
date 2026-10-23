// SPDX-License-Identifier: Apache-2.0
// Separate ordinary mathematical review, authored without using the generator's confirmation scan.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as c from './capital.mjs';
const producer = (id, kappa, delta, stock) => ({id, kappa, delta, stock});
const recipe = (id, requires, produces, cost) => ({id, requires, produces, cost});
const stocks = [[], ['a'], ['b'], ['a', 'b']];
const spec = {capabilities: ['a', 'b'], recipes: [recipe('a', [], ['a'], 2),
    recipe('b', ['a'], ['b'], 1), recipe('both', [], ['a', 'b'], 2)]};

function bruteCompletion(model, initial, target) {
    const contains = (stock, required) => required.every(value => stock.includes(value));
    const walk = (stock, cost) => {
        if (contains(stock, target)) return cost;
        let result = Infinity;
        for (const action of model.recipes) {
            if (!contains(stock, action.requires)) continue;
            const next = [...new Set(stock.concat(action.produces))];
            if (next.length === stock.length) continue;
            result = Math.min(result, walk(next, cost + action.cost));
        }
        return result;
    };
    return walk(initial, 0);
}
function bruteLaunch(model, rows, target, cash) {
    const repairs = rows.map(row => bruteCompletion(model, row.stock, target));
    for (let opening = 0; opening <= 60; opening++) {
        if (rows.some((row, i) => opening >= row.kappa && opening + row.delta - repairs[i] >= cash)) return opening;
    }
    return Infinity;
}

test('independent enumeration of executable paths and feasible cash prefixes agrees across42subportfolios', () => {
    let families = 0, scans = 0, covers = 0;
    for (let pattern = 0; pattern < 6; pattern++) {
        const family = [producer('a', pattern % 4, 4 - pattern, stocks[pattern % 4]),
            producer('b', 5, -2 + pattern, stocks[(pattern + 1) % 4]),
            producer('c', 1 + pattern % 2, 3, stocks[(pattern + 2) % 4])];
        for (let mask = 1; mask < 8; mask++) {
            const retained = family.filter((_, i) => mask & (1 << i));
            const result = c.retentionLaw(spec, family, retained.map(row => row.id));
            assert.equal(result.status, 'FINITE');
            let scanned = 0;
            for (const target of stocks) for (let cash = 0; cash <= 20; cash++) {
                const full = bruteLaunch(spec, family, target, cash);
                const kept = bruteLaunch(spec, retained, target, cash);
                assert.equal(c.portfolioCapital(spec, family, target, cash).capital, full);
                scanned = Math.max(scanned, kept - full); scans++;
            }
            assert.equal(result.loss, scanned);
            assert.equal(bruteLaunch(spec, retained, result.witness.target, result.witness.terminalCash)
                - bruteLaunch(spec, family, result.witness.target, result.witness.terminalCash), scanned);
            assert.equal(c.epsilonCover(spec, family, retained.map(row => row.id), scanned).covered, true);
            if (scanned > 0) assert.equal(c.epsilonCover(spec, family, retained.map(row => row.id), scanned - 1).covered, false);
            families++; covers++;
        }
    }
    assert.equal(families, 42); assert.equal(scans, 3528); assert.equal(covers, 42);
});

test('negative pairwise substitution remains signed with different output stocks', () => {
    const a = producer('a', 5, 0, ['a']); const b = producer('b', 1, 20, []);
    const relation = c.productiveDominance(spec, a, b);
    assert.equal(relation.distance, -4); assert.equal(relation.dominates, true);
    assert.equal(relation.reconstruction.cost, 2);
    for (const target of stocks) for (let x = 0; x <= 15; x++) {
        assert(bruteLaunch(spec, [b], target, x) - bruteLaunch(spec, [a], target, x) <= -4);
    }
    assert.equal(c.retentionLaw(spec, [a, b], ['b']).loss, 0);
});

test('equivalence pruning keeps the earliest policy even when free installation changes output stock', () => {
    const free = {capabilities: ['a', 'b'], recipes: [recipe('install-a', [], ['a'], 0), recipe('install-b', [], ['b'], 0)]};
    const family = stocks.map((stock, i) => producer(`p${i}`, 2, 3, stock));
    const result = c.pruneDominated(free, family);
    assert.deepEqual(result.retained.map(row => row.id), ['p0']);
    assert.equal(result.loss.loss, 0);
    for (let i = 0; i < family.length; i++) {
        const proof = result.certificates[i];
        assert.equal(proof.to, 'p0'); assert.equal(proof.distance, 0);
        assert.equal(c.checkCompletionWitness(free, [], family[i].stock, proof.reconstruction).verified, true);
    }
    const reversed = c.pruneDominated(free, [...family].reverse());
    assert.deepEqual(reversed.retained.map(row => row.id), ['p3']);
});

test('jointly unavailable targets are excluded and actual loss is unbounded only after losing reachable stock', () => {
    const noRecipes = {capabilities: ['a', 'b'], recipes: []};
    const family = [producer('first', 2, 3, ['a']), producer('same', 3, 2, ['a'])];
    const finite = c.retentionLaw(noRecipes, family, ['first']);
    assert.equal(finite.status, 'FINITE'); assert.equal(finite.loss, 0);
    assert.equal(c.portfolioCapital(noRecipes, family, ['b'], 0).status, 'UNREACHABLE');
    const third = producer('other', 0, 0, ['b']);
    const missing = c.retentionLaw(noRecipes, family.concat(third), ['first']);
    assert.equal(missing.status, 'UNBOUNDED_MISSING_CAPABILITY');
    assert.deepEqual(missing.witness.target, ['b']);
    assert.equal(missing.witness.full.capital, 0); assert.equal(missing.witness.retained.status, 'UNREACHABLE');
    assert.equal(JSON.stringify(missing).includes('NaN'), false);
});

test('B must be a nonempty identity-preserving subset of A', () => {
    const family = [producer('first', 2, 3, []), producer('second', 1, 1, ['a'])];
    for (const retained of [[], ['first', 'first'], ['missing']]) assert.throws(() => c.retentionLaw(spec, family, retained));
    assert.equal(c.retentionLaw(spec, family, family.map(row => row.id)).loss, 0);
    assert.throws(() => c.productiveDominance(spec, family[0], {...family[0], delta: 4}));
});

test('cover chains add allowances while a fresh direct certificate can be strictly tighter', () => {
    const family = [producer('full', 0, 0, ['a', 'b']), producer('a', 0, 0, ['a']), producer('empty', 0, 0, [])];
    const result = c.substitutionChain(spec, family, ['full', 'a', 'empty'], [2, 3]);
    assert.equal(result.cumulativeAllowance, 5);
    assert.equal(result.direct.distance, 2);
    assert.deepEqual(result.steps.map(step => step.distance), [1, 2]);
    for (const step of result.steps) assert(step.distance <= step.allowance);
    for (const target of stocks) for (let x = 0; x <= 10; x++) {
        assert(bruteLaunch(spec, [family[2]], target, x) - bruteLaunch(spec, [family[0]], target, x)
            <= result.cumulativeAllowance);
    }
});

test('a capped final direct cover replay is inconclusive after both individual substitutions finish', () => {
    const sequence = {capabilities: ['a', 'b'], recipes: [recipe('a', [], ['a'], 1), recipe('b', ['a'], ['b'], 1)]};
    const family = [producer('full', 0, 0, ['a', 'b']), producer('a', 0, 0, ['a']), producer('empty', 0, 0, [])];
    assert.equal(c.productiveDominance(sequence, family[0], family[1], {maxStates: 2}).status, 'FOUND');
    assert.equal(c.productiveDominance(sequence, family[1], family[2], {maxStates: 2}).status, 'FOUND');
    const result = c.substitutionChain(sequence, family, ['full', 'a', 'empty'], [1, 1], {maxStates: 2});
    assert.equal(result.status, 'INCONCLUSIVE');
    assert.equal(result.cumulativeAllowance, 2);
    assert.equal(result.steps.length, 2);
    assert.equal(result.direct.status, 'INCONCLUSIVE');
});
