// SPDX-License-Identifier: Apache-2.0
// Presentation evidence only. These snapshots are never accepted by a transaction,
// runtime, reuse, evaluation or recovery authorization API.
import { ACTIONS } from '../ascension-wallet/protocol.mjs';
import { unresolved } from '../ascension-wallet/client.mjs';

export const CYCLE_NODES=Object.freeze(['Insight','Nova-Seeds','MARK','Sovereign','Business','Marketplace',
  'Jobs','Agents','Nodes','Council','Value Reservoir','Architect']);
const definitions=[
  ['Insight','Nova-Seeds',['package','plan','opportunity'],[],[],['project','compile'],
    ['Review the objective and exact plan','Examiner l’objectif et le plan exact'],
    ['Local opportunity, public evidence and committed plan; no mint or execution observed.','Objectif local, preuve publique et plan engagé; aucune création ou exécution observée.'],
    ['Opportunity owner; rights and objective criteria must be explicit.','Responsable de l’objectif; droits et critères explicites requis.']],
  ['Nova-Seeds','MARK',['package','publication'],['chain'],['seal','open'],['fund','funding-target'],
    ['Review campaign prerequisites','Examiner les prérequis de la campagne'],
    ['Seed commitments and campaign snapshot only; ownership, review and funding need fresh checks.','Engagements de la semence et instantané de campagne; propriété, revue et financement à revérifier.'],
    ['Eligible original business and current seed owner; opening needs its own wallet preview.','Entreprise admissible d’origine et propriétaire actuel; ouverture avec devis distinct.']],
  ['MARK','Sovereign',[],['chain'],['open','buy','bloom','route','collect','close'],['review','refresh-review'],
    ['Open current chain inspection','Ouvrir l’inspection actuelle de la chaîne'],
    ['Campaign phase, deadlines and retained wallet intents; no coordinating authority is inferred.','Phase, échéances et intentions conservées; aucune autorité de coordination déduite.'],
    ['Read-only coordination; each wallet actor keeps their own authority.','Coordination en lecture seule; chaque acteur conserve son autorité.']],
  ['Sovereign','Business',[],['identity'],[],['mint','check-identity'],
    ['Open business identity inspection','Ouvrir l’inspection de l’identité'],
    ['Exact deployment identity/admission observation; a project or role label grants no eligibility.','Identité et admission du déploiement exact; aucun droit accordé par le nom du rôle.'],
    ['Business owner; namespace and admission authorities decide separately.','Propriétaire de l’entreprise; autorités du nom et de l’admission distinctes.']],
  ['Business','Marketplace',['plan','missions'],['chain','terms'],['route'],['launch','job-choice'],
    ['Review the committed routing inputs','Examiner les données engagées de publication'],
    ['Committed job, preposting terms and campaign only; capacity, reserve, review and owner must be rechecked.','Travail engagé, conditions préalables et campagne; capacité, réserve, revue et propriétaire à revérifier.'],
    ['Original business and current owner; routing remains a separate confirmed wallet action.','Entreprise d’origine et propriétaire actuel; publication avec confirmation distincte.']],
  ['Marketplace','Jobs',['jobIds'],['route','job'],['route'],['launch','inspect-job'],
    ['Open assignment inspection','Ouvrir l’inspection de l’attribution'],
    ['Actual route receipt and separately inspected assignment; retained job IDs alone prove no award.','Reçu de publication et attribution inspectée séparément; les identifiants seuls ne prouvent aucun gain.'],
    ['Protocol observation; the actual award determines the selected worker.','Observation du protocole; l’attribution réelle détermine l’exécutant.']],
  ['Jobs','Agents',['missions'],['job','terms','runtime'],[],['runtime','runtime-observer-key'],
    ['Review the runtime handoff','Examiner le transfert vers l’exécution'],
    ['Assignment, request and signed run evidence; posted, authorized and executed are distinct.','Attribution, demande et preuve signée; publication, autorisation et exécution sont distinctes.'],
    ['Selected worker and separately trusted controller must authorize exact bounded work.','Exécutant sélectionné et contrôleur fiable distinct; travail exact et délimité requis.']],
  ['Agents','Value Reservoir',['assets'],['runtime','reuse'],[],['continue','reuse-source'],
    ['Review exact artifact reuse','Examiner la réutilisation de l’artefact exact'],
    ['Result bytes and local rights declarations; acceptance, reuse and valuation are separate.','Octets du résultat et déclarations locales des droits; acceptation, réutilisation et valeur distinctes.'],
    ['Reviewer and rights holder; payment or a PASS cannot authorize reuse.','Réviseur et titulaire des droits; paiement ou PASS n’autorise pas la réutilisation.']],
  ['Jobs','Value Reservoir',['missions'],['settlement','ledger','reservoir'],[],['reservoir','refresh-ledger'],
    ['Open receipt-ledger reconciliation','Ouvrir le rapprochement des reçus'],
    ['Historical gross/net payouts and burn in $AGIALPHA, not USD or profit; current custody and costs are separate.','Paiements historiques bruts/nets et destruction en $AGIALPHA, sans USD ni profit; avoirs actuels et coûts distincts.'],
    ['Pinned observer reconciles canonical finality; each beneficiary keeps their own entitlement.','Observateur fiable et finalité canonique; chaque bénéficiaire conserve ses droits.']],
  ['Value Reservoir','Nova-Seeds',['linkage','assets','evaluations'],['reservoir','reuse'],[],['continue','next-cycle-title'],
    ['Review a distinct successor draft','Examiner un brouillon de cycle distinct'],
    ['Owned assets, rights and versioned continuation; claims are not cash and no grant is inherited.','Actifs détenus, droits et continuation versionnée; créances non liquides et aucune autorisation héritée.'],
    ['Rightful fund owner and parent owner; new package, review, funding and grant remain separate.','Propriétaire légitime des fonds et du parent; nouveau paquet, revue, financement et autorisation distincts.']],
  ['Value Reservoir','Marketplace',[],['chain','reservoir','ledger'],['collect','reclaim','buy','approve','route'],['reservoir','refresh-reservoir'],
    ['Open owned-funds inspection','Ouvrir l’inspection des fonds détenus'],
    ['Owned capital, campaign reserve and claims are separate; proposals neither reserve nor send funds.','Capital détenu, réserve et créances distincts; les propositions ne réservent ni n’envoient de fonds.'],
    ['Entitled holder or original business; every reclaim, approval and purchase has its own gate.','Titulaire ayant droit ou entreprise d’origine; récupération, autorisation et achat distincts.']],
  ['Agents','Nodes',['missions'],['terms'],[],['runtime','runtime-family'],
    ['Review bounded host inputs','Examiner les données délimitées du système'],
    ['Exact request and sealed terms; this browser has no authenticated host-health or live-run observation.','Demande exacte et conditions scellées; aucune observation authentifiée de santé ou d’exécution en direct.'],
    ['Host operator and controller; installed runtime, isolation and fresh scoped grant required.','Opérateur du système et contrôleur; environnement installé, isolation et autorisation nouvelle requis.']],
  ['Nodes','Agents',['missions'],['runtime'],[],['runtime','runtime-result-file'],
    ['Open signed result verification','Ouvrir la vérification du résultat signé'],
    ['Signed returned output, failure or uncertainty only; host liveness and cleanup are not inferred.','Résultat signé, échec ou incertitude; aucune activité ou remise en état du système déduite.'],
    ['Host signs observed evidence; caller pins trust separately. No automatic resume.','Le système signe ses observations; confiance fixée séparément. Aucune reprise automatique.']],
  ['Architect','Sovereign',['evaluations'],['evaluation'],[],['continue','improvement-decision'],
    ['Review the bounded adoption decision','Examiner la décision d’adoption délimitée'],
    ['Frozen comparison and explicit local decision; FAIL, inconclusive or payment never promotes a candidate.','Comparaison figée et décision locale explicite; échec, incertitude ou paiement ne promeut jamais un candidat.'],
    ['Authorized reviewer decides separately; preserve the baseline and fresh successor gates.','Réviseur autorisé distinct; conserver la référence et les nouveaux contrôles du cycle suivant.']],
  ['Sovereign','Architect',['evaluations','missions'],['evaluation'],[],['continue','evaluation-freeze-file'],
    ['Open frozen comparison inspection','Ouvrir l’inspection de la comparaison figée'],
    ['Original baseline, criterion and measured outcomes; missing costs and holdout qualification remain unknown.','Référence, critère et mesures d’origine; coûts manquants et qualification indépendante restent inconnus.'],
    ['Operator supplies authorized artifacts; evaluator must declare scope and custody.','L’opérateur fournit les artefacts autorisés; l’évaluateur déclare portée et garde.']],
  ['Architect','Insight',['opportunity','evaluations','linkage'],['evaluation'],[],['continue','next-cycle-evidence'],
    ['Review findings for the next objective','Examiner les conclusions pour le prochain objectif'],
    ['Versioned findings and unresolved assumptions; negative findings remain useful, estimates are not spendable.','Conclusions versionnées et hypothèses ouvertes; résultats négatifs utiles, estimations non dépensables.'],
    ['Opportunity owner reviews the original evidence and its uncertainty before changing the objective.','Le responsable examine les preuves originales et leur incertitude avant de changer l’objectif.']],
  ['Insight','Architect',['opportunity','plan','evaluations'],[],[],['continue','evaluation-freeze-file'],
    ['Review preregistered acceptance conditions','Examiner les critères préenregistrés'],
    ['Local objective and fixed comparison proposal; a planned evaluation is not an executed result.','Objectif local et proposition de comparaison fixe; une évaluation prévue n’est pas un résultat exécuté.'],
    ['Opportunity owner proposes; reviewer controls the actual comparison decision.','Le responsable propose; le réviseur contrôle la décision réelle de comparaison.']],
  ['Council','Sovereign',['evaluations'],['chain','job','settlement','evaluation'],['attest','validate'],['review','refresh-review'],
    ['Open scoped review inspection','Ouvrir l’inspection de la revue délimitée'],
    ['Seed review, job acceptance, local adoption and spending remain distinct; no universal Council approval.','Revue de semence, acceptation du travail, adoption locale et dépenses distinctes; aucune approbation universelle.'],
    ['Each eligible validator, assigned committee, reviewer or fund owner acts only in their own scope.','Chaque validateur, comité, réviseur ou propriétaire agit uniquement dans sa portée.']]
];
export const CYCLE_EDGES=Object.freeze(definitions.map((entry,index)=>Object.freeze({
  id:`E${String(index+1).padStart(2,'0')}`,from:entry[0],to:entry[1],local:entry[2],observations:entry[3],
  journal:entry[4],target:entry[5],label:entry[6],scope:entry[7],actor:entry[8]
})));
const snapshots=new WeakMap();
const json=value=>JSON.stringify(value,(_,part)=>typeof part==='bigint'?String(part):part);
const copy=value=>JSON.parse(json(value));
const pick=(value,keys)=>Object.fromEntries(keys.filter(key=>value?.[key]!==undefined).map(key=>[key,value[key]]));
function binding(flow) {
  return {projectId:flow.project?.projectId,cycleId:flow.currentCycle?.cycleId,
    package:flow.package,packageIdentity:json({capsule:flow.package?.capsuleHash,
      plan:flow.package?.plan?.planRoot,evidence:flow.package?.evidenceHash,deployment:flow.package?.deployment}),seedId:flow.seedId??null,client:flow.client,sessionClient:flow.session?.client,
    epoch:flow.client?.epoch,account:flow.client?.account??null,profile:json(flow.client?.profile??null)};
}
function sameContext(left,right) {
  return Object.keys(left).every(key=>left[key]===right[key]);
}
export function invalidateEdgeEvidence(flow,kind) {
  const entries=snapshots.get(flow);
  if(entries)for(const [name,entry] of entries)if(!kind||kind===name)entry.invalidated=true;
}
// Call only after the existing verifier succeeds. Retain the captured source as
// an observation, never as an authority token. Restored JSON cannot populate it.
export function rememberEdgeEvidence(flow,kind,record,{epoch=flow.client?.epoch,now=Date.now()}={}) {
  if(!flow.project||flow.client?.epoch!==epoch||flow.session&&flow.session.client!==flow.client)return;
  const entries=snapshots.get(flow)||new Map();
  entries.set(kind,{binding:binding(flow),record:copy(record),observedAt:now,invalidated:false});
  snapshots.set(flow,entries);
}
export async function readEdgeEvidence(flow,kind,read) {
  invalidateEdgeEvidence(flow,kind);
  const context=binding(flow),record=await read();
  if(sameContext(context,binding(flow)))rememberEdgeEvidence(flow,kind,record);
  return record;
}
function observation(flow,kind,now) {
  const entry=snapshots.get(flow)?.get(kind);
  if(!entry)return null;
  const fresh=!entry.invalidated&&sameContext(entry.binding,binding(flow))&&
    now>=entry.observedAt&&now-entry.observedAt<120000;
  return {kind,state:fresh?'observed':'stale',observedAt:new Date(entry.observedAt).toISOString(),
    context:pick(entry.binding,['projectId','cycleId','seedId','epoch','account','profile']),
    scope:'Snapshot only; refresh before any consequential action.',record:copy(entry.record)};
}
const recordKinds={E05:['preposting'],E07:['preposting','runtime-run'],E08:['runtime-run','settlement'],
  E09:['settlement'],E10:['rights'],E12:['preposting'],E13:['runtime-run'],
  E14:['evaluation'],E15:['evaluation','runtime-run'],E16:['evaluation'],E17:['evaluation'],
  E18:['settlement','evaluation']};
