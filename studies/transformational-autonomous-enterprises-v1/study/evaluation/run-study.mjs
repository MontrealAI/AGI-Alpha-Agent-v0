// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {reference,checkArtifact,sha256,stable} from './checker.mjs';
import {createQualifier} from './qualifier.mjs';

const here=path.dirname(fileURLToPath(import.meta.url)),study=path.dirname(here),candidateRoot=path.join(study,'enterprise');
const output=path.resolve(process.argv[2]??path.join(study,'results'));
const {solve,createWorkspace,sourceManifest}=await import(pathToFileURL(path.join(candidateRoot,'compiler.mjs')).href);
const criteriaBytes=fs.readFileSync(path.join(here,'criteria.json')),criteria=JSON.parse(criteriaBytes),missionsBytes=fs.readFileSync(path.join(here,'missions.json')),missions=JSON.parse(missionsBytes);
const source=sourceManifest();
const variants=[{id:'sliced',candidate:'full-loop',mode:'sliced'},{id:'full-replay',candidate:'full-loop',mode:'full-replay'},{id:'no-inheritance',candidate:'no-inheritance',mode:'full-replay'},{id:'no-construction',candidate:'no-construction',mode:'sliced'},{id:'old-algebra',candidate:'wrong-algebra',mode:'sliced'},{id:'direct-specialist',candidate:'direct-specialist',mode:'sliced'},{id:'old-representation',candidate:'old-representation',mode:'sliced',supplementary:true}];
const number=n=>Number(n.toFixed(6)),sum=(rows,key)=>rows.reduce((s,r)=>s+(r[key]??0),0),median=values=>[...values].sort((a,b)=>a-b)[Math.floor(values.length/2)];
fs.mkdirSync(output,{recursive:true});
function pin(){for(const entry of source.installedCatalog)if(sha256(fs.readFileSync(path.join(candidateRoot,entry.name)))!==entry.sha256)throw Error('CANDIDATE_CHANGED_DURING_SCORING');}
function artifactOf(result,mission){
  const input=Buffer.from(stable(mission)+'\n');
  const groups=result.rows.map(r=>({group:r.group,total:Number(r.amount)}));
  const artifact={schema:'tae.artifact.v1',missionId:mission.missionId,capabilityHash:result.capability?.id??source.rootSha256,inputHash:sha256(input),output:{groups,total:groups.reduce((s,r)=>s+r.total,0)},currentProof:null,authority:[]};
  const bytes=Buffer.from(stable(artifact)+'\n');return {input,artifact,bytes,proof:checkArtifact(bytes,input,criteriaBytes)};
}
const fullRows=[],trials=[],examples={};
for(let repeat=0;repeat<3;repeat++){
  const order=repeat%2?[...variants].reverse():variants;
  for(const variant of order){
    pin();let workspace=createWorkspace({id:'study-'+variant.id+'-'+repeat});const start=performance.now(),cpu=process.cpuUsage();const qualifier=await createQualifier(candidateRoot,{mode:variant.mode,specialist:variant.id==='direct-specialist'});const rows=[];
    for(let index=0;index<missions.length;index++){
      const mission=missions[index];pin();
      if(index===16&&workspace.capability)workspace=createWorkspace({id:'successor-'+variant.id+'-'+repeat,parent:workspace});
      const rowStart=performance.now(),expected=reference(mission),selected=variant.id==='old-algebra'&&mission.kind!=='remediation-impact'?'full-loop':variant.candidate;
      const result=solve(mission,{workspace,variant:selected,budget:{operations:1000000,hashBytes:10000000,elapsedMs:10000}});workspace=result.workspace;
      let evaluation=null,qualification=null,accepted=false;
      if(result.status==='complete'&&result.delivery?.status==='ready'){
        qualification=await qualifier.qualify(mission.kind);evaluation=artifactOf(result,mission);accepted=evaluation.proof.accepted;
      }
      const correct=expected.accepted?accepted:!accepted;
      const row={repeat,variant:variant.id,missionId:mission.missionId,kind:mission.kind,expectedValid:expected.accepted,referenceReason:expected.reason??null,status:result.status,delivery:result.delivery?.status??null,accepted,correct,failure:result.failure,semanticFailures:evaluation?.proof.failures??[],elapsedMs:number(performance.now()-rowStart),metrics:result.metrics,qualification:qualification?.counts??null,freshReference:expected.counts,receiptReference:evaluation?.proof.counts??{referenceSteps:0,inputFacts:0},output:result.rows,capabilityId:result.capability?.id??null,reuse:result.reuseLedger,currentProof:result.currentProof,authority:result.authority};rows.push(row);fullRows.push(row);
      if(repeat===0&&variant.id==='sliced'&&[0,17].includes(index)){
        const role=index===0?'parent':'successor';examples[role]={mission,result,artifact:evaluation?.artifact,proof:evaluation?.proof,qualification,source};
        const dir=path.join(output,role);fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'input.json'),evaluation.input);fs.writeFileSync(path.join(dir,'artifact.json'),evaluation.bytes);fs.writeFileSync(path.join(dir,'proof.json'),stable(evaluation.proof)+'\n');fs.writeFileSync(path.join(dir,'candidate.json'),JSON.stringify(result,null,2)+'\n');
      }
    }
    const elapsedMs=performance.now()-start,q=qualifier.snapshot();
    const trial={repeat,variant:variant.id,validAccepted:rows.filter(r=>r.expectedValid&&r.accepted).length,validCount:rows.filter(r=>r.expectedValid).length,invalidRefused:rows.filter(r=>!r.expectedValid&&!r.accepted).length,invalidCount:rows.filter(r=>!r.expectedValid).length,correctDecisions:rows.filter(r=>r.correct).length,qualification:q,elapsedMs:number(elapsedMs),cpuMicroseconds:process.cpuUsage(cpu),candidateOperations:sum(rows.map(r=>r.metrics),'operations'),candidateHashBytes:sum(rows.map(r=>r.metrics),'hashBytes'),constructionOperations:sum(rows.map(r=>r.metrics),'constructionOperations'),freshReferenceSteps:sum(rows.map(r=>r.freshReference),'referenceSteps')+sum(rows.map(r=>r.receiptReference),'referenceSteps'),freshInputFacts:sum(rows.map(r=>r.freshReference),'inputFacts')+sum(rows.map(r=>r.receiptReference),'inputFacts'),sourcePinHashBytes:source.installedCatalog.reduce((s,r)=>s+r.bytes,0)*(rows.length+1),freshReceipts:rows.filter(r=>r.accepted).length,perMissionLatencyMs:{median:number(median(rows.map(r=>r.elapsedMs))),p95:number([...rows.map(r=>r.elapsedMs)].sort((a,b)=>a-b)[Math.floor(rows.length*.95)])}};
    trials.push(trial);fs.writeFileSync(path.join(output,'progress.json'),JSON.stringify({completed:trials.length,trial},null,2));console.log(JSON.stringify(trial));
  }
}
const summaries=variants.map(variant=>{
  const run=trials.filter(r=>r.variant===variant.id);
  return {name:variant.id,supplementary:!!variant.supplementary,trials:run.length,validAccepted:sum(run,'validAccepted'),validCount:sum(run,'validCount'),invalidRefused:sum(run,'invalidRefused'),invalidCount:sum(run,'invalidCount'),correctDecisions:sum(run,'correctDecisions'),qualificationCasesPerTrial:run[0].qualification.qualificationCases,qualificationAssertionsPerTrial:run[0].qualification.qualificationAssertions,qualificationReferenceStepsPerTrial:run[0].qualification.referenceSteps,freshReferenceStepsPerTrial:run[0].freshReferenceSteps,candidateOperationsPerTrial:run[0].candidateOperations,candidateHashBytesPerTrial:run[0].candidateHashBytes,qualificationHashBytesPerTrial:run[0].qualification.hashBytes,constructionOperationsPerTrial:run[0].constructionOperations,medianElapsedMs:number(median(run.map(r=>r.elapsedMs))),minElapsedMs:Math.min(...run.map(r=>r.elapsedMs)),maxElapsedMs:Math.max(...run.map(r=>r.elapsedMs)),cpuUserMicroseconds:sum(run.map(r=>r.cpuMicroseconds),'user'),cpuSystemMicroseconds:sum(run.map(r=>r.cpuMicroseconds),'system')};
});
const sliced=summaries.find(r=>r.name==='sliced'),replay=summaries.find(r=>r.name==='full-replay');
const reduction=1-sliced.qualificationCasesPerTrial/replay.qualificationCasesPerTrial;
const summary={schema:'tae.study-results.v1',edition:criteria.edition,criteriaSha256:sha256(criteriaBytes),missionsSha256:sha256(missionsBytes),checkerSha256:sha256(fs.readFileSync(path.join(here,'checker.mjs'))),qualifierSha256:sha256(fs.readFileSync(path.join(here,'qualifier.mjs'))),runnerSha256:sha256(fs.readFileSync(fileURLToPath(import.meta.url))),candidateSource:source,population:criteria.population,repetitions:3,variants:summaries,technicalThreshold:{predeclaredPercent:50,observedPercent:number(reduction*100),identicalDecisions:fullRows.filter(r=>r.variant==='sliced').every(r=>fullRows.find(o=>o.variant==='full-replay'&&o.repeat===r.repeat&&o.missionId===r.missionId)?.accepted===r.accepted),freshAnswersChecked:true,passed:reduction>=.5&&sliced.correctDecisions===144&&replay.correctDecisions===144,meaning:'finite qualification-case reduction only; not external practical/economic value'},economics:{cashReceivedUSD:0,firmExternalOffer:null,realizedProfit:null,fullyAttributableCostUSD:null,newPaidServicesUSD:0,modelAuthoringCostUSD:null,humanMinutes:null,commercialTarget:'unproven',customerDemand:'unvalidated',testTokensAreRevenue:false},limitations:['Finite authored module catalog and deterministic symbolic planning; no autonomous source invention or learned-provider substitution.','Same-controller separate checker and task owner; no hostile OS or institutional independence claim.','Three timing repetitions are descriptive and system-dependent.','Qualification checks and instrumented events are not CPU instructions, dollars, or formal program proofs.','Source composition is not installed Fleet host qualification or held Harness integration.'],failures:fullRows.filter(r=>!r.correct||r.status!=='complete'||r.semanticFailures.length).map(r=>({variant:r.variant,repeat:r.repeat,missionId:r.missionId,status:r.status,failure:r.failure,semanticFailures:r.semanticFailures,correctRejection:!r.expectedValid&&!r.accepted}))};
pin();
fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify(summary,null,2)+'\n');fs.writeFileSync(path.join(output,'trials.json'),JSON.stringify(trials,null,2)+'\n');fs.writeFileSync(path.join(output,'all-results.json'),JSON.stringify(fullRows,null,2)+'\n');fs.writeFileSync(path.join(output,'examples.json'),JSON.stringify(examples,null,2)+'\n');
console.log(JSON.stringify({summary:output,technicalThreshold:summary.technicalThreshold,variants:summaries}));
