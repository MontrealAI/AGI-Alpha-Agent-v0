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
function cid(bytes) {
  const source=Buffer.concat([Buffer.from([1,85,18,32]),createHash('sha256').update(Buffer.from(bytes)).digest()]);
  let bits=0,value=0,result='b';const alphabet='abcdefghijklmnopqrstuvwxyz234567';
  for(const byte of source){value=(value<<8)|byte;bits+=8;while(bits>=5){result+=alphabet[(value>>>(bits-5))&31];bits-=5;}}
  if(bits)result+=alphabet[(value<<(5-bits))&31];return result;
}
async function main(){
  await requireDisposableLocalNetwork();
  const f=await fixture(),temp=fs.mkdtempSync(path.join(os.tmpdir(),'nova-studio-'));
  fs.mkdirSync(out,{recursive:true});
  for(const folder of ['ascension','ascension-wallet','nova-studio'])fs.cpSync(path.join(root,'docs/assets',folder),path.join(temp,'assets',folder),{recursive:true});
  fs.cpSync(path.join(root,'docs/ascension/mainnet'),path.join(temp,'ascension/mainnet'),{recursive:true});
  const {ACTIONS,CONTRACTS}=await import(path.join(root,'docs/assets/ascension-wallet/protocol.mjs'));
  const contracts={};
  for(const [key,contract] of Object.entries({Access:f.access,Seed:f.seed,Oracle:f.oracle,Jobs:f.jobs,Mark:f.mark,Token:f.token}))
    contracts[key]={address:contract.target,sha256:sha(Buffer.from((await ethers.provider.getCode(contract.target)).slice(2),'hex'))};
  const actors=[f.business,f.funder,f.agent,...f.validators].map(s=>s.address.toLowerCase());
  const profile={schema:'agialpha.qualified-wallet-profile.v1',chainId:31337,profile:'disposable-exact-source-nova-studio',
    stage:'canary',newExposureEnabled:true,contracts,actions:Object.keys(ACTIONS),
    scope:{actors,actions:Object.fromEntries(Object.keys(ACTIONS).map(k=>[k,{maxArgs:k==='approve'?{'1':ethers.parseEther('10000').toString()}:k==='buy'?{'2':ethers.parseEther('500').toString()}:{}}]))},
    dependencies:[],authorities:['Access','Oracle','Jobs'].map(contract=>({contract,owner:f.governor.address})),
    evidence:{classification:'exact-source-local-with-mock-external-dependencies',sourceHashes:{},notMainnet:true}};
  for(const contract of [f.ens,f.wrapper])profile.dependencies.push({address:contract.target,sha256:sha(Buffer.from((await ethers.provider.getCode(contract.target)).slice(2),'hex')),slots:[]});
  for(const name of ['AscensionAccess','NovaSeed','AscensionRiskOracle','AscensionJobMarket','AscensionMark','AscensionToken'])
    profile.evidence.sourceHashes[name]=sha(fs.readFileSync(path.join(root,`contracts/ascension/${name}.sol`)));
  fs.writeFileSync(path.join(temp,'assets/ascension-wallet/qualified-profiles.mjs'),`export const QUALIFIED_PROFILES=Object.freeze(${JSON.stringify([profile])});\n`);
  fs.writeFileSync(path.join(temp,'assets/ascension-wallet/profile.json'),serialize(profile));
  const {WalletSession}=await import(path.join(temp,'assets/ascension-wallet/session.mjs'));
  const {NovaWorkflow}=await import(path.join(temp,'assets/nova-studio/workflow.mjs'));
  const {PinataStorage}=await import(path.join(temp,'assets/nova-studio/storage.mjs'));
  const {compilePlan,leaf}=await import(path.join(temp,'assets/nova-studio/plan.mjs'));
  const {strictJSON,hashBytes}=await import(path.join(temp,'assets/nova-studio/package.mjs'));
  const files=new Map(),events=[];
  function publish(bytes){const key=cid(bytes);files.set(key,Buffer.from(bytes));return key;}
  const storage=new PinataStorage(async(url,options)=>{
    if(options.method==='POST')return new Response(JSON.stringify({data:{cid:publish(await options.body.get('file').arrayBuffer())}}));
    const bytes=files.get(url.split('/').at(-1));return new Response(bytes||'',{status:bytes?200:404});
  });
  const map=new Map(),store={getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v)},locks={request:async(_name,_options,fn)=>fn({name:'test-node-lock'})};
  const session=new WalletSession(profile,store,locks),flow=new NovaWorkflow(session,storage);
  async function choose(signer){session.client.select({request:async({method,params=[]})=>{
    if(method==='eth_accounts'||method==='eth_requestAccounts')return [signer.address];
    if(method==='eth_sendTransaction')assert.equal(params[0].from.toLowerCase(),signer.address.toLowerCase());
    return network.provider.request({method,params});
  }});await session.client.connect();}
  async function action(name,input={}){
    const preview=await flow.prepare(name,input);assert.equal(preview.transaction.value,'0x0');
    const hash=await flow.confirm(true),record=await flow.reconcile(hash);assert.equal(record.status,'finalized');
    events.push({action:name,hash,status:record.status});return record;
  }
  for(const count of [1,2,3,7,127,128]){
    const plan=compilePlan(Array.from({length:count},(_,i)=>({...spec,goal:`Job ${i} — énergie`})));for(const j of plan.jobs)assert.equal(j.leaf,await f.jobs.hashSpec(j.index,j.spec));
  }
  await choose(f.business);
  await flow.create({title:'Private exact-source acceptance',description:'Must not appear in uploaded artifacts.',jobs:[spec,spec],evidence:'Synthetic local acceptance, not an independent real-world review.'},'local test capsule passphrase');
  const initialKit=await flow.kit();await flow.publish('synthetic-local-storage-token',true);
  const identity=await flow.chain.identity();assert.equal(identity.eligible,true);
  const mint=await action('seal');assert.equal(flow.seedId,'1');assert.equal(mint.transaction.to.toLowerCase(),f.seed.target.toLowerCase());
  assert.equal(mint.args[0],flow.package.capsuleHash);assert.equal(mint.args[1],flow.package.plan.planRoot);
  const opened=await flow.chain.openMintReceipt(mint.hash,flow.package);assert.equal(opened.seedId,'1');
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
  const resultHash=await hashBytes(Buffer.from('local synthetic result bytes'));
  await assert.rejects(flow.prepare('submit',{jobId:'1',result:resultHash,uri:'ipfs://'+publish(Buffer.from('wrong result bytes'))}),/Published result bytes/);
  await action('submit',{jobId:'1',result:resultHash,uri:'ipfs://'+publish(Buffer.from('local synthetic result bytes'))});
  for(const reviewer of f.validators.slice(0,2)){await choose(reviewer);await action('validate',{jobId:'1',result:resultHash,approved:'true',reviewed:true,findings:'Synthetic local acceptance result inspected by fixture signer.'});}
  assert.equal((await f.jobs.jobs(1)).state,4n);
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
  const freshStore=()=>{const saved=new Map();return {getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v)};};
  const restored=new NovaWorkflow(new WalletSession(profile,freshStore(),locks),storage);
  await restored.restore(serialize(kit),'local test capsule passphrase');assert.equal(restored.seedId,'1');assert.equal(restored.client.pending.status,'submission-unknown');
  const bad=structuredClone(profile);bad.contracts.Mark.address=CONTRACTS.Mark;assert.throws(()=>new WalletSession(bad,store,locks),/differs/);
  // A reviewed build may suspend exposure without stranding previously signed
  // journals. This alternative policy exists only in another disposable copy.
  const restricted=path.join(temp,'restricted');fs.cpSync(path.join(temp,'assets'),path.join(restricted,'assets'),{recursive:true});
  const suspended={...profile,newExposureEnabled:false};
  fs.writeFileSync(path.join(restricted,'assets/ascension-wallet/qualified-profiles.mjs'),`export const QUALIFIED_PROFILES=Object.freeze(${JSON.stringify([suspended])});\n`);
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
  fs.writeFileSync(path.join(out,'exact-source-report.json'),serialize({schema:'agialpha.nova-studio.acceptance.v1',classification:profile.evidence.classification,
    sourceHashes:profile.evidence.sourceHashes,compiler:(await artifacts.getBuildInfo('contracts/Ascension.sol:AscensionMark'))?.solcVersion||require('./compiler-policy').SOLC_VERSION,
    actions:events,compilerSizes:[1,2,3,7,127,128],checks:['mint intent/event/readback','separate validators','explicit approval/purchase','bloom','route proof/escrow/committee','native handoff','paid result','refund collection','close/reclaim','unknown import recovery','initial kit receipt recovery','mixed-profile rejection'],mainnetTransactions:0}));
  if(process.env.NOVA_BROWSER==='1'){
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
          res.setHeader('Content-Type','application/json');res.end(serialize({result:await network.provider.request({method,params})}));return;
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
    const config={url:`http://127.0.0.1:${server.address().port}/ascension/mainnet/`,actors:actors,committee:f.committee,output:out};
    fs.writeFileSync(path.join(out,'browser-config.json'),serialize(config));
    try{await new Promise((resolve,reject)=>{
      const child=spawn(process.env.ALPHA_PYTHON||'python',[path.join(root,'tests/nova-studio/browser.py'),path.join(out,'browser-config.json')],{cwd:root,stdio:'inherit'});
      child.on('exit',code=>code===0?resolve():reject(Error(`Browser acceptance failed: ${code}`)));child.on('error',reject);
    });}finally{await new Promise(resolve=>server.close(resolve));}
  }
  const sourceFiles=['docs/ascension/mainnet/index.html'];
  for(const folder of ['docs/assets/nova-studio','docs/assets/ascension-wallet','docs/assets/ascension'])
    for(const file of fs.readdirSync(path.join(root,folder),{recursive:true}))
      if(fs.statSync(path.join(root,folder,file)).isFile())sourceFiles.push(folder+'/'+file);
  const manifest={schema:'agialpha.nova-studio.evidence-index.v1',
    commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),
    workingTreeDirty:!!execFileSync('git',['status','--porcelain'],{cwd:root,encoding:'utf8'}).trim(),
    classification:profile.evidence.classification,profile,mainnetTransactions:0,
    command:process.env.NOVA_BROWSER==='1'?'NOVA_BROWSER=1 npx --no-install hardhat run scripts/nova-studio.js':'npx --no-install hardhat run scripts/nova-studio.js',
    sourceHashes:Object.fromEntries(sourceFiles.sort().map(file=>[file,sha(fs.readFileSync(path.join(root,file)))])),
    artifacts:Object.fromEntries(fs.readdirSync(out).filter(name=>name!=='evidence-index.json' && fs.statSync(path.join(out,name)).isFile()).sort().map(name=>{
      const bytes=fs.readFileSync(path.join(out,name));return [name,{sha256:sha(bytes),bytes:bytes.length}];
    })),notPerformed:['live storage account','physical wallets','human screen reader','real validators','mainnet canary','independent security review']};
  fs.writeFileSync(path.join(out,'evidence-index.json'),serialize(manifest));
  fs.rmSync(temp,{recursive:true,force:true});console.log(`Nova-Seed exact-source acceptance passed: ${events.length} local wallet actions. Evidence: ${out}`);
}
main().catch(error=>{console.error(error);process.exitCode=1;});
