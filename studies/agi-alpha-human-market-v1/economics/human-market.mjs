// SPDX-License-Identifier: Apache-2.0
import {createFirm, unpaid, receivable, expense, payBills, collect, liquidity, operatingSurplus,
  chooseBuyer, randomDraw} from './upstream/market/upstream/src/cash-core.mjs';
import {planMission, calculateInvestment} from './upstream/market/upstream/canonical/shadow-ledger.mjs';
import {fundingView, OPENING_RD_REFERENCE} from './upstream/market/upstream/deployment-robustness/funding.mjs';

export const SCHEMA = 'agi-alpha-human-market/v1';
const sum = values => values.reduce((a, b) => a + b, 0);
const assert = (value, message) => { if (!value) throw Error(message); };
const integer = (value, name, minimum = 0, maximum = 1_000_000_000) => {
  assert(Number.isSafeInteger(value) && value >= minimum && value <= maximum, `Explicit bounded integer required: ${name}`);
};
const probability = (value, name) => assert(Number.isFinite(value) && value >= 0 && value <= 1,
  `Explicit probability required: ${name}`);
const required = (object, names, label) => {
  assert(object && Object.getPrototypeOf(object) === Object.prototype, `${label} must be a plain object`);
  for (const name of names) assert(Object.hasOwn(object, name), `${label}.${name} is required`);
};
const cents = value => Math.round(value);
const amount = (minutes, rate) => cents(minutes * rate / 60);
const copy = value => JSON.parse(JSON.stringify(value));

