// SPDX-License-Identifier: Apache-2.0
// Research-only adapter: no payment, credential, execution-authority or scheduler API.
import {
  randomDraw, chooseBuyer, createFirm, expense, payBills, collect, liquidity,
  unpaid, receivable, canonicalProjection
} from './inherited/upstream/src/market-adapter-primitives.mjs';
import { generatedResources } from './inherited/continuation.mjs';
import { calculateInvestment } from './inherited/upstream/canonical/shadow-ledger.mjs';

export const SCHEMA = 'capability-advantage-network-market/v1';
export const ARMS = Object.freeze(['A', 'B', 'C', 'D']);
const HASH = /^[a-f0-9]{64}$/;
const assert = (condition, message) => { if (!condition) throw Error(message); };
const clone = value => JSON.parse(JSON.stringify(value));
const sum = rows => rows.reduce((a, b) => a + b, 0);
const cents = value => Math.max(0, Math.round(value));
const costNames = ['discovery', 'construction', 'failedCandidates', 'validation', 'integration',
  'modelAndTools', 'residualAttention', 'maintenance', 'revalidation'];

export function validateCalibration(raw) {
  const value = clone(raw);
  assert(value.schema === 'capability-advantage-calibration/v1', 'Wrong calibration schema');
  assert(value.basis === 'EXECUTED_RESEARCH_COHORT_ONLY', 'Calibration must name executed research scope');
  assert(value.actual_customer_collections_cents === 0, 'Actual collections remain zero');
  assert(value.actual_total_cost_cents === null, 'Unknown complete actual cost must remain null');
  assert(Array.isArray(value.families) && value.families.length === 3, 'Exactly three frozen generations required');
  const ids = new Set();
  for (const [index, family] of value.families.entries()) {
    assert(family.id === `G${index + 1}` && !ids.has(family.id), 'Generation order required');
    assert(family.tested === true && HASH.test(family.asset_sha256) && HASH.test(family.acceptance_sha256),
      'Executed asset and acceptance identity required');
    assert(Array.isArray(family.prerequisites) && family.prerequisites.every(p => ids.has(p)), 'Dependencies must precede child');
    assert(family.trials.length >= 2, 'Multiple fresh cases required per generation');
    const trials = new Set();
    for (const trial of family.trials) {
      assert(typeof trial.task_id === 'string' && !trials.has(trial.task_id), 'Unique case identities required');
      trials.add(trial.task_id);
      assert(['standard', 'hard'].includes(trial.difficulty), 'Explicit difficulty stratum required');
      for (const method of ['before', 'reconstructed', 'shared', 'conventional']) {
        const row = trial[method];
        if (method === 'before' && row?.accepted === null && row?.cpu_seconds === null && row?.basis === 'NOT_RUN') continue;
        assert(typeof row?.accepted === 'boolean', `Executed acceptance required: ${method}`);
        assert(Number.isFinite(row.cpu_seconds) && row.cpu_seconds >= 0, 'Measured CPU seconds required');
      }
    }
    for (const key of ['construction_seconds', 'failed_candidate_seconds', 'validation_seconds',
      'integration_seconds', 'conventional_construction_seconds', 'independent_reconstruction_seconds']) {
      assert(Number.isFinite(family.resources[key]) && family.resources[key] >= 0, `Resource measurement required: ${key}`);
    }
    ids.add(family.id);
  }
  for (const key of ['registry_cpu_seconds', 'graph_cpu_seconds', 'registry_build_seconds', 'graph_build_seconds'])
    assert(Number.isFinite(value.retrieval[key]) && value.retrieval[key] >= 0, `Retrieval measurement required: ${key}`);
  for (const row of value.resource_allocation ?? []) {
    assert(typeof row.allocation_basis === 'string' && row.allocation_basis.length > 0, 'Allocation basis required');
    const allocated = sum(value.families.map(f => f.resources[row.field]));
    assert(Math.abs(allocated - row.total_seconds) < 0.000001, `Resource interval allocated more than once: ${row.field}`);
  }
  return value;
}

