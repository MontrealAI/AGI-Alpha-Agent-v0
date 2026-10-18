// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { canonical, digest } from '../../docs/assets/successor/engine.mjs';
import { createJoinMission, runJoinExperiment } from './engine.mjs';
import { createProject, appendCycle, serializeProject } from './project.mjs';
import { createNativeHandoff, inspectNativeHandoff, runNativeHandoff, inspectNativeReturn,
    importNativeReturn, inspectContinuity, nativeCatalog, exactDigest, COMPATIBILITY } from './continuity.mjs';

const sourceHash = 'b'.repeat(64);
const mission = createJoinMission({ leftCsv: 'id,name,value\nA,left,10\nA,same,20\nB,missing,3\n',
    rightCsv: 'key,name,value\nA,same,20\nA,right,30\nC,missing,4\n', leftKey: 'id', rightKey: 'key' });
const initial = appendCycle(createProject({ name: 'Catalog Ω' }),
    { mission, result: await runJoinExperiment(mission), sourceHash: 'a'.repeat(64) });
const options = { route: 'AGIALPHA', sourceHash, rights: { dataClass: 'synthetic',
    source: 'Test fixture; no personal data', license: 'Apache-2.0' }, owner: 'local-owner',
    reviewMinutes: 10, compiledAt: '2026-10-18T15:00:00.000Z' };
const handoffRaw = await createNativeHandoff(initial, options);
const returnRaw = await runNativeHandoff(handoffRaw, { sourceHash });
const recordRaw = await importNativeReturn(initial, handoffRaw, returnRaw, { sourceHash });
async function reseal(raw, change) {
    const value = JSON.parse(raw); delete value.sha256; await change(value);
    return canonical({ ...value, sha256: await exactDigest(canonical(value)) });
}
async function changePack(change) {
    return reseal(returnRaw, async value => {
        const pack = JSON.parse(value.nativePackRaw); delete pack.integrityDigest;
        await change(pack);
        pack.integrityDigest = await digest('workbench-pack', pack);
        value.nativePackRaw = canonical(pack);
    });
}

test('native handoff retains exact project history and executable catalog semantics', async () => {
    const { handoff, project, cycle, spec, compilation } = await inspectNativeHandoff(handoffRaw);
    assert.equal(handoff.project.raw, serializeProject(initial));
    assert.equal(handoff.project.sha256, await exactDigest(serializeProject(initial)));
    assert.equal(project.id, initial.id); assert.equal(cycle.id, initial.cycles[0].id);
    assert.equal(canonical(spec.inputs.mission), canonical(mission));
    assert.equal(handoff.cycle.missionSha256, await exactDigest(canonical(mission)));
    assert.equal(spec.schema, 'successor-workbench/v1');
    assert.equal(spec.family, 'catalog-reconciliation');
    assert.deepEqual(nativeCatalog.validate(spec), spec);
    assert.equal(compilation.status, 'SEALED'); assert.equal(compilation.graph.nodes.length, 7);
    assert.ok(compilation.graph.nodes.every(job => job.state === 'DRAFT'));
    assert.equal(compilation.budgetReservations.unit, 'AGIALPHA');
    assert.equal(compilation.budgetReservations.reservedBaseUnits, '0');
    assert.equal(compilation.authorityCreated, 'NONE');
    assert.equal(COMPATIBILITY.fleet, 'catalog-executor-not-installed');
    assert.equal(COMPATIBILITY.manager, 'catalog-executor-not-installed');
});

