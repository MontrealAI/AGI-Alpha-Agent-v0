// SPDX-License-Identifier: Apache-2.0
// Read-only audit of three real SIMULATED posterior-diagnostic arms. No financial authority.
// Derived from reconcile_v3.mjs; frozen primary bridge remains unchanged.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import zlib from 'node:zlib';
import readline from 'node:readline';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here);
const resultsDir = path.resolve(process.argv[2] || path.join(root, 'results/paid_work_posterior_diagnostic'));
const configPath = path.resolve(process.argv[3] || path.join(resultsDir, 'frozen_config.json'));
const output = path.resolve(process.argv[4] || path.join(root, 'qa/posterior_diagnostic_reconciliation.json'));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const expected = {
  'shadow-ledger.mjs': 'cdc7c5a73593050a9af79b54589462e27f61b868e88ca6985d5cb639f3066d21',
  'automated-costs.mjs': '0dfca3ae4e7ef1d17bc78521f91917ef068280cf832d3565c354de2085c52506',
  'funding.mjs': '7c017e77f26ca7c755e8fb832ec4e7eddfe241c758b769931e72fadedbb3e083',
};
for (const [name, hash] of Object.entries(expected)) {
  if (sha(fs.readFileSync(path.join(here, 'upstream', name))) !== hash)
    throw Error('Changed upstream module: ' + name);
}
const {replayLedger} = await import('./upstream/shadow-ledger.mjs');
const {fundingView} = await import('./upstream/funding.mjs');
const {evaluateAutomatedCosts, AUTOMATED_STAGES} = await import('./upstream/automated-costs.mjs');
const c = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const registerPath = fs.existsSync(path.join(resultsDir, 'frozen_workflow_costs.json')) ? path.join(resultsDir, 'frozen_workflow_costs.json') : path.resolve(path.dirname(configPath), c.cost_register);
const register = JSON.parse(fs.readFileSync(registerPath, 'utf8'));
const betaAt = month => c.network.beta_epochs.filter(e => e.month <= month).at(-1) || c.network.beta_epochs[0];
const files = fs.readdirSync(resultsDir).filter(n => n.endsWith('_complete_records.jsonl.gz')).sort();
if (!files.length) throw Error('Complete histories required; representative ledgers are insufficient.');
const sum = xs => xs.reduce((a, b) => a + b, 0);
const cents = x => Math.round(x * 100);
const micros = x => Math.round(x * 1e6);
const val = (o, k) => Number(o[k] || 0);
const flows = ['operating_outflow', 'investment_outflow', 'refund_outflow', 'arrears_outflow'];
const directKeys = ['production_cost', 'correction_cost', 'recovery_cost', 'storage_cost', 'recipient_acquisition_cost', 'network_access_cost', 'network_distribution_cost', 'network_composition_cost'];
const businessKeys = ['qualification_cost', 'unsupported_intake_cost', 'fixed_cost', 'payment_fees', 'arrears_paid', 'baseline_equivalent_acquisition_cost'];
const investmentKeys = ['investment_cost', 'retention_cost', 'emergence_scan_cost', 'discovery_cost', 'setup_fixed_cost', 'maintenance_cost', 'revalidation_cost', 'beta_reevaluation_cost', 'revocation_cost'];
const report = {
  schema: 'paid-job-posterior-diagnostic-reconciliation/v1', status: 'IN_PROGRESS', basis: 'SIMULATED_READ_ONLY_RECONCILIATION', financial_authority: 'NONE',
  results_path: path.relative(root, resultsDir), configuration_path: path.relative(root, configPath),
  directed_software_fixture: c.qa_directed_fixture || null,
  source_hashes: {bridge: sha(fs.readFileSync(fileURLToPath(import.meta.url))), config: sha(fs.readFileSync(configPath))},
  upstream: {commit: 'daac40ee9e02a1b1bb100d7b9fcfa5caab04c297', status: 'Unmerged historical research PR source, not accepted-main production code', sha256: expected},
  histories: 0, months: 0, paired_worlds: 0, purchases: 0, completed_campaigns: 0,
  initial_alpha_assessments: 0, retained_alpha_assessments: 0, admitted_alpha_assessments: 0,
  admitted_with_nonpositive_construction_inclusive_forecast: 0,
  charged_recipient_acquisitions: 0, charged_compositions: 0, activity_receipts: 0, source_jobs: 0, source_job_candidates: 0, paid_job_retentions: 0,
  max_cash_residual_usd: 0, max_canonical_cent_difference: 0,
  failures: [], specimens: [], scenario_totals: {}, diagnostic_paired_values: [],
  interpretation: [
    'All commercial histories are simulated; canonical observed collections remain explicitly unknown.',
    'The canonical funding week field is an alias for simulation month. A separate one-month snapshot preserves dynamic reserves.',
    'Known future refunds are accrued obligations; that amount is removed from the reserve-only portion to avoid counting it twice.',
    'The legacy strict full-seed-recovery view is descriptive, not imported as the new investment policy or success rule.',
    'The funding helper retains legacy metadata about unpriced discovery. Its numeric ceilings alone are reused; the new ledger separately prices its entire declared campaign.',
    'Canonical automated-cost normalization uses one pooled true accepted project; all failed and zero-output histories remain in the numerator.',
    'Production cost includes original-model validation. A packed stage allocation in the canonical adapter does not mean validation was free.',
    'Source-job A costs are linked to prior paid activity; they are excluded from incremental B admission and never charged again.',
    'Initial and retained graph admission both require positive prospective incremental value; construction-inclusive residual forecasts are not actual historical repayment.',
    'A contains direct job expense plus explicitly separated baseline overhead; B contains incremental retention/lifecycle; C contains optional research and priced startup discovery.',
    'Arithmetic reconciliation does not validate demand, quality assumptions, commercial scope or scientific causality.'
  ],
};
const freezePath = path.join(resultsDir, 'freeze.json');
if (fs.existsSync(freezePath)) {
  const freeze = JSON.parse(fs.readFileSync(freezePath, 'utf8'));
  const changed = Object.entries(freeze.closure_sha256 || {}).filter(([p, hash]) => !fs.existsSync(path.join(root,p)) || sha(fs.readFileSync(path.join(root,p))) !== hash);
  report.freeze_closure = {manifest_sha256: sha(fs.readFileSync(freezePath)), files_checked: Object.keys(freeze.closure_sha256 || {}).length, matched: changed.length === 0, changed: changed.map(([p]) => p)};
  if (changed.length) report.failures.push({label:'frozen_source_closure_changed', paths:changed.map(([p]) => p)});
} else report.freeze_closure = {matched:null, note:'Development or explicit QA fixture; no confirmation freeze is asserted.'};
function check(ok, label, context = {}) {
  if (!ok && report.failures.length < 200) report.failures.push({label, ...context});
}
function near(actual, wanted, tolerance, label, context = {}) {
  check(Math.abs(actual - wanted) <= tolerance, label, {...context, actual, expected: wanted});
}
const groups = new Map();
const pooled = new Map();

