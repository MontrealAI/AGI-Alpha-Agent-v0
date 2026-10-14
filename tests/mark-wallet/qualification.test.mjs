// SPDX-License-Identifier: Apache-2.0
// Deterministic mocked RPC qualification boundaries; these are not Mainnet commissioning evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,copyFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {MarkClient, canonicalProfile, deploymentDescriptor, sha256Hex, sha256Text} from '../../docs/assets/ascension-wallet/client.mjs';
import {ACTIONS, CONTRACTS, METHODS, SELECTORS as SHARED_SELECTORS, callData, tuple} from '../../docs/assets/ascension-wallet/protocol.mjs';
import {qualificationIdentity,QUALIFICATION_METHODS} from '../../docs/assets/ascension-wallet/qualification.mjs';
const SELECTORS={...SHARED_SELECTORS,...Object.fromEntries(Object.entries(QUALIFICATION_METHODS).map(([key,value])=>[key,value.selector]))};
const actor='0x'+'99'.repeat(20), governor='0x'+'98'.repeat(20), ens='0x'+'97'.repeat(20), zero='0x'+'00'.repeat(20);
const genesis='0x'+'01'.repeat(32), blockHash='0x'+'02'.repeat(32), digest='ab'.repeat(32);
const seedArgs=['0x'+'11'.repeat(32),'0x'+'22'.repeat(32),'1','ipfs://bafy-reviewed-fixture','0','0x'+'33'.repeat(32)];
const word=(types,values)=>'0x'+tuple(types,values);
async function profile() {
  const runtime=await sha256Hex('0x6000'), contracts=Object.fromEntries(Object.keys(CONTRACTS).map((key,i)=>[
    key,{address:key==='Token'?CONTRACTS.Token:'0x'+(i+10).toString(16).padStart(2,'0').repeat(20),sha256:runtime}
  ]));
  const owner=word(['address'],[governor]), pendingOwner=word(['address'],[zero]);
  const expiry=String(Math.floor(Date.now()/1000)+3600);
  return {schema:'agialpha.qualified-wallet-profile.v1',profile:'hypothetical-qualified-fixture',environment:'qualified-mainnet',chainId:1,
    mainnetQualification:true,newExposureEnabled:true,sourceSHA256:digest,abiSHA256:await sha256Text(qualificationIdentity()),
    genesisHash:genesis,deploymentBlock:'0x1',deploymentBlockHash:blockHash,contracts,validUntil:expiry,
    actions:Object.keys(ACTIONS),recoveryActions:['sell','reclaim','collect','close','approve','availability','agentWithdraw','validatorWithdraw'],
    continuationActions:['award','submit','validate','timeout'],
    qualification:Object.fromEntries(['evidenceSHA256','dependencyReviewSHA256','sourceVerificationSHA256','authorityReviewSHA256','approvalSHA256','canaryEvidenceSHA256','publicApprovalSHA256'].map(k=>[k,digest])),
    protocol:{Access:{owner,pendingOwner,roots:['0x'+'a1'.repeat(32),'0x'+'a2'.repeat(32),'0x'+'a3'.repeat(32)]},
      Oracle:{owner,pendingOwner,minimumStake:word(['uint256'],['100']),quorum:word(['uint16'],['2']),maximumRiskBps:word(['uint16'],['1000'])},
      Jobs:{owner,pendingOwner,minimumStake:word(['uint256'],['100']),reviewWindow:word(['uint32'],['259200']),validatorBps:word(['uint16'],['500'])}},
    dependencies:{Token:{address:CONTRACTS.Token,sha256:runtime,proxy:null,authority:{model:'governed',evidenceSHA256:digest,checks:[{kind:'call',data:SELECTORS.owner,expected:owner}]}},
      ENS:{address:ens,sha256:runtime,proxy:null,authority:{model:'immutable',evidenceSHA256:digest,checks:[]}},Wrapper:null}};
}
async function fixture(t, mutate=()=>{}, stage='canary', editEntry=()=>{}) {
  const p=await profile();mutate(p);
  const encoded=canonicalProfile(p), profileSHA256=await sha256Text(encoded);
  const authorization={profileSHA256,approvalSHA256:digest,validUntil:p.validUntil,intents:[
    {action:'seal',from:actor,to:p.contracts.Seed.address,data:callData('seal',seedArgs),value:'0x0',nonce:'0x0',maxGas:'0x186a0'}]};
  const authorizationJSON=canonicalProfile(authorization);
  const entry={canonicalJSON:encoded,sha256:profileSHA256,stage,authorizationJSON,authorizationSHA256:await sha256Text(authorizationJSON)};
  await editEntry(entry);
  const folder=await mkdtemp(join(tmpdir(),'nova-qualification-'));t.after(()=>rm(folder,{recursive:true,force:true}));
  for(const file of ['client.mjs','protocol.mjs','qualification.mjs','recovery.mjs','session.mjs'])
    await copyFile(new URL('../../docs/assets/ascension-wallet/'+file,import.meta.url),join(folder,file));
  await writeFile(join(folder,'qualified-profiles.mjs'),'export const QUALIFIED_PROFILES=Object.freeze(['+JSON.stringify(entry)+']);\n');
  const exports=await import(pathToFileURL(join(folder,'client.mjs')));
  const {MarkClient:BoundClient}=exports;
  const client=new BoundClient(p), addresses=Object.fromEntries(Object.entries(p.contracts).map(([k,v])=>[v.address.toLowerCase(),k]));
  const provider={nonce:'0x0',sends:0,account:actor,changedAuthority:false,changedCode:false,changedPointer:false,
    async request({method,params=[]}) {
      if(method==='eth_chainId')return '0x1';
      if(['eth_accounts','eth_requestAccounts'].includes(method))return [this.account];
      if(method==='eth_getCode')return this.changedCode&&params[0].toLowerCase()===ens?'0x6001':'0x6000';
      if(method==='eth_getBlockByNumber')return {number:params[0]==='0x0'?'0x0':'0x1',hash:params[0]==='0x0'?genesis:blockHash,timestamp:'0x'+Math.floor(Date.now()/1000).toString(16)};
      if(method==='eth_getTransactionCount')return this.nonce;
      if(method==='eth_estimateGas')return this.gas||'0xc350';
      if(method==='eth_getBalance')return '0xde0b6b3a7640000';
      if(method==='eth_getStorageAt')return this.changedPointer?'0x'+'00'.repeat(32):p.dependencies.Token.proxy.pointer.expected;
      if(method==='eth_call') {
        const tx=params[0], contract=addresses[tx.to.toLowerCase()], key=Object.keys(SELECTORS).find(k=>tx.data.slice(0,10)===SELECTORS[k]);
        if(key==='owner'&&contract==='Token')return this.changedAuthority?word(['address'],[actor]):p.protocol.Access.owner;
        if(typeof p.protocol[contract]?.[key]==='string')return this.changedAuthority&&key==='owner'?word(['address'],[actor]):p.protocol[contract][key];
        const bound={access:'Access',seed:'Seed',oracle:'Oracle',jobsBinding:'Jobs',mark:'Mark',marketplace:'Jobs',token:'Token'}[key];
        if(bound)return word(['address'],[p.contracts[bound].address]);
        if(key==='decimals')return word(['uint8'],['18']);
        if(key==='roots')return word(['bytes32'],[p.protocol.Access.roots[Number(BigInt('0x'+tx.data.slice(-64)))]]);
        if(key==='ens')return word(['address'],[ens]);if(key==='wrapper')return word(['address'],[zero]);
        if(['seal','reclaim','nextId'].includes(key))return word(['uint256'],['7']);
        if(key==='approve')return word(['bool'],[true]);
        if(['balanceOf','allowance','stake','locked','lockedUntil'].includes(key))return word(METHODS[key].outputs,['0']);
        if(['admitted','eligible'].includes(key))return word(['bool'],[false]);
        return '0x';
      }
      if(method==='eth_sendTransaction'){this.sends++;this.last=params[0];return '0x'+'45'.repeat(32);}
      if(method==='eth_getTransactionReceipt')return {transactionHash:params[0],status:'0x1',blockNumber:'0x1',blockHash,gasUsed:this.receiptGas||'0xc350',logs:[]};
      if(method==='eth_getTransactionByHash')return {type:'0x2',hash:params[0],from:this.last.from,to:this.last.to,input:this.last.data,value:'0x0',nonce:this.last.nonce,chainId:'0x1',blockNumber:'0x1',blockHash,gas:this.receiptLimit||this.last.gas};
      throw Error('Unexpected mock RPC '+method);
    }};
  client.select(provider);await client.connect();
  const {WalletSession:BoundSession}=await import(pathToFileURL(join(folder,'session.mjs')));
  return {client,provider,p,authorization,BoundClient,BoundSession,folder,exports};
}
test('unmodified production build rejects imported qualified and local profiles',async()=>{
  const p=await profile();assert.throws(()=>new MarkClient(p),/Unsupported/);
  assert.throws(()=>new MarkClient({...p,schema:'agialpha.nova-local-profile.v1',chainId:31337,environment:'local-exact-source',mainnetQualification:false}),/Unsupported/);
});
test('source-bound exact canary intent can be prepared; package identity is independent of run authorization',async t=>{
  const {client,provider,p,authorization}=await fixture(t);
  assert.equal(client.profileIdentity,authorization.profileSHA256);assert.equal(p.canaryIntents,undefined);
  const preview=await client.prepare('seal',seedArgs);
  assert.equal(preview.transaction.data,authorization.intents[0].data);
  assert.equal(preview.transaction.value,'0x0');
  await client.confirm(true);assert.equal(provider.sends,1);assert.equal(client.pending.requiresEffectVerification,true);
  assert.equal(client.pending.authorizationSHA256,client.authorizationIdentity);
});
test('canary refuses changed sender, exact artifact bytes, nonce and gas cap',async t=>{
  for(const alteration of ['sender','bytes','nonce','gas']) {
    const {client,provider}=await fixture(t);const args=[...seedArgs];
    if(alteration==='sender'){provider.account=governor;client.account=null;}
    if(alteration==='bytes')args[3]='ipfs://different-actual-artifact';
    if(alteration==='nonce')provider.nonce='0x1';
    if(alteration==='gas')provider.gas='0x186a0';
    await assert.rejects(client.prepare('seal',args),/canary/);assert.equal(provider.sends,0);
  }
});
test('fresh dependency, protocol authority and proxy implementation changes invalidate final confirmation',async t=>{
  for(const change of ['changedAuthority','changedCode','changedPointer']) {
    const {client,provider}=await fixture(t,p=>{
      if(change==='changedPointer')p.dependencies.Token.proxy={implementation:ens,implementationSHA256:p.dependencies.ENS.sha256,
        pointer:{kind:'storage',slot:'0x'+'11'.repeat(32),expected:word(['address'],[ens])}};
    });
    await client.prepare('seal',seedArgs);provider[change]=true;
    await assert.rejects(client.confirm(true),/authority|dependency|implementation/);assert.equal(provider.sends,0);
  }
});
test('expired exposure authorization preserves inspection, exact zero revocation and reviewed recovery',async t=>{
  const {client,provider}=await fixture(t,p=>{p.validUntil=String(Math.floor(Date.now()/1000)-1);});
  assert.equal((await client.inspect()).verification.newExposureEnabled,false);
  await assert.rejects(client.prepare('seal',seedArgs),/expired/);
  await assert.rejects(client.prepare('approve',['Mark','1']),/expired/);
  await client.prepare('approve',['Mark','0']);client.cancelPreview();
  await client.prepare('reclaim',['7']);await client.confirm(true);assert.equal(provider.sends,1);
});
test('qualification expiry occurring after preview blocks new exposure at confirmation',async t=>{
  const {client,provider,p}=await fixture(t);await client.prepare('seal',seedArgs);
  t.mock.method(Date,'now',()=>Number(p.validUntil)*1000+1);
  await assert.rejects(client.confirm(true),/expired/);assert.equal(provider.sends,0);
});
test('profile mutation and archived address qualification cannot enter a source-pinned registry',async t=>{
  const {client,p,BoundClient}=await fixture(t);
  const changed=structuredClone(p);changed.actions=[];assert.throws(()=>new BoundClient(changed),/Unsupported/);
  assert.throws(()=>{client.profile.newExposureEnabled=false;},TypeError);
  assert.throws(()=>{client.profile.contracts.Mark.address=actor;},TypeError);
  await assert.rejects(fixture(t,q=>{q.contracts.Mark.address=CONTRACTS.Mark;}),/Archived/);
});
test('public qualification requires canary and public approval evidence',async t=>{
  await assert.rejects(fixture(t,p=>{delete p.qualification.canaryEvidenceSHA256;},'public'),/evidence/);
  const {client}=await fixture(t,()=>{},'public');assert.equal((await client.verify()).qualificationStage,'public');
});
test('changed ABI identity and mixed deployment modules cannot qualify',async t=>{
  const {client}=await fixture(t,p=>{p.abiSHA256='00'.repeat(32);});
  await assert.rejects(client.prepare('seal',seedArgs),/ABI/);
});
test('actual wallet gas escalation never becomes a completed canary intent',async t=>{
  const {client,provider}=await fixture(t);await client.prepare('seal',seedArgs);const hash=await client.confirm(true);
  provider.receiptLimit='0x186a1';
  await assert.rejects(client.receipt(hash),/gas scope/);assert.equal(client.pending.status,'authorization-mismatch');
  await assert.rejects(client.prepare('seal',seedArgs),/outstanding/);
});
test('same deployed artifacts survive qualification renewal and promotion, but not changed code',async()=>{
  const p=await profile(), promoted=structuredClone(p);
  promoted.validUntil=String(BigInt(p.validUntil)+100000n);promoted.qualification.publicApprovalSHA256='cd'.repeat(32);
  promoted.actions=['seal'];promoted.recoveryActions=[];
  assert.deepEqual(deploymentDescriptor(p),deploymentDescriptor(promoted));
  promoted.contracts.Seed.sha256='00'.repeat(32);assert.notDeepEqual(deploymentDescriptor(p),deploymentDescriptor(promoted));
});

