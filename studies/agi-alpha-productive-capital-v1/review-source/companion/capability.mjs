// SPDX-License-Identifier: Apache-2.0
import {createWorkbench} from '../vendor/alpha/companion/vendor/examples/successor-workbench/engine.mjs';
import {canonical,digest} from '../vendor/alpha/companion/vendor/docs/assets/successor/engine.mjs';
import {portfolio,Meter,inspectTask,verifyLocal,lowerBound} from '../vendor/alpha/companion/core.mjs';
const copy=x=>JSON.parse(JSON.stringify(x));
const html=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sorted=x=>[...x].sort();
export const STAGES=['Identify','Out-Learn','Out-Think','Out-Design','Out-Strategise','Out-Execute','Out-Evolve'];
export const MANIFEST={id:'productive-capital',version:1,en:'A verified release change dossier',fr:'Un dossier de changement vérifié',scope:'Public-source inventory, bounded planning and bilingual release documentation; deterministic local research.',artifact:'release-dossier.html'};
const file=(name,type,value)=>({name,type,content:typeof value==='string'?value:JSON.stringify(value,null,2)+'\n'});
export function validateProject(p){
 if(p?.schema!=='productive-project/v1'||!['public-derived-synthetic','synthetic'].includes(p.data_class))throw Error('PROJECT_SCHEMA');
 if(!Array.isArray(p.components)||p.components.length<1||p.components.length>18)throw Error('COMPONENT_SCOPE');
 const ids=new Set(p.components.map(x=>x.id));if(ids.size!==p.components.length)throw Error('DUPLICATE_COMPONENT');
 const visiting=new Set(),done=new Set(),map=new Map(p.components.map(x=>[x.id,x]));
 function visit(id){if(visiting.has(id))throw Error('DEPENDENCY_CYCLE');if(done.has(id))return;const c=map.get(id);if(!c)throw Error('MISSING_DEPENDENCY');
  if(typeof c.content!=='string'||c.content.length>30000||!/^https:\/\/github.com\/MontrealAI\//.test(c.source_url)||!c.source_sha256?.match(/^[a-f0-9]{64}$/)||!Array.isArray(c.deps))throw Error('SOURCE_EVIDENCE_REQUIRED');
  visiting.add(id);c.deps.forEach(visit);visiting.delete(id);done.add(id);
 }
 p.components.forEach(c=>visit(c.id));inspectTask(p.task);return true;
}
async function sourceHash(text){const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));return Array.from(new Uint8Array(b)).map(x=>x.toString(16).padStart(2,'0')).join('');}
async function stateHash(s){const {integrity,...body}=s;return digest('productive-state',body);}
export async function inspectState(state){if(state?.schema!=='productive-state/v1'||state.integrity!==await stateHash(state))throw Error('PARENT_STATE_INTEGRITY');return true;}
async function fingerprints(project){
 const hashes={};for(const c of project.components)hashes[c.id]=await sourceHash(c.content);
 const byId=new Map(project.components.map(c=>[c.id,c])),keys={},closures={};
 async function key(id){if(keys[id])return keys[id];let ancestors=new Set();for(const d of byId.get(id).deps){await key(d);ancestors.add(d);for(const a of closures[d])ancestors.add(a);}
  closures[id]=sorted(ancestors);keys[id]=await digest('evidence-node',{id,source:hashes[id],url:byId.get(id).source_url,source_sha256:byId.get(id).source_sha256,deps:sorted(byId.get(id).deps).map(d=>[d,keys[d]])});return keys[id];
 }
 for(const c of project.components)await key(c.id);return {hashes,keys,closures};
}
export async function retainedParent(project,previous=null){
 const start=performance.now();validateProject(project);if(previous)await inspectState(previous);
 const fp=await fingerprints(project),old=previous?.index??{};const changed=project.components.filter(c=>!old[c.id]||old[c.id].hash!==fp.hashes[c.id]||canonical(sorted(old[c.id].deps))!==canonical(sorted(c.deps))||old[c.id].evidence.source_url!==c.source_url||old[c.id].evidence.original_source_sha256!==c.source_sha256).map(c=>c.id);
 const removed=Object.keys(old).filter(id=>!fp.hashes[id]);
 const parent={id:'evidence-index-v1',schema:'evidence-index/v1',project_id:project.id,previous_integrity:previous?.integrity??null,hashes:fp.hashes,keys:fp.keys,closures:fp.closures,changed:sorted(changed),removed:sorted(removed)};
 return {parent,parent_call:{capability:'evidence-index-v1',input_digest:await digest('productive-project',project),output_digest:await digest('evidence-index',parent),wall_ms:Math.round(performance.now()-start),reads:project.components.length,source_bytes:project.components.reduce((s,c)=>s+new TextEncoder().encode(c.content).length,0)}};
}
export async function constructChild(parent){
 if(parent?.schema!=='evidence-index/v1')throw Error('PARENT_REQUIRED');
 const descriptor={schema:'dependency-repair/v1',id:'dependency-repair-v1',parent_id:'evidence-index-v1',parent_digest:await digest('evidence-index',parent),algorithm:'transitive-evidence-invalidation',version:1,permissions:[],limits:{components:18,planning_jobs:18}};
 return {...descriptor,digest:await digest('dependency-repair',descriptor)};
}
function descendants(project,roots){const affected=new Set(roots);let changed=true;while(changed){changed=false;for(const c of project.components)if(!affected.has(c.id)&&c.deps.some(d=>affected.has(d))){affected.add(c.id);changed=true;}}return sorted(affected);}
export async function childImpact(project,parent,previous,child){
 const {digest:childDigest,...desc}=child??{};
 if(childDigest!==await digest('dependency-repair',desc)||desc.parent_id!=='evidence-index-v1')throw Error('CHILD_BINDING');
 if(parent.project_id!==project.id||parent.previous_integrity!==previous?.integrity)throw Error('PARENT_USE_BINDING');
 const invalidated=descendants(project,[...parent.changed,...parent.removed]);
 const certificate={schema:'change-impact/v1',capability:'dependency-repair-v1',predecessor:previous?.integrity??null,parent_digest:await digest('evidence-index',parent),child_digest:childDigest,changed:parent.changed,removed:parent.removed,invalidated,unchanged:project.components.map(c=>c.id).filter(id=>!invalidated.includes(id)).sort(),method:'Transitive dependency closure over declared edges',proof_scope:'Completeness relative to supplied graph, not discovery of undeclared dependencies.'};
 return {...certificate,digest:await digest('change-impact',certificate)};
}
function extractEvidence(component,fp){
 const lines=component.content.split('\n'),license=lines.find(x=>/SPDX-License-Identifier:/.test(x))??null;
 const references=[...component.content.matchAll(/(?:from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"])/g)].map(x=>x[1]??x[2]);
 const declared=[...component.content.matchAll(/(?:export\s+(?:async\s+)?(?:function|class|const)\s+|^def\s+|^class\s+|contract\s+)([A-Za-z_][A-Za-z_0-9]*)/gm)].map(x=>x[1]);
 return {id:component.id,path:component.path,source_url:component.source_url,original_source_sha256:component.source_sha256,current_sha256:fp.hashes[component.id],synthetic_modified:component.source_sha256!==fp.hashes[component.id],line_count:lines.length,bytes:new TextEncoder().encode(component.content).length,spdx:license?.trim()??null,declared_names:sorted(new Set(declared)),literal_imports:sorted(new Set(references)),deps:sorted(component.deps),transitive_dependencies:fp.closures[component.id],dependency_key:fp.keys[component.id],claims_scope:'Literal source inventory only; no security, functional or deployed-bytecode audit.'};
}
async function conventionalKeys(project){
 const nodes={};for(const c of project.components)nodes[c.id]={c,hash:await sourceHash(c.content)};
 const pending=project.components.map(c=>c.id),keys={},closures={};
 while(pending.length){let progress=false;for(let i=pending.length-1;i>=0;i--){const id=pending[i],n=nodes[id];if(n.c.deps.some(d=>!keys[d]))continue;
  closures[id]=sorted(new Set(n.c.deps.flatMap(d=>[d,...closures[d]])));keys[id]=await digest('evidence-node',{id,source:n.hash,url:n.c.source_url,source_sha256:n.c.source_sha256,deps:sorted(n.c.deps).map(d=>[d,keys[d]])});pending.splice(i,1);progress=true;}
  if(!progress)throw Error('DEPENDENCY_CYCLE');
 }
 return {hashes:Object.fromEntries(Object.entries(nodes).map(([k,v])=>[k,v.hash])),keys,closures};
}
function normalizedTask(task){const t=copy(task);delete t.id;return t;}
function choosePlan(task,native){
 const meter=new Meter(1000000),ordinary=portfolio(task,meter,undefined,{stopOnQualified:false});
 const candidates=[{method:'existing-alpha-portfolio',result:ordinary.result,work:meter.spent}],rejected=[];if(native&&!native.schedule)rejected.push({method:'existing-native-specialist',rejected:true,error:native.status??'NO_SCHEDULE'});
 if(native?.schedule){const m=inspectTask(task),bound=lowerBound(m);const r={schema:'release-plan-result/v1',task_id:task.id,schedule:native.schedule,makespan:native.makespan,movement:native.movement??0,lower_bound:bound,optimal_by_lower_bound:native.makespan===bound.value,proof:[],authority:[]};
  try{verifyLocal(task,r);candidates.push({method:task.kind==='repair'?'existing-native-repair':'existing-native-highs',result:r,work:null});}catch(error){rejected.push({method:'existing-native-specialist',rejected:true,error:error.message});}
 }
 candidates.sort((a,b)=>{const qa=a.result.makespan<=task.deadline,qb=b.result.makespan<=task.deadline;if(qa!==qb)return qa?-1:1;return (task.kind==='repair'&&qa?a.result.movement-b.result.movement:0)||a.result.makespan-b.result.makespan;});
 return {selected:candidates[0],alternatives:candidates.map(x=>({method:x.method,makespan:x.result.makespan,movement:x.result.movement,qualified:x.result.makespan<=task.deadline})),rejected_alternatives:rejected,ordinary_work:meter.spent,native_present:Boolean(native),native_status:native?.status??'NOT_RUN'};
}
function dossier(project,assurance,plan,impact){
 const rows=assurance.components.map(c=>`<tr><td>${html(c.id)}</td><td>${html(c.path)}</td><td>${c.bytes}</td><td>${html(c.deps.join(', ')||'—')}</td><td><a href="${html(c.source_url)}">Source</a></td><td><code>${c.current_sha256}</code></td></tr>`).join('');
 const schedule=plan.result.schedule.map(s=>`<tr><td>${html(s.id)}</td><td>${s.start}</td><td>${s.end}</td><td>${html(project.task.jobs.find(j=>j.id===s.id).deps.join(', '))}</td></tr>`).join('');
 return `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${html(project.title)} — verified release dossier</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:3em auto;padding:0 2em;color:#21143b}h1,h2{color:#4c248b}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left;overflow-wrap:anywhere}code{font-size:10px;word-break:break-all}.label{color:#666}aside{background:#f0e9ff;padding:1.2em;border-radius:12px}</style><h1>${html(project.title)}</h1><p class="label">AGI ALPHA FLYWHEEL · Productive Capital Engine · Cycle ${project.cycle}</p><aside><b>Recorded local computation / Calcul local enregistré.</b> Public source metadata with synthetic project dependencies and revisions. Planning does not execute a rollout. Source scanning does not certify security or contract behavior.</aside><h2>Decision / Décision</h2><p>Release evidence contains ${assurance.components.length} components. The machine-checked plan ends at slot ${plan.result.makespan} against deadline ${project.task.deadline}; method: ${html(plan.method)}. / Le dossier contient ${assurance.components.length} composants. Le plan vérifié automatiquement se termine au créneau ${plan.result.makespan}, pour une échéance de ${project.task.deadline}.</p><h2>Revision scope / Portée de la révision</h2><p>Changed / Modifiés: ${html(impact.changed.join(', ')||'none / aucun')}. Invalidated / À reconstruire: ${html(impact.invalidated.join(', ')||'none / aucun')}. Every unchanged record retains the exact predecessor evidence key. / Chaque élément inchangé conserve la clé de preuve de son prédécesseur.</p><h2>Source assurance / Traçabilité des sources</h2><table><thead><tr><th>ID</th><th>Path / Chemin</th><th>Bytes</th><th>Dependencies</th><th>Reference</th><th>Current SHA-256</th></tr></thead><tbody>${rows}</tbody></table><h2>Rollout plan / Plan de livraison</h2><table><thead><tr><th>Job</th><th>Start / Début</th><th>End / Fin</th><th>Dependencies</th></tr></thead><tbody>${schedule}</tbody></table><h2>Acceptance boundary / Limites</h2><p>All three deliverables share the same project revision and source keys. Declared dependencies, capacity, releases and frozen starts are machine-checked. Human acceptance, full delivery cost, paid demand and authenticated executor operation remain unmeasured here. / Les trois livrables partagent la même révision et les mêmes clés de source. Les dépendances, capacités, disponibilités et débuts figés déclarés sont vérifiés. L'acceptation humaine, le coût complet, la demande payante et l'exécution authentifiée ne sont pas mesurés ici.</p></html>`;
}
export async function runProject(project,{arm='flywheel',previous=null,child=null,nativeResult=null,sourceHash:binding='0'.repeat(64)}={}){
 const begin=performance.now(),trace=[],metrics={source_bytes_read:0,lines_examined:0,built_items:0,reused_items:0,parent_calls:0,child_calls:0,ordinary_work:0};
 validateProject(project);if(previous)await inspectState(previous);
 let fp,parentCall=null,parent=null,impact;
 if(arm==='flywheel'){
  const result=await retainedParent(project,previous);parent=result.parent;parentCall=result.parent_call;fp={hashes:parent.hashes,keys:parent.keys,closures:parent.closures};metrics.parent_calls=1;metrics.source_bytes_read=parentCall.source_bytes;
  if(child){impact=await childImpact(project,parent,previous,child);metrics.child_calls=1;}else{if(previous&&project.cycle>=2)throw Error('CHILD_REQUIRED_FOR_FRESH_CHANGE');const invalidated=project.components.filter(c=>!previous?.index[c.id]||previous.index[c.id].key!==fp.keys[c.id]).map(c=>c.id).sort();impact={schema:'change-impact/v1',capability:'evidence-index-v1',predecessor:previous?.integrity??null,changed:parent.changed,removed:parent.removed,invalidated,unchanged:project.components.map(c=>c.id).filter(id=>!invalidated.includes(id)).sort(),method:'Retained evidence index initial or stable production',proof_scope:'No claimed child capability before construction.'};impact.digest=await digest('change-impact',impact);}
 }else{fp=await conventionalKeys(project);metrics.source_bytes_read=project.components.reduce((s,c)=>s+new TextEncoder().encode(c.content).length,0);
  const changed=project.components.filter(c=>!previous?.index[c.id]||previous.index[c.id].hash!==fp.hashes[c.id]||canonical(previous.index[c.id].deps)!==canonical(sorted(c.deps))||previous.index[c.id].evidence.source_url!==c.source_url||previous.index[c.id].evidence.original_source_sha256!==c.source_sha256).map(c=>c.id);
  const invalidated=project.components.filter(c=>!previous?.index[c.id]||previous.index[c.id].key!==fp.keys[c.id]).map(c=>c.id).sort();
  impact={schema:'change-impact/v1',capability:'ordinary-content-cache',predecessor:previous?.integrity??null,changed:sorted(changed),removed:[],invalidated,unchanged:project.components.map(c=>c.id).filter(id=>!invalidated.includes(id)).sort(),method:'Independent iterative content-key memoization',proof_scope:'Completeness relative to supplied graph only.'};impact.digest=await digest('change-impact',impact);
 }
 const components=project.components.map(c=>{const prior=previous?.index[c.id];if(arm!=='full_rebuild'&&prior?.key===fp.keys[c.id]){metrics.reused_items++;return copy(prior.evidence);}metrics.built_items++;metrics.lines_examined+=c.content.split('\n').length;return extractEvidence(c,fp);});
 const assurance={schema:'release-assurance/v1',project_id:project.id,cycle:project.cycle,components,dependency_edges:project.components.flatMap(c=>c.deps.map(d=>[d,c.id])).sort(),input_class:project.data_class};
 const taskKey=await digest('release-task',normalizedTask(project.task));let plan;
 if(arm!=='full_rebuild'&&previous?.task_key===taskKey){plan=copy(previous.plan);plan.result.task_id=project.task.id;plan.reused=true;}
 else{const selected=choosePlan(project.task,nativeResult);plan={schema:'rollout-plan/v1',project_id:project.id,cycle:project.cycle,task:copy(project.task),result:selected.selected.result,method:selected.selected.method,alternatives:selected.alternatives,rejected_alternatives:selected.rejected_alternatives,task_key:taskKey,reused:false};metrics.ordinary_work=selected.ordinary_work;}
 plan.project_id=project.id;plan.cycle=project.cycle;plan.task=copy(project.task);verifyLocal(project.task,plan.result);
 const consistency={schema:'cross-artifact-consistency/v1',project_id:project.id,cycle:project.cycle,source_keys:fp.keys,assurance_digest:await digest('assurance',assurance),planning_digest:await digest('planning',plan),impact_digest:impact.digest,locked_starts:project.task.locked??{},parent_integrity:previous?.integrity??null};
 const document=dossier(project,assurance,plan,impact);consistency.dossier_sha256=await sourceHash(document);
 const artifacts=[file('release-assurance.json','application/json',assurance),file('rollout-plan.json','application/json',plan),file('release-dossier.html','text/html',document),file('change-impact.json','application/json',impact),file('consistency.json','application/json',consistency)];
 const state={schema:'productive-state/v1',project_id:project.id,cycle:project.cycle,index:Object.fromEntries(components.map(c=>[c.id,{hash:fp.hashes[c.id],key:fp.keys[c.id],deps:c.deps,evidence:c}])),task_key:taskKey,plan};state.integrity=await stateHash(state);
 const stageRecords=[['Identify',{objective:project.title,acceptance:'Three synchronized deliverables; exact source inventory, valid plan, bilingual dossier.'}],['Out-Learn',{sources:components.map(c=>({id:c.id,url:c.source_url,sha256:c.current_sha256}))}],['Out-Think',{changed:impact.changed,affected:impact.invalidated}],['Out-Design',{capability:arm==='flywheel'?'dependency-repair-v1':'ordinary-content-cache',source_keys:fp.keys}],['Out-Strategise',{selected:plan.method,alternatives:plan.alternatives,rejected_alternatives:plan.rejected_alternatives}],['Out-Execute',{artifact_names:artifacts.map(a=>a.name),planning_only:true}],['Out-Evolve',{retained_state:state.integrity,parent_call:parentCall,child_use:arm==='flywheel'?(impact.child_digest??null):null,production_authority:false}]];
 const adapter={manifest:MANIFEST,validate:input=>{if(input.project_id!==project.id||input.revision!==project.cycle)throw Error('PROJECT_BINDING');},execute:async(input,checkpoint)=>{for(const [stage,artifact]of stageRecords){await checkpoint(stage);trace.push({stage,artifact,artifact_digest:await digest(stage.toLowerCase(),artifact)});}return {decision:'READY_FOR_INDEPENDENT_RESEARCH_CHECK',summary:{components:components.length,makespan:plan.result.makespan,deadline:project.task.deadline,artifact_count:5},evidence:{stages:trace,metrics,parent_call:parentCall,scope:'Local deterministic research; no authenticated execution or financial settlement.'},artifacts,limits:['Source extraction is a literal inventory, not security or functional certification.','Planning does not perform physical work.','No measured human time, complete Agent cost, customer demand or revenue.']};}};
 const workbench=createWorkbench([adapter]);
 const spec={schema:'successor-workbench/v1',family:MANIFEST.id,name:'Productive Capital Engine',language:'en',owner:'productive-capital-research',rights:{dataClass:'synthetic',source:'Pinned public source snapshots and explicitly synthetic project requirements',license:'Apache-2.0'},reviewMinutes:30,inputs:{project_id:project.id,revision:project.cycle}};
 const pack=await workbench.run(spec,{sourceHash:binding});await workbench.inspectPack(pack);
 return {pack,state,assurance,plan,impact,consistency,metrics,trace,wall_ms:performance.now()-begin};
}
