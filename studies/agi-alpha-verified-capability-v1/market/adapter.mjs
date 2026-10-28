// SPDX-License-Identifier: Apache-2.0
import { createHash } from 'node:crypto';
import { readFileSync, realpathSync } from 'node:fs';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { COST_CATEGORIES, SCHEMA, validateProfile } from './inherited/continuation.mjs';
import { validateConfig } from './inherited/upstream/src/market.mjs';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export const canonical = value => JSON.stringify(value, (_k, x) => x && typeof x === 'object' && !Array.isArray(x)
  ? Object.fromEntries(Object.keys(x).sort().map(k => [k, x[k]])) : x);
const assert = (ok, why) => { if (!ok) throw Error(why); };
const sum = values => values.reduce((a, b) => a + b, 0);
const HASH = /^[a-f0-9]{64}$/;
const finite = (n, name) => assert(Number.isFinite(n) && n >= 0, `Invalid nonnegative quantity: ${name}`);
const integer = (n, name) => assert(Number.isSafeInteger(n) && n >= 0, `Invalid nonnegative integer: ${name}`);
export function fileAt(root, path) {
  assert(typeof path === 'string' && path.length && !isAbsolute(path), 'Study-relative path required');
  const full = resolve(root, path), rel = relative(root, full);
  assert(rel !== '..' && !rel.startsWith('../') && rel !== '', 'Path escapes study');
  return full;
}
export function readBound(root, row) {
  assert(HASH.test(row.sha256), 'Exact SHA-256 required');
  const file = fileAt(root, row.path), actual = realpathSync(file), rel = relative(realpathSync(root), actual);
  assert(rel !== '..' && !rel.startsWith('../'), 'Symlink escapes study');
  const bytes = readFileSync(file);
  assert(sha256(bytes) === row.sha256, `Identity mismatch: ${row.path}`);
  if (Object.hasOwn(row, 'bytes')) assert(bytes.length === row.bytes, `Byte count mismatch: ${row.path}`);
  return bytes;
}
export const readJSON = (root, path) => JSON.parse(readFileSync(fileAt(root, path), 'utf8'));

export function verifyInherited(root = ROOT) {
  const provenance = readJSON(root, 'market/inherited/PROVENANCE.json');
  assert(provenance.commit === 'daac40ee9e02a1b1bb100d7b9fcfa5caab04c297' && provenance.unchanged === true,
    'Exact inherited source commit required');
  assert(Array.isArray(provenance.files) && provenance.files.length === 10, 'Complete inherited closure required');
  provenance.files.forEach(row => readBound(root, row));
  const pinned = {
    'market/inherited/continuation.mjs':'5248bd12b0130f2630d449aeda0d76c6ad78980a8cad45fb5c5907661aa29c26',
    'market/inherited/continuation-core.mjs':'5f675c6b979ee8d73f67953a9101abfa776516c4260cf4695cc73407d00a70f4',
    'market/inherited/upstream/src/market.mjs':'52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27',
    'market/inherited/upstream/canonical/shadow-ledger.mjs':'cdc7c5a73593050a9af79b54589462e27f61b868e88ca6985d5cb639f3066d21',
    'market/inherited/upstream/canonical/automated-costs.mjs':'0dfca3ae4e7ef1d17bc78521f91917ef068280cf832d3565c354de2085c52506'
  };
  for (const [path, hash] of Object.entries(pinned)) assert(provenance.files.find(x => x.path === path)?.sha256 === hash,
    `Original market/canonical source identity changed: ${path}`);
  return provenance;
}

