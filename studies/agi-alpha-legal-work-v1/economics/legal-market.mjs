import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve, dirname} from 'node:path';
import {replayLedger, planMission, calculateInvestment} from './inherited/canonical/shadow-ledger.mjs';
import {chooseBuyer, randomDraw} from './inherited/src/market.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const PARAMS = JSON.parse(readFileSync(resolve(HERE, 'parameters.json'), 'utf8'));
const sum = rows => rows.reduce((a, b) => a + b, 0);
const cents = value => Math.round(value);
const assert = (condition, message) => { if (!condition) throw Error(message); };
const hash = value => createHash('sha256').update(value).digest('hex');
const STAGES = ['B', 'C1', 'C', 'D'];
const REF = 'SIMULATION ONLY; conditional professional acceptance, hypothetical CAD receipts and costs; no market or legal acceptance is observed.';

export function validateProduction(input) {
  const records = Array.isArray(input) ? input : input?.records;
  assert(Array.isArray(records) && records.length > 0, 'Nonempty executed production records required');
  const ids = new Set();
  for (const row of records) {
    assert(row && typeof row === 'object', 'Production record must be an object');
    assert(typeof row.case_id === 'string' && /^[A-Za-z0-9._:-]{1,80}$/.test(row.case_id), 'Invalid case_id');
    assert(STAGES.includes(row.arm), 'Use explicit stages B, C1, C and D');
    assert(typeof row.accepted_deterministic === 'boolean', 'Technical acceptance must be explicit');
    assert(['unknown', 'accepted', 'rejected'].includes(row.professional_acceptance), 'Professional acceptance must be explicit');
    assert(Number.isFinite(row.runtime_seconds) && row.runtime_seconds >= 0, 'Finite nonnegative runtime required');
    assert(Number.isInteger(row.attempts) && row.attempts >= 1, 'All attempts must be included');
    assert(typeof row.escalation_required === 'boolean', 'Escalation must be explicit');
    if (row.professional_review_minutes !== undefined && row.professional_review_minutes !== null)
      assert(Number.isFinite(row.professional_review_minutes) && row.professional_review_minutes >= 0, 'Invalid measured review time');
    const id = `${row.arm}:${row.case_id}`;
    assert(!ids.has(id), 'Duplicate aggregated production record'); ids.add(id);
  }
  const byStage = Object.fromEntries(STAGES.map(stage => [stage, records.filter(row => row.arm === stage)]));
  assert(byStage.B.length > 0, 'Baseline B records required');
  const baseIds = byStage.B.map(row => row.case_id).sort();
  for (const stage of STAGES.filter(s => byStage[s].length))
    assert(JSON.stringify(byStage[stage].map(row => row.case_id).sort()) === JSON.stringify(baseIds), 'Matched case identities required');
  return {records, byStage, caseIds: baseIds, summary: Object.fromEntries(STAGES.map(stage => {
    const rows = byStage[stage];
    return [stage, rows.length ? {
      cases: rows.length, technicalAccepted: rows.filter(row => row.accepted_deterministic).length,
      technicalPassRate: rows.filter(row => row.accepted_deterministic).length / rows.length,
      professionallyAccepted: rows.filter(row => row.professional_acceptance === 'accepted').length,
      professionalAcceptanceUnknown: rows.filter(row => row.professional_acceptance === 'unknown').length,
      escalations: rows.filter(row => row.escalation_required).length,
      totalRuntimeSeconds: sum(rows.map(row => row.runtime_seconds)),
      meanRuntimeSeconds: sum(rows.map(row => row.runtime_seconds)) / rows.length,
      meanAttempts: sum(rows.map(row => row.attempts)) / rows.length,
      measuredProfessionalReviewMinutes: rows.every(row => row.professional_review_minutes !== undefined && row.professional_review_minutes !== null)
        ? sum(rows.map(row => row.professional_review_minutes)) / rows.length : null
    } : null];
  }))};
}

