// SPDX-License-Identifier: Apache-2.0
import type { Individual as BaseIndividual } from '../state/serializer.js';

export interface Mutant extends BaseIndividual {
  strategy: string;
  depth: number;
  horizonYears: number;
}

export function mutate(
  pop: Mutant[],
  rand: () => number,
  strategies: string[],
  gen = 0,
  adaptive = false,
  scale = 1,
  gpu = false,
): Mutant[] {
  const clamp = (v: number): number => Math.min(1, Math.max(0, v));
  const mutants: Mutant[] = [];
  function converged() {
    if (!adaptive) return false;
    const meanL = pop.reduce((s, d) => s + (d.logic ?? 0), 0) / pop.length;
    const meanF = pop.reduce((s, d) => s + (d.feasible ?? 0), 0) / pop.length;
    const varL = pop.reduce((s, d) => s + Math.pow((d.logic ?? 0) - meanL, 2), 0) / pop.length;
    const varF = pop.reduce((s, d) => s + Math.pow((d.feasible ?? 0) - meanF, 2), 0) / pop.length;
    return varL + varF < 1e-3;
  }
  const isConv = converged();
  for (const d of pop) {
    for (const s of strategies) {
      switch (s) {
        case 'gaussian':
          {
            let sigma = 0.12 * Math.log1p(d.horizonYears || 0) * scale;
            if (isConv) sigma *= 0.5;
            mutants.push({
              logic: clamp(d.logic + (rand() - 0.5) * sigma),
              feasible: clamp(d.feasible + (rand() - 0.5) * sigma),
              strategy: s,
              depth: gen,
              horizonYears: d.horizonYears,
            });
          }
          break;
        case 'swap': {
          const other = pop[Math.floor(rand() * pop.length)];
          mutants.push({
            logic: other.logic,
            feasible: d.feasible,
            strategy: s,
            depth: gen,
            horizonYears: d.horizonYears,
          });
          break;
        }
        case 'jump':
          mutants.push({
            logic: rand(),
            feasible: rand(),
            strategy: s,
            depth: gen,
            horizonYears: d.horizonYears,
          });
          break;
        case 'scramble': {
          const other = pop[Math.floor(rand() * pop.length)];
          mutants.push({
            logic: d.logic,
            feasible: other.feasible,
            strategy: s,
            depth: gen,
            horizonYears: d.horizonYears,
          });
          break;
        }
      }
    }
  }
  return pop.concat(mutants);
}
