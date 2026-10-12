// SPDX-License-Identifier: Apache-2.0
// Bundled with the unchanged SUCCESSOR engine by generate_successor_pocket.py.
const pocketSource = '<!doctype html>\n' + document.documentElement.outerHTML;
const el = id => document.getElementById(id);
const en = Object.fromEntries([...document.querySelectorAll('[data-word]')].map(node => [node.dataset.word, node.textContent]));
en.title = 'A little universe. A lab of your own.';
const fr = {
    skip: 'Aller au laboratoire', larger: 'Texte plus grand', edition: 'LABORATOIRE PERSONNEL',
    title: 'Un petit univers. Votre propre laboratoire.',
    lead: 'Donnez-lui un nom. Lancez une expérience. Gardez le tout. Votre prochaine découverte commence par un peu de curiosité.',
    free: 'Gratuit à explorer. Sans compte, portefeuille ni installation.',
    loading: 'Ouverture du laboratoire… Si ce message reste affiché, essayez un navigateur récent avec JavaScript activé.',
    step1: 'Personnalisez-le', step2: 'Voyez-le fonctionner', step3: 'Emportez-le',
    yourspace: 'VOTRE ESPACE DE DÉCOUVERTE', setup: 'À votre image.', name: 'Donnez un nom à votre laboratoire',
    namehelp: 'Un surnom suffit. Vous pouvez le changer à tout moment.', challenge: 'Choisissez un défi',
    small: 'Une première découverte · 256 événements', medium: 'Un plus grand défi · 1 000 événements', big: 'Aller plus loin · 4 000 événements',
    challengehelp: 'Un événement est un enregistrement fictif de service. Votre laboratoire regroupe les données et vérifie les totaux.',
    run: 'Donner vie à mon Ω', cancel: 'Arrêter cette expérience', ready: 'À votre rythme. L’exemple est déjà prêt.',
    what: 'Que fait mon Ω exactement?',
    whattext: 'Il essaie quatre petits programmes, en choisit un, puis le vérifie sur six nouveaux jeux de données. Vous voyez si les réponses correspondent et combien de temps il a fallu. Ce sont de vrais calculs sur votre appareil.',
    limit: 'C’est une expérience informatique ciblée, pas un assistant IA généraliste. Elle n’effectue pas de missions, ne gagne pas d’argent et n’agit pas à votre place.',
    yourlab: 'VOTRE SUCCESSOR Ω', emptytitle: 'Votre première découverte est à un clic.',
    emptytext: 'Voyez différentes approches résoudre le même défi. Changez sa taille, recommencez et créez une petite collection d’expériences.',
    local: 'MESURÉ ICI · EXPÉRIENCE LOCALE', checks: 'Vérifications concordantes', programs: 'Programmes comparés', experiments: 'Expériences conservées',
    timing: 'Durée des six vérifications', approach: 'Approche', time: 'Millisecondes',
    timinghelp: 'Un temps plus court signifie plus rapide dans cet essai. Les temps varient selon votre appareil et les applications ouvertes. Un résultat plus rapide est une observation, pas une preuve indépendante d’amélioration.',
    again: 'Essayer un nouveau défi', history: 'Ma collection d’expériences',
    historyhelp: 'Les huit expériences les plus récentes. Les résultats sauvegardés sont des notes historiques; lancez une nouvelle expérience pour vérifier à nouveau.',
    evidence: 'Examiner la dernière expérience', export: 'Enregistrer les données de l’expérience',
    keepbadge: 'QUELQUE CHOSE À GARDER', keep: 'Votre Ω. Sur votre appareil.',
    keeptext: 'Gardez un petit fichier contenant votre nom, vos expériences et le laboratoire fonctionnel. Ouvrez-le dans votre navigateur pour recommencer, même sans internet.',
    savehelp: 'Choisissez « Enregistrer mon Ω », puis consultez Téléchargements. Ouvrez le fichier HTML dans Chrome, Edge, Firefox ou Safari. Enregistrez une nouvelle copie après vos prochaines expériences; le fichier ouvert ne se met pas à jour tout seul.',
    save: 'Enregistrer mon Ω', savebefore: 'Vous pouvez l’enregistrer avant ou après votre première expérience.',
    questions: 'Quelques réponses rassurantes.', own: 'Qu’est-ce qui m’appartient?',
    owntext: 'Vous gardez votre laboratoire nommé et vos fichiers d’expériences sur votre appareil. Le logiciel inclus est libre sous licence Apache 2.0 : vous pouvez l’utiliser, le copier et le modifier selon cette licence. Ce n’est ni un jeton, ni un NFT, ni une part d’entreprise, ni une propriété intellectuelle exclusive.',
    private: 'Où vont mes informations?',
    privatetext: 'Le laboratoire n’envoie votre nom ni vos expériences nulle part. Il n’utilise ni compte, ni suivi analytique, ni stockage automatique du navigateur. Enregistrez votre copie avant de fermer ou de recharger. Les fichiers téléchargés ne sont pas chiffrés; partagez-les à votre discrétion.',
    phone: 'Puis-je utiliser mon téléphone ou ma tablette?',
    phonetext: 'Oui, vous pouvez expérimenter ici. Certains téléphones affichent un aperçu des fichiers HTML sans les exécuter. Ouvrez votre copie interactive dans un navigateur sur ordinateur. Gardez le fichier original si votre appareil ne montre qu’un aperçu.',
    next: 'Que puis-je explorer ensuite?',
    nexttext: 'L’espace SUCCESSOR Ω complet propose une revue des preuves étape par étape, des comparaisons de deuxième génération et un parcours vers un logiciel installé.',
    advanced: 'Explorer l’espace complet (en ligne)', footer: 'La curiosité entre vos mains.', home: 'Explorer AGI ALPHA (en ligne)', license: 'Licence du logiciel · Apache 2.0',
};
const words = {
    en: {working:'Trying four approaches…', checking:'Checking six fresh workloads…', done:'Your experiment is ready. Save your Ω to keep it.', stopped:'Stopped. Your earlier experiments are still here.', failed:'The experiment could not finish. Your earlier results are safe. Try again in a current browser.', invalid:'Please give your lab a name of 1–48 characters and choose one of the three challenges.', saved:'Your download is ready. Look for the HTML file in Downloads. Save again after making changes.', savefailed:'The download could not be created. Keep this page open and try again.', restored:'Your saved collection is open. These are historical, unverified notes. Try a new challenge to make fresh measurements.', damaged:'The saved data could not be read. The lab is ready for a fresh experiment; the original file is unchanged.', verified:'The answers matched.', rejected:'An answer did not match.', detail:'Your chosen program passed the exact-output checks. Compare its time below, then try another challenge.', faildetail:'Keep the original approach. Inspect the experiment before relying on this result.', original:'Original approach', alternative:'Sorting approach', yours:'Your chosen program', sample:'sample events', historical:'SAVED NOTES · RERUN TO CHECK', unsupported:'This browser is missing the local cryptography needed by the experiment. Open this page or saved file in a current desktop browser.'},
    fr: {working:'Essai de quatre approches…', checking:'Vérification de six nouvelles charges…', done:'Votre expérience est prête. Enregistrez votre Ω pour la garder.', stopped:'Arrêté. Vos expériences précédentes sont toujours là.', failed:'L’expérience n’a pas pu se terminer. Vos résultats précédents sont conservés. Réessayez dans un navigateur récent.', invalid:'Donnez un nom de 1 à 48 caractères au laboratoire et choisissez l’un des trois défis.', saved:'Votre téléchargement est prêt. Cherchez le fichier HTML dans Téléchargements. Enregistrez à nouveau après vos modifications.', savefailed:'Le téléchargement n’a pas pu être créé. Gardez cette page ouverte et réessayez.', restored:'Votre collection est ouverte. Ce sont des notes historiques non vérifiées. Essayez un nouveau défi pour effectuer de nouvelles mesures.', damaged:'Les données sauvegardées sont illisibles. Le laboratoire est prêt pour un nouvel essai; le fichier original reste intact.', verified:'Les réponses correspondent.', rejected:'Une réponse ne correspond pas.', detail:'Votre programme a passé les vérifications de résultats exacts. Comparez sa durée ci-dessous, puis essayez un autre défi.', faildetail:'Conservez l’approche d’origine. Examinez l’expérience avant de vous fier au résultat.', original:'Approche d’origine', alternative:'Approche par tri', yours:'Votre programme choisi', sample:'événements fictifs', historical:'NOTES SAUVEGARDÉES · À REVÉRIFIER', unsupported:'Ce navigateur ne propose pas la cryptographie locale nécessaire. Ouvrez cette page ou le fichier enregistré dans un navigateur récent sur ordinateur.'},
};
let state = {schema:'successor-pocket-v1', name:'My Ω', language:'en', large:false, events:256, seed:42, history:[], evidence:null};
let statusKey = 'ready', downloadStatusKey = null, restored = false, controller = null, hasUnsavedChanges = false;
function validatePocket(value) {
    if (!exact(value, Object.keys(state)) || value.schema !== state.schema || !scalar(value.name) || !value.name.trim() || value.name.length > 48 || !['en','fr'].includes(value.language) || typeof value.large !== 'boolean' || ![256,1000,4000].includes(value.events) || !integer(value.seed,0,4294967295) || !Array.isArray(value.history) || value.history.length > 8) throw Error('Invalid saved lab');
    for (const item of value.history) {
        if (!exact(item,['seed','events','matched','correctness','totals','candidates']) || !integer(item.seed,0,4294967295) || ![256,1000,4000].includes(item.events) || !integer(item.matched,0,6) || typeof item.correctness !== 'boolean' || item.candidates !== 4 || !exact(item.totals,['current','beta','candidate']) || Object.values(item.totals).some(n => !integer(n,1,Number.MAX_SAFE_INTEGER))) throw Error('Invalid experiment note');
    }
    // Evidence is an inert historical document. It never supplies executable code or authority.
    if (value.evidence !== null && (!value.evidence || typeof value.evidence !== 'object' || Array.isArray(value.evidence))) throw Error('Invalid historical evidence');
    canonical(value);
    return value;
}
try {
    const saved = parseBounded(el('omega-state').textContent);
    if (Object.keys(saved).length) { state = validatePocket(saved); restored = state.history.length > 0; statusKey = restored ? 'restored' : 'ready'; }
} catch { statusKey = 'damaged'; }
const preferenceQuery = new URLSearchParams(location.search);
if (preferenceQuery.has('lang')) state.language = preferenceQuery.get('lang') === 'fr' ? 'fr' : 'en';
if (preferenceQuery.has('text')) state.large = preferenceQuery.get('text') === 'large';
const w = key => words[state.language][key] || (state.language === 'fr' ? fr : en)[key];
function say(key) { statusKey = key; el('status').textContent = w(key); }
function render() {
    document.documentElement.lang = state.language;
    document.documentElement.classList.toggle('large', state.large);
    for (const node of document.querySelectorAll('[data-word]')) node.textContent = (state.language === 'fr' ? fr : en)[node.dataset.word];
    document.title = state.name + ' · SUCCESSOR Ω';
    el('language').textContent = state.language === 'en' ? 'Français' : 'English';
    el('language').lang = state.language === 'en' ? 'fr' : 'en';
    el('large').setAttribute('aria-pressed', String(state.large));
    document.querySelector('.preferences').setAttribute('aria-label', state.language === 'fr' ? 'Préférences de lecture' : 'Reading preferences');
    document.querySelector('.steps').setAttribute('aria-label', state.language === 'fr' ? 'Trois étapes simples' : 'Three simple steps');
    el('progress').setAttribute('aria-label', state.language === 'fr' ? 'Progression de l’expérience' : 'Experiment progress');
    el('result-title').textContent = el('lab-name').value.trim() || state.name;
    if (downloadStatusKey) el('save-status').textContent = w(downloadStatusKey);
    el('empty').hidden = state.history.length > 0;
    el('outcome').hidden = !state.history.length;
    say(statusKey);
    const latest = state.history.at(-1);
    if (!latest) return;
    el('verdict').textContent = w(latest.correctness ? 'verified' : 'rejected');
    el('explanation').textContent = w(restored ? 'restored' : latest.correctness ? 'detail' : 'faildetail');
    if (restored) document.querySelector('.badge').textContent = w('historical');
    el('checks').textContent = latest.matched + ' / 6';
    el('programs').textContent = latest.candidates;
    el('count').textContent = state.history.length;
    el('timings').replaceChildren();
    for (const [key,label] of [['current','original'],['beta','alternative'],['candidate','yours']]) {
        const row = document.createElement('tr'), heading = document.createElement('th'), cell = document.createElement('td');
        heading.scope = 'row'; heading.textContent = w(label);
        cell.textContent = (latest.totals[key] / 1000000).toLocaleString(state.language, {minimumFractionDigits:3,maximumFractionDigits:3});
        row.append(heading, cell); el('timings').append(row);
    }
    el('history').replaceChildren();
    for (const record of state.history) {
        const li = document.createElement('li');
        li.textContent = `${record.events.toLocaleString(state.language)} ${w('sample')} · ${record.matched}/6 · ${w(record.correctness ? 'verified' : 'rejected')}`;
        el('history').append(li);
    }
    el('evidence').textContent = JSON.stringify(state.evidence, null, 2);
    el('export-evidence').disabled = state.evidence === null;
}
function readInputs() {
    const name = el('lab-name').value.trim(), events = Number(el('challenge').value);
    const valid = name.length >= 1 && name.length <= 48 && scalar(name) && [256,1000,4000].includes(events);
    el('lab-name').setAttribute('aria-invalid', String(!name || name.length > 48 || !scalar(name)));
    if (!valid) { say('invalid'); el('status').focus(); return false; }
    state.name = name; state.events = events;
    return true;
}
function busy(value) {
    for (const id of ['run','again','save','lab-name','challenge']) el(id).disabled = value;
    el('cancel').hidden = !value; el('progress').hidden = !value;
    el('lab-form').setAttribute('aria-busy', String(value));
}
async function runExperiment() {
    if (controller || !readInputs()) return;
    if (!crypto?.subtle || !crypto.randomUUID) { say('unsupported'); return; }
    controller = new AbortController(); busy(true); el('progress').value = 0; say('working');
    try {
        const request = newRequest({seed:state.seed, max_events:state.events, max_candidates:4, formation_trials:1, language:state.language});
        const discovery = await discover(request, {signal:controller.signal, onProgress:(n,total) => { el('progress').value = n/total; }});
        const frozen = await freeze(request, discovery, 'ENGINE_SOURCE_HASH');
        el('progress').value = 1; say('checking');
        const evaluation = await evaluate(request, frozen, {signal:controller.signal});
        if (controller.signal.aborted) throw new DOMException('Cancelled','AbortError');
        const note = {seed:request.seed, events:request.max_events, matched:evaluation.cases.filter(c => c.exact_output).length, correctness:evaluation.correctness, totals:evaluation.totals_ns, candidates:discovery.actual_candidates};
        state.history = [...state.history,note].slice(-8);
        state.evidence = {scope:'personal-browser-experiment', request, discovery, frozen, evaluation, authority:[]};
        state.seed = (state.seed + 104729) >>> 0;
        restored = false; hasUnsavedChanges = true; el('progress').value = 3; say('done'); render(); el('result-title').focus();
    } catch (error) { say(error.name === 'AbortError' ? 'stopped' : 'failed'); el('status').focus(); }
    finally { controller = null; busy(false); }
}
function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const link = document.createElement('a'); link.href = url; link.download = name; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
}
el('lab-name').value = state.name; el('challenge').value = state.events;
el('lab-form').addEventListener('submit', event => { event.preventDefault(); runExperiment(); });
el('again').addEventListener('click', runExperiment);
el('cancel').addEventListener('click', () => controller?.abort());
el('lab-name').addEventListener('input', () => { hasUnsavedChanges = true; el('result-title').textContent = el('lab-name').value || 'Ω'; });
el('challenge').addEventListener('change', () => { hasUnsavedChanges = true; });
el('language').addEventListener('click', () => { state.language = state.language === 'en' ? 'fr' : 'en'; hasUnsavedChanges = true; render(); });
el('large').addEventListener('click', () => { state.large = !state.large; hasUnsavedChanges = true; render(); });
el('save').addEventListener('click', () => {
    if (!readInputs()) return;
    try {
        const encoded = canonical(validatePocket(state)).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026');
        const file = pocketSource.replace(/(<script type="application\/json" id="omega-state">)[\s\S]*?(<\/script>)/, (_, start, end) => start + encoded + end);
        download('My-SUCCESSOR-Omega.html', file, 'text/html;charset=utf-8'); hasUnsavedChanges = false;
        downloadStatusKey = 'saved'; el('save-status').textContent = w(downloadStatusKey);
    } catch { downloadStatusKey = 'savefailed'; el('save-status').textContent = w(downloadStatusKey); }
});
el('export-evidence').addEventListener('click', () => {
    if (state.evidence) download('SUCCESSOR-Omega-experiment.json', JSON.stringify(state.evidence,null,2), 'application/json');
});
addEventListener('beforeunload', event => { if (hasUnsavedChanges) { event.preventDefault(); event.returnValue = ''; } });
render(); el('loading').hidden = true; el('app').hidden = false;
