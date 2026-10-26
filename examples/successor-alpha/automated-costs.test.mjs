// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {AUTOMATED_COST_SCHEMA,AUTOMATED_STAGES,evaluateAutomatedCosts,inspectAutomatedCosts} from './automated-costs.mjs';

const fact=(value,basis='estimated')=>({value,basis:value===null?'unknown':basis,reference:'Explicit test input; no live-cost observation'});
function scenario(name='base') {
  return {name,capacityRequestsPerMonth:fact(2000),utilizationBps:fact(5000),acceptanceBps:fact(8000),
    attemptsPerRequestPpm:fact(1250000),operations:AUTOMATED_STAGES.map(stage=>({id:stage,stage,
      frequency:stage==='execution'?'attempt':stage==='packaging'?'accepted':'request',
      unitsPerOccurrencePpm:fact(1000000),unitCostMicros:fact(stage==='execution'?100000:0),implementation:'modeled'})),
    residual:[{id:'human-exception',stage:'recovery',exceptionsPerRequestPpm:fact(10000),minutesPerException:fact(6),hourlyCostMicros:fact(60000000)}],
    monthly:[{id:'shared-maintenance',kind:'maintenance',amountMicros:fact(80000000),allocationBps:fact(5000)}],
    investments:[{id:'shared-development',kind:'development',amountMicros:fact(480000000),allocationBps:fact(5000),amortizationMonths:fact(12)}],
    humanBaseline:{minutesPerAccepted:fact(20),hourlyCostMicros:fact(60000000)}};
}
const record=()=>({schema:AUTOMATED_COST_SCHEMA,offeringId:'tested-job',currency:'USD',
  scenarios:['base','conservative','stress'].map(scenario)});
const first=raw=>evaluateAutomatedCosts(raw).scenarios[0];

test('three cost tiers reconcile attempts, failures, residual exceptions and shared allocation',()=>{
  const result=first(record());
  assert.deepEqual(result.volume,{requestsPerMonth:1000,attemptsPerMonth:1250,acceptedPerMonth:800,utilizationBps:5000,acceptanceBps:8000});
  assert.equal(result.costs.nextRequestMicros,185000);
  assert.equal(result.costs.marginalMicrosPerAccepted,231250);
  assert.equal(result.costs.variableMonthlyMicros,185000000);
  assert.equal(result.costs.sharedMonthlyMicros,40000000);
  assert.equal(result.costs.amortizedMonthlyMicros,20000000);
  assert.equal(result.costs.recurringMicrosPerAccepted,281250);
  assert.equal(result.costs.fullyLoadedMicrosPerAccepted,306250);
  assert.equal(result.residualHumanMinutesPerRequest,0.06);
  assert.equal(result.humanBaselineMicrosPerAccepted,20000000);
  assert.equal(result.comparison.fullyLoaded.outcome,'win');
  assert.equal(result.comparison.fullyLoaded.breakEvenHumanMinutes,0.30625);
  assert.equal(result.comparison.fullyLoaded.breakEvenHumanSeconds,19);
});

test('failed attempts are charged; per-accepted packaging is charged only for accepted output',()=>{
  const input=record(), s=input.scenarios[0];
  s.residual=[];s.monthly=[];s.investments=[];
  s.operations.find(row=>row.stage==='packaging').unitCostMicros=fact(50000);
  const result=first(input);
  assert.equal(result.costs.nextRequestMicros,165000);
  assert.equal(result.costs.marginalMicrosPerAccepted,206250);
  s.acceptanceBps=fact(4000);
  assert.equal(first(input).costs.marginalMicrosPerAccepted,362500);
});

test('lower utilization changes fixed allocation per accepted job without a second utilization divisor',()=>{
  const input=record(), base=first(input);
  input.scenarios[0].utilizationBps=fact(2500);
  const half=first(input);
  assert.equal(half.costs.marginalMicrosPerAccepted,base.costs.marginalMicrosPerAccepted);
  assert.equal(half.costs.sharedMonthlyMicros,base.costs.sharedMonthlyMicros);
  assert.equal(half.costs.recurringMicrosPerAccepted,331250);
  assert.equal(half.costs.fullyLoadedMicrosPerAccepted,381250);
});

test('one-time development is amortized once and never included in marginal or recurring work',()=>{
  const input=record(), before=first(input);
  input.scenarios[0].investments[0].amountMicros=fact(960000000);
  const after=first(input);
  assert.equal(after.costs.marginalMicrosPerAccepted,before.costs.marginalMicrosPerAccepted);
  assert.equal(after.costs.recurringMicrosPerAccepted,before.costs.recurringMicrosPerAccepted);
  assert.equal(after.costs.fullyLoadedMicrosPerAccepted,331250);
  assert.equal(after.components.investments[0].amortizedMonthlyMicros,40000000);
});

