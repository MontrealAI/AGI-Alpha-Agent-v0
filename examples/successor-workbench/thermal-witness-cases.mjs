// SPDX-License-Identifier: Apache-2.0
// Portable numerical/boundary checks; the Node wrapper separately exercises the actual workbench.
export async function runThermalCases({ thermalExample, executeThermal, validateThermalInput, foundryWitnessFixture }) {
  const passed = [];
  const equal = (actual, expected, name) => {
    if (actual !== expected) throw Error(name + ': ' + String(actual) + ' != ' + String(expected));
  };
  const check = (value, name) => { if (!value) throw Error(name); };
  const reject = (fn, name) => {
    let failed = false; try { fn(); } catch { failed = true; }
    check(failed, name);
  };
  const run = input => executeThermal(input, async () => {});
  const record = async (name, fn) => { await fn(); passed.push(name); };
  await record('constant measured volume defeats command gain error with exact units', async () => {
    const r = await run(thermalExample());
    equal(r.evidence.quantity.estimate, '3680000000', 'independent hand calculation');
    equal(r.evidence.commandOnlyBaseline.heatMicroJ, '4000000000', 'command baseline');
    equal(r.evidence.quantity.low, r.evidence.quantity.high, 'exact fixture');
    equal(r.decision, 'CONDITIONAL_BOUNDS_MET', 'conditional arithmetic');
    equal(r.summary.acceptedCapability, false, 'no acceptance by worker');
  });
  await record('hidden truth is not an input field', () => {
    const x = thermalExample(); x.truth = 3680; reject(() => validateThermalInput(x), 'truth input');
  });
  await record('missing independent volume does not qualify', async () => {
    const x = thermalExample(); x.measurement.volumeWitness.kind = 'ABSENT';
    equal((await run(x)).decision, 'OBSERVABILITY_NOT_ESTABLISHED', 'missing volume');
  });
  await record('command-derived volume does not qualify', async () => {
    const x = thermalExample(); x.measurement.volumeWitness.kind = 'COMMAND_DERIVED';
    equal((await run(x)).decision, 'OBSERVABILITY_NOT_ESTABLISHED', 'derived volume');
  });
  await record('shared source labels do not establish independence', async () => {
    const x = thermalExample(); x.measurement.volumeWitness.sourceId = x.measurement.commandSourceId;
    equal((await run(x)).decision, 'OBSERVABILITY_NOT_ESTABLISHED', 'shared source');
  });
  await record('unknown whole-flow coverage does not qualify', async () => {
    const x = thermalExample(); x.measurement.coverage = 'UNKNOWN';
    equal((await run(x)).decision, 'OBSERVABILITY_NOT_ESTABLISHED', 'coverage');
  });
  await record('unbounded temperature does not qualify', async () => {
    const x = thermalExample(); x.measurement.temperatureWitness.kind = 'UNBOUNDED';
    equal((await run(x)).decision, 'OBSERVABILITY_NOT_ESTABLISHED', 'temperature');
  });
  await record('relative uncertainty uses the true-heat lower bound', async () => {
    const x = thermalExample(); x.measurement.intervals[0].volumeUncertaintyNL = 9200000;
    const r = await run(x);
    equal(r.evidence.uncertainty.worstRelativeErrorPpm, '111112', 'one ninth, rounded up');
    equal(r.decision, 'UNCERTAINTY_EXCEEDS_POLICY', 'wide uncertainty');
  });
  await record('zero-crossing aggregate heat is unidentifiable', async () => {
    const x = thermalExample(); x.measurement.intervals[0].deltaTemperatureUK = 0;
    x.measurement.intervals[0].deltaTemperatureUncertaintyUK = 100;
    equal((await run(x)).decision, 'POSITIVE_HEAT_NOT_IDENTIFIABLE', 'zero crossing');
  });
  await record('signed intervals are retained and integrated', async () => {
    const x = thermalExample(); x.measurement.windowMs = 120000;
    x.measurement.intervals.push({ ...x.measurement.intervals[0], sequence: 1, startMs: 60000,
      deltaTemperatureUK: -1000000 });
    equal((await run(x)).evidence.quantity.estimate, '3312000000', 'signed net heat');
  });
  await record('work exhaustion is incomplete, never a completed negative', async () => {
    const x = thermalExample(); x.measurement.windowMs = 120000;
    x.measurement.intervals.push({ ...x.measurement.intervals[0], sequence: 1, startMs: 60000 });
    x.maxWorkUnits = 1; const r = await run(x);
    equal(r.decision, 'WORK_BUDGET_EXHAUSTED', 'budget');
    equal(r.evidence.completion, 'EXHAUSTED', 'completion');
    equal(r.evidence.workUnits, 1, 'exact work limit');
    equal(r.evidence.coverageMs, 60000, 'partial window retained');
  });
  await record('interrupted checkpoint propagates without an accepted result', async () => {
    let failed = false;
    try { await executeThermal(thermalExample(), async () => { throw Error('CANCELLED'); }); }
    catch (error) { failed = error.message === 'CANCELLED'; }
    check(failed, 'cancellation propagation');
  });
  await record('caller mutation after checkpoint cannot change the captured inputs', async () => {
    const x = thermalExample();
    const r = await executeThermal(x, async () => { x.measurement.intervals[0].volumeNL = 1; });
    equal(r.evidence.quantity.estimate, '3680000000', 'owned input snapshot');
  });
  for (const [name, mutate] of [
    ['duplicate sequence', x => { x.measurement.intervals[0].sequence = 1; }],
    ['missing acquisition window', x => { x.measurement.windowMs++; }],
    ['noninteger volume', x => { x.measurement.intervals[0].volumeNL = 0.2; }],
    ['negative zero', x => { x.measurement.intervals[0].startMs = -0; }],
    ['negative duration', x => { x.measurement.intervals[0].durationMs = -1; }],
    ['unknown schema', x => { x.schema = 'thermal-witness/v9'; }],
    ['loosened five percent policy', x => { x.policy.maxRelativeErrorPpm = 50001; }],
    ['oversized decimal', x => { x.policy.minimumHeatMicroJ = '1'.repeat(25); }],
    ['accessor input', x => { Object.defineProperty(x.measurement.intervals[0], 'volumeNL',
      { get() { return 92000000; }, enumerable: true }); }],
    ['sparse interval array', x => { delete x.measurement.intervals[0]; }],
    ['symbol property', x => { x[Symbol('hidden')] = 1; }],
  ]) {
    await record('reject ' + name, () => { const x = thermalExample(); mutate(x); reject(() => validateThermalInput(x), name); });
  }
  await record('heat capacity is derived from independent loss and container bounds', async () => {
    const r = await run(thermalExample('heat-capacity'));
    equal(r.evidence.downstream.estimate, '268/1', '3680-800-200 joules over 10K');
    equal(r.decision, 'CONDITIONAL_BOUNDS_MET', 'heat capacity bounds');
  });
  await record('heat capacity refuses an absent independent reference', async () => {
    const x = thermalExample('heat-capacity'); x.extension.kind = 'ABSENT';
    equal((await run(x)).decision, 'ADDITIONAL_INDEPENDENT_WITNESS_REQUIRED', 'sample reference');
  });
  await record('zero lower temperature rise is not regularized', async () => {
    const x = thermalExample('heat-capacity'); x.extension.temperatureRiseUK.low = 0;
    equal((await run(x)).decision, 'HEAT_CAPACITY_NOT_IDENTIFIABLE', 'sample unidentifiable');
  });
  await record('downstream heat capacity uncertainty is separately constrained', async () => {
    const x = thermalExample('heat-capacity'); x.extension.temperatureRiseUK.low = 1000000;
    equal((await run(x)).decision, 'DOWNSTREAM_UNCERTAINTY_EXCEEDS_POLICY', 'sample accuracy');
  });
  await record('impossible loss budget remains inconsistent', async () => {
    const x = thermalExample('heat-capacity');
    x.extension.lossEnergyMicroJ = { low: '5000000000', estimate: '5000000000', high: '5000000000' };
    equal((await run(x)).decision, 'ENERGY_BOUNDARY_INCONSISTENT', 'losses');
  });
  await record('recovery accounts for stored energy with exact rational result', async () => {
    const r = await run(thermalExample('heat-recovery'));
    equal(r.evidence.downstream.estimate, '87/125', '(3680-200)/5000');
    equal(r.decision, 'CONDITIONAL_BOUNDS_MET', 'recovery bound');
  });
  await record('recovery with zero denominator lower bound is unidentifiable', async () => {
    const x = thermalExample('heat-recovery'); x.extension.inputEnergyMicroJ.low = '0';
    equal((await run(x)).decision, 'RECOVERY_RATIO_NOT_IDENTIFIABLE', 'denominator');
  });
  await record('impossible recovery is preserved above one rather than clamped', async () => {
    const x = thermalExample('heat-recovery');
    x.extension.inputEnergyMicroJ = { low: '1000000000', estimate: '1000000000', high: '1000000000' };
    const r = await run(x);
    equal(r.evidence.downstream.estimate, '87/25', 'unclamped ratio');
    equal(r.decision, 'ENERGY_BOUNDARY_INCONSISTENT', 'impossible recovery');
  });
  await record('submicrojoule results round bounds outward', async () => {
    const x = thermalExample();
    x.measurement.densityKgPerM3 = { low: 1, estimate: 1, high: 1 };
    x.measurement.specificHeatJPerKgK = { low: 1, estimate: 1, high: 1 };
    x.measurement.intervals[0].volumeNL = 1; x.measurement.intervals[0].deltaTemperatureUK = 1;
    const r = await run(x); equal(r.evidence.quantity.low, '0', 'floor'); equal(r.evidence.quantity.high, '1', 'ceil');
    equal(r.decision, 'POSITIVE_HEAT_NOT_IDENTIFIABLE', 'rounding uncertainty');
  });
  await record('published metrology failure is reproduced by independent ODE reference', async () => {
    const f = foundryWitnessFixture(), r = await run(f.input);
    check(Math.abs(f.audit.trueSecondaryHeatJ - 5009.6244576737745) < 0.000001, 'published truth');
    check(Math.abs(f.audit.legacyCommandHeatJ - 5445.281559253128) < 0.000001, 'published calorimeter');
    check(f.audit.oldRelativeError > 0.08, 'old failure retained');
    equal(r.evidence.quantity.low, '4943354615', 'independent integer lower bound');
    equal(r.evidence.quantity.estimate, '5035816195', 'independent integer estimate');
    equal(r.evidence.quantity.high, '5129056527', 'independent integer upper bound');
    equal(r.evidence.uncertainty.worstRelativeErrorPpm, '18862', 'independent relative bound');
    equal(r.evidence.inheritedFailure.status, 'RETAINED_UNDETECTED_FAILURE', 'history preservation');
    equal(r.decision, 'CONDITIONAL_BOUNDS_MET', 'new construction');
    check(!JSON.stringify(f.input).includes('multipliers') && !JSON.stringify(f.input).includes('trueSecondaryHeatJ'),
      'worker does not receive hidden evaluator state');
  });
  for (const scenario of ['nominal', 'flow-power-uncertainty']) for (const history of [-10, 0, 10]) {
    await record('independent containment ' + scenario + ' history ' + history, async () => {
      const f = foundryWitnessFixture({ scenario, initialHistoryK: history,
        volumeMeterBias: history < 0 ? -0.005 : history === 0 ? 0.003 : 0.005,
        differentialBiasK: history < 0 ? -0.004 : 0.002 });
      const r = await run(f.input), q = f.audit.trueSecondaryHeatJ;
      check(Number(r.evidence.quantity.low) / 1e6 <= q && q <= Number(r.evidence.quantity.high) / 1e6, 'reference contained');
      equal(r.decision, 'CONDITIONAL_BOUNDS_MET', 'declared conditional interval');
    });
  }
  await record('too-wide differential calibration fails useful accuracy', async () => {
    const f = foundryWitnessFixture();
    f.input.measurement.intervals.forEach(v => { v.deltaTemperatureUncertaintyUK = 50000; });
    equal((await run(f.input)).decision, 'UNCERTAINTY_EXCEEDS_POLICY', 'wide sensor error');
  });
  await record('a conventional equivalent instrument ties, not universal superiority', async () => {
    const x = thermalExample(), y = thermalExample();
    y.measurement.volumeWitness.sourceId = 'conventional-volume';
    y.measurement.temperatureWitness.sourceId = 'conventional-differential';
    const a = await run(x), b = await run(y);
    equal(JSON.stringify(a.evidence.quantity), JSON.stringify(b.evidence.quantity), 'equal instrument');
  });
  return { passed: passed.length, cases: passed };
}
