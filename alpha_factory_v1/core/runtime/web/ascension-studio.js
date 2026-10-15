// SPDX-License-Identifier: Apache-2.0
'use strict';

const $ = id => document.getElementById(id);
const MAX_REQUEST_BYTES = 512 * 1024;
let accessToken = '', selected = null, installation = null, fileText = '', busy = false, epoch = 0, allRecords = [];
const english = Object.fromEntries([...document.querySelectorAll('[data-i18n]')].map(node => [node.dataset.i18n, node.textContent]));
const french = {
  budget: 'Budget de planification',

  ecosystem: 'Marchés et exécuteurs',
  freezeDownload: 'Télécharger le gel signé de l’évaluation pour Studio',
  firstInstall: 'Première installation avec les identités déjà vérifiées', firstInstallHelp: 'L’opérateur du poste effectue cette étape une fois. Choisissez les acteurs déjà installés et le déploiement vérifié. Les clés locales facultatives doivent déjà exister en privé avec leurs jetons d’approbation distincts. Ce formulaire ne crée aucune clé et ne remplace aucune configuration.', setupConfirm: 'Comme opérateur du poste, j’ai vérifié ces acteurs, clés privées et paramètres de lecture de la chaîne, et j’autorise cette première installation.', install: 'Installer les paramètres examinés',
  pairTitle: 'Apparier un nouveau travail', pairHelp: 'Choisissez un déploiement installé et le numéro réel de la graine. L’appariement prépare une institution bornée et les obligations exactes du cycle de vie. Toutes les obligations associées restent en attente; aucune autorisation d’exécution ni admission n’est créée.', pairTemplate: 'Déploiement et politique de rôles installés', pairSeed: 'Numéro réel de la graine', pairConfirm: 'Préparer ce travail exact avec la politique installée et l’allocation bornée sélectionnées.', pair: 'Apparier et préparer le travail exact',
  controllerApproval: 'Approbation du contrôleur sur ce poste', controllerHelp: 'Le contrôleur installé peut examiner la portée exacte et la signer avec son jeton d’approbation distinct. La signature ne lance pas l’exécution.', controllerToken: 'Jeton distinct du contrôleur', controllerConfirm: 'Comme contrôleur nommé, j’approuve et signe uniquement cette portée d’exécution exacte et figée.', controllerSign: 'Signer cette autorisation exacte', localRun: 'Exécuter avec l’autorisation signée conservée', reviewToken: 'Jeton distinct du responsable d’acceptation', reviewConfirm: 'Comme responsable d’acceptation nommé, je signe et enregistre la décision sélectionnée sur cet artefact exact.', localReview: 'Signer et enregistrer la décision locale sélectionnée',
  evaluationTitle: 'Figer et évaluer une amélioration', evaluationHelp: 'Pour un rapport numérique, choisissez une référence conservée avant d’exécuter un nouveau travail sur des entrées différentes. La comparaison figée vérifie les méthodes exactes et les limites de ressources du même rapport. Un résultat peut échouer ou rester non concluant; l’admission reste distincte.', baseline: 'Résultat de référence conservé', freezeEvaluation: 'Figer la comparaison avant l’exécution', evaluate: 'Évaluer la comparaison figée', evaluationDownload: 'Télécharger le rapport d’évaluation signé', evaluationDetails: 'Critères figés et preuves de l’évaluation',
  skip: 'Aller à l’espace de travail', local: 'OPÉRATEUR LOCAL', agent: 'Espace de l’agent', setup: 'Configuration', language: 'Langue',
  eyebrow: 'UN PROJET · AUTORITÉ EXPLICITE · PREUVES CONSERVÉES', title: 'Reliez votre travail à son exécuteur.',
  intro: 'Apportez le fichier de travail de Nova-Seed Studio à cet agent installé. Examinez les conditions exactes, vérifiez l’attribution, obtenez l’autorisation distincte du contrôleur et rapportez les preuves à votre projet.',
  boundary: 'Cette page utilise uniquement son propre serveur local. Un site hébergé ne peut pas se connecter à cet agent. Importer un fichier n’installe aucune confiance, n’accorde aucune permission, ne signe aucune transaction et ne démarre aucun travail.',
  connectTitle: 'Connectez-vous à votre agent installé', tokenHelp: 'Utilisez le jeton d’accès du fichier privé api.token de cet agent. Il reste en mémoire dans cette page et est effacé à la déconnexion.',
  token: 'Jeton d’accès', connect: 'Se connecter', installation: 'Autorité installée', refresh: 'Actualiser', disconnect: 'Se déconnecter', setupGuide: 'Lire le guide de configuration initiale', profiles: 'Profils de projet et de cycle installés',
  importTitle: 'Apportez votre projet', importHelp: 'Dans Nova-Seed Studio, téléchargez la demande destinée à l’exécuteur. Sélectionnez-la ici, puis examinez et préparez sa portée exacte. Les données sources restent dans le journal privé de cet agent.',
  requestFile: 'Demande de travail Studio (.json)', prepare: 'Examiner et préparer', inputDetails: 'Aperçu du fichier sélectionné', history: 'Continuer un travail conservé', historyHelp: 'Rouvrez une entrée après une actualisation ou une interruption. Consulter l’historique ne relance jamais l’exécution et ne restaure aucune permission.',
  exactScope: 'Demande exacte, travail préparé et graphe installé', sealTitle: 'Sceller avant la publication du travail',
  sealDownload: 'Télécharger le scellement signé avant publication pour Studio', sealReturn: 'Importez ce scellement exact dans Studio avant d’acheminer le travail. Les octets signés et la liaison au plan sont conservés.',
  sealHelp: 'Examinez le travail préparé et toutes les obligations associées. Le scellement enregistre les conditions exactes et observe la chaîne configurée. Il ne publie pas de travail et n’autorise pas l’exécution. La graine doit déjà être liée à ce plan; le travail ne doit pas encore avoir été publié.',
  sealConfirm: 'J’ai examiné ces conditions et le graphe installé, et j’autorise leur scellement avant publication.', seal: 'Sceller les conditions exactes',
  bindTitle: 'Vérifier la publication et l’attribution', bindHelp: 'Après la publication du travail scellé et la sélection d’un travailleur par l’entreprise, saisissez les références des transactions. Le nœud configuré vérifie le travail réel, le travailleur, l’indice du plan et les échéances. Une demande non signée est préparée pour le contrôleur de l’institution.',
  jobId: 'Numéro du travail sur le marché', worker: 'Portefeuille du travailleur attribué', posting: 'Transaction de publication', assignment: 'Transaction d’attribution', expiry: 'Expiration de l’autorisation (UTC, avant l’échéance du travail)', bind: 'Vérifier l’attribution et préparer la demande',
  runTitle: 'Obtenir l’autorisation du contrôleur, puis exécuter', runHelp: 'Transmettez la demande exacte au contrôleur installé par le canal de votre choix. Importez son enveloppe d’exécution signée. L’agent vérifie le signataire et toute la portée figée avant de démarrer. Aucune clé provenant du fichier n’est acceptée.',
  grantDownload: 'Télécharger la demande d’autorisation non signée', grantDetails: 'Portée exacte à autoriser par le contrôleur', grantFile: 'Enveloppe d’exécution signée par le contrôleur (.json)', runConfirm: 'J’autorise une exécution bornée de ce travail exact avec l’autorisation distincte signée par le contrôleur.', run: 'Vérifier l’autorisation et exécuter le travail exact',
  runLimits: 'Le travail pris en charge utilise l’exécuteur fixe installé, sans réseau, commande arbitraire, portefeuille ni navigateur personnel. Il s’agit d’un calcul réel, sans prétendre démontrer un modèle en direct ou un contrôle informatique sans restriction.',
  recoveryTitle: 'Examiner une transmission interrompue', recoveryHelp: 'Une réponse perdue peut laisser un résultat terminé dans le journal natif. Récupérez ce résultat exact sans réexécuter. Si aucun résultat terminé n’existe, le contrôleur doit traiter le travail interrompu et sa réservation de ressources par le processus de récupération établi.', recover: 'Récupérer le résultat natif terminé',
  resultTitle: 'Rapporter les preuves et demander une révision', resultHelp: 'Le résultat conserve les octets exacts de l’artefact, la demande, l’attribution et les signatures de livraison. Importez-le dans Nova-Seed Studio avec la clé publique de cet agent conservée séparément. Une évaluation négative exacte peut être acceptée comme travail sans adopter le candidat.',
  resultDownload: 'Télécharger le résultat Studio signé', reviewDecision: 'Décision locale à préparer', reviewAccept: 'Accepter le travail livré', reviewReject: 'Refuser le travail livré', acceptanceDownload: 'Télécharger la demande de révision locale', resultDetails: 'Artefact exact et signatures',
  acceptanceTitle: 'Enregistrer une acceptation locale distincte', acceptanceHelp: 'Le responsable d’acceptation installé examine l’artefact et signe la demande exacte. Importez son enveloppe job-acceptance signée pour clôturer la réservation des ressources. Cela ne remplace ni la révision des validateurs sur la chaîne ni un paiement.', acceptanceFile: 'Enveloppe signée par le responsable d’acceptation (.json)', acceptanceConfirm: 'Enregistrer cette décision distincte signée sur le travail livré exact.', accept: 'Vérifier et enregistrer la décision locale',
  settlementTitle: 'Observer la révision et le règlement sur la chaîne', settlementHelp: 'Après la livraison réelle au marché, la révision des validateurs et la clôture, saisissez la transaction de clôture. Le lecteur configuré rapproche l’artefact exact, les révisions, les remboursements, les paiements et les destructions. Cette opération lit uniquement la chaîne.', settlementTx: 'Transaction de clôture', settle: 'Vérifier le règlement', settlementDownload: 'Télécharger l’historique signé du règlement', settlementDetails: 'Détails du règlement vérifié', recordDetails: 'Dossier complet conservé par l’opérateur',
  footer: 'Acteurs explicites. Travail exact. Preuves récupérables. Un nouveau cycle exige son propre profil approuvé, sa propre attribution et sa propre autorisation. Aucune adoption ni aucun paiement automatique.', notice: 'Avis du projet',
};
const messages = {
  en: {
    ready: 'Installed profiles are available. Every work request still requires exact review and a separate execution grant.',
    setupNeeded: 'Setup is incomplete. An operator must install the project profile, trusted public identities and existing institution before preparation. Work files cannot supply that authority. Read the setup guide.',
    name: 'Journal identity', key: 'Public key to retain independently', control: 'Agent control', pause: 'Pause agent', resume: 'Resume agent',
    empty: 'No retained Studio work yet.', disconnected: 'Disconnected. Private page contents and token cleared.', connected: 'Connected. Select a work file or reopen a retained project.',
    invalidFile: 'Select a Studio work request JSON file.', tooLarge: 'The file exceeds 512 KiB. Reduce its bounded inputs before importing.', requestTooLarge: 'The encoded request exceeds the 512 KiB API limit, including JSON escaping and handoff fields. Reduce its inputs or formatting before importing.', signedTooLarge: 'The signed envelope exceeds 128 KiB.',
    changedSession: 'Connection changed. Reconnect and inspect retained history.', failed: 'Operation failed. Refresh the retained record and inspect its state before retrying.',
    waiting: 'Working. Keep this page open; if the response is lost, reconnect and open the retained record.',
    prepared: 'Prepared — no grant', sealed: 'Sealed — awaiting assignment', bound: 'Assignment verified — awaiting grant', running: 'Execution may be active', interrupted: 'Interrupted — recovery required', delivered: 'Delivered — review and settlement separate', settled: 'Settlement observed',
    nextPrepared: 'Review the exact scope and seal it before the marketplace job is posted.', nextSealed: 'Return to the business’s marketplace workflow to post and assign this sealed job, then verify both transactions here.',
    nextBound: 'The installed controller must separately sign the exact grant request. Import that signed grant and explicitly authorize the run.',
    nextRunning: 'Execution may still be running. Refresh first. Retrieving a retained result never starts another execution.', nextInterrupted: 'Retrieve an already completed result if available. Uncertain work requires the controller’s recovery decision; do not replay it.',
    nextDelivered: 'Return the signed result to Studio. Local acceptance, on-chain review, settlement and candidate adoption are separate decisions.',
    nextSettled: 'Inspect payouts, burns and refunds. Preserve this history. A distinct next mission needs its own explicit project/cycle profile, assignment and grant.',
    project: 'Project', cycle: 'Cycle', request: 'Exact request digest', chain: 'Chain', market: 'Marketplace', seed: 'Seed', controller: 'Grant controller', reviewer: 'Local acceptance owner',
    missingConfirmation: 'Review the terms and check the explicit confirmation before continuing.', selectEnvelope: 'Select the separately signed envelope first.',
    complete: 'Phase recorded. Inspect the retained evidence and next action.', verdict: 'Recorded candidate outcome: ', notAdopted: '. No candidate authority or adoption was granted.',
    accepted: 'Local work accepted; the exact runtime resource reservation has been reconciled.', rejected: 'Local work rejected; the exact runtime resource reservation has been reconciled.', pendingAcceptance: 'Local acceptance is pending. The runtime resource reservation remains separate from chain settlement.',
    settlement: 'Verified settlement status: ', outcome: ' · Work review: ', timestamp: 'Select an explicit UTC expiry before the job deadline.', selected: 'Selected request: ',
    paused: 'Agent paused. Active work stops at its next bounded checkpoint.', resumed: 'Agent resumed. No job was started.',
  },
  fr: {
    ready: 'Les profils installés sont disponibles. Chaque demande exige encore une révision exacte et une autorisation d’exécution distincte.',
    setupNeeded: 'Configuration incomplète. Un opérateur doit installer le profil du projet, les identités publiques de confiance et une institution existante. Les fichiers de travail ne peuvent fournir cette autorité. Consultez le guide.',
    name: 'Identité du journal', key: 'Clé publique à conserver séparément', control: 'État de l’agent', pause: 'Mettre l’agent en pause', resume: 'Reprendre l’agent',
    empty: 'Aucun travail Studio conservé.', disconnected: 'Déconnecté. Le contenu privé et le jeton ont été effacés de la page.', connected: 'Connecté. Sélectionnez un fichier ou rouvrez un projet conservé.',
    invalidFile: 'Sélectionnez un fichier JSON de demande Studio.', tooLarge: 'Le fichier dépasse 512 Kio. Réduisez ses entrées avant l’importation.', requestTooLarge: 'La demande encodée dépasse la limite de 512 Kio de l’API, avec les échappements JSON et les champs de transmission. Réduisez ses entrées ou sa mise en forme avant l’importation.', signedTooLarge: 'L’enveloppe signée dépasse 128 Kio.',
    changedSession: 'La connexion a changé. Reconnectez-vous et consultez l’historique.', failed: 'Échec de l’opération. Actualisez le dossier conservé et examinez son état avant de réessayer.',
    waiting: 'Opération en cours. Gardez cette page ouverte; si la réponse est perdue, reconnectez-vous et ouvrez le dossier conservé.',
    prepared: 'Préparé — sans autorisation', sealed: 'Scellé — attribution attendue', bound: 'Attribution vérifiée — autorisation attendue', running: 'Exécution peut-être active', interrupted: 'Interrompu — récupération requise', delivered: 'Livré — révision et règlement distincts', settled: 'Règlement observé',
    nextPrepared: 'Examinez la portée exacte et scellez-la avant la publication du travail sur le marché.', nextSealed: 'L’entreprise doit publier et attribuer ce travail scellé dans son parcours de marché; vérifiez ensuite les deux transactions ici.',
    nextBound: 'Le contrôleur installé doit signer séparément la demande exacte. Importez son autorisation signée et autorisez explicitement l’exécution.',
    nextRunning: 'L’exécution peut être en cours. Actualisez d’abord. Récupérer un résultat conservé ne lance jamais une autre exécution.', nextInterrupted: 'Récupérez un résultat déjà terminé s’il existe. Un travail incertain exige la décision de récupération du contrôleur; ne le relancez pas.',
    nextDelivered: 'Rapportez le résultat signé dans Studio. L’acceptation locale, la révision sur la chaîne, le règlement et l’adoption sont des décisions distinctes.',
    nextSettled: 'Examinez paiements, destructions et remboursements. Conservez cet historique. Une mission distincte exige son propre profil projet/cycle, sa propre attribution et sa propre autorisation.',
    project: 'Projet', cycle: 'Cycle', request: 'Empreinte exacte de la demande', chain: 'Chaîne', market: 'Marché', seed: 'Graine', controller: 'Contrôleur de l’autorisation', reviewer: 'Responsable d’acceptation locale',
    missingConfirmation: 'Examinez les conditions et cochez la confirmation explicite avant de continuer.', selectEnvelope: 'Sélectionnez d’abord l’enveloppe signée séparément.',
    complete: 'Étape enregistrée. Examinez les preuves conservées et la prochaine action.', verdict: 'Résultat du candidat enregistré : ', notAdopted: '. Aucune autorité ni adoption du candidat n’a été accordée.',
    accepted: 'Travail accepté localement; la réservation exacte des ressources a été rapprochée.', rejected: 'Travail refusé localement; la réservation exacte des ressources a été rapprochée.', pendingAcceptance: 'Acceptation locale en attente. La réservation des ressources reste distincte du règlement sur la chaîne.',
    settlement: 'État du règlement vérifié : ', outcome: ' · Révision du travail : ', timestamp: 'Choisissez une expiration UTC explicite avant l’échéance du travail.', selected: 'Demande sélectionnée : ',
    paused: 'Agent en pause. Le travail actif s’arrête au prochain point de contrôle borné.', resumed: 'Agent repris. Aucun travail n’a démarré.',
  },
};
const lang = () => $('language').value;
const t = key => messages[lang()][key] || key;
const pretty = value => JSON.stringify(value, null, 2);
const setupFields = [
  ['template-id','text','Policy name','Nom de la politique','bounded-work'],
  ['controller','controller','Trusted controller','Contrôleur vérifié',''], ['producer','producer','Trusted producer','Producteur vérifié',''], ['reviewer','acceptance','Trusted acceptance owner','Responsable d’acceptation vérifié',''],
  ['valid-until','datetime-local','Policy expiry (UTC)','Expiration de la politique (UTC)',''], ['max-calls','number','Maximum controllable calls per work item','Appels contrôlables maximaux par travail','7'],
  ['rpc-url','url','Operator-selected read-only RPC URL','URL RPC de lecture choisie par l’opérateur',''], ['chain-id','text','Chain ID','ID de chaîne','1'],
  ['market','text','Pinned marketplace address','Adresse du marché vérifiée',''], ['market-hash','text','Marketplace runtime Keccak-256','Keccak-256 du code du marché',''],
  ['token-hash','text','Token runtime Keccak-256','Keccak-256 du code du jeton',''], ['confirmations','number','Required confirmations','Confirmations requises','12'],
  ['mark','text','Pinned MARK address','Adresse MARK vérifiée',''], ['mark-hash','text','MARK runtime Keccak-256','Keccak-256 du code MARK',''],
  ['seed','text','Pinned NovaSeed address','Adresse NovaSeed vérifiée',''], ['seed-hash','text','NovaSeed runtime Keccak-256','Keccak-256 du code NovaSeed',''],
  ['scope','scope','Declared chain evidence scope','Portée déclarée des preuves de chaîne',''],
  ['controller-key','optional','Existing controller key file, relative to agent home (optional)','Fichier de clé du contrôleur dans le répertoire privé (facultatif)',''],
  ['controller-token-file','optional','Existing controller approval-token file (optional)','Fichier du jeton distinct du contrôleur (facultatif)',''],
  ['reviewer-key','optional','Existing acceptance key file, relative to agent home (optional)','Fichier de clé d’acceptation dans le répertoire privé (facultatif)',''],
  ['reviewer-token-file','optional','Existing acceptance approval-token file (optional)','Fichier du jeton distinct d’acceptation (facultatif)',''],
];
function setupForm() {
  for (const [id, type, en, fr, initial] of setupFields) {
    let field = $('setup-' + id), label = $('setup-label-' + id);
    if (!field) {
      const box = document.createElement('div'); label = document.createElement('label'); label.id = 'setup-label-' + id; label.htmlFor = 'setup-' + id;
      const choices = ['controller','producer','acceptance','scope'].includes(type);
      field = document.createElement(choices ? 'select' : 'input'); field.id = 'setup-' + id;
      if (choices) {
        const options = type === 'scope' ? [{principal:'operator-configured-chain'},{principal:'disposable-local-fixture'}] : installation.setup_roles.filter(item => item.roles.includes(type));
        for (const item of options) {const option = document.createElement('option'); option.value = item.principal; option.textContent = item.principal; field.append(option);}
      } else {field.type = type === 'optional' ? 'text' : type; field.value = initial; if (type === 'datetime-local') field.step = '1';}
      field.required = type !== 'optional'; if (type === 'number') {field.min = '1'; field.max = id === 'max-calls' ? '100' : '1024';}
      box.append(label, field); $('setup-fields').append(box);
    }
    label.textContent = lang() === 'fr' ? fr : en;
  }
  for (const prefix of ['controller','reviewer']) {
    const choose = () => {
      const role = installation.setup_roles.find(item => item.principal === $('setup-' + prefix).value);
      $('setup-' + prefix + '-token-file').value = role?.approval_token_file || '';
      $('setup-' + prefix + '-token-file').readOnly = true;
    };
    $('setup-' + prefix).onchange = choose; choose();
  }
}
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
function entries(node, values) {
  node.replaceChildren(...values.flatMap(([key, value]) => {
    const label = document.createElement('dt'), content = document.createElement('dd');
    label.textContent = key; content.textContent = String(value ?? '—'); return [label, content];
  }));
}
async function api(path, options = {}) {
  if (typeof options.body === 'string' && new TextEncoder().encode(options.body).byteLength > MAX_REQUEST_BYTES) {
    throw new Error(t('requestTooLarge'));
  }
  const started = epoch;
  const response = await fetch('/api' + path, {...options, headers: {
    Authorization: 'Bearer ' + accessToken, 'Content-Type': 'application/json', ...(options.headers || {}),
  }});
  const body = await response.json();
  if (started !== epoch) throw new Error(t('changedSession'));
  if (!response.ok) throw new Error(typeof body.error === 'string' ? body.error : typeof body.detail === 'string' ? body.detail : t('failed'));
  return body;
}
function setBusy(value) {
  busy = value; document.body.classList.toggle('busy', value);
  for (const node of document.querySelectorAll('#workspace button, #workspace input, #workspace select')) {
    if (['pause', 'disconnect'].includes(node.id)) continue;
    node.disabled = value;
  }
  if (!value) $('prepare').disabled = !installation?.configured;
  $('workspace').setAttribute('aria-busy', String(value));
}
async function guarded(action) {
  if (busy) return;
  setBusy(true);
  try { await action(); } catch (error) { if (accessToken) message(error.message, true); else message(t('disconnected')); }
  finally { setBusy(false); }
}
function download(name, value) {
  const url = URL.createObjectURL(new Blob([pretty(value)], {type: 'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderInstallation() {
  if (!installation) return;
  $('prerequisite').textContent = t(installation.configured ? 'ready' : 'setupNeeded');
  entries($('installation'), [[t('name'), installation.identity], [t('key'), installation.public_key], [t('control'), installation.control]]);
  $('profiles').textContent = pretty(installation.profiles);
  $('first-install').hidden = installation.configured || !installation.setup_roles?.length;
  if (!$('first-install').hidden) setupForm();
  $('pairing-panel').hidden = !installation.templates?.length;
  const selectedTemplate = $('pair-template').value;
  $('pair-template').replaceChildren(...(installation.templates || []).map(template => {
    const option = document.createElement('option'); option.value = template.template_id;
    option.textContent = template.template_id + ' · ' + template.controller + ' · calls ≤ ' + template.max_calls;
    return option;
  }));
  if ([...$('pair-template').options].some(option => option.value === selectedTemplate)) $('pair-template').value = selectedTemplate;
  $('profiles').textContent = pretty({profiles:installation.profiles, templates:installation.templates});
  $('pause').textContent = t(installation.control === 'paused' ? 'resume' : 'pause');
  $('prepare').disabled = busy || !installation.configured;
}
function render(record) {
  selected = record; $('selected').hidden = false;
  $('project-label').textContent = t(record.state);
  $('goal').textContent = record.request.plan.jobs[record.request.plan_index].spec.goal;
  const context = record.market_context;
  entries($('context'), [[t('project'), record.project_id], [t('cycle'), record.cycle_id], [t('request'), record.request_digest],
    [t('chain'), context.chain_id], [t('market'), context.market], [t('seed'), context.seed_id],
    [t('controller'), record.controller], [t('reviewer'), record.prepared.job_contract.acceptance_owner]]);
  const next = {prepared:'nextPrepared',sealed:'nextSealed',bound:'nextBound',running:'nextRunning',interrupted:'nextInterrupted',delivered:'nextDelivered',settled:'nextSettled'};
  $('next-action').textContent = t(next[record.state]);
  $('phases').replaceChildren(...['prepared','sealed','bound','delivered','settled'].map(state => {
    const li = document.createElement('li'); li.textContent = t(state);
    if (state === record.state || (state === 'bound' && ['running','interrupted'].includes(record.state))) li.setAttribute('aria-current', 'step');
    return li;
  }));
  $('scope').textContent = pretty({request:record.request, prepared:record.prepared, graph:record.graph});
  $('record-preview').textContent = pretty(record);
  $('seal-panel').hidden = record.state !== 'prepared'; $('seal-confirm').checked = false;
  $('seal-export-panel').hidden = !record.seal;
  $('bind-panel').hidden = record.state !== 'sealed';
  $('grant-panel').hidden = record.state !== 'bound'; $('grant-preview').textContent = record.grant_request ? pretty(record.grant_request) : '';
  $('local-grant').hidden = !installation?.local_signers?.includes(record.controller);
  $('local-run-form').hidden = !record.signed_authorization;
  $('controller-token').value = ''; $('controller-confirm').checked = false; $('local-run-confirm').checked = false;
  $('grant-file').value = ''; $('run-confirm').checked = false;
  $('recovery-panel').hidden = !['running','interrupted'].includes(record.state);
  $('result-panel').hidden = !record.result;
  if (record.result) {
    $('verdict').textContent = t('verdict') + record.result.candidate_verdict + t('notAdopted');
    $('result-preview').textContent = pretty(record.result);
    $('acceptance-panel').hidden = Boolean(record.local_acceptance);
    $('local-review-form').hidden = !installation?.local_signers?.includes(record.prepared.job_contract.acceptance_owner);
    $('acceptance-status').textContent = t(record.local_acceptance ? (record.local_acceptance.payload.accepted ? 'accepted' : 'rejected') : 'pendingAcceptance');
    $('acceptance-download').disabled = !record.review_requests || busy;
  }
  $('accept-file').value = ''; $('accept-confirm').checked = false;
  $('review-token').value = ''; $('review-confirm').checked = false;
  $('settlement-panel').hidden = !record.settlement;
  if (record.settlement) {
    $('settlement-summary').textContent = t('settlement') + record.settlement.settlement_status + t('outcome') + record.settlement.job_acceptance;
    $('settlement-preview').textContent = pretty(record.settlement);
  }
  $('evaluation-panel').hidden = record.request.work_spec.family !== 'numerical';
  $('evaluation-form').hidden = Boolean(record.evaluation_freeze) || !['prepared','sealed','bound'].includes(record.state);
  $('evaluate').hidden = !record.evaluation_freeze || !record.result;
  $('freeze-download').hidden = !record.evaluation_freeze;
  $('evaluation-download').hidden = !record.evaluation;
  $('evaluation-preview').textContent = pretty({freeze:record.evaluation_freeze || null, report:record.evaluation || null});
  $('baseline').replaceChildren(...allRecords.filter(item => item.request_digest !== record.request_digest && item.family === 'numerical' && ['delivered','settled'].includes(item.state)).map(item => {
    const option = document.createElement('option'); option.value = item.request_digest; option.textContent = item.project_id.slice(0,8) + ' · ' + item.cycle_id.slice(0,8) + ' · ' + item.plan_index; return option;
  }));
}
async function refresh() {
  installation = await api('/ascension-studio/status'); renderInstallation();
  const records = await api('/ascension-studio/work');
  allRecords = records;
  $('history').replaceChildren(...records.map(record => {
    const row = document.createElement('button'); row.className = 'mission-row';
    const title = document.createElement('span'), state = document.createElement('small');
    title.textContent = record.project_id.slice(0, 8) + ' · ' + record.cycle_id.slice(0, 8) + ' · ' + record.plan_index; state.textContent = t(record.state); row.append(title, state);
    row.addEventListener('click', () => guarded(async () => {render(await api('/ascension-studio/work/' + record.request_digest));}));
    return row;
  }));
  if (!records.length) $('history').textContent = t('empty');
  if (selected) render(await api('/ascension-studio/work/' + selected.request_digest));
}
async function mutate(action, extra) {
  if (!selected) throw new Error(t('invalidFile'));
  message(t('waiting'));
  const record = await api('/ascension-studio/' + action, {method:'POST', body:JSON.stringify({request_digest:selected.request_digest, revision:selected.revision, ...extra})});
  render(record); await refresh(); message(t('complete'));
}
async function envelope(input) {
  const file = input.files[0]; if (!file) throw new Error(t('selectEnvelope'));
  if (file.size > 128 * 1024) throw new Error(t('signedTooLarge'));
  return file.text();
}
$('language').addEventListener('change', () => {
  document.documentElement.lang = lang();
  for (const node of document.querySelectorAll('[data-i18n]')) node.textContent = (lang() === 'fr' ? french : english)[node.dataset.i18n] || english[node.dataset.i18n];
  renderInstallation(); if (selected) render(selected); if (accessToken && !busy) guarded(refresh);
});
$('login-form').addEventListener('submit', event => {
  event.preventDefault(); guarded(async () => {
    epoch++; accessToken = $('token').value.trim(); $('token').value = '';
    try {await refresh();} catch (error) {accessToken = ''; throw error;}
    $('login').hidden = true; $('workspace').hidden = false; message(t('connected'));
  });
});
$('disconnect').addEventListener('click', () => {
  epoch++; accessToken = ''; selected = null; installation = null; fileText = ''; allRecords = [];
  $('workspace').hidden = true; $('login').hidden = false; $('selected').hidden = true;
  for (const node of document.querySelectorAll('#workspace pre, #workspace dl, #history, #file-summary')) node.replaceChildren();
  for (const input of document.querySelectorAll('#workspace input')) {input.value = ''; if (input.type === 'checkbox') input.checked = false;}
  $('token').value = ''; message(t('disconnected'));
});
$('pause').addEventListener('click', async () => {
  if (!installation) return;
  try {
    const paused = installation.control !== 'paused';
    await api('/control', {method:'POST',body:JSON.stringify({state:paused ? 'paused' : 'ready'})});
    installation.control = paused ? 'paused' : 'ready'; renderInstallation(); message(t(paused ? 'paused' : 'resumed'));
  } catch (error) {message(error.message, true);}
});
$('refresh').addEventListener('click', () => guarded(refresh));
$('request-file').addEventListener('change', () => guarded(async () => {
  fileText = ''; $('input-preview').textContent = ''; $('file-summary').textContent = '';
  const file = $('request-file').files[0]; if (!file) return;
  if (file.size > MAX_REQUEST_BYTES) throw new Error(t('tooLarge'));
  const raw = await file.text(), value = JSON.parse(raw);
  if (value.schema !== 'agialpha.ascension.studio-work.v1') throw new Error(t('invalidFile'));
  fileText = raw; $('input-preview').textContent = pretty(value); $('file-summary').textContent = t('selected') + value.project_id + ' · ' + value.cycle_id;
}));
$('import-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  if (!fileText) throw new Error(t('invalidFile')); message(t('waiting'));
  render(await api('/ascension-studio/import', {method:'POST',body:JSON.stringify({request_json:fileText})}));
  await refresh(); message(t('complete'));
});});
$('seal').addEventListener('click', () => guarded(async () => {
  if (!$('seal-confirm').checked) throw new Error(t('missingConfirmation'));
  await mutate('seal', {confirm:true});
}));
$('bind-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  const value = $('expires').value;
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?$/.test(value)) throw new Error(t('timestamp'));
  const expires = value.length === 16 ? value + ':00Z' : value + 'Z';
  await mutate('bind', {market_job_id:$('job-id').value, posting_tx:$('posting-tx').value, assignment_tx:$('assignment-tx').value, acting_identity:$('worker').value, expires_at:expires});
});});
$('grant-download').addEventListener('click', () => {if (selected?.grant_request) download('ascension-grant-request-' + selected.cycle_id + '.json', selected.grant_request);});
$('seal-download').addEventListener('click', () => {if (selected?.seal) download('ascension-preposting-seal-' + selected.cycle_id + '.json', selected.seal);});
$('run-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  if (!$('run-confirm').checked) throw new Error(t('missingConfirmation'));
  await mutate('run-import', {authorization_json:await envelope($('grant-file')),confirm:true});
});});
$('recover').addEventListener('click', () => guarded(() => mutate('recover', {})));
$('result-download').addEventListener('click', () => guarded(async () => {
  download('ascension-result-' + selected.cycle_id + '.json', await api('/ascension-studio/work/' + selected.request_digest + '/export'));
}));
$('acceptance-download').addEventListener('click', () => {
  const choice = $('review-decision').value, request = selected?.review_requests?.[choice];
  if (request) download('ascension-review-' + choice + '-' + selected.cycle_id + '.json', request);
});
$('accept-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  if (!$('accept-confirm').checked) throw new Error(t('missingConfirmation'));
  await mutate('accept-import', {acceptance_json:await envelope($('accept-file')),confirm:true});
});});
$('settle-form').addEventListener('submit', event => {event.preventDefault(); guarded(() => mutate('settle', {settlement_tx:$('settlement-tx').value}));});
$('settlement-download').addEventListener('click', () => guarded(async () => {
  download('ascension-settlement-' + selected.cycle_id + '.json', await api('/ascension-studio/work/' + selected.request_digest + '/settlement'));
}));
$('pair-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  if (!fileText) throw new Error(t('invalidFile'));
  if (!$('pair-confirm').checked) throw new Error(t('missingConfirmation'));
  render(await api('/ascension-studio/pair', {method:'POST',body:JSON.stringify({request_json:fileText,template_id:$('pair-template').value,seed_id:$('pair-seed').value,confirm:true})}));
  await refresh(); message(t('complete'));
});});
$('controller-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  if (!$('controller-confirm').checked) throw new Error(t('missingConfirmation'));
  const token = $('controller-token').value; $('controller-token').value = '';
  await mutate('sign-grant', {approval_token:token,confirm:true});
});});
$('local-run-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  if (!$('local-run-confirm').checked) throw new Error(t('missingConfirmation'));
  await mutate('run-signed', {confirm:true});
});});
$('local-review-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  if (!$('review-confirm').checked) throw new Error(t('missingConfirmation'));
  const token = $('review-token').value; $('review-token').value = '';
  await mutate('sign-review', {approval_token:token,decision:$('review-decision').value,confirm:true});
});});
$('evaluation-form').addEventListener('submit', event => {event.preventDefault(); guarded(() => mutate('freeze-evaluation', {baseline_request_digest:$('baseline').value,evaluation_id:crypto.randomUUID()}));});
$('evaluate').addEventListener('click', () => guarded(() => mutate('evaluate', {})));
$('evaluation-download').addEventListener('click', () => {if (selected?.evaluation) download('ascension-evaluation-' + selected.cycle_id + '.json', selected.evaluation);});
$('freeze-download').addEventListener('click', () => {if (selected?.evaluation_freeze) download('ascension-evaluation-freeze-' + selected.cycle_id + '-' + selected.request.plan_index + '.json', selected.evaluation_freeze);});
$('setup-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  if (!$('setup-confirm').checked) throw new Error(t('missingConfirmation'));
  const value = id => $('setup-' + id).value;
  const expiry = value('valid-until'); if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?$/.test(expiry)) throw new Error(t('timestamp'));
  const template = {template_id:value('template-id'),controller:value('controller'),producer:value('producer'),acceptance_owner:value('reviewer'),valid_until:expiry + (expiry.length === 16 ? ':00Z' : 'Z'),rpc_url:value('rpc-url'),max_calls:Number(value('max-calls')),
    market_context:{chain_id:value('chain-id'),market:value('market'),market_code_hash:value('market-hash'),token_code_hash:value('token-hash'),confirmations:Number(value('confirmations')),scope:value('scope'),mark:value('mark'),mark_code_hash:value('mark-hash'),seed:value('seed'),seed_code_hash:value('seed-hash'),seed_id:'1'}};
  const signers = [];
  for (const [prefix, principal] of [['controller',template.controller],['reviewer',template.acceptance_owner]]) {
    if (value(prefix + '-key')) {
      const signer = {principal,key_file:value(prefix + '-key'),approval_token_file:value(prefix + '-token-file')};
      const existing = signers.find(item => item.principal === principal);
      if (existing && pretty(existing) !== pretty(signer)) throw new Error(t('failed'));
      if (!existing) signers.push(signer);
    }
  }
  installation = await api('/ascension-studio/install', {method:'POST',body:JSON.stringify({template,signers,confirm:true})});
  await refresh(); message(t('complete'));
});});
