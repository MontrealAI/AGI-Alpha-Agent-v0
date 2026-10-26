// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {buildForest,buildGraphEpoch,digest,ZERO_ROOT,canonicalize} from './commitments.mjs';
import {createFixtureResolver,createFixtureAttestation,createFixtureRoot} from './authority.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const load=relative=>JSON.parse(readFileSync(path.join(ROOT,relative),'utf8'));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const file=relative=>({path:relative,sha256:sha(readFileSync(path.join(ROOT,relative)))});
const save=(relative,value)=>{const full=path.join(ROOT,relative);mkdirSync(path.dirname(full),{recursive:true});writeFileSync(full,JSON.stringify(value,null,2)+'\n',{flag:'wx'});};

export function buildCatalog({baseline='evidence/development/final-source-baseline',output='evidence/catalog'}={}) {
  const packet=load(baseline+'/packet.json');
  if(packet.accepted!==true||packet.decision!=='CONSISTENT')throw Error('INDEPENDENT_ACCEPTED_DEVELOPMENT_REQUIRED');
  const executedSource=load(baseline+'/source-identity.json');
  if(packet.source_sha256!==executedSource.sha256||sha(Buffer.from(canonicalize(executedSource.files)))!==executedSource.sha256)throw Error('DEVELOPMENT_SOURCE_MANIFEST_INVALID');
  for(const entry of executedSource.files)if(sha(readFileSync(path.join(ROOT,entry.path)))!==entry.sha256)throw Error('DEVELOPMENT_SOURCE_CHANGED:'+entry.path);
  const development=load('inputs/missions-v1/manifest.json').jobs.find(x=>x.group==='development');
  if(!development||sha(readFileSync(path.join(ROOT,development.job)))!==development.job_sha256)throw Error('DEVELOPMENT_JOB_IDENTITY');
  const reverification=spawnSync('python3',[path.join(ROOT,'src/validate_dossier.py'),'--baseline',path.join(ROOT,baseline),'--job',path.join(ROOT,development.job)],{encoding:'utf8',timeout:30000,maxBuffer:3000000});
  if(reverification.status!==0)throw Error('INDEPENDENT_ADMISSION_REVERIFICATION_FAILED:'+reverification.stderr);
  const admissionReceipt=JSON.parse(reverification.stdout);
  if(admissionReceipt.accepted!==true)throw Error('SEMANTIC_ADMISSION_REFUSED');
  save(output+'/admission-reverification.json',admissionReceipt);
  const fixture=load('fixtures/authority.json'),resolver=createFixtureResolver(fixture);
  const policy={id:'verified-capability-admission-v1',mode:'FIXTURE_ONLY',proofLevel:'LOCAL_EXECUTED_SCOPED_WITH_SAME_SESSION_VERIFICATION',
    attestationAuthority:'EXACT_DIRECT_AGENT_PLUS_ISSUE_SKILL_ATTESTATION_GRANT',rootAuthority:'EXACT_DIRECT_AGENT_PLUS_COMMIT_GRAPH_ROOT_GRANT',
    liveIdentityEnforcement:'NOT_RUN',jobsRolesChanged:false,technicalAdmission:'Exact executable binding, available dossier, independent composition, eligible scoped fixture attestation, fresh and unblocked.',
    economicAdmission:'Separate complete-cost evidence; no automatic financial admission.',fallback:'Unchanged incumbent must pass its own complete input/metadata acceptance.',
    expiryRule:'Refuse current reuse after expiry, revocation, supersession, changed authority or missing evidence. Historical validity remains separately inspectable.'};
  const scope={id:'complete-lock-metadata-v1',inputs:['agialpha-lock-job/v1','exact public wheel set','project root constraints'],outputs:['complete accepted metadata decision packet'],
    supported:['CONSISTENT','substantiated CONFLICT'],limits:['No installation, ABI, application behavior, security or release qualification','No private customer data','Exact current native marker environment only'],
    failures:['Unknown evidence, unsupported requirements or failed independent verification produces INCOMPLETE'],missionTrigger:'Substantive lock, root-requirement, environment or input identity change; title/replay labels excluded.'};
  const environment={target:packet.target_environment,tools:packet.result.tool_versions};
  const rights={implementation:'Apache-2.0',inputs:'Public wheel metadata with original third-party licenses retained',restrictions:['No private data','No authority to install, sign, transact or settle','No live ENS identity assertion']};
  const policyDigest=digest(policy,'validation-policy'),scopeDigest=digest(scope,'tested-scope'),environmentDigest=digest(environment,'tested-environment'),rightsDigest=digest(rights,'reuse-rights');
  const dossier={id:'independent-native-baseline-dossier',kind:'validation-dossier',status:'PASS_SCOPE_ONLY',
    files:[file(baseline+'/packet.json'),file(baseline+'/execution/verification.json'),file(baseline+'/execution/pack.json'),file(baseline+'/execution/inspection.json'),file(output+'/admission-reverification.json')],
    observed:'Real local offline pip resolution, independent exact-wheel closure verification and unchanged native Workbench packaging.',
    unknown:['Customer acceptance','Human attention','Complete monetary construction cost','Live agent authority'],failureHistory:['Inherited second investment slower than direct alternatives; no economic admission']};
  const evidenceDigest=digest(dossier,'validation-dossier');
  const defs=[
    {id:'lock-preflight',files:['production/retained.py'],requires:[],outputs:['exact-pip-report'],purpose:'Resolve the exact wheel lock and enforce project root constraints with ordinary pip.'},
    {id:'metadata-verifier',files:['production/verify.py'],requires:[],outputs:['independent-metadata-certificate'],purpose:'Independently inspect wheel identities, active dependency metadata, roots and captured pip result.'},
    {id:'native-workbench',files:['production/workbench.mjs',...load('native/SOURCE.json').files.map(x=>'native/'+x.path)],requires:['lock-preflight@1','metadata-verifier@1'],outputs:['native-workbench-evidence-pack'],purpose:'Run preflight and separate verifier through the unchanged SUCCESSOR Workbench and preserve its HOLD/empty-authority history.'},
    {id:'decision-delivery',files:['src/production.py','src/acceptance.py'],requires:['native-workbench@1'],outputs:['complete-lock-decision-packet'],purpose:'Produce the complete English/French decision, source manifest and usable packet without widening application claims.'}
  ];
  const skills=defs.map(spec=>{
    const files=spec.files.map(file).sort((a,b)=>a.path.localeCompare(b.path));
    const implementationDigest=digest(files,'implementation-files');
    return {id:spec.id,version:'1',state:'ADMITTED_FIXTURE_ONLY',implementation:{files,entrypoint:spec.files[0]},requires:spec.requires,
      contract:{inputs:scope.inputs,outputs:spec.outputs,purpose:spec.purpose,preconditions:['Exact source and input identities','Complete local evidence','No network dependency resolution'],limits:scope.limits},
      validationDossier:dossier.id,knownFailures:scope.failures,rights,costs:{construction:'costs/research-resource-ledger.json',validation:'costs/research-resource-ledger.json',operating:'evidence/production-summary.json',upkeep:'market/cost-assumptions.json',actualCompleteCost:'UNKNOWN'},
      rollback:'Refuse graph reuse and retain unchanged incumbent; restore evidence then revalidate a new admission record.',
      binding:{id:spec.id,version:'1',implementationDigest,dependencyDigests:[],scopeDigest,environmentDigest,policyDigest,evidenceDigest,rightsDigest,expiresAt:500}};
  });
  for(const skill of skills)skill.binding.dependencyDigests=skill.requires.map(id=>skills.find(s=>`${s.id}@${s.version}`===id).binding.implementationDigest).sort();
  const members=skills.map(x=>`${x.id}@${x.version}`);
  const composition={id:'complete-lock-native-composition-v1',kind:'composition-validation',decision:'PASS_COMBINED_WORKFLOW',members,
    scopeDigest,environmentDigest,files:[file(baseline+'/packet.json'),file(baseline+'/execution/verification.json')],
    actualExecutable:'src/production.py --route native',claim:'Development admission only; primary transfer remains untested until frozen confirmation.'};
  const compositionDigest=digest(composition,'composition-validation');
  const edges=skills.flatMap(s=>s.requires.map(target=>({id:`${s.id}-requires-${target}`,from:`${s.id}@${s.version}`,to:target,relation:'depends_on',
    scopeDigest,environmentDigest,policyDigest,compositionEvidence:compositionDigest,state:'VALIDATED_FIXTURE_ONLY'})));
  edges.push({id:'preflight-verifier-compatibility',from:'lock-preflight@1',to:'metadata-verifier@1',relation:'compatible_with',scopeDigest,environmentDigest,policyDigest,compositionEvidence:compositionDigest,state:'VALIDATED_FIXTURE_ONLY'});
  const attestations=skills.map(skill=>createFixtureAttestation(skill.binding,{nonce:`attest-${skill.id}-v1`,graphId:'agi-alpha-verified-capability-research',signer:'fixture:attestation-delegate'},resolver));
  const admissions=skills.map(skill=>({id:'admit-'+skill.id,kind:'technical-admission',skill:`${skill.id}@${skill.version}`,decision:'ADMIT_FIXTURE_ONLY',
    skillBindingDigest:digest(skill.binding,'skill-binding'),evidenceDigest,authoritySource:'EXCLUSIVE_AGENT_FIXTURE_ATTESTATION',nativeAuthority:[],economicAdmission:'UNASSESSED'}));
  const records={skill:skills,edge:edges,evidence:[dossier,composition,...admissions],proofbundle:[{id:'baseline-proofbundle',dossier:dossier.id,composition:composition.id,proofLevel:policy.proofLevel,evidenceDigest}],
    policy:[policy],attestation:attestations,revocation:[],supersession:[],metadata:[{id:'experiment-custody',source:'Additive research; original Jobs/native histories unchanged',actualCollections:'0',liveIdentityEnforcement:'NOT_RUN'},
      {id:'successor-record-reference',kind:'SuccessorRecord-projection',predecessor:'inherited-full-lock-pipeline',successor:'decision-delivery@1',mechanism:'Executable composition plus scoped graph selection; no measured self-acceleration claim',evidenceDigest}]};
  const forest=buildForest(records),snapshotDigest=digest(resolver.resolveSnapshot('fixture-state-100'),'authority-snapshot');
  const firstRecords=structuredClone(records);
  firstRecords.skill=firstRecords.skill.filter(s=>s.id!=='decision-delivery');firstRecords.edge=firstRecords.edge.filter(e=>e.from!=='decision-delivery@1');
  for(const skill of firstRecords.skill)skill.state='CANDIDATE_NO_FUTURE_INFLUENCE';
  firstRecords.attestation=firstRecords.attestation.filter(a=>a.skill.id!=='decision-delivery');
  firstRecords.evidence=firstRecords.evidence.filter(e=>e.kind!=='composition-validation'&&e.skill!=='decision-delivery@1');
  for(const evidence of firstRecords.evidence)if(evidence.kind==='technical-admission')evidence.decision='REFUSE_REUSE_PENDING_COMPOSITION';
  firstRecords.proofbundle=[];firstRecords.metadata=firstRecords.metadata.filter(x=>x.kind!=='SuccessorRecord-projection');
  firstRecords.metadata.push({id:'candidate-state-boundary',influence:'NONE_PENDING_COMPOSITION',note:'Candidate commitment only; component records and edges cannot authorize reuse before combined-workflow evidence is admitted.'});
  const prefixForest=buildForest(firstRecords);
  const firstPacket=buildGraphEpoch({forest:prefixForest,graphId:'agi-alpha-verified-capability-research',agent:'research.agent.agi.eth',chainId:31337,registry:'fixture:ens-v1',epoch:1,previousRoot:ZERO_ROOT,policyDigest,snapshotDigest});
  const firstRoot=createFixtureRoot(firstPacket,{nonce:'root-epoch-1',graphId:firstPacket.graphId,signer:'fixture:root-delegate'},resolver);
  const packetRoot=buildGraphEpoch({forest,graphId:firstPacket.graphId,agent:firstPacket.agent,chainId:31337,registry:'fixture:ens-v1',epoch:2,previousRoot:firstRoot.graphRoot,policyDigest,snapshotDigest});
  const root=createFixtureRoot(packetRoot,{nonce:'root-epoch-2',graphId:packetRoot.graphId,signer:'fixture:root-delegate'},resolver);
  const context={mode:'FIXTURE_ONLY',now:150,chainId:31337,registry:'fixture:ens-v1',graphId:packetRoot.graphId,policyDigest,currentSnapshotId:'fixture-state-100',intent:'reuse',evidenceAvailable:true,
    scopeDigest,environmentDigest,rightsDigest,output:'complete-lock-decision-packet',expectedGraphRoot:root.graphRoot,expectedEpoch:root.epoch,expectedPreviousRoot:root.previousRoot};
  const catalog={schema:'agi-alpha-validated-skill-catalog/v1',mode:'FIXTURE_ONLY',targetSkill:'decision-delivery@1',policy,scope,environment,rights,context,
    composition:{id:composition.id,evidenceDigest:compositionDigest},forest,root,history:[firstRoot,root],nativeState:'UNCHANGED_HOLD_EMPTY_AUTHORITY'};
  save(output+'/catalog.json',catalog);save(output+'/epoch-1.json',{forest:prefixForest,root:firstRoot});save(output+'/epoch-2.json',{forest,root});
  save(output+'/admissions.json',{schema:'agi-alpha-graph-admission-sidecar/v1',mode:'FIXTURE_ONLY',live_identity_enforcement:'NOT_RUN',native_pack:file(baseline+'/execution/pack.json'),
    graph_root:root.graphRoot,technical_admissions:admissions,economic_admission:'UNASSESSED',actualCollections:0,
    note:'Research sidecar references the unchanged native Workbench history; it does not grant native operating authority or settlement.'});
  return {catalog,bytes:Buffer.byteLength(canonicalize(catalog)),records:Object.fromEntries(Object.entries(forest.classes).map(([k,v])=>[k,v.count])),root:root.graphRoot};
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
  const output=process.argv[2]||'evidence/catalog';if(existsSync(path.join(ROOT,output,'catalog.json')))throw Error('PRESERVE_EXISTING_CATALOG');
  const result=buildCatalog({output});console.log(JSON.stringify({bytes:result.bytes,records:result.records,root:result.root}));
}
