// SPDX-License-Identifier: Apache-2.0
// Local zero-cap route inspection and native Jobs MissionPack continuity.
// Imported observations are never execution permission or independent proof.
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,lstatSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {inspectDiscoveryLabWorkRequest as inspectManager} from './vendored/manager-receiver/discovery-lab-work-request.mjs';
import {inspectDiscoveryLabWorkRequest as inspectJobs} from './vendored/jobs-receiver/discovery-lab-work-request.mjs';
import {canonical,payloadDigest,RESOURCE_KEYS} from './vendored/jobs-receiver/discovery-lab-contract.mjs';
import {createMissionPack,verifyMissionPack,restoreMissionPack,createSuccessor} from './vendored/jobs-core/pack.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const need=(ok,message)=>{if(!ok)throw Error(message);};
const zeros=()=>Object.fromEntries(RESOURCE_KEYS.map(k=>[k,0]));

export function verifyBridgeSources(){
  const manifest=JSON.parse(readFileSync(resolve(here,'vendored/SOURCES.json'),'utf8'));
  for(const entry of manifest.files){
    const path=resolve(here,entry.vendored_path);
    need(path.startsWith(here+'/vendored/'),'Vendor path leaves fixed root');
    need(lstatSync(path).isFile(),'Vendor source must be a regular file');
    const bytes=readFileSync(path);
    need(sha(bytes)===entry.sha256,'Vendored source changed: '+entry.vendored_path);
  }
  return manifest;
}

