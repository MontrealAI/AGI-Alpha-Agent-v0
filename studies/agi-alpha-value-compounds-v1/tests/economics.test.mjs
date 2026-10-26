import test from 'node:test';
import assert from 'node:assert/strict';
import {buildEconomics, finiteInvestmentGrid, humanThresholds} from '../src/economics.mjs';

test('unknown complete costs propagate through both canonical accounting engines', () => {
  const result = buildEconomics();
  assert.equal(result.accounting_status.economic_admission,'HOLD');
  assert.equal(result.canonical_ledger_summary.observed.revenue,0);
  assert.equal(result.canonical_ledger_summary.observed.fullCost,null);
  assert.equal(result.canonical_ledger_summary.observed.availableSurplus,null);
  for (const row of result.canonical_cost_projection.scenarios) {
    assert.equal(row.costs.marginalMicrosPerAccepted,null);
    assert.equal(row.costs.recurringMicrosPerAccepted,null);
    assert.equal(row.costs.fullyLoadedMicrosPerAccepted,null);
  }
  assert.equal(result.recorded_substantive_missions,0);
  assert.equal(result.accounting_container_counts_as_job,false);
  assert.equal(result.accounting_status.observed_investment_outlay_minor,null);
  assert.equal(result.accounting_status.financial_transactions_executed,0);
  assert(result.investment_sensitivity.rows.every(row => row.netBenefit === null));
});

test('failed mission and investment unknowns cannot be erased by accepted missions', () => {
  const result = buildEconomics({observed:{missions:[
    {mission_id:'fresh-1',acceptance:'accepted',reference:'fresh input A'},
    {mission_id:'fresh-2',acceptance:'rejected',reference:'fresh input B'}]}});
  assert.equal(result.recorded_substantive_missions,2);
  assert.equal(result.accepted_research_missions,1);
  assert.equal(result.rejected_research_missions,1);
  assert.equal(result.actual_paid_customer_missions,0);
  assert.equal(result.canonical_ledger_summary.missions.length,3);
  assert.equal(result.canonical_ledger_summary.observed.fullCost,null);
  assert.equal(result.canonical_ledger_summary.observed.availableSurplus,null);
  assert.throws(() => buildEconomics({observed:{collections_minor:100}}),/no paid receipts/);
  assert.throws(() => buildEconomics({observed:{missions:[{mission_id:'x',acceptance:'accepted'},{mission_id:'x',acceptance:'accepted'}]}}),/Duplicate/);
});

test('finite sensitivity charges failed construction and upkeep and never admits actual investment', () => {
  const result = finiteInvestmentGrid({basis:'assumed',constructionCostMinor:100,failedConstructionCostMinor:20,
    maintenancePerReuseMinor:3,expectedSavingPerReuseMinor:13});
  const one = result.rows.find(row => row.remainingReuses === 1), twelve = result.rows.find(row => row.remainingReuses === 12);
  assert.equal(one.netBenefit,-110);
  assert.equal(twelve.netBenefit,0);
  assert.equal(twelve.breakEvenReuses,12);
  assert.equal(twelve.economically_admitted,false);
  const loss = finiteInvestmentGrid({basis:'assumed',constructionCostMinor:100,failedConstructionCostMinor:20,
    maintenancePerReuseMinor:3,expectedSavingPerReuseMinor:-1});
  assert(loss.rows.every(row => row.paysBackWithinHorizon === false));
  assert.throws(() => finiteInvestmentGrid({constructionCostMinor:0}),/explicitly labeled assumed/);
});

test('customer threshold requires declared equal effort and does not turn provider cost into price', () => {
  const result = humanThresholds([{kind:'provider_cost',currency:'USD',amountMinor:100},
    {kind:'customer_price',currency:'USD',amountMinor:100},
    {kind:'customer_price',currency:'USD',amountMinor:100,equal_customer_effort_assumption:true}]);
  assert(Math.abs(result.user_supplied_scenarios[0].break_even_human_minutes-60/50.14)<1e-12);
  assert.equal(result.user_supplied_scenarios[1].break_even_human_minutes,null);
  assert(Math.abs(result.user_supplied_scenarios[2].break_even_human_minutes-60/50.14)<1e-12);
  assert.equal(result.actual_customer_price_minor,null);
  assert.equal(result.actual_human_duration_minutes,null);
});