test('actual native SDK execution preserves duplicate pairs, missing rows and conflicts', async () => {
    const read = await inspectNativeReturn(handoffRaw, returnRaw);
    assert.equal(read.pack.result.summary.matchedPairs, 4);
    assert.equal(read.pack.result.summary.unmatchedLeft, 1);
    assert.equal(read.pack.result.summary.unmatchedRight, 1);
    assert.equal(read.pack.result.summary.conflicts, 3);
    const exact = JSON.parse(read.files.find(file => file.name === 'exact-result.json').content);
    assert.deepEqual(exact.mission, mission);
    for (const strategy of exact.result.strategies) assert.deepEqual(strategy.pairs, [[0, 0], [0, 1], [1, 0], [1, 1]]);
    assert.equal(read.files.length, 5);
    assert.equal(read.pack.frozen.sourceHash, sourceHash);
    assert.equal(read.pack.frozen.provider, null);
    assert.equal(read.pack.economics.computeCost, null);
    assert.equal(read.independentReview, false); assert.equal(read.productionQualified, false);
    assert.equal(read.currentReview, null); assert.equal(read.runAuthorized, false);
    assert.deepEqual(read.authority, []);
});

test('handoff requires an explicit permitted-rights declaration and a supported route', async () => {
    await assert.rejects(createNativeHandoff(initial, { ...options, rights: undefined }), /EXPLICIT_RIGHTS/);
    await assert.rejects(createNativeHandoff(initial, { ...options, rights: { ...options.rights, dataClass: 'private' } }));
    await assert.rejects(createNativeHandoff(initial, { ...options, route: 'USDC' }), /NATIVE_ROUTE_UNSUPPORTED/);
    await assert.rejects(createNativeHandoff(createProject(), options), /RUN_CATALOG_FIRST/);
    await assert.rejects(createNativeHandoff(initial, { ...options, name: 'X'.repeat(49) }), /NATIVE_NAME/);
});

test('unknown fields, duplicate JSON fields, altered routes and rehashed changed inputs are refused', async () => {
    await assert.rejects(inspectNativeHandoff(handoffRaw.replace('{', '{"schema":"duplicate",')));
    for (const change of [
        value => { value.extra = true; },
        value => { value.authority = 'production'; },
        value => { value.route.asset = 'USDC'; },
        value => { value.cycle.id = crypto.randomUUID(); },
        value => { value.project.revision += 1; },
        value => { const spec = JSON.parse(value.specRaw); spec.inputs.mission.left.rows[0][1] = 'changed'; value.specRaw = canonical(spec); },
        value => { const plan = JSON.parse(value.compilationRaw); plan.graph.nodes[0].state = 'ACCEPTED'; value.compilationRaw = canonical(plan); },
    ]) await assert.rejects(inspectNativeHandoff(await reseal(handoffRaw, change)));
});

test('source substitutions cannot execute; cancellation returns no completed native evidence', async () => {
    await assert.rejects(runNativeHandoff(handoffRaw, { sourceHash: 'c'.repeat(64) }), /SOURCE_DRIFT/);
    await assert.rejects(runNativeHandoff(handoffRaw), /SOURCE_HASH/);
    const controller = new AbortController(); controller.abort();
    await assert.rejects(runNativeHandoff(handoffRaw, { sourceHash, signal: controller.signal }), /CANCELLED/);
});

test('rehashed provider, authority, economics and admission claims do not pass as local native evidence', async () => {
    for (const change of [
        pack => { pack.frozen.provider = 'external-provider'; },
        pack => { pack.frozen.authority = ['spend']; },
        pack => { pack.evaluation.independentProof = true; },
        pack => { pack.evaluation.admission = 'ADMIT'; },
        pack => { pack.economics.computeCost = 0; },
        pack => { pack.economics.humanMinutes = 0; },
        pack => { pack.chronicle[0].inheritedProof = true; },
    ]) await assert.rejects(inspectNativeReturn(handoffRaw, await changePack(change)));
});

test('rehashed summary, pairs and artifact changes fail independent exact recomputation', async () => {
    for (const change of [
        pack => { pack.result.summary.matchedPairs = 3; },
        pack => { pack.result.evidence.experiment.strategies[0].pairs.pop(); },
        async pack => {
            const artifact = pack.result.artifacts[0]; artifact.content = 'invented output\n';
            const { digest: _, ...body } = artifact;
            artifact.digest = await digest('workbench-artifact', body);
        },
    ]) await assert.rejects(inspectNativeReturn(handoffRaw, await changePack(change)));
});

