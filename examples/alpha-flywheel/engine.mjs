// SPDX-License-Identifier: Apache-2.0
// Public teaching simulation. No model calls, customer activity or operating authority.
const clone = value => JSON.parse(JSON.stringify(value));
const money = value => Math.round((value + Number.EPSILON) * 100) / 100;
const sum = rows => money(rows.reduce((total, row) => total + row.amount, 0));
const pair = (en, fr) => ({ en, fr });
const fail = code => { throw Error(code); };
const finite = (value, low, high, code) => {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < low || value > high) fail(code);
  return value;
};
const freeze = value => {
  for (const child of Object.values(value)) if (child && typeof child === 'object') freeze(child);
  return Object.freeze(value);
};
function rng(seed) {
  let state = seed >>> 0;
  return () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 4294967296; };
}

export const VERSION = 'alpha-flywheel-model/1.0.0';
export const UNIT_ECONOMICS = Object.freeze({ baseDelivery: 2660, correctionEnvelope: 450,
  supportAccrualPerAccepted: 150, fixedBusinessOverhead: 1500, collectionFeeRate: 0.029, evidence: 'ASSUMED' });
export const DEVELOPMENT_SEEDS = Object.freeze([1103, 2251, 3371, 4483, 5501, 6619, 7741, 8863,
  9901, 10193, 11353, 12503, 13627, 14731, 15859, 16963]);
const policyCache = new Map();
export const MISSION = freeze({
  title: pair('An algorithm foundry for resilient space operations', 'Une fonderie d’algorithmes pour des opérations spatiales résilientes'),
  customer: pair('A small satellite operator planning competing downlink windows.', 'Un opérateur de petits satellites planifiant des fenêtres de liaison concurrentes.'),
  restriction: pair('Limited ground-station time and conflicting high-value observations.', 'Un temps de station au sol limité et des observations utiles en conflit.'),
  approach: pair('Reframe the queue as a constrained weighted schedule; compare a simple baseline and independently check every constraint.', 'Reformuler la file en calendrier pondéré sous contraintes ; comparer une référence simple et vérifier chaque contrainte.'),
  deliverable: pair('An executable scheduling method, a feasible plan, comparison evidence and a constraint report. The public sample solves five synthetic windows; the full customer mission is modeled.', 'Une méthode de planification exécutable, un plan réalisable, des comparaisons et un rapport de contraintes. L’exemple public résout cinq fenêtres synthétiques ; la mission client complète est modélisée.'),
  acceptance: pair('No overlapping use of the single station, all windows respected, reproducible objective comparison and explicit refusal outside the supported scope.', 'Aucun chevauchement sur la station unique, respect de toutes les fenêtres, comparaison reproductible et refus explicite hors périmètre.'),
  originatingMission: 'public-constellation-001',
  scope: 'Public synthetic scheduling methods only; no satellite command or operational flight software.',
});

