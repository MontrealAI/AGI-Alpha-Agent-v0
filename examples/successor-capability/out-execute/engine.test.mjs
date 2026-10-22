// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {MODEL_SCHEMA, SEMANTICS, CHECKER_VERSION, clone, seal, validateModel} from './model.mjs';
import {exhaustive, verifyContract, verifyDecomposition} from './checker.mjs';
import {execute, startExecution, advanceExecution, restoreExecution, retainCompletion,
    inspectArchive, inspectCompletion, selectBoundary, decompose} from './engine.mjs';
import {containment, scalarCounterexample, interactingPaths, weightedStream} from './fixtures.mjs';
const source = {compilerSha256: 'a'.repeat(64), checkerSha256: 'b'.repeat(64), evaluatorVersion: CHECKER_VERSION};
const selection = {maxBoundary: 1, shortlist: ['b'], horizon: 8};
const run = (model, more = {}) => execute(model, {source, selection, ...more});

test('exact current witness changes while coordinator optimization stops', async () => {
    const before = await run(containment()); assert.equal(before.status, 'COMPLETE');
    assert.deepEqual(before.completion.artifact, {b: 0, x: 0, y: 0});
    const archive = await retainCompletion(before);
    const after = await run(containment(true), {archive});
    assert.deepEqual(after.completion.artifact, {b: 0, x: 1, y: 0});
    assert.equal(after.completion.selection.cost, 1);
    assert.equal(after.completion.change.semanticStop, true);
    assert.deepEqual(after.completion.change.retained, ['module:y']);
    assert.deepEqual(after.completion.change.rebuilt, ['module:x']);
    assert.equal(after.work.boundaryAssignments, 0);
    assert.equal(after.work.acceptanceBoundaryAssignments, 2);
    assert.ok(after.work.reuseAuditAssignments > 0);
    await inspectArchive(await retainCompletion(after));
});

test('same scalar optimum is not continuation equivalence', async () => {
    const before = await run(scalarCounterexample());
    const after = await run(scalarCounterexample(true), {archive: await retainCompletion(before)});
    assert.equal(before.completion.selection.cost, 0);
    assert.equal(after.completion.selection.cost, 2);
    assert.equal(after.completion.change.semanticStop, false);
    assert.ok(after.work.boundaryAssignments > 0);
});

test('two bipartite paths cannot compose into a two-color five-cycle', async () => {
    for (const colors of [2, 3]) {
        const model = interactingPaths(colors);
        const result = await execute(model, {source, selection: {maxBoundary: 2, shortlist: ['u', 'v'], horizon: 8}});
        assert.equal(result.completion.selection.status, colors === 2 ? 'INFEASIBLE' : 'OPTIMAL');
        assert.equal(result.completion.selection.status, exhaustive(model).status);
        await inspectCompletion(result.completion);
    }
});

test('source/evaluator/domain/scope changes conservatively invalidate evidence', async () => {
    const before = await run(containment()), archive = await retainCompletion(before);
    const sourceChanged = await run(containment(), {archive, source: {...source, compilerSha256: 'c'.repeat(64)}});
    assert.deepEqual(sourceChanged.completion.change.retained, []);
    assert.equal(sourceChanged.completion.change.semanticStop, false);
    await assert.rejects(() => run(containment(), {source: {...source, evaluatorVersion: 'stale'}}), /EVALUATOR/);
    const domainChanged = containment(); domainChanged.variables.find(v => v.id === 'x').domain = [1, 0];
    const revised = await run(domainChanged, {archive});
    assert.ok(revised.completion.change.rebuilt.includes('module:x'));
    const hidden = containment(); hidden.factors.push({id: 'hidden', scope: ['x', 'y'], costs: [0, 1, 1, 0]});
    assert.throws(() => verifyDecomposition(hidden, before.completion.decomposition), /HIDDEN_CROSS/);
    const repartitioned = await run(hidden, {archive});
    assert.deepEqual(repartitioned.completion.change.retained, []);
    assert.equal(repartitioned.completion.selection.cost, exhaustive(hidden).cost);
});

