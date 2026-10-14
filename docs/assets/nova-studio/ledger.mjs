// SPDX-License-Identifier: Apache-2.0
// Read-only, receipt-reverified history. This is neither a custody account nor a reservation service.
import {address,uint} from '../ascension-wallet/protocol.mjs';
import {profileIdentity,strictJSON,deploymentIdentityStatus} from './package.mjs';
import {verifySettlementRecord} from './runtime.mjs';
import {validateProject,observeCycle,projectReservoir,proposeReinvestment,deploymentAddress} from './cycle.mjs';

const stable = value => JSON.stringify(value,(_key,item) => item && typeof item === 'object' && !Array.isArray(item) ?
  Object.fromEntries(Object.keys(item).sort().map(key => [key,item[key]])) : item);
const same = (left,right) => stable(left) === stable(right);
const hash = value => {
  if (typeof value !== 'string' || !/^0x[0-9a-fA-F]{64}$/.test(value)) throw Error('Invalid chain evidence hash.');
  return value.toLowerCase();
};
function quantity(value) {
  if (typeof value !== 'string' || !/^(0x[0-9a-fA-F]+|0|[1-9][0-9]*)$/.test(value)) throw Error('Invalid chain quantity.');
  return uint(String(BigInt(value)));
}
const amounts = row => Object.fromEntries(Object.entries(row).map(([key,value]) =>
  [key,typeof value === 'bigint' ? String(value) : value]));