const SOURCE = freeze({
  version: VERSION, evidenceDate: '2026-10-26', type: 'ASSUMED_TEACHING_MODEL',
  horizonDays: 90, population: 18,
  url: 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/examples/alpha-flywheel/README.md',
  humanReference: {
    amount: 24000, hours: 160, hourlyRate: 150, currency: 'USD', evidence: 'ASSUMED',
    scope: '30-day engineering package: 60h algorithm/software, 40h verification, 24h operations research, 20h domain analysis, 16h project delivery; 160h at an assumed blended USD150/h.',
    uncertaintyRange: [16000, 40000], matchedPeriodDays: 30,
  },
  foundations: [
    { id: 'agi-alpha-work-economics-v1', version: 'v1', horizon: '36 fresh bounded reconciliation jobs; scope of original paper only', population: 36, type: 'EXTERNALLY_REPORTED',
      url: '../papers/agi-alpha-work-economics-v1.pdf', sha256: '8b9df6f5ef1887d6f972ccfbe26d61a5551962dea41ad7c6595d431dfacb2f51',
      limitation: 'Different clerical task and horizon. No performance or monetary figures are transferred to the space-engineering simulation.' },
    { id: 'agi-alpha-capability-construction-v1', version: 'v1', horizon: '42 fresh jobs across seven digital-work families; scope of original paper only', population: 42, type: 'EXTERNALLY_REPORTED',
      url: '../papers/agi-alpha-capability-construction-v1.pdf', sha256: '51ee8ded6860b6ab6b1a7bd1e0901fe864a96c30d40446c3743dd975ba139b28',
      limitation: 'Reusable invocation does not establish net savings or durable advantage. No positive retention finding is assumed from this paper.' },
  ],
  assumptions: [
    { id: 'human-reference', status: 'ASSUMED', range: [16000, 40000], dependsOn: 'Matched human-service price and displayed customer savings.' },
    { id: 'demand', status: 'ASSUMED', range: [0.35, 1], dependsOn: 'Sales, price choice, utilization and skill reuse.' },
    { id: 'quality', status: 'ASSUMED', range: [0.65, 0.98], dependsOn: 'Acceptance, corrections, refunds and quality-linked profit.' },
    { id: 'complete-cost', status: 'ASSUMED', range: [0.8, 2.2], dependsOn: 'Profit and available operating funds. Includes business overhead and automated checking.' },
    { id: 'reuse-transfer', status: 'ASSUMED', range: [0, 650], dependsOn: 'Optional retention decision and later direct delivery savings.' },
  ],
  limitation: 'Illustrative engineering venture, not a calibrated commercial forecast. No observed sales, frontier-model task execution or human-team matched trial. Studies remain separate and retain their original limitations.',
});
const preset = (id, title, description, parameters) => ({ id, title, description, horizonDays: 90, population: 18, source: SOURCE, ...parameters });
export const PRESETS = freeze([
  preset('baseline', pair('Useful delivery first', 'Livrer utile d’abord'), pair('Conditional profitable delivery; assess optional direct reuse savings.', 'Livraison profitable sous hypothèses ; examiner les économies de réutilisation facultatives.'),
    { demand: 0.9, quality: 0.93, costMultiplier: 1, reuseSaving: 650, capacity: 6, seedCapital: 30000 }),
  preset('stress', pair('Demand and quality stress', 'Pression sur la demande et la qualité'), pair('Fewer buyers, more errors, higher costs. Preserve adverse results.', 'Moins d’acheteurs, plus d’erreurs et des coûts accrus. Conserver les résultats défavorables.'),
    { demand: 0.4, quality: 0.7, costMultiplier: 2.1, reuseSaving: 250, capacity: 4, seedCapital: 16000 }),
  preset('frontier', pair('When frontier Beta improves', 'Quand la référence Beta progresse'), pair('Ordinary frontier tools absorb the old method; retention can lose its advantage.', 'Les outils courants absorbent l’ancienne méthode ; sa conservation peut perdre son intérêt.'),
    { demand: 0.9, quality: 0.96, costMultiplier: 0.85, reuseSaving: 30, capacity: 6, seedCapital: 30000 }),
]);

const POLICY_NAMES = ['beta', 'retain', 'invest', 'bundle'];
const deliveryItems = [
  ['intake-clarification', 180], ['reasoning-learning-development', 1600], ['sandbox-tools-compute', 220],
  ['automated-independent-checks', 360], ['packaging-recovery', 120], ['business-support-allocation', 180],
];
const retentionItems = [
  ['extraction', 180], ['generalization', 160], ['fresh-validation', 200], ['packaging', 90],
  ['integration', 70], ['sharing', 60], ['revalidation', 100], ['upkeep', 80],
];
const assessmentCost = 120;
const retentionCost = sum(retentionItems.map(([id, amount]) => ({ id, amount }))) + assessmentCost;

function expectedDemand(price, settings) {
  // Four explicit buyer choices. Public cohort preferences are the declared model, not future observations.
  const choices = { enterprise: 0, human: 0, postpone: 0, none: 0 };
  for (let i = 0; i < 18; i++) {
    const budget = 6500 + i * 900;
    const urgency = (i % 6) / 5;
    if (budget < 8000) choices.none++;
    else if (price <= budget && price <= 24000 * (0.55 + 0.3 * urgency)) choices.enterprise += settings.demand;
    else if (budget >= 21000 && urgency > 0.6) choices.human++;
    else choices.postpone++;
  }
  // Remaining fractional expected leads abstain rather than becoming invisible demand.
  choices.none = money(18 - choices.enterprise - choices.human - choices.postpone);
  return { ...choices, enterprise: money(choices.enterprise) };
}

function policyForecast(policy, expectedJobs, settings) {
  const reuses = Math.max(0, expectedJobs * settings.quality - 1);
  const assessed = policy !== 'beta';
  const extraInvestment = policy === 'invest' || policy === 'bundle' ? 3600 : 0;
  const extraSaving = policy === 'bundle' ? 700 : policy === 'invest' ? 400 : 0;
  const retentionWanted = policy === 'retain' || policy === 'bundle';
  const grossBenefit = money(reuses * (retentionWanted ? settings.reuseSaving : 0));
  const retentionNet = money(grossBenefit - retentionCost);
  const bundleNet = money(reuses * (settings.reuseSaving + extraSaving) - retentionCost - extraInvestment);
  const retain = retentionWanted && (policy === 'bundle' ? bundleNet : retentionNet) > 0;
  const invest = extraInvestment > 0 && (policy === 'bundle' ? bundleNet > 0 : reuses * extraSaving > extraInvestment);
  const B = assessed ? assessmentCost + (retain ? retentionCost - assessmentCost : 0) : 0;
  const C = invest ? extraInvestment : 0;
  const benefit = money(reuses * ((retain ? settings.reuseSaving : 0) + (invest ? extraSaving : 0)));
  return { assessed, retain, invest, B, C, benefit, reuses: money(reuses), grossBenefit,
    retentionNet, bundleNet, perReuseSaving: money((retain ? settings.reuseSaving : 0) + (invest ? extraSaving : 0)) };
}

