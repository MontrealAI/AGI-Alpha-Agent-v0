// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const fixtures=JSON.parse(readFileSync(new URL('../../examples/ecosystem/fleet-work-vectors.json',import.meta.url),'utf8'));
for(const vector of fixtures.vectors)test(`exact Python/Node wire bytes: ${vector.kind}`,()=>{
 const raw=Buffer.from(vector.spec_base64,'base64'),{validation,result}=vector;
 assert.equal(raw.toString('base64'),vector.spec_base64);
 assert.equal('0x'+hash(raw),validation.spec_hash);
 assert.equal(result.spec_base64,vector.spec_base64);
 assert.equal(result.spec_hash,validation.spec_hash);
 assert.equal(result.canonical_mission,validation.canonical_mission);
 assert.equal(hash(Buffer.from(validation.canonical_mission,'utf8')),validation.mission_hash);
 assert.equal(result.mission_hash,validation.mission_hash);
 assert.equal(hash(Buffer.from(result.canonical_result,'utf8')),result.result_hash);
 assert.deepEqual(JSON.parse(result.canonical_result),result.result);
 assert.equal(JSON.parse(result.canonical_mission).seed,42);
 if(vector.kind==='forecast'){
  assert.match(result.canonical_mission,/0\.0,-0\.0,1\.0/);
  assert.ok(Object.is(JSON.parse(result.canonical_mission).work.observations[1],-0));
 }
});
