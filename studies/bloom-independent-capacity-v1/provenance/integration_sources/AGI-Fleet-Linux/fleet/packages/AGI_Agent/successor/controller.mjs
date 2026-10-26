import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {OutcomeLedger,summarizeOutcomes,exportAttemptObservations} from './outcomes.mjs';
import {fail,keys,canonical,parseStrict,sha256} from './vendor/manager/site/assets/successor/safe.mjs';
import {compileRequest,inspectRequest,computer,checkReturnedWork} from './project.mjs';

// This adapter owns no wallet, provider credential, local service or alternate worker.
// All work goes through the installed Controller -> Studio -> Companion -> ComputeWorker.
export class SuccessorController {
  constructor(controller,role,studioAPI) {
    this.c=controller;this.role=role;this.api=studioAPI;this.tickets=new Map();this.authorizationGeneration=0;
    this.dir=path.join(controller.home,'successor-execution');this.problem=null;this.records=[];
    try {
      if(!fs.existsSync(this.dir))fs.mkdirSync(this.dir,{mode:0o700});
      const stat=fs.lstatSync(this.dir);fail(stat.isDirectory()&&!stat.isSymbolicLink()&&!(stat.mode&0o077),'FLEET_STORE_UNSAFE');
      this.outcomes=new OutcomeLedger(path.join(controller.home,'successor-outcomes'));
      this.records=this.storedRecords();
    } catch(error){this.problem=error.code||error.message;}
  }
  read(name){const fd=fs.openSync(path.join(this.dir,name),fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);try{const s=fs.fstatSync(fd);fail(s.isFile()&&s.nlink===1&&s.size<6500000,'FLEET_HISTORY_DAMAGED');return parseStrict(fs.readFileSync(fd,'utf8'),6500000);}finally{fs.closeSync(fd);}}
  storedRecords(){
    const names=fs.readdirSync(this.dir);fail(names.length<=100,'FLEET_HISTORY_FULL');
    return names.map(name=>{fail(/^[a-f0-9]{64}\.json$/.test(name),'FLEET_HISTORY_DAMAGED');const record=this.read(name);fail(record.key+'.json'===name&&record.role===this.role,'FLEET_HISTORY_DAMAGED');return record;});
  }
  taskIdentity(record){return record.request?.plan.missionSha256??record.taskSha256??record.specSha256;}
  nextOrdinal(taskSha256,stored=this.storedRecords()){
    const prior=stored.filter(r=>this.taskIdentity(r)===taskSha256),journal=this.outcomes.read().filter(r=>r.event.type==='funnel'&&r.event.data.stage==='attempted'&&r.event.data.taskSha256===taskSha256&&r.event.data.role===this.role);
    return Math.max(prior.length,...prior.map(r=>r.attemptOrdinal??0),...journal.map(r=>r.event.data.attemptOrdinal))+1;
  }
  reserve(record,family){
    const lock=path.join(this.c.home,'successor-attempt.lock');let fd;
    try{fd=fs.openSync(lock,'wx',0o600);}catch(error){if(error.code==='EEXIST')fail(false,'FLEET_ATTEMPT_LOCKED');throw error;}
    try{
      // Re-read durable evidence inside the exclusive reservation lock. A
      // changed deadline/budget/runtime is another attempt on the same task.
      const stored=this.storedRecords();fail(stored.length<100,'FLEET_HISTORY_FULL');fail(!stored.some(r=>r.key===record.key),'FLEET_ALREADY_ATTEMPTED');
      record.taskSha256=this.taskIdentity(record);record.attemptOrdinal=this.nextOrdinal(record.taskSha256,stored);record.repeatOfTaskSha256=record.attemptOrdinal>1?record.taskSha256:null;
      this.persist(record,true);this.records=[...stored,record];this.observe(record,'reserved');
      this.funnel(record.key,record.request,'attempted',family,record);
      if(record.attemptOrdinal>1)this.funnel(record.key,record.request,'repeated',family,record);
      this.outcomes.append({attempt:record.key,type:'cost',at:record.at,evidenceSha256:record.specSha256,data:{id:'provider-billing-unavailable',category:'provider',basis:'unknown',currency:'USD',amountMicros:null,billingReferenceSha256:null}});
    }finally{fs.closeSync(fd);fs.unlinkSync(lock);}
  }
  persist(record,exclusive=false){
    const destination=path.join(this.dir,record.key+'.json'),temporary=destination+'.'+crypto.randomUUID();
    const raw=canonical(record)+'\n';fail(Buffer.byteLength(raw)<6500000,'FLEET_HISTORY_LIMIT');
    if(exclusive){const fd=fs.openSync(destination,'wx',0o600);try{fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
    else {const fd=fs.openSync(temporary,'wx',0o600);try{fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(temporary,destination);}
    const fd=fs.openSync(this.dir,'r');try{fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
  }
  async health(spec=null){
    fail(!this.problem,'FLEET_HISTORY_DAMAGED');fail(this.c.vault.unlocked,'NODE_LOCKED');
    const companion=this.c.companion;
    fail(companion.config.enabled&&companion.config.mode==='workstation','COMPANION_WORKSTATION_REQUIRED');
    const h=await companion.readComputeHealth(companion.getToken(),AbortSignal.timeout(5000));
    fail(h.gatewayReady&&!h.stopped&&h.policyHash===companion.state.computePolicy,'FLEET_COMPUTE_NOT_READY');
    fail(h.runtime&&h.runtime.scope==='isolated-public','FLEET_RUNTIME_UNAVAILABLE');
    const role=this.role==='agent'?'agent':'reviewer';
    if(spec)computer.checkRuntime(spec,h.runtime,role,Math.floor(companion.now()/1000));
    return {schema:'agi-fleet/successor-runtime-observation/v1',role,runtime:h.runtime,runtimeSha256:computer.digest(h.runtime),policyHash:h.policyHash,
      observedAt:companion.now(),expiresAt:companion.now()+60000,qualification:h.qualification,authority:'none'};
  }
  status(){
    const unlocked=this.c.vault.unlocked,records=unlocked&&this.outcomes?this.outcomes.read():[];
    return {outcomeSummary:unlocked&&this.outcomes?summarizeOutcomes(records):null,role:this.role,problem:this.problem,studio:this.c.studio.status(),
      runs:unlocked?this.records.map(({request,...r})=>({...r,projectView:r.projectView??{goal:request?.plan.goal??null,inputs:request?.plan.immutableInputs.map(f=>f.name)??[],outputs:[],budget:null},outcomeSummary:summarizeOutcomes(exportAttemptObservations(records,r.key))})):[],authority:'none',productionQualified:false};
  }
  funnel(key,request,stage,family='not-recorded',reservation=null){
    const taskSha256=reservation?.taskSha256??request?.plan.missionSha256??key,attemptOrdinal=reservation?.attemptOrdinal??this.nextOrdinal(taskSha256);
    this.outcomes.append({attempt:key,type:'funnel',at:this.c.companion.now(),evidenceSha256:key,data:{taskSha256,stage,family,role:this.role,attemptOrdinal,repeatOfTaskSha256:reservation?.repeatOfTaskSha256??(attemptOrdinal>1?taskSha256:null)}});
  }
  async prepare(input,principal){
    fail(typeof principal==='string'&&principal.length>0,'FLEET_SESSION_REQUIRED');
    fail(this.records.length<100,'FLEET_HISTORY_FULL');this.c.requireStopped();
    const authorizationGeneration=this.authorizationGeneration;
    let compiled,request=null,studioInput,family='not-recorded';
    if(this.role==='agent'){
      keys(input,['request','context'],'FLEET_PREPARE_FIELDS');
      const result=await compileRequest(input.request,typeof input.context==='string'?parseStrict(input.context,100000):input.context,Math.floor(this.c.companion.now()/1000));
      request=result.request;compiled=result.compiled;family={analyst:'data-reconciliation',website:'website'}[result.state.mission.kind]??'custom';this.api.studioSpec(compiled.spec);studioInput={specification:compiled.spec};
    }else{
      keys(input,['handoff'],'FLEET_PREPARE_FIELDS');let raw=typeof input.handoff==='string'?parseStrict(input.handoff,128*1024*1024):input.handoff;const h=this.api.validateHandoff(raw.handoff??raw);
      fail(h.specification.profile==='computer-work/v2','FLEET_V2_REQUIRED');compiled={spec:h.specification,specSha256:h.specHash};studioInput={handoff:h};
    }
    const key=await sha256({role:this.role,spec:compiled.spec,delivery:studioInput.handoff?.deliveryHash??null});
    fail(authorizationGeneration===this.authorizationGeneration,'FLEET_AUTHORIZATION_REVOKED');
    this.funnel(key,request,'offered',family);
    const observation=await this.health(compiled.spec);
    fail(authorizationGeneration===this.authorizationGeneration,'FLEET_AUTHORIZATION_REVOKED');
    this.funnel(key,request,'admissible',family);
    fail(!this.records.some(r=>r.key===key),'FLEET_ALREADY_ATTEMPTED');
    const ticket=crypto.randomBytes(32).toString('hex'),expiresAt=Math.min(observation.expiresAt,compiled.spec.deadline*1000);
    this.tickets.set(ticket,{authorizationGeneration,principal,expiresAt,compiled,request,studioInput,key,family,scope:this.c.studio.scopeHash(),observation});
    while(this.tickets.size>8)this.tickets.delete(this.tickets.keys().next().value);
    return {ticket,expiresAt,key,specification:compiled.spec,specificationSha256:compiled.specSha256,observation,
      action:this.role==='agent'?'Create and self-check the exact public work':'Review the exact delivered bytes',
      declaredTaskBudget:compiled.spec.budget,budgetEnforcement:'Existing compute call and duration limits; USDC amounts are planning bounds, not measured provider billing.',financialAction:'none',independentControl:'UNVERIFIED',confirmationRequired:true};
  }
  async execute(input,principal){
    keys(input,['ticket','key','confirm'],'FLEET_EXECUTE_FIELDS');fail(input.confirm===true,'FLEET_CONFIRM_REQUIRED');
    const grant=this.tickets.get(input.ticket);this.tickets.delete(input.ticket);
    const now=this.c.companion.now();
    fail(grant&&grant.principal===principal&&grant.key===input.key,'FLEET_TICKET_INVALID');
    fail(now>=grant.observation.observedAt&&now<grant.expiresAt,'FLEET_TICKET_EXPIRED');
    fail(grant.scope===this.c.studio.scopeHash(),'FLEET_SCOPE_CHANGED');
    fail(grant.authorizationGeneration===this.authorizationGeneration,'FLEET_AUTHORIZATION_REVOKED');
    const fresh=await this.health(grant.compiled.spec);
    fail(grant.authorizationGeneration===this.authorizationGeneration,'FLEET_AUTHORIZATION_REVOKED');
    fail(grant.scope===this.c.studio.scopeHash(),'FLEET_SCOPE_CHANGED');
    fail(fresh.runtimeSha256===grant.observation.runtimeSha256&&fresh.policyHash===grant.observation.policyHash,'FLEET_RUNTIME_CHANGED');
    const record={schema:'agi-fleet/successor-attempt/v1',key:grant.key,role:this.role,status:'reserved',at:now,run:null,
      specSha256:grant.compiled.specSha256,request:grant.request,observation:fresh,
      projectView:{goal:grant.compiled.spec.prompt,inputs:grant.compiled.spec.inputs.map(f=>f.name),outputs:grant.compiled.spec.outputs.map(f=>f.name),budget:grant.compiled.spec.budget,deadline:grant.compiled.spec.deadline,family:grant.family}};
    this.reserve(record,grant.family);
    try{const run=this.c.studio.start(grant.studioInput);record.run=run.id;record.status='dispatched';this.persist(record);this.observe(record,'dispatched');return {key:record.key,run};}
    catch(error){record.status='blocked-or-uncertain';this.persist(record);this.observe(record,'blocked-or-uncertain');throw error;}
  }
  observe(record,state,outputHashes=[]){this.outcomes.append({attempt:record.key,type:'attempt',at:this.c.companion.now(),evidenceSha256:record.specSha256,data:{state,projectSha256:record.request?.plan.missionSha256??record.specSha256,method:record.request?.plan.candidateSha256??'installed-node-review',inputHashes:record.request?.plan.immutableInputs.map(f=>f.sha256)??[],outputHashes,runtimeSha256:record.observation.runtimeSha256}});}
  revoke(){this.authorizationGeneration++;this.tickets.clear();return {revoked:true,runningWork:'Use Stop work to cancel the active Studio run. Safety STOP evidence is preserved.'};}
  async stop(){this.revoke();const result=await this.c.studio.cancel();for(const r of this.records.filter(r=>r.status==='dispatched')){this.observe(r,'stopped');r.status='stopped';this.persist(r);}return result;}
  async result(key,reviewReceipt=null){
    if(typeof reviewReceipt==='string'){reviewReceipt=parseStrict(reviewReceipt,1000000);reviewReceipt=reviewReceipt.receipt??reviewReceipt;}
    const r=this.records.find(r=>r.key===key);fail(r&&r.run,'FLEET_RUN_UNKNOWN');
    const receipt=this.c.studio.export(r.run,'receipt'),handoff=this.c.studio.export(r.run,'handoff');
    fail(handoff.specHash===r.specSha256,'FLEET_SPECIFICATION_CHANGED');
    this.observe(r,'completed',[handoff.deliveryHash]);
    const observations=exportAttemptObservations(this.outcomes.read(),key);
    if(this.role==='node')return {handoff,receipt,outcomeObservations:observations};
    if(reviewReceipt===null)return {request:r.request,handoff,receipt,outcomeObservations:observations};
    const result=await checkReturnedWork(r.request,handoff,reviewReceipt,this.api);
    this.outcomes.append({attempt:r.key,type:'review',at:this.c.companion.now(),evidenceSha256:await sha256(reviewReceipt),data:{verdict:result.outcome==='accepted'?'accepted':'rejected',control:'unverified',deliverySha256:handoff.deliveryHash,eligibilityEvidenceSha256:null}});
    return {...result,outcomeObservations:exportAttemptObservations(this.outcomes.read(),key)};
  }
}
