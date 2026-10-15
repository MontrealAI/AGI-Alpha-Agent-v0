const $ = id => document.getElementById(id);
const english = Object.fromEntries([...document.querySelectorAll('[data-i18n]')].map(el => [el.dataset.i18n, el.textContent]));
const french = {
  eyebrow:'VOTRE TRAVAIL. VOS PREUVES. VOTRE CONTRÔLE.', title:'Une mission à conserver.',
  intro:'Transformez des données publiques ou synthétiques en rapport vérifié. Conservez les données, le résultat et votre avis ensemble, puis revenez quand vous le souhaitez.',
  local:'Calcul local dans ce navigateur', saved:'Missions enregistrées', open:'Ouvrir', new:'Nouvel exemple',
  import:'Inspecter un fichier enregistré', fork:'Utiliser les données dans une nouvelle mission',
  mission:'Mission', result:'Résultat', checks:'Vérifications', permissions:'Permissions', history:'Historique',
  name:'Nom de la mission', csv:'Données : CSV group,amount, avec montants entiers',unit:'Unité',rights:'Droits sur les données',
  source:'Source des données',license:'Licence ou permission',minutes:'Capacité de révision en minutes (1–120)',
  save:'Enregistrer les données',run:'Exécuter cette mission',stop:'Arrêter',interrupt:'Marquer l’exécution interrompue comme arrêtée',
  editHint:'Après enregistrement, les modifications effacent le résultat et l’avis courants. Les observations précédentes restent dans l’historique.',
  export:'Enregistrer le dossier de mission',exportHint:'Conservez une copie dans un fichier. Le stockage du navigateur peut être effacé ou indisponible. Les avis importés restent historiques.',
  note:'Votre note de révision',accept:'Accepter ce résultat localement',reject:'Rejeter ce résultat',
  reviewHint:'Votre avis est autodéclaré. Il n’autorise aucun paiement, aucune admission sur un marché ni aucune exécution externe.',
  permissionText:'Cette tâche utilise uniquement les données fournies. Aucun fournisseur, portefeuille ou exécuteur externe n’est connecté. Aucun fichier ne rétablit une transaction ou une permission.',
  cost:'Dépenses fournisseur et règlement : zéro. Coût de calcul de l’appareil et temps humain : inconnus.',
  fleet:'Fleet : aucun transfert vers un exécuteur commissionné n’est disponible ici pour ce rapport.',
  markets:'AGI Jobs utilise un processus d’admission $AGIALPHA distinct ; AGIJobManager utilise un processus USDC distinct.',
  historyHint:'Au plus 16 observations précédentes sont conservées. Les empreintes vérifient la cohérence, pas l’identité ni une certification indépendante.',
  sourceHint:'Identité exacte du code intégré',
};
let language='en', db=null, current=null, readOnly=false, dirty=false, busy=false, epoch=0;
let pendingRun=false, stopping=false, unpersisted=false;
let active=null, historicalBytes=null, mode='empty', ready=false;
const urls=[];
const say=(en,fr)=>language==='fr'?fr:en;
function status(en,fr=en){$('status').textContent=say(en,fr);}
function clearError(){$('error').hidden=true;$('error').textContent='';}
function error(e){$('error').hidden=false;$('error').textContent=String(e?.code||e?.message||e);}
function id(){return crypto.randomUUID();}
function view(name){document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==name);document.querySelectorAll('[data-view]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.view===name)));}
function controls(){
  const writable=ready&&db&&current&&!readOnly&&!busy&&!pendingRun&&!stopping&&current.state!=='running';
  for(const key of ['name','csv','unit','rights','source','license','minutes'])$(key).disabled=!writable;
  $('save').disabled=!writable||!dirty;
  $('run').disabled=!writable||dirty;
  $('stop').disabled=!active||readOnly;
  $('interrupt').disabled=!ready||!db||!current||readOnly||busy||!!active||current.state!=='running';
  $('note').disabled=!writable||dirty||current.state!=='result';
  $('accept').disabled=$('reject').disabled=$('note').disabled;
  $('export').disabled=!current||busy;
  $('fork').disabled=!db||busy||pendingRun||stopping||!historicalBytes;
  for(const key of ['open','new','saved'])$(key).disabled=!ready||!db||busy||pendingRun||stopping||!!active;
  $('import').disabled=!ready||busy||pendingRun||stopping||!!active;
  $('language').disabled=!ready;
  document.querySelectorAll('[data-view]').forEach(el=>el.disabled=!ready);
}
function fill(){if(!current)return;const s=current.spec;for(const [key,value]of Object.entries({name:s.name,csv:s.inputs.csv,unit:s.inputs.unit,rights:s.rights.dataClass,source:s.rights.source,license:s.rights.license,minutes:String(s.reviewMinutes)}))$(key).value=value;$('note').value='';dirty=false;}
function spec(){
  const raw=$('minutes').value;
  if(!/^(0|[1-9][0-9]*)$/.test(raw))throw Error('REVIEW_MINUTES_REQUIRE_INTEGER_TEXT');
  return {...current.spec,name:$('name').value,inputs:{csv:$('csv').value,unit:$('unit').value},
    rights:{dataClass:$('rights').value,source:$('source').value,license:$('license').value},reviewMinutes:Number(raw)};
}
function download(text,name,type='application/json'){
  const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function render(){
  for(const url of urls.splice(0))URL.revokeObjectURL(url);
  $('files').replaceChildren();
  const result=current?.result?.pack;
  const historical=readOnly||dirty;
  $('result-summary').textContent=!result?say('No current result. Save your input, then run the mission.','Aucun résultat courant. Enregistrez les données, puis exécutez la mission.'):
    (historical?say('Historical result. It is not current for this page. ','Résultat historique. Il n’est pas courant pour cette page. '):'')+JSON.stringify(result.result.summary);
  $('result-data').textContent=result?JSON.stringify(result.result.evidence,null,2):'';
  if(result)for(const file of result.result.artifacts){
    const button=document.createElement('button');button.textContent=file.name;button.addEventListener('click',()=>download(file.content,file.name,file.type));$('files').append(button);
  }
  $('check-summary').textContent=result?(historical?say('Historical checks only.','Vérifications historiques seulement.'):say('Deterministic output and exact hashes checked. Your separate review is still your decision.','Résultat déterministe et empreintes exactes vérifiés. Votre avis distinct reste votre décision.')):say('No completed result to review.','Aucun résultat terminé à examiner.');
  $('check-data').textContent=current?JSON.stringify({mode,state:current.state,sourceHash:current.sourceHash,specDigest:current.specDigest,
    persisted:!unpersisted,resultDigest:current.result?.bindingDigest??null,review:current.review,currentReview:historical?null:current.review},null,2):'';
  $('history-data').textContent=current?JSON.stringify(current.history,null,2):'';
  $('identity').textContent=current?`${current.missionId} · revision ${current.revision} · ${mode}`:'';
  controls();
}
async function refreshList(){if(!db)return;const all=await db.list();$('saved').replaceChildren();for(const item of all){const option=document.createElement('option');option.value=item.missionId;option.textContent=`${item.spec?.name||item.missionId} · r${item.revision}`;$('saved').append(option);}if(current)$('saved').value=current.missionId;}
function loseStorage(e,confirmed=false){
  try{db?.close();}catch{}db=null;readOnly=true;mode='lost-storage';error(e);
  status(confirmed?'The change committed, but the storage index could not be read. Export this record; further execution is disabled.':'Local storage is unavailable or corrupt. You may inspect a file; execution is disabled.',
    confirmed?'La modification a été enregistrée, mais l’index est illisible. Exportez ce dossier ; l’exécution est désactivée.':'Le stockage local est indisponible ou corrompu. Vous pouvez inspecter un fichier ; l’exécution est désactivée.');
}
async function persist(next,expected){
  await records.validateRecord(next);
  try{await db.save(next,expected);}catch(e){
    current=next;unpersisted=true;
    if(e.code==='LOCAL_REVISION_CONFLICT'){readOnly=true;mode='conflict';active?.controller.abort();status('Another tab changed this mission. This unpersisted copy is read-only. Export it or open the saved mission to inspect the latest revision.','Un autre onglet a modifié cette mission. Cette copie non enregistrée est en lecture seule. Exportez-la ou ouvrez la mission enregistrée pour voir la dernière révision.');}
    else{readOnly=true;mode='lost-storage';active?.controller.abort();status('Storage could not confirm this change. Keep a file copy and reopen before continuing.','Le stockage n’a pas confirmé cette modification. Conservez une copie et rouvrez avant de continuer.');}
    throw e;
  }
  current=next;unpersisted=false;dirty=false;try{await refreshList();}catch(e){loseStorage(e,true);}render();
}
async function operation(action){if(busy||active||pendingRun||stopping)return;++epoch;busy=true;clearError();controls();try{await action();}catch(e){error(e);}finally{busy=false;render();}}
async function openSaved(){const token=++epoch;const item=await db.get($('saved').value);if(!item)throw Error('LOCAL_MISSION_MISSING');const checked=await records.validateRecord(item);if(token!==epoch)return;current=checked;unpersisted=false;historicalBytes=null;readOnly=current.sourceHash!==SOURCE_HASH;mode=readOnly?'historical':'current';fill();render();status(readOnly?'Source changed. This record is historical and read-only. Export and import to create a new draft.':'Saved mission opened. No execution has restarted.',readOnly?'Le code a changé. Ce dossier est historique et en lecture seule. Exportez et importez pour créer un brouillon.':'Mission enregistrée ouverte. Aucune exécution n’a redémarré.');}
async function newMission(){++epoch;const record=await records.createRecord({missionId:id(),sourceHash:SOURCE_HASH,spec:workbench.example('public-data')});await persist(record,null);if(!db)return;readOnly=false;mode='current';historicalBytes=null;fill();view('mission');status('Example saved locally. Edit the input or run it.','Exemple enregistré localement. Modifiez les données ou exécutez-le.');}
async function run(){
  if(busy||active||pendingRun||stopping||dirty||readOnly||!current)return;
  pendingRun=true;
  busy=true;++epoch;clearError();controls();
  let attempt=null;
  try{
    const prior=current;const next=await records.startRun(prior,{expectedRevision:prior.revision,runId:id()});
    await persist(next,prior.revision);
    if(!db||readOnly)return;
    attempt={record:next,controller:new AbortController(),epoch:++epoch};active=attempt;busy=false;controls();
    status('Running the saved input locally…','Exécution locale des données enregistrées…');
    const pack=await workbench.run(next.spec,{sourceHash:SOURCE_HASH,signal:attempt.controller.signal});
    if(active!==attempt||epoch!==attempt.epoch||attempt.controller.signal.aborted)return;
    busy=true;
    const finished=await records.completeRun(next,pack,{expectedRevision:next.revision,runId:next.run.runId});
    if(active!==attempt||epoch!==attempt.epoch||attempt.controller.signal.aborted)return;
    await persist(finished,next.revision);active=null;view('result');
    if(!readOnly)status('Result saved. Inspect its files and checks, then record your review.','Résultat enregistré. Inspectez les fichiers et vérifications, puis consignez votre avis.');
  }catch(e){if(active!==attempt)return;error(e);active=null;attempt?.controller.abort();if(attempt&&!readOnly){++epoch;try{const stopped=await records.interruptRun(attempt.record,{expectedRevision:attempt.record.revision,runId:attempt.record.run.runId,reason:String(e.message).slice(0,200)});await persist(stopped,attempt.record.revision);}catch(failure){error(failure);}}}
  finally{pendingRun=false;busy=false;render();}
}
async function stop(){const attempt=active;if(!attempt||stopping)return;stopping=true;active=null;++epoch;attempt.controller.abort();busy=true;controls();try{const stopped=await records.stopRun(attempt.record,{expectedRevision:attempt.record.revision,runId:attempt.record.run.runId,reason:'User requested STOP.'});await persist(stopped,attempt.record.revision);if(!readOnly)status('Stopped. No result was promoted.','Arrêté. Aucun résultat n’a été promu.');}catch(e){error(e);}finally{stopping=false;busy=false;render();}}
$('editor').addEventListener('submit',event=>{event.preventDefault();operation(async()=>{const prior=current;const next=await records.editRecord(prior,spec(),{expectedRevision:prior.revision});await persist(next,prior.revision);fill();if(!readOnly)status('Input saved. Prior results are historical.','Données enregistrées. Les résultats précédents sont historiques.');});});
for(const key of ['name','csv','unit','rights','source','license','minutes'])$(key).addEventListener('input',()=>{dirty=true;++epoch;render();});
$('new').addEventListener('click',()=>operation(newMission));$('open').addEventListener('click',()=>operation(openSaved));$('run').addEventListener('click',run);$('stop').addEventListener('click',stop);
$('interrupt').addEventListener('click',()=>operation(async()=>{const prior=current;await persist(await records.interruptRun(prior,{expectedRevision:prior.revision,runId:prior.run.runId,reason:'Explicit recovery after interrupted browser session.'}),prior.revision);if(!readOnly)status('Interrupted run closed. A new run requires your action.','Exécution interrompue fermée. Une nouvelle exécution nécessite votre action.');}));
for(const [button,decision]of [['accept','accepted'],['reject','rejected']])$(button).addEventListener('click',()=>operation(async()=>{const prior=current;await persist(await records.reviewRecord(prior,{expectedRevision:prior.revision,decision,note:$('note').value}),prior.revision);if(!readOnly)status('Your local review is saved. No external authority was granted.','Votre avis local est enregistré. Aucune autorité externe n’a été accordée.');}));
$('export').addEventListener('click',()=>operation(async()=>{download(await records.serializeRecord(current),`successor-${unpersisted?'unpersisted-':''}${current.missionId}.json`);}));
$('import').addEventListener('change',async()=>{
  const file=$('import').files[0];if(!file||active||pendingRun||stopping)return;const token=++epoch;busy=true;clearError();controls();
  try{if(file.size>records.RECORD_LIMITS.bytes)throw Error('RECORD_BYTES');const bytes=new Uint8Array(await file.arrayBuffer());const restored=await records.restoreRecord(bytes,{sourceHash:SOURCE_HASH});if(token!==epoch||$('import').files[0]!==file)return;current=restored.record;unpersisted=true;historicalBytes=bytes;readOnly=true;mode='historical';fill();render();status('Imported file inspected as historical evidence. Use its input in a new mission to run and review locally.','Fichier importé inspecté comme preuve historique. Utilisez ses données dans une nouvelle mission pour exécuter et examiner localement.');}catch(e){if(token===epoch)error(e);}finally{if($('import').files[0]===file)$('import').value='';if(token===epoch){busy=false;render();}}
});
$('fork').addEventListener('click',()=>operation(async()=>{const record=await records.importRecord(historicalBytes,{missionId:id(),sourceHash:SOURCE_HASH});await persist(record,null);if(!db)return;readOnly=false;mode='current';historicalBytes=null;fill();view('mission');status('New draft saved. Imported results and reviews remain historical.','Nouveau brouillon enregistré. Les résultats et avis importés restent historiques.');}));
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>view(button.dataset.view)));
$('language').addEventListener('click',()=>{language=language==='en'?'fr':'en';document.documentElement.lang=language;$('language').textContent=language==='en'?'Français':'English';for(const el of document.querySelectorAll('[data-i18n]'))el.textContent=(language==='fr'?french:english)[el.dataset.i18n]||english[el.dataset.i18n];render();});
(async()=>{try{db=await storage.openMissionStore();await refreshList();status('Choose a saved mission or create a new example.','Choisissez une mission enregistrée ou créez un nouvel exemple.');}catch(e){loseStorage(e);}finally{ready=true;render();}})();
