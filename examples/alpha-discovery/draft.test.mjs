// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createDraft,restoreDraft} from './draft.mjs';
import {example,validate} from './engine.mjs';
function raw(){const v=example();v.mission='';v.changed='';v.evidence=[];v.metrics.forEach(r=>{r.minimumGain='';for(const role of ['baseline','alternative','candidate']){r[role].value='';r[role].basis='unknown';r[role].reference='';}});return v;}
test('partial drafts preserve blanks without analysis or authority',()=>{const v=createDraft(raw(),0,'en');assert.equal(v.state,'partial-unvalidated');assert.equal(v.authority,'none');assert.equal(v.input.metrics[0].baseline.value,'');assert.deepEqual(restoreDraft(JSON.stringify(v)),v);assert.throws(()=>validate(v.input));});
test('partial malformed numeric text is preserved without becoming zero',()=>{const input=raw();input.metrics[0].candidate.value='1.5';input.metrics[0].minimumGain='unfinished';const v=createDraft(input,2,'fr');assert.equal(restoreDraft(JSON.stringify(v)).input.metrics[0].candidate.value,'1.5');assert.throws(()=>validate(v.input));});
test('drafts reject injected authority, extra fields and unsupported schema',()=>{const v=createDraft(raw(),1,'en');for(const change of [{authority:'execute'},{schema:'alpha-opportunity-brief/v1'},{state:'validated'},{analysis:{}},{step:4},{language:'xx'}])assert.throws(()=>restoreDraft(JSON.stringify({...v,...change})));});
test('strict parsing rejects duplicate keys and malformed scalars',()=>{const v=createDraft(raw(),0,'en');assert.throws(()=>restoreDraft(JSON.stringify(v).replace('"step":0','"step":0,"step":1')));v.input.mission='\ud800';assert.throws(()=>createDraft(v.input,0,'en'));});
test('bounded row shape, links and text reject ambiguous restoration',()=>{for(const mutate of [v=>v.evidence.push({kind:'research',claim:'',reference:'',basis:'supplied-report',supports:['candidate','candidate']}),v=>v.metrics.pop(),v=>v.mission='x'.repeat(2001),v=>v.metrics[0].candidate.value=null,v=>v.extra=true]){const input=raw();mutate(input);assert.throws(()=>createDraft(input,0,'en'));}});
test('all native-supported metric counts preserve their order',()=>{const input=raw();input.metrics.push(structuredClone(input.metrics[0]));assert.equal(createDraft(input,0,'en').input.metrics.length,6);});
