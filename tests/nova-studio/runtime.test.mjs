// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {generateKeyPairSync,sign} from 'node:crypto';
import {canonical,digest} from '../../docs/assets/successor/engine.mjs';
import {createPackage,hashBytes,objectHash,strictJSON} from '../../docs/assets/nova-studio/package.mjs';
import {resultCommitments,verifyRuntimeResult,verifySettlementRecord,verifyTerms,verifyEvaluationRecords} from '../../docs/assets/nova-studio/runtime.mjs';
import {createProject,validateProject,updateCycle,addCycle,registerMission,preserveSignedRecord} from '../../docs/assets/nova-studio/cycle.mjs';
import {NovaWorkflow} from '../../docs/assets/nova-studio/workflow.mjs';

// Actual installed fixed computation; the Python helper explicitly supplies unit RPC observations.
const native=JSON.parse(execFileSync(process.env.ALPHA_PYTHON||'python',['-c',String.raw`
import json,sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path.cwd()/"tests/runtime"))
from test_successor_studio import prepared_runtime,evaluation_runtime,request
from alpha_factory_v1.core.runtime.successor import studio,ascension
from test_successor_ascension import CLOSE_TX
outputs=[]
for positive in (True,False):
    with TemporaryDirectory() as folder:
        baseline_request,_,store,keys,rpc,reader,seal,binding,authorization,dispatcher=prepared_runtime(Path(folder))
        baseline=studio.execute_work(dispatcher,baseline_request,seal,binding,authorization)
        rpc.artifact_hash=baseline["artifact_keccak256"];rpc.close("paid");rpc.height=4
        studio.settle_work(store.journal,baseline_request,baseline,reader,settlement_tx=CLOSE_TX)
        settlement=ascension.list_settlements(store.journal,"institution")[0]
        fresh=request(negative=not positive);fresh["plan_index"]=0;fresh["work_spec"]["inputs"]["upper"]=2
        freeze=studio.freeze_evaluation(store.journal,baseline_request,baseline,fresh,evaluation_id="53e9f622-4487-4440-9c05-8fb2544c79a7")
        worker,sealed,bound,authorized=evaluation_runtime(store,keys,fresh)
        result=studio.execute_work(worker,fresh,sealed,bound,authorized)
        report=studio.evaluate_work(store.journal,freeze,baseline_request,baseline,fresh,result)
        outputs.append(dict(key=store.journal.public,baseline_request=baseline_request,baseline=baseline,request=fresh,result=result,freeze=freeze,report=report,settlement=settlement))
print(json.dumps(outputs))
`],{cwd:new URL('../../',import.meta.url),env:{...process.env,NO_DISCLAIMER:'1'},maxBuffer:4000000,timeout:60000}));
const encoder=new TextEncoder(), copy=value=>structuredClone(value);
const pair=generateKeyPairSync('ed25519'), publicKey=pair.publicKey.export({format:'der',type:'spki'}).subarray(-32).toString('hex');
async function envelope(domain,body) {
  const commitment=await digest(domain,body);
  return {domain,body,digest:commitment,public_key:publicKey,signature:sign(null,Buffer.from(commitment,'hex'),pair.privateKey).toString('base64')};
}
async function resignResult(value, artifact=null, literal=null) {
  const result=copy(value);
  for (const name of ['terms_seal','execution_binding']) result[name]=await envelope(result[name].domain,result[name].body);
  if (artifact || literal!==null) result.artifact_utf8=literal ?? canonical(artifact);
  const hashes=await resultCommitments(encoder.encode(result.artifact_utf8));
  result.artifact_sha256=hashes.sha256;result.artifact_keccak256=hashes.keccak256;
  const content=strictJSON(result.artifact_utf8);
  result.candidate_verdict=content.candidate_verdict;
  result.delivery=await envelope('ascension-delivery-binding',{...result.delivery.body,
    artifact_size:hashes.size,artifact_keccak256:hashes.keccak256,candidate_verdict:content.candidate_verdict});
  const {signature,...body}=result, signed=await envelope('ascension-studio-result',body);
  return {...body,signature:{public_key:publicKey,digest:signed.digest,signature:signed.signature}};
}
function profileFor(seal) {
  const context=seal.body.market_context;
  return {chainId:Number(context.chain_id),contracts:{
    Jobs:{address:context.market,archivedKeccak256:context.market_code_hash},
    Mark:{address:context.mark,archivedKeccak256:context.mark_code_hash},
    Seed:{address:context.seed,archivedKeccak256:context.seed_code_hash},
    Token:{address:'0xa61a3b3a130a9c20768eebf97e21515a6046a1fa',archivedKeccak256:context.token_code_hash}}};
}
const historicalCanonical=body=>canonical(body).replace(/"time_ns":"([1-9][0-9]*)"}$/, '"time_ns":$1}');
async function signJournal(body,literal=null) {
  const canonical_body=literal ?? historicalCanonical({...body,identity:'urn:agialpha:ed25519:'+publicKey});
  const hash=(await hashBytes(encoder.encode(canonical_body))).slice(2);
  return {schema:'agialpha.ascension.journal-settlement.v1',public_key:publicKey,canonical_body,hash,
    signature:sign(null,Buffer.from(hash,'hex'),pair.privateKey).toString('base64'),settlement:body.document.settlement};
}

