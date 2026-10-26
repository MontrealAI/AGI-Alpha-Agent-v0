// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp, writeFile, readFile, mkdir, cp, symlink, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadFoundations, admitCatalogue, assessReuse, createSelector} from '../src/admission/bridge.mjs';
import {createAdmittedWorkbench} from '../src/admission/workbench.mjs';

const scratch = resolve(fileURLToPath(new URL('../../../../', import.meta.url)));
const foundationDirectory = process.env.AGI_DISCOVERY_FOUNDATIONS || join(scratch, 'research-inputs/graph-foundations');
const foundations = await loadFoundations(foundationDirectory);
const hash = data => createHash('sha256').update(data).digest('hex');
const work = await mkdtemp(join(tmpdir(), 'agi-work-admission-'));
const root = join(work, 'artifacts');
await mkdir(root);
const descriptors = {};
for (const [name, text] of Object.entries({
  'index.mjs': 'export const indexFormat = 1;\n',
  'witness.mjs': 'export const witnessFormat = 1;\n',
  'index-check.json': '{"accepted":true,"scope":"index"}\n',
  'witness-check.json': '{"accepted":true,"scope":"witness"}\n',
  'composition-check.json': '{"accepted":true,"scope":"composition"}\n',
})) {
  await writeFile(join(root, name), text);
  descriptors[name] = {path: name, bytes: Buffer.byteLength(text), sha256: hash(text)};
}
const catalogue = {
  schema: 'agi-alpha.work-discovery-catalogue.v1', mode: 'FIXTURE_ONLY', graphId: 'unit-control-graph',
  policy: {id: 'finite-test-policy', version: 1}, environment: {node: process.versions.node},
  rights: {license: 'Apache-2.0', class: 'synthetic'},
  skills: [
    {id: 'contract-index', version: '1', creator: 'fixture:creator-a', scope: {family: 'index', finite: true},
      implementationFiles: [descriptors['index.mjs']], evidenceFiles: [descriptors['index-check.json']],
      compositionEvidenceFiles: [], dependencies: [], expiresAt: 700},
    {id: 'compatibility-witness', version: '1', creator: 'fixture:creator-b', scope: {family: 'witness', finite: true},
      implementationFiles: [descriptors['witness.mjs']], evidenceFiles: [descriptors['witness-check.json']],
      compositionEvidenceFiles: [descriptors['composition-check.json']], dependencies: ['contract-index@1'], expiresAt: 700},
  ], edges: [{from: 'contract-index@1', to: 'compatibility-witness@1', kind: 'requires'}],
};
async function verifyEvidence({skill, binding, files}) {
  const accepted = skill.evidenceFiles.every(file => JSON.parse(files.get(file.path)).accepted === true);
  const compositionAccepted = skill.compositionEvidenceFiles.every(file => JSON.parse(files.get(file.path)).accepted === true);
  return {accepted, compositionAccepted, validatorId: 'unit-fixture-verifier',
    scopeDigest: binding.scopeDigest, implementationDigest: binding.implementationDigest};
}
const make = (changes = {}) => admitCatalogue({catalogue, foundations, artifactRoot: root, verifyEvidence, ...changes});
const admission = await make();
const reuse = (changes = {}) => assessReuse({admission, foundations, artifactRoot: root, ...changes});

test.after(async () => {await rm(work, {recursive: true});});

test('actual inherited primitives produce explicit fixture-only admission', async () => {
  assert.equal(admission.assessments.length, 2);
  assert.equal(admission.rootAssessment.ok, true);
  assert.equal(admission.liveIdentityEnforcement, 'NOT_RUN');
  assert.equal(admission.cryptographicAuthentication, false);
  assert.deepEqual(admission.executionAuthority, []);
  assert.equal(admission.settlement, 'NOT_CONNECTED');
  assert.equal((await reuse()).ok, true);
});

test('creator, validator grant and root grant are separate recorded roles', () => {
  assert.equal(admission.skills[0].creator, 'fixture:creator-a');
  assert.equal(admission.attestations[0].agent, 'research.agent.agi.eth');
  assert.equal(admission.attestations[0].signer, 'fixture:attestation-delegate');
  assert.equal(admission.root.signer, 'fixture:root-delegate');
  assert.equal(admission.rootAssessment.authorizedOperation, 'COMMIT_GRAPH_ROOT');
});

