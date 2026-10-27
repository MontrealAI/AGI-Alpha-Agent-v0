import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {resolve, dirname} from 'node:path';
import {calculateInvestment, planMission} from './inherited/canonical/shadow-ledger.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const assert = (condition, reason) => { if (!condition) throw Error(reason); };
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export const assumptions = Object.freeze({currency: 'CAD', wageHourlyCents: 6521, wageSource: 'Government of Canada Job Bank, Ontario NOC41101 median',
  wageSourceURL: 'https://www.jobbank.gc.ca/wagereport/occupation/15815', employmentBurdenFactor: 1.3,
  reviewMinutesRange: [1, 3, 5, 10, 20], measuredReviewAdvantageMinutes: null, referenceAssumedReviewAdvantageMinutes: 0,
  offeredPriceCentsRange: [500, 1000, 2000], addedBuyerIntegrationMinutesPerJobRange: [0, 1, 5],
  existingOrdinaryToolIncrementalLicenseCents: 0,
  providerOperatorMinutesRange: [0, 1, 3, 5], providerSupportMinutesRange: [0, 1], providerHourlyCents: 4000,
  computeHourlyCents: 25, toolCentsPerAttempt: 25, providerOnboardingMinutes: 60, buyerLifetimeJobsRange: [12, 50, 200],
  hypotheticalNewCapabilityCostCents: 40000, hypotheticalUpkeepPerReuseCents: 25,
  investmentReuseRange: [12, 50, 100, 250], historicalResearchCostCents: null,
  interpretation: 'Wage is sourced. All times, price, rate allocations, workload and costs are declared sensitivity coordinates. Ordinary Word-like review ranges are not measured Microsoft workflow times. Zero incremental ordinary-tool license assumes an already licensed user; no subscription quote is invented.'});

