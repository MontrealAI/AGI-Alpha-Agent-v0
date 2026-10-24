// SPDX-License-Identifier: Apache-2.0
// Admission-only cases. No repository bridge, native worker or EVM is started.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { solve } from '../enterprise/compiler.mjs';
import { flatControl, diamondBOM, diamondImpact } from '../enterprise/development-cases.mjs';
import { checkArtifact } from '../evaluation/checker.mjs';
import { artifactFor, externalAdmission } from './artifact.mjs';
import { canonicalBytes, prepareDelivery, proofHash, createMissionDelivery } from './mission-delivery.mjs';

const criteria = readFileSync(new URL('../evaluation/criteria.json', import.meta.url));
const admit = externalAdmission(checkArtifact, criteria);
const routes = [
  ['flat-reduction in a fresh workspace', flatControl, {}],
  ['weighted direct specialist in a fresh workspace', diamondBOM, { variant: 'direct-specialist' }],
  ['Boolean direct specialist in a fresh workspace', diamondImpact, { variant: 'direct-specialist' }]
];

for (const [label, mission, options] of routes) {
  test(label + ' receives a fresh accepted source-bound artifact', async () => {
    const result = solve(mission, options);
    assert.equal(result.status, 'complete');
    assert.equal(result.delivery.status, 'ready');
    assert.equal(result.capability, null);
    const prepared = prepareDelivery(mission, result);
    const artifact = artifactFor(mission, result);
    const proof = checkArtifact(canonicalBytes(artifact), canonicalBytes(mission), criteria);
    assert.equal(artifact.capabilityHash, result.sources.rootSha256);
    assert.equal(prepared.binding.capabilityId, result.sources.rootSha256);
    assert.equal(prepared.binding.capabilityManifestSha256, null);
    assert.equal(proof.accepted, true);
    assert.equal(proof.capabilityHash, prepared.binding.capabilityId);
    assert.equal((await admit(mission, result)).accepted, true);
    assert.equal(result.currentProof, null);
    assert.deepEqual(result.authority, []);
  });
}

test('a constructed capability retains its real definition identity', () => {
  const result = solve(diamondBOM);
  const prepared = prepareDelivery(diamondBOM, result);
  const artifact = artifactFor(diamondBOM, result);
  assert.equal(prepared.binding.capabilityId, result.capability.id);
  assert.equal(artifact.capabilityHash, result.capability.id);
  assert.notEqual(artifact.capabilityHash, result.sources.rootSha256);
  assert.match(prepared.binding.capabilityManifestSha256, /^[a-f0-9]{64}$/);
});

test('capability-free fallback refuses a changed or missing source catalogue identity', () => {
  const original = solve(flatControl);
  for (const mutate of [
    result => { result.sources.rootSha256 = '0'.repeat(64); },
    result => { result.sources.installedCatalog[0].bytes += 1; },
    result => { result.sources = null; }
  ]) {
    const result = structuredClone(original);
    mutate(result);
    assert.throws(() => prepareDelivery(flatControl, result), { code: 'SOURCE_CATALOG_BINDING' });
    assert.throws(() => artifactFor(flatControl, result), { code: 'SOURCE_CATALOG_BINDING' });
  }
});

test('source fallback proof rebinding is refused before any native bridge load', async () => {
  for (const [, mission, options] of routes) {
    const result = solve(mission, options);
    const delivery = createMissionDelivery({ repositories: {}, check: async (...args) => {
      const accepted = await admit(...args);
      return { ...accepted, proof: { ...accepted.proof, capabilityHash: '0'.repeat(64) } };
    } });
    await assert.rejects(delivery.deliver(mission, result), { code: 'PROOF_BINDING' });
    assert.equal(delivery.statistics().completed, 0);
  }
});

test('matching fallback proof passes its binding guard before the later output guard', async () => {
  const result = solve(flatControl);
  const delivery = createMissionDelivery({ repositories: {}, check: async (...args) => {
    const accepted = await admit(...args);
    assert.equal(accepted.accepted, true);
    const artifact = { ...accepted.artifact, output: { ...accepted.artifact.output, total: accepted.artifact.output.total + 1 } };
    return { ...accepted, artifact, proof: { ...accepted.proof, artifactSha256: proofHash(artifact) } };
  } });
  await assert.rejects(delivery.deliver(flatControl, result), { code: 'ARTIFACT_OUTPUT_BINDING' });
});

test('fallback and constructed paths retain candidate proof, authority and capability checks', () => {
  const flat = solve(flatControl);
  assert.throws(() => artifactFor(flatControl, { ...flat, currentProof: { accepted: true } }), { code: 'CANDIDATE_AUTHORITY' });
  assert.throws(() => artifactFor(flatControl, { ...flat, authority: ['execute'] }), { code: 'CANDIDATE_AUTHORITY' });
  const structured = solve(diamondBOM);
  assert.throws(() => artifactFor(diamondBOM, { ...structured, capability: { ...structured.capability, id: '0'.repeat(64) } }), { code: 'CAPABILITY_BINDING' });
});
