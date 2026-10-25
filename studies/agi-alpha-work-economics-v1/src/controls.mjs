// SPDX-License-Identifier: Apache-2.0
// Study-only finite control cases. Never edits upstream source or initializes Journal.
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as workbench from '../upstream/examples/successor-workbench/engine.mjs';
import * as record from '../upstream/examples/successor-workbench/mission-record.mjs';
import * as guide from '../upstream/examples/ti-guide/guide.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
if (args.length === 1 && args[0] === '--help') {
  console.log('node src/controls.mjs --out NEW_OUTPUT_DIRECTORY');
  process.exit(0);
}
if (args.length !== 2 || args[0] !== '--out') {
  throw Error('Usage: node src/controls.mjs --out NEW_OUTPUT_DIRECTORY');
}
const out = resolve(args[1]);
const sha256 = value => createHash('sha256').update(value).digest('hex');
const json = value => JSON.stringify(value, null, 2) + '\n';
const clone = value => JSON.parse(JSON.stringify(value));
const errorData = error => ({ name: error.name, code: error.code ?? null, message: error.message, stack: error.stack ?? null });
const writeJson = (path, value) => writeFile(path, json(value), { flag: 'wx' });
const same = (a, b) => guide.canonical(a) === guide.canonical(b);
async function attempt(operation) {
  try { return { status: 'returned', value: await operation(), error: null }; }
  catch (error) { return { status: 'rejected', value: null, error: errorData(error) }; }
}
const isError = (value, expected) => value.status === 'rejected' && value.error.message === expected;
const baseSpec = () => ({
  ...workbench.example('public-data'),
  name: 'Finite controls: public-data report',
  inputs: { csv: 'group,amount\nCatalog,4\nCatalog,3\nWebsite,2\nLibrary,-1\nLibrary,5\n', unit: 'synthetic exception counts' },
});
const catalogInput = () => ({
  leftCsv: 'id,name,qty\nA,Part A,10\nB,Part B,3\n',
  rightCsv: 'id,name,qty\nA,Part A,12\nC,Part C,8\n',
  leftKey: 'id', rightKey: 'id',
});

