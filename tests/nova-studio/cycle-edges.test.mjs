// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { CYCLE_EDGES, CYCLE_NODES, describeCycleEdges, rememberEdgeEvidence, invalidateEdgeEvidence,
  readEdgeEvidence, edgeRecordJSON } from '../../docs/assets/nova-studio/cycle-edges.mjs';
import { createProject, preserveSignedRecord } from '../../docs/assets/nova-studio/cycle.mjs';

const expected=[['Insight','Nova-Seeds'],['Nova-Seeds','MARK'],['MARK','Sovereign'],['Sovereign','Business'],
  ['Business','Marketplace'],['Marketplace','Jobs'],['Jobs','Agents'],['Agents','Value Reservoir'],
  ['Jobs','Value Reservoir'],['Value Reservoir','Nova-Seeds'],['Value Reservoir','Marketplace'],
  ['Agents','Nodes'],['Nodes','Agents'],['Architect','Sovereign'],['Sovereign','Architect'],
  ['Architect','Insight'],['Insight','Architect'],['Council','Sovereign']];
const now=Date.parse('2026-10-14T12:00:00Z');
async function fixture({prepared=false}={}) {
  const project=await createProject(null),client={epoch:1,account:'0x'+'1'.repeat(40),history:[],
    profile:{chainId:31337,profile:'synthetic-test-only',newExposureEnabled:false}};
  const flow={project,currentCycle:project.cycles[0],client,session:{client},seedId:null,package:null};
  if(prepared){flow.package={schema:'synthetic-test-only',capsuleHash:'0x'+'a'.repeat(64),
    plan:{planRoot:'0x'+'b'.repeat(64),jobs:[{index:0,spec:{goal:'Bounded synthetic test'}}]}};flow.seedId='7';}
  return flow;
}
const view=(flow,id,options={})=>describeCycleEdges(flow,{now,...options}).find(edge=>edge.id===id);

test('all 18 original directions and 12 components have distinct bilingual scope and safe navigation',async()=>{
  const flow=await fixture({prepared:true});
  assert.equal(CYCLE_NODES.length,12);assert.deepEqual(CYCLE_EDGES.map(e=>[e.from,e.to]),expected);
  for(const language of ['en','fr']){
    const edges=describeCycleEdges(flow,{language,now});
    assert.equal(new Set(edges.map(e=>e.id)).size,18);
    assert.equal(new Set(edges.map(e=>e.scope)).size,18);
    assert.equal(new Set(edges.map(e=>e.actor)).size,18);
    for(const edge of edges){
      assert.equal(edge.id,`E${String(edges.indexOf(edge)+1).padStart(2,'0')}`);
      assert.ok(edge.action.step&&edge.action.target&&edge.action.label&&edge.action.reason);
      assert.ok(edge.records.context.projectId===flow.project.projectId);
      assert.notEqual(edge.state,'observed');assert.match(edge.boundary,language==='en'?/Navigation only/:/Navigation uniquement/);
      assert.equal('execute' in edge.action,false);assert.equal('prepare' in edge.action,false);
    }
  }
});

test('empty and prepared project states never imply observed execution, settlement or approval',async()=>{
  const flow=await fixture();
  for(const edge of describeCycleEdges(flow,{now})){
    assert.equal(edge.state,'not-observed');assert.deepEqual(edge.records.observations,[]);
    if(!['E01','E04'].includes(edge.id))assert.equal(edge.action.target,'title');
  }
  flow.package={schema:'local',plan:{planRoot:'exact',jobs:[]}};
  assert.equal(view(flow,'E01').state,'local');assert.equal(view(flow,'E17').state,'local');
  for(const id of ['E07','E08','E09','E12','E13','E18'])assert.equal(view(flow,id).state,'not-observed');
  assert.equal(view(flow,'E02').action.target,'existing-seed');
});

