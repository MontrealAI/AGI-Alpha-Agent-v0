// SPDX-License-Identifier: Apache-2.0
import {inspectJourney} from './journey.mjs';
import {canonical} from './journey-codec.mjs';
export async function openJourneyStore(receivers, {indexedDB=globalThis.indexedDB,name='agialpha.guided-project.v1'}={}) {
  if (!indexedDB) throw Error('JOURNEY_STORAGE_UNAVAILABLE');
  const db = await new Promise((resolve,reject) => {
    let settled=false;const request=indexedDB.open(name,1);
    request.onupgradeneeded=()=>request.result.createObjectStore('journeys',{keyPath:'projectId'});
    request.onerror=request.onblocked=()=>{settled=true;reject(Error('JOURNEY_STORAGE_UNAVAILABLE'));};
    request.onsuccess=()=>{if(settled)request.result.close();else resolve(request.result);};
  });
  db.onversionchange=()=>db.close();
  function transaction(mode, operation) {
    return new Promise((resolve,reject)=>{
      let tx,reason,result;
      try {tx=db.transaction('journeys',mode);} catch {reject(Error('JOURNEY_STORAGE_CLOSED'));return;}
      tx.oncomplete=()=>resolve(result);tx.onabort=()=>reject(reason??Error('JOURNEY_STORAGE_FAILED'));tx.onerror=()=>{};
      const abort=code=>{reason=Error(code);tx.abort();};
      try {operation(tx.objectStore('journeys'),value=>{result=value;},abort);} catch (error) {reason=error;tx.abort();}
    });
  }
  async function read(projectId) {
    return transaction('readonly',(store,done)=>{const request=store.get(projectId);request.onsuccess=()=>done(request.result?.raw??null);});
  }
  return {
    async get(projectId) {const raw=await read(projectId);if(raw!==null)await inspectJourney(raw,receivers);return raw;},
    async save(raw, expected=null) {
      const checked=await inspectJourney(raw,receivers), prior=await read(checked.project.projectId);
      if(prior!==expected)throw Error('JOURNEY_REVISION_CONFLICT');
      if(prior!==null){
        const old=await inspectJourney(prior,receivers),before=old.journey.history,after=checked.journey.history;
        if(after.length<=before.length||canonical(after.slice(0,before.length))!==canonical(before))throw Error('JOURNEY_HISTORY_REWRITTEN');
      }
      return transaction('readwrite',(store,done,abort)=>{
        const request=store.get(checked.project.projectId);
        request.onsuccess=()=>{
          if((request.result?.raw??null)!==prior){abort('JOURNEY_REVISION_CONFLICT');return;}
          const write=()=>{try{store.put({projectId:checked.project.projectId,raw});done(raw);}catch{abort('JOURNEY_STORAGE_FAILED');}};
          if(prior===null){const count=store.count();count.onsuccess=()=>count.result>=12?abort('JOURNEY_STORAGE_LIMIT'):write();}
          else write();
        };
      });
    },
    close(){db.close();},
  };
}
