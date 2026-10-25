// SPDX-License-Identifier: Apache-2.0
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {evaluateAutomatedCosts,AUTOMATED_STAGES} from '../../../examples/successor-alpha/automated-costs.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const read=async name=>JSON.parse(await readFile(join(here,name),'utf8'));
const facts=await read('HUMAN_BENCHMARK_SOURCES.json');
const traces=await read('corrected-execution-traces.json');
const measurements=await read('corrected-external-process-measurements.json');
const fact=(value,basis,reference)=>({value,basis,reference});
const estimate=(value,reference)=>fact(value,'estimated',reference+'; planning assumption, not observed billing.');
const unknown=reference=>fact(null,'unknown',reference);
const wage=facts.rates.find(row=>row.id==='us_office_admin_compensation_dec2025').hourlyCostMicros;
const engineering=facts.rates.find(row=>row.id==='us_professional_compensation_dec2025').hourlyCostMicros;
const input={schema:'alpha-automated-costs/v1',offeringId:'committed-source-assurance',currency:'USD',scenarios:[]};
const assumptions=[
  {name:'base',utilization:5000,acceptance:9800,attempts:1020000,userMinutes:1,exceptionPpm:0,exceptionMinutes:0,
    capacityMonthly:20,businessMonthly:15,modelCallMicros:100000,toolCallMicros:10000,
    maintenanceModelCalls:100,maintenanceToolCalls:500,setupModelCalls:20,setupToolCalls:50,setupHumanMinutes:10,
    developmentModelCalls:500,failedConstructionCalls:100,developmentToolCalls:500,
    months:12,operationMicros:20,transportMicros:5000},
  {name:'conservative',utilization:2000,acceptance:9500,attempts:1150000,userMinutes:2,exceptionPpm:50000,exceptionMinutes:5,
    capacityMonthly:50,businessMonthly:50,modelCallMicros:500000,toolCallMicros:50000,
    maintenanceModelCalls:500,maintenanceToolCalls:1000,setupModelCalls:100,setupToolCalls:500,setupHumanMinutes:30,
    developmentModelCalls:2000,failedConstructionCalls:500,developmentToolCalls:500,
    months:12,operationMicros:100,transportMicros:20000},
  {name:'stress',utilization:500,acceptance:8000,attempts:1750000,userMinutes:5,exceptionPpm:200000,exceptionMinutes:10,
    capacityMonthly:100,businessMonthly:100,modelCallMicros:2000000,toolCallMicros:100000,
    maintenanceModelCalls:1000,maintenanceToolCalls:5000,setupModelCalls:500,setupToolCalls:1000,setupHumanMinutes:120,
    developmentModelCalls:10000,failedConstructionCalls:5000,developmentToolCalls:5000,
    months:6,operationMicros:500,transportMicros:100000},
];
const constructionAssumptions=assumptions.map(({name,...values})=>({name,
  ...Object.fromEntries(Object.entries(values).map(([key,value])=>[key,estimate(value,
    'Explicit automated-configuration scenario quantity; model/tool call budgets are not executed calls or vendor price quotes')])),
  oneTimeOperatorHourlyCostMicros:engineering}));
