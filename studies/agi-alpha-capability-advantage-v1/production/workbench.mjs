import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir,realpath} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createWorkbench} from '../identity/native/examples/successor-workbench/engine.mjs';

export const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export const sha=raw=>createHash('sha256').update(raw).digest('hex');
const emit=(name,value)=>({name,type:'application/json',content:JSON.stringify(value,null,2)+'\n'});
const assert=(ok,why)=>{if(!ok)throw Error(why);};
async function sourceIdentity(){
  const manifest=JSON.parse(await readFile(path.join(ROOT,'protocol/runtime-source.json'),'utf8'));
  for(const entry of manifest.files){
    const raw=await readFile(path.join(ROOT,entry.path));
    assert(sha(raw)===entry.sha256&&raw.length===entry.bytes,'RUNTIME_SOURCE_DRIFT:'+entry.path);
  }
  return sha(JSON.stringify(manifest));
}
async function inside(file){
  const full=path.resolve(file),real=await realpath(full);
  assert(real.startsWith(ROOT+path.sep),'STUDY_PATH_REQUIRED');return real;
}
async function execute(args,budget){
  return new Promise((resolve,reject)=>{
    const processChild=spawn(process.env.PYTHON_EXECUTABLE||'python3',args,{cwd:ROOT,stdio:['ignore','pipe','pipe'],
      env:{...process.env,OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1',MKL_NUM_THREADS:'1',PYTHONHASHSEED:'0'}});
    let stdout='',stderr='',done=false;
    const timer=setTimeout(()=>{processChild.kill('SIGKILL');},Math.max(1,Math.min(50000,budget)));
    processChild.stdout.on('data',x=>{stdout+=x;if(stdout.length>2000000)processChild.kill('SIGKILL');});
    processChild.stderr.on('data',x=>{stderr=(stderr+x).slice(-16000);});
    processChild.on('error',error=>{clearTimeout(timer);reject(error);});
    processChild.on('close',(code,signal)=>{if(done)return;done=true;clearTimeout(timer);if(code!==0)return reject(Error(`BOUNDED_CHILD_${code}_${signal}:${stderr}`));resolve({stdout,stderr});});
  });
}

export async function run(jobFile,oracleFile,outDirectory,method='shared',selection=null,parent=null){
  const started=performance.now();
  assert(['shared','conventional','independent'].includes(method),'DECLARED_SOLVER_REQUIRED');
  const jobPath=await inside(jobFile),oraclePath=await inside(oracleFile),jobRaw=await readFile(jobPath),job=JSON.parse(jobRaw),jobHash=sha(jobRaw);
  const oracleHash=sha(await readFile(oraclePath)),sourceHash=await sourceIdentity();
  const parentTask=parent?await inside(parent.task):null,parentResult=parent?await inside(parent.result):null;
  const parentHashes=parent?[sha(await readFile(parentTask)),sha(await readFile(parentResult))]:null;
  const directory=path.resolve(outDirectory);assert(directory.startsWith(ROOT+path.sep),'STUDY_OUTPUT_REQUIRED');
  await mkdir(directory,{recursive:true});assert((await realpath(directory)).startsWith(ROOT+path.sep),'OUTPUT_SYMLINK');
  const guard=async()=>{assert(sha(await readFile(jobPath))===jobHash&&sha(await readFile(oraclePath))===oracleHash,'INPUT_DRIFT');assert(await sourceIdentity()===sourceHash,'SOURCE_DRIFT');
    if(parent)assert(sha(await readFile(parentTask))===parentHashes[0]&&sha(await readFile(parentResult))===parentHashes[1],'PARENT_DRIFT');};
  const adapter={manifest:{id:'capability-network-research',version:1,en:'Solve a constrained network engineering job',fr:'Résoudre un travail d’ingénierie de réseau',
      scope:'Bounded synthetic sparse-network forward, inverse and finite-scenario design research; no physical or live-agent qualification.',artifact:'numerical-evidence.json'},
    validate(input){assert(Object.keys(input).sort().join('|')==='id|jobSha256|method'&&input.id===job.id&&input.jobSha256===jobHash&&input.method===method,'REGISTERED_JOB_REQUIRED');},
    async execute(input,checkpoint){
      await checkpoint('validated-capability-selection');await guard();
      if(selection){assert(selection.ok===true&&selection.executionAuthorized===true,'CAPABILITY_NOT_AUTHORIZED');}
      await execute([path.join(ROOT,'production/worker.py'),method,jobPath,path.join(directory,'result.json')],57000-(performance.now()-started));
      await checkpoint('independent-complete-numerical-acceptance');await guard();
      const verifyArgs=[path.join(ROOT,'production/check_result.py'),jobPath,path.join(directory,'result.json'),oraclePath,path.join(directory,'verification.json')];
      if(parent)verifyArgs.push('--parent-task',parentTask,'--parent-result',parentResult);
      await execute(verifyArgs,57000-(performance.now()-started));
      await guard();
      const resultRaw=await readFile(path.join(directory,'result.json')),verificationRaw=await readFile(path.join(directory,'verification.json'));
      const verification=JSON.parse(verificationRaw),accepted=verification.accepted===true;
      const ref={job:job.id,family:job.family,resultSha256:sha(resultRaw),verificationSha256:sha(verificationRaw),jobSha256:jobHash,oracleSha256:oracleHash,method};
      return {decision:accepted?'ACCEPTED_WITH_SCOPE':'REJECTED_WITH_EVIDENCE',summary:{job:job.id,family:job.family,accepted,nodeCount:job.network.node_count},
        evidence:{...ref,sourceHash,execution:'LOCAL_AUTHORED_RESEARCH_ADAPTER',identity:'FIXTURE_ONLY',liveAuthentication:'NOT RUN',actualCustomerAcceptance:false,
          selection:selection?{strategy:selection.strategy,root:selection.root,skillIds:selection.skillIds}:null},
        artifacts:[emit('numerical-evidence.json',ref),emit('independent-acceptance.json',verification),emit('result-location.json',{path:'result.json',sha256:sha(resultRaw),bytes:resultRaw.length})],
        limits:['Synthetic engineering research, no paid job or physical qualification.','Native admission remains HOLD and settlement disconnected.','Full numerical arrays retained in result.json; proof does not establish correctness.','Model authoring, active human attention and complete monetary costs are not measured.']};
    }};
  const workbench=createWorkbench([adapter]);
  const spec={schema:'successor-workbench/v1',family:adapter.manifest.id,name:'AGI ALPHA Capability Advantage',language:'en',owner:'local-research',
    rights:{dataClass:'synthetic',source:'Frozen synthetic graph-network research inputs with independently held numerical answers',license:'Apache-2.0'},reviewMinutes:1,
    inputs:{id:job.id,jobSha256:jobHash,method}};
  const pack=await workbench.run(spec,{sourceHash});const inspection=await workbench.inspectPack(pack);
  assert(performance.now()-started<=60000,'COMPLETE_JOB_BUDGET_EXCEEDED');
  await writeFile(path.join(directory,'pack.json'),JSON.stringify(pack,null,2)+'\n');await writeFile(path.join(directory,'inspection.json'),JSON.stringify(inspection,null,2)+'\n');
  assert(performance.now()-started<=60000,'COMPLETE_JOB_BUDGET_EXCEEDED');
  return {accepted:pack.result.summary.accepted,decision:pack.result.decision,admission:pack.evaluation.admission,authority:pack.evaluation.authority,settlement:pack.evaluation.settlement,
    scope:pack.evaluation.scope,jobHash,sourceHash,elapsedSeconds:(performance.now()-started)/1000,inspection};
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
  const [job,oracle,output,method,parentTask,parentResult]=process.argv.slice(2);
  try{console.log(JSON.stringify(await run(job,oracle,output,method,null,parentTask?{task:parentTask,result:parentResult}:null)));}catch(error){console.error(String(error));process.exitCode=2;}
}
