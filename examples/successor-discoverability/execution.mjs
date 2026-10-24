// SPDX-License-Identifier: Apache-2.0
import { executeProgram, validateProblem, snapshot } from './compiler.mjs';
import { acquireSynthetic } from './domains.mjs';
import { createDiscoverabilityWorkbench, discoverabilityMission } from './workbench-adapter.mjs';
import { canonical, parseBounded, digest } from '../../docs/assets/successor/engine.mjs';

const capture = value => parseBounded(canonical(value));
const checkSource = sourceHash => {
  if (!/^[a-f0-9]{64}$/.test(sourceHash || '')) throw Error('SOURCE_IDENTITY_REQUIRED');
};
const asMicros = (start, end) => {
  const value = Math.max(0, Math.round((end - start) * 1000));
  if (!Number.isSafeInteger(value)) throw Error('TIMING_RANGE');
  return value;
};

export async function executeObservations(workbenchPack, observations, {
  clock = () => globalThis.performance.now(),
} = {}) {
  const started = clock(), pack = capture(snapshot(workbenchPack)), retained = capture(snapshot(observations));
  await createDiscoverabilityWorkbench().inspectPack(pack);
  const sourceHash = pack.frozen.sourceHash, workbenchPackDigest = pack.integrityDigest;
  checkSource(sourceHash);
  const construction = pack.result.evidence.construction;
  if (construction.status !== 'COMPILED') throw Error('COMPILED_PROGRAM_REQUIRED');
  const problem = pack.spec.inputs.problem, program = construction.program;
  const result = executeProgram(problem, program, retained);
  const body = {
    schema: 'discoverability.execution.v1', sourceHash, workbenchPackDigest,
    programDigest: await digest('discoverability-program', program),
    observations: retained, result,
    decodingElapsedMicroseconds: asMicros(started, clock()),
    acceptedCapability: false, independentlyAuthenticated: false,
    authority: [], settlement: 'NOT_CONNECTED',
  };
  return { ...body, integrityDigest: await digest('discoverability-execution', body) };
}

export async function runSyntheticJourney(problem, evaluator, {
  sourceHash, compiler, budget = 2000000, signal,
  onCheckpoint = async () => {}, clock = () => globalThis.performance.now(),
} = {}) {
  checkSource(sourceHash);
  problem = validateProblem(problem);
  evaluator = snapshot(evaluator);
  const evaluatorKeys = Object.keys(evaluator).sort();
  if (evaluatorKeys.some(key => !['worldId', 'nuisanceScale', 'errorSign'].includes(key)) ||
      typeof evaluator.worldId !== 'string') throw Error('EVALUATOR_INPUT');
  if (evaluator.nuisanceScale !== undefined && (!Number.isSafeInteger(evaluator.nuisanceScale) || Math.abs(evaluator.nuisanceScale) > 10000)) throw Error('EVALUATOR_NUISANCE');
  if (evaluator.errorSign !== undefined && ![-1, 0, 1].includes(evaluator.errorSign)) throw Error('EVALUATOR_ERROR');
  const checkpoint = async phase => {
    await onCheckpoint(phase);
    if (signal?.aborted) throw Error('CANCELLED');
  };
  await checkpoint('compile');
  const runtime = createDiscoverabilityWorkbench(compiler ? { compiler } : {});
  const start = clock();
  const pack = await runtime.run(discoverabilityMission(problem, { budget }), {
    sourceHash, signal, onCheckpoint, clock,
  });
  const compilationElapsedMicroseconds = asMicros(start, clock());
  const construction = pack.result.evidence.construction;
  if (construction.status !== 'COMPILED') {
    return {
      schema: 'discoverability.synthetic-journey.v1',
      mode: 'NEWLY_EXECUTED_SYNTHETIC', pack, execution: null, evaluator: null,
      operationalState: 'CONSTRUCTION_REFUSED',
      costs: { compilerWorkUnits: construction.work.used, compilationElapsedMicroseconds,
        acquisitionDeclaredUnits: 0, physicalAcquisitionCost: null, computeCost: null, humanMinutes: null },
      acceptedCapability: false, authority: [], settlement: 'NOT_CONNECTED',
    };
  }
  await checkpoint('acquire new synthetic readings');
  const started = clock();
  const acquisition = acquireSynthetic(problem, construction.program, evaluator.worldId, {
    nuisanceScale: evaluator.nuisanceScale ?? 13, errorSign: evaluator.errorSign ?? 0,
  });
  const acquisitionElapsedMicroseconds = asMicros(started, clock());
  await checkpoint('decode observations');
  const execution = await executeObservations(pack, acquisition.observations, { clock });
  const matched = execution.result.status === 'DECIDED' &&
    execution.result.decision === acquisition.truthForEvaluatorOnly.requiredDecision;
  const body = {
    schema: 'discoverability.synthetic-journey.v1',
    mode: 'NEWLY_EXECUTED_SYNTHETIC', pack, execution,
    evaluator: {
      disclosure: 'The actual world and expected decision are visible only to this synthetic acquisition/evaluation stage, not passed to the compiler or decoder.',
      acquisition: capture(acquisition), matched,
      independence: 'ALGORITHMIC_ROLE_SEPARATION_WITHIN_ONE_PROCESS',
    },
    operationalState: matched ? 'SYNTHETIC_DELIVERY_MATCHED' : 'SYNTHETIC_DELIVERY_FAILED',
    costs: {
      compilerWorkUnits: construction.work.used, compilationElapsedMicroseconds,
      acquisitionDeclaredUnits: construction.program.totalCost, acquisitionElapsedMicroseconds,
      physicalAcquisitionCost: null, computeCost: null, humanMinutes: null,
    },
    acceptedCapability: false, authority: [], settlement: 'NOT_CONNECTED',
  };
  await checkpoint('retain delivery evidence');
  return { ...body, integrityDigest: await digest('discoverability-journey', body) };
}
