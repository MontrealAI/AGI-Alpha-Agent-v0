// SPDX-License-Identifier: Apache-2.0
const originalDocument = '<!doctype html>\n' + document.documentElement.outerHTML;
const byId = id => document.getElementById(id);
const english = Object.fromEntries([...document.querySelectorAll('[data-word]')].map(el => [el.dataset.word, el.textContent]));
english.title = 'Build the intelligence you can keep.';
const french = {
  skip:'Aller à l’atelier', larger:'Texte plus grand', eyebrow:'VOTRE MISSION. VOS MÉTHODES. VOTRE PROCHAIN CHAPITRE.',
  title:'Construisez l’intelligence que vous gardez.', intro:'Donnez une mission à votre SUCCESSOR Ω. Alpha construit et compare des candidats. AGI Jobs transforme le plan en tâches délimitées et vérifiables. Emportez l’exemple fonctionnel.',
  begin:'Construire mon premier Ω ↓', free:'Environ 5 minutes · Gratuit · Sans compte, portefeuille ni installation',
  'mission-card':'Votre analyste de données ouvertes.', 'mission-sub':'Une petite mission. Des réponses exactes. Des preuves à examiner.', candidate:'CANDIDAT · ATELIER LOCAL',
  shared:'DEUX SYSTÈMES DÉPLOYÉS · UN MÊME JETON', copy:'Copier l’adresse du jeton', 'all-contracts':'Voir les 29 contrats déployés ↓',
  together:'DEUX PROJETS, UN EXEMPLE CONCRET', 'together-title':'Du plan à un résultat que vous pouvez examiner.',
  'alpha-title':'Construire un candidat', 'alpha-text':'Quatre petits programmes rivalisent pour regrouper des données fictives et calculer des totaux exacts. Gardez la configuration choisie, l’identité du code et les mesures.',
  'jobs-title':'Rendre le travail vérifiable', 'jobs-text':'Le véritable compilateur AGI Jobs produit 21 tâches avec entrées, limites, dépendances, critères et empreintes non signées. Ce sont des brouillons à examiner.',
  'own-title':'Garder le dossier complet', 'own-text':'Enregistrez le laboratoire, la mission, le graphe de tâches, les résultats et les notes. La preuve indépendante et une décision d’admission distincte restent nécessaires.',
  workshop:'L’ATELIER PRATIQUE', 'workshop-title':'Faites d’Atlas Ω le vôtre.', scope:'La mission : compter les événements, les erreurs, la durée totale et maximale par jour et service. Les données sont fictives et non personnelles. Aucun modèle externe n’est appelé.',
  loading:'Ouverture de l’atelier… JavaScript et Web Crypto sont nécessaires.', step1:'1 · Nommer et planifier', step2:'2 · Construire et comparer', step3:'3 · Examiner et garder',
  settings:'Votre point de départ', name:'Nommez votre Ω', events:'Quelle quantité de données fictives?', budget:'Budget de planification · jetons AGIALPHA',
  'budget-help':'Exemple modifiable, sans devis ni fonds déposés. Rien n’est dépensé. Gaz, mises, revue et exploitation doivent être estimés séparément.',
  run:'Construire et tester mon Ω', stop:'Arrêter', ready:'Tout est prêt pour votre premier exemple.', labels:'Les noms du producteur, du vérificateur et du décideur sont des rôles fictifs, sans identité indépendante ni approbation signée.',
  'result-label':'VOTRE DOSSIER DE CONSTRUCTION', 'empty-title':'Un premier pas concret.', empty:'Construisez l’exemple pour voir les tests d’exactitude, les durées mesurées et le portefeuille de tâches.',
  local:'RÉPÉTITION LOCALE · ADMISSION SUSPENDUE', checks:'jeux de données concordants', jobs:'brouillons de tâches', spent:'jetons dépensés', timings:'Mesuré ici · six comparaisons', approach:'Approche',
  'timing-note':'Le candidat peut perdre. Les durées varient avec l’appareil, l’ordre des tests et le navigateur. Il ne s’agit ni de preuve indépendante ni d’avantage économique mesuré.',
  historical:'Notes historiques restaurées. Relancez la construction pour produire de nouvelles preuves.', rollback:'Conserver la référence',
  'jobs-heading':'Un plan clair, une tâche délimitée à la fois.', 'jobs-note':'Chaque phase correspond aux tâches du véritable compilateur. Après la construction, ouvrez une phase pour voir ses livrables. Les tâches restent DRAFT; une empreinte lie les termes, elle n’accepte pas le travail. Les détails exportés du compilateur sont en anglais.',
  'keep-label':'QUELQUE CHOSE À GARDER', 'keep-title':'Votre Ω. Votre prochaine expérience.', 'keep-text':'Téléchargez le laboratoire complet. Ouvrez le fichier HTML dans un navigateur sur ordinateur, même hors ligne. Il conserve vos dernières notes; relancez pour de nouveaux résultats. Enregistrez une nouvelle copie après modification.',
  privacy:'Vos entrées restent dans cette page. Aucun envoi ni enregistrement automatique. Les fichiers téléchargés sont lisibles : utilisez un surnom et enregistrez avant de fermer.',
  save:'Enregistrer mon Ω fonctionnel', pack:'Télécharger le dossier · JSON', briefs:'Télécharger les 21 fiches de tâches', request:'Télécharger la requête Alpha', inspect:'Examiner le dossier exact et l’identité du code',
  integrity:'L’empreinte vérifie la cohérence, pas l’authenticité. Ce format d’exemple n’est ni une instruction de règlement ni une sauvegarde native à restaurer.',
  'next-label':'ADAPTEZ L’EXEMPLE À VOTRE MISSION', 'next-title':'Construire. Prouver. Puis décider.', next1:'Choisir une tâche utile et testable',
  'next1-text':'Commencez par un calcul sur données publiques, une fonction libre ou une reproduction numérique. Fixez les droits, résultats, limites d’erreur, temps de revue et budget réversible.',
  next2:'Commander des tâches délimitées', 'next2-text':'Utilisez les fiches exportées pour convenir des livrables. Un opérateur doit choisir et mettre en service le marché, les identités, les preuves et le règlement. Cet atelier ne publie aucune tâche réelle.',
  next3:'Mériter la permission suivante', 'next3-text':'Figez le candidat complet. Des vérificateurs indépendants doivent le comparer aux meilleures références sur du travail frais et protégé, coûts complets inclus. Seule une décision humaine distincte peut accorder une autorité limitée, temporaire et révocable.',
  native:'Exécuter la même requête dans votre environnement Alpha installé', 'native-text':'Après la construction, téléchargez la requête Alpha. Avec alpha-agent installé, exécutez la commande ci-dessous. Le résultat est une répétition locale distincte; examinez-le dans l’espace Alpha complet.', 'full-lab':'Ouvrir l’espace Alpha complet ↗',
  'contracts-label':'DÉPLOIEMENTS ETHEREUM MAINNET DOCUMENTÉS', 'contracts-title':'Deux suites déployées. Le même $AGIALPHA.',
  'contract-scope':'Les 29 instances ci-dessous proviennent des dossiers publics des 11–12 octobre 2026. Le jeton partagé a 18 décimales. Ces dossiers identifient les déploiements; ils ne suivent pas leur disponibilité en direct.',
  routing:'Le MARK déployé d’Alpha est lié à son propre marché. Il ne transfère pas les fonds vers AGIJobsv0. Le déploiement Alpha précède des protections ultérieures; le dossier Jobs n’ouvre pas l’admission publique. Vérifiez l’état de préparation avant tout financement réel.',
  'alpha-readiness':'Déploiement et préparation Alpha ↗', 'jobs-readiness':'Préparation AGI Jobs ↗', questions:'Quelques réponses claires.',
  'is-asi':'Ai-je créé une ASI spécialisée?', 'is-asi-text':'Vous avez construit un exemple de candidat reproductible. L’ASI spécialisée est une désignation limitée à une mission, acquise par preuve comparative indépendante. SUCCESSOR Ω exige aussi une admission distincte et responsable. Cet atelier n’accorde ni l’une ni l’autre.',
  ownership:'Qu’est-ce qui m’appartient?', 'ownership-text':'Vous contrôlez vos fichiers téléchargés, notes et résultats. Le code Alpha est sous Apache 2.0 et le compilateur AGI Jobs sous MIT. Les droits des tiers demeurent. Propriété exclusive, droits sur les travaux commandés et portabilité des fournisseurs doivent être établis séparément.',
  models:'Où sont les modèles neuronaux?', 'models-text':'Cet exemple utilise du code déterministe pour rendre chaque résultat examinable. Un successeur neuronal-symbolique peut ajouter des modèles remplaçables et des programmes exécutables par tâches délimitées. Les exigences de mission, preuve, coûts, retour arrière et admission restent les mêmes.',
  papers:'Quel lien avec les quatre guides SUCCESSOR Ω?', 'papers-text':'L’exemple concrétise leur cycle : choisir une mission réversible, constituer les tâches, former et figer un candidat, le comparer, conserver les preuves utiles et séparer l’admission. Les cas publics du navigateur forment un Gym pédagogique, sans remplacer une évaluation indépendante protégée.',
  source:'Code source et guide de reproduction ↗', 'jobs-home':'Explorer AGI Jobs ↗', licenses:'Licences des logiciels inclus',
};
const phases = [
  ['Constitute the mission', 'Constituer la mission', 0, 4],
  ['Design the teaching Gym', 'Concevoir le Gym pédagogique', 4, 7],
  ['Build the candidate', 'Construire le candidat', 7, 11],
  ['Prepare proof & rollback', 'Préparer la preuve et le retour arrière', 11, 16],
  ['Evaluate & seek acceptance', 'Évaluer et demander l’acceptation', 16, 19],
  ['Admit & renew separately', 'Admettre et renouveler séparément', 19, 21],
];
let language = new URLSearchParams(location.search).get('lang') === 'fr' ? 'fr' : 'en';
const largePreference = new URLSearchParams(location.search).get('text') === 'large';
document.documentElement.classList.toggle('large',largePreference);
byId('larger').setAttribute('aria-pressed',String(largePreference));
let pack = null, notes = null, controller = null, seed = 42;
let formState = {name:'Atlas Ω',events:1000,budget:'2100'};
try {
  const raw = byId('saved-state').textContent;
  if (raw.length > 500000) throw Error('Saved notes exceed the size limit.');
  const saved = JSON.parse(raw);
  if (saved.form) {
    model.missionFor(saved.form);
    if (![256,1000,4000].includes(saved.form.events)) throw Error('Invalid workload.');
    formState = saved.form;
    language = saved.language === 'fr' ? 'fr' : 'en';
    notes = saved.notes || null;
  }
} catch { byId('status').textContent = 'Saved settings could not be restored. Start a new build.'; }
byId('name').value = formState.name;
byId('events').value = formState.events;
byId('budget').value = formState.budget;
const words = (en, fr) => language === 'fr' ? fr : en;
function message(en, fr) { byId('status').textContent = words(en, fr); }
function renderPortfolio() {
  byId('portfolio').replaceChildren();
  for (const [en,fr,start,end] of phases) {
    const details = document.createElement('details'), summary = document.createElement('summary');
    summary.textContent = `${language === 'fr' ? fr : en} · ${end-start} ${words('jobs','tâches')}`;
    details.append(summary);
    for (let i=start;i<end;i++) {
      const article=document.createElement('article'), h=document.createElement('h4'), p=document.createElement('p');
      article.className='job'; h.textContent=`${i+1}. ${jobsTemplates.JOB_TEMPLATES[i].title}`;
      p.textContent=model.DELIVERABLES[i]; article.append(h,p);
      if(pack){ const info=document.createElement('p'); info.textContent=`DRAFT · ${pack.compilation.graph.nodes[i].digest}`; article.append(info); }
      details.append(article);
    }
    byId('portfolio').append(details);
  }
}
function render() {
  document.documentElement.lang=language;
  for(const node of document.querySelectorAll('[data-word]')) node.textContent=(language==='fr'?french:english)[node.dataset.word] || english[node.dataset.word];
  byId('language').textContent=language==='fr'?'English':'Français';
  byId('language').lang=language==='fr'?'en':'fr';
  if(pack){
    byId('result-title').textContent=pack.title;
    byId('checks').textContent=`${pack.evaluation.cases.filter(c=>c.exact_output).length} / 6`;
    byId('verdict').textContent=pack.evaluation.correctness ? words('Exactness checks passed. Read the comparison before deciding what to keep.','Les tests d’exactitude passent. Examinez la comparaison avant de choisir.') : words('A hard check failed. Keep the baseline and investigate.','Un test obligatoire échoue. Conservez la référence et examinez l’erreur.');
    byId('timings').replaceChildren();
    for(const [key,en,fr] of [['current','Existing baseline','Référence actuelle'],['beta','Map-based alternative','Autre référence déterministe'],['candidate','Your candidate','Votre candidat']]){
      const tr=document.createElement('tr'), th=document.createElement('th'), td=document.createElement('td');
      th.scope='row';th.textContent=words(en,fr);td.textContent=(pack.evaluation.totals_ns[key]/1e6).toFixed(3);tr.append(th,td);byId('timings').append(tr);
    }
  }
  byId('result').hidden=!pack;byId('empty').hidden=!!pack;
  for(const id of ['pack','briefs','request'])byId(id).disabled=!pack;
  byId('evidence').textContent=JSON.stringify(pack||notes||{},null,2);
  renderPortfolio();
}
function download(filename, text, type) {
  const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');
  a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  byId('save-status').textContent=words('Download prepared. Check your Downloads folder.','Téléchargement préparé. Consultez votre dossier Téléchargements.');
}
function settings(){ return {name:byId('name').value.trim(), events:Number(byId('events').value), budget:byId('budget').value}; }
function invalidate(){ if(pack)notes={status:'HISTORICAL_ONLY',record:pack};pack=null;render();message('Settings changed. Build again to bind fresh results to them.','Paramètres modifiés. Relancez pour obtenir des résultats correspondants.'); }
byId('form').addEventListener('input',invalidate);
byId('form').addEventListener('submit',async event=>{
  event.preventDefault();if(controller)return;
  controller=new AbortController();if(pack)notes={status:'HISTORICAL_ONLY',record:pack};pack=null;render();
  for(const id of ['run','name','events','budget','save','language'])byId(id).disabled=true;
  byId('stop').hidden=false;byId('progress').hidden=false;
  try {
    pack=await model.buildPack({...settings(),language,seed:seed++,engineSourceHash:ENGINE_HASH},{signal:controller.signal,onProgress:phase=>{
      byId('progress').value={compile:0,discover:1,evaluate:2}[phase];
      message({compile:'Compiling 21 bounded work orders…',discover:'Comparing four candidate programs…',evaluate:'Checking the frozen candidate on six further workloads…'}[phase],{compile:'Compilation de 21 tâches délimitées…',discover:'Comparaison de quatre programmes candidats…',evaluate:'Vérification du candidat figé sur six autres jeux de données…'}[phase]);
    }});
    byId('progress').value=3;render();message('Build complete. Review your results and save your Ω.','Construction terminée. Examinez les résultats et enregistrez votre Ω.');
    byId('result-title').tabIndex=-1;byId('result-title').focus();
  } catch(error){pack=null;render();message(error.name==='AbortError'?'Stopped. No active result; no funds spent.':'Build failed: '+error.message,error.name==='AbortError'?'Arrêté. Aucun résultat actif; aucune dépense.':'Échec : '+error.message);}
  finally { controller=null;for(const id of ['run','name','events','budget','save','language'])byId(id).disabled=false;byId('stop').hidden=true;byId('progress').hidden=true; }
});
byId('stop').onclick=()=>controller?.abort();
byId('language').onclick=()=>{language=language==='en'?'fr':'en';render();};
byId('larger').onclick=()=>{const active=document.documentElement.classList.toggle('large');byId('larger').setAttribute('aria-pressed',String(active));};
byId('rollback').onclick=()=>{notes={status:'BASELINE_RETAINED',record:pack};pack=null;render();message('Baseline retained. The candidate is now only a historical note. Build again to propose a successor.','Référence conservée. Le candidat est désormais une note historique. Relancez pour proposer un successeur.');};
byId('pack').onclick=()=>{if(pack)download('successor-build-pack.json',JSON.stringify(pack,null,2)+'\n','application/json');};
byId('briefs').onclick=()=>{if(pack)download('successor-job-briefs.md',model.jobBriefs(pack),'text/markdown');};
byId('request').onclick=()=>{if(pack)download('request.json',JSON.stringify(pack.request,null,2)+'\n','application/json');};
byId('save').onclick=()=>{
  try {
    model.missionFor(settings());
    const saved=JSON.stringify({form:settings(),language,notes:pack?{status:'HISTORICAL_ONLY',record:pack}:notes}).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');
    const html=originalDocument.replace(/(<script type="application\/json" id="saved-state">)[\s\S]*?(<\/script>)/,(_,a,b)=>a+saved+b);
    download('My-SUCCESSOR-Omega-Builder.html',html,'text/html');
  }catch(error){byId('save-status').textContent=error.message;}
};
byId('copy-token').hidden=false;
byId('copy-token').onclick=async()=>{try{await navigator.clipboard.writeText(model.TOKEN);byId('copy-status').textContent=words('Address copied.','Adresse copiée.');}catch{byId('copy-status').textContent=words('Select and copy the full address shown here.','Sélectionnez et copiez l’adresse complète affichée.');}};
render();
if(notes)message('Your saved settings and historical notes are restored. Build again for current results.','Paramètres et notes historiques restaurés. Relancez pour de nouveaux résultats.');
byId('app').hidden=false;byId('loading').hidden=true;
if(!globalThis.crypto?.subtle){byId('run').disabled=true;message('Web Crypto is unavailable. Open this file in a current desktop browser.','Web Crypto est indisponible. Ouvrez ce fichier dans un navigateur récent sur ordinateur.');}
