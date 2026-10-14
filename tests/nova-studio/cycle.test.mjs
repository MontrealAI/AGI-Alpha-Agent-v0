// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createPackage,exportKit,importKit,hashBytes,objectHash,fileBytes,recoverPackage} from '../../docs/assets/nova-studio/package.mjs';
import {sealSeed} from '../../docs/assets/ascension/crypto.mjs';
import {CONTRACTS} from '../../docs/assets/ascension-wallet/protocol.mjs';
import {createProject,validateProject,updateCycle,addCycle,preserveSignedRecord,exportProjectKit,importProjectKit,
  observeCycle,projectCycleState,projectReservoir,proposeReinvestment,reconcileCapital,registerAsset,requireReuseRights,
  verifyReuseRights,freezeEvaluation,recordEvaluation,verifyEvaluation,decideEvaluation,prepareSuccessor,
  registerMission,completeMission,projectObjectHash,deploymentAddress} from '../../docs/assets/nova-studio/cycle.mjs';

const profile = {chainId:1,profile:'archived-read-only-unit-fixture',sourceSHA256:'a'.repeat(64),abiSHA256:'b'.repeat(64),
  contracts:Object.fromEntries(Object.entries(CONTRACTS).filter(([key])=>key!=='Token').map(([key,value])=>[key,{address:value,sha256:'c'.repeat(64)}]))};
const passphrase = 'a separate private recovery passphrase', now = Date.now();
const who = '0x1111111111111111111111111111111111111111', other = '0x2222222222222222222222222222222222222222';
const h = digit => '0x'+digit.repeat(64), enc = new TextEncoder();
const spec = {goal:'Integrate public x^4 on [0,3]',successMetric:'Report exact error, including a negative result.',
  bounty:'100000000000000000000',duration:86400,priceWeight:6000};
const draft = {title:'Private opportunity',description:'Unreleased private terms',jobs:[spec],evidence:'Synthetic reproducible reference.'};
const pkg = await createPackage(draft,passphrase,profile);
async function historicalPackage() {
  const deployment = {chainId:profile.chainId,profile:profile.profile,
    contracts:Object.fromEntries(Object.entries(CONTRACTS).map(([name,value])=>[name,value.toLowerCase()]))};
  const evidence = {...pkg.evidence,deployment}, evidenceHash = await objectHash(evidence);
  const capsule = await sealSeed({...await recoverPackage(pkg,passphrase),deployment,evidenceHash},passphrase);
  return {...pkg,deployment,evidence,evidenceHash,capsule,capsuleHash:await objectHash(capsule),capsuleByteHash:await hashBytes(fileBytes(capsule))};
}
const parent = async () => {
  const project = await createProject(pkg,{title:draft.title,opportunity:{baseline:'private baseline'}});
  return updateCycle(project,project.activeCycleId,{seedId:'7'});
};
const nextPackage = (parentId = '7', target = profile) => createPackage({...draft,parent:parentId,
  jobs:[{...spec,goal:'Integrate public x^2 on [0,3]'}],evidence:'Fresh second synthetic workload.'},passphrase,target);
const currentChain = (project,overrides = {}) => {
  const cycle = project.cycles.at(-1), blockHash = h('a');
  const state = {verification:{blockNumber:'0x20',blockHash,blockTime:'0x'+Math.floor(now/1000).toString(16)},
    wallet:{account:who,balance:1000n,admitted:true,stake:{Jobs:50n,Oracle:70n,agentLocked:20n,validatorLockedUntil:0n}},
    campaign:{business:other,supply:10n,reserve:601n,phase:3n,base:10n,slope:1n},yourLots:3n,
    seedOwner:who,green:false,review:{until:'1'},...overrides};
  const client = {profile,epoch:0,pending:null,guard(epoch){if (epoch !== this.epoch) throw Error('Epoch changed.');}};
  return {client,state,async seed(id,p){assert.equal(id,cycle.seedId);assert.deepEqual(p,cycle.package);return state;}};
};
const requestFor = (project,index = 0,inputs = {source:'synthetic x^4 [0,3]'}) => ({schema:'agialpha.ascension.studio-work.v1',
  project_id:project.projectId,cycle_id:project.activeCycleId,plan:project.cycles.at(-1).package.plan,plan_index:index,
  work_spec:{inputs,goal:project.cycles.at(-1).package.plan.jobs[index].spec.goal}});

