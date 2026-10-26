// SPDX-License-Identifier: Apache-2.0
import {calculateInvestment, planMission} from '../../heritage/graph-foundations/market/inherited/upstream/canonical/shadow-ledger.mjs';
import {randomDraw} from '../../heritage/graph-foundations/market/inherited/upstream/src/market.mjs';
import {PROTOCOL, laborCents, cpuMicroUSD, sensitivityCells} from './protocol.mjs';
import {
  createLedger, accrueCost, invoice, settleWeek, availableInvestmentCents,
  fundInvestment, ledgerSnapshot,
} from './ledger.mjs';

const ARM_IDS = ['A', 'B', 'C', 'D'];
const SHA256 = /^[a-f0-9]{64}$/;
const sum = values => values.reduce((total, value) => total + value, 0);
const own = (object, key) => Object.hasOwn(object, key);
const clone = value => JSON.parse(JSON.stringify(value));

export function validateCalibration(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw Error('Calibration object required');
  const permitted = ['schema', 'measurementKind', 'acceptanceScope', 'acceptanceSpecificationSha256',
    'acceptanceEquivalent', 'sourceManifestSha256', 'evidence', 'arms', 'sourceAvailability', 'commonCosts'];
  if (Object.keys(input).some(key => !permitted.includes(key))) throw Error('Unknown calibration field');
  if (input.schema !== 'agi-alpha.work-discovery.calibration.v1' ||
      input.measurementKind !== 'EXECUTED_PUBLIC_LOCAL') throw Error('Executed public-local calibration required');
  if (typeof input.acceptanceScope !== 'string' || input.acceptanceScope.length < 10 ||
      input.acceptanceScope.length > 1000 || typeof input.acceptanceEquivalent !== 'boolean') {
    throw Error('Explicit matched acceptance scope and disposition required');
  }
  for (const key of ['acceptanceSpecificationSha256', 'sourceManifestSha256']) {
    if (!SHA256.test(input[key])) throw Error(`SHA-256 required: ${key}`);
  }
  if (!Array.isArray(input.evidence) || input.evidence.length === 0 || input.evidence.length > 100) {
    throw Error('Calibration evidence bindings required');
  }
  for (const evidence of input.evidence) {
    if (!evidence || Object.keys(evidence).some(key => !['path', 'sha256'].includes(key)) ||
        typeof evidence.path !== 'string' || !evidence.path || evidence.path.startsWith('/') ||
        evidence.path.includes('\\') || evidence.path.split('/').some(part => !part || part === '..' || part === '.') ||
        !SHA256.test(evidence.sha256)) throw Error('Invalid relative evidence binding');
  }
  if (!input.arms || Object.keys(input.arms).sort().join(',') !== ARM_IDS.join(',')) throw Error('Exactly four measured arms required');
  for (const id of ARM_IDS) {
    const arm = input.arms[id];
    if (!arm || Object.keys(arm).sort().join(',') !==
        ['accepted', 'attempts', 'inputBlocked', 'cpuSecondsMean', 'wallSecondsMean',
          'cpuSecondsAvailableMean', 'wallSecondsAvailableMean', 'cpuSecondsBlockedMean',
          'wallSecondsBlockedMean'].sort().join(',')) throw Error(`Invalid measured arm ${id}`);
    if (!Number.isSafeInteger(arm.attempts) || arm.attempts < 1 || arm.attempts > 1_000_000 ||
        !Number.isSafeInteger(arm.inputBlocked) || arm.inputBlocked < 0 || arm.inputBlocked > arm.attempts ||
        !Number.isSafeInteger(arm.accepted) || arm.accepted < 0 || arm.accepted > arm.attempts - arm.inputBlocked) {
      throw Error(`Invalid observed acceptance counts for ${id}`);
    }
    for (const key of ['cpuSecondsMean', 'wallSecondsMean', 'cpuSecondsAvailableMean', 'wallSecondsAvailableMean',
      'cpuSecondsBlockedMean', 'wallSecondsBlockedMean']) {
      if (typeof arm[key] !== 'number' || !Number.isFinite(arm[key]) || arm[key] < 0 || arm[key] > 1_000_000) {
        throw Error(`Invalid observed ${key} for ${id}`);
      }
    }
    for (const dimension of ['cpu', 'wall']) {
      const expected = (arm[`${dimension}SecondsAvailableMean`] * (arm.attempts - arm.inputBlocked) +
        arm[`${dimension}SecondsBlockedMean`] * arm.inputBlocked) / arm.attempts;
      if (Math.abs(arm[`${dimension}SecondsMean`] - expected) > 1e-8) throw Error('Planned-case cost denominator does not reconcile');
    }
  }
  const available = input.sourceAvailability;
  if (!available || available.planned !== input.arms.A.attempts || available.inputBlocked !== input.arms.A.inputBlocked ||
      available.available !== available.planned - available.inputBlocked ||
      available.scenarioProbability !== available.available / available.planned ||
      typeof available.interpretation !== 'string') throw Error('Complete source-availability scenario required');
  if (ARM_IDS.some(id => input.arms[id].attempts !== available.planned || input.arms[id].inputBlocked !== available.inputBlocked)) {
    throw Error('Common source gate must preserve identical planned denominators');
  }
  const commonKeys = ['experimentalAcquisitionCpuSecondsPerPlanned', 'experimentalAcquisitionWallSecondsPerPlanned',
    'experimentalArmSharingDivisor', 'standaloneAcquisitionCpuSecondsPerPlanned',
    'standaloneAcquisitionWallSecondsPerPlanned', 'acquisitionSessionOverheadCpuSecondsPerPlanned',
    'acquisitionSessionOverheadWallSecondsPerPlanned', 'driverCpuSecondsPerPlanned', 'driverWallSecondsPerPlanned', 'allocation'];
  if (!input.commonCosts || Object.keys(input.commonCosts).sort().join('|') !== commonKeys.sort().join('|')) {
    throw Error('Explicit common acquisition and driver cost allocation required');
  }
  for (const key of commonKeys.filter(key => key !== 'allocation')) {
    if (!Number.isFinite(input.commonCosts[key]) || input.commonCosts[key] < 0) throw Error('Unknown or invalid common execution cost');
  }
  if (input.commonCosts.experimentalArmSharingDivisor !== 4 || typeof input.commonCosts.allocation !== 'string') {
    throw Error('Standalone cost allocation must explicitly remove experimental arm sharing');
  }
  for (const dimension of ['Cpu', 'Wall']) {
    const allocated = input.commonCosts[`experimentalAcquisition${dimension}SecondsPerPlanned`] * 4 +
      input.commonCosts[`acquisitionSessionOverhead${dimension}SecondsPerPlanned`];
    if (Math.abs(input.commonCosts[`standaloneAcquisition${dimension}SecondsPerPlanned`] - allocated) > 1e-8) {
      throw Error('Standalone acquisition allocation does not reconcile');
    }
  }
  return clone(input);
}

