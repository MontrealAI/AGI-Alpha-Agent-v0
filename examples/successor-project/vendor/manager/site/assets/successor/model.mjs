import { fail, keys, text, canonical, clone, sha256, isHash, parseStrict, LIMITS, safePath, publicOnly } from './safe.mjs';
import { ENGINE, validateMission, executeMission } from './missions.mjs';
import { executeMission as executeLegacy } from './legacy-missions.mjs';
import { checkArtifacts as checkLegacy } from './legacy-checker.mjs';
import { checkArtifacts } from './checker.mjs';
import { validateImprovement } from './jobs.mjs';

export const SCHEMA = 'agijobmanager/successor-capsule/v1';
export const ARCHIVE_SCHEMA = 'agijobmanager/successor-capsule/v2';
export const STORAGE_KEY = 'agijobmanager_successor_capsule_v1';
export const EVIDENCE_BOUNDARY = { evidence: 'local-measurement', payment: 'unfunded', qualification: 'not-evaluated', authority: 'none' };
export function historyEvents(state) {
  return [...(state.archives || []).flatMap(segment => segment.events), ...state.chronicle];
}
export function historyCapacity(state) {
  return { remaining: LIMITS.events - state.chronicle.length, archivedSegments: (state.archives || []).length, maximumSegments: LIMITS.historySegments, totalEvents: historyEvents(state).length };
}
export async function appendEvent(state, action, subject) {
  fail(state.chronicle.length < LIMITS.events, 'HISTORY_LIMIT'); text(subject, 2000);
  const events = historyEvents(state);
  const record = { sequence: events.length, action, subject, previous: events.at(-1)?.sha256 || null };
  const event = { ...record, sha256: await sha256(record) };
  const payload = { state: { ...state, chronicle: [...state.chronicle, event] }, sourceManifest: null };
  fail(new TextEncoder().encode(canonical({ format: state.schema === ARCHIVE_SCHEMA ? 'successor-portable/2' : 'successor-portable/1', payload, sha256: '0'.repeat(64) })).length <= LIMITS.capsule, 'CAPSULE_CAPACITY');
  state.chronicle.push(event); return state;
}
export async function createSystem(mission) {
  validateMission(mission);
  const state = { schema: SCHEMA, engine: ENGINE, mission: clone(mission), candidates: [], plans: [], active: null, chronicle: [], ...EVIDENCE_BOUNDARY };
  await appendEvent(state, 'mission-defined', await sha256(mission)); return state;
}
export async function freezeCandidate(mission, variant, sourceIdentity, engine = ENGINE) {
  validateMission(mission); fail(isHash(sourceIdentity), 'SOURCE_IDENTITY');
  const specification = clone(mission), specificationSha256 = await sha256(specification);
  // The specification/configuration is frozen before execution/checking.
  const manifest = { engine, sourceSha256: sourceIdentity, specificationSha256, variant, tools: ['local-code'], permissions: [], provider: null };
  const { files, gaps } = (engine === 'successor-local/1' ? executeLegacy : executeMission)(specification, variant);
  const artifacts = await Promise.all(files.map(async f => ({ ...f, sha256: await sha256(f.content) })));
  const result = { manifest, files: artifacts, gaps, checker: (engine === 'successor-local/1' ? checkLegacy : checkArtifacts)(specification, variant, files) };
  return { ...result, id: await sha256(result) };
}
export async function runCandidate(state, variant, sourceIdentity) {
  fail(state.chronicle.length < LIMITS.events, 'HISTORY_LIMIT');
  const next = clone(state);
  let candidate;
  try { candidate = await freezeCandidate(next.mission, variant, sourceIdentity, next.engine); }
  catch (error) {
    const code = /^[A-Z_]{1,80}$/.test(error.code || '') ? error.code : 'RUN_FAILED';
    await appendEvent(next, 'run-failed', code);
    error.failureState = next; throw error;
  }
  if (!next.candidates.some(c => c.id === candidate.id)) { fail(next.candidates.length < LIMITS.candidates, 'CANDIDATE_LIMIT'); next.candidates.push(candidate); }
  await appendEvent(next, 'candidate-checked', candidate.id);
  return { state: next, candidate };
}
export async function recordPlan(state, plan) {
  await validateImprovement(plan);
  fail(plan.missionSha256 === await sha256(state.mission), 'PLAN_MISSION');
  const next = clone(state);
  if (!next.plans.some(p => p.commitment === plan.commitment)) {
    fail(next.plans.length < 12, 'PLAN_LIMIT'); next.plans.push(clone(plan));
  }
  await appendEvent(next, 'plan-prepared', plan.commitment); return next;
}
export function compareCandidates(incumbent, proposed) {
  fail(incumbent && proposed, 'CANDIDATE_REQUIRED');
  fail(incumbent.manifest.specificationSha256 === proposed.manifest.specificationSha256, 'COMPARISON_SCOPE');
  const before = incumbent.gaps.length, after = proposed.gaps.length;
  const outcome = !proposed.checker.passed ? 'regression' : before > after ? 'improvement' : before === after ? 'tie' : 'regression';
  return { incumbent: incumbent.id, proposed: proposed.id, outcome, recommendation: outcome === 'improvement' ? 'review-choice' : 'retain', evidence: 'local-measurement', independentController: false, protectedEvaluation: false, generalSuperiority: false };
}
export async function chooseCandidate(state, id, decision) {
  fail(['keep', 'replace', 'rollback'].includes(decision), 'DECISION');
  const candidate = state.candidates.find(c => c.id === id); fail(candidate?.checker.passed, 'CANDIDATE_REJECTED');
  if (decision === 'keep') fail(state.active === null || state.active === id, 'RETAIN_INCUMBENT');
  if (decision === 'rollback') fail(historyEvents(state).some(e => ['keep', 'replace', 'rollback'].includes(e.action) && e.subject === id), 'NO_PREVIOUS_VERSION');
  if (decision === 'replace') {
    const active = state.candidates.find(c => c.id === state.active);
    fail(active && compareCandidates(active, candidate).outcome === 'improvement', 'RETAIN_INCUMBENT');
  }
  const next = clone(state); next.active = id; await appendEvent(next, decision, id); return next;
}
export async function validateState(value, { reproduce = true } = {}) {
  const segmented = value?.schema === ARCHIVE_SCHEMA;
  keys(value, ['schema', 'engine', 'mission', 'candidates', 'plans', 'active', 'chronicle', ...(segmented ? ['archives'] : []), ...Object.keys(EVIDENCE_BOUNDARY)], 'CAPSULE_FIELDS');
  fail([SCHEMA, ARCHIVE_SCHEMA].includes(value.schema) && [ENGINE, 'successor-local/1'].includes(value.engine), 'VERSION'); validateMission(value.mission);
  for (const [key, expected] of Object.entries(EVIDENCE_BOUNDARY)) fail(value[key] === expected, 'AUTHORITY_NONE');
  fail(Array.isArray(value.plans) && value.plans.length <= 12, 'PLANS');
  for (const plan of value.plans) { await validateImprovement(plan); fail(plan.missionSha256 === await sha256(value.mission), 'PLAN_MISSION'); }
  fail(Array.isArray(value.candidates) && value.candidates.length <= LIMITS.candidates && new Set(value.candidates.map(c => c.id)).size === value.candidates.length, 'CANDIDATES');
  for (const candidate of value.candidates) {
    keys(candidate, ['manifest', 'files', 'gaps', 'checker', 'id'], 'CANDIDATE_FIELDS');
    keys(candidate.manifest, ['engine', 'sourceSha256', 'specificationSha256', 'variant', 'tools', 'permissions', 'provider'], 'MANIFEST_FIELDS');
    fail(isHash(candidate.manifest.sourceSha256) && candidate.manifest.engine === value.engine && candidate.manifest.provider === null && canonical(candidate.manifest.permissions) === '[]' && canonical(candidate.manifest.tools) === '["local-code"]', 'AUTHORITY_NONE');
    fail(candidate.manifest.specificationSha256 === await sha256(value.mission), 'SPECIFICATION_CHANGED');
    fail(['baseline', 'improved'].includes(candidate.manifest.variant), 'VARIANT');
    fail(Array.isArray(candidate.files) && candidate.files.length <= 3, 'FILES');
    for (const file of candidate.files) {
      keys(file, ['name', 'mediaType', 'content', 'sha256'], 'FILE_FIELDS'); safePath(file.name); text(file.content, LIMITS.output); fail(['text/html', 'application/json'].includes(file.mediaType), 'MEDIA_TYPE'); fail(file.sha256 === await sha256(file.content), 'ARTIFACT_CHANGED');
    }
    const { id, ...body } = candidate; fail(id === await sha256(body), 'CANDIDATE_CHANGED');
    const checked = (value.engine === 'successor-local/1' ? checkLegacy : checkArtifacts)(value.mission, candidate.manifest.variant, candidate.files);
    fail(canonical(candidate.checker) === canonical(checked), 'EVIDENCE_CHANGED');
    if (reproduce) {
      const actual = (value.engine === 'successor-local/1' ? executeLegacy : executeMission)(value.mission, candidate.manifest.variant);
      fail(canonical(actual.files) === canonical(candidate.files.map(({ sha256: hash, ...file }) => file)) && canonical(actual.gaps) === canonical(candidate.gaps), 'REBUILD_MISMATCH');
    }
  }
  fail(value.active === null || value.candidates.some(c => c.id === value.active && c.checker.passed), 'ACTIVE_CANDIDATE');
  fail(Array.isArray(value.chronicle) && value.chronicle.length >= 1 && value.chronicle.length <= LIMITS.events, 'CHRONICLE');
  if (segmented) {
    fail(Array.isArray(value.archives) && value.archives.length >= 1 && value.archives.length <= LIMITS.historySegments, 'HISTORY_ARCHIVES');
    let start = 0;
    for (const segment of value.archives) {
      keys(segment, ['start', 'events', 'sha256'], 'HISTORY_ARCHIVE_FIELDS');
      fail(segment.start === start && Array.isArray(segment.events) && segment.events.length >= 1 && segment.events.length <= LIMITS.events, 'HISTORY_ARCHIVE_RANGE');
      fail(segment.sha256 === await sha256({ start: segment.start, events: segment.events }), 'HISTORY_ARCHIVE_CHANGED');
      start += segment.events.length;
    }
  }
  const events = historyEvents(value), boundaries = new Map();
  if (segmented) for (const segment of value.archives) boundaries.set(segment.start + segment.events.length, segment.sha256);
  let selected = null; const checked = new Set(), previouslySelected = new Set();
  for (const [index, event] of events.entries()) {
    keys(event, ['sequence', 'action', 'subject', 'previous', 'sha256'], 'EVENT_FIELDS'); text(event.subject, 2000);
    fail(['mission-defined', 'candidate-checked', 'keep', 'replace', 'rollback', 'restored', 'plan-prepared', 'run-failed', 'method-reused', 'input-mapped', ...(segmented ? ['history-continued'] : [])].includes(event.action), 'EVENT_ACTION');
    fail(event.sequence === index && event.previous === (index ? events[index - 1].sha256 : null), 'CHRONICLE_CHAIN');
    const { sha256: hash, ...record } = event; fail(hash === await sha256(record), 'CHRONICLE_CHANGED');
    if (!index) fail(event.action === 'mission-defined' && event.subject === await sha256(value.mission), 'CHRONICLE_MISSION');
    else fail(event.action !== 'mission-defined', 'CHRONICLE_MISSION');
    if (['keep', 'replace', 'rollback', 'candidate-checked'].includes(event.action)) fail(value.candidates.some(c => c.id === event.subject), 'CHRONICLE_CANDIDATE');
    if (event.action === 'history-continued') fail(boundaries.get(index) === event.subject, 'HISTORY_CONTINUATION');
    if (boundaries.has(index)) fail(event.action === 'history-continued' && event.subject === boundaries.get(index), 'HISTORY_CONTINUATION');
    if (event.action === 'candidate-checked') checked.add(event.subject);
    if (event.action === 'plan-prepared') fail(value.plans.some(p => p.commitment === event.subject), 'CHRONICLE_PLAN');
    if (event.action === 'method-reused') { const reuse = parseStrict(event.subject, 2000); keys(reuse, ['parentCapsuleSha256', 'parentMissionSha256', 'parentCandidate', 'kind', 'variant'], 'REUSE_FIELDS'); fail(index === 1 && [reuse.parentCapsuleSha256,reuse.parentMissionSha256,reuse.parentCandidate].every(isHash) && reuse.kind === value.mission.kind && ['baseline','improved'].includes(reuse.variant), 'REUSE_LINEAGE'); }
    if (event.action === 'input-mapped') { const mapping = parseStrict(event.subject, 2000); keys(mapping, ['originalSha256','normalizedSha256','mapping','decimalFormat'], 'MAPPING_FIELDS'); fail(isHash(mapping.originalSha256) && mapping.normalizedSha256 === await sha256(value.mission.input) && mapping.decimalFormat === 'dot-decimal-text', 'MAPPING_BINDING'); keys(mapping.mapping, ['id','category','value'], 'MAPPING_FIELDS'); fail(Object.values(mapping.mapping).every(v=>typeof v === 'string' && v.length > 0 && v.length <= 80) && new Set(Object.values(mapping.mapping)).size === 3, 'MAPPING_FIELDS'); }
    if (event.action === 'run-failed') fail(/^[A-Z_]{1,80}$/.test(event.subject), 'FAILURE_CODE');
    if (['keep', 'replace', 'rollback'].includes(event.action)) {
      fail(checked.has(event.subject), 'CHRONICLE_ORDER');
      if (event.action === 'keep') fail(selected === null || selected === event.subject, 'CHRONICLE_ORDER');
      if (event.action === 'replace') fail(selected && compareCandidates(value.candidates.find(c => c.id === selected), value.candidates.find(c => c.id === event.subject)).outcome === 'improvement', 'CHRONICLE_ORDER');
      if (event.action === 'rollback') fail(previouslySelected.has(event.subject), 'CHRONICLE_ORDER');
      selected = event.subject; previouslySelected.add(selected);
    }
  }
  fail(value.candidates.every(c => checked.has(c.id)), 'CHRONICLE_ORDER');
  fail(selected === value.active, 'CHRONICLE_SELECTION'); return value;
}
export async function exportCapsule(state, sourceManifest = null) {
  await validateState(state);
  const payload = { state, sourceManifest };
  const capsule = { format: state.schema === ARCHIVE_SCHEMA ? 'successor-portable/2' : 'successor-portable/1', payload, sha256: await sha256(payload) };
  fail(new TextEncoder().encode(canonical(capsule)).length <= LIMITS.capsule, 'INPUT_SIZE');
  const raw = JSON.stringify(capsule, null, 2) + '\n';
  // Whitespace must not turn an accepted compact capsule into an unimportable export.
  return new TextEncoder().encode(raw).length <= LIMITS.capsule ? raw : canonical(capsule);
}
export async function exportableState(next, sourceManifest = null) {
  try { await exportCapsule(next, sourceManifest); }
  catch (error) { if (error.code === 'INPUT_SIZE') fail(false, 'CAPSULE_CAPACITY'); throw error; }
  return next;
}
export async function inspectCapsule(raw) {
  const capsule = parseStrict(raw); keys(capsule, ['format', 'payload', 'sha256'], 'CAPSULE_FIELDS'); fail(['successor-portable/1', 'successor-portable/2'].includes(capsule.format), 'VERSION');
  keys(capsule.payload, ['state', 'sourceManifest'], 'PAYLOAD_FIELDS'); fail(capsule.sha256 === await sha256(capsule.payload), 'CAPSULE_CHANGED');
  if (capsule.payload.sourceManifest !== null) {
    keys(capsule.payload.sourceManifest, ['repository', 'commit', 'engineSha256', 'files', 'license'], 'SOURCE_FIELDS');
    const source = capsule.payload.sourceManifest;
    fail(source.repository === 'MontrealAI/AGIJobManager' && /^[a-f0-9]{40}$/.test(source.commit) && isHash(source.engineSha256) && source.license === 'MIT', 'SOURCE_FIELDS');
    fail(Array.isArray(source.files) && source.files.length <= 50, 'SOURCE_FILES');
    for (const file of source.files) { keys(file, ['path', 'sha256'], 'SOURCE_FILE'); safePath(file.path); fail(isHash(file.sha256), 'SOURCE_HASH'); }
  }
  fail(capsule.format === (capsule.payload.state.schema === ARCHIVE_SCHEMA ? 'successor-portable/2' : 'successor-portable/1'), 'VERSION');
  publicOnly(canonical(capsule.payload.state)); await validateState(capsule.payload.state);
  return { capsule, summary: { name: capsule.payload.state.mission.name, kind: capsule.payload.state.mission.kind, candidates: capsule.payload.state.candidates.length, evidence: 'historical-local', authority: 'none', payments: 'unfunded' } };
}
export async function restoreCapsule(inspected, confirmed) {
  fail(confirmed === true, 'RESTORE_CONFIRMATION');
  const { capsule } = await inspectCapsule(JSON.stringify(inspected.capsule));
  // Restoring is inspection plus an explicit workspace replacement, not a new task event.
  // It must work even when every history slot is occupied.
  return clone(capsule.payload.state);
}
export async function continueHistory(state, confirmed, sourceManifest = null) {
  fail(confirmed === true, 'HISTORY_CONFIRMATION'); await validateState(state);
  const checkpoint = await exportCapsule(state, sourceManifest);
  const next = clone(state), archives = next.archives || [];
  fail(archives.length < LIMITS.historySegments, 'HISTORY_ARCHIVE_LIMIT');
  const segment = { start: historyEvents(next).length - next.chronicle.length, events: clone(next.chronicle) };
  segment.sha256 = await sha256(segment); archives.push(segment);
  next.schema = ARCHIVE_SCHEMA; next.archives = archives; next.chronicle = [];
  await appendEvent(next, 'history-continued', segment.sha256);
  await validateState(next); await exportableState(next, sourceManifest);
  return { state: next, checkpoint };
}
export function readableSummary(state) {
  const fr = state.mission.language === 'fr', selected = state.candidates.find(c => c.id === state.active);
  return [(state.mission.name || 'SUCCESSOR Ω'), state.mission.purpose, '', (fr ? 'Mission : ' : 'Mission: ') + state.mission.kind, (fr ? 'Droits : ' : 'Rights: ') + state.mission.rights, (fr ? 'Version choisie : ' : 'Selected version: ') + (selected?.manifest.variant || (fr ? 'aucune' : 'none')), (fr ? 'Vérifications locales : ' : 'Local checks: ') + (selected ? String(selected.checker.passed) : '—'), '', fr ? 'Mesures locales uniquement. Aucune qualification indépendante, autorité, publication ou transaction. Les résultats enregistrés sont historiques : relancez les vérifications.' : 'Local measurements only. No independent qualification, authority, publication or transaction. Saved measurements are historical: rerun the checks.', '', fr ? 'Conservez le HTML autonome, le fichier JSON, les sources et leurs licences. Enregistrez un nouveau fichier après chaque modification. Un fichier et son empreinte peuvent être modifiés ensemble : ce journal local ne prouve pas son auteur.' : 'Keep the offline HTML, JSON capsule, editable sources and licenses. Save a new file after each change. A file and its checksum can be changed together: the local Chronicle does not prove authorship.', '', (fr ? 'Historique (' : 'Chronicle (') + (state.archives || []).length + (fr ? ' segments archivés; tous les événements conservés) :' : ' archived segments; all events retained):'), ...(state.archives || []).map(segment => (fr ? 'Archive à l’événement ' : 'Archive at event ') + (segment.start + 1) + ': ' + segment.sha256), ...historyEvents(state).map(e => `${e.sequence + 1}. ${e.action}: ${e.subject}`)].join('\n') + '\n';
}

export function selectedMethod(state) {
  return state.candidates.find(c => c.id === state.active)?.manifest.variant || (historyEvents(state).find(e => e.action === 'method-reused') ? parseStrict(historyEvents(state).find(e => e.action === 'method-reused').subject).variant : 'baseline');
}
export async function reuseSystem(parent, mission, confirmed, sourceManifest = null) {
  fail(confirmed === true, 'REUSE_CONFIRMATION'); await validateState(parent); validateMission(mission);
  const selected = parent.candidates.find(c => c.id === parent.active); fail(selected?.checker.passed, 'SELECT_VERSION');
  fail(mission.kind === parent.mission.kind && mission.kind !== 'custom', 'REUSE_KIND');
  fail(mission.input !== parent.mission.input, 'REUSE_INPUT');
  const parentCapsule = await exportCapsule(parent, sourceManifest), next = await createSystem(mission);
  await appendEvent(next, 'method-reused', canonical({parentCapsuleSha256:JSON.parse(parentCapsule).sha256,parentMissionSha256:await sha256(parent.mission),parentCandidate:selected.id,kind:mission.kind,variant:selected.manifest.variant}));
  return {state:next,parentCapsule,variant:selected.manifest.variant};
}
