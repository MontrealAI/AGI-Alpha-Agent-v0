/* Offline DOM/logic QA. This deliberately does not claim browser layout QA. */
'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=__dirname,file=path.join(root,'The_Capability_Advantage_EN_FR.html');
const html=fs.readFileSync(file,'utf8');
const report={started_utc:new Date().toISOString(),artifact:file,checks:[],browser_qa:{status:'not_run',reason:'An existing local headless Chrome was found in another scratch environment. Its launch was blocked by the execution sandbox before a page opened. See qa_browser_report.json; no browser was installed and no cloud browser was invoked.'},layout_visual_qa:{status:'not_run',reason:'Existing browser launch blocked by the execution sandbox; no rendered page or screenshot was produced.'}};
const stripped=html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,'');
const elements=[],downloads=[],blobs=new Map();
class Element{
 constructor(tag,attrs={}){this.tagName=tag.toUpperCase();this.attributes=attrs;this.dataset={};this.style={};this.events={};this.textContent='';this.innerHTML='';this.value='';for(const[k,v]of Object.entries(attrs))if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;this.classList={toggle:(c,on)=>{const a=new Set((this.attributes.class||'').split(/\s+/).filter(Boolean));if(on===undefined)on=!a.has(c);if(on)a.add(c);else a.delete(c);this.attributes.class=[...a].join(' ');return on;},contains:c=>(this.attributes.class||'').split(/\s+/).includes(c)};}
 getAttribute(k){return this.attributes[k]??null;}
 setAttribute(k,v){this.attributes[k]=String(v);}
 addEventListener(name,fn){(this.events[name]??=[]).push(fn);}
 click(){if(this.tagName==='A'&&this.download)downloads.push({filename:this.download,url:this.href,blob:blobs.get(this.href)});for(const fn of this.events.click||[])fn({target:this});}
}
for(const match of stripped.matchAll(/<([a-z][a-z0-9-]*)(\s[^<>]*?)?\/?>/gi)){
 const attrs={};for(const a of (match[2]||'').matchAll(/([^\s=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g))attrs[a[1]]=a[2]??a[3]??a[4]??'';
 elements.push(new Element(match[1],attrs));
}
const dataMatch=html.match(/<script id="study-data" type="application\/json">([\s\S]*?)<\/script>/);
assert(dataMatch,'embedded study data');
const dataElement=new Element('script',{id:'study-data'});dataElement.textContent=dataMatch[1];elements.push(dataElement);
const document={
 documentElement:elements.find(e=>e.tagName==='HTML'),title:'',
 getElementById:id=>elements.find(e=>e.attributes.id===id),
 querySelectorAll:selector=>{
  if(selector.startsWith('[')){const m=selector.match(/^\[([^=\]]+)(?:=["']?([^"'\]]+)["']?)?\]$/);if(!m)throw new Error('Unsupported QA selector: '+selector);return elements.filter(e=>Object.hasOwn(e.attributes,m[1])&&(m[2]===undefined||e.attributes[m[1]]===m[2]));}
  if(selector.startsWith('.'))return elements.filter(e=>e.classList.contains(selector.slice(1)));
  throw new Error('Unsupported QA selector: '+selector);
 },
 createElement:tag=>new Element(tag)
};
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].filter(m=>!/^<script[^>]*type=["']application\/json/.test(m[0]));
assert.equal(scripts.length,1);
const context={document,window:{},console,Intl,Date,JSON,Number,String,Math,Blob,setTimeout:()=>0,URL:{createObjectURL:blob=>{const u='blob:qa-'+blobs.size;blobs.set(u,blob);return u;},revokeObjectURL:()=>{}}};
vm.createContext(context);vm.runInContext(scripts[0][1],context,{filename:file});
const demo=context.window.DEMO;
function check(name,fn){try{fn();report.checks.push({name,passed:true});}catch(error){report.checks.push({name,passed:false,error:error.stack});throw error;}}
async function main(){
 check('embedded actual panel: 12 accepted outcomes',()=>assert.equal(demo.data.summary.accepted_method_stages,12));
 check('primary results preserve all four accepted arms and measured whole-job times',()=>{
  if(demo.data.primary.status!=='available')return;
  const primary=demo.data.primary.data;
  assert.equal(primary.chains,12);
  for(const arm of Object.values(primary.arms)){assert.equal(arm.accepted_stages,36);assert.equal(arm.accepted_chains,12);}
  assert(primary.arms.A.cpu_seconds<primary.arms.B.cpu_seconds);
  assert(primary.arms.A.elapsed_seconds<primary.arms.C.elapsed_seconds);
  assert(document.getElementById('primary-live').innerHTML.includes('98.68 s'));
 });
 check('model default preserves the prespecified non-winning case',()=>{
  if(demo.data.economics.status!=='available')return;
  const e=demo.data.economics,selected=e.data.conditions[demo.state.scenario],rep=e.representative;
  assert.equal(selected.condition_id,'structural-01');assert.equal(selected.schedule_id,'reference');
  assert.equal(rep.seed,12001);
  const expected={A:-61116,B:-61578,C:-61578,D:-61137};
  for(const [name,value] of Object.entries(expected)){
   assert.equal(rep.arms[name].summary.project_inclusive_profit_cents,value);
   assert.equal(rep.arms[name].summary.accepted,0);
   assert.equal(rep.arms[name].summary.collected_cents,0);
   assert.equal(Object.keys(rep.arms[name].assets).length,0);
  }
  assert(document.getElementById('representative-table').innerHTML.includes('-$611.16'));
  assert.equal(e.completion.worlds,2304);
  assert.equal(e.completion.primary_histories,9216);
  assert.equal(e.analysis.qualifying_later_bundle_worlds.B,0);
  assert.equal(e.analysis.qualifying_later_bundle_worlds.C,0);
  assert.equal(e.analysis.signs.C_minus_B_project_cents.paired_worlds.zero,2304);
  assert.equal(e.analysis.signs.C_minus_B_unrounded_compute_project_cents.paired_worlds.negative,5);
  assert.equal(e.analysis.signs.C_minus_B_unrounded_compute_project_cents.paired_worlds.positive,49);
 });
 check('EN/FR translation key coverage',()=>{
  assert.deepEqual(Object.keys(demo.translations.en).sort(),Object.keys(demo.translations.fr).sort());
  for(const el of elements)for(const key of ['i18n','i18nTitle','i18nAria'])if(el.dataset[key])for(const lang of ['en','fr'])assert(Object.hasOwn(demo.translations[lang],el.dataset[key]),lang+':'+el.dataset[key]);
 });
 let combinations=0;
 for(const lang of ['en','fr'])for(const chain of demo.data.chains)for(const stage of ['forward','inverse','design'])for(const timing of ['solver','complete']){
  demo.state.lang=lang;demo.state.chain=chain.id;demo.state.stage=stage;demo.state.timing=timing;demo.render();
  const pair=chain.stages[stage],a=pair.retained_independent,b=pair.acquired_shared,key=timing==='solver'?'method_call_wall_seconds':'stage_total_wall_seconds';
  const format=new Intl.NumberFormat(lang==='fr'?'fr-FR':'en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
  assert.equal(document.getElementById('selected-ratio').textContent,format.format(b[key]/a[key])+'×');
  for(const el of document.querySelectorAll('[data-chain]'))assert.equal(el.classList.contains('active'),el.dataset.chain===chain.id);
  for(const el of document.querySelectorAll('[data-stage]'))assert.equal(el.classList.contains('active'),el.dataset.stage===stage);
  assert.equal(document.documentElement.lang,lang);
  assert.equal(document.getElementById('retained-accepted').textContent,demo.translations[lang].accepted);
  assert.equal(document.getElementById('original-accepted').textContent,demo.translations[lang].accepted);
  combinations++;
 }
 report.checks.push({name:'all language × chain × stage × timing combinations',passed:true,combinations});
 if(demo.data.economics.status==='available'){
  let economicCombinations=0;
  for(const lang of ['en','fr'])for(let i=0;i<demo.data.economics.data.conditions.length;i++){
   demo.state.lang=lang;demo.state.scenario=i;demo.render();
   const record=demo.data.economics.data.conditions[i];
   const expected=new Intl.NumberFormat(lang==='fr'?'fr-FR':'en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2}).format(record.arms.A.project_profit.mean/100);
   assert(document.getElementById('scenario-result').innerHTML.includes(expected));
   assert(document.getElementById('scenario-result').innerHTML.includes(demo.translations[lang].costScheduleWarning));
   assert.equal(document.getElementById('economics-status').textContent,demo.translations[lang].modeled);
   assert.equal(document.getElementById('economics-pending').classList.contains('hidden'),true);
   economicCombinations++;
  }
  report.checks.push({name:'all 144 registered economic cells in both languages',passed:true,combinations:economicCombinations});
  demo.state.scenario=demo.data.economics.data.conditions.findIndex(c=>c.condition_id==='structural-01'&&c.schedule_id==='reference');
 }
 check('actual control events and repeated selectors',()=>{
  document.querySelectorAll('[data-lang]').find(e=>e.dataset.lang==='en').click();
  document.querySelectorAll('[data-chain]').find(e=>e.dataset.chain==='TRANSFER-01').click();
  document.querySelectorAll('[data-stage]').find(e=>e.dataset.stage==='inverse').click();
  document.querySelectorAll('[data-timing]').find(e=>e.dataset.timing==='complete').click();
  assert.equal(demo.state.lang,'en');assert.equal(demo.state.chain,'TRANSFER-01');assert.equal(demo.state.stage,'inverse');assert.equal(demo.state.timing,'complete');
 });
 demo.downloadEvidence();
 const downloaded=JSON.parse(await downloads[0].blob.text());
 check('downloaded selected evidence contains exact records and provenance',()=>{
  assert.equal(downloaded.selection.chain,'TRANSFER-01');assert.equal(downloaded.selection.stage,'inverse');
  assert.equal(downloaded.selected_stage_outcomes.retained_independent.accepted,true);
  assert.equal(downloaded.selected_stage_outcomes.acquired_shared.accepted,true);
  assert.equal(downloaded.source_freeze.methods.retained_independent.sha256,'ebac83103628a8824e88484ab643a2ff359dec26ff26f99285d54642758aa7de');
  assert(downloaded.limitations.length>=4);
  if(demo.data.economics.status==='available'){
   assert.equal(downloaded.selected_economic_scenario.condition_id,'structural-01');
   assert.equal(downloaded.selected_economic_scenario.schedule_id,'reference');
   assert.equal(downloaded.economics.data.unknown_actual_cost_boundary.actual_total_cost_cents,null);
   assert.equal(downloaded.economics.data.unknown_actual_cost_boundary.affirmative_investment,false);
  }
 });
 check('no external script, stylesheet, image, font, frame or network fetch',()=>{
  assert(!/<(?:script|img|iframe|link)\b[^>]*(?:src|href)\s*=\s*["']https?:/i.test(html));
  assert(!/@import|fetch\s*\(|XMLHttpRequest|WebSocket|https?:\/\//.test(scripts[0][1]));
  assert(!/url\(\s*["']?https?:/i.test(html));
 });
 check('unknown monetary cost remains explicit',()=>{
  assert.equal(demo.data.costs.monetary_cost,null);
  assert.equal(demo.data.costs.human_active_attention_seconds,null);
  assert.equal(demo.data.summary.uniqueness_claim,false);
 });
 check('primary and economics state accurately follows embedded source availability',()=>{
  assert.equal(document.getElementById('primary-status').textContent,demo.translations.en[demo.data.primary.status==='available'?'measured':'notRun']);
  assert.equal(document.getElementById('economics-status').textContent,demo.translations.en[demo.data.economics.status==='available'?'modeled':'notRun']);
 });
 report.finished_utc=new Date().toISOString();report.passed=report.checks.every(c=>c.passed);
 report.environment={node:process.version,dom_mode:'purpose-built DOM harness running the unchanged embedded application JavaScript; no layout engine'};
 fs.writeFileSync(path.join(root,'qa_dom_report.json'),JSON.stringify(report,null,2)+'\n');
 fs.writeFileSync(path.join(root,'qa_downloaded_evidence.json'),JSON.stringify(downloaded,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
}
main().catch(error=>{report.finished_utc=new Date().toISOString();report.passed=false;report.error=error.stack;fs.writeFileSync(path.join(root,'qa_dom_report.json'),JSON.stringify(report,null,2)+'\n');console.error(error.stack);process.exitCode=1;});
