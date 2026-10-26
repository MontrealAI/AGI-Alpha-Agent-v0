// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createFixtureResolver,createFixtureRoot,fixtureSignature} from '../src/authority.mjs';
import {buildForest,buildGraphEpoch,digest} from '../src/commitments.mjs';
import {selectWorkflow} from '../src/selection.mjs';

const base=JSON.parse(readFileSync(new URL('../evidence/catalog/catalog.json',import.meta.url)));
const resolver=createFixtureResolver(JSON.parse(readFileSync(new URL('../fixtures/authority.json',import.meta.url))));
const clone=value=>structuredClone(value),records=c=>Object.fromEntries(Object.entries(c.forest.classes).map(([type,v])=>[type,v.records.map(x=>x.record)]));
function rewritten(change,{append=false}={}){
  const c=clone(base),r=records(c);change(r,c);c.forest=buildForest(r);
  const packet=buildGraphEpoch({forest:c.forest,graphId:c.root.graphId,agent:c.root.agent,chainId:c.root.chainId,registry:c.root.registry,epoch:c.root.epoch+(append?1:0),previousRoot:append?c.root.graphRoot:c.root.previousRoot,policyDigest:c.root.policyDigest,snapshotDigest:c.root.snapshotDigest});
  const root=createFixtureRoot(packet,{nonce:'diagnostic-root-'+digest(r,'control').slice(0,10),graphId:packet.graphId,signer:'fixture:root-delegate'},resolver);
  c.history=append?[...c.history,root]:[c.history[0],root];c.root=root;c.context={...c.context,expectedGraphRoot:root.graphRoot,expectedEpoch:root.epoch,expectedPreviousRoot:root.previousRoot};return c;
}
const cases=[];
const add=(id,c=base,context=c.context,expected=false,extra={})=>cases.push({id,c,context,expected,...extra});
add('fresh-in-scope',base,base.context,true);
add('expired',base,{...base.context,now:501});
add('transferred-authority',base,{...base.context,now:250,currentSnapshotId:'fixture-state-200'});
add('wrong-environment',base,{...base.context,environmentDigest:'0'.repeat(64)});
add('wrong-scope',base,{...base.context,scopeDigest:'0'.repeat(64)});
add('wrong-rights',base,{...base.context,rightsDigest:'0'.repeat(64)});
add('stale-root-anchor',base,{...base.context,expectedGraphRoot:base.history[0].graphRoot});
add('revoked-skill',rewritten(r=>r.revocation.push({id:'revocation-control',kind:'skill-revocation',targetSkill:'decision-delivery@1',reason:'Controlled diagnostic revocation',policyDigest:base.root.policyDigest}),{append:true}));
add('superseded-skill',rewritten(r=>r.supersession.push({id:'supersession-control',kind:'skill-supersession',predecessor:'decision-delivery@1',successor:'replacement-unadmitted@2',policyDigest:base.root.policyDigest}),{append:true}));
add('unavailable-evidence',rewritten(r=>r.evidence.find(x=>x.kind==='validation-dossier').files[0].path='evidence/does-not-exist.json'));
add('invalid-attestation',rewritten(r=>r.attestation[0].signature.payloadDigest='0'.repeat(64)));
add('club-attester',rewritten(r=>{r.attestation[0].agent='reviewer.club.agi.eth';r.attestation[0].signature=fixtureSignature(r.attestation[0]);}));
add('nested-attester',rewritten(r=>{r.attestation[0].agent='child.research.agent.agi.eth';r.attestation[0].signature=fixtureSignature(r.attestation[0]);}));
add('missing-composition-validation',rewritten(r=>r.evidence.splice(r.evidence.findIndex(x=>x.kind==='composition-validation'),1)));
add('conflicting-dependency',rewritten(r=>r.edge.push({...r.edge[0],id:'controlled-conflict',from:'decision-delivery@1',to:'native-workbench@1',relation:'conflicts_with'})));
add('unvalidated-relationship',rewritten(r=>r.edge[0].state='CANDIDATE'));
add('candidate-skill',rewritten(r=>r.skill.find(x=>x.id==='decision-delivery').state='CANDIDATE'));
const brokenHistory=clone(base);brokenHistory.history[0].previousRoot='1'.repeat(64);add('broken-root-history',brokenHistory);
const tamperedProof=clone(base);tamperedProof.forest.classes.skill.records[0].proof.siblings[0]='f'.repeat(64);add('tampered-inclusion',tamperedProof);
const result=[];
for(const scenario of cases)for(const strategy of ['registry','graph']){
  const actual=selectWorkflow(scenario.c,scenario.context,resolver,{strategy});
  assert.equal(actual.ok,scenario.expected,scenario.id+':'+strategy);
  result.push({id:scenario.id,strategy,expected:scenario.expected,passed:actual.ok===scenario.expected,result:actual});
}
const ablations=[];
for(const [id,caseId,ablation] of [['remove-freshness','expired','no-freshness'],['remove-agent-authentication','invalid-attestation','no-authority'],['remove-relationship-compatibility','conflicting-dependency','no-relationships']]){
  const scenario=cases.find(x=>x.id===caseId),actual=selectWorkflow(scenario.c,scenario.context,resolver,{strategy:'graph',ablation});
  assert.equal(actual.ok,true,id+' must expose inappropriate reuse in this diagnostic');
  ablations.push({id,scenario:caseId,unsafe_diagnostic_only:true,expected_unsafe_reuse:true,result:actual});
}
const registry=selectWorkflow(base,base.context,resolver,{strategy:'registry'}),graph=selectWorkflow(base,base.context,resolver,{strategy:'graph'});
assert.deepEqual(registry.selected,graph.selected);
const output={schema:'agi-alpha-scoped-reuse-controls/v1',software_controls:result.length+ablations.length+1,passed:result.length+ablations.length+1,results:result,ablations,
  relationship_ablation:{same_selected_pipeline:true,registry:registry.counters,graph:graph.counters},
  actual_production_jobs:0,live_identity_enforcement:'NOT_RUN',identity_mode:'FIXTURE_ONLY',
  scope:'Controlled software safety and mechanism cases. Neither rejected reuse nor proof success is a new useful customer job or return on investment.',
  source_sha256:createHash('sha256').update(readFileSync(new URL(import.meta.url))).digest('hex')};
if(process.argv.includes('--write'))writeFileSync(new URL('../evidence/reuse-controls.json',import.meta.url),JSON.stringify(output,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({controls:output.software_controls,passed:output.passed,live_identity_enforcement:'NOT_RUN'}));