// Verify actual released bytes before relying on any source identifier.
const manifestPath = join(root, 'protocol/UPSTREAM_SOURCE_MANIFEST.json');
const upstreamManifest = JSON.parse(await readFile(manifestPath, 'utf8'));
const expectedByPath = new Map(upstreamManifest.map(item => [item.path, item]));
const originalSourcesPath = 'alpha_factory_v1/core/runtime/successor/workbench_sources.json';
const originalSourcesBytes = await readFile(join(root, 'upstream', originalSourcesPath));
const originalSources = JSON.parse(originalSourcesBytes);
const guidePaths = ['examples/successor-alpha/engine.mjs', 'examples/successor-alpha/research.mjs', 'examples/ti-guide/guide.mjs'];
const exercisedPaths = [...new Set([
  ...Object.keys(originalSources.sources),
  'examples/successor-workbench/mission-record.mjs', originalSourcesPath, ...guidePaths,
])].sort();
const verifiedSources = [];
for (const path of exercisedPaths) {
  const bytes = await readFile(join(root, 'upstream', path));
  const expected = expectedByPath.get(path);
  const actual = { path, sha256: sha256(bytes), bytes: bytes.length };
  if (!expected || actual.sha256 !== expected.actual_sha256 || bytes.length !== expected.actual_size) {
    throw Error('UPSTREAM_MANIFEST_MISMATCH: ' + path);
  }
  if (Object.hasOwn(originalSources.sources, path) && originalSources.sources[path] !== actual.sha256) {
    throw Error('ORIGINAL_WORKBENCH_SOURCE_MISMATCH: ' + path);
  }
  verifiedSources.push(actual);
}
const sourceHash = originalSources.sourceHash;
if (!/^[a-f0-9]{64}$/.test(sourceHash)) throw Error('ORIGINAL_SOURCE_IDENTITY_INVALID');
const guideSourceEntries = verifiedSources.filter(item => guidePaths.includes(item.path));
const guideSourceHash = sha256(guide.canonical(guideSourceEntries));
if (sourceHash === guideSourceHash) throw Error('SOURCE_SCOPES_NOT_DISTINCT');
await mkdir(out); // Refuse every existing directory; never overwrite an earlier run.
const began = new Date().toISOString();
await writeJson(join(out, 'source-identity.json'), {
  snapshotCommit: 'f836f06e8351e64db1da770e16e304b5feb01f28',
  executionFilesMatchRelease: 'v1.43.0', releaseCommit: '5499495911bf8822ac0aa8c9007f00789c1132b5',
  workbenchSourceHash: sourceHash, workbenchIdentityDefinition: 'Original verified workbench_sources.json sourceHash; listed dependencies separately matched byte-for-byte.',
  guideSourceHash, guideIdentityDefinition: 'SHA-256(UTF-8 canonical JSON of sorted {path,sha256,bytes} entries for guide, research and alpha engine).',
  mismatchInterpretation: 'Two different inspected source scopes; not a simulated claim about a future upgrade.',
  exercisedFiles: verifiedSources,
  upstreamManifestSha256: sha256(await readFile(manifestPath)),
  launcherSha256: sha256(await readFile(fileURLToPath(import.meta.url))),
  protocolSha256: sha256(await readFile(join(root, 'protocol/PROTOCOL_CONTROLS.md'))),
});
const report = {
  schema: 'agialpha-local-controls/v1', began, completed: null,
  status: 'RUNNING', node: process.version, platform: process.platform, architecture: process.arch,
  scope: 'Finite foreground original APIs; no Journal, daemon, remote worker, credentials, model calls, or financial transactions.',
  controlCaseDenominator: 8, businessDeliverablesCounted: 0,
  acceptanceKind: 'Predeclared study assertions of published API contracts; not independent human acceptance.',
  sourceHash, guideSourceHash, cases: [],
};
async function saveReport() { await writeFile(join(out, 'controls.json'), json(report)); }
await saveReport();
async function caseRun(id, title, operation) {
  const dir = join(out, id); await mkdir(dir);
  const checks = [];
  const check = (name, passed, actual = null, expected = null) => checks.push({ name, passed: Boolean(passed), actual, expected });
  const start = process.hrtime.bigint();
  const entry = { id, title, began: new Date().toISOString(), status: 'RUNNING', checks, observations: null, unexpectedError: null };
  try { entry.observations = await operation({ dir, check }); }
  catch (error) { entry.unexpectedError = errorData(error); }
  entry.elapsedNanoseconds = String(process.hrtime.bigint() - start);
  entry.completed = new Date().toISOString();
  entry.status = !entry.unexpectedError && checks.length > 0 && checks.every(item => item.passed) ? 'PASS' : 'FAIL';
  await writeJson(join(dir, 'observations.json'), entry);
  report.cases.push(entry); await saveReport();
  console.log(id + ' ' + entry.status);
}
async function startingRecord(missionId, runId, commitment = sourceHash) {
  const draft = await record.createRecord({ missionId, sourceHash: commitment, spec: baseSpec() });
  return record.startRun(draft, { expectedRevision: draft.revision, runId });
}
async function completedRecord(missionId, runId) {
  const running = await startingRecord(missionId, runId);
  const pack = await workbench.run(running.spec, { sourceHash });
  const completed = await record.completeRun(running, pack, { expectedRevision: running.revision, runId });
  return { running, pack, completed };
}
async function workspaceFor(input, runId) {
  const result = await guide.compute(input);
  const workspace = guide.makeWorkspace(input, result, {
    approach: 'grouped', sourceHash: guideSourceHash, runId,
    createdAt: new Date().toISOString(), language: 'en',
  });
  return { result, workspace, raw: json(workspace), csv: guide.fullDifferencesCsv(result) };
}