export const COST_SCHEDULES = Object.freeze([
  {id: 'low', basis: 'SCENARIO_NOT_INVOICE_OR_EMPIRICAL_BOUND', resource_hourly_cents: 100,
    compute_hourly_cents: 100, model_tools_cents_per_build: 100, audit_minutes_per_build: 5,
    attention_hourly_cents: 3000, discovery_minutes_per_build: 2, maintenance_cents_week: 10,
    revalidation_cents: 50, residual_minutes_per_job: 0.5, common_initial_cents: 5000,
    common_weekly_cents: 200, historical_research_cents: 36152},
  {id: 'reference', basis: 'SCENARIO_NOT_INVOICE_OR_EMPIRICAL_BOUND', resource_hourly_cents: 1000,
    compute_hourly_cents: 100, model_tools_cents_per_build: 1000, audit_minutes_per_build: 20,
    attention_hourly_cents: 6000, discovery_minutes_per_build: 10, maintenance_cents_week: 50,
    revalidation_cents: 250, residual_minutes_per_job: 2, common_initial_cents: 5000,
    common_weekly_cents: 200, historical_research_cents: 36152},
  {id: 'high', basis: 'SCENARIO_NOT_INVOICE_OR_EMPIRICAL_BOUND', resource_hourly_cents: 10000,
    compute_hourly_cents: 100, model_tools_cents_per_build: 10000, audit_minutes_per_build: 60,
    attention_hourly_cents: 12000, discovery_minutes_per_build: 30, maintenance_cents_week: 250,
    revalidation_cents: 1000, residual_minutes_per_job: 5, common_initial_cents: 5000,
    common_weekly_cents: 200, historical_research_cents: 36152}
]);

export function balancedPanel() {
  const factors = {
    network_size: [4, 16, 64], demand_multiplier: [0, 0.25, 1, 4], copying_delay_weeks: [0, 4, 12],
    initial_overlap: [0.2, 0.8], integration_cents: [0, 250], diverse: [false, true],
    harder_mix: [false, true], reconstruction_factor: [0.1, 1],
    acquisition_failure_probability: [0, 0.2], useful_life_weeks: [8, 26],
    stale_probability: [0, 0.1], choice_model: ['deterministic', 'logit'],
    posted_price_cents: [500, 2000, 8000], payment_delay_weeks: [2, 13],
    contribution_reward_share: [0, 0.25, 0.5]
  };
  const panel = Array.from({length: 48}, (_, i) => ({id: `structural-${String(i + 1).padStart(2, '0')}`}));
  for (const [name, levels] of Object.entries(factors)) {
    const order = Array.from({length: 48}, (_, i) => i).sort((a, b) =>
      randomDraw(26026, 'design', name, a) - randomDraw(26026, 'design', name, b));
    for (let i = 0; i < 48; i++) panel[order[i]][name] = levels[i % levels.length];
  }
  assert(new Set(panel.map(({id, ...row}) => JSON.stringify(row))).size === 48, 'Panel duplicates');
  return panel;
}

export function buildCost(family, schedule, arm, condition, calibration) {
  const r = family.resources;
  const seconds = arm === 'D' ? r.conventional_construction_seconds : r.construction_seconds;
  const retrieval = family.id !== 'G1' ? 0 : arm === 'B' ? calibration.retrieval.registry_build_seconds :
    arm === 'C' ? calibration.retrieval.graph_build_seconds : 0;
  const research = seconds * condition.reconstruction_factor;
  const rows = {
    discovery: cents(schedule.discovery_minutes_per_build * schedule.resource_hourly_cents / 60),
    construction: cents((research + retrieval) * schedule.resource_hourly_cents / 3600),
    failedCandidates: cents(r.failed_candidate_seconds * schedule.resource_hourly_cents / 3600),
    validation: cents(r.validation_seconds * schedule.resource_hourly_cents / 3600),
    integration: cents(r.integration_seconds * schedule.resource_hourly_cents / 3600),
    modelAndTools: schedule.model_tools_cents_per_build,
    residualAttention: cents(schedule.audit_minutes_per_build * schedule.attention_hourly_cents / 60),
    maintenance: 0, revalidation: 0
  };
  return {categories: rows, total_cents: sum(Object.values(rows)), basis: schedule.basis,
    resource_interpretation: 'Elapsed research-resource seconds priced by declared tariff; not measured human labor or a token bill.'};
}

function ownCost(family, schedule, condition, conventional = false) {
  const seconds = conventional ? family.resources.conventional_construction_seconds : family.resources.independent_reconstruction_seconds;
  return cents(seconds * condition.reconstruction_factor *
    schedule.resource_hourly_cents / 3600) + schedule.model_tools_cents_per_build +
    cents(family.resources.validation_seconds * schedule.resource_hourly_cents / 3600);
}