test('actual Python execution verifies exact UTF-8 hashes, signatures, terms and verdicts in browser code',async()=>{
  for (const example of native) {
    const checked=await verifyRuntimeResult(example.request,example.result,example.key);
    assert.equal(checked.hashes.keccak256,example.result.artifact_keccak256);
    assert.equal(checked.hashes.sha256,example.result.artifact_sha256);
    assert.notEqual(checked.hashes.sha256,checked.hashes.keccak256);
    assert.equal(checked.authority,'not_granted');
    const terms=example.result.terms_seal, profile=profileFor(terms);
    await verifyTerms(example.request,terms,profile,terms.body.market_context.seed_id,example.key);
    await assert.rejects(verifyRuntimeResult(example.request,example.result,publicKey),/signer/);
  }
});

test('even an authenticated envelope cannot swap artifact fields, canonical bytes or candidate verdict',async()=>{
  const example=native[0], artifact=strictJSON(example.result.artifact_utf8);
  const extra=await resignResult(example.result,{...artifact,run_command:'not executable'});
  await assert.rejects(verifyRuntimeResult(example.request,extra,publicKey),/artifact fields/);
  const whitespace=await resignResult(example.result,null,example.result.artifact_utf8+' ');
  await assert.rejects(verifyRuntimeResult(example.request,whitespace,publicKey),/canonical bytes/);
  const verdict=await resignResult(example.result,{...artifact,candidate_verdict:'FAIL'});
  await assert.rejects(verifyRuntimeResult(example.request,verdict,publicKey),/verdict differs/);
  const signature=copy(example.result);signature.signature.authority='granted';
  await assert.rejects(verifyRuntimeResult(example.request,signature,example.key),/signature fields/);
  const changed=copy(example.request);changed.work_spec.inputs.steps+=2;
  await assert.rejects(verifyRuntimeResult(changed,example.result,example.key),/identity/);
});

test('terms compare independently pinned or current code hashes without conflating SHA and Keccak',async()=>{
  const example=native[0], terms=example.result.terms_seal, profile=profileFor(terms), context=terms.body.market_context;
  const hashes={Jobs:context.market_code_hash,Mark:context.mark_code_hash,Seed:context.seed_code_hash,Token:context.token_code_hash};
  await verifyTerms(example.request,terms,profile,context.seed_id,example.key,hashes);
  await assert.rejects(verifyTerms(example.request,terms,profile,context.seed_id,example.key,{...hashes,Jobs:'0x'+'ab'.repeat(32)}),/bytecode/);
  const changed=copy(profile);changed.contracts.Mark.archivedKeccak256='0x'+'ab'.repeat(32);
  await assert.rejects(verifyTerms(example.request,terms,changed,context.seed_id,example.key),/bytecode/);
  await assert.rejects(verifyTerms(example.request,terms,profile,'999',example.key),/seed/);
});

test('native settlement preserves exact uint64 timestamp lexeme and original signed bytes',async()=>{
  const record=native[0].settlement, original=record.canonical_body;
  const lexeme=/"time_ns":([0-9]+)/.exec(original)[1];
  assert.ok(BigInt(lexeme)>BigInt(Number.MAX_SAFE_INTEGER));
  assert.throws(()=>strictJSON(original),/exact integer/);
  const parsed=strictJSON(original,2000000,{historicalTimestamp:true});
  assert.equal(parsed.time_ns,lexeme);
  assert.deepEqual(await verifySettlementRecord(record,native[0].key),record.settlement);
  assert.equal(record.canonical_body,original);
  await assert.rejects(verifySettlementRecord({...record,canonical_body:original.replace(lexeme,String(BigInt(lexeme)+1n))},native[0].key),/bytes changed/);
  for (const text of ['{"time_ns":18446744073709551616}','{"time_ns":"1791950711069209658"}',
    '{"time_ns":1e18}','{"nested":{"time_ns":1791950711069209658}}','{"time_ns":1,"sequence":1791950711069209658}']) {
    assert.throws(()=>strictJSON(text,2000000,{historicalTimestamp:true}));
  }
});