await caseRun('C01_STOP', 'Pre-aborted cooperative STOP', async ({ dir, check }) => {
  const running = await startingRecord('controls-stop', 'stop-1');
  await writeJson(join(dir, 'input.json'), running.spec);
  const controller = new AbortController(); controller.abort('Predeclared control STOP');
  let checkpoints = 0;
  const run = await attempt(() => workbench.run(running.spec, { sourceHash, signal: controller.signal, onCheckpoint: async () => { checkpoints++; } }));
  await writeJson(join(dir, 'run-attempt.json'), run);
  const stopped = await record.stopRun(running, { expectedRevision: running.revision, runId: 'stop-1', reason: 'Pre-aborted control; original run returned no pack.' });
  await writeFile(join(dir, 'stopped-record.json'), await record.serializeRecord(stopped), { flag: 'wx' });
  check('Original runtime reports CANCELLED', isError(run, 'CANCELLED'), run.error?.message, 'CANCELLED');
  check('No pack returned', run.value === null);
  check('Stop transition removes active run and result', stopped.state === 'stopped' && stopped.run === null && stopped.result === null && stopped.review === null);
  return { checkpoints, deliveredPacks: run.status === 'returned' ? 1 : 0, scope: 'Pre-aborted cooperative check; not an arbitrary process kill.' };
});

await caseRun('C02_RECOVERY', 'Interrupted record, historical restore, explicit import and new run', async ({ dir, check }) => {
  const running = await startingRecord('controls-interrupted', 'interrupted-1');
  await writeJson(join(dir, 'input.json'), running.spec);
  let checkpoints = 0; const progress = [];
  const run = await attempt(() => workbench.run(running.spec, {
    sourceHash, onProgress: phase => progress.push(phase),
    onCheckpoint: async () => { if (++checkpoints === 3) throw Error('INJECTED_INTERRUPTION'); },
  }));
  await writeJson(join(dir, 'interrupted-attempt.json'), run);
  const interrupted = await record.interruptRun(running, { expectedRevision: running.revision, runId: 'interrupted-1', reason: 'Injected checkpoint exception; explicit restart required.' });
  const serialized = await record.serializeRecord(interrupted);
  await writeFile(join(dir, 'interrupted-record.json'), serialized, { flag: 'wx' });
  const restored = await record.restoreRecord(serialized, { sourceHash });
  await writeJson(join(dir, 'restored-view.json'), restored);
  const imported = await record.importRecord(serialized, { missionId: 'controls-recovery-import', sourceHash });
  await writeJson(join(dir, 'imported-draft.json'), imported);
  const restarted = await record.startRun(imported, { expectedRevision: imported.revision, runId: 'explicit-restart-1' });
  const pack = await workbench.run(restarted.spec, { sourceHash });
  const completed = await record.completeRun(restarted, pack, { expectedRevision: restarted.revision, runId: 'explicit-restart-1' });
  await writeJson(join(dir, 'explicit-new-run-pack.json'), pack);
  await writeFile(join(dir, 'completed-record.json'), await record.serializeRecord(completed), { flag: 'wx' });
  for (const artifact of pack.result.artifacts) await writeFile(join(dir, artifact.name), artifact.content, { flag: 'wx' });
  check('First attempt interrupted without a pack', isError(run, 'INJECTED_INTERRUPTION') && run.value === null && checkpoints === 3);
  check('Restore is historical and read-only', restored.mode === 'historical' && restored.readOnly === true && restored.reason === 'EXTERNAL_RESTORE' && restored.currentResult === null && restored.currentReview === null);
  check('Explicit import creates new draft without a result', imported.state === 'draft' && imported.missionId !== interrupted.missionId && imported.result === null && imported.review === null);
  check('Imported history has no inherited authority', imported.history.length > 0 && imported.history.every(item => item.trust === 'historical-untrusted'));
  check('Explicit new run returns correct aggregation', completed.state === 'result' && same(pack.result.summary, { rows: 5, groups: 3, total: 13, unit: 'synthetic exception counts' }), pack.result.summary);
  return { checkpoints, progress, firstAttemptPacks: run.status === 'returned' ? 1 : 0, explicitNewRunPacks: 1, recovery: 'Explicit input restart, not continuation from an internal checkpoint; record validation also recomputes deterministic output.' };
});

