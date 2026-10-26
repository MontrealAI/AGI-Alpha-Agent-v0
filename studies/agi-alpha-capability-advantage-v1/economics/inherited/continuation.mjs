// SPDX-License-Identifier: Apache-2.0
import { simulate as frozenSimulate, randomDraw } from './upstream/src/market.mjs';
import { simulate as hookedSimulate } from './continuation-core.mjs';

export const SCHEMA = 'agi-alpha-second-investment-continuation/v1';
export const COST_CATEGORIES = Object.freeze([
  'priorDiscovery', 'discovery', 'rejectedCandidates', 'construction',
  'verification', 'integration', 'researcherContribution', 'modelAndTools'
]);
export const EFFECT_CATEGORIES = Object.freeze([
  'providerMinutesSaved', 'computeAndToolCentsSaved', 'customerReviewMinutesSaved'
]);
const assert = (condition, message) => { if (!condition) throw Error(message); };
const sum = values => values.reduce((a, b) => a + b, 0);
const clone = value => JSON.parse(JSON.stringify(value));
const integer = (value, label) => {
  assert(Number.isSafeInteger(value) && value >= 0 && value <= 1_000_000_000, `${label}: explicit safe nonnegative integer required`);
  return value;
};
const HASH = /^[a-f0-9]{64}$/;
const OPENING_RD = 'upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing';

export function validateProfile(value) {
  assert(value && typeof value === 'object' && !Array.isArray(value), 'Explicit candidate profile required');
  const p = clone(value);
  assert(p.schema === SCHEMA, 'Unknown second-investment profile schema');
  assert(typeof p.id === 'string' && p.id.length > 0, 'Candidate identity required');
  assert(HASH.test(p.assetSHA256) && HASH.test(p.acceptanceEvidenceSHA256), 'Asset and acceptance identities required');
  assert(typeof p.tested === 'boolean', 'Actual tested status must be explicit');
  assert(typeof p.researchPrototypeConstructed === 'boolean', 'Completed prototype research must be explicitly disclosed');
  assert(['adaptive', 'completed-research-replay'].includes(p.policy), 'Explicit research-financing policy required');
  if (p.policy === 'completed-research-replay') {
    assert(p.researchPrototypeConstructed, 'Completed-research replay requires an actual prototype');
    assert(p.earliestWeek === p.lastDecisionWeek, 'Completed-research replay must use one predeclared decision checkpoint');
  }
  for (const name of ['earliestWeek', 'lastDecisionWeek', 'pauseWeeks', 'usefulLifeWeeks', 'researchEnvelopeCents']) integer(p[name], name);
  assert(p.lastDecisionWeek >= p.earliestWeek && p.pauseWeeks >= 1 && p.usefulLifeWeeks >= 1, 'Finite decision, construction and useful-life windows required');
  for (const name of ['integrationFailureProbability', 'forecastDiscount']) {
    assert(Number.isFinite(p[name]) && p[name] >= 0 && p[name] <= 1, `Explicit probability required: ${name}`);
  }
  assert(p.costs && typeof p.costs === 'object', 'Every complete-cost category must be explicit');
  assert(Object.keys(p.costs).every(k => [...COST_CATEGORIES, 'weeklyMaintenance'].includes(k)), 'Unrecognized cost category cannot be silently omitted');
  for (const name of [...COST_CATEGORIES, 'weeklyMaintenance']) {
    const row = p.costs[name];
    assert(row && typeof row === 'object' && typeof row.explanation === 'string' && row.explanation.length > 0, `Cost explanation required: ${name}`);
    assert(['scenario', 'measured-time-assumed-tariff', 'unknown'].includes(row.basis), `Unknown cost basis: ${name}`);
    if (row.basis === 'unknown') assert(row.amountCents === null, `Unknown cost cannot be zero-filled: ${name}`);
    else integer(row.amountCents, name);
  }
  assert(p.effects && p.effectEvidence, 'Effects and their evidence must be explicitly supplied');
  assert(Object.keys(p.effects).every(k => EFFECT_CATEGORIES.includes(k)), 'Unsupported economic effect');
  for (const name of EFFECT_CATEGORIES) {
    assert(Number.isFinite(p.effects[name]) && Math.abs(p.effects[name]) <= 1_000_000, `Explicit bounded signed effect required: ${name}`);
    assert(typeof p.effectEvidence[name] === 'string' && p.effectEvidence[name].length > 0, `Evidence or zero-effect explanation required: ${name}`);
  }
  assert(Number.isSafeInteger(p.effects.computeAndToolCentsSaved), 'Signed integer compute cents required');
  if (Object.hasOwn(p, 'unroundedComputeSavingsMicrocentsPerJob')) {
    assert(Number.isSafeInteger(p.unroundedComputeSavingsMicrocentsPerJob) &&
      Math.abs(p.unroundedComputeSavingsMicrocentsPerJob) <= 1_000_000_000_000,
    'Explicit bounded signed microcent compute effect required');
  }
  assert(p.effects.providerMinutesSaved === 0 || p.tested, 'Untested source cannot receive a measured time benefit');
  assert(EFFECT_CATEGORIES.every(name => p.effects[name] === 0) || p.tested, 'Untested source cannot receive an economic effect');
  return p;
}

