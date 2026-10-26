// SPDX-License-Identifier: Apache-2.0
// All calibration numbers in this file are synthetic arithmetic controls, not execution observations.
// This file never invokes campaignWorlds() or runPrimaryCampaign().
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {PROTOCOL, sensitivityCells, laborCents, cpuMicroUSD} from '../src/economics/protocol.mjs';
import {
  createLedger, accrueCost, invoice, settleWeek, availableInvestmentCents, fundInvestment,
  ledgerSnapshot, assertLedger,
} from '../src/economics/ledger.mjs';
import {
  validateCalibration, prospectiveCost as prospectiveCostRaw, selectTariff as selectTariffRaw, candidateBudget, evaluateInvestment,
  buyerOffers as buyerOffersRaw, chooseBuyer, simulatePolicy, deploymentDiagnostics, compactHistory, WEEKLY_COLUMNS,
} from '../src/economics/model.mjs';
import {SOURCE_FILES, STUDY_ROOT, verifyFreeze} from '../src/economics/run_campaign.mjs';
import {normalizeExecutedCampaign} from '../src/economics/normalize.mjs';
import {randomDraw} from '../heritage/graph-foundations/market/inherited/upstream/src/market.mjs';

const clonedProtocol = () => JSON.parse(JSON.stringify(PROTOCOL));
const syntheticCalibration = (cpu = {A: 0.01, B: 0.02, C: 0.005, D: 0.006}) => ({
  schema: 'agi-alpha.work-discovery.calibration.v1', measurementKind: 'EXECUTED_PUBLIC_LOCAL',
  acceptanceScope: 'SYNTHETIC UNIT TEST: selected structural GET JSON response contracts',
  acceptanceSpecificationSha256: '1'.repeat(64), sourceManifestSha256: '2'.repeat(64),
  acceptanceEquivalent: true,
  evidence: [{path: 'SYNTHETIC_UNIT_TEST_NOT_EXECUTED.json', sha256: '3'.repeat(64)}],
  arms: Object.fromEntries(['A', 'B', 'C', 'D'].map(id => [id,
    {attempts: 4, accepted: 4, inputBlocked: 0, cpuSecondsMean: cpu[id], wallSecondsMean: cpu[id],
      cpuSecondsAvailableMean: cpu[id], wallSecondsAvailableMean: cpu[id],
      cpuSecondsBlockedMean: 0, wallSecondsBlockedMean: 0}])),
  sourceAvailability: {planned: 4, inputBlocked: 0, available: 4, scenarioProbability: 1,
    interpretation: 'Synthetic test condition only'},
  commonCosts: {
    experimentalAcquisitionCpuSecondsPerPlanned: 0.01, experimentalAcquisitionWallSecondsPerPlanned: 0.02,
    experimentalArmSharingDivisor: 4,
    standaloneAcquisitionCpuSecondsPerPlanned: 0.04, standaloneAcquisitionWallSecondsPerPlanned: 0.08,
    acquisitionSessionOverheadCpuSecondsPerPlanned: 0, acquisitionSessionOverheadWallSecondsPerPlanned: 0,
    driverCpuSecondsPerPlanned: 0.001, driverWallSecondsPerPlanned: 0.001,
    allocation: 'Synthetic unit test allocation, not an observed production cost',
  },
});
const selectTariff = (cell, protocol = PROTOCOL) => selectTariffRaw(cell, protocol, syntheticCalibration());
const prospectiveCost = (cell, options = {}) => prospectiveCostRaw(cell, {calibration: syntheticCalibration(), ...options});
const buyerOffers = options => buyerOffersRaw({calibration: syntheticCalibration(), ...options});
const cell = (options = {}) => sensitivityCells().find(item => Object.entries({
  demand: 'reference', integrationMinutes: 0, competitorStrength: 'equal', costBundle: 'low', ...options,
}).every(([key, value]) => item[key] === value));
const budgetDecision = overrides => evaluateInvestment({id: 'investment1', calibration: syntheticCalibration(),
  cell: cell(), expectedReuses: 1000, availableCents: 100_000, remainingWeeks: 26, ...overrides});

