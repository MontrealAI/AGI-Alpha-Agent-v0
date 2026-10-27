import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve, dirname} from 'node:path';
import {createFixtureResolver, createFixtureAttestation, createFixtureRoot, authenticateAttestation, authorizeRoot} from './inherited/src/authority.mjs';
import {canonicalize, digest, buildForest, buildGraphEpoch, ZERO_ROOT} from './inherited/src/commitments.mjs';
import {createSelector} from './inherited/src/selection.mjs';

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = resolve(HERE, 'inherited');
const read = path => JSON.parse(readFileSync(resolve(ROOT, path), 'utf8'));
const clone = x => JSON.parse(JSON.stringify(x));
const same = (a, b) => canonicalize(a) === canonicalize(b);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const file = path => ({path, sha256: sha(readFileSync(resolve(ROOT, path)))});
const save = (path, data) => writeFileSync(resolve(HERE, path), JSON.stringify(data, null, 2) + '\n');
const GRAPH_ID = 'legal-nda-source-fidelity-research';
const key = skill => `${skill.id}@${skill.version}`;

export function buildLegalCatalog() {
  const fixture = read('fixtures/authority.json'), resolver = createFixtureResolver(fixture);
  const evidence = read('assets/development-validation.json');
  if (evidence.decision !== 'PASS_EXACT_SOURCE_AND_COMPOSITION_ONLY' || evidence.records.length !== 12)
    throw Error('SOURCE_FIDELITY_EVIDENCE_REQUIRED');
  const policy = {id: 'legal-source-fidelity-only-v1', proofLevel: 'FIXTURE_EXACT_SOURCE_AND_COMPOSITION_ONLY',
    technicalScope: 'Exact source passages and changed-text coverage on six fixed synthetic development documents',
    legalCorrectness: 'NOT_ASSESSED', professionalAcceptance: 'NOT_ASSESSED', economicAdmission: 'UNASSESSED',
    attestationRole: 'EXACT_DIRECT_AGENT_WITH_ISSUE_SKILL_ATTESTATION_GRANT', rootRole: 'SEPARATE_COMMIT_GRAPH_ROOT_GRANT',
    authenticatedLiveIdentity: 'NOT_RUN', jobsClubValidationChanged: false, contractsChanged: false, settlementChanged: false};
  const scope = {jurisdiction: 'Ontario, Canada', documentFamily: 'commercial mutual NDA',
    playbook: 'ONT-NDA-RESEARCH-1.0', lawEpoch: '2026-10-26-research-scope-marker-not-legal-opinion',
    outputs: ['source-linked-mechanical-NDA-support'],
    failures: ['No professional legal acceptance', 'Fresh legal-status generalization unassessed', 'Ambiguity escalated']};
  const environment = {documentFormat: 'UTF-8-plain-text', hostDigest: file('assets/legal_packet.py').sha256,
    python: '3.12', offsets: 'Unicode-code-points-end-exclusive'};
  const rights = {code: 'Apache-2.0 inherited notices retained', input: 'original synthetic development cases',
    restrictions: ['No client data', 'No client advice or negotiation', 'No signer credentials', 'No live ENS or settlement']};
  const policyDigest = digest(policy, 'validation-policy'), scopeDigest = digest(scope, 'tested-scope');
  const environmentDigest = digest(environment, 'tested-environment'), rightsDigest = digest(rights, 'reuse-rights');
  const dossier = {id: 'legal-source-fidelity-dossier-v1', kind: 'validation-dossier',
    files: [file('assets/development-validation.json'), file('assets/scorer.py'), file('assets/production-freeze.json')],
    observed: '12 executed stage/case combinations; independent source-reference and changed-coverage functions, no keys',
    unobserved: ['Legal correctness', 'Human professional judgment', 'Market demand', 'Complete costs', 'Live identities']};
  const defs = [{id: 'nda-reference', files: ['assets/references.py', 'assets/legal_packet.py'], requires: [],
    output: 'source-reference-context', purpose: 'Resolve explicitly supported references and defined periods while preserving exact source spans'},
  {id: 'nda-amendment', files: ['assets/amendments.py', 'assets/legal_packet.py'], requires: ['nda-reference@1'],
    output: 'source-linked-mechanical-NDA-support', purpose: 'Compose explicit whole-section replacement and reference resolution; unresolved amendments escalate'}];
  const skills = defs.map(def => {
    const files = def.files.map(file), contract = {inputs: ['synthetic-NDA-and-versioned-research-playbook'], outputs: [def.output], purpose: def.purpose,
      limitations: scope.failures};
    const implementationDigest = digest({files, entrypoint: def.files[0], contract, requires: def.requires}, 'executable-asset');
    return {id: def.id, version: '1', state: 'ADMITTED_FIXTURE_ONLY', implementation: {files, entrypoint: def.files[0]},
      requires: def.requires, contract, rights, knownFailures: scope.failures, validationDossier: dossier.id,
      binding: {id: def.id, version: '1', implementationDigest, dependencyDigests: [], scopeDigest, environmentDigest, policyDigest,
        evidenceDigest: digest(dossier, 'validation-dossier'), rightsDigest, expiresAt: 500}};
  });
  const composition = {id: 'legal-two-asset-source-composition-v1', kind: 'composition-validation', decision: 'PASS_COMBINED_WORKFLOW',
    meaningOfPass: 'Exact source references and changed coverage only; no correctness assertion for legal-rule classifications',
    members: skills.map(key), implementationIdentities: skills.map(s => ({skill: key(s), implementationDigest: s.binding.implementationDigest, requires: s.requires})),
    files: [file('assets/development-validation.json')], scopeDigest, environmentDigest};
  dossier.composition = composition;
  const evidenceDigest = digest(dossier, 'validation-dossier'), compositionDigest = digest(composition, 'composition-validation');
  for (const skill of skills) skill.binding.evidenceDigest = evidenceDigest;
  for (const skill of skills) skill.binding.dependencyDigests = skill.requires.map(id => digest(skills.find(s => key(s) === id).binding, 'skill-binding')).sort();
  const edges = [{id: 'amendment-requires-reference', from: 'nda-amendment@1', to: 'nda-reference@1', relation: 'depends_on',
    scopeDigest, environmentDigest, policyDigest, compositionEvidence: compositionDigest, state: 'VALIDATED_FIXTURE_ONLY'}];
  const attestations = skills.map(s => createFixtureAttestation(s.binding, {graphId: GRAPH_ID, nonce: `legal-attest-${s.id}`,
    signer: 'fixture:attestation-delegate'}, resolver));
  const admissions = skills.map(s => ({id: `admit-${s.id}`, kind: 'technical-admission', skill: key(s), decision: 'ADMIT_FIXTURE_ONLY',
    skillBindingDigest: digest(s.binding, 'skill-binding'), evidenceDigest, legalAcceptance: 'NOT_ASSESSED', claimScope: policy.technicalScope}));
  const records = {skill: skills, edge: edges, evidence: [dossier, composition, ...admissions], policy: [policy], attestation: attestations,
    proofbundle: [{id: 'source-only-proof-bundle', evidenceDigest, professionalAcceptance: 'NOT_ASSESSED'}],
    revocation: [], supersession: [], metadata: [{id: 'scope-boundary', mode: 'FIXTURE_ONLY', liveAuthentication: false,
      actualCollections: 0, nativeAuthority: [], jobsClubValidation: 'UNCHANGED', contractsAndSettlement: 'UNCHANGED'}]};
  const forest = buildForest(records), first = clone(records);
  first.skill = first.skill.filter(s => s.id === 'nda-reference'); first.edge = []; first.attestation = first.attestation.filter(a => a.skill.id === 'nda-reference');
  first.evidence = first.evidence.filter(e => e.kind === 'validation-dossier');
  first.proofbundle = []; first.skill[0].state = 'CANDIDATE_NO_REUSE_BEFORE_COMPOSITION';
  const snapshotDigest = digest(resolver.resolveSnapshot('fixture-state-100'), 'authority-snapshot');
  const epoch = (f, number, previous) => buildGraphEpoch({forest: f, graphId: GRAPH_ID, agent: 'research.agent.agi.eth',
    chainId: 31337, registry: 'fixture:ens-v1', epoch: number, previousRoot: previous, policyDigest, snapshotDigest,
    proofLevel: policy.proofLevel});
  const firstRoot = createFixtureRoot(epoch(buildForest(first), 1, ZERO_ROOT), {graphId: GRAPH_ID, nonce: 'legal-root-1', signer: 'fixture:root-delegate'}, resolver);
  const root = createFixtureRoot(epoch(forest, 2, firstRoot.graphRoot), {graphId: GRAPH_ID, nonce: 'legal-root-2', signer: 'fixture:root-delegate'}, resolver);
  const context = {mode: 'FIXTURE_ONLY', now: 150, chainId: 31337, registry: 'fixture:ens-v1', graphId: GRAPH_ID,
    policyDigest, scopeDigest, environmentDigest, rightsDigest, currentSnapshotId: 'fixture-state-100', intent: 'reuse', evidenceAvailable: true,
    output: 'source-linked-mechanical-NDA-support', expectedGraphRoot: root.graphRoot, expectedEpoch: 2, expectedPreviousRoot: firstRoot.graphRoot};
  const catalog = {schema: 'agi-alpha-validated-skill-catalog/v1', mode: 'FIXTURE_ONLY', targetSkill: 'nda-amendment@1',
    policy, scope, environment, rights, context, composition: {id: composition.id, evidenceDigest: compositionDigest}, forest, root, history: [firstRoot, root]};
  return {catalog, fixture};
}