test('independent checker rejects rehashed wrong minima, witnesses and missing rows', async () => {
    const state = await run(containment()), original = state.completion.contracts[0];
    for (const mutation of [c => c.rows[0].cost++, c => c.rows[0].witness[0] ^= 1,
        c => c.rows.pop(), c => c.model.factors[0].costs[0]++, c => c.rows.reverse()]) {
        let corrupt = clone(original); mutation(corrupt); delete corrupt.digest; corrupt = await seal(corrupt);
        await assert.rejects(() => verifyContract(state.model, original.module, corrupt), /CHECKER_/);
    }
    let corrupt = clone(state.completion); corrupt.countedWork = 0; delete corrupt.digest; corrupt = await seal(corrupt);
    await assert.rejects(() => inspectCompletion(corrupt), /COST_ACCOUNT/);
});

test('partial cancellation survives export, restore and bounded resume without accepted output', async () => {
    let state = await startExecution(containment(), {source, selection});
    state = await advanceExecution(state, {modules: 1});
    assert.equal(state.status, 'PAUSED'); assert.equal(state.completion, null);
    state = await advanceExecution(state, {cancel: true});
    assert.equal(state.status, 'CANCELLED');
    const reopened = await restoreExecution(JSON.parse(JSON.stringify(state)));
    const finished = await advanceExecution(reopened.checkpoint, {modules: 8});
    assert.ok(reopened.countedVerificationWork > 0);
    assert.equal(finished.status, 'COMPLETE');
    assert.equal(finished.completion.selection.cost, exhaustive(containment()).cost);
    const forged = clone(state); forged.work.constructionAssignments = 0;
    await assert.rejects(() => restoreExecution(forged), /CHECKPOINT_WORK/);
    const low = await run(containment(), {budget: 1});
    assert.equal(low.status, 'INCONCLUSIVE'); assert.equal(low.completion, null);
    await assert.rejects(() => retainCompletion(low), /UNFINISHED/);
});

test('boundary-only revisions reuse interiors but recompute the current objective', async () => {
    const before = await run(containment()), model = containment(); model.factors[0].costs = [9, 0];
    const after = await run(model, {archive: await retainCompletion(before)});
    assert.deepEqual(after.completion.change.rebuilt, []);
    assert.equal(after.completion.change.semanticStop, false);
    assert.deepEqual(after.completion.artifact, {b: 1, x: 1, y: 1});
});

test('interacting extension retains old modules and constructs only the new interior', async () => {
    const before = await run(containment()), model = containment();
    model.variables.push({id: 'z', domain: [0, 1]});
    model.factors.push({id: 'newModule', scope: ['b', 'z'], costs: [0, 4, 4, 0]});
    const after = await run(model, {archive: await retainCompletion(before)});
    assert.deepEqual(after.completion.change.retained, ['module:x', 'module:y']);
    assert.deepEqual(after.completion.change.rebuilt, ['module:z']);
    assert.equal(after.completion.selection.cost, exhaustive(model).cost);
    await inspectArchive(await retainCompletion(after));
});

test('authored ternary snapshots agree with the independent full enumeration', async () => {
    for (const seed of [310000, 310001, 310002, 310003]) {
        let archive = null;
        for (const model of weightedStream(seed)) {
            const state = await execute(model, {source, archive});
            assert.equal(state.status, 'COMPLETE');
            assert.equal(state.completion.selection.cost, exhaustive(model).cost);
            archive = await retainCompletion(state);
        }
        await inspectArchive(archive);
    }
});

test('finite complete factor tables and budgets fail closed', () => {
    for (const change of [m => m.factors[0].costs.pop(), m => m.factors[0].costs[0] = -1,
        m => m.factors[0].costs[0] = Infinity, m => m.variables[0].domain.push(0),
        m => m.factors[0].scope.push('unknown'), m => m.schema = 'future']) {
        const model = containment(); change(model); assert.throws(() => validateModel(model));
    }
    assert.ok(selectBoundary(containment(), selection).inspected > 0);
    assert.equal(decompose(containment(), ['b']).modules.length, 2);
});

