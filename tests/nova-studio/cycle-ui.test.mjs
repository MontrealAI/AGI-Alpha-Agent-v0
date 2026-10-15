// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { installCycleUI, renderCycleUI } from '../../docs/assets/nova-studio/cycle-ui.mjs';
import { CYCLE_EDGES, rememberEdgeEvidence } from '../../docs/assets/nova-studio/cycle-edges.mjs';
import { createProject, preserveSignedRecord, exportProjectKit, importProjectKit } from '../../docs/assets/nova-studio/cycle.mjs';

class Element {
  constructor() { this.children=[];this.value='';this.textContent='';this.listeners=new Map();this.dataset={};this.attributes=new Map(); }
  append(...children) { this.children.push(...children);children.forEach(child=>child.parentElement=this); }
  replaceChildren(...children) { this.children=[...children]; }
  addEventListener(type,handler) { this.listeners.set(type,handler); }
  closest() { return this; }
  setAttribute(key,value) { this.attributes.set(key,value); }
  getAttribute(key) { return this.attributes.get(key); }
  contains(element) { return this===element||this.children.some(child=>child.contains(element)); }
  focus() { document.activeElement=this; }
  scrollIntoView() {}
  after() {}
  get text() { return this.textContent+this.children.map(child=>child.text).join(''); }
}
function documentFixture() {
  const elements=new Map(),created=[];
  const createElement=()=>{const element=new Element();created.push(element);return element;};
  return {getElementById:id=>{
    const existing=created.findLast(element=>element.id===id);if(existing)return existing;
    if(!elements.has(id))elements.set(id,new Element());
    return elements.get(id);
  },createElement,createTextNode:text=>Object.assign(new Element(),{textContent:text})};
}
function mount(project,options={}) {
  globalThis.document=documentFixture();
  const flow={project,currentCycle:project.cycles[0],seedId:null,jobIds:[],runtimeResult:null};
  installCycleUI({getFlow:()=>flow,run:fn=>fn(),download:()=>{},status:()=>{},go:()=>{},packageView:()=>{},
    setNativeResult:()=>{},getLanguage:()=>'en',...options});
  return flow;
}

test('encrypted historical records with unknown shapes remain inspectable without breaking recovery UI',async()=>{
  let project=await createProject(null,{title:'Recovered historical evidence'});
  for(const originalText of ['null','[]','{"candidate_verdict":"PASS"}','{"execution_binding":null}'])
    project=await preserveSignedRecord(project,{kind:'runtime-run',originalText});
  project=await preserveSignedRecord(project,{kind:'runtime-run',originalText:JSON.stringify({
    schema:'agialpha.ascension.studio-result.v1',project_id:project.projectId,cycle_id:project.activeCycleId,
    artifact_keccak256:{toString:null}})});
  project=await preserveSignedRecord(project,{kind:'settlement',originalText:'null\n'});
  const passphrase='private project recovery test phrase';
  project=await importProjectKit(JSON.stringify(await exportProjectKit(project,passphrase)),passphrase);
  const before=JSON.stringify(project),flow=mount(project);
  assert.doesNotThrow(()=>renderCycleUI(flow));
  assert.equal(document.getElementById('reuse-source').children.length,1,'Unknown evidence must not be reusable.');
  assert.match(document.getElementById('candidate-summary').text,/unrecognized historical record/i);
  assert.equal(JSON.stringify(project),before,'Rendering must retain every historical byte unchanged.');
  assert.equal(document.getElementById('cycle-graph').children[1].children.length,18,'Keep all original flowchart directions.');
});