export function openingCostItems(cell, protocol = PROTOCOL) {
  const cost = protocol.costBundles[cell.costBundle];
  return {
    historical_discovery: laborCents(cost.historicalDiscoveryMinutes, protocol),
    historical_failed_discovery: laborCents(cost.historicalFailedDiscoveryMinutes, protocol),
    historical_inference: cost.historicalInferenceCents,
    ordinary_setup: laborCents(cost.setupMinutes, protocol) + cost.setupOtherCents,
  };
}

export function prospectiveCost(cell, {calibration, laborEfficiency = 1, protocol = PROTOCOL} = {}) {
  if (!Number.isFinite(laborEfficiency) || laborEfficiency <= 0) throw Error('Positive labor efficiency required');
  if (!calibration?.sourceAvailability || !calibration.commonCosts) throw Error('Explicit execution calibration required for full-cost pricing');
  const cost = protocol.costBundles[cell.costBundle];
  const pricing = protocol.pricing;
  const sourceProbability = calibration.sourceAvailability.scenarioProbability;
  const availableCases = calibration.arms.A.attempts - calibration.arms.A.inputBlocked;
  const conditionalProbability = protocol.market.commonExecutionStressSuccessProbability *
    (availableCases ? calibration.arms.A.accepted / availableCases : 0);
  const rejectionProbability = 1 - conditionalProbability;
  const modeledAttemptCount = 1 + rejectionProbability;
  const modeledFailedAttempts = rejectionProbability + rejectionProbability ** 2;
  const expectedPaidProbability = sourceProbability * (1 - rejectionProbability ** 2) * protocol.market.paymentProbability;
  const labor = minutes => laborCents(minutes * laborEfficiency, protocol);
  const common = calibration.commonCosts, a = calibration.arms.A;
  const expectedCPUSecondsPerIntended = common.standaloneAcquisitionCpuSecondsPerPlanned +
    common.driverCpuSecondsPerPlanned * (1 + sourceProbability * rejectionProbability) +
    sourceProbability * modeledAttemptCount * a.cpuSecondsAvailableMean +
    (1 - sourceProbability) * a.cpuSecondsBlockedMean;
  const itemsCents = {
    deliveryAndVerification: labor(sourceProbability * cost.residualMinutesPerAttempt * modeledAttemptCount),
    rejectedAttemptCorrection: labor(sourceProbability * protocol.market.correctionMinutesPerRejectedAttempt * modeledFailedAttempts),
    unavailableSourceTriage: labor((1 - sourceProbability) * protocol.market.correctionMinutesPerRejectedAttempt),
    support: labor(sourceProbability * cost.supportMinutesPerOrder),
    onboardingAllocation: Math.ceil(labor(sourceProbability * cost.providerOnboardingMinutes) /
      pricing.assumedCustomerReusesForOnboardingAllocation),
    weeklyBusinessAllocation: Math.ceil(labor(cost.weeklyBusinessMinutes) / pricing.referenceJobsPerWeek),
    baseMaintenanceAllocation: Math.ceil(labor(cost.weeklyBaseMaintenanceMinutes) / pricing.referenceJobsPerWeek),
    toolsAllocation: Math.ceil(cost.weeklyToolCents / pricing.referenceJobsPerWeek),
    ordinarySetupAllocation: Math.ceil((labor(cost.setupMinutes) + cost.setupOtherCents) /
      (protocol.campaign.weeks * pricing.referenceJobsPerWeek)),
    meteredComputeAllowance: Math.max(pricing.commonComputeAllowanceCentsPerOrder,
      Math.ceil(expectedCPUSecondsPerIntended * protocol.rates.cpuUSDPerHour * 100 / 3600)),
  };
  const expectedCostCentsPerIntended = sum(Object.values(itemsCents));
  return {prospectiveCostCents: expectedPaidProbability > 0 ?
    Math.ceil(expectedCostCentsPerIntended / expectedPaidProbability) : null,
  expectedCostCentsPerIntended, expectedPaidProbability, sourceProbability, conditionalProbability,
  expectedCPUSecondsPerIntended, itemsCents, modeledAttemptCount, laborEfficiency};
}

export function selectTariff(cell, protocol = PROTOCOL, calibration) {
  const costing = prospectiveCost(cell, {protocol, calibration});
  const {prospectiveCostCents, modeledAttemptCount} = costing;
  const pricing = protocol.pricing;
  const grid = pricing.tariffMinutes.map(minutes => laborCents(minutes, protocol));
  const priceCents = prospectiveCostCents === null ? grid.at(-1) :
    (grid.find(value => value >= prospectiveCostCents) ?? grid.at(-1));
  return {priceCents, prospectiveCostCents, prospectiveCostItemsCents: costing.itemsCents,
    expectedCostCentsPerIntended: costing.expectedCostCentsPerIntended,
    expectedPaidProbability: costing.expectedPaidProbability,
    gridCents: grid, modeledAttemptCount,
    coveredAtAssumedReferenceUtilization: prospectiveCostCents !== null && priceCents >= prospectiveCostCents,
    basis: 'ASSUMED_FIXED_RULE_NO_OBSERVED_WILLINGNESS_TO_PAY',
    excludesFromPriceAllocation: 'Historical research and future capability investment; both remain charged to their ledgers.'};
}

function budgetItems(budget, protocol) {
  return {
    constructionCents: laborCents(budget.constructionMinutes, protocol),
    failedConstructionCents: laborCents(budget.failedConstructionMinutes, protocol),
    validationCents: laborCents(budget.validationMinutes, protocol),
    integrationCents: laborCents(budget.integrationMinutes, protocol),
    inferenceCents: budget.inferenceCents,
    maintenanceMicroUSDPerReuse: Math.ceil(budget.maintenanceMinutesPerReuse * protocol.rates.wageUSDPerHour * 1_000_000 / 60),
  };
}

