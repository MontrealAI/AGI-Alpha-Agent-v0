// SPDX-License-Identifier: Apache-2.0
// Development acquisition/evaluator only. The worker imports neither this file nor the reference.
import { thermalExample } from './thermal-witness.mjs';
import { referenceFixture } from './thermal-witness-reference.mjs';

export function foundryWitnessFixture(options = {}) {
  const { observations, audit, assumptions } = referenceFixture(options);
  const input = thermalExample('delivered-heat');
  const exact = value => ({ low: value, estimate: value, high: value });
  input.measurement.densityKgPerM3 = exact(observations.densityKgPerM3);
  input.measurement.specificHeatJPerKgK = exact(observations.cpJPerKgK);
  input.measurement.windowMs = 720000;
  input.measurement.intervals = observations.intervals.map((v, sequence) => ({
    sequence, startMs: sequence * 1000, durationMs: v.durationMs,
    commandFlowNLPerMin: v.commandedFlowNanoLitresPerMinute,
    volumeNL: v.witnessedVolumeNanoLitres, volumeUncertaintyNL: v.volumeUncertaintyNanoLitres,
    deltaTemperatureUK: v.deltaTemperatureMicroK, deltaTemperatureUncertaintyUK: v.deltaTemperatureUncertaintyMicroK,
  }));
  return { input, audit, assumptions };
}
