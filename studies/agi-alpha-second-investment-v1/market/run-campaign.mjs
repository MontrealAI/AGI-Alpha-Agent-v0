// SPDX-License-Identifier: Apache-2.0
import { createReadStream, createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createGzip } from 'node:zlib';
import { once } from 'node:events';
import { pipeline } from 'node:stream/promises';
import { pairedContinuation, validateProfile, COST_CATEGORIES, SCHEMA } from './continuation.mjs';
import { validateConfig } from './upstream/src/market.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const assert = (condition, message) => { if (!condition) throw Error(message); };
const clone = value => JSON.parse(JSON.stringify(value));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const sum = values => values.reduce((a, b) => a + b, 0);
const HASH = /^[a-f0-9]{64}$/;
const integer = (n, name, minimum = 0) => assert(Number.isSafeInteger(n) && n >= minimum, `Invalid ${name}`);
const localPath = path => {
  assert(typeof path === 'string' && path.length > 0 && !isAbsolute(path), 'A market-relative path is required');
  const p = resolve(ROOT, path);
  assert(relative(ROOT, p) !== '..' && !relative(ROOT, p).startsWith('../'), 'Path escapes the registered market directory');
  return p;
};
const json = path => JSON.parse(readFileSync(localPath(path), 'utf8'));

function parseArgs(argv) {
  const result = { protocol: 'campaign-protocol.json', freeze: null, output: null, validateOnly: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--validate-only') result.validateOnly = true;
    else if (['--protocol', '--freeze', '--output'].includes(argv[i])) {
      const key = argv[i].slice(2);
      assert(argv[i + 1] && !argv[i + 1].startsWith('--'), `Missing ${argv[i]} value`);
      result[key] = argv[++i];
    } else throw Error(`Unknown argument: ${argv[i]}`);
  }
  return result;
}

