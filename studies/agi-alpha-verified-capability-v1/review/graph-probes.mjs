// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {selectWorkflow,createSelector} from '../src/selection.mjs';
import {buildForest,buildGraphEpoch,digest} from '../src/commitments.mjs';
import {createFixtureResolver,createFixtureRoot,createFixtureAttestation,authorizeRoot,authenticateAttestation} from '../src/authority.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const started=performance.now(),cpuStarted=process.cpuUsage();
const catalogPath=process.argv[2]||'evidence/development/catalog-03/catalog.json';
const output=process.argv[3]||'review/graph-probes-before.json';
const original=JSON.parse(readFileSync(path.join(ROOT,catalogPath),'utf8'));
const resolver=createFixtureResolver(JSON.parse(readFileSync(path.join(ROOT,'fixtures/authority.json'),'utf8')));
const copy=x=>structuredClone(x);
const rows=[];
const records=c=>Object.fromEntries(Object.entries(c.forest.classes).map(([k,v])=>[k,v.records.map(x=>x.record)]));
const rebind=(c,raw,label)=>{
  c.forest=buildForest(raw);
  const packet=buildGraphEpoch({forest:c.forest,graphId:c.root.graphId,agent:c.root.agent,chainId:c.root.chainId,registry:c.root.registry,
    epoch:c.root.epoch,previousRoot:c.root.previousRoot,policyDigest:c.root.policyDigest,snapshotDigest:c.root.snapshotDigest});
  c.root=createFixtureRoot(packet,{nonce:label,graphId:packet.graphId,signer:'fixture:root-delegate'},resolver);
  c.history=[c.history[0],c.root];c.context.expectedGraphRoot=c.root.graphRoot;
  c.context.expectedEpoch=c.root.epoch;c.context.expectedPreviousRoot=c.root.previousRoot;
  return c;
};
const probe=(name,c,context=c.context,expected=false)=>{
  let result,registry;
  try{result=selectWorkflow(c,context,resolver,{strategy:'graph'});}
  catch(error){result={ok:false,reasons:[String(error.message)]};}
  try{registry=selectWorkflow(c,context,resolver,{strategy:'registry'});}
  catch(error){registry={ok:false,reasons:[String(error.message)]};}
  const equalSelected=JSON.stringify(result.selected||[])===JSON.stringify(registry.selected||[]);
  rows.push({name,expected_ok:expected,observed_ok:result.ok,registry_ok:registry.ok,
    passed:result.ok===expected&&registry.ok===expected&&equalSelected,reasons:result.reasons,registry_reasons:registry.reasons,
    selected:result.selected,registry_selected:registry.selected,counters:result.counters,registry_counters:registry.counters});
  return result;
};

probe('baseline-control',copy(original),copy(original.context),true);
probe('expired-skill-refuses',copy(original),{...original.context,now:600});
probe('changed-authority-refuses',copy(original),{...original.context,now:250,currentSnapshotId:'fixture-state-200'});
probe('wrong-current-root-refuses',copy(original),{...original.context,expectedGraphRoot:'0'.repeat(64)});
probe('wrong-current-epoch-refuses',copy(original),{...original.context,expectedEpoch:999,expectedPreviousRoot:'f'.repeat(64)});

