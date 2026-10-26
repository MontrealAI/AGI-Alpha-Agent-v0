// SPDX-License-Identifier: Apache-2.0
import {createHash} from 'node:crypto';
import {lstat, readFile, realpath} from 'node:fs/promises';
import {resolve, relative, isAbsolute, sep} from 'node:path';
import {pathToFileURL} from 'node:url';

export const FOUNDATION_COMMIT = 'c9f2892c06e173cb0f9d5ae710cffc4a6f1fa723';
export const FOUNDATION_SHA256 = Object.freeze({
  'src/authority.mjs': '5229ee523cc6280debed2c55aff922d7d1192c848ade43676a9db86121294de1',
  'src/commitments.mjs': '454175c59be23ca5c8d86162403ca8a21a37b9ffddfceebd0f453b1730dd917e',
  'fixtures/authority.json': 'c130af4be60ab8ab5e61292ddbdd7f9588f2f8817c0edca150ccfc8709624da4',
});
const HEX = /^[0-9a-f]{64}$/;
const ID = /^[a-z][a-z0-9-]{0,63}$/;
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const check = (value, reason) => {if (!value) throw Error(reason);};
const keyFor = skill => `${skill.id}@${skill.version}`;
const ordered = values => [...values].sort();
const unique = values => new Set(values).size === values.length;
function freeze(value) {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value)) freeze(child);
    Object.freeze(value);
  }
  return value;
}

async function checkedFile(root, name, expected = null) {
  check(typeof name === 'string' && name.length > 0 && !isAbsolute(name), 'RELATIVE_FILE_REQUIRED');
  const parts = name.split('/');
  check(parts.every(part => part && part !== '.' && part !== '..' && !part.includes('\\')), 'UNSAFE_FILE_PATH');
  let path = root;
  for (const part of parts) {
    path = resolve(path, part);
    const status = await lstat(path);
    check(!status.isSymbolicLink(), 'SYMLINK_REFUSED');
  }
  const local = relative(root, path);
  check(local !== '..' && !local.startsWith(`..${sep}`) && !isAbsolute(local), 'FILE_OUTSIDE_ROOT');
  const status = await lstat(path);
  check(status.isFile() && status.size <= 32_000_000, 'REGULAR_BOUNDED_FILE_REQUIRED');
  const bytes = await readFile(path);
  if (expected) {
    check(bytes.length === expected.bytes, 'FILE_SIZE_MISMATCH');
    check(hash(bytes) === expected.sha256, 'FILE_DIGEST_MISMATCH');
  }
  return bytes;
}

export async function loadFoundations(directory) {
  const root = resolve(directory);
  check(await realpath(root) === root, 'FOUNDATION_SYMLINK_REFUSED');
  const identities = {};
  for (const [path, expected] of Object.entries(FOUNDATION_SHA256)) {
    const bytes = await checkedFile(root, path);
    check(hash(bytes) === expected, 'FOUNDATION_SOURCE_MISMATCH');
    identities[path] = {sha256: expected, bytes: bytes.length};
  }
  const commitments = await import(pathToFileURL(resolve(root, 'src/commitments.mjs')).href);
  const authority = await import(pathToFileURL(resolve(root, 'src/authority.mjs')).href);
  for (const [path, expected] of Object.entries(FOUNDATION_SHA256)) {
    check(hash(await checkedFile(root, path)) === expected, 'FOUNDATION_CHANGED_DURING_IMPORT');
  }
  const fixture = JSON.parse(await readFile(resolve(root, 'fixtures/authority.json'), 'utf8'));
  return Object.freeze({commitments, authority, fixture: freeze(fixture), identities: freeze(identities), sourceCommit: FOUNDATION_COMMIT});
}