export function readInputs(protocolPath) {
  const protocol = json(protocolPath);
  assert(protocol.schema === 'agi-alpha-second-investment-campaign/v1', 'Unknown campaign protocol');
  assert(['DRAFT_AWAITING_PUBLIC_REGISTRATION', 'FROZEN_BEFORE_MARKET_OUTCOMES'].includes(protocol.status), 'Unknown protocol status');
  assert(protocol.baseConfig.weeks === 52, 'The original 52-week service horizon must be retained');
  assert(protocol.baseConfig.initialCashCents === 100000 && protocol.baseConfig.reserveCents === 20000,
    'Original finite USD1000 capital and USD200 reserve must be retained');
  assert(protocol.baseConfig.investmentCostBasis === 'full-history' && protocol.baseConfig.historicalCostTiming === 'opening',
    'Opening historical cost accounting must be retained');
  assert(protocol.baseConfig.investmentFunding === 'seed-funded' && protocol.baseConfig.pricingPolicy === 'fixed',
    'First adoption keeps its disclosed seed funding and fixed posted-price policy');
  assert(protocol.actualCustomerCollectionsCents === 0 && protocol.actualTransactions === 0 && protocol.newFinancialAuthority === false,
    'Simulation cannot create observed receipts or financial authority');
  validateConfig(protocol.baseConfig);
  assert(Array.isArray(protocol.seeds) && protocol.seeds.length === 24 && new Set(protocol.seeds).size === 24, 'Exactly24distinct frozen seeds required');
  protocol.seeds.forEach(n => { integer(n, 'seed', 1); assert(n <= 0xffffffff, 'Seed exceeds32bit range'); });
  assert(protocol.seeds.every((n, i) => n === 8001 + i), 'This campaign uses only preregistered seeds8001-8024');
  assert(protocol.limits.maxWallSeconds === 180 && protocol.limits.maxCpuSeconds === 180, 'The180second campaign budgets cannot be extended');
  const costs = json(protocol.costProfilesFile);
  const effects = json(protocol.effectProfileFile);
  assert(costs.schema === 'agi-alpha-second-investment-cost-profiles/v1' && costs.sameProfileForBAndC === true,
    'Comparable B/C scenario cost profiles required');
  assert(effects.schema === 'agi-alpha-second-investment-effect-profile/v1' && effects.arms?.B && effects.arms?.C,
    'Frozen actual B/C effect identities required');
  for (const arm of ['B', 'C']) {
    const effect = effects.arms[arm];
    assert(effect.effects.providerMinutesSaved === 0 && effect.effects.customerReviewMinutesSaved === 0,
      'No human or customer savings were measured in this campaign');
    assert(effect.effects.computeAndToolCentsSaved === 0,
      'Measured CPU differences in this campaign are below cent-ledger precision');
    assert(HASH.test(effect.assetSHA256) && HASH.test(effect.acceptanceEvidenceSHA256), 'Exact actual asset/acceptance identities required');
  }
  assert(Array.isArray(protocol.conditions) && protocol.conditions.length === 13, 'Exactly13frozen conditions required');
  assert(new Set(protocol.conditions.map(c => c.id)).size === 13, 'Condition IDs must be unique');
  assert(protocol.conditions.some(c => c.marketOverrides?.arrivalProbability === 0), 'Zero-demand condition must be retained');
  assert(Array.isArray(protocol.policies) && protocol.policies.length === 2, 'Both predeclared policies required');
  assert(new Set(protocol.policies.map(p => p.id)).size === 2, 'Policy IDs must be unique');
  assert(JSON.stringify(protocol.costProfileIds) === JSON.stringify(['low', 'reference', 'high']), 'All three declared cost profiles required');
  assert(protocol.unknownProfileId === 'actual-unknown', 'Actual unidentified-cost boundary must be retained');
  for (const name of [...protocol.costProfileIds, protocol.unknownProfileId]) {
    const row = costs.profiles[name];
    assert(row && row.costs, `Missing cost profile: ${name}`);
    const allKnown = COST_CATEGORIES.every(k => row.costs[k]?.amountCents !== null);
    assert(row.totalOneoffCents === (allKnown ? sum(COST_CATEGORIES.map(k => row.costs[k].amountCents)) : null),
      `Incorrect complete oneoff total: ${name}`);
  }
  const groups = [];
  for (const condition of protocol.conditions) {
    assert(condition.marketOverrides && condition.profileOverrides, 'Both override maps must be explicit');
    assert(Object.keys(condition.profileOverrides).every(k => ['integrationFailureProbability', 'weeklyMaintenanceCents'].includes(k)),
      'Unsupported profile intervention');
    for (const costProfileId of protocol.costProfileIds) {
      for (const policy of protocol.policies) groups.push({ condition, costProfileId, policy });
    }
  }
  const unknownCondition = protocol.conditions.find(c => c.id === protocol.unknownProfileScope.conditionId);
  assert(unknownCondition?.id === 'reference' && protocol.unknownProfileScope.allPolicies === true, 'Unknown costs use only the registered reference/both-policies boundary');
  for (const policy of protocol.policies) groups.push({ condition: unknownCondition, costProfileId: protocol.unknownProfileId, policy });
  for (const group of groups) {
    group.id = `${group.condition.id}__${group.costProfileId}__${group.policy.id}`;
    group.config = { ...protocol.baseConfig, ...group.condition.marketOverrides, id: `${protocol.id}/${group.id}` };
    assert(group.config.weeks === 52 && group.config.initialCashCents === 100000 && group.config.reserveCents === 20000,
      'A condition altered the finite capital/reserve/horizon');
    validateConfig(group.config);
    group.profiles = Object.fromEntries(['B', 'C'].map(arm => {
      const identity = effects.arms[arm], assignedCosts = clone(costs.profiles[group.costProfileId].costs);
      if (Object.hasOwn(group.condition.profileOverrides, 'weeklyMaintenanceCents')) {
        assignedCosts.weeklyMaintenance = {
          amountCents: group.condition.profileOverrides.weeklyMaintenanceCents, basis: 'scenario',
          explanation: 'Predeclared USD2/week second-capability upkeep stress; applied identically to B/C.'
        };
      }
      const profile = {
        schema: SCHEMA, id: identity.id, assetSHA256: identity.assetSHA256,
        acceptanceEvidenceSHA256: identity.acceptanceEvidenceSHA256, tested: identity.tested,
        ...protocol.candidateDefaults,
        policy: group.policy.policy, earliestWeek: group.policy.earliestWeek, lastDecisionWeek: group.policy.lastDecisionWeek,
        integrationFailureProbability: group.condition.profileOverrides.integrationFailureProbability ??
          protocol.candidateDefaults.integrationFailureProbability,
        costs: assignedCosts, effects: clone(identity.effects), effectEvidence: clone(identity.effectEvidence),
        unroundedComputeSavingsMicrocentsPerJob: identity.unroundedComputeSavingsMicrocentsPerJob
      };
      return [arm, validateProfile(profile)];
    }));
  }
  assert(groups.length === 80 && groups.length * protocol.seeds.length === 1920, 'Incorrect registered campaign size');
  assert(protocol.expected.pairedWorlds === 1920 && protocol.expected.groups === 80 && protocol.expected.enterpriseRuns === 5760,
    'Declared campaign totals do not match generated design');
  const representative = protocol.representativeSelection;
  assert(representative.conditionId === 'reference' && representative.seed === 8001 && representative.allPolicies === true,
    'Representative selection cannot change after registration');
  assert(JSON.stringify(representative.costProfileIds) === JSON.stringify(['low', 'reference', 'high', 'actual-unknown']),
    'All preselected reference cost profiles must be retained');
  return { protocol, costs, effects, groups, protocolPath };
}

