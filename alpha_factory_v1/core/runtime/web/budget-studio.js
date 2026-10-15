// SPDX-License-Identifier: Apache-2.0
'use strict';
const $=id=>document.getElementById(id);
const STORAGE_KEY='agialpha.native-budget.pending.v1';
const MAX_RECOVERY_BYTES=8192,MAX_RESPONSE_BYTES=8*1024*1024;
let accessToken='',journalIdentity='',epoch=0,busy=false,snapshot=null,preview=null,pending=null,invalidRecovery=false,timer=null,messageKey=null,messageError=false;
const requests=new Set();
const english=Object.fromEntries([...document.querySelectorAll('[data-i18n]')].map(node=>[node.dataset.i18n,node.textContent]));
const french={
  skip:'Aller à l’espace de travail',local:'OPÉRATEUR LOCAL',studio:'Studio Ascension',agent:'Espace de l’agent',language:'Langue',
  eyebrow:'UN JOURNAL · UNITÉS EXACTES · RAPPROCHEMENT EXPLICITE',title:'Coordonner un budget de planification.',
  intro:'Les sessions utilisant ce même journal natif partagent un budget déclaré pour un propriétaire, une chaîne et un jeton. Réservez une capacité de planification, puis rapprochez-la explicitement.',
  boundary:'Ceci ne bloque aucun fonds, ne vérifie ni propriété ni solde, n’empêche aucun transfert externe et n’autorise aucun paiement ou exécution. Les répertoires d’agents distincts et copies du journal ne se coordonnent pas. Utilisez un seul journal faisant autorité.',
  connectTitle:'Se connecter à cet agent installé',tokenHelp:'Utilisez son jeton d’accès existant. Il reste uniquement en mémoire, jamais dans la récupération, une URL ou un téléchargement. Recharger ou déconnecter l’efface.',
  token:'Jeton d’accès',connect:'Se connecter',authority:'Journal connecté',disconnect:'Se déconnecter',
  sessionHelp:'Changer de connexion ou de portée invalide l’aperçu. Chaque nouvelle demande utilise la révision inspectée. Une réponse perdue conserve la demande exacte pour une nouvelle tentative explicite.',
  scope:'Portée exacte de planification',owner:'Adresse du propriétaire déclaré',chain:'ID de chaîne',asset:'Adresse du jeton',inspect:'Inspecter l’état de planification conservé',snapshot:'Dernier état inspecté',
  units:'Tous les montants sont des unités de base exactes du jeton. Le plafond cumulatif est une hypothèse de l’opérateur, pas un solde ou un revenu. Les réservations actives n’expirent jamais automatiquement. Les montants consommés restent déduits.',
  rawState:'Dossier conservé du journal',operation:'Préparer une demande de planification explicite',action:'Opération',
  set_limit:'Fixer le plafond cumulatif de planification',reserve:'Réserver une capacité pour un projet',release:'Libérer une réservation active rapprochée',commit:'Enregistrer la capacité consommée',
  reservation:'ID stable de réservation',amount:'Montant exact en unités de base',purpose:'Projet/cycle ou motif du rapprochement',prepare:'Examiner la demande exacte',preview:'Examiner avant l’enregistrement',
  storageDisclosure:'Avant l’envoi, cet onglet conserve la demande exacte, le propriétaire déclaré, les montants, le motif et l’identité du journal dans son stockage de session pour récupération après rechargement. Aucun jeton d’accès n’est conservé. Cette copie reste jusqu’à une réponse vérifiée ou un rapprochement explicite; elle n’autorise aucune dépense.',
  confirmAck:'J’ai examiné cette demande exacte et sa révision inspectée. J’autorise son enregistrement et la copie de récupération divulguée de cet onglet. Libérer ou consommer reflète mon rapprochement distinct; ce n’est pas une preuve de paiement.',
  confirm:'Enregistrer la demande examinée',cancel:'Annuler l’aperçu',pending:'Demande conservée à examiner',
  pendingHelp:'Reconnectez-vous au même journal et inspectez cette portée exacte avant de réessayer. Seuls la demande native inchangée et son ID seront renvoyés. Aucune transaction de portefeuille n’est rejouée ni réservation libérée. Une réponse indisponible ne prouve pas un échec.',
  retryAck:'J’ai examiné la demande exacte originale et j’autorise uniquement sa nouvelle tentative native idempotente.',retry:'Réessayer la demande exacte',export:'Télécharger la copie de récupération',
  dismissAck:'J’ai inspecté l’état actuel et le refus explicite. Effacer uniquement cette demande refusée pour préparer de nouvelles conditions examinées. Ne modifier aucune réservation.',dismiss:'Effacer la demande refusée rapprochée',
  invalidTitle:'Copie de récupération indisponible',invalidHelp:'Les données de cet onglet sont mal formées, trop grandes ou indisponibles. Toute nouvelle mutation est bloquée. Conservez et rapprochez toute demande incertaine auprès du journal original avant d’effacer la copie locale.',
  invalidAck:'J’ai conservé et rapproché toute demande incertaine. Effacer cette copie inutilisable sans modifier le journal.',clearInvalid:'Effacer la copie locale inutilisable',
  footer:'Coordination de planification uniquement. Garde des fonds, dépôt du marché, autorisations d’exécution et décisions de revue restent distincts.',notice:'Avis du projet'
};
const words={
  en:{ready:'Connect explicitly, then inspect the exact planning scope.',connected:'Connected. Inspect an exact scope; no request was replayed.',
    disconnected:'Disconnected. Token and private page contents cleared. Any pending request copy remains in this tab for explicit recovery.',
    changed:'Connection or journal changed. Reconnect to the original journal and inspect again.',
    unavailable:'Response unavailable. Current capacity is unknown. Inspect the original journal; do not infer failure or release a reservation.',
    invalid:'The response or recovery record is unsupported. No new mutation is permitted.',
    scope:'Use nonzero owner/token addresses and an exact positive chain ID.',units:'Use canonical whole-number base units up to uint256.',
    fresh:'Inspect this exact scope again before preparing or retrying.',conflict:'The request was explicitly rejected. Inspect current state before reviewing any new terms.',
    auth:'Authentication failed. Reconnect using the existing authorized token.',missing:'No pool was found for this exact scope. Only a reviewed initial ceiling can be recorded.',
    current:'Observed planning revision; a concurrent change will reject stale terms.',expired:'Inspection expired. Refresh before any new request or retry.',
    limit:'Cumulative ceiling',reserved:'Active reservations',committed:'Consumed capacity',available:'Unallocated planning capacity',revision:'Inspected revision',
    empty:'No retained reservations.',select:'Review reconciliation',reservedState:'Reserved',releasedState:'Released',committedState:'Consumed',
    initialize:'Set or adjust a cumulative planning ceiling. It cannot fall below retained reservations plus consumed capacity.',
    reserveHelp:'Use a new stable reservation ID and identify the project/cycle. Existing IDs cannot be reused.',
    terminalHelp:'Use the exact ID of an active reservation. Amount is fixed to zero because the server reconciles its full retained amount. Inspect any uncertain wallet effect separately.',
    confirm:'Review and explicitly acknowledge the exact request.',prepared:'Preview only. Nothing has been recorded.',
    recorded:'Request recorded in the native journal. No wallet funds were moved or locked.',replayed:'Exact request recognized; current retained state returned. No second mutation was made.',
    pending:'An exact request is retained. Its effect may be unknown; inspect and retry it without changing any field.',
    rejected:'The exact request received an explicit rejection. Inspect current state before clearing this copy or retrying unchanged.',
    wrongJournal:'The pending copy belongs to a different journal. No retry or new mutation is permitted here.',
    storage:'Recovery storage is unavailable. New mutations are blocked. Preserve and reconcile the original request.',
    restored:'A pending request was recovered locally. Reconnect to its original journal, inspect its scope and explicitly retry.',
    cleared:'Only the reconciled local copy was cleared. No journal reservation was changed.',
    purpose:'Provide a purpose or reconciliation reason of 1–500 characters.',reservation:'Use a stable ID of 1–64 letters, digits, underscores or hyphens.',
    insufficient:'The requested amount exceeds the last inspected planning capacity.',active:'Select a retained active reservation.',unknown:'An unresolved request must be reconciled before preparing another.'},
  fr:{ready:'Connectez-vous explicitement, puis inspectez la portée exacte.',connected:'Connecté. Inspectez une portée exacte; aucune demande n’a été rejouée.',
    disconnected:'Déconnecté. Jeton et contenu privé effacés. Toute copie en attente reste dans cet onglet pour récupération explicite.',
    changed:'Connexion ou journal modifié. Reconnectez-vous au journal original et inspectez à nouveau.',
    unavailable:'Réponse indisponible. Capacité actuelle inconnue. Inspectez le journal original; ne déduisez aucun échec et ne libérez aucune réservation.',
    invalid:'Réponse ou récupération non prise en charge. Aucune nouvelle mutation permise.',scope:'Utilisez des adresses non nulles et un ID de chaîne entier positif exact.',
    units:'Utilisez des unités de base entières canoniques jusqu’à uint256.',fresh:'Inspectez à nouveau cette portée exacte avant de préparer ou réessayer.',
    conflict:'Demande explicitement refusée. Inspectez l’état actuel avant d’examiner de nouvelles conditions.',auth:'Échec d’authentification. Reconnectez-vous avec le jeton autorisé existant.',
    missing:'Aucun budget trouvé pour cette portée exacte. Seul un plafond initial examiné peut être enregistré.',
    current:'Révision de planification observée; un changement concurrent refusera les conditions périmées.',expired:'Inspection périmée. Actualisez avant toute demande ou nouvelle tentative.',
    limit:'Plafond cumulatif',reserved:'Réservations actives',committed:'Capacité consommée',available:'Capacité de planification non allouée',revision:'Révision inspectée',empty:'Aucune réservation conservée.',
    select:'Examiner le rapprochement',reservedState:'Réservé',releasedState:'Libéré',committedState:'Consommé',
    initialize:'Fixer ou ajuster un plafond cumulatif. Il ne peut être inférieur aux réservations conservées et à la capacité consommée.',
    reserveHelp:'Utilisez un nouvel ID stable et identifiez le projet/cycle. Un ID existant ne peut pas être réutilisé.',
    terminalHelp:'Utilisez l’ID exact d’une réservation active. Le montant est fixé à zéro; le serveur rapproche le montant conservé complet. Inspectez séparément tout effet incertain du portefeuille.',
    confirm:'Examinez et confirmez explicitement la demande exacte.',prepared:'Aperçu uniquement. Rien n’a été enregistré.',
    recorded:'Demande enregistrée dans le journal natif. Aucun fonds déplacé ou bloqué.',replayed:'Demande exacte reconnue; état conservé actuel retourné. Aucune seconde mutation.',
    pending:'Une demande exacte est conservée. Son effet peut être inconnu; inspectez et réessayez sans modifier aucun champ.',
    rejected:'La demande exacte a reçu un refus explicite. Inspectez l’état actuel avant d’effacer cette copie ou de réessayer sans changement.',
    wrongJournal:'Cette copie appartient à un autre journal. Aucune nouvelle tentative ni mutation permise ici.',
    storage:'Stockage de récupération indisponible. Les mutations restent bloquées. Conservez et rapprochez la demande originale.',
    restored:'Demande récupérée localement. Reconnectez-vous au journal original, inspectez sa portée et réessayez explicitement.',
    cleared:'Seule la copie locale rapprochée a été effacée. Aucune réservation modifiée.',purpose:'Indiquez un motif de 1 à 500 caractères.',
    reservation:'Utilisez un ID stable de 1 à 64 lettres, chiffres, tirets ou traits de soulignement.',insufficient:'Le montant dépasse la capacité inspectée.',
    active:'Choisissez une réservation active conservée.',unknown:'Rapprochez la demande non résolue avant d’en préparer une autre.'}
};
const lang=()=>$('language').value==='fr'?'fr':'en',t=key=>words[lang()][key],pretty=value=>JSON.stringify(value,null,2);
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const exact=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join()===keys.slice().sort().join();
const bytes=text=>new TextEncoder().encode(text).length;
function message(value,error=false){messageKey=Object.keys(words[lang()]).find(key=>t(key)===value)||null;messageError=error;
  $('message').textContent=value;$('message').className=error?'error':'';}
