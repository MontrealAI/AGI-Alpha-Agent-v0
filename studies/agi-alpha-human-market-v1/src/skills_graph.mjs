// SPDX-License-Identifier: Apache-2.0
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {digest,buildForest,buildGraphEpoch,verifyEpochInclusion} from '../../../upstream/verified-capability/src/commitments.mjs';
import {createFixtureResolver,createFixtureAttestation,createFixtureRoot,authenticateAttestation,authorizeRoot}
  from '../../../upstream/verified-capability/src/authority.mjs';

const folder=resolve(process.argv[2]);
const evidence=await readFile(resolve(process.argv[3]));
const verdict=JSON.parse(evidence.toString('utf8'));
const fixture=JSON.parse(await readFile(new URL('../../../upstream/verified-capability/fixtures/authority.json',import.meta.url),'utf8'));
const resolver=createFixtureResolver(fixture);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const implementation=sha(await readFile(new URL('./cleaner.py',import.meta.url)));
const contractHash=sha(await readFile(new URL('../protocol/DELIVERY_CONTRACT.md',import.meta.url)));
const freezeBytes=await readFile(new URL('../protocol/production-freeze.json',import.meta.url));
const freeze=JSON.parse(freezeBytes.toString('utf8'));
for(const item of freeze.files){
  const current=await readFile(new URL('../../../'+item.path,import.meta.url));
  if(sha(current)!==item.sha256)throw Error('FROZEN_GRAPH_SOURCE_DRIFT:'+item.path);
}
if(verdict.all_checks_passed!==true||verdict.production_freeze_sha256!==sha(freezeBytes)||
  verdict.contract_sha256!==contractHash)throw Error('UNQUALIFIED_FRESH_EVIDENCE');
const panel=verdict.accepted_primary_by_generation_and_class;
if(panel?.G1?.simple!==8||panel?.G1?.locale!==8||panel?.G2?.simple!==8||panel?.G2?.locale!==8||panel?.G2?.versioned!==8)
  throw Error('MISSING_SCOPED_ACCEPTANCE');
const indexBytes=await readFile(resolve(folder,'index.json'));
if(sha(indexBytes)!==verdict.sealed_index_sha256)throw Error('PREDICTION_SEAL_MISMATCH');
const policy={schema:'human-market-graph-policy/v1',mode:'FIXTURE_ONLY',liveAuthentication:'NOT_RUN',
  validatorEligibility:'direct *.agent.agi.eth; exact authenticated controller and attestation grant required',
  creator:'fixture:csv-builder',validatorSigner:'fixture:attestation-delegate',rootSigner:'fixture:root-delegate',
  executionAuthority:[],jobsClubValidation:'UNCHANGED',publicationAuthority:'UNCHANGED',
  claim:'Source and factual-scope commitment only; no usefulness or operating grant from inclusion.'};
const skills=[];
for(const g of [1,2])skills.push({id:g===1?'csv-locale-normalization':'csv-latest-version-reconciliation',version:'1',
  implementationDigest:implementation,dependencyDigests:g===2?[digest(skills[0],'skill-dependency')]:[],
  scopeDigest:digest({contractSHA256:contractHash,generation:g},'scope'),environmentDigest:digest(freeze.environment,'environment'),
  policyDigest:digest(policy,'policy'),evidenceDigest:sha(evidence),rightsDigest:digest('Apache-2.0','rights'),expiresAt:600});
const attestations=skills.map((skill,i)=>createFixtureAttestation(skill,{nonce:'hm-att-'+i,graphId:'research-graph',
  signer:'fixture:attestation-delegate',issuedAt:100,expiresAt:500},resolver));
const contexts=skills.map(skill=>({mode:'FIXTURE_ONLY',now:150,chainId:31337,registry:'fixture:ens-v1',graphId:'research-graph',
  policyDigest:skill.policyDigest,scopeDigest:skill.scopeDigest,environmentDigest:skill.environmentDigest,
  rightsDigest:skill.rightsDigest,currentSnapshotId:'fixture-state-100',evidenceAvailable:true}));
const admission=skills.map((skill,i)=>authenticateAttestation(attestations[i],skill,contexts[i],resolver));
if(admission.some(x=>!x.ok))throw Error('FIXTURE_ADMISSION_FAILED');
const forest=buildForest({skill:skills,attestation:attestations,policy:[policy],
  edge:[{from:skills[1].id,to:skills[0].id,kind:'requires',compositionEvidenceDigest:sha(evidence)}],
  evidence:[{id:'fresh-csv-validation',digest:sha(evidence),externalProfessionalAssessment:false}],
  metadata:[{creator:'fixture:csv-builder',freshness:'logical fixture time150; expires500',supersession:'explicit only'}]});
const packet=buildGraphEpoch({forest,graphId:'research-graph',agent:'research.agent.agi.eth',chainId:31337,
  registry:'fixture:ens-v1',epoch:1,policyDigest:skills[0].policyDigest,snapshotDigest:digest(fixture,'snapshot')});
const rootRecord=createFixtureRoot(packet,{nonce:'hm-root-1',graphId:'research-graph',signer:'fixture:root-delegate',
  issuedAt:100,expiresAt:500},resolver);
const rootAuth=authorizeRoot(rootRecord,contexts[0],resolver);
if(!rootAuth.ok)throw Error('FIXTURE_ROOT_FAILED');
for(const [type,group] of Object.entries(forest.classes))for(const leaf of group.records)
  if(!verifyEpochInclusion(packet,type,leaf.record,leaf.proof))throw Error('INCLUSION_FAILED');
const result={schema:'human-market-skills-graph/v1',policy,skills,attestations,admission,forest,packet,rootRecord,rootAuth,
  liveENS:'NOT_RUN',cryptographicAuthentication:false,executionAuthority:[],
  usefulness:'Defined by independent fresh-work acceptance and the separate economic test, not this root.'};
await writeFile(resolve(folder,'skills-graph.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({root:packet.graphRoot,admissions:admission.length,mode:'FIXTURE_ONLY'}));
