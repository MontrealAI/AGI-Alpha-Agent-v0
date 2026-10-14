// SPDX-License-Identifier: Apache-2.0
import { tokens, units, uint, address, curve } from '../ascension-wallet/protocol.mjs';
import { StudioChain } from './chain.mjs';
import { verifyPlan } from './plan.mjs';
import { createPackage, recoverPackage, exportKit, importKit, objectHash, hashBytes, profileIdentity, verifyPackage, strictJSON } from './package.mjs';
import { publishPackage, verifyPublication, metadataFor } from './storage.mjs';
import { createProject, updateCycle, addCycle, preserveSignedRecord, exportProjectKit, importProjectKit, registerMission, completeMission, observeCycle, projectReservoir, freezeEvaluation, recordEvaluation, verifyEvaluation, decideEvaluation, prepareSuccessor } from './cycle.mjs';
import { makeRuntimeRequest, verifyTerms, verifyRuntimeResult, verifySettlementRecord, resultCommitments, verifyEnvelope } from './runtime.mjs';
import * as runtimeEvidence from './runtime.mjs';
import { canonical, digest } from '../successor/engine.mjs?nova-cycle=38c4f38978bf9fc29f207bae3adee0755bc6530d04502a36c491cc430787e488';
const eq = (a,b) => address(a) === address(b);
export class NovaWorkflow {
  constructor(session, storage) {
    this.session=session; this.client=session.client; this.chain=new StudioChain(this.client); this.storage=storage;
    this.package=null; this.publication=null; this.seedId=null; this.jobIds=[]; this.recovered=false; this.exported=false;
    this.observation=null; this.preview=null;
    this.project=null; this.runtimeResult=null; this.runtimeTrust=null; this.runtimeTerms=new Map();
    this.runtimeSettlement=null; this.runtimeEvaluation=null; this.runtimeReuse=null;
  }
  get cycleId() { return this.project?.activeCycleId || null; }
  get currentCycle() { return this.project?.cycles.find(cycle=>cycle.cycleId===this.cycleId) || null; }
  async ensureProject(options={}) {
    if (!this.project) this.project=await createProject(this.package,options);
    return this.project;
  }
  async syncProject() {
    await this.ensureProject();
    this.project=await updateCycle(this.project,this.cycleId,{...(this.package?{package:this.package}:{}),publication:this.publication,
      seedId:this.seedId,jobIds:this.jobIds,journal:this.client.journal()});
    return this.project;
  }
  async projectKit(passphrase) {
    await this.syncProject();
    return exportProjectKit(this.project,passphrase);
  }
  async restoreProject(text,passphrase,capsulePassphrase=passphrase) {
    const project=await importProjectKit(text,passphrase), cycle=project.cycles.find(item=>item.cycleId===project.activeCycleId);
    const genome=cycle.package?await recoverPackage(cycle.package,capsulePassphrase,this.client.profile):null;
    if (cycle.journal?.transactions?.length) await this.session.restore(cycle.journal);
    this.clearPreview(); this.project=project; this.package=cycle.package; this.publication=cycle.publication;
    this.seedId=cycle.seedId; this.jobIds=[...cycle.jobIds]; this.recovered=true; this.exported=false;
    this.observation=null; this.runtimeResult=null; this.runtimeTrust=null; this.runtimeTerms.clear();
    this.runtimeSettlement=null; this.runtimeEvaluation=null; this.runtimeReuse=null;
    return genome;
  }
  async nextCycle(draft,passphrase,options={}) {
    if (!this.package) throw Error('Create and preserve the first exact package first.');
    await this.syncProject();
    let parent='0';
    if (this.seedId) {
      const state=await this.inspect();
      if (!eq(await this.client.identity(),state.seedOwner)) throw Error('Only the current seed owner may use this same-contract parent.');
      parent=this.seedId;
    }
    const pkg=await createPackage({...draft,parent},passphrase,this.client.profile);
    if (this.runtimeReuse) await this.refreshArtifactReuse();
    if (this.runtimeEvaluation?.report) await this.importEvaluation(this.runtimeEvaluation.freezeText,this.runtimeEvaluation.reportText,this.runtimeEvaluation.observerKey);
    const reuse=this.runtimeReuse, evaluation=this.runtimeEvaluation;
    if (this.currentCycle.missions.length && !this.currentCycle.evaluations.some(item=>item.evidence&&item.decision)) throw Error('Review and record the evaluated improvement outcome before deliberately continuing this native project.');
    if (this.currentCycle.missions.length && !reuse) throw Error('Select and freshly review an actual accepted first-cycle artifact for reuse before continuing.');
    const adopted=evaluation && this.currentCycle.evaluations.find(item=>item.evaluationId===evaluation.modelId)?.decision?.decision==='adopt';
    const project=reuse?await prepareSuccessor(this.project,this.cycleId,pkg,{...options,assetIds:[reuse.asset.assetId],verifiedAssets:[reuse.token],evaluationId:adopted?evaluation.modelId:null,verified:evaluation?.token}):await addCycle(this.project,pkg,{parentCycleId:this.cycleId,...options});
    this.clearPreview(); this.project=project; this.package=pkg; this.publication=null; this.seedId=null; this.jobIds=[];
    this.observation=null; this.recovered=true; this.exported=false; this.runtimeResult=null; this.runtimeTrust=null; this.runtimeTerms.clear();
    this.runtimeSettlement=null; this.runtimeEvaluation=null;
    return pkg;
  }
  async runtimeRequest(index,workSpec) {
    await this.syncProject();
    const reuse=this.runtimeReuse;
    if (reuse && reuse.sourceCycleId!==this.cycleId) {
      await this.refreshArtifactReuse();
      const {assertNumericalReuse}=await import('./reuse.mjs');
      workSpec=assertNumericalReuse(this.runtimeReuse.selection,workSpec,{projectId:this.project.projectId,cycleId:this.cycleId});
      workSpec={...workSpec,rights:{...workSpec.rights,source:`${workSpec.rights.source}; reused calculation-input.json SHA-256 ${reuse.asset.digest}`}};
    }
    const request=await makeRuntimeRequest(this.package,Number(index),this.project.projectId,this.cycleId,workSpec);
    const existing=this.currentCycle.missions.find(m=>m.request.plan_index===Number(index));
    if (existing) {
      if (canonical(existing.request)!==canonical(request)) throw Error('This committed job already has an immutable executor request. Use another plan index or a new cycle for changed work.');
      return existing.request;
    }
    this.project=await registerMission(this.project,this.cycleId,{request,...(reuse&&reuse.sourceCycleId!==this.cycleId?{sourceAssetIds:[reuse.asset.assetId],verifiedAssets:[this.runtimeReuse.token],freshConditions:'Fresh coefficients with the explicitly reviewed prior calculation procedure; new authorization required.'}:{})});
    return request;
  }
  requestFor(index) {
    const missions=this.currentCycle?.missions.filter(m=>m.request.plan_index===Number(index)) || [];
    if (missions.length!==1) throw Error('Prepare the exact executor request for this committed job first.');
    return missions[0].request;
  }
  async verifyNativeTerms(request,seal,observerKey) {
    await this.client.verify();
    const codeHashes={};
    await Promise.all(['Jobs','Mark','Seed','Token'].map(async name=>{
      const code=await this.client.read('eth_getCode',[this.client.contracts[name],'latest']);
      if (!/^0x(?:[0-9a-fA-F]{2})+$/.test(code)) throw Error('Native deployment bytecode is unavailable.');
      const bytes=Uint8Array.from(code.slice(2).match(/../g),part=>parseInt(part,16));
      codeHashes[name]=(await resultCommitments(bytes)).keccak256;
    }));
    return verifyTerms(request,seal,this.client.profile,this.seedId,observerKey,codeHashes);
  }
  async importTerms(index,text,observerKey) {
    const request=this.requestFor(index), seal=strictJSON(text), epoch=this.client.epoch;
    const body=await this.verifyNativeTerms(request,seal,observerKey);
    const checkpoint=body.preposting_checkpoint;
    const block=await this.client.read('eth_getBlockByNumber',['0x'+BigInt(checkpoint.number).toString(16),false]);
    if (block?.hash!==checkpoint.hash) throw Error('Preposting checkpoint is no longer canonical. Ask the runtime to inspect it.');
    if ((await this.chain.call('Mark','posted',[this.seedId,Number(index)]))[0]) throw Error('A new runtime seal cannot be attached after this job was posted.');
    this.client.guard(epoch);
    const project=await preserveSignedRecord(this.project,{kind:'preposting',originalText:text});
    this.project=project; this.runtimeTerms.set(Number(index),{seal,observerKey,epoch});
    return body;
  }
  async importRuntimeResult(text,observerKey) {
    const result=strictJSON(text), index=result.execution_binding?.body?.plan_binding?.plan_index;
    const request=this.requestFor(index), checked=await verifyRuntimeResult(request,result,observerKey);
    await this.verifyNativeTerms(request,result.terms_seal,observerKey);
    const epoch=this.client.epoch, state=await this.client.inspect(this.seedId,String(checked.binding.market_job_id));
    if (String((await this.chain.call('Mark','jobSeed',[String(checked.binding.market_job_id)]))[0])!==String(this.seedId) || state.job.worker.toLowerCase()!==checked.binding.selected_worker.toLowerCase() || state.job.specHash!==checked.binding.market_spec_hash) throw Error('Observed job and native result disagree.');
    const delivered=state.job.resultHash!=='0x'+'0'.repeat(64);
    if (([3n,4n].includes(state.job.state)||delivered) && state.job.resultHash!==checked.hashes.keccak256) throw Error('The chain delivery differs from this exact native artifact.');
    checked.deliveryState=delivered?'recorded-on-chain':state.job.state>=5n?'closed-without-delivery':'not-yet-delivered';
    this.client.guard(epoch);
    const project=await preserveSignedRecord(this.project,{kind:'runtime-run',originalText:text});
    this.project=project; this.runtimeResult=result; this.runtimeTrust={observerKey,epoch};
    return checked;
  }
  async importRuntimeSettlement(text,observerKey) {
    if (!this.runtimeResult) throw Error('Verify the exact native result with your pinned observer key first.');
    const record=strictJSON(text), settlement=await verifySettlementRecord(record,observerKey);
    const result=this.runtimeResult, binding=result.execution_binding.body, epoch=this.client.epoch;
    await verifyRuntimeResult(this.requestFor(binding.plan_binding.plan_index),result,observerKey);
    if (settlement.chain.chain!==String(this.client.profile.chainId) || settlement.chain.market.toLowerCase()!==this.client.contracts.Jobs.toLowerCase() || String(settlement.chain.job)!==String(binding.market_job_id) || settlement.execution_binding_digest!==result.execution_binding.digest || settlement.delivery_digest!==result.delivery.digest || settlement.candidate_verdict!==result.candidate_verdict) throw Error('Settlement does not belong to this exact execution and delivery.');
    const jobId=String(binding.market_job_id), receipt=await this.client.read('eth_getTransactionReceipt',[settlement.transaction_hash]);
    if (!receipt || receipt.status!=='0x1' || receipt.blockHash!==settlement.block.hash || BigInt(receipt.blockNumber)!==BigInt(settlement.block.number)) throw Error('Settlement receipt is missing, reverted or changed.');
    const finalized=await this.client.read('eth_getBlockByNumber',['finalized',false]);
    if (!finalized || BigInt(finalized.number)<BigInt(receipt.blockNumber)) throw Error('Settlement is not finalized. Keep it pending.');
    const state=await this.client.inspect(this.seedId,jobId);
    const terminal={4:['accepted','paid'],5:['rejected','failed'],6:['unresolved_no_quorum','refunded']}[Number(state.job.state)];
    if (!terminal || settlement.job_acceptance!==terminal[0] || settlement.settlement_status!==terminal[1] || settlement.token?.toLowerCase()!==this.client.contracts.Token.toLowerCase() || settlement.decimals!==18 || settlement.symbol!=='AGIALPHA' || settlement.customer_realized_value!==null || ['memory_admission','institutional_admission','authority_status'].some(field=>settlement[field]!=='not_granted')) throw Error('Signed settlement status, asset or authority claims contradict the verified chain outcome.');
    const closed=this.chain.events(receipt,'Jobs','Closed').filter(event=>String(event.id)===jobId);
    if (closed.length!==1 || closed[0].state!==state.job.state || closed[0].refundable!==BigInt(settlement.refund_base_units) || state.job.resultHash!==result.artifact_keccak256) throw Error('Settlement event, final state and exact result do not reconcile.');
    const payouts=this.chain.events(receipt,'Jobs','Payout').filter(event=>String(event.id)===jobId);
    if (payouts.length!==settlement.payouts.length || payouts.some((event,i)=>event.recipient.toLowerCase()!==settlement.payouts[i].recipient.toLowerCase() || event.gross!==BigInt(settlement.payouts[i].gross) || event.burned!==BigInt(settlement.payouts[i].burned))) throw Error('Settlement payouts and burn differ from the signed accounting.');
    if ((await this.client.read('eth_getBlockByNumber',[receipt.blockNumber,false]))?.hash!==receipt.blockHash) throw Error('Settlement block reorganized. Refresh before continuing.');
    for (const cycle of this.project.cycles) for (const item of cycle.signedRecords.filter(r=>r.kind==='settlement')) {
      const old=strictJSON(item.originalText).settlement;
      if (old && canonical(old.chain)===canonical(settlement.chain) && (cycle.cycleId!==this.cycleId || canonical(old)!==canonical(settlement))) throw Error('This payment is already attributed to another cycle or result.');
    }
    this.client.guard(epoch);
    let project=await preserveSignedRecord(this.project,{kind:'settlement',originalText:text});
    const mission=this.currentCycle.missions.find(item=>item.request.plan_index===binding.plan_binding.plan_index);
    project=await completeMission(project,this.cycleId,mission.missionId,{runId:binding.execution_authorization.authorization_id,resultDigest:result.artifact_sha256,settlementId:`${settlement.chain.chain}:${settlement.chain.market.toLowerCase()}:${settlement.chain.job}`});
    this.project=project; this.runtimeSettlement={text,settlement,observerKey};
    return settlement;
  }
  retainedResult(artifactHash) {
    for (const cycle of this.project.cycles) for (const record of cycle.signedRecords.filter(item=>item.kind==='runtime-run')) {
      const result=strictJSON(record.originalText);
      if (result.artifact_keccak256!==artifactHash) continue;
      const request=cycle.missions.find(item=>item.request.plan_index===result.execution_binding.body.plan_binding.plan_index)?.request;
      if (request) return {request,result,cycle,originalText:record.originalText};
    }
    throw Error('Retain the exact original runtime result and request before evaluating it.');
  }
  async evaluationProtocol(freeze,baseline) {
    const body=freeze.body;
    return {baselineDigest:await objectHash({method:body.methods.baseline,environment:body.source_environment_digest}),candidateDigest:await objectHash({method:body.methods.candidate,environment:body.source_environment_digest}),taskDigest:'0x'+body.request_digest,procedureDigest:'0x'+freeze.digest,resourceBudget:body.budget,acceptance:{criterion:body.criterion,scope:'Exact numerical quality only; costs and independent holdout remain unqualified.'},heldOut:{method:body.input_policy,evidenceDigest:await objectHash(body.fresh_common_inputs),tuningExposure:false},expectedRunIds:[body.request_digest],rollbackDigest:baseline.result.artifact_sha256};
  }
  async importEvaluationFreeze(text,observerKey) {
    const freeze=strictJSON(text), body=await verifyEnvelope(freeze,'ascension-evaluation-freeze',observerKey);
    if (body.project_id!==this.project.projectId || body.cycle_id!==this.cycleId || body.authority_status!=='not_granted') throw Error('Evaluation freeze belongs to another project or cycle.');
    const baseline=this.retainedResult(body.baseline_artifact_keccak256);
    await verifyRuntimeResult(baseline.request,baseline.result,observerKey);
    if (body.baseline_request_digest!==baseline.result.request_digest) throw Error('Baseline request differs from its frozen identity.');
    // Runtime domain separation differs from the private project checksum.
    let request;
    for (const item of this.currentCycle.missions) if (await digest('ascension-studio-request',item.request)===body.request_digest) request=item.request;
    if (!request || canonical(request.work_spec.inputs)!==canonical(body.fresh_common_inputs)) throw Error('Prepare the exact fresh comparison request before importing its freeze.');
    if (this.currentCycle.signedRecords.some(item=>item.kind==='runtime-run'&&strictJSON(item.originalText).request_digest===body.request_digest)) throw Error('Import the frozen protocol before the fresh execution result. Preserve late records as history only.');
    const protocol=await this.evaluationProtocol(freeze,baseline);
    let project=await preserveSignedRecord(this.project,{kind:'evaluation',originalText:text});
    const known=this.currentCycle.evaluations.find(item=>item.protocol.procedureDigest==='0x'+freeze.digest);
    if (known && canonical(known.protocol)!==canonical(protocol)) throw Error('Retained model protocol differs from the signed native freeze.');
    if (!known) project=await freezeEvaluation(project,this.cycleId,protocol);
    const evaluation=project.cycles.find(item=>item.cycleId===this.cycleId).evaluations.find(item=>item.protocol.procedureDigest==='0x'+freeze.digest);
    this.project=project; this.runtimeEvaluation={modelId:evaluation.evaluationId,freeze,freezeText:text,observerKey,token:null};
    return freeze;
  }
  async importEvaluation(freezeText,reportText,observerKey) {
    const freeze=strictJSON(freezeText), report=strictJSON(reportText), body=freeze.body;
    if (body.project_id!==this.project.projectId || body.cycle_id!==this.cycleId || body.authority_status!=='not_granted') throw Error('Evaluation freeze belongs to another project or cycle.');
    const evaluation=this.currentCycle.evaluations.find(item=>item.protocol.procedureDigest==='0x'+freeze.digest);
    if (!evaluation) throw Error('Import and retain the frozen protocol before the fresh execution result.');
    const baseline=this.retainedResult(body.baseline_artifact_keccak256), evaluated=this.retainedResult(report.body.evaluated_artifact_keccak256);
    if (evaluated.cycle.cycleId!==this.cycleId) throw Error('Evaluated execution belongs to another cycle.');
    const checked=await runtimeEvidence.verifyEvaluationRecords(freeze,report,baseline.request,baseline.result,evaluated.request,evaluated.result,observerKey);
    if (canonical(evaluation.protocol)!==canonical(await this.evaluationProtocol(freeze,baseline))) throw Error('Retained evaluation protocol differs from the authenticated frozen comparison.');
    let project=await preserveSignedRecord(this.project,{kind:'evaluation',originalText:reportText});
    const record=project.cycles.find(item=>item.cycleId===this.cycleId).signedRecords.find(item=>item.originalText===reportText);
    const verdict=checked.outcome==='PASS'?'PASS':checked.outcome==='FAIL'?'FAIL':'inconclusive';
    const derived={protocolHash:evaluation.protocolHash,verdict,sourceRecordId:record.recordId,runIds:[body.request_digest],leakage:false,comparableBudgets:canonical(body.budget)===canonical(report.body.budget),qualityRegressed:verdict==='FAIL',missingCosts:report.body.compute_cost===null||report.body.human_cost===null,originalReport:reportText};
    if (!evaluation.evidence) project=await recordEvaluation(project,evaluation.evaluationId,derived);
    else {
      const {reportHash,effectiveVerdict,...retained}=evaluation.evidence;
      if (reportHash!==await hashBytes(new TextEncoder().encode(reportText))) throw Error('Recovered original report hash changed.');
      if (canonical(retained)!==canonical(derived) || effectiveVerdict!==verdict) throw Error('Recovered evaluation claims differ from the authenticated numerical outcome.');
    }
    const current=project.cycles.find(item=>item.cycleId===this.cycleId).evaluations.find(item=>item.evaluationId===evaluation.evaluationId);
    const token=await verifyEvaluation(project,evaluation.evaluationId,async()=>({valid:true,protocolHash:await objectHash(await this.evaluationProtocol(freeze,baseline)),reportHash:await hashBytes(new TextEncoder().encode(reportText)),verdict,source:`Separately pinned native observer ${observerKey}; fixed numerical scope, not independent review.`}));
    this.project=project; this.runtimeEvaluation={modelId:evaluation.evaluationId,freeze,freezeText,report,reportText,observerKey,token};
    return {...checked,evaluation:current};
  }
  async decideImprovement(decision,reviewer,rationale) {
    const evidence=this.runtimeEvaluation;
    if (!evidence?.report) throw Error('Verify a frozen comparison and its original report first.');
    this.project=await decideEvaluation(this.project,evidence.modelId,{decision,reviewer,rationale,verified:evidence.token});
    return this.currentCycle.evaluations.find(item=>item.evaluationId===evidence.modelId);
  }
  async authorizeArtifactReuse(review,source={}) {
    const {authorizeArtifactReuse}=await import('./reuse.mjs');
    const retained=this.retainedResult(source.artifactHash||this.runtimeResult?.artifact_keccak256);
    const {result,request,cycle}=retained, sourceCycleId=cycle.cycleId;
    const observerKey=source.observerKey||this.runtimeTrust?.observerKey;
    const record=cycle.signedRecords.find(item=>item.kind==='settlement'&&strictJSON(item.originalText).settlement?.delivery_digest===result.delivery.digest);
    if (!record || !observerKey) throw Error('Retain the exact finalized settlement and pin the source runtime observer first.');
    const authorized=await authorizeArtifactReuse(this.project,sourceCycleId,{artifactName:'calculation-input.json',review,verifyCurrent:async()=>{
      const verifier=new NovaWorkflow(this.session,this.storage);
      verifier.project={...this.project,activeCycleId:sourceCycleId}; verifier.package=cycle.package;
      verifier.seedId=cycle.seedId;
      await verifier.importRuntimeResult(retained.originalText,observerKey);
      const settlement=await verifier.importRuntimeSettlement(record.originalText,observerKey);
      return {request,result,settlement,observerKey};
    }});
    this.project=authorized.project; this.runtimeReuse={...authorized,sourceCycleId,review,observerKey,artifactHash:result.artifact_keccak256};
    return authorized;
  }
  async refreshArtifactReuse() {
    const reuse=this.runtimeReuse;
    if (!reuse) throw Error('Select and review an exact reusable artifact first.');
    return this.authorizeArtifactReuse(reuse.review,{artifactHash:reuse.artifactHash,observerKey:reuse.observerKey});
  }
  async reservoir() {
    await this.syncProject();
    const observation=await observeCycle(this.project,this.cycleId,this.chain);
    return projectReservoir(this.project,this.cycleId,observation);
  }
  async ledger(observerKey) {
    await this.syncProject();
    const {readProjectLedger}=await import('./ledger.mjs');
    return readProjectLedger(this.project,this.chain,{observerKey,account:this.client.account});
  }
  async reinvestmentProposal(input) {
    await this.syncProject();
    const {createReinvestmentProposal}=await import('./ledger.mjs');
    return createReinvestmentProposal(this.project,this.cycleId,this.chain,{...input,destination:{deployment:profileIdentity(this.client.profile),seedId:this.seedId},approvalActor:this.client.account});
  }
  clearPreview() { this.preview=null; this.client.cancelPreview(); }
  async create(draft, passphrase) {
    if (this.package) throw Error('Preserve this package and deliberately prepare a new cycle.');
    const pkg=await createPackage(draft,passphrase,this.client.profile);
    const project=this.project?await updateCycle(this.project,this.cycleId,{package:pkg}):await createProject(pkg,{title:draft.title});
    this.clearPreview(); this.package=pkg; this.publication=null; this.seedId=null; this.jobIds=[];
    this.project={...project,title:draft.title}; this.runtimeResult=null; this.runtimeTrust=null; this.runtimeTerms.clear();
    this.runtimeSettlement=null; this.runtimeEvaluation=null; this.runtimeReuse=null;
    this.recovered=true; this.exported=false; this.observation=null; return pkg;
  }
  async restore(text,passphrase) {
    const body=await importKit(text,this.client.profile);
    const genome=await recoverPackage(body.package,passphrase,this.client.profile);
    let project=await createProject(body.package,{title:genome.project?.title||'Recovered Nova-Seed project'});
    project=await updateCycle(project,project.activeCycleId,{publication:body.publication,seedId:body.seedId,jobIds:body.jobIds,journal:body.journal});
    // Import journal first; refusal must not replace the current project.
    if (body.journal?.transactions?.length) await this.session.restore(body.journal);
    this.clearPreview(); this.package=body.package; this.publication=body.publication; this.seedId=body.seedId;
    this.jobIds=body.jobIds; this.recovered=true; this.exported=false; this.observation=null;
    this.project=project; this.runtimeResult=null; this.runtimeTrust=null; this.runtimeTerms.clear();
    this.runtimeSettlement=null; this.runtimeEvaluation=null; this.runtimeReuse=null;
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
      if (this.currentCycle?.missions.some(m=>m.request.plan_index===index)) {
        const retained=this.runtimeTerms.get(index);
        if (!retained) throw Error('Import and verify the signed native preposting terms before routing this executor request.');
        const terms=await this.verifyNativeTerms(this.requestFor(index),retained.seal,retained.observerKey);
        const checkpoint=terms.preposting_checkpoint;
        if ((await c.read('eth_getBlockByNumber',['0x'+BigInt(checkpoint.number).toString(16),false]))?.hash!==checkpoint.hash) throw Error('The native preposting checkpoint changed. Reconcile before routing.');
      }
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
        const published=await this.storage.retrieveBytes(input.uri,undefined,2000000);
        const deliveredHash=input.hashAlgorithm==='keccak256'?(await resultCommitments(published.bytes)).keccak256:published.byteHash;
        if (input.hashAlgorithm && !['sha256','keccak256'].includes(input.hashAlgorithm)) throw Error('Unsupported result commitment domain.');
        if (deliveredHash!==input.result)
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