function forecast(price, policy, settings) {
  const buyerChoices = expectedDemand(price, settings);
  const jobs = Math.min(settings.capacity, buyerChoices.enterprise);
  const allocation = policyForecast(policy, jobs, settings);
  const expectedCorrect = settings.quality + (1 - settings.quality) * 0.88 * 0.68;
  const expectedGross = expectedCorrect + (1 - settings.quality) * 0.12;
  const collections = money(jobs * price * expectedCorrect);
  const A = money(1500 + jobs * (2660 * settings.costMultiplier + (1 - settings.quality) * 0.88 * 450 * settings.costMultiplier) + jobs * price * expectedGross * 0.029);
  const profit = money(collections - A - allocation.B - allocation.C + allocation.benefit);
  const startup = money(1500 + 2660 * settings.costMultiplier + price * 0.029 + allocation.B + allocation.C);
  return { price, policy, expectedProfit: profit, expectedJobs: money(jobs), expectedCorrect: money(expectedCorrect),
    buyerChoices, allocation, feasible: startup <= settings.seedCapital - 2000 };
}

export function optimizePolicy(settings, options = {}) {
  const selected = PRESETS.find(item => item.id === (typeof settings === 'string' ? settings : settings?.id));
  if (!selected) fail('UNKNOWN_PRESET');
  const policy = options.policy ?? 'auto';
  if (![...POLICY_NAMES, 'auto'].includes(policy)) fail('INVALID_POLICY');
  const requestedPrice = options.price ?? 0;
  finite(requestedPrice, 0, 24000, 'INVALID_PRICE');
  if (requestedPrice !== 0 && (!Number.isInteger(requestedPrice) || requestedPrice < 1000)) fail('INVALID_PRICE');
  const key = `${selected.id}:${policy}:${requestedPrice}`;
  if (policyCache.has(key)) return clone(policyCache.get(key));
  const prices = requestedPrice ? [requestedPrice] : Array.from({ length: 13 }, (_, i) => 6000 + i * 1000);
  const policies = policy === 'auto' ? POLICY_NAMES : [policy];
  const search = prices.flatMap(price => policies.map(name => {
    const fixed = forecast(price, name, selected);
    const summaries = DEVELOPMENT_SEEDS.map(seed => simulatePolicy({ preset: selected.id, seed, policy: name, price }, fixed).summary);
    const profits = summaries.map(summary => summary.profit).sort((a, b) => a - b);
    return { ...fixed, approximateAnalyticMargin: fixed.expectedProfit,
      expectedProfit: money(profits.reduce((total, value) => total + value, 0) / profits.length),
      development: { count: profits.length, meanProfit: money(profits.reduce((total, value) => total + value, 0) / profits.length),
        medianProfit: money((profits[7] + profits[8]) / 2), minimumProfit: profits[0],
        lossCount: profits.filter(value => value < 0).length,
        cashShortfallCount: summaries.filter(summary => summary.cashShortfalls > 0).length,
        qualityFailureCount: summaries.filter(summary => summary.qualityFailures > 0).length },
    };
  }));
  const available = search.filter(row => row.feasible).sort((a, b) => b.expectedProfit - a.expectedProfit || POLICY_NAMES.indexOf(a.policy) - POLICY_NAMES.indexOf(b.policy) || a.price - b.price);
  const best = available[0] ?? { ...search[0], expectedProfit: 0, expectedJobs: 0, policy: 'beta', feasible: false };
  const result = { ...best, reasonKey: !best.feasible ? 'insufficient-cash' : best.expectedProfit <= 0 ? 'no-profitable-policy-in-search' : best.policy === 'beta' ? 'profitable-beta-is-valid' : best.allocation.retain ? 'reuse-benefit-exceeds-incremental-cost' : 'retain-reserves',
    searchSpace: { prices, policies, scenarioSeeds: [...DEVELOPMENT_SEEDS], scenarioCount: DEVELOPMENT_SEEDS.length,
      objective: 'Highest mean 90-day operating profit on these 16 predeclared development scenarios, using the same cash/quality ledger simulation as replay; ties prefer simpler policy. This is a finite development-scenario optimum, not expected real-world profit or an untouched confirmation result.',
      allocationRule: 'Retention and investment decisions use only the declared prospective buyer/quality assumptions; replay-seed outcomes and future quality are unavailable to the decision.' }, search };
  policyCache.set(key, clone(result));
  return result;
}