export function analyzeReconciliation(input) {
  const records = Array.isArray(input) ? input : input?.records;
  assert(Array.isArray(records) && records.length > 0, 'Actual two-method production records required');
  const ids = new Set();
  for (const row of records) {
    assert(typeof row.case_id === 'string' && row.case_id.length > 0, 'Case identity required');
    assert(['characters', 'lines'].includes(row.method), 'Only the two actual methods are admitted');
    assert(typeof row.accepted_deterministic === 'boolean', 'Objective technical result required');
    assert(Number.isFinite(row.runtime_seconds) && row.runtime_seconds >= 0, 'Measured runtime required');
    assert(Number.isInteger(row.attempts) && row.attempts >= 1, 'Attempt aggregate required');
    assert(!ids.has(`${row.method}:${row.case_id}`), 'Duplicate aggregate'); ids.add(`${row.method}:${row.case_id}`);
  }
  const methods = Object.fromEntries(['characters', 'lines'].map(method => [method, records.filter(row => row.method === method)]));
  assert(methods.characters.length > 0 && methods.lines.length > 0, 'Both measured methods required');
  assert(JSON.stringify(methods.characters.map(row => row.case_id).sort()) === JSON.stringify(methods.lines.map(row => row.case_id).sort()), 'Matched cases required');
  const measured = Object.fromEntries(Object.entries(methods).map(([method, rows]) => {
    const accepted = rows.filter(row => row.accepted_deterministic).length;
    return [method, {cases: rows.length, acceptedTechnical: accepted, rejectedTechnical: rows.length - accepted,
      totalRuntimeSeconds: rows.reduce((a, row) => a + row.runtime_seconds, 0),
      meanRuntimeSeconds: rows.reduce((a, row) => a + row.runtime_seconds, 0) / rows.length,
      totalAttempts: rows.reduce((a, row) => a + row.attempts, 0),
      acceptanceScope: 'Exact source/changed-text conservation only; redline usability and professional or commercial acceptance unassessed'}];
  }));
  const wage = assumptions.wageHourlyCents * assumptions.employmentBurdenFactor;
  const demandThresholds = [];
  for (const ordinaryReviewMinutes of assumptions.reviewMinutesRange) for (const offeredPriceCents of assumptions.offeredPriceCentsRange)
    for (const addedBuyerIntegrationMinutes of assumptions.addedBuyerIntegrationMinutesPerJobRange) {
      const ordinaryCost = ordinaryReviewMinutes * wage / 60;
      const customerCost = offeredPriceCents + (ordinaryReviewMinutes + addedBuyerIntegrationMinutes) * wage / 60;
      demandThresholds.push({ordinaryReviewMinutesAssumed: ordinaryReviewMinutes, equalAGIReviewMinutesAssumed: ordinaryReviewMinutes,
        offeredPriceCentsAssumed: offeredPriceCents, addedBuyerIntegrationMinutesAssumed: addedBuyerIntegrationMinutes,
        humanOrdinaryOpportunityCostCents: ordinaryCost, buyerPricePlusOpportunityCostCents: customerCost,
        buyerSavingsAtNoMeasuredAdvantageCents: ordinaryCost - customerCost,
        requiredSavedMinutesToBreakEven: offeredPriceCents * 60 / wage + addedBuyerIntegrationMinutes,
        sufficientEvenIfAllOrdinaryMinutesRemoved: ordinaryReviewMinutes >= offeredPriceCents * 60 / wage + addedBuyerIntegrationMinutes,
        condition: 'Necessary value threshold, not demonstrated savings or willingness to pay'});
    }
  const providerThresholds = [];
  for (const [method, m] of Object.entries(measured)) for (const operationMinutes of assumptions.providerOperatorMinutesRange)
    for (const supportMinutes of assumptions.providerSupportMinutesRange) for (const lifetimeJobs of assumptions.buyerLifetimeJobsRange) {
      const technicalCompute = m.totalRuntimeSeconds / 3600 * assumptions.computeHourlyCents;
      const tools = m.totalAttempts * assumptions.toolCentsPerAttempt;
      const labor = (operationMinutes + supportMinutes) / 60 * assumptions.providerHourlyCents * m.cases;
      const marginalPerAccepted = m.acceptedTechnical ? (technicalCompute + tools + labor) / m.acceptedTechnical : null;
      const integrationAllocation = assumptions.providerOnboardingMinutes / 60 * assumptions.providerHourlyCents / lifetimeJobs;
      providerThresholds.push({method, operationMinutesAssumed: operationMinutes, supportMinutesAssumed: supportMinutes,
        buyerLifetimeJobsAssumed: lifetimeJobs, computeShadowAllocationCents: technicalCompute,
        marginalCostPerTechnicallyAcceptedPacketCents: marginalPerAccepted,
        providerOnboardingAllocationPerJobCents: integrationAllocation,
        priceToCoverMarginalAndOnboardingCents: marginalPerAccepted === null ? null : marginalPerAccepted + integrationAllocation,
        completeRecurringCostCents: null, fullyAllocatedCostCents: null,
        missing: ['Measured handling/support effort', 'Acquisition', 'Professional review if needed', 'Maintenance', 'Complete historical research cost']});
    }
  const noInvestment = assumptions.investmentReuseRange.map(reuses => ({reusesAssumed: reuses,
    actualNewRetainedCapabilitySupplied: false, measuredIncrementalHumanBenefit: null,
    noBenefitControl: calculateInvestment({constructionCostMinor: assumptions.hypotheticalNewCapabilityCostCents,
      failedConstructionCostMinor: 0, maintenancePerReuseMinor: assumptions.hypotheticalUpkeepPerReuseCents,
      expectedSavingPerReuseMinor: 0, remainingReuses: reuses}),
    action: 'NO_WORTHWHILE_NEW_CAPABILITY_ESTABLISHED'}));
  const actual = planMission({missionId: 'reconciliation-research', currency: 'CAD',
    reference: 'Two ordinary comparison methods; technical conservation only; no commercial acceptance, customers or collections.',
    acceptance: 'unknown', totalCollectedCents: 0, totalOperatingCostCents: null, operatingCostsComplete: false,
    capabilityCostCents: null, reserveCents: null, obligationCents: null});
  return {schema: 'legal-reconciliation-unit-economics/v1', basis: 'MEASURED_MECHANICS_PLUS_EXPLICIT_THRESHOLDS',
    assumptions, measured, demandThresholds, providerThresholds, noInvestment, actualLedger: actual,
    conclusions: {observedCollectionsCents: 0, actualAvailableOperatingSurplus: null, humanWorkAdvantage: 'NOT_MEASURED',
      commercialAlternativeSuperiority: 'NOT_ESTABLISHED', retainedSkillBenefit: 'NO_NEW_RETAINED_SKILL_IN_THIS_VARIANT',
      selfFinancingSuccession: 'NOT_ESTABLISHED', historicalCostRecovery: 'UNKNOWN'},
    caution: 'A whole-document replace can conserve every changed character while being a poor redline. Technical conservation is not complete usability or professional acceptance. No duplicated B/C efficacy arms were created.'};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [, , input, output] = process.argv; assert(input && output, 'Usage: node secondary-unit.mjs INPUT_JSON OUTPUT_DIRECTORY');
  const raw = readFileSync(input), result = analyzeReconciliation(JSON.parse(raw));
  mkdirSync(output, {recursive: true});
  writeFileSync(resolve(output, 'unit-thresholds.json'), JSON.stringify(result, null, 2) + '\n');
  writeFileSync(resolve(output, 'input-provenance.json'), JSON.stringify({inputSHA256: hash(raw),
    sourceSHA256: hash(readFileSync(fileURLToPath(import.meta.url))), sourceFile: 'economics/secondary-unit.mjs',
    actualCollectionsCents: 0}, null, 2) + '\n');
  process.stdout.write(JSON.stringify({methods: result.measured, actualCollectionsCents: 0, actualAvailableSurplus: null}) + '\n');
}
