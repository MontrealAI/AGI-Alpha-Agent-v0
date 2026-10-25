// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import {mkdtemp, readFile, writeFile, rm, readdir, cp} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import childProcess,{spawn,execFileSync} from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {makePlan,runPlan} from './run-mission.mjs';
import {canonical} from '../../../examples/ti-guide/guide.mjs';

const REF=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
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

test('report publication before its stage receipt recovers with the original committed reporting context',async()=>{
  await temporary(async outputRoot=>{
    for(const published of [false,true]) {
      const {plan:scope,approvalDigest}=await plan('report-publication-'+published);
      await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'reporting'});
      const directory=join(outputRoot,scope.runId),historical=await readFile(join(directory,'report.md'));
      const context=await readFile(join(directory,'report-context.json'));
      // Simulate process loss after context publication, on either side of the report publication.
      await rm(join(directory,'stage-reporting.json'));
      if(!published)await rm(join(directory,'report.md'));
      const completed=await runPlan(scope,{approvalDigest,outputRoot});
      assert.equal(completed.accepted,true);assert.equal(completed.interruptedOrUncommittedAttempts.value,1);
      assert.deepEqual(await readFile(join(directory,'report.md')),historical);
      assert.deepEqual(await readFile(join(directory,'report-context.json')),context);
      assert.equal(completed.stages.at(-1).reportContext.unknownAttempts,0);
      assert(Object.hasOwn(completed.artifacts,'report-context.json'));
      assert.equal((await runPlan(scope,{approvalDigest,outputRoot})).reconnected,true);
    }
  });
});

test('tampered reporting context or receipt refuses completion without replacing the report',async()=>{
  await temporary(async outputRoot=>{
    for(const mutation of ['attempt-hash','approval','stage-boundary','receipt-context']) {
      const {plan:scope,approvalDigest}=await plan('report-tamper-'+mutation);
      await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'reporting'});
      const directory=join(outputRoot,scope.runId),historical=await readFile(join(directory,'report.md'));
      if(mutation==='receipt-context') {
        const receipt=JSON.parse(await readFile(join(directory,'stage-reporting.json'),'utf8'));
        receipt.reportContext.unknownAttempts++;
        await writeFile(join(directory,'stage-reporting.json'),JSON.stringify(receipt));
      } else {
        await rm(join(directory,'stage-reporting.json'));
        const context=JSON.parse(await readFile(join(directory,'report-context.json'),'utf8'));
        if(mutation==='attempt-hash')context.attempts[0].sha256='0'.repeat(64);
        if(mutation==='approval')context.approvalDigest='0'.repeat(64);
        if(mutation==='stage-boundary')context.priorStageReceipts=6;
        await writeFile(join(directory,'report-context.json'),JSON.stringify(context));
      }
      await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/Reporting/);
      assert.equal(existsSync(join(directory,'COMPLETE.json')),false);
      assert.deepEqual(await readFile(join(directory,'report.md')),historical);
    }
  });
});

test('retained reporting context does not reset the total attempt ceiling',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await makePlan({manifestPath:'docs/successor/alpha/sources.json',sourceRef:REF,
      runId:'report-attempt-ceiling',maxAttempts:128,maxTotalSeconds:2560});
    await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'reporting'});
    const directory=join(outputRoot,scope.runId),historical=await readFile(join(directory,'report.md'));
    await rm(join(directory,'stage-reporting.json'));
    // Inert started-attempt fixtures fill the same pre-existing history ceiling.
    for(let index=0;index<127;index++) {
      const attempt='00000000-0000-4000-8000-'+String(index).padStart(12,'0');
      await writeFile(join(directory,`attempt-${attempt}.json`),JSON.stringify({attempt,approvalDigest,state:'started'}));
      await writeFile(join(directory,`reservation-${String(index+2).padStart(3,'0')}.json`),JSON.stringify({
        schema:'alpha-source-reservation/v1',approvalDigest,ordinal:index+2,reservedSeconds:20,attempt,
        startedAt:new Date().toISOString(),accounting:'Inert complete reservation fixture.'}));
    }
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/128-attempt bound/);
    assert.equal(existsSync(join(directory,'COMPLETE.json')),false);
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

