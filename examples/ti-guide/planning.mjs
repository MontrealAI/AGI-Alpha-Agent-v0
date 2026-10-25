// SPDX-License-Identifier: Apache-2.0
// Input preparation only. The installed executor remains the acceptance boundary.
import * as alpha from '../successor-alpha/engine.mjs';

export const SAMPLE_JOBS = 'id,duration,crew,deps\nJ1,1,1,\nJ2,3,2,J1\nJ3,2,1,J1\nJ4,2,1,J2|J3\nJ5,2,2,J4\nJ6,1,1,J4\nJ7,1,1,J5|J6\n';
export function preparePlanning(settings) {
    const fail = message => { throw Error(message); };
    const integer = (value, low, high, name) => {
        const n = Number(value);
        if (String(value).trim() === '' || !Number.isSafeInteger(n) || n < low || n > high) fail(name);
        return n;
    };
    if (!/^[A-Za-z0-9_.-]{1,80}$/.test(settings.id)) fail('PROJECT_ID');
    if (!['public', 'synthetic'].includes(settings.dataClass)) fail('INPUT_RIGHTS_SCOPE');
    const csv = alpha.parseCsv(settings.jobsCsv);
    if (JSON.stringify(csv.headers) !== JSON.stringify(['id', 'duration', 'crew', 'deps'])) fail('JOB_COLUMNS');
    if (!csv.rows.length || csv.rows.length > 18) fail('JOB_COUNT');
    const jobs = csv.rows.map(([id, duration, crew, deps]) => ({ id,
        duration: integer(duration, 1, 12, 'DURATION'), crew: integer(crew, 1, 4, 'CREW'),
        deps: deps === '' ? [] : deps.split('|') }));
    const ids = new Set(jobs.map(j => j.id));
    if (ids.size !== jobs.length || jobs.some(j => !/^J[1-9][0-9]{0,2}$/.test(j.id))) fail('JOB_IDS');
    if (jobs.some(j => new Set(j.deps).size !== j.deps.length || j.deps.some(id => !ids.has(id)))) fail('DEPENDENCIES');
    const done = new Set();
    function visit(id, active = new Set()) {
        if (active.has(id)) fail('DEPENDENCY_CYCLE');
        if (done.has(id)) return;
        const next = new Set(active); next.add(id);
        for (const dep of jobs.find(j => j.id === id).deps) visit(dep, next);
        done.add(id);
    }
    for (const j of jobs) visit(j.id);
    const slots = integer(settings.slots, 2, 128, 'HORIZON');
    const capacity = integer(settings.capacity, 1, 4, 'CAPACITY');
    const deadline = integer(settings.deadline, 1, slots, 'DEADLINE');
    const observed = integer(settings.observedAt, 0, slots - 1, 'OBSERVATION');
    const start = integer(settings.outageStart, observed, slots - 1, 'OUTAGE');
    const end = integer(settings.outageEnd, start + 1, slots, 'OUTAGE');
    const reduced = integer(settings.outageCapacity, 0, capacity - 1, 'OUTAGE_CAPACITY');
    const changedDuration = integer(settings.changedDuration, 1, 12, 'DURATION');
    const changed = jobs.find(j => j.id === settings.changedJob);
    if (!changed || changed.duration === changedDuration) fail('CHANGED_JOB');
    const initial = { schema: 'release-plan/v1', id: settings.id, kind: 'plan',
        public_or_synthetic: settings.dataClass, planning_only: true, jobs,
        capacity: Array(slots).fill(capacity), deadline };
    if (new TextEncoder().encode(JSON.stringify(initial)).length > 16000) fail('TASK_BYTES');
    return { initial, changes: { durations: { [changed.id]: changedDuration }, deadline },
        repair: { observed_at: observed, capacity: Array.from({ length: slots }, (_, i) =>
            i >= start && i < end ? reduced : capacity), deadline },
        construction: { enabled: settings.construction === true } };
}
