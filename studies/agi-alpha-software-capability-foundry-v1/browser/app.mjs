// SPDX-License-Identifier: Apache-2.0
import { createWorkbench } from './vendor/alpha/examples/successor-workbench/engine.mjs';
import { canonical, parseBounded } from './vendor/alpha/docs/assets/successor/engine.mjs';
import { createAdapter, sha256 } from './adapter.mjs';

const $ = id => document.getElementById(id);
const KEY = 'agialpha.software-capability-foundry.workspace.v1';
const STAGES = ['A','B','C','D'];
let sourceHash, workbench, example, research, state, controller, paused=false, busy=false, ready=false;
async function resource(name,options={}) {
  const embedded=document.getElementById('foundry-embedded-resources');
  if(embedded){const entries=JSON.parse(embedded.textContent);if(!Object.hasOwn(entries,name))throw Error('Packaged resource is unavailable: '+name);const raw=atob(entries[name]);return new Response(Uint8Array.from(raw,c=>c.charCodeAt(0)));}
  return fetch(name,options);
}
const newState = () => ({schema:'foundry-workspace/v1',sourceHash,nextStage:0,completed:[],instrument:null,pending:null,status:'ready',journal:[],retirements:[]});
const message = text => { $('notice').textContent=text; };
function failure(error) { $('error').hidden=false; $('error').textContent=error.message || String(error); }
function clearFailure() { $('error').hidden=true; $('error').textContent=''; }
function log(kind,data={}) { state.journal.push({at:new Date().toISOString(),kind,...data}); }
function persist() {
  const raw=JSON.stringify(state);
  if (new TextEncoder().encode(raw).byteLength>2_000_000) throw Error('Workspace exceeds the 2 MB recovery bound. Export a smaller workspace before continuing.');
  try { localStorage.setItem(KEY,raw); $('recovery-note').textContent='Saved on this device. Reopening stays inactive until you choose to continue.'; }
  catch { $('recovery-note').textContent='Device storage is unavailable. Use Export workspace to preserve your completed results.'; }
}
function download(name,content,type='application/json') {
  const url=URL.createObjectURL(new Blob([content],{type}));
  const a=document.createElement('a'); a.href=url; a.download=name; document.body.append(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function textElement(tag,text,className='') { const node=document.createElement(tag); node.textContent=text; if(className)node.className=className; return node; }
function showPack(pack) {
  const result=pack.result, info=result.evidence.output, summary=result.summary;
  const stage=summary.stage;
  $('status-tag').textContent=result.decision.replaceAll('_',' ');
  $('status-tag').className='status-tag '+(result.decision==='REFUSED_OUT_OF_SCOPE'?'refused':'positive');
  const headings={A:'The source bytes match.',B:'The instrument works on a fresh portfolio.',C:'The differences are now precise.',D:'The boundary was respected.',custom:'Your file comparison is ready.'};
  const descriptions={A:'Eight complete source files were checked against the pinned public snapshot. The retained local instrument has a version, code identity and explicit limits.',B:'Eight different gallery assets were checked using the exact instrument retained from Mission A. Each parent invocation appears in the downloaded trace.',C:'A fixed authored constructor used the earlier instrument twice and produced a different output: a drift report. This case includes four deliberately seeded changes.',D:'A parent-traversal path was refused before file content was read. The accepted instrument stays available for supported work.',custom:'This compares only the text files you selected. No uploaded code is executed and no bytes are sent to a remote service.'};
  $('result-title').textContent=result.decision==='REFUSED_OUT_OF_SCOPE'?'The boundary was respected.':headings[stage] || 'Inspected result'; $('result-description').textContent=result.decision==='REFUSED_OUT_OF_SCOPE'?'This input is outside the instrument’s declared scope. Reuse was refused; completed prior evidence remains available.':descriptions[stage] || '';
  $('files-count').textContent=String(summary.files); $('bytes-count').textContent=summary.bytes.toLocaleString(); $('parent-count').textContent=String(summary.parentInvocations);
  $('elapsed').textContent=pack.economics.elapsedMilliseconds.toLocaleString()+' ms';
  const out=$('output');out.className='output';out.replaceChildren();
  if(info.schema==='foundry-text-snapshot/v1') {
    const table=document.createElement('table'),head=document.createElement('thead'),tr=document.createElement('tr');
    tr.append(textElement('th','FILE / COMPUTED SHA-256'),textElement('th','CORRECTNESS'));head.append(tr);table.append(head);
    const body=document.createElement('tbody');
    for(const file of info.files) {const row=document.createElement('tr'),name=textElement('td',file.path);name.append(textElement('code',file.sha256));row.append(name,textElement('td','Exact bytes · '+file.bytes.toLocaleString()+' B'));body.append(row);}
    table.append(body);out.append(table);
  } else if(info.schema==='foundry-drift-report/v1') {
    if(info.exact) out.append(textElement('p','All filenames, modes and byte hashes match.'));
    else {const list=document.createElement('ul');for(const [key,label] of [['changed','Changed'],['missing','Missing'],['unexpected','Unexpected'],['modeChanged','Mode changed']])for(const name of info[key]){const item=document.createElement('li');item.append(textElement('span',label,'drift-label'),document.createTextNode(name));list.append(item);}out.append(list);}
    out.append(textElement('code','Baseline '+info.before),textElement('code','Candidate '+info.after));
  } else {out.append(textElement('p',info.reason),textElement('p','Action: refuse reuse. External writes: 0.'));
  }
  $('download-result').disabled=false;
  $('download-result').onclick=()=>download('foundry-mission-'+stage.toLowerCase()+'-pack.json',JSON.stringify(pack,null,2)+'\n');
}
function render() {
  if(!state)return;
  $('journey-status').textContent=busy?(paused?'Paused':'Running'):state.status==='complete'?'Complete':state.status;
  const retired=state.nextStage>0&&!state.instrument;
  const button=$('continue');button.disabled=!ready||busy||state.nextStage>=4||retired;
  button.firstChild.textContent=state.nextStage>=4?'Example complete':retired?'Instrument retired':state.pending?'Resume interrupted mission ':'Run mission '+STAGES[state.nextStage]+' ';
  $('try').disabled=!ready||busy||(retired&&state.nextStage<4); $('try').firstChild.textContent=state.nextStage>=4?'Review the result ':state.completed.length?'Continue example ':'Try it now ';
  $('pause').disabled=!busy; $('pause').textContent=paused?'Resume':'Pause'; $('stop').disabled=!busy;
  $('export').disabled=busy||!state.completed.length; $('rollback').disabled=busy||!state.instrument;
  $('compare-own').disabled=!ready||busy||!$('rights').checked||!$('baseline-files').files.length||!$('candidate-files').files.length;
  $('restore').disabled=busy;
  for(const row of $('stages').children) {const stage=row.dataset.stage,done=state.completed.find(pack=>pack.result.summary.stage===stage);row.className=done?'done':STAGES[state.nextStage]===stage?'current':'';row.querySelector('.step-state').textContent=done?done.result.decision==='REFUSED_OUT_OF_SCOPE'?'Correct refusal':'Evidence available':STAGES[state.nextStage]===stage?(busy?'Running':'Ready to run'):'Awaiting prior work';row.tabIndex=done?0:-1;row.setAttribute('role','button');row.setAttribute('aria-disabled',String(!done));}
  $('asset-hash').textContent=state.instrument?'Instrument SHA-256\n'+state.instrument:state.retirements.length?'Instrument retired. Historical evidence preserved.':'No accepted local instrument yet.';
}
function stageInput(index) {
  const stage=STAGES[index],files=structuredClone(stage==='A'?example.mission_a:example.mission_b),base={stage,files,parent:state.instrument};
  if(stage==='C') {
    base.candidate=files.map(({expected,...file})=>({...file}));
    base.candidate[0].text+='\n/* Deliberately seeded local drift fixture. */\n';
    base.candidate[1].mode='100755';base.candidate.pop();
    base.candidate.push({path:'generated/NOTICE.txt',mode:'100644',text:'New illustrative generated notice.\n'});
  }
  if(stage==='D')base.files=[{path:'../outside-the-snapshot.txt',mode:'100644',text:'This path must be refused before content processing.'}];
  return base;
}
function mission(input) {return {schema:'successor-workbench/v1',family:'software-capability-foundry',name:'Software Capability Foundry',language:'en',owner:'local-browser-user',rights:{dataClass:input.stage==='custom'?'licensed-nonpersonal':'public',source:input.stage==='custom'?'User-selected permitted text files':'Pinned public AGI ALPHA source '+example.source_commit,license:input.stage==='custom'?'User asserts permission for this local comparison':example.license},reviewMinutes:10,inputs:input};}
function assertExample(pack) {
  const stage=pack.result.summary.stage,output=pack.result.evidence.output;
  if(['A','B'].includes(stage)&&pack.result.decision!=='VERIFIED_SNAPSHOT')throw Error('Public example correctness check failed.');
  if(stage==='C'&&(!['changed','missing','unexpected','modeChanged'].every(key=>output[key].length===1)||output.exact))throw Error('The seeded drift did not match its public oracle.');
  if(stage==='D'&&pack.result.decision!=='REFUSED_OUT_OF_SCOPE')throw Error('The out-of-scope path was not refused.');
}
async function execute(input,index=null) {
  if(busy||!ready)return;clearFailure();busy=true;paused=false;controller=new AbortController();
  const pending={stage:input.stage,index,startedAt:new Date().toISOString()};state.pending=pending;state.status='running';log('started',{stage:input.stage});persist();render();message('Computing from the supplied bytes through the existing workbench…');
  try {
    const pack=await workbench.run(mission(input),{sourceHash,signal:controller.signal,onProgress:phase=>message('Live local computation · '+phase.replaceAll('-',' ')),onCheckpoint:async()=>{while(paused&&!controller.signal.aborted)await new Promise(resolve=>setTimeout(resolve,40));}});
    assertExample(pack);await workbench.inspectPack(pack);
    const next=structuredClone(state);next.completed.push(pack);
    if(new TextEncoder().encode(JSON.stringify(next)).byteLength>1_900_000)throw Error('The next result would exceed the recovery workspace bound. Existing history remains intact.');
    state=next;state.instrument=pack.result.evidence.retainedInstrument?pack.result.evidence.instrumentId:state.instrument;
    if(index!==null)state.nextStage=index+1;state.pending=null;state.status=state.nextStage>=4?'complete':'ready';log('completed',{stage:input.stage,packDigest:pack.integrityDigest});persist();showPack(pack);
    message(input.stage==='D'?'All four local cases complete. Inspect the research record for the separate confirmation results.':'Result verified and saved locally. '+(index!==null&&index<3?'Continue to Mission '+STAGES[index+1]+'.':'Download or export the evidence.'));
  } catch(error) {
    state.status=controller.signal.aborted?'stopped':'interrupted';log(controller.signal.aborted?'stopped':'failed',{stage:input.stage,reason:error.message});persist();
    if(controller.signal.aborted)message('Stopped. Completed results remain saved. The interrupted mission can be restarted explicitly.');else failure(error);
  } finally {busy=false;paused=false;controller=null;render();}
}
async function runNext() {if(state.nextStage>=4){$('workspace').scrollIntoView({behavior:'smooth'});return;}await execute(stageInput(state.nextStage),state.nextStage);}
async function inspectWorkspace(raw) {
  const incoming=parseBounded(raw);
  if(incoming.schema!=='foundry-workspace/v1'||incoming.sourceHash!==sourceHash||!Number.isInteger(incoming.nextStage)||incoming.nextStage<0||incoming.nextStage>4||!Array.isArray(incoming.completed)||incoming.completed.length>12||!Array.isArray(incoming.journal)||incoming.journal.length>1000||!Array.isArray(incoming.retirements))throw Error('Unsupported or differently bound workspace. Current work was not changed.');
  for(const pack of incoming.completed)await workbench.inspectPack(pack);
  const stages=incoming.completed.map(pack=>pack.result.summary.stage).filter(s=>s!=='custom');
  if(new Set(stages).size!==stages.length||STAGES.slice(0,incoming.nextStage).some(s=>!stages.includes(s)))throw Error('Workspace has missing or duplicate completed missions.');
  if(incoming.instrument!==null&&!incoming.completed.some(pack=>pack.result.evidence.instrumentId===incoming.instrument&&pack.result.evidence.retainedInstrument))throw Error('Retained instrument has no accepted local source.');
  incoming.status=incoming.pending?'interrupted':incoming.nextStage>=4?'complete':'ready';
  return incoming;
}
async function ownFiles(list) {
  if(list.length<1||list.length>128)throw Error('Select between 1 and 128 files for each set.');
  if([...list].reduce((sum,file)=>sum+file.size,0)>1_000_000)throw Error('Each file set must be at most 1 MB.');
  const rows=[];for(const file of list){const bytes=await file.arrayBuffer();let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);}catch{throw Error('Only valid UTF-8 text files are supported.');}rows.push({path:file.name,mode:'100644',text});}return rows;
}
function wire() {
  $('try').onclick=()=>{$('workspace').scrollIntoView({behavior:'smooth'});void runNext();};$('continue').onclick=()=>void runNext();
  $('pause').onclick=()=>{paused=!paused;log(paused?'paused':'resumed',{stage:state.pending?.stage});persist();message(paused?'Paused. No new file is processed until you resume.':'Resuming the same bounded local mission.');render();};
  $('stop').onclick=()=>{controller?.abort();paused=false;};
  $('export').onclick=()=>download('agi-alpha-foundry-workspace.json',JSON.stringify({...state,status:state.pending?'interrupted':state.status},null,2)+'\n');
  $('rollback').onclick=()=>{clearFailure();state.retirements.push({instrument:state.instrument,at:new Date().toISOString()});state.instrument=null;state.status='rolled-back';log('instrument-retired');persist();render();message('Selected instrument retired. All completed evidence and history remain available for export.');};
  $('restore').onchange=async event=>{clearFailure();try{const file=event.target.files[0];if(!file)return;if(file.size>2_000_000)throw Error('Workspace exceeds 2 MB.');const restored=await inspectWorkspace(await file.text());state=restored;log('restored-inactive');persist();if(state.completed.length)showPack(state.completed.at(-1));render();message('Workspace inspected and restored inactive. No mission was executed by restoration.');}catch(error){failure(error);}finally{event.target.value='';}};
  for(const row of $('stages').children){const activate=()=>{const pack=state.completed.find(p=>p.result.summary.stage===row.dataset.stage);if(pack)showPack(pack);};row.onclick=activate;row.onkeydown=event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();activate();}};}
  for(const id of ['rights','baseline-files','candidate-files'])$(id).onchange=render;
  $('compare-own').onclick=async()=>{clearFailure();try{if(!state.instrument)throw Error('Run Mission A first to retain the local instrument.');if(!$('rights').checked)throw Error('Confirm permitted nonpersonal inputs.');const files=await ownFiles($('baseline-files').files),candidate=await ownFiles($('candidate-files').files);await execute({stage:'custom',files,candidate,parent:state.instrument});$('workspace').scrollIntoView({behavior:'smooth'});}catch(error){failure(error);}};
}
function showResearch(data) {
  $('research-headline').textContent=data.headline;
  $('research-status').textContent=data.status;
  $('research-findings').replaceChildren();for(const finding of data.findings||[]){const card=textElement('article','','finding');card.append(textElement('span',finding.label),textElement('strong',finding.value),textElement('p',finding.note));$('research-findings').append(card);}
  $('research-limits').replaceChildren();for(const limit of data.limits||[])$('research-limits').append(textElement('li',limit));
  $('research-links').replaceChildren();for(const link of data.links||[]){if(!/^(?:\.\.?\/|https:\/\/)/.test(link.href))continue;const a=textElement('a',link.label+' ↗');a.href=link.href;if(link.download===true)a.download=link.href.split('/').at(-1);$('research-links').append(a);}
}
async function initialize() {
  wire();
  try {
    const manifest=await (await resource('source-manifest.json',{cache:'no-store'})).json();
    if(manifest.schema!=='foundry-browser-source/v1')throw Error('Browser source manifest is missing.');
    for(const [name,expected] of Object.entries(manifest.files)){if(name.includes('..')||name.startsWith('/'))throw Error('Unsafe source path.');const response=await resource(name,{cache:'no-store'});if(!response.ok)throw Error('Pinned browser source is unavailable.');const data=await response.arrayBuffer();if(data.byteLength!==expected.bytes||await sha256(data)!==expected.sha256)throw Error('Pinned source verification failed: '+name);}
    sourceHash=await sha256(canonical(manifest.files));if(sourceHash!==manifest.sourceHash)throw Error('Browser source closure does not match.');
    workbench=createWorkbench([createAdapter(manifest.files['adapter.mjs'].sha256)]);
    example=await (await resource('example-data.json')).json();research=await(await resource('research.json',{cache:'no-store'})).json();showResearch(research);
    if(document.getElementById('foundry-embedded-resources')){for(const a of document.querySelectorAll('a[download]')){const name=a.getAttribute('href').replace(/^\.\//,'');a.addEventListener('click',async event=>{event.preventDefault();const response=await resource(name);download(name.split('/').at(-1),await response.arrayBuffer(),name.endsWith('.mjs')?'text/javascript':name.endsWith('.md')?'text/markdown':'application/json');});}}
    state=newState();let saved;try{saved=localStorage.getItem(KEY);}catch{}
    if(saved){try{state=await inspectWorkspace(saved);if(state.completed.length)showPack(state.completed.at(-1));message(state.pending?'Interrupted work found. Explicitly resume to restart the incomplete mission.':'Previous workspace restored inactive. No completed mission was run again.');}catch(error){failure(error);message('Saved workspace has another or invalid source binding. A new inactive workspace is ready.');}}
    else message('Pinned runtime and example bytes verified. Choose Try it now to compute the first result.');
    ready=true;render();document.documentElement.dataset.ready='true';
  } catch(error){failure(error);message('Initialization refused. No local mission was executed.');document.documentElement.dataset.ready='failed';}
}
void initialize();
