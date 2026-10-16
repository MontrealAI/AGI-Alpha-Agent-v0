// Inert project continuity. Native data is revalidated; no permission is imported.
import { canonical, parseBounded } from './vendor/alpha/docs/assets/successor/engine.mjs';
import { validateProject, exactDigest } from './vendor/alpha/examples/successor-project/engine.mjs';
import { validate, plan, run } from './vendor/alpha/examples/successor-workbench/engine.mjs';
import { createRecord, startRun, completeRun, validateRecord } from './vendor/alpha/examples/successor-workbench/mission-record.mjs';
import { compileJobs } from '../../packages/successor-core/src/compiler.mjs';
import { ALPHA_NATIVE_SOURCE, JOBS_COMPILER_SOURCE, RECEIVER_SOURCE } from './project-native-source.mjs';

export const PROJECT_TRANSFER_SCHEMA = 'agijobsv0/alpha-project-transfer/v1';
export const PROJECT_TRANSFER_LIMIT = 2_000_000;
export const PROJECT_ROUTE = Object.freeze({ backend: 'agijobsv0-jobregistry-v2', asset: 'AGIALPHA' });
export const PROJECT_SOURCE = Object.freeze({ adapter: 'agijobsv0-project-receiver/v1', receiver: RECEIVER_SOURCE, alpha: ALPHA_NATIVE_SOURCE, compiler: JOBS_COMPILER_SOURCE });
const MAX_HISTORY = 8;
function fail(ok, code) { if (!ok) throw Object.assign(Error(code), { code }); }
function fields(value, names) {
  fail(value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === [...names].sort().join('|'), 'JOBS_PROJECT_FIELDS');
}
const clone = value => parseBounded(canonical(value));
const same = (a, b) => canonical(a) === canonical(b);
function price(value) {
  fail(typeof value === 'string' && /^[1-9][0-9]{0,24}$/.test(value) && BigInt(value) <= 1_000_000n * 10n ** 18n, 'JOBS_PROJECT_AGIALPHA_AMOUNT');
  fail(BigInt(value) >= 7n, 'JOBS_PROJECT_MINIMUM_BASE_UNITS');
  return value;
}
function identity(project) {
  return { projectId: project.projectId, cycleId: project.cycles.at(-1).cycleId, revision: project.revision, projectDigest: project.projectDigest };
}
async function upstream(raw, options) {
  const supplied = parseBounded(raw);
  if (supplied.schema === 'successor-project/v1') {
    return { project: await validateProject(raw), validation: { kind: 'native-alpha', source: ALPHA_NATIVE_SOURCE } };
  }
  fail(supplied.schema === 'agijobmanager/alpha-project-transfer/v1', 'JOBS_PROJECT_UPSTREAM_SCHEMA');
  const installed = options.managerInspector;
  fail(installed && typeof installed.inspect === 'function' && installed.source && installed.source.repository === 'MontrealAI/AGIJobManager', 'JOBS_PROJECT_MANAGER_VALIDATOR_REQUIRED');
  // The installed inspector and its source pin come from application code, never supplied JSON.
  const inspected = await installed.inspect(raw);
  const project = await validateProject(supplied.original.raw);
  fail(inspected && same(inspected.originalProject, project), 'JOBS_PROJECT_MANAGER_BINDING');
  return { project, validation: { kind: 'native-manager', source: clone(installed.source) } };
}
async function compile(spec, amountBaseUnits, compiledAt) {
  fail(typeof compiledAt === 'string' && Number.isFinite(Date.parse(compiledAt)) && new Date(compiledAt).toISOString() === compiledAt, 'JOBS_PROJECT_CLOCK');
  const native = await plan(spec, compiledAt);
  const mission = clone(native.constitution);
  mission.budget.limitBaseUnits = price(amountBaseUnits);
  const jobs = native.graph.nodes.map((node, index) => {
    const { digest, sealed, signatureStatus, ...draft } = node;
    return { ...draft, budget: { ...draft.budget, limitBaseUnits: (BigInt(amountBaseUnits) / BigInt(native.graph.nodes.length) + (BigInt(index) < BigInt(amountBaseUnits) % BigInt(native.graph.nodes.length) ? 1n : 0n)).toString() } };
  });
  return compileJobs(mission, { jobs, edges: native.graph.edges, now: compiledAt });
}
async function workFor(project, amountBaseUnits, compiledAt, upstreamSha256) {
  const cycle = project.cycles.at(-1), record = parseBounded(cycle.records.at(-1).bytes);
  fail(cycle.mapping.choices.family === 'public-data' && record.spec.family === 'public-data', 'JOBS_PROJECT_MAPPING_UNAVAILABLE');
  const spec = validate(record.spec);
  const nativeSpecRaw = canonical(spec), nativeSpecSha256 = await exactDigest(nativeSpecRaw);
  const compiledRaw = canonical(await compile(spec, amountBaseUnits, compiledAt)), compiledSha256 = await exactDigest(compiledRaw);
  const envelope = { schema: 'agijobsv0.successor-public-data-work.v1', project: identity(project), upstreamSha256, source: PROJECT_SOURCE, route: PROJECT_ROUTE, executor: 'fixed-js-public-data-v1',
    native: { namespace: 'successor-workbench/v1', raw: nativeSpecRaw, sha256: nativeSpecSha256 },
    planning: { amountBaseUnits, decimals: 18, status: 'unfunded-proposal' }, compiled: { sha256: compiledSha256, compiledAt } };
  const specRaw = canonical(envelope);
  return { namespace: envelope.schema, executor: envelope.executor, nativeSpecRaw, nativeSpecSha256, specRaw, specSha256: await exactDigest(specRaw), compiledRaw, compiledSha256, compiledAt };
}
async function seal(value) {
  const raw = canonical({ ...value, sha256: await exactDigest(canonical(value)) });
  fail(new TextEncoder().encode(raw).length <= PROJECT_TRANSFER_LIMIT, 'JOBS_PROJECT_SIZE');
  return raw;
}
async function sourceHash() { return exactDigest(canonical(PROJECT_SOURCE)); }
async function initialRecord(project, spec) {
  return createRecord({ missionId: 'jobs-' + project.projectDigest.slice(0, 40), sourceHash: await sourceHash(), spec });
}
async function replay(prior, pack, index) {
  const runId = 'jobs-local-run-' + index;
  const running = await startRun(prior, { expectedRevision: prior.revision, runId });
  return completeRun(running, pack, { expectedRevision: running.revision, runId });
}
export async function importAlphaProject(raw, { amountBaseUnits, compiledAt, ...options }) {
  const { project, validation } = await upstream(raw, options);
  const planning = { amountBaseUnits: price(amountBaseUnits), decimals: 18, status: 'unfunded-proposal' };
  const originalHash = await exactDigest(raw);
  return seal({ schema: PROJECT_TRANSFER_SCHEMA, source: PROJECT_SOURCE, project: identity(project), original: { raw, sha256: originalHash }, upstreamValidation: validation,
    route: PROJECT_ROUTE, planning, work: await workFor(project, amountBaseUnits, compiledAt, originalHash), history: [{ kind: 'imported', upstreamSha256: originalHash }],
    authority: 'none', qualification: 'source-only', settlement: 'not-connected' });
}
export async function inspectProjectTransfer(raw, options = {}) {
  const transfer = parseBounded(raw);
  fields(transfer, ['schema','source','project','original','upstreamValidation','route','planning','work','history','authority','qualification','settlement','sha256']);
  const { sha256, ...body } = transfer;
  fail(sha256 === await exactDigest(canonical(body)), 'JOBS_PROJECT_INTEGRITY');
  fail(transfer.schema === PROJECT_TRANSFER_SCHEMA && transfer.authority === 'none' && transfer.qualification === 'source-only' && transfer.settlement === 'not-connected', 'JOBS_PROJECT_AUTHORITY');
  fail(same(transfer.source, PROJECT_SOURCE), 'JOBS_PROJECT_SOURCE_DRIFT');
  fail(same(transfer.route, PROJECT_ROUTE), 'JOBS_PROJECT_ROUTE');
  fields(transfer.original, ['raw','sha256']);
  fail(transfer.original.sha256 === await exactDigest(transfer.original.raw), 'JOBS_PROJECT_ORIGINAL_BYTES');
  const { project, validation } = await upstream(transfer.original.raw, options);
  fail(same(transfer.project, identity(project)) && same(transfer.upstreamValidation, validation), 'JOBS_PROJECT_BINDING');
  fields(transfer.planning, ['amountBaseUnits','decimals','status']);
  price(transfer.planning.amountBaseUnits);
  fail(transfer.planning.decimals === 18 && transfer.planning.status === 'unfunded-proposal', 'JOBS_PROJECT_FUNDING');
  fail(same(transfer.work, await workFor(project, transfer.planning.amountBaseUnits, transfer.work.compiledAt, transfer.original.sha256)), 'JOBS_PROJECT_WORK_CHANGED');
  fail(Array.isArray(transfer.history) && transfer.history.length >= 1 && transfer.history.length <= MAX_HISTORY, 'JOBS_PROJECT_HISTORY_LIMIT');
  const spec = parseBounded(transfer.work.nativeSpecRaw);
  let lastRecord = await initialRecord(project, spec);
  for (const [index, entry] of transfer.history.entries()) {
    if (index === 0) { fields(entry, ['kind','upstreamSha256']); fail(entry.kind === 'imported' && entry.upstreamSha256 === transfer.original.sha256, 'JOBS_PROJECT_IMPORT_CLAIM'); continue; }
    fields(entry, ['kind','raw','sha256']);
    fail(entry.kind === 'local-result' && entry.sha256 === await exactDigest(entry.raw), 'JOBS_PROJECT_RESULT_BYTES');
    const actual = await validateRecord(parseBounded(entry.raw));
    fail(actual.state === 'result' && actual.review === null && actual.result !== null, 'JOBS_PROJECT_RESULT_STATE');
    const expected = await replay(lastRecord, actual.result.pack, index);
    fail(same(actual, expected), 'JOBS_PROJECT_HISTORY_REWRITTEN');
    lastRecord = actual;
  }
  return { transfer, project, originalProject: project, spec, lastRecord, receiptStatus: 'no-rpc-receipt-attached', operationalAuthority: [], productionQualified: false };
}
export async function runProjectTransfer(raw, options = {}) {
  const { transfer, project, spec, lastRecord } = await inspectProjectTransfer(raw, options);
  fail(transfer.history.length < MAX_HISTORY, 'JOBS_PROJECT_HISTORY_LIMIT');
  const pack = await run(spec, { sourceHash: await sourceHash() });
  const recordRaw = canonical(await replay(lastRecord, pack, transfer.history.length));
  transfer.history.push({ kind: 'local-result', raw: recordRaw, sha256: await exactDigest(recordRaw) });
  delete transfer.sha256;
  const result = await seal(transfer);
  await inspectProjectTransfer(result, options);
  return result;
}