function normalize(catalogue, foundations) {
  const {canonicalize} = foundations.commitments;
  const owned = JSON.parse(canonicalize(catalogue));
  check(owned.schema === 'agi-alpha.work-discovery-catalogue.v1', 'CATALOGUE_SCHEMA');
  check(owned.mode === 'FIXTURE_ONLY', 'LIVE_IDENTITY_ENFORCEMENT_NOT_RUN');
  check(ID.test(owned.graphId), 'GRAPH_ID');
  for (const field of ['policy', 'environment', 'rights']) {
    check(owned[field] && typeof owned[field] === 'object' && !Array.isArray(owned[field]), 'CONTEXT_REQUIRED');
  }
  check(Array.isArray(owned.skills) && owned.skills.length > 0 && owned.skills.length <= 128, 'SKILL_BOUND');
  check(Array.isArray(owned.edges) && owned.edges.length <= 512, 'EDGE_BOUND');
  const keys = owned.skills.map(keyFor);
  check(unique(keys), 'DUPLICATE_SKILL');
  let declaredBytes = 0;
  for (const skill of owned.skills) {
    check(ID.test(skill.id) && /^[1-9][0-9]{0,7}$/.test(skill.version), 'SKILL_ID_OR_VERSION');
    check(typeof skill.creator === 'string' && skill.creator.startsWith('fixture:'), 'FIXTURE_CREATOR_REQUIRED');
    check(skill.scope && typeof skill.scope === 'object' && !Array.isArray(skill.scope), 'SCOPE_REQUIRED');
    check(Number.isSafeInteger(skill.expiresAt) && skill.expiresAt > 0, 'SKILL_EXPIRY');
    check(Array.isArray(skill.dependencies) && unique(skill.dependencies), 'DEPENDENCY_LIST');
    check(skill.dependencies.every(dep => keys.includes(dep) && dep !== keyFor(skill)), 'UNKNOWN_DEPENDENCY');
    for (const field of ['implementationFiles', 'evidenceFiles', 'compositionEvidenceFiles']) {
      check(Array.isArray(skill[field]) && skill[field].length <= 128, 'FILE_MANIFEST_BOUND');
      check(unique(skill[field].map(file => file.path)), 'DUPLICATE_FILE');
      for (const file of skill[field]) {
        check(typeof file.path === 'string' && HEX.test(file.sha256), 'FILE_IDENTITY');
        check(Number.isSafeInteger(file.bytes) && file.bytes >= 0 && file.bytes <= 32_000_000, 'FILE_SIZE');
        declaredBytes += file.bytes;
        check(declaredBytes <= 128_000_000, 'CATALOGUE_RESOURCE_BOUND');
      }
    }
    check(skill.implementationFiles.length > 0 && skill.evidenceFiles.length > 0, 'SOURCE_AND_EVIDENCE_REQUIRED');
    check(skill.dependencies.length === 0 || skill.compositionEvidenceFiles.length > 0, 'COMPOSITION_EVIDENCE_REQUIRED');
  }
  const expected = owned.skills.flatMap(skill => skill.dependencies.map(from => ({from, to: keyFor(skill), kind: 'requires'})));
  const sortEdges = edges => ordered(edges.map(edge => canonicalize(edge)));
  check(canonicalize(sortEdges(owned.edges)) === canonicalize(sortEdges(expected)), 'EDGE_DEPENDENCY_MISMATCH');
  const visiting = new Set(), complete = new Set(), byKey = new Map(owned.skills.map(skill => [keyFor(skill), skill]));
  function visit(key) {
    check(!visiting.has(key), 'DEPENDENCY_CYCLE');
    if (complete.has(key)) return;
    visiting.add(key);
    for (const dependency of byKey.get(key).dependencies) visit(dependency);
    visiting.delete(key); complete.add(key);
  }
  keys.forEach(visit);
  return owned;
}

async function verifiedFiles(skill, artifactRoot) {
  const files = new Map();
  for (const field of ['implementationFiles', 'evidenceFiles', 'compositionEvidenceFiles']) {
    for (const descriptor of skill[field]) {
      files.set(descriptor.path, await checkedFile(artifactRoot, descriptor.path, descriptor));
    }
  }
  return files;
}

function bindings(catalogue, foundations) {
  const {digest} = foundations.commitments;
  const implementationDigests = new Map(catalogue.skills.map(skill =>
    [keyFor(skill), digest(skill.implementationFiles, 'work-discovery-implementation-files')]));
  return catalogue.skills.map(skill => ({id: skill.id, version: skill.version,
    implementationDigest: implementationDigests.get(keyFor(skill)),
    dependencyDigests: ordered(skill.dependencies.map(key => implementationDigests.get(key))),
    scopeDigest: digest(skill.scope, 'work-discovery-scope'),
    environmentDigest: digest(catalogue.environment, 'work-discovery-environment'),
    policyDigest: digest(catalogue.policy, 'work-discovery-policy'),
    evidenceDigest: digest({evidence: skill.evidenceFiles, composition: skill.compositionEvidenceFiles}, 'work-discovery-evidence'),
    rightsDigest: digest(catalogue.rights, 'work-discovery-rights'), expiresAt: skill.expiresAt}));
}

