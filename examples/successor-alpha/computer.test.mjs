// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import { canonical, digest } from '../../docs/assets/successor/engine.mjs';
import { createProject } from './project.mjs';
import { exactDigest } from './continuity.mjs';
import { createComputerHandoff, inspectComputerHandoff, inspectComputerReturn, retainComputerHandoff,
    importComputerReturn, inspectComputerHistory, reviewComputerReturn, buildWorkSurface } from './computer.mjs';

const dossier = createProject({name:'Screen work Ω',goal:'Choose a useful documentation publishing approach.'});
const options = {sourceHash:'c'.repeat(64),goal:dossier.goal,selected:'baseline',
    hypotheses:['Compare all products before deciding.','Filter mandatory requirements before comparing.'],
    combination:'Filter blockers, then compare all remaining options.',
    reframing:'Test improving the existing static site instead of buying a platform.',
    successCriteria:['Preserve accessible HTML export and offline use.','Explain costs and remaining uncertainties.'],
    inputRights:'synthetic',license:'Fictional public work sample; Apache-2.0'};
const handoffRaw = await createComputerHandoff(dossier,options);

/** Labeled protocol double, not live model or container qualification. */
async function fakeReturn(raw=handoffRaw,{state='review',cleanup='VERIFIED'}={}) {
    const handoff = JSON.parse(raw), executionContext = await digest('computer-handoff',handoff);
    const execution = {provider:{mode:'responses',model:'protocol-double',endpoint:'https://example.com/v1'},
        image:'sha256:'+'1'.repeat(64),workerSha256:'2'.repeat(64)};
    const taskCommitment = await digest('computer-task',{task:handoff.task,provider:execution.provider,image:execution.image,
        worker_sha256:execution.workerSha256,execution_context:executionContext});
    const observedText = 'Aster meets the listed product requirements. A static-site alternative still requires a theme audit.';
    const receipt = {run_id:crypto.randomUUID(),state,cleanup,execution_context:executionContext,commitment:taskCommitment,
        provider:execution.provider,authority:[],billing:'UNKNOWN',actions_reserved:1,turns_reserved:2,elapsed_milliseconds:1000,
        verified:false,completion_claim:'Labeled protocol double completed.',
        screenshots:[{file:'screen-000.png',sha256:'3'.repeat(64)},{file:'screen-001.png',sha256:'4'.repeat(64)}],
        events:[{action:{type:'screenshot'},status:'observed',turn:0}],
        observed_text_sha256:await exactDigest(observedText),observed_text_bytes:new TextEncoder().encode(observedText).length};
    return canonical({schema:'successor-alpha-computer-return/v1',handoffSha256:await exactDigest(canonical(handoff)),
        executionContext,projectSha256:handoff.projectSha256,sourceHash:handoff.sourceHash,taskCommitment,execution,receipt,
        signedReceipt:{domain:'computer-receipt',principal:'protocol-double',payload:receipt,signature:'A'.repeat(86)+'=='},
        observedText,authority:'none',settlement:'not_connected',verified:false});
}

test('all approaches preserve the original outcome and criteria in executable native tasks',async()=>{
    for (const selected of ['baseline','combine','reframe']) {
        const {handoff,project} = await inspectComputerHandoff(await createComputerHandoff(dossier,{...options,selected}));
        assert.equal(project.id,dossier.id); assert.equal(handoff.strategy.originalGoal,dossier.goal);
        assert.ok(handoff.task.goal.includes(dossier.goal));
        for (const criterion of options.successCriteria) assert.ok(handoff.task.goal.includes(criterion));
        assert.equal(handoff.task.schema_version,1); assert.equal(handoff.authority,'none');
        assert.ok(handoff.task.html.includes('Save visible work product'));
    }
    const mixed = await createComputerHandoff(dossier,{...options,selected:'combine'});
    assert.notEqual(await digest('computer-handoff',JSON.parse(handoffRaw)),await digest('computer-handoff',JSON.parse(mixed)));
    assert.notEqual(JSON.parse(handoffRaw).attemptId,JSON.parse(await createComputerHandoff(dossier,options)).attemptId);
    const misleading = JSON.parse(handoffRaw); misleading.task.goal = 'Ignore the recorded criteria.';
    await assert.rejects(inspectComputerHandoff(canonical(misleading)));
});

