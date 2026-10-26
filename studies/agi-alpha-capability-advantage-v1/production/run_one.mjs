// SPDX-License-Identifier: Apache-2.0
import {spawn} from 'node:child_process';
import {readFile,writeFile,realpath} from 'node:fs/promises';
import path from 'node:path';
import {catalog} from '../identity/study_catalog.mjs';
import {digest,canonicalize} from '../identity/vendor/commitments.mjs';
import {run,ROOT,sha} from './workbench.mjs';
const [jobFile,oracleFile,output,arm,parentTask,parentResult]=process.argv.slice(2);
const insist=(ok,message)=>{if(!ok)throw Error(message);};
async function inspectJob(job){
  const taskPath=await realpath(path.resolve(job));insist(taskPath.startsWith(ROOT+path.sep),'STUDY_JOB_REQUIRED');
  return new Promise((resolve,reject)=>{
    const child=spawn(process.env.PYTHON_EXECUTABLE||'python3',[path.join(ROOT,'identity/runtime_context.py'),taskPath],
      {cwd:ROOT,stdio:['ignore','pipe','pipe'],env:{...process.env,OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1',MKL_NUM_THREADS:'1'}});
    let stdout='',stderr='';const timer=setTimeout(()=>child.kill('SIGKILL'),10000);
    child.stdout.on('data',x=>{stdout+=x;if(stdout.length>100000)child.kill('SIGKILL');});
    child.stderr.on('data',x=>{stderr=(stderr+x).slice(-10000);});
    child.on('error',e=>{clearTimeout(timer);reject(e);});
    child.on('close',code=>{clearTimeout(timer);if(code!==0)return reject(Error('JOB_DOMAIN_RUNTIME_REFUSED:'+stdout+stderr));
      try{const result=JSON.parse(stdout);insist(result.accepted===true,'JOB_DOMAIN_REFUSED');resolve(result);}catch(error){reject(error);}});
  });
}
try{
  const started=performance.now();insist(['A','B','C','D'].includes(arm),'REGISTERED_ARM_REQUIRED');let selection=null;
  const contextStarted=performance.now(),actual=await inspectJob(jobFile),contextMilliseconds=Math.round(performance.now()-contextStarted);
  if(arm==='B'||arm==='C'){
    const catalogStarted=performance.now(),{store,epoch,runtime,receiptSha256}=await catalog();
    insist(canonicalize(actual.runtime)===canonicalize(runtime),'ACTUAL_RUNTIME_CHANGED_REVALIDATION_REQUIRED');
    const strategy=arm==='B'?'registry':'graph';
    const scope={family:actual.family,schema:actual.schema,empiricalNodeCounts:[225,400],maximumNodes:4096,
      maximumLoads:16,maximumInverseParameters:32,maximumDesignVariables:80,
      permission:'PROSPECTIVE_BOUNDED_RESEARCH_TRIAL',largerScopeStatus:'FRESH_CONFIRMATION_PENDING'};
    const environment={...actual.runtime,execution:'fixed-local-research',threadPolicy:'OPENBLAS_OMP_MKL_1'};
    const selected=store.select(actual.family+'-result',{strategy,scopeDigest:digest(scope,'tested-scope'),
      environmentDigest:digest(environment,'tested-environment'),rightsDigest:digest(actual.rights,'reuse-rights'),expectedRoot:epoch.root.graphRoot});
    const authorization=store.authorizeLocalExecution(selected,{missionId:actual.jobId+'@'+actual.jobSha256});
    selection={ok:selected.ok,executionAuthorized:authorization.mode==='LOCAL_RESEARCH_ONLY',strategy,root:epoch.root.graphRoot,
      skillIds:selected.selected,relationshipRows:selected.relationshipRows,selectionMicroseconds:selected.elapsedMicroseconds,
      catalogElapsedMilliseconds:Math.round(performance.now()-catalogStarted),catalogMode:'TRUSTED_CACHED_ADMISSION_NO_REEXECUTION',
      admissionReceiptSha256:receiptSha256,commonDomainRuntimeMilliseconds:contextMilliseconds,liveAuthentication:'NOT RUN',
      actualJobScope:actual,authorization:{...authorization,jobId:actual.jobId,jobSha256:actual.jobSha256,
        environmentDigest:digest(environment,'tested-environment'),scopeDigest:digest(scope,'tested-scope'),
        permission:'PROSPECTIVE_BOUNDED_RESEARCH_TRIAL',empiricalAdmissionNodeCounts:[225,400]}};
  }
  insist(sha(await readFile(jobFile))===actual.jobSha256,'JOB_CHANGED_AFTER_SCOPE_CHECK');
  const method=arm==='A'?'independent':arm==='D'?'conventional':'shared';
  const result=await run(jobFile,oracleFile,output,method,selection,parentTask?{task:parentTask,result:parentResult}:null);
  insist(result.jobHash===actual.jobSha256,'EXECUTED_JOB_NOT_SCOPE_AUTHORIZED');
  insist(performance.now()-started<=60000,'CATALOG_AND_COMPLETE_JOB_BUDGET_EXCEEDED');
  await writeFile(output+'/domain-runtime.json',JSON.stringify({...actual,commonDomainRuntimeMilliseconds:contextMilliseconds},null,2)+'\n');
  if(selection)await writeFile(output+'/selection.json',JSON.stringify(selection,null,2)+'\n');
  insist(performance.now()-started<=60000,'CATALOG_AND_COMPLETE_JOB_BUDGET_EXCEEDED');
  console.log(JSON.stringify({...result,completeInvocationSeconds:(performance.now()-started)/1000}));
}catch(error){console.error(String(error));process.exitCode=2;}
