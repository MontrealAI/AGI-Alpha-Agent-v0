// SPDX-License-Identifier: Apache-2.0
import { ACTIONS, tokens, units, uint, address, curve } from '../ascension-wallet/protocol.mjs';
import { canonicalProfile, unresolved } from '../ascension-wallet/client.mjs';
import { INTERFACES, StudioChain } from './chain.mjs';
import { keccak256 } from './vendor/ethers-6.17.0.mjs';
import { verifyNativeDelivery } from './native-delivery.mjs';
import { verifyPlan } from './plan.mjs';
import { createPackage, recoverPackage, exportKit, importKit, objectHash, profileIdentity, verifyPackage, deploymentIdentityStatus } from './package.mjs';
import { publishPackage, verifyPublication, metadataFor } from './storage.mjs';
const eq = (a,b) => address(a) === address(b);
export class NovaWorkflow {
  constructor(session, storage) {
    this.session=session; this.client=session.client; this.chain=new StudioChain(this.client); this.storage=storage;
    this.package=null; this.publication=null; this.seedId=null; this.jobIds=[]; this.recovered=false; this.exported=false;
    this.observation=null; this.preview=null;
    this.client.requireEffectVerification=true; this.nativeDelivery=null; this.verifiedRoutes=new Map();
  }
  clearPreview() { this.preview=null; this.client.cancelPreview(); }
  get deploymentIdentity() { return this.package ? deploymentIdentityStatus(this.package,this.client.profile) : null; }
  stale() { this.observation=null; this.nativeDelivery=null; this.verifiedRoutes.clear(); this.clearPreview(); }
  async create(draft, passphrase) {
    if (this.client.history.some(unresolved)) throw Error('Reconcile the outstanding transaction before replacing its project.');
    const pkg=await createPackage(draft,passphrase,this.client.profile);
    this.clearPreview(); this.package=pkg; this.publication=null; this.seedId=null; this.jobIds=[];
    this.recovered=true; this.exported=false; this.stale(); return pkg;
  }
  async restore(text,passphrase) {
    const body=await importKit(text,this.client.profile);
    const genome=await recoverPackage(body.package,passphrase,this.client.profile);
    if (!this.client.history.some(unresolved) && body.journal?.transactions?.length)
      await this.session.restore(body.journal);
    return this.session.exclusive(async()=>{
      // Attaching recovery material never replaces the live journal. A fresh tab
      // may recover the exact pending route/funding intent without submitting it.
      const p=body.package;
      const outstanding=this.client.history.filter(unresolved);
      let associated=outstanding.length===0;
      for (const pending of outstanding) {
        const imported=body.journal?.transactions?.find(record=>record.action===pending.action &&
          canonicalProfile(record.transaction)===canonicalProfile(pending.transaction) &&
          canonicalProfile(record.args)===canonicalProfile(pending.args));
        if (pending.action==='seal') {
          if (pending.args[0]===p.capsuleHash && pending.args[1]===p.plan.planRoot &&
              String(pending.args[2])===String(p.plan.jobs.length) && String(pending.args[4])===p.parent &&
              pending.args[5]===p.evidenceHash && (!body.publication || pending.args[3]===body.publication.metadataURI))
            associated=true;
        } else {
          if (!imported) continue;
          const fields=ACTIONS[pending.action]?.fields || [];
          if (fields.some((field,index)=>field.key==='id' && String(pending.args[index])!==body.seedId ||
              field.key==='job' && !body.jobIds.includes(String(pending.args[index])))) continue;
          if (pending.action==='route') {
            const index=Number(pending.args[1]), job=p.plan.jobs[index];
            if (!job || INTERFACES.Mark.encodeFunctionData('route',[body.seedId,index,job.spec,job.proof,
                pending.args[4],pending.args[5]]).toLowerCase()!==pending.transaction.data.toLowerCase()) continue;
          }
          associated=true;
        }
      }
      // The shared journal can contain several projects. Attach one matching
      // project at a time; all other uncertain records continue blocking writes.
      if (!associated) throw Error('Restore the exact package and recovery seed associated with an unresolved transaction.');
      this.package=p; this.publication=body.publication; this.seedId=body.seedId;
      this.jobIds=body.jobIds; this.recovered=true; this.exported=false; this.stale();
      return genome;
    });
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
    this.clearPreview(); this.observation=null;
    const state=await this.chain.seed(seedId,this.package);
    this.seedId=seedId; this.observation=state; return state;
  }
  async preflight(action,input={}) {
    const c=this.client, chain=this.chain, who=await c.identity();
    if (action==='seal') {
      if (!this.package || !this.recovered || !this.exported || this.seedId) throw Error('Recover and export this unminted package first.');
      await verifyPackage(this.package,c.profile);
      if (this.deploymentIdentity!=='exact-source')
        throw Error('This legacy package records addresses only. Preserve it for recovery; create a new package with exact source identity before minting.');
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
        const retrieved=await this.storage.retrieveBytes(input.uri,undefined,2000000);
        if (input.native===true) {
          const native=this.nativeDelivery;
          if (!native || native.epoch!==c.epoch || native.seedId!==this.seedId || native.jobId!==jobId ||
              native.resultHash!==input.result || native.planRoot!==this.package.plan.planRoot)
            throw Error('Import and verify this native delivery for the connected worker and exact selected job first.');
          const work=await this.workPackage(jobId);
          const checked=await verifyNativeDelivery(native.source,{trustedPublicKey:native.signer,
            plan:this.package.plan,index:work.job.index});
          if (checked.resultHash!==input.result || keccak256(retrieved.bytes)!==input.result)
            throw Error('Published native delivery bytes differ from the verified signed artifact.');
        } else if (retrieved.byteHash!==input.result) throw Error('Published result bytes do not match the selected generic SHA-256 result file.');
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
    return this.session.exclusive(async()=>{
      // Sync the shared journal and stop before live observations can be reused
      // while an earlier transaction still has an uncertain effect.
      if (this.client.history.some(unresolved)) throw Error('Reconcile the outstanding transaction before starting another.');
      const epoch=this.client.epoch, [method,values]=await this.preflight(action,input);
      this.client.guard(epoch);
      const preview=await this.client.prepare(method,values);
      this.preview={action,input:JSON.parse(JSON.stringify(input)),method,values,prepared:preview};
      return preview;
    });
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
    this.clearPreview();
    return this.session.exclusive(async()=>{
      try {
        const record=await this.client.receipt(hash,true);
        if (!['finalized','effect-unverified'].includes(record.status) || record.receipt?.status!=='0x1') {
          this.stale(); return record;
        }
        const selectedMint=record.action==='seal' && this.package && record.args[0]===this.package.capsuleHash &&
          record.args[1]===this.package.plan.planRoot && record.args[5]===this.package.evidenceHash;
        if (selectedMint && !this.publication) {
          const metadataURI=record.args[3], {object:metadata}=await this.storage.retrieve(metadataURI);
          const expected=metadataFor(this.package,metadata.capsule?.uri,metadata.evidence?.uri);
          this.publication=await verifyPublication(this.package,{schema:'agialpha.nova-studio.publication.v1',metadataURI,
            capsuleURI:metadata.capsule.uri,evidenceURI:metadata.evidence.uri,metadataHash:await objectHash(expected)},this.storage);
        }
        if (record.action==='seal') {
          if (selectedMint) {
            this.observation=await this.chain.verifyMint(record,this.package,this.publication); this.seedId=this.observation.seedId;
          } else await this.chain.openMintReceipt(hash);
        } else if (record.action==='route') {
          const seedId=String(record.args[0]);
          const selected=!!this.package && this.seedId===seedId;
          const jobId=await this.chain.verifyRoute(record,selected?this.package:null,seedId);
          if (selected) {
            this.verifiedRoutes.set(jobId,{hash,index:Number(record.args[1])});
            if (!this.jobIds.includes(jobId)) this.jobIds.push(jobId);
            this.observation=await this.chain.seed(seedId,this.package);
          }
        } else if (this.seedId) this.observation=await this.chain.seed(this.seedId,this.package);
        else await this.client.inspect();
        if (record.status==='effect-unverified') this.client.completeEffects(record);
        return record;
      } catch (error) { this.stale(); throw error; }
    });
  }
  async workPackage(jobId) {
    await verifyPackage(this.package,this.client.profile);
    const state=await this.chain.inspectJob(this.seedId,jobId,this.package), job=state.job;
    // JobMarket hashes index zero, while MARK commits the actual plan index.
    const {leaf}=await import('./plan.mjs');
    let matching=this.package.plan.jobs.filter(x=>leaf(0,x.spec)===job.specHash);
    if (matching.length>1) {
      // Identical specifications are legal at different committed indices. Resolve
      // the actual index from a canonical transaction, never from imported status.
      const routes=this.client.history.filter(r=>r.action==='route' && String(r.args[0])===this.seedId);
      if (this.verifiedRoutes.has(jobId)) routes.push({hash:this.verifiedRoutes.get(jobId).hash});
      const verified=[];
      for (const hash of new Set(routes.map(route=>route.hash).filter(Boolean))) {
        const route=await this.chain.openRouteReceipt(hash,this.package,this.seedId);
        if (route.jobId===jobId) verified.push(this.package.plan.jobs[route.index]);
      }
      matching=verified;
    }
    if (matching.length!==1) throw Error('Restore the recovery journal containing the original route receipt to identify this committed job.');
    return {schema:'agialpha.nova-studio.work.v1',deployment:this.package.deployment,seedId:this.seedId,jobId,
      job:matching[0],plan:this.package.plan,artifacts:this.publication,
      allowedInputs:'Public, licensed or explicitly authorized synthetic inputs only.',
      acceptance:matching[0].spec.successMetric,delivery:{due:String(job.due),reviewEnd:String(job.reviewEnd),
        required:'Generic files: exact SHA-256. Native signed Ascension delivery: Keccak-256 of the original complete signed envelope. Use the matching import mode, immutable URI and independent review evidence.'},
      native:{verifyPlan:'alpha-agent ascension-check plan.json',delivery:'alpha-agent ascension-deliver',
        guide:'https://montrealai.github.io/AGI-Alpha-Agent-v0/agent/ASCENSION_PROTOCOL/'},
      runtime:{status:'not-connected',authority:'No execution, spending or wallet permission granted.'}};
  }
  async importNativeDelivery(source,{trustedPublicKey,jobId}) {
    this.nativeDelivery=null; this.clearPreview();
    const epoch=this.client.epoch, work=await this.workPackage(jobId);
    const checked=await verifyNativeDelivery(source,{trustedPublicKey,plan:this.package.plan,index:work.job.index});
    this.client.guard(epoch);
    const state=await this.chain.inspectJob(this.seedId,jobId,this.package);
    if (BigInt(state.job.resultHash)!==0n && state.job.resultHash!==checked.resultHash)
      throw Error('This signed artifact differs from the result already delivered on chain.');
    this.nativeDelivery=Object.freeze({...checked,source,epoch,seedId:this.seedId,jobId,status:'evidence-imported'});
    const {source:privateSource,epoch:walletEpoch,...report}=this.nativeDelivery;
    return report;
  }
  async openRouteReceipt(hash) {
    if (!this.package || !this.seedId) throw Error('Open the seed and restore its exact package first.');
    const route=await this.chain.openRouteReceipt(hash,this.package,this.seedId);
    this.verifiedRoutes.set(route.jobId,{hash,index:route.index});
    if (!this.jobIds.includes(route.jobId)) this.jobIds.push(route.jobId);
    return route;
  }
}
