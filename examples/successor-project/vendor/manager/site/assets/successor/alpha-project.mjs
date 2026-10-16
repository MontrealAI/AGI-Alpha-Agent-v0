import { fail, keys, canonical, parseStrict, sha256, publicOnly } from './safe.mjs';
import { defaultMission, csvRows, validateMission } from './missions.mjs';
import { createSystem, runCandidate, chooseCandidate, exportCapsule, inspectCapsule, recordPlan } from './model.mjs';
import { prepareImprovement } from './jobs.mjs';
import { validateProject as validateNativeProject } from './vendor/alpha-project/examples/successor-project/engine.mjs';

export const ALPHA_SOURCE = Object.freeze({ repository: 'MontrealAI/AGI-Alpha-Agent-v0', commit: '7c410d3d61d5d6bba5354307e1784dba2b3aa177', tree: 'e80b1dc06317d939e3dd22d2db063a7f1706ddcb' });
export const MAPPING = 'alpha-public-data-to-manager-rows/v1';
const MAX = 4_000_000;
export async function validateBrowserAlpha(raw) {
  parseStrict(raw, 2_000_000); publicOnly(raw);
  try { return await validateNativeProject(raw); } catch { fail(false, 'ALPHA_NATIVE_INVALID'); }
}
function mapMission(project, language) {
  fail(['en', 'fr'].includes(language), 'LANGUAGE');
  const cycle = project.cycles.at(-1), record = parseStrict(cycle.records.at(-1).bytes, 2_000_000);
  fail(record.spec.family === 'public-data' && cycle.mapping.choices.family === 'public-data', 'ALPHA_MAPPING_UNAVAILABLE');
  fail(cycle.mapping.choices.duplicatePolicy === 'sum-all-rows-no-deduplication' && cycle.mapping.choices.unitPolicy === 'unchanged-integer-units', 'ALPHA_MAPPING_POLICY');
  const rows = csvRows(record.spec.inputs.csv, 2); fail(canonical(rows.shift()) === canonical(['group', 'amount']), 'ALPHA_CSV_HEADER');
  // Native Alpha validates integer amounts first. Assign a distinct row identity to
  // every source row, so Manager's ID deduplication never merges equal Alpha rows.
  const input = rows.map((row, index) => { fail(row.length === 2 && /^-?(?:0|[1-9]\d*)$/.test(row[1]), 'ALPHA_INTEGER_MAPPING'); return { id: `alpha-row-${index + 1}`, category: row[0], value: row[1] }; });
  const mission = defaultMission('analyst', language), fr = language === 'fr';
  mission.name = fr ? 'Projet Alpha — vérification des totaux' : 'Alpha project — check category totals';
  mission.purpose = fr ? 'Recalculer les totaux des mêmes lignes sources, sans modifier les unités ni fusionner les doublons.' : 'Recompute totals from the same source rows, preserving units and every duplicate row.';
  mission.input = canonical(input);
  mission.rights = `${cycle.mapping.choices.dataRights}; ${record.spec.inputs.unit}. ` + (fr ? 'Déclaration fournie, non authentifiée; confirmer les droits avant publication.' : 'Supplied declaration, unauthenticated; confirm rights before publication.');
  validateMission(mission); return mission;
}
function projectIdentity(project) { const cycle = project.cycles.at(-1); return { projectId: project.projectId, cycleId: cycle.cycleId, revision: project.revision, projectDigest: project.projectDigest }; }
async function seal(body) { const raw = canonical({ ...body, sha256: await sha256(body) }); fail(new TextEncoder().encode(raw).length <= MAX, 'TRANSFER_SIZE'); return raw; }
export async function importAlphaProject(raw, { language, mappingAcknowledgement }, context) {
  fail(mappingAcknowledgement === MAPPING, 'EXPLICIT_MAPPING_REQUIRED');
  const project = await context.validateNative(raw), mission = mapMission(project, language);
  const capsule = await exportCapsule(await createSystem(mission), context.sourceManifest);
  return seal({ schema: 'agijobmanager/alpha-project-transfer/v1', source: ALPHA_SOURCE, managerSource: context.managerSource, project: projectIdentity(project), original: { raw, sha256: await sha256(raw) }, mapping: { id: MAPPING, language, rowIdentity: 'source-row-position', units: 'unchanged', duplicates: 'every-source-row' }, history: [{ kind: 'imported', capsule, sha256: await sha256(capsule) }], authority: 'none', qualification: 'not-evaluated', settlement: 'not-connected' });
}
export async function inspectAlphaProject(raw, context) {
  const transfer = parseStrict(raw, MAX);
  keys(transfer, ['schema', 'source', 'managerSource', 'project', 'original', 'mapping', 'history', 'authority', 'qualification', 'settlement', 'sha256'], 'TRANSFER_FIELDS');
  const { sha256: checksum, ...body } = transfer;
  fail(checksum === await sha256(body), 'TRANSFER_CHANGED');
  fail(transfer.schema === 'agijobmanager/alpha-project-transfer/v1' && transfer.authority === 'none' && transfer.qualification === 'not-evaluated' && transfer.settlement === 'not-connected', 'TRANSFER_AUTHORITY');
  fail(canonical(transfer.source) === canonical(ALPHA_SOURCE), 'ALPHA_SOURCE_PIN');
  fail(canonical(transfer.managerSource) === canonical(context.managerSource), 'MANAGER_SOURCE_DRIFT');
  keys(transfer.original, ['raw', 'sha256']); fail(transfer.original.sha256 === await sha256(transfer.original.raw), 'ORIGINAL_CHANGED');
  const project = await context.validateNative(transfer.original.raw);
  fail(canonical(transfer.project) === canonical(projectIdentity(project)), 'PROJECT_CHANGED');
  const mission = mapMission(project, transfer.mapping.language);
  fail(canonical(transfer.mapping) === canonical({ id: MAPPING, language: mission.language, rowIdentity: 'source-row-position', units: 'unchanged', duplicates: 'every-source-row' }), 'MAPPING_CHANGED');
  fail(Array.isArray(transfer.history) && transfer.history.length > 0 && transfer.history.length <= 8, 'TRANSFER_HISTORY');
  let prior;
  for (const [index, entry] of transfer.history.entries()) {
    keys(entry, ['kind', 'capsule', 'sha256']); fail(entry.sha256 === await sha256(entry.capsule), 'CAPSULE_CHANGED');
    fail(index === 0 ? entry.kind === 'imported' : ['local-run', 'selected-for-usdc-draft'].includes(entry.kind), 'TRANSFER_HISTORY');
    const inspected = await inspectCapsule(entry.capsule), state = inspected.capsule.payload.state;
    fail(canonical(inspected.capsule.payload.sourceManifest) === canonical(context.sourceManifest), 'MANAGER_SOURCE_DRIFT');
    fail(canonical(state.mission) === canonical(mission), 'MISSION_CHANGED');
    if (prior) {
      fail(state.chronicle.length > prior.chronicle.length && canonical(state.chronicle.slice(0, prior.chronicle.length)) === canonical(prior.chronicle), 'HISTORY_REWRITTEN');
      const plan = state.plans.find(p => p.commitment === state.chronicle.at(-1).subject);
      const expected = await nextState(prior, entry.kind, plan?.draft.fields.budget, context);
      fail(canonical(state) === canonical(expected), 'TRANSITION_CHANGED');
    }
    else fail(canonical(state) === canonical(await createSystem(mission)), 'IMPORT_EXECUTION_CLAIM');
    prior = state;
  }
  return { transfer, state: prior, originalProject: project };
}
export async function advanceAlphaProject(raw, { action, budget }, context) {
  const { transfer, state } = await inspectAlphaProject(raw, context);
  fail(transfer.history.length < 8, 'TRANSFER_HISTORY'); const manifest = context.sourceManifest;
  fail(['run', 'select-and-draft'].includes(action), 'TRANSFER_ACTION');
  fail(action !== 'run' || transfer.history.length < 7, 'TRANSFER_DRAFT_RESERVE');
  const kind = action === 'run' ? 'local-run' : 'selected-for-usdc-draft';
  const next = await nextState(state, kind, budget, context);
  const capsule = await exportCapsule(next, manifest);
  transfer.history.push({ kind, capsule, sha256: await sha256(capsule) }); delete transfer.sha256;
  const result = await seal(transfer); await inspectAlphaProject(result, context); return result;
}

async function nextState(state, kind, budget, context) {
  if (kind === 'local-run') {
    fail(state.active === null && state.plans.length === 0, 'EXPLICIT_NEW_CYCLE_REQUIRED');
    return (await runCandidate(state, 'baseline', context.sourceManifest.engineSha256)).state;
  }
  fail(kind === 'selected-for-usdc-draft' && state.candidates.length > 0, 'RUN_REQUIRED');
  const next = await chooseCandidate(state, state.candidates.at(-1).id, 'keep');
  return recordPlan(next, await prepareImprovement(next, { budget, requested: next.mission.purpose }));
}