test('valid signatures cannot rewrite historical metadata, attribution or canonical serialization',async()=>{
  const original=native[0].settlement, parsed=strictJSON(original.canonical_body,2000000,{historicalTimestamp:true});
  const valid=await signJournal(parsed);await verifySettlementRecord(valid,publicKey);
  const wrong=await signJournal({...parsed,mission:'@successor:ascension:settlement:'+'a'.repeat(64)});
  await assert.rejects(verifySettlementRecord(wrong,publicKey),/attribution/);
  const spaced=await signJournal(parsed,valid.canonical_body+' ');
  await assert.rejects(verifySettlementRecord(spaced,publicKey),/canonical bytes/);
  const changed={...valid,settlement:{...valid.settlement,candidate_verdict:'PASS'}};
  await assert.rejects(verifySettlementRecord(changed,publicKey),/signed original/);
});

test('real preregistered matched numerical PASS and FAIL reports verify without granting adoption',async()=>{
  for (const [index,example] of native.entries()) {
    const result=await verifyEvaluationRecords(example.freeze,example.report,example.baseline_request,example.baseline,example.request,example.result,example.key);
    assert.equal(result.outcome,index===0?'PASS':'FAIL');
    assert.equal(result.report.admission,'HOLD');assert.equal(result.authority,'not_granted');
    assert.equal(result.report.independent_proof,false);assert.equal(result.report.compute_cost,null);
  }
});

test('authenticated evaluation cannot relabel failures, costs, budgets, methods or evidence',async()=>{
  const example=native[1], baseline=await resignResult(example.baseline), result=await resignResult(example.result);
  const freeze=await envelope('ascension-evaluation-freeze',copy(example.freeze.body));
  const report=await envelope('ascension-evaluation-report',copy(example.report.body));
  await verifyEvaluationRecords(freeze,report,example.baseline_request,baseline,example.request,result,publicKey);
  for (const change of [{outcome:'PASS'},{compute_cost:0},{authority_status:'granted'},{independent_proof:true},
    {exact_absolute_errors:{trapezoid:'0/1',simpson:'0/1'}},{methods:{baseline:'simpson',candidate:'simpson'}}]) {
    const tampered=await envelope('ascension-evaluation-report',{...report.body,...change});
    await assert.rejects(verifyEvaluationRecords(freeze,tampered,example.baseline_request,baseline,example.request,result,publicKey),/differs/);
  }
  const loose=await envelope('ascension-evaluation-freeze',{...freeze.body,budget:{...freeze.body.budget,calls:2}});
  await assert.rejects(verifyEvaluationRecords(loose,report,example.baseline_request,baseline,example.request,result,publicKey),/frozen|Frozen/);
});

let recordedFailure;
async function retainedFailProject() {
  recordedFailure ??= (async()=>{
    const example=native[1], profile={...profileFor(example.result.terms_seal),profile:'native-unit-observations'};
    const pkg=await createPackage({title:'Retained numerical failure',description:'Native fixed computation with unit RPC observations.',
      jobs:example.request.plan.jobs.map(job=>job.spec),evidence:'Exact signed negative comparison.'},
      'a separate recovery passphrase for the unit fixture',profile);
    assert.equal(canonical(pkg.plan),canonical(example.request.plan));
    // Preserve the native fixture's exact serialization and opaque identities.
    pkg.plan=copy(example.request.plan);
    let project=await createProject(pkg);
    project.projectId=example.request.project_id;project.activeCycleId=example.request.cycle_id;
    project.cycles[0].cycleId=example.request.cycle_id;
    project=await validateProject(project);
    for (const request of [example.baseline_request,example.request])
      project=await registerMission(project,project.activeCycleId,{request});
    project=await preserveSignedRecord(project,{kind:'runtime-run',originalText:JSON.stringify(example.baseline)});
    const flow=new NovaWorkflow({client:{}},null);flow.project=project;
    const freezeText=JSON.stringify(example.freeze), reportText=JSON.stringify(example.report);
    await flow.importEvaluationFreeze(freezeText,example.key);
    flow.project=await preserveSignedRecord(flow.project,{kind:'runtime-run',originalText:JSON.stringify(example.result)});
    const checked=await flow.importEvaluation(freezeText,reportText,example.key);
    assert.equal(checked.outcome,'FAIL');assert.equal(checked.evaluation.evidence.effectiveVerdict,'FAIL');
    await assert.rejects(flow.decideImprovement('adopt','operator','A failure cannot authorize adoption.'),/fresh verification/);
    return {project:flow.project,freezeText,reportText,key:example.key};
  })();
  return copy(await recordedFailure);
}