export function validateDesign(d) {
  assert(d.schema === 'agi-alpha-verified-capability-market-design/v1', 'Unknown market design');
  assert(['DRAFT_AWAITING_ROOT_FREEZE', 'FROZEN_BEFORE_MARKET_OUTCOMES'].includes(d.status), 'Unknown freeze state');
  assert(d.baseConfig.weeks === 52 && d.baseConfig.initialCashCents === 100000 && d.baseConfig.reserveCents === 20000,
    'Original52week/1000USD/200USD resource limits required');
  assert(d.baseConfig.investmentCostBasis === 'full-history' && d.baseConfig.historicalCostTiming === 'opening',
    'Historical cost timing cannot change');
  validateConfig(d.baseConfig);
  assert(d.productionMissionCount === 18, 'Frozen18fresh mission design required');
  assert(d.primaryMissionCount === 15 && d.stressMissionCount === 3, 'Primary/stress cohort separation required');
  assert(d.seeds.length === 24 && d.seeds.every((s, i) => s === 9101 + i), 'Fresh registered seeds9101-9124 required');
  assert(d.conditions.length === 6 && new Set(d.conditions.map(x => x.id)).size === 6, 'Six distinct market conditions required');
  assert(d.conditions.some(x => x.marketOverrides.arrivalProbability === 0) &&
    d.conditions.some(x => x.marketOverrides.integrationCents > 0) &&
    d.conditions.some(x => x.profileOverrides.weeklyMaintenanceFloorCents > 0) &&
    d.conditions.some(x => x.marketOverrides.aiQuality > 0.9), 'Required negative-demand/integration/upkeep/competition stresses absent');
  assert(d.policies.length === 2 && d.policies[0].policy === 'adaptive' && d.policies[1].policy === 'completed-research-replay',
    'Both inherited financing policies required');
  assert(canonical(d.costProfileIds) === canonical(['low', 'reference', 'high', 'actual-unknown']), 'All cost profiles required');
  assert(d.calibration.humanProviderMinutesSaved === 0 && d.calibration.customerReviewMinutesSaved === 0 &&
    d.calibration.proofPremiumCents === 0 && d.calibration.trustUplift === 0 && d.calibration.qualityUplift === 0 &&
    d.calibration.priceUplift === 0, 'Unmeasured proof, trust, quality, price or human benefit');
  assert(d.calibration.cpuTariffUSDPerCoreHour === 1 && canonical(d.calibration.cpuTariffSensitivity) === canonical([0.1, 1, 10]),
    'Preregistered assumed CPU tariffs required');
  assert(d.limits.maxWallSeconds === 180 && d.limits.maxCpuSeconds === 180, 'Fixed finite campaign budget required');
  assert(d.expected.cells === 48 && d.expected.pairedWorlds === 1152 && d.expected.enterpriseHistories === 3456,
    'Unexpected campaign size');
  assert(d.actualCustomerCollectionsCents === 0 && d.actualTransactions === 0 && d.newFinancialAuthority === false &&
    d.liveIdentityEnforcement === 'NOT RUN', 'Research must not claim live authority or receipts');
  return d;
}

export function validateProduction(summary, missionCount = 18) {
  assert(summary && summary.arms, 'Measured production summary required');
  assert(summary.execution_costs_known !== false,
    'Incomplete execution CPU: measured lower bounds cannot calibrate economic effects');
  const expectedIds = summary.arms.A?.per_mission?.map(x => x.id).sort();
  assert(Array.isArray(expectedIds) && new Set(expectedIds).size === missionCount, 'Distinct fresh mission identities required');
  for (const arm of ['A', 'B', 'C', 'D']) {
    const s = summary.arms[arm];
    assert(s && s.mission_count === missionCount && s.per_mission.length === missionCount, `Wrong mission denominator: ${arm}`);
    assert(s.primary_count === 15 && s.stress_count === 3, 'Explicit primary/stress counts required');
    assert(s.per_mission.filter(x => x.cohort === 'primary').length === 15 &&
      s.per_mission.filter(x => x.cohort === 'stress').length === 3, 'Mislabeled primary/stress observations');
    integer(s.accepted_count, 'accepted count'); integer(s.tools_total, 'tool count'); integer(s.cache_confirmations, 'cache confirmations');
    finite(s.cpu_seconds_total, 'inclusive CPU'); finite(s.elapsed_seconds_total, 'inclusive elapsed');
    assert(canonical(s.per_mission.map(x => x.id).sort()) === canonical(expectedIds), `Unmatched fresh missions: ${arm}`);
    for (const row of s.per_mission) {
      assert(typeof row.accepted === 'boolean' && typeof row.id === 'string', `Acceptance record required: ${arm}`);
      assert(row.child_cpu_known !== false && row.production?.descendant_cpu_complete !== false &&
        row.unmeasured_child_cost !== 'UNKNOWN_NOT_ZERO',
        `Incomplete child CPU for ${arm}/${row.id}: measured lower bounds cannot calibrate economic effects`);
      finite(row.cpu_seconds, 'mission CPU'); finite(row.elapsed_seconds, 'mission elapsed');
      assert(typeof row.decision === 'string' && row.decision.length > 0, 'Actual decision identity required');
      assert(row.cohort === summary.arms.A.per_mission.find(x => x.id === row.id).cohort,
        `Primary/stress cohort mismatch for matched mission: ${row.id}`);
    }
    assert(s.accepted_count === s.per_mission.filter(x => x.accepted).length, `Acceptance count mismatch: ${arm}`);
    assert(s.cpu_seconds_total + 1e-6 >= sum(s.per_mission.map(x => x.cpu_seconds)), 'CPU total omits measured mission cost');
    assert(s.elapsed_seconds_total + 1e-6 >= sum(s.per_mission.map(x => x.elapsed_seconds)), 'Elapsed total omits measured mission cost');
  }
  return summary;
}

