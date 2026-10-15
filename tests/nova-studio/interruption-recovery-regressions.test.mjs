// SPDX-License-Identifier: Apache-2.0
// Synthetic portable-history associations; real browser/EVM drills are separate.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {WalletSession} from '../../docs/assets/ascension-wallet/session.mjs';
import {NovaWorkflow} from '../../docs/assets/nova-studio/workflow.mjs';
import {createPackage} from '../../docs/assets/nova-studio/package.mjs';
import {createProject,updateCycle,addCycle,exportProjectKit} from '../../docs/assets/nova-studio/cycle.mjs';
import {callData} from '../../docs/assets/ascension-wallet/protocol.mjs';

const profile=JSON.parse(fs.readFileSync(new URL('../../docs/assets/ascension-wallet/profile.json',import.meta.url)));
const passphrase='synthetic successor interruption passphrase';
const draft={title:'Parent',description:'Synthetic recovery association',evidence:'Local only',
  jobs:[{goal:'First input',successMetric:'Exact output',bounty:'1000',duration:3600,priceWeight:5000}]};
function session() {
  const values=new Map();
  return new WalletSession(profile,{getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value)},
    {request:async(_name,_options,callback)=>callback({})});
}
async function successorKit(seedIds,{foreign=false}={}) {
  const client=session().client;
  const first=await createPackage(draft,passphrase,foreign?{...profile,profile:profile.profile+'-foreign'}:profile);
  const transactions=seedIds.map((seedId,index)=>({schema:'agialpha.mark-wallet-transaction.v2',action:'reclaim',args:[seedId],
    chainId:profile.chainId,createdAt:'2026-10-14T00:00:00.000Z',status:'finalized',hash:'0x'+String(index+1).repeat(64),
    transaction:{from:'0x'+'11'.repeat(20),to:client.contracts.Mark,data:callData('reclaim',[seedId]),value:'0x0',
      chainId:client.chainId,nonce:'0x'+index.toString(16),gas:'0x100000'}}));
  const journal={...client.journal(),transactions};
  let project=await createProject(first);
  // NovaWorkflow.nextCycle syncs the shared journal into the old cycle first.
  project=await updateCycle(project,project.activeCycleId,{seedId:'7',journal});
  const next=await createPackage({...draft,parent:foreign?'0':'7',title:'Successor',
    jobs:[{...draft.jobs[0],goal:'Distinct input'}]},passphrase,profile);
  project=await addCycle(project,next);
  project=await updateCycle(project,project.activeCycleId,{journal});
  return {project,kit:JSON.stringify(await exportProjectKit(project,passphrase))};
}

test('unminted successor restores a shared parent-cycle journal without granting current authority',async()=>{
  const {project,kit}=await successorKit(['7']), flow=new NovaWorkflow(session(),{});
  await flow.restoreProject(kit,passphrase);
  assert.deepEqual(flow.project,project);assert.equal(flow.seedId,null);
  assert.equal(flow.project.cycles.length,2);assert.equal(flow.client.provider,null);assert.equal(flow.client.account,null);
  assert.equal(flow.client.pending.status,'submission-unknown');assert.equal(flow.runtimeTrust,null);
  await assert.rejects(flow.prepare('reclaim',{}),/outstanding/);
});

test('unrelated imported journal cannot acquire a successor association',async()=>{
  const {kit}=await successorKit(['8']), flow=new NovaWorkflow(session(),{});
  await assert.rejects(flow.restoreProject(kit,passphrase),/exact package.*unresolved/);
  assert.equal(flow.client.pending.status,'submission-unknown');assert.equal(flow.package,null);
});

test('recognized parent association never discards another unresolved shared transaction',async()=>{
  const {kit}=await successorKit(['7','8']), flow=new NovaWorkflow(session(),{});
  await flow.restoreProject(kit,passphrase);
  assert.equal(flow.client.history.length,2);
  assert.ok(flow.client.history.every(record=>record.status==='submission-unknown'));
  await assert.rejects(flow.prepare('reclaim',{}),/outstanding/);
});


test('foreign retained parent deployment cannot associate a selected-profile journal',async()=>{
  const {kit}=await successorKit(['7'],{foreign:true}), flow=new NovaWorkflow(session(),{});
  await assert.rejects(flow.restoreProject(kit,passphrase),/exact package.*unresolved/);
  assert.equal(flow.client.pending.status,'submission-unknown');assert.equal(flow.package,null);
});