test('opaque, malicious-looking and unknown signed history stays exact, safe and historical',async()=>{
  const flow=await fixture();
  const originals=['null','[]','{"candidate_verdict":"PASS"}','{"execution_binding":null}',
    '{"schema":"future-version","html":"<script>alert(1)</script>","authority":"granted"}'];
  for(const originalText of originals)flow.project=await preserveSignedRecord(flow.project,{kind:'runtime-run',originalText});
  flow.project=await preserveSignedRecord(flow.project,{kind:'settlement',originalText:'null\n'});
  flow.currentCycle=flow.project.cycles[0];const before=JSON.stringify(flow.project);
  for(const id of ['E07','E08','E13']){
    const edge=view(flow,id);assert.equal(edge.state,'historical-unverified');
    assert.deepEqual(edge.records.historical.signedRecords.filter(r=>r.kind==='runtime-run').map(r=>r.originalText),originals);
    assert.deepEqual(edge.records.observations,[]);
  }
  assert.equal(view(flow,'E09').state,'historical-unverified');
  assert.equal(view(flow,'E09').records.historical.signedRecords[0].originalText,'null\n');
  assert.equal(JSON.stringify(flow.project),before);
});

test('restored model decisions, assets, mission outcomes and IDs never become live observations',async()=>{
  const flow=await fixture({prepared:true});
  Object.assign(flow.currentCycle,{evaluations:[{evidence:{effectiveVerdict:'PASS'},decision:{decision:'adopt'}}],
    assets:[{trust:'verified',rights:'allowed'}],missions:[{runId:'finished',settlementId:'paid',authority:'granted'}],jobIds:['9']});
  flow.observation={green:true};flow.runtimeResult={candidate_verdict:'PASS'};
  flow.runtimeTrust={epoch:1};flow.runtimeSettlement={settlement_status:'paid'};
  for(const id of ['E06','E07','E08','E09','E10','E12','E13','E14','E15','E16','E17','E18']){
    const edge=view(flow,id);assert.equal(edge.state,'historical-unverified',id);
    assert.equal(edge.records.historical.trust,'historical-unverified');assert.deepEqual(edge.records.observations,[]);
  }
});

test('each edge uses only its specified observed sources and preserves exact negative outcomes',async()=>{
  for(const edge of CYCLE_EDGES){
    const flow=await fixture({prepared:true});
    for(const kind of edge.observations){
      rememberEdgeEvidence(flow,kind,{kind,verdict:'FAIL',amount:123456789012345678901234567890n,
        outcome:'unresolved_no_quorum',authority:'not_granted'},{now});
    }
    const result=view(flow,edge.id);
    assert.equal(result.state,edge.observations.length?'observed':'local');
    assert.deepEqual(result.records.observations.map(record=>record.kind),edge.observations);
    assert.deepEqual(result.records.missingObservations,[]);
    for(const record of result.records.observations){
      assert.equal(record.record.verdict,'FAIL');assert.equal(record.record.outcome,'unresolved_no_quorum');
      assert.equal(record.record.amount,'123456789012345678901234567890');
    }
    assert.doesNotThrow(()=>edgeRecordJSON(result.records));
    if(edge.observations.length){
      invalidateEdgeEvidence(flow);
      assert.equal(view(flow,edge.id).state,'stale');
      assert.equal(view(flow,edge.id).records.observations[0].record.verdict,'FAIL');
    }
  }
});

test('snapshot expiry, clock rollback, provider/account/profile/cycle/package/seed change invalidate views',async()=>{
  const scenarios=[
    [flow=>{flow.client.epoch++;},now],
    [flow=>{flow.client.account='0x'+'2'.repeat(40);},now],
    [flow=>{flow.client.profile.chainId=1;},now],
    [flow=>{flow.session.client={};},now],
    [flow=>{flow.currentCycle={...flow.currentCycle,cycleId:'another-cycle'};},now],
    [flow=>{flow.project={...flow.project,projectId:'another-project'};},now],
    [flow=>{flow.package={...flow.package};},now],
    [flow=>{flow.package.plan.planRoot='changed-in-place';},now],
    [flow=>{flow.seedId='8';},now],
    [()=>{},now+120000],[()=>{},now-1]
  ];
  for(const [mutate,time] of scenarios){
    const flow=await fixture({prepared:true});rememberEdgeEvidence(flow,'chain',{seedId:'7',green:true},{now});
    assert.equal(view(flow,'E02').state,'observed');mutate(flow);
    const result=view(flow,'E02',{now:time});assert.equal(result.state,'stale');
    assert.equal(result.records.observations[0].record.seedId,'7');
    assert.ok(result.records.missingObservations.includes('chain'));
  }
});