export function configuration(overrides = {}) {
  const base = PARAMS.config;
  for (const key of Object.keys(overrides)) assert(Object.hasOwn(base, key), `Unknown parameter ${key}`);
  const c = {...base, ...overrides};
  for (const [key, value] of Object.entries(c)) {
    if (key === 'historicalResearchCostCents' && value === null) continue;
    assert(typeof value === 'number' && Number.isFinite(value) && value >= 0, `Invalid ${key}`);
    if (key.endsWith('Cents')) assert(Number.isSafeInteger(value), `Integer cents required: ${key}`);
  }
  for (const key of ['arrivalProbability', 'professionalAcceptanceProbability', 'collectionProbability', 'capacityRealizationFraction', 'cashRealizationFraction'])
    assert(c[key] <= 1, `Probability/fraction exceeds one: ${key}`);
  assert(c.cashRealizationFraction <= c.capacityRealizationFraction, 'Cash realization cannot exceed valued capacity');
  for (const key of ['weeks', 'buyers', 'paymentDelayWeeks', 'capabilityUsefulLifeWeeks', 'investmentEarliestWeek', 'investmentPauseWeeks'])
    assert(Number.isInteger(c[key]), `Integer required: ${key}`);
  assert(c.weeks >= 1 && c.weeks <= 104 && c.buyers >= 1 && c.buyers <= 40, 'Finite scenario bounds');
  assert(c.expectedBuyerLifetimeJobs > 0, 'Positive buyer lifetime workload assumption required');
  assert(c.capabilityUsefulLifeWeeks >= 1 && c.investmentPauseWeeks >= 1, 'Positive construction pause and useful lifetime required');
  return c;
}

function professionalRate(c) { return c.lawyerHourlyCents * c.laborBurdenFactor; }
function minuteCost(minutes, hourly) { return cents(minutes * hourly / 60); }
function stageMinutes(c, stage, kind) {
  const suffix = stage === 'C1' ? 'C' : stage;
  return c[`${kind}Minutes${suffix}`];
}
function unitCost(c, summary, stage, extraMaintenance = 0) {
  const s = summary[stage]; if (!s) return null;
  const operation = minuteCost(stageMinutes(c, stage, 'operator'), c.providerHourlyCents);
  const correction = minuteCost((1 - s.technicalPassRate) * c.technicalCorrectionMinutes, c.providerHourlyCents);
  const support = minuteCost(c.supportMinutes, c.providerHourlyCents);
  const compute = cents(s.meanRuntimeSeconds / 3600 * c.computeHourlyCents);
  const tools = cents(s.meanAttempts * c.toolCentsPerAttempt);
  return {operation, correction, support, compute, tools, extraMaintenance,
    total: operation + correction + support + compute + tools + extraMaintenance};
}
function caseCost(c, row, stage, extraMaintenance = 0) {
  return minuteCost(stageMinutes(c, stage, 'operator') + c.supportMinutes + (row.accepted_deterministic ? 0 : c.technicalCorrectionMinutes), c.providerHourlyCents)
    + cents(row.runtime_seconds / 3600 * c.computeHourlyCents) + row.attempts * c.toolCentsPerAttempt + extraMaintenance;
}

export function unitEconomics(production, overrides = {}) {
  const c = configuration(overrides), p = validateProduction(production);
  const wage = professionalRate(c), human = minuteCost(c.humanMinutes, wage);
  const onboard = minuteCost(c.buyerOnboardingMinutes / c.expectedBuyerLifetimeJobs, wage);
  const alternative = c.alternativeToolCentsPerJob + minuteCost(c.alternativeReviewMinutes + c.alternativeOnboardingMinutes / c.expectedBuyerLifetimeJobs, wage);
  return {currency: 'CAD', basis: 'CONDITIONAL_COST_SCENARIO', humanOnlyCostCents: human,
    humanOnlyMinutesStatus: 'unmeasured scenario coordinate, not an empirical competent-human task estimate',
    practicalAlternativeCostCents: alternative, practicalAlternativeStatus: 'unexecuted generic competitive proxy, not a vendor quotation',
    stages: Object.fromEntries(STAGES.map(stage => {
      if (!p.summary[stage]) return [stage, null];
      const parts = unitCost(c, p.summary, stage), review = minuteCost(stageMinutes(c, stage, 'review'), wage);
      const attention = review + onboard, buyerTotal = c.offerPriceCents + attention;
      return [stage, {measured: p.summary[stage], providerMarginalCostCents: parts.total, providerMarginalComponentsCents: parts,
        buyerProfessionalReviewCents: review, buyerOnboardingAllocationCents: onboard, offerPriceCents: c.offerPriceCents,
        buyerPricePlusAttentionCents: buyerTotal, customerOpportunityCostSavingCents: human - buyerTotal,
        customerAvoidedPayrollCashCents: minuteCost(Math.max(0, c.humanMinutes - stageMinutes(c, stage, 'review') - c.buyerOnboardingMinutes / c.expectedBuyerLifetimeJobs), wage) * c.cashRealizationFraction,
        customerNetCashSavingCents: cents(minuteCost(Math.max(0, c.humanMinutes - stageMinutes(c, stage, 'review') - c.buyerOnboardingMinutes / c.expectedBuyerLifetimeJobs), wage) * c.cashRealizationFraction - c.offerPriceCents),
        priceCeilingAgainstHumanCents: Math.max(0, human - attention),
        priceCeilingAgainstAlternativeCents: Math.max(0, alternative - attention),
        residualReviewBreakEvenAgainstHumanMinutes: (human - c.offerPriceCents - onboard) * 60 / wage,
        residualReviewBreakEvenAgainstAlternativeMinutes: (alternative - c.offerPriceCents - onboard) * 60 / wage,
        historicalFullyAllocatedCostCents: null}];
    })), scope: 'Every review minute is a declared scenario unless separately measured. Professional review, onboarding, failed attempts and support are charged. Full allocated cost remains unknown without historical research cost and actual workload.'};
}

