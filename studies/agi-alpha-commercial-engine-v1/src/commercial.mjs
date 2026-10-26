// SPDX-License-Identifier: Apache-2.0
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {AUTOMATED_STAGES} from '../canonical/automated-costs.mjs';
import {planMission, replayLedger, calculateInvestment} from '../canonical/shadow-ledger.mjs';

export const SCHEMA = 'agi-alpha-commercial-assessment/v1';
export const SERVICE_CATEGORIES = [...AUTOMATED_STAGES, 'business', 'setup', 'service_maintenance'];
export const INVESTMENT_CATEGORIES = ['discovery', 'construction', 'failed_candidates', 'verification', 'integration'];
const MAX = 1_000_000_000_000;
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value)
  && Object.getPrototypeOf(value) === Object.prototype;
function assert(ok, message) { if (!ok) throw Error(message); }
function fields(value, allowed, label, required = allowed) {
  assert(plain(value), `${label}: plain object required`);
  assert(Object.keys(value).every(key => allowed.includes(key)), `${label}: unknown field`);
  assert(required.every(key => Object.hasOwn(value, key)), `${label}: missing field`);
}
function frame(raw) {
  let nodes = 0, characters = 0;
  const ancestors = new Set();
  const copy = (value, depth) => {
    assert(++nodes <= 50000 && depth <= 24, 'Input exceeds finite frame bounds');
    if (value === null || typeof value === 'boolean') return value;
    if (typeof value === 'number') {
      assert(Number.isSafeInteger(value) && !Object.is(value, -0), 'Whole finite input quantities required');
      return value;
    }
    if (typeof value === 'string') {
      characters += value.length;
      assert(characters <= 1_000_000, 'Input text exceeds bounds');
      return value;
    }
    const array = Array.isArray(value);
    assert(plain(value) || array, 'Input must be plain JSON');
    assert(!ancestors.has(value), 'Cyclic input refused');
    const descriptors = Object.getOwnPropertyDescriptors(value);
    const keys = Reflect.ownKeys(descriptors);
    assert(keys.every(key => typeof key === 'string' && key !== 'toJSON' &&
      Object.hasOwn(descriptors[key], 'value') && (descriptors[key].enumerable || (array && key === 'length'))),
    'Accessors, hidden properties and serializers refused');
    if (array) assert(value.length <= 4096 && keys.length === value.length + 1 &&
      keys.every(key => key === 'length' || (/^(0|[1-9][0-9]*)$/.test(key) && Number(key) < value.length)),
    'Sparse or oversized array refused');
    const result = array ? [] : {};
    ancestors.add(value);
    for (const key of keys) {
      if (array && key === 'length') continue;
      Object.defineProperty(result, key, {value: copy(descriptors[key].value, depth + 1),
        enumerable: true, writable: true, configurable: true});
    }
    ancestors.delete(value);
    return result;
  };
  return copy(raw, 0);
}
function id(value, label) {
  assert(typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,49}$/.test(value), `Invalid ${label}`);
  return value;
}
function reference(value, label) {
  assert(typeof value === 'string' && value.trim().length > 0 && value.length <= 1000 &&
    !/[\u0000-\u001f]/.test(value), `Invalid ${label}`);
  return value;
}
function amount(value, label, signed = false) {
  assert(value === null || (Number.isSafeInteger(value) && !Object.is(value, -0) &&
    Math.abs(value) <= MAX && (signed || value >= 0)), `Invalid ${label}`);
  return value;
}
function whole(value, label, maximum) {
  amount(value, label);
  assert(value === null || value <= maximum, `${label} exceeds bound`);
  return value;
}
function safe(value) {
  assert(value >= BigInt(-MAX) && value <= BigInt(MAX), 'Calculated amount exceeds supported bound');
  return Number(value);
}
const sum = values => values.some(value => value === null) ? null : safe(values.reduce((a, b) => a + BigInt(b), 0n));
const product = (a, b) => a === null || b === null ? null : safe(BigInt(a) * BigInt(b));
const difference = (a, b) => a === null || b === null ? null : safe(BigInt(a) - BigInt(b));
const ceilDivide = (a, b) => a === null || b === null || b <= 0 ? null : safe((BigInt(a) + BigInt(b) - 1n) / BigInt(b));
function roundedMinutesCost(minutes, hourly) {
  return minutes === null || hourly === null ? null : safe((BigInt(minutes) * BigInt(hourly) + 59n) / 60n);
}
function coveredItems(raw, categories, label, ids, units = false) {
  assert(Array.isArray(raw) && raw.length <= 128, `Invalid ${label}`);
  const rows = raw.map(row => {
    fields(row, ['id', 'category', 'amount_cents', 'settlement', 'reference', ...(units ? ['units'] : [])], label);
    id(row.id, `${label} id`);
    assert(!ids.has(row.id), `Duplicate bill or charge identity: ${row.id}`);
    ids.add(row.id);
    assert(categories.includes(row.category), `Invalid ${label} category`);
    amount(row.amount_cents, `${label} amount`);
    assert(['paid', 'unpaid', 'unknown'].includes(row.settlement), `Invalid ${label} settlement`);
    reference(row.reference, `${label} reference`);
    if (units) assert(['attempt', 'period'].includes(row.units), `Invalid ${label} units`);
    return {...row};
  });
  return {rows, missing_categories: categories.filter(category => !rows.some(row => row.category === category))};
}
function totals(rows) {
  return {
    incurred: sum(rows.map(row => row.total_cents)),
    paid: rows.some(row => row.settlement === 'unknown') ? null :
      sum(rows.filter(row => row.settlement === 'paid').map(row => row.total_cents)),
    unpaid: rows.some(row => row.settlement === 'unknown') ? null :
      sum(rows.filter(row => row.settlement === 'unpaid').map(row => row.total_cents))
  };
}
function projection(name, price, operatingCost, capabilityCost, reserves, obligations) {
  return planMission({missionId: name, reference: 'Explicit hypothetical period; no customer collection is asserted.',
    currency: 'USD', acceptance: 'accepted', totalCollectedCents: null, priceAssumptionCents: price,
    totalOperatingCostCents: operatingCost, operatingCostsComplete: operatingCost !== null,
    capabilityCostCents: capabilityCost, reserveCents: reserves, obligationCents: obligations,
    costBasis: 'assumed', reinvestmentBps: 0});
}
function buyerModel(buyer, price) {
  fields(buyer, ['hourly_cents', 'traditional_minutes', 'customer_minutes', 'source'], 'Buyer assumptions');
  for (const key of ['hourly_cents', 'traditional_minutes', 'customer_minutes']) amount(buyer[key], key);
  reference(buyer.source, 'Buyer source');
  const human = roundedMinutesCost(buyer.traditional_minutes, buyer.hourly_cents);
  const attention = roundedMinutesCost(buyer.customer_minutes, buyer.hourly_cents);
  const buyerCost = sum([price, attention]);
  return {...buyer, human_labor_cost_cents: human, residual_customer_effort_cost_cents: attention,
    price_plus_customer_effort_cents: buyerCost, buyer_savings_cents: difference(human, buyerCost),
    maximum_equal_cost_price_cents: difference(human, attention),
    required_traditional_minutes: buyerCost === null || !buyer.hourly_cents ? null : buyerCost * 60 / buyer.hourly_cents,
    scope: 'Conditional equivalent-quality wage-only comparison. Duration, willingness to pay and full employer cost are not inferred from a wage.'};
}

