import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash, webcrypto } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { requireResearchOnly } from './enforce_research_only.mjs';

globalThis.crypto ??= webcrypto;
const here = path.dirname(fileURLToPath(import.meta.url));
const [rootArg, inputArg, outputArg] = process.argv.slice(2);
if (!rootArg || !inputArg || !outputArg) throw Error('Usage: node native_bridge.mjs SOURCE_ROOT INPUT_JSON NEW_OUTPUT_DIR');
const root = path.resolve(rootArg), output = path.resolve(outputArg);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const pins = JSON.parse(await fs.readFile(path.join(here, 'native_source_pins.json'), 'utf8'));
for (const item of pins.files) {
  const bytes = await fs.readFile(path.join(root, item.path));
  const blob = createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${bytes.length}\0`), bytes])).digest('hex');
  if (bytes.length !== item.bytes || sha(bytes) !== item.sha256 || blob !== item.git_blob)
    throw Error(`Pinned native source differs: ${item.path}`);
}
const nativeImport = relative => import(pathToFileURL(path.join(root, relative)).href);
const insight = await nativeImport('docs/assets/insight/engine.mjs');
const ascension = await nativeImport('docs/assets/ascension/engine.mjs');
const crypto = await nativeImport('docs/assets/ascension/crypto.mjs');
const fusion = await nativeImport('docs/assets/nova-studio/plan.mjs');
const inputBytes = await fs.readFile(inputArg);
const input = JSON.parse(inputBytes);
requireResearchOnly(input.qualification);
if (input.schema !== 'agialpha.study.native-bridge-input.v1') throw Error('Unexpected research handoff schema');
for (const name of ['witness', 'rights', 'uncertainties', 'next_experiment', 'discovery_record_sha256'])
  if (!input[name]) throw Error(`Missing research field: ${name}`);
if (!/^[0-9a-f]{64}$/.test(input.discovery_record_sha256)) throw Error('Discovery digest must identify real bytes');
if (typeof input.discovery_record_path !== 'string') throw Error('A local discovery record path is required');
const discoveryBytes = await fs.readFile(path.resolve(path.dirname(inputArg), input.discovery_record_path));
if (sha(discoveryBytes) !== input.discovery_record_sha256) throw Error('Discovery record bytes differ from the committed record');
const researchRecord = JSON.parse(discoveryBytes);
if (researchRecord.new_discovery !== false || researchRecord.qualified_venture !== false || researchRecord.decision !== 'reject-known-construction') throw Error('Rejected research verdict was changed');
requireResearchOnly(researchRecord.qualification);
if (JSON.stringify(researchRecord.qualification) !== JSON.stringify(input.qualification)) throw Error('Input qualification differs from frozen research record');
if (!Array.isArray(input.candidates) || !input.candidates.length) throw Error('No discovered candidate records');
const selected = input.candidates.find(item => item.id === input.selected_id);
if (!selected) throw Error('Selected candidate must be in the discovery record');
if (selected.id !== researchRecord.candidate_id || selected.research_status !== 'rejected-known-construction') throw Error('Only the rejected known construction may enter this handoff');
if (!Array.isArray(input.milestones) || !input.milestones.length) throw Error('No executable milestones');
const allIds = new Set(input.milestones.map(item => item.id));
if (allIds.size !== input.milestones.length) throw Error('Milestone IDs must be unique');
const completed = new Set();
for (const milestone of input.milestones) {
  if (!Array.isArray(milestone.depends_on) || milestone.depends_on.some(id => !completed.has(id)))
    throw Error('Milestones must be topologically ordered with prior dependencies');
  if (!Number.isFinite(milestone.cost_limit_usd) || milestone.cost_limit_usd < 0 ||
      !Array.isArray(milestone.permissions) || !milestone.acceptance || !milestone.falsifier || !milestone.command)
    throw Error('Milestone needs a bounded budget, permissions, executable command, acceptance and falsifier');
  completed.add(milestone.id);
}
const fixtureTasks = prefix => Array.from({length:4}, (_, i) => ({
  id:`${prefix}-${i}`, arrival:0, minutes:1, review_minutes:1, due:10, valid:i !== 3
}));
const weights = Object.fromEntries(insight.SECTORS.map(sector => [sector, sector === selected.sector ? 10000 : 0]));
const scenario = {
  schema:'agialpha.insight.scenario.v1', id:input.id, title:input.title,
  question:input.question, envelope_usd:'0', weights_bps:weights, sources:input.sources,
  claims:input.candidates.map(({id,sector,title,hypothesis,source_ids,metric,target,evidence_needed}) =>
    ({id,sector,title,hypothesis,source_ids,metric,target,evidence_needed})),
  workload:{training:fixtureTasks('schema-training'), holdout:fixtureTasks('schema-holdout')}
};
const dossier = insight.buildDossier(scenario, insight.DEFAULT_CONFIG);
const sourceText = input.sources.filter(s => selected.source_ids.includes(s.id)).map(s => `${s.title}: ${s.text}`).join('\n');
const planning = input.planning_assumptions ?? {research:1, delivery:1, verification:1};
const analysis = ascension.analyseScenario({
  schema:'agialpha.ascension.scenario.v1', id:input.id, title:input.title,
  goal:input.goal, description:input.question, unit:'schema fixture; no economic value', budget:1, risk_limit:0,
  opportunities:[{id:selected.id, title:selected.title, sector:selected.sector, evidence:sourceText,
    cost:1, value:1, risk:0, effort:[planning.research,planning.delivery,planning.verification]}]
});
const plan = fusion.compilePlan(input.milestones.map(item => ({
  goal:item.goal, successMetric:item.acceptance, bounty:'100', duration:item.duration_seconds, priceWeight:5000
})));
fusion.verifyPlan(plan);
const genome = ascension.makeGenome(analysis);
genome.study = {
  schema:'agialpha.study.provenance.v1', input_sha256:sha(inputBytes),
  qualification:input.qualification,
  discovery_record_sha256:input.discovery_record_sha256,
  opportunity:selected, sources:input.sources, transformation_witness:input.witness,
  rights:input.rights, uncertainties:input.uncertainties, next_experiment:input.next_experiment,
  executable_milestones:input.milestones, fusion_plan:plan,
  authorization:'Research artifact only. No production admission, ENS assertion, mint, listing, funding or settlement.',
  native_semantics:'Insight processes supplied candidates. Its mandatory workload and Ascension unit allocation are schema fixtures, excluded from scientific outcomes and commercial economics.'
};
const passphrase = 'public-research-fixture-passphrase';
const capsule = await crypto.sealSeed(genome, passphrase);
const recovered = await crypto.openSeed(capsule, passphrase);
if (crypto.canonicalJSON(recovered) !== crypto.canonicalJSON(genome)) throw Error('Recovered genome mismatch');
const checks = [{name:'pinned_native_source_closure',passed:true}, {name:'discovery_record_bytes_bound',passed:true},
  {name:'native_insight_dossier',passed:dossier.schema === 'agialpha.insight.dossier.v1'},
  {name:'economic_value_not_asserted',passed:dossier.economic_value_verified_usd === '0'},
  {name:'native_novaseed_roundtrip',passed:true}, {name:'native_fusionplan_proofs',passed:true}];
async function refusal(name, action) {
  try { await action(); } catch (error) { checks.push({name,passed:true,refusal:String(error.message)}); return; }
  throw Error(`Expected refusal missing: ${name}`);
}
const changedPlan = structuredClone(plan); changedPlan.jobs[0].spec.goal += ' altered';
await refusal('tampered_plan_refused', () => fusion.verifyPlan(changedPlan));
const unknownSource = structuredClone(scenario); unknownSource.claims[0].source_ids = ['absent-source'];
await refusal('unknown_claim_source_refused', () => insight.buildDossier(unknownSource, insight.DEFAULT_CONFIG));
const changedCapsule = structuredClone(capsule); changedCapsule.commitment = '0'.repeat(64);
await refusal('tampered_capsule_refused', () => crypto.openSeed(changedCapsule, passphrase));
await refusal('wrong_fixture_passphrase_refused', () => crypto.openSeed(capsule, 'different-research-fixture-passphrase'));
const mark = {
  status:'not-qualified-research-inspection', source_function:'docs/assets/ascension/engine.mjs:curveQuote',
  quote:ascension.curveQuote({supply:0,lots:3,base:'1',slope:'0.1'}),
  eligible_venture:false, authorized_transaction:false, revenue_usd:0,
  meaning:'Actual execution of existing quote arithmetic with hypothetical token units; no funding, market admission or trade.'
};
checks.push({name:'mark_quote_arithmetic_fixture',passed:mark.quote.amount === '3.3'});
for (const field of ['qualified_venture','new_discovery','authorized_transaction','minted','listed','live_identity_asserted','execution_authority']) {
  const q=structuredClone(input.qualification);q[field]=true;
  await refusal('research_guard_refuses_'+field, () => requireResearchOnly(q));
}
const cash=structuredClone(input.qualification);cash.collected_cash_usd=1;
await refusal('research_guard_refuses_unobserved_cash', () => requireResearchOnly(cash));
if (checks.some(check => !check.passed)) throw Error('A native integration check failed');
await fs.mkdir(output);
const artifacts = {};
async function save(name, value) {
  const bytes = Buffer.from(JSON.stringify(value,null,2)+'\n');
  await fs.writeFile(path.join(output,name),bytes,{flag:'wx'});
  artifacts[name] = {bytes:bytes.length,sha256:sha(bytes)};
}
await save('insight_dossier.json',dossier);
await save('nova_seed_genome.json',genome);
await save('nova_seed_sealed.json',capsule);
await save('fusion_plan.json',plan);
await save('mark_inspection.json',mark);
await save('qualification_manifest.json',{
  schema:'agialpha.research-only-output-manifest.v1', qualification:input.qualification,
  source_commit:pins.source_commit, research_record_sha256:input.discovery_record_sha256,
  artifact_bindings:structuredClone(artifacts),
  enforcement:'Companion local guard checks statuses and exact bytes; the native schema does not decide scientific novelty or grant production eligibility.',
  native_scope:'Existing main source executed locally. New guard is an adapter, not a production registry or permission service.'
});
const receipt = {
  schema:'agialpha.study.native-bridge-receipt.v1',source:pins, input_sha256:sha(inputBytes),
  node_version:process.version,genome_sha256:await crypto.hashObject(genome),plan_root:plan.planRoot,
  qualification:input.qualification,checks,artifacts,observed:'Local actual source execution and cryptographic roundtrip',
  fixtures:'Mandatory Insight workload, single-item Ascension allocation, token bounties, MARK quote and public capsule passphrase',
  scope:'Research handoff, no production-protected capability admission and no live identity or commercial transaction',
  reproduction:'Random crypto salts/IVs/blind produce new sealed bytes. Recovered payload, plan root and scientific bindings must agree.'
};
await fs.writeFile(path.join(output,'native_receipt.json'),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({output,checks:checks.length,passed:checks.filter(c=>c.passed).length,
  genome_sha256:receipt.genome_sha256,plan_root:receipt.plan_root})+'\n');
