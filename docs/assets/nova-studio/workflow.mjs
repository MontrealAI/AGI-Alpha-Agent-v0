// SPDX-License-Identifier: Apache-2.0
// The Studio orchestrates the shared MARK client. It never owns a signer or retries a write.
import {ACTIONS, address, bytes32, uint, units, tokens, curve, callData, tuple} from '../ascension-wallet/protocol.mjs';
import {json, unresolved, deploymentDescriptor} from '../ascension-wallet/client.mjs';
import {hashObject} from '../ascension/crypto.mjs';
import {compilePlan, verifyPlan} from './plan.mjs';
import {verifyPackage, isRecoveryVerified, parseBoundedJSON} from './package.mjs';
import {verifyPublication} from './storage.mjs';
import {keccak256, toUtf8Bytes} from './vendor/ethers-6.17.0.min.mjs';

const ZERO = `0x${'0'.repeat(40)}`;
const ZERO_HASH = `0x${'0'.repeat(64)}`;
const DAY = 86400n;
const SITE = 'https://montrealai.github.io/AGI-Alpha-Agent-v0/';
const TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const ROLES = ['Business', 'Agent', 'Validator'];
const NAMESPACES = ['alpha.agi.eth', 'alpha.agent.agi.eth', 'alpha.club.agi.eth'];
const CAMPAIGNS = ['none', 'funding', 'activated', 'closed'];
const JOBS = ['none', 'posted', 'worker-awarded', 'result-delivered', 'paid', 'failed', 'refunded'];
const ALIASES = {identity:'register', mint:'seal', 'request-review':'openReview', 'risk-approve':'attest',
  campaign:'open', fund:'buy', activate:'bloom'};
const idString = value => {
  if (typeof value === 'number') requireThat(Number.isSafeInteger(value), 'Identifiers must be exact integer strings.');
  const number = uint(String(value));
  if (!number) throw Error('A positive on-chain identifier is required.');
  return number.toString();
};
const hash = value => `0x${bytes32(value)}`;
const equal = (a, b) => String(a).toLowerCase() === String(b).toLowerCase();
const requireThat = (condition, message) => { if (!condition) throw Error(message); };
const object = (keys, values) => Object.fromEntries(keys.map((key, index) => [key, values[index]]));
const clone = value => JSON.parse(json(value));
const specArgs = spec => [spec.goal, spec.successMetric, spec.bounty, String(spec.duration), String(spec.priceWeight)];
async function boundedMap(values, read, limit = 8) {
  const result = [];
  for (let index = 0; index < values.length; index += limit)
    result.push(...await Promise.all(values.slice(index,index + limit).map(read)));
  return result;
}
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
function receiptEvents(client, name, receipt) {
  const events = client.events(name, receipt);
  return Array.isArray(events) ? events : events ? [events] : [];
}
function oneEvent(client, name, receipt, matches = () => true) {
  const events = receiptEvents(client, name, receipt).filter(matches);
  requireThat(events.length === 1, `${name}: expected exactly one matching event from the selected contract.`);
  return events[0];
}

// Preserve the native Python canonical bytes, including floats and Unicode key ordering.
// The strict JSON parser validates the document; this scanner only locates its signed body.
export function nativeSignatureBody(source, envelope) {
  requireThat(source.startsWith('{"body":{'), 'Use the exact compact native delivery, without reserializing it.');
  let depth = 0, quoted = false, escaped = false, end = -1;
  for (let i = 8; i < source.length; i++) {
    const char = source[i];
    if (quoted) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') quoted = false;
    } else if (char === '"') quoted = true;
    else {
      requireThat(!/[\x20\x09\x0a\x0d]/.test(char), 'Native delivery formatting changed. Restore the exact original file.');
      if (char === '{' || char === '[') depth++;
      if (char === '}' || char === ']') { depth--; if (depth === 0) { end = i + 1; break; } }
    }
  }
  requireThat(end > 8 && source.slice(end) === `,"publicKey":${JSON.stringify(envelope.publicKey)},"signature":${JSON.stringify(envelope.signature)}}`,
    'Native delivery envelope formatting changed.');
  return source.slice(8,end);
}

export function fundingTerms(input, now, reviewWindow, planBudget) {
  const base = uint(units(input.base).toString(), 96), slope = uint(units(input.slope).toString(), 96);
  const target = uint(units(input.target).toString(), 96), maxLots = uint(String(input.maxLots), 32);
  const fundingEnd = uint(String(input.fundingEnd), 64), duration = uint(String(input.duration), 32);
  requireThat(base > 0n && maxLots > 0n && maxLots <= 1000000n, 'Use a positive first-lot price and 1–1,000,000 lots.');
  const maximumFunding = curve(0n, maxLots, base, slope);
  requireThat(target > 0n && target <= maximumFunding, 'The funding target is not reachable at this curve and lot limit.');
  requireThat(fundingEnd > now && fundingEnd <= now + 30n * DAY, 'Funding must end within the next 30 days.');
  requireThat(duration > reviewWindow && duration <= 90n * DAY, 'Execution must exceed the review window and fit within 90 days.');
  return {base, slope, target, maxLots, fundingEnd, duration, maximumFunding,
    planBudget:BigInt(planBudget), partialFunding:target < BigInt(planBudget)};
}