test('project and cycle identities exist before package or NFT and preserve original commitments',async()=>{
  const project = await createProject(null,{title:'Before mint',opportunity:{objective:'public task'}}), id = project.activeCycleId;
  assert.equal(project.cycles[0].package,null);assert.match(project.projectId,/^[a-f0-9-]{36}$/);
  const bound = await updateCycle(project,id,{package:pkg});
  assert.equal(bound.projectId,project.projectId);assert.equal(bound.activeCycleId,id);assert.equal(project.cycles[0].package,null);
  const changed = await createPackage({...draft,description:'different'},passphrase,profile);
  await assert.rejects(updateCycle(bound,id,{package:changed}),/immutable/);
  assert.equal(projectCycleState(bound).artifacts,'committed-local-package');
});

test('compatible large packages above legacy canonical object limit still enter private project recovery',async()=>{
  const large = await createPackage({...draft,jobs:Array.from({length:128},(_,i)=>({...spec,
    goal:`${i}: ${'a'.repeat(300)}`,successMetric:'Report exact error and reproducible evidence.'}))},passphrase,profile);
  assert.ok(enc.encode(JSON.stringify(large)).length > 250000);
  const project = await createProject(large);
  assert.deepEqual((await importProjectKit(JSON.stringify(await exportProjectKit(project,passphrase)),passphrase)).cycles[0].package,large);
});

test('full private recovery encrypts plan, terms and original signed strings without changing v1 semantics',async()=>{
  let project = await parent();
  const originalText = '{ "signed": { "payload": "é original bytes", "sequence": 1 }, "signature": "historical-only" }\n';
  project = await preserveSignedRecord(project,{kind:'runtime-run',originalText});
  const kit = await exportProjectKit(project,passphrase), encoded = JSON.stringify(kit);
  for (const secret of [draft.title,spec.goal,originalText,passphrase,project.projectId]) assert.ok(!encoded.includes(secret));
  const restored = await importProjectKit(encoded,passphrase);
  assert.equal(restored.cycles[0].signedRecords[0].originalText,originalText);assert.deepEqual(restored,project);
  assert.equal(projectCycleState(restored).runtime,'requires-current-authorization');
  assert.equal(projectCycleState(restored).settlement,'not-observed');
  await assert.rejects(importProjectKit(encoded,'a wrong but long passphrase'));
  for (const changed of [{...kit,iterations:1},{...kit,ciphertext:kit.ciphertext.slice(0,-4)+'AAAA'},
    {...kit,salt:btoa('b'.repeat(16))},{...kit,iv:btoa('b'.repeat(12))},{...kit,projectId:project.projectId}])
    await assert.rejects(importProjectKit(JSON.stringify(changed),passphrase));
  const readable = JSON.stringify(await exportKit(pkg));
  assert.ok(readable.includes(spec.goal));assert.equal((await importKit(readable)).package.schema,pkg.schema);
});

test('historical records remain exact, deduplicated and unable to import credentials or active grants',async()=>{
  const project = await parent(), originalText = '{"payload":{"sequence":1},"signature":"old"}';
  const withRecord = await preserveSignedRecord(project,{kind:'settlement',originalText});
  assert.deepEqual(await preserveSignedRecord(withRecord,{kind:'settlement',originalText}),withRecord);
  await assert.rejects(preserveSignedRecord(withRecord,{kind:'delivery',originalText}),/another/);
  await assert.rejects(preserveSignedRecord(project,{kind:'grant',originalText}),/active grants/);
  await assert.rejects(preserveSignedRecord(project,{kind:'runtime-run',originalText:'{"private_key":"no"}'}),/credentials/);
  await assert.rejects(preserveSignedRecord(project,{kind:'runtime-run',originalText:'{"x":1,"x":2}'}),/Duplicate/);
  const changed = structuredClone(withRecord); changed.cycles[0].signedRecords[0].originalText += ' ';
  await assert.rejects(validateProject(changed),/historical record/);
});