export function verifyFreeze(inputs, freezePath) {
  const freeze = json(freezePath);
  assert(inputs.protocol.status === 'FROZEN_BEFORE_MARKET_OUTCOMES', 'Economic execution requires the frozen registered protocol');
  assert(typeof inputs.protocol.registrationURL === 'string' && inputs.protocol.registrationURL.startsWith('https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850'),
    'Public coordination registration reference required');
  assert(Number.isFinite(Date.parse(inputs.protocol.registeredAtUTC)), 'Registration time required');
  assert(freeze.schema === 'agi-alpha-second-investment-campaign-freeze/v1' && freeze.marketOutcomesInspected === false,
    'Explicit pre-outcome source freeze required');
  assert(Array.isArray(freeze.files) && freeze.files.length > 0, 'Source-bound freeze files required');
  const paths = new Set();
  for (const file of freeze.files) {
    assert(!paths.has(file.path) && HASH.test(file.sha256), 'Unique frozen paths and exact hashes required');
    paths.add(file.path);
    const bytes = readFileSync(localPath(file.path));
    assert(sha(bytes) === file.sha256, `Frozen source mismatch: ${file.path}`);
    if (Object.hasOwn(file, 'bytes')) assert(bytes.length === file.bytes, `Frozen byte count mismatch: ${file.path}`);
  }
  const required = [
    'run-campaign.mjs', 'continuation.mjs', 'continuation-core.mjs', 'core-transformation.json',
    'upstream/src/market.mjs', 'upstream/canonical/shadow-ledger.mjs', 'upstream/canonical/automated-costs.mjs',
    inputs.protocolPath, inputs.protocol.effectProfileFile, inputs.protocol.costProfilesFile
  ];
  for (const path of required) assert(paths.has(path), `Required economic input not frozen: ${path}`);
  assert(sha(readFileSync(localPath('upstream/src/market.mjs'))) ===
    '52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27', 'Original market source changed');
  return { freeze, freezeSHA256: sha(readFileSync(localPath(freezePath))) };
}

