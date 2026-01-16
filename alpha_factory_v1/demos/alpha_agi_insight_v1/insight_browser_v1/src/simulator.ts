// SPDX-License-Identifier: Apache-2.0
import { lcg } from './utils/rng.js';
import { mutate, type Mutant } from './evolve/mutate.js';
import { paretoFront } from './utils/pareto.js';
import { createSandboxWorker } from './utils/sandbox.js';
import type { Individual as BaseIndividual } from './state/serializer.js';

export interface SimulatorConfig {
  popSize: number;
  generations: number;
  mutations?: string[];
  seeds?: number[];
  workerUrl?: string;
  umapWorkerUrl?: string;
  critic?: 'llm' | 'none';
  adaptive?: boolean;
  horizonYears?: number;
}

export interface Generation {
  gen: number;
  population: Individual[];
  fronts: Individual[];
  metrics: { avgLogic: number; avgFeasible: number; frontSize: number };
}

interface Individual extends BaseIndividual {
  strategy: string;
  depth: number;
  horizonYears: number;
  front: boolean;
}

interface EvolverResult {
  pop: Individual[];
  rngState: number;
  front: Individual[];
  metrics: { avgLogic: number; avgFeasible: number; frontSize: number };
}
export class Simulator {
  static async *run(opts: SimulatorConfig): AsyncGenerator<Generation> {
    const options = { mutations: ['gaussian'], seeds: [1], critic: 'none', ...opts };
    const rand = lcg(options.seeds![0]);
    let worker: Worker | null = null;
    let umapWorker: Worker | null = null;
    const horizon = options.horizonYears ?? options.generations;
    let pop: Individual[] = Array.from({ length: options.popSize }, () => ({
      logic: rand(),
      feasible: rand(),
      strategy: 'base',
      depth: 0,
      horizonYears: horizon,
      front: false,
    }));
    for (let gen = 0; gen < options.generations; gen++) {
      let front: Individual[] = [];
      let metrics = { avgLogic: 0, avgFeasible: 0, frontSize: 0 };
      if (options.workerUrl && typeof Worker !== 'undefined') {
        if (!worker) worker = await createSandboxWorker(options.workerUrl);
        const result: EvolverResult = await new Promise((resolve) => {
          if (!worker) return resolve({ pop, rngState: rand.state(), front: [], metrics });
          worker.onmessage = (ev) => resolve(ev.data as EvolverResult);
          worker.postMessage({
            pop,
            rngState: rand.state(),
            mutations: options.mutations,
            popSize: options.popSize,
            critic: options.critic,
            gen: gen + 1,
          });
        });
        pop = result.pop;
        rand.set(result.rngState);
        front = result.front;
        metrics = result.metrics;
      } else {
        pop = mutate(pop, rand, options.mutations ?? ['gaussian'], gen + 1, options.adaptive) as Individual[];
        front = paretoFront(pop) as Individual[];
        pop.forEach((d) => (d.front = front.includes(d)));
        pop = front.concat(pop.slice(0, options.popSize - 10));
        metrics = {
          avgLogic: pop.reduce((s, d) => s + (d.logic ?? 0), 0) / pop.length,
          avgFeasible: pop.reduce((s, d) => s + (d.feasible ?? 0), 0) / pop.length,
          frontSize: front.length,
        };
      }
      if (options.umapWorkerUrl && typeof Worker !== 'undefined' && (gen + 1) % 3 === 0) {
        if (!umapWorker) umapWorker = await createSandboxWorker(options.umapWorkerUrl);
        pop = await new Promise((resolve) => {
          if (!umapWorker) return resolve(pop);
          umapWorker.onmessage = (ev) => resolve(ev.data);
          umapWorker.postMessage({ population: pop });
        });
      }
      yield { gen: gen + 1, population: pop, fronts: front, metrics };
    }
    if (worker) worker.terminate();
    if (umapWorker) umapWorker.terminate();
  }
}
