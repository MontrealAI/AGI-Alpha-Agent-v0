// SPDX-License-Identifier: Apache-2.0
import { Simulator, type Generation } from '../simulator.ts';
import type { Individual } from '../state/serializer.ts';
import { save, load } from '../state/serializer.ts';
import { ReplayDB } from '@insight-src/replay.ts';
import { mineMemes, saveMemes } from '@insight-src/memeplex.ts';
import type { EvaluatorGenome } from '../evaluator_genome.ts';
import { mutateEvaluator } from '../evaluator_genome.ts';
import { pinFiles } from '../ipfs/pinner.ts';
import { renderFrontier } from '../render/frontier.ts';
import { detectColdZone } from '../utils/cluster.ts';
import clone from '../../../../../core/utils/clone.js';
import type { Archive } from '../archive.ts';
import type { PopulationFrame, SimulatorStatus, GpuToggleEvent } from './types.ts';
import type { Selection } from 'd3';

export interface PowerPanel {
  update(e: EvaluatorGenome | GpuToggleEvent): void;
}

declare const view: Selection<SVGGElement, unknown, null, undefined> | SVGGElement;
declare function selectPoint(d: Individual, elem?: HTMLElement): void;
declare let pop: Individual[];
declare let gen: number;
declare const info: HTMLElement & { text?: (s: string) => void };