const allocatedPrimaryMean = (summary, arm, field, totalField) => {
  const s = summary.arms[arm], primary = s.per_mission.filter(x => x.cohort === 'primary');
  const shared = Math.max(0, s[totalField] - sum(s.per_mission.map(x => x[field])));
  return sum(primary.map(x => x[field])) / primary.length + shared / s.mission_count;
};

export function sourceManifestHash(files) {
  return sha256(canonical(files.map(({ path, sha256: hash }) => ({ path, sha256: hash })).sort((a, b) => a.path.localeCompare(b.path))));
}

export function verifyAssetBindings(bindings, summary, root = ROOT) {
  assert(bindings.schema === 'agi-alpha-verified-capability-asset-bindings/v1', 'Explicit actual asset bindings required');
  const checked = {};
  for (const arm of ['B', 'C']) {
    const a = bindings.assets?.[arm];
    assert(a && typeof a.id === 'string' && a.id.length && Array.isArray(a.files) && a.files.length > 0, `Actual asset source closure required: ${arm}`);
    assert(new Set(a.files.map(x => x.path)).size === a.files.length, 'Duplicate asset source');
    a.files.forEach(row => readBound(root, row));
    const manifestHash = sourceManifestHash(a.files);
    const evidence = readBound(root, { path: a.admission_evidence_path, sha256: a.admission_evidence_sha256 });
    const record = JSON.parse(evidence);
    const admitted = Array.isArray(record.admissions) && record.admissions.some(r => r.asset_id === a.id &&
      r.decision === 'ADMIT' && r.mode === 'FIXTURE_ONLY' && r.source_manifest_sha256 === manifestHash);
    const rows = summary.arms[arm].per_mission;
    const used = rows.filter(r => r.accepted).length > 0 && rows.filter(r => r.accepted).every(r => r.asset_id === a.id);
    checked[arm] = { id: a.id, assetSHA256: manifestHash, acceptanceEvidenceSHA256: a.admission_evidence_sha256,
      sourceFiles: a.files, admitted, usedOnAcceptedFreshMissions: used,
      tested: admitted && used && summary.arms[arm].accepted_count === summary.arms[arm].mission_count,
      identityMode: 'FIXTURE_ONLY', liveIdentityEnforcement: 'NOT RUN' };
  }
  return checked;
}

export function deriveMeasuredEffects(summary, assets, tariff = 1) {
  validateProduction(summary);
  assert(Number.isFinite(tariff) && tariff > 0, 'Explicit positive assumed compute tariff required');
  const primaryMean = arm => allocatedPrimaryMean(summary, arm, 'cpu_seconds', 'cpu_seconds_total');
  const baseline = primaryMean('A');
  return Object.fromEntries(['B', 'C'].map(arm => {
    const s = summary.arms[arm], a = assets[arm];
    const equivalent = s.per_mission.every(row => {
      const ref = summary.arms.A.per_mission.find(x => x.id === row.id);
      return row.accepted && ref.accepted && row.decision === ref.decision;
    });
    const tested = a.tested && equivalent;
    const cpuSaving = baseline - primaryMean(arm);
    const rawMicros = cpuSaving * tariff / 3600 * 100_000_000;
    const microcents = tested ? Math.round(rawMicros) : 0;
    const cents = Math.trunc(microcents / 1_000_000) || 0;
    return [arm, { id: a.id, assetSHA256: a.assetSHA256, acceptanceEvidenceSHA256: a.acceptanceEvidenceSHA256,
      tested, researchPrototypeConstructed: true,
      effects: { providerMinutesSaved: 0, computeAndToolCentsSaved: cents, customerReviewMinutesSaved: 0 },
      effectEvidence: {
        providerMinutesSaved: 'Human effort unmeasured; zero incremental economic credit, not evidence of zero human work.',
        computeAndToolCentsSaved: `Inclusive measured A-minus-${arm} CPU ${cpuSaving} seconds per fresh mission, priced only at assumed USD${tariff}/core-hour. Signed subcent residual retained. Failed/non-equivalent output receives no saving credit.`,
        customerReviewMinutesSaved: 'Customer effort, trust, willingness to pay and price premium unmeasured; no incremental credit.'
      },
      unroundedComputeSavingsMicrocentsPerJob: microcents,
      measuredCpuSecondsSavedPerMission: cpuSaving,
      primaryObservations: 15, designedStressObservationsNotUsedForCalibration: 3,
      sharedCPUAllocation: 'Inclusive total CPU beyond individual rows is charged uniformly across18fresh outcomes; no shared overhead is omitted.',
      exactConditionalComputeCentsSavedPerMission: tested ? rawMicros / 1_000_000 : 0,
      equivalentAcceptedOutcomes: equivalent, actualAssetAdmission: a.admitted,
      actualAssetUsedOnFreshWork: a.usedOnAcceptedFreshMissions,
      actualCompleteMonetaryCost: null, liveIdentityEnforcement: 'NOT RUN' }];
  }));
}