function variableCost(trial, method, schedule, retrieval = 0) {
  assert(trial[method].cpu_seconds !== null, 'Unknown computation is not free');
  return cents((trial[method].cpu_seconds + retrieval) * schedule.compute_hourly_cents / 3600) +
    cents(schedule.residual_minutes_per_job * schedule.attention_hourly_cents / 60);
}

function configFor(condition) {
  return {weeks: 52, initialCashCents: 100000, reserveCents: 20000, expenseDelayWeeks: 0,
    paymentDelayWeeks: condition.payment_delay_weeks ?? 2, refundDelayWeeks: 1, paymentProbability: 0.98,
    investmentCostBasis: 'full-history', historicalCostTiming: 'opening',
    choiceModel: condition.choice_model, logitScaleCents: 1200};
}

function initialAgents(condition, seed) {
  return Array.from({length: condition.network_size}, (_, i) => {
    const prior = ['G1', 'G2', 'G3'].filter(g => randomDraw(seed, 'prior', condition.diverse ? i : 0, g) < condition.initial_overlap);
    return {id: `simulated-recipient-${i}`, own: new Set(prior), conventional: new Set(prior),
      counterfactual: {own: new Set(prior), conventional: new Set(prior), acquired: new Set()},
      acquired: new Set(), usefulTransfers: 0};
  });
}

function quoteRoute(arm, agent, family, trial, state, schedule, condition, calibration) {
  const routes = [];
  const pool = family.trials.filter(t => t.difficulty === trial.difficulty);
  const probability = method => pool.some(t => t[method].accepted === null) ? 0 : sum(pool.map(t => Number(t[method].accepted))) / pool.length;
  const averageCost = (method, retrieval = 0) => cents(sum(pool.map(t => variableCost(t, method, schedule, retrieval))) / pool.length);
  if (probability('before') > 0) routes.push({id: 'ordinary-tools', method: 'before', fixed: 0,
    unit: variableCost(trial, 'before', schedule), forecastUnit: averageCost('before'), quality: probability('before')});
  if (probability('reconstructed') > 0) routes.push({id: 'independent-reconstruction', method: 'reconstructed',
    fixed: agent.own.has(family.id) ? 0 : ownCost(family, schedule, condition),
    unit: variableCost(trial, 'reconstructed', schedule), forecastUnit: averageCost('reconstructed'), quality: probability('reconstructed')});
  if (probability('conventional') > 0) routes.push({id: 'conventional-reconstruction', method: 'conventional',
    fixed: agent.conventional.has(family.id) ? 0 : ownCost(family, schedule, condition, true),
    unit: variableCost(trial, 'conventional', schedule), forecastUnit: averageCost('conventional'), quality: probability('conventional')});
  const shared = state.assets[family.id];
  if (shared?.active && ['B', 'C', 'D'].includes(arm)) {
    const method = arm === 'D' ? 'conventional' : 'shared';
    const retrieval = arm === 'B' ? calibration.retrieval.registry_cpu_seconds :
      arm === 'C' ? calibration.retrieval.graph_cpu_seconds : 0;
    if (probability(method) > 0) routes.push({id: arm === 'D' ? 'conventional-service' : 'validated-acquisition', method,
      fixed: agent.acquired.has(family.id) ? 0 : condition.integration_cents,
      unit: variableCost(trial, method, schedule, retrieval), forecastUnit: averageCost(method, retrieval), quality: probability(method)});
  }
  routes.sort((a, b) => (a.fixed + a.forecastUnit) / a.quality - (b.fixed + b.forecastUnit) / b.quality || a.id.localeCompare(b.id));
  return routes[0] ?? null;
}

function strongestIndependentCost(agent, family, trial, schedule, condition) {
  const costs = [];
  const pool = family.trials.filter(t => t.difficulty === trial.difficulty);
  for (const method of ['before', 'reconstructed', 'conventional']) {
    const probability = pool.some(t => t[method].accepted === null) ? 0 : sum(pool.map(t => Number(t[method].accepted))) / pool.length;
    if (!probability) continue;
    const fixed = method === 'before' ? 0 : method === 'reconstructed' ?
      (agent.own.has(family.id) ? 0 : ownCost(family, schedule, condition)) :
      (agent.conventional.has(family.id) ? 0 : ownCost(family, schedule, condition, true));
    costs.push((sum(pool.map(t => variableCost(t, method, schedule))) / pool.length + fixed) / probability);
  }
  return costs.length ? Math.min(...costs) : null;
}

