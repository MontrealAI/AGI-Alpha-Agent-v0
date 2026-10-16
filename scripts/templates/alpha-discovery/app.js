// SPDX-License-Identifier: Apache-2.0
const $ = id => document.getElementById(id);
let language='en', brief=null, revision=0, busy=false, importEpoch=0, step=0, expert=false;
const words={mission:['Your mission','Votre mission'],baseline:['Current baseline: what you do today','Référence actuelle : votre pratique'],alternative:['Best credible alternative','Meilleure alternative crédible'],candidate:['Candidate hypothesis to investigate','Hypothèse candidate à explorer'],changed:['What changed, and why now?','Qu’est-ce qui a changé, et pourquoi maintenant ?'],rights:['Input rights and source scope','Droits et périmètre des données'],kind:['Evidence type','Type de preuve'],claim:['Finding or lesson (including failed attempts)','Constat ou leçon (y compris les échecs)'],reference:['Source, date, conditions and limitations','Source, date, conditions et limites'],basis:['Evidence basis','Base de preuve'],supports:['Supports which option or change?','Quelle option ou quel changement ?'],name:['Name','Nom'],status:['Constraint status','État de la contrainte'],unit:['Common unit','Unité commune'],direction:['Better means','Amélioration souhaitée'],minimumGain:['Minimum gain over BOTH comparators (0 = no worse)','Gain minimal sur les DEUX références (0 = non inférieur)'],value:['Value (blank means unknown)','Valeur (vide = inconnue)'],benefit:['Mission benefit','Bénéfice pour la mission'],cost:['Total cost','Coût total'],proof:['Proof and qualification burden','Effort de preuve et qualification'],risk:['Residual risk','Risque résiduel'],human:['Human burden','Effort humain']};
const options={kind:[['research','Research','Recherche'],['expertise','Expertise','Expertise'],['experiment','Experiment / failure','Expérience / échec'],['lesson','Lesson','Leçon'],['change','What changed','Changement']],basis:[['unknown','Unknown','Inconnu'],['illustrative','Illustrative assumption','Hypothèse illustrative'],['supplied-report','Supplied report, unverified','Rapport fourni, non vérifié']],supports:[['candidate','Candidate','Candidate'],['baseline','Baseline','Référence'],['alternative','Alternative','Alternative'],['change','What changed','Changement']],status:[['unknown','Unknown','Inconnu'],['reported-pass','Reported pass, unverified','Réussite déclarée, non vérifiée'],['reported-fail','Reported failure','Échec déclaré']],direction:[['higher','Higher','Plus élevé'],['lower','Lower','Plus faible']]};
function translate(){document.documentElement.lang=language;$('language').textContent=language==='en'?'Français':'English';document.querySelectorAll('[data-en]').forEach(el=>el.textContent=el.dataset[language]);}
function say(en,fr){return language==='en'?en:fr;}
function bilingual(el,en,fr){el.dataset.en=en;el.dataset.fr=fr;el.textContent=say(en,fr);return el;}
function node(tag,parent,en,fr){const el=document.createElement(tag);if(en!==undefined)bilingual(el,en,fr);parent.append(el);return el;}
function field(parent,key,value,id,choices){
  const label=node('label',parent,...(words[key]||[key,key]));label.htmlFor=id;
  const el=document.createElement(choices?'select':['claim','reference','changed','mission'].includes(key)?'textarea':'input');el.id=id;el.dataset.key=key;
  if(choices)for(const [value,en,fr]of choices){const option=node('option',el,en,fr);option.value=value;}
  else {el.maxLength=['name','unit'].includes(key)?160:2000;if(['value','minimumGain'].includes(key))el.inputMode='numeric';}
  el.value=value??'';parent.append(el);return el;
}
function removeButton(box,container,prefix,minimum=0){
  const button=node('button',box,'Remove entry','Retirer l’entrée');button.type='button';button.addEventListener('click',()=>{if(container.children.length<=minimum)return;box.remove();[...container.children].forEach((entry,index)=>{entry.querySelectorAll('[id]').forEach(el=>{const old=el.id;el.id=old.replace(new RegExp(`^${prefix}-\\d+-`),`${prefix}-${index}-`);const label=[...entry.querySelectorAll('label')].find(label=>label.htmlFor===old);if(label)label.htmlFor=el.id;});});invalidate();});
}
function evidenceRow(row,index){
  const box=node('fieldset',$('ledger'));box.className='entry';node('legend',box,`Evidence ${index+1}`,`Preuve ${index+1}`);
  for(const key of ['kind','claim','reference','basis'])field(box,key,row[key],`e-${index}-${key}`,key==='basis'?options.basis.filter(x=>x[0]!=='unknown'):options[key]);
  const support=node('fieldset',box);support.id=`e-${index}-supports`;node('legend',support,...words.supports);for(const [value,en,fr] of options.supports){const label=node('label',support);label.className='support-choice';const check=node('input',label);check.type='checkbox';check.value=value;check.id=`e-${index}-support-${value}`;check.checked=row.supports.includes(value);label.htmlFor=check.id;node('span',label,en,fr);}
  removeButton(box,$('ledger'),'e');

}
function constraintRow(row,index){const box=node('fieldset',$('constraints'));box.className='entry';node('legend',box,`Constraint ${index+1}`,`Contrainte ${index+1}`);for(const key of ['name','status','reference'])field(box,key,row[key],`c-${index}-${key}`,options[key]);removeButton(box,$('constraints'),'c',1);}
function fill(input){
  for(const id of ['framing','alternatives','ledger','constraints','metrics'])$(id).replaceChildren();
  for(const key of ['mission','baseline','alternative','candidate','changed','rights'])field($(key==='mission'||key==='changed'?'framing':'alternatives'),key,input[key],key);
  input.evidence.forEach(evidenceRow);input.constraints.forEach(constraintRow);
  input.metrics.forEach((row,index)=>{
    const box=node('details',$('metrics'));box.className='metric entry';box.dataset.category=row.category;
    node('summary',box,...words[row.category]);
    for(const key of ['name','unit','direction','minimumGain'])field(box,key,row[key],`m-${index}-${key}`,options[key]);
    const grid=node('div',box);grid.className='grid';
    for(const role of ['baseline','alternative','candidate']){const group=node('fieldset',grid);node('legend',group,...words[role]);for(const key of ['value','basis','reference'])field(group,key,row[role][key],`m-${index}-${role}-${key}`,options[key]);}
  });
  invalidate();translate();
}
function number(text,nullable=false){if(text===''&&nullable)return null;if(!/^-?(?:0|[1-9]\d*)$/.test(text))throw Error(say('Use whole numbers in explicit scaled units; leave unknown values blank.','Utilisez des nombres entiers dans des unités explicitement mises à l’échelle ; laissez les valeurs inconnues vides.'));const result=Number(text);if(!Number.isFinite(result))throw Error('DISCOVERY_VALUE');return result;}
function read(raw=false){
  const input={schema:discovery.SCHEMA};for(const key of ['mission','baseline','alternative','candidate','changed','rights'])input[key]=$(key).value;
  input.evidence=[...$('ledger').children].map((_,i)=>Object.fromEntries(['kind','claim','reference','basis','supports'].map(key=>[key,key==='supports'?[...$(`e-${i}-${key}`).querySelectorAll('input:checked')].map(el=>el.value):$(`e-${i}-${key}`).value])));
  input.constraints=[...$('constraints').children].map((_,i)=>Object.fromEntries(['name','status','reference'].map(key=>[key,$(`c-${i}-${key}`).value])));
  input.metrics=[...$('metrics').children].map((box,i)=>{const row={category:box.dataset.category};for(const key of ['name','unit','direction','minimumGain'])row[key]=key==='minimumGain'&&!raw?number($(`m-${i}-${key}`).value):$(`m-${i}-${key}`).value;for(const role of ['baseline','alternative','candidate'])row[role]=Object.fromEntries(['value','basis','reference'].map(key=>[key,key==='value'&&!raw?number($(`m-${i}-${role}-${key}`).value,true):$(`m-${i}-${role}-${key}`).value]));return row;});return input;
}
function invalidate(){revision++;brief=null;$('result').hidden=true;$('export').disabled=true;$('error').hidden=true;updateJourney();}
function error(e){$('error').hidden=false;$('error').textContent=String(e.message||e);}
function render(){
  if(!brief)return;
  const a=brief.analysis;
  $('decision').textContent=a.decision==='retain-incumbent'?say('Keep the incumbent. Reframe the candidate.','Conservez l’existant. Reformulez la candidate.'):a.decision==='evidence-needed'?say('A useful question, not yet an established advantage.','Une question utile, pas encore un avantage établi.'):say('A candidate worth independent review.','Une candidate à examiner indépendamment.');
  $('why').textContent=say(`${a.gaps.length} evidence gaps. Keep “${brief.input.baseline}” available. Comparisons use supplied claims only.`,`${a.gaps.length} lacunes de preuve. Gardez « ${brief.input.baseline} » disponible. Les comparaisons utilisent uniquement les déclarations fournies.`);
  $('hypotheses').replaceChildren();for(const h of a.hypotheses){const article=node('article',$('hypotheses'));node('h4',article,h.option,h.option);node('p',article,say('Why now: ','Pourquoi maintenant : ')+h.whyNow,say('Why now: ','Pourquoi maintenant : ')+h.whyNow);node('p',article,`${h.evidence.length} linked supplied entries; hypothesis, not discovery.`,`${h.evidence.length} références fournies liées ; hypothèse, pas découverte.`);for(const e of h.evidence)node('p',article,`${e.claim} — ${e.reference}`,`${e.claim} — ${e.reference}`);}
  const target=a.experiment.target;
  $('experiment').textContent=target.kind==='constraint'?say(`First resolve “${target.subject}”. Ask a qualified reviewer for the smallest safe evidence review or accredited test. Do not begin physical testing from this proposal.`,`Résolvez d’abord « ${target.subject} ». Demandez à une personne qualifiée la plus petite revue sûre ou un essai accrédité. Ne commencez aucun essai physique à partir de cette proposition.`):say(`Investigate “${target.subject}” against both alternatives. Agree the method, uncertainty, independent reviewer, budget and stop conditions before any work.`,`Examinez « ${target.subject} » face aux deux alternatives. Convenez de la méthode, de l’incertitude, de l’examen indépendant, du budget et des conditions d’arrêt avant tout travail.`);
  $('gaps').replaceChildren();for(const gap of a.gaps)node('li',$('gaps'),gap.subject,gap.subject);
  $('inspection').textContent=JSON.stringify(brief,null,2);$('result').hidden=false;$('export').disabled=false;bilingual($('draft-state'),'Proposal computed from supplied inputs. Editing returns to a partial draft.','Proposition calculée à partir des données fournies. Toute modification rétablit le brouillon.');
}
function missingField(){return [...$('editor').querySelectorAll('input,textarea,select')].find(el=>el.type!=='checkbox'&&el.dataset.key!=='value'&&!el.value.trim());}
function grow(){document.querySelectorAll('textarea').forEach(el=>{if(el.getClientRects().length){el.style.height='auto';el.style.height=`${el.scrollHeight+4}px`;}});}
function updateJourney(focus=false){
  document.querySelectorAll('[data-step]').forEach(el=>el.hidden=!expert&&Number(el.dataset.step)!==step);
  for(let i=0;i<4;i++){$(`edit-step-${i}`).setAttribute('aria-current',!expert&&step===i?'step':'false');}
  $('show-all').setAttribute('aria-pressed',String(expert));$('journey-back').hidden=expert||step===0;$('journey-next').hidden=expert||step===3;
  const summary=$('journey-summary');summary.replaceChildren();
  for(const key of ['mission','changed','baseline','alternative','candidate']){const value=$(key)?.value||'';if(!value&&key!=='mission'&&key!=='changed')continue;const chars=Array.from(value);const preview=chars.slice(0,180).join('')+(chars.length>180?'…':'');node('p',summary,`${words[key][0]}: ${preview||'Still open'}`,`${words[key][1]} : ${preview||'Question ouverte'}`);}
  const count=$('ledger').children.length;node('p',summary,`${count} supplied evidence entries; references remain unverified.`,`${count} entrées de preuve fournies ; références non vérifiées.`);
  if(!brief)bilingual($('draft-state'),'Partial draft · No current analysis. Save before leaving.','Brouillon partiel · Aucune analyse actuelle. Enregistrez avant de partir.');
  const missing=missingField();$('next-question').textContent=missing?say(`Next question: ${words[missing.dataset.key]?.[0]||missing.dataset.key}`,`Prochaine question : ${words[missing.dataset.key]?.[1]||missing.dataset.key}`):say('Review the comparisons, then find the next evidence step.','Vérifiez les comparaisons, puis trouvez la prochaine étape de preuve.');
  grow();if(focus)$(`step-${step}`).focus();
}
function go(next){revision++;step=next;expert=false;updateJourney(true);}
$('journey-next').addEventListener('click',()=>go(Math.min(3,step+1)));
$('journey-back').addEventListener('click',()=>go(Math.max(0,step-1)));
for(let i=0;i<4;i++)$(`edit-step-${i}`).addEventListener('click',()=>go(i));
$('show-all').addEventListener('click',()=>{revision++;expert=!expert;updateJourney();});
$('metrics').addEventListener('toggle',grow,true);
window.addEventListener('resize',grow);
$('save-draft').addEventListener('click',()=>{try{const draft=drafts.createDraft(read(true),step,language);const url=URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='alpha-discovery-partial-draft.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){error(e);}});
$('editor').addEventListener('input',invalidate);$('editor').addEventListener('change',invalidate);
$('editor').addEventListener('submit',async event=>{event.preventDefault();if(busy)return;const missing=missingField();if(missing){const section=missing.closest('[data-step]');if(!expert&&section)go(Number(section.dataset.step));error(Error(say('Complete this question, or save your partial draft. Unknown observations may stay blank; describe unmeasured evidence explicitly.','Complétez cette question ou enregistrez le brouillon. Les observations inconnues peuvent rester vides ; décrivez explicitement les preuves manquantes.')));const details=missing.closest('details');if(details)details.open=true;grow();missing.focus();return;}busy=true;$('analyze').disabled=true;const expected=revision;try{const next=await discovery.createBrief(read(),SOURCE_HASH);if(revision!==expected)return;brief=next;render();$('result').focus();}catch(e){error(e);}finally{busy=false;$('analyze').disabled=false;}});
$('example').addEventListener('click',()=>{expert=true;fill(discovery.example());});
$('add-evidence').addEventListener('click',()=>{const n=$('ledger').children.length;if(n>=24)return;evidenceRow({kind:'research',claim:'',reference:'',basis:'supplied-report',supports:[]},n);invalidate();$(`e-${n}-claim`).focus();});
$('add-constraint').addEventListener('click',()=>{const n=$('constraints').children.length;if(n>=12)return;constraintRow({name:'',status:'unknown',reference:''},n);invalidate();$(`c-${n}-name`).focus();});
$('language').addEventListener('click',()=>{revision++;language=language==='en'?'fr':'en';translate();render();updateJourney();});
$('export').addEventListener('click',()=>{if(!brief)return;const url=URL.createObjectURL(new Blob([JSON.stringify(brief,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='alpha-opportunity-unfunded.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('restore').addEventListener('change',async()=>{const file=$('restore').files[0];if(!file)return;const expected=revision, token=++importEpoch;try{if(file.size>2000000)throw Error('DISCOVERY_IMPORT_SIZE');const bytes=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());if(token!==importEpoch)return;if(revision!==expected)throw Error(say('Inputs changed while reading; reopen the file.','Données modifiées pendant la lecture ; rouvrez le fichier.'));const parsed=transport.parseBounded(bytes);if(parsed.schema===drafts.DRAFT_SCHEMA){const draft=drafts.restoreDraft(bytes);language=draft.language;step=draft.step;expert=false;fill(draft.input);bilingual($('status'),'Partial draft restored. No analysis or authority imported.','Brouillon partiel restauré. Aucune analyse ni autorité importée.');return;}const restored=discovery.restoreInput(bytes);expert=true;fill(restored);bilingual($('status'),'Only inputs restored. Imported results and permissions were discarded. Recompute a fresh proposal.','Seules les données ont été restaurées. Résultats et permissions importés ignorés. Recalculez une proposition.');}catch(e){if(token===importEpoch)error(e);}finally{if(token===importEpoch)$('restore').value='';}});
const initial=discovery.example();for(const key of ['mission','baseline','alternative','candidate','changed','rights'])initial[key]='';initial.evidence=[];initial.constraints=[{name:'',status:'unknown',reference:''}];initial.metrics.forEach(row=>{row.name=words[row.category][0];row.minimumGain='';row.unit='';for(const role of ['baseline','alternative','candidate'])row[role]={value:null,basis:'unknown',reference:''};});fill(initial);