function scenarioModel(raw, asset, evidence, actualAvailable) {
  fields(raw, ['id', 'label', 'asset_id', 'price_cents', 'accepted_jobs', 'failed_attempts', 'collection_bps',
    'cost_items', 'investment_items', 'reserves_cents', 'opening_obligations', 'opening_obligations_complete', 'maintenance_per_reuse_cents',
    'expected_saving_per_reuse_cents', 'remaining_reuses', 'buyer', 'next_investment'], 'Scenario');
  id(raw.id, 'scenario id'); reference(raw.label, 'scenario label');
  assert(raw.id.length <= 40, 'Scenario id must leave room for canonical projection suffixes');
  assert(raw.asset_id === asset.id, 'Scenario investment must reference the exact tested asset');
  amount(raw.price_cents, 'price'); amount(raw.reserves_cents, 'reserves');
  whole(raw.accepted_jobs, 'accepted jobs', 100000); whole(raw.failed_attempts, 'failed attempts', 100000);
  whole(raw.collection_bps, 'collection basis points', 10000); whole(raw.remaining_reuses, 'remaining reuses', 1000000);
  amount(raw.maintenance_per_reuse_cents, 'asset upkeep'); amount(raw.expected_saving_per_reuse_cents, 'expected saving', true);
  const attempts = sum([raw.accepted_jobs, raw.failed_attempts]);
  const ids = new Set();
  const costs = coveredItems(raw.cost_items, SERVICE_CATEGORIES, 'Service costs', ids, true);
  const investment = coveredItems(raw.investment_items, INVESTMENT_CATEGORIES, 'Investment costs', ids);
  const opening = coveredItems(raw.opening_obligations, ['prior_obligation'], 'Opening obligations', ids);
  assert(typeof raw.opening_obligations_complete === 'boolean', 'Opening obligation coverage must be explicit');
  assert(opening.rows.every(row => row.settlement === 'unpaid' || row.settlement === 'unknown'),
    'Opening obligations must be outstanding, not already paid');
  const serviceRows = costs.rows.map(row => ({...row, total_cents: row.units === 'attempt' ?
    product(row.amount_cents, attempts) : row.amount_cents}));
  const assetRows = investment.rows.map(row => ({...row, total_cents: row.amount_cents}));
  const upkeep = {id: `${raw.id}:asset-upkeep`, category: 'asset_upkeep', settlement: 'paid',
    amount_cents: raw.maintenance_per_reuse_cents, total_cents: product(raw.maintenance_per_reuse_cents, raw.accepted_jobs),
    reference: 'Explicit scenario: incremental asset upkeep on each accepted invocation; distinct from general service maintenance.'};
  assert(!ids.has(upkeep.id), 'Reserved asset-upkeep identity duplicated');
  const completeService = costs.missing_categories.length === 0;
  const completeInvestment = investment.missing_categories.length === 0;
  const service = totals([...serviceRows, upkeep]), fixed = totals(assetRows);
  if (!completeService) service.incurred = service.paid = service.unpaid = null;
  if (!completeInvestment) fixed.incurred = fixed.paid = fixed.unpaid = null;
  const openingTotal = raw.opening_obligations_complete ?
    totals(opening.rows.map(row => ({...row, total_cents: row.amount_cents}))).unpaid : null;
  const invoiceTotal = product(raw.price_cents, raw.accepted_jobs);
  const expectedCollections = invoiceTotal === null || raw.collection_bps === null ? null :
    safe(BigInt(invoiceTotal) * BigInt(raw.collection_bps) / 10000n);
  const lostCollections = difference(invoiceTotal, expectedCollections);
  const expectedOperating = sum([service.incurred, fixed.incurred]);
  const expectedPaid = sum([service.paid, fixed.paid]);
  const allUnpaid = sum([service.unpaid, fixed.unpaid, openingTotal]);
  const economic = projection(`${raw.id}-economic`, expectedCollections, service.incurred, fixed.incurred, 0, 0);
  const cash = projection(`${raw.id}-cash`, expectedCollections, service.paid, fixed.paid, raw.reserves_cents, allUnpaid);
  const fixedNonFailure = completeInvestment ? sum(assetRows.filter(row => row.category !== 'failed_candidates')
    .map(row => row.total_cents)) : null;
  const failedConstruction = completeInvestment ? sum(assetRows.filter(row => row.category === 'failed_candidates')
    .map(row => row.total_cents)) : null;
  const repayment = calculateInvestment({constructionCostMinor: fixedNonFailure, failedConstructionCostMinor: failedConstruction,
    maintenancePerReuseMinor: raw.maintenance_per_reuse_cents, expectedSavingPerReuseMinor: raw.expected_saving_per_reuse_cents,
    remainingReuses: raw.remaining_reuses});
  fields(raw.next_investment, ['asset_id', 'full_cost_cents', 'justification_established', 'reference'], 'Next investment');
  id(raw.next_investment.asset_id, 'next asset'); amount(raw.next_investment.full_cost_cents, 'next full cost');
  assert(typeof raw.next_investment.justification_established === 'boolean', 'Next justification must be boolean');
  reference(raw.next_investment.reference, 'Next investment reference');
  const available = cash.summary.scenario.availableSurplus;
  const affordable = available === null || raw.next_investment.full_cost_cents === null ? null :
    available >= raw.next_investment.full_cost_cents;
  const afterNext = available === null || raw.next_investment.full_cost_cents === null ? null :
    difference(available, raw.next_investment.full_cost_cents);
  const actualAffordable = actualAvailable === null || raw.next_investment.full_cost_cents === null ? null :
    actualAvailable >= raw.next_investment.full_cost_cents;
  const contribution = raw.accepted_jobs === null || raw.accepted_jobs === 0 ? null :
    expectedCollections === null || service.incurred === null ? null : (expectedCollections - service.incurred) / raw.accepted_jobs;
  const actualProofComplete = asset.source_sha256 !== null && evidence.fresh_equivalent_work_verified &&
    evidence.complete_monetary_costs_verified && evidence.actual_repayment_verified;
  const operatingMargin = economic.summary.scenario.operatingMargin;
  let decision = 'INCOMPLETE_ASSUMPTIONS';
  if (operatingMargin !== null) decision = raw.accepted_jobs === 0 ? 'NO_ACCEPTED_DEMAND' :
    operatingMargin <= 0 ? 'NO_POSITIVE_PROFIT_UNDER_ASSUMPTIONS' : 'POSITIVE_MODELED_MARGIN_ONLY';
  return {
    id: raw.id, label: raw.label, basis: 'explicitly_modeled', asset_id: raw.asset_id,
    assumptions: raw, attempts_including_failures: attempts, accepted_jobs: raw.accepted_jobs,
    failed_attempts: raw.failed_attempts, invoices_at_full_collection_cents: invoiceTotal,
    modeled_collections_cents: expectedCollections, modeled_uncollected_cents: lostCollections,
    actual_collections_created_cents: 0, billed_cost_rows: [...serviceRows, upkeep, ...assetRows],
    missing_service_categories: costs.missing_categories, missing_investment_categories: investment.missing_categories,
    complete_attributable_incurred_cost_cents: expectedOperating, paid_cash_expenses_cents: expectedPaid,
    unpaid_current_expenses_cents: sum([service.unpaid, fixed.unpaid]), opening_unpaid_obligations_cents: openingTotal,
    economic_margin_cents: operatingMargin,
    operating_margin_fraction: expectedCollections === null || expectedCollections === 0 || operatingMargin === null ? null :
      operatingMargin / expectedCollections,
    recurring_cost_per_accepted_job_cents: raw.accepted_jobs === null || raw.accepted_jobs === 0 || service.incurred === null ? null :
      service.incurred / raw.accepted_jobs,
    loaded_cost_per_accepted_job_cents: raw.accepted_jobs === null || raw.accepted_jobs === 0 || expectedOperating === null ? null :
      expectedOperating / raw.accepted_jobs,
    recurring_contribution_per_accepted_job_cents: contribution,
    required_price_for_economic_break_even_cents: raw.accepted_jobs === null || raw.collection_bps === null ||
      raw.accepted_jobs === 0 || raw.collection_bps === 0 || expectedOperating === null ? null :
      ceilDivide(product(expectedOperating, 10000), product(raw.accepted_jobs, raw.collection_bps)),
    cash_after_obligations_and_reserves_cents: cash.summary.scenario.afterReserves,
    modeled_available_to_commit_cents: available, buyer: buyerModel(raw.buyer, raw.price_cents),
    exact_asset_repayment_scenario: repayment,
    next_investment: {...raw.next_investment, modeled_affordable: affordable,
      observed_surplus_affords_assumed_cost: actualAffordable,
      modeled_remaining_after_next_cents: afterNext,
      economically_eligible_for_review: actualAffordable === true && actualProofComplete && raw.next_investment.justification_established,
      action_authorized: false,
      hold_reasons: [!actualProofComplete ? 'Current tested asset has not established actual complete-cost repayment.' : null,
        !raw.next_investment.justification_established ? 'Next investment has no established independent repayment case.' : null,
        affordable !== true ? 'Affordable surplus is absent or incomplete even under the assumptions.' : null,
        actualAffordable !== true ? 'Observed spendable surplus does not establish affordability.' : null].filter(Boolean)},
    decision,
    canonical_economic_projection: economic,
    canonical_cash_projection: cash,
    accounting_scope: {
      economic: 'All attributable paid and accrued service/investment costs are deducted once. No second deduction for the same unpaid bills.',
      cash: 'Canonical fullCost here is a paid-cash projection only, not complete economic cost. Unpaid current costs and separate opening obligations are deducted once, followed by reserves.',
      collection: 'The native assumed-price field carries modeled collections. Every modeled collected-revenue field is null; no observed receipt is fabricated.',
      demand: 'Accepted jobs and failures are explicit demand/quality assumptions, never derived from test counts or packet replays.',
      repayment: 'Lifetime savings must compare equivalent accepted work against the strongest practical alternative. A positive scenario does not establish observed savings.',
      allocation: 'The entire incremental asset construction account is charged once in this finite modeled period; no favorable amortization is silently chosen.'
    }
  };
}