export function validateHumanConfig(raw) {
  const c = copy(raw);
  required(c, ['id', 'currency', 'weeks', 'buyers', 'arrivalProbability', 'classes', 'profiles', 'capabilities',
    'initialCashCents', 'reserveCents', 'initialSetupCents', 'historicalResearchCents', 'weeklyOverheadCents', 'opportunityScreeningCents', 'opportunityAcquisitionCents',
    'paymentDelayWeeks', 'paymentProbability', 'expenseDelayWeeks', 'refundDelayWeeks', 'refundProbability',
    'discountBps', 'buyerHourlyCents', 'humanReviewMinutes', 'humanQuality', 'enterprisePerceivedQuality',
    'humanDays', 'enterpriseDays', 'delayCentsPerDay', 'buyerIntegrationCents', 'buyerSwitchingCents', 'providerOnboardingCents',
    'buyerValueMultiplier', 'buyerErrorLossCents', 'buyerProcurementBudgetCents', 'enterpriseSlotsPerWeek',
    'choiceModel', 'logitScaleCents', 'forecastDiscount', 'investmentEarliestWeek', 'forecastWindowWeeks',
    'fieldReliabilityMultiplier', 'paymentFeeBps', 'fiscalReserveBps', 'priceEvidenceReference', 'costAssumptionsReference', 'productionEvidenceReference',
    'allMoneyIsAssumed', 'demandIsAssumed'], 'configuration');
  assert(['USD', 'CAD', 'EUR'].includes(c.currency), 'Explicit supported currency required');
  assert(typeof c.id === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$/.test(c.id), 'Safe unique scenario identity required');
  assert(c.allMoneyIsAssumed === true && c.demandIsAssumed === true, 'Simulation labels must remain explicit');
  assert(['deterministic', 'logit'].includes(c.choiceModel), 'Unknown buyer choice model');
  for (const key of ['arrivalProbability', 'paymentProbability', 'refundProbability', 'humanQuality',
    'enterprisePerceivedQuality', 'forecastDiscount', 'fieldReliabilityMultiplier']) probability(c[key], key);
  for (const key of ['weeks', 'buyers', 'initialCashCents', 'reserveCents', 'initialSetupCents',
    'historicalResearchCents', 'weeklyOverheadCents', 'opportunityScreeningCents', 'opportunityAcquisitionCents', 'paymentDelayWeeks', 'expenseDelayWeeks', 'refundDelayWeeks',
    'discountBps', 'buyerHourlyCents', 'humanReviewMinutes', 'humanDays', 'enterpriseDays', 'delayCentsPerDay',
    'buyerIntegrationCents', 'buyerSwitchingCents', 'providerOnboardingCents', 'buyerErrorLossCents', 'buyerProcurementBudgetCents',
    'enterpriseSlotsPerWeek', 'logitScaleCents', 'investmentEarliestWeek', 'forecastWindowWeeks', 'paymentFeeBps', 'fiscalReserveBps']) integer(c[key], key);
  assert(c.weeks > 0 && c.weeks <= 104 && c.buyers > 0 && c.buyers <= 40, 'Finite campaign limits exceeded');
  assert(c.discountBps <= 10000 && c.paymentFeeBps <= 10000 && c.fiscalReserveBps <= 10000 && c.forecastWindowWeeks > 0,
    'Invalid discount/fee/reserve/window');
  assert(c.initialCashCents >= c.reserveCents, 'Seed must cover declared reserve');
  assert(Number.isFinite(c.buyerValueMultiplier) && c.buyerValueMultiplier >= 0, 'Value multiplier required');
  for (const key of ['priceEvidenceReference', 'costAssumptionsReference', 'productionEvidenceReference']) {
    assert(typeof c[key] === 'string' && c[key].length > 0, `Source reference required: ${key}`);
  }
  assert(Array.isArray(c.classes) && c.classes.length > 0 && c.classes.length <= 8, 'Finite job-class list required');
  const ids = new Set();
  for (const item of c.classes) {
    required(item, ['id', 'weight', 'humanReferenceCents', 'priceEvidenceReference'], 'job class');
    assert(typeof item.id === 'string' && /^[a-z][a-z0-9-]{0,30}$/.test(item.id) && !ids.has(item.id), 'Unique class identity required');
    ids.add(item.id); probability(item.weight, 'class weight'); integer(item.humanReferenceCents, 'human reference', 1);
    assert(typeof item.priceEvidenceReference === 'string' && item.priceEvidenceReference.length > 0, 'Class price source required');
  }
  assert(Math.abs(sum(c.classes.map(x => x.weight)) - 1) < 1e-9, 'Class weights must sum to one');
  assert(Array.isArray(c.profiles) && c.profiles.length >= 1 && c.profiles.length <= 3, 'One to three actual profiles required');
  assert(new Set(c.profiles.map(p => p.id)).size === c.profiles.length, 'Production profile IDs must be unique');
  for (const p of c.profiles) {
    required(p, ['id', 'sourceSHA256', 'evidenceReference', 'classes'], 'production profile');
    assert(/^[a-f0-9]{64}$/.test(p.sourceSHA256), 'Actual profile source hash required');
    assert(typeof p.evidenceReference === 'string' && p.evidenceReference.length > 0, 'Profile evidence reference required');
    for (const item of c.classes) {
      const v = p.classes[item.id];
      required(v, ['supported', 'acceptanceProbability', 'deliveryCostCents', 'businessCostCents',
        'customerMinutes', 'attemptsPerJob', 'marginalExecutionCostCents', 'setupAllocationCents'], 'class profile');
      assert(typeof v.supported === 'boolean', 'Explicit support flag required');
      probability(v.acceptanceProbability, 'acceptance probability');
      for (const key of ['deliveryCostCents', 'businessCostCents', 'customerMinutes', 'attemptsPerJob',
        'marginalExecutionCostCents', 'setupAllocationCents']) integer(v[key], key);
      assert(v.attemptsPerJob > 0, 'All attempts must be counted');
      assert(v.marginalExecutionCostCents <= v.deliveryCostCents, 'Marginal cost exceeds recurring delivery cost');
      if (!v.supported) assert(v.acceptanceProbability === 0, 'Unsupported tasks cannot be accepted');
    }
  }
  assert(Array.isArray(c.capabilities) && c.capabilities.length === c.profiles.length - 1, 'Profiles and investments must form one chain');
  assert(new Set(c.capabilities.map(p => p.id)).size === c.capabilities.length, 'Capability IDs must be unique');
  c.capabilities.forEach((cap, i) => {
    required(cap, ['id', 'sourceSHA256', 'evidenceReference', 'constructionCents', 'validationCents',
      'failedDiscoveryCents', 'integrationCents', 'weeklyMaintenanceCents', 'lifetimeWeeks', 'constructionWeeks'], 'capability');
    assert(cap.sourceSHA256 === c.profiles[i + 1].sourceSHA256, 'Capability must bind the resulting profile');
    for (const key of ['constructionCents', 'validationCents', 'failedDiscoveryCents', 'integrationCents',
      'weeklyMaintenanceCents', 'lifetimeWeeks', 'constructionWeeks']) integer(cap[key], key);
    assert(cap.lifetimeWeeks > 0 && cap.constructionWeeks > 0, 'Finite positive useful/build lifetime required');
    assert(typeof cap.evidenceReference === 'string' && cap.evidenceReference.length > 0, 'Capability benefit evidence required');
  });
  return c;
}

