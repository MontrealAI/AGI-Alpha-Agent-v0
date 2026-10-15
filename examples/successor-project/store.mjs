// SPDX-License-Identifier: Apache-2.0
import {canonical} from '../../docs/assets/successor/engine.mjs';
import {validateProject} from './engine.mjs';
export async function openProjectStore({indexedDB=globalThis.indexedDB,name='agialpha.successor-project.v1'}={}){
  if(!indexedDB)throw Error('PROJECT_STORAGE_UNAVAILABLE');
  const db=await new Promise((resolve,reject)=>{let settled=false;const r=indexedDB.open(name,1);r.onupgradeneeded=()=>r.result.createObjectStore('projects',{keyPath:'projectId'});r.onerror=r.onblocked=()=>{settled=true;reject(Error('PROJECT_STORAGE_UNAVAILABLE'));};r.onsuccess=()=>{if(settled)r.result.close();else resolve(r.result);};});
  db.onversionchange=()=>db.close();
  function transaction(mode,fn){return new Promise((resolve,reject)=>{let tx;try{tx=db.transaction('projects',mode);}catch{reject(Error('PROJECT_STORAGE_CLOSED'));return;}let value,reason;tx.oncomplete=()=>resolve(value);tx.onabort=()=>reject(reason||Error('PROJECT_STORAGE_FAILED'));tx.onerror=()=>{};const abort=code=>{reason=Error(code);tx.abort();};try{fn(tx.objectStore('projects'),v=>{value=v;},abort);}catch(e){reason=e;tx.abort();}});}
  async function get(id){const raw=await transaction('readonly',(s,done)=>{const r=s.get(id);r.onsuccess=()=>done(r.result??null);});return raw===null?null:validateProject(raw);}
  return {get,
    async list(){const rows=await transaction('readonly',(s,done,fail)=>{const r=s.getAll(undefined,13);r.onsuccess=()=>r.result.length>12?fail('PROJECT_STORAGE_LIMIT'):done(r.result);});return Promise.all(rows.map(validateProject));},
    async save(raw,expected=null){
      const next=await validateProject(raw);const prior=await get(next.projectId);
      if(expected!==null&&(!prior||prior.revision!==expected.revision||prior.projectDigest!==expected.digest||next.revision!==expected.revision+1))throw Error('PROJECT_REVISION_CONFLICT');
      if(expected===null&&prior!==null)throw Error('PROJECT_IMPORT_CONFLICT');
      return transaction('readwrite',(s,done,fail)=>{const r=s.get(next.projectId);r.onsuccess=()=>{try{
        if(canonical(r.result??null)!==canonical(prior)){fail('PROJECT_REVISION_CONFLICT');return;}
        const write=()=>{try{s.put(next);done(next);}catch{fail('PROJECT_STORAGE_FAILED');}};if(prior===null){const count=s.count();count.onsuccess=()=>count.result>=12?fail('PROJECT_STORAGE_LIMIT'):write();}else write();
      }catch{fail('PROJECT_STORAGE_FAILED');}};});
    },close(){db.close();}};
}
