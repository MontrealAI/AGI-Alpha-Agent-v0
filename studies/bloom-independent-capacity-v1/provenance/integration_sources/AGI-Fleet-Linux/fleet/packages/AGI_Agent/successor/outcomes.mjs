import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {canonical,parseStrict,fail,keys,isHash} from './vendor/manager/site/assets/successor/safe.mjs';
const digest=value=>createHash('sha256').update(canonical(value)).digest('hex');
const stages=['setup','preparation','authorization','monitoring','review','repair','support','recovery'];
const actors=['operator','reviewer','support','founder','engineer','unspecified'];
const optionalKeys=(value,required,optional,code)=>keys(value,[...required,...optional.filter(k=>Object.hasOwn(value,k))],code);
function validate(event){
  keys(event,['attempt','type','at','evidenceSha256','data'],'OUTCOME_FIELDS');fail(isHash(event.attempt)&&isHash(event.evidenceSha256)&&Number.isSafeInteger(event.at)&&event.at>=0,'OUTCOME_IDENTITY');
  const d=event.data;
  if(event.type==='attempt'){
    keys(d,['state','projectSha256','method','inputHashes','outputHashes','runtimeSha256'],'OUTCOME_ATTEMPT');
    fail(['reserved','dispatched','blocked-or-uncertain','paused','stopped','abandoned','completed'].includes(d.state)&&isHash(d.projectSha256)&&typeof d.method==='string'&&d.method.length<=120,'OUTCOME_ATTEMPT');
    fail([d.inputHashes,d.outputHashes].every(list=>Array.isArray(list)&&list.length<=40&&list.every(isHash))&&(d.runtimeSha256===null||isHash(d.runtimeSha256)),'OUTCOME_ATTEMPT');
  }else if(event.type==='cost'){
    keys(d,['id','category','basis','currency','amountMicros','billingReferenceSha256'],'OUTCOME_COST');
    fail(typeof d.id==='string'&&d.id.length>0&&d.id.length<=100&&['provider','compute','review','setup','support'].includes(d.category)&&['estimated','metered','invoiced','subscription-allocated','unknown'].includes(d.basis)&&/^[A-Z]{3,6}$/.test(d.currency),'OUTCOME_COST');
    fail(d.basis==='unknown'?d.amountMicros===null:typeof d.amountMicros==='string'&&/^(0|[1-9]\d{0,24})$/.test(d.amountMicros),'OUTCOME_COST');
    fail(d.billingReferenceSha256===null||isHash(d.billingReferenceSha256),'OUTCOME_COST');
  }else if(event.type==='human-time'){
    optionalKeys(d,['stage','activeSeconds','waitingSeconds','measurement'],['actor'],'OUTCOME_TIME');fail(d.actor===undefined||actors.includes(d.actor),'OUTCOME_TIME');fail(stages.includes(d.stage)&&['observed','operator-reported'].includes(d.measurement)&&[d.activeSeconds,d.waitingSeconds].every(n=>Number.isSafeInteger(n)&&n>=0&&n<=604800),'OUTCOME_TIME');
  }else if(event.type==='review'){
    keys(d,['verdict','control','deliverySha256','eligibilityEvidenceSha256'],'OUTCOME_REVIEW');
    fail(['accepted','rejected','abstained'].includes(d.verdict)&&['internal','unverified','externally-attested'].includes(d.control)&&isHash(d.deliverySha256)&&(d.eligibilityEvidenceSha256===null||isHash(d.eligibilityEvidenceSha256)),'OUTCOME_REVIEW');
    fail(d.control!=='externally-attested'||isHash(d.eligibilityEvidenceSha256),'OUTCOME_REVIEW');
  }else if(event.type==='funnel'){
    keys(d,['taskSha256','stage','family','role','attemptOrdinal','repeatOfTaskSha256'],'OUTCOME_FUNNEL');
    fail(isHash(d.taskSha256)&&['offered','admissible','attempted','repaired','rejected','abandoned','repeated'].includes(d.stage)&&['data-reconciliation','website','repository','custom','not-recorded'].includes(d.family)&&['agent','node','manual'].includes(d.role)&&Number.isSafeInteger(d.attemptOrdinal)&&d.attemptOrdinal>=1&&d.attemptOrdinal<=10000&&(d.repeatOfTaskSha256===null||isHash(d.repeatOfTaskSha256)),'OUTCOME_FUNNEL');
    fail(d.stage!=='repeated'||isHash(d.repeatOfTaskSha256),'OUTCOME_FUNNEL');
  }else if(event.type==='eligibility-audit'){
    keys(d,['verdict','reviewEvidenceSha256','auditEvidenceSha256'],'OUTCOME_AUDIT');fail(['eligible','ineligible'].includes(d.verdict)&&isHash(d.reviewEvidenceSha256)&&isHash(d.auditEvidenceSha256),'OUTCOME_AUDIT');
  }else fail(false,'OUTCOME_TYPE');
}
export function verifyLedger(records){
  fail(Array.isArray(records)&&records.length<=10000,'OUTCOME_LIMIT');const charges=new Set(),expenses=new Map();
  for(const [i,r] of records.entries()){
    keys(r,['sequence','previous','event','sha256'],'OUTCOME_RECORD');const {sha256,...body}=r;
    fail(r.sequence===i&&r.previous===(i?records[i-1].sha256:null)&&sha256===digest(body),'OUTCOME_CHANGED');validate(r.event);
    if(r.event.type==='cost'){const d=r.event.data,id=r.event.attempt+':'+d.id,basis=id+':'+d.basis;fail(!charges.has(basis),'OUTCOME_DUPLICATE_COST');charges.add(basis);const scope=d.category+':'+d.currency;fail(!expenses.has(id)||expenses.get(id)===scope,'OUTCOME_EXPENSE_CHANGED');expenses.set(id,scope);}
  }return records;
}
export class OutcomeLedger{
  constructor(dir){this.dir=dir;this.file=path.join(dir,'attempts.jsonl');if(!fs.existsSync(dir))fs.mkdirSync(dir,{mode:0o700});this.read();}
  read(){
    const s=fs.lstatSync(this.dir);fail(s.isDirectory()&&!s.isSymbolicLink()&&!(s.mode&0o077)&&(process.getuid===undefined||s.uid===process.getuid()),'OUTCOME_STORE_UNSAFE');
    if(!fs.existsSync(this.file))return [];
    const fd=fs.openSync(this.file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);try{const s=fs.fstatSync(fd);fail(s.isFile()&&s.nlink===1&&!(s.mode&0o077)&&s.size<8000000&&(process.getuid===undefined||s.uid===process.getuid()),'OUTCOME_STORE_UNSAFE');const raw=fs.readFileSync(fd,'utf8');fail(!raw||raw.endsWith('\n'),'OUTCOME_TORN');return verifyLedger(raw.trim()?raw.trim().split('\n').map(line=>parseStrict(line,20000)):[]);}finally{fs.closeSync(fd);}
  }
  append(event){
    validate(event);const lock=path.join(this.dir,'append.lock'),lockfd=fs.openSync(lock,'wx',0o600);
    try{const records=this.read(),body={sequence:records.length,previous:records.at(-1)?.sha256??null,event},record={...body,sha256:digest(body)};verifyLedger([...records,record]);const raw=canonical(record)+'\n';fail(Buffer.byteLength(raw)+records.reduce((n,r)=>n+Buffer.byteLength(canonical(r))+1,0)<8000000,'OUTCOME_LIMIT');
      const fd=fs.openSync(this.file,fs.constants.O_CREAT|fs.constants.O_WRONLY|fs.constants.O_APPEND|fs.constants.O_NOFOLLOW,0o600);try{fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}return record;
    }finally{fs.closeSync(lockfd);fs.unlinkSync(lock);}
  }
}
// Portable attempt history is re-chained locally. It contains neither other
// attempts nor their global predecessor links, and grants no execution authority.
export function exportAttemptObservations(records,attempt){
  verifyLedger(records);fail(isHash(attempt),'OUTCOME_IDENTITY');const selected=[];
  for(const {event} of records)if(event.attempt===attempt){const body={sequence:selected.length,previous:selected.at(-1)?.sha256??null,event};selected.push({...body,sha256:digest(body)});}
  return verifyLedger(selected);
}
export function summarizeOutcomes(records){
  verifyLedger(records);const attempts=new Set(),accepted=new Set(),costs={},time={},actorTime={},expenses=new Map(),latestAttempts=new Map(),taskMetadata=new Map(),repairedAttempts=new Set(),reviews=new Map(),audits=new Map();
  const counts=Object.fromEntries(['offered','admissible','attempted','firstPassAccepted','repaired','rejected','abandoned','repeated'].map(k=>[k,new Set()])),reviewAssertions={internal:new Set(),unverified:new Set(),'externally-attested':new Set()};
  for(const {event:e} of records){const d=e.data;
    if(e.type==='attempt'){attempts.add(e.attempt);latestAttempts.set(e.attempt,d.state);}
    if(e.type==='funnel'&&d.role!=='node'){counts[d.stage].add(d.taskSha256);if(!taskMetadata.has(e.attempt)||d.stage==='attempted')taskMetadata.set(e.attempt,d);if(d.stage==='repaired')repairedAttempts.add(e.attempt);if(d.stage==='attempted')attempts.add(e.attempt);}
    if(e.type==='review')reviews.set(e.attempt,e);
    if(e.type==='eligibility-audit')audits.set(d.reviewEvidenceSha256,d);
    if(e.type==='cost'){
      const key=e.attempt+':'+d.id,prior=expenses.get(key)??[];prior.push({...d,attempt:e.attempt});expenses.set(key,prior);
      if(d.basis!=='unknown'){const k=d.currency+':'+d.basis;costs[k]=(BigInt(costs[k]??'0')+BigInt(d.amountMicros)).toString();}
    }
    if(e.type==='human-time'){
      for(const [map,key] of [[time,d.stage+':'+d.measurement],[actorTime,(d.actor??'unspecified')+':'+d.stage+':'+d.measurement]]){const row=map[key]??={activeSeconds:0,waitingSeconds:0};row.activeSeconds+=d.activeSeconds;row.waitingSeconds+=d.waitingSeconds;}
    }
  }
  const unknown=[],selectedCosts={},selectedCostBases={},rank={'unknown':0,'estimated':1,'subscription-allocated':2,'metered':3,'invoiced':4};
  for(const entries of expenses.values()){
    const selected=entries.reduce((a,b)=>rank[a.basis]>=rank[b.basis]?a:b);
    if(selected.basis==='unknown')unknown.push({attempt:selected.attempt,id:selected.id,category:selected.category,currency:selected.currency});
    else{selectedCosts[selected.currency]=(BigInt(selectedCosts[selected.currency]??'0')+BigInt(selected.amountMicros)).toString();selectedCostBases[selected.basis]=(selectedCostBases[selected.basis]??0)+1;}
  }
  let eligibilityAuditAcceptedAssertions=0,unclassifiedAcceptedAssertions=0;
  for(const [attempt,e] of reviews){const d=e.data,meta=taskMetadata.get(attempt);if(d.verdict==='accepted'){
    reviewAssertions[d.control].add(attempt);if(d.control==='externally-attested')accepted.add(attempt);
    if(meta&&meta.role!=='node'&&meta.attemptOrdinal===1&&!repairedAttempts.has(attempt)&&meta.repeatOfTaskSha256===null)counts.firstPassAccepted.add(meta.taskSha256);else if(!meta)unclassifiedAcceptedAssertions++;
    if(d.control==='externally-attested'&&audits.get(e.evidenceSha256)?.verdict==='eligible'&&audits.get(e.evidenceSha256)?.auditEvidenceSha256===d.eligibilityEvidenceSha256)eligibilityAuditAcceptedAssertions++;
  }else if(d.verdict==='rejected'&&meta&&meta.role!=='node')counts.rejected.add(meta.taskSha256);}
  for(const [attempt,state] of latestAttempts){const meta=taskMetadata.get(attempt);if(state==='abandoned'&&meta&&meta.role!=='node')counts.abandoned.add(meta.taskSha256);}
  return {attempts:attempts.size,externallyAttestedAccepted:accepted.size,funnel:Object.fromEntries(Object.entries(counts).map(([k,v])=>[k,v.size])),
    acceptanceAssertionsByControl:Object.fromEntries(Object.entries(reviewAssertions).map(([k,v])=>[k,v.size])),eligibilityAuditAcceptedAssertions,unclassifiedAcceptedAssertions,independentlyAcceptedUsefulOutcomes:null,
    funnelScope:'Distinct task hashes with explicit observations; first-pass counts review assertions, not independently accepted useful jobs. Node review work is excluded from task counts. Repetitions remain separate.',
    costMicrosByCurrencyAndBasis:costs,selectedExpenseMicrosByCurrency:selectedCosts,selectedExpenseBasisCounts:selectedCostBases,
    costSelection:'One basis per attempt/expense ID: invoiced, then metered, subscription-allocated, estimated. Reuse an ID for the same expense; different IDs are distinct charges. Totals can mix bases and exclude unknowns; completeness is not established.',
    humanTimeByStage:time,humanTimeByActorAndStage:actorTime,unknownCosts:unknown,costPerIndependentlyAcceptedOutcome:null,activeMinutesPerIndependentlyAcceptedOutcome:null,
    independentControl:'Eligibility audit records are assertions with external evidence hashes; verify the actual audit and reviewer control before reporting independently accepted useful outcomes.',economics:'NOT_EVALUATED',humanEffort:'NOT_EVALUATED',productionQualified:false};
}
