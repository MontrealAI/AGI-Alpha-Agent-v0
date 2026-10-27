// SPDX-License-Identifier: Apache-2.0
// Offline bindings of a supplied research opportunity to existing AGI ALPHA components.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const STUDY = path.dirname(HERE);
const PUBLIC_FIXTURE_PASSPHRASE = 'PUBLIC-RESEARCH-ONLY-NO-CONFIDENTIALITY-2026';
const encoder = new TextEncoder();
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const clone = value => structuredClone(value);
const json = value => JSON.stringify(value, null, 2) + '\n';

function args(argv) {
  const options = { input: 'config/venture.json', output: 'integration/artifacts/selected' };
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    if (!['--input', '--output'].includes(key) || !argv[i + 1]) {
      throw Error('Usage: node integration/run_integration.mjs --input config/venture.json [--output integration/artifacts/selected]');
    }
    options[key.slice(2)] = argv[i + 1];
  }
  return options;
}

function contained(root, supplied) {
  const resolved = path.resolve(root, supplied);
  if (resolved !== root && !resolved.startsWith(root + path.sep)) throw Error('Path leaves its authorized study directory.');
  return resolved;
}

async function sourceModules() {
  const manifestBytes = await readFile(path.join(HERE, 'source_manifest.json'));
  const manifest = JSON.parse(manifestBytes);
  for (const file of manifest.files) {
    const bytes = await readFile(contained(HERE, file.path));
    assert.equal(bytes.length, file.bytes, 'Vendored source length changed: ' + file.path);
    assert.equal(sha(bytes), file.sha256, 'Vendored source hash changed: ' + file.path);
  }
  const load = name => import(pathToFileURL(path.join(HERE, 'vendor/docs/assets', name)));
  const [insight, discovery, seed, plan, project, packages, mark, qualification] = await Promise.all([
    load('insight/engine.mjs'), load('discovery/engine.mjs'), load('ascension/crypto.mjs'),
    load('nova-studio/plan.mjs'), load('nova-studio/cycle.mjs'), load('nova-studio/package.mjs'),
    load('ascension-wallet/protocol.mjs'), load('ascension-wallet/qualified-profiles.mjs'),
  ]);
  assert.equal(qualification.QUALIFIED_PROFILES.length, 0, 'The original empty qualification registry must remain unchanged.');
  return { manifest, manifestHash: sha(manifestBytes), insight, discovery, seed, plan, project, packages, mark };
}

async function rejection(operation) {
  try {
    await operation();
  } catch (error) {
    return { refused: true, reason: String(error.message || error) };
  }
  return { refused: false, reason: null };
}

async function provenance(records) {
  if (!Array.isArray(records)) throw Error('provenance_files must be a list of supplied public record paths and SHA-256 digests.');
  const checked = [];
  for (const record of records) {
    if (!record || typeof record.path !== 'string' || !/^[0-9a-f]{64}$/.test(record.sha256)) {
      throw Error('Each provenance record needs a study-relative path and exact SHA-256.');
    }
    const filename = await realpath(contained(STUDY, record.path));
    contained(STUDY, filename);
    const info = await stat(filename);
    if (!info.isFile() || info.size > 2000000) throw Error('Each provenance reference must be a public file no larger than 2 MB.');
    const bytes = await readFile(filename);
    assert.equal(sha(bytes), record.sha256, 'Public provenance record changed: ' + record.path);
    checked.push({ path: record.path, sha256: record.sha256, bytes: bytes.length });
  }
  return checked;
}

