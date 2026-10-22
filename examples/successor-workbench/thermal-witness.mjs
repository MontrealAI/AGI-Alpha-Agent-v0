// SPDX-License-Identifier: Apache-2.0
export const THERMAL_SCHEMA = 'thermal-witness/v1';
export const INHERITED_FOUNDRY_FAILURE = Object.freeze({
  status: 'RETAINED_UNDETECTED_FAILURE',
  release: 'study-foundry-v2-2026-10-22-r1',
  predictedHeatJ: '5175.8646948056885',
  commandFlowCalorimeterHeatJ: '5445.281559253128',
  independentReferenceHeatJ: '5009.6244576737745',
  runtimeRelativeResidual: '0.049477122810963045',
  trueRelativeHeatError: '0.08696402400224054',
  scope: 'Historical simulated result; a new witness run does not rewrite or qualify it.',
});

function fields(value, keys, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('SCHEMA: ' + label);
  const proto = Object.getPrototypeOf(value);
  if (proto !== Object.prototype && proto !== null) throw Error('SCHEMA: ' + label);
  const actual = Reflect.ownKeys(value);
  if (actual.length !== keys.length || actual.some(key => typeof key !== 'string')) throw Error('SCHEMA: ' + label);
  actual.sort();
  const expected = [...keys].sort();
  if (actual.some((key, index) => key !== expected[index])) throw Error('SCHEMA: ' + label);
  for (const key of actual) {
    const d = Object.getOwnPropertyDescriptor(value, key);
    if (!d.enumerable || !Object.hasOwn(d, 'value')) throw Error('DATA_REQUIRED: ' + label);
  }
}
function integer(value, low, high, label) {
  if (!Number.isSafeInteger(value) || Object.is(value, -0) || value < low || value > high) {
    throw Error('BOUNDS: ' + label);
  }
}
function text(value, label) {
  if (typeof value !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9:._-]{0,95}$/.test(value)) {
    throw Error('IDENTITY: ' + label);
  }
}
function decimal(value, label) {
  if (typeof value !== 'string' || !/^(0|[1-9][0-9]{0,23})$/.test(value)) throw Error('DECIMAL: ' + label);
  return BigInt(value);
}
function band(value, maximum, label) {
  fields(value, ['low', 'estimate', 'high'], label);
  integer(value.low, 0, maximum, label);
  integer(value.estimate, value.low, maximum, label);
  integer(value.high, value.estimate, maximum, label);
}
function energyBand(value, label) {
  fields(value, ['low', 'estimate', 'high'], label);
  const a = decimal(value.low, label), b = decimal(value.estimate, label), c = decimal(value.high, label);
  if (a > b || b > c) throw Error('ORDER: ' + label);
}
function witness(value, kinds, label) {
  fields(value, ['sourceId', 'kind'], label);
  text(value.sourceId, label);
  if (!kinds.includes(value.kind)) throw Error('WITNESS: ' + label);
}
export function validateThermalInput(input) {
  fields(input, ['schema', 'family', 'measurement', 'policy', 'extension', 'maxWorkUnits'], 'thermal input');
  if (input.schema !== THERMAL_SCHEMA ||
      !['delivered-heat', 'heat-capacity', 'heat-recovery'].includes(input.family)) throw Error('UNSUPPORTED_THERMAL_SCHEMA');
  integer(input.maxWorkUnits, 1, 960, 'work units');
  fields(input.policy, ['maxRelativeErrorPpm', 'minimumHeatMicroJ'], 'fixed policy');
  integer(input.policy.maxRelativeErrorPpm, 1, 50000, 'accuracy policy, at most 5 percent');
  decimal(input.policy.minimumHeatMicroJ, 'minimum heat');
  const m = input.measurement;
  fields(m, ['mode', 'coverage', 'propertyModel', 'commandSourceId', 'volumeWitness', 'temperatureWitness',
    'densityKgPerM3', 'specificHeatJPerKgK', 'windowMs', 'intervals'], 'measurement');
  if (m.mode !== 'SIMULATED_MEASUREMENTS' ||
      !['WHOLE_FLOW_DECLARED_BOUNDS', 'UNKNOWN'].includes(m.coverage) ||
      !['CONSTANT_WITHIN_INTERVAL', 'VARIABLE_OR_UNKNOWN'].includes(m.propertyModel)) throw Error('MEASUREMENT_MODE');
  text(m.commandSourceId, 'command source');
  witness(m.volumeWitness, ['INDEPENDENT_SIMULATED', 'COMMAND_DERIVED', 'ABSENT'], 'volume witness');
  witness(m.temperatureWitness, ['BOUNDED_SIMULATED', 'UNBOUNDED'], 'temperature witness');
  band(m.densityKgPerM3, 5000, 'density');
  band(m.specificHeatJPerKgK, 20000, 'specific heat');
  if (m.densityKgPerM3.low === 0 || m.specificHeatJPerKgK.low === 0) throw Error('POSITIVE_MATERIAL_PROPERTIES');
  integer(m.windowMs, 1, 3600000, 'window');
  if (!Array.isArray(m.intervals) || m.intervals.length < 1 || m.intervals.length > 960 ||
      Reflect.ownKeys(m.intervals).length !== m.intervals.length + 1) throw Error('INTERVAL_COUNT');
  let next = 0;
  for (let i = 0; i < m.intervals.length; i++) {
    const d = Object.getOwnPropertyDescriptor(m.intervals, String(i));
    if (!d || !Object.hasOwn(d, 'value')) throw Error('INTERVAL_DATA_REQUIRED');
    const v = d.value;
    fields(v, ['sequence', 'startMs', 'durationMs', 'commandFlowNLPerMin', 'volumeNL',
      'volumeUncertaintyNL', 'deltaTemperatureUK', 'deltaTemperatureUncertaintyUK'], 'interval');
    integer(v.sequence, i, i, 'sequence');
    integer(v.startMs, next, next, 'contiguous coverage');
    integer(v.durationMs, 1, 60000, 'duration');
    integer(v.commandFlowNLPerMin, 0, 200000000, 'command flow');
    integer(v.volumeNL, 0, 1000000000, 'volume');
    integer(v.volumeUncertaintyNL, 0, v.volumeNL, 'volume uncertainty');
    integer(v.deltaTemperatureUK, -30000000, 30000000, 'differential temperature');
    integer(v.deltaTemperatureUncertaintyUK, 0, 5000000, 'temperature uncertainty');
    next += v.durationMs;
  }
  if (next !== m.windowMs) throw Error('INCOMPLETE_WINDOW');
  const e = input.extension;
  if (input.family === 'delivered-heat') fields(e, [], 'heat extension');
  else {
    fields(e, input.family === 'heat-capacity'
      ? ['sourceId', 'kind', 'temperatureRiseUK', 'lossEnergyMicroJ', 'containerEnergyMicroJ']
      : ['sourceId', 'kind', 'inputEnergyMicroJ', 'storageReleaseMicroJ', 'minimumRecoveryPpm'], 'extension');
    text(e.sourceId, 'extension source');
    if (!['INDEPENDENT_SIMULATED', 'COMMAND_DERIVED', 'ABSENT'].includes(e.kind)) throw Error('EXTENSION_WITNESS');
    if (input.family === 'heat-capacity') {
      band(e.temperatureRiseUK, 100000000, 'sample temperature rise');
      energyBand(e.lossEnergyMicroJ, 'loss energy');
      energyBand(e.containerEnergyMicroJ, 'container energy');
    } else {
      energyBand(e.inputEnergyMicroJ, 'input energy');
      energyBand(e.storageReleaseMicroJ, 'storage release');
      integer(e.minimumRecoveryPpm, 0, 1000000, 'minimum recovery');
    }
  }
  return input;
}
function floor(n, d) { const q = n / d; return n < 0n && n % d !== 0n ? q - 1n : q; }
function ceil(n, d) { return -floor(-n, d); }
function round(n, d) { return n < 0n ? -round(-n, d) : (2n * n + d) / (2n * d); }
function abs(n) { return n < 0n ? -n : n; }
function min(values) { return values.reduce((a, b) => a < b ? a : b); }
function max(values) { return values.reduce((a, b) => a > b ? a : b); }
function rational(n, d) {
  if (d <= 0n) throw Error('NONPOSITIVE_DENOMINATOR');
  let a = abs(n), b = d;
  while (b) { const c = a % b; a = b; b = c; }
  return String(n / (a || 1n)) + '/' + String(d / (a || 1n));
}
function quality(estimate, low, high) {
  const radius = max([abs(estimate - low), abs(high - estimate)]);
  const denominator = low > 0n ? low : high < 0n ? -high : 0n;
  return { radiusMicroJ: String(radius), worstRelativeErrorPpm: denominator === 0n
    ? null : String(ceil(radius * 1000000n, denominator)) };
}
function ratioQuality(lowN, lowD, estimateN, estimateD, highN, highD) {
  if (lowN <= 0n || lowD <= 0n || estimateD <= 0n || highD <= 0n) return null;
  const lowerDeviation = ceil(abs(estimateN * lowD - lowN * estimateD) * 1000000n,
    estimateD * lowN);
  const upperDeviation = ceil(abs(highN * estimateD - estimateN * highD) * lowD * 1000000n,
    highD * estimateD * lowN);
  return String(max([lowerDeviation, upperDeviation]));
}
function ratioBounds(lowN, estimateN, highN, lowD, estimateD, highD) {
  const estimate = estimateD > 0n ? rational(estimateN, estimateD) : null;
  if (lowD <= 0n) return { low: null, estimate, high: null, worstRelativeErrorPpm: null,
    ratioDomain: 'DENOMINATOR_INCLUDES_ZERO' };
  const corners = [[lowN, lowD], [lowN, highD], [highN, lowD], [highN, highD]];
  const compare = (a, b) => a[0] * b[1] - b[0] * a[1];
  const lower = corners.reduce((a, b) => compare(a, b) <= 0n ? a : b);
  const upper = corners.reduce((a, b) => compare(a, b) >= 0n ? a : b);
  return { low: rational(...lower), estimate, high: rational(...upper),
    worstRelativeErrorPpm: ratioQuality(lower[0], lower[1], estimateN, estimateD, upper[0], upper[1]),
    ratioDomain: 'POSITIVE_DENOMINATOR' };
}
function strings(low, estimate, high) {
  return { low: String(low), estimate: String(estimate), high: String(high) };
}
function jsonArtifact(name, value) {
  return { name, type: 'application/json', content: JSON.stringify(value, null, 2) + '\n' };
}
export async function executeThermal(supplied, checkpoint) {
  validateThermalInput(supplied);
  const input = JSON.parse(JSON.stringify(supplied));
  validateThermalInput(input);
  if (typeof checkpoint !== 'function') throw Error('CHECKPOINT_REQUIRED');
  const m = input.measurement, rho = m.densityKgPerM3, cp = m.specificHeatJPerKgK;
  let lowNumerator = 0n, estimateNumerator = 0n, highNumerator = 0n, commandNumerator = 0n, work = 0;
  const scale = 1000000000000n;
  for (const v of m.intervals) {
    if (work === input.maxWorkUnits) break;
    await checkpoint('thermal-interval');
    const volumes = [BigInt(v.volumeNL - v.volumeUncertaintyNL), BigInt(v.volumeNL + v.volumeUncertaintyNL)];
    const temperatures = [BigInt(v.deltaTemperatureUK - v.deltaTemperatureUncertaintyUK),
      BigInt(v.deltaTemperatureUK + v.deltaTemperatureUncertaintyUK)];
    const products = [];
    for (const r of [rho.low, rho.high]) for (const c of [cp.low, cp.high]) {
      for (const volume of volumes) for (const temperature of temperatures) {
        products.push(BigInt(r) * BigInt(c) * volume * temperature);
      }
    }
    lowNumerator += min(products); highNumerator += max(products);
    estimateNumerator += BigInt(rho.estimate) * BigInt(cp.estimate) * BigInt(v.volumeNL) * BigInt(v.deltaTemperatureUK);
    commandNumerator += BigInt(rho.estimate) * BigInt(cp.estimate) * BigInt(v.commandFlowNLPerMin)
      * BigInt(v.durationMs) * BigInt(v.deltaTemperatureUK);
    work++;
  }
  const complete = work === m.intervals.length;
  const low = floor(lowNumerator, scale), high = ceil(highNumerator, scale), estimate = round(estimateNumerator, scale);
  const commandEstimate = round(commandNumerator, scale * 60000n);
  const uncertainty = quality(estimate, low, high);
  const observable = m.coverage === 'WHOLE_FLOW_DECLARED_BOUNDS' &&
    m.propertyModel === 'CONSTANT_WITHIN_INTERVAL' &&
    m.volumeWitness.kind === 'INDEPENDENT_SIMULATED' && m.temperatureWitness.kind === 'BOUNDED_SIMULATED' &&
    new Set([m.commandSourceId, m.volumeWitness.sourceId, m.temperatureWitness.sourceId]).size === 3;
  const accurate = uncertainty.worstRelativeErrorPpm !== null &&
    BigInt(uncertainty.worstRelativeErrorPpm) <= BigInt(input.policy.maxRelativeErrorPpm);
  let decision = !complete ? 'WORK_BUDGET_EXHAUSTED' : !observable ? 'OBSERVABILITY_NOT_ESTABLISHED'
    : low <= 0n ? 'POSITIVE_HEAT_NOT_IDENTIFIABLE' : !accurate ? 'UNCERTAINTY_EXCEEDS_POLICY'
      : low < BigInt(input.policy.minimumHeatMicroJ) ? 'HEAT_TARGET_NOT_MET' : 'CONDITIONAL_BOUNDS_MET';
  const quantity = { name: 'delivered heat', unit: 'microjoules', ...strings(low, estimate, high) };
  let downstream = null;
  if (complete && input.family !== 'delivered-heat') {
    const e = input.extension;
    const independent = e.kind === 'INDEPENDENT_SIMULATED' &&
      ![m.commandSourceId, m.volumeWitness.sourceId, m.temperatureWitness.sourceId].includes(e.sourceId);
    if (input.family === 'heat-capacity') {
      const losses = e.lossEnergyMicroJ, container = e.containerEnergyMicroJ, rise = e.temperatureRiseUK;
      const netLow = low - BigInt(losses.high) - BigInt(container.high);
      const netHigh = high - BigInt(losses.low) - BigInt(container.low);
      const netEstimate = estimate - BigInt(losses.estimate) - BigInt(container.estimate);
      downstream = { name: 'single-sample heat capacity', unit: 'joules per kelvin',
        netEnergyMicroJ: strings(netLow, netEstimate, netHigh), temperatureRiseUK: rise,
        ...ratioBounds(netLow, netEstimate, netHigh, BigInt(rise.low), BigInt(rise.estimate), BigInt(rise.high)),
        assumption: 'All residual measured heat enters one sample; losses and container storage are independently bounded.' };
      if (decision === 'CONDITIONAL_BOUNDS_MET') {
        if (!independent) decision = 'ADDITIONAL_INDEPENDENT_WITNESS_REQUIRED';
        else if (rise.low === 0) decision = 'HEAT_CAPACITY_NOT_IDENTIFIABLE';
        else if (netHigh <= 0n) decision = 'ENERGY_BOUNDARY_INCONSISTENT';
        else if (netLow <= 0n) decision = 'ENERGY_BOUNDARY_NOT_RESOLVED';
        else if (downstream.worstRelativeErrorPpm === null ||
          BigInt(downstream.worstRelativeErrorPpm) > BigInt(input.policy.maxRelativeErrorPpm)) {
          decision = 'DOWNSTREAM_UNCERTAINTY_EXCEEDS_POLICY';
        }
      }
    } else {
      const energy = e.inputEnergyMicroJ, storage = e.storageReleaseMicroJ;
      const netLow = low - BigInt(storage.high), netHigh = high - BigInt(storage.low);
      const netEstimate = estimate - BigInt(storage.estimate);
      const denominatorLow = BigInt(energy.low), denominatorHigh = BigInt(energy.high);
      downstream = { name: 'storage-adjusted heat recovery', unit: 'dimensionless',
        netHeatMicroJ: strings(netLow, netEstimate, netHigh),
        inputEnergyMicroJ: energy, minimumRecoveryPpm: e.minimumRecoveryPpm,
        ...ratioBounds(netLow, netEstimate, netHigh, denominatorLow, BigInt(energy.estimate), denominatorHigh),
        assumption: 'The independent input bound covers every energy input; stored-energy release is separately bounded.' };
      if (decision === 'CONDITIONAL_BOUNDS_MET') {
        if (!independent) decision = 'ADDITIONAL_INDEPENDENT_WITNESS_REQUIRED';
        else if (denominatorLow === 0n) decision = 'RECOVERY_RATIO_NOT_IDENTIFIABLE';
        else if (netHigh < 0n || netLow > denominatorHigh) decision = 'ENERGY_BOUNDARY_INCONSISTENT';
        else if (netLow < 0n || netHigh > denominatorLow) decision = 'ENERGY_BOUNDARY_NOT_RESOLVED';
        else if (downstream.worstRelativeErrorPpm === null ||
          BigInt(downstream.worstRelativeErrorPpm) > BigInt(input.policy.maxRelativeErrorPpm)) {
          decision = 'DOWNSTREAM_UNCERTAINTY_EXCEEDS_POLICY';
        } else if (netLow * 1000000n < BigInt(e.minimumRecoveryPpm) * denominatorHigh) decision = 'RECOVERY_TARGET_NOT_MET';
      }
    }
  }
  await checkpoint('thermal-evidence');
  const evidence = {
    schema: THERMAL_SCHEMA, family: input.family, completion: complete ? 'COMPLETE' : 'EXHAUSTED',
    intervalsProcessed: work, intervalsDeclared: m.intervals.length,
    workUnits: work, workUnitDefinition: 'One bounded interval reduction; validation and fixed final arithmetic are outside this counter.',
    coverageMs: m.intervals.slice(0, work).reduce((sum, v) => sum + v.durationMs, 0),
    simulation: true, physicalValidity: 'NOT_ESTABLISHED', independentReview: false,
    witnessIndependence: 'Declared synthetic channel separation, not authenticated metrological or organizational independence.',
    propertyModel: m.propertyModel,
    acquisitionAssumption: 'Density and specific heat are constant within each interval. The temperature bound covers its volume-weighted mean differential; property-temperature covariance is not modeled.',
    observable, quantity, uncertainty, downstream,
    commandOnlyBaseline: { heatMicroJ: String(commandEstimate), errorVsWitnessEstimateMicroJ: String(commandEstimate - estimate),
      canBoundHiddenFlowError: false },
    inheritedFailure: INHERITED_FOUNDRY_FAILURE,
    calculation: 'rho[kg/m3] * cp[J/kg/K] * volume[nL] * deltaT[microK] / 10^12 = microjoules; interval extrema rounded outwards.',
  };
  const proposal = {
    schema: 'thermal-capability-proposal/v1', family: input.family, decision,
    boundedArithmeticAccepted: decision === 'CONDITIONAL_BOUNDS_MET',
    acceptedCapability: false, authority: [], settlement: 'NOT_CONNECTED',
    requires: ['Independent result acceptance', 'Authenticated witness acquisition', 'Actual harness execution and recovery receipt'],
  };
  return { decision, summary: { family: input.family, completion: evidence.completion, intervalsProcessed: work,
    acceptedCapability: false, physicalValidity: 'NOT_ESTABLISHED' }, evidence,
    artifacts: [jsonArtifact('thermal-bounds.json', evidence), jsonArtifact('thermal-capability-proposal.json', proposal)],
    limits: [
      'Executed fixed calorimetry arithmetic over simulated measurement inputs; no physical instrument is controlled.',
      'Bounds assume complete participating-flow coverage, fixed properties within each interval and honest calibration limits. Unmodeled property-temperature covariance or omitted errors can invalidate them.',
      'A command-derived volume cannot observe actuator bias. Different source labels alone do not prove independence.',
      'The historical Foundry failure remains retained; this new computation is not a rerun of the original full study.',
      'A source or packaged-worker result alone does not establish SUCCESSOR harness recovery, independent Fleet acceptance or contract settlement.',
    ] };
}
export const thermalWitnessAdapter = Object.freeze({
  manifest: Object.freeze({
    id: 'thermal-witness', version: 1,
    en: 'Construct a witnessed thermal measurement', fr: 'Construire une mesure thermique avec référence',
    scope: 'Bounded simulated whole-flow calorimetry and conditional downstream quantities; no physical or financial authority.',
    artifact: 'thermal-bounds.json',
  }),
  validate: validateThermalInput, execute: executeThermal,
});
export function thermalExample(family = 'delivered-heat') {
  const bandOf = n => ({ low: n, estimate: n, high: n });
  const energy = n => bandOf(String(n));
  const extension = family === 'delivered-heat' ? {} : family === 'heat-capacity'
    ? { sourceId: 'sample-reference', kind: 'INDEPENDENT_SIMULATED', temperatureRiseUK: bandOf(10000000),
      lossEnergyMicroJ: energy(800000000), containerEnergyMicroJ: energy(200000000) }
    : { sourceId: 'energy-reference', kind: 'INDEPENDENT_SIMULATED', inputEnergyMicroJ: energy(5000000000),
      storageReleaseMicroJ: energy(200000000), minimumRecoveryPpm: 600000 };
  const input = {
    schema: THERMAL_SCHEMA, family,
    measurement: {
      mode: 'SIMULATED_MEASUREMENTS', coverage: 'WHOLE_FLOW_DECLARED_BOUNDS',
      propertyModel: 'CONSTANT_WITHIN_INTERVAL', commandSourceId: 'controller-telemetry',
      volumeWitness: { sourceId: 'independent-volume', kind: 'INDEPENDENT_SIMULATED' },
      temperatureWitness: { sourceId: 'differential-reference', kind: 'BOUNDED_SIMULATED' },
      densityKgPerM3: bandOf(1000), specificHeatJPerKgK: bandOf(4000), windowMs: 60000,
      intervals: [{ sequence: 0, startMs: 0, durationMs: 60000, commandFlowNLPerMin: 100000000,
        volumeNL: 92000000, volumeUncertaintyNL: 0, deltaTemperatureUK: 10000000, deltaTemperatureUncertaintyUK: 0 }],
    },
    policy: { maxRelativeErrorPpm: 50000, minimumHeatMicroJ: '1000000' }, extension, maxWorkUnits: 960,
  };
  validateThermalInput(input);
  return input;
}
