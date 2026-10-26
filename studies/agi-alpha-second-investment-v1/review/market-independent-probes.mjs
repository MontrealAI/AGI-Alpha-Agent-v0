// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {dirname, resolve} from 'node:path';
import {simulate as original, defaultConfig} from '../market/upstream/src/market.mjs';
import {simulate as patched} from '../market/continuation-core.mjs';
import {pairedContinuation, generatedResources, COST_CATEGORIES, SCHEMA} from '../market/continuation.mjs';

const directory = dirname(fileURLToPath(import.meta.url));
const started = performance.now();
const usage = process.cpuUsage();
const results = [];
const check = (name, operation) => {
  try { results.push({name, passed: true, observation: operation()}); }
  catch (error) { results.push({name, passed: false, error: String(error.stack)}); }
};
const config = {
  id: 'INDEPENDENT-SYNTHETIC-LEDGER-CONTROL-NOT-CONFIRMATION', weeks: 16,
  buyers: 4, arrivalProbability: 1, supportedFraction: 1, initialCashCents: 1000000,
  reserveCents: 1000, initialSetupCents: 100, weeklyOverheadCents: 10,
  paymentProbability: 1, paymentDelayWeeks: 1, expenseDelayWeeks: 1,
  initialTrust: 0.99, skepticalShare: 0, successProbability: 1, overloadPenalty: 0,
  humanHourlyCents: 100000, aiInitialPriceCents: 1000000, aiCostCents: 100000,
  diyEffortFraction: 10, integrationCents: 0, switchingCents: 0,
  enterpriseDays: 0, delayCostCentsPerDay: 0, competitorStrategy: 'fixed',
  pricingPolicy: 'fixed', initialPriceCents: 2000, adoptionHours: 0.01,
  investmentFunding: 'seed-funded', investmentEarliestWeek: 1,
  assetMaintenanceCentsPerWeek: 1, buyerProcurementBudgetCents: 100000,
};
const profile = overrides => ({
  schema: SCHEMA, id: 'SYNTHETIC-ARITHMETIC-NOT-A-RESEARCH-ASSET',
  assetSHA256: 'e'.repeat(64), acceptanceEvidenceSHA256: 'f'.repeat(64),
  tested: true, researchPrototypeConstructed: true, policy: 'completed-research-replay',
  earliestWeek: 6, lastDecisionWeek: 6, pauseWeeks: 2, usefulLifeWeeks: 5,
  researchEnvelopeCents: 10000, forecastDiscount: 0.5, integrationFailureProbability: 0,
  costs: Object.fromEntries([...COST_CATEGORIES, 'weeklyMaintenance'].map(key =>
    [key, {amountCents: 1, basis: 'scenario', explanation: 'Synthetic arithmetic fixture; no measured fee.'}])),
  effects: {providerMinutesSaved: 2, computeAndToolCentsSaved: 0, customerReviewMinutesSaved: 0},
  effectEvidence: {providerMinutesSaved: 'Synthetic only.', computeAndToolCentsSaved: 'Synthetic zero.',
    customerReviewMinutesSaved: 'Synthetic zero.'}, ...overrides,
});

check('generated continuation core is exactly the disclosed frozen-source transformation', () => {
  const transformation = JSON.parse(readFileSync(resolve(directory, '../market/core-transformation.json'), 'utf8'));
  const originalBytes = readFileSync(resolve(directory, '../market/upstream/src/market.mjs'));
  const digest = bytes => createHash('sha256').update(bytes).digest('hex');
  assert.equal(digest(originalBytes), transformation.originalSHA256);
  let reconstructed = originalBytes.toString('utf8');
  for (const patch of transformation.patches) {
    assert.equal(reconstructed.split(patch.before).length - 1, 1);
    reconstructed = reconstructed.replace(patch.before, patch.after);
  }
  assert.equal(reconstructed, readFileSync(resolve(directory, '../market/continuation-core.mjs'), 'utf8'));
  assert.equal(digest(reconstructed), transformation.resultSHA256);
  return {singleOccurrencePatches: transformation.patches.length, exactByteMatch: true};
});

check('neutral hook-free core matches original with transactions, defaults, and delayed refunds', () => {
  let transactions = 0;
  for (const changes of [{}, {paymentDelayWeeks: 4, expenseDelayWeeks: 3},
      {successProbability: 0.5, refundProbability: 1, refundDelayWeeks: 3},
      {paymentProbability: 0.5, qualityShockWeek: 8, qualityShockFactor: 0.5}]) {
    for (const arm of ['A', 'B', 'C']) {
      const a = original({...config, ...changes}, 93217, arm);
      const b = patched({...config, ...changes}, 93217, arm);
      assert.deepEqual(b, a);
      transactions += a.histories.cash.length;
    }
  }
  assert.ok(transactions > 0);
  return {comparisons: 12, syntheticCashEvents: transactions};
});

check('same checkpoint, all second costs, delayed activation, and cash identity hold', () => {
  const p = profile();
  const result = pairedContinuation(config, 93217, {B: p, C: p});
  assert.equal(result.commonPrefixExact, true);
  assert.deepEqual(result.arms.B.histories, result.arms.C.histories);
  const arm = result.arms.B;
  const investment = arm.secondInvestment;
  assert.equal(investment.modeledConstructionAttempted, true);
  assert.equal(investment.availableWeek, 8);
  assert.equal(investment.completeRealizedSecondCostsCents, 13);
  assert.equal(investment.completedResearchCostCountedExactlyOnce, true);
  assert.equal(investment.outsideEnterprisePrototypeCostCents, 0);
  assert.equal(investment.investmentPaidFromGeneratedResources, true);
  assert.ok(arm.histories.jobs.filter(j => j.secondAssetSHA256).every(j => j.week >= 8 && j.week < 13));
  assert.equal(arm.summary.finalCashCents, config.initialCashCents +
    arm.histories.cash.reduce((sum, event) => sum + event.amountCents, 0));
  return {attempted: true, financiallyAdmitted: investment.financiallyAdmitted,
    syntheticSecondInvocations: investment.actualAssetInvocationsInModel,
    completeSyntheticCostCents: investment.completeRealizedSecondCostsCents};
});

