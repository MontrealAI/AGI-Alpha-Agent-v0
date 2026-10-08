// SPDX-License-Identifier: Apache-2.0
import {newRequest, validateRequest, parseBounded, digest, discover, freeze, evaluate, renew, verifyNative} from './engine.mjs';
const $ = id => document.getElementById(id);
const english = Object.fromEntries([...document.querySelectorAll('[data-i18n]')].map(el => [el.dataset.i18n, el.textContent]));
english.title = 'Intelligence earns its next chapter.';
const french = {
    skip:'Aller à la mission',language:'Langue',demos:'Tous les laboratoires',guide:'Guide pratique',eyebrow:'α-AGI ASCENSION → SUCCESSOR Ω',title:'L’intelligence mérite son prochain chapitre.',lead:'Construire une capacité utile. Examiner la version exacte. Préserver les acquis. Chaque successeur doit obtenir sa propre autorisation.',enter:'Commencer une mission ↗',noaccount:'Sans compte, portefeuille, clé API ni téléchargement de modèle.',scope:'RÉPÉTITION LOCALE · Calcul réel sur des données publiques synthétiques. Les temps du navigateur sont descriptifs. Aucune preuve indépendante ni autorité opérationnelle.',missionlabel:'ESPACE DE MISSION',missiontitle:'Des métriques exactes. Puis de meilleures performances.',restart:'Recommencer',choose:'Choisir',underwrite:'Engager',discover:'Explorer',freeze:'Figer',evaluate:'Évaluer',decide:'Décider',renew:'Renouveler',inputs:'01 / Définir le programme de preuve',mission:'Mission',missionhelp:'Compter les événements, sommer et maximiser leur durée, compter les erreurs par jour et service. Résultats exacts et rejet des données invalides obligatoires.',seed:'Graine',events:'Événements par charge',candidates:'Budget de candidats',trials:'Essais appariés de renouvellement',strategy:'Décision d’engagement',buildoption:'Construire · comparaison bornée',retainoption:'Conserver Current',repairoption:'Réparer · évaluer l’intervention simple',rentoption:'Louer · demander des preuves au fournisseur',partneroption:'Collaborer · demander des preuves au partenaire',reserveoption:'Réserver les ressources',stopoption:'Arrêter',underwritebutton:'Consigner l’engagement borné',underwritehelp:'Cette décision autorise seulement ce programme de preuve dans le navigateur. Aucun fonds dépensé ni permission de production accordée.',constitution:'Constitution de mission',constitutiontext:'Événements synthétiques publics; au plus 20 000 événements, huit compositions uniques et six essais appariés. Aucun réseau, fichier, identifiant ni code arbitraire de candidat. Arrêt si résultat incorrect. Coûts humains, monétaires et pic mémoire non mesurés.',alternatives:'02 / Current et solutions crédibles',currenttitle:'Un passage. Groupes exacts.',currenttext:'Un accumulateur compétent par dictionnaire. Le conserver est une issue valide.',betatitle:'Trier. Réduire. Comparer.',betatext:'Une réduction triée indépendante, avec les mêmes données et obligations d’exactitude.',challengertitle:'Composer un spécialiste.',challengertext:'Construire des combinaisons distinctes de tables, caches et mises à jour dans une grammaire bornée.',actions:'03 / Exécuter la prochaine obligation de preuve',discoverbutton:'Lancer l’exploration',freezebutton:'Figer le candidat exact',evaluatebutton:'Évaluer de nouvelles charges',cancel:'Annuler',empty:'Consignez l’engagement pour commencer. Chaque transition produit des preuves et ouvre l’étape suivante.',inspect:'Examiner les manifestes et preuves exacts',decisiontitle:'04 / Décision responsable et continuité',principal:'Étiquette du décideur local (sans données personnelles)',decision:'Décision',holdoption:'Attendre · obtenir les preuves manquantes',currentoption:'Conserver Current',betaoption:'Conserver Beta pour qualification',recordbutton:'Consigner la décision locale',renewbutton:'Préserver et lancer la génération deux',exportbutton:'Exporter toutes les preuves',decisionhelp:'Les étiquettes locales ne sont pas des identités authentifiées. Ce journal est un dossier de répétition. Chaque génération commence sans preuve active ni autorité.',nativeeyebrow:'NAVIGATEUR ↔ CLI INSTALLÉE',nativetitle:'Exécuter la requête exacte dans votre environnement.',nativehelp:'Téléchargez une requête validée, exécutez la commande installée et importez son résultat. Le navigateur vérifie le lien à la requête originale et le condensat des preuves. Un condensat atteste la cohérence, pas l’authenticité ni l’indépendance.',nativeisolation:'La commande native exécute des moteurs fixes. Le code arbitraire nécessite l’exécuteur Docker configuré séparément; aucun repli sur l’hôte.',requestexport:'Télécharger request.json',requestimport:'Restaurer le fichier request.json original',resultimport:'Importer le fichier result.json natif',trustkey:'Clé publique fiable facultative (hex, fournie séparément)',nativeempty:'Aucun résultat natif importé. Les clés contenues dans les preuves ne sont jamais automatiquement fiables.',nativeinspect:'Examiner les preuves natives importées',help:'Première utilisation, hors ligne et récupération',helptext:'Ouvrez cette page en ligne une fois et attendez « Cache hors ligne prêt ». Les visites suivantes peuvent exécuter les moteurs sans connexion. La première visite exige le site ou un paquet servi sur localhost. Aucun modèle facultatif requis. Les paramètres sont conservés localement; après rechargement, réexécutez les preuves. Exportez avant d’effacer les données du navigateur.',readguide:'Lire le guide complet anglais / français ↗',footer:'Travail utile. Continuité responsable.',disclaimer:'Avis relatif à la recherche'
};
const messages = {
    ready:['Choose your bounds and record underwriting. Current remains the serving reference.','Choisissez les limites et consignez l’engagement. Current reste la référence active.'],
    stale:['Inputs changed. Prior dependent results are stale; record new underwriting before continuing.','Paramètres modifiés. Les résultats dépendants sont périmés; consignez un nouvel engagement.'],
    underwritten:['Bounded programme recorded. Next: construct and measure distinct challengers.','Programme borné consigné. Ensuite : construire et mesurer des candidats distincts.'],
    alternative:['Decision recorded. This option needs no candidate run; missing supplier or partner evidence remains unavailable.','Décision consignée. Aucun candidat nécessaire; les preuves manquantes du fournisseur ou partenaire restent indisponibles.'],
    discovering:['Constructing candidates and testing the WORLD prediction…','Construction des candidats et examen de la prédiction WORLD…'],
    discovered:['Discovery complete. Inspect attempts, then freeze the exact selected challenger.','Exploration terminée. Examinez les essais puis figez le candidat exact.'],
    frozen:['Exact candidate, engine, request, comparators and protocol frozen. Next: fresh local evaluation.','Candidat, moteur, requête, comparateurs et protocole figés. Ensuite : évaluation locale nouvelle.'],
    evaluating:['Evaluating fresh workloads. A correctness failure overrides any speed improvement.','Évaluation de nouvelles charges. Un résultat incorrect annule tout gain de vitesse.'],
    evaluated:['Evaluation complete. HOLD: independent proof, frontier evidence, costs and operational authority are missing. Record a local decision.','Évaluation terminée. ATTENTE : preuve indépendante, comparateur de pointe, coûts et autorité manquants. Consignez une décision locale.'],
    decided:['Local decision recorded without a production grant. Preserve permitted methods and run matched renewal trials.','Décision locale consignée sans permission de production. Préservez les méthodes permises et lancez les essais appariés.'],
    renewing:['Generation two: matched treatment/control formation trials. Proof and authority start empty.','Génération deux : essais de formation traitement/témoin. Preuve et autorité initialement vides.'],
    renewed:['Two-generation record complete. Export the evidence. Equal formation effort is a valid result; no compounding claim is earned.','Dossier de deux générations terminé. Exportez les preuves. Un effort égal est valide; aucun gain récursif démontré.'],
    cancelled:['Execution cancelled. Completed earlier stages remain inspectable; retry the interrupted step.','Exécution annulée. Les étapes antérieures restent consultables; relancez l’étape interrompue.'],
    restored:['Original request restored. Rerun evidence, or import its native return. No authority restored.','Requête originale restaurée. Réexécutez les preuves ou importez le résultat natif. Aucune autorité restaurée.'],
    cache:['Offline cache ready. Fixed browser engines are available on cached visits.','Cache hors ligne prêt. Moteurs fixes disponibles lors des visites en cache.'],
    cachefail:['Offline cache unavailable. Keep an online connection or serve the downloaded site package on localhost.','Cache hors ligne indisponible. Restez connecté ou servez le paquet téléchargé sur localhost.']
};
let language = 'en', request, state = {}, stage = 'choose', controller = null, serial = 0, inputRevision = 0;
let nativeEnvelope = null;
const t = (en, fr) => language === 'fr' ? fr : en;
function translate() {
    document.documentElement.lang = language; $('language').value = language;
    for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = (language === 'fr' ? french : english)[el.dataset.i18n] || english[el.dataset.i18n];
    $('progress').setAttribute('aria-label', t('Execution progress', 'Progression de l’exécution'));
}
function status(key, error = false) {
    $('status').textContent = messages[key] ? messages[key][language === 'fr' ? 1 : 0] : key;
    $('status').classList.toggle('error', error);
}
function save() { try { localStorage.setItem('successor-request-v1', JSON.stringify(request)); } catch { /* optional recovery storage */ } }
function readInputs() {
    for (const id of ['seed', 'events', 'candidates', 'trials']) if ($(id).value === '' || !$(id).checkValidity()) throw Error(t('Enter an integer within every displayed bound.', 'Saisissez un entier dans chaque limite affichée.'));
    return newRequest({seed: Number($('seed').value), max_events: Number($('events').value), max_candidates: Number($('candidates').value), formation_trials: Number($('trials').value), language});
}
function controls() {
    const busy = Boolean(controller);
    $('underwrite').disabled = busy;
    $('discover').disabled = busy || !state.underwriting || !['build', 'repair'].includes(state.underwriting.choice) || Boolean(state.discovery);
    $('freeze').disabled = busy || !state.discovery || Boolean(state.frozen);
    $('evaluate').disabled = busy || !state.frozen || Boolean(state.evaluation);
    $('record').disabled = busy || !state.evaluation || Boolean(state.decision);
    $('principal').disabled = busy || Boolean(state.decision); $('decision').disabled = busy || Boolean(state.decision);
    $('renew').disabled = busy || !state.decision || Boolean(state.renewal);
    $('export').disabled = busy || !state.underwriting;
    $('cancel').hidden = !busy; $('progress').hidden = !busy;
    for (const el of document.querySelectorAll('[data-step]')) {
        if (el.dataset.step === stage) el.setAttribute('aria-current', 'step'); else el.removeAttribute('aria-current');
    }
}
function clearNative() { nativeEnvelope = null; $('native-evidence').textContent = '{}'; $('native-status').textContent = (language === 'fr' ? french : english).nativeempty; }
function invalidate() {
    inputRevision++; serial++; controller?.abort(); controller = null; state = {}; stage = 'choose'; request = null;
    clearNative(); status('stale'); render(); controls();
}
function add(parent, tag, text, className) {
    const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; parent.append(node); return node;
}
function render() {
    const box = $('results'); box.replaceChildren();
    if (state.discovery) {
        add(box, 'h4', t('Challengers constructed, not replayed', 'Candidats construits, sans rejeu'), 'result-head');
        add(box, 'p', t(`${state.discovery.actual_candidates} unique compositions. WORLD prediction: nested maps reduce tuple-key serialization; actual development time determines selection.`, `${state.discovery.actual_candidates} compositions uniques. Prédiction WORLD : les tables imbriquées réduisent la sérialisation; le temps mesuré guide la sélection.`), 'quiet');
        const scroll = add(box, 'div', '', 'table-scroll'), table = add(scroll, 'table', '');
        const head = table.createTHead().insertRow();
        for (const label of [t('Composition', 'Composition'), t('Correct', 'Exact'), t('Development ms', 'Développement ms')]) add(head, 'th', label);
        for (const a of state.discovery.attempts) {
            const row = table.createTBody().insertRow();
            add(row, 'td', `${a.config.layout} / cache:${a.config.cache_last} / ${a.config.update}`);
            add(row, 'td', a.correctness ? t('Passed', 'Réussi') : t('Failed', 'Échec'));
            add(row, 'td', (a.elapsed_ns / 1000000).toFixed(3));
        }
    } else add(box, 'p', (language === 'fr' ? french : english).empty, 'quiet');
    if (state.frozen) add(box, 'p', t('Frozen release: ', 'Version figée : ') + state.frozen.release_hash.slice(0, 20) + '…', 'quiet');
    if (state.evaluation) {
        const evaluation = state.evaluation;
        add(box, 'h4', t('HOLD · qualification remains open', 'ATTENTE · qualification en cours'), 'result-head');
        add(box, 'p', t('Measured local outcome: ', 'Résultat local mesuré : ') + evaluation.local_verdict, 'quiet');
        const grid = add(box, 'div', '', 'result-meta');
        for (const name of ['current', 'beta', 'candidate']) {
            const cell = add(grid, 'div', ''); add(cell, 'b', (evaluation.totals_ns[name] / 1000000).toFixed(2) + ' ms'); add(cell, 'span', name.toUpperCase());
        }
        add(box, 'p', t('Six fresh workloads; exact-output hard gate: ', 'Six nouvelles charges; exactitude obligatoire : ') + (evaluation.correctness ? t('passed.', 'réussie.') : t('failed.', 'échec.')), 'quiet');
        add(box, 'p', t('Browser timer resolution, JIT, run order and device load confound timings. Peak memory, review burden and money are unknown. Neither a local speedup nor a signature establishes independent Alpha.', 'La résolution de l’horloge, le JIT, l’ordre et la charge influencent les temps. Pic mémoire, effort de révision et coûts monétaires inconnus. Ni un gain local ni une signature n’établit un Alpha indépendant.'), 'quiet');
    }
    if (state.decision) add(box, 'p', t('Recorded local decision: ', 'Décision locale consignée : ') + state.decision.choice + t(' · authority: none', ' · autorité : aucune'), 'quiet');
    if (state.renewal) add(box, 'p', t(`${state.renewal.trials.length} matched formation trials complete. Generation two inherits a configuration-order hint; active proof and grants remain empty.`, `${state.renewal.trials.length} essais appariés terminés. La génération deux hérite d’un ordre suggéré; preuve active et permissions restent vides.`), 'quiet');
    $('evidence').textContent = JSON.stringify({request, ...state}, null, 2);
}
function errorText(error) {
    const translations = {
        'Invalid versioned rehearsal request':'Requête de répétition versionnée invalide',
        'Import exceeds 2 MB':'Le fichier dépasse 2 Mo',
        'Duplicate JSON key':'Clé JSON dupliquée',
        'Import complexity exceeds limit':'La complexité du fichier dépasse la limite',
        'Malformed Unicode':'Unicode malformé',
        'Expected integer JSON value':'Une valeur JSON entière est requise',
        'Unsafe integer':'Entier non représentable exactement',
        'Trailing JSON content':'Contenu JSON supplémentaire',
        'Unsupported native evidence envelope':'Format natif de preuve non pris en charge',
        'Native result belongs to a different request':'Le résultat natif appartient à une autre requête',
        'Authenticated evidence request or scope mismatch':'La requête ou la portée authentifiée ne correspond pas',
        'Native evidence digest mismatch':'Le condensat des preuves natives ne correspond pas',
        'Malformed native signature':'Signature native malformée',
        'Invalid native signature':'Signature native invalide',
        'Trusted key must be 32-byte lowercase hex':'La clé fiable doit contenir 32 octets hexadécimaux en minuscules',
        'No matching trusted signature':'Aucune signature fiable correspondante',
        'Invalid trusted signature':'Signature fiable invalide',
        'Engine source unavailable':'Source du moteur indisponible'
    };
    return language === 'fr' ? (translations[error.message] || error.message) : error.message;
}
async function action(work) {
    const revision = inputRevision;
    try { await work(); } catch (error) { if (revision !== inputRevision || error.name === 'StaleError') return; status(error.name === 'AbortError' ? 'cancelled' : t('Blocked: ', 'Bloqué : ') + errorText(error), true); } finally { if (revision !== inputRevision && !request) { state = {}; stage = 'choose'; status('stale'); } render(); controls(); if (revision === inputRevision && !controller) $('status').focus({preventScroll:true}); }
}
async function running(key, work) {
    const ticket = ++serial; controller = new AbortController(); const signal = controller.signal; status(key); controls();
    $('progress').value = 0; $('progress').max = 1;
    const onProgress = (value, max) => { if (ticket === serial) { $('progress').value = value; $('progress').max = max; } };
    try { const result = await work({signal, onProgress}); if (signal.aborted) throw new DOMException('Cancelled', 'AbortError'); if (ticket !== serial) throw new DOMException('Inputs changed', 'StaleError'); return result; }
    finally { if (ticket === serial) controller = null; }
}
function download(name, value) {
    const blob = new Blob([JSON.stringify(value, null, 2) + '\n'], {type:'application/json'}), url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function setRequest(value) {
    request = validateRequest(value); language = request.language; translate();
    $('seed').value = request.seed; $('events').value = request.max_events; $('candidates').value = request.max_candidates; $('trials').value = request.formation_trials;
    save();
}
$('language').addEventListener('change', () => { language = $('language').value; translate(); invalidate(); });
for (const id of ['seed', 'events', 'candidates', 'trials', 'strategy', 'mission']) $(id).addEventListener('input', invalidate);
$('cancel').addEventListener('click', () => controller?.abort());
$('restart').addEventListener('click', () => { invalidate(); setRequest(newRequest({language})); status('ready'); render(); controls(); $('underwrite').focus(); });
$('underwrite').addEventListener('click', () => action(async () => {
    request ||= readInputs(); save(); state = {underwriting:{choice:$('strategy').value, scope:'browser-rehearsal', production_authority:[], bounded_request_hash:await digest('request', request)}};
    stage = 'underwrite'; status(['build','repair'].includes(state.underwriting.choice) ? 'underwritten' : 'alternative');
}));
$('discover').addEventListener('click', () => action(async () => {
    state.discovery = await running('discovering', options => discover(request, options)); stage = 'discover'; status('discovered');
}));
$('freeze').addEventListener('click', () => action(async () => {
    const frozen = await running('frozen', async () => {
        const response = await fetch(new URL('./engine.mjs', import.meta.url)); if (!response.ok) throw Error('Engine source unavailable');
        const sourceHash = await digest('browser-engine-source', await response.text());
        return freeze(request, state.discovery, sourceHash);
    }); state.frozen = frozen; stage = 'freeze'; status('frozen');
}));
$('evaluate').addEventListener('click', () => action(async () => {
    state.evaluation = await running('evaluating', options => evaluate(request, state.frozen, options)); stage = 'evaluate'; status('evaluated');
}));
$('record').addEventListener('click', () => action(async () => {
    const principal = $('principal').value.trim(); if (!/^[a-zA-Z0-9_.-]{1,64}$/.test(principal)) throw Error(t('Use a non-personal ASCII operator label.', 'Utilisez une étiquette ASCII non personnelle.'));
    state.decision = {principal_label:principal, authenticated:false, choice:$('decision').value, release_hash:state.frozen.release_hash, scope:'browser-rehearsal', authority:[]}; stage = 'decide'; status('decided');
}));
$('renew').addEventListener('click', () => action(async () => {
    state.renewal = await running('renewing', options => renew(request, state.discovery, {...options, engineSourceHash:state.frozen.manifest.engine_source_hash})); stage = 'renew'; status('renewed');
}));
$('export').addEventListener('click', () => action(async () => {
    const evidence = {schema_version:1, scope:'browser-rehearsal', request, request_hash:await digest('request', request), ...state};
    download('successor-browser-evidence.json', {schema_version:1, evidence, evidence_hash:await digest('evidence', evidence), signature:null, authority:[]});
}));
$('request-export').addEventListener('click', () => action(async () => { request ||= readInputs(); save(); download('request.json', request); }));
async function importFile(input) { const file = input.files?.[0]; if (!file) return null; if (file.size > 2000000) throw Error('Import exceeds 2 MB'); return parseBounded(await file.text()); }
$('request-import').addEventListener('change', () => action(async () => { const value = await importFile($('request-import')); if (!value) return; validateRequest(value); invalidate(); setRequest(value); status('restored'); }));
async function nativeStatus() {
    if (!nativeEnvelope) return;
    if (!request) throw Error(t('Restore the original request first.', 'Restaurez d’abord la requête originale.'));
    $('native-status').textContent = t('Verifying imported evidence; no authority.', 'Vérification des preuves importées; aucune autorité.');
    const boundRequest = request;
    const verified = await verifyNative(boundRequest, nativeEnvelope), trusted = $('trust-key').value.trim();
    let signer = t('Authenticity unverified; no trusted key supplied.', 'Authenticité non vérifiée; aucune clé fiable fournie.');
    if (trusted) {
        if (!/^[a-f0-9]{64}$/.test(trusted)) throw Error('Trusted key must be 32-byte lowercase hex');
        const signature = nativeEnvelope.signature;
        if (!signature || signature.public_key !== trusted || typeof signature.signature !== 'string') throw Error('No matching trusted signature');
        const key = await crypto.subtle.importKey('raw', Uint8Array.from(trusted.match(/../g), x => parseInt(x,16)), {name:'Ed25519'}, false, ['verify']);
        const sig = Uint8Array.from(atob(signature.signature), c => c.charCodeAt(0));
        const data = Uint8Array.from(nativeEnvelope.evidence_hash.match(/../g), x => parseInt(x,16));
        if (sig.length !== 64 || !await crypto.subtle.verify('Ed25519', key, sig, data)) throw Error('Invalid trusted signature');
        signer = t('Signature verified against the separately supplied key; local signer only.', 'Signature vérifiée par la clé fournie séparément; signataire local seulement.');
    }
    if (request !== boundRequest) throw new DOMException('Inputs changed', 'StaleError');
    $('native-status').textContent = t('NATIVE LOCAL REHEARSAL · Original request and evidence digests match. ', 'RÉPÉTITION NATIVE LOCALE · Requête et condensat des preuves concordent. ') + signer + t(' Independent proof and authority remain absent.', ' Preuve indépendante et autorité restent absentes.');
    $('native-evidence').textContent = JSON.stringify(verified.evidence, null, 2);
}
$('result-import').addEventListener('change', () => action(async () => {
    const value = await importFile($('result-import')); if (!value) return;
    if (!request) throw Error(t('Restore or download the original request first.', 'Restaurez ou téléchargez d’abord la requête originale.'));
    clearNative(); const boundRequest = request; await verifyNative(boundRequest, value);
    if (request !== boundRequest) throw new DOMException('Inputs changed', 'StaleError');
    nativeEnvelope = value; await nativeStatus();
}));
$('trust-key').addEventListener('change', () => action(nativeStatus));
try { const saved = localStorage.getItem('successor-request-v1'); setRequest(saved ? parseBounded(saved) : newRequest()); } catch { setRequest(newRequest()); }
translate(); status('ready'); render(); controls();
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register(new URL('../../service-worker.js', import.meta.url), {scope:new URL('../../', import.meta.url).pathname})
        .then(() => navigator.serviceWorker.ready).then(() => { $('offline-status').textContent = messages.cache[language === 'fr' ? 1 : 0]; })
        .catch(() => { $('offline-status').textContent = messages.cachefail[language === 'fr' ? 1 : 0]; });
} else $('offline-status').textContent = messages.cachefail[language === 'fr' ? 1 : 0];
