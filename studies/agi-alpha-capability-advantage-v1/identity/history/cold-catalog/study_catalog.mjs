import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createCapabilityStore} from './capability-store.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=async p=>JSON.parse(await readFile(path.join(ROOT,p),'utf8'));
async function independentlyVerify(cases){
  return new Promise((resolve,reject)=>{
    const child=spawn(process.env.PYTHON_EXECUTABLE||'python3',[path.join(ROOT,'identity/validate_evidence.py')],
      {cwd:ROOT,stdio:['pipe','pipe','pipe'],env:{...process.env,OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1',MKL_NUM_THREADS:'1'}});
    let stdout='',stderr='';const timer=setTimeout(()=>child.kill('SIGKILL'),30000);
    child.stdin.end(JSON.stringify({cases}));child.stdout.on('data',x=>{stdout+=x;if(stdout.length>1000000)child.kill('SIGKILL');});
    child.stderr.on('data',x=>{stderr=(stderr+x).slice(-10000);});child.on('error',e=>{clearTimeout(timer);reject(e);});
    child.on('close',code=>{clearTimeout(timer);if(code!==0)return reject(Error(`VALIDATOR_${code}:${stderr}`));try{resolve(JSON.parse(stdout));}catch(error){reject(error);}});
  });
}
export async function catalog(){
  const config=await read('identity/catalog.json'),fixture=await read('identity/authority-fixtures.json');
  const verifierSource=await Promise.all(['workloads/verifier.py','identity/validate_evidence.py','identity/study_catalog.mjs'].map(async p=>({path:p,sha256:hash(await readFile(path.join(ROOT,p)))})));
  const verifier=async ({dossier,binding})=>{
    const checked=await independentlyVerify(dossier.evidence.cases);
    return {accepted:checked.accepted,checks:checked.checks,implementationDigest:binding.implementationDigest,evidenceDigest:binding.evidenceDigest,scopeDigest:binding.scopeDigest};
  };
  const compositionVerifier=async ({dossier,bindingDigest})=>{
    const checked=await independentlyVerify(dossier.evidence.cases);
    return {accepted:checked.accepted,checks:checked.checks,compositionValidated:checked.accepted,bindingDigest};
  };
  const store=createCapabilityStore({rootDirectory:ROOT,fixture,verifier,compositionVerifier,verifierSource,compositionVerifierSource:verifierSource,
    executionPolicy:{mode:'LOCAL_RESEARCH_ONLY',nativeAuthority:[],allowedSkills:['forward@1','inverse@1','design@1'],maxRuns:36,expiresAt:9000}});
  for(const dossier of config.skills)await store.admit(dossier);
  for(const composition of config.compositions)await store.admitComposition(composition);
  const epoch=store.publish();
  return {store,epoch};
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
  const started=performance.now(),cpu=process.cpuUsage(),{store,epoch}=await catalog();
  await mkdir(path.join(ROOT,'evidence/admission'),{recursive:true});
  const receipt={schema:'capability-advantage-admission/v1',...store.inspect(),epoch,wallMilliseconds:Math.round(performance.now()-started),
    nodeCpuMicroseconds:process.cpuUsage(cpu),childCpu:'Metered by outer process',identity:'FIXTURE_ONLY',liveAuthentication:'NOT RUN'};
  await writeFile(path.join(ROOT,'evidence/admission/catalog-admission.json'),JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify({root:epoch.root.graphRoot,skills:receipt.records.length,compositions:receipt.compositions.length,wallMilliseconds:receipt.wallMilliseconds}));
}