export function generatedResources(firm, config) {
  const unpaid = sum(firm.bills.filter(b => !b.paid).map(b => b.amountCents));
  const accrued = sum(Object.values(firm.costs));
  const openingHistory = config.investmentCostBasis === 'full-history' && config.historicalCostTiming === 'opening'
    ? sum(firm.bills.filter(b => {
      if (b.category !== 'capability' || b.reference !== OPENING_RD || b.week !== 0 || !b.paid || b.paidWeek !== 0) return false;
      const i = firm.cashEvents.findIndex(e => e.reference === b.id && e.type === 'expense_payment' &&
        e.week === 0 && e.amountCents === -b.amountCents);
      return i >= 0 && !firm.cashEvents.slice(0, i).some(e => e.type === 'simulated_collection');
    }).map(b => b.amountCents)) : 0;
  assert(openingHistory <= config.initialCashCents, 'Historical seed allocation exceeds original capital');
  const cashBound = firm.cashCents - unpaid - config.reserveCents;
  const generatedBound = firm.grossCollectionsCents - accrued + openingHistory;
  return {
    availableCents: Math.max(0, Math.min(cashBound, generatedBound)),
    cashCents: firm.cashCents, unpaidObligationsCents: unpaid, reserveCents: config.reserveCents,
    collectedCents: firm.grossCollectionsCents, allAccruedCostsCents: accrued,
    seedPaidOpeningHistoryCents: openingHistory, cashBoundCents: cashBound, generatedBoundCents: generatedBound
  };
}

