// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createPackage,hashBytes,strictJSON} from '../../docs/assets/nova-studio/package.mjs';
import {CONTRACTS} from '../../docs/assets/ascension-wallet/protocol.mjs';
import {createProject,updateCycle,registerMission,prepareSuccessor} from '../../docs/assets/nova-studio/cycle.mjs';
import {authorizeArtifactReuse,assertNumericalReuse} from '../../docs/assets/nova-studio/reuse.mjs';
import {makeRuntimeRequest,resultCommitments} from '../../docs/assets/nova-studio/runtime.mjs';
import {leaf} from '../../docs/assets/nova-studio/plan.mjs';
import {canonical,digest} from '../../docs/assets/successor/engine.mjs';
import {example,run} from '../../examples/successor-workbench/engine.mjs';

const encoder = new TextEncoder(), now = Date.now(), passphrase = 'separate local fixture passphrase';
const profile = {chainId:1,profile:'archived-read-only-unit-fixture',
  contracts:Object.fromEntries(Object.entries(CONTRACTS).filter(([key])=>key!=='Token').map(([key,value])=>[key,{address:value}]))};
const job = {goal:'Compute a synthetic polynomial and report both correct and negative findings.',
  successMetric:'Supply exact source inputs, rational results and a truthful tolerance verdict.',
  bounty:'100000000000000000000',duration:86400,priceWeight:6000};
const pkg = await createPackage({title:'Reuse fixture',description:'No live authority',jobs:[job],evidence:'Synthetic local reference.'},passphrase,profile);
const keys = await crypto.subtle.generateKey({name:'Ed25519'},true,['sign','verify']);
const observerKey = Buffer.from(await crypto.subtle.exportKey('raw',keys.publicKey)).toString('hex');
async function signature(domain,body) {
  const commitment = await digest(domain,body), signed = await crypto.subtle.sign('Ed25519',keys.privateKey,Buffer.from(commitment,'hex'));
  return {public_key:observerKey,digest:commitment,signature:Buffer.from(signed).toString('base64')};
}
async function envelope(domain,body) { return {domain,body,...await signature(domain,body)}; }
async function fixture(mutateReport = null) {
  let project = await createProject(pkg);
  project = await updateCycle(project,project.activeCycleId,{seedId:'7'});
  const workSpec = {...example('numerical'),owner:project.projectId,
    inputs:{coefficients:[0,0,0,0,1],lower:0,upper:3,steps:2,tolerancePpm:10}};
  const request = await makeRuntimeRequest(pkg,0,project.projectId,project.activeCycleId,workSpec);
  project = await registerMission(project,project.activeCycleId,{request});
  const report = await run(workSpec,{sourceHash:'a'.repeat(64)});
  if (mutateReport) {
    await mutateReport(report);
    const {integrityDigest,...body} = report; report.integrityDigest = await digest('workbench-pack',body);
  }
  const requestDigest = await digest('ascension-studio-request',request);
  const jobContract = {job_id:`studio-${project.activeCycleId}-0`,institution_id:'fixture-institution',mission_id:'fixture-mission',
    release_digest:'c'.repeat(64),environment_digest:'d'.repeat(64),evidence_assumptions:['studio-request-sha256:'+requestDigest]};
  const terms = {schema_version:1,job_contract:jobContract,job_terms_digest:await digest('job-terms',jobContract),
    legacy_spec:job,market_spec_hash:leaf(0,job),market_job_id:null,assigned_worker:null,
    plan_binding:{kind:'mark-seed',plan_root:pkg.plan.planRoot,plan_index:0,indexed_leaf:leaf(0,job)},market_context:{
      chain_id:'1',market:CONTRACTS.Jobs,seed:CONTRACTS.Seed,seed_id:'7'}};
  const seal = await envelope('ascension-terms',terms);
  const binding = await envelope('ascension-execution-binding',{schema_version:1,terms_seal_digest:seal.digest,
    job_terms_digest:terms.job_terms_digest,plan_binding:terms.plan_binding,market_context:terms.market_context,
    institution_id:jobContract.institution_id,mission_id:jobContract.mission_id,logical_job_id:jobContract.job_id,
    market_spec_hash:terms.market_spec_hash,
    market_job_id:'12',selected_worker:'0x1111111111111111111111111111111111111111',
    execution_authorization:{authorization_id:'fixture-one-use-execution',job_terms_digest:terms.job_terms_digest,
      release_digest:jobContract.release_digest,environment_digest:jobContract.environment_digest,
      acting_identity:'0x1111111111111111111111111111111111111111',market_binding_digest:null}});
  const artifact = {schema:'agialpha.ascension.work-artifact.v1',project_id:project.projectId,cycle_id:project.activeCycleId,
    request_digest:requestDigest,execution_binding_digest:binding.digest,authorization_id:'fixture-one-use-execution',
    report,candidate_verdict:'FAIL',authority_status:'not_granted'};
  const artifact_utf8 = canonical(artifact), hashes = await resultCommitments(encoder.encode(artifact_utf8));
  const delivery = await envelope('ascension-delivery-binding',{schema_version:1,execution_binding_digest:binding.digest,
    artifact_keccak256:hashes.keccak256,artifact_size:hashes.size,candidate_verdict:'FAIL'});
  const body = {schema:'agialpha.ascension.studio-result.v1',project_id:project.projectId,cycle_id:project.activeCycleId,
    request_digest:requestDigest,terms_seal:seal,execution_binding:binding,delivery,artifact_utf8,
    artifact_sha256:hashes.sha256,artifact_keccak256:hashes.keccak256,candidate_verdict:'FAIL',
    scope:'native-fixed-workbench',authority_status:'not_granted'};
  const result = {...body,signature:await signature('ascension-studio-result',body)};
  const settlement = {chain:{chain:'1',market:CONTRACTS.Jobs,job:'12'},job_acceptance:'accepted',settlement_status:'paid',
    execution_binding_digest:binding.digest,delivery_digest:delivery.digest,candidate_verdict:'FAIL',authority_status:'not_granted'};
  const current = {request,result,settlement,observerKey};
  const review = {reviewer:'Local fixture operator',rationale:'I reviewed the synthetic source, declared Apache license and exact recipe bytes.',
    license:workSpec.rights.license,validUntil:new Date(now+86400000).toISOString()};
  return {project,current,workSpec,review};
}

