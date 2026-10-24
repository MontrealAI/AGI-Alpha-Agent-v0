// SPDX-License-Identifier: Apache-2.0
// A finite typed module catalog and inspectable executable IR, not source synthesis.
import { readFileSync } from 'node:fs';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';
import { CandidateError, LIMITS, invariant, exactKeys, label, deepFreeze, canonical, copy, digest, createMeter } from './protocol.mjs';
import { buildRepresentation, bindQuery, STRATEGIES } from './representation.mjs';
import { weightedReduce } from './kernel-weighted.mjs';
import { booleanReduce } from './kernel-boolean.mjs';
import { flatReduce, normalizeRows } from './normalizer.mjs';
import { directReduce } from './direct-specialist.mjs';

export const VARIANTS = Object.freeze(['full-loop', 'no-inheritance', 'no-construction', 'wrong-algebra', 'old-representation', 'direct-specialist']);
export const MISSION_KINDS = Object.freeze(['bom-demand', 'remediation-impact', 'flat-reduction']);
const moduleDefinitions = Object.freeze({
  'protocol.mjs': { exports: ['createMeter', 'canonical', 'digest'], dependencies: [] },
  'representation.mjs': { exports: ['parseGraph', 'topologicalOrder', 'buildRepresentation', 'bindQuery'], dependencies: ['protocol.mjs'] },
  'kernel-weighted.mjs': { exports: ['weightedReduce'], dependencies: ['protocol.mjs', 'representation.mjs'] },
  'kernel-boolean.mjs': { exports: ['booleanReduce'], dependencies: ['protocol.mjs', 'representation.mjs'] },
  'normalizer.mjs': { exports: ['flatReduce', 'normalizeRows'], dependencies: ['protocol.mjs'] },
  'direct-specialist.mjs': { exports: ['directReduce'], dependencies: ['protocol.mjs', 'representation.mjs', 'normalizer.mjs'] },
  'compiler.mjs': { exports: ['createWorkspace', 'solve', 'executeProgram', 'exportWorkspace', 'restoreWorkspace', 'sourceManifest'], dependencies: ['protocol.mjs', 'representation.mjs', 'kernel-weighted.mjs', 'kernel-boolean.mjs', 'normalizer.mjs', 'direct-specialist.mjs'] }
});

export function sourceManifest({ meter } = {}) {
  meter ??= createMeter();
  const modules = Object.entries(moduleDefinitions).map(([name, definition]) => {
    meter.tick('source-file-read'); const source = readFileSync(new URL(name, import.meta.url));
    return { name, sha256: meter.hash(source, 'source-file'), bytes: source.byteLength, exports: [...definition.exports], dependencies: [...definition.dependencies] };
  });
  return deepFreeze({ schema: 'tae/source-manifest-v1', language: 'ECMAScript modules', runtime: process.version, installedCatalog: modules, rootSha256: meter.hash(modules, 'source-inventory'), qualification: 'not-established-by-candidate' });
}