function compactArm(run, arm) {
  const s = run.summary, x = run.secondInvestment;
  return {
    arm, enterpriseProfitCents: s.profitCents, finalCashCents: s.finalCashCents,
    obligationsCents: s.obligationsCents, collectionsCents: s.grossCollectionsCents,
    accepted: s.enterpriseAccepted, attempts: s.enterpriseAttempts, rejected: s.enterpriseRejected,
    refundsCents: s.refundsCents, insolvent: s.insolvent,
    projectInclusiveProfitCents: x ? x.projectProfitAfterCompletedPrototypeCostsCents : s.profitCents,
    firstInvestmentWeek: s.investmentWeek,
    completeCostsPriced: x ? x.completeCostProfilePriced : true,
    declaredCompletePrototypeCents: x?.declaredCompletePrototypeOneoffCostCents ?? (arm === 'A' ? 0 : null),
    secondCostsInEnterpriseCents: x?.completeRealizedSecondCostsCents ?? 0,
    outsideEnterprisePrototypeCostCents: x ? x.outsideEnterprisePrototypeCostCents : 0,
    searchWeek: x?.searchWeek ?? null, secondAttemptWeek: x?.investmentWeek ?? null,
    modeledConstructionAttempted: x?.modeledConstructionAttempted ?? false,
    admitted: x?.financiallyAdmitted ?? false,
    secondInvestmentPaidFromGeneratedResources: x?.investmentPaidFromGeneratedResources ?? false,
    secondFailedIntegration: x?.failedIntegration ?? false,
    secondInvocations: x?.actualAssetInvocationsInModel ?? 0,
    directAvoidedSecondCostCents: x?.directAvoidedDeliveryCostCents ?? 0,
    directSecondCostRepayment: x?.directCostRepayment ?? false,
    terminalGeneratedFundsCents: x?.terminalFunding.availableCents ?? null,
    subcentComputeNetResidualMicrocents: x?.subcentComputeEffect?.netSavingsNotRepresentedByCentLedgerMicrocents ?? null,
    subcentComputeMaximumAbsoluteResidualUSD: x?.subcentComputeEffect?.maximumAbsoluteUnrepresentedUSD ?? null,
    completedResearchCostCountedExactlyOnce: x?.completedResearchCostCountedExactlyOnce ?? null,
    initialCheckpoint: x?.initialCheckpoint ?? null,
    firstSecondDecision: x?.decisions?.[0] ?? null,
    secondConstructionDecision: x?.decisions?.find(d =>
      ['invest-second-capability', 'operating-funded-unqualified-research-attempt'].includes(d.action)) ?? null
  };
}

const quantile = (sorted, q) => {
  if (!sorted.length) return null;
  const position = (sorted.length - 1) * q, lower = Math.floor(position), upper = Math.ceil(position);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
};
export function distribution(values) {
  const known = values.filter(v => typeof v === 'number' && Number.isFinite(v));
  const sorted = [...known].sort((a, b) => a - b), n = sorted.length;
  if (!n) return { n: 0, missing: values.length, mean: null, min: null, p05: null, median: null, p95: null,
    max: null, negative: 0, zero: 0, positive: 0, meanMC95Low: null, meanMC95High: null };
  const mean = sum(known) / n;
  const sampleVariance = n > 1 ? sum(known.map(v => (v - mean) ** 2)) / (n - 1) : null;
  const half = sampleVariance === null ? null : 1.96 * Math.sqrt(sampleVariance / n);
  return { n, missing: values.length - n, mean, min: sorted[0], p05: quantile(sorted, 0.05),
    median: quantile(sorted, 0.5), p95: quantile(sorted, 0.95), max: sorted.at(-1),
    negative: known.filter(v => v < 0).length, zero: known.filter(v => v === 0).length,
    positive: known.filter(v => v > 0).length,
    meanMC95Low: half === null ? null : mean - half, meanMC95High: half === null ? null : mean + half };
}

