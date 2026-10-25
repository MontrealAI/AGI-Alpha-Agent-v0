// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {createHash, randomUUID} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {constants, existsSync, writeFileSync} from 'node:fs';
import {mkdir, readFile, writeFile, open, link, unlink, lstat, rename, readdir} from 'node:fs/promises';
import {dirname, resolve, join, relative} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import * as guide from '../../../examples/ti-guide/guide.mjs';
import {parseBounded} from '../../../docs/assets/successor/engine.mjs';

const HERE=dirname(fileURLToPath(import.meta.url)), ROOT=resolve(HERE,'../../..');
const DEPENDENCIES=['examples/ti-guide/guide.mjs','examples/successor-alpha/engine.mjs',
  'examples/successor-alpha/research.mjs','docs/assets/successor/engine.mjs'];
const STAGES=['recovery','planning','preparation','execution','verification','correction','packaging','reporting'];
const OUTPUTS={recovery:[],planning:[],preparation:['prepared-inputs.json','declared-inventory.csv','observed-inventory.csv'],
  execution:['result.json'],verification:['acceptance.json'],correction:['correction.json'],
  packaging:['differences.csv','action-plan.csv','workspace.json'],reporting:['report.md']};
const json=value=>JSON.stringify(value,null,2)+'\n';
const hash=value=>createHash('sha256').update(value).digest('hex');
const safePath=value=>typeof value==='string' && /^[A-Za-z0-9_.\/-]+$/.test(value) &&
  !value.startsWith('/') && value.split('/').every(part=>part && part!=='.' && part!=='..');
