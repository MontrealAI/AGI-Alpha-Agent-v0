// SPDX-License-Identifier: Apache-2.0
/** Exercise the committed computation bundle without a DOM, browser or external service. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
import {execute, retainCompletion} from './engine.mjs';
import {containment} from './fixtures.mjs';
import {CHECKER_VERSION} from './model.mjs';

async function bundledComputation(body) {
    const page = await readFile(new URL('../../../docs/successor/capabilities/index.html', import.meta.url), 'utf8');
    const script = page.match(/<script>([\s\S]*?)<\/script>/)?.[1];
    assert.ok(script, 'The committed portable page must contain its computation bundle.');
    const marker = '\n// SPDX-License-Identifier: Apache-2.0\n// The injected capability model';
    const split = script.indexOf(marker);
    assert.ok(split > 0 && script.lastIndexOf(marker) === split, 'Locate the UI boundary without executing the UI.');
    const result = await runInNewContext(script.slice(0, split)
        + `\nreturn (async()=>{${body}})();\n})();`, {crypto: globalThis.crypto, TextEncoder, TextDecoder});
    return JSON.parse(result);
}

test('generated bundle exports generator functions and preserves current computation after history restore', async () => {
    const result = await bundledComputation(`
        const assignments = [...outExecuteModel.assignments(['x'], {x: [0, 1]})];
        const source = {compilerSha256: 'a'.repeat(64), checkerSha256: 'b'.repeat(64),
            evaluatorVersion: outExecuteModel.CHECKER_VERSION};
        let history = outEvolve.createOutEvolveWorkspace('generated-bundle-history');
        let state = await outExecute.startExecution(outExecuteFixtures.containment(), {source});
        const save = async () => {history = await outEvolve.appendOutEvolveEvent(history, 'execution',
            {projectId: history.id, checkpoint: state});};
        await save(); state = await outExecute.advanceExecution(state, {modules: 1}); await save();
        if (state.next !== 1) throw Error('The first bundled component did not execute.');
        state = await outExecute.advanceExecution(state, {cancel: true}); await save();
        const reopened = await outEvolve.inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
        history = reopened.workspace; state = reopened.latestExecution;
        state = await outExecute.advanceExecution(state, {modules: 8}); await save();
        const first = state.completion;
        state = await outExecute.execute(outExecuteFixtures.containment(true),
            {source, archive: await outExecute.retainCompletion(state)}); await save();
        const checked = await outEvolve.inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
        return JSON.stringify({assignments, first, second: state.completion,
            completions: checked.executionCompletions.length, status: checked.latestExecution.status});
    `);
    assert.deepEqual(result.assignments, [[0], [1]]);
    assert.equal(result.status, 'COMPLETE'); assert.equal(result.completions, 2);
    const source = {compilerSha256: 'a'.repeat(64), checkerSha256: 'b'.repeat(64), evaluatorVersion: CHECKER_VERSION};
    const first = await execute(containment(), {source});
    const second = await execute(containment(true), {source, archive: await retainCompletion(first)});
    for (const [bundled, direct] of [[result.first, first.completion], [result.second, second.completion]]) {
        for (const key of ['selection', 'artifact', 'work', 'change', 'countedWork']) {
            assert.deepEqual(bundled[key], direct[key], key);
        }
    }
    assert.equal(result.second.change.semanticStop, true);
});