export function createDirect(catalog, resolver) {
  const start = performance.now(), cpu = process.cpuUsage(), owned = clone(catalog);
  const byKey = new Map(owned.forest.classes.skill.records.map(row => [key(row.record), row.record]));
  const recipe = owned.forest.classes.evidence.records.find(row => row.record.kind === 'composition-validation').record.members;
  const usage = process.cpuUsage(cpu);
  return {construction: {elapsed_seconds: (performance.now() - start) / 1000, cpu_seconds: (usage.user + usage.system) / 1e6},
    select(context) {
      const started = performance.now(), began = process.cpuUsage(), reasons = [], selected = [];
      const counters = {proof_checks: 0, attestation_checks: 0, root_authority_checks: 0, relationship_rows_examined: 0,
        relationship_traversals: 0, recipe_members_read: 0, file_reads: 0, bytes_hashed: 0, model_calls: 0};
      const verified = path => {
        if (typeof path.path !== 'string' || path.path.startsWith('/') || path.path.split('/').includes('..')) return false;
        try { const bytes = readFileSync(resolve(ROOT, path.path)); counters.file_reads++; counters.bytes_hashed += bytes.length; return sha(bytes) === path.sha256; }
        catch { return false; }
      };
      if (digest(owned.scope, 'tested-scope') !== context.scopeDigest || digest(owned.environment, 'tested-environment') !== context.environmentDigest ||
          digest(owned.rights, 'reuse-rights') !== context.rightsDigest) reasons.push('CURRENT_SCOPE_ENVIRONMENT_OR_RIGHTS_CHANGED');
      for (const id of recipe) {
        counters.recipe_members_read++;
        const skill = byKey.get(id), dossier = owned.forest.classes.evidence.records.find(row => row.record.id === skill.validationDossier)?.record;
        if (!skill.requires.every(dep => selected.includes(dep))) reasons.push('DEPENDENCY_NOT_AVAILABLE');
        counters.relationship_rows_examined += skill.requires.length;
        if (!same(skill.binding.dependencyDigests, skill.requires.map(dep => digest(byKey.get(dep).binding, 'skill-binding')).sort())) reasons.push('DEPENDENCY_BINDING_CHANGED');
        const implementation = {files: skill.implementation.files, entrypoint: skill.implementation.entrypoint, contract: skill.contract, requires: skill.requires};
        if (digest(implementation, 'executable-asset') !== skill.binding.implementationDigest || !skill.implementation.files.every(verified)) reasons.push('IMPLEMENTATION_CHANGED');
        const evidenceAvailable = Boolean(dossier && digest(dossier, 'validation-dossier') === skill.binding.evidenceDigest && dossier.files.every(verified));
        const attestation = owned.forest.classes.attestation.records.find(row => row.record.skill.id === skill.id)?.record;
        counters.attestation_checks++;
        const auth = authenticateAttestation(attestation, skill.binding, {...context, evidenceAvailable}, resolver);
        if (!auth.ok) reasons.push(...auth.reasons);
        selected.push(id);
      }
      const used = process.cpuUsage(began);
      return {strategy: 'independently-retained-direct-recipe', ok: reasons.length === 0, selected: reasons.length ? [] : selected,
        reasons: [...new Set(reasons)], counters, elapsed_seconds: (performance.now() - started) / 1000,
        cpu_seconds: (used.user + used.system) / 1e6, liveIdentityEnforcement: 'NOT_RUN', legalAcceptance: 'NOT_ASSESSED'};
    }};
}