const stateLabels={
  unknown:['Unresolved wallet intent; effects unknown','Intention du portefeuille non résolue; effets inconnus'],
  observed:['Observed snapshot; refresh before acting','Instantané observé; actualiser avant toute action'],
  stale:['Stale or changed context; recheck required','Périmé ou contexte modifié; revérification requise'],
  'historical-unverified':['Historical evidence; current trust not established','Preuve historique; confiance actuelle non établie'],
  local:['Local preparation; no external outcome established','Préparation locale; aucun résultat externe établi'],
  'not-observed':['Not observed','Non observé']
};
function matchingJournal(record,flow,cycle) {
  // The shared wallet journal may contain several projects. Retain only intents
  // whose exact seed, package or known job belongs to this selected cycle.
  const args=record.args;
  if(!Array.isArray(args))return false;
  if(record.action==='seal')return !!flow.package&&args[0]===flow.package.capsuleHash&&args[1]===flow.package.plan.planRoot;
  return (ACTIONS[record.action]?.fields||[]).some((field,index)=>
    field.key==='id'&&flow.seedId!==null&&String(args[index])===String(flow.seedId)||
    field.key==='job'&&(cycle.jobIds||[]).includes(String(args[index])));
}
export function describeCycleEdges(flow,{language='en',now=Date.now()}={}) {
  const lang=language==='fr'?1:0,cycle=flow.currentCycle,project=flow.project;
  if(!cycle||!project)return [];
  const local={package:flow.package?pick(flow.package,['schema','deployment','capsuleHash','capsuleByteHash','evidenceHash','parent']):null,
    plan:flow.package?.plan??null,publication:flow.publication??null,jobIds:cycle.jobIds,
    missions:cycle.missions,assets:cycle.assets,evaluations:cycle.evaluations,linkage:cycle.linkage,
    opportunity:project.opportunity};
  const useful=value=>value!==null&&value!==undefined&&(typeof value!=='object'||Object.keys(value).length>0);
  const pending=(flow.client?.history||[]).filter(unresolved);
  return CYCLE_EDGES.map(edge=>{
    const observed=edge.observations.map(kind=>observation(flow,kind,now)).filter(Boolean);
    const retained=(cycle.signedRecords||[]).filter(record=>(recordKinds[edge.id]||[]).includes(record.kind));
    const journal=(cycle.journal?.transactions||[]).filter(record=>edge.journal.includes(record.action)&&matchingJournal(record,flow,cycle));
    const retainedKeys=['publication','jobIds','missions','assets','evaluations','linkage'];
    const localRecords=Object.fromEntries(edge.local.filter(key=>!retainedKeys.includes(key)&&useful(local[key])).map(key=>[key,local[key]]));
    const retainedModel=Object.fromEntries(edge.local.filter(key=>retainedKeys.includes(key)&&useful(local[key])).map(key=>[key,local[key]]));
    const state=pending.length?'unknown':observed.some(record=>record.state==='observed')?'observed':observed.length?'stale':
      retained.length||journal.length||Object.keys(retainedModel).length?'historical-unverified':Object.keys(localRecords).length?'local':'not-observed';
    let [step,target]=edge.target,label=edge.label[lang],reason=edge.actor[lang];
    // Navigation itself is safe. Never shortcut the actual control's validation,
    // public disclosure, rights, wallet, signing, execution or adoption gates.
    if(pending.length){step='resume';target='reconcile-hash';label=lang?'Examiner l’intention non résolue':'Inspect the unresolved intent';
      reason=lang?'Effet inconnu; rapprocher l’intention originale avant toute nouvelle action.':'Unknown effect; reconcile the original intent before any new action.';}
    else if(!flow.package&&![ 'E01','E04' ].includes(edge.id)){
      step='project';target='title';label=lang?'Examiner ou récupérer le projet exact':'Review or recover the exact project';
      reason=lang?'Aucun paquet actuel; préparer ou récupérer les engagements exacts avant de continuer.':'No current package; prepare or recover exact commitments before continuing.';
    }else if(['E02','E03','E05','E06','E09','E11','E18'].includes(edge.id)&&!flow.seedId){
      step='resume';target='existing-seed';label=lang?'Ouvrir l’inspection de la semence':'Open seed inspection';
      reason=lang?'Aucune semence observée; ne pas déduire une création ou un financement.':'No observed seed; do not infer minting or funding.';
    }
    const records={context:{projectId:project.projectId,cycleId:cycle.cycleId,ordinal:cycle.ordinal,
      seedId:flow.seedId??null,packageCommitments:cycle.commitments},local:localRecords,observations:observed,
      historical:{trust:'historical-unverified',signedRecords:retained,journal,model:retainedModel},
      pendingIntents:pending,
      missingObservations:edge.observations.filter(kind=>!observed.some(record=>record.kind===kind&&record.state==='observed'))};
    return {id:edge.id,from:edge.from,to:edge.to,state,stateLabel:stateLabels[state][lang],records,
      scope:edge.scope[lang],actor:edge.actor[lang],action:{step,target,label,reason},
      boundary:lang?'Navigation uniquement. Aucune signature, dépense, exécution, publication ou adoption déclenchée. Les contrôles existants exigent leurs propres vérifications et consentements.':'Navigation only. No signing, spending, execution, publication or adoption is triggered. Existing controls require their own checks and consent.'};
  });
}
export const edgeRecordJSON=value=>JSON.stringify(value,(_,part)=>typeof part==='bigint'?String(part):part,2);
