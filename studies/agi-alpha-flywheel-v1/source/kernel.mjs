// SPDX-License-Identifier: Apache-2.0
import {createWorkbench,example} from './vendor/examples/successor-workbench/engine.mjs';
import {canonical,digest} from './vendor/docs/assets/successor/engine.mjs';
import {validateDocument,evaluate,runComparison} from './vendor/docs/assets/transformational-intelligence/source-understanding.mjs';

export const METHODS=['lead-order','weighted-without-dependencies','audit-after-draft','dependency-graph-before-compression'];
export const ARMS=['flywheel','cache','frozen','expert'];
export const STAGES=['Identify','Out-Learn','Out-Think','Out-Design','Out-Strategise','Out-Execute','Out-Evolve'];
export const COST_CATEGORIES=['construction','qualification','execution','validation','routing','retention','maintenance','runtime'];
const clone=value=>JSON.parse(JSON.stringify(value));
const bytes=value=>new TextEncoder().encode(typeof value==='string'?value:canonical(value)).length;
const now=()=>globalThis.performance.now();
const edges=doc=>doc.claims.reduce((n,c)=>n+c.depends_on.length,0);
const fact=(n,k)=>{let v=1;for(let i=1;i<=k;i++)v=v*(n-i+1)/i;return Math.round(v);};
const subsets=(n,k)=>Array.from({length:Math.min(n,k)+1},(_,i)=>fact(n,i)).reduce((a,b)=>a+b,0);
export function comparisonUnits(doc,k){const n=doc.claims.length,e=edges(doc);return n*2**n+subsets(n,k)*(n+e+1)+5*n+2*e;}
export class Exhausted extends Error {constructor(){super('BUDGET_EXHAUSTED');this.code='BUDGET_EXHAUSTED';}}
export class Meter {
  constructor(limit,spent=0){this.limit=limit;this.spent=spent;this.counts=Object.fromEntries(COST_CATEGORIES.map(k=>[k,0]));this.events=[];}
  charge(category,units,operation){if(!Number.isSafeInteger(units)||units<0)throw Error('COST_INVALID');if(this.spent+units>this.limit){const error=new Exhausted();error.denied_charge={category,units,operation,cumulative:this.spent,limit:this.limit,status:'refused-not-spent'};throw error;}this.spent+=units;this.counts[category]+=units;this.events.push({category,units,operation,cumulative:this.spent});}
}
function walk(doc,id){const seen=new Set(),todo=[id],map=new Map(doc.claims.map(c=>[c.id,c]));while(todo.length){const next=todo.pop();if(seen.has(next))continue;seen.add(next);todo.push(...map.get(next).depends_on);}return seen;}
function score(doc,ids,meter,category){meter.charge(category,doc.claims.length+edges(doc)+1,'structural-evaluation');return evaluate(doc,ids);}
function better(a,b){return !b||a.structural_score>b.structural_score||(a.structural_score===b.structural_score&&(a.selected.length<b.selected.length||(a.selected.length===b.selected.length&&a.selected.join(',')<b.selected.join(','))));}
export function selectOne(document,method,k,meter=new Meter(1_000_000),category='execution'){
  if(!METHODS.includes(method)||!Number.isInteger(k)||k<1||k>3)throw Error('PROGRAM_OR_CAP_INVALID');
  const doc=validateDocument(document),claims=doc.claims,n=claims.length;
  meter.charge(category,n+edges(doc)+Math.ceil(bytes(doc)/1024),'read-validated-source');
  const max=Math.min(k,n);
  if(method==='lead-order')return score(doc,claims.slice(0,max).map(c=>c.id),meter,category);
  if(method==='dependency-graph-before-compression'){
    let best;
    for(let mask=0;mask<2**n;mask++){
      meter.charge(category,n,'mask-claim-visits');
      const ids=claims.filter((_,i)=>mask&2**i).map(c=>c.id);
      if(ids.length>max)continue;
      const item=score(doc,ids,meter,category);
      if(!item.missing.length&&better(item,best))best=item;
    }
    return best;
  }
  const ranked=[...claims].sort((a,b)=>{meter.charge(category,1,'rank-comparison');return b.weight-a.weight||claims.indexOf(a)-claims.indexOf(b);});
  if(method==='weighted-without-dependencies')return score(doc,ranked.slice(0,max).map(c=>c.id),meter,category);
  let selected=new Set(ranked.slice(0,max).map(c=>c.id));
  for(const id of [...selected]){meter.charge(category,n+edges(doc),'audit-prerequisites');if([...walk(doc,id)].some(dep=>!selected.has(dep)))selected.delete(id);}
  for(const c of ranked){meter.charge(category,n+edges(doc),'audit-fill');const proposed=new Set([...selected,...walk(doc,c.id)]);if(proposed.size<=max)selected=proposed;}
  return score(doc,[...selected],meter,category);
}
function compare(doc,k,meter,category){meter.charge(category,comparisonUnits(doc,k),'released-all-five-comparison');return runComparison(doc,k);}
function methodScope(method){return method==='weighted-without-dependencies'?'independent-clauses':method==='lead-order'?'ordered-independent':'acyclic-graph';}
const capabilityBody=item=>Object.fromEntries(['schema','method','scope','sourceHash','created_epoch','proof','authority','reuse'].map(key=>[key,item[key]]));
export async function verifyCapability(item){if(item.schema!=='flywheel-capability/v1'||!METHODS.includes(item.method)||item.scope!==methodScope(item.method)||!Number.isInteger(item.created_epoch)||item.created_epoch<0||!Array.isArray(item.proof)||item.proof.length||!Array.isArray(item.authority)||item.authority.length||item.reuse!=='Fresh result checks remain required.'||item.digest!==await digest('flywheel-capability',capabilityBody(item)))throw Error('CAPABILITY_BINDING');return clone(item);}
function applicable(item,doc){if(item.scope==='acyclic-graph')return true;if(edges(doc))return false;if(item.scope==='independent-clauses')return true;return doc.claims.every((c,i)=>!i||doc.claims[i-1].weight>=c.weight);}
function chooseInherited(retained,doc,meter){meter.charge('routing',doc.claims.length+edges(doc)+retained.length,'route-current-requirement');const eligible=retained.filter(item=>applicable(item,doc));return eligible.sort((a,b)=>METHODS.indexOf(a.method)-METHODS.indexOf(b.method))[0]?.method||'lead-order';}
function expert(doc,meter){meter.charge('routing',doc.claims.length+edges(doc),'authored-structural-rule');return edges(doc)?'dependency-graph-before-compression':'weighted-without-dependencies';}
function checkInput(input){
  if(!input||!ARMS.includes(input.arm)||!Number.isInteger(input.stream)||!Number.isInteger(input.epoch)||!Number.isInteger(input.budget)||input.budget<1||input.budget>2_000_000||!Number.isInteger(input.spent)||input.spent<0||input.spent>input.budget)throw Error('STUDY_INPUT');
  if(!Number.isInteger(input.max_clauses)||input.max_clauses<1||input.max_clauses>3||!Array.isArray(input.retained)||input.retained.length>2)throw Error('STUDY_BOUNDS');
  for(const group of ['development','qualification','missions']){if(!Array.isArray(input[group])||input[group].length<1||input[group].length>6)throw Error('TASK_BOUNDS');input[group].forEach(validateDocument);}
  if(input.retained.some(x=>!METHODS.includes(x.method)||typeof x.digest!=='string'||x.authority?.length||x.proof?.length))throw Error('CAPABILITY_INPUT');
  if(typeof input.sourceHash!=='string'||!/^[a-f0-9]{64}$/.test(input.sourceHash))throw Error('SOURCE_BINDING');
}

