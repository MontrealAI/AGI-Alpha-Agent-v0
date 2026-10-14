// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {compilePlan} from '../../docs/assets/nova-studio/plan.mjs';
import {preparePackage} from '../../docs/assets/nova-studio/package.mjs';
import {PinataStorage, publishPackage, verifyPublication, importPublication, artifactURI, UPLOAD_ENDPOINT}
  from '../../docs/assets/nova-studio/storage.mjs';

const pkg = await preparePackage({
  genome: {schema: 'agialpha.novaseed.genome.v1', note: 'Only encrypted'},
  plan: compilePlan([{goal: 'Public job', successMetric: 'Reproducible result', bounty: '100', duration: 100, priceWeight: 0}]),
  passphrase: 'a private testing capsule passphrase', evidence: {summary: 'Public proof'},
  profile: {chainId: 31337, profile: 'fixture-only', contracts: {Seed: {address: '0x' + '11'.repeat(20)}}},
});
function fixture() {
  const objects = new Map(), calls = [], credential = 'SESSION_ONLY_CREDENTIAL';
  const fetchImpl = async (url, options) => {
    calls.push({url, options});
    assert.equal(options.redirect, 'error'); assert.equal(options.credentials, 'omit');
    if (url === UPLOAD_ENDPOINT) {
      assert.equal(options.headers.Authorization, `Bearer ${credential}`);
      assert.equal(options.body.get('network'), 'public');
      const bytes = await options.body.get('file').text();
      const digest = createHash('sha256').update(bytes).digest('hex');
      const cid = 'b' + [...digest].map(digit => 'abcdefghijklmnop'[parseInt(digit, 16)]).join('');
      objects.set(cid, bytes);
      return new Response(JSON.stringify({data: {cid}}), {headers: {'content-type': 'application/json'}});
    }
    assert.equal(options.headers.Authorization, undefined);
    const value = objects.get(url.split('/').at(-1));
    return new Response(value || 'missing', {status: value ? 200 : 404});
  };
  const adapter = new PinataStorage({token: credential, fetchImpl});
  return {adapter, objects, calls, credential};
}
test('production adapter performs upload, exact readback and existing-URI import on fixture transport', async () => {
  const f = fixture();
  await assert.rejects(publishPackage(pkg, {adapter: f.adapter, name: 'Public project'}), /confirm/);
  const published = await publishPackage(pkg, {adapter: f.adapter, name: 'Public project', description: 'Public summary', disclosureAccepted: true});
  assert.equal(f.calls.filter(call => call.options.method === 'POST').length, 3);
  assert.equal(published.metadata.plan.root, pkg.plan.planRoot);
  assert.equal(published.metadata.capsule.hash, pkg.commitments.capsuleHash);
  assert.equal(published.metadata.chainId, 31337);
  const imported = await importPublication(pkg, published.metadataURI, {adapter: f.adapter});
  assert.equal(imported.metadataURI, published.metadataURI);
  assert.equal(JSON.stringify(published).includes(f.credential), false);
  assert.equal(JSON.stringify(f.adapter).includes(f.credential), false);
  f.adapter.clearCredentials();
  await assert.rejects(f.adapter.uploadJSON({test: true}), /credential/);
  await verifyPublication(pkg, published, {adapter: f.adapter});
});
test('changed/missing bytes or mixed-network metadata cannot enable a package', async () => {
  const f = fixture();
  const published = await publishPackage(pkg, {adapter: f.adapter, name: 'Public project', disclosureAccepted: true});
  const cid = published.capsuleURI.slice(7), original = f.objects.get(cid);
  f.objects.set(cid, original + '\n');
  await assert.rejects(verifyPublication(pkg, published, {adapter: f.adapter}), /commitments/);
  f.objects.set(cid, original); f.objects.delete(published.evidenceURI.slice(7));
  await assert.rejects(verifyPublication(pkg, published, {adapter: f.adapter}), /Storage/);
  const changed = structuredClone(published); changed.metadata.chainId = 1;
  await assert.rejects(verifyPublication(pkg, changed, {adapter: f.adapter}), /exact capsule/);
});
test('URI policy denies arbitrary origins, query secrets, traversal, data and placeholders', () => {
  const cid = 'b' + 'a'.repeat(52);
  assert.equal(artifactURI(`https://ipfs.io/ipfs/${cid}`).uri, `ipfs://${cid}`);
  for (const uri of ['', 'ipfs://YOUR_CID', `ipfs://${cid}/../x`, `ipfs://${cid}/x`, 'data:application/json,{}',
    `https://evil.example/ipfs/${cid}`, `https://gateway.pinata.cloud.evil.example/ipfs/${cid}`,
    `https://user:password@gateway.pinata.cloud/ipfs/${cid}`, `https://gateway.pinata.cloud/ipfs/${cid}?token=secret`,
    `https://ipfs.io/ipfs/${cid}#fragment`, 'javascript:alert(1)']) assert.throws(() => artifactURI(uri));
});
test('browser fetch keeps its global receiver rather than the adapter instance', async () => {
  const adapter = new PinataStorage({fetchImpl: function () {
    assert.equal(this, globalThis);
    return Promise.resolve(new Response('{"public":true}'));
  }});
  const result = await adapter.readJSON('ipfs://b' + 'a'.repeat(52));
  assert.deepEqual(result.value, {public: true});
});
test('redirects, oversized streams, duplicate keys and provider credential errors are rejected', async () => {
  const cid = 'b' + 'a'.repeat(52), uri = `ipfs://${cid}`;
  const cases = [async () => new Response('x'.repeat(250001)), async () => new Response('{"a":1,"a":2}'),
    async () => ({ok: true, redirected: true}), async () => { throw Error('secret credential echo'); },
    async () => new Response(new Uint8Array([0xc0, 0xaf]))];
  for (const fetchImpl of cases) {
    const adapter = new PinataStorage({fetchImpl});
    await assert.rejects(adapter.readJSON(uri), error => !error.message.includes('secret credential echo'));
  }
});