test('recovered editable PASS claims cannot turn an authenticated native FAIL into adoption authority',async()=>{
  const {project,freezeText,reportText,key}=await retainedFailProject();
  const evidence=project.cycles[0].evaluations[0].evidence;
  evidence.verdict='PASS';evidence.effectiveVerdict='PASS';evidence.qualityRegressed=false;
  // Recovery validates structure and checksums; current verification must reject these coherent lies.
  const recovered=await validateProject(project);
  assert.equal(recovered.cycles[0].evaluations[0].evidence.originalReport,reportText);
  const flow=new NovaWorkflow({client:{}},null);flow.project=recovered;
  await assert.rejects(flow.importEvaluation(freezeText,reportText,key),/authenticated numerical outcome/);
  assert.equal(flow.runtimeEvaluation,null);
  await assert.rejects(flow.decideImprovement('adopt','operator','Imported claim is unverified.'),/Verify a frozen comparison/);
});

test('recovered recomputed protocol hashes cannot replace the authenticated frozen acceptance criterion',async()=>{
  const {project,freezeText,reportText,key}=await retainedFailProject();
  const evaluation=project.cycles[0].evaluations[0];
  evaluation.protocol.acceptance.criterion='Accept every completed numerical run.';
  evaluation.protocolHash=await objectHash(evaluation.protocol);
  evaluation.evidence.protocolHash=evaluation.protocolHash;
  const recovered=await validateProject(project);
  assert.equal(recovered.cycles[0].evaluations[0].evidence.originalReport,reportText);
  const flow=new NovaWorkflow({client:{}},null);flow.project=recovered;
  await assert.rejects(flow.importEvaluation(freezeText,reportText,key),/authenticated frozen comparison/);
  assert.equal(flow.runtimeEvaluation,null);
  await assert.rejects(flow.decideImprovement('adopt','operator','Imported criterion is unverified.'),/Verify a frozen comparison/);
});

test('moving authenticated parent evaluation history into a new child cannot authorize that child cycle',async()=>{
  const retained=await retainedFailProject(), example=native[1];
  const profile={...profileFor(example.result.terms_seal),profile:'native-unit-observations'};
  const parent=await updateCycle(retained.project,retained.project.activeCycleId,{seedId:'1'});
  const pkg=await createPackage({title:'Distinct child work',description:'A different committed child cycle.',parent:'1',
    jobs:[{...example.request.plan.jobs[0].spec,goal:'A new numerical task in a distinct child cycle.'}],
    evidence:'Fresh child inputs require their own execution and evaluation.'},
    'a separate recovery passphrase for the child fixture',profile);
  const relocated=await addCycle(parent,pkg), oldCycle=relocated.cycles[0], child=relocated.cycles[1];
  const evaluation=copy(oldCycle.evaluations[0]);evaluation.evaluationId=crypto.randomUUID();
  child.evaluations.push(evaluation);
  const reportIndex=oldCycle.signedRecords.findIndex(record=>record.originalText===retained.reportText);
  assert.ok(reportIndex>=0);
  child.signedRecords.push(...oldCycle.signedRecords.splice(reportIndex,1));
  // A fresh model ID and valid global record references deliberately bypass structural duplicate checks.
  const recovered=await validateProject(relocated);
  assert.notEqual(recovered.cycles[0].evaluations[0].evaluationId,recovered.cycles[1].evaluations[0].evaluationId);
  assert.equal(recovered.activeCycleId,child.cycleId);
  const flow=new NovaWorkflow({client:{}},null);flow.project=recovered;
  const before=copy(recovered);
  await assert.rejects(flow.importEvaluation(retained.freezeText,retained.reportText,retained.key),/another project or cycle/);
  assert.deepEqual(flow.project,before);assert.equal(flow.runtimeEvaluation,null);assert.equal(flow.runtimeReuse,null);
  await assert.rejects(flow.decideImprovement('adopt','operator','Parent history is not child authority.'),/Verify a frozen comparison/);
});

