// SPDX-License-Identifier: Apache-2.0
import {CONTRACTS, METHODS, ACTIONS, callData, decode, address, bytes32, parseFields, isRecovery} from './protocol.mjs';
import {QUALIFIED_PROFILES} from './qualified-profiles.mjs';
import {validateQualification, authorizeQualifiedIntent, verifyQualification, qualificationIdentity} from './qualification.mjs';
const PINNED_PROFILES = Object.freeze(QUALIFIED_PROFILES.map(entry => Object.freeze({...entry})));
const READ_METHODS = new Set(['eth_chainId','eth_accounts','eth_getBlockByNumber','eth_getCode','eth_call','eth_estimateGas','eth_getBalance','eth_getTransactionCount','eth_getTransactionReceipt','eth_getTransactionByHash','eth_getLogs','eth_getStorageAt']);
const TERMINAL = ['not-submitted','rejected-by-wallet','finalized','reverted','cancelled','replaced'];
export const unresolved = record => !!record && !TERMINAL.includes(record.status);
const quantity = value => { if (typeof value !== 'string' || !/^0x(0|[1-9a-f][0-9a-f]*)$/i.test(value)) throw Error('Malformed RPC quantity.'); return BigInt(value); };
function frozen(value) { if (value && typeof value==='object') { for (const part of Object.values(value)) frozen(part); Object.freeze(value); } return value; }
export const json = value => JSON.stringify(value, (_, v) => typeof v === 'bigint' ? v.toString() : v, 2);
export function canonicalProfile(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalProfile).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonicalProfile(value[k])).join(',') + '}';
  if (value === undefined || (typeof value === 'number' && !Number.isSafeInteger(value))) throw Error('Invalid profile value.');
  return JSON.stringify(value);
}
export async function sha256Text(value) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), b => b.toString(16).padStart(2, '0')).join('');
}
const freeze = value => {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
};
function registryAuthorization(entry) {
  if (entry.stage !== 'canary') return null;
  if (typeof entry.authorizationJSON !== 'string' || entry.authorizationJSON.length > 100000 ||
      !/^[0-9a-f]{64}$/.test(entry.authorizationSHA256)) throw Error('Missing build-bound canary authorization.');
  const scope = JSON.parse(entry.authorizationJSON);
  if (canonicalProfile(scope) !== entry.authorizationJSON) throw Error('Noncanonical canary authorization.');
  return freeze(scope);
}
export function deploymentDescriptor(profile) {
  if (!profile || !Number.isSafeInteger(profile.chainId) || profile.chainId <= 0 || typeof profile.profile !== 'string' ||
      !profile.contracts || typeof profile.contracts !== 'object') throw Error('Missing immutable deployment identity.');
  const contracts = Object.fromEntries(Object.keys(profile.contracts).sort().map(key => {
    const record = profile.contracts[key];
    return [key,{address:address(record.address),sha256:record.sha256 || null,keccak256:record.archivedKeccak256 || null}];
  }));
  return freeze({schema:'agialpha.deployment-identity.v1',chainId:profile.chainId,profile:profile.profile,contracts,
    sourceSHA256:profile.sourceSHA256 || profile.sourceManifestSHA256 || null,abiSHA256:profile.abiSHA256 || null,
    genesisHash:profile.genesisHash || null,deploymentBlock:profile.deploymentBlock || null,deploymentBlockHash:profile.deploymentBlockHash || null});
}
export function availableProfiles(defaultProfile) {
  const values = [validateProfile(defaultProfile),...PINNED_PROFILES.map(entry => validateProfile(JSON.parse(entry.canonicalJSON)))];
  const seen = new Set();
  return Object.freeze(values.filter(profile => {const key=canonicalProfile(profile);if(seen.has(key))return false;seen.add(key);return true;}).map(profile => {
    const entry=PINNED_PROFILES.find(item => item.canonicalJSON===canonicalProfile(profile));
    return freeze({id:entry?.sha256 || profile.profile,stage:entry?.stage || 'archive',label:profile.profile,profile});
  }));
}
export function selectBuildProfile(id, defaultProfile) {
  const choice=availableProfiles(defaultProfile).find(item => item.id===id);
  if (!choice) throw Error('Deployment is not registered in this build.');
  return choice.profile;
}
export async function sha256Hex(hex) {
  if (typeof hex !== 'string' || !/^0x([0-9a-fA-F]{2})+$/.test(hex) || hex.length > 200002) throw Error('Missing or malformed contract bytecode.');
  const bytes = Uint8Array.from(hex.slice(2).match(/../g), h => parseInt(h, 16));
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
}
export function validateProfile(p) {
  if (p && PINNED_PROFILES.filter(entry => entry.canonicalJSON === canonicalProfile(p)).length > 1)
    throw Error('Ambiguous deployment authorization registry.');
  const pinned = p && PINNED_PROFILES.find(entry => entry.canonicalJSON === canonicalProfile(p));
  if (pinned) {
    const local = pinned.stage === 'local' && p.schema === 'agialpha.nova-local-profile.v1' &&
      p.environment === 'local-exact-source' && [1337,31337].includes(p.chainId) && p.mainnetQualification === false;
    const qualified = ['canary','public'].includes(pinned.stage);
    if ((!local && !qualified) || typeof p.newExposureEnabled !== 'boolean' || !/^[0-9a-f]{64}$/.test(p.sourceSHA256) ||
        !/^[0-9a-f]{64}$/.test(p.abiSHA256) || !/^[0-9a-f]{64}$/.test(pinned.sha256) ||
        !Array.isArray(p.actions) || new Set(p.actions).size !== p.actions.length ||
        p.actions.some(key => !Object.hasOwn(ACTIONS,key))) throw Error('Invalid build-bound deployment qualification.');
    bytes32(p.genesisHash); bytes32(p.deploymentBlockHash); quantity(p.deploymentBlock);
    for (const key of Object.keys(CONTRACTS)) {
      address(p.contracts?.[key]?.address);
      if (!/^[0-9a-f]{64}$/.test(p.contracts[key].sha256)) throw Error('Missing build-bound runtime digest.');
      if (local && key !== 'Token' && Object.entries(CONTRACTS).some(([name,value]) => name !== 'Token' && address(p.contracts[key].address) === address(value)))
        throw Error('Local profile cannot impersonate the archived Mainnet suite.');
    }
    if (qualified) validateQualification(p,pinned.stage,registryAuthorization(pinned),pinned.sha256);
    return freeze(JSON.parse(JSON.stringify(p)));
  }
  if (!p || p.schema !== 'agialpha.mark-wallet-profile.v1' || p.chainId !== 1 || p.profile !== 'ascension-2026-10-11-solc-0.8.24' || p.newExposureEnabled !== false)
    throw Error('Unsupported or unreviewed deployment profile. New exposure requires an exact profile pinned in this build.');
  for (const key of ['Access','Seed','Oracle','Jobs','Mark']) {
    if (address(p.contracts?.[key]?.address) !== address(CONTRACTS[key]) || !/^[0-9a-f]{64}$/.test(p.contracts[key].sha256))
      throw Error('Deployment profile address or bytecode digest mismatch.');
  }
  return freeze(JSON.parse(JSON.stringify(p)));
}
export function assertSupportedEnvelope(tx) {
  if (!tx || !['0x0','0x1','0x2'].includes(tx.type) ||
      (tx.authorizationList != null && (!Array.isArray(tx.authorizationList) || tx.authorizationList.length)))
    throw Error('Unsupported transaction envelope or additional authorization list. Export and review the transaction; do not resend.');
  return tx;
}
export class MarkClient {
  constructor(profile, notify = () => {}, persist = () => {}) {
    Object.defineProperty(this,'profile',{value:frozen(JSON.parse(JSON.stringify(validateProfile(profile)))),writable:false}); this.notify = notify;
    const entry = PINNED_PROFILES.find(item => item.canonicalJSON === canonicalProfile(this.profile));
    Object.defineProperties(this, {
      chainId:{value:'0x' + this.profile.chainId.toString(16)},
      contracts:{value:Object.freeze({...CONTRACTS,...Object.fromEntries(Object.entries(this.profile.contracts).map(([k,v]) => [k,v.address]))})},
      profileIdentity:{value:entry?.sha256 || this.profile.profile}, stage:{value:entry?.stage || 'archive'},
      authorization:{value:entry?.stage === 'canary' ? registryAuthorization(entry) : null},
      authorizationIdentity:{value:entry?.stage === 'canary' ? entry.authorizationSHA256 : null}
    });
    this.provider = null; this.account = null; this.epoch = 0;
    this.prepared = null; this.pending = null; this.history = []; this.report = null;
    this.listeners = []; this.previewRevision = 0;
    this.requireEffectVerification = false;
    this.persist = persist;
  }
  emit() { this.notify(this); }
  journal() { return {schema:'agialpha.mark-wallet-journal.v2',chainId:this.profile.chainId,profile:this.profile.profile,
    profileIdentity:this.profileIdentity,deployment:deploymentDescriptor(this.profile),transactions:this.history}; }
  checkpoint() {
    this.pending = this.history.findLast(unresolved) || this.history.at(-1) || null;
    this.persist(this.journal()); this.emit();
  }
  restore(value) {
    if (json(value).length > 1000000 || value?.schema !== 'agialpha.mark-wallet-journal.v2' || value.chainId !== this.profile.chainId || (value.profile && value.profile !== this.profile.profile) ||
        (value.deployment && canonicalProfile(value.deployment) !== canonicalProfile(deploymentDescriptor(this.profile))) ||
        (this.stage !== 'archive' && (!value.deployment || value.profile !== this.profile.profile)) ||
        !Array.isArray(value.transactions) || value.transactions.length > 100) throw Error('Invalid or oversized recovery journal.');
    const records = value.transactions.map(r => {
      const action = ACTIONS[r.action], tx = r.transaction;
      if (!Object.hasOwn(ACTIONS,r.action) || !action || !tx || !Array.isArray(r.args) ||
          r.schema !== 'agialpha.mark-wallet-transaction.v2' || r.chainId !== this.profile.chainId || tx.chainId !== this.chainId ||
          address(tx.to) !== address(this.contracts[action.contract]) || tx.data !== callData(action.method,r.args) ||
          tx.value !== '0x0' || !Number.isFinite(Date.parse(r.createdAt)) ||
          ![...TERMINAL,'awaiting-wallet','submission-unknown','submitted','reorged','mined-not-finalized','effect-unverified','authorization-mismatch','unsupported-envelope'].includes(r.status))
        throw Error('Journal transaction does not match an allowed action.');
      // Historical intent stays readable after an exposure policy is suspended.
      // Import grants no signing authority; prepare/confirm enforce current policy.
      address(tx.from); quantity(tx.nonce); quantity(tx.gas);
      if (r.hash !== null) bytes32(r.hash);
      if (r.candidateHash) bytes32(r.candidateHash);
      return {...r, transaction:{...tx}, status:r.status === 'awaiting-wallet' ? 'submission-unknown' : r.status};
    });
    this.history = records; this.pending = records.findLast(unresolved) || records.at(-1) || null;
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
    if (this.stage !== 'archive') {
      const entry = PINNED_PROFILES.find(p => p.canonicalJSON === canonicalProfile(this.profile));
      if (!entry || await sha256Text(entry.canonicalJSON) !== entry.sha256 ||
          await sha256Text(qualificationIdentity()) !== this.profile.abiSHA256)
        throw Error('Profile and ABI do not match this build. All wallet writes are blocked.');
      if (entry.stage === 'canary' && await sha256Text(entry.authorizationJSON) !== entry.authorizationSHA256)
        throw Error('Canary authorization does not match this build.');
      const genesis = await this.read('eth_getBlockByNumber',['0x0',false],epoch);
      const deployment = await this.read('eth_getBlockByNumber',[this.profile.deploymentBlock,false],epoch);
      if (genesis?.hash !== this.profile.genesisHash || deployment?.hash !== this.profile.deploymentBlockHash)
        throw Error('Chain genesis or deployment block does not match the pinned profile.');
    }

    const block = await this.read('eth_getBlockByNumber', ['latest',false], epoch);
    if (!block || !/^0x[0-9a-f]+$/i.test(block.number) || !/^0x[0-9a-f]+$/i.test(block.timestamp)) throw Error('Missing observed block.');
    bytes32(block.hash);
    for (const key of Object.keys(this.profile.contracts)) {
      const code = await this.read('eth_getCode', [this.contracts[key], block.number], epoch);
      if (await sha256Hex(code) !== this.profile.contracts[key].sha256) throw Error(`${key}: bytecode does not match the selected deployment. All wallet writes are blocked.`);
      this.guard(epoch);
    }
    for (const dependency of this.stage === 'local' ? this.profile.dependencies || [] : []) {
      if (await sha256Hex(await this.read('eth_getCode',[address(dependency.address),block.number],epoch)) !== dependency.sha256)
        throw Error('External dependency code changed.');
      for (const slot of dependency.slots || []) {
        if ((await this.read('eth_getStorageAt',[address(dependency.address),slot.key,block.number],epoch)).toLowerCase() !== slot.value.toLowerCase())
          throw Error('External proxy implementation or authority changed.');
      }
    }
    for (const authority of this.stage === 'local' ? this.profile.authorities || [] : []) {
      if ((await this.call(authority.contract,'owner',[],block.number,epoch))[0] !== address(authority.owner))
        throw Error('Deployment governance changed; qualification must be reviewed.');
    }
    const bindings = [['Seed','access','Access'],['Oracle','access','Access'],['Oracle','seed','Seed'],['Oracle','marketplace','Jobs'],['Jobs','access','Access'],['Jobs','oracle','Oracle'],['Jobs','mark','Mark'],['Mark','seed','Seed'],['Mark','access','Access'],['Mark','oracle','Oracle'],['Mark','jobsBinding','Jobs'],['Mark','token','Token'],['Jobs','token','Token'],['Oracle','token','Token']];
    for (const [contract, getter, expected] of bindings) {
      const [actual] = await this.call(contract, getter, [], block.number, epoch);
      if (actual !== address(this.contracts[expected])) throw Error(`${contract}.${getter}: wrong protocol binding.`);
    }
    if ((await this.call('Token','decimals',[],block.number,epoch))[0] !== 18n) throw Error('Token decimals mismatch.');
    const qualification = ['canary','public'].includes(this.stage) ? await verifyQualification(this,block,epoch,sha256Hex) : null;
    const canonical = await this.read('eth_getBlockByNumber',[block.number,false],epoch);
    if (canonical?.hash !== block.hash) throw Error('Observed block reorganized. Refresh before continuing.');
    await this.chain(epoch);
    this.report = {schema:'agialpha.mark-wallet-observation.v1', chainId:this.profile.chainId, blockNumber:block.number, blockHash:block.hash, blockTime:block.timestamp,
      observedAt:new Date().toISOString(), suiteBytecodeMatches:true, bindingsMatch:true, externalDependenciesIndependentlyReviewed:false,
      newExposureEnabled:this.profile.newExposureEnabled && (qualification?.authorizationCurrent ?? true),
      authorizationCurrent:qualification?.authorizationCurrent ?? false, finality:'observed-not-finalized', profile:this.profile.profile,
      profileIdentity:this.profileIdentity,environment:this.profile.environment || 'archived-mainnet',qualificationStage:this.stage,
      externalDependenciesMatchManifest:['canary','public'].includes(this.stage)};
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
    if (this.stage !== 'archive') {
      if (!this.profile.actions.includes(actionId)) throw Error('Action is outside this profile commissioning scope.');
      if (!this.profile.newExposureEnabled && action.risk === 'new' && !isRecovery(actionId,args))
        throw Error('New exposure is suspended for this qualified deployment. Permitted recovery remains available.');
      return;
    }
    if (action.risk === 'new' && !isRecovery(actionId,args))
      throw Error('New exposure is not commissioned for this archived deployment. This is not bypassed by wallet connection or an acknowledgement. Recovery and existing obligations remain available.');
    // Revoking existing future availability is a recovery action; new approvals never get a blanket bypass.
  }
  async prepare(actionId, rawValues) {
    if (unresolved(this.pending) || this.history.some(unresolved)) throw Error('Reconcile the outstanding transaction before starting another.');
    this.prepared = null; const revision = ++this.previewRevision;
    const epoch = this.epoch, args = parseFields(actionId, rawValues, this.contracts), action = ACTIONS[actionId];
    // Encoding validates widths, arrays and text even for policy-blocked actions.
    const data = callData(action.method,args);
    this.allowed(actionId,args);
    const from = await this.identity(epoch), report = await this.verify(epoch);
    const nonce = await this.read('eth_getTransactionCount',[from,'pending'],epoch); quantity(nonce);
    const tx = {from, to:this.contracts[action.contract], data, value:'0x0', chainId:this.chainId, nonce};
    authorizeQualifiedIntent(this.profile,this.stage,actionId,tx,report.blockTime,args,this.authorization);
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
    authorizeQualifiedIntent(this.profile,this.stage,actionId,tx,report.blockTime,args,this.authorization);
    this.prepared = Object.freeze({actionId, args:frozen(args), transaction:Object.freeze(tx), simulatedResult:result, gas:gas.toString(),
      report, preparedAt:Date.now(), epoch, note:action.note});
    this.emit(); return this.prepared;
  }
  cancelPreview() { this.previewRevision++; this.prepared = null; this.emit(); }
  async confirm(acknowledged = false) {
    const p = this.prepared;
    if (!acknowledged || !p) throw Error('Prepare and explicitly acknowledge this exact transaction first.');
    if (unresolved(this.pending) || this.history.some(unresolved)) throw Error('An outstanding transaction already exists.');
    this.prepared = null; this.guard(p.epoch);
    if (Date.now() - p.preparedAt > 60000) throw Error('Preview expired. Prepare again.');
    this.allowed(p.actionId,p.args);
    if (await this.identity(p.epoch) !== p.transaction.from) throw Error('Account changed.');
    const report = await this.verify(p.epoch);
    authorizeQualifiedIntent(this.profile,this.stage,p.actionId,p.transaction,report.blockTime,p.args,this.authorization);
    if (await this.read('eth_call',[p.transaction,'latest'],p.epoch) !== p.simulatedResult) throw Error('Simulation result changed. Prepare a new preview.');
    const gas = BigInt(await this.read('eth_estimateGas',[p.transaction],p.epoch));
    if (gas <= 0n || gas > BigInt(p.transaction.gas)) throw Error('Gas estimate changed materially. Prepare again.');
    if (quantity(await this.read('eth_getTransactionCount',[p.transaction.from,'pending'],p.epoch)) !== quantity(p.transaction.nonce))
      throw Error('Wallet nonce changed. Prepare again; another transaction may be pending.');
    if (await this.identity(p.epoch) !== p.transaction.from) throw Error('Account changed.');
    this.guard(p.epoch);
    if (Date.now() - p.preparedAt > 60000) throw Error('Preview expired during final checks. Prepare again.');
    const provider = this.provider;
    const intentSHA256 = await sha256Text(canonicalProfile(p.transaction));
    this.guard(p.epoch);
    authorizeQualifiedIntent(this.profile,this.stage,p.actionId,p.transaction,report.blockTime,p.args,this.authorization);
    this.pending = {schema:'agialpha.mark-wallet-transaction.v2', action:p.actionId, args:p.args, chainId:this.profile.chainId, transaction:p.transaction,
      profile:this.profileIdentity,intentSHA256,authorizationSHA256:this.authorizationIdentity,
      requiresEffectVerification:this.requireEffectVerification || ['seal','route'].includes(p.actionId),effectVerified:false,
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
  async receipt(hash, reconcile = false, {requireEffectVerification = false} = {}) {
    bytes32(hash); const epoch = this.epoch; await this.chain(epoch);
    const known = this.history.find(x => x.hash?.toLowerCase() === hash.toLowerCase() || x.candidateHash?.toLowerCase() === hash.toLowerCase());
    const record = known || (reconcile ? this.pending : null);
    if (!record || record.status === 'awaiting-wallet') throw Error('Load a recovery journal and finish any open wallet prompt first.');
    const receipt = await this.read('eth_getTransactionReceipt',[hash],epoch);
    if (!receipt) { record.status='submitted'; record.effectVerified=false; this.checkpoint(); return {status:'pending-or-replaced',hash}; }
    if (!['0x0','0x1'].includes(receipt.status) || receipt.transactionHash?.toLowerCase() !== hash.toLowerCase()) throw Error('Malformed transaction receipt.');
    const tx = await this.read('eth_getTransactionByHash',[hash],epoch);
    try { assertSupportedEnvelope(tx); } catch (error) {
      record.status='unsupported-envelope';record.effectVerified=false;record.receipt=receipt;this.checkpoint();
      throw error;
    }
    if (!tx || tx.hash?.toLowerCase() !== hash.toLowerCase() || address(tx.from) !== address(record.transaction.from) ||
        quantity(tx.nonce) !== quantity(record.transaction.nonce) || quantity(tx.chainId) !== BigInt(this.profile.chainId) ||
        tx.blockHash !== receipt.blockHash || tx.blockNumber !== receipt.blockNumber)
      throw Error('Receipt transaction does not match the recorded sender, nonce, chain and block.');
    const matches = tx.to && address(tx.to) === address(record.transaction.to) &&
      tx.input?.toLowerCase() === record.transaction.data.toLowerCase() && quantity(tx.value) === 0n;
    if (!matches && !reconcile) throw Error('Receipt transaction does not match the prepared action.');
    const block = await this.read('eth_getBlockByNumber',[receipt.blockNumber,false],epoch);
    if (block?.hash !== receipt.blockHash) { record.status = 'reorged'; record.effectVerified=false; this.checkpoint(); throw Error('Receipt block is no longer canonical. Reconcile before continuing.'); }
    let finalized = false;
    try { const b = await this.read('eth_getBlockByNumber',['finalized',false],epoch); finalized = !!b && BigInt(b.number) >= BigInt(receipt.blockNumber); }
    catch { this.guard(epoch); }
    const canonical = await this.read('eth_getBlockByNumber',[receipt.blockNumber,false],epoch);
    if (canonical?.hash !== receipt.blockHash) { record.status='reorged'; record.effectVerified=false; this.checkpoint(); throw Error('Receipt reorganized during finality checks.'); }
    if (record.authorizationSHA256 && matches) {
      let withinGasScope = false;
      try { withinGasScope = quantity(tx.gas) <= quantity(record.transaction.gas) && quantity(receipt.gasUsed) <= quantity(tx.gas); }
      catch { /* An absent or malformed gas field is not evidence of canary compliance. */ }
      if (!withinGasScope) {
        record.status='authorization-mismatch';record.effectVerified=false;record.receipt=receipt;this.checkpoint();
        throw Error('Actual wallet transaction exceeded or omitted the reviewed canary gas scope. Export and review the receipt; do not resend.');
      }
    }
    const cancelled = tx.to && address(tx.to) === address(tx.from) && quantity(tx.value) === 0n && tx.input === '0x';
    record.candidateHash = hash;
    if (requireEffectVerification || this.requireEffectVerification) {
      record.requiresEffectVerification=true; record.effectVerified=false;
    }
    if (!matches || !finalized || record.effectBlockHash !== receipt.blockHash) record.effectVerified=false;
    record.status = !finalized ? 'mined-not-finalized' : !matches ? (cancelled ? 'cancelled' : 'replaced') : receipt.status === '0x0' ? 'reverted' : 'finalized';
    if (record.status === 'finalized' && (record.requiresEffectVerification || ['seal','route'].includes(record.action)) && !record.effectVerified)
      record.status = 'effect-unverified';
    record.receipt = receipt; record.finalized = finalized;
    this.pending = this.history.findLast(unresolved) || this.history.at(-1) || null;
    this.checkpoint(); return record;
  }
  completeEffects(record) {
    if (!this.history.includes(record) || record.status !== 'effect-unverified' || !record.finalized || record.receipt?.status !== '0x1')
      throw Error('Only a recorded verified successful receipt can complete effect verification.');
    record.effectVerified=true; record.effectBlockHash=record.receipt.blockHash; record.status='finalized';
    this.pending = this.history.findLast(unresolved) || this.history.at(-1) || null; this.checkpoint();
    return record;
  }
}