const investmentCost = cap => cap.constructionCents + cap.validationCents + cap.failedDiscoveryCents + cap.integrationCents;
const recurring = p => p.deliveryCostCents + p.businessCostCents;
const fiscalReserve = (f, c) => cents(Math.max(0, f.grossCollectionsCents -
  sum(Object.entries(f.costs).filter(([k]) => k !== 'capability').map(([, v]) => v))) * c.fiscalReserveBps / 10000);
const protectedLiquidity = (f, c) => liquidity(f, c) - fiscalReserve(f, c);
function generated(f, c) {
  const total = sum(Object.values(f.costs));
  const paidHistorical = f.bills.filter(b => b.reference === OPENING_RD_REFERENCE && b.paid && b.paidWeek === 0)
    .reduce((n, b) => n + b.amountCents, 0);
  return Math.max(0, Math.min(protectedLiquidity(f, c), f.grossCollectionsCents - total + paidHistorical - fiscalReserve(f, c)));
}

function profileIndex(week, investments) {
  let index = 0;
  for (const investment of investments) {
    if (investment.availableWeek > week || investment.expiresWeek <= week) break;
    index++;
  }
  return index;
}

function classFor(c, seed, week, buyer) {
  let draw = randomDraw(seed, 'job-class', week, buyer);
  for (const item of c.classes) { draw -= item.weight; if (draw <= 0) return item; }
  return c.classes.at(-1);
}

function project(f, c) {
  const ref = 'SIMULATED human-market economics. Actual customer collections are zero. All costs are declared assumptions.';
  const operating = sum(Object.entries(f.costs).filter(([k]) => k !== 'capability').map(([, v]) => v));
  const paid = sum(Object.entries(f.paidCosts).filter(([k]) => k !== 'capability').map(([, v]) => v));
  const common = {reference: ref, currency: c.currency, acceptance: 'accepted', totalCollectedCents: 0,
    operatingCostsComplete: true, costBasis: 'assumed', reinvestmentBps: 0};
  const economic = planMission({...common, missionId: 'human-market-economic',
    priceAssumptionCents: f.grossCollectionsCents + receivable(f), totalOperatingCostCents: operating,
    capabilityCostCents: f.costs.capability, reserveCents: 0, obligationCents: 0});
  const cash = planMission({...common, missionId: 'human-market-cash', priceAssumptionCents: f.grossCollectionsCents,
    totalOperatingCostCents: paid, capabilityCostCents: f.paidCosts.capability, reserveCents: c.reserveCents + fiscalReserve(f, c),
    obligationCents: unpaid(f)});
  assert(cash.summary.observed.revenue === 0, 'Simulated receipts contaminated actual revenue');
  assert(cash.summary.scenario.afterReserves === f.cashCents - f.openingCashCents - unpaid(f) - c.reserveCents - fiscalReserve(f, c),
    'Canonical cash reconciliation failed');
  assert(economic.summary.scenario.operatingMargin === f.cashCents + receivable(f) - unpaid(f) - f.openingCashCents,
    'Canonical accrued reconciliation failed');
  return {economic, cash};
}

