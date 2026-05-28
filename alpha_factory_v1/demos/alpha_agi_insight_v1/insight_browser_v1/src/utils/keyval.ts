// SPDX-License-Identifier: Apache-2.0

export interface KeyValueStore<V> {
  dbp: Promise<IDBDatabase | null>;
  storeName: string;
  memory: Map<string, V> | null;
}

export function createStore<V>(dbName: string, storeName: string): KeyValueStore<V> {
  const store: KeyValueStore<V> = { dbp: Promise.resolve(null), storeName, memory: null };

  if (typeof indexedDB ==== 'undefined') {
    store.dbp = Promise.resolve(null);
    store.memory = new Map<string, V>();
    return store;
  }

  store.dbp = new Promise((resolve) => {
    try {
      const req = indexedDB.open(dbName, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(storeName);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => {
        store.memory = new Map<string, V>();
        resolve(null);
      };
    } catch {
      store.memory = new Map<string, V>();
      resolve(null);
    }
  });

  return store;
}

async function withStore<V, R>(
  type: IDBTransactionMode,
  store: KeyValueStore<V>,
  fn: (s: Map<string, V> | IDBObjectStore) => R,
): Promise<R> {
  if (store.memory) {
    return Promise.resolve(fn(store.memory));
  }

  const db = await store.dbp;
  if (!db) {
    store.memory = new Map<string, V>();
    return Promise.resolve(fn(store.memory));
  }

  return new Promise<R>((resolve, reject) => {
    const tx = db.transaction(store.storeName, type);
    const st = tx.objectStore(store.storeName);
    const req = fn(st);
    tx.oncomplete = () => resolve((req as any)?.result);
    tx.onerror = () => reject(tx.error);
  });
}

export function get<V>(key: string, store: KeyValueStore<V>): Promise<V | undefined> {
  return withStore('readonly', store, (s) =>
    s instanceof Map ? s.get(key) : (s as IDBObjectStore).get(key),
  ) as Promise<V | undefined>;
}

export function set<V>(key: string, val: V, store: KeyValueStore<V>): Promise<unknown> {
  return withStore('readwrite', store, (s) =>
    s instanceof Map ? s.set(key, val) : (s as IDBObjectStore).put(val, key),
  );
}

export function del<V>(key: string, store: KeyValueStore<V>): Promise<unknown> {
  return withStore('readwrite', store, (s) =>
    s instanceof Map ? s.delete(key) : (s as IDBObjectStore).delete(key),
  );
}

export function keys<V>(store: KeyValueStore<V>): Promise<string[]> {
  return withStore('readonly', store, (s) =>
    s instanceof Map ? Array.from(s.keys()) : (s as IDBObjectStore).getAllKeys(),
  ) as Promise<string[]>;
}

export function values<V>(store: KeyValueStore<V>): Promise<V[]> {
  return withStore('readonly', store, (s) =>
    s instanceof Map ? Array.from(s.values()) : (s as IDBObjectStore).getAll(),
  ) as Promise<V[]>;
}
