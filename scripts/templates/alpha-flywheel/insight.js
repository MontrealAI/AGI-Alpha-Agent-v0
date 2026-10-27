// SPDX-License-Identifier: Apache-2.0
function renderInsight(){
  const evidence=INSIGHT_EVIDENCE, chosen=$('insight-candidate').value;
  $('insight-candidate').replaceChildren();
  for(const row of evidence.candidate_dossier){const option=document.createElement('option');option.value=row.id;option.textContent=row[language]||row.en;$('insight-candidate').appendChild(option);}
  if(evidence.candidate_dossier.some(row=>row.id===chosen))$('insight-candidate').value=chosen;else $('insight-candidate').value='usable-research-access';
  const candidate=evidence.candidate_dossier.find(row=>row.id===$('insight-candidate').value);
  const findings={
    'calibration-cohort':say('Rejected for this increment: shared access and proficiency testing are established; material quality and liability evidence is unavailable.','Piste écartée ici : accès partagé et essais d’aptitude établis ; preuves de qualité des matériaux et de responsabilité indisponibles.'),
    'heat-access':say('Rejected for this increment: deployment needs local health, accessibility, transport and facility evidence.','Piste écartée ici : une mise en service demande des preuves locales de santé, d’accessibilité, de transport et d’installations.'),
    'usable-research-access':say('Selected for exploratory construction: compose resource, institution, data and method prerequisites. Existing procedures are substantial prior art; recipient need and novelty remain unresolved.','Retenue pour une construction exploratoire : composer les prérequis des ressources, institutions, données et méthodes. Les procédures existantes constituent des antériorités substantielles ; besoin réel et nouveauté restent non établis.')
  };
  setText('insight-candidate-detail',findings[candidate.id]);
  const ordinary=evidence.search_report.arms.find(row=>row.arm==='U');
  setText('insight-search-denominator',say(`Frozen search denominator: ${ordinary.denominator} units per arm. U: ${ordinary.counts.missing} missing; E: one supplied candidate, two rejected paths. No measured search advantage.`,`Dénominateur figé : ${ordinary.denominator} unités par groupe. U : ${ordinary.counts.missing} absentes ; E : une candidate fournie, deux pistes écartées. Aucun avantage de recherche mesuré.`));
  const episode=evidence.construction_cases.find(row=>row.case_id===$('insight-case').value), result=episode.result;
  const names={
    'institution-clearance':say('Institutional clearance required','Autorisation de l’institution requise'),
    'access-award':say('Resource allocation declared','Attribution de ressource déclarée'),
    'scope-check':say('Required method scope checked','Portée de la méthode vérifiée'),
    'local-adapter':say('Local data adapter; approval required','Adaptateur local ; autorisation requise'),
    'bounded-run':say('Bounded experiment; approval required','Expérience bornée ; autorisation requise')
  };
  const container=$('insight-construction');container.replaceChildren();
  const status=document.createElement('p');status.className='insight-status';status.dataset.state=result.status;status.textContent=result.status==='conditional-plan'?say('CONDITIONAL PATH CONSTRUCTED','CHEMIN CONDITIONNEL CONSTRUIT'):result.status==='no-plan'?say('NO PATH WITHIN THE ORIGINAL OBLIGATIONS','AUCUN CHEMIN RESPECTANT LES OBLIGATIONS'):say('INCOMPLETE — SEARCH BUDGET EXHAUSTED','INCOMPLET — BUDGET DE RECHERCHE ÉPUISÉ');container.appendChild(status);
  if(result.steps.length){const list=document.createElement('ol');list.className='check-list';for(const step of result.steps){const item=document.createElement('li');item.textContent=names[step.step_id]||step.purpose;list.appendChild(item);}container.appendChild(list);}
  const note=document.createElement('p');note.className='fine';note.textContent=say(`${result.pending_permissions.length} pending permissions · ${result.preserved_obligations.length} original obligations · authority granted: none.`,`${result.pending_permissions.length} autorisations en attente · ${result.preserved_obligations.length} obligations initiales · autorité accordée : aucune.`);container.appendChild(note);
  pairs($('insight-claims'),[
    [say('Discovery','Découverte'),say('Exploratory — no stronger headline earned','Exploratoire — aucune percée qualifiée')],
    [say('Technical construction','Construction technique'),say('Finite local witness checked; external acceptance absent','Témoin local fini vérifié ; acceptation externe absente')],
    [say('Operational Alpha: E − U','Alpha opérationnel : E − U'),say('Unmeasured','Non mesuré')],
    [say('Retained Alpha: E+ − E','Alpha retenu : E+ − E'),say('Unmeasured; no retention admitted','Non mesuré ; aucune rétention admise')]
  ]);
  const policy=evidence.economics.policies.find(row=>row.cost_case===$('insight-cost').value&&row.price_usd===Number($('insight-price').value));
  const forecast=policy.assessment, amount=forecast.expected_economic_contribution_micro_usd;
  const expected=Number(amount.numerator)/Number(amount.denominator)/1000000;
  const cost=Object.values(policy.components_usd_per_attempt).reduce((a,b)=>a+b,0);
  pairs($('insight-economics'),[
    [say('Assumed participants / capacity','Participants supposés / capacité'),`${policy.assumed_participants} / 4`],
    [say('A: complete modeled cost per attempt','A : coût complet modélisé par tentative'),usd(cost)],
    [say('Modeled campaign contribution after defaults/refunds','Contribution de campagne modélisée après défauts/remboursements'),usd(expected)],
    [say('Required fictional prefunding including reserve','Préfinancement fictif requis, réserve incluse'),usd(forecast.required_prefunding_micro_usd/1000000)],
    [say('B: additional retention / observed benefit','B : rétention supplémentaire / bénéfice observé'),say('USD 5 screen; USD 150 retention rejected / benefit unmeasured','Filtrage de 5 USD ; rétention de 150 USD rejetée / bénéfice non mesuré')],
    [say('C: optional research, separate from delivery','C : recherche facultative, distincte de la livraison'),say('USD 0 / 100 / 500 scenarios','Scénarios de 0 / 100 / 500 USD')],
    [say('Actual profit / collections','Profit réel / encaissements'),say('Unknown / USD 0','Inconnu / 0 USD')]
  ]);
  setText('insight-transfer',say('Two fresh synthetic local processes reproduced checked paths; an ordinary library with identical information ties. Live authenticated transfer and retained-skill benefit remain unqualified.','Deux processus locaux sur de nouveaux cas synthétiques ont reproduit les chemins vérifiés ; une bibliothèque ordinaire au contenu identique les égale. Le transfert authentifié réel et le bénéfice de rétention restent non qualifiés.'));
  const sources=$('insight-sources');sources.replaceChildren();
  for(const source of evidence.sources){const p=document.createElement('p'),a=document.createElement('a');a.href=source.url;a.textContent=source.title;a.rel='noreferrer';p.appendChild(a);sources.appendChild(p);}
}
for(const id of ['insight-candidate','insight-case','insight-price','insight-cost'])$(id).addEventListener('change',renderInsight);
$('insight-seed-export').addEventListener('click',()=>download('agi-alpha-research-nova-seed.json',JSON.stringify(INSIGHT_EVIDENCE.seed,null,2)));
$('insight-plan-export').addEventListener('click',()=>download('agi-alpha-research-fusion-plan.json',JSON.stringify(INSIGHT_EVIDENCE.plan,null,2)));
$('insight-export').addEventListener('click',()=>download('agi-alpha-insight-frontier-evidence.json',JSON.stringify(INSIGHT_EVIDENCE,null,2)));