export function engineeringSample() {
  const windows = [
    { id: 'aurora', start: 0, end: 4, value: 8 }, { id: 'boreal', start: 0, end: 2, value: 5 },
    { id: 'cirrus', start: 2, end: 4, value: 5 }, { id: 'delta', start: 4, end: 7, value: 7 },
    { id: 'eclipse', start: 6, end: 8, value: 6 },
  ];
  const feasible = plan => plan.every((window, i) => !i || window.start >= plan[i - 1].end);
  let best = [], objective = 0;
  for (let mask = 0; mask < 2 ** windows.length; mask++) {
    const plan = windows.filter((_, i) => mask & (1 << i)).sort((a, b) => a.start - b.start || a.end - b.end);
    const score = plan.reduce((total, window) => total + window.value, 0);
    if (feasible(plan) && score > objective) { best = plan; objective = score; }
  }
  const baseline = [];
  for (const window of [...windows].sort((a, b) => b.value - a.value)) {
    if (feasible([...baseline, window].sort((a, b) => a.start - b.start))) baseline.push(window);
  }
  return { schema: 'flywheel.public-schedule/v1', mode: 'ACTUAL_LOCAL_FINITE_COMPUTATION',
    windows, schedule: best, objective, baseline: baseline.sort((a, b) => a.start - b.start),
    baselineObjective: baseline.reduce((total, window) => total + window.value, 0),
    checkedSubsets: 32, feasible: feasible(best), authority: [],
    limitation: 'Exact enumeration of five public synthetic windows, not frontier reasoning or deployed space operations.' };
}