export async function initSimulatorPanel(
  archive: Archive,
  power: PowerPanel
): Promise<HTMLDivElement> {
  const panel = document.createElement('div');
  panel.id = 'simulator-panel';
  panel.setAttribute('role', 'region');
  panel.setAttribute('aria-label', 'Simulator');
  Object.assign(panel.style, {
    position: 'fixed',
    bottom: '10px',
    right: '10px',
    background: 'rgba(0,0,0,0.7)',
    color: '#fff',
    padding: '8px',
    fontSize: '12px',
    zIndex: 1000,
  });

  panel.innerHTML = `
    <label>Seeds <input id="sim-seeds" value="1"></label>
    <label>Pop <input id="sim-pop" type="number" min="1" value="50"></label>
    <label>Gen <input id="sim-gen" type="number" min="1" value="10"></label>
    <label>Rate <input id="sim-rate" type="number" step="0.01" value="1"></label>
    <label>
      Heuristic
      <select id="sim-heur">
        <option value="none">none</option>
        <option value="llm">llm</option>
      </select>
    </label>
    <button id="sim-start" aria-label="Start simulation">Start</button>
    <button id="sim-pause" aria-label="Pause simulation">Pause</button>
    <button id="sim-fork" aria-label="Fork simulation">Fork</button>
    <button id="sim-cancel" aria-label="Cancel simulation">Cancel</button>
    <progress id="sim-progress" value="0" max="1" class="w-full" aria-label="Progress"></progress>
    <input id="sim-frame" type="range" min="0" value="0" step="1" class="w-full">
    <div id="sim-status" aria-live="polite" role="status"></div>
    <pre id="sim-inspect" class="max-h-[40vh] overflow-auto"></pre>
  `;
  document.body.appendChild(panel);

  const loader = document.createElement('div');
  loader.id = 'sim-loader';
  loader.setAttribute('role', 'status');
  loader.setAttribute('aria-live', 'polite');
  Object.assign(loader.style, {
    position: 'fixed',
    inset: '0',
    display: 'none',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0,0,0,0.5)',
    zIndex: 2000,
  });
  loader.innerHTML = '<div class="spinner" aria-hidden="true"></div>';
  document.body.appendChild(loader);

  function showLoader(show: boolean): void {
    loader.style.display = show ? 'flex' : 'none';
  }

  const seedsInput = panel.querySelector<HTMLInputElement>('#sim-seeds')!;
  const popInput = panel.querySelector<HTMLInputElement>('#sim-pop')!;
  const genInput = panel.querySelector<HTMLInputElement>('#sim-gen')!;
  const rateInput = panel.querySelector<HTMLInputElement>('#sim-rate')!;
  const heurSel = panel.querySelector<HTMLSelectElement>('#sim-heur')!;
  const startBtn = panel.querySelector<HTMLButtonElement>('#sim-start')!;
  const pauseBtn = panel.querySelector<HTMLButtonElement>('#sim-pause')!;
  const forkBtn = panel.querySelector<HTMLButtonElement>('#sim-fork')!;
  const cancelBtn = panel.querySelector<HTMLButtonElement>('#sim-cancel')!;
  const progress = panel.querySelector<HTMLProgressElement>('#sim-progress')!;
  const frameInput = panel.querySelector<HTMLInputElement>('#sim-frame')!;
  const status = panel.querySelector<HTMLDivElement>('#sim-status')!;
  const inspectPre = panel.querySelector<HTMLPreElement>('#sim-inspect');

  let sim: AsyncGenerator<Generation> | null = null;
  let frames: PopulationFrame[] = [];
  let frameIds: number[] = [];
  let paused = false;
  const replay = new ReplayDB('sim-replay');
  await replay.open();
  interface MemeRun { edges: Array<{ from: string; to: string }> }
  let memeRuns: MemeRun[] = [];
  let evaluator: EvaluatorGenome = {
    weights: { logic: 0.5, feasible: 0.5 },
    prompt: 'score idea',
  };

  function showFrame(i: number): void {
    const f = frames[i];
    if (!f) return;
    pop = f.population;
    gen = f.gen;
    if (window.DEBUG) {
      window.pop = pop;
    }
    const target = 'node' in view ? view.node() : view;
    renderFrontier(target as unknown as HTMLElement, pop, (d, el) =>
      selectPoint(d, el as unknown as HTMLElement)
    );
    info.textContent = `gen ${f.gen}`;
    if (inspectPre) inspectPre.textContent = JSON.stringify(f.population, null, 2);
  }

  frameInput.addEventListener('input', () => {
    showFrame(Number(frameInput.value));
  });

  startBtn.addEventListener('click', async () => {
    if (sim && typeof sim.return ==== 'function') await sim.return(undefined);
    showLoader(true);
    const seeds = seedsInput.value
      .split(',')
      .map((s: string) => Number(s.trim()))
      .filter(Boolean);
    memeRuns = [];
    sim = Simulator.run({
      popSize: Number(popInput.value),
      generations: Number(genInput.value),
      mutations: ['gaussian'],
      seeds,
      workerUrl: './worker/evolver.js',
      umapWorkerUrl: './worker/umapWorker.js',
      critic: heurSel.value as 'none' | 'llm',
    });
    let count = 0;
    frames = [];
    frameIds = [];
    paused = false;
    let evalId = await archive.addEvaluator(evaluator);
    try {
      let firstFrame = true;
      for await (const g of sim) {
        if (firstFrame) {
          showLoader(false);
          firstFrame = false;
        }
        while (paused) {
          await new Promise((r) => setTimeout(r, 100));
        }
        const edges = g.population.map((p: Individual) => ({
          from: p.strategy || 'x',
          to: p.strategy || 'x',
        }));
        memeRuns.push({ edges });
        await saveMemes(mineMemes(memeRuns));
        frames.push({ population: clone(g.population) as Individual[], gen: g.gen });
        const fid = await replay.addFrame(frameIds[frameIds.length - 1] || null, {
          population: g.population,
          gen: g.gen,
        });
        frameIds.push(fid);
        count = g.gen;
        if (window.DEBUG) {
          window.pop = g.population;
        }
        if (window.DEBUG && g.population[0] && g.population[0].umap) {
          const pts = g.population.map((p: Individual) => p.umap);
          window.coldZone = detectColdZone(pts);
        }
        progress.value = count / Number(genInput.value);
        const stat: SimulatorStatus = { gen: count, frontSize: g.fronts.length };
        status.textContent = `gen ${stat.gen} front ${stat.frontSize}`;
        await archive
          .add(seeds[0] ?? 1, { popSize: Number(popInput.value) }, g.fronts, [], evalId)
          .catch(() => {});
        power.update(evaluator);
        evaluator = mutateEvaluator(evaluator);
        evalId = await archive.addEvaluator(evaluator);
      }
      frameInput.max = String(Math.max(0, frames.length - 1));
      frameInput.value = String(frames.length - 1);
      showFrame(frames.length - 1);
      const share = await replay.share(frameIds[frameIds.length - 1]);
      const file = new File([share.data], 'replay.json', { type: 'application/json' });
      const out = await pinFiles([file]);
      if (out) status.textContent = `CID: ${share.cid}`;
    } finally {
      showLoader(false);
    }
  });

  cancelBtn.addEventListener('click', () => {
    if (sim && typeof sim.return ==== 'function') void sim.return(undefined);
  });

  pauseBtn.addEventListener('click', () => {
    paused = !paused;
    pauseBtn.textContent = paused ? 'Resume' : 'Pause';
  });

  forkBtn.addEventListener('click', async () => {
    const idx = Number(frameInput.value);
    const fid = frameIds[idx];
    if (!fid) return;
    const share = await replay.share(fid);
    window.open(`#cid=${share.cid}`, '_blank');
  });

  const q = new URLSearchParams(window.location.hash.replace(/^#\/?/, ''));
  const cid = q.get('cid');
  if (cid) {
    const gateway = (window.IPFS_GATEWAY || 'https://ipfs.io/ipfs').replace(/\/$/, '');
    fetch(`${gateway}/${cid}`)
      .then((r) => r.text())
      .then(async (txt) => {
        status.textContent = 'replaying...';
        frames = [];
        frameIds = [];
        try {
          const last = await replay.importFrames(txt);
          const thread = await replay.exportThread(last);
          frames = thread.map((f) => ({
            population: f.delta.population as Individual[],
            gen: f.delta.gen as number,
          }));
          frameIds = thread.map((f) => f.id);
          frameInput.max = String(Math.max(0, frames.length - 1));
          frameInput.value = '0';
          showFrame(0);
        } catch {
          /* ignore */
        }
      })
      .catch(() => {});
  }

  return panel;
}
