// SPDX-License-Identifier: Apache-2.0
import { canonical, digest, parseBounded } from '../../docs/assets/successor/engine.mjs';
import { missionFor } from '../build-successor/model.mjs';
import { compileJobs } from '../build-successor/vendor/agijobs/compiler.mjs';
import { createPortfolioJobs } from '../build-successor/vendor/agijobs/templates.mjs';

export const VERSION = 'successor-workbench/v1';
export const REGISTRY = Object.freeze([
  { id: 'reliability', en: 'Repair a range utility', fr: 'Réparer un utilitaire', artifact: 'repair.patch', scope: 'Closed interval utilities in the documented finite source grammar.' },
  { id: 'performance', en: 'Compare real algorithms', fr: 'Comparer des algorithmes', artifact: 'benchmark.json', scope: 'Exact sorted unique integer values; sort/reduce versus Set/sort.' },
  { id: 'documentation', en: 'Check executable examples', fr: 'Vérifier des exemples exécutables', artifact: 'checked-examples.md', scope: 'Named URI and UTF-8 SDK operations in bounded JSON examples.' },
  { id: 'public-data', en: 'Turn data into a report', fr: 'Transformer des données en rapport', artifact: 'report.html', scope: 'Public or synthetic two-column CSV with exact integer amounts.' },
  { id: 'numerical', en: 'Reproduce a calculation', fr: 'Reproduire un calcul', artifact: 'numerical.json', scope: 'Polynomial integration using exact rational arithmetic and two quadrature rules.' },
]);

const clone = value => parseBounded(canonical(value));
function fields(value, keys, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).sort().join('|') !== [...keys].sort().join('|')) throw Error(`SCHEMA: ${label}`);
}
function integer(value, low, high, label) {
  if (!Number.isSafeInteger(value) || value < low || value > high) throw Error(`BOUNDS: ${label}`);
}
function text(value, maximum, label) {
  if (typeof value !== 'string' || !value.trim() || value.length > maximum) throw Error(`TEXT: ${label}`);
}
function html(value) { return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char])); }
function file(name, type, content) { return { name, type, content }; }
function jsonFile(name, object) { return file(name, 'application/json', JSON.stringify(object, null, 2) + '\n'); }

export function example(family = 'reliability') {
  const inputs = {
    reliability: { source: 'export function contains(value, low, high) { return low < value && value < high; }', low: 0, high: 10, cases: [-1, 0, 1, 5, 9, 10, 11] },
    performance: { values: [8, 3, 8, 1, 0, -3, 3, 12, 0, 7], repetitions: 7, repeats: 100 },
    documentation: { markdown: '# URI helper examples\n\n```successor-example\n{"operation":"url-encode","input":"hello world","expected":"hello+world"}\n```\n\n```successor-example\n{"operation":"url-decode","input":"hello%20world","expected":"hello world"}\n```\n' },
    'public-data': { csv: 'group,amount\nResearch,120\nSoftware,85\nResearch,35\nDocumentation,60\nSoftware,-5\n', unit: 'synthetic units' },
    numerical: { coefficients: [0, 0, 1], lower: 0, upper: 3, steps: 12, tolerancePpm: 1 },
  };
  if (!Object.hasOwn(inputs, family)) throw Error('UNSUPPORTED_FAMILY');
  return { schema: VERSION, family, name: 'My SUCCESSOR Ω', language: 'en', owner: 'local-owner',
    rights: { dataClass: 'synthetic', source: 'Included public example', license: 'Apache-2.0' },
    reviewMinutes: 10, inputs: clone(inputs[family]) };
}

