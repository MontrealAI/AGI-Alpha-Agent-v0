// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {compilePlan,verifyPlan,jobFromEditor} from '../../docs/assets/nova-studio/plan.mjs';
import {createPackage,recoverPackage,exportKit,importKit,strictJSON,fileBytes,objectHash} from '../../docs/assets/nova-studio/package.mjs';
import {PinataStorage,publishPackage,verifyPublication,artifactURI,GATEWAYS} from '../../docs/assets/nova-studio/storage.mjs';
import {QUALIFIED_PROFILES} from '../../docs/assets/ascension-wallet/qualified-profiles.mjs';
const require=createRequire(import.meta.url), reference=require('../contracts/scripts/plan.js');
const profile=JSON.parse(fs.readFileSync(new URL('../../docs/assets/ascension-wallet/profile.json',import.meta.url)));
const spec={goal:'A public, measurable task',successMetric:'Tests pass; repeatable evidence is supplied.',bounty:'100000000000000000000',duration:86400,priceWeight:6000};
const draft={title:'Private project name',description:'Private preparation details',jobs:[spec],evidence:'Public verification procedure.'};
const passphrase='capsule test passphrase only';
test('production has no qualified replacement or local write-enable profile',()=>assert.deepEqual(QUALIFIED_PROFILES,[]));
for(const count of [1,2,3,7,127,128]) test(`browser, JS and Python compiler agree at ${count} jobs`,()=>{
  const specs=Array.from({length:count},(_,i)=>({...spec,goal:`${i}: énergie 🌱`,priceWeight:i}));
  const actual=compilePlan(specs);assert.deepEqual(actual,reference.compilePlan(specs));assert.deepEqual(verifyPlan(actual),actual);
  const native=JSON.parse(execFileSync(process.env.ALPHA_PYTHON||'python',['-c',
    'import json,sys; from alpha_factory_v1.core.runtime.ascension import compile_plan; print(json.dumps(compile_plan(json.load(sys.stdin))))'],{input:JSON.stringify(specs),cwd:new URL('../../',import.meta.url),env:{...process.env,NO_DISCLAIMER:'1'}}));
  assert.deepEqual(actual,native);
});
test('numeric, Unicode, job count and exact proof boundaries',()=>{
  for(const count of [0,129])assert.throws(()=>compilePlan(Array(count).fill(spec)));
  for(const bounty of ['99','1e18','0.1','01',String(2n**96n)])assert.throws(()=>compilePlan([{...spec,bounty}]));
  assert.equal(compilePlan([{...spec,bounty:String(2n**96n-1n)}]).totalBounty,String(2n**96n-1n));
  assert.throws(()=>compilePlan([{...spec,goal:'é'.repeat(257)}]));
  assert.throws(()=>compilePlan([{...spec,goal:'\ud800'}]));
  assert.throws(()=>compilePlan([{...spec,duration:1.5}]));
  assert.throws(()=>compilePlan([{...spec,priceWeight:10001}]));
  assert.equal(jobFromEditor({...spec,bounty:'0.0000000000000001'}).bounty,'100');
  const plan=compilePlan([spec,{...spec,goal:'Second'},{...spec,goal:'Third'}]);plan.jobs[2].proof.push(plan.jobs[0].leaf);assert.throws(()=>verifyPlan(plan));
});
test('encryption binds the actual plan, recovery, whole capsule and byte hashes',async()=>{
  const pkg=await createPackage(draft,passphrase,profile), opened=await recoverPackage(pkg,passphrase,profile);
  assert.deepEqual(opened.onchain_plan,pkg.plan);assert.equal(opened.project.title,draft.title);
  assert.equal(await objectHash(pkg.capsule),pkg.capsuleHash);assert.notEqual(pkg.capsuleHash,'0x'+pkg.capsule.commitment);assert.notEqual(pkg.capsuleHash,pkg.capsuleByteHash);
  await assert.rejects(recoverPackage(pkg,'incorrect passphrase',profile));
  const changed=structuredClone(pkg);changed.plan.jobs[0].spec.goal='Altered';await assert.rejects(recoverPackage(changed,passphrase));
  const kit=await exportKit(pkg), encoded=JSON.stringify(kit);
  assert.ok(!encoded.includes(passphrase));assert.ok(!encoded.includes(draft.title));assert.ok(!encoded.includes(draft.description));
  const restored=await importKit(encoded,profile);assert.deepEqual(restored.package,pkg);
  const journal={transactions:[]}, snapshot=await exportKit(pkg,{journal});journal.transactions.push({unrelated:'later mutation'});
  assert.deepEqual((await importKit(JSON.stringify(snapshot),profile)).journal.transactions,[]);
  kit.body.seedId='999';await assert.rejects(importKit(JSON.stringify(kit),profile));
  await assert.rejects(importKit(encoded,{...profile,chainId:5}));
  const again=await createPackage(draft,passphrase,profile);assert.notEqual(again.capsuleHash,pkg.capsuleHash);
});
test('compatible capsule bounds account for proofs, Unicode and base64 overhead',async()=>{
  const pkg=await createPackage({...draft,jobs:Array.from({length:128},(_,i)=>({...spec,goal:`Job ${i}`}))},passphrase,profile);
  assert.ok(fileBytes(pkg.capsule).length<=250000);
  await assert.rejects(createPackage({...draft,jobs:Array.from({length:128},()=>({...spec,goal:'é'.repeat(256),successMetric:'é'.repeat(256)}))},passphrase,profile),/exceed/);
});
test('hostile and ambiguous JSON and unsafe references reject',()=>{
  for(const raw of ['{"x":1,"x":2}','{"x":1,"\\u0078":2}','{"__proto__":{"a":1}}','{"constructor":1}','[1e999]','[9007199254740993]','['.repeat(30)+'0'+']'.repeat(30)])assert.throws(()=>strictJSON(raw));
  for(const uri of ['ipfs://placeholder','https://example.com','javascript:alert(1)','ipfs://Qm'+'a'.repeat(44)+'/x','ipfs://Qm'+'a'.repeat(44)+'?token=secret'])assert.throws(()=>artifactURI(uri));
});
test('real adapter HTTP semantics: public multipart upload, retrieval, resume, mismatch, size and credential boundaries',async()=>{
  const pkg=await createPackage(draft,passphrase,profile), files=new Map(), calls=[];
  const fetcher=async(url,options)=>{
    calls.push({url,options});
    if(options.method==='POST'){
      assert.equal(url,'https://uploads.pinata.cloud/v3/files');assert.equal(options.body.get('network'),'public');
      assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');
      const cid='Qm'+String.fromCharCode(97+files.size).repeat(44);files.set(cid,new Uint8Array(await options.body.get('file').arrayBuffer()));
      return new Response(JSON.stringify({data:{cid}}));
    }
    assert.equal(options.headers,undefined);return new Response(files.get(url.split('/').at(-1)));
  };
  const storage=new PinataStorage(fetcher), checkpoints=[];
  const publication=await publishPackage(pkg,storage,'test-token-not-a-real-secret',p=>checkpoints.push(p));
  assert.equal(files.size,3);assert.equal(checkpoints.length,3);
  await verifyPublication(pkg,publication,storage,{independent:true});
  assert.ok(calls.some(x=>x.url.startsWith(GATEWAYS[1])));
  await publishPackage(pkg,storage,'test-token-not-a-real-secret',()=>{},publication);assert.equal(files.size,3);
  for(const bytes of files.values()){const text=new TextDecoder().decode(bytes);assert.ok(!text.includes(passphrase));assert.ok(!text.includes(draft.title));assert.ok(!text.includes('test-token-not-a-real-secret'));}
  files.set(publication.metadataURI.slice(7),new TextEncoder().encode('{}'));await assert.rejects(verifyPublication(pkg,publication,storage),/differs/);
  await assert.rejects(new PinataStorage(async()=>new Response('x'.repeat(300000))).retrieve(publication.metadataURI),/size/);
});
test('vendored ethers is byte-for-byte the locked 6.17.0 distribution',()=>{
  assert.equal(require('../contracts/node_modules/ethers/package.json').version,'6.17.0');
  assert.deepEqual(fs.readFileSync(new URL('../../docs/assets/nova-studio/vendor/ethers-6.17.0.mjs',import.meta.url)),fs.readFileSync(new URL('../contracts/node_modules/ethers/dist/ethers.min.js',import.meta.url)));
});