test('final-acceptance budget failures remain unaccepted and survive independent restore', async () => {
    const before = await run(containment()), archive = await retainCompletion(before);
    const full = await run(containment(true), {archive});
    const partial = await run(containment(true), {archive, budget: full.completion.countedWork - 1});
    assert.equal(partial.status, 'INCONCLUSIVE'); assert.equal(partial.reason, 'current-acceptance-exceeds-budget');
    assert.equal(partial.completion, null); assert.ok(partial.work.profileComparisons > 0);
    const restored = await restoreExecution(clone(partial));
    assert.deepEqual(restored.checkpoint.work, partial.work);
    assert.equal((await advanceExecution(restored.checkpoint)).status, 'INCONCLUSIVE');
    await assert.rejects(() => advanceExecution(clone(before)), /EXPLICIT_RESTORE/);
});

test('checkpoint terminal status and reason require a real reachable budget failure', async () => {
    const paused = await startExecution(containment(), {source, selection});
    for (const reason of ['fabricated-budget-failure', 'ingestion-selection-and-import-audit-exceed-budget',
        'next-module-exceeds-budget', 'boundary-selection-exceeds-budget', 'current-acceptance-exceeds-budget']) {
        await assert.rejects(() => restoreExecution({...clone(paused), status: 'INCONCLUSIVE', reason}), /CHECKPOINT_/);
    }
    await assert.rejects(() => restoreExecution({...clone(paused), reason: 'operator-cancelled'}), /TERMINAL_REASON/);
    await assert.rejects(() => restoreExecution({...clone(paused), status: 'CANCELLED', reason: null}), /TERMINAL_REASON/);
    const initialFailure = await run(containment(), {budget: 1});
    assert.equal((await restoreExecution(initialFailure)).checkpoint.status, 'INCONCLUSIVE');
    await assert.rejects(() => restoreExecution({...clone(initialFailure), status: 'PAUSED', reason: null}), /REACHABLE/);
    const nextFailure = await run(containment(), {budget: Object.values(paused.work).reduce((a, b) => a + b, 0)});
    assert.equal(nextFailure.reason, 'next-module-exceeds-budget');
    assert.equal((await restoreExecution(nextFailure)).checkpoint.status, 'INCONCLUSIVE');
    const completed = await run(containment());
    await assert.rejects(() => restoreExecution({...clone(completed), reason: 'operator-cancelled'}), /TERMINAL_REASON/);
});

test('actual ancestor profile comparisons are charged during reuse, restore and every archive depth', async () => {
    const first = await run(containment());
    const second = await run(containment(true), {archive: await retainCompletion(first)});
    const archive = await retainCompletion(second), checked = await inspectArchive(archive);
    assert.equal(checked.audit.profileComparisons, second.work.profileComparisons);
    assert.ok(checked.audit.profileComparisons > 0);
    const third = await run(containment(true), {archive});
    assert.equal(third.work.reuseAuditProfileComparisons, checked.audit.profileComparisons);
    const thirdArchive = await inspectArchive(await retainCompletion(third));
    assert.equal(thirdArchive.audit.profileComparisons, second.work.profileComparisons + third.work.profileComparisons);
    const restored = await restoreExecution(third);
    assert.equal(restored.verificationWork.reuseAuditProfileComparisons,
        third.work.reuseAuditProfileComparisons + third.work.profileComparisons);
});

const singleton = cost => ({schema: MODEL_SCHEMA, semantics: SEMANTICS,
    variables: [{id: 'x', domain: [0]}], factors: [{id: 'f', scope: ['x'], costs: [cost]}]});

