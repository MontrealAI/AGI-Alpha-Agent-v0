// SPDX-License-Identifier: Apache-2.0
'use strict';
const $=id=>document.getElementById(id);
const INITIAL={schema:'release-plan/v1',id:'public-release-plan',kind:'plan',public_or_synthetic:'synthetic',planning_only:true,jobs:[{id:'J1',duration:2,crew:1,deps:[]},{id:'J2',duration:4,crew:2,deps:['J1']},{id:'J3',duration:3,crew:1,deps:['J1']},{id:'J4',duration:3,crew:2,deps:['J2']},{id:'J5',duration:2,crew:1,deps:['J3']},{id:'J6',duration:1,crew:1,deps:['J4','J5']}],capacity:Array(32).fill(2),deadline:24};
const SAMPLE={initial:INITIAL,changes:{durations:{J2:6},deadline:28},repair:{observed_at:9,capacity:Array.from({length:32},(_,i)=>i>=14&&i<19?1:2),deadline:28},construction:{enabled:true}};
$('input').value=JSON.stringify(SAMPLE,null,2);
let token='',connected=false,currentPlan=null,latestStatus=null,running=false,polling=null,language='en';
const words={en:{start:'Start',connect:'Connect',disconnect:'Disconnect',review:'Review',pause:'Pause',resume:'Resume',stop:'Stop',keep:'Keep',improve:'Improve',export:'Export',approve:'Approve and start work',resumeApproved:'Resume approved work'},fr:{start:'Démarrer',connect:'Connecter',disconnect:'Déconnecter',review:'Vérifier',pause:'Pause',resume:'Reprendre',stop:'Arrêter',keep:'Conserver',improve:'Améliorer',export:'Exporter',approve:'Autoriser et démarrer',resumeApproved:'Reprendre le travail autorisé'}};
const word=key=>words[language][key];
const number=x=>typeof x==='number'?new Intl.NumberFormat('en',{maximumFractionDigits:3}).format(x):'Unknown';
const message=(text,error=false)=>{if(error){$('error').textContent=text;$('error').hidden=false;}else{$('status').textContent=text;$('error').hidden=true;}};
async function api(action,body){
 if(!token)throw Error('Connect with the existing operator token first.');
 const response=await fetch('/api/strategy-executor/'+action,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)}),cache:'no-store'});
 const result=await response.json();if(!response.ok)throw Error(result.error||'Executor request refused. Inspect retained status before retrying.');return result;
}
function controls(){
 $('prepare').disabled=!connected||running||latestStatus?.state!=='ready'||!latestStatus?.source_available;
 $('connect').disabled=connected;$('disconnect').disabled=!connected;
 $('review').disabled=!connected;$('pause').disabled=!connected||latestStatus?.state==='stopped';$('stop').disabled=!connected||latestStatus?.state==='stopped';
 const reviewable=['prepared','approved'].includes(currentPlan?.state);
 $('approve').disabled=!connected||running||!latestStatus?.source_available||latestStatus?.state!=='ready'||!reviewable||!$('consent').checked;
 $('consent').disabled=running||!reviewable;
 $('mission-select').disabled=!connected||running||!Object.keys(latestStatus?.plans??{}).length;
 $('export').disabled=!connected||!currentPlan;
 $('keep').disabled=running||!currentPlan?.outcome?.result?.capabilities;
 $('improve').disabled=!connected||running||!currentPlan?.outcome?.result?.next_improvement;
 for(const id of ['connect','disconnect','review','stop','keep','improve','export'])$(id).textContent=word(id);$('approve').textContent=word(currentPlan?.state==='approved'?'resumeApproved':'approve');$('prepare').textContent=word('start');$('pause').textContent=word(latestStatus?.state==='paused'?'resume':'pause');
}
function balances(status){
 const titles={service_work:'Service work',improvement_work:'Improvement work',native_calls:'Native specialist calls',native_solve_seconds:'Native solve allowance'};
 const box=$('balances');box.replaceChildren();
 for(const [key,title]of Object.entries(titles)){const el=document.createElement('div');el.className='balance';const name=document.createElement('span');name.textContent=title;const value=document.createElement('strong');value.textContent=number(status.spent?.[key])+' / '+number(status.total?.[key]);const reserved=document.createElement('small');reserved.textContent=number(status.reserved?.[key])+' reserved · '+number(currentPlan?.observed?.[key]??0)+' observed';el.append(name,value,reserved);box.append(el);}
}
function showPlan(plan,{resetConsent=true}={}){
 currentPlan=plan;$('plan').hidden=false;if(resetConsent)$('consent').checked=false;
 const pairs={'Executor':plan.executor_id,'Source identity':plan.source_hash,'Method':plan.method,'Mission state':plan.state,'Service work cap':number(plan.caps?.service_work),'Improvement work cap':number(plan.caps?.improvement_work),'Native specialist ceiling':number(plan.caps?.native_calls)+' calls · '+number(plan.caps?.native_solve_seconds)+' solve seconds','Expires':new Date(plan.expires_at*1000).toLocaleString(),'Maximum request time':number(plan.request_seconds)+' seconds','Approval digest':plan.plan_digest};
 const dl=$('scope');dl.replaceChildren();for(const [key,value]of Object.entries(pairs)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=value;dl.append(dt,dd);}
 $('approved-input').textContent=JSON.stringify(plan.input,null,2);controls();
}
function retainedMissions(status){
 const plans=Object.values(status.plans??{}).sort((a,b)=>(b.prepared_at??0)-(a.prepared_at??0)||b.plan_id.localeCompare(a.plan_id));
 const select=$('mission-select');
 const labels=plans.map(plan=>[plan.plan_id,(plan.input?.initial?.id??plan.input?.task?.id??plan.request_id??plan.plan_id)+' · '+plan.method+' · '+plan.state]);
 const signature=JSON.stringify(labels);
 if(select.dataset.missions!==signature){select.replaceChildren();for(const[value,label]of labels){const option=document.createElement('option');option.value=value;option.textContent=label;select.append(option);}if(!plans.length){const option=document.createElement('option');option.value='';option.textContent=language==='fr'?'Aucune mission conservée':'No retained missions';select.append(option);}select.dataset.missions=signature;}
 const selected=currentPlan&&status.plans?.[currentPlan.plan_id]||plans[0];
 if(selected){const changed=currentPlan?.plan_id!==selected.plan_id;showPlan(selected,{resetConsent:changed});select.value=selected.plan_id;renderOutcome(selected);}
 else{currentPlan=null;$('plan').hidden=true;$('consent').checked=false;clearOutcome();}
}
function clearOutcome(){
 $('results').replaceChildren();$('evidence').hidden=true;$('raw').textContent='';
 $('method-note').textContent='Retained methods require fresh checks before later use. Keep saves inspectable method records.';
}
function renderOutcome(plan){
 const outcome=plan.outcome;
 if(!outcome){
  clearOutcome();
  if(plan.partial_receipts?.length){$('results').replaceChildren();for(const receipt of plan.partial_receipts){const card=document.createElement('section');card.className='result';const h=document.createElement('h3');h.textContent=['Initial plan retained','Changed plan retained','Repair retained'][receipt.phase_index]??'Checked phase retained';const text=document.createElement('p');text.textContent='A checked phase is committed to the executor journal. Mission state: '+plan.state+'. Receipt: '+receipt.receipt_hash;card.append(h,text);$('results').append(card);}$('evidence').hidden=false;$('raw').textContent=JSON.stringify(plan,null,2);}
  return;
 }
 const result=outcome.result??{},target=$('results');target.replaceChildren();
 for(const [index,phase]of (result.phases??[]).entries()){
  const section=document.createElement('section');section.className='result';const h=document.createElement('h3');h.textContent=phase.label??['First plan','Changed plan','Repair'][index]??'Result';
  const detail=document.createElement('p');const schedule=phase.result??phase.delivery?.result??{};detail.textContent=(phase.qualified?'Qualified':'Review required')+' · Makespan '+number(schedule.makespan)+' · Movement '+number(schedule.movement)+' · '+(typeof phase.selected_method==='string'?phase.selected_method:phase.selected_method?.name??phase.selected_method?.kind??'See the evidence for the selected method');section.append(h,detail);
  if(Array.isArray(schedule.schedule)){const table=document.createElement('table');table.className='schedule';const tr=document.createElement('tr');for(const label of ['Job','Start','Finish']){const th=document.createElement('th');th.scope='col';th.textContent=label;tr.append(th);}const head=document.createElement('thead');head.append(tr);table.append(head);const body=document.createElement('tbody');for(const item of schedule.schedule){const row=document.createElement('tr');for(const value of [item.id,item.start,item.end]){const td=document.createElement('td');td.textContent=String(value);row.append(td);}body.append(row);}table.append(body);section.append(table);}
  if(phase.baseline_source){const p=document.createElement('p');const baseline=phase.baseline_source;p.textContent=typeof baseline==='string'?'Repair baseline: '+baseline:'Repair baseline: prior verified plan '+String(baseline.receipt_hash??'').slice(0,16)+' · Commitments inferred from the supplied planning time '+String(baseline.observed_at??'')+'. Physical job execution is not observed by this planner.';section.append(p);}target.append(section);
 }
 for(const [key,title]of [['capabilities','What was retained'],['inheritance','Did inheriting the parent help?'],['repair_usefulness','Was the repair tool useful?']]){if(result[key]===undefined)continue;const section=document.createElement('section');section.className='result';const h=document.createElement('h3');h.textContent=title;const p=document.createElement('pre');p.textContent=JSON.stringify(result[key],null,2);section.append(h,p);target.append(section);}
 $('evidence').hidden=false;$('raw').textContent=JSON.stringify(plan,null,2);
 $('method-note').textContent=result.next_improvement?'A bounded next improvement is available for separate review and approval.':'No further improvement proposal is admitted by this run. Retaining a competent incumbent is valid. Keep saves candidate records for inspection, with no authority.';
}
function download(name,record){const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function refresh(){
 if(!connected)return;const status=await api('status');if(!connected)return;latestStatus=status;retainedMissions(status);balances(status);
 $('executor').textContent='Executor '+status.executor_id+' · Source '+status.source_hash+' · One request at a time';
 $('connection').textContent=status.source_available?'Connected':'Source unavailable';$('connection').classList.toggle('online',status.source_available);
 $('background').textContent=status.active_after_browser_close?'A bounded request is active on the executor. Closing this tab does not cancel it. Use Pause or Stop.':'The executor reports no active request. Prepared plans require explicit approval.';
 if(!running)message(currentPlan?'Mission state: '+currentPlan.state+'.':'Executor '+status.state+'. Review its scope before starting.');controls();return status;
}
$('connect-form').addEventListener('submit',async event=>{event.preventDefault();token=$('token').value;$('token').value='';$('consent').checked=false;try{await api('status');connected=true;await refresh();polling=setInterval(()=>refresh().catch(error=>{latestStatus={...latestStatus,state:'disconnected',source_available:false};$('connection').textContent='Status unavailable';$('connection').classList.remove('online');message('Disconnected from status: '+error.message,true);controls();}),1200);}catch(error){token='';connected=false;message(error.message,true);controls();}});
$('disconnect').addEventListener('click',()=>{token='';connected=false;$('consent').checked=false;clearInterval(polling);$('connection').textContent='Disconnected';$('connection').classList.remove('online');message('Disconnected. An already approved bounded request may still be active on the executor.');controls();});
$('prepare').addEventListener('click',async()=>{try{const input=JSON.parse($('input').value);const plan=await api('prepare',{method:'run-journey',input,request_id:crypto.randomUUID()});showPlan(plan);message('Plan prepared. Review both accounts, source and expiry, then approve this exact scope.');await refresh();}catch(error){message(error.message,true);}});
$('consent').addEventListener('change',controls);
$('mission-select').addEventListener('change',()=>{const selected=latestStatus?.plans?.[$('mission-select').value];if(!selected||running)return;showPlan(selected);renderOutcome(selected);balances(latestStatus);message('Mission state: '+selected.state+'. Running or uncertain work is never retried automatically.');});
$('approve').addEventListener('click',async()=>{if(!currentPlan||!$('consent').checked||!['prepared','approved'].includes(currentPlan.state))return;const binding={plan_id:currentPlan.plan_id,plan_digest:currentPlan.plan_digest};const needsApproval=currentPlan.state==='prepared';running=true;controls();try{if(needsApproval)currentPlan=await api('approve',binding);message('Running on '+currentPlan.executor_id+'. The executor is planning, adapting and repairing this project.');currentPlan=await api('run',binding);renderOutcome(currentPlan);message('Mission '+currentPlan.state+'. Review the result, retained methods and both cost accounts.');}catch(error){message(error.message+' Inspect retained status before retrying.',true);}finally{running=false;$('consent').checked=false;try{await refresh();}catch(error){message(error.message,true);}controls();}});
$('review').addEventListener('click',()=>refresh().catch(error=>message(error.message,true)));
$('pause').addEventListener('click',async()=>{try{await api('control',{state:latestStatus?.state==='paused'?'ready':'paused'});await refresh();}catch(error){message(error.message,true);}});
$('stop').addEventListener('click',async()=>{try{await api('control',{state:'stopped'});await refresh();message('Stopped. This installed operating envelope cannot resume. Review and export retained evidence.');}catch(error){message(error.message,true);}});
$('keep').addEventListener('click',()=>{const result=currentPlan?.outcome?.result;if(!result?.capabilities)return;download('strategy-methods-'+currentPlan.plan_id+'.json',{schema:'strategy-method-inspection/v1',source_hash:currentPlan.source_hash,origin_plan:currentPlan.plan_digest,origin_outcome:currentPlan.outcome_hash,capabilities:result.capabilities,proof:[],authority:[],limits:'Inspection records only. Fresh correctness, applicability and economic admission are required before reuse.'});message('Method records saved for inspection. No authority or proof was inherited.');});
$('improve').addEventListener('click',async()=>{const proposal=currentPlan?.outcome?.result?.next_improvement;if(!proposal)return;try{showPlan(await api('prepare',{method:'construct',input:proposal,request_id:crypto.randomUUID()}));message('Review the separately budgeted improvement before approving.');await refresh();}catch(error){message(error.message,true);}});
$('export').addEventListener('click',async()=>{try{download('strategy-mission-'+currentPlan.plan_id+'.json',await api('export/'+currentPlan.plan_id));}catch(error){message(error.message,true);}});
controls();

$('language').addEventListener('click',()=>{language=language==='en'?'fr':'en';document.documentElement.lang=language;$('language').textContent=language==='en'?'FR':'EN';$('language').setAttribute('aria-label',language==='en'?'Français':'English');const fr=language==='fr';const text={'hero-title':fr?'Planifier. Adapter.':'Plan. Adapt.','hero-subtitle':fr?'Réparer ce qui change.':'Repair what changes.','intro':fr?'Planifiez une livraison, adaptez ses exigences, puis réparez ce même projet. Conservez la méthode utile et vérifiez son apport.':'Make a release plan, adapt its requirements, then repair that same project. Keep the useful method. See what it earned.','mode':fr?'Mode connecté · Méthodes vérifiées · Votre exécuteur local configuré':'Connected mode · Reviewed planning methods · Your configured local executor','connect-title':fr?'Connecter le travail autorisé':'Connect to approved work','mission-title':fr?'Préparer une livraison publique':'Prepare a public release','progress-title':fr?'Historique de votre mission':'Your mission history','mission-select-label':fr?'Missions conservées':'Retained missions','history-note':fr?'Reconnectez-vous pour vérifier le travail conservé. Un plan autorisé peut reprendre après un nouveau consentement ; le travail en cours ou incertain n’est jamais relancé automatiquement.':'Reconnect to review saved work. An approved plan can resume after fresh consent; running or uncertain work is never retried automatically.','approved-input-title':fr?'Entrée exacte de ce plan':'Exact mission input for this plan','approved-input-note':fr?'Cette entrée conservée est liée à l’empreinte d’autorisation. Modifier l’entrée ci-dessus ne modifie pas ce plan. Utilisez Démarrer pour préparer une autre mission.':'This saved input is fixed by the approval digest. Editing the input above does not change this plan. Use Start to prepare a different mission.','cost-note':fr?'Le service et l’amélioration disposent de comptes protégés distincts. Les allocations du solveur et les mesures réelles restent séparées. Les coûts humains et monétaires demeurent inconnus.':'Service and improvement have separate protected accounts. Solver allocations and actual measurements remain separate. Human and monetary costs remain unknown.'};for(const[id,value]of Object.entries(text))$(id).textContent=value;document.querySelector('label[for=token]').textContent=fr?'Jeton d’accès existant de l’opérateur':'Existing operator access token';const labels=fr?['Planifier','Adapter','Réparer']:['Plan','Adapt','Repair'];document.querySelectorAll('.journey strong').forEach((el,i)=>el.textContent=labels[i]);controls();});