export function candidateBudget(id, cell, protocol = PROTOCOL) {
  const cost = protocol.costBundles[cell.costBundle];
  const definitions = {
    investment1: {before: 'A', after: 'B', base: cost.investment1},
    investment2: {before: 'B', after: 'C', base: cost.investment2},
    investment2graph: {before: 'B', after: 'D', base: cost.investment2, graph: cost.graphExtra},
    graphDiagnostic: {before: 'C', after: 'D', base: cost.graphExtra},
  };
  const definition = definitions[id];
  if (!definition) throw Error('Unknown candidate investment');
  const items = {base: budgetItems(definition.base, protocol)};
  if (definition.graph) items.graphExtra = budgetItems(definition.graph, protocol);
  const failedConstructionCents = sum(Object.values(items).map(item => item.failedConstructionCents));
  const constructionCents = sum(Object.values(items).map(item => item.constructionCents + item.validationCents +
    item.integrationCents + item.inferenceCents));
  const maintenanceBeforeCents = laborCents(activeMaintenanceMinutes(definition.before, cost), protocol);
  const maintenanceAfterCents = laborCents(activeMaintenanceMinutes(definition.after, cost), protocol);
  return {id, before: definition.before, after: definition.after, items, constructionCents,
    failedConstructionCents, fixedCostCents: constructionCents + failedConstructionCents,
    maintenanceMicroUSDPerReuse: (maintenanceAfterCents - maintenanceBeforeCents) * 10_000,
    maintenanceRounding: 'Increment of the actual rounded per-attempt cash charge, including retained prerequisites.',
    diagnosticOnly: id === 'graphDiagnostic'};
}

export function evaluateInvestment({id, calibration, cell, expectedReuses, availableCents, remainingWeeks,
  maintenanceMultiplier = 1, protocol = PROTOCOL}) {
  const budget = candidateBudget(id, cell, protocol);
  if (!Number.isSafeInteger(expectedReuses) || expectedReuses < 0 || expectedReuses > 1_000_000 ||
      !Number.isSafeInteger(availableCents) || availableCents < 0 || !Number.isFinite(remainingWeeks) ||
      remainingWeeks < 0 || remainingWeeks > protocol.investment.usefulLifeWeeks ||
      !Number.isFinite(maintenanceMultiplier) || maintenanceMultiplier < 0) {
    throw Error('Invalid finite investment forecast');
  }
  const before = calibration.arms[budget.before], after = calibration.arms[budget.after];
  const signedMeasuredCPUSavingSeconds = before.cpuSecondsAvailableMean - after.cpuSecondsAvailableMean;
  const savingMicroUSD = cpuMicroUSD(signedMeasuredCPUSavingSeconds, protocol);
  const maintenanceMicroUSD = Math.ceil(budget.maintenanceMicroUSDPerReuse * maintenanceMultiplier);
  // The inherited function is unchanged. Here one minor unit means one micro-USD, explicitly, not a cent.
  const canonical = calculateInvestment({
    constructionCostMinor: budget.constructionCents * 10_000,
    failedConstructionCostMinor: budget.failedConstructionCents * 10_000,
    maintenancePerReuseMinor: maintenanceMicroUSD,
    expectedSavingPerReuseMinor: savingMicroUSD,
    remainingReuses: expectedReuses,
  });
  const matched = calibration.acceptanceEquivalent && before.accepted > 0 && after.accepted > 0 &&
    before.accepted === before.attempts - before.inputBlocked && after.accepted === after.attempts - after.inputBlocked;
  const weeklyCashRoundingProvisionMicroUSD = Math.ceil(remainingWeeks) * 10_000;
  const conservativeNetBenefitMicroUSD = canonical.netBenefit === null ? null :
    canonical.netBenefit - weeklyCashRoundingProvisionMicroUSD;
  const marginalSaving = savingMicroUSD - maintenanceMicroUSD;
  const conservativeBreakEvenReuses = marginalSaving > 0 ?
    Math.ceil((budget.fixedCostCents * 10_000 + weeklyCashRoundingProvisionMicroUSD) / marginalSaving) : null;
  const reasons = [];
  if (!matched) reasons.push('MATCHED_EXECUTED_ACCEPTANCE_NOT_ESTABLISHED');
  if (remainingWeeks <= 0 || expectedReuses === 0) reasons.push('NO_VALID_REUSE_WITHIN_LIFE');
  if (savingMicroUSD <= 0) reasons.push('NONPOSITIVE_MEASURED_CPU_SAVING');
  if (conservativeNetBenefitMicroUSD === null || conservativeNetBenefitMicroUSD <= 0 || !canonical.paysBackWithinHorizon) {
    reasons.push('COMPLETE_COST_NOT_REPAID_WITHIN_LIFE');
  }
  if (budget.fixedCostCents > availableCents) reasons.push('INSUFFICIENT_OPERATING_GENERATED_FUNDS');
  const reusesPerWeek = remainingWeeks > 0 ? expectedReuses / remainingWeeks : 0;
  return {...budget, qualifies: reasons.length === 0, reasons, expectedReuses, remainingWeeks,
    availableCents, signedMeasuredCPUSavingSeconds, expectedSavingMicroUSDPerReuse: savingMicroUSD,
    incrementalMaintenanceMicroUSDPerReuse: maintenanceMicroUSD, canonicalUnit: 'micro-USD', canonical,
    weeklyCashRoundingProvisionMicroUSD, conservativeNetBenefitMicroUSD, conservativeBreakEvenReuses,
    modeledPaybackWeeks: conservativeBreakEvenReuses !== null && reusesPerWeek > 0 ? conservativeBreakEvenReuses / reusesPerWeek : null,
    savingScope: 'Conditional executed service CPU only. Common acquisition and driver costs are fully charged and cancel across arms; blocked-source handling is not credited as a capability gain.',
    credit: {measuredCPUOnly: true, assumedAttentionSavingsCents: 0, assumedDemandPremiumCents: 0,
      assumedQualityPremiumCents: 0, comparatorReconstructionCostCents: 0}};
}

function choose(values, seed, ...keys) {
  return values[Math.floor(randomDraw(seed, ...keys) * values.length)];
}

export function buyerProfile(seed, buyer, protocol = PROTOCOL) {
  const humanMinutes = choose(protocol.market.humanOnlyMinutes, seed, 'buyer-human-minutes', buyer);
  const willingnessMultiplier = choose(protocol.market.willingnessMultipliers, seed, 'buyer-willingness', buyer);
  return {buyer, humanMinutes, willingnessMultiplier,
    willingnessCents: Math.floor(laborCents(humanMinutes, protocol) * willingnessMultiplier)};
}

