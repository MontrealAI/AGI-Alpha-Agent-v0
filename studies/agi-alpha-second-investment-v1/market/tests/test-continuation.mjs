// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { simulate as legacy, defaultConfig, randomDraw } from '../upstream/src/market.mjs';
import { simulate as patched } from '../continuation-core.mjs';
import { createSecondHooks, generatedResources, COST_CATEGORIES, SCHEMA,
  validateProfile, pairedContinuation } from '../continuation.mjs';

const syntheticProfile = overrides => ({
  schema: SCHEMA, id: 'SYNTHETIC-UNIT-TEST-NOT-A-RESEARCH-ASSET',
  assetSHA256: 'a'.repeat(64), acceptanceEvidenceSHA256: 'b'.repeat(64), tested: true,
  researchPrototypeConstructed: false, policy: 'adaptive',
  earliestWeek: 20, lastDecisionWeek: 40, pauseWeeks: 1, usefulLifeWeeks: 25,
  researchEnvelopeCents: 10000, forecastDiscount: 0.5, integrationFailureProbability: 0,
  costs: Object.fromEntries([...COST_CATEGORIES, 'weeklyMaintenance'].map(k => [k,
    { amountCents: k === 'weeklyMaintenance' ? 10 : 100, basis: 'scenario', explanation: 'Synthetic arithmetic fixture only.' }])),
  effects: { providerMinutesSaved: 2, computeAndToolCentsSaved: 0, customerReviewMinutesSaved: 0 },
  effectEvidence: { providerMinutesSaved: 'Synthetic test value, not measured research evidence.',
    computeAndToolCentsSaved: 'No reduction in this test.', customerReviewMinutesSaved: 'No reduction in this test.' },
  ...overrides
});
const syntheticFirm = () => ({
  cashCents: 111000, grossCollectionsCents: 20000, insolvent: false, assetActive: true,
  costs: { delivery: 0, business: 8000, capability: 1000, maintenance: 0, refund: 0 },
  paidCosts: { delivery: 0, business: 8000, capability: 1000, maintenance: 0, refund: 0 },
  bills: [{ id: 'history', week: 0, dueWeek: 0, category: 'capability', amountCents: 1000,
    paid: true, paidWeek: 0, reference: 'upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing' }],
  cashEvents: [{ week: 0, type: 'expense_payment', amountCents: -1000, cashAfterCents: 99000, reference: 'history' }],
  invoices: []
});
const config = { ...defaultConfig, weeks: 52 };
const expense = (f, week, category, amount, due, reference) => {
  if (amount === 0) return;
  f.costs[category] += amount;
  f.bills.push({ id: `bill-${f.bills.length}`, week, dueWeek: due, category, amountCents: amount, paid: false, reference });
};
const payBills = (f, week) => {
  for (const b of f.bills.filter(b => !b.paid && b.dueWeek <= week)) {
    if (f.cashCents < b.amountCents) { f.insolvent = true; continue; }
    f.cashCents -= b.amountCents; f.paidCosts[b.category] += b.amountCents;
    b.paid = true; b.paidWeek = week;
    f.cashEvents.push({ week, type: 'expense_payment', amountCents: -b.amountCents, reference: b.id });
  }
};
const unitCost = (c, active) => Math.round((c.commonResidualMinutes +
  (active ? c.assetResidualMinutes : c.ordinaryFinalizationMinutes)) * c.hourlyProviderCents / 60) + c.computeAndToolCents;
const tick = (hooks, f, week, extra = {}) => {
  hooks.activate({ firm: f, week });
  hooks.beforeMarket({ config, firm: f, week, seed: 17, priorAccepted: 32, expense, payBills, unitCost, ...extra });
};

test('frozen upstream source identity is intact', () => {
  const source = readFileSync(new URL('../upstream/src/market.mjs', import.meta.url));
  assert.equal(createHash('sha256').update(source).digest('hex'),
    '52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27');
});

