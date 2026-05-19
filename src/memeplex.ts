// SPDX-License-Identifier: Apache-2.0

export interface Edge {
  from: string;
  to: string;
}

export interface Meme {
  edges: Edge[];
  count: number;
}

const DB_NAME = 'memeplex';
const MEME_STORE = 'memes';

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(MEME_STORE)) db.createObjectStore(MEME_STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function withStore<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDB().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(MEME_STORE, mode);
        const st = tx.objectStore(MEME_STORE);
        const req = fn(st);
        const finalize = (handler: () => void) => {
          handler();
          db.close();
        };
        tx.oncomplete = () => finalize(() => resolve(req.result as T));
        tx.onerror = () => finalize(() => reject(tx.error));
        tx.onabort = () => finalize(() => reject(tx.error));
      }),
  );
}

/**
 * Discover frequently occurring edges across runs.
 *
 * @param runs - Runs containing edge histories.
 * @param minSupport - Minimum run count for an edge to be considered a meme.
 * @returns List of mined memes.
 */
export function mineMemes(runs: Array<{ edges: Edge[] }>, minSupport = 2): Meme[] {
  const counts: Record<string, number> = {};
  for (const r of runs) {
    const seen = new Set<string>();
    for (const e of r.edges) {
      const k = `${e.from}->${e.to}`;
      if (!seen.has(k)) {
        counts[k] = (counts[k] || 0) + 1;
        seen.add(k);
      }
    }
  }
  const memes: Meme[] = [];
  for (const [k, c] of Object.entries(counts)) {
    if (c >= minSupport) {
      const [from, to] = k.split('->');
      memes.push({ edges: [{ from, to }], count: c });
    }
  }
  return memes;
}

/**
 * Persist mined memes in IndexedDB, replacing existing data.
 *
 * @param memes - Memes to store.
 */
export async function saveMemes(memes: Meme[]): Promise<void> {
  await withStore('readwrite', (s) => {
    s.clear();
    for (const m of memes) s.put(m, `${m.edges[0].from}->${m.edges[0].to}`);
    return s.put({}, '__dummy__');
  });
}

/**
 * Load stored memes from IndexedDB.
 *
 * @returns Array of persisted memes.
 */
export async function loadMemes(): Promise<Meme[]> {
  const items = (await withStore<Meme[]>('readonly', (s) => s.getAll())) || [];
  return items.filter((m) => m && m.edges);
}
