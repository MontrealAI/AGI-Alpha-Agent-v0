// SPDX-License-Identifier: Apache-2.0
// Disposable in-process Hardhat only. The qualified registry is built in a TEMP COPY.
// No local profile or test provider is shipped in production browser assets.
const {ethers,network,artifacts}=require('hardhat');
const {fixture,spec,now,jump}=require('./fixture');
const {requireDisposableLocalNetwork}=require('./disposable');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),http=require('node:http');
const {createHash}=require('node:crypto'),{spawn,execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../..'),out=path.resolve(process.env.NOVA_EVIDENCE||path.join(root,'evidence/nova-studio'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const serialize=x=>JSON.stringify(x,(_,v)=>typeof v==='bigint'?String(v):v,2)+'\n';
function native(args, input) {
  return JSON.parse(execFileSync(process.env.ALPHA_PYTHON||'python3',
    [path.join(root,'tests/nova-studio/native_fixture.py'),...args],
    {cwd:root,env:{...process.env,PYTHONPATH:root,NO_DISCLAIMER:'1'},input:JSON.stringify(input),
      encoding:'utf8',timeout:30000,stdio:['pipe','pipe','pipe']}));
}
function receiptSummary(receipt) {
  assert.equal(receipt.status,'0x1');
  return Object.fromEntries(['status','transactionHash','blockHash','blockNumber','from','to'].map(key=>[key,receipt[key]]));
}
function cid(bytes) {
  const source=Buffer.concat([Buffer.from([1,85,18,32]),createHash('sha256').update(Buffer.from(bytes)).digest()]);
  let bits=0,value=0,result='b';const alphabet='abcdefghijklmnopqrstuvwxyz234567';
  for(const byte of source){value=(value<<8)|byte;bits+=8;while(bits>=5){result+=alphabet[(value>>>(bits-5))&31];bits-=5;}}
  if(bits)result+=alphabet[(value<<(5-bits))&31];return result;
}
async function main(){
  await requireDisposableLocalNetwork();
  const sourceFiles=['docs/ascension/mainnet/index.html','docs/ascension-protocol/mainnet/index.html',
    'docs/assets/successor/engine.mjs',
    'tests/contracts/scripts/nova-studio.js','tests/nova-studio/browser.py','tests/nova-studio/browser-provider.js',
    'tests/nova-studio/native_fixture.py','tests/contracts/contracts/ascension/NovaPlanProofHarness.sol'];
  for(const folder of ['docs/assets/nova-studio','docs/assets/ascension-wallet','docs/assets/ascension','contracts/ascension'])
    for(const file of fs.readdirSync(path.join(root,folder),{recursive:true}))
      if(fs.statSync(path.join(root,folder,file)).isFile())sourceFiles.push(folder+'/'+file);
  const testedSourceHashes=Object.fromEntries(sourceFiles.sort().map(file=>[file,sha(fs.readFileSync(path.join(root,file)))]));
  const f=await fixture(),temp=fs.mkdtempSync(path.join(os.tmpdir(),'nova-studio-'));
  fs.mkdirSync(out,{recursive:true});
  for(const folder of ['ascension','ascension-wallet','nova-studio','successor'])fs.cpSync(path.join(root,'docs/assets',folder),path.join(temp,'assets',folder),{recursive:true});
  fs.cpSync(path.join(root,'docs/ascension/mainnet'),path.join(temp,'ascension/mainnet'),{recursive:true});
  const {ACTIONS,CONTRACTS}=await import(path.join(root,'docs/assets/ascension-wallet/protocol.mjs'));
  const {canonicalProfile}=await import(path.join(root,'docs/assets/ascension-wallet/client.mjs'));
  const {qualificationIdentity}=await import(path.join(root,'docs/assets/ascension-wallet/qualification.mjs'));
  const sourceHashes={},compilerBuilds={};
  for(const name of ['AscensionAccess','NovaSeed','AscensionRiskOracle','AscensionJobMarket','AscensionMark']) {
    const artifact=await artifacts.readArtifact(name), build=await artifacts.getBuildInfo(`${artifact.sourceName}:${name}`);
    assert.ok(build,`Missing exact compiler input for ${name}`);
    assert.equal(build.solcVersion,require('./compiler-policy').SOLC_VERSION);
    assert.deepEqual(build.input.settings.optimizer,{enabled:true,runs:200});
    assert.equal(build.input.settings.viaIR,true);assert.equal(build.input.settings.evmVersion,'cancun');
    for(const [file,input] of Object.entries(build.input.sources)) {
      if(!file.startsWith('contracts/ascension/') || !fs.existsSync(path.join(root,file)))continue;
      assert.equal(input.content,fs.readFileSync(path.join(root,file),'utf8'),`Stale compiled source: ${file}`);
      assert.equal(input.content,fs.readFileSync(path.join(root,'tests/contracts',file),'utf8'),`Divergent fixture: ${file}`);
      sourceHashes[file]=sha(Buffer.from(input.content));
    }
    compilerBuilds[name]={source:artifact.sourceName,solcVersion:build.solcVersion,
      inputSHA256:sha(JSON.stringify(build.input)),settings:build.input.settings};
  }
  const sourceSHA256=sha(canonicalProfile({sources:sourceHashes,compilerBuilds}));
  const contracts={};
  for(const [key,contract] of Object.entries({Access:f.access,Seed:f.seed,Oracle:f.oracle,Jobs:f.jobs,Mark:f.mark,Token:f.token}))
    contracts[key]={address:contract.target,sha256:sha(Buffer.from((await ethers.provider.getCode(contract.target)).slice(2),'hex'))};
  const actors=[f.business,f.funder,f.agent,...f.validators].map(s=>s.address.toLowerCase());
  const genesis=await network.provider.request({method:'eth_getBlockByNumber',params:['0x0',false]});
  const deployment=await network.provider.request({method:'eth_getBlockByNumber',params:['latest',false]});
  const profile={schema:'agialpha.nova-local-profile.v1',chainId:31337,profile:'disposable-exact-source-nova-studio',
    environment:'local-exact-source',mainnetQualification:false,newExposureEnabled:true,contracts,actions:Object.keys(ACTIONS),
    sourceSHA256,abiSHA256:sha(qualificationIdentity()),genesisHash:genesis.hash,
    deploymentBlock:deployment.number,deploymentBlockHash:deployment.hash,
    dependencies:[],authorities:['Access','Oracle','Jobs'].map(contract=>({contract,owner:f.governor.address})),
    evidence:{classification:'exact-source-local-with-mock-external-dependencies',sourceHashes,notMainnet:true}};
  for(const contract of [f.ens,f.wrapper])profile.dependencies.push({address:contract.target,sha256:sha(Buffer.from((await ethers.provider.getCode(contract.target)).slice(2),'hex')),slots:[]});
  const registryEntry=p=>({canonicalJSON:canonicalProfile(p),sha256:sha(canonicalProfile(p)),stage:'local'});
  const writeRegistry=(directory,p)=>fs.writeFileSync(path.join(directory,'assets/ascension-wallet/qualified-profiles.mjs'),
    `export const QUALIFIED_PROFILES=Object.freeze(${JSON.stringify([registryEntry(p)])});\n`);
  writeRegistry(temp,profile);
  fs.writeFileSync(path.join(temp,'assets/ascension-wallet/profile.json'),serialize(profile));
  const {WalletSession}=await import(path.join(temp,'assets/ascension-wallet/session.mjs'));
  const {NovaWorkflow}=await import(path.join(temp,'assets/nova-studio/workflow.mjs'));
  const {PinataStorage}=await import(path.join(temp,'assets/nova-studio/storage.mjs'));
  const {compilePlan}=await import(path.join(temp,'assets/nova-studio/plan.mjs'));
  const {strictJSON,hashBytes}=await import(path.join(temp,'assets/nova-studio/package.mjs'));
  const files=new Map(),events=[];
  function publish(bytes){const key=cid(bytes);files.set(key,Buffer.from(bytes));return key;}
  const storage=new PinataStorage(async(url,options)=>{
    if(options.method==='POST')return new Response(JSON.stringify({data:{cid:publish(await options.body.get('file').arrayBuffer())}}));
    const bytes=files.get(url.split('/').at(-1));return new Response(bytes||'',{status:bytes?200:404});
  });
  const map=new Map(),store={getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v)},locks={request:async(_name,_options,fn)=>fn({name:'test-node-lock'})};
  const freshStore=()=>{const saved=new Map();return {getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v)};};
  const session=new WalletSession(profile,store,locks),flow=new NovaWorkflow(session,storage);
  let transformRPC=null;
  async function choose(signer){session.client.select({request:async({method,params=[]})=>{
    if(method==='eth_accounts'||method==='eth_requestAccounts')return [signer.address];
    if(method==='eth_sendTransaction')assert.equal(params[0].from.toLowerCase(),signer.address.toLowerCase());
    const result=await network.provider.request({method,params});
    return transformRPC?transformRPC(method,params,result):result;
  }});await session.client.connect();}
  async function action(name,input={}){
    const preview=await flow.prepare(name,input);assert.equal(preview.transaction.value,'0x0');
    const hash=await flow.confirm(true),record=await flow.reconcile(hash);assert.equal(record.status,'finalized');
    events.push({action:name,hash,status:record.status,receipt:receiptSummary(record.receipt)});return record;
  }
  const sizes=[1,2,3,7,127,128],specifications=sizes.map(count=>Array.from({length:count},(_,i)=>({...spec,
    goal:`Job ${i} — énergie α 🚀`,bounty:i===count-1?(2n**96n-1n).toString():(100n+BigInt(i)).toString(),
    duration:i%2?90*86400:1,priceWeight:i%2?10000:0})));
  const nativePlans=native(['--compile-plans'],specifications), proofHarness=await (await ethers.getContractFactory('NovaPlanProofHarness')).deploy();
  await proofHarness.waitForDeployment();
  let proofsVerified=0;
  for(const [i,specs] of specifications.entries()){
    const plan=compilePlan(specs);assert.deepEqual(plan,require('./plan').compilePlan(specs));assert.deepEqual(plan,nativePlans[i]);
    for(const j of plan.jobs){assert.equal(j.leaf,await f.jobs.hashSpec(j.index,j.spec));
      assert.equal(await proofHarness.verify(j.proof,plan.planRoot,j.leaf),true);
      assert.equal(await proofHarness.verify(j.proof,plan.planRoot,ethers.id('altered leaf')),false);proofsVerified++;}
    if([3,7,127].includes(specs.length))assert.ok(plan.jobs.at(-1).proof.length<plan.jobs[0].proof.length);
  }
  await choose(f.business);
  await flow.create({title:'Private exact-source acceptance',description:'Must not appear in uploaded artifacts.',jobs:[spec,spec],evidence:'Synthetic local acceptance, not an independent real-world review.'},'local test capsule passphrase');
  const initialKit=await flow.kit();await flow.publish('synthetic-local-storage-token',true);
  const identity=await flow.chain.identity();assert.equal(identity.eligible,true);
  await flow.prepare('seal');await choose(f.funder);
  await assert.rejects(flow.confirm(true),/fresh action|context|preview/i);
  assert.equal(await f.seed.nextId(),0n);
  await choose(f.business);await flow.prepare('seal');const mintHash=await flow.confirm(true);
  const sealedTopic=f.seed.interface.getEvent('SeedSealed').topicHash;
  transformRPC=(method,params,result)=>{
    if(method!=='eth_getTransactionReceipt'||params[0]!==mintHash||!result)return result;
    const actual=result.logs.find(log=>log.topics?.[0]===sealedTopic);
    return {...result,logs:[...result.logs.filter(log=>log.topics?.[0]!==sealedTopic),{...actual,address:f.outsider.address}]};
  };
  await assert.rejects(flow.reconcile(mintHash),/matching SeedSealed/);
  assert.equal(flow.client.pending.status,'effect-unverified');assert.equal(flow.seedId,null);assert.equal(flow.observation,null);
  const barrier=new WalletSession(profile,freshStore(),locks);barrier.client.restore(flow.client.journal());
  assert.equal(barrier.client.pending.status,'effect-unverified');
  await assert.rejects(flow.prepare('seal'),/outstanding|unresolved|reconcile/i);
  transformRPC=null;const mint=await flow.reconcile(mintHash);
  assert.equal(mint.status,'finalized');events.push({action:'seal',hash:mint.hash,status:mint.status,receipt:receiptSummary(mint.receipt)});
  assert.equal(flow.seedId,'1');assert.equal(mint.transaction.to.toLowerCase(),f.seed.target.toLowerCase());
  assert.equal(mint.args[0],flow.package.capsuleHash);assert.equal(mint.args[1],flow.package.plan.planRoot);
  const opened=await flow.chain.openMintReceipt(mint.hash,flow.package);assert.equal(opened.seedId,'1');
  // A later receipt recheck must repeat semantic verification even when the
  // same block previously finalized. Old success cannot bless missing effects.
  transformRPC=(method,params,result)=>method==='eth_getTransactionReceipt'&&params[0]===mintHash&&result?
    {...result,logs:result.logs.filter(log=>log.topics?.[0]!==sealedTopic)}:result;
  await assert.rejects(flow.reconcile(mintHash),/matching SeedSealed/);
  assert.equal(flow.client.pending.status,'effect-unverified');assert.equal(flow.observation,null);
  await assert.rejects(flow.prepare('openReview'),/outstanding|unresolved|reconcile/i);
  assert.equal(flow.observation,null);
  transformRPC=null;await flow.reconcile(mintHash);
  await action('openReview');
  await assert.rejects(flow.prepare('attest',{risk:'1000',approved:'true',reviewed:true,findings:'self review'}),/creator|owner/);
  for(const reviewer of f.validators.slice(0,2)){await choose(reviewer);await action('attest',{risk:'1000',approved:'true',reviewed:true,findings:'Local test review by distinct fixture signer; not independent humans.'});}
  assert.equal((await flow.inspect()).green,true);
  await choose(f.business);await action('open',{base:'1',slope:'0',maxLots:'1000',target:'100',fundingHours:'24',executionDays:'14'});
  await choose(f.funder);await f.token.connect(f.funder).approve(f.mark.target,0);
  await assert.rejects(flow.prepare('buy',{count:'100',limit:'100'}),/approval/);
  await action('approveFunding',{count:'100',limit:'100'});await action('buy',{count:'100',limit:'100'});
  await choose(f.business);await assert.rejects(flow.prepare('bloom',{irreversible:false}),/Acknowledge/);await action('bloom',{irreversible:true});
  await assert.rejects(flow.prepare('route',{index:'0',auction:'60',reviewers:[f.validators[0].address,f.validators[0].address,f.validators[2].address]}),/distinct/);
  await action('route',{index:'0',auction:'60',reviewers:f.committee});assert.equal(flow.jobIds[0],'1');
  await assert.rejects(flow.prepare('route',{index:'0',auction:'60',reviewers:f.committee}),/already posted/);
  const work=await flow.workPackage('1');assert.equal(work.runtime.status,'not-connected');assert.equal(work.job.spec.bounty,spec.bounty);assert.equal(work.job.index,0);
  await choose(f.agent);
  await assert.rejects(flow.prepare('bid',{jobId:'1',price:'80',duration:String(spec.duration)}),/shorter/);
  await assert.rejects(flow.prepare('submit',{jobId:'1',result:'0x'+'11'.repeat(32),uri:'ipfs://not-delivered'}),/awarded worker/);
  await action('bid',{jobId:'1',price:'80',duration:'3600'});
  await jump((await f.jobs.jobs(1)).auctionEnd);await action('award',{jobId:'1'});
  const genericHash=await hashBytes(Buffer.from('local generic result bytes'));
  await assert.rejects(flow.prepare('submit',{jobId:'1',result:genericHash,uri:'ipfs://'+publish(Buffer.from('wrong result bytes'))}),/Published result bytes/);
  const nativeDelivery=native([path.join(out,'local-native-delivery.json')],flow.package.plan);
  const nativeBytes=fs.readFileSync(path.join(out,nativeDelivery.artifact)),resultHash=ethers.keccak256(nativeBytes);
  assert.equal(resultHash,nativeDelivery.resultHash);assert.equal(sha(nativeBytes),nativeDelivery.byteSHA256);
  await assert.rejects(flow.importNativeDelivery(nativeBytes,{trustedPublicKey:'00'.repeat(32),jobId:'1'}),/signer|signature|trusted/i);
  await assert.rejects(flow.importNativeDelivery(Buffer.from(JSON.stringify(JSON.parse(nativeBytes))),
    {trustedPublicKey:nativeDelivery.signer,jobId:'1'}),/signature|canonical|exact|integer/i);
  const imported=await flow.importNativeDelivery(nativeBytes,{trustedPublicKey:nativeDelivery.signer,jobId:'1'});
  assert.equal(imported.resultHash,resultHash);assert.equal(imported.signatureVerified,true);assert.equal(imported.connected,false);
  await assert.rejects(flow.prepare('submit',{jobId:'1',result:resultHash,uri:'ipfs://'+publish(Buffer.from('wrong result bytes')),native:true}),/native|JSON|exact|signature/i);
  await action('submit',{jobId:'1',result:resultHash,uri:'ipfs://'+publish(nativeBytes),native:true});
  async function balances(seedId){return {worker:String(await f.token.balanceOf(f.agent.address)),
    validator1:String(await f.token.balanceOf(f.validators[0].address)),validator2:String(await f.token.balanceOf(f.validators[1].address)),
    supply:String(await f.token.totalSupply()),markReserve:String((await f.mark.campaigns(seedId)).reserve)};}
  function accounting(before,after,jobId){
    const delta=Object.fromEntries(Object.keys(before).map(key=>[key,String(BigInt(after[key])-BigInt(before[key]))]));
    const expected=Object.fromEntries(Object.entries({worker:'75.24',validator1:'1.98',validator2:'1.98',supply:'-0.8',markReserve:'0'})
      .map(([key,value])=>[key,String(ethers.parseEther(value))]));
    assert.deepEqual(delta,expected);return {jobId,before,after,delta,expected,burned:String(-BigInt(delta.supply)),confirmed:true};
  }
  const beforeSettlement=await balances('1');
  for(const reviewer of f.validators.slice(0,2)){await choose(reviewer);await action('validate',{jobId:'1',result:resultHash,approved:'true',reviewed:true,findings:'Synthetic local acceptance result inspected by fixture signer.'});}
  assert.equal((await f.jobs.jobs(1)).state,4n);
  assert.equal((await f.jobs.jobs(1)).resultHash,resultHash);
  assert.equal((await flow.chain.inspectJob('1','1',flow.package)).job.settlementConfirmed,true);
  const settlement=accounting(beforeSettlement,await balances('1'),'1');
  await choose(f.business);await action('collect',{jobId:'1'});
  await assert.rejects(flow.prepare('close'),/missions still open/);
  // This partial-budget campaign has a second identical, unposted job. Resolve
  // closure only after its real contract deadline; no fixture state override.
  await jump((await f.mark.campaigns(1)).executionEnd+1n);await action('close');
  await choose(f.funder);await action('reclaim');assert.equal((await f.mark.campaigns(1)).reserve,0n);
  await action('revoke',{spender:'Mark'});assert.equal(await f.token.allowance(f.funder.address,f.mark.target),0n);
  await choose(f.business);await action('transferSeed',{acknowledged:true,to:f.funder.address});
  assert.equal((await flow.inspect()).green,false);
  assert.equal((await f.mark.campaigns(1)).business,f.business.address);
  assert.deepEqual((await flow.chain.ownedSeeds(f.funder.address,'0')).seeds,['1']);
  await choose(f.funder);await action('transferSeed',{acknowledged:true,to:f.business.address});
  const kit=await flow.kit();fs.writeFileSync(path.join(out,'local-recovery-example.json'),serialize(kit));
  fs.writeFileSync(path.join(out,'local-work-example.json'),serialize(work));
  const restored=new NovaWorkflow(new WalletSession(profile,freshStore(),locks),storage);
  await restored.restore(serialize(kit),'local test capsule passphrase');assert.equal(restored.seedId,'1');assert.equal(restored.client.pending.status,'submission-unknown');
  const bad=structuredClone(profile);bad.contracts.Mark.address=CONTRACTS.Mark;assert.throws(()=>new WalletSession(bad,store,locks),/differs|Unsupported|unreviewed/);
  // A reviewed build may suspend exposure without stranding previously signed
  // journals. This alternative policy exists only in another disposable copy.
  const restricted=path.join(temp,'restricted');fs.cpSync(path.join(temp,'assets'),path.join(restricted,'assets'),{recursive:true});
  const suspended={...profile,newExposureEnabled:false};
  writeRegistry(restricted,suspended);
  const {WalletSession:RestrictedSession}=await import(path.join(restricted,'assets/ascension-wallet/session.mjs'));
  const recoveryOnly=new RestrictedSession(suspended,freshStore(),locks);
  recoveryOnly.client.restore(session.client.journal());assert.equal(recoveryOnly.client.history.length,events.length);
  recoveryOnly.client.select({request:({method,params=[]})=>method==='eth_accounts'||method==='eth_requestAccounts'?Promise.resolve([f.funder.address]):network.provider.request({method,params})});
  await assert.rejects(recoveryOnly.prepare('buy',['1','1','1']),/suspended/);
  assert.equal((await recoveryOnly.prepare('approve',['Mark','0'])).args[1],'0');
  await recoveryOnly.reconcile(recoveryOnly.client.pending.hash);
  // Test that a stale initial kit can still recover a mint through the shared journal.
  const mintJournal={...session.client.journal(),transactions:[mint]};
  const recovered=new NovaWorkflow(new WalletSession(profile,freshStore(),locks),storage);
  await recovered.restore(serialize(initialKit),'local test capsule passphrase');
  recovered.client.restore(mintJournal);recovered.client.select({request:({method,params=[]})=>network.provider.request({method,params})});
  await recovered.reconcile(mint.hash);assert.equal(recovered.seedId,'1');
  // Remove a genuinely mined transfer using the disposable chain's snapshot.
  // The separate recovery journal must remain unresolved; the app never resends.
  const reorgSnapshot=await network.provider.request({method:'evm_snapshot',params:[]});
  const reorgFlow=new NovaWorkflow(new WalletSession(profile,freshStore(),locks),storage);
  await reorgFlow.restore(serialize(kit),'local test capsule passphrase');
  reorgFlow.client.select({request:({method,params=[]})=>method==='eth_accounts'||method==='eth_requestAccounts'?
    Promise.resolve([f.business.address]):network.provider.request({method,params})});
  for(const record of [...reorgFlow.client.history].reverse())await reorgFlow.reconcile(record.hash);
  await reorgFlow.prepare('transferSeed',{acknowledged:true,to:f.funder.address});
  const reorgHash=await reorgFlow.confirm(true);assert.equal((await reorgFlow.reconcile(reorgHash)).status,'finalized');
  await network.provider.request({method:'evm_revert',params:[reorgSnapshot]});
  assert.notEqual((await reorgFlow.reconcile(reorgHash)).status,'finalized');assert.equal(reorgFlow.observation,null);
  await assert.rejects(reorgFlow.prepare('transferSeed',{acknowledged:true,to:f.funder.address}),/outstanding|unresolved|reconcile/i);
  assert.equal(reorgFlow.observation,null,'Blocked preparation must not revive an invalidated observation');
  assert.equal(await f.seed.ownerOf(1),f.business.address);
  const report={schema:'agialpha.nova-studio.acceptance.v1',passed:true,classification:profile.evidence.classification,
    sourceHashes:profile.evidence.sourceHashes,sourceSHA256,compiler:require('./compiler-policy').SOLC_VERSION,compilerBuilds,
    actions:events,compilerSizes:sizes,proofsVerified,nativeDelivery,settlement,
    failureCases:{foreignMintEvent:'effect-unverified',finalizedReceiptRecheck:'effect-unverified',restoredEffectBarrier:true,staleWalletPreview:true,
      removedReceipt:{hash:reorgHash,status:reorgFlow.client.pending.status,observationCleared:reorgFlow.observation===null,resubmitted:false}},
    checks:['mint intent/event/readback','separate validators','explicit approval/purchase','bloom','route proof/escrow/committee',
      'native handoff','paid result','refund collection','close/reclaim','unknown import recovery','initial kit receipt recovery',
      'mixed-profile rejection','all 268 browser/native/JavaScript/Solidity leaves and proofs','stale wallet preview rejected',
      'foreign mint emitter remains effect-unverified','genuine EVM reorg preserves unresolved barrier','original native bytes signed and replayed'],mainnetTransactions:0};
  fs.writeFileSync(path.join(out,'exact-source-report.json'),serialize(report));
  if(process.env.NOVA_BROWSER==='1'){
    let browserBeforeSettlement=null;
    const browserTransactions=[];
    const server=http.createServer(async(req,res)=>{
      try{
        const url=new URL(req.url,'http://localhost');
        if(url.pathname==='/advance-auction'&&req.method==='POST'){
          await requireDisposableLocalNetwork();
          await jump((await f.jobs.jobs(2)).auctionEnd);res.end('{}');return;
        }
        if(url.pathname==='/rpc'&&req.method==='POST'){
          let body='';for await(const chunk of req){body+=chunk;if(body.length>1000000)throw Error('oversize');}
          const {method,params=[]}=strictJSON(body);
          const allowed=['eth_chainId','eth_getBlockByNumber','eth_getCode','eth_call','eth_estimateGas','eth_getBalance','eth_getTransactionCount','eth_getTransactionReceipt','eth_getTransactionByHash','eth_getLogs','eth_getStorageAt','eth_sendTransaction'];
          if(!allowed.includes(method))throw Error('RPC not permitted by test bridge');
          if(method==='eth_sendTransaction') {
            await requireDisposableLocalNetwork();
            const tx=params[0];
            assert.ok(actors.includes(tx.from?.toLowerCase()),'Only disposable fixture actors may send through this bridge');
            if(tx.to?.toLowerCase()===f.jobs.target.toLowerCase() && tx.data?.startsWith(f.jobs.interface.getFunction('validate').selector) && !browserBeforeSettlement)
              browserBeforeSettlement=await balances('2');
          }
          const result=await network.provider.request({method,params});
          if(method==='eth_sendTransaction')browserTransactions.push(result);
          res.setHeader('Content-Type','application/json');res.end(serialize({result}));return;
        }
        if(url.pathname==='/upload'&&req.method==='POST'){
          const parts=[];for await(const chunk of req)parts.push(chunk);
          const form=await new Request('http://localhost/upload',{method:'POST',headers:{'Content-Type':req.headers['content-type']},body:Buffer.concat(parts)}).formData();
          assert.equal(form.get('network'),'public');res.setHeader('Content-Type','application/json');res.end(JSON.stringify({data:{cid:publish(await form.get('file').arrayBuffer())}}));return;
        }
        if(url.pathname.startsWith('/ipfs/')){const bytes=files.get(url.pathname.slice(6));res.statusCode=bytes?200:404;res.setHeader('Content-Type','application/json');res.end(bytes||'missing');return;}
        const relative=decodeURIComponent(url.pathname).replace(/^\//,'');
        const file=path.resolve(temp,relative.endsWith('/')?relative+'index.html':relative);
        if(!file.startsWith(temp+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.statusCode=404;res.end('not found');return;}
        const type={'.html':'text/html','.mjs':'text/javascript','.css':'text/css','.json':'application/json'}[path.extname(file)]||'application/octet-stream';
        res.setHeader('Content-Type',type);res.end(fs.readFileSync(file));
      }catch(error){res.statusCode=400;res.end(serialize({error:{message:error.message,code:error.code||-32000}}));}
    });
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    const config={url:`http://127.0.0.1:${server.address().port}/ascension/mainnet/`,actors:actors,committee:f.committee,output:out,
      profile:registryEntry(profile).sha256};
    fs.writeFileSync(path.join(out,'browser-config.json'),serialize(config));
    try{await new Promise((resolve,reject)=>{
      const child=spawn(process.env.ALPHA_PYTHON||'python',[path.join(root,'tests/nova-studio/browser.py'),path.join(out,'browser-config.json')],
        {cwd:root,env:{...process.env,PYTHONPATH:root,NO_DISCLAIMER:'1'},stdio:'inherit'});
      child.on('exit',code=>code===0?resolve():reject(Error(`Browser acceptance failed: ${code}`)));child.on('error',reject);
    });}finally{await new Promise(resolve=>server.close(resolve));}
    const browserReport=JSON.parse(fs.readFileSync(path.join(out,'browser-report.json'),'utf8'));
    const browserNative=browserReport.nativeDelivery,bytes=fs.readFileSync(path.join(out,browserNative.artifact));
    assert.equal(ethers.keccak256(bytes),browserNative.resultHash);assert.equal(sha(bytes),browserNative.byteSHA256);
    const browserJob=await f.jobs.jobs(2);assert.equal(browserJob.state,4n);assert.equal(browserJob.resultHash,browserNative.resultHash);
    assert.equal((await f.mark.campaigns(2)).reserve,0n);
    assert.ok(browserBeforeSettlement,'Browser never requested independent result validation');
    report.browserNativeDelivery=browserNative;
    report.browserSettlement=accounting(browserBeforeSettlement,await balances('2'),'2');
    report.browserReceipts=await Promise.all(browserTransactions.map(async hash=>receiptSummary(
      await network.provider.request({method:'eth_getTransactionReceipt',params:[hash]}))));
    fs.writeFileSync(path.join(out,'exact-source-report.json'),serialize(report));
  }
  for(const [file,digest] of Object.entries(testedSourceHashes))
    assert.equal(sha(fs.readFileSync(path.join(root,file))),digest,`Source changed during acceptance; rerun the exact final build: ${file}`);
  const manifest={schema:'agialpha.nova-studio.evidence-index.v1',
    commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),
    workingTreeDirty:!!execFileSync('git',['status','--porcelain'],{cwd:root,encoding:'utf8'}).trim(),
    classification:profile.evidence.classification,profile,mainnetTransactions:0,
    command:process.env.NOVA_BROWSER==='1'?'NOVA_BROWSER=1 npx --no-install hardhat run scripts/nova-studio.js':'npx --no-install hardhat run scripts/nova-studio.js',
    sourceHashes:testedSourceHashes,
    artifacts:Object.fromEntries(fs.readdirSync(out).filter(name=>name!=='evidence-index.json' && fs.statSync(path.join(out,name)).isFile()).sort().map(name=>{
      const bytes=fs.readFileSync(path.join(out,name));return [name,{sha256:sha(bytes),bytes:bytes.length}];
    })),notPerformed:['live storage account','physical wallets','human screen reader','real validators','mainnet canary','independent security review']};
  fs.writeFileSync(path.join(out,'evidence-index.json'),serialize(manifest));
  if(process.env.NOVA_BROWSER==='1')execFileSync(process.env.ALPHA_PYTHON||'python3',[
    '-c','import sys; from pathlib import Path; from scripts.nova_studio_evidence import verify_lifecycle; verify_lifecycle(Path(sys.argv[1]), sys.argv[2])',
    out,manifest.commit],{cwd:root,env:{...process.env,PYTHONPATH:root,NO_DISCLAIMER:'1'},stdio:'inherit'});
  fs.rmSync(temp,{recursive:true,force:true});console.log(`Nova-Seed exact-source acceptance passed: ${events.length} local wallet actions. Evidence: ${out}`);
}
main().catch(error=>{console.error(error);process.exitCode=1;});