export function controls(catalog, fixture) {
  const out = [], resolver = createFixtureResolver(fixture), skill = catalog.forest.classes.skill.records[0].record;
  const attest = catalog.forest.classes.attestation.records.find(row => row.record.skill.id === skill.id).record;
  const one = (id, checked, property = 'ok') => {
    if (checked[property] !== false) throw Error(`ADVERSE_CONTROL_FAILED:${id}`);
    out.push({id, refused: true, reasons: checked.reasons, historyValid: checked.historyValid ?? null});
  };
  const auth = context => authenticateAttestation(attest, skill.binding, {...catalog.context, ...context}, resolver);
  one('live-mode-with-no-authenticated-agent', auth({mode: 'LIVE'}));
  for (const agent of ['research.club.agi.eth', 'research.agent.agi.eth.evil', 'x.research.agent.agi.eth']) {
    const a = createFixtureAttestation(skill.binding, {agent, graphId: GRAPH_ID, nonce: 'adverse-agent', signer: 'fixture:owner-1'}, resolver);
    one(`ineligible-${agent}`, authenticateAttestation(a, skill.binding, catalog.context, resolver));
  }
  for (const [name, field] of [['playbook', 'playbook'], ['jurisdiction', 'jurisdiction'], ['law-epoch', 'lawEpoch']])
    one(`changed-${name}`, auth({scopeDigest: digest({...catalog.scope, [field]: 'CHANGED'}, 'tested-scope')}));
  one('changed-document-format', auth({environmentDigest: digest({...catalog.environment, documentFormat: 'scanned-PDF'}, 'tested-environment')}));
  one('changed-playbook-policy', auth({policyDigest: 'a'.repeat(64)}));
  one('changed-rights', auth({rightsDigest: 'b'.repeat(64)}));
  const changedSource = {...skill.binding, implementationDigest: 'c'.repeat(64)};
  one('changed-source-digest', authenticateAttestation(attest, changedSource, catalog.context, resolver));
  const changedDependency = {...skill.binding, dependencyDigests: ['d'.repeat(64)]};
  one('changed-dependency-digest', authenticateAttestation(attest, changedDependency, catalog.context, resolver));
  one('expired-skill-and-attestation', auth({now: 501}));
  one('revoked-skill', auth({revokedSkills: [key(skill)]}));
  one('revoked-attestation', auth({revokedAttestations: [attest.nonce]}));
  const stale = clone(fixture), snapshot = clone(stale.snapshots[0]); snapshot.id = 'legal-current-revoked'; snapshot.blockNumber = 101;
  snapshot.names['research.agent.agi.eth'].revoked = true; stale.snapshots.push(snapshot);
  one('revoked-agent-current-state', authenticateAttestation(attest, skill.binding, {...catalog.context, currentSnapshotId: snapshot.id}, createFixtureResolver(stale)));
  const expiredAgent = clone(fixture), exp = clone(expiredAgent.snapshots[0]); exp.id = 'legal-current-expired'; exp.blockNumber = 102;
  exp.names['research.agent.agi.eth'].expiresAt = 140; expiredAgent.snapshots.push(exp);
  one('expired-agent-current-state', authenticateAttestation(attest, skill.binding, {...catalog.context, currentSnapshotId: exp.id}, createFixtureResolver(expiredAgent)));
  one('old-valid-attestation-after-supersession', auth({supersededSkills: [key(skill)]}));
  const wrongWriter = createFixtureRoot(catalog.root, {graphId: GRAPH_ID, nonce: 'wrong-root-role', signer: 'fixture:attestation-delegate'}, resolver);
  one('attestation-role-cannot-commit-root', authorizeRoot(wrongWriter, {...catalog.context, admissionsVerified: true, lifecycleEvidenceVerified: true}, resolver));
  one('rollback-old-root-without-revalidation', authorizeRoot(catalog.history[0], {...catalog.context, admissionsVerified: true, lifecycleEvidenceVerified: true}, resolver));
  one('missing-evidence', auth({evidenceAvailable: false}));
  return out;
}

