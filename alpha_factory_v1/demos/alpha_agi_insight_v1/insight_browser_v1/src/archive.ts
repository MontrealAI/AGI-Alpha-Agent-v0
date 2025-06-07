// SPDX-License-Identifier: Apache-2.0
import { createStore, set, get, del, values } from './utils/keyval.ts';
import type { EvaluatorGenome } from './evaluator_genome.ts';
import type { Individual } from './state/serializer.ts';
import { detectColdZone } from './utils/cluster.ts';
import { chat } from './utils/llm.ts';

interface KeyValueStore<T> {
  dbp: Promise<IDBDatabase | null>;
  storeName: string;
  memory: Map<string, T> | null;
}

interface WindowWithToast extends Window {
  toast?: (msg: string) => void;
}

export interface RunParams {
  sector?: string;
  keywords?: string[];
  [key: string]: unknown;
}

export interface InsightRun {
  id: string;
  seed: number;
  params: RunParams;
  paretoFront: Individual[];
  parents: string[];
  evalId: string;
  score: number;
  impactScore: number;
  novelty: number;
  timestamp: number;
}

export interface EvaluatorRecord {
  id: string;
  genome: EvaluatorGenome;
}

export class Archive {
  private runStore: KeyValueStore<InsightRun>;
  private evalStore: KeyValueStore<EvaluatorRecord>;
  private disabled = false;
  constructor(private name = 'insight-archive') {
    this.runStore = createStore<InsightRun>(this.name, 'runs');
    this.evalStore = createStore<EvaluatorRecord>(this.name, 'evals');
  }

  async open(): Promise<void> {
    await this.runStore.dbp;
    await this.evalStore.dbp;
    if (!this.disabled) {
      if (
        typeof document !== 'undefined' &&
        typeof document.hasStorageAccess === 'function'
      ) {
        try {
          const access = await (
            (document as { hasStorageAccess?: () => Promise<boolean> }).hasStorageAccess?.() ??
            Promise.resolve(false)
          );
          if (!access) {
            this.runStore.memory = new Map<string, InsightRun>();
            this.evalStore.memory = new Map<string, EvaluatorRecord>();
          }
        } catch {
          this.runStore.memory = new Map<string, InsightRun>();
          this.evalStore.memory = new Map<string, EvaluatorRecord>();
        }
      }

      if (this.runStore.memory || this.evalStore.memory) {
        this.disabled = true;
        const toast = (window as WindowWithToast).toast;
        if (typeof toast === 'function') {
          toast('Archive disabled (no storage access)');
        }
      }
    }
  }

  private _vector(front: Individual[]): [number, number] {
    if (!front.length) return [0, 0];
    const l = front.reduce((s, d) => s + (d.logic ?? 0), 0) / front.length;
    const f = front.reduce((s, d) => s + (d.feasible ?? 0), 0) / front.length;
    return [l, f];
  }

  private _dist(a: [number, number], b: [number, number]): number {
    return Math.hypot(a[0] - b[0], a[1] - b[1]);
  }

  private async _novelty(vec: [number, number], k = 5): Promise<number> {
    const runs = await this.list();
    if (!runs.length) return 0;
    const dists = runs.map((r) => this._dist(vec, this._vector(r.paretoFront)));
    dists.sort((a, b) => a - b);
    const n = Math.min(k, dists.length);
    return dists.slice(0, n).reduce((s, d) => s + d, 0) / n;
  }

