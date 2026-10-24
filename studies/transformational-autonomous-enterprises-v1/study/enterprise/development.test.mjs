// SPDX-License-Identifier: Apache-2.0
// Development checks; no evaluator receipts and no hidden-bank access.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createWorkspace, solve, exportWorkspace, restoreWorkspace, sourceManifest } from './compiler.mjs';
import { buildRepresentation, parseGraph, topologicalOrder } from './representation.mjs';
import { weightedReduce } from './kernel-weighted.mjs';
import { booleanReduce } from './kernel-boolean.mjs';
import { createMeter } from './protocol.mjs';
import { diamondBOM, diamondImpact, flatControl } from './development-cases.mjs';

test('weighted diamond retains both paths; successor reachability is idempotent', () => {
  const parent = solve(diamondBOM);
  assert.equal(parent.status, 'complete');
  assert.deepEqual(parent.rows, [{ group: 'assembly', amount: '2' }, { group: 'branch-left', amount: '4' }, { group: 'branch-right', amount: '6' }, { group: 'shared-part', amount: '62' }]);
  const child = solve(diamondImpact, { workspace: createWorkspace({ id: 'successor', parent: parent.workspace }) });
  assert.equal(child.status, 'complete');
  assert.deepEqual(child.rows, [{ group: 'customer-service', amount: '1' }, { group: 'gateway', amount: '1' }, { group: 'isolated-service', amount: '0' }, { group: 'library', amount: '1' }, { group: 'worker', amount: '1' }]);
  assert.deepEqual(Object.keys(parent.capability.programs), ['bom-demand']);
  assert.deepEqual(child.reuseLedger.added, ['kernel-boolean.mjs']);
  assert.ok(child.reuseLedger.retained.includes('representation.mjs'));
  assert.equal(child.workspace.parentId, parent.workspace.id);
  assert.equal(child.workspace.history.length, 2);
  assert.equal(child.currentProof, null); assert.deepEqual(child.authority, []);
});

test('direct module APIs preserve parallel edges, duplicate seeds, zero and disconnected values', () => {
  const dag = buildRepresentation({ nodes: ['a', 'b', 'z'], edges: [{ from: 'a', to: 'b', weight: 2 }, { from: 'a', to: 'b', weight: 2 }] });
  const query = { seeds: [{ node: 'a', amount: 3 }, { node: 'a', amount: 2 }, { node: 'z', amount: 0 }], targets: ['b', 'z'] };
  assert.deepEqual(weightedReduce(dag, query), [{ group: 'b', amount: '20' }, { group: 'z', amount: '0' }]);
  assert.deepEqual(booleanReduce(dag, query), [{ group: 'b', amount: '1' }, { group: 'z', amount: '0' }]);
});

test('reordering input leaves canonical representation invariant under one strategy', () => {
  const a = buildRepresentation(diamondBOM.graph);
  const b = buildRepresentation({ nodes: [...diamondBOM.graph.nodes].reverse(), edges: [...diamondBOM.graph.edges].reverse() });
  assert.deepEqual(a, b);
  assert.ok(topologicalOrder(parseGraph(diamondBOM.graph)).indexOf('assembly') < topologicalOrder(parseGraph(diamondBOM.graph)).indexOf('shared-part'));
});

test('cycle, undeclared endpoint, unsafe integer, duplicate target, and excessive graph refuse', () => {
  const variants = [
    { ...diamondBOM, graph: { ...diamondBOM.graph, edges: [...diamondBOM.graph.edges, { from: 'shared-part', to: 'assembly', weight: 1 }] } },
    { ...diamondBOM, graph: { ...diamondBOM.graph, edges: [{ from: 'absent', to: 'assembly', weight: 1 }] } },
    { ...diamondBOM, seeds: [{ node: 'assembly', amount: Number.MAX_SAFE_INTEGER + 1 }] },
    { ...diamondBOM, targets: ['assembly', 'assembly'] },
    { ...diamondBOM, graph: { nodes: Array.from({ length: 65 }, (_, i) => `node-${i}`), edges: [] } }
  ];
  for (const mission of variants) { const result = solve(mission); assert.equal(result.status, 'refused'); assert.equal(result.rows, null); assert.equal(result.capability, null); assert.equal(result.workspace.history.at(-1).status, 'refused'); }
});