const fact=(value,reference,basis='measured')=>({value,basis,reference});
const artifactName=value=>typeof value==='string' && /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(value);
function git(args,timeout=5000) {
  const environment=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^git_/i.test(key)));
  return execFileSync('git',['--no-lazy-fetch','--no-replace-objects','--no-pager',...args],
    {cwd:ROOT,timeout,maxBuffer:4_000_000,env:{...environment,GIT_TERMINAL_PROMPT:'0',GIT_OPTIONAL_LOCKS:'0'}});
}
function committed(ref,path,deadline=null) {
  assert.match(ref,/^[0-9a-f]{40}$/); assert(safePath(path),'Use a bounded repository-relative public source path.');
  const remaining=()=>{const value=deadline===null?5000:Math.ceil(deadline-performance.now());
    assert(value>0,'Approved elapsed budget exhausted; checkpoint retained.');return Math.min(5000,value);};
  const listing=git(['ls-tree','-z',ref,'--',path],remaining()).toString().split('\0');
  assert.equal(listing.length,2,'An exact committed source entry is required.');
  const [metadata,listedPath]=listing[0].split('\t'),[mode,type]=metadata.split(' ');
  assert.equal(listedPath,path);assert(type==='blob' && ['100644','100755'].includes(mode),
    'Only committed ordinary source files with mode 100644 or 100755 are admitted.');
  return git(['show',`${ref}:${path}`],remaining());
}
async function ordinary(path,maximum=2_000_000) {
  const file=await open(path,constants.O_RDONLY|(constants.O_NONBLOCK??0)|(constants.O_NOFOLLOW??0));
  try {
    const stat=await file.stat(); assert(stat.isFile() && stat.size<=maximum,'A bounded ordinary artifact is required.');
    const data=Buffer.alloc(maximum+1); let used=0;
    while(used<data.length){const {bytesRead}=await file.read(data,used,data.length-used,null);if(!bytesRead)break;used+=bytesRead;}
    assert(used<=maximum,'Artifact exceeds its byte bound.');
    return data.subarray(0,used);
  } finally {await file.close();}
}
async function exclusive(path,data) {
  const temporary=join(dirname(path),'.pending-'+randomUUID());
  const file=await open(temporary,'wx',0o600);
  try {await file.writeFile(data);await file.sync();} finally {await file.close();}
  try {await link(temporary,path);} finally {await unlink(temporary);}
}
function manifestSources(bytes) {
  assert(bytes.length<=200_000,'Manifest exceeds 200 KB.');
  const value=parseBounded(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  assert(value.sources && typeof value.sources==='object' && !Array.isArray(value.sources),'Manifest needs source identities.');
  const rows=Object.entries(value.sources).sort(([a],[b])=>a<b?-1:a>b?1:0);
  assert(rows.length>0 && rows.length<=128,'Use 1–128 explicit source paths.');
  for(const [path,digest] of rows){assert(safePath(path),'Unsafe source path.');assert.match(digest,/^[0-9a-f]{64}$/);}
  return rows;
}
async function installedIdentity() {
  const dependencySha256={};
  for(const path of DEPENDENCIES)dependencySha256[path]=hash(await ordinary(join(ROOT,path)));
  dependencySha256[relative(ROOT,fileURLToPath(import.meta.url))]=hash(await ordinary(fileURLToPath(import.meta.url)));
  return {methodIdentity:hash(guide.canonical(dependencySha256)),dependencySha256};
}
export async function makePlan({manifestPath,sourceRef,runId,maxSeconds=20,createdAt=new Date().toISOString(),
  maxAttempts=8,maxTotalSeconds=maxSeconds*maxAttempts,expiresAt=new Date(Date.parse(createdAt)+3_600_000).toISOString(),
  schema='alpha-source-assurance-plan/v3'}) {
  const wall=performance.now(),cpu=process.cpuUsage();
  assert(safePath(manifestPath),'Choose an explicit public manifest path.');
  assert.match(sourceRef,/^[0-9a-f]{40}$/);assert.match(runId,/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/);
  assert(Number.isSafeInteger(maxSeconds) && maxSeconds>=1 && maxSeconds<=60,'Use a 1–60 second budget.');
  assert(typeof createdAt==='string' && new Date(createdAt).toISOString()===createdAt,'Use an exact ISO date.');
  assert(['alpha-source-assurance-plan/v2','alpha-source-assurance-plan/v3'].includes(schema));
  if(schema==='alpha-source-assurance-plan/v3') {
    assert(Number.isSafeInteger(maxAttempts) && maxAttempts>=1 && maxAttempts<=128,'Use a 1–128 attempt envelope.');
    assert(Number.isSafeInteger(maxTotalSeconds) && maxTotalSeconds>=maxSeconds && maxTotalSeconds<=3600,
      'Total reserved execution must be between one attempt and 3600 seconds.');
    assert(typeof expiresAt==='string' && new Date(expiresAt).toISOString()===expiresAt &&
      Date.parse(expiresAt)>Date.parse(createdAt) && Date.parse(expiresAt)-Date.parse(createdAt)<=86_400_000,
      'Use an explicit expiry within 24 hours of plan creation.');
  }
  const deadline=wall+maxSeconds*1000,source=committed(sourceRef,manifestPath,deadline), rows=manifestSources(source);
  for(const path of DEPENDENCIES)assert.equal(hash(await ordinary(join(ROOT,path))),hash(committed(sourceRef,path,deadline)),
    'Installed comparison dependency differs from the approved source.');
  const identity=await installedIdentity();
  const plan={schema,offeringId:'committed-source-assurance',runId,createdAt,manifestPath,sourceRef,
    manifestSha256:hash(source),sourceCount:rows.length,maxSeconds,...identity,authority:'none',
    ...(schema==='alpha-source-assurance-plan/v3'?{maxAttempts,maxTotalSeconds,expiresAt}:{}),
    acceptance:'Exact source identities and lossless difference/action exports; no approval of source behavior.',
    allowedOperations:['read fixed public Git blobs','deterministic catalogue comparison','write this run artifact directory']};
  const used=process.cpuUsage(cpu);
  return {plan,approvalDigest:hash(guide.canonical(plan)),planningFacts:{
    wallMicroseconds:fact(Math.ceil((performance.now()-wall)*1000),'Observed automatic scope preparation and planning.'),
    cpuMicroseconds:fact(used.user+used.system,'Observed local Node CPU; child Git CPU excluded.'),
    toolInvocations:fact(2+2*DEPENDENCIES.length,'Fixed Git blob reads during automatic planning.'),
    modelCalls:fact(0,'No model adapter is called by deterministic planning.'),
    monetaryCost:fact(null,'Execution timing is not full monetary cost.','unknown')}};
}
async function checkedPlan(raw,approvalDigest,rebuild=true) {
  const frame=parseBounded(typeof raw==='string'?raw:guide.canonical(raw));
  assert(['alpha-source-assurance-plan/v2','alpha-source-assurance-plan/v3'].includes(frame?.schema));
  assert.match(frame.runId,/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/);
  assert(Number.isSafeInteger(frame.maxSeconds) && frame.maxSeconds>=1 && frame.maxSeconds<=60);
  assert.equal(hash(guide.canonical(frame)),approvalDigest,'Approve the exact bounded plan digest.');
  if(frame.schema==='alpha-source-assurance-plan/v3') {
    assert(Number.isSafeInteger(frame.maxAttempts) && frame.maxAttempts>=1 && frame.maxAttempts<=128);
    assert(Number.isSafeInteger(frame.maxTotalSeconds) && frame.maxTotalSeconds>=frame.maxSeconds && frame.maxTotalSeconds<=3600);
    assert(new Date(frame.createdAt).toISOString()===frame.createdAt && new Date(frame.expiresAt).toISOString()===frame.expiresAt);
    assert(Date.parse(frame.expiresAt)>Date.parse(frame.createdAt) && Date.parse(frame.expiresAt)-Date.parse(frame.createdAt)<=86_400_000);
    assert(Date.now()>=Date.parse(frame.createdAt),'Approved plan is not yet valid.');
    assert(Date.now()<Date.parse(frame.expiresAt),'Approved envelope expired; a new exact approval is required.');
  }
  if(!rebuild)return frame;
  const rebuilt=await makePlan(frame);
  assert.equal(guide.canonical(rebuilt.plan),guide.canonical(frame),'Plan fields, dependencies or source changed.');
  assert.equal(rebuilt.approvalDigest,approvalDigest,'Approve the exact bounded plan digest.');
  return rebuilt.plan;
}
export function independentlyCheck(input,result) {
  const left=guide.preview(input.leftCsv), right=guide.preview(input.rightCsv);
  const expected=new Map(left.rows.map(([path,digest])=>[path,digest]));
  assert.equal(expected.size,left.rows.length);assert.deepEqual(left.headers,['path','sha256']);
  assert.deepEqual(right.headers,['path','sha256']);assert.equal(right.rows.length,left.rows.length);
  const changed=right.rows.filter(([path,digest])=>{assert(expected.has(path));return expected.get(path)!==digest;});
  assert.equal(new Set(right.rows.map(row=>row[0])).size,right.rows.length);
  assert.equal(result.metrics.matchedPairs,left.rows.length);assert.equal(result.metrics.unmatchedRows,0);
  assert.deepEqual(result.differences.map(row=>[row.key,row.leftValue,row.rightValue]),
    changed.map(([path,digest])=>[path,expected.get(path),digest]));
  assert.equal(result.metrics.fieldDifferences,changed.length);assert.equal(result.metrics.actionGroups,changed.length);
  assert.equal(result.resolution.coverage.originalOccurrences,changed.length);
  assert.equal(result.resolution.automaticallyResolved,false);
  assert.equal(result.leftIdentity.sha256,hash(input.leftCsv));assert.equal(result.rightIdentity.sha256,hash(input.rightCsv));
  return {schema:'alpha-source-assurance-acceptance/v1',accepted:true,sourceRows:left.rows.length,changedPaths:changed.map(row=>row[0]),
    checker:'Separate exact-key/hash map checks; Python verify-run.py supplies a separate CSV/Git implementation.',
    commercialAcceptance:'unknown',authority:'none'};
}
async function loadJSON(path){return parseBounded((await ordinary(path)).toString('utf8'));}
function reportMarkdown(plan,acceptance,traces,unknownAttempts) {
  return `# Finished public-source assurance\n\n${plan.sourceCount} committed source identities checked; ${acceptance.changedPaths.length} paths need attention.\n\n`+
    `Source: ${plan.sourceRef}; manifest: ${plan.manifestPath}.\n\n`+
    `The action plan and full differences identify every mismatch. Nothing modifies or approves the inspected source.\n\n`+
    `## Automated work\n\nPreparation, bounded planning, comparison, exact checking, refusal/correction decision, packaging, reporting and checkpoint recovery run in software after approval.\n\n`+
    `## Cost and attention\n\n${traces.length} prior stage receipts; ${unknownAttempts} interrupted/uncommitted attempt(s) at this reporting checkpoint. Completion and reconnect receipts account for later restart cost. No service model calls were used. These are process observations, not complete Agent monetary cost. Hardware, allocated engineering/maintenance, wages, human comparison time and commercial acceptance remain unmeasured.\n\n`+
    `User decisions remain: approve the exact input scope, inspect the finished report and decide whether proposed source corrections should be commissioned. Those decisions do not become routine operator labor in this offering.\n\n`+
    `## Scope\n\nForeground local Node execution only. No authenticated executor, network, wallet, payment, scheduler or arbitrary source-code execution.\n`;
}
async function checkedReportContext(directory,approvalDigest,traces,snapshot) {
  assert.deepEqual(Object.keys(snapshot).sort(),['approvalDigest','attempt','attempts','priorStageReceipts','schema'],
    'Reporting snapshot fields changed.');
  assert.equal(snapshot.schema,'alpha-source-report-context/v1');
  assert.equal(snapshot.approvalDigest,approvalDigest,'Reporting snapshot changed the approved scope.');
  assert.match(snapshot.attempt,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.equal(snapshot.priorStageReceipts,7,'Reporting snapshot changed its stage boundary.');
  assert(traces.length>=snapshot.priorStageReceipts,'Reporting snapshot precedes missing stage receipts.');
  assert(Array.isArray(snapshot.attempts) && snapshot.attempts.length>0 && snapshot.attempts.length<=128,
    'Reporting snapshot needs 1–128 committed attempt identities.');
  const names=snapshot.attempts.map(row=>row.name);
  assert.deepEqual(names,[...new Set(names)].sort(),'Reporting snapshot attempts must be unique and sorted.');
  assert(names.includes(`attempt-${snapshot.attempt}.json`),'Reporting snapshot lost its original attempt.');
  for(const row of snapshot.attempts) {
    assert.deepEqual(Object.keys(row).sort(),['name','sha256']);
    assert.match(row.name,/^attempt-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.json$/);
    assert.match(row.sha256,/^[0-9a-f]{64}$/);
    const bytes=await ordinary(join(directory,row.name)),record=parseBounded(bytes.toString('utf8'));
    assert.equal(hash(bytes),row.sha256,'Reporting snapshot attempt bytes changed.');
    assert.equal(row.name,`attempt-${record.attempt}.json`,'Reporting snapshot attempt identity changed.');
    assert.equal(record.approvalDigest,approvalDigest);assert.equal(record.state,'started');
  }
  return {priorStageReceipts:snapshot.priorStageReceipts,unknownAttempts:snapshot.attempts.length-1};
}
async function reverifyDelivery(directory,plan,deadline,traces,checkpoint=()=>{}) {
  checkpoint();
  const wall=performance.now(),cpu=process.cpuUsage(),manifest=committed(plan.sourceRef,plan.manifestPath,deadline);
  assert.equal(hash(manifest),plan.manifestSha256);
  const declared=manifestSources(manifest),observed=declared.map(([path])=>{
    checkpoint();return [path,hash(committed(plan.sourceRef,path,deadline))];});
  const input={leftCsv:guide.safeCsv([['path','sha256'],...declared]),rightCsv:guide.safeCsv([['path','sha256'],...observed]),leftKey:'path',rightKey:'path'};
  const expectedPrepared={schema:'alpha-source-assurance-inputs/v1',sourceRef:plan.sourceRef,manifestPath:plan.manifestPath,input};
  assert.equal(guide.canonical(await loadJSON(join(directory,'prepared-inputs.json'))),guide.canonical(expectedPrepared),
    'Prepared checkpoint differs from the approved Git source.');
  const recomputed=await guide.compute(input),saved=await loadJSON(join(directory,'result.json'));
  assert.equal(guide.canonical(saved),guide.canonical(recomputed),'Saved result differs from complete recomputation.');
  const acceptance=independentlyCheck(input,recomputed);
  assert.equal(guide.canonical(await loadJSON(join(directory,'acceptance.json'))),guide.canonical(acceptance));
  const workspace=guide.makeWorkspace(input,recomputed,{approach:'grouped',sourceHash:plan.methodIdentity,
    runId:plan.runId,createdAt:plan.createdAt,language:'en'});
  assert.equal(guide.canonical(await loadJSON(join(directory,'workspace.json'))),guide.canonical(workspace));
  for(const [name,expected] of Object.entries({'declared-inventory.csv':input.leftCsv,'observed-inventory.csv':input.rightCsv,
    'differences.csv':guide.fullDifferencesCsv(recomputed),'action-plan.csv':guide.actionPlanCsv(recomputed)}))
    assert.equal((await ordinary(join(directory,name),8_000_000)).toString('utf8'),expected,'Derived delivery differs: '+name);
  const reporting=traces.find(receipt=>receipt.stage==='reporting'),context=reporting?.reportContext;
  const snapshot=await loadJSON(join(directory,'report-context.json'));
  assert.equal(guide.canonical(context),guide.canonical(await checkedReportContext(directory,
    hash(guide.canonical(plan)),traces,snapshot)),'Reporting checkpoint differs from its committed historical context.');
  assert.equal((await ordinary(join(directory,'report.md'))).toString('utf8'),
    reportMarkdown(plan,acceptance,traces.slice(0,context.priorStageReceipts),context.unknownAttempts),
    'Report differs from its exact historical reporting checkpoint.');
  const used=process.cpuUsage(cpu);
  checkpoint();
  return {schema:'alpha-source-final-revalidation/v1',accepted:true,stage:'verification',
    check:'Full Git-bound preparation, complete existing-guide result, workspace, all deliverable CSVs and report recomputed before completion.',
    wallMicroseconds:fact(Math.ceil((performance.now()-wall)*1000),'Observed final whole-output revalidation.'),
    cpuMicroseconds:fact(used.user+used.system,'Observed local Node CPU; child Git CPU excluded.'),
    toolInvocations:fact(2+2*declared.length,'Fixed Git reads in final revalidation.'),
    modelCalls:fact(0,'No model adapter is called by deterministic revalidation.'),
    monetaryCost:fact(null,'Complete execution timing still requires prices and amortized costs.','unknown')};
}
export async function runPlan(raw,{approvalDigest,outputRoot=join(HERE,'corrected-runs'),stopAfter=null}={}) {
  const invokedAt=performance.now(),invokedCPU=process.cpuUsage();
  const plan=await checkedPlan(raw,approvalDigest,false), directory=join(resolve(outputRoot),plan.runId);
  await mkdir(outputRoot,{recursive:true});
  assert(!(await lstat(outputRoot)).isSymbolicLink(),'Output root cannot be a symlink.');
  await mkdir(directory,{recursive:false}).catch(error=>{if(error.code!=='EEXIST')throw error;});
  assert((await lstat(directory)).isDirectory() && !(await lstat(directory)).isSymbolicLink());
  const lock=join(directory,'writer.lock');
  try {await exclusive(lock,json({pid:process.pid,approvalDigest}));} catch(error) {
    if(error.code!=='EEXIST')throw error;
    const recoveryLock=join(directory,'recovery.lock');
    try {await exclusive(recoveryLock,json({pid:process.pid,approvalDigest}));}
    catch(recoveryError){if(recoveryError.code==='EEXIST')throw Error('Recovery already owned or interrupted; explicit operator inspection required.');throw recoveryError;}
    try {
      const previous=await loadJSON(lock);
      assert.equal(previous.approvalDigest,approvalDigest,'Existing run belongs to a different plan.');
      assert(Number.isSafeInteger(previous.pid) && previous.pid>0,'Invalid prior writer identity.');
      let alive=true;try{process.kill(previous.pid,0);}catch(probe){if(probe.code==='ESRCH')alive=false;else throw probe;}
      assert(!alive,'A writer still owns this run.');
      await rename(lock,join(directory,'interrupted-lock-'+randomUUID()+'.json'));
      await exclusive(lock,json({pid:process.pid,approvalDigest}));
    } finally {await unlink(recoveryLock);}
  }
  const attempt=randomUUID(),bounded=plan.schema==='alpha-source-assurance-plan/v3';
  const deadline=Math.min(invokedAt+plan.maxSeconds*1000,
    bounded?performance.now()+Math.max(0,Date.parse(plan.expiresAt)-Date.now()):Infinity),traces=[];
  const overhead=()=>{const used=process.cpuUsage(invokedCPU);return {stage:'recovery',kind:'invocation-validation-and-reconnect',
    wallMicroseconds:fact(Math.ceil((performance.now()-invokedAt)*1000),'Observed plan/source revalidation and recovery overhead.'),
    cpuMicroseconds:fact(used.user+used.system,'Observed Node CPU including local recovery; child Git CPU excluded.'),
    modelCalls:fact(0,'No model adapter is called by recovery.'),
    monetaryCost:fact(null,'Allocate compute and maintenance explicitly; do not erase restart costs.','unknown')};};
  const stopped=()=>{
    if(performance.now()>deadline)throw Error('Approved elapsed budget exhausted; checkpoint retained.');
    if(bounded && Date.now()>=Date.parse(plan.expiresAt))throw Error('Approved envelope expired; no renewal was made.');
    if(existsSync(join(directory,'CANCEL'))) {
      try {writeFileSync(join(directory,'CANCELLED.json'),json({schema:'alpha-source-cancellation/v1',approvalDigest,
        recordedAt:new Date().toISOString(),state:'cancelled'}),{flag:'wx',mode:0o600});}
      catch(error){if(error.code!=='EEXIST')throw error;}
    }
    if(existsSync(join(directory,'CANCELLED.json')))throw Error('Mission permanently cancelled; preserve the record and use a new approved run.');
  };
  const known=async filename=>{try{return await ordinary(join(directory,filename),8_000_000);}catch(error){if(error.code==='ENOENT')return null;throw error;}};
  const retain=async(filename,bytes)=>{
    const prior=await known(filename);
    if(prior){assert.equal(hash(prior),hash(bytes),'Existing artifact differs; retained bytes are not overwritten.');return;}
    await exclusive(join(directory,filename),bytes);
  };
  try {
    await retain('plan.json',json(plan));
    stopped();
    let authorization=null;
    if(bounded) {
      const names=(await readdir(directory)).filter(name=>name.startsWith('reservation-')).sort();
      assert(names.length<plan.maxAttempts && names.length<128,
        `Approved ${plan.maxAttempts}-attempt bound exhausted (absolute 128-attempt bound); no automatic renewal.`);
      for(let index=0;index<names.length;index++) {
        assert.equal(names[index],`reservation-${String(index+1).padStart(3,'0')}.json`,'Reservation history is not contiguous.');
        const prior=await loadJSON(join(directory,names[index]));
        assert.equal(prior.schema,'alpha-source-reservation/v1');assert.equal(prior.approvalDigest,approvalDigest);
        assert.equal(prior.ordinal,index+1);assert.equal(prior.reservedSeconds,plan.maxSeconds);
      }
      const ordinal=names.length+1,reservedSeconds=ordinal*plan.maxSeconds;
      assert(reservedSeconds<=plan.maxTotalSeconds,'Approved total execution reservation exhausted; no automatic renewal.');
      authorization={schema:'alpha-source-reservation/v1',approvalDigest,ordinal,reservedSeconds:plan.maxSeconds,
        attempt,startedAt:new Date().toISOString(),accounting:'Full attempt allowance retained, including interrupted work and reconnect.'};
      await exclusive(join(directory,`reservation-${String(ordinal).padStart(3,'0')}.json`),json(authorization));
    }
    await checkedPlan(plan,approvalDigest);
    const completed=await known('COMPLETE.json');
    if(completed){const summary=parseBounded(completed.toString());assert.equal(summary.approvalDigest,approvalDigest);
      const required=['plan.json','final-acceptance.json','report-context.json',...STAGES.map(stage=>`stage-${stage}.json`),...Object.values(OUTPUTS).flat()];
      for(const name of required)assert(Object.hasOwn(summary.artifacts,name),'Completed payload is incomplete.');
      for(const [name,digest] of Object.entries(summary.artifacts)){assert(artifactName(name),'Unsafe artifact name.');
        assert.equal(hash(await ordinary(join(directory,name),8_000_000)),digest);}
      await reverifyDelivery(directory,plan,deadline,summary.stages,stopped);
      return {...summary,reconnected:true,reconnectObservations:overhead(),...(authorization?{authorization}: {})};}
    await exclusive(join(directory,`attempt-${attempt}.json`),json({attempt,approvalDigest,state:'started',
      invocationOverhead:overhead(),monetaryCost:fact(null,'Interrupted or unfinished work is not zero.','unknown')}));
    let prepared,result,acceptance;
    for(const stage of STAGES) {
      stopped();
      if(await known('STOP'))throw Error('STOP requested; no new stage was started.');
      const prior=await known(`stage-${stage}.json`);
      if(prior){const receipt=parseBounded(prior.toString());assert.equal(receipt.approvalDigest,approvalDigest);
        assert.equal(receipt.stage,stage);assert.deepEqual(Object.keys(receipt.artifacts).sort(),[...OUTPUTS[stage]].sort());
        for(const [name,digest] of Object.entries(receipt.artifacts)){assert(artifactName(name),'Unsafe artifact name.');
          assert.equal(hash(await ordinary(join(directory,name),8_000_000)),digest);}
        traces.push(receipt);continue;}
      const wall=performance.now(),cpu=process.cpuUsage(),artifacts={};let toolInvocations=0,reportContext=null;
      const save=async(name,value)=>{stopped();const bytes=typeof value==='string'?value:json(value);await retain(name,bytes);artifacts[name]=hash(bytes);};
      if(stage==='preparation') {
        const source=committed(plan.sourceRef,plan.manifestPath,deadline);toolInvocations+=2;assert.equal(hash(source),plan.manifestSha256);
        const rows=manifestSources(source),observed=[];
        for(const [path] of rows){stopped();observed.push([path,hash(committed(plan.sourceRef,path,deadline))]);toolInvocations+=2;}
        prepared={schema:'alpha-source-assurance-inputs/v1',sourceRef:plan.sourceRef,manifestPath:plan.manifestPath,
          input:{leftCsv:guide.safeCsv([['path','sha256'],...rows]),rightCsv:guide.safeCsv([['path','sha256'],...observed]),leftKey:'path',rightKey:'path'}};
        await save('prepared-inputs.json',prepared);await save('declared-inventory.csv',prepared.input.leftCsv);
        await save('observed-inventory.csv',prepared.input.rightCsv);
      } else if(stage==='execution') {
        prepared??=await loadJSON(join(directory,'prepared-inputs.json'));result=await guide.compute(prepared.input);
        await save('result.json',result);
      } else if(stage==='verification') {
        prepared??=await loadJSON(join(directory,'prepared-inputs.json'));result??=await loadJSON(join(directory,'result.json'));
        acceptance=independentlyCheck(prepared.input,result);await save('acceptance.json',acceptance);
      } else if(stage==='correction') {
        acceptance??=await loadJSON(join(directory,'acceptance.json'));
        await save('correction.json',{decision:'report-discrepancies-without-source-mutation',changedPaths:acceptance.changedPaths,
          needsRoutineCorrection:false,limit:'The offering identifies drift; it does not decide which source is right or execute a repair.'});
      } else if(stage==='packaging') {
        prepared??=await loadJSON(join(directory,'prepared-inputs.json'));result??=await loadJSON(join(directory,'result.json'));
        await save('differences.csv',guide.fullDifferencesCsv(result));await save('action-plan.csv',guide.actionPlanCsv(result));
        await save('workspace.json',guide.makeWorkspace(prepared.input,result,{approach:'grouped',sourceHash:plan.methodIdentity,
          runId:plan.runId,createdAt:plan.createdAt,language:'en'}));
      } else if(stage==='reporting') {
        acceptance??=await loadJSON(join(directory,'acceptance.json'));
        const attemptNames=(await readdir(directory)).filter(name=>/^attempt-.*\.json$/.test(name)).sort();
        assert(attemptNames.length<=128,'Run history exhausted its 128-attempt bound; preserve it and prepare a new run.');
        let snapshot=await known('report-context.json');
        if(snapshot) snapshot=parseBounded(snapshot.toString('utf8'));
        else {
          assert(!(await known('report.md')),'An existing report has no committed reporting snapshot.');
          const attempts=[];
          for(const name of attemptNames)
            attempts.push({name,sha256:hash(await ordinary(join(directory,name)))});
          snapshot={schema:'alpha-source-report-context/v1',approvalDigest,attempt,priorStageReceipts:traces.length,attempts};
          await checkedReportContext(directory,approvalDigest,traces,snapshot);
          await retain('report-context.json',json(snapshot));
        }
        reportContext=await checkedReportContext(directory,approvalDigest,traces,snapshot);
        await save('report.md',reportMarkdown(plan,acceptance,traces,reportContext.unknownAttempts));
      }
      const used=process.cpuUsage(cpu),receipt={schema:'alpha-automated-stage/v1',stage,approvalDigest,attempt,artifacts,
        ...(reportContext?{reportContext}:{}),
        wallMicroseconds:fact(Math.ceil((performance.now()-wall)*1000),'Observed local Node elapsed stage time.'),
        cpuMicroseconds:fact(used.user+used.system,'Observed local process CPU; child Git CPU excluded.'),
        toolInvocations:fact(toolInvocations,'Fixed Git read invocations in this stage.'),modelCalls:fact(0,'No model adapter is called by this deterministic service.'),
        routineHumanMinutes:fact(0,'No operator intervention inside the automated approved local run; user decisions are separate.'),
        monetaryCost:fact(null,'Use separately sourced compute rates and allocated setup/maintenance; process timing alone is not money.','unknown')};
      await exclusive(join(directory,`stage-${stage}.json`),json(receipt));traces.push(receipt);
      if(stage===stopAfter)return {state:'checkpointed',stage,directory,approvalDigest};
    }
    const finalRevalidation=await reverifyDelivery(directory,plan,deadline,traces,stopped);
    await exclusive(join(directory,`final-revalidation-${attempt}.json`),json(finalRevalidation));
    await retain('final-acceptance.json',json({schema:'alpha-source-final-acceptance/v1',accepted:true,approvalDigest,
      sourceRef:plan.sourceRef,methodIdentity:plan.methodIdentity,check:finalRevalidation.check,authority:'none'}));
    const artifacts={};
    for(const name of (await readdir(directory)).filter(name=>!['writer.lock','COMPLETE.json'].includes(name) && artifactName(name)).sort())
      artifacts[name]=hash(await ordinary(join(directory,name),8_000_000));
    const summary={schema:'alpha-automated-source-delivery/v2',accepted:true,approvalDigest,runId:plan.runId,
      sourceRef:plan.sourceRef,methodIdentity:plan.methodIdentity,artifacts,stages:traces,finalRevalidation,
      interruptedOrUncommittedAttempts:fact((await readdir(directory)).filter(name=>/^attempt-.*\.json$/.test(name)).length-1,
        'Observed earlier unfinished attempt records; retained costs are not automatically refunded or erased.'),
      fullAgentCost:fact(null,'Execution trace is available; full monetary cost requires explicit rates/amortization.','unknown'),
      ...(authorization?{authorization}:{}),
      connectedExecution:'NOT RUN; foreground local Node only',commercialAcceptance:'unknown',authority:'none'};
    stopped();
    await exclusive(join(directory,'COMPLETE.json'),json(summary));return {...summary,directory,reconnected:false};
  } finally {await unlink(lock).catch(error=>{if(error.code!=='ENOENT')throw error;});}
}
async function main(args) {
  const command=args.shift(), options={};
  assert(['plan','run'].includes(command),'Use plan or run.');
  while(args.length){const name=args.shift(),value=args.shift();assert(['--manifest','--ref','--run-id','--approve','--plan','--stop-after',
    '--max-seconds','--max-attempts','--total-seconds','--expires-at'].includes(name) && value && !Object.hasOwn(options,name),'Unsupported or duplicate option.');options[name]=value;}
  if(command==='plan') {
    assert(Object.keys(options).every(name=>['--manifest','--ref','--run-id','--max-seconds','--max-attempts','--total-seconds','--expires-at'].includes(name)));
    const bounds={};for(const [option,field] of [['--max-seconds','maxSeconds'],['--max-attempts','maxAttempts'],['--total-seconds','maxTotalSeconds']])
      if(Object.hasOwn(options,option)){assert(/^[1-9][0-9]*$/.test(options[option]));bounds[field]=Number(options[option]);}
    if(options['--expires-at'])bounds.expiresAt=options['--expires-at'];
    const result=await makePlan({manifestPath:options['--manifest'],sourceRef:options['--ref'],runId:options['--run-id'],...bounds});
    await mkdir(join(HERE,'corrected-plans'),{recursive:true});const path=join(HERE,'corrected-plans',result.plan.runId+'.json');
    await exclusive(path,json(result.plan));await exclusive(path.replace(/\.json$/,'.facts.json'),json(result.planningFacts));
    console.log(json({...result,planFile:relative(ROOT,path)}));
  } else {
    assert(Object.keys(options).every(name=>['--plan','--approve','--stop-after'].includes(name)));
    assert(options['--plan'] && safePath(options['--plan']) && resolve(ROOT,options['--plan']).startsWith(join(HERE,'corrected-plans')+'/'),'Use a corrected plan created by this bounded CLI.');
    assert(!options['--stop-after'] || STAGES.includes(options['--stop-after']));
    const result=await runPlan((await ordinary(resolve(ROOT,options['--plan']))).toString('utf8'),
      {approvalDigest:options['--approve'],stopAfter:options['--stop-after']||null});console.log(json(result));
  }
}
if(process.argv[1] && import.meta.url===pathToFileURL(resolve(process.argv[1])).href)
  main(process.argv.slice(2)).catch(error=>{console.error('Source assurance refused: '+error.message);process.exitCode=1;});