test('a JSON-cloned flow or copied serialized observations cannot restore current trust',async()=>{
  const flow=await fixture({prepared:true});rememberEdgeEvidence(flow,'chain',{seedId:'7',green:true},{now});
  const serialized=JSON.parse(JSON.stringify(flow));serialized.currentCycle=serialized.project.cycles[0];
  serialized.graphEvidence=view(flow,'E02').records.observations;
  assert.notEqual(view(serialized,'E02').state,'observed');
  assert.equal(view(serialized,'E02').records.observations.length,0);
});

test('failed/reorganized refresh invalidates older evidence without erasing it',async()=>{
  const flow=await fixture({prepared:true});rememberEdgeEvidence(flow,'chain',{blockHash:'old',seedId:'7'},{now});
  await assert.rejects(()=>readEdgeEvidence(flow,'chain',async()=>{throw Error('Reorganized receipt');}),/Reorganized/);
  assert.equal(view(flow,'E02').state,'stale');assert.equal(view(flow,'E02').records.observations[0].record.blockHash,'old');
  await readEdgeEvidence(flow,'chain',async()=>({blockHash:'new',seedId:'7'}));
  assert.equal(view(flow,'E02',{now:Date.now()}).state,'observed');
  assert.equal(view(flow,'E02',{now:Date.now()}).records.observations[0].record.blockHash,'new');
});

test('wallet change during asynchronous read never attaches evidence to the new wallet context',async()=>{
  const flow=await fixture({prepared:true});
  await readEdgeEvidence(flow,'identity',async()=>{flow.client.epoch++;return {eligible:true};});
  assert.equal(view(flow,'E04').state,'not-observed');
  rememberEdgeEvidence(flow,'identity',{eligible:true},{epoch:flow.client.epoch-1,now});
  assert.equal(view(flow,'E04').state,'not-observed');
});

test('unknown wallet effects redirect every edge to the original reconciliation form',async()=>{
  const flow=await fixture({prepared:true});
  flow.client.history=[{status:'unknown',action:'seal',hash:null}];
  const before=JSON.stringify(flow);
  for(const language of ['en','fr'])for(const edge of describeCycleEdges(flow,{language,now})){
    assert.equal(edge.state,'unknown');assert.equal(edge.action.step,'resume');assert.equal(edge.action.target,'reconcile-hash');
    assert.match(edge.action.reason,language==='en'?/Unknown effect/:/Effet inconnu/);
  }
  assert.equal(JSON.stringify(flow),before);
});


test('display snapshots are copies and shared wallet history cannot claim foreign project actions',async()=>{
  const flow=await fixture({prepared:true});
  rememberEdgeEvidence(flow,'chain',{seedId:'7',green:false},{now});
  view(flow,'E02').records.observations[0].record.green=true;
  assert.equal(view(flow,'E02').records.observations[0].record.green,false);
  flow.currentCycle.jobIds=['11'];
  flow.currentCycle.journal={transactions:[
    {action:'open',args:['7'],status:'finalized'},
    {action:'open',args:['8'],status:'finalized'},
    {action:'collect',args:['11'],status:'finalized'},
    {action:'collect',args:['12'],status:'finalized'},
    {action:'approve',args:['unrelated-spender'],status:'finalized'}]};
  assert.deepEqual(view(flow,'E03').records.historical.journal.map(item=>item.args[0]),['7','11']);
  assert.deepEqual(view(flow,'E11').records.historical.journal.map(item=>item.args[0]),['11']);
});
