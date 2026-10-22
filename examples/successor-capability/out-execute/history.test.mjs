// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createOutEvolveWorkspace, appendOutEvolveEvent, inspectOutEvolveWorkspace, requireHistoryContinuation, inspectExecutionRecovery} from '../out-evolve-workspace.mjs';
import {CHECKER_VERSION, clone} from './model.mjs';
import {startExecution, advanceExecution, execute, retainCompletion} from './engine.mjs';
import {containment} from './fixtures.mjs';
const source = {compilerSha256: 'a'.repeat(64), checkerSha256: 'b'.repeat(64), evaluatorVersion: CHECKER_VERSION};
const options = {source, selection: {maxBoundary: 1, shortlist: ['b'], horizon: 8}};
const append = (history, checkpoint) => appendOutEvolveEvent(history, 'execution', {projectId: history.id, checkpoint});

test('Out-Execute extends one existing Out-Evolve history with failures, interruptions, acceptance and reuse', async () => {
    let history = createOutEvolveWorkspace('shared-project-history');
    history = await appendOutEvolveEvent(history, 'failure', {message: 'Earlier Out-Evolve attempt failed.'});
    let state = await startExecution(containment(), options);
    history = await append(history, state);
    state = await advanceExecution(state, {modules: 1}); history = await append(history, state);
    state = await advanceExecution(state, {cancel: true}); history = await append(history, state);
    const interrupted = JSON.parse(JSON.stringify(history));
    assert.equal((await inspectOutEvolveWorkspace(interrupted)).latestExecution.status, 'CANCELLED');
    state = await advanceExecution(state, {modules: 8}); history = await append(history, state);
    const next = await execute(containment(true), {...options, archive: await retainCompletion(state)});
    history = await append(history, next);
    const opened = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.equal(opened.failed, 1);
    assert.equal(opened.executionCompletions.length, 2);
    assert.equal(opened.latestExecution.completion.change.semanticStop, true);
    assert.ok(opened.executionVerificationWork > 0);
    assert.throws(() => requireHistoryContinuation(history, interrupted), /discard/);
});

test('pending attempts, detached ancestry and cross-project data cannot overwrite the history', async () => {
    let history = createOutEvolveWorkspace('frozen-project-history');
    const pending = await startExecution(containment(), options); history = await append(history, pending);
    const other = await startExecution(containment(true), options);
    await assert.rejects(() => append(history, other), /pending/);
    await assert.rejects(() => appendOutEvolveEvent(history, 'execution', {projectId: 'other-project', checkpoint: pending}), /identity/);
    const completed = await execute(containment(), options), successor = await execute(containment(true),
        {...options, archive: await retainCompletion(completed)});
    await assert.rejects(() => append(createOutEvolveWorkspace('detached-project'), successor), /ancestry/);
});


test('terminal forgery cannot release a pending history or reclassify a genuine inconclusive attempt', async () => {
    let history = createOutEvolveWorkspace('terminal-guard-history');
    const paused = await startExecution(containment(), options); history = await append(history, paused);
    const forged = {...clone(paused), status: 'INCONCLUSIVE', reason: 'next-module-exceeds-budget'};
    await assert.rejects(() => append(history, forged), /BUDGET_REASON/);
    const newAttempt = await startExecution(containment(true), options);
    await assert.rejects(() => append(history, newAttempt), /pending/);
    const low = await execute(containment(), {...options, budget: 1});
    let terminal = await append(createOutEvolveWorkspace('real-terminal-history'), low);
    await assert.rejects(() => append(terminal, low), /stale/);
});

test('saved and unsaved recovery wrappers round trip without dropping the original history or progress', async () => {
    let history = createOutEvolveWorkspace('recovery-roundtrip-history');
    history = await appendOutEvolveEvent(history, 'failure', {message: 'A retained prior failure.'});
    let state = await startExecution(containment(), options); history = await append(history, state);
    state = await advanceExecution(state, {modules: 1}); history = await append(history, state);
    const ordinary = {schema: 'out-execute-recovery/v1', history, checkpoint: state};
    const opened = await inspectExecutionRecovery(clone(ordinary), {current: history});
    assert.deepEqual(opened.workspace, history); assert.equal(opened.recovery.appended, false);
    const completed = await advanceExecution(state, {modules: 8});
    history = await appendOutEvolveEvent(history, 'failure', {message: 'Failed to append the new checkpoint; preserve this failure too.'});
    const unsaved = {schema: 'out-execute-unsaved-recovery/v1', history, checkpoint: completed};
    const recovered = await inspectExecutionRecovery(clone(unsaved), {current: history});
    assert.deepEqual(recovered.workspace.events.slice(0, history.events.length), history.events);
    assert.deepEqual(recovered.latestExecution.completion, completed.completion);
    assert.equal(recovered.recovery.appended, true); assert.equal(recovered.failed, 2);
    const second = await inspectExecutionRecovery({schema: ordinary.schema, history: recovered.workspace,
        checkpoint: recovered.latestExecution}, {current: recovered.workspace});
    assert.deepEqual(second.workspace, recovered.workspace);
    await assert.rejects(() => inspectExecutionRecovery({...ordinary, checkpoint: completed}), /differs/);
    await assert.rejects(() => inspectExecutionRecovery(ordinary, {current: recovered.workspace}), /discard/);
    const rebound = await startExecution(containment(true), options);
    await assert.rejects(() => inspectExecutionRecovery({...unsaved, checkpoint: rebound}), /pending/);
    const corrupt = clone(completed); corrupt.completion.artifact.x = 65535;
    await assert.rejects(() => inspectExecutionRecovery({...unsaved, checkpoint: corrupt}));
    await assert.rejects(() => inspectExecutionRecovery({...unsaved, extra: true}), /wrapper/);
});
