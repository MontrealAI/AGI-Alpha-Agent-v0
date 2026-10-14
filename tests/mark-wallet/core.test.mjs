// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {CONTRACTS,METHODS,SELECTORS,callData,tuple,decode,units,tokens,uint,curve,parseFields} from '../../docs/assets/ascension-wallet/protocol.mjs';
import {MarkClient,sha256Hex,validateProfile} from '../../docs/assets/ascension-wallet/client.mjs';
const ACCOUNT='0x1111111111111111111111111111111111111111', HASH='0x'+'ab'.repeat(32), BLOCK='0x'+'12'.repeat(32);
const ADDRESS_TO_KEY=Object.fromEntries(Object.entries(CONTRACTS).map(([k,v])=>[v.toLowerCase(),k]));
const profile=()=>({schema:'agialpha.mark-wallet-profile.v1',chainId:1,profile:'ascension-2026-10-11-solc-0.8.24',newExposureEnabled:false,
  contracts:Object.fromEntries(['Access','Seed','Oracle','Jobs','Mark'].map(k=>[k,{address:CONTRACTS[k],sha256:'f3df0a62b10f205b0f29768b7dc4deef63d6bdb4ac982e45d2ea3a3a51c27b9a'}]))});
async function fixture() {
  const p=profile(), digest=await sha256Hex('0x6000'); for(const c of Object.values(p.contracts)) c.sha256=digest;
  const events=new Map(), calls=[];
  const provider={chain:'0x1',account:ACCOUNT,code:'0x6000',sendError:null,sends:0,result:'100',delay:null,
    on(event,fn){events.set(event,fn)},removeListener(event){events.delete(event)},emit(event){events.get(event)?.()},
    async request({method,params=[]}) {
      calls.push({method,params});
      if(method==='eth_chainId') return this.chain;
      if(method==='eth_accounts'||method==='eth_requestAccounts') { if(method==='eth_requestAccounts'&&this.announce) this.emit('accountsChanged'); return [this.account]; }
      if(method==='eth_getCode') return this.code;
      if(method==='eth_getBlockByNumber') return {number:'0x100',hash:BLOCK,timestamp:'0x6ace0000'};
      if(method==='eth_getBalance') return '0xde0b6b3a7640000';
      if(method==='eth_estimateGas') { if(this.delay) await this.delay; return '0xc350'; }
      if(method==='eth_call') {
        const tx=params[0], contract=ADDRESS_TO_KEY[tx.to.toLowerCase()], selector=tx.data.slice(0,10);
        const key=Object.keys(SELECTORS).find(k=>SELECTORS[k]===selector);
        const bound={access:'Access',seed:'Seed',oracle:'Oracle',jobsBinding:'Jobs',mark:'Mark',marketplace:'Jobs',token:'Token'}[key];
        if(bound) return '0x'+tuple(['address'],[CONTRACTS[bound]]);
        if(key==='decimals') return '0x'+tuple(['uint8'],['18']);
        if(key==='reclaim'||key==='claimRefund') return '0x'+tuple(['uint256'],[this.result]);
        if(key==='approve') return '0x'+tuple(['bool'],[true]);
        if(key==='nextId') return '0x'+tuple(['uint256'],['0']);
        if(['balanceOf','allowance','stake','locked','lockedUntil','minimumStake'].includes(key)) return '0x'+tuple(METHODS[key].outputs,['0']);
        if(['eligible','admitted','green'].includes(key)) return '0x'+tuple(['bool'],[false]);
        if(key==='campaigns') return '0x'+tuple(METHODS[key].outputs,[ACCOUNT,'2','1','50','100','20','0','0','864000','2000000000','0','230','1','0x'+'22'.repeat(32)]);
        if(key==='ownerOf') return '0x'+tuple(['address'],[ACCOUNT]);
        if(key==='plan') return '0x'+tuple(['bytes32','uint32'],['0x'+'33'.repeat(32),'1']);
        if(key==='lots') return '0x'+tuple(['uint256'],['5']);
        return '0x';
      }
      if(method==='eth_sendTransaction') { this.sends++; this.last=params[0]; if(this.sendError) throw this.sendError; return HASH; }
      if(method==='eth_getTransactionReceipt') return this.noReceipt?null:{transactionHash:HASH,status:this.reverted?'0x0':'0x1',blockHash:BLOCK,blockNumber:'0x100'};
      if(method==='eth_getTransactionByHash') return {from:this.last.from,to:this.wrongTo?ACCOUNT:this.last.to,input:this.last.data,value:'0x0'};
      if(method==='wallet_switchEthereumChain') {this.chain='0x1';this.emit('chainChanged');return null;}
      throw Error(`Unexpected RPC ${method}`);
    }};
  const client=new MarkClient(p);client.select(provider);await client.connect();calls.length=0;
  return {client,provider,calls,p};
}
test('exact 18-decimal token conversion; no floats, commas or exponent shortcuts',()=>{
  assert.equal(units('1.000000000000000001'),1000000000000000001n);
  assert.equal(tokens(1000000000000000001n),'1.000000000000000001');
  for(const value of ['-1','1e18','1,000','01','1.0000000000000000001','NaN','Infinity']) assert.throws(()=>units(value));
  assert.throws(()=>uint('256',8));assert.throws(()=>uint(100));
});
test('known ERC20 selector and exact bounded-approval calldata',()=>{
  assert.equal(SELECTORS.approve,'0x095ea7b3');
  assert.equal(callData('approve',[ACCOUNT,'0']),'0x095ea7b3'+'0'.repeat(24)+ACCOUNT.slice(2)+'0'.repeat(64));
});
test('decoder rejects noncanonical booleans, high address bits and malformed lengths',()=>{
  assert.throws(()=>decode(['bool'],'0x'+tuple(['uint256'],['2'])));
  assert.throws(()=>decode(['address'],'0x'+'f'.repeat(64)));
  assert.throws(()=>decode(['uint96'],'0x01'));
  assert.throws(()=>callData('__proto__',[]));
});
test('dynamic string offsets and UTF-8 bytes are exact',()=>{
  const encoded=tuple(['uint8','string'],['0','é']);
  assert.equal(encoded.slice(64,128),BigInt(64).toString(16).padStart(64,'0'));
  assert.equal(encoded.slice(128,192),BigInt(2).toString(16).padStart(64,'0'));
  assert.equal(encoded.slice(192,196),'c3a9');
  assert.throws(()=>tuple(['string'],['é'.repeat(257)]));
});
test('curve and split purchases agree; count and width bounds are enforced',()=>{
  assert.equal(curve(0,40,units('2'),units('0.1')),units('158'));
  assert.equal(curve(0,20,2,1)+curve(20,20,2,1),curve(0,40,2,1));
  assert.throws(()=>curve(1000000,1,2,1));
});
test('FusionPlan fields are strict; namespace labels are not full names',()=>{
  assert.throws(()=>parseFields('register',['0','foo.alpha.agi.eth']));
  assert.deepEqual(parseFields('register',['0','foo-bar']),['0','foo-bar']);
  const spec=JSON.stringify({goal:'g',successMetric:'m',bounty:'1',duration:2,priceWeight:6000});
  const args=parseFields('route',['1','0',spec,'[]','1',JSON.stringify([ACCOUNT,ACCOUNT,ACCOUNT])]);
  assert.equal(callData('route',args).slice(0,10),SELECTORS.route);
  assert.throws(()=>parseFields('route',['1','0',spec.slice(0,-1)+',"extra":0}','[]','1','[]']));
});
test('profile rejects enabling funding, wrong chain and changed addresses',async()=>{
  const {p}=await fixture(); assert.throws(()=>validateProfile({...p,newExposureEnabled:true}));
  assert.throws(()=>validateProfile({...p,chainId:31337}));
  const bad=structuredClone(p);bad.contracts.Mark.address=ACCOUNT;assert.throws(()=>validateProfile(bad));
});
test('inspection never requests account access or sends a transaction',async()=>{
  const {client,calls}=await fixture();const observation=await client.inspect();
  assert.equal(observation.nextSeedId,0n);assert.equal(observation.verification.newExposureEnabled,false);
  assert.equal(calls.some(c=>['eth_requestAccounts','eth_sendTransaction'].includes(c.method)),false);
});
test('first connection tolerates the legitimate accountsChanged announcement',async()=>{
  const {client,provider}=await fixture();client.disconnect();provider.announce=true;client.select(provider);
  assert.equal(await client.connect(),ACCOUNT);
});
test('new funding and nonzero approvals are blocked before any RPC',async()=>{
  const {client,calls}=await fixture();
  await assert.rejects(client.prepare('buy',['1','1','2']),/not commissioned/);
  await assert.rejects(client.prepare('approve',['Mark','1']),/not commissioned/);
  assert.equal(calls.length,0);
});
test('recovery is not blocked by denied admission or expired green status',async()=>{
  const {client,provider}=await fixture();
  const preview=await client.prepare('sell',['1','1','0.1']);
  assert.equal(preview.transaction.to,CONTRACTS.Mark);assert.equal(provider.sends,0);
  await client.confirm(true);assert.equal(provider.sends,1);assert.equal(provider.last.value,'0x0');
});
test('zero allowance is a real bounded recovery transaction only to an allowed spender',async()=>{
  const {client}=await fixture();await client.prepare('approve',['Mark','0']);
  assert.equal(client.prepared.transaction.to,CONTRACTS.Token);
  assert.throws(()=>parseFields('approve',[ACCOUNT,'0']));
});
test('wrong chain blocks preparation and signing, even without an event',async()=>{
  const {client,provider}=await fixture();await client.prepare('reclaim',['1']);provider.chain='0x89';
  await assert.rejects(client.confirm(true),/Wrong network/);assert.equal(provider.sends,0);
});
test('bytecode mismatch blocks recovery instead of falling back to a demo',async()=>{
  const {client,provider}=await fixture();provider.code='0x6001';
  await assert.rejects(client.prepare('reclaim',['1']),/bytecode/);assert.equal(provider.sends,0);
});
test('missing bytecode and RPC failures remain errors',async()=>{
  const {client,provider}=await fixture();provider.code='0x';await assert.rejects(client.verify(),/bytecode/);
});
test('changing accounts invalidates the preview; no stale signature request',async()=>{
  const {client,provider}=await fixture();await client.prepare('sell',['1','1','0']);provider.emit('accountsChanged');
  assert.equal(client.prepared,null);await assert.rejects(client.confirm(true),/Prepare/);assert.equal(provider.sends,0);
});
test('editing or cancelling while preparation is in flight invalidates the result',async()=>{
  const {client,provider}=await fixture();let resume;provider.delay=new Promise(r=>resume=r);
  const pending=client.prepare('reclaim',['1']);
  await new Promise(r=>setTimeout(r,15));client.cancelPreview();resume();
  await assert.rejects(pending,/Inputs changed/);assert.equal(client.prepared,null);
});
test('explicit acknowledgement is mandatory and preview expiry is enforced',async()=>{
  const {client,provider}=await fixture();await client.prepare('reclaim',['1']);await assert.rejects(client.confirm(false),/acknowledge/);
  client.prepared={...client.prepared,preparedAt:Date.now()-61000};
  await assert.rejects(client.confirm(true),/expired/);assert.equal(provider.sends,0);
});
test('changed simulated reclaim proceeds require a new preview',async()=>{
  const {client,provider}=await fixture();await client.prepare('reclaim',['1']);provider.result='99';
  await assert.rejects(client.confirm(true),/Simulation result changed/);assert.equal(provider.sends,0);
});
test('confirm is single use; double clicks and pending repeats cannot duplicate a send',async()=>{
  const {client,provider}=await fixture();await client.prepare('reclaim',['1']);
  const first=client.confirm(true);await assert.rejects(client.confirm(true),/Prepare/);await first;
  await assert.rejects(client.prepare('reclaim',['1']),/outstanding/);assert.equal(provider.sends,1);
});
test('wallet rejection is explicit and not automatically retried',async()=>{
  const {client,provider}=await fixture();provider.sendError={code:4001};await client.prepare('reclaim',['1']);
  await assert.rejects(client.confirm(true),/rejected/);assert.equal(provider.sends,1);assert.equal(client.pending.status,'rejected-by-wallet');
});
test('unknown signing outcome blocks retries and provider changes',async()=>{
  const {client,provider}=await fixture();provider.sendError=Error('disconnected');await client.prepare('reclaim',['1']);
  await assert.rejects(client.confirm(true),/unknown/);assert.equal(client.pending.status,'submission-unknown');
  await assert.rejects(client.prepare('reclaim',['1']),/outstanding/);assert.throws(()=>client.select(provider),/Resolve/);
});
test('real receipts distinguish pending, reverted and finalized; calldata must match',async()=>{
  const {client,provider}=await fixture();await client.prepare('reclaim',['1']);await client.confirm(true);
  provider.noReceipt=true;assert.equal((await client.receipt(HASH)).status,'pending-or-replaced');provider.noReceipt=false;
  provider.wrongTo=true;await assert.rejects(client.receipt(HASH),/does not match/);provider.wrongTo=false;
  provider.reverted=true;assert.equal((await client.receipt(HASH)).status,'reverted');provider.reverted=false;
  assert.equal((await client.receipt(HASH)).status,'finalized');
});