export function buyerOffers({profile, state, week, cell, priceCents, calibration, enterpriseOpen = true, protocol = PROTOCOL}) {
  const market = protocol.market, strength = cell.competitorStrength;
  const copied = week >= market.competitorCopyWeek;
  const diyMinutes = profile.humanMinutes;
  const aiInitialCost = prospectiveCost(cell, {calibration, laborEfficiency: market.aiLaborEfficiency[strength], protocol});
  const aiCurrentCost = prospectiveCost(cell, {calibration, laborEfficiency: market.aiLaborEfficiency[strength] *
    (copied ? market.competitorCopyEffortMultiplier : 1), protocol});
  const tariffGrid = protocol.pricing.tariffMinutes.map(minutes => laborCents(minutes, protocol));
  const aiInitialPrice = aiInitialCost.prospectiveCostCents === null ? tariffGrid.at(-1) :
    (tariffGrid.find(price => price >= aiInitialCost.prospectiveCostCents) ?? tariffGrid.at(-1));
  const aiPrice = Math.max(aiCurrentCost.prospectiveCostCents ?? tariffGrid.at(-1),
    Math.ceil(aiInitialPrice * (copied ? market.competitorCopyPriceMultiplier : 1)));
  const review = laborCents(market.customerReviewMinutes, protocol);
  const integration = option => laborCents(state[option] ? 0 : cell.integrationMinutes, protocol);
  // Public DIY wins exact ties; there is no invented preference, exclusivity or quality premium.
  const offers = [
    {id: 'diy', priceCents: 0, attentionCents: laborCents(diyMinutes, protocol), integrationCents: 0},
    {id: 'ai', priceCents: aiPrice, attentionCents: review, integrationCents: integration('ai'),
      prospectiveCostCents: aiCurrentCost.prospectiveCostCents, completeProspectiveCostItemsCents: aiCurrentCost.itemsCents},
    {id: 'human', priceCents: laborCents(profile.humanMinutes, protocol), attentionCents: review, integrationCents: 0},
  ];
  if (enterpriseOpen) offers.push({id: 'enterprise', priceCents, attentionCents: review,
    integrationCents: integration('enterprise')});
  return offers.map(offer => ({...offer, copied, qualityPremiumCents: 0,
    generalizedCostCents: offer.priceCents + offer.attentionCents + offer.integrationCents}));
}

export function chooseBuyer(offers, willingnessCents, tieDraw = 0.5) {
  if (!Number.isFinite(tieDraw) || tieDraw < 0 || tieDraw >= 1) throw Error('A bounded paired tie draw is required');
  const eligible = offers.filter(offer => offer.generalizedCostCents <= willingnessCents);
  if (!eligible.length) return {id: 'decline', generalizedCostCents: 0};
  const minimum = Math.min(...eligible.map(offer => offer.generalizedCostCents));
  const tied = eligible.filter(offer => offer.generalizedCostCents === minimum);
  return tied.find(offer => offer.id === 'diy') ?? tied[Math.floor(tieDraw * tied.length)];
}

function activeCapability(investments, week) {
  const first = investments.find(item => item.id === 'investment1' && week < item.expiresWeek);
  if (!first) return 'A';
  const second = investments.find(item => ['investment2', 'investment2graph'].includes(item.id) && week < item.expiresWeek);
  return second?.after ?? 'B';
}

function activeMaintenanceMinutes(capability, cost) {
  if (capability === 'A') return 0;
  let minutes = cost.investment1.maintenanceMinutesPerReuse;
  if (capability === 'C' || capability === 'D') minutes += cost.investment2.maintenanceMinutesPerReuse;
  if (capability === 'D') minutes += cost.graphExtra.maintenanceMinutesPerReuse;
  return minutes;
}