test('equally informed indexed registry and graph choose identical dependency plan', () => {
  const registry = createSelector(admission, foundations, 'registry')(['compatibility-witness@1']);
  const graph = createSelector(admission, foundations, 'graph')(['compatibility-witness@1']);
  assert.deepEqual(registry.selected, ['contract-index@1', 'compatibility-witness@1']);
  assert.deepEqual(registry.selected, graph.selected);
  assert.equal(registry.informationDigest, graph.informationDigest);
  assert.equal(registry.inspectedSkills, graph.inspectedSkills);
});

test('selection does not silently invent unsupported skills', () => {
  assert.throws(() => createSelector(admission, foundations)(['unseen@1']), /UNSUPPORTED_SKILL/);
});

test('separate composition evidence is mandatory', async () => {
  const changed = structuredClone(catalogue); changed.skills[1].compositionEvidenceFiles = [];
  await assert.rejects(make({catalogue: changed}), /COMPOSITION_EVIDENCE_REQUIRED/);
});

test('component acceptance alone cannot establish composition acceptance', async () => {
  await assert.rejects(make({verifyEvidence: async values => ({...await verifyEvidence(values), compositionAccepted: false})}),
    /COMPOSITION_NOT_VALIDATED/);
});

test('installed technical verifier must run and bind the source and scope', async () => {
  await assert.rejects(make({verifyEvidence: null}), /INSTALLED_EVIDENCE_VERIFIER_REQUIRED/);
  await assert.rejects(make({verifyEvidence: async values => ({...await verifyEvidence(values), scopeDigest: '0'.repeat(64)})}),
    /TECHNICAL_VERDICT_BINDING_MISMATCH/);
  await assert.rejects(make({verifyEvidence: async () => ({accepted: false})}), /TECHNICAL_EVIDENCE_NOT_ACCEPTED/);
});

test('live mode cannot accept any fixture', async () => {
  await assert.rejects(make({catalogue: {...catalogue, mode: 'LIVE'}}), /LIVE_IDENTITY_ENFORCEMENT_NOT_RUN/);
});

test('file drift is rejected on current reuse', async () => {
  const copy = join(work, 'changed'); await cp(root, copy, {recursive: true});
  await writeFile(join(copy, 'index.mjs'), 'wrong\n');
  await assert.rejects(reuse({artifactRoot: copy}), /FILE_SIZE_MISMATCH|FILE_DIGEST_MISMATCH/);
});

test('same-length source tampering is rejected by digest', async () => {
  const copy = join(work, 'same-size'); await cp(root, copy, {recursive: true});
  const source = await readFile(join(copy, 'index.mjs'), 'utf8');
  await writeFile(join(copy, 'index.mjs'), source.replace('1', '2'));
  await assert.rejects(reuse({artifactRoot: copy}), /FILE_DIGEST_MISMATCH/);
});

test('missing evidence cannot retain admission', async () => {
  const copy = join(work, 'missing'); await cp(root, copy, {recursive: true});
  await rm(join(copy, 'witness-check.json'));
  await assert.rejects(reuse({artifactRoot: copy}), /ENOENT/);
});

test('symlink and traversal manifests cannot leave the artifact root', async () => {
  const linked = join(work, 'linked'); await cp(root, linked, {recursive: true});
  await rm(join(linked, 'index.mjs')); await symlink(join(root, 'index.mjs'), join(linked, 'index.mjs'));
  await assert.rejects(reuse({artifactRoot: linked}), /SYMLINK_REFUSED/);
  const changed = structuredClone(catalogue); changed.skills[0].implementationFiles[0].path = '../index.mjs';
  await assert.rejects(make({catalogue: changed}), /UNSAFE_FILE_PATH/);
});

test('unknown dependency, altered edge information and cycles fail closed', async () => {
  const missing = structuredClone(catalogue); missing.skills[1].dependencies = ['missing@1'];
  await assert.rejects(make({catalogue: missing}), /UNKNOWN_DEPENDENCY/);
  await assert.rejects(make({catalogue: {...catalogue, edges: []}}), /EDGE_DEPENDENCY_MISMATCH/);
  const cycle = structuredClone(catalogue);
  cycle.skills[0].dependencies = ['compatibility-witness@1'];
  cycle.skills[0].compositionEvidenceFiles = [descriptors['composition-check.json']];
  cycle.edges.push({from: 'compatibility-witness@1', to: 'contract-index@1', kind: 'requires'});
  await assert.rejects(make({catalogue: cycle}), /DEPENDENCY_CYCLE/);
});

