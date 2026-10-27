// SPDX-License-Identifier: Apache-2.0
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const request=JSON.parse(readFileSync(0,'utf8'));
const root=resolve(request.upstream);
const {createModeledNetwork}=await import(pathToFileURL(`${root}/graph/simulation_adapter.mjs`).href);
const {assessAlpha}=await import(pathToFileURL(`${root}/model/alpha_gate.mjs`).href);
const {contentDigest}=await import(pathToFileURL(`${root}/graph/encoding.mjs`).href);
const bytes=readFileSync(request.artifact);
const sha=createHash('sha256').update(bytes).digest('hex');
if(sha!==request.expected_sha256)throw Error('ARTIFACT_IDENTITY_MISMATCH');
const network=createModeledNetwork({networkId:'evidence-construction-conditional-transfer-v1',
  betaVersion:'same-expert-without-new-artifact-v1',scopeDigest:contentDigest('primary-report-evidence-compiler-v1'),
  environmentDigest:contentDigest('local-artifact-actual-money-assumed-identity-fixture-v1'),dependencyMap:{}});
const payload={schema:'actual-artifact-with-modeled-economic-evidence/v1',sha256:sha,
  encoding:'base64',content:bytes.toString('base64'),empiricalEconomicAdmission:false,
  provenance:'Researcher-constructed actual bytes; assumed monetary pairs; fixture identity only'};
const common={keys:['evidence-compiler'],week:0,expiryWeek:100,version:'1',privatePayload:payload,
  comparisonUniverse:{model:'same-frontier',expertTools:'same-common-tools',retainedArtifactAvailable:false}};
const rows=[];
for(const [name,deltas,available] of [
  ['conditional-positive',[1667,2083,2500,1667,2083,2500,2083,2083],false],
  ['no-gain',[0,0,0,0,0,0,0,0],false],
  ['negative-transfer',[-100,-100,-100,-100,-100,-100,-100,-100],false],
  ['already-available',[2083,2083,2083,2083,2083,2083,2083,2083],true]]){
  const id=`evidence-compiler-${name}`;
  const bindings=network.assessmentBindings({...common,id,equivalenceKey:id});
  const pairedTrials=deltas.map((delta,i)=>({probeId:`${name}-modeled-pair-${i}`,clusterId:`${name}-assumed-cluster-${i}`,
    fresh:true,baseline:{netMissionValueCents:0},candidate:{netMissionValueCents:delta}}));
  const assessment=assessAlpha({bindings,pairedTrials,lifecycleCostCents:3000,evaluationCostCents:3000,
    forecastEligibleUses:4,alreadyAvailable:available,correctnessChecksPassed:true});
  const admitted=network.admit({...common,id,assessment,evidence:{mode:'MODELED',empiricalOperationalValidation:false,
    provenanceDigest:contentDigest({scope:'Explicit assumed paired monetary worlds, not observed labor or customers',artifactSha256:sha})}});
  rows.push({case:name,assessment,admitted,evidence_type:'SIMULATED_ECONOMIC_ADMISSION'});
}
const retrieved=network.reuse({id:'evidence-compiler-conditional-positive',member:'lyra.agent.agi.eth',week:1,right:'retrieve'});
const recovered=Buffer.from(retrieved.payload?.content??'','base64');
if(!retrieved.ok||!recovered.equals(bytes))throw Error('TRANSFER_FAILED');
mkdirSync(request.out,{recursive:true});
writeFileSync(resolve(request.out,'recovered-capability-v1.zip'),recovered);
const unknown=network.reuse({id:'evidence-compiler-conditional-positive',member:'unknown.agent.agi.eth',week:1,right:'retrieve'});
const changed=network.advanceBeta('stronger-ordinary-default-v2',2);
const stale=network.reuse({id:'evidence-compiler-conditional-positive',member:'lyra.agent.agi.eth',week:3,right:'retrieve'});
const result={schema:'actual-byte-transfer-conditional-economics/v1',artifact_sha256:sha,artifact_bytes:bytes.length,
  transferred_identical_bytes:true,recipient_execution_performed_by_this_script:false,
  conditional_assessments:rows,unknown_member_refused:!unknown.ok,changed_beta_refused:!stale.ok,
  beta_transition:changed,production_admission:false,actual_economic_admission:false,live_ENS:false,
  actual_customer_revenue_cents:0,actual_complete_cost_cents:null,
  identity_mode:'EXISTING_DECLARED_FIXTURE_AUTHORITY',money_mode:'MODELED',network:network.snapshot()};
writeFileSync(resolve(request.out,'modeled-transfer.json'),JSON.stringify(result,null,2)+'\n');
process.stdout.write(JSON.stringify({artifact_sha256:sha,artifact_bytes:bytes.length,
  conditional_assessment_verdicts:rows.map(x=>[x.case,x.assessment.verdict]),
  unknown_member_refused:!unknown.ok,changed_beta_refused:!stale.ok,actual_economic_admission:false}));
