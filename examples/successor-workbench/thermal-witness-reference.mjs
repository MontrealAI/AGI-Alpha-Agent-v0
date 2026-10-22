// SPDX-License-Identifier: Apache-2.0
// Independent evaluator and simulated acquisition fixture; never an oracle input to the worker.
// Source: study-foundry-v2-2026-10-22-r1, thermal-mismatch-calorimetry retained case.
const RHO = 998, CP = 4180, DT = 1 / 32, CALIBRATION_K = 0.005, CURVATURE_K_S2 = 32;
const TRUE_PARAMETERS = [9.285413423151033, 6.50436699223976, 213.21484295526542, 0.21639317592913168];
const FROZEN_PARAMETERS = [9.287682987903008, 6.50569574461775, 213.18475571276835, 0.21448608367764566];
const SCHEDULE = [
  { duration_s: 120, heater_W: 0, q1_L_min: 0.12, q2_L_min: 0.1, inlet1_C: 20, inlet2_C: 20 },
  { duration_s: 120, heater_W: 42, q1_L_min: 0.12, q2_L_min: 0.1, inlet1_C: 20, inlet2_C: 20 },
  { duration_s: 180, heater_W: 0, q1_L_min: 0.12, q2_L_min: 0.1, inlet1_C: 20, inlet2_C: 20 },
  { duration_s: 120, heater_W: 64, q1_L_min: 0.18, q2_L_min: 0.15, inlet1_C: 20, inlet2_C: 20 },
  { duration_s: 180, heater_W: 0, q1_L_min: 0.18, q2_L_min: 0.15, inlet1_C: 20, inlet2_C: 20 },
];
function referenceRhs(y, u, p, m, reset) {
  const a = y[0], b = y[1], w = y[2], memory = y[3];
  const q1 = u.q1_L_min * m[0], q2 = u.q2_L_min * m[1], f1 = q1 / 60000, f2 = q2 / 60000;
  const k1 = p[0] * Math.pow(q1 / 0.1, 0.7), k2 = p[1] * Math.pow(q2 / 0.1, 0.7);
  const pressure = (t, q) => 2.6e9 * Math.exp(-0.022 * (t - 20)) * q + 4e13 * q * Math.abs(q);
  const x1 = k1 * (w - a), x2 = k2 * (w - b), xh = p[3] * (w - memory);
  return [
    (RHO * CP * f1 * (u.inlet1_C - a) + x1 + pressure(a, f1) * f1) / 40,
    (RHO * CP * f2 * (u.inlet2_C - b) + x2 + pressure(b, f2) * f2) / 40,
    (u.heater_W * m[2] - x1 - x2 - 0.18 * (w - 20) - xh - (reset ? 12 * (w - 20) : 0)) / p[2],
    (xh - (reset ? 8 * (memory - 20) : 0)) / 80,
    RHO * CP * f2 * (b - u.inlet2_C),
  ];
}
function referenceStep(y, u, p, m, reset) {
  const a = referenceRhs(y, u, p, m, reset);
  const b = referenceRhs(y.map((x, i) => x + DT * a[i] / 2), u, p, m, reset);
  const c = referenceRhs(y.map((x, i) => x + DT * b[i] / 2), u, p, m, reset);
  const d = referenceRhs(y.map((x, i) => x + DT * c[i]), u, p, m, reset);
  return y.map((x, i) => x + DT * (a[i] + 2 * b[i] + 2 * c[i] + d[i]) / 6);
}
function declaredCurvatureBound() {
  const q = 0.2 / 60000, a = RHO * CP * q, k1 = 14 * Math.pow(2, 0.7), k2 = 11 * Math.pow(2, 0.7);
  const r = 2.6e9 * Math.exp(0.11), pump = (r * q + 4e13 * q * q) * q;
  const receiverSlope = ((a + k2) * 30 + pump) / 40;
  const wallSlope = (80 + (k1 + k2) * 30 + 0.18 * 25 + 0.55 * 30) / 140;
  return (a + k2 + 0.022 * r * q * q) / 40 * receiverSlope + k2 / 40 * wallSlope;
}
function referenceFixture({
  scenario = 'flow-power-uncertainty', initialHistoryK = 10, volumeMeterBias = 0.003, differentialBiasK = 0.002,
} = {}) {
  const variants = { nominal: [1, 1, 1], 'flow-power-uncertainty': [1.08, 0.92, 1.05] };
  const m = variants[scenario];
  if (!m || !Number.isFinite(initialHistoryK) || Math.abs(initialHistoryK) > 10) throw Error('REFERENCE_CASE');
  if (!Number.isFinite(volumeMeterBias) || Math.abs(volumeMeterBias) > 0.005 ||
      !Number.isFinite(differentialBiasK) || Math.abs(differentialBiasK) > CALIBRATION_K) {
    throw Error('REFERENCE_CHANNEL_SCOPE');
  }
  if (declaredCurvatureBound() > CURVATURE_K_S2) throw Error('CURVATURE_CERTIFICATE');
  const p = TRUE_PARAMETERS.slice();
  const reset = { q1_L_min: 0.15, q2_L_min: 0.15, inlet1_C: 20, inlet2_C: 20, heater_W: 0 };
  let y = [20, 20, 20, 20 + initialHistoryK, 0], steps = 0;
  for (let k = 0; k < 180 / DT; k++) { y = referenceStep(y, reset, p, m, true); steps++; }
  const resetState = y.slice(0, 4); y[4] = 0;
  const intervals = [], sampledTemperatures = [], volumeOracle = [];
  const deltaUncertaintyMicroK = Math.ceil(1e6 * (CALIBRATION_K + CURVATURE_K_S2 * DT * DT / 12)) + 1;
  let elapsed = 0, legacyCommandHeatJ = 0, lastLegacyTemperature = y[1];
  for (const u of SCHEDULE) {
    const actualFlow = u.q2_L_min * m[1], trueVolumeNl = actualFlow / 60 * 1e9;
    for (let second = 1; second <= u.duration_s; second++) {
      let sampledDeltaIntegral = 0;
      for (let k = 0; k < 1 / DT; k++) {
        const previous = y, next = referenceStep(y, u, p, m, false);
        sampledDeltaIntegral += DT * ((previous[1] - u.inlet2_C) + (next[1] - u.inlet2_C)) / 2;
        y = next; steps++;
        if (y.slice(0, 4).some(t => t < 15 || t > 45)) throw Error('REFERENCE_STATE_ENVELOPE');
      }
      const witnessedVolume = Math.round(trueVolumeNl * (1 + volumeMeterBias));
      const observation = {
        durationMs: 1000,
        commandedFlowNanoLitresPerMinute: Math.round(u.q2_L_min * 1e9),
        witnessedVolumeNanoLitres: witnessedVolume,
        volumeUncertaintyNanoLitres: Math.ceil(witnessedVolume * 0.01) + 1,
        deltaTemperatureMicroK: Math.round(1e6 * (sampledDeltaIntegral + differentialBiasK)),
        deltaTemperatureUncertaintyMicroK: deltaUncertaintyMicroK,
      };
      if (Object.values(observation).some(x => !Number.isSafeInteger(x))) throw Error('UNSAFE_FIXTURE_INTEGER');
      intervals.push(observation);
      sampledTemperatures.push({ time_s: elapsed + second, outlet2_C: y[1], inlet2_C: u.inlet2_C });
      volumeOracle.push(trueVolumeNl);
      if (second % 10 === 0) {
        legacyCommandHeatJ += RHO * CP * u.q2_L_min / 60000 * 10 * (lastLegacyTemperature + y[1] - 2 * u.inlet2_C) / 2;
        lastLegacyTemperature = y[1];
      }
    }
    elapsed += u.duration_s;
  }
  if (intervals.length > 960) throw Error('INTERVAL_LIMIT');
  const measuredQ = intervals.reduce((s, x) =>
    s + RHO * CP * x.witnessedVolumeNanoLitres * x.deltaTemperatureMicroK / 1e18, 0);
  return {
    observations: { densityKgPerM3: RHO, cpJPerKgK: CP, intervals },
    audit: {
      scenario, multipliers: m, parameters: p, resetState, finalState: y.slice(0, 4), trueSecondaryHeatJ: y[4],
      legacyCommandHeatJ, witnessPointHeatJ: measuredQ,
      witnessPointRelativeError: Math.abs(measuredQ - y[4]) / Math.abs(y[4]),
      oldRelativeError: Math.abs(legacyCommandHeatJ - y[4]) / Math.abs(y[4]),
      maxDeclaredSecondDerivativeBound: declaredCurvatureBound(), deltaUncertaintyMicroK,
      steps, rhsCalls: steps * 4, simulatedResetSeconds: 180, simulatedMissionSeconds: 720,
      volumeOracleNanoLitres: volumeOracle, sampledTemperatures,
    },
    assumptions: {
      physics: 'Simulated declared four-state model; no physical certification.',
      densityAndHeatCapacity: 'Fixed synthetic constants without uncertainty.',
      observation: 'Mean differential temperature from sampled temperatures, never from oracle heat; separate simulated volume channel.',
      calibration: '1% volume uncertainty; +/-0.005 K differential calibration; quantization covered upward.',
      temporalBound: 'Composite-trapezoid mean error <= M*dt^2/12, M=32 K/s^2 within the declared parameter/state/control box.',
      channelIndependence: 'Modeled separate volume channel; common-cause corruption is not ruled out.',
      runtimeSeparation: 'Send observations only to the worker; audit and hidden multipliers never enter its input.',
    },
  };
}
export { referenceFixture, declaredCurvatureBound, SCHEDULE, TRUE_PARAMETERS, FROZEN_PARAMETERS };