test('private recovery and runtime requests honor their own larger bounds without changing capsule hash domains',async()=>{
  let project = await parent();
  const input = 'x'.repeat(280000), request = requestFor(project,0,{largePublicInput:input});
  project = await registerMission(project,project.activeCycleId,{request});
  assert.equal(project.cycles[0].missions[0].inputDigest,await projectObjectHash(request.work_spec.inputs));
  assert.equal(await projectObjectHash({b:2,a:1}),await objectHash({a:1,b:2}));
  for (let i=0;i<4;i++) project = await preserveSignedRecord(project,{kind:'runtime-run',
    originalText:JSON.stringify({run:i,evidence:'x'.repeat(1400000)})});
  const kit = await exportProjectKit(project,passphrase);
  assert.ok(kit.ciphertext.length > 7500000);
  assert.deepEqual(await importProjectKit(JSON.stringify(kit),passphrase),project);
  await assert.rejects(projectObjectHash({x:'x'.repeat(2000001)}),/size limit/);
});

test('fresh projections refuse imported flags, account changes, reorg hashes and old observations',async()=>{
  const project = await parent(), chain = currentChain(project), observation = await observeCycle(project,project.activeCycleId,chain,{now});
  assert.equal(projectCycleState(project,project.activeCycleId,{observation,now}).ownership,'current-owner');
  assert.equal(projectCycleState(project,project.activeCycleId,{observation:structuredClone(observation),now}).fresh,false);
  assert.equal(projectCycleState(project,project.activeCycleId,{observation,now:now+120001}).fresh,false);
  assert.equal(projectCycleState(project,project.activeCycleId,{observation,now,currentBlockHash:h('b')}).fresh,false);
  chain.client.epoch++;
  assert.equal(projectCycleState(project,project.activeCycleId,{observation,now}).fresh,false);
});

test('current descriptors and historical identities retain exact bytes and separate address extraction from source verification',async()=>{
  const legacy = await historicalPackage();
  for (const [original,status] of [[pkg,'exact-source'],[legacy,'legacy-addresses']]) {
    const before = JSON.stringify(original);
    let project = await createProject(original);
    project = await updateCycle(project,project.activeCycleId,{seedId:'7'});
    const chain = currentChain(project), observation = await observeCycle(project,project.activeCycleId,chain);
    assert.equal(observation.deploymentIdentity,status);
    const reservoir = projectReservoir(project,project.activeCycleId,observation);
    assert.equal(reservoir.deploymentIdentity,status);assert.equal(reservoir.asset,CONTRACTS.Token.toLowerCase());
    assert.equal(reservoir.campaign.controller,CONTRACTS.Mark.toLowerCase());
    assert.equal(reservoir.stake[0].contract,CONTRACTS.Jobs.toLowerCase());
    assert.equal(proposeReinvestment(reservoir,{sourceOwner:who,approvalActor:who,amount:'1',
      destination:{deployment:pkg.deployment,seedId:'9'},rationale:'Review a fresh task',risk:'Principal may be spent.'}).status,'proposal-only');
    const restored = await importProjectKit(JSON.stringify(await exportProjectKit(project,passphrase)),passphrase);
    assert.deepEqual(restored.cycles[0].package,original);assert.equal(JSON.stringify(original),before);
  }
  assert.equal(deploymentAddress(pkg.deployment,'Jobs'),CONTRACTS.Jobs.toLowerCase());
  assert.equal(deploymentAddress(pkg.deployment,'Token'),CONTRACTS.Token.toLowerCase());
  assert.equal(deploymentAddress({...pkg.deployment,contracts:{...pkg.deployment.contracts,Token:{address:other}}},'Token'),other);
  assert.throws(()=>deploymentAddress({...pkg.deployment,contracts:{...pkg.deployment.contracts,Token:null}},'Token'),/full 0x/);
  const project = await parent();
  for (const changed of [{...profile,sourceSHA256:'d'.repeat(64)},
    {...profile,contracts:{...profile.contracts,Jobs:{...profile.contracts.Jobs,sha256:'e'.repeat(64)}}}]) {
    const chain = currentChain(project);chain.client.profile=changed;
    await assert.rejects(observeCycle(project,project.activeCycleId,chain),/source identity/);
  }
  const sameAddressesNewSource = {...profile,sourceSHA256:'f'.repeat(64)};
  await assert.rejects(addCycle(project,await nextPackage('7',sameAddressesNewSource)),/off-chain/);
});