function emptyPermissions(value) {
  const result = copy(value);
  result.currentProof = null; result.authority = [];
  if (result.capability) { result.capability.currentProof = null; result.capability.authority = []; }
  return result;
}
function validateWorkspace(workspace) {
  invariant(workspace?.schema === 'tae/workspace-v1', 'INVALID_WORKSPACE', 'Expected a versioned candidate workspace.');
  label(workspace.id, 'workspace id');
  invariant(STRATEGIES.includes(workspace.modelId), 'UNKNOWN_MODEL', 'Unknown symbolic model identity.');
  invariant(Array.isArray(workspace.history) && workspace.history.length <= 10000, 'HISTORY_LIMIT', 'History must be a bounded array.');
  invariant(workspace.currentProof === null && Array.isArray(workspace.authority) && workspace.authority.length === 0, 'NONEMPTY_AUTHORITY', 'The candidate cannot hold a current proof or authority.');
  if (workspace.capability) {
    invariant(workspace.capability.schema === 'tae/capability-v1' && typeof workspace.capability.id === 'string', 'INVALID_CAPABILITY', 'Unsupported capability manifest.');
    invariant(workspace.capability.currentProof === null && workspace.capability.authority?.length === 0, 'NONEMPTY_AUTHORITY', 'Capability proof and authority must remain empty.');
    invariant(workspace.capability.programs && Array.isArray(workspace.capability.modules), 'INVALID_CAPABILITY', 'Capability lacks executable programs or module identities.');
  }
  return workspace;
}
export function createWorkspace({ id = 'writer4-enterprise', modelId = 'kahn-v1', parent = null } = {}) {
  label(id, 'workspace id'); invariant(STRATEGIES.includes(modelId), 'UNKNOWN_MODEL', 'Only declared symbolic model identities are supported.');
  let historicalEvidence = []; let capability = null; let history = []; let generation = 0;
  if (parent) {
    invariant(parent.schema === 'tae/workspace-v1', 'INVALID_WORKSPACE', 'Parent workspace schema is unsupported.');
    // A caller-supplied receipt is history only. Descendants never inherit it as proof.
    historicalEvidence = [...(parent.historicalEvidence ?? []), ...(parent.currentProof ? [{ type: 'untrusted-imported-historical-proof', value: copy(parent.currentProof) }] : [])];
    const sanitized = emptyPermissions(parent); validateWorkspace(sanitized);
    capability = sanitized.capability; history = sanitized.history; generation = parent.generation + 1;
  }
  return deepFreeze({ schema: 'tae/workspace-v1', id, generation, parentId: parent?.id ?? null, modelId, modelKind: 'deterministic-symbolic-traversal', learnedProviderSwap: 'unverified', capability, history, historicalEvidence, currentProof: null, authority: [] });
}
export function exportWorkspace(workspace) {
  const snapshot = emptyPermissions(workspace); validateWorkspace(snapshot);
  return canonical({ schema: 'tae/workspace-export-v1', payload: snapshot, sha256: digest(snapshot), warning: 'Checksum detects accidental corruption; it is not a signature, certification, or permission.' });
}
export function restoreWorkspace(serialized, { modelId } = {}) {
  invariant(typeof serialized === 'string' && Buffer.byteLength(serialized) <= 20000000, 'EXPORT_LIMIT', 'Export must be a bounded JSON string.');
  let envelope; try { envelope = JSON.parse(serialized); } catch { throw new CandidateError('INVALID_EXPORT', 'Export is not valid JSON.'); }
  invariant(envelope.schema === 'tae/workspace-export-v1' && digest(envelope.payload) === envelope.sha256, 'EXPORT_CHECKSUM', 'Export checksum or schema is invalid.');
  const restored = emptyPermissions(envelope.payload); validateWorkspace(restored);
  const nextModel = modelId ?? restored.modelId; invariant(STRATEGIES.includes(nextModel), 'UNKNOWN_MODEL', 'Unknown symbolic model identity.');
  restored.modelId = nextModel;
  restored.restore = { sourceCompatibility: 'requires-external-revalidation', modelChanged: nextModel !== envelope.payload.modelId, currentProofReset: true, authorityReset: true };
  return deepFreeze(restored);
}