export function validate(spec, adapter = null) {
  fields(spec, ['schema','family','name','language','owner','rights','reviewMinutes','inputs'], 'mission');
  if (spec.schema !== VERSION || !(REGISTRY.some(item => item.id === spec.family) || adapter?.manifest.id === spec.family)) throw Error('UNSUPPORTED_VERSION_OR_FAMILY');
  text(spec.name, 64, 'name'); text(spec.owner, 128, 'owner');
  if (!['en','fr'].includes(spec.language)) throw Error('LANGUAGE');
  fields(spec.rights, ['dataClass','source','license'], 'rights');
  if (!['public','licensed-nonpersonal','synthetic'].includes(spec.rights.dataClass)) throw Error('INPUT_RIGHTS');
  text(spec.rights.source, 1000, 'source'); text(spec.rights.license, 1000, 'license');
  integer(spec.reviewMinutes, 1, 120, 'review capacity');
  const value = spec.inputs;
  if (adapter) {
    adapter.validate(clone(value));
  } else if (spec.family === 'reliability') {
    fields(value, ['source','low','high','cases'], 'reliability input');
    text(value.source, 2000, 'source'); rangeProgram(value.source);
    integer(value.low, -1000000, 1000000, 'low'); integer(value.high, value.low, 1000000, 'high');
    if (!Array.isArray(value.cases) || value.cases.length < 1 || value.cases.length > 2000) throw Error('CASES');
    value.cases.forEach(n => integer(n, -1000001, 1000001, 'case'));
  } else if (spec.family === 'performance') {
    fields(value, ['values','repetitions','repeats'], 'performance input');
    if (!Array.isArray(value.values) || value.values.length < 1 || value.values.length > 2000) throw Error('VALUES');
    value.values.forEach(n => integer(n, -1000000, 1000000, 'value'));
    integer(value.repetitions, 3, 15, 'repetitions'); integer(value.repeats, 1, 500, 'repeats');
  } else if (spec.family === 'documentation') {
    fields(value, ['markdown'], 'documentation input'); text(value.markdown, 100000, 'markdown');
    const matches = [...value.markdown.matchAll(/```successor-example\s*\n([\s\S]*?)\n```/g)];
    if (!matches.length || matches.length > 40) throw Error('EXAMPLES: use 1–40 successor-example JSON blocks');
    for (const match of matches) validateDocExample(parseBounded(match[1]));
  } else if (spec.family === 'public-data') {
    fields(value, ['csv','unit'], 'data input'); text(value.csv, 100000, 'csv'); text(value.unit, 80, 'unit');
    readRows(value.csv);
  } else {
    fields(value, ['coefficients','lower','upper','steps','tolerancePpm'], 'numerical input');
    if (!Array.isArray(value.coefficients) || !value.coefficients.length || value.coefficients.length > 7) throw Error('COEFFICIENTS');
    value.coefficients.forEach(n => integer(n, -1000, 1000, 'coefficient'));
    integer(value.lower, -100, 99, 'lower'); integer(value.upper, value.lower + 1, 100, 'upper');
    integer(value.steps, 2, 1000, 'steps'); if (value.steps % 2) throw Error('EVEN_STEPS_REQUIRED');
    integer(value.tolerancePpm, 0, 1000000, 'absolute tolerance in millionths');
  }
  canonical(spec);
  return clone(spec);
}

export async function semanticIdentity(spec, adapter = null) {
  const { name, language, ...semantic } = validate(spec, adapter);
  return digest('workbench-mission', semantic);
}

