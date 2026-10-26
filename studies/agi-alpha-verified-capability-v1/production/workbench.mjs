// SPDX-License-Identifier: Apache-2.0
import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createWorkbench} from '../native/examples/successor-workbench/engine.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const emit=(name,value)=>({name,type:'application/json',content:JSON.stringify(value,null,2)+'\n'});
function inside(file){const p=path.resolve(file);if(!p.startsWith(ROOT+path.sep))throw Error('STUDY_PATH_REQUIRED');return p;}
async function identity(){
  const names=['production/retained.py','production/workbench.mjs','production/verify.py','protocol/acceptance-contract.json'];
  const native=JSON.parse(await readFile(path.join(ROOT,'native/SOURCE.json'),'utf8'));
  const entries=[];
  for(const n of names)entries.push([n,sha(await readFile(path.join(ROOT,n)))]);
  for(const n of native.files){const raw=await readFile(inside(path.join(ROOT,'native',n.path)));if(sha(raw)!==n.sha256||raw.length!==n.bytes)throw Error('NATIVE_IDENTITY');entries.push(['native/'+n.path,n.sha256]);}
  return sha(JSON.stringify(entries));
}
function execute(args,allowed=[0]){return new Promise((resolve,reject)=>{
  const child=spawn(process.env.PYTHON_EXECUTABLE||'python3',args,{cwd:ROOT,stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='',closed=false;const timer=setTimeout(()=>{child.kill('SIGKILL');reject(Error('RESEARCH_OPERATION_TIMEOUT'));},90000);
  child.stdout.on('data',x=>{stdout+=x;if(stdout.length>3000000)child.kill('SIGKILL');});child.stderr.on('data',x=>{stderr=(stderr+x).slice(-12000);});
  child.on('error',e=>{clearTimeout(timer);reject(e);});child.on('close',code=>{if(closed)return;closed=true;clearTimeout(timer);if(!allowed.includes(code))return reject(Error(`OPERATION_${code}: ${stderr}`));resolve(stdout);});
});}

export async function run(jobFile,outDirectory){
  const jobPath=inside(jobFile),directory=inside(outDirectory),jobRaw=await readFile(jobPath),job=JSON.parse(jobRaw),jobHash=sha(jobRaw);
  const sourceHash=await identity();await mkdir(directory,{recursive:true});
  const adapter={manifest:{id:'full-lock-evidence',version:1,en:'Check the complete dependency lock',fr:'Vérifier le verrou complet des dépendances',scope:'Exact selected wheel metadata and project requirements; no application runtime qualification.',artifact:'lock-decision.json'},
    validate(input){if(!input||Object.keys(input).sort().join('|')!=='id|jobSha256'||input.id!==job.id||input.jobSha256!==jobHash)throw Error('REGISTERED_JOB_REQUIRED');},
    async execute(input,checkpoint){
      await checkpoint('hash-bound-ordinary-pip-preflight');
      if(sha(await readFile(jobPath))!==jobHash||await identity()!==sourceHash)throw Error('SOURCE_OR_JOB_CHANGED');
      await execute([path.join(ROOT,'production/retained.py'),'--job',jobPath,'--out',path.join(directory,'delivery')]);
      await checkpoint('independent-wheel-metadata-verification');
      await execute([path.join(ROOT,'production/verify.py'),'--job',jobPath,'--result',path.join(directory,'delivery/result.json'),'--out',path.join(directory,'verification.json')],[0,2]);
      if(sha(await readFile(jobPath))!==jobHash||await identity()!==sourceHash)throw Error('SOURCE_OR_JOB_CHANGED');
      const result=JSON.parse(await readFile(path.join(directory,'delivery/result.json'),'utf8'));
      const verification=JSON.parse(await readFile(path.join(directory,'verification.json'),'utf8'));
      return {decision:verification.status==='COMPLETE'?verification.verdict:'INCOMPLETE',summary:{job:job.id,scope:'COMPLETE_LOCK_METADATA_ONLY',accepted:verification.status==='COMPLETE',distributions:job.wheels.length},
        evidence:{jobSha256:jobHash,sourceHash,verificationSha256:sha(await readFile(path.join(directory,'verification.json'))),execution:'LOCAL_RESEARCH_ADAPTER',runtimeModelCalls:0,authoring:'assistant-authored thin ordinary-tool adapter',customerAcceptanceObserved:false},
        artifacts:[emit('lock-decision.json',result),emit('independent-check-summary.json',{status:verification.status,verdict:verification.verdict,sha256:sha(await readFile(path.join(directory,'verification.json')))}),
          emit('complete-evidence-reference.json',{directory:'delivery',files:result.files,verification:'verification.json',job:job.id,scope:'All actual logs, wheel identities, pip report and independent metadata graph remain in the companion'})],
        limits:['A metadata-consistent lock can still fail application tests.','Historical research proposal; no customer order or commercial receipt.','Local research execution, HOLD, empty authority and disconnected settlement.','The schema review field is not measured human labor or a payment.']};
    }};
  const wb=createWorkbench([adapter]);
  const spec={schema:'successor-workbench/v1',family:'full-lock-evidence',name:'AGI ALPHA Second Investment',language:'en',owner:'local-research',rights:{dataClass:'public',source:'Exact public project source and hash-bound public wheel metadata',license:'Apache-2.0 implementation; original wheel licenses preserved'},reviewMinutes:1,inputs:{id:job.id,jobSha256:jobHash}};
  const pack=await wb.run(spec,{sourceHash});const inspection=await wb.inspectPack(pack);
  await writeFile(path.join(directory,'pack.json'),JSON.stringify(pack,null,2)+'\n');await writeFile(path.join(directory,'inspection.json'),JSON.stringify(inspection,null,2)+'\n');
  return {decision:pack.result.decision,summary:pack.result.summary,admission:pack.evaluation.admission,authority:pack.evaluation.authority,inspection:inspection.authentication};
}
if(process.argv[1]===fileURLToPath(import.meta.url)){const [job,out]=process.argv.slice(2);if(!job||!out)throw Error('Usage: node production/workbench.mjs JOB OUTPUT');console.log(JSON.stringify(await run(job,out)));}
