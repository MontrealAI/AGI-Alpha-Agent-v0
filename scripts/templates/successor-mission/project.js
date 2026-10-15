// One additive project layer in the existing mission workspace. No external execution.
let projectDB=null,dossier=null,projectHistorical=false,projectUnpersisted=false,projectState=null,selectedDiscoveryBytes=null;
const mappingChoices=()=>({family:'public-data',selection:'explicit-user-selection',duplicatePolicy:'sum-all-rows-no-deduplication',unitPolicy:'unchanged-integer-units',dataRights:current.spec.rights.dataClass});
function projectControls(){
  const idle=ready&&!busy&&!active&&!pendingRun&&!stopping;
  $('project-start').disabled=!idle||!projectDB||!current||dirty||!$('project-choice').checked;
  $('project-export').disabled=!dossier||busy;
  $('project-import').disabled=!idle;
  $('project-open').disabled=!idle||!projectDB;
  $('project-saved').disabled=!idle||!projectDB;
  $('project-resume').disabled=!idle||!dossier||!projectHistorical||!projectDB||!$('project-choice').checked;
  $('project-choice').disabled=!idle;
  $('discovery-import').disabled=!idle;
  $('discovery-clear').disabled=!idle||!selectedDiscoveryBytes;
  if(dossier&&dirty&&!$('project-choice').checked)$('save').disabled=true;
  $('project-summary').textContent=dossier?`${dossier.projectId} · cycle ${dossier.cycles.at(-1).cycleId} · revision ${dossier.revision} · ${projectHistorical?'historical / historique':projectUnpersisted?'not saved / non enregistré':'local'} · authority: none / aucune`:say('Choose and save the permitted CSV below, then explicitly link it to an illustrative reporting opportunity.','Choisissez et enregistrez le CSV autorisé ci-dessous, puis reliez-le explicitement à une possibilité illustrative de rapport.');
  $('project-history').textContent=dossier?JSON.stringify({sourceAuthenticity:'not-established',sourceCurrent:projectState?.sourceCurrent??false,currentReview:projectHistorical||readOnly||dirty?null:projectState?.currentReview,cycles:dossier.cycles.map((c,i)=>({cycleId:c.cycleId,parentCycleDigest:c.parentCycleDigest,discovery:JSON.parse(c.discovery.bytes).input,mapping:c.mapping,unfundedStageWork:c.stageWork,recordDigests:c.records.map(a=>a.artifactDigest),evaluationStatus:i<dossier.cycles.length-1?'stale-dependent-evaluation':projectHistorical?'historical-incomplete':c.evaluationDraft?.status||'not-prepared',evaluationDraft:c.evaluationDraft})),decisions:dossier.history},null,2):'';
  $('project-next').textContent=dossier?(projectHistorical?say('Next: explicitly start a fresh cycle. Imported results and reviews stay historical.','Suite : démarrez explicitement un nouveau cycle. Les résultats et avis importés restent historiques.'):current?.result?say('Next: inspect the actual result. Candidate identities, protected evaluation, metric methods and reviewer custody are still missing.','Suite : inspectez le résultat réel. Les identités, l’évaluation protégée, les méthodes et la garde des preuves restent à définir.'):say('Next: explicitly run this local CSV task.','Suite : exécutez explicitement cette tâche CSV locale.')):'';
}
async function projectList(){if(!projectDB)return;const rows=await projectDB.list();$('project-saved').replaceChildren();for(const p of rows){const option=document.createElement('option');option.value=p.projectId;option.textContent=`${p.projectId} · r${p.revision}`;$('project-saved').append(option);}if(dossier)$('project-saved').value=dossier.projectId;}
async function saveProject(next,expected){
  try{await projectDB.save(next,expected);}catch(e){dossier=next;projectUnpersisted=true;projectHistorical=true;readOnly=true;mode='project-conflict-or-storage-loss';current=JSON.parse(next.cycles.at(-1).records.at(-1).bytes);status('Project save failed. This copy is read-only; export it, then reopen the saved project.','Échec de l’enregistrement. Cette copie est en lecture seule ; exportez-la, puis rouvrez le projet enregistré.');throw e;}
  projectState=await projects.projectView(next,{sourceHash:SOURCE_HASH,sources:PROJECT_SOURCES,restored:false});
  if(!projectState.sourceCurrent){readOnly=true;projectHistorical=true;}
  dossier=next;projectUnpersisted=false;current=JSON.parse(next.cycles.at(-1).records.at(-1).bytes);dirty=false;unpersisted=false;
  try{await projectList();}catch(e){readOnly=true;projectHistorical=true;error(e);status('Project committed, but its index could not be read. Export before reopening.','Projet enregistré, mais index illisible. Exportez-le avant de rouvrir.');}
}
async function persistProject(next){
  const prior=dossier,old=JSON.parse(prior.cycles.at(-1).records.at(-1).bytes);let updated;
  if(next.specDigest!==old.specDigest){
    if(!$('project-choice').checked)throw Error('PROJECT_EXPLICIT_INPUT_SELECTION_REQUIRED');
    const fresh=await records.createRecord({missionId:id(),sourceHash:SOURCE_HASH,spec:next.spec});
    const selected={...mappingChoices(),dataRights:fresh.spec.rights.dataClass};
    updated=await projects.nextCycle(prior,{cycleId:id(),record:fresh,choices:selected,sourceHash:SOURCE_HASH,sources:PROJECT_SOURCES,expectedRevision:prior.revision});
  }else updated=await projects.appendRecord(prior,next,{expectedRevision:prior.revision,sourceHash:SOURCE_HASH,sources:PROJECT_SOURCES});
  await saveProject(updated,{revision:prior.revision,digest:prior.projectDigest});render();
}
$('discovery-import').addEventListener('change',async()=>{
  const file=$('discovery-import').files[0];if(!file||busy||active||pendingRun||stopping)return;const token=++epoch;busy=true;controls();clearError();
  try{if(file.size>projects.LIMIT)throw Error('PROJECT_BYTES');const text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(new Uint8Array(await file.arrayBuffer()));const brief=await projects.inspectDiscovery(text);if(token!==epoch||$('discovery-import').files[0]!==file)return;selectedDiscoveryBytes=text;$('project-choice').checked=false;$('discovery-selected').textContent='For a NEW project / Pour un NOUVEAU projet : '+brief.input.mission+' · Imported claims, unverified source/authorship. Exact bytes retained; integrity only. / Déclarations importées, source et auteur non vérifiés.';}catch(e){if(token===epoch)error(e);}finally{if(token===epoch){busy=false;render();}if($('discovery-import').files[0]===file)$('discovery-import').value='';}
});
$('discovery-clear').addEventListener('click',()=>{selectedDiscoveryBytes=null;$('project-choice').checked=false;$('discovery-selected').textContent='Illustrative public-data opportunity / Possibilité illustrative de données publiques';controls();});
$('project-choice').addEventListener('change',controls);
$('project-start').addEventListener('click',()=>operation(async()=>{
  if(!$('project-choice').checked||dirty||!current)throw Error('PROJECT_EXPLICIT_INPUT_SELECTION_REQUIRED');
  const fresh=await records.createRecord({missionId:id(),sourceHash:SOURCE_HASH,spec:current.spec});
  const discoveryBytes=selectedDiscoveryBytes??transport.canonical(await discovery.createBrief(projects.publicDataOpportunity(),SOURCE_HASH));
  const next=await projects.createProject({projectId:id(),cycleId:id(),sourceHash:SOURCE_HASH,discoveryBytes,record:fresh,choices:mappingChoices(),sources:PROJECT_SOURCES});
  projectHistorical=false;readOnly=false;await saveProject(next,null);mode=readOnly?'project-storage-loss':'project';fill();status(selectedDiscoveryBytes?'Project saved with the exact imported discovery bytes. Claims remain unverified; the selected CSV is a separate bounded task.':'Project saved with the labelled illustrative opportunity. Run the explicitly selected CSV task.','Projet enregistré. Les déclarations restent non vérifiées ; la tâche CSV est choisie séparément.');
}));
$('project-export').addEventListener('click',()=>operation(async()=>{await projects.validateProject(dossier);download(transport.canonical(dossier),`successor-project-${projectUnpersisted?'unpersisted-':''}${dossier.projectId}.json`);}));
async function inspectProject(raw){selectedDiscoveryBytes=null;$('discovery-selected').textContent='New project: illustrative opportunity. Current project discovery is shown below. / Nouveau projet : illustration. Le dossier actuel figure ci-dessous.';const checked=await projects.validateProject(raw);const inspected=await projects.projectView(checked,{sourceHash:SOURCE_HASH,sources:PROJECT_SOURCES,restored:true});projectState=inspected;dossier=checked;current=inspected.record;projectHistorical=true;readOnly=true;mode='project-historical';historicalBytes=null;fill();$('project-choice').checked=false;status('Project restored as history. No review or permission became current. Select the input and start a fresh cycle.','Projet restauré comme historique. Aucun avis ni permission n’est devenu courant. Choisissez les données et démarrez un nouveau cycle.');}
$('project-open').addEventListener('click',()=>operation(async()=>{const p=await projectDB.get($('project-saved').value);if(!p)throw Error('PROJECT_NOT_FOUND');await inspectProject(p);projectUnpersisted=false;}));
$('project-import').addEventListener('change',async()=>{
  const file=$('project-import').files[0];if(!file||busy||active||pendingRun||stopping)return;const token=++epoch;busy=true;controls();clearError();
  try{if(file.size>projects.LIMIT)throw Error('PROJECT_BYTES');const bytes=new Uint8Array(await file.arrayBuffer());const text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);const p=await projects.validateProject(text);if(token!==epoch||$('project-import').files[0]!==file)return;await inspectProject(p);projectUnpersisted=true;}catch(e){if(token===epoch)error(e);}finally{if(token===epoch){busy=false;render();}if($('project-import').files[0]===file)$('project-import').value='';}
});
$('project-resume').addEventListener('click',()=>operation(async()=>{
  if(!$('project-choice').checked||!projectHistorical)throw Error('PROJECT_EXPLICIT_INPUT_SELECTION_REQUIRED');
  const prior=dossier;const stored=await projectDB.get(prior.projectId);
  if(stored&&stored.projectDigest!==prior.projectDigest)throw Error('PROJECT_IMPORT_CONFLICT_OPEN_LATEST');
  const fresh=await records.createRecord({missionId:id(),sourceHash:SOURCE_HASH,spec:current.spec});
  const next=await projects.nextCycle(prior,{cycleId:id(),record:fresh,choices:mappingChoices(),sourceHash:SOURCE_HASH,sources:PROJECT_SOURCES,recovered:true,expectedRevision:prior.revision});
  projectHistorical=false;readOnly=false;await saveProject(next,stored?{revision:stored.revision,digest:stored.projectDigest}:null);
  mode=readOnly?'project-storage-loss':'project';fill();view('mission');status('Fresh cycle saved in the same project. Running and reviewing require new explicit actions.','Nouveau cycle enregistré dans le même projet. Exécuter et réviser nécessitent de nouvelles actions explicites.');
}));

(async()=>{try{db=await storage.openMissionStore();await refreshList();try{projectDB=await projectStorage.openProjectStore();await projectList();}catch(e){error(e);}status('Choose a saved mission or create a new example.','Choisissez une mission enregistrée ou créez un nouvel exemple.');}catch(e){loseStorage(e);}finally{ready=true;render();}})();