function rangeProgram(source) {
  const match = /^\s*export\s+function\s+contains\s*\(\s*value\s*,\s*low\s*,\s*high\s*\)\s*\{\s*return\s+low\s*(<=|<)\s*value\s*&&\s*value\s*(<=|<)\s*high\s*;\s*\}\s*$/.exec(source);
  if (!match) throw Error('SOURCE_GRAMMAR: only the documented bounded contains function is supported');
  return { lower: match[1], upper: match[2], execute: (value, low, high) =>
    (match[1] === '<=' ? low <= value : low < value) && (match[2] === '<=' ? value <= high : value < high) };
}
async function reliability(input, checkpoint) {
  const incumbent = rangeProgram(input.source);
  const cases = [...new Set([...input.cases, input.low - 1, input.low, input.high, input.high + 1])];
  const tests = cases.map(value => ({value, expected: value >= input.low && value <= input.high,
    actual: incumbent.execute(value, input.low, input.high)}));
  const attempts = [];
  for (const lower of ['<','<=']) for (const upper of ['<','<=']) {
    await checkpoint('testing');
    const source = `export function contains(value, low, high) { return low ${lower} value && value ${upper} high; }`;
    const method = rangeProgram(source);
    const failed = cases.filter(value => method.execute(value, input.low, input.high) !== (value >= input.low && value <= input.high));
    attempts.push({source, failed});
  }
  const selected = attempts.find(item => item.failed.length === 0);
  const defects = tests.filter(item => item.expected !== item.actual);
  const candidate = selected.source;
  const originalLines=input.source.trim().split(/\r?\n/);
  const patch = `--- a/contains.mjs\n+++ b/contains.mjs\n@@ -1,${originalLines.length} +1 @@\n${originalLines.map(line=>'-'+line).join('\n')}\n+${candidate}\n`;
  const checks = `// SPDX-License-Identifier: Apache-2.0\nimport assert from 'node:assert/strict';\nimport { contains } from './contains.mjs';\nfor (const c of ${JSON.stringify(tests.map(({value,expected})=>({value,expected})))}) assert.equal(contains(c.value, ${input.low}, ${input.high}), c.expected);\nconsole.log('All ${tests.length} fixed contract checks passed');\n`;
  return { decision: defects.length ? 'REPAIR_PROPOSED' : 'RETAIN_INCUMBENT', summary: {tests: tests.length, defects: defects.length, candidateFailures: 0},
    evidence: {tests, attempts, protectedCases: false, execution: 'Finite source grammar interpreted without eval or arbitrary host execution'},
    artifacts: [file('contains.mjs','text/javascript',candidate+'\n'), file('original.mjs','text/javascript',input.source+'\n'),
      file('check.mjs','text/javascript',checks),file('repair.patch','text/plain',defects.length ? patch : '# No repair needed.\n'),jsonFile('tests.json',tests)],
    limits: ['This adapter supports the declared range utility grammar only; arbitrary repositories need a separately isolated executor.', 'Public contract tests are engineering evidence, not independently protected qualification.'] };
}

async function performanceWork(input, checkpoint) {
  const sortUnique = values => values.slice().sort((a,b)=>a-b).filter((n,i,a)=>i===0 || n!==a[i-1]);
  const setUnique = values => [...new Set(values)].sort((a,b)=>a-b);
  const expected = sortUnique(input.values);
  const samples = { sort: [], set: [] };
  for (let r=0;r<input.repetitions;r++) {
    for (const name of (r%2 ? ['set','sort'] : ['sort','set'])) {
      await checkpoint('benchmarking');
      const fn = name==='sort' ? sortUnique : setUnique;
      const start = globalThis.performance.now(); let actual;
      for (let i=0;i<input.repeats;i++) actual=fn(input.values);
      samples[name].push(Math.max(0,Math.round((globalThis.performance.now()-start)*1000)));
      if (canonical(actual)!==canonical(expected)) throw Error('CRITICAL_CORRECTNESS_FAILURE');
    }
  }
  const median = values => [...values].sort((a,b)=>a-b)[Math.floor(values.length/2)];
  const selected = median(samples.set) < median(samples.sort) ? 'set' : 'sort';
  const report = { samplesMicrosecondsPerBatch: samples, batchRepeats: input.repeats,
    medianMicroseconds: {sort: median(samples.sort),set: median(samples.set)}, selected, output: expected,
    resourceTradeoff: 'Set retains a hash table and a unique-value array; sort copies and sorts all input values. Peak memory is not measured.' };
  return {decision: selected==='sort'?'RETAIN_INCUMBENT':'CANDIDATE_FASTER_IN_THIS_RUN',summary:{inputCount:input.values.length,outputCount:expected.length,correct:true},
    evidence:report,artifacts:[jsonFile('benchmark.json',report),jsonFile('values.json',input.values),
      file('unique.mjs','text/javascript',`// SPDX-License-Identifier: Apache-2.0\nexport const unique = ${selected==='set' ? "values => [...new Set(values)].sort((a,b)=>a-b)" : "values => values.slice().sort((a,b)=>a-b).filter((n,i,a)=>i===0 || n!==a[i-1])"};\n`)],
    limits:['Device/JIT/order effects can dominate small timings. This result does not establish general superiority.', 'Peak memory, monetary cost and human savings are unmeasured.']};
}

