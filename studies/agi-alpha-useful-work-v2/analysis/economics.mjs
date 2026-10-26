// SPDX-License-Identifier: Apache-2.0
// Additive evidence mapping into the unchanged project cost and shadow-ledger APIs.
import {readFileSync, writeFileSync, mkdirSync, existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve, dirname, join} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {buildEconomics, costTemplate, humanThresholds} from '../canonical/value-compounds/src/economics.mjs';
import {replayLedger, calculateInvestment} from '../canonical/value-compounds/discovery/canonical/shadow-ledger.mjs';
import {AUTOMATED_STAGES} from '../canonical/value-compounds/discovery/canonical/automated-costs.mjs';

export const INPUT_SCHEMA = 'useful-work-economic-evidence/v2';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ARMS = ['manual', 'retained', 'conventional'];
const OWNERS = ['discovery', 'shared_investment', 'manual_construction', 'retained_construction',
  'conventional_construction', 'delivery', 'maintenance'];
const RESOURCE_FIELDS = ['wall_seconds', 'child_cpu_seconds', 'controller_cpu_seconds',
  'network_requests', 'network_response_bytes', 'runtime_model_calls', 'inference_tokens',
  'human_minutes', 'customer_minutes'];
const PINS = {
  'canonical/value-compounds/src/economics.mjs': 'd655a48c9321a67dd2a129169fc00b7476a523592e6ab1efdad7eb5ac1a87a99',
  'canonical/value-compounds/discovery/canonical/automated-costs.mjs': '0dfca3ae4e7ef1d17bc78521f91917ef068280cf832d3565c354de2085c52506',
  'canonical/value-compounds/discovery/canonical/shadow-ledger.mjs': 'cdc7c5a73593050a9af79b54589462e27f61b868e88ca6985d5cb639f3066d21'
};
const QUESTIONS = [
  'Did the mission enable a useful decision or action?',
  'Were complete delivery economics compelling against equivalent human work and strong practical tools?',
  'What executable capability was created or improved?',
  'Did fresh subsequent work repay complete incremental investment?',
  'What productive capacity or available resources resulted?',
  'Which next investment is justified, including adoption, maintenance, preserving reserves or stopping?'
];
const sha = raw => createHash('sha256').update(raw).digest('hex');
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value)
  && Object.getPrototypeOf(value) === Object.prototype;
const known = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const quantity = value => known(value) ? value : null;
const sumKnown = values => values.every(known) ? values.reduce((a,b)=>a+b,0) : null;
const unknownFact = reference => ({value:null,basis:'unknown',reference});

function assert(ok, message) {if (!ok) throw Error(message);}
function identifier(value, label) {
  assert(typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,49}$/.test(value), `Invalid ${label}`);
  return value;
}
function artifact(path, expected = null, root = ROOT, parse = true) {
  assert(typeof path === 'string' && path.length > 0, 'Evidence path required');
  const absolute = resolve(root,path), raw = readFileSync(absolute);
  assert(raw.length <= 20_000_000, 'Evidence exceeds finite 20 MB input bound');
  const hash = sha(raw);
  if (expected !== null) assert(hash === expected, `Evidence hash mismatch: ${path}`);
  return {path:absolute,sha256:hash,bytes:raw.length,data:parse ? JSON.parse(raw) : null};
}
const identity = ({path,sha256,bytes}) => ({path,sha256,bytes});