function programFor(kind, modelId) {
  invariant(kind === 'bom-demand' || kind === 'remediation-impact', 'UNSUPPORTED_PROGRAM', 'Only the two declared structured algebras can be constructed.');
  const boolean = kind === 'remediation-impact';
  return {
    schema: 'tae/reduction-ir-v1', accepts: kind, representation: 'tae/dag-representation-v1', modelId,
    algebra: boolean ? 'boolean-or-and' : 'nonnegative-integer-sum-product',
    steps: [
      { module: 'representation.mjs', export: 'buildRepresentation', input: 'mission.graph', output: 'dag' },
      { module: boolean ? 'kernel-boolean.mjs' : 'kernel-weighted.mjs', export: boolean ? 'booleanReduce' : 'weightedReduce', input: ['dag', 'mission.seeds', 'mission.targets'], output: 'rows' },
      { module: 'normalizer.mjs', export: 'normalizeRows', input: 'rows', output: 'delivery' }
    ]
  };
}
function capabilityFor(kind, workspace, sources, meter, { rebuild = false } = {}) {
  const previous = workspace.capability;
  const programs = rebuild ? {} : copy(previous?.programs ?? {});
  const required = programFor(kind, workspace.modelId);
  const oldProgram = programs[kind];
  const modelChanged = Object.values(programs).some(program => program.modelId !== workspace.modelId);
  if (modelChanged) for (const missionKind of Object.keys(programs)) programs[missionKind] = programFor(missionKind, workspace.modelId);
  programs[kind] = required;
  const names = new Set(['protocol.mjs', 'representation.mjs', 'normalizer.mjs']);
  for (const program of Object.values(programs)) for (const step of program.steps) names.add(step.module);
  const modules = sources.installedCatalog.filter(module => names.has(module.name)).map(module => { meter.tick('bind-capability-module'); return copy(module); });
  const retained = []; const changed = []; const added = []; const rebuilt = [];
  for (const module of modules) {
    const old = previous?.modules.find(entry => entry.name === module.name);
    if (rebuild) rebuilt.push(module.name);
    else if (!old) added.push(module.name);
    else if (old.sha256 === module.sha256 && !(modelChanged && module.name === 'representation.mjs')) retained.push(module.name);
    else changed.push(module.name);
  }
  const typedDefinition = { programs, modules, limits: LIMITS, modelId: workspace.modelId };
  const id = meter.hash(typedDefinition, 'capability-definition');
  const parentCapabilityId = id === previous?.id ? previous.parentCapabilityId : previous?.id ?? null;
  const constructionRequired = rebuild || !oldProgram || modelChanged || changed.length > 0 || added.length > 0;
  if (constructionRequired) { for (const program of Object.values(programs)) for (const step of program.steps) { meter.tick('construct-typed-instruction'); invariant(moduleDefinitions[step.module]?.exports.includes(step.export), 'INVALID_IR', 'IR references an unavailable module export.'); } }
  const capability = {
    schema: 'tae/capability-v1', id, version: 1, name: 'bounded-graph-to-reduction', parentCapabilityId,
    construction: 'finite typed executable IR assembled from declared preimplemented modules',
    inputs: ['weighted DAG, seeds, unique targets'], outputs: ['exact canonical decimal rows', 'bounded CSV delivery'],
    programs, modules, limits: { ...LIMITS }, modelId: workspace.modelId,
    provenance: { sourceCatalogSha256: sources.rootSha256, parentCapabilityId },
    verification: 'Candidate structural checks only; independent mission and module evaluation required.',
    costs: { constructionOperations: null, marginalExecutionOperations: null, pricing: 'not-assigned' },
    currentProof: null, authority: []
  };
  return { capability: deepFreeze(capability), ledger: deepFreeze({ retained, added, changed, rebuilt, modelChanged, constructed: constructionRequired }), validationRequest: { requestedOnly: true, missionOutput: 'always', qualificationModules: rebuild ? modules.map(module => module.name) : [...added, ...changed], qualificationStatus: 'not-established', reusableModuleHistoryIsNotMissionProof: true } };
}

export function executeProgram(program, mission, { meter, modelId = program?.modelId } = {}) {
  meter ??= createMeter();
  invariant(program?.schema === 'tae/reduction-ir-v1' && program.accepts === mission.kind, 'PROGRAM_MISSION_MISMATCH', 'Executable program does not accept this mission kind.');
  invariant(canonical(program) === canonical(programFor(mission.kind, modelId)), 'INVALID_IR', 'Program differs from the declared typed grammar.');
  const representation = buildRepresentation(mission.graph, { meter, strategy: modelId });
  const query = { seeds: mission.seeds, targets: mission.targets };
  const rows = program.algebra === 'boolean-or-and' ? booleanReduce(representation, query, { meter }) : weightedReduce(representation, query, { meter });
  return { representation, rows };
}

function validateMission(mission, meter) {
  invariant(mission?.schema === 'tae/mission-v1', 'INVALID_SCHEMA', 'Mission schema must be tae/mission-v1.');
  invariant(MISSION_KINDS.includes(mission.kind), 'UNSUPPORTED_KIND', 'Mission kind is outside the declared population.');
  exactKeys(mission, mission.kind === 'flat-reduction' ? ['schema', 'missionId', 'kind', 'rows'] : ['schema', 'missionId', 'kind', 'graph', 'seeds', 'targets']);
  label(mission.missionId, 'mission id'); meter.tick('validate-mission-envelope');
}