test('a wholly automated scenario replaces human work with charged software, preserving prior records',()=>{
  const input=record(), original=structuredClone(input), s=input.scenarios[0];
  s.residual=[];
  s.operations.find(row=>row.stage==='recovery').unitCostMicros=fact(10000);
  const result=first(input);
  assert.equal(result.residualHumanMinutesPerRequest,0);
  assert.equal(result.costs.nextRequestMicros,135000);
  assert.equal(original.scenarios[0].residual[0].exceptionsPerRequestPpm.value,10000);
  assert.equal(result.components.operations.find(row=>row.stage==='recovery').implementation,'modeled');
});

test('unknown execution, maintenance and development propagate only to affected cost tiers',()=>{
  for(const [edit,expected] of [
    [s=>s.operations[0].unitCostMicros=fact(null),[null,null,null]],
    [s=>s.monthly[0].amountMicros=fact(null),[231250,null,null]],
    [s=>s.investments[0].amountMicros=fact(null),[231250,281250,null]]
  ]) {
    const input=record();edit(input.scenarios[0]);const result=first(input);
    assert.deepEqual([result.costs.marginalMicrosPerAccepted,result.costs.recurringMicrosPerAccepted,result.costs.fullyLoadedMicrosPerAccepted],expected);
    assert.ok(result.unknownInputs.length);
  }
});

test('zero or unknown accepted volume is not free delivery',()=>{
  for(const value of [0,null]) {
    const input=record();input.scenarios[0].acceptanceBps=fact(value);const result=first(input);
    assert.equal(result.costs.marginalMicrosPerAccepted,null);
    assert.equal(result.costs.recurringMicrosPerAccepted,null);
    assert.equal(result.costs.fullyLoadedMicrosPerAccepted,null);
  }
  const input=record();input.scenarios[0].utilizationBps=fact(0);
  const result=first(input);
  assert.equal(result.costs.recurringMicrosPerAccepted,null);
  assert.equal(result.costs.fullyLoadedMicrosPerAccepted,null);
  assert.equal(result.costs.marginalMicrosPerAccepted,231250);
});

test('no human timing is invented; known wages still support cost break-even',()=>{
  const input=record();input.scenarios[0].humanBaseline.minutesPerAccepted=fact(null);
  const result=first(input);
  assert.equal(result.humanBaselineMicrosPerAccepted,null);
  assert.equal(result.comparison.fullyLoaded.outcome,'unknown');
  assert.equal(result.comparison.fullyLoaded.breakEvenHumanMinutes,0.30625);
  input.scenarios[0].humanBaseline.hourlyCostMicros=fact(0);
  assert.equal(first(input).comparison.fullyLoaded.breakEvenHumanMinutes,null);
});

test('unfavorable and exact break-even comparisons remain visible across scenarios',()=>{
  const input=record();
  input.scenarios[0].humanBaseline.minutesPerAccepted=fact(0);
  assert.equal(first(input).comparison.fullyLoaded.outcome,'loss');
  input.scenarios[0].residual=[];input.scenarios[0].monthly=[];input.scenarios[0].investments=[];
  input.scenarios[0].attemptsPerRequestPpm=fact(1000000);
  input.scenarios[0].acceptanceBps=fact(10000);
  input.scenarios[0].humanBaseline.minutesPerAccepted=fact(1);
  input.scenarios[0].humanBaseline.hourlyCostMicros=fact(6000000);
  assert.equal(first(input).comparison.fullyLoaded.outcome,'tie');
});

test('subcent costs retain precision until the final upward micro-unit rounding',()=>{
  const input=record(),s=input.scenarios[0];s.residual=[];s.monthly=[];s.investments=[];
  s.operations.forEach(row=>{row.unitCostMicros=fact(1);row.unitsPerOccurrencePpm=fact(100000);row.frequency='request';});
  s.acceptanceBps=fact(10000);
  const result=first(input);
  assert.equal(result.costs.nextRequestMicros,1);
  assert.equal(result.costs.fullyLoadedMicrosPerAccepted,1);
  assert.equal(result.components.operations.reduce((n,row)=>n+row.costMicrosPerRequest,0),8);
});

test('explicit no-cost inventories differ from omitted or unknown inventory',()=>{
  const input=record();input.scenarios[0].residual=[];input.scenarios[0].monthly=[];input.scenarios[0].investments=[];
  assert.equal(first(input).costs.sharedMonthlyMicros,0);
  for(const key of ['residual','monthly','investments']) {
    const bad=structuredClone(input);delete bad.scenarios[0][key];assert.throws(()=>first(bad),/fields/);
  }
  const bad=structuredClone(input);bad.scenarios[0].operations.pop();assert.throws(()=>first(bad),/Every workflow stage/);
});

