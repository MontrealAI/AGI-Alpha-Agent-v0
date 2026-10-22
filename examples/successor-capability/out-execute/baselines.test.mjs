// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {fixedCertificateRunner, fromScratch} from './baselines.mjs';
import {containment, scalarCounterexample} from './fixtures.mjs';
import {clone} from './model.mjs';

test('a sufficient fixed proof is cheaper on identical inputs and guarded constant shifts', () => {
    const run = fixedCertificateRunner(), model = containment(), first = run(model);
    const second = run(model);
    assert.equal(second.retained, true); assert.ok(second.countedWork < first.countedWork);
    const shifted = clone(model); shifted.factors[0].costs = shifted.factors[0].costs.map(value => value + 3);
    const third = run(shifted);
    assert.equal(third.retained, true); assert.equal(third.cost, fromScratch(shifted).cost);
    assert.equal(third.cost, first.cost + 3);
});

test('caller mutation cannot forge the retained fixed proof, and changed support rejects reuse', () => {
    const run = fixedCertificateRunner(), model = containment(), first = run(model);
    first.artifact.x = 123; first.cost = 99; model.factors[0].costs[0] = 99;
    const second = run(containment()); assert.equal(second.retained, true);
    assert.equal(second.cost, fromScratch(containment()).cost);
    const blocked = containment(); blocked.factors[0].costs[0] = null;
    const third = run(blocked); assert.equal(third.retained, false);
    assert.equal(third.cost, fromScratch(blocked).cost);
});

test('same optimum without a preserved full factor guard does not qualify a fixed proof', () => {
    const run = fixedCertificateRunner(); run(scalarCounterexample());
    const revised = run(scalarCounterexample(true));
    assert.equal(revised.retained, false); assert.equal(revised.cost, fromScratch(scalarCounterexample(true)).cost);
});
