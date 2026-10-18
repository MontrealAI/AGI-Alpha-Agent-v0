// SPDX-License-Identifier: Apache-2.0
const $ = id => document.getElementById(id);
const pageOptions = new URLSearchParams(location.search);
let language = pageOptions.get('lang') === 'fr' || document.documentElement.dataset.language === 'fr' ? 'fr' : 'en';
let largeText = pageOptions.get('text') === 'large' || document.documentElement.dataset.textSize === 'large';
let stage = 0, mode = 'example', mission = null, result = null, dossier = null;
let valueEstimate = null;
let artifacts = null, busy = false, controller = null, runToken = 0, revision = 0, importToken = 0;
let notice = null, lastStatus = null, lastError = null;
const sample = alpha.createSampleMission({seed: 42, leftRows: 240, rightRows: 360});
const en = {};
for (const el of document.querySelectorAll('[data-i18n]')) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll('br').forEach(br => br.replaceWith('\n'));
    en[el.dataset.i18n] = clone.textContent;
}
const fr = {
    adoptionTitle:'Cette capacité vaudrait-elle la peine d’être adoptée ?',adoptionIntro:'Estimez votre effort complet, y compris l’examen et les corrections. Les millisecondes du navigateur ne mesurent pas le temps humain gagné.',
    valueBefore:'Minutes actuelles par exécution',valueAfter:'Minutes prévues avec cet outil',valueFrequency:'Exécutions par mois',valueHourly:'Votre valeur d’une heure',valueSetup:'Coût initial de mise en place et d’intégration',valueCurrency:'Devise commune',valueCalculate:'Estimer selon mes hypothèses',valueProjection:'PROJECTION · VOS HYPOTHÈSES',valueLimit:'Calcul arithmétique de vos estimations, pas une économie mesurée ni garantie. Il exclut les coûts non saisis, les coûts récurrents et les coûts d’erreur ou de risque. Vérifiez les résultats réels avant adoption.',valueDownload:'Télécharger les hypothèses et la projection',
    joinedPreview:'Aperçu du catalogue joint',comparisonTable:'Comparaison complète des méthodes',largerText:'Agrandir le texte',returnSetup:'Revenir à la préparation',tryExample:'Essayer l’exemple inclus',skip:'Aller à votre mission',brandCaption:'PAR AGI ALPHA',mainNavigation:'Navigation principale',
    howItWorks:'L’expérience',openProject:'Ouvrir un projet',
    heroEyebrow:'VOTRE MISSION. VOTRE AVANTAGE. VOTRE INSTITUTION.',
    heroLine1:'Trouvez votre',heroLine2:'avantage.',heroLine3:'Concrétisez-le.\nGardez ce que vous bâtissez.',
    heroDescription:'Transformez un vrai obstacle en capacité utile. Comparez les résultats. Conservez les outils, les preuves et les leçons qui renforceront la prochaine mission.',
    firstAdvantage:'Trouver mon premier avantage',bringCatalogs:'Utiliser mes propres catalogues',
    startNote:'Gratuit. Sans compte, portefeuille ni installation. Dans votre navigateur.',
    imageAlt:'Illustration ornée violette et dorée du parcours Alpha, Gym, Specialist ASI et SUCCESSOR Ω.',
    artEyebrow:'CONÇU POUR DURER',artCaption:'Possédez l’institution.\nChangez les modèles. Préservez la mission.',
    artNote:'L’ambition est durable. Le premier pas utile vous appartient.',valueLabel:'Ce que vous emportez',
    valueOne:'Un résultat utile',valueOneText:'Résolvez une tâche concrète et délimitée.',
    valueTwo:'Une comparaison vérifiable',valueTwoText:'Voyez ce qui progresse, et à quel coût.',
    valueThree:'Une capacité à conserver',valueThreeText:'Emportez l’outil, les preuves et l’historique.',
    missionEyebrow:'VOTRE PREMIER ALPHA',missionTitle:'Deux catalogues.\nUne réponse fiable.',
    missionIntro:'Trouvez les correspondances, les produits manquants et les valeurs contradictoires. Découvrez ensuite quelle méthode effectue le même travail exact avec moins d’effort.',
    missionLabel:'LA MISSION',missionName:'Des catalogues clairs',
    missionSummary:'Rapprochez deux catalogues publics. Obtenez les données et une méthode réutilisable.',
    missionProgress:'Progression de la mission',stepAlpha:'Définir l’avantage',stepGym:'Comparer les méthodes',
    evidence:'Preuves',stepEvidence:'Examiner le résultat réel',yourSuccessor:'Votre SUCCESSOR',
    stepSuccessor:'Conserver. Utiliser. Poursuivre.',localNote:'Local, par conception.\nVos catalogues restent dans ce navigateur.',
    startHere:'COMMENCEZ ICI',alphaTitle:'Vivez une mission complète.',
    alphaLead:'Un exemple inclus vous mène d’un obstacle quotidien à des fichiers utiles, une comparaison équitable et une capacité à conserver.',
    sourceLabel:'Source des catalogues',includedExample:'Exemple inclus',myCatalogs:'Mes catalogues publics',
    catalogOne:'Votre catalogue de produits',catalogTwo:'Un catalogue fournisseur',
    exampleGoal:'L’avantage à bâtir',exampleGoalText:'Obtenez les correspondances exactes et les exceptions en réduisant le travail de rapprochement.',
    syntheticNote:'Exemple synthétique, sans données personnelles. Les résultats sont calculés à chaque exécution.',
    runExample:'Découvrir mon premier Alpha',
    inputNote:'Collez ou choisissez deux fichiers CSV publics, sans données personnelles. Jusqu’à 200 Ko et 1 500 lignes par catalogue ; 10 000 paires en sortie. Cellules entre guillemets et UTF-8 acceptés.',
    leftCatalog:'Catalogue de référence',rightCatalog:'Second catalogue',chooseCsv:'Choisir un fichier CSV',
    uploadLeft:'Importer le catalogue de référence',uploadRight:'Importer le second catalogue',checkColumns:'Vérifier mes colonnes',
    leftKey:'Relier cette colonne de référence',rightKey:'À cette colonne du second catalogue',
    matchingNote:'Clés et champs communs sont comparés exactement. Les clés doivent être renseignées ; les doublons sont conservés et peuvent produire plusieurs lignes. Sans correspondance approximative ni nettoyage automatique.',
    runMine:'Trouver l’avantage dans mes catalogues',gymTitle:'Mettez de meilleures méthodes au travail.',
    gymLead:'Quatre méthodes établies. Les mêmes catalogues. Des sorties exactes contrôlées face à une référence simple.',
    gymNote:'Nous comptons les comparaisons, les opérations d’index et les paires produites. Le temps du navigateur est mesuré séparément : il varie selon l’appareil et les données.',
    cancelRun:'Annuler cette exécution',resultEyebrow:'VOTRE MISSION, LIVRÉE',localResult:'Calculé localement',
    evidenceTitle:'Une clarté exploitable.',matchedPairs:'paires correspondantes',unmatchedRows:'lignes sans correspondance',
    conflictingPairs:'paires avec divergences',joinedCsv:'Catalogue joint',unmatchedLeft:'Référence : lignes non reliées',
    unmatchedRight:'Second : lignes non reliées',conflictsCsv:'Divergences de valeurs',previewJoined:'Aperçu du catalogue joint',
    previewNote:'Six premières lignes, valeurs exactes. Les CSV neutralisent les cellules de type formule pour la sécurité des tableurs ; le JSON préserve le texte original.',observedAdvantage:'L’AVANTAGE OBSERVÉ',
    comparisonLabel:'Comparaison des opérations logiques',
    operationNote:'Le travail logique compte comparaisons de clés, insertions d’index, recherches et paires produites. Il exclut le hachage interne, les allocations, le tri des sorties, la vérification et l’export. Les lignes indexées/triées ne mesurent ni octets ni mémoire maximale.',
    inspectComparison:'Examiner la comparaison complète',method:'Méthode',operations:'Travail logique',browserTime:'Temps navigateur',
    correctness:'Vérification des sorties',indexedRows:'Lignes indexées',sortedRows:'Lignes triées',
    methodNote:'Cette mission compare des algorithmes classiques. Elle démontre un avantage logiciel délimité ; elle n’établit ni intelligence nouvelle, supériorité générale, qualification indépendante, ni économies organisationnelles.',
    levelObserved:'Observé ici',levelObservedText:'Sorties utiles, contrôles exacts et travail mesuré sur ces données.',
    levelNext:'Ensuite : qualification indépendante',levelNextText:'Cas nouveaux et protégés, alternatives crédibles et examen avant une confiance élargie.',
    keepCapability:'Conserver cette capacité',tryDifferent:'Essayer d’autres données',successorEyebrow:'VOTRE SUCCESSOR · À VOUS DE POURSUIVRE',
    successorTitle:'Gardez plus qu’un résultat.',
    successorLead:'Emportez l’outil, la comparaison et l’historique. Ajoutez de nouveaux catalogues. Lancez le cycle suivant. Bâtissez sur ce qui a fait ses preuves.',
    nameProject:'Donnez un nom à votre projet',portableTitle:'Votre espace complet',
    portableText:'Un seul fichier HTML. Ouvrez-le hors ligne pour traiter de nouveaux catalogues, retrouver la comparaison et poursuivre votre projet.',
    downloadWorkspace:'Télécharger mon espace',toolTitle:'Votre capacité réutilisable',
    toolText:'Un outil Node.js lisible pour la même jointure exacte. Intégrez la méthode à votre propre travail.',
    downloadTool:'Télécharger l’outil · .mjs',downloadReport:'Rapport de preuve',downloadProject:'Projet et historique des cycles',
    historyTitle:'Ce que votre institution retient',
    historyNote:'Un projet portable conserve les données de mission et les observations locales. Les résultats importés restent historiques : recalculez-les avant de vous y fier. Aucune permission ni aucun fonds ne sont importés.',
    beyondBrowser:'Poursuivre au-delà de ce navigateur',
    beyondText:'Préparez une revue indépendante ou une réalisation sous forme de travail délimité. Ces fichiers sont des brouillons non financés ; examinez le périmètre, le prestataire et l’état de préparation avant de commander.',
    handoffUsdc:'Préparer un brouillon USDC',handoffAgialpha:'Préparer un brouillon $AGIALPHA',
    contractsTitle:'Contrats Alpha actuels',contractsNote:'Adresses Ethereum Mainnet fournies par le propriétaire le 18 octobre 2026. Vérification indépendante en chaîne en attente. Références informatives : cette mission gratuite ne nécessite aucune interaction avec les contrats.',
    nextCycle:'Commencer mon prochain cycle',backEvidence:'Revenir aux preuves',
    continuity:'Déjà commencé ? Emportez l’historique de votre projet.',restoreProject:'Restaurer un projet',restoreFile:'Restaurer un fichier de projet',
    experienceEyebrow:'UNE MISSION. UNE INSTITUTION DURABLE.',experienceTitle:'Bâtissez l’avantage.\nPréservez ce qui le rend possible.',
    experienceIntro:'Votre mission reste centrale. Modèles, méthodes et prestataires peuvent changer à mesure que de meilleures capacités font leurs preuves.',
    alphaMeaning:'Trouvez l’avantage à bâtir. Précisez qui en bénéficie, ce qui compte et ce qu’un meilleur résultat apporterait.',
    gymMeaning:'Développez des approches concurrentes dans un environnement délimité. Apprenez des résultats utiles et des échecs.',
    asiMeaning:'Une désignation propre à la mission qui se mérite : figer une candidate, tester du travail nouveau et protégé, surpasser des alternatives crédibles.',
    omegaMeaning:'Après preuve et autorisation explicite, conservez la capacité, les éléments probants et la mémoire opérationnelle pour la suite.',
    biggerMission:'UNE AUTRE MISSION EN TÊTE ?',biggerTitle:'Partez de l’avantage qui compte pour vous.',
    biggerText:'Cadrez une opportunité de recherche, d’ingénierie ou d’organisation dans le carnet de découverte Alpha. Il prépare un plan ; l’exécution et la preuve dépendent de la mission.',
    openNotebook:'Ouvrir la découverte Alpha',questionsTitle:'Quelques points utiles.',questionFree:'Que puis-je faire gratuitement ?',
    answerFree:'Exécutez l’exemple ou vos propres catalogues CSV publics dans les limites indiquées, examinez les résultats et téléchargez la capacité, le rapport et l’espace. Cette mission n’utilise aucune API de modèle et ne demande ni compte ni portefeuille.',
    questionAlpha:'Qu’est-ce qui constitue Alpha ici ?',
    answerAlpha:'Vous obtenez des données rapprochées exploitables et une capacité réutilisable. Comparez chaque méthode sur votre charge réelle. Ces résultats aident à évaluer une opportunité Alpha ; supériorité indépendante et valeur économique réalisée exigent d’autres preuves, y compris les coûts d’intégration et l’effort humain.',
    questionOwn:'Que puis-je conserver ?',
    answerOwn:'Vous contrôlez les fichiers téléchargés : espace, code réutilisable, données, sorties et historique. Le code inclus est sous licence Apache 2.0. Les droits sur les données et les travaux commandés ou tiers restent à établir.',
    questionTrust:'Cela certifie-t-il Specialist ASI ou autorise-t-il un déploiement ?',
    answerTrust:'Non. C’est une démonstration locale opérationnelle et délimitée. Une évaluation indépendante sur du travail nouveau et protégé et une autorisation explicite restent des étapes distinctes. Le Gym développe la capacité ; il ne la certifie pas.',
    footerMotto:'POSSÉDEZ L’INSTITUTION. PRÉSERVEZ LA MISSION.',footerScope:'Une première capacité utile. Une ambition ouverte.',
    sourceGuide:'Source et guide de reproduction ↗',missionProtocol:'Protocole de mission SUCCESSOR ↗',disclaimer:'Prototype de recherche et avis'
};
const ariaEn = {};
for (const el of document.querySelectorAll('[data-i18n-aria]')) ariaEn[el.dataset.i18nAria] = el.getAttribute('aria-label');
const altEn = {};
for (const el of document.querySelectorAll('[data-i18n-alt]')) altEn[el.dataset.i18nAlt] = el.getAttribute('alt');
const say = (english, french) => language === 'fr' ? french : english;
const number = n => new Intl.NumberFormat(language === 'fr' ? 'fr-CA' : 'en-CA').format(n);
const percentage = n => new Intl.NumberFormat(language === 'fr' ? 'fr-CA' : 'en-CA', {maximumFractionDigits:1}).format(n);
function node(tag, parent, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    if (parent) parent.append(el);
    return el;
}
function translate() {
    document.documentElement.lang = language; document.documentElement.dataset.language = language;
    document.title = say('Find your advantage · SUCCESSOR Ω','Trouvez votre avantage · SUCCESSOR Ω');
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = language === 'fr' ? fr[el.dataset.i18n] || en[el.dataset.i18n] : en[el.dataset.i18n]; });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => el.setAttribute('aria-label', language === 'fr' ? fr[el.dataset.i18nAria] || ariaEn[el.dataset.i18nAria] : ariaEn[el.dataset.i18nAria]));
    document.querySelectorAll('[data-i18n-alt]').forEach(el => el.setAttribute('alt', language === 'fr' ? fr[el.dataset.i18nAlt] : altEn[el.dataset.i18nAlt]));
    $('lang-en').setAttribute('aria-pressed', String(language === 'en'));
    $('lang-fr').setAttribute('aria-pressed', String(language === 'fr'));
    renderSample();
    if (result) renderResult();
    renderHistory();
    renderNotice();
    if (lastStatus) $('status').textContent = say(...lastStatus);
    if (lastError && !$('error').hidden) $('error').textContent = errorMessage(lastError);
    renderValue();
    if (!$('key-mapping').hidden) updateMappingSummary();
}
function status(english, french) { lastStatus = [english, french]; $('status').textContent = say(english, french); }
function renderNotice() {
    if (!notice) return;
    $('restored-note').textContent = notice.type === 'restored' ? say(
        `“${notice.name}” restored with ${notice.cycles} historical cycles. Inputs are ready. Run again for fresh local evidence; imported timings and claims are not new observations.`,
        `« ${notice.name} » restauré avec ${notice.cycles} cycles historiques. Les données sont prêtes. Relancez pour de nouvelles preuves locales ; temps et déclarations importés restent historiques.`
    ) : say('Your history is preserved. Replace either catalog or run these inputs again to begin the next cycle.',
        'Votre historique est conservé. Remplacez un catalogue ou relancez ces données pour le cycle suivant.');
    $('restored-note').hidden = false;
}
function errorMessage(error) {
    const message = String(error?.message || error);
    const localized = {
        'CSV needs a header row.':'Le CSV doit contenir une ligne d’en-tête.',
        'CSV headers must be nonempty and unique.':'Les en-têtes CSV doivent être renseignés et uniques.',
        'Every CSV row must have the header column count.':'Chaque ligne CSV doit contenir autant de colonnes que l’en-tête.',
        'Unclosed quoted CSV cell.':'Une cellule CSV entre guillemets n’est pas refermée.',
        'Quote inside an unquoted CSV cell.':'Un guillemet apparaît dans une cellule CSV non délimitée.',
        'Unexpected text after a closing CSV quote.':'Du texte suit le guillemet de fermeture d’une cellule CSV.',
        'Join keys must be nonempty exact strings.':'Toutes les clés de jointure doivent être renseignées.',
        'Choose a key column present in each CSV.':'Choisissez une colonne clé présente dans chaque CSV.',
        'CSV cannot contain NUL characters.':'Le CSV ne doit pas contenir de caractères NUL.',
        'Each CSV must contain at most 200000 UTF-8 bytes.':'Chaque CSV est limité à 200 000 octets UTF-8.',
        'CSV exceeds 1500 data rows.':'Chaque catalogue est limité à 1 500 lignes de données.',
        'CSV exceeds 32 columns.':'Chaque CSV est limité à 32 colonnes.',
        'CSV cells exceed 4096 characters.':'Une cellule CSV dépasse la limite de 4 096 caractères.',
        'Join exceeds 10000 output pairs.':'Cette jointure dépasse 10 000 paires. Réduisez les données ou les doublons.',
        'Unsupported or invalid SUCCESSOR project.':'Ce fichier n’est pas un projet SUCCESSOR pris en charge ou valide.',
        'This project contains six full cycles. Export it before starting a separate project.':'Ce projet contient six cycles complets. Téléchargez-le avant de commencer un projet distinct.',
        'Invalid name.':'Donnez au projet un nom de 1 à 80 caractères.'
    };
    return language === 'fr' ? localized[message] || `L’opération n’a pas abouti. Vérifiez le format et les limites du fichier. Détail : ${message}` : message;
}
function showError(error, focusEl) {
    lastError = error;
    $('error').textContent = errorMessage(error);
    $('error').hidden = false; $('error-actions').hidden = false;
    if (focusEl) { focusEl.setAttribute('aria-invalid','true'); focusEl.focus(); }
    else $('error').scrollIntoView({block:'nearest'});
}
function clearError() {
    lastError = null;
    $('error').hidden = true; $('error-actions').hidden = true;
    document.querySelectorAll('[aria-invalid=true]').forEach(el => el.removeAttribute('aria-invalid'));
}
function go(next, focus = true) {
    stage = next;
    ['alpha','gym','evidence','successor'].forEach((name, i) => {
        $(`pane-${name}`).hidden = i !== next;
        const item = $(`journey-${i}`);
        item.classList.toggle('completed', i < next);
        if (i === next) item.setAttribute('aria-current','step'); else item.removeAttribute('aria-current');
    });
    if (focus) {
        const target = $(`${['alpha','gym','evidence','successor'][next]}-title`);
        target.focus({preventScroll:true});
        $('mission').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
    }
}
function setMode(next, focus = false) {
    mode = next;
    $('example-inputs').hidden = next !== 'example';
    $('custom-form').hidden = next !== 'custom';
    $('mode-example').setAttribute('aria-pressed',String(next === 'example'));
    $('mode-custom').setAttribute('aria-pressed',String(next === 'custom'));
    if (focus && next === 'custom') $('left-csv').focus();
}
function renderSample() {
    for (const [side, table] of [['left',sample.left],['right',sample.right]]) {
        $(`sample-${side}-count`).textContent = say(`${number(table.rows.length)} synthetic records`,`${number(table.rows.length)} lignes synthétiques`);
        const container = document.querySelectorAll('.sample-grid')[side === 'left' ? 0 : 1];
        container.replaceChildren();
        const columns = table.headers.slice(0,3);
        for (const cell of columns) node('span',container,cell);
        for (const row of table.rows.slice(0,3)) for (const cell of row.slice(0,3)) node('span',container,cell);
    }
}
function clearCurrent() {
    if (busy) cancelRun(false);
    revision += 1; result = null; artifacts = null; mission = null; valueEstimate = null; $('value-result').hidden = true;
    $('restored-note').hidden = true;
    notice = null;
    clearError();
}
function updateMappingSummary() {
    try {
        const left = alpha.parseCsv($('left-csv').value), right = alpha.parseCsv($('right-csv').value);
        const names = left.headers.filter(name => name !== $('left-key').value && name !== $('right-key').value && right.headers.includes(name));
        $('mapping-summary').textContent = say(
            `${number(left.rows.length)} reference rows · ${number(right.rows.length)} second rows. Shared fields compared: ${names.length ? names.join(', ') : 'none'}.`,
            `${number(left.rows.length)} lignes de référence · ${number(right.rows.length)} lignes du second catalogue. Champs communs comparés : ${names.length ? names.join(', ') : 'aucun'}.`
        );
    } catch { $('key-mapping').hidden = true; }
}
function checkColumns() {
    clearError();
    for (const side of ['left','right']) {
        try {
            const table = alpha.parseCsv($(`${side}-csv`).value);
            const select = $(`${side}-key`), previous = select.value;
            select.replaceChildren();
            for (const header of table.headers) { const option = node('option',select,header); option.value = header; }
            select.value = table.headers.includes(previous) ? previous : table.headers[0];
        } catch (error) { showError(error,$(`${side}-csv`)); return false; }
    }
    $('key-mapping').hidden = false;
    updateMappingSummary();
    $('left-key').focus();
    return true;
}
function controls(disabled) {
    for (const id of ['hero-start','hero-custom','example-start','custom-start','mode-example','mode-custom','check-columns','open-project-top','open-project-bottom']) $(id).disabled = disabled;
}
const strategyNames = {
    nested_scan:['Nested scan · current method','Balayage imbriqué · méthode actuelle'],
    fixed_right_hash:['Hash the right table · alternative','Hachage à droite · alternative'],
    smaller_side_hash:['Hash the smaller table · candidate','Hachage du petit côté · candidate'],
    sort_merge:['Sort and merge · alternative','Tri et fusion · alternative']
};
function strategyName(strategy) { return say(...(strategyNames[strategy.strategyId] || [strategy.label,strategy.label])); }
async function run(m) {
    if (busy) return;
    clearError();
    if (dossier?.cycles.length >= 6) {
        showError(Error(say('This project contains six full cycles. Export it before starting a separate project.','Ce projet contient six cycles complets. Téléchargez-le avant de commencer un projet distinct.')));
        if (result) go(3);
        return;
    }
    busy = true; controls(true); controller = new AbortController();
    const token = ++runToken, expectedRevision = revision;
    $('run-progress').style.width = '5%';
    $('run-status').textContent = say('Preparing your comparison…','Préparation de votre comparaison…');
    go(1);
    try {
        const next = await runAlphaMission(m, {signal:controller.signal,onProgress: progress => {
            if (token !== runToken) return;
            const completed = Number(progress.completed ?? 0), total = Number(progress.total ?? 4);
            $('run-progress').style.width = `${Math.max(8,Math.min(95,(completed / total) * 100))}%`;
            const definition = alpha.STRATEGIES.find(s => s.id === progress.strategyId);
            $('run-status').textContent = definition ? say(`Comparing: ${strategyName({strategyId:definition.id,label:definition.label})}`,`Comparaison : ${strategyName({strategyId:definition.id,label:definition.label})}`) : say('Verifying exact outputs…','Vérification des sorties exactes…');
        }});
        if (token !== runToken || revision !== expectedRevision) return;
        alpha.verifyExperiment(m,next);
        const nextArtifacts = alpha.buildArtifacts(m,next);
        const nextDossier = project.appendCycle(dossier || project.createProject({
            name:say('My first Alpha','Mon premier Alpha'),
            goal:say('Reconcile public catalogs exactly and retain a useful, reusable method.','Rapprocher exactement des catalogues publics et conserver une méthode utile et réutilisable.')
        }),{mission:m,result:next,sourceHash:SOURCE_HASH});
        mission = m; result = next; artifacts = nextArtifacts; dossier = nextDossier;
        $('project-name').value = dossier.name;
        $('run-progress').style.width = '100%';
        renderResult(); renderHistory(); go(2);
        status('Your mission is ready. Download the catalog or keep the capability.','Votre mission est prête. Téléchargez le catalogue ou conservez la capacité.');
    } catch (error) {
        if (token !== runToken) return;
        go(0);
        if (error?.name !== 'AbortError') showError(error);
    } finally {
        if (token === runToken) { busy = false; controls(false); controller = null; }
    }
}
function cancelRun(focus = true) {
    runToken += 1; controller?.abort(); controller = null; busy = false; controls(false);
    go(0,focus);
    status('Run canceled. Your previous project history is preserved.','Exécution annulée. L’historique précédent de votre projet est conservé.');
}
function renderResult() {
    if (!result || !mission) return;
    const rec = result.reconciliation;
    $('matched-count').textContent = number(rec.matchedPairs);
    $('unmatched-count').textContent = number(rec.unmatchedLeft.length + rec.unmatchedRight.length);
    $('conflict-count').textContent = number(rec.conflicts.length);
    $('result-summary').textContent = say(
        `${number(mission.left.rows.length + mission.right.rows.length)} source records reconciled. Matching pairs, unmatched rows and exact value differences are ready to download.`,
        `${number(mission.left.rows.length + mission.right.rows.length)} lignes sources rapprochées. Correspondances, lignes non reliées et divergences exactes sont prêtes à télécharger.`
    );
    const baseline = result.strategies.find(s => s.strategyId === 'nested_scan');
    const best = result.strategies.find(s => s.strategyId === 'smaller_side_hash');
        const strongest = [...result.strategies].filter(s => ['fixed_right_hash','sort_merge'].includes(s.strategyId)).sort((a,b)=>a.metrics.logicalOperations-b.metrics.logicalOperations)[0];
    const competitiveGain = strongest.metrics.logicalOperations - best.metrics.logicalOperations;
    const competitivePercent = strongest.metrics.logicalOperations ? 100 * competitiveGain / strongest.metrics.logicalOperations : 0;
    $('advantage-title').textContent = competitiveGain > 0 ? say(
        `${percentage(competitivePercent)}% less logical work than the strongest alternative.`,
        `${percentage(competitivePercent)} % de travail logique en moins que la meilleure alternative.`
    ) : competitiveGain === 0 ? say(
        'Matches the strongest alternative on logical work.',
        'Même travail logique que la meilleure alternative.'
    ) : say('The strongest alternative does less logical work.','La meilleure alternative effectue moins de travail logique.');
    $('advantage-detail').textContent = say(
        `The smaller-side candidate uses ${number(best.metrics.logicalOperations)} logical operations, versus ${number(strongest.metrics.logicalOperations)} for ${strategyName(strongest)} and ${number(baseline.metrics.logicalOperations)} for the current nested scan. All return the same exact matches.`,
        `La candidate du petit côté utilise ${number(best.metrics.logicalOperations)} opérations logiques, contre ${number(strongest.metrics.logicalOperations)} pour ${strategyName(strongest)} et ${number(baseline.metrics.logicalOperations)} pour le balayage actuel. Toutes produisent les mêmes correspondances exactes.`
    );
    $('comparison-bars').replaceChildren(); $('comparison-table').replaceChildren();
    const max = Math.max(1,...result.strategies.map(s => s.metrics.logicalOperations));
    for (const strategy of result.strategies) {
        const block = node('div',$('comparison-bars'));
        const heading = node('div',block,undefined,'bar-heading');
        node('span',heading,strategyName(strategy)); node('strong',heading,number(strategy.metrics.logicalOperations));
        const track = node('div',block,undefined,'bar-track');
        const fill = node('div',track,undefined,`bar-fill${strategy.strategyId === best.strategyId ? ' best' : ''}`);
        fill.style.setProperty('--bar-width',`${100 * strategy.metrics.logicalOperations / max}%`);
        const row = node('tr',$('comparison-table'));
        node('td',row,strategyName(strategy)); node('td',row,number(strategy.metrics.logicalOperations));
        node('td',row,number(strategy.metrics.indexedRows)); node('td',row,number(strategy.metrics.sortedRows));
        node('td',row,`${percentage(strategy.metrics.elapsedMicros / 1000)} ms`);
        node('td',row,strategy.verified?say('Exact match','Correspondance exacte'):say('Unverified','Non vérifié'),'verified');
    }
    for (const comparison of result.assessment.comparisons.filter(c => c.strategyId !== 'nested_scan')) {
        const alternative = result.strategies.find(s => s.strategyId === comparison.strategyId);
        const text = say(
            `Against ${strategyName(alternative)}: ${number(comparison.logicalOperationsSaved)} logical operations saved; ${number(comparison.auxiliaryRowsSaved)} fewer auxiliary row references (negative means more).`,
            `Face à ${strategyName(alternative)} : ${number(comparison.logicalOperationsSaved)} opérations logiques économisées ; ${number(comparison.auxiliaryRowsSaved)} références de lignes auxiliaires en moins (négatif = davantage).`
        );
        const line = node('p',$('advantage-detail'),text); line.className = 'competitive-note';
    }
    const preview = $('joined-preview'); preview.replaceChildren();
    const table = node('table',preview), thead = node('thead',table), header = node('tr',thead), body = node('tbody',table);
    for (const text of [...mission.left.headers.map(h=>`left.${h}`),...mission.right.headers.map(h=>`right.${h}`)]) node('th',header,text);
    for (const [left,right] of best.pairs.slice(0,6)) { const tr = node('tr',body); for (const value of [...mission.left.rows[left],...mission.right.rows[right]]) node('td',tr,value); }
}
function syncName() {
    if (!dossier) return;
    const name = $('project-name').value.trim();
    if (!name || name.length > 80) throw Error(say('Give your project a name from 1 to 80 characters.','Donnez au projet un nom de 1 à 80 caractères.'));
    dossier = project.renameProject(dossier,name);
}
function renderHistory() {
    $('cycle-history').replaceChildren();
    $('cycle-count').textContent = dossier ? say(`${dossier.cycles.length} ${dossier.cycles.length === 1?'cycle':'cycles'}`,`${dossier.cycles.length} ${dossier.cycles.length === 1?'cycle':'cycles'}`) : say('No cycles yet','Aucun cycle');
    if (!dossier) return;
    for (const [index,cycle] of dossier.cycles.entries()) {
        const item = node('li',$('cycle-history'));
        node('strong',item,say(`Cycle ${index+1} · Catalog reconciliation`,`Cycle ${index+1} · Rapprochement de catalogues`));
        node('span',item,say(`${number(cycle.mission.left.rows.length + cycle.mission.right.rows.length)} source records · ${number(cycle.result.reconciliation.matchedPairs)} matched pairs`,`${number(cycle.mission.left.rows.length + cycle.mission.right.rows.length)} lignes sources · ${number(cycle.result.reconciliation.matchedPairs)} paires`));
        node('small',item,say(`Local engineering run · ${new Intl.DateTimeFormat('en-CA',{dateStyle:'medium',timeStyle:'short'}).format(new Date(cycle.createdAt))}`,`Exécution d’ingénierie locale · ${new Intl.DateTimeFormat('fr-CA',{dateStyle:'medium',timeStyle:'short'}).format(new Date(cycle.createdAt))}`));
    }
}
function download(name, contents, type = 'text/plain;charset=utf-8') {
    const blob = new Blob([contents],{type});
    const url = URL.createObjectURL(blob), anchor = document.createElement('a');
    anchor.href = url; anchor.download = name; document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url),1500);
    status(`Downloaded ${name}. Your browser may ask where to save it.`,`Téléchargement de ${name}. Votre navigateur peut demander où l’enregistrer.`);
}
async function safeDownload(action) {
    clearError();
    try { syncName(); await action(); } catch (error) { showError(error,/name|nom/.test(String(error.message)) ? $('project-name') : undefined); }
}
function fillMission(m) {
    $('left-csv').value = project.tableCsv(m.left); $('right-csv').value = project.tableCsv(m.right);
    setMode('custom');
    checkColumns();
    $('left-key').value = m.left.key; $('right-key').value = m.right.key;
    updateMappingSummary();
}
async function restoreSerialized(serialized) {
    const restored = project.inspectProject(serialized);
    clearCurrent(); dossier = restored; $('project-name').value = restored.name;
    notice = {type:'restored',name:restored.name,cycles:restored.cycles.length};
    if (restored.cycles.length) fillMission(restored.cycles.at(-1).mission);
    else setMode('custom');
    go(0);
    $('restored-note').textContent = say(
        `“${restored.name}” restored with ${restored.cycles.length} historical ${restored.cycles.length === 1 ? 'cycle' : 'cycles'}. Inputs are ready. Run again for fresh local evidence; imported timings and claims are not new observations.`,
        `« ${restored.name} » restauré avec ${restored.cycles.length} ${restored.cycles.length === 1 ? 'cycle historique' : 'cycles historiques'}. Les données sont prêtes. Relancez pour de nouvelles preuves locales ; temps et déclarations importés restent historiques.`
    );
    renderNotice(); renderHistory();
    status('Project restored. Run the inputs again for current evidence.','Projet restauré. Relancez les données pour obtenir des preuves actuelles.');
}
$('error-setup').addEventListener('click',() => { clearError(); go(0); });
$('error-example').addEventListener('click',() => { clearError(); go(0); setMode('example'); });
$('hero-start').addEventListener('click',() => { setMode('example'); run(sample); });
$('example-start').addEventListener('click',() => run(sample));
$('hero-custom').addEventListener('click',() => { go(0); setMode('custom',true); });
$('mode-example').addEventListener('click',() => setMode('example'));
$('mode-custom').addEventListener('click',() => setMode('custom',true));
$('check-columns').addEventListener('click',checkColumns);
$('cancel-run').addEventListener('click',() => cancelRun());
$('custom-form').addEventListener('submit',event => {
    event.preventDefault(); clearError();
    if ($('key-mapping').hidden && !checkColumns()) return;
    try {
        const next = alpha.createJoinMission({leftCsv:$('left-csv').value,rightCsv:$('right-csv').value,leftKey:$('left-key').value,rightKey:$('right-key').value});
        run(next);
    } catch (error) { showError(error); }
});
for (const side of ['left','right']) {
    $(`${side}-csv`).addEventListener('input',() => { clearCurrent(); importToken += 1; $('key-mapping').hidden = true; $(`${side}-file-name`).textContent = ''; });
    $(`${side}-key`).addEventListener('change',() => { clearCurrent(); updateMappingSummary(); });
    $(`${side}-file`).addEventListener('change',async () => {
        const input = $(`${side}-file`), file = input.files[0]; if (!file) return;
        const token = ++importToken, expected = revision;
        clearError();
        try {
            if (file.size > 200000) throw Error(say('Choose a CSV no larger than 200 KB. Split a larger catalog before importing.','Choisissez un CSV de 200 Ko au maximum. Divisez un catalogue plus volumineux.'));
            const text = new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
            if (token !== importToken || expected !== revision) throw Error(say('Inputs changed while the file was being read. Choose the file again.','Les données ont changé pendant la lecture. Choisissez le fichier à nouveau.'));
            alpha.parseCsv(text);
            clearCurrent(); $(`${side}-csv`).value = text; $(`${side}-file-name`).textContent = file.name;
            $('key-mapping').hidden = true;
            status('CSV loaded. Check your columns when both catalogs are ready.','CSV chargé. Vérifiez les colonnes lorsque les deux catalogues sont prêts.');
        } catch (error) { showError(error,$(`${side}-csv`)); }
        finally { input.value = ''; }
    });
}
for (const [id,key,name] of [['download-joined','joinedCsv','joined-catalog.csv'],['download-unmatched-left','unmatchedLeftCsv','unmatched-reference.csv'],['download-unmatched-right','unmatchedRightCsv','unmatched-second.csv'],['download-conflicts','conflictsCsv','catalog-conflicts.csv']]) {
    $(id).addEventListener('click',() => { if (artifacts) download(name,artifacts[key],'text/csv;charset=utf-8'); });
}
$('keep-capability').addEventListener('click',() => { if (result) { renderHistory(); go(3); } });
$('back-evidence').addEventListener('click',() => { if (result) go(2); });
$('edit-inputs').addEventListener('click',() => { if (mission) fillMission(mission); go(0); });
$('next-cycle').addEventListener('click',() => {
    try {
        syncName();
        if (dossier?.cycles.length >= 6) throw Error(say('This project contains six full cycles. Download your project and workspace, then open a fresh page for a separate project.','Ce projet contient six cycles. Téléchargez le projet et l’espace, puis ouvrez une nouvelle page pour un projet distinct.'));
        if (mission) fillMission(mission);
        clearCurrent(); go(0);
        notice = {type:'next'};
        $('restored-note').textContent = say('Your history is preserved. Replace either catalog or run these inputs again to begin the next cycle.','Votre historique est conservé. Remplacez un catalogue ou relancez ces données pour le cycle suivant.');
        $('restored-note').hidden = false;
    } catch (error) { showError(error); }
});
$('download-workspace').addEventListener('click',() => safeDownload(async () => download('my-successor-workspace.html',await exportPortable(dossier),'text/html;charset=utf-8')));
$('download-tool').addEventListener('click',() => safeDownload(() => download('successor-catalog-capability.mjs',project.buildCapability(mission,result),'text/javascript;charset=utf-8')));
$('download-report').addEventListener('click',() => safeDownload(() => download('successor-alpha-evidence.html',project.buildReport(mission,result,{name:dossier.name,goal:dossier.goal,language}),'text/html;charset=utf-8')));
$('download-project').addEventListener('click',() => safeDownload(() => download('my-successor-project.json',project.serializeProject(dossier),'application/json')));
for (const [id,route] of [['handoff-usdc','USDC'],['handoff-agialpha','AGIALPHA']]) $(id).addEventListener('click',() => safeDownload(() => download(`successor-${route.toLowerCase()}-unfunded-draft.json`,JSON.stringify(project.prepareHandoff(dossier,route),null,2),'application/json')));
function renderValue() {
    $('value-result').hidden = !valueEstimate;
    if (!valueEstimate) return;
    const currency = $('value-currency').value;
    const money = cents => new Intl.NumberFormat(language === 'fr' ? 'fr-CA' : 'en-CA',{style:'currency',currency}).format(cents/100);
    $('value-summary').textContent = say(
        `Projected monthly time value: ${money(valueEstimate.monthlyCents)}. After entered setup cost, first month: ${money(valueEstimate.netFirstMonthCents)}. Setup recovery: ${valueEstimate.breakEvenMonths === null ? 'not established' : `${number(valueEstimate.breakEvenMonths)} ${valueEstimate.breakEvenMonths === 1 ? 'month' : 'months'}`}.`,
        `Valeur mensuelle projetée du temps : ${money(valueEstimate.monthlyCents)}. Premier mois après le coût initial saisi : ${money(valueEstimate.netFirstMonthCents)}. Récupération du coût initial : ${valueEstimate.breakEvenMonths === null ? 'non établie' : `${number(valueEstimate.breakEvenMonths)} mois`}.`
    );
}
function wholeInput(id) {
    const input = $(id);
    if (!/^\d+$/.test(input.value) || Number(input.value) > 1000000) {
        input.setAttribute('aria-invalid','true'); input.focus();
        throw Error(say('Enter whole, nonnegative minutes and monthly runs, up to 1,000,000.','Saisissez des minutes et exécutions entières, non négatives, jusqu’à 1 000 000.'));
    }
    return Number(input.value);
}
function centsInput(id) {
    const input = $(id);
    if (!/^\d+(?:\.\d{1,2})?$/.test(input.value) || Number(input.value) > 10000) {
        input.setAttribute('aria-invalid','true'); input.focus();
        throw Error(say('Enter a nonnegative amount up to 10,000, using at most two decimal places.','Saisissez un montant non négatif jusqu’à 10 000, avec deux décimales au maximum.'));
    }
    return Math.round(Number(input.value)*100);
}
$('value-form').addEventListener('submit',event => {
    event.preventDefault(); $('value-error').hidden = true;
    try {
        valueEstimate = project.estimateValue({beforeMinutes:wholeInput('value-before'),afterMinutes:wholeInput('value-after'),runsPerMonth:wholeInput('value-frequency'),hourlyValueCents:centsInput('value-hourly'),setupCents:centsInput('value-setup')});
        renderValue();
    } catch (error) { $('value-error').hidden = false; $('value-error').textContent = errorMessage(error); }
});
$('value-form').addEventListener('input',() => { valueEstimate = null; $('value-result').hidden = true; $('value-error').hidden = true; $('value-form').querySelectorAll('[aria-invalid]').forEach(el=>el.removeAttribute('aria-invalid')); });
$('download-value').addEventListener('click',() => { if (valueEstimate) download('successor-alpha-value-assumptions.json',JSON.stringify({...valueEstimate,currency:$('value-currency').value,projectId:dossier?.id,cycleId:dossier?.cycles.at(-1)?.id},null,2),'application/json'); });
$('project-name').addEventListener('input',() => { $('project-name').removeAttribute('aria-invalid'); });
for (const id of ['open-project-top','open-project-bottom']) $(id).addEventListener('click',() => $('restore-project').click());
$('restore-project').addEventListener('change',async () => {
    const file = $('restore-project').files[0]; if (!file) return;
    const token = ++importToken, expected = revision;
    try {
        if (file.size > 2000000) throw Error(say('Choose a project JSON file no larger than 2 MB.','Choisissez un fichier JSON de projet de 2 Mo au maximum.'));
        const text = new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
        if (token !== importToken || revision !== expected) throw Error(say('Inputs changed while the project was being read. Reopen the file.','Les données ont changé pendant la lecture du projet. Rouvrez le fichier.'));
        await restoreSerialized(text);
    } catch (error) { showError(error); }
    finally { $('restore-project').value = ''; }
});
function applyTextSize() {
    document.documentElement.dataset.textSize = largeText ? 'large' : 'standard';
    document.body.classList.toggle('large-text',largeText);
    $('text-size').setAttribute('aria-pressed',String(largeText));
}
$('text-size').addEventListener('click',() => { largeText = !largeText; applyTextSize(); });
applyTextSize();
$('lang-en').addEventListener('click',() => { language = 'en'; translate(); });
$('lang-fr').addEventListener('click',() => { language = 'fr'; translate(); });
$('contract-list').replaceChildren();
if (typeof DEPLOYMENT !== 'undefined' && DEPLOYMENT.contracts) {
    for (const entry of Object.values(DEPLOYMENT.contracts)) {
        if (!/^0x[0-9a-fA-F]{40}$/.test(entry.address)) continue;
        const a = node('a',$('contract-list'));
        a.href = `https://etherscan.io/address/${entry.address}#code`; a.target = '_blank'; a.rel = 'noopener noreferrer';
        node('span',a,entry.name); node('code',a,entry.address);
    }
}
translate(); go(0,false);
const saved = $('saved-project').textContent.trim();
if (saved && saved !== '{}') {
    try { restoreSerialized(saved).catch(showError); } catch (error) { showError(error); }
}
