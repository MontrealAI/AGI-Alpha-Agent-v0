// SPDX-License-Identifier: Apache-2.0
// Pure bounded algorithms shared by the browser worker and independent acceptance tests.
const fail = (message) => {
    throw new Error(message);
};
const finite = (value, name, min = 0, max = 1e9) => {
    if (
        typeof value !== "number" ||
        !Number.isFinite(value) ||
        value < min ||
        value > max
    )
        fail(`${name} must be a number from ${min} to ${max}.`);
    return value;
};
const integer = (value, name, min, max) => {
    finite(value, name, min, max);
    if (!Number.isInteger(value)) fail(`${name} must be a whole number.`);
    return value;
};
const text = (value, name, max = 2000) => {
    if (typeof value !== "string" || !value.trim() || value.length > max)
        fail(`${name} must contain 1–${max} characters.`);
    return value;
};
const list = (value, name, min, max) => {
    if (!Array.isArray(value) || value.length < min || value.length > max)
        fail(`${name} must contain ${min}–${max} entries.`);
    return value;
};
const keys = (value, allowed, label) => {
    if (Object.keys(value).some((key) => !allowed.includes(key)))
        fail(`${label} contains an unsupported field.`);
};
const identifier = (value, label) => {
    if (typeof value !== "string" || !/^[A-Za-z0-9_-]{1,64}$/.test(value))
        fail(`${label} needs 1–64 letters, digits, underscores or hyphens.`);
    return value;
};
const unique = (entries, label) => {
    const ids = entries.map((entry) => identifier(entry.id, `${label} ID`));
    if (new Set(ids).size !== ids.length) fail(`${label} IDs must be unique.`);
};
const sum = (numbers) => numbers.reduce((a, b) => a + b, 0);
const mean = (numbers) => sum(numbers) / numbers.length;
const EPS = 1e-7;

function allocation(work, progress) {
    const items = list(work.items, "Items", 1, 18);
    unique(items, "Item");
    const budget = integer(work.budget, "Budget", 1, 1e13);
    const riskLimit = integer(
        work.max_risk ?? 180000,
        "Maximum risk",
        0,
        180000,
    );
    for (const item of items) {
        keys(item, ["id", "cost", "value", "risk"], "Item");
        integer(item.cost, `Item ${item.id} cost`, 1, 1e12);
        integer(item.value, `Item ${item.id} value`, 0, 1e12);
        item.risk ??= 0;
        integer(item.risk, `Item ${item.id} risk`, 0, 10000);
    }
    const total = 2 ** items.length;
    let best = { mask: 0, cost: 0, value: 0, risk: 0 };
    for (let mask = 1; mask < total; mask++) {
        let cost = 0,
            value = 0,
            risk = 0;
        for (let i = 0; i < items.length; i++)
            if (mask & (1 << i)) {
                cost += items[i].cost;
                value += items[i].value;
                risk += items[i].risk;
            }
        if (
            cost <= budget + EPS &&
            risk <= riskLimit + EPS &&
            (value > best.value + EPS ||
                (Math.abs(value - best.value) <= EPS &&
                    (risk < best.risk - EPS ||
                        (Math.abs(risk - best.risk) <= EPS &&
                            cost < best.cost - EPS))))
        )
            best = { mask, cost, value, risk };
        if (mask % 65536 === 0)
            progress(
                `Compared ${mask.toLocaleString()} of ${total.toLocaleString()} subsets.`,
            );
    }
    const chosen = items.filter((_, i) => best.mask & (1 << i));
    const baseline = { cost: 0, risk: 0, value: 0 };
    for (const item of items)
        if (
            baseline.cost + item.cost <= budget + EPS &&
            baseline.risk + item.risk <= riskLimit + EPS
        ) {
            for (const key of ["cost", "risk", "value"])
                baseline[key] += item[key];
        }
    const actual = Object.fromEntries(
        ["cost", "risk", "value"].map((key) => [
            key,
            sum(chosen.map((item) => item[key])),
        ]),
    );
    if (
        actual.cost > budget + EPS ||
        actual.risk > riskLimit + EPS ||
        Math.abs(actual.value - best.value) > EPS
    )
        fail("Independent allocation check failed.");
    return {
        method: "Exhaustive bounded subset search",
        summary: `${chosen.length} of ${items.length} items selected within both constraints.`,
        metrics: [
            ["Selected value", actual.value],
            ["Input-order baseline", baseline.value],
            ["Value improvement", actual.value - baseline.value],
            ["Budget used", `${actual.cost} / ${budget}`],
        ],
        headers: ["Item", "Selected", "Cost", "Value", "Risk"],
        rows: items.map((item, i) => [
            item.id,
            best.mask & (1 << i) ? "Yes" : "No",
            item.cost,
            item.value,
            item.risk,
        ]),
        checks: [
            `All ${total.toLocaleString()} possible subsets compared.`,
            "Selected costs and risks independently summed and checked.",
            "Empty selection is feasible; ties prefer lower risk, then lower cost.",
        ],
        limits: `Optimal within these ${items.length} indivisible items, the two supplied constraints using exact integer totals. Values and risks are your assumptions, not measured revenue. Units: ${work.unit || "planning units"}.`,
        evidence: {
            selected: chosen.map((item) => item.id),
            totals: actual,
            baseline,
            examined_subsets: total,
            tolerance: EPS,
        },
    };
}