function maybeBuild(arm, family, week, state, firm, config, schedule, condition, calibration, seed, decisions) {
  if (arm === 'A' || state.assets[family.id] || family.prerequisites.some(id => !state.assets[id]?.active)) return;
  const release = (Number(family.id.slice(1)) - 1) * 16;
  if (week < release || week >= config.weeks - 2) return;
  const cost = buildCost(family, schedule, arm, condition, calibration);
  const horizon = Math.min(condition.useful_life_weeks, config.weeks - week - 1);
  const recent = state.opportunities.filter(x => x.family === family.id && x.week >= Math.max(0, week - 8) && x.week < week);
  const forecast = Math.floor(recent.length / Math.max(1, Math.min(8, week)) * horizon * 0.5);
  const missingRecipients = state.agents.filter(agent => !agent.own.has(family.id) && !agent.conventional.has(family.id)).length;
  const newRecipients = Math.min(missingRecipients, forecast);
  const ordinaryEnough = family.trials.every(t => t.before.accepted);
  const perNew = ordinaryEnough ? 0 : Math.min(ownCost(family, schedule, condition),
    ownCost(family, schedule, condition, true)) - condition.integration_cents;
  const upkeep = horizon * schedule.maintenance_cents_week + Math.floor(horizon / 8) * schedule.revalidation_cents;
  const forecastBenefit = newRecipients * Math.max(0, perNew) *
    (1 - condition.acquisition_failure_probability) - cost.total_cents - upkeep;
  const creatorReservation = cost.categories.validation + cost.categories.integration + cost.categories.discovery;
  const collectibleShare = Math.min(1, condition.copying_delay_weeks / Math.max(1, horizon));
  const forecastCreatorReward = cents(newRecipients * Math.max(0, perNew) *
    (condition.contribution_reward_share ?? 0.25) * collectibleShare * (1 - condition.acquisition_failure_probability));
  const contributionAllowed = arm === 'D' || forecastCreatorReward >= creatorReservation;
  const funds = generatedResources(firm, config);
  const available = family.id === 'G1' ? Math.max(0, liquidity(firm, config)) : funds.availableCents;
  const isSeed = family.id === 'G1';
  const admitted = forecastBenefit > 0 && available >= cost.total_cents && contributionAllowed;
  const record = {week, arm, family: family.id, action: admitted ? 'construct' : 'retain-alternatives',
    asset_sha256: family.asset_sha256, acceptance_sha256: family.acceptance_sha256,
    fixed_cost: cost, forecast_uses: forecast, forecast_new_recipients: newRecipients,
    forecast_net_cents: forecastBenefit, funding: isSeed ? 'seed' : 'operating-generated',
    available_cents: available, generated_resources: funds,
    contribution_policy: {forecast_reward_cents: forecastCreatorReward, reservation_cost_cents: creatorReservation,
      share: condition.contribution_reward_share ?? 0.25, copied_fee_fraction: 1 - collectibleShare,
      willing_to_contribute: contributionAllowed, transfer_is_internal: true},
    reasons: [...(forecastBenefit <= 0 ? ['no forecast complete-cost benefit'] : []),
      ...(available < cost.total_cents ? ['insufficient current permitted resources'] : []),
      ...(!contributionAllowed ? ['creator rejects contribution reward below incremental reservation cost'] : [])]};
  decisions.push(record);
  if (!admitted) return;
  for (const [category, amount] of Object.entries(cost.categories)) if (amount) {
    expense(firm, week, 'capability', amount, week, `capability:${family.asset_sha256}:${category}`);
  }
  payBills(firm, week, config);
  assert(!firm.insolvent && firm.cashCents >= config.reserveCents, 'Construction violated finite funding boundary');
  const failed = randomDraw(seed, 'construction-integration', family.id) < condition.acquisition_failure_probability;
  state.assets[family.id] = {active: false, builtWeek: week, availableWeek: week + 1,
    expiresWeek: week + 1 + condition.useful_life_weeks, failed, cost: cost.total_cents,
    upkeep: 0, uses: 0, additionalAccepted: 0, avoided: 0, funding: record.funding};
  record.failed = failed;
}