await caseRun('C03_BOUNDS', 'Clock-boundary budget and input ceiling', async ({ dir, check }) => {
  const spec = baseSpec(); await writeJson(join(dir, 'valid-input.json'), spec);
  let clockCalls = 0; let checkpoints = 0;
  const clockValues = [];
  const budget = await attempt(() => workbench.run(spec, {
    sourceHash, clock: () => { const value = clockCalls++ === 0 ? 0 : 60001; clockValues.push(value); return value; },
    onCheckpoint: async () => { checkpoints++; },
  }));
  await writeJson(join(dir, 'budget-attempt.json'), budget);
  const oversized = baseSpec(); oversized.inputs.csv = 'group,amount\n' + 'A,1\n'.repeat(25000);
  await writeJson(join(dir, 'oversized-input.json'), oversized);
  const bound = await attempt(() => workbench.run(oversized, { sourceHash }));
  await writeJson(join(dir, 'input-bound-attempt.json'), bound);
  check('Injected budget boundary refused', isError(budget, 'TIME_BUDGET_EXCEEDED') && budget.value === null);
  check('CSV over ceiling refused', oversized.inputs.csv.length > 100000 && isError(bound, 'TEXT: csv') && bound.value === null);
  return { clockValues, checkpoints, oversizedCsvBytes: Buffer.byteLength(oversized.inputs.csv), enforcedCsvCharacterCeiling: 100000, timeTest: 'Injected monotonic clock, not real 60-second work', monetaryBudget: 'NOT_TESTED' };
});

await caseRun('C04_SOURCE', 'Different source identity remains historical and cannot complete current run', async ({ dir, check }) => {
  const { pack, completed } = await completedRecord('controls-source-original', 'source-original-1');
  const serialized = await record.serializeRecord(completed);
  await writeFile(join(dir, 'original-record.json'), serialized, { flag: 'wx' });
  const restored = await record.restoreRecord(serialized, { sourceHash: guideSourceHash });
  await writeJson(join(dir, 'different-source-restored-view.json'), restored);
  const mismatched = await startingRecord('controls-source-different', 'source-different-1', guideSourceHash);
  await writeJson(join(dir, 'different-source-running-record.json'), mismatched);
  const promotion = await attempt(() => record.completeRun(mismatched, pack, { expectedRevision: mismatched.revision, runId: 'source-different-1' }));
  await writeJson(join(dir, 'promotion-attempt.json'), promotion);
  check('Distinct inspected source identities used', sourceHash !== guideSourceHash);
  check('Mismatched restore has no current result or review', restored.reason === 'SOURCE_MISMATCH' && restored.mode === 'historical' && restored.readOnly === true && restored.currentResult === null && restored.currentReview === null);
  check('Pack cannot complete differently bound run', isError(promotion, 'SOURCE_MISMATCH') && promotion.value === null);
  return { originalSourceHash: sourceHash, mismatchedDeclaredSourceHash: guideSourceHash, interpretation: 'Intentional mismatch of two inspected source scopes, not an observed release upgrade.' };
});

