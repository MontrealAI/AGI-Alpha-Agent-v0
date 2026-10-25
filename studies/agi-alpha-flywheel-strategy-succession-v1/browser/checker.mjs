// SPDX-License-Identifier: Apache-2.0
// Separate browser implementation. It imports no planner or planner verifier.
// Same project authorship and local custody: this is not external certification.

export function checkSchedule(task, result, meter = null) {
    let checks = 0;
    const tick = (kind, count = 1) => {
        checks += count;
        if (meter && typeof meter.tick === 'function') meter.tick(`browser-check:${kind}`, count);
    };
    const require = (condition, code) => {
        tick('assertion');
        if (!condition) throw new Error(code);
    };
    const integer = (value, low, high) => Number.isSafeInteger(value) && value >= low && value <= high;
    require(task?.schema === 'release-plan/v1', 'CHECK_TASK_SCHEMA');
    require(typeof task.id === 'string' && ['plan', 'repair'].includes(task.kind), 'CHECK_TASK_KIND');
    require(task.planning_only === true && ['synthetic', 'public'].includes(task.public_or_synthetic), 'CHECK_INPUT_SCOPE');
    require(Array.isArray(task.jobs) && integer(task.jobs.length, 1, 18), 'CHECK_JOB_SCOPE');
    require(Array.isArray(task.capacity) && integer(task.capacity.length, 1, 128), 'CHECK_TIME_SCOPE');
    require(task.capacity.every(value => integer(value, 0, 4)), 'CHECK_CAPACITY_SCOPE');
    const horizon = task.capacity.length;
    const deadline = task.deadline ?? horizon;
    require(integer(deadline, 1, horizon), 'CHECK_DEADLINE');
    const jobs = new Map();
    for (const job of task.jobs) {
        tick('input-job');
        require(typeof job.id === 'string' && /^J[1-9][0-9]{0,2}$/.test(job.id), 'CHECK_JOB_ID');
        require(!jobs.has(job.id), 'CHECK_DUPLICATE_JOB');
        require(integer(job.duration, 1, 12) && integer(job.crew, 1, 4), 'CHECK_JOB_RESOURCE');
        require(Array.isArray(job.deps ?? []), 'CHECK_DEPENDENCIES');
        require(new Set(job.deps ?? []).size === (job.deps ?? []).length, 'CHECK_DUPLICATE_DEPENDENCY');
        jobs.set(job.id, {...job, deps: [...(job.deps ?? [])]});
    }
    const releases = task.release ?? {};
    const locks = task.locked ?? {};
    const baseline = task.baseline ?? {};
    for (const [id, time] of Object.entries(releases)) {
        require(jobs.has(id) && integer(time, 0, horizon - 1), 'CHECK_RELEASE');
    }
    for (const [id, time] of Object.entries(locks)) {
        require(jobs.has(id) && integer(time, releases[id] ?? 0, horizon - jobs.get(id).duration), 'CHECK_LOCK');
    }
    for (const [id, time] of Object.entries(baseline)) {
        require(jobs.has(id) && integer(time, 0, horizon - jobs.get(id).duration), 'CHECK_BASELINE');
    }
    require(task.kind !== 'plan' || Object.keys(locks).length === 0, 'CHECK_PLAN_LOCKS');
    require(task.kind !== 'repair' || Object.keys(baseline).length === jobs.size, 'CHECK_REPAIR_BASELINE');
    for (const [id, time] of Object.entries(locks)) {
        require(baseline[id] === time, 'CHECK_LOCK_BASELINE');
        for (const parent of jobs.get(id).deps) {
            require(parent in locks && locks[parent] + jobs.get(parent)?.duration <= time, 'CHECK_LOCK_PREFIX');
        }
    }
    require(task.kind !== 'plan' || (!task.baseline && task.movement_limit === undefined), 'CHECK_PLAN_REPAIR_INPUT');
    if (task.movement_limit !== undefined) {
        require(integer(task.movement_limit, 0, 18 * 128), 'CHECK_MOVEMENT_LIMIT');
    }

    // Kahn traversal verifies graph acyclicity and obtains an independent critical-path bound.
    const incoming = new Map();
    const next = new Map([...jobs.keys()].map(id => [id, []]));
    const earliestEnd = new Map();
    for (const job of jobs.values()) {
        incoming.set(job.id, job.deps.length);
        for (const parent of job.deps) {
            tick('graph-edge');
            require(jobs.has(parent), 'CHECK_UNKNOWN_DEPENDENCY');
            next.get(parent).push(job.id);
        }
    }
    const queue = [...incoming].filter(([, count]) => count === 0).map(([id]) => id);
    let visited = 0;
    let critical = 0;
    while (queue.length) {
        const id = queue.shift();
        const job = jobs.get(id);
        let begin = releases[id] ?? 0;
        for (const parent of job.deps) {
            tick('graph-time');
            begin = Math.max(begin, earliestEnd.get(parent));
        }
        if (id in locks) {
            require(locks[id] >= begin, 'CHECK_LOCK_PRECEDENCE');
            begin = locks[id];
        }
        const end = begin + job.duration;
        earliestEnd.set(id, end);
        critical = Math.max(critical, end);
        visited += 1;
        for (const child of next.get(id)) {
            incoming.set(child, incoming.get(child) - 1);
            if (incoming.get(child) === 0) queue.push(child);
        }
    }
    require(visited === jobs.size, 'CHECK_DEPENDENCY_CYCLE');

    require(result?.schema === 'release-plan-result/v1' && result.task_id === task.id, 'CHECK_RECEIPT_BINDING');
    require(Array.isArray(result.schedule) && result.schedule.length === jobs.size, 'CHECK_RESULT_SIZE');
    const placed = new Map();
    for (const item of result.schedule) {
        tick('result-job');
        require(jobs.has(item.id) && !placed.has(item.id), 'CHECK_RESULT_ID');
        const job = jobs.get(item.id);
        require(integer(item.start, 0, horizon) && integer(item.end, 1, horizon), 'CHECK_TIME_INTEGER');
        require(item.end - item.start === job.duration, 'CHECK_DURATION');
        require(item.start >= (releases[item.id] ?? 0), 'CHECK_RELEASE_VIOLATION');
        require(!(item.id in locks) || item.start === locks[item.id], 'CHECK_LOCK_CHANGED');
        placed.set(item.id, item);
    }
    for (const job of jobs.values()) {
        for (const parent of job.deps) {
            tick('precedence');
            require(placed.get(parent).end <= placed.get(job.id).start, 'CHECK_PRECEDENCE_VIOLATION');
        }
    }

    // Scan each period from the complete finished schedule, not the planner's construction state.
    const usage = [];
    for (let time = 0; time < horizon; time += 1) {
        let occupied = 0;
        for (const [id, item] of placed) {
            tick('period-job');
            if (item.start <= time && time < item.end) occupied += jobs.get(id).crew;
        }
        require(occupied <= task.capacity[time], 'CHECK_CAPACITY_VIOLATION');
        usage.push(occupied);
    }
    let makespan = 0;
    let movement = 0;
    let totalDemand = 0;
    let lockedEnd = 0;
    for (const [id, item] of placed) {
        tick('objective');
        makespan = Math.max(makespan, item.end);
        if (id in baseline) movement += Math.abs(item.start - baseline[id]);
        totalDemand += jobs.get(id).duration * jobs.get(id).crew;
        if (id in locks) lockedEnd = Math.max(lockedEnd, locks[id] + jobs.get(id).duration);
    }
    let cumulativeCapacity = 0;
    let loadBound = horizon + 1;
    for (let time = 0; time < horizon; time += 1) {
        tick('load-bound');
        cumulativeCapacity += task.capacity[time];
        if (cumulativeCapacity >= totalDemand) {
            loadBound = time + 1;
            break;
        }
    }
    const bound = Math.max(critical, loadBound, lockedEnd);
    const optimalByBound = makespan === bound;
    require(result.makespan === makespan && result.movement === movement, 'CHECK_FALSE_OBJECTIVE');
    require(result.lower_bound?.value === bound, 'CHECK_FALSE_BOUND');
    require(result.optimal_by_lower_bound === optimalByBound, 'CHECK_FALSE_OPTIMALITY');
    require(Array.isArray(result.proof) && result.proof.length === 0, 'CHECK_INHERITED_PROOF');
    require(Array.isArray(result.authority) && result.authority.length === 0, 'CHECK_INHERITED_AUTHORITY');
    return {
        valid: true,
        qualified: makespan <= deadline && (task.movement_limit === undefined || movement <= task.movement_limit),
        makespan,
        movement,
        lower_bound: bound,
        optimal_by_lower_bound: optimalByBound,
        checks,
        usage,
        proof: [],
        authority: [],
        independence: 'separate implementation; same project authorship and local custody',
    };
}

export async function checkForWorkbench(task, result) {
    const counts = {total: 0};
    const meter = {tick(kind, count = 1) {
        counts[kind] = (counts[kind] ?? 0) + count;
        counts.total += count;
    }};
    try {
        const checked = checkSchedule(task, result, meter);
        return {...checked, counts, errors: []};
    } catch (error) {
        return {valid: false, qualified: false, counts, errors: [{code: error.message}]};
    }
}
