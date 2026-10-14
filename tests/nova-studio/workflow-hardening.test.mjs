// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {NovaWorkflow} from '../../docs/assets/nova-studio/workflow.mjs';
import {StudioChain,INTERFACES} from '../../docs/assets/nova-studio/chain.mjs';
import {createPackage,exportKit,hashBytes,objectHash,profileIdentity} from '../../docs/assets/nova-studio/package.mjs';
import {leaf} from '../../docs/assets/nova-studio/plan.mjs';
import {unresolved} from '../../docs/assets/ascension-wallet/client.mjs';
import {TOKEN} from '../../docs/assets/ascension-wallet/protocol.mjs';
import {keccak256} from '../../docs/assets/nova-studio/vendor/ethers-6.17.0.mjs';

const profile=JSON.parse(fs.readFileSync(new URL('../../docs/assets/ascension-wallet/profile.json',import.meta.url)));
const contracts=Object.fromEntries(Object.entries(profile.contracts).map(([key,value])=>[key,value.address]));
const A='0x'+'11'.repeat(20), B='0x'+'22'.repeat(20), ZERO='0x'+'00'.repeat(32);
const HASH='0x'+'aa'.repeat(32), BLOCK='0x'+'bb'.repeat(32), OTHER='0x'+'cc'.repeat(32);
const spec={goal:'Prove the exact committed result',successMetric:'Repeatable evidence passes.',bounty:'1000',duration:3600,priceWeight:5000};
const draft={title:'Regression project',description:'Private draft',jobs:[spec],evidence:'Public verification procedure.'};
const passphrase='local capsule regression passphrase';
const packagePromise=createPackage(draft,passphrase,profile);
const publication={metadataURI:'ipfs://Qm'+'a'.repeat(44)};
const report={blockNumber:'0x20',blockHash:BLOCK,blockTime:'100'};

function harness() {
  let locked=false;
  const client={profile,contracts,history:[],pending:null,epoch:0,account:A,cancelPreview(){this.prepared=null;},
    guard(epoch){assert.equal(epoch,this.epoch);},identity:async()=>A,
    read:async()=>({hash:BLOCK,number:'0x20'})};
  const session={client,exclusive:async fn=>{assert.equal(locked,false);locked=true;try{return await fn();}finally{locked=false;}},
    restore:async()=>{throw Error('Existing journal must remain untouched.');}};
  return {flow:new NovaWorkflow(session,{}),client,session,isLocked:()=>locked};
}
function log(contract,event,args,overrides={}) {
  return {address:contracts[contract],...INTERFACES[contract].encodeEventLog(event,args),transactionHash:HASH,
    blockHash:BLOCK,blockNumber:'0x20',removed:false,...overrides};
}
function receipt(logs=[]) {return {status:'0x1',transactionHash:HASH,blockHash:BLOCK,blockNumber:'0x20',logs,from:A,to:contracts.Seed};}
function mintRecord(pkg) {
  const args=[pkg.capsuleHash,pkg.plan.planRoot,pkg.plan.jobs.length,publication.metadataURI,pkg.parent,pkg.evidenceHash];
  return {action:'seal',args,status:'effect-unverified',finalized:true,hash:HASH,
    transaction:{from:A,to:contracts.Seed,data:INTERFACES.Seed.encodeFunctionData('seal',args)},
    receipt:receipt([log('Seed','SeedSealed',['7',A,pkg.capsuleHash,pkg.plan.planRoot,pkg.parent,pkg.evidenceHash]),
      log('Seed','Transfer',['0x'+'00'.repeat(20),A,'7'])])};
}
function jobValues(state=2n,resultHash=ZERO) {
  return [contracts.Mark,A,A,1000n,900n,100n,90n,10000n,1000n,900n,3600n,5000n,0n,0n,state,leaf(0,spec),resultHash,0n,false];
}
function bindSeedReads(flow,livePackage,values=jobValues()) {
  flow.client.inspect=async()=>({verification:{...report},campaign:{phase:2n},seedOwner:B});
  flow.client.call=async(contract,method)=>{
    if(contract==='Jobs'&&method==='job')return values;
    throw Error(`Unexpected read ${contract}.${method}`);
  };
  flow.chain.call=async(contract,method)=>{
    if(method==='genomes')return [livePackage.capsuleHash,livePackage.plan.planRoot,livePackage.evidenceHash,
      BigInt(livePackage.parent),BigInt(livePackage.plan.jobs.length),A];
    if(method==='tokenURI')return [publication.metadataURI];
    if(method==='rounds')return [1n,500n,2n,0n,A];
    if(method==='quorum')return [2n];
    if(method==='maximumRiskBps')return [500n];
    if(method==='REVIEW_WINDOW')return [259200n];
    if(method==='VALIDATOR_BPS')return [1000n];
    if(method==='jobSeed')return [7n];
    throw Error(`Unexpected read ${contract}.${method}`);
  };
}