export function simulateNetwork(rawCalibration, condition, schedule, seed, arm, options = {}) {
  assert(ARMS.includes(arm), 'Unknown comparison arm');
  const calibration = options.validated ? rawCalibration : validateCalibration(rawCalibration);
  const config = configFor(condition), firm = createFirm('enterprise', config.initialCashCents);
  const agents = initialAgents(condition, seed), state = {assets: {}, opportunities: [], agents};
  const decisions = [], jobs = [], transfers = [], buyerChoices = [], balances = [], contributionAllocations = [];
  const competitors = {cash: 50000, copied: new Set(), copyingCosts: 0};
  const buyerRetained = new Map();
  const buyers = Math.max(4, Math.min(40, condition.network_size));
  const maxJobsWeek = Math.min(64, condition.network_size * 2);
  expense(firm, 0, 'business', schedule.common_initial_cents, 0, 'SCENARIO common setup');
  expense(firm, 0, 'capability', schedule.historical_research_cents, 0,
    'upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing');
  payBills(firm, 0, config);
  for (let week = 0; week <= 52 + config.paymentDelayWeeks + config.refundDelayWeeks + 1; week++) {
    collect(firm, week, config); payBills(firm, week, config);
    for (const family of calibration.families) {
      const asset = state.assets[family.id];
      if (asset) asset.active = !asset.failed && week >= asset.availableWeek && week < asset.expiresWeek &&
        !firm.insolvent && family.prerequisites.every(id => state.assets[id]?.active);
    }
    if (week < 52 && !firm.insolvent) {
      expense(firm, week, 'business', schedule.common_weekly_cents, week, 'SCENARIO recurring common overhead');
      for (const [id, asset] of Object.entries(state.assets)) if (asset.active) {
        let amount = schedule.maintenance_cents_week;
        if ((week - asset.availableWeek + 1) % 8 === 0) amount += schedule.revalidation_cents;
        expense(firm, week, 'maintenance', amount, week, `capability:${id}:maintenance/revalidation`);
        asset.upkeep += amount;
        if (!competitors.copied.has(id) && week >= asset.availableWeek + condition.copying_delay_weeks) {
          const family = calibration.families.find(f => f.id === id);
          const copyingCost = ownCost(family, schedule, condition);
          if (competitors.cash >= copyingCost) { competitors.cash -= copyingCost;
            competitors.copyingCosts += copyingCost; competitors.copied.add(id); }
        }
      }
      payBills(firm, week, config);
      for (const family of calibration.families) if (Number(family.id.slice(1)) <= (options.maxSharedGeneration ?? 3))
        maybeBuild(arm, family, week, state, firm, config, schedule, condition, calibration, seed, decisions);
      let attempted = 0;
      for (let buyerId = 0; buyerId < buyers; buyerId++) {
        const p = Math.min(1, 0.25 * condition.demand_multiplier);
        if (randomDraw(seed, 'arrival', week, buyerId) >= p || attempted >= maxJobsWeek) continue;
        const maxGeneration = Math.min(3, Math.floor(week / 16) + 1);
        const family = calibration.families[Math.floor(randomDraw(seed, 'family', week, buyerId) * maxGeneration)];
        const trials = family.trials.filter(t => t.difficulty === (condition.harder_mix ? 'hard' : 'standard'));
        const pool = trials.length ? trials : family.trials;
        const trial = pool[Math.floor(randomDraw(seed, 'trial', week, buyerId) * pool.length)];
        const agentIndex = condition.diverse ? Math.floor(randomDraw(seed, 'agent', week, buyerId) * agents.length) :
          buyerId % agents.length;
        const agent = agents[agentIndex];
        const id = `w${week}-b${buyerId}`;
        state.opportunities.push({week, id, family: family.id, agent: agent.id});
        let route = quoteRoute(arm, agent, family, trial, state, schedule, condition, calibration);
        if (route && liquidity(firm, config) < route.fixed + route.unit) route = null;
        const baseAlternative = strongestIndependentCost(agent.counterfactual, family, trial, schedule, condition);
        const counterfactualRoute = quoteRoute('A', agent.counterfactual, family, trial, state, schedule, condition, calibration);
        const key = `${buyerId}:${family.id}`, ownBuyer = buyerRetained.has(key);
        const probability = method => pool.some(t => t[method].accepted === null) ? 0 : sum(pool.map(t => Number(t[method].accepted))) / pool.length;
        const avgUnit = method => sum(pool.map(t => variableCost(t, method, schedule))) / pool.length;
        const diyRoutes = ['before', 'conventional'].filter(method => probability(method) > 0).map(method => ({method,
          quality: probability(method), cost: avgUnit(method) + (method === 'before' || ownBuyer ? 0 : ownCost(family, schedule, condition, true))}));
        diyRoutes.sort((a, b) => a.cost / a.quality - b.cost / b.quality);
        const diy = diyRoutes[0];
        const posted = condition.posted_price_cents ?? 2000;
        const buyer = {valueCents: 5000, errorLossCents: 10000};
        const offers = [];
        if (route) offers.push({id: 'enterprise', quality: route.quality, priceCents: posted,
          effortCents: condition.integration_cents, delayCents: 0, switchCents: 0});
        if (probability('conventional') > 0) offers.push({id: 'conventional', quality: probability('conventional'),
          priceCents: cents(posted * (competitors.copied.has(family.id) ? 0.8 : 1.2)),
          effortCents: condition.integration_cents, delayCents: 0, switchCents: 0});
        if (diy) offers.push({id: 'diy', quality: diy.quality, priceCents: 0,
          effortCents: diy.cost, delayCents: 0, switchCents: 0});
        const picked = chooseBuyer(offers, buyer, config, randomDraw(seed, 'choice', week, buyerId));
        buyerChoices.push({week, id, family: family.id, choice: picked.choice, utility_cents: picked.utilityCents,
          ...(options.includeOffers ? {offers: picked.offers} : {}), basis: 'SIMULATED_DEMAND'});
        if (picked.choice === 'diy') buyerRetained.set(key, true);
        if (picked.choice !== 'enterprise') continue;
        attempted++;
        const acquisition = route.id === 'validated-acquisition' && !agent.acquired.has(family.id);
        const stale = route.id === 'validated-acquisition' && randomDraw(seed, 'stale', week, buyerId) < condition.stale_probability;
        const failed = acquisition && randomDraw(seed, 'acquisition-failure', week, buyerId) < condition.acquisition_failure_probability;
        const accepted = trial[route.method].accepted && !stale && !failed;
        if (route.fixed) expense(firm, week, route.id.endsWith('reconstruction') ? 'capability' : 'delivery',
          route.fixed, week, `${id}:${route.id}`);
        expense(firm, week, 'delivery', route.unit, week, `${id}:execution-verification-attention`);
        payBills(firm, week, config);
        if (route.id === 'independent-reconstruction') agent.own.add(family.id);
        if (route.id === 'conventional-reconstruction') agent.conventional.add(family.id);
        if (counterfactualRoute?.id === 'independent-reconstruction') agent.counterfactual.own.add(family.id);
        if (counterfactualRoute?.id === 'conventional-reconstruction') agent.counterfactual.conventional.add(family.id);
        if (accepted && ['validated-acquisition', 'conventional-service'].includes(route.id)) agent.acquired.add(family.id);
        firm.attempts++; accepted ? firm.accepted++ : firm.rejected++;
        if (accepted) {
          const invoice = {id: `enterprise-invoice-${firm.invoices.length}`, mission: id, week,
            dueWeek: week + config.paymentDelayWeeks, amountCents: posted, status: 'pending',
            pays: randomDraw(seed, 'payment', week, buyerId) < config.paymentProbability, refund: false};
          firm.invoices.push(invoice); firm.grossInvoicesCents += posted;
        }
        const asset = state.assets[family.id];
        const usedShared = ['validated-acquisition', 'conventional-service'].includes(route.id);
        const avoided = accepted && baseAlternative !== null ? baseAlternative - route.fixed - route.unit : 0;
        if (usedShared && asset) { asset.uses++; asset.avoided += avoided;
          if (accepted && baseAlternative === null) asset.additionalAccepted++; }
        if (acquisition) {
          transfers.push({id, week, agent: agent.id, family: family.id, accepted, failed, stale,
            best_independent_cost_cents: baseAlternative, acquisition_and_execution_cents: route.fixed + route.unit,
            recipient_net_cents: baseAlternative === null ? null : baseAlternative - route.fixed - route.unit,
            unsupported_before: baseAlternative === null, basis: 'SIMULATED_CONDITIONAL_ON_EXECUTED_COHORT'});
          if (accepted) agent.usefulTransfers++;
          const reward = accepted && !competitors.copied.has(family.id) ?
            Math.max(0, Math.floor(avoided * (condition.contribution_reward_share ?? 0.25))) : 0;
          contributionAllocations.push({id, from: agent.id, to: `creator:${family.id}`, reward_cents: reward,
            internal_transfer_net_enterprise_value_cents: 0,
            explanation: 'Distributional illustration only. Fees are not enterprise revenue or additional value.'});
        }
        jobs.push({id, week, family: family.id, trial_id: trial.task_id, recipient: agent.id,
          accepted, route: route.id, cost_cents: route.fixed + route.unit, simulated_price_cents: accepted ? posted : 0,
          compute_unrounded_cents: trial[route.method].cpu_seconds * schedule.compute_hourly_cents / 3600,
          compute_charged_cents: cents(trial[route.method].cpu_seconds * schedule.compute_hourly_cents / 3600),
          asset_sha256: usedShared ? family.asset_sha256 : null, stale, acquisition_failed: failed,
          basis: 'SIMULATED_JOB_USING_EXECUTED_CASE_CALIBRATION'});
      }
    }
    balances.push({week, cash_cents: firm.cashCents, obligations_cents: unpaid(firm), receivables_cents: receivable(firm),
      generated: generatedResources(firm, config), accrued_costs_cents: sum(Object.values(firm.costs))});
  }
  const canonical = canonicalProjection(firm, config);
  const actualPrototypeArm = arm === 'A' ? 'D' : arm;
  const completedPrototypeCosts = calibration.families.filter(family => !options.excludeLaterPrototypeCosts ||
    Number(family.id.slice(1)) <= (options.maxSharedGeneration ?? 3)).map(family => ({family: family.id,
    ...buildCost(family, schedule, actualPrototypeArm, condition, calibration)}));
  const completePrototypeTotal = sum(completedPrototypeCosts.map(c => c.total_cents));
  const financedPrototypeTotal = sum(Object.values(state.assets).map(a => a.cost));
  const outsidePrototypeTotal = completePrototypeTotal - financedPrototypeTotal;
  assert(outsidePrototypeTotal >= 0, 'Completed prototype cost charged more than once');
  const assets = Object.fromEntries(Object.entries(state.assets).map(([id, a]) => {
    const payoff = calculateInvestment({constructionCostMinor: a.cost, failedConstructionCostMinor: 0,
      maintenancePerReuseMinor: 0, expectedSavingPerReuseMinor: a.avoided - a.upkeep, remainingReuses: 1});
    return [id, {...a, direct_payback: a.uses > 0 && payoff.netBenefit >= 0,
      entire_cohort_payoff: payoff, source: calibration.families.find(f => f.id === id).asset_sha256}];
  }));
  assert(firm.cashCents === firm.openingCashCents + sum(firm.cashEvents.map(e => e.amountCents)), 'Cash identity');
  assert(canonical.cash.summary.observed.revenue === 0, 'Simulated receipts contaminated actual ledger');
  assert(contributionAllocations.every(e => e.internal_transfer_net_enterprise_value_cents === 0), 'Internal fee double count');
  return {schema: SCHEMA, seed, arm, condition, cost_schedule: schedule.id,
    basis: 'SIMULATED_CONDITIONAL_MODEL_NOT_COMMERCIAL_ACTIVITY', actual_collections_cents: 0,
    actual_full_cost_cents: null, actual_full_history_return_cents: null,
    summary: {accepted: firm.accepted, rejected: firm.rejected, attempts: firm.attempts,
      useful_transfers: transfers.filter(t => t.accepted && (t.recipient_net_cents > 0 || t.unsupported_before)).length,
      collected_cents: firm.grossCollectionsCents, accrued_costs_cents: sum(Object.values(firm.costs)),
      profit_cents: canonical.economic.summary.scenario.operatingMargin, cash_cents: firm.cashCents,
      prospective_deployment_profit_cents: canonical.economic.summary.scenario.operatingMargin + schedule.historical_research_cents,
      completed_prototype_cost_cents: completePrototypeTotal,
      enterprise_financed_prototype_cost_cents: financedPrototypeTotal,
      outside_enterprise_prototype_cost_cents: outsidePrototypeTotal,
      project_inclusive_profit_cents: canonical.economic.summary.scenario.operatingMargin - outsidePrototypeTotal,
      subcent_compute_rounding_residual_cents: sum(jobs.map(j => j.compute_unrounded_cents - j.compute_charged_cents)),
      insolvency: firm.insolvent, generated_available_cents: generatedResources(firm, config).availableCents,
      hypothetical_population: agents.length, actually_executed_network_agents: 0},
    assets, completed_prototype_costs: completedPrototypeCosts, canonical, histories: {cash: firm.cashEvents, bills: firm.bills, invoices: firm.invoices,
      balances, jobs, transfers, decisions, buyerChoices, contributionAllocations},
    competitor: {copying_costs_cents: competitors.copyingCosts, copied: [...competitors.copied]},
    limits: ['Empirical cohort resampling is not a field reliability estimate.',
      'All dollar costs, demand, pricing and residual attention are declared assumptions.',
      'Each simulated purchase is one separately demanded stage service; a connected three-stage research chain is not three customers.',
      'The actual prototypes already exist. Modeled construction timing is a counterfactual finance test, not customer-funded research history.',
      'Population diversity and scale are simulated, not actual new agents.',
      'Level6 development acceleration is not tested by this market model.']};
}

