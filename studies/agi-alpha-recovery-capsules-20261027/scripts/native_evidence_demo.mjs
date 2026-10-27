// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import { canonicalJSON, hashObject, sealSeed, openSeed } from '../upstream/docs/assets/ascension/crypto.mjs';
import { compilePlan, verifyPlan } from '../upstream/docs/assets/nova-studio/plan.mjs';
import { validate, analyze } from '../upstream/examples/alpha-discovery/engine.mjs';

const inputPath=path.resolve(process.argv[2]);
const outputDirectory=path.dirname(inputPath);
const input=JSON.parse(fs.readFileSync(inputPath,'utf8'));
const bindings=input.bindings;
if(await hashObject(bindings)!==input.binding_sha256) throw Error('CROSS_LANGUAGE_BINDING_DIGEST_MISMATCH');
const publicFixturePassphrase='public-recovery-research-fixture-not-a-secret';
const genome={schema:'agialpha.novaseed.genome.v1',purpose:'Bind local recovery-delivery evidence without asserting market or identity authority',bindings};
const sealed=await sealSeed(genome,publicFixturePassphrase);
const opened=await openSeed(sealed,publicFixturePassphrase);
if(canonicalJSON(opened)!==canonicalJSON(genome)) throw Error('NOVA_ROUNDTRIP_MISMATCH');
const changed=structuredClone(sealed);
const bytes=Buffer.from(changed.ciphertext,'base64'); bytes[0]^=1; changed.ciphertext=bytes.toString('base64');
let tamperRejected=false;
try{await openSeed(changed,publicFixturePassphrase);}catch{tamperRejected=true;}
if(!tamperRejected) throw Error('NOVA_TAMPER_NOT_REJECTED');
const jobs=bindings.cases.map(row=>({
  goal:`Recovery ${row.case}; input ${row.input_sha256}; output ${row.recovered_notebook_sha256}; protocol ${bindings.protocol_sha256}`,
  successMetric:`Local evidence ${input.binding_sha256}; passing reports ${row.passing_execution_reports}; independent ${row.independent_passing_reports}; no commercial acceptance or authority.`,
  bounty:'100',duration:172800,priceWeight:0
}));
const plan=compilePlan(jobs); const rebuilt=verifyPlan(plan);
if(plan.planRoot!==rebuilt.planRoot) throw Error('FUSION_ROOT_MISMATCH');
const altered=structuredClone(plan); altered.jobs[0].spec.successMetric+=' changed';
let planTamperRejected=false;
try{verifyPlan(altered);}catch{planTamperRejected=true;}
if(!planTamperRejected) throw Error('FUSION_TAMPER_NOT_REJECTED');
const observation=(value,basis,reference)=>({value,basis,reference});
const unknown=reference=>observation(null,'unknown',reference);
const successful=bindings.cases.filter(row=>row.passing_execution_reports>0).length;
const baseline=bindings.cases.filter(row=>row.before_records.some(r=>r.reported_accepted)).length;
const discovery={schema:'alpha-discovery/v1',
  mission:'Restore an eligible authorized analytical notebook to a portable verified digital handoff at a sustainable accepted-outcome price.',
  baseline:'Customer attempts recovery using its existing staff and tools, or abandons the analysis.',
  alternative:'Competent human provider or a maintained free notebook edition where equivalent; exact matched service performance unmeasured.',
  candidate:'Bounded Analytical Recovery Capsule, with executed public analogues and separately modeled commercial economics.',
  changed:'The study executes model-assisted recovery, independent checks and packaging with existing tool capability. Incremental Operational Alpha is not established.',
  rights:'Public study fixture; source licenses preserved. Future customer reuse requires mission-specific authority; no private credentials or live ENS identity used.',
  evidence:[{kind:'experiment',claim:`${successful} current delivery cases have at least one passing local report; digests bind original and repaired artifacts.`,reference:`sha256:${input.binding_sha256}`,basis:'supplied-report',supports:['candidate','change']},
    {kind:'lesson',claim:'A free newer handbook edition is a material conventional alternative; these examples are not customers.',reference:'protocol.json selection.bias',basis:'supplied-report',supports:['alternative','baseline']}],
  constraints:[{name:'Complete actual resource billing',status:'unknown',reference:'native Charge records retain null accruals.'},
    {name:'Paid customer acceptance at the frozen price',status:'unknown',reference:'Zero actual buyers and collections.'},
    {name:'Mission-specific rights for private customer inputs',status:'unknown',reference:'Only public licensed analogues executed.'}],
  metrics:[
    {name:'Local computational case acceptance','unit':'cases','category':'benefit','direction':'higher','minimumGain':0,
      baseline:observation(baseline,'supplied-report','Bound unchanged-source execution reports'),alternative:unknown('No matched current-edition experiment'),candidate:observation(successful,'supplied-report','Bound local execution reports')},
    {name:'Complete actual delivery cost','unit':'USD micro-units','category':'cost','direction':'lower','minimumGain':0,baseline:unknown('No matched bill'),alternative:unknown('Human reference is estimated'),candidate:unknown('Actual API and resource accruals unavailable')},
    {name:'Independent acceptance checks','unit':'passing report files','category':'proof','direction':'higher','minimumGain':0,baseline:unknown('No matched independent provider evaluation'),alternative:unknown('No matched independent provider evaluation'),candidate:observation(bindings.cases.reduce((n,c)=>n+c.independent_passing_reports,0),'supplied-report','Bound independent fresh-case report files')},
    {name:'Unresolved customer failure risk','unit':'basis points','category':'risk','direction':'lower','minimumGain':0,baseline:unknown('Unmeasured'),alternative:unknown('Unmeasured'),candidate:unknown('Not calibrated from purposive examples')},
    {name:'Actual customer attention','unit':'minutes','category':'human','direction':'lower','minimumGain':0,baseline:unknown('No customer'),alternative:unknown('No customer'),candidate:unknown('No customer')}
  ]
};
const insightInput=validate(discovery), insight=analyze(insightInput);
if(insight.authority!=='none'||insight.independentProof!==false) throw Error('UNEXPECTED_INSIGHT_AUTHORITY');
const save=(name,value)=>fs.writeFileSync(path.join(outputDirectory,name),JSON.stringify(value,null,2)+'\n');
save('native_nova_seed.json',sealed);
save('native_fusion_plan.json',plan);
save('native_insight.json',{input:insightInput,analysis:insight});
const result={
  nova_seed:{status:'EXECUTED_LOCAL',payload_hash:await hashObject(genome),commitment:sealed.commitment,opened_payload_equal:true,tampered_ciphertext_rejected:tamperRejected,
    credential_status:'Public reproducibility fixture passphrase; no confidentiality or live secret claimed.'},
  fusion_plan:{status:'EXECUTED_LOCAL_COMPILE_AND_VERIFY',jobs:plan.jobs.length,plan_root:plan.planRoot,total_nominal_bounty_base_units:plan.totalBounty,token:plan.token,decimals:plan.decimals,
    tampered_specification_rejected:planTamperRejected,nominal_duration_seconds:172800,bounty_boundary:'100 base units per job are a schema demonstration; no funding, token issuance, USDC revenue, market value or live assignment.'},
  insight:{status:'EXECUTED_LOCAL_VALIDATE_AND_ANALYZE',decision:insight.decision,authority:insight.authority,independent_proof:insight.independentProof,
    boundary:'Native evidence-needed result preserves unknown paid demand and actual billing. It does not override the separately reported conditional commercial simulation.'}
};
console.log(JSON.stringify(result));
