// SPDX-License-Identifier: Apache-2.0
let automationRecord = null, automationSummary = null, automationImportVersion = 0;
Object.assign(fr,{
    automationTitle:'Coût de la livraison automatisée',automationInspect:'Examiner ou modifier les hypothèses partagées',
    automationIntro:'Distinguez le coût marginal du prochain travail, le coût récurrent au volume prévu et le coût complet avec les investissements amortis. Chaque étape conserve sa provenance et ses inconnues.',
    automationBoundary:'Les appels de modèles ne représentent qu’un composant. Un scénario remplace le travail humain par des opérations logicielles chiffrées ; il ne prouve ni l’exécution authentifiée ni l’acceptation du client.',
    automationInputs:'Registre partagé des tâches et des coûts · JSON',
    automationInputHelp:'Huit étapes : préparation, planification, exécution, vérification, correction, conditionnement, rapport et récupération. Chaque fait est mesuré, sourcé, estimé ou inconnu. Les montants sont en millionièmes de devise ; les fréquences sont explicites.',
    automationExample:'Charger un exemple explicitement estimé',automationUnknown:'Repartir avec les coûts inconnus',
    automationCalculate:'Calculer les trois niveaux de coût',automationOpen:'Importer un registre partagé',
    automationDownload:'Télécharger le registre partagé des tâches et des coûts',automationScenario:'Scénario à reprendre dans la fiche de mission',
    automationApply:'Reprendre le coût récurrent provisoire',
    automationApplyHelp:'Seule l’allocation récurrente des ressources est reprise. Excluez le coût d’opportunité du client avant de calculer la trésorerie de l’entreprise. Les décaissements de mise en place et de développement restent inconnus dans la fiche de mission. Renseignez investissements réels, réserves et obligations avant de calculer un surplus. Un amortissement économique n’est pas de la trésorerie disponible.',
    automationScenarioBase:'Base',automationScenarioConservative:'Prudent',automationScenarioStress:'Tension',
    automationLimit:'Les trois scénarios sont des hypothèses comparatives, jamais des montants à additionner. Les pertes et les faibles volumes restent visibles. Le réinvestissement demeure une planification sans transaction.',
});
function parseAutomation(raw) {
    if(typeof raw!=='string' || new TextEncoder().encode(raw).length>200000)throw Error('Automated cost records are limited to 200 KB.');
    return automatedCosts.inspectAutomatedCosts(JSON.parse(transport.canonical(transport.parseBounded(raw))));
}
function automationMoney(value) {
    return value===null ? say('Unknown','Inconnu') : new Intl.NumberFormat(language==='fr'?'fr-CA':'en-CA',
        {style:'currency',currency:automationSummary.currency,minimumFractionDigits:2,maximumFractionDigits:6}).format(value/1000000);
}
function renderAutomatedCosts() {
    $('automation-result').replaceChildren(); $('automation-result').hidden=!automationSummary;
    $('automation-download').disabled=!automationSummary;
    const selected=automationSummary?.scenarios.find(row=>row.name===$('automation-scenario').value);
    $('automation-apply').disabled=!dossier?.cycles.length || selected?.costs.recurringMicrosPerAccepted==null;
    if(!automationSummary)return;
    node('p',$('automation-result'),say('Conditional cost per accepted deliverable. Every failed attempt and entered exception is included.',
        'Coût conditionnel par livraison acceptée. Chaque tentative infructueuse et exception saisie est incluse.'));
    const wrap=node('div',$('automation-result'),undefined,'table-scroll'),table=node('table',wrap);
    const head=node('tr',node('thead',table));
    for(const title of [say('Scenario','Scénario'),say('Marginal','Marginal'),say('Recurring','Récurrent'),
        say('Fully loaded','Complet'),say('Traditional work','Travail traditionnel'),say('Accepted/month','Acceptés/mois'),say('Fully loaded comparison','Comparaison du coût complet')]){
        const th=node('th',head,title);th.scope='col';
    }
    const body=node('tbody',table);
    for(const row of automationSummary.scenarios){
        const tr=node('tr',body);
        for(const value of [say(row.name,{base:'base',conservative:'prudent',stress:'tension'}[row.name]),
            automationMoney(row.costs.marginalMicrosPerAccepted),automationMoney(row.costs.recurringMicrosPerAccepted),
            automationMoney(row.costs.fullyLoadedMicrosPerAccepted),automationMoney(row.humanBaselineMicrosPerAccepted),
            row.volume.acceptedPerMonth===null?say('Unknown','Inconnu'):number(row.volume.acceptedPerMonth),
            say({win:'Wins',tie:'Break-even',loss:'Loses',unknown:'Unknown'}[row.comparison.fullyLoaded.outcome],
                {win:'Gain',tie:'Équilibre',loss:'Perte',unknown:'Inconnu'}[row.comparison.fullyLoaded.outcome])])node('td',tr,String(value));
        const detail=node('p',$('automation-result'));
        const threshold=row.comparison.fullyLoaded.breakEvenHumanMinutes;
        detail.textContent=say(`${row.name}: ${row.unknownInputs.length} unknown input(s); expected residual human exceptions ${row.residualHumanMinutesPerRequest===null?'unknown':row.residualHumanMinutesPerRequest} min/request. Fully loaded human-work break-even: ${threshold===null?'unknown':threshold.toFixed(3)+' min'}.`,
            `${({base:'Base',conservative:'Prudent',stress:'Tension'})[row.name]} : ${row.unknownInputs.length} donnée(s) inconnue(s) ; exceptions humaines résiduelles prévues ${row.residualHumanMinutesPerRequest===null?'inconnues':row.residualHumanMinutesPerRequest} min/demande. Seuil de rentabilité complet du travail humain : ${threshold===null?'inconnu':threshold.toFixed(3)+' min'}.`);
    }
    node('p',$('automation-result'),say('Task duration and equivalent acceptance remain assumptions unless supported by task evidence. A sourced wage alone does not establish time saved.',
        'La durée et l’acceptation équivalente restent des hypothèses sans preuves sur la tâche. Un coût horaire sourcé ne démontre pas le temps gagné.'));
}
function useAutomation(record) {
    const checked=automatedCosts.inspectAutomatedCosts(record);
    automationImportVersion++;
    automationSummary=automatedCosts.evaluateAutomatedCosts(checked);automationRecord=checked;
    $('automation-record').value=JSON.stringify(checked,null,2);$('automation-error').hidden=true;renderAutomatedCosts();
}
function automationError(error) {
    $('automation-error').textContent=say('Cost record refused: ','Registre de coûts refusé : ')+error.message;
    $('automation-error').hidden=false;
}
function serializeAutomatedCosts() {
    return automationRecord && dossier ? JSON.stringify({schema:'successor-alpha-automated-costs/v1',
        projectId:dossier.id,record:automatedCosts.inspectAutomatedCosts(automationRecord)}) : 'null';
}
function restoreAutomatedCosts() {
    const raw=$('saved-automated-costs').textContent.trim();
    if(!raw || raw==='null')return;
    const value=JSON.parse(transport.canonical(transport.parseBounded(raw)));
    if(!value || Object.keys(value).sort().join()!=='projectId,record,schema' ||
        value.schema!=='successor-alpha-automated-costs/v1' || value.projectId!==dossier?.id)
        throw Error('Automated cost plan does not match this project.');
    useAutomation(value.record);
}
$('automation-record').value=JSON.stringify(AUTOMATED_COST_UNKNOWN,null,2);
$('automation-record').addEventListener('input',()=>{
    automationImportVersion++;
    automationRecord=null;automationSummary=null;$('automation-error').hidden=true;renderAutomatedCosts();
});
$('automation-calculate').addEventListener('click',()=>{automationImportVersion++;try{useAutomation(parseAutomation($('automation-record').value));}catch(error){automationError(error);}});
$('automation-example').addEventListener('click',()=>{try{useAutomation(AUTOMATED_COST_EXAMPLE);}catch(error){automationError(error);}});
$('automation-unknown').addEventListener('click',()=>{try{useAutomation(AUTOMATED_COST_UNKNOWN);}catch(error){automationError(error);}});
$('automation-scenario').addEventListener('change',renderAutomatedCosts);
$('automation-download').addEventListener('click',()=>{
    if(automationRecord)download('automated-task-cost-record.json',JSON.stringify(automationRecord,null,2),'application/json');
});
$('automation-open').addEventListener('click',()=>$('automation-file').click());
$('automation-file').addEventListener('change',async()=>{
    const file=$('automation-file').files[0];if(!file)return;const expected=++automationImportVersion;
    try{
        if(file.size>200000)throw Error('Automated cost records are limited to 200 KB.');
        const raw=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
        if(expected!==automationImportVersion)throw Error('Cost record changed during import.');
        useAutomation(parseAutomation(raw));
    }catch(error){automationError(error);}finally{$('automation-file').value='';}
});
$('automation-apply').addEventListener('click',()=>{
    automationImportVersion++;
    try{
        const record=parseAutomation($('automation-record').value),summary=automatedCosts.evaluateAutomatedCosts(record);
        const scenario=summary.scenarios.find(row=>row.name===$('automation-scenario').value);
        const micros=scenario?.costs.recurringMicrosPerAccepted;
        if(!dossier?.cycles.length || micros==null)throw Error('Complete a mission and resolve the cost inputs before applying a modeled allocation.');
        if(micros>1000000000000)throw Error('Modeled amount exceeds the supported mission input range.');
        if($('shadow-currency').value!==record.currency)throw Error(say(
            'The cost record currency differs from the mission currency. Use a matching cost record; no amounts were copied or converted.',
            'La devise du registre de coûts diffère de celle de la mission. Utilisez un registre dans la même devise ; aucun montant n’a été copié ni converti.'));
        $('automation-error').hidden=true;
        $('shadow-cost').value=String(Math.ceil(micros/10000)/100);
        $('shadow-cost-complete').checked=false;$('shadow-construction').value='';
        $('shadow-result').hidden=true;$('shadow-panel').open=true;
        $('shadow-cost').focus();
        status('Modeled recurring allocation copied. Investment cash costs remain unknown. Complete period costs, reserves, buyer attention and acceptance before calculating any surplus.',
            'Allocation récurrente modélisée copiée. Les investissements décaissés restent inconnus. Complétez coûts de période, réserves, attention du client et acceptation avant tout calcul de surplus.');
    }catch(error){automationError(error);}
});