export function pairedNetwork(calibration, condition, schedule, seed, options = {}) {
  const checked = options.validated ? calibration : validateCalibration(calibration);
  const arms = Object.fromEntries(ARMS.map(arm => [arm, simulateNetwork(checked, condition, schedule, seed, arm,
    {...options, validated: true})]));
  const profit = arm => arms[arm].summary.profit_cents;
  const differences = {B_minus_A_cents: profit('B') - profit('A'), C_minus_B_cents: profit('C') - profit('B'),
    C_minus_D_cents: profit('C') - profit('D'), B_minus_D_cents: profit('B') - profit('D')};
  for (const [left, right] of [['B', 'A'], ['C', 'B'], ['C', 'D'], ['B', 'D']])
    differences[`${left}_minus_${right}_project_cents`] = arms[left].summary.project_inclusive_profit_cents - arms[right].summary.project_inclusive_profit_cents;
  const financeControls = {};
  for (const arm of ['B', 'C']) {
    const laterBuilt = Object.keys(arms[arm].assets).some(id => id !== 'G1');
    if (laterBuilt) {
      const control = simulateNetwork(checked, condition, schedule, seed, arm, {...options, validated: true,
        maxSharedGeneration: 1, excludeLaterPrototypeCosts: true});
      financeControls[arm] = {basis: 'SAME_WORLD_COUNTERFACTUAL_NO_LATER_SHARED_CAPABILITY',
        incremental_project_profit_cents: arms[arm].summary.project_inclusive_profit_cents - control.summary.project_inclusive_profit_cents,
        summary: control.summary, ...(options.keepFinanceHistories ? {histories: control.histories, canonical: control.canonical} : {})};
    } else {
      const outside = sum(arms[arm].completed_prototype_costs.filter(row => row.family !== 'G1').map(row => row.total_cents));
      financeControls[arm] = {basis: 'NO_LATER_ADOPTION_IDENTICAL_OPERATIONS_PLUS_OUTSIDE_RESEARCH_COST',
        incremental_project_profit_cents: -outside, operational_histories_identical: true};
    }
  }
  const succession = arm => ['B', 'C'].includes(arm) && financeControls[arm].incremental_project_profit_cents > 0 ?
    Object.entries(arms[arm].assets).filter(([id, a]) => id !== 'G1' &&
      a.funding === 'operating-generated' && a.direct_payback && !a.failed && a.uses > 0).map(([id]) => id) : [];
  return {schema: 'capability-advantage-paired-market/v1', seed, condition_id: condition.id,
    cost_schedule: schedule.id, arms, differences, finance_controls: financeControls,
    succession: Object.fromEntries(ARMS.map(arm => [arm, succession(arm)])),
    actual_success_claim_allowed: false};
}

export function unknownCostBoundary() {
  return {basis: 'ACTUAL_COSTS_UNKNOWN', actual_collections_cents: 0, actual_total_cost_cents: null,
    full_history_return_cents: null, levels_3_and_5: 'UNIDENTIFIED', affirmative_investment: false,
    unknown_categories: costNames, reason: 'No unknown authoring/inference/attention cost is replaced by zero.'};
}