test('well-shaped historical result and matching settlement stay selectable but require current verification',async()=>{
  let project=await createProject(null),cycleId=project.activeCycleId;
  const result={schema:'agialpha.ascension.studio-result.v1',project_id:project.projectId,cycle_id:cycleId,
    artifact_keccak256:'0x'+'a'.repeat(64),artifact_sha256:'0x'+'b'.repeat(64),candidate_verdict:'PASS',
    delivery:{digest:'c'.repeat(64)},execution_binding:{body:{market_job_id:'7'}}};
  for(const originalText of ['null',JSON.stringify(result)])
    project=await preserveSignedRecord(project,{kind:'runtime-run',originalText});
  for(const originalText of ['null\n',JSON.stringify({settlement:{delivery_digest:result.delivery.digest}})])
    project=await preserveSignedRecord(project,{kind:'settlement',originalText});
  const flow=mount(project);renderCycleUI(flow);
  const options=document.getElementById('reuse-source').children;
  assert.equal(options.length,2);assert.equal(options[1].value,result.artifact_keccak256);
  assert.match(document.getElementById('candidate-summary').text,/historical.*unverified/i);
  assert.match(document.getElementById('candidate-summary').text,/PASS/);
});


test('every edge reveals current records and safely focuses its form in EN/FR with keyboard return',async()=>{
  for(const language of ['en','fr']){
    const project=await createProject(null),navigated=[],messages=[];
    const flow=mount(project,{getLanguage:()=>language,go:step=>navigated.push(step),status:message=>messages.push(message)});
    flow.package={schema:'local-test',plan:{planRoot:'exact',jobs:[]}};flow.seedId='7';
    for(const edge of CYCLE_EDGES)for(const kind of edge.observations)
      rememberEdgeEvidence(flow,kind,{kind,verdict:'FAIL',authority:'not_granted'});
    renderCycleUI(flow);
    for(const edge of CYCLE_EDGES){
      const button=document.getElementById(`cycle-edge-${edge.id}`);
      button.listeners.get('click')();
      assert.equal(button.getAttribute('aria-expanded'),'true');
      assert.equal(document.activeElement.id,'cycle-edge-title');
      assert.match(document.getElementById('cycle-edge-title').textContent,new RegExp(edge.id));
      const record=JSON.parse(document.getElementById('cycle-edge-record').textContent);
      assert.equal(record.context.projectId,project.projectId);
      assert.deepEqual(record.observations.map(item=>item.kind),edge.observations);
      const action=document.getElementById('cycle-edge-action'),target=action.getAttribute('aria-controls');
      let activated=false;document.getElementById(target).listeners.set('click',()=>{activated=true;});
      action.listeners.get('click')();
      assert.equal(document.activeElement,document.getElementById(target));assert.equal(activated,false);
      assert.equal(navigated.at(-1),edge.target[0]);
      assert.match(messages.at(-1),language==='en'?/Navigation only/:/Navigation uniquement/);
      document.getElementById('cycle-edge-back').listeners.get('click')();
      assert.equal(document.activeElement,button);
    }
  }
});

test('open inspector updates after state changes and action activation re-resolves the live flow',async()=>{
  const flow=mount(await createProject(null));
  flow.package={schema:'local-test',plan:{planRoot:'exact',jobs:[]}};flow.seedId='7';
  flow.client={epoch:1,account:'original',profile:{chainId:31337},history:[]};
  rememberEdgeEvidence(flow,'chain',{seedId:'7',green:false});renderCycleUI(flow);
  document.getElementById('cycle-edge-E03').listeners.get('click')();
  assert.equal(document.getElementById('cycle-edge-state').dataset.state,'observed');
  document.getElementById('cycle-edge-action').focus();
  flow.client.epoch++;renderCycleUI(flow);
  assert.equal(document.getElementById('cycle-edge-state').dataset.state,'stale');
  assert.equal(document.activeElement.id,'cycle-edge-action');
  flow.client.history=[{status:'unknown',action:'seal'}];
  document.getElementById('cycle-edge-action').listeners.get('click')();
  assert.equal(document.activeElement,document.getElementById('reconcile-hash'));
  let prevented=false;
  document.getElementById('cycle-edge-inspector').listeners.get('keydown')({key:'Escape',preventDefault:()=>{prevented=true;}});
  assert.equal(prevented,true);assert.equal(document.activeElement.id,'cycle-edge-E03');
});