function schedule(work, progress) {
    const jobs = list(work.jobs, "Jobs", 1, 7);
    unique(jobs, "Job");
    for (const job of jobs) {
        keys(job, ["id", "due", "operations"], "Job");
        job.due ??= 10000000;
        integer(job.due, `Job ${job.id} due time`, 1, 10000000);
        list(job.operations, `${job.id} operations`, 1, 12).forEach((op, i) => {
            keys(op, ["machine", "duration"], "Operation");
            identifier(op.machine, `${job.id} operation ${i + 1} machine`);
            integer(
                op.duration,
                `${job.id} operation ${i + 1} duration`,
                1,
                100000,
            );
        });
    }
    function evaluate(order) {
        const available = new Map(),
            operations = [],
            completion = new Map();
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
            completion.set(job.id, clock);
        }
        return {
            order: order.map((index) => jobs[index].id),
            operations,
            makespan: Math.max(...available.values()),
            tardiness: sum(
                jobs.map((job) =>
                    Math.max(0, completion.get(job.id) - job.due),
                ),
            ),
        };
    }
    const baseline = evaluate(jobs.map((_, i) => i));
    let best = baseline,
        examined = 0;
    function visit(order, remaining) {
        if (!remaining.length) {
            const candidate = evaluate(order);
            examined++;
            if (
                candidate.makespan < best.makespan - EPS ||
                (Math.abs(candidate.makespan - best.makespan) <= EPS &&
                    candidate.tardiness < best.tardiness)
            )
                best = candidate;
            if (examined % 1000 === 0)
                progress(`Compared ${examined} job-priority orders.`);
            return;
        }
        remaining.forEach((value, i) =>
            visit(
                [...order, value],
                [...remaining.slice(0, i), ...remaining.slice(i + 1)],
            ),
        );
    }
    visit(
        [],
        jobs.map((_, i) => i),
    );
    for (const job of jobs) {
        const ops = best.operations
            .filter((op) => op.job === job.id)
            .sort((a, b) => a.sequence - b.sequence);
        if (
            ops.length !== job.operations.length ||
            ops.some((op, i) => i && op.start < ops[i - 1].end - EPS)
        )
            fail("Operation precedence verification failed.");
    }
    for (const machine of new Set(best.operations.map((op) => op.machine))) {
        const ops = best.operations
            .filter((op) => op.machine === machine)
            .sort((a, b) => a.start - b.start);
        if (ops.some((op, i) => i && op.start < ops[i - 1].end - EPS))
            fail("Machine overlap verification failed.");
    }
    return {
        method: "Exhaustive job-priority search",
        summary: `Use job priority ${best.order.join(" → ")}. All operation sequences and machine capacity checks passed.`,
        metrics: [
            ["Makespan", best.makespan],
            ["Input-order baseline", baseline.makespan],
            ["Time improvement", baseline.makespan - best.makespan],
            ["Total tardiness", best.tardiness],
        ],
        headers: ["Job", "Operation", "Machine", "Start", "Finish"],
        rows: best.operations.map((op) => [
            op.job,
            op.sequence + 1,
            op.machine,
            op.start,
            op.end,
        ]),
        checks: [
            `All ${examined} job-priority permutations compared.`,
            "Each job follows its operation sequence.",
            "No machine processes overlapping operations.",
        ],
        limits: "Best among this serial job-priority scheduling policy, not all possible job-shop schedules. Due times affect only the tie-break; tardiness is reported, not a hard deadline guarantee. No real equipment is controlled.",
        evidence: {
            ...best,
            baseline_makespan: baseline.makespan,
            examined_orders: examined,
        },
    };
}

