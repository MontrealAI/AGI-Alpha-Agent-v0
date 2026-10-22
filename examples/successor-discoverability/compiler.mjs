// SPDX-License-Identifier: Apache-2.0
export const SCHEMA = 'discoverability.problem.v1';
export const COMPILER_VERSION = '1.0.0-experimental';
const fail = m => { throw new TypeError(m); };
const integer = (v, lo, hi, label) => { if (!Number.isSafeInteger(v) || v < lo || v > hi) fail(label); return v; };
const exact = (o, keys, label) => { if (!o || typeof o !== 'object' || Array.isArray(o) || Object.keys(o).sort().join('|') !== [...keys].sort().join('|')) fail(label); };
export function snapshot(value) {
  let nodes = 0;
  function copy(v, depth) {
    if (++nodes > 30000 || depth > 16) fail('JSON framing limit');
    if (v === null || typeof v === 'boolean') return v;
    if (typeof v === 'number') { if (!Number.isSafeInteger(v)) fail('integer JSON required'); return v; }
    if (typeof v === 'string') { if (v.length > 100000) fail('string limit'); return v; }
    if (!v || typeof v !== 'object') fail('plain JSON required');
    const proto = Object.getPrototypeOf(v);
    if (!Array.isArray(v) && proto !== Object.prototype && proto !== null) fail('plain object required');
    const names = Object.keys(v);
    if (names.length > 30000) fail('object limit');
    const out = Array.isArray(v) ? [] : {};
    for (const k of names) {
      if (['__proto__','constructor','prototype'].includes(k)) fail('forbidden key');
      const d = Object.getOwnPropertyDescriptor(v, k);
      if (!d || !Object.hasOwn(d, 'value')) fail('accessor prohibited');
      out[k] = copy(d.value, depth + 1);
    }
    if (Array.isArray(v) && (names.length !== v.length || names.some((k,i) => k !== String(i)))) fail('dense arrays required');
    return out;
  }
  return copy(value, 0);
}
export function canonical(v) {
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
  return JSON.stringify(v);
}
function frozen(v) { if(v && typeof v==='object'){ for(const x of Object.values(v)) frozen(x); Object.freeze(v); } return v; }
const dot = (a,b) => a.reduce((s,x,i) => s + x*b[i], 0);
const gcd = (a,b) => b ? gcd(b,a%b) : Math.abs(a);
function validate(p) {
  exact(p,['schema','id','channels','worlds','nuisance','grammar','missionBudget'],'problem fields');
  if(p.schema !== SCHEMA || typeof p.id !== 'string' || !/^[a-z][a-z0-9-]{1,79}$/.test(p.id)) fail('problem identity');
  if(!Array.isArray(p.channels) || p.channels.length<1 || p.channels.length>10) fail('channel count');
  const n=p.channels.length, ids=new Set();
  for(const c of p.channels){
    exact(c,['id','cost','noise'],'channel fields');
    if(typeof c.id!=='string' || !/^[a-z][a-z0-9-]{0,47}$/.test(c.id) || ids.has(c.id)) fail('channel identity');
    ids.add(c.id); integer(c.cost,1,1000000,'channel cost'); integer(c.noise,0,10000,'noise');
  }
  if(!Array.isArray(p.worlds) || p.worlds.length<2 || p.worlds.length>64) fail('world count');
  const worlds=new Set();
  for(const w of p.worlds){
    exact(w,['id','goal','signal'],'world fields');
    if(typeof w.id!=='string'||!w.id||w.id.length>80||worlds.has(w.id)) fail('world identity');
    worlds.add(w.id);
    if(typeof w.goal!=='string'||!w.goal||w.goal.length>80) fail('goal');
    if(!Array.isArray(w.signal)||w.signal.length!==n) fail('signal dimension');
    for(const x of w.signal) integer(x,-1000000,1000000,'signal');
  }
  if(!Array.isArray(p.nuisance)||p.nuisance.length!==n) fail('nuisance rows');
  const m=p.nuisance[0]?.length;
  integer(m,0,4,'nuisance columns');
  for(const row of p.nuisance){ if(!Array.isArray(row)||row.length!==m) fail('nuisance matrix'); for(const x of row) integer(x,-100,100,'nuisance'); }
  exact(p.grammar,['maxSupport','weightLimit','maxL1'],'grammar');
  integer(p.grammar.maxSupport,1,n,'support'); integer(p.grammar.weightLimit,1,3,'weight limit'); integer(p.grammar.maxL1,1,12,'L1');
  integer(p.missionBudget,1,10000000,'mission budget');
  return p;
}
export const validateProblem = input => frozen(validate(snapshot(input)));
class Exhausted extends Error {}
class Meter {
  constructor(limit,checkpoint){this.limit=integer(limit,1,20000000,'work budget');this.used=0;this.counts={};this.checkpoint=checkpoint;this.last=0;}
  step(kind,n=1){ if(this.used+n>this.limit) throw new Exhausted('work budget exhausted'); this.used+=n; this.counts[kind]=(this.counts[kind]||0)+n; }
  async cooperate(force=false){if(force||this.used-this.last>=128){this.last=this.used;await this.checkpoint();}}
  report(){return {used:this.used,limit:this.limit,counters:{...this.counts}};}
}
const structural = p => canonical({schema:SCHEMA,channels:p.channels,nuisance:p.nuisance,grammar:p.grammar});
function legal(w,p){
  const g=p.grammar;
  if(w.length!==p.channels.length||w.some(x=>!Number.isSafeInteger(x)||Math.abs(x)>g.weightLimit)) return false;
  if(w.filter(Boolean).length>g.maxSupport||w.reduce((s,x)=>s+Math.abs(x),0)>g.maxL1) return false;
  const first=w.find(x=>x!==0);
  if(!first||first<0||w.reduce((a,b)=>gcd(a,b),0)!==1) return false;
  return (p.nuisance[0]||[]).every((_,j)=>dot(w,p.nuisance.map(r=>r[j]))===0);
}
async function construct(p,meter){
  const n=p.channels.length,g=p.grammar,templates=[],w=Array(n).fill(0);
  async function rec(i,s,l,first){
    meter.step('grammarNodes'); await meter.cooperate();
    if(i===n){
      if(!s||w.reduce((a,b)=>gcd(a,b),0)!==1) return;
      meter.step('nuisanceChecks',Math.max(1,p.nuisance[0].length));
      if(legal(w,p)) templates.push(Object.freeze([...w]));
      return;
    }
    w[i]=0; await rec(i+1,s,l,first);
    if(s>=g.maxSupport) return;
    for(let x=-g.weightLimit;x<=g.weightLimit;x++){
      if(x===0||(!first&&x<0)||l+Math.abs(x)>g.maxL1) continue;
      w[i]=x; await rec(i+1,s+1,l+Math.abs(x),true);
    }
    w[i]=0;
  }
  await rec(0,0,0,false);
  templates.sort((a,b)=>canonical(a).localeCompare(canonical(b),'en'));
  return Object.freeze(templates);
}
function observationsFor(p,weights){
  return {weights:[...weights],cost:p.channels.reduce((s,c,i)=>s+(weights[i]?c.cost:0),0),radius:p.channels.reduce((s,c,i)=>s+Math.abs(weights[i])*c.noise,0),
    responses:p.worlds.map(w=>({world:w.id,goal:w.goal,center:dot(weights,w.signal)}))};
}
function pairsFor(p){const pairs=[];for(let i=0;i<p.worlds.length;i++)for(let j=i+1;j<p.worlds.length;j++)if(p.worlds[i].goal!==p.worlds[j].goal)pairs.push([i,j]);return pairs;}
function maskFor(e,pairs){let mask=0n;for(let i=0;i<pairs.length;i++){const[a,b]=pairs[i];if(Math.abs(e.responses[a].center-e.responses[b].center)>2*e.radius)mask|=1n<<BigInt(i);}return mask;}
function transcriptWitness(p,experiments,pair){
  const [i,j]=pair;
  return {left:p.worlds[i].id,right:p.worlds[j].id,leftGoal:p.worlds[i].goal,rightGoal:p.worlds[j].goal,
    observationTwice:experiments.map(e=>Math.max(e.responses[i].center-e.radius,e.responses[j].center-e.radius)+Math.min(e.responses[i].center+e.radius,e.responses[j].center+e.radius)),
    scope:'All qualified experiments in this finite grammar; fresh independent bounded errors for each acquisition. Not impossibility outside the grammar.'};
}
export function createCompiler({strategy='cached'}={}){
  if(!['cached','fresh'].includes(strategy)) fail('compiler strategy');
  const cache=new Map(); let hits=0,misses=0;
  return {
    stats:()=>({hits,misses,entries:cache.size}),
    async compile(input,{budget=2000000,checkpoint=async()=>{}}={}){
      const p=validateProblem(input),meter=new Meter(budget,checkpoint),key=structural(p),pairs=pairsFor(p);
      let templates=[],libraryHit=false,all=[],best=null,bestCost=null,searchComplete=false;
      try{
        await meter.cooperate(true);
        meter.step('frame',p.channels.length+p.worlds.length+pairs.length);
        if(strategy==='cached'&&cache.has(key)){templates=cache.get(key);libraryHit=true;hits++;meter.step('libraryLookup');}
        else{templates=await construct(p,meter);misses++;if(strategy==='cached'){if(cache.size>=8)cache.delete(cache.keys().next().value);cache.set(key,templates);}}
        for(const weights of templates){
          meter.step('responseEvaluation',p.worlds.length*p.channels.length);
          const e=observationsFor(p,weights);
          meter.step('decisionPairChecks',pairs.length); e.mask=maskFor(e,pairs); all.push(e);
          await meter.cooperate();
        }
        const full=(1n<<BigInt(pairs.length))-1n,union=all.reduce((m,e)=>m|e.mask,0n);
        const base={compilerVersion:COMPILER_VERSION,problemId:p.id,libraryHit,templateCount:templates.length,goalPairCount:pairs.length};
        if(union!==full){
          const k=pairs.findIndex((_,i)=>(union&(1n<<BigInt(i)))===0n);
          return {...base,status:'UNIDENTIFIABLE_WITHIN_GRAMMAR',certificate:{decisionIdentifiable:false,optimalWithinGrammar:false,searchComplete:true},
            witness:transcriptWitness(p,all,pairs[k]),experiments:all.map(({mask,...e})=>e),work:meter.report()};
        }
        if(!pairs.length){best=[];bestCost=0;searchComplete=true;}
        else{
          const byMask=new Map();
          for(const e of all){if(!e.mask)continue;const k=e.mask.toString(),old=byMask.get(k);if(!old||e.cost<old.cost)byMask.set(k,e);}
          let candidates=[...byMask.values()];
          const keep=[];
          for(let i=0;i<candidates.length;i++){
            let dominated=false;
            for(let j=0;j<candidates.length;j++){
              if(i===j)continue;
              meter.step('dominanceChecks');
              if(candidates[j].cost<=candidates[i].cost&&(candidates[j].mask|candidates[i].mask)===candidates[j].mask){dominated=true;break;}
              await meter.cooperate();
            }
            if(!dominated)keep.push(candidates[i]);
          }
          candidates=keep.sort((a,b)=>a.cost-b.cost||canonical(a.weights).localeCompare(canonical(b.weights),'en'));
          const options=pairs.map((_,i)=>candidates.map((e,j)=>(e.mask&(1n<<BigInt(i)))?j:-1).filter(j=>j>=0));
          let cover=0n,chosen=[];
          while(cover!==full){
            meter.step('greedySteps',candidates.length);
            let pick=-1,ratio=-1;
            for(let i=0;i<candidates.length;i++){
              let v=candidates[i].mask&~cover,count=0;while(v){v&=v-1n;count++;}
              const r=count/candidates[i].cost;if(r>ratio){ratio=r;pick=i;}
            }
            chosen.push(pick);cover|=candidates[pick].mask;
          }
          best=chosen.map(i=>candidates[i]);bestCost=best.reduce((s,e)=>s+e.cost,0);
          const seen=new Map();
          async function search(covered,cost,selected){
            meter.step('searchNodes');await meter.cooperate();
            if(covered===full){if(cost<bestCost){bestCost=cost;best=selected.map(i=>candidates[i]);}return;}
            if(cost>=bestCost)return;
            const ck=covered.toString();if(seen.has(ck)&&seen.get(ck)<=cost)return;seen.set(ck,cost);
            let branch=null;
            for(let k=0;k<pairs.length;k++){
              if(covered&(1n<<BigInt(k)))continue;
              meter.step('branchChecks');
              const o=options[k].filter(i=>cost+candidates[i].cost<bestCost);
              if(!o.length)return;
              if(!branch||o.length<branch.length)branch=o;
            }
            for(const i of branch)await search(covered|candidates[i].mask,cost+candidates[i].cost,[...selected,i]);
          }
          await search(0n,0,[]);searchComplete=true;
        }
        const experiments=best.map(({mask,...e})=>e);
        const program={schema:'discoverability.program.v1',problemKey:canonical(p),experiments,totalCost:bestCost,
          protocol:'fresh-independent-bounded-read-errors; shared additive nuisance cancelled within each experiment'};
        return {...base,status:bestCost>p.missionBudget?'OVER_MISSION_BUDGET':'COMPILED',program,
          certificate:{decisionIdentifiable:true,optimalWithinGrammar:true,searchComplete,acceptedForBudget:bestCost<=p.missionBudget},work:meter.report()};
      }catch(e){
        if(!(e instanceof Exhausted))throw e;
        return {compilerVersion:COMPILER_VERSION,problemId:p.id,status:'BUDGET_EXHAUSTED',libraryHit,templateCount:templates.length,
          certificate:{decisionIdentifiable:false,optimalWithinGrammar:false,searchComplete:false},work:meter.report(),
          limits:['Incomplete search is not a negative scientific result; no program is qualified.']};
      }
    }
  };
}
export function inspectProgram(input,raw){
  const p=validateProblem(input),program=snapshot(raw);
  exact(program,['schema','problemKey','experiments','totalCost','protocol'],'program fields');
  if(program.schema!=='discoverability.program.v1'||program.problemKey!==canonical(p))fail('program scope changed');
  if(program.protocol!=='fresh-independent-bounded-read-errors; shared additive nuisance cancelled within each experiment')fail('measurement protocol');
  if(!Array.isArray(program.experiments)||program.experiments.length>2016)fail('experiment count');
  integer(program.totalCost,0,1000000000,'total cost');
  let cost=0;
  for(const e of program.experiments){
    exact(e,['weights','cost','radius','responses'],'experiment fields');
    if(!Array.isArray(e.weights)||!legal(e.weights,p))fail('illegal experiment');
    const expected=observationsFor(p,e.weights);
    if(canonical(e)!==canonical(expected))fail('experiment certificate changed');
    cost+=e.cost;
  }
  if(cost!==program.totalCost||cost>p.missionBudget)fail('program cost');
  const pairs=pairsFor(p),full=(1n<<BigInt(pairs.length))-1n,union=program.experiments.reduce((m,e)=>m|maskFor(e,pairs),0n);
  if(union!==full)fail('goal separation certificate failed');
  return {problem:p,program};
}
export function executeProgram(input,raw,observations){
  const {problem:p,program}=inspectProgram(input,raw),ys=snapshot(observations);
  if(!Array.isArray(ys)||ys.length!==program.experiments.length)fail('observation count');
  const rational=ys.map(y=>{
    if(Number.isSafeInteger(y)) return {n:BigInt(y),d:1n};
    exact(y,['numerator','denominator'],'rational observation');
    integer(y.numerator,-Number.MAX_SAFE_INTEGER,Number.MAX_SAFE_INTEGER,'observation numerator');
    integer(y.denominator,1,1000000000,'observation denominator');
    return {n:BigInt(y.numerator),d:BigInt(y.denominator)};
  });
  const compatible=p.worlds.filter((w,i)=>program.experiments.every((e,j)=>{
    const {n,d}=rational[j],center=BigInt(e.responses[i].center)*d,delta=n-center;
    return (delta<0n?-delta:delta)<=BigInt(e.radius)*d;
  }));
  const goals=[...new Set(compatible.map(w=>w.goal))];
  return {status:goals.length===1?'DECIDED':goals.length===0?'OUT_OF_SCOPE':'AMBIGUOUS',decision:goals.length===1?goals[0]:null,compatibleWorlds:compatible.map(w=>w.id)};
}
