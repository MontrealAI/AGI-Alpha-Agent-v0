// SPDX-License-Identifier: Apache-2.0
export interface ReplayDelta {
  [key: string]: any;
}

export interface ReplayFrame {
  id: number;
  parent: number | null;
  delta: ReplayDelta;
  timestamp: number;
}

const DB_NAME = 'replay';
const FRAME_STORE = 'frames';
const HAS_INDEXED_DB = typeof indexedDB !== 'undefined';
const MEMORY_STORE = new Map<number, ReplayFrame>();

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(FRAME_STORE)) db.createObjectStore(FRAME_STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function withStore<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDB().then(
    db => new Promise<T>((resolve, reject) => {
      const tx = db.transaction(FRAME_STORE, mode);
      const st = tx.objectStore(FRAME_STORE);
      const req = fn(st);
      tx.oncomplete = () => resolve(req.result as T);
      tx.onerror = () => reject(tx.error);
    })
  );
}

/**
 * Persistence helper for storing and retrieving replay frames.
 * Each frame links to its parent so threads can be reconstructed.
 */
export class ReplayDB {
  /**
   * Create a new replay database wrapper.
   *
   * @param name - Optional IndexedDB name.
   */
  constructor(private name = DB_NAME) {}

  /** Open the underlying database. */
  async open(): Promise<void> {
    if (HAS_INDEXED_DB) {
      await openDB();
    }
  }

  /**
   * Store a frame and return its generated ID.
   *
   * @param parent - ID of the parent frame or `null` if root.
   * @param delta - Partial state update for this frame.
   * @returns The new frame ID.
   */
  async addFrame(parent: number | null, delta: ReplayDelta): Promise<number> {
    const uuidFn = (globalThis.crypto as Crypto | undefined)?.randomUUID;
    const id =
      typeof uuidFn === 'function'
        ? parseInt(uuidFn.call(globalThis.crypto).replace(/-/g, '').slice(0, 13), 16)
        : Date.now() + Math.floor(Math.random() * 1000);
    const frame: ReplayFrame = { id, parent, delta, timestamp: Date.now() };
    if (HAS_INDEXED_DB) {
      await withStore('readwrite', (s) => s.put(frame, id));
    } else {
      MEMORY_STORE.set(id, frame);
    }
    return id;
  }

  /**
   * Retrieve a frame by ID.
   *
   * @param id - Frame identifier.
   * @returns The stored frame or `undefined`.
   */
  async getFrame(id: number): Promise<ReplayFrame | undefined> {
    if (HAS_INDEXED_DB) {
      return withStore('readonly', (s) => s.get(id));
    }
    return MEMORY_STORE.get(id);
  }

  /**
   * Return the chain of frames ending at `id` in chronological order.
   *
   * @param id - Last frame ID in the thread.
   */
  async exportThread(id: number): Promise<ReplayFrame[]> {
    const out: ReplayFrame[] = [];
    let cur: number | null = id;
    while (cur) {
      const f = await this.getFrame(cur);
      if (!f) break;
      out.unshift(f);
      cur = f.parent;
    }
    return out;
  }

  /**
   * Compute a hex-encoded CID for the given frames.
   */
  static async cidForFrames(frames: ReplayFrame[]): Promise<string> {
    const deltas = frames.map((f) => f.delta);
    const buf = new TextEncoder().encode(JSON.stringify(deltas));
    const hash = await crypto.subtle.digest('SHA-256', buf);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  }

  /**
   * Compute the CID for the thread containing `id`.
   *
   * @param id - Last frame in the thread.
   */
  async computeCid(id: number): Promise<string> {
    const frames = await this.exportThread(id);
    return ReplayDB.cidForFrames(frames);
  }

  /**
   * Export a thread and return its CID and serialized data.
   *
   * @param id - Last frame in the thread to share.
   */
  async share(id: number): Promise<{ cid: string; data: string }> {
    const frames = await this.exportThread(id);
    const cid = await ReplayDB.cidForFrames(frames);
    const data = JSON.stringify(frames.map((f) => ({ parent: f.parent, delta: f.delta })));
    return { cid, data };
  }

  /**
   * Import a JSON thread created by {@link share}.
   *
   * @param json - JSON representation of frames.
   * @returns ID of the last imported frame.
   */
  async importFrames(json: string): Promise<number> {
    const records: Array<{ parent: number | null; delta: ReplayDelta }> = JSON.parse(json);
    let parent: number | null = null;
    let last = 0;
    for (const r of records) {
      last = await this.addFrame(parent, r.delta);
      parent = last;
    }
    return last;
  }
}