test('neutral patch gives byte-identical JSON on finite zero-demand software controls', () => {
  for (const supplied of [
    { weeks: 8, buyers: 1, arrivalProbability: 0 },
    { weeks: 12, buyers: 1, arrivalProbability: 0, expenseDelayWeeks: 3, paymentDelayWeeks: 6 },
    { weeks: 8, buyers: 1, arrivalProbability: 0, initialCashCents: 0 },
    { weeks: 8, buyers: 1, arrivalProbability: 0, investmentCostBasis: 'adoption-only' }
  ]) for (const firstArm of ['A', 'B', 'C']) {
    assert.equal(JSON.stringify(patched(supplied, 17, firstArm)), JSON.stringify(legacy(supplied, 17, firstArm)));
  }
});

test('unpriced prior discovery remains unknown and blocks a claim', () => {
  const p = syntheticProfile(); p.costs.priorDiscovery = {
    amountCents: null, basis: 'unknown', explanation: 'Inherited discovery tariff not observed.'
  };
  const hooks = createSecondHooks(p), f = syntheticFirm();
  hooks.initialize({ config }); tick(hooks, f, 20);
  const result = hooks.finalize({ firm: f, jobs: [], config });
  assert.equal(result.invested, false); assert.equal(result.completeCostProfilePriced, false);
  assert.deepEqual(result.unknownCostCategories, ['priorDiscovery']);
  assert.equal(f.cashCents, 111000);
});

test('missing cost categories and zero-filled unknowns are rejected', () => {
  const p = syntheticProfile(); delete p.costs.verification;
  assert.throws(() => validateProfile(p), /Cost explanation/);
  const q = syntheticProfile(); q.costs.priorDiscovery.basis = 'unknown';
  assert.throws(() => validateProfile(q), /zero-filled/);
});

test('opening seed and future invoices cannot fund second construction', () => {
  const f = syntheticFirm(); f.grossCollectionsCents = 0; f.invoices = [{ amountCents: 999999, status: 'pending' }];
  assert.equal(generatedResources(f, config).availableCents, 0);
  const hooks = createSecondHooks(syntheticProfile()); hooks.initialize({ config }); tick(hooks, f, 20);
  assert.equal(hooks.finalize({ firm: f, jobs: [], config }).invested, false);
  assert.equal(f.cashCents, 111000);
});

test('unpaid obligations and one reserve constrain generated funds', () => {
  const f = syntheticFirm(); f.cashCents = 20500;
  f.bills.push({ id: 'unpaid', amountCents: 300, paid: false, category: 'delivery', week: 19 });
  f.costs.delivery += 300;
  assert.equal(generatedResources(f, config).availableCents, 200);
  f.bills[0].paid = false;
  assert.equal(generatedResources(f, config).seedPaidOpeningHistoryCents, 0);
  assert.equal(generatedResources(f, config).availableCents, 0);
});

test('zero evidenced benefit preserves no-investment decision and charges search once', () => {
  const p = syntheticProfile({ effects: { providerMinutesSaved: 0, computeAndToolCentsSaved: 0, customerReviewMinutesSaved: 0 } });
  const hooks = createSecondHooks(p), f = syntheticFirm(); hooks.initialize({ config });
  tick(hooks, f, 20); tick(hooks, f, 21);
  const result = hooks.finalize({ firm: f, jobs: [], config });
  assert.equal(result.invested, false); assert.equal(result.completeRealizedSecondCostsCents, 300);
  assert.equal(f.cashCents, 110700); assert.equal(f.bills.filter(b => b.reference.startsWith('second:')).length, 3);
});

test('completed research replay exposes an affordable but unjustified full-cost attempt', () => {
  const p = syntheticProfile({ policy: 'completed-research-replay', researchPrototypeConstructed: true,
    earliestWeek: 20, lastDecisionWeek: 20,
    effects: { providerMinutesSaved: 0, computeAndToolCentsSaved: 0, customerReviewMinutesSaved: 0 } });
  const hooks = createSecondHooks(p), f = syntheticFirm(); hooks.initialize({ config }); tick(hooks, f, 20);
  const result = hooks.finalize({ firm: f, jobs: [], config });
  assert.equal(result.modeledConstructionAttempted, true); assert.equal(result.invested, false);
  assert.equal(result.financiallyAdmitted, false); assert.equal(result.completeRealizedSecondCostsCents, 800);
  assert.equal(result.outsideEnterprisePrototypeCostCents, 0);
  assert.equal(result.decisions[0].action, 'operating-funded-unqualified-research-attempt');
  assert.equal(f.cashCents, 110200);
});

