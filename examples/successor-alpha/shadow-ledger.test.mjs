// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {SCHEMA, appendEvent, calculateInvestment, planMission, replayLedger} from './shadow-ledger.mjs';

const inputs = overrides => ({missionId: 'fresh-1', acceptance: 'accepted', totalCollectedCents: 8000, priceAssumptionCents: 10000,
  totalOperatingCostCents: 2500, operatingCostsComplete: true, capabilityCostCents: 1000,
  reserveCents: 500, obligationCents: 200, reinvestmentBps: 5000,
  humanMinutes: 5, humanHourlyCents: 6000, traditionalMinutes: 120, ...overrides});
const financial = (id, type, category, amountMinor, basis = 'observed', missionId = 'fresh-1') =>
  ({id, type, category, amountMinor, basis, missionId, reference: 'Source-bound accounting assertion'});

test('assumed price stays separate from collected money; full arithmetic reconciles', () => {
  const result = planMission(inputs());
  assert.equal(result.summary.observed.revenue, 8000);
  assert.equal(result.summary.observed.fullCost, null);
  assert.equal(result.summary.observed.availableSurplus, null);
  assert.deepEqual(result.summary.scenario, {revenue: 10000, fullCost: 3500, operatingMargin: 6500,
    reserve: 500, unpaidObligations: 200, afterReserves: 5800, availableSurplus: 5800, eligibleInvestment: 2900});
  assert.deepEqual(result.comparison, {traditionalCost: 12000, humanAttentionCost: 500,
    customerPricePlusAttention: 10500, providerFullCost: 3500, customerSavings: 1500,
    breakEvenTraditionalMinutes: 105,
    scope: 'Conditional equal-acceptance scenario using supplied wage and duration assumptions; remaining customer attention is distinct from provider costs.'});
  assert.match(result.summary.scope, /not authenticated receipts/);
});

test('complete observed account remains distinct from modeled customer price', () => {
  const {summary} = planMission(inputs({costBasis: 'observed'}));
  assert.equal(summary.observed.operatingMargin, 4500);
  assert.equal(summary.observed.availableSurplus, 3800);
  assert.equal(summary.observed.eligibleInvestment, 1900);
  assert.equal(summary.scenario.eligibleInvestment, 2900);
});

test('unknowns never become zero; explicit aggregate completeness is required', () => {
  for (const overrides of [{operatingCostsComplete: false}, {totalOperatingCostCents: null},
    {capabilityCostCents: null}, {reserveCents: null}, {obligationCents: null}]) {
    const {summary} = planMission(inputs(overrides));
    assert.equal(summary.scenario.availableSurplus, null);
    assert.equal(summary.scenario.eligibleInvestment, null);
  }
  const {summary, comparison} = planMission();
  assert.equal(summary.scenario.fullCost, null);
  assert.equal(comparison.traditionalCost, null);
  assert.equal(comparison.customerPricePlusAttention, null);
});

test('zero reinvestment and explicit zero costs are valid; negative margin is preserved', () => {
  const zero = planMission(inputs({reinvestmentBps: 0})).summary;
  assert.equal(zero.scenario.eligibleInvestment, 0);
  const loss = planMission(inputs({priceAssumptionCents: 2000})).summary;
  assert.equal(loss.scenario.operatingMargin, -1500);
  assert.equal(loss.scenario.afterReserves, -2200);
  assert.equal(loss.scenario.availableSurplus, 0);
  assert.equal(loss.scenario.eligibleInvestment, 0);
  const free = planMission(inputs({totalOperatingCostCents: 0, capabilityCostCents: 0,
    reserveCents: 0, obligationCents: 0})).summary;
  assert.equal(free.scenario.fullCost, 0);
});

