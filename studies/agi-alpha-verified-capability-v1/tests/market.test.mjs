// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ROOT, bindCosts, canonical, deriveMeasuredEffects, directAlternativeComparison, fileAt,
  hypotheticalHumanBreakEven, readBound, readJSON, sha256, sourceManifestHash, validateDesign,
  validateProduction, verifyAssetBindings, verifyInherited } from '../market/adapter.mjs';
import { distribution, verifyFreeze } from '../market/run-campaign.mjs';
import { calculateInvestment, planMission } from '../market/inherited/upstream/canonical/shadow-ledger.mjs';

function summary() {
  return {execution_costs_known:true, arms:Object.fromEntries(['A', 'B', 'C', 'D'].map((arm, i) => {
    const rows = Array.from({length:18}, (_, n) => ({id:`mission-${n}`, cohort:n < 15 ? 'primary' : 'stress',
      accepted:true, decision:'CONSISTENT', child_cpu_known:true,
      cpu_seconds:1 - i * 0.1, elapsed_seconds:2 - i * 0.1, asset_id:`asset-${arm}`}));
    return [arm, {mission_count:18, primary_count:15, stress_count:3, accepted_count:18, tools_total:36, cache_confirmations:1,
      cpu_seconds_total:rows.reduce((s, r) => s + r.cpu_seconds, 0), elapsed_seconds_total:rows.reduce((s, r) => s + r.elapsed_seconds, 0), per_mission:rows}];
  }))};
}
const assets = Object.fromEntries(['B', 'C'].map(a => [a, {id:`asset-${a}`, assetSHA256:'a'.repeat(64),
  acceptanceEvidenceSHA256:'b'.repeat(64), tested:true, admitted:true, usedOnAcceptedFreshMissions:true}]));

