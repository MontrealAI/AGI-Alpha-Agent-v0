// SPDX-License-Identifier: Apache-2.0
// Public development inputs, never the independent frozen holdout population.
export const diamondBOM = {
  schema: 'tae/mission-v1', missionId: 'public-development-bom', kind: 'bom-demand',
  graph: { nodes: ['assembly', 'branch-left', 'branch-right', 'shared-part'], edges: [
    { from: 'assembly', to: 'branch-left', weight: 2 }, { from: 'assembly', to: 'branch-right', weight: 3 },
    { from: 'branch-left', to: 'shared-part', weight: 5 }, { from: 'branch-right', to: 'shared-part', weight: 7 }
  ] }, seeds: [{ node: 'assembly', amount: 2 }], targets: ['assembly', 'branch-left', 'branch-right', 'shared-part']
};
export const diamondImpact = {
  schema: 'tae/mission-v1', missionId: 'public-development-remediation', kind: 'remediation-impact',
  graph: { nodes: ['library', 'gateway', 'worker', 'customer-service', 'isolated-service'], edges: [
    { from: 'library', to: 'gateway', weight: 1 }, { from: 'library', to: 'worker', weight: 1 },
    { from: 'gateway', to: 'customer-service', weight: 1 }, { from: 'worker', to: 'customer-service', weight: 1 }
  ] }, seeds: [{ node: 'library', amount: 1 }], targets: ['library', 'gateway', 'worker', 'customer-service', 'isolated-service']
};
export const flatControl = { schema: 'tae/mission-v1', missionId: 'public-development-flat', kind: 'flat-reduction', rows: [{ group: 'part', amount: 2 }, { group: 'part', amount: -1 }, { group: 'other', amount: 3 }] };