export function investmentSensitivity(production) {
  const p = validateProduction(production), rows = [];
  for (const correctionMinutes of [0, 2, 5, 10, 20, 45]) for (const maintenanceCents of [0, 25, 100])
    for (const reuses of [12, 50, 100, 250]) for (const [from, to] of [['B', 'C1'], ['B', 'D'], ['C1', 'C']]) {
      if (!p.summary[from] || !p.summary[to]) continue;
      const c = configuration({technicalCorrectionMinutes: correctionMinutes});
      const second = to === 'C', fixed = second ? c.secondCapabilityConstructionCents : c.capabilityConstructionCents;
      const failed = second ? c.secondCapabilityFailedConstructionCents : c.capabilityFailedConstructionCents;
      const saving = unitCost(c, p.summary, from).total - unitCost(c, p.summary, to).total;
      rows.push({from, to, correctionMinutesAssumed: correctionMinutes, maintenancePerUseCentsAssumed: maintenanceCents,
        reusesAssumed: reuses, usefulLifetimeWeeksAssumed: c.capabilityUsefulLifeWeeks,
        minimumGrossSavingPerUseCents: Math.ceil((fixed + failed) / reuses) + maintenanceCents,
        assessment: calculateInvestment({constructionCostMinor: fixed, failedConstructionCostMinor: failed,
          maintenancePerReuseMinor: maintenanceCents, expectedSavingPerReuseMinor: saving, remainingReuses: reuses}),
        qualification: 'Conditional direct-cost threshold; not demand, professional productivity, or realized profit. Simulation separately charges service interruption and business costs.'});
    }
  return {schema: 'agi-alpha-legal-investment-sensitivity/v1', currency: 'CAD', rows};
}

function addPeriod(events, id, totals, initialReserve) {
  events.push({id: `${id}:mission`, type: 'mission', missionId: id, acceptance: 'accepted', reference: REF});
  const row = (type, category, amountMinor, basis = 'assumed') => ({id: `${id}:${type}:${category}`, type, missionId: id,
    reference: REF, category, amountMinor, basis});
  events.push(row('revenue', 'collected', 0, 'observed'), row('revenue', 'price', totals.collections),
    ...['delivery', 'business', 'capability', 'maintenance'].map(category => row('cost', category, totals[category])),
    row('reserve', 'reliability', initialReserve), row('obligation', 'unpaid', 0));
}
function snapshot(events, seed) {
  const ledger = {schema: 'alpha-shadow-ledger/v1', currency: 'CAD', events};
  const result = replayLedger(ledger, {reinvestmentBps: 10000});
  return {ledger, result, cashAfterReserve: seed + (result.scenario.afterReserves ?? 0),
    earnedAvailable: result.scenario.availableSurplus ?? 0};
}
function availableWithPeriod(events, seed, id, totals, reserve) {
  const copy = [...events]; addPeriod(copy, id, totals, reserve); return snapshot(copy, seed);
}

