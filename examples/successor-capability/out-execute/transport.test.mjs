// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {installedSource} from './source-manifest.mjs';
import {execute, retainCompletion} from './engine.mjs';
import {containment} from './fixtures.mjs';
import {prepareWorkRequest, inspectWorkRequest} from './transport.mjs';
import {clone, seal} from './model.mjs';

test('actual installed-source closure binds separate inert target drafts without token conversion', async () => {
    const manifest = await installedSource(), source = manifest.source;
    assert.ok(Object.keys(manifest.compilerSources).length >= 4);
    const state = await execute(containment(), {source}), archive = await retainCompletion(state);
    for (const target of ['manager-usdc', 'jobs-agialpha', 'fleet-qualified-review']) {
        const options = {projectId: 'one-project-history', target, expectedSource: source};
        const request = await prepareWorkRequest(archive, options);
        const checked = await inspectWorkRequest(request, options);
        assert.equal(checked.executable, false); assert.deepEqual(checked.authority, []);
        assert.equal(request.limits.spendBaseUnits, '0'); assert.equal(request.limits.tokenConversion, 'none');
        assert.equal(request.targetInterface.asset, target === 'manager-usdc' ? 'USDC' : target === 'jobs-agialpha' ? 'AGIALPHA' : null);
        for (const mutate of [r => r.limits.funded = true, r => r.targetInterface.asset = 'BTC',
            r => r.archiveSha256 = '0'.repeat(64), r => r.acceptance.independentEvaluator = 'self-approved']) {
            let corrupt = clone(request); mutate(corrupt); delete corrupt.digest; corrupt = await seal(corrupt);
            await assert.rejects(() => inspectWorkRequest(corrupt, options));
        }
    }
    await assert.rejects(() => prepareWorkRequest(archive, {projectId: 'one-project-history', target: 'manager-usdc'}), /EXPECTED_SOURCE/);
});
