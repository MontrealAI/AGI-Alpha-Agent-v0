// SPDX-License-Identifier: Apache-2.0
// Fixed shipped registrations; imported missions cannot install executable adapters.
import * as core from './engine.mjs';
import { thermalWitnessAdapter, thermalExample } from './thermal-witness.mjs';

const runtime = core.createWorkbench([thermalWitnessAdapter]);
export const VERSION = core.VERSION;
export const REGISTRY = runtime.registry;
export const validate = runtime.validate;
export const plan = runtime.plan;
export const run = runtime.run;
export const inspectPack = runtime.inspectPack;

export function example(family = 'reliability') {
  if (family !== 'thermal-witness') return core.example(family);
  return { ...core.example(), family, name: 'Witnessed thermal measurement',
    rights: { dataClass: 'synthetic', source: 'Declared simulated whole-flow fixture', license: 'Apache-2.0' },
    inputs: thermalExample() };
}
