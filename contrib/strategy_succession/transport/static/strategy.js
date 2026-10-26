// SPDX-License-Identifier: Apache-2.0
'use strict';
const $=id=>document.getElementById(id);
const INITIAL={schema:'release-plan/v1',id:'public-release-plan',kind:'plan',public_or_synthetic:'synthetic',planning_only:true,jobs:[{id:'J1',duration:2,crew:1,deps:[]},{id:'J2',duration:4,crew:2,deps:['J1']},{id:'J3',duration:3,crew:1,deps:['J1']},{id:'J4',duration:3,crew:2,deps:['J2']},{id:'J5',duration:2,crew:1,deps:['J3']},{id:'J6',duration:1,crew:1,deps:['J4','J5']}],capacity:Array(32).fill(2),deadline:24};
const SAMPLE={initial:INITIAL,changes:{durations:{J2:6},deadline:28},repair:{observed_at:9,capacity:Array.from({length:32},(_,i)=>i>=12&&i<15?1:2),deadline:28},construction:{enabled:true}};
$('input').value=JSON.stringify(SAMPLE,null,2);
let token='',connected=false,currentPlan=null,latestStatus=null,running=false,polling=null,language=new URLSearchParams(location.search).get('lang')==='fr'?'fr':'en';
const words={en:{start:'Start',connect:'Connect',disconnect:'Disconnect',review:'Review',pause:'Pause',resume:'Resume',stop:'Stop',keep:'Keep',improve:'Improve',export:'Export',approve:'Approve and start work',resumeApproved:'Resume approved work'},fr:{start:'Démarrer',connect:'Connecter',disconnect:'Déconnecter',review:'Vérifier',pause:'Pause',resume:'Reprendre',stop:'Arrêter',keep:'Conserver',improve:'Améliorer',export:'Exporter',approve:'Autoriser et démarrer',resumeApproved:'Reprendre le travail autorisé'}};
const say=(en,fr)=>language==='fr'?fr:en;
const word=key=>words[language][key];
const stateName=state=>({prepared:say('Prepared','Préparée'),approved:say('Approved','Autorisée'),running:say('Running','En cours'),completed:say('Finished','Terminée'),rejected:say('Rejected','Refusée'),unknown:say('Awaiting evidence','En attente de preuves'),reconciled:say('Reconciled; outcome unknown','Rapproché ; résultat inconnu'),ready:say('Ready','Prêt'),paused:say('Paused','En pause'),stopped:say('Stopped','Arrêté'),disconnected:say('Disconnected','Déconnecté')}[state]??String(state));
const methodName=method=>({'run-journey':say('Plan → adapt → repair','Planifier → adapter → réparer'),'run-mission':say('Planning mission','Mission de planification'),construct:say('Method construction','Construction de méthode'),'ordinary-portfolio':say('Existing specialist portfolio','Portefeuille de spécialistes existant'),'retained-qualified-trial':say('Retained method trial','Essai de méthode conservée'),'native-repair':say('Native repair specialist','Spécialiste natif de réparation'),'native-deadline':say('Native deadline specialist','Spécialiste natif d’échéance'),'native-makespan':say('Native makespan specialist','Spécialiste natif de durée')}[method]??String(method??say('See evidence','Voir les preuves')));
const phaseName=index=>[say('Initial plan','Plan initial'),say('Changed requirements','Exigences modifiées'),say('Repair the same project','Réparer le même projet')][index]??say('Result','Résultat');
const number=x=>typeof x==='number'?new Intl.NumberFormat(language,{maximumFractionDigits:3}).format(x):say('Unknown','Inconnu');
const message=(text,error=false)=>{if(error){$('error').textContent=text;$('error').hidden=false;}else{lastFailure=null;$('status').textContent=text;$('error').hidden=true;}};
async function api(action,body){
 if(!token)throw Error('ACCESS_REQUIRED');
 const response=await fetch('/api/strategy-executor/'+action,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)}),cache:'no-store'});
 const result=await response.json();if(!response.ok)throw Error(result.error||'Executor request refused. Inspect retained status before retrying.');return result;
}
function controls(){
 $('prepare').disabled=!connected||running||latestStatus?.state!=='ready'||!latestStatus?.source_available;
 $('connect').disabled=connected;$('disconnect').disabled=!connected;
 $('review').disabled=!connected;$('pause').disabled=!connected||latestStatus?.state==='stopped';$('stop').disabled=!connected||latestStatus?.state==='stopped';
 const reviewable=['prepared','approved'].includes(currentPlan?.state);
 $('approve').disabled=!connected||running||!latestStatus?.source_available||latestStatus?.state!=='ready'||!reviewable||!$('consent').checked;
 $('consent').disabled=running||!reviewable;
 $('mission-select').disabled=!connected||running||!Object.keys(latestStatus?.plans??{}).length;
 $('export').disabled=!connected||!currentPlan;$('report').disabled=!currentPlan?.outcome;
 $('keep').disabled=running||!currentPlan?.outcome?.result?.capabilities;
 $('improve').disabled=!connected||running||!currentPlan?.outcome?.result?.next_improvement;
 $('report').textContent=say('Download report','Télécharger le rapport');for(const id of ['connect','disconnect','review','stop','keep','improve','export'])$(id).textContent=word(id);$('approve').textContent=word(currentPlan?.state==='approved'?'resumeApproved':'approve');$('prepare').textContent=word('start');$('pause').textContent=word(latestStatus?.state==='paused'?'resume':'pause');
}
function balances(status){
 const titles={service_work:say('Service work','Travail de service'),improvement_work:say('Improvement work','Travail d’amélioration'),native_calls:say('Native specialist calls','Appels au spécialiste natif'),native_solve_seconds:say('Native solve allowance','Allocation du solveur natif')};
 const box=$('balances');box.replaceChildren();
 for(const [key,title]of Object.entries(titles)){const el=document.createElement('div');el.className='balance';const name=document.createElement('span');name.textContent=title;const value=document.createElement('strong');value.textContent=number(status.spent?.[key])+' / '+number(status.total?.[key]);const reserved=document.createElement('small');reserved.textContent=number(status.reserved?.[key])+say(' reserved · ',' réservés · ')+number(currentPlan?.observed?.[key]??0)+say(' observed',' observés');el.append(name,value,reserved);box.append(el);}
}
function showPlan(plan,{resetConsent=true}={}){
 currentPlan=plan;$('plan').hidden=false;if(resetConsent)$('consent').checked=false;
 const pairs={
  [say('Executor','Exécuteur')]:plan.executor_id,[say('Source identity','Identité du code')]:plan.source_hash,
  [say('Method','Méthode')]:methodName(plan.method),[say('Mission state','État de la mission')]:stateName(plan.state),
  [say('Service work cap','Plafond du travail de service')]:number(plan.caps?.service_work),
  [say('Improvement work cap','Plafond du travail d’amélioration')]:number(plan.caps?.improvement_work),
  [say('Native specialist ceiling','Plafond du spécialiste natif')]:number(plan.caps?.native_calls)+say(' calls · ',' appels · ')+number(plan.caps?.native_solve_seconds)+say(' solve-allowance seconds',' secondes allouées au solveur'),
  [say('Expires','Expiration')]:new Date(plan.expires_at*1000).toLocaleString(language),
  [say('Maximum request time','Durée maximale de la demande')]:number(plan.request_seconds)+say(' seconds',' secondes'),
  [say('Approval digest','Empreinte d’autorisation')]:plan.plan_digest};
 const dl=$('scope');dl.replaceChildren();for(const [key,value]of Object.entries(pairs)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=value;dl.append(dt,dd);}
 $('approved-input').textContent=JSON.stringify(plan.input,null,2);controls();
}
function retainedMissions(status){
 const plans=Object.values(status.plans??{}).sort((a,b)=>(b.prepared_at??0)-(a.prepared_at??0)||b.plan_id.localeCompare(a.plan_id));
 const select=$('mission-select');
 const labels=plans.map(plan=>[plan.plan_id,(plan.input?.initial?.id??plan.input?.task?.id??plan.request_id??plan.plan_id)+' · '+methodName(plan.method)+' · '+stateName(plan.state)]);
 const signature=JSON.stringify(labels);
 if(select.dataset.missions!==signature){select.replaceChildren();for(const[value,label]of labels){const option=document.createElement('option');option.value=value;option.textContent=label;select.append(option);}if(!plans.length){const option=document.createElement('option');option.value='';option.textContent=language==='fr'?'Aucune mission conservée':'No retained missions';select.append(option);}select.dataset.missions=signature;}
 const selected=currentPlan&&status.plans?.[currentPlan.plan_id]||plans[0];
 if(selected){const changed=currentPlan?.plan_id!==selected.plan_id;showPlan(selected,{resetConsent:changed});select.value=selected.plan_id;renderOutcome(selected);}
 else{currentPlan=null;$('plan').hidden=true;$('consent').checked=false;clearOutcome();}
}
function clearOutcome(){
 $('results').replaceChildren();$('evidence').hidden=true;$('raw').textContent='';
 $('method-note').textContent=say('Retained methods require fresh checks before later use. Keep saves inspectable method records.','Les méthodes conservées exigent de nouvelles vérifications avant réutilisation. Conserver télécharge des dossiers à examiner.');
}