export function directAlternativeComparison(summary, tariffs = [0.1, 1, 10]) {
  validateProduction(summary);
  const rows = Object.fromEntries(['A', 'B', 'C', 'D'].map(arm => [arm, summary.arms[arm].per_mission.filter(x => x.cohort === 'primary')]));
  const mean = (arm, key) => allocatedPrimaryMean(summary, arm, key, key === 'cpu_seconds' ? 'cpu_seconds_total' : 'elapsed_seconds_total');
  const equivalent = arm => rows[arm].every(x => {
    const d = rows.D.find(y => y.id === x.id);
    return x.accepted && d.accepted && x.decision === d.decision;
  });
  return {
    schema: 'agi-alpha-verified-capability-direct-alternative/v1', primaryCount: 15,
    arms: Object.fromEntries(['A', 'B', 'C', 'D'].map(arm => [arm, {meanCPUSeconds:mean(arm, 'cpu_seconds'), meanElapsedSeconds:mean(arm, 'elapsed_seconds')}])),
    comparisons: Object.fromEntries(['A', 'B', 'C'].map(arm => [arm, {
      equivalentAcceptedOutputs: equivalent(arm),
      CPUSecondsSavedVersusD: mean('D', 'cpu_seconds') - mean(arm, 'cpu_seconds'),
      elapsedSecondsSavedVersusD: mean('D', 'elapsed_seconds') - mean(arm, 'elapsed_seconds'),
      DUsesLessMeasuredCPU: equivalent(arm) && mean('D', 'cpu_seconds') < mean(arm, 'cpu_seconds'),
      assumedTariffUSDSavedPerUse: tariffs.map(t => ({USDPerCoreHour:t, deltaUSD:(mean('D', 'cpu_seconds') - mean(arm, 'cpu_seconds')) * t / 3600}))
    }])),
    completeDAdoptionCost: null, globalEconomicAdmission: null,
    scope: 'Direct D is a real measured alternative. The native-history A/B/C market comparison does not establish superiority or global adoption over D. Complete integration, attention and historical costs remain unknown.'
  };
}

export function bindCosts(spec, profileId, arm, maintenanceFloor = 0) {
  assert(spec.schema === 'agi-alpha-verified-capability-costs/v1' && ['B', 'C'].includes(arm), 'Cost schema/arm mismatch');
  assert(Object.hasOwn(spec.profiles, profileId), 'Unknown cost profile');
  const multiplier = spec.profiles[profileId].multiplier;
  const seen = new Set(), assigned = Object.fromEntries(COST_CATEGORIES.map(k => [k, []]));
  for (const row of spec.rows) {
    assert(!seen.has(row.id) && Object.hasOwn(assigned, row.canonicalCategory), 'Duplicate or unrecognized cost allocation');
    seen.add(row.id); integer(row.referenceCents[arm], row.id);
    assigned[row.canonicalCategory].push({ ...row, amountCents: multiplier === null ? null : Math.round(row.referenceCents[arm] * multiplier) });
  }
  const costs = Object.fromEntries(COST_CATEGORIES.map(k => {
    assert(assigned[k].length, `Missing complete category: ${k}`);
    return [k, { amountCents: multiplier === null ? null : sum(assigned[k].map(x => x.amountCents)),
      basis: multiplier === null ? 'unknown' : 'scenario',
      explanation: assigned[k].map(x => `${x.id}: ${x.explanation}`).join(' ') }];
  }));
  spec.weeklyRows.forEach(row => integer(row.referenceCents[arm], row.id));
  costs.weeklyMaintenance = {
    amountCents: multiplier === null ? null : Math.max(maintenanceFloor, sum(spec.weeklyRows.map(x => Math.round(x.referenceCents[arm] * multiplier)))),
    basis: multiplier === null ? 'unknown' : 'scenario',
    explanation: 'Explicit recurring maintenance, storage and revalidation allocation. Unknown actual all-in upkeep stays null; priced scenarios are neither invoices nor empirical bounds.'
  };
  return { costs, detailedRows: Object.values(assigned).flat(),
    totalOneoffCents: multiplier === null ? null : sum(COST_CATEGORIES.map(k => costs[k].amountCents)) };
}