function simulatePolicy(options = {}, fixedSelection = null) {
  const presetId = options.preset ?? 'baseline';
  const selectedPreset = PRESETS.find(item => item.id === presetId);
  if (!selectedPreset) fail('UNKNOWN_PRESET');
  const seed = options.seed ?? 42;
  if (!Number.isSafeInteger(seed) || seed < 0 || seed > 4294967295) fail('INVALID_SEED');
  const settings = clone(selectedPreset);
  const selected = fixedSelection ?? optimizePolicy(settings, options);
  const random = rng((seed ^ 0xa11fac7) >>> 0);
  const input = { preset: presetId, seed, policy: options.policy ?? 'auto', price: options.price ?? 0 };
  const accounts = { A: [], B: [], C: [] }, ledger = [], failures = [];
  let cash = settings.seedCapital, grossReceipts = 0, refunds = 0, accepted = 0, attempted = 0;
  let corrected = 0, refused = 0, falseAcceptances = 0, qualityFailures = 0, cashShortfalls = 0;
  let qualityReceipts = 0, candidateAssessed = false, retained = false, invested = false, supportObligations = 0, candidateOrigin = null;
  const initialReserve = 2000;
  const spend = (account, id, amount, missionId) => {
    amount = money(amount);
    if (cash - amount < initialReserve + supportObligations) return false;
    accounts[account].push({ id: `${missionId ?? 'enterprise'}:${id}`, activity: id, missionId, amount, account, cashPaid: true, evidence: 'ASSUMED' });
    cash = money(cash - amount); return true;
  };
  spend('A', 'fixed-business-overhead', 1500, null);
  const opportunities = [];
  for (let i = 0; i < 18; i++) {
    const budget = 6500 + i * 900, urgency = (i % 6) / 5;
    const preference = budget < 8000 ? 'none' : selected.price <= budget && selected.price <= 24000 * (0.55 + 0.3 * urgency) ? 'enterprise' : budget >= 21000 && urgency > 0.6 ? 'human' : 'postpone';
    const demandDraw = random(), qualityDraw = random(), checkDraw = random(), correctionDraw = random(), lateDraw = random();
    let choice = preference === 'enterprise' && demandDraw > settings.demand ? 'none' : preference;
    if (choice !== 'enterprise' || attempted >= settings.capacity || !selected.feasible) {
      opportunities.push({ id: i + 1, choice: choice === 'enterprise' ? 'capacity-or-cash-deferred' : choice }); continue;
    }
    const missionId = `modeled-job-${i + 1}`;
    const saving = (retained ? settings.reuseSaving : 0) + (invested ? (selected.policy === 'bundle' ? 700 : 400) : 0);
    const base = money(2660 * settings.costMultiplier - saving);
    const maxCorrection = money(450 * settings.costMultiplier);
    const collectionFee = money(selected.price * 0.029);
    // Delivery and its correction envelope must exist before any receipt is booked.
    const required = money(base + maxCorrection + collectionFee);
    if (cash - initialReserve - supportObligations < required) { cashShortfalls++; opportunities.push({ id: i + 1, choice: 'cash-refused' }); continue; }
    attempted++;
    const startCash = cash;
    for (const [id, amount] of deliveryItems) {
      const value = id === 'reasoning-learning-development' ? money(amount * settings.costMultiplier - saving) : money(amount * settings.costMultiplier);
      spend('A', id, value, missionId);
    }
    const initiallyCorrect = qualityDraw < settings.quality;
    const falsePass = !initiallyCorrect && checkDraw < 0.12;
    let correct = initiallyCorrect, correctedHere = false, status = 'accepted';
    if (!correct && !falsePass) {
      spend('A', 'correction-and-recheck', maxCorrection, missionId);
      correctedHere = correctionDraw < 0.68;
      correct = correctedHere;
      if (correctedHere) corrected++;
    }
    const late = lateDraw < (presetId === 'stress' ? 0.18 : 0.04);
    if (correct || falsePass) {
      grossReceipts = money(grossReceipts + selected.price); cash = money(cash + selected.price);
      spend('A', 'collection-processing', collectionFee, missionId);
      if (falsePass) {
        falseAcceptances++; qualityFailures++; status = 'false-acceptance-refunded';
        refunds = money(refunds + selected.price); cash = money(cash - selected.price);
        failures.push({ missionId, reason: 'false-pass-later-discovered', refund: selected.price });
      } else {
        accepted++; supportObligations = money(supportObligations + UNIT_ECONOMICS.supportAccrualPerAccepted);
        accounts.A.push({ id: `${missionId}:unpaid-support-accrual`, activity: 'unpaid-support-accrual', missionId,
          amount: UNIT_ECONOMICS.supportAccrualPerAccepted, account: 'A', cashPaid: false, evidence: 'ASSUMED' });
        if (!late) qualityReceipts = money(qualityReceipts + selected.price);
        else { qualityFailures++; status = 'accepted-late'; failures.push({ missionId, reason: 'late', refund: 0 }); }
      }
    } else { refused++; qualityFailures++; status = 'refused-no-collection'; failures.push({ missionId, reason: 'correction-failed', refund: 0 }); }
    let allocation = 'none';
    if (correct && !late && !candidateAssessed && selected.allocation?.assessed) {
      if (spend('B', 'candidate-assessment', assessmentCost, missionId)) {
        candidateAssessed = true; candidateOrigin = missionId; allocation = 'rejected';
        const extraB = selected.allocation.retain ? retentionCost - assessmentCost : 0;
        const extraC = selected.allocation.invest ? 3600 : 0;
        if (cash - initialReserve - supportObligations >= extraB + extraC) {
          if (selected.allocation.retain) {
            for (const [id, amount] of retentionItems) spend('B', id, amount, missionId);
            retained = true; allocation = 'retained-public-fixture';
          }
          if (selected.allocation.invest) { spend('C', 'additional-method-development', 3600, missionId); invested = true; }
        } else allocation = 'deferred-reserve-required';
      } else allocation = 'assessment-deferred-cash';
    }
    const costs = sum(Object.values(accounts).flat().filter(row => row.missionId === missionId));
    ledger.push({ missionId, startedDay: 1 + i * 5, day: 1 + i * 5 + (late ? 4 : 3),
      promisedDeliveryDays: 3, status, correct, late, corrected: correctedHere,
      price: selected.price, grossReceipt: correct || falsePass ? selected.price : 0,
      refund: falsePass ? selected.price : 0, costs, startCash, endCash: cash,
      reuseSaving: saving, allocation, authority: [] });
    opportunities.push({ id: i + 1, choice, missionId });
  }
  const costsA = sum(accounts.A), costsB = sum(accounts.B), costsC = sum(accounts.C);
  const costs = money(costsA + costsB + costsC), collections = money(grossReceipts - refunds);
  const profit = money(collections - costs), obligations = supportObligations, paidCosts = money(costs - obligations);
  const reserves = initialReserve, availableFunds = money(Math.max(0, cash - reserves - obligations));
  const expectedBenefit = selected.allocation?.grossBenefit ?? 0;
  const retention = {
    decision: retained ? 'RETAINED_SIMULATION' : candidateAssessed ? 'REJECTED_SIMULATION' : 'NOT_RETAINED',
    reasonKey: retained ? 'fresh-reuse-forecast-exceeds-incremental-cost' : candidateAssessed ? 'insufficient-incremental-value-or-cash' : 'profitable-job-needs-no-retained-skill',
    candidate: { id: 'public-window-packing-v1', status: retained ? 'ADMITTED_PUBLIC_FIXTURE' : candidateAssessed ? 'REJECTED_PUBLIC_FIXTURE' : 'CANDIDATE',
      originatingMission: candidateOrigin ?? MISSION.originatingMission, implementation: 'Constraint-aware window-packing template; public example only.',
      scope: 'Synthetic single-station, fixed-window schedules', prerequisites: ['Public synthetic input', 'Single ground station'],
      betaBaseline: presetId === 'frontier' ? 'frontier-beta/2' : 'frontier-beta/1',
      evidence: 'Modeled fresh-task direct resource savings; not an empirical protected evaluation.',
      acceptanceCriteria: 'Fresh modeled benefit exceeds only incremental retention/sharing costs; no claimed general flight qualification.',
      incrementalCosts: retentionCost, expectedReuseBenefit: expectedBenefit, validationStatus: 'SIMULATION_ONLY',
      version: '1.0.0', expiryDay: 90, revoked: false, rights: 'PUBLIC_EXAMPLE_APACHE_2.0', sharingRestrictions: 'Public teaching capsule only; no protected network capability contents.' },
    incrementalCost: costsB, expectedReuseBenefit: expectedBenefit,
    netBenefit: money(expectedBenefit - retentionCost), breakEvenReuse: settings.reuseSaving ? Math.ceil(retentionCost / settings.reuseSaving) : null,
    actualModeledReuseSaving: money(ledger.reduce((total, row) => total + row.reuseSaving, 0)),
    assessmentCost, policyVersion: 'alpha-admission-public-fixture/1',
  };
  return {
    schema: 'alpha-flywheel.simulation/v1', version: VERSION, mode: 'SIMULATION', input,
    scenarioPartition: DEVELOPMENT_SEEDS.includes(seed) ? 'DEVELOPMENT_REPLAY' : 'EXPLORATION_NOT_CONFIRMATION',
    preset: clone(selectedPreset), mission: clone(MISSION), selected,
    unitEconomics: { ...UNIT_ECONOMICS, costMultiplier: settings.costMultiplier,
      maximumPaidDeliveryEnvelope: money((UNIT_ECONOMICS.baseDelivery + UNIT_ECONOMICS.correctionEnvelope) * settings.costMultiplier + selected.price * UNIT_ECONOMICS.collectionFeeRate + UNIT_ECONOMICS.fixedBusinessOverhead),
      maximumCompleteDeliveryEnvelope: money((UNIT_ECONOMICS.baseDelivery + UNIT_ECONOMICS.correctionEnvelope) * settings.costMultiplier + selected.price * UNIT_ECONOMICS.collectionFeeRate + UNIT_ECONOMICS.fixedBusinessOverhead + UNIT_ECONOMICS.supportAccrualPerAccepted) },
    summary: { humanReference: 24000, offeredPrice: selected.price, customerSavings: money(24000 - selected.price),
      attempted, accepted, grossReceipts, refunds, collections, costs, paidCosts, costsA, costsB, costsC,
      profit, seedCapital: settings.seedCapital, cash, reserves, obligations, availableFunds,
      cashShortfalls, qualityFailures, corrected, refused, falseAcceptances,
      qualityLinkedReceipts: qualityReceipts, qualityLinkedProfit: money(qualityReceipts - costs),
      qualityLinkedRefundTreatment: 'Correct on-time receipts only minus all costs. Refunded false passes are already absent from eligible receipts; refunds are not deducted a second time.',
      ordinaryReconciliation: 'cash = seed capital + net collections - paid costs; profit = net collections - all A/B/C expenses including unpaid support; available = max(0, cash - reserves - unpaid obligations).',
    }, accounts, ledger, opportunities, failures, retention, priceSearch: selected.search,
    sample: engineeringSample(),
    models: { assumed: [
      { role: 'reasoning-strategy', label: 'Astra-powered frontier reasoning', configuration: 'Assumed stage capability; no API identifier or token price asserted.' },
      { role: 'visual-computer-use', label: 'GPT-6.1 Terra', configuration: 'Assumed suitable visual/execution stage; no runtime integration or access asserted.' },
    ], executed: [], documentation: [
      { url: 'https://developers.openai.com/api/docs/models/gpt-6-astra', checkedAt: '2026-10-26', accountAccessVerified: false },
      { url: 'https://developers.openai.com/api/docs/models/gpt-6.1-terra', checkedAt: '2026-10-26', accountAccessVerified: false },
    ], execution: 'Only deterministic JavaScript calculations and the public finite scheduling sample execute.' },
    limitations: [SOURCE.limitation, 'No real receipts, model calls, customer acceptance, ENS authorization or execution permission. All monetary values are assumed USD.',
      'The price search is optimal only within its declared finite assumed model. Real buyer responses and quality can reverse the outcome.',
      'Quality-linked sensitivity preserves all costs; late accepted work retains ordinary receipts and is excluded from quality-linked receipts.',
      'Available funds include seed capital and are not the same as earned profit. Reserves and remaining support obligations are encumbered cash.'],
  };
}