test('wallet balance, backing reserve, stakes and rightful claim stay separate in native units',async()=>{
  const project = await parent(), chain = currentChain(project), observation = await observeCycle(project,project.activeCycleId,chain,{now});
  const foreignProject = crypto.randomUUID(), reservation = {reservationId:'shared-plan',chainId:1,asset:CONTRACTS.Token,
    owner:who,amount:'300',projectId:foreignProject,status:'planned'};
  const projection = projectReservoir(project,project.activeCycleId,observation,{now,reservations:[reservation,reservation]});
  assert.equal(projection.walletBalance,'1000');assert.equal(projection.availableForProposal,'700');
  assert.equal(projection.campaign.reserve,'601');assert.equal(projection.claim.amount,'180');
  assert.equal(projection.claim.spendable,false);assert.equal(projection.campaign.spendableByBusiness,false);
  assert.equal(projection.stake[0].amount,'50');assert.equal(projection.profit,null);
  const proposal = proposeReinvestment(projection,{sourceOwner:who,approvalActor:who,amount:'700',
    destination:{deployment:pkg.deployment,seedId:'9'},rationale:'New reviewed task',risk:'Principal may be spent.'});
  assert.equal(proposal.status,'proposal-only');assert.equal(proposal.exactCalls,null);
  assert.throws(()=>proposeReinvestment(structuredClone(projection),{sourceOwner:who}),/imported/);
  assert.throws(()=>proposeReinvestment(projection,{sourceOwner:other,approvalActor:who,amount:'1'}),/owned/);
  assert.throws(()=>proposeReinvestment(projection,{sourceOwner:who,approvalActor:who,amount:'701'}),/exceeds/);
  const conflict = {...reservation,amount:'301'};
  assert.throws(()=>projectReservoir(project,project.activeCycleId,observation,{now,reservations:[reservation,conflict]}),/Conflicting/);
  chain.client.pending = {status:'submission-unknown'};
  assert.equal(projectReservoir(project,project.activeCycleId,observation,{now}).availableForProposal,'0');
  assert.throws(()=>proposeReinvestment(projection,{sourceOwner:who,approvalActor:who,amount:'1'}),/exceeds/);
});

test('flow arithmetic deduplicates receipts, separates burns/returned principal and never assigns another actor payout',()=>{
  const flow = {chainId:1,market:CONTRACTS.Jobs,jobId:'12',transactionHash:h('c'),logIndex:1,
    asset:CONTRACTS.Token,kind:'payout',recipient:who,gross:'100',burned:'5'};
  const result = reconcileCapital([flow,flow,{...flow,logIndex:2,kind:'principal-return',gross:'200',burned:'0'},
    {...flow,logIndex:3,recipient:other}],{owner:who});
  assert.equal(result.uniqueObservations,3);assert.equal(result.assets[0].netPayout,'95');
  assert.equal(result.assets[0].burned,'5');assert.equal(result.assets[0].returnedPrincipal,'200');
  assert.equal(result.assets[0].otherRecipients,'95');assert.equal(result.profit,null);assert.equal(result.spendableIncrease,null);
  assert.throws(()=>reconcileCapital([flow,{...flow,gross:'200'}],{owner:who}),/Conflicting/);
  assert.throws(()=>reconcileCapital([{...flow,burned:'101'}],{owner:who}),/Burn/);
});

test('successor preserves identities, rejects replayed package and distinguishes cross-profile provenance',async()=>{
  const project = await parent(), successorPackage = await nextPackage(), next = await addCycle(project,successorPackage);
  assert.equal(next.projectId,project.projectId);assert.notEqual(next.activeCycleId,project.activeCycleId);
  assert.deepEqual(next.cycles[0],project.cycles[0]);assert.equal(next.cycles[1].linkage.kind,'same-contract-parent');
  assert.equal(next.cycles[1].seedId,null);assert.equal(next.cycles[1].signedRecords.length,0);
  await assert.rejects(addCycle(project,pkg),/own package/);
  const different = {...profile,profile:'another-exact-deployment'};
  await assert.rejects(addCycle(project,await nextPackage('7',different)),/off-chain/);
  const cross = await addCycle(project,await nextPackage('0',different));
  assert.equal(cross.cycles[1].linkage.kind,'cross-deployment-provenance');
  assert.deepEqual(cross.cycles[1].linkage.parentDeployment,pkg.deployment);
});

