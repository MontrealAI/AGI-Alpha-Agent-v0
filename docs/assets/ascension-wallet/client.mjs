// SPDX-License-Identifier: Apache-2.0
import {CONTRACTS, METHODS, ACTIONS, callData, decode, address, bytes32, parseFields, isRecovery} from './protocol.mjs';
import {QUALIFIED_PROFILES} from './qualified-profiles.mjs';
import {canonicalJSON} from '../ascension/crypto.mjs';
const READ_METHODS = new Set(['eth_chainId','eth_accounts','eth_getBlockByNumber','eth_getCode','eth_call','eth_estimateGas','eth_getBalance','eth_getTransactionCount','eth_getTransactionReceipt','eth_getTransactionByHash','eth_getLogs','eth_getStorageAt']);
const TERMINAL = ['not-submitted','rejected-by-wallet','finalized','reverted','cancelled','replaced'];
export const unresolved = record => !!record && !TERMINAL.includes(record.status);
const quantity = value => { if (typeof value !== 'string' || !/^0x(0|[1-9a-f][0-9a-f]*)$/i.test(value)) throw Error('Malformed RPC quantity.'); return BigInt(value); };
function frozen(value) { if (value && typeof value==='object') { for (const part of Object.values(value)) frozen(part); Object.freeze(value); } return value; }
export const json = value => JSON.stringify(value, (_, v) => typeof v === 'bigint' ? v.toString() : v, 2);
export async function sha256Hex(hex) {
  if (typeof hex !== 'string' || !/^0x([0-9a-fA-F]{2})+$/.test(hex) || hex.length > 200002) throw Error('Missing or malformed contract bytecode.');
  const bytes = Uint8Array.from(hex.slice(2).match(/../g), h => parseInt(h, 16));
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
}
export function validateProfile(p) {
  const registered = QUALIFIED_PROFILES.find(x => x.profile === p?.profile);
  if (registered) {
    if (canonicalJSON(p) !== canonicalJSON(registered) || p.schema !== 'agialpha.qualified-wallet-profile.v1' ||
        !Number.isSafeInteger(p.chainId) || p.chainId < 1 || !['canary','public'].includes(p.stage) ||
        typeof p.newExposureEnabled !== 'boolean' || !p.evidence || !Array.isArray(p.dependencies) || !p.dependencies.length ||
        !Array.isArray(p.authorities) || !p.authorities.length || !Array.isArray(p.actions) ||
        (p.stage === 'canary' && (!p.scope?.actors?.length || !p.scope?.actions)))
      throw Error('Profile differs from the reviewed, build-time qualification registry.');
    for (const key of ['Access','Seed','Oracle','Jobs','Mark','Token']) {
      address(p.contracts?.[key]?.address);
      if (!/^[0-9a-f]{64}$/.test(p.contracts[key].sha256)) throw Error('Missing exact runtime identity.');
    }
    return JSON.parse(JSON.stringify(registered));
  }
  if (!p || p.schema !== 'agialpha.mark-wallet-profile.v1' || p.chainId !== 1 || p.profile !== 'ascension-2026-10-11-solc-0.8.24' || p.newExposureEnabled !== false)
    throw Error('Unsupported or unreviewed deployment profile. This build supports the recorded suite with new funding disabled.');
  for (const key of ['Access','Seed','Oracle','Jobs','Mark']) {
    if (address(p.contracts?.[key]?.address) !== address(CONTRACTS[key]) || !/^[0-9a-f]{64}$/.test(p.contracts[key].sha256))
      throw Error('Deployment profile address or bytecode digest mismatch.');
  }
  return p;
}
export class MarkClient {
  constructor(profile, notify = () => {}, persist = () => {}) {
    Object.defineProperty(this,'profile',{value:frozen(JSON.parse(JSON.stringify(validateProfile(profile)))),writable:false}); this.notify = notify;
    this.chainId = '0x' + this.profile.chainId.toString(16);
    this.contracts = Object.freeze({...CONTRACTS, ...Object.fromEntries(Object.entries(this.profile.contracts).map(([k,v]) => [k,v.address]))});
    this.provider = null; this.account = null; this.epoch = 0;
    this.prepared = null; this.pending = null; this.history = []; this.report = null;
    this.listeners = []; this.previewRevision = 0;
    this.persist = persist;
  }
  emit() { this.notify(this); }
  journal() { return {schema:'agialpha.mark-wallet-journal.v2',chainId:this.profile.chainId,profile:this.profile.profile,transactions:this.history}; }
  checkpoint() { this.persist(this.journal()); this.emit(); }
  restore(value) {
    if (json(value).length > 1000000 || value?.schema !== 'agialpha.mark-wallet-journal.v2' || value.chainId !== this.profile.chainId || (value.profile && value.profile !== this.profile.profile) ||
        (this.profile.schema==='agialpha.qualified-wallet-profile.v1' && value.profile !== this.profile.profile) ||
        !Array.isArray(value.transactions) || value.transactions.length > 100) throw Error('Invalid or oversized recovery journal.');
    const records = value.transactions.map(r => {
      const action = ACTIONS[r.action], tx = r.transaction;
      if (!Object.hasOwn(ACTIONS,r.action) || !action || !tx || !Array.isArray(r.args) ||
          r.schema !== 'agialpha.mark-wallet-transaction.v2' || r.chainId !== this.profile.chainId || tx.chainId !== this.chainId ||
          address(tx.to) !== address(this.contracts[action.contract]) || tx.data !== callData(action.method,r.args) ||
          tx.value !== '0x0' || !Number.isFinite(Date.parse(r.createdAt)) ||
          ![...TERMINAL,'awaiting-wallet','submission-unknown','submitted','reorged','mined-not-finalized'].includes(r.status))
        throw Error('Journal transaction does not match an allowed action.');
      // Historical intent stays readable after an exposure policy is suspended.
      // Import grants no signing authority; prepare/confirm enforce current policy.
      address(tx.from); quantity(tx.nonce); quantity(tx.gas);
      if (r.hash !== null) bytes32(r.hash);
      if (r.candidateHash) bytes32(r.candidateHash);
      return {...r, transaction:{...tx}, status:r.status === 'awaiting-wallet' ? 'submission-unknown' : r.status};
    });
    if (records.slice(0,-1).some(unresolved)) throw Error('Only the latest journal entry may be unresolved.');
    this.history = records; this.pending = records.at(-1) || null;
  }
  invalidate() { this.epoch++; this.previewRevision++; this.prepared = null; this.report = null; this.account = null; this.emit(); }
  detach() {
    for (const [event, fn] of this.listeners) this.provider?.removeListener?.(event, fn);
    this.listeners = [];
  }
  select(provider) {
    if (this.pending?.status === 'awaiting-wallet') throw Error('Resolve the existing wallet request before changing provider.');
    if (!provider || typeof provider.request !== 'function') throw Error('No compatible wallet provider.');
    this.detach(); this.provider = provider; this.invalidate();
    for (const event of ['chainChanged','accountsChanged','disconnect']) {
      const fn = () => this.invalidate();
      provider.on?.(event, fn); this.listeners.push([event, fn]);
    }
  }
  disconnect() {
    if (this.pending?.status === 'awaiting-wallet') throw Error('Resolve the pending wallet request first.');
    this.detach(); this.provider = null; this.invalidate();
  }
  guard(epoch) { if (epoch !== this.epoch || !this.provider) throw Error('Wallet or network changed. Reconnect and prepare again.'); }
  async read(method, params = [], epoch = this.epoch) {
    if (!READ_METHODS.has(method) || !this.provider) throw Error('Read method/provider not allowed.');
    const provider = this.provider;
    let timer;
    try {
      const result = await Promise.race([provider.request({method, params}), new Promise((_, reject) => { timer = setTimeout(() => reject(Error('RPC read timed out; no pass was recorded.')), 15000); })]);
      this.guard(epoch); return result;
    } finally { clearTimeout(timer); }
  }
  async chain(epoch = this.epoch) {
    if (await this.read('eth_chainId', [], epoch) !== this.chainId) throw Error('Wrong network. Select the deployment network explicitly in your wallet.');
  }
  async identity(epoch = this.epoch) {
    await this.chain(epoch);
    const accounts = await this.read('eth_accounts', [], epoch);
    if (!Array.isArray(accounts) || !accounts.length) throw Error('Connect your wallet before preparing a transaction.');
    const a = address(accounts[0]);
    if (this.account && a !== this.account) { this.invalidate(); throw Error('Account changed. Reconnect.'); }
    return a;
  }
  async connect() {
    if (!this.provider) throw Error('Choose a wallet first.');
    const selected = this.provider;
    await this.chain();
    await selected.request({method:'eth_requestAccounts'});
    if (selected !== this.provider) throw Error('Selected wallet changed during connection.');
    // The permission request can legitimately emit accountsChanged. Read the fresh identity.
    const epoch = this.epoch; this.account = await this.identity(epoch); this.emit(); return this.account;
  }
  async switchMainnet() {
    if (!this.provider || this.pending?.status === 'awaiting-wallet') throw Error('Choose a wallet and finish any pending request.');
    this.prepared = null;
    await this.provider.request({method:'wallet_switchEthereumChain',params:[{chainId:this.chainId}]});
    this.invalidate();
  }
  async call(contract, method, args = [], block = 'latest', epoch = this.epoch, from = null) {
    if (!Object.hasOwn(this.contracts, contract)) throw Error('Unknown contract.');
    const tx = {to: this.contracts[contract], data: callData(method, args)};
    if (from) tx.from = address(from);
    return decode(METHODS[method].outputs, await this.read('eth_call', [tx, block], epoch));
  }
  async verify(epoch = this.epoch) {
    await this.chain(epoch);
    const block = await this.read('eth_getBlockByNumber', ['latest',false], epoch);
    if (!block || !/^0x[0-9a-f]+$/i.test(block.number) || !/^0x[0-9a-f]+$/i.test(block.timestamp)) throw Error('Missing observed block.');
    bytes32(block.hash);
    for (const key of Object.keys(this.profile.contracts)) {
      const code = await this.read('eth_getCode', [this.contracts[key], block.number], epoch);
      if (await sha256Hex(code) !== this.profile.contracts[key].sha256) throw Error(`${key}: bytecode does not match the selected deployment. All wallet writes are blocked.`);
      this.guard(epoch);
    }
    for (const dependency of this.profile.dependencies || []) {
      if (await sha256Hex(await this.read('eth_getCode',[address(dependency.address),block.number],epoch)) !== dependency.sha256)
        throw Error('External dependency code changed.');
      for (const slot of dependency.slots || []) {
        if ((await this.read('eth_getStorageAt',[address(dependency.address),slot.key,block.number],epoch)).toLowerCase() !== slot.value.toLowerCase())
          throw Error('External proxy implementation or authority changed.');
      }
    }
    for (const authority of this.profile.authorities || []) {
      if ((await this.call(authority.contract,'owner',[],block.number,epoch))[0] !== address(authority.owner))
        throw Error('Deployment governance changed; qualification must be reviewed.');
    }
    const bindings = [['Seed','access','Access'],['Oracle','access','Access'],['Oracle','seed','Seed'],['Oracle','marketplace','Jobs'],['Jobs','access','Access'],['Jobs','oracle','Oracle'],['Jobs','mark','Mark'],['Mark','seed','Seed'],['Mark','access','Access'],['Mark','oracle','Oracle'],['Mark','jobsBinding','Jobs'],['Mark','token','Token'],['Jobs','token','Token'],['Oracle','token','Token']];
    for (const [contract, getter, expected] of bindings) {
      const [actual] = await this.call(contract, getter, [], block.number, epoch);
      if (actual !== address(this.contracts[expected])) throw Error(`${contract}.${getter}: wrong protocol binding.`);
    }
    if ((await this.call('Token','decimals',[],block.number,epoch))[0] !== 18n) throw Error('Token decimals mismatch.');
    const canonical = await this.read('eth_getBlockByNumber',[block.number,false],epoch);
    if (canonical?.hash !== block.hash) throw Error('Observed block reorganized. Refresh before continuing.');
    await this.chain(epoch);
    this.report = {schema:'agialpha.mark-wallet-observation.v1', chainId:this.profile.chainId, blockNumber:block.number, blockHash:block.hash, blockTime:block.timestamp,
      observedAt:new Date().toISOString(), suiteBytecodeMatches:true, bindingsMatch:true, externalDependenciesIndependentlyReviewed:false,
      newExposureEnabled:this.profile.newExposureEnabled, finality:'observed-not-finalized', profile:this.profile.profile};
    this.emit(); return this.report;
  }
  async inspect(seedId = null, jobId = null) {
    const epoch = this.epoch, report = await this.verify(epoch), block = report.blockNumber;
    const result = {verification:report, contracts:this.contracts, nextSeedId:(await this.call('Seed','nextId',[],block,epoch))[0]};
    // Wallet permissions are never requested by inspection.
    const accounts = await this.read('eth_accounts',[],epoch);
    const who = Array.isArray(accounts) && accounts.length ? address(accounts[0]) : null;
    if (who) {
      result.wallet = {account:who, balance:(await this.call('Token','balanceOf',[who],block,epoch))[0],
        admitted:(await this.call('Access','admitted',[who],block,epoch))[0], roles:[], allowances:{}, stake:{}};
      for (const role of ['0','1','2']) result.wallet.roles.push((await this.call('Access','eligible',[who,role],block,epoch))[0]);
      for (const key of ['Mark','Oracle','Jobs']) result.wallet.allowances[key] = (await this.call('Token','allowance',[who,this.contracts[key]],block,epoch))[0];
      for (const key of ['Oracle','Jobs']) result.wallet.stake[key] = (await this.call(key,'stake',[who],block,epoch))[0];
      result.wallet.stake.agentLocked = (await this.call('Jobs','locked',[who],block,epoch))[0];
      result.wallet.stake.validatorLockedUntil = (await this.call('Oracle','lockedUntil',[who],block,epoch))[0];
    }
    if (seedId) {
      const values = await this.call('Mark','campaigns',[seedId],block,epoch);
      const keys = ['business','base','slope','target','maxLots','supply','posted','active','duration','fundingEnd','executionEnd','reserve','phase','businessNode'];
      result.campaign = Object.fromEntries(keys.map((key,i) => [key,values[i]]));
      result.seedOwner = (await this.call('Seed','ownerOf',[seedId],block,epoch))[0];
      result.green = (await this.call('Oracle','green',[seedId],block,epoch))[0];
      result.plan = await this.call('Seed','plan',[seedId],block,epoch);
      result.yourLots = who ? (await this.call('Mark','lots',[seedId,who],block,epoch))[0] : null;
    }
    if (jobId) {
      const v = await this.call('Jobs','job',[jobId],block,epoch);
      const keys = ['client','business','worker','bounty','price','bond','auctionEnd','executionEnd','reviewEnd','due','duration','priceWeight','yes','no','state','specHash','resultHash','refund','claimed'];
      result.job = Object.fromEntries(keys.map((key,i) => [key,v[i]]));
    }
    const canonical = await this.read('eth_getBlockByNumber',[block,false],epoch);
    if(canonical?.hash !== report.blockHash) throw Error('Observation reorganized during inspection. Refresh.');
    this.guard(epoch); return result;
  }
  allowed(actionId, args) {
    const action = ACTIONS[actionId];
    if (!action || !Object.hasOwn(ACTIONS,actionId)) throw Error('Action is not allowlisted.');
    if (this.profile.schema==='agialpha.qualified-wallet-profile.v1') {
      if (!this.profile.newExposureEnabled && action.risk==='new' && !isRecovery(actionId,args))
        throw Error('New exposure is suspended for this qualified deployment. Permitted recovery remains available.');
      if (!this.profile.actions.includes(actionId)) throw Error('Action is outside this profile commissioning scope.');
      const scope = this.profile.scope;
      if (this.profile.stage === 'canary') {
        const rule = scope.actions[actionId];
        if (!rule) throw Error('Action is outside the authorized canary.');
        for (const [index, maximum] of Object.entries(rule.maxArgs || {}))
          if (BigInt(args[Number(index)]) > BigInt(maximum)) throw Error('Action exceeds the authorized canary amount.');
        if (rule.seedIds && !rule.seedIds.includes(String(args[0]))) throw Error('Seed is outside the authorized canary.');
      }
      return;
    }
    if (action.risk === 'new' && !isRecovery(actionId,args))
      throw Error('New exposure is not commissioned for this archived deployment. This is not bypassed by wallet connection or an acknowledgement. Recovery and existing obligations remain available.');
    // Revoking existing future availability is a recovery action; new approvals never get a blanket bypass.
  }
  checkScopeTime(actionId,args) {
    if (this.profile.stage==='canary' && this.profile.scope.until && ACTIONS[actionId].risk==='new' && !isRecovery(actionId,args) &&
        BigInt(this.report.blockTime)>=BigInt(this.profile.scope.until)) throw Error('Canary authorization expired. Existing recovery actions remain available.');
  }
  checkActor(from) {
    if (this.profile.stage === 'canary' && !this.profile.scope.actors.map(address).includes(address(from)))
      throw Error('Wallet is outside the authorized canary participants.');
  }
  async prepare(actionId, rawValues) {
    if (unresolved(this.pending)) throw Error('Reconcile the outstanding transaction before starting another.');
    this.prepared = null; const revision = ++this.previewRevision;
    const epoch = this.epoch, args = parseFields(actionId, rawValues, this.contracts), action = ACTIONS[actionId];
    // Encoding validates widths, arrays and text even for policy-blocked actions.
    const data = callData(action.method,args);
    this.allowed(actionId,args);
    const from = await this.identity(epoch), report = await this.verify(epoch);
    this.checkActor(from); this.checkScopeTime(actionId,args);
    const nonce = await this.read('eth_getTransactionCount',[from,'pending'],epoch); quantity(nonce);
    const tx = {from, to:this.contracts[action.contract], data, value:'0x0', chainId:this.chainId, nonce};
    const result = await this.read('eth_call',[tx,'latest'],epoch);
    decode(METHODS[action.method].outputs,result);
    if (actionId === 'approve' && decode(['bool'],result)[0] !== true) throw Error('Token approval simulation returned false.');
    const gas = BigInt(await this.read('eth_estimateGas',[tx],epoch));
    if (gas <= 0n || gas > 30000000n) throw Error('Unreasonable gas estimate.');
    const balance = BigInt(await this.read('eth_getBalance',[from,'latest'],epoch));
    if (balance === 0n) throw Error('This wallet needs ETH for network fees.');
    if (await this.identity(epoch) !== from) throw Error('Account changed.');
    if (revision !== this.previewRevision) throw Error('Inputs changed during preparation. Prepare again.');
    tx.gas = `0x${(gas * 120n / 100n).toString(16)}`;
    this.prepared = Object.freeze({actionId, args:Object.freeze(args), transaction:Object.freeze(tx), simulatedResult:result, gas:gas.toString(),
      report, preparedAt:Date.now(), epoch, note:action.note});
    this.emit(); return this.prepared;
  }
  cancelPreview() { this.previewRevision++; this.prepared = null; this.emit(); }
  async confirm(acknowledged = false) {
    const p = this.prepared;
    if (!acknowledged || !p) throw Error('Prepare and explicitly acknowledge this exact transaction first.');
    if (unresolved(this.pending)) throw Error('An outstanding transaction already exists.');
    this.prepared = null; this.guard(p.epoch);
    if (Date.now() - p.preparedAt > 60000) throw Error('Preview expired. Prepare again.');
    this.allowed(p.actionId,p.args); this.checkActor(p.transaction.from);
    if (await this.identity(p.epoch) !== p.transaction.from) throw Error('Account changed.');
    await this.verify(p.epoch); this.checkScopeTime(p.actionId,p.args);
    if (await this.read('eth_call',[p.transaction,'latest'],p.epoch) !== p.simulatedResult) throw Error('Simulation result changed. Prepare a new preview.');
    const gas = BigInt(await this.read('eth_estimateGas',[p.transaction],p.epoch));
    if (gas <= 0n || gas > BigInt(p.transaction.gas)) throw Error('Gas estimate changed materially. Prepare again.');
    if (quantity(await this.read('eth_getTransactionCount',[p.transaction.from,'pending'],p.epoch)) !== quantity(p.transaction.nonce))
      throw Error('Wallet nonce changed. Prepare again; another transaction may be pending.');
    if (await this.identity(p.epoch) !== p.transaction.from) throw Error('Account changed.');
    this.guard(p.epoch);
    if (Date.now() - p.preparedAt > 60000) throw Error('Preview expired during final checks. Prepare again.');
    const provider = this.provider;
    this.pending = {schema:'agialpha.mark-wallet-transaction.v2', action:p.actionId, args:p.args, chainId:this.profile.chainId, transaction:p.transaction,
      createdAt:new Date().toISOString(), status:'awaiting-wallet', hash:null};
    this.history.push(this.pending); this.history = this.history.slice(-100);
    // Persist the exact intent BEFORE the wallet is opened. Storage failure sends nothing.
    try { this.checkpoint(); } catch (error) { this.pending.status='not-submitted'; this.emit(); throw error; }
    try {
      // No timeout/retry around signing: a delayed wallet response must never cause a second send.
      const hash = await provider.request({method:'eth_sendTransaction',params:[p.transaction]});
      bytes32(hash); this.pending.hash = hash; this.pending.status = 'submitted'; this.checkpoint(); return hash;
    } catch (error) {
      this.pending.status = error?.code === 4001 ? 'rejected-by-wallet' : 'submission-unknown';
      this.checkpoint(); throw Error(this.pending.status === 'submission-unknown' ? 'Submission outcome is unknown. Check wallet activity and reconcile its transaction hash below; do not blindly retry.' : 'You rejected the wallet request. No automatic retry.');
    }
  }
  async receipt(hash, reconcile = false) {
    bytes32(hash); const epoch = this.epoch; await this.chain(epoch);
    const record = reconcile ? this.pending : this.history.find(x => x.hash?.toLowerCase() === hash.toLowerCase());
    if (!record || record.status === 'awaiting-wallet') throw Error('Load a recovery journal and finish any open wallet prompt first.');
    const receipt = await this.read('eth_getTransactionReceipt',[hash],epoch);
    if (!receipt) { record.status='submitted'; this.checkpoint(); return {status:'pending-or-replaced',hash}; }
    if (!['0x0','0x1'].includes(receipt.status) || receipt.transactionHash?.toLowerCase() !== hash.toLowerCase()) throw Error('Malformed transaction receipt.');
    const tx = await this.read('eth_getTransactionByHash',[hash],epoch);
    if (!tx || tx.hash?.toLowerCase() !== hash.toLowerCase() || address(tx.from) !== address(record.transaction.from) ||
        quantity(tx.nonce) !== quantity(record.transaction.nonce) || quantity(tx.chainId) !== BigInt(this.profile.chainId) ||
        tx.blockHash !== receipt.blockHash || tx.blockNumber !== receipt.blockNumber)
      throw Error('Receipt transaction does not match the recorded sender, nonce, chain and block.');
    const matches = tx.to && address(tx.to) === address(record.transaction.to) &&
      tx.input?.toLowerCase() === record.transaction.data.toLowerCase() && quantity(tx.value) === 0n;
    if (!matches && !reconcile) throw Error('Receipt transaction does not match the prepared action.');
    const block = await this.read('eth_getBlockByNumber',[receipt.blockNumber,false],epoch);
    if (block?.hash !== receipt.blockHash) { record.status = 'reorged'; this.checkpoint(); throw Error('Receipt block is no longer canonical. Reconcile before continuing.'); }
    let finalized = false;
    try { const b = await this.read('eth_getBlockByNumber',['finalized',false],epoch); finalized = !!b && BigInt(b.number) >= BigInt(receipt.blockNumber); }
    catch { this.guard(epoch); }
    const canonical = await this.read('eth_getBlockByNumber',[receipt.blockNumber,false],epoch);
    if (canonical?.hash !== receipt.blockHash) { record.status='reorged'; this.checkpoint(); throw Error('Receipt reorganized during finality checks.'); }
    const cancelled = tx.to && address(tx.to) === address(tx.from) && quantity(tx.value) === 0n && tx.input === '0x';
    record.candidateHash = hash;
    record.status = !finalized ? 'mined-not-finalized' : !matches ? (cancelled ? 'cancelled' : 'replaced') : receipt.status === '0x0' ? 'reverted' : 'finalized';
    record.receipt = receipt; record.finalized = finalized; this.checkpoint(); return record;
  }
}
