// SPDX-License-Identifier: MIT
// Read-only source probe of the supplied local V93 interface. No browser, network,
// wallet, or production authority is exercised. Only rendering functions are
// replaced with no-ops; business functions are the supplied source unchanged.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';

const root = path.resolve(import.meta.dirname, '..', '..');
const relativeSource = 'beyond_beta/sources/supplied/goalos-v93-rsi-validated-skill-graph-ascension-lab-interface.html';
const bytes = fs.readFileSync(path.join(root, relativeSource));
const sourceSha256 = crypto.createHash('sha256').update(bytes).digest('hex');
if (sourceSha256 !== '3c3d606a76ec6a0ca1e854205032042284f83cff866e5eb3f3ae541675dac6ee') throw Error('Unexpected supplied source identity');
const scripts = [...bytes.toString('utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)];
if (scripts.length !== 1) throw Error('Expected one inline script');
const injection = `
render=()=>{}; log=()=>{}; pulse=()=>{}; earn=()=>{}; toast=()=>{};
globalThis.__audit={snapshot:()=>JSON.parse(JSON.stringify(state))};
`;
const script = scripts[0][1].replace(/\}\)\(\);\s*$/, injection + '\n})();');
if (!script.includes('globalThis.__audit')) throw Error('Probe injection failed');

function fresh(overrides={}) {
  const defaults={proofLevel:3,cycles:5,evidence:72,advantage:66,reuse:78,risk:26,novelty:62,visual:100,objective:'',method:'',limits:''};
  const elements=new Map(Object.entries({...defaults,...overrides}).map(([k,v])=>[k,{value:String(v)}]));
  const window={addEventListener(){}};
  const context=vm.createContext({window,document:{getElementById(id){if(!elements.has(id))elements.set(id,{value:''});return elements.get(id);}},setTimeout(){throw Error('No timer execution permitted in source probe');}});
  vm.runInContext(script,context,{timeout:1000,filename:relativeSource});
  return {call:(name,...args)=>window[name](...args),set:(name,value)=>elements.get(name).value=String(value),state:()=>context.__audit.snapshot()};
}
function candidate(overrides={}) {const a=fresh(overrides);a.call('loadPreset','trust');a.call('startMission');a.call('createJobs');a.call('completeJobs');return a;}
function changedFrontier(a,b){return Object.keys(a).some(k=>a[k]!==b[k]);}
const probes=[];
function record(id,kind,claim,run){const details=run();probes.push({id,kind,claim,...details});}

record('V93-C01','positive_control','An ordinary simulated candidate can pass the local Chronicle gate.',()=>{const a=candidate();a.call('admitSkill');const s=a.state();return {observed:s.chronicle.length===1&&s.skills[0].status==='admitted-chronicle',details:{chronicleEntries:s.chronicle.length,status:s.skills[0].status}};});
record('V93-C02','positive_control','A clean boot blocks next-mission generation.',()=>{const a=fresh();a.call('generateNextMission');const s=a.state();return {observed:s.cycle===0&&s.edges.length===0,details:{cycle:s.cycle,edges:s.edges.length}};});
record('V93-C03','positive_control','The supplied deliberately bad skill remains outside Chronicle.',()=>{const a=fresh();a.call('injectBadSkill');a.call('reuseSelected');const s=a.state();return {observed:s.chronicle.length===0&&!s.edges.some(e=>e.type==='future-prior'),details:{status:s.skills[0].status,chronicleEntries:s.chronicle.length}};});