for(const a of assumptions){
  const operations=AUTOMATED_STAGES.map(stage=>({id:'local-'+stage,stage,
    frequency:['packaging','reporting'].includes(stage)?'accepted':'attempt',
    unitsPerOccurrencePpm:fact(1000000,'measured',`corrected-execution-traces.json: eight-stage fixed software implementation invoked in both primary missions; not a production failure-rate estimate; stage=${stage}`),
    unitCostMicros:estimate(a.operationMicros,'Variable local operation electricity/tool/storage allocation; excludes the separately allocated fixed monthly capacity and maintenance'),
    implementation:'implemented'}));
  operations.push({id:'connected-admission-overhead',stage:'execution',frequency:'attempt',
    unitsPerOccurrencePpm:estimate(1000000,'One authenticated admission/report transport per attempt in the modeled missing connected route'),
    unitCostMicros:estimate(a.transportMicros,'Explicit missing-route software and transport budget; no provider call or approved connection executed'),implementation:'modeled'});
  input.scenarios.push({name:a.name,
    capacityRequestsPerMonth:estimate(1000,'Hypothetical provisioned offering capacity, not measured fleet throughput or demand'),
    utilizationBps:estimate(a.utilization,'Hypothetical offering utilization; no paid demand is established'),
    acceptanceBps:estimate(a.acceptance,'Expected complete-request acceptance; two deterministic jobs do not estimate production reliability'),
    attemptsPerRequestPpm:estimate(a.attempts,'Initial attempt plus expected failures/retries; failed work is charged'),operations,
    residual:[
      {id:'required-user-decision',stage:'planning',exceptionsPerRequestPpm:estimate(1000000,'One required objective/rights/scope approval; user decision, not routine staffed service'),
        minutesPerException:estimate(a.userMinutes,'Unmeasured user-decision duration sensitivity, charged conservatively instead of erased'),hourlyCostMicros:wage},
      {id:'residual-exception-investigation',stage:'recovery',exceptionsPerRequestPpm:estimate(a.exceptionPpm,'Unmeasured exceptional investigation rate after automated bounded recovery'),
        minutesPerException:estimate(a.exceptionMinutes,'Exceptional investigation effort; no permanent per-job operator assumed'),hourlyCostMicros:wage}],
    monthly:[
      {id:'fixed-capacity',kind:'capacity',amountMicros:estimate(a.capacityMonthly*1000000,
        'Hypothetical fixed capacity allocation; excludes the separately priced variable operation energy/tool budgets'),
        allocationBps:estimate(10000,'Offering share of this fixed capacity; no second utilization charge')},
      {id:'automated-shared-maintenance',kind:'maintenance',amountMicros:estimate(
        a.maintenanceModelCalls*a.modelCallMicros+a.maintenanceToolCalls*a.toolCallMicros,
        'automated-configuration-assumptions.json: priced model/tool maintenance calls; proposed software replacement, not recurring staffed labor or executed provider calls'),
        allocationBps:estimate(10000,'Offering allocation of shared automated maintenance, charged once monthly')},
      {id:'business-software',kind:'business',amountMicros:estimate(a.businessMonthly*1000000,
        'Estimated reporting, storage and business-software allocation; no routine employee handling assumed'),
        allocationBps:estimate(10000,'Offering share; no duplicate charge in variable costs')}],
    investments:[
      {id:'initial-setup',kind:'setup',amountMicros:estimate(
        a.setupModelCalls*a.modelCallMicros+a.setupToolCalls*a.toolCallMicros+
          Number((BigInt(a.setupHumanMinutes)*BigInt(engineering.value)+59n)/60n),
        'automated-configuration-assumptions.json: priced software configuration/check calls plus explicitly one-time operator permission/installation decision; duration estimated, compensation sourced'),
        allocationBps:estimate(10000,'Offering share of this one-time setup pool'),amortizationMonths:estimate(a.months,'Finite expected amortization horizon, not permanent reuse')},
      {id:'development-including-failed-work',kind:'development',amountMicros:estimate(
        (a.developmentModelCalls+a.failedConstructionCalls)*a.modelCallMicros+a.developmentToolCalls*a.toolCallMicros,
        'automated-configuration-assumptions.json: explicit successful and unsuccessful automated construction model calls plus tool/CI checks; actual historical engineering cost remains unknown'),
        allocationBps:estimate(10000,'Offering share; no duplicate charge in per-request or monthly costs'),amortizationMonths:estimate(a.months,'Finite expected development reuse horizon')}],
    humanBaseline:{minutesPerAccepted:unknown('No matched traditional non-AI task duration observation; compute break-even and explicit sensitivity instead'),hourlyCostMicros:wage}});
}
const summary=evaluateAutomatedCosts(input);
const sensitivities=[1,2,5,15,30,60,120].map(minutes=>{
  const record=structuredClone(input);
  for(const scenario of record.scenarios)scenario.humanBaseline.minutesPerAccepted=estimate(minutes,'Traditional non-AI duration sensitivity for equivalent accepted scope; not an observed timing');
  return {traditionalMinutes:minutes,scenarios:evaluateAutomatedCosts(record).scenarios.map(row=>({name:row.name,
    humanBaselineMicrosPerAccepted:row.humanBaselineMicrosPerAccepted,comparison:row.comparison}))};
});
const observedOnly=structuredClone(input);
for(const s of observedOnly.scenarios){
  for(const op of s.operations)op.unitCostMicros=unknown('No measured monetary bill; implementation and timing do not establish price');
  for(const row of s.monthly)row.amountMicros=unknown('Actual ongoing full operation cost not observed');
  for(const row of s.investments)row.amountMicros=unknown('Actual complete setup/development cost not observed');
  s.humanBaseline.minutesPerAccepted=unknown('Matched human timing is unmeasured');
}
const sourceHashes={};
for(const name of ['HUMAN_BENCHMARK_SOURCES.json','corrected-execution-traces.json','corrected-external-process-measurements.json'])
  sourceHashes[name]=createHash('sha256').update(await readFile(join(here,name))).digest('hex');