export function assessCommercial(raw) {
  const input = frame(raw);
  fields(input, ['schema', 'asset', 'evidence', 'actual_ledger', 'scenarios'], 'Commercial assessment');
  assert(input.schema === SCHEMA, 'Unsupported commercial assessment schema');
  fields(input.asset, ['id', 'source_sha256', 'reference'], 'Asset');
  id(input.asset.id, 'asset id');
  assert(input.asset.source_sha256 === null || /^[a-f0-9]{64}$/.test(input.asset.source_sha256), 'Invalid exact asset hash');
  reference(input.asset.reference, 'Asset reference');
  fields(input.evidence, ['fresh_equivalent_work_verified', 'complete_monetary_costs_verified',
    'actual_repayment_verified', 'reference'], 'Evidence');
  for (const key of ['fresh_equivalent_work_verified', 'complete_monetary_costs_verified', 'actual_repayment_verified'])
    assert(typeof input.evidence[key] === 'boolean', 'Evidence claims require explicit boolean values');
  reference(input.evidence.reference, 'Evidence reference');
  if (input.evidence.actual_repayment_verified) assert(input.evidence.complete_monetary_costs_verified &&
    input.evidence.fresh_equivalent_work_verified && input.asset.source_sha256 !== null,
  'Actual repayment requires exact-asset, fresh-work and complete monetary evidence');
  const actual = input.actual_ledger === null ? null : replayLedger(input.actual_ledger);
  if (actual) assert(actual.currency === 'USD', 'This comparison does not infer currency conversion');
  assert(Array.isArray(input.scenarios) && input.scenarios.length <= 32, 'Invalid scenario array');
  const seen = new Set();
  const scenarios = input.scenarios.map(row => {
    assert(!seen.has(row.id), 'Duplicate scenario id'); seen.add(row.id);
    return scenarioModel(row, input.asset, input.evidence, actual?.observed.availableSurplus ?? null);
  });
  return {schema: 'agi-alpha-commercial-assessment-result/v1', currency: 'USD', asset: input.asset,
    evidence_assertions: input.evidence,
    actual: {canonical_summary: actual, observed_collections_cents: actual?.observed.revenue ?? null,
      complete_observed_cost_cents: actual?.observed.fullCost ?? null,
      observed_margin_cents: actual?.observed.operatingMargin ?? null,
      observed_available_surplus_cents: actual?.observed.availableSurplus ?? null,
      repayment_status: input.evidence.actual_repayment_verified ? 'SUPPLIED_EVIDENCE_REQUIRES_REVIEW' : 'NOT_ESTABLISHED',
      monetary_admission: 'NO_AUTOMATIC_PROMOTION',
      scope: 'Canonical supplied-evidence accounting. The module does not authenticate bills, customer acceptance or asserted evidence.'},
    scenarios,
    claims: {commercial_success_proven_by_this_model: false, actual_financing_executed: false,
      self_acceleration_demonstrated: false, transaction_authority: false},
    scope: 'Nontransactional commercial decision aid using unchanged AGI ALPHA cost-stage and shadow-ledger APIs. Unknowns remain unknown; modeled profitability is not realized profit.'};
}