export function actualLedger(production) {
  const p = validateProduction(production), events = [];
  for (const stage of STAGES.filter(s => p.summary[s])) {
    const allAccepted = p.byStage[stage].every(row => row.professional_acceptance === 'accepted');
    const anyUnknown = p.byStage[stage].some(row => row.professional_acceptance === 'unknown');
    const reference = 'Research production only. Technical acceptance is not professional legal acceptance. No customers or payments. Full actual cost unmetered.';
    const mission = planMission({missionId: `actual-${stage}`, currency: 'CAD', reference,
      acceptance: anyUnknown ? 'unknown' : allAccepted ? 'accepted' : 'rejected', totalCollectedCents: 0,
      priceAssumptionCents: null, totalOperatingCostCents: null, operatingCostsComplete: false,
      capabilityCostCents: null, reserveCents: null, obligationCents: null});
    events.push(...mission.ledger.events);
  }
  const ledger = {schema: 'alpha-shadow-ledger/v1', currency: 'CAD', events};
  return {ledger, summary: replayLedger(ledger), observedOutcome: 'NO_OBSERVED_COMMERCIAL_OR_SELF_FINANCING_RESULT'};
}

export function simulateLegal(production, overrides = {}, seed = 1, strategy = 'reinvest') {
  assert(['baseline', 'retained-from-start', 'full-from-start', 'conventional-from-start', 'reinvest'].includes(strategy), 'Unknown strategy');
  const c = configuration(overrides), p = validateProduction(production), events = [], weeks = [], jobs = [], decisions = [];
  const byCase = Object.fromEntries(STAGES.map(stage => [stage, Object.fromEntries(p.byStage[stage].map(row => [row.case_id, row]))]));
  const wage = professionalRate(c), valueWage = wage * c.capacityRealizationFraction;
  let stage = ({'retained-from-start': 'C1', 'full-from-start': 'C', 'conventional-from-start': 'D'})[strategy] || 'B';
  assert(p.summary[stage], `Executed stage ${stage} unavailable`);
  let expired = false, pausedUntil = -1, expiresWeek = stage === 'B' ? Infinity : c.capabilityUsefulLifeWeeks;
  let initialConstruction = stage === 'B' ? 0 : c.capabilityConstructionCents + c.capabilityFailedConstructionCents;
  if (stage === 'C') initialConstruction += c.secondCapabilityConstructionCents + c.secondCapabilityFailedConstructionCents;
  assert(initialConstruction <= Math.max(0, c.initialSeedCents - c.reserveCents), 'Declared seed cannot fund opening construction and reserve');
  let purchasedFirst = stage !== 'B', purchasedSecond = stage === 'C', insolvent = false;
  let firstAvoided = 0, secondAvoided = 0, firstUses = 0, secondUses = 0, firstRepaymentWeek = null, secondRepaymentWeek = null;
  let firstFixed = stage === 'B' ? 0 : c.capabilityConstructionCents + c.capabilityFailedConstructionCents;
  let secondFixed = stage === 'C' ? c.secondCapabilityConstructionCents + c.secondCapabilityFailedConstructionCents : 0;
  let firstEstimatedPauseContribution = 0;
  const onboarded = new Set(), receivables = [], acceptedHistory = [], investments = [];
  const finalWeek = c.weeks + c.paymentDelayWeeks;
  let acceptedCount = 0, rejectedCount = 0, opportunityCount = 0, buyerDeclines = 0, alternatives = 0;
  let customerMinutes = 0, customerPriceCents = 0, avoidedHumanMinutes = 0;
  for (let week = 0; week <= finalWeek; week++) {
    const id = `w${week}`, totals = {collections: 0, delivery: 0, business: 0, capability: 0, maintenance: 0};
    const reserve = week === 0 ? c.reserveCents : 0;
    for (const invoice of receivables.filter(row => !row.processed && row.due <= week)) {
      invoice.processed = true; if (invoice.pays) totals.collections += invoice.amount;
    }
    if (week === 0) totals.capability = initialConstruction;
    if (week >= expiresWeek && stage !== 'B') { stage = 'B'; expired = true; }
    let cash = availableWithPeriod(events, c.initialSeedCents, id, totals, reserve);
    if (week < c.weeks && !insolvent) {
      const standing = c.fixedWeeklyCents + c.maintenanceWeeklyCents;
      if (cash.cashAfterReserve < standing) insolvent = true;
      else { totals.business += c.fixedWeeklyCents; totals.maintenance += c.maintenanceWeeklyCents; }
      cash = availableWithPeriod(events, c.initialSeedCents, id, totals, reserve);
      if (strategy === 'reinvest' && !insolvent && !expired && week >= c.investmentEarliestWeek && week >= pausedUntil) {
        const candidates = stage === 'B' && !purchasedFirst ? ['C1', 'D'] :
          stage === 'C1' && !purchasedSecond && firstUses >= 4 && firstAvoided >= firstFixed + firstEstimatedPauseContribution ? ['C'] : [];
        const rate = sum(acceptedHistory.slice(Math.max(0, week - 8), week)) / Math.max(1, Math.min(week, 8));
        const horizon = Math.max(0, Math.min(c.capabilityUsefulLifeWeeks, c.weeks - week - c.investmentPauseWeeks,
          stage === 'C1' ? expiresWeek - week - c.investmentPauseWeeks : Infinity));
        const forecast = Math.floor(rate * horizon), currentUnit = unitCost(c, p.summary, stage).total;
        const choices = candidates.filter(s => p.summary[s]).map(candidate => {
          const second = candidate === 'C', fixed = second ? c.secondCapabilityConstructionCents : c.capabilityConstructionCents;
          const failed = second ? c.secondCapabilityFailedConstructionCents : c.capabilityFailedConstructionCents;
          const maintenance = second ? c.secondCapabilityMaintenancePerUseCents : c.capabilityMaintenancePerUseCents;
          const saving = currentUnit - unitCost(c, p.summary, candidate).total;
          const investment = calculateInvestment({constructionCostMinor: fixed, failedConstructionCostMinor: failed,
            maintenancePerReuseMinor: maintenance, expectedSavingPerReuseMinor: saving, remainingReuses: forecast});
          const foregone = cents(rate * c.investmentPauseWeeks * Math.max(0, c.offerPriceCents * c.professionalAcceptanceProbability * c.collectionProbability - currentUnit));
          return {candidate, investment, foregoneContributionCents: foregone, expectedNetAfterPauseCents: investment.netBenefit - foregone,
            fundingRequiredCents: fixed + failed, earnedAvailableCents: cash.earnedAvailable, remainingWeeks: horizon};
        }).sort((a, b) => b.expectedNetAfterPauseCents - a.expectedNetAfterPauseCents || a.candidate.localeCompare(b.candidate));
        for (const choice of choices) decisions.push({week, ...choice, action: 'considered', basis: 'CONDITIONAL_MODEL_NO_ACTUAL_INVESTMENT'});
        const best = choices[0];
        if (best && best.expectedNetAfterPauseCents > 0 && best.earnedAvailableCents >= best.fundingRequiredCents && cash.cashAfterReserve >= best.fundingRequiredCents) {
          const dependencyExpiry = stage === 'C1' ? expiresWeek : Infinity;
          totals.capability += best.fundingRequiredCents; stage = best.candidate; pausedUntil = week + c.investmentPauseWeeks;
          expiresWeek = Math.min(dependencyExpiry, pausedUntil + best.remainingWeeks);
          if (stage === 'C') { purchasedSecond = true; secondFixed = best.fundingRequiredCents; }
          else { purchasedFirst = true; firstFixed = best.fundingRequiredCents; firstEstimatedPauseContribution = best.foregoneContributionCents; }
          investments.push({week, ...best, funding: 'available-earned-operating-surplus-only', activatedWeek: pausedUntil,
            expiresWeek, stage, actualFinancialAction: false});
        }
      }
      let acceptedThisWeek = 0;
      for (let buyer = 0; buyer < c.buyers; buyer++) {
        if (randomDraw(seed, 'arrival', week, buyer) >= c.arrivalProbability) continue;
        opportunityCount++;
        const caseId = p.caseIds[Math.floor(randomDraw(seed, 'case', week, buyer) * p.caseIds.length)];
        const humanEffort = minuteCost(c.humanMinutes, valueWage), quality = c.professionalAcceptanceProbability;
        const value = cents(humanEffort * c.buyerValueMultiplier + c.qualityLossCents * (1 - quality));
        const buyerSpec = {valueCents: value, errorLossCents: c.qualityLossCents};
        const offers = [{id: 'human-normal-tools', priceCents: 0, quality, effortCents: humanEffort, delayCents: 0, switchCents: 0},
          {id: 'practical-alternative-proxy', priceCents: c.alternativeToolCentsPerJob, quality,
            effortCents: minuteCost(c.alternativeReviewMinutes + c.alternativeOnboardingMinutes / c.expectedBuyerLifetimeJobs, valueWage), delayCents: 0, switchCents: 0}];
        const row = byCase[stage][caseId], extraMaintenance = stage === 'B' ? 0 : c.capabilityMaintenancePerUseCents + (stage === 'C' ? c.secondCapabilityMaintenancePerUseCents : 0);
        const actualCost = caseCost(c, row, stage, extraMaintenance);
        const onboard = onboarded.has(buyer) ? 0 : minuteCost(c.providerOnboardingMinutes, c.providerHourlyCents);
        const acquire = onboarded.has(buyer) ? 0 : c.acquisitionCentsPerProspect;
        cash = availableWithPeriod(events, c.initialSeedCents, id, totals, reserve);
        const ownEffort = minuteCost(stageMinutes(c, stage, 'review') + c.buyerOnboardingMinutes / c.expectedBuyerLifetimeJobs, valueWage);
        const alternativeBurden = Math.min(...offers.map(offer => offer.priceCents + offer.effortCents));
        if (!insolvent && week >= pausedUntil && cash.cashAfterReserve >= actualCost + onboard + acquire &&
            c.offerPriceCents + ownEffort + c.buyerMinimumSavingsCents <= alternativeBurden)
          offers.push({id: 'agi-alpha', priceCents: c.offerPriceCents, quality,
            effortCents: ownEffort, delayCents: 0, switchCents: 0});
        if (!onboarded.has(buyer) && !insolvent && cash.cashAfterReserve >= acquire) totals.business += acquire;
        const picked = chooseBuyer(offers, buyerSpec, {choiceModel: 'deterministic'}, 0.5);
        if (picked.choice !== 'agi-alpha') {
          if (picked.choice === 'defer') buyerDeclines++; else alternatives++;
          jobs.push({week, buyer, case_id: caseId, choice: picked.choice, basis: 'SIMULATED_BUYER_CHOICE'}); continue;
        }
        if (!onboarded.has(buyer)) { totals.business += onboard; onboarded.add(buyer); customerMinutes += c.buyerOnboardingMinutes; }
        totals.delivery += actualCost - extraMaintenance; totals.maintenance += extraMaintenance;
        if (stage !== 'B') {
          const firstStage = stage === 'C' ? 'C1' : stage;
          firstAvoided += caseCost(c, byCase.B[caseId], 'B') - caseCost(c, byCase[firstStage][caseId], firstStage, c.capabilityMaintenancePerUseCents);
          firstUses++;
          if (firstAvoided >= firstFixed && firstRepaymentWeek === null) firstRepaymentWeek = week;
        }
        if (stage === 'C') {
          secondAvoided += caseCost(c, byCase.C1[caseId], 'C1', c.capabilityMaintenancePerUseCents) - actualCost;
          secondUses++;
          if (secondAvoided >= secondFixed && secondRepaymentWeek === null) secondRepaymentWeek = week;
        }
        const accepted = row.accepted_deterministic && randomDraw(seed, 'professional-acceptance', week, buyer) < quality;
        customerMinutes += stageMinutes(c, stage, 'review');
        const invoice = accepted ? {due: week + c.paymentDelayWeeks, amount: c.offerPriceCents,
          pays: randomDraw(seed, 'collection', week, buyer) < c.collectionProbability, processed: false} : null;
        avoidedHumanMinutes += c.humanMinutes;
        if (invoice) { receivables.push(invoice); customerPriceCents += c.offerPriceCents; acceptedCount++; acceptedThisWeek++; }
        else { rejectedCount++; customerMinutes += c.humanMinutes; }
        jobs.push({week, buyer, case_id: caseId, stage, choice: picked.choice, acceptedSimulated: accepted,
          technicalCasePassed: row.accepted_deterministic, deliveryCostCents: actualCost, invoiceCents: invoice?.amount || 0,
          basis: 'SIMULATED_ACCEPTANCE_NOT_INFERRED_FROM_TECHNICAL_TESTS'});
      }
      acceptedHistory.push(acceptedThisWeek);
    }
    for (const invoice of receivables.filter(row => !row.processed && row.due <= week)) {
      invoice.processed = true; if (invoice.pays) totals.collections += invoice.amount;
    }
    addPeriod(events, id, totals, reserve);
    cash = snapshot(events, c.initialSeedCents);
    if (cash.cashAfterReserve < 0) insolvent = true;
    weeks.push({week, stage, pausedUntil, expiresWeek: Number.isFinite(expiresWeek) ? expiresWeek : null,
      ...totals, earnedAvailableCents: cash.earnedAvailable, cashAfterReserveCents: cash.cashAfterReserve, insolvent});
  }
  const final = snapshot(events, c.initialSeedCents), s = final.result.scenario;
  assert(final.result.observed.revenue === 0, 'Hypothetical receipts contaminated observed collections');
  assert(investments.every(row => row.earnedAvailableCents >= row.fundingRequiredCents), 'Seed cannot finance a claimed earned investment');
  assert(jobs.every(row => row.acceptedSimulated !== false || row.invoiceCents === 0), 'Rejected attempt invoiced');
  const historical = c.historicalResearchCostCents;
  const categories = Object.fromEntries(['delivery', 'business', 'capability', 'maintenance'].map(category =>
    [category, sum(events.filter(event => event.type === 'cost' && event.category === category).map(event => event.amountMinor))]));
  return {schema: 'agi-alpha-legal-market/v1', currency: 'CAD', basis: 'CONDITIONAL_SIMULATION', seed, strategy, config: c,
    productionSummary: p.summary, summary: {opportunities: opportunityCount, buyerDeclines, alternativeChoices: alternatives,
      providerAttempts: acceptedCount + rejectedCount, simulatedAccepted: acceptedCount, simulatedRejected: rejectedCount,
      simulatedCollectionsCents: s.revenue, allProviderCostsCents: s.fullCost, cashOperatingProfitCents: s.operatingMargin,
      providerCostCategoriesCents: categories,
      recurringCostPerSimulatedAcceptedCents: acceptedCount ? cents((categories.delivery + categories.business + categories.maintenance) / acceptedCount) : null,
      modeledAllocatedCostPerSimulatedAcceptedCents: acceptedCount ? cents(s.fullCost / acceptedCount) : null,
      heldReserveCents: s.reserve, availableOperatingSurplusCents: s.availableSurplus, unpaidObligationsCents: s.unpaidObligations,
      remainingSeedPlusEarnedCashCents: c.initialSeedCents + s.operatingMargin,
      historicalResearchCostCents: historical, fullyAllocatedProfitCents: historical === null ? null : s.operatingMargin - historical,
      researchCostRecovered: historical === null ? null : s.operatingMargin >= historical,
      firstInvestmentFunded: strategy === 'reinvest' && investments.length >= 1,
      secondInvestmentFunded: strategy === 'reinvest' && investments.some(row => row.stage === 'C'),
      firstCapabilityUses: firstUses, secondCapabilityUses: secondUses,
      firstModeledAvoidedCostCents: firstAvoided, secondModeledAvoidedCostCents: secondAvoided,
      firstConstructionAndFailedCostCents: firstFixed, secondConstructionAndFailedCostCents: secondFixed,
      firstEstimatedPauseContributionCents: firstEstimatedPauseContribution,
      firstDirectRepaymentWeek: firstRepaymentWeek, secondDirectRepaymentWeek: secondRepaymentWeek,
      firstDirectCostRepaid: firstUses > 0 && firstAvoided >= firstFixed,
      secondDirectCostRepaid: secondUses > 0 && secondAvoided >= secondFixed,
      customerProfessionalAndIntegrationMinutes: customerMinutes,
      customerOpportunityMinutesSaved: avoidedHumanMinutes - customerMinutes,
      customerInvoicedCents: customerPriceCents,
      customerNetAvoidedCashCents: cents(Math.max(0, avoidedHumanMinutes - customerMinutes) * wage / 60 * c.cashRealizationFraction - customerPriceCents),
      observedCollectionsCents: 0, insolvent},
    canonicalLedger: final.ledger, canonicalSummary: final.result, weekly: weeks, jobs, investmentDecisions: decisions, investments,
    limits: ['Professional acceptance, review effort, demand and all monetary costs remain conditional assumptions.',
      'Technical pass rates affect only assumed correction burden; they are not legal-accuracy probabilities.',
      'Human-only, buyer review and commercial-alternative timings were not measured; generic price is not a vendor quote.',
      'Prices are support-packet prices, not complete legal-service invoices; professional work stays in the buyer cost.',
      'No historical cost-recovery conclusion while historicalResearchCostCents is null.',
      'No Nash-equilibrium or optimal pricing claim. No $AGIALPHA earnings, funding or appreciation.']};
}