function resourcesFrom(raw) {
  const values = Object.fromEntries(RESOURCE_FIELDS.map(k=>[k,null]));
  values.wall_seconds = quantity(raw.wall_seconds);
  values.child_cpu_seconds = quantity(raw.child_cpu_seconds);
  values.controller_cpu_seconds = quantity(raw.meter_cpu_seconds ?? raw.process_cpu_seconds);
  values.network_requests = quantity(raw.network_requests ?? raw.runtime_network_requests);
  values.network_response_bytes = quantity(raw.network_response_bytes);
  values.runtime_model_calls = quantity(raw.runtime_model_calls);
  values.inference_tokens = quantity(raw.inference_tokens);
  values.human_minutes = quantity(raw.human_minutes);
  values.customer_minutes = quantity(raw.customer_minutes);
  return {...values,
    measured_cpu_seconds:sumKnown([values.child_cpu_seconds,values.controller_cpu_seconds]),
    peak_rss_kib:quantity(raw.child_peak_rss_kib ?? raw.self_peak_rss_kib),
    logical_storage_snapshot_bytes:quantity(raw.logical_storage_bytes_before_final_reports),
    model_count_policy:'A generic meter zero is not a child-model count; meter_model_calls is never substituted.'};
}

function aggregate(rows) {
  const included = rows.filter(r=>r.accounting_role === 'additive');
  const measures = {};
  for (const key of [...RESOURCE_FIELDS,'measured_cpu_seconds']) {
    const values = included.map(r=>r.resources[key]);
    const measured = values.filter(known);
    measures[key] = {total:values.length ? sumKnown(values) : null,
      measured_subtotal:measured.length ? measured.reduce((a,b)=>a+b,0) : null,
      measured_records:measured.length,unknown_records:values.length-measured.length};
  }
  const peaks = included.map(r=>r.resources.peak_rss_kib).filter(known);
  return {additive_records:included.length,nested_or_documentary_records:rows.length-included.length,
    failed_records:included.filter(r=>r.outcome === 'failed').length,measures,
    peak_rss_kib_observed_maximum:peaks.length ? Math.max(...peaks) : null,
    peak_rss_policy:'Maximum observed child peak; not a sum, simultaneous enterprise peak or complete memory bill.',
    wall_policy:'Sum of declared command intervals; not automatically end-to-end turnaround, human effort or money.',
    complete_money_usd:null};
}

function resourceInventory(entries, root) {
  assert(Array.isArray(entries) && entries.length <= 1000, 'Invalid bounded resource inventory');
  const ids = new Set(), additivePaths = new Set();
  const rows = entries.map(entry => {
    assert(plain(entry),'Resource entry must be an object');
    identifier(entry.id,'resource id'); assert(!ids.has(entry.id),'Duplicate resource id'); ids.add(entry.id);
    assert(OWNERS.includes(entry.ownership),'Unknown resource ownership');
    assert(['shared',...ARMS].includes(entry.arm),'Unknown resource arm');
    assert(['succeeded','failed','unknown'].includes(entry.outcome),'Unknown resource outcome');
    assert(['additive','nested_evidence','documentary'].includes(entry.accounting_role),'Explicit accounting_role required');
    assert(Array.isArray(entry.stages) && entry.stages.every(s=>AUTOMATED_STAGES.includes(s)), 'Invalid stage inventory');
    const evidence = artifact(entry.evidence_path,entry.evidence_sha256 ?? null,root,entry.format !== 'jsonl');
    if (entry.accounting_role === 'additive') {
      assert(!additivePaths.has(evidence.path),'Same resource receipt counted twice'); additivePaths.add(evidence.path);
    }
    const raw = evidence.data;
    let resources = Object.fromEntries([...RESOURCE_FIELDS,'measured_cpu_seconds','peak_rss_kib','logical_storage_snapshot_bytes'].map(k=>[k,null]));
    if (entry.format !== 'jsonl') {
      assert(plain(raw),'Resource receipt must be an object');
      if (entry.outcome === 'succeeded') assert(raw.complete_success !== false && raw.complete !== false
        && !(typeof raw.exit_code === 'number' && raw.exit_code !== 0), 'Failed receipt cannot be reclassified as successful');
      resources = resourcesFrom(raw);
    } else assert(entry.accounting_role === 'documentary','JSONL event logs are documentary, not additive resource bills');
    if (entry.ownership === 'delivery') {
      identifier(entry.mission_id,'delivery mission_id'); assert(ARMS.includes(entry.arm),'Delivery requires a concrete arm');
    }
    if (entry.accounting_role === 'nested_evidence') assert(typeof entry.covered_by === 'string','Nested evidence needs covered_by');
    return {...entry,evidence:identity(evidence),resources,
      receipt_schema:raw?.schema ?? null,receipt_complete_success:raw?.complete_success ?? raw?.complete ?? null,
      monetary_amount_minor:null};
  });
  for (const row of rows) if (row.accounting_role === 'nested_evidence')
    assert(rows.some(other=>other.id === row.covered_by && other.accounting_role === 'additive'), 'Missing additive parent for nested evidence');
  return rows;
}