test('declared primary design is 24 cells, 16 paired seeds and exactly two possible investments', () => {
  assert.equal(sensitivityCells().length, 24);
  assert.equal(new Set(sensitivityCells().map(item => item.id)).size, 24);
  assert.equal(PROTOCOL.campaign.pairedSeeds.length, 16);
  assert.equal(24 * 16, PROTOCOL.campaign.expectedWorlds);
  assert.deepEqual(PROTOCOL.investment.policies.D, ['investment1', 'investment2graph']);
  assert.equal(PROTOCOL.rates.annualWageUSD / PROTOCOL.rates.assumedAnnualHours, 65.375);
  assert.equal(PROTOCOL.campaign.maxOutputBytes < 100_000_000, true);
});

test('calibration rejects invented zero defaults, unknown fields, invalid counts and nonfinite measurements', () => {
  for (const mutate of [
    input => {delete input.arms.C;}, input => {input.arms.A.accepted = 5;},
    input => {input.arms.A.cpuSecondsMean = null;}, input => {input.arms.A.cpuSecondsMean = Infinity;},
    input => {input.arms.A.wallSecondsMean = -1;}, input => {input.attentionSavingsMinutes = 10;},
    input => {input.evidence[0].path = '../outside.json';}, input => {input.sourceManifestSha256 = 'not-a-hash';},
    input => {input.measurementKind = 'MODELED';},
  ]) {
    const input = syntheticCalibration(); mutate(input);
    assert.throws(() => validateCalibration(input));
  }
  const input = syntheticCalibration(), validated = validateCalibration(input);
  input.arms.A.cpuSecondsMean = 999;
  assert.equal(validated.arms.A.cpuSecondsMean, 0.01);
});

test('seed, reserve and an unpaid invoice cannot become available operating funds', () => {
  const ledger = createLedger(PROTOCOL.capital);
  assert.equal(availableInvestmentCents(ledger), 0);
  invoice(ledger, {week: 1, dueWeek: 3, amountCents: 50_000, willPay: true});
  settleWeek(ledger, 2);
  assert.equal(ledger.cashCents, 100_000);
  assert.equal(availableInvestmentCents(ledger), 0);
  assert.equal(ledgerSnapshot(ledger).receivableCents, 50_000);
  settleWeek(ledger, 3);
  assert.equal(availableInvestmentCents(ledger), 50_000);
  assert.equal(ledger.actualCollectionsCents, 0);
});

test('all accrued operating costs and unpaid obligations constrain investment before their payment date', () => {
  const ledger = createLedger({initialSeedCents: 30_000, reserveCents: 20_000});
  invoice(ledger, {week: 0, dueWeek: 1, amountCents: 40_000, willPay: true});
  accrueCost(ledger, {week: 0, dueWeek: 5, category: 'support', amountCents: 35_000});
  settleWeek(ledger, 1);
  assert.equal(ledger.cashCents, 70_000);
  assert.equal(ledger.operatingPaidCents, 0);
  assert.equal(availableInvestmentCents(ledger), 5000);
  settleWeek(ledger, 5);
  assert.equal(ledger.cashCents, 35_000);
  assert.equal(availableInvestmentCents(ledger), 5000);
  assertLedger(ledger);
});

test('historical opening costs reduce cash once without being operating receipts or candidate construction', () => {
  const ledger = createLedger(PROTOCOL.capital);
  accrueCost(ledger, {week: 0, category: 'failed_discovery', amountCents: 10_000, opening: true});
  settleWeek(ledger, 0); settleWeek(ledger, 0);
  assert.equal(ledger.cashCents, 90_000);
  assert.equal(ledger.openingPaidCents, 10_000);
  assert.equal(ledger.operatingAccruedCents, 0);
  assert.equal(availableInvestmentCents(ledger), 0);
  assert.equal(ledger.investmentsCents, 0);
});

