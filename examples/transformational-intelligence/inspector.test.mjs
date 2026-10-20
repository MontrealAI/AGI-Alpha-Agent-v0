// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {assertPublicContent, inspectTransformationEnvelope} from './inspector.mjs';

const fixture = JSON.parse(await readFile(process.env.TI_NATIVE_CAMPAIGN
    || fileURLToPath(new URL('./campaign.json', import.meta.url)), 'utf8'));
const clone = () => structuredClone(fixture);

test('actual native complete campaign roundtrips exactly without authority', async () => {
    const checked = await inspectTransformationEnvelope(JSON.stringify(fixture));
    assert.deepEqual(JSON.parse(JSON.stringify(checked)), fixture);
    assert.equal(checked.review.independent, false);
    assert.equal(checked.authorization.binding, null);
    assert.equal(checked.charter.budgets.USDCBaseUnits, '0');
    assert.equal(checked.charter.budgets.AGIALPHABaseUnits, '0');
    assert.equal(checked.result.means_millionths.candidate, checked.result.means_millionths['unrestricted-exact-search']);
});

test('forged source-to-outcome result scores and program identities reject', async () => {
    for (const mutate of [
        e => { e.result.observed_gain_vs_incumbent = 999999; },
        e => { e.result.means_millionths.candidate = 999999; },
        e => { e.result.results = {}; },
        e => { e.result.results.candidate[0].program_digest = '0'.repeat(64); },
        e => { e.result.beats_unrestricted = true; },
        e => { e.result.costs.paid_calls = 1; },
        e => { e.result.independent_review = 'accepted'; },
    ]) {
        const changed = clone(); mutate(changed);
        await assert.rejects(inspectTransformationEnvelope(changed));
    }
});

test('stale bindings purpose substitution and imported authority reject', async () => {
    for (const mutate of [
        e => { e.charter.purpose = 'Publish a different goal'; },
        e => { e.charter.budgets.USDCBaseUnits = '1000000'; },
        e => { e.authorization.binding = e.bindings_digest; },
        e => { e.review.independent = 1; },
        e => { e.charter.publicOnly = 1; },
        e => { e.evaluation.epoch = true; },
        e => { e.settlement.transaction_prepared = true; },
    ]) {
        const changed = clone(); mutate(changed);
        await assert.rejects(inspectTransformationEnvelope(changed));
    }
});

test('malformed frozen phase evidence and parser ambiguity reject', async () => {
    for (const mutate of [
        e => { e.freeze.journal_predecessor = 'unverified'; },
        e => { e.freeze.journal_revision = 'unverified'; },
        e => { e.result = null; },
        e => { e.phase = 'frozen'; e.freeze = null; e.result = null; },
        e => { e.phase = 'queued'; e.result = null; },
        e => { delete e.result.fresh_sources[0].schema_version; },
    ]) {
        const changed = clone(); mutate(changed);
        await assert.rejects(inspectTransformationEnvelope(changed));
    }
    await assert.rejects(inspectTransformationEnvelope('{"schema":"v1","schema":"v2"}'));
    await assert.rejects(inspectTransformationEnvelope('{"number":1e100}'));
});

test('decoded and quoted credential-shaped content rejects before retention', () => {
    for (const content of [{configuration: {api_key: 'synthetic-fixture-only'}},
        {claims: [{text: '{"api_key":"synthetic-fixture-only"}'}]},
        {deep: [{accessToken: 'synthetic-fixture-only'}]},
        '{"secret":"synthetic-fixture-only"}', '{"api\\u005fkey":"synthetic-fixture-only"}',
        {configuration: {'api%5Fkey': 'synthetic-fixture-only'}},
        JSON.stringify({text: JSON.stringify({api_key: 'synthetic-fixture-only'})})]) {
        assert.throws(() => assertPublicContent(content), /credential-shaped/);
    }
    assert.doesNotThrow(() => assertPublicContent({schema: fixture.schema, authorization: fixture.authorization}));
    for (const key of ['x-api-key', 'x-auth-token', 'proxy-authorization', 'aws_secret_access_key']) {
        assert.throws(() => assertPublicContent({configuration: {[key]: 'synthetic-fixture-only'}}), /credential-shaped/);
    }
    assert.doesNotThrow(() => assertPublicContent({max_tokens: 1200, computational_tokens: 'public discussion'}));
    assert.doesNotThrow(() => assertPublicContent(JSON.stringify(fixture)));
    assert.doesNotThrow(() => assertPublicContent({raw: JSON.stringify({raw: JSON.stringify(fixture)})}));
    for (const value of [{value:'synthetic-fixture-only'}, ['synthetic-fixture-only'], true, false, 1, 0]) {
        for (const key of ['api_key','x-api-key','authorization']) {
            assert.throws(() => assertPublicContent({[key]:value}), /credential-shaped/);
            assert.throws(() => assertPublicContent({text:JSON.stringify({[key]:value})}), /credential-shaped/);
        }
    }
});
