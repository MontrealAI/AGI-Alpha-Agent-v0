// SPDX-License-Identifier: Apache-2.0
// Transactional local persistence. It grants no execution or marketplace authority.
export const MAX_RECORD_BYTES = 2_000_000;
export const MAX_MISSIONS = 12;

export class MissionStorageError extends Error {
  constructor(code) { super(code); this.name = 'MissionStorageError'; this.code = code; }
}

function envelope(record) {
  if (!record || typeof record !== 'object' || Array.isArray(record) ||
      typeof record.missionId !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(record.missionId) ||
      !Number.isSafeInteger(record.revision) || record.revision < 0) {
    throw new MissionStorageError('INVALID_STORAGE_ENVELOPE');
  }
  const text = JSON.stringify(record);
  if (new TextEncoder().encode(text).length > MAX_RECORD_BYTES) {
    throw new MissionStorageError('LOCAL_RECORD_LIMIT');
  }
  return JSON.parse(text);
}

export async function openMissionStore({ indexedDB = globalThis.indexedDB,
  name = 'agialpha.successor-mission.v1' } = {}) {
  if (!indexedDB) throw new MissionStorageError('LOCAL_STORAGE_UNAVAILABLE');
  const db = await new Promise((resolve, reject) => {
    let request, settled = false;
    const fail = code => { settled = true; reject(new MissionStorageError(code)); };
    try { request = indexedDB.open(name, 1); }
    catch { reject(new MissionStorageError('LOCAL_STORAGE_UNAVAILABLE')); return; }
    request.onupgradeneeded = () => request.result.createObjectStore('missions', { keyPath: 'missionId' });
    request.onerror = () => fail('LOCAL_STORAGE_UNAVAILABLE');
    request.onblocked = () => fail('LOCAL_STORAGE_BLOCKED');
    request.onsuccess = () => {
      if (settled) request.result.close();
      else { settled = true; resolve(request.result); }
    };
  });
  let closed = false;
  db.onversionchange = () => { closed = true; db.close(); };

  function transact(mode, action) {
    return new Promise((resolve, reject) => {
      if (closed) { reject(new MissionStorageError('LOCAL_STORAGE_CLOSED')); return; }
      let tx;
      try { tx = db.transaction('missions', mode); }
      catch { reject(new MissionStorageError('LOCAL_STORAGE_UNAVAILABLE')); return; }
      let value, reason;
      const fail = code => { reason = new MissionStorageError(code); tx.abort(); };
      tx.oncomplete = () => resolve(value);
      tx.onabort = () => reject(reason || new MissionStorageError('LOCAL_STORAGE_WRITE_FAILED'));
      tx.onerror = () => { reason ||= new MissionStorageError('LOCAL_STORAGE_WRITE_FAILED'); };
      try { action(tx.objectStore('missions'), result => { value = result; }, fail); }
      catch (error) { reason = error; tx.abort(); }
    });
  }

  return {
    async get(id) {
      return transact('readonly', (store, done, fail) => {
        const request = store.get(id);
        request.onsuccess = () => {
          try { done(request.result === undefined ? null : envelope(request.result)); }
          catch { fail('LOCAL_RECORD_CORRUPT'); }
        };
      });
    },
    async list() {
      return transact('readonly', (store, done, fail) => {
        const request = store.getAll(undefined, MAX_MISSIONS + 1);
        request.onsuccess = () => {
          try {
            if (request.result.length > MAX_MISSIONS) throw Error('limit');
            done(request.result.map(envelope));
          } catch { fail('LOCAL_RECORD_CORRUPT'); }
        };
      });
    },
    async save(record, expectedRevision = null) {
      const copy = envelope(record);
      if (expectedRevision !== null && (!Number.isSafeInteger(expectedRevision) || expectedRevision < 0)) {
        throw new MissionStorageError('INVALID_EXPECTED_REVISION');
      }
      if (copy.revision !== (expectedRevision === null ? 0 : expectedRevision + 1)) {
        throw new MissionStorageError('INVALID_NEXT_REVISION');
      }
      return transact('readwrite', (store, done, fail) => {
        const request = store.get(copy.missionId);
        request.onsuccess = () => {
          const prior = request.result;
          if (expectedRevision === null ? prior !== undefined : prior?.revision !== expectedRevision) {
            fail('LOCAL_REVISION_CONFLICT'); return;
          }
          const write = () => { store.put(copy); done(copy); };
          if (prior === undefined) {
            const count = store.count();
            count.onsuccess = () => {
              if (count.result >= MAX_MISSIONS) fail('LOCAL_MISSION_LIMIT');
              else write();
            };
          } else write();
        };
      });
    },
    close() { closed = true; db.close(); },
  };
}