test('selected event must belong to the receipt transaction and canonical block',()=>{
  const chain=new StudioChain({contracts});
  const good=log('Seed','Transfer',['0x'+'00'.repeat(20),A,'7']);
  assert.equal(chain.events(receipt([good]),'Seed','Transfer').length,1);
  for(const change of [{transactionHash:OTHER},{blockHash:OTHER},{blockNumber:'0x21'},{removed:true},{transactionHash:undefined}])
    assert.throws(()=>chain.events(receipt([{...good,...change}]),'Seed','Transfer'),/canonical receipt/);
  assert.equal(chain.events(receipt([{...good,address:B}]),'Seed','Transfer').length,0);
  assert.throws(()=>chain.events({...receipt([good]),status:'0x0'},'Seed','Transfer'),/successful receipt/);
});

test('mint requires the exact mint Transfer and immutable creator while allowing a subsequent owner',async()=>{
  const pkg=await packagePromise,{flow}=harness(), record=mintRecord(pkg);
  bindSeedReads(flow,pkg);
  const observed=await flow.chain.verifyMint(record,pkg,publication);
  assert.equal(observed.seedId,'7');assert.equal(observed.seedOwner,B);
  record.receipt.logs.pop();
  await assert.rejects(flow.chain.verifyMint(record,pkg,publication),/NFT transfer/);
  record.receipt.logs.push(log('Seed','Transfer',['0x'+'00'.repeat(20),B,'7']));
  await assert.rejects(flow.chain.verifyMint(record,pkg,publication),/NFT transfer/);
});

test('direct mint and route receipt imports reject unsupported authorization envelopes',async()=>{
  for(const method of ['openMintReceipt','openRouteReceipt']) {
    const chain=new StudioChain({verify:async()=>{},read:async name=>name==='eth_getTransactionReceipt'?receipt():
      {type:'0x4',authorizationList:[{}]}});
    await assert.rejects(chain[method](HASH,await packagePromise,'7'),/Unsupported transaction envelope/);
  }
});

test('effect verification remains unresolved and locked on failure, and can reconcile the same mint',async()=>{
  const pkg=await packagePromise,{flow,client,isLocked}=harness(),record=mintRecord(pkg);
  flow.package=pkg;flow.publication=publication;flow.observation={green:true};flow.verifiedRoutes.set('3',{hash:OTHER});
  client.history=[record];client.pending=record;
  client.receipt=async()=>{assert.equal(isLocked(),true);return record;};
  client.completeEffects=value=>{assert.equal(isLocked(),true);assert.equal(value,record);value.status='finalized';};
  let missing=true;
  flow.chain.verifyMint=async()=>{assert.equal(isLocked(),true);if(missing)throw Error('Missing SeedSealed log.');return {seedId:'7'};};
  await assert.rejects(flow.reconcile(HASH),/Missing SeedSealed/);
  assert.equal(unresolved(record),true);assert.equal(flow.observation,null);assert.equal(flow.verifiedRoutes.size,0);
  await assert.rejects(flow.create(draft,passphrase),/outstanding/);
  flow.preflight=async()=>{flow.observation={green:true};throw Error('Preflight must not run while effects remain uncertain.');};
  await assert.rejects(flow.prepare('seal'),/outstanding/);assert.equal(flow.observation,null);
  missing=false;await flow.reconcile(HASH);assert.equal(record.status,'finalized');assert.equal(flow.seedId,'7');
  client.receipt=async()=>({status:'pending-or-replaced',hash:HASH});
  await flow.reconcile(HASH);assert.equal(flow.observation,null);
});

test('work export rejects a different full seed even when one job specification is identical',async()=>{
  const pkg=await packagePromise,other=await createPackage({...draft,jobs:[spec,{...spec,goal:'Another job'}]},passphrase,profile);
  const {flow}=harness();flow.package=pkg;flow.seedId='7';bindSeedReads(flow,other);
  await assert.rejects(flow.workPackage('9'),/immutable seed commitments/);
  bindSeedReads(flow,pkg);const work=await flow.workPackage('9');
  assert.equal(work.plan.planRoot,pkg.plan.planRoot);assert.equal(work.job.index,0);
});