function amount(value){if(typeof value!=='string'||!/^(0|[1-9][0-9]{0,77})$/.test(value)||BigInt(value)>(1n<<256n)-1n)throw Error(t('units'));return value;}
function scope(value){
  if(!exact(value,['owner','chain_id','token'])||!Number.isSafeInteger(value.chain_id)||value.chain_id<1||
    !['owner','token'].every(key=>typeof value[key]==='string'&&/^0x[0-9a-fA-F]{40}$/.test(value[key])&&BigInt(value[key])!==0n))throw Error(t('scope'));
  return {owner:value.owner.toLowerCase(),chain_id:value.chain_id,token:value.token.toLowerCase()};
}
function formScope(){const chain=$('chain-id').value;if(!/^[1-9][0-9]*$/.test(chain))throw Error(t('scope'));return scope({owner:$('owner').value.trim(),chain_id:Number(chain),token:$('asset-token').value.trim()});}
function validateCommand(value){
  if(!exact(value,['scope','request_id','action','expected_revision','reservation_id','amount','purpose'])||
    !['set_limit','reserve','release','commit'].includes(value.action)||!Number.isSafeInteger(value.expected_revision)||value.expected_revision<0||
    typeof value.request_id!=='string'||!/^[a-zA-Z0-9_-]{1,64}$/.test(value.request_id))throw Error(t('invalid'));
  const checked=scope(value.scope);if(!equal(checked,value.scope))throw Error(t('invalid'));
  amount(value.amount);
  if(typeof value.purpose!=='string'||!value.purpose.trim()||[...value.purpose].length>500)throw Error(t('purpose'));
  if(typeof value.reservation_id!=='string'||(value.action==='set_limit'?value.reservation_id!=='' : !/^[a-zA-Z0-9_-]{1,64}$/.test(value.reservation_id)))throw Error(t('reservation'));
  if(value.action==='reserve'&&value.amount==='0'||['release','commit'].includes(value.action)&&value.amount!=='0')throw Error(t('units'));
  return value;
}
function validateRecovery(value){
  if(!exact(value,['schema','origin','journal','command','state'])||value.schema!==STORAGE_KEY||value.origin!==location.origin||
    !/^urn:agialpha:ed25519:[0-9a-f]{64}$/.test(value.journal)||!['unknown','rejected'].includes(value.state))throw Error(t('invalid'));
  validateCommand(value.command);if(bytes(JSON.stringify(value))>MAX_RECOVERY_BYTES)throw Error(t('invalid'));return value;
}
function storePending(value){
  try{const text=JSON.stringify(validateRecovery(value));sessionStorage.setItem(STORAGE_KEY,text);
    if(sessionStorage.getItem(STORAGE_KEY)!==text)throw Error();pending=value;
  }catch{invalidRecovery=true;throw Error(t('storage'));}
}
function removePending(){
  try{sessionStorage.removeItem(STORAGE_KEY);if(sessionStorage.getItem(STORAGE_KEY)!==null)throw Error();pending=null;invalidRecovery=false;}
  catch{invalidRecovery=true;throw Error(t('storage'));}
}
try{const text=sessionStorage.getItem(STORAGE_KEY);if(text!==null){if(bytes(text)>MAX_RECOVERY_BYTES)throw Error();const value=JSON.parse(text);
  if(JSON.stringify(value)!==text)throw Error();pending=validateRecovery(value);}}