record('V93-F01','draft_invariant_violation','Canonical promotion grants a reuse path without a Chronicle entry.',()=>{const a=candidate();a.call('canonicalReview');a.call('reuseSelected');const s=a.state();return {observed:s.chronicle.length===0&&s.canonical.length===1&&s.edges.some(e=>e.type==='future-prior'),details:{chronicleEntries:s.chronicle.length,canonicalEntries:s.canonical.length,status:s.skills[0].status,futurePriorEdges:s.edges.filter(e=>e.type==='future-prior')}};});
record('V93-F02','draft_invariant_violation','A retired skill still seeds a mission through historical Chronicle.',()=>{const a=candidate();a.call('admitSkill');a.call('retireSelected');a.call('generateNextMission');const s=a.state();return {observed:s.skills[0].status==='retired'&&s.cycle===1&&s.edges.some(e=>e.type==='future-prior'&&e.from===s.skills[0].id),details:{currentStatus:s.skills[0].status,cycle:s.cycle,futurePriorEdges:s.edges.filter(e=>e.type==='future-prior')}};});
record('V93-F03','draft_invariant_violation','The gate uses the mutable slider rather than the mission-bound L5 policy.',()=>{const a=candidate({proofLevel:5});a.call('admitSkill');const before=a.state();a.set('proofLevel',3);a.call('admitSkill');const after=a.state();return {observed:before.chronicle.length===0&&after.chronicle.length===1&&after.mission.proof_level==='L5 Chronicle / Formal',details:{frozenMissionProofLevel:after.mission.proof_level,skillProofLevel:after.skills[0].proofLevel,beforeStatus:before.skills[0].status,afterStatus:after.skills[0].status,currentSlider:3}};});
record('V93-F04','draft_invariant_violation','Repeating admission increments the frontier without new evidence or a new Chronicle entry.',()=>{const a=candidate();a.call('admitSkill');const before=a.state();a.call('admitSkill');const after=a.state();return {observed:before.chronicle.length===1&&after.chronicle.length===1&&changedFrontier(before.frontier,after.frontier),details:{entriesBefore:before.chronicle.length,entriesAfter:after.chronicle.length,frontierBefore:before.frontier,frontierAfter:after.frontier}};});
record('V93-F05','draft_invariant_violation','A composition can be admitted using inherited evidence IDs and no new job execution.',()=>{const a=candidate({evidence:100,advantage:100,reuse:100,risk:0,novelty:0});a.call('admitSkill');const before=a.state();a.call('composeSelected');a.call('admitSkill');const after=a.state();const child=after.skills.at(-1);return {observed:after.chronicle.length===2&&child.status==='admitted-chronicle'&&JSON.stringify(child.evidenceSet)===JSON.stringify(before.skills[0].evidenceSet)&&after.jobs.length===before.jobs.length,details:{parentEvidence:before.skills[0].evidenceSet,childEvidence:child.evidenceSet,jobsBefore:before.jobs.length,jobsAfter:after.jobs.length,childStatus:child.status}};});
record('V93-F06','draft_invariant_violation','Retirement can be undone by the same admission command and stale evidence.',()=>{const a=candidate();a.call('admitSkill');a.call('retireSelected');const before=a.state();a.call('admitSkill');const after=a.state();return {observed:before.skills[0].status==='retired'&&after.skills[0].status==='admitted-chronicle'&&JSON.stringify(before.skills[0].evidenceSet)===JSON.stringify(after.skills[0].evidenceSet),details:{beforeStatus:before.skills[0].status,afterStatus:after.skills[0].status,evidenceUnchanged:JSON.stringify(before.skills[0].evidenceSet)===JSON.stringify(after.skills[0].evidenceSet)}};});

const result={schema:'beyond-beta-v93-source-probe/v1',evidenceClass:'own-observation-of-supplied-local-demo-code',source:{path:relativeSource,sha256:sourceSha256},method:{execution:'Node vm with no provided network, process, filesystem, wallet, or browser globals',changes:'Rendering, logging, animation, badge and toast functions replaced with no-ops; read-only state snapshot injected. Business functions unmodified. Only public UI actions and UI form fields invoked.',scope:'Local source logic, not browser rendering, live protocol exploit, real proof, real job execution, or economic evidence.'},probes,allExpectedBehaviorsReproduced:probes.every(p=>p.observed)};
const out=process.argv[2]||path.join(import.meta.dirname,'v93-interface-probes.json');
fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({out,sourceSha256,probes:probes.length,allExpectedBehaviorsReproduced:result.allExpectedBehaviorsReproduced}));
if(!result.allExpectedBehaviorsReproduced)process.exitCode=1;