function missionsFrom(entries, primaryArm, root) {
  assert(Array.isArray(entries) && entries.length <= 100,'Invalid bounded mission inventory');
  const ids = new Set(), triggers = new Set();
  return entries.map(mission => {
    identifier(mission.mission_id,'mission_id'); assert(!ids.has(mission.mission_id),'Duplicate mission_id'); ids.add(mission.mission_id);
    assert(['development','confirmation','control'].includes(mission.phase),'Invalid mission phase');
    assert(plain(mission.trigger),'Substantive trigger evidence required');
    for (const key of ['kind','before_identity','after_identity','reference'])
      assert(typeof mission.trigger[key] === 'string' && mission.trigger[key].length > 0, `Trigger ${key} required`);
    const substantive = mission.trigger.before_identity !== mission.trigger.after_identity && mission.phase !== 'control';
    const triggerKey = JSON.stringify([mission.trigger.kind,mission.trigger.before_identity,mission.trigger.after_identity]);
    if (substantive) {assert(!triggers.has(triggerKey),'Repeated unchanged trigger cannot count as another mission');triggers.add(triggerKey);}
    assert(Array.isArray(mission.outcomes) && mission.outcomes.length <= 3,'Invalid outcome inventory');
    const arms = new Set();
    const outcomes = mission.outcomes.map(outcome => {
      assert(ARMS.includes(outcome.arm) && !arms.has(outcome.arm),'Duplicate or unsupported outcome arm');arms.add(outcome.arm);
      assert(typeof outcome.accepted === 'boolean' || outcome.accepted === null,'Acceptance must be typed true/false/null');
      assert(typeof outcome.independently_verified === 'boolean','Independent verification flag required');
      assert(['SCOPED_COMPONENT_PRESERVED','COMPONENT_REGRESSION','INCOMPLETE_HOLD','NOT_EXECUTED'].includes(outcome.decision),'Unknown decision');
      if (outcome.accepted) assert(outcome.independently_verified && ['SCOPED_COMPONENT_PRESERVED','COMPONENT_REGRESSION'].includes(outcome.decision),
        'Accepted outcome needs verified actionable component verdict');
      const evidence = artifact(outcome.evidence_path,outcome.evidence_sha256 ?? null,root);
      return {...outcome,evidence:identity(evidence),
        acceptance_scope:'Explicit supplied acceptance mapping into pinned decision evidence; no count inferred from tests or prose.'};
    });
    const primary = outcomes.find(o=>o.arm === primaryArm);
    return {...mission,substantive,outcomes,
      primary_acceptance:!primary || primary.accepted === null ? 'unknown' : primary.accepted ? 'accepted':'rejected',
      freshness_status:mission.freshness_status ?? 'not_established'};
  });
}

