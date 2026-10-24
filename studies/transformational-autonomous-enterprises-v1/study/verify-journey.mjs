// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { canonicalBytes } from './integration/mission-delivery.mjs';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const STAGES = ['Commit mission and evaluator bytes', 'Open local risk review', 'Local staked risk attestation', 'Local staked risk attestation', 'Open plan-restricted funding', 'Fund with local fixture tokens', 'Activate local plan treasury', 'Route committed bounded job', 'Collateral-backed local bid', 'Assign the bounded job', 'Deliver exact checked artifact', 'Local exact-artifact validator vote', 'Local exact-artifact validator vote', 'Collect unused job escrow', 'Close completed campaign', 'Return unused local capital'];

/** Verify the join, not just two unrelated successful subsystems. */
export function verifyJourney(journey, evm) {
  const joins = [];
  const transactionHashes = new Set();
  for (const [name, receipt] of [['parent', evm], ['successor', evm.successorLifecycle]]) {
    const delivery = journey[name];
    assert(delivery && receipt, 'Two complete deliveries and EVM receipts required');
    assert.equal(delivery.missionId, receipt.missionId);
    assert.equal(delivery.admission.accepted, true);
    assert.equal(delivery.admission.proof.accepted, true);
    const artifact = delivery.admission.artifact, proof = delivery.admission.proof;
    assert.equal(artifact.missionId, receipt.missionId);
    assert.equal(proof.missionId, receipt.missionId);
    assert.equal(delivery.binding.missionId, receipt.missionId);
    assert.equal(artifact.inputHash, proof.inputSha256);
    assert.equal(proof.inputSha256, receipt.inputSha256);
    assert.equal(proof.capabilityHash, receipt.capabilityHash);
    assert.equal(artifact.capabilityHash, receipt.capabilityHash);
    assert.equal(proof.artifactSha256, receipt.artifactSha256);
    assert.equal(artifact.currentProof, null); assert.deepEqual(artifact.authority, []);
    assert.deepEqual(proof.authority, []); assert.deepEqual(proof.failures, []);
    assert.equal(delivery.bindingSha256, sha(canonicalBytes(delivery.binding).trimEnd()), 'Graph binding digest differs');
    assert.equal(receipt.bundleComponents.artifactSha256, receipt.artifactSha256);
    assert.equal(receipt.bundleComponents.proofSha256, receipt.proofSha256);
    assert.equal(receipt.candidateBinding.sourceCatalogSha256, delivery.binding.sourceCatalogSha256);
    assert.equal(sha(canonicalBytes(delivery.admission.artifact)), receipt.artifactSha256);
    assert.equal(sha(canonicalBytes(delivery.admission.proof)), receipt.proofSha256);
    assert.equal(delivery.binding.capabilityId, receipt.capabilityHash);
    assert.equal(delivery.binding.inputSha256, receipt.inputSha256);
    assert.deepEqual(delivery.native.result.groups.map(({ group, total }) => ({ group, total })), delivery.admission.artifact.output.groups);
    assert.equal(delivery.native.result.total, delivery.admission.artifact.output.total);
    for (const repository of ['alpha', 'manager', 'jobs', 'fleet']) {
      const binding = delivery.transferBindings[repository];
      assert.equal(binding.missionId, receipt.missionId);
      assert.equal(binding.graphBindingSha256, delivery.bindingSha256, 'Repository envelope graph binding differs');
      assert.equal(binding.scientificArtifactSha256, receipt.artifactSha256);
      assert.equal(binding.scientificProofSha256, receipt.proofSha256);
      assert.equal(binding.artifactSha256, sha(delivery.native.artifacts[repository]));
    }
    assert.equal(receipt.chainId, '31337');
    assert.equal(receipt.lineageBeforeReview.currentProof, null);
    assert.deepEqual(receipt.lineageBeforeReview.authority, []);
    assert.equal(receipt.lineageBeforeReview.riskApproved, false);
    assert.equal(receipt.authority.productionAuthority, false);
    assert.equal(receipt.steps.length, 16, 'The declared16-stage local lifecycle must be complete');
    assert.deepEqual(receipt.steps.map(step => step.stage), STAGES, 'Lifecycle stage order differs from the fixed adapter');
    assert(receipt.steps.every(step => Number(step.status) === 1), 'All lifecycle receipts must succeed');
    let previousBlock = 0;
    for (const step of receipt.steps) {
      assert(/^0x[0-9a-f]{64}$/.test(step.transactionHash) && !transactionHashes.has(step.transactionHash), 'Distinct local transaction hashes required');
      transactionHashes.add(step.transactionHash);
      assert(Number.isSafeInteger(step.block) && step.block > previousBlock, 'Ordered lifecycle blocks required');
      previousBlock = step.block;
      assert(BigInt(step.gasUsed) > 0n);
    }
    assert.equal(BigInt(receipt.lifecycleGasUsed), receipt.steps.reduce((total, step) => total + BigInt(step.gasUsed), 0n));
    const a = receipt.accounting;
    assert.equal(BigInt(a.funded), BigInt(a.workerNet) + BigInt(a.validatorsNet) + BigInt(a.burned) + BigInt(a.refunded));
    assert.equal(BigInt(a.remainingReserve), 0n);
    joins.push({ missionId: receipt.missionId, artifactSha256: receipt.artifactSha256, proofSha256: receipt.proofSha256, capabilityHash: receipt.capabilityHash, seedId: receipt.seedId, jobId: receipt.jobId, repositories: Object.keys(delivery.transferBindings), exactGroups: delivery.native.result.groups, localTransactions: receipt.steps.length, tokenConservation: true });
  }
  assert.notEqual(joins[0].missionId, joins[1].missionId);
  assert.notEqual(journey.parent.binding.missionKind, journey.successor.binding.missionKind);
  assert.equal(String(evm.successorLifecycle.parentSeedId), String(evm.seedId));
  assert.equal(evm.sessionLifecycleTransactions, 32);
  assert.equal(evm.sessionLifecycleTransactions, transactionHashes.size);
  assert.equal(BigInt(evm.sessionLifecycleGasUsed), BigInt(evm.lifecycleGasUsed) + BigInt(evm.successorLifecycle.lifecycleGasUsed));
  assert.deepEqual(evm.localContractAddresses, evm.successorLifecycle.localContractAddresses);
  assert.deepEqual(evm.localCodeHashes, evm.successorLifecycle.localCodeHashes);
  assert.equal(journey.parent.native.projectId, journey.successor.native.projectId);
  assert.equal(journey.successor.native.ancestry.length, 2);
  assert(journey.successor.native.ancestry[1].parentCycleDigest);
  return { schema: 'tae.joined-acceptance.v1', accepted: true, checks: 'Exact mission, input, capability, artifact and proof bindings across all four source APIs and the local EVM; exact outputs, lineage reset and token conservation', joins, scope: 'Separate same-controller implementations; local source composition and disposable EVM. Computation precedes on-chain award; not a live job dispatcher. No production permission, real token movement, customer demand or commercial value established.' };
}

