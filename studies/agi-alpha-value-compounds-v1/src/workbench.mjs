// SPDX-License-Identifier: Apache-2.0
// Registered, local-only adapter on the unchanged SUCCESSOR Workbench extension API.
import {createWorkbench} from '../native/examples/successor-workbench/engine.mjs';
import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createInterface} from 'node:readline';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json=(name,x)=>({name,type:'application/json',content:JSON.stringify(x,null,2)+'\n'});
export async function assetIdentity(){
  const names=(await readdir(path.join(ROOT,'src'))).filter(n=>/\.(py|mjs)$/.test(n)).sort();
  const rows=[];for(const n of names)rows.push([n,hash(await readFile(path.join(ROOT,'src',n)))]);
  rows.push(['native/SOURCE.json',hash(await readFile(path.join(ROOT,'native/SOURCE.json')))]);
  return hash(JSON.stringify(rows));
}
function compact(report,receipt){
  const consumer=report.consumer_assessment||{};
  const changes=(report.reports||[]).flatMap(m=>m.functions.filter(f=>f.status==='call_loss').map(f=>({path:m.path,name:f.name,witness:f.witness,reason:f.reason||null})));
  return {schema:'upgrade-customer-packet/v1',mission_digest:report.mission_digest,repository:report.repository,before_ref:report.before_ref,after_ref:report.after_ref,status:report.status,arm:report.arm,
    changed_modules:report.changed_modules,unchanged_modules:report.unchanged_modules||0,summary:report.summary||null,
    binding_losses:changes,consumer_coverage:consumer.coverage||null,candidate_coverage:consumer.candidate_coverage||null,
    consumer_findings:consumer.findings||[],syntactic_candidate_findings:consumer.syntactic_candidate_findings||[],
    verification:(report.independent_validation||[]).map(v=>({path:v.path,accepted:v.accepted})),
    resources:report.meter,complete_money_cost_usd:null,actual_customer_receipts_usd:0,
    full_evidence:{path:path.relative(ROOT,receipt.path),sha256:receipt.sha256,bytes:receipt.bytes},
    action:report.status==='INVENTORY_ONLY'?'Review source inventories and diffs; this arm does not produce compatibility assessment.':changes.length?'Review listed binding losses and affected caller candidates. Run project integration checks before choosing an upgrade or pin.':'No supported binding loss found. Review unresolved scope, behavioral changes and project integration tests before upgrading.',
    limits:report.limits||['Unchanged input is a no-op, not a new customer job.']};
}
function readable(p,language){
  const fr=language==='fr';
  const title=fr?'Décision de mise à jour des dépendances':'Dependency upgrade decision packet';
  const heading=fr?'Votre résultat':'Your result';
  const rows=p.binding_losses.map(x=>`<tr><td>${esc(x.path)}</td><td>${esc(x.name)}</td><td>${esc(JSON.stringify(x.witness))}</td></tr>`).join('');
  const callerRows=[...p.consumer_findings.map(x=>({...x,lane:'strict'})),...p.syntactic_candidate_findings.map(x=>({...x,lane:'candidate / runtime unproved'}))].map(x=>`<tr><td>${esc(x.consumer_path)}:${x.line}</td><td>${esc(x.lane)}</td><td><code>${esc(x.snippet)}</code></td></tr>`).join('');
  return `<!doctype html><html lang="${language}"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${title}</title><style>body{font:17px/1.55 system-ui;color:#21153c;background:#faf8ff;max-width:1100px;margin:48px auto;padding:24px}header{padding:32px;background:#28104e;color:white;border-radius:18px}small{letter-spacing:.12em}h1{font-size:36px}h2{color:#6026a0;margin-top:2em}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #d7cbea}code{white-space:pre-wrap;overflow-wrap:anywhere}.note{background:#eee4fb;border-left:4px solid #8250c6;padding:20px}p{overflow-wrap:anywhere}</style><header><small>AGI ALPHA · TRANSFORMATIONAL INTELLIGENCE ∞ · SUCCESSOR Ω</small><h1>${title}</h1><p>${esc(p.repository)} · ${esc(p.status)}</p></header><h2>${heading}</h2><p>${fr?'Évaluation locale des sources déclarées :':'Local assessment of declared sources:'} ${p.changed_modules} ${fr?'modules modifiés':'changed modules'}, ${p.binding_losses.length} ${fr?'déclarations perdant une forme d’appel acceptée':'declarations losing an accepted call shape'}.</p><p>${esc(p.action)}</p><div class="note">${fr?'Ce résultat ne constitue pas une autorisation de déploiement. Les candidats syntaxiques exigent une validation d’intégration. Le coût monétaire complet et le prix restent inconnus.':'This is not deployment authorization. Syntactic candidates require integration validation. Complete monetary cost and customer price remain unknown.'}</div><h2>${fr?'Appels du projet à examiner':'Project calls to review'}</h2><table><thead><tr><th>${fr?'Source':'Source'}</th><th>${fr?'Qualification':'Qualification'}</th><th>${fr?'Appel':'Call'}</th></tr></thead><tbody>${callerRows||`<tr><td colspan="3">${fr?'Aucun appel affecté établi dans la portée capturée. Cela ne prouve pas la compatibilité du projet.':'No affected call established in captured scope. This does not prove project compatibility.'}</td></tr>`}</tbody></table><h2>${fr?'Changements vérifiés de liaison des arguments':'Verified argument-binding changes'}</h2><table><thead><tr><th>Module</th><th>${fr?'Déclaration':'Declaration'}</th><th>${fr?'Contre-exemple':'Counterexample'}</th></tr></thead><tbody>${rows||'<tr><td colspan="3">0</td></tr>'}</tbody></table><h2>${fr?'Ressources et limites':'Resources and limits'}</h2><p>CPU ${(p.resources.cpu_ns/1e9).toFixed(3)} s · ${fr?'durée':'elapsed'} ${(p.resources.wall_ns/1e9).toFixed(3)} s · ${fr?'appels de modèle à l’exécution':'runtime model calls'} 0.</p><p>${fr?'Reçus clients réels : 0. Coût marginal, coût récurrent et coût complet : inconnus.':'Actual customer receipts: 0. Marginal, recurring and fully loaded money costs: unknown.'}</p><ul>${p.limits.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><h2>${fr?'Preuve complète':'Complete evidence'}</h2><p>${esc(p.full_evidence.path)}<br>SHA-256 ${esc(p.full_evidence.sha256)}</p><p>${esc(p.before_ref)} → ${esc(p.after_ref)}</p></html>`;
}
export async function createSession(outDirectory,cacheDirectory,{reuse=true}={}){
  const out=path.resolve(outDirectory),cache=path.resolve(cacheDirectory);await mkdir(out,{recursive:true});await mkdir(cache,{recursive:true});
  const registry=JSON.parse(await readFile(path.join(ROOT,'data/missions.json'),'utf8'));
  const child=spawn(process.env.PYTHON_EXECUTABLE||'python',[path.join(ROOT,'src/worker.py'),'--out',out,'--cache',cache],{cwd:ROOT,stdio:['pipe','pipe','pipe']});
  let errors='',pending=null;child.stderr.on('data',b=>{errors=(errors+b.toString()).slice(-8000);});
  createInterface({input:child.stdout}).on('line',line=>{if(pending){const {resolve,reject,timer}=pending;pending=null;clearTimeout(timer);try{resolve(JSON.parse(line));}catch(e){reject(e);}}});
  child.on('exit',code=>{if(pending){clearTimeout(pending.timer);pending.reject(Error(`WORKER_EXIT ${code}: ${errors}`));pending=null;}});
  const request=(mission,arm)=>new Promise((resolve,reject)=>{if(pending)throw Error('SERIAL_WORKER_REQUIRED');const timer=setTimeout(()=>{child.kill();reject(Error('WORKER_TIMEOUT'));pending=null;},45000);pending={resolve,reject,timer};child.stdin.write(JSON.stringify({mission,arm,reuse})+'\n');});
  const adapter={manifest:{id:'upgrade-assessment',version:1,en:'Assess a dependency upgrade',fr:'Évaluer une mise à jour',scope:'Registered public source snapshots; local binding evidence and captured consumer call shapes only.',artifact:'upgrade-packet.json'},validate(input){if(!input||Object.keys(input).sort().join('|')!=='arm|mission'||!Object.hasOwn(registry.missions,input.mission)||!['incumbent','retained','conventional'].includes(input.arm))throw Error('REGISTERED_MISSION_REQUIRED');},async execute(input,checkpoint){
    await checkpoint('assessing-registered-source');const receipt=await request(input.mission,input.arm);const file=path.resolve(receipt.path);if(!file.startsWith(out+path.sep))throw Error('OUTPUT_PATH');const raw=await readFile(file);if(hash(raw)!==receipt.sha256)throw Error('WORKER_EVIDENCE_IDENTITY');const report=JSON.parse(raw);const packet=compact(report,receipt);await checkpoint('independent-validation-completed');
    const artifacts=[json('upgrade-packet.json',packet),{name:'report-en.html',type:'text/html',content:readable(packet,'en')},{name:'report-fr.html',type:'text/html',content:readable(packet,'fr')},json('source-identities.json',report.manifest),json('resource-receipt.json',{...packet.resources,marginal_cost_usd:null,recurring_cost_usd:null,fully_loaded_cost_usd:null,construction_inference_usd:null}),json('full-evidence-reference.json',packet.full_evidence)];
    return {decision:report.status,summary:{changedModules:report.changed_modules,bindingLosses:packet.binding_losses.length,strictConsumerFindings:packet.consumer_findings.length,syntacticCandidateFindings:packet.syntactic_candidate_findings.length},evidence:{sourceBound:true,independentReportValid:report.summary?.independent_report_valid??null,fullEvidenceSha256:receipt.sha256,execution:'LOCAL_RESEARCH_ADAPTER',runtimeModelCalls:0},artifacts,limits:packet.limits};
  }};
  const workbench=createWorkbench([adapter]),sourceHash=await assetIdentity();
  return {async run(mission,arm,language='en'){
    const spec={schema:'successor-workbench/v1',family:'upgrade-assessment',name:'AGI ALPHA Upgrade Decision',language,owner:'local-research',rights:{dataClass:'public',source:'Registered source-pinned repository snapshots; see source identities',license:'Respective upstream licenses preserved'},reviewMinutes:1,inputs:{mission,arm}};
    const pack=await workbench.run(spec,{sourceHash});const inspected=await workbench.inspectPack(pack);return {pack,inspected};
  },close(){child.stdin.end();child.kill();}};
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
  const [mission,arm='retained',directory=path.join(ROOT,'results/local')]=process.argv.slice(2);if(!mission)throw Error('Usage: node src/workbench.mjs MISSION [ARM] [OUTPUT_DIRECTORY]');
  const session=await createSession(path.join(directory,'evidence'),path.join(directory,'cache'));
  try{const result=await session.run(mission,arm);await writeFile(path.join(directory,'pack.json'),JSON.stringify(result.pack,null,2)+'\n');for(const f of result.pack.result.artifacts)await writeFile(path.join(directory,f.name),f.content);await writeFile(path.join(directory,'inspection.json'),JSON.stringify(result.inspected,null,2)+'\n');console.log(JSON.stringify({decision:result.pack.result.decision,summary:result.pack.result.summary,elapsed_ms:result.pack.economics.elapsedMilliseconds,authentication:result.inspected.authentication}));}finally{session.close();}
}
