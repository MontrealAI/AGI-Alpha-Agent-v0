// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {assessCommercial, inputTemplate} from '../src/commercial.mjs';
import {planMission} from '../canonical/shadow-ledger.mjs';

function fixture() {
  const input = inputTemplate();
  input.asset.source_sha256 = 'a'.repeat(64);
  input.actual_ledger = planMission({missionId: 'internal-work', acceptance: 'accepted',
    reference: 'Test-only supplied evidence, not customer acceptance', totalCollectedCents: 0}).ledger;
  const scenario = input.scenarios[0];
  Object.assign(scenario, {id: 'example', price_cents: 9900, accepted_jobs: 12, failed_attempts: 3,
    collection_bps: 10000, reserves_cents: 5000, opening_obligations_complete: true,
    maintenance_per_reuse_cents: 200, expected_saving_per_reuse_cents: 1000, remaining_reuses: 12});
  scenario.cost_items = scenario.cost_items.map(row => ({...row, amount_cents: row.units === 'attempt' ? 100 : 1000,
    settlement: 'paid', reference: 'Explicit arbitrary test assumption; not an estimated commercial cost.'}));
  scenario.investment_items = scenario.investment_items.map(row => ({...row, amount_cents: 1000, settlement: 'paid',
    reference: 'Explicit arbitrary test assumption.'}));
  scenario.opening_obligations = [{id: 'prior-bill', category: 'prior_obligation', amount_cents: 2000,
    settlement: 'unpaid', reference: 'Test-only previous-period bill, excluded from current-period expenses.'}];
  scenario.buyer = {hourly_cents: 6538, traditional_minutes: null, customer_minutes: 0,
    source: 'Rate-only illustration. No matched professional duration supplied.'};
  scenario.next_investment = {asset_id: 'next-test-asset', full_cost_cents: 10000,
    justification_established: false, reference: 'Next hypothetical asset has no independent economic evidence.'};
  return input;
}
const model = input => assessCommercial(input).scenarios[0];

test('all unknowns remain incomplete, with no actual receipts manufactured', () => {
  const result = assessCommercial(inputTemplate());
  assert.equal(result.actual.observed_collections_cents, null);
  assert.equal(result.scenarios[0].economic_margin_cents, null);
  assert.equal(result.scenarios[0].modeled_available_to_commit_cents, null);
  assert.equal(result.scenarios[0].opening_unpaid_obligations_cents, null);
  assert.equal(result.scenarios[0].decision, 'INCOMPLETE_ASSUMPTIONS');
});

test('failed deliveries stay in complete service cost; they are not billable accepted jobs', () => {
  const output = model(fixture());
  assert.equal(output.attempts_including_failures, 15);
  assert.equal(output.modeled_collections_cents, 118800);
  assert.equal(output.complete_attributable_incurred_cost_cents, 22400);
  assert.equal(output.economic_margin_cents, 96400);
  assert.equal(output.cash_after_obligations_and_reserves_cents, 89400);
});

test('modeled price and collections never appear as observed revenue', () => {
  const result = assessCommercial(fixture());
  assert.equal(result.actual.observed_collections_cents, 0);
  assert.equal(result.actual.complete_observed_cost_cents, null);
  assert.equal(result.actual.observed_available_surplus_cents, null);
  assert.equal(result.scenarios[0].canonical_cash_projection.summary.observed.revenue, null);
  assert.equal(result.scenarios[0].canonical_economic_projection.summary.observed.revenue, null);
  assert.equal(result.claims.commercial_success_proven_by_this_model, false);
});

test('each paid or accrued current bill is deducted once in both economic and cash views', () => {
  const input = fixture(), baseline = model(input);
  input.scenarios[0].cost_items.find(row => row.category === 'execution').settlement = 'unpaid';
  input.scenarios[0].investment_items.find(row => row.category === 'construction').settlement = 'unpaid';
  const output = model(input);
  assert.equal(output.unpaid_current_expenses_cents, 2500);
  assert.equal(output.paid_cash_expenses_cents, baseline.paid_cash_expenses_cents - 2500);
  assert.equal(output.economic_margin_cents, baseline.economic_margin_cents);
  assert.equal(output.cash_after_obligations_and_reserves_cents, baseline.cash_after_obligations_and_reserves_cents);
});