export function inputTemplate() {
  const item = (category, units = false) => ({id: `${units ? 'service' : 'investment'}-${category}`, category,
    amount_cents: null, settlement: 'unknown', reference: 'Unmeasured; replace only with explicit evidence or a labeled assumption.',
    ...(units ? {units: AUTOMATED_STAGES.includes(category) ? 'attempt' : 'period'} : {})});
  return {schema: SCHEMA, asset: {id: 'component-compatibility', source_sha256: null,
    reference: 'Supply the exact retained asset identity from the frozen study.'},
  evidence: {fresh_equivalent_work_verified: false, complete_monetary_costs_verified: false,
    actual_repayment_verified: false, reference: 'No complete monetary repayment evidence supplied.'},
  actual_ledger: null,
  scenarios: [{id: 'unpriced', label: 'Incomplete hypothesis; all unavailable costs remain unknown.', asset_id: 'component-compatibility',
    price_cents: null, accepted_jobs: null, failed_attempts: null, collection_bps: null,
    cost_items: SERVICE_CATEGORIES.map(category => item(category, true)),
    investment_items: INVESTMENT_CATEGORIES.map(category => item(category)),
    reserves_cents: null, opening_obligations: [], opening_obligations_complete: false, maintenance_per_reuse_cents: null,
    expected_saving_per_reuse_cents: null, remaining_reuses: null,
    buyer: {hourly_cents: null, traditional_minutes: null, customer_minutes: null,
      source: 'Matched human duration, customer effort and rate have not been supplied.'},
    next_investment: {asset_id: 'unselected-next-investment', full_cost_cents: null,
      justification_established: false, reference: 'No next investment has earned admission.'}}]};
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const arg = process.argv[2];
    if (arg === '--help' || !arg) {
      process.stdout.write('Usage: node src/commercial.mjs INPUT.json\n       node src/commercial.mjs --template\n' +
        'Reads bounded plain JSON and prints nontransactional assessment JSON. No network, payment, credential or runtime action.\n' +
        'Costs are USD cents. All scenario numbers are assumptions. Unknown values must be null.\n');
    } else if (arg === '--template') process.stdout.write(`${JSON.stringify(inputTemplate(), null, 2)}\n`);
    else {
      assert(process.argv.length === 3, 'Exactly one input path is required');
      const bytes = readFileSync(arg);
      assert(bytes.length <= 2_000_000, 'Input file exceeds 2 MB');
      process.stdout.write(`${JSON.stringify(assessCommercial(JSON.parse(bytes.toString('utf8'))), null, 2)}\n`);
    }
  } catch (error) { process.stderr.write(`Commercial assessment refused: ${error.message}\n`); process.exitCode = 2; }
}
