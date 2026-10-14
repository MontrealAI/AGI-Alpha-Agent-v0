// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {compilePlan} from '../../docs/assets/nova-studio/plan.mjs';
import {canonicalJSON, hashObject, sealSeed, openSeed} from '../../docs/assets/ascension/crypto.mjs';
import {deploymentDescriptor} from '../../docs/assets/ascension-wallet/client.mjs';
import {preparePackage, verifyPackage, createRecoveryKit, restoreRecoveryKit, parseBoundedJSON,
  canonicalEnvelope, byteDigest, isRecoveryVerified, clearRecoveryState, convertLegacyCapsule,
  MAX_KIT_BYTES} from '../../docs/assets/nova-studio/package.mjs';
const passphrase = 'a private capsule test phrase outside every export';
const profile = {chainId: 31337, profile: 'test-only-profile', contracts: {Seed: {address: '0x' + '11'.repeat(20)}}};
const spec = {goal: 'Check a public fixture', successMetric: 'The result equals 42', bounty: '100', duration: 3600, priceWeight: 5000};
const plan = compilePlan([spec]);
const genome = {schema: 'agialpha.novaseed.genome.v1', name: 'private project', privateNotes: 'encrypted only'};
const evidence = {schema: 'agialpha.novaseed.evidence.v1', summary: 'Public evidence only'};
const prepare = (overrides = {}) => preparePackage({genome, plan, passphrase, profile, evidence, ...overrides});
const initial = await prepare();