export function runSimulation(options = {}) { return simulatePolicy(options); }

export function exportSimulation(result, language = 'en') {
  if (!['en', 'fr'].includes(language) || result?.schema !== 'alpha-flywheel.simulation/v1') fail('INVALID_EXPORT');
  return JSON.stringify({ schema: 'alpha-flywheel.replay/v1', modelVersion: VERSION, language, input: result.input }, null, 2);
}

export function importSimulation(text) {
  if (typeof text !== 'string' || text.length > 4096) fail('INVALID_IMPORT');
  let parsed;
  try { parsed = JSON.parse(text); } catch { fail('INVALID_IMPORT'); }
  if (parsed?.schema !== 'alpha-flywheel.replay/v1' || parsed.modelVersion !== VERSION || !['en', 'fr'].includes(parsed.language)) fail('INCOMPATIBLE_REPLAY');
  if (!parsed.input || Object.keys(parsed.input).some(key => !['preset', 'seed', 'policy', 'price'].includes(key))) fail('INVALID_IMPORT');
  return { language: parsed.language, result: runSimulation(parsed.input) };
}

export function createPublicSkillRegistry() {
  // In-memory PUBLIC fixtures. This API is deliberately not an authorization service.
  const current = new Map(), history = [], failureMemory = [];
  let baseline = 'frontier-beta/1';
  const read = id => { const skill = current.get(id); if (!skill) fail('UNKNOWN_CANDIDATE'); return skill; };
  const save = (skill, event) => { current.set(skill.id, skill); history.push({ id: skill.id, event, status: skill.status, version: skill.version }); return clone(skill); };
  const notTerminal = skill => { if (['REVOKED', 'RETIRED', 'SUPERSEDED'].includes(skill.status)) fail('TERMINAL_SKILL'); };
  const isCurrent = (skill, day) => skill.status === 'ADMITTED' && skill.expiryDay > day && skill.betaBaseline === baseline && skill.components.every(id => isCurrent(read(id), day));
  return Object.freeze({
    create(input) {
      if (!input || !/^[a-z0-9][a-z0-9-]{1,63}$/.test(input.id) || current.has(input.id)) fail('INVALID_OR_DUPLICATE_CANDIDATE');
      if (input.rights !== 'PUBLIC_EXAMPLE_APACHE_2.0' || !input.originatingMission || !input.scope || !input.implementation) fail('PUBLIC_RIGHTS_AND_SCOPE_REQUIRED');
      const components = input.components ?? [];
      if (!Array.isArray(components) || components.length > 8 || new Set(components).size !== components.length || components.some(id => !current.has(id) || !isCurrent(read(id), 0))) fail('CURRENT_COMPONENTS_REQUIRED');
      return save({ id: input.id, components: clone(components), originatingMission: input.originatingMission, scope: input.scope,
        implementation: input.implementation, prerequisites: clone(input.prerequisites ?? []),
        rights: input.rights, status: 'CANDIDATE', policyVersion: 'alpha-admission-public-fixture/1',
        betaBaseline: baseline, version: 1, expiryDay: 90, evidence: null, assessment: null, validation: null }, 'candidate');
    },
    evidence(id, input) {
      const skill = read(id); notTerminal(skill);
      if (!['CANDIDATE', 'EVIDENCE'].includes(skill.status) || input?.kind !== 'PUBLIC_FRESH_FIXTURE' || !input.fresh || !input.criteria || !input.taskFamily) fail('FRESH_EVIDENCE_REQUIRED');
      finite(input.benefit, 0, 100000, 'INVALID_BENEFIT'); finite(input.incrementalCost, assessmentCost, 100000, 'INVALID_INCREMENTAL_COST');
      return save({ ...skill, status: 'EVIDENCE', evidence: clone(input) }, 'evidence');
    },
    assess(id) {
      const skill = read(id); notTerminal(skill);
      if (skill.status !== 'EVIDENCE') fail('EVIDENCE_REQUIRED');
      const passed = skill.evidence.benefit > skill.evidence.incrementalCost && skill.evidence.duplicate !== true;
      const assessed = { ...skill, status: passed ? 'ASSESSED' : 'REJECTED', assessment: { passed, charged: assessmentCost, net: money(skill.evidence.benefit - skill.evidence.incrementalCost) } };
      if (!passed) failureMemory.push({ id, reason: skill.evidence.duplicate ? 'duplicate' : 'insufficient-net-benefit', assessmentCost });
      return save(assessed, 'assessment');
    },
    validate(id, input) {
      const skill = read(id); notTerminal(skill);
      if (skill.status !== 'ASSESSED' || input?.freshPass !== true || input?.baseline !== baseline || !input?.independentCheck || (skill.components.length > 0 && input.compositionChecked !== true)) fail('FRESH_VALIDATION_REQUIRED');
      return save({ ...skill, status: 'VALIDATED', validation: clone(input) }, 'validation');
    },
    admit(id, day = 0) {
      const skill = read(id); notTerminal(skill); finite(day, 0, 100000, 'INVALID_DAY');
      if (skill.status !== 'VALIDATED' || !skill.assessment?.passed || skill.betaBaseline !== baseline || day >= skill.expiryDay) fail('ADMISSION_REQUIRED');
      return save({ ...skill, status: 'ADMITTED' }, 'admission');
    },
    discover({ day = 0, baseline: requestedBaseline = baseline } = {}) {
      finite(day, 0, 100000, 'INVALID_DAY');
      return [...current.values()].filter(skill => isCurrent(skill, day) && skill.betaBaseline === requestedBaseline && requestedBaseline === baseline).map(clone);
    },
    reuse(id, { day = 0, scope, baseline: requestedBaseline = baseline, fixtureEligible = false } = {}) {
      const skill = read(id); finite(day, 0, 100000, 'INVALID_DAY');
      if (fixtureEligible !== true) fail('FIXTURE_AUTHORIZATION_REQUIRED');
      if (!isCurrent(skill, day) || requestedBaseline !== baseline || skill.betaBaseline !== baseline || scope !== skill.scope) fail('CURRENT_APPLICABLE_ADMISSION_REQUIRED');
      return { skill: clone(skill), mode: 'PUBLIC_FIXTURE_REUSE', authority: [], liveIdentityQualified: false };
    },
    baselineChanged(next) {
      if (typeof next !== 'string' || !/^frontier-beta\/[1-9][0-9]{0,3}$/.test(next) || next === baseline) fail('INVALID_BASELINE');
      baseline = next;
      for (const skill of [...current.values()]) if (skill.status === 'ADMITTED') save({ ...skill, status: 'NEEDS_REVALIDATION', validation: null }, 'baseline-changed');
      return baseline;
    },
    revalidate(id, input) {
      const skill = read(id); notTerminal(skill);
      if (skill.status !== 'NEEDS_REVALIDATION' || input?.baseline !== baseline || !['retains', 'adapt', 'ordinary-beta', 'retire'].includes(input.outcome)) fail('REVALIDATION_REQUIRED');
      if (input.outcome === 'ordinary-beta' || input.outcome === 'retire') return save({ ...skill, status: 'RETIRED', retirementReason: input.outcome }, 'revalidation-retirement');
      finite(input.benefit, 0, 100000, 'INVALID_BENEFIT'); finite(input.incrementalCost, assessmentCost, 100000, 'INVALID_INCREMENTAL_COST');
      finite(input.day ?? 0, 0, 100000, 'INVALID_DAY');
      if (input.freshPass !== true || !(input.benefit > input.incrementalCost) || !input.independentCheck ||
          (skill.components.length > 0 && (input.compositionChecked !== true || skill.components.some(id => !isCurrent(read(id), input.day ?? 0))))) fail('FRESH_NET_ADVANTAGE_REQUIRED');
      return save({ ...skill, status: 'ADMITTED', betaBaseline: baseline, version: skill.version + 1, validation: clone(input) }, 'revalidation');
    },
    revoke(id) { const skill = read(id); notTerminal(skill); return save({ ...skill, status: 'REVOKED' }, 'revocation'); },
    retire(id) { const skill = read(id); notTerminal(skill); return save({ ...skill, status: 'RETIRED' }, 'retirement'); },
    supersede(id, replacementId) {
      const skill = read(id), replacement = read(replacementId); notTerminal(skill);
      if (replacement.status !== 'ADMITTED' || replacementId === id) fail('ADMITTED_REPLACEMENT_REQUIRED');
      return save({ ...skill, status: 'SUPERSEDED', replacementId }, 'supersession');
    },
    inspect(id) { return clone(read(id)); },
    history() { return clone(history); }, failures() { return clone(failureMemory); },
    qualification() { return { mode: 'PUBLIC_FIXTURE_ONLY', liveIdentityQualified: false, protectedContents: false, authority: [] }; },
  });
}