export const adapter={
  manifest:{id:'flywheel-source-study',version:1,en:'Build a reusable source selector',fr:'Construire une méthode réutilisable',scope:'Finite synthetic annotated source-graph work; structural support only; no current proof or external authority.',artifact:'capability.json'},
  validate:checkInput,
  async execute(input,checkpoint){
    const meter=new Meter(input.budget,input.spent),trace=[],attempts=[],observations=[],retired=[];
    let retained=clone(input.retained),selected='lead-order',incumbent='lead-order',proposed='lead-order',decision='RETAIN_INCUMBENT',failure=null,deniedCharge=null;
    const stage=async name=>{trace.push({stage:name,cumulative_units:meter.spent});await checkpoint(name);};
    try {
      meter.charge('runtime',1,'released-workbench-invocation');
      await stage('Identify');
      meter.charge('maintenance',Math.ceil(bytes(retained)/1024)+retained.length,'inspect-retained-bytes-and-scope');
      for(const item of retained)await verifyCapability(item);
      for(const item of retained){if(item.sourceHash!==input.sourceHash){retired.push({...item,reason:'source-version-changed'});}}
      retained=retained.filter(x=>x.sourceHash===input.sourceHash);
      incumbent=chooseInherited(retained,input.development[0],meter);
      await stage('Out-Learn');
      if(input.arm==='flywheel'||input.arm==='cache'){
        const comparisons=input.development.map(doc=>compare(doc,input.max_clauses,meter,'construction'));
        const reusable=retained.find(x=>x.method===incumbent)&&comparisons.every(value=>{
          const old=value.methods.find(x=>x.method===incumbent),best=value.methods.find(x=>x.method==='dependency-graph-before-compression');
          return !old.missing.length&&old.structural_score===best.structural_score;
        });
        if(reusable){proposed=incumbent;attempts.push({method:incumbent,status:'reused-qualified',construction_skipped:true});}
        else{
          const totals=Object.fromEntries(METHODS.map(m=>[m,{score:0,missing:0,units:0}]));
          for(let index=0;index<input.development.length;index++){
            const doc=input.development[index],comparison=comparisons[index];
            for(const method of METHODS){const value=comparison.methods.find(x=>x.method===method);totals[method].score+=value.structural_score;totals[method].missing+=value.missing.length;const before=meter.spent;selectOne(doc,method,input.max_clauses,meter,'construction');totals[method].units+=meter.spent-before;}
          }
          for(const method of METHODS)attempts.push({method,...totals[method],status:totals[method].missing?'rejected-unsupported':'eligible'});
          const valid=attempts.filter(x=>x.status==='eligible').sort((a,b)=>b.score-a.score||a.units-b.units||METHODS.indexOf(a.method)-METHODS.indexOf(b.method));
          proposed=valid[0]?.method||incumbent;
        }
      }else proposed=input.arm==='expert'?expert(input.development[0],meter):'lead-order';
      await stage('Out-Think');
      const oldCandidate=retained.find(x=>x.method===proposed&&x.sourceHash===input.sourceHash);
      const candidate=oldCandidate?{...capabilityBody(oldCandidate),digest:oldCandidate.digest}:{schema:'flywheel-capability/v1',method:proposed,scope:methodScope(proposed),sourceHash:input.sourceHash,created_epoch:input.epoch,proof:[],authority:[],reuse:'Fresh result checks remain required.'};
      if(!candidate.digest)candidate.digest=await digest('flywheel-capability',candidate);
      meter.charge('retention',Math.ceil(bytes(candidate)/1024),'construct-and-hash-capability');
      await stage('Out-Design');
      let proposedScore=0,incumbentScore=0,unsupported=0,qualifiedCount=0;
      for(const doc of input.qualification){const comparison=compare(doc,input.max_clauses,meter,'qualification');const chosen=comparison.methods.find(x=>x.method===(input.arm==='expert'?expert(doc,meter):proposed)),old=comparison.methods.find(x=>x.method===incumbent);proposedScore+=chosen.structural_score;incumbentScore+=old.structural_score;unsupported+=chosen.missing.length;qualifiedCount+=!chosen.missing.length&&chosen.structural_score===comparison.methods.find(x=>x.method==='dependency-graph-before-compression').structural_score?1:0;}
      const admitted=unsupported===0&&qualifiedCount===input.qualification.length&&proposedScore>=incumbentScore;
      selected=(input.arm==='frozen')?'lead-order':admitted?proposed:incumbent;
      decision=admitted&&selected!==incumbent?'ACCEPT_RESEARCH_REUSE':admitted?'RETAIN_INCUMBENT':'REJECT_DESCENDANT';
      await stage('Out-Strategise');
      if(admitted&&(input.arm==='flywheel'||input.arm==='cache')&&selected!=='lead-order'){
        const existing=retained.find(x=>x.method===selected&&x.sourceHash===input.sourceHash);
        if(!existing)retained.push({...candidate,validated_epoch:input.epoch,last_used_epoch:input.epoch});
        else existing.last_used_epoch=input.epoch;
        while(retained.length>2){retained.sort((a,b)=>a.last_used_epoch-b.last_used_epoch||a.digest.localeCompare(b.digest));retired.push({...retained.shift(),reason:'two-artifact-retention-cap'});}
      }
      await stage('Out-Execute');
      for(let index=0;index<input.missions.length;index++){
        await checkpoint('Out-Execute');const doc=input.missions[index],begin=meter.spent,t0=now();
        const method=input.arm==='expert'?expert(doc,meter):selected;
        const value=selectOne(doc,method,input.max_clauses,meter),comparison=compare(doc,input.max_clauses,meter,'validation');
        const expected=comparison.methods.find(x=>x.method==='dependency-graph-before-compression'),qualified=!value.missing.length&&value.structural_score===expected.structural_score;
        observations.push({stream:input.stream,arm:input.arm,epoch:input.epoch,mission_id:`s${input.stream}-g${input.epoch}-m${index}`,document:doc,max_clauses:input.max_clauses,method,selected:value.selected,structural_score:value.structural_score,optimal_score:expected.structural_score,missing:value.missing,qualified,status:'completed',cost_before:begin,cost_after:meter.spent,cost_breakdown:clone(meter.counts),elapsed_ns:Math.round((now()-t0)*1e6),capability_digest:retained.find(x=>x.method===method)?.digest||null});
      }
      await stage('Out-Evolve');
      meter.charge('retention',Math.ceil(bytes(retained)/1024)+Math.ceil(bytes(retired)/1024),'retain-capabilities-and-tombstones');
    }catch(error){if(error.code!=='BUDGET_EXHAUSTED'){error.research_partial={stream:input.stream,arm:input.arm,epoch:input.epoch,spent:meter.spent,costs:meter.counts,cost_events:meter.events,trace,observations};throw error;}failure='budget-exhausted';deniedCharge=error.denied_charge;decision='STOP_BUDGET';retained=clone(input.retained);}
    const result={stream:input.stream,arm:input.arm,epoch:input.epoch,incumbent,proposed,selected,decision,failure,denied_charge:deniedCharge,retained,retired,attempts,trace,observations,spent:meter.spent,costs:meter.counts,cost_events:meter.events,coverage:observations.filter(x=>x.qualified).length};
    return {decision,summary:{qualified:result.coverage,requested:input.missions.length,logical_units:meter.spent,retained:retained.length},evidence:result,artifacts:[{name:'capability.json',type:'application/json',content:JSON.stringify({retained,retired,activeProof:[],activeAuthority:[]},null,2)+'\n'},{name:'source-summaries.json',type:'application/json',content:JSON.stringify(observations.map(x=>({mission_id:x.mission_id,selected:x.selected,qualified:x.qualified})),null,2)+'\n'}],limits:['Synthetic supplied annotations; structural support is not source truth or reader benefit.','Closed supplied selector grammar; no invented general algorithm, protected external examination, native signed runtime or production authority.','Standardized structural work units are an accounting proxy; monetary, human and model-authoring costs remain unmeasured.']};
  }
};
export const workbench=createWorkbench([adapter]);
export function makeSpec(input){const spec=example();return {...spec,family:adapter.manifest.id,name:'AGI ALPHA FLYWHEEL',rights:{dataClass:'synthetic',source:'Frozen synthetic acyclic source clauses',license:'Apache-2.0'},reviewMinutes:1,inputs:clone(input)};}
export async function runEpoch(input,options={}){return workbench.run(makeSpec(input),{sourceHash:input.sourceHash,...options});}
export async function inspectEpoch(pack){const view=await workbench.inspectPack(pack);if(view.activeProof.length||view.activeAuthority.length)throw Error('IMPORTED_AUTHORITY');return view;}