await caseRun('C05_CORRUPTION', 'Changed saved claims rejected', async ({ dir, check }) => {
  const original = await workspaceFor(catalogInput(), 'controls-corruption-original');
  await writeFile(join(dir, 'original-workspace.json'), original.raw, { flag: 'wx' });
  const pristineRestore = await attempt(() => guide.restoreWorkspace(original.raw, guideSourceHash));
  await writeJson(join(dir, 'pristine-workspace-restore.json'), pristineRestore);
  const altered = clone(original.workspace); altered.result.metrics.matchedPairs += 1;
  const corruptRaw = json(altered); await writeFile(join(dir, 'corrupt-workspace.json'), corruptRaw, { flag: 'wx' });
  const workspaceRestore = await attempt(() => guide.restoreWorkspace(corruptRaw, guideSourceHash));
  await writeJson(join(dir, 'corrupt-workspace-attempt.json'), workspaceRestore);
  const draft = await record.createRecord({ missionId: 'controls-corrupt-record', sourceHash, spec: baseSpec() });
  await writeFile(join(dir, 'original-record.json'), await record.serializeRecord(draft), { flag: 'wx' });
  const alteredRecord = clone(draft); alteredRecord.revision += 1;
  await writeJson(join(dir, 'corrupt-record.json'), alteredRecord);
  const recordRestore = await attempt(() => record.restoreRecord(json(alteredRecord), { sourceHash }));
  await writeJson(join(dir, 'corrupt-record-attempt.json'), recordRestore);
  check('Original workspace restores', pristineRestore.status === 'returned' && same(pristineRestore.value.result, original.result));
  check('Changed result claim rejected by recomputation', isError(workspaceRestore, 'The saved results differ from recomputation. No result or authority was restored.') && workspaceRestore.value === null);
  check('Changed record revision rejected by digest', isError(recordRestore, 'RECORD_INTEGRITY') && recordRestore.value === null);
  return { pristineWorkspaceRestored: pristineRestore.status === 'returned', originalMatchedPairs: original.result.metrics.matchedPairs, corruptedClaim: altered.result.metrics.matchedPairs, authorityRestoredFromCorruption: false };
});

await caseRun('C06_ROLLBACK', 'Restore preserved local artifact bytes', async ({ dir, check }) => {
  const prior = await workspaceFor(catalogInput(), 'controls-rollback-prior');
  const changed = catalogInput(); changed.rightCsv = 'id,name,qty\nA,Part A,10\nB,Part B,3\nD,Part D,1\n';
  const later = await workspaceFor(changed, 'controls-rollback-later');
  const fileNames = ['workspace.json', 'all-differences.csv'];
  const priorBytes = [Buffer.from(prior.raw), Buffer.from(prior.csv)];
  const laterBytes = [Buffer.from(later.raw), Buffer.from(later.csv)];
  for (const name of ['prior', 'later', 'active']) await mkdir(join(dir, name));
  const identities = [];
  for (let i = 0; i < fileNames.length; i++) {
    const name = fileNames[i];
    await writeFile(join(dir, 'prior', name), priorBytes[i], { flag: 'wx' });
    await writeFile(join(dir, 'later', name), laterBytes[i], { flag: 'wx' });
    const active = join(dir, 'active', name);
    await writeFile(active, priorBytes[i], { flag: 'wx' });
    await writeFile(active, laterBytes[i]);
    const observedLater = await readFile(active);
    await writeFile(active, await readFile(join(dir, 'prior', name)));
    const restoredBytes = await readFile(active);
    const item = { name, priorSha256: sha256(priorBytes[i]), laterSha256: sha256(observedLater), restoredSha256: sha256(restoredBytes), priorBytes: priorBytes[i].length, laterBytes: observedLater.length, restoredBytes: restoredBytes.length };
    identities.push(item);
    check(name + ': later content was different', item.laterSha256 !== item.priorSha256);
    check(name + ': exact preserved bytes restored', restoredBytes.equals(priorBytes[i]) && item.restoredSha256 === item.priorSha256 && item.restoredBytes === item.priorBytes);
  }
  const restored = await guide.restoreWorkspace(await readFile(join(dir, 'active/workspace.json'), 'utf8'), guideSourceHash);
  check('Restored workspace still verifies', same(restored.result, prior.result) && restored.authority === 'none');
  await writeJson(join(dir, 'artifact-identities.json'), identities);
  return { identities, priorMetrics: prior.result.metrics, laterMetrics: later.result.metrics, scope: 'Local snapshot copying; no claim of atomic multi-file, transactional, production, or contract rollback.' };
});