export function hypotheticalHumanBreakEven({ completeOneoffCents, maintenanceCents, forgoneContributionCents,
  forecastUses, computeCentsSavedPerUse, hourlyProviderCents = 6538, passThrough = 0.25 }) {
  const required = [completeOneoffCents, maintenanceCents, forgoneContributionCents, forecastUses, computeCentsSavedPerUse];
  if (required.some(x => x === null || !Number.isFinite(x))) return { secondsPerUse: null, status: 'UNKNOWN_COMPLETE_COST_OR_WORKLOAD' };
  if (forecastUses <= 0) return { secondsPerUse: null, status: 'NO_FORECAST_WORKLOAD' };
  assert(hourlyProviderCents > 0 && passThrough >= 0 && passThrough < 1, 'Invalid hypothetical labor tariff');
  const requiredNet = completeOneoffCents + maintenanceCents + forgoneContributionCents -
    forecastUses * computeCentsSavedPerUse * (1 - passThrough);
  return { secondsPerUse: Math.max(0, requiredNet / (forecastUses * hourlyProviderCents / 3600 * (1 - passThrough))),
    status: 'HYPOTHETICAL_UNMEASURED_THRESHOLD',
    interpretation: 'Required additional provider attention saving per accepted use. This is not assigned to any treatment and does not alter the frozen financial decisions.' };
}

export function assembleInputs(root = ROOT, designPath = 'protocol/market-design.json') {
  const design = validateDesign(readJSON(root, designPath));
  const inherited = verifyInherited(root);
  const summaryRaw = readFileSync(fileAt(root, design.productionSummary));
  const production = validateProduction(JSON.parse(summaryRaw), design.productionMissionCount);
  const bindings = readJSON(root, design.assetBindings), costs = readJSON(root, design.costAssumptions);
  const assets = verifyAssetBindings(bindings, production, root);
  const effects = deriveMeasuredEffects(production, assets, design.calibration.cpuTariffUSDPerCoreHour);
  const cells = [];
  for (const condition of design.conditions) for (const policy of design.policies) for (const costProfileId of design.costProfileIds) {
    const id = `${condition.id}__${policy.id}__${costProfileId}`;
    const config = { ...design.baseConfig, ...condition.marketOverrides, id: `${design.id}/${id}` };
    assert(config.weeks === 52 && config.initialCashCents === 100000 && config.reserveCents === 20000, 'Condition changed finite resources');
    validateConfig(config);
    const profiles = Object.fromEntries(['B', 'C'].map(arm => {
      const e = effects[arm], cost = bindCosts(costs, costProfileId, arm, condition.profileOverrides.weeklyMaintenanceFloorCents ?? 0);
      const candidate = { schema: SCHEMA, id: e.id, assetSHA256: e.assetSHA256, acceptanceEvidenceSHA256: e.acceptanceEvidenceSHA256,
        tested: e.tested, ...design.candidateDefaults, policy: policy.policy, earliestWeek: policy.earliestWeek,
        lastDecisionWeek: policy.lastDecisionWeek, costs: cost.costs, effects: e.effects, effectEvidence: e.effectEvidence,
        unroundedComputeSavingsMicrocentsPerJob: e.unroundedComputeSavingsMicrocentsPerJob };
      return [arm, validateProfile(candidate)];
    }));
    cells.push({ id, condition: condition.id, policy: policy.id, costProfileId, config, profiles });
  }
  assert(cells.length === design.expected.cells, 'Cell inventory differs from frozen design');
  return { design, designPath, production, productionSHA256: sha256(summaryRaw), bindings, assets, costs, effects, cells, inherited };
}
