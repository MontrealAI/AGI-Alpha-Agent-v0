// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as c from './capital.mjs';
const r = (id, requires, produces, cost) => ({id, requires, produces, cost});
const p = (id, kappa, delta, stock) => ({id, kappa, delta, stock});
const spec = {capabilities: ['F', 'C', 'S'], recipes: [r('F', [], ['F'], 12), r('C', ['F'], ['C'], 3),
    r('S', ['F'], ['S'], 4), r('direct-C', [], ['C'], 20), r('direct-S', [], ['S'], 20)]};
const family = [p('a', 2, 8, []), p('b', 5, 4, ['F'])];
test('synthetic cash example reconstructs both targets and preserves complete policies', () => {
    const example = c.syntheticCapitalExample();
    assert.deepEqual(example.targets.map(t => [t.full.capital, t.cashOnly.capital]), [[5, 13], [5, 13]]);
    assert.equal(example.retention.loss, 8);
    assert.deepEqual(example.retention.witness.target, ['F']);
    assert.equal(example.retention.witness.terminalCash, 9);
    assert.deepEqual(example.traces.a.prefixes.map(e => e.cumulativeCash), [-2, 8]);
    assert.deepEqual(example.traces.b.prefixes.map(e => e.cumulativeCash), [7, -5, 4]);
    assert.equal(example.traces.a.kappa, 2); assert.equal(example.traces.b.kappa, 5);
    assert.equal(example.traces.bRefundable.kappa, 12);
    assert.equal(example.traces.bRefundable.delta, 4);
    assert.equal(example.spec.recipes.length, 5);
    assert.ok(example.spec.recipes.every(recipe => recipe.cost >= 0));
});
test('Dijkstra and independent decreasing-stock DP agree on every cash-example stock and target', () => {
    const table = c.completionTable(spec);
    assert.equal(table.status, 'COMPLETE'); assert.equal(table.valuesChecked, 64);
    assert.equal(table.witnessesChecked, 64); assert.equal(table.geometry.status, 'QUALIFIED_FINITE');
    for (const stock of table.stocks) for (const target of table.stocks) {
        const a = c.completion(spec, stock, target), b = c.completionDynamic(spec, stock, target);
        assert.equal(a.cost, b.cost); assert.equal(a.status, b.status);
        if (a.status === 'FOUND') assert.equal(c.checkCompletionWitness(spec, stock, target, a).verified, true);
    }
});
test('a minimum may install an extra byproduct and zero-price installation changes the stock', () => {
    const bulk = {capabilities: ['a', 'b'], recipes: [r('package', [], ['a', 'b'], 0), r('single', [], ['a'], 4)]};
    const result = c.completion(bulk, [], ['a']);
    assert.equal(result.cost, 0); assert.equal(result.witness.steps.length, 1);
    assert.deepEqual(result.witness.final, ['a', 'b']); assert.equal(result.witness.steps[0].recipeId, 'package');
    assert.equal(c.completionDynamic(bulk, [], ['a']).cost, 0);
    assert.equal(c.completion(bulk, ['a'], ['a']).witness.steps.length, 0);
});
test('an initially attractive but expensive direct recipe cannot hide a cheaper reconstruction', () => {
    const s = {capabilities: ['a', 'b'], recipes: [r('direct', [], ['b'], 10),
        r('first', [], ['a'], 2), r('second', ['a'], ['b'], 1)]};
    const result = c.completion(s, [], ['b']);
    assert.equal(result.cost, 3); assert.deepEqual(result.witness.steps.map(s => s.recipeId), ['first', 'second']);
});
test('unreachable is supported by a closed reachable set; no-effect cycles do not require search loops', () => {
    const s = {capabilities: ['a', 'b'], recipes: [r('install', [], ['a'], 0), r('no-effect', ['a'], ['a'], 0)]};
    const result = c.completion(s, [], ['b']);
    assert.equal(result.status, 'UNREACHABLE'); assert.equal(result.cost, null);
    assert.deepEqual(result.unreachableCertificate.reachable, [[], ['a']]);
    assert.equal(c.checkCompletionWitness(s, [], ['b'], result).verified, true);
    assert.equal(c.completionDynamic(s, [], ['b']).status, 'UNREACHABLE');
    const broken = structuredClone(result); broken.unreachableCertificate.reachable = [[]];
    assert.throws(() => c.checkCompletionWitness(s, [], ['b'], broken), /closed/);
});
test('state, work and elapsed caps remain inconclusive without unreachable certificates', () => {
    for (const cap of [{maxStates: 0}, {maxStates: 1}, {maxExpansions: 0}, {maxElapsedMs: 0}]) {
        const result = c.completion(spec, [], ['C'], cap);
        assert.equal(result.status, 'INCONCLUSIVE'); assert.equal(result.cost, null);
        assert.equal(result.unreachableCertificate, null);
        assert.throws(() => c.checkCompletionWitness(spec, [], ['C'], result));
    }
    assert.equal(c.completionDynamic(spec, [], ['C'], {maxStates: 1}).status, 'INCONCLUSIVE');
    assert.equal(c.completionTable(spec, {maxStates: 1}).status, 'INCONCLUSIVE');
    assert.equal(c.completion(spec, ['F'], ['F'], {maxStates: 0}).cost, 0);
});
test('witness validation rejects changed stock transitions, charges, endpoints and totals', () => {
    const result = c.completion(spec, [], ['C']);
    for (const mutate of [x => x.witness.steps[0].charge++, x => x.witness.steps[0].to = ['C'],
        x => x.witness.steps[0].from = ['S'], x => x.witness.final = ['F'], x => x.cost++]) {
        const changed = structuredClone(result); mutate(changed);
        assert.throws(() => c.checkCompletionWitness(spec, [], ['C'], changed));
    }
});
test('portfolio selects a complete producer, including an economically worse cash route with usable stock', () => {
    const result = c.portfolioCapital(spec, family, ['C'], 6);
    assert.equal(result.producer.id, 'b'); assert.equal(result.capital, 5);
    assert.equal(result.reconstruction.cost, 3);
    assert.equal(c.capitalRequirement(spec, family[0], ['C'], 6).capital, 13);
    assert.equal(c.capitalRequirement(spec, family[1], ['C'], 6).capital, 5);
    assert.equal(c.productiveDominance(spec, family[1], family[0]).dominates, false);
    assert.equal(c.productiveDominance(spec, family[0], family[0]).dominates, true);
});
test('uniform epsilon cover carries the attaining reconstruction witness', () => {
    const cover = c.epsilonCover(spec, family, ['a'], 8);
    assert.equal(cover.covered, true); assert.equal(cover.loss, 8);
    assert.equal(c.epsilonCover(spec, family, ['a'], 7).covered, false);
    const relation = cover.comparisons.find(row => row.producer === 'b').selected;
    assert.equal(relation.reconstruction.cost, 12);
    assert.equal(c.checkCompletionWitness(spec, [], ['F'], relation.reconstruction).verified, true);
    assert.equal(c.retentionLaw(spec, family, ['a', 'b']).loss, 0);
});
test('an unreconstructible producer causes explicit unbounded missing capability, not infinity subtraction', () => {
    const s = {capabilities: ['a', 'b'], recipes: []}, rows = [p('a', 0, 0, ['a']), p('b', 0, 0, ['b'])];
    const result = c.retentionLaw(s, rows, ['a']);
    assert.equal(result.status, 'UNBOUNDED_MISSING_CAPABILITY'); assert.equal(result.loss, null);
    assert.equal(result.witness.full.status, 'FOUND'); assert.equal(result.witness.retained.status, 'UNREACHABLE');
    assert.equal(c.epsilonCover(s, rows, ['a'], 100).covered, false);
    const noTarget = c.portfolioCapital(s, [rows[0]], ['b'], 0);
    assert.equal(noTarget.status, 'UNREACHABLE'); assert.equal(noTarget.capital, null);
    assert.ok(!JSON.stringify(result).includes('NaN'));
});
test('caps propagate through capital, retention and dominance instead of manufacturing guarantees', () => {
    const cap = {maxStates: 0};
    assert.equal(c.capitalRequirement(spec, family[0], ['F'], 0, cap).status, 'INCONCLUSIVE');
    assert.equal(c.portfolioCapital(spec, family, ['F'], 0, cap).status, 'INCONCLUSIVE');
    assert.equal(c.retentionLaw(spec, family, ['a'], cap).status, 'INCONCLUSIVE');
    assert.equal(c.epsilonCover(spec, family, ['a'], 8, cap).covered, null);
    assert.equal(c.pruneDominated(spec, family, cap).status, 'INCONCLUSIVE');
});
test('stable productive pruning keeps earliest equivalent representatives and a direct witness for every deletion', () => {
    const rows = [p('first', 2, 8, []), p('equivalent', 2, 8, []), p('worse', 3, 7, []), family[1]];
    const result = c.pruneDominated(spec, rows);
    assert.equal(result.status, 'COMPLETE'); assert.deepEqual(result.retained.map(p => p.id), ['first', 'b']);
    assert.equal(result.loss.loss, 0); assert.equal(result.certificates.length, 4);
    assert.ok(result.certificates.every(r => r.status === 'FOUND' && r.distance <= 0));
});
test('signed single-producer differences need no artificial zero clipping', () => {
    const s = {capabilities: [], recipes: []};
    const a = p('a', 5, 0, []), b = p('b', 1, 4, []);
    assert.equal(c.productiveDominance(s, a, b).distance, -4);
    assert.equal(c.retentionLaw(s, [a, b], ['b']).loss, 0);
});
test('successive substitution allowances accumulate and retain every executable path', () => {
    const s = {capabilities: ['a', 'b'], recipes: [r('a', [], ['a'], 3), r('b', ['a'], ['b'], 5)]};
    const rows = [p('both', 0, 0, ['a', 'b']), p('only-a', 0, 0, ['a']), p('empty', 0, 0, [])];
    const result = c.substitutionChain(s, rows, ['both', 'only-a', 'empty'], [5, 3]);
    assert.equal(result.cumulativeAllowance, 8); assert.equal(result.direct.distance, 8);
    assert.deepEqual(result.steps.map(x => x.reconstruction.cost), [5, 3]);
    assert.throws(() => c.substitutionChain(s, rows, ['both', 'only-a', 'empty'], [4, 3]), /allowance/);
});
test('nonsubmodular purchase prices preserve executable triangle geometry', () => {
    const result = c.capitalControls().nonsubmodular;
    assert.deepEqual(result.values, [2, 2, 2, 4]);
    assert.equal(result.left, 4); assert.equal(result.right, 6);
    assert.equal(result.violatesSubmodularity, true); assert.equal(result.geometry.status, 'QUALIFIED_FINITE');
});
test('arbitrary reflexive maps can violate triangle and invalidate the universal retention law', () => {
    const result = c.capitalControls().triangleViolation;
    assert.equal(result.assessment.status, 'TRIANGLE_VIOLATION');
    assert.ok(result.actualLoss > result.pairwiseExpression);
    assert.deepEqual(result.assessment.witness, {L: 0, K: 1, Q: 2, direct: 4, first: 1, second: 1, via: 2});
    assert.equal(c.qualifyCompletionMap([[0, null], [null, 0]]).status, 'QUALIFIED_EXTENDED');
    assert.equal(c.qualifyCompletionMap([[1]]).status, 'INVALID_REFLEXIVITY');
});
test('separate paths cannot supply coordinatewise-minimum imaginary resources', () => {
    const result = c.capitalControls().vector;
    assert.equal(result.status, 'NO_SUPPLIED_PATH_FITS'); assert.equal(result.selected, null);
    const accepted = c.resourceWitness([...result.paths.map(({id, steps}) => ({id, steps})),
        {id: 'actual-fit', steps: [[0, 1], [1, 0]]}], [1, 1]);
    assert.equal(accepted.status, 'FEASIBLE_PATH'); assert.equal(accepted.selected.id, 'actual-fit');
    assert.deepEqual(accepted.selected.total, [1, 1]);
});
test('reserve closure and exact integer model bounds refuse invalid or richer accounting', () => {
    assert.throws(() => c.completion({...spec, recipes: [r('negative', [], ['F'], -1)]}, [], ['F']));
    assert.throws(() => c.completion({...spec, recipes: [r('fractional', [], ['F'], 0.5)]}, [], ['F']));
    assert.throws(() => c.completion(spec, ['F', 'F'], ['C']));
    assert.throws(() => c.completion(spec, [], ['unknown']));
    assert.throws(() => c.completion({...spec, rights: 'different'}, [], ['F']));
    assert.throws(() => c.capitalRequirement(spec, p('bad', 2, -3, []), ['F'], 0));
    assert.throws(() => c.portfolioCapital(spec, [], ['F'], 0));
    assert.throws(() => c.retentionLaw(spec, family, []));
    assert.throws(() => c.retentionLaw(spec, family, ['unknown']));
    assert.throws(() => c.profileFromTrace([{id: 'release', cashChange: 1, reserveChange: -1}]));
    assert.throws(() => c.profileFromTrace([{id: 'hold', cashChange: 1, reserveChange: 1}]), /close/);
    assert.throws(() => c.resourceWitness([{id: 'a', steps: [[0]]}], [1, 1]));
});
test('receipt-priced foundry catalogue selects direct inverse unless convolution is separately required', () => {
    const names = ['F2', 'F4', 'F8', 'F16', 'F32', 'C32', 'S32'];
    const costs = [592, 2192, 8640, 34624, 139328];
    const recipes = costs.map((cost, i) => r(`build-${names[i]}`, i ? [names[i - 1]] : [], [names[i]], cost));
    recipes.push(r('build-convolution', ['F32'], ['C32'], 592132), r('direct-inverse', ['F32'], ['S32'], 78016),
        r('inherited-inverse', ['F32', 'C32'], ['S32'], 30912));
    const s = {capabilities: names, recipes};
    const joint = c.completion(s, [], ['F32', 'C32', 'S32']);
    assert.equal(joint.cost, 808420); assert.equal(joint.witness.steps.at(-1).recipeId, 'inherited-inverse');
    const inverseOnly = c.completion(s, names.slice(0, 5), ['S32']);
    assert.equal(inverseOnly.cost, 78016); assert.equal(inverseOnly.witness.steps[0].recipeId, 'direct-inverse');
    assert.ok(592132 + 30912 > inverseOnly.cost);
    assert.equal(c.completionDynamic(s, [], ['F32', 'C32', 'S32']).cost, joint.cost);
});
test('72 independent seeded catalogues check actual completion values and all scanned cash targets', () => {
    const result = c.runCapitalConfirmation({cases: 72, seed: 20261021});
    assert.equal(result.counts.catalogues, 72); assert.equal(result.counts.completionValues, 32256);
    assert.ok(result.counts.capitalTargets > 0); assert.ok(result.counts.triangleTriples > 0);
    assert.equal(result.reports.length, 72);
    assert.ok(result.reports.every(r => r.scannedLoss === r.certificate.loss));
    assert.match(result.generator, /different/); assert.equal(result.source, 'independent reimplementation');
});