function forecast(work) {
    const values = list(work.observations, "Observations", 12, 2000);
    values.forEach((value, i) => finite(value, `Observation ${i + 1}`, -1e9));
    const holdout = integer(
        work.holdout ?? 4,
        "Holdout size",
        2,
        Math.floor(values.length / 3),
    );
    const horizon = integer(work.horizon ?? 3, "Forecast horizon", 1, 100);
    const train = values.slice(0, -holdout),
        truth = values.slice(-holdout);
    const season = integer(
        work.season ?? 1,
        "Season length",
        1,
        Math.min(100, Math.floor(train.length / 2)),
    );
    function predict(name, history, count) {
        if (name === "last") return Array(count).fill(history.at(-1));
        if (name === "mean") return Array(count).fill(mean(history));
        if (name === "drift")
            return Array.from(
                { length: count },
                (_, i) =>
                    history.at(-1) +
                    ((i + 1) * (history.at(-1) - history[0])) /
                        (history.length - 1),
            );
        const cycle = history.slice(-season);
        return Array.from({ length: count }, (_, i) => cycle[i % cycle.length]);
    }
    const start = Math.max(2, season, train.length - 60);
    const scores = ["last", "mean", "drift", "seasonal"].map((name) => ({
        name,
        training_mae: mean(
            train
                .slice(start)
                .map((actual, i) =>
                    Math.abs(
                        actual - predict(name, train.slice(0, start + i), 1)[0],
                    ),
                ),
        ),
    }));
    scores.sort((a, b) => a.training_mae - b.training_mae);
    const selected = scores[0].name;
    const heldoutPredictions = predict(selected, train, holdout);
    const error = mean(
        truth.map((actual, i) => Math.abs(actual - heldoutPredictions[i])),
    );
    const baseline = mean(
        truth.map((actual) => Math.abs(actual - train.at(-1))),
    );
    const future = predict(selected, values, horizon);
    if (![...future, ...heldoutPredictions, error].every(Number.isFinite))
        fail("Forecast returned non-finite results.");
    return {
        method: "Train-only selection + temporal holdout",
        summary: `${selected} won the training comparison. Its separate holdout mean absolute error is ${error.toFixed(4)} ${work.unit || "units"}.`,
        metrics: [
            ["Selected policy", selected],
            ["Holdout MAE", error],
            ["Last-value baseline MAE", baseline],
            ["Training observations", train.length],
        ],
        headers: ["Period", "Observed", "Predicted", "Partition"],
        rows: [
            ...truth.map((actual, i) => [
                train.length + i + 1,
                actual,
                heldoutPredictions[i],
                "Untouched holdout",
            ]),
            ...future.map((prediction, i) => [
                values.length + i + 1,
                "Unknown",
                prediction,
                "Future estimate",
            ]),
        ],
        checks: [
            "Policy selected exclusively on expanding training windows.",
            "Holdout observations were excluded from selection and holdout prediction.",
            "Future estimates refit the chosen policy on all supplied observations.",
        ],
        limits: "These are simple last/mean/drift/seasonal baselines, not market predictions. The holdout measures this one historical split; no confidence interval or reliable future-performance guarantee is implied.",
        evidence: {
            selected,
            training_scores: scores,
            train_count: train.length,
            holdout_predictions: heldoutPredictions,
            holdout_actual: truth,
            holdout_mae: error,
            baseline_mae: baseline,
            future,
            observations: values,
        },
    };
}