test('expired or not-yet-valid approval refuses before any mission directory or source execution',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await makePlan({manifestPath:'docs/successor/alpha/sources.json',sourceRef:REF,
      runId:'expired-envelope',createdAt:'2000-01-01T00:00:00.000Z'});
    assert.equal(scope.schema,'alpha-source-assurance-plan/v3');
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/expired/);
    const future=await makePlan({manifestPath:'docs/successor/alpha/sources.json',sourceRef:REF,
      runId:'future-envelope',createdAt:'2099-01-01T00:00:00.000Z'});
    await assert.rejects(()=>runPlan(future.plan,{approvalDigest:future.approvalDigest,outputRoot}),/not yet valid/);
    assert.deepEqual(await readdir(outputRoot),[]);
  });
});

test('durable reservations cap retries and reconnects without refunding interrupted work',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await makePlan({manifestPath:'docs/successor/alpha/sources.json',sourceRef:REF,
      runId:'finite-attempts',maxAttempts:2,maxTotalSeconds:40});
    await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'preparation'});
    const completed=await runPlan(scope,{approvalDigest,outputRoot});
    assert.equal(completed.accepted,true);assert.equal(completed.authorization.ordinal,2);
    const directory=join(outputRoot,scope.runId),before=await readFile(join(directory,'COMPLETE.json'));
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/attempt bound exhausted/);
    assert.deepEqual(await readFile(join(directory,'COMPLETE.json')),before);
    assert.equal((await readdir(directory)).filter(name=>name.startsWith('reservation-')).length,2);
    const reservation=JSON.parse(await readFile(join(directory,'reservation-001.json')));
    assert.equal(reservation.reservedSeconds,20);
  });
});

test('total execution reservation can exhaust before the attempt ceiling and cannot renew in place',async()=>{
  await temporary(async outputRoot=>{
    const args={manifestPath:'docs/successor/alpha/sources.json',sourceRef:REF,runId:'finite-total',maxAttempts:8,maxTotalSeconds:20};
    const {plan:scope,approvalDigest}=await makePlan(args);
    await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'planning'});
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/total execution reservation exhausted/);
    const enlarged=await makePlan({...args,maxTotalSeconds:40});
    await assert.rejects(()=>runPlan(enlarged.plan,{approvalDigest:enlarged.approvalDigest,outputRoot}),/not overwritten/);
    assert.equal(existsSync(join(outputRoot,scope.runId,'COMPLETE.json')),false);
  });
});

test('CANCEL is terminal while STOP remains a checkpoint pause; neither creates an accepted job',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('cancelled');
    await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'execution'});
    const directory=join(outputRoot,scope.runId),result=await readFile(join(directory,'result.json'));
    await writeFile(join(directory,'CANCEL'),'Cancellation by the existing host.');
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/permanently cancelled/);
    await rm(join(directory,'CANCEL'));
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/permanently cancelled/);
    assert.equal(existsSync(join(directory,'COMPLETE.json')),false);
    assert.deepEqual(await readFile(join(directory,'result.json')),result);
    assert.equal((await readdir(directory)).filter(name=>name.startsWith('reservation-')).length,1);
  });
});

test('a malformed reservation history and an interrupted recovery guard fail closed',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('corrupt-reservations');
    await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'planning'});
    const directory=join(outputRoot,scope.runId),first=JSON.parse(await readFile(join(directory,'reservation-001.json')));
    await writeFile(join(directory,'reservation-001.json'),JSON.stringify({...first,reservedSeconds:0}));
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}));
    await writeFile(join(directory,'reservation-001.json'),JSON.stringify(first));
    await writeFile(join(directory,'writer.lock'),JSON.stringify({pid:2147483647,approvalDigest}));
    await writeFile(join(directory,'recovery.lock'),'Unresolved recovery ownership.');
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/explicit operator inspection/);
    await rm(join(directory,'writer.lock'));
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/explicit operator inspection/);
    assert.equal(existsSync(join(directory,'COMPLETE.json')),false);
  });
});