/** Reverify saved settlement bytes against a caller-pinned observer and the selected exact deployment. */
export async function readProjectLedger(project,chain,{observerKey,account = chain.client.account} = {}) {
  if (typeof observerKey !== 'string' || !/^[0-9a-f]{64}$/.test(observerKey))
    throw Error('Provide the independently pinned observer public key; embedded recovery keys are not trusted.');
  const verifiedProject = await validateProject(project), client = chain.client, epoch = client.epoch;
  const deployment = profileIdentity(client.profile), owner = account ? address(account) : null;
  const contracts = Object.fromEntries(['Token','Jobs','Mark'].map(name => [name,deploymentAddress(deployment,name)]));
  const observation = await client.verify(), finalized = await client.read('eth_getBlockByNumber',['finalized',false]);
  if (!finalized?.number || !finalized.hash) throw Error('A finalized chain checkpoint is required for historical accounting.');
  const block = observation.blockNumber, seen = new Map(), recipients = new Map(), campaigns = new Map(), checkedSeeds = new Set();
  const settlements = [], refunds = [], skippedProfiles = [], closureGas = new Map();
  for (const cycle of verifiedProject.cycles) {
    for (const saved of cycle.signedRecords.filter(record => record.kind === 'settlement')) {
      // The exact historical string is authenticated; no imported status or embedded public key is sufficient.
      const record = strictJSON(saved.originalText), settlement = await verifySettlementRecord(record,observerKey);
      const attribution = `${settlement.chain.chain}:${address(settlement.chain.market)}:${settlement.chain.job}`;
      const prior = seen.get(attribution);
      if (prior) {
        if (prior.cycleId !== cycle.cycleId || !same(prior.settlement,settlement))
          throw Error('The same chain, market and job cannot be attributed to multiple cycles or conflicting settlements.');
        continue;
      }
      seen.set(attribution,{cycleId:cycle.cycleId,settlement});
      let deploymentIdentity;
      try { deploymentIdentity = deploymentIdentityStatus(cycle.package,client.profile); } catch {
        skippedProfiles.push({cycleId:cycle.cycleId,attribution,status:'requires-original-deployment'}); continue;
      }
      if (!cycle.seedId || settlement.chain.chain !== String(deployment.chainId) ||
          address(settlement.chain.market) !== contracts.Jobs ||
          address(settlement.token) !== contracts.Token || settlement.decimals !== 18)
        throw Error('Settlement does not identify this exact cycle, native token and deployment.');
      if (!checkedSeeds.has(cycle.cycleId)) {
        const genome = await chain.call('Seed','genomes',[cycle.seedId],block), pkg = cycle.package;
        if (genome[0] !== pkg.capsuleHash || genome[1] !== pkg.plan.planRoot || genome[2] !== pkg.evidenceHash ||
            String(genome[3]) !== pkg.parent || Number(genome[4]) !== pkg.plan.jobs.length)
          throw Error('The observed seed does not retain this cycle’s original package and plan commitments.');
        checkedSeeds.add(cycle.cycleId);
      }
      const jobId = String(uint(settlement.chain.job)), transactionHash = hash(settlement.transaction_hash);
      const receipt = await client.read('eth_getTransactionReceipt',[transactionHash]);
      if (!receipt || receipt.status !== '0x1' || hash(receipt.transactionHash) !== transactionHash ||
          hash(receipt.blockHash) !== hash(settlement.block?.hash) ||
          quantity(receipt.blockNumber) !== quantity(String(settlement.block?.number)))
        throw Error('Settlement receipt is missing, reverted or inconsistent with its original signed record.');
      if (quantity(receipt.blockNumber) > quantity(finalized.number) || quantity(receipt.blockNumber) > quantity(block))
        throw Error('Settlement is not finalized at the observed checkpoint.');
      const [job,seed,collected] = await Promise.all([
        client.call('Jobs','job',[jobId],block),chain.call('Mark','jobSeed',[jobId],block),
        chain.external(contracts.Mark,'function collected(uint256) view returns(bool)',[jobId],block)
      ]);
      const state = Number(job[14]), refund = uint(settlement.refund_base_units);
      if (String(seed[0]) !== cycle.seedId || address(job[0]) !== contracts.Mark ||
          ![4,5,6].includes(state) || uint(String(job[17])) !== refund || typeof job[18] !== 'boolean' ||
          typeof collected[0] !== 'boolean' || job[18] !== collected[0])
        throw Error('Current terminal job, originating campaign or refund custody does not reconcile.');
      const expected = state === 4 ? ['accepted','paid'] : state === 5 ? ['rejected','failed'] : ['unresolved_no_quorum','refunded'];
      if (settlement.job_acceptance !== expected[0] || settlement.settlement_status !== expected[1])
        throw Error('Signed acceptance and settlement labels differ from the actual terminal state.');
      const closed = chain.events(receipt,'Jobs','Closed').filter(event => String(event.id) === jobId);
      if (closed.length !== 1 || Number(closed[0].state) !== state || closed[0].refundable !== refund)
        throw Error('Exactly one matching Closed event and refund amount is required.');
      const payouts = chain.events(receipt,'Jobs','Payout').filter(event => String(event.id) === jobId);
      if (!Array.isArray(settlement.payouts) || payouts.length !== settlement.payouts.length)
        throw Error('Receipt payouts differ from the original signed accounting.');
      const paid = payouts.map((event,index) => {
        const claimed = settlement.payouts[index], recipient = address(event.recipient);
        const gross = uint(String(event.gross)), burned = uint(String(event.burned));
        if (recipient !== address(claimed.recipient) || gross !== uint(claimed.gross) || burned !== uint(claimed.burned) || burned !== gross/100n)
          throw Error('Receipt recipient, gross payout or burn differs from signed accounting.');
        if (state === 4) {
          const total = recipients.get(recipient) || {recipient,grossPayout:0n,burned:0n,netPayout:0n};
          total.grossPayout += gross; total.burned += burned; total.netPayout += gross-burned; recipients.set(recipient,total);
        }
        return {recipient,gross:String(gross),burned:String(burned),net:String(gross-burned),
          kind:state === 5 ? 'slash-refund-accrual' : 'paid-income'};
      });
      const grossTotal = paid.reduce((total,row) => total+BigInt(row.gross),0n);
      if ((state === 4 && (paid.length !== 3 || grossTotal !== uint(String(job[4])) || refund !== uint(String(job[3]))-grossTotal)) ||
          (state === 5 && (paid.length !== 1 || paid[0].recipient !== contracts.Mark ||
            grossTotal !== uint(String(job[5])) || refund !== uint(String(job[3]))+grossTotal-grossTotal/100n)) ||
          (state === 6 && (paid.length || refund !== uint(String(job[3])))))
        throw Error('Terminal payout, slashing and refund arithmetic differs from the deployed contract.');
      if (!campaigns.has(cycle.seedId)) {
        const campaign = await client.call('Mark','campaigns',[cycle.seedId],block);
        campaigns.set(cycle.seedId,{seedId:cycle.seedId,business:address(campaign[0]),reserve:String(uint(String(campaign[11]))),
          supply:String(uint(String(campaign[5]))),phase:Number(campaign[12]),spendableByBusiness:false});
      }
      const campaign = campaigns.get(cycle.seedId);
      refunds.push({cycleId:cycle.cycleId,seedId:cycle.seedId,jobId,amount:String(refund),
        status:collected[0] ? 'collected-into-campaign' : 'collectible-by-mark',
        currentCustodian:collected[0] ? (campaign.phase === 3 && campaign.supply === '0' ? null : contracts.Mark) : contracts.Jobs,
        campaignFullyReclaimed:campaign.phase === 3 && campaign.supply === '0',
        currentReserve:campaign.reserve,withdrawnToAccount:null,spendable:false,
        note:collected[0] ? 'Historical campaign inflow; current reserve is shared backing, not this refund plus reserve.' :
          'Only MARK may collect into the originating campaign; this is not a wallet balance.'});
      let gas = null;
      if (receipt.from && receipt.gasUsed != null && receipt.effectiveGasPrice != null) {
        gas = {payer:address(receipt.from),wei:String(quantity(receipt.gasUsed)*quantity(receipt.effectiveGasPrice)),transactionHash};
        if (closureGas.has(transactionHash) && !same(closureGas.get(transactionHash),gas)) throw Error('Conflicting closure gas observation.');
        closureGas.set(transactionHash,gas);
      }
      if ((await client.read('eth_getBlockByNumber',[receipt.blockNumber,false]))?.hash?.toLowerCase() !== hash(receipt.blockHash))
        throw Error('Settlement block reorganized; refresh history.');
      settlements.push({cycleId:cycle.cycleId,seedId:cycle.seedId,jobId,attribution,transactionHash,deploymentIdentity,
        blockNumber:receipt.blockNumber,blockHash:receipt.blockHash,state,jobAcceptance:expected[0],settlementStatus:expected[1],
        candidateVerdict:settlement.candidate_verdict,payouts:paid,refund:String(refund),closureGas:gas,
        trust:'pinned-observer-and-finalized-canonical-receipt',authority:'none'});
    }
  }
  await chain.canonical(observation);
  if ((await client.read('eth_getBlockByNumber',[finalized.number,false]))?.hash?.toLowerCase() !== hash(finalized.hash))
    throw Error('Finalized checkpoint changed; refresh history.');
  client.guard(epoch);
  const owned = owner ? recipients.get(owner) || {recipient:owner,grossPayout:0n,burned:0n,netPayout:0n} :
    {recipient:null,grossPayout:null,burned:null,netPayout:null};
  return {schema:'agialpha.nova-studio.receipt-ledger.v1',projectId:project.projectId,deployment,observation,
    settlements,recipients:[...recipients.values()].map(amounts),ownerTotals:{owner,...amounts(owned),
      observedClosureGasWei:owner ? String([...closureGas.values()].filter(row => row.payer === owner).reduce((total,row) => total+BigInt(row.wei),0n)) : null,
      returnedPrincipal:null},refunds,campaigns:[...campaigns.values()],closureGas:[...closureGas.values()],skippedProfiles,
    closureGasCoverage:{knownTransactions:closureGas.size,unknownTransactions:new Set(settlements.filter(row => !row.closureGas).map(row => row.transactionHash)).size},
    costs:{ethGas:null,providerCharges:null,storageCharges:null},spendableIncrease:null,profit:null,
    scope:'Saved signed settlements reverified on this deployment; not a complete account transaction history.',
    notes:['Payout history is recipient-specific and never added to current wallet balances.',
      'Collected refunds and campaign reserves overlap. Zero remaining supply establishes that lots have exited, not who received prior returns.',
      'Returned principal recipients and amounts require their own CapitalReturned receipts; they are not inferred as revenue.',
      'Closure transaction gas is partial ETH cost only; all-cycle gas, provider charges, storage charges and profit remain unknown.',
      'This read-only view grants no rights and creates no cross-project or cross-device fund reservation.']};
}

