// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {NovaWorkflow, fundingTerms, nativeSignatureBody} from '../../docs/assets/nova-studio/workflow.mjs';
import {compilePlan} from '../../docs/assets/nova-studio/plan.mjs';
import {tuple} from '../../docs/assets/ascension-wallet/protocol.mjs';

const ZERO = `0x${'0'.repeat(64)}`, blockHash = `0x${'a'.repeat(64)}`;
const alice = `0x${'1'.repeat(40)}`, bob = `0x${'2'.repeat(40)}`, seed = `0x${'3'.repeat(40)}`;
const transfer = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const spec = {goal:'Preserve exact specification',successMetric:'Check all integer results',
  bounty:'1000000000000000000',duration:3600,priceWeight:6000};
const client = overrides => ({epoch:0,chainId:1,profile:{profile:'unit-profile',contracts:{Seed:{deploymentBlock:1}}},
  contracts:{Seed:seed,Jobs:bob,Mark:alice,Access:bob},prepare:async()=>{},receipt:async()=>{},
  cancelPreview(){},...overrides});
const terms = changes => ({base:'2',slope:'0.1',maxLots:'100',target:'100',fundingEnd:'86401',duration:'345601',...changes});

test('funding arithmetic is exact above Number.MAX_SAFE_INTEGER and explains partial targets', () => {
  const result = fundingTerms(terms(),1n,259200n,'100000000000000000001');
  assert.equal(result.maximumFunding,695000000000000000000n);
  assert.equal(result.target,100000000000000000000n);
  assert.equal(result.partialFunding,true);
  assert.equal(fundingTerms(terms({target:'101'}),1n,259200n,'100000000000000000001').partialFunding,false);
});

test('unreachable targets, integer overflow and inadequate time fail before signing', () => {
  for (const change of [{target:'696'},{maxLots:'1000001'},{base:'0'},{fundingEnd:'1'},
    {fundingEnd:String(30 * 86400 + 2)},{duration:'259200'},{duration:String(90 * 86400 + 1)},
    {base:'79228162514.264337593543950336'},{base:'2e0'},{target:'0.0000000000000000001'}])
    assert.throws(()=>fundingTerms(terms(change),1n,259200n,'100'));
});

test('closed unfunded campaign is not reported activated or funded', () => {
  const flow = new NovaWorkflow(client());
  flow.state.observation = {campaign:{phase:3n,executionEnd:0n,reserve:0n,target:100n}};
  flow.steps();
  assert.notEqual(flow.state.steps.find(step=>step.id==='activate').status,'done');
  assert.notEqual(flow.state.steps.find(step=>step.id==='fund').status,'done');
  flow.state.observation.campaign.executionEnd = 123n; flow.steps();
  assert.equal(flow.state.steps.find(step=>step.id==='activate').status,'done');
});

test('auction and delivery failures do not fabricate result delivery', () => {
  const flow = new NovaWorkflow(client());
  for (const state of [5n,6n]) {
    flow.state.observation = {job:{state,resultHash:ZERO,settlementConfirmed:true}}; flow.steps();
    assert.notEqual(flow.state.steps.find(step=>step.id==='deliver').status,'done');
    assert.equal(flow.state.steps.find(step=>step.id==='settle').status,'done');
  }
  flow.state.observation.job.resultHash = blockHash; flow.steps();
  assert.equal(flow.state.steps.find(step=>step.id==='deliver').status,'done');
});

test('an observed terminal job is not a confirmed settlement during finality lag', () => {
  const flow = new NovaWorkflow(client());
  flow.state.observation = {job:{state:4n,resultHash:blockHash,settlementConfirmed:false}};
  flow.steps();
  assert.equal(flow.state.steps.find(step=>step.id==='deliver').status,'done');
  assert.notEqual(flow.state.steps.find(step=>step.id==='settle').status,'done');
  flow.state.observation.job.settlementConfirmed = true; flow.steps();
  assert.equal(flow.state.steps.find(step=>step.id==='settle').status,'done');
});

