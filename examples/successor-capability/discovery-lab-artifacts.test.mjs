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

test('validation returns the owned artifact snapshot despite post-digest caller mutation', async () => {
    const artifact = (await makeArtifacts(bindings, runCampaign(DEFAULT_CHARTER)))[0];
    const expected = structuredClone(artifact);
    const pending = validateArtifact(artifact);
    artifact.scope = {forged: true};
    artifact.payload.scope = {forged: true};
    artifact.payload.program.queryRows[0].interval[0]++;
    artifact.digest = '0'.repeat(64);
    assert.deepEqual(await pending, expected);
});

test('artifact construction owns all campaign stages before the first asynchronous digest', async () => {
    const result = runCampaign(DEFAULT_CHARTER);
    const expected = await makeArtifacts(bindings, result);
    const pending = makeArtifacts(bindings, result);
    result.stages[1].scope = {forged: true};
    result.stages[1].program = null;
    result.invalidations.changed.push('forged');
    assert.deepEqual(await pending, expected);
});

for (const [name, change] of [
    ['scope', input => { input.scope = {callerChanged: true}; }],
    ['payload', input => { input.payload.program = {callerChanged: true}; }],
    ['costs', input => { input.costs.search++; }]
]) {
    test(`artifact validation retains the committed ${name} snapshot across hashing`, async () => {
        const original = (await makeArtifacts(bindings, runCampaign(DEFAULT_CHARTER)))[0];
        const input = JSON.parse(canonical(original)), pending = validateArtifact(input);
        change(input);
        const validated = await pending;
        assert.deepEqual(validated, original);
        assert.notEqual(validated, input);
        assert.deepEqual(await validateArtifact(validated), original);
    });
}

test('artifact validation uses descriptor values without rereading caller properties', async () => {
    const original = (await makeArtifacts(bindings, runCampaign(DEFAULT_CHARTER)))[0];
    let reads = 0;
    const input = new Proxy(original, {get() { reads++; throw Error('Caller property was reread'); }});
    assert.deepEqual(await validateArtifact(input), original);
    assert.equal(reads, 0);
});

test('an unknown artifact field in the first captured frame cannot disappear before validation', async () => {
    const original = (await makeArtifacts(bindings, runCampaign(DEFAULT_CHARTER)))[0];
    let scans = 0;
    const input = new Proxy({...original, authority: true}, {
        ownKeys(value) {
            return ++scans === 1 ? Reflect.ownKeys(value) : Reflect.ownKeys(value).filter(key => key !== 'authority');
        }
    });
    await assert.rejects(validateArtifact(input), /Unsupported versioned Discovery Lab artifact/);
    assert.equal(scans, 1);
});

for (const [name, change] of [
    ['stage', input => { input.stages[5] = {...input.stages[5], reason: 'caller changed'}; }],
    ['scope', input => { input.stages[0].scope = {callerChanged: true}; }],
    ['costs', input => { input.stages[4].cost.search++; }],
    ['invalidations', input => {
        input.invalidations = {changed: ['memory'], earliest: 'think', invalidated: STAGES.slice(1)};
    }]
]) {
    test(`all six artifacts retain one campaign snapshot when caller ${name} changes during hashing`, async () => {
        const original = runCampaign(DEFAULT_CHARTER), expected = await makeArtifacts(bindings, original);
        const input = JSON.parse(canonical(original)), pending = makeArtifacts(bindings, input);
        change(input);
        const artifacts = await pending;
        assert.deepEqual(artifacts, expected);
        for (const artifact of artifacts) assert.deepEqual(await validateArtifact(artifact), artifact);
    });
}

test('artifact construction uses captured campaign fields without original property reads', async () => {
    const original = runCampaign(DEFAULT_CHARTER), expected = await makeArtifacts(bindings, original);
    let reads = 0;
    const input = new Proxy(original, {get() { reads++; throw Error('Caller campaign property was reread'); }});
    assert.deepEqual(await makeArtifacts(bindings, input), expected);
    assert.equal(reads, 0);
});

test('artifact construction rejects an unsupported campaign schema from the first captured frame', async () => {
    const original = runCampaign(DEFAULT_CHARTER);
    const input = new Proxy({...original, schema: 'unsupported-campaign/v1'}, {
        get(value, key) { return key === 'schema' ? original.schema : Reflect.get(value, key); }
    });
    await assert.rejects(makeArtifacts(bindings, input), /All six ordered campaign artifacts are required/);
});
