// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {checkSchedule} from './checker.mjs';
import {initialTask} from './demo-task.mjs';
import {Meter, portfolio, plan, SPECIALISTS} from '../companion/core.mjs';

const task = initialTask();
const {result} = portfolio(task, new Meter(100000));
const report = checkSchedule(task, result);
assert.equal(report.valid, true);
assert.equal(report.qualified, result.makespan <= task.deadline);
const copy = value => JSON.parse(JSON.stringify(value));
let assertions = 2;
function rejects(change, pattern) {
    const t = copy(task);
    const r = copy(result);
    change(t, r);
    assert.throws(() => checkSchedule(t, r), pattern);
    assertions += 1;
}
rejects((t, r) => { r.task_id = 'different-mission'; }, /BINDING/);
rejects((t, r) => { r.schedule[0].end += 1; }, /DURATION/);
rejects((t, r) => { r.schedule[1].id = r.schedule[0].id; }, /RESULT_ID/);
rejects((t, r) => { r.proof = ['historical-proof']; }, /INHERITED_PROOF/);
rejects((t, r) => { r.authority = ['production']; }, /INHERITED_AUTHORITY/);
rejects((t, r) => { r.makespan += 1; }, /FALSE_OBJECTIVE/);
rejects((t, r) => { r.lower_bound.value += 1; }, /FALSE_BOUND/);
rejects((t, r) => { r.optimal_by_lower_bound = !r.optimal_by_lower_bound; }, /FALSE_OPTIMALITY/);
rejects((t) => { t.capacity.fill(0); }, /CAPACITY_VIOLATION/);
rejects((t) => { t.jobs[0].deps = ['J9']; }, /DEPENDENCY_CYCLE/);
rejects((t) => { t.jobs[0].deps = ['J999']; }, /UNKNOWN_DEPENDENCY/);
const missed = copy(task);
missed.deadline = 1;
assert.equal(checkSchedule(missed, result).qualified, false);
assertions += 1;
const repair = {
    schema: 'release-plan/v1', id: 'late-locked-repair', kind: 'repair',
    jobs: [{id: 'J1', duration: 2, crew: 1, deps: []}, {id: 'J2', duration: 3, crew: 1, deps: ['J1']}],
    capacity: Array(20).fill(1), release: {}, locked: {J1: 5}, baseline: {J1: 5, J2: 7},
    deadline: 15, planning_only: true, public_or_synthetic: 'synthetic',
};
const repaired = plan(repair, {kind: 'repair', base: SPECIALISTS[0], mode: 'stable', stability: 2}, new Meter(100000));
assert.equal(checkSchedule(repair, repaired).lower_bound, 10);
assertions += 1;
const movedLock = copy(repair);
movedLock.baseline.J1 = 4;
assert.throws(() => checkSchedule(movedLock, repaired), /LOCK_BASELINE/);
assertions += 1;
const openPrefix = copy(repair);
openPrefix.locked = {J2: 7};
assert.throws(() => checkSchedule(openPrefix, repaired), /LOCK_PREFIX/);
assertions += 1;
rejects(t => { t.planning_only = false; }, /INPUT_SCOPE/);
console.log(JSON.stringify({schema: 'browser-checker-tests/v1', assertions, result: 'PASS', checks: report.checks}));