export function createSecondHooks(input) {
  const profile = validateProfile(input);
  const state = {
    profile, active: false, pending: false, attempted: false, searched: false,
    financiallyAdmitted: false, replayEvaluated: false,
    searchWeek: null, investmentWeek: null, availableWeek: null, expiresWeek: null,
    failed: false, unknownCosts: [], costsPaid: {}, decisions: [], invocations: 0,
    directAvoidedDeliveryCostCents: 0, realizedMaintenanceCents: 0,
    initialCheckpoint: null
  };
  const unknown = [...COST_CATEGORIES, 'weeklyMaintenance'].filter(k => profile.costs[k].basis === 'unknown');
  state.unknownCosts = unknown;
  const amount = key => profile.costs[key].amountCents;
  const searchKeys = ['priorDiscovery', 'discovery', 'rejectedCandidates'];
  const buildKeys = COST_CATEGORIES.filter(key => !searchKeys.includes(key));
  const known = unknown.length === 0;
  const searchCost = known ? sum(searchKeys.map(amount)) : null;
  const buildCost = known ? sum(buildKeys.map(amount)) : null;
  const completeCost = known ? searchCost + buildCost : null;
  const effective = config => !state.active ? config : {
    ...config,
    commonResidualMinutes: config.commonResidualMinutes - profile.effects.providerMinutesSaved,
    computeAndToolCents: config.computeAndToolCents - profile.effects.computeAndToolCentsSaved,
    customerReviewMinutes: config.customerReviewMinutes - profile.effects.customerReviewMinutesSaved
  };
  const charge = (firm, config, week, keys, expense, payBills) => {
    for (const key of keys) {
      assert(!Object.hasOwn(state.costsPaid, key), 'Second cost category charged twice');
      expense(firm, week, 'capability', amount(key), week, `second:${profile.assetSHA256}:${key}`);
      state.costsPaid[key] = amount(key);
    }
    payBills(firm, week, config);
  };
  return {
    initialize({ config }) {
      assert(config.weeks <= 52, 'Second investment cannot extend the original 52-week service horizon');
      assert(profile.lastDecisionWeek < config.weeks, 'Second decision must fit the original service horizon');
      assert(profile.effects.providerMinutesSaved <= config.commonResidualMinutes, 'Second saving exceeds surviving provider burden');
      assert(profile.effects.computeAndToolCentsSaved <= config.computeAndToolCents, 'Second saving exceeds existing tool cost');
      assert(profile.effects.customerReviewMinutesSaved <= config.customerReviewMinutes, 'Customer saving exceeds existing effort');
    },
    activate({ firm, week }) {
      if (state.pending && week >= state.availableWeek) {
        state.pending = false;
        firm.secondAssetPending = false;
        state.active = !state.failed && !firm.insolvent;
      }
      if (state.active && week >= state.expiresWeek) state.active = false;
    },
    effectiveConfig: effective,
    beforeMarket({ config, firm, week, seed, priorAccepted, expense, payBills, unitCost }) {
      if (state.active && !firm.insolvent) {
        const upkeep = amount('weeklyMaintenance');
        expense(firm, week, 'maintenance', upkeep, week + config.expenseDelayWeeks, `second:${profile.assetSHA256}:maintenance`);
        state.realizedMaintenanceCents += upkeep;
        payBills(firm, week, config);
      }
      if (state.attempted || state.replayEvaluated || week < profile.earliestWeek || week > profile.lastDecisionWeek) return;
      const funds = generatedResources(firm, config);
      const record = { week, candidate: profile.id, assetSHA256: profile.assetSHA256, beforeSearch: funds,
        action: 'retain-incumbent', reasons: [], completeOneoffCostCents: completeCost };
      if (!known) { record.reasons.push('Complete-cost profile has unidentified categories'); record.unknownCosts = unknown; }
      if (!profile.tested) record.reasons.push('Actual candidate acceptance is not established');
      if (!firm.assetActive) record.reasons.push('Initial productive capability is not active');
      if (firm.insolvent) record.reasons.push('Enterprise is insolvent');
      if (completeCost !== null && completeCost > profile.researchEnvelopeCents) record.reasons.push('Complete commitment exceeds declared resource envelope');
      if (profile.policy === 'completed-research-replay') {
        state.replayEvaluated = true;
        if (completeCost !== null && funds.availableCents < completeCost) {
          record.reasons.push('Complete executed research cost exceeds currently generated resources');
        }
      }
      if (record.reasons.length) {
        if (profile.policy === 'completed-research-replay') record.action = 'completed-prototype-not-financed';
        state.decisions.push(record); return;
      }
      if (!state.searched) {
        if (funds.availableCents < searchCost) {
          record.reasons.push('Currently generated resources cannot pay search costs');
          state.decisions.push(record); return;
        }
        state.initialCheckpoint = { week, funding: clone(funds) };
        charge(firm, config, week, searchKeys, expense, payBills);
        state.searched = true; state.searchWeek = week;
      }
      const afterSearch = generatedResources(firm, config);
      const availableWeek = week + profile.pauseWeeks;
      const remainingWeeks = Math.max(0, Math.min(config.weeks - availableWeek, profile.usefulLifeWeeks));
      const forecastUses = Math.floor(priorAccepted / Math.max(1, Math.min(8, week)) * remainingWeeks * profile.forecastDiscount);
      const hypothetical = { ...config,
        commonResidualMinutes: config.commonResidualMinutes - profile.effects.providerMinutesSaved,
        computeAndToolCents: config.computeAndToolCents - profile.effects.computeAndToolCentsSaved };
      const perUseSaving = Math.max(0, Math.floor((unitCost(config, true) - unitCost(hypothetical, true)) * (1 - config.expectedPassThrough)));
      const priorInvoices = firm.invoices.filter(i => i.week >= Math.max(0, week - 8) && i.week < week);
      const priorPrice = priorInvoices.length ? sum(priorInvoices.map(i => i.amountCents)) / priorInvoices.length : 0;
      const forgone = Math.max(0, Math.round(priorAccepted / Math.max(1, Math.min(8, week)) * profile.pauseWeeks *
        Math.max(0, priorPrice * config.paymentProbability - unitCost(config, true) * config.failureCorrectionMultiplier)));
      const forecastUpkeep = remainingWeeks * amount('weeklyMaintenance');
      const expectedNet = forecastUses * perUseSaving * (1 - profile.integrationFailureProbability) - completeCost - forecastUpkeep - forgone;
      Object.assign(record, { afterSearch, searchPreviouslyPaidCents: searchCost, remainingConstructionCents: buildCost,
        forecastUses, productiveWeeks: remainingWeeks, forecastAvoidedCostPerUseCents: perUseSaving,
        forecastMaintenanceCents: forecastUpkeep, expectedForgoneContributionCents: forgone,
        expectedCompleteCostNetBenefitCents: expectedNet,
        forecastLimitation: 'Gate monetizes evidenced provider/tool savings only. Customer-effort changes alone do not create seller revenue.' });
      if (afterSearch.availableCents < buildCost) record.reasons.push('Construction exceeds currently generated resources after search');
      if (expectedNet <= 0) record.reasons.push('No forecast complete-cost repayment within remaining useful life');
      if (remainingWeeks === 0) record.reasons.push('No production time remains after construction');
      if (profile.policy === 'adaptive' && record.reasons.length) { state.decisions.push(record); return; }
      if (profile.policy === 'completed-research-replay' && remainingWeeks === 0) {
        record.action = 'completed-prototype-not-financed'; state.decisions.push(record); return;
      }
      state.financiallyAdmitted = record.reasons.length === 0;
      record.financiallyAdmitted = state.financiallyAdmitted;
      record.action = state.financiallyAdmitted ? 'invest-second-capability' : 'operating-funded-unqualified-research-attempt';
      charge(firm, config, week, buildKeys, expense, payBills);
      assert(!firm.insolvent, 'Second investment must be fully paid without insolvency');
      state.attempted = true; state.investmentWeek = week;
      state.availableWeek = availableWeek; state.expiresWeek = availableWeek + profile.usefulLifeWeeks;
      state.failed = randomDraw(seed, 'second-asset-integration-failure', week) < profile.integrationFailureProbability;
      state.pending = true; firm.secondAssetPending = true;
      record.integrationFailure = state.failed; record.availableWeek = availableWeek;
      record.afterConstruction = generatedResources(firm, config);
      state.decisions.push(record);
    },
    afterProduction({ week, jobs }) {
      if (!state.active) return;
      for (const job of jobs.filter(j => j.week === week && j.provider === 'enterprise')) {
        job.secondAssetUsed = profile.id;
        job.secondAssetSHA256 = profile.assetSHA256;
        state.invocations++;
      }
    },
    finalize({ firm, jobs, config }) {
      const baseUnit = Math.round((config.commonResidualMinutes + config.assetResidualMinutes) * config.hourlyProviderCents / 60) + config.computeAndToolCents;
      const secondUnit = Math.round((config.commonResidualMinutes + config.assetResidualMinutes -
        profile.effects.providerMinutesSaved) * config.hourlyProviderCents / 60) +
        config.computeAndToolCents - profile.effects.computeAndToolCentsSaved;
      const direct = sum(jobs.filter(j => j.secondAssetSHA256 === profile.assetSHA256).map(j =>
        Math.round(baseUnit * (j.qualityGood ? 1 : config.failureCorrectionMultiplier)) -
        Math.round(secondUnit * (j.qualityGood ? 1 : config.failureCorrectionMultiplier))));
      const realizedOneoff = sum(Object.values(state.costsPaid));
      const fullRealized = realizedOneoff + state.realizedMaintenanceCents;
      const funded = state.attempted && state.decisions.find(d =>
        ['invest-second-capability', 'operating-funded-unqualified-research-attempt'].includes(d.action));
      const outsidePrototype = profile.researchPrototypeConstructed ? (known ? completeCost - realizedOneoff : null) : 0;
      const unrounded = profile.unroundedComputeSavingsMicrocentsPerJob ?? null;
      const usedJobs = jobs.filter(j => j.secondAssetSHA256 === profile.assetSHA256);
      const baseAfterProviderEffect = secondUnit + profile.effects.computeAndToolCentsSaved;
      const precisionResiduals = unrounded === null ? [] : usedJobs.map(j => {
        const correction = j.qualityGood ? 1 : config.failureCorrectionMultiplier;
        const chargedComputeSavingCents = Math.round(baseAfterProviderEffect * correction) - Math.round(secondUnit * correction);
        return unrounded * correction - chargedComputeSavingCents * 1_000_000;
      });
      return {
        schema: SCHEMA, basis: 'SIMULATED', profile, actualCustomerCollectionsCents: 0,
        unknownCostCategories: unknown, completeCostProfilePriced: known,
        allInCostBasis: known ? 'Explicit complete-category scenario, not an empirically bounded actual invoice' : 'UNIDENTIFIED',
        searched: state.searched, searchWeek: state.searchWeek,
        invested: state.attempted && state.financiallyAdmitted,
        modeledConstructionAttempted: state.attempted, financiallyAdmitted: state.financiallyAdmitted,
        investmentWeek: state.investmentWeek,
        availableWeek: state.availableWeek, expiresWeek: state.expiresWeek,
        failedIntegration: state.failed, actualAssetInvocationsInModel: state.invocations,
        costsPaidByCategoryCents: state.costsPaid, maintenanceAccruedCents: state.realizedMaintenanceCents,
        completeRealizedSecondCostsCents: fullRealized, directAvoidedDeliveryCostCents: direct,
        completedPrototypeResearchDisclosed: profile.researchPrototypeConstructed,
        declaredCompletePrototypeOneoffCostCents: completeCost,
        outsideEnterprisePrototypeCostCents: outsidePrototype,
        outsideResearchProvenance: 'Completed research that the modeled enterprise does not fund remains explicit external research contribution. It adds no enterprise cash. Project-inclusive profit deducts this cost once; original enterprise cash is unchanged.',
        directNetBenefitCents: direct - fullRealized,
        directCostRepayment: state.attempted && state.invocations > 0 && direct > 0 && direct >= fullRealized,
        directRepaymentInterpretation: 'Avoided delivery cost only. This flag omits foregone contribution and buyer/competitor effects; positive paired project-inclusive profit is additionally required for a financial reinvestment claim.',
        subcentComputeEffect: unrounded === null ? null : {
          unit: 'one microcent = 0.000001 USD cent = 0.00000001 USD',
          unroundedNetSavingsMicrocentsPerJob: unrounded,
          centLedgerSavingsMicrocentsPerJob: profile.effects.computeAndToolCentsSaved * 1_000_000,
          netSavingsNotRepresentedByCentLedgerMicrocents: sum(precisionResiduals),
          maximumAbsoluteUnrepresentedUSD: sum(precisionResiduals.map(Math.abs)) / 100_000_000,
          correctionAndCentRoundingIncluded: true,
          scope: 'Executed modeled uses, before any second-order market response to a finer price grid. Negative means a cost penalty, not a saving.'
        },
        investmentPaidFromGeneratedResources: !!funded,
        initialCheckpoint: state.initialCheckpoint, terminalFunding: generatedResources(firm, config),
        decisions: state.decisions,
        interpretation: 'Model decisions are counterfactual. Source construction, acceptance, measured effects and actual research expenditure require external evidence. No second purchase occurs when no worthwhile candidate qualifies.',
        legacyRepaymentCountersInterpretation: 'The upstream direct-repayment fields now aggregate all capability bills. Use this record and paired enterprise-profit differences for the second investment.'
      };
    }
  };
}