test('prior outstanding bills affect cash availability without distorting current period margin', () => {
  const input = fixture(), before = model(input);
  input.scenarios[0].opening_obligations[0].amount_cents += 4000;
  const output = model(input);
  assert.equal(output.economic_margin_cents, before.economic_margin_cents);
  assert.equal(output.modeled_available_to_commit_cents, before.modeled_available_to_commit_cents - 4000);
});

test('duplicate invoice identity across paid cost and unpaid obligation is refused', () => {
  const input = fixture();
  input.scenarios[0].opening_obligations[0].id = input.scenarios[0].cost_items[0].id;
  assert.throws(() => model(input), /Duplicate bill/);
});

test('same construction charge cannot be duplicated in service costs', () => {
  const input = fixture();
  input.scenarios[0].investment_items[0].id = input.scenarios[0].cost_items[0].id;
  assert.throws(() => model(input), /Duplicate bill/);
});

test('missing required delivery stage is not an implicit zero', () => {
  const input = fixture();
  input.scenarios[0].cost_items = input.scenarios[0].cost_items.filter(row => row.category !== 'recovery');
  const output = model(input);
  assert.deepEqual(output.missing_service_categories, ['recovery']);
  assert.equal(output.complete_attributable_incurred_cost_cents, null);
  assert.equal(output.modeled_available_to_commit_cents, null);
});

test('missing failed-candidate investment account prevents complete repayment arithmetic', () => {
  const input = fixture();
  input.scenarios[0].investment_items = input.scenarios[0].investment_items.filter(row => row.category !== 'failed_candidates');
  const output = model(input);
  assert.equal(output.exact_asset_repayment_scenario.fixedCost, null);
  assert.equal(output.exact_asset_repayment_scenario.paysBackWithinHorizon, null);
});

test('unknown money propagates even when the physical work is accepted', () => {
  const input = fixture();
  input.scenarios[0].cost_items.find(row => row.category === 'verification').amount_cents = null;
  const output = model(input);
  assert.equal(output.economic_margin_cents, null);
  assert.equal(output.loaded_cost_per_accepted_job_cents, null);
  assert.equal(output.required_price_for_economic_break_even_cents, null);
});

test('unknown settlement permits an economic cost but blocks cash availability', () => {
  const input = fixture();
  input.scenarios[0].cost_items[0].settlement = 'unknown';
  const output = model(input);
  assert.equal(output.economic_margin_cents, 96400);
  assert.equal(output.paid_cash_expenses_cents, null);
  assert.equal(output.modeled_available_to_commit_cents, null);
});

test('zero demand does not manufacture a per-customer cost or financing', () => {
  const input = fixture();
  Object.assign(input.scenarios[0], {accepted_jobs: 0, failed_attempts: 0});
  const output = model(input);
  assert.equal(output.modeled_collections_cents, 0);
  assert.equal(output.economic_margin_cents, -8000);
  assert.equal(output.loaded_cost_per_accepted_job_cents, null);
  assert.equal(output.required_price_for_economic_break_even_cents, null);
  assert.equal(output.modeled_available_to_commit_cents, 0);
  assert.equal(output.decision, 'NO_ACCEPTED_DEMAND');
});

test('low demand retains complete construction rather than favorable amortization', () => {
  const input = fixture();
  Object.assign(input.scenarios[0], {accepted_jobs: 1, failed_attempts: 0});
  const output = model(input);
  assert.equal(output.complete_attributable_incurred_cost_cents, 9000);
  assert.equal(output.loaded_cost_per_accepted_job_cents, 9000);
  assert.equal(output.modeled_available_to_commit_cents, 0);
});

