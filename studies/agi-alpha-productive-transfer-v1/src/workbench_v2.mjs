// SPDX-License-Identifier: Apache-2.0
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createWorkbench} from '../vendor/native/examples/successor-workbench/engine.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const json=(name,value)=>({name,type:'application/json',content:JSON.stringify(value,null,2)+'\n'});

async function sourceIdentity(){
  const native=JSON.parse(await readFile(path.join(ROOT,'vendor/native/SOURCE.json')));
  const files=[];
  for(const row of native.files){
    const raw=await readFile(path.join(ROOT,'vendor/native',row.path));
    if(raw.length!==row.bytes||sha(raw)!==row.sha256)throw Error('UNCHANGED_NATIVE_IDENTITY');
    files.push([row.path,row.sha256]);
  }
  for(const name of ['src/intake.py','src/run_mission_v2.py','src/conventional_v2.py','src/delivery_v2.py','src/workbench_v2.mjs',
    'protocol/model-extraction-prompt.txt','vendor/product/contrib/upgrade_decision/core.py']){
    files.push([name,sha(await readFile(path.join(ROOT,name)))]);
  }
  return sha(JSON.stringify(files));
}

function execute(args){
  return new Promise((resolve,reject)=>{
    const child=spawn(process.env.PYTHON_EXECUTABLE||'python',[path.join(ROOT,'src/run_mission_v2.py'),...args],
      {cwd:ROOT,stdio:['ignore','pipe','pipe']});
    let output='',errors='',oversized=false;
    const timer=setTimeout(()=>{child.kill('SIGKILL');},30000);
    child.stdout.on('data',b=>{output+=b;if(output.length>300000){oversized=true;child.kill('SIGKILL');}});
    child.stderr.on('data',b=>{errors=(errors+b).slice(-10000);});
    child.on('error',e=>{clearTimeout(timer);reject(e);});
    child.on('close',code=>{clearTimeout(timer);if(code!==0||oversized)return reject(Error(`DELIVERY_FAILED ${code} ${errors}`));
      try{resolve(JSON.parse(output));}catch(e){reject(e);}});
  });
}

export async function runMission(rawPath,arm,outputPath,proposalPath=null){
  if(!['A','B','C'].includes(arm))throw Error('ARM');
  const sourceHash=await sourceIdentity();
  const raw=await readFile(rawPath),task=JSON.parse(raw);
  const directory=path.resolve(outputPath);
  await mkdir(directory,{recursive:false});
  const sourceTaskSha256=sha(raw);
  const proposalSha256=proposalPath?sha(await readFile(proposalPath)):null;
  const adapter={
    manifest:{id:'source-intake-transfer-v2',version:2,en:'Review a dependency call contract',fr:'Examiner un contrat d’appel',
      scope:'Captured public consumer sources; exact selected binding and explicit unresolved scope.',artifact:'intake-result.json'},
    validate(input){
      const expected={id:task.id,arm,sourceTaskSha256,proposalSha256};
      if(!input||Object.keys(input).sort().join('|')!==Object.keys(expected).sort().join('|')||
        Object.entries(expected).some(([key,value])=>input[key]!==value))throw Error('EXACT_TASK');
    },
    async execute(input,checkpoint){
      await checkpoint('captured-source-intake-and-exact-verification');
      const args=['--raw',path.resolve(rawPath),'--arm',arm,'--out',path.join(directory,'delivery')];
      if(proposalPath)args.push('--proposal',path.resolve(proposalPath));
      const receipt=await execute(args);
      const resultRaw=await readFile(path.join(directory,'delivery/result.json'));
      if(sha(resultRaw)!==receipt.resultSha256)throw Error('RESULT_IDENTITY');
      const result=JSON.parse(resultRaw);
      await checkpoint('bilingual-handoff-complete-independent-acceptance-pending');
      const light={...result};delete light.request;
      return {decision:result.nextAction,summary:{mission:task.id,selectedCalls:receipt.selectedCalls,
        unresolvedIntake:receipt.unresolvedIntake,completeScopeAccepted:null},
        evidence:{sourceTaskSha256,proposalSha256,resultSha256:receipt.resultSha256,execution:'FINITE_LOCAL_RESEARCH',
          currentSessionModelInput:arm!=='C',operatorAuthority:false,customerAcceptance:false},
        artifacts:[json('intake-result.json',light),json('execution-receipt.json',receipt),
          json('captured-source-reference.json',{sourceTaskSha256,fullTask:'../../../inputs/followup/'+path.basename(rawPath),
            fullLocalResult:'delivery/result.json',fullResultSha256:receipt.resultSha256})],
        limits:result.limits};
    }
  };
  const workbench=createWorkbench([adapter]);
  const spec={schema:'successor-workbench/v1',family:adapter.manifest.id,name:'AGI ALPHA source intake',language:'en',owner:'local-research',
    rights:{dataClass:'public',source:'Exact captured public Git bodies; license records retained in each input',license:'Source-specific licenses; Apache-2.0 adapter'},
    reviewMinutes:1,inputs:{id:task.id,arm,sourceTaskSha256,proposalSha256}};
  const pack=await workbench.run(spec,{sourceHash});
  const inspection=await workbench.inspectPack(pack);
  await writeFile(path.join(directory,'workbench-pack.json'),JSON.stringify(pack,null,2)+'\n');
  await writeFile(path.join(directory,'workbench-inspection.json'),JSON.stringify(inspection,null,2)+'\n');
  return {mission:task.id,arm,decision:pack.result.decision,admission:pack.evaluation.admission,
    authority:pack.evaluation.authority,authentication:inspection.authentication,
    sourceHash,actualCollectionsUsd:0};
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
  const [raw,arm,out,proposal]=process.argv.slice(2);
  if(!raw||!arm||!out)throw Error('Usage: node src/workbench.mjs RAW ARM NEW_OUT [PROPOSAL]');
  console.log(JSON.stringify(await runMission(raw,arm,out,proposal)));
}