export function simulatePolicy({calibration: suppliedCalibration, cell, seed, policy, protocol = PROTOCOL,
  testOnlyWeeks = null}) {
  const calibration = validateCalibration(suppliedCalibration);
  if (!ARM_IDS.includes(policy) || !Number.isSafeInteger(seed) || seed < 0) throw Error('Invalid paired policy or seed');
  const knownCell = sensitivityCells(protocol).find(entry => entry.id === cell.id);
  if (!knownCell || JSON.stringify(knownCell) !== JSON.stringify(cell)) throw Error('Cell must match the declared protocol');
  const weeks = testOnlyWeeks ?? protocol.campaign.weeks;
  if (!Number.isSafeInteger(weeks) || weeks < 1 || weeks > protocol.campaign.weeks) throw Error('Invalid finite horizon');
  const market = protocol.market, cost = protocol.costBundles[cell.costBundle];
  const tariff = selectTariff(cell, protocol, calibration), ledger = createLedger(protocol.capital);
  for (const [category, amountCents] of Object.entries(openingCostItems(cell, protocol))) {
    accrueCost(ledger, {week: 0, category, amountCents, opening: true});
  }
  settleWeek(ledger, 0);
  const states = Array.from({length: market.buyers}, () => ({enterprise: false, diy: false, ai: false}));
  const profiles = states.map((_, buyer) => buyerProfile(seed, buyer, protocol));
  const history = [], assets = [], investmentChecks = [], investmentOutcomes = [];
  const totals = {arrivals: 0, orders: 0, attempts: 0, accepted: 0, rejected: 0, failedAttempts: 0, inputBlocked: 0,
    unavailableOpportunities: 0,
    capacityRefusals: 0, modeledBuyerSavingsCents: 0, cpuSeconds: 0, wallSeconds: 0, providerMinutes: 0};
  const choices = {enterprise: 0, diy: 0, ai: 0, human: 0, decline: 0};
  const executable = calibration.arms.A.attempts - calibration.arms.A.inputBlocked;
  const commonSuccess = market.commonExecutionStressSuccessProbability *
    (executable ? calibration.arms.A.accepted / executable : 0);
  const common = calibration.commonCosts;
  const path = protocol.investment.policies[policy];
  let lastDecisionKey = null;
  for (let week = 1; week <= weeks; week++) {
    settleWeek(ledger, week);
    const row = {week, capability: activeCapability(assets, week), arrivals: 0, orders: 0, attempts: 0,
      accepted: 0, rejected: 0, failedAttempts: 0, inputBlocked: 0, unavailableOpportunities: 0,
      capacityRefusals: 0, modeledBuyerSavingsCents: 0,
      cpuSeconds: 0, wallSeconds: 0, providerMinutes: 0,
      choices: {enterprise: 0, diy: 0, ai: 0, human: 0, decline: 0}, investmentId: null};
    if (ledger.insolvencyWeek === null) {
      const fixedMinutes = cost.weeklyBusinessMinutes + cost.weeklyBaseMaintenanceMinutes;
      row.providerMinutes += fixedMinutes;
      for (const [category, amountCents] of Object.entries({
        business: laborCents(cost.weeklyBusinessMinutes, protocol),
        base_maintenance: laborCents(cost.weeklyBaseMaintenanceMinutes, protocol), tools: cost.weeklyToolCents,
      })) accrueCost(ledger, {week, dueWeek: week + market.expenseDelayWeeks, category, amountCents});
      const candidateId = path[assets.length];
      const first = assets.find(item => item.id === 'investment1');
      const prerequisiteActive = !first || week < first.expiresWeek;
      if (candidateId && week >= protocol.investment.earliestWeek && prerequisiteActive) {
        const lookback = history.slice(-protocol.investment.forecastLookbackWeeks);
        const recentAttempts = sum(lookback.map(item => item.attempts));
        const remainingWeeks = Math.max(0, Math.min(protocol.investment.usefulLifeWeeks, weeks - week + 1,
          first ? first.expiresWeek - week : Infinity));
        const expectedReuses = Math.floor((lookback.length ? recentAttempts / lookback.length : 0) *
          protocol.investment.forecastReuseDiscount * remainingWeeks);
        const decision = evaluateInvestment({id: candidateId, calibration, cell, expectedReuses,
          remainingWeeks, availableCents: availableInvestmentCents(ledger), protocol});
        const decisionKey = `${candidateId}:${decision.reasons.join('|')}`;
        if (decisionKey !== lastDecisionKey || decision.qualifies || week === weeks) {
          investmentChecks.push({week, ...decision});
          lastDecisionKey = decisionKey;
        }
        if (decision.qualifies) {
          fundInvestment(ledger, {id: candidateId, week, amountCents: decision.fixedCostCents, economics: decision});
          assets.push({id: candidateId, after: decision.after, week, expiresWeek: week + remainingWeeks});
          investmentOutcomes.push({id: candidateId, admittedWeek: week, expiresWeek: week + remainingWeeks,
            fixedCostCents: decision.fixedCostCents, expectedReuses: decision.expectedReuses,
            signedSavingMicroUSDPerReuse: decision.expectedSavingMicroUSDPerReuse,
            incrementalMaintenanceMicroUSDPerReuse: decision.incrementalMaintenanceMicroUSDPerReuse,
            uses: 0, grossMeasuredSavingMicroUSD: 0, completeIncrementalMaintenanceMicroUSD: 0,
            cashRoundingProvisionMicroUSD: 0, lastChargedWeek: null,
            modeledRepaidWeek: null});
          row.investmentId = candidateId;
          row.capability = activeCapability(assets, week);
        }
      }
    }
    for (let buyer = 0; buyer < market.buyers; buyer++) {
      if (randomDraw(seed, 'arrival', week, buyer) >= cell.arrivalProbability) continue;
      row.arrivals++;
      const sourceAvailable = randomDraw(seed, 'source-availability', week, buyer) <
        calibration.sourceAvailability.scenarioProbability;
      if (!sourceAvailable) row.unavailableOpportunities++;
      const profile = profiles[buyer], state = states[buyer];
      const chosen = chooseBuyer(buyerOffers({profile, state, week, cell, priceCents: tariff.priceCents,
        enterpriseOpen: ledger.insolvencyWeek === null, protocol, calibration}), profile.willingnessCents,
      randomDraw(seed, 'paid-offer-tie', week, buyer));
      row.choices[chosen.id]++;
      if (chosen.id !== 'enterprise') {
        if (own(state, chosen.id)) state[chosen.id] = true;
        continue;
      }
      const execution = calibration.arms[row.capability];
      const firstUseMinutes = state.enterprise ? 0 : cost.providerOnboardingMinutes;
      const requiredMinutes = firstUseMinutes + cost.supportMinutesPerOrder + cost.residualMinutesPerAttempt +
        market.correctionMinutesPerRejectedAttempt;
      if (row.providerMinutes + requiredMinutes > market.providerAttentionMinutesPerWeek ||
          row.cpuSeconds + common.standaloneAcquisitionCpuSecondsPerPlanned + common.driverCpuSecondsPerPlanned +
            Math.max(execution.cpuSecondsAvailableMean, execution.cpuSecondsBlockedMean) > market.machineCPUSecondsPerWeek ||
          row.wallSeconds + common.standaloneAcquisitionWallSecondsPerPlanned + common.driverWallSecondsPerPlanned +
            Math.max(execution.wallSecondsAvailableMean, execution.wallSecondsBlockedMean) > market.machineWallSecondsPerWeek) {
        row.capacityRefusals++;
        continue;
      }
      row.orders++;
      let accepted = false;
      row.cpuSeconds += common.standaloneAcquisitionCpuSecondsPerPlanned + common.driverCpuSecondsPerPlanned;
      row.wallSeconds += common.standaloneAcquisitionWallSecondsPerPlanned + common.driverWallSecondsPerPlanned;
      if (!sourceAvailable) {
        row.inputBlocked++;
        row.rejected++;
        row.cpuSeconds += execution.cpuSecondsBlockedMean;
        row.wallSeconds += execution.wallSecondsBlockedMean;
        row.providerMinutes += market.correctionMinutesPerRejectedAttempt;
        accrueCost(ledger, {week, dueWeek: week + market.expenseDelayWeeks, category: 'source_unavailable_triage',
          amountCents: laborCents(market.correctionMinutesPerRejectedAttempt, protocol)});
        continue; // A missing frozen source is never randomly retried into availability.
      }
      state.enterprise = true;
      const orderMinutes = firstUseMinutes + cost.supportMinutesPerOrder;
      row.providerMinutes += orderMinutes;
      accrueCost(ledger, {week, dueWeek: week + market.expenseDelayWeeks, category: 'onboarding_support',
        amountCents: laborCents(orderMinutes, protocol)});
      for (let attempt = 0; attempt < market.maxAttempts; attempt++) {
        const maintenanceMinutes = activeMaintenanceMinutes(row.capability, cost);
        if (row.providerMinutes + cost.residualMinutesPerAttempt + maintenanceMinutes +
            market.correctionMinutesPerRejectedAttempt > market.providerAttentionMinutesPerWeek ||
            row.cpuSeconds + execution.cpuSecondsAvailableMean + (attempt ? common.driverCpuSecondsPerPlanned : 0) >
              market.machineCPUSecondsPerWeek ||
            row.wallSeconds + execution.wallSecondsAvailableMean + (attempt ? common.driverWallSecondsPerPlanned : 0) >
              market.machineWallSecondsPerWeek) break;
        row.attempts++;
        row.cpuSeconds += execution.cpuSecondsAvailableMean + (attempt ? common.driverCpuSecondsPerPlanned : 0);
        row.wallSeconds += execution.wallSecondsAvailableMean + (attempt ? common.driverWallSecondsPerPlanned : 0);
        row.providerMinutes += cost.residualMinutesPerAttempt + maintenanceMinutes;
        accrueCost(ledger, {week, dueWeek: week + market.expenseDelayWeeks, category: 'delivery_attention',
          amountCents: laborCents(cost.residualMinutesPerAttempt, protocol)});
        accrueCost(ledger, {week, dueWeek: week + market.expenseDelayWeeks, category: 'capability_maintenance',
          amountCents: laborCents(maintenanceMinutes, protocol)});
        for (const outcome of investmentOutcomes) {
          if (week >= outcome.expiresWeek || row.capability === 'A') continue;
          if (outcome.id !== 'investment1' && row.capability === 'B') continue;
          outcome.uses++;
          outcome.grossMeasuredSavingMicroUSD += outcome.signedSavingMicroUSDPerReuse;
          outcome.completeIncrementalMaintenanceMicroUSD += outcome.incrementalMaintenanceMicroUSDPerReuse;
          if (outcome.lastChargedWeek !== week) {
            outcome.cashRoundingProvisionMicroUSD += 10_000;
            outcome.lastChargedWeek = week;
          }
          if (outcome.modeledRepaidWeek === null && outcome.grossMeasuredSavingMicroUSD >=
              outcome.fixedCostCents * 10_000 + outcome.completeIncrementalMaintenanceMicroUSD +
              outcome.cashRoundingProvisionMicroUSD) {
            outcome.modeledRepaidWeek = week;
          }
        }
        if (randomDraw(seed, 'execution', week, buyer, attempt) < commonSuccess) {accepted = true; break;}
        row.failedAttempts++;
        row.providerMinutes += market.correctionMinutesPerRejectedAttempt;
        accrueCost(ledger, {week, dueWeek: week + market.expenseDelayWeeks, category: 'rejection_correction',
          amountCents: laborCents(market.correctionMinutesPerRejectedAttempt, protocol)});
      }
      if (accepted) {
        row.accepted++;
        row.modeledBuyerSavingsCents += laborCents(profile.humanMinutes, protocol) - chosen.generalizedCostCents;
        invoice(ledger, {week, dueWeek: week + market.paymentDelayWeeks, amountCents: tariff.priceCents,
          willPay: randomDraw(seed, 'payment', week, buyer) < market.paymentProbability});
      } else row.rejected++;
    }
    // Aggregate metered CPU at the weekly billing interval; no per-call minimum conceals signed deltas.
    if (row.orders) accrueCost(ledger, {week, dueWeek: week + market.expenseDelayWeeks, category: 'compute',
      amountCents: Math.ceil(row.cpuSeconds * protocol.rates.cpuUSDPerHour * 100 / 3600)});
    settleWeek(ledger, week);
    row.ledger = ledgerSnapshot(ledger);
    for (const key of Object.keys(totals)) totals[key] += row[key];
    for (const id of Object.keys(choices)) choices[id] += row.choices[id];
    history.push(row);
  }
  const closing = ledgerSnapshot(ledger);
  for (const outcome of investmentOutcomes) {
    outcome.netMeasuredBenefitMicroUSD = outcome.grossMeasuredSavingMicroUSD -
      outcome.completeIncrementalMaintenanceMicroUSD - outcome.fixedCostCents * 10_000 - outcome.cashRoundingProvisionMicroUSD;
    outcome.benefitRepaidCompleteCost = outcome.netMeasuredBenefitMicroUSD >= 0;
  }
  return {
    schema: 'agi-alpha.work-discovery.simulated-policy.v1', cell: clone(cell), seed, policy,
    outputKind: testOnlyWeeks === null ? 'PRIMARY_SIMULATED_COUNTERFACTUAL' : 'SYNTHETIC_CONTROL_OR_TRUNCATED_TEST',
    weeks, initialCapability: 'A', closingCapability: history.at(-1).capability,
    actualCollectionsCents: 0, actualFullCostCents: null, actualOperatingProfitCents: null,
    tariff, commonConditionalSuccessProbability: commonSuccess, sourceAvailability: calibration.sourceAvailability,
    commonCostAllocation: calibration.commonCosts, competitorChoicesAreNotAcceptedDeliveries: true,
    totals, choices, closing,
    costItemsCents: clone(ledger.costsByCategory), investments: investmentOutcomes, investmentChecks,
    earnedOrdinaryOperatingSurplus: closing.operatingSurplusCents > 0 && closing.insolvencyWeek === null,
    recoveredHistoricalAndInvestmentCosts: closing.historicalRecoveryCents >= 0 && closing.insolvencyWeek === null,
    modeledSelfFinancingSuccession: investmentOutcomes.length === 2 &&
      investmentOutcomes.every(outcome => outcome.benefitRepaidCompleteCost) && closing.insolvencyWeek === null,
    history,
    limitation: 'Conditional simulated buyers and money; accepted public executions calibrate mechanical costs only. No paid demand or realized profit.',
  };
}

