// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { apparatus, expandApparatus } from './apparatus.mjs';
import { construct, createSearch, lineageConstructionCost, exportSearchCheckpoint, importSearchCheckpoint } from './constructor.mjs';
import { freezeCapability, importCapability, digestCapability } from './capability-package.mjs';
import { compareCapability, buildSuccessor } from './evaluation.mjs';

let generations;
function family() {
    generations ||= (async () => {
        const original = apparatus('shielded');
        const first = await freezeCapability(original, construct(original));
        const expanded = expandApparatus(original);
        const second = await freezeCapability(expanded, construct(expanded, {parent: first}), {parent: first});
        // The third package tests accounting, not a third accepted productive operation.
        const third = await freezeCapability(expanded, construct(expanded, {parent: second}), {parent: second});
        return {first, second, third, expanded};
    })();
    return generations;
}

test('three frozen generations retain every ancestor construction through standalone import and checkpoint replay', async () => {
    const {first, second, third, expanded} = await family();
    const firstCost = first.costLedger.total, secondCost = second.costLedger.total, thirdCost = third.costLedger.total;
    assert.equal(first.parentAssets.ancestorCost, 0);
    assert.equal(second.parentAssets.ancestorCost, firstCost);
    assert.equal(third.parentAssets.ancestorCost, firstCost + secondCost);
    assert.equal(lineageConstructionCost(third), firstCost + secondCost + thirdCost);
    assert.equal(third.search.checkpoint.inheritance.ancestorCost, firstCost + secondCost);
    assert.deepEqual(await importCapability(JSON.parse(JSON.stringify(third))), third);
    const checkpoint = createSearch(expanded, {parent: second});
    const token = JSON.parse(JSON.stringify(exportSearchCheckpoint(checkpoint)));
    const restored = importSearchCheckpoint(token, {parent: second});
    assert.equal(restored.inheritance.ancestorCost, firstCost + secondCost);
    assert.deepEqual(restored, checkpoint);
    assert.ok(third.costLedger.total <= third.search.limits.maxCost);
});

test('third-generation comparison and attempted repeated succession include the complete frozen parent lineage', async () => {
    const {first, second, third} = await family();
    const ancestor = first.costLedger.total + second.costLedger.total;
    const comparison = await compareCapability(third);
    assert.equal(comparison.costs.ancestorConstructionCost, ancestor);
    assert.equal(comparison.costs.remainingConstructionCost, third.costLedger.total);
    assert.match(comparison.costs.ancestorAccountingScope, /All frozen package construction ledgers/);
    assert.equal(comparison.costs.coldStart, ancestor + third.costLedger.total);
    assert.equal(comparison.costs.totalAtHorizon,
        ancestor + third.costLedger.total + comparison.costs.uses * comparison.costs.operationPerUse);
    const earlierSuccession = await buildSuccessor(first, {seed: 12345});
    assert.equal(earlierSuccession.status, 'PASS');
    assert.equal(earlierSuccession.newFunction.accepted, true);
    assert.deepEqual(earlierSuccession.invalidated,
        ['parent scope certificate', 'prior observations as fresh evidence']);
    assert.equal(earlierSuccession.oldScope.status, 'FAIL');
    assert.equal(earlierSuccession.oldScope.report.ok, false);
    assert.equal(earlierSuccession.oldScope.reason,
        'Original package was not qualified for the reservoir-exposing productive operation.');
    assert.equal(earlierSuccession.oldScope.diagnostic.envelope.ok, false);
    assert.equal(earlierSuccession.oldScope.diagnostic.independent.ok, false);
    assert.equal(earlierSuccession.oldScope.diagnostic.explanation,
        'Replaying the old plan under the newly required operation exposes recurring reservoir contamination.');
    const succession = await buildSuccessor(second, {seed: 12345});
    assert.equal(succession.costs.ancestor, ancestor);
    assert.match(succession.costs.ancestorAccountingScope, /prior task evaluations are outside package ancestry/);
    assert.equal(succession.costs.cumulative, ancestor + succession.costs.remaining);
    assert.equal(succession.costs.cumulativeAfterAcceptance,
        ancestor + succession.costs.remainingAfterAcceptance);
    assert.equal(succession.oldScope.status, 'UNEXPECTED-PASS');
    assert.equal(succession.oldScope.report.ok, true);
    assert.equal(succession.oldScope.reason,
        'Original package already qualifies for the reservoir-exposing productive operation.');
    assert.equal(succession.oldScope.diagnostic.envelope.ok, true);
    assert.equal(succession.oldScope.diagnostic.independent.ok, true);
    assert.equal(succession.oldScope.diagnostic.explanation,
        'Replaying the old plan preserves the required error envelope in the supplied model.');
    assert.equal(succession.newFunction.accepted, false);
    assert.deepEqual(succession.invalidated, ['prior observations as fresh evidence']);
    assert.equal(succession.status, 'FAIL', 'Repeating an existing scope is not a genuinely new accepted function.');
    const exhausted = await buildSuccessor(second, {seed: 12345, searchOptions: {maxStates: 1}});
    assert.equal(exhausted.status, 'INCONCLUSIVE');
    assert.equal(exhausted.costs.ancestor, ancestor);
    assert.equal(exhausted.costs.cumulative, ancestor + exhausted.costs.remaining);
});

test('rehashed or directly supplied discounted lineage totals cannot erase an earlier generation', async () => {
    const {first, second, third, expanded} = await family();
    const discounted = structuredClone(third);
    discounted.parentAssets.ancestorCost = second.costLedger.total;
    discounted.digest = await digestCapability(discounted);
    await assert.rejects(importCapability(discounted), /cumulative ancestor cost/);
    const forgedParent = structuredClone(second);
    forgedParent.parentAssets.ancestorCost = 0;
    forgedParent.digest = await digestCapability(forgedParent);
    assert.throws(() => createSearch(expanded, {parent: forgedParent}), /cumulative ancestor cost/);
    assert.throws(() => lineageConstructionCost(forgedParent), /cumulative ancestor cost/);
    assert.ok(first.costLedger.total > 0);
    const overflow = structuredClone(first);
    overflow.costLedger.total = Number.MAX_SAFE_INTEGER;
    const overflowChild = structuredClone(second);
    overflowChild.search.parentSource = overflow;
    overflowChild.parentAssets.parentDigest = overflow.digest;
    overflowChild.parentAssets.ancestorCost = Number.MAX_SAFE_INTEGER;
    assert.throws(() => lineageConstructionCost(overflowChild), /overflow/);
});