function validateDocExample(value) {
  fields(value,['operation','input','expected'],'documentation example');
  if (!['url-encode','url-decode','utf8-bytes'].includes(value.operation)) throw Error('UNSUPPORTED_SDK_OPERATION');
  if (typeof value.input!=='string' || value.input.length>4000 || typeof value.expected!=='string') throw Error('SDK_INPUT');
}
function sdk(value) {
  if(value.operation==='url-encode')return encodeURIComponent(value.input);
  if(value.operation==='url-decode')return decodeURIComponent(value.input);
  return String(new TextEncoder().encode(value.input).length);
}
async function documentation(input, checkpoint) {
  const checks=[]; let offset=0; let repaired='';
  for (const match of input.markdown.matchAll(/```successor-example\s*\n([\s\S]*?)\n```/g)) {
    await checkpoint('checking-examples');
    const value=parseBounded(match[1]); let actual=null,error=null;
    try { actual=sdk(value); } catch { error='INVALID_URI_ENCODING'; }
    checks.push({index:checks.length+1,...value,actual,error,passed:error===null&&actual===value.expected});
    repaired+=input.markdown.slice(offset,match.index)+(error ? match[0] : '```successor-example\n'+JSON.stringify({...value,expected:actual})+'\n```');
    offset=match.index+match[0].length;
  }
  repaired+=input.markdown.slice(offset);
  const failures=checks.filter(c=>!c.passed), errors=checks.filter(c=>c.error);
  return {decision:errors.length?'REPAIR_REQUIRED':failures.length?'DOCUMENTATION_CORRECTION_PROPOSED':'RETAIN_INCUMBENT',
    summary:{examples:checks.length,incorrectExamples:failures.length,invalidInputs:errors.length},evidence:{checks,contract:'URI component encoding/decoding and UTF-8 byte count; actual standard-library execution'},
    artifacts:[file('original-examples.md','text/markdown',input.markdown),file('checked-examples.md','text/markdown',repaired),jsonFile('example-checks.json',checks)],
    limits:['Only the named SDK operations run. Markdown outside the example blocks remains inert.', 'Proposed expected-value corrections require review; original failures remain in the evidence.']};
}

