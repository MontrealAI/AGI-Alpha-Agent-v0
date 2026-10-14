// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {canonical,digest} from '../../docs/assets/successor/engine.mjs';
import {CONTRACTS} from '../../docs/assets/ascension-wallet/protocol.mjs';
import {createPackage,hashBytes,objectHash,fileBytes,recoverPackage} from '../../docs/assets/nova-studio/package.mjs';
import {sealSeed} from '../../docs/assets/ascension/crypto.mjs';
import {createProject,updateCycle,addCycle,preserveSignedRecord} from '../../docs/assets/nova-studio/cycle.mjs';
import {StudioChain,INTERFACES} from '../../docs/assets/nova-studio/chain.mjs';
import {readProjectLedger,createReinvestmentProposal} from '../../docs/assets/nova-studio/ledger.mjs';

const profile = {chainId:1,profile:'archived-read-only-ledger-fixture',sourceSHA256:'a'.repeat(64),abiSHA256:'b'.repeat(64),
  contracts:Object.fromEntries(Object.entries(CONTRACTS).filter(([key]) => key !== 'Token').map(([key,value]) => [key,{address:value,sha256:'c'.repeat(64)}]))};
const who = '0x1111111111111111111111111111111111111111', reviewer = '0x2222222222222222222222222222222222222222';
const other = '0x3333333333333333333333333333333333333333', h = digit => '0x'+digit.repeat(64);
const key = generateKeyPairSync('ed25519'), observerKey = key.publicKey.export({format:'der',type:'spki'}).subarray(-32).toString('hex');
const encoder = new TextEncoder(), passphrase = 'a separate ledger fixture passphrase';
const pkg = await createPackage({title:'Ledger fixture',description:'Synthetic read-only RPC observations',evidence:'Local tests only.',
  jobs:[{goal:'Report exact computation',successMetric:'Truthful positive or negative result',bounty:'10000',duration:86400,priceWeight:6000}]},passphrase,profile);
