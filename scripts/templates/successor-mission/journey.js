// Exact native protocol receivers are bundled with this page. Imported content supplies data only.
const journeyReceivers=Object.freeze({
  manager:raw=>stageManager.inspectAlphaProject(raw,{...stageManagerContext.CONTEXT,validateNative:stageManager.validateBrowserAlpha}),
  jobs:raw=>stageJobs.inspectProjectTransfer(raw,{managerInspector:{source:stageManagerContext.CONTEXT.managerSource,inspect:journeyReceivers.manager}}),
  fleet:raw=>stageFleet.inspectProjectReturn(raw),
});
let journeyDB=null,journeyRaw=null,journeyRead=null,journeyUnsaved=false,recoveryRaw=null,recoveryProjectId=null;
function journeyControls(){
  const idle=ready&&!busy&&!active&&!pendingRun&&!stopping;
  $('journey-recovery').hidden=recoveryRaw===null;
  $('recovery-export').disabled=$('recovery-save').disabled=$('recovery-confirm').disabled=!idle||recoveryRaw===null;
  $('recovery-summary').textContent=recoveryRaw?`${recoveryProjectId} · ${new TextEncoder().encode(recoveryRaw).length} bytes · ${say('protected until you confirm keeping it','protégé jusqu’à confirmation de conservation')}`:'';
  $('journey-export').disabled=!idle||!dossier;
  $('route-export').disabled=!idle||!dossier||dirty;
  $('fleet-export').disabled=!idle||!dossier||dirty;
  $('journey-import').disabled=!idle;
  $('return-import').disabled=!idle||!dossier;
  $('journey-route').disabled=!idle;
  const route=$('journey-route').value,fr=language==='fr';
  const manager=route==='manager-usdc';
  const currentJobs=journeyRead&&dossier&&journeyRead.project.projectId===dossier.projectId&&journeyRead.project.projectDigest===dossier.projectDigest?journeyRead.routeTransfers?.['jobs-transfer']:null;
  $('jobs-planning').hidden=manager;$('jobs-amount').disabled=!idle||!!currentJobs;
  $('jobs-run').disabled=!idle||!currentJobs||dirty;
  if(currentJobs)$('jobs-amount').value=journeys.agialphaTokens(transport.parseBounded(currentJobs).planning.amountBaseUnits);
  $('route-export').textContent=manager?say('1. Download project for Manager','1. Télécharger pour Manager'):currentJobs?say('Download retained $AGIALPHA proposal','Télécharger la proposition $AGIALPHA conservée'):say('Compile and keep $AGIALPHA proposal','Compiler et conserver la proposition $AGIALPHA');
  $('route-open').href=manager?'https://montrealai.github.io/AGIJobManager/'+(fr?'fr/':'')+'successor/#alpha-project':'https://montrealai.github.io/AGIJobsv0/';
  $('route-open').textContent=manager?say('2. Open Manager · price in USDC','2. Ouvrir Manager · prix en USDC'):say('Read Jobs rules · $AGIALPHA','Lire les règles Jobs · $AGIALPHA');
  const displayed=journeyRead&&dossier&&journeyRead.project.projectId===dossier.projectId?journeyRead:null;
  $('journey-summary').textContent=displayed?`${displayed.project.projectId} · ${displayed.journey.history.length} ${say('retained stages','étapes conservées')} · ${journeyUnsaved?say('export before leaving','exportez avant de quitter'):say('saved locally','enregistré localement')} · ${say('historical receipts; no settlement','preuves historiques ; aucun règlement')}`:say('Run and review your project, choose one payment route, then keep each returned file in this history.','Exécutez et révisez le projet, choisissez un mode de règlement, puis conservez chaque fichier retourné dans cet historique.');
  $('journey-history').textContent=displayed?JSON.stringify({projectId:displayed.project.projectId,stages:displayed.summaries,authority:'none',independentReview:false,productionQualified:false,settlement:'not-connected'},null,2):'';
}
async function keepJourney(next,prior){
  const nextRead=await journeys.inspectJourney(next,journeyReceivers);
  if(recoveryRaw&&recoveryRaw!==next){
    const protectedRead=await journeys.inspectJourney(recoveryRaw,journeyReceivers),before=protectedRead.journey.history,after=nextRead.journey.history;
    const extendsProtected=nextRead.project.projectId===protectedRead.project.projectId&&after.length>=before.length&&before.every((event,i)=>event.kind===after[i].kind&&event.raw===after[i].raw&&event.sha256===after[i].sha256);
    if(!extendsProtected)throw Error('JOURNEY_KEEP_PROTECTED_RECOVERY_COPY_FIRST');
  }
  journeyRaw=next;journeyRead=nextRead;journeyUnsaved=true;
  try{
    if(journeyDB){await journeyDB.save(next,prior);journeyUnsaved=false;recoveryRaw=null;recoveryProjectId=null;}
    else {recoveryRaw=next;recoveryProjectId=nextRead.project.projectId;}
  }catch(e){
    recoveryRaw=next;recoveryProjectId=nextRead.project.projectId;
    status('Linked history could not be saved. Export the protected recovery copy before leaving; other history cannot replace it until you confirm keeping the file.','L’historique n’a pas pu être enregistré. Exportez la copie protégée avant de quitter ; un autre historique ne peut la remplacer avant votre confirmation.');throw e;
  }
}
window.addEventListener('beforeunload',event=>{if(recoveryRaw!==null){event.preventDefault();event.returnValue='';}});
$('recovery-export').addEventListener('click',()=>operation(async()=>{
  if(!recoveryRaw)throw Error('JOURNEY_NO_RECOVERY_COPY');
  await journeys.inspectJourney(recoveryRaw,journeyReceivers);
  download(recoveryRaw,`alpha-guided-recovery-${recoveryProjectId}.json`);
  status('Recovery download prepared. Confirm that you kept the exact file before acknowledging; this copy remains protected.','Téléchargement préparé. Confirmez avoir conservé le fichier exact avant de l’attester ; cette copie reste protégée.');
}));
$('recovery-save').addEventListener('click',()=>operation(async()=>{
  if(!recoveryRaw)throw Error('JOURNEY_NO_RECOVERY_COPY');
  const pending=recoveryRaw,checked=await journeys.inspectJourney(pending,journeyReceivers);
  const opened=await journeyStorage.openJourneyStore(journeyReceivers);
  try{
    const actual=await opened.get(checked.project.projectId);
    if(actual!==pending)await opened.save(pending,actual);
    journeyDB?.close();journeyDB=opened;
    if(journeyRaw===pending)journeyUnsaved=false;
    recoveryRaw=null;recoveryProjectId=null;
    status('Protected recovery history saved locally. Its complete prior history was checked and the write committed.','Historique protégé enregistré localement. L’historique antérieur complet a été vérifié et l’écriture confirmée.');
  }catch(e){opened.close();throw e;}
}));
$('recovery-confirm').addEventListener('click',()=>operation(async()=>{
  if(!recoveryRaw)throw Error('JOURNEY_NO_RECOVERY_COPY');
  recoveryRaw=null;recoveryProjectId=null;
  status('You confirmed keeping the recovery file. Other project histories may now be opened. The unsaved copy is still not recorded in local storage.','Vous confirmez avoir conservé le fichier. Les autres historiques peuvent être ouverts. La copie non enregistrée n’a toujours pas été sauvegardée localement.');
}));
async function syncJourney(){
  if(!dossier||dirty)throw Error('JOURNEY_SAVE_PROJECT_INPUT_FIRST');
  if(recoveryRaw&&recoveryProjectId!==dossier.projectId)throw Error('JOURNEY_KEEP_PROTECTED_RECOVERY_COPY_FIRST');
  const nativeRaw=transport.canonical(await projects.validateProject(dossier));
  let prior=journeyRaw&&journeyRead?.project.projectId===dossier.projectId?journeyRaw:null;
  if(!prior&&journeyDB)prior=await journeyDB.get(dossier.projectId);
  let next=prior??await journeys.createJourney(nativeRaw);
  const checked=await journeys.inspectJourney(next,journeyReceivers);
  if(checked.nativeRaw!==nativeRaw)next=await journeys.appendJourney(next,'alpha-cycle',nativeRaw,journeyReceivers);
  if(next!==prior)await keepJourney(next,prior);
  else {journeyRaw=next;journeyRead=checked;}
  return journeyRead;
}
$('journey-route').addEventListener('change',journeyControls);
$('route-export').addEventListener('click',()=>operation(async()=>{
  const read=await syncJourney();
  if($('journey-route').value==='manager-usdc'){
    download(read.nativeRaw,`alpha-project-${read.project.projectId}.json`);
    status('Project downloaded. Open Manager, inspect this file and confirm its mapping and USDC price there. No job is funded.','Projet téléchargé. Ouvrez Manager, inspectez le fichier, confirmez l’adaptation et le prix en USDC. Aucun financement.');
  }else{
    let raw=read.routeTransfers?.['jobs-transfer'];
    if(!raw){
      raw=await stageJobs.importAlphaProject(read.nativeRaw,{amountBaseUnits:journeys.agialphaBaseUnits($('jobs-amount').value),compiledAt:new Date().toISOString()});
      const prior=journeyRaw;await keepJourney(await journeys.appendJourney(prior,'jobs-transfer',raw,journeyReceivers),prior);
    }
    download(raw,`jobs-agialpha-project-${read.project.projectId}.json`);
    status('Native Jobs compiler produced seven bounded unfunded proposals in $AGIALPHA. The exact transfer is retained; inspect it or run its local task before preparing Fleet.','Le compilateur Jobs a produit sept propositions limitées non financées en $AGIALPHA. Le transfert exact est conservé ; inspectez-le ou exécutez la tâche locale avant Fleet.');
  }
}));
$('journey-export').addEventListener('click',()=>operation(async()=>{
  if(!journeyUnsaved||journeyRead?.project.projectId!==dossier?.projectId)await syncJourney();else await journeys.inspectJourney(journeyRaw,journeyReceivers);
  download(journeyRaw,`alpha-guided-project-${dossier.projectId}.json`);
}));
$('jobs-run').addEventListener('click',()=>operation(async()=>{
  const read=await syncJourney(),raw=read.routeTransfers?.['jobs-transfer'];if(!raw)throw Error('JOURNEY_JOBS_PROPOSAL_REQUIRED');
  const next=await stageJobs.runProjectTransfer(raw,{managerInspector:{source:stageManagerContext.CONTEXT.managerSource,inspect:journeyReceivers.manager}}),prior=journeyRaw;
  await keepJourney(await journeys.appendJourney(prior,'jobs-transfer',next,journeyReceivers),prior);
  download(next,`jobs-agialpha-result-${read.project.projectId}.json`);
  status('Local Jobs result checked and retained. This is bounded browser work; independent review and settlement remain separate.','Résultat local Jobs vérifié et conservé. Il s’agit d’un travail limité dans le navigateur ; la révision indépendante et le règlement restent distincts.');
}));
$('fleet-export').addEventListener('click',()=>operation(async()=>{
  const read=await syncJourney(),upstream=read.latestTransfer?.raw??read.nativeRaw;
  const requested=$('journey-route').value;
  if(read.latestTransfer){const wanted=read.latestTransfer.kind==='manager-transfer'?'manager-usdc':'agijobsv0-jobregistry-v2';if(wanted!==requested)throw Error('JOURNEY_SELECTED_ROUTE_DIFFERS_FROM_RETURN');}
  const request=await stageFleet.createProjectRequest(upstream,{language,route:requested});
  download(request,`fleet-project-request-${read.project.projectId}.json`);
  status('Fleet request downloaded. Its local operator must explicitly authorize execution and internal checking. This request grants no permission or funding.','Demande Fleet téléchargée. Son opérateur local doit autoriser explicitement l’exécution et la vérification interne. Aucun financement ni permission n’est accordé.');
}));
async function importedJourney(file){
  if(file.size>journeys.JOURNEY_LIMIT)throw Error('JOURNEY_BYTES');
  return new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(new Uint8Array(await file.arrayBuffer()));
}
$('return-import').addEventListener('change',async()=>{
  const file=$('return-import').files[0];if(!file||busy||active||pendingRun||stopping)return;
  await operation(async()=>{
    const raw=await importedJourney(file),kind=journeys.returnKind(raw);
    await syncJourney();const prior=journeyRaw,next=await journeys.appendJourney(prior,kind,raw,journeyReceivers);
    await keepJourney(next,prior);
    status('Validated return retained in the same project history. Imported reviews remain historical; select the input and start a fresh Alpha cycle to continue.','Retour validé conservé dans le même historique. Les avis importés restent historiques ; choisissez les données et créez un nouveau cycle Alpha pour continuer.');
  });$('return-import').value='';
});
$('journey-import').addEventListener('change',async()=>{
  const file=$('journey-import').files[0];if(!file||busy||active||pendingRun||stopping)return;
  await operation(async()=>{
    const raw=await importedJourney(file);
    if(recoveryRaw&&recoveryRaw!==raw)throw Error('JOURNEY_KEEP_PROTECTED_RECOVERY_COPY_FIRST');
    const read=await journeys.inspectJourney(raw,journeyReceivers);
    const stored=journeyDB?await journeyDB.get(read.project.projectId):null;
    if(stored&&stored!==raw)throw Error('JOURNEY_IMPORT_CONFLICT_OPEN_SAVED_HISTORY');
    await inspectProject(read.nativeRaw);journeyRaw=raw;journeyRead=read;journeyUnsaved=!stored;
    if(!stored)await keepJourney(raw,null);
    status('Complete history inspected. Native work and returned receipts remain historical. Choose the input and start a fresh cycle explicitly.','Historique complet inspecté. Les résultats et avis restent historiques. Choisissez les données et créez explicitement un nouveau cycle.');
  });$('journey-import').value='';
});
(async()=>{try{journeyDB=await journeyStorage.openJourneyStore(journeyReceivers);}catch(e){error(e);}finally{journeyControls();}})();
