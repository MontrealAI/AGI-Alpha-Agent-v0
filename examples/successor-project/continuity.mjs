// SPDX-License-Identifier: Apache-2.0
// Node receiver: retained cross-repository work history conveys no authority.
import fs from 'node:fs';
import path from 'node:path';
import {spawn, execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {canonical, parseBounded} from '../../docs/assets/successor/engine.mjs';
import {validateProject, nextCycle, appendRecord, exactDigest} from './engine.mjs';
import {createRecord, startRun, completeRun} from '../successor-workbench/mission-record.mjs';
import {run} from '../successor-workbench/engine.mjs';

export const MANAGER_SOURCE = Object.freeze({repository:'MontrealAI/AGIJobManager',commit:'0845a77e6be6bda2e3acdf21544776d60ffdb666',tree:'d417343b95b4e648cd9c6e1e9a994ee2ca708234'});
export const ALPHA_BASELINE = Object.freeze({repository:'MontrealAI/AGI-Alpha-Agent-v0',commit:'7c410d3d61d5d6bba5354307e1784dba2b3aa177',tree:'e80b1dc06317d939e3dd22d2db063a7f1706ddcb'});
export const ALPHA_NATIVE_SOURCE = Object.freeze({repository:'MontrealAI/AGI-Alpha-Agent-v0',commit:'ccad46c561e1b649c77a61d11d405b2ec255e09c',tree:'e987ff3b748cc56a324239fcc3eb6a018010eeec',manifestSha256:'908268b06a535a15ad1725deea48fdd160db6816a2af6d643421383826cd6dea'});
export const LIMIT = 2_000_000;
const ACK = 'new-public-data-cycle';
// Complete execution and builder-data closure of the selected Manager adapter.
const MANAGER_FILES = Object.freeze(['scripts/successor/alpha-project.mjs','scripts/successor/build.mjs',
  'scripts/successor/portable.test.mjs','site/successor.mjs','site/assets/payments.mjs',
  'site/assets/employer-model.mjs',...['safe','legacy-missions','legacy-checker','mapping','missions',
  'checker','model','jobs','archive','app'].map(name=>'site/assets/successor/'+name+'.mjs'),
  'site/assets/successor/style.css','package.json','LICENSE']);
function fail(ok,code){if(!ok)throw Error('CONTINUITY_'+code);}
function fields(value,names){fail(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...names].sort().join('|'),'FIELDS');}
function checkedCheckout(directory,pin){
  fail(typeof directory==='string'&&path.isAbsolute(directory),'CHECKOUT');
  const root=fs.realpathSync(directory);
  const git=args=>execFileSync('git',['-C',root,...args],{encoding:'utf8',timeout:10000,maxBuffer:100000}).trim();
  fail(git(['rev-parse','HEAD'])===pin.commit&&git(['rev-parse','HEAD^{tree}'])===pin.tree,'SOURCE_PIN');
  fail(git(['status','--porcelain','--untracked-files=no'])==='','SOURCE_DIRTY');
  const sourceManifest='docs/successor/mission/sources.json';
  const paths=pin.repository===MANAGER_SOURCE.repository?MANAGER_FILES:[sourceManifest,
    ...Object.keys(JSON.parse(git(['show',pin.commit+':'+sourceManifest])).sources)];
  const entries=execFileSync('git',['-C',root,'ls-tree','-rz',pin.commit,'--',...paths],{timeout:10000,maxBuffer:200000}).toString('utf8').split('\0').filter(Boolean);
  fail(entries.length===paths.length,'SOURCE_BYTES');
  for(const entry of entries){
    const [metadata,relative]=entry.split('\t'),[mode,type,expected]=metadata.split(' ');
    fail(type==='blob'&&['100644','100755'].includes(mode)&&paths.includes(relative),'SOURCE_BYTES');
    const file=path.join(root,relative);
    try{
      fail(fs.lstatSync(file).isFile()&&fs.realpathSync(file)===file,'SOURCE_BYTES');
      const data=fs.readFileSync(file);
      fail(createHash('sha1').update('blob '+data.length+'\0').update(data).digest('hex')===expected,'SOURCE_BYTES');
    }catch{fail(false,'SOURCE_BYTES');}
  }
  // Editable-source metadata must not override Git provenance in a pinned checkout.
  if(pin.repository===MANAGER_SOURCE.repository)fail(!fs.existsSync(path.join(root,'SOURCE.json')),'SOURCE_BYTES');
  return root;
}
async function receiverIdentity(){return {adapterSha256:await exactDigest(fs.readFileSync(fileURLToPath(import.meta.url),'utf8')),nativeBaseline:ALPHA_NATIVE_SOURCE,originalAlpha:ALPHA_BASELINE,manager:MANAGER_SOURCE};}
async function inspectManager(raw,{managerCheckout,alphaBaselineCheckout}){
  parseBounded(raw);
  const manager=checkedCheckout(managerCheckout,MANAGER_SOURCE),alpha=checkedCheckout(alphaBaselineCheckout,ALPHA_BASELINE);
  const program=`import {inspectAlphaProject} from './scripts/successor/alpha-project.mjs';
const chunks=[];for await(const c of process.stdin)chunks.push(c);
const read=await inspectAlphaProject(Buffer.concat(chunks).toString('utf8'),{alphaCheckout:process.argv[1]});
process.stdout.write(JSON.stringify({project:read.transfer.project,checkpoints:read.transfer.history.length,candidates:read.state.candidates.length,plans:read.state.plans.length}));`;
  const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
  const summary=await new Promise((resolve,reject)=>{
    const child=spawn(process.execPath,['--input-type=module','-e',program,alpha],{cwd:manager,env,stdio:['pipe','pipe','pipe']});
    const chunks=[];let bytes=0,failed=false;
    const timer=setTimeout(()=>{failed=true;child.kill();reject(Error('CONTINUITY_MANAGER_TIMEOUT'));},20000);
    child.stdout.on('data',c=>{bytes+=c.length;if(bytes>16000){failed=true;child.kill();reject(Error('CONTINUITY_MANAGER_OUTPUT'));}else chunks.push(c);});
    child.stderr.resume();child.stdin.on('error',()=>{});
    child.on('error',()=>{clearTimeout(timer);reject(Error('CONTINUITY_MANAGER_UNAVAILABLE'));});
    child.on('close',code=>{clearTimeout(timer);if(failed)return;try{fail(code===0,'MANAGER_NATIVE_INVALID');resolve(parseBounded(Buffer.concat(chunks).toString('utf8')));}catch(e){reject(e);}});
    child.stdin.end(raw);
  });
  const transfer=parseBounded(raw),original=await validateProject(transfer.original.raw);
  fail(summary.project.projectId===original.projectId&&summary.project.projectDigest===original.projectDigest,'PROJECT_IDENTITY');
  return {transfer,original,summary};
}
function nativeSources(){
  const manifest=JSON.parse(fs.readFileSync(new URL('../../docs/successor/mission/sources.json',import.meta.url),'utf8'));
  const source=p=>({repository:ALPHA_NATIVE_SOURCE.repository,commit:ALPHA_NATIVE_SOURCE.commit,path:p,sha256:manifest.sources[p]});
  return {sourceHash:manifest.sourceHash,sources:{discovery:source('examples/alpha-discovery/engine.mjs'),mission:source('examples/successor-workbench/mission-record.mjs')}};
}
async function checkNativeSources(alphaBaselineCheckout){
  checkedCheckout(alphaBaselineCheckout,ALPHA_BASELINE);
  const bytes=fs.readFileSync(new URL('../../docs/successor/mission/sources.json',import.meta.url),'utf8');
  fail(await exactDigest(bytes)===ALPHA_NATIVE_SOURCE.manifestSha256,'NATIVE_MANIFEST_DRIFT');
  const manifest=JSON.parse(bytes);
  for(const [relative,hash] of Object.entries(manifest.sources)){
    const local=fs.readFileSync(new URL('../../'+relative,import.meta.url),'utf8');
    fail(await exactDigest(local)===hash,'NATIVE_SOURCE_DRIFT');
  }
}
async function freshProject(original,selection){
  fields(selection,['acknowledgement','cycleId','missionId','spec']);fail(selection.acknowledgement===ACK,'EXPLICIT_NEW_INPUT');
  fail(selection.spec.family==='public-data','MAPPING_UNAVAILABLE');
  const {sourceHash,sources}=nativeSources();
  const record=await createRecord({missionId:selection.missionId,sourceHash,spec:selection.spec});
  const choices={family:'public-data',selection:'explicit-user-selection',duplicatePolicy:'sum-all-rows-no-deduplication',unitPolicy:'unchanged-integer-units',dataRights:selection.spec.rights.dataClass};
  return nextCycle(original,{cycleId:selection.cycleId,record,choices,sourceHash,sources,recovered:true,expectedRevision:original.revision});
}
async function runProject(project,index,recordedPack=null){
  const {sourceHash,sources}=nativeSources(),record=parseBounded(project.cycles.at(-1).records.at(-1).bytes);
  const runId='continuation-run-'+index,running=await startRun(record,{expectedRevision:record.revision,runId});
  const started=await appendRecord(project,running,{expectedRevision:project.revision,sourceHash,sources});
  const completed=await completeRun(running,recordedPack??await run(running.spec,{sourceHash}),{expectedRevision:running.revision,runId});
  return appendRecord(started,completed,{expectedRevision:started.revision,sourceHash,sources});
}
async function seal(body){const raw=canonical({...body,sha256:await exactDigest(canonical(body))});parseBounded(raw);return raw;}
export async function importManagerCycle(managerRaw,selection,options){
  await checkNativeSources(options.alphaBaselineCheckout);
  const {original}=await inspectManager(managerRaw,options),next=await freshProject(original,selection),projectRaw=canonical(next);
  return seal({schema:'successor-project-continuity/v1',sources:await receiverIdentity(),manager:{raw:managerRaw,sha256:await exactDigest(managerRaw)},selection,history:[{kind:'new-alpha-cycle',projectRaw,sha256:await exactDigest(projectRaw)}],authority:'none',qualification:'not-evaluated',settlement:'not-connected'});
}
export async function inspectContinuity(raw,options){
  const value=parseBounded(raw);fields(value,['schema','sources','manager','selection','history','authority','qualification','settlement','sha256']);
  const {sha256,...body}=value;fail(sha256===await exactDigest(canonical(body)),'INTEGRITY');
  fail(value.schema==='successor-project-continuity/v1'&&value.authority==='none'&&value.qualification==='not-evaluated'&&value.settlement==='not-connected','AUTHORITY');
  fail(canonical(value.sources)===canonical(await receiverIdentity()),'SOURCE_DRIFT');
  await checkNativeSources(options.alphaBaselineCheckout);
  fields(value.manager,['raw','sha256']);fail(value.manager.sha256===await exactDigest(value.manager.raw),'MANAGER_BYTES');
  const checked=await inspectManager(value.manager.raw,options);
  fail(Array.isArray(value.history)&&value.history.length>0&&value.history.length<=8,'HISTORY_LIMIT');
  let expected=await freshProject(checked.original,value.selection);
  for(const [index,entry] of value.history.entries()){
    fields(entry,['kind','projectRaw','sha256']);fail(entry.kind===(index===0?'new-alpha-cycle':'local-alpha-run'),'HISTORY_ACTION');
    fail(entry.sha256===await exactDigest(entry.projectRaw),'NATIVE_BYTES');
    const actual=await validateProject(entry.projectRaw);
    if(index>0){
      const recorded=parseBounded(actual.cycles.at(-1).records.at(-1).bytes);
      fail(recorded.state==='result'&&recorded.result?.pack,'RUN_RESULT');
      // Native completeRun recomputes semantic outputs and checks the pack.
      // Preserve supplied historical timestamp/timing; never invent measurements during replay.
      expected=await runProject(expected,index,recorded.result.pack);
    }
    fail(canonical(actual)===canonical(expected),'TRANSITION_CHANGED');
  }
  return {continuity:value,project:expected,managerSummary:checked.summary};
}
export async function advanceContinuity(raw,options){
  const {continuity,project}=await inspectContinuity(raw,options);fail(continuity.history.length<8,'HISTORY_LIMIT');
  const next=await runProject(project,continuity.history.length),projectRaw=canonical(next);
  continuity.history.push({kind:'local-alpha-run',projectRaw,sha256:await exactDigest(projectRaw)});delete continuity.sha256;
  const result=await seal(continuity);await inspectContinuity(result,options);return result;
}