function settlementWorkflow(project,result,record,state=4n) {
  const settlement=record.settlement, profile=profileFor(result.terms_seal);
  const receipt={status:'0x1',blockHash:settlement.block.hash,blockNumber:'0x'+BigInt(settlement.block.number).toString(16)};
  // Explicit unit observations let the test vary live state without rewriting the native signed record.
  const client={profile,contracts:Object.fromEntries(Object.entries(profile.contracts).map(([name,value])=>[name,value.address])),
    epoch:0,guard(epoch){assert.equal(epoch,this.epoch);},
    async read(method,params) {
      if (method==='eth_getTransactionReceipt') {assert.equal(params[0],settlement.transaction_hash);return receipt;}
      if (method==='eth_getBlockByNumber') return {number:receipt.blockNumber,hash:receipt.blockHash};
      throw Error('Unexpected unit RPC request: '+method);
    },
    async inspect(seedId,jobId) {
      assert.equal(String(seedId),String(result.terms_seal.body.market_context.seed_id));
      assert.equal(String(jobId),String(settlement.chain.job));
      return {job:{state,resultHash:result.artifact_keccak256}};
    }};
  const flow=new NovaWorkflow({client},null);
  flow.project=copy(project);flow.runtimeResult=copy(result);flow.seedId=result.terms_seal.body.market_context.seed_id;
  flow.chain.events=(observed,contract,event)=>{
    assert.equal(observed,receipt);assert.equal(contract,'Jobs');
    if (event==='Closed') return [{id:BigInt(settlement.chain.job),state,refundable:BigInt(settlement.refund_base_units)}];
    if (event==='Payout') return settlement.payouts.map(payout=>({id:BigInt(settlement.chain.job),recipient:payout.recipient,
      gross:BigInt(payout.gross),burned:BigInt(payout.burned)}));
    throw Error('Unexpected unit receipt event: '+event);
  };
  return flow;
}
async function rejectsSettlementWithoutMutation(flow,record,key) {
  const before=copy(flow.project);
  await assert.rejects(flow.importRuntimeSettlement(JSON.stringify(record),key),/contradict the verified chain outcome/);
  assert.deepEqual(flow.project,before);
  assert.equal(flow.runtimeSettlement,null);assert.equal(flow.runtimeReuse,null);
  assert.ok(flow.currentCycle.missions.every(mission=>mission.runId===null && mission.settlementId===null));
  assert.equal(flow.currentCycle.signedRecords.filter(item=>item.kind==='settlement').length,0);
}

test('native signed paid settlement rejects failed or refunded current state before changing history or reuse',async()=>{
  const {project}=await retainedFailProject(), example=native[1], record=example.settlement;
  assert.equal(record.settlement.job_acceptance,'accepted');assert.equal(record.settlement.settlement_status,'paid');
  const paid=settlementWorkflow(project,example.baseline,record);
  await paid.importRuntimeSettlement(JSON.stringify(record),example.key);
  assert.equal(paid.runtimeSettlement.settlement.settlement_status,'paid');
  assert.ok(paid.currentCycle.missions.find(mission=>mission.request.plan_index===example.baseline_request.plan_index).settlementId);
  for (const state of [5n,6n])
    await rejectsSettlementWithoutMutation(settlementWorkflow(project,example.baseline,record,state),record,example.key);
});

test('even authenticated settlement asset, acceptance and authority claims must match fixed chain semantics',async()=>{
  const {project}=await retainedFailProject(), example=native[1], result=await resignResult(example.baseline);
  const body=strictJSON(example.settlement.canonical_body,2000000,{historicalTimestamp:true});
  for (const change of [{token:'0x'+'11'.repeat(20)},{decimals:6},{symbol:'OTHER'},
    {customer_realized_value:'100'},{memory_admission:'granted'},{institutional_admission:'granted'},
    {authority_status:'granted'},{job_acceptance:'rejected'},{settlement_status:'refunded'}]) {
    const changed=copy(body);changed.document.settlement={...changed.document.settlement,...change};
    const record=await signJournal(changed);
    await rejectsSettlementWithoutMutation(settlementWorkflow(project,result,record),record,publicKey);
  }
});