  async add(
    seed: number,
    params: RunParams,
    paretoFront: Individual[],
    parents: string[] = [],
    evalId: string = ''
  ): Promise<string> {
    await this.open();
    const vec = this._vector(paretoFront);
    const score = (vec[0] + vec[1]) / 2;
    const novelty = await this._novelty(vec);
    let impact = 0;
    try {
      if (localStorage.getItem('OPENAI_API_KEY')) {
        const resp = await chat(
          `Estimate economic impact for: ${JSON.stringify(paretoFront)}`,
        );
        const val = parseFloat(resp);
        if (!Number.isNaN(val)) impact = val;
      }
    } catch {
      impact = 0;
    }
    const impactScore = score + impact;
    const id = typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : String(Date.now());
    const run: InsightRun = {
      id,
      seed,
      params,
      paretoFront,
      parents,
      evalId,
      score,
      impactScore,
      novelty,
      timestamp: Date.now(),
    };
    try {
      await set(id, run, this.runStore);
    } catch (err: unknown) {
      if ((err as DOMException)?.name === 'QuotaExceededError') {
        await this.prune();
        const toast = (window as WindowWithToast).toast;
        if (typeof toast === 'function') {
          toast('Archive full; oldest runs pruned');
        }
        await set(id, run, this.runStore);
      } else {
        throw err;
      }
    }
    await this.prune(50);
    return id;
  }

  async list(): Promise<InsightRun[]> {
    await this.open();
    const runs = (await values(this.runStore)) as InsightRun[];
    runs.sort((a, b) => a.timestamp - b.timestamp);
    return runs;
  }

  async addEvaluator(genome: EvaluatorGenome): Promise<string> {
    await this.open();
    const id = typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : String(Date.now());
    const rec: EvaluatorRecord = { id, genome };
    await set(id, rec, this.evalStore);
    return id;
  }

  async listEvaluators(): Promise<EvaluatorRecord[]> {
    await this.open();
    const evals = (await values(this.evalStore)) as EvaluatorRecord[];
    return evals;
  }

  async prune(max = 50): Promise<void> {
    const runs = await this.list();
    if (runs.length <= max) return;
    runs.sort(
      (a, b) =>
        b.score + b.novelty - (a.score + a.novelty) || b.timestamp - a.timestamp,
    );
    const keep = runs.slice(0, max);
    const remove = runs.slice(max);
    await Promise.all(
      remove.map((r) =>
        del(r.id, this.runStore).catch((err: unknown) => {
          if (err instanceof DOMException) {
            console.warn('Failed to delete run', r.id, err);
          } else {
            throw err;
          }
        }),
      ),
    );
    const keepIds = new Set(keep.map((r) => r.evalId));
    const evals = (await values(this.evalStore)) as EvaluatorRecord[];
    await Promise.all(
      evals
        .filter((e) => !keepIds.has(e.id))
        .map((e) =>
          del(e.id, this.evalStore).catch((err: unknown) => {
            if (err instanceof DOMException) {
              console.warn('Failed to delete evaluator', e.id, err);
            } else {
              throw err;
            }
          }),
        )
    );
  }

  async selectParents(
    count: number,
    beta = 1,
    gamma = 1,
    rand: () => number = Math.random,
  ): Promise<InsightRun[]> {
    const runs = await this.list();
    if (!runs.length) return [];
    const scoreW = runs.map((r) => Math.exp(beta * (r.impactScore ?? r.score)));
    const novW = runs.map((r) => Math.exp(gamma * r.novelty));
    const sumS = scoreW.reduce((a, b) => a + b, 0);
    const sumN = novW.reduce((a, b) => a + b, 0);
    const points = runs.map((r) => this._vector(r.paretoFront));
    const cz = detectColdZone(points);
    const bins = 10;
    const factors = points.map(([x, y]) => {
      const cx = Math.floor(x * bins);
      const cy = Math.floor(y * bins);
      return cx === cz.x && cy === cz.y ? 2 : 1;
    });
    const weights = runs.map((_, i) => (scoreW[i] / sumS) * (novW[i] / sumN) * factors[i]);
    const wSum = weights.reduce((a, b) => a + b, 0);
    for (let i = 0; i < weights.length; i++) weights[i] /= wSum;
    const selected: InsightRun[] = [];
    for (let i = 0; i < Math.min(count, runs.length); i++) {
      let r = rand();
      let idx = 0;
      for (; idx < weights.length; idx++) {
        if (r < weights[idx]) break;
        r -= weights[idx];
      }
      selected.push(runs[idx]);
    }
    return selected;
  }
}