test('settlement remains observed until matching canonical finalized job state is available',async()=>{
  const {flow,client}=harness(),latest=jobValues(4n,HASH);
  flow.chain.seed=async()=>({verification:{...report}});
  flow.chain.call=async()=>[7n];
  let finalState=jobValues(3n,HASH),canonical=BLOCK,unavailable=false;
  client.call=async(_contract,_method,_args,block)=>block==='0x20'?latest:finalState;
  client.read=async(_method,[block])=>{
    if(block==='finalized'){if(unavailable)throw Error('Unsupported finalized tag');return {number:'0x10',hash:BLOCK};}
    return {hash:block==='0x10'?canonical:BLOCK};
  };
  let state=await flow.chain.inspectJob('7','9');
  assert.equal(state.job.settlement,'accepted-payment');assert.equal(state.job.settlementConfirmed,false);
  finalState=latest;state=await flow.chain.inspectJob('7','9');assert.equal(state.job.settlementConfirmed,true);
  canonical=OTHER;state=await flow.chain.inspectJob('7','9');assert.equal(state.job.settlementConfirmed,false);
  unavailable=true;state=await flow.chain.inspectJob('7','9');assert.equal(state.job.settlementConfirmed,false);
});

test('fresh recovery attaches the exact pending route or purchase without replacing the live journal',async()=>{
  const pkg=await packagePromise;
  for(const action of ['route','buy','approve']) {
    const {flow,client}=harness(),job=pkg.plan.jobs[0];
    const args=action==='route'?['7','0',job.spec,job.proof,'60',[A,B,contracts.Seed]]:
      action==='buy'?['7','1','1000']:[contracts.Mark,'1000'];
    const pending={action,args,status:'submission-unknown',transaction:{from:A,to:contracts.Mark,
      data:action==='route'?INTERFACES.Mark.encodeFunctionData('route',args):'0x1234',nonce:'0x1'}};
    client.history=[pending];client.pending=pending;
    const kit=await exportKit(pkg,{seedId:'7',journal:{transactions:[pending]}});
    await flow.restore(JSON.stringify(kit),passphrase);
    assert.equal(flow.package.capsuleHash,pkg.capsuleHash);assert.equal(client.pending,pending);
    assert.equal(pending.status,'submission-unknown');assert.equal(flow.observation,null);
    if(action==='route') {
      const wrong=await exportKit(pkg,{seedId:'8',journal:{transactions:[pending]}});
      await assert.rejects(flow.restore(JSON.stringify(wrong),passphrase),/recovery seed/);
    }
  }
});

test('address-only legacy package stays recoverable but cannot authorize a new mint',async()=>{
  const pkg=structuredClone(await packagePromise),{flow}=harness();
  pkg.deployment={chainId:profile.chainId,profile:profile.profile,contracts:{Token:TOKEN.toLowerCase(),
    ...Object.fromEntries(Object.entries(profile.contracts).map(([key,value])=>[key,value.address.toLowerCase()]))}};
  pkg.evidence.deployment=pkg.deployment;pkg.evidenceHash=await objectHash(pkg.evidence);
  flow.package=pkg;flow.recovered=true;flow.exported=true;
  assert.equal(flow.deploymentIdentity,'legacy-addresses');
  await assert.rejects(flow.preflight('seal'),/legacy package records addresses only/);
  assert.notDeepEqual(pkg.deployment,profileIdentity(profile));
});

test('a shared multi-project journal can attach each package without clearing unrelated uncertainty',async()=>{
  const first=await packagePromise,second=await createPackage({...draft,title:'Second project'},passphrase,profile);
  const {flow,client}=harness(),older=mintRecord(first),newer=mintRecord(second);
  older.status='submission-unknown';newer.status='submission-unknown';
  newer.transaction={...newer.transaction,nonce:'0x2'};
  client.history=[older,newer];client.pending=newer;
  const journal={transactions:[older,newer]};
  await flow.restore(JSON.stringify(await exportKit(second,{journal,seedId:'8'})),passphrase);
  assert.equal(flow.package.capsuleHash,second.capsuleHash);
  assert.deepEqual(client.history,[older,newer]);assert.equal(client.history.every(unresolved),true);
  await flow.restore(JSON.stringify(await exportKit(first,{journal,seedId:'7'})),passphrase);
  assert.equal(flow.package.capsuleHash,first.capsuleHash);
  assert.equal(client.pending,newer);assert.equal(client.history.every(unresolved),true);
  await assert.rejects(flow.prepare('seal'),/outstanding/);
});

