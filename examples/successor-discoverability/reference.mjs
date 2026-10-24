// SPDX-License-Identifier: Apache-2.0
// Independent finite-model reference. Imports no producer code.
// Complete Cartesian grammar enumeration and direct subset checking are correctness
// references, not claims about an optimized conventional implementation's runtime.
export const REFERENCE_VERSION = '1.0.0';
const err = text => { throw new TypeError(text); };
const int = (v, a, b, tag) => { if (!Number.isSafeInteger(v) || Object.is(v, -0) || v < a || v > b) err(tag); return v; };
const fields = (v, keys, tag) => {
  if (!v || typeof v !== 'object' || Array.isArray(v)) err(tag);
  const got = Object.keys(v); if (got.length !== keys.length || keys.some(k => !Object.hasOwn(v, k))) err(tag);
};
function owned(v) {
  let count = 0;
  const copy = (x, depth) => {
    if (++count > 40000 || depth > 18) err('reference framing limit');
    if (x === null || typeof x === 'boolean') return x;
    if (typeof x === 'number') { int(x, -Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER, 'reference exact integer'); return x; }
    if (typeof x === 'string') { if (x.length > 300000) err('reference string limit'); return x; }
    if (!x || typeof x !== 'object') err('reference JSON data');
    if (!Array.isArray(x) && ![Object.prototype, null].includes(Object.getPrototypeOf(x))) err('reference plain data');
    const keys = Reflect.ownKeys(x).filter(k => !(Array.isArray(x) && k === 'length'));
    if (keys.some(k => typeof k !== 'string')) err('reference symbol key');
    if (Array.isArray(x) && (keys.length !== x.length || keys.some((k, i) => k !== String(i)))) err('reference dense array');
    const out = Array.isArray(x) ? [] : Object.create(null);
    for (const key of keys) {
      const d = Object.getOwnPropertyDescriptor(x, key);
      if (!d || !d.enumerable || !Object.hasOwn(d, 'value')) err('reference data property');
      out[key] = copy(d.value, depth + 1);
    }
    return out;
  };
  return copy(v, 0);
}
function canon(v) {
  if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']';
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}';
  return JSON.stringify(v);
}
export function referenceProblem(input) {
  const p = owned(input);
  fields(p, ['schema','id','channels','worlds','nuisance','grammar','missionBudget'], 'reference problem fields');
  if (p.schema !== 'discoverability.problem.v1' || typeof p.id !== 'string' || !/^[a-z][a-z0-9-]{1,79}$/.test(p.id)) err('reference identity');
  if (!Array.isArray(p.channels) || p.channels.length < 1 || p.channels.length > 10) err('reference channels');
  const n = p.channels.length, names = new Set();
  for (const c of p.channels) {
    fields(c, ['id','cost','noise'], 'reference channel fields');
    if (typeof c.id !== 'string' || !/^[a-z][a-z0-9-]{0,47}$/.test(c.id) || names.has(c.id)) err('reference channel identity');
    names.add(c.id); int(c.cost, 1, 1000000, 'reference cost'); int(c.noise, 0, 10000, 'reference noise');
  }
  if (!Array.isArray(p.worlds) || p.worlds.length < 2 || p.worlds.length > 64) err('reference worlds');
  const worldNames = new Set();
  for (const w of p.worlds) {
    fields(w, ['id','goal','signal'], 'reference world fields');
    if (typeof w.id !== 'string' || !w.id || w.id.length > 80 || worldNames.has(w.id)) err('reference world identity');
    worldNames.add(w.id);
    if (typeof w.goal !== 'string' || !w.goal || w.goal.length > 80 || !Array.isArray(w.signal) || w.signal.length !== n) err('reference goal/signal');
    w.signal.forEach(x => int(x, -1000000, 1000000, 'reference signal'));
  }
  if (!Array.isArray(p.nuisance) || p.nuisance.length !== n || !Array.isArray(p.nuisance[0])) err('reference nuisance');
  const m = int(p.nuisance[0].length, 0, 4, 'reference nuisance columns');
  for (const r of p.nuisance) {
    if (!Array.isArray(r) || r.length !== m) err('reference nuisance row');
    r.forEach(x => int(x, -100, 100, 'reference nuisance coefficient'));
  }
  fields(p.grammar, ['maxSupport','weightLimit','maxL1'], 'reference grammar fields');
  int(p.grammar.maxSupport, 1, n, 'reference support'); int(p.grammar.weightLimit, 1, 3, 'reference weights');
  int(p.grammar.maxL1, 1, 12, 'reference L1'); int(p.missionBudget, 1, 10000000, 'reference mission budget');
  return p;
}
class ReferenceExhausted extends Error {}
function meter(limit) {
  int(limit, 1, 100000000, 'reference work budget');
  return {used: 0, counts: Object.create(null), spend(kind, amount = 1) {
    if (this.used + amount > limit) throw new ReferenceExhausted('reference exhausted');
    this.used += amount; this.counts[kind] = (this.counts[kind] || 0) + amount;
  }, report() { return {limit, used: this.used, counters: {...this.counts}}; }};
}
const abs = x => x < 0n ? -x : x;
function gcd(a, b) { a = abs(a); b = abs(b); while (b) { const r = a % b; a = b; b = r; } return a; }
function scalar(a, b) { let x = 0n; for (let i = 0; i < a.length; i++) x += BigInt(a[i]) * BigInt(b[i]); return x; }
function allowed(w, p) {
  if (!Array.isArray(w) || w.length !== p.channels.length || w.some(x => !Number.isSafeInteger(x) || Math.abs(x) > p.grammar.weightLimit)) return false;
  let support = 0, l1 = 0, divisor = 0n, first = 0;
  for (const x of w) { if (x) { support++; if (!first) first = x; } l1 += Math.abs(x); divisor = gcd(divisor, BigInt(x)); }
  if (!support || first < 0 || support > p.grammar.maxSupport || l1 > p.grammar.maxL1 || divisor !== 1n) return false;
  for (let j = 0; j < p.nuisance[0].length; j++) if (scalar(w, p.nuisance.map(row => row[j])) !== 0n) return false;
  return true;
}
function experiment(w, p) {
  let cost = 0, radius = 0n;
  for (let i = 0; i < w.length; i++) { if (w[i]) cost += p.channels[i].cost; radius += BigInt(Math.abs(w[i])) * BigInt(p.channels[i].noise); }
  return {weights: [...w], cost, radius: Number(radius),
    responses: p.worlds.map(x => ({world:x.id, goal:x.goal, center:Number(scalar(w,x.signal))}))};
}
function catalogue(p, m) {
  const n = p.channels.length, q = p.grammar.weightLimit, base = 2*q+1, total = base**n, out = [];
  for (let code = 0; code < total; code++) {
    m.spend('cartesianVectors');
    let remainder = code; const w = [];
    for (let i = 0; i < n; i++) { w.push(remainder % base - q); remainder = Math.floor(remainder/base); }
    if (allowed(w,p)) { m.spend('referenceResponses', p.worlds.length*n); out.push(experiment(w,p)); }
  }
  out.sort((a,b)=>canon(a.weights).localeCompare(canon(b.weights),'en'));
  return out;
}
function targets(p) {
  const result = [];
  for (let i=0;i<p.worlds.length;i++) for (let j=i+1;j<p.worlds.length;j++)
    if (p.worlds[i].goal!==p.worlds[j].goal) result.push([i,j]);
  return result;
}
function separates(e,i,j) { return abs(BigInt(e.responses[i].center)-BigInt(e.responses[j].center))>2n*BigInt(e.radius); }
function missingPair(es,pairs,m) {
  for (const [i,j] of pairs) {
    let yes=false;
    for (const e of es) { m.spend('directPairChecks'); if(separates(e,i,j)){yes=true;break;} }
    if(!yes)return [i,j];
  }
  return null;
}
function witness(p, es, pair) {
  const [i,j]=pair;
  return {left:p.worlds[i].id,right:p.worlds[j].id,leftGoal:p.worlds[i].goal,rightGoal:p.worlds[j].goal,
    observationTwice:es.map(e=>{
      const lo=Math.max(e.responses[i].center-e.radius,e.responses[j].center-e.radius);
      const hi=Math.min(e.responses[i].center+e.radius,e.responses[j].center+e.radius);
      if(lo>hi)err('reference witness does not overlap'); return lo+hi;
    })};
}
function resultError(e,m) { if(!(e instanceof ReferenceExhausted))throw e; return {status:'REFERENCE_BUDGET_EXHAUSTED',complete:false,work:m.report()}; }
export function referenceCatalogue(input,{budget=2000000}={}) {
  const p=referenceProblem(input),m=meter(budget);
  try { const experiments=catalogue(p,m);return {status:'COMPLETE',experiments,work:m.report()}; } catch(e){return resultError(e,m);}
}
export function conventionalStatic(input,{budget=10000000}={}) {
  const p=referenceProblem(input),m=meter(budget);
  try {
    const es=catalogue(p,m),pairs=targets(p),miss=missingPair(es,pairs,m);
    if(miss)return {status:'UNIDENTIFIABLE_WITHIN_GRAMMAR',complete:true,templateCount:es.length,witness:witness(p,es,miss),work:m.report()};
    let best=null,bestCost=Infinity,subsets=0;
    const selected=[];
    function visit(index,cost) {
      m.spend('subsetNodes');
      if(index<es.length) { visit(index+1,cost);selected.push(index);visit(index+1,cost+es[index].cost);selected.pop();return; }
      subsets++;
      if(!missingPair(selected.map(i=>es[i]),pairs,m) && cost<bestCost){bestCost=cost;best=[...selected];}
    }
    visit(0,0);
    return {status:bestCost<=p.missionBudget?'COMPILED':'OVER_MISSION_BUDGET',complete:true,
      minimumCost:bestCost,experiments:best.map(i=>es[i]),templateCount:es.length,subsetsChecked:subsets,work:m.report(),
      scope:'Exact direct subset correctness reference; runtime is not an optimized conventional performance baseline.'};
  } catch(e){return resultError(e,m);}
}
function responseCells(e, p, m) {
  const points=[...new Set(e.responses.flatMap(r=>[r.center-e.radius,r.center+e.radius]))].sort((a,b)=>a-b),samples=[];
  for(let i=0;i<points.length;i++){samples.push(2*points[i]);if(i+1<points.length)samples.push(points[i]+points[i+1]);}
  const masks=new Map();
  for(const y2 of samples){
    let mask=0n;
    for(let i=0;i<p.worlds.length;i++){m.spend('adaptiveCellChecks');if(abs(BigInt(y2)-2n*BigInt(e.responses[i].center))<=2n*BigInt(e.radius))mask|=1n<<BigInt(i);}
    if(mask)masks.set(mask.toString(),{mask,observationTwice:y2});
  }
  return [...masks.values()];
}
export function conventionalAdaptive(input,{budget=10000000}={}) {
  const p=referenceProblem(input),m=meter(budget);
  try {
    const es=catalogue(p,m),parts=es.map(e=>responseCells(e,p,m)),memo=new Map();
    const sameGoal=mask=>{let goal=null;for(let i=0;i<p.worlds.length;i++)if(mask&(1n<<BigInt(i))){if(goal===null)goal=p.worlds[i].goal;else if(goal!==p.worlds[i].goal)return false;}return true;};
    function solve(mask){
      const key=mask.toString();if(memo.has(key))return memo.get(key);
      m.spend('adaptiveStates');
      if(sameGoal(mask)){const leaf={cost:0,experiment:null};memo.set(key,leaf);return leaf;}
      let best={cost:Infinity,experiment:null};
      for(let i=0;i<es.length;i++){
        m.spend('adaptiveAlternatives');
        const branches=new Map();
        for(const cell of parts[i]){const child=mask&cell.mask;if(child)branches.set(child.toString(),child);}
        if([...branches.values()].some(x=>x===mask))continue;
        let worst=0,finite=true;
        for(const child of branches.values()){const value=solve(child);if(!Number.isFinite(value.cost)){finite=false;break;}worst=Math.max(worst,value.cost);}
        const value=es[i].cost+worst;
        if(finite&&value<best.cost)best={cost:value,experiment:i,branches:[...branches.keys()]};
      }
      memo.set(key,best);return best;
    }
    const full=(1n<<BigInt(p.worlds.length))-1n,root=solve(full);
    const policy=[...memo.entries()].map(([worldMask,row])=>({worldMask,cost:Number.isFinite(row.cost)?row.cost:null,experiment:row.experiment===null?null:es[row.experiment].weights,branches:row.branches||[]}));
    return {status:Number.isFinite(root.cost)?(root.cost<=p.missionBudget?'COMPILED':'OVER_MISSION_BUDGET'):'UNIDENTIFIABLE_WITHIN_GRAMMAR',
      complete:true,worstAcquisitionCost:Number.isFinite(root.cost)?root.cost:null,templateCount:es.length,states:policy.length,policy,work:m.report(),
      scope:'Exact finite minimax adaptive policy; fresh independent bounded errors. Repeating a probe that can retain the entire belief cannot improve its worst-case value.'};
  } catch(e){return resultError(e,m);}
}
function inspectProgram(p,raw,m){
  const v=owned(raw);
  fields(v,['schema','problemKey','experiments','totalCost','protocol'],'reference program fields');
  if(v.schema!=='discoverability.program.v1'||v.problemKey!==canon(p)||v.protocol!=='fresh-independent-bounded-read-errors; shared additive nuisance cancelled within each experiment')err('reference source/scope/protocol binding');
  if(!Array.isArray(v.experiments)||v.experiments.length>2016)err('reference program length');
  int(v.totalCost,0,1000000000,'reference total cost');
  let sum=0;
  for(const e of v.experiments){
    m.spend('programExperiments');fields(e,['weights','cost','radius','responses'],'reference experiment fields');
    if(!allowed(e.weights,p)||canon(e)!==canon(experiment(e.weights,p)))err('reference experiment mismatch');
    sum+=e.cost;
  }
  if(sum!==v.totalCost)err('reference ledger mismatch');
  if(missingPair(v.experiments,targets(p),m))err('reference conflicting goal transcript');
  return v;
}
export function verifyProgramReference(input,raw,{budget=2000000,requireBudget=true}={}){
  const p=referenceProblem(input),m=meter(budget);
  try{const program=inspectProgram(p,raw,m);if(requireBudget&&program.totalCost>p.missionBudget)err('reference budget exceeded');
    return {valid:true,totalCost:program.totalCost,experiments:program.experiments.length,work:m.report(),scope:'Independent arithmetic and decision correctness; no optimality, model truth or promotion authority implied.'};
  }catch(e){if(e instanceof ReferenceExhausted)return resultError(e,m);return {valid:false,reason:e.message,work:m.report()};}
}
function rational(value){
  if(Number.isSafeInteger(value)&&!Object.is(value,-0))return [BigInt(value),1n];
  fields(value,['numerator','denominator'],'reference rational fields');
  int(value.numerator,-Number.MAX_SAFE_INTEGER,Number.MAX_SAFE_INTEGER,'reference numerator');
  int(value.denominator,1,1000000000,'reference denominator');
  return [BigInt(value.numerator),BigInt(value.denominator)];
}
export function decodeReference(input,raw,observations){
  const p=referenceProblem(input),m=meter(2000000),program=inspectProgram(p,raw,m),ys=owned(observations);
  if(program.totalCost>p.missionBudget)err('reference budget exceeded');
  if(!Array.isArray(ys)||ys.length!==program.experiments.length)err('reference observation count');
  const rr=ys.map(rational),compatible=[];
  for(let i=0;i<p.worlds.length;i++){
    let admitted=true;
    for(let j=0;j<program.experiments.length;j++){
      const e=program.experiments[j],[a,b]=rr[j];
      if(abs(a-BigInt(e.responses[i].center)*b)>BigInt(e.radius)*b){admitted=false;break;}
    }
    if(admitted)compatible.push(p.worlds[i]);
  }
  const goals=[...new Set(compatible.map(w=>w.goal))];
  return {status:goals.length===1?'DECIDED':goals.length?'AMBIGUOUS':'OUT_OF_SCOPE',decision:goals.length===1?goals[0]:null,compatibleWorlds:compatible.map(w=>w.id)};
}