test('imported possession, NFT identity and accepted flags cannot authorize artifact reuse',async()=>{
  let project = await parent();
  const asset = {assetId:'reference-component',digest:h('b'),kind:'source',source:'Public synthetic source',license:'Apache-2.0',
    permittedUses:['successor-input'],rightsEvidence:h('c'),review:{decision:'accepted',reviewer:'operator',evidenceDigest:h('d')},
    validUntil:new Date(now+86400000).toISOString(),revoked:false,scope:'Only the bounded synthetic reference workload'};
  project = await registerAsset(project,project.activeCycleId,asset);
  assert.throws(()=>requireReuseRights({...asset,revoked:true},{licenseCompatible:true}),/current rights/);
  const successor = await nextPackage();
  await assert.rejects(prepareSuccessor(project,project.activeCycleId,successor,{assetIds:[asset.assetId]}),/fresh rights/);
  const token = await verifyReuseRights(project,project.activeCycleId,asset.assetId,async()=>({valid:true,digest:asset.digest,
    rightsEvidence:asset.rightsEvidence,licenseCompatible:true,source:'separately reviewed license and exact source'}));
  const next = await prepareSuccessor(project,project.activeCycleId,successor,{assetIds:[asset.assetId],verifiedAssets:[token]});
  assert.equal(next.cycles.length,2);
  await assert.rejects(prepareSuccessor(project,project.activeCycleId,successor,{assetIds:[asset.assetId],verifiedAssets:[structuredClone(token)]}),/fresh rights/);
});

const frozen = {baselineDigest:h('1'),candidateDigest:h('2'),taskDigest:h('3'),procedureDigest:h('4'),
  resourceBudget:{wallTimeMs:10000,providerCostMicros:'0'},acceptance:{exactTolerancePpm:10},
  heldOut:{method:'Fresh synthetic task after artifact freeze',evidenceDigest:h('5'),tuningExposure:false},
  expectedRunIds:['comparison-1','comparison-2'],rollbackDigest:h('1')};
async function evaluated(overrides = {}) {
  let project = await parent();
  project = await freezeEvaluation(project,project.activeCycleId,frozen);
  const evaluation = project.cycles[0].evaluations[0], originalReport = JSON.stringify({native:'exact reviewed comparison',verdict:overrides.verdict||'PASS'});
  project = await preserveSignedRecord(project,{kind:'evaluation',originalText:originalReport});
  const sourceRecordId = await hashBytes(enc.encode(originalReport));
  project = await recordEvaluation(project,evaluation.evaluationId,{protocolHash:evaluation.protocolHash,verdict:'PASS',sourceRecordId,
    runIds:frozen.expectedRunIds,leakage:false,comparableBudgets:true,qualityRegressed:false,missingCosts:true,originalReport,...overrides});
  return {project,id:evaluation.evaluationId};
}

test('evaluation freezes criteria, retains negative findings and detects leakage, omitted runs and regressions',async()=>{
  for (const [overrides,expected] of [[{verdict:'FAIL'},'FAIL'],[{leakage:true},'inconclusive'],
    [{runIds:['comparison-1']},'inconclusive'],[{comparableBudgets:false},'inconclusive'],[{qualityRegressed:true},'FAIL'],
    [{verdict:'not-run'},'not-run'],[{verdict:'unauthorized'},'unauthorized']]) {
    const {project,id} = await evaluated(overrides);
    assert.equal(project.cycles[0].evaluations[0].evidence.effectiveVerdict,expected);
    await assert.rejects(decideEvaluation(project,id,{decision:'adopt',reviewer:'operator',rationale:'Looks good'}),/fresh verification/);
    const retained = await decideEvaluation(project,id,{decision:'retain-baseline',reviewer:'operator',rationale:'Keep the negative evidence.'});
    assert.equal(retained.cycles[0].evaluations[0].decision.decision,'retain-baseline');
  }
  const {project} = await evaluated(), changed = structuredClone(project);
  changed.cycles[0].evaluations[0].protocol.acceptance.exactTolerancePpm = 100000;
  await assert.rejects(validateProject(changed),/criteria changed/);
});

test('adoption needs fresh verification of exact native report; recovery cannot recreate this authority',async()=>{
  const {project,id} = await evaluated(), evaluation = project.cycles[0].evaluations[0];
  const verified = await verifyEvaluation(project,id,async(protocol,original)=>{
    assert.deepEqual(protocol,frozen);assert.equal(original,evaluation.evidence.originalReport);
    return {valid:true,protocolHash:evaluation.protocolHash,reportHash:evaluation.evidence.reportHash,verdict:'PASS',source:'trusted local native verifier'};
  });
  const adopted = await decideEvaluation(project,id,{decision:'adopt',reviewer:'independent operator',rationale:'Exact source and measurements reviewed.',verified});
  const successor = await nextPackage();
  assert.equal((await prepareSuccessor(adopted,adopted.activeCycleId,successor,{evaluationId:id,verified})).cycles.length,2);
  const restored = await importProjectKit(JSON.stringify(await exportProjectKit(adopted,passphrase)),passphrase);
  assert.equal(projectCycleState(restored).improvement,'not-adopted');
  await assert.rejects(prepareSuccessor(restored,restored.activeCycleId,successor,{evaluationId:id,verified:structuredClone(verified)}),/fresh verification/);
});