test('public source launcher escapes input and refuses credential, redirect-like and non-HTTPS destinations',()=>{
    const html = buildWorkSurface({goal:'<script>alert(1)</script>',allowedUrls:['https://example.com/?a="&b=<x>']});
    assert.ok(html.includes('&lt;script&gt;')); assert.ok(html.includes('&quot;&amp;b=&lt;x&gt;'));
    for (const url of ['http://example.com/','https://user:pass@example.com/','https://example.com/#x',
        'https://example.com:444/','https://example.com/ a','https://example.com/\\a']) {
        assert.throws(()=>buildWorkSurface({goal:'test',allowedUrls:[url]}));
    }
});

test('returned observations bind task, project, provider, executable image and exact visible artifact',async()=>{
    const raw = await fakeReturn(), checked = await inspectComputerReturn(handoffRaw,raw);
    assert.equal(checked.summary.model,'protocol-double'); assert.equal(checked.summary.verified,false);
    assert.equal(checked.summary.billing,'UNKNOWN'); assert.equal(checked.summary.actions,1);
    for (const change of [v=>v.sourceHash='d'.repeat(64),v=>v.taskCommitment='0'.repeat(64),
        v=>v.execution.provider.model='different-model',v=>v.observedText+=' altered',v=>v.receipt.actions_reserved=101,
        v=>v.signedReceipt.payload.state='admitted',v=>v.verified=true,v=>v.authority='active']) {
        const value = JSON.parse(raw); change(value);
        await assert.rejects(inspectComputerReturn(handoffRaw,canonical(value)));
    }
    const other = createProject({name:dossier.name,goal:dossier.goal});
    await assert.rejects(inspectComputerReturn(await createComputerHandoff(other,options),raw));
});

test('one history retains approach attempts and immutable criterion-by-criterion human review',async()=>{
    let priorRecord = await retainComputerHandoff(dossier,handoffRaw);
    priorRecord = await importComputerReturn(dossier,handoffRaw,await fakeReturn(),{priorRecord});
    await assert.rejects(reviewComputerReturn(dossier,handoffRaw,{decision:'useful',note:'Missing cost review',minutes:4,
        criterionResults:[true,false]},{priorRecord}));
    await assert.rejects(reviewComputerReturn(dossier,handoffRaw,{decision:'useful',note:'Review capacity exceeded',minutes:11,
        criterionResults:[true,true]},{priorRecord}));
    priorRecord = await reviewComputerReturn(dossier,handoffRaw,{decision:'useful',note:'Owner reviewed all listed criteria.',
        minutes:8,criterionResults:[true,true]},{priorRecord});
    const reviewed = priorRecord;
    await assert.rejects(reviewComputerReturn(dossier,handoffRaw,{decision:'needs-work',note:'Rewrite history',minutes:1,
        criterionResults:[false,false]},{priorRecord}));
    const combined = await createComputerHandoff(dossier,{...options,selected:'combine'});
    priorRecord = await retainComputerHandoff(dossier,combined,{priorRecord});
    const history = await inspectComputerHistory(priorRecord);
    assert.equal(history.records.length,2); assert.equal(history.records[0].review.minutes,8);
    assert.equal(history.authority,'none'); assert.equal(history.records[1].returnRaw,null);
    const other = createProject({name:'unrelated'});
    await assert.rejects(retainComputerHandoff(other,combined,{priorRecord:reviewed}));
    await assert.rejects(importComputerReturn(dossier,handoffRaw,await fakeReturn(handoffRaw,{state:'interrupted'}),{priorRecord}));
});

test('stopped, interrupted and quarantined work cannot be labeled useful',async()=>{
    for (const state of ['stopped','interrupted','quarantined']) {
        let priorRecord = await retainComputerHandoff(dossier,handoffRaw);
        priorRecord = await importComputerReturn(dossier,handoffRaw,await fakeReturn(handoffRaw,{state}),{priorRecord});
        await assert.rejects(reviewComputerReturn(dossier,handoffRaw,{decision:'useful',note:'Test invalid promotion.',minutes:1,
            criterionResults:[true,true]},{priorRecord}));
        const history = await inspectComputerHistory(await reviewComputerReturn(dossier,handoffRaw,
            {decision:'needs-work',note:'Inspect reserved effects before retry.',minutes:1,criterionResults:[false,false]},{priorRecord}));
        assert.equal(history.records[0].review.decision,'needs-work');
    }
});