test('identical event IDs are idempotent; conflicting reuse is refused atomically', () => {
  const {ledger} = planMission(inputs());
  const same = appendEvent(ledger, {...ledger.events[0]});
  assert.deepEqual(same, ledger);
  assert.equal(ledger.events.length, 9);
  assert.throws(() => appendEvent(ledger, {...ledger.events[0], reference: 'Conflict'}), /Conflicting duplicate/);
  assert.deepEqual(replayLedger({...ledger, events: [...ledger.events, ledger.events[0]]}), replayLedger(ledger));
  assert.throws(() => replayLedger({...ledger, events: [...ledger.events, {...ledger.events[0], reference: 'Conflict'}]}), /Conflicting duplicate/);
});

test('deterministic replay ignores order, returns owned values, and retains evidence', () => {
  const {ledger} = planMission(inputs());
  assert.deepEqual(replayLedger({...ledger, events: [...ledger.events].reverse()}), replayLedger(ledger));
  const row = {id: 'cap-reject', type: 'capability', missionId: 'fresh-1', capabilityId: 'repair-v2',
    action: 'rejected', reference: 'Independent regression failure: preserve incumbent'};
  const next = appendEvent(ledger, row);
  row.action = 'admitted';
  assert.equal(replayLedger(next).missions[0].capabilityEvents[0].action, 'rejected');
  assert.equal(replayLedger(next).scenario.fullCost, 3500);
});

test('failed attempts and maintenance costs remain in total costs', () => {
  let {ledger} = planMission(inputs());
  ledger = appendEvent(ledger, financial('failed-attempt', 'cost', 'delivery', 400));
  ledger = appendEvent(ledger, financial('stale-repair', 'cost', 'maintenance', 300));
  const result = replayLedger(ledger, {reinvestmentBps: 5000});
  assert.equal(result.scenario.fullCost, 4200);
  assert.equal(result.scenario.availableSurplus, 5100);
});

test('failed construction is not erased and another mission cannot hide losses', () => {
  const a = planMission(inputs({costBasis: 'observed', priceAssumptionCents: null})).ledger;
  const b = planMission(inputs({missionId: 'fresh-2', acceptance: 'rejected', totalCollectedCents: 0,
    priceAssumptionCents: 0, totalOperatingCostCents: 7000, capabilityCostCents: 1000,
    reserveCents: 0, obligationCents: 0, costBasis: 'observed'})).ledger;
  const result = replayLedger({...a, events: [...a.events, ...b.events]}, {reinvestmentBps: 10000});
  assert.equal(result.observed.operatingMargin, -3500);
  assert.equal(result.observed.availableSurplus, 0);
  assert.equal(result.observed.eligibleInvestment, 0);
});

test('unknown/rejected commercial acceptance cannot make collected money investable', () => {
  for (const acceptance of ['unknown', 'rejected']) {
    const {summary} = planMission(inputs({acceptance, costBasis: 'observed'}));
    assert.equal(summary.observed.availableSurplus, null);
    assert.equal(summary.scenario.eligibleInvestment, null);
    assert.equal(summary.missions[0].observed.availableSurplus, acceptance === 'unknown' ? null : 0);
  }
});

test('incomplete observed proceeds do not erase a price-only planning scenario', () => {
  const {summary} = planMission(inputs({totalCollectedCents: null}));
  assert.equal(summary.observed.revenue, null);
  assert.equal(summary.scenario.revenue, 10000);
  const actualOnly = planMission(inputs({priceAssumptionCents: null})).summary;
  assert.equal(actualOnly.scenario.revenue, 8000);
});

