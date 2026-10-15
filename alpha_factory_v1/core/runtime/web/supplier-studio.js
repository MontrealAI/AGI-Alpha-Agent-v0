// SPDX-License-Identifier: Apache-2.0
'use strict';
const $=id=>document.getElementById(id), pretty=value=>JSON.stringify(value,null,2);
let token='', identity='', epoch=0, operation=0, intent=0, fileSequence=0, busy=false, state=null, selected=null, permission=null, spec=null;
let notice=null, executing=null;
const t=(en,fr)=>$('language').value==='fr'?fr:en;
function message(en,fr,error=false){notice={en,fr,error};$('message').textContent=t(en,fr);$('message').classList.toggle('error',error);}
function translate(){for(const node of document.querySelectorAll('[data-fr]')){node.dataset.en??=node.textContent;node.textContent=node.dataset[$('language').value];}document.documentElement.lang=$('language').value;if(notice)message(notice.en,notice.fr,notice.error);render();}
function changedIntent(){intent++;permission=null;$('run-confirm').checked=false;$('admit-confirm').checked=false;render();}
function clearConfirmations(){for(const id of ['run-confirm','review-confirm','reconcile-confirm'])$(id).checked=false;}
function controls(){
  for(const node of document.querySelectorAll('#workspace button,#workspace input,#workspace textarea,#workspace select'))node.disabled=busy;
  $('disconnect').disabled=false;
  const ready=Boolean(state?.profiles?.market&&state?.profiles?.executor&&state?.control==='ready');
  $('admit').disabled=busy||!ready||!spec;
  $('prepare').disabled=busy||!ready||selected?.state!=='admitted';
  $('execute').disabled=busy||!ready||selected?.state!=='admitted'||!permission;
  $('review').disabled=busy||selected?.state!=='review';
  $('export').disabled=busy||selected?.state!=='approved';
  $('reconcile').disabled=busy||!['stopped','interrupted'].includes(selected?.state);
  $('stop').disabled=!selected||(!['running','review'].includes(selected.state)&&executing?.binding!==selected.id);
  $('workspace').setAttribute('aria-busy',String(busy));
}
function render(){
  if(state){$('profiles').textContent=pretty(state);$('readiness').textContent=state.profiles.market&&state.profiles.executor?t('Profiles installed. Host isolation and provider commissioning still require separate evidence.','Profils installés. L’isolation hôte et la configuration du fournisseur exigent encore des preuves distinctes.'):t('Setup required. The host operator must install reviewed market and executor profiles; a work file cannot install them.','Installation requise. L’opérateur hôte doit installer les profils du marché et de l’exécuteur vérifiés; un fichier de travail ne peut pas le faire.');
    $('history').replaceChildren();for(const item of state.records){const button=document.createElement('button');button.textContent=`${item.job_id} · ${item.state}`;button.addEventListener('click',()=>guard(async()=>show(item.binding)));$('history').append(button);}}
  $('selected').hidden=!selected;if(selected){$('selection').textContent=`${selected.observation.job_id} · ${selected.state} · ${selected.attempt_id||'—'}`;$('record').textContent=pretty(selected);}
  $('permission').textContent=permission?pretty(permission):'';controls();
}
async function api(action,body){
  const started=epoch,sequence=operation,encoded=body===undefined?undefined:JSON.stringify(body);
  if(encoded&&new TextEncoder().encode(encoded).length>512*1024)throw Error('request-size');
  const response=await fetch('/api/supplier-browser/'+action,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,'X-AGIALPHA-Journal':identity,'Content-Type':'application/json'},body:encoded});
  if(started!==epoch||sequence!==operation)throw Error('session-changed');const value=await response.json();if(started!==epoch||sequence!==operation)throw Error('session-changed');if(!response.ok)throw Error('request-failed');return value;
}
async function refresh(){const next=await api('status');if(identity&&next.identity!==identity){disconnect();throw Error('identity-changed');}if(typeof next.identity!=='string'||!Array.isArray(next.records))throw Error('invalid-status');identity=next.identity;state=next;render();}
async function show(binding){const next=await api('show',{binding});selected=next;permission=null;clearConfirmations();$('result-hash').textContent='';render();}
async function guard(action,urgent=false){
  if(busy&&!urgent)return;const started=epoch,sequence=++operation;busy=true;controls();
  const current=()=>started===epoch&&sequence===operation;
  try{await action(current);if(current())message('Recorded. Inspect retained evidence before the next action.','Enregistré. Examinez les preuves conservées avant l’action suivante.');}
  catch{if(current()){permission=null;message('Operation unavailable or response uncertain. Refresh retained state before retrying.','Opération indisponible ou réponse incertaine. Actualisez l’état conservé avant de réessayer.',true);}}
  finally{if(current()){busy=false;render();}}
}
function disconnect(){epoch++;operation++;fileSequence++;token='';identity='';state=null;selected=null;permission=null;spec=null;busy=false;executing=null;for(const id of ['token','job-id','worker','assignment','note','spec-file'])$(id).value='';for(const id of ['record','permission','profiles','history','spec-preview','spec-hash','result-hash','selection','readiness'])$(id).replaceChildren();clearConfirmations();$('admit-confirm').checked=false;$('workspace').hidden=true;$('selected').hidden=true;$('login').hidden=false;message('Disconnected; page token cleared. Already-started work continues on the agent. Reconnect to inspect or STOP it.','Déconnecté; jeton effacé. Le travail déjà démarré continue sur l’agent. Reconnectez-vous pour l’inspecter ou l’arrêter.');}
$('login-form').addEventListener('submit',event=>{event.preventDefault();if(busy)return;epoch++;token=$('token').value;$('token').value='';identity='';guard(async current=>{await refresh();if(current()){$('login').hidden=true;$('workspace').hidden=false;}});});
$('disconnect').addEventListener('click',disconnect);$('language').addEventListener('change',translate);
$('refresh').addEventListener('click',()=>guard(async()=>{await refresh();if(selected)await show(selected.id);}));
$('spec-file').addEventListener('change',async()=>{
  changedIntent();const started=epoch,sequence=++fileSequence;spec=null;$('admit-confirm').checked=false;$('spec-preview').textContent='';$('spec-hash').textContent='';controls();const file=$('spec-file').files[0];if(!file)return;
  try{if(file.size>64000)throw Error('size');const bytes=new Uint8Array(await file.arrayBuffer());if(bytes.length>64000)throw Error('size');const text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);const hash=await crypto.subtle.digest('SHA-256',bytes);if(started!==epoch||sequence!==fileSequence)return;spec=bytes;$('spec-preview').textContent=text;$('spec-hash').textContent='specHash: 0x'+[...new Uint8Array(hash)].map(x=>x.toString(16).padStart(2,'0')).join('');}
  catch{if(started===epoch&&sequence===fileSequence)message('Choose an exact UTF-8 work file within 64,000 bytes. The server validates its full schema before admission.','Choisissez un fichier UTF-8 exact de 64 000 octets maximum. Le serveur vérifie son schéma complet avant admission.',true);}finally{if(started===epoch&&sequence===fileSequence)controls();}
});
$('admit-form').addEventListener('submit',event=>{event.preventDefault();if(!spec||!$('admit-confirm').checked)return;const body={spec_base64:btoa(String.fromCharCode(...spec)),job_id:$('job-id').value,worker:$('worker').value,assignment_tx:$('assignment').value,confirm:true};guard(async()=>{const record=await api('admit',body);await refresh();await show(record.id);$('admit-confirm').checked=false;});});
$('prepare').addEventListener('click',()=>{if(!selected)return;const binding=selected.id,generation=intent;guard(async current=>{const value=await api('prepare',{binding});if(current()&&generation===intent){permission=value;$('run-confirm').checked=false;}});});
$('execute').addEventListener('click',()=>{if(!selected||!permission||!$('run-confirm').checked)return;const body={binding:selected.id,permit:permission.permit,confirm:true};permission=null;clearConfirmations();const attempt={binding:body.binding};executing=attempt;guard(async current=>{try{await api('execute',body);if(current()){await refresh();if(current())await show(body.binding);}}finally{if(executing===attempt)executing=null;}});});
$('stop').addEventListener('click',()=>{if(!selected)return;const binding=selected.id;permission=null;clearConfirmations();guard(async current=>{await api('stop',{binding,confirm:true});if(current()){await refresh();await show(binding);}},true);});
$('review').addEventListener('click',()=>{if(!selected||!$('review-confirm').checked||!$('note').value.trim())return;const body={binding:selected.id,revision:selected.revision,result_hash:selected.result_hash,approve:$('decision').value==='true',note:$('note').value,confirm:true};guard(async()=>{await api('review',body);await refresh();await show(body.binding);});});
$('reconcile').addEventListener('click',()=>{if(!selected||!$('reconcile-confirm').checked||!$('note').value.trim())return;const body={binding:selected.id,revision:selected.revision,note:$('note').value,confirm:true};guard(async()=>{await api('reconcile',body);await refresh();await show(body.binding);});});
$('export').addEventListener('click',()=>{if(!selected)return;const binding=selected.id;guard(async current=>{const value=await api('export',{binding});const bytes=Uint8Array.from(atob(value.artifact_base64),x=>x.charCodeAt(0));const hash='0x'+[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');if(!current())return;if(hash!==value.result_hash)throw Error('hash');const url=URL.createObjectURL(new Blob([bytes],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='reviewed-supplier-browser-delivery.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('result-hash').textContent='resultHash: '+hash;});});
for(const id of ['job-id','worker','assignment'])$(id).addEventListener('input',changedIntent);
for(const id of ['note','decision'])$(id).addEventListener('input',()=>{$('review-confirm').checked=false;$('reconcile-confirm').checked=false;});
window.addEventListener('pagehide',disconnect);translate();$('loading').hidden=true;for(const id of ['token','connect','language'])$(id).disabled=false;
