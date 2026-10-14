// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {RecoveryStore} from '../../docs/assets/ascension-wallet/recovery.mjs';
test('storage corruption and write loss fail closed',()=>{
  let raw=null;const storage={getItem:()=>raw,setItem:(k,v)=>{raw=v;}};const store=new RecoveryStore(storage,null);
  store.write({transactions:[]});assert.deepEqual(store.read(),{transactions:[]});
  raw='{';assert.throws(()=>store.read());raw=null;storage.setItem=()=>{};assert.throws(()=>store.write({}),/saved/);
});
test('missing or held browser lock cannot invoke a signing callback',async()=>{
  let calls=0;await assert.rejects(new RecoveryStore({},null).exclusive(()=>calls++),/Web Locks/);
  const held={request:async(k,options,fn)=>fn(null)};
  await assert.rejects(new RecoveryStore({},held).exclusive(()=>calls++),/Another MARK tab/);assert.equal(calls,0);
});
