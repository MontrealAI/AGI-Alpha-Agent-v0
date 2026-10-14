// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { installCycleUI, renderCycleUI } from '../../docs/assets/nova-studio/cycle-ui.mjs';
import { createProject, preserveSignedRecord, exportProjectKit, importProjectKit } from '../../docs/assets/nova-studio/cycle.mjs';

class Element {
  constructor() { this.children=[];this.value='';this.textContent='';this.listeners=new Map(); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children=[...children]; }
  addEventListener(type,handler) { this.listeners.set(type,handler); }
  closest() { return this; }
  after() {}
  get text() { return this.textContent+this.children.map(child=>child.text).join(''); }
}
function documentFixture() {
  const elements=new Map();
  return {getElementById:id=>{
    if(!elements.has(id))elements.set(id,new Element());
    return elements.get(id);
  },createElement:()=>new Element(),createTextNode:text=>Object.assign(new Element(),{textContent:text})};
}
function mount(project) {
  globalThis.document=documentFixture();
  const flow={project,currentCycle:project.cycles[0],seedId:null,jobIds:[],runtimeResult:null};
  installCycleUI({getFlow:()=>flow,run:fn=>fn(),download:()=>{},status:()=>{},go:()=>{},packageView:()=>{},
    setNativeResult:()=>{},getLanguage:()=>'en'});
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