test('defaulted invoices are not cash, profit or receivables after their due date', () => {
  const ledger = createLedger(PROTOCOL.capital);
  invoice(ledger, {week: 1, dueWeek: 3, amountCents: 8000, willPay: false});
  settleWeek(ledger, 3);
  const snapshot = ledgerSnapshot(ledger);
  assert.equal(snapshot.defaultedCents, 8000);
  assert.equal(snapshot.receivableCents, 0);
  assert.equal(snapshot.simulatedCollectionsCents, 0);
  assert.equal(snapshot.availableInvestmentCents, 0);
});

test('finite cash pays bills only with available cash and preserves insolvency after a late recovery', () => {
  const ledger = createLedger({initialSeedCents: 100, reserveCents: 20});
  accrueCost(ledger, {week: 0, category: 'delivery', amountCents: 150});
  invoice(ledger, {week: 0, dueWeek: 2, amountCents: 200, willPay: true});
  settleWeek(ledger, 0);
  assert.equal(ledger.cashCents, 0);
  assert.equal(ledgerSnapshot(ledger).unpaidCents, 50);
  assert.equal(ledger.insolvencyWeek, 0);
  settleWeek(ledger, 2);
  assert.equal(ledger.cashCents, 150);
  assert.equal(ledger.insolvencyWeek, 0);
  assert.throws(() => fundInvestment(ledger, {id: 'x', week: 2, amountCents: 1,
    economics: {qualifies: true, fixedCostCents: 1}}), /Insolvent/);
});

test('negative measured CPU saving cannot be replaced by attention, graph or reconstruction value', () => {
  const decision = budgetDecision();
  assert.equal(decision.signedMeasuredCPUSavingSeconds, -0.01);
  assert(decision.reasons.includes('NONPOSITIVE_MEASURED_CPU_SAVING'));
  assert.equal(decision.qualifies, false);
  assert.equal(decision.credit.assumedAttentionSavingsCents, 0);
  assert.equal(decision.credit.assumedDemandPremiumCents, 0);
  assert.equal(decision.credit.comparatorReconstructionCostCents, 0);
  assert(cpuMicroUSD(-0.01) < 0);
  assert.equal(cpuMicroUSD(0.00001), 0);
});

test('synthetic large positive saving still needs complete cost repayment and operating affordability', () => {
  const calibration = syntheticCalibration({A: 3600, B: 1800, C: 900, D: 1000});
  const positive = budgetDecision({calibration});
  assert.equal(positive.qualifies, true);
  assert(positive.canonical.breakEvenReuses > 0);
  assert(positive.modeledPaybackWeeks <= 26);
  const noFunds = budgetDecision({calibration, availableCents: 0});
  assert.deepEqual(noFunds.reasons, ['INSUFFICIENT_OPERATING_GENERATED_FUNDS']);
  const tooFew = budgetDecision({calibration, expectedReuses: 1});
  assert(tooFew.reasons.includes('COMPLETE_COST_NOT_REPAID_WITHIN_LIFE'));
  assert.throws(() => budgetDecision({calibration, remainingWeeks: 27}), /finite investment forecast/);
});

test('failed or unmatched calibration blocks an investment even with profitable synthetic arithmetic', () => {
  const calibration = syntheticCalibration({A: 3600, B: 1800, C: 900, D: 1000});
  calibration.arms.B.accepted = 3;
  assert(budgetDecision({calibration}).reasons.includes('MATCHED_EXECUTED_ACCEPTANCE_NOT_ESTABLISHED'));
  calibration.arms.B.accepted = 4;
  calibration.acceptanceEquivalent = false;
  assert(budgetDecision({calibration}).reasons.includes('MATCHED_EXECUTED_ACCEPTANCE_NOT_ESTABLISHED'));
});