function deliveryEnvelopes(envelopes, resources, missions) {
  assert(Array.isArray(envelopes) && envelopes.length <= 300,'Invalid delivery envelope inventory');
  const keys = new Set();
  return envelopes.map(envelope => {
    const key = `${envelope.mission_id}:${envelope.arm}`;
    assert(!keys.has(key),'Duplicate delivery envelope');keys.add(key);
    assert(ARMS.includes(envelope.arm) && missions.some(m=>m.mission_id === envelope.mission_id),'Unknown delivery envelope');
    assert(typeof envelope.scope_complete === 'boolean','Delivery scope completeness must be explicit');
    assert(Array.isArray(envelope.resource_ids),'Delivery resource references required');
    const rows = envelope.resource_ids.map(id=>{
      const row = resources.find(r=>r.id === id);assert(row,'Missing delivery resource reference');
      assert(row.ownership === 'delivery' && row.mission_id === envelope.mission_id && row.arm === envelope.arm,'Delivery ownership mismatch');
      return row;
    });
    assert(new Set(envelope.resource_ids).size === envelope.resource_ids.length,'Repeated delivery resource reference');
    const stages = new Set(rows.flatMap(r=>r.stages));
    const missing = AUTOMATED_STAGES.filter(stage=>!stages.has(stage));
    if (envelope.scope_complete) assert(missing.length === 0 && rows.some(r=>r.accounting_role === 'additive'),
      'Complete delivery must declare all stages and contain an additive receipt');
    return {...envelope,missing_stages:missing,resources:aggregate(rows),
      completeness_basis:'Input attestation of bounded stage coverage; monetary completeness is not implied.'};
  });
}

function symbolicSensitivity() {
  return {schema:'symbolic-investment-sensitivity/v1',horizon_missions:null,utilization:null,
    amortization_months:null,demand_evidence:null,
    canonical_unknown_investment:calculateInvestment({constructionCostMinor:null,failedConstructionCostMinor:null,
      maintenancePerReuseMinor:null,expectedSavingPerReuseMinor:null,remainingReuses:null}),
    equations:{
      net_benefit:'B(N) = sum_{j=1..N}(C_incumbent,j - C_retained,j - incremental_maintenance_j) - I_complete',
      repayment:'Repayment requires B(N) >= 0 with equivalent accepted outcomes and complete attributable costs.',
      constant_case_threshold:'If s-m > 0, N_break_even = ceil(I_complete/(s-m)); otherwise positive I has no finite payoff under that assumption.',
      acceptance_and_failures:'Cost per accepted delivery includes every failed attempt and correction in the numerator.',
      low_utilization:'Recurring cost per accepted delivery = total recurring delivery and shared costs / accepted deliveries; zero accepted output has no finite per-accepted cost.',
      financing:'Available_to_commit = cash - unpaid_obligations - required_reserves; simulated savings or allocations are not collections.'},
    money_inputs:{complete_investment_minor:null,saving_per_equivalent_accepted_mission_minor:null,
      incremental_maintenance_minor:null,available_to_commit_minor:null},
    numeric_price_or_horizon_assumed:false,positive_repayment_asserted:false};
}

