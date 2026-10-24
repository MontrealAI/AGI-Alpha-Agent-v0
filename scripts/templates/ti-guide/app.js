// SPDX-License-Identifier: Apache-2.0
const $ = id => document.getElementById(id);
const english = Object.fromEntries([...document.querySelectorAll('[data-t]')].map(el => [el.dataset.t, el.innerHTML]));
const french = {
    skip:'Aller à la tâche', brand:'INTELLIGENCE TRANSFORMATIONNELLE',eyebrow:'UN PETIT CHANGEMENT. UN RÉSULTAT UTILE.',
    title:'Deux listes.<br>La suite devient claire.',lead:'Repérez ce qui mérite attention. Rassemblez les écarts. Gardez une méthode à réutiliser.',
    free:'Gratuit · Sans compte · Sans installation · Vos données restent ici',nav1:'Votre objectif',nav2:'L’obstacle',nav3:'Une autre méthode ?',nav4:'Votre résultat',
    reset:'Réinitialiser',task:'Comparer deux listes et voir ce qui mérite attention.',sampleNote:'Commencez par un petit exemple de produits. La même méthode accepte vos fichiers CSV sans données personnelles.',
    listA:'Liste A',listB:'Liste B',own:'Utiliser mes propres fichiers CSV',
    privacy:'Avant l’import : tout est traité dans ce navigateur. Les fichiers ne sont ni téléversés ni envoyés à un service d’IA. Utilisez des données publiques ou autorisées sans renseignements personnels ; évitez les données sensibles. Maximum 200 Ko et 1 500 lignes par liste.',
    fileA:'Choisir le CSV de la liste A',fileB:'Choisir le CSV de la liste B',pasteA:'Ou coller le CSV de la liste A',pasteB:'Ou coller le CSV de la liste B',keyA:'Colonne d’identification dans la liste A',keyB:'Colonne d’identification dans la liste B',
    keyHelp:'La colonne d’identification désigne le même article dans les deux listes, par exemple un code produit. Les identifiants répétés sont conservés ; chaque paire correspondante est comparée.',
    csvHelp:'CSV signifie colonnes séparées par des virgules, avec une ligne d’en-tête. La comparaison est exacte, y compris les espaces, la casse et le format des nombres. Seules les autres colonnes de même nom sont comparées. Maximum 32 colonnes, 4 096 caractères par cellule et 10 000 paires correspondantes.',
    sample:'Reprendre l’exemple',try:'Essayer maintenant',open:'Ouvrir un espace sauvegardé',narrow:'Cette édition compare des listes. Elle n’exécute pas de tâches en texte libre, n’utilise pas de modèle de langage en direct et ne décide pas quelle source est correcte.',
    obstacleLead:'Voici ce que montrent réellement les données actuelles.',yourGoal:'Votre objectif',goal:'Repérer tous les articles à examiner, sans perdre le moindre écart sous-jacent.',confirm:'Continuez si c’est le résultat souhaité. Vous pouvez aussi conserver une fiche distincte pour chaque exception originale.',confirmButton:'Oui — essayer une autre méthode',keep:'Conserver la méthode originale',
    changeLead:'Testez une autre organisation des mêmes preuves : une fiche d’action pour chaque article concerné.',originalLabel:'La méthode originale',testedLabel:'Le changement testé',beforeText:'Examiner séparément chaque ligne sans correspondance ou paire de lignes divergentes.',afterText:'Rassembler les exceptions du même identifiant exact dans une fiche d’action. Conserver toutes les références et valeurs divergentes.',
    measurement:'Ces chiffres mesurent les fiches et la couverture des preuves, pas le temps gagné, le travail sous-jacent ou une précision accrue. Aucune correction automatique n’a été faite.',grouped:'Vue par action',detailed:'Vue détaillée originale',useGrouped:'Utiliser cette vue par action',ready:'Un résultat utile. Une méthode à garder.',supportsLabel:'Ce que le résultat permet de conclure',unresolvedTitle:'Ce qui reste à résoudre',unresolved:'Vous devez encore vérifier les absences et choisir les bonnes valeurs. Aucune liste n’est présumée correcte. Le regroupement conserve les désaccords sans les trancher. L’effort humain, le temps gagné et la précision accrue n’ont pas été mesurés.',
    downloadActions:'Télécharger mon plan d’action',downloadDiffs:'Télécharger tous les écarts',save:'Sauvegarder cet espace',reuse:'Réutiliser avec d’autres données',saveHint:'La sauvegarde télécharge un seul fichier HTML autonome avec vos données, résultats et réglages. Rouvrez-le hors ligne : il contrôle le résultat enregistré et peut comparer de nouvelles données. Ce fichier contient vos données ; conservez-le dans un endroit approprié.',inspect:'Examiner toutes les fiches de résultat',cancel:'Annuler',back:'← Retour',local:'TRAITEMENT LOCAL · AUCUN TÉLÉVERSEMENT',how:'Voir le fonctionnement',howText:'Ce guide utilise le code de comparaison et de regroupement publié d’AGI ALPHA. La correspondance exacte et les règles déterministes s’exécutent localement dans un worker. Chaque paire divergente et ligne sans correspondance reste traçable. Les numéros désignent les lignes de données après l’en-tête, pas les lignes physiques du texte.',howLimit:'Les colonnes de noms différents sont signalées comme non examinées. Les identifiants répétés produisent toutes les paires correspondantes dans les limites indiquées. Aucun rapprochement approximatif, modification automatique, examen externe, paiement ou exécution native Harness/Fleet. Les cellules CSV ressemblant à une formule reçoivent une apostrophe ; l’espace conserve les données exactes.',json:'Télécharger l’espace JSON et les preuves',source:'Code source et validation',paper:'Lire l’article fondateur',advanced:'Outils de catalogue existants',licenses:'Licences du code',footer:'Ouvrir une tâche. Changer une contrainte amovible. Garder ce qui aide.',disclaimer:'Prototype de recherche et avis',
};
let language = 'en', step = 1, input = {...guide.SAMPLE}, result = null, approach = 'grouped', view = 'grouped';
let worker = null, workerUrl = null, token = 0, busy = false, runId = '', createdAt = '', restored = false;
let reading = 0, fileVersions = {left:0,right:0}, restoreVersion = 0, trace = [];
let fileErrors = {left:null,right:null};
const say = (en, fr) => language === 'fr' ? fr : en;
const text = (id, en, fr) => { $(id).textContent = say(en, fr); };
function node(tag, parent, value, className) {
    const el = document.createElement(tag); if (value !== undefined) el.textContent = String(value);
    if (className) el.className = className; parent.append(el); return el;
}
function errorMessage(message) {
    const map = {
        'CSV needs a header row.':'Le CSV doit contenir une ligne d’en-tête.',
        'CSV headers must be nonempty and unique.':'Les en-têtes doivent être non vides et uniques.',
        'Every CSV row must have the header column count.':'Chaque ligne doit avoir le même nombre de colonnes que l’en-tête.',
        'Unclosed quoted CSV cell.':'Une cellule entre guillemets n’est pas fermée.',
        'Quote inside an unquoted CSV cell.':'Un guillemet apparaît dans une cellule non délimitée.',
        'Unexpected text after a closing CSV quote.':'Texte inattendu après le guillemet fermant.',
        'CSV cannot contain NUL characters.':'Le CSV ne peut pas contenir de caractères NUL.',
        'Join keys must be nonempty exact strings.':'Chaque ligne doit avoir un identifiant non vide.',
        'Choose a key column present in each CSV.':'Choisissez une colonne d’identification présente dans chaque CSV.',
        'Join exceeds 10000 output pairs.':'La comparaison dépasse 10 000 paires. Réduisez les doublons ou la taille des listes.',
        'Each CSV must contain at most 200000 UTF-8 bytes.':'Chaque CSV est limité à 200 000 octets UTF-8.',
        'CSV exceeds 1500 data rows.':'Chaque CSV est limité à 1 500 lignes de données.',
        'CSV exceeds 32 columns.':'Chaque CSV est limité à 32 colonnes.',
        'CSV cells exceed 4096 characters.':'Chaque cellule est limitée à 4 096 caractères.',
        'Full difference evidence exceeds 1.5 MB. Use smaller lists; nothing was truncated.':'Les preuves complètes dépassent 1,5 Mo. Réduisez les listes ; aucun résultat n’a été tronqué.',
        'The saved results differ from recomputation. No result or authority was restored.':'Les résultats enregistrés diffèrent du nouveau calcul. Aucun résultat ni autorité n’a été restauré.',
        'Unsupported workspace or method version. Reopen its original saved HTML.':'Espace ou version de méthode non pris en charge. Rouvrez son fichier HTML d’origine.',
    };
    return language === 'fr' ? (map[message] || 'Opération refusée : ' + message) : message;
}
function showError(message, id = 'error') { $(id).textContent = errorMessage(message); $(id).hidden = false; }
function clearError() { $('error').hidden = true; $('status').textContent = ''; }
function setLanguage(value) {
    language = value; document.documentElement.lang = value;
    for (const el of document.querySelectorAll('[data-t]')) {
        const content = (value === 'fr' ? french : english)[el.dataset.t];
        if (el.dataset.t === 'title') el.innerHTML = content; else el.textContent = content;
    }
    $('en').setAttribute('aria-pressed',String(value === 'en')); $('fr').setAttribute('aria-pressed',String(value === 'fr'));
    refreshPreviews(); render(false);
}
function table(parent, headers, rows) {
    const wrap = node('div',parent,undefined,'table-wrap'), t = node('table',wrap), head = node('tr',node('thead',t));
    for (const name of headers) { const th = node('th',head,name); th.scope = 'col'; }
    const body = node('tbody',t);
    for (const row of rows) { const tr = node('tr',body); for (const cell of row) node('td',tr,cell); }
    return wrap;
}
function updatePreview(side) {
    const target = $(side+'-preview'), select = $(side+'-key'); target.replaceChildren(); $(side+'-error').hidden = true;
    try {
        if(fileErrors[side])throw Error(fileErrors[side]);
        const data = guide.preview($(side+'-csv').value), previous = select.value || input[side+'Key'];
        select.replaceChildren();
        for (const key of data.headers) { const option = node('option',select,key); option.value = key; }
        select.value = data.headers.includes(previous) ? previous : data.headers[0];
        table(target,data.headers,data.rows.slice(0,4));
        if (data.rows.length > 4) node('p',target,say(`Showing 4 of ${data.rows.length} rows.`, `Aperçu : 4 lignes sur ${data.rows.length}.`));
        $(side+'-count').textContent = say(`${data.rows.length} data rows`,`${data.rows.length} lignes`);
        return true;
    } catch (error) {
        $(side+'-count').textContent = say('Needs attention','À vérifier'); select.replaceChildren();
        showError(say(side === 'left' ? 'List A: ' : 'List B: ',side === 'left' ? 'Liste A : ' : 'Liste B : ')+errorMessage(error.message), side+'-error');
        node('p',target,errorMessage(error.message)); return false;
    }
}
function refreshPreviews() {
    const a = updatePreview('left'), b = updatePreview('right');
    $('try').disabled = !a || !b || busy || reading > 0;
    $('try').textContent = $('own-data').open ? say('Compare my lists','Comparer mes listes') : say('Try it now','Essayer maintenant');
}
function applyInput(value) {
    fileErrors={left:null,right:null};
    input = {...value}; $('left-csv').value = value.leftCsv; $('right-csv').value = value.rightCsv;
    refreshPreviews(); $('left-key').value = value.leftKey; $('right-key').value = value.rightKey;
}
function currentInput() { return {leftCsv:$('left-csv').value,rightCsv:$('right-csv').value,leftKey:$('left-key').value,rightKey:$('right-key').value}; }
function stop() {
    token++; worker?.terminate(); worker = null; if (workerUrl) URL.revokeObjectURL(workerUrl); workerUrl = null;
    busy = false; $('busy').hidden = true;
    for (const el of document.querySelectorAll('button,input,textarea,select')) if (!['download-json'].includes(el.id)) el.disabled = false;
    $('download-json').disabled = !result; refreshPreviews();
}
function invalidate() { restoreVersion++; stop(); result = null; restored = false; runId = ''; step = 1; clearError(); render(false); }
async function execute(payload) {
    if (busy || reading) return;
    clearError(); result = null; restored = false; $('download-json').disabled = true;
    busy = true; const mine = ++token; trace = [];
    for (const el of document.querySelectorAll('button,input,textarea,select')) el.disabled = !['cancel','reset','en','fr'].includes(el.id);
    $('busy').hidden = false; $('progress').value = 0; text('progress-text','Reading the inputs…','Lecture des données…');
    try {
        if (typeof Worker === 'undefined' || !crypto.subtle) throw Error(say('This browser cannot run the local comparison. Use a current browser; no upload fallback is used.','Ce navigateur ne permet pas le calcul local. Utilisez un navigateur récent ; aucun téléversement de remplacement.'));
        workerUrl = URL.createObjectURL(new Blob([WORKER_SOURCE],{type:'text/javascript'})); worker = new Worker(workerUrl);
        const value = await new Promise((resolve,reject) => {
            worker.onmessage = ({data}) => {
                if (mine !== token) return;
                if (data.type === 'progress') {
                    trace.push(data.stage); const stages = ['parse','compare','preserve','complete'];
                    $('progress').value = stages.indexOf(data.stage)+1;
                    const labels = {parse:['Reading the CSV columns…','Lecture des colonnes CSV…'],compare:['Comparing exact identifiers and values…','Comparaison des identifiants et valeurs exacts…'],preserve:['Checking every evidence reference…','Contrôle de chaque référence de preuve…'],complete:['Comparison complete.','Comparaison terminée.']};
                    $('progress-text').textContent = say(...labels[data.stage]);
                } else if (data.type === 'result') resolve(data.value); else reject(Error(data.message));
            };
            worker.onerror = () => reject(Error(say('The local worker could not finish. Your input files were not uploaded. Try smaller lists or reopen your saved workspace.','Le calcul local n’a pas abouti. Aucun fichier n’a été téléversé. Essayez des listes plus petites ou rouvrez l’espace sauvegardé.')));
            worker.postMessage({...payload,sourceHash:SOURCE_HASH});
        });
        if (mine !== token) return;
        if (payload.kind === 'restore') {
            applyInput(value.input); result = value.result; approach = value.approach; runId = value.runId; createdAt = value.createdAt;
            language = value.language; restored = true; step = 4; setLanguage(language);
        } else { input = {...payload.input}; result = value; approach = 'grouped'; view = 'grouped'; runId = crypto.randomUUID(); createdAt = new Date().toISOString(); step = 2; }
        stop(); render();
        if (restored) text('status','Saved results rechecked locally. This is a restored run, with no imported authority.','Résultats enregistrés contrôlés localement. Il s’agit d’un résultat restauré, sans autorité importée.');
    } catch (error) { if (mine === token) { stop(); step = 1; render(); showError(error.message); } }
}
function metric(parent, count, en, fr) { const box = node('div',parent,undefined,'metric'); node('strong',box,count); node('span',box,say(en,fr)); }
function describe(diff) {
    if (diff.kind === 'conflict') return say(`List A row ${diff.leftRow} says “${diff.leftValue}”; List B row ${diff.rightRow} says “${diff.rightValue}” for ${diff.field}.`, `Liste A, ligne ${diff.leftRow} : « ${diff.leftValue} » ; liste B, ligne ${diff.rightRow} : « ${diff.rightValue} » pour ${diff.field}.`);
    return diff.kind === 'missing_from_right' ? say(`List A row ${diff.leftRow} has no matching identifier in List B.`,`La ligne ${diff.leftRow} de la liste A n’a pas d’identifiant correspondant dans la liste B.`) : say(`List B row ${diff.rightRow} has no matching identifier in List A.`,`La ligne ${diff.rightRow} de la liste B n’a pas d’identifiant correspondant dans la liste A.`);
}
function detailRows(parent, differences) {
    let shown = 0; const holder = node('div',parent), more = node('button',parent);
    function next() {
        shown = Math.min(shown+30,differences.length); holder.replaceChildren();
        table(holder,[say('Item','Article'),say('Difference','Écart'),say('Evidence reference','Référence')],differences.slice(0,shown).map(d => [d.key,describe(d),`${d.id} → ${d.action}`]));
        more.hidden = shown >= differences.length;
        more.textContent = say(`Show more (${shown}/${differences.length})`,`Afficher la suite (${shown}/${differences.length})`);
    }
    more.addEventListener('click',next); next();
}
function resultView(parent, mode) {
    parent.replaceChildren();
    if (!result.differences.length) { node('p',parent,say('No differences in the compared columns.','Aucun écart dans les colonnes comparées.')); return; }
    if (mode === 'original') { detailRows(parent,result.differences); return; }
    const holder = node('div',parent), more = node('button',parent); let shown = 0;
    function next() {
        for (const action of result.resolution.actions.slice(shown,shown+10)) {
            const article = node('article',holder,undefined,'action-record');
            node('h3',article,`${action.key} · ${say('Action','Action')} ${action.id.replace('action-','')}`);
            const type = action.type === 'review_shared_values' ? say('Review conflicting values','Examiner les valeurs divergentes') : action.type === 'missing_from_left' ? say('Check omission from List A','Vérifier l’absence dans la liste A') : say('Check omission from List B','Vérifier l’absence dans la liste B');
            node('p',article,type); node('p',article,say(`${action.occurrences.length} original exception reference(s). No value has been chosen.`,`${action.occurrences.length} référence(s) d’exception originale. Aucune valeur n’a été choisie.`));
            const details = node('details',article); node('summary',details,say('See every difference and source row','Voir tous les écarts et lignes sources'));
            details.addEventListener('toggle',() => { if (details.open && !details.dataset.loaded) { details.dataset.loaded='true'; detailRows(details,result.differences.filter(x => x.action === action.id)); } });
        }
        shown = Math.min(shown+10,result.resolution.actions.length); more.hidden = shown >= result.resolution.actions.length;
        more.textContent = say(`Show more actions (${shown}/${result.resolution.actions.length})`,`Afficher la suite (${shown}/${result.resolution.actions.length})`);
    }
    more.addEventListener('click',next); next();
}
function render(focus = true) {
    const titles = [say('What do you want to accomplish?','Que voulez-vous accomplir ?'),say('What makes this difficult?','Qu’est-ce qui rend cela difficile ?'),say('Try a better setup.','Essayez une autre méthode.'),say('Use the result.','Utilisez le résultat.')];
    $('step-title').textContent = titles[step-1]; $('step-count').textContent = say(`STEP ${step} OF 4`,`ÉTAPE ${step} SUR 4`);
    for (let i=1;i<=4;i++) { $('step-'+i).hidden = step!==i; const el = document.querySelector(`[data-step="${i}"]`); if(step===i)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current'); }
    $('back').hidden = step === 1; $('download-json').disabled = !result;
    if (result) {
        const m = result.metrics, r = result.resolution;
        $('obstacle-metrics').replaceChildren(); metric($('obstacle-metrics'),m.leftRows+m.rightRows,'input rows','lignes en entrée'); metric($('obstacle-metrics'),m.unmatchedKeys,'unmatched identifiers','identifiants sans correspondance'); metric($('obstacle-metrics'),m.conflictingPairs,'conflicting row pairs','paires divergentes');
        $('obstacle-example').replaceChildren();
        const d = result.differences[0]; node('h3',$('obstacle-example'),d ? say(`An actual example: ${d.key}`,`Un exemple réel : ${d.key}`) : say('No exception found.','Aucune exception trouvée.'));
        node('p',$('obstacle-example'),d ? describe(d) : say('There is nothing to group in the compared columns. You can keep the original view.','Il n’y a rien à regrouper dans les colonnes comparées. Vous pouvez conserver la vue originale.'));
        const repeated = r.actions.find(x => x.occurrences.length > 1);
        if (repeated) node('p',$('obstacle-example'),say(`“${repeated.key}” appears in ${repeated.occurrences.length} exception records. Those records concern the same identifier.`,`« ${repeated.key} » apparaît dans ${repeated.occurrences.length} fiches d’exception. Elles concernent le même identifiant.`));
        $('input-warnings').replaceChildren();
        node('p',$('input-warnings'),say(`Compared columns: ${m.comparedColumns.join(', ') || 'none'}. Matching row pairs: ${m.matchedPairs}. Unmatched source rows: ${m.unmatchedRows}.`,`Colonnes comparées : ${m.comparedColumns.join(', ') || 'aucune'}. Paires correspondantes : ${m.matchedPairs}. Lignes sans correspondance : ${m.unmatchedRows}.`));
        node('p',$('input-warnings'),say(`Repeated identifiers: ${m.leftDuplicates.keys} in List A, ${m.rightDuplicates.keys} in List B. All matching pairs are retained.`,`Identifiants répétés : ${m.leftDuplicates.keys} dans A, ${m.rightDuplicates.keys} dans B. Toutes les paires correspondantes sont conservées.`));
        if (m.unsharedLeft.length || m.unsharedRight.length) node('p',$('input-warnings'),say(`Not compared because column names do not match: A [${m.unsharedLeft.join(', ')}]; B [${m.unsharedRight.join(', ')}].`,`Non comparées, car les noms diffèrent : A [${m.unsharedLeft.join(', ')}] ; B [${m.unsharedRight.join(', ')}].`));
        text('before-count',`${r.burden.pairwiseReviewItems} exception records`,`${r.burden.pairwiseReviewItems} fiches d’exception`); text('after-count',`${m.actionGroups} action records`,`${m.actionGroups} fiches d’action`);
        text('coverage',`${m.evidenceReferences}/${r.coverage.originalOccurrences} original exception references preserved · ${result.differences.length} detailed difference records.`,`${m.evidenceReferences}/${r.coverage.originalOccurrences} références d’exception conservées · ${result.differences.length} fiches d’écart détaillées.`);
        text('grouping-message',r.diagnosis.groupingReducesDecisionItems ? 'Grouping brings repeated exceptions together. Keep it only if reviewing one item at a time helps your goal.' : 'Grouping did not reduce the number of records. Keeping the original approach is a useful outcome.',r.diagnosis.groupingReducesDecisionItems ? 'Le regroupement rassemble les exceptions répétées. Conservez-le seulement si examiner un article à la fois sert votre objectif.' : 'Le regroupement n’a pas réduit le nombre de fiches. Conserver la méthode originale est un résultat utile.');
        if (step === 3) { resultView($('step3-view'),view); $('view-grouped').setAttribute('aria-pressed',String(view==='grouped')); $('view-detail').setAttribute('aria-pressed',String(view==='original')); }
        if (step === 4) {
            text('result-summary',`${m.actionGroups} items need attention; ${m.evidenceReferences} original exception references retained.`,`${m.actionGroups} articles à examiner ; ${m.evidenceReferences} références d’exception conservées.`);
            text('choice-summary',approach==='grouped' ? 'One action record per affected identifier, with the original detailed view retained.' : 'You kept the original detailed approach. The grouped action plan remains an optional companion.',approach==='grouped' ? 'Une fiche d’action par identifiant concerné, avec la vue détaillée originale conservée.' : 'Vous avez conservé la méthode détaillée originale. Le plan regroupé reste un complément facultatif.');
            text('supports-summary',`${m.leftRows} + ${m.rightRows} input rows; ${m.unmatchedKeys} unmatched identifiers; ${m.conflictingPairs} conflicting pairs; ${m.fieldDifferences} conflicting field values. ${m.evidenceReferences}/${r.coverage.originalOccurrences} exception references preserved in ${m.actionGroups} action groups.`,`${m.leftRows} + ${m.rightRows} lignes en entrée ; ${m.unmatchedKeys} identifiants sans correspondance ; ${m.conflictingPairs} paires divergentes ; ${m.fieldDifferences} valeurs de champ divergentes. ${m.evidenceReferences}/${r.coverage.originalOccurrences} références conservées dans ${m.actionGroups} groupes d’action.`);
            resultView($('step4-view'),approach);
        }
        $('receipt').textContent = JSON.stringify({sourceHash:SOURCE_HASH,runId,createdAt,state:restored?'restored_rechecked':'computed_current_inputs',inputIdentities:{left:result.leftIdentity,right:result.rightIdentity},settings:{leftKey:input.leftKey,rightKey:input.rightKey,approach},metrics:m,coverage:r.coverage,stages:trace,limitations:guide.LIMITATIONS},null,2);
    } else $('receipt').textContent = say('Source SHA-256: ','SHA-256 du code : ')+SOURCE_HASH;
    if (focus) $('step-title').focus();
}
function workspace() { if (!result) throw Error('No computed result.'); return guide.makeWorkspace(input,result,{approach,sourceHash:SOURCE_HASH,runId,createdAt,language}); }
function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content],{type})), a = document.createElement('a'); a.href=url; a.download=name; a.click();
    setTimeout(()=>URL.revokeObjectURL(url),30000);
    text('status',`Download prepared: ${name}. Check your browser’s downloads.`,`Téléchargement préparé : ${name}. Consultez les téléchargements du navigateur.`);
}
function safeDownload(action) { try { clearError(); action(); } catch (error) { showError(error.message); } }
function savePortable() {
    const raw = JSON.stringify(workspace()); if(new TextEncoder().encode(raw).length>8000000)throw Error('Workspace exceeds 8 MB.');
    const clone = document.documentElement.cloneNode(true);
    for(const el of clone.querySelectorAll('details'))el.removeAttribute('open');
    clone.querySelector('#saved-workspace').textContent = raw.replaceAll('<','\\u003c');
    for (const el of clone.querySelectorAll('[data-t]')) el.innerHTML = english[el.dataset.t];
    for (const id of ['left-csv','right-csv','left-preview','right-preview','step3-view','step4-view','receipt','status','error']) clone.querySelector('#'+id).textContent='';
    for (const el of clone.querySelectorAll('input[type=file]')) el.removeAttribute('value');
    clone.lang='en'; clone.querySelector('title').textContent = 'My two-list workspace · AGI ALPHA';
    return '<!doctype html>\n'+clone.outerHTML;
}
$('try').addEventListener('click',()=>execute({kind:'compute',input:currentInput()}));
$('confirm').addEventListener('click',()=>{step=3;render();});
for(const id of ['original-2','original-3'])$(id).addEventListener('click',()=>{approach='original';step=4;render();});
$('use-grouped').addEventListener('click',()=>{approach='grouped';step=4;render();});
for(const [id,value] of [['view-grouped','grouped'],['view-detail','original']])$(id).addEventListener('click',()=>{view=value;render(false);});
$('back').addEventListener('click',()=>{step=Math.max(1,step-1);render();});
$('cancel').addEventListener('click',()=>{stop();text('status','Canceled. No partial result was retained. Your inputs are still here.','Annulé. Aucun résultat partiel conservé. Vos données sont toujours présentes.');});
function reset() { restoreVersion++; fileVersions.left++; fileVersions.right++; fileErrors={left:null,right:null}; stop(); result=null;step=1;restored=false;runId='';trace=[];clearError();applyInput(guide.SAMPLE);$('own-data').open=false;for(const s of ['left','right'])$(s+'-file').value='';render(); }
$('reset').addEventListener('click',reset); $('sample').addEventListener('click',reset);
$('reuse').addEventListener('click',()=>{restoreVersion++;stop();result=null;step=1;restored=false;runId='';clearError();$('own-data').open=true;render();text('status','Replace either list. The next comparison computes a new result; this run is not reused. Save first if you want to keep it.','Remplacez une liste. La comparaison suivante calcule un nouveau résultat sans réutiliser celui-ci. Sauvegardez d’abord pour le conserver.');});
$('own-data').addEventListener('toggle',()=>{
    if($('own-data').open)$('own-data').after($('step1-actions'));
    else document.querySelector('.preview-grid').before($('step1-actions'));
    refreshPreviews();
});
for(const side of ['left','right']) {
    $(side+'-csv').addEventListener('input',()=>{fileErrors[side]=null;fileVersions[side]++;invalidate();refreshPreviews();});
    $(side+'-key').addEventListener('change',invalidate);
    $(side+'-file').addEventListener('change',async event=>{
        const file = event.target.files[0]; if(!file)return;fileErrors[side]=null;invalidate(); const version = ++fileVersions[side];reading++;refreshPreviews();
        try {
            if(file.size>200000)throw Error(say('Choose a CSV no larger than 200 KB. Split a larger list first.','Choisissez un CSV de 200 Ko maximum. Divisez d’abord une liste plus grande.'));
            const raw = new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await file.arrayBuffer());
            if(version!==fileVersions[side])return;
            $(side+'-csv').value=raw; refreshPreviews();
        } catch(error) {if(version===fileVersions[side]) {$(side+'-csv').value='';fileErrors[side]=error instanceof TypeError ? say('This file is not valid UTF-8 CSV. Export it as CSV UTF-8 and try again.','Ce fichier n’est pas un CSV UTF-8 valide. Exportez-le en CSV UTF-8 puis réessayez.') : error.message;}}
        finally {reading--;refreshPreviews();}
    });
}
$('en').addEventListener('click',()=>setLanguage('en'));$('fr').addEventListener('click',()=>setLanguage('fr'));
$('download-actions').addEventListener('click',()=>safeDownload(()=>download('my-action-plan.csv',guide.actionPlanCsv(result),'text/csv;charset=utf-8')));
$('download-differences').addEventListener('click',()=>safeDownload(()=>download('full-differences.csv',guide.fullDifferencesCsv(result),'text/csv;charset=utf-8')));
$('download-json').addEventListener('click',()=>safeDownload(()=>download('my-workspace.json',JSON.stringify(workspace(),null,2),'application/json')));
$('save').addEventListener('click',()=>safeDownload(()=>download('my-workspace.html',savePortable(),'text/html;charset=utf-8')));
$('open').addEventListener('click',()=>$('workspace-file').click());
$('workspace-file').addEventListener('change',async event=>{
    const file=event.target.files[0]; if(!file)return;const expected=++restoreVersion;
    try {if(file.size>8000000)throw Error('Workspaces must be no larger than 8 MB.');const raw=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());if(expected===restoreVersion)await execute({kind:'restore',raw});}catch(error){if(expected===restoreVersion)showError(error.message);}finally{event.target.value='';}
});
applyInput(guide.SAMPLE);if(new URLSearchParams(location.search).get('lang')==='fr')setLanguage('fr');render(false);
const saved = $('saved-workspace').textContent;
if(saved.trim() !== 'null')execute({kind:'restore',raw:saved});
window.addEventListener('pagehide',()=>{worker?.terminate();if(workerUrl)URL.revokeObjectURL(workerUrl);});
