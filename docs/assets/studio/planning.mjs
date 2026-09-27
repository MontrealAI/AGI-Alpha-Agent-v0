// SPDX-License-Identifier: Apache-2.0
// Bounded planning kernels. Callers validate input schemas and numeric limits.
const sum = (xs) => xs.reduce((a, b) => a + b, 0);

export function planSchedule(jobs, deadline) {
    const evaluate = (order) => {
        const available = new Map(),
            operations = [],
            commitments = [];
        for (const index of order) {
            const job = jobs[index];
            let clock = 0;
            job.operations.forEach((op, sequence) => {
                const start = Math.max(clock, available.get(op.machine) || 0);
                const end = start + op.duration;
                operations.push({
                    job: job.id,
                    sequence,
                    machine: op.machine,
                    start,
                    end,
                });
                available.set(op.machine, end);
                clock = end;
            });
            commitments.push({
                id: job.id,
                completion: clock,
                due: job.due,
                slack: job.due - clock,
            });
        }
        const makespan = Math.max(...available.values());
        const tardiness = sum(commitments.map((j) => Math.max(0, -j.slack)));
        const window_overrun = Math.max(0, makespan - deadline);
        return {
            order: order.map((i) => jobs[i].id),
            operations,
            commitments,
            makespan,
            tardiness,
            late_jobs: commitments.filter((j) => j.slack < 0).length,
            window_overrun,
            violation_hours: tardiness + window_overrun,
        };
    };
    const baseline = evaluate(jobs.map((_, i) => i));
    let best = baseline,
        examined_orders = 0,
        feasible_orders = 0;
    const visit = (order, remaining) => {
        if (!remaining.length) {
            const candidate = evaluate(order);
            examined_orders++;
            if (!candidate.violation_hours) feasible_orders++;
            if (
                candidate.violation_hours < best.violation_hours ||
                (candidate.violation_hours === best.violation_hours &&
                    candidate.makespan < best.makespan)
            )
                best = candidate;
            return;
        }
        remaining.forEach((i, n) =>
            visit(
                [...order, i],
                remaining.filter((_, k) => k !== n),
            ),
        );
    };
    visit(
        [],
        jobs.map((_, i) => i),
    );
    // Reconcile the chosen schedule against source operations, not the search score.
    for (const job of jobs) {
        const ops = best.operations
            .filter((op) => op.job === job.id)
            .sort((a, b) => a.sequence - b.sequence);
        if (
            ops.length !== job.operations.length ||
            ops.some(
                (op, i) =>
                    op.machine !== job.operations[i].machine ||
                    op.end - op.start !== job.operations[i].duration ||
                    op.start < (i ? ops[i - 1].end : 0),
            )
        )
            throw new Error("Schedule precedence or duration check failed.");
        const commitment = best.commitments.find((j) => j.id === job.id);
        if (
            commitment.completion !== ops.at(-1).end ||
            commitment.slack !== job.due - ops.at(-1).end
        )
            throw new Error("Schedule completion check failed.");
    }
    for (const machine of new Set(best.operations.map((op) => op.machine))) {
        const ops = best.operations
            .filter((op) => op.machine === machine)
            .sort((a, b) => a.start - b.start);
        if (ops.some((op, i) => i && op.start < ops[i - 1].end))
            throw new Error("Schedule resource overlap check failed.");
    }
    return {
        ...best,
        examined_orders,
        feasible_orders,
        baseline_makespan: baseline.makespan,
        baseline_tardiness: baseline.tardiness,
    };
}

export function planService(p, coverage, future) {
    // Integer products keep the conversion exact; floor only whole completed cases.
    const minutesNumerator =
        p.shift_hours * 60 * (100 - p.shrinkage_percent) * p.occupancy_percent;
    const caseDenominator = 10000 * p.handle_minutes;
    let backlog = p.backlog;
    const shifts = coverage.map((row, i) => {
        const forecast = Math.max(0, future[i]);
        const arrivals = Math.ceil(
            (forecast * (100 + p.reserve_percent)) / 100,
        );
        const start_backlog = backlog;
        const clearance = Math.ceil(
            backlog / Math.max(1, p.clear_backlog_periods - i),
        );
        const target = arrivals + clearance;
        const required_staff = Math.ceil(
            (target * caseDenominator) / minutesNumerator,
        );
        const extra = Math.min(
            row.extra_limit,
            Math.max(0, required_staff - row.available_staff),
        );
        const capacity = Math.floor(
            ((row.available_staff + extra) * minutesNumerator) /
                caseDenominator,
        );
        const completed = Math.min(capacity, arrivals + backlog);
        backlog += arrivals - completed;
        const shortfall = Math.max(0, target - capacity);
        const cost = extra * row.extra_shift_cost;
        if (
            extra > row.extra_limit ||
            backlog < 0 ||
            start_backlog + arrivals !== completed + backlog
        )
            throw new Error(
                "Staffing capacity or backlog reconciliation failed.",
            );
        return {
            ...row,
            forecast,
            arrivals,
            start_backlog,
            target,
            required_staff,
            extra,
            capacity,
            completed,
            shortfall,
            end_backlog: backlog,
            cost,
        };
    });
    return {
        shifts,
        productive_minutes: minutesNumerator / 10000,
        extra_shifts: sum(shifts.map((r) => r.extra)),
        cost: sum(shifts.map((r) => r.cost)),
        peak_extra: Math.max(...shifts.map((r) => r.extra)),
        ending_backlog: backlog,
        shortfall_periods: shifts.filter((r) => r.shortfall > 0).length,
    };
}
