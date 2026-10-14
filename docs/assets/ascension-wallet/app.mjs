// SPDX-License-Identifier: Apache-2.0
import {ACTIONS, uint, tokens, curve, parseFields, isRecovery} from './protocol.mjs';
import {json, unresolved, availableProfiles, selectBuildProfile, canonicalProfile} from './client.mjs';
import {JOURNAL_KEY} from './recovery.mjs';
import {WalletSession, profileForJournal} from './session.mjs';
const $ = id => document.getElementById(id);
let language = 'en', client = null, busy = false, snapshot = null, observedEpoch = -1;
let session = null, storageError = null, defaultProfile = null, profiles = [];
function syncJournal() {
  if(storageError) throw Error(storageError);
  session?.sync();
}
async function journalAction(fn) {
  if(!session||storageError) throw Error(storageError||'Recovery storage is unavailable; signing is disabled.');
  return session.exclusive(fn);
}
const providers = [];
const text = (en, fr) => language === 'fr' ? fr : en;
function status(message) { $('status').textContent = String(message).slice(0,1800); }
function save(name, data) {
  const url = URL.createObjectURL(new Blob([json(data)+'\n'],{type:'application/json'}));
  const a = document.createElement('a'); a.href=url; a.download=name; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function refresh() {
  if (client && observedEpoch !== client.epoch) {
    observedEpoch = client.epoch; snapshot = null; $('ack').checked = false;
    $('snapshot').textContent = '—'; $('quote-output').textContent = '—';
    $('snapshot-summary').textContent = text('Wallet context changed. Inspect again for a fresh observation.', 'Contexte modifié. Effectuez une nouvelle consultation.');
  }
  const ready = !!client?.provider;
  for (const id of ['connect','switch','disconnect','inspect','prepare']) $(id).disabled = busy || !ready;
  for (const id of ['wallet-choice','action','discover']) $(id).disabled = busy;
  for (const el of $('action-fields').querySelectorAll('input,select,textarea')) el.disabled = busy;
  $('account').textContent = client?.account ? `Chain ${client.profile.chainId} · ${client.account}` : text('No connected account. Select the chosen deployment’s network in your wallet.','Aucun compte connecté. Sélectionnez le réseau du déploiement choisi dans votre portefeuille.');
  $('deployment-choice').disabled=busy||!client;
  if(client){$('deployment-choice').value=client.profileIdentity;profileView();}
  $('preview-panel').hidden = !client?.prepared;
  $('confirm').disabled = busy || !client?.prepared || !$('ack').checked;
  if(storageError) $('confirm').disabled=true;
  $('cancel').disabled = busy;
  $('export-state').disabled = !snapshot;
  $('quote-buy').disabled = busy || !snapshot?.campaign || !ready;
  $('quote-sell').disabled = busy || !snapshot?.campaign || !ready;
  $('receipt').disabled = busy || !(client?.pending?.hash||client?.pending?.candidateHash) || !ready;
  $('export-journal').disabled = !client?.history.length;
  $('reconcile').disabled = busy || !ready || !client?.pending || client.pending.status==='awaiting-wallet';
  $('import-journal').disabled = busy || unresolved(client?.pending);
  $('journal').textContent = client?.history.length ? json(client.history) : '—';
  $('transaction-link').replaceChildren();
  const receiptHash=client?.pending?.candidateHash||client?.pending?.hash;
  if (receiptHash) {
    const el=document.createElement(client.profile.chainId===1?'a':'span');
    if(client.profile.chainId===1){el.href=`https://etherscan.io/tx/${receiptHash}`;el.rel='noopener noreferrer';el.target='_blank';}
    el.textContent=`${client.pending.status} · ${receiptHash}`;$('transaction-link').append(el);
  }
}
async function run(fn) {
  if (busy) return;
  busy=true; refresh();
  try { await fn(); } catch (error) { status(error?.message || 'Operation failed.'); }
  finally { busy=false; refresh(); }
}
function changed() {
  client?.cancelPreview(); $('ack').checked=false; refresh();
}
function profileView() {
  const archive=client.stage==='archive',local=client.stage==='local';
  $('deployment-heading').textContent=`α-AGI MARK · ${client.stage.toUpperCase()} · chain ${client.profile.chainId}`;
  $('boundary-title').textContent=archive?text('Deployed does not mean commissioned','Déployé ne signifie pas mis en service'):local?text('Local rehearsal · test assets only','Répétition locale · actifs de test'):text('Build-qualified deployment · explicit authorization','Déploiement qualifié · autorisation explicite');
  $('boundary-copy').textContent=archive
    ?text('The October 11, 2026 contracts are immutable and predate newer settlement safeguards. This build blocks new funding, stake deposits, seed/campaign creation and new work commitments. Eligible recovery and completion of existing obligations use real wallet transactions. No checkbox bypasses commissioning.','Les contrats immuables du 11 octobre 2026 précèdent de nouvelles protections de règlement. Cette version bloque les nouveaux financements, dépôts, créations et engagements. Les récupérations admissibles et obligations existantes utilisent de vraies transactions. Aucune case ne remplace la mise en service.')
    :local?text('This separately built profile uses disposable local contracts and test assets. It is not a Mainnet qualification. Every send still requires an explicit transaction preview and wallet confirmation.','Ce profil distinct utilise des contrats locaux jetables et des actifs de test. Il ne qualifie pas Mainnet. Chaque envoi exige un devis explicite et une confirmation du portefeuille.')
    :text('This profile is pinned in this release with exact source, code and authorization evidence. Each action rechecks its permitted scope and current deployment state. A canary authorizes only its bounded rehearsal; it is not public activation.','Ce profil est inscrit dans cette version avec ses sources, son code et ses preuves d’autorisation exacts. Chaque action revérifie son périmètre et l’état actuel. Un essai limité n’autorise pas l’activation publique.');
  $('switch').textContent=client.profile.chainId===1?text('Switch to Mainnet','Passer à Mainnet'):text('Switch to selected network','Passer au réseau choisi');
  for(const option of $('action').options){const a=ACTIONS[option.value];const restricted=a.risk==='new'&&(!client.profile.newExposureEnabled||(client.profile.actions&&!client.profile.actions.includes(option.value)));option.textContent=`${restricted?text('[Restricted] ','[Restreint] '):''}${a.label}`;}
  const action=ACTIONS[$('action').value];
  $('action-policy').textContent=action?.risk==='new'&&!client.profile.newExposureEnabled
    ?text('New exposure is blocked by the selected profile. Zero allowance or future-availability revocation remains available where applicable.','Les nouveaux engagements sont bloqués par le profil choisi. La révocation à zéro d’une autorisation ou disponibilité reste possible.')
    :text('A real wallet action must satisfy this profile’s current scope and contract conditions. Review token consequences and separate network fees.','Une action réelle doit respecter le périmètre du profil et les conditions des contrats. Examinez ses conséquences et les frais réseau distincts.');
  $('studio-link').href=`../../ascension/mainnet/?profile=${encodeURIComponent(client.profileIdentity)}&chain=${client.profile.chainId}${$('seed-id').value?`&seed=${encodeURIComponent($('seed-id').value)}`:''}${$('job-id').value?`&job=${encodeURIComponent($('job-id').value)}`:''}`;
}
function addressesView() {
  $('addresses').replaceChildren();
  for(const [name,value] of Object.entries(client.contracts)){
    const p=document.createElement('p'),el=document.createElement(client.profile.chainId===1?'a':'span');
    if(client.profile.chainId===1){el.href=`https://etherscan.io/address/${value}#code`;el.target='_blank';el.rel='noopener noreferrer';}
    el.textContent=`${name}: ${value}`;p.append(el);$('addresses').append(p);
  }
}
function actionFields() {
  changed();
  const action = ACTIONS[$('action').value];
  $('action-note').textContent = action.note;
  $('action-fields').replaceChildren();
  for (const f of action.fields) {
    const label=document.createElement('label'); label.textContent=f.label;
    let input;
    if (['boolean','spender','role'].includes(f.kind)) {
      input=document.createElement('select');
      const choices=f.kind==='boolean'?['false','true']:f.kind==='spender'?['Mark','Jobs','Oracle']:['0','1','2'];
      for (const value of choices) { const option=document.createElement('option'); option.value=value; option.textContent=value; input.append(option); }
    } else {
      input=document.createElement(['spec','proof','committee'].includes(f.kind)?'textarea':'input');
      if (f.kind==='integer'||f.kind==='tokens') input.inputMode=f.kind==='tokens'?'decimal':'numeric';
      input.autocomplete='off'; input.spellcheck=false;
      input.maxLength=['spec','proof','committee'].includes(f.kind)?16000:1024;
      if (f.key==='id') input.value=$('seed-id').value;
      if (f.key==='job') input.value=$('job-id').value;
      if (f.kind==='spec') input.placeholder='{"goal":"…","successMetric":"…","bounty":"1000000000000000000","duration":86400,"priceWeight":6000}';
      if (f.kind==='proof') input.placeholder='["0x…"] (or [] for a one-leaf plan)';
      if (f.kind==='committee') input.placeholder='["0x…","0x…","0x…"]';
    }
    input.id=`field-${f.key}`; input.required=true; input.addEventListener('input',changed); input.addEventListener('change',changed);
    label.append(input); $('action-fields').append(label);
  }
}
function addProvider(provider,name) {
  if (!provider || typeof provider.request!=='function' || providers.some(x=>x.provider===provider) || providers.length>=20) return;
  const index=providers.push({provider,name:String(name||'Browser wallet').slice(0,80)})-1;
  const option=document.createElement('option'); option.value=String(index); option.textContent=providers[index].name;
  $('wallet-choice').append(option);
}
function discover() {
  window.dispatchEvent(new Event('eip6963:requestProvider'));
  if (window.ethereum) addProvider(window.ethereum,'Browser wallet (legacy provider)');
  status(text('Choose a listed wallet. If none appears, open this page in a compatible wallet browser or install an injected wallet.','Choisissez un portefeuille. Sinon, ouvrez cette page dans le navigateur d’un portefeuille compatible.'));
}
window.addEventListener('eip6963:announceProvider', event => {
  try { addProvider(event.detail?.provider,event.detail?.info?.name); } catch { /* Untrusted extension metadata is ignored. */ }
});
$('discover').addEventListener('click',discover);
$('deployment-choice').addEventListener('change',()=>{const selectedId=$('deployment-choice').value;return run(async()=>{
  if(selectedId===client.profileIdentity)return;
  client=await session.selectProfile(selectBuildProfile(selectedId,defaultProfile));observedEpoch=-1;snapshot=null;
  client.disconnect();$('wallet-choice').value='';$('seed-id').value='';$('job-id').value='';
  addressesView();actionFields();
  status(text('Registered deployment selected. Choose and reconnect your wallet; no account or signature request was sent.','Déploiement inscrit choisi. Choisissez et reconnectez votre portefeuille; aucune demande de compte ou signature envoyée.'));
});});
for(const id of ['seed-id','job-id'])$(id).addEventListener('input',changed);
$('wallet-choice').addEventListener('change',()=>run(async()=>{
  const item=providers[Number($('wallet-choice').value)];
  if ($('wallet-choice').value===''||!item) { client?.disconnect(); return; }
  client.select(item.provider); snapshot=null; $('snapshot').textContent='—'; $('quote-output').textContent='—'; changed();
  status(text('Wallet selected. Inspection requests no account permissions; Connect requests the selected account.','Portefeuille sélectionné. La consultation ne demande aucune permission de compte.'));
}));
$('connect').addEventListener('click',()=>run(async()=>{ await client.connect(); status(text('Account connected. No transaction was signed.','Compte connecté. Aucune transaction signée.')); }));
$('switch').addEventListener('click',()=>run(async()=>{ await client.switchMainnet(); status(text('Reconnect after selecting this deployment’s network.','Reconnectez-vous après la sélection du réseau de ce déploiement.')); }));
$('disconnect').addEventListener('click',()=>run(async()=>{ client.disconnect(); $('wallet-choice').value=''; snapshot=null; status(text('This page is disconnected. Wallet permissions can be revoked in the wallet.','Page déconnectée. Révoquez les permissions dans le portefeuille.')); }));
$('inspect').addEventListener('click',()=>run(async()=>{
  changed(); snapshot=null; $('snapshot').textContent='—'; $('quote-output').textContent='—'; $('snapshot-summary').textContent=text('No fresh observation yet.','Aucune observation actualisée.'); status(text('Verifying the pinned bytecode and bindings…','Vérification du bytecode et des liaisons…'));
  const seed=$('seed-id').value ? uint($('seed-id').value).toString() : null;
  const job=$('job-id').value ? uint($('job-id').value).toString() : null;
  const observation=await client.inspect(seed,job); snapshot={...observation,selectedSeed:seed}; $('snapshot').textContent=json(snapshot);
  const phase=snapshot.campaign ? ['None / Aucune','Funding / Financement','Bloomed / Engagée','Closed / Fermée'][Number(snapshot.campaign.phase)] : null;
  $('snapshot-summary').textContent=`${text('Observed block','Bloc observé')} ${BigInt(snapshot.verification.blockNumber)} · ${text('Nova-Seeds created','Nova-Seeds créés')}: ${snapshot.nextSeedId}${phase?` · ${phase} · ${tokens(snapshot.campaign.reserve)} $AGIALPHA`:''} · ${snapshot.verification.newExposureEnabled?text('Subject to the selected profile’s explicit scope','Soumis au périmètre explicite du profil choisi'):text('New funding not commissioned','Nouveau financement non autorisé')}`;
  status(text('Observation complete. Bytecode matching is not an independent audit or approval for public funding.','Observation terminée. La concordance du bytecode n’est ni un audit indépendant ni une autorisation de financement.'));
}));
for (const side of ['buy','sell']) $(`quote-${side}`).addEventListener('click',()=>run(async()=>{
  $('quote-output').textContent='—';
  const id=snapshot?.selectedSeed; if (!id) throw Error('Inspect a specific Nova-Seed first.');
  const fresh=await client.inspect(id), c=fresh.campaign, count=uint($('quote-count').value,32);
  if (!count || c.phase!==1n) throw Error('A positive lot count and a funding-phase campaign are required.');
  if (side==='sell'&&(count>c.supply||fresh.yourLots===null||count>fresh.yourLots)) throw Error('The connected wallet does not hold that many lots.');
  if (side==='buy'&&c.supply+count>c.maxLots) throw Error('Maximum campaign lots exceeded.');
  const supply=side==='buy'?c.supply:c.supply-count;
  const local=curve(supply,count,c.base,c.slope);
  const [onchain]=await client.call('Mark','quote',[String(supply),String(count),String(c.base),String(c.slope)],fresh.verification.blockNumber);
  if (onchain!==local) throw Error('Quote mismatch. No transaction prepared.');
  $('quote-output').textContent=`${tokens(local)} $AGIALPHA · ${text('observed block','bloc observé')} ${BigInt(fresh.verification.blockNumber)}. ${text('Quote only, not an executable guarantee. Set your explicit maximum cost or minimum return in the action form.','Devis indicatif. Définissez le coût maximal ou retour minimal dans le formulaire.')}`;
}));
$('action').addEventListener('change',actionFields);
$('prepare').addEventListener('click',()=>run(async()=>{
  $('ack').checked=false;
  const id=$('action').value, values=ACTIONS[id].fields.map(f=>$(`field-${f.key}`).value);
  // Surface the policy result before making any account or transaction request.
  const args=parseFields(id,values); const preview=await client.prepare(id,values);
  $('preview').textContent=json({...preview,method:ACTIONS[id].method,arguments:args,recovery:isRecovery(id,args)});
  status(text('Preview prepared. Read it, then explicitly confirm in your wallet.','Devis préparé. Examinez-le, puis confirmez dans votre portefeuille.'));
  $('preview-title').scrollIntoView({block:'start',behavior:'instant'});
}));
$('ack').addEventListener('change',refresh);
$('confirm').addEventListener('click',()=>run(async()=>{
  status(text('Rechecking state before opening your wallet. Do not retry while a signature is pending.','Nouvelle vérification avant signature. Ne réessayez pas pendant une demande en attente.'));
  const hash=await journalAction(()=>client.confirm($('ack').checked)); $('ack').checked=false;
  status(`${text('Submitted, not yet confirmed','Envoyée, pas encore confirmée')}: ${hash}`);
}));
$('cancel').addEventListener('click',()=>{changed(); status(text('Preview cancelled. Nothing was sent.','Devis annulé. Aucun envoi.'));});
$('receipt').addEventListener('click',()=>run(async()=>{ const result=await journalAction(()=>client.receipt(client.pending.candidateHash||client.pending.hash,!!client.pending.candidateHash)); status(`${result.status} · ${result.candidateHash||result.hash}`); }));
$('reconcile').addEventListener('click',()=>run(async()=>{
  const result=await journalAction(()=>client.receipt($('reconcile-hash').value.trim(),true));
  status(`${result.status} · ${result.candidateHash||result.hash||''}`);
}));
$('import-journal').addEventListener('change',()=>run(async()=>{
  const file=$('import-journal').files[0]; if(!file) return;
  if(file.size>1000000) throw Error('Journal exceeds 1 MB.');
  const value=JSON.parse(await file.text());
  await session.restore(value);
  changed();status(text('Journal imported. Reconcile every recorded broadcast before signing again.','Journal importé. Réconciliez chaque envoi enregistré avant toute nouvelle signature.'));
  $('import-journal').value='';
}));
$('export-state').addEventListener('click',()=>save('mark-mainnet-observation.json',snapshot));
$('export-journal').addEventListener('click',()=>save('mark-mainnet-transaction-journal.json',client.journal()));
window.addEventListener('storage',event=>{
  if(event.key===JOURNAL_KEY || event.key===null) {
    client?.cancelPreview();
    if(!busy) try {syncJournal();refresh();} catch(error) {storageError=error.message;status(storageError);refresh();}
  }
});
$('language').addEventListener('click',()=>{
  language=language==='en'?'fr':'en'; document.documentElement.lang=language;
  for(const el of document.querySelectorAll('[data-en]')) el.textContent=el.dataset[language];
  $('language').textContent=language==='en'?'Français':'English'; refresh();
});
for(const [id,a] of Object.entries(ACTIONS)) {
  const option=document.createElement('option'); option.value=id; option.textContent=`${a.risk==='new'?'[Commissioning pending] ':''}${a.label}`; $('action').append(option);
}
$('action').value='sell'; actionFields();
window.addEventListener('beforeunload',event=>{if(client?.history.length){event.preventDefault();event.returnValue='';}});
try {
  const response=await fetch(new URL('./profile.json',import.meta.url),{cache:'no-store',redirect:'error'});
  if(!response.ok) throw Error('The deployment profile is missing. Build the wallet assets before serving; wallet actions remain disabled.');
  defaultProfile=await response.json();profiles=availableProfiles(defaultProfile);
  $('deployment-choice').replaceChildren();for(const choice of profiles){const option=document.createElement('option');option.value=choice.id;option.textContent=`${choice.stage.toUpperCase()} · ${choice.label} · chain ${choice.profile.chainId}`;$('deployment-choice').append(option);}
  const storage={getItem:key=>{try{return window.localStorage.getItem(key);}catch{storageError='Browser storage unavailable; signing disabled.';return null;}},
    setItem:(key,value)=>{if(storageError)throw Error(storageError);window.localStorage.setItem(key,value);}};
  const context=new URLSearchParams(location.search),requested=context.get('profile');
  const requestedChoices=requested?profiles.filter(choice=>choice.id===requested||choice.profile.profile===requested):[];
  const requestedChoice=requestedChoices.length===1?requestedChoices[0]:null;
  const journalProfile=profileForJournal(defaultProfile,storage);
  const savedChoice=storage.getItem(JOURNAL_KEY)?profiles.find(choice=>canonicalProfile(choice.profile)===canonicalProfile(journalProfile)):null;
  const selected=savedChoice||requestedChoice||profiles[0];
  session=new WalletSession(selected.profile,storage,navigator.locks,refresh);client=session.client;
  const contextMatches=requestedChoice?.id===client.profileIdentity&&(!context.has('chain')||context.get('chain')===String(client.profile.chainId));
  if(contextMatches)for(const [parameter,input] of [['seed','seed-id'],['job','job-id']]){
    const value=context.get(parameter);if(value&&/^[1-9][0-9]{0,77}$/.test(value))try{$(input).value=uint(value).toString();}catch{/* Invalid context remains empty. */}
  }
  addressesView();actionFields();refresh();discover();
  if(requested&&!contextMatches)status(text('Link context was not applied. Select its exact registered deployment; the saved journal keeps its original profile.','Le contexte du lien n’a pas été appliqué. Choisissez son déploiement inscrit exact; le journal garde son profil original.'));
  if(storageError)status(storageError);
} catch(error) { status(error.message); }
