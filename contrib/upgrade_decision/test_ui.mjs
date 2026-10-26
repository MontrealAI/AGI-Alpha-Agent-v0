// SPDX-License-Identifier: Apache-2.0
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
const source=readFileSync(new URL('./offering.js',import.meta.url));
const ui=await import('data:text/javascript;base64,'+source.toString('base64'));
const input={schema:'alpha-upgrade-selection/v1',case_id:'native-component-refresh-development',pack_sha256:'a'.repeat(64)};
test('bounded registered selection, no endpoint or command field',()=>{
  assert.deepEqual(ui.parsePreparedInput(JSON.stringify(input)),input);
  for(const value of [{...input,command:'run'}, {...input,endpoint:'https://example.com'}, {...input,case_id:'../private'}, {...input,pack_sha256:'main'},null])
    assert.throws(()=>ui.parsePreparedInput(JSON.stringify(value)));
  assert.throws(()=>ui.parsePreparedInput(' '.repeat(32769)));
});
test('exact finite plan is understandable in both languages',()=>{
  const plan={input,expires_at:1900000000,request_seconds:60,caps:{service_work:2}};
  assert.match(ui.planSummary(plan,'en'),/Maximum attempts within this approval: 2/);
  assert.match(ui.planSummary(plan,'fr'),/Tentatives maximales/);
  assert.match(ui.planSummary(plan,'en'),/costs remain unknown/);
});
test('actual bytes must match length and digest before download',async()=>{
  const raw=new Uint8Array([80,75,3,4,1,2,3,4]);
  const digest=Buffer.from(await crypto.subtle.digest('SHA-256',raw)).toString('hex');
  const item={filename:'native-component-refresh-development.zip',mime:'application/zip',bytes:raw.length,sha256:digest,base64:Buffer.from(raw).toString('base64')};
  assert.deepEqual(await ui.checkedDownload(item),raw);
  for(const changed of [{...item,bytes:9},{...item,sha256:'0'.repeat(64)},{...item,filename:'../result.zip'},{...item,mime:'text/html'}])
    await assert.rejects(()=>ui.checkedDownload(changed));
});