export async function admitCatalogue({catalogue, foundations, artifactRoot, verifyEvidence, issuedAt = 100,
  now = 150, expiresAt = 500, epoch = 1, previousRoot = '0'.repeat(64)}) {
  check(typeof verifyEvidence === 'function', 'INSTALLED_EVIDENCE_VERIFIER_REQUIRED');
  const input = normalize(catalogue, foundations), sourceRoot = resolve(artifactRoot);
  check(await realpath(sourceRoot) === sourceRoot, 'ARTIFACT_ROOT_SYMLINK_REFUSED');
  const {digest, buildForest, buildGraphEpoch, canonicalize} = foundations.commitments;
  const {createFixtureResolver, createFixtureAttestation, createFixtureRoot, authenticateAttestation, authorizeRoot} = foundations.authority;
  const resolver = createFixtureResolver(foundations.fixture), bound = bindings(input, foundations);
  const policyDigest = digest(input.policy, 'work-discovery-policy');
  const context = {mode: 'FIXTURE_ONLY', now, chainId: 31337, registry: 'fixture:ens-v1',
    graphId: input.graphId, policyDigest, currentSnapshotId: 'fixture-state-100', evidenceAvailable: true};
  const skills = [], attestations = [], assessments = [];
  for (let i = 0; i < input.skills.length; i++) {
    const skill = input.skills[i], binding = bound[i], files = await verifiedFiles(skill, sourceRoot);
    const verdict = await verifyEvidence({skill: structuredClone(skill), binding: structuredClone(binding), files});
    check(verdict?.accepted === true && typeof verdict.validatorId === 'string' && verdict.validatorId.length > 0,
      'TECHNICAL_EVIDENCE_NOT_ACCEPTED');
    check(verdict.scopeDigest === binding.scopeDigest && verdict.implementationDigest === binding.implementationDigest,
      'TECHNICAL_VERDICT_BINDING_MISMATCH');
    check(skill.dependencies.length === 0 || verdict.compositionAccepted === true, 'COMPOSITION_NOT_VALIDATED');
    const attestation = createFixtureAttestation(binding, {graphId: input.graphId, issuedAt, expiresAt,
      nonce: `${input.graphId}:skill:${keyFor(skill)}:${epoch}`, signer: 'fixture:attestation-delegate'}, resolver);
    const assessment = authenticateAttestation(attestation, binding, {...context, scopeDigest: binding.scopeDigest,
      environmentDigest: binding.environmentDigest, rightsDigest: binding.rightsDigest}, resolver);
    check(assessment.ok, 'FIXTURE_ATTESTATION_REJECTED');
    skills.push({...binding, creator: skill.creator, dependencies: skill.dependencies, technicalVerifier: verdict.validatorId});
    attestations.push(attestation); assessments.push(assessment);
  }
  const records = {skill: skills, edge: input.edges,
    evidence: input.skills.map((skill, i) => ({id: keyFor(skill), digest: bound[i].evidenceDigest,
      files: [...skill.evidenceFiles, ...skill.compositionEvidenceFiles]})),
    attestation: attestations, policy: [{policyDigest, policy: input.policy}],
    metadata: [{mode: 'FIXTURE_ONLY', liveIdentityEnforcement: 'NOT_RUN', cryptographicAuthentication: false,
      executionAuthority: [], settlement: 'NOT_CONNECTED', sourceCommit: FOUNDATION_COMMIT}]};
  const forest = buildForest(records);
  const packet = buildGraphEpoch({forest, graphId: input.graphId, agent: 'research.agent.agi.eth',
    chainId: 31337, registry: 'fixture:ens-v1', epoch, previousRoot, policyDigest,
    snapshotDigest: digest(input, 'work-discovery-catalogue')});
  const root = createFixtureRoot(packet, {graphId: input.graphId, issuedAt, expiresAt,
    nonce: `${input.graphId}:root:${epoch}`, signer: 'fixture:root-delegate'}, resolver);
  const rootAssessment = authorizeRoot(root, {...context, expectedPreviousRoot: previousRoot, expectedEpoch: epoch,
    admissionsVerified: true, lifecycleEvidenceVerified: true}, resolver);
  check(rootAssessment.ok, 'FIXTURE_ROOT_REJECTED');
  const body = {schema: 'agi-alpha.work-discovery-admission.v1', mode: 'FIXTURE_ONLY', catalogue: input,
    skills, attestations, assessments, forest, root, rootAssessment, issuedAt, checkedAt: now,
    liveIdentityEnforcement: 'NOT_RUN', cryptographicAuthentication: false, executionAuthority: [],
    settlement: 'NOT_CONNECTED', foundationSources: foundations.identities};
  return {...JSON.parse(canonicalize(body)), admissionDigest: digest(body, 'work-discovery-admission')};
}