function investmentDecision(f, c, week, choices, maximumInvestments) {
  const next = f.investments.length;
  if (next >= c.capabilities.length || next >= maximumInvestments || f.insolvent || week < c.investmentEarliestWeek) return null;
  if (profileIndex(week, f.investments) !== next) return null;
  const cap = c.capabilities[next], before = c.profiles[next], after = c.profiles[next + 1];
  const predecessorRemaining = next ? Math.min(...f.investments.map(x => x.expiresWeek)) - week - cap.constructionWeeks : c.weeks;
  const full = investmentCost(cap), lifetime = Math.min(cap.lifetimeWeeks, c.weeks - week - cap.constructionWeeks, predecessorRemaining);
  const window = Math.min(c.forecastWindowWeeks, week);
  const recent = choices.filter(j => j.week >= week - window && j.week < week);
  let benefitPerWeek = 0, eligiblePrior = 0;
  for (const prior of recent) {
    const item = c.classes.find(x => x.id === prior.classId);
    const price = cents(item.humanReferenceCents * (1 - c.discountBps / 10000));
    const contribution = profile => {
      const p = profile.classes[item.id];
      if (!p.supported || price > prior.remainingBuyerBudgetCents) return 0;
      const offer = {id: 'enterprise', priceCents: price, quality: c.enterprisePerceivedQuality,
        effortCents: amount(p.customerMinutes, c.buyerHourlyCents), delayCents: c.enterpriseDays * c.delayCentsPerDay,
        switchCents: prior.enterpriseSwitchCostCents};
      const selection = chooseBuyer([...prior.offers.filter(x => x.id === 'human'), offer],
        {valueCents: prior.buyerValueCents, errorLossCents: c.buyerErrorLossCents}, c, prior.forecastChoiceDraw);
      if (selection.choice !== 'enterprise') return 0;
      const netReceipts = price * p.acceptanceProbability * c.fieldReliabilityMultiplier * c.paymentProbability *
        (1 - c.refundProbability - c.paymentFeeBps / 10000);
      const onboarding = prior.providerOnboardingDue ? c.providerOnboardingCents : 0;
      return (netReceipts - recurring(p) - onboarding) * (1 - c.fiscalReserveBps / 10000);
    };
    benefitPerWeek += (contribution(after) - contribution(before)) / window;
    eligiblePrior++;
  }
  const forecastBenefit = Math.floor(benefitPerWeek * Math.max(0, lifetime) * c.forecastDiscount);
  const forecastMaintenance = Math.max(0, lifetime) * cap.weeklyMaintenanceCents;
  const ceiling = generated(f, c), available = protectedLiquidity(f, c);
  const decision = {week, capabilityId: cap.id, sourceSHA256: cap.sourceSHA256, fullCostCents: full,
    forecastBenefitCents: forecastBenefit, forecastMaintenanceCents: forecastMaintenance,
    forecastNetCents: forecastBenefit - forecastMaintenance - full, forecastWeeks: Math.max(0, lifetime),
    recentObservedScenarioOpportunities: eligiblePrior, operatingGeneratedCents: ceiling, liquidAfterObligationsAndReserveCents: available,
    forecastBasis: 'Counterfactual replay of prior simulated opportunities only, through the same human/enterprise/defer buyer rule; unchanged price and quality beliefs. Demand is assumed, and no future outcomes are used.',
    action: 'hold', reason: 'No positive full-cost benefit within remaining useful life'};
  if (lifetime <= 0 || forecastBenefit <= full + forecastMaintenance) return decision;
  if (ceiling < full || available < full) return {...decision, reason: 'Insufficient collected operating-generated resources'};
  expense(f, week, 'capability', full, week, cap.sourceSHA256); payBills(f, week, c);
  assert(!f.insolvent, 'An investment caused insolvency despite affordability gate');
  const record = {...decision, action: 'invest', reason: 'Positive declared-model value and generated-funds affordability',
    availableWeek: week + cap.constructionWeeks, expiresWeek: week + cap.constructionWeeks + cap.lifetimeWeeks,
    predecessor: next ? c.capabilities[next - 1].id : c.profiles[0].id, beforeProfile: before.id, afterProfile: after.id};
  f.investments.push(record); return record;
}