test('historical route reconciliation verifies the indexed calldata proof without its capsule',async()=>{
  const pkg=await packagePromise,{flow}=harness(),job=pkg.plan.jobs[0],reviewers=[A,B,contracts.Seed];
  bindSeedReads(flow,pkg,jobValues(1n));
  const read=flow.chain.call.bind(flow.chain);
  flow.chain.call=async(contract,method,args)=>method==='committees'?[reviewers[Number(args[1])]]:read(contract,method,args);
  const args=['7','0',job.spec,job.proof,'60',reviewers];
  const record={action:'route',args,status:'effect-unverified',finalized:true,
    transaction:{from:A,to:contracts.Mark,data:INTERFACES.Mark.encodeFunctionData('route',args)},
    receipt:receipt([log('Mark','MissionRouted',['7','0','9',job.leaf])])};
  assert.equal(await flow.chain.verifyRoute(record,null,'7'),'9');
  const other=await createPackage({...draft,jobs:[{...spec,goal:'Another commitment'}]},passphrase,profile);
  bindSeedReads(flow,other,jobValues(1n));
  await assert.rejects(flow.chain.verifyRoute(record,null,'7'),/immutable plan root/);
});

test('reconciling another project’s historical mint preserves the selected project context',async()=>{
  const pkg=await packagePromise,{flow,client}=harness(),record=mintRecord(pkg);
  flow.package={capsuleHash:OTHER,plan:{planRoot:OTHER},evidenceHash:OTHER};flow.seedId='8';flow.jobIds=['10'];
  const selected={seedId:'8'};flow.observation=selected;
  client.history=[record];client.pending=record;client.receipt=async()=>record;
  client.completeEffects=value=>{value.status='finalized';};
  let verified=false;flow.chain.openMintReceipt=async hash=>{assert.equal(hash,HASH);verified=true;return {seedId:'7'};};
  await flow.reconcile(HASH);
  assert.equal(verified,true);assert.equal(record.status,'finalized');assert.equal(flow.seedId,'8');
  assert.equal(flow.observation,selected);assert.deepEqual(flow.jobIds,['10']);
});

test('native submit binds trusted signature, exact uploaded bytes, worker epoch and routed index',async()=>{
  const pkg=await packagePromise,{flow,client}=harness();flow.package=pkg;flow.seedId='7';
  const keys=await crypto.subtle.generateKey('Ed25519',true,['sign','verify']);
  const publicKey=Buffer.from(await crypto.subtle.exportKey('raw',keys.publicKey)).toString('hex');
  const body=JSON.stringify({jobIndex:0,nativeExport:{receipt:{body:{document:{request:{goal:spec.goal},
    review:{approved:true},state:'completed'}}}},plan:pkg.plan,schema:'agialpha.ascension.reviewed-delivery.v1'});
  const signature=Buffer.from(await crypto.subtle.sign('Ed25519',keys.privateKey,
    await crypto.subtle.digest('SHA-256',new TextEncoder().encode(body)))).toString('base64');
  const source=`{"body":${body},"publicKey":${JSON.stringify(publicKey)},"signature":${JSON.stringify(signature)}}`;
  const original=new TextEncoder().encode(source), result=keccak256(original);
  const job={state:2n,worker:A,due:900n,resultHash:ZERO};
  flow.workPackage=async()=>({job:pkg.plan.jobs[0]});
  flow.chain.inspectJob=async()=>({job});
  flow.chain.seed=async()=>({verification:{...report},campaign:{}});
  flow.chain.call=async()=>[7n];client.inspect=async()=>({verification:{...report},job});
  let bytes=original;flow.storage.retrieveBytes=async()=>({bytes,byteHash:await hashBytes(bytes)});
  const imported=await flow.importNativeDelivery(source,{trustedPublicKey:publicKey,jobId:'9'});
  assert.equal(imported.resultHash,result);assert.equal(imported.source,undefined);assert.equal(imported.connected,false);
  assert.deepEqual(await flow.preflight('submit',{jobId:'9',result,uri:publication.metadataURI,native:true}),
    ['submit',['9',result,publication.metadataURI]]);
  await assert.rejects(flow.preflight('submit',{jobId:'9',result,uri:publication.metadataURI}),/generic SHA-256/);
  bytes=new TextEncoder().encode(source+'\n');
  await assert.rejects(flow.preflight('submit',{jobId:'9',result,uri:publication.metadataURI,native:true}),/Published native/);
  bytes=original;client.epoch++;
  await assert.rejects(flow.preflight('submit',{jobId:'9',result,uri:publication.metadataURI,native:true}),/connected worker/);
});
