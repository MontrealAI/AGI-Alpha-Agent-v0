// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as plans from './shadow-plan.mjs';

const project = {id:'project-1',cycles:[{id:'cycle-1',sourceHash:'a'.repeat(64)}]};
const inputs = {currency:'USD',acceptance:'accepted',totalCollectedCents:null,priceAssumptionCents:10000,
    totalOperatingCostCents:50,operatingCostsComplete:true,capabilityCostCents:1000,reserveCents:2000,
    obligationCents:500,costBasis:'assumed',reinvestmentBps:5000,humanMinutes:0,humanHourlyCents:4000,traditionalMinutes:300};

test('one current snapshot per retained mission; repeated calculation is idempotent and revisions remain',()=>{
    const first=plans.recordPlan(plans.createPlans(project),project,inputs);
    assert.deepEqual(plans.recordPlan(first,project,inputs),first);
    const changed=plans.recordPlan(first,project,{...inputs,priceAssumptionCents:9000});
    const replay=plans.replayPlans(changed,project);
    assert.equal(replay.revisions,2); assert.equal(replay.missions.length,1);
    assert.equal(replay.missions[0].summary.scenario.afterReserves,5450);
    assert.equal(replay.missions[0].summary.scenario.eligibleInvestment,2725);
    assert.equal(replay.missions[0].summary.observed.availableSurplus,null);
    assert.equal(first.entries[0].inputs.priceAssumptionCents,10000);
});

test('fresh mission keeps earlier history and money denominations remain explicit per mission',()=>{
    const first=plans.recordPlan(plans.createPlans(project),project,inputs);
    const secondProject={...project,cycles:[...project.cycles,{id:'cycle-2',sourceHash:'b'.repeat(64)}]};
    const second=plans.recordPlan(first,secondProject,{...inputs,currency:'CAD',priceAssumptionCents:5000});
    const replay=plans.replayPlans(second,secondProject);
    assert.equal(replay.missions.length,2); assert.equal(replay.missions[0].summary.currency,'USD');
    assert.equal(replay.missions[1].summary.currency,'CAD');
    assert.equal(Object.hasOwn(replay,'totalSurplus'),false);
});

test('foreign projects, changed sources, authority, duplicate keys and unbound inputs refuse',()=>{
    const first=plans.recordPlan(plans.createPlans(project),project,inputs);
    for(const edit of [x=>x.projectId='other',x=>x.authority='spend',x=>x.entries[0].sourceHash='c'.repeat(64),
        x=>x.entries[0].cycleId='missing',x=>x.entries[0].inputs.costBasis='observed',x=>x.entries[0].inputs.hidden=1]) {
        const bad=structuredClone(first); edit(bad); assert.throws(()=>plans.inspectPlans(bad,project));
    }
    assert.throws(()=>plans.inspectPlans('{"schema":1,"schema":2}',project),/Duplicate/);
    assert.throws(()=>plans.inspectPlans(' '.repeat(200001),project),/200 KB/);
    assert.throws(()=>plans.recordPlan(plans.createPlans({...project,cycles:[]}),{...project,cycles:[]},inputs));
});

test('unknown costs and acceptance stay unknown through export/replay and revisions are bounded',()=>{
    const first=plans.recordPlan(plans.createPlans(project),project,{...inputs,acceptance:'unknown',totalOperatingCostCents:null});
    assert.equal(plans.replayPlans(JSON.stringify(first),project).missions[0].summary.scenario.availableSurplus,null);
    let archive=first;
    for(let i=1;i<24;i++)archive=plans.recordPlan(archive,project,{...inputs,priceAssumptionCents:i});
    assert.throws(()=>plans.recordPlan(archive,project,{...inputs,priceAssumptionCents:25}),/24 revisions/);
});