export function simulateHumanMarket(raw, seed, {maximumInvestments = 2} = {}) {
  const c = validateHumanConfig(raw); integer(seed, 'seed', 0, 0xffffffff); integer(maximumInvestments, 'maximum investments', 0, 2);
  const f = createFirm('enterprise', c.initialCashCents), jobs = [], choices = [], decisions = [];
  const buyers = Array.from({length: c.buyers}, (_, i) => ({id: i, usedEnterprise: false, spent: 0, lastProvider: null}));
  if (c.historicalResearchCents) expense(f, 0, 'capability', c.historicalResearchCents, 0, OPENING_RD_REFERENCE);
  expense(f, 0, 'business', c.initialSetupCents, 0, 'Shared service setup and discovery: charged once');
  payBills(f, 0, c);
  const collectWithFees = week => {
    collect(f, week, c);
    for (const invoice of f.invoices.filter(i => i.status === 'collected' && !i.feeRecorded)) {
      expense(f, week, 'business', cents(invoice.amountCents * c.paymentFeeBps / 10000), week, `collection-fee:${invoice.id}`);
      invoice.feeRecorded = true;
    }
  };
  const terminal = c.weeks + Math.max(c.paymentDelayWeeks + c.refundDelayWeeks, c.expenseDelayWeeks) + 1;
  for (let week = 0; week <= terminal; week++) {
    collectWithFees(week); payBills(f, week, c);
    if (week < c.weeks) {
      if (!f.insolvent) expense(f, week, 'business', c.weeklyOverheadCents, week + c.expenseDelayWeeks, 'Recurring service business costs');
      const activeIndex = profileIndex(week, f.investments);
      for (let i = 0; i < activeIndex && !f.insolvent; i++) expense(f, week, 'maintenance', c.capabilities[i].weeklyMaintenanceCents,
        week + c.expenseDelayWeeks, c.capabilities[i].sourceSHA256);
      payBills(f, week, c);
      const decision = investmentDecision(f, c, week, choices, maximumInvestments); if (decision) decisions.push(decision);
      let slots = 0;
      const profile = c.profiles[profileIndex(week, f.investments)];
      for (const buyer of buyers) {
        if (randomDraw(seed, 'arrival', week, buyer.id) >= c.arrivalProbability) continue;
        if (!f.insolvent) {
          expense(f, week, 'business', c.opportunityAcquisitionCents, week + c.expenseDelayWeeks,
            `opportunity-acquisition:w${week}-b${buyer.id}`);
          expense(f, week, 'business', c.opportunityScreeningCents, week + c.expenseDelayWeeks,
            `opportunity-screen:w${week}-b${buyer.id}`);
          payBills(f, week, c);
        }
        const item = classFor(c, seed, week, buyer.id), p = profile.classes[item.id];
        const price = cents(item.humanReferenceCents * (1 - c.discountBps / 10000));
        const budget = c.buyerProcurementBudgetCents - buyer.spent;
        const offers = [];
        if (item.humanReferenceCents <= budget) offers.push({id: 'human', priceCents: item.humanReferenceCents,
          quality: c.humanQuality, effortCents: amount(c.humanReviewMinutes, c.buyerHourlyCents),
          delayCents: c.humanDays * c.delayCentsPerDay,
          switchCents: buyer.lastProvider && buyer.lastProvider !== 'human' ? c.buyerSwitchingCents : 0});
        if (!f.insolvent && p.supported && slots < c.enterpriseSlotsPerWeek && price <= budget &&
            protectedLiquidity(f, c) >= recurring(p) + (buyer.usedEnterprise ? 0 : c.providerOnboardingCents)) offers.push({id: 'enterprise', priceCents: price,
          quality: c.enterprisePerceivedQuality, effortCents: amount(p.customerMinutes, c.buyerHourlyCents),
          delayCents: c.enterpriseDays * c.delayCentsPerDay,
          switchCents: (!buyer.usedEnterprise ? c.buyerIntegrationCents : 0) +
            (buyer.lastProvider && buyer.lastProvider !== 'enterprise' ? c.buyerSwitchingCents : 0)});
        const picked = chooseBuyer(offers, {valueCents: cents(item.humanReferenceCents * c.buyerValueMultiplier),
          errorLossCents: c.buyerErrorLossCents}, c, randomDraw(seed, 'choice', week, buyer.id));
        choices.push({week, buyer: buyer.id, classId: item.id, choice: picked.choice,
          offers: picked.offers, utilityCents: picked.utilityCents, remainingBuyerBudgetCents: budget,
          buyerValueCents: cents(item.humanReferenceCents * c.buyerValueMultiplier),
          enterpriseSwitchCostCents: (!buyer.usedEnterprise ? c.buyerIntegrationCents : 0) +
            (buyer.lastProvider && buyer.lastProvider !== 'enterprise' ? c.buyerSwitchingCents : 0),
          providerOnboardingDue: !buyer.usedEnterprise,
          forecastChoiceDraw: randomDraw(seed, 'forecast-choice', week, buyer.id)});
        if (picked.choice === 'defer') continue;
        buyer.lastProvider = picked.choice;
        if (picked.choice === 'human') { buyer.spent += item.humanReferenceCents; continue; }
        const onboardingCost = buyer.usedEnterprise ? 0 : c.providerOnboardingCents;
        if (onboardingCost) expense(f, week, 'business', onboardingCost, week + c.expenseDelayWeeks, `provider-onboarding:b${buyer.id}`);
        buyer.usedEnterprise = true; slots++; f.attempts++;
        const accepted = randomDraw(seed, 'accepted', week, buyer.id) < p.acceptanceProbability * c.fieldReliabilityMultiplier;
        if (accepted) f.accepted++; else f.rejected++;
        const id = `w${week}-b${buyer.id}`;
        expense(f, week, 'delivery', p.deliveryCostCents, week + c.expenseDelayWeeks, id);
        expense(f, week, 'business', p.businessCostCents, week + c.expenseDelayWeeks, id);
        payBills(f, week, c);
        const job = {id, week, buyer: buyer.id, classId: item.id, provider: 'enterprise', accepted,
          profileId: profile.id, profileSourceSHA256: profile.sourceSHA256, priceCents: price,
          humanReferenceCents: item.humanReferenceCents, customerNominalSavingsCents: accepted ? item.humanReferenceCents - price : 0,
          marginalExecutionCostCents: p.marginalExecutionCostCents, recurringCostCents: recurring(p),
          allocatedSetupCents: p.setupAllocationCents, actualAttempts: p.attemptsPerJob,
          providerOnboardingCents: onboardingCost,
          customerMinutes: p.customerMinutes, invoiceCreated: accepted};
        if (accepted) {
          const invoice = {id: `enterprise-invoice-${f.invoices.length}`, mission: id, week,
            dueWeek: week + c.paymentDelayWeeks, amountCents: price, status: 'pending',
            pays: randomDraw(seed, 'payment', week, buyer.id) < c.paymentProbability,
            refund: randomDraw(seed, 'refund', week, buyer.id) < c.refundProbability};
          f.invoices.push(invoice); f.grossInvoicesCents += price; buyer.spent += price;
          if (c.paymentDelayWeeks === 0) { collectWithFees(week); payBills(f, week, c); }
        }
        jobs.push(job);
      }
    }
    f.balanceHistory.push({week, cashCents: f.cashCents, receivablesCents: receivable(f), obligationsCents: unpaid(f),
      reserveCents: c.reserveCents, availableCashCents: liquidity(f, c), earnedAvailableCents: operatingSurplus(f, c),
      fiscalReserveCents: fiscalReserve(f, c), protectedCashCents: protectedLiquidity(f, c),
      generatedAvailableCents: generated(f, c), cumulativeCollectionsCents: f.grossCollectionsCents,
      accruedCostsCents: sum(Object.values(f.costs)), paidCostsCents: sum(Object.values(f.paidCosts)),
      profileIndex: profileIndex(week, f.investments), insolvent: f.insolvent});
  }
  const canonical = project(f, c);
  const histories = {jobs, choices, decisions, investments: f.investments, balances: f.balanceHistory,
    invoices: f.invoices, bills: f.bills, cash: f.cashEvents};
  const attribution = fundingView({config: {...c, investmentCostBasis: 'full-history', historicalCostTiming: 'opening'}, histories});
  assert(c.initialCashCents + sum(f.cashEvents.map(e => e.amountCents)) === f.cashCents, 'Cash events do not reconcile');
  assert(jobs.every(j => j.accepted || !j.invoiceCreated), 'Rejected work received an invoice');
  assert(f.investments.every(i => i.operatingGeneratedCents >= i.fullCostCents), 'Investment used seed or unavailable receipts');
  const accepted = jobs.filter(j => j.accepted), recurringCosts = sum(jobs.map(j => j.recurringCostCents));
  const recurringOperatingCosts = sum(Object.entries(f.costs).filter(([key]) => key !== 'capability').map(([, value]) => value)) - c.initialSetupCents;
  return {schema: SCHEMA, basis: 'SIMULATED', actualCustomerCollectionsCents: 0, currency: c.currency,
    config: c, seed, maximumInvestments, histories, canonical,
    fundingAttribution: {...attribution, additionalPrudentialFiscalReserveCents: fiscalReserve(f, c),
      finalAvailableAfterPrudentialReserveCents: generated(f, c),
      interpretation: 'Original fixed-reserve attribution is preserved. The additional fiscal reserve is deducted by this adapter before any investment; it is an assumption, not a statutory rate or actual tax assessment.'},
    summary: {opportunities: choices.length, buyerDeclines: choices.filter(x => x.choice === 'defer').length,
      humanChosen: choices.filter(x => x.choice === 'human').length, attempts: f.attempts, accepted: f.accepted,
      rejected: f.rejected, totalExecutionAttempts: sum(jobs.map(j => j.actualAttempts)),
      grossInvoicesCents: f.grossInvoicesCents, grossCollectionsCents: f.grossCollectionsCents,
      refundsCents: f.costs.refund, defaultsCents: f.writtenOffCents, finalCashCents: f.cashCents,
      obligationsCents: unpaid(f), receivablesCents: receivable(f), reserveCents: c.reserveCents,
      fiscalReserveCents: fiscalReserve(f, c), totalProtectedReservesCents: c.reserveCents + fiscalReserve(f, c),
      accruedCostsCents: sum(Object.values(f.costs)), paidCostsCents: sum(Object.values(f.paidCosts)),
      costCategoriesCents: copy(f.costs), fullProjectProfitCents: canonical.economic.summary.scenario.operatingMargin,
      fullProjectCostRecovered: canonical.economic.summary.scenario.operatingMargin >= 0,
      deploymentValueBeforeHistoricalCostCents: canonical.economic.summary.scenario.operatingMargin + c.historicalResearchCents,
      operatingGeneratedAvailableCents: generated(f, c), investmentCount: f.investments.length,
      perAcceptedMarginalExecutionCents: accepted.length ? sum(jobs.map(j => j.marginalExecutionCostCents)) / accepted.length : null,
      perAcceptedDeliveryAndSupportCents: accepted.length ? recurringCosts / accepted.length : null,
      recurringOperatingCostsCents: recurringOperatingCosts,
      perAcceptedRecurringCents: accepted.length ? recurringOperatingCosts / accepted.length : null,
      setupAllocationPerAcceptedCents: accepted.length ? c.initialSetupCents / accepted.length : null,
      historicalAllocationPerAcceptedCents: accepted.length ? c.historicalResearchCents / accepted.length : null,
      capabilityInvestmentCents: sum(f.investments.map(i => i.fullCostCents)),
      perAcceptedFullyAllocatedCents: accepted.length ? sum(Object.values(f.costs)) / accepted.length : null,
      nominalCustomerSavingsCents: sum(accepted.map(j => j.customerNominalSavingsCents)), insolvent: f.insolvent},
    limitations: ['Human prices remain the comparison benchmark; no other AI provider is modeled.',
      'Buyer demand, quality beliefs, attention, money amounts and collections are declared scenarios.',
      'Finite synthetic confirmation measures do not establish field reliability or paying demand.',
      'No token issuance, transfer, appreciation, wallet action or live settlement is represented.',
      'Setup allocations describe unit economics; shared setup is charged once in the cash ledger.',
      'An investment forecast is not a realized return; use same-world fixed-profile controls.']};
}