test('exact budgets accept feasible and infeasible results without a speculative feasibility charge', async () => {
    for (const cost of [null, 0]) for (const maxBoundary of [0, 1]) {
        const model = singleton(cost), policy = {maxBoundary, shortlist: null, horizon: 8};
        const full = await execute(model, {source, selection: policy});
        assert.equal(full.completion.selection.status, cost === null ? 'INFEASIBLE' : 'OPTIMAL');
        assert.equal(full.contracts.length, maxBoundary === 0 ? 1 : 0);
        if (maxBoundary === 0) assert.equal(full.completion.countedWork, cost === null ? 11 : 14);
        const exact = await execute(model, {source, selection: policy, budget: full.completion.countedWork});
        assert.equal(exact.status, 'COMPLETE'); assert.deepEqual(exact.work, full.work);
        assert.deepEqual(exact.completion.selection, full.completion.selection);
        assert.deepEqual(exact.completion.artifact, full.completion.artifact);
        await inspectCompletion(exact.completion);
        assert.equal((await restoreExecution(clone(exact))).checkpoint.status, 'COMPLETE');
        const reasons = new Set();
        for (let budget = 1; budget < full.completion.countedWork; budget++) {
            const low = await execute(model, {source, selection: policy, budget});
            assert.equal(low.status, 'INCONCLUSIVE'); assert.equal(low.completion, null);
            reasons.add(low.reason);
            const restored = await restoreExecution(clone(low));
            assert.deepEqual(restored.checkpoint.work, low.work);
            assert.equal((await advanceExecution(restored.checkpoint)).status, 'INCONCLUSIVE');
            assert.equal(restored.verificationWork.reuseAuditAssignments,
                low.work.reuseAuditAssignments + low.work.constructionAssignments + low.work.boundaryAssignments);
            assert.equal(restored.verificationWork.reuseAuditFactorLookups, low.work.reuseAuditFactorLookups
                + low.work.constructionFactorLookups + low.work.profileLookups + low.work.boundaryFactorLookups);
            assert.equal(low.work.acceptanceBoundaryAssignments, 0);
            assert.equal(low.work.materializedValues, 0); assert.equal(low.work.outputFactorLookups, 0);
            if (low.reason === 'boundary-selection-exceeds-budget') assert.equal(low.work.boundaryAssignments, 0);
            if (low.reason === 'current-acceptance-exceeds-budget') assert.equal(low.work.boundaryAssignments, 1);
            await assert.rejects(() => restoreExecution({...clone(low), budget: full.budget}), /CHECKPOINT_/);
        }
        assert.ok(reasons.has('boundary-selection-exceeds-budget'));
        assert.ok(reasons.has('current-acceptance-exceeds-budget'));
        if (maxBoundary === 0) assert.ok(reasons.has('next-module-exceeds-budget'));
    }
});

test('semantic-stop exact budgets omit only the reused selection, never current acceptance', async () => {
    for (const cost of [null, 0]) for (const maxBoundary of [0, 1]) {
        const model = singleton(cost), policy = {maxBoundary, shortlist: null, horizon: 8};
        const before = await execute(model, {source, selection: policy}), archive = await retainCompletion(before);
        const full = await execute(model, {source, selection: policy, archive});
        assert.equal(full.completion.change.semanticStop, true);
        assert.equal(full.work.boundaryAssignments, 0); assert.equal(full.work.profileLookups, 0);
        assert.equal(full.work.acceptanceBoundaryAssignments, 1);
        const exact = await execute(model, {source, selection: policy, archive, budget: full.completion.countedWork});
        assert.equal(exact.status, 'COMPLETE'); assert.deepEqual(exact.work, full.work);
        await inspectArchive(await retainCompletion(exact));
        const low = await execute(model, {source, selection: policy, archive, budget: full.completion.countedWork - 1});
        assert.equal(low.status, 'INCONCLUSIVE'); assert.equal(low.reason, 'current-acceptance-exceeds-budget');
        assert.equal(low.completion, null); assert.equal(low.work.boundaryAssignments, 0);
        assert.equal(low.work.acceptanceBoundaryAssignments, 0);
        const restored = await restoreExecution(clone(low));
        assert.deepEqual(restored.checkpoint.work, low.work);
        assert.equal(restored.verificationWork.reuseAuditAssignments, low.work.reuseAuditAssignments);
        assert.equal(restored.verificationWork.reuseAuditFactorLookups, low.work.reuseAuditFactorLookups);
        assert.equal(restored.verificationWork.reuseAuditProfileComparisons,
            low.work.reuseAuditProfileComparisons + low.work.profileComparisons);
        await assert.rejects(() => restoreExecution({...clone(low), budget: full.budget}), /CHECKPOINT_/);
    }
});