export function deploymentDiagnostics(suppliedCalibration, protocol = PROTOCOL) {
  const calibration = validateCalibration(suppliedCalibration);
  const tables = [];
  for (const costBundle of Object.keys(protocol.costBundles)) {
    const cell = sensitivityCells(protocol).find(entry => entry.costBundle === costBundle &&
      entry.demand === 'reference' && entry.integrationMinutes === 0 && entry.competitorStrength === 'strong');
    const tariff = selectTariff(cell, protocol, calibration);
    for (const residualMinutes of protocol.diagnostics.residualMinutes) {
      for (const humanMinutes of protocol.market.humanOnlyMinutes) {
        // No simulated revenue is placed in the canonical function's observed-revenue field.
        const illustrativeRecurringCents = laborCents(residualMinutes +
          protocol.costBundles[costBundle].supportMinutesPerOrder, protocol) +
          protocol.pricing.commonComputeAllowanceCentsPerOrder;
        const canonical = planMission({missionId: `diag-${costBundle}-${residualMinutes}-${humanMinutes}`,
          reference: 'Assumed matched public-tool workflow and review; no measured human trial or paid receipt',
          currency: 'USD', acceptance: calibration.acceptanceEquivalent ? 'accepted' : 'unknown',
          totalCollectedCents: 0, priceAssumptionCents: tariff.priceCents,
          totalOperatingCostCents: illustrativeRecurringCents, operatingCostsComplete: false,
          capabilityCostCents: null, reserveCents: 0, obligationCents: 0, costBasis: 'assumed',
          reinvestmentBps: 0, humanMinutes: protocol.market.customerReviewMinutes,
          humanHourlyCents: Math.round(protocol.rates.wageUSDPerHour * 100), traditionalMinutes: humanMinutes});
        tables.push({costBundle, residualMinutes, humanOnlyMinutes: humanMinutes,
          humanOnlyCostCents: laborCents(humanMinutes, protocol), customerPriceCents: tariff.priceCents,
          modeledCustomerReviewCents: laborCents(protocol.market.customerReviewMinutes, protocol),
          customerSavingsCents: laborCents(humanMinutes, protocol) - tariff.priceCents -
            laborCents(protocol.market.customerReviewMinutes, protocol),
          marginalAttentionAndSupportCents: illustrativeRecurringCents,
          fullCostKnown: false, canonical,
          canonicalHourlyRoundingNote: 'Canonical planMission accepts integer hourly cents; 65.375 USD is rounded to 6538 cents there only.'});
      }
    }
  }
  const measuredArms = Object.fromEntries(ARM_IDS.map(id => [id, {
    ...calibration.arms[id], acceptedRate: calibration.arms[id].accepted / calibration.arms[id].attempts,
    conditionalAcceptedRate: calibration.arms[id].attempts > calibration.arms[id].inputBlocked ?
      calibration.arms[id].accepted / (calibration.arms[id].attempts - calibration.arms[id].inputBlocked) : null,
    standaloneCPUSecondsPerPlannedIncludingAcquisitionAndDriver: calibration.arms[id].cpuSecondsMean +
      calibration.commonCosts.standaloneAcquisitionCpuSecondsPerPlanned + calibration.commonCosts.driverCpuSecondsPerPlanned,
    standaloneCPUSecondsPerAcceptedIncludingAllFailures: calibration.arms[id].accepted ?
      (calibration.arms[id].cpuSecondsMean + calibration.commonCosts.standaloneAcquisitionCpuSecondsPerPlanned +
        calibration.commonCosts.driverCpuSecondsPerPlanned) * calibration.arms[id].attempts / calibration.arms[id].accepted : null,
    modeledCPUCostMicroUSDPerPlanned: cpuMicroUSD(calibration.arms[id].cpuSecondsMean +
      calibration.commonCosts.standaloneAcquisitionCpuSecondsPerPlanned + calibration.commonCosts.driverCpuSecondsPerPlanned, protocol),
    modelHumanAttentionReductionMinutes: null,
  }]));
  const thresholds = [];
  for (const costBundle of Object.keys(protocol.costBundles)) {
    const cell = sensitivityCells(protocol).find(entry => entry.costBundle === costBundle);
    for (const id of ['investment1', 'investment2', 'investment2graph', 'graphDiagnostic']) {
      for (const maintenanceMultiplier of protocol.investment.maintenanceMultipliersForDiagnostics) {
        const decision = evaluateInvestment({id, calibration, cell, expectedReuses: 156, availableCents: 0,
          remainingWeeks: protocol.investment.usefulLifeWeeks, maintenanceMultiplier, protocol});
        const requiredAdditionalSavingMicroUSD = Math.max(0,
          Math.ceil(decision.fixedCostCents * 10_000 / 156) + decision.incrementalMaintenanceMicroUSDPerReuse -
          decision.expectedSavingMicroUSDPerReuse);
        thresholds.push({...decision, diagnosticOnly: true, assumedDiagnosticReuses: 156,
          requiredAdditionalUnmeasuredSavingMicroUSDPerReuse: requiredAdditionalSavingMicroUSD,
          requiredUnmeasuredAttentionMinutesPerReuse: requiredAdditionalSavingMicroUSD * 60 /
            (protocol.rates.wageUSDPerHour * 1_000_000),
          scenarioStatus: 'THRESHOLD_ONLY_NO_SAVING_CREDIT_NO_FUNDED_CAMPAIGN'});
      }
    }
  }
  return {schema: 'agi-alpha.work-discovery.economic-diagnostics.v1', measuredArms,
    illustrativeMatchedHumanTables: tables, investmentAndGraphThresholds: thresholds,
    sourceAvailability: calibration.sourceAvailability, commonCosts: calibration.commonCosts,
    actualCollectionsCents: 0, actualCosts: clone(protocol.unknownActualCosts),
    warning: 'Attention, demand, pricing and reconstruction benefits are not measured. Hypothetical thresholds do not enter investment gates.'};
}

