// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { canonical } from '../../docs/assets/successor/engine.mjs';
import { createProject, serializeProject } from './project.mjs';
import { discoverStrategy, resolveDiscrepancies } from './research.mjs';
import { createNativeHandoff, runNativeHandoff, importNativeReturn } from './continuity.mjs';
import { inspectLearningArchive } from './learning.mjs';

// Actual GUI export from 7cf97aa3, before the shared validator extraction. Its
// labeled protocol-double return is historical test evidence, not qualification.
const oldRaw = await readFile(new URL('./fixtures/learning-archive-7cf.json', import.meta.url), 'utf8');
const old = JSON.parse(oldRaw);
const cycle = old.project.cycles[0];
const strategy = await discoverStrategy(cycle.mission, { sourceHash:cycle.sourceHash, confirmationSeed:29 });
const resolution = resolveDiscrepancies(cycle.mission, cycle.result);
const sourceHash = 'c'.repeat(64);
const nativeHandoffRaw = await createNativeHandoff(old.project, {
    route:'AGIALPHA', sourceHash, owner:'local-owner', reviewMinutes:10,
    rights:{dataClass:'synthetic',source:'Synthetic test fixture; no personal data',license:'Apache-2.0'},
    compiledAt:'2026-10-19T12:00:00.000Z',
});
const nativeReturnRaw = await runNativeHandoff(nativeHandoffRaw, { sourceHash });
const nativeContinuityRaw = await importNativeReturn(old.project, nativeHandoffRaw, nativeReturnRaw, { sourceHash });
const full = {...old, records:[{cycleId:cycle.id,strategy,resolution}],nativeHandoffRaw,nativeContinuityRaw};

test('the actual old GUI archive preserves catalog lineage, exact attempts and reviewed incumbent bytes', async()=>{
    const checked = await inspectLearningArchive(oldRaw);
    assert.equal(canonical(old),oldRaw);
    assert.equal(serializeProject(checked.project),canonical(old.project));
    assert.equal(checked.project.cycles.length,1);
    assert.equal(checked.computerHistoryRaw,old.computerHistoryRaw);
    assert.equal(checked.checkedComputer.records.length,2);
    for (const [index, record] of checked.checkedComputer.records.entries()) {
        assert.equal(record.handoffRaw,JSON.parse(old.computerHistoryRaw).records[index].handoffRaw);
        assert.equal(record.returnRaw,JSON.parse(old.computerHistoryRaw).records[index].returnRaw);
    }
    assert.equal(checked.checkedComputer.records[0].review.decision,'useful');
    assert.equal(checked.checkedComputer.records[1].review,null);
    assert.equal(oldRaw,await readFile(new URL('./fixtures/learning-archive-7cf.json', import.meta.url),'utf8'));
});

test('both archive versions use native research, resolution and continuity checks without rewriting history', async()=>{
    const raw = JSON.stringify(full,null,2), checked = await inspectLearningArchive(raw);
    assert.equal(checked.nativeHandoffRaw,nativeHandoffRaw);
    assert.equal(checked.nativeContinuityRaw,nativeContinuityRaw);
    assert.equal(checked.computerHistoryRaw,old.computerHistoryRaw);
    assert.equal(canonical(checked.records),canonical(full.records));
    assert.equal(checked.records[0].strategy.decision.retainedPlanHash,strategy.decision.retainedPlanHash);
    const v1 = {...full,schema:'successor-alpha-learning-archive/v1'};
    delete v1.computerHistoryRaw;
    const checkedV1 = await inspectLearningArchive(canonical(v1));
    assert.equal(checkedV1.checkedComputer,null);
    assert.equal(checkedV1.nativeContinuityRaw,nativeContinuityRaw);
    assert.equal(raw,JSON.stringify(full,null,2));
});

test('archive containers cannot add authority, change lineage, detach lessons or promote altered native evidence', async()=>{
    for (const change of [
        value=>{value.authority='production';},
        value=>{value.project=createProject({name:'Different project',goal:old.project.goal});},
        value=>{value.records[0].cycleId=crypto.randomUUID();},
        value=>{value.records.push(structuredClone(value.records[0]));},
        value=>{value.records[0].strategy.externalAuthority=true;},
        value=>{value.records[0].resolution.coverage.originalOccurrences+=1;},
        value=>{value.nativeHandoffRaw=value.nativeHandoffRaw.replace('"authority":"none"','"authority":"production"');},
        value=>{value.nativeContinuityRaw=value.nativeContinuityRaw.replace('"authority":"none"','"authority":"production"');},
        value=>{value.computerHistoryRaw=value.computerHistoryRaw.replace('"authority":"none"','"authority":"production"');},
    ]) {
        const value = structuredClone(full); change(value);
        assert.ok(canonical(value)!==canonical(full),'mutation must change the imported archive');
        await assert.rejects(inspectLearningArchive(canonical(value)));
    }
});

test('complete imports retain the existing exact-field, duplicate-key and two-megabyte bounds', async()=>{
    await assert.rejects(inspectLearningArchive(oldRaw.replace('{','{"schema":"duplicate",')));
    await assert.rejects(inspectLearningArchive(' '.repeat(2_000_001)));
    await assert.rejects(inspectLearningArchive(canonical({...old,schema:'successor-alpha-learning-archive/v1'})));
    const missing = {...old}; delete missing.computerHistoryRaw;
    await assert.rejects(inspectLearningArchive(canonical(missing)));
});