export function simulateContinuation(config, seed, profile = null, options = {}) {
  assert(!Object.hasOwn(options, 'continuationHooks'), 'Use a validated candidate profile, not injected hooks');
  if (profile === null) return hookedSimulate(config, seed, 'B', options);
  const run = hookedSimulate(config, seed, 'B', { ...options, continuationHooks: createSecondHooks(profile) });
  const second = run.secondInvestment;
  second.enterpriseProfitBeforeUnpricedCostsCents = run.summary.profitCents;
  second.projectProfitAfterCompletedPrototypeCostsCents = second.outsideEnterprisePrototypeCostCents === null
    ? null : run.summary.profitCents - second.outsideEnterprisePrototypeCostCents;
  second.completedResearchCostCountedExactlyOnce = second.completeCostProfilePriced && second.completedPrototypeResearchDisclosed
    ? second.declaredCompletePrototypeOneoffCostCents ===
      sum(Object.values(second.costsPaidByCategoryCents)) + second.outsideEnterprisePrototypeCostCents : null;
  return run;
}

const prefix = (run, beforeWeek) => Object.fromEntries(
  ['cash', 'balances', 'invoices', 'bills', 'buyerChoices', 'jobs', 'investmentDecisions', 'investments', 'competitorActions', 'prices']
    .map(key => [key, run.histories[key].filter(row => row.week < beforeWeek).map(row => {
      const copy = clone(row);
      if (key === 'invoices') {
        delete copy.status; delete copy.collectedWeek;
      }
      if (key === 'bills' && copy.paidWeek >= beforeWeek) { copy.paid = false; delete copy.paidWeek; }
      return copy;
    })])
);