async function historicalPackage() {
  const deployment = {chainId:profile.chainId,profile:profile.profile,
    contracts:Object.fromEntries(Object.entries(CONTRACTS).map(([name,value])=>[name,value.toLowerCase()]))};
  const evidence = {...pkg.evidence,deployment}, evidenceHash = await objectHash(evidence);
  const capsule = await sealSeed({...await recoverPackage(pkg,passphrase),deployment,evidenceHash},passphrase);
  return {...pkg,deployment,evidence,evidenceHash,capsule,capsuleHash:await objectHash(capsule),capsuleByteHash:await hashBytes(fileBytes(capsule))};
}
async function journal(settlement) {
  const body = {schema:1,sequence:1,previous:'0'.repeat(64),identity:'urn:agialpha:ed25519:'+observerKey,
    mission:'@successor:ascension:settlement:'+await digest('settlement-job',settlement.chain),time_ns:'1700000000000000000',
    document:{settlement,state:'imported'}};
  const canonical_body = canonical(body).replace(/"time_ns":"([1-9][0-9]*)"}$/, '"time_ns":$1}');
  const hash = (await hashBytes(encoder.encode(canonical_body))).slice(2);
  return {schema:'agialpha.ascension.journal-settlement.v1',public_key:observerKey,canonical_body,hash,
    signature:sign(null,Buffer.from(hash,'hex'),key.privateKey).toString('base64'),settlement};
}
function event(name,values,index) {
  const data = INTERFACES.Jobs.encodeEventLog(INTERFACES.Jobs.getEvent(name),values);
  return {address:CONTRACTS.Jobs,...data,logIndex:'0x'+index.toString(16),removed:false,
    transactionHash:h('c'),blockHash:h('a'),blockNumber:'0x10'};
}
async function fixture({state = 4,collected = false,fullyReclaimed = false,sourcePackage = pkg} = {}) {
  let project = await createProject(sourcePackage);
  project = await updateCycle(project,project.activeCycleId,{seedId:'7',jobIds:['12']});
  const payouts = state === 4 ? [{recipient:who,gross:'6800',burned:'68'},{recipient:reviewer,gross:'600',burned:'6'},
    {recipient:other,gross:'600',burned:'6'}] : state === 5 ? [{recipient:CONTRACTS.Mark,gross:'1000',burned:'10'}] : [];
  const refund = state === 4 ? '2000' : state === 5 ? '10990' : '10000';
  const labels = state === 4 ? ['accepted','paid'] : state === 5 ? ['rejected','failed'] : ['unresolved_no_quorum','refunded'];
  const settlement = {schema_version:1,chain:{chain:'1',market:CONTRACTS.Jobs.toLowerCase(),job:'12'},
    transaction_hash:h('c'),block:{number:16,hash:h('a')},job_acceptance:labels[0],settlement_status:labels[1],
    payouts,refund_base_units:refund,token:CONTRACTS.Token,decimals:18,candidate_verdict:'FAIL'};
  project = await preserveSignedRecord(project,{kind:'settlement',originalText:JSON.stringify(await journal(settlement))});
  const report = {chainId:'0x1',blockNumber:'0x30',blockHash:h('b'),blockTime:'0x100',observedAt:new Date().toISOString()};
  const receipt = {status:'0x1',transactionHash:h('c'),blockNumber:'0x10',blockHash:h('a'),from:reviewer,
    gasUsed:'0x5208',effectiveGasPrice:'0x64',logs:[...payouts.map((row,i) => event('Payout',['12',row.recipient,row.gross,row.burned],i)),
      event('Closed',['12',state,refund],payouts.length)]};
  const job = [CONTRACTS.Mark,other,who,10000n,8000n,1000n,0n,0n,0n,0n,0n,0n,0n,0n,BigInt(state),h('e'),h('f'),BigInt(refund),collected];
  const campaign = [other,100n,0n,1000n,100n,fullyReclaimed ? 0n : 10n,1n,0n,0n,10000n,0n,
    fullyReclaimed ? 0n : collected ? BigInt(refund) : 0n,3n,h('0')];
  const client = {profile,contracts:CONTRACTS,epoch:0,pending:null,account:who,async verify(){return report;},
    guard(epoch){if (this.epoch !== epoch) throw Error('Epoch changed.');},
    async read(method,args) {
      if (method === 'eth_getTransactionReceipt') return receipt;
      if (method === 'eth_getBlockByNumber') {
        if (args[0] === 'finalized' || args[0] === '0x2f') return {number:'0x2f',hash:h('d'),timestamp:'0x100'};
        if (args[0] === '0x10') return {number:'0x10',hash:h('a'),timestamp:'0x80'};
        return {number:'0x30',hash:report.blockHash,timestamp:'0x100'};
      }
      throw Error('Unexpected RPC '+method);
    },
    async call(contract,method) {
      if (contract === 'Jobs' && method === 'job') return job;
      if (contract === 'Mark' && method === 'campaigns') return campaign;
      if (contract === 'Mark' && method === 'quote') return [100n];
      throw Error('Unexpected read '+contract+'.'+method);
    }};
  const chain = new StudioChain(client);
  chain.call = async (contract,method) => {
    if (contract === 'Seed' && method === 'genomes') return [sourcePackage.capsuleHash,sourcePackage.plan.planRoot,sourcePackage.evidenceHash,0n,1n,who];
    if (contract === 'Mark' && method === 'jobSeed') return [7n];
    throw Error('Unexpected Studio read '+contract+'.'+method);
  };
  chain.external = async () => [collected];
  chain.seed = async () => ({verification:report,wallet:{account:who,balance:1000n,stake:{Jobs:50n,Oracle:0n,
    agentLocked:0n,validatorLockedUntil:0n}},campaign:{business:other,supply:10n,reserve:2000n,phase:3n,base:100n,slope:0n},yourLots:0n});
  return {project,chain,client,receipt,settlement,campaign,job,report};
}