test('collection losses reduce cash despite unchanged invoice price', () => {
  const input = fixture();
  input.scenarios[0].collection_bps = 7500;
  const output = model(input);
  assert.equal(output.invoices_at_full_collection_cents, 118800);
  assert.equal(output.modeled_collections_cents, 89100);
  assert.equal(output.modeled_uncollected_cents, 29700);
});

test('maintenance can erase a superficially positive saving', () => {
  const input = fixture();
  input.scenarios[0].maintenance_per_reuse_cents = 1000;
  const output = model(input);
  assert.equal(output.exact_asset_repayment_scenario.breakEvenReuses, null);
  assert.equal(output.exact_asset_repayment_scenario.netBenefit, -5000);
  assert.equal(output.exact_asset_repayment_scenario.paysBackWithinHorizon, false);
});

test('zero advantage against the strong conventional method gives no positive asset payback', () => {
  const input = fixture();
  input.scenarios[0].expected_saving_per_reuse_cents = 0;
  const output = model(input);
  assert.equal(output.exact_asset_repayment_scenario.breakEvenReuses, null);
  assert.equal(output.exact_asset_repayment_scenario.paysBackWithinHorizon, false);
});

test('unknown savings remains unknown; commercial margin is not capability repayment', () => {
  const input = fixture();
  input.scenarios[0].expected_saving_per_reuse_cents = null;
  const output = model(input);
  assert.ok(output.economic_margin_cents > 0);
  assert.equal(output.exact_asset_repayment_scenario.netBenefit, null);
  assert.equal(output.exact_asset_repayment_scenario.paysBackWithinHorizon, null);
});

test('hypothetical buyer savings do not add operating revenue', () => {
  const input = fixture(), before = model(input);
  input.scenarios[0].buyer.traditional_minutes = 600;
  const output = model(input);
  assert.ok(output.buyer.buyer_savings_cents > 0);
  assert.equal(output.modeled_collections_cents, before.modeled_collections_cents);
  assert.equal(output.modeled_available_to_commit_cents, before.modeled_available_to_commit_cents);
});

test('human wage gives a break-even duration, not an invented observed duration', () => {
  const output = model(fixture());
  assert.equal(output.buyer.human_labor_cost_cents, null);
  assert.equal(output.buyer.buyer_savings_cents, null);
  assert.equal(output.buyer.required_traditional_minutes, 9900 * 60 / 6538);
});

test('an unrelated asset cannot be given this candidate economic results', () => {
  const input = fixture();
  input.scenarios[0].asset_id = 'unrelated-capability';
  assert.throws(() => model(input), /exact tested asset/);
});

test('affordability alone does not justify a next investment or create authority', () => {
  const output = model(fixture());
  assert.equal(output.next_investment.modeled_affordable, true);
  assert.equal(output.next_investment.observed_surplus_affords_assumed_cost, null);
  assert.equal(output.next_investment.economically_eligible_for_review, false);
  assert.equal(output.next_investment.action_authorized, false);
});

test('even asserted repayment cannot make modeled collections real', () => {
  const input = fixture();
  Object.assign(input.evidence, {fresh_equivalent_work_verified: true, complete_monetary_costs_verified: true,
    actual_repayment_verified: true});
  input.scenarios[0].next_investment.justification_established = true;
  const output = model(input);
  assert.equal(output.next_investment.economically_eligible_for_review, false);
});

test('negative costs, fractional cents, sparse arrays and accessor input are refused', () => {
  for (const invalid of [-1, 0.5, Infinity]) {
    const input = fixture(); input.scenarios[0].price_cents = invalid;
    assert.throws(() => model(input));
  }
  const sparse = fixture(); sparse.scenarios.length = 2;
  assert.throws(() => assessCommercial(sparse), /Sparse/);
  const accessor = fixture(); Object.defineProperty(accessor, 'schema', {get: () => 'unsafe'});
  assert.throws(() => assessCommercial(accessor), /Accessors/);
});