test('source, runtime, chain genesis and deployment anchor pins fail closed',async t=>{
  for(const field of ['sourceSHA256','abiSHA256','genesisHash','deploymentBlock','deploymentBlockHash'])
    await assert.rejects(fixture(t,p=>{delete p[field];}));
  for(const tag of ['0x0','0x1']) {
    const {client,provider}=await fixture(t);const request=provider.request.bind(provider);
    provider.request=async rpc=>rpc.method==='eth_getBlockByNumber'&&rpc.params[0]===tag
      ? {...await request(rpc),hash:'0x'+'ee'.repeat(32)}:request(rpc);
    await assert.rejects(client.verify(),/genesis or deployment/);
  }
});
test('canonical registry and separate authorization digests are checked before signing',async t=>{
  for(const key of ['sha256','authorizationSHA256']) {
    const {client,provider}=await fixture(t,()=>{},key==='sha256'?'public':'canary',entry=>{entry[key]='00'.repeat(32);});
    await assert.rejects(client.prepare('seal',seedArgs),/build/);assert.equal(provider.sends,0);
  }
});
test('an unresolved journal survives same-deployment suspension and public promotion',async t=>{
  const original=await fixture(t);await original.client.prepare('seal',seedArgs);const hash=await original.client.confirm(true);
  const journal=JSON.parse(JSON.stringify(original.client.journal()));
  for(const stage of ['canary','public']) {
    const next=await fixture(t,p=>{p.newExposureEnabled=false;p.validUntil=String(BigInt(p.validUntil)+3600n);},stage);
    next.client.restore(journal);assert.equal(next.client.pending.status,'submitted');
    await assert.rejects(next.client.prepare('reclaim',['1']),/outstanding/);
    next.client.select(original.provider);const receipt=await next.client.receipt(hash,true);
    assert.equal(receipt.status,'effect-unverified');next.client.completeEffects(receipt);
    await assert.rejects(next.client.prepare('seal',seedArgs),/suspended/);
    await next.client.prepare('reclaim',['1']);
  }
});
test('registered profiles are explicitly enumerable and selection preserves each deployment journal',async t=>{
  const {exports,BoundSession,p,provider}=await fixture(t);
  const archive={schema:'agialpha.mark-wallet-profile.v1',chainId:1,profile:'ascension-2026-10-11-solc-0.8.24',newExposureEnabled:false,
    contracts:Object.fromEntries(['Access','Seed','Oracle','Jobs','Mark'].map(key=>[key,{address:CONTRACTS[key],sha256:p.contracts[key].sha256}]))};
  const choices=exports.availableProfiles(archive);assert.equal(choices.length,2);assert.equal(choices[0].stage,'archive');
  assert.equal(exports.selectBuildProfile(choices[1].id,archive).profile,p.profile);
  assert.throws(()=>exports.selectBuildProfile('browser-import',archive),/registered/);
  const values=new Map(),storage={getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value)};
  const locks={request:async(key,options,fn)=>fn({name:key})};
  const session=new BoundSession(p,storage,locks);session.client.select(provider);await session.client.connect();
  await session.prepare('reclaim',['1']);await session.confirm(true);
  await assert.rejects(session.selectProfile(archive),/outstanding/);
  await session.reconcile(session.client.pending.hash);const saved=session.client.journal();
  await session.selectProfile(archive);assert.equal(session.client.history.length,0);
  await session.selectProfile(p);assert.deepEqual(session.client.journal(),saved);
});