catch{invalidRecovery=true;}
function current(){try{return !!accessToken&&!!journalIdentity&&!!snapshot&&snapshot.epoch===epoch&&performance.now()<snapshot.expires&&equal(snapshot.scope,formScope());}catch{return false;}}
function invalidate(){snapshot=null;preview=null;clearTimeout(timer);$('confirm-ack').checked=false;$('retry-ack').checked=false;$('dismiss-ack').checked=false;render();}
function acceptSnapshot(record,wanted,missing=false){
  snapshot={scope:wanted,record,missing,revision:missing?0:record.revision,epoch,expires:performance.now()+60000};preview=null;
  clearTimeout(timer);timer=setTimeout(()=>{preview=null;$('confirm-ack').checked=false;render();message(t('expired'));},60000);
}
function checkedRecord(record,wanted){
  if(!record||!equal(scope(record.scope),wanted)||!Number.isSafeInteger(record.revision)||record.revision<1||
    typeof record.digest!=='string'||!/^[0-9a-f]{64}$/.test(record.digest)||record.authority!=='planning-only'||
    record.wallet_balance_verified!==false||record.external_transfers_prevented!==false||!record.reservations||
    typeof record.reservations!=='object'||Array.isArray(record.reservations)||Object.keys(record.reservations).length>1024)throw Error(t('invalid'));
  let reserved=0n,committed=0n;
  for(const [id,item] of Object.entries(record.reservations)){
    if(!/^[a-zA-Z0-9_-]{1,64}$/.test(id)||!item||!['reserved','released','committed'].includes(item.state)||typeof item.purpose!=='string'||[...item.purpose].length>500)throw Error(t('invalid'));
    const count=BigInt(amount(item.amount));if(item.state==='reserved')reserved+=count;if(item.state==='committed')committed+=count;
  }
  const limit=BigInt(amount(record.limit));
  if(amount(record.reserved)!==String(reserved)||amount(record.committed)!==String(committed)||amount(record.available)!==String(limit-reserved-committed))throw Error(t('invalid'));
  return record;
}
async function api(path,body){
  const started=epoch,token=accessToken,identity=journalIdentity,controller=new AbortController();requests.add(controller);
  try{
    const response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',cache:'no-store',credentials:'omit',redirect:'error',signal:controller.signal,
      headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',...(identity?{'X-AGIALPHA-Journal':identity}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
    if(response.url!==location.origin+'/api'+path)throw Error(t('invalid'));
    if(!response.ok){await response.body?.cancel();if(started!==epoch)throw Error(t('changed'));
      const error=Error(t(response.status===401?'auth':response.status===409?'conflict':'invalid'));error.httpStatus=response.status;throw error;}
    const reader=response.body?.getReader();if(!reader)throw Error(t('invalid'));
    const chunks=[];let size=0;
    try{while(true){const chunk=await reader.read();if(chunk.done)break;size+=chunk.value.byteLength;
      if(size>MAX_RESPONSE_BYTES){await reader.cancel();throw Error(t('invalid'));}chunks.push(chunk.value);}}
    finally{reader.releaseLock();}
    if(started!==epoch)throw Error(t('changed'));
    const joined=new Uint8Array(size);let offset=0;for(const chunk of chunks){joined.set(chunk,offset);offset+=chunk.byteLength;}
    return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(joined));
  }finally{requests.delete(controller);}
}
async function verifyJournal(){const status=await api('/status');if(status.valid!==true||status.identity!==journalIdentity)throw Error(t('changed'));}
async function guarded(action){
  if(busy)return;const started=epoch;busy=true;render();
  try{await action();}catch(error){if(started!==epoch)return;
    if(error.httpStatus===401){disconnect();message(t('auth'),true);}else{snapshot=null;preview=null;message(Object.values(words[lang()]).includes(error.message)?error.message:t('unavailable'),true);}
  }finally{if(started===epoch){busy=false;render();}}
}
function disconnect(){epoch++;for(const request of requests)request.abort();requests.clear();clearTimeout(timer);accessToken='';journalIdentity='';snapshot=null;preview=null;busy=false;
  for(const id of ['token','owner','chain-id','asset-token','reservation-id','amount','purpose'])$(id).value='';
  for(const id of ['confirm-ack','retry-ack','dismiss-ack','invalid-ack'])$(id).checked=false;
  for(const id of ['record','preview-record','pending-record','journal-identity'])$(id).textContent='';$('totals').replaceChildren();$('reservations').replaceChildren();
  render();message(t('disconnected'));
}
function render(){
  const connected=!!accessToken&&!!journalIdentity,fresh=current(),matching=!!pending&&pending.journal===journalIdentity;
  $('login').hidden=connected;$('workspace').hidden=!connected;$('workspace').setAttribute('aria-busy',String(busy));
  $('journal-identity').textContent=journalIdentity;
  for(const field of document.querySelectorAll('#workspace input,#workspace textarea,#workspace select,#workspace button'))if(field.id!=='disconnect')field.disabled=busy;
  for(const id of ['owner','chain-id','asset-token'])$(id).readOnly=!!pending;
  $('prepare').disabled=busy||!fresh||!!pending||invalidRecovery;
  $('preview-panel').hidden=!preview||!!pending;
  $('confirm').disabled=busy||!fresh||!preview||!$('confirm-ack').checked||invalidRecovery||!!pending;
  const terminal=['release','commit'].includes($('action').value),initial=$('action').value==='set_limit';
  $('reservation-id').disabled=busy||initial;$('reservation-id').required=!initial;$('amount').readOnly=terminal;
  $('operation-help').textContent=t(initial?'initialize':terminal?'terminalHelp':'reserveHelp');
  $('snapshot-panel').hidden=!snapshot;
  if(snapshot){$('snapshot-state').textContent=t(!fresh?'expired':snapshot.missing?'missing':'current');
    const values=[[t('revision'),snapshot.revision],...(!snapshot.missing?['limit','reserved','committed','available'].map(key=>[t(key),snapshot.record[key]]):[])];
    $('totals').replaceChildren(...values.flatMap(([label,value])=>{const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(value);return [dt,dd];}));
    $('record').textContent=pretty(snapshot.missing?{scope:snapshot.scope,state:'not-initialized',revision:0}:snapshot.record);
    $('reservations').replaceChildren();
    const rows=Object.entries(snapshot.record?.reservations||{});
    if(!rows.length){const p=document.createElement('p');p.textContent=t('empty');$('reservations').append(p);}
    for(const [id,entry] of rows){const item=document.createElement('div'),p=document.createElement('p');
      p.textContent=`${id} · ${entry.amount} · ${t(entry.state+'State')} · ${entry.purpose}`;item.append(p);
      if(entry.state==='reserved'){const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=t('select');button.disabled=busy||!fresh||!!pending||invalidRecovery;
        button.addEventListener('click',()=>{$('action').value='release';$('reservation-id').value=id;$('amount').value='0';preview=null;render();$('purpose').focus();});item.append(button);}
      $('reservations').append(item);}
  }
  $('pending-panel').hidden=!pending;
  if(pending){$('pending-state').textContent=t(!matching?'wrongJournal':pending.state==='rejected'?'rejected':'pending');$('pending-record').textContent=connected?pretty(pending):'';}
  const retryReady=fresh&&matching&&equal(snapshot.scope,pending?.command.scope)&&!invalidRecovery;
  $('retry').disabled=busy||!retryReady||!$('retry-ack').checked;
  $('export-pending').disabled=busy||!pending;
  $('rejected-controls').hidden=pending?.state!=='rejected';$('dismiss').disabled=busy||!retryReady||!$('dismiss-ack').checked;
  $('invalid-panel').hidden=!invalidRecovery;$('clear-invalid').disabled=busy||!$('invalid-ack').checked;
}
async function inspect(){
  const wanted=formScope();invalidate();await verifyJournal();
  try{const result=checkedRecord(await api('/budget/inspect',wanted),wanted);acceptSnapshot(result,wanted);message(t('current'));}
  catch(error){if(error.httpStatus!==404)throw error;acceptSnapshot(null,wanted,true);message(t('missing'));}
}
function prepare(){
  if(!current())throw Error(t('fresh'));if(pending||invalidRecovery)throw Error(t('unknown'));
  const action=$('action').value,terminal=['release','commit'].includes(action);
  const command=validateCommand({scope:snapshot.scope,request_id:crypto.randomUUID(),action,expected_revision:snapshot.revision,
    reservation_id:action==='set_limit'?'':$('reservation-id').value.trim(),amount:terminal?'0':$('amount').value,purpose:$('purpose').value.trim()});
  if(snapshot.missing&&action!=='set_limit')throw Error(t('fresh'));
  if(action==='reserve'&&(Object.hasOwn(snapshot.record.reservations,command.reservation_id)||BigInt(command.amount)>BigInt(snapshot.record.available)))throw Error(t('insufficient'));
  if(terminal&&snapshot.record?.reservations[command.reservation_id]?.state!=='reserved')throw Error(t('active'));
  preview={schema:STORAGE_KEY,origin:location.origin,journal:journalIdentity,command,state:'unknown'};
  $('preview-record').textContent=pretty(preview);$('confirm-ack').checked=false;render();$('preview-title').focus();message(t('prepared'));
}
async function sendPending(){
  const original=pending;if(!original||!current()||original.journal!==journalIdentity||!equal(original.command.scope,snapshot.scope)||invalidRecovery)throw Error(t('fresh'));
  const started=epoch;await verifyJournal();
  if(started!==epoch||!current()||original!==pending)throw Error(t('fresh'));
  // Keep the same immutable command across network loss, reload and every retry.
  snapshot=null;preview=null;render();
  try{
    const response=await api('/budget/operate',original.command),result=checkedRecord(response,original.command.scope);
    if(typeof result.replayed!=='boolean')throw Error(t('invalid'));
    removePending();acceptSnapshot(result,original.command.scope);message(t(result.replayed?'replayed':'recorded'));
  }catch(error){
    if(started===epoch&&[409,422].includes(error.httpStatus))storePending({...original,state:'rejected'});
    throw error;
  }
}
$('login-form').addEventListener('submit',event=>{event.preventDefault();if(busy)return;
  accessToken=$('token').value.trim();$('token').value='';epoch++;snapshot=null;preview=null;journalIdentity='';
  guarded(async()=>{const status=await api('/status');if(status.valid!==true||typeof status.identity!=='string'||!/^urn:agialpha:ed25519:[0-9a-f]{64}$/.test(status.identity))throw Error(t('invalid'));
    journalIdentity=status.identity;
    if(pending){$('owner').value=pending.command.scope.owner;$('chain-id').value=String(pending.command.scope.chain_id);$('asset-token').value=pending.command.scope.token;}
    message(t(pending?'restored':'connected'));});
});
$('disconnect').addEventListener('click',disconnect);
$('scope-form').addEventListener('submit',event=>{event.preventDefault();guarded(inspect);});
for(const id of ['owner','chain-id','asset-token'])$(id).addEventListener('input',invalidate);
$('operation-form').addEventListener('input',()=>{preview=null;$('confirm-ack').checked=false;render();});
$('action').addEventListener('change',()=>{preview=null;$('confirm-ack').checked=false;
  if(['release','commit'].includes($('action').value))$('amount').value='0';
  if($('action').value==='reserve')$('reservation-id').value=crypto.randomUUID();render();});
