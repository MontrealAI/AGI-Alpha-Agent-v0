// SPDX-License-Identifier: Apache-2.0
// Declared before the economic outcome campaign. None of these market defaults is an observation.

function deepFreeze(value) {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value)) deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

export const PROTOCOL = deepFreeze({
  schema: 'agi-alpha.work-discovery.economic-protocol.v1',
  id: 'public-api-contract-service-primary-v1',
  money: 'USD',
  measurementKind: 'EXECUTED_PUBLIC_LOCAL',
  actualCollectionsCents: 0,
  campaign: {
    weeks: 52,
    pairedSeeds: Array.from({length: 16}, (_, index) => index + 1),
    expectedCells: 24,
    expectedWorlds: 384,
    policies: ['A', 'B', 'C', 'D'],
    maxOutputBytes: 90_000_000,
  },
  capital: {initialSeedCents: 100_000, reserveCents: 20_000},
  rates: {annualWageUSD: 135_980, assumedAnnualHours: 2_080, wageUSDPerHour: 65.375, cpuUSDPerHour: 1},
  demand: {low: 0.025, reference: 0.125, high: 0.25},
  integrationMinutes: [0, 15],
  competitorStrengths: ['strong', 'equal'],
  costBundles: {
    low: {
      historicalDiscoveryMinutes: 60, historicalFailedDiscoveryMinutes: 30, historicalInferenceCents: 500,
      setupMinutes: 15, setupOtherCents: 500,
      residualMinutesPerAttempt: 2, supportMinutesPerOrder: 0.5, providerOnboardingMinutes: 5,
      weeklyBusinessMinutes: 5, weeklyBaseMaintenanceMinutes: 2, weeklyToolCents: 100,
      investment1: {
        constructionMinutes: 60, failedConstructionMinutes: 15, validationMinutes: 30,
        integrationMinutes: 15, inferenceCents: 500, maintenanceMinutesPerReuse: 0.10,
      },
      investment2: {
        constructionMinutes: 45, failedConstructionMinutes: 15, validationMinutes: 30,
        integrationMinutes: 15, inferenceCents: 500, maintenanceMinutesPerReuse: 0.10,
      },
      graphExtra: {
        constructionMinutes: 15, failedConstructionMinutes: 0, validationMinutes: 15,
        integrationMinutes: 10, inferenceCents: 250, maintenanceMinutesPerReuse: 0.05,
      },
    },
    reference: {
      historicalDiscoveryMinutes: 240, historicalFailedDiscoveryMinutes: 120, historicalInferenceCents: 2500,
      setupMinutes: 60, setupOtherCents: 2000,
      residualMinutesPerAttempt: 5, supportMinutesPerOrder: 2, providerOnboardingMinutes: 15,
      weeklyBusinessMinutes: 15, weeklyBaseMaintenanceMinutes: 5, weeklyToolCents: 500,
      investment1: {
        constructionMinutes: 240, failedConstructionMinutes: 60, validationMinutes: 60,
        integrationMinutes: 30, inferenceCents: 2500, maintenanceMinutesPerReuse: 0.50,
      },
      investment2: {
        constructionMinutes: 180, failedConstructionMinutes: 45, validationMinutes: 60,
        integrationMinutes: 30, inferenceCents: 2000, maintenanceMinutesPerReuse: 0.50,
      },
      graphExtra: {
        constructionMinutes: 60, failedConstructionMinutes: 15, validationMinutes: 30,
        integrationMinutes: 20, inferenceCents: 1000, maintenanceMinutesPerReuse: 0.25,
      },
    },
  },
  market: {
    buyers: 24,
    humanOnlyMinutes: [5, 15, 45],
    willingnessMultipliers: [0.5, 0.8, 1.2],
    customerReviewMinutes: 2,
    publicDiyRule: 'Same competent public-tool human-only duration; no additional assumed automation saving.',
    aiLaborEfficiency: {strong: 0.60, equal: 1},
    equalCompetitorTariffRule: 'Identical cost-to-collected-job formula and labor-equivalent tariff grid.',
    equalPriceChoice: 'Public DIY wins exact ties; other equal-minimum offers split by a common seeded draw.',
    competitorCopyWeek: 20,
    competitorCopyEffortMultiplier: 0.75,
    competitorCopyPriceMultiplier: 0.80,
    commonExecutionStressSuccessProbability: 0.98,
    sourceAvailabilityRule: 'Common per-job fraction of all frozen intended cases; scenario condition, not a population estimate.',
    unavailableSourceRetry: false,
    maxAttempts: 2,
    correctionMinutesPerRejectedAttempt: 5,
    paymentDelayWeeks: 2,
    paymentProbability: 0.98,
    expenseDelayWeeks: 1,
    providerAttentionMinutesPerWeek: 240,
    machineCPUSecondsPerWeek: 3600,
    machineWallSecondsPerWeek: 3600,
  },
  pricing: {
    rule: 'smallest labor-equivalent tariff covering expected collected-job full prospective cost at reference intended utilization',
    tariffMinutes: [2, 5, 10, 15, 30, 60],
    referenceJobsPerWeek: 3,
    assumedCustomerReusesForOnboardingAllocation: 8,
    commonComputeAllowanceCentsPerOrder: 1,
    fixedAcrossPoliciesAndDemandCells: true,
  },
  investment: {
    earliestWeek: 8,
    forecastLookbackWeeks: 8,
    forecastReuseDiscount: 0.5,
    usefulLifeWeeks: 26,
    maintenanceMultipliersForDiagnostics: [0, 1, 2, 4],
    policies: {A: [], B: ['investment1'], C: ['investment1', 'investment2'], D: ['investment1', 'investment2graph']},
    gate: 'signed executed CPU cost savings only; complete incremental cost; finite life; operating funds only',
    noAttentionSavingsCredit: true,
    noDemandOrQualityPremium: true,
    retainedConventionalComparator: true,
  },
  diagnostics: {
    residualMinutes: [2, 5, 10],
    maximumAnalyticReuses: 1_000_000,
    reconstructionBenefit: 'UNMEASURED_THRESHOLD_ONLY_NO_CAMPAIGN',
  },
  unknownActualCosts: {
    authoringInferenceCents: null,
    historicalResearchLaborCents: null,
    failedDiscoveryLaborCents: null,
    constructionLaborCents: null,
    reviewerAttentionMinutes: null,
    onboardingMinutes: null,
    supportMinutes: null,
    maintenanceMinutes: null,
    customerAcquisitionCents: null,
    actualFullCostCents: null,
    realizedOperatingProfitCents: null,
  },
  provenance: {
    wage: {
      kind: 'SOURCED_ANCHOR_DERIVED_HOURLY',
      annualUSD: 135_980,
      period: 'May 2025',
      url: 'https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm',
      inheritedEvidence: 'heritage/graph-foundations/market/inherited/upstream/protocol/external-sources.json#S01',
      transformation: '135980 / assumed 2080 annual working hours = 65.375 USD/hour',
      limitation: 'Employee wage anchor; excludes benefits and is not a contractor quote or willingness-to-pay observation.',
    },
    execution: {
      kind: 'OBSERVED_WHEN_CALIBRATION_IS_SUPPLIED',
      fields: ['attempts', 'accepted', 'cpuSecondsMean', 'wallSecondsMean'],
      limitation: 'Public local accepted work; small sample is not a market reliability estimate or paid production.',
    },
    remainingParameters: {
      kind: 'ASSUMED_PREDECLARED',
      includes: [
        'job durations, labor loads and inference allowances', 'arrivals, buyer pool and willingness to pay',
        'tariff rule and utilization', 'competitor complete cost, effort, price, copying and cuts',
        'integration, review, support, maintenance and correction', 'payment delay/default and capacity',
        'CPU tariff, useful life, investment forecast and seed/reserve',
      ],
      limitation: 'Sensitivity conditions only. No demand, price, attention reduction or zero-cost operating work is asserted.',
    },
    accounting: {
      primitive: 'heritage/graph-foundations/market/inherited/upstream/canonical/shadow-ledger.mjs',
      sha256: 'cdc7c5a73593050a9af79b54589462e27f61b868e88ca6985d5cb639f3066d21',
      exportsReused: ['calculateInvestment', 'planMission'],
      note: 'Verbatim inherited primitives. All new campaign receipts are simulated; canonical scenario price is an explicit amount.',
    },
  },
  scope: [
    'Same selected structural GET 2xx JSON response-contract outcome and acceptance in every offering.',
    'A is the retained independent conventional builder, never rebuilt per job.',
    'B, C and D start with A; no candidate is installed before its funded incremental gate passes.',
    'D has the same skills, evidence and dependencies as C; its second asset includes itemized graph costs.',
    'The equal AI-assisted competitor uses the identical complete prospective cost function; stronger efficiency is an explicit assumption.',
    'Competitors retain conventional tooling and are assessed against the same accepted output; neither competitor pays repeated reconstruction.',
    'Common historical discovery and ordinary setup are paid at opening once per counterfactual enterprise.',
    'Historical discovery excludes the candidate construction budgets charged once upon investment.',
    'Actual study research costs remain unknown where unmetered; model budgets are not substituted for them.',
    'No token appreciation, internal-transfer profit, real customer payment, financial transaction or authority is created.',
    'Unavailable frozen inputs remain failed intended cases; acquisition is charged and a technical retry cannot make the input available.',
    'Every alternative has the same source gate and limited dossier scope; offer selections are not accepted competitor deliveries.',
  ],
});