export function pairedHumanMarket(raw, seed) {
  const c = validateHumanConfig(raw);
  const runs = [0, 1, 2].map(maximumInvestments => simulateHumanMarket(c, seed, {maximumInvestments}));
  const [base, first, full] = runs;
  const protectedCash = run => run.summary.finalCashCents - run.summary.obligationsCents - run.summary.totalProtectedReservesCents;
  const comparisons = [first, full].map((r, i) => ({maximumInvestments: i + 1,
    deltaProjectProfitCents: r.summary.fullProjectProfitCents - base.summary.fullProjectProfitCents,
    deltaCashCents: r.summary.finalCashCents - base.summary.finalCashCents,
    deltaProtectedCashCents: protectedCash(r) - protectedCash(base),
    deltaAccepted: r.summary.accepted - base.summary.accepted,
    operatingFinancedInvestments: r.histories.investments.length,
    allInvestmentsOperatingFinanced: r.histories.investments.every(x => x.operatingGeneratedCents >= x.fullCostCents)}));
  const secondIncremental = full.summary.fullProjectProfitCents - first.summary.fullProjectProfitCents;
  const secondProtectedIncremental = protectedCash(full) - protectedCash(first);
  const repaymentWeek = (invested, control, index, basis) => {
    const investment = invested.histories.investments[index]; if (!investment) return null;
    const value = b => basis === 'protected-cash' ? b.cashCents - b.obligationsCents - b.reserveCents - b.fiscalReserveCents :
      b.cashCents + b.receivablesCents - b.obligationsCents;
    return invested.histories.balances.find((b, i) => b.week >= investment.availableWeek &&
      value(b) > value(control.histories.balances[i]))?.week ?? null;
  };
  const totalProfileUses = (run, index) => run.histories.jobs.filter(j => j.accepted &&
    run.config.profiles.findIndex(p => p.id === j.profileId) >= index + 1).length;
  const uses = (run, index) => run.histories.jobs.filter(j => {
    if (!j.accepted || run.config.profiles.findIndex(p => p.id === j.profileId) < index + 1) return false;
    const before = run.config.profiles[index].classes[j.classId], after = run.config.profiles[index + 1].classes[j.classId];
    return before.supported !== after.supported || before.acceptanceProbability !== after.acceptanceProbability ||
      recurring(before) !== recurring(after);
  }).length;
  return {schema: 'agi-alpha-human-market-paired/v1', seed, configId: c.id, runs, comparisons,
    connectedCycle: {firstInvestmentFunded: first.summary.investmentCount >= 1,
      firstCapabilityAcceptedUses: uses(first, 0), secondCapabilityAcceptedUses: uses(full, 1),
      firstProfileTotalAcceptedUses: totalProfileUses(first, 0), secondProfileTotalAcceptedUses: totalProfileUses(full, 1),
      firstRepaymentWeek: repaymentWeek(first, base, 0, 'protected-cash'), secondRepaymentWeek: repaymentWeek(full, first, 1, 'protected-cash'),
      firstAccruedValueRepaymentWeek: repaymentWeek(first, base, 0, 'accrued'), secondAccruedValueRepaymentWeek: repaymentWeek(full, first, 1, 'accrued'),
      firstRepaysInPairedModel: first.summary.investmentCount >= 1 && uses(first, 0) > 0 &&
        comparisons[0].deltaProjectProfitCents > 0 && comparisons[0].deltaProtectedCashCents > 0,
      secondInvestmentFunded: full.summary.investmentCount >= 2,
      secondIncrementalProjectValueCents: secondIncremental,
      secondIncrementalProtectedCashCents: secondProtectedIncremental,
      finalOperatingGeneratedSurplusCents: full.summary.operatingGeneratedAvailableCents,
      historicalAndFullProjectCostRecovered: full.summary.fullProjectCostRecovered,
      secondRepaysInPairedModel: full.summary.investmentCount >= 2 && uses(full, 1) > 0 && secondIncremental > 0 && secondProtectedIncremental > 0,
      fullCycleWithinModel: full.summary.investmentCount >= 2 && uses(first, 0) > 0 && uses(full, 1) > 0 &&
        comparisons[0].deltaProjectProfitCents > 0 && comparisons[0].deltaProtectedCashCents > 0 &&
        secondIncremental > 0 && secondProtectedIncremental > 0 && comparisons[1].deltaProjectProfitCents > 0 &&
        full.summary.operatingGeneratedAvailableCents > 0},
    interpretation: 'Same random world compares own no-investment, first-only and two-investment policies. Positive value is conditional simulated value, not observed commercial profit.'};
}

export function investmentArithmetic(input) { return calculateInvestment(input); }
