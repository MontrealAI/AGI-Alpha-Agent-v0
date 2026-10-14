// SPDX-License-Identifier: Apache-2.0
import { WalletSession, discoverWallets, profileForJournal } from '../ascension-wallet/session.mjs';
import { JOURNAL_KEY } from '../ascension-wallet/recovery.mjs';
import { ACTIONS, tokens, curve, uint } from '../ascension-wallet/protocol.mjs';
import { json, unresolved, availableProfiles, selectBuildProfile } from '../ascension-wallet/client.mjs';
import { canonicalJSON, openSeed } from '../ascension/crypto.mjs';
import { compilePlan, jobFromEditor } from './plan.mjs';
import { fileBytes, hashBytes, objectHash, strictJSON, profileIdentity, deploymentIdentityStatus } from './package.mjs';
import { PinataStorage, metadataFor, verifyPublication } from './storage.mjs';
import { NovaWorkflow } from './workflow.mjs';
const $ = id => document.getElementById(id);
let language='en', busy=false, session=null, flow=null, compiled=null, legacyGenome=null, identity=null, resultHash=null;
let epoch=-1, storageFault=null, stopDiscovery=null, nativeResult=null;
let defaultProfile=null, profiles=[];
const wallets=[];
const text=(en,fr)=>language==='fr'?fr:en;
function status(message,error=false) { $('status').textContent=String(message).slice(0,1600); $('status').classList.toggle('error',error); }
function download(name,data,raw=false) {
  const value=raw?data:json(data)+'\n', blob=new Blob([value],{type:'application/json'}), url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function go(step) {
  for(const el of document.querySelectorAll('.step')) el.hidden=el.id!==`step-${step}`;
  for(const el of document.querySelectorAll('[data-step]')) {
    if(el.dataset.step===step) el.setAttribute('aria-current','step');else el.removeAttribute('aria-current');
  }
  $('workspace').focus({preventScroll:true});$('workspace').scrollIntoView({block:'start'});
}
function translate() {
  for(const el of document.querySelectorAll('[data-fr]')) {el.dataset.en??=el.textContent;el.textContent=el.dataset[language];}
  document.documentElement.lang=language;$('language').textContent=language==='en'?'Français':'English';render();
}
function field(label,key,value,kind='input') {
  const el=document.createElement('label');el.textContent=label;
  const input=document.createElement(kind); input.dataset.field=key;input.value=value;input.autocomplete='off';
  if(kind==='textarea'){input.rows=2;input.maxLength=512;}else input.inputMode=key==='bounty'?'decimal':'numeric';
  el.append(input);return el;
}
function addJob(spec={goal:'',successMetric:'',bounty:'100000000000000000000',duration:86400,priceWeight:6000}) {
  if($('jobs').children.length>=128) throw Error('At most 128 jobs.');
  const box=document.createElement('fieldset');box.className='job-editor';
  const legend=document.createElement('legend');legend.textContent=`Job / Travail ${$('jobs').children.length+1}`;box.append(legend);
  box.append(field('Goal / Objectif','goal',spec.goal,'textarea'),field('Acceptance criteria / Critères de réussite','successMetric',spec.successMetric,'textarea'));
  const grid=document.createElement('div');grid.className='field-grid';
  grid.append(field('Maximum bounty ($AGIALPHA) / Budget','bounty',tokens(spec.bounty)),field('Delivery (seconds) / Délai (secondes)','duration',String(spec.duration)),field('Price preference (0–10,000 bps) / Préférence prix','priceWeight',String(spec.priceWeight)));
  box.append(grid);const remove=document.createElement('button');remove.textContent='Remove job / Retirer';
  remove.addEventListener('click',()=>{box.remove();edited();});box.append(remove);$('jobs').append(box);
}
function jobs() {return [...$('jobs').children].map(box=>jobFromEditor(Object.fromEntries([...box.querySelectorAll('[data-field]')].map(el=>[el.dataset.field,el.value]))));}
function edited() {
  compiled=null;flow?.clearPreview();$('compile-summary').textContent=text('Edits apply to a new package. A previously sealed package stays frozen.','Les modifications créent un nouveau paquet. Le paquet déjà chiffré reste inchangé.');
  $('transaction-ack').checked=false;render();
}
function clearResult() {
  resultHash=null;nativeResult=null;$('result-digest').value='';$('result-hash').textContent='';flow?.clearPreview();
}
function resultView() {
  const native=$('result-format').value==='native-signed';
  for(const id of ['result-file','result-format','native-signer','onchain-job'])$(id).disabled=busy;
  $('native-delivery-controls').hidden=!native;
  $('verify-native-result').disabled=busy||!$('result-file').files.length;
  $('result-format-note').textContent=native
    ?text('The native path verifies the independently trusted signer and exact plan/job binding, then commits the original file bytes with Keccak-256. It never substitutes SHA-256.','Le format natif vérifie le signataire fiable et le lien exact au plan/travail, puis engage les octets originaux avec Keccak-256. SHA-256 ne s’y substitue jamais.')
    :text('The generic path commits exact bytes with SHA-256 and does not verify a native signature. Select native format for a signed alpha-agent export.','Le chemin générique engage les octets exacts avec SHA-256, sans vérifier une signature native. Sélectionnez le format natif pour un export signé alpha-agent.');
  $('result-digest').value=resultHash||'';
  $('result-hash').textContent=resultHash?`${native?'Keccak-256 · '+text('native signature and job verified','signature native et travail vérifiés'):'SHA-256 · '+text('generic file','fichier générique')} · ${resultHash}`:'';
  $('runtime-state').textContent=nativeResult
    ?text('No runtime connected. Signed delivery evidence was verified for the actual job. Signature verification does not replay the work or replace independent on-chain review.','Aucun environnement d’exécution connecté. La livraison signée a été vérifiée pour le travail réel. La signature ne rejoue pas le travail et ne remplace pas la revue indépendante sur la chaîne.')
    :text('No runtime connected. Export the work package and follow the native or SUCCESSOR Ω guide. Posting a job does not automatically start an agent.','Aucun environnement d’exécution connecté. Exportez le paquet et suivez le guide natif ou SUCCESSOR Ω. Publier un travail ne lance pas automatiquement un agent.');
}
function render() {
  if(!flow) return;
  const c=flow.client, pkg=flow.package, archived=c.profile.schema==='agialpha.mark-wallet-profile.v1';
  $('deployment-choice').disabled=busy;$('deployment-choice').value=c.profileIdentity;
  if(epoch!==c.epoch){epoch=c.epoch;flow.preview=null;flow.observation=null;identity=null;$('transaction-ack').checked=false;$('identity-summary').textContent='';}
  $('mode').textContent=c.profile.chainId!==1?text('LOCAL REHEARSAL · test assets only','RÉPÉTITION LOCALE · actifs de test'):
    c.profile.newExposureEnabled?`${c.profile.stage.toUpperCase()} · Ethereum Mainnet`:!archived?text('Qualified deployment · new exposure suspended','Déploiement qualifié · nouveaux engagements suspendus'):text('Local preparation · Mainnet archive: new exposure restricted','Préparation locale · Archive Mainnet : nouveaux engagements bloqués');
  $('deployment-policy').textContent=c.profile.newExposureEnabled?text('This build binds the selected qualified deployment. Review every wallet action.','Cette version lie le déploiement qualifié sélectionné. Examinez chaque action.'):
    !archived?text('New exposure is suspended by the current reviewed build. Permitted recovery remains available.','Les nouveaux engagements sont suspendus par la version examinée. Les récupérations permises restent accessibles.'):text('The October 11 contracts are immutable and predate settlement fixes. New minting, approvals and funding remain blocked. The complete workflow is exercised against a separately built local profile. Public activation requires an independently qualified deployment.','Les contrats immuables du 11 octobre précèdent les correctifs de règlement. La création, les autorisations et le financement restent bloqués. Le parcours complet est testé avec un profil local distinct. L’activation publique exige un déploiement qualifié indépendamment.');
  const legacyIdentity=pkg&&deploymentIdentityStatus(pkg,c.profile)==='legacy-addresses';
  $('package-state').textContent=pkg?(legacyIdentity?text('Recovered legacy package · new mint blocked','Ancien paquet récupéré · nouvelle création bloquée'):text('Encrypted · recovery tested','Chiffré · récupération vérifiée')):text('No package yet','Aucun paquet');
  $('job-count').textContent=String((pkg?.plan||compiled)?.jobs.length||0);
  $('budget').textContent=`${tokens((pkg?.plan||compiled)?.totalBounty||'0')} $AGIALPHA`;
  $('seed-summary').textContent=flow.seedId||'—';$('account').textContent=c.account||text('No connected account.','Aucun compte connecté.');
  const preview=!!c.prepared;
  $('preview-panel').hidden=!preview;
  $('confirm').disabled=busy||!preview||!$('transaction-ack').checked||!$('journal-consent').checked||!!storageFault;
  for(const id of ['seal-package','compile','publish-artifacts','restore-kit','route','mint','bloom']) $(id).disabled=busy;
  for(const id of ['export-kit','export-kit-again','export-capsule','export-plan']) $(id).disabled=!pkg||busy;
  if(nativeResult&&(nativeResult.jobId!==$('onchain-job').value||nativeResult.seedId!==flow.seedId))clearResult();
  resultView();
  $('journal').textContent=c.history.length?json(c.journal()):'—';
  const state=flow.observation;
  if(state){
    $('review-status').textContent=`${state.green?text('Green now','Vert actuellement'):text('Not green','Non approuvé')} · ${state.review.yes}/${state.review.quorum} yes · ${state.review.no} no · ${text('Round expires','Expiration')} ${new Date(Number(state.review.until)*1000).toISOString()}`;
    $('funding-status').textContent=`${['No campaign / Aucune campagne','Funding / Financement','Activated / Activée','Closed / Fermée'][Number(state.campaign.phase)]} · ${tokens(state.campaign.reserve)} $AGIALPHA ${text('reserve','réserve')} · ${tokens(state.campaign.target)} target · ${pkg?tokens(pkg.plan.totalBounty):'?'} ${text('total plan budget. A partial target does not fund all jobs.','budget total du plan. Un objectif partiel ne finance pas tous les travaux.')}`;
    $('nft-card').replaceChildren(); const h=document.createElement('h3');h.textContent=`Nova-Seed #${state.seedId}`;
    const p=document.createElement('p');p.textContent=`${text('Current owner','Propriétaire actuel')}: ${state.seedOwner}`;
    const code=document.createElement('p');code.textContent=`${flow.client.contracts.Seed} · chain ${flow.client.profile.chainId}`;
    const note=document.createElement('p');note.textContent=text('Commitments read back. Ownership does not transfer the capsule passphrase or an existing campaign’s business authority.','Empreintes vérifiées sur la chaîne. La propriété ne transmet ni la phrase secrète ni l’autorité d’une campagne existante.');
    $('nft-card').append(h,p,code,note);
  } else { $('nft-card').replaceChildren();$('review-status').textContent=text('Refresh chain state to check current review.','Actualisez la chaîne pour vérifier la revue.');$('funding-status').textContent=''; }
  $('mark-link').href=`../../ascension-protocol/mainnet/?profile=${encodeURIComponent(c.profileIdentity)}&chain=${c.profile.chainId}${flow.seedId?`&seed=${flow.seedId}`:''}${$('onchain-job').value?`&job=${encodeURIComponent($('onchain-job').value)}`:''}`;
}
async function run(fn) {
  if(busy)return;busy=true;render();
  try{await fn();}catch(error){status(text('Action needs attention: ','Action à vérifier : ')+(error?.message||'Operation failed.'),true);}
  finally{busy=false;render();}
}
function action(id,name,inputs=()=>({})) {$(id).addEventListener('click',()=>run(()=>prepare(name,inputs())));}
async function prepare(name,input) {
  if(!$('journal-consent').checked)throw Error('Enable the disclosed recovery journal before preparing a wallet action.');
  const p=await flow.prepare(name,input);$('transaction-ack').checked=false;
  $('preview-note').textContent=p.note;
  $('preview-summary').textContent=`${ACTIONS[p.actionId].label}. From ${p.transaction.from} to ${p.transaction.to}. ETH value: 0. Estimated gas: ${p.gas} units. Network gas is charged separately by your wallet. Preview expires in 60 seconds.`;
  $('preview').textContent=json(p);render();$('preview-title').focus();$('preview-panel').scrollIntoView({block:'start'});
  status(text('Preview ready. No transaction has been sent.','Devis prêt. Aucune transaction envoyée.'));
}
function packageView() {
  const pkg=flow.package;if(!pkg)return;
  $('commitments').textContent=json({innerCommitment:pkg.capsule.commitment,capsuleHash:pkg.capsuleHash,fileSHA256:pkg.capsuleByteHash,planRoot:pkg.plan.planRoot,evidenceHash:pkg.evidenceHash});
  $('public-fields').textContent=json({encryptedCapsule:{hash:pkg.capsuleHash,size:fileBytes(pkg.capsule).length},evidence:pkg.evidence,plan:{root:pkg.plan.planRoot,count:pkg.plan.jobs.length,totalBounty:pkg.plan.totalBounty},deployment:pkg.deployment,parent:pkg.parent});
  $('job-choice').replaceChildren();for(const job of pkg.plan.jobs){const op=document.createElement('option');op.value=String(job.index);op.textContent=`${job.index+1}. ${job.spec.goal}`;$('job-choice').append(op);}
  $('funding-target').value=tokens(pkg.plan.totalBounty);$('plan-details').textContent=json(pkg.plan);
}
for(const el of document.querySelectorAll('[data-step]'))el.addEventListener('click',()=>go(el.dataset.step));
for(const el of document.querySelectorAll('[data-next]'))el.addEventListener('click',()=>go(el.dataset.next));
$('language').addEventListener('click',()=>{language=language==='en'?'fr':'en';translate();});
$('deployment-choice').addEventListener('change',()=>{const selectedId=$('deployment-choice').value;return run(async()=>{
  const profile=selectBuildProfile(selectedId,defaultProfile);
  if(selectedId===flow.client.profileIdentity)return;
  if(flow.package)throw Error(text('Export the current recovery kit and clear this project before selecting another deployment. Its encrypted commitments cannot be relabeled.','Exportez le kit actuel et effacez ce projet avant de choisir un autre déploiement. Ses engagements chiffrés ne peuvent pas être réétiquetés.'));
  await session.selectProfile(profile);session.client.disconnect();flow=new NovaWorkflow(session,new PinataStorage());epoch=-1;
  $('wallet-choice').value='';$('existing-seed').value='';$('onchain-job').value='';$('parent').value='0';clearResult();
  status(text('Registered deployment selected. Select and connect your wallet again; no wallet request was sent.','Déploiement inscrit sélectionné. Choisissez et reconnectez votre portefeuille; aucune requête envoyée.'));
});});
$('add-job').addEventListener('click',()=>run(async()=>{addJob();edited();}));
$('step-project').addEventListener('input',edited);
$('example').addEventListener('click',()=>{
  if(flow?.package)return status('Export and clear the existing project before loading an example.',true);
  $('title').value='EXAMPLE · Public performance improvement';$('description').value='Illustrative project. Replace these assumptions with your own.';
  $('evidence').value='Use a public repository and reproducible benchmark. Compare the same workload and document hardware, baseline and results.';
  $('jobs').replaceChildren();addJob({goal:'Improve the throughput of a public open-source parser.',successMetric:'All upstream tests pass; a reproducible benchmark improves median throughput by at least 15% without higher error rates.',bounty:'100000000000000000000',duration:86400,priceWeight:6000});edited();
});
$('compile').addEventListener('click',()=>run(async()=>{compiled=compilePlan(jobs());$('plan-details').textContent=json(compiled);$('compile-summary').textContent=`${compiled.jobs.length} jobs · ${tokens(compiled.totalBounty)} $AGIALPHA · ${text('Exact plan compiled locally. Reviewers receive the contract-defined allocation from the gross price; gas is separate.','Plan exact compilé localement. La part des validateurs est prélevée sur le prix brut; les frais réseau sont distincts.')}`;status('Plan compiled. No wallet or network access.');}));
$('seal-package').addEventListener('click',()=>run(async()=>{
  if(flow.package)throw Error('The existing package is frozen. Export it, then clear this project to create an explicit new version.');
  if($('passphrase').value!==$('passphrase-again').value)throw Error('Passphrases do not match.');
  try{await flow.create({title:$('title').value,description:$('description').value,jobs:jobs(),evidence:$('evidence').value,parent:$('parent').value,legacyGenome},$('passphrase').value);}
  finally{$('passphrase').value='';$('passphrase-again').value='';}
  packageView();$('recovery-result').textContent=text('Encrypted and successfully reopened locally. Download the recovery kit before publication or minting.','Chiffré et rouvert avec succès. Téléchargez le kit avant publication ou création du NFT.');status('Exact package encrypted and recovery verified.');
}));
for(const id of ['export-kit','export-kit-again'])$(id).addEventListener('click',()=>run(async()=>{download('Nova-Seed-Recovery-Kit.json',await flow.kit());status(text('Recovery kit downloaded. Keep the passphrase separately.','Kit téléchargé. Gardez la phrase secrète séparément.'));}));
$('export-capsule').addEventListener('click',()=>download('nova-capsule.json',fileBytes(flow.package.capsule),true));
$('export-plan').addEventListener('click',()=>download('plan.json',fileBytes(flow.package.plan),true));
$('publish-artifacts').addEventListener('click',()=>run(async()=>{
  try{await flow.publish($('storage-token').value,$('public-consent').checked);$('publication-state').textContent=flow.publication.metadataURI;status('All three published artifacts were retrieved and their exact bytes verified. Export your updated kit.');}
  finally{$('storage-token').value='';}
}));
$('verify-publication').addEventListener('click',()=>run(async()=>{flow.publication=await verifyPublication(flow.package,flow.publication,flow.storage,{independent:true});status('Exact bytes verified through both configured gateways.');}));
$('import-publication').addEventListener('click',()=>run(async()=>{
  const metadata=metadataFor(flow.package,$('capsule-uri').value,$('evidence-uri').value);
  const p={schema:'agialpha.nova-studio.publication.v1',capsuleURI:$('capsule-uri').value,evidenceURI:$('evidence-uri').value,metadataURI:$('metadata-uri').value,metadataHash:await objectHash(metadata)};
  flow.publication=await verifyPublication(flow.package,p,flow.storage);$('publication-state').textContent=p.metadataURI;status('Existing artifacts match the exact package.');
}));
function discover(){stopDiscovery?.();stopDiscovery=discoverWallets(window,(provider,name)=>{
  if(wallets.some(w=>w.provider===provider))return;wallets.push({provider,name});const op=document.createElement('option');op.value=String(wallets.length-1);op.textContent=name;$('wallet-choice').append(op);
});}
$('discover').addEventListener('click',discover);
$('wallet-choice').addEventListener('change',()=>run(async()=>{const w=wallets[Number($('wallet-choice').value)];if($('wallet-choice').value===''||!w)session.client.disconnect();else session.client.select(w.provider);status('Wallet selected. Account access requires a separate click.');}));
$('connect').addEventListener('click',()=>run(async()=>{await session.client.connect();status('Wallet connected. No signature requested.');}));
$('switch-network').addEventListener('click',()=>run(()=>session.client.switchMainnet()));
$('disconnect').addEventListener('click',()=>run(async()=>{session.client.disconnect();$('wallet-choice').value='';}));
$('check-identity').addEventListener('click',()=>run(async()=>{identity=await flow.chain.identity();$('identity-details').textContent=json(identity);$('identity-summary').textContent=identity.eligible?'Eligible business / Entreprise admissible':`Waiting for owned registered ENS name and/or admission. Current admission operator: ${identity.governor}`;status('Identity read from the current deployment.');}));
$('admission-request').addEventListener('click',()=>run(async()=>{identity=await flow.chain.identity();download('nova-operator-request.json',{schema:'agialpha.nova-studio.operator-request.v1',deployment:profileIdentity(session.client.profile),requester:identity.who,operator:identity.governor,role:0,namespace:'alpha.agi.eth',observation:identity,request:'Provision an owned business subname through the genuine namespace process, then separately evaluate time-limited admission. This file grants neither.'});}));
action('register','register',()=>({label:$('ens-label').value}));action('mint','seal');action('open-review','openReview');
action('transfer-seed','transferSeed',()=>({to:$('seed-recipient').value,acknowledged:$('transfer-ack').checked}));
$('successor-seed').addEventListener('click',()=>run(async()=>{
  const state=await flow.inspect();
  if(!flow.package)throw Error('Recover the parent’s exact package before deriving a successor.');
  if(flow.client.account?.toLowerCase()!==state.seedOwner.toLowerCase())throw Error('Connect the current owner to create a successor.');
  const parent=state.seedId, inherited=flow.package.plan.jobs.map(j=>j.spec);
  download(`Nova-Seed-${parent}-Recovery-Kit.json`,await flow.kit());
  flow=new NovaWorkflow(session,new PinataStorage());compiled=null;legacyGenome=null;
  $('title').value=`Successor to Nova-Seed #${parent}`;$('description').value='';$('parent').value=parent;
  $('jobs').replaceChildren();for(const spec of inherited)addJob(spec);
  go('project');status('Parent exported unchanged. Edit and encrypt a new version; review and campaign authority are not inherited.');
}));
$('refresh-review').addEventListener('click',()=>run(()=>flow.inspect()));
$('review-reference').addEventListener('click',()=>run(async()=>{await flow.inspect();download('nova-review-reference.json',{schema:'agialpha.nova-studio.review-reference.v1',deployment:profileIdentity(session.client.profile),seedId:flow.seedId,metadataURI:flow.observation.metadataURI,genome:flow.observation.genome,round:flow.observation.review,guide:'Obtain authorized capsule access separately. Connect your own validator wallet and refresh current state. This reference is not an approval.'});}));
action('attest','attest',()=>({risk:$('risk').value,approved:$('review-decision').value,findings:$('review-findings').value,reviewed:$('review-ack').checked}));
$('export-review-evidence').addEventListener('click',()=>run(async()=>{
  if(!flow.reviewEvidence)throw Error('Prepare your attestation to bind its exact round and findings first.');
  download('nova-validator-evidence.json',fileBytes(flow.reviewEvidence),true);
}));
action('approve-validator','approveStake',()=>({spender:'Oracle',amount:$('stake-amount').value}));action('deposit-validator','validatorDeposit',()=>({amount:$('stake-amount').value}));action('withdraw-validator','validatorWithdraw',()=>({amount:$('stake-amount').value}));
action('availability','availability',()=>({business:$('availability-business').value,until:String(Math.floor(new Date($('availability-until').value+'Z').getTime()/1000)),capacity:$('capacity').value}));
action('revoke-availability','availability',()=>({business:$('availability-business').value,until:'0',capacity:'0'}));
action('open-campaign','open',()=>({base:$('curve-base').value,slope:$('curve-slope').value,maxLots:$('max-lots').value,target:$('funding-target').value,fundingHours:$('funding-hours').value,executionDays:$('execution-days').value}));
const buyInputs=()=>({count:$('lot-count').value,limit:$('max-cost').value});action('approve-funding','approveFunding',buyInputs);action('buy','buy',buyInputs);
$('quote').addEventListener('click',()=>run(async()=>{const s=await flow.inspect(),c=s.campaign,count=uint($('lot-count').value,32);if(c.phase!==1n||count===0n||c.supply+count>c.maxLots)throw Error('Inspect a funding campaign and valid lot count.');const q=curve(c.supply,count,c.base,c.slope);if((await flow.client.call('Mark','quote',[String(c.supply),String(count),String(c.base),String(c.slope)]))[0]!==q)throw Error('Quote mismatch.');$('quote-output').textContent=`${tokens(q)} $AGIALPHA · ${count} lots. Set your own maximum; approval and purchase remain separate.`;}));
action('bloom','bloom',()=>({irreversible:$('bloom-ack').checked}));
action('route','route',()=>({index:$('job-choice').value,auction:$('auction').value,reviewers:[1,2,3].map(i=>$(`reviewer-${i}`).value)}));
$('inspect-job').addEventListener('click',()=>run(async()=>{
  const s=await flow.chain.inspectJob(flow.seedId,$('onchain-job').value,flow.package);$('job-state').textContent=json(s.job);
  const state=Number(s.job.state),confirmed=s.job.settlementConfirmed===true;
  const labels=[text('Unknown','Inconnu'),text('Job posted; auction open','Travail publié; enchère ouverte'),text('Worker awarded','Exécutant sélectionné'),text('Result delivered; review pending','Résultat livré; revue en attente')];
  let label=labels[state];
  if(state>=4){
    const outcome=state===4?text('Settlement paid','Règlement payé'):state===5?text('Failure or slashing','Échec ou pénalité'):text('Refund','Remboursement');
    label=confirmed?`${outcome} · ${text('canonical finalized state verified','état canonique finalisé vérifié')}`
      :text('Terminal job state observed; settlement is pending canonical finality.','État terminal observé; le règlement attend la finalité canonique.');
  }
  status(`${label||text('Unknown','Inconnu')}. ${text('Runtime connection is not established by this state.','Cet état n’établit aucune connexion à un environnement d’exécution.')}`);
}));
$('work-package').addEventListener('click',()=>run(async()=>download('nova-runtime-work.json',await flow.workPackage($('onchain-job').value))));
action('bid','bid',()=>({jobId:$('onchain-job').value,price:$('bid-price').value,duration:$('bid-duration').value}));action('award','award',()=>({jobId:$('onchain-job').value}));
action('approve-worker','approveStake',()=>({spender:'Jobs',amount:$('worker-stake').value}));
action('deposit-worker','agentDeposit',()=>({amount:$('worker-stake').value}));
action('withdraw-worker','agentWithdraw',()=>({amount:$('worker-stake').value}));
async function readResult() {
  clearResult();const f=$('result-file').files[0];if(!f||f.size>2000000)throw Error('Use an exact result file no larger than 2 MB.');
  if($('result-format').value==='native-signed')status(text('Native file selected. Enter an independently trusted signer key and verify this delivery before submission.','Fichier natif choisi. Indiquez une clé de signataire fiable et vérifiez la livraison avant soumission.'));
  else resultHash=await hashBytes(await f.arrayBuffer());
  resultView();
}
$('result-file').addEventListener('change',()=>run(readResult));
$('result-format').addEventListener('change',()=>run(async()=>{clearResult();if($('result-file').files.length)await readResult();resultView();}));
$('native-signer').addEventListener('input',()=>{clearResult();resultView();});
$('onchain-job').addEventListener('input',()=>{clearResult();resultView();});
$('verify-native-result').addEventListener('click',()=>run(async()=>{
  clearResult();
  if($('result-format').value!=='native-signed')throw Error('Select the signed native delivery path explicitly.');
  const f=$('result-file').files[0];if(!f||f.size>2000000)throw Error('Use an exact native delivery file no larger than 2 MB.');
  const source=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await f.arrayBuffer());
  nativeResult=await flow.importNativeDelivery(source,{trustedPublicKey:$('native-signer').value,jobId:$('onchain-job').value});
  resultHash=nativeResult.resultHash;resultView();
  status(text('Native delivery verified. Exact Keccak-256 hash filled automatically; no runtime connection is claimed.','Livraison native vérifiée. Empreinte Keccak-256 exacte remplie automatiquement; aucune connexion d’exécution n’est revendiquée.'));
}));
action('submit-result','submit',()=>{
  const native=$('result-format').value==='native-signed';
  if(native&&(!nativeResult||nativeResult.resultHash!==resultHash||nativeResult.jobId!==$('onchain-job').value||nativeResult.seedId!==flow.seedId))throw Error('Verify the signed native delivery for this exact job before submission.');
  return {jobId:$('onchain-job').value,result:resultHash,uri:$('result-uri').value,native};
});
action('validate-result','validate',()=>({jobId:$('onchain-job').value,result:resultHash,approved:$('result-decision').value,findings:$('result-findings').value,reviewed:$('result-review-ack').checked}));
action('timeout-job','timeout',()=>({jobId:$('onchain-job').value}));
$('restore-kit').addEventListener('click',()=>run(async()=>{
  const f=$('kit-file').files[0];if(!f||f.size>2000000)throw Error('Choose a recovery kit up to 2 MB.');
  try{await flow.restore(await f.text(),$('restore-passphrase').value);}finally{$('restore-passphrase').value='';}
  packageView();$('existing-seed').value=flow.seedId||'';
  status(deploymentIdentityStatus(flow.package,flow.client.profile)==='legacy-addresses'
    ?text('Legacy package recovered unchanged. Its address-only deployment identity cannot authorize a new mint. Original recovery and read-only inspection remain available; reconcile imported transaction outcomes.','Ancien paquet récupéré sans modification. Son identité limitée aux adresses ne permet pas une nouvelle création. La récupération et la consultation restent accessibles; réconciliez les transactions importées.')
    :text('Package recovered locally. Imported transaction outcomes must be reconciled; nothing was signed.','Paquet récupéré localement. Réconciliez les transactions importées; aucune signature effectuée.'));
}));
$('convert-legacy').addEventListener('click',()=>run(async()=>{const f=$('legacy-file').files[0];if(!f||f.size>350000)throw Error('Choose an original sealed capsule up to 350 KB.');if(flow.package)throw Error('Export and clear the current package first.');try{legacyGenome=await openSeed(strictJSON(await f.text(),350000),$('restore-passphrase').value);}finally{$('restore-passphrase').value='';}if(legacyGenome.onchain_plan){$('jobs').replaceChildren();for(const j of legacyGenome.onchain_plan.jobs)addJob(j.spec);}go('project');status('Original capsule remains unchanged. Complete the project editor to seal a new executable version.');}));
$('open-seed').addEventListener('click',()=>run(async()=>{await flow.inspect($('existing-seed').value);go('mint');status('Existing seed inspected. Import matching artifacts to route its committed plan.');}));
$('open-receipt').addEventListener('click',()=>run(async()=>{const state=await flow.chain.openMintReceipt($('existing-receipt').value,flow.package);flow.seedId=state.seedId;flow.observation=state;go('mint');status('Canonical mint receipt and seed commitments verified.');}));
$('scan-seeds').addEventListener('click',()=>run(async()=>{if(!flow.client.account)throw Error('Connect the account to discover its seeds.');const r=await flow.chain.ownedSeeds(flow.client.account,$('scan-block').value);$('scan-block').value=r.nextBlock;$('owned-seeds').textContent=r.seeds.length?`Currently owned IDs: ${r.seeds.join(', ')}.`:'No currently owned seed found in this range.';$('owned-seeds').append(document.createTextNode(r.done?' Latest block reached.':' Continue with the next range.'));}));
async function reconcile(){const hash=$('reconcile-hash').value||flow.client.pending?.candidateHash||flow.client.pending?.hash;if(!hash)throw Error('Obtain the original or replacement hash from your wallet; do not resend.');const record=await flow.reconcile(hash);if(flow.jobIds.length)$('onchain-job').value=flow.jobIds.at(-1);status(`${record.status}. ${record.status==='finalized'?'Canonical receipt checked. Export the updated recovery kit.':'Keep this action unresolved until canonical finality is verified.'}`);}
$('reconcile').addEventListener('click',()=>run(reconcile));
$('export-journal').addEventListener('click',()=>download('mark-mainnet-transaction-journal.json',flow.client.journal()));
action('sell','sell',()=>({count:$('sell-count').value,limit:$('min-return').value}));action('collect','collect',()=>({jobId:$('onchain-job').value}));action('close-campaign','close');action('reclaim','reclaim');action('revoke-mark','revoke',()=>({spender:'Mark'}));
action('transfer-lots','transferLots',()=>({to:$('lot-recipient').value,count:$('transfer-lot-count').value}));
$('confirm').addEventListener('click',()=>run(async()=>{if(!$('journal-consent').checked)throw Error('Consent to the public recovery journal is required.');const hash=await flow.confirm($('transaction-ack').checked);$('transaction-ack').checked=false;$('reconcile-hash').value=hash;go('resume');status(`Submitted, not confirmed: ${hash}. Reconcile before another action.`);}));
$('cancel-preview').addEventListener('click',()=>{flow.clearPreview();render();});
$('transaction-ack').addEventListener('change',render);$('journal-consent').addEventListener('change',render);
$('clear-project').addEventListener('click',()=>run(async()=>{if(unresolved(flow.client.pending))throw Error('Resolve the outstanding transaction before clearing this project.');flow=new NovaWorkflow(session,new PinataStorage());compiled=null;legacyGenome=null;resultHash=null;for(const id of ['title','description','evidence','passphrase','passphrase-again','restore-passphrase','storage-token'])$(id).value='';$('jobs').replaceChildren();addJob();$('plan-details').textContent='—';$('commitments').textContent='—';$('public-fields').textContent='—';$('job-choice').replaceChildren();go('project');status('Project cleared from this page. Best-effort UI clearing is not guaranteed memory erasure.');}));
document.addEventListener('input',event=>{if(!['transaction-ack','journal-consent','reconcile-hash'].includes(event.target.id)&&flow?.client.prepared){flow.clearPreview();$('transaction-ack').checked=false;render();}});
window.addEventListener('storage',event=>{if(event.key===JOURNAL_KEY||event.key===null){flow?.clearPreview();if(!busy)try{session?.sync();render();}catch(error){storageFault=error.message;status(storageFault,true);}}});
window.addEventListener('beforeunload',event=>{if(flow?.package||unresolved(flow?.client.pending)){event.preventDefault();event.returnValue='';}});
addJob();
try {
  const response=await fetch(new URL('../ascension-wallet/profile.json',import.meta.url),{cache:'no-store',redirect:'error'});
  if(!response.ok)throw Error('Missing deployment profile. Build the site before opening Studio.');
  const storage={getItem:key=>{try{return window.localStorage.getItem(key);}catch{storageFault='Browser storage unavailable; signing disabled.';return null;}},
    setItem:(key,value)=>{if(storageFault||!$('journal-consent').checked)throw Error(storageFault||'Public journal consent is required.');window.localStorage.setItem(key,value);}};
  defaultProfile=await response.json();profiles=availableProfiles(defaultProfile);
  $('deployment-choice').replaceChildren();for(const item of profiles){const option=document.createElement('option');option.value=item.id;option.textContent=`${item.stage.toUpperCase()} · ${item.label} · chain ${item.profile.chainId}`;$('deployment-choice').append(option);}
  const context=new URLSearchParams(location.search),requested=context.get('profile');
  const matches=id=>profiles.filter(item=>item.id===id||item.profile.profile===id);
  const journalProfile=profileForJournal(defaultProfile,storage);
  const savedChoice=storage.getItem(JOURNAL_KEY)?profiles.find(item=>canonicalJSON(item.profile)===canonicalJSON(journalProfile)):null;
  const requestedChoices=requested?matches(requested):[];
  const requestedChoice=requestedChoices.length===1?requestedChoices[0]:null;
  const selected=savedChoice||requestedChoice||profiles[0];
  session=new WalletSession(selected.profile,storage,navigator.locks,render);flow=new NovaWorkflow(session,new PinataStorage());
  epoch=flow.client.epoch;render();
  status(text('Start locally, without connecting a wallet. Existing project? Open Resume & recover.','Commencez localement, sans portefeuille. Projet existant ? Ouvrez Reprendre et récupérer.'));
  if(requested){
    if(!requestedChoice||requestedChoice.id!==selected.id||(context.has('chain')&&context.get('chain')!==String(selected.profile.chainId)))
      status(text('Link context was not applied. Select its exact registered deployment; the saved journal keeps its original profile.','Le contexte du lien n’a pas été appliqué. Choisissez son déploiement inscrit exact; le journal garde son profil original.'),true);
    else for(const [parameter,input] of [['seed','existing-seed'],['job','onchain-job']]){const value=context.get(parameter);if(value&&/^[1-9][0-9]{0,77}$/.test(value))$(input).value=uint(value).toString();}
  }
  if(storageFault)status(storageFault,true);
}catch(error){status(error.message,true);}

$('export-result-review').addEventListener('click',()=>run(async()=>{if(!flow.resultReviewEvidence)throw Error('Prepare your result review first.');download('nova-result-review.json',flow.resultReviewEvidence);}));