test('revocation preserves historical attestation while blocking future reuse', async () => {
  const result = await reuse({revokedSkills: ['contract-index@1']});
  assert.equal(result.ok, false); assert.equal(result.skills[0].historyValid, true);
  assert.ok(result.skills[0].reasons.includes('SKILL_REVOKED'));
});

test('supersession and expiry cannot inherit current permission', async () => {
  assert.equal((await reuse({supersededSkills: ['compatibility-witness@1']})).ok, false);
  const expired = await reuse({now: 501});
  assert.equal(expired.ok, false); assert.equal(expired.skills[0].historyValid, true);
});

test('changed fixture ownership removes current influence without rewriting history', async () => {
  const result = await reuse({now: 250, currentSnapshotId: 'fixture-state-200'});
  assert.equal(result.ok, false); assert.equal(result.skills[0].historyValid, true);
});

test('expected root, epoch and admission are explicit freshness checks', async () => {
  assert.equal((await reuse({expectedGraphRoot: '0'.repeat(64)})).ok, false);
  assert.equal((await reuse({expectedEpoch: 2})).ok, false);
  await assert.rejects(reuse({expectedAdmissionDigest: '0'.repeat(64)}), /UNEXPECTED_ADMISSION/);
});

test('tampered admitted catalogue is rejected before reuse', async () => {
  const changed = structuredClone(admission); changed.catalogue.skills[0].scope.family = 'anything';
  await assert.rejects(reuse({admission: changed}), /ADMISSION_INTEGRITY/);
});

test('pinned original source and fixture cannot be silently replaced', async () => {
  const copy = join(work, 'foundations'); await cp(foundationDirectory, copy, {recursive: true});
  await writeFile(join(copy, 'src/authority.mjs'), '// replaced\n');
  await assert.rejects(loadFoundations(copy), /FOUNDATION_SOURCE_MISMATCH/);
  assert.throws(() => {foundations.fixture.snapshots[0].names['research.agent.agi.eth'].registryOwner = 'fixture:other';}, TypeError);
});

test('existing Workbench executes a guarded installed adapter with exact provenance', async () => {
  const adapter = {manifest: {id: 'unit-admission-check', version: 1, en: 'Unit admission check', fr: 'Contrôle unitaire',
    scope: 'Synthetic unit control, not a production comparison.', artifact: 'result.json'},
  validate(input) {assert.deepEqual(Object.keys(input), ['value']); assert.ok(Number.isSafeInteger(input.value));},
  async execute(input, checkpoint, selected) {
    await checkpoint('unit-control');
    return {decision: 'TEST_CONTROL', summary: {value: input.value}, evidence: {selected: selected.selected},
      artifacts: [{name: 'result.json', type: 'application/json', content: JSON.stringify({value: input.value})}],
      limits: ['Synthetic control of the admission wrapper only.']};
  }};
  const spec = {schema: 'successor-workbench/v1', family: adapter.manifest.id, name: 'Admission unit control',
    language: 'en', owner: 'fixture:test-owner', rights: {dataClass: 'synthetic', source: 'Unit control', license: 'Apache-2.0'},
    reviewMinutes: 1, inputs: {value: 7}};
  for (const strategy of ['registry', 'graph']) {
    const runtime = createAdmittedWorkbench({adapter, admission, foundations, artifactRoot: root,
      requiredSkills: ['compatibility-witness@1'], strategy});
    const pack = await runtime.run(spec, {sourceHash: hash('unit-control-not-production')});
    assert.equal(pack.result.summary.value, 7);
    assert.equal(pack.evaluation.admission, 'HOLD');
    assert.deepEqual(pack.evaluation.authority, []);
    assert.equal(pack.result.evidence.skillAdmission.liveIdentityEnforcement, 'NOT_RUN');
    assert.equal(pack.result.evidence.skillAdmission.selection.strategy, strategy);
    await runtime.inspectPack(pack);
  }
  const rejected = createAdmittedWorkbench({adapter, admission, foundations, artifactRoot: root,
    requiredSkills: ['compatibility-witness@1'], context: {now: 150, revokedSkills: ['contract-index@1']}});
  await assert.rejects(rejected.run(spec, {sourceHash: hash('unit-control-not-production')}), /CURRENT_FIXTURE_ADMISSION_REFUSED/);
});