test('construction is paid once and all failed construction, validation, integration and inference are included', () => {
  const calibration = syntheticCalibration({A: 3600, B: 1800, C: 900, D: 1000});
  const decision = budgetDecision({calibration});
  const item = decision.items.base;
  assert.equal(decision.fixedCostCents, item.constructionCents + item.failedConstructionCents +
    item.validationCents + item.integrationCents + item.inferenceCents);
  const ledger = createLedger(PROTOCOL.capital);
  assert.throws(() => fundInvestment(ledger, {id: 'investment1', week: 1,
    amountCents: decision.fixedCostCents, economics: decision}), /seed/);
  invoice(ledger, {week: 0, dueWeek: 1, amountCents: 30_000, willPay: true});
  settleWeek(ledger, 1);
  const before = ledger.cashCents;
  fundInvestment(ledger, {id: 'investment1', week: 1, amountCents: decision.fixedCostCents, economics: decision});
  assert.equal(ledger.cashCents, before - decision.fixedCostCents);
  assert.throws(() => fundInvestment(ledger, {id: 'investment1', week: 2,
    amountCents: decision.fixedCostCents, economics: decision}), /only once/);
});

test('graph second investment includes the base asset plus separately costed graph work', () => {
  const registry = candidateBudget('investment2', cell());
  const graph = candidateBudget('investment2graph', cell());
  const extra = candidateBudget('graphDiagnostic', cell());
  assert.deepEqual(graph.items.base, registry.items.base);
  assert.deepEqual(graph.items.graphExtra, extra.items.base);
  assert.equal(graph.fixedCostCents, registry.fixedCostCents + extra.fixedCostCents);
  assert.equal(graph.maintenanceMicroUSDPerReuse,
    registry.maintenanceMicroUSDPerReuse + extra.maintenanceMicroUSDPerReuse);
  assert.equal(graph.before, 'B');
  assert.equal(graph.after, 'D');
});

test('investment maintenance matches increments of actually rounded cash charges', () => {
  const cost = PROTOCOL.costBundles.low;
  const first = candidateBudget('investment1', cell());
  const second = candidateBudget('investment2', cell());
  assert.equal(first.maintenanceMicroUSDPerReuse,
    laborCents(cost.investment1.maintenanceMinutesPerReuse) * 10_000);
  assert.equal(first.maintenanceMicroUSDPerReuse + second.maintenanceMicroUSDPerReuse,
    laborCents(cost.investment1.maintenanceMinutesPerReuse + cost.investment2.maintenanceMinutesPerReuse) * 10_000);
});

test('price is frozen by prospective full recurring cost and unaffected by observed outcomes or demand cells', () => {
  const prices = new Map();
  for (const item of sensitivityCells()) {
    const tariff = selectTariff(item);
    const prior = prices.get(item.costBundle);
    if (prior !== undefined) assert.equal(tariff.priceCents, prior);
    prices.set(item.costBundle, tariff.priceCents);
    assert(tariff.gridCents.includes(tariff.priceCents));
    assert(tariff.priceCents >= tariff.prospectiveCostCents);
    assert(tariff.prospectiveCostItemsCents.weeklyBusinessAllocation > 0);
    assert(tariff.prospectiveCostItemsCents.baseMaintenanceAllocation > 0);
    assert(tariff.prospectiveCostItemsCents.ordinarySetupAllocation > 0);
  }
});

test('equal AI-assisted competitor bears identical verification, support, overhead, tooling and setup costs', () => {
  const currentCell = cell(), tariff = selectTariff(currentCell);
  const offers = buyerOffers({profile: {humanMinutes: 45}, state: {diy: false, ai: false, enterprise: false},
    week: 1, cell: currentCell, priceCents: tariff.priceCents});
  const ai = offers.find(offer => offer.id === 'ai');
  assert.equal(ai.prospectiveCostCents, tariff.prospectiveCostCents);
  assert.deepEqual(ai.completeProspectiveCostItemsCents, tariff.prospectiveCostItemsCents);
  assert.equal(prospectiveCost(currentCell).prospectiveCostCents, tariff.prospectiveCostCents);
  assert(ai.priceCents >= ai.prospectiveCostCents);
});

test('buyer can refuse, public DIY can win, and integration attention disappears only after actual use', () => {
  const currentCell = cell({integrationMinutes: 15});
  const input = {profile: {humanMinutes: 5}, state: {diy: true, ai: false, enterprise: false},
    week: 1, cell: currentCell, priceCents: 50_000};
  const offers = buyerOffers(input);
  assert.equal(chooseBuyer(offers, 0).id, 'decline');
  assert.equal(chooseBuyer(offers, 100_000).id, 'diy');
  assert.equal(offers.find(offer => offer.id === 'enterprise').integrationCents, laborCents(15));
  input.state.enterprise = true;
  assert.equal(buyerOffers(input).find(offer => offer.id === 'enterprise').integrationCents, 0);
});

