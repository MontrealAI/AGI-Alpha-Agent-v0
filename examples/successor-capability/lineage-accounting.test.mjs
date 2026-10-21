// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { apparatus, expandApparatus } from './apparatus.mjs';
import { construct, createSearch, lineageConstructionCost, exportSearchCheckpoint, importSearchCheckpoint } from './constructor.mjs';
import { freezeCapability, importCapability, digestCapability } from './capability-package.mjs';
import { compareCapability, buildSuccessor, evaluateFrozenReuse } from './evaluation.mjs';

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
    assert.deepEqual([firstCost, secondCost, thirdCost], [591, 1157, 955]);
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

test('standard-only parent primitives retain incompatible diagnostics and complete successor and scratch evidence', async () => {
    for (const id of ['protect-residual', 'flush-residual', 'dependent-installation']) {
        const app = apparatus('shielded');
        if (id === 'dependent-installation') {
            const sensor = app.primitives.find(primitive => primitive.id === 'sense-residual');
            sensor.cost = 0;
            sensor.support.scopes = ['standard'];
            app.primitives.find(primitive => primitive.id === 'protect-residual').requires = [sensor.id];
            app.primitives.find(primitive => primitive.id === 'reference-residual').cost = 100;
        } else app.primitives.find(primitive => primitive.id === id).support.scopes = ['standard'];
        const parent = await freezeCapability(app, construct(app));
        if (id !== 'dependent-installation') assert.equal(parent.costLedger.total, 591);
        assert.deepEqual(await importCapability(parent), parent);
        const report = await buildSuccessor(parent, {seed: 12345});
        assert.equal(report.status, 'PASS');
        assert.equal(report.oldScope.status, 'FAIL');
        assert.equal(report.oldScope.report.ok, false);
        assert.equal(report.oldScope.diagnostic.envelope.status, 'INCOMPATIBLE');
        assert.match(report.oldScope.diagnostic.envelope.reason, /outside support envelope/);
        assert.equal(report.oldScope.diagnostic.independent.status, 'NOT-RUN');
        assert.equal(report.oldScope.diagnostic.reservoirMeasurement.status, 'NOT-RUN');
        assert.equal(Object.hasOwn(report.oldScope.diagnostic.reservoirMeasurement, 'value'), false);
        assert.equal(report.costs.oldScopeCheck, 2);
        assert.equal(report.costs.ancestor, parent.costLedger.total);
        assert.equal(report.costs.cumulative, parent.costLedger.total + report.costs.remaining);
        assert.equal(report.result.qualification.status, 'qualified');
        assert.equal(report.scratch.qualification.status, 'qualified');
        assert.ok(report.scratchReuse.cases.every(item => item.status === 'PASS'));
        assert.equal(report.newFunction.accepted, true);
        assert.deepEqual(report.newFunction.operations, ['reservoir']);
        assert.deepEqual(await importCapability(report.package), report.package);
        const excluded = report.inheritanceDiagnostic.excludedInstallations;
        assert.deepEqual(excluded.map(item => item.id), id === 'dependent-installation'
            ? ['sense-residual', 'protect-residual'] : id === 'protect-residual' ? [id] : []);
        if (excluded.length) assert.match(excluded[0].reason, /does not support/);
        if (id === 'dependent-installation') {
            assert.match(excluded[1].reason, /Requires an installation excluded/);
            assert.deepEqual(excluded[1].missingRequirements, ['sense-residual']);
        }
        const resumed = importSearchCheckpoint(JSON.parse(JSON.stringify(exportSearchCheckpoint(report.result.checkpoint))),
            {parent});
        assert.deepEqual(resumed, report.result.checkpoint);
    }
});

test('maximum-length apparatus identity remains valid and deterministic when its scope expands', async () => {
    const app = apparatus('shielded');
    app.id = 'a'.repeat(80);
    const parent = await freezeCapability(app, construct(app));
    const expanded = expandApparatus(app);
    assert.equal(expanded.id, app.id);
    assert.deepEqual(expandApparatus(expanded), expanded);
    const report = await buildSuccessor(parent, {seed: 12345});
    assert.equal(report.status, 'PASS');
    assert.equal(report.package.apparatus.id.length, 80);
    assert.deepEqual(await importCapability(report.package), report.package);
});

test('reservoir-only ancestry preserves its own obligations and can add only the previously absent standard operation', async () => {
    const app = apparatus('shielded');
    app.scope = ['reservoir'];
    const parent = await freezeCapability(app, construct(app));
    const originalReuse = await evaluateFrozenReuse(parent, {seed: 12345});
    assert.equal(originalReuse.status, 'PASS');
    assert.equal(originalReuse.cases.length, 3);
    assert.equal(originalReuse.measurements.length, 24);
    assert.ok(originalReuse.cases.every(item => item.operation === 'reservoir'));
    const report = await buildSuccessor(parent, {seed: 12345});
    assert.equal(report.status, 'PASS');
    assert.deepEqual(report.obligations.priorScope, ['reservoir']);
    assert.equal(report.obligations.priorCases.length, 3);
    assert.ok(report.obligations.priorCases.every(item => item.operation === 'reservoir' && item.status === 'PASS'));
    assert.equal(report.newFunction.accepted, true);
    assert.equal(report.newFunction.operation, 'standard');
    assert.deepEqual(report.newFunction.operations, ['standard']);
    assert.equal(report.newFunction.cases.length, 3);
    assert.ok(report.newFunction.cases.every(item => item.operation === 'standard' && item.status === 'PASS'));
    assert.equal(report.oldScope.diagnostic.operationMeasurement.operation, 'standard');
    assert.match(report.oldScope.reason, /newly required standard/);
    assert.equal(report.costs.ancestor, parent.costLedger.total);
    assert.deepEqual(await importCapability(report.package), report.package);
    const repeated = await buildSuccessor(report.package, {seed: 12345});
    assert.equal(repeated.status, 'FAIL');
    assert.equal(repeated.newFunction.accepted, false);
    assert.equal(repeated.newFunction.operation, null);
    assert.deepEqual(repeated.newFunction.operations, []);
    assert.deepEqual(repeated.newFunction.cases, []);
    assert.equal(repeated.obligations.priorCases.length, 6);
});
