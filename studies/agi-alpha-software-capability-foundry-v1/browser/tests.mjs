// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { test } from 'node:test';
import { createWorkbench } from './vendor/alpha/examples/successor-workbench/engine.mjs';
import { createAdapter, snapshot, drift, checkFiles, OutsideScope } from './adapter.mjs';

const source=JSON.parse(await readFile(new URL('./source-manifest.json',import.meta.url)));
const example=JSON.parse(await readFile(new URL('./example-data.json',import.meta.url)));
const wb=createWorkbench([createAdapter(source.files['adapter.mjs'].sha256)]);
const spec=input=>({schema:'successor-workbench/v1',family:'software-capability-foundry',name:'Software Capability Foundry',language:'en',owner:'local-user',rights:{dataClass:'public',source:'Pinned public source',license:'Apache-2.0'},reviewMinutes:10,inputs:input});
const run=input=>wb.run(spec(input),{sourceHash:source.sourceHash});
let parent;

test('browser source closure matches exact files',async()=>{for(const [path,expected]of Object.entries(source.files)){const raw=await readFile(new URL(path,import.meta.url));assert.equal(raw.length,expected.bytes);assert.equal(createHash('sha256').update(raw).digest('hex'),expected.sha256);}});
test('A: actual public-source bytes match independent Node crypto',async()=>{const p=await run({stage:'A',files:example.mission_a,parent:null});assert.equal(p.result.decision,'VERIFIED_SNAPSHOT');assert.equal(p.result.summary.files,8);for(const f of example.mission_a)assert.equal(createHash('sha256').update(f.text).digest('hex'),f.expected);parent=p.result.evidence.instrumentId;assert.equal(p.result.summary.parentInvocations,0);assert.equal(p.evaluation.admission,'HOLD');assert.equal(p.evaluation.settlement,'NOT_CONNECTED');});
test('B: changed public portfolio invokes the retained instrument',async()=>{const p=await run({stage:'B',files:example.mission_b,parent});assert.equal(p.result.decision,'VERIFIED_SNAPSHOT');assert.equal(p.result.summary.parentInvocations,1);assert.equal(p.result.evidence.parentTrace[0].instrument,parent);});
test('C: distinct diagnostic identifies all four exact drift classes',async()=>{const old=[{path:'a',mode:'100644',text:'a'},{path:'b',mode:'100644',text:'b'},{path:'gone',mode:'100644',text:'gone'}],next=[{path:'a',mode:'100644',text:'changed'},{path:'b',mode:'100755',text:'b'},{path:'new',mode:'100644',text:'new'}];const p=await run({stage:'C',files:old,candidate:next,parent});const out=p.result.evidence.output;assert.deepEqual(out.changed,['a']);assert.deepEqual(out.missing,['gone']);assert.deepEqual(out.unexpected,['new']);assert.deepEqual(out.modeChanged,['b']);assert.equal(p.result.summary.parentInvocations,2);});
test('D: unsupported relative path produces a refusal pack',async()=>{const p=await run({stage:'D',files:[{path:'../escape',mode:'100644',text:'no'}],parent});assert.equal(p.result.decision,'REFUSED_OUT_OF_SCOPE');assert.equal(p.result.summary.bytes,0);});
test('wrong parent refuses rather than silently rebuilding',async()=>{const p=await run({stage:'B',files:example.mission_b,parent:'f'.repeat(64)});assert.equal(p.result.decision,'REFUSED_OUT_OF_SCOPE');assert.equal(p.result.summary.parentInvocations,0);});
test('source-byte mutation fails expected SHA-256',async()=>{const files=structuredClone(example.mission_a);files[0].text+='changed';const p=await run({stage:'A',files,parent:null});assert.equal(p.result.decision,'REFUSED_OUT_OF_SCOPE');});
test('symlink and gitlink modes refuse',()=>{for(const mode of ['120000','160000'])assert.throws(()=>checkFiles([{path:'x',mode,text:'x'}]),OutsideScope);});
test('absolute, dot, newline, backslash and empty paths refuse',()=>{for(const path of ['/a','a/../b','a/./b','a\nb','a\\b','a//b',''])assert.throws(()=>checkFiles([{path,mode:'100644',text:'a'}]),OutsideScope);});
test('duplicate paths refuse',()=>{assert.throws(()=>checkFiles([{path:'a',mode:'100644',text:'a'},{path:'a',mode:'100644',text:'b'}]),OutsideScope);});
test('oversize content refuses',()=>{assert.throws(()=>checkFiles([{path:'a',mode:'100644',text:'a'.repeat(1_000_001)}]),OutsideScope);});
test('snapshot output is order invariant',async()=>{const rows=[{path:'z',mode:'100644',text:'z'},{path:'a',mode:'100644',text:'a'}];assert.deepEqual(await snapshot(rows),await snapshot([...rows].reverse()));});
test('identical snapshot reports no drift',async()=>{const value=await snapshot(example.mission_a);assert.equal(drift(value,value).exact,true);});
test('STOP aborts the actual workbench path',async()=>{const control=new AbortController();await assert.rejects(wb.run(spec({stage:'A',files:example.mission_a,parent:null}),{sourceHash:source.sourceHash,signal:control.signal,onCheckpoint:async()=>control.abort()}),/CANCELLED/);});
test('workbench inspection refuses a mutated output pack',async()=>{const p=await run({stage:'A',files:example.mission_a,parent:null});p.result.summary.files=999;await assert.rejects(wb.inspectPack(p),/PACK_INTEGRITY/);});