test('wrong project, stale cycle, changed source and duplicate returns are rejected', async () => {
    const other = appendCycle(createProject(), { mission, result: await runJoinExperiment(mission), sourceHash });
    await assert.rejects(importNativeReturn(other, handoffRaw, returnRaw), /STALE_PROJECT_RETURN/);
    const advanced = appendCycle(initial, { mission, result: await runJoinExperiment(mission), sourceHash });
    await assert.rejects(importNativeReturn(advanced, handoffRaw, returnRaw), /STALE_PROJECT_RETURN/);
    await assert.rejects(importNativeReturn(initial, handoffRaw, returnRaw, { sourceHash: 'c'.repeat(64) }), /SOURCE_DRIFT/);
    await assert.rejects(importNativeReturn(initial, handoffRaw, returnRaw, { priorRecord: recordRaw }), /DUPLICATE_OR_CHANGED_RETURN/);
    const changedReturn = await reseal(returnRaw, value => { value.projectId = other.id; });
    await assert.rejects(inspectNativeReturn(handoffRaw, changedReturn), /RETURN_BINDING/);
});

test('later native runs append exact project snapshots and preserve original cycle and return bytes', async () => {
    const advanced = appendCycle(initial, { mission, result: await runJoinExperiment(mission), sourceHash });
    const nextHandoff = await createNativeHandoff(advanced, options);
    const nextReturn = await runNativeHandoff(nextHandoff, { sourceHash });
    const retained = await importNativeReturn(advanced, nextHandoff, nextReturn, { priorRecord: recordRaw, sourceHash });
    const original = await inspectContinuity(recordRaw), next = await inspectContinuity(retained);
    assert.equal(next.project.id, initial.id); assert.equal(next.project.cycles.length, 2);
    assert.equal(canonical(next.project.cycles[0]), canonical(initial.cycles[0]));
    assert.deepEqual(next.continuity.snapshots[0], original.continuity.snapshots[0]);
    assert.deepEqual(next.continuity.returns[0], original.continuity.returns[0]);
    assert.equal(next.continuity.returns[0].returnRaw, returnRaw);
    assert.equal(next.continuity.returns.length, 2); assert.equal(next.continuity.snapshots.length, 2);
    assert.deepEqual(next.activeProof, []); assert.deepEqual(next.authority, []);
});

test('continuity imports reject rewritten snapshots and invented qualification after checksum resealing', async () => {
    await assert.rejects(inspectContinuity(await reseal(recordRaw, value => { value.qualification = 'specialist_asi'; })));
    await assert.rejects(inspectContinuity(await reseal(recordRaw, async value => {
        const project = JSON.parse(value.snapshots[0].raw); project.cycles[0].mission.left.rows[0][1] = 'changed';
        value.snapshots[0].raw = canonical(project); value.snapshots[0].sha256 = await exactDigest(value.snapshots[0].raw);
    })));
    const rewrite = structuredClone(initial); rewrite.name = 'changed without revision';
    const handoff = await createNativeHandoff(rewrite, options), returned = await runNativeHandoff(handoff, { sourceHash });
    await assert.rejects(importNativeReturn(rewrite, handoff, returned, { priorRecord: recordRaw }), /REVISION_CONFLICT/);
});

test('capacity failure never deletes or mutates earlier exact project and return bytes', async () => {
    const before = recordRaw;
    await assert.rejects(inspectContinuity(' '.repeat(2_000_001)), /CAPACITY/);
    const record = JSON.parse(recordRaw);
    const oversized = await reseal(recordRaw, value => { value.returns = Array.from({ length: 9 }, () => record.returns[0]); });
    await assert.rejects(inspectContinuity(oversized), /HISTORY_CAPACITY/);
    assert.equal(recordRaw, before); assert.equal((await inspectContinuity(recordRaw)).continuity.returns[0].returnRaw, returnRaw);
});