test('exact internal completion does not pretend oversized outputs are deliverable', () => {
  const result = solve({ ...diamondBOM, seeds: [{ node: 'assembly', amount: 1000000 }] });
  assert.equal(result.status, 'complete'); assert.equal(result.delivery.status, 'infeasible');
  assert.equal(result.rows.find(row => row.group === 'shared-part').amount, '31000000');
  const totalOnly = solve({ ...flatControl, rows: [{ group: 'a', amount: 600000 }, { group: 'b', amount: 600000 }] });
  assert.equal(totalOnly.status, 'complete'); assert.equal(totalOnly.delivery.status, 'infeasible'); assert.equal(totalOnly.delivery.totalExceeded, true); assert.deepEqual(totalOnly.delivery.excessiveGroups, []);
  assert.equal(solve({ ...flatControl, rows: [{ group: 'a', amount: 1000001 }] }).status, 'refused');
  assert.equal(solve({ ...diamondBOM, seeds: [] }).status, 'refused');
  assert.equal(solve({ ...flatControl, rows: [{ group: 'unadmitted space', amount: 1 }] }).status, 'refused');
});

test('budget exhaustion and kill switch retain failures and no output', () => {
  for (const options of [{ budget: { operations: 2 } }, { budget: { hashBytes: 10 } }, { budget: { elapsedMs: 0 } }]) {
    const result = solve(diamondBOM, options); assert.equal(result.status, 'exhausted'); assert.equal(result.rows, null); assert.equal(result.metrics.failedRunRetained, true);
  }
  const result = solve(diamondBOM, { signal: { aborted: true } }); assert.equal(result.status, 'interrupted'); assert.equal(result.rows, null);
  const controller = new AbortController(); const meter = createMeter({}, controller.signal); controller.abort(); assert.throws(() => meter.tick('stopped'), { code: 'INTERRUPTED' });
});

test('export/restore retains history and typed assets, resets current proof/authority', () => {
  const parent = solve(diamondBOM).workspace;
  const text = exportWorkspace(parent); const restored = restoreWorkspace(text);
  assert.deepEqual(restored.capability, parent.capability); assert.deepEqual(restored.history, parent.history); assert.equal(restored.currentProof, null); assert.deepEqual(restored.authority, []);
  assert.throws(() => restoreWorkspace(text.replace('public-development-bom', 'forged-mission-id')), { code: 'EXPORT_CHECKSUM' });
  const descendant = createWorkspace({ id: 'reset-child', parent: { ...parent, currentProof: { claimed: 'externally-supplied' }, authority: ['transfer'] } });
  assert.equal(descendant.currentProof, null); assert.deepEqual(descendant.authority, []); assert.equal(descendant.historicalEvidence.length, 1);
  const denied = solve(diamondBOM, { workspace: { ...parent, authority: ['transfer'] } }); assert.equal(denied.status, 'refused'); assert.equal(denied.failure.code, 'NONEMPTY_AUTHORITY');
});

test('symbolic strategy swap preserves answers but requests representation requalification', () => {
  const parent = solve(diamondBOM);
  const swapped = restoreWorkspace(exportWorkspace(parent.workspace), { modelId: 'dfs-v1' });
  const child = solve(diamondImpact, { workspace: swapped });
  assert.deepEqual(child.rows, solve(diamondImpact).rows); assert.equal(child.reuseLedger.modelChanged, true); assert.ok(child.reuseLedger.changed.includes('representation.mjs')); assert.equal(child.model.learnedProviderSwap, 'unverified');
  assert.equal(child.currentProof, null); assert.deepEqual(child.authority, []);
});

