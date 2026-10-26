// SPDX-License-Identifier: Apache-2.0
import {readFileSync, lstatSync, realpathSync} from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {canonicalize, digest, buildForest, buildGraphEpoch, verifyEpochInclusion, ZERO_ROOT} from './vendor/commitments.mjs';
import {createFixtureResolver, createFixtureAttestation, authenticateAttestation, createFixtureRoot, authorizeRoot} from './vendor/authority.mjs';

const HEX = /^[a-f0-9]{64}$/;
const copied = value => JSON.parse(canonicalize(value));
const immutable = value => {if(value && typeof value === 'object') {Object.values(value).forEach(immutable); Object.freeze(value);} return value;};
const owned = value => immutable(copied(value));
const same = (a, b) => canonicalize(a) === canonicalize(b);
const key = value => `${value.id}@${value.version}`;
const sha = value => createHash('sha256').update(value).digest('hex');
const insist = (condition, message) => {if(!condition) throw Error(message);};

export const DEFAULT_POLICY = Object.freeze({
  id:'capability-advantage-research-v1', mode:'FIXTURE_ONLY',
  scope:'Sparse network forward, inverse and design research software; independently checked finite workloads.',
  attestation:'Eligible direct agent with separate ISSUE_SKILL_ATTESTATION grant.',
  publication:'Separate COMMIT_GRAPH_ROOT grant; no execution authority.',
  validation:'Installed independent verifier executes before admission and revalidation; caller PASS flags ignored.',
  composition:'Independent combined-workflow verification bound to all exact component versions.',
  execution:'Separate finite local research permission; no Harness, Fleet, settlement or live authority.',
  liveIdentityEnforcement:'NOT_RUN', jobsClubValidatorsChanged:false
});

