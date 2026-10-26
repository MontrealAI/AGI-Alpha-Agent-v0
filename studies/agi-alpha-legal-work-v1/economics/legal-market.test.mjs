import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {actualLedger, configuration, simulateLegal, unitEconomics, validateProduction} from './legal-market.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
function fixture() {
  return {schema: 'UNIT_TEST_FIXTURE_NOT_RESEARCH_EVIDENCE', records: ['B', 'C1', 'C', 'D'].flatMap(arm =>
    Array.from({length: 12}, (_, i) => ({case_id: `unit-${i}`, arm, accepted_deterministic:
      arm === 'B' ? i < 6 : arm === 'C1' || arm === 'D' ? i < 9 : true,
    professional_acceptance: 'unknown', runtime_seconds: 0.01, attempts: 1, escalation_required: i > 8}))) };
}

test('unchanged canonical accounting and market libraries retain inherited identities', () => {
  const manifest = JSON.parse(readFileSync(resolve(HERE, 'inherited-manifest.json')));
  for (const row of manifest.source_files)
    assert.equal(createHash('sha256').update(readFileSync(resolve(HERE, row.path))).digest('hex'), row.sha256);
});
test('technical acceptance does not create professional or financial acceptance', () => {
  const result = actualLedger(fixture());
  assert.equal(result.summary.observed.revenue, 0);
  assert.equal(result.summary.observed.availableSurplus, null);
  assert.equal(result.summary.scenario.availableSurplus, null);
  assert(result.summary.missions.every(row => row.acceptance === 'unknown'));
});
test('missing professional status and mismatched cases are rejected', () => {
  const a = fixture(); delete a.records[0].professional_acceptance;
  assert.throws(() => validateProduction(a), /Professional acceptance/);
  const b = fixture(); b.records.pop();
  assert.throws(() => validateProduction(b), /Matched case/);
});
test('duplicate attempts cannot silently inflate evaluation sample', () => {
  const a = fixture(); a.records.push(a.records[0]);
  assert.throws(() => validateProduction(a), /Duplicate/);
});
test('nonfinite or negative runtime is rejected', () => {
  for (const number of [NaN, Infinity, -1]) {
    const a = fixture(); a.records[0].runtime_seconds = number;
    assert.throws(() => validateProduction(a), /runtime/);
  }
});
test('unobserved human review is preserved as unknown', () => {
  assert.equal(validateProduction(fixture()).summary.B.measuredProfessionalReviewMinutes, null);
  assert.equal(unitEconomics(fixture()).stages.C.historicalFullyAllocatedCostCents, null);
});
test('zero assumed correction and identical runtime produce no incremental monetary saving', () => {
  const result = unitEconomics(fixture());
  assert.equal(result.stages.B.providerMarginalCostCents, result.stages.C.providerMarginalCostCents);
  assert.equal(result.stages.B.buyerProfessionalReviewCents, result.stages.C.buyerProfessionalReviewCents);
});
test('all failed technical attempts retain costs under an explicit correction scenario', () => {
  const result = unitEconomics(fixture(), {technicalCorrectionMinutes: 12});
  assert.equal(result.stages.B.providerMarginalComponentsCents.correction, 400);
  assert.equal(result.stages.C.providerMarginalComponentsCents.correction, 0);
});
test('capacity productivity is distinct from cash savings', () => {
  const result = unitEconomics(fixture(), {reviewMinutesC: 10, buyerOnboardingMinutes: 0});
  assert(result.stages.C.customerOpportunityCostSavingCents > 0);
  assert.equal(result.stages.C.customerAvoidedPayrollCashCents, 0);
  assert.equal(result.stages.C.customerNetCashSavingCents, -1000);
});
test('canonical scenario receipts remain outside observed collections', () => {
  const result = simulateLegal(fixture(), {reviewMinutesB: 0, reviewMinutesC: 0, reviewMinutesD: 0,
    buyerOnboardingMinutes: 0, alternativeToolCentsPerJob: 10000, capacityRealizationFraction: 1}, 1, 'baseline');
  assert(result.summary.simulatedCollectionsCents > 0);
  assert.equal(result.canonicalSummary.observed.revenue, 0);
  assert.equal(result.summary.observedCollectionsCents, 0);
  assert.equal(result.summary.remainingSeedPlusEarnedCashCents,
    result.config.initialSeedCents + result.summary.cashOperatingProfitCents);
});
test('seed remains outside available earned surplus', () => {
  const result = simulateLegal(fixture(), {arrivalProbability: 0, initialSeedCents: 1000000}, 1, 'reinvest');
  assert.equal(result.summary.availableOperatingSurplusCents, 0);
  assert.equal(result.investments.length, 0);
  assert(result.summary.remainingSeedPlusEarnedCashCents > 0);
});
test('no claimed worthwhile investment without positive benefit', () => {
  const result = simulateLegal(fixture(), {reviewMinutesB: 0, reviewMinutesC: 0, reviewMinutesD: 0,
    buyerOnboardingMinutes: 0, alternativeToolCentsPerJob: 10000, capacityRealizationFraction: 1,
    capabilityConstructionCents: 1, capabilityFailedConstructionCents: 0, capabilityMaintenancePerUseCents: 0}, 1);
  assert.equal(result.investments.length, 0);
  assert(result.investmentDecisions.every(row => row.expectedNetAfterPauseCents <= 0));
});
test('rejected simulated attempts have no invoice but keep cost and review time', () => {
  const result = simulateLegal(fixture(), {reviewMinutesB: 0, professionalAcceptanceProbability: 0.5,
    buyerOnboardingMinutes: 0, alternativeToolCentsPerJob: 10000, buyerValueMultiplier: 10,
    capacityRealizationFraction: 1}, 1, 'baseline');
  assert(result.jobs.some(row => row.acceptedSimulated === false));
  assert(result.jobs.filter(row => row.acceptedSimulated === false).every(row => row.invoiceCents === 0 && row.deliveryCostCents > 0));
  assert(result.summary.customerProfessionalAndIntegrationMinutes > 0);
});
test('paired worlds use identical opportunities and freeze seed deterministically', () => {
  const a = simulateLegal(fixture(), {}, 19, 'baseline');
  const b = simulateLegal(fixture(), {}, 19, 'reinvest');
  assert.deepEqual(a.summary, b.summary);
  assert.deepEqual(a.jobs, b.jobs);
  assert.deepEqual(b, simulateLegal(fixture(), {}, 19, 'reinvest'));
});
test('fully allocated outcome stays null until explicit historical cost is supplied', () => {
  const a = simulateLegal(fixture(), {}, 1, 'baseline');
  assert.equal(a.summary.fullyAllocatedProfitCents, null);
  assert.equal(a.summary.researchCostRecovered, null);
  const b = simulateLegal(fixture(), {historicalResearchCostCents: 12345}, 1, 'baseline');
  assert.equal(b.summary.fullyAllocatedProfitCents, a.summary.cashOperatingProfitCents - 12345);
});
test('unaffordable opening capability is rejected rather than funded by fictitious cash', () => {
  assert.throws(() => simulateLegal(fixture(), {initialSeedCents: 100}, 1, 'retained-from-start'), /seed/);
});
test('unknown monetary fields and token funding cannot enter assumptions', () => {
  assert.throws(() => configuration({tokenAppreciationCents: 1000000}), /Unknown parameter/);
  assert.throws(() => configuration({cashRealizationFraction: 0.9, capacityRealizationFraction: 0.5}), /Cash realization/);
});
test('successive construction uses earned surplus and preserves dependency expiry', () => {
  const input = fixture();
  for (const row of input.records) {
    row.accepted_deterministic = true;
    row.attempts = {B: 5, C1: 3, C: 1, D: 6}[row.arm];
  }
  const result = simulateLegal(input, {buyerOnboardingMinutes: 0, providerOnboardingMinutes: 0,
    alternativeToolCentsPerJob: 10000, capacityRealizationFraction: 1, reviewMinutesB: 0, reviewMinutesC: 0, reviewMinutesD: 0,
    offerPriceCents: 600, technicalCorrectionMinutes: 0, capabilityConstructionCents: 100,
    capabilityFailedConstructionCents: 0, secondCapabilityConstructionCents: 100, secondCapabilityFailedConstructionCents: 0,
    capabilityMaintenancePerUseCents: 0, secondCapabilityMaintenancePerUseCents: 0,
    reserveCents: 0, fixedWeeklyCents: 0, maintenanceWeeklyCents: 0, acquisitionCentsPerProspect: 0,
    investmentEarliestWeek: 2, arrivalProbability: 1, professionalAcceptanceProbability: 1, collectionProbability: 1, paymentDelayWeeks: 0}, 1);
  assert.equal(result.investments.length, 2);
  const [first, second] = result.investments;
  assert(first.earnedAvailableCents >= first.fundingRequiredCents);
  assert(second.earnedAvailableCents >= second.fundingRequiredCents);
  assert(second.week > result.summary.firstDirectRepaymentWeek);
  assert(second.expiresWeek <= first.expiresWeek);
  assert.equal(result.summary.providerCostCategoriesCents.capability, first.fundingRequiredCents + second.fundingRequiredCents);
});
test('an expired capability stops reuse without historical attestations extending its life', () => {
  const result = simulateLegal(fixture(), {capabilityUsefulLifeWeeks: 2, reviewMinutesB: 0, reviewMinutesC: 0,
    buyerOnboardingMinutes: 0, alternativeToolCentsPerJob: 10000, capacityRealizationFraction: 1}, 1, 'retained-from-start');
  assert(result.jobs.some(row => row.stage === 'C1'));
  assert(result.jobs.filter(row => row.stage).every(row => row.week < 2 || row.stage === 'B'));
});
test('acquisition charges declined prospects and stops charging an onboarded buyer', () => {
  const declined = simulateLegal(fixture(), {weeks: 1, buyers: 1, arrivalProbability: 1}, 1, 'baseline');
  assert.equal(declined.summary.providerAttempts, 0);
  assert.equal(declined.summary.providerCostCategoriesCents.business, 500 + 200);
  const accepted = simulateLegal(fixture(), {weeks: 3, buyers: 1, arrivalProbability: 1, reviewMinutesB: 0,
    buyerOnboardingMinutes: 0, alternativeToolCentsPerJob: 10000, capacityRealizationFraction: 1,
    professionalAcceptanceProbability: 1}, 1, 'baseline');
  assert.equal(accepted.summary.providerAttempts, 3);
  assert.equal(accepted.summary.providerCostCategoriesCents.business, 3 * 500 + 200 + 4000);
});
test('deterministically rejected packets never earn receipts even with perfect assumed professional acceptance', () => {
  const input = fixture(); for (const row of input.records) row.accepted_deterministic = false;
  const result = simulateLegal(input, {reviewMinutesB: 0, buyerOnboardingMinutes: 0,
    alternativeToolCentsPerJob: 10000, capacityRealizationFraction: 1, professionalAcceptanceProbability: 1,
    collectionProbability: 1, paymentDelayWeeks: 0, technicalCorrectionMinutes: 15}, 1, 'baseline');
  assert(result.summary.providerAttempts > 0);
  assert.equal(result.summary.simulatedAccepted, 0);
  assert.equal(result.summary.simulatedCollectionsCents, 0);
  assert(result.summary.providerCostCategoriesCents.delivery > 0);
  assert(result.jobs.filter(row => row.choice === 'agi-alpha').every(row => row.invoiceCents === 0));
});
