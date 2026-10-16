// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {canonical} from './journey-codec.mjs';
import {fixture} from './journey-fixture.mjs';
import {CONTEXT} from './vendor/manager-context.mjs';
import {managerContext,managerInspector,jobsOptions,receivers,managerImport} from './receivers.mjs';

test('cold owned receiver contexts cannot be mutated into a false complete source inventory',async()=>{
  const expected=structuredClone(CONTEXT);
  const edits=[
    ()=>{CONTEXT.sourceManifest.files.length=0;},
    ()=>{CONTEXT.sourceManifest.files[0].sha256='0'.repeat(64);},
    ()=>{CONTEXT.managerSource.engineSha256='0'.repeat(64);},
    ()=>{managerContext.sourceManifest={...expected.sourceManifest,files:[]};},
    ()=>{managerInspector.source={repository:'MontrealAI/AGIJobManager'};},
    ()=>{jobsOptions.managerInspector={inspect:async()=>({})};},
    ()=>{receivers.manager=async()=>({});},
  ];
  for(const edit of edits)assert.throws(edit,TypeError);
  assert.deepEqual(CONTEXT,expected);
  const native=await fixture('en','immutable-guided-context');
  const raw=await managerImport(canonical(native),'en'),read=await receivers.manager(raw);
  const source=JSON.parse(read.transfer.history[0].capsule).payload.sourceManifest;
  assert.deepEqual(source,expected.sourceManifest);assert.ok(source.files.length>0);
  read.transfer.managerSource.engineSha256='0'.repeat(64);source.files.length=0;
  assert.deepEqual(CONTEXT,expected,'parsed outputs remain detached data');
  assert.equal((await receivers.manager(raw)).transfer.managerSource.engineSha256,expected.managerSource.engineSha256);
});
