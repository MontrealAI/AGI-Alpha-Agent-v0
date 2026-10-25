// SPDX-License-Identifier: Apache-2.0
export function parsePreparedInput(raw) {
  if(typeof raw!=='string'||new TextEncoder().encode(raw).length>32768)throw Error('INPUT_BOUND');
  const value=JSON.parse(raw);
  if(!value||Array.isArray(value)||Object.keys(value).sort().join(',')!=='approval_digest,plan,scope_id' ||
     typeof value.scope_id!=='string'||!value.plan||Array.isArray(value.plan)||value.plan.schema!=='alpha-source-assurance-plan/v3'||
     typeof value.approval_digest!=='string'||!/^[0-9a-f]{64}$/.test(value.approval_digest))throw Error('INPUT_FORMAT');
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
  const source=plan?.input?.plan;if(!source)return '';
  const fr=language==='fr',expiry=new Date(plan.expires_at*1000).toISOString();
  return [
    (fr?'Périmètre : ':'Scope: ')+plan.input.scope_id,
    (fr?'Révision publique exacte : ':'Exact public commit: ')+source.sourceRef,
    (fr?'Inventaire : ':'Manifest: ')+source.manifestPath+' · '+source.sourceCount+(fr?' fichiers publics':' public files'),
    (fr?'Expiration de la source : ':'Source approval expires: ')+source.expiresAt,
    (fr?'Expiration de l’exécuteur : ':'Executor approval expires: ')+expiry,
    fr?`Une tentative source ; ${source.maxSeconds} s pour le travail, ${source.maxSeconds} s pour la vérification indépendante ; limite totale de la demande : ${plan.request_seconds} s.`:
       `One source attempt; ${source.maxSeconds} s for work, ${source.maxSeconds} s for independent verification; total request elapsed cap: ${plan.request_seconds} s.`,
    fr?'ZIP attendu : deux inventaires, écarts et actions CSV complets, espace de travail portable, rapport, plan et acceptations.':
       'Expected ZIP: both inventories, complete difference/action CSVs, portable workspace, report, plan and acceptance records.',
    fr?'Aucune approbation du comportement du code, transaction ou reprise autonome.':'No source-behavior approval, transaction or unattended recovery.'
  ].join('\n');
}
if(typeof document!=='undefined') {
  const $=id=>document.getElementById(id);
  let language='en',token='',selected=null,busy=false,executorState='disconnected';
  const words={connected:['Connected to the existing local executor.','Connecté à l’exécuteur local existant.'],
    disconnected:['Disconnected; the local approved request may still be active.','Déconnecté ; la demande locale approuvée peut rester active.'],
    error:['Request failed. Inspect durable history before retrying; no automatic replay.','Demande échouée. Inspectez l’historique durable avant de réessayer ; aucune reprise automatique.'],
    input:['Import the exact owner-prepared input and a valid request ID.','Importez l’entrée exacte préparée par le responsable et un identifiant valide.'],
    prepared:['Review the exact finite plan before approval.','Examinez le plan fini exact avant approbation.'],
    approved:['Exact plan approved. You may now run its fixed mission.','Plan exact approuvé. Vous pouvez exécuter sa mission fixe.'],
    running:['Approved bounded work is running in the existing local process.','Le travail approuvé et borné s’exécute dans le processus local existant.'],
    complete:['Request returned. Inspect the retained outcome and verified download below.','Demande retournée. Examinez le résultat conservé et le téléchargement vérifié ci-dessous.'],
    paused:['Paused. Interrupted work requires inspection; no automatic replay.','Suspendu. Le travail interrompu exige une inspection ; aucune reprise automatique.'],
    stopped:['Permanent STOP recorded for this installed envelope.','ARRÊT permanent enregistré pour cette enveloppe installée.']};
  const say=key=>{$('status').textContent=words[key]?.[language==='fr'?1:0]||words.error[language==='fr'?1:0];};
  function controls(){
    $('prepare').disabled=!token||busy||executorState!=='ready';
    for(const id of ['refresh','pause','stop'])$(id).disabled=!token;
    $('resume').disabled=!token||executorState!=='paused';
    $('approve').disabled=!token||busy||executorState!=='ready'||selected?.state!=='prepared';
    $('run').disabled=!token||busy||executorState!=='ready'||selected?.state!=='approved';
    $('connect').disabled=busy;$('disconnect').disabled=!token;
  }
  async function api(action,body) {
    if(!token)throw Error('DISCONNECTED');
    const response=await fetch('/api/strategy-executor/'+action,{method:body?'POST':'GET',cache:'no-store',
      credentials:'omit',headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},
      ...(body?{body:JSON.stringify(body)}:{})});
    if(!response.ok)throw Error('HTTP_'+response.status);
    return response.json();
  }
  function save(bytes,mime,filename) {
    const url=URL.createObjectURL(new Blob([bytes],{type:mime})),anchor=document.createElement('a');
    anchor.href=url;anchor.download=filename;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function select(plan) {selected=plan;$('plan-summary').textContent=planSummary(plan,language);$('plan').textContent=plan?JSON.stringify(plan,null,2):'';controls();}
  async function history() {
    const status=await api('status');executorState=status.state;
    $('executor-state').textContent=(language==='fr'?'État de l’exécuteur : ':'Executor state: ')+status.state;
    $('history').replaceChildren();
    for(const plan of Object.values(status.plans||{})) {
      const article=document.createElement('article'),label=document.createElement('p');
      label.textContent=plan.plan_id+' · '+plan.state;article.append(label);
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
    controls();return status;
  }
  async function action(fn) {if(busy)return;busy=true;controls();try{await fn();}catch{say('error');}finally{busy=false;controls();}}
  $('language').onclick=()=>{
    language=language==='en'?'fr':'en';document.documentElement.lang=language;
    for(const element of document.querySelectorAll('[data-en]'))element.textContent=element.dataset[language];
    $('language').textContent=language==='en'?'Français':'English';
    $('input').setAttribute('aria-label',language==='fr'?'Entrée JSON de source préparée':'Prepared source input JSON');
    if(selected)select(selected);if(token)history().catch(()=>say('error'));
  };
  $('connect').onclick=()=>action(async()=>{token=$('token').value;$('token').value='';
    try{await history();say('connected');}catch(error){token='';throw error;}});
  $('disconnect').onclick=()=>{token='';executorState='disconnected';$('executor-state').textContent='';$('token').value='';selected=null;$('plan').textContent='';$('plan-summary').textContent='';$('history').replaceChildren();say('disconnected');controls();};
  $('input').oninput=()=>select(null);$('request-id').oninput=()=>select(null);
  $('file').onchange=async()=>{const file=$('file').files[0];try{
    if(!file||file.size>32768)throw Error('INPUT_BOUND');const raw=await file.text();parsePreparedInput(raw);$('input').value=raw;select(null);
  }catch{say('input');}finally{$('file').value='';}};
  $('prepare').onclick=()=>action(async()=>{
    let input;try{input=parsePreparedInput($('input').value);if(!/^[A-Za-z0-9_-]{1,64}$/.test($('request-id').value))throw Error('ID');}catch{say('input');return;}
    select(await api('prepare',{method:'run-mission',input,request_id:$('request-id').value}));say('prepared');await history();
  });
  const ref=()=>({plan_id:selected.plan_id,plan_digest:selected.plan_digest});
  $('approve').onclick=()=>action(async()=>{select(await api('approve',ref()));say('approved');await history();});
  $('run').onclick=()=>action(async()=>{say('running');select(await api('run',ref()));say('complete');await history();});
  $('refresh').onclick=()=>history().catch(()=>say('error'));
  const control=async(state,message)=>{try{await api('control',{state});say(message);await history();}catch{say('error');}};
  $('pause').onclick=()=>control('paused','paused');
  $('resume').onclick=()=>control('ready','connected');
  $('stop').onclick=()=>control('stopped','stopped');
  for(const element of document.querySelectorAll('[data-en]'))element.textContent=element.dataset.en;
  controls();
}