function summarizeGroup(group, rows, expected) {
  const output = { groupId: group.id, conditionId: group.condition.id, costProfileId: group.costProfileId,
    policyId: group.policy.id, completedSeeds: rows.length, expectedSeeds: expected,
    complete: rows.length === expected, unit: 'USD cents unless named otherwise', arms: {}, causal: {} };
  for (const arm of ['A', 'B', 'C']) {
    const armRows = rows.map(r => r.arms[arm]);
    const numericFields = ['enterpriseProfitCents', 'projectInclusiveProfitCents', 'finalCashCents', 'obligationsCents',
      'collectionsCents', 'accepted', 'attempts', 'rejected', 'refundsCents', 'declaredCompletePrototypeCents',
      'secondCostsInEnterpriseCents', 'outsideEnterprisePrototypeCostCents', 'secondInvocations',
      'directAvoidedSecondCostCents', 'terminalGeneratedFundsCents', 'subcentComputeNetResidualMicrocents',
      'subcentComputeMaximumAbsoluteResidualUSD'];
    output.arms[arm] = Object.fromEntries(numericFields.map(k => [k, distribution(armRows.map(r => r[k]))]));
    output.arms[arm].counts = Object.fromEntries(['insolvent', 'modeledConstructionAttempted', 'admitted',
      'secondInvestmentPaidFromGeneratedResources', 'secondFailedIntegration', 'directSecondCostRepayment']
      .map(k => [k, armRows.filter(r => r[k]).length]));
    output.arms[arm].counts.conditionalFinancialGatePasses = arm === 'A' ? 0 : rows.filter(r =>
      r.qualification[arm].conditionalModeledFinancialGatePassed).length;
  }
  for (const key of ['B_minus_A_profitCents', 'C_minus_A_profitCents', 'B_minus_C_profitCents',
    'B_minus_A_projectInclusiveProfitCents', 'C_minus_A_projectInclusiveProfitCents',
    'B_minus_C_projectInclusiveProfitCents', 'B_minus_A_accepted', 'C_minus_A_accepted']) {
    output.causal[key] = distribution(rows.map(r => r.causal[key]));
  }
  return output;
}

