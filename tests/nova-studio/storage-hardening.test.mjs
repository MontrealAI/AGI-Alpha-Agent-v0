// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {PinataStorage,publishPackage,verifyPublication} from '../../docs/assets/nova-studio/storage.mjs';
import {createPackage,recoverPackage,verifyPackage,exportKit,importKit,deploymentIdentityStatus,
  profileIdentity,objectHash,fileBytes,hashBytes,PACKAGE_SCHEMA} from '../../docs/assets/nova-studio/package.mjs';
import {sealSeed,openSeed} from '../../docs/assets/ascension/crypto.mjs';
import {compilePlan} from '../../docs/assets/nova-studio/plan.mjs';
import {TOKEN} from '../../docs/assets/ascension-wallet/protocol.mjs';

const cid='Qm'+'a'.repeat(44),uri='ipfs://'+cid,credential='synthetic-not-a-real-storage-credential';
const profile={chainId:31337,profile:'fixture-exact-source',sourceSHA256:'a'.repeat(64),abiSHA256:'b'.repeat(64),
  genesisHash:'0x'+'1'.repeat(64),contracts:{Seed:{address:'0x'+'11'.repeat(20),sha256:'c'.repeat(64)}}};
const spec={goal:'Synthetic bounded task',successMetric:'Result is 18',bounty:'100',duration:3600,priceWeight:5000};
const draft={title:'Private fixture',description:'Private preparation',jobs:[spec],evidence:'Synthetic public evidence',parent:'7'};
const phrase='local capsule test passphrase outside every artifact';
const pkg=await createPackage(draft,phrase,profile);

test('storage transport keeps the global receiver required by native browser fetch',async()=>{
  const receiver=function(){assert.equal(this,globalThis);return Promise.resolve(new Response('{}'));};
  assert.deepEqual((await new PinataStorage(receiver).retrieve(uri)).object,{});
  assert.throws(()=>new PinataStorage(null),/transport/);
});
test('transport errors and malformed provider responses cannot echo upload credentials',async()=>{
  for(const fetcher of [async()=>{throw Error('Provider echoed '+credential);},
    async()=>new Response(credential),async()=>new Response('x'.repeat(33000))]) {
    await assert.rejects(new PinataStorage(fetcher).publish({},'fixture.json',credential),error=>
      error.message.startsWith('Storage upload failed.')&&!error.message.includes(credential));
  }
});
test('storage refuses redirects, changed response destinations and unbounded readback limits',async()=>{
  for(const field of [{redirected:true},{url:'https://unreviewed.example/ipfs/'+cid}]) {
    const response=new Response('{}');for(const [key,value] of Object.entries(field))Object.defineProperty(response,key,{value});
    await assert.rejects(new PinataStorage(async()=>response).retrieve(uri),/Storage retrieval failed/);
  }
  const storage=new PinataStorage(async()=>new Response('{}'));
  for(const maximum of [0,2000001,Infinity,1.5])await assert.rejects(storage.retrieveBytes(uri,undefined,maximum),/size limit/);
});
test('publication retains completed checkpoints and verifies both reviewed gateways after interruption',async()=>{
  const files=new Map(),reads=[],uploads=[];let failEvidence=true;
  const storage=new PinataStorage(async(url,options)=>{
    if(options.method==='POST') {
      const file=options.body.get('file');uploads.push(file.name);
      if(file.name==='nova-evidence.json'&&failEvidence){failEvidence=false;throw Error('Synthetic interruption');}
      const id='Qm'+String.fromCharCode(97+files.size).repeat(44);
      files.set(id,new Uint8Array(await file.arrayBuffer()));return new Response(JSON.stringify({data:{cid:id}}));
    }
    reads.push(url);return new Response(files.get(url.split('/').at(-1)));
  });
  let checkpoint=null;
  await assert.rejects(publishPackage(pkg,storage,credential,value=>{checkpoint=value;}),/Storage upload failed/);
  assert.ok(checkpoint.capsuleURI);assert.equal(checkpoint.evidenceURI,undefined);
  const publication=await publishPackage(pkg,storage,credential,()=>{},checkpoint);
  assert.equal(uploads.filter(name=>name==='nova-capsule.json').length,1);
  await verifyPublication(pkg,publication,storage,{independent:true});
  assert.ok(reads.some(url=>url.startsWith('https://ipfs.io/ipfs/')));
});
test('new encrypted packages bind immutable source/code identity while qualification can renew',async()=>{
  assert.equal(deploymentIdentityStatus(pkg,profile),'exact-source');
  const opened=await openSeed(pkg.capsule,phrase);
  assert.deepEqual(opened.deployment,profileIdentity(profile));
  assert.equal(opened.evidenceHash,pkg.evidenceHash);assert.equal(opened.parent,'7');
  const renewal={...profile,stage:'public',validUntil:'1900000000',qualification:{evidence:'updated'}};
  await recoverPackage(pkg,phrase,renewal);
  for(const field of ['sourceSHA256','abiSHA256','genesisHash']) {
    const changed={...profile,[field]:'d'.repeat(64)};
    await assert.rejects(verifyPackage(pkg,changed),/source identity/);
  }
  const changed=structuredClone(profile);changed.contracts.Seed.sha256='e'.repeat(64);
  await assert.rejects(verifyPackage(pkg,changed),/source identity/);
});
test('legacy address-only recovery remains readable without relabeling its original commitments',async()=>{
  const deployment={chainId:profile.chainId,profile:profile.profile,
    contracts:{Token:TOKEN.toLowerCase(),Seed:profile.contracts.Seed.address.toLowerCase()}};
  const plan=compilePlan(draft.jobs),evidence={schema:'agialpha.nova-studio.evidence.v1',deployment,
    planRoot:plan.planRoot,description:draft.evidence};
  const evidenceHash=await objectHash(evidence);
  const capsule=await sealSeed({schema:'agialpha.novaseed.genome.v1',project:{title:draft.title,description:draft.description},
    deployment,onchain_plan:plan,evidenceHash,parent:'7'},phrase);
  const legacy={schema:PACKAGE_SCHEMA,deployment,capsule,plan,evidence,capsuleHash:await objectHash(capsule),
    capsuleByteHash:await hashBytes(fileBytes(capsule)),evidenceHash,parent:'7'};
  const before=JSON.stringify(legacy);
  assert.equal(deploymentIdentityStatus(legacy,profile),'legacy-addresses');
  await recoverPackage(legacy,phrase,profile);
  const restored=await importKit(JSON.stringify(await exportKit(legacy)),profile);
  assert.deepEqual(restored.package,legacy);assert.equal(JSON.stringify(legacy),before);
  assert.equal(deploymentIdentityStatus(restored.package,profile),'legacy-addresses');
});