function readRows(csv) {
  const lines=[]; let row=[],cell='',quoted=false,closed=false;
  for(let i=0;i<csv.length;i++) {
    const ch=csv[i];
    if(quoted){if(ch==='"'){if(csv[i+1]==='"'){cell+='"';i++;}else{quoted=false;closed=true;}}else cell+=ch;}
    else if(ch==='"'&&!cell&&!closed)quoted=true;
    else if(ch===','){row.push(cell);cell='';closed=false;}
    else if(ch==='\n'||ch==='\r'){if(ch==='\r'&&csv[i+1]==='\n')i++;row.push(cell);lines.push(row);row=[];cell='';closed=false;}
    else{if(closed||ch==='"')throw Error('CSV_QUOTING');cell+=ch;}
    if(lines.length>2001)throw Error('CSV_ROW_LIMIT');
  }
  if(quoted)throw Error('CSV_UNCLOSED_QUOTE');
  if(row.length||cell||closed){row.push(cell);lines.push(row);}
  if(canonical(lines.shift())!==canonical(['group','amount'])||!lines.length)throw Error('CSV_HEADER: group,amount');
  return lines.map((item,index)=>{
    if(item.length!==2||!item[0].trim()||item[0].length>100||!/^[-]?(0|[1-9][0-9]{0,8})$/.test(item[1]))throw Error(`CSV_ROW: ${index+2}`);
    const amount=Number(item[1]); integer(amount,-1000000,1000000,'amount');
    return {group:item[0],amount};
  });
}
function csvCell(value) { const raw=String(value);return '"'+(/^[=+\-@\t\r]/.test(raw)?"'"+raw:raw).replaceAll('"','""')+'"'; }
async function publicData(input, checkpoint) {
  const rows=readRows(input.csv), groups=new Map();
  for(const row of rows){await checkpoint('analysing');const old=groups.get(row.group)||{group:row.group,count:0,total:0,min:row.amount,max:row.amount};old.count++;old.total+=row.amount;old.min=Math.min(old.min,row.amount);old.max=Math.max(old.max,row.amount);groups.set(row.group,old);}
  const summary=[...groups.values()].sort((a,b)=>a.group<b.group?-1:a.group>b.group?1:0);
  const total=rows.reduce((sum,row)=>sum+row.amount,0);
  if(summary.reduce((sum,row)=>sum+row.total,0)!==total)throw Error('RECONCILIATION_FAILED');
  const report='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SUCCESSOR data report</title><style>body{font:18px system-ui;max-width:60rem;margin:3rem auto;padding:1rem}td,th{padding:.6rem;text-align:left;border-bottom:1px solid #aaa}table{border-collapse:collapse}</style><h1>Public-data report</h1><p>'+html(rows.length)+' rows · '+html(input.unit)+' · exact total '+html(total)+'</p><table><thead><tr><th>Group</th><th>Count</th><th>Total</th><th>Minimum</th><th>Maximum</th></tr></thead><tbody>'+summary.map(row=>'<tr>'+[row.group,row.count,row.total,row.min,row.max].map(v=>'<td>'+html(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table><p>Descriptive results for the supplied data only. Coverage and causal interpretation require review.</p></html>';
  return {decision:'REPORT_READY_FOR_REVIEW',summary:{rows:rows.length,groups:summary.length,total,unit:input.unit},evidence:{groups:summary,reconciled:true},
    artifacts:[file('report.html','text/html',report),file('summary.csv','text/csv','group,count,total,min,max\n'+summary.map(row=>[csvCell(row.group),row.count,row.total,row.min,row.max].join(',')).join('\n')+'\n'),jsonFile('analysis.json',{total,groups:summary})],
    limits:['Exact descriptive arithmetic does not establish population coverage or causality.', 'CSV labels are escaped against formula interpretation; the source remains in the mission specification.']};
}

function fraction(n,d=1n){if(d===0n)throw Error('ZERO_DENOMINATOR');if(d<0n){n=-n;d=-d;}let a=n<0n?-n:n,b=d;while(b){const c=a%b;a=b;b=c;}return [n/(a||1n),d/(a||1n)];}
function add(a,b){return fraction(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);}
function mul(a,b){return fraction(a[0]*b[0],a[1]*b[1]);}
function abs(a){return [a[0]<0n?-a[0]:a[0],a[1]];}
function rationalText(a){return `${a[0]}/${a[1]}`;}
function polynomial(coefficients,x){let result=[0n,1n];for(const c of [...coefficients].reverse())result=add(mul(result,x),[BigInt(c),1n]);return result;}
async function numerical(input,checkpoint){
  const h=fraction(BigInt(input.upper-input.lower),BigInt(input.steps));let trap=[0n,1n],simpson=[0n,1n];
  for(let i=0;i<=input.steps;i++){await checkpoint('integrating');const y=polynomial(input.coefficients,add([BigInt(input.lower),1n],mul(h,[BigInt(i),1n])));trap=add(trap,mul(y,[i===0||i===input.steps?1n:2n,1n]));simpson=add(simpson,mul(y,[i===0||i===input.steps?1n:i%2?4n:2n,1n]));}
  trap=mul(trap,mul(h,[1n,2n]));simpson=mul(simpson,mul(h,[1n,3n]));
  let exact=[0n,1n];input.coefficients.forEach((c,i)=>{const n=BigInt(i+1);exact=add(exact,fraction(BigInt(c)*(BigInt(input.upper)**n-BigInt(input.lower)**n),n));});
  const error=value=>abs(add(value,[-exact[0],exact[1]]));const tolerance=fraction(BigInt(input.tolerancePpm),1000000n);
  const passes=value=>{const e=error(value);return e[0]*tolerance[1]<=tolerance[0]*e[1];};
  const evidence={analytic:rationalText(exact),trapezoid:rationalText(trap),simpson:rationalText(simpson),
    absoluteErrors:{trapezoid:rationalText(error(trap)),simpson:rationalText(error(simpson))},absoluteTolerance:rationalText(tolerance),
    passes:{trapezoid:passes(trap),simpson:passes(simpson)},arithmetic:'Exact reduced BigInt rational numbers; coefficients in increasing powers'};
  return {decision:passes(simpson)?'WITHIN_DECLARED_TOLERANCE':'REPAIR_REQUIRED',summary:{steps:input.steps,degree:input.coefficients.length-1,...evidence.passes},
    evidence,artifacts:[jsonFile('numerical.json',evidence),jsonFile('calculation-input.json',input)],
    limits:['This reconstructs polynomial quadrature under stated assumptions, not an arbitrary scientific paper.', 'Input uncertainty, physical-model validity and external replication are unmeasured.']};
}

const HANDLERS = {reliability,performance:performanceWork,documentation,'public-data':publicData,numerical};

export async function plan(spec, now = new Date().toISOString(), adapter = null) {
  const checked=validate(spec,adapter), identity=await semanticIdentity(checked,adapter);
  const mission=missionFor({name:checked.name,budget:'1',now});
  mission.missionId='work-'+identity.slice(0,24); mission.title=checked.name;
  mission.objective=(adapter?.manifest || REGISTRY.find(item=>item.id===checked.family)).scope;
  mission.budget.limitBaseUnits='0';mission.budget.maxJobs=7;
  mission.proofProtocol.minimumMargin=0;
  mission.allowedTools=['fixed-workbench-'+checked.family];
  mission.rights[0].dataClass=checked.rights.dataClass==='synthetic'?'synthetic':'public-licensed-nonpersonal';
  mission.rights[0].license=checked.rights.license;mission.rights[0].sourceId='mission-input';
  const proposed=createPortfolioJobs(mission), grouped=new Map();
  for(const job of proposed){if(!grouped.has(job.family))grouped.set(job.family,[]);grouped.get(job.family).push(job);}
  const jobs=[...grouped.entries()].map(([family,items])=>({...items[0],jobId:mission.missionId+':'+family,
    objective:items.map(item=>item.objective).join(' '),covers:items.flatMap(item=>item.covers),
    acceptance:{...items[0].acceptance,predicate:'Review the exact input, delivered artifacts and retained failures for: '+items.map(item=>item.objective).join(' ')}}));
  const order=['constitution','evidence','formation','challenge','verification','admission','renewal'];
  jobs.sort((a,b)=>order.indexOf(a.family)-order.indexOf(b.family));
  const edges=jobs.slice(1).map((job,i)=>({from:jobs[i].jobId,to:job.jobId,kind:'evidence'}));
  for(const edge of edges)jobs.find(job=>job.jobId===edge.to).authorizedInputs.push(edge.from);
  return compileJobs(mission,{jobs,edges,now});
}

export async function run(spec, {sourceHash,signal,onProgress=()=>{},onCheckpoint=async()=>{},clock=()=>globalThis.performance.now(),adapter=null}={}) {
  const input=validate(spec,adapter);
  if(!/^[a-f0-9]{64}$/.test(sourceHash||''))throw Error('SOURCE_IDENTITY_REQUIRED');
  const started=clock();let count=0;
  const checkpoint=async phase=>{
    await onCheckpoint();
    if(signal?.aborted)throw Error('CANCELLED');
    if(clock()-started>60000)throw Error('TIME_BUDGET_EXCEEDED');
    if(count++%25===0){onProgress(phase);await new Promise(resolve=>setTimeout(resolve,0));}
  };
  await checkpoint('planning');
  const missionDigest=await semanticIdentity(input,adapter), createdAt=new Date().toISOString();
  const frozen={schema:VERSION,missionDigest,sourceHash,adapter:input.family,adapterVersion:adapter?.manifest.version || 1,
    model:null,provider:null,authority:[],inputPolicy:input.rights,reviewMinutes:input.reviewMinutes};
  const releaseDigest=await digest('workbench-release',frozen);
  const compilation=await plan(input,createdAt,adapter);
  const result=await (adapter?.execute || HANDLERS[input.family])(input.inputs,checkpoint);
  fields(result,['decision','summary','evidence','artifacts','limits'],'adapter output');
  text(result.decision,128,'decision');
  if(!Array.isArray(result.artifacts)||result.artifacts.length<1||result.artifacts.length>12)throw Error('ARTIFACT_COUNT');
  await checkpoint('verifying');
  const artifacts=await Promise.all(result.artifacts.map(async artifact=>({...artifact,digest:await digest('workbench-artifact',artifact)})));
  const body={schema:VERSION,spec:input,createdAt,frozen,releaseDigest,compilation,result:{...result,artifacts},
    economics:{elapsedMilliseconds:Math.max(0,Math.round(clock()-started)),providerSpendBaseUnits:'0',settlementSpendBaseUnits:'0',
      computeCost:null,humanMinutes:null,reviewCapacityMinutes:input.reviewMinutes,allowanceIs:'UNFUNDED'},
    evaluation:{scope:'PUBLIC_LOCAL_EXECUTION',independentProof:false,admission:'HOLD',authority:[],settlement:'NOT_CONNECTED'},
    chronicle:[{kind:'local-result',decision:result.decision,missionDigest,releaseDigest,inheritedProof:false,inheritedAuthority:false}]};
  const pack={...body,integrityDigest:await digest('workbench-pack',body)};
  await inspectPack(pack,adapter);
  return pack;
}

export async function inspectPack(value, adapter = null) {
  fields(value,['schema','spec','createdAt','frozen','releaseDigest','compilation','result','economics','evaluation','chronicle','integrityDigest'],'pack');
  validate(value.spec,adapter);
  const {integrityDigest,...body}=value;
  if(integrityDigest!==await digest('workbench-pack',body))throw Error('PACK_INTEGRITY');
  if(value.frozen.missionDigest!==await semanticIdentity(value.spec,adapter)||value.releaseDigest!==await digest('workbench-release',value.frozen))throw Error('PACK_BINDING');
  if(!Array.isArray(value.result.artifacts)||value.result.artifacts.length>12)throw Error('PACK_ARTIFACTS');
  for(const artifact of value.result.artifacts){fields(artifact,['name','type','content','digest'],'artifact');
    if(['mission.json','evidence.json','READ_ME.txt','lifecycle.json','signed-receipt.json','source-key.txt'].includes(artifact.name)||
       /^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\.|$)/i.test(artifact.name)||artifact.name.endsWith('.'))throw Error('RESERVED_ARTIFACT_NAME');
    if(!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$/.test(artifact.name)||!['text/javascript','text/plain','text/csv','text/html','text/markdown','application/json'].includes(artifact.type)||typeof artifact.content!=='string'||artifact.content.length>200000)throw Error('ARTIFACT_POLICY');
    const {digest:hash,...content}=artifact;if(hash!==await digest('workbench-artifact',content))throw Error('ARTIFACT_INTEGRITY');}
  if(new Set(value.result.artifacts.map(item=>item.name)).size!==value.result.artifacts.length)throw Error('DUPLICATE_ARTIFACT');
  if(canonical(value.compilation)!==canonical(await plan(value.spec,value.createdAt,adapter)))throw Error('JOB_BINDING');
  return {spec:clone(value.spec),history:{missionDigest:value.frozen.missionDigest,releaseDigest:value.releaseDigest,decision:value.result.decision},
    authentication:'UNAUTHENTICATED_HISTORICAL_IMPORT',activeProof:[],activeAuthority:[]};
}

export function createWorkbench(adapters = []) {
  const installed = new Map();
  for(const adapter of adapters){
    fields(adapter,['manifest','validate','execute'],'installed adapter');
    const manifest=adapter.manifest;
    fields(manifest,['id','version','en','fr','scope','artifact'],'adapter manifest');
    if(!/^[a-z][a-z0-9-]{1,47}$/.test(manifest.id)||REGISTRY.some(item=>item.id===manifest.id)||installed.has(manifest.id))throw Error('ADAPTER_ID');
    integer(manifest.version,1,1000000,'adapter version');
    for(const key of ['en','fr','scope','artifact'])text(manifest[key],1000,key);
    if(typeof adapter.validate!=='function'||typeof adapter.execute!=='function')throw Error('ADAPTER_INTERFACE');
    installed.set(manifest.id,Object.freeze({...adapter,manifest:Object.freeze(clone(manifest))}));
  }
  const resolve=spec=>installed.get(spec.family)||null;
  return Object.freeze({registry:Object.freeze([...REGISTRY,...[...installed.values()].map(item=>item.manifest)]),
    validate:spec=>validate(spec,resolve(spec)),
    run:(spec,options)=>run(spec,{...options,adapter:resolve(spec)}),
    plan:(spec,now)=>plan(spec,now,resolve(spec)),
    inspectPack:pack=>inspectPack(pack,resolve(pack.spec))});
}