{
 const c=copy(original);c.history=[];probe('missing-root-history-refuses',c);
}
{
 const c=copy(original);c.history[0].signature.payloadDigest='f'.repeat(64);probe('unauthorized-history-prefix-refuses',c);
}
{
 const c=copy(original),raw=records(c);
 raw.revocation=[{id:'revoke-target',kind:'skill-revocation',targetSkill:'decision-delivery@1',policyDigest:c.root.policyDigest,reason:'Substantiated failure'},
                 {id:'revoke-unrelated',kind:'skill-revocation',targetSkill:'unrelated@1',policyDigest:c.root.policyDigest,reason:'Other disposition'}];
 rebind(c,raw,'probe-root-revocations');
 probe('genuine-current-revocation-refuses',c);
 const unrelated=c.forest.classes.revocation.records.find(x=>x.record.targetSkill==='unrelated@1');
 c.forest.classes.revocation.records=[copy(unrelated),copy(unrelated)];
 probe('duplicated-inclusion-cannot-hide-revocation',c);
}
{
 const c=copy(original),raw=records(c),skill=raw.skill.find(s=>s.id==='decision-delivery');
 skill.requires=[];
 raw.edge=raw.edge.filter(edge=>edge.from!=='decision-delivery@1');
 const composition=raw.evidence.find(e=>e.kind==='composition-validation');composition.members=['decision-delivery@1'];
 c.composition.evidenceDigest=digest(composition,'composition-validation');
 for(const edge of raw.edge)edge.compositionEvidence=c.composition.evidenceDigest;
 rebind(c,raw,'probe-root-dependency-removal');
 probe('root-writer-cannot-remove-attested-dependency',c);
}
{
 const c=copy(original),raw=records(c);
 raw.skill.find(s=>s.id==='decision-delivery').state='REVOKED';
 rebind(c,raw,'probe-root-inconsistent-lifecycle');
 probe('revoked-skill-state-without-lifecycle-row-refuses',c);
}
{
 const c=copy(original),raw=records(c),at=raw.attestation.findIndex(a=>a.skill.id==='decision-delivery');
 raw.attestation[at]=createFixtureAttestation(raw.skill.find(s=>s.id==='decision-delivery').binding,
   {nonce:'probe-root-writer-attestation',graphId:c.root.graphId,signer:'fixture:root-delegate'},resolver);
 rebind(c,raw,'probe-root-domain-separation');
 probe('root-writer-without-attestation-grant-refuses',c);
}
{
 const c=copy(original),raw=records(c),at=raw.attestation.findIndex(a=>a.skill.id==='decision-delivery');
 raw.attestation[at]=createFixtureAttestation(raw.skill.find(s=>s.id==='decision-delivery').binding,
   {nonce:'probe-deeper-subname',graphId:c.root.graphId,agent:'child.research.agent.agi.eth',signer:'fixture:attestation-delegate'},resolver);
 rebind(c,raw,'probe-root-deeper-subname');
 probe('deeper-agent-subname-does-not-inherit-authority',c);
}
{
 const c=copy(original);c.scope.limits=['Any application is qualified without testing'];
 probe('displayed-scope-must-match-attested-digest',c);
}
{
 const c=copy(original);c.environment.target.python_full_version='9.99.0';
 probe('displayed-environment-must-match-attested-digest',c);
}
{
 const c=copy(original);c.rights.restrictions=[];
 probe('displayed-rights-must-match-attested-digest',c);
}
{
 const c=copy(original),selector=createSelector(c,resolver,{strategy:'graph'});
 c.root.graphRoot='a'.repeat(64);c.forest.classes.revocation.records.push({record:{targetSkill:'decision-delivery@1'}});
 const result=selector.select(original.context);
 rows.push({name:'prepared-selector-owns-catalog-frame',expected_ok:true,observed_ok:result.ok,passed:result.ok===true,reasons:result.reasons});
}
{
 const c=copy(original);
 const callbackResolver={...resolver,verifyFixtureSignature(envelope){
  if(envelope.action==='ISSUE_SKILL_ATTESTATION'){
   c.forest.classes.skill.records.find(row=>row.record.id==='decision-delivery').record.requires=[];
   const composition=c.forest.classes.evidence.records.find(row=>row.record.kind==='composition-validation').record;
   composition.members=['decision-delivery@1'];c.composition.evidenceDigest=digest(composition,'composition-validation');
   for(const row of c.forest.classes.edge.records){
    if(row.record.from==='decision-delivery@1')row.record.relation='related_to';
    row.record.compositionEvidence=c.composition.evidenceDigest;
   }
  }
  return resolver.verifyFixtureSignature(envelope);
 }};
 let result;try{result=selectWorkflow(c,c.context,callbackResolver,{strategy:'graph'});}
 catch(error){result={ok:false,reasons:[String(error.message)],selected:[]};}
 const completeOriginal=result.ok&&JSON.stringify(result.selected)===JSON.stringify(['lock-preflight@1','metadata-verifier@1','native-workbench@1','decision-delivery@1']);
 rows.push({name:'direct-selector-owns-post-proof-catalog-frame',expected:'refuse or use complete immutable original',observed_ok:result.ok,
   passed:!result.ok||completeOriginal,reasons:result.reasons,selected:result.selected});
}
// snapshotDigest binds graph snapshot material; authorityStateDigest separately
// binds signer state. The generic commitment API must not conflate those values.
{
 const c=copy(original),raw=records(c);c.root.snapshotDigest='a'.repeat(64);
 rebind(c,raw,'probe-root-independent-snapshot-material');
 const result=authorizeRoot(c.root,{...c.context,admissionsVerified:true,lifecycleEvidenceVerified:true},resolver);
 rows.push({name:'graph-snapshot-and-authority-state-digests-remain-distinct',expected_ok:true,observed_ok:result.ok,passed:result.ok===true,reasons:result.reasons});
}
{
 const c=copy(original),context={...c.context,expectedEpoch:999,admissionsVerified:true,lifecycleEvidenceVerified:true};
 const callbackResolver={...resolver,resolveSnapshot(id){context.expectedEpoch=c.root.epoch;return resolver.resolveSnapshot(id);}};
 const result=authorizeRoot(c.root,context,callbackResolver);
 rows.push({name:'root-authorizer-owns-precallback-context',expected_ok:false,observed_ok:result.ok,passed:result.ok===false,reasons:result.reasons});
}
{
 const c=copy(original),skill=c.forest.classes.skill.records.find(r=>r.record.id==='decision-delivery').record;
 const attestation=c.forest.classes.attestation.records.find(r=>r.record.skill.id===skill.id).record;
 const context={...c.context,revokedSkills:['decision-delivery@1']};
 const callbackResolver={...resolver,resolveSnapshot(id){context.revokedSkills.length=0;return resolver.resolveSnapshot(id);}};
 const result=authenticateAttestation(attestation,skill.binding,context,callbackResolver);
 rows.push({name:'attestation-authorizer-owns-nested-revocation-context',expected_ok:false,observed_ok:result.ok,passed:result.ok===false,reasons:result.reasons});
}

const sourceFiles=['src/authority.mjs','src/commitments.mjs','src/selection.mjs','src/build_catalog.mjs'];
const report={schema:'verified-capability-independent-graph-probes/v1',scope:'Same-session independent source reviewer; bounded fixture logic, no live ENS, signature, transaction, application or commercial claim',catalog:catalogPath,
  source:sourceFiles.map(p=>({path:p,sha256:createHash('sha256').update(readFileSync(path.join(ROOT,p))).digest('hex')})),
  valid_baseline_control:rows[0].passed,passed:rows.filter(x=>x.passed).length,failed:rows.filter(x=>!x.passed).length,rows};
const cpuUsed=process.cpuUsage(cpuStarted);
report.review_resources={elapsed_seconds:(performance.now()-started)/1000,cpu_seconds:(cpuUsed.user+cpuUsed.system)/1e6,
  model_calls_in_script:0,network_calls:0,transactions:0,reviewer_attention:'UNKNOWN',authoring_inference_cost:'UNKNOWN'};
report.probe_source_sha256=createHash('sha256').update(readFileSync(fileURLToPath(import.meta.url))).digest('hex');
writeFileSync(path.join(ROOT,output),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(report));
