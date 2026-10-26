// SPDX-License-Identifier: Apache-2.0
// Input construction only. All production cost arithmetic uses the shared engine.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {AUTOMATED_COST_SCHEMA,AUTOMATED_STAGES,evaluateAutomatedCosts} from '../../../examples/successor-alpha/automated-costs.mjs';
const here=dirname(fileURLToPath(import.meta.url));
const delivery=JSON.parse(await readFile(join(here,'unattended-recovery.json'),'utf8'));
assert.equal(delivery.passed,true);assert(delivery.result.independentAcceptance.accepted);
const observations={wallMicroseconds:delivery.result.executionObservations.workerWallMicroseconds.value,scope:delivery.result.executionObservations.scope};
const fact=(value,basis,reference)=>({value,basis,reference});
const assumed=(value,description)=>fact(value,'estimated','ASSUMED illustrative operating scenario; not measured or sourced: '+description);
const zero=description=>assumed(0,description);
const labor=fact(74420000,'sourced','US BLS ECEC civilian professional/related total compensation, June2026, released9Sep2026, https://www.bls.gov/news.release/ecec.t02.htm . Broad reference group; not a quoted task-specific rate.');
const cases=[
 {name:'base',capacity:400,utilization:2500,acceptance:9500,attempts:1200000,seconds:Math.ceil(observations.wallMicroseconds/1000000)+2,host:20000000,upkeep:74420000,business:20000000,development:5000000000,setup:150000000,months:12,exceptions:10000,exceptionMinutes:5},
 {name:'conservative',capacity:1000,utilization:500,acceptance:8000,attempts:1800000,seconds:25,host:80000000,upkeep:148840000,business:60000000,development:12000000000,setup:400000000,months:12,exceptions:50000,exceptionMinutes:10},
 {name:'stress',capacity:400,utilization:100,acceptance:5000,attempts:2000000,seconds:45,host:200000000,upkeep:595360000,business:200000000,development:40000000000,setup:1000000000,months:6,exceptions:200000,exceptionMinutes:20}
];
const model={schema:AUTOMATED_COST_SCHEMA,offeringId:'connected-source-assurance-simulation',currency:'USD',scenarios:cases.map(c=>{
 // Price a share of fixed monthly hardware once. Variable allocation is removed
 // from the remaining capacity row, avoiding duplicate hardware charges.
 const rate=Math.ceil(c.host/(30*24*3600));
 const requests=c.capacity*c.utilization/10000;
 const activeAllocation=requests*c.attempts/1000000*c.seconds*rate;
 assert(Number.isSafeInteger(activeAllocation)&&activeAllocation<=c.host);
 const operations=AUTOMATED_STAGES.map(stage=>({id:'included-'+stage,stage,frequency:'request',
  unitsPerOccurrencePpm:zero('Stage is automated and included once in the complete attempt resource window below.'),
  unitCostMicros:zero('No separately priced stage charge in this simulation; not a claim of free execution.'),implementation:'implemented'}));
 operations.push({id:'complete-attempt-resource-window',stage:'execution',frequency:'attempt',
  unitsPerOccurrencePpm:assumed(c.seconds*1000000,c.name==='base'?'Measured successful source-worker attempt wall time rounded up, plus2seconds assumed preparation/approval/parent overhead; failed-attempt distribution unmeasured.':'Complete attempt-window sensitivity including preparation, verification, reporting and recovery overhead.'),
  unitCostMicros:assumed(rate,'Active-second allocation from an assumed30-day monthly host share. This is cost allocation/opportunity cost, not an observed extra cash invoice.'),implementation:'modeled'});
 return {name:c.name,capacityRequestsPerMonth:assumed(c.capacity,'Declared capacity; future missions still require separate finite authorizations.'),
  utilizationBps:assumed(c.utilization,'Demand/utilization assumption; no production demand observed.'),
  acceptanceBps:assumed(c.acceptance,'Accepted fraction assumption; not inferred from the internal qualification sample.'),
  attemptsPerRequestPpm:assumed(c.attempts,'Mean attempts including failures/recovery; bounded by the declared two-attempt configuration.'),
  operations,residual:[{id:'provider-residual-exceptions',stage:'recovery',exceptionsPerRequestPpm:assumed(c.exceptions,'Residual provider exception frequency.'),
   minutesPerException:assumed(c.exceptionMinutes,'Provider attention per exception; customer input/approval/review is separate and unknown.'),hourlyCostMicros:labor}],
  monthly:[{id:'remaining-capacity-allocation',kind:'capacity',amountMicros:assumed(c.host-activeAllocation,'Remaining monthly hardware share after active-window allocation, so active and standby are not double counted.'),allocationBps:assumed(10000,'This scenario is the already-attributed source-offering share.')},
   {id:'shared-upkeep',kind:'maintenance',amountMicros:assumed(c.upkeep,'One/two/eight professional reference hours per month; no permanently staffed execution service is assumed.'),allocationBps:assumed(10000,'Attributable offering share.')},
   {id:'business-storage-and-delivery',kind:'business',amountMicros:assumed(c.business,'Attributable storage/retention, delivery, administration and business expense allowance; no bills observed.'),allocationBps:assumed(10000,'Attributable offering share.')}],
  investments:[{id:'implementation-and-failed-construction',kind:'development',amountMicros:assumed(c.development,'Attributable implementation, evaluation, failures and authoring/model costs; actual complete expenditure unknown.'),allocationBps:assumed(10000,'Already-attributed source-offering share.'),amortizationMonths:assumed(c.months,'Assumed useful life, not promised demand or payback.')},
   {id:'one-time-operator-setup',kind:'setup',amountMicros:assumed(c.setup,'Approved profile preparation, public input acquisition, installation and acceptance; actual setup cost unknown.'),allocationBps:assumed(10000,'Already-attributed source-offering share.'),amortizationMonths:assumed(c.months,'Same declared useful life.')}],
  humanBaseline:{minutesPerAccepted:fact(null,'unknown','Matched competent human duration without AI unknown; ordinary Git tools are permitted in that baseline. Use break-even thresholds, not an invented savings ratio.'),hourlyCostMicros:labor}};
})};
const result=evaluateAutomatedCosts(model);
const provenance={schema:'alpha-source-economics-scope/v1',mode:'SIMULATED_COST_ALLOCATION_NOT_ACTUAL_BILLING',
 simulationParameters:cases,measuredOperatingObservations:observations,modelCalls:0,actualFullCurrencyCosts:null,customerPrice:null,customerEffortMinutes:null,collections:null,availableSurplus:null,
 humanActivities:{automated:['preparation','bounded planning','execution','verification','correction decision','packaging','reporting','eligible checkpoint recovery'],oneTimeSetup:['install and review profile','register permitted public inputs','existing operator authentication setup'],sharedMaintenance:['software/security/profile upkeep','future qualification'],customerEffort:['choose input','approve exact scope','inspect and use report'],residualExceptions:['corrupt history or interrupted recovery guard','expired/exhausted authorization','unsupported inputs']},
 interpretation:'The same complete deliverable and correctness contract applies. Provider costs are not selling prices or customer savings. Monthly volume assumes separately authorized finite missions, never silent renewal. Existing conventional Git tools remain the strongest practical non-AI alternative. No observed cost advantage, profitable method admission or self-acceleration is established.'};
await writeFile(join(here,'modeled-cost-inputs.json'),JSON.stringify(model,null,2)+'\n');
await writeFile(join(here,'modeled-cost-results.json'),JSON.stringify(result,null,2)+'\n');
await writeFile(join(here,'economic-scope.json'),JSON.stringify(provenance,null,2)+'\n');
const csv=['scenario,requests_per_month,accepted_per_month,attempts_per_month,marginal_usd,recurring_usd,fully_loaded_usd,break_even_professional_minutes,comparison'];
for(const s of result.scenarios)csv.push([s.name,s.volume.requestsPerMonth,s.volume.acceptedPerMonth,s.volume.attemptsPerMonth,
 s.costs.marginalMicrosPerAccepted/1000000,s.costs.recurringMicrosPerAccepted/1000000,s.costs.fullyLoadedMicrosPerAccepted/1000000,s.comparison.fullyLoaded.breakEvenHumanMinutes,s.comparison.fullyLoaded.outcome].join(','));
await writeFile(join(here,'modeled-cost-sensitivity.csv'),csv.join('\n')+'\n');
console.log(JSON.stringify(result.scenarios.map(s=>({name:s.name,costs:s.costs,comparison:s.comparison.fullyLoaded}))));