export function compactEvm(evm) {
  return {
    mode: 'Actual disposable local EVM; mock tokens and ENS', chainId: evm.chainId,
    setupTransactions: evm.fixtureSetup.transactions.length, lifecycleTransactions: evm.sessionLifecycleTransactions,
    setupGasUsed: evm.fixtureSetup.gasUsed, lifecycleGasUsed: evm.sessionLifecycleGasUsed,
    missions: [evm, evm.successorLifecycle].map(receipt => ({ missionId: receipt.missionId, seedId: receipt.seedId, parentSeedId: receipt.parentSeedId, jobId: receipt.jobId, artifactSha256: receipt.artifactSha256, proofSha256: receipt.proofSha256, capabilityHash: receipt.capabilityHash, resultHash: receipt.resultHash, planRoot: receipt.plan.planRoot, lineageBeforeReview: receipt.lineageBeforeReview, localContractAddresses: receipt.localContractAddresses, accounting: receipt.accounting, steps: receipt.steps.map(step => ({ stage: step.stage, transactionHash: step.transactionHash, block: step.block, status: step.status, gasUsed: step.gasUsed })) })),
    limitations: evm.limitations
  };
}

export function tokenFlow(evm) {
  const format = value => { const n = BigInt(value), whole = n / 10n ** 18n, decimal = String(n % 10n ** 18n).padStart(18, '0').replace(/0+$/, ''); return String(whole) + (decimal ? '.' + decimal : ''); };
  const a = evm.accounting;
  return { scope: 'Per mission; mock AGIALPHA only', funded: format(a.funded), worker: format(a.workerNet), validators: format(a.validatorsNet), burn: format(a.burned), returned: format(a.refunded) };
}
