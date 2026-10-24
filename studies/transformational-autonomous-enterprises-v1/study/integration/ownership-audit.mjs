// SPDX-License-Identifier: Apache-2.0
// External revalidation of export/restore and a real symbolic strategy change.
import { readFileSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { createWorkspace, solve, exportWorkspace, restoreWorkspace } from '../enterprise/compiler.mjs';
import { checkArtifact } from '../evaluation/checker.mjs';
import { externalAdmission } from './artifact.mjs';
import { proofHash } from './mission-delivery.mjs';

const inputPath = process.argv[2] ?? 'study/results/journey-inputs/examples.json';
const outputPath = process.argv[3] ?? 'study/results/ownership-audit.json';
const examples = JSON.parse(readFileSync(inputPath, 'utf8'));
const criteria = readFileSync(new URL('../evaluation/criteria.json', import.meta.url), 'utf8');
const check = externalAdmission(checkArtifact, criteria);
const parent = examples.parent.result;
const successor = examples.successor.result;
const parentSerializedBefore = JSON.stringify(parent);
const successorSerializedBefore = JSON.stringify(successor);
const exported = exportWorkspace(successor.workspace);
const restored = restoreWorkspace(exported);
assert.deepEqual(restored.history, successor.workspace.history);
assert.deepEqual(restored.capability, successor.workspace.capability);
assert.equal(restored.currentProof, null); assert.deepEqual(restored.authority, []);
const descendant = createWorkspace({ id: 'ownership-generation-3', parent: { ...restored, currentProof: examples.successor.proof, authority: ['not-an-authorized-grant'] } });
assert.equal(descendant.currentProof, null); assert.deepEqual(descendant.authority, []);
const swapped = restoreWorkspace(exportWorkspace(descendant), { modelId: 'dfs-v1' });
const mission = { ...examples.parent.mission, missionId: 'ownership-generation-3-bom' };
const third = solve(mission, { workspace: swapped });
assert.equal(third.status, 'complete');
assert.deepEqual(third.rows, parent.rows);
assert.ok(third.reuseLedger.modelChanged); assert.ok(third.reuseLedger.changed.includes('representation.mjs'));
const receipt = await check(mission, third);
assert.equal(receipt.accepted, true);
for (const result of [parent, successor, third]) {
  assert.notEqual(result.capability.id, result.capability.parentCapabilityId);
  assert.equal(result.currentProof, null); assert.deepEqual(result.authority, []);
}
assert.equal(third.workspace.history.length, 3);
assert.deepEqual(third.workspace.history.slice(0, 2), successor.workspace.history);
assert.equal(third.capability.parentCapabilityId, successor.capability.id);
assert.equal(JSON.stringify(parent), parentSerializedBefore); assert.equal(JSON.stringify(successor), successorSerializedBefore);
const costs = [parent, successor, third].map(result => ({ missionId: result.missionId, ...result.metrics }));
const result = {
  schema: 'tae/customer-state-control-audit-v1', createdAt: new Date().toISOString(), inputPath,
  passed: true, independentSemanticRevalidation: receipt,
  export: { sha256WithNewline: proofHash(JSON.parse(exported)), bytes: Buffer.byteLength(exported), survives: ['typed executable programs', 'module hashes and dependencies', 'mission history', 'historical provenance'], reset: ['current proof', 'authority'], checksumIsSignature: false },
  restore: restored.restore,
  descendant: { generation: descendant.generation, historicalEvidenceCount: descendant.historicalEvidence.length, currentProof: descendant.currentProof, authority: descendant.authority },
  modelSwap: { before: successor.model, after: third.model, sourceCodeChanged: false, actualAlgorithmChanged: 'Kahn topological queue to DFS topological traversal', identicalAnswersForRepeatedBOM: true, requestedRequalification: third.validationRequest, learnedProviderSwap: 'unverified' },
  lineage: [parent, successor, third].map(result => ({ missionId: result.missionId, workspaceId: result.workspace.id, parentWorkspaceId: result.workspace.parentId, generation: result.workspace.generation, capabilityId: result.capability.id, parentCapabilityId: result.capability.parentCapabilityId, historyLength: result.workspace.history.length, currentProof: result.currentProof, authority: result.authority })),
  cumulativeEvidence: { resultRecordsPreservedSeparately: true, records: costs, totals: { operations: costs.reduce((sum, item) => sum + item.operations, 0), hashBytes: costs.reduce((sum, item) => sum + item.hashBytes, 0), candidateElapsedMs: costs.reduce((sum, item) => sum + item.elapsedMs, 0), providerCalls: 0, fundsMoved: '0' }, costsAreDollars: false },
  thirdMission: { mission, result: third }, limits: ['Three-generation finite development audit, not universal inheritance.', 'Separate evaluator implementation under the same controller.', 'Proof receipts remain outside candidate state.', 'Workspace checksum is not authority or a cryptographic signature.', 'Candidate and native source swaps do not establish a learned-provider swap.']
};
writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({ outputPath, passed: result.passed, generations: result.lineage, modelSwap: result.modelSwap, cumulative: result.cumulativeEvidence.totals }, null, 2));
