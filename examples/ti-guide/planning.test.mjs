// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {preparePlanning, SAMPLE_JOBS} from './planning.mjs';

const settings = {id:'community-release-seven',dataClass:'synthetic',jobsCsv:SAMPLE_JOBS,
    slots:32,capacity:2,deadline:30,changedJob:'J3',changedDuration:4,observedAt:2,
    outageStart:8,outageEnd:13,outageCapacity:1,construction:false};

test('prepares distinct graph and finite request without execution or authority', () => {
    const before=JSON.stringify(settings), mission=preparePlanning(settings);
    assert.equal(JSON.stringify(settings),before);
    assert.equal(mission.initial.jobs.length,7);
    assert.deepEqual(mission.initial.jobs[3].deps,['J2','J3']);
    assert.deepEqual(mission.changes.durations,{J3:4});
    assert.deepEqual(mission.repair.capacity.slice(7,14),[2,1,1,1,1,1,2]);
    assert.deepEqual(mission.construction,{enabled:false});
    assert.equal(mission.initial.planning_only,true);
    assert.equal(mission.repair.baseline,undefined);
    assert.equal(mission.repair.locked,undefined);
    assert.equal(mission.authority,undefined);
});
test('construction is explicit and neither forecast nor acceptance is invented', () => {
    const mission=preparePlanning({...settings,construction:true,dataClass:'public'});
    assert.equal(mission.construction.enabled,true);
    assert.equal(mission.initial.public_or_synthetic,'public');
    assert.equal(mission.verified,undefined);
    assert.equal(mission.costs,undefined);
});
for(const [name,changes,code]of[
    ['duplicate jobs',{jobsCsv:SAMPLE_JOBS.replace('J7,','J1,')},'JOB_IDS'],
    ['unknown dependency',{jobsCsv:SAMPLE_JOBS.replace('J5|J6','J999')},'DEPENDENCIES'],
    ['dependency cycle',{jobsCsv:SAMPLE_JOBS.replace('J1,1,1,','J1,1,1,J7')},'DEPENDENCY_CYCLE'],
    ['changed column names',{jobsCsv:SAMPLE_JOBS.replace('crew','people')},'JOB_COLUMNS'],
    ['same duration',{changedDuration:2},'CHANGED_JOB'],
    ['unknown changed job',{changedJob:'J8'},'CHANGED_JOB'],
    ['fractional duration',{changedDuration:2.5},'DURATION'],
    ['past disruption',{outageStart:1},'OUTAGE'],
    ['empty disruption',{outageEnd:8},'OUTAGE'],
    ['no capacity reduction',{outageCapacity:2},'OUTAGE_CAPACITY'],
    ['oversized horizon',{slots:129},'HORIZON'],
    ['missing horizon',{slots:''},'HORIZON'],
    ['private input',{dataClass:'private'},'INPUT_RIGHTS_SCOPE'],
    ['unsafe project identifier',{id:'<script>'},'PROJECT_ID'],
])test('refuses '+name,()=>assert.throws(()=>preparePlanning({...settings,...changes}),new RegExp(code)));
