// SPDX-License-Identifier: Apache-2.0
import {readFile,writeFile,mkdir,lstat,realpath} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createCapabilityStore} from './capability-store.mjs';
import {canonicalize} from './vendor/commitments.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const same=(a,b)=>canonicalize(a)===canonicalize(b);
const read=async p=>JSON.parse(await readFile(path.join(ROOT,p),'utf8'));
const insist=(ok,message)=>{if(!ok)throw Error(message);};
const CONFIG='identity/catalog.json',FIXTURE='identity/authority-fixtures.json';
const RECEIPT='evidence/admission-cached/catalog-admission.json',PIN='protocol/admission-pin.json';
const HELPERS=['workloads/verifier.py','workloads/workload_generator.py','identity/validate_evidence.py',
  'identity/build_catalog.py','identity/runtime_context.py','identity/study_catalog.mjs','identity/capability-store.mjs',
  'identity/vendor/authority.mjs','identity/vendor/commitments.mjs'];
const verifierPaths=['workloads/verifier.py','identity/validate_evidence.py','identity/study_catalog.mjs'];
async function file(p){const raw=await readFile(path.join(ROOT,p));return {path:p,sha256:hash(raw),bytes:raw.length};}
async function verifyFiles(entries){
  for(const entry of entries){
    const full=path.resolve(ROOT,entry.path);insist(full.startsWith(ROOT+path.sep),'BOUND_PATH_REQUIRED');
    insist((await realpath(full)).startsWith(ROOT+path.sep),'BOUND_REALPATH_REQUIRED');
    for(let at=full;at!==ROOT;at=path.dirname(at))insist(!(await lstat(at)).isSymbolicLink(),'BOUND_SYMLINK_REFUSED');
    const actual=await file(entry.path);insist(actual.sha256===entry.sha256&&(entry.bytes===undefined||actual.bytes===entry.bytes),'ADMISSION_INPUT_DRIFT:'+entry.path);
  }
}
function options(config,fixture,verifierSource,verifier,compositionVerifier){
  return {rootDirectory:ROOT,fixture,verifier,compositionVerifier,verifierSource,compositionVerifierSource:verifierSource,
    executionPolicy:{mode:'LOCAL_RESEARCH_ONLY',nativeAuthority:[],allowedSkills:config.skills.map(x=>x.id+'@'+x.version),maxRuns:1,expiresAt:9000}};
}