function research(work, goal) {
    const sources = list(work.sources, "Sources", 1, 20);
    unique(sources, "Source");
    const keywords = [
        ...new Set(goal.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) || []),
    ].filter(
        (word) =>
            !new Set([
                "the",
                "and",
                "with",
                "from",
                "this",
                "that",
                "for",
                "what",
                "are",
                "was",
            ]).has(word),
    );
    const candidates = [];
    for (const source of sources) {
        keys(source, ["id", "title", "text", "url"], "Source");
        if (
            source.url !== undefined &&
            (typeof source.url !== "string" || source.url.length > 2048)
        )
            fail("Source URL must be at most 2,048 characters.");
        text(source.title, "Source title", 300);
        text(source.text, "Source text", 20000);
        const sentences = source.text.match(/[^.!?\n]+(?:[.!?]+|$)/g) || [
            source.text,
        ];
        for (const raw of sentences) {
            const quote = raw.trim();
            if (!quote) continue;
            const lower = quote.toLowerCase();
            const matched = keywords.filter((word) => lower.includes(word));
            candidates.push({
                source_id: source.id,
                title: source.title,
                quote,
                score: matched.length,
                matched,
            });
        }
    }
    candidates.sort((a, b) => b.score - a.score);
    const selected = candidates.filter((item) => item.score > 0).slice(0, 8);
    const claims = selected.length
        ? selected
        : candidates.slice(0, Math.min(3, sources.length));
    for (const claim of claims)
        if (
            !sources
                .find((source) => source.id === claim.source_id)
                .text.includes(claim.quote)
        )
            fail("Source quotation verification failed.");
    return {
        method: "Extractive research · exact source quotations",
        summary: selected.length
            ? `${claims.length} matching passages from your supplied sources. Read their context before drawing conclusions.`
            : "No keyword overlap was found. These source excerpts provide context; they do not answer the goal.",
        metrics: [
            ["Sources inspected", sources.length],
            ["Exact quotations", claims.length],
            [
                "Goal terms matched",
                new Set(claims.flatMap((claim) => claim.matched)).size,
            ],
        ],
        headers: ["Source", "Exact quotation", "Matched terms"],
        rows: claims.map((claim) => [
            `${claim.title} [${claim.source_id}]`,
            claim.quote,
            claim.matched.join(", ") || "None",
        ]),
        checks: [
            "Every displayed quotation checked against the original supplied source.",
            "Source IDs are unique and accompany every quotation.",
            "No external source or generative model was used.",
        ],
        limits: "Keyword ranking retrieves passages; it does not establish source truth, causal reasoning or completeness. There is no web browsing. A configured local agent can add model synthesis with quotation checks.",
        evidence: {
            citations: claims,
            source_ids: sources.map((source) => source.id),
            selection: selected.length ? "keyword_overlap" : "context_only",
        },
    };
}

export function runMission(request, progress = () => {}) {
    if (!request || typeof request !== "object")
        fail("Import a mission object.");
    if (JSON.stringify(request).length > 250000)
        fail("Mission input exceeds 250,000 characters.");
    keys(
        request,
        ["goal", "work", "seed", "population", "generations"],
        "Mission",
    );
    text(request.goal, "Goal");
    if (request.goal.length < 3) fail("Goal needs at least 3 characters.");
    if (request.seed !== undefined)
        integer(request.seed, "Seed", 0, 2 ** 32 - 1);
    if (request.population !== undefined)
        integer(request.population, "Population", 4, 50);
    if (request.generations !== undefined)
        integer(request.generations, "Generations", 1, 50);
    const work = request.work;
    if (!work || typeof work !== "object")
        fail("A mission needs a work object.");
    const fields = {
        allocation: ["items", "budget", "max_risk", "unit"],
        research: ["sources"],
        schedule: ["jobs", "unit"],
        forecast: ["observations", "holdout", "horizon", "season", "unit"],
    };
    if (!fields[work.kind]) fail("Choose a supported mission type.");
    keys(work, ["kind", ...fields[work.kind]], "Work");
    if (work.unit !== undefined)
        text(work.unit, "Unit", work.kind === "schedule" ? 30 : 60);
    progress("Inputs validated. Comparing candidate solutions.");
    let result;
    if (work.kind === "allocation") result = allocation(work, progress);
    else if (work.kind === "schedule") result = schedule(work, progress);
    else if (work.kind === "forecast") result = forecast(work);
    else if (work.kind === "research") result = research(work, request.goal);
    else
        fail(
            "Choose research, allocation, schedule or forecast. Coding runs in your local agent with Docker isolation.",
        );
    progress("Independent checks complete. Preparing evidence for review.");
    return { schema: "agialpha-browser-result-v1", kind: work.kind, ...result };
}
