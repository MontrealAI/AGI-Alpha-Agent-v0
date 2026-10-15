// SPDX-License-Identifier: Apache-2.0
import { Interface, id, zeroPadValue, toQuantity } from './vendor/ethers-6.17.0.mjs';
import { address, uint } from '../ascension-wallet/protocol.mjs';
import { assertSupportedEnvelope } from '../ascension-wallet/client.mjs';
import { leaf, pair, verifyPlan } from './plan.mjs';
import { verifyPackage } from './package.mjs';
const ABIS = {
  Seed:[
    'function seal(bytes32,bytes32,uint32,string,uint256,bytes32) returns(uint256)',
    'function tokenURI(uint256) view returns(string)',
    'function genomes(uint256) view returns(bytes32 capsuleHash,bytes32 planRoot,bytes32 evidenceHash,uint256 parent,uint32 jobs,address creator)',
    'event SeedSealed(uint256 indexed seedId,address indexed creator,bytes32 capsuleHash,bytes32 planRoot,uint256 parent,bytes32 evidenceHash)',
    'event Transfer(address indexed from,address indexed to,uint256 indexed tokenId)'
  ],
  Access:[
    'function admission(address) view returns(bytes32 evidence,uint64 until)',
    'function ens() view returns(address)', 'function wrapper() view returns(address)',
    'function roots(uint8) view returns(bytes32)'
  ],
  Oracle:[
    'function rounds(uint256) view returns(uint64 number,uint64 until,uint16 yes,uint16 no,address owner)',
    'function quorum() view returns(uint16)', 'function maximumRiskBps() view returns(uint16)',
    'function voted(uint256,uint64,address) view returns(bool)'
  ],
  Jobs:[
    'function REVIEW_WINDOW() view returns(uint32)', 'function VALIDATOR_BPS() view returns(uint16)',
    'function committees(uint256,uint256) view returns(address)',
    'event Closed(uint256 indexed id,uint8 state,uint256 refundable)',
    'event Payout(uint256 indexed id,address indexed recipient,uint256 gross,uint256 burned)'
  ],
  Mark:[
    'function route(uint256,uint32,(string goal,string successMetric,uint96 bounty,uint32 duration,uint16 priceWeight),bytes32[],uint32,address[3]) returns(uint256)',
    'function posted(uint256,uint32) view returns(bool)', 'function jobSeed(uint256) view returns(uint256)',
    'event MissionRouted(uint256 indexed id,uint32 indexed index,uint256 indexed jobId,bytes32 leaf)',
    'event Bloomed(uint256 indexed id,bytes32 indexed businessNode,bytes32 planRoot,uint256 funding)',
    'event CapitalReturned(uint256 indexed id,address indexed account,uint256 amount)'
  ]
};
export const INTERFACES = Object.fromEntries(Object.entries(ABIS).map(([key,abi]) => [key,new Interface(abi)]));
export class StudioChain {
  constructor(client) { this.client = client; }
  async call(contract, method, args = [], block = 'latest') {
    const iface = INTERFACES[contract];
    if (!iface?.getFunction(method)) throw Error('Unknown Studio read.');
    const data = iface.encodeFunctionData(method,args);
    return iface.decodeFunctionResult(method,await this.client.read('eth_call',[{to:this.client.contracts[contract],data},block]));
  }
  async external(contractAddress, signature, args, block) {
    const iface = new Interface([signature]), fragment = iface.fragments[0];
    return iface.decodeFunctionResult(fragment,await this.client.read('eth_call',[
      {to:address(contractAddress),data:iface.encodeFunctionData(fragment,args)},block]));
  }
  async identity(who = this.client.account, role = '0') {
    if (!who) throw Error('Connect the relevant actor’s wallet first.');
    const report = await this.client.verify(), block = report.blockNumber;
    const [node] = await this.client.call('Access','names',[who,role],block);
    const [admission, governor, admitted, eligible, ens, wrapper] = await Promise.all([
      this.call('Access','admission',[who],block), this.client.call('Access','owner',[],block),
      this.client.call('Access','admitted',[who],block), this.client.call('Access','eligible',[who,role],block),
      this.call('Access','ens',[],block), this.call('Access','wrapper',[],block)
    ]);
    let nameOwner = null, wrapped = null;
    const [namespaceRoot]=await this.call('Access','roots',[role],block);
    let [namespaceAdministrator]=await this.external(ens[0],'function owner(bytes32) view returns(address)',[namespaceRoot],block);
    if (address(namespaceAdministrator)===address(wrapper[0]) && BigInt(wrapper[0])!==0n)
      [namespaceAdministrator]=await this.external(wrapper[0],'function getData(uint256) view returns(address,uint32,uint64)',[BigInt(namespaceRoot)],block);
    if (BigInt(node) !== 0n) {
      [nameOwner] = await this.external(ens[0],'function owner(bytes32) view returns(address)',[node],block);
      if (address(nameOwner) === address(wrapper[0]) && BigInt(wrapper[0]) !== 0n) {
        const v = await this.external(wrapper[0],'function getData(uint256) view returns(address,uint32,uint64)',[BigInt(node)],block);
        wrapped = {owner:v[0],fuses:String(v[1]),expiry:String(v[2])};
      }
    }
    await this.canonical(report);
    return { who, role, node, nameOwner, wrapped, namespaceRoot, namespaceAdministrator, governor:governor[0], admitted:admitted[0], eligible:eligible[0],
      admission:{evidence:admission[0],until:String(admission[1])}, blockNumber:block };
  }
  async canonical(report) {
    if ((await this.client.read('eth_getBlockByNumber',[report.blockNumber,false]))?.hash !== report.blockHash)
      throw Error('Observation reorganized. Refresh before continuing.');
  }
  async seed(seedId, pkg = null) {
    uint(seedId); if (!BigInt(seedId)) throw Error('Seed ID must be positive.');
    const state = await this.client.inspect(seedId), block = state.verification.blockNumber;
    const [genome, uri, round, quorum, threshold, window, fees] = await Promise.all([
      this.call('Seed','genomes',[seedId],block),this.call('Seed','tokenURI',[seedId],block),
      this.call('Oracle','rounds',[seedId],block),this.call('Oracle','quorum',[],block),
      this.call('Oracle','maximumRiskBps',[],block),this.call('Jobs','REVIEW_WINDOW',[],block),this.call('Jobs','VALIDATOR_BPS',[],block)
    ]);
    state.seedId = seedId; state.metadataURI = uri[0];
    state.genome = {capsuleHash:genome[0],planRoot:genome[1],evidenceHash:genome[2],parent:String(genome[3]),jobs:Number(genome[4]),creator:genome[5]};
    state.review = {round:String(round[0]),until:String(round[1]),yes:Number(round[2]),no:Number(round[3]),owner:round[4],quorum:Number(quorum[0]),maximumRiskBps:Number(threshold[0])};
    state.reviewWindow = Number(window[0]); state.validatorBps = Number(fees[0]);
    if (pkg) {
      await verifyPackage(pkg,this.client.profile);
      if (genome[0] !== pkg.capsuleHash || genome[1] !== pkg.plan.planRoot || genome[2] !== pkg.evidenceHash ||
          String(genome[3]) !== pkg.parent || Number(genome[4]) !== pkg.plan.jobs.length)
        throw Error('This package does not match the immutable seed commitments.');
    }
    await this.canonical(state.verification); return state;
  }
  async inspectJob(seedId, jobId, pkg = null) {
    uint(jobId); if (!BigInt(jobId)) throw Error('Job ID must be positive.');
    const state=await this.seed(seedId,pkg), block=state.verification.blockNumber;
    const values=await this.client.call('Jobs','job',[jobId],block);
    const keys=['client','business','worker','bounty','price','bond','auctionEnd','executionEnd','reviewEnd','due',
      'duration','priceWeight','yes','no','state','specHash','resultHash','refund','claimed'];
    const job=Object.fromEntries(keys.map((key,index)=>[key,values[index]]));
    if (String((await this.call('Mark','jobSeed',[jobId],block))[0])!==String(seedId))
      throw Error('Job does not belong to this seed’s MARK campaign.');
    const delivered=BigInt(job.resultHash)!==0n;
    job.settlement=job.state===4n?'accepted-payment':job.state===5n?
      delivered?'reviewer-rejection-with-slashing':'delivery-timeout-with-slashing':job.state===6n?
        delivered?'missing-review-quorum-refund':'no-eligible-winner-refund':'not-settled';
    job.settlementConfirmed=false;
    if (job.state>=4n) {
      const epoch=this.client.epoch;
      try {
        const finalized=await this.client.read('eth_getBlockByNumber',['finalized',false]);
        if (!finalized?.number || !finalized?.hash) throw Error('Finality is unavailable.');
        const observed=await this.client.call('Jobs','job',[jobId],finalized.number);
        await this.canonical({blockNumber:finalized.number,blockHash:finalized.hash});
        job.settlementConfirmed=observed[14]===job.state && observed[16]===job.resultHash && observed[17]===job.refund;
        job.settlementFinality={blockNumber:finalized.number,blockHash:finalized.hash};
      } catch { this.client.guard(epoch); }
    }
    await this.canonical(state.verification); state.job=job; return state;
  }
  events(receipt, contract, event) {
    if (receipt?.status!=='0x1' || !/^0x[0-9a-f]{64}$/i.test(receipt.transactionHash) ||
        !/^0x[0-9a-f]{64}$/i.test(receipt.blockHash) || !/^0x[0-9a-f]+$/i.test(receipt.blockNumber) ||
        !Array.isArray(receipt.logs) || receipt.logs.length > 10000) throw Error('Malformed successful receipt logs.');
    const iface = INTERFACES[contract], topic = iface.getEvent(event).topicHash;
    return receipt.logs.filter(log => address(log.address) === address(this.client.contracts[contract]) && log.topics?.[0] === topic)
      .map(log => {
        if (log.removed || log.transactionHash?.toLowerCase()!==receipt.transactionHash.toLowerCase() ||
            log.blockHash?.toLowerCase()!==receipt.blockHash.toLowerCase() || log.blockNumber!==receipt.blockNumber)
          throw Error('Event does not belong to this canonical receipt transaction and block.');
        return iface.parseLog(log).args;
      });
  }
  async verifyMint(record, pkg, publication) {
    if (!['finalized','effect-unverified'].includes(record.status) || !record.finalized || record.action !== 'seal')
      throw Error('Mint has not finalized as the original action.');
    const intent=INTERFACES.Seed.encodeFunctionData('seal',[pkg.capsuleHash,pkg.plan.planRoot,pkg.plan.jobs.length,
      publication.metadataURI,pkg.parent,pkg.evidenceHash]);
    if (record.transaction.data.toLowerCase()!==intent.toLowerCase()) throw Error('Mint intent differs from the exact package.');
    const matches = this.events(record.receipt,'Seed','SeedSealed').filter(e =>
      address(e.creator) === address(record.transaction.from) && e.capsuleHash === pkg.capsuleHash && e.planRoot === pkg.plan.planRoot &&
      String(e.parent) === pkg.parent && e.evidenceHash === pkg.evidenceHash);
    if (matches.length !== 1) throw Error('Receipt must contain exactly one matching SeedSealed event.');
    const seedId = String(matches[0].seedId), state = await this.seed(seedId,pkg);
    const transfers=this.events(record.receipt,'Seed','Transfer').filter(e=>String(e.tokenId)===seedId &&
      BigInt(e.from)===0n && address(e.to)===address(record.transaction.from));
    if (transfers.length!==1 || address(state.genome.creator)!==address(record.transaction.from))
      throw Error('Mint requires its exact zero-address NFT transfer and immutable creator readback.');
    if (state.metadataURI !== publication.metadataURI) throw Error('Minted tokenURI differs from the published metadata.');
    await this.canonical({blockNumber:record.receipt.blockNumber,blockHash:record.receipt.blockHash});
    return state;
  }
  async openMintReceipt(hash, pkg = null) {
    const c=this.client; await c.verify();
    if (!/^0x[0-9a-fA-F]{64}$/.test(hash)) throw Error('Use a transaction hash, not a predicted NFT ID.');
    const receipt=await c.read('eth_getTransactionReceipt',[hash]), tx=await c.read('eth_getTransactionByHash',[hash]);
    assertSupportedEnvelope(tx);
    if (!receipt || receipt.status!=='0x1' || receipt.transactionHash?.toLowerCase()!==hash.toLowerCase() ||
        !tx || tx.hash?.toLowerCase()!==hash.toLowerCase() || BigInt(tx.chainId)!==BigInt(c.profile.chainId) ||
        address(tx.to)!==address(c.contracts.Seed) || BigInt(tx.value)!==0n || tx.blockHash!==receipt.blockHash ||
        tx.blockNumber!==receipt.blockNumber || address(tx.from)!==address(receipt.from) || address(tx.to)!==address(receipt.to))
      throw Error('Not a successful direct mint transaction for this deployment.');
    const parsed=INTERFACES.Seed.parseTransaction({data:tx.input,value:tx.value});
    if (parsed?.name!=='seal') throw Error('Transaction was not a direct seal call.');
    const events=this.events(receipt,'Seed','SeedSealed');
    if (events.length!==1) throw Error('Ambiguous mint receipt.');
    const e=events[0], a=parsed.args;
    if (address(e.creator)!==address(tx.from) || e.capsuleHash!==a[0] || e.planRoot!==a[1] || e.parent!==a[4] || e.evidenceHash!==a[5])
      throw Error('Mint event does not match transaction intent.');
    const transfers=this.events(receipt,'Seed','Transfer').filter(log=>log.tokenId===e.seedId &&
      BigInt(log.from)===0n && address(log.to)===address(tx.from));
    if (transfers.length!==1) throw Error('Mint receipt is missing its exact NFT ownership transfer.');
    const finalized=await c.read('eth_getBlockByNumber',['finalized',false]);
    if (!finalized || BigInt(finalized.number)<BigInt(receipt.blockNumber)) throw Error('Mint receipt is not finalized yet.');
    const state=await this.seed(String(e.seedId),pkg);
    if (state.genome.capsuleHash!==a[0] || state.genome.planRoot!==a[1] || state.genome.jobs!==Number(a[2]) ||
        state.metadataURI!==a[3] || state.genome.parent!==String(a[4]) || state.genome.evidenceHash!==a[5] ||
        address(state.genome.creator)!==address(tx.from)) throw Error('Mint readback mismatch.');
    if ((await c.read('eth_getBlockByNumber',[receipt.blockNumber,false]))?.hash!==receipt.blockHash) throw Error('Mint block reorganized.');
    return state;
  }
  async verifyRoute(record, pkg, seedId) {
    if (!['finalized','effect-unverified'].includes(record.status) || !record.finalized || record.action !== 'route')
      throw Error('Routing has not finalized.');
    const state=await this.seed(seedId,pkg);
    const index = Number(record.args[1]);
    let job;
    if (pkg) { verifyPlan(pkg.plan); job=pkg.plan.jobs[index]; }
    else {
      // A preserved historical intent can be reconciled without its capsule.
      // Recover its exact indexed proof from calldata, never from a new form.
      const parsed=INTERFACES.Mark.parseTransaction({data:record.transaction.data});
      if (parsed?.name!=='route' || String(parsed.args[0])!==seedId || Number(parsed.args[1])!==index)
        throw Error('Historical route intent differs from the selected receipt.');
      const value=parsed.args[2], spec={goal:value[0],successMetric:value[1],bounty:String(value[2]),
        duration:Number(value[3]),priceWeight:Number(value[4])};
      const proof=Array.from(parsed.args[3]);
      if (!Number.isSafeInteger(index) || index<0 || index>=state.genome.jobs || proof.length>7)
        throw Error('Historical route index or proof exceeds the committed plan.');
      job={index,spec,leaf:leaf(index,spec),proof};
      if (proof.reduce((root,sibling)=>pair(root,sibling),job.leaf)!==state.genome.planRoot)
        throw Error('Historical route proof differs from the immutable plan root.');
    }
    if (!job || String(record.args[0])!==seedId) throw Error('Route belongs to another seed or plan index.');
    const intent=INTERFACES.Mark.encodeFunctionData('route',[seedId,index,job.spec,job.proof,record.args[4],record.args[5]]);
    if (intent.toLowerCase()!==record.transaction.data.toLowerCase()) throw Error('Route calldata differs from the exact committed job.');
    const matches = this.events(record.receipt,'Mark','MissionRouted').filter(e => String(e.id) === seedId && Number(e.index) === index && e.leaf === job?.leaf);
    if (matches.length !== 1) throw Error('Receipt must contain exactly one matching routed job.');
    const jobId = String(matches[0].jobId), block = record.receipt.blockNumber;
    const values = await this.client.call('Jobs','job',[jobId],block);
    if (address(values[0]) !== address(this.client.contracts.Mark) || address(values[1]) !== address(record.transaction.from) ||
        values[3] !== BigInt(job.spec.bounty) || values[15] !== leaf(0,job.spec) || values[14] !== 1n ||
        String((await this.call('Mark','jobSeed',[jobId],block))[0]) !== seedId)
      throw Error('Routed job escrow, specification or contract relationship differs.');
    for (let i=0;i<3;i++) if (address((await this.call('Jobs','committees',[jobId,i],block))[0]) !== address(record.args[5][i]))
      throw Error('Routed review committee differs.');
    if ((await this.client.read('eth_getBlockByNumber',[block,false]))?.hash !== record.receipt.blockHash) throw Error('Route receipt reorganized.');
    return jobId;
  }
  async openRouteReceipt(hash, pkg, seedId) {
    const c=this.client; await c.verify();
    if (!/^0x[0-9a-fA-F]{64}$/.test(hash)) throw Error('A route transaction hash is required.');
    const receipt=await c.read('eth_getTransactionReceipt',[hash]), tx=await c.read('eth_getTransactionByHash',[hash]);
    assertSupportedEnvelope(tx);
    if (!receipt || receipt.status!=='0x1' || receipt.transactionHash?.toLowerCase()!==hash.toLowerCase() ||
        !tx || tx.hash?.toLowerCase()!==hash.toLowerCase() || BigInt(tx.chainId)!==BigInt(c.profile.chainId) ||
        address(tx.to)!==address(c.contracts.Mark) || BigInt(tx.value)!==0n || tx.blockHash!==receipt.blockHash ||
        tx.blockNumber!==receipt.blockNumber || address(tx.from)!==address(receipt.from) || address(tx.to)!==address(receipt.to))
      throw Error('Not a successful direct route transaction for this deployment.');
    const parsed=INTERFACES.Mark.parseTransaction({data:tx.input,value:tx.value});
    if (parsed?.name!=='route' || String(parsed.args[0])!==seedId) throw Error('Route belongs to another seed.');
    const finalized=await c.read('eth_getBlockByNumber',['finalized',false]);
    if (!finalized || BigInt(finalized.number)<BigInt(receipt.blockNumber)) throw Error('Route is not finalized.');
    const record={action:'route',status:'effect-unverified',finalized:true,receipt,args:parsed.args,
      transaction:{from:tx.from,to:tx.to,data:tx.input}};
    const jobId=await this.verifyRoute(record,pkg,seedId);
    return {jobId,index:Number(parsed.args[1]),seedId,hash,receipt};
  }
  async reviewer(who, business, horizon, block) {
    const c=this.client;
    const [valid, availability, capacity, active, stake] = await Promise.all([
      c.call('Oracle','isValidator',[who],block),c.call('Oracle','jobAvailability',[who,business],block),
      c.call('Oracle','jobCapacity',[who],block),c.call('Oracle','activeJobs',[who],block),c.call('Oracle','stake',[who],block)
    ]);
    return {address:address(who),eligible:valid[0],until:String(availability[0]),capacity:Number(capacity[0]),active:Number(active[0]),stake:String(stake[0]),
      available:valid[0] && availability[0] >= BigInt(horizon) && active[0] < capacity[0]};
  }
  async ownedSeeds(who, fromBlock, span = 2000) {
    address(who); uint(String(fromBlock));
    if (!Number.isSafeInteger(span) || span < 1 || span > 2000) throw Error('Scan at most 2,000 blocks at a time.');
    const report = await this.client.verify(), last = BigInt(report.blockNumber), from = BigInt(fromBlock);
    const end = from + BigInt(span) - 1n < last ? from + BigInt(span) - 1n : last;
    if (from > last) return {seeds:[],nextBlock:String(from),done:true};
    const ownerTopic = zeroPadValue(who,32), transferTopic = id('Transfer(address,address,uint256)');
    const common = {address:this.client.contracts.Seed,fromBlock:toQuantity(from),toBlock:toQuantity(end)};
    const incoming = await this.client.read('eth_getLogs',[{...common,topics:[transferTopic,null,ownerTopic]}]);
    const outgoing = await this.client.read('eth_getLogs',[{...common,topics:[transferTopic,ownerTopic]}]);
    if (!Array.isArray(incoming) || !Array.isArray(outgoing) || incoming.length+outgoing.length > 4000) throw Error('Log range too large. Use a smaller range.');
    const candidates = new Set();
    for (const log of [...incoming,...outgoing]) {
      if (log.removed || address(log.address) !== address(common.address)) throw Error('Unstable ownership logs.');
      candidates.add(String(INTERFACES.Seed.parseLog(log).args.tokenId));
    }
    if (candidates.size>128) throw Error('Too many seeds in this range; reduce its size.');
    const seeds=[];
    for (const seedId of candidates) if ((await this.client.call('Seed','ownerOf',[seedId],report.blockNumber))[0] === address(who)) seeds.push(seedId);
    await this.canonical(report);
    return {seeds,nextBlock:String(end+1n),done:end===last,observedBlock:report.blockNumber};
  }
}