test('ablations expose their failure without claiming independent acceptance', () => {
  assert.equal(solve(diamondBOM, { variant: 'no-construction' }).status, 'refused');
  assert.equal(solve(flatControl, { variant: 'no-construction' }).status, 'complete');
  const correct = solve(diamondImpact);
  const wrong = solve(diamondImpact, { variant: 'wrong-algebra' });
  const old = solve(diamondImpact, { variant: 'old-representation' });
  assert.notDeepEqual(wrong.rows, correct.rows); assert.notDeepEqual(old.rows, correct.rows);
  assert.equal(wrong.independentAcceptance, 'not-established-by-candidate');
  assert.deepEqual(solve(diamondImpact, { variant: 'direct-specialist' }).rows, correct.rows);
});

test('no inheritance rebuilds only required program and names all requalification modules', () => {
  const parent = solve(diamondBOM);
  const result = solve(diamondImpact, { workspace: parent.workspace, variant: 'no-inheritance' });
  assert.deepEqual(Object.keys(result.capability.programs), ['remediation-impact']); assert.deepEqual(result.reuseLedger.retained, []);
  assert.deepEqual(result.validationRequest.qualificationModules, result.capability.modules.map(module => module.name));
});

test('three generations preserve lineage without self-parent edges or changing prior cost evidence', () => {
  const first = solve(diamondBOM);
  const firstSnapshot = JSON.stringify(first);
  const second = solve(diamondImpact, { workspace: createWorkspace({ id: 'generation-2', parent: first.workspace }) });
  const secondSnapshot = JSON.stringify(second);
  const third = solve({ ...diamondImpact, missionId: 'generation-3-mission' }, { workspace: createWorkspace({ id: 'generation-3', parent: second.workspace }) });
  assert.notEqual(second.capability.id, first.capability.id);
  assert.equal(second.capability.parentCapabilityId, first.capability.id);
  assert.equal(third.capability.id, second.capability.id);
  assert.equal(third.capability.parentCapabilityId, first.capability.id);
  assert.equal(third.capability.provenance.parentCapabilityId, first.capability.id);
  for (const result of [first, second, third]) { assert.notEqual(result.capability.id, result.capability.parentCapabilityId); assert.equal(result.currentProof, null); assert.deepEqual(result.authority, []); }
  assert.equal(third.workspace.generation, 2); assert.equal(third.workspace.history.length, 3);
  assert.deepEqual(third.workspace.history.slice(0, 2), second.workspace.history);
  assert.equal(JSON.stringify(first), firstSnapshot); assert.equal(JSON.stringify(second), secondSnapshot);
  assert.ok([first, second, third].reduce((sum, result) => sum + result.metrics.hashBytes, 0) > third.metrics.hashBytes);
});

test('source identities, candidate mutation boundaries, and instrumentation are inspectable', () => {
  const manifest = sourceManifest(); assert.equal(manifest.installedCatalog.length, 7);
  for (const module of manifest.installedCatalog) { assert.match(module.sha256, /^[a-f0-9]{64}$/u); assert.ok(module.bytes > 0); }
  const result = solve(diamondBOM); assert.ok(Object.isFrozen(result.workspace.capability.programs));
  assert.ok(result.metrics.hashBytes > manifest.installedCatalog.reduce((sum, module) => sum + module.bytes, 0));
  assert.equal(result.metrics.operations, result.metrics.controlOperations + result.metrics.constructionOperations + result.metrics.executionOperations);
  assert.equal(result.metrics.hashBytes, result.metrics.controlHashBytes + result.metrics.constructionHashBytes + result.metrics.executionHashBytes);
  assert.equal(result.metrics.providerCalls, 0); assert.equal(result.metrics.fundsMoved, '0');
});