test('cost identity duplication and incomplete provenance cannot double count or hide a cost',()=>{
  const duplicate=record();duplicate.scenarios[0].monthly[0].id='execution';assert.throws(()=>first(duplicate),/Duplicate cost identity/);
  for(const edit of [x=>x.basis='observed',x=>x.reference='',x=>x.value=-1,x=>x.value=0.5,x=>x.value=Infinity,
    x=>{x.value=null;x.basis='estimated';},x=>{x.value=0;x.basis='unknown';}]) {
    const bad=record();edit(bad.scenarios[0].operations[0].unitCostMicros);assert.throws(()=>first(bad));
  }
});

test('unsupported currencies, mixed fields and duplicate scenarios refuse',()=>{
  for(const edit of [x=>x.currency='AGIALPHA',x=>x.scenarios[0].currency='CAD',x=>x.scenarios[1].name='base',
    x=>x.offeringId='bad id',x=>x.scenarios[0].attemptsPerRequestPpm=fact(999999),
    x=>x.scenarios[0].investments[0].amortizationMonths=fact(0),x=>x.scenarios[0].utilizationBps=fact(10001)]) {
    const bad=record();edit(bad);assert.throws(()=>first(bad));
  }
});

test('owned frames reject mutable accessors and serializers without invoking them',()=>{
  let reads=0;
  const bad=record();Object.defineProperty(bad.scenarios[0].operations[0].unitCostMicros,'value',{get(){reads++;return -1;},enumerable:true});
  assert.throws(()=>evaluateAutomatedCosts(bad),/accessors/);assert.equal(reads,0);
  const serial=record();serial.toJSON=()=>{reads++;return record();};
  assert.throws(()=>inspectAutomatedCosts(serial),/serializers/);assert.equal(reads,0);
  const sparse=record();delete sparse.scenarios[0].operations[0];assert.throws(()=>first(sparse),/sparse/);
  const cyclic=record();cyclic.hidden=cyclic;assert.throws(()=>first(cyclic),/cycles/);
});

test('inspection and replay return owned deterministic outputs without changing supplied inputs',()=>{
  const input=record(),saved=JSON.stringify(input),inspection=inspectAutomatedCosts(input),before=evaluateAutomatedCosts(input);
  inspection.scenarios[0].operations[0].unitCostMicros.value=999;
  before.scenarios[0].components.operations[0].costMicrosPerRequest=999;
  assert.equal(JSON.stringify(input),saved);
  assert.equal(first(JSON.parse(saved)).costs.fullyLoadedMicrosPerAccepted,306250);
  assert.deepEqual(evaluateAutomatedCosts(JSON.parse(saved)),evaluateAutomatedCosts(input));
});

test('bounded monetary outputs fail rather than overflow or conceal huge failed-attempt costs',()=>{
  const input=record();input.scenarios[0].operations[2].unitCostMicros=fact(1000000000000);
  input.scenarios[0].operations[2].unitsPerOccurrencePpm=fact(100000000);
  input.scenarios[0].attemptsPerRequestPpm=fact(100000000);
  assert.throws(()=>first(input),/safe output bounds/);
});

test('many distinct amortization denominators keep approximate thresholds finite and JSON-safe',()=>{
  const primes=[];
  for(let number=2;number<=1200;number++) {
    if(!primes.some(divisor=>divisor*divisor<=number && number%divisor===0))primes.push(number);
  }
  const input=record(),s=input.scenarios[0];
  s.capacityRequestsPerMonth=fact(1);s.utilizationBps=fact(10000);s.acceptanceBps=fact(10000);
  s.operations.forEach(row=>row.unitCostMicros=fact(0));s.residual=[];s.monthly=[];
  s.investments=primes.slice(-128).map((months,i)=>({id:'investment-'+i,kind:'setup',amountMicros:fact(1),
    allocationBps:fact(10000),amortizationMonths:fact(months)}));
  s.humanBaseline.hourlyCostMicros=fact(1);
  const result=first(input),minutes=result.comparison.fullyLoaded.breakEvenHumanMinutes;
  const independentlySummed=primes.slice(-128).reduce((total,months)=>total+60/months,0);
  assert.ok(Number.isFinite(minutes));assert.ok(Math.abs(minutes-independentlySummed)<1e-10);
  assert.equal(JSON.parse(JSON.stringify(result)).comparison.fullyLoaded.breakEvenHumanMinutes,minutes);
});

test('published examples are explicit modeled scenarios and unknown template remains unresolved',()=>{
  const example=JSON.parse(readFileSync(new URL('./fixtures/automated-costs-example.json',import.meta.url)));
  const unknown=JSON.parse(readFileSync(new URL('./fixtures/automated-costs-unknown.json',import.meta.url)));
  const summary=evaluateAutomatedCosts(example);
  assert.equal(summary.scenarios.length,3);
  assert.ok(summary.scenarios.every(row=>row.costs.fullyLoadedMicrosPerAccepted!==null));
  assert.ok(summary.scenarios.some(row=>row.comparison.fullyLoaded.outcome==='loss'));
  assert.ok(evaluateAutomatedCosts(unknown).scenarios.every(row=>row.costs.fullyLoadedMicrosPerAccepted===null));
});