test('unaffordable completed research stays explicit outside the finite enterprise', () => {
  const p = syntheticProfile({ policy: 'completed-research-replay', researchPrototypeConstructed: true,
    earliestWeek: 20, lastDecisionWeek: 20 });
  const hooks = createSecondHooks(p), f = syntheticFirm();
  f.grossCollectionsCents = 0;
  hooks.initialize({ config }); tick(hooks, f, 20); tick(hooks, f, 21);
  const result = hooks.finalize({ firm: f, jobs: [], config });
  assert.equal(result.modeledConstructionAttempted, false); assert.equal(result.invested, false);
  assert.equal(result.completeRealizedSecondCostsCents, 0); assert.equal(result.outsideEnterprisePrototypeCostCents, 800);
  assert.equal(f.cashCents, 111000); assert.equal(result.decisions.length, 1);
  assert.equal(result.decisions[0].action, 'completed-prototype-not-financed');
});

test('adaptive decline does not erase a completed prototype construction cost', () => {
  const p = syntheticProfile({ researchPrototypeConstructed: true,
    effects: { providerMinutesSaved: 0, computeAndToolCentsSaved: 0, customerReviewMinutesSaved: 0 } });
  const hooks = createSecondHooks(p), f = syntheticFirm(); hooks.initialize({ config }); tick(hooks, f, 20);
  const result = hooks.finalize({ firm: f, jobs: [], config });
  assert.equal(result.invested, false); assert.equal(result.completeRealizedSecondCostsCents, 300);
  assert.equal(result.outsideEnterprisePrototypeCostCents, 500);
  assert.equal(result.completeRealizedSecondCostsCents + result.outsideEnterprisePrototypeCostCents, 800);
});

test('paid construction cannot activate early and certain failure is rejected', () => {
  for (const failure of [0, 1]) {
    const p = syntheticProfile({ integrationFailureProbability: failure });
    const hooks = createSecondHooks(p), f = syntheticFirm(); hooks.initialize({ config }); tick(hooks, f, 20);
    const before = hooks.finalize({ firm: f, jobs: [], config });
    if (failure === 1) {
      assert.equal(before.invested, false, 'Certain failure must fail the prospective repayment gate');
      continue;
    }
    assert.equal(before.invested, true); assert.equal(before.completeRealizedSecondCostsCents, 800);
    assert.equal(f.secondAssetPending, true); assert.equal(hooks.effectiveConfig(config).commonResidualMinutes, 2);
    const jobs = [{ week: 21, provider: 'enterprise', qualityGood: true }];
    tick(hooks, f, 21); hooks.afterProduction({ week: 21, jobs });
    const after = hooks.finalize({ firm: f, jobs, config });
    assert.equal(f.secondAssetPending, false); assert.equal(hooks.effectiveConfig(config).commonResidualMinutes, 0);
    assert.equal(after.completeRealizedSecondCostsCents, 810); assert.equal(after.actualAssetInvocationsInModel, 1);
    assert.equal(after.directAvoidedDeliveryCostCents, 218);
  }
});

test('an adverse realized integration retains its construction charge and pause', () => {
  const p = syntheticProfile({ integrationFailureProbability: 0.1 });
  let seed = 1;
  while (randomDraw(seed, 'second-asset-integration-failure', 20) >= 0.1) seed++;
  const hooks = createSecondHooks(p), f = syntheticFirm(); hooks.initialize({ config });
  tick(hooks, f, 20, { seed });
  assert.equal(f.secondAssetPending, true);
  tick(hooks, f, 21, { seed });
  const result = hooks.finalize({ firm: f, jobs: [], config });
  assert.equal(result.invested, true); assert.equal(result.failedIntegration, true);
  assert.equal(result.completeRealizedSecondCostsCents, 800);
  assert.equal(result.actualAssetInvocationsInModel, 0);
  assert.equal(hooks.effectiveConfig(config).commonResidualMinutes, 2);
  assert.equal(result.directCostRepayment, false);
});

