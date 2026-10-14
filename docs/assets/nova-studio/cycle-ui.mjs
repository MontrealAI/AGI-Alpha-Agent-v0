// SPDX-License-Identifier: Apache-2.0
import { tokens, units, uint } from '../ascension-wallet/protocol.mjs';
import { strictJSON, exportKit } from './package.mjs';
import { resultCommitments } from './runtime.mjs';

const $=id=>document.getElementById(id), encoder=new TextEncoder();
const nodes=['Insight','Nova-Seeds','MARK','Sovereign','Business','Marketplace','Jobs','Agents','Nodes','Council','Value Reservoir','Architect'];
const edges=[['Insight','Nova-Seeds'],['Nova-Seeds','MARK'],['MARK','Sovereign'],['Sovereign','Business'],
  ['Business','Marketplace'],['Marketplace','Jobs'],['Jobs','Agents'],['Agents','Value Reservoir'],
  ['Jobs','Value Reservoir'],['Value Reservoir','Nova-Seeds'],['Value Reservoir','Marketplace'],
  ['Agents','Nodes'],['Nodes','Agents'],['Architect','Sovereign'],['Sovereign','Architect'],
  ['Architect','Insight'],['Insight','Architect'],['Council','Sovereign']];
let handlers=null;
async function readFile(id,limit=2000000) {
  const file=$(id).files[0];
  if (!file || file.size>limit) throw Error('Choose a supported bounded JSON file / Choisissez un fichier JSON de taille permise.');
  return file.text();
}
function line(label,value) {
  const p=document.createElement('p'), strong=document.createElement('strong');
  strong.textContent=label+': ';p.append(strong,document.createTextNode(String(value)));return p;
}
function historicalResult(record,project,cycle) {
  // Recovery preserves opaque signed bytes, including records from other runtime
  // versions. A readable local checksum is not current signature verification.
  const result=strictJSON(record.originalText);
  const matches=(value,pattern)=>typeof value==='string'&&pattern.test(value);
  if(result?.schema!=='agialpha.ascension.studio-result.v1' || result.project_id!==project.projectId ||
      result.cycle_id!==cycle.cycleId || !matches(result.artifact_keccak256,/^0x[0-9a-f]{64}$/) ||
      !matches(result.artifact_sha256,/^0x[0-9a-f]{64}$/) || !matches(result.delivery?.digest,/^[0-9a-f]{64}$/) ||
      !matches(result.execution_binding?.body?.market_job_id,/^[1-9][0-9]{0,77}$/) ||
      !['PASS','FAIL','RETAIN_INCUMBENT','INSUFFICIENT_EVIDENCE','NOT_APPLICABLE'].includes(result.candidate_verdict))return null;
  return result;
}
function workSpec(flow,language) {
  const family=$('runtime-family').value;
  const number=id=>{const raw=$(id).value;if(!/^-?(0|[1-9]\d*)$/.test(raw))throw Error('Use exact whole numbers / Utilisez des entiers exacts.');const value=Number(raw);if(!Number.isSafeInteger(value))throw Error('Integer exceeds supported range.');return value;};
  const inputs=family==='public-data'?{csv:$('runtime-csv').value,unit:$('runtime-unit').value}:{
    coefficients:$('numerical-coefficients').value.split(',').map(v=>{const value=Number(v.trim());if(!v.trim()||!Number.isSafeInteger(value))throw Error('Use comma-separated integer coefficients.');return value;}),
    lower:number('numerical-lower'),upper:number('numerical-upper'),steps:number('numerical-steps'),tolerancePpm:number('numerical-tolerance')};
  return {schema:'successor-workbench/v1',family,name:'Nova-Seed bounded work',language,owner:flow.project.projectId,
    rights:{dataClass:$('runtime-rights').value,source:$('runtime-source').value,license:$('runtime-license').value},reviewMinutes:10,inputs};
}
export function installCycleUI(options) {
  handlers=options;
  const {getFlow,run,download,status,go,packageView,setNativeResult,getLanguage}=options;
  const act=(id,fn)=>$(id).addEventListener('click',()=>run(fn));
  const key=()=>$('runtime-observer-key').value.trim();
  const algorithm=document.createElement('label');algorithm.textContent='Result commitment / Empreinte du résultat';
  const select=document.createElement('select');select.id='result-algorithm';
  for(const [value,label] of [['sha256','SHA-256 · existing Studio delivery'],['keccak256','Keccak-256 · native SUCCESSOR delivery']]){const option=document.createElement('option');option.value=value;option.textContent=label;select.append(option);}
  algorithm.append(select);$('result-file').closest('label').after(algorithm);
  $('runtime-family').addEventListener('change',()=>{
    $('runtime-data-fields').hidden=$('runtime-family').value!=='public-data';
    $('runtime-numerical-fields').hidden=$('runtime-family').value!=='numerical';
  });
  act('export-runtime-request',async()=>{
    const flow=getFlow();await flow.ensureProject();
    const request=await flow.runtimeRequest(Number($('job-choice').value||0),workSpec(flow,getLanguage()));
    download('nova-executor-request.json',request);
    $('runtime-request-state').textContent='Request frozen. Import it in the installed local operator desk before routing. / Demande figée. Importez-la avant publication.';
    status('Exact executor request prepared; no execution or wallet authority granted.');
  });
  act('import-runtime-terms',async()=>{
    await getFlow().importTerms(Number($('job-choice').value||0),await readFile('terms-file'),key());
    $('runtime-request-state').textContent='Signed preposting terms verified against the current chain. / Conditions signées vérifiées sur la chaîne.';
    status('Preposting terms verified. The existing launch control still requires a separate wallet confirmation.');
  });
  act('import-runtime-result',async()=>{
    const checked=await getFlow().importRuntimeResult(await readFile('runtime-result-file'),key());
    setNativeResult(checked.hashes.keccak256,'keccak256');
    $('onchain-job').value=String(checked.binding.market_job_id);
    $('native-run-status').textContent=`${checked.result.candidate_verdict} · native execution evidence verified / preuve native vérifiée. Acceptance and payment remain separate.`;
    $('native-run-details').textContent=JSON.stringify({project:checked.result.project_id,cycle:checked.result.cycle_id,
      worker:checked.binding.selected_worker,job:checked.binding.market_job_id,hashes:checked.hashes,
      candidateVerdict:checked.result.candidate_verdict,summary:checked.artifact.report.result.summary,
      authority:'not_granted',providerSpend:'No paid model used',hostCost:'unmeasured'},null,2);
    status('Exact native artifact verified. Inspect its contents, publish only with consent, and use the existing worker delivery and reviewer controls.');
  });
  act('export-native-artifact',async()=>{
    const result=getFlow().runtimeResult;if(!result)throw Error('Verify a native result first.');
    download('nova-exact-result.json',encoder.encode(result.artifact_utf8),true);
  });
  act('publish-native-artifact',async()=>{
    const flow=getFlow(),result=flow.runtimeResult;if(!result||!$('runtime-public-consent').checked)throw Error('Verify the native file and approve its public disclosure first.');
    try{
      const bytes=encoder.encode(result.artifact_utf8),published=await flow.storage.publishBytes(bytes,'nova-exact-result.json',$('runtime-storage-token').value);
      const retrieved=await flow.storage.retrieveBytes(published.uri,undefined,2000000),hashes=await resultCommitments(retrieved.bytes);
      if(hashes.keccak256!==result.artifact_keccak256||hashes.sha256!==result.artifact_sha256)throw Error('Published bytes changed.');
      $('result-uri').value=published.uri;setNativeResult(hashes.keccak256,'keccak256');
      status('Exact public result verified. Prepare delivery separately in Launch & follow.');
    }finally{$('runtime-storage-token').value='';}
  });
  act('import-runtime-settlement',async()=>{
    const settlement=await getFlow().importRuntimeSettlement(await readFile('settlement-file'),key());
    $('native-settlement-status').textContent=`${settlement.job_acceptance} · ${settlement.settlement_status} · candidate ${settlement.candidate_verdict} · no adoption or authority granted`;
    status('Signed settlement reconciled with finalized chain receipt, exact result, payouts and burn.');
  });
  act('import-evaluation-freeze',async()=>{
    const freeze=await getFlow().importEvaluationFreeze(await readFile('evaluation-freeze-file'),key());
    $('evaluation-status').textContent='Frozen before this fresh result; no execution authority / Figé avant le résultat; sans autorisation';
    $('evaluation-details').textContent=JSON.stringify(freeze.body,null,2);
    status('Frozen comparison retained. The local operator must separately authorize and execute the fresh committed work.');
  });
  act('import-evaluation',async()=>{
    const checked=await getFlow().importEvaluation(await readFile('evaluation-freeze-file'),await readFile('evaluation-report-file'),key());
    $('evaluation-status').textContent=`${checked.outcome} · fixed numerical quality only / qualité numérique délimitée`;
    $('evaluation-details').textContent=JSON.stringify(checked.report,null,2);
    status('Original frozen comparison verified. Review its scope, unknown costs and baseline before recording a decision.');
  });
  act('adopt-candidate',async()=>{
    const decision=await getFlow().decideImprovement($('improvement-decision').value,$('evaluation-reviewer').value,$('evaluation-rationale').value);
    $('evaluation-status').textContent=`${decision.decision.decision} · ${decision.evidence.effectiveVerdict} · no execution authority / sans autorisation`;
    status('Reviewed decision preserved. Baseline and every original outcome remain in project history.');
  });
  act('authorize-artifact-reuse',async()=>{
    const date=$('reuse-valid-until').value;
    if(!date)throw Error('Choose a UTC rights review expiry within the next 24 hours.');
    const selected=await getFlow().authorizeArtifactReuse({reviewer:$('reuse-reviewer').value,rationale:$('reuse-rationale').value,
      license:$('reuse-license').value,validUntil:new Date(date+'Z').toISOString()},
      {artifactHash:$('reuse-source').value,observerKey:key()});
    $('reuse-status').textContent='Exact accepted recipe selected; local rights declaration / Recette acceptée; déclaration locale';
    $('reuse-details').textContent=JSON.stringify(selected.selection,null,2);
    const inherited=selected.selection.inherited;
    $('runtime-family').value='numerical';$('runtime-data-fields').hidden=true;$('runtime-numerical-fields').hidden=false;
    for(const [id,value] of [['numerical-lower',inherited.lower],['numerical-upper',inherited.upper],['numerical-steps',inherited.steps],['numerical-tolerance',inherited.tolerancePpm],['runtime-license',selected.selection.license]])$(id).value=String(value);
    status('The next request will inherit these exact recipe parameters and require fresh coefficients and a new execution grant.');
  });
  act('refresh-reservoir',async()=>{
    $('reservoir-summary').replaceChildren();$('reservoir-details').textContent='—';
    $('reservoir-status').textContent='Refreshing / Actualisation…';
    try{
      const value=await getFlow().reservoir();
      const amount=raw=>raw===null||raw===undefined?'Unavailable / Indisponible':`${tokens(raw)} $AGIALPHA`;
      $('reservoir-status').textContent=value.fresh?'Current chain observation / Observation actuelle':'Unavailable; refresh required / Indisponible';
      $('reservoir-summary').append(line('Wallet-owned / Détenu',amount(value.walletBalance)),
        line('Available for a proposal / Disponible pour proposition',amount(value.walletBalance===null?null:value.availableForProposal)),
        line('Campaign backing, separate / Réserve distincte',amount(value.campaign?.reserve)),
        line('Your claim / Votre créance',value.claim?.amount?`${tokens(value.claim.amount)} $AGIALPHA · not spendable until exit / après sortie`:value.claim?'Contingent / Conditionnelle':'Unavailable / Indisponible'),
        line('Host, review, storage and gas costs / Coûts','Unknown until measured; no profit inferred / Inconnus, aucun profit déduit'));
      $('reservoir-details').textContent=JSON.stringify(value,null,2);
    }catch(error){$('reservoir-status').textContent='Unavailable; no zero balance inferred / Indisponible; aucun solde nul déduit';throw error;}
  });
  act('refresh-ledger',async()=>{
    $('ledger-summary').replaceChildren();$('ledger-details').textContent='—';$('ledger-status').textContent='Rechecking original receipts / Vérification des reçus…';
    try{
      const value=await getFlow().ledger(key());
      $('ledger-status').textContent=`${value.settlements.length} reconciled settlements / règlements rapprochés`;
      for(const recipient of value.recipients)$('ledger-summary').append(line(recipient.recipient,`${tokens(recipient.grossPayout)} gross / brut · ${tokens(recipient.burned)} burned / brûlé · ${tokens(recipient.netPayout)} net $AGIALPHA`));
      $('ledger-summary').append(line('Current wallet funds / Solde actuel','Refresh assets separately; historical flows are not added / Actualiser séparément'));
      $('ledger-details').textContent=JSON.stringify(value,null,2);
      status('Canonical finalized receipts reconciled. Recipient payouts and campaign refunds remain separate; no profit inferred.');
    }catch(error){$('ledger-status').textContent='Unavailable; no historical balance inferred / Indisponible';throw error;}
  });
  const proposalInput=()=>({amount:units($('reinvestment-amount').value).toString(),lotCount:uint($('reinvestment-lots').value,32).toString(),rationale:$('reinvestment-rationale').value,risk:$('reinvestment-risk').value});
  act('review-reinvestment',async()=>{
    $('reinvestment-details').textContent='—';
    const proposal=await getFlow().reinvestmentProposal(proposalInput());
    $('reinvestment-details').textContent=JSON.stringify(proposal,null,2);
    $('reinvestment-status').textContent='Proposal only; no funds reserved or sent / Proposition; aucun fonds réservé ou envoyé';
    status('Current owned balance and destination quote checked. Every funding action still requires its own preview and confirmation.');
  });
  act('use-reinvestment',async()=>{
    const input=proposalInput();await getFlow().reinvestmentProposal(input);
    $('lot-count').value=input.lotCount;$('max-cost').value=tokens(input.amount);
    go('fund');status('Quote refreshed and funding form filled. Prepare approval and purchase separately.');
  });
  act('next-cycle',async()=>{
    const flow=getFlow();if(!$('reuse-ack').checked)throw Error('Review baseline retention and fresh authorization first.');
    const job=flow.package?.plan.jobs[Number($('job-choice').value||0)]?.spec;
    if(!job)throw Error('Recover the current exact plan first.');
    try{
      await flow.nextCycle({title:$('next-cycle-title').value,description:'Deliberately prepared successor; no authority inherited.',
        jobs:[{...job,goal:$('next-cycle-goal').value}],evidence:$('next-cycle-evidence').value},$('next-cycle-passphrase').value);
      packageView();go('protect');status('New exact cycle prepared. Previous history is preserved. Export both the current recovery kit and full encrypted project.');
      $('native-run-status').textContent='New mission; no execution yet / Nouvelle mission; aucune exécution';
      $('native-settlement-status').textContent='';$('native-run-details').textContent='—';
    }finally{$('next-cycle-passphrase').value='';}
  });
  act('export-project',async()=>{
    try{download('Nova-Seed-Full-Project.encrypted.json',await getFlow().projectKit($('project-passphrase').value));status('Full private project encrypted and exported. Retain each capsule passphrase separately.');}
    finally{$('project-passphrase').value='';}
  });
  act('restore-project',async()=>{
    try{
      await getFlow().restoreProject(await readFile('project-file',12000000),$('project-restore-passphrase').value,$('project-capsule-passphrase').value);
      packageView();$('runtime-observer-key').value='';$('native-run-details').textContent='—';$('native-settlement-status').textContent='';
      $('native-run-status').textContent='Historical records restored; pin current trust and refresh / Historique restauré; vérifier la confiance';
      status('Linked project restored. No execution grant, adoption, wallet signature or payment was replayed.');
    }finally{$('project-restore-passphrase').value='';$('project-capsule-passphrase').value='';}
  });
}
export function renderCycleUI(flow) {
  if(!handlers||!flow?.project)return;
  const project=flow.project,cycle=flow.currentCycle;
  $('project-context').textContent=`${project.title} · ${project.projectId} · Cycle ${cycle.ordinal} / ${project.cycles.length}`;
  $('cycle-history').replaceChildren();
  for(const item of project.cycles){
    const details=document.createElement('details'),summary=document.createElement('summary');
    summary.textContent=`Cycle ${item.ordinal} · ${item.seedId?`Nova-Seed #${item.seedId}`:'Local preparation / Préparation locale'} · ${item.signedRecords.length} retained records / preuves conservées`;
    const record=document.createElement('pre');record.tabIndex=0;record.textContent=JSON.stringify({cycleId:item.cycleId,parent:item.linkage,commitments:item.commitments,
      jobs:item.jobIds,records:item.signedRecords.map(r=>({kind:r.kind,sha256:r.sha256,trust:r.trust})),evaluations:item.evaluations},null,2);
    details.append(summary,record);
    if(item.package){const button=document.createElement('button');button.textContent='Export original cycle kit / Exporter ce cycle';button.addEventListener('click',()=>handlers.run(async()=>handlers.download(`Nova-Cycle-${item.ordinal}.json`,await exportKit(item.package,item))));details.append(button);}
    $('cycle-history').append(details);
  }
  $('candidate-summary').replaceChildren();
  const selectedSource=$('reuse-source').value;
  $('reuse-source').replaceChildren();
  const empty=document.createElement('option');empty.value='';empty.textContent='Choose a retained result / Choisir un résultat';$('reuse-source').append(empty);
  for(const item of project.cycles)for(const record of item.signedRecords.filter(r=>r.kind==='runtime-run')){
    const result=historicalResult(record,project,item);
    if(!result || !item.signedRecords.some(r=>r.kind==='settlement'&&strictJSON(r.originalText)?.settlement?.delivery_digest===result.delivery.digest))continue;
    const option=document.createElement('option');option.value=result.artifact_keccak256;
    option.textContent=`Cycle ${item.ordinal} · job ${result.execution_binding.body.market_job_id} · ${result.artifact_sha256.slice(0,18)}…`;
    $('reuse-source').append(option);
  }
  $('reuse-source').value=selectedSource||flow.runtimeResult?.artifact_keccak256||'';
  if(!$('reuse-valid-until').value)$('reuse-valid-until').value=new Date(Date.now()+3600000).toISOString().slice(0,16);
  const results=cycle.signedRecords.filter(r=>r.kind==='runtime-run');
  for(const record of results){
    const result=historicalResult(record,project,cycle);
    $('candidate-summary').append(line('Historical report · unverified / Rapport historique · non vérifié',
      result?result.candidate_verdict:'Unrecognized historical record retained / Document historique non reconnu conservé'),
      line('Adoption / Adoption','Not granted by payment or recovery / Non accordée par paiement ou récupération'));
  }
  if(!results.length)$('candidate-summary').append(line('Evaluation / Évaluation','No execution report retained / Aucun rapport conservé'));
  for(const evaluation of cycle.evaluations)$('candidate-summary').append(line('Frozen comparison / Comparaison figée',`${evaluation.evidence?.effectiveVerdict||'Awaiting evidence'} · ${evaluation.decision?.decision||'Decision pending'} · costs unqualified / coûts non qualifiés`));
  $('cycle-graph').replaceChildren();
  const table=document.createElement('table'),caption=document.createElement('caption');caption.textContent='12 components · 18 original directions / 12 composants · 18 directions';
  const head=document.createElement('thead'),tr=document.createElement('tr');
  for(const label of ['Component / Composant','Evidence and next actor / Preuve et acteur']){const th=document.createElement('th');th.scope='col';th.textContent=label;tr.append(th);}head.append(tr);table.append(caption,head);
  const body=document.createElement('tbody');
  for(const node of nodes){const row=document.createElement('tr'),name=document.createElement('th'),value=document.createElement('td');name.scope='row';name.textContent=node;value.textContent=graphState(node,flow);row.append(name,value);body.append(row);}table.append(body);$('cycle-graph').append(table);
  const list=document.createElement('ul');for(const [from,to] of edges){const item=document.createElement('li');item.textContent=`${from} → ${to} · inspect evidence / examiner les preuves`;list.append(item);}$('cycle-graph').append(list);
}
function graphState(node,flow) {
  const states={Insight:'Declared objective; inspect assumptions / Objectif déclaré',
    'Nova-Seeds':flow.seedId?`Seed #${flow.seedId}; refresh current owner / actualiser`:'Exact local package; mint separately / Paquet local',
    MARK:flow.observation?'Campaign observed; refresh before funding / Actualiser avant financement':'Refresh campaign / Actualiser la campagne',
    Sovereign:'Separate owner and controller decisions / Décisions distinctes',Business:'Wallet identity and admission require live reads / Vérifier l’identité',
    Marketplace:'Exact deployment-bound market / Marché lié au déploiement',Jobs:flow.jobIds.length?'Inspect each assignment and deadline / Examiner les attributions':'No routed job observed / Aucun travail observé',
    Agents:flow.runtimeResult?'Pinned native execution evidence; no new authority / Preuve native':'Connect installed runtime and controller / Connecter le contrôleur',
    Nodes:'Operator owns host health and isolation / L’opérateur contrôle l’environnement',Council:'Seed, result and adoption decisions remain distinct / Revues distinctes',
    'Value Reservoir':'Refresh owned capital, claims and obligations / Actualiser actifs et obligations',Architect:'Candidate verdict is separate from adoption / Verdict distinct de l’adoption'};
  return states[node];
}
