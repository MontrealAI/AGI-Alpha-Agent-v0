// SPDX-License-Identifier: Apache-2.0
// Trusted caller boundary. The enterprise cannot supply or replace the checker.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createBridge } from './source-bridge.mjs';

export class DeliveryError extends Error {
  constructor(code, message, details = {}) { super(message); this.name = 'DeliveryError'; this.code = code; this.details = details; }
}
const requireThat = (condition, code, message, details) => { if (!condition) throw new DeliveryError(code, message, details); };
const canonical = value => JSON.stringify(value, function (_key, entry) { return entry !== null && typeof entry === 'object' && !Array.isArray(entry) ? Object.fromEntries(Object.keys(entry).sort().map(key => [key, entry[key]])) : entry; });
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hash = value => hashBytes(canonical(value));
export const canonicalBytes = value => `${canonical(value)}\n`;
export const proofHash = value => hashBytes(canonicalBytes(value));
const clone = value => JSON.parse(canonical(value));
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;

export function prepareDelivery(mission, result) {
  requireThat(result?.schema === 'tae/candidate-result-v1' && result.status === 'complete' && result.delivery?.status === 'ready', 'NOT_DELIVERABLE', 'Only internally complete and delivery-feasible results can reach the native boundary.');
  requireThat(result.missionId === mission?.missionId && result.kind === mission.kind, 'MISSION_IDENTITY', 'Mission identity or kind differs.');
  requireThat(result.currentProof === null && Array.isArray(result.authority) && result.authority.length === 0, 'CANDIDATE_AUTHORITY', 'A candidate cannot attach a current proof or permission.');
  requireThat(result.inputHash === hash(mission), 'INPUT_BINDING', 'Candidate input hash differs from the exact mission.');
  requireThat(Array.isArray(result.rows) && result.rows.length > 0 && result.rows.length <= 2000, 'ROW_LIMIT', 'Native delivery rows must be nonempty and bounded.');
  const seen = new Set(); let total = 0n;
  const rows = result.rows.map(row => {
    requireThat(typeof row.group === 'string' && /^[A-Za-z0-9_-]{1,48}$/u.test(row.group) && !seen.has(row.group), 'GROUP_BOUNDARY', 'Output groups must be unique admitted labels.'); seen.add(row.group);
    requireThat(typeof row.amount === 'string' && /^(0|-?[1-9][0-9]*)$/u.test(row.amount) && row.amount.length <= 8, 'AMOUNT_BOUNDARY', 'Output amount must be a bounded canonical integer string.');
    const value = BigInt(row.amount); requireThat(value <= 1000000n && value >= -1000000n, 'AMOUNT_BOUNDARY', 'Output amount exceeds the native per-group boundary.'); total += value;
    return { group: row.group, amount: row.amount };
  }).sort((a, b) => compare(a.group, b.group));
  requireThat(total <= 1000000n && total >= -1000000n, 'TOTAL_BOUNDARY', 'Signed aggregate exceeds the native boundary.');
  requireThat(canonical(rows) === canonical(result.rows) && hash(rows) === result.outputHash, 'OUTPUT_BINDING', 'Output ordering, content, or hash differs.');
  const csv = `group,amount\n${rows.map(row => `${row.group},${row.amount}`).join('\n')}\n`;
  requireThat(csv === result.csv, 'CSV_BINDING', 'Native CSV differs from exact normalized rows.');
  let capabilityId = null;
  if (result.capability) {
    const { programs, modules, limits, modelId } = result.capability;
    capabilityId = hash({ programs, modules, limits, modelId });
    requireThat(capabilityId === result.capability.id, 'CAPABILITY_BINDING', 'Capability definition differs from its digest.');
    requireThat(result.capability.currentProof === null && result.capability.authority?.length === 0, 'CAPABILITY_AUTHORITY', 'A retained capability cannot supply mission proof or authority.');
  }
  const binding = {
    schema: 'tae/graph-to-native-binding-v1', missionId: mission.missionId, missionKind: mission.kind,
    inputSha256: proofHash(mission), candidateInputSha256: hash(mission), outputRowsSha256: hash(rows), canonicalOutputRowsSha256: proofHash(rows), csvSha256: hashBytes(csv),
    capabilityId, capabilityManifestSha256: result.capability ? hash(result.capability) : null,
    sourceCatalogSha256: result.sources?.rootSha256 ?? null,
    semanticScope: 'Graph semantics require the independent mission checker; native CSV arithmetic checks do not validate graph semantics.',
    currentProof: null, authority: []
  };
  return { missionId: mission.missionId, rows, total: total.toString(), csv, binding, bindingSha256: hash(binding) };
}