check('direct repayment is narrower than paired economic repayment', () => {
  const p = profile();
  const result = pairedContinuation(config, 93217, {B: p, C: p});
  assert.equal(result.arms.B.secondInvestment.directCostRepayment, true);
  assert.ok(result.causal.B_minus_A_projectInclusiveProfitCents < 0);
  assert.equal(result.arms.B.secondInvestment.financiallyAdmitted, false);
  assert.equal(result.qualification.B.conditionalModeledFinancialGatePassed, false);
  return {directCostRepayment: true, projectInclusiveIncrementalProfitNegative: true,
    explanation: 'Construction pauses forgo revenue; direct avoided delivery cost does not measure that loss.'};
});

check('signed regressions remain penalties and cannot pass the financial qualification', () => {
  const p = profile({effects: {
    providerMinutesSaved: -0.5, computeAndToolCentsSaved: -1, customerReviewMinutesSaved: -1
  }, unroundedComputeSavingsMicrocentsPerJob: -1_250_000});
  const result = pairedContinuation(config, 93217, {B: p, C: p});
  const second = result.arms.B.secondInvestment;
  assert.equal(second.modeledConstructionAttempted, true);
  assert.ok(second.actualAssetInvocationsInModel > 0);
  assert.ok(second.directAvoidedDeliveryCostCents < 0);
  assert.ok(second.subcentComputeEffect.netSavingsNotRepresentedByCentLedgerMicrocents < 0);
  assert.equal(second.financiallyAdmitted, false);
  assert.equal(second.directCostRepayment, false);
  assert.equal(result.qualification.B.conditionalModeledFinancialGatePassed, false);
  assert.ok(result.causal.B_minus_A_projectInclusiveProfitCents < 0);
  return {negativeEffectsPreserved: true, qualificationPassed: false, syntheticModeledUses: second.actualAssetInvocationsInModel};
});

check('unknown research fees remain unknown and do not enter available capital', () => {
  const p = profile(); p.costs.modelAndTools = {
    amountCents: null, basis: 'unknown', explanation: 'Fee was not observed.'};
  const result = pairedContinuation(config, 93217, {B: p, C: p});
  assert.deepEqual(result.arms.B.histories, result.arms.A.histories);
  assert.equal(result.arms.B.secondInvestment.outsideEnterprisePrototypeCostCents, null);
  assert.equal(result.arms.B.secondInvestment.projectProfitAfterCompletedPrototypeCostsCents, null);
  assert.equal(result.arms.B.secondInvestment.modeledConstructionAttempted, false);
  return {projectProfit: null, fullPrototypeCost: null, hiddenCashInjection: false};
});

check('unpaid refunds and delivery obligations constrain funds, historical seed is added back once', () => {
  const f = {
    cashCents: 13000, grossCollectionsCents: 5000,
    costs: {capability: 1000, business: 500, delivery: 1500, refund: 500, maintenance: 0},
    bills: [
      {id: 'opening', week: 0, category: 'capability', amountCents: 1000, paid: true, paidWeek: 0,
        reference: 'upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing'},
      {id: 'delivery', category: 'delivery', amountCents: 1000, paid: false},
      {id: 'refund', category: 'refund', amountCents: 500, paid: false},
    ],
    cashEvents: [{week: 0, type: 'expense_payment', amountCents: -1000, reference: 'opening'},
      {week: 1, type: 'simulated_collection', amountCents: 5000, reference: 'invoice'}],
  };
  const c = {...defaultConfig, initialCashCents: 10000, reserveCents: 2000};
  const funds = generatedResources(f, c);
  assert.equal(funds.availableCents, 2500);
  assert.equal(funds.unpaidObligationsCents, 1500);
  assert.equal(funds.seedPaidOpeningHistoryCents, 1000);
  assert.equal(funds.generatedBoundCents, 2500);
  f.bills[0].paidWeek = 2;
  assert.equal(generatedResources(f, c).seedPaidOpeningHistoryCents, 0);
  assert.equal(generatedResources(f, c).availableCents, 1500);
  return {availableBeforeLateHistoryCents: 2500, availableAfterLateHistoryCents: 1500};
});

const cpu = process.cpuUsage(usage);
const artifact = {
  schema: 'independent-second-investment-market-controls/v1',
  purpose: 'Synthetic software controls only; not research confirmation, real buyers or economic evidence.',
  sourceSHA256: Object.fromEntries(['continuation.mjs', 'continuation-core.mjs', 'build-core.mjs'].map(name =>
    [name, createHash('sha256').update(readFileSync(resolve(directory, '../market', name))).digest('hex')])),
  elapsedWallSeconds: (performance.now() - started) / 1000,
  processCpuSeconds: (cpu.user + cpu.system) / 1e6, results,
  allPassed: results.every(item => item.passed),
};
writeFileSync(resolve(directory, 'market-independent-probes.json'), JSON.stringify(artifact, null, 2) + '\n');
console.log(JSON.stringify({allPassed: artifact.allPassed, controls: results.length,
  failures: results.filter(item => !item.passed)}));
if (!artifact.allPassed) process.exitCode = 1;
