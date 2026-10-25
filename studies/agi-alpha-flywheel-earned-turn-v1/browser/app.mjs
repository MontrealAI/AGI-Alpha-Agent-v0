import {openMissionStore} from '../runtime/vendor/examples/successor-workbench/mission-store.mjs';
import {executeMission,inspectPack,hash,TITLES,accountFor,reserveFor} from './mission.mjs';
import {network,updated,inspectParent,validateConfig} from './core.mjs';
import {checkResponse} from './checker.mjs';
const $=id=>document.getElementById(id),fmt=n=>Math.round(n).toLocaleString('en-US'),esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export async function startApp({data}){
 let store=null,state=null,revision=null,running=false,controller=null,paused=false,selected=-1,blocked=false,writeTail=Promise.resolve();
 const revisions=new Map();
 const source=data.execution_source_hash;
 const notify=(message,error=false)=>{const e=$('app-status');e.hidden=!message;e.textContent=message;e.className='notice'+(error?' error':'');};
 function event(kind,detail={}){state.events.push({at:new Date().toISOString(),kind,...detail});if(state.events.length>150)throw Error('EVENT_LIMIT');}
 async function save(){
  const snapshot=structuredClone(state);
  const task=writeTail.then(async()=>{const expected=revisions.get(snapshot.run_id)??null;const record={missionId:snapshot.run_id,revision:expected===null?0:expected+1,payload:snapshot,payload_hash:await hash(snapshot)};await store.save(record,expected);revisions.set(snapshot.run_id,record.revision);if(state?.run_id===snapshot.run_id)revision=record.revision;});
  writeTail=task.catch(()=>{});return task;
 }
 function newState(){return {schema:'earned-turn-browser-state/v1',run_id:'earned-'+Date.now()+'-'+Math.floor(Math.random()*1e6),created_at:new Date().toISOString(),source_hash:source,stage:0,status:'READY',config:{load:Number($('load-input').value),strength:Number($('strength-input').value)},accepted:[],parent:null,successor:null,reference_factor:null,events:[],pending:null,accounts:{service:{limit:220000,spent:0},improvement:{limit:80000,spent:0}},baseline_operations:0,intervention_count:0,human_minutes:null,active_authority:[]};}
 async function validateStored(s){
  if(s.schema!=='earned-turn-browser-state/v1'||s.source_hash!==source||!Number.isSafeInteger(s.stage)||s.stage<0||s.stage>4||!Array.isArray(s.accepted)||s.accepted.length!==s.stage||s.active_authority.length!==0)throw Error('STORED_SCOPE_OR_SOURCE_CHANGED');
  for(const key of ['service','improvement']){const a=s.accounts[key];if(!Number.isSafeInteger(a.spent)||a.spent<0||a.spent>a.limit||a.limit!==(key==='service'?220000:80000))throw Error('STORED_BUDGET');}
  if(s.pending&&(s.pending.phase!==s.stage||s.pending.account!==accountFor(s.stage)||s.pending.ceiling!==reserveFor(s.stage)||s.accounts[s.pending.account].spent+s.pending.ceiling>s.accounts[s.pending.account].limit))throw Error('STORED_RESERVATION_SCOPE');
  for(const r of s.accepted){if(!r.valid||!checkResponse(r.network,r.b,r.x).valid||r.result_hash!==await hash({network:r.network,b:r.b,x:r.x}))throw Error('STORED_RESULT_CHANGED');await inspectPack(r.pack);}
  if(s.parent){inspectParent(s.parent,await hash(network()),source);const {id,...p}=s.parent;if(id!==await hash(p))throw Error('STORED_PARENT_CHANGED');}
  if(s.successor){const {id,...p}=s.successor;if(id!==await hash(p)||p.parent_id!==s.parent?.id)throw Error('STORED_SUCCESSOR_CHANGED');}
 }
 function drawNetwork(record){
  const net=record?.network||network(),values=record?.x||Array(64).fill(0),max=Math.max(...values,.0001),changed=new Set((state?.successor?.changes||[]).map(e=>e.index));
  const showChanges=record&&record.phase>=2,point=i=>[47+(i%8)*56,30+Math.floor(i/8)*47];
  let svg='<svg viewBox="0 0 486 396" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Computed node responses. Reinforced edges are gold."><defs><radialGradient id="gridGlow"><stop stop-color="#5b3682" stop-opacity=".22"/><stop offset="1" stop-color="#5b3682" stop-opacity="0"/></radialGradient></defs><ellipse cx="243" cy="195" rx="235" ry="182" fill="url(#gridGlow)"/>';
  net.edges.forEach((e,index)=>{const a=point(e.u),b=point(e.v),hot=showChanges&&changed.has(index);svg+=`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${hot?'#ecc78b':'#58466d'}" stroke-width="${hot?4:1.4}" opacity="${hot?1:.6}"/>`;});
  values.forEach((v,i)=>{const [x,y]=point(i),t=v/max,r=record?4.3+4.5*t:4.4,color=record?`rgb(${Math.round(117-16*t)},${Math.round(88+132*t)},${Math.round(151+52*t)})`:'#76628f',load=record?.b[i]>0;svg+=`<g><title>Node ${i}: response ${Number(v).toPrecision(5)}${load?', applied demand '+Number(record.b[i]).toPrecision(4):''}</title>${load?`<circle cx="${x}" cy="${y}" r="${r+5}" fill="none" stroke="#c6a3ff" stroke-width="1" opacity=".75"/>`:''}<circle cx="${x}" cy="${y}" r="${r}" fill="${color}" stroke="${record?'#a9eddf80':'#a78abb70'}" stroke-width=".7"/></g>`;});
  svg+='<text x="243" y="386" fill="#a99cbf" text-anchor="middle" font-family="system-ui,sans-serif" font-size="9" letter-spacing="1.4">64 NODES · 112 LINKS · GROUNDED AT EVERY NODE</text></svg>';
  $('network-map').innerHTML=svg;
 }
 function render(){
  const records=state?.accepted||[],record=records.find(r=>r.phase===selected)||records.at(-1),stage=state?.stage||0;
  $('start-button').disabled=blocked||running||!store||state?.status==='ROLLED_BACK'||stage===4;
  $('start-button').querySelector('span').textContent=stage===4?'Four missions complete':state?'Resume missions':'Start four missions';
  $('stop-button').disabled=!running;$('pause-button').disabled=!running;$('pause-button').textContent=paused?'Will pause after result':'Pause after result';$('reset-button').disabled=running||!store;
  $('load-input').disabled=Boolean(state);$('strength-input').disabled=Boolean(state);
  for(const id of ['download-button','download-assets','stale-button','shift-button'])$(id).disabled=running||!state||!records.length;
  $('rollback-button').disabled=running||!state?.successor||state?.status==='ROLLED_BACK';
  $('journey').innerHTML=TITLES.map((title,i)=>`<button class="${records[i]?'done ':''}${record?.phase===i?'active':''}" data-phase="${i}" ${!records[i]?'disabled':''}><span class="step"><b>${['A','B','C','D'][i]}</b>${['DELIVER','REUSE','CONSTRUCT','TRANSFER'][i]}</span><span class="step-status">${records[i]?'VERIFIED':running&&stage===i?'COMPUTING':''}</span><h3>${title}</h3></button>`).join('');
  $('journey').querySelectorAll('button').forEach(el=>el.onclick=()=>{selected=Number(el.dataset.phase);render();});
  const status=state?.status;
  $('run-status').textContent=running?`Computing mission ${['A','B','C','D'][stage]} through the local workbench…`:status==='COMPLETE'?'Four missions accepted. Select any step to inspect its result.':status==='ROLLED_BACK'?'Rolled back to the accepted parent. Successor evidence remains preserved.':state?`${stage} / 4 accepted · ${status==='PAUSED'?'paused at a durable boundary':status==='STOPPED'?'stopped; resume is explicit':status==='RECOVERED'?'recovered; interrupted attempt charged':status==='BUDGET_STOP'?'budget limit reached':'ready to resume'}`:'Ready · one start, four bounded missions, no external actions.';
  $('map-kicker').textContent=record?`MISSION ${record.mission} / ${['DELIVER','REUSE','CONSTRUCT','TRANSFER'][record.phase]}`:'A USEFUL FIRST RESULT';
  $('map-title').textContent=record?['Response to the first demand','A fresh demand, the same instrument','Two changes from the accepted result','Fresh work on the changed network'][record.phase]:'The network before a mission';
  $('valid-badge').textContent=record?'Balance verified':'Ready to compute';$('valid-badge').className='badge'+(record?'':' neutral');
  drawNetwork(record);
  const copies=['The first load is solved and independently checked. Its serialized factorization becomes a reusable response instrument.','The demand changed. The retained factor solves the fresh problem; the checker reconstructs every edge balance.','Two heavily loaded links from the actual accepted Mission B are strengthened. Two parent solves help construct a new update instrument.','A third demand is solved on the changed network. The successor applies its update and calls the retained parent; direct refactorization confirms the result.'];
  $('result-heading').textContent=record?['A result worth keeping.','An instrument used again.','A different capability built.','A successor doing fresh work.'][record.phase]:'Ready when you are.';
  $('result-copy').textContent=record?copies[record.phase]:'Start once. The workbench will compute, check and retain each accepted result before moving to the next mission.';
  $('result-metrics').innerHTML=record?`<div><dt>Peak node response</dt><dd>${Math.max(...record.x).toFixed(4)}</dd></div><div><dt>Relative residual</dt><dd class="small-value">${record.checker.relative_residual.toExponential(1)}</dd></div><div><dt>Parent solve calls</dt><dd>${record.parent_construction_calls+record.parent_execution_calls}</dd></div><div><dt>Browser elapsed</dt><dd class="small-value">${record.costs.browser_elapsed_ms.toFixed(2)} ms</dd></div>`:'<div><dt>Fresh outputs</dt><dd>0 / 4</dd></div><div><dt>Parent calls</dt><dd>0</dd></div>';
  const assets=[];
  if(state?.parent)assets.push(`<div class="asset"><span class="asset-icon">λ</span><div><strong>Parent · response factorization</strong><p>Executable triangular factors for the exact starting network.</p><code>${esc(state.parent.id.slice(0,16))}…</code></div></div>`);
  if(state?.successor)assets.push(`<div class="asset"><span class="asset-icon">Ω</span><div><strong>Successor · network update</strong><p>${state.status==='ROLLED_BACK'?'RETIRED by rollback. Evidence preserved.':'Two constructed response columns, a small update solver and a binding to Mission B.'}</p><code>${esc(state.successor.id.slice(0,16))}…</code></div></div>`);
  $('asset-list').innerHTML=assets.join('')||'<p class="muted">No acquired asset yet.</p>';
  $('cost-rows').innerHTML=records.length?records.map(r=>{const d=r.costs.reference_operations-r.costs.operations;return `<tr><td><strong>${r.mission}</strong> · ${['First response','Fresh demand','Construct update','Updated demand'][r.phase]}</td><td class="${d>=0?'num':'loss'}">${fmt(r.costs.operations)}</td><td>${fmt(r.costs.reference_operations)}</td><td>${d>0?'Less work':d<0?'Direct uses less':'Equal'}</td></tr>`;}).join(''):'<tr><td colspan="4" class="empty">Start a mission to create fresh evidence.</td></tr>';
  const spent=records.reduce((n,r)=>n+r.costs.operations,0),ref=records.reduce((n,r)=>n+r.costs.reference_operations,0);
  $('cost-total').innerHTML=records.length?`<tr><td>Accepted work total</td><td>${fmt(spent)}</td><td>${fmt(ref)}</td><td>${ref>spent?fmt(ref-spent)+' fewer':ref<spent?fmt(spent-ref)+' more':'Equal'}</td></tr>`:'';
  $('account-bars').innerHTML=['service','improvement'].map(k=>{const a=state?.accounts[k]||{spent:0,limit:k==='service'?220000:80000};return `<div class="meter ${k}"><div class="meter-head"><strong>${k==='service'?'Mission delivery':'Capability construction'}</strong><span>${fmt(a.spent)} / ${fmt(a.limit)}</span></div><div class="meter-track"><i style="width:${Math.min(100,a.spent/a.limit*100)}%"></i></div></div>`;}).join('');
  $('event-log').textContent=state?state.events.map(e=>`${e.at.slice(11,23)}  ${e.kind}  ${Object.entries(e).filter(([k])=>!['at','kind'].includes(k)).map(([k,v])=>k+'='+JSON.stringify(v)).join(' ')}`).join('\n'):'No events yet.';
  globalThis.__earnedTurnState=state;
 }
 async function initialise(){
  store=await openMissionStore({name:'agialpha.earned-turn.browser.v1'});
  const stored=(await store.list()).sort((a,b)=>String(b.payload?.created_at).localeCompare(String(a.payload?.created_at)))[0];
  if(stored){
   if(stored.payload_hash!==await hash(stored.payload))throw Error('STORED_RECORD_INTEGRITY');
   await validateStored(stored.payload);state=stored.payload;revision=stored.revision;revisions.set(state.run_id,revision);
   $('load-input').value=state.config.load;$('strength-input').value=state.config.strength;
   if(state.pending){const p=state.pending;state.accounts[p.account].spent+=p.ceiling;event('INTERRUPTED_ATTEMPT_CHARGED',{phase:p.phase,reserved_operations:p.ceiling,reason:'No accepted acknowledgement before reload'});state.pending=null;state.status='RECOVERED';await save();notify('Recovered accepted history. The interrupted attempt is charged its reserved ceiling; no partial output was admitted.');}
   else if(state.status==='RUNNING'){state.status='PAUSED';event('RESTART_AT_ACCEPTED_BOUNDARY');await save();}
  }
 }
 async function start(){
  if(running||blocked)return;
  try{
   if(!state){const candidate=newState();validateConfig(candidate.config);state=candidate;event('EXPLICIT_START',{missions:4});state.intervention_count++;await save();}
   else{await validateStored(state);event('EXPLICIT_RESUME');state.intervention_count++;}
   running=true;paused=false;controller=new AbortController();state.status='RUNNING';await save();notify('');render();
   while(state.stage<4&&!paused&&!controller.signal.aborted){
    const phase=state.stage,account=accountFor(phase),ceiling=reserveFor(phase),a=state.accounts[account];
    if(a.spent+ceiling>a.limit){state.status='BUDGET_STOP';event('BUDGET_REFUSAL',{phase,account,required:ceiling,available:a.limit-a.spent});await save();break;}
    state.pending={phase,account,ceiling};event('RESERVE',{phase,account,ceiling});await save();
    try{
     const {next,record}=await executeMission(state,phase,{sourceHash:source,signal:controller.signal,onProgress:p=>{$('run-status').textContent=`Mission ${['A','B','C','D'][phase]} · ${p} · fresh local computation`;},onCheckpoint:async()=>{if(controller.signal.aborted)throw Error('CANCELLED');}});
     if(controller.signal.aborted)throw Error('CANCELLED');
     next.events=state.events;next.intervention_count=state.intervention_count;state=next;state.accounts[account].spent+=record.costs.operations;state.baseline_operations+=record.costs.reference_operations;state.pending=null;event('ACCEPTED',{phase,parent_construction_calls:record.parent_construction_calls,parent_execution_calls:record.parent_execution_calls,result_hash:record.result_hash});
     state.status=state.stage===4?'COMPLETE':paused?'PAUSED':'RUNNING';await save();selected=phase;render();
     await new Promise(resolve=>setTimeout(resolve,0));
    }catch(error){
     state.accounts[account].spent+=ceiling;state.pending=null;state.status=error.message==='CANCELLED'?'STOPPED':'FAILED';event('ATTEMPT_REFUSED',{phase,reason:error.message,conservative_charge:ceiling});await save();
     if(error.message!=='CANCELLED')notify('The mission was refused: '+error.message+'. Earlier accepted results remain available.',true);
     break;
    }
   }
   if(state.status==='RUNNING'){state.status=paused?'PAUSED':'STOPPED';event(paused?'PAUSED_AT_ACCEPTED_BOUNDARY':'STOPPED');await save();}
  }catch(error){blocked=true;notify('Local execution stopped: '+error.message+'. Export available evidence before changing this browser’s storage.',true);}
  finally{running=false;controller=null;render();}
 }
 function download(name,value){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
 $('start-button').onclick=start;
 $('pause-button').onclick=()=>{paused=true;event('HUMAN_PAUSE_REQUEST');state.intervention_count++;render();};
 $('stop-button').onclick=()=>{if(controller){event('HUMAN_STOP_REQUEST');state.intervention_count++;controller.abort();}};
 $('reset-button').onclick=()=>{if(running)return;state=null;revision=null;selected=-1;blocked=false;notify('Previous runs remain in this browser’s history. This starts a new bounded stream.');$('control-result').hidden=true;render();};
 $('download-button').onclick=()=>download('AGI_ALPHA_Earned_Turn_Local_Evidence.json',{mode:'FRESH_BROWSER_LOCAL',source_hash:source,bundle_identity:data.source_hash,state,limits:{native_confirmation:false,external_proof:false,monetary_cost:null,human_minutes:null,live_authority:[],baseline_measurement_operations:state.baseline_operations}});
 $('download-assets').onclick=()=>download('AGI_ALPHA_Earned_Turn_Executable_Assets.json',{schema:'earned-turn-assets/v1',source_hash:source,parent:state.parent,successor:state.successor,source_response:state.accepted.find(r=>r.phase===1),interface:'Use core.mjs triangular / solveUpdate from the exact browser source archive; factors and update columns serialized here.',proof_status:'Historical local checks only; recheck fresh inputs',authority:[]});
 const controlResult=(text,kind)=>{const e=$('control-result');e.hidden=false;e.textContent=text;if(state){event(kind,{message:text});save().catch(err=>notify(err.message,true));}render();};
 $('stale-button').onclick=async()=>{try{inspectParent({...state.parent,network_hash:'changed-network'},await hash(network()),source);controlResult('Unexpected acceptance. Do not use this result.','FAULT_FAILED');}catch(e){controlResult('Refused: the network fingerprint changed. The old factor is not applicable; the accepted parent remains intact.','STALE_EVIDENCE_REFUSED');}};
 $('shift-button').onclick=()=>{try{updated(network(),[{...network().edges[0],index:0,delta:-1}]);controlResult('Unexpected acceptance. Do not use this result.','FAULT_FAILED');}catch(e){controlResult('Refused: a negative conductance change is outside the qualified positive-update interface. Retain the incumbent or commission a separate refactorization.','UNSUPPORTED_UPDATE_REFUSED');}};
 $('rollback-button').onclick=async()=>{state.status='ROLLED_BACK';event('HUMAN_ROLLBACK',{active:state.parent.id,retired:state.successor.id});state.intervention_count++;await save();selected=1;controlResult('Rolled back to the accepted parent. The successor is inactive, its historical evidence remains preserved, and no completed output is silently rerun.','ROLLBACK_CONFIRMED');};
 $('source-identity').textContent='Browser execution SHA-256: '+source+' · upstream source closure: '+data.upstream_description;
 if(data.research){const r=data.research;$('research-summary').innerHTML=`<h3>${esc(r.headline||'Frozen study results')}</h3><p>${esc(r.summary||'Recorded native study, packaged separately from the browser computation.')}</p><p class="mono">${esc(r.protocol_hash||r.source_hash||'')}</p>`;$('research-download').disabled=false;$('research-download').onclick=()=>download('AGI_ALPHA_Earned_Turn_Recorded_Study.json',r);}
 try{await initialise();}catch(error){blocked=true;notify('Local state could not be validated: '+error.message+'. No stored output has been admitted.',true);}
 render();globalThis.__earnedTurnReady=true;
 globalThis.__earnedTurnTest={start,validateStored,record:()=>state,source};
}