export function createMissionDelivery({ repositories, check, concurrency = 2, maxQueued = 32 } = {}) {
  requireThat(typeof check === 'function', 'MISSING_INDEPENDENT_CHECK', 'The trusted caller must install an external mission checker.');
  requireThat(Number.isInteger(concurrency) && concurrency >= 1 && concurrency <= 2 && Number.isInteger(maxQueued) && maxQueued >= 0 && maxQueued <= 32, 'RESOURCE_CEILING', 'Local concurrency is limited to 2 and queue depth to 32.');
  const jobs = new Map(); const queue = []; const events = [];
  let active = 0; let maxObserved = 0; let bridgePromise = null; let completed = 0; let failed = 0; let reused = 0;
  async function acquire(signal) {
    requireThat(!signal?.aborted, 'INTERRUPTED', 'Caller stopped this delivery before admission.');
    if (active < concurrency) { active++; maxObserved = Math.max(maxObserved, active); return; }
    requireThat(queue.length < maxQueued, 'QUEUE_FULL', 'The bounded delivery queue is full.');
    await new Promise(resolve => queue.push(resolve));
    if (signal?.aborted) { release(); throw new DeliveryError('INTERRUPTED', 'Caller stopped this queued delivery.'); }
  }
  function release() { const next = queue.shift(); if (next) next(); else active--; }
  async function deliver(mission, result, { projectId = 'writer4-graph-enterprise', cycleId = mission?.missionId, parentProject = null, language = 'en', signal } = {}) {
    const prepared = prepareDelivery(mission, result);
    const key = hash({ bindingSha256: prepared.bindingSha256, projectId, cycleId, parentProjectSha256: parentProject === null ? null : hashBytes(parentProject), language });
    if (jobs.has(key)) { reused++; return jobs.get(key); }
    const pending = (async () => {
      const started = performance.now(); const cpu = process.cpuUsage();
      let acquired = false;
      try {
        await acquire(signal); acquired = true;
        requireThat(!signal?.aborted, 'INTERRUPTED', 'Caller stopped this delivery before scientific admission.');
        const admission = await check(mission, result, prepared.binding);
        requireThat(admission?.accepted === true && admission.proof?.accepted === true, 'SEMANTIC_ADMISSION', 'The external mission checker did not accept this result.', { admission: admission ?? null });
        const proof = admission.proof;
        requireThat(proof.missionId === mission.missionId && proof.inputSha256 === prepared.binding.inputSha256 && proof.capabilityHash === prepared.binding.capabilityId, 'PROOF_BINDING', 'Independent proof does not bind this mission input and capability.');
        requireThat(admission.artifact && proof.artifactSha256 === proofHash(admission.artifact), 'ARTIFACT_BINDING', 'Independent proof does not bind the supplied canonical artifact.');
        const expectedGroups = prepared.rows.map(row => ({ group: row.group, total: Number(row.amount) }));
        requireThat(canonical(admission.artifact.output?.groups) === canonical(expectedGroups) && String(admission.artifact.output?.total) === prepared.total, 'ARTIFACT_OUTPUT_BINDING', 'Canonical artifact differs from the exact normalized output groups.');
        requireThat(!signal?.aborted, 'INTERRUPTED', 'Caller stopped this delivery before native execution.');
        bridgePromise ??= createBridge(repositories);
        const bridge = await bridgePromise;
        const native = await bridge.run({ csv: prepared.csv, missionId: mission.missionId, projectId, cycleId, parentProject, language, unit: mission.kind === 'bom-demand' ? 'exact required part units' : mission.kind === 'remediation-impact' ? 'unique affected-service indicators' : 'declared integer units' });
        const actualGroups = native.result.groups.map(group => ({ group: group.group, total: group.total })).sort((a, b) => compare(a.group, b.group));
        requireThat(canonical(actualGroups) === canonical(expectedGroups) && String(native.result.total) === prepared.total, 'NATIVE_GROUP_MISMATCH', 'Native results differ from at least one canonical output group or the signed total.');
        requireThat(native.originalMissionIdPreserved, 'NATIVE_MISSION_IDENTITY', 'Native mission identity was not preserved.');
        requireThat(!signal?.aborted, 'INTERRUPTED_AFTER_NATIVE', 'Caller interrupted the bounded native computation; artifacts are retained in this error.', { native });
        const transferBindings = Object.fromEntries(['alpha', 'manager', 'jobs', 'fleet'].map(repository => [repository, { missionId: mission.missionId, graphBindingSha256: prepared.bindingSha256, artifactSha256: hashBytes(native.artifacts[repository]), scientificArtifactSha256: proof.artifactSha256, scientificProofSha256: proofHash(proof) }]));
        const record = { schema: 'tae/integrated-delivery-v1', status: 'local-source-composition-executed', missionId: mission.missionId, binding: prepared.binding, bindingSha256: prepared.bindingSha256, admission: clone(admission), transferBindings, native, metrics: { elapsedMs: performance.now() - started, cpuMicroseconds: process.cpuUsage(cpu), providerCalls: 0, fundsMoved: '0' }, authority: [], semanticChecks: 'external mission checker', nativeChecks: 'fixed arithmetic and artifact checks', settlement: 'not-connected', interruptionScope: 'Before admission or after bounded native run; native worker API provides no mid-call cancellation.' };
        completed++; events.push({ key, missionId: mission.missionId, status: 'complete', elapsedMs: record.metrics.elapsedMs }); return record;
      } catch (error) { failed++; events.push({ key, missionId: mission.missionId, status: 'failed', code: error.code ?? error.message, elapsedMs: performance.now() - started }); jobs.delete(key); throw error; }
      finally { if (acquired) release(); }
    })();
    jobs.set(key, pending); return pending;
  }
  function statistics() { return clone({ concurrency, maxQueued, active, queued: queue.length, maxObserved, completed, failed, idempotentReuses: reused, events, sourceBridgeSha256: hashBytes(readFileSync(new URL('./source-bridge.mjs', import.meta.url))) }); }
  return { deliver, statistics };
}
