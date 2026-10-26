// Synthetic software controls only; these inputs are not production calibration.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { PassThrough, Writable } from 'node:stream';
import { validateCalibration, balancedPanel, pairedNetwork, simulateNetwork, COST_SCHEDULES,
  unknownCostBoundary, buildCost, ownCost, quoteRoute, alternativeStatus, directTransferValue,
  qualifyLaterBundle } from './network_market.mjs';
import { generatedResources } from './inherited/continuation.mjs';
import { streamFinalizer } from './run_market.mjs';

const resource = (seconds, basis = 'measured_elapsed_allocation') => ({seconds, basis, reference: 'SYNTHETIC SOFTWARE CONTROL'});
const fixture = (ordinary = true) => ({schema: 'capability-advantage-calibration/v2',
  basis: 'EXECUTED_RESEARCH_COHORT_ONLY', actual_customer_collections_cents: 0, actual_total_cost_cents: null,
  timing_scope: 'complete_stage_no_additional_retrieval', resources_are_exclusive_or_explicitly_included: true,
  families: [1, 2, 3].map(i => ({id: `G${i}`, title: 'SYNTHETIC SOFTWARE CONTROL', prerequisites: i > 1 ? [`G${i - 1}`] : [],
    arm_assets: Object.fromEntries(['A','B','C','D'].map(a => [a, {sha256: String(i).repeat(64), acceptance_sha256: 'a'.repeat(64)}])),
    tested: true,
    resources: {by_arm: Object.fromEntries(['A','B','C','D'].map(a => [a, {
      construction: resource(['A','D'].includes(a) ? 3600 : 30), failedCandidates: resource(10),
      validation: resource(5), integration: resource(5)}]))},
    trials: ['standard', 'hard'].map(difficulty => ({task_id: `CONTROL-${i}-${difficulty}`,
      chain_id: `CONTROL-${difficulty}`, difficulty, before: {accepted: ordinary, cpu_seconds: 2},
      methods: Object.fromEntries(['A','B','C','D'].map(a => [a, {accepted: true, cpu_seconds: 1, timing_scope: 'complete_stage'}]))}))})),
  retrieval: {registry_build: resource(0), graph_build: resource(0)}});
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
  const a = fixture(); a.families[0].arm_assets.A.sha256 = 'fake'; assert.throws(() => validateCalibration(a));
  const b = fixture(); b.families[1].resources.by_arm.B.construction.seconds = null; assert.throws(() => validateCalibration(b));
  const c = fixture(); c.actual_customer_collections_cents = 1; assert.throws(() => validateCalibration(c));
  const d = fixture(); d.families[1].trials[0].methods.B.accepted = null; assert.throws(() => validateCalibration(d));
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
  const calibration = fixture(); calibration.retrieval.graph_build.seconds = 3600;
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
    for (const method of ['A','B','C','D']) trial.methods[method].accepted = false;
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

test('independent alternatives pay every complete construction category', () => {
  const calibration = fixture(false), family = calibration.families[0], schedule = COST_SCHEDULES[1];
  assert.equal(ownCost(family, schedule, condition), 4172);
  assert.equal(ownCost(family, schedule, condition), buildCost(family, schedule, 'A', condition, calibration).total_cents);
  const record = buildCost(family, schedule, 'A', condition, calibration);
  assert(record.categories.discovery > 0 && record.categories.failedCandidates > 0 &&
    record.categories.integration > 0 && record.categories.residualAttention > 0);
});

test('A is charged its own author interval rather than D interval', () => {
  const calibration = fixture();
  for (const family of calibration.families) {
    family.resources.by_arm.A.construction.seconds = 225.039 / 3;
    family.resources.by_arm.D.construction.seconds = 303.680 / 3;
  }
  const schedule = COST_SCHEDULES[2];
  const run = simulateNetwork(calibration, {...condition, demand_multiplier: 0}, schedule, 996006, 'A');
  const expected = calibration.families.reduce((s, f) => s + buildCost(f, schedule, 'A', condition, calibration).total_cents, 0);
  const wrong = calibration.families.reduce((s, f) => s + buildCost(f, schedule, 'D', condition, calibration).total_cents, 0);
  assert.equal(run.summary.completed_prototype_cost_cents, expected);
  assert.notEqual(expected, wrong);
});

test('shared quote anticipates acquisition and stale-skill risk', () => {
  const calibration = fixture(false), family = calibration.families[0], trial = family.trials[0];
  const agent = {own: new Set(), conventional: new Set(), acquired: new Set()};
  const risks = {...condition, integration_cents: 0, acquisition_failure_probability: 0.2, stale_probability: 0.1};
  const quote = quoteRoute('C', agent, family, trial, {assets: {G1: {active: true}}}, COST_SCHEDULES[1], risks, calibration);
  assert.equal(quote.id, 'validated-acquisition');
  assert(Math.abs(quote.quality - 0.72) < 1e-12);
  assert(Math.abs(quote.expectedCostPerAccepted - (quote.fixed + quote.forecastUnit) / 0.72) < 1e-12);
  agent.acquired.add('G1');
  const reused = quoteRoute('C', agent, family, trial, {assets: {G1: {active: true}}}, COST_SCHEDULES[1], risks, calibration);
  assert.equal(reused.quality, 0.9);
});