export function buildStudyEconomics(input, {root=ROOT,inputIdentity=null}={}) {
  assert(plain(input) && input.schema === INPUT_SCHEMA,'Unsupported economic evidence schema');
  assert(ARMS.includes(input.primary_arm),'Explicit primary arm required');
  assert(input.actual_collections_minor === 0,'This nontransactional study has zero actual collections');
  for (const name of ['starting_capital_minor','approved_allocation_minor','customer_price_minor'])
    assert(input[name] === null,`${name} must retain the present unknown`);
  const capabilityId = identifier(input.capability_id ?? 'component-compatibility','capability_id');
  const canonicalSources = Object.entries(PINS).map(([path,hash])=>identity(artifact(path,hash,ROOT,false)));
  const resources = resourceInventory(input.resource_entries ?? [],root);
  const missions = missionsFrom(input.missions ?? [],input.primary_arm,root);
  for (const row of resources) if (row.ownership === 'delivery') assert(missions.some(m=>m.mission_id === row.mission_id),'Orphan delivery resource');
  const envelopes = deliveryEnvelopes(input.delivery_envelopes ?? [],resources,missions);
  const real = missions.filter(m=>m.substantive);
  for (const row of resources) row.canonical_account = row.ownership === 'delivery'
    && real.some(m=>m.mission_id === row.mission_id) ? row.mission_id : 'study-investment';
  const confirmation = real.filter(m=>m.phase === 'confirmation');
  const byArm = Object.fromEntries(ARMS.map(arm=>[arm,{
    accepted:real.filter(m=>m.outcomes.some(o=>o.arm===arm && o.accepted===true)).length,
    rejected:real.filter(m=>m.outcomes.some(o=>o.arm===arm && o.accepted===false)).length,
    unknown_or_not_executed:real.filter(m=>!m.outcomes.some(o=>o.arm===arm && typeof o.accepted === 'boolean')).length,
    confirmation_accepted:confirmation.filter(m=>m.outcomes.some(o=>o.arm===arm && o.accepted===true)).length,
    delivery_resources:aggregate(resources.filter(r=>r.ownership==='delivery' && r.arm===arm))
  }]));
  const costRecord = costTemplate(capabilityId);
  const fixedGroups = ['discovery','shared_investment','manual_construction','retained_construction','conventional_construction'];
  for (const scenario of costRecord.scenarios) scenario.investments = fixedGroups.map(group=>({
    id:group.replaceAll('_','-'),kind:'development',
    amountMicros:unknownFact(`Complete ${group} includes its failed attempts and model/tool work; unpriced.`),
    allocationBps:{value:10000,basis:'estimated',reference:'This row means the attributable group only, not an assumed enterprise reinvestment share.'},
    amortizationMonths:unknownFact('No demand-supported allocation horizon is available.')}));
  const base = buildEconomics({capability_id:capabilityId,canonical_cost_record:costRecord,
    observed:{collections_minor:0,missions:real.map(m=>({mission_id:m.mission_id,acceptance:m.primary_acceptance,
      reference:`${m.phase}; primary arm ${input.primary_arm}; trigger ${m.trigger.reference}`})),
      resources:null,limitations:['No actual customer price, paid demand, matched human duration, complete construction bill or approved funding allocation.']}},
    {canonical_sources:canonicalSources,metrics_reference:inputIdentity ? `Economic mapping SHA256 ${inputIdentity.sha256}`:'Explicit supplied economic evidence mapping'});
  const {investment_sensitivity:_unusedAssumedHorizonGrid,...canonical} = base;
  const ledger = structuredClone(base.canonical_ledger);
  ledger.events = ledger.events.filter(e=>e.id !== 'study-investment:cost:capability');
  for (const group of fixedGroups) for (const state of ['successful-or-unclassified','failed']) {
    const rows = resources.filter(r=>r.ownership===group && (state==='failed' ? r.outcome==='failed':r.outcome!=='failed'));
    ledger.events.push({id:`study-investment:capability:${group}:${state==='failed'?'failed':'other'}`,
      type:'cost',missionId:'study-investment',category:'capability',amountMinor:null,basis:'unknown',
      reference:`Same tested capability; ${group}, ${state}; ${rows.length} attributable evidence records. Empty inventory is missing coverage, not free construction.`});
  }
  const ledgerSummary = replayLedger(ledger);
  const artifacts = (input.capability_artifacts ?? []).map(path=>identity(artifact(path,null,root,false)));
  const groups = Object.fromEntries(OWNERS.map(group=>[group,aggregate(resources.filter(r=>r.ownership===group))]));
  const operationalPairs = [];
  for (const mission of confirmation) for (const comparator of ['manual','conventional']) {
    const retainedOutcome = mission.outcomes.find(o=>o.arm==='retained');
    const comparatorOutcome = mission.outcomes.find(o=>o.arm===comparator);
    const retained = envelopes.find(e=>e.mission_id===mission.mission_id && e.arm==='retained');
    const compared = envelopes.find(e=>e.mission_id===mission.mission_id && e.arm===comparator);
    const fresh = mission.freshness_status === 'untouched_before_protocol_freeze';
    const equivalent = fresh && retainedOutcome?.accepted===true && comparatorOutcome?.accepted===true
      && retained?.scope_complete===true && compared?.scope_complete===true;
    const delta = key => equivalent && known(retained.resources.measures[key].total) && known(compared.resources.measures[key].total)
      ? compared.resources.measures[key].total - retained.resources.measures[key].total:null;
    operationalPairs.push({mission_id:mission.mission_id,comparator,freshness_status:mission.freshness_status,
      equivalent_accepted_complete_scope:equivalent,
      wall_seconds_reduction:delta('wall_seconds'),measured_cpu_seconds_reduction:delta('measured_cpu_seconds'),
      monetary_saving_minor:null,failed_attempts_still_in_campaign_resources:true});
  }
  const acceptedPrimary = real.filter(m=>m.primary_acceptance==='accepted').length;
  const finance = {actual_collections_minor:0,starting_capital_minor:null,approved_allocation_minor:null,
    customer_price_minor:null,complete_delivery_cost_minor:null,complete_investment_minor:null,
    obligations_minor:null,reserves_minor:null,available_surplus_minor:null,available_to_commit_minor:null,
    actual_new_paid_commitments_minor:0,financial_transactions:0,
    operational_benefit:'Assess separately using accepted scope and complete measured resource envelopes.',
    monetary_repayment:'NOT_ESTABLISHED',financeable_expansion:'NOT_ESTABLISHED',economic_admission:'HOLD'};
  const answers = [
    {question:QUESTIONS[0],status:acceptedPrimary ? 'OBSERVED_BOUNDED_INTERNAL_OUTPUTS':'NOT_YET_ESTABLISHED',
      answer:`${acceptedPrimary} accepted primary-arm packages among ${real.length} distinct substantive triggers; customer use, paid demand and action completion remain separately unobserved.`},
    {question:QUESTIONS[1],status:'COMPLETE_COMMERCIAL_COMPARISON_UNKNOWN',
      answer:'Complete inference/construction/delivery prices and matched human duration are unknown. Report accepted scope and physical resources against both practical automated comparators; no commercial superiority follows.'},
    {question:QUESTIONS[2],status:artifacts.length ? 'EXECUTABLE_ARTIFACTS_IDENTIFIED':'ARTIFACT_INVENTORY_INCOMPLETE',
      answer:input.capability_description ?? 'One retained component-compatibility evidence capability; implementation identity must be supplied.',artifacts},
    {question:QUESTIONS[3],status:'MONETARY_REPAYMENT_NOT_ESTABLISHED',
      answer:'Fresh-work resource differences, if present, do not identify complete construction, inference and maintenance money. Both builders and failed construction remain charged to this finite study account.'},
    {question:QUESTIONS[4],status:'OUTPUTS_OBSERVED_CAPACITY_AND_CASH_UNIDENTIFIED',
      answer:'Distinct accepted outputs are counted by arm. Future monthly capacity, demand, available cash and financeable capacity increase are unknown; earlier completion is not additional eventual output.'},
    {question:QUESTIONS[5],status:'NO_FINANCED_EXPANSION_JUSTIFIED',
      answer:'Any engineering adoption requires the frozen empirical gate. Monetary expansion remains on HOLD; obtain actual complete cost and approved funds or a real receipt before a paid commitment. Preserving or retiring the capability remains an evidence-based option.'}
  ];
  return {...canonical,schema:'useful-work-economics/v2',scope:'Nontransactional bounded component-compatibility research; one tested capability, existing canonical accounting APIs.',
    input_provenance:inputIdentity,canonical_sources:canonicalSources,
    canonical_ledger:ledger,canonical_ledger_summary:ledgerSummary,
    accounting_status:{...canonical.accounting_status,approved_allocation_minor:null,financeable_capacity_increase_proven:false},
    finance,investment_sensitivity:symbolicSensitivity(),human_comparison:humanThresholds([]),
    manual_incumbent_status:'Actual first manual assembly/probe created inside this study; construction is charged. It is not a measured competent-human, no-AI service baseline.',
    human_counterfactual_status:'Modeled wage-only equivalent-scope threshold; human duration, responsibility, effort and customer price unmeasured.',
    missions,distinct_substantive_missions:real.length,nonmission_or_noop_records:missions.length-real.length,
    declared_confirmation_missions:confirmation.length,actual_paid_customer_missions:0,
    outcomes_by_arm:byArm,primary_arm:input.primary_arm,delivery_envelopes:envelopes,
    resource_records:resources,resource_campaign:aggregate(resources),resources_by_ownership:groups,
    empirical_resources:{campaign:aggregate(resources),by_ownership:groups},
    cost_template_status:'Unknown canonical template with explicit attributable construction groups; no numeric utilization, demand, amortization, service price or cost selected.',
    construction_and_unsuccessful_resources:aggregate(resources.filter(r=>fixedGroups.includes(r.ownership))),
    unsuccessful_resources:aggregate(resources.filter(r=>r.outcome==='failed')),
    operational_pairs:operationalPairs,investment_questions:answers,
    completeness:{monetary_complete:false,matched_human_duration_measured:false,
      all_delivery_scopes_attested:real.length>0 && real.every(m=>envelopes.some(e=>e.mission_id===m.mission_id && e.arm===input.primary_arm && e.scope_complete)),
      raw_logs_do_not_imply_billing:true,missing_inventory_is_not_zero:true,
      amortization_or_utilization_assumed:false},
    attribution_notes:[
      'Resource ownership categories are exclusive; failed attempts remain within their actual builder/shared owner.',
      'The canonical study-investment account is one accounting container, not a customer mission or a second asset.',
      'Documentary and nested observations do not add resource charges on top of an encompassing additive receipt.',
      'Shared discovery/evaluation and both newly constructed builders are included; legacy reuse does not become free new construction.',
      'The canonical reinvestmentBps default is an inert API value, not a selected financing policy or earned allocation.',
      'Unsuccessful or incomplete work retains its resources while contributing no accepted output.',
      'Acceptance/freshness mappings are explicit input assertions tied to evidence; this script does not replace technical validation.'
    ]};
}

