// SPDX-License-Identifier: Apache-2.0
// Fixed disposable keys and mocked read-only RPC; no network or wallet qualification.
const test=require('node:test'),assert=require('node:assert/strict'),E=require('ethers');
const P=require('../scripts/mainnet-authority'),L=require('../scripts/mainnet'),C=require('../scripts/deploy-mainnet-creator'),V=require('../scripts/authority-verification-package'),R=require('../scripts/authority-rpc');
const {AGIALPHA_ADDRESS:TOKEN}=require('../../../token.config');
const creator=new E.Wallet('0x'+'11'.repeat(32)).address,governor='0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99',pin={number:100,hash:E.id('synthetic conventional pin')};
const revision={commit:'a'.repeat(40),tree:'b'.repeat(40),lockSha256:'c'.repeat(64)};
function config(){return {schema:'agialpha.mainnet.config.v2',chainId:1,deployer:creator,nonce:0,block:pin,governor:{kind:'ledger-eoa',address:governor,addressAcknowledgement:governor},dependencies:Object.fromEntries(Object.entries({token:TOKEN,ens:L.ENS,wrapper:L.WRAPPER}).map(([k,address])=>[k,{address,codeHash:E.keccak256('0x6000')}])),rootOwners:Object.fromEntries(L.roots.map(n=>[n,governor])),parameters:{minimumValidatorStake:'10000000000000000000',minimumAgentStake:'10000000000000000000',quorum:2,maximumRiskBps:2000},sender:{mode:P.CONVENTIONAL},envelope:{gasLimit:'8000000',maxFeePerGas:'10000000000',maxPriorityFeePerGas:'1000000000',accessList:[]}};}
function journal(c){return {schema:'ethereum.cross-project-nonce-journal.v1',journalId:'synthetic-conventional',revision:1,chainId:1,sender:c.deployer,scope:['alpha','jobs','manager'],block:c.block,latestNonce:0,pendingNonce:0,allocations:[{project:'alpha',startNonce:0,count:5},{project:'jobs',startNonce:5,count:1},{project:'manager',startNonce:6,count:1}]};}
const compiled=P.compiledContracts();
function rpc(c,code,changes={}){return async(method,args)=>{
 if(changes[method])return changes[method](args);
 if(method==='eth_chainId')return '0x1';
 if(method==='eth_getBlockByNumber')return {number:'0x64',hash:pin.hash,timestamp:'0x100',gasLimit:'0x1c9c380'};
 if(method==='eth_getCode'){const a=args[0].toLowerCase();if(a===creator.toLowerCase())return code;if(Object.values(c.dependencies).some(d=>d.address.toLowerCase()===a))return '0x6000';if(a===governor.toLowerCase()||Object.values(planAddresses).some(v=>v.toLowerCase()===a))return '0x';throw Error('Unexpected wallet-target read');}
 if(method==='eth_getTransactionCount')return '0x0';
 if(method==='eth_call'){const {data}=args[0],coder=E.AbiCoder.defaultAbiCoder();if(data.startsWith(E.id('decimals()').slice(0,10)))return coder.encode(['uint8'],[18]);if(data.startsWith(E.id('owner(bytes32)').slice(0,10)))return coder.encode(['address'],[governor]);throw Error('Unexpected wallet-state call');}
 throw Error('Unexpected RPC '+method);
};}
const planAddresses=Object.fromEntries(P.NAMES.map((n,i)=>[n,E.getCreateAddress({from:creator,nonce:i})]));
test('conventional profile is exact, has no reports and preserves governor/envelope validation',async()=>{
 const c=config();assert.doesNotThrow(()=>P.validateConfig(c));for(const key of ['target','targetCodeHash','storageChecks','qualification','delegationCode'])assert.throws(()=>P.validateConfig({...c,sender:{...c.sender,[key]:null}}));
 const plan=await P.makePlan(c,compiled,revision,journal(c));assert.equal(plan.directOriginationEvidence,undefined);await assert.rejects(P.makePlan(c,compiled,revision,journal(c),{}));
 assert.equal(plan.governanceCalls.length,2);assert.match(C.creatorReview(plan).assurance,/Conventional transaction correctness only/);
 const bundle=await V.plannedPackage(plan,revision,compiled);assert.equal(bundle.manifest.senderMode,P.CONVENTIONAL);assert.match(bundle.manifest.originationScope,/no-invocation/);assert.equal(bundle.files['origination-evidence.json'],undefined);
 assert.equal(R.scopeForPlan(plan).noCall,undefined);assert(!P.signingBoundary(plan).requiredExecutorChecks.some(x=>x.includes("delegation")));
 for(const tx of plan.transactions){assert.equal(tx.envelope.type,2);assert.equal(tx.envelope.to,null);assert.equal(tx.envelope.value,'0');assert.deepEqual(tx.envelope.accessList,[]);}
 assert.throws(()=>P.validateConfig({...c,deployer:governor}),/separate/);assert.throws(()=>P.validateConfig({...c,envelope:{...c.envelope,authorizationList:[]}}));
});
for(const code of ['0x','0xef0100'+'22'.repeat(20),'0xef0100'+TOKEN.slice(2).toLowerCase(),'0x6000'])test('conventional code observation adds no eligibility gate: '+code,async()=>{
 const c=config(),plan=await P.makePlan(c,compiled,revision,journal(c));const result=await P.preflight(plan,rpc(c,code),revision);assert.equal(result.preflightPassed,true);assert.equal(result.nextIndex,0);assert.equal(result.readyToBroadcast,false);
 // Arbitrary contract code is deliberately not approved here; actual node validation remains authoritative.
 const old={...c,sender:{mode:P.EMPTY}},oldPlan=await P.makePlan(old,compiled,revision,journal(old));if(code!=='0x')await assert.rejects(P.preflight(oldPlan,rpc(old,code),revision),/Empty-code/);
 await assert.rejects(P.preflight(plan,rpc(c,code,{'eth_chainId':()=> '0x2'}),revision),/chain/);
 await assert.rejects(P.preflight(plan,rpc(c,code,{'eth_getTransactionCount':()=> '0x1'}),revision),/nonce drift/);
});