test('failed transfers and unknown alternatives retain all incurred costs', () => {
  assert.equal(directTransferValue(false, 1000, 125), -125);
  assert.equal(directTransferValue(true, null, 125), -125);
  assert.equal(directTransferValue(true, 1000, 125), 875);
});

test('a profitable later bundle returns no individual generation success label', () => {
  const run = {completed_prototype_costs: [{family: 'G2', total_cents: 100}, {family: 'G3', total_cents: 100}],
    assets: {G2: {cost: 100, avoided: 350, upkeep: 0, uses: 3, failed: false, funding: 'operating-generated'},
      G3: {cost: 100, avoided: 0, upkeep: 0, uses: 1, failed: false, funding: 'operating-generated'}}};
  const control = {incremental_project_profit_cents: 150, incremental_unrounded_compute_project_profit_cents: 149.8};
  const result = qualifyLaterBundle(run, control);
  assert.equal(result.qualifies, true);
  assert.equal(result.scope, 'G2_G3_LATER_INVESTMENT_BUNDLE_ONLY');
  assert.equal(result.individual_generation_qualification, 'NOT_ESTABLISHED_BY_THIS_CONTROL');
  assert(!Object.hasOwn(result, 'qualifying_generation_ids'));
  delete run.assets.G3;
  assert.equal(qualifyLaterBundle(run, control).qualifies, false);
});

test('unknown raw prior capability is never relabeled unsupported', () => {
  const calibration = fixture(false), family = calibration.families[0];
  for (const trial of family.trials) {
    trial.before = {accepted: null, cpu_seconds: null, basis: 'NOT_RUN'};
    trial.methods.A.accepted = false; trial.methods.D.accepted = false;
  }
  assert.equal(alternativeStatus(family, family.trials[0], null), 'RAW_PRIOR_NOT_RUN_NO_SUCCESSFUL_MEASURED_ALTERNATIVE');
  assert.equal(alternativeStatus(family, family.trials[0], 100), 'MEASURED_RECONSTRUCTABLE_OR_ORDINARY_ALTERNATIVE');
  for (const trial of family.trials) trial.before = {accepted: false, cpu_seconds: 1};
  assert.equal(alternativeStatus(family, family.trials[0], null), 'ALL_MEASURED_ALTERNATIVES_FAILED_IN_THIS_FINITE_STRATUM');
});

test('B and C have distinct complete timing and acceptance with no extra retrieval bill', () => {
  const calibration = fixture(false), family = calibration.families[0], trial = family.trials[0];
  trial.methods.B.cpu_seconds = 1; trial.methods.C.cpu_seconds = 3;
  const agent = {own: new Set(), conventional: new Set(), acquired: new Set(['G1'])};
  const state = {assets: {G1: {active: true}}};
  const b = quoteRoute('B', agent, family, trial, state, COST_SCHEDULES[1], condition, calibration);
  const c = quoteRoute('C', agent, family, trial, state, COST_SCHEDULES[1], condition, calibration);
  assert(Math.abs(c.unit - b.unit - 2 * COST_SCHEDULES[1].compute_hourly_cents / 3600) < 1e-12);
  trial.methods.C.accepted = false;
  const failedC = quoteRoute('C', agent, family, trial, state, COST_SCHEDULES[1], condition, calibration);
  assert.notEqual(failedC.method, 'C');
  calibration.retrieval.graph_cpu_seconds = 100;
  assert.throws(() => validateCalibration(calibration));
});

test('same stream completion can be awaited after a post-finish failure without hanging', async () => {
  const input = new PassThrough(), output = new Writable({write(_chunk, _encoding, callback) { callback(); }});
  const finish = streamFinalizer(input, output);
  input.pipe(output); input.write('preserved partial evidence');
  await finish();
  let caught = false;
  try { throw Error('synthetic failure after finish'); } catch { caught = true; await finish(); }
  assert.equal(caught, true); assert.equal(output.writableFinished, true);
});

test('subcent computation is charged through a cumulative carry and remains visible', () => {
  const run = simulateNetwork(fixture(), {...condition, demand_multiplier: 4, posted_price_cents: 2000},
    COST_SCHEDULES[0], 996007, 'A');
  const raw = run.histories.jobs.reduce((s, j) => s + j.compute_unrounded_cents, 0);
  const charged = run.histories.jobs.reduce((s, j) => s + j.compute_charged_cents, 0);
  assert(raw > 0); assert.equal(charged, Math.ceil(raw));
  assert(charged - raw >= 0 && charged - raw < 1);
  assert.equal(run.summary.project_inclusive_unrounded_compute_profit_cents,
    run.summary.project_inclusive_profit_cents - run.summary.subcent_compute_rounding_residual_cents);
});

test('declared root resource proxies stay labeled and duplicated measured intervals are refused', () => {
  const calibration = fixture();
  calibration.families[0].resources.by_arm.B.construction = resource(1000, 'scenario_resource_proxy');
  assert.equal(validateCalibration(calibration).families[0].resources.by_arm.B.construction.basis, 'scenario_resource_proxy');
  calibration.resource_allocation = [{arm: 'D', category: 'construction', total_seconds: 3600,
    allocation_basis: 'One interval, not three duplicated copies'}];
  assert.throws(() => validateCalibration(calibration));
  for (const family of calibration.families) family.resources.by_arm.D.construction.seconds = 1200;
  assert.doesNotThrow(() => validateCalibration(calibration));
});
