// @ts-nocheck
// SPDX-License-Identifier: Apache-2.0
import { createStore, set, values } from '../utils/keyval.ts';

export async function loadExamples(url = './data/critics/innovations.txt') {
  try {
    const res = await fetch(url);
    if (!res.ok) return [];
    const text = await res.text();
    return text.split(/\n/).map(l => l.trim()).filter(Boolean);
  } catch {
    return [];
  }
}

export class LogicCritic {
  constructor(examples: string[] = [], prompt: string = 'judge logic') {
    this.examples = examples;
    this.prompt = prompt;
    this.index = {};
    this.examples.forEach((e, i) => {
      this.index[e.toLowerCase()] = i;
    });
    this.scale = Math.max(this.examples.length - 1, 1);
  }

  score(genome) {
    const key = String(genome).toLowerCase();
    const pos = this.index[key] ?? -1;
    const base = pos >= 0 ? (pos + 1) / (this.scale + 1) : 0;
    const noise = Math.random() * 0.001;
    const val = base + noise;
    return Math.min(1, Math.max(0, val));
  }
}

export class FeasibilityCritic {
  constructor(examples: string[] = [], prompt: string = 'judge feasibility') {
    this.examples = examples;
    this.prompt = prompt;
  }

  static jaccard(a, b) {
    const sa = new Set(a);
    const sb = new Set(b);
    if (!sa.size || !sb.size) return 0;
    let inter = 0;
    for (const x of sa) if (sb.has(x)) inter++;
    const union = new Set([...a, ...b]).size;
    return inter / union;
  }

  score(genome) {
    const tokens = String(genome).toLowerCase().split(/\s+/);
    let best = 0;
    for (const ex of this.examples) {
      const sim = FeasibilityCritic.jaccard(tokens, ex.toLowerCase().split(/\s+/));
      if (sim > best) best = sim;
    }
    const noise = Math.random() * 0.001;
    const val = best + noise;
    return Math.min(1, Math.max(0, val));
  }
}

export class JudgmentDB {
  constructor(name: string = 'critic-judgments') {
    this.store = createStore(name, 'judgments');
  }

  async add(genome, scores) {
    await set(Date.now() + Math.random(), { genome, scores }, this.store);
  }

  async querySimilar(genome) {
    const all = await values(this.store);
    const tokens = String(genome).toLowerCase().split(/\s+/);
    let best = null;
    let bestSim = -1;
    for (const rec of all) {
      const sim = FeasibilityCritic.jaccard(tokens, rec.genome.toLowerCase().split(/\s+/));
      if (sim > bestSim) {
        bestSim = sim;
        best = rec;
      }
    }
    return best;
  }
}

export function mutatePrompt(prompt: string, rand: () => number = Math.random): string {
  const words = ['insightful', 'detailed', 'robust', 'novel'];
  const tokens = prompt.split(/\s+/);
  if (rand() < 0.5 && tokens.length > 1) {
    tokens.splice(Math.floor(rand() * tokens.length), 1);
  } else {
    const w = words[Math.floor(rand() * words.length)];
    tokens.splice(Math.floor(rand() * (tokens.length + 1)), 0, w);
  }
  return tokens.join(' ');
}

export function consilience(scores: Record<string, number>): number {
  const vals = Object.values(scores);
  const avg = vals.reduce((s, v) => s + v, 0) / vals.length;
  const sd = Math.sqrt(vals.reduce((s, v) => s + (v - avg) ** 2, 0) / vals.length);
  return 1 - sd;
}

export async function scoreGenome(
  genome: string,
  critics: Array<{ score: (g: string) => number; prompt?: string }>,
  db?: JudgmentDB,
  threshold = 0.6,
): Promise<{ scores: Record<string, number>; cons: number }> {
  const scores = {};
  for (const c of critics) {
    scores[c.constructor.name] = c.score(genome);
  }
  const past = db ? await db.querySimilar(genome) : null;
  if (past) {
    for (const k of Object.keys(scores)) {
      if (past.scores[k] !== undefined) {
        scores[k] = (scores[k] + past.scores[k]) / 2;
      }
    }
  }
  if (db) await db.add(genome, scores);
  const cons = consilience(scores);
  if (cons < threshold) {
    for (const c of critics) if (c.prompt) c.prompt = mutatePrompt(c.prompt);
    if (typeof window !== 'undefined') {
      window.recordedPrompts = critics.map(c => c.prompt);
    }
  }
  return { scores, cons };
}

if (typeof window !== 'undefined') {
  window.JudgmentDB = JudgmentDB;
  window.consilience = consilience;
  window.scoreGenome = scoreGenome;
  window.LogicCritic = LogicCritic;
  window.FeasibilityCritic = FeasibilityCritic;
}