test('competitor copying permits a sustainable automated price cut while conventional effort remains matched', () => {
  const input = {profile: {humanMinutes: 45}, state: {diy: true, ai: true, enterprise: true},
    cell: cell(), priceCents: 1000};
  const before = buyerOffers({...input, week: 1}), after = buyerOffers({...input, week: 20});
  const find = (offers, id) => offers.find(offer => offer.id === id);
  assert(find(after, 'ai').priceCents < find(before, 'ai').priceCents);
  assert(find(after, 'ai').priceCents >= find(after, 'ai').prospectiveCostCents);
  assert.equal(find(after, 'diy').attentionCents, laborCents(45));
  assert.equal(find(after, 'diy').attentionCents, find(before, 'diy').attentionCents);
  assert.equal(find(after, 'enterprise').priceCents, find(before, 'enterprise').priceCents);
});

test('three-week synthetic paired controls have identical opportunities and retained A before any gate', () => {
  const input = {calibration: syntheticCalibration(), cell: cell({demand: 'high'}), seed: 7, testOnlyWeeks: 3};
  const outputs = ['A', 'B', 'C', 'D'].map(policy => simulatePolicy({...input, policy}));
  assert(outputs[0].totals.arrivals > 0);
  for (const output of outputs) {
    assert.equal(output.outputKind, 'SYNTHETIC_CONTROL_OR_TRUNCATED_TEST');
    assert.equal(output.actualCollectionsCents, 0);
    assert.equal(output.actualOperatingProfitCents, null);
    assert.equal(output.investments.length, 0);
    assert.equal(output.closingCapability, 'A');
    assert.deepEqual(output.history, outputs[0].history);
    assert(compactHistory(output).every(row => row.length === WEEKLY_COLUMNS.length));
  }
});

test('an insolvent synthetic service stops new orders while continuing finite ledger settlement', () => {
  const protocol = clonedProtocol();
  protocol.capital.initialSeedCents = 1;
  const currentCell = sensitivityCells(protocol).find(item => item.demand === 'high' && item.costBundle === 'low');
  const result = simulatePolicy({calibration: syntheticCalibration(), cell: currentCell,
    seed: 3, policy: 'C', protocol, testOnlyWeeks: 2});
  assert.equal(result.closing.insolvencyWeek, 0);
  assert.equal(result.totals.orders, 0);
  assert.equal(result.closing.cashCents, 0);
  assert.equal(result.closing.investmentCents, 0);
  assert(result.closing.unpaidCents > 0);
});

test('diagnostic reconstruction thresholds never become credited savings or actual cost observations', () => {
  const diagnostics = deploymentDiagnostics(syntheticCalibration());
  assert.equal(diagnostics.actualCollectionsCents, 0);
  assert(Object.values(diagnostics.actualCosts).every(value => value === null));
  assert.equal(diagnostics.illustrativeMatchedHumanTables.length, 18);
  for (const threshold of diagnostics.investmentAndGraphThresholds) {
    assert.equal(threshold.diagnosticOnly, true);
    assert.equal(threshold.credit.assumedAttentionSavingsCents, 0);
    assert.equal(threshold.availableCents, 0);
    assert(threshold.requiredUnmeasuredAttentionMinutesPerReuse >= 0);
  }
  for (const row of diagnostics.illustrativeMatchedHumanTables) {
    const collected = row.canonical.ledger.events.find(event => event.type === 'revenue' && event.category === 'collected');
    assert.equal(collected.amountMinor, 0);
    assert.equal(row.fullCostKnown, false);
  }
});