export function pairedContinuation(config, seed, profiles, options = {}) {
  assert(profiles && profiles.B && profiles.C, 'Both improvement methods need explicit profiles');
  const arms = {
    A: simulateContinuation(config, seed, null, options),
    B: simulateContinuation(config, seed, profiles.B, options),
    C: simulateContinuation(config, seed, profiles.C, options)
  };
  const decisionWeek = Math.min(profiles.B.earliestWeek, profiles.C.earliestWeek);
  const baselinePrefix = JSON.stringify(prefix(arms.A, decisionWeek));
  assert(['B', 'C'].every(arm => JSON.stringify(prefix(arms[arm], decisionWeek)) === baselinePrefix), 'Second-investment arms do not share the same enterprise prefix');
  assert(JSON.stringify(arms.A) === JSON.stringify(frozenSimulate(config, seed, 'B', options)), 'No-investment continuation changed the frozen incumbent');
  const projectDelta = arm => arms[arm].secondInvestment.projectProfitAfterCompletedPrototypeCostsCents === null
    ? null : arms[arm].secondInvestment.projectProfitAfterCompletedPrototypeCostsCents - arms.A.summary.profitCents;
  const qualify = arm => {
    const s = arms[arm].secondInvestment;
    return {
      conditionalModeledFinancialGatePassed: s.invested && s.completeCostProfilePriced &&
        s.investmentPaidFromGeneratedResources && s.actualAssetInvocationsInModel > 0 &&
        s.directCostRepayment && projectDelta(arm) !== null && projectDelta(arm) > 0,
      projectInclusiveIncrementCents: projectDelta(arm),
      qualification: 'Conditional financial calculation only; actual source acceptance and effect provenance require the separately frozen production evidence. Direct cost repayment alone is insufficient.'
    };
  };
  return {
    schema: 'agi-alpha-second-investment-paired/v1', basis: 'SIMULATED', seed,
    config: arms.A.config, firstAssetShared: arms.A.histories.investments[0]?.asset ?? null,
    commonPrefixBeforeWeek: decisionWeek, commonPrefixExact: true,
    qualification: { B: qualify('B'), C: qualify('C') },
    arms,
    causal: {
      B_minus_A_profitCents: arms.B.summary.profitCents - arms.A.summary.profitCents,
      C_minus_A_profitCents: arms.C.summary.profitCents - arms.A.summary.profitCents,
      B_minus_C_profitCents: arms.B.summary.profitCents - arms.C.summary.profitCents,
      B_minus_A_projectInclusiveProfitCents: arms.B.secondInvestment.projectProfitAfterCompletedPrototypeCostsCents === null
        ? null : arms.B.secondInvestment.projectProfitAfterCompletedPrototypeCostsCents - arms.A.summary.profitCents,
      C_minus_A_projectInclusiveProfitCents: arms.C.secondInvestment.projectProfitAfterCompletedPrototypeCostsCents === null
        ? null : arms.C.secondInvestment.projectProfitAfterCompletedPrototypeCostsCents - arms.A.summary.profitCents,
      B_minus_C_projectInclusiveProfitCents: projectDelta('B') === null || projectDelta('C') === null
        ? null : projectDelta('B') - projectDelta('C'),
      B_minus_A_accepted: arms.B.summary.enterpriseAccepted - arms.A.summary.enterpriseAccepted,
      C_minus_A_accepted: arms.C.summary.enterpriseAccepted - arms.A.summary.enterpriseAccepted
    },
    disclaimer: 'No external capital injection, transaction, new customer observation or equilibrium claim.'
  };
}