test('malformed, mixed-currency and unsupported accounting refuses', () => {
  const {ledger} = planMission(inputs());
  for (const event of [financial('bad', 'revenue', 'collected', 1, 'assumed'),
    financial('bad', 'revenue', 'price', 1, 'observed'), financial('bad', 'cost', 'delivery', 0, 'unknown'),
    financial('bad', 'cost', 'delivery', -1), financial('bad', 'cost', 'delivery', 0.1),
    financial('bad', 'cost', 'delivery', 1e13), financial('bad', 'cost', 'treasury', 5),
    {...financial('bad', 'cost', 'delivery', 5), token: 'AGIALPHA'},
    financial('bad', 'cost', 'delivery', 1, 'observed', 'missing')])
    assert.throws(() => appendEvent(ledger, event));
  assert.throws(() => replayLedger({...ledger, currency: 'AGIALPHA'}));
  assert.throws(() => replayLedger({...ledger, schema: 'future'}));
  assert.throws(() => replayLedger({...ledger, authority: 'spend'}));
  assert.throws(() => replayLedger({...ledger, events: Array(4097).fill(ledger.events[0])}));
  assert.throws(() => replayLedger(ledger, {reinvestmentBps: 10001}));
  assert.throws(() => replayLedger(ledger, {reinvestmentBps: 0.5}));
  assert.throws(() => planMission({totalOperatingCosts: 0}));
  assert.throws(() => planMission(inputs({operatingCostsComplete: 1})));
});

test('missing cost inventory and missing reserve remain unknown', () => {
  const ledger = {schema: SCHEMA, currency: 'USD', events: [
    {id: 'm', type: 'mission', missionId: 'fresh-1', acceptance: 'accepted', reference: 'Local assertion'},
    financial('r', 'revenue', 'collected', 20000), financial('c', 'cost', 'delivery', 50)]};
  const result = replayLedger(ledger);
  assert.equal(result.observed.fullCost, null);
  assert.equal(result.observed.reserve, null);
  assert.equal(result.observed.availableSurplus, null);
  assert.deepEqual(result.missions[0].missingCostCategories, ['business', 'capability', 'maintenance']);
});

test('large human-cost products use exact rounding and refuse unsafe totals', () => {
  assert.equal(planMission(inputs({humanMinutes: 1, humanHourlyCents: 1})).comparison.humanAttentionCost, 1);
  assert.throws(() => planMission(inputs({humanMinutes: 1e12, humanHourlyCents: 1e12})), /integer bounds/);
});

test('finite reuse includes failed construction and maintenance; short reuse fails payback', () => {
  const inputs = {constructionCostMinor: 1000, failedConstructionCostMinor: 500,
    maintenancePerReuseMinor: 100, expectedSavingPerReuseMinor: 400, remainingReuses: 4};
  const result = calculateInvestment(inputs);
  assert.equal(result.fixedCost, 1500);
  assert.equal(result.maintenanceCost, 400);
  assert.equal(result.lifetimeCost, 1900);
  assert.equal(result.grossSaving, 1600);
  assert.equal(result.netBenefit, -300);
  assert.equal(result.breakEvenReuses, 5);
  assert.equal(result.paysBackWithinHorizon, false);
  const enough = calculateInvestment({...inputs, remainingReuses: 5});
  assert.equal(enough.netBenefit, 0);
  assert.equal(enough.paysBackWithinHorizon, true);
});

test('no assumed capability success; zero and negative savings preserve construction loss', () => {
  const inputs = {constructionCostMinor: 1000, failedConstructionCostMinor: 500,
    maintenancePerReuseMinor: 100, expectedSavingPerReuseMinor: 0, remainingReuses: 4};
  const noGain = calculateInvestment(inputs);
  assert.equal(noGain.netBenefit, -1900);
  assert.equal(noGain.breakEvenReuses, null);
  assert.equal(noGain.paysBackWithinHorizon, false);
  assert.equal(calculateInvestment({...inputs, expectedSavingPerReuseMinor: -100}).netBenefit, -2300);
  assert.equal(calculateInvestment({...inputs, expectedSavingPerReuseMinor: null}).netBenefit, null);
  assert.equal(calculateInvestment({...inputs, remainingReuses: null}).paysBackWithinHorizon, null);
  assert.equal(calculateInvestment({...inputs, remainingReuses: 0}).netBenefit, -1500);
  assert.equal(calculateInvestment().netBenefit, null);
});