test('recovered evaluation IDs cannot be cloned or reused for a different comparison in another cycle',async()=>{
  const {project,id} = await evaluated(), successor = await addCycle(project,await nextPackage());
  const cloned = structuredClone(successor);
  cloned.cycles[1].evaluations.push(structuredClone(cloned.cycles[0].evaluations[0]));
  const before = JSON.stringify(cloned);
  await assert.rejects(validateProject(cloned),/unique across all project cycles/);
  await assert.rejects(exportProjectKit(cloned,passphrase),/unique across all project cycles/);
  let verifierCalls = 0;
  await assert.rejects(verifyEvaluation(cloned,id,async()=>{verifierCalls++;return {valid:true};}),/unique across all project cycles/);
  assert.equal(verifierCalls,0);assert.equal(JSON.stringify(cloned),before);
  const distinct = await freezeEvaluation(successor,successor.activeCycleId,{...frozen,taskDigest:h('6'),
    expectedRunIds:['a genuinely different second-cycle comparison']});
  assert.notEqual(distinct.cycles[1].evaluations[0].evaluationId,id);
  const reused = structuredClone(distinct);reused.cycles[1].evaluations[0].evaluationId=id;
  await assert.rejects(validateProject(reused),/unique across all project cycles/);
  const restored = await importProjectKit(JSON.stringify(await exportProjectKit(distinct,passphrase)),passphrase);
  assert.equal(restored.cycles[0].evaluations[0].evaluationId,id);
  assert.equal(restored.cycles[1].evaluations[0].evaluationId,distinct.cycles[1].evaluations[0].evaluationId);
});

test('multiple unexecuted missions work; completed missions cannot replay input, run, result or settlement',async()=>{
  const multiple = await createPackage({...draft,jobs:[spec,{...spec,goal:'Second committed job'},{...spec,goal:'Third committed job'}]},passphrase,profile);
  let project = await createProject(multiple);
  project = await updateCycle(project,project.activeCycleId,{seedId:'7'});
  const request = requestFor(project);
  project = await registerMission(project,project.activeCycleId,{request});
  project = await registerMission(project,project.activeCycleId,{request:requestFor(project,1,{source:'different synthetic x^4'})});
  assert.equal(project.cycles[0].missions.length,2);assert.equal(project.cycles[0].missions[1].runId,null);
  await assert.rejects(registerMission(project,project.activeCycleId,{request:requestFor(project,0,{source:'replacement'})}),/committed plan index/);
  const first = project.cycles[0].missions[0];
  project = await completeMission(project,project.activeCycleId,first.missionId,{runId:'real-local-run-1',resultDigest:h('6'),settlementId:'1:market:12'});
  await assert.rejects(completeMission(project,project.activeCycleId,project.cycles[0].missions[1].missionId,
    {runId:'real-local-run-1',resultDigest:h('7'),settlementId:'1:market:13'}),/cannot reuse/);
  await assert.rejects(completeMission(project,project.activeCycleId,project.cycles[0].missions[1].missionId,
    {runId:null,resultDigest:h('7'),settlementId:'1:market:13'}),/run ID/);
  const changed = structuredClone(project);changed.cycles[0].missions[0].request.work_spec.inputs.source='substituted';
  await assert.rejects(validateProject(changed),/identity or request changed/);
  await assert.rejects(registerMission(project,project.activeCycleId,{request:requestFor(project,2,{source:'third'}),inputDigest:h('f')}),/must match/);
  const second = await addCycle(project,await nextPackage()), secondRequest = requestFor(second,0,{source:'new x^2 data'});
  const started = await registerMission(second,second.activeCycleId,{request:secondRequest});
  assert.equal(started.cycles[1].missions[0].authority,'requires-new-grant');
  await assert.rejects(completeMission(started,started.activeCycleId,started.cycles[1].missions[0].missionId,
    {runId:'real-local-run-2',resultDigest:h('8'),settlementId:'1:market:12'}),/cannot reuse/);
});
