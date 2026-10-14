// SPDX-License-Identifier: Apache-2.0
import {MarkClient, json, unresolved, availableProfiles, selectBuildProfile} from '../ascension-wallet/client.mjs';
import {RecoveryStore, JOURNAL_KEY} from '../ascension-wallet/recovery.mjs';
import {ACTIONS, uint} from '../ascension-wallet/protocol.mjs';
import {compilePlan, toBaseUnits, formatTokens} from './plan.mjs';
import {preparePackage, verifyPackage, createRecoveryKit, restoreRecoveryKit, convertLegacyCapsule,
  isRecoveryVerified, clearRecoveryState, parseBoundedJSON, MAX_KIT_BYTES} from './package.mjs';
import {PinataStorage, publishPackage, importPublication} from './storage.mjs';
import {NovaWorkflow} from './workflow.mjs';

const $ = id => document.getElementById(id);
const text = (en, fr) => language === 'fr' ? fr : en;
const providers = [];
let language = 'en', step = 0, busy = false, client = null, workflow = null;
let recovery = null, storageError = null, storedJournal = null, observedEpoch = -1;
let plan = null, adapter = null, restoredPublication = null, parent = '0';
let nextJob = 0, discoveryCursor = null, profileError = null;
let defaultProfile = null, registeredProfiles = [];
const time = seconds => {
  const value = Number(seconds);
  return Number.isSafeInteger(value) && value > 0 ? new Date(value * 1000).toLocaleString(language === 'fr' ? 'fr-CA' : 'en-CA') : '—';
};
const cloneJSON = value => JSON.parse(json(value));
const pkg = () => workflow?.state.package || null;
const activePlan = () => pkg()?.plan || plan;
const amount = value => value === undefined || value === null ? '—' : `${formatTokens(value)} $AGIALPHA`;
const translations = {
  package:['Encrypted package recovered','Dossier chiffré récupéré'], publish:['Artifacts retrieved and verified','Artefacts relus et vérifiés'],
  identity:['Business eligible','Entreprise admissible'], mint:['NFT observed','NFT observé'], review:['Current independent approval','Approbation indépendante actuelle'],
  campaign:['Campaign observed','Campagne observée'], fund:['Funding target reached','Objectif de financement atteint'], activate:['Campaign activated','Campagne activée'],
  route:['Committed job posted','Travail engagé publié'], deliver:['Result delivered','Résultat livré'], settle:['Settlement observed','Règlement observé'],
};
const actionNames = {
  identity:['Register owned business name','Enregistrer le nom détenu'], mint:['Mint your Nova-Seed','Créer votre NFT Nova-Seed'],
  'request-review':['Open independent risk review','Ouvrir l’évaluation indépendante'], 'risk-approve':['Submit my risk attestation','Soumettre mon attestation'],
  campaign:['Open this seed’s funding campaign','Ouvrir la campagne de ce NFT'], approve:['Set the exact spending allowance','Définir l’autorisation de dépense exacte'],
  fund:['Purchase campaign funding lots','Acheter des lots de financement'], activate:['Activate campaign (bloom)','Activer la campagne (bloom)'],
  route:['Post the selected committed job','Publier le travail engagé sélectionné'], sell:['Redeem funding lots','Racheter les lots'],
  close:['Close the eligible campaign','Fermer la campagne admissible'], reclaim:['Claim proportional remaining capital','Réclamer la part du solde'],
  collect:['Return this job’s refund to MARK','Rapatrier le remboursement dans MARK'],
  transferSeed:['Transfer this Nova-Seed NFT','Transférer ce NFT Nova-Seed'],
  submit:['Submit this verified worker delivery','Soumettre cette livraison vérifiée'],
  award:['Process an ended auction','Traiter une enchère terminée'], timeout:['Process an expired job','Traiter un travail expiré'],
};
function status(message, error = false) {
  $('status').textContent = String(message).slice(0, 2200);
  $('status').classList.toggle('error', error);
}
function explainError(error) {
  let message = String(error?.message || error || 'Operation failed.').slice(0, 1800);
  // A provider may echo arbitrary data, including a credential. Render text only and redact known secret fields.
  for (const id of ['passphrase', 'passphrase-confirm', 'reopen-passphrase', 'legacy-passphrase', 'storage-token']) {
    const secret = $(id).value;
    if (secret) message = message.split(secret).join('[redacted]');
  }
  if (language !== 'fr') return message;
  const known = [
    [/New exposure is not commissioned|not commissioned for this archived/, 'Les nouveaux engagements restent bloqués sur le déploiement archivé. Utilisez un déploiement qualifié; la récupération existante reste disponible.'],
    [/Reconcile the outstanding|outstanding transaction|outstanding action/, 'Une transaction reste non résolue. Ouvrez « Récupérer et gérer » et vérifiez son résultat avant toute nouvelle demande.'],
    [/Wrong network/, 'Le portefeuille utilise un autre réseau. Choisissez explicitement le réseau du profil, puis reconnectez le compte.'],
    [/Connect your wallet|Choose a wallet|No compatible wallet/, 'Sélectionnez et connectez votre portefeuille dans « Identité et NFT ».'],
    [/Wallet or network changed|Account changed|Inputs changed|preview expired|Preview expired/i, 'Le contexte a changé ou l’aperçu a expiré. Actualisez les données et préparez un nouvel aperçu.'],
    [/New capsule passphrase|passphrase|decrypt|Decryption|operation-specific reason/i, 'La récupération locale a échoué. Vérifiez la phrase de capsule et le fichier exact. Votre phrase de portefeuille ne doit jamais être utilisée ici.'],
    [/quorum|risk approval is missing|round expired|seven-day round/, 'L’évaluation actuelle est absente, expirée ou encore en cours. Actualisez son état; les validateurs doivent agir eux-mêmes.'],
    [/Storage upload or retrieval/, 'La publication ou la lecture a échoué. Vérifiez votre accès Pinata, la disponibilité du fournisseur, CORS et la taille des fichiers.'],
    [/currently owned registered business|business ENS|not the current NFT owner/, 'Le compte doit être le propriétaire admissible avec son nom ENS d’entreprise actuellement détenu. Actualisez l’identité et contactez le responsable si nécessaire.'],
    [/Use a positive|Use a valid|Malformed|uint|whole number|decimal|Token amount|Each goal|Bounty must|Delivery duration|Price preference/, 'Vérifiez les valeurs saisies : montants exacts, limites des contrats et descriptions en UTF-8.'],
  ];
  const translated = known.find(([pattern]) => pattern.test(message));
  return translated ? translated[1] : `L’action n’a pas abouti. Aucune relance automatique. Détail : ${message}`;
}
async function run(operation, pending = null) {
  if (busy) return;
  busy = true;
  if (pending) status(pending);
  render();
  try { await operation(); }
  catch (error) { status(explainError(error), true); }
  finally { busy = false; render(); }
}
function save(name, value) {
  const source = json(value) + '\n';
  const url = URL.createObjectURL(new Blob([source], {type:'application/json'}));
  const a = document.createElement('a');
  a.href = url; a.download = name; a.rel = 'noopener'; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function element(tag, value, className) {
  const node = document.createElement(tag);
  if (value !== undefined) node.textContent = value;
  if (className) node.className = className;
  return node;
}
function localized(node, en, fr) {
  node.dataset.en = en; node.dataset.fr = fr; node.textContent = text(en, fr); return node;
}
function positive(value, bits = 32) {
  const result = uint(String(value), bits);
  if (result === 0n) throw Error(text('Enter a positive whole number.', 'Saisissez un entier positif.'));
  return result;
}
function invalidate() {
  if (workflow) workflow.invalidate();
  else client?.cancelPreview();
  $('preview-ack').checked = false;
}
function go(index, focus = true) {
  step = index;
  for (const panel of document.querySelectorAll('[data-panel]')) panel.hidden = Number(panel.dataset.panel) !== step;
  for (const button of document.querySelectorAll('[data-step]')) {
    if (Number(button.dataset.step) === step) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  }
  if (focus) document.querySelector(`[data-panel="${step}"] h2`).focus({preventScroll:true});
  render();
}
function syncJournal() {
  if (!recovery || storageError) throw Error(storageError || text('Recovery storage is unavailable.', 'Le stockage de récupération est indisponible.'));
  const saved = recovery.read(), raw = JSON.stringify(saved);
  if (raw !== storedJournal) {
    if (saved) client.restore(saved);
    else if (unresolved(client.pending)) throw Error('An outstanding journal was removed. Export and reconcile before continuing.');
    storedJournal = raw;
    invalidate();
  }
}
async function journalAction(operation) {
  if (!recovery || storageError) throw Error(storageError || 'Recovery storage is unavailable.');
  return recovery.exclusive(async () => { syncJournal(); return operation(); });
}
function requireWorkflow() {
  if (!workflow) throw Error(profileError || text('The pinned deployment profile is unavailable. Build the Studio assets first.', 'Le profil de déploiement est indisponible. Générez d’abord les ressources Studio.'));
  return workflow;
}
function requirePackage() {
  if (!pkg()) throw Error(text('Compile, encrypt and recover a package first.', 'Compilez, chiffrez et récupérez d’abord le dossier.'));
  return pkg();
}
function addJob(spec = null) {
  if (pkg()) throw Error('The sealed plan is frozen.');
  if ($('job-editor').children.length >= 128) throw Error('A FusionPlan contains at most 128 jobs.');
  const id = ++nextJob, card = element('section', undefined, 'job-card');
  card.dataset.job = String(id);
  const heading = element('div', undefined, 'job-card-head');
  const title = element('h4'); title.className = 'job-title';
  const remove = localized(element('button'), 'Remove job', 'Retirer le travail');
  remove.type = 'button'; remove.className = 'quiet';
  remove.addEventListener('click', () => {
    if ($('job-editor').children.length === 1) { status(text('Keep at least one job.', 'Conservez au moins un travail.'), true); return; }
    card.remove(); planChanged(); numberJobs();
  });
  heading.append(title, remove); card.append(heading);
  function field(key, en, fr, value, type = 'input') {
    const container = element('div'), label = localized(element('label'), en, fr), input = element(type);
    input.id = `job-${id}-${key}`; input.className = `job-${key}`; input.value = value || '';
    input.autocomplete = 'off'; input.spellcheck = type === 'textarea'; label.htmlFor = input.id;
    if (type === 'textarea') { input.rows = 2; input.maxLength = 512; }
    else { input.inputMode = key === 'bounty' ? 'decimal' : 'numeric'; input.maxLength = key === 'bounty' ? 100 : 10; }
    input.addEventListener('input', planChanged); container.append(label, input); return container;
  }
  card.append(field('goal', 'What must be delivered?', 'Que faut-il livrer ?', spec?.goal, 'textarea'));
  card.append(field('success', 'How will acceptance be verified?', 'Comment vérifier l’acceptation ?', spec?.successMetric, 'textarea'));
  const grid = element('div', undefined, 'field-grid');
  grid.append(field('bounty', 'Maximum bounty ($AGIALPHA)', 'Prime maximale ($AGIALPHA)', spec ? formatTokens(spec.bounty) : '100'));
  grid.append(field('duration', 'Delivery duration (seconds)', 'Délai de livraison (secondes)', String(spec?.duration ?? 86400)));
  grid.append(field('weight', 'Price preference (0–10,000)', 'Préférence du prix (0–10 000)', String(spec?.priceWeight ?? 6000)));
  card.append(grid);
  card.append(localized(element('p', undefined, 'hint'),
    '1–512 UTF-8 bytes per description. 86,400 seconds = 1 day. A weight of 6,000 means 60% price preference and 40% delivery-time preference.',
    '1 à 512 octets UTF-8 par description. 86 400 secondes = 1 jour. Un poids de 6 000 donne 60 % au prix et 40 % au délai.'));
  $('job-editor').append(card); numberJobs();
}
function numberJobs() {
  for (const [index, card] of [...$('job-editor').children].entries()) {
    card.querySelector('.job-title').textContent = `${text('Job', 'Travail')} ${String(index + 1).padStart(2, '0')}`;
    const remove = card.querySelector('button');
    remove.setAttribute('aria-label', text(`Remove job ${index + 1}`, `Retirer le travail ${index + 1}`));
    remove.disabled = busy || !!pkg() || $('job-editor').children.length === 1;
  }
}
function planChanged() {
  if (pkg()) return;
  plan = null; $('plan-result').textContent = '';
  $('plan-output').textContent = '—'; invalidate(); render();
}
function buildPlan() {
  if (!$('project-name').value.trim() || !$('project-description').value.trim())
    throw Error(text('Add a project name and a clear project description.', 'Ajoutez un nom et une description claire du projet.'));
  return compilePlan([...$('job-editor').children].map(card => {
    const read = key => card.querySelector(`.job-${key}`).value;
    return {goal:read('goal'), successMetric:read('success'), bounty:toBaseUnits(read('bounty')),
      duration:Number(positive(read('duration'))), priceWeight:Number(uint(read('weight'), 16))};
  }));
}
function fillPlan(value) {
  $('job-editor').replaceChildren();
  const original = workflow?.state.package;
  if (workflow) workflow.state.package = null;
  for (const job of value.jobs) addJob(job.spec);
  if (workflow) workflow.state.package = original;
  plan = value;
}
function updateRoutes() {
  const value = $('route-job').value, jobs = activePlan()?.jobs || [];
  if ($('route-job').dataset.root !== activePlan()?.planRoot) {
    $('route-job').replaceChildren();
    for (const job of jobs) {
      const option = element('option', `${job.index + 1}. ${job.spec.goal.slice(0, 90)}`);
      option.value = String(job.index); $('route-job').append(option);
    }
    $('route-job').dataset.root = activePlan()?.planRoot || '';
    if (jobs.some(job => String(job.index) === value)) $('route-job').value = value;
  }
  const selected = jobs[Number($('route-job').value)];
  $('route-summary').textContent = selected ? `${selected.spec.goal} · ${amount(selected.spec.bounty)} · ${selected.spec.duration} ${text('seconds', 'secondes')}\n${selected.spec.successMetric}` : text('Restore the exact plan to choose a committed job.', 'Restaurez le plan exact pour choisir un travail engagé.');
}
function render() {
  if (workflow) { workflow.context(); workflow.steps(); }
  const state = workflow?.state, observation = state?.observation, p = activePlan();
  if (client && observedEpoch !== client.epoch) {
    observedEpoch = client.epoch; discoveryCursor = null; $('preview-ack').checked = false;
    $('funding-quote').textContent = ''; $('owned-seeds').replaceChildren();
  }
  const connected = !!client?.account, selected = !!client?.provider;
  for (const button of document.querySelectorAll('button')) button.disabled = busy;
  for (const input of document.querySelectorAll('input,select,textarea')) input.disabled = busy;
  $('project-editor').disabled = busy || !!pkg(); $('seal-fields').disabled = busy || !!pkg();
  $('deployment-choice').disabled = busy || !defaultProfile || !!pkg() || unresolved(client?.pending);
  $('frozen-note').hidden = !pkg();
  for (const id of ['connect', 'switch-network', 'disconnect', 'inspect-wallet']) $(id).disabled = busy || !selected;
  for (const button of document.querySelectorAll('[data-wallet]')) button.disabled = busy || !connected;
  for (const button of document.querySelectorAll('[data-read]')) button.disabled = busy || !selected;
  $('compile').disabled = busy || !!pkg(); $('add-job').disabled = busy || !!pkg();
  $('plan-next').disabled = busy || !p; $('seal-package').disabled = busy || !p || !!pkg() || !workflow;
  for (const id of ['export-kit', 'export-kit-again']) $(id).disabled = busy || !pkg() || !isRecoveryVerified(pkg());
  for (const id of ['publish', 'verify-publication', 'reopen-package']) $(id).disabled = busy || !pkg();
  $('export-work').disabled = busy || !state?.jobId;
  $('export-native-plan').disabled = busy || !p;
  $('delivery-result-hash').value = state?.runtime?.resultHash || '';
  $('convert-legacy').disabled = busy || !plan || !!pkg();
  $('export-review').disabled = busy || !observation?.seed;
  $('export-journal').disabled = busy || !client?.history.length;
  $('clear-journal').disabled = busy || !client?.history.length || unresolved(client?.pending);
  $('refresh-receipt').disabled = busy || !selected || !(client?.pending?.hash || client?.pending?.candidateHash);
  $('reconcile').disabled = busy || !selected || !client?.pending || client.pending.status === 'awaiting-wallet';
  $('create-successor').disabled = busy || !connected || !observation?.seed;
  $('preview-panel').hidden = !client?.prepared || !workflow?.preview;
  $('confirm').disabled = busy || !client?.prepared || !workflow?.preview || !$('preview-ack').checked || !$('journal-consent').checked || !!storageError;
  $('summary-title').textContent = $('project-name').value || text('Recovered Nova-Seed project', 'Projet Nova-Seed récupéré');
  if (!p && !$('project-name').value) $('summary-title').textContent = text('A new beginning', 'Un nouveau départ');
  $('summary-jobs').textContent = p ? String(p.jobs.length) : '—';
  $('summary-budget').textContent = p ? amount(p.totalBounty) : '—';
  $('summary-seed').textContent = state?.seedId ? `${state.seedId}${observation?.seed ? '' : text(' · unverified', ' · non vérifié')}` : '—';
  $('summary-job').textContent = state?.jobId ? `${state.jobId}${observation?.job ? '' : text(' · unverified', ' · non vérifié')}` : '—';
  $('progress-facts').replaceChildren();
  for (const flag of state?.steps || []) {
    const label = translations[flag.id];
    if (label) $('progress-facts').append(element('li', text(...label), flag.status === 'done' ? 'done' : ''));
  }
  const local = client?.stage === 'local', canary = client?.stage === 'canary', publicProfile = client?.stage === 'public';
  $('mode').textContent = local ? text('Exact-source local rehearsal', 'Répétition locale des sources exactes') : canary ? text('Authorized canary profile', 'Profil canari autorisé') : publicProfile ? text('Qualified live profile', 'Profil réel qualifié') : observation ? text('Live inspection · restricted legacy recovery', 'Consultation réelle · récupération de l’archive') : text('Local preparation', 'Préparation locale');
  $('mode-detail').textContent = local ? text('Test chain only. These are not mainnet receipts.', 'Chaîne de test seulement. Ce ne sont pas des reçus Mainnet.') : canary ? text('Only the build-bound participants, actions and limits are eligible.', 'Seuls les participants, actions et limites inscrits dans la version sont admissibles.') : publicProfile ? text('Every action is checked against this exact qualified deployment.', 'Chaque action est vérifiée contre ce déploiement qualifié exact.') : observation ? text('New exposure on the archived deployment is blocked.', 'Les nouveaux engagements sont bloqués sur l’archive.') : connected ? text('Account connected. No action without your confirmation.', 'Compte connecté. Chaque action exige votre confirmation.') : text('No wallet connection. No transaction.', 'Aucun portefeuille connecté. Aucune transaction.');
  $('deployment-policy').textContent = profileError || (local ? text('Exact-source local profile. This exercises real contract transitions on a local test chain; it is not authorization for mainnet funds.', 'Profil local des sources exactes. Les transitions sont réelles sur la chaîne locale; aucune autorisation de fonds Mainnet n’en découle.') : canary ? text('Bounded operator canary. Only the registered participants, authorized operations and exact limits in this release can be used. Every intent is independently checked against that scope.', 'Canari opérateur limité. Seuls les participants, opérations et limites exactes inscrits dans cette version sont utilisables. Chaque intention est vérifiée contre cette autorisation.') : publicProfile ? text('This release includes a qualified deployment. Current bytecode, bindings, dependencies and operation permissions must still pass before every wallet request.', 'Cette version inclut un déploiement qualifié. Le bytecode, les liaisons, dépendances et permissions actuels doivent encore être vérifiés avant chaque demande.') : text('Archived Mainnet deployment: new minting, review approvals, funding and job commitments are blocked. A separately authorized, qualified deployment is the next operator prerequisite. Existing permitted recovery remains available.', 'Déploiement Mainnet archivé : nouvelles créations, approbations, financements et engagements bloqués. Un déploiement séparément autorisé et qualifié est requis. La récupération admissible reste disponible.'));
  $('account').textContent = connected ? `${text('Account', 'Compte')} · ${client.account} · ${text('chain', 'chaîne')} ${client.chainId}` : text('No connected account.', 'Aucun compte connecté.');
  if (observation?.identity) {
    const identity = observation.identity, business = identity.roles[0];
    $('identity-result').textContent = `${text('Admission', 'Admission')}: ${identity.admitted ? text('current', 'valide') : text('missing or expired', 'absente ou expirée')} · ${text('Business role', 'Rôle entreprise')}: ${business.eligible ? text('eligible', 'admissible') : text('not eligible', 'non admissible')} · ${text('Name registered / owned', 'Nom enregistré / détenu')}: ${business.registered ? text('yes', 'oui') : text('no', 'non')} / ${business.owns ? text('yes', 'oui') : text('no', 'non')} · ${text('Admission until', 'Admission jusqu’au')}: ${time(identity.until)} · ${text('Current admission operator', 'Responsable actuel')}: ${identity.admin}`;
  } else $('identity-result').textContent = text('Inspect to read actual role ownership, admission and the current operator.', 'Consultez pour lire la propriété du rôle, l’admission et le responsable actuel.');
  const missing = [];
  if (!pkg()) missing.push(text('encrypted package', 'dossier chiffré'));
  if (!isRecoveryVerified(pkg())) missing.push(text('local recovery test', 'test local de récupération'));
  if (!state?.recoveryExported) missing.push(text('Recovery Kit export', 'export du kit'));
  if (!state?.publication) missing.push(text('retrieved publication', 'publication relue'));
  if (!observation?.identity?.roles[0]?.eligible) missing.push(text('live business eligibility', 'admissibilité entreprise actuelle'));
  if (!local && !canary && !publicProfile) missing.push(text('qualified deployment for new exposure', 'déploiement qualifié pour de nouveaux engagements'));
  $('mint-prerequisites').textContent = missing.length ? `${text('Still needed', 'Encore nécessaire')} : ${missing.join(' · ')}.` : text('Prerequisites are present; all will be checked again during preparation.', 'Les prérequis sont présents; ils seront revérifiés lors de la préparation.');
  $('seed-card').hidden = !observation?.seed;
  $('seed-card').replaceChildren();
  if (observation?.seed) {
    const s = observation.seed;
    $('seed-card').append(element('h4', `Nova-Seed #${s.id}`));
    for (const line of [`${text('Chain / contract', 'Chaîne / contrat')}: ${client.chainId} · ${client.contracts.Seed}`, `${text('Current owner', 'Propriétaire actuel')}: ${s.owner}`, `${text('Plan', 'Plan')}: ${s.planRoot}`, `${text('Capsule', 'Capsule')}: ${s.capsuleHash}`, `${text('Metadata', 'Métadonnées')}: ${s.metadataURI}`, `${text('Observed block', 'Bloc observé')}: ${BigInt(observation.verification.blockNumber)}`]) $('seed-card').append(element('p', line));
  }
  const review = observation?.review;
  $('review-status').textContent = review ? `${text('Round', 'Session')} ${review.number} · ${review.green ? text('Current green approval', 'Approbation verte actuelle') : text('Approval not current', 'Approbation non actuelle')} · ${text('Approve / reject / quorum', 'Pour / contre / quorum')}: ${review.yes} / ${review.no} / ${review.quorum} · ${text('Expires', 'Expire')}: ${time(review.until)} · ${text('Maximum risk', 'Risque maximal')}: ${review.maximumRiskBps} / 10,000` : text('Open a verified seed, then refresh its live review state.', 'Ouvrez un Nova-Seed vérifié, puis actualisez son évaluation.');
  const campaign = observation?.campaign;
  const phaseNames = [text('No campaign', 'Aucune campagne'), text('Funding', 'Financement'), text('Activated', 'Activée'), text('Closed', 'Fermée')];
  $('campaign-status').textContent = campaign ? `${phaseNames[Number(campaign.phase)]} · ${text('Reserve', 'Réserve')}: ${amount(campaign.reserve)} · ${text('Target', 'Objectif')}: ${amount(campaign.target)} · ${text('Whole plan', 'Plan complet')}: ${p ? amount(p.totalBounty) : text('restore its plan', 'restaurer son plan')} · ${text('Funding deadline', 'Fin du financement')}: ${time(campaign.fundingEnd)} · ${text('Execution deadline', 'Fin d’exécution')}: ${time(campaign.executionEnd)}${observation.budget && !observation.budget.targetFundsWholePlan ? text(' · The target covers only part of the plan.', ' · L’objectif ne couvre qu’une partie du plan.') : ''}` : text('No campaign observation yet.', 'Aucune observation de campagne.');
  $('route-result').textContent = observation?.job ? `${text('Job', 'Travail')} #${state.jobId} · ${text('Stage', 'État')}: ${jobStage(observation.job.stage)} · ${text('Refund', 'Remboursement')}: ${amount(observation.job.refund)}` : text('A posted job is not yet a running or completed job.', 'Un travail publié n’est pas encore un travail exécuté ou terminé.');
  const job = observation?.job, activated = !!campaign && BigInt(campaign.executionEnd) > 0n;
  const execution = [
    [text('Campaign activated', 'Campagne activée'), activated, activated ? text('Observed', 'Observée') : text('Not observed', 'Non observée')],
    [text('Job posted', 'Travail publié'), !!job, job ? `#${state.jobId}` : text('Not observed', 'Non observé')],
    [text('Worker awarded', 'Exécutant sélectionné'), !!job && !/^0x0{40}$/i.test(job.worker), job && !/^0x0{40}$/i.test(job.worker) ? job.worker : text('Not observed', 'Non observé')],
    [text('Runtime connected', 'Système connecté'), false, text('Not connected · authentication required', 'Non connecté · authentification requise')],
    [text('Result delivered', 'Résultat livré'), !!job?.resultHash && !/^0x0{64}$/i.test(job.resultHash), job?.resultHash && !/^0x0{64}$/i.test(job.resultHash) ? text('Hash observed', 'Empreinte observée') : text('Not observed', 'Non observé')],
    [text('Settlement', 'Règlement'), !!job && Number(job.state) >= 4, job ? settlement(job.settlement) : text('Not observed', 'Non observé')],
  ];
  $('execution-states').replaceChildren();
  for (const [label, done, value] of execution) {
    const li = element('li', undefined, done ? 'done' : ''); li.append(element('span', label), element('strong', value)); $('execution-states').append(li);
  }
  const record = client?.pending;
  $('pending-status').textContent = record ? `${transactionState(record.status)} · ${ACTIONS[record.action]?.label || record.action} · ${text('Created', 'Créée')}: ${new Date(record.createdAt).toLocaleString(language === 'fr' ? 'fr-CA' : 'en-CA')}` : text('No saved transaction. New actions are never submitted automatically.', 'Aucune transaction sauvegardée. Aucune nouvelle action n’est envoyée automatiquement.');
  $('journal-output').textContent = client?.history.length ? json(client.journal()) : '—';
  $('observation-output').textContent = observation ? json(observation) : '—';
  $('transaction-link').replaceChildren();
  const transactionHash = record?.candidateHash || record?.hash;
  if (transactionHash && client.chainId === 1) {
    const a = element('a', transactionHash); a.href = `https://etherscan.io/tx/${transactionHash}`; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.className = 'address'; $('transaction-link').append(a);
  } else if (transactionHash) $('transaction-link').append(element('p', transactionHash, 'address'));
  if (workflow) {
    const links = workflow.links();
    for (const id of ['reviewer-mark-link', 'work-mark-link', 'recovery-mark-link']) $(id).href = links.mark;
    $('runtime-link').href = links.successor;
  }
  updateRoutes(); numberJobs();
}
function jobStage(value) {
  const values = {none:['None','Aucun'], posted:['Posted','Publié'], 'worker-awarded':['Worker awarded','Exécutant sélectionné'],
    'result-delivered':['Result delivered','Résultat livré'], paid:['Paid','Payé'], failed:['Failed / slashed','Échec / pénalité'], refunded:['Refunded','Remboursé']};
  return values[value] ? text(...values[value]) : text('Unknown', 'Inconnu');
}
function settlement(value) {
  const values = {'accepted-payment':['Accepted payment','Paiement accepté'], 'rejection-or-delivery-timeout-with-slashing':['Rejected or late delivery; slashing','Refus ou retard; pénalité'],
    'refunded-without-slashing':['Refund without slashing','Remboursement sans pénalité'], 'not-settled':['Not settled','Non réglé']};
  return values[value] ? text(...values[value]) : text('Unknown', 'Inconnu');
}
function transactionState(value) {
  const values = {'awaiting-wallet':['Awaiting your wallet','En attente du portefeuille'], 'submission-unknown':['Submission unknown — reconcile before retrying','Envoi incertain — réconcilier avant de réessayer'],
    submitted:['Submitted; awaiting verification','Envoyée; vérification requise'], 'mined-not-finalized':['Mined; awaiting finality','Incluse; finalité en attente'],
    finalized:['Original action finalized','Action originale finalisée'], reverted:['Reverted','Annulée par le contrat'], cancelled:['Cancelled in wallet','Annulée dans le portefeuille'],
    replaced:['Replaced by another action','Remplacée par une autre action'], reorged:['Block reorganized; reconcile','Bloc réorganisé; réconcilier'],
    'not-submitted':['Not submitted','Non envoyée'], 'rejected-by-wallet':['Wallet request declined','Demande refusée'],
    'effect-unverified':['Transaction finalized; contract effects still require verification','Transaction finalisée; effets du contrat à vérifier'],
    'authorization-mismatch':['Transaction differs from the authorized scope; reconcile','Transaction hors du périmètre autorisé; réconcilier'],
    'pending-or-replaced':['Pending or replaced; still unresolved','En attente ou remplacée; non résolue']};
  return values[value] ? text(...values[value]) : String(value);
}
function previewText(action, summary) {
  const name = actionNames[action] ? text(...actionNames[action]) : action;
  if (action === 'mint') return `${name}. ${text('No token fee or allowance. Only ETH network fees.', 'Aucun frais ni autorisation de jetons. Seulement les frais réseau ETH.')}`;
  if (action === 'approve') return `${name}: ${summary.amount} $AGIALPHA. ${text('This does not purchase lots.', 'Cela n’achète aucun lot.')}`;
  if (action === 'fund') return `${name}: ${summary.lots} ${text('lots, at most', 'lots, au maximum')} ${summary.maxCost} $AGIALPHA.`;
  if (action === 'activate') return `${name}. ${text('Trading and curve redemption stop immediately. Activation does not start a runtime.', 'Les échanges et rachats sur la courbe cessent immédiatement. L’activation ne démarre aucun système.')}`;
  if (action === 'route') return `${name}: ${summary.spec?.goal || ''}. ${text('Maximum bounty', 'Prime maximale')}: ${amount(summary.spec?.bounty)}.`;
  if (action === 'campaign') return `${name}. ${text('Target', 'Objectif')}: ${amount(summary.target)}. ${summary.partialFunding ? text('This funds only part of the plan.', 'Cela ne finance qu’une partie du plan.') : text('Target covers the committed bounty budget.', 'L’objectif couvre les primes engagées.')}`;
  return name;
}
function showPreview(prepared) {
  $('preview-summary').textContent = previewText(prepared.action, prepared.summary);
  $('preview-facts').replaceChildren();
  const fields = [[text('Network', 'Réseau'), `${client.chainId === 1 ? 'Ethereum Mainnet' : text('Local test chain', 'Chaîne locale de test')} · ${client.chainId}`],
    [text('Sender', 'Expéditeur'), prepared.transaction.from], [text('Destination', 'Destination'), prepared.transaction.to],
    [text('Contract action', 'Action du contrat'), ACTIONS[prepared.actionId]?.method || prepared.actionId],
    [text('ETH sent to contract', 'ETH envoyé au contrat'), '0 ETH'],
    [text('Gas estimate; paid separately in ETH', 'Gaz estimé; frais distincts en ETH'), prepared.gas],
    [text('Deployment', 'Déploiement'), client.profile.profile]];
  for (const [label, value] of fields) { const div = element('div'); div.append(element('dt', label), element('dd', String(value))); $('preview-facts').append(div); }
  $('preview-output').textContent = json(prepared); $('preview-ack').checked = false;
  render(); $('preview-panel').hidden = false; $('preview-title').focus({preventScroll:true});
  $('preview-panel').scrollIntoView({block:'start', behavior:'instant'});
  status(text('Read this exact action, enable the public recovery journal, then confirm if you choose.', 'Examinez cette action exacte, activez le journal public de récupération, puis confirmez si vous le souhaitez.'));
}
async function prepare(action, input = {}) {
  requireWorkflow();
  if (!client.account) throw Error(text('Connect the selected wallet before preparing an action.', 'Connectez le portefeuille choisi avant de préparer une action.'));
  const prepared = await workflow.prepare(action, input); showPreview(prepared);
}
function wire(id, operation, message = null) {
  $(id).addEventListener('click', () => run(operation, message ? text(...message) : null));
}
function profileOptions() {
  const selected = $('deployment-choice').value;
  $('deployment-choice').replaceChildren();
  for (const entry of registeredProfiles) {
    const stageLabel = {archive:text('Archive · recovery only', 'Archive · récupération seulement'),
      local:text('Exact-source local test', 'Test local des sources exactes'), canary:text('Authorized canary', 'Canari autorisé'),
      public:text('Qualified live deployment', 'Déploiement réel qualifié')}[entry.stage] || entry.stage;
    const option = element('option', `${stageLabel} · ${entry.profile.profile} · ${text('chain', 'chaîne')} ${entry.profile.chainId}`);
    option.value = entry.id; $('deployment-choice').append(option);
  }
  if (registeredProfiles.some(entry => entry.id === selected)) $('deployment-choice').value = selected;
}
function useProfile(profile) {
  const previous = client;
  const candidate = new MarkClient(profile, render, journal => {
    if (!recovery || storageError || !$('journal-consent').checked) throw Error(storageError || 'Public recovery-journal consent is required before a wallet request.');
    recovery.write(journal); storedJournal = JSON.stringify(journal);
  });
  previous?.disconnect();
  client = candidate; workflow = new NovaWorkflow(client, render);
  storedJournal = null; storageError = null; profileError = null; observedEpoch = -1;
  $('wallet-choice').value = ''; discoveryCursor = null; parent = '0'; restoredPublication = null;
  try {
    recovery ||= new RecoveryStore(window.localStorage, navigator.locks);
    syncJournal();
  } catch (error) {
    storageError = text('The saved journal must be restored under its original registered deployment before new signing. ', 'Le journal sauvegardé doit être restauré avec son déploiement inscrit original avant toute signature. ') + explainError(error);
    status(storageError, true);
  }
}
$('deployment-choice').addEventListener('change', () => run(async () => {
  const prior = registeredProfiles.find(entry => entry.id === client?.profileIdentity)?.id;
  try {
    if (pkg()) throw Error(text('This sealed package retains its exact deployment. Start a new session to change deployment.', 'Ce dossier scellé conserve son déploiement exact. Commencez une nouvelle session pour le changer.'));
    if (unresolved(client?.pending)) throw Error('Reconcile the outstanding transaction under its original profile first.');
    useProfile(selectBuildProfile($('deployment-choice').value, defaultProfile));
    if (!storageError) status(text('Deployment selected. Reconnect explicitly; your unsealed job draft is preserved.', 'Déploiement sélectionné. Reconnectez-vous explicitement; votre brouillon non scellé est conservé.'));
  } catch (error) { if (prior) $('deployment-choice').value = prior; throw error; }
}));

for (const button of document.querySelectorAll('[data-step],[data-go]')) button.addEventListener('click', () => go(Number(button.dataset.step ?? button.dataset.go)));
$('start-create').addEventListener('click', () => go(1));
$('start-resume').addEventListener('click', () => { go(6); $('import-kit').focus(); });
$('start-existing').addEventListener('click', () => { go(3); $('open-seed-id').focus(); });
wire('start-explore', async () => {
  if (pkg() || $('project-name').value || $('project-description').value) throw Error(text('Your current work is preserved. Clear the private session before loading an example.', 'Votre travail est conservé. Effacez la session privée avant de charger un exemple.'));
  $('project-name').value = text('Example · public data quality report', 'Exemple · rapport de qualité de données publiques');
  $('project-description').value = text('Build a reproducible quality report for a licensed public dataset, with clear tests and a usable result.', 'Créer un rapport reproductible de qualité pour un jeu public sous licence, avec des tests clairs et un résultat utilisable.');
  $('job-editor').replaceChildren();
  addJob({goal:text('Produce a reproducible data-quality report from the selected public dataset.', 'Produire un rapport reproductible de qualité du jeu de données public.'),
    successMetric:text('Include the source URL and license, reproducible commands, missing-value checks and a report that passes the agreed acceptance tests.', 'Inclure URL et licence, commandes reproductibles, tests de valeurs manquantes et rapport satisfaisant les critères convenus.'),
    bounty:toBaseUnits('100'),duration:86400,priceWeight:6000});
  $('evidence-text').value = text('Example only. Select and document the exact public licensed source and objective acceptance tests before committing.', 'Exemple uniquement. Définir la source publique sous licence et les tests objectifs avant tout engagement.');
  plan = null; go(1); status(text('Editable example loaded. Replace the assumptions before committing real work.', 'Exemple modifiable chargé. Remplacez les hypothèses avant d’engager un vrai travail.'));
});
wire('add-job', async () => { addJob(); planChanged(); });
for (const id of ['project-name', 'project-description']) $(id).addEventListener('input', planChanged);
wire('compile', async () => {
  plan = buildPlan(); $('plan-output').textContent = json(plan);
  $('plan-result').textContent = `${text('Exact plan checked', 'Plan exact vérifié')} · ${plan.jobs.length} ${text('jobs', 'travaux')} · ${amount(plan.totalBounty)}.`;
  $('campaign-target').value = formatTokens(plan.totalBounty);
  status(text('The exact plan and proofs are ready. Editing any job will require compiling again.', 'Le plan exact et ses preuves sont prêts. Toute modification exige une nouvelle compilation.'));
});
$('plan-next').addEventListener('click', () => go(2));
wire('seal-package', async () => {
  requireWorkflow();
  if (!plan) throw Error(text('Compile your plan first.', 'Compilez d’abord votre plan.'));
  if ($('passphrase').value !== $('passphrase-confirm').value) throw Error(text('The capsule passphrases do not match.', 'Les phrases secrètes de capsule diffèrent.'));
  if (!$('evidence-text').value.trim()) throw Error(text('Describe the public evidence and acceptance context first.', 'Décrivez d’abord les preuves publiques et le contexte d’acceptation.'));
  const prepared = await preparePackage({genome:{schema:'agialpha.novaseed.genome.v1', name:$('project-name').value,
    description:$('project-description').value}, plan, passphrase:$('passphrase').value,
    evidence:{schema:'agialpha.novaseed.public-evidence.v1', statement:$('evidence-text').value}, profile:client.profile});
  await workflow.setPackage(prepared, {parent});
  $('passphrase').value = ''; $('passphrase-confirm').value = '';
  $('commitments').textContent = json(prepared.commitments); $('evidence-output').textContent = json(prepared.evidence);
  $('package-result').textContent = text('Encrypted once. Exact plan recovered and verified locally. Export your Recovery Kit next.', 'Chiffré une fois. Plan exact récupéré et vérifié localement. Exportez maintenant votre kit.');
  status(text('Your encrypted package passed its recovery test. The passphrase fields have been cleared.', 'Votre dossier chiffré a réussi le test. Les champs de phrase secrète ont été effacés.'));
}, ['Encrypting and verifying the exact capsule locally…', 'Chiffrement et vérification locale de la capsule exacte…']);
async function exportKit() {
  const p = requirePackage();
  if (!$('recovery-disclosure').checked && !$('recovery-disclosure-again').checked) {
    const control = step === 6 ? $('recovery-disclosure-again') : $('recovery-disclosure');
    control.focus();
    throw Error(text('Review and acknowledge the readable contents of the private Recovery Kit first.', 'Examinez et acceptez d’abord le contenu lisible du kit privé.'));
  }
  const state = workflow.state;
  const kit = await createRecoveryKit(p, {publication:state.publication || restoredPublication,
    ids:{seedId:state.seedId,jobId:state.jobId,parent:state.parent}, receipts:cloneJSON(state.receipts || []),
    journal:client.history.length ? cloneJSON(client.journal()) : null, disclosureAccepted:true});
  save('Nova-Seed-Recovery-Kit.json', kit); workflow.markRecoveryExported();
  status(text('Recovery Kit download prepared. Keep it private and store your capsule passphrase separately.', 'Téléchargement du kit préparé. Gardez-le privé et conservez la phrase de capsule séparément.'));
}
wire('export-kit', exportKit); wire('export-kit-again', exportKit);
wire('publish', async () => {
  const p = requirePackage();
  if (!$('publication-disclosure').checked) throw Error(text('Review and authorize the public artifacts before uploading.', 'Examinez et autorisez les artefacts publics avant de publier.'));
  if (!workflow.state.recoveryExported) throw Error(text('Export your Recovery Kit before publishing.', 'Exportez votre kit avant de publier.'));
  adapter?.clearCredentials(); adapter = new PinataStorage({token:$('storage-token').value}); $('storage-token').value = '';
  const publication = await publishPackage(p, {adapter, name:$('public-name').value,
    description:$('public-description').value, disclosureAccepted:true});
  await workflow.setPublication(publication, {adapter}); restoredPublication = null;
  $('metadata-uri').value = publication.metadataURI;
  $('publication-output').textContent = json(publication);
  $('publication-result').textContent = text('Capsule, evidence and metadata were uploaded and retrieved with matching commitments.', 'Capsule, preuves et métadonnées publiées puis relues avec engagements concordants.');
  status(text('Publication verified. Export an updated Recovery Kit to retain these references.', 'Publication vérifiée. Exportez un kit actualisé pour conserver ces références.'));
}, ['Publishing and retrieving the exact artifacts…', 'Publication et relecture des artefacts exacts…']);
wire('verify-publication', async () => {
  const p = requirePackage(); adapter ||= new PinataStorage();
  const publication = await importPublication(p, $('metadata-uri').value.trim(), {adapter});
  await workflow.setPublication(publication, {adapter}); restoredPublication = null;
  $('publication-output').textContent = json(publication);
  $('publication-result').textContent = text('Existing artifacts retrieved and matched to this exact package.', 'Artefacts existants relus et reliés à ce dossier exact.');
  status(text('Publication verified. Its availability will be checked again before minting.', 'Publication vérifiée. Sa disponibilité sera revérifiée avant la création du NFT.'));
});
$('clear-token').addEventListener('click', () => { $('storage-token').value = ''; adapter?.clearCredentials(); status(text('Upload credential forgotten by this session.', 'Identifiant de publication oublié par cette session.')); });
function addProvider(provider, name) {
  if (!provider || typeof provider.request !== 'function' || providers.length >= 20 || providers.some(item => item.provider === provider)) return;
  const index = providers.push({provider,name:String(name || 'Browser wallet').slice(0,80)}) - 1;
  const option = element('option', providers[index].name); option.value = String(index); $('wallet-choice').append(option);
}
window.addEventListener('eip6963:announceProvider', event => {
  try { addProvider(event.detail?.provider, event.detail?.info?.name); } catch { /* Extension metadata is untrusted data. */ }
});
$('discover').addEventListener('click', () => {
  window.dispatchEvent(new Event('eip6963:requestProvider'));
  if (window.ethereum) addProvider(window.ethereum, text('Browser wallet (legacy provider)', 'Portefeuille navigateur (ancien fournisseur)'));
  status(text('Choose a listed wallet. If none is listed, use a compatible injected wallet. No account access was requested.', 'Choisissez un portefeuille listé. Sinon, utilisez une extension compatible. Aucun accès au compte n’a été demandé.'));
});
$('wallet-choice').addEventListener('change', () => run(async () => {
  requireWorkflow();
  const item = $('wallet-choice').value === '' ? null : providers[Number($('wallet-choice').value)];
  if (item) client.select(item.provider); else client.disconnect();
  invalidate(); status(text('Provider selected. Connect requests account access; inspection is read-only.', 'Fournisseur choisi. La connexion demande l’accès au compte; la consultation reste en lecture seule.'));
}));
wire('connect', async () => { await client.connect(); status(text('Account connected. No transaction was requested.', 'Compte connecté. Aucune transaction demandée.')); });
wire('switch-network', async () => { await client.switchMainnet(); status(text('Network selected. Connect the account again.', 'Réseau choisi. Reconnectez le compte.')); });
wire('disconnect', async () => { client.disconnect(); $('wallet-choice').value = ''; invalidate(); status(text('Page disconnected. Wallet permissions remain managed in your wallet.', 'Page déconnectée. Les permissions se gèrent dans votre portefeuille.')); });
wire('inspect-wallet', async () => { await requireWorkflow().refresh(); status(text('Live deployment and eligibility observation verified.', 'Consultation du déploiement et de l’admissibilité vérifiée.')); }, ['Reading exact deployment, roles and admission…', 'Lecture du déploiement, des rôles et de l’admission…']);
wire('register-business', () => prepare('identity', {role:'0', label:$('business-label').value}));
wire('identity-handoff', async () => { save('Nova-Seed-Identity-Request.json', requireWorkflow().operatorRequest('0', $('business-label').value)); status(text('Operator request exported. It records a request, not authorization.', 'Demande opérateur exportée. Elle ne constitue pas une autorisation.')); });
wire('mint', () => prepare('mint'), ['Rechecking the exact package and mint prerequisites…', 'Vérification du dossier exact et des prérequis de création…']);
wire('open-seed', async () => {
  const wf = requireWorkflow(), id = $('open-seed-id').value.trim(), hash = $('open-receipt').value.trim();
  if (!!id === !!hash) throw Error(text('Provide either a seed ID or a mint transaction hash.', 'Indiquez soit un identifiant, soit une empreinte de création.'));
  if (hash) await wf.openReceipt(hash); else await wf.refresh(positive(id,256).toString(), null);
  status(text('Existing seed read and verified. No new seed was minted.', 'Nova-Seed existant lu et vérifié. Aucun nouveau NFT n’a été créé.'));
});
wire('my-seeds', async () => {
  const result = await requireWorkflow().discoverSeeds({fromBlock:uint($('discovery-start').value,64).toString(), cursor:discoveryCursor});
  discoveryCursor = result.complete ? null : result.cursor; $('owned-seeds').replaceChildren();
  $('owned-seeds').append(element('p', `${text('Current ownership verified for', 'Propriété actuelle vérifiée pour')} ${result.seeds.length} ${text('seeds in the scanned range.', 'Nova-Seeds dans la plage parcourue.')} ${result.complete ? text('Scan complete.', 'Recherche terminée.') : text(`More history remains. Next block: ${result.nextBlock}. Select Find my seeds again to continue.`, `Historique restant. Prochain bloc : ${result.nextBlock}. Cliquez encore pour continuer.`)}`));
  for (const seed of result.seeds) {
    const button = element('button', `Nova-Seed #${seed.id}`, 'secondary'); button.type = 'button';
    button.addEventListener('click', () => run(async () => { await workflow.refresh(seed.id, null); $('open-seed-id').value = seed.id; }));
    $('owned-seeds').append(button);
  }
  status(text('Ownership scan finished for this bounded range. Incoming and outgoing transfers were reconciled.', 'Recherche terminée pour cette plage limitée. Transferts entrants et sortants réconciliés.'));
});
wire('refresh-review', async () => { await requireWorkflow().refresh(); status(text('Review, campaign and job observations refreshed.', 'Évaluation, campagne et travail actualisés.')); });
wire('request-review', () => prepare('request-review'));
wire('export-review', async () => { save('Nova-Seed-Review-Request.json', requireWorkflow().reviewerRequest()); status(text('Public review reference exported. Share only through your chosen reviewer channel.', 'Référence publique exportée. Transmettez-la par le canal choisi avec les évaluateurs.')); });
wire('attest-risk', () => {
  if (!$('risk-decision').value) throw Error(text('Make your own decision after reviewing the evidence.', 'Prenez votre propre décision après examen des preuves.'));
  return prepare('risk-approve', {riskBps:$('risk-score').value, approved:$('risk-decision').value === 'true', evidenceHash:$('risk-evidence').value});
});
wire('open-campaign', () => {
  const end = new Date($('campaign-end').value).getTime();
  if (!Number.isFinite(end) || end % 1000 !== 0) throw Error(text('Choose a valid funding end date and time.', 'Choisissez une date et une heure de fin valides.'));
  return prepare('campaign', {base:$('campaign-base').value, slope:$('campaign-slope').value,
    maxLots:$('campaign-lots').value, target:$('campaign-target').value,
    fundingEnd:String(end / 1000), duration:String(positive($('campaign-days').value) * 86400n)});
});
wire('quote-funding', async () => {
  const quote = await requireWorkflow().quoteFunding($('fund-lots').value);
  $('fund-max').value = quote.maxCost;
  $('funding-quote').textContent = `${quote.lots} ${text('lots', 'lots')} · ${quote.cost} $AGIALPHA · ${text('Current allowance', 'Autorisation actuelle')}: ${amount(quote.allowance)} · ${quote.needsApproval ? text('A separate bounded approval is needed.', 'Une autorisation limitée distincte est nécessaire.') : text('Existing allowance covers this quote.', 'L’autorisation actuelle couvre ce devis.')} ${quote.partialFunding ? text('The campaign target does not cover the full plan.', 'L’objectif ne couvre pas tout le plan.') : ''}`;
  status(text('Current quote loaded into your maximum cost. Review it before approval or purchase.', 'Le devis actuel remplit le coût maximal. Examinez-le avant toute autorisation ou achat.'));
});
wire('approve-funding', () => prepare('approve', {spender:'Mark', amount:$('fund-max').value}));
wire('fund', () => prepare('fund', {lots:$('fund-lots').value, maxCost:$('fund-max').value}));
wire('activate', () => prepare('activate'));
wire('route', () => prepare('route', {index:$('route-job').value, auctionSeconds:$('auction-seconds').value,
  reviewers:[$('reviewer-1').value, $('reviewer-2').value, $('reviewer-3').value]}));
wire('export-work', async () => { save('Nova-Seed-Work-Package.json', requireWorkflow().workPackage(Number($('route-job').value))); status(text('Exact work package exported. Runtime remains unconnected until independently authenticated.', 'Dossier exact exporté. Le système reste non connecté jusqu’à une authentification indépendante.')); });
wire('export-native-plan', async () => {
  if (!activePlan()) throw Error('Compile or restore your exact plan first.');
  save('fusion-plan.json', activePlan());
  status(text('Native-compatible FusionPlan exported. Use the work package to retain the deployment and actual job binding.', 'FusionPlan natif exporté. Utilisez le dossier de travail pour conserver le déploiement et le lien au travail réel.'));
});
wire('verify-delivery', async () => {
  const file = $('delivery-file').files?.[0];
  if (!file || file.size > 2000000) throw Error(text('Choose a signed delivery JSON file of at most 2 MB.', 'Choisissez un fichier JSON signé d’au plus 2 Mo.'));
  const delivery = await requireWorkflow().importDelivery(await file.text(), {trustedPublicKey:$('delivery-key').value.trim(), index:Number($('route-job').value)});
  $('delivery-result').textContent = text('Signed delivery evidence verified for the actual job. This is evidence import, not a live runtime connection or an on-chain approval.', 'Preuve de livraison signée vérifiée pour le travail réel. Cet import n’est ni une connexion active ni une approbation sur la chaîne.');
  status(text('Delivery verified. Independent result review and settlement remain separate.', 'Livraison vérifiée. L’évaluation indépendante et le règlement restent distincts.'));
  return delivery;
});
wire('submit-delivery', () => {
  const wf = requireWorkflow();
  if (wf.state.runtime?.status !== 'evidence-imported' || !wf.state.runtime.signatureVerified || wf.state.runtime.jobId !== wf.state.jobId)
    throw Error(text('Connect the assigned worker and verify the exact signed delivery for this job first.', 'Connectez l’exécutant attribué et vérifiez d’abord sa livraison signée exacte.'));
  return prepare('submit', {result:wf.state.runtime.resultHash, uri:$('delivery-uri').value.trim()});
});
wire('award-job', () => prepare('award'));
wire('timeout-job', () => prepare('timeout'));
wire('open-route-receipt', async () => {
  await requireWorkflow().openRouteReceipt($('route-receipt').value.trim());
  if (workflow.state.route?.index !== undefined) $('route-job').value = String(workflow.state.route.index);
  status(text('Routing receipt, exact plan index and posted job verified.', 'Reçu de publication, index exact et travail publié vérifiés.'));
});
wire('transfer-seed', () => prepare('transferSeed', {to:$('transfer-to').value, acknowledged:$('transfer-ack').checked}));
wire('sell', () => prepare('sell', {count:$('sell-lots').value, minReturn:$('sell-min').value}));
wire('close-campaign', () => prepare('close'));
wire('reclaim', () => prepare('reclaim'));
wire('collect-refund', () => prepare('collect'));
wire('revoke-allowance', () => prepare('approve', {spender:'Mark', amount:'0'}));
wire('create-successor', async () => {
  const wf = requireWorkflow();
  if (pkg() && !wf.state.recoveryExported) throw Error(text('Export the parent Recovery Kit first.', 'Exportez d’abord le kit du parent.'));
  const successor = await wf.createSuccessor(); parent = successor.parent;
  const oldName = $('project-name').value;
  workflow = new NovaWorkflow(client, render); restoredPublication = null;
  plan = successor.plan; if (plan) fillPlan(plan);
  $('project-name').value = oldName ? `${oldName} · ${text('successor', 'successeur')}` : `${text('Successor to Nova-Seed', 'Successeur du Nova-Seed')} #${parent}`;
  $('package-result').textContent = ''; $('publication-result').textContent = ''; $('commitments').textContent = '—';
  $('publication-output').textContent = '—'; $('metadata-uri').value = ''; $('recovery-disclosure').checked = false;
  $('publication-disclosure').checked = false; $('evidence-text').value = ''; go(1);
  status(text(`Parent #${parent} verified and preserved. Edit the new plan and evidence; no approval is inherited.`, `Parent #${parent} vérifié et conservé. Modifiez le nouveau plan et ses preuves; aucune approbation n’est héritée.`));
});
$('preview-ack').addEventListener('change', render);
for (const id of ['journal-consent', 'journal-consent-recovery']) $(id).addEventListener('change', () => {
  const checked = $(id).checked;
  $('journal-consent').checked = checked; $('journal-consent-recovery').checked = checked; render();
});
wire('confirm', async () => {
  if (!$('journal-consent').checked) throw Error(text('Enable the public recovery journal before signing.', 'Activez le journal public de récupération avant signature.'));
  const hash = await journalAction(() => workflow.confirm($('preview-ack').checked));
  $('preview-ack').checked = false;
  status(`${text('Submitted, not yet confirmed. Verify the receipt in Recover & manage.', 'Envoyée, pas encore confirmée. Vérifiez le reçu dans Récupérer et gérer.')} ${hash}`);
  go(6);
}, ['Rechecking before the wallet request. Do not retry an unanswered request.', 'Nouvelle vérification avant signature. Ne relancez pas une demande sans réponse.']);
$('cancel-preview').addEventListener('click', () => { invalidate(); status(text('Preview cancelled. Nothing was sent.', 'Aperçu annulé. Rien n’a été envoyé.')); render(); });
async function reconcile(hash) {
  const record = await journalAction(() => requireWorkflow().reconcile(hash));
  status(`${transactionState(record.status)}. ${text('All subsequent actions still require their own preview.', 'Chaque action suivante exige son propre aperçu.')}`);
}
wire('refresh-receipt', () => reconcile(client.pending.candidateHash || client.pending.hash));
wire('reconcile', () => reconcile($('reconcile-hash').value.trim()));
wire('export-journal', async () => { save('Nova-Seed-MARK-Transaction-Journal.json', requireWorkflow().client.journal()); status(text('Public transaction journal exported.', 'Journal public des transactions exporté.')); });
$('import-kit').addEventListener('change', () => run(async () => {
  const file = $('import-kit').files?.[0]; if (!file) return;
  if (file.size > MAX_KIT_BYTES) throw Error(text('The Recovery Kit exceeds 2 MB.', 'Le kit dépasse 2 Mo.'));
  const restored = await restoreRecoveryKit(await file.text());
  requireWorkflow();
  const wf = new NovaWorkflow(client);
  await wf.setPackage(restored.package, {parent:restored.ids?.parent || '0', recoveryExported:true});
  for (const key of ['seedId', 'jobId']) {
    const id = restored.ids?.[key]; wf.state[key] = id === undefined || id === null || id === '' ? null : positive(String(id),256).toString();
  }
  if (restored.journal?.transactions?.length) {
    const checked = new MarkClient(client.profile); checked.restore(restored.journal);
    if (checked.pending) checked.pending.status = 'submission-unknown';
    await journalAction(async () => {
      if (unresolved(client.pending) && json(client.journal()) !== json(restored.journal)) throw Error('Reconcile the existing journal before importing another.');
      if (!$('journal-consent').checked) throw Error(text('This kit contains transactions. Enable the public recovery journal in Identity & mint, then import again.', 'Ce kit contient des transactions. Activez le journal public dans Identité et NFT, puis importez de nouveau.'));
      recovery.write(checked.journal()); client.restore(checked.journal()); storedJournal = JSON.stringify(checked.journal());
    });
  }
  workflow = wf; workflow.notify = render;
  parent = wf.state.parent; restoredPublication = restored.publication;
  plan = restored.package.plan;
  $('project-name').value = ''; $('project-description').value = ''; fillPlan(plan);
  $('evidence-text').value = restored.package.evidence.statement || ''; $('evidence-output').textContent = json(restored.package.evidence);
  $('commitments').textContent = json(restored.package.commitments); $('plan-output').textContent = json(plan);
  $('metadata-uri').value = restoredPublication?.metadataURI || ''; $('publication-output').textContent = restoredPublication ? json(restoredPublication) : '—';
  $('publication-result').textContent = restoredPublication ? text('Imported references are unverified. Explicitly retrieve them again before minting.', 'Références importées non vérifiées. Relisez-les explicitement avant de créer un NFT.') : '';
  $('package-result').textContent = text('Kit integrity checked. Enter your capsule passphrase below for a fresh local recovery test.', 'Intégrité du kit vérifiée. Saisissez la phrase de capsule pour un nouveau test local.');
  $('open-seed-id').value = wf.state.seedId || ''; $('reopen-passphrase').focus();
  $('import-kit').value = '';
  status(text('Recovery Kit restored without network traffic or wallet prompts. Decrypt locally, then explicitly refresh chain state.', 'Kit restauré sans trafic réseau ni demande de signature. Déchiffrez localement, puis actualisez explicitement la chaîne.'));
}));
wire('reopen-package', async () => {
  await verifyPackage(requirePackage(), {passphrase:$('reopen-passphrase').value}); $('reopen-passphrase').value = '';
  $('package-result').textContent = text('The encrypted capsule recovered the exact plan. No transaction was requested.', 'La capsule chiffrée restitue le plan exact. Aucune transaction demandée.');
  status(text('Local recovery passed. Reverify any publication and refresh chain observations before continuing.', 'Récupération locale réussie. Revérifiez la publication et actualisez la chaîne avant de continuer.'));
}, ['Decrypting and checking the exact saved plan locally…', 'Déchiffrement et vérification locale du plan sauvegardé…']);
wire('convert-legacy', async () => {
  if (pkg() || workflow?.state.seedId) throw Error(text('Conversion is only for a new project using an unminted legacy capsule.', 'La conversion concerne un nouveau projet utilisant une ancienne capsule non créée sur chaîne.'));
  if (!plan || !$('evidence-text').value.trim()) throw Error(text('Compile the new plan and enter public evidence first.', 'Compilez le nouveau plan et saisissez les preuves publiques.'));
  const file = $('legacy-file').files?.[0];
  if (!file || file.size > 250000) throw Error(text('Choose the original capsule JSON, at most 250 KB.', 'Choisissez la capsule JSON originale, au plus 250 Ko.'));
  const original = parseBoundedJSON(await file.text());
  const converted = await convertLegacyCapsule(original, $('legacy-passphrase').value, {plan,
    evidence:{schema:'agialpha.novaseed.public-evidence.v1',statement:$('evidence-text').value}, profile:requireWorkflow().client.profile});
  await workflow.setPackage(converted.package, {parent:'0'}); $('legacy-passphrase').value = '';
  save('Nova-Seed-Original-Legacy-Capsule.json', converted.original);
  $('commitments').textContent = json(converted.package.commitments); $('evidence-output').textContent = json(converted.package.evidence);
  $('package-result').textContent = text('Legacy capsule preserved. A new encrypted package with the exact plan passed recovery. Export its new Recovery Kit.', 'Ancienne capsule conservée. Le nouveau dossier chiffré contient le plan exact et a réussi la récupération. Exportez son nouveau kit.');
  go(2); status(text('Conversion completed locally. The original NFT, if any, was not modified.', 'Conversion locale terminée. Aucun NFT existant n’a été modifié.'));
});
wire('clear-session', async () => {
  if (!$('clear-ack').checked) throw Error(text('Confirm you saved the files you need.', 'Confirmez avoir sauvegardé les fichiers nécessaires.'));
  if (unresolved(client?.pending)) throw Error(text('Reconcile the outstanding transaction before clearing the session.', 'Réconciliez la transaction en attente avant d’effacer la session.'));
  adapter?.clearCredentials(); clearRecoveryState();
  window.location.reload();
});
wire('clear-journal', async () => {
  if (!$('clear-ack').checked) throw Error(text('Confirm you saved the Recovery Kit and journal.', 'Confirmez avoir sauvegardé le kit et le journal.'));
  await journalAction(async () => {
    if (unresolved(client.pending)) throw Error('Reconcile the outstanding transaction before removing its journal.');
    recovery.storage.removeItem(JOURNAL_KEY); storedJournal = 'null'; client.history = []; client.pending = null; invalidate();
  });
  status(text('The local public transaction journal was removed. Exported files and confirmed chain transactions remain.', 'Le journal local a été supprimé. Les fichiers exportés et transactions confirmées restent conservés.'));
});
window.addEventListener('storage', event => {
  if (event.key === JOURNAL_KEY || event.key === null) {
    invalidate();
    if (!busy) try { syncJournal(); render(); } catch (error) { storageError = explainError(error); status(storageError, true); render(); }
  }
});
window.addEventListener('beforeunload', event => {
  if ((pkg() && !workflow.state.recoveryExported) || unresolved(client?.pending)) { event.preventDefault(); event.returnValue = ''; }
});
$('language').addEventListener('click', () => {
  language = language === 'en' ? 'fr' : 'en'; document.documentElement.lang = language;
  for (const node of document.querySelectorAll('[data-en]')) node.textContent = node.dataset[language];
  $('language').textContent = language === 'en' ? 'Français' : 'English'; $('language').lang = language === 'en' ? 'fr' : 'en';
  $('project-name').placeholder = text('A useful, specific outcome', 'Un résultat utile et précis');
  profileOptions();
  if (workflow?.preview) $('preview-summary').textContent = previewText(workflow.preview.action, workflow.preview.summary);
  status(text('English selected. Your project content is unchanged.', 'Français sélectionné. Le contenu de votre projet est conservé.'));
  render();
});
$('large-text').addEventListener('click', () => {
  const enabled = document.documentElement.classList.toggle('large-text'); $('large-text').setAttribute('aria-pressed', String(enabled));
});
for (const input of document.querySelectorAll('input,select,textarea')) {
  if (!['preview-ack', 'journal-consent', 'journal-consent-recovery', 'deployment-choice', 'clear-ack', 'recovery-disclosure', 'recovery-disclosure-again', 'reopen-passphrase', 'reconcile-hash', 'import-kit', 'wallet-choice'].includes(input.id)) {
    input.addEventListener('input', () => { invalidate(); if (input.id === 'route-job') updateRoutes(); });
    input.addEventListener('change', () => { invalidate(); if (input.id === 'route-job') updateRoutes(); });
  }
}
addJob();
const initialEnd = new Date(Date.now() + 7 * 86400000);
$('campaign-end').value = new Date(initialEnd.getTime() - initialEnd.getTimezoneOffset() * 60000).toISOString().slice(0,16);
render();
try {
  const response = await fetch(new URL('../ascension-wallet/profile.json', import.meta.url), {cache:'no-store',redirect:'error'});
  if (!response.ok) throw Error('The deployment profile is missing. Build the shared wallet assets before serving the Studio.');
  const profile = parseBoundedJSON(await response.text()); defaultProfile = profile;
  registeredProfiles = availableProfiles(profile); profileOptions(); useProfile(profile);
  const query = new URLSearchParams(window.location.search);
  if (query.has('seed') || query.has('job')) {
    if (query.has('profile') && query.get('profile') !== client.profileIdentity) {
      const selected = selectBuildProfile(query.get('profile'), defaultProfile);
      if (unresolved(client.pending)) throw Error('Reconcile the outstanding action under its original profile before opening another deployment.');
      useProfile(selected); $('deployment-choice').value = client.profileIdentity;
    }
    if (query.has('chain') && query.get('chain') !== String(client.chainId)) throw Error('The link belongs to another deployment chain. No chain state was loaded.');
    if (query.has('seed')) { workflow.state.seedId = positive(query.get('seed'),256).toString(); $('open-seed-id').value = workflow.state.seedId; }
    if (query.has('job')) workflow.state.jobId = positive(query.get('job'),256).toString();
    go(3, false);
    status(text('Link identifiers loaded as unverified hints. Choose a provider and explicitly inspect to resume.', 'Identifiants du lien chargés comme indices non vérifiés. Choisissez un fournisseur et consultez explicitement pour reprendre.'));
  }
} catch (error) { profileError = explainError(error); status(profileError, true); }
render();