export function sensitivityCells(protocol = PROTOCOL) {
  const cells = [];
  for (const [demand, arrivalProbability] of Object.entries(protocol.demand)) {
    for (const integrationMinutes of protocol.integrationMinutes) {
      for (const competitorStrength of protocol.competitorStrengths) {
        for (const costBundle of Object.keys(protocol.costBundles)) {
          cells.push({
            id: `${demand}-i${integrationMinutes}-${competitorStrength}-${costBundle}`,
            demand, arrivalProbability, integrationMinutes, competitorStrength, costBundle,
          });
        }
      }
    }
  }
  return cells;
}

export function laborCents(minutes, protocol = PROTOCOL) {
  if (!Number.isFinite(minutes) || minutes < 0) throw Error('Nonnegative finite labor minutes required');
  return Math.max(0, Math.ceil(minutes * protocol.rates.wageUSDPerHour * 100 / 60 - 1e-9));
}

export function cpuMicroUSD(seconds, protocol = PROTOCOL) {
  if (!Number.isFinite(seconds)) throw Error('Finite signed CPU seconds required');
  // Truncation cannot manufacture a positive saving from a sub-micro-dollar difference.
  return Math.trunc(seconds * protocol.rates.cpuUSDPerHour * 1_000_000 / 3600) || 0;
}
