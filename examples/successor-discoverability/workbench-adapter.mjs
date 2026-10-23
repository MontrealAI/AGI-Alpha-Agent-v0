// SPDX-License-Identifier: Apache-2.0
import { createWorkbench } from '../successor-workbench/engine.mjs';
import { canonical, parseBounded } from '../../docs/assets/successor/engine.mjs';
import { createCompiler, validateProblem } from './compiler.mjs';

const ownFields = (value, expected, label) => {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      ![Object.prototype, null].includes(Object.getPrototypeOf(value)) ||
      Object.getOwnPropertySymbols(value).length) throw Error(label);
  const keys = Object.getOwnPropertyNames(value).sort(), want = [...expected].sort();
  if (keys.length !== want.length || keys.some((key, index) => key !== want[index])) throw Error(label);
  for (const key of keys) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor.enumerable || !Object.hasOwn(descriptor, 'value')) throw Error(label);
  }
};
const jsonFile = (name, value) => ({
  name, type: 'application/json', content: JSON.stringify(value, null, 2) + '\n',
});

export function createDiscoverabilityAdapter({ compiler = createCompiler() } = {}) {
  if (!compiler || typeof compiler.compile !== 'function' || typeof compiler.stats !== 'function') {
    throw Error('INSTALLED_COMPILER_REQUIRED');
  }
  return {
    manifest: {
      id: 'discoverability', version: 1,
      en: 'Construct a decision-making instrument',
      fr: 'Construire un instrument de décision',
      scope: 'Compile bounded integer contrasts that distinguish declared decisions despite explicitly modeled nuisance and bounded measurement error.',
      artifact: 'experiment-plan.json',
    },
    validate(input) {
      ownFields(input, ['problem', 'budget'], 'DISCOVERABILITY_INPUT_SCHEMA');
      if (!Number.isSafeInteger(input.budget) || input.budget < 1 || input.budget > 2000000) {
        throw Error('DISCOVERABILITY_WORK_BUDGET');
      }
      validateProblem(input.problem);
    },
    async execute(input, checkpoint) {
      const before = parseBounded(canonical(compiler.stats()));
      await checkpoint('compiling an informative experiment');
      const result = await compiler.compile(input.problem, {
        budget: input.budget,
        checkpoint: () => checkpoint('constructing bounded integer contrasts'),
      });
      await checkpoint('recording the construction and limits');
      const after = parseBounded(canonical(compiler.stats()));
      const statuses = {
        COMPILED: 'REVIEW_REQUIRED',
        UNIDENTIFIABLE_WITHIN_GRAMMAR: 'REJECTED_WITHIN_GRAMMAR',
        OVER_MISSION_BUDGET: 'REJECTED_OVER_MISSION_BUDGET',
        BUDGET_EXHAUSTED: 'INCONCLUSIVE',
      };
      if (!Object.hasOwn(statuses, result.status)) throw Error('COMPILER_STATUS');
      const selected = result.program?.experiments || [];
      const acquisitionCost = selected.reduce((sum, experiment) => sum + experiment.cost, 0);
      if (!Number.isSafeInteger(acquisitionCost)) throw Error('ACQUISITION_COST');
      const acceptance = {
        schema: 'discoverability.acceptance.v1',
        compilerStatus: result.status,
        acceptedCapability: false,
        criterion: 'Every pair of declared worlds with different required decisions has at least one selected contrast with strictly disjoint bounded observation intervals.',
        uncertaintyModel: 'Nuisance belongs to the declared linear span; each experiment obtains fresh channel reads with independently bounded continuous errors.',
        declaredModelOnly: true,
        requiresIndependentReview: true,
        authority: [],
        settlement: 'NOT_CONNECTED',
      };
      return {
        decision: statuses[result.status],
        summary: {
          compilerStatus: result.status,
          experimentCount: selected.length,
          acquisitionCost,
          acquisitionCostUnit: 'declared per-channel acquisition units',
          workUsed: result.work.used,
          workLimit: result.work.limit,
          acceptedCapability: false,
        },
        evidence: {
          construction: result,
          compilerStatsBefore: before,
          compilerStatsAfter: after,
          acceptance,
          inheritedJobsDraft: 'The existing seven-package unfunded compiler retains aggregation-specific baseline and hard-gate wording. This draft is not a commissioned discoverability acceptance contract.',
        },
        artifacts: [
          jsonFile('experiment-plan.json', result),
          jsonFile('input-model.json', input.problem),
          jsonFile('acceptance.json', acceptance),
        ],
        limits: [
          'The returned instrument is executable software over a declared finite model, not a physical sensor or acquired measurement.',
          'A finite-model certificate does not establish that the real world belongs to that model or calibration envelope.',
          'Compilation, local execution, independent review, capability promotion and settlement are separate states.',
          'Acquisition units and compiler work units are not dollars. Compute, human labor and commercial value require separate observations.',
          'The inherited Jobs work packages are inert zero-funded drafts; no new receiver, executor, role eligibility or financial authority is created.',
        ],
      };
    },
  };
}

export function createDiscoverabilityWorkbench(options = {}) {
  return createWorkbench([createDiscoverabilityAdapter(options)]);
}

export function discoverabilityMission(problem, { budget = 2000000, name = 'Discoverability Ω', language = 'en' } = {}) {
  return {
    schema: 'successor-workbench/v1', family: 'discoverability', name, language,
    owner: 'local-owner',
    rights: { dataClass: 'synthetic', source: 'Explicit finite candidate model supplied for this local experiment', license: 'Apache-2.0' },
    reviewMinutes: 10, inputs: { problem, budget },
  };
}
