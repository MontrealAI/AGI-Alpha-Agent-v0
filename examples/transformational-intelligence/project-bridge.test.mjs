// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createProjectHistory,appendProjectHistory,inspectProjectHistory,prepareSummaryHandoff} from './project-bridge.mjs';
import {exactDigest} from '../successor-alpha/continuity.mjs';

const raw=readFileSync(new URL('./campaign.json',import.meta.url),'utf8');
const native=JSON.parse(raw);

test('same native campaign retains exact original bytes and uses the installed Computer Use protocol',async()=>{
    const requestRaw=JSON.stringify(native.bindings.request,null,2);
    let project=await createProjectHistory(requestRaw);
    project=await appendProjectHistory(project,'native-result',raw);
    const prepared=await prepareSummaryHandoff(project), checked=await inspectProjectHistory(prepared.projectRaw);
    assert.equal(checked.project.projectId,native.campaign_id);
    assert.equal(checked.project.history[0].raw,requestRaw);
    assert.equal(checked.project.history[1].raw,raw);
    assert.deepEqual(checked.project.history.map(e=>e.kind),['native-request','native-result','computer-handoff']);
    const handoff=JSON.parse(prepared.handoffRaw);
    assert.equal(handoff.sourceHash,await exactDigest(raw));
    assert.equal(JSON.parse(handoff.projectRaw).id,native.campaign_id);
    assert.equal(handoff.authority,'none');
    assert.deepEqual(handoff.task.allowed_urls,[]);
    assert.match(handoff.task.html,/Independent usefulness review pending/);
    assert.equal((await prepareSummaryHandoff(prepared.projectRaw)).handoffRaw,prepared.handoffRaw);
    assert.equal(await appendProjectHistory(project,'native-result',raw),project);
});

test('incomplete evidence cannot prepare a summary and forged native scores cannot enter history',async()=>{
    const project=await createProjectHistory(JSON.stringify(native.bindings.request));
    await assert.rejects(prepareSummaryHandoff(project),/completed native result/);
    const forged=structuredClone(native);forged.result.means_millionths.candidate+=1;
    await assert.rejects(appendProjectHistory(project,'native-result',JSON.stringify(forged)),/reproduced/);
    assert.equal((await inspectProjectHistory(project)).project.history.length,1);
});