test('select actual accepted artifact bytes, retain a paid negative finding and require explicit local rights review',async()=>{
  const {project,current,workSpec,review} = await fixture(); let checks = 0;
  const reuse = await authorizeArtifactReuse(project,project.activeCycleId,{review,verifyCurrent:async()=>{checks++;return current;},now});
  assert.equal(checks,1);assert.equal(reuse.project.cycles[0].assets.length,1);assert.equal(project.cycles[0].assets.length,0);
  assert.equal(reuse.asset.digest,await hashBytes(reuse.sourceBytes));
  assert.deepEqual(strictJSON(new TextDecoder().decode(reuse.sourceBytes)),workSpec.inputs);
  assert.match(reuse.asset.source,/local operator attestation/);assert.match(reuse.asset.scope,/No candidate adoption/);
  assert.equal(current.result.candidate_verdict,'FAIL');assert.equal(reuse.project.cycles[0].evaluations.length,0);
  assert.equal(reuse.selection.inherited.absoluteTolerance,'1/100000');
  const successorPkg = await createPackage({title:'New exact task',description:'Fresh polynomial with reused recipe',
    jobs:[{...job,goal:'Use fresh x^2 coefficients with the reviewed fixed numerical recipe.'}],
    parent:'7',evidence:'Distinct synthetic source and fresh authorization required.'},passphrase,profile);
  assert.equal((await prepareSuccessor(reuse.project,project.activeCycleId,successorPkg,
    {assetIds:[reuse.asset.assetId],verifiedAssets:[reuse.token],now})).cycles.length,2);
});