$('operation-form').addEventListener('submit',event=>{event.preventDefault();try{prepare();}catch(error){message(error.message,true);}});
for(const id of ['confirm-ack','retry-ack','dismiss-ack','invalid-ack'])$(id).addEventListener('change',render);
$('cancel-preview').addEventListener('click',()=>{preview=null;$('confirm-ack').checked=false;render();});
$('confirm').addEventListener('click',()=>guarded(async()=>{
  if(!$('confirm-ack').checked||!preview||!current()||pending||invalidRecovery)throw Error(t('confirm'));
  storePending(JSON.parse(JSON.stringify(preview)));await sendPending();
}));
$('retry').addEventListener('click',()=>guarded(async()=>{if(!$('retry-ack').checked)throw Error(t('confirm'));await sendPending();}));
$('dismiss').addEventListener('click',()=>{try{if(!$('dismiss-ack').checked||pending?.state!=='rejected'||!current()||pending.journal!==journalIdentity)throw Error(t('fresh'));
  removePending();invalidate();message(t('cleared'));}catch(error){message(error.message,true);}render();});
$('clear-invalid').addEventListener('click',()=>{try{if(!$('invalid-ack').checked)throw Error(t('confirm'));removePending();invalidate();message(t('cleared'));}catch(error){message(error.message,true);}render();});
$('export-pending').addEventListener('click',()=>{if(!pending)return;const url=URL.createObjectURL(new Blob([pretty(validateRecovery(pending))],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='native-planning-pending.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('language').addEventListener('change',()=>{document.documentElement.lang=lang();document.title=lang()==='fr'?'Réservations de planification · Opérateur local':'Planning reservations · Local operator';
  for(const node of document.querySelectorAll('[data-i18n]'))node.textContent=(lang()==='fr'?french:english)[node.dataset.i18n];
  if(messageKey)message(t(messageKey),messageError);render();});
window.addEventListener('pagehide',()=>{accessToken='';epoch++;for(const request of requests)request.abort();});
window.addEventListener('pageshow',event=>{if(event.persisted)disconnect();});
message(t(invalidRecovery?'invalid':pending?'restored':'ready'),invalidRecovery);render();

// Never expose an active credential form before its submit handler is installed.
$('token').disabled=false;$('connect').disabled=false;$('initializing').hidden=true;