export function createCapabilityStore({rootDirectory, fixture, verifier, compositionVerifier,
  verifierSource, compositionVerifierSource, policy = DEFAULT_POLICY, graphId = 'capability-advantage-research',
  executionPolicy = null, cachedState = null, expectedCachedStateSha256 = null}) {
  insist(typeof verifier === 'function' && typeof compositionVerifier === 'function', 'INSTALLED_VERIFIERS_REQUIRED');
  const root = realpathSync(rootDirectory), resolver = createFixtureResolver(fixture), frozenPolicy = owned(policy);
  const policyDigest = digest(frozenPolicy, 'validation-policy');
  const records = new Map(), compositions = new Map(), outputIndex = new Map(), adjacency = new Map();
  const events = [], roots = [], retired = new Set(), superseded = new Set(), receipts = [];
  const issuedSelections = new WeakMap();
  const seenNonces = [], execution = executionPolicy === null ? null : owned(executionPolicy);
  let currentRoot = null, forest = null, runs = 0;

  function files(entries) {
    insist(Array.isArray(entries) && entries.length > 0, 'BOUND_FILES_REQUIRED');
    const used = new Set();
    return entries.map(entry => {
      insist(entry && typeof entry.path === 'string' && !path.isAbsolute(entry.path) && HEX.test(entry.sha256), 'INVALID_FILE_IDENTITY');
      const full = path.resolve(root, entry.path);
      insist(full.startsWith(root + path.sep) && realpathSync(full).startsWith(root + path.sep), 'FILE_OUTSIDE_ROOT');
      for(let at = full; at !== root; at = path.dirname(at)) insist(!lstatSync(at).isSymbolicLink(), 'SYMLINK_FORBIDDEN');
      insist(!used.has(entry.path), 'DUPLICATE_FILE'); used.add(entry.path);
      const bytes = readFileSync(full);
      insist(sha(bytes) === entry.sha256, 'FILE_IDENTITY_CHANGED:' + entry.path);
      return Object.freeze({path:entry.path, sha256:entry.sha256, bytes:bytes.length, text:bytes.toString('utf8')});
    });
  }
  const verifierFiles = owned(verifierSource), compositionFiles = owned(compositionVerifierSource);
  files(verifierFiles); files(compositionFiles);
  if(cachedState !== null) {
    insist(HEX.test(expectedCachedStateSha256 || '') && sha(Buffer.from(canonicalize(cachedState))) === expectedCachedStateSha256,
      'TRUSTED_CACHED_STATE_IDENTITY_REQUIRED');
    const state = owned(cachedState);
    insist(state.schema === 'capability-advantage-cached-state/v1' && state.policyDigest === policyDigest &&
      state.graphId === graphId && state.currentRoot?.graphRoot === state.roots?.at(-1)?.graphRoot,
      'CACHED_STATE_CONTEXT_MISMATCH');
    for(const record of state.records) {
      const id = key(record.dossier); insist(!records.has(id), 'DUPLICATE_CACHED_SKILL'); records.set(id, record);
      for(const output of record.dossier.outputs) outputIndex.set(output, [...(outputIndex.get(output) || []), id]);
      adjacency.set(id, [...record.dossier.dependencies]);
      seenNonces.push([graphId, record.attestation.action, record.attestation.agent, record.attestation.nonce].join('|'));
    }
    for(const item of state.compositions) compositions.set(item.dossier.target, item);
    for(const event of state.events) {events.push(event); (event.kind === 'revoke' ? retired : superseded).add(event.predecessor);}
    roots.push(...state.roots); receipts.push(...state.receipts); forest = state.forest; currentRoot = state.currentRoot;
  }

  function context(binding, now, snapshotId, intent = 'reuse') {
    return {mode:'FIXTURE_ONLY', now, chainId:31337, registry:'fixture:ens-v1', graphId, policyDigest,
      currentSnapshotId:snapshotId, intent, evidenceAvailable:true, scopeDigest:binding.scopeDigest,
      environmentDigest:binding.environmentDigest, rightsDigest:binding.rightsDigest,
      revokedSkills:[...retired], supersededSkills:[...superseded], seenNonces:[...seenNonces]};
  }

  function active(record, now, snapshotId) {
    insist(record, 'MISSING_SKILL');
    files(record.dossier.implementation.files); files(record.dossier.evidence.files); files(verifierFiles);
    const auth = authenticateAttestation(record.attestation, record.binding, context(record.binding, now, snapshotId), resolver);
    insist(auth.ok, 'SKILL_UNAVAILABLE:' + auth.reasons.join('|'));
    const dependencies = record.dossier.dependencies.map(id => {
      const dependency = records.get(id); insist(dependency, 'MISSING_DEPENDENCY');
      return digest(dependency.binding, 'skill-binding');
    }).sort();
    insist(same(dependencies, record.binding.dependencyDigests), 'DEPENDENCY_BINDING_CHANGED');
    return auth;
  }

  async function admit(dossierInput, {agent = 'research.agent.agi.eth', signer = 'fixture:attestation-delegate',
    now = 150, snapshotId = 'fixture-state-100', revalidation = false} = {}) {
    const started = performance.now(), dossier = owned(dossierInput), id = key(dossier);
    insist(typeof dossier.id === 'string' && /^[a-z][a-z0-9-]{1,63}$/.test(dossier.id), 'INVALID_SKILL_ID');
    insist(typeof dossier.version === 'string' && dossier.version.length > 0, 'VERSION_REQUIRED');
    insist(typeof dossier.creator === 'string' && dossier.creator.length > 0 && typeof dossier.motivatingJob === 'string', 'PROVENANCE_REQUIRED');
    insist(Array.isArray(dossier.dependencies) && new Set(dossier.dependencies).size === dossier.dependencies.length, 'DEPENDENCIES_REQUIRED');
    insist(Array.isArray(dossier.outputs) && dossier.outputs.length > 0 && new Set(dossier.outputs).size === dossier.outputs.length, 'OUTPUTS_REQUIRED');
    insist(Number.isSafeInteger(dossier.expiresAt) && dossier.expiresAt > now, 'INVALID_EXPIRY');
    insist(!records.has(id) || revalidation, 'VERSION_ALREADY_ADMITTED');
    insist(!retired.has(id) && !superseded.has(id), 'LIFECYCLE_BLOCK_REQUIRES_NEW_VERSION');
    if(revalidation) insist(records.has(id) && same(records.get(id).dossier, dossier), 'REVALIDATION_CANNOT_REWRITE_VERSION');
    const implementationFiles = files(dossier.implementation.files), evidenceFiles = files(dossier.evidence.files);
    files(verifierFiles);
    const dependencyDigests = dossier.dependencies.map(dependencyId => {
      const dependency = records.get(dependencyId); active(dependency, now, snapshotId);
      return digest(dependency.binding, 'skill-binding');
    }).sort();
    const implementationDigest = digest(dossier.implementation, 'executable-asset');
    const scopeDigest = digest(dossier.scope, 'tested-scope'), environmentDigest = digest(dossier.environment, 'tested-environment');
    const rightsDigest = digest(dossier.rights, 'reuse-rights');
    const evidenceDigest = digest({evidence:dossier.evidence, verifierSource:verifierFiles}, 'validation-dossier');
    const binding = owned({id:dossier.id, version:dossier.version, implementationDigest, dependencyDigests, scopeDigest,
      environmentDigest, policyDigest, evidenceDigest, rightsDigest, expiresAt:dossier.expiresAt});
    const checked = await verifier(owned({dossier, binding, implementationFiles, evidenceFiles}));
    insist(checked && checked.accepted === true && Number.isSafeInteger(checked.checks) && checked.checks > 0, 'INDEPENDENT_VALIDATION_FAILED');
    insist(checked.implementationDigest === implementationDigest && checked.evidenceDigest === evidenceDigest && checked.scopeDigest === scopeDigest, 'VALIDATOR_BINDING_MISMATCH');
    const nonce = `admit-${id}-${receipts.length + 1}`;
    const attestation = createFixtureAttestation(binding, {agent, signer, graphId, snapshotId, issuedAt:now,
      expiresAt:dossier.expiresAt, nonce}, resolver);
    const auth = authenticateAttestation(attestation, binding, context(binding, now, snapshotId, 'admit'), resolver);
    insist(auth.ok, 'ATTESTATION_REFUSED:' + auth.reasons.join('|'));
    seenNonces.push(auth.nonceKey);
    const validation = owned(checked), record = owned({dossier, binding, attestation, validation,
      status:'ADMITTED_FIXTURE_ONLY', creator:dossier.creator, attester:agent, validationSigner:signer,
      liveIdentityEnforcement:'NOT_RUN', economicAdmission:'UNASSESSED', nativeAuthority:[]});
    records.set(id, record);
    for(const output of dossier.outputs) outputIndex.set(output, [...new Set([...(outputIndex.get(output) || []), id])]);
    adjacency.set(id, [...dossier.dependencies]);
    currentRoot = null;
    const receipt = {kind:revalidation ? 'revalidate' : 'admit', skill:id, bindingDigest:digest(binding, 'skill-binding'),
      checks:checked.checks, elapsedMicroseconds:Math.max(0, Math.round((performance.now() - started) * 1000)),
      verdict:'ADMITTED_FIXTURE_ONLY', liveIdentityEnforcement:'NOT_RUN'};
    receipts.push(receipt);
    return copied(record);
  }

  async function admitComposition(input, {now = 150, snapshotId = 'fixture-state-100'} = {}) {
    const dossier = owned(input);
    insist(typeof dossier.id === 'string' && records.has(dossier.target), 'COMPOSITION_TARGET_REQUIRED');
    insist(Array.isArray(dossier.members) && dossier.members.length > 1 && new Set(dossier.members).size === dossier.members.length,
      'MULTIPLE_DISTINCT_COMPONENTS_REQUIRED');
    const ordered = plan(dossier.target, 'registry');
    insist(same(ordered, dossier.members), 'COMPOSITION_CLOSURE_MISMATCH');
    const bindings = ordered.map(id => {const record = records.get(id); active(record, now, snapshotId); return {skill:id, binding:record.binding};});
    const evidenceFiles = files(dossier.evidence.files); files(compositionFiles);
    const bindingDigest = digest({dossier, bindings, verifierSource:compositionFiles}, 'independent-composition');
    const checked = await compositionVerifier(owned({dossier, bindings, bindingDigest, evidenceFiles}));
    insist(checked && checked.accepted === true && checked.compositionValidated === true && checked.bindingDigest === bindingDigest &&
      Number.isSafeInteger(checked.checks) && checked.checks > 0, 'INDEPENDENT_COMPOSITION_VALIDATION_FAILED');
    compositions.set(dossier.target, owned({dossier, bindings, bindingDigest, validation:checked}));
    receipts.push({kind:'composition-admission', target:dossier.target, bindingDigest, checks:checked.checks});
    currentRoot = null;
    return copied(compositions.get(dossier.target));
  }

  function plan(target, strategy) {
    insist(['registry', 'graph'].includes(strategy), 'UNKNOWN_STRATEGY');
    const visited = new Set(), visiting = new Set(), ordered = [];
    function walk(id) {
      insist(!visiting.has(id), 'DEPENDENCY_CYCLE');
      if(visited.has(id)) return;
      const record = records.get(id); insist(record, 'MISSING_DEPENDENCY');
      visiting.add(id);
      const dependencies = strategy === 'graph' ? adjacency.get(id) : record.dossier.dependencies;
      dependencies.forEach(walk); visiting.delete(id); visited.add(id); ordered.push(id);
    }
    walk(target); return ordered;
  }

  function lifecycle(kind, predecessor, successor, reason) {
    insist(records.has(predecessor) && typeof reason === 'string' && reason.length > 0, 'LIFECYCLE_EVIDENCE_REQUIRED');
    if(kind === 'revoke') {insist(!retired.has(predecessor), 'ALREADY_REVOKED'); retired.add(predecessor);}
    else {insist(records.has(successor) && predecessor !== successor, 'ADMITTED_SUCCESSOR_REQUIRED'); superseded.add(predecessor);}
    events.push(owned({kind, predecessor, successor, reason, policyDigest, sequence:events.length + 1})); currentRoot = null;
  }

  function publish({agent = 'research.agent.agi.eth', signer = 'fixture:root-delegate', now = 150,
    snapshotId = 'fixture-state-100'} = {}) {
    insist(records.size > 0, 'NO_ADMISSIONS');
    for(const [id, record] of records) if(!retired.has(id) && !superseded.has(id)) active(record, now, snapshotId);
    const state = {
      skill:[...records.values()].map(r => ({id:key(r.dossier), creator:r.creator, status:r.status, binding:r.binding, dossier:r.dossier})),
      edge:[...records.values()].flatMap(r => r.dossier.dependencies.map(to => ({from:key(r.dossier), to, relation:'requires', policyDigest}))),
      evidence:[...records.values()].map(r => ({id:key(r.dossier), validation:r.validation, evidenceDigest:r.binding.evidenceDigest}))
        .concat([...compositions.values()].map(c => ({id:c.dossier.id, composition:c}))),
      proofbundle:[{id:'research-boundary', proofLevel:'LOCAL_RESEARCH_SAME_SESSION_REVIEW', liveIdentityEnforcement:'NOT_RUN'}],
      policy:[frozenPolicy], attestation:[...records.values()].map(r => r.attestation),
      revocation:events.filter(e => e.kind === 'revoke'), supersession:events.filter(e => e.kind === 'supersede'),
      metadata:[{id:'execution-separation', nativeAuthority:[], executionPolicyInherited:false, liveIdentityEnforcement:'NOT_RUN'}]
    };
    const built = buildForest(state), previousRoot = roots.at(-1)?.graphRoot || ZERO_ROOT, epoch = roots.length + 1;
    const snapshotDigest = digest(resolver.resolveSnapshot(snapshotId), 'authority-snapshot');
    const packet = buildGraphEpoch({forest:built, graphId, agent, chainId:31337, registry:'fixture:ens-v1', epoch, previousRoot,
      policyDigest, snapshotDigest, proofLevel:'LOCAL_RESEARCH_SAME_SESSION_REVIEW'});
    const rootRecord = createFixtureRoot(packet, {agent, signer, graphId, snapshotId, issuedAt:now, expiresAt:9000,
      nonce:'root-' + epoch}, resolver);
    const authorization = authorizeRoot(rootRecord, {mode:'FIXTURE_ONLY', now, chainId:31337, registry:'fixture:ens-v1', graphId,
      policyDigest, currentSnapshotId:snapshotId, expectedPreviousRoot:previousRoot, expectedEpoch:epoch,
      expectedGraphRoot:rootRecord.graphRoot, admissionsVerified:true, lifecycleEvidenceVerified:true}, resolver);
    insist(authorization.ok, 'ROOT_PUBLICATION_REFUSED:' + authorization.reasons.join('|'));
    currentRoot = owned(rootRecord); forest = owned(built); roots.push(currentRoot);
    return copied({root:currentRoot, forest, history:roots});
  }

  function select(output, {strategy = 'registry', scopeDigest, environmentDigest, rightsDigest, now = 150,
    snapshotId = 'fixture-state-100', expectedRoot} = {}) {
    const started = performance.now();
    try {
      insist(currentRoot && forest, 'UNPUBLISHED_STATE');
      insist(expectedRoot === currentRoot.graphRoot, 'TRUSTED_ROOT_REQUIRED');
      const candidates = outputIndex.get(output) || [];
      let lastError = 'NO_MATCHING_OUTPUT';
      for(const target of candidates) {
        try {
          const record = records.get(target);
          insist(record.binding.scopeDigest === scopeDigest && record.binding.environmentDigest === environmentDigest &&
            record.binding.rightsDigest === rightsDigest, 'MISSION_SCOPE_OR_ENVIRONMENT_MISMATCH');
          const selected = plan(target, strategy);
          const rootAuth = authorizeRoot(currentRoot, {mode:'FIXTURE_ONLY', now, chainId:31337, registry:'fixture:ens-v1', graphId,
            policyDigest, currentSnapshotId:snapshotId, intent:'reuse', expectedPreviousRoot:currentRoot.previousRoot,
            expectedEpoch:currentRoot.epoch, expectedGraphRoot:currentRoot.graphRoot, admissionsVerified:true,
            lifecycleEvidenceVerified:true}, resolver);
          insist(rootAuth.ok, 'ROOT_AUTHORITY_STALE');
          for(const id of selected) {
            const current = records.get(id); active(current, now, snapshotId);
            const leaf = forest.classes.skill.records.find(row => row.record.id === id);
            insist(leaf && verifyEpochInclusion(currentRoot, 'skill', leaf.record, leaf.proof), 'SKILL_INCLUSION_FAILED');
          }
          if(selected.length > 1) {
            const composition = compositions.get(target); insist(composition, 'COMPOSITION_NOT_INDEPENDENTLY_VALIDATED');
            files(composition.dossier.evidence.files); files(compositionFiles);
            const currentBindings = selected.map(id => ({skill:id, binding:records.get(id).binding}));
            insist(same(currentBindings, composition.bindings), 'COMPOSITION_REVALIDATION_REQUIRED');
          }
          const selection = owned({ok:true, decision:'REUSE_WITHIN_FIXTURE_SCOPE', strategy, selected, output, graphRoot:currentRoot.graphRoot,
            relationshipRows:selected.reduce((n, id) => n + records.get(id).dossier.dependencies.length, 0),
            elapsedMicroseconds:Math.max(0, Math.round((performance.now() - started) * 1000)),
            liveIdentityEnforcement:'NOT_RUN', cryptographicAuthentication:false, nativeAuthority:[], economicAdmission:'UNASSESSED'});
          issuedSelections.set(selection, {snapshotId});
          return selection;
        } catch(error) {lastError = error.message;}
      }
      throw Error(lastError);
    } catch(error) {
      return {ok:false, decision:'REFUSE_REUSE', strategy, selected:[], reason:error.message,
        elapsedMicroseconds:Math.max(0, Math.round((performance.now() - started) * 1000)), liveIdentityEnforcement:'NOT_RUN', nativeAuthority:[]};
    }
  }

  function authorizeLocalExecution(selection, {missionId, now = 150} = {}) {
    insist(execution && execution.mode === 'LOCAL_RESEARCH_ONLY' && execution.nativeAuthority?.length === 0,
      'SEPARATE_LOCAL_EXECUTION_PERMISSION_REQUIRED');
    insist(issuedSelections.has(selection) && selection.ok && currentRoot && selection.graphRoot === currentRoot.graphRoot, 'CURRENT_SELECTION_REQUIRED');
    insist(typeof missionId === 'string' && missionId.length > 0 && Number.isSafeInteger(now) && now < execution.expiresAt, 'EXECUTION_CONTEXT_INVALID');
    insist(Number.isSafeInteger(execution.maxRuns) && runs < execution.maxRuns, 'EXECUTION_BUDGET_EXHAUSTED');
    insist(selection.selected.every(id => execution.allowedSkills.includes(id)), 'EXECUTION_SKILL_NOT_ALLOWED');
    for(const id of selection.selected) active(records.get(id), now, issuedSelections.get(selection).snapshotId);
    runs++;
    return {mode:'LOCAL_RESEARCH_ONLY', missionId, usedRuns:runs, maxRuns:execution.maxRuns,
      nativeAuthority:[], liveIdentityEnforcement:'NOT_RUN', fundsReserved:'0', settlement:'NOT_CONNECTED'};
  }

  return Object.freeze({admit, admitComposition, publish, select, authorizeLocalExecution,
    revoke:(id, reason) => lifecycle('revoke', id, null, reason),
    supersede:(oldId, newId, reason) => lifecycle('supersede', oldId, newId, reason),
    inspect:() => copied({records:[...records.values()], compositions:[...compositions.values()], events, roots, receipts,
      liveIdentityEnforcement:'NOT_RUN', nativeAuthority:[]}),
    exportCachedState:() => copied({schema:'capability-advantage-cached-state/v1', policyDigest, graphId,
      records:[...records.values()], compositions:[...compositions.values()], events, roots, receipts,
      forest, currentRoot}),
    policyDigest, graphId});
}
