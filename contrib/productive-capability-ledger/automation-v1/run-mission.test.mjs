// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import {mkdtemp, readFile, writeFile, rm, readdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {spawn,execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {makePlan,runPlan} from './run-mission.mjs';

const REF='0255ebf0a3289e1011f3a8fad165baf140480241';
const source=new URL('./run-mission.mjs',import.meta.url).href;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function temporary(work){const root=await mkdtemp(join(tmpdir(),'alpha-auto-source-'));try{await work(root);}finally{await rm(root,{recursive:true,force:true});}}
const plan=id=>makePlan({manifestPath:'docs/successor/alpha/sources.json',sourceRef:REF,runId:id});

test('approved fresh scope completes all stages and a duplicate request rechecks without replacing artifacts',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('fresh-a');
    const complete=await runPlan(scope,{approvalDigest,outputRoot});
    assert.equal(complete.accepted,true);assert.equal(complete.stages.length,8);
    assert.equal(complete.fullAgentCost.value,null);
    const before=await readFile(join(outputRoot,'fresh-a','COMPLETE.json'));
    const again=await runPlan(scope,{approvalDigest,outputRoot});
    assert.equal(again.reconnected,true);assert.equal(again.reconnectObservations.modelCalls.value,0);
    assert(again.reconnectObservations.wallMicroseconds.value>0);
    assert.deepEqual(await readFile(join(outputRoot,'fresh-a','COMPLETE.json')),before);
    for(const row of complete.stages){assert.equal(row.modelCalls.value,0);assert.equal(row.monetaryCost.value,null);}
  });
});

test('exact approval, source and dependency boundaries refuse malformed scope without output',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('bad-scope');
    await assert.rejects(()=>runPlan({...scope,authority:'production'},{approvalDigest,outputRoot}));
    await assert.rejects(()=>runPlan(scope,{approvalDigest:'0'.repeat(64),outputRoot}));
    await assert.rejects(()=>makePlan({manifestPath:'../private',sourceRef:REF,runId:'bad'}));
    await assert.rejects(()=>makePlan({manifestPath:'docs/try/sources.json',sourceRef:'main',runId:'bad'}));
    assert.deepEqual(await readdir(outputRoot),[]);
  });
});

test('checkpoint interruption resumes exact committed work, and STOP retains all evidence',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('checkpoint');
    const interrupted=await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'execution'});
    assert.equal(interrupted.state,'checkpointed');
    const directory=join(outputRoot,'checkpoint'), original=await readFile(join(directory,'result.json'));
    await writeFile(join(directory,'STOP'),'');
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/STOP/);
    assert.deepEqual(await readFile(join(directory,'result.json')),original);
    await rm(join(directory,'STOP'));
    const resumed=await runPlan(scope,{approvalDigest,outputRoot});
    assert.equal(resumed.accepted,true);assert.deepEqual(await readFile(join(directory,'result.json')),original);
    assert.match(await readFile(join(directory,'report.md'),'utf8'),/2 interrupted\/uncommitted attempt/);
  });
});

test('rehashed traversal and altered saved results refuse before restoring accepted status',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('tampered');
    await runPlan(scope,{approvalDigest,outputRoot});
    const directory=join(outputRoot,'tampered'), manifest=JSON.parse(await readFile(join(directory,'COMPLETE.json'),'utf8'));
    manifest.artifacts['../outside']=sha('not-a-permitted-artifact');
    await writeFile(join(directory,'COMPLETE.json'),JSON.stringify(manifest));
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/Unsafe artifact name/);
    delete manifest.artifacts['../outside'];
    const result=JSON.parse(await readFile(join(directory,'result.json'),'utf8'));result.metrics.matchedPairs++;
    const raw=JSON.stringify(result);await writeFile(join(directory,'result.json'),raw);manifest.artifacts['result.json']=sha(raw);
    await writeFile(join(directory,'COMPLETE.json'),JSON.stringify(manifest));
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}));
  });
});