const csvValue = value => value === null || value === undefined ? '' :
  /[",\n\r]/.test(String(value)) ? `"${String(value).replaceAll('"', '""')}"` : String(value);
function toCsv(rows, fields) {
  return fields.join(',') + '\n' + rows.map(row => fields.map(k => csvValue(row[k])).join(',')).join('\n') + '\n';
}
async function fileHash(path) {
  const h = createHash('sha256');
  for await (const chunk of createReadStream(path)) h.update(chunk);
  return h.digest('hex');
}

export async function runRegisteredCampaign(inputs, freezeReceipt, outputPath) {
  const { protocol, groups } = inputs;
  const output = localPath(outputPath);
  assert(!existsSync(output), 'Refusing to overwrite or restart an existing campaign output');
  mkdirSync(dirname(output), { recursive: true }); mkdirSync(output);
  const startedUTC = new Date().toISOString(), started = performance.now(), cpuStart = process.cpuUsage();
  const resources = () => {
    const cpu = process.cpuUsage(cpuStart);
    return { wallSeconds: (performance.now() - started) / 1000, cpuSeconds: (cpu.user + cpu.system) / 1_000_000 };
  };
  const budget = () => {
    const r = resources();
    assert(r.wallSeconds <= protocol.limits.maxWallSeconds && r.cpuSeconds <= protocol.limits.maxCpuSeconds,
      `Registered180second budget reached: ${JSON.stringify(r)}`);
  };
  writeFileSync(resolve(output, 'STARTED.json'), JSON.stringify({ schema: 'agi-alpha-second-investment-start/v1',
    startedUTC, freezeSHA256: freezeReceipt.freezeSHA256, expected: protocol.expected,
    limits: protocol.limits, runKind: 'FROZEN_MARKET_CONFIRMATION', actualFinancialAction: false }, null, 2) + '\n');
  const outputGzip = resolve(output, 'complete-paired-worlds.jsonl.gz');
  const gzip = createGzip({ level: 6 }), destination = createWriteStream(outputGzip, { flags: 'wx' });
  let archiveError = null;
  const archiveCompletion = pipeline(gzip, destination).catch(error => { archiveError = error; });
  const deadline = setTimeout(() => {
    const error = Error('Registered180second wall budget reached during asynchronous archive work');
    gzip.destroy(error); destination.destroy(error);
  }, protocol.limits.maxWallSeconds * 1000);
  const rawHash = createHash('sha256'), rows = [], representatives = [], groupRows = new Map(groups.map(g => [g.id, []]));
  let attemptedWorlds = 0, completedWorlds = 0, failure = null, current = null, archiveCompleted = false;
  try {
    for (const group of groups) {
      for (const seed of protocol.seeds) {
        current = { groupId: group.id, conditionId: group.condition.id, costProfileId: group.costProfileId,
          policyId: group.policy.id, seed };
        budget(); if (archiveError) throw archiveError;
        attemptedWorlds++;
        const paired = pairedContinuation(group.config, seed, group.profiles);
        assert(paired.commonPrefixExact, 'Inherited enterprise checkpoint mismatch');
        for (const arm of ['B', 'C']) {
          const x = paired.arms[arm].secondInvestment;
          if (x.completeCostProfilePriced) assert(x.completedResearchCostCountedExactlyOnce,
            `Completed prototype cost not counted exactly once: ${arm}`);
          assert(paired.arms[arm].observedCustomerCollectionsCents === 0, 'Observed receipts contaminated');
        }
        const full = { ...current, schema: 'agi-alpha-second-investment-campaign-world/v1',
          sourceFreezeSHA256: freezeReceipt.freezeSHA256, paired };
        const line = JSON.stringify(full) + '\n'; rawHash.update(line);
        if (!gzip.write(line)) await once(gzip, 'drain');
        const compact = { ...current, arms: Object.fromEntries(['A', 'B', 'C'].map(arm => [arm, compactArm(paired.arms[arm], arm)])),
          causal: paired.causal, qualification: paired.qualification };
        rows.push(compact); groupRows.get(group.id).push(compact); completedWorlds++;
        const selected = protocol.representativeSelection;
        if (group.condition.id === selected.conditionId && seed === selected.seed && selected.costProfileIds.includes(group.costProfileId)) {
          representatives.push(full);
        }
        if (completedWorlds % 96 === 0) process.stdout.write(JSON.stringify({ phase: 'executing-frozen-design',
          completedWorlds, expected: protocol.expected.pairedWorlds, resources: resources() }) + '\n');
        budget();
      }
    }
  } catch (error) {
    failure = { message: error.message, at: current, attemptedWorlds, completedWorlds,
      resources: resources(), partialResultsRetained: true, automaticRetry: false };
  } finally {
    gzip.end(); await archiveCompletion;
    clearTimeout(deadline);
    archiveCompleted = archiveError === null;
    if (archiveError && failure === null) failure = { message: archiveError.message, at: current,
      attemptedWorlds, completedWorlds, partialResultsRetained: true, automaticRetry: false };
  }
  const executionResources = resources();
  if (!failure && (executionResources.wallSeconds > protocol.limits.maxWallSeconds || executionResources.cpuSeconds > protocol.limits.maxCpuSeconds)) {
    failure = { message: 'Registered budget reached during archive finalization', resources: executionResources,
      attemptedWorlds, completedWorlds, partialResultsRetained: true, automaticRetry: false };
  }
  const complete = failure === null && completedWorlds === protocol.expected.pairedWorlds && archiveCompleted;
  const summaries = groups.map(group => summarizeGroup(group, groupRows.get(group.id), protocol.seeds.length));
  const compactPath = resolve(output, 'compact-worlds.jsonl');
  writeFileSync(compactPath, rows.map(row => JSON.stringify(row)).join('\n') + '\n');
  writeFileSync(resolve(output, 'predeclared-representatives.json'), JSON.stringify({
    selection: protocol.representativeSelection, selectedBeforeOutcomes: true, worlds: representatives }, null, 2) + '\n');
  writeFileSync(resolve(output, 'summary.json'), JSON.stringify({
    schema: 'agi-alpha-second-investment-campaign-summary/v1', complete,
    sourceFreezeSHA256: freezeReceipt.freezeSHA256, expected: protocol.expected,
    completedWorlds, groups: summaries,
    interpretation: protocol.inference,
    actualCustomerCollectionsCents: 0, actualTransactions: 0,
    unknownCostPolicy: 'Unknown project-inclusive costs and deltas remain null and count as missing. They are never replaced by zero.',
    gridWarning: 'Counts across designed conditions are not market probabilities. No automatic success narrative is generated.'
  }, null, 2) + '\n');
  const flat = rows.map(row => ({
    group_id: row.groupId, condition: row.conditionId, cost_profile: row.costProfileId, policy: row.policyId, seed: row.seed,
    A_profit_cents: row.arms.A.enterpriseProfitCents, B_profit_cents: row.arms.B.enterpriseProfitCents,
    C_profit_cents: row.arms.C.enterpriseProfitCents,
    B_project_profit_cents: row.arms.B.projectInclusiveProfitCents, C_project_profit_cents: row.arms.C.projectInclusiveProfitCents,
    B_minus_A_project_cents: row.causal.B_minus_A_projectInclusiveProfitCents,
    C_minus_A_project_cents: row.causal.C_minus_A_projectInclusiveProfitCents,
    B_minus_C_project_cents: row.causal.B_minus_C_projectInclusiveProfitCents,
    B_complete_costs_priced: row.arms.B.completeCostsPriced,
    B_research_attempted: row.arms.B.modeledConstructionAttempted,
    C_research_attempted: row.arms.C.modeledConstructionAttempted,
    B_admitted: row.arms.B.admitted, C_admitted: row.arms.C.admitted,
    B_conditional_financial_gate: row.qualification.B.conditionalModeledFinancialGatePassed,
    C_conditional_financial_gate: row.qualification.C.conditionalModeledFinancialGatePassed,
    B_generated_funded: row.arms.B.secondInvestmentPaidFromGeneratedResources,
    C_generated_funded: row.arms.C.secondInvestmentPaidFromGeneratedResources,
    B_second_uses: row.arms.B.secondInvocations, C_second_uses: row.arms.C.secondInvocations,
    B_declared_complete_cost_cents: row.arms.B.declaredCompletePrototypeCents,
    B_outside_prototype_cost_cents: row.arms.B.outsideEnterprisePrototypeCostCents,
    C_outside_prototype_cost_cents: row.arms.C.outsideEnterprisePrototypeCostCents,
    B_second_costs_in_enterprise_cents: row.arms.B.secondCostsInEnterpriseCents,
    B_subcent_residual_microcents: row.arms.B.subcentComputeNetResidualMicrocents,
    C_subcent_residual_microcents: row.arms.C.subcentComputeNetResidualMicrocents,
    A_accepted: row.arms.A.accepted, B_accepted: row.arms.B.accepted, C_accepted: row.arms.C.accepted,
    A_insolvent: row.arms.A.insolvent, B_insolvent: row.arms.B.insolvent, C_insolvent: row.arms.C.insolvent
  }));
  if (flat.length) writeFileSync(resolve(output, 'outcomes.csv'), toCsv(flat, Object.keys(flat[0])));
  const csvSummary = summaries.map(s => ({
    group_id: s.groupId, condition: s.conditionId, cost_profile: s.costProfileId, policy: s.policyId,
    completed_seeds: s.completedSeeds, complete: s.complete,
    B_minus_A_project_mean_cents: s.causal.B_minus_A_projectInclusiveProfitCents.mean,
    B_minus_A_project_p05_cents: s.causal.B_minus_A_projectInclusiveProfitCents.p05,
    B_minus_A_project_median_cents: s.causal.B_minus_A_projectInclusiveProfitCents.median,
    B_minus_A_project_p95_cents: s.causal.B_minus_A_projectInclusiveProfitCents.p95,
    B_minus_A_project_losses: s.causal.B_minus_A_projectInclusiveProfitCents.negative,
    B_minus_A_project_unknown: s.causal.B_minus_A_projectInclusiveProfitCents.missing,
    C_minus_A_project_mean_cents: s.causal.C_minus_A_projectInclusiveProfitCents.mean,
    B_minus_C_project_mean_cents: s.causal.B_minus_C_projectInclusiveProfitCents.mean,
    B_research_attempts: s.arms.B.counts.modeledConstructionAttempted,
    B_admissions: s.arms.B.counts.admitted, B_financial_gate_passes: s.arms.B.counts.conditionalFinancialGatePasses,
    C_financial_gate_passes: s.arms.C.counts.conditionalFinancialGatePasses,
    B_mean_accepted: s.arms.B.accepted.mean, B_mean_final_cash_cents: s.arms.B.finalCashCents.mean
  }));
  writeFileSync(resolve(output, 'summary.csv'), toCsv(csvSummary, Object.keys(csvSummary[0])));
  if (failure) writeFileSync(resolve(output, 'FAILURE.json'), JSON.stringify(failure, null, 2) + '\n');
  const receipt = {
    schema: 'agi-alpha-second-investment-campaign-completion/v1', complete, startedUTC,
    completedUTC: new Date().toISOString(), sourceFreezeSHA256: freezeReceipt.freezeSHA256,
    expectedPairedWorlds: protocol.expected.pairedWorlds, attemptedWorlds, completedWorlds,
    completedEnterpriseRuns: completedWorlds * 3, archiveCompleted,
    completePairedWorldsRawSHA256: rawHash.digest('hex'),
    completePairedWorldsGzipSHA256: await fileHash(outputGzip),
    summarySHA256: await fileHash(resolve(output, 'summary.json')),
    compactWorldsSHA256: await fileHash(compactPath),
    executionResources, totalProcessResourcesIncludingReporting: resources(),
    scientificBudgetIncludes: 'Market execution, serialization, compression and stream finalization.',
    reportingOutsideScientificBudget: 'Descriptive summary formatting and artifact hashing; no additional economic scenarios.',
    limits: protocol.limits, failure,
    actualCustomerCollectionsCents: 0, actualTransactions: 0, automaticRetry: false,
    resultInterpretation: 'Diagnostic output only. Financial qualification remains conditional on frozen production evidence and explicit economic assumptions.'
  };
  writeFileSync(resolve(output, 'completion.json'), JSON.stringify(receipt, null, 2) + '\n');
  process.stdout.write(JSON.stringify(receipt, null, 2) + '\n');
  return receipt;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputs = readInputs(args.protocol);
  if (args.validateOnly) {
    if (args.freeze) verifyFreeze(inputs, args.freeze);
    process.stdout.write(JSON.stringify({ valid: true, economicOutcomesExecuted: 0,
      groups: inputs.groups.length, pairedWorldsPlanned: inputs.protocol.expected.pairedWorlds,
      protocolSHA256: sha(readFileSync(localPath(args.protocol))) }) + '\n');
    return;
  }
  assert(args.freeze && args.output, 'Economic execution requires --freeze and a new --output directory');
  const freezeReceipt = verifyFreeze(inputs, args.freeze);
  const result = await runRegisteredCampaign(inputs, freezeReceipt, args.output);
  if (!result.complete) process.exitCode = 1;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
}
