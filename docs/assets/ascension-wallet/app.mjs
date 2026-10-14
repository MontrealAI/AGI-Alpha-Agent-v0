// SPDX-License-Identifier: Apache-2.0
import {ACTIONS, CONTRACTS, uint, tokens, curve, parseFields, isRecovery} from './protocol.mjs';
import {MarkClient, json, unresolved, availableProfiles, selectBuildProfile} from './client.mjs';
import {RecoveryStore, JOURNAL_KEY} from './recovery.mjs';
const $ = id => document.getElementById(id);
let language = 'en', client = null, busy = false, snapshot = null, observedEpoch = -1;
let recovery = null, storedJournal = null, storageError = null;
function syncJournal() {
  if(storageError) throw Error(storageError);
  const saved=recovery.read(), raw=JSON.stringify(saved);
  if(raw!==storedJournal) {
    if(saved) client.restore(saved);
    else if(unresolved(client.pending)) throw Error('The outstanding journal was removed. Export it and reconcile before continuing.');
    storedJournal=raw; client.cancelPreview();
  }
}
async function journalAction(fn) {
  if(!recovery) throw Error('Recovery storage is unavailable; signing is disabled.');
  return recovery.exclusive(async()=>{syncJournal(); return fn();});
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
  $('deployment-choice').disabled=busy || unresolved(client?.pending);
  for (const el of $('action-fields').querySelectorAll('input,select,textarea')) el.disabled = busy;
  $('account').textContent = client?.account ? `Chain ${client.chainId} · ${client.account}` : text('No connected account. Select the deployment network in your wallet.','Aucun compte connecté. Sélectionnez le réseau du déploiement dans votre portefeuille.');
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
    if(client.chainId!==1) { $('transaction-link').textContent=`${client.pending.status} · chain ${client.chainId} · ${receiptHash}`; return; }
    const a = document.createElement('a'); a.href=`https://etherscan.io/tx/${receiptHash}`;
    a.textContent=`${client.pending.status} · ${receiptHash}`; a.rel='noopener noreferrer'; a.target='_blank';
    $('transaction-link').append(a);
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
function actionFields() {
  changed();
  const action = ACTIONS[$('action').value];
  $('action-note').textContent = action.note;
  $('action-policy').textContent = action.risk === 'new' && (!client || client.stage==='archive')
    ? text('New exposure is blocked for this archived profile. Zero allowance or future-availability revocation is available where applicable.','Les nouveaux engagements sont bloqués. La révocation à zéro d’une autorisation ou disponibilité reste possible.')
    : text('Real wallet action, subject to current contract conditions. It may spend ETH and can change or settle existing obligations.','Action réelle soumise aux règles actuelles du contrat. Elle consomme des frais ETH et peut modifier ou régler une obligation.');
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
$('wallet-choice').addEventListener('change',()=>run(async()=>{
  const item=providers[Number($('wallet-choice').value)];
  if ($('wallet-choice').value===''||!item) { client?.disconnect(); return; }
  client.select(item.provider); snapshot=null; $('snapshot').textContent='—'; $('quote-output').textContent='—'; changed();
  status(text('Wallet selected. Inspection requests no account permissions; Connect requests the selected account.','Portefeuille sélectionné. La consultation ne demande aucune permission de compte.'));
}));
$('connect').addEventListener('click',()=>run(async()=>{ await client.connect(); status(text('Account connected. No transaction was signed.','Compte connecté. Aucune transaction signée.')); }));
$('switch').addEventListener('click',()=>run(async()=>{ await client.switchMainnet(); status(text('Reconnect after selecting the deployment network.','Reconnectez-vous après la sélection du réseau du déploiement.')); }));
$('disconnect').addEventListener('click',()=>run(async()=>{ client.disconnect(); $('wallet-choice').value=''; snapshot=null; status(text('This page is disconnected. Wallet permissions can be revoked in the wallet.','Page déconnectée. Révoquez les permissions dans le portefeuille.')); }));
$('inspect').addEventListener('click',()=>run(async()=>{
  changed(); snapshot=null; $('snapshot').textContent='—'; $('quote-output').textContent='—'; $('snapshot-summary').textContent=text('No fresh observation yet.','Aucune observation actualisée.'); status(text('Verifying the pinned bytecode and bindings…','Vérification du bytecode et des liaisons…'));
  const seed=$('seed-id').value ? uint($('seed-id').value).toString() : null;
  const job=$('job-id').value ? uint($('job-id').value).toString() : null;
  const observation=await client.inspect(seed,job); snapshot={...observation,selectedSeed:seed}; $('snapshot').textContent=json(snapshot);
  const phase=snapshot.campaign ? ['None / Aucune','Funding / Financement','Bloomed / Engagée','Closed / Fermée'][Number(snapshot.campaign.phase)] : null;
  $('snapshot-summary').textContent=`${text('Observed block','Bloc observé')} ${BigInt(snapshot.verification.blockNumber)} · ${text('Nova-Seeds created','Nova-Seeds créés')}: ${snapshot.nextSeedId}${phase?` · ${phase} · ${tokens(snapshot.campaign.reserve)} $AGIALPHA`:''} · ${client.stage==='archive'?text('New funding not commissioned','Nouveau financement non autorisé'):client.stage}`;
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
  const args=parseFields(id,values,client.contracts); const preview=await client.prepare(id,values);
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
  await journalAction(async()=>{
    if(unresolved(client.pending)) throw Error('Reconcile the existing journal before importing another.');
    const checked=new MarkClient(client.profile); checked.restore(value);
    // Imported statuses are not evidence. Recheck the latest on-chain outcome.
    if(checked.pending) {
      checked.pending.status='submission-unknown';
      checked.pending.effectVerified=false;
      delete checked.pending.effectBlockHash;
    }
    recovery.write(checked.journal()); client.restore(checked.journal()); storedJournal=JSON.stringify(checked.journal());
    changed(); status(text('Journal imported. Reconcile a transaction hash before signing again.','Journal importé. Réconciliez une empreinte avant toute nouvelle signature.'));
  });
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
  $('language').textContent=language==='en'?'Français':'English'; deploymentLabel(); refresh();
});
function deploymentLabel() {
  if(!client) return;
  $('deployment-status').textContent=`${client.profile.profile} · chain ${client.chainId} · ${client.stage}`;
  $('deployment-heading').textContent=`α-AGI MARK · ${client.chainId===1?'Ethereum Mainnet':text('Local test network','Réseau local de test')} · chain ${client.chainId}`;
  $('archive-boundary').hidden=client.stage!=='archive';
  $('selected-boundary').hidden=client.stage==='archive';
  $('selected-boundary').textContent=client.stage==='local'
    ? text('Disposable local deployment. These transactions and accounts are test evidence, not Mainnet activity.','Déploiement local jetable. Ces transactions et comptes sont des preuves de test, pas une activité Mainnet.')
    : text('Source-reviewed deployment selection. Each action still requires current on-chain eligibility, qualification and explicit wallet confirmation. Canary actions are limited to the registered exact intents.','Déploiement sélectionné dans les sources vérifiées. Chaque action exige toujours admissibilité, qualification et confirmation explicite. Le canari est limité aux intentions exactes enregistrées.');
  for(const option of $('action').options) option.textContent=`${client.stage==='archive' && ACTIONS[option.value].risk==='new'?'[Commissioning pending] ':''}${ACTIONS[option.value].label}`;
}
$('deployment-choice').addEventListener('change',()=>run(async()=>{
  if(unresolved(client?.pending)) throw Error('Reconcile the outstanding transaction before changing deployment.');
  const target=new URL(window.location.href); target.search=''; target.searchParams.set('profile',$('deployment-choice').value);
  client?.disconnect(); window.location.assign(target.href);
}));
for(const [id,a] of Object.entries(ACTIONS)) {
  const option=document.createElement('option'); option.value=id; option.textContent=`${a.risk==='new'?'[Commissioning pending] ':''}${a.label}`; $('action').append(option);
}
$('action').value='sell'; actionFields();
window.addEventListener('beforeunload',event=>{if(client?.history.length){event.preventDefault();event.returnValue='';}});
try {
  const response=await fetch(new URL('./profile.json',import.meta.url),{cache:'no-store',redirect:'error'});
  if(!response.ok) throw Error('The deployment profile is missing. Build the wallet assets before serving; wallet actions remain disabled.');
  const defaultProfile=await response.json(), context=new URLSearchParams(window.location.search);
  const choices=availableProfiles(defaultProfile);
  for(const choice of choices) {const option=document.createElement('option');option.value=choice.id;option.textContent=`${choice.label} · ${choice.stage}`;$('deployment-choice').append(option);}
  const selected=context.get('profile') || choices[0].id;
  client=new MarkClient(selectBuildProfile(selected,defaultProfile),refresh,journal=>{
    if(!recovery||storageError) throw Error(storageError||'Recovery storage is unavailable.');
    recovery.write(journal); storedJournal=JSON.stringify(journal);
  });
  $('deployment-choice').value=selected; deploymentLabel();
  for(const [name,value] of Object.entries(client.contracts)) {
    const p=document.createElement('p'); p.textContent=`${name}: ${value}`;
    if(client.chainId===1) {const a=document.createElement('a');a.href=`https://etherscan.io/address/${value}#code`;a.textContent=p.textContent;a.target='_blank';a.rel='noopener noreferrer';p.replaceChildren(a);}
    $('addresses').append(p);
  }
  if (context.has('seed') || context.has('job')) {
    if (context.get('profile') !== client.profileIdentity || context.get('chain') !== String(client.chainId))
      throw Error('The linked project belongs to a different deployment. Return to Nova Studio and select the matching profile. No wallet request was made.');
    for (const [key,id] of [['seed','seed-id'],['job','job-id']]) {
      if (!context.has(key)) continue;
      const value=uint(context.get(key));
      if (!value) throw Error('A linked seed or job identifier must be positive.');
      $(id).value=value.toString();
    }
    actionFields();
    status(text('Project identifiers loaded. Select a wallet and inspect to verify current state; the link grants no signing authority.','Identifiants chargés. Sélectionnez un portefeuille et consultez l’état actuel; le lien ne donne aucune autorisation de signature.'));
  }
  try { recovery=new RecoveryStore(window.localStorage,navigator.locks); syncJournal(); }
  catch(error) { storageError=`Recovery unavailable: ${error.message}`; }
  refresh(); discover(); if(storageError) status(storageError);
} catch(error) { status(error.message); }
