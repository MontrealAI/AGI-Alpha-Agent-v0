const $ = id => document.getElementById(id);
const {canonical, parseBounded} = transport;
const {assess, exampleContract, exportRecord, freezeContract, reportTemplate, restoreRecord, validateReport} = evaluation;
let current = null, previous = null, dirty = false, busy = false, epoch = 0, lang = 'en', assessment = null, expiryTimer = null;
const say = (en, fr) => lang === 'fr' ? fr : en;
const pretty = value => JSON.stringify(value, null, 2);
function buttons() {
    $('freeze').disabled = busy;
    $('add').disabled = busy || !current || dirty;
    $('report').disabled = busy || !current || dirty;
    $('save').disabled = busy || !current || dirty;
    $('previous').disabled = busy || !previous;
    $('restore').disabled = busy;
}
function scheduleExpiry() {
    clearTimeout(expiryTimer); expiryTimer = null;
    if (!current || dirty) return;
    const remaining = Date.parse(current.frozen.contract.expiresAt) - Date.now();
    if (remaining > 0) expiryTimer = setTimeout(() => {
        show(); refresh().catch(error => { $('error').textContent = error.message; $('error').hidden = false; });
    }, Math.min(remaining, 2147483647));
}
async function refresh() {
    if (!current || dirty) return;
    const snapshot = current, token = epoch;
    const result = await assess(snapshot.frozen, snapshot.reports);
    if (current === snapshot && token === epoch && !dirty) { assessment = result; show(); }
}
function show() {
    $('result').hidden = !assessment || dirty;
    $('binding').textContent = current && !dirty ? current.frozen.contractDigest : say('Not frozen. Edits require a new contract.', 'Non figé. Les modifications exigent un nouveau contrat.');
    if (assessment) {
        const displayed = Date.now() >= Date.parse(assessment.expiresAt) ? {...assessment, status: 'expired'} : assessment;
        $('comparison').textContent = displayed.status;
        $('scope').textContent = `${current.frozen.contract.mission} · ${assessment.candidate.id} · ${assessment.expiresAt}`;
        $('inspection').textContent = pretty(displayed);
        $('gaps').replaceChildren(...assessment.gaps.map(text => { const li = document.createElement('li'); li.textContent = text; return li; }));
        $('comparisons').replaceChildren(...assessment.comparisons.map(row => {
            const p = document.createElement('p'); p.textContent = `${row.metricId}: ${row.status}; ${canonical(row.conservativeGains)}`; return p;
        }));
    }
    buttons(); scheduleExpiry();
}
async function action(work) {
    if (busy) return;
    busy = true; const token = epoch; $('error').hidden = true; buttons();
    try { await work(token); }
    catch (error) { $('error').textContent = say('Not accepted: ', 'Non accepté : ') + error.message; $('error').hidden = false; }
    finally { busy = false; show(); }
}
function download(record) {
    const url = URL.createObjectURL(new Blob([pretty(record) + '\n'], {type: 'application/json'}));
    const a = document.createElement('a'); a.href = url; a.download = 'specialist-evaluation-record.json'; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('contract').value = pretty(exampleContract());
$('contract').addEventListener('input', () => {
    epoch++; dirty = true;
    if (current) previous = current;
    $('notice').textContent = say('Draft changed. Previous evidence is historical; save the previous valid record if needed.', 'Brouillon modifié. Les preuves précédentes sont historiques ; enregistrez le dossier précédent si nécessaire.'); show();
});
$('freeze').addEventListener('click', () => action(async token => {
    const frozen = await freezeContract(parseBounded($('contract').value));
    const template = await reportTemplate(frozen), next = await exportRecord(frozen);
    const result = await assess(frozen);
    if (token !== epoch) throw Error('DRAFT_CHANGED');
    if (current) previous = current;
    current = next; assessment = result; dirty = false; $('report').value = pretty(template);
    $('notice').textContent = say('Exact contract frozen locally. No candidate or test ran; independent verification is uncommissioned.', 'Contrat exact figé localement. Aucun candidat ni test exécuté ; vérification indépendante non mandatée.');
}));
$('add').addEventListener('click', () => action(async token => {
    const report = await validateReport(parseBounded($('report').value), current.frozen);
    const next = await exportRecord(current.frozen, [...current.reports, report]);
    const result = await assess(next.frozen, next.reports);
    if (token !== epoch || dirty) throw Error('DRAFT_CHANGED');
    previous = current; current = next; assessment = result;
    $('notice').textContent = say('Report retained as supplied evidence. No independent trust or permission was created.', 'Rapport conservé comme preuve déclarée. Aucune confiance indépendante ni permission créée.');
}));
$('save').addEventListener('click', () => action(async token => {
    if (!current || dirty) return;
    await refresh();
    if (token !== epoch || dirty) throw Error('DRAFT_CHANGED');
    download(current);
}));
$('previous').addEventListener('click', () => { if (previous && !busy) download(previous); });
$('restore').addEventListener('change', () => {
    const file = $('restore').files[0]; if (!file) return;
    action(async token => {
        if (file.size > 2000000) throw Error('Import exceeds 2 MB');
        const bytes = new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer());
        const restored = await restoreRecord(bytes), template = await reportTemplate(restored.record.frozen);
        if (token !== epoch) throw Error('DRAFT_CHANGED');
        if (current) previous = current;
        current = restored.record; assessment = restored.assessment; dirty = false;
        $('contract').value = pretty(current.frozen.contract); $('report').value = pretty(template);
        $('notice').textContent = say('Historical reports reopened. No authority or reviewer trust restored.', 'Rapports historiques rouverts. Aucune autorité ni confiance du réviseur restaurée.');
    }).finally(() => { $('restore').value = ''; });
});
$('language').addEventListener('click', () => {
    lang = lang === 'en' ? 'fr' : 'en'; document.documentElement.lang = lang;
    document.querySelectorAll('[data-en]').forEach(node => { node.textContent = node.dataset[lang]; });
    $('language').textContent = lang === 'en' ? 'Français' : 'English'; show();
});
window.addEventListener('focus', () => { show(); refresh().catch(() => {}); });
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') { show(); refresh().catch(() => {}); }
});
show();