export async function bridgeReceipt(nativeReceipt,{artifactPath}){
  verifyBridgeSources();
  need(nativeReceipt.schema==='writer9-native-harness-receipt/v1','Unsupported native receipt');
  need(lstatSync(artifactPath).isFile(),'Artifact must be a regular file');
  const bytes=readFileSync(artifactPath),artifactHash=sha(bytes);
  const numericalArtifact=JSON.parse(bytes.toString('utf8'));
  need(artifactHash===nativeReceipt.phases.formation.artifact_sha256,'Artifact binding differs');
  need(artifactHash===nativeReceipt.phases.challenge.artifact_sha256,'Checker binding differs');
  const expectedBindings={
    missionId:'capability-00000000-0000-4000-8000-000000000009',revision:0,
    purposeDigest:sha(Buffer.from('Writer 9 constructive foresight bounded numerical artifact')),
    charterDigest:sha(Buffer.from(canonical(nativeReceipt.phases.constitution))),
    modelDigest:nativeReceipt.world.artifact_digest,
    sourceDigest:nativeReceipt.release_digest,
    evaluatorDigest:nativeReceipt.proof.protocol_digest,
  };
  const payload={schema:'writer9-checked-numerical-artifact/v1',artifactSha256:artifactHash,
    receiptCommitment:sha(Buffer.from(canonical(nativeReceipt.phases.challenge))),
    accepted:nativeReceipt.phases.challenge.accepted,
    residual:nativeReceipt.phases.challenge.max_residual,
    threshold:nativeReceipt.phases.challenge.threshold,
    scope:'Local numerical checker result; handoff independently checks byte binding only'};
  const limits={acquisitions:0,search:0,checking:100000,memoryBytes:2000000,storageBytes:1000000,
    workerCapacity:1,installations:0,elapsedMs:10000};
  const routes=[],controls=[];
  for(const [route,currency,inspect] of [['manager-usdc','USDC6',inspectManager],['jobs-agialpha','AGIALPHA18',inspectJobs]]){
    const commission={id:'writer9-check-'+route,branch:'writer9-research',route,currency,capBaseUnits:'0',status:'DRAFT_NOT_SUBMITTED'};
    const request={schema:'successor-discovery-work-request/v1',...expectedBindings,stage:'execute',inputArtifacts:[artifactHash],
      resourceLimits:limits,executionMode:'synthetic-local',commission,payloadDigest:await payloadDigest(payload),payload};
    const raw=canonical(request);
    const options={expectedBindings,expectedCommission:{id:commission.id,branch:commission.branch,route},
      inspectCampaign:async checked=>{
        const matches=canonical(checked)===canonical(payload)&&sha(readFileSync(artifactPath))===artifactHash;
        const accepted=matches&&payload.accepted;
        return {accepted,resourceUsed:{...zeros(),checking:1,memoryBytes:bytes.length},
          reasons:accepted?[]:[matches?'NUMERICAL_CHECK_REJECTED':'ARTIFACT_CHANGED']};
      }};
    const admitted=await inspect(raw,options);
    need(admitted.authority==='none'&&admitted.lifecycle.settlement==='not-connected','Route improperly conveyed authority');
    routes.push({route,currency,request,receipt:admitted,semanticScope:'Hash-bound handoff of prior local numerical check; no independent numerical examination'});
    for(const [name,run] of [
      ['stale-bindings',()=>inspect(raw,{...options,expectedBindings:{...expectedBindings,sourceDigest:'0'.repeat(64)}})],
      ['nonzero-cap',()=>inspect(canonical({...request,commission:{...commission,capBaseUnits:'1'}}),options)],
      ['altered-payload',()=>inspect(canonical({...request,payload:{...payload,artifactSha256:'0'.repeat(64)}}),options)],
    ]){
      let rejected=false,reason='';
      try{await run();}catch(error){rejected=true;reason=error.code||error.message;}
      need(rejected,'Required route refusal failed: '+name);
      controls.push({route,name,rejected,reason});
    }
  }
  const license='Apache-2.0 research records; scientific input rights remain separately documented';
  const record=(path,kind,content)=>({path,kind,rights:'owned',license,content});
  const numericalRecipes=[];
  if(numericalArtifact.schema==='writer9-readiness-demo-artifact/v1'){
    need(typeof numericalArtifact.recipe_payload_json==='string','Numerical recipe bytes are required');
    need(sha(Buffer.from(numericalArtifact.recipe_payload_json))===numericalArtifact.recipe_payload_sha256,'Numerical recipe binding differs');
    const recipe=JSON.parse(numericalArtifact.recipe_payload_json);
    need(recipe.authority==='none'&&recipe.recipe?.authority==='none','Numerical recipe cannot convey authority');
    numericalRecipes.push(record('numerical-recipe.json','replay-recipe',{
      recipePayloadJSON:numericalArtifact.recipe_payload_json,recipePayloadSha256:numericalArtifact.recipe_payload_sha256,
      interpretation:'Exact data only; fixed audited ReadinessInstrument.restore must refactor and revalidate under fresh research authority'}));
  }
  const proof=nativeReceipt.proof;
  const pack=await createMissionPack({institutionId:'writer9-fixture-institution',missionId:'writer9-constructive-foresight',
    artifacts:[
      record('world.json','program',nativeReceipt.world),record('policy.json','program',nativeReceipt.policy),
      record('candidate.json','candidate',nativeReceipt.release),record('numerical-check.json','evidence',payload),
      record('proof-history.json','proof-history',{proofId:proof.proof_id,claim:proof.claim,outcome:proof.outcome,
        releaseDigest:proof.release_digest,evidenceCommitment:proof.evidence_commitment,validUntil:proof.valid_until,
        scope:'Public RFC test-key receipt; not authenticated independent proof'}),
      record('negative-knowledge.json','negative-knowledge',{nativeControls:nativeReceipt.controls,routeControls:controls}),
      ...numericalRecipes,
      record('replay-recipe.json','replay-recipe',{sourceManifest:'vendored/SOURCES.json',artifactDigest:'sha256:'+artifactHash,
        requirement:'Use complete downloaded research source; restore never runs code or grants permission'}),
    ],chronicle:[{sourceRelease:nativeReceipt.release_digest,artifactDigest:'sha256:'+artifactHash,
      observation:'Measured local numerical output; external adoption remains unobserved'}],
    exclusions:['Active permission','Operational credentials','Customer acceptance','Prospective adoption outcomes']});
  const inspection=await verifyMissionPack(pack),restored=await restoreMissionPack(pack);
  need(inspection.authenticated===false,'Integrity is not authenticated provenance');
  need(restored.activeAuthority.length===0&&restored.proofCurrency==='absent'&&restored.executionEnabled===false,'Restore inherited permission');
  const successor=await createSuccessor(restored,{id:'writer9-next-capability',supplier:'same-frozen-local-research-source'});
  need(successor.authority.length===0&&successor.proofCurrency==='absent'&&successor.parentPackDigest===pack.digest,'Successor inherited proof or lost lineage');
  return {schema:'writer9-cross-repository-boundary-receipt/v1',routes,controls,pack,inspection,restored,successor,
    fleet:{commit:'45759fb096faf8988f58ae5ea71248d0f35a97c7',evidence:'source-inspected-only',runtimeExecuted:false,
      reason:'Current Fleet main does not provision a custom numerical-instrument executor; held lanes were not used.'},
    scope:'Two zero-cap local route inspections plus actual knowledge-only Jobs restore and successor lineage; no installed four-product or financial acceptance'};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const [receiptPath,artifactPath,destination]=process.argv.slice(2);
  need(receiptPath&&artifactPath&&destination,'Usage: node framework_bridge.mjs NATIVE_RECEIPT ARTIFACT OUTPUT');
  const result=await bridgeReceipt(JSON.parse(readFileSync(receiptPath,'utf8')),{artifactPath:resolve(artifactPath)});
  writeFileSync(destination,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({output:destination,routes:result.routes.map(r=>({route:r.route,state:r.receipt.state,currency:r.currency,authority:r.receipt.authority})),controls:result.controls.length,restoredProof:result.restored.proofCurrency,restoredAuthority:result.restored.activeAuthority,successor:result.successor.digest}));
}