const output={schema:'alpha-automated-offering-analysis/v1',offeringId:input.offeringId,sourceHashes,
  actualExecution:{primaryMissions:traces.runs.length,operatingReplications:measurements.runs.length,
    routineOperatorHandling:'Zero observed inside the approved deterministic local run; user decisions and commercial acceptance are separate.',
    fullMonetaryCost:null,modelProviderCalls:0,
    measurementScope:'External replication includes launch/import/Git descendant CPU; stages alone exclude subprocess cost. No authenticated executor test performed.'},
  primaryModeledComparison:summary,humanDurationSensitivity:sensitivities,
  observedCostOnly:evaluateAutomatedCosts(observedOnly),
  limits:['This is an additive product configuration model, not a change to frozen studies or a new empirical economic endpoint.',
    'Hourly compensation is sourced; traditional task durations, demand, failure rates, software-call prices/counts, setup attention and utilization are not measured.',
    'Required user-decision effort is priced explicitly; no permanent routine human delivery staff is assumed.',
    'The deterministic delivery service has no model-provider invocation. Automated construction/maintenance are separately priced software simulations, including failed calls and tool checks; no live construction is inferred.',
    'Observed-cost-only tiers remain unknown. Fully specified scenarios are completed conditional calculations, not established real AGI ALPHA cost.',
    'Equal acceptance, quality, revisions and scope are conditions, not an inferred human trial result.',
    'Economic amortization is not treasury cash. No savings, token issuance, transfer or price assumption is collected revenue.',
    'Missing authenticated admission is modeled separately. Only that live route remains unexecuted; it does not invalidate this calculation.']};
await writeFile(join(here,'automated-cost-record.json'),JSON.stringify(input,null,2)+'\n');
await writeFile(join(here,'automated-configuration-assumptions.json'),JSON.stringify({
  schema:'alpha-automated-configuration-assumptions/v1',scenarios:constructionAssumptions,
  scope:'Model and tool prices are explicit estimates, not dated vendor quotes or actual invoices. Calls replace one-time/shared work in the modeled configuration and do not imply execution. Required one-time operator decisions remain.'},null,2)+'\n');
