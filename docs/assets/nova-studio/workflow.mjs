// SPDX-License-Identifier: Apache-2.0
import { tokens, units, uint, address, curve } from '../ascension-wallet/protocol.mjs';
import { StudioChain } from './chain.mjs';
import { verifyPlan } from './plan.mjs';
import { createPackage, recoverPackage, exportKit, importKit, objectHash, profileIdentity, verifyPackage } from './package.mjs';
import { publishPackage, verifyPublication, metadataFor } from './storage.mjs';
const eq = (a,b) => address(a) === address(b);
export class NovaWorkflow {
  constructor(session, storage) {
    this.session=session; this.client=session.client; this.chain=new StudioChain(this.client); this.storage=storage;
    this.package=null; this.publication=null; this.seedId=null; this.jobIds=[]; this.recovered=false; this.exported=false;
    this.observation=null; this.preview=null;
  }
  clearPreview() { this.preview=null; this.client.cancelPreview(); }
  async create(draft, passphrase) {
    const pkg=await createPackage(draft,passphrase,this.client.profile);
    this.clearPreview(); this.package=pkg; this.publication=null; this.seedId=null; this.jobIds=[];
    this.recovered=true; this.exported=false; this.observation=null; return pkg;
  }
  async restore(text,passphrase) {
    const body=await importKit(text,this.client.profile);
    const genome=await recoverPackage(body.package,passphrase,this.client.profile);
    // Import journal first; refusal must not replace the current project.
    if (body.journal?.transactions?.length) await this.session.restore(body.journal);
    this.clearPreview(); this.package=body.package; this.publication=body.publication; this.seedId=body.seedId;
    this.jobIds=body.jobIds; this.recovered=true; this.exported=false; this.observation=null;
    return genome;
  }
  async kit() {
    const kit=await exportKit(this.package,{publication:this.publication,seedId:this.seedId,jobIds:this.jobIds,journal:this.client.journal()});
    this.exported=true; return kit;
  }
  async publish(credential, publicConsent) {
    if (!publicConsent || !this.recovered || !this.exported) throw Error('Recover and export your kit, then review and approve the public fields.');
    this.clearPreview();
    this.publication=await publishPackage(this.package,this.storage,credential,p=>{this.publication=p;},this.publication);
    return this.publication;
  }
  async inspect(seedId=this.seedId) {
    this.clearPreview();
    const state=await this.chain.seed(seedId,this.package);
    this.seedId=seedId; this.observation=state; return state;
  }
  async preflight(action,input={}) {
    const c=this.client, chain=this.chain, who=await c.identity();
    if (action==='seal') {
      if (!this.package || !this.recovered || !this.exported || this.seedId) throw Error('Recover and export this unminted package first.');
      await verifyPackage(this.package,c.profile);
      this.publication=await verifyPublication(this.package,this.publication,this.storage);
      if (!(await chain.identity(who)).eligible) throw Error('The minting wallet needs an owned registered business name and current admission.');
      if (this.package.parent!=='0' && !eq((await c.call('Seed','ownerOf',[this.package.parent]))[0],who)) throw Error('This wallet does not own the parent seed.');
      const p=this.package;
      return ['seal',[p.capsuleHash,p.plan.planRoot,String(p.plan.jobs.length),this.publication.metadataURI,p.parent,p.evidenceHash]];
    }
    if (action==='register') return ['register',[input.role || '0',input.label]];
    if (['validatorDeposit','validatorWithdraw','agentDeposit','agentWithdraw'].includes(action)) return [action,[input.amount]];
    if (action==='approveStake') {
      if (!['Oracle','Jobs'].includes(input.spender)) throw Error('Select the validator or worker staking contract.');
      return ['approve',[input.spender,input.amount]];
    }
    if (action==='availability') return ['availability',[input.business,input.until,input.capacity]];
    if (action==='revoke') return ['approve',[input.spender,'0']];
    if (!this.seedId) throw Error('Open or mint the seed first.');
    const state=await chain.seed(this.seedId,this.package), campaign=state.campaign, now=BigInt(state.verification.blockTime);
    this.observation=state;
    if (action==='transferSeed') {
      if (!input.acknowledged || !eq(who,state.seedOwner)) throw Error('Only the current owner may explicitly transfer this NFT.');
      return ['transferSeed',[who,input.to,this.seedId]];
    }
    if (action==='openReview') return ['openReview',[this.seedId]];
    if (action==='attest') {
      if (!this.recovered || !this.package || !input.reviewed) throw Error('Recover and verify the package and explicitly complete your independent review.');
      if (typeof input.findings!=='string' || !input.findings.trim() || new TextEncoder().encode(input.findings).length>8000) throw Error('Record substantive review findings up to 8 KB.');
      if (eq(who,state.seedOwner) || eq(who,state.genome.creator)) throw Error('The creator and owner cannot independently review this seed.');
      if (!(await c.call('Oracle','isValidator',[who]))[0]) throw Error('Current validator identity and sufficient stake are required.');
      if (BigInt(state.review.until)<=now) throw Error('Review round has expired. The owner must open a new round.');
      if ((await chain.call('Oracle','voted',[this.seedId,state.review.round,who]))[0]) throw Error('This validator already voted in this round.');
      this.reviewEvidence={schema:'agialpha.nova-studio.review.v1',deployment:profileIdentity(c.profile),
        seedId:this.seedId,round:state.review.round,reviewer:who,findings:input.findings};
      return ['attest',[this.seedId,input.risk,input.approved,await objectHash(this.reviewEvidence)]];
    }
    if (action==='open') {
      if (campaign.phase!==0n) throw Error('This seed already has a campaign. Resume it; a closed campaign cannot reopen.');
      const base=units(input.base), slope=units(input.slope), count=uint(input.maxLots,32), target=units(input.target);
      uint(String(base),96); uint(String(slope),96); uint(String(target),96);
      if (!base || !count || !target || curve(0n,count,base,slope)<target) throw Error('The funding target must be reachable within the lot limit.');
      const hours=uint(input.fundingHours,32), duration=uint(input.executionDays,32)*86400n;
      if (!hours || hours>720n || duration<=BigInt(state.reviewWindow) || duration>90n*86400n) throw Error('Funding: 1–720 hours. Execution: more than 3 and at most 90 days.');
      return ['open',[this.seedId,input.base,input.slope,input.maxLots,input.target,String(now+hours*3600n),String(duration)]];
    }
    if (['approveFunding','buy','sell'].includes(action)) {
      const count=uint(input.count,32);
      if (!count || campaign.phase!==1n || (action==='sell' && (state.yourLots===null || count>state.yourLots))) throw Error('Choose a valid lot count in the funding phase.');
      const supply=action==='sell'?campaign.supply-count:campaign.supply;
      if (supply<0n || (action!=='sell' && supply+count>campaign.maxLots)) throw Error('Lot count exceeds the campaign bound.');
      const cost=curve(supply,count,campaign.base,campaign.slope);
      if ((await c.call('Mark','quote',[String(supply),String(count),String(campaign.base),String(campaign.slope)],state.verification.blockNumber))[0]!==cost)
        throw Error('Provider quote differs from exact local arithmetic.');
      const limit=units(input.limit);
      if (action==='sell') {
        if (cost<limit) throw Error('Current return is below your minimum.');
        return ['sell',[this.seedId,input.count,input.limit]];
      }
      if (cost>limit) throw Error(`Current quote is ${tokens(cost)} $AGIALPHA, above your maximum.`);
      if (action==='approveFunding') return ['approve',['Mark',input.limit]];
      if ((await c.call('Token','allowance',[who,c.contracts.Mark]))[0]<cost) throw Error('Prepare a separate bounded approval, confirm it, then prepare the purchase again.');
      return ['buy',[this.seedId,input.count,input.limit]];
    }
    if (action==='bloom') {
      if (!input.irreversible) throw Error('Acknowledge that activation immediately ends curve trading and redemption.');
      if (campaign.phase!==1n || campaign.reserve<campaign.target || now>=campaign.fundingEnd || !state.green ||
          !eq(who,campaign.business) || !eq(who,state.seedOwner) || !(await c.call('Access','owns',[who,campaign.businessNode]))[0])
        throw Error('Activation needs the original business authority, current owner, live review and funded open campaign.');
      return ['bloom',[this.seedId]];
    }
    if (action==='route') {
      if (!this.package || !this.recovered) throw Error('Recover the exact committed plan before launching a job.');
      verifyPlan(this.package.plan);
      const index=Number(uint(input.index,32)), job=this.package.plan.jobs[index], auction=uint(input.auction,32);
      if (!job || !auction || auction>7n*86400n || !Array.isArray(input.reviewers) || input.reviewers.length!==3) throw Error('Select a committed job, a 1–604,800 second auction and three reviewers.');
      if (campaign.phase!==2n || !state.green || !eq(who,campaign.business) || !eq(who,state.seedOwner)) throw Error('Only the current green business can route an activated campaign.');
      if ((await chain.call('Mark','posted',[this.seedId,index]))[0]) throw Error('This plan index is already posted. Reconcile the original route; do not repeat it.');
      const horizon=now+auction+BigInt(job.spec.duration)+BigInt(state.reviewWindow);
      if (horizon>campaign.executionEnd || BigInt(job.spec.bounty)>campaign.reserve) throw Error('Job exceeds remaining execution time or treasury reserve.');
      const reviewers=input.reviewers.map(address);
      if (new Set(reviewers).size!==3 || reviewers.some(x=>eq(x,who)||eq(x,c.contracts.Mark))) throw Error('Choose three distinct independent reviewers.');
      const availability=await Promise.all(reviewers.map(x=>chain.reviewer(x,who,horizon,state.verification.blockNumber)));
      if (availability.some(x=>!x.available)) throw Error('A reviewer lacks current eligibility, stake, opt-in time or capacity. Ask that reviewer to update availability.');
      return ['route',[this.seedId,input.index,JSON.stringify(job.spec),JSON.stringify(job.proof),input.auction,JSON.stringify(reviewers)]];
    }
    if (['close','reclaim'].includes(action)) return [action,[this.seedId]];
    if (action==='transferLots') return [action,[this.seedId,input.to,input.count]];
    if (['collect','bid','award','submit','validate','timeout','jobRefund'].includes(action)) {
      const jobId=input.jobId;
      if (String((await chain.call('Mark','jobSeed',[jobId]))[0])!==this.seedId) throw Error('Job does not belong to this seed’s MARK campaign.');
      const inspection=await c.inspect(this.seedId,jobId), job=inspection.job, observed=BigInt(inspection.verification.blockTime);
      if (action==='bid') {
        const duration=uint(input.duration,32), price=units(input.price);
        if (job.state!==1n || observed>=job.auctionEnd) throw Error('This auction is no longer accepting bids.');
        if (!duration || duration>=job.duration || job.auctionEnd+duration>=job.executionEnd)
          throw Error('Promise a delivery time shorter than the job limit. Leave time for the award transaction; late awards can still make a bid ineligible.');
        if (price<100n || price>job.bounty) throw Error('Bid price must fit the committed bounty and contract minimum.');
        return ['bid',[jobId,input.price,input.duration]];
      }
      if (action==='award' && (job.state!==1n || observed<job.auctionEnd)) throw Error('An open auction can be processed only after its end.');
      if (action==='submit') {
        if (job.state!==2n || !eq(who,job.worker) || observed>job.due) throw Error('Delivery requires the awarded worker, an assigned job and an unexpired delivery deadline. Refresh the job state.');
        if ((await this.storage.retrieveBytes(input.uri,undefined,2000000)).byteHash!==input.result)
          throw Error('Published result bytes do not match the selected result file.');
        return ['submit',[jobId,input.result,input.uri]];
      }
      if (action==='validate') {
        if (job.state!==3n || observed>job.reviewEnd || input.result?.toLowerCase()!==job.resultHash.toLowerCase())
          throw Error('Review requires the exact delivered result hash, a submitted job and an unexpired review deadline.');
        if (!input.reviewed || typeof input.findings!=='string' || !input.findings.trim() || new TextEncoder().encode(input.findings).length>8000)
          throw Error('Independently review the exact delivered file and record findings up to 8 KB.');
        this.resultReviewEvidence={schema:'agialpha.nova-studio.result-review.v1',deployment:profileIdentity(c.profile),
          seedId:this.seedId,jobId,resultHash:input.result,reviewer:who,approved:input.approved==='true',findings:input.findings};
        return ['validate',[jobId,input.result,input.approved,await objectHash(this.resultReviewEvidence)]];
      }
      return [action,[jobId]];
    }
    throw Error('Unsupported workflow action.');
  }
  async prepare(action,input={}) {
    this.clearPreview();
    const epoch=this.client.epoch, [method,values]=await this.preflight(action,input);
    this.client.guard(epoch);
    const preview=await this.session.prepare(method,values);
    this.preview={action,input:JSON.parse(JSON.stringify(input)),method,values,prepared:preview};
    return preview;
  }
  async confirm(acknowledged) {
    const intent=this.preview;
    if (!intent || this.client.prepared!==intent.prepared) throw Error('Prepare a fresh action first.');
    // Publication, eligibility, capacity and phase are refreshed immediately before signing.
    return this.session.confirm(acknowledged,async()=>{
      const [method,values]=await this.preflight(intent.action,intent.input);
      // Relative campaign deadlines were bound at preview. Validate rather than silently replacing them.
      if (method==='open') values[5]=intent.values[5];
      if (method!==intent.method || JSON.stringify(values)!==JSON.stringify(intent.values)) throw Error('Action changed after preview. Prepare again.');
      if (this.client.prepared!==intent.prepared) throw Error('Wallet context changed after preview.');
    });
  }
  async reconcile(hash) {
    const record=await this.session.reconcile(hash); this.preview=null;
    if (record.status!=='finalized') return record;
    if (record.action==='seal' && this.package && !this.publication) {
      const metadataURI=record.args[3], {object:metadata}=await this.storage.retrieve(metadataURI);
      const expected=metadataFor(this.package,metadata.capsule?.uri,metadata.evidence?.uri);
      this.publication=await verifyPublication(this.package,{schema:'agialpha.nova-studio.publication.v1',metadataURI,
        capsuleURI:metadata.capsule.uri,evidenceURI:metadata.evidence.uri,metadataHash:await objectHash(expected)},this.storage);
    }
    if (record.action==='seal' && this.package && this.publication) {
      this.observation=await this.chain.verifyMint(record,this.package,this.publication); this.seedId=this.observation.seedId;
    } else if (record.action==='route' && this.package && this.seedId) {
      const jobId=await this.chain.verifyRoute(record,this.package,this.seedId);
      if (!this.jobIds.includes(jobId)) this.jobIds.push(jobId);
      this.observation=await this.chain.seed(this.seedId,this.package);
    } else if (this.seedId) this.observation=await this.chain.seed(this.seedId,this.package);
    return record;
  }
  async workPackage(jobId) {
    await verifyPackage(this.package,this.client.profile);
    const state=await this.client.inspect(this.seedId,jobId), job=state.job;
    if (String((await this.chain.call('Mark','jobSeed',[jobId]))[0])!==this.seedId) throw Error('Job is not bound to this seed.');
    // JobMarket hashes index zero, while MARK commits the actual plan index.
    const {leaf}=await import('./plan.mjs');
    let matching=this.package.plan.jobs.filter(x=>leaf(0,x.spec)===job.specHash);
    if (matching.length>1) {
      // Identical specifications are legal at different committed indices. Resolve
      // the actual index from a canonical transaction, never from imported status.
      const routes=this.client.history.filter(r=>r.action==='route' && String(r.args[0])===this.seedId);
      const verified=[];
      for (const route of routes) {
        if (!route.hash) continue;
        const receipt=await this.session.exclusive(()=>this.client.receipt(route.hash));
        if (await this.chain.verifyRoute(receipt,this.package,this.seedId)===jobId)
          verified.push(this.package.plan.jobs[Number(route.args[1])]);
      }
      matching=verified;
    }
    if (matching.length!==1) throw Error('Restore the recovery journal containing the original route receipt to identify this committed job.');
    return {schema:'agialpha.nova-studio.work.v1',deployment:this.package.deployment,seedId:this.seedId,jobId,
      job:matching[0],plan:this.package.plan,artifacts:this.publication,
      allowedInputs:'Public, licensed or explicitly authorized synthetic inputs only.',
      acceptance:matching[0].spec.successMetric,delivery:{due:String(job.due),reviewEnd:String(job.reviewEnd),
        required:'Exact result-file SHA-256, immutable result URI and independent review evidence'},
      native:{verifyPlan:'alpha-agent ascension-check plan.json',delivery:'alpha-agent ascension-deliver',
        guide:'agent/ASCENSION_PROTOCOL.md'},runtime:{status:'not-connected',authority:'No execution, spending or wallet permission granted.'}};
  }
}