function validateInput(input) {
  if (input?.schema !== 'agialpha.opportunity-construction.venture.v1') throw Error('Unsupported research venture input schema.');
  if (input.evidence_scope !== 'offline-research' || input.publication_safe !== true) {
    throw Error('This adapter accepts only explicitly public, offline research inputs.');
  }
  if (input.protocol_amounts !== 'unfunded-encoding-only') {
    throw Error('Protocol bounties and arithmetic must be labelled unfunded encoding only.');
  }
  if (typeof input.title !== 'string' || !input.title.trim()) throw Error('A real selected-opportunity title is required.');
  if (!input.opportunity || Array.isArray(input.opportunity) || typeof input.opportunity !== 'object') {
    throw Error('Supply the actual selected Opportunity object.');
  }
  if (!Array.isArray(input.fusion_plan_jobs) || !input.fusion_plan_jobs.length) {
    throw Error('Supply at least one actual work specification in the existing FusionPlan schema.');
  }
}

async function main() {
  const options = args(process.argv.slice(2));
  const modules = await sourceModules();
  const { insight, discovery, seed, plan, project, packages, mark } = modules;
  const inputPath = await realpath(contained(STUDY, options.input));
  contained(STUDY, inputPath);
  const inputBytes = await readFile(inputPath);
  const input = packages.strictJSON(inputBytes.toString('utf8'), 250000);
  validateInput(input);
  const publicRecords = await provenance(input.provenance_files || []);
  const inputHash = sha(inputBytes);
  const opportunityHash = await seed.hashObject(input.opportunity);
  const sourceHash = modules.manifestHash;
  const checks = [];
  const checked = (name, condition) => {
    assert.ok(condition, name);
    checks.push({ name, passed: true });
  };

  // Existing parsers/digests preserve the supplied object. They do not discover it or validate its truth.
  const portableOpportunity = insight.serializePortableJSON(input.opportunity);
  const parsedOpportunity = discovery.parse(portableOpportunity);
  checked('Actual opportunity survives existing Insight serialization and Discovery parsing',
    seed.canonicalJSON(parsedOpportunity) === seed.canonicalJSON(input.opportunity));
  checked('Existing canonical digest agrees with independent SHA-256 bytes',
    await discovery.digest(parsedOpportunity) === sha(encoder.encode(discovery.canonical(input.opportunity))));
  const insightRefusal = await rejection(() => insight.buildEvidence(input.opportunity, insight.DEFAULT_CONFIG));
  checked('Insight scheduling engine refuses a generic opportunity outside its schema', insightRefusal.refused);
  const insightBoundary = {
    function: 'buildEvidence(actualOpportunity, DEFAULT_CONFIG)',
    result: insightRefusal,
    interpretation: 'Expected schema boundary, not an opportunity failure or a discovery performance score.',
    scope: 'Insight Atlas validates its supplied local scheduling model; it cannot validate generic opportunity truth.',
    chronicle_promotions: 0,
  };

  const fusionPlan = plan.compilePlan(input.fusion_plan_jobs);
  checked('Existing FusionPlan compiler and verifier agree exactly',
    seed.canonicalJSON(plan.verifyPlan(fusionPlan)) === seed.canonicalJSON(fusionPlan));
  const changedPlan = clone(fusionPlan);
  const originalGoal = changedPlan.jobs[0].spec.goal;
  changedPlan.jobs[0].spec.goal = (originalGoal[0] === 'X' ? 'Y' : 'X') + originalGoal.slice(1);
  const changedPlanRefusal = await rejection(() => plan.verifyPlan(changedPlan));
  checked('Changing the committed work goal is refused', changedPlanRefusal.refused);
  const changedBounty = clone(fusionPlan);
  changedBounty.totalBounty = (BigInt(changedBounty.totalBounty) + 1n).toString();
  checked('Changing the committed plan total is refused', (await rejection(() => plan.verifyPlan(changedBounty))).refused);

  const nativeProject = await project.createProject(null, { title: input.title, opportunity: input.opportunity });
  const reopenedProject = await project.validateProject(nativeProject);
  checked('Nova createProject retains the complete actual Opportunity',
    seed.canonicalJSON(reopenedProject.opportunity) === seed.canonicalJSON(input.opportunity));
  const credentialInjection = clone(nativeProject);
  credentialInjection.opportunity.active_grant = 'fabricated imported authority';
  checked('Native project validation refuses imported authority fields',
    (await rejection(() => project.validateProject(credentialInjection))).refused);

  const genome = {
    schema: 'agialpha.novaseed.genome.v1',
    study_scope: 'Public offline research capsule; unminted and unfunded; no operational authority.',
    project: nativeProject,
    onchain_plan: fusionPlan,
    provenance: { input_sha256: inputHash, opportunity_sha256: opportunityHash, source_manifest_sha256: sourceHash, public_records: publicRecords },
  };
  const capsule = await seed.sealSeed(genome, PUBLIC_FIXTURE_PASSPHRASE);
  const opened = await seed.openSeed(capsule, PUBLIC_FIXTURE_PASSPHRASE);
  checked('Existing Nova-Seed encryption/decryption preserves the exact complete genome',
    seed.canonicalJSON(opened) === seed.canonicalJSON(genome));
  checked('Recovered Opportunity and plan bind to the same payload',
    await seed.hashObject(opened.project.opportunity) === opportunityHash &&
    plan.verifyPlan(opened.onchain_plan).planRoot === fusionPlan.planRoot);
  checked('Native project validator accepts the decrypted project unchanged',
    seed.canonicalJSON(await project.validateProject(opened.project)) === seed.canonicalJSON(nativeProject));
  checked('Wrong research passphrase is refused',
    (await rejection(() => seed.openSeed(capsule, PUBLIC_FIXTURE_PASSPHRASE + '-wrong'))).refused);
  const changedCiphertext = clone(capsule);
  changedCiphertext.ciphertext = (changedCiphertext.ciphertext[0] === 'A' ? 'B' : 'A') + changedCiphertext.ciphertext.slice(1);
  checked('Altered encrypted bytes are refused',
    (await rejection(() => seed.openSeed(changedCiphertext, PUBLIC_FIXTURE_PASSPHRASE))).refused);
  const nativeState = project.projectCycleState(nativeProject);
  checked('Recovered project has no observed settlement or current execution authority',
    nativeState.settlement === 'not-observed' && nativeState.runtime === 'requires-current-authorization' && nativeState.fresh === false);

  let markInspection = {
    executed: false,
    reason: 'No explicit MARK arithmetic fixture supplied.',
    usd_transferred: '0',
    token_transferred: '0',
    economic_value_estimate: null,
  };
  if (input.mark_curve_fixture !== undefined) {
    const fixture = input.mark_curve_fixture;
    if (fixture?.scope !== 'unfunded-integer-arithmetic-only' || fixture.usd_equivalent !== null) {
      throw Error('MARK fixture must explicitly have no USD equivalent or commercial meaning.');
    }
    for (const key of ['supply', 'count', 'base', 'slope']) {
      if (typeof fixture[key] !== 'string' || !/^(0|[1-9][0-9]*)$/.test(fixture[key])) throw Error('MARK quantities must be canonical integer strings.');
    }
    const { supply, count, base, slope } = fixture;
    const quoted = mark.curve(supply, count, base, slope);
    const [s, n, b, m] = [supply, count, base, slope].map(BigInt);
    const independentlyComputed = n * b + m * n * (2n * s + n - (n ? 1n : 0n)) / 2n;
    checked('Existing MARK integer curve matches an independent arithmetic calculation', quoted === independentlyComputed);
    markInspection = {
      executed: true, function: 'curve', input: fixture, result_base_units: quoted.toString(),
      result_token_display: mark.tokens(quoted), token: 'AGIALPHA', decimals: 18,
      interpretation: 'Unfunded protocol arithmetic. No buyer price, funding commitment, token valuation, demand, profit or receipts follow.',
      usd_transferred: '0', token_transferred: '0', economic_value_estimate: null,
    };
  }

  let discoveryDossier = null;
  if (input.discovery_scenario !== undefined) {
    discoveryDossier = await discovery.evaluate(input.discovery_scenario);
    checked('Optional supplied Discovery priority dossier replays exactly',
      discovery.canonical(await discovery.verify(discoveryDossier)) === discovery.canonical(discoveryDossier));
  }
  const output = contained(HERE, path.relative(HERE, contained(STUDY, options.output)));
  await mkdir(path.dirname(output), { recursive: true });
  await mkdir(output); // Preserve all prior runs: explicit fresh destination is required.
  const artifacts = {};
  async function save(name, value) {
    const bytes = typeof value === 'string' ? value : json(value);
    await writeFile(path.join(output, name), bytes, { flag: 'wx' });
    artifacts[name] = { bytes: Buffer.byteLength(bytes), sha256: sha(bytes) };
  }
  await save('venture.input.json', inputBytes.toString('utf8'));
  await save('opportunity.json', portableOpportunity);
  await save('fusion-plan.json', fusionPlan);
  await save('nova-project.json', nativeProject);
  await save('nova-genome.public.json', genome);
  await save('nova-seed.sealed.json', capsule);
  await save('insight-boundary.json', insightBoundary);
  await save('mark-inspection.json', markInspection);
  if (discoveryDossier) await save('discovery-dossier.json', discoveryDossier);
  const evidence = {
    schema: 'agialpha.opportunity-construction.integration-evidence.v1',
    status: 'passed', observed_at: new Date().toISOString(), runtime: process.version,
    source_commit: modules.manifest.commit, source_manifest_sha256: sourceHash,
    input_path: path.relative(STUDY, inputPath), input_sha256: inputHash,
    opportunity_sha256: opportunityHash, plan_root: fusionPlan.planRoot,
    capsule_object_sha256: await seed.hashObject(capsule), genome_object_sha256: await seed.hashObject(genome),
    project_id: nativeProject.projectId, cycle_id: nativeProject.activeCycleId,
    provenance_files: publicRecords, native_project_state: nativeState,
    checks, expected_insight_refusal: insightRefusal,
    optional_discovery_priority_evaluation: discoveryDossier !== null,
    qualification_registry_entries: 0,
    external_effects: { provider_calls: 0, wallet_requests: 0, network_requests: 0, mint_calls: 0, trade_calls: 0, usd_transferred: '0', token_transferred: '0' },
    evidence_boundary: [
      'The actual hosted blind-search records and construction establish the source of the opportunity; this harness does not discover or substantiate it.',
      'Native object creation, schema validation, encryption round trips and commitments are actual local executions, not commercial or scientific acceptance.',
      'The native project has no attached deployment package, minted seed or posted jobs. The compatible standalone genome binds its project and plan.',
      'FusionPlan token amounts are unfunded encoding fixtures. MARK arithmetic has no USD equivalent and supplies no economic result.',
      'Any optional Discovery priorities describe supplied assumptions, not probabilities, value or authenticated evidence.',
      'The public fixture passphrase provides reproducibility, not confidentiality. Random capsule salt, IV, blind and project UUIDs vary on rerun.',
      'REUSE stable structure; RECHECK the next mission; REGRANT authority separately. No existing validator role changes.',
    ],
    preserved_namespaces: { businesses: '*.alpha.agi.eth', ascension_agents: '*.alpha.agent.agi.eth', validators: '*.alpha.club.agi.eth', other_agent_interfaces: '*.agent.agi.eth is a distinct interface; no live ENS check here.' },
    public_fixture_passphrase: PUBLIC_FIXTURE_PASSPHRASE,
    artifacts,
  };
  await writeFile(path.join(output, 'evidence.json'), json(evidence), { flag: 'wx' });
  process.stdout.write(json({ status: evidence.status, output: path.relative(STUDY, output), input_sha256: inputHash,
    opportunity_sha256: opportunityHash, plan_root: fusionPlan.planRoot, source_commit: evidence.source_commit,
    scientific_discovery_claim: false, commercial_acceptance_claim: false }));
}

main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1; });