export function* campaignWorlds(calibration, protocol = PROTOCOL) {
  const validated = validateCalibration(calibration), cells = sensitivityCells(protocol);
  if (cells.length !== protocol.campaign.expectedCells ||
      cells.length * protocol.campaign.pairedSeeds.length !== protocol.campaign.expectedWorlds) {
    throw Error('Predeclared campaign dimensions changed');
  }
  for (const cell of cells) {
    for (const seed of protocol.campaign.pairedSeeds) {
      yield {cell, seed, policies: protocol.campaign.policies.map(policy =>
        simulatePolicy({calibration: validated, cell, seed, policy, protocol}))};
    }
  }
}

export const WEEKLY_COLUMNS = [
  'week', 'capability', 'arrivals', 'orders', 'attempts', 'accepted', 'rejected', 'failedAttempts',
  'capacityRefusals', 'enterpriseChoices', 'diyChoices', 'aiChoices', 'humanChoices', 'declines',
  'cpuSeconds', 'wallSeconds', 'providerMinutes', 'modeledBuyerSavingsCents', 'cashCents',
  'simulatedCollectionsCents', 'operatingCostCents', 'unpaidCents', 'receivableCents',
  'availableInvestmentCents', 'investmentCents', 'investmentId', 'insolvencyWeek',
  'inputBlocked',
  'unavailableOpportunities',
];

export function compactHistory(result) {
  return result.history.map(row => [row.week, row.capability, row.arrivals, row.orders, row.attempts,
    row.accepted, row.rejected, row.failedAttempts, row.capacityRefusals, row.choices.enterprise,
    row.choices.diy, row.choices.ai, row.choices.human, row.choices.decline, row.cpuSeconds,
    row.wallSeconds, row.providerMinutes, row.modeledBuyerSavingsCents, row.ledger.cashCents,
    row.ledger.simulatedCollectionsCents, row.ledger.operatingCostCents, row.ledger.unpaidCents,
    row.ledger.receivableCents, row.ledger.availableInvestmentCents, row.ledger.investmentCents,
    row.investmentId, row.ledger.insolvencyWeek, row.inputBlocked, row.unavailableOpportunities]);
}