export async function assessReuse({admission, foundations, artifactRoot, now = 150,
  currentSnapshotId = 'fixture-state-100', revokedSkills = [], supersededSkills = [], revokedRoots = [],
  expectedGraphRoot = admission.root.graphRoot, expectedEpoch = admission.root.epoch,
  expectedAdmissionDigest = admission.admissionDigest}) {
  const {digest, canonicalize, verifyEpochInclusion, buildForest} = foundations.commitments;
  const {authenticateAttestation, authorizeRoot, createFixtureResolver} = foundations.authority;
  const {admissionDigest, ...body} = JSON.parse(canonicalize(admission));
  check(body.schema === 'agi-alpha.work-discovery-admission.v1' && body.mode === 'FIXTURE_ONLY', 'ADMISSION_SCHEMA');
  check(admissionDigest === digest(body, 'work-discovery-admission'), 'ADMISSION_INTEGRITY');
  check(admissionDigest === expectedAdmissionDigest, 'UNEXPECTED_ADMISSION');
  const catalogue = normalize(body.catalogue, foundations), bound = bindings(catalogue, foundations);
  const resolver = createFixtureResolver(foundations.fixture), results = [];
  check(body.skills.length === bound.length && body.attestations.length === bound.length, 'ADMISSION_COVERAGE');
  check(body.root.snapshotDigest === digest(catalogue, 'work-discovery-catalogue'), 'CATALOGUE_ROOT_MISMATCH');
  const forestRecords = Object.fromEntries(Object.entries(body.forest.classes).map(([type, value]) =>
    [type, value.records.map(row => row.record)]));
  check(canonicalize(buildForest(forestRecords)) === canonicalize(body.forest), 'FOREST_INTEGRITY');
  const context = {mode: 'FIXTURE_ONLY', now, currentSnapshotId, graphId: catalogue.graphId,
    chainId: 31337, registry: 'fixture:ens-v1', policyDigest: digest(catalogue.policy, 'work-discovery-policy'),
    evidenceAvailable: true, intent: 'reuse', revokedSkills, supersededSkills, revokedRoots};
  for (let i = 0; i < catalogue.skills.length; i++) {
    await verifiedFiles(catalogue.skills[i], resolve(artifactRoot));
    const binding = bound[i], skill = body.skills[i];
    check(canonicalize(foundations.authority.skillBinding(skill)) === canonicalize(binding), 'SKILL_BINDING_MISMATCH');
    const leaf = body.forest.classes.skill.records.find(record => record.record.id === skill.id && record.record.version === skill.version);
    check(leaf && canonicalize(leaf.record) === canonicalize(skill) &&
      verifyEpochInclusion(body.root, 'skill', skill, leaf.proof), 'SKILL_INCLUSION_FAILED');
    results.push(authenticateAttestation(body.attestations[i], binding, {...context, scopeDigest: binding.scopeDigest,
      environmentDigest: binding.environmentDigest, rightsDigest: binding.rightsDigest}, resolver));
  }
  const root = authorizeRoot(body.root, {...context, expectedPreviousRoot: body.root.previousRoot,
    expectedEpoch, expectedGraphRoot, admissionsVerified: results.every(result => result.ok), lifecycleEvidenceVerified: true}, resolver);
  return {ok: results.every(result => result.ok) && root.ok, skills: results, root, mode: 'FIXTURE_ONLY',
    liveIdentityEnforcement: 'NOT_RUN', cryptographicAuthentication: false, executionAuthority: [],
    settlement: 'NOT_CONNECTED', informationDigest: digest(catalogue, 'work-discovery-catalogue')};
}

export function createSelector(admission, foundations, strategy = 'registry') {
  check(['registry', 'graph'].includes(strategy), 'SELECTION_STRATEGY');
  const catalogue = normalize(admission.catalogue, foundations), {digest} = foundations.commitments;
  const rows = new Map(catalogue.skills.map(skill => [keyFor(skill), skill]));
  const adjacency = new Map(catalogue.skills.map(skill => [keyFor(skill), []]));
  for (const edge of catalogue.edges) adjacency.get(edge.to).push(edge.from);
  return required => {
    check(Array.isArray(required) && required.length > 0 && required.length <= 128 && unique(required), 'REQUESTED_SKILLS');
    const selected = [], seen = new Set();
    function visit(key) {
      check(rows.has(key), 'UNSUPPORTED_SKILL');
      if (seen.has(key)) return;
      const dependencies = strategy === 'graph' ? adjacency.get(key) : rows.get(key).dependencies;
      ordered(dependencies).forEach(visit); seen.add(key); selected.push(key);
    }
    ordered(required).forEach(visit);
    return {strategy, selected, inspectedSkills: selected.length,
      informationDigest: digest(catalogue, 'work-discovery-catalogue'),
      scope: 'Equal skills, evidence and dependencies; selection is not admission or proof of economic value.'};
  };
}