const stageName=stage=>({dispatch:say('Dispatch strategy','Stratégie d’ordonnancement'),lookahead:say('Look-ahead strategy','Stratégie d’anticipation'),repair:say('Repair strategy','Stratégie de réparation')}[stage]??String(stage??say('Method','Méthode')));
function admissionName(decision){
 if(decision==='HOLD_FULL_COST_UNKNOWN')return say('Hold — full cost is unknown','En attente — coût complet inconnu');
 if(typeof decision==='string'&&decision.startsWith('HOLD'))return say('Hold — inspect the admission evidence','En attente — vérifier les preuves d’admission');
 if(typeof decision==='string'&&decision.startsWith('DEFER'))return say('Deferred — inspect the evidence','Différé — examiner les preuves')+' ('+decision+')';
 if(typeof decision==='string'&&decision.startsWith('REJECT'))return say('Rejected — inspect the evidence','Refusé — examiner les preuves')+' ('+decision+')';
 return typeof decision==='string'?decision.replaceAll('_',' ').toLowerCase():say('Not established','Non établi');
}
function paragraph(parent,text,className=''){const p=document.createElement('p');p.textContent=text;if(className)p.className=className;parent.append(p);}
function summaryTable(parent,headers,rows){
 const table=document.createElement('table');table.className='schedule summary-table';const thead=document.createElement('thead'),head=document.createElement('tr');
 for(const label of headers){const th=document.createElement('th');th.scope='col';th.textContent=label;head.append(th);}thead.append(head);table.append(thead);const body=document.createElement('tbody');
 for(const values of rows){const row=document.createElement('tr');for(const value of values){const td=document.createElement('td');td.textContent=String(value);row.append(td);}body.append(row);}table.append(body);parent.append(table);
}
function resultSummary(key,value,section){
 if(key==='capabilities'){
  const methods=Array.isArray(value)?value:[];const promoted=methods.filter(item=>item.asset?.active===true&&item.gate?.accepted===true).length;
  paragraph(section,say(number(methods.length)+' candidate methods retained for inspection; '+number(promoted)+' admitted for active use.',number(methods.length)+' méthodes candidates conservées pour inspection ; '+number(promoted)+' admises à une utilisation active.'));
  for(const item of methods){const gate=item.gate??item.asset?.admission??{};const checked=item.qualification?.correctness===true||gate.correctness===true;paragraph(section,stageName(item.stage??item.asset?.stage)+' · '+(checked?say('Correctness checks passed','Vérifications de justesse réussies'):say('Checks require review','Vérifications à examiner'))+' · '+number(item.construction_work)+say(' construction work units · ',' unités de construction · ')+admissionName(item.decision??gate.decision)+'.');}
  paragraph(section,say('Inspection records carry no production authority. Human and monetary costs remain unknown.','Ces dossiers d’inspection ne confèrent aucune autorité de production. Les coûts humains et monétaires restent inconnus.'),'meta');
 }else if(key==='inheritance'){
  const comparisons=Array.isArray(value?.diagnostics)?value.diagnostics:[];
  if(!comparisons.length)paragraph(section,say('No matched inheritance comparison is available for this run.','Aucune comparaison appariée de réutilisation n’est disponible pour cette exécution.'));
  for(const comparison of comparisons){
   const heading=document.createElement('h4');heading.textContent=stageName(comparison.stage);section.append(heading);const arms=Array.isArray(comparison.arms)?comparison.arms:[];
   const equalCaps=arms.length>0&&arms.every(arm=>arm.total_allocation===arms[0].total_allocation&&arm.child_allocation===arms[0].child_allocation&&arm.reconstruction_allocation===arms[0].reconstruction_allocation);
   paragraph(section,(equalCaps?say('Equal total allowance: ','Même allocation totale : ')+number(arms[0].total_allocation)+say(' counted units per method. ',' unités comptées par méthode. '):say('Allowances differ or are incomplete; inspect the evidence. ','Les allocations diffèrent ou sont incomplètes ; vérifier les preuves. '))+(comparison.equal_fresh_outputs===true?say('Fresh outputs match.','Les nouveaux résultats concordent.'):say('Fresh outputs differ or their equality is unestablished.','Les nouveaux résultats diffèrent ou leur égalité n’est pas établie.')));
   const treatmentNames={inherited:say('Inherited parent','Parent réutilisé'),rebuilt:say('Rebuilt parent','Parent reconstruit'),equivalent:say('Equivalent reuse','Réutilisation équivalente')};
   summaryTable(section,[say('Method','Méthode'),say('Counted work','Travail compté'),say('Build allowance','Budget de construction'),say('Checks','Vérifications')],arms.map(arm=>{const q=arm.child?.qualification?.candidate;return[treatmentNames[arm.treatment]??String(arm.treatment??say('Unknown','Inconnu')),number(arm.total_work),number(arm.child_allocation),q&&typeof q.qualified==='number'&&typeof q.count==='number'?number(q.qualified)+'/'+number(q.count)+say(' qualified',' qualifiés'):say('See evidence','Voir les preuves')];}));
  }
  paragraph(section,say('These local construction comparisons include ordinary reuse. Counted work is not money, and lower counts do not establish economic promotion or self-acceleration.','Ces comparaisons locales incluent la réutilisation ordinaire. Le travail compté n’est pas de l’argent ; un compte plus faible n’établit ni admission économique ni autoaccélération.'),'meta');
 }else{
  const candidate=value?.candidate_trial,specialist=value?.best_current_specialist;
  const consequence=value?.consequence==='TIE'?say('The repair candidate tied the strongest current specialist on this task.','La méthode candidate de réparation égale le meilleur spécialiste actuel pour cette tâche.'):say('Repair comparison: ','Comparaison de réparation : ')+consequenceName(value?.consequence)+'.';paragraph(section,consequence);
  summaryTable(section,[say('Method','Méthode'),say('Makespan / movement','Durée / déplacement'),say('Counted work','Travail compté'),say('Checks','Vérifications')],[[say('Repair candidate','Méthode candidate'),candidate],[say('Strongest specialist','Meilleur spécialiste'),specialist]].map(([name,trial])=>[name,number(trial?.result?.makespan)+' / '+number(trial?.result?.movement),number(trial?.work),trial?.valid===true&&trial?.qualified===true?say('Qualified','Qualifié'):say('Review required','À vérifier')]));
  const selectedName=methodName(value?.selected_method);
  paragraph(section,say('Selected method: ','Méthode sélectionnée : ')+selectedName+' · '+admissionName(value?.economic_decision)+'. '+(value?.production_promotion===true?say('Any production authority still requires separate authorization.','Toute autorité de production exige une autorisation distincte.'):say('No production promotion.','Aucune admission en production.')));
 }
 paragraph(section,say('The complete records remain in the source-bound evidence below.','Les dossiers complets restent disponibles dans les preuves liées à la source ci-dessous.'),'meta');
}
function renderOutcome(plan){
 const outcome=plan.outcome;
 if(!outcome){
  clearOutcome();
  if(plan.partial_receipts?.length){$('results').replaceChildren();for(const receipt of plan.partial_receipts){const card=document.createElement('section');card.className='result';const h=document.createElement('h3');h.textContent=phaseName(receipt.phase_index)+say(' retained',' conservé');const text=document.createElement('p');text.textContent=say('A checked phase is committed to the executor journal. Mission state: ','Une étape vérifiée est conservée dans le journal de l’exécuteur. État de la mission : ')+stateName(plan.state)+say('. Receipt: ','. Reçu : ')+receipt.receipt_hash;card.append(h,text);$('results').append(card);}$('evidence').hidden=false;$('raw').textContent=JSON.stringify(plan,null,2);}
  return;
 }
 const result=outcome.result??{},target=$('results');target.replaceChildren();
 for(const [index,phase]of (result.phases??[]).entries()){
  const section=document.createElement('section');section.className='result';const h=document.createElement('h3');h.textContent=phaseName(index);
  const detail=document.createElement('p');const schedule=phase.result??phase.delivery?.result??{};detail.textContent=(phase.qualified?say('Qualified','Qualifié'):say('Review required','À vérifier'))+say(' · Makespan ',' · Durée ')+number(schedule.makespan)+say(' · Movement ',' · Déplacement ')+number(schedule.movement)+' · '+methodName(phase.selected_method);section.append(h,detail);
  if(Array.isArray(schedule.schedule)){const table=document.createElement('table');table.className='schedule';const tr=document.createElement('tr');for(const label of [say('Job','Tâche'),say('Start','Début'),say('Finish','Fin')]){const th=document.createElement('th');th.scope='col';th.textContent=label;tr.append(th);}const head=document.createElement('thead');head.append(tr);table.append(head);const body=document.createElement('tbody');for(const item of schedule.schedule){const row=document.createElement('tr');for(const value of [item.id,item.start,item.end]){const td=document.createElement('td');td.textContent=String(value);row.append(td);}body.append(row);}table.append(body);section.append(table);}
  if(phase.baseline_source){const p=document.createElement('p');const baseline=phase.baseline_source;p.textContent=typeof baseline==='string'?say('Repair baseline: ','Référence de réparation : ')+baseline:say('Repair baseline: prior verified plan ','Référence de réparation : plan antérieur vérifié ')+String(baseline.receipt_hash??'').slice(0,16)+say(' · Commitments inferred from the supplied planning time ',' · Engagements déduits de l’instant de planification fourni ')+String(baseline.observed_at??'')+say('. Physical job execution is not observed by this planner.','. Ce planificateur n’observe pas le travail physique.');section.append(p);}target.append(section);
 }
 for(const [key,title]of [['capabilities',say('What was retained','Ce qui a été conservé')],['inheritance',say('Did inheriting the parent help?','La réutilisation du parent a-t-elle aidé ?')],['repair_usefulness',say('Was the repair tool useful?','La méthode de réparation a-t-elle été utile ?')]]){if(result[key]===undefined)continue;const section=document.createElement('section');section.className='result';const h=document.createElement('h3');h.textContent=title;section.append(h);resultSummary(key,result[key],section);target.append(section);}
 $('evidence').hidden=false;$('raw').textContent=JSON.stringify(plan,null,2);
 $('method-note').textContent=result.next_improvement?say('A bounded next improvement is available for separate review and approval.','Une amélioration limitée est disponible pour examen et autorisation distincts.'):say('No further improvement proposal is admitted by this run. Retaining a competent incumbent is valid. Keep saves candidate records for inspection, with no authority.','Aucune proposition supplémentaire n’est admise par cette exécution. Conserver un spécialiste compétent est valable. Conserver télécharge des dossiers candidats sans autorité.');
}
function download(name,record){const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function refresh(){
 if(!connected)return;const status=await api('status');if(!connected)return;latestStatus=status;retainedMissions(status);balances(status);
 $('executor').textContent=say('Executor ','Exécuteur ')+status.executor_id+say(' · Source ',' · Code ')+status.source_hash+say(' · One request at a time',' · Une demande à la fois');
 $('connection').textContent=status.source_available?say('Connected','Connecté'):say('Source unavailable','Code indisponible');$('connection').classList.toggle('online',status.source_available);
 $('background').textContent=status.active_after_browser_close===true?say('A bounded request is active on the executor. Closing this tab does not cancel it. Use Pause or Stop.','Une demande limitée est active sur l’exécuteur. Fermer cet onglet ne l’annule pas. Utilisez Pause ou Arrêter.'):status.active_after_browser_close===false&&status.execution_observation!=='awaiting-evidence'?say('The executor reports no active request. Prepared plans require explicit approval.','L’exécuteur ne signale aucune demande active. Les plans préparés exigent une autorisation explicite.'):say('Executor cannot confirm whether earlier work finished. Inspect retained evidence; do not retry uncertain work.','L’exécuteur ne peut pas confirmer si le travail précédent est terminé. Vérifiez les preuves conservées ; ne relancez pas un travail incertain.');
 if(!running&&!lastFailure)message(currentPlan?say('Mission state: ','État de la mission : ')+stateName(currentPlan.state)+'.':say('Executor ','Exécuteur ')+stateName(status.state)+say('. Review its scope before starting.','. Vérifiez sa portée avant de démarrer.'));controls();return status;
}
$('connect-form').addEventListener('submit',async event=>{event.preventDefault();token=$('token').value;$('token').value='';$('consent').checked=false;try{await api('status');connected=true;await refresh();polling=setInterval(()=>refresh().catch(error=>{latestStatus={...latestStatus,state:'disconnected',source_available:false};$('connection').textContent=say('Status unavailable','État indisponible');$('connection').classList.remove('online');failure(error);controls();}),1200);}catch(error){token='';connected=false;failure(error);controls();}});
$('disconnect').addEventListener('click',()=>{token='';connected=false;$('consent').checked=false;clearInterval(polling);$('connection').textContent=say('Disconnected','Déconnecté');$('connection').classList.remove('online');message(say("Disconnected. An already approved bounded request may still be active on the executor.","Déconnecté. Une demande limitée déjà autorisée peut rester active sur l’exécuteur."));controls();});
$('prepare').addEventListener('click',async()=>{try{const input=preflightInput();const plan=await api('prepare',{method:'run-journey',input,request_id:crypto.randomUUID()});showPlan(plan);message(say("Plan prepared. Review both accounts, source and expiry, then approve this exact scope.","Plan préparé. Vérifiez les deux comptes, le code et l’expiration, puis autorisez cette portée exacte."));await refresh();}catch(error){failure(error);}});
$('consent').addEventListener('change',controls);
$('mission-select').addEventListener('change',()=>{const selected=latestStatus?.plans?.[$('mission-select').value];if(!selected||running)return;showPlan(selected);renderOutcome(selected);balances(latestStatus);message(say('Mission state: ','État de la mission : ')+stateName(selected.state)+say('. Running or uncertain work is never retried automatically.','. Le travail en cours ou incertain n’est jamais relancé automatiquement.'));});
$('approve').addEventListener('click',async()=>{if(!currentPlan||!$('consent').checked||!['prepared','approved'].includes(currentPlan.state))return;const binding={plan_id:currentPlan.plan_id,plan_digest:currentPlan.plan_digest};const needsApproval=currentPlan.state==='prepared';running=true;controls();try{if(needsApproval)currentPlan=await api('approve',binding);message(say('Running on ','Exécution sur ')+currentPlan.executor_id+say('. The executor is planning, adapting and repairing this project.','. L’exécuteur planifie, adapte et répare ce projet.'));currentPlan=await api('run',binding);renderOutcome(currentPlan);message(say('Mission ','Mission ')+stateName(currentPlan.state)+say('. Review the result, retained methods and both cost accounts.','. Examinez le résultat, les méthodes conservées et les deux comptes de coûts.'));}catch(error){failure(error);}finally{running=false;$('consent').checked=false;try{await refresh();}catch(error){failure(error);}controls();}});
$('review').addEventListener('click',()=>refresh().catch(error=>failure(error)));
$('pause').addEventListener('click',async()=>{try{await api('control',{state:latestStatus?.state==='paused'?'ready':'paused'});await refresh();}catch(error){failure(error);}});
$('stop').addEventListener('click',async()=>{try{await api('control',{state:'stopped'});await refresh();message(say("Stopped. This installed operating envelope cannot resume. Review and export retained evidence.","Arrêté. Cette enveloppe installée ne peut pas reprendre. Examinez et exportez les preuves conservées."));}catch(error){failure(error);}});
$('keep').addEventListener('click',()=>{const result=currentPlan?.outcome?.result;if(!result?.capabilities)return;download('strategy-methods-'+currentPlan.plan_id+'.json',{schema:'strategy-method-inspection/v1',source_hash:currentPlan.source_hash,origin_plan:currentPlan.plan_digest,origin_outcome:currentPlan.outcome_hash,capabilities:result.capabilities,proof:[],authority:[],limits:'Inspection records only. Fresh correctness, applicability and economic admission are required before reuse.'});message(say("Method records saved for inspection. No authority or proof was inherited.","Dossiers de méthode téléchargés pour examen. Aucune autorité ni preuve héritée."));});
$('improve').addEventListener('click',async()=>{const proposal=currentPlan?.outcome?.result?.next_improvement;if(!proposal)return;try{showPlan(await api('prepare',{method:'construct',input:proposal,request_id:crypto.randomUUID()}));message(say("Review the separately budgeted improvement before approving.","Vérifiez l’amélioration au budget distinct avant de l’autoriser."));await refresh();}catch(error){failure(error);}});
$('export').addEventListener('click',async()=>{try{download('strategy-mission-'+currentPlan.plan_id+'.json',await api('export/'+currentPlan.plan_id));}catch(error){failure(error);}});
controls();

function consequenceName(value){
 return {WIN:say('candidate win','victoire du candidat'),LOSS:say('candidate loss','défaite du candidat'),TIE:say('tie','égalité'),REFUSED_OR_UNQUALIFIED:say('refused or unqualified','refusé ou non qualifié'),DEFER_NO_FROZEN_REPAIR:say('deferred: no frozen repair candidate','différé : aucun candidat de réparation figé')}[value]??say('not established','non établi');
}
function failure(error){
 const value=error?.message??String(error);lastFailure=value;
 const errors={
  ACCESS_REQUIRED:['Connect with the existing operator token first.','Connectez-vous d’abord avec le jeton existant de l’opérateur.'],
  INPUT_JSON:['Use a JSON object containing initial, changes, repair and optional construction.','Utilisez un objet JSON contenant initial, changes, repair et éventuellement construction.'],
  INPUT_TASK:['Check release-plan/v1, the project identifier, public/synthetic permission and planning_only:true.','Vérifiez release-plan/v1, l’identifiant, l’autorisation public/synthetic et planning_only:true.'],
  INPUT_JOBS:['Use 1–18 unique J1…J999 jobs, durations 1–12, crew 1–4 and valid acyclic dependencies.','Utilisez 1–18 tâches J1…J999 uniques, durées 1–12, effectifs 1–4 et dépendances valides sans cycle.'],
  INPUT_CALENDAR:['Check the 1–128-slot calendar (capacity 0–4), deadline and observation time.','Vérifiez le calendrier de 1–128 créneaux (capacité 0–4), l’échéance et l’instant d’observation.'],
  INPUT_CHANGE:['Supply supported changes and repair fields. Do not supply a repair baseline, locks or authority.','Fournissez les champs de modification et de réparation pris en charge. Ne fournissez ni référence de réparation, ni verrouillage, ni autorité.'],
  INPUT_BYTES:['Choose a mission JSON no larger than 32 KB; each task must be at most 16 KB.','Choisissez un JSON de mission de 32 Ko maximum ; chaque tâche est limitée à 16 Ko.'],
  'Access token required':['The existing operator token is required.','Le jeton existant de l’opérateur est requis.'],
  'Executor state conflict; inspect retained status before retrying.':['Executor state conflict. Inspect retained status before retrying.','Conflit d’état de l’exécuteur. Examinez l’état conservé avant toute nouvelle tentative.'],
  'Executor input, source or evidence validation failed.':['Executor input, source or evidence validation failed.','Échec de validation des données, du code ou des preuves par l’exécuteur.'],
  'Fixed executor stopped without a committed reply; inspect retained status.':['The executor stopped without a committed reply. Inspect retained status.','L’exécuteur s’est arrêté sans réponse enregistrée. Examinez l’état conservé.'],
 };
 const pair=errors[value]??["Request unavailable. Inspect retained status and operator setup before retrying.","Demande indisponible. Examinez l’état conservé et la configuration de l’opérateur avant toute nouvelle tentative."];
 message(say(...pair),true);
}
let lastFailure=null;
// Preliminary usability checks only. No source, feasibility, cost or authority admission.
function preflightInput(){
 let value;try{value=JSON.parse($('input').value);}catch{throw Error('INPUT_JSON');}
 const object=x=>x&&typeof x==='object'&&!Array.isArray(x);
 const keys=(x,allowed)=>object(x)&&Object.keys(x).every(k=>allowed.includes(k));
 const integer=(n,min,max)=>Number.isSafeInteger(n)&&n>=min&&n<=max;
 if(!keys(value,['initial','changes','repair','construction'])||!value.initial||!value.changes||!value.repair)throw Error('INPUT_JSON');
 if(new TextEncoder().encode(JSON.stringify(value)).length>32768||new TextEncoder().encode(JSON.stringify(value.initial)).length>16000)throw Error('INPUT_BYTES');
 const t=value.initial;
 if(t.schema!=='release-plan/v1'||t.kind!=='plan'||typeof t.id!=='string'||!t.id.length||t.id.length>128||!['public','synthetic'].includes(t.public_or_synthetic)||t.planning_only!==true)throw Error('INPUT_TASK');
 if(!Array.isArray(t.jobs)||!integer(t.jobs.length,1,18))throw Error('INPUT_JOBS');
 const ids=new Set(t.jobs.map(j=>j?.id));
 if(ids.size!==t.jobs.length||t.jobs.some(j=>!keys(j,['id','duration','crew','deps'])||!/^J[1-9][0-9]{0,2}$/.test(j.id)||!integer(j.duration,1,12)||!integer(j.crew,1,4)||!Array.isArray(j.deps)||new Set(j.deps).size!==j.deps.length||j.deps.some(d=>!ids.has(d))))throw Error('INPUT_JOBS');
 const done=new Set();function visit(id,active=new Set()){if(active.has(id))throw Error('INPUT_JOBS');if(done.has(id))return;const next=new Set(active);next.add(id);for(const dep of t.jobs.find(j=>j.id===id).deps)visit(dep,next);done.add(id);}for(const j of t.jobs)visit(j.id);
 const calendar=x=>Array.isArray(x)&&integer(x.length,1,128)&&x.every(n=>integer(n,0,4));
 if(!calendar(t.capacity)||(t.deadline!==undefined&&!integer(t.deadline,1,t.capacity.length))||!integer(value.repair.observed_at,0,(value.changes.capacity??t.capacity).length-1))throw Error('INPUT_CALENDAR');
 if(!keys(value.changes,['durations','crew','capacity','release','deadline'])||!keys(value.repair,['observed_at','capacity','deadline','movement_limit'])||(value.construction!==undefined&&(!keys(value.construction,['enabled'])||typeof value.construction.enabled!=='boolean'))||t.baseline!==undefined||t.locked!==undefined||t.proof!==undefined||t.authority!==undefined)throw Error('INPUT_CHANGE');
 for(const [name,max]of [['durations',12],['crew',4]])if(value.changes[name]!==undefined&&(!object(value.changes[name])||Object.entries(value.changes[name]).some(([id,n])=>!ids.has(id)||!integer(n,1,max))))throw Error('INPUT_CHANGE');
 for(const [x,inheritedCapacity]of [[value.changes,t.capacity],[value.repair,value.changes.capacity??t.capacity]])if((x.capacity!==undefined&&!calendar(x.capacity))||(x.deadline!==undefined&&!integer(x.deadline,1,x.capacity?.length??inheritedCapacity.length)))throw Error('INPUT_CALENDAR');
 if(value.repair.capacity&&(value.repair.capacity.length!==(value.changes.capacity??t.capacity).length||value.repair.capacity.slice(0,value.repair.observed_at).some((n,i)=>n!==(value.changes.capacity??t.capacity)[i])))throw Error('INPUT_CALENDAR');
 $('input-feedback').textContent=say('Preliminary format checks passed. Feasibility, source, limits and approval still require the executor. No work has started.','Vérifications préliminaires du format réussies. L’exécuteur doit encore vérifier la faisabilité, le code, les limites et l’autorisation. Aucun travail démarré.');
 lastFailure=null;$('error').hidden=true;
 return value;
}
$('check-input').addEventListener('click',()=>{try{preflightInput();}catch(error){failure(error);}});
$('input-file').addEventListener('change',async event=>{
 const file=event.target.files[0];if(!file)return;
 try{if(file.size>32768)throw Error('INPUT_BYTES');$('input').value=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());preflightInput();}catch(error){failure(error);}finally{event.target.value='';}
});
function readableReport(plan){
 const lines=[say('AGI ALPHA · Mission report','AGI ALPHA · Rapport de mission'),
  say('Mission: ','Mission : ')+plan.plan_id,say('Source: ','Code : ')+plan.source_hash,
  say('Outcome hash: ','Empreinte du résultat : ')+plan.outcome_hash,
  say('State: ','État : ')+stateName(plan.state),
  say('Method: ','Méthode : ')+methodName(plan.method),
  say('Executor outcome verification: ','Vérification du résultat par l’exécuteur : ')+(plan.outcome?.verified===true?say('passed','réussie'):say('not verified — review required','non vérifié — examen requis')),
  say('Planning artifacts only. Physical work is not observed. No production authority.','Plans uniquement. Le travail physique n’est pas observé. Aucune autorité de production.'),''];
 if(!plan.outcome?.result?.phases?.length)lines.push(say('No planning schedules are present. For method construction, export the complete capability record, qualification and cost evidence.','Aucun calendrier de planification n’est présent. Pour une construction de méthode, exportez le dossier complet de capacité, de qualification et de coûts.'),'');
 for(const[index,phase]of(plan.outcome?.result?.phases??[]).entries()){
  lines.push(phaseName(index)+' · '+(phase.qualified?say('Qualified','Qualifié'):say('Review required','À vérifier')),
   say('Phase verification: ','Vérification de l’étape : ')+(phase.verified===true?say('passed','réussie'):say('not verified','non vérifiée')),
   say('Method: ','Méthode : ')+methodName(phase.selected_method),
   say('Makespan / movement: ','Durée / déplacement : ')+number(phase.result?.makespan)+' / '+number(phase.result?.movement),
   say('Receipt: ','Reçu : ')+phase.receipt_hash);
  for(const row of phase.result?.schedule??[])lines.push(row.id+' · '+row.start+' → '+row.end);
  lines.push('');
 }
 lines.push(say('Observed costs (declared units, not money):','Coûts observés (unités déclarées, pas de l’argent) :'),JSON.stringify(plan.outcome?.costs,null,2),
  say('native_solve_seconds is the charged solve ALLOWANCE per attempted native call, including failures; it is not measured CPU or wall time. Actual telemetry, when available, remains separate in the signed export.','native_solve_seconds est l’ALLOCATION de solveur débitée pour chaque appel natif tenté, y compris les échecs ; ce n’est pas une mesure CPU ou de durée réelle. Les mesures disponibles restent distinctes dans l’export signé.'),
  say('The fixed algorithms make zero model inference calls. Development and model-assisted authorship costs are outside that runtime count and remain partly unknown.','Les algorithmes fixes effectuent zéro appel d’inférence de modèle. Les coûts de développement et de rédaction assistée par modèle sont hors de ce compte d’exécution et restent partiellement inconnus.'),
  say('Approved caps:','Plafonds autorisés :'),JSON.stringify(plan.caps,null,2),
  say('Repair comparison: ','Comparaison de réparation : ')+consequenceName(plan.outcome?.result?.repair_usefulness?.consequence),
  admissionName(plan.outcome?.result?.repair_usefulness?.economic_decision),
  say('Human effort and full monetary/lifecycle costs remain unknown. Work counts do not establish savings, profit or self-acceleration. Export signed JSON for complete receipts, candidate comparisons, actual telemetry and provenance.','L’effort humain et les coûts monétaires et de cycle de vie complets restent inconnus. Les comptes n’établissent ni économie, ni profit, ni autoaccélération. Exportez le JSON signé pour les reçus, comparaisons, mesures réelles et provenance complets.'));
 return lines.join('\n')+'\n';
}
$('report').addEventListener('click',()=>{if(!currentPlan?.outcome)return;const blob=new Blob([readableReport(currentPlan)],{type:'text/plain;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='strategy-report-'+currentPlan.plan_id+'-'+language+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
function setLanguage(value){
 language=value;document.documentElement.lang=value;document.title=say('Strategy Succession · AGI ALPHA','Succession de stratégies · AGI ALPHA');
 $('language').textContent=value==='fr'?'EN':'FR';$('language').setAttribute('aria-label',value==='fr'?'English':'Français');
 for(const el of document.querySelectorAll('[data-fr]')){el.dataset.en??=el.textContent;el.textContent=value==='fr'?el.dataset.fr:el.dataset.en;}
 controls();
 if(currentPlan){showPlan(currentPlan,{resetConsent:false});renderOutcome(currentPlan);}
 if(latestStatus){retainedMissions(latestStatus);balances(latestStatus);}
 if(connected)refresh().catch(failure);
 if(lastFailure)failure(Error(lastFailure));
}
$('language').addEventListener('click',()=>setLanguage(language==='en'?'fr':'en'));
setLanguage(language);
