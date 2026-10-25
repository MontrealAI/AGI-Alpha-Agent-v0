// SPDX-License-Identifier: Apache-2.0
// UI component regressions with simulated API responses; no executor or research run.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import vm from 'node:vm';
import {resolve} from 'node:path';
const staticRoot=resolve(process.argv[2]??'transport/static');
const source=readFileSync(resolve(staticRoot,'strategy.js'),'utf8');
const html=readFileSync(resolve(staticRoot,'strategy.html'),'utf8');
class Element{
 constructor(){this.children=[];this.dataset={};this.value='';this.textContent='';this.hidden=false;this.disabled=false;this.checked=false;this.events={};this.classList={toggle(){},remove(){}};}
 addEventListener(name,callback){this.events[name]=callback;}
 async trigger(name){return this.events[name]?.({preventDefault(){}});}
 replaceChildren(...nodes){this.children=[...nodes];}
 append(...nodes){this.children.push(...nodes);}
 setAttribute(name,value){this[name]=value;}
 click(){}
}
const makePlan=(id,state,time,input)=>({plan_id:id,plan_digest:'digest-'+id,request_id:'request-'+id,state,prepared_at:time,expires_at:Date.now()/1000+1000,request_seconds:60,executor_id:'test-fixed',source_hash:'a'.repeat(64),method:'run-journey',caps:{service_work:10,improvement_work:10,native_calls:0,native_solve_seconds:0},input,...(state==='completed'?{outcome_hash:'outcome-'+id,outcome:{result:{phases:[],capabilities:{parent:{method:'test-only',proof:[],authority:[]}}},verified:true}}:{})});
function page(plans){
 const elements=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(x=>[x[1],new Element()]));
 const calls=[],downloads=[];const status={state:'ready',source_available:true,source_hash:'a'.repeat(64),executor_id:'test-fixed',plans,spent:{},reserved:{},total:{},active_after_browser_close:false};
 const context=vm.createContext({console,Intl,Date,JSON,Object,Array,String,Error,URLSearchParams,location:{search:''},TextEncoder,TextDecoder,crypto:{randomUUID:()=> 'new-request'},Blob:class{constructor(parts){this.parts=parts;}},URL:{createObjectURL(blob){downloads.push(blob.parts.join(''));return 'blob:test';},revokeObjectURL(){}},setTimeout(){},setInterval(){return 1;},clearInterval(){},document:{documentElement:{},getElementById:id=>{if(!elements[id])throw Error('Missing UI id '+id);return elements[id];},createElement:()=>new Element(),querySelector:()=>new Element(),querySelectorAll:()=>[]},fetch:async(url,options)=>{
  const action=url.replace('/api/strategy-executor/','');const body=options.body?JSON.parse(options.body):undefined;calls.push({action,body});let result=status;
  if(action==='approve'){result=status.plans[body.plan_id];assert.equal(body.plan_digest,result.plan_digest);result={...result,state:'approved'};status.plans[body.plan_id]=result;}
  if(action==='run'){const original=status.plans[body.plan_id];assert.equal(original.state,'approved');assert.equal(body.plan_digest,original.plan_digest);result={...original,state:'completed',outcome_hash:'new-outcome',outcome:{result:{phases:[]},verified:true}};status.plans[body.plan_id]=result;}
  if(action==='prepare'){result=makePlan('new-plan','prepared',300,body.input);status.plans[result.plan_id]=result;}
  if(action.startsWith('export/'))result={body:{plan:status.plans[action.split('/')[1]]},signature:'test-only'};
  return {ok:true,json:async()=>structuredClone(result)};
 }});
 vm.runInContext(source,context,{filename:resolve(staticRoot,'strategy.js')});
 return {elements,context,calls,downloads,status,connect:async()=>{elements.token.value='memory-only-test-token';await elements['connect-form'].trigger('submit');}};
}
const completed=makePlan('old','completed',100,{initial:{id:'old-goal'}});
const approved=makePlan('new','approved',200,{initial:{id:'approved-goal'}});
const first=page({old:completed,new:approved});await first.connect();
assert.equal(first.elements['mission-select'].value,'new');assert.equal(first.elements['approved-input'].textContent,JSON.stringify(approved.input,null,2));assert.equal(first.elements.approve.disabled,true);assert.equal(first.calls.filter(x=>['approve','run'].includes(x.action)).length,0);
first.elements.consent.checked=true;await first.elements.consent.trigger('change');assert.equal(first.elements.approve.textContent,'Resume approved work');assert.equal(first.elements.approve.disabled,false);await first.elements.approve.trigger('click');assert.equal(first.calls.filter(x=>x.action==='approve').length,0);assert.equal(first.calls.filter(x=>x.action==='run').length,1);assert.equal(first.elements.consent.checked,false);
first.elements['mission-select'].value='old';await first.elements['mission-select'].trigger('change');assert.equal(first.elements.export.disabled,false);assert.equal(vm.runInContext('currentPlan.plan_id',first.context),'old');await first.elements.export.trigger('click');assert.equal(first.calls.at(-1).action,'export/old');assert(!first.downloads.at(-1).includes('memory-only-test-token'));
const second=page(first.status.plans);await second.connect();assert.equal(second.elements['mission-select'].value,'new');assert.equal(second.elements.export.disabled,false);assert.equal(second.calls.filter(x=>['approve','run'].includes(x.action)).length,0);
for(const state of ['running','unknown','reconciled']){const p=page({one:makePlan('one',state,1,{initial:{id:'uncertain'}})});await p.connect();p.elements.consent.checked=true;await p.elements.consent.trigger('change');assert.equal(p.elements.approve.disabled,true);await p.elements.approve.trigger('click');assert.equal(p.calls.filter(x=>['approve','run'].includes(x.action)).length,0);assert.equal(p.elements.export.disabled,false);}
const fresh=page({});await fresh.connect();const freshInput=JSON.parse(vm.runInContext('JSON.stringify(SAMPLE)',fresh.context));freshInput.initial.id='captured-original';fresh.elements.input.value=JSON.stringify(freshInput);await fresh.elements.prepare.trigger('click');const captured=fresh.elements['approved-input'].textContent;fresh.elements.input.value=JSON.stringify({initial:{id:'edited-later'}});assert.equal(fresh.elements['approved-input'].textContent,captured);assert(captured.includes('captured-original'));fresh.elements.consent.checked=true;await fresh.elements.consent.trigger('change');await fresh.elements.approve.trigger('click');assert.equal(fresh.calls.filter(x=>x.action==='approve').length,1);assert.equal(fresh.calls.filter(x=>x.action==='run').length,1);assert.equal(fresh.status.plans['new-plan'].input.initial.id,'captured-original');
const reconnect=page({one:approved});await reconnect.connect();reconnect.elements.consent.checked=true;await reconnect.elements.consent.trigger('change');await reconnect.elements.disconnect.trigger('click');assert.equal(vm.runInContext('token',reconnect.context),'');await reconnect.connect();assert.equal(reconnect.elements.consent.checked,false);assert.equal(reconnect.elements.approve.disabled,true);
assert(!source.includes('localStorage')&&!source.includes('sessionStorage')&&!source.includes('indexedDB'));assert(!source.includes("scope:'ordinary'"));assert(html.includes('Exact mission input for this plan'));
const actual=JSON.parse(readFileSync(resolve('acceptance-public/integrated-journey.json'),'utf8'));
const summaryPage=page({});summaryPage.context.fixture=actual;vm.runInContext('renderOutcome(fixture)',summaryPage.context);
const nodeText=node=>node.textContent+' '+node.children.map(nodeText).join(' ');
const mainText=nodeText(summaryPage.elements.results);
assert(mainText.includes('3 candidate methods retained for inspection; 0 admitted for active use.'));
assert(mainText.includes('Hold — full cost is unknown'));
assert(mainText.includes('Inherited parent')&&mainText.includes('Rebuilt parent')&&mainText.includes('Equivalent reuse'));
for(const comparison of actual.outcome.result.inheritance.diagnostics)for(const arm of comparison.arms)assert(mainText.includes(new Intl.NumberFormat('en').format(arm.total_work)));
assert(mainText.includes('tied the strongest current specialist'));
assert(mainText.includes('Existing specialist portfolio'));
assert(!mainText.includes('"lifecycle_costs"')&&!mainText.includes('"authority"'));
assert(mainText.length<9000);
assert(summaryPage.elements.raw.textContent.includes('"lifecycle_costs"')&&summaryPage.elements.raw.textContent.includes('"authority"'));
// Preliminary input feedback must not reserve work, approve or run a bad request.
const badInput=page({});await badInput.connect();badInput.elements.input.value='{}';await badInput.elements.prepare.trigger('click');assert.equal(badInput.calls.filter(x=>['prepare','approve','run'].includes(x.action)).length,0);assert.equal(badInput.elements.error.hidden,false);
const cyclic=JSON.parse(vm.runInContext('JSON.stringify(SAMPLE)',badInput.context));cyclic.initial.jobs[0].deps=['J6'];badInput.elements.input.value=JSON.stringify(cyclic);await badInput.elements.prepare.trigger('click');assert.equal(badInput.calls.filter(x=>['prepare','approve','run'].includes(x.action)).length,0);assert(badInput.elements.error.textContent.includes('acyclic dependencies'));
// A rejected or nonplanning outcome must never become a qualified planning report.
const reports=page({});reports.context.rejected={...makePlan('rejected-report','rejected',1,{}),outcome_hash:'failed-outcome',outcome:{verified:false,costs:{service_work:2,improvement_work:0,native_calls:0,native_solve_seconds:0,unknown_costs:['unmeasured']},result:{phases:[{verified:false,qualified:false,result:{schedule:[],makespan:null,movement:null},receipt_hash:'unverified-receipt',selected_method:null}]}}};
const rejectedReport=vm.runInContext('readableReport(rejected)',reports.context);assert(rejectedReport.includes('State: Rejected'));assert(rejectedReport.includes('not verified — review required'));assert(rejectedReport.includes('Phase verification: not verified'));assert(rejectedReport.includes('Review required'));assert(!rejectedReport.includes(' · Qualified'));assert(rejectedReport.includes('ALLOWANCE')&&rejectedReport.includes('not measured CPU or wall time'));assert(rejectedReport.includes('costs remain unknown'));
reports.context.construct={...reports.context.rejected,method:'construct',outcome:{verified:false,result:{decision:'HOLD'},costs:{}}};const constructionReport=vm.runInContext('readableReport(construct)',reports.context);assert(constructionReport.includes('Method: Method construction'));assert(constructionReport.includes('No planning schedules are present'));assert(constructionReport.includes('complete capability record'));assert(constructionReport.includes('not verified — review required'));
const uncertain=page({one:makePlan('one','running',1,{initial:{id:'older-run'}})});uncertain.status.active_after_browser_close=null;uncertain.status.execution_observation='awaiting-evidence';await uncertain.connect();assert.equal(uncertain.elements.background.textContent,'Executor cannot confirm whether earlier work finished. Inspect retained evidence; do not retry uncertain work.');assert(!uncertain.elements.background.textContent.includes('no active request'));assert.equal(uncertain.calls.filter(x=>['run','approve'].includes(x.action)).length,0);uncertain.status.active_after_browser_close=true;uncertain.status.execution_observation='running-in-this-executor';await uncertain.elements.review.trigger('click');await new Promise(resolve=>setImmediate(resolve));assert(uncertain.elements.background.textContent.includes('A bounded request is active'));uncertain.status.active_after_browser_close=false;uncertain.status.execution_observation='idle';await uncertain.elements.review.trigger('click');await new Promise(resolve=>setImmediate(resolve));assert(uncertain.elements.background.textContent.includes('no active request'));
console.log(JSON.stringify({scope:'Component tests with simulated API and recorded engineering artifact rendering only; no browser/executor/scientific acceptance.',checks:18,passed:true,main_summary_characters:mainText.length,full_record_characters:summaryPage.elements.raw.textContent.length,covered:['retained newest selection','immutable input review','fresh consent','approved exact resume without reapproval','completed selection/export','fresh-page history restoration','running/unknown/reconciled no retry','prepared approve then run','editor cannot change prepared input','disconnect clears token','reconnect clears consent','no browser storage and strict sample fields','concise actual outcome summaries with complete raw evidence retained','observed active vs uncertain retained run vs idle wording','unverified rejected report preserves failed verification and unknown costs','nonplanning report has no schedule or qualified-plan claim','invalid input receives feedback without preparation or authority','cyclic input cannot create a prepared request']}));
