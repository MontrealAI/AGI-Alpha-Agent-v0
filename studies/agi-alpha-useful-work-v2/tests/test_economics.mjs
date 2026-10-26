// SPDX-License-Identifier: Apache-2.0
// Synthetic accounting controls; no experimental outcomes or market observations.
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {buildStudyEconomics,INPUT_SCHEMA} from '../analysis/economics.mjs';

const empty = () => ({schema:INPUT_SCHEMA,capability_id:'component-compatibility',primary_arm:'retained',
  actual_collections_minor:0,starting_capital_minor:null,approved_allocation_minor:null,customer_price_minor:null,
  missions:[],resource_entries:[],delivery_envelopes:[],capability_artifacts:[]});
function fixture(t) {
  const root = mkdtempSync(join(tmpdir(),'component-economics-control-'));
  t.after(()=>rmSync(root,{recursive:true,force:true}));
  const write = (name,body) => writeFileSync(join(root,name),JSON.stringify(body));
  write('decision.json',{synthetic_control_only:true});
  return {root,write,input:empty()};
}
const mission = (id='m1') => ({mission_id:id,phase:'confirmation',freshness_status:'untouched_before_protocol_freeze',
  trigger:{kind:'dependency_bundle',before_identity:'before',after_identity:'after',reference:'synthetic control'},
  outcomes:[{arm:'retained',accepted:true,independently_verified:true,decision:'SCOPED_COMPONENT_PRESERVED',evidence_path:'decision.json'}]});
const receipt = (id,path='receipt.json') => ({id,ownership:'retained_construction',arm:'retained',outcome:'failed',
  accounting_role:'additive',stages:['correction'],evidence_path:path});

test('unknown money remains unknown under unchanged canonical modules',()=>{
  const out=buildStudyEconomics(empty());
  assert.equal(out.finance.actual_collections_minor,0);
  for (const key of ['starting_capital_minor','approved_allocation_minor','customer_price_minor',
    'complete_delivery_cost_minor','complete_investment_minor','available_surplus_minor','available_to_commit_minor'])
    assert.equal(out.finance[key],null);
  assert.equal(out.canonical_ledger_summary.observed.revenue,0);
  assert.equal(out.canonical_ledger_summary.observed.fullCost,null);
  assert.equal(out.canonical_ledger_summary.observed.availableSurplus,null);
  for(const s of out.canonical_cost_projection.scenarios) {
    assert.equal(s.costs.marginalMicrosPerAccepted,null);
    assert.equal(s.costs.recurringMicrosPerAccepted,null);
    assert.equal(s.costs.fullyLoadedMicrosPerAccepted,null);
  }
  assert.equal(out.investment_sensitivity.horizon_missions,null);
  assert.equal(out.investment_sensitivity.numeric_price_or_horizon_assumed,false);
});

test('no fabricated collection or price accepted',()=>{
  const input=empty(); input.actual_collections_minor=1;
  assert.throws(()=>buildStudyEconomics(input),/zero actual collections/);
  input.actual_collections_minor=0;input.customer_price_minor=1;
  assert.throws(()=>buildStudyEconomics(input),/present unknown/);
});

test('failed construction resources remain charged and no output is counted',t=>{
  const {root,write,input}=fixture(t);
  write('receipt.json',{schema:'alpha-measured-command/v1',complete_success:false,exit_code:1,
    wall_seconds:2,child_cpu_seconds:0.2,meter_cpu_seconds:0.1,money_usd:null});
  input.resource_entries=[receipt('failed')];
  const out=buildStudyEconomics(input,{root});
  assert.equal(out.unsuccessful_resources.measures.wall_seconds.total,2);
  assert.equal(out.resource_campaign.failed_records,1);
  assert.equal(out.accepted_research_missions,0);
  assert.equal(out.resource_campaign.measures.runtime_model_calls.total,null);
  assert.equal(out.resource_records[0].canonical_account,'study-investment');
});

test('failed receipt cannot be classified successful',t=>{
  const {root,write,input}=fixture(t);
  write('receipt.json',{complete_success:false,wall_seconds:1});
  input.resource_entries=[{...receipt('x'),outcome:'succeeded'}];
  assert.throws(()=>buildStudyEconomics(input,{root}),/reclassified/);
});

test('nested measurements are not double counted',t=>{
  const {root,write,input}=fixture(t);
  write('outer.json',{wall_seconds:5,child_cpu_seconds:1,meter_cpu_seconds:0.1});
  write('inner.json',{wall_seconds:4,child_cpu_seconds:0.9,meter_cpu_seconds:0});
  input.resource_entries=[receipt('outer','outer.json'),
    {...receipt('inner','inner.json'),accounting_role:'nested_evidence',covered_by:'outer'}];
  const out=buildStudyEconomics(input,{root});
  assert.equal(out.resource_campaign.measures.wall_seconds.total,5);
  assert.equal(out.resource_campaign.nested_or_documentary_records,1);
});

test('duplicate additive receipt refused',t=>{
  const {root,write,input}=fixture(t);write('receipt.json',{wall_seconds:1});
  input.resource_entries=[receipt('a'),receipt('b')];
  assert.throws(()=>buildStudyEconomics(input,{root}),/counted twice/);
});

test('duplicate substantive trigger refused despite different mission IDs',t=>{
  const {root,input}=fixture(t);input.missions=[mission('a'),mission('b')];
  assert.throws(()=>buildStudyEconomics(input,{root}),/another mission/);
});

test('unchanged request is not a counted mission',t=>{
  const {root,input}=fixture(t);const row=mission();row.trigger.after_identity='before';input.missions=[row];
  const out=buildStudyEconomics(input,{root});
  assert.equal(out.distinct_substantive_missions,0);assert.equal(out.accepted_research_missions,0);
  assert.equal(out.nonmission_or_noop_records,1);
});

test('incomplete outcome cannot be admitted by an accepted flag',t=>{
  const {root,input}=fixture(t);const row=mission();row.outcomes[0].decision='INCOMPLETE_HOLD';input.missions=[row];
  assert.throws(()=>buildStudyEconomics(input,{root}),/verified actionable/);
});

test('isolated execution receipt is not complete delivery',t=>{
  const {root,write,input}=fixture(t);input.missions=[mission()];write('receipt.json',{wall_seconds:1});
  input.resource_entries=[{...receipt('one'),ownership:'delivery',mission_id:'m1',stages:['execution']}];
  input.delivery_envelopes=[{mission_id:'m1',arm:'retained',scope_complete:true,resource_ids:['one']}];
  assert.throws(()=>buildStudyEconomics(input,{root}),/declare all stages/);
});

test('generic meter own zero model count is not child zero',t=>{
  const {root,write,input}=fixture(t);
  write('receipt.json',{wall_seconds:1,meter_model_calls:0,runtime_model_calls:null});
  input.resource_entries=[receipt('one')];
  const out=buildStudyEconomics(input,{root});
  assert.equal(out.resource_campaign.measures.runtime_model_calls.total,null);
  assert.equal(out.resource_campaign.measures.runtime_model_calls.measured_subtotal,null);
});
