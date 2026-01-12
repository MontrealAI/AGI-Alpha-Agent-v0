// SPDX-License-Identifier: Apache-2.0

export function createStore(dbName, storeName) {
  const store = { dbp: Promise.resolve(null), storeName, memory: null };

  if (typeof indexedDB === 'undefined') {
    store.dbp = Promise.resolve(null);
    store.memory = new Map();
    return store;
  }

  store.dbp = new Promise((resolve) => {
    try {
      const req = indexedDB.open(dbName, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(storeName);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => {
        store.memory = new Map();
        resolve(null);
      };
    } catch {
      store.memory = new Map();
      resolve(null);
    }
  });

  return store;
}

async function withStore(type, store, fn) {
  if (store.memory) {
    return Promise.resolve(fn(store.memory));
  }

  const db = await store.dbp;
  if (!db) {
    store.memory = new Map();
    return Promise.resolve(fn(store.memory));
  }

  return new Promise((resolve, reject) => {
    const tx = db.transaction(store.storeName, type);
    const st = tx.objectStore(store.storeName);
    const req = fn(st);
    tx.oncomplete = () => resolve(req?.result);
    tx.onerror = () => reject(tx.error);
  });
}

export function get(key, store) {
  return withStore('readonly', store, (s) => (s instanceof Map ? s.get(key) : s.get(key)));
}

export function set(key, val, store) {
  return withStore('readwrite', store, (s) => (s instanceof Map ? s.set(key, val) : s.put(val, key)));
}

export function del(key, store) {
  return withStore('readwrite', store, (s) => (s instanceof Map ? s.delete(key) : s.delete(key)));
}

export function keys(store) {
  return withStore('readonly', store, (s) => (s instanceof Map ? Array.from(s.keys()) : s.getAllKeys()));
}

export function values(store) {
  return withStore('readonly', store, (s) => (s instanceof Map ? Array.from(s.values()) : s.getAll()));
}