test('reverify exact signed records and actual receipt events; keep payout recipients, refunds and closure gas separate',async()=>{
  const f = await fixture(), ledger = await readProjectLedger(f.project,f.chain,{observerKey});
  assert.deepEqual(ledger.ownerTotals,{owner:who,recipient:who,grossPayout:'6800',burned:'68',netPayout:'6732',
    observedClosureGasWei:'0',returnedPrincipal:null});
  assert.equal(ledger.recipients.length,3);assert.equal(ledger.refunds[0].status,'collectible-by-mark');
  assert.equal(ledger.refunds[0].amount,'2000');assert.equal(ledger.refunds[0].spendable,false);
  assert.equal(ledger.closureGas[0].payer,reviewer);assert.equal(ledger.closureGas[0].wei,'2100000');
  assert.equal(ledger.profit,null);assert.equal(ledger.spendableIncrease,null);assert.equal(ledger.costs.ethGas,null);
  assert.equal(ledger.settlements[0].candidateVerdict,'FAIL');
  const payer = await readProjectLedger(f.project,f.chain,{observerKey,account:reviewer});
  assert.equal(payer.ownerTotals.netPayout,'594');assert.equal(payer.ownerTotals.observedClosureGasWei,'2100000');
  const unconnected = await readProjectLedger(f.project,f.chain,{observerKey,account:null});
  assert.equal(unconnected.ownerTotals.grossPayout,null);assert.equal(unconnected.ownerTotals.netPayout,null);
  assert.equal(unconnected.ownerTotals.observedClosureGasWei,null);assert.equal(unconnected.recipients.length,3);
  delete f.receipt.effectiveGasPrice;
  const missingGas = await readProjectLedger(f.project,f.chain,{observerKey});
  assert.deepEqual(missingGas.closureGasCoverage,{knownTransactions:0,unknownTransactions:1});
  assert.equal(missingGas.costs.ethGas,null);
  const collected = await fixture({collected:true,fullyReclaimed:true});
  const exit = await readProjectLedger(collected.project,collected.chain,{observerKey});
  assert.equal(exit.refunds[0].campaignFullyReclaimed,true);assert.equal(exit.refunds[0].currentCustodian,null);
  assert.equal(exit.refunds[0].withdrawnToAccount,null);assert.equal(exit.campaigns[0].reserve,'0');
});

test('failed slash event accrues into refundable campaign custody and no-quorum refund is not paid income',async()=>{
  for (const state of [5,6]) {
    const f = await fixture({state}), ledger = await readProjectLedger(f.project,f.chain,{observerKey});
    assert.equal(ledger.recipients.length,0);assert.equal(ledger.ownerTotals.netPayout,'0');
    assert.equal(ledger.refunds[0].amount,state === 5 ? '10990' : '10000');
    if (state === 5) assert.equal(ledger.settlements[0].payouts[0].kind,'slash-refund-accrual');
  }
});

test('legacy ledger history remains labeled and immutable while current descriptors reject same-address source changes',async()=>{
  for (const [original,status] of [[pkg,'exact-source'],[await historicalPackage(),'legacy-addresses']]) {
    const before = JSON.stringify(original), f = await fixture({sourcePackage:original});
    const ledger = await readProjectLedger(f.project,f.chain,{observerKey});
    assert.equal(ledger.settlements[0].deploymentIdentity,status);assert.equal(ledger.ownerTotals.netPayout,'6732');
    assert.equal(ledger.refunds[0].currentCustodian,CONTRACTS.Jobs.toLowerCase());
    assert.equal(JSON.stringify(f.project.cycles[0].package),before);assert.equal(JSON.stringify(original),before);
    f.campaign[12] = 1n;
    const proposal = await createReinvestmentProposal(f.project,f.project.activeCycleId,f.chain,{amount:'100',lotCount:'1',
      destination:{deployment:pkg.deployment,seedId:'8'},rationale:'A separately reviewed task',risk:'Possible principal loss.'});
    assert.equal(proposal.observation.deploymentIdentity,status);assert.equal(proposal.quote.baseUnits,'100');
  }
  const f = await fixture();f.client.profile={...profile,sourceSHA256:'f'.repeat(64)};
  const skipped = await readProjectLedger(f.project,f.chain,{observerKey});
  assert.equal(skipped.settlements.length,0);assert.equal(skipped.skippedProfiles.length,1);
  await assert.rejects(createReinvestmentProposal(f.project,f.project.activeCycleId,f.chain,{amount:'100',
    destination:{deployment:pkg.deployment,seedId:'8'}}),/exact currently verified destination/);
});

