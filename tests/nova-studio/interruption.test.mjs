// SPDX-License-Identifier: Apache-2.0
// Synthetic persisted checkpoints with a new process at every point. These are
// deterministic portable-recovery checks, not an all-stage EVM/browser crash drill.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { spawnSync } from 'node:child_process';
import { WalletSession } from '../../docs/assets/ascension-wallet/session.mjs';
import { ACTIONS, callData, parseFields } from '../../docs/assets/ascension-wallet/protocol.mjs';
import { NovaWorkflow } from '../../docs/assets/nova-studio/workflow.mjs';
import { createPackage, fileBytes, hashBytes } from '../../docs/assets/nova-studio/package.mjs';
import { createProject, updateCycle, addCycle, preserveSignedRecord, exportProjectKit,
  registerMission, freezeEvaluation } from '../../docs/assets/nova-studio/cycle.mjs';

const profile=JSON.parse(fs.readFileSync(new URL('../../docs/assets/ascension-wallet/profile.json',import.meta.url)));
const passphrase='synthetic interruption recovery passphrase';
const A='0x'+'11'.repeat(20), H='0x'+'ab'.repeat(32);
const spec={goal:'Integrate a bounded public polynomial',successMetric:'Retain exact numerical error.',
  bounty:'1000',duration:3600,priceWeight:5000};
const draft={title:'Interruption fixture',description:'No real account, approval, money or participant.',
  jobs:[spec],evidence:'Deterministic local recovery only.'};
const pkg=await createPackage(draft,passphrase,profile);
const uri='ipfs://Qm'+'a'.repeat(44);
const points=['upload','mint','approval','purchase','route','runtime-start','delivery','review',
  'settlement-import','claim','successor'];
function session() {
  const values=new Map();
  return new WalletSession(profile,{getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value)},
    {request:async(_name,_options,callback)=>callback({})});
}
function record(client,action,values,status='awaiting-wallet') {
  const args=parseFields(action,values,client.contracts);
  return {schema:'agialpha.mark-wallet-transaction.v2',action,args,chainId:profile.chainId,
    createdAt:'2026-10-14T00:00:00.000Z',status,hash:status==='finalized'?H:null,effectVerified:true,
    transaction:{from:A,to:client.contracts[ACTIONS[action].contract],data:callData(ACTIONS[action].method,args),
      chainId:client.chainId,nonce:'0x1',gas:'0x100000',value:'0x0'}};
}
function checkFresh(point,project,pending=false) {
  return exportProjectKit(project,passphrase).then(kit=>{
    const child=spawnSync(process.execPath,[new URL('./helpers/fresh-session-recovery.mjs',import.meta.url).pathname],
      {input:JSON.stringify({point,profile,project,draft,kit:JSON.stringify(kit),passphrase,pending}),
        encoding:'utf8',timeout:30000,maxBuffer:4000000});
    assert.equal(child.status,0,child.stderr || String(child.error));
    const result=JSON.parse(child.stdout);
    assert.equal(result.point,point);assert.equal(result.restored,true);assert.equal(result.automaticEffects,0);
  });
}
for (const point of points) test(`fresh-session interruption checkpoint: ${point}`,async()=>{
  let project=await createProject(pkg), pending=false;
  if (point!=='upload' && point!=='mint') project=await updateCycle(project,project.activeCycleId,{seedId:'7',jobIds:['12']});
  const client=session().client;
  const actions={
    mint:['seal',[pkg.capsuleHash,pkg.plan.planRoot,'1',uri,'0',pkg.evidenceHash]],
    approval:['approve',['Mark','0.000000000000001']],
    purchase:['buy',['7','1','0.000000000000001']],
    route:['route',['7','0',JSON.stringify(spec),'[]','60',JSON.stringify([A,'0x'+'22'.repeat(20),'0x'+'33'.repeat(20)])]],
    delivery:['submit',['12',H,uri]],review:['validate',['12',H,'true',H]],claim:['reclaim',['7']],
  };
  if (actions[point]) {
    const [action,args]=actions[point];
    // A forged historical terminal label is as untrusted as an unknown send.
    const status=point==='approval'?'finalized':'awaiting-wallet';
    project=await updateCycle(project,project.activeCycleId,{journal:{...client.journal(),transactions:[record(client,action,args,status)]}});
    pending=true;
  }
  if (['runtime-start','delivery','review','settlement-import','successor'].includes(point)) {
    const request={schema:'agialpha.ascension.studio-work.v1',project_id:project.projectId,cycle_id:project.activeCycleId,
      plan:pkg.plan,plan_index:0,work_spec:{inputs:{coefficients:[0,0,1]},goal:spec.goal}};
    project=await registerMission(project,project.activeCycleId,{request});
    project=await preserveSignedRecord(project,{kind:'preposting',originalText:'{ "synthetic": "preposting checkpoint" }\n'});
  }
  if (['delivery','review','settlement-import','successor'].includes(point))
    project=await preserveSignedRecord(project,{kind:'runtime-run',originalText:'{ "synthetic": "retained output only" }\n'});
  if (['settlement-import','successor'].includes(point))
    project=await preserveSignedRecord(project,{kind:'settlement',originalText:'{ "synthetic": "unverified settlement" }\n'});
  if (point==='successor') {
    project=await freezeEvaluation(project,project.activeCycleId,{
      baselineDigest:H,candidateDigest:'0x'+'cd'.repeat(32),taskDigest:H,procedureDigest:H,resourceBudget:{wallTimeMs:1000,providerCostMicros:'0'},
      acceptance:{exactTolerancePpm:1},heldOut:{method:'Synthetic fresh inputs',evidenceDigest:H,tuningExposure:false},
      expectedRunIds:['fixture-comparison'],rollbackDigest:H});
    const next=await createPackage({...draft,parent:'7',jobs:[{...spec,goal:'A distinct next input'}]},passphrase,profile);
    project=await addCycle(project,next);
  }
  await checkFresh(point,project,pending);
});

test('interrupted upload retains the first CID and explicit resume never uploads the capsule again',async()=>{
  const wallet=session(), files=new Map(), published=[];
  let fail=true;
  const storage={
    async publish(object,name) {
      published.push(name);
      if (name==='nova-evidence.json' && fail) throw Error('Synthetic lost upload response');
      const target='ipfs://Qm'+String.fromCharCode(98+files.size).repeat(44);
      files.set(target,object);return {uri:target};
    },
    async retrieve(target) {const object=files.get(target);return {object,byteHash:await hashBytes(fileBytes(object))};},
  };
  const flow=new NovaWorkflow(wallet,storage);
  await flow.create(draft,passphrase);await flow.kit();
  await assert.rejects(flow.publish('synthetic-no-service-token',true),/lost upload/);
  assert.ok(flow.publication.capsuleURI);assert.equal(flow.publication.evidenceURI,undefined);
  const before=flow.package, kit=await flow.projectKit(passphrase), restored=new NovaWorkflow(session(),storage);
  await restored.restoreProject(JSON.stringify(kit),passphrase);await restored.kit();
  fail=false;await restored.publish('synthetic-no-service-token',true);
  assert.equal(published.filter(name=>name==='nova-capsule.json').length,1);
  assert.deepEqual(restored.package,before);assert.equal(restored.seedId,null);
});
