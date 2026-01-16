// SPDX-License-Identifier: Apache-2.0
export interface TaxonomyNode {
  id: string;
  parent: string | null;
}

export interface HyperGraph {
  nodes: Record<string, TaxonomyNode>;
}

/**
 * Mine a taxonomy from a list of insight runs. Each run may define
 * `params.sector` which becomes a node in the taxonomy.
 */
export function mineTaxonomy(runs: Array<{ params?: { sector?: string } }>): HyperGraph {
  const graph: HyperGraph = { nodes: {} };
  for (const r of runs) {
    const sec = r.params?.sector;
    if (sec && !graph.nodes[sec]) {
      graph.nodes[sec] = { id: sec, parent: null };
    }
  }
  return graph;
}

/**
 * Remove nodes not present in `valid`.
 */
export function pruneTaxonomy(graph: HyperGraph, valid: Set<string>): HyperGraph {
  const out: HyperGraph = { nodes: {} };
  for (const id of valid) {
    const n = graph.nodes[id];
    if (n) out.nodes[id] = n;
  }
  return out;
}

const DB_NAME = 'sectorTaxonomy';
const NODE_STORE = 'nodes';
const META_STORE = 'meta';
const VERSION_KEY = 'version';
const CURRENT_VERSION = 1;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(NODE_STORE)) db.createObjectStore(NODE_STORE);
      if (!db.objectStoreNames.contains(META_STORE)) db.createObjectStore(META_STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function withStore<T>(mode: IDBTransactionMode, store: string, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDB().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(store, mode);
        const st = tx.objectStore(store);
        const req = fn(st);
        tx.oncomplete = () => resolve(req.result as T);
        tx.onerror = () => reject(tx.error);
      }),
  );
}

export async function saveTaxonomy(graph: HyperGraph): Promise<void> {
  await withStore('readwrite', NODE_STORE, (s) => {
    s.clear();
    for (const n of Object.values(graph.nodes)) s.put(n, n.id);
    return s.put(0, '__dummy__');
  });
  await withStore('readwrite', META_STORE, (s) => s.put(CURRENT_VERSION, VERSION_KEY));
}

export async function loadTaxonomy(): Promise<HyperGraph> {
  const version = await withStore<number>('readonly', META_STORE, (s) => s.get(VERSION_KEY));
  if (version !== CURRENT_VERSION) {
    await withStore('readwrite', NODE_STORE, (s) => {
      s.clear();
      return s.put(0, '__dummy__');
    });
    await withStore('readwrite', META_STORE, (s) => s.put(CURRENT_VERSION, VERSION_KEY));
    return { nodes: {} };
  }
  const nodes = (await withStore< TaxonomyNode[] >('readonly', NODE_STORE, (s) => s.getAll())) || [];
  const out: HyperGraph = { nodes: {} };
  for (const n of nodes) {
    if (n && n.id) out.nodes[n.id] = { id: n.id, parent: n.parent ?? null };
  }
  return out;
}

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((t) => t);
}

function toVector(tokens: string[]): Record<string, number> {
  const vec: Record<string, number> = {};
  for (const t of tokens) vec[t] = (vec[t] || 0) + 1;
  return vec;
}

function cosine(a: Record<string, number>, b: Record<string, number>): number {
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (const k in a) {
    dot += (a[k] || 0) * (b[k] || 0);
    na += a[k] * a[k];
  }
  for (const k in b) nb += b[k] * b[k];
  if (!na || !nb) return 0;
  return dot / Math.sqrt(na * nb);
}

function jaccard(a: Set<string>, b: Set<string>): number {
  const inter = new Set([...a].filter((x) => b.has(x))).size;
  const union = new Set([...a, ...b]).size;
  if (!union) return 0;
  return inter / union;
}

export function clusterKeywords(
  runs: Array<{ keywords: string[] }>,
  thresh = 0.6,
): string[][] {
  const kwRuns: Record<string, Set<string>> = {};
  runs.forEach((r, i) => {
    for (const k of r.keywords || []) {
      kwRuns[k] = kwRuns[k] || new Set();
      kwRuns[k].add(String(i));
    }
  });
  const keys = Object.keys(kwRuns);
  const clusters: string[][] = [];
  const used = new Set<string>();
  for (let i = 0; i < keys.length; i++) {
    const a = keys[i];
    if (used.has(a)) continue;
    const group = [a];
    used.add(a);
    for (let j = i + 1; j < keys.length; j++) {
      const b = keys[j];
      if (used.has(b)) continue;
      if (jaccard(kwRuns[a], kwRuns[b]) >= thresh) {
        group.push(b);
        used.add(b);
      }
    }
    clusters.push(group);
  }
  return clusters;
}

export async function validateLabel(name: string): Promise<boolean> {
  try {
    // @ts-ignore - optional alias provided by the Insight build pipeline
    const { chat } = await import('@insight-src/utils/llm.js');
    const resp = await chat(`Does '${name}' denote a distinct economic activity?`);
    return /^yes/i.test(String(resp).trim());
  } catch {
    return false;
  }
}

function bestParent(label: string, graph: HyperGraph): [string | null, number] {
  const vec = toVector(tokenize(label));
  let best: string | null = null;
  let score = 0;
  for (const n of Object.values(graph.nodes)) {
    if (!n.id) continue;
    const sim = cosine(vec, toVector(tokenize(n.id)));
    if (sim > score) {
      score = sim;
      best = n.id;
    }
  }
  return [best, score];
}

export async function proposeSectorNodes(
  runs: Array<{ keywords: string[] }>,
  graph: HyperGraph,
): Promise<HyperGraph> {
  const clusters = clusterKeywords(runs, 0.6);
  for (const c of clusters) {
    const name = c.join(' ');
    if (graph.nodes[name]) continue;
    if (!(await validateLabel(name))) continue;
    const [parent, sim] = bestParent(name, graph);
    if (parent && sim > 0.9) continue;
    graph.nodes[name] = { id: name, parent: sim > 0.3 ? parent : null };
  }
  await saveTaxonomy(graph);
  return graph;
}
