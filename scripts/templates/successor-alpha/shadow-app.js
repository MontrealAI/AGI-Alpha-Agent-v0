// SPDX-License-Identifier: Apache-2.0
const shadowFields = {
    totalOperatingCostCents:'shadow-cost',priceAssumptionCents:'shadow-price',totalCollectedCents:'shadow-collected',
    reserveCents:'shadow-reserve',obligationCents:'shadow-obligation',capabilityCostCents:'shadow-construction',
    traditionalMinutes:'shadow-traditional-minutes',humanHourlyCents:'shadow-hourly',humanMinutes:'shadow-attention'
};
function shadowInputs() {
    const inputs = {currency:$('shadow-currency').value,acceptance:$('shadow-acceptance').value,
        operatingCostsComplete:$('shadow-cost-complete').checked,costBasis:'assumed',
        reinvestmentBps:Number($('shadow-reinvestment').value)*100};
    for (const [key,id] of Object.entries(shadowFields)) {
        const value = $(id).value.trim(), minutes = ['traditionalMinutes','humanMinutes'].includes(key);
        if (value && (!(minutes ? /^\d+$/ : /^\d+(?:\.\d{1,2})?$/).test(value) || Number(value) > 1000000)) {
            $(id).setAttribute('aria-invalid','true'); $(id).focus();
            throw Error(say('Enter nonnegative amounts with up to two decimals, and whole minutes, up to 1,000,000. Leave unknowns blank.',
                'Saisissez des montants non négatifs à deux décimales et des minutes entières, jusqu’à 1 000 000. Laissez les inconnues vides.'));
        }
        inputs[key] = value === '' ? null : Math.round(Number(value)*(minutes ? 1 : 100));
    }
    return inputs;
}
function fillShadow(inputs) {
    for (const [key,id] of Object.entries(shadowFields)) $(id).value = inputs?.[key] == null ? '' :
        String(inputs[key]/(['traditionalMinutes','humanMinutes'].includes(key) ? 1 : 100));
    $('shadow-currency').value = inputs?.currency || 'USD';
    $('shadow-acceptance').value = inputs?.acceptance || 'unknown';
    $('shadow-cost-complete').checked = inputs?.operatingCostsComplete || false;
    $('shadow-reinvestment').value = String((inputs?.reinvestmentBps || 0)/100);
}
function renderShadow() {
    const current = dossier?.cycles.at(-1);
    if (current?.id !== shadowFormCycleId) {
        shadowFormCycleId=current?.id;
        const retained=shadowArchive?.projectId === dossier?.id ?
            [...shadowArchive.entries].reverse().find(entry=>entry.cycleId===current?.id) : null;
        fillShadow(retained?.inputs);
    }
    $('shadow-calculate').disabled = !current;
    $('shadow-download').disabled = !shadowArchive?.entries.length;
    if (!shadowArchive || shadowArchive.projectId !== dossier?.id) {
        shadowCurrent = null; $('shadow-result').hidden = true; return;
    }
    const replayed = shadow.replayPlans(shadowArchive,dossier);
    const selected = replayed.missions.find(item => item.cycleId === current?.id);
    shadowCurrent = selected || null;
    $('shadow-result').replaceChildren(); $('shadow-result').hidden = !replayed.missions.length;
    if (!replayed.missions.length) return;
    node('p',$('shadow-result'),say(`${replayed.missions.length} planned mission(s); ${replayed.revisions} retained revision(s). Latest record per mission is counted once.`,
        `${replayed.missions.length} mission(s) planifiée(s) ; ${replayed.revisions} révision(s) conservée(s). Chaque mission est comptée une seule fois.`));
    if (!selected) {
        node('p',$('shadow-result'),say('Earlier planning records are retained. Enter fresh assumptions for this new cycle.',
            'Les fiches précédentes sont conservées. Saisissez de nouvelles hypothèses pour ce cycle.')); return;
    }
    const currency = selected.summary.currency;
    const money = value => value === null ? say('Unknown','Inconnu') :
        new Intl.NumberFormat(language === 'fr' ? 'fr-CA' : 'en-CA',{style:'currency',currency}).format(value/100);
    const rows = [
        [say('Traditional workflow · assumption','Travail traditionnel · hypothèse'),selected.comparison.traditionalCost],
        [say('Customer price + remaining attention','Prix client + attention restante'),selected.comparison.customerPricePlusAttention],
        [say('Customer savings · conditional','Économies du client · conditionnelles'),selected.comparison.customerSavings],
        [say('Collected revenue · self-reported','Recettes encaissées · votre déclaration'),selected.summary.observed.revenue],
        [say('Provider full cost · scenario','Coût complet du prestataire · scénario'),selected.summary.scenario.fullCost],
        [say('Operating margin · scenario','Marge d’exploitation · scénario'),selected.summary.scenario.operatingMargin],
        [say('Required reserves','Réserves nécessaires'),selected.summary.scenario.reserve],
        [say('Unpaid obligations','Obligations impayées'),selected.summary.scenario.unpaidObligations],
        [say('After reserves and obligations · scenario','Après réserves et obligations · scénario'),selected.summary.scenario.afterReserves],
        [say('Available surplus · scenario','Surplus disponible · scénario'),selected.summary.scenario.availableSurplus],
        [say('Potential capability investment · scenario','Investissement potentiel en capacités · scénario'),selected.summary.scenario.eligibleInvestment],
        [say('Available cash surplus · observed complete costs required','Surplus de trésorerie · coûts complets observés requis'),selected.summary.observed.availableSurplus]
    ];
    const dl=node('dl',$('shadow-result'));
    for (const [label,value] of rows) { node('dt',dl,label); node('dd',dl,money(value)); }
    const threshold=selected.comparison.breakEvenTraditionalMinutes;
    node('p',$('shadow-result'),threshold === null ? say('Human-work break-even is unknown. Enter a price, human attention and an hourly cost.',
        'Le seuil de rentabilité du travail humain est inconnu. Saisissez prix, attention humaine et coût horaire.') :
        say(`Conditional buyer break-even: ${threshold.toFixed(2)} traditional-work minutes.`,
            `Seuil conditionnel pour le client : ${threshold.toFixed(2)} minutes de travail traditionnel.`));
    node('p',$('shadow-result'),say('No capability gain or payment is established. The provider cost already includes declared human effort. Reinvestment uses only a scenario and grants no spending authority.',
        'Aucun gain de capacité ni paiement n’est établi. Le coût du prestataire comprend déjà l’effort humain déclaré. Le réinvestissement repose sur un scénario et n’accorde aucun pouvoir de dépense.'));
}
function serializeShadow() {
    return shadowArchive ? transport.canonical(shadow.inspectPlans(shadowArchive,dossier)) : 'null';
}
function restoreShadow() {
    const raw=$('saved-shadow-ledger').textContent.trim();
    if (raw && raw !== 'null') {
        shadowArchive=shadow.inspectPlans(raw,dossier);
        fillShadow(shadowArchive.entries.at(-1)?.inputs); renderShadow();
    }
}
function shadowError(error) {
    $('shadow-error').hidden=false;
    $('shadow-error').textContent=say('Planning record refused: ','Fiche de planification refusée : ')+error.message;
}
$('shadow-calculate').addEventListener('click',()=>{
    $('shadow-error').hidden=true;
    try {
        shadowArchive=shadow.recordPlan(shadowArchive || shadow.createPlans(dossier),dossier,shadowInputs());
        renderShadow();
    } catch(error) {shadowError(error);}
});
for (const element of $('shadow-panel').querySelectorAll('input:not([type=file]),select')) element.addEventListener('input',()=>{
    $('shadow-result').hidden=true; $('shadow-error').hidden=true;
    element.removeAttribute('aria-invalid');
});
$('shadow-download').addEventListener('click',()=>{
    try {download('successor-planning-ledger.json',serializeShadow(),'application/json');} catch(error){shadowError(error);}
});
$('shadow-import').addEventListener('click',()=>$('shadow-file').click());
$('shadow-file').addEventListener('change',async()=>{
    const file=$('shadow-file').files[0]; if(!file)return;
    const version=++shadowImportVersion, projectId=dossier?.id, cycleId=dossier?.cycles.at(-1)?.id;
    try {
        if(file.size>200000)throw Error('Planning history exceeds 200 KB.');
        const raw=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
        if(version!==shadowImportVersion || dossier?.id!==projectId || dossier?.cycles.at(-1)?.id!==cycleId)throw Error('Project changed during import.');
        const incoming=shadow.inspectPlans(raw,dossier);
        if(shadowArchive && shadowArchive.entries.some((entry,i)=>transport.canonical(entry)!==transport.canonical(incoming.entries[i])))
            throw Error('Import would replace or remove retained planning history.');
        shadowArchive=incoming; fillShadow(incoming.entries.at(-1)?.inputs); renderShadow();
    } catch(error){shadowError(error);} finally{$('shadow-file').value='';}
});