test('economic freeze binds the complete static import closure and preserves canonical bytes', async () => {
  const sourceFiles = [];
  for (const path of SOURCE_FILES) {
    const bytes = await readFile(resolve(STUDY_ROOT, path));
    sourceFiles.push({path, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex')});
  }
  const freeze = {schema: 'agi-alpha.work-discovery.economic-freeze.v1',
    status: 'SELF_DECLARED_BEFORE_ECONOMIC_OUTCOME_CAMPAIGN',
    protocolSha256: createHash('sha256').update(JSON.stringify(PROTOCOL)).digest('hex'), sourceFiles,
    calibration: sourceFiles.find(file => file.path === 'tests/economics.test.mjs')};
  assert.equal(await verifyFreeze(freeze), true);
  freeze.sourceFiles = freeze.sourceFiles.filter(file => !file.path.endsWith('/ledger.mjs'));
  await assert.rejects(verifyFreeze(freeze), /freeze required/);
});

test('normalization preserves blocked intended cases, conditional acceptance and standalone shared costs', () => {
  const records = [];
  for (const arm of ['A', 'B', 'C', 'D']) {
    for (const blocked of [false, true]) records.push({arm, pair: blocked ? ['v3', 'v4'] : ['v1', 'v2'],
      accepted: !blocked, status: blocked ? 'INPUT_ACQUISITION_FAILED' : 'ACCEPTED_SCOPED_RESEARCH_OUTPUT',
      cpuSeconds: blocked ? 0.1 : 1, wallSeconds: blocked ? 0.2 : 2,
      sharedAcquisitionCpuSeconds: 0.25, sharedAcquisitionWallSeconds: 0.5});
  }
  const campaign = {schema: 'api-production-campaign/v1', phase: 'primary', sourceQualification: 'PASS',
    finalSourceCheck: {accepted: true, sha256: '2'.repeat(64)}, records, driverOverheadCpuSeconds: 0.08, wallSeconds: 9.6};
  const input = {campaign,
    productionProtocol: {primary_pairs: [['v1', 'v2'], ['v3', 'v4']], transfer_pairs: [['v2', 'v3']]},
    acquisitionManifest: {sessions: [{cpuSeconds: 5, wallSeconds: 7}], entries: {all: {cpuSeconds: 4, wallSeconds: 6}}},
    evidence: syntheticCalibration().evidence, acceptanceSpecificationSha256: '1'.repeat(64)};
  const normalized = validateCalibration(normalizeExecutedCampaign(input));
  assert.equal(normalized.sourceAvailability.scenarioProbability, 0.5);
  assert.equal(normalized.arms.A.accepted, 1);
  assert.equal(normalized.arms.A.attempts, 2);
  assert.equal(normalized.arms.A.inputBlocked, 1);
  assert.equal(normalized.arms.A.cpuSecondsMean, 0.55);
  assert.equal(normalized.commonCosts.standaloneAcquisitionCpuSecondsPerPlanned, 1 + 1 / 3);
  assert.equal(normalized.commonCosts.driverCpuSecondsPerPlanned, 0.01);
  assert.equal(normalized.acceptanceEquivalent, true);
  campaign.records.pop();
  assert.throws(() => normalizeExecutedCampaign(input), /denominator/);
});

test('source failure never becomes a successful technical retry and still incurs acquisition and triage cost', () => {
  const calibration = syntheticCalibration();
  for (const arm of Object.values(calibration.arms)) {
    Object.assign(arm, {accepted: 2, inputBlocked: 2,
      cpuSecondsMean: (arm.cpuSecondsAvailableMean + 0.1) / 2,
      wallSecondsMean: (arm.wallSecondsAvailableMean + 0.1) / 2,
      cpuSecondsBlockedMean: 0.1, wallSecondsBlockedMean: 0.1});
  }
  calibration.sourceAvailability = {planned: 4, available: 2, inputBlocked: 2, scenarioProbability: 0.5,
    interpretation: 'Synthetic mixed availability; selected seed tests an unavailable intended job'};
  const protocol = clonedProtocol();
  protocol.demand.reference = 1;
  protocol.market.buyers = 1;
  protocol.market.humanOnlyMinutes = [45];
  protocol.market.willingnessMultipliers = [2];
  const currentCell = sensitivityCells(protocol).find(item => item.demand === 'reference' &&
    item.integrationMinutes === 0 && item.competitorStrength === 'equal' && item.costBundle === 'low');
  // Choose an adversarial arithmetic control, never a production scenario or reported result.
  const seed = Array.from({length: 100}, (_, index) => index + 1).find(value =>
    randomDraw(value, 'source-availability', 1, 0) >= 0.5 && randomDraw(value, 'paid-offer-tie', 1, 0) >= 0.5);
  const result = simulatePolicy({calibration, cell: currentCell, seed, policy: 'A', protocol, testOnlyWeeks: 1});
  assert(result.totals.orders > 0);
  assert.equal(result.totals.attempts, 0);
  assert.equal(result.totals.accepted, 0);
  assert.equal(result.totals.inputBlocked, result.totals.orders);
  assert.equal(result.closing.invoicedCents, 0);
  assert(result.costItemsCents.source_unavailable_triage > 0);
  assert(result.costItemsCents.compute > 0);
  assert.equal(result.costItemsCents.onboarding_support, undefined);
  assert.equal(result.totals.unavailableOpportunities, result.totals.arrivals);
});

test('equal complete-cost tariffs are symmetric and paid-offer ties are neutral while free DIY stays available', () => {
  const currentCell = cell(), tariff = selectTariff(currentCell);
  const offers = buyerOffers({profile: {humanMinutes: 45}, state: {diy: true, ai: true, enterprise: true},
    week: 1, cell: currentCell, priceCents: tariff.priceCents});
  const ai = offers.find(offer => offer.id === 'ai'), enterprise = offers.find(offer => offer.id === 'enterprise');
  assert.equal(ai.priceCents, enterprise.priceCents);
  assert.equal(chooseBuyer(offers, 100_000, 0.1).id, 'ai');
  assert.equal(chooseBuyer(offers, 100_000, 0.9).id, 'enterprise');
  assert.equal(offers.find(offer => offer.id === 'diy').attentionCents, laborCents(45));
});

test('full cost per collected job mechanically includes source failures, retry risk and noncollection', () => {
  const calibration = syntheticCalibration();
  for (const arm of Object.values(calibration.arms)) {
    arm.inputBlocked = 2; arm.accepted = 2;
    arm.cpuSecondsMean /= 2; arm.wallSecondsMean /= 2;
  }
  calibration.sourceAvailability = {planned: 4, inputBlocked: 2, available: 2, scenarioProbability: 0.5,
    interpretation: 'Synthetic pricing cost control'};
  const costing = prospectiveCostRaw(cell(), {calibration});
  assert.equal(costing.expectedPaidProbability, 0.5 * (1 - 0.02 ** 2) * 0.98);
  assert(costing.itemsCents.unavailableSourceTriage > 0);
  assert.equal(costing.prospectiveCostCents,
    Math.ceil(costing.expectedCostCentsPerIntended / costing.expectedPaidProbability));
  const before = prospectiveCost(cell());
  assert(costing.prospectiveCostCents > before.prospectiveCostCents);
});

test('source availability does not mislabel accepted available work as technical rejection', () => {
  const calibration = syntheticCalibration({A: 3600, B: 1800, C: 900, D: 1000});
  for (const arm of Object.values(calibration.arms)) {
    arm.inputBlocked = 2; arm.accepted = 2;
    arm.cpuSecondsMean /= 2; arm.wallSecondsMean /= 2;
  }
  calibration.sourceAvailability = {planned: 4, inputBlocked: 2, available: 2, scenarioProbability: 0.5,
    interpretation: 'Synthetic availability condition'};
  validateCalibration(calibration);
  const decision = budgetDecision({calibration});
  assert.equal(decision.qualifies, true);
  assert(!decision.reasons.includes('MATCHED_EXECUTED_ACCEPTANCE_NOT_ESTABLISHED'));
  assert.equal(decision.weeklyCashRoundingProvisionMicroUSD, 260_000);
  assert.equal(decision.conservativeNetBenefitMicroUSD, decision.canonical.netBenefit - 260_000);
});