export function generateDocument(seed,epoch,index,partition='demo'){
  let state=seed>>>0;const random=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state;};
  const n=[5,6,7,8,9,10][epoch],claims=[];
  for(let i=0;i<n;i++){
    let deps=[];
    if([2,3,5].includes(epoch)&&i>0){if(random()%3!==0)deps.push('C'+(random()%i));if(i>2&&random()%2===0)deps.push('C'+(random()%i));deps=[...new Set(deps)];}
    claims.push({schema_version:1,id:'C'+i,text:`Synthetic ${partition} ${seed} requirement ${epoch} observation ${index}, clause ${i}: bounded instrument condition ${random()%100000}.`,weight:1+random()%29,depends_on:deps,provenance:'Synthetic finite-generator/v1; no empirical source truth asserted.'});
  }
  if(epoch===0)claims.sort((a,b)=>b.weight-a.weight);
  else for(let i=claims.length-1;i>0;i--){const j=random()%(i+1);[claims[i],claims[j]]=[claims[j],claims[i]];}
  return validateDocument({schema_version:1,schema:'source-document/v1',title:`Synthetic requirement generation ${epoch+1}`,source_url:'https://github.com/MontrealAI/AGI-Alpha-Agent-v0',public_non_personal:true,claims});
}
export function makeStream(seed,stream=0,partition='demo'){
  return {stream,seed,partition,epochs:Array.from({length:6},(_,epoch)=>({epoch,max_clauses:[3,2,3,2,3,1][epoch],development:Array.from({length:2},(_,i)=>generateDocument(seed+epoch*100000+i*177+11,epoch,i,partition+'-development')),qualification:Array.from({length:2},(_,i)=>generateDocument(seed+epoch*100000+i*251+30001,epoch,i,partition+'-qualification')),missions:Array.from({length:6},(_,i)=>generateDocument(seed+epoch*100000+i*379+60001,epoch,i,partition+'-terminal'))}))};
}
export async function runStream(manifest,{arm='flywheel',budget=500000,sourceHash='0'.repeat(64),onEvent=()=>{},onPack=async()=>{},signal}={}){
  let retained=[],spent=0,terminal='finite-stream-complete';const generations=[],observations=[];
  for(const epoch of manifest.epochs){
    if(signal?.aborted){onEvent({state:'stopped',reason:'operator'});break;}
    const input={...epoch,stream:manifest.stream,arm,budget,spent,retained,sourceHash};
    onEvent({state:'running',epoch:epoch.epoch,arm});
    const pack=await runEpoch(input,{signal,onProgress:stage=>onEvent({stage,epoch:epoch.epoch,arm})});
    const result=pack.result.evidence;await onPack(pack);await inspectEpoch(pack);
    spent=result.spent;retained=result.retained;observations.push(...result.observations);generations.push({...result,packDigest:pack.integrityDigest,observations:undefined,cost_events:undefined});
    onEvent({state:'completed',epoch:epoch.epoch,arm,qualified:result.coverage,retained:retained.length,spent});
    if(result.failure){terminal=result.failure;break;}
  }
  return {stream:manifest.stream,arm,budget,spent,retained,generations,observations,qualified:observations.filter(x=>x.qualified).length,requested:manifest.epochs.reduce((n,e)=>n+e.missions.length,0),state:signal?.aborted?'stopped':terminal};
}
export async function runToy(seed=20261024,callbacks={}){return runStream(makeStream(seed,0,'demo'),callbacks);}
