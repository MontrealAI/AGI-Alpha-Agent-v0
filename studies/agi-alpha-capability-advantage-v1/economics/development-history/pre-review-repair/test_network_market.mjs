// Synthetic software controls only; these inputs are not production calibration.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { validateCalibration, balancedPanel, pairedNetwork, simulateNetwork, COST_SCHEDULES,
  unknownCostBoundary, buildCost } from './network_market.mjs';
import { generatedResources } from './inherited/continuation.mjs';

const fixture = (ordinary = true) => ({schema: 'capability-advantage-calibration/v1',
  basis: 'EXECUTED_RESEARCH_COHORT_ONLY', actual_customer_collections_cents: 0, actual_total_cost_cents: null,
  families: [1, 2, 3].map(i => ({id: `G${i}`, title: 'SYNTHETIC SOFTWARE CONTROL', prerequisites: i > 1 ? [`G${i - 1}`] : [],
    asset_sha256: String(i).repeat(64), acceptance_sha256: 'a'.repeat(64), tested: true,
    resources: {construction_seconds: 30, failed_candidate_seconds: 10, validation_seconds: 5,
      integration_seconds: 5, conventional_construction_seconds: 3600, independent_reconstruction_seconds: 3600},
    trials: ['standard', 'hard'].map(difficulty => ({task_id: `CONTROL-${i}-${difficulty}`, difficulty,
      before: {accepted: ordinary, cpu_seconds: 2}, reconstructed: {accepted: true, cpu_seconds: 1},
      shared: {accepted: true, cpu_seconds: 1}, conventional: {accepted: true, cpu_seconds: 1}}))})),
  retrieval: {registry_cpu_seconds: 0, graph_cpu_seconds: 0, registry_build_seconds: 0, graph_build_seconds: 0}});
const condition = {...balancedPanel()[0], network_size: 4, demand_multiplier: 1, initial_overlap: 0.2,
  copying_delay_weeks: 4, integration_cents: 0, diverse: true, harder_mix: false,
  reconstruction_factor: 1, acquisition_failure_probability: 0, useful_life_weeks: 26,
  stale_probability: 0, choice_model: 'logit'};

test('the exact frozen upstream prefix is preserved', () => {
  const dir = new URL('./', import.meta.url);
  const input = readFileSync(new URL('inherited/upstream/src/market.mjs', dir));
  const output = readFileSync(new URL('inherited/upstream/src/market-adapter-primitives.mjs', dir));
  assert.deepEqual(output.subarray(0, input.length), input);
  assert.equal(createHash('sha256').update(input).digest('hex'),
    '52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27');
});

test('the structural panel has fixed, balanced factor margins', () => {
  const panel = balancedPanel();
  assert.equal(panel.length, 48);
  for (const key of Object.keys(panel[0]).filter(k => k !== 'id')) {
    const levels = [...new Set(panel.map(r => r[key]))];
    for (const level of levels) assert.equal(panel.filter(r => r[key] === level).length, 48 / levels.length);
  }
});

test('actual unknown costs cannot promote an investment', () => {
  const boundary = unknownCostBoundary();
  assert.equal(boundary.affirmative_investment, false);
  assert.equal(boundary.actual_total_cost_cents, null);
  assert.equal(boundary.actual_collections_cents, 0);
});

test('calibration rejects missing evidence, unknown timing and fabricated actual receipts', () => {
  const a = fixture(); a.families[0].asset_sha256 = 'fake'; assert.throws(() => validateCalibration(a));
  const b = fixture(); b.families[1].resources.construction_seconds = null; assert.throws(() => validateCalibration(b));
  const c = fixture(); c.actual_customer_collections_cents = 1; assert.throws(() => validateCalibration(c));
  const d = fixture(); d.families[1].trials[0].shared.accepted = null; assert.throws(() => validateCalibration(d));
});