export function summarizeCampaign(policyResults, protocol = PROTOCOL) {
  const groups = [];
  for (const cell of sensitivityCells(protocol)) {
    for (const policy of protocol.campaign.policies) {
      const records = policyResults.filter(result => result.cell.id === cell.id && result.policy === policy);
      if (records.length !== protocol.campaign.pairedSeeds.length) throw Error('Incomplete primary cell');
      const distribution = values => ({minimum: Math.min(...values), mean: sum(values) / values.length,
        maximum: Math.max(...values)});
      groups.push({cell: cell.id, policy, seeds: records.length,
        actualCollectionsCents: 0,
        positiveOrdinarySurplusCount: records.filter(record => record.earnedOrdinaryOperatingSurplus).length,
        recoveredFullHistoryCount: records.filter(record => record.recoveredHistoricalAndInvestmentCosts).length,
        firstInvestmentCount: records.filter(record => record.investments.length >= 1).length,
        secondInvestmentCount: records.filter(record => record.investments.length >= 2).length,
        repaidSuccessionCount: records.filter(record => record.modeledSelfFinancingSuccession).length,
        insolvencyCount: records.filter(record => record.closing.insolvencyWeek !== null).length,
        acceptedJobs: distribution(records.map(record => record.totals.accepted)),
        simulatedCollectionsCents: distribution(records.map(record => record.closing.simulatedCollectionsCents)),
        operatingSurplusCents: distribution(records.map(record => record.closing.operatingSurplusCents)),
        fullCostRecoveryCents: distribution(records.map(record => record.closing.historicalRecoveryCents)),
        closingCashCents: distribution(records.map(record => record.closing.cashCents)),
      });
    }
  }
  const paired = [];
  for (const [before, after] of [['A', 'B'], ['B', 'C'], ['C', 'D']]) {
    for (const cell of sensitivityCells(protocol)) {
      const differences = protocol.campaign.pairedSeeds.map(seed => {
        const get = policy => policyResults.find(result => result.cell.id === cell.id && result.seed === seed && result.policy === policy);
        const a = get(before), b = get(after);
        return {seed, operatingSurplusDeltaCents: b.closing.operatingSurplusCents - a.closing.operatingSurplusCents,
          fullCostRecoveryDeltaCents: b.closing.historicalRecoveryCents - a.closing.historicalRecoveryCents,
          acceptedJobsDelta: b.totals.accepted - a.totals.accepted,
          capabilityInvestmentDeltaCents: b.closing.investmentCents - a.closing.investmentCents};
      });
      paired.push({cell: cell.id, before, after, differences});
    }
  }
  return {schema: 'agi-alpha.work-discovery.economic-summary.v1',
    worlds: protocol.campaign.expectedWorlds, policiesPerWorld: 4, groups, paired,
    actualCollectionsCents: 0, actualPaidDemandEstablished: false,
    actualCosts: clone(protocol.unknownActualCosts),
    interpretation: 'These are sensitivity outcomes of declared assumptions and paired simulation seeds, not confidence intervals for actual market demand.'};
}

export function paperSummary(summary, diagnostics, calibration, protocol = PROTOCOL) {
  const cells = sensitivityCells(protocol).map(cell => ({
    ...cell,
    policies: Object.fromEntries(summary.groups.filter(group => group.cell === cell.id).map(group => [group.policy, {
      simulatedOperatingProfitCents: group.operatingSurplusCents,
      simulatedProjectProfitCents: group.fullCostRecoveryCents,
      simulatedCollectionsCents: group.simulatedCollectionsCents,
      acceptedJobs: group.acceptedJobs,
      positiveOperatingSeeds: group.positiveOrdinarySurplusCount,
      recoveredProjectSeeds: group.recoveredFullHistoryCount,
      firstInvestmentSeeds: group.firstInvestmentCount,
      secondInvestmentSeeds: group.secondInvestmentCount,
      repaidSuccessionSeeds: group.repaidSuccessionCount,
      insolvencySeeds: group.insolvencyCount,
    }])),
  }));
  return {
    schema: 'agi-alpha.work-discovery.paper-economic-summary.v1',
    actualCollectionsCents: 0, realizedCommercialSuccess: false,
    scope: 'Selected structural response-contract dossiers; runtime/API compatibility still needs documentation review.',
    sourceAvailability: diagnostics.sourceAvailability,
    measuredMechanicalResources: diagnostics.measuredArms,
    commonAcquisitionAndDriverAllocation: diagnostics.commonCosts,
    unitCostScenarios: Object.keys(protocol.costBundles).map(costBundle => {
      const cell = sensitivityCells(protocol).find(item => item.costBundle === costBundle);
      return {costBundle, tariff: selectTariff(cell, protocol, calibration), openingItemsCents: openingCostItems(cell, protocol),
        incrementalInvestments: ['investment1', 'investment2', 'investment2graph'].map(id => candidateBudget(id, cell, protocol))};
    }),
    breakEvenAndPaybackDiagnostics: diagnostics.investmentAndGraphThresholds.map(item => ({
      candidate: item.id, before: item.before, after: item.after,
      fixedCostCents: item.fixedCostCents,
      incrementalMaintenanceMicroUSDPerReuse: item.incrementalMaintenanceMicroUSDPerReuse,
      signedExecutedCPUSavingSeconds: item.signedMeasuredCPUSavingSeconds,
      cpuValuationSavingMicroUSDPerReuse: item.expectedSavingMicroUSDPerReuse,
      breakEvenReuses: item.canonical.breakEvenReuses,
      conservativeBreakEvenReuses: item.conservativeBreakEvenReuses,
      usefulLifeWeeks: item.remainingWeeks, assumedDiagnosticReuses: item.assumedDiagnosticReuses,
      modeledPaybackWeeks: item.modeledPaybackWeeks,
      unmeasuredAttentionThresholdMinutesPerReuse: item.requiredUnmeasuredAttentionMinutesPerReuse,
      diagnosticOnly: true,
    })),
    cells,
    assumptions: {
      wageUSDPerHour: protocol.rates.wageUSDPerHour,
      humanOnlyMinutes: protocol.market.humanOnlyMinutes,
      residualMinutes: protocol.diagnostics.residualMinutes,
      simulatedOperatingProfitDefinition: 'Simulated collections minus all accrued delivery and recurring business costs.',
      simulatedProjectProfitDefinition: 'Simulated collections minus operating costs, opening historical/setup costs and once-only capability investments.',
      horizon: '52 weeks; uncollected invoices are not profit or spendable funds; unpaid expenses remain obligations.',
      ranges: 'Minimum/mean/maximum across 16 paired seeds in each of 24 explicitly assumed market cells.',
    },
    unknownActualCosts: protocol.unknownActualCosts,
  };
}