test('finite investment boundaries reject invalid horizons and unsafe products', () => {
  assert.throws(() => calculateInvestment({remainingReuses: 1.5}));
  assert.throws(() => calculateInvestment({remainingReuses: 1_000_001}));
  assert.throws(() => calculateInvestment({constructionCostMinor: -1}));
  assert.throws(() => calculateInvestment({automaticTransfer: true}));
  assert.throws(() => calculateInvestment({maintenancePerReuseMinor: 1e12, remainingReuses: 1e6}), /integer bounds/);
});

test('changing amount getters cannot pass validation with one value and compute another', () => {
  const {ledger} = planMission(inputs({costBasis: 'observed'}));
  const delivery = ledger.events.find(event => event.type === 'cost' && event.category === 'delivery');
  let reads = 0;
  Object.defineProperty(delivery, 'amountMinor', {enumerable: true, configurable: true,
    get() { return ++reads === 1 ? 1000 : -5000; }});
  assert.throws(() => replayLedger(ledger), /accessors/);
  assert.equal(reads, 0);
  assert.throws(() => appendEvent(ledger, financial('extra', 'cost', 'delivery', 1)), /accessors/);
  assert.equal(reads, 0);
});

test('all public APIs reject getters before reads or mutation of sibling values', () => {
  const {ledger} = planMission(inputs());
  let invoked = 0;
  const getter = value => ({enumerable: true, get() { invoked++; ledger.events[0].reference = 'Mutated'; return value; }});
  const badEvent = financial('bad-frame', 'cost', 'delivery', 10);
  Object.defineProperty(badEvent, 'amountMinor', getter(10));
  assert.throws(() => appendEvent(ledger, badEvent), /accessors/);
  const badPlan = inputs();
  Object.defineProperty(badPlan, 'totalOperatingCostCents', getter(10));
  assert.throws(() => planMission(badPlan), /accessors/);
  const badInvestment = {};
  Object.defineProperty(badInvestment, 'constructionCostMinor', getter(10));
  assert.throws(() => calculateInvestment(badInvestment), /accessors/);
  const badOptions = {};
  Object.defineProperty(badOptions, 'reinvestmentBps', getter(10000));
  assert.throws(() => replayLedger(ledger, badOptions), /accessors/);
  assert.equal(invoked, 0);
  assert.notEqual(ledger.events[0].reference, 'Mutated');
});

test('serializers, coercion and unsupported JSON cannot mutate the validated frame', () => {
  const {ledger} = planMission(inputs());
  let invoked = 0;
  const coercion = {toString() {invoked++; ledger.events[0].reference = 'Mutated'; return '0';}};
  assert.throws(() => planMission(inputs({reference: coercion})), /plain JSON data/);
  assert.throws(() => calculateInvestment({constructionCostMinor: coercion}), /plain JSON data/);
  const serializer = {...ledger, toJSON() {invoked++; return {...ledger, currency: 'CAD'};}};
  assert.throws(() => replayLedger(serializer), /serializers/);
  assert.equal(invoked, 0);
  assert.notEqual(ledger.events[0].reference, 'Mutated');
  for (const value of [NaN, Infinity, -Infinity, undefined, 1n]) {
    assert.throws(() => planMission(inputs({totalOperatingCostCents: value})));
    assert.throws(() => calculateInvestment({constructionCostMinor: value}));
  }
  const inherited = Object.create({amountMinor: 100});
  assert.throws(() => calculateInvestment(inherited), /prototype/);
  const sparse = {...ledger, events: new Array(2)};
  assert.throws(() => replayLedger(sparse), /sparse/);
  const cyclic = {}; cyclic.loop = cyclic;
  assert.throws(() => planMission(cyclic), /cycle/);
  let nested = {};
  for (let i = 0; i < 40; i++) nested = {nested};
  assert.throws(() => planMission(nested), /frame bounds/);
});