test('seed cash alone never becomes operating-generated resources', () => {
  const firm = {cashCents: 100000, bills: [], costs: {capability: 0}, grossCollectionsCents: 0, cashEvents: []};
  const funds = generatedResources(firm, {reserveCents: 20000, initialCashCents: 100000,
    investmentCostBasis: 'full-history', historicalCostTiming: 'opening'});
  assert.equal(funds.availableCents, 0);
  assert.equal(funds.cashBoundCents, 80000);
});

test('registry and graph are behaviorally identical when source and overhead are identical', () => {
  const run = pairedNetwork(fixture(), condition, COST_SCHEDULES[0], 996001);
  assert.deepEqual(run.arms.B.summary, run.arms.C.summary);
  assert.equal(run.differences.C_minus_B_cents, 0);
  assert.equal(run.arms.C.actual_full_history_return_cents, null);
});

test('complete ledgers reconcile with no demand and do not invent receipts', () => {
  const run = simulateNetwork(fixture(), {...condition, demand_multiplier: 0}, COST_SCHEDULES[0], 996002, 'B');
  assert.equal(run.summary.accepted, 0);
  assert.equal(run.summary.collected_cents, 0);
  assert.equal(run.actual_collections_cents, 0);
  assert.equal(run.summary.cash_cents, 100000 - run.summary.accrued_costs_cents);
  assert.equal(Object.keys(run.assets).length, 0);
  assert.equal(run.canonical.cash.summary.observed.revenue, 0);
});

test('shared indexing construction is charged once, not per generation', () => {
  const calibration = fixture(); calibration.retrieval.graph_build_seconds = 3600;
  const first = buildCost(calibration.families[0], COST_SCHEDULES[1], 'C', condition, calibration);
  const next = buildCost(calibration.families[1], COST_SCHEDULES[1], 'C', condition, calibration);
  assert.equal(first.categories.construction - next.categories.construction, COST_SCHEDULES[1].resource_hourly_cents);
});

test('competent ordinary tools prevent falsely credited scarce-capability construction', () => {
  const run = simulateNetwork(fixture(true), condition, COST_SCHEDULES[0], 996003, 'C');
  assert.equal(Object.keys(run.assets).length, 0);
  assert(run.histories.decisions.every(d => d.forecast_net_cents <= 0));
});

test('failed work cannot create invoices or collections', () => {
  const calibration = fixture(false);
  for (const family of calibration.families) for (const trial of family.trials)
    for (const method of ['reconstructed', 'shared', 'conventional']) trial[method].accepted = false;
  const run = simulateNetwork(calibration, condition, COST_SCHEDULES[0], 996004, 'B');
  assert.equal(run.summary.accepted, 0);
  assert.equal(run.histories.invoices.length, 0);
  assert.equal(run.summary.collected_cents, 0);
});

test('finite funding, preserved learning and internal-transfer conservation hold in a constructed positive control', () => {
  const calibration = fixture(false);
  const schedule = {...COST_SCHEDULES[0], resource_hourly_cents: 10000,
    model_tools_cents_per_build: 0, audit_minutes_per_build: 0, residual_minutes_per_job: 0,
    discovery_minutes_per_build: 0, common_initial_cents: 0, common_weekly_cents: 0,
    historical_research_cents: 0, maintenance_cents_week: 0, revalidation_cents: 0};
  const run = simulateNetwork(calibration, {...condition, network_size: 16, demand_multiplier: 4,
    initial_overlap: 0, choice_model: 'deterministic', copying_delay_weeks: 12, posted_price_cents: 2000}, schedule, 996005, 'C');
  assert(run.summary.accepted > 0);
  assert(run.histories.balances.every(b => b.cash_cents >= 0));
  assert(run.histories.decisions.filter(d => d.action === 'construct').every(d => d.available_cents >= d.fixed_cost.total_cents));
  assert(run.histories.contributionAllocations.every(r => r.internal_transfer_net_enterprise_value_cents === 0));
  assert.equal(run.actual_collections_cents, 0);
  const transfers = run.histories.transfers;
  assert.equal(new Set(transfers.filter(t => t.accepted).map(t => `${t.agent}:${t.family}`)).size,
    transfers.filter(t => t.accepted).length);
});