/** Create a balance-bounded suggestion; existing wallet preparation and explicit confirmations remain mandatory. */
export async function createReinvestmentProposal(project,cycleId,chain,{amount,destination,
  approvalActor = chain.client.account,rationale,risk,reservations = [],lotCount} = {}) {
  const client = chain.client, epoch = client.epoch, deployment = profileIdentity(client.profile);
  if (!destination || !same(destination.deployment,deployment)) throw Error('Select the exact currently verified destination deployment.');
  const observation = await observeCycle(project,cycleId,chain);
  const reservoir = projectReservoir(project,cycleId,observation,{reservations});
  let quote = null;
  if (lotCount !== undefined) {
    const count = uint(lotCount,32);
    if (!count) throw Error('Propose at least one lot.');
    const campaign = await client.call('Mark','campaigns',[destination.seedId],observation.blockNumber);
    const checkpoint = await client.read('eth_getBlockByNumber',[observation.blockNumber,false]);
    if (Number(campaign[12]) !== 1 || quantity(checkpoint.timestamp) >= uint(String(campaign[9])) ||
        uint(String(campaign[5]))+count > uint(String(campaign[4]))) throw Error('Destination is not open for the proposed lot count.');
    const [cost] = await client.call('Mark','quote',[String(campaign[5]),lotCount,String(campaign[1]),String(campaign[2])],observation.blockNumber);
    if (!uint(String(cost)) || uint(String(cost)) > uint(amount)) throw Error('Current lot quote exceeds the proposed maximum cost.');
    quote = {lotCount,baseUnits:String(cost),maxCost:amount,blockNumber:observation.blockNumber,blockHash:observation.blockHash,
      status:'read-only-quote; refresh in existing wallet preparation'};
  }
  await chain.canonical(observation); client.guard(epoch);
  const proposal = proposeReinvestment(reservoir,{sourceOwner:client.account,amount,destination,approvalActor,rationale,risk});
  return {...proposal,quote,observation,availableForProposal:reservoir.availableForProposal,
    allocation:'none; this proposal does not reserve funds',actualSpend:'none; no transaction has been prepared or sent'};
}
