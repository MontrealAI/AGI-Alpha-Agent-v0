// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import test from 'node:test';
import * as alpha from './engine.mjs';
import { discoverStrategy, strategyExampleMission } from './research.mjs';
import { buildPlanCapability } from './capability.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const sourceHash = 'c'.repeat(64);
const sources = async () => ({ sourceHash, engineSource: await readFile(join(here, 'engine.mjs'), 'utf8'),
    researchSource: await readFile(join(here, 'research.mjs'), 'utf8') });

test('retained constructed capability imports outside the repository and executes changed inputs with exact evidence', async () => {
    const mission = strategyExampleMission();
    const report = await discoverStrategy(mission, { sourceHash, confirmationSeed: 99 });
    assert.equal(report.decision.promoted, true);
    const options = await sources(), code = await buildPlanCapability(mission, report, options);
    assert.equal(/^\s*import\b/m.test(code), false);
    assert.equal(/\bimport\s*\(/.test(code), false);
    assert.equal(code.includes('node:'), false);
    const root = await mkdtemp(join(tmpdir(), 'successor-retained-capability-'));
    try {
        const path = join(root, 'retained-catalog.mjs');
        await writeFile(path, code);
        const module = await import(pathToFileURL(path).href);
        const input = { leftCsv: 'sku,title\nNEW,Alpha\nNEW,Beta\nLEFT,Only left',
            rightCsv: 'key,title\nNEW,Alpha\nNEW,=2+2\nRIGHT,Only right', leftKey: 'sku', rightKey: 'key' };
        const expectedMission = alpha.createJoinMission(input);
        const expected = alpha.executeJoin(expectedMission, 'nested_scan').pairs;
        const result = module.reconcileCatalogs(input);
        assert.deepEqual(result.pairs, expected);
        assert.equal(alpha.verifyJoinResult(expectedMission, result.pairs), true);
        assert.deepEqual(result.reconciliation.unmatchedLeft, [2]);
        assert.deepEqual(result.reconciliation.unmatchedRight, [2]);
        assert.equal(result.reconciliation.conflicts.length, 3);
        assert.equal(alpha.parseCsv(result.joinedCsv).rows.length, 4);
        assert.ok(result.joinedCsv.includes("'=2+2"));
        assert.equal(JSON.parse(result.exactJson).mission.right.rows[1][1], '=2+2');
        assert.equal(result.scope.externalAuthority, false);
        assert.equal(result.scope.independentlyQualified, false);
        assert.equal(result.scope.planHash, report.decision.retainedPlanHash);
        assert.deepEqual(module.metadata.retainedPlan, report.decision.retainedPlan);
        assert.equal(module.metadata.componentHashes.engine,
            createHash('sha256').update(options.engineSource).digest('hex'));
        assert.throws(() => { module.metadata.retainedPlan.guard.op = 'none'; });
        assert.throws(() => module.reconcileCatalogs({ ...input, leftKey: 'missing' }));
    } finally { await rm(root, { recursive: true, force: true }); }
});

test('a held research record exports its retained incumbent instead of its rejected nominee', async () => {
    const mission = alpha.createSampleMission();
    const report = await discoverStrategy(mission, { sourceHash, confirmationSeed: 23 });
    assert.equal(report.decision.state, 'held');
    const code = await buildPlanCapability(mission, report, await sources());
    const module = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
    assert.equal(module.metadata.planHash, report.incumbent.planHash);
    assert.deepEqual(module.metadata.retainedPlan, report.incumbent.plan);
    assert.equal(module.metadata.origin.decision, 'held');
});

test('builder refuses forged research, mismatched source context and unsupported source inputs', async () => {
    const mission = alpha.createSampleMission({ leftRows: 5, rightRows: 7 });
    const report = await discoverStrategy(mission, { sourceHash, confirmationSeed: 12 });
    const good = await sources();
    const forged = structuredClone(report); forged.decision.retainedPlan.leaf.large.op = 'run_shell';
    await assert.rejects(buildPlanCapability(mission, forged, good));
    await assert.rejects(buildPlanCapability(mission, report, { ...good, sourceHash: 'd'.repeat(64) }));
    for (const options of [null, {}, { ...good, engineSource: null }, { ...good, researchSource: {} },
        { ...good, engineSource: good.engineSource + '\nimport fs from "node:fs";\n' },
        { ...good, researchSource: good.researchSource + '\nexport default 1;\n' },
        { ...good, engineSource: good.engineSource + '\neval("1");\n' },
        { ...good, engineSource: good.engineSource + 'x'.repeat(250001) }]) {
        await assert.rejects(buildPlanCapability(mission, report, options));
    }
});

test('retained-program resource constraints are checked again for new workloads', async () => {
    const mission = strategyExampleMission();
    const report = await discoverStrategy(mission, { sourceHash, maxAuxiliaryRows: 0, confirmationSeed: 42 });
    assert.equal(report.decision.retainedPlan.guard.op, 'uniform_key');
    const code = await buildPlanCapability(mission, report, await sources());
    const module = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
    assert.throws(() => module.reconcileCatalogs({ leftCsv: 'id\na\nb', rightCsv: 'id\na\nb', leftKey: 'id', rightKey: 'id' }),
        /auxiliary-row constraint/);
});