test('simultaneous submissions share one immutable job and cannot duplicate its dispatch',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await plan('parallel-submit');
    const command=`const {runPlan}=await import(${JSON.stringify(source)});try{const r=await runPlan(JSON.parse(process.argv[1]),JSON.parse(process.argv[2]));console.log(JSON.stringify({accepted:r.accepted,reconnected:r.reconnected}));}catch(e){console.error(e.message);process.exitCode=1;}`;
    const invoke=()=>new Promise((resolve,reject)=>{
      const child=spawn(process.execPath,['--input-type=module','-e',command,JSON.stringify(scope),JSON.stringify({approvalDigest,outputRoot})],{stdio:['ignore','pipe','pipe']});
      let stdout='',stderr='';child.stdout.on('data',data=>stdout+=data);child.stderr.on('data',data=>stderr+=data);
      child.once('error',reject);child.once('exit',code=>resolve({code,stdout,stderr}));
    });
    const results=await Promise.all([invoke(),invoke()]);
    assert(results.some(result=>result.code===0));
    for(const result of results)if(result.code!==0)assert.match(result.stderr,/writer still owns|Recovery already owned|EEXIST/);
    const directory=join(outputRoot,scope.runId),complete=await readFile(join(directory,'COMPLETE.json'));
    assert.equal(JSON.parse(complete).accepted,true);
    const deliveries=results.filter(result=>result.code===0).map(result=>JSON.parse(result.stdout));
    assert.equal(deliveries.filter(result=>!result.reconnected).length,1);
    assert.equal((await readdir(outputRoot)).length,1);
    assert.equal((await readdir(directory)).filter(name=>name.startsWith('reservation-')).length,deliveries.length);
    assert.deepEqual(await readFile(join(directory,'COMPLETE.json')),complete);
  });
});

test('inherited Git routing cannot redirect the fixed repository source read',async()=>{
  await temporary(async outputRoot=>{
    const foreign=join(outputRoot,'unrelated.git');
    execFileSync('git',['init','--bare','--quiet',foreign]);
    const prior=process.env.GIT_DIR;process.env.GIT_DIR=foreign;
    try {
      const {plan:scope,approvalDigest}=await plan('fixed-repository');
      const result=await runPlan(scope,{approvalDigest,outputRoot});
      assert.equal(result.accepted,true);assert.equal(result.sourceRef,REF);
    } finally {if(prior===undefined)delete process.env.GIT_DIR;else process.env.GIT_DIR=prior;}
  });
});

test('a missing committed source body refuses locally without fetching or accepting partial work',async()=>{
  await temporary(async outputRoot=>{
    const git=(args,input)=>execFileSync('git',args,{input,encoding:'utf8',stdio:['pipe','pipe','pipe']}).trim();
    const body='Absent synthetic source body '+randomUUID(),missing=git(['hash-object','--stdin'],body);
    assert.throws(()=>git(['--no-lazy-fetch','cat-file','-e',missing]));
    const manifest=JSON.stringify({sources:{'fixtures/unavailable-source.txt':sha(body)}});
    const manifestBlob=git(['hash-object','-w','--stdin'],manifest);
    const fixtures=git(['mktree','--missing'],`100644 blob ${missing}\tunavailable-source.txt\n100644 blob ${manifestBlob}\tmissing-source-manifest.json\n`);
    const previous=git(['ls-tree',REF]).split('\n').filter(line=>!line.endsWith('\tfixtures'));
    const tree=git(['mktree','--missing'],previous.concat(`040000 tree ${fixtures}\tfixtures`).join('\n')+'\n');
    const sourceRef=git(['-c','user.name=Automation regression','-c','user.email=regression@example.invalid',
      'commit-tree',tree,'-p',REF],'Inert missing-object regression; no refs or repository configuration changed.\n');
    const {plan:scope,approvalDigest}=await makePlan({manifestPath:'fixtures/missing-source-manifest.json',sourceRef,runId:'missing-body'});
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/bad object|missing|Command failed/);
    assert.equal(existsSync(join(outputRoot,'missing-body','COMPLETE.json')),false);
    assert.throws(()=>git(['--no-lazy-fetch','cat-file','-e',missing]));
  });
});

