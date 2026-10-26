// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('./strategy.js',import.meta.url));
const {parsePreparedInput,checkedDownload,planSummary}=await import('data:text/javascript;base64,'+source.toString('base64'));

test('prepared source input has explicit fixed schema and digest',()=>{
  const value={scope_id:'public-guide',plan:{schema:'alpha-source-assurance-plan/v3'},approval_digest:'a'.repeat(64)};
  assert.deepEqual(parsePreparedInput(JSON.stringify(value)),value);
  for(const raw of ['[]','null',JSON.stringify({...value,endpoint:'https://other.example'}),JSON.stringify({...value,approval_digest:'wrong'}),' '.repeat(32769)])
    assert.throws(()=>parsePreparedInput(raw));
});
test('download requires exact SHA-256, length and bounded safe filename',async()=>{
  const bytes=Buffer.from('actual packaged customer bytes'),value={filename:'mission-1.zip',mime:'application/zip',
    bytes:bytes.length,base64:bytes.toString('base64'),sha256:createHash('sha256').update(bytes).digest('hex')};
  assert.deepEqual(Buffer.from(await checkedDownload(value)),bytes);
  for(const changed of [{...value,bytes:bytes.length+1},{...value,sha256:'a'.repeat(64)},
    {...value,filename:'../unsafe.zip'},{...value,base64:'!'},{...value,mime:'text/html'}])
    await assert.rejects(()=>checkedDownload(changed));
});

test('plain bilingual summary states exact source, expiry, attempt and full request cap',()=>{
  const plan={input:{scope_id:'public-guide',plan:{sourceRef:'a'.repeat(40),manifestPath:'docs/try/sources.json',
    sourceCount:8,expiresAt:'2026-10-26T01:00:00.000Z',maxSeconds:20}},expires_at:1792976400,request_seconds:45};
  for(const lang of ['en','fr']){const text=planSummary(plan,lang);assert(text.includes('a'.repeat(40)));
    assert(text.includes('45 s'));assert(text.includes('20 s'));assert(text.includes('2026-10-26T01:00:00.000Z'));}
  assert.equal(planSummary(null),'');
});