test('exact plan is inside the existing capsule; commitment meanings remain distinct', async () => {
  const opened = await openSeed(initial.capsule, passphrase);
  assert.deepEqual(opened, {...genome, onchain_plan: plan});
  assert.equal(initial.commitments.capsuleHash, '0x' + await hashObject(initial.capsule));
  assert.equal(initial.commitments.innerCommitment, '0x' + initial.capsule.commitment);
  assert.notEqual(initial.commitments.capsuleHash, initial.commitments.innerCommitment);
  assert.equal(initial.commitments.capsuleByteDigest, await byteDigest(canonicalJSON(initial.capsule)));
  assert.notEqual(initial.commitments.capsuleByteDigest, await byteDigest(JSON.stringify(initial.capsule, null, 2)));
  assert.equal(initial.commitments.evidenceHash, '0x' + await hashObject(evidence));
  assert.equal(initial.commitments.planRoot, plan.planRoot);
  assert.equal(initial.commitments.profileHash, '0x' + await hashObject(deploymentDescriptor(profile)));
  assert.equal(Object.isFrozen(initial.plan.jobs[0].spec), true);
  assert.equal(JSON.stringify(initial).includes(genome.privateNotes), false);
});
test('qualification renewal preserves artifact deployment identity, while address changes do not', async () => {
  const renewed = structuredClone(initial);
  renewed.profile = {...renewed.profile, stage: 'public', validUntil: '1900000000',
    qualification: {schema: 'fixture-v1', digest: 'updated-evidence'}};
  await verifyPackage(renewed);
  assert.equal('0x' + await hashObject(deploymentDescriptor(renewed.profile)), initial.commitments.profileHash);
  renewed.profile.contracts.Seed.address = '0x' + '22'.repeat(20);
  await assert.rejects(verifyPackage(renewed), /deployment/);
});
test('recovery proof binds capsule, plan, profile and evidence; serialized flags cannot authorize', async () => {
  clearRecoveryState();
  const imported = JSON.parse(JSON.stringify(initial));
  await verifyPackage(imported);
  assert.equal(isRecoveryVerified(imported), false);
  await verifyPackage(imported, {passphrase});
  assert.equal(isRecoveryVerified(imported), true);
  const forged = structuredClone(imported);
  forged.plan = compilePlan([{...spec, goal: 'different valid job'}]);
  forged.commitments.planRoot = forged.plan.planRoot;
  await verifyPackage(forged);
  assert.equal(isRecoveryVerified(forged), false);
  await assert.rejects(verifyPackage(forged, {passphrase}), /exact FusionPlan/);
  const changedEvidence = structuredClone(imported);
  changedEvidence.evidence.summary = 'changed';
  changedEvidence.commitments.evidenceHash = '0x' + await hashObject(changedEvidence.evidence);
  await verifyPackage(changedEvidence);
  assert.equal(isRecoveryVerified(changedEvidence), false);
});
test('randomized sealing, wrong passphrase and tampering', async () => {
  const another = await prepare();
  assert.notEqual(another.commitments.capsuleHash, initial.commitments.capsuleHash);
  await assert.rejects(verifyPackage(initial, {passphrase: 'this is the wrong passphrase'}), /Could not open/);
  const changed = structuredClone(initial); changed.capsule.ciphertext = 'AAAA';
  await assert.rejects(verifyPackage(changed), /field length/);
  const altered = structuredClone(initial); altered.capsule.iv = 'AQEBAQEBAQEBAQEB';
  await assert.rejects(verifyPackage(altered), /commitments/);
});
test('private recovery kit is portable, checksummed and never contains passphrase or plaintext genome', async () => {
  await verifyPackage(initial, {passphrase});
  await assert.rejects(createRecoveryKit(initial), /plaintext plan/);
  const kit = await createRecoveryKit(initial, {disclosureAccepted: true, ids: {seed: '7'}});
  const serialized = canonicalEnvelope(kit);
  assert.equal(serialized.includes(passphrase), false);
  assert.equal(serialized.includes(genome.privateNotes), false);
  assert.equal(serialized.includes(spec.goal), true);
  clearRecoveryState();
  const withoutSecret = await restoreRecoveryKit(serialized);
  assert.equal(withoutSecret.recoveryVerified, false);
  const restored = await restoreRecoveryKit(serialized, {passphrase});
  assert.equal(restored.recoveryVerified, true);
  assert.equal(restored.needsLiveReconciliation, true);
  assert.deepEqual(restored.package.capsule, initial.capsule);
  assert.deepEqual(restored.package.plan, plan);
  const changed = structuredClone(kit); changed.content.ids.seed = '8';
  await assert.rejects(restoreRecoveryKit(changed), /checksum/);
  await assert.rejects(createRecoveryKit(initial, {disclosureAccepted: true, journal: {passphrase}}), /secrets/);
});
test('legacy capsule conversion preserves original, adds exact plan before resealing', async () => {
  const old = await sealSeed(genome, passphrase);
  const converted = await convertLegacyCapsule(old, passphrase, {plan, evidence, profile});
  assert.deepEqual(converted.original, old);
  assert.deepEqual(await openSeed(old, passphrase), genome);
  assert.deepEqual((await openSeed(converted.package.capsule, passphrase)).onchain_plan, plan);
  await assert.rejects(convertLegacyCapsule(initial.capsule, passphrase, {plan, evidence, profile}), /already contains/);
});
test('128 short jobs seal/reopen; excessive text including ciphertext overhead rejects early', async () => {
  const maximum = compilePlan(Array.from({length: 128}, () => spec));
  const prepared = await prepare({plan: maximum});
  assert.equal((await openSeed(prepared.capsule, passphrase)).onchain_plan.jobs.length, 128);
  assert.ok(canonicalEnvelope(await createRecoveryKit(prepared, {disclosureAccepted: true})).length < MAX_KIT_BYTES);
  const oversized = compilePlan(Array.from({length: 128}, () => ({...spec, goal: 'é'.repeat(256), successMetric: 'é'.repeat(256)})));
  await assert.rejects(prepare({plan: oversized}), /250 KB capsule limit/);
});
test('imports reject duplicate escaped keys, polluted keys, unsafe numbers, malformed Unicode and nesting', () => {
  for (const value of ['{"a":1,"a":2}', '{"a":1,"\\u0061":2}', '{"__proto__":{}}', '{"constructor":{}}',
    '{"a":1e999}', '{"a":9007199254740993}', '{"a":"\\ud800"}', '{"a":1,}', '[1,]', 'true false',
    '['.repeat(26) + '0' + ']'.repeat(26)]) assert.throws(() => parseBoundedJSON(value));
  assert.throws(() => parseBoundedJSON('"' + 'é'.repeat(130000) + '"'), /byte limit/);
  assert.deepEqual(parseBoundedJSON(' {"a": [1, false, null, "é🚀"]} '), {a: [1, false, null, 'é🚀']});
});
test('native-only parsing can preserve oversized integer lexemes without rounding or changing signature bytes', () => {
  const source = '{"time_ns":1800000000000000001,"index":0}';
  assert.throws(() => parseBoundedJSON(source), /exact/);
  assert.deepEqual(parseBoundedJSON(source, {preserveUnsafeIntegers: true}),
    {time_ns: '1800000000000000001', index: 0});
  for (const number of ['1e99', '9007199254740993.0', '1e999'])
    assert.throws(() => parseBoundedJSON('{"value":' + number + '}', {preserveUnsafeIntegers: true}));
});
test('vendored ethers is the unmodified locked 6.17.0 ES module', () => {
  const data = readFileSync(new URL('../../docs/assets/nova-studio/vendor/ethers-6.17.0.min.mjs', import.meta.url));
  assert.equal(createHash('sha256').update(data).digest('hex'), 'b016b0c3898c78fd8156466eb1ff1f42c9df951c2f0d64c9bdf799fe745b0a6c');
  assert.deepEqual(data, readFileSync(new URL('../contracts/node_modules/ethers/dist/ethers.min.js', import.meta.url)));
});
