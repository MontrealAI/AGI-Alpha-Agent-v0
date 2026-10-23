// SPDX-License-Identifier: Apache-2.0
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { checkArtifact } from '../evaluation/checker.mjs';
import { createMissionDelivery, proofHash } from './mission-delivery.mjs';
import { externalAdmission } from './artifact.mjs';

const examplesPath = path.resolve(process.argv[2] ?? 'study/results/journey-inputs/examples.json');
const repositoriesRoot = path.resolve(process.argv[3] ?? 'repos');
const outputPath = path.resolve(process.argv[4] ?? 'study/results/journey.json');
const examples = JSON.parse(readFileSync(examplesPath, 'utf8'));
const criteriaBytes = readFileSync(new URL('../evaluation/criteria.json', import.meta.url), 'utf8');
const check = externalAdmission(checkArtifact, criteriaBytes);
const delivery = createMissionDelivery({ repositories: Object.fromEntries(['alpha', 'manager', 'jobs', 'fleet'].map(name => [name, path.join(repositoriesRoot, name)])), check, concurrency: 2 });
const started = performance.now();
const parent = await delivery.deliver(examples.parent.mission, examples.parent.result, { projectId: 'writer4-graph-enterprise' });
const successor = await delivery.deliver(examples.successor.mission, examples.successor.result, { projectId: 'writer4-graph-enterprise', parentProject: parent.native.artifacts.alpha });
for (const [name, result] of Object.entries({ parent, successor })) {
  if (examples[name].artifact && proofHash(examples[name].artifact) !== result.admission.proof.artifactSha256) throw Error(`Stored ${name} canonical artifact differs from the recomputed proof binding.`);
}
const result = {
  schema: 'tae/two-mission-four-repository-journey-v1', createdAt: new Date().toISOString(),
  examplesPath: path.relative(process.cwd(), examplesPath), elapsedMs: performance.now() - started,
  scope: { mode: 'local-source-composition', scientificCheck: 'separate implementation; same controller', nativeHostAdmission: 'NOT_RUN', processIsolation: 'NOT_TESTED', settlement: 'not-connected', financialTransfers: 'none', learnedProviderSwap: 'unverified', independentCustomerDemand: 'unverified' },
  parent, successor, statistics: delivery.statistics()
};
writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({ outputPath, parent: { missionId: parent.missionId, total: parent.native.result.total, groups: parent.native.result.groups, scientificAccepted: parent.admission.accepted, nativeReviewPassed: parent.native.artifacts.review.checker.passed }, successor: { missionId: successor.missionId, total: successor.native.result.total, groups: successor.native.result.groups, scientificAccepted: successor.admission.accepted, nativeReviewPassed: successor.native.artifacts.review.checker.passed, ancestry: successor.native.ancestry }, elapsedMs: result.elapsedMs, scope: result.scope }, null, 2));
