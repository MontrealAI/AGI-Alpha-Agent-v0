import {readFile,writeFile} from 'node:fs/promises';
import {catalog} from '../identity/study_catalog.mjs';
import {run} from './workbench.mjs';
const [jobFile,oracleFile,output,arm,parentTask,parentResult]=process.argv.slice(2);
try{
  const started=performance.now();let selection=null;
  if(arm==='B'||arm==='C'){
    const {store,epoch}=await catalog(),job=JSON.parse(await readFile(jobFile,'utf8'));
    const record=store.inspect().records.find(r=>r.dossier.id===job.family),strategy=arm==='B'?'registry':'graph';
    const selected=store.select(job.family+'-result',{strategy,scopeDigest:record.binding.scopeDigest,environmentDigest:record.binding.environmentDigest,
      rightsDigest:record.binding.rightsDigest,expectedRoot:epoch.root.graphRoot});
    const authorization=store.authorizeLocalExecution(selected,{missionId:job.id});
    selection={ok:selected.ok,executionAuthorized:authorization.mode==='LOCAL_RESEARCH_ONLY',strategy,root:epoch.root.graphRoot,skillIds:selected.selected,
      relationshipRows:selected.relationshipRows,selectionMicroseconds:selected.elapsedMicroseconds,catalogElapsedMilliseconds:Math.round(performance.now()-started),
      liveAuthentication:'NOT RUN',authorization};
  }
  const method=arm==='A'?'independent':arm==='D'?'conventional':'shared';
  const result=await run(jobFile,oracleFile,output,method,selection,parentTask?{task:parentTask,result:parentResult}:null);
  if(performance.now()-started>60000)throw Error('CATALOG_AND_COMPLETE_JOB_BUDGET_EXCEEDED');
  if(selection)await writeFile(output+'/selection.json',JSON.stringify(selection,null,2)+'\n');
  console.log(JSON.stringify(result));
}catch(error){console.error(String(error));process.exitCode=2;}