function main() {
  const args = process.argv.slice(2), options = {};
  for (let i=0;i<args.length;i+=2) {
    assert(['--input','--out','--root'].includes(args[i]) && args[i+1],
      'Usage: node analysis/economics.mjs --input economic-evidence.json --out new-output-directory [--root project-root]');
    assert(!options[args[i]],'Duplicate option');options[args[i]]=resolve(args[i+1]);
  }
  assert(options['--input'] && options['--out'],'Input and output required');
  assert(!existsSync(options['--out']),'Refusing to overwrite an economic result edition');
  const source = artifact(options['--input']);
  const result = buildStudyEconomics(source.data,{root:options['--root'] ?? ROOT,inputIdentity:identity(source)});
  mkdirSync(options['--out'],{recursive:true});
  const files = {'economics.json':result,'canonical-ledger.json':result.canonical_ledger,
    'canonical-ledger-summary.json':result.canonical_ledger_summary,
    'canonical-cost-input.json':result.canonical_cost_input,'canonical-cost-output.json':result.canonical_cost_projection,
    'resource-accounts.json':{records:result.resource_records,campaign:result.resource_campaign,ownership:result.resources_by_ownership},
    'investment-questions.json':result.investment_questions,'symbolic-sensitivities.json':result.investment_sensitivity};
  for (const [name,data] of Object.entries(files)) writeFileSync(join(options['--out'],name),JSON.stringify(data,null,2)+'\n');
  console.log(JSON.stringify({status:'COMPLETE_ACCOUNTING_MAPPING',economic_admission:'HOLD',
    actual_collections_minor:0,complete_cost_minor:null,substantive_missions:result.distinct_substantive_missions,
    accepted_primary_outputs:result.accepted_research_missions,output:options['--out']}));
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) main();