test('imports, wrong observer, changed receipts, unsafe finality, reorg and cross-cycle duplicate attribution fail closed',async()=>{
  const f = await fixture();
  await assert.rejects(readProjectLedger(f.project,f.chain,{observerKey:'0'.repeat(64)}));
  f.receipt.status = '0x0';await assert.rejects(readProjectLedger(f.project,f.chain,{observerKey}),/receipt/);f.receipt.status = '0x1';
  const logs = f.receipt.logs;f.receipt.logs = logs.slice(1);
  await assert.rejects(readProjectLedger(f.project,f.chain,{observerKey}),/payouts/);f.receipt.logs = logs;
  f.receipt.logs[0].removed = true;await assert.rejects(readProjectLedger(f.project,f.chain,{observerKey}),/canonical receipt/);
  f.receipt.logs[0].removed = false;
  f.receipt.logs[0].blockHash = h('f');
  await assert.rejects(readProjectLedger(f.project,f.chain,{observerKey}),/canonical receipt/);
  f.receipt.logs[0].blockHash = h('a');
  const read = f.client.read;f.client.read = async (method,args) => method === 'eth_getBlockByNumber' && args[0] === 'finalized' ?
    {number:'0xf',hash:h('d')} : read.call(f.client,method,args);
  await assert.rejects(readProjectLedger(f.project,f.chain,{observerKey}),/finalized/);f.client.read = read;
  f.client.read = async (method,args) => method === 'eth_getBlockByNumber' && args[0] === '0x10' ?
    {number:'0x10',hash:h('f')} : read.call(f.client,method,args);
  await assert.rejects(readProjectLedger(f.project,f.chain,{observerKey}),/reorganized/);f.client.read = read;
  const childPkg = await createPackage({title:'Child',description:'Separate cycle',evidence:'Fresh evidence',parent:'7',
    jobs:pkg.plan.jobs.map(row=>({...row.spec,goal:'A distinct second computation'}))},passphrase,profile);
  let duplicate = await addCycle(f.project,childPkg);
  duplicate = await updateCycle(duplicate,duplicate.activeCycleId,{seedId:'8'});
  duplicate = await preserveSignedRecord(duplicate,{kind:'settlement',originalText:JSON.stringify(await journal(f.settlement),null,2)});
  await assert.rejects(readProjectLedger(duplicate,f.chain,{observerKey}),/multiple cycles/);
});

test('reinvestment refreshes real ownership and exact quote, deducts supplied obligations and never sends or allocates',async()=>{
  const f = await fixture();f.campaign[12] = 1n;
  const options = {amount:'100',destination:{deployment:pkg.deployment,seedId:'8'},approvalActor:who,
    rationale:'Fund a fresh committed task',risk:'Loss of principal is possible.',lotCount:'1'};
  const proposal = await createReinvestmentProposal(f.project,f.project.activeCycleId,f.chain,options);
  assert.equal(proposal.status,'proposal-only');assert.equal(proposal.quote.baseUnits,'100');assert.equal(proposal.exactCalls,null);
  assert.equal(proposal.actualSpend,'none; no transaction has been prepared or sent');
  const reservation = {reservationId:'other-project',projectId:crypto.randomUUID(),chainId:1,asset:CONTRACTS.Token,
    owner:who,amount:'901',status:'planned'};
  await assert.rejects(createReinvestmentProposal(f.project,f.project.activeCycleId,f.chain,{...options,reservations:[reservation]}),/exceeds/);
  await assert.rejects(createReinvestmentProposal(f.project,f.project.activeCycleId,f.chain,{...options,amount:'99'}),/quote/);
  await assert.rejects(createReinvestmentProposal(f.project,f.project.activeCycleId,f.chain,{...options,approvalActor:other}),/owned/);
  f.client.pending = {status:'submission-unknown'};
  await assert.rejects(createReinvestmentProposal(f.project,f.project.activeCycleId,f.chain,options),/exceeds/);
});
