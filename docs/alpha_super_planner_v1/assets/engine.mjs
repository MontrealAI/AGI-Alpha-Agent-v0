// SPDX-License-Identifier: Apache-2.0
const fields = (obj, keys, name) => {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj) || Object.keys(obj).sort().join('|') !== [...keys].sort().join('|')) throw new Error(`${name}: unexpected or missing fields`);
};
const integer = (n, max, name) => { if (!Number.isInteger(n) || n < 0 || n > max) throw new Error(`${name}: expected an integer from 0 to ${max}`); };
const label = (s, max, name) => { if (typeof s !== 'string' || !s.trim() || s !== s.trim() || [...s].length > max) throw new Error(`${name}: expected 1–${max} characters`); return s.trim(); };
export function validate(raw) {
  fields(raw, ['schema','goal','budget','effort_capacity','max_risk','tasks'], 'Input');
  if (raw.schema !== 'agialpha.bounded-plan.v1') throw new Error('Unsupported input schema');
  const goal = label(raw.goal, 500, 'Goal');
  integer(raw.budget, 1000000, 'Budget'); integer(raw.effort_capacity, 1000000, 'Effort'); integer(raw.max_risk, 100, 'Risk limit');
  if (!Array.isArray(raw.tasks) || raw.tasks.length < 1 || raw.tasks.length > 16) throw new Error('Expected 1–16 tasks');
  const ids = new Set();
  const tasks = raw.tasks.map((task) => {
    fields(task, ['id','label','cost','effort','value','risk','requires'], 'Task');
    if (typeof task.id !== 'string' || !/^[a-z][a-z0-9_-]{0,31}$/.test(task.id) || ids.has(task.id)) throw new Error('Task IDs must be unique lowercase identifiers');
    ids.add(task.id);
    for (const k of ['cost','effort','value']) integer(task[k],1000000,`${task.id}.${k}`);
    integer(task.risk,100,`${task.id}.risk`);
    if (!Array.isArray(task.requires) || task.requires.length > 15 || task.requires.some(x => typeof x !== 'string') || new Set(task.requires).size !== task.requires.length) throw new Error(`${task.id}: dependencies must be unique IDs`);
    return {...task, label:label(task.label,120,`${task.id}.label`), requires:[...task.requires]};
  });
  const byId = new Map(tasks.map(t => [t.id,t]));
  const visiting=new Set(), done=new Set();
  function visit(id) {
    if (visiting.has(id)) throw new Error('Task dependency cycle');
    if (done.has(id)) return;
    visiting.add(id);
    for (const dep of byId.get(id).requires) {
      if (!ids.has(dep) || dep === id) throw new Error(`${id}: unknown or self dependency`);
      visit(dep);
    }
    visiting.delete(id);done.add(id);
  }
  tasks.forEach(t => visit(t.id));
  return {...raw, goal, tasks};
}
function lexical(a,b) { for(let i=0;i<Math.min(a.length,b.length);i++){ if(a[i]!==b[i])return a[i]<b[i]?-1:1; } return a.length-b.length; }
export function solve(raw) {
  const input=validate(raw), tasks=[...input.tasks].sort((a,b)=>a.id<b.id?-1:1);
  const positions=new Map(tasks.map((t,i)=>[t.id,i]));
  const masks=tasks.map(t=>t.requires.reduce((mask,id)=>mask | (1<<positions.get(id)),0));
  let best={ids:[],cost:0,effort:0,value:0,max_risk:0}, feasible=0;
  for(let mask=0;mask<(1<<tasks.length);mask++) {
    let cost=0,effort=0,value=0,risk=0,valid=true;const ids=[];
    for(let i=0;i<tasks.length;i++) if(mask & (1<<i)) {
      const t=tasks[i];
      if(t.risk>input.max_risk || (mask&masks[i])!==masks[i]) {valid=false;break;}
      cost+=t.cost;effort+=t.effort;value+=t.value;risk=Math.max(risk,t.risk);ids.push(t.id);
      if(cost>input.budget || effort>input.effort_capacity){valid=false;break;}
    }
    if(!valid)continue;feasible++;
    if(value>best.value || value===best.value && (cost<best.cost || cost===best.cost && (effort<best.effort || effort===best.effort && lexical(ids,best.ids)<0))) best={ids,cost,effort,value,max_risk:risk};
  }
  const completed=new Set(), steps=[];
  while(steps.length<best.ids.length) {
    const t=tasks.find(t=>best.ids.includes(t.id) && !completed.has(t.id) && t.requires.every(id=>completed.has(id)));
    steps.push(t.id);completed.add(t.id);
  }
  return {schema:'agialpha.bounded-plan-result.v1',goal:input.goal,selected_ids:best.ids,steps,totals:{cost:best.cost,effort:best.effort,value:best.value,max_risk:best.max_risk},omitted_ids:tasks.filter(t=>!completed.has(t.id)).map(t=>t.id),feasible_subsets:feasible};
}
// Preserve the CLI's duplicate-key and integer-token rejection for imported JSON.
export function parseInput(text) {
  if (new TextEncoder().encode(text).length > 65536) throw new Error('Input exceeds 64 KiB');
  let at=0;
  const ws=()=>{while(/[\t\n\r ]/.test(text[at] || '\0'))at++;};
  const fail=()=>{throw new Error('Invalid JSON or noninteger number token');};
  function string() {
    const start=at++;
    while(at<text.length){if(text[at]==='\\'){at+=2;continue;}if(text[at++]==='"')return JSON.parse(text.slice(start,at));}fail();
  }
  function value(depth=0) {
    if(depth>32)throw new Error('Input nesting is too deep');ws();const c=text[at];
    if(c==='"')return string();
    if(c==='{') {at++;ws();const obj=Object.create(null),seen=new Set();if(text[at]==='}'){at++;return obj;}while(true){ws();if(text[at]!=='"')fail();const key=string();if(seen.has(key))throw new Error('Duplicate JSON key');seen.add(key);ws();if(text[at++]!==':')fail();obj[key]=value(depth+1);ws();const sep=text[at++];if(sep==='}')return obj;if(sep!==',')fail();}}
    if(c==='['){at++;ws();const arr=[];if(text[at]===']'){at++;return arr;}while(true){arr.push(value(depth+1));ws();const sep=text[at++];if(sep===']')return arr;if(sep!==',')fail();}}
    for(const [token,result] of [['true',true],['false',false],['null',null]])if(text.startsWith(token,at)){at+=token.length;return result;}
    const token=text.slice(at).match(/^-?(?:0|[1-9][0-9]*)/);if(!token)fail();at+=token[0].length;if(/[.eE0-9]/.test(text[at] || '\0'))fail();return Number(token[0]);
  }
  const parsed=value();ws();if(at!==text.length)fail();if (parsed && typeof parsed === 'object' && Object.keys(parsed).sort().join('|') === 'input|result') return validate(parsed.input);
  return validate(parsed);
}
