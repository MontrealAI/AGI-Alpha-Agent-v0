// SPDX-License-Identifier: Apache-2.0
export function parsePreparedInput(raw) {
  if(typeof raw!=='string'||new TextEncoder().encode(raw).length>32768)throw Error('INPUT_BOUND');
  const value=JSON.parse(raw);
  if(!value||Array.isArray(value)||Object.keys(value).sort().join(',')!=='case_id,pack_sha256,schema'||
    value.schema!=='alpha-upgrade-selection/v1'||typeof value.case_id!=='string'||
    !/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(value.case_id)||typeof value.pack_sha256!=='string'||
    !/^[0-9a-f]{64}$/.test(value.pack_sha256))throw Error('INPUT_FORMAT');
  return value;
}
export async function checkedDownload(value) {
  if(!value||typeof value.filename!=='string'||!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.zip$/.test(value.filename)||
     value.mime!=='application/zip'||!Number.isSafeInteger(value.bytes)||value.bytes<1||value.bytes>750000||
     typeof value.base64!=='string'||value.base64.length>1000000||!/^[0-9a-f]{64}$/.test(value.sha256))throw Error('DOWNLOAD_FORMAT');
  const text=atob(value.base64),bytes=Uint8Array.from(text,char=>char.charCodeAt(0));
  if(bytes.length!==value.bytes)throw Error('DOWNLOAD_LENGTH');
  const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(actual!==value.sha256)throw Error('DOWNLOAD_HASH');
  return bytes;
}
export function planSummary(plan,language='en') {
  if(!plan?.input?.case_id)return '';
  const fr=language==='fr';
  return [
    (fr?'Changement choisi : ':'Selected change: ')+plan.input.case_id,
    (fr?'Travail : examiner les appels sélectionnés, vérifier les sources, produire le dossier bilingue.':'Work: inspect selected calls, check source evidence, produce the bilingual packet.'),
    (fr?'Expiration : ':'Expires: ')+new Date(plan.expires_at*1000).toISOString(),
    (fr?'Limite totale (s) : ':'Total request limit (s): ')+plan.request_seconds,
    (fr?'Tentatives maximales dans cette autorisation : ':'Maximum attempts within this approval: ')+plan.caps.service_work,
    fr?'Aucune modification de dépendance ni transaction. Les coûts monétaires complets restent inconnus.':'No dependency change or transaction. Complete monetary costs remain unknown.',
    fr?'Résultat : rapport lisible, sources, limites, prochaine action, coûts et historique signé.':'Result: readable report, sources, limits, next action, costs and signed history.'
  ].join('\n');
}
if(typeof document!=='undefined') {
  const $=id=>document.getElementById(id);
  let language='en',token='',selected=null,busy=false,executorState='disconnected';
  let connectionEpoch=0,statusSequence=0,pollTimer=null,pollCount=0;
  const words={connected:['Connected to the existing local executor.','Connecté à l’exécuteur local existant.'],
    disconnected:['Disconnected; the local approved request may still be active.','Déconnecté ; la demande locale approuvée peut rester active.'],
    error:['Request failed. Inspect durable history; only an explicitly installed recovery allowance can resume the same mission.','Demande échouée. Inspectez l’historique ; seule une reprise explicitement installée peut continuer la même mission.'],
    input:['Import the exact owner-prepared input and a valid request ID.','Importez l’entrée exacte préparée par le responsable et un identifiant valide.'],
    prepared:['Review the exact finite plan before approval.','Examinez le plan fini exact avant approbation.'],
    approved:['Exact plan approved. You may now run its fixed mission.','Plan exact approuvé. Vous pouvez exécuter sa mission fixe.'],
    running:['Approved bounded work is running in the existing local process.','Le travail approuvé et borné s’exécute dans le processus local existant.'],
    complete:['Request returned. Inspect the retained outcome and verified download below.','Demande retournée. Examinez le résultat conservé et le téléchargement vérifié ci-dessous.'],
    paused:['Paused. Resume can recover eligible source work only within its original limits.','Suspendu. La reprise ne continue que le travail source admissible dans ses limites initiales.'],
    cancelled:['Mission cancellation recorded durably.','Annulation durable de la mission enregistrée.'],
    stopped:['Permanent STOP recorded for this installed envelope.','ARRÊT permanent enregistré pour cette enveloppe installée.']};
  async function menu() {
    const value=JSON.parse($('offering-catalog').textContent);
    if(value.schema!=='alpha-upgrade-catalog/v1'||!value.cases||Object.keys(value.cases).length>32)throw Error('MENU');
    const select=$('case');
    for(const [id,item] of Object.entries(value.cases)){
      if(typeof item.missionKey!=='string'||!/^([0-9a-f]{64})$/.test(item.missionKey))throw Error('MISSION_IDENTITY');
      parsePreparedInput(JSON.stringify({schema:'alpha-upgrade-selection/v1',case_id:id,pack_sha256:item.sha256}));
      const option=document.createElement('option');option.value=id;option.textContent=item.title;option.dataset.en=item.title;option.dataset.fr=id==='native-component-refresh-development'?'Dépendances natives · 61 vérifications · développement':'Starlette / HTTPX · exemple historique';select.append(option);
    }
    const choose=()=>{
      $('input').value=JSON.stringify({schema:'alpha-upgrade-selection/v1',case_id:select.value,pack_sha256:value.cases[select.value].sha256});
      $('request-id').value='upgrade-'+value.cases[select.value].missionKey.slice(0,48);selected=null;controls();
    };
    select.onchange=choose;choose();
  }
  const say=key=>{$('status').textContent=words[key]?.[language==='fr'?1:0]||words.error[language==='fr'?1:0];};
  function controls(){
    $('prepare').disabled=!token||busy||executorState!=='ready';
    for(const id of ['refresh','pause','stop'])$(id).disabled=!token;
    $('resume').disabled=!token||executorState!=='paused';
    $('approve').disabled=!token||busy||executorState!=='ready'||selected?.state!=='prepared';
    $('run').disabled=!token||busy||executorState!=='ready'||selected?.state!=='approved';
    $('cancel').disabled=!token||!selected||['completed','rejected','cancelled','reconciled'].includes(selected.state);
    $('connect').disabled=busy;$('disconnect').disabled=!token;
  }
  async function api(action,body) {
    if(!token)throw Error('DISCONNECTED');
    const epoch=connectionEpoch,requestToken=token;
    const response=await fetch('/api/strategy-executor/'+action,{method:body?'POST':'GET',cache:'no-store',
      credentials:'omit',headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},
      ...(body?{body:JSON.stringify(body)}:{})});
    if(!response.ok)throw Error('HTTP_'+response.status);
    const result=await response.json();
    if(epoch!==connectionEpoch||requestToken!==token)throw Error('STALE_CONNECTION');
    return result;
  }
  function save(bytes,mime,filename) {
    const url=URL.createObjectURL(new Blob([bytes],{type:mime})),anchor=document.createElement('a');
    anchor.href=url;anchor.download=filename;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function select(plan) {selected=plan;$('plan-summary').textContent=planSummary(plan,language);$('plan').textContent=plan?JSON.stringify(plan,null,2):'';controls();}
  async function history() {
    const epoch=connectionEpoch,sequence=++statusSequence;
    const status=await api('status');
    if(epoch!==connectionEpoch||sequence!==statusSequence||!token)return status;
    executorState=status.state;
    $('executor-state').textContent=(language==='fr'?'État de l’exécuteur : ':'Executor state: ')+status.state;
    $('history').replaceChildren();
    for(const plan of Object.values(status.plans||{})) {
      const article=document.createElement('article'),label=document.createElement('p');
      label.textContent=plan.plan_id+' · '+plan.state;article.append(label);
      if(plan.outcome?.result?.refused){const reason=document.createElement('p');reason.textContent=language==='fr'?'Demande non prise en charge : les sources ou preuves ne correspondent pas au périmètre approuvé. Examinez les entrées avant de continuer.':'Request unsupported: sources or evidence do not match the approved scope. Review the inputs before continuing.';article.append(reason);}
      if(plan.outcome?.result?.nextAction){const summary=document.createElement('p');const a=plan.outcome.result.nextAction;summary.textContent=language==='fr'?(['HOLD_UPDATE_AND_TEST','HOLD_COMPONENT_AND_INVESTIGATE'].includes(a)?'Suspendez cette mise à niveau et testez le conflit.':'Examinez le rapport et les vérifications restantes.'):(['HOLD_UPDATE_AND_TEST','HOLD_COMPONENT_AND_INVESTIGATE'].includes(a)?'Hold this update and test the conflict.':'Review the report and remaining checks.');article.append(summary);}
      const cost=document.createElement('small');
      cost.textContent=(language==='fr'?'Coût monétaire total et prix client : inconnus. Tentatives imputées : ':'Full monetary cost and customer price: unknown. Charged attempts: ')+(plan.recovery_attempts?.length??plan.observed?.service_work??0);article.append(cost);
      const inspect=document.createElement('button');inspect.textContent=language==='fr'?'Examiner le plan':'Inspect plan';
      inspect.onclick=()=>select(plan);article.append(inspect);
      const evidence=document.createElement('button');evidence.textContent=language==='fr'?'Exporter l’historique signé':'Export signed history';
      evidence.onclick=async()=>{try{save(JSON.stringify(await api('export/'+plan.plan_id),null,2),'application/json',plan.plan_id+'.json');}catch{say('error');}};
      article.append(evidence);
      if(plan.state==='completed'&&plan.outcome?.verified===true&&plan.outcome.result?.download) {
        const download=document.createElement('button');download.textContent=language==='fr'?'Télécharger le résultat ZIP vérifié':'Download verified result ZIP';
        download.onclick=async()=>{try{const item=plan.outcome.result.download;save(await checkedDownload(item),item.mime,item.filename);}catch{say('error');}};
        article.append(download);
      }
      $('history').append(article);
      if(selected?.plan_id===plan.plan_id)select(plan);
    }
    controls();clearTimeout(pollTimer);
    if(Object.values(status.plans||{}).some(p=>p.state==='running')&&pollCount<120){
      pollCount++;pollTimer=setTimeout(()=>{if(token&&epoch===connectionEpoch)history().catch(()=>say('error'));},500);
    }else pollCount=0;
    return status;
  }
  async function action(fn) {if(busy)return;busy=true;controls();try{await fn();}catch{say('error');}finally{busy=false;controls();}}
  $('language').onclick=()=>{
    language=language==='en'?'fr':'en';document.documentElement.lang=language;
    for(const element of document.querySelectorAll('[data-en]'))element.textContent=element.dataset[language];
    $('language').textContent=language==='en'?'Français':'English';
    $('input').setAttribute('aria-label',language==='fr'?'Sélection de mise à niveau préparée':'Prepared upgrade selection JSON');
    if(selected)select(selected);if(token)history().catch(()=>say('error'));
  };
  $('connect').onclick=()=>action(async()=>{connectionEpoch++;pollCount=0;token=$('token').value;$('token').value='';
    try{await history();say('connected');}catch(error){token='';throw error;}});
  $('disconnect').onclick=()=>{connectionEpoch++;clearTimeout(pollTimer);pollCount=0;token='';executorState='disconnected';$('executor-state').textContent='';$('token').value='';selected=null;$('plan').textContent='';$('plan-summary').textContent='';$('history').replaceChildren();say('disconnected');controls();};
  $('input').oninput=()=>select(null);$('request-id').oninput=()=>select(null);
  $('file').onchange=async()=>{const file=$('file').files[0];try{
    if(!file||file.size>32768)throw Error('INPUT_BOUND');const raw=await file.text();parsePreparedInput(raw);$('input').value=raw;select(null);
  }catch{say('input');}finally{$('file').value='';}};
  $('prepare').onclick=()=>action(async()=>{
    let input;try{input=parsePreparedInput($('input').value);if(!/^[A-Za-z0-9_-]{1,64}$/.test($('request-id').value))throw Error('ID');}catch{say('input');return;}
    select(await api('prepare',{method:'run-mission',input,request_id:$('request-id').value}));say(selected.state==='completed'?'complete':'prepared');await history();
  });
  const ref=()=>({plan_id:selected.plan_id,plan_digest:selected.plan_digest});
  $('approve').onclick=()=>action(async()=>{select(await api('approve',ref()));say('approved');await history();});
  $('run').onclick=()=>action(async()=>{say('running');select(await api('run',ref()));say('complete');await history();});
  $('cancel').onclick=async()=>{try{select(await api('cancel',ref()));say('cancelled');await history();}catch{say('error');}};
  $('refresh').onclick=()=>history().catch(()=>say('error'));
  const control=async(state,message)=>{try{await api('control',{state});say(message);await history();}catch{say('error');}};
  $('pause').onclick=()=>control('paused','paused');
  $('resume').onclick=()=>control('ready','connected');
  $('stop').onclick=()=>control('stopped','stopped');
  for(const element of document.querySelectorAll('[data-en]'))element.textContent=element.dataset.en;
  controls();menu().catch(()=>say('input'));
}
