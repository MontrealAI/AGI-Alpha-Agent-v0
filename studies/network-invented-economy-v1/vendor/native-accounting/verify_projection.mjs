// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {AUTOMATED_STAGES,evaluateAutomatedCosts} from './automated-costs.mjs';
import {calculateInvestment,replayLedger} from './shadow-ledger.mjs';
import {projectScenario} from './project_scenario.mjs';

const checks = [];
const check = (name,body) => {body();checks.push({name,result:'PASS'});};
const assumed = value => ({value,basis:'estimated',reference:'Constructed arithmetic fixture; not an empirical estimate'});
const unknown = () => ({value:null,basis:'unknown',reference:'No human-work observation supplied in this arithmetic fixture'});
const stageDollars = [40,80,400,150,40,20,10,20];
const scenario = name => ({
  name,capacityRequestsPerMonth:assumed(4),utilizationBps:assumed(5000),acceptanceBps:assumed(7500),
  attemptsPerRequestPpm:assumed(1000000),
  operations:AUTOMATED_STAGES.map((stage,i)=>({
    id:`${stage}-cost`,stage,frequency:'request',unitsPerOccurrencePpm:assumed(1000000),
    unitCostMicros:assumed(stageDollars[i]*1000000),implementation:'modeled'
  })),
  residual:[],
  monthly:[{id:'shared-cost',kind:'capacity',amountMicros:assumed(180000000),allocationBps:assumed(10000)}],
  investments:[{id:'setup-cost',kind:'setup',amountMicros:assumed(1200000000),allocationBps:assumed(10000),
    amortizationMonths:assumed(12)}],
  humanBaseline:{minutesPerAccepted:unknown(),hourlyCostMicros:unknown()}
});
const costRecord = {schema:'alpha-automated-costs/v1',offeringId:'network-mechanism-arithmetic-fixture',currency:'USD',
  scenarios:['base','conservative','stress'].map(scenario)};
const costSummary = evaluateAutomatedCosts(costRecord);
check('Native automated-cost schema accepts every explicitly priced workflow stage',()=>{
  const result=costSummary.scenarios[0];
  assert.equal(result.costs.nextRequestMicros,760000000);
  assert.equal(result.costs.recurringMicrosPerAccepted,1133333334);
  assert.equal(result.costs.fullyLoadedMicrosPerAccepted,1200000000);
  assert.equal(result.residualHumanMinutesPerRequest,0);
});
check('Unknown matched human effort remains unknown',()=>{
  assert.equal(costSummary.scenarios[0].comparison.fullyLoaded.outcome,'unknown');
});
check('Missing workflow-stage cost is rejected',()=>{
  const record=structuredClone(costRecord);record.scenarios[0].operations.pop();
  assert.throws(()=>evaluateAutomatedCosts(record),/Every workflow stage/);
});
check('Duplicate cost identity is rejected',()=>{
  const record=structuredClone(costRecord);record.scenarios[0].operations[1].id=record.scenarios[0].operations[0].id;
  assert.throws(()=>evaluateAutomatedCosts(record),/Duplicate cost identity/);
});
check('Unknown production cost cannot silently become zero',()=>{
  const record=structuredClone(costRecord);record.scenarios[0].operations[2].unitCostMicros=unknown();
  assert.equal(evaluateAutomatedCosts(record).scenarios[0].costs.fullyLoadedMicrosPerAccepted,null);
});
const fixture = [{id:'simulated-001',acceptance:'accepted',modeledCollectionsMinor:500000,
  costsMinor:{delivery:76000,business:18000,capability:120000,maintenance:2000},reserveMinor:20000,obligationMinor:5000}];
const projection=projectScenario(JSON.stringify(fixture));
check('Native scenario arithmetic includes capability construction, maintenance, reserve and obligation',()=>{
  assert.equal(projection.summary.scenario.fullCost,216000);
  assert.equal(projection.summary.scenario.availableSurplus,259000);
});
check('Modeled collections never become observed collections or surplus',()=>{
  assert.equal(projection.summary.observed.revenue,null);
  assert.equal(projection.summary.observed.availableSurplus,null);
});
check('Native optional reinvestment remains zero',()=>{
  assert.equal(projection.summary.reinvestmentBps,0);
  assert.equal(projection.summary.scenario.eligibleInvestment,0);
});
check('Assumed collected receipt is rejected by the native schema',()=>{
  const record=structuredClone(projection.ledger);
  const receipt=record.events.find(row=>row.type==='revenue'&&row.category==='collected');
  receipt.basis='assumed';receipt.amountMinor=500000;
  assert.throws(()=>replayLedger(record),/Collected revenue must be observed/);
});
check('Failed work remains a cost in the aggregate',()=>{
  const rejected={...fixture[0],id:'simulated-002',acceptance:'rejected',modeledCollectionsMinor:0,
    costsMinor:{delivery:100000,business:0,capability:0,maintenance:0},reserveMinor:0,obligationMinor:0};
  assert.equal(projectScenario(JSON.stringify([...fixture,rejected])).summary.scenario.availableSurplus,159000);
});
check('Projection rejects executable object inputs',()=>{
  assert.throws(()=>projectScenario(fixture),/serialized JSON/);
});
check('Negative investment economics are retained',()=>{
  const result=calculateInvestment({constructionCostMinor:100000,failedConstructionCostMinor:20000,
    maintenancePerReuseMinor:1000,expectedSavingPerReuseMinor:500,remainingReuses:20});
  assert.equal(result.netBenefit,-130000);assert.equal(result.paysBackWithinHorizon,false);
});
const receipt={schema:'network-economy-native-accounting-check/v1',sourceCommit:'c4a7febc02fb9d607e9da5ece2101c4b6b36fc64',
  runtime:process.version,kind:'ACTUAL local arithmetic and rejection checks over constructed fixtures',
  productionQualification:false,liveCollections:false,
  developmentFailures:[{kind:'fixture arithmetic assertion',initialExpectedMicros:860000000,actualCorrectMicros:760000000,
    correction:'Corrected the authored expected sum of eight stage fixtures and dependent totals; native modules unchanged.'}],
  checks,costRecord,costSummary,projection};
const output=JSON.stringify(receipt,null,2)+'\n';
if(process.argv[2])writeFileSync(process.argv[2],output);else process.stdout.write(output);
