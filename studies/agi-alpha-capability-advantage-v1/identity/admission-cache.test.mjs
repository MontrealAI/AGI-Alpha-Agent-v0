// SPDX-License-Identifier: Apache-2.0
// Software controls only; these do not count as production jobs or skills.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp,copyFile,rm} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {test} from 'node:test';
import {createCapabilityStore,DEFAULT_POLICY} from './capability-store.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=async p=>JSON.parse(await readFile(path.join(ROOT,p),'utf8'));
const receipt=await read('evidence/admission-cached/catalog-admission.json');
const fixture=await read('identity/authority-fixtures.json');
const config=await read('identity/catalog.json');
const clone=value=>JSON.parse(JSON.stringify(value));
const source=receipt.verifierSource;
let callbackCalls=0;
const forbidden=async()=>{callbackCalls++;throw Error('CACHED_REUSE_MUST_NOT_REEXECUTE_ADMISSION');};
function store(extra={}){
  return createCapabilityStore({rootDirectory:ROOT,fixture,verifier:forbidden,compositionVerifier:forbidden,
    verifierSource:source,compositionVerifierSource:source,cachedState:receipt.state,
    expectedCachedStateSha256:receipt.stateSha256,
    executionPolicy:{mode:'LOCAL_RESEARCH_ONLY',nativeAuthority:[],allowedSkills:config.skills.map(x=>x.id+'@'+x.version),maxRuns:1,expiresAt:9000},
    ...extra});
}
function select(instance,family,strategy='registry'){
  const record=receipt.state.records.find(x=>x.dossier.id===family&&x.dossier.version===(family==='design'?'2':'1'));
  return instance.select(family+'-result',{strategy,scopeDigest:record.binding.scopeDigest,
    environmentDigest:record.binding.environmentDigest,rightsDigest:record.binding.rightsDigest,
    expectedRoot:receipt.epoch.root.graphRoot});
}

test('cached validated state restores without calling either admission callback',()=>{
  const current=store();assert.equal(select(current,'forward').ok,true);assert.equal(callbackCalls,0);
});
test('registry and graph select the same active contributed composition',()=>{
  const left=select(store(),'design','registry'),right=select(store(),'design','graph');
  assert.equal(left.ok,true);assert.equal(right.ok,true);
  assert.deepEqual(left.selected,['forward@1','inverse@1','design@2']);
  assert.deepEqual(left.selected,right.selected);assert.equal(callbackCalls,0);
});
test('cached state mutation cannot reuse its original trusted identity',()=>{
  const changed=clone(receipt.state);changed.records[0].validation.accepted=false;
  assert.throws(()=>store({cachedState:changed}),/TRUSTED_CACHED_STATE_IDENTITY_REQUIRED/);
});
test('cached state cannot migrate to a different validation policy',()=>{
  assert.throws(()=>store({policy:{...DEFAULT_POLICY,id:'different-policy'}}),/CACHED_STATE_CONTEXT_MISMATCH/);
});
test('cached source drift refuses selection even with the original receipt',async()=>{
  const temporary=await mkdtemp(path.join(ROOT,'audit/cache-source-control-'));
  try{
    for(const item of receipt.inputManifest){
      const target=path.join(temporary,item.path);await mkdir(path.dirname(target),{recursive:true});
      await copyFile(path.join(ROOT,item.path),target);
    }
    const current=store({rootDirectory:temporary});
    await writeFile(path.join(temporary,'skills/core.py'),'# replaced after admission\n');
    const answer=select(current,'forward');assert.equal(answer.ok,false);assert.match(answer.reason,/FILE_IDENTITY_CHANGED/);
  }finally{await rm(temporary,{recursive:true,force:true});}
});
test('serialized selection is not execution permission',()=>{
  const current=store(),chosen=select(current,'forward');
  assert.throws(()=>current.authorizeLocalExecution(clone(chosen),{missionId:'software-control'}),/CURRENT_SELECTION_REQUIRED/);
});
test('cached admission retains a separate finite local execution budget',()=>{
  const current=store(),chosen=select(current,'forward');
  assert.equal(current.authorizeLocalExecution(chosen,{missionId:'software-control'}).mode,'LOCAL_RESEARCH_ONLY');
  assert.throws(()=>current.authorizeLocalExecution(chosen,{missionId:'software-control-repeat'}),/EXECUTION_BUDGET_EXHAUSTED/);
});

const development=await read('workloads/development/tasks/DEV-FORWARD.json');
async function inspect(task){
  const temporary=await mkdtemp(path.join(ROOT,'audit/domain-control-')),file=path.join(temporary,'task.json');
  try{
    const raw=JSON.stringify(task)+'\n';await writeFile(file,raw);
    let output;
    try{output=execFileSync('python3',[path.join(ROOT,'identity/runtime_context.py'),file],
      {encoding:'utf8',env:{...process.env,OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1',MKL_NUM_THREADS:'1'}});}
    catch(error){output=error.stdout;}
    return {answer:JSON.parse(output),raw};
  }finally{await rm(temporary,{recursive:true,force:true});}
}
test('actual job check binds exact bytes and measured runtime with provisional scope',async()=>{
  const {answer,raw}=await inspect(development);assert.equal(answer.accepted,true);
  assert.equal(answer.jobSha256,createHash('sha256').update(raw).digest('hex'));
  assert.deepEqual(answer.runtime,receipt.runtime);assert.equal(answer.thisJobNumericalAcceptance,'PENDING');
  assert.equal(answer.permission,'PROSPECTIVE_BOUNDED_RESEARCH_TRIAL');
  assert.deepEqual(answer.empiricalAdmissionNodeCounts,[225,400]);assert.deepEqual(answer.nativeAuthority,[]);
});
for(const [name,change,reason] of [
  ['unknown schema',task=>{task.schema='unknown';},'UNSUPPORTED_SCHEMA'],
  ['unsupported family',task=>{task.family='arbitrary-code';},'UNSUPPORTED_FAMILY'],
  ['oversized job',task=>{task.network.node_count=4097;},'NODE_SCOPE'],
  ['missing declared synthetic provenance',task=>{task.provenance.data_class='unknown';},'SYNTHETIC_RESEARCH_RIGHTS_REQUIRED'],
  ['invalid numeric load',task=>{task.loads[0][0]=null;},'LOAD_SCOPE'],
  ['ungrounded components',task=>{task.network.ground.fill(0);},'UNGROUNDED_COMPONENT']
])test('actual job check refuses '+name,async()=>{
  const task=clone(development);change(task);const {answer}=await inspect(task);
  assert.equal(answer.accepted,false);assert.match(answer.reason,new RegExp(reason));
});