export function measure(catalog, fixture, repeats = 50) {
  const resolver = createFixtureResolver(fixture), selectors = {
    direct: createDirect(catalog, resolver), registry: createSelector(catalog, resolver, {strategy: 'registry'}),
    graph: createSelector(catalog, resolver, {strategy: 'graph'})};
  const observations = [], names = ['direct', 'registry', 'graph'];
  for (let i = 0; i < repeats; i++) for (let j = 0; j < names.length; j++) {
    const strategy = names[(i + j) % names.length], result = selectors[strategy].select(catalog.context);
    if (!result.ok || !same(result.selected, ['nda-reference@1', 'nda-amendment@1'])) throw Error('SELECTION_REFUSED:' + strategy + ':' + result.reasons);
    observations.push({repeat: i, strategy, ...result});
  }
  const summary = Object.fromEntries(names.map(strategy => {
    const rows = observations.filter(row => row.strategy === strategy), wall = rows.map(row => row.elapsed_seconds), cpu = rows.map(row => row.cpu_seconds);
    return [strategy, {n: rows.length, identical_selected_recipe: true, construction: selectors[strategy].construction,
      mean_wall_seconds: wall.reduce((a, b) => a + b, 0) / rows.length, mean_cpu_seconds: cpu.reduce((a, b) => a + b, 0) / rows.length,
      min_wall_seconds: Math.min(...wall), max_wall_seconds: Math.max(...wall), deterministic_checks_per_selection: rows[0].counters}];
  }));
  return {schema: 'legal-graph-selection-panel/v1', basis: 'LOCAL_MEASURED_RESEARCH_ONLY', inventory_size: 2, dependency_edges: 1,
    root: catalog.root.graphRoot, same_inventory_evidence_and_dependencies: true, summary, observations,
    monetarySavingClaim: 'NOT_ESTABLISHED', legalCorrectness: 'NOT_ASSESSED', liveIdentity: 'REFUSED_WITHOUT_AUTHENTICATED_AGENT',
    maintenance: {versioned_skills: 2, dependency_bindings: 1, fixture_attestations: 2, separately_authorized_root: 1,
      scope_fields_requiring_revalidation: ['jurisdiction', 'playbook', 'lawEpoch', 'documentFormat', 'hostDigest', 'sourceDigest', 'dependencyDigest'],
      complete_human_upkeep_cost: 'UNKNOWN'},
    interpretation: 'Direct recipe avoids shared-root verification; registry and graph both validate the identical shared inventory. Timing includes those explicit differences. No forced registry scan penalty, network retrieval or model calls. Two assets do not establish graph scale advantage.'};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const command = process.argv[2]; mkdirSync(resolve(HERE, 'results'), {recursive: true});
  if (command === 'build') { const built = buildLegalCatalog(); save('catalog.json', built.catalog); save('authority-fixture.json', built.fixture);
    save('results/controls.json', {scope: 'Fixture authority and freshness only', controls: controls(built.catalog, built.fixture)});
    process.stdout.write(JSON.stringify({built: true, root: built.catalog.root.graphRoot}) + '\n'); }
  else if (command === 'measure') {
    const catalog = JSON.parse(readFileSync(resolve(HERE, 'catalog.json'))), fixture = JSON.parse(readFileSync(resolve(HERE, 'authority-fixture.json')));
    const freeze = JSON.parse(readFileSync(resolve(HERE, 'source-freeze.json')));
    for (const row of freeze.files) if (sha(readFileSync(resolve(HERE, row.path))) !== row.sha256) throw Error('FROZEN_SOURCE_CHANGED:' + row.path);
    const result = measure(catalog, fixture); save('results/selection-panel.json', result);
    process.stdout.write(JSON.stringify(result.summary) + '\n');
  } else throw Error('Use build or measure');
}
