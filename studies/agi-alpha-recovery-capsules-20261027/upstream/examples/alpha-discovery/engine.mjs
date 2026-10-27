// SPDX-License-Identifier: Apache-2.0
import { canonical, digest, parseBounded } from '../../docs/assets/successor/engine.mjs';

export const SCHEMA = 'alpha-discovery/v1';
export const CATEGORIES = ['benefit', 'cost', 'proof', 'risk', 'human'];
const ROLES = ['baseline', 'alternative', 'candidate'];
function keys(value, expected) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).sort().join('|') !== [...expected].sort().join('|')) throw Error('DISCOVERY_SCHEMA');
}
function text(value, limit = 2000) {
  if (typeof value !== 'string' || !value.trim() || value.length > limit) throw Error('DISCOVERY_TEXT');
}
export function validate(input) {
  keys(input, ['schema','mission','baseline','alternative','candidate','changed','rights','evidence','constraints','metrics']);
  if (input.schema !== SCHEMA) throw Error('DISCOVERY_VERSION');
  for (const key of ['mission','baseline','alternative','candidate','changed','rights']) text(input[key]);
  if (!Array.isArray(input.evidence) || input.evidence.length > 24) throw Error('DISCOVERY_EVIDENCE');
  input.evidence.forEach(row => {
    keys(row, ['kind','claim','reference','basis','supports']);
    if (!['research','expertise','experiment','lesson','change'].includes(row.kind) || !['illustrative','supplied-report'].includes(row.basis)) throw Error('DISCOVERY_EVIDENCE_BASIS');
    text(row.claim); text(row.reference);
    if (!Array.isArray(row.supports) || !row.supports.length || row.supports.length > 4 || row.supports.some(role => ![...ROLES,'change'].includes(role))) throw Error('DISCOVERY_EVIDENCE_LINK');
  });
  if (!Array.isArray(input.constraints) || !input.constraints.length || input.constraints.length > 12) throw Error('DISCOVERY_CONSTRAINTS');
  input.constraints.forEach(row => {
    keys(row, ['name','status','reference']); text(row.name); text(row.reference);
    if (!['unknown','reported-pass','reported-fail'].includes(row.status)) throw Error('DISCOVERY_CONSTRAINT_STATUS');
  });
  if (!Array.isArray(input.metrics) || input.metrics.length < 5 || input.metrics.length > 12 || CATEGORIES.some(category => !input.metrics.some(row => row.category === category))) throw Error('DISCOVERY_METRIC_CATEGORIES');
  input.metrics.forEach(row => {
    keys(row, ['name','unit','category','direction','minimumGain','baseline','alternative','candidate']);
    text(row.name, 160); text(row.unit, 80);
    if (!CATEGORIES.includes(row.category) || !['higher','lower'].includes(row.direction) || typeof row.minimumGain !== 'number' || !Number.isSafeInteger(row.minimumGain) || row.minimumGain < 0 || row.minimumGain > 1e12) throw Error('DISCOVERY_METRIC');
    ROLES.forEach(role => {
      const observation = row[role]; keys(observation, ['value','basis','reference']);
      if (observation.value !== null && (typeof observation.value !== 'number' || !Number.isSafeInteger(observation.value) || Math.abs(observation.value) > 1e12)) throw Error('DISCOVERY_VALUE');
      if (!['unknown','illustrative','supplied-report'].includes(observation.basis)) throw Error('DISCOVERY_BASIS');
      text(observation.reference);
      if (observation.basis === 'unknown' && observation.value !== null) throw Error('DISCOVERY_UNKNOWN_VALUE');
    });
  });
  return parseBounded(canonical(input));
}
export function example() {
  const observation = value => ({value,basis:value === null ? 'unknown' : 'illustrative',reference:'Illustrative planning input; no research or test result supplied.'});
  return {schema:SCHEMA,mission:'A longer-lasting, affordable battery with demanding safety requirements',baseline:'Keep the current qualified battery',alternative:'An existing qualified supplier option',candidate:'Investigate a revised cell/system design',changed:'A new design approach may be feasible; supporting evidence is missing.',rights:'Synthetic example only. Use public or authorized nonpersonal inputs.',
    evidence:[{kind:'change',claim:'A design possibility to investigate, not a demonstrated breakthrough.',reference:'Illustrative scenario, not a published finding.',basis:'illustrative',supports:['candidate','change']}],
    constraints:[{name:'Safety qualified for the intended application by a competent independent facility',status:'unknown',reference:'No physical safety tests supplied.'}],
    metrics:[['Service life','cycles','benefit','higher',100,600,700,900],['Lifecycle cost','same currency per service unit','cost','lower',0,100,95,90],['Qualification effort','person-hours','proof','lower',0,10,12,null],['Residual failure risk','same defined risk measure','risk','lower',0,null,null,null],['Operator burden','hours per service unit','human','lower',0,2,2,null]].map(([name,unit,category,direction,minimumGain,b,a,c]) => ({name,unit,category,direction,minimumGain,baseline:observation(b),alternative:observation(a),candidate:observation(c)}))};
}
export function analyze(raw) {
  const input = validate(raw), gaps = [], assumptions = [];
  input.constraints.forEach((row,index) => {
    if (row.status !== 'reported-pass') gaps.push({kind:'constraint',index,reason:row.status === 'reported-fail' ? 'reported-failure' : 'unknown',subject:row.name});
  });
  const comparisons = input.metrics.map((row,index) => {
    const missing = ROLES.filter(role => row[role].value === null || row[role].basis !== 'supplied-report');
    if (missing.length) gaps.push({kind:'measurement',index,reason:'missing-or-illustrative',subject:row.name,roles:missing});
    const computable = ROLES.every(role => row[role].value !== null);
    const sign = row.direction === 'higher' ? 1 : -1;
    const gainOverBaseline = computable ? (sign * (row.candidate.value - row.baseline.value) || 0) : null;
    const gainOverAlternative = computable ? (sign * (row.candidate.value - row.alternative.value) || 0) : null;
    const clearsComparison = computable && gainOverBaseline >= row.minimumGain && gainOverAlternative >= row.minimumGain;
    return {index,category:row.category,name:row.name,unit:row.unit,gainOverBaseline,gainOverAlternative,minimumGain:row.minimumGain,
      status:missing.length ? 'unestablished' : clearsComparison ? 'reported-threshold-met' : 'reported-threshold-missed',illustrative:missing.length > 0};
  });
  if (!input.evidence.some(row => row.supports.includes('change') && row.basis === 'supplied-report')) gaps.push({kind:'change',reason:'unsupported',subject:input.changed});
  ROLES.forEach(role => { if (!input.evidence.some(row => row.supports.includes(role) && row.basis === 'supplied-report')) gaps.push({kind:'evidence',reason:'unsupported',subject:input[role],role}); });
  const hypotheses = ROLES.map(role => ({role,option:input[role],whyNow:input.changed,evidence:input.evidence.map((row,index) => ({...row,index})).filter(row => row.supports.includes(role)),status:'hypothesis-not-discovery',question:role === 'candidate' ? 'Does the proposed change improve the mission over both credible comparators after all burdens?' : 'Could keeping or adopting this option meet the mission with less proof effort and risk?'}));
  input.evidence.forEach(row => assumptions.push({claim:row.claim,basis:row.basis,reference:row.reference}));
  const failure = input.constraints.some(row => row.status === 'reported-fail');
  const misses = comparisons.filter(row => row.status === 'reported-threshold-missed');
  // No automatic exchange rate between safety, money, proof effort and human burden.
  const positiveAdvantage = ['gainOverBaseline','gainOverAlternative'].every(key => comparisons.some(row => row.status === 'reported-threshold-met' && row[key] > 0));
  const decision = failure || misses.length || (!gaps.length && !positiveAdvantage) ? 'retain-incumbent' : gaps.length ? 'evidence-needed' : 'candidate-for-independent-review';
  const decisive = gaps[0] || (misses.length ? {kind:'comparison',index:misses[0].index,subject:misses[0].name} : {kind:'independent-review',subject:input.mission});
  const metric = Number.isInteger(decisive.index) && decisive.kind !== 'constraint' ? input.metrics[decisive.index] : null;
  const experiment = {status:'proposal-not-executed',target:decisive,
    hypothesis:metric ? `${input.candidate}: ${metric.direction} ${metric.name} than both comparators by at least ${metric.minimumGain} ${metric.unit}.` : decisive.subject,
    comparators:[input.baseline,input.alternative],
    measure:metric ? {name:metric.name,unit:metric.unit,direction:metric.direction,minimumGain:metric.minimumGain} : null,
    method:decisive.kind === 'constraint' ? 'Have a qualified reviewer define the smallest safe evidence review or accredited test. No physical test instructions are generated.' : 'Pre-register a like-for-like comparison with a qualified reviewer, exact inputs, measurement method, uncertainty and a held-out check before collecting new evidence.',
    stopConditions:input.constraints.map(row => row.name),budget:'Unspecified; agree a limit before commissioning.',acceptance:'Reviewer must verify provenance, comparability, uncertainty, all constraints and net burden. A local calculation is not independent proof.'};
  return {schema:'alpha-opportunity-analysis/v1',decision,hypotheses,comparisons,gaps,assumptions,experiment,
    retainedOption:input.baseline,authority:'none',independentProof:false,limitations:['Supplied reports are not verified here.','No literature search, provider call or physical experiment ran.','No safety, profitability, institutional admission or production fitness is established.']};
}
export async function createBrief(raw, sourceHash) {
  if (!/^[a-f0-9]{64}$/.test(sourceHash)) throw Error('DISCOVERY_SOURCE');
  const input = validate(raw), analysis = analyze(input);
  const content = {schema:'alpha-opportunity-brief/v1',sourceHash,input,inputDigest:await digest('alpha-discovery-input',input),analysis,
    handoff:{schema:'successor-unfunded-proposal/v1',purpose:input.mission,inputs:'Only the attached supplied discovery inputs; rights require recipient review.',
      gym:{stage:'formation-proposal',purpose:'Develop capability before real-world trust. The Gym trains; it does not certify.',simulationLimits:'No simulation has run. Any future simulation guides experiments and is not physical validation.',experimentalHistory:input.evidence.filter(row => ['experiment','lesson'].includes(row.kind)),preserveFailures:true,observations:input.metrics.map(row => ({name:row.name,unit:row.unit})),actions:['review-evidence','propose-bounded-test'],constraints:input.constraints,termination:analysis.experiment.stopConditions,reward:'Vector comparisons only; no scalar utility inferred.'},
      job:{status:'unfunded-draft',output:'Evidence ledger, comparison and experiment report',verifier:'Unassigned independent qualified reviewer',budget:null,expiry:null,permissions:[],prohibitions:['No spending','No provider calls','No private upload','No physical operation','No production activation'],rollback:'Retain incumbent; reject unsupported candidate.'},
      compatibility:[{repository:'AGI-Alpha-Agent-v0',capability:'Human-readable proposal; existing local workbench requires a separately selected supported task.'},{repository:'AGIJobsv0',capability:'Planning only; not JobRegistry v2 WorkSpec, assignment or AGIALPHA authorization.'},{repository:'AGIJobManager',capability:'Planning only; not Manager WorkSpec, USDC funding or authorization.'},{repository:'AGI-Fleet-Linux',capability:'Planning only; no qualified executor adapter or grant.'}],authority:'none'}};
  return {...content,briefDigest:await digest('alpha-discovery-brief',content)};
}
export function restoreInput(bytes) {
  const parsed = parseBounded(bytes);
  // Imported analysis and permission claims are discarded, never restored as authority.
  return validate(parsed.input || parsed);
}
