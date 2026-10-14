// SPDX-License-Identifier: Apache-2.0
import { canonical, digest } from '../successor/engine.mjs?nova-cycle=38c4f38978bf9fc29f207bae3adee0755bc6530d04502a36c491cc430787e488';
import { keccak256 } from './vendor/ethers-6.17.0.mjs';
import { hashBytes, strictJSON, verifyPackage } from './package.mjs';
import { leaf, verifyPlan } from './plan.mjs';

const encoder = new TextEncoder();
function fields(value, expected, name) {
  if (!value || typeof value!=='object' || Array.isArray(value) ||
      Object.keys(value).sort().join()!==[...expected].sort().join()) throw Error(`Unexpected ${name} fields.`);
}
function count(value, name) {
  if (!Number.isSafeInteger(value) || value<0) throw Error(`Invalid ${name}.`);
  return value;
}
function checkRequest(request) {
  fields(request,['schema','project_id','cycle_id','plan','plan_index','work_spec'],'runtime request');
  if (request.schema!=='agialpha.ascension.studio-work.v1' ||
      ![request.project_id,request.cycle_id].every(value=>typeof value==='string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value))) throw Error('Invalid runtime project or cycle identity.');
  verifyPlan(request.plan);
  if (!Number.isSafeInteger(request.plan_index) || request.plan_index<0 || !request.plan.jobs[request.plan_index] ||
      request.work_spec?.schema!=='successor-workbench/v1' || !['reliability','performance','documentation','public-data','numerical'].includes(request.work_spec.family)) throw Error('Unsupported runtime work request.');
}
async function checkSealedRequest(request, body) {
  checkRequest(request);
  const job=request.plan.jobs[request.plan_index], requestDigest=await digest('ascension-studio-request',request);
  if (canonical(body.legacy_spec)!==canonical(job.spec) || body.plan_binding?.kind!=='mark-seed' ||
      body.plan_binding.plan_root!==request.plan.planRoot || body.plan_binding.plan_index!==request.plan_index ||
      body.plan_binding.indexed_leaf!==leaf(request.plan_index,job.spec) || body.market_spec_hash!==leaf(0,job.spec) ||
      body.market_job_id!==null || body.assigned_worker!==null) throw Error('Terms do not bind this exact unassigned committed work.');
  if (body.job_contract?.job_id!==`studio-${request.cycle_id}-${request.plan_index}` ||
      body.job_terms_digest!==await digest('job-terms',body.job_contract) ||
      canonical(body.job_contract.evidence_assumptions)!==canonical(['studio-request-sha256:'+requestDigest])) throw Error('Sealed richer terms do not commit this exact executor request.');
}
function candidateVerdict(pack) {
  const family=pack?.spec?.family, summary=pack?.result?.summary;
  if (!summary || typeof summary!=='object') throw Error('Missing actual runtime summary.');
  if (family==='numerical') {
    if (typeof summary.simpson!=='boolean') throw Error('Invalid numerical verdict.');
    return summary.simpson?'PASS':'FAIL';
  }
  if (family==='documentation') return count(summary.incorrectExamples,'incorrect examples') || count(summary.invalidInputs,'invalid inputs') ? 'FAIL':'PASS';
  if (family==='reliability') return count(summary.candidateFailures,'candidate failures')?'FAIL':count(summary.defects,'defects')?'PASS':'RETAIN_INCUMBENT';
  if (family==='performance') {
    if (typeof summary.correct!=='boolean') throw Error('Invalid correctness verdict.');
    return summary.correct?'INSUFFICIENT_EVIDENCE':'FAIL';
  }
  if (family==='public-data') return 'NOT_APPLICABLE';
  throw Error('Unsupported candidate verdict family.');
}
const hex = value => {
  if (typeof value !== 'string' || !/^[0-9a-f]+$/.test(value) || value.length % 2) throw Error('Invalid public signature encoding.');
  return Uint8Array.from(value.match(/../g), part => parseInt(part,16));
};
const little = bytes => BigInt('0x'+[...bytes].reverse().map(x=>x.toString(16).padStart(2,'0')).join(''));
const lowOrder = new Set([
  '0000000000000000000000000000000000000000000000000000000000000000',
  '0100000000000000000000000000000000000000000000000000000000000000',
  'ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f',
  '26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05',
  'c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a'
]);
function point(bytes) {
  if (bytes.length!==32) throw Error('Ed25519 requires a 32-byte public point.');
  const y=bytes.slice(); y[31]&=127;
  const value=[...y].map(x=>x.toString(16).padStart(2,'0')).join('');
  if (little(y)>=(1n<<255n)-19n || lowOrder.has(value)) throw Error('Invalid or low-order Ed25519 point.');
}
export async function verifySignature(body,domain,signature,trustedKey) {
  return verifyDigestSignature(await digest(domain,body),signature,trustedKey).then(()=>body);
}
export async function verifyDigestSignature(commitment,signature,trustedKey) {
  if (typeof trustedKey!=='string' || !/^[0-9a-f]{64}$/.test(trustedKey)) throw Error('Pin the runtime observer public key through your operator first.');
  if (signature?.public_key!==trustedKey || !/^[A-Za-z0-9+/]{86}==$/.test(signature?.signature||'')) throw Error('Runtime signer does not match the separately pinned observer.');
  if (signature.digest!==commitment) throw Error('Runtime evidence commitment changed.');
  const publicBytes=hex(trustedKey), bytes=Uint8Array.from(atob(signature.signature),c=>c.charCodeAt(0));
  point(publicBytes); point(bytes.slice(0,32));
  if (bytes.length!==64 || little(bytes.slice(32))>=(1n<<252n)+27742317777372353535851937790883648493n) throw Error('Noncanonical runtime signature.');
  const key=await crypto.subtle.importKey('raw',publicBytes,{name:'Ed25519'},false,['verify']);
  if (!await crypto.subtle.verify('Ed25519',key,bytes,hex(commitment))) throw Error('Runtime evidence signature is invalid.');
  return true;
}
export async function verifyEnvelope(envelope,domain,trustedKey) {
  if (!envelope || Object.keys(envelope).sort().join()!==['domain','body','digest','public_key','signature'].sort().join() || envelope.domain!==domain || envelope.body?.schema_version!==1) throw Error('Unsupported signed runtime record.');
  return verifySignature(envelope.body,domain,envelope,trustedKey);
}
export async function resultCommitments(bytes) {
  const data=bytes instanceof Uint8Array?bytes:new Uint8Array(bytes);
  if (!data.length || data.length>2000000) throw Error('Choose exact result bytes between 1 byte and 2 MB.');
  return {sha256:await hashBytes(data),keccak256:keccak256(data),size:data.length};
}
export async function makeRuntimeRequest(pkg,index,projectId,cycleId,workSpec) {
  await verifyPackage(pkg); verifyPlan(pkg.plan);
  if (!Number.isSafeInteger(index) || !pkg.plan.jobs[index]) throw Error('Choose a committed plan index.');
  const spec=strictJSON(JSON.stringify(workSpec));
  if (spec?.schema!=='successor-workbench/v1' || !['reliability','performance','documentation','public-data','numerical'].includes(spec.family)) throw Error('Choose a supported installed workbench adapter.');
  return {schema:'agialpha.ascension.studio-work.v1',project_id:projectId,cycle_id:cycleId,plan:pkg.plan,plan_index:index,work_spec:spec};
}
export async function verifyTerms(request,seal,profile,seedId,trustedKey,runtimeCodeHashes=null) {
  const body=await verifyEnvelope(seal,'ascension-terms',trustedKey), context=body.market_context;
  const contracts=profile.contracts;
  if (!context || String(context.chain_id)!==String(profile.chainId) || context.market?.toLowerCase()!==contracts.Jobs.address.toLowerCase() || context.mark?.toLowerCase()!==contracts.Mark.address.toLowerCase() || context.seed?.toLowerCase()!==contracts.Seed.address.toLowerCase() || String(context.seed_id)!==String(seedId)) throw Error('Terms belong to another deployment or seed.');
  for (const [key,field] of [['Jobs','market_code_hash'],['Mark','mark_code_hash'],['Seed','seed_code_hash'],['Token','token_code_hash']]) {
    const configured=contracts[key]?.keccak256 || contracts[key]?.archivedKeccak256;
    const observed=runtimeCodeHashes?.[key];
    if (!/^0x[0-9a-f]{64}$/.test(context[field]||'') ||
        (configured && context[field]!==configured.toLowerCase()) ||
        (runtimeCodeHashes && (!/^0x[0-9a-f]{64}$/.test(observed||'') || context[field]!==observed))) throw Error('Terms runtime bytecode differs from the selected or freshly verified deployment.');
  }
  await checkSealedRequest(request,body);
  return body;
}
export async function verifyRuntimeResult(request,result,trustedKey) {
  checkRequest(request);
  if (result?.schema!=='agialpha.ascension.studio-result.v1' || result.project_id!==request.project_id || result.cycle_id!==request.cycle_id || result.scope!=='native-fixed-workbench' || result.authority_status!=='not_granted') throw Error('Runtime result belongs to another project, cycle or scope.');
  const {signature,...body}=result;
  if (Object.keys(result).sort().join()!==['schema','project_id','cycle_id','request_digest','terms_seal','execution_binding','delivery','artifact_utf8','artifact_sha256','artifact_keccak256','candidate_verdict','scope','authority_status','signature'].sort().join() || result.request_digest!==await digest('ascension-studio-request',request)) throw Error('Runtime request identity or fields changed.');
  fields(signature,['public_key','digest','signature'],'runtime result signature');
  await verifySignature(body,'ascension-studio-result',signature,trustedKey);
  const delivery=await verifyEnvelope(result.delivery,'ascension-delivery-binding',trustedKey);
  const binding=await verifyEnvelope(result.execution_binding,'ascension-execution-binding',trustedKey);
  const terms=await verifyEnvelope(result.terms_seal,'ascension-terms',trustedKey);
  await checkSealedRequest(request,terms);
  if (binding.terms_seal_digest!==result.terms_seal.digest || binding.job_terms_digest!==terms.job_terms_digest || canonical(binding.plan_binding)!==canonical(terms.plan_binding) || canonical(binding.market_context)!==canonical(terms.market_context)) throw Error('Execution does not bind the original sealed terms.');
  const auth=binding.execution_authorization, job=terms.job_contract;
  if (!auth || binding.institution_id!==job.institution_id || binding.mission_id!==job.mission_id || binding.logical_job_id!==job.job_id ||
      binding.market_spec_hash!==terms.market_spec_hash || auth.job_terms_digest!==terms.job_terms_digest ||
      auth.release_digest!==job.release_digest || auth.environment_digest!==job.environment_digest ||
      auth.acting_identity?.toLowerCase()!==binding.selected_worker || auth.market_binding_digest!==null) throw Error('Execution actor, release, environment or richer work terms disagree.');
  if (typeof result.artifact_utf8!=='string') throw Error('Runtime artifact must preserve its exact UTF-8 text.');
  const bytes=encoder.encode(result.artifact_utf8), hashes=await resultCommitments(bytes);
  if (result.artifact_sha256!==hashes.sha256 || result.artifact_keccak256!==hashes.keccak256 || delivery.artifact_keccak256!==hashes.keccak256 || delivery.artifact_size!==hashes.size || delivery.execution_binding_digest!==result.execution_binding.digest || delivery.candidate_verdict!==result.candidate_verdict) throw Error('Result file, delivery and execution commitments disagree.');
  const artifact=strictJSON(result.artifact_utf8);
  fields(artifact,['schema','project_id','cycle_id','request_digest','execution_binding_digest','authorization_id','report','candidate_verdict','authority_status'],'runtime artifact');
  if (canonical(artifact)!==result.artifact_utf8) throw Error('Runtime artifact must retain its original canonical bytes.');
  if (artifact.schema!=='agialpha.ascension.work-artifact.v1' || artifact.project_id!==request.project_id || artifact.cycle_id!==request.cycle_id || artifact.request_digest!==result.request_digest || artifact.execution_binding_digest!==result.execution_binding.digest || artifact.candidate_verdict!==result.candidate_verdict || artifact.authority_status!=='not_granted') throw Error('Exact runtime artifact context disagrees.');
  if (artifact.authorization_id!==binding.execution_authorization?.authorization_id || canonical(artifact.report?.spec)!==canonical(request.work_spec)) throw Error('Executed authorization or actual inputs differ from the request.');
  if (candidateVerdict(artifact.report)!==result.candidate_verdict) throw Error('Candidate verdict differs from the actual fixed-work report.');
  return {result,artifact,bytes,hashes,binding,delivery,trust:'pinned-runtime-observation',authority:'not_granted'};
}
export async function verifySettlementRecord(record,trustedKey) {
  if (record?.schema!=='agialpha.ascension.journal-settlement.v1' || Object.keys(record).sort().join()!==['schema','public_key','canonical_body','hash','signature','settlement'].sort().join()) throw Error('Import the original signed native settlement journal record.');
  const sha=await hashBytes(encoder.encode(record.canonical_body));
  if (sha!=='0x'+record.hash) throw Error('Original settlement journal bytes changed.');
  await verifyDigestSignature(record.hash,{public_key:record.public_key,digest:record.hash,signature:record.signature},trustedKey);
  const body=strictJSON(record.canonical_body,2000000,{historicalTimestamp:true});
  if (Object.keys(body).sort().join()!==['schema','sequence','previous','identity','mission','time_ns','document'].sort().join() || body.schema!==1 || !Number.isSafeInteger(body.sequence) || body.sequence<1 || !/^[0-9a-f]{64}$/.test(body.previous) || body.identity!=='urn:agialpha:ed25519:'+trustedKey || typeof body.time_ns!=='string') throw Error('Invalid historical settlement journal identity or counters.');
  if (Object.keys(body.document||{}).sort().join()!=='settlement,state' || body.document.state!=='imported' || canonical(body.document.settlement)!==canonical(record.settlement)) throw Error('Settlement differs from its signed original journal.');
  const historicalCanonical=canonical(body).replace(/"time_ns":"([1-9][0-9]*)"}$/, '"time_ns":$1}');
  if (historicalCanonical!==record.canonical_body) throw Error('Historical settlement must preserve its exact original canonical bytes.');
  const chain=record.settlement.chain;
  if (record.settlement.schema_version!==1 || Object.keys(chain||{}).sort().join()!=='chain,job,market' || !/^[1-9][0-9]*$/.test(chain.chain) || !/^[1-9][0-9]*$/.test(chain.job) || !/^0x[0-9a-fA-F]{40}$/.test(chain.market) || body.mission!=='@successor:ascension:settlement:'+await digest('settlement-job',chain)) throw Error('Invalid signed settlement attribution.');
  return record.settlement;
}

function rational(n,d=1n) {
  if (d<=0n) throw Error('Rational denominator must be positive.');
  let a=n<0n?-n:n,b=d; while (b) {const rest=a%b;a=b;b=rest;}
  const common=a||1n; return [n/common,d/common];
}
function parseRational(value) {
  if (typeof value!=='string' || value.length>160 || !/^-?[0-9]+\/[1-9][0-9]*$/.test(value)) throw Error('Expected bounded exact rational evidence.');
  const [n,d]=value.split('/').map(BigInt), result=rational(n,d);
  if (`${result[0]}/${result[1]}`!==value) throw Error('Rational evidence must be canonical and reduced.');
  return result;
}
const add=(left,right)=>rational(left[0]*right[1]+right[0]*left[1],left[1]*right[1]);
const compare=(left,right)=>{const delta=left[0]*right[1]-right[0]*left[1];return delta<0n?-1:delta>0n?1:0;};
const absolute=value=>[value[0]<0n?-value[0]:value[0],value[1]];
function numericalEvidence(request,pack) {
  if (request.work_spec.family!=='numerical') throw Error('Frozen comparison supports numerical work only.');
  const input=request.work_spec.inputs;
  fields(input,['coefficients','lower','upper','steps','tolerancePpm'],'numerical inputs');
  if (!Array.isArray(input.coefficients) || !input.coefficients.length || input.coefficients.length>7 ||
      input.coefficients.some(n=>!Number.isSafeInteger(n)||n < -1000||n>1000) ||
      !Number.isSafeInteger(input.lower) || input.lower < -100 || input.lower>99 ||
      !Number.isSafeInteger(input.upper) || input.upper<=input.lower || input.upper>100 ||
      !Number.isSafeInteger(input.steps) || input.steps<2 || input.steps>1000 || input.steps%2 ||
      !Number.isSafeInteger(input.tolerancePpm) || input.tolerancePpm<0 || input.tolerancePpm>1000000) throw Error('Numerical evidence exceeds its declared fixed work bounds.');
  const evidence=pack.result.evidence;
  fields(evidence,['analytic','trapezoid','simpson','absoluteErrors','absoluteTolerance','passes','arithmetic'],'numerical evidence');
  fields(evidence.absoluteErrors,['trapezoid','simpson'],'method errors');
  fields(evidence.passes,['trapezoid','simpson'],'method verdicts');
  let truth=[0n,1n];
  input.coefficients.forEach((coefficient,index)=>{
    const power=BigInt(index+1);
    truth=add(truth,rational(BigInt(coefficient)*(BigInt(input.upper)**power-BigInt(input.lower)**power),power));
  });
  const tolerance=rational(BigInt(input.tolerancePpm),1000000n);
  if (compare(truth,parseRational(evidence.analytic)) || compare(tolerance,parseRational(evidence.absoluteTolerance))) throw Error('Analytical reference or frozen tolerance changed.');
  const errors={};
  for (const method of ['trapezoid','simpson']) {
    const estimate=parseRational(evidence[method]);
    errors[method]=absolute(add(estimate,[-truth[0],truth[1]]));
    if (compare(errors[method],parseRational(evidence.absoluteErrors[method])) ||
        evidence.passes[method] !== (compare(errors[method],tolerance)<=0) ||
        pack.result.summary[method]!==evidence.passes[method]) throw Error('Measured method errors or tolerance verdicts disagree.');
  }
  return {input,evidence,errors,tolerance};
}
export async function verifyEvaluationRecords(freeze,report,baselineRequest,baselineResult,request,result,key) {
  const protocol=await verifyEnvelope(freeze,'ascension-evaluation-freeze',key);
  const decision=await verifyEnvelope(report,'ascension-evaluation-report',key);
  fields(protocol,['schema_version','evaluation_id','project_id','cycle_id','baseline_request_digest','baseline_artifact_keccak256','request_digest','methods','fresh_common_inputs','budget','criterion','input_policy','selection_policy','source_environment_digest','authority_status'],'frozen evaluation');
  await verifyRuntimeResult(baselineRequest,baselineResult,key);
  const checked=await verifyRuntimeResult(request,result,key), pack=checked.artifact.report;
  if (baselineRequest.project_id!==request.project_id || baselineRequest.work_spec.family!=='numerical') throw Error('Evaluation baseline belongs to another project or work family.');
  const {input,evidence,errors,tolerance}=numericalEvidence(request,pack);
  if (['coefficients','lower','upper'].every(name=>canonical(baselineRequest.work_spec.inputs[name])===canonical(input[name]))) throw Error('Evaluation reused the original polynomial and domain.');
  const budget={calls:1,max_milliseconds:65000,steps_per_method:input.steps};
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(protocol.evaluation_id||'') ||
      protocol.project_id!==request.project_id || protocol.cycle_id!==request.cycle_id ||
      protocol.baseline_request_digest!==await digest('ascension-studio-request',baselineRequest) ||
      protocol.baseline_artifact_keccak256!==baselineResult.artifact_keccak256 ||
      protocol.request_digest!==await digest('ascension-studio-request',request) ||
      canonical(protocol.methods)!==canonical({baseline:'trapezoid',candidate:'simpson'}) ||
      canonical(protocol.fresh_common_inputs)!==canonical(input) || canonical(protocol.budget)!==canonical(budget) ||
      protocol.criterion!=='candidate meets frozen absolute tolerance and has smaller exact error than baseline' ||
      protocol.input_policy!=='fresh operator-visible common inputs; no independently protected holdout' ||
      protocol.selection_policy!=='one predeclared fixed comparison; retain all outcomes and unknown costs' ||
      protocol.source_environment_digest!==result.terms_seal.body.job_contract.environment_digest ||
      protocol.authority_status!=='not_granted') throw Error('Frozen evaluation differs from the exact methods, inputs, budget or runtime.');
  const elapsed=count(pack.economics.elapsedMilliseconds,'elapsed milliseconds');
  const outcome=elapsed>budget.max_milliseconds?'INSUFFICIENT_EVIDENCE':
    compare(errors.simpson,tolerance)>0 || compare(errors.simpson,errors.trapezoid)>0?'FAIL':
    compare(errors.simpson,errors.trapezoid)===0?'TIE':'PASS';
  const expected={schema_version:1,evaluation_id:protocol.evaluation_id,project_id:protocol.project_id,cycle_id:protocol.cycle_id,
    freeze_digest:freeze.digest,baseline_artifact_keccak256:baselineResult.artifact_keccak256,evaluated_artifact_keccak256:result.artifact_keccak256,
    request_digest:protocol.request_digest,methods:protocol.methods,common_inputs:input,exact_absolute_errors:evidence.absoluteErrors,
    absolute_tolerance:evidence.absoluteTolerance,outcome,measured_elapsed_milliseconds:elapsed,budget,compute_cost:null,human_cost:null,
    provider_execution:false,independent_proof:false,scope:'exact numerical error on one fresh common polynomial; no general or economic superiority',
    tradeoff:'Both methods share the same node evaluations; general accuracy, memory and costs remain unqualified.',admission:'HOLD',authority_status:'not_granted'};
  if (canonical(decision)!==canonical(expected)) throw Error('Signed evaluation outcome differs from the actual matched numerical evidence.');
  return {freeze:protocol,report:decision,outcome,authority:'not_granted',trust:'pinned-runtime-observation'};
}
