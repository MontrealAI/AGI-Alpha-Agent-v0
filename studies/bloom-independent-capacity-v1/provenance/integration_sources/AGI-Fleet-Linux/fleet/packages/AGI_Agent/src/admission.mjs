import { QualificationService } from './admission-core/economics/qualification-service.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { parseUnits } from 'ethers';
import core from './admission-core/economics/admission.cjs';
import units from './admission-core/lib/usdc.js';
import { readAdmissionState } from './admission-core/economics/admission-state.mjs';
import { readClosureState } from './admission-core/economics/closure-state.mjs';
import { sha256 } from './util.mjs';
import {verifyAgentWindows,digest as reviewTimeDigest,validatePolicy as validateReviewTimePolicy} from '../workforce/review-time.mjs';
const {checkNewWork:checkAdmission,digest,validatePolicy}=core, {parseUSDC,formatUSDC}=units;
const cash=x=>BigInt(parseUSDC(x));
const ensure=(x,m)=>{if(!x)throw new Error('ADMISSION_'+m);};
function readFile(file) {const s=fs.lstatSync(file);ensure(s.isFile()&&!s.isSymbolicLink()&&s.size<=1048576,'FILE_LIMIT');return fs.readFileSync(file);}
export class Admission {
 constructor(c,chain,store,{readState=readAdmissionState,readClosure=readClosureState}={}) {Object.assign(this,{c,chain,store,readState,readClosure});this.role=c.agent?'agent':'reviewer';this.wallet=(c.agent??c.validator).toLowerCase();this.seals=new Map();this.service=new QualificationService();}
 init() {this.store.db.exec('CREATE TABLE IF NOT EXISTS admission_reservations(job TEXT PRIMARY KEY, epoch TEXT NOT NULL, policy TEXT NOT NULL, packet TEXT NOT NULL, exposure TEXT NOT NULL, cost TEXT NOT NULL, gas TEXT NOT NULL, closed INTEGER NOT NULL DEFAULT 0)');this.store.db.exec('CREATE TABLE IF NOT EXISTS admission_attempts(job TEXT PRIMARY KEY,attempts INTEGER NOT NULL)');}
 async state(job,confirmations=0) {return this.readState({primary:this.chain.provider,secondary:this.chain.provider.witness,chainId:this.c.chainId,manager:this.c.manager,wallet:this.wallet,jobId:String(job),confirmations});}
 async check(job,specHash=null,options={}) {
  try {return await this.service.run('admit:'+job, signal=>this.checkNow(job,specHash,{...options,signal}));}
  finally {this.store.set('qualificationService',this.service.snapshot());}
 }
 async checkNow(job,specHash=null,{gasBudget=0n,rebroadcast=false,commitment=null,signal}={}) {
  // Local chain fixtures have no native USDC or production admission authority.
  if(this.c.chainId===31337)return {decision:'LOCAL_SIMULATION_ONLY'};
  try {
   ensure(['1','11155111'].includes(String(this.c.chainId)),'NATIVE_USDC_CHAIN');ensure(/^(0|[1-9][0-9]{0,77})$/.test(String(job)),'JOB_ID');this.init();
   const policy=this.store.meta('admissionPolicy');ensure(policy,'POLICY_REQUIRED');validatePolicy(policy);ensure(policy.schemaVersion===6&&policy.reviewPayment==='operator-budget','OPERATOR_BUDGET_POLICY_REQUIRED');
   ensure(this.c.chainId!==1||policy.calibration.allowedKinds.every(x=>x==='observed'),'MAINNET_OBSERVED_EVIDENCE_REQUIRED');
   const policyHash=digest(policy);ensure(policy.role===this.role&&policy.wallet===this.wallet&&policy.manager===this.c.manager.toLowerCase()&&policy.chainId===this.c.chainId,'POLICY_SCOPE');
   const file=path.join(this.c.dataDir,'admission','inbox',String(job)+'.json'), bytes=readFile(file), envelope=JSON.parse(bytes), packet=envelope.payload;
   // Verify before allowing packet-controlled filesystem paths or RPC work.
   ensure(packet&&/^[0-9a-f]{64}$/.test(packet.evidence?.reportSha256??''),'REPORT_HASH');
   const report=readFile(path.join(this.c.dataDir,'admission','evidence',packet.evidence.reportSha256+'.json'));ensure(sha256(report)===packet.evidence.reportSha256,'REPORT_CHANGED');
   const s=await this.state(job);
   ensure(s.pendingUSDC==='0','UNPAID_CLAIMS_REQUIRE_RECOVERY');
   if(!specHash) {if(this.role==='agent')specHash=this.store.work?.(job)?.spec_hash;else {const r=this.store.job(job)?.review;specHash=r?JSON.parse(r).specHash:null;}}
   ensure(typeof specHash==='string','SPEC_NOT_VERIFIED');
   if(!commitment) {
    if(this.role==='agent')commitment={action:'apply',decision:null,completionURI:null,deliverySha256:null};
    else {const r=JSON.parse(this.store.job(job)?.review??'null');ensure(r&&['approve','reject'].includes(r.decision),'REVIEW_REQUIRED');commitment={action:'vote',decision:r.decision,completionURI:r.completionURI,deliverySha256:r.deliveryHash};}
   }
   if(this.role==='reviewer')ensure(commitment.completionURI===s.completionURI,'DELIVERY_CHANGED');
   const identities=packet.identities??{},actors=packet.lifecycle?.participants??[];
   const employer=actors.find(a=>a.role==='employer'), agent=actors.find(a=>a.role==='agent');
   ensure(identities[employer?.id]?.wallet===s.employer,'EMPLOYER_CHANGED');
   ensure(s.assignedAgent==='0x'+'0'.repeat(40)||identities[agent?.id]?.wallet===s.assignedAgent,'AGENT_CHANGED');
   const timePolicy=validateReviewTimePolicy(this.store.meta('reviewTimePolicy'));
   ensure(timePolicy.chainId===this.c.chainId&&timePolicy.manager===this.c.manager.toLowerCase()&&timePolicy.employer===s.employer,'REVIEW_TIME_POLICY_SCOPE');
   const windowFile=path.join(this.c.dataDir,'admission','review-windows',String(job)+'.json'),windowBytes=readFile(windowFile),windowEvidence=JSON.parse(windowBytes);
   ensure(windowEvidence&&Object.keys(windowEvidence).sort().join('|')==='offerId|receipts','REVIEW_TIME_EVIDENCE_FIELDS');
   const reviewJob=await this.chain.snapshot(job);
   ensure(reviewJob.specURI===s.specURI&&reviewJob.buyer.toLowerCase()===s.employer,'REVIEW_TIME_CHAIN_STATE');
   const windows=verifyAgentWindows({policy:timePolicy,payload:packet,offerId:windowEvidence.offerId,receipts:windowEvidence.receipts,job:reviewJob});
   // Do not forget old open obligations when upgrading a funded wallet.
   for(const old of this.store.ownJobs())ensure(this.store.db.prepare('SELECT job FROM admission_reservations WHERE job=? AND closed=0').get(String(old.id)),'LEGACY_OPEN_OBLIGATION');
   let rows=this.store.db.prepare('SELECT * FROM admission_reservations WHERE closed=0').all();ensure(rows.length<=100,'JOURNAL_CAPACITY');
   const closable=[];
   const finalState=await this.state(job);ensure(JSON.stringify(finalState.terms)===JSON.stringify(s.terms)&&finalState.specURI===s.specURI&&finalState.employer===s.employer&&finalState.assignedAgent===s.assignedAgent&&finalState.completionURI===s.completionURI&&!finalState.completed&&!finalState.expired&&finalState.pendingUSDC==='0','STATE_CHANGED');
   const now=Math.floor(Date.now()/1000), observed={chainId:this.c.chainId,manager:this.c.manager.toLowerCase(),wallet:this.wallet,jobId:String(job),specURI:s.specURI,specSha256:specHash,terms:s.terms,observedAt:s.block.timestamp,commitment};
   ensure(!s.completed&&!s.expired,'JOB_TERMINAL');
   // A slow portfolio scan must not turn an old read into a fresh observation.
   ensure(now-s.block.timestamp<=120,'STALE_STATE');
   const nativeBalance=await this.chain.provider.getBalance(this.wallet);
   ensure(!signal?.aborted,'QUALIFICATION_DEADLINE');
   const result=this.store.transaction(()=>{
    ensure(digest(this.store.meta('admissionPolicy'))===policyHash,'POLICY_CHANGED');
    for(const id of closable)this.store.db.prepare('UPDATE admission_reservations SET closed=1 WHERE job=?').run(id);
    rows=this.store.db.prepare('SELECT * FROM admission_reservations WHERE closed=0').all();
    const prior=this.store.db.prepare('SELECT * FROM admission_reservations WHERE job=?').get(String(job));
    ensure(!prior||(!prior.closed&&prior.policy===policyHash),'RESERVATION_SCOPE');
    const others=rows.filter(x=>x.job!==String(job));
    const charged=this.store.db.prepare('SELECT cost FROM admission_reservations WHERE epoch=?').all(policy.epoch).reduce((n,x)=>n+BigInt(x.cost),0n);
    const portfolio={openExposureUSDC:formatUSDC(others.reduce((n,x)=>n+BigInt(x.exposure),0n)),epochCostUSDC:formatUSDC(charged-(prior?BigInt(prior.cost):0n)),openJobs:others.length};
    const r=checkAdmission({policy,envelope,observed,portfolio,evidenceReport:report.toString(),now});
    if(prior)ensure(cash(r.reserveExposureUSDC)>=BigInt(prior.exposure)&&cash(r.reserveCostUSDC)>=BigInt(prior.cost),'RESERVATION_CANNOT_SHRINK');
    const nativeReserved=others.reduce((n,row)=>{const used=this.store.db.prepare('SELECT gas_budget FROM txs WHERE job=?').all(row.job).reduce((v,t)=>v+BigInt(t.gas_budget),0n);return n+(BigInt(row.gas)>used?BigInt(row.gas)-used:0n);},0n);
    const txs=this.store.db.prepare('SELECT gas_budget,hash FROM txs WHERE job=?').all(String(job));
    const spent=txs.reduce((n,t)=>n+BigInt(t.gas_budget),0n);
    const headroom=parseUnits(this.c.limits.maxTxETH,18)*2n;
    ensure(spent+(rebroadcast?0n:gasBudget)+headroom<=BigInt(r.gasBudgetWei),'JOB_GAS_BUDGET');
    ensure(nativeBalance>=nativeReserved+BigInt(r.gasBudgetWei)-spent,'AGGREGATE_ETH_RESERVE');
    this.store.db.prepare('INSERT INTO admission_reservations(job,epoch,policy,packet,exposure,cost,gas) VALUES(?,?,?,?,?,?,?) ON CONFLICT(job) DO UPDATE SET packet=excluded.packet,exposure=excluded.exposure,cost=excluded.cost,gas=excluded.gas').run(String(job),policy.epoch,policyHash,r.packetDigest,cash(r.reserveExposureUSDC).toString(),cash(r.reserveCostUSDC).toString(),r.gasBudgetWei);
    return r;
   });
   ensure(sha256(readFile(file))===sha256(bytes)&&sha256(readFile(windowFile))===sha256(windowBytes),'PACKET_CHANGED');
   ensure(Math.floor(Date.now()/1000)<result.expiresAt&&Math.floor(Date.now()/1000)-s.block.timestamp<=120,'PACKET_OR_STATE_EXPIRED');
   ensure(!signal?.aborted,'QUALIFICATION_DEADLINE');
   this.seals.set(String(job),{file,bytesHash:sha256(bytes),policyHash,windowFile,windowHash:sha256(windowBytes),reviewTimePolicyHash:reviewTimeDigest(timePolicy),reviewStart:Math.min(...windows.map(x=>x.start)),agentSeconds:timePolicy.agentSeconds,observedAt:s.block.timestamp,expiresAt:result.expiresAt,commitment:result.commitment,maxPreparationAttempts:result.maxPreparationAttempts});
   return result;
  } catch(e) {if(String(e.message).startsWith('ADMISSION_'))throw e;throw new Error('ADMISSION_DENIED: '+String(e.message).slice(0,300));}
 }
 assertCurrent({kind,job,bond='0',decision=null}) {
  if(this.c.chainId===31337||!(kind==='apply'||kind==='vote'||(kind==='approve'&&BigInt(bond)>0n)))return;
  const s=this.seals.get(String(job));ensure(s&&Math.floor(Date.now()/1000)<s.expiresAt&&Math.floor(Date.now()/1000)-s.observedAt<=120,'NO_FRESH_SIGNING_SEAL');
  if(kind==='vote')ensure(decision===s.commitment.decision,'VOTE_CHANGED');
  ensure(digest(this.store.meta('admissionPolicy'))===s.policyHash&&sha256(readFile(s.file))===s.bytesHash,'AUTHORITY_CHANGED_BEFORE_SIGNING');
  ensure(reviewTimeDigest(this.store.meta('reviewTimePolicy'))===s.reviewTimePolicyHash&&sha256(readFile(s.windowFile))===s.windowHash&&Math.floor(Date.now()/1000)+s.agentSeconds<=s.reviewStart,'REVIEW_TIME_CHANGED_BEFORE_SIGNING');
 }
 async beforeCommit({kind,job,bond='0',gasBudget=0n,rebroadcast=false,decision=null}) {
  if(kind==='apply'||kind==='vote'||(kind==='approve'&&BigInt(bond)>0n)) {
   const r=await this.check(job,null,{gasBudget,rebroadcast});
   if(kind==='vote'&&this.c.chainId!==31337)ensure(r.commitment.decision===decision,'VOTE_CHANGED');return r;
  }
 }
 consumePreparation(job) {
  if(this.c.chainId===31337)return;
  const s=this.seals.get(String(job));ensure(s,'PREPARATION_SEAL_REQUIRED');
  this.assertCurrent({kind:this.role==='agent'?'apply':'approve',job,bond:'1'});
  this.store.transaction(()=>{const n=this.store.db.prepare('SELECT attempts FROM admission_attempts WHERE job=?').get(String(job))?.attempts??0;
   ensure(n<s.maxPreparationAttempts,'PREPARATION_ATTEMPTS_EXHAUSTED');
   this.store.db.prepare('INSERT INTO admission_attempts VALUES(?,?) ON CONFLICT(job) DO UPDATE SET attempts=excluded.attempts').run(String(job),n+1);
  });
 }
 async reconcile(options={}) {
  try{return await this.service.run('reconcile',signal=>this.reconcileNow({...options,signal}),{priority:'recovery'});}
  finally{this.store.set('qualificationService',this.service.snapshot());}
 }
 async reconcileNow({limit=5,signal}={}) {
  if(this.c.chainId===31337)return {closed:0};
  ensure(Number.isInteger(limit)&&limit>=1&&limit<=20,'RECONCILE_LIMIT');this.init();
  const rows=this.store.db.prepare('SELECT * FROM admission_reservations WHERE closed=0 ORDER BY job').all();
  const start=this.store.meta('admissionReconcileCursor',0)%Math.max(1,rows.length);let closed=0;
  for(let i=0;i<Math.min(limit,rows.length);i++) {
   const row=rows[(start+i)%rows.length];
   try {
    if(this.store.pending())break;
    const ref=this.store.meta('admissionTerminal:'+row.job);let proof;
    if(ref) proof=await this.readClosure({primary:this.chain.provider,secondary:this.chain.provider.witness,chainId:this.c.chainId,manager:this.c.manager,wallet:this.wallet,jobId:row.job,transactionHash:ref.transactionHash,confirmations:Math.max(64,this.c.confirmations)});
    else {
     const s=await this.state(row.job,Math.max(64,this.c.confirmations));
     const committed=this.store.db.prepare("SELECT hash FROM txs WHERE job=? AND kind IN ('apply','vote') AND (state='pending' OR status=1)").get(row.job);
     const lost=this.role==='agent'&&!committed&&s.assignedAgent!=='0x'+'0'.repeat(40)&&s.assignedAgent!==this.wallet;
     ensure(s.completed||s.expired||lost,'NOT_CLOSED');proof={...s,reason:lost?'LOST_BID':'TERMINAL'};
    }
    ensure(proof.pendingUSDC==='0','UNPAID_CLAIMS_REQUIRE_RECOVERY');
    ensure(!signal?.aborted,'QUALIFICATION_DEADLINE');
    this.store.transaction(()=>{ensure(!this.store.pending(),'TRANSACTION_PENDING');this.store.db.prepare('UPDATE admission_reservations SET closed=1 WHERE job=? AND closed=0').run(row.job);this.store.set('admissionClosure:'+row.job,proof);});closed++;
   } catch(e) {this.store.set('admissionReconcileError:'+row.job,{at:Math.floor(Date.now()/1000),code:String(e.message).slice(0,160)});}
  }
  this.store.set('admissionReconcileCursor',(start+limit)%Math.max(1,rows.length));return {closed};
 }
}
