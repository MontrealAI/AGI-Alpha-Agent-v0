// SPDX-License-Identifier: Apache-2.0
import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {compilePlan} from '../../docs/assets/nova-studio/plan.mjs';
import {strictJSON} from '../../docs/assets/nova-studio/package.mjs';
import {parseNativeJSON,verifyNativeDelivery,MAX_NATIVE_BYTES} from '../../docs/assets/nova-studio/native-delivery.mjs';
import {keccak256} from '../../docs/assets/nova-studio/vendor/ethers-6.17.0.mjs';

const directory=mkdtempSync(join(tmpdir(),'nova-native-verifier-'));
after(()=>rmSync(directory,{recursive:true,force:true}));
const spec={goal:'Allocate {one,two} from budget 10 — énergie 🌱',
  successMetric:'Select both items with total cost 10 and value 18.',bounty:'100',duration:3600,priceWeight:5000};
const plan=compilePlan([spec,spec]);
const program=`
import json,sys
from pathlib import Path
from alpha_factory_v1.core.runtime.ascension import delivery,verify_delivery
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.store import Journal,digest
plan=json.load(sys.stdin)
mission=Mission.model_validate({"goal":plan["jobs"][0]["spec"]["goal"],"work":{"kind":"allocation","budget":10,"items":[{"id":"one","cost":3,"value":8},{"id":"two","cost":7,"value":10}]}})
journal=Journal.initialize(Path(sys.argv[1])/"state")
engine=Engine(journal)
record=engine.execute(journal.submit(mission)["id"])
assert record["state"]=="review" and record["result"]["cost"]==10 and record["result"]["value"]==18
engine.review(record["id"],record["revision"],digest(record["result"]),True,"Synthetic local review; not an independent real-world reviewer.")
data=delivery(journal,plan,0,record["id"])
verified=verify_delivery(data,journal.public,plan["planRoot"])
print(json.dumps({"text":data.decode(),"publicKey":journal.public,"verified":verified}))
`;
const fixture=JSON.parse(execFileSync(process.env.ALPHA_PYTHON||'python',['-c',program,directory],{
  cwd:new URL('../../',import.meta.url),input:JSON.stringify(plan),encoding:'utf8',timeout:30000,
  env:{...process.env,NO_DISCLAIMER:'1'},stdio:['pipe','pipe','pipe'],
}));
const settings={trustedPublicKey:fixture.publicKey,plan,index:0};
const bytes=new TextEncoder().encode(fixture.text);

test('real native Engine delivery verifies original bytes, signer, exact plan/index and Keccak result',async()=>{
  assert.equal(fixture.verified.valid,true);
  const result=await verifyNativeDelivery(bytes,settings);
  assert.deepEqual(result,await verifyNativeDelivery(fixture.text,settings));
  assert.equal(result.resultHash,fixture.verified.resultHash);
  assert.equal(result.resultHash,keccak256(bytes));
  assert.notEqual(result.resultHash,'0x'+createHash('sha256').update(bytes).digest('hex'));
  assert.equal(result.signer,fixture.publicKey);
  assert.equal(result.signatureVerified,true);
  assert.equal(result.connected,false);
  assert.equal(result.executionReplayed,false);
  assert.equal(Object.isFrozen(result),true);
  const timestamp=fixture.text.match(/"time_ns":([0-9]+)/)[1];
  assert.ok(BigInt(timestamp)>BigInt(Number.MAX_SAFE_INTEGER));
  assert.equal(parseNativeJSON(bytes).body.nativeExport.receipt.body.time_ns,timestamp);
  assert.throws(()=>strictJSON(fixture.text),/exact integer/);
});
test('wrong trusted signer, plan or repeated-specification index cannot validate a delivery',async()=>{
  await assert.rejects(verifyNativeDelivery(bytes,{...settings,trustedPublicKey:'00'.repeat(32)}),/signer/);
  await assert.rejects(verifyNativeDelivery(bytes,{...settings,index:1}),/plan or job index/);
  await assert.rejects(verifyNativeDelivery(bytes,{...settings,index:'0'}),/routed plan index/);
  await assert.rejects(verifyNativeDelivery(bytes,{...settings,plan:compilePlan([{...spec,goal:'Different goal'}])}),
    /plan or job index/);
});
test('changed result bytes, rounded timestamps, whitespace and BOM never preserve native authorization',async()=>{
  const tampered=fixture.text.replace('"budget":10','"budget":11');
  assert.notEqual(tampered,fixture.text);
  await assert.rejects(verifyNativeDelivery(tampered,settings),/signature/);
  const reserialized=JSON.stringify(JSON.parse(fixture.text));
  assert.notEqual(reserialized,fixture.text);
  await assert.rejects(verifyNativeDelivery(reserialized,settings),/signature|format/);
  await assert.rejects(verifyNativeDelivery(fixture.text+'\n',settings),/format/);
  await assert.rejects(verifyNativeDelivery(JSON.stringify(JSON.parse(fixture.text),null,2),settings),/compact/);
  await assert.rejects(verifyNativeDelivery(new Uint8Array([0xef,0xbb,0xbf,...bytes]),settings),/native JSON|compact/);
  await assert.rejects(verifyNativeDelivery(new Uint8Array([0xc0,0xaf]),settings),/UTF-8/);
  await assert.rejects(verifyNativeDelivery(fixture.text.replace('"state":"completed"','"state":"review"'),settings),
    /completed/);
});
test('native-only parser is bounded and rejects duplicate keys, pollution, unsafe exponents and malformed Unicode',()=>{
  assert.deepEqual(parseNativeJSON('{"time_ns":1800000000000000001,"fraction":0.25}'),
    {time_ns:'1800000000000000001',fraction:0.25});
  for(const source of ['{"a":1,"\\u0061":2}','{"__proto__":{}}','{"constructor":0}',
    '{"x":"\\ud800"}','[1e999]','[9007199254740993.0]','[9007199254740993e0]',
    '['.repeat(26)+'0'+']'.repeat(26),'true false','[1,]']) assert.throws(()=>parseNativeJSON(source));
  assert.throws(()=>parseNativeJSON('"'+'a'.repeat(MAX_NATIVE_BYTES)+'"'),/byte limit/);
});
