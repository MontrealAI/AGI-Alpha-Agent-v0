// SPDX-License-Identifier: Apache-2.0
// Post-output independent arithmetic audit. Frozen model and results are unchanged.
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {simulateLegal} from '../economics/legal-market.mjs';
import {randomDraw} from '../economics/inherited/src/market.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const econ = path.join(root, 'economics');
const read = name => JSON.parse(readFileSync(path.join(econ, name), 'utf8'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const sum = values => values.reduce((a, b) => a + b, 0);
const campaign = read('results/primary-v2/campaign.json');
const production = read('production-input.json');
const params = read('parameters.json');
const freeze = read('source-freeze.json');
const problems = [];
let assertions = 0;
const check = (condition, context) => { assertions++; if (!condition) problems.push(context); };
for (const file of freeze.files)
  check(hash(readFileSync(path.join(econ, file.path))) === file.sha256, 'FROZEN_SOURCE:' + file.path);
const provenance = read('results/primary-v2/input-provenance.json');
for (const [key, name] of [['productionSHA256', 'production-input.json'], ['sourceSHA256', 'legal-market.mjs'], ['parametersSHA256', 'parameters.json']])
  check(hash(readFileSync(path.join(econ, name))) === provenance[key], 'INPUT_PROVENANCE:' + key);
check(readFileSync(path.join(econ, 'parameters.json')).equals(readFileSync(path.join(econ, 'history/model-v1/parameters.json'))), 'SCENARIOS_CHANGED_AFTER_V1');

const strategies = ['baseline', 'reinvest', 'retainedFromStart', 'fullFromStart', 'conventional'];
const aggregate = Object.fromEntries(strategies.map(s => [s, {worlds: 0, attempts: 0, accepted: 0, rejected: 0, declines: 0, alternatives: 0, collections_cents: 0, profit_cents: 0, positive_profit_worlds: 0, investments: 0}]));
for (const world of campaign.worlds) {
  const scenario = params.scenario_definitions.find(s => s.id === world.scenario);
  const config = {...params.config, ...scenario.changes};
  for (const strategy of strategies) {
    const s = world[strategy], tag = world.scenario + ':' + world.seed + ':' + strategy;
    check(s.allProviderCostsCents === sum(Object.values(s.providerCostCategoriesCents)), 'COST_SUM:' + tag);
    check(s.cashOperatingProfitCents === s.simulatedCollectionsCents - s.allProviderCostsCents, 'OPERATING_PROFIT:' + tag);
    check(s.remainingSeedPlusEarnedCashCents === config.initialSeedCents + s.cashOperatingProfitCents, 'SEED_CASH:' + tag);
    check(s.availableOperatingSurplusCents === Math.max(0, s.cashOperatingProfitCents - s.heldReserveCents - s.unpaidObligationsCents), 'EARNED_SURPLUS:' + tag);
    check(s.heldReserveCents === config.reserveCents, 'RESERVE_ONCE:' + tag);
    check(s.unpaidObligationsCents === 0, 'NO_UNPAID_MODEL_OBLIGATIONS:' + tag);
    check(s.providerAttempts === s.simulatedAccepted + s.simulatedRejected, 'ATTEMPT_SUM:' + tag);
    check(s.opportunities === s.providerAttempts + s.buyerDeclines + s.alternativeChoices, 'BUYER_CHOICE_SUM:' + tag);
    check(s.customerInvoicedCents === s.simulatedAccepted * config.offerPriceCents, 'INVOICED_ONLY_ACCEPTED:' + tag);
    check(s.simulatedCollectionsCents <= s.customerInvoicedCents, 'COLLECTIONS_BOUND:' + tag);
    check(s.observedCollectionsCents === 0 && s.historicalResearchCostCents === null && s.fullyAllocatedProfitCents === null, 'OBSERVED_UNKNOWN_BOUNDARY:' + tag);
    if (strategy !== 'reinvest') {
      const construction = strategy === 'baseline' ? 0 : config.capabilityConstructionCents + config.capabilityFailedConstructionCents + (strategy === 'fullFromStart' ? config.secondCapabilityConstructionCents + config.secondCapabilityFailedConstructionCents : 0);
      check(s.providerCostCategoriesCents.capability === construction, 'CONSTRUCTION_ONCE:' + tag);
    }
    const a = aggregate[strategy]; a.worlds++;
    for (const [key, field] of [['attempts','providerAttempts'],['accepted','simulatedAccepted'],['rejected','simulatedRejected'],['declines','buyerDeclines'],['alternatives','alternativeChoices'],['collections_cents','simulatedCollectionsCents'],['profit_cents','cashOperatingProfitCents']]) a[key] += s[field];
    a.positive_profit_worlds += Number(s.cashOperatingProfitCents > 0);
    a.investments += Number(s.firstInvestmentFunded);
  }
}
for (const a of Object.values(aggregate)) a.means = Object.fromEntries(['attempts','accepted','rejected','declines','alternatives','collections_cents','profit_cents'].map(k => [k, a[k] / a.worlds]));

// One existing high-attempt world is replayed to expose job-level bookkeeping.
const selected = campaign.worlds.reduce((a, b) => b.reinvest.providerAttempts > a.reinvest.providerAttempts ? b : a);
const changes = params.scenario_definitions.find(s => s.id === selected.scenario).changes;
const trace = simulateLegal(production, changes, selected.seed, 'reinvest');
check(JSON.stringify(trace.summary) === JSON.stringify(selected.reinvest), 'SINGLE_REPLAY_MATCHES_STORED_SUMMARY');
const byCase = new Map(production.records.map(row => [row.arm + ':' + row.case_id, row]));
const attempts = trace.jobs.filter(j => j.choice === 'agi-alpha');
const invoices = attempts.filter(j => j.acceptedSimulated);
const paid = invoices.filter(j => randomDraw(selected.seed, 'collection', j.week, j.buyer) < trace.config.collectionProbability);
for (const job of attempts) {
  const actual = byCase.get(job.stage + ':' + job.case_id);
  check(job.technicalCasePassed === actual.accepted_deterministic, 'JOB_TECHNICAL_BINDING:' + job.case_id);
  check(actual.accepted_deterministic || (!job.acceptedSimulated && job.invoiceCents === 0), 'FAILED_TECHNICAL_INVOICE:' + job.case_id);
  check(job.acceptedSimulated || job.invoiceCents === 0, 'REJECTED_INVOICE:' + job.case_id);
  check(job.deliveryCostCents > 0, 'FAILED_ATTEMPT_COST_PRESERVED:' + job.case_id);
}
check(sum(paid.map(j => j.invoiceCents)) === trace.summary.simulatedCollectionsCents, 'PAID_INVOICES_RECONCILE');
check(sum(attempts.map(j => j.deliveryCostCents)) === trace.summary.providerCostCategoriesCents.delivery, 'JOB_DELIVERY_COSTS_RECONCILE');
let runningCollections = 0, runningCost = 0;
for (const week of trace.weekly) {
  const due = sum(paid.filter(j => j.week + trace.config.paymentDelayWeeks === week.week).map(j => j.invoiceCents));
  check(week.collections === due, 'COLLECTION_DELAY:' + week.week);
  runningCollections += week.collections;
  runningCost += week.delivery + week.business + week.capability + week.maintenance;
  check(week.cashAfterReserveCents === trace.config.initialSeedCents + runningCollections - runningCost - trace.config.reserveCents, 'WEEKLY_CASH:' + week.week);
  check(week.earnedAvailableCents === Math.max(0, runningCollections - runningCost - trace.config.reserveCents), 'WEEKLY_EARNED_EXCLUDES_SEED:' + week.week);
}
const actual = campaign.actualLedger.summary.observed;
check(actual.revenue === 0 && actual.fullCost === null && actual.availableSurplus === null, 'ACTUAL_LEDGER_NO_KNOWN_SURPLUS');
const out = {
  schema: 'independent-economic-accounting-audit/v1', created_at: new Date().toISOString(),
  audit_basis: 'Post-output arithmetic and boundary review; no parameters, frozen model, campaign results or acceptance labels modified.',
  source_freeze_sha256: hash(readFileSync(path.join(econ,'source-freeze.json'))),
  assertions, problems, accepted_arithmetic_audit: problems.length === 0,
  stored_summaries_checked: campaign.worlds.length * strategies.length,
  strategy_aggregates: aggregate,
  single_replay: {
    scenario: selected.scenario, seed: selected.seed, summary_matches_stored: JSON.stringify(trace.summary) === JSON.stringify(selected.reinvest),
    opportunities: trace.summary.opportunities, attempts: attempts.length,
    unique_modeled_customers: new Set(attempts.map(j => j.buyer)).size,
    configured_prospective_buyers: trace.config.buyers,
    invoices: invoices.length, paid_invoices: paid.length,
    technically_failed_attempts: attempts.filter(j => !j.technicalCasePassed).length,
    failed_technical_invoices: attempts.filter(j => !j.technicalCasePassed && j.invoiceCents !== 0).length,
    simulated_collections_cents: trace.summary.simulatedCollectionsCents,
    costs_cents: trace.summary.allProviderCostsCents,
    operating_profit_cents: trace.summary.cashOperatingProfitCents,
    available_earned_surplus_cents: trace.summary.availableOperatingSurplusCents,
    actual_collections_cents: 0,
    note: 'Modeled customer identities and adoption are simulated, not evidence of actual customers.'
  },
  remaining_limits: [
    'Frozen v2 emitted limits contain stale wording: technical passes affect correction burden AND the acceptance/invoice gate.',
    'Buyer offer quality uses an assumed conditional professional-acceptance probability without measured technical pass-rate adjustment; demand is an optimistic perceived-quality scenario, not empirically calibrated overall reliability.',
    'No first or second earned investment occurred, so observed campaign paths cannot demonstrate successful repayment or succession; those gates are code/control properties only.',
    'All reserves, business costs, review/correction times and payment behavior are assumptions; zero unpaid provider obligations is a model cash-first assumption.',
    'Historical research costs are unknown; modeled fully allocated cost does not establish full historical cost recovery.',
    'The reference/campaign monetary outcomes remain simulations. No professional acceptance, actual customers, collections or viable commercial result is observed.'
  ]
};
writeFileSync(path.join(root,'evidence/economics-independent-audit.json'), JSON.stringify(out,null,2)+'\n');
writeFileSync(path.join(root,'evidence/economics-independent-single-replay.json'), JSON.stringify(trace,null,2)+'\n');
console.log(JSON.stringify({assertions, problems, stored_summaries_checked:out.stored_summaries_checked, single_replay:out.single_replay}));
if (problems.length) process.exitCode = 1;
