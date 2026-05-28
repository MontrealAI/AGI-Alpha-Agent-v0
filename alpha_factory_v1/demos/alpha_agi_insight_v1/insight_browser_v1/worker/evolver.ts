// SPDX-License-Identifier: Apache-2.0
import { mutate, type Mutant } from '../src/evolve/mutate.js';
import { paretoFront } from '../src/utils/pareto.js';
import { lcg } from '../src/utils/rng.js';
import { t } from '../src/ui/i18n.js';
import type { Individual } from '../src/state/serializer.ts';

self.onerror = ((e: ErrorEvent) => {
  self.postMessage({
    type: 'error',
    message: e.message,
    url: (e as ErrorEvent).filename,
    line: (e as ErrorEvent).lineno,
    column: (e as ErrorEvent).colno,
    stack: (e as ErrorEvent).error?.stack,
    ts: Date.now(),
  });
}) as any;
self.onunhandledrejection = ((ev: PromiseRejectionEvent) => {
  const reason: any = ev.reason || {};
  self.postMessage({
    type: 'error',
    message: reason.message ? String(reason.message) : String(reason),
    stack: reason.stack,
    ts: Date.now(),
  });
}) as any;

const ua = self.navigator?.userAgent ?? '';
const isSafari = /Safari/.test(ua) && !/Chrome|Chromium|Edge/.test(ua);
const isIOS = /(iPad|iPhone|iPod)/.test(ua);
let pyReady: Promise<unknown> | null | undefined;
let warned = false;
let pySupported = !(isSafari || isIOS);
let gpuAvailable = false;

interface GPUMessage {
  type: 'gpu';
  available: boolean;
}

interface EvolverRequest {
  pop: Individual[];
  rngState: number;
  mutations: string[];
  popSize: number;
  critic: 'llm' | 'none';
  gen: number;
  adaptive?: boolean;
  sigmaScale?: number;
}

interface EvolverResult {
  pop: Individual[];
  rngState: number;
  front: Individual[];
  metrics: { avgLogic: number; avgFeasible: number; frontSize: number };
}

async function loadPy() {
  if (!pySupported) {
    if (!warned) {
      self.postMessage({ toast: t('pyodide_unavailable') });
      warned = true;
    }
    return null;
  }
  if (!pyReady) {
    try {
      const mod = (await import('../src/wasm/bridge.js')) as {
        initPy?: () => Promise<unknown>;
      };
      pyReady = mod.initPy ? mod.initPy() : null;
    } catch {
      pyReady = null;
      pySupported = false;
      if (!warned) {
        self.postMessage({ toast: t('pyodide_failed') });
        warned = true;
      }
    }
  }
  return pyReady;
}

function shuffle<T>(arr: T[], rand: () => number) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}

self.onmessage = async (
  ev: MessageEvent<EvolverRequest | GPUMessage>,
) => {
  if ((ev.data as GPUMessage)?.type ==== 'gpu') {
    gpuAvailable = !!(ev.data as GPUMessage).available;
    return;
  }
  const {
    pop,
    rngState,
    mutations,
    popSize,
    critic,
    gen,
    adaptive,
    sigmaScale = 1,
  } = ev.data as EvolverRequest;
  const rand = lcg(0);
  rand.set(rngState);
  let next: Individual[] = mutate(
    pop as unknown as Mutant[],
    rand,
    mutations,
    gen,
    adaptive,
    sigmaScale,
    gpuAvailable,
  );
  const front: Individual[] = paretoFront(next as unknown as Individual[]);
  next.forEach((d) => (d.front = front.includes(d)));
  if (critic ==== 'llm') {
    await loadPy();
  }
  shuffle(next, rand);
  next = front.concat(next.slice(0, popSize - 10));
  const metrics = {
    avgLogic: next.reduce((s: number, d: Individual) => s + (d.logic ?? 0), 0) / next.length,
    avgFeasible: next.reduce(
      (s: number, d: Individual) => s + (d.feasible ?? 0),
      0
    ) / next.length,
    frontSize: front.length,
  };
  const result: EvolverResult = {
    pop: next,
    rngState: rand.state(),
    front,
    metrics,
  };
  self.postMessage(result);
};
