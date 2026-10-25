// SPDX-License-Identifier: Apache-2.0
export const SCHEMA='release-plan/v1';
export const LIMITS=Object.freeze({jobs:18,horizon:128,crew:4,astDepth:4});
export class WorkLimit extends Error{constructor(message='WORK_LIMIT'){super(message);this.name='WorkLimit';}}
export class Meter{
 constructor(limit=Infinity){this.limit=limit;this.spent=0;this.counts={};}
 tick(kind,n=1){if(!Number.isSafeInteger(n)||n<0)throw new Error('INVALID_CHARGE');if(this.spent+n>this.limit)throw new WorkLimit();this.spent+=n;this.counts[kind]=(this.counts[kind]||0)+n;}
 snapshot(){return {spent:this.spent,limit:Number.isFinite(this.limit)?this.limit:null,counts:{...this.counts}};}
}
const clone=x=>JSON.parse(JSON.stringify(x));
const lex=(a,b)=>a<b?-1:a>b?1:0;
const cmp=(a,b)=>lex(a.id,b.id);
function meteredStableSort(items,compare,meter,kind){
 // Explicit insertion sort keeps counted comparisons invariant across engine
 // versions and JIT tiers; native Array.sort comparison counts are not stable.
 for(let i=1;i<items.length;i++){const value=items[i];let j=i-1;while(j>=0){meter.tick(kind);if(compare(items[j],value)<=0)break;items[j+1]=items[j];meter.tick('strategy:sort-move');j--;}items[j+1]=value;}
 return items;
}
export function inspectTask(task,meter=new Meter()){
 if(!task||task.schema!==SCHEMA||typeof task.id!=='string'||!['plan','repair'].includes(task.kind))throw new Error('TASK_SCHEMA');
 const inputBytes=new TextEncoder().encode(JSON.stringify(task)).length;meter.tick('inspect:input-block64',Math.ceil(inputBytes/64));if(inputBytes>16000||task.id.length>128)throw new Error('TASK_INPUT_SIZE');
 if(!['synthetic','public'].includes(task.public_or_synthetic)||task.planning_only!==true)throw new Error('INPUT_RIGHTS_SCOPE');
 if(task.horizon!==undefined&&task.horizon!==task.capacity?.length)throw new Error('HORIZON_MISMATCH');
 if(!Array.isArray(task.jobs)||!task.jobs.length||task.jobs.length>LIMITS.jobs)throw new Error('JOB_SCOPE');
 if(!Array.isArray(task.capacity)||!task.capacity.length||task.capacity.length>LIMITS.horizon||task.capacity.some(x=>!Number.isSafeInteger(x)||x<0||x>LIMITS.crew))throw new Error('CAPACITY_SCOPE');
 if(task.jobs.some(j=>!j||typeof j!=='object'||!Array.isArray(j.deps)))throw new Error('JOB_SCHEMA');
 if(task.deadline!==undefined&&(!Number.isSafeInteger(task.deadline)||task.deadline<1||task.deadline>task.capacity.length))throw new Error('DEADLINE_SCOPE');
 if(task.movement_limit!==undefined&&(!Number.isSafeInteger(task.movement_limit)||task.movement_limit<0||task.movement_limit>LIMITS.jobs*LIMITS.horizon))throw new Error('MOVEMENT_SCOPE');
 const jobs=task.jobs.map(j=>({...j,deps:[...(j.deps||[])]})).sort(cmp),byId=new Map();
 for(const j of jobs){meter.tick('inspect:job');if(typeof j.id!=='string'||!/^J[1-9][0-9]{0,2}$/.test(j.id)||byId.has(j.id)||!Number.isSafeInteger(j.duration)||j.duration<1||j.duration>12||!Number.isSafeInteger(j.crew)||j.crew<1||j.crew>LIMITS.crew||!Array.isArray(j.deps)||new Set(j.deps).size!==j.deps.length)throw new Error('JOB_SCHEMA');byId.set(j.id,j);}
 const seen=new Set(),order=[];
 function visit(id,stack){meter.tick('inspect:edge');if(stack.has(id))throw new Error('DEPENDENCY_CYCLE');if(seen.has(id))return;const j=byId.get(id);if(!j)throw new Error('UNKNOWN_DEPENDENCY');const next=new Set(stack);next.add(id);for(const d of j.deps)visit(d,next);seen.add(id);order.push(id);}
 for(const j of jobs)visit(j.id,new Set());
 const release=Object.fromEntries(jobs.map(j=>[j.id,0]));for(const [id,t]of Object.entries(task.release||{})){meter.tick('inspect:release');if(!byId.has(id)||!Number.isSafeInteger(t)||t<0||t>=task.capacity.length)throw new Error('RELEASE_SCOPE');release[id]=t;}
 const locked={};for(const [id,t]of Object.entries(task.locked||{})){meter.tick('inspect:locked');if(!byId.has(id)||!Number.isSafeInteger(t)||t<release[id]||t+byId.get(id).duration>task.capacity.length)throw new Error('LOCK_SCOPE');locked[id]=t;}
 if(task.kind==='plan'&&Object.keys(locked).length)throw new Error('PLAN_HAS_LOCKS');
 for(const [id,t]of Object.entries(task.baseline||{})){meter.tick('inspect:baseline');if(!byId.has(id)||!Number.isSafeInteger(t)||t<0||t+byId.get(id).duration>task.capacity.length)throw new Error('BASELINE_SCOPE');}
 if(task.kind==='repair'&&(!task.baseline||Object.keys(task.baseline).length!==jobs.length))throw new Error('REPAIR_BASELINE_REQUIRED');
 if(task.kind==='plan'&&(task.baseline||task.movement_limit!==undefined))throw new Error('PLAN_HAS_REPAIR_INPUT');
 for(const [id,t]of Object.entries(locked))if(task.baseline[id]!==t)throw new Error('LOCK_BASELINE_MISMATCH');
 if(jobs.reduce((s,j)=>s+j.duration*j.crew,0)>task.capacity.reduce((a,b)=>a+b,0))throw new Error('INSUFFICIENT_TOTAL_CAPACITY');
 return {task,jobs,byId,order,release,locked,horizon:task.capacity.length};
}
export function features(model,meter){
 const cp={},work={},fanout={},earliest={},children=Object.fromEntries(model.jobs.map(j=>[j.id,[]]));
 for(const j of model.jobs)for(const p of j.deps){meter.tick('features:edge');children[p].push(j.id);}
 for(const id of model.order){const j=model.byId.get(id);earliest[id]=model.release[id];for(const p of j.deps){meter.tick('features:earliest');earliest[id]=Math.max(earliest[id],earliest[p]+model.byId.get(p).duration);}if(id in model.locked){if(model.locked[id]<earliest[id])throw new Error('LOCK_PRECEDENCE_CONFLICT');earliest[id]=model.locked[id];}}
 for(const id of [...model.order].reverse()){
  const j=model.byId.get(id),desc=new Set();let tail=0;
  for(const c of children[id]){meter.tick('features:critical');tail=Math.max(tail,cp[c]);desc.add(c);for(const z of fanout[c]){meter.tick('features:descendant');desc.add(z);}}
  cp[id]=j.duration+tail;fanout[id]=desc;work[id]=j.duration*j.crew;for(const x of desc){meter.tick('features:work');const k=model.byId.get(x);work[id]+=k.duration*k.crew;}
 }
 return {cp,work,fanout:Object.fromEntries(Object.entries(fanout).map(([k,v])=>[k,v.size])),earliest};
}
export function lowerBound(model,meter=new Meter()){
 const f=features(model,meter);let critical=0,total=0,locked=0;
 for(const j of model.jobs){meter.tick('bound:job');critical=Math.max(critical,f.earliest[j.id]+j.duration);total+=j.duration*j.crew;if(j.id in model.locked)locked=Math.max(locked,model.locked[j.id]+j.duration);}
 let accumulated=0,load=model.horizon+1;
 for(let t=0;t<model.horizon;t++){meter.tick('bound:capacity');accumulated+=model.task.capacity[t];if(accumulated>=total){load=t+1;break;}}
 return {value:Math.max(critical,load,locked),critical,load,locked};
}
export const SPECIALISTS=Object.freeze([
 {kind:'dispatch',name:'critical-path',weights:{cp:1}},
 {kind:'dispatch',name:'longest-first',weights:{duration:1}},
 {kind:'dispatch',name:'shortest-first',weights:{duration:-1}},
 {kind:'dispatch',name:'descendant-work',weights:{work:1}},
 {kind:'dispatch',name:'critical-resource',weights:{cp:4,work:1,duration:2}},
]);
export function inspectStrategy(ast,depth=0){
 if(!ast||depth>LIMITS.astDepth)throw new Error('STRATEGY_SCOPE');
 if(depth===0&&new TextEncoder().encode(JSON.stringify(ast)).length>4096)throw new Error('STRATEGY_INPUT_SIZE');
 if(ast.kind==='dispatch'){
  if(!ast.weights||typeof ast.weights!=='object'||!Object.keys(ast.weights).length||Object.keys(ast.weights).some(k=>!['cp','work','duration','fanout','earliest','crew'].includes(k))||Object.values(ast.weights).some(v=>!Number.isFinite(v)||Math.abs(v)>8))throw new Error('STRATEGY_WEIGHTS');
 }else if(ast.kind==='lookahead'){
  if(!Number.isSafeInteger(ast.width)||ast.width<2||ast.width>4||!Number.isSafeInteger(ast.steps)||ast.steps<1||ast.steps>18||!['always','contention'].includes(ast.trigger))throw new Error('LOOKAHEAD_SCOPE');inspectStrategy(ast.base,depth+1);if(ast.base.kind!=='dispatch')throw new Error('LOOKAHEAD_BASE');
 }else if(ast.kind==='repair'){
  if(!['stable','quality','selective'].includes(ast.mode)||![0,1,2].includes(ast.stability)||!['dispatch','lookahead'].includes(ast.base?.kind))throw new Error('REPAIR_SCOPE');inspectStrategy(ast.base,depth+1);
 }else throw new Error('UNKNOWN_STRATEGY');
 return true;
}
function initialState(model,meter){
 const scheduled={},usage=Array(model.horizon).fill(0);
 for(const [id,start]of Object.entries(model.locked)){const j=model.byId.get(id);scheduled[id]={id,start,end:start+j.duration};for(let t=start;t<start+j.duration;t++){meter.tick('schedule:lock-slot');usage[t]+=j.crew;if(usage[t]>model.task.capacity[t])throw new Error('LOCK_CAPACITY_CONFLICT');}}
 for(const [id,slot]of Object.entries(scheduled))for(const p of model.byId.get(id).deps){meter.tick('schedule:lock-dependency');if(!scheduled[p]||scheduled[p].end>slot.start)throw new Error('LOCK_PREFIX_NOT_CLOSED');}
 return {scheduled,usage,order:[]};
}
function ready(model,state,meter){const out=[];for(const j of model.jobs){meter.tick('schedule:ready-job');if(state.scheduled[j.id])continue;let ok=true;for(const p of j.deps){meter.tick('schedule:ready-edge');if(!state.scheduled[p]){ok=false;break;}}if(ok)out.push(j);}return out;}
function earliestSlot(model,state,j,meter){
 let start=model.release[j.id];for(const p of j.deps){meter.tick('schedule:dependency-time');start=Math.max(start,state.scheduled[p].end);}
 for(let s=start;s+j.duration<=model.horizon;s++){
  meter.tick('schedule:start-trial');let ok=true;
  for(let t=s;t<s+j.duration;t++){meter.tick('schedule:capacity-slot');if(state.usage[t]+j.crew>model.task.capacity[t]){ok=false;break;}}
  if(ok)return s;
 }
 throw new Error('NO_FEASIBLE_INSERTION');
}
function place(model,state,j,meter){const start=earliestSlot(model,state,j,meter);state.scheduled[j.id]={id:j.id,start,end:start+j.duration};state.order.push(j.id);for(let t=start;t<start+j.duration;t++){meter.tick('schedule:commit-slot');state.usage[t]+=j.crew;}}
function score(j,f,weights,meter){let s=0;for(const [key,value]of Object.entries(weights)){meter.tick('strategy:score-term');const x=key==='duration'||key==='crew'?j[key]:f[key][j.id];s+=value*x;}return s;}
function baseOf(ast){return ast.kind==='dispatch'?ast:baseOf(ast.base);}
function ranked(model,state,f,ast,meter){
 const base=baseOf(ast),items=ready(model,state,meter).map(j=>({j,score:score(j,f,base.weights,meter)}));
 meteredStableSort(items,(a,b)=>b.score-a.score||lex(a.j.id,b.j.id),meter,'strategy:priority-compare');return items.map(x=>x.j);
}
function objective(model,state){const makespan=Math.max(0,...Object.values(state.scheduled).map(j=>j.end));let movement=0;for(const j of Object.values(state.scheduled))if(model.task.baseline?.[j.id]!==undefined)movement+=Math.abs(j.start-model.task.baseline[j.id]);return {makespan,movement};}
function finishDispatch(model,state,f,ast,meter){while(Object.keys(state.scheduled).length<model.jobs.length){const list=ranked(model,state,f,ast,meter);if(!list.length)throw new Error('NO_READY_JOB');place(model,state,list[0],meter);}return state;}
function compareOut(a,b,model,repair){
 if(repair&&model.task.deadline!==undefined){const aq=a.makespan<=model.task.deadline,bq=b.makespan<=model.task.deadline;if(aq!==bq)return aq?-1:1;if(aq)return a.movement-b.movement||a.makespan-b.makespan;}
 return a.makespan-b.makespan||(repair?a.movement-b.movement:0);
}
function shouldRollout(model,state,list,ast,meter){
 if(ast.trigger==='always')return true;
 let crew=0;for(const j of list){meter.tick('strategy:contention');crew+=j.crew;}return crew>Math.max(...model.task.capacity);
}
export function plan(task,strategy,meter=new Meter()){
 inspectStrategy(strategy);const model=inspectTask(task,meter);if((strategy.kind==='repair')!==(task.kind==='repair'))throw new Error('STRATEGY_APPLICABILITY');
 if(strategy.kind==='repair')meter.tick('strategy:repair-policy-entry');
 if(strategy.kind==='repair'&&strategy.mode==='selective'){
  const stable=plan(task,{...strategy,mode:'stable',stability:2},meter);
  // A bounded selective repair asks the inherited policy for a second plan only
  // when preserving the old ordering misses the current user's target.
  if(qualifies(task,stable))return {...stable,repair_mode:'selective:stable'};
  const quality=plan(task,{...strategy,mode:'quality',stability:0},meter);
  const selected=compareOut(stable,quality,model,true)<=0?stable:quality;
  return {...selected,repair_mode:selected===stable?'selective:stable':'selective:quality'};
 }
 const f=features(model,meter),bound=lowerBound(model,meter),state=initialState(model,meter);let ast=strategy.kind==='repair'?strategy.base:strategy,lookaheadSteps=0;
 while(Object.keys(state.scheduled).length<model.jobs.length){
  const list=ranked(model,state,f,ast,meter);if(!list.length)throw new Error('NO_READY_JOB');let chosen=list[0];
  if(ast.kind==='lookahead'&&strategy.mode!=='stable'&&lookaheadSteps<ast.steps&&list.length>1&&shouldRollout(model,state,list,ast,meter)){
   if(strategy.kind==='repair')meter.tick('strategy:inherited-lookahead-decision');
   let best=null;for(const j of list.slice(0,ast.width)){
    meter.tick('strategy:rollout');const trial=clone(state);meter.tick('strategy:state-copy',model.horizon+Object.keys(state.scheduled).length);
    try{place(model,trial,j,meter);meter.tick('strategy:inherited-dispatch-rollout');finishDispatch(model,trial,f,ast.base,meter);const q=objective(model,trial);if(!best||compareOut(q,best.q,model,strategy.kind==='repair')<0){best={j,q};}if(q.makespan===bound.value&&strategy.kind!=='repair')break;}catch(e){if(e instanceof WorkLimit)throw e;}
   }
   if(best)chosen=best.j;lookaheadSteps++;
  }
  if(strategy.kind==='repair'&&strategy.mode==='stable'&&strategy.stability>0&&model.task.baseline){
   const head=list.slice(0,Math.min(list.length,1+strategy.stability));meteredStableSort(head,(a,b)=>(model.task.baseline[a.id]??Infinity)-(model.task.baseline[b.id]??Infinity)||lex(a.id,b.id),meter,'strategy:stability-compare');chosen=head[0];
  }
  place(model,state,chosen,meter);
 }
 const q=objective(model,state),schedule=Object.values(state.scheduled).sort((a,b)=>a.start-b.start||lex(a.id,b.id));
 return {schema:'release-plan-result/v1',task_id:task.id,schedule,makespan:q.makespan,movement:q.movement,lower_bound:bound,optimal_by_lower_bound:q.makespan===bound.value,dispatch_order:state.order,lookahead_steps:lookaheadSteps,proof:[],authority:[]};
}
export function qualifies(task,result){return Boolean(result&&result.makespan<=(task.deadline??task.capacity.length)&&(task.movement_limit===undefined||result.movement<=task.movement_limit));}
export function verifyLocal(task,result,meter=new Meter()){
 const m=inspectTask(task,meter);if(result?.schema!=='release-plan-result/v1'||result.task_id!==task.id||!Array.isArray(result.schedule)||result.schedule.length!==m.jobs.length)throw new Error('RESULT_SCHEMA');
 const byId=new Map(),usage=Array(m.horizon).fill(0);for(const j of result.schedule){meter.tick('verify:job');const spec=m.byId.get(j.id);if(!spec||byId.has(j.id)||!Number.isSafeInteger(j.start)||!Number.isSafeInteger(j.end)||j.start<m.release[j.id]||j.end!==j.start+spec.duration||j.end>m.horizon||(j.id in m.locked&&j.start!==m.locked[j.id]))throw new Error('INVALID_JOB_RESULT');byId.set(j.id,j);for(let t=j.start;t<j.end;t++){meter.tick('verify:slot');usage[t]+=spec.crew;if(usage[t]>m.task.capacity[t])throw new Error('CAPACITY_VIOLATION');}}
 for(const j of m.jobs)for(const p of j.deps){meter.tick('verify:dependency');if(byId.get(p).end>byId.get(j.id).start)throw new Error('DEPENDENCY_VIOLATION');}
 let movement=0;for(const j of result.schedule){meter.tick('verify:movement');if(task.baseline?.[j.id]!==undefined)movement+=Math.abs(j.start-task.baseline[j.id]);}
 const bound=lowerBound(m,meter);if(result.makespan!==Math.max(...result.schedule.map(j=>j.end))||result.movement!==movement||result.lower_bound?.value!==bound.value||result.optimal_by_lower_bound!==(result.makespan===bound.value)||!Array.isArray(result.proof)||result.proof.length||!Array.isArray(result.authority)||result.authority.length)throw new Error('FALSE_RESULT_CLAIM');
 return {valid:true,qualified:qualifies(task,result),lower_bound:bound.value,optimal_by_lower_bound:result.optimal_by_lower_bound,proof:[],authority:[]};
}
export function specialistMethods(kind){return kind==='repair'?[{kind:'repair',name:'preserve-order',mode:'stable',stability:2,base:clone(SPECIALISTS[0])},...SPECIALISTS.map(base=>({kind:'repair',name:base.name,mode:'quality',stability:0,base:clone(base)}))]:SPECIALISTS;}
export function portfolio(task,meter=new Meter(),methods=null,{stopOnQualified=false}={}){let best=null;const attempts=[];for(const raw of methods??specialistMethods(task.kind)){const method=task.kind==='repair'&&raw.kind!=='repair'?{kind:'repair',mode:'quality',stability:0,base:raw}:raw;const before=meter.spent;try{const result=plan(task,method,meter);attempts.push({method:raw.name||raw.kind,work:meter.spent-before,makespan:result.makespan,qualified:qualifies(task,result)});if(!best||compareOut(result,best.result,{task},task.kind==='repair')<0)best={method,result};if((stopOnQualified&&qualifies(task,result))||(result.optimal_by_lower_bound&&(task.movement_limit===undefined||qualifies(task,result))))break;}catch(e){if(e instanceof WorkLimit){attempts.push({method:raw.name||raw.kind,work:meter.spent-before,error:e.message});if(best)return {...best,attempts,search_stopped:'WORK_LIMIT'};throw e;}attempts.push({method:raw.name||raw.kind,work:meter.spent-before,error:e.message});}}if(!best)throw new Error('NO_FEASIBLE_PORTFOLIO');return {...best,attempts};}
export function candidateDispatches(){const candidates=[...SPECIALISTS.map(clone)];for(const cp of [-4,0,4,8])for(const work of [0,1,4])for(const duration of [-4,0,4])if(cp||work||duration)candidates.push({kind:'dispatch',name:`learned-${cp}-${work}-${duration}`,weights:Object.fromEntries(Object.entries({cp,work,duration}).filter(([,v])=>v))});return candidates;}
export function constructLookaheads(parent){inspectStrategy(parent);if(parent.kind!=='dispatch')throw new Error('DISPATCH_PARENT_REQUIRED');return [1,3,18].flatMap(steps=>[2,4].map(width=>({kind:'lookahead',base:clone(parent),width,steps,trigger:'contention'})));}
export function constructRepairs(parent){inspectStrategy(parent);if(!['dispatch','lookahead'].includes(parent.kind))throw new Error('REPAIR_PARENT_REQUIRED');return ['quality','stable','selective'].map(mode=>({kind:'repair',base:clone(parent),mode,stability:mode==='stable'?2:0}));}