test('useful-life expiration stops benefits and upkeep', () => {
  const p = syntheticProfile({ usefulLifeWeeks: 2 });
  for (const key of COST_CATEGORIES) p.costs[key].amountCents = 0;
  p.costs.weeklyMaintenance.amountCents = 1;
  const hooks = createSecondHooks(p), f = syntheticFirm(); hooks.initialize({ config });
  tick(hooks, f, 20); tick(hooks, f, 21); tick(hooks, f, 22); tick(hooks, f, 23);
  const result = hooks.finalize({ firm: f, jobs: [], config });
  assert.equal(result.invested, true); assert.equal(result.maintenanceAccruedCents, 2);
  assert.equal(hooks.effectiveConfig(config).commonResidualMinutes, 2);
});

test('future horizon extension and unsupported cost/effect fields are rejected', () => {
  assert.throws(() => createSecondHooks(syntheticProfile()).initialize({ config: { ...config, weeks: 104 } }), /52-week/);
  const p = syntheticProfile(); p.costs.hiddenSubsidy = { amountCents: 500, basis: 'scenario', explanation: 'Must fail' };
  assert.throws(() => validateProfile(p), /silently omitted/);
  const q = syntheticProfile(); q.effects.extraRevenue = 500;
  assert.throws(() => validateProfile(q), /Unsupported economic effect/);
});

test('second time saving cannot spend the initial asset benefit again', () => {
  const hooks = createSecondHooks(syntheticProfile({ effects: {
    providerMinutesSaved: 10, computeAndToolCentsSaved: 0, customerReviewMinutesSaved: 0
  } }));
  assert.throws(() => hooks.initialize({ config }), /surviving provider burden/);
});

test('signed measured regressions increase costs instead of being clipped to zero', () => {
  const p = syntheticProfile({ policy: 'completed-research-replay', researchPrototypeConstructed: true,
    earliestWeek: 20, lastDecisionWeek: 20, unroundedComputeSavingsMicrocentsPerJob: -1_250_000,
    effects: { providerMinutesSaved: -0.5, computeAndToolCentsSaved: -1, customerReviewMinutesSaved: -1 } });
  const hooks = createSecondHooks(p), f = syntheticFirm(); hooks.initialize({ config });
  tick(hooks, f, 20); tick(hooks, f, 21);
  const jobs = [{ week: 21, provider: 'enterprise', qualityGood: true },
    { week: 21, provider: 'enterprise', qualityGood: false }];
  hooks.afterProduction({ week: 21, jobs });
  const effective = hooks.effectiveConfig(config), result = hooks.finalize({ firm: f, jobs, config });
  assert.equal(effective.commonResidualMinutes, 2.5); assert.equal(effective.computeAndToolCents, 26);
  assert.equal(effective.customerReviewMinutes, 9); assert.equal(result.directAvoidedDeliveryCostCents, -137);
  assert.equal(result.invested, false); assert.equal(result.directCostRepayment, false);
  assert.equal(result.subcentComputeEffect.netSavingsNotRepresentedByCentLedgerMicrocents, -1125000);
});

test('all new arms retain the same first-asset history on a zero-demand control', () => {
  const p = syntheticProfile({ earliestWeek: 4, lastDecisionWeek: 7 });
  const result = pairedContinuation({ weeks: 8, buyers: 1, arrivalProbability: 0 }, 17, { B: p, C: p });
  assert.equal(result.commonPrefixExact, true);
  assert.deepEqual(result.arms.A.histories, result.arms.B.histories);
  assert.deepEqual(result.arms.B.summary, result.arms.C.summary);
  assert.equal(result.qualification.B.conditionalModeledFinancialGatePassed, false);
});