test('preserved inherited simulation and canonical monetary source closure matches ten exact identities', () => {
  assert.equal(verifyInherited().files.length, 10);
});
test('registered design has48cells and zero assumed human/proof premium without executing outcomes', () => {
  const d = validateDesign(readJSON(ROOT, 'protocol/market-design.json'));
  assert.equal(d.expected.pairedWorlds, 1152); assert.equal(d.calibration.customerReviewMinutesSaved, 0);
  assert.throws(() => validateDesign({...d, calibration:{...d.calibration, trustUplift:0.1}}), /Unmeasured/);
});
test('same skills, evidence and root proof costs are charged in both registry and graph', () => {
  const spec = readJSON(ROOT, 'market/cost-assumptions.json');
  const proof = spec.rows.find(x => x.id === 'proofGenerationAndChecking');
  assert.equal(proof.referenceCents.B, proof.referenceCents.C);
  assert.equal(bindCosts(spec, 'reference', 'B').totalOneoffCents, 8850);
  assert.equal(bindCosts(spec, 'reference', 'C').totalOneoffCents, 9050);
});
test('unknown costs never become zero or known under upkeep stress', () => {
  const s = readJSON(ROOT, 'market/cost-assumptions.json');
  const c = bindCosts(s, 'actual-unknown', 'C', 200);
  assert.equal(c.totalOneoffCents, null); assert.equal(c.costs.weeklyMaintenance.amountCents, null);
  assert.ok(Object.values(c.costs).every(x => x.basis === 'unknown'));
});
test('duplicate cost rows cannot double-count shared construction', () => {
  const s = readJSON(ROOT, 'market/cost-assumptions.json'); s.rows.push(s.rows[0]);
  assert.throws(() => bindCosts(s, 'reference', 'C'), /Duplicate/);
});
test('accepted outcome count and inclusive costs are validated against raw mission records', () => {
  const s = summary(); assert.equal(validateProduction(s), s);
  s.arms.C.cpu_seconds_total = 0;
  assert.throws(() => validateProduction(s), /omits measured/);
});
test('incomplete descendant CPU cannot turn a finite lower bound into an economic estimate', () => {
  const global = summary(); global.execution_costs_known = false;
  assert.throws(() => deriveMeasuredEffects(global, assets), /Incomplete execution CPU/);
  for (const field of ['child_cpu_known', 'production', 'unmeasured_child_cost']) {
    const s = summary(), row = s.arms.C.per_mission[0];
    row[field] = field === 'child_cpu_known' ? false : field === 'production'
      ? {descendant_cpu_complete:false} : 'UNKNOWN_NOT_ZERO';
    assert.throws(() => deriveMeasuredEffects(s, assets), /Incomplete child CPU/);
    assert.throws(() => directAlternativeComparison(s), /Incomplete child CPU/);
  }
});
test('unchanged request confirmations are separate from18mission denominator', () => {
  const s = summary(); s.arms.C.cache_confirmations = 100;
  assert.equal(validateProduction(s).arms.C.mission_count, 18);
  s.arms.C.mission_count = 118;
  assert.throws(() => validateProduction(s), /denominator/);
});
test('CPU economics uses15primary observations and excludes designed stress observations', () => {
  const s = summary(), before = deriveMeasuredEffects(s, assets);
  for (const row of s.arms.C.per_mission.filter(x => x.cohort === 'stress')) row.cpu_seconds = 100;
  s.arms.C.cpu_seconds_total = s.arms.C.per_mission.reduce((t, x) => t + x.cpu_seconds, 0);
  assert.equal(deriveMeasuredEffects(s, assets).C.measuredCpuSecondsSavedPerMission, before.C.measuredCpuSecondsSavedPerMission);
});
test('cohort labels must match and shared recurring overhead cannot vanish from calibration', () => {
  const s = summary(), before = deriveMeasuredEffects(s, assets).C.measuredCpuSecondsSavedPerMission;
  s.arms.C.cpu_seconds_total += 18;
  assert.ok(Math.abs(deriveMeasuredEffects(s, assets).C.measuredCpuSecondsSavedPerMission - (before - 1)) < 1e-9);
  s.arms.C.per_mission[0].cohort = 'stress'; s.arms.C.per_mission[17].cohort = 'primary';
  assert.throws(() => validateProduction(s), /cohort mismatch/);
});
test('signed subcent cost is retained while cent ledger and human effects remain zero', () => {
  const s = summary();
  for (const row of s.arms.C.per_mission) row.cpu_seconds = 1.2;
  s.arms.C.cpu_seconds_total = 21.6;
  const e = deriveMeasuredEffects(s, assets).C;
  assert.equal(e.effects.computeAndToolCentsSaved, 0); assert.ok(e.unroundedComputeSavingsMicrocentsPerJob < 0);
  assert.equal(e.effects.providerMinutesSaved, 0); assert.equal(e.effects.customerReviewMinutesSaved, 0);
});
test('faster rejected or non-equivalent outcomes receive no economic saving credit', () => {
  const s = summary(); s.arms.C.per_mission[0].accepted = false; s.arms.C.accepted_count = 17;
  const e = deriveMeasuredEffects(s, assets).C;
  assert.equal(e.tested, false); assert.equal(e.unroundedComputeSavingsMicrocentsPerJob, 0);
});
test('faster direct conventional alternative remains visible and global adoption unknown', () => {
  const x = directAlternativeComparison(summary());
  assert.equal(x.comparisons.C.DUsesLessMeasuredCPU, true); assert.equal(x.globalEconomicAdmission, null);
  assert.ok(x.comparisons.C.assumedTariffUSDSavedPerUse.every(r => r.deltaUSD < 0));
});
test('exact asset source and actual mission usage are required, not a production-used flag', () => {
  const root = mkdtempSync(join(tmpdir(), 'verified-capability-market-assets-'));
  try {
    writeFileSync(join(root, 'asset.txt'), 'executable source');
    const files = [{path:'asset.txt', sha256:sha256('executable source')}], h = sourceManifestHash(files);
    const ev = JSON.stringify({admissions:['B', 'C'].map(a => ({asset_id:`asset-${a}`, decision:'ADMIT', mode:'FIXTURE_ONLY', source_manifest_sha256:h}))});
    writeFileSync(join(root, 'admission.json'), ev);
    const bindings = {schema:'agi-alpha-verified-capability-asset-bindings/v1', assets:Object.fromEntries(['B', 'C'].map(a => [a,
      {id:`asset-${a}`, files, admission_evidence_path:'admission.json', admission_evidence_sha256:sha256(ev), production_used:true}]))};
    const s = summary(); assert.equal(verifyAssetBindings(bindings, s, root).C.tested, true);
    s.arms.C.per_mission[0].asset_id = 'different-asset';
    assert.equal(verifyAssetBindings(bindings, s, root).C.tested, false);
    writeFileSync(join(root, 'asset.txt'), 'changed source');
    assert.throws(() => verifyAssetBindings(bindings, s, root), /Identity mismatch/);
  } finally {rmSync(root, {recursive:true, force:true});}
});
test('source-manifest hash is order stable and refuses path escape', () => {
  const a = [{path:'z', sha256:'a'.repeat(64)}, {path:'a', sha256:'b'.repeat(64)}];
  assert.equal(sourceManifestHash(a), sourceManifestHash([...a].reverse()));
  assert.throws(() => fileAt(ROOT, '../outside'), /escapes/);
});
test('hypothetical attention threshold never becomes an assigned saving or free missing workload', () => {
  const x = hypotheticalHumanBreakEven({completeOneoffCents:10000, maintenanceCents:0, forgoneContributionCents:0,
    forecastUses:100, computeCentsSavedPerUse:0, hourlyProviderCents:6000, passThrough:0});
  assert.equal(x.secondsPerUse, 60); assert.equal(x.status, 'HYPOTHETICAL_UNMEASURED_THRESHOLD');
  assert.equal(hypotheticalHumanBreakEven({completeOneoffCents:null, maintenanceCents:0, forgoneContributionCents:0,
    forecastUses:100, computeCentsSavedPerUse:0}).secondsPerUse, null);
});
test('canonical full investment includes unsuccessful construction and upkeep exactly once', () => {
  const x = calculateInvestment({constructionCostMinor:10000, failedConstructionCostMinor:2000,
    maintenancePerReuseMinor:100, expectedSavingPerReuseMinor:300, remainingReuses:100});
  assert.equal(x.lifetimeCost, 22000); assert.equal(x.grossSaving, 30000); assert.equal(x.netBenefit, 8000);
});
test('canonical actual receipt zero does not resolve unknown complete costs', () => {
  const x = planMission({missionId:'fixture', reference:'Synthetic accounting control', acceptance:'accepted',
    totalCollectedCents:0, priceAssumptionCents:2000, totalOperatingCostCents:null, operatingCostsComplete:false,
    capabilityCostCents:null, reserveCents:20000, obligationCents:0});
  assert.equal(x.summary.observed.revenue, 0); assert.equal(x.summary.observed.fullCost, null);
  assert.equal(x.summary.scenario.eligibleInvestment, null);
});
test('distribution preserves missing and losing paths instead of averaging unknown as zero', () => {
  const x = distribution([null, -300, -100, 200]);
  assert.equal(x.missing, 1); assert.equal(x.negative, 2); assert.equal(x.mean, -200 / 3);
});
test('market execution cannot proceed without root preregistration', () => {
  assert.throws(() => verifyFreeze({design:{status:'DRAFT_AWAITING_ROOT_FREEZE'}}, 'absent.json'), /must freeze/);
});
