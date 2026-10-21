// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {makeArtifacts, validateArtifact} from './discovery-lab-artifacts.mjs';
import {DEFAULT_CHARTER, runCampaign} from './discovery-lab.mjs';
import {BINDING_KEYS, STAGES, canonical} from './discovery-lab-contract.mjs';
const bindings = {missionId: 'capability-00000000-0000-4000-8000-000000000000', revision: 1,
    purposeDigest: '1'.repeat(64), charterDigest: '2'.repeat(64), modelDigest: '3'.repeat(64),
    sourceDigest: '4'.repeat(64), evaluatorDigest: '5'.repeat(64)};
test('six strict versioned artifacts bind one mission, all executable data, costs and predecessor digests', async () => {
    const result = runCampaign(DEFAULT_CHARTER), artifacts = await makeArtifacts(bindings, result);
    assert.deepEqual(artifacts.map(item => item.kind), STAGES);
    for (const [index, artifact] of artifacts.entries()) {
        assert.equal(artifact.schema, 'discovery-lab-artifact/v1');
        assert.equal(artifact.executionMode, 'synthetic-local');
        assert.deepEqual(artifact.inputArtifacts, artifacts.slice(0, index).map(item => item.digest));
        assert.deepEqual(artifact.payload.program, result.stages[index].program);
        for (const key of BINDING_KEYS) assert.equal(artifact[key], bindings[key]);
        assert.deepEqual(await validateArtifact(JSON.parse(canonical(artifact))), artifact);
    }
});
test('artifact substitution, unsupported fields, omitted programs and future dependencies fail closed', async () => {
    const artifact = (await makeArtifacts(bindings, runCampaign(DEFAULT_CHARTER)))[1];
    for (const change of [item => { item.revision++; }, item => { item.kind = 'learn'; },
        item => { item.authority = true; }, item => { delete item.payload.program; },
        item => { item.payload.program = null; }, item => { item.inputArtifacts = []; },
        item => { item.dependencies = ['evolve']; }]) {
        const altered = JSON.parse(canonical(artifact)); change(altered);
        await assert.rejects(validateArtifact(altered));
    }
});