await caseRun('C07_FALLBACK', 'Retained catalog key refused; explicit valid key succeeds', async ({ dir, check }) => {
  const current = catalogInput();
  const retained = { description: 'Prior catalog plan selected sku as exact key', leftKey: 'sku', rightKey: 'sku' };
  await writeJson(join(dir, 'retained-plan.json'), retained);
  const wrong = { ...current, leftKey: retained.leftKey, rightKey: retained.rightKey };
  await writeJson(join(dir, 'inappropriate-reuse-input.json'), wrong);
  const refused = await attempt(() => guide.compute(wrong));
  await writeJson(join(dir, 'inappropriate-reuse-attempt.json'), refused);
  await writeJson(join(dir, 'explicit-fallback-input.json'), current);
  const fallback = await workspaceFor(current, 'controls-explicit-fallback');
  await writeFile(join(dir, 'fallback-workspace.json'), fallback.raw, { flag: 'wx' });
  await writeFile(join(dir, 'all-differences.csv'), fallback.csv, { flag: 'wx' });
  check('Missing retained key refused without deliverable', isError(refused, 'Choose a key column present in each CSV.') && refused.value === null);
  const metrics = fallback.result.metrics;
  check('Explicit valid-key fallback has expected complete counts', metrics.matchedPairs === 1 && metrics.unmatchedRows === 2 && metrics.conflictingPairs === 1 && metrics.fieldDifferences === 1, metrics);
  check('Fallback makes no automatic source correction', fallback.result.limitations.automaticallyResolved === false);
  return { retainedKeys: [retained.leftKey, retained.rightKey], correctedKeys: [current.leftKey, current.rightKey], correctionType: 'Explicit predeclared configuration fallback; no autonomous schema inference claim.', metrics };
});

await caseRun('C08_AMBIGUITY', 'Numeric-looking exact identifiers remain unresolved', async ({ dir, check }) => {
  const input = { leftCsv: 'id,name,qty\n001,Part A,10\n', rightCsv: 'id,name,qty\n1,Part A,10\n', leftKey: 'id', rightKey: 'id' };
  await writeJson(join(dir, 'input.json'), input);
  const computed = await workspaceFor(input, 'controls-identifier-ambiguity');
  await writeFile(join(dir, 'workspace.json'), computed.raw, { flag: 'wx' });
  await writeFile(join(dir, 'all-differences.csv'), computed.csv, { flag: 'wx' });
  const result = computed.result;
  const kinds = result.differences.map(item => [item.key, item.kind]).sort((a, b) => a[0].localeCompare(b[0]));
  check('Exact identifiers not numerically coerced', result.metrics.matchedPairs === 0 && result.metrics.unmatchedRows === 2 && result.metrics.unmatchedKeys === 2, result.metrics);
  check('Both exact strings and source sides preserved', same(kinds, [['001', 'missing_from_right'], ['1', 'missing_from_left']]), kinds);
  check('Ambiguity not automatically resolved', result.limitations.automaticallyResolved === false && computed.workspace.authority === 'none');
  return { metrics: result.metrics, preservedIdentifiers: kinds, unresolvedDecision: 'A responsible user must determine whether 001 and 1 denote the same entity.' };
});

report.completed = new Date().toISOString();
report.passed = report.cases.filter(item => item.status === 'PASS').length;
report.failed = report.cases.filter(item => item.status === 'FAIL').length;
report.status = report.passed === report.controlCaseDenominator ? 'PASS' : 'FAIL';
await saveReport();
const evidence = [];
async function listEvidence(dir) {
  for (const item of (await readdir(dir, { withFileTypes: true })).sort((a, b) => a.name.localeCompare(b.name))) {
    const path = join(dir, item.name);
    if (item.isDirectory()) await listEvidence(path);
    else if (item.isFile()) {
      const bytes = await readFile(path);
      evidence.push({ path: relative(out, path).split('\\').join('/'), bytes: bytes.length, sha256: sha256(bytes) });
    }
  }
}
await listEvidence(out);
await writeJson(join(out, 'evidence-manifest.json'), { schema: 'sha256-evidence-manifest/v1', files: evidence, excludesSelf: true });
console.log(JSON.stringify({ status: report.status, passed: report.passed, failed: report.failed, output: out }));
process.exitCode = report.failed ? 1 : 0;