export async function createAdmission(){
  const started=performance.now(),cpu=process.cpuUsage(),config=await read(CONFIG),fixture=await read(FIXTURE);
  insist(config.schema==='capability-advantage-catalog/v2','CURRENT_CATALOG_REQUIRED');
  await verifyFiles([config.executionReceipt]);
  const executed=await read(config.executionReceipt.path);
  insist(executed.schema==='capability-current-implementation-validation/v1'&&executed.accepted===true&&executed.entries.length===8,
    'ACTUAL_CURRENT_EXECUTION_REQUIRED');
  insist(executed.dispatch_entries?.length===6,'CURRENT_PRODUCTION_DISPATCH_REQUIRED');
  await verifyFiles(executed.source_files);
  for(const entry of [...executed.entries,...executed.dispatch_entries]){
    insist(entry.accepted===true,'EXECUTED_CASE_REJECTED');
    const report=await read(entry.case.verification);insist(report.accepted===true,'INDEPENDENT_CASE_REJECTED');
  }
  const verifierSource=await Promise.all(verifierPaths.map(async p=>{const x=await file(p);return {path:x.path,sha256:x.sha256};}));
  const verifier=async({dossier,binding})=>{
    const records=executed.entries.filter(x=>x.skill===dossier.id+'@'+dossier.version);
    insist(records.length===2&&same(records.map(x=>x.case),dossier.evidence.cases),'EXECUTION_CASE_BINDING_MISMATCH');
    const dispatched=executed.dispatch_entries.filter(x=>x.skill===dossier.id+'@'+dossier.version);
    insist(same(dispatched.map(x=>x.case),dossier.evidence.dispatchCases),'DISPATCH_CASE_BINDING_MISMATCH');
    insist(records.every(x=>x.entrypoint===dossier.implementation.entrypoint&&x.callable===dossier.implementation.callable),'EXECUTION_ENTRYPOINT_BINDING_MISMATCH');
    await verifyFiles(dossier.implementation.files);await verifyFiles(dossier.evidence.files);
    return {accepted:true,checks:records.length+dispatched.length,implementationDigest:binding.implementationDigest,
      evidenceDigest:binding.evidenceDigest,scopeDigest:binding.scopeDigest};
  };
  const compositionVerifier=async({dossier,bindingDigest})=>{
    const records=executed.entries.filter(x=>dossier.members.includes(x.skill));
    insist(records.length===2*dossier.members.length&&same(records.map(x=>x.case),dossier.evidence.cases),'COMPOSITION_EXECUTION_BINDING_MISMATCH');
    const dispatched=dossier.target==='design@1'?[]:executed.dispatch_entries.filter(x=>dossier.members.includes(x.skill));
    insist(same(dispatched.map(x=>x.case),dossier.evidence.dispatchCases),'COMPOSITION_DISPATCH_BINDING_MISMATCH');
    await verifyFiles(dossier.evidence.files);
    return {accepted:true,checks:records.length+dispatched.length,compositionValidated:true,bindingDigest};
  };
  const store=createCapabilityStore(options(config,fixture,verifierSource,verifier,compositionVerifier));
  for(const dossier of config.skills)await store.admit(dossier);
  for(const composition of config.compositions)await store.admitComposition(composition);
  store.publish();
  for(const item of config.supersessions)store.supersede(item.old,item.new,item.reason);
  const epoch=store.publish(),state=store.exportCachedState();
  const paths=new Set([CONFIG,FIXTURE,...HELPERS,config.executionReceipt.path]);
  for(const item of executed.source_files)paths.add(item.path);
  for(const dossier of config.skills)for(const item of [...dossier.implementation.files,...dossier.evidence.files])paths.add(item.path);
  for(const dossier of config.compositions)for(const item of dossier.evidence.files)paths.add(item.path);
  const inputManifest=await Promise.all([...paths].sort().map(file));
  const receipt={schema:'capability-advantage-cached-admission/v1',nodeVersion:process.version,runtime:config.runtime,
    state,stateSha256:hash(Buffer.from(canonicalize(state))),epoch,verifierSource,inputManifest,
    currentExecutionReceipt:config.executionReceipt,sourceValidation:'ACTUAL_VERSION_SPECIFIC_EXECUTION_THEN_INDEPENDENT_ACCEPTANCE',
    admissionCharge:'ONE_TIME; both B/C reuse the same frozen admission',
    wallMilliseconds:Math.round(performance.now()-started),nodeCpuMicroseconds:process.cpuUsage(cpu),
    liveAuthentication:'NOT RUN',nativeAuthority:[]};
  await mkdir(path.dirname(path.join(ROOT,RECEIPT)),{recursive:true});
  const raw=JSON.stringify(receipt,null,2)+'\n';await writeFile(path.join(ROOT,RECEIPT),raw,{flag:'wx'});
  const pin={schema:'capability-advantage-admission-pin/v1',receipt:{path:RECEIPT,sha256:hash(raw),bytes:Buffer.byteLength(raw)},
    config:await file(CONFIG),fixture:await file(FIXTURE),stateSha256:receipt.stateSha256,graphRoot:epoch.root.graphRoot,
    requirement:'This pin and all referenced JSON must be included in the immutable production source/protocol freeze.'};
  await writeFile(path.join(ROOT,PIN),JSON.stringify(pin,null,2)+'\n',{flag:'wx'});
  return {store,epoch,receipt,pin};
}

export async function catalog(){
  const pin=await read(PIN);insist(pin.schema==='capability-advantage-admission-pin/v1','ADMISSION_PIN_REQUIRED');
  const runtimeSource=await read('protocol/runtime-source.json');
  for(const p of [PIN,RECEIPT,CONFIG,FIXTURE]){
    const expected=runtimeSource.files.find(x=>x.path===p);insist(expected,'PRODUCTION_FREEZE_MISSING_ADMISSION:'+p);await verifyFiles([expected]);
  }
  await verifyFiles([pin.receipt,pin.config,pin.fixture]);
  const receipt=await read(pin.receipt.path),config=await read(CONFIG),fixture=await read(FIXTURE);
  insist(receipt.schema==='capability-advantage-cached-admission/v1'&&receipt.nodeVersion===process.version,'ADMISSION_RUNTIME_CHANGED');
  insist(receipt.stateSha256===pin.stateSha256&&receipt.epoch.root.graphRoot===pin.graphRoot,'ADMISSION_PIN_CONTEXT_MISMATCH');
  await verifyFiles(receipt.inputManifest);
  const disabled=async()=>{throw Error('CACHED_REUSE_CANNOT_ADMIT_NEW_EVIDENCE');};
  const store=createCapabilityStore({...options(config,fixture,receipt.verifierSource,disabled,disabled),
    cachedState:receipt.state,expectedCachedStateSha256:pin.stateSha256});
  return {store,epoch:receipt.epoch,config,runtime:receipt.runtime,receiptSha256:pin.receipt.sha256};
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
  try{const {epoch,receipt}=await createAdmission();console.log(JSON.stringify({root:epoch.root.graphRoot,
    skills:receipt.state.records.length,compositions:receipt.state.compositions.length,
    wallMilliseconds:receipt.wallMilliseconds,receipt:RECEIPT,pin:PIN}));}
  catch(error){console.error(String(error));process.exitCode=2;}
}