await writeFile(join(here,'observed-components-unknown-cost-record.json'),JSON.stringify(observedOnly,null,2)+'\n');
await writeFile(join(here,'automated-cost-analysis.json'),JSON.stringify(output,null,2)+'\n');
const dollars=value=>value===null?'unknown':(value/1000000).toFixed(4);
const lines=[
  '# Automated source assurance: work, costs and remaining decisions','',
  'This is the existing product ledger’s additive automated-configuration analysis. It preserves the original staffed-study results and their interpretation. Neither USD31.74 nor a USD0.17 token component is treated as actual AGI ALPHA delivery cost.','',
  '## Actual completed work','',
  'Two fresh pinned public-source inventory missions produce complete, checked CSV differences, action plans, a recomputable workspace and a finished report. Preparation, planning, comparison, independent verification, packaging, reporting and restart handling execute in software. Source correctness is not inferred from matching source hashes. Required input rights, objective/scope approval and commercial acceptance remain user decisions.','',
  'The corrected runner is reused on the second source scope. Original recovery failures and old-source receipts remain; corrected acceptance is bound to the corrected implementation. Operating replications measure launch, imports, Git descendants and completion revalidation separately from task diversity. Monetary cost remains unmeasured.','',
  '## Completed conditional model','',
  'Each priced software replacement has measured, sourced, estimated or unknown provenance in the shared record. The model prices automated setup/construction/maintenance calls and tool checks, including unsuccessful construction. These calls are simulated budgets, not executed provider calls or vendor price quotations. One-time operator setup decisions and required per-request user decisions are separately priced assumptions. There is no permanent routine delivery staff assumption.','',
  '| Scenario | Expected accepted/month | Marginal/accepted | Recurring/accepted | Fully loaded/accepted | Human break-even, full cost |',
  '| --- | ---: | ---: | ---: | ---: | ---: |',
  ...summary.scenarios.map(row=>`| ${row.name} | ${row.volume.acceptedPerMonth} | USD${dollars(row.costs.marginalMicrosPerAccepted)} | USD${dollars(row.costs.recurringMicrosPerAccepted)} | USD${dollars(row.costs.fullyLoadedMicrosPerAccepted)} | ${row.comparison.fullyLoaded.breakEvenHumanMinutes.toFixed(3)} min |`),'',
  'The human hourly compensation comes from the preserved research BLS office/admin rate, USD35.96/hour including benefits (December 2025). Actual equivalent traditional task duration is unknown. Break-even times and the separate 1/2/5/15/30/60/120-minute sensitivities replace an invented speedup. These are conditional equal-scope, equal-acceptance comparisons, not measured savings.','',
  '| Assumed traditional minutes | Base, fully loaded | Conservative, fully loaded | Stress, fully loaded |',
  '| --- | --- | --- | --- |',
  ...sensitivities.map(row=>`| ${row.traditionalMinutes} | ${row.scenarios.map(s=>s.comparison.fullyLoaded.outcome).join(' | ')} |`),'',
  'The observed-components-only record leaves monetary prices and full historical development costs unknown. Its three total-cost tiers therefore remain unknown. This is distinct from the completed priced simulation. Initial one-time human setup/development sensitivity files are preserved alongside the automated target; no earlier research file is rewritten.','',
  '## Economic and authority limits','',
  'These cost tiers include the valued time of required user decisions as a resource cost. That opportunity cost is not automatically a provider cash expense. ',
  'Amortization is an economic allocation, not available treasury cash. The UI carries only a provisional recurring allocation into the existing mission ledger and leaves actual construction/period costs unknown until separately supplied. Customer savings never become revenue. Required reserves, obligations and transaction authority remain separate. No payment or token action is performed.','',
  'The authenticated browser-to-approved-executor route remains unexecuted and requires the existing approved operator environment. This does not block the completed conditional model or these deterministic local deliverables. Missing live admission is explicitly priced as modeled software; it is not qualified by simulation.','',
  'Reproduce: `node contrib/productive-capability-ledger/automation-v1/model-automated-offering.mjs`. See the shared JSON record, provenance register, workflow map, corrected raw deliveries and independent review receipts in this directory.',''
];
await writeFile(join(here,'AUTOMATED_ECONOMICS.md'),lines.join('\n'));
console.log(JSON.stringify(summary.scenarios.map(row=>({name:row.name,...row.costs,
  residualHumanMinutesPerRequest:row.residualHumanMinutesPerRequest,breakEvenMinutes:row.comparison.fullyLoaded.breakEvenHumanMinutes}))));