export function solve(mission, { workspace = createWorkspace(), variant = 'full-loop', budget = {}, signal } = {}) {
  const started = performance.now(); const cpuStart = process.cpuUsage();
  const meter = createMeter(budget, signal); const trace = []; let stage = 'Identify';
  let state = workspace; let sources = null; let capability = workspace?.capability ?? null; let reuseLedger = null; let validationRequest = null; let representation = null; let representationHash = null; let output = null; let status = 'complete'; let failure = null; let inputHash = null; let outputHash = null;
  const begin = (name, phase, explanation, details = {}) => { stage = name; meter.setPhase(phase, name); trace.push({ stage: name, status: 'started', explanation, details, atMs: performance.now() - started }); };
  const finish = (details = {}) => { const event = trace.at(-1); event.status = 'complete'; event.output = details; event.finishedAtMs = performance.now() - started; };
  const skip = (name, why) => trace.push({ stage: name, status: 'justified-skip', explanation: why, atMs: performance.now() - started });
  try {
    invariant(VARIANTS.includes(variant), 'UNKNOWN_VARIANT', 'Unknown comparison variant.'); validateWorkspace(workspace);
    begin('Identify', 'control', 'Declare the mission, unresolved demand hypothesis, and bounded task domain.');
    validateMission(mission, meter); inputHash = meter.hash(mission, 'mission-input');
    finish({ missionId: mission.missionId, kind: mission.kind, demand: 'synthetic research task; external customer demand unverified', bindingConstraint: 'native CSV execution does not encode structured graph semantics', inputHash });
    begin('Out-Learn', 'control', 'Read exact installed module identities and retain only bounded structural knowledge.');
    sources = sourceManifest({ meter });
    finish({ sourceCatalogSha256: sources.rootSha256, learnedProviderCalls: 0, limitation: 'Source inventory is not independent correctness qualification.' });
    if (variant === 'no-construction' && mission.kind !== 'flat-reduction') throw new CandidateError('CONSTRUCTION_DISABLED', 'The native flat-reduction route cannot answer structured graph missions without an enabling compiler.');
    if (variant === 'direct-specialist' || mission.kind === 'flat-reduction') {
      skip('Out-Think', mission.kind === 'flat-reduction' ? 'Flat input already matches the supported delivery representation.' : 'Matched deterministic specialist solves the mission without a reusable IR.');
      skip('Out-Design', mission.kind === 'flat-reduction' ? 'No new capability is useful for this flat control.' : 'Direct specialist constructs no inherited capability.');
    } else {
      begin('Out-Think', 'construction', 'Replace a flat aggregation assumption with an acyclic shared graph and an explicit mission algebra.');
      meter.tick('select-algebra'); finish({ representation: 'tae/dag-representation-v1', algebra: mission.kind === 'bom-demand' ? 'nonnegative-integer-sum-product' : 'boolean-or-and', invariants: ['acyclic directed graph', 'parallel-edge multiplicity retained', 'seed and target identity', 'exact output integers'] });
      begin('Out-Design', 'construction', 'Assemble or reuse an executable typed reduction program; add the Boolean kernel only for the successor grammar.');
      const built = capabilityFor(mission.kind, workspace, sources, meter, { rebuild: variant === 'no-inheritance' }); capability = built.capability; reuseLedger = built.ledger; validationRequest = built.validationRequest;
      finish({ capabilityId: capability.id, grammar: Object.keys(capability.programs), reuseLedger, verification: 'External qualification pending.' });
    }
    begin('Out-Strategise', 'control', 'Select the declared tested route within exact resource ceilings.');
    meter.tick('select-route'); finish({ chosen: variant, alternatives: ['direct-specialist', 'no-construction', 'full-loop'], selection: 'Variant assigned by experiment, not claimed globally optimal.', budget: { ...budget }, currencies: ['USDC6 route retained externally', 'AGIALPHA18 route retained externally'], fundsAuthorized: false });
    begin('Out-Execute', 'execution', 'Compute exact mission outputs and compile them into the existing bounded CSV boundary.');
    let rows;
    if (mission.kind === 'flat-reduction') rows = flatReduce(mission.rows, { meter });
    else if (variant === 'direct-specialist') ({ representation, rows } = directReduce(mission, { meter, strategy: workspace.modelId }));
    else if (variant === 'wrong-algebra') {
      representation = buildRepresentation(mission.graph, { meter, strategy: workspace.modelId });
      rows = mission.kind === 'remediation-impact' ? weightedReduce(representation, { seeds: mission.seeds, targets: mission.targets }, { meter }) : booleanReduce(representation, { seeds: mission.seeds, targets: mission.targets }, { meter });
    } else if (variant === 'old-representation') {
      // Deliberate ablation: old flat view only sees seed rows, losing transitive edges.
      representation = buildRepresentation(mission.graph, { meter, strategy: workspace.modelId });
      const checked = bindQuery(representation, { seeds: mission.seeds, targets: mission.targets }, { meter });
      const seeds = new Map(); for (const seed of mission.seeds) { meter.tick('ablation-seed-add'); seeds.set(seed.node, (seeds.get(seed.node) ?? 0n) + BigInt(seed.amount)); }
      rows = checked.targets.map(group => ({ group, amount: (mission.kind === 'remediation-impact' ? (seeds.get(group) > 0n ? 1n : 0n) : (seeds.get(group) ?? 0n)).toString() }));
    } else ({ representation, rows } = executeProgram(capability.programs[mission.kind], mission, { meter, modelId: workspace.modelId }));
    output = normalizeRows(rows, { meter }); outputHash = meter.hash(output.rows, 'mission-output');
    if (representation) representationHash = meter.hash(representation, 'compiled-representation');
    finish({ outputHash, rows: output.rows.length, delivery: output.delivery.status, independentAcceptance: 'not-established-by-candidate' });
    if (variant === 'direct-specialist' || mission.kind === 'flat-reduction') skip('Out-Evolve', 'This route produced no useful new structured capability to propose.');
    else {
      begin('Out-Evolve', 'control', 'Retain the executable program as a proposal with empty current proof and empty authority.');
      meter.tick('record-proposed-capability'); finish({ capabilityId: capability.id, promotion: 'not-performed', currentProof: null, authority: [], requires: 'Independent module qualification, mission-output evaluation, and separately granted authority.' });
    }
  } catch (error) {
    if (!(error instanceof CandidateError)) throw error;
    status = error.code === 'INTERRUPTED' ? 'interrupted' : error.code.startsWith('BUDGET_') ? 'exhausted' : 'refused';
    failure = { code: error.code, message: error.message, details: error.details, stage };
    if (trace.at(-1)?.status === 'started') { trace.at(-1).status = status; trace.at(-1).failure = failure; }
    // Partial calculations and incomplete proposals are never publishable outputs.
    output = null; outputHash = null; capability = workspace?.capability ?? null;
  }
  const metrics = { ...meter.snapshot(), cpuMicroseconds: process.cpuUsage(cpuStart), maxRSSKiB: process.resourceUsage().maxRSS, failedRunRetained: status !== 'complete' };
  if (capability && status === 'complete') capability = deepFreeze({ ...copy(capability), costs: { constructionOperationsThisRun: metrics.constructionOperations, executionOperationsThisRun: metrics.executionOperations, hashBytesThisRun: metrics.hashBytes, elapsedMsThisRun: metrics.elapsedMs, note: 'Named instrumentation events and measured time, not a price or economic valuation.' } });
  const historyEntry = { missionId: typeof mission?.missionId === 'string' ? mission.missionId : null, kind: mission?.kind ?? null, variant, status, inputHash, outputHash, capabilityId: capability?.id ?? null, failure, currentProof: null, authority: [] };
  const baseState = workspace?.schema === 'tae/workspace-v1' ? workspace : createWorkspace();
  state = emptyPermissions({ ...copy(baseState), capability, history: [...(Array.isArray(baseState.history) ? baseState.history : []), historyEntry] });
  if (state.history.length > 10000) state.history = state.history.slice(-10000);
  return deepFreeze({ schema: 'tae/candidate-result-v1', missionId: historyEntry.missionId, kind: historyEntry.kind, variant, status, failure, rows: output?.rows ?? null, csv: output?.csv ?? null, delivery: output?.delivery ?? null, inputHash, outputHash, representation: representationHash ? { schema: representation.schema, sha256: representationHash, modelId: representation.strategy, nodes: representation.nodes.length, edges: representation.edges.length } : null, sources, capability, reuseLedger, validationRequest, trace, metrics, workspace: state, model: { id: workspace?.modelId ?? null, kind: 'deterministic-symbolic-traversal', learnedProviderSwap: 'unverified' }, currentProof: null, authority: [], independentAcceptance: 'not-established-by-candidate' });
}

export const SOURCE_DIRECTORY = fileURLToPath(new URL('.', import.meta.url));