test('a rehashed uncommitted result cannot publish fabricated action CSV on its first resumed completion',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('forged-actions');
    await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'execution'});
    const directory=join(outputRoot,'forged-actions');
    const result=JSON.parse(await readFile(join(directory,'result.json'),'utf8'));
    result.resolution.actionsCsv='UNVERIFIED_ACTION_FROM_REHASHED_CHECKPOINT\n';
    const bytes=JSON.stringify(result)+'\n';await writeFile(join(directory,'result.json'),bytes);
    const stage=JSON.parse(await readFile(join(directory,'stage-execution.json'),'utf8'));
    stage.artifacts['result.json']=sha(bytes);await writeFile(join(directory,'stage-execution.json'),JSON.stringify(stage)+'\n');
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/complete recomputation/);
    assert.equal(existsSync(join(directory,'COMPLETE.json')),false);
  });
});

test('reporting checkpoint and lost final commit recover without replacing historical reports or timing receipts',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('reporting-boundary');
    await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'reporting'});
    const directory=join(outputRoot,'reporting-boundary'),historical=await readFile(join(directory,'report.md'));
    const completed=await runPlan(scope,{approvalDigest,outputRoot});assert.equal(completed.accepted,true);
    assert.equal(completed.interruptedOrUncommittedAttempts.value,1);
    assert.deepEqual(await readFile(join(directory,'report.md')),historical);
    const acceptance=await readFile(join(directory,'final-acceptance.json'));
    await rm(join(directory,'COMPLETE.json'));
    const recovered=await runPlan(scope,{approvalDigest,outputRoot});assert.equal(recovered.accepted,true);
    assert.deepEqual(await readFile(join(directory,'final-acceptance.json')),acceptance);
    assert.deepEqual(await readFile(join(directory,'report.md')),historical);
  });
});

test('Git symlink blobs are refused as source files without reading the symlink target',async()=>{
  await temporary(async outputRoot=>{
    const git=(args,input)=>execFileSync('git',args,{input,encoding:'utf8'}).trim();
    const target='../../../never-read-private-target',link=git(['hash-object','-w','--stdin'],target);
    const manifest=JSON.stringify({sources:{'fixtures/source-audit-link':sha(target)}});
    const manifestBlob=git(['hash-object','-w','--stdin'],manifest);
    const fixtures=git(['mktree'],`120000 blob ${link}\tsource-audit-link\n100644 blob ${manifestBlob}\tsource-audit-manifest.json\n`);
    const previous=git(['ls-tree',REF]).split('\n').filter(line=>!line.endsWith('\tfixtures'));
    const tree=git(['mktree'],previous.concat(`040000 tree ${fixtures}\tfixtures`).join('\n')+'\n');
    const sourceRef=git(['-c','user.name=Automation regression','-c','user.email=regression@example.invalid',
      'commit-tree',tree,'-p',REF], 'Inert symlink-mode regression fixture; no refs changed.\n');
    const {plan:scope,approvalDigest}=await makePlan({manifestPath:'fixtures/source-audit-manifest.json',sourceRef,runId:'git-link'});
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/ordinary source files with mode/);
    assert.equal(existsSync(join(outputRoot,'git-link','COMPLETE.json')),false);
  });
});

test('actual killed process releases no false completion and stale-lock recovery preserves unknown work',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('killed');
    const command=`const {runPlan}=await import(${JSON.stringify(source)});await runPlan(JSON.parse(process.argv[1]),JSON.parse(process.argv[2]));`;
    const child=spawn(process.execPath,['--input-type=module','-e',command,JSON.stringify(scope),JSON.stringify({approvalDigest,outputRoot})],{stdio:['ignore','pipe','pipe']});
    const exited=new Promise(resolve=>child.once('exit',(code,signal)=>resolve({code,signal})));
    const deadline=Date.now()+5000;
    while(!existsSync(join(outputRoot,'killed','stage-planning.json')) && Date.now()<deadline && child.exitCode===null)
      await new Promise(resolve=>setTimeout(resolve,1));
    assert(existsSync(join(outputRoot,'killed','stage-planning.json')),'Child never reached a committed planning checkpoint.');
    child.kill('SIGKILL');const end=await exited;assert.equal(end.signal,'SIGKILL');
    assert.equal(existsSync(join(outputRoot,'killed','COMPLETE.json')),false);
    const completed=await runPlan(scope,{approvalDigest,outputRoot});assert.equal(completed.accepted,true);
    assert((await readdir(join(outputRoot,'killed'))).some(name=>name.startsWith('interrupted-lock-')));
    assert.match(await readFile(join(outputRoot,'killed','report.md'),'utf8'),/1 interrupted\/uncommitted attempt/);
  });
});
