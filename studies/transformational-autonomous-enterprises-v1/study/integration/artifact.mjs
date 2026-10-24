// SPDX-License-Identifier: Apache-2.0
// Trusted integration wrapper; only the external evaluator issues proof receipts.
import { canonicalBytes, proofHash, prepareDelivery } from './mission-delivery.mjs';

export function artifactFor(mission, result) {
  const prepared = prepareDelivery(mission, result);
  return {
    schema: 'tae.artifact.v1', missionId: mission.missionId,
    capabilityHash: prepared.binding.capabilityId, inputHash: proofHash(mission),
    output: { groups: prepared.rows.map(row => ({ group: row.group, total: Number(row.amount) })), total: Number(prepared.total) },
    currentProof: null, authority: []
  };
}
export function externalAdmission(checkArtifact, criteriaBytes) {
  return async (mission, result) => {
    const artifact = artifactFor(mission, result);
    const proof = await checkArtifact(canonicalBytes(artifact), canonicalBytes(mission), criteriaBytes);
    return { accepted: proof.accepted === true, artifact, proof };
  };
}
