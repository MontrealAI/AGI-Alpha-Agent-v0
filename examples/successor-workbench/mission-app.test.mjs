// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import * as records from './mission-record.mjs';
import * as workbench from './engine.mjs';
const source=fs.readFileSync(new URL('../../scripts/templates/successor-mission/app.js',import.meta.url),'utf8')+fs.readFileSync(new URL('../../scripts/templates/successor-mission/project.js',import.meta.url),'utf8');
const marker='(async()=>{try{db=';
assert.equal(source.split(marker).length,2,'test must retain the real bootstrap boundary');
const sourceHash='a'.repeat(64);
async function harness({failWrite=0,failList=0,code='LOCAL_REVISION_CONFLICT',hold=false,boot=false,runningRecord=false}={}){
  let initial=await records.createRecord({missionId:'test-mission',sourceHash,spec:workbench.example('public-data')});
  if(runningRecord)initial=await records.startRun(initial,{expectedRevision:0,runId:'interrupted-run'});
  let stored=initial,writes=0,lists=0,closed=false,engineCalls=0,release;
  const blocked=new Promise(resolve=>{release=resolve;});
  const elements=new Map();
  const element=id=>elements.get(id)||elements.set(id,{value:'',textContent:'',disabled:false,hidden:false,dataset:{},
    addEventListener(){},setAttribute(){},replaceChildren(){},append(){},click(){}}).get(id);
  const db={close(){closed=true;},async get(){return stored;},async save(next,expected){
    writes++;if(writes===failWrite)throw Object.assign(Error(code),{code});
    assert.equal(stored.revision,expected);stored=next;
  },async list(){lists++;if(lists===failList)throw Object.assign(Error('corrupt'),{code:'LOCAL_RECORD_CORRUPT'});return[stored];}};
  const engine={...workbench,async run(...args){engineCalls++;if(hold){await blocked;throw Error('CANCELLED');}return workbench.run(...args);}};
  const context=vm.createContext({document:{getElementById:element,querySelectorAll:()=>[],createElement:()=>element('created')},
    records,workbench:engine,storage:{async openMissionStore(){return db;}},crypto,AbortController,URL,Blob,setTimeout,console,
    TextEncoder,TextDecoder,SOURCE_HASH:sourceHash,initial,testdb:db});
  const hooks=`\nglobalThis.hooks={run,stop,operation,openSaved,state:()=>({active:!!active,busy,readOnly,mode,pendingRun,stopping,unpersisted,hasDB:!!db,current})};`;
  vm.runInContext(boot?source+hooks:source.split(marker)[0]+'\ncurrent=initial;db=testdb;ready=true;'+hooks,context);
  if(boot)await new Promise(resolve=>setTimeout(resolve,0));
  return {hooks:context.hooks,element,release,stored:()=>stored,engineCalls:()=>engineCalls,closed:()=>closed};
}
for(const code of ['LOCAL_REVISION_CONFLICT','LOCAL_STORAGE_WRITE_FAILED']){
  for(const phase of ['start','completion','stop'])test(`${phase} ${code} retains recoverable read-only copy`,async()=>{
    const h=await harness({failWrite:phase==='start'?1:2,code,hold:phase==='stop'});
    const running=h.hooks.run();
    if(phase==='stop'){
      for(let i=0;!h.hooks.state().active&&i<100;i++)await new Promise(resolve=>setTimeout(resolve,1));
      assert.equal(h.hooks.state().active,true);await h.hooks.stop();h.release();
    }
    await running;
    const state=h.hooks.state();
    assert.equal(state.active,false);assert.equal(state.pendingRun,false);assert.equal(state.stopping,false);
    assert.equal(state.readOnly,true);assert.equal(state.unpersisted,true);
    assert.equal(h.element('run').disabled,true);assert.equal(h.element('open').disabled,false);
    assert.equal(h.element('import').disabled,false);assert.equal(h.element('export').disabled,false);
    let exported=false;await h.hooks.operation(async()=>{await records.serializeRecord(state.current);exported=true;});
    assert.equal(exported,true,'export operation must actually run');
    assert.equal(h.stored().revision,phase==='start'?0:1,'failed write cannot overwrite retained state');
    if(phase==='start')assert.equal(h.engineCalls(),0);
  });
}
test('corrupt initial storage closes execution and retains historical import access',async()=>{
  const h=await harness({failList:1,boot:true});const state=h.hooks.state();
  assert.equal(h.closed(),true);assert.equal(state.hasDB,false);assert.equal(state.readOnly,true);
  assert.equal(h.element('new').disabled,true);assert.equal(h.element('run').disabled,true);
  assert.equal(h.element('import').disabled,false);assert.equal(h.engineCalls(),0);
});
test('post-commit index corruption preserves acknowledged record but blocks execution',async()=>{
  const h=await harness({failList:1});await h.hooks.run();const state=h.hooks.state();
  assert.equal(h.closed(),true);assert.equal(state.hasDB,false);assert.equal(state.readOnly,true);
  assert.equal(state.unpersisted,false);assert.equal(h.stored().revision,1);
  assert.equal(h.engineCalls(),0);assert.equal(h.element('new').disabled,true);
  assert.equal(h.element('export').disabled,false);
});

test('reopening a persisted running record never resumes execution automatically',async()=>{
  const h=await harness({runningRecord:true,boot:true});
  await h.hooks.openSaved();
  assert.equal(h.hooks.state().current.state,'running');
  assert.equal(h.engineCalls(),0);assert.equal(h.element('run').disabled,true);
  assert.equal(h.element('interrupt').disabled,false);
});