function quantile(values, fraction) { const a = [...values].sort((a, b) => a - b); return a[Math.floor((a.length - 1) * fraction)]; }
function describe(values) { return {mean: sum(values) / values.length, min: Math.min(...values), p10: quantile(values, 0.1),
  median: quantile(values, 0.5), p90: quantile(values, 0.9), max: Math.max(...values), negativeShare: values.filter(x => x < 0).length / values.length}; }

export function campaign(production, seeds = 24) {
  assert(Number.isInteger(seeds) && seeds >= 1 && seeds <= 100, 'Use 1-100 paired worlds');
  const summaries = [], worlds = [];
  for (const scenario of PARAMS.scenario_definitions) {
    const rows = [];
    for (let seed = 1; seed <= seeds; seed++) {
      const baseline = simulateLegal(production, scenario.changes, seed, 'baseline');
      const reinvest = simulateLegal(production, scenario.changes, seed, 'reinvest');
      const c1 = simulateLegal(production, scenario.changes, seed, 'retained-from-start');
      const full = simulateLegal(production, scenario.changes, seed, 'full-from-start');
      const conventional = simulateLegal(production, scenario.changes, seed, 'conventional-from-start');
      const row = {scenario: scenario.id, seed, baseline: baseline.summary, reinvest: reinvest.summary,
        retainedFromStart: c1.summary, fullFromStart: full.summary, conventional: conventional.summary,
        reinvestMinusBaselineCents: reinvest.summary.cashOperatingProfitCents - baseline.summary.cashOperatingProfitCents,
        retainedMinusBaselineCents: c1.summary.cashOperatingProfitCents - baseline.summary.cashOperatingProfitCents,
        fullMinusConventionalCents: full.summary.cashOperatingProfitCents - conventional.summary.cashOperatingProfitCents};
      rows.push(row); worlds.push(row);
    }
    summaries.push({scenario: scenario.id, worlds: seeds,
      baselineProfitCents: describe(rows.map(x => x.baseline.cashOperatingProfitCents)),
      reinvestProfitCents: describe(rows.map(x => x.reinvest.cashOperatingProfitCents)),
      reinvestMinusBaselineCents: describe(rows.map(x => x.reinvestMinusBaselineCents)),
      retainedMinusBaselineCents: describe(rows.map(x => x.retainedMinusBaselineCents)),
      fullMinusConventionalCents: describe(rows.map(x => x.fullMinusConventionalCents)),
      firstInvestmentWorlds: rows.filter(x => x.reinvest.firstInvestmentFunded).length,
      secondInvestmentWorlds: rows.filter(x => x.reinvest.secondInvestmentFunded).length,
      simulatedCollectionsCents: describe(rows.map(x => x.reinvest.simulatedCollectionsCents))});
  }
  return {schema: 'agi-alpha-legal-economics-campaign/v1', basis: 'SCENARIO_DISTRIBUTIONS_NOT_EMPIRICAL_CONFIDENCE_INTERVALS',
    currency: 'CAD', pairedWorldsPerScenario: seeds, actualLedger: actualLedger(production), unitEconomics: unitEconomics(production),
    investmentSensitivity: investmentSensitivity(production), summaries, worlds};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [, , input, output, count] = process.argv;
  assert(input && output, 'Usage: node legal-market.mjs PRODUCTION_JSON OUTPUT_DIRECTORY [SEEDS]');
  const raw = readFileSync(input), production = JSON.parse(raw), result = campaign(production, Number(count || 24));
  mkdirSync(output, {recursive: true});
  writeFileSync(resolve(output, 'campaign.json'), JSON.stringify(result, null, 2) + '\n');
  writeFileSync(resolve(output, 'reference-ledger.json'), JSON.stringify(simulateLegal(production, {}, 1), null, 2) + '\n');
  writeFileSync(resolve(output, 'input-provenance.json'), JSON.stringify({productionSHA256: hash(raw),
    sourceSHA256: hash(readFileSync(fileURLToPath(import.meta.url))), parametersSHA256: hash(readFileSync(resolve(HERE, 'parameters.json'))),
    actualCollectionsCents: 0, executedAt: new Date().toISOString()}, null, 2) + '\n');
  process.stdout.write(JSON.stringify({output, scenarios: result.summaries.length, pairedWorldsPerScenario: result.pairedWorldsPerScenario,
    actualCollectionsCents: result.actualLedger.summary.observed.revenue, actualSurplus: result.actualLedger.summary.observed.availableSurplus}) + '\n');
}