export class NovaWorkflow {
  constructor(client, notify = () => {}) {
    requireThat(client && typeof client.prepare === 'function' && typeof client.receipt === 'function',
      'The Studio requires the shared MARK wallet client.');
    this.client = client; this.client.requireEffectVerification = true;
    this.notify = notify; this.adapter = null; this.preview = null;
    this.revision = 0; this.observedEpoch = client.epoch; this.verifiedRoute = null;
    this.state = {package:null, publication:null, recoveryExported:false, parent:'0', seedId:null, jobId:null,
      observation:null, mint:null, route:null, steps:[], runtime:{status:'not-connected'}, receipts:[]};
    this.steps();
  }
  emit() { this.steps(); this.notify(this.state); }
  context() {
    if (this.observedEpoch !== this.client.epoch) {
      this.observedEpoch = this.client.epoch; this.state.observation = null; this.preview = null;
      this.state.runtime = {status:'not-connected'};
    }
  }
  invalidate() { this.revision++; this.preview = null; this.client.cancelPreview(); this.emit(); }
  async binding() {
    return hashObject({profile:this.client.profile, package:this.state.package?.commitments || null,
      publication:this.state.publication?.metadataURI || null, parent:this.state.parent,
      seedId:this.state.seedId, jobId:this.state.jobId});
  }
  async setPackage(pkg, {publication = null, recoveryExported = false, parent = '0', adapter = null} = {}) {
    await verifyPackage(pkg);
    requireThat(await hashObject(deploymentDescriptor(pkg.profile)) === await hashObject(deploymentDescriptor(this.client.profile)),
      'This package belongs to another deployment profile. Imported profiles cannot enable wallet writes.');
    if (unresolved(this.client.pending)) {
      const pending = this.client.pending;
      const sameMint = pending.action === 'seal' && equal(pending.args[0],pkg.commitments.capsuleHash) &&
        equal(pending.args[1],pkg.plan.planRoot) && String(pending.args[2]) === String(pkg.plan.jobs.length) &&
        String(pending.args[4]) === String(parent) && equal(pending.args[5],pkg.commitments.evidenceHash) &&
        (!publication || publication.metadataURI === pending.args[3]);
      const samePackage = this.state.package &&
        await hashObject(this.state.package.commitments) === await hashObject(pkg.commitments);
      requireThat(sameMint || samePackage,
        'This package does not match the unresolved intent. Restore its exact original package before reconciling.');
    }
    if (this.state.observation?.seed) this.assertPackageSeed(pkg, this.state.observation.seed);
    this.state.package = freeze(clone(pkg)); this.state.publication = null;
    this.state.parent = uint(String(parent)).toString(); this.state.recoveryExported = recoveryExported === true;
    this.adapter = adapter; this.invalidate();
    if (publication) await this.setPublication(publication, {adapter});
    this.emit(); return this.state.package;
  }
  async setPublication(publication, {adapter = this.adapter} = {}) {
    requireThat(this.state.package, 'Prepare or restore the exact encrypted package first.');
    const verified = await verifyPublication(this.state.package, publication, {adapter:adapter || undefined});
    this.state.publication = freeze(clone(verified?.metadataURI ? verified : publication));
    this.adapter = adapter; this.invalidate(); return this.state.publication;
  }
  markRecoveryExported() {
    requireThat(this.state.package, 'There is no encrypted package to export.');
    this.state.recoveryExported = true; this.invalidate();
  }
  assertPackageSeed(pkg, seed) {
    requireThat(equal(pkg.commitments.capsuleHash, seed.capsuleHash) && equal(pkg.plan.planRoot, seed.planRoot) &&
      equal(pkg.commitments.evidenceHash, seed.evidenceHash) && BigInt(pkg.plan.jobs.length) === BigInt(seed.jobs),
    'The attached capsule, plan, evidence or job count does not match this immutable NFT.');
  }
  async canonical(blockNumber, blockHash, epoch = this.client.epoch) {
    const block = await this.client.read('eth_getBlockByNumber', [blockNumber, false], epoch);
    requireThat(block && equal(block.hash, blockHash), 'The observed block reorganized. Refresh before continuing.');
    return block;
  }
  async seedRecord(id, block = 'latest', epoch = this.client.epoch) {
    const c = this.client, args = [idString(id)];
    const [genome, owner, uri, plan] = await Promise.all([
      c.call('Seed','genomes',args,block,epoch), c.call('Seed','ownerOf',args,block,epoch),
      c.call('Seed','tokenURI',args,block,epoch), c.call('Seed','plan',args,block,epoch)
    ]);
    const seed = object(['capsuleHash','planRoot','evidenceHash','parent','jobs','creator'], genome);
    requireThat(equal(seed.planRoot, plan[0]) && seed.jobs === plan[1], 'Genome and plan readbacks disagree.');
    return {...seed, id:args[0], owner:owner[0], metadataURI:uri[0]};
  }
  async identityStatus(account, report) {
    const c = this.client, who = address(account);
    const roles = await boundedMap([0,1,2], async role => {
      const observed = await c.inspectRole(who,String(role),report);
      return {...observed,role,label:ROLES[role],namespace:NAMESPACES[role],registered:observed.node !== ZERO_HASH};
    },3);
    return {account:who,evidence:roles[0].admission.evidence,until:roles[0].admission.until,
      admin:roles[0].governor,roles,admitted:roles[0].admitted};
  }
  async refresh(seedId = this.state.seedId, jobId = this.state.jobId) {
    this.context(); const c = this.client, epoch = c.epoch;
    this.state.observation = null;
    const selectedSeed = seedId === null || seedId === '' ? null : idString(seedId);
    const selectedJob = jobId === null || jobId === '' ? null : idString(jobId);
    const snapshot = await c.inspect(selectedSeed, selectedJob), block = snapshot.verification.blockNumber;
    snapshot.reviewWindow = (await c.call('Jobs','reviewWindow',[],block,epoch))[0];
    if (snapshot.wallet) snapshot.identity = await this.identityStatus(snapshot.wallet.account, snapshot.verification);
    if (selectedSeed) {
      snapshot.seed = await this.seedRecord(selectedSeed, block, epoch);
      if (this.state.package) this.assertPackageSeed(this.state.package, snapshot.seed);
      snapshot.review = object(['number','until','yes','no','owner'],
        await c.call('Oracle','rounds',[selectedSeed],block,epoch));
      snapshot.review.quorum = (await c.call('Oracle','quorum',[],block,epoch))[0];
      snapshot.review.maximumRiskBps = (await c.call('Oracle','maximumRiskBps',[],block,epoch))[0];
      snapshot.review.green = snapshot.green;
      snapshot.review.expired = snapshot.review.until <= BigInt(snapshot.verification.blockTime);
      snapshot.posted = [];
      if (this.state.package) {
        snapshot.posted = await boundedMap(this.state.package.plan.jobs, async job =>
          (await c.call('Mark','posted',[selectedSeed,String(job.index)],block,epoch))[0]);
        const planBudget = BigInt(this.state.package.plan.totalBounty);
        const unpostedBudget = this.state.package.plan.jobs.reduce((sum, job) =>
          sum + (snapshot.posted[job.index] ? 0n : BigInt(job.spec.bounty)), 0n);
        snapshot.budget = {planBudget, unpostedBudget, committedToPostedJobs:planBudget - unpostedBudget,
          reserve:snapshot.campaign.reserve, target:snapshot.campaign.target,
          targetFundsWholePlan:snapshot.campaign.target >= planBudget,
          reserveFundsRemainingPlan:snapshot.campaign.reserve >= unpostedBudget};
      }
      snapshot.phase = CAMPAIGNS[Number(snapshot.campaign.phase)];
    }
    if (selectedJob) {
      const boundSeed = (await c.call('Mark','jobSeed',[selectedJob],block,epoch))[0];
      requireThat(!selectedSeed || boundSeed === BigInt(selectedSeed), 'This job belongs to a different seed or marketplace.');
      snapshot.job.seedId = boundSeed.toString();
      snapshot.job.collected = (await c.call('Mark','collected',[selectedJob],block,epoch))[0];
      snapshot.job.committee = await boundedMap([0,1,2], async i =>
        (await c.call('Jobs','committees',[selectedJob,String(i)],block,epoch))[0],3);
      snapshot.job.stage = JOBS[Number(snapshot.job.state)];
      snapshot.job.settlement = Number(snapshot.job.state) === 4 ? 'accepted-payment' :
        Number(snapshot.job.state) === 5 ? snapshot.job.resultHash === ZERO_HASH ?
          'delivery-timeout-with-slashing' : 'reviewer-rejection-with-slashing' :
          Number(snapshot.job.state) === 6 ? snapshot.job.resultHash === ZERO_HASH ?
            'no-eligible-winner-refund' : 'missing-review-quorum-refund' : 'not-settled';
      snapshot.job.settlementConfirmed = false;
      if (Number(snapshot.job.state) >= 4) {
        try {
          const finalized = await c.read('eth_getBlockByNumber',['finalized',false],epoch);
          requireThat(finalized?.number && finalized?.hash, 'Finality is not available.');
          const settled = await c.call('Jobs','job',[selectedJob],finalized.number,epoch);
          snapshot.job.settlementConfirmed = settled[14] === snapshot.job.state &&
            equal(settled[16],snapshot.job.resultHash) && settled[17] === snapshot.job.refund;
          await this.canonical(finalized.number,finalized.hash,epoch);
          snapshot.job.settlementFinality = {blockNumber:finalized.number,blockHash:finalized.hash};
        } catch { c.guard(epoch); snapshot.job.settlementConfirmed = false; }
      }
    }
    await this.canonical(block, snapshot.verification.blockHash, epoch);
    this.state.seedId = selectedSeed; this.state.jobId = selectedJob; this.state.observation = snapshot;
    this.emit(); return snapshot;
  }
  inspect(seedId = this.state.seedId, jobId = this.state.jobId) { return this.refresh(seedId, jobId); }
  steps() {
    const s = this.state, o = s.observation, phase = Number(o?.campaign?.phase || 0), job = Number(o?.job?.state || 0);
    const activated = phase === 2 || (phase === 3 && o.campaign.executionEnd > 0n);
    const flags = [!!s.package, !!s.publication, !!o?.identity?.roles?.[0]?.eligible, !!o?.seed,
      !!o?.review?.green, phase > 0, activated || (phase === 1 && o.campaign.reserve >= o.campaign.target),
      activated, job > 0, !!o?.job?.resultHash && o.job.resultHash !== ZERO_HASH, o?.job?.settlementConfirmed === true];
    const ids = ['package','publish','identity','mint','review','campaign','fund','activate','route','deliver','settle'];
    const labels = ['Prepare and recover','Publish verified artifacts','Business eligibility','Nova-Seed NFT',
      'Independent review','Open campaign','Fund campaign','Activate campaign','Post committed job','Deliver result','Settle'];
    const first = flags.indexOf(false);
    s.steps = ids.map((id, index) => ({id, label:labels[index], status:flags[index] ? 'done' : index === first ? 'current' : 'waiting'}));
  }
  requireSeed() { requireThat(this.state.seedId, 'Open or mint a verified seed first.'); return this.state.seedId; }
  requirePackage() { requireThat(this.state.package, 'Restore the exact committed encrypted package first.'); return this.state.package; }
  operatorRequest(role = '0', label = '') {
    const o = this.state.observation;
    requireThat(o?.identity, 'Inspect the connected wallet before preparing an operator request.');
    const roleId = Number(uint(String(role), 8));
    requireThat(roleId < 3, 'Unknown Ascension identity role.');
    return {schema:'agialpha.novaseed.identity-request.v1', chainId:this.client.chainId,
      profile:this.client.profile.profile, access:this.client.contracts.Access, applicant:o.identity.account,
      role:roleId, requestedName:label ? `${label}.${NAMESPACES[roleId]}` : `Required name under ${NAMESPACES[roleId]}`,
      currentAdmission:{evidence:o.identity.evidence, until:String(o.identity.until)},
      admissionOperator:o.identity.admin, requiredAction:'Provision an owned ENS subname through the genuine namespace operator, then the applicant registers it. The current Access owner independently decides admission.',
      authorization:'Request only. It grants no ENS ownership, admission, signing authority or successful review.'};
  }
  reviewerRequest() {
    const id = this.requireSeed(), o = this.state.observation;
    requireThat(o?.seed, 'Refresh the seed before sharing its public review reference.');
    return {schema:'agialpha.novaseed.review-request.v1', chainId:this.client.chainId, profile:this.client.profile.profile,
      seedContract:this.client.contracts.Seed, oracle:this.client.contracts.Oracle, seedId:id,
      capsuleHash:o.seed.capsuleHash, planRoot:o.seed.planRoot, evidenceHash:o.seed.evidenceHash,
      metadataURI:o.seed.metadataURI, owner:o.seed.owner, creator:o.seed.creator,
      round:String(o.review.number), until:String(o.review.until), quorum:String(o.review.quorum),
      maximumRiskBps:String(o.review.maximumRiskBps),
      url:`?seed=${id}&profile=${encodeURIComponent(this.client.profileIdentity)}&chain=${this.client.chainId}`,
      instructions:'Use your own eligible staked validator wallet and assess the actual evidence. Obtain capsule disclosure separately when needed. Address separation alone does not establish independence.'};
  }
  async quoteFunding(lots) {
    const id = this.requireSeed(), o = await this.refresh(id), c = o.campaign, count = uint(String(lots), 32);
    requireThat(c.phase === 1n && count > 0n && c.supply + count <= c.maxLots, 'Use a valid lot count in an open funding campaign.');
    const cost = curve(c.supply, count, c.base, c.slope);
    const onchain = (await this.client.call('Mark','quote',
      [String(c.supply),String(count),String(c.base),String(c.slope)],o.verification.blockNumber))[0];
    requireThat(cost === onchain, 'Local and on-chain funding quotes disagree.');
    const allowance = o.wallet?.allowances?.Mark || 0n;
    return {lots:count.toString(), cost:tokens(cost), maxCost:tokens(cost), costBaseUnits:cost.toString(),
      allowance:allowance.toString(), needsApproval:allowance < cost, supply:String(c.supply), target:tokens(c.target),
      planBudget:this.state.package ? tokens(this.state.package.plan.totalBounty) : null,
      partialFunding:!!o.budget && c.target < o.budget.planBudget, observedBlock:o.verification.blockNumber};
  }
  async preflight(action, input) {
    this.context(); const c = this.client, epoch = c.epoch;
    const o = await this.refresh(), block = o.verification.blockNumber, now = BigInt(o.verification.blockTime);
    const who = await c.identity(epoch), id = this.state.seedId, campaign = o.campaign;
    const currentOwner = () => requireThat(o.seed && equal(o.seed.owner, who), 'The connected wallet is not the current NFT owner.');
    const eligibleBusiness = () => requireThat(o.identity?.roles[0].eligible, 'A currently owned registered business ENS name and live admission are required.');
    const green = () => requireThat(o.green === true, 'Independent risk approval is missing, expired or no longer eligible. Refresh review and its actual participants.');
    let key = ALIASES[action] || action, values, summary = {};
    if (action === 'identity' || key === 'register') {
      const role = String(input.role ?? '0'), label = input.label;
      requireThat(/^[0-2]$/.test(role), 'Choose Business, Agent or Validator.');
      requireThat(typeof label === 'string' && /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/.test(label), 'Use one lowercase ASCII ENS label.');
      const root = (await c.call('Access','roots',[role],block,epoch))[0];
      const node = (await c.call('Access','child',[root,label],block,epoch))[0];
      requireThat((await c.call('Access','owns',[who,node],block,epoch))[0], 'This wallet does not own the requested live ENS subname. Request it from the namespace operator.');
      values = [role,label]; summary = {name:`${label}.${NAMESPACES[Number(role)]}`, admissionSeparate:true};
    } else if (key === 'seal') {
      requireThat(!id, 'This project already has an opened Nova-Seed. Resume it or explicitly start a new project before minting another NFT.');
      const pkg = this.requirePackage(); await verifyPackage(pkg);
      requireThat(isRecoveryVerified(pkg) && this.state.recoveryExported,
        'Decrypt and verify the package, then export your recovery kit before preparing mint.');
      requireThat(this.state.publication, 'Publish and retrieve the exact capsule, evidence and metadata first.');
      await verifyPublication(pkg, this.state.publication, {adapter:this.adapter || undefined});
      requireThat(await hashObject(deploymentDescriptor(pkg.profile)) === await hashObject(deploymentDescriptor(c.profile)),
        'The package deployment identity changed.');
      eligibleBusiness();
      if (this.state.parent !== '0') requireThat(equal((await c.call('Seed','ownerOf',[this.state.parent],block,epoch))[0],who),
        'Creating a successor requires current ownership of the parent in this exact deployment.');
      values = [pkg.commitments.capsuleHash,pkg.plan.planRoot,String(pkg.plan.jobs.length),
        this.state.publication.metadataURI,this.state.parent,pkg.commitments.evidenceHash];
      summary = {capsuleHash:values[0], planRoot:values[1], jobs:values[2], metadataURI:values[3], parent:values[4],
        evidenceHash:values[5], mintFee:'0', tokenApprovalRequired:false, ethValue:'0', gas:'Separate ETH network fee'};
    } else if (key === 'openReview') {
      this.requireSeed(); currentOwner(); eligibleBusiness();
      requireThat(o.review.until < now, 'The current seven-day round is still active, including rejected rounds. Wait until it expires.');
      values = [id]; summary = {expiresApproximately:String(now + 7n * DAY), quorum:String(o.review.quorum)};
    } else if (key === 'attest') {
      this.requireSeed();
      requireThat(o.review.until > now && equal(o.review.owner,o.seed.owner), 'The round expired or the NFT changed owner.');
      requireThat(o.review.yes < o.review.quorum && o.review.no < o.review.quorum, 'This review round is already decided.');
      requireThat(!equal(who,o.seed.owner) && !equal(who,o.seed.creator), 'Owner and creator cannot review their own seed.');
      requireThat((await c.call('Oracle','isValidator',[who],block,epoch))[0], 'The reviewer needs current validator eligibility and sufficient stake.');
      requireThat(!(await c.call('Oracle','voted',[id,String(o.review.number),who],block,epoch))[0], 'This validator already voted in this round.');
      const risk = uint(String(input.riskBps),16);
      requireThat(risk <= 10000n && typeof input.approved === 'boolean' && hash(input.evidenceHash) !== ZERO_HASH,
        'Record an explicit evidence-bound risk decision between 0 and 10,000 basis points.');
      values = [id,String(risk),String(input.approved),hash(input.evidenceHash)];
      summary = {round:String(o.review.number), lockedUntil:String(o.review.until), independentAssessmentRequired:true};
    } else if (key === 'open') {
      this.requireSeed(); currentOwner(); green();
      requireThat(campaign.phase === 0n, 'This NFT already has a campaign. Resume it; closed campaigns cannot be reopened.');
      const pkg = this.requirePackage(), terms = fundingTerms(input,now,o.reviewWindow,pkg.plan.totalBounty);
      const longest = Math.max(...pkg.plan.jobs.map(job => job.spec.duration));
      requireThat(terms.duration >= BigInt(longest) + o.reviewWindow + 1n,
        'The execution period cannot fit the longest committed job plus auction and review.');
      values = [id,input.base,input.slope,String(input.maxLots),input.target,String(input.fundingEnd),String(input.duration)];
      summary = {...clone(terms), riskApprovalUntil:String(o.review.until),
        explanation:terms.partialFunding ? 'This target funds only part of the committed plan.' : 'The target covers the complete committed bounty budget.'};
    } else if (key === 'approve') {
      requireThat(['Mark','Oracle','Jobs'].includes(input.spender), 'Approve only a selected protocol spender.');
      const amount = units(input.amount), current = o.wallet?.allowances?.[input.spender] || 0n;
      requireThat(amount === 0n || current === 0n, 'Revoke the current nonzero allowance first, then explicitly prepare the new bounded amount.');
      requireThat(amount <= (o.wallet?.balance || 0n), 'Limit this approval to the exact intended spend within your current token balance.');
      if (input.spender === 'Mark' && amount > 0n) {
        this.requireSeed(); requireThat(campaign.phase === 1n, 'A funding campaign is required before granting its spend allowance.');
      }
      values = [input.spender,input.amount]; summary = {spender:c.contracts[input.spender], amount:input.amount,
        purchase:false, note:'An allowance transaction does not buy lots or deposit stake.'};
    } else if (key === 'buy') {
      this.requireSeed(); green(); requireThat(o.identity?.admitted, 'Funding participants need live admission; a business name is not required.');
      requireThat(campaign.phase === 1n && now < campaign.fundingEnd && equal(o.seed.owner,campaign.business), 'Funding is closed or campaign ownership changed.');
      const count = uint(String(input.lots),32);
      requireThat(count > 0n && campaign.supply + count <= campaign.maxLots, 'This lot count exceeds the remaining campaign capacity.');
      const cost = curve(campaign.supply,count,campaign.base,campaign.slope);
      const quoted = (await c.call('Mark','quote',[String(campaign.supply),String(count),String(campaign.base),String(campaign.slope)],block,epoch))[0];
      requireThat(quoted === cost, 'Funding quote mismatch.');
      const maximum = input.maxCost === undefined ? cost : units(input.maxCost);
      requireThat(maximum >= cost, 'The current quote exceeds your maximum cost.');
      requireThat(o.wallet.allowances.Mark >= maximum, 'Prepare the exact bounded MARK allowance first, then prepare the purchase again.');
      requireThat(o.wallet.balance >= cost, 'Insufficient $AGIALPHA balance for this purchase.');
      values = [id,String(count),tokens(maximum)]; summary = {lots:String(count), cost:tokens(cost), maxCost:tokens(maximum),
        allowanceSeparate:true, riskApprovalUntil:String(o.review.until), target:tokens(campaign.target)};
    } else if (key === 'bloom') {
      this.requireSeed(); currentOwner(); green();
      requireThat(equal(who,campaign.business), 'Only the campaign’s recorded business can activate it. NFT transfer does not transfer that authority.');
      requireThat(campaign.phase === 1n && now < campaign.fundingEnd && campaign.reserve >= campaign.target,
        'The campaign must still be funding and meet its target before activation.');
      requireThat((await c.call('Access','owns',[who,campaign.businessNode],block,epoch))[0], 'The original campaign ENS authority is no longer held.');
      values = [id]; summary = {irreversible:true, endsTradingAndCurveRedemption:true, reserve:tokens(campaign.reserve),
        target:tokens(campaign.target), wholePlanFunded:!!o.budget?.reserveFundsRemainingPlan};
    } else if (key === 'route') {
      this.requireSeed(); const pkg = this.requirePackage(); verifyPlan(pkg.plan); currentOwner(); green(); eligibleBusiness();
      requireThat(campaign.phase === 2n && equal(who,campaign.business), 'Only the recorded business can route an activated campaign.');
      requireThat((await c.call('Access','owns',[who,campaign.businessNode],block,epoch))[0], 'The campaign ENS authority changed.');
      const index = uint(String(input.index),32), planned = pkg.plan.jobs[Number(index)], auction = uint(String(input.auctionSeconds),32);
      requireThat(planned && index < BigInt(pkg.plan.jobs.length) && !o.posted[Number(index)], 'Select an unposted committed plan job.');
      requireThat(auction > 0n && auction <= 7n * DAY, 'Auction duration must be between one second and seven days.');
      const horizon = now + auction + BigInt(planned.spec.duration) + o.reviewWindow;
      requireThat(horizon <= campaign.executionEnd, 'Auction, work and review no longer fit before the campaign execution deadline.');
      requireThat(campaign.reserve >= BigInt(planned.spec.bounty), 'The campaign reserve cannot fund this committed bounty.');
      requireThat(Array.isArray(input.reviewers) && input.reviewers.length === 3, 'Select three genuine reviewers.');
      const reviewers = input.reviewers.map(address);
      requireThat(new Set(reviewers).size === 3 && reviewers.every(v => v !== ZERO && !equal(v,who) && !equal(v,c.contracts.Mark)),
        'Reviewers must be three distinct addresses, separate from the business and MARK.');
      const checks = await boundedMap(reviewers, async reviewer => {
        const [[valid],[until],[capacity],[active]] = await Promise.all([
          c.call('Oracle','isValidator',[reviewer],block,epoch),c.call('Oracle','jobAvailability',[reviewer,who],block,epoch),
          c.call('Oracle','jobCapacity',[reviewer],block,epoch),c.call('Oracle','activeJobs',[reviewer],block,epoch)
        ]);
        requireThat(valid && until >= horizon && active < capacity,
          `Reviewer ${reviewer} lacks live eligibility, stake, opted-in time or remaining capacity.`);
        return {reviewer,until:String(until),capacity:String(capacity),active:String(active)};
      },2);
      const indexed = (await c.call('Jobs','hashSpec',[String(index),specArgs(planned.spec)],block,epoch))[0];
      requireThat(equal(indexed,planned.leaf), 'The selected contract disagrees with the exact compiled job leaf.');
      values = [id,String(index),json(planned.spec),json(planned.proof),String(auction),json(reviewers)];
      summary = {index:String(index),spec:planned.spec,leaf:planned.leaf,proof:planned.proof,reviewers:checks,
        reviewEndNoEarlierThan:String(horizon), reserveAfterBounty:tokens(campaign.reserve - BigInt(planned.spec.bounty)),
        runtime:'Posting does not start a runtime. Export the bound work package after confirmation.'};
    } else if (key === 'transferSeed') {
      this.requireSeed(); currentOwner();
      requireThat(input.acknowledged === true, 'Confirm that transfer does not carry the capsule passphrase or campaign authority and may interrupt review or activation.');
      values = [who,address(input.to),id]; summary = {existingCampaignAuthority:campaign.business, privateCapsuleNotTransferred:true};
    } else {
      requireThat(Object.hasOwn(ACTIONS,key), 'Unsupported Studio action.');
      if (Array.isArray(input)) values = input;
      else if (Array.isArray(input.values)) values = input.values;
      else {
        values = ACTIONS[key].fields.map(field => {
          if (field.key === 'id') return this.requireSeed();
          if (field.key === 'job') return idString(input.job ?? this.state.jobId);
          const value = input[field.key];
          requireThat(value !== undefined, `Missing ${field.label}.`);
          return typeof value === 'boolean' ? String(value) : String(value);
        });
      }
      for (let position = 0; position < ACTIONS[key].fields.length; position++) {
        const field = ACTIONS[key].fields[position];
        if (field.key === 'id') requireThat(idString(values[position]) === this.requireSeed(),
          'This action references another seed. Open and verify that project explicitly first.');
        if (field.key === 'job') requireThat(this.state.jobId && idString(values[position]) === this.state.jobId,
          'This action references another job. Open and verify that job explicitly first.');
      }
      summary = {existingObligation:true,note:ACTIONS[key].note};
    }
    await this.canonical(block,o.verification.blockHash,epoch);
    return {key,values,summary};
  }
  async prepare(action, input = {}) {
    requireThat(!unresolved(this.client.pending), 'Reconcile the outstanding action before preparing another.');
    this.preview = null; const revision = ++this.revision;
    const result = await this.preflight(action,input);
    const prepared = await this.client.prepare(result.key,result.values);
    requireThat(revision === this.revision, 'The project changed while preparing. Prepare again.');
    const binding = await this.binding();
    this.preview = freeze({action,input:clone(input),binding,revision,prepared,summary:clone(result.summary)});
    this.emit(); return {...prepared,action,summary:this.preview.summary};
  }
  async confirm(acknowledged = false) {
    const preview = this.preview;
    requireThat(acknowledged === true && preview && this.client.prepared === preview.prepared,
      'Prepare and explicitly confirm the displayed transaction first.');
    requireThat(preview.revision === this.revision && preview.binding === await this.binding(), 'The package or deployment changed. Prepare again.');
    await this.preflight(preview.action,preview.input);
    requireThat(this.preview === preview && preview.binding === await this.binding(), 'The action context changed. Prepare again.');
    const transactionHash = await this.client.confirm(true);
    this.preview = null; this.emit(); return transactionHash;
  }
  async verifiedReceipt(hashValue) {
    const c = this.client, epoch = c.epoch, transactionHash = hash(hashValue);
    await c.verify(epoch);
    const receipt = await c.read('eth_getTransactionReceipt',[transactionHash],epoch);
    requireThat(receipt && receipt.status === '0x1' && equal(receipt.transactionHash,transactionHash), 'A mined successful receipt is required.');
    const tx = await c.read('eth_getTransactionByHash',[transactionHash],epoch);
    requireThat(tx && equal(tx.hash,transactionHash) && BigInt(tx.chainId) === BigInt(c.chainId) &&
      tx.blockNumber === receipt.blockNumber && equal(tx.blockHash,receipt.blockHash) &&
      equal(tx.from,receipt.from) && equal(tx.to,receipt.to) && BigInt(tx.value) === 0n,
    'Receipt, transaction, sender, destination, value and deployment chain do not agree.');
    await this.canonical(receipt.blockNumber,receipt.blockHash,epoch);
    const finalized = await c.read('eth_getBlockByNumber',['finalized',false],epoch);
    requireThat(finalized && BigInt(finalized.number) >= BigInt(receipt.blockNumber), 'The transaction is mined but not finalized. Reconcile again later.');
    return {receipt,tx,epoch};
  }
  async verifyMint(record) {
    const transactionHash = typeof record === 'string' ? record : record.candidateHash || record.hash;
    const {receipt,tx,epoch} = await this.verifiedReceipt(transactionHash), c = this.client;
    requireThat(equal(tx.to,c.contracts.Seed), 'The mint was sent to a different NovaSeed contract.');
    const event = oneEvent(c,'SeedSealed',receipt,e => equal(e.creator,tx.from));
    const id = idString(event.seedId ?? event.id), minted = await this.seedRecord(id,receipt.blockNumber,epoch);
    oneEvent(c,'Transfer',receipt,e => String(e.tokenId) === id && equal(e.from,ZERO) && equal(e.to,tx.from));
    requireThat(equal(minted.creator,tx.from) &&
      equal(event.capsuleHash,minted.capsuleHash) && equal(event.planRoot,minted.planRoot) &&
      equal(event.evidenceHash,minted.evidenceHash) && BigInt(event.parent) === minted.parent,
    'Mint event and immutable on-chain commitments do not agree.');
    const exactCall = callData('seal',[minted.capsuleHash,minted.planRoot,String(minted.jobs),minted.metadataURI,String(minted.parent),minted.evidenceHash]);
    requireThat(equal(tx.input,exactCall), 'The actual mint transaction does not match the verified NFT fields.');
    if (this.state.package) {
      this.assertPackageSeed(this.state.package,minted);
      requireThat(String(minted.parent) === this.state.parent, 'The minted parent differs from the prepared successor.');
      if (this.state.publication) requireThat(minted.metadataURI === this.state.publication.metadataURI, 'The minted metadata URI differs from the retrieved publication.');
    }
    await this.canonical(receipt.blockNumber,receipt.blockHash,epoch);
    const snapshot = await this.refresh(id,null);
    this.state.mint = {hash:hash(transactionHash),seedId:id,receipt,commitments:clone(minted),
      status:'finalized',ownershipChanged:!equal(snapshot.seed.owner,tx.from)};
    this.emit(); return this.state.mint;
  }
  async openReceipt(transactionHash) { return this.verifyMint(transactionHash); }
  async verifyRoute(record) {
    const {receipt,tx,epoch} = await this.verifiedReceipt(record.candidateHash || record.hash), c = this.client;
    requireThat(equal(tx.to,c.contracts.Mark) && record.action === 'route' && equal(tx.input,callData('route',record.args)),
      'This is not the recorded MARK route intent.');
    const [seed,index,spec,proof,auction,reviewers] = record.args;
    const event = oneEvent(c,'MissionRouted',receipt,e => String(e.id ?? e.seedId) === String(seed) && String(e.index) === String(index));
    const jobId = idString(event.jobId), planned = this.requirePackage().plan.jobs[Number(index)];
    requireThat(planned && equal(event.leaf,planned.leaf) && json(spec) === json(specArgs(planned.spec)),
      'The routed event is not the exact committed specification.');
    const [marketHash] = await c.call('Jobs','hashSpec',['0',spec],receipt.blockNumber,epoch);
    const read = object(['client','business','worker','bounty','price','bond','auctionEnd','executionEnd','reviewEnd','due',
      'duration','priceWeight','yes','no','state','specHash','resultHash','refund','claimed'],
    await c.call('Jobs','job',[jobId],receipt.blockNumber,epoch));
    const bound = (await c.call('Mark','jobSeed',[jobId],receipt.blockNumber,epoch))[0];
    const posted = oneEvent(c,'JobPosted',receipt,e => String(e.id) === jobId && equal(e.business,tx.from));
    requireThat(equal(posted.specHash,marketHash) && posted.goal === planned.spec.goal &&
      posted.successMetric === planned.spec.successMetric && BigInt(posted.bounty) === BigInt(planned.spec.bounty) &&
      BigInt(posted.auctionEnd) === read.auctionEnd && BigInt(posted.reviewEnd) === read.reviewEnd,
    'The job posting event does not bind the exact text, bounty and deadlines.');
    requireThat(bound === BigInt(seed) && equal(read.client,c.contracts.Mark) && equal(read.business,tx.from) &&
      equal(read.specHash,marketHash) && read.bounty === BigInt(planned.spec.bounty) &&
      read.duration === BigInt(planned.spec.duration) && read.priceWeight === BigInt(planned.spec.priceWeight) && read.state > 0n,
    'The resulting job does not match its seed, client, business, specification, bounty and auction state.');
    for (let i = 0; i < 3; i++) requireThat(equal(
      (await c.call('Jobs','committees',[jobId,String(i)],receipt.blockNumber,epoch))[0],reviewers[i]),
    'The resulting reviewer committee differs from the authorized route.');
    requireThat((await c.call('Mark','posted',[String(seed),String(index)],receipt.blockNumber,epoch))[0], 'The committed index was not marked posted.');
    requireThat(read.state >= 4n || (await c.call('Token','balanceOf',[c.contracts.Jobs],receipt.blockNumber,epoch))[0] >= read.bounty,
      'The marketplace escrow does not cover the newly posted job bounty.');
    await this.canonical(receipt.blockNumber,receipt.blockHash,epoch);
    await this.refresh(String(seed),jobId);
    this.state.route = {hash:hash(record.candidateHash || record.hash),seedId:String(seed),index:Number(index),jobId,
      leaf:event.leaf,receipt,status:'finalized'};
    this.verifiedRoute = freeze(clone(this.state.route));
    this.state.runtime = {status:'not-connected'}; this.emit(); return this.state.route;
  }
  async openRouteReceipt(transactionHash) {
    const {receipt,tx,epoch} = await this.verifiedReceipt(transactionHash), c = this.client;
    requireThat(equal(tx.to,c.contracts.Mark), 'The route transaction targets a different MARK contract.');
    const event = oneEvent(c,'MissionRouted',receipt), seedId = idString(event.id), index = Number(event.index);
    const pkg = this.requirePackage(), planned = pkg.plan.jobs[index];
    requireThat(planned && equal(planned.leaf,event.leaf), 'This route belongs to another exact plan or index.');
    const jobId = idString(event.jobId), job = await c.call('Jobs','job',[jobId],receipt.blockNumber,epoch);
    const block = await this.canonical(receipt.blockNumber,receipt.blockHash,epoch), reviewers = [];
    for (let i = 0; i < 3; i++) reviewers.push((await c.call('Jobs','committees',[jobId,String(i)],receipt.blockNumber,epoch))[0]);
    const args = [seedId,String(index),specArgs(planned.spec),planned.proof,String(job[6] - BigInt(block.timestamp)),reviewers];
    requireThat(equal(tx.input,callData('route',args)), 'The route receipt does not encode this exact job, proof and committee.');
    return this.verifyRoute({action:'route',args,hash:hash(transactionHash)});
  }
  async reconcile(transactionHash) {
    const c = this.client, known = c.history.find(record => equal(record.hash,transactionHash) || equal(record.candidateHash,transactionHash));
    let result;
    try {
      result = await c.receipt(transactionHash,!known);
      this.preview = null;
      if (!['finalized','effect-unverified'].includes(result.status) || result.receipt?.status !== '0x1') {
        this.invalidateObservation(transactionHash,result.status); return result;
      }
      if (result.action === 'seal') await this.verifyMint(result);
      else if (result.action === 'route') await this.verifyRoute(result);
      else { await this.verifyTransition(result); await this.refresh(); }
      if (result.status === 'effect-unverified') c.completeEffects(result);
    } catch (error) {
      this.invalidateObservation(transactionHash,'effect-unverified'); throw error;
    }
    const saved = this.state.receipts.find(receipt => equal(receipt.hash,transactionHash));
    if (saved) { saved.status = 'finalized'; saved.receipt = result.receipt; }
    else
      this.state.receipts.push({hash:hash(transactionHash),action:result.action,status:'finalized',receipt:result.receipt});
    this.emit(); return result;
  }
  invalidateObservation(transactionHash, status) {
    this.preview = null; this.state.observation = null;
    for (const key of ['mint','route']) if (equal(this.state[key]?.hash,transactionHash)) this.state[key].status = status;
    for (const receipt of this.state.receipts) if (equal(receipt.hash,transactionHash)) receipt.status = status;
    this.verifiedRoute = null; this.emit();
  }
  async verifyTransition(record) {
    const c = this.client, receipt = record.receipt, id = record.args[0], block = receipt.blockNumber;
    if (record.action === 'open') {
      oneEvent(c,'MarketOpened',receipt,e => String(e.id) === String(id) && equal(e.business,record.transaction.from));
      const campaign = await c.call('Mark','campaigns',[String(id)],block);
      requireThat(campaign[12] === 1n && equal(campaign[0],record.transaction.from) &&
        campaign[1] === BigInt(record.args[1]) && campaign[2] === BigInt(record.args[2]) &&
        campaign[3] === BigInt(record.args[4]) && campaign[4] === BigInt(record.args[3]), 'Opened campaign readback differs from the funding terms.');
    } else if (record.action === 'openReview') {
      const event = oneEvent(c,'ReviewOpened',receipt,e => String(e.seedId ?? e.id) === String(id) && equal(e.owner,record.transaction.from));
      const round = await c.call('Oracle','rounds',[String(id)],block);
      requireThat(round[0] === BigInt(event.round) && round[1] === BigInt(event.until) && equal(round[4],record.transaction.from), 'Review round readback mismatch.');
    } else if (record.action === 'attest') {
      const event = oneEvent(c,'RiskAttested',receipt,e => String(e.seedId ?? e.id) === String(id) && equal(e.validator,record.transaction.from));
      requireThat(BigInt(event.riskBps) === BigInt(record.args[1]) && equal(event.evidenceHash,record.args[3]) &&
        (await c.call('Oracle','voted',[String(id),String(event.round),record.transaction.from],block))[0], 'Risk vote readback mismatch.');
    } else if (record.action === 'buy') {
      const event = oneEvent(c,'Traded',receipt,e => String(e.id) === String(id) && equal(e.account,record.transaction.from) && e.buy === true);
      requireThat(BigInt(event.lots) === BigInt(record.args[1]) && BigInt(event.value) <= BigInt(record.args[2]) &&
        (await c.call('Mark','lots',[String(id),record.transaction.from],block))[0] >= BigInt(event.lots), 'Funding receipt does not match the bounded purchase.');
    } else if (record.action === 'bloom') {
      const event = oneEvent(c,'Bloomed',receipt,e => String(e.id) === String(id));
      const campaign = await c.call('Mark','campaigns',[String(id)],block), plan = await c.call('Seed','plan',[String(id)],block);
      requireThat(campaign[12] === 2n && equal(event.planRoot,plan[0]) && equal(event.businessNode,campaign[13]) &&
        BigInt(event.funding) === campaign[11], 'Activation event and campaign state do not agree.');
    }
    await this.canonical(receipt.blockNumber,receipt.blockHash);
  }
  async discoverSeeds({fromBlock, cursor = null, toBlock, maxWindows = 5} = {}) {
    const c = this.client, epoch = c.epoch, report = await c.verify(epoch), who = await c.identity(epoch);
    const profile = c.profile.profile, contract = address(c.contracts.Seed);
    requireThat(Number.isInteger(maxWindows) && maxWindows >= 1 && maxWindows <= 10, 'Use 1–10 bounded discovery windows.');
    if (cursor) requireThat(cursor.profile === profile && cursor.contract === contract && cursor.account === who &&
      cursor.chainId === c.chainId, 'This ownership cursor belongs to another wallet or deployment.');
    let start = cursor ? uint(cursor.nextBlock) : uint(String(fromBlock ?? c.profile.contracts.Seed.deploymentBlock ?? c.profile.deploymentBlock ?? '0'));
    const end = uint(String(toBlock ?? BigInt(report.blockNumber))), candidates = new Set(cursor?.candidates || []);
    requireThat(candidates.size <= 5000 && end <= BigInt(report.blockNumber), 'Discovery bounds exceed the observed chain.');
    let windows = 0, windowSize = 2000n;
    while (start <= end && windows < maxWindows) {
      const last = start + windowSize - 1n < end ? start + windowSize - 1n : end;
      const accountTopic = `0x${tuple(['address'],[who])}`, range = {address:contract,
        fromBlock:`0x${start.toString(16)}`,toBlock:`0x${last.toString(16)}`};
      let logs;
      try {
        const groups = await Promise.all([
          c.read('eth_getLogs',[{...range,topics:[TRANSFER,null,accountTopic]}],epoch),
          c.read('eth_getLogs',[{...range,topics:[TRANSFER,accountTopic]}],epoch)
        ]);
        requireThat(groups.every(Array.isArray), 'Invalid ownership log response.'); logs = groups.flat();
        requireThat(logs.length <= 2000, 'Provider returned too many ownership logs; reduce the discovery window.');
      } catch (error) {
        c.guard(epoch); if (windowSize <= 1n) throw error; windowSize /= 2n; continue;
      }
      for (const log of logs) {
        requireThat(!log.removed && equal(log.address,contract) && Array.isArray(log.topics) && log.topics.length === 4 &&
          equal(log.topics[0],TRANSFER) && (equal(log.topics[1],accountTopic) || equal(log.topics[2],accountTopic)) && log.data === '0x',
        'Invalid or removed NFT ownership log.');
        requireThat(BigInt(log.blockNumber) >= start && BigInt(log.blockNumber) <= last, 'Ownership log lies outside the requested range.');
        await this.canonical(log.blockNumber,log.blockHash,epoch);
        candidates.add(idString(BigInt(hash(log.topics[3])).toString()));
        requireThat(candidates.size <= 5000, 'Discovery reached its 5,000-seed limit. Resume using a narrower block range.');
      }
      start = last + 1n; windows++;
    }
    const seeds = [];
    for (const id of candidates) {
      const owner = (await c.call('Seed','ownerOf',[id],report.blockNumber,epoch))[0];
      if (equal(owner,who)) seeds.push({id,owner,contract,chainId:c.chainId});
    }
    await this.canonical(report.blockNumber,report.blockHash,epoch);
    return {seeds,complete:start > end,observedBlock:report.blockNumber,
      cursor:{schema:'agialpha.novaseed.discovery.v1',chainId:c.chainId,profile,contract,account:who,
        nextBlock:start.toString(),candidates:[...candidates]}, nextBlock:start.toString(),
      notice:'Ownership is verified at the displayed block. Resume scans and refresh after incoming or outgoing transfers.'};
  }
  async createSuccessor(seedId = this.state.seedId) {
    const id = idString(seedId), o = await this.refresh(id), who = await this.client.identity();
    requireThat(equal(o.seed.owner,who), 'Only the current owner can use this seed as a parent.');
    return {parent:id,profile:clone(this.client.profile),parentCommitments:clone(o.seed),
      plan:this.state.package ? clone(this.state.package.plan) : null,
      instructions:'Create and seal a new package. The parent remains unchanged; risk review, admission, funding and evidence are not inherited.'};
  }
  workPackage(index = this.state.route?.index) {
    const pkg = this.requirePackage(), o = this.state.observation, seedId = this.requireSeed();
    requireThat(this.state.jobId && o?.job && o.job.seedId === seedId, 'Refresh a verified posted MARK job before exporting work.');
    requireThat(Number.isInteger(index) && pkg.plan.jobs[index], 'Choose the exact routed plan index.');
    const job = pkg.plan.jobs[index], zeroIndexed = compilePlan([job.spec]).jobs[0].leaf;
    requireThat(equal(o.job.specHash,zeroIndexed) && this.verifiedRoute?.index === index &&
      this.verifiedRoute.jobId === this.state.jobId && this.verifiedRoute.seedId === seedId,
    'Reconcile the exact MissionRouted receipt for this seed, job and index before exporting work. Identical specifications do not identify a plan index.');
    return {schema:'agialpha.novaseed.work-package.v1',chainId:this.client.chainId,profile:clone(this.client.profile),
      seedId,jobId:this.state.jobId,planIndex:index,plan:clone(pkg.plan),spec:clone(job.spec),proof:clone(job.proof),
      leaf:job.leaf,marketSpecHash:zeroIndexed,commitments:clone(pkg.commitments),
      artifacts:this.state.publication ? {metadataURI:this.state.publication.metadataURI,
        capsuleURI:this.state.publication.capsuleURI,evidenceURI:this.state.publication.evidenceURI} : null,
      acceptanceCriteria:job.spec.successMetric,allowedInputs:'Public, licensed or explicitly authorized inputs only; no wallet secrets or capsule passphrase.',
      delivery:{format:'agialpha.ascension.reviewed-delivery.v1',exactBytesRequired:true,resultHash:'Keccak-256 of the exact delivered bytes',
        independentOnChainReviewRequired:true},runtime:{status:'not-connected',
        setupGuide:`${SITE}agent/FACTORY_GUIDE/`,protocolGuide:`${SITE}agent/ASCENSION_PROTOCOL/`,successorGuide:`${SITE}successor/`,
        commands:['alpha-agent ascension-check plan.json',
          `alpha-agent ascension-deliver plan.json --index ${index} --mission MISSION_ID --output delivery.json`,
          `alpha-agent ascension-verify-delivery delivery.json --public-key TRUSTED_KEY --plan-root ${pkg.plan.planRoot}`],
        authority:'Exporting this file grants no execution, wallet, computer-use or settlement permission.'},
      deadlines:{auctionEnd:String(o.job.auctionEnd),executionEnd:String(o.job.executionEnd),reviewEnd:String(o.job.reviewEnd),due:String(o.job.due)},
      siteBase:SITE,links:{mark:new URL(this.links().mark,`${SITE}ascension/mainnet/`).href,
        nativeGuide:`${SITE}agent/FACTORY_GUIDE/`,successor:`${SITE}successor/`}};
  }
  async importDelivery(source, {trustedPublicKey, index = this.verifiedRoute?.index} = {}) {
    const work = this.workPackage(index);
    requireThat(typeof source === 'string' && typeof trustedPublicKey === 'string' && /^[0-9a-f]{64}$/i.test(trustedPublicKey),
      'Use exact native delivery bytes and an independently trusted Ed25519 public key.');
    const envelope = parseBoundedJSON(source,{maxBytes:2 * 1024 * 1024,preserveUnsafeIntegers:true});
    requireThat(Object.keys(envelope).sort().join() === 'body,publicKey,signature',
      'The delivery must retain its exact canonical bytes and supported envelope.');
    const signedBody = nativeSignatureBody(source,envelope);
    requireThat(equal(envelope.publicKey,trustedPublicKey), 'The delivery signer differs from the independently trusted key.');
    const body = envelope.body;
    requireThat(body?.schema === 'agialpha.ascension.reviewed-delivery.v1' &&
      Object.keys(body).sort().join() === 'jobIndex,nativeExport,plan,schema', 'Unsupported native Ascension delivery.');
    verifyPlan(body.plan);
    requireThat(body.plan.planRoot === work.plan.planRoot && body.jobIndex === index,
      'The delivery belongs to another committed plan or job index.');
    const document = body.nativeExport?.receipt?.body?.document;
    requireThat(document?.review?.approved === true && document?.request?.goal === work.spec.goal,
      'The native delivery must bind a locally approved mission with this exact committed goal.');
    requireThat(typeof envelope.signature === 'string' && /^[A-Za-z0-9+/]{86}==$/.test(envelope.signature),
      'Malformed Ed25519 signature.');
    const keyBytes = Uint8Array.from(trustedPublicKey.match(/../g),value => parseInt(value,16));
    const publicKey = await crypto.subtle.importKey('raw',keyBytes,{name:'Ed25519'},false,['verify']);
    const signature = Uint8Array.from(atob(envelope.signature),char => char.charCodeAt(0));
    const signedDigest = await crypto.subtle.digest('SHA-256',toUtf8Bytes(signedBody));
    requireThat(await crypto.subtle.verify('Ed25519',publicKey,signature,signedDigest), 'Native delivery signature verification failed.');
    const resultHash = keccak256(toUtf8Bytes(source)), o = await this.refresh();
    if (o.job.resultHash !== ZERO_HASH) requireThat(equal(o.job.resultHash,resultHash),
      'The imported bytes differ from the artifact already submitted on chain.');
    this.state.runtime = {status:'evidence-imported',jobId:work.jobId,seedId:work.seedId,index,resultHash,
      signer:trustedPublicKey,signatureVerified:true,connected:false,executionReplayed:false,
      qualification:'Signer and exact plan/job binding checked. Run the native verifier for computational replay; independent on-chain review remains separate.'};
    this.emit(); return this.state.runtime;
  }
  links() {
    const query = new URLSearchParams({profile:this.client.profileIdentity,chain:String(this.client.chainId)});
    if (this.state.seedId) query.set('seed',this.state.seedId);
    if (this.state.jobId) query.set('job',this.state.jobId);
    return {mark:`../../ascension-protocol/mainnet/?${query}`,nativeGuide:'../../agent/FACTORY_GUIDE/',
      successor:'../../successor/',journal:'Shared MARK transaction journal; unresolved actions remain blocking across both workspaces.'};
  }
}