test('identical specifications cannot substitute a different routed plan index', () => {
  const flow = new NovaWorkflow(client()), plan = compilePlan([spec,spec]);
  flow.state.package = {plan,commitments:{}}; flow.state.seedId = '1'; flow.state.jobId = '7';
  flow.state.observation = {posted:[true,true],job:{seedId:'1',specHash:compilePlan([spec]).jobs[0].leaf,
    auctionEnd:10n,executionEnd:20n,reviewEnd:30n,due:0n}};
  flow.state.route = {seedId:'1',jobId:'7',index:1};
  assert.throws(()=>flow.workPackage(1),/Reconcile the exact MissionRouted receipt/);
  flow.verifiedRoute = {seedId:'1',jobId:'7',index:0};
  assert.throws(()=>flow.workPackage(1),/Reconcile the exact MissionRouted receipt/);
  assert.equal(flow.workPackage(0).planIndex,0);
  flow.state.jobId = '8'; assert.throws(()=>flow.workPackage(0),/Reconcile the exact MissionRouted receipt/);
});

test('native signature checks retain Python float bytes and Unicode ordering', () => {
  const body = '{"float":1.0,"nested":{"brace":"}\\\"["},"tiny":1e-07,"\ue000":1,"𐀀":2}';
  const source = `{"body":${body},"publicKey":"abc","signature":"xyz"}`;
  const envelope = JSON.parse(source);
  assert.equal(nativeSignatureBody(source,envelope),body);
  assert.notEqual(JSON.stringify(envelope.body),body);
  assert.throws(()=>nativeSignatureBody(source+'\n',envelope),/formatting changed/);
  assert.throws(()=>nativeSignatureBody(source.replace('1.0','1.0 '),envelope),/formatting changed/);
});

test('native signatures preserve large native bodies beyond capsule canonical limits', () => {
  const body = `{"evidence":"${'x'.repeat(300000)}"}`;
  const source = `{"body":${body},"publicKey":"abc","signature":"xyz"}`;
  assert.equal(nativeSignatureBody(source,JSON.parse(source)).length,body.length);
});

test('bounded ownership discovery includes received and outgoing NFTs and confirms present owner', async () => {
  const seen = [], incoming = id => ({address:seed,topics:[transfer,`0x${tuple(['address'],[bob])}`,
    `0x${tuple(['address'],[alice])}`,`0x${BigInt(id).toString(16).padStart(64,'0')}`],data:'0x',
    blockNumber:'0x2',blockHash,removed:false});
  const fake = client({identity:async()=>alice,guard(){},
    verify:async()=>({blockNumber:'0x5',blockHash}),
    read:async(method,params)=>{
      if(method==='eth_getBlockByNumber') return {number:params[0],hash:blockHash};
      if(method==='eth_getLogs') { seen.push(params[0]); return params[0].topics[1]===null ? [incoming(1),incoming(2)] : []; }
      throw Error(method);
    },call:async(contract,method,args)=> { assert.equal(method,'ownerOf'); return [args[0]==='1' ? alice : bob]; }
  });
  const flow = new NovaWorkflow(fake), found = await flow.discoverSeeds();
  assert.equal(seen.length,2); assert.equal(found.complete,true);
  assert.deepEqual(found.seeds.map(item=>item.id),['1']);
  assert.equal(seen[0].fromBlock,'0x1');
  assert.equal(seen[1].topics[1],`0x${tuple(['address'],[alice])}`);
  await assert.rejects(flow.discoverSeeds({cursor:{...found.cursor,account:bob}}),/another wallet/);
});

test('ownership cursors resume bounded windows and cannot silently switch networks', async () => {
  const fake = client({identity:async()=>alice,guard(){},verify:async()=>({blockNumber:'0x2710',blockHash}),
    read:async(method,params)=>method==='eth_getLogs' ? [] : {number:params[0],hash:blockHash}});
  const flow = new NovaWorkflow(fake), first = await flow.discoverSeeds({maxWindows:1});
  assert.equal(first.complete,false); assert.equal(first.cursor.nextBlock,'2001');
  const second = await flow.discoverSeeds({maxWindows:1,cursor:first.cursor});
  assert.equal(second.cursor.nextBlock,'4001');
  await assert.rejects(flow.discoverSeeds({cursor:{...second.cursor,chainId:31337}}),/another wallet or deployment/);
});

test('lost canonical confirmation removes completion and work-package authority', () => {
  const flow = new NovaWorkflow(client()); flow.state.mint = {hash:blockHash,status:'finalized'};
  flow.state.observation = {seed:{},campaign:{phase:2n,reserve:1n,target:1n}};
  flow.verifiedRoute = {seedId:'1',jobId:'1',index:0};
  flow.invalidateObservation(blockHash,'reorged');
  assert.equal(flow.state.observation,null); assert.equal(flow.state.mint.status,'reorged');
  assert.equal(flow.verifiedRoute,null); assert.notEqual(flow.state.steps.find(step=>step.id==='mint').status,'done');
});