function audit(r) {
  report.histories++;
  const ctx = {scenario: r.scenario, world: r.world, policy: r.policy, diagnostic_arm: r.diagnostic_arm};
  check(['frozen_beta','frozen_network','posterior_coherent_network'].includes(r.diagnostic_arm), 'explicit_diagnostic_arm', ctx);
  const m = r.metrics, rows = r.ledger, events = r.events;
  const setup = m.discovery_cost + m.setup_fixed_cost;
  let previous = c.seed_cash - setup, paid = setup, receipts = 0;
  check(rows.length === c.months + c.runoff_months, 'complete_horizon', ctx);
  const byMonth = new Map(rows.map(x => [x.month, x]));
  const beforePurchase = new Map();
  for (const row of rows) {
    report.months++;
    receipts += row.collections;
    paid += sum(flows.map(k => val(row, k)));
    const predicted = previous + row.collections - sum(flows.map(k => val(row, k)));
    const error = Math.abs(predicted - row.closing_cash);
    report.max_cash_residual_usd = Math.max(report.max_cash_residual_usd, error);
    near(row.opening_cash, previous, 1e-5, 'opening_cash_continuity', {...ctx, month: row.month});
    near(row.closing_cash, predicted, 1e-5, 'cash_flow_conservation', {...ctx, month: row.month});
    near(row.closing_cash, c.seed_cash + receipts - paid, 1e-5, 'cumulative_cash_conservation', {...ctx, month: row.month});
    check(row.closing_cash >= -1e-7 && row.unpaid_obligations >= -1e-7, 'nonnegative_cash_obligations', {...ctx, month: row.month});
    near(row.true_accepted_projects + row.false_passes, row.validated_deliveries, 0, 'monthly_quality_partition', {...ctx, month: row.month});
    const known = row.known_future_refunds;
    const pendingRecovery = val(row, 'pending_recovery_obligation');
    const liabilities = cents(row.unpaid_obligations + known + pendingRecovery);
    const reserveOnly = cents(Math.max(0, row.reserve - known - pendingRecovery));
    const cash = cents(row.closing_cash), collected = cents(receipts);
    const accrued = cents(paid + row.unpaid_obligations + known + pendingRecovery);
    const strict = Math.min(cash - liabilities - reserveOnly, collected - accrued - reserveOnly);
    const canonical = fundingView({
      config: {id: r.scenario, initialCashCents: cents(c.seed_cash), reserveCents: reserveOnly, weeks: c.months,
        investmentCostBasis: 'full-history', historicalCostTiming: 'not-opening'},
      arm: r.policy, seed: r.world,
      histories: {bills: [], cash: [], balances: [{
        week: row.month, cashCents: cash, obligationsCents: liabilities,
        cumulativeCollectionsCents: collected, accruedCostsCents: accrued,
        earnedAvailableCents: strict, reserveCents: reserveOnly,
      }]},
    }).terminal;
    const numericUncommitted = Math.max(0, canonical.cashCapBeforeEarmarksCents);
    const gap = Math.abs(numericUncommitted - cents(row.available_uncommitted_cash));
    report.max_canonical_cent_difference = Math.max(report.max_canonical_cent_difference, gap);
    check(gap <= 3, 'canonical_liquidity_ceiling', {...ctx, month: row.month, gap_cents: gap});
    if (report.specimens.length < 6 && row.month === rows.length) report.specimens.push({...ctx, terminal: canonical});
    beforePurchase.set(row.month, {cash: row.closing_cash, paid, receipts, known, unpaid: row.unpaid_obligations, reserve: row.reserve});
    const units = [['tokens', 'tokens'], ['workbench_minutes', 'workbench_minutes'], ['container_minutes', 'container_minutes']];
    for (const [suffix, limit] of units) {
      const d = row['delivery_' + suffix], a = row['research_' + suffix], cap = row['capacity_' + limit];
      if (d === undefined || a === undefined || cap === undefined) {
        check(false, 'missing_monthly_resource_record', {...ctx, month: row.month, unit: suffix});
      } else {
        check(d >= -1e-6 && a >= -1e-6 && d + a <= cap + 1e-5, 'monthly_resource_capacity', {...ctx, month: row.month, unit: suffix, delivery: d, research: a, capacity: cap});
      }
    }
    previous = row.closing_cash;
  }
  const last = rows.at(-1);
  near(m.closing_cash, last.closing_cash, 1e-5, 'terminal_cash', ctx);
  near(m.unpaid_obligations, last.unpaid_obligations + val(last,'pending_recovery_obligation'), 1e-5, 'terminal_all_obligations_visible', ctx);
  near(m.net_profit, last.closing_cash - c.seed_cash - m.unpaid_obligations, 1e-5, 'terminal_profit', ctx);
  near(m.collections, receipts, 1e-5, 'total_collections', ctx);
  near(m.true_accepted_projects + m.false_passes, m.validated_deliveries, 0, 'quality_partition', ctx);
  check(last.outstanding_receivables === 0 && last.known_future_refunds === 0, 'receivables_refund_runoff_explicit', ctx);
  near(last.pending_recovery_tasks, val(m,'unresolved_recovery_tasks'), 0, 'unfinished_recovery_not_erased', ctx);
  near(val(last,'pending_recovery_obligation'), val(m,'unresolved_recovery_obligation'), 1e-5, 'unfinished_recovery_obligation_visible', ctx);
  const directPaid = sum(directKeys.map(k => val(m, k)));
  const unresolvedDirect = sum((r.activities || []).filter(x => !x.cash_paid && x.cost_key === 'recovery_cost').map(x => x.cost_usd));
  const direct = directPaid + unresolvedDirect;
  const business = sum(businessKeys.map(k => val(m, k)));
  const investments = sum(investmentKeys.map(k => val(m, k)));
  const unpaidRefund = val(m, 'refund_obligations_unpaid');
  const unpaidOperating = m.unpaid_obligations - unpaidRefund;
  const complete = directPaid + business + investments + unpaidOperating;
  near(m.fully_allocated_cost_total, complete, 1e-5, 'independent_full_cost', ctx);
  near(m.net_profit, m.collections - m.refunds - unpaidRefund - complete, 1e-5, 'complete_cost_profit', ctx);
  near(m.direct_cost_total, direct, 1e-5, 'direct_cost_total', ctx);
  if (m.true_accepted_projects > 0) {
    near(m.fully_allocated_cost_per_true_project, complete / m.true_accepted_projects, 1e-6, 'true_accept_denominator', ctx);
  } else check(m.fully_allocated_cost_per_true_project === null, 'zero_output_ratio_undefined', ctx);
  near(m.quality_adjusted_profit, m.net_profit - m.undetected_paid_false_pass_revenue, 1e-5, 'quality_adjusted_profit', ctx);
  for (const suffix of ['tokens', 'workbench_minutes', 'container_minutes']) {
    for (const type of ['delivery', 'research']) {
      if (rows.every(x => x[type + '_' + suffix] !== undefined))
        near(sum(rows.map(x => x[type + '_' + suffix])), m[type + '_' + suffix], 1e-4, 'resource_totals', {...ctx, unit: type + '_' + suffix});
    }
  }
  const activities = r.activities || [], jobs = r.job_records || {};
  const activityById = new Map();
  check(Array.isArray(r.activities) && r.activities.length > 0, 'complete_activity_export', ctx);
  for (const activity of activities) {
    report.activity_receipts++;
    check(typeof activity.activity_id === 'string' && !activityById.has(activity.activity_id), 'unique_charged_activity_identity', {...ctx, activity_id: activity.activity_id});
    check(['A','B','C'].includes(activity.ledger), 'disjoint_ABC_assignment', {...ctx, activity_id: activity.activity_id});
    check(Number.isFinite(activity.cost_usd) && activity.cost_usd >= 0, 'nonnegative_activity_charge', {...ctx, activity_id: activity.activity_id});
    activityById.set(activity.activity_id, activity);
    if (activity.activity_components?.length) {
      near(sum(activity.activity_components.map(x => x.usd)), activity.cost_usd, 1e-5, 'activity_component_cost_identity', {...ctx, activity_id: activity.activity_id});
    }
  }
  near(sum(activities.map(x => x.cost_usd)), complete, 1e-5, 'all_expenses_once_in_ABC', ctx);
  near(sum(activities.filter(x => x.cash_paid).map(x => x.cost_usd)), paid - m.refunds, 1e-5, 'activity_cash_charges_reconcile_bank', ctx);
  for (const [letter, metric] of [['A','ledger_A_delivery_total'], ['B','ledger_B_retention_total'], ['C','ledger_C_optional_research_total']])
    near(sum(activities.filter(x => x.ledger === letter).map(x => x.cost_usd)), m[metric], 1e-5, 'ABC_reported_partition', {...ctx, ledger: letter});
  near(m.baseline_overhead_in_A + m.direct_job_cost_in_A, m.ledger_A_delivery_total, 1e-5, 'A_overhead_separately_disclosed', ctx);
  for (const row of rows) {
    const actualResources = activities.filter(x => x.month === row.month && x.cash_paid && x.resource_budget_or_execution && !['investment_cost','retention_cost'].includes(x.cost_key));
    for (const [field, suffix] of [['tokens','tokens'], ['minutes','workbench_minutes'], ['container_minutes','container_minutes']])
      near(sum(actualResources.map(x => x.resource_budget_or_execution[field])), row['delivery_'+suffix] + row['research_'+suffix], 1e-4, 'activity_resources_match_month', {...ctx, month: row.month, field});
  }
  report.source_jobs += Object.keys(jobs).length;
  const jobReceiptIds = new Set();
  for (const [id, job] of Object.entries(jobs)) {
    check(job.job_id === id && !jobReceiptIds.has(job.receipt_id), 'unique_source_job_receipt', {...ctx, job_id: id});
    jobReceiptIds.add(job.receipt_id);
    const charged = (job.charged_activity_ids || []).map(x => activityById.get(x));
    check(charged.every(Boolean), 'source_job_activity_references_resolve', {...ctx, job_id: id});
    near(sum(charged.filter(x => x?.ledger === 'A').map(x => x.cost_usd)), job.ledger_A_charged_cost, 1e-5, 'source_job_A_cost_identity', {...ctx, job_id: id});
    near(sum(charged.filter(x => x?.ledger === 'B').map(x => x.cost_usd)), job.ledger_B_charged_cost, 1e-5, 'source_job_B_cost_identity', {...ctx, job_id: id});
    check(!job.actually_collected_by_horizon || job.payment_authorized && job.status === 'validated_pass', 'collections_require_authorized_delivered_job', {...ctx, job_id: id});
    check(!job.actually_refunded_by_horizon || job.actually_collected_by_horizon, 'refund_requires_collection', {...ctx, job_id: id});
  }
  for (const event of events.filter(x => x.kind === 'paid_job_candidate')) {
    report.source_job_candidates++;
    const job = jobs[event.origin_job_id];
    check(Boolean(job) && job.status === 'validated_pass', 'candidate_origin_observably_delivered', {...ctx, id: event.id});
    if (!job) continue;
    check(event.origin.kind === 'paid_job' && event.origin.outcome_observed === 'validated_pass' && event.origin.ledger_receipt_id === job.receipt_id, 'candidate_origin_receipt_matches', {...ctx, id: event.id});
    const source = event.source_activity_ids.map(x => activityById.get(x));
    check(source.every(x => x && x.ledger === 'A' && x.cash_paid && x.month <= event.month), 'source_job_costs_precede_incremental_candidate', {...ctx, id: event.id});
    near(sum(source.filter(Boolean).map(x => x.cost_usd)), event.source_cost_already_charged, 1e-5, 'source_cost_exact_prior_A_activity', {...ctx, id: event.id});
    near(event.origin.delivery_cost_already_charged, event.source_cost_already_charged, 1e-5, 'origin_excluded_cost_identity', {...ctx, id: event.id});
    const scan = activityById.get(event.retention_scan_activity_id);
    check(scan?.ledger === 'B' && scan.cost_key === 'emergence_scan_cost' && scan.cost_usd > 0, 'candidate_scan_charged_in_B', {...ctx, id: event.id});
  }
  const missionId = 'simulated-enterprise';
  const base = {missionId, reference: 'SIMULATED complete-history projection; not an observed sale'};
  const e = (id, type, category, amount, basis = 'assumed') => ({...base, id, type, category, amountMinor: amount, basis});
  const shadow = replayLedger({schema: 'alpha-shadow-ledger/v1', currency: 'USD', events: [
    {...base, id: 'mission', type: 'mission', acceptance: m.true_accepted_projects > 0 ? 'accepted' : 'rejected'},
    e('observed-not-claimed', 'revenue', 'collected', null, 'unknown'),
    e('modeled-net-receipts', 'revenue', 'price', cents(m.collections - m.refunds)),
    e('delivery', 'cost', 'delivery', cents(directPaid)),
    e('business', 'cost', 'business', cents(business)),
    e('construction', 'cost', 'capability', cents(investments - m.maintenance_cost - m.revalidation_cost - m.beta_reevaluation_cost - m.revocation_cost)),
    e('maintenance', 'cost', 'maintenance', cents(m.maintenance_cost + m.revalidation_cost + m.beta_reevaluation_cost + m.revocation_cost)),
    e('owed', 'obligation', 'unpaid', cents(m.unpaid_obligations)),
    e('reserve', 'reserve', 'reliability', cents(last.reserve)),
  ]}, {reinvestmentBps: 10000});
  check(shadow.observed.revenue === null, 'no_observed_revenue_claim', ctx);
  near(shadow.scenario.operatingMargin, cents(m.net_profit + m.unpaid_obligations), 3, 'canonical_shadow_margin', ctx);

  const purchases = events.filter(e => ['research_purchase','retention_purchase'].includes(e.kind));
  const completed = events.filter(e => ['research_complete','retention_complete'].includes(e.kind));
  report.purchases += purchases.length;
  report.completed_campaigns += completed.length;
  near(sum(purchases.map(x => x.bill)), m.investment_cost + m.retention_cost, 1e-5, 'all_investment_bills', ctx);
  near(sum(purchases.map(x => x.seed_funded)), m.research_seed_funded + m.retention_seed_funded, 1e-5, 'seed_funding_total', ctx);
  near(sum(purchases.map(x => x.operating_funded)), m.research_operating_funded + m.retention_operating_funded, 1e-5, 'operating_funding_total', ctx);
  for (const p of purchases) {
    const row = beforePurchase.get(p.month), priorCash = row.cash + p.bill;
    const billReceipt = activityById.get(p.incremental_receipt_id);
    check(Boolean(billReceipt) && billReceipt.cash_paid && billReceipt.month === p.month, 'purchase_has_exact_paid_activity_receipt', {...ctx, id: p.id});
    if (billReceipt) {
      near(billReceipt.cost_usd, p.bill, 1e-5, 'purchase_receipt_cost_identity', {...ctx, id: p.id});
      check(billReceipt.ledger === (p.kind === 'retention_purchase' ? 'B' : 'C'), 'purchase_correct_ledger_class', {...ctx, id: p.id});
    }
    if (p.kind === 'retention_purchase') {
      report.paid_job_retentions++;
      const source = events.find(x => x.kind === 'paid_job_candidate' && x.id === p.id);
      check(Boolean(source) && source.month <= p.month, 'retention_has_earlier_observed_job_candidate', {...ctx, id: p.id});
      check(p.source_job_construction_recharged === false && p.origin.kind === 'paid_job', 'no_source_job_recharge_in_B', {...ctx, id: p.id});
      if (source) check(JSON.stringify(source.origin) === JSON.stringify(p.origin), 'retention_origin_provenance_unchanged', {...ctx, id: p.id});
    }
    near(p.seed_funded + p.operating_funded, p.bill, 1e-5, 'exclusive_funding_partition', {...ctx, month: p.month});
    near(p.cash_after, row.cash, 1e-5, 'purchase_cash_snapshot', {...ctx, month: p.month});
    check(priorCash + 1e-7 >= p.bill + row.reserve + row.unpaid, 'investment_liquidity_guard', {...ctx, month: p.month});
    const generated = Math.max(0, priorCash - c.seed_cash - row.unpaid - row.known);
    check(p.operating_funded <= generated + 1e-5, 'no_liability_or_seed_labeled_earnings', {...ctx, month: p.month, classified: p.operating_funded, available_generated: generated});
    if (c.policy.allow_seed_funded_research === false && p.kind === 'research_purchase')
      near(p.seed_funded, 0, 1e-7, 'seed_research_disabled', {...ctx, month: p.month});
    if (p.qa_forced_capital_action) {
      check(c.qa_directed_fixture?.basis === 'AUTHOR_SPECIFIED_SYNTHETIC_BRANCH_TEST' && c.qa_directed_fixture.not_a_primary_or_favorable_economic_scenario === true, 'forced_action_only_in_explicit_software_QA', {...ctx, month: p.month});
    } else check(p.expected_incremental_terminal_cash > 0, 'positive_registered_forecast', {...ctx, month: p.month});
    const availableByConvention = Math.max(0, priorCash - c.seed_cash - p.reserve - p.unpaid_obligations_before);
    near(p.available_operating_after_reserve_before, availableByConvention, 1e-5, 'earnings_after_full_reserve_convention', {...ctx, month: p.month});
    near(p.operating_funded, Math.min(p.bill, availableByConvention), 1e-5, 'operating_funding_exact_partition', {...ctx, month: p.month});
    const source = (p.kind === 'retention_purchase' ? register.incremental_retention_options : register.investment_campaigns)[p.action];
    near(p.quantity_multiplier, c.scenarios[r.scenario].activity_quantity_multiplier, 1e-9, 'campaign_quantity_scenario_match', {...ctx, month: p.month});
    near(p.source_budget, source.derived_budget_usd, 1e-5, 'campaign_complete_source_budget', {...ctx, month: p.month});
    near(p.bill, source.derived_budget_usd * p.quantity_multiplier, 1e-5, 'campaign_complete_bill', {...ctx, month: p.month});
    const finishes = completed.filter(x => x.id === p.id && x.month - x.actual_build_months + 1 === p.month);
    if (finishes.length) check(finishes[0].month >= p.month, 'construction_after_funding', {...ctx, month: p.month});
  }
  for (const e of completed) {
    const starts = e.month - e.actual_build_months + 1;
    const p = purchases.find(x => x.id === e.id && x.month === starts);
    check(Boolean(p), 'campaign_has_prior_paid_purchase', {...ctx, month: e.month});
    if (p) {
      near(e.paid_cost, p.bill, 1e-5, 'campaign_bill_identity', {...ctx, month: e.month});
      const source = (p.kind === 'retention_purchase' ? register.incremental_retention_options : register.investment_campaigns)[p.action];
      near(e.consumed_minutes, source.resource_minutes * p.quantity_multiplier, 1e-5, 'completed_campaign_workbench_charged', {...ctx, month: e.month});
      near(e.consumed_tokens, sum(['astra_input','astra_output','terra_input','terra_output'].map(k => source[k])) * p.quantity_multiplier, 1e-4, 'completed_campaign_tokens_charged', {...ctx, month: e.month});
    }
  }
  for (const [metric, sourceField] of [['research_workbench_minutes','resource_minutes'], ['research_container_minutes','container_sessions_16gb']]) {
    const factor = sourceField === 'container_sessions_16gb' ? 20 : 1;
    const committed = sum(purchases.map(p => (p.kind === 'retention_purchase' ? register.incremental_retention_options : register.investment_campaigns)[p.action][sourceField] * p.quantity_multiplier * factor));
    check(m[metric] <= committed + 1e-4, 'research_resource_within_paid_commitment', {...ctx, metric, used:m[metric], committed});
    if (!m.campaign_unfinished_at_horizon) near(m[metric], committed, 1e-4, 'all_paid_campaign_resources_completed', {...ctx, metric});
  }
  const committedTokens = sum(purchases.map(p => sum(['astra_input','astra_output','terra_input','terra_output'].map(k => (p.kind === 'retention_purchase' ? register.incremental_retention_options : register.investment_campaigns)[p.action][k])) * p.quantity_multiplier));
  check(m.research_tokens <= committedTokens + 1e-4, 'research_tokens_within_paid_commitment', ctx);
  if (!m.campaign_unfinished_at_horizon) near(m.research_tokens, committedTokens, 1e-4, 'all_paid_campaign_tokens_completed', ctx);

  const completedById = new Map(completed.map(e => [e.id,e]));
  for (const e of events.filter(x => ['alpha_assessment','alpha_reassessment'].includes(x.kind))) {
    const a = e.assessment, initial = e.kind === 'alpha_assessment';
    if (initial) report.initial_alpha_assessments++; else report.retained_alpha_assessments++;
    const evidence = e.evidence;
    check(evidence.payment_basis === 'SIMULATED_LEDGER_RECEIPT' && evidence.paid_amount > 0, 'assessment_has_paid_simulated_receipt', {...ctx,id:e.id,month:e.month});
    check(evidence.acceptance_unit === 'component_test' && evidence.complete_project_test_executions === 0 && evidence.project_value_basis === 'MODEL_EXTRAPOLATION_FROM_COMPONENT_TESTS', 'component_tests_not_project_trials', {...ctx,id:e.id});
    const paidEvidence = activityById.get(evidence.paid_receipt_id);
    check(Boolean(paidEvidence) && paidEvidence.cash_paid && paidEvidence.month <= e.month, 'assessment_paid_receipt_resolves_to_activity', {...ctx,id:e.id,receipt:evidence.paid_receipt_id});
    if (paidEvidence) near(evidence.paid_amount, paidEvidence.cost_usd, 1e-5, 'assessment_paid_amount_matches_activity', {...ctx,id:e.id});
    if (initial) {
      const build = completedById.get(e.id);
      check(Boolean(build) && build.month === e.month, 'assessment_after_complete_paid_construction', {...ctx,id:e.id});
      if (build) near(evidence.paid_amount, build.paid_cost, 1e-5, 'initial_assessment_in_complete_campaign_bill', {...ctx,id:e.id});
    } else near(evidence.paid_amount, e.paid_cost, 1e-5, 'reassessment_paid_receipt_matches_event', {...ctx,id:e.id});
    if (a) {
      check(a.assessment_unit === 'component_test' && a.accepted_complete_deployments === 0, 'no_complete_project_acceptance_in_component_assessment', {...ctx,id:e.id});
      near(a.full_cycle_expected_net_alpha, a.expected_prospective_net_alpha - a.sunk_costs, 1e-5, 'alpha_full_cycle_cost_identity', {...ctx,id:e.id});
      const graphRecord = r.lifecycle.records[e.id];
      const origin = e.origin || graphRecord?.origin;
      check(Boolean(origin), 'assessment_origin_present', {...ctx,id:e.id});
      const excluded = origin?.kind === 'paid_job' ? origin.delivery_cost_already_charged : 0;
      near(a.job_delivery_cost_excluded_from_incremental_gate, excluded, 1e-5, 'admission_excludes_exact_already_charged_job_cost', {...ctx,id:e.id});
      near(a.construction_inclusive_residual_forecast, a.full_cycle_expected_net_alpha, 1e-5, 'historical_forecast_label_identity', {...ctx,id:e.id});
      check(a.historical_recovery_requires_separate_cash_ledger === true, 'forecast_not_historical_repayment', {...ctx,id:e.id});
      if (e.admitted) {
        report.admitted_alpha_assessments++;
        report.admitted_with_nonpositive_construction_inclusive_forecast += Number(a.full_cycle_expected_net_alpha <= 0);
        check(a.expected_prospective_net_alpha > 0, 'admitted_positive_prospective_alpha', {...ctx,id:e.id});
        if (initial) check(a.gate_context === 'initial_admission', 'initial_incremental_admission_context', {...ctx,id:e.id});
        else check(a.gate_context === 'retention_reassessment', 'retention_distinguished_from_new_alpha', {...ctx,id:e.id});
      }
      if (initial) {
        const build = completedById.get(e.id);
        if (build) near(a.sunk_costs, build.paid_cost, 1e-5, 'initial_retention_or_research_spend_stays_in_historical_forecast', {...ctx,id:e.id});
      }
    } else check(!e.admitted, 'no_admission_without_assessment', {...ctx,id:e.id});
  }
  const acquisitions = events.filter(e => e.kind === 'recipient_acquisition');
  report.charged_recipient_acquisitions += acquisitions.length;
  check(sum(acquisitions.map(e => e.paid_cost)) <= m.recipient_acquisition_cost + m.network_distribution_cost + 1e-5, 'all_observed_network_acquisitions_charged', ctx);
  const compositions = events.filter(e => e.kind === 'composition_checked');
  report.charged_compositions += compositions.length;
  near(sum(compositions.map(e => e.paid_cost)), m.network_composition_cost, 1e-5, 'all_composition_checks_charged', ctx);
  near(sum(events.filter(e => e.kind === 'alpha_reassessment').map(e => e.paid_cost)), m.beta_reevaluation_cost, 1e-5, 'all_paid_reassessments_reported', ctx);
  const groupKey = r.scenario + ':' + r.world;
  const group = groups.get(groupKey) || {};
  check(!group[r.diagnostic_arm], 'no_duplicate_diagnostic_history', ctx);
  group[r.diagnostic_arm] = {metrics:r.metrics,ledger:r.ledger,activities:r.activities.filter(e => e.ledger === 'B' && e.cost_usd > 0 || e.cost_key === 'investment_cost')}; groups.set(groupKey, group);
  if (group.frozen_beta && group.frozen_network && group.posterior_coherent_network) {
    report.paired_worlds++;
    const a = group.frozen_beta;
    for (const arm of ['frozen_network','posterior_coherent_network']) {
      const b = group[arm];
      const first = Math.min(...b.activities.filter(e => e.ledger === 'B' && e.cost_usd > 0 || e.cost_key === 'investment_cost').map(e => e.month), Infinity);
      for (let i = 0; i < a.ledger.length; i++) {
        if (a.ledger[i].month < first)
          check(JSON.stringify(a.ledger[i]) === JSON.stringify(b.ledger[i]), 'paired_before_any_retention_or_research_cost_identity', {...ctx, diagnostic_arm: arm, month: a.ledger[i].month});
      }
    }
    const old = group.frozen_network.metrics, changed = group.posterior_coherent_network.metrics;
    report.diagnostic_paired_values.push({scenario:r.scenario,world:r.world,
      frozen_network_minus_beta:old.net_profit-a.metrics.net_profit,
      posterior_network_minus_beta:changed.net_profit-a.metrics.net_profit,
      posterior_network_minus_frozen:changed.net_profit-old.net_profit,
      posterior_quality_adjusted_minus_beta:changed.quality_adjusted_profit-a.metrics.quality_adjusted_profit,
      posterior_true_projects_minus_beta:changed.true_accepted_projects-a.metrics.true_accepted_projects,
      posterior_retention_cost:changed.retention_cost,
      posterior_optional_research_cost:changed.investment_cost,
      posterior_useful_recipient_projects:changed.retention_useful_fresh_projects,
      posterior_retention_seed_funded:changed.retention_seed_funded,
      posterior_retention_operating_funded:changed.retention_operating_funded});
    groups.delete(groupKey);
  }
  const key = r.scenario + ':' + r.diagnostic_arm;
  report.scenario_totals[key] ||= {histories: 0, true_projects: 0, false_passes: 0, complete_cost: 0, net_profit: 0};
  const total = report.scenario_totals[key];
  total.histories++; total.true_projects += m.true_accepted_projects; total.false_passes += m.false_passes;
  total.complete_cost += complete; total.net_profit += m.net_profit;
  if (r.policy === 'optimized_beta') {
    const agg = pooled.get(r.scenario) || {histories: 0, metrics: {}};
    agg.histories++;
    for (const [key, value] of Object.entries(m)) if (typeof value === 'number') agg.metrics[key] = (agg.metrics[key] || 0) + value;
    pooled.set(r.scenario, agg);
  }
}
for (const file of files) {
  const stream = fs.createReadStream(path.join(resultsDir, file)).pipe(zlib.createGunzip());
  for await (const line of readline.createInterface({input: stream, crlfDelay: Infinity})) if (line) audit(JSON.parse(line));
}
check(groups.size === 0, 'complete_counterfactual_triplets', {remaining: groups.size});
const mapping = {base: 'central', conservative: 'conservative', stress: 'favorable'};
if (Object.values(mapping).every(s => pooled.has(s) && pooled.get(s).metrics.true_accepted_projects > 0)) {
  const fact = (value, description) => ({value, basis: 'estimated', reference: 'SIMULATED retrospective normalized allocation: ' + description});
  const scenarios = Object.entries(mapping).map(([name, actual]) => {
    const m = pooled.get(actual).metrics, n = m.true_accepted_projects;
    const stages = {preparation: 0, planning: 0, execution: m.production_cost,
      verification: 0, correction: m.correction_cost, packaging: m.storage_cost,
      reporting: m.recipient_acquisition_cost + m.network_access_cost + m.network_distribution_cost + m.network_composition_cost, recovery: m.recovery_cost};
    const business = sum(businessKeys.map(k => val(m, k))) + m.unpaid_obligations - val(m,'refund_obligations_unpaid');
    const investments = sum(investmentKeys.map(k => val(m, k)));
    const hours = actual === 'conservative' ? 112 : actual === 'favorable' ? 320 : 196;
    return {name, capacityRequestsPerMonth: fact(1, 'one pooled true accepted project'),
      utilizationBps: fact(10000, 'normalization only'), acceptanceBps: fact(10000, 'not an assumed success rate'),
      attemptsPerRequestPpm: fact(1000000, 'all failure costs already embedded'),
      operations: AUTOMATED_STAGES.map(stage => ({id: stage, stage, frequency: 'request',
        unitsPerOccurrencePpm: fact(1000000, 'unit allocation'),
        unitCostMicros: fact(micros(stages[stage] / n), stage + ' pooled costs / true outcomes'),
        implementation: 'modeled'})),
      residual: [],
      monthly: [{id: 'business', kind: 'business', amountMicros: fact(micros(business / n), 'all pooled business and unpaid costs'), allocationBps: fact(10000, 'complete allocation')}],
      investments: [{id: 'lifecycle', kind: 'development', amountMicros: fact(micros(investments / n), 'all setup, campaign and upkeep costs'), allocationBps: fact(10000, 'complete allocation'), amortizationMonths: fact(1, 'whole-horizon normalization')}],
      humanBaseline: {minutesPerAccepted: fact(hours * 60, 'assumed full-package team hours'),
        hourlyCostMicros: fact(micros(c.scenarios[actual].human_reference / hours), 'published-rate / assumed-hours reference')},
    };
  });
  const costs = evaluateAutomatedCosts({schema: 'alpha-automated-costs/v1', offeringId: 'vof-complete-history-normalization', currency: 'USD', scenarios});
  for (const row of costs.scenarios) {
    const m = pooled.get(mapping[row.name]).metrics;
    near(row.costs.fullyLoadedMicrosPerAccepted / 1e6, m.fully_allocated_cost_total / m.true_accepted_projects, .00002, 'canonical_pooled_accepted_cost', {scenario: mapping[row.name]});
  }
  report.automated_cost_reconciliation = {mapping, raw_denominators: Object.fromEntries([...pooled].map(([s, a]) => [s, {histories: a.histories, true_projects: a.metrics.true_accepted_projects, false_passes: a.metrics.false_passes}])), result: costs};
}
report.status = report.failures.length ? 'FAIL' : 'PASS';
fs.mkdirSync(path.dirname(output), {recursive: true});
fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({status: report.status, histories: report.histories, months: report.months, purchases: report.purchases, paired_worlds: report.paired_worlds, failures: report.failures.length, output}));
if (report.failures.length) process.exitCode = 1;