test('new execution consumes selected exact steps, tolerance and bounds while using different coefficients',async()=>{
  const {project,current,workSpec,review} = await fixture();
  const reuse = await authorizeArtifactReuse(project,project.activeCycleId,{review,verifyCurrent:async()=>current,now});
  const context = {projectId:project.projectId,cycleId:crypto.randomUUID(),now};
  const next = {...workSpec,inputs:{...workSpec.inputs,coefficients:[0,0,1]}};
  assert.deepEqual(assertNumericalReuse(reuse.selection,next,context),next);
  for (const [field,value] of [['steps',4],['lower',-1],['upper',5],['tolerancePpm',20]])
    assert.throws(()=>assertNumericalReuse(reuse.selection,{...next,inputs:{...next.inputs,[field]:value}},context),/Inherited/);
  assert.throws(()=>assertNumericalReuse(reuse.selection,workSpec,context),/distinct polynomial/);
  assert.throws(()=>assertNumericalReuse(structuredClone(reuse.selection),next,context),/imported selections/);
  assert.throws(()=>assertNumericalReuse(reuse.selection,next,{...context,cycleId:project.activeCycleId}),/reuse authority/);
  assert.throws(()=>assertNumericalReuse(reuse.selection,next,{...context,projectId:crypto.randomUUID()}),/reuse authority/);
  assert.throws(()=>assertNumericalReuse(reuse.selection,next,{...context,now:now+300001}),/reuse authority/);
  assert.throws(()=>assertNumericalReuse(reuse.selection,{...next,rights:{...next.rights,license:'unknown'}},context),/source license/);
});

test('rejected, foreign, unverified or differently signed reports cannot enter the reusable reservoir',async()=>{
  const {project,current,review} = await fixture();
  await assert.rejects(authorizeArtifactReuse(project,project.activeCycleId,{review}),/Refresh/);
  for (const change of [{job_acceptance:'rejected'},{settlement_status:'pending'},{execution_binding_digest:'0'.repeat(64)},
    {chain:{...current.settlement.chain,job:'13'}}])
    await assert.rejects(authorizeArtifactReuse(project,project.activeCycleId,{review,verifyCurrent:async()=>({
      ...current,settlement:{...current.settlement,...change}}),now}),/exact execution/);
  await assert.rejects(authorizeArtifactReuse(project,project.activeCycleId,{review,
    verifyCurrent:async()=>({...current,observerKey:'a'.repeat(64)}),now}),/signer/);
  await assert.rejects(authorizeArtifactReuse(project,project.activeCycleId,{artifactName:'numerical.json',review,
    verifyCurrent:async()=>current,now}),/calculation-input/);
  await assert.rejects(authorizeArtifactReuse(project,project.activeCycleId,{review:{...review,license:'License bypass'},
    verifyCurrent:async()=>current,now}),/exact declared license/);
  await assert.rejects(authorizeArtifactReuse(project,project.activeCycleId,{review:{...review,rationale:''},
    verifyCurrent:async()=>current,now}),/rationale/);
  await assert.rejects(authorizeArtifactReuse(project,project.activeCycleId,{review:{...review,validUntil:new Date(now+86400001).toISOString()},
    verifyCurrent:async()=>current,now}),/24 hours/);
});

test('even a signed contradictory source cannot swap, duplicate or relabel selected recipe bytes',async()=>{
  for (const mutate of [report=>report.result.artifacts.push({...report.result.artifacts[1]}),
    async report=>{
      const artifact=report.result.artifacts[1];artifact.content=JSON.stringify({...report.spec.inputs,steps:4});
      const {digest:old,...body}=artifact;artifact.digest=await digest('workbench-artifact',body);
    },report=>{report.result.evidence.absoluteTolerance='10/1';},
    report=>{report.result.artifacts[1].digest='0'.repeat(64); }]) {
    const {project,current,review}=await fixture(mutate);
    await assert.rejects(authorizeArtifactReuse(project,project.activeCycleId,{review,verifyCurrent:async()=>current,now}),
      /unambiguous|executed inputs|digest differs/);
  }
});