test('source rebuild preserves the approved expiry between real Git reads under a controlled clock',async()=>{
  await temporary(async outputRoot=>{
    const planned=await plan('rebuild-expiry'),started=Date.now(),expiry=started+560;
    const scope={...planned.plan,expiresAt:new Date(expiry).toISOString()},approvalDigest=sha(canonical(scope));
    let utc=started,monotonic=performance.now();const calls=[];
    const originalDate=Date.now,descriptor=Object.getOwnPropertyDescriptor(performance,'now'),originalExec=childProcess.execFileSync;
    Date.now=()=>utc;Object.defineProperty(performance,'now',{configurable:true,value:()=>monotonic});
    childProcess.execFileSync=(file,args,options)=>{
      if(file!=='git')return originalExec(file,args,options);
      calls.push(utc);const result=originalExec(file,args,options);utc+=80;monotonic+=80;return result;
    };syncBuiltinESMExports();
    try {await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/elapsed budget|expired/);}
    finally {
      Date.now=originalDate;if(descriptor)Object.defineProperty(performance,'now',descriptor);else delete performance.now;
      childProcess.execFileSync=originalExec;syncBuiltinESMExports();
    }
    assert(calls.length>0);assert(calls.every(value=>value<expiry),'A new Git read started after approved expiry.');
    assert.equal(existsSync(join(outputRoot,scope.runId,'COMPLETE.json')),false);
  });
});

test('independent verifier and runner refuse truncated, duplicated or substituted reservation history',async()=>{
  await temporary(async outputRoot=>{
    const {plan:scope,approvalDigest}=await makePlan({manifestPath:'docs/try/sources.json',sourceRef:REF,runId:'verifier-coverage'});
    await runPlan(scope,{approvalDigest,outputRoot,stopAfter:'preparation'});
    await runPlan(scope,{approvalDigest,outputRoot});await runPlan(scope,{approvalDigest,outputRoot});
    const directory=join(outputRoot,scope.runId),checker=fileURLToPath(new URL('./verify-run.py',import.meta.url));
    const check=path=>JSON.parse(execFileSync('python',[checker,path],{encoding:'utf8',stdio:['ignore','pipe','pipe']}));
    assert.equal(check(directory).accepted,true);
    for(const mutation of ['truncated','duplicate','substituted','omitted-attempt']) {
      const copy=join(outputRoot,'copy-'+mutation);await cp(directory,copy,{recursive:true});
      const complete=JSON.parse(await readFile(join(copy,'COMPLETE.json'))),first=JSON.parse(await readFile(join(copy,'reservation-001.json')));
      const second=JSON.parse(await readFile(join(copy,'reservation-002.json')));
      if(mutation==='truncated') {
        await rm(join(copy,'reservation-002.json'));await rm(join(copy,'reservation-003.json'));
        delete complete.artifacts['reservation-002.json'];complete.authorization=first;
      } else if(mutation==='omitted-attempt')delete complete.artifacts[`attempt-${second.attempt}.json`];
      else {
        second.attempt=mutation==='duplicate'?first.attempt:randomUUID();const bytes=JSON.stringify(second)+'\n';
        await writeFile(join(copy,'reservation-002.json'),bytes);complete.artifacts['reservation-002.json']=sha(bytes);complete.authorization=second;
      }
      await writeFile(join(copy,'COMPLETE.json'),JSON.stringify(complete));
      assert.throws(()=>check(copy),/reservation|Reservation|attempt|Attempt/);
    }
    await rm(join(directory,'reservation-002.json'));await rm(join(directory,'reservation-003.json'));
    await assert.rejects(()=>runPlan(scope,{approvalDigest,outputRoot}),/Unreserved execution attempt/);
  });
});
