// SPDX-License-Identifier: Apache-2.0
import {
    canonical,
    digest,
    parse,
    hashBytes,
} from "../discovery/engine.mjs?v=1.24.0";
import constants from "./constants.mjs?v=1.24.0";
export { canonical, digest, parse };
export const SCHEMA = "agialpha.mats.scenario.v1";
export const REPORT_SCHEMA = "agialpha.mats.run.v1";
const Q = 1000000;
const sum = (items) => items.reduce((a, b) => a + b, 0);
function keys(value, fields, label) {
    if (
        !value ||
        typeof value !== "object" ||
        Array.isArray(value) ||
        canonical(Object.keys(value).sort()) !== canonical([...fields].sort())
    )
        throw Error(label + " has missing or unknown fields");
}
function integer(value, low, high, label) {
    if (!Number.isSafeInteger(value) || value < low || value > high)
        throw Error(
            label + " must be an integer from " + low + " through " + high,
        );
}
function text(value, label, maximum) {
    if (
        typeof value !== "string" ||
        !value.trim() ||
        new TextEncoder().encode(value).length > maximum ||
        /[\u0000-\u001f\ud800-\udfff]/u.test(value)
    )
        throw Error(label + " must be bounded text without control characters");
}
function identifier(value) {
    if (typeof value !== "string" || !/^[a-z][a-z0-9-]{0,39}$/.test(value))
        throw Error("Invalid ID");
}
export function validate(raw) {
    keys(
        raw,
        [
            "schema",
            "id",
            "title",
            "note",
            "seed",
            "search",
            "objective",
            "gates",
            "resources",
            "stages",
        ],
        "Scenario",
    );
    if (raw.schema !== SCHEMA) throw Error("Unsupported MATS scenario schema");
    identifier(raw.id);
    text(raw.title, "Title", 160);
    text(raw.note, "Assumptions", 600);
    integer(raw.seed, 1, 4294967295, "Seed");
    const limits = {
        iterations: [1, 240],
        depth: [1, 6],
        explorationBps: [0, 40000],
        trainingSamples: [4, 64],
        evaluationSamples: [20, 128],
    };
    keys(raw.search, [...Object.keys(limits), "auditOracle"], "Search");
    for (const [field, [low, high]] of Object.entries(limits))
        integer(raw.search[field], low, high, field);
    if (typeof raw.search.auditOracle !== "boolean")
        throw Error("auditOracle must be true or false");
    for (const [section, bounds] of [
        [
            "objective",
            {
                value: [0, 10000],
                costWeight: [0, 100],
                timeWeight: [0, 100],
                escapePenalty: [0, 100000],
            },
        ],
        [
            "gates",
            {
                minGain: [0, 10000],
                maxEscapeBps: [0, 10000],
                deadline: [1, 10000],
                maxMeanCost: [0, 10000],
                maxReviewMinutes: [0, 1440],
                bountyTokens: [1, 1000000],
            },
        ],
    ]) {
        keys(raw[section], Object.keys(bounds), section);
        for (const [field, [low, high]] of Object.entries(bounds))
            integer(raw[section][field], low, high, field);
    }
    if (
        !Array.isArray(raw.resources) ||
        raw.resources.length < 1 ||
        raw.resources.length > 4
    )
        throw Error("Provide 1–4 resource pools");
    const resources = new Set();
    for (const resource of raw.resources) {
        keys(resource, ["id", "label", "capacity"], "Resource");
        identifier(resource.id);
        text(resource.label, "Resource label", 80);
        integer(resource.capacity, 1, 4, "Resource capacity");
        if (resources.has(resource.id)) throw Error("Duplicate resource ID");
        resources.add(resource.id);
    }
    if (
        !Array.isArray(raw.stages) ||
        raw.stages.length < 2 ||
        raw.stages.length > 6
    )
        throw Error("Provide 2–6 stages in topological order");
    const seen = new Set();
    let space = 1;
    raw.stages.forEach((stage, index) => {
        keys(
            stage,
            [
                "id",
                "label",
                "metaAgent",
                "resource",
                "depends",
                "baseline",
                "choices",
            ],
            "Stage",
        );
        identifier(stage.id);
        identifier(stage.resource);
        if (seen.has(stage.id)) throw Error("Duplicate stage ID");
        seen.add(stage.id);
        text(stage.label, "Stage label", 80);
        text(stage.metaAgent, "Meta-agent label", 80);
        if (!resources.has(stage.resource))
            throw Error("Unknown stage resource");
        if (!Array.isArray(stage.depends) || stage.depends.length > 6)
            throw Error("Dependencies require earlier stage indices");
        stage.depends.forEach((parent) =>
            integer(parent, 0, index - 1, "Dependency index"),
        );
        if (new Set(stage.depends).size !== stage.depends.length)
            throw Error("Duplicate dependency");
        if (
            !Array.isArray(stage.choices) ||
            stage.choices.length < 2 ||
            stage.choices.length > 4
        )
            throw Error("Each stage needs 2–4 executable model choices");
        integer(stage.baseline, 0, stage.choices.length - 1, "Baseline choice");
        const ids = new Set();
        for (const choice of stage.choices) {
            keys(
                choice,
                [
                    "id",
                    "label",
                    "minutes",
                    "cost",
                    "defectBps",
                    "detectBps",
                    "reviewMinutes",
                ],
                "Choice",
            );
            identifier(choice.id);
            text(choice.label, "Choice label", 80);
            if (ids.has(choice.id)) throw Error("Duplicate choice ID");
            ids.add(choice.id);
            for (const [field, low, high] of [
                ["minutes", 1, 240],
                ["cost", 0, 1000],
                ["defectBps", 0, 10000],
                ["detectBps", 0, 10000],
                ["reviewMinutes", 0, 240],
            ])
                integer(choice[field], low, high, field);
        }
        space *= stage.choices.length;
    });
    if (space > 1024)
        throw Error(
            "The bounded laboratory supports at most 1,024 complete designs",
        );
    return parse(canonical(raw));
}
export class Random {
    constructor(seed) {
        this.state = seed >>> 0 || 1;
    }
    next() {
        let value = this.state;
        value ^= value << 13;
        value ^= value >>> 17;
        value ^= value << 5;
        this.state = value >>> 0;
        return this.state;
    }
}
export function workloads(source, count, seed) {
    const stream = new Random(seed);
    return Array.from({ length: count }, () =>
        source.stages.map(() => [
            80 + (stream.next() % 41),
            stream.next() % 10000,
            stream.next() % 10000,
        ]),
    );
}
export function simulate(source, policy, rolls) {
    const slots = Object.fromEntries(
        source.resources.map((pool) => [pool.id, Array(pool.capacity).fill(0)]),
    );
    const rows = [];
    source.stages.forEach((stage, index) => {
        const choice = stage.choices[policy[index]],
            [demand, defect, detection] = rolls[index];
        const fault =
            stage.depends.some((parent) => rows[parent].fault) ||
            defect < choice.defectBps;
        const rework = Number(fault && detection < choice.detectBps);
        const duration =
            Math.floor((choice.minutes * demand + 99) / 100) * (1 + rework);
        const lanes = slots[stage.resource],
            lane = lanes.indexOf(Math.min(...lanes));
        const start = Math.max(
                lanes[lane],
                ...stage.depends.map((parent) => rows[parent].end),
            ),
            end = start + duration;
        lanes[lane] = end;
        rows.push({
            stage: index,
            choice: policy[index],
            lane,
            start,
            end,
            cost: choice.cost * (1 + rework),
            rework,
            fault: !!(fault && !rework),
            reviewMinutes: choice.reviewMinutes * (1 + rework),
        });
    });
    const predecessors = new Set(
        source.stages.flatMap((stage) => stage.depends),
    );
    const escaped = Number(
        rows.some((row, index) => !predecessors.has(index) && row.fault),
    );
    const cost = sum(rows.map((row) => row.cost)),
        makespan = Math.max(...rows.map((row) => row.end)),
        objective = source.objective;
    return {
        utility:
            objective.value -
            cost * objective.costWeight -
            makespan * objective.timeWeight -
            escaped * objective.escapePenalty,
        cost,
        makespan,
        escaped,
        rework: sum(rows.map((row) => row.rework)),
        reviewMinutes: sum(rows.map((row) => row.reviewMinutes)),
        stages: rows,
    };
}
export function measure(source, policy, samples, details = false) {
    const episodes = samples.map((row) => simulate(source, policy, row));
    const totals = Object.fromEntries(
        [
            "utility",
            "cost",
            "makespan",
            "escaped",
            "rework",
            "reviewMinutes",
        ].map((key) => [key, sum(episodes.map((row) => row[key]))]),
    );
    const result = {
        totals,
        p95Minutes: episodes.map((row) => row.makespan).sort((a, b) => a - b)[
            Math.floor((95 * episodes.length + 99) / 100) - 1
        ],
    };
    if (details) result.episodes = episodes;
    return result;
}
const policyKey = (policy) => policy.join(",");
export function moves(source, policy, forbidden) {
    const result = [];
    source.stages.forEach((stage, index) =>
        stage.choices.forEach((_, option) => {
            const changed = [...policy];
            changed[index] = option;
            if (option !== policy[index] && !forbidden.has(policyKey(changed)))
                result.push({ stage: index, from: policy[index], to: option });
        }),
    );
    return result;
}
function rewritten(policy, move) {
    const result = [...policy];
    result[move.stage] = move.to;
    return result;
}
function isqrt(value) {
    let root = Math.floor(Math.sqrt(value));
    while ((root + 1) * (root + 1) <= value) root++;
    while (root * root > value) root--;
    return root;
}
export function uct(total, visits, parentVisits, exploration) {
    if (visits <= 0) return 10 ** 15;
    return (
        Math.floor(total / visits) +
        Math.floor(
            (exploration *
                isqrt(
                    Math.floor(
                        (constants.logQ[Math.max(1, parentVisits)] * Q) /
                            visits,
                    ),
                )) /
                10000,
        )
    );
}
function lexLess(a, b) {
    for (let index = 0; index < a.length; index++)
        if (a[index] !== b[index]) return a[index] < b[index];
    return false;
}
export function search(source) {
    const spec = source.search,
        baseline = source.stages.map((stage) => stage.baseline);
    const samples = workloads(
            source,
            spec.trainingSamples,
            source.seed ^ 0x9e3779b9,
        ),
        stream = new Random(source.seed),
        cache = new Map();
    function score(policy) {
        const key = policyKey(policy);
        if (!cache.has(key)) cache.set(key, measure(source, policy, samples));
        return cache.get(key);
    }
    const upperCost = sum(
        source.stages.map(
            (stage) =>
                Math.max(...stage.choices.map((choice) => choice.cost)) * 2,
        ),
    );
    const upperTime = sum(
        source.stages.map(
            (stage) =>
                Math.floor(
                    (Math.max(
                        ...stage.choices.map((choice) => choice.minutes),
                    ) *
                        120 +
                        99) /
                        100,
                ) * 2,
        ),
    );
    const objective = source.objective,
        span =
            upperCost * objective.costWeight +
            upperTime * objective.timeWeight +
            objective.escapePenalty +
            1,
        floor = objective.value - span;
    const nodes = [];
    function add(policy, parent, move, path) {
        const depth = path.length,
            forbidden = new Set([
                ...path.map((index) => policyKey(nodes[index].policy)),
                policyKey(policy),
            ]);
        const node = {
            id: nodes.length,
            parent,
            depth,
            policy: [...policy],
            rewrite: move,
            children: [],
            visits: 0,
            totalQ: 0,
            untried: depth < spec.depth ? moves(source, policy, forbidden) : [],
        };
        nodes.push(node);
        if (parent !== null) nodes[parent].children.push(node.id);
        return node.id;
    }
    add(baseline, null, null, []);
    let best = [...baseline],
        bestScore = score(best).totals.utility,
        bestIteration = 0,
        bestPath = [];
    const trace = [];
    for (let iteration = 0; iteration < spec.iterations; iteration++) {
        const path = [0];
        let expanded = null;
        while (nodes[path.at(-1)].depth < spec.depth) {
            const node = nodes[path.at(-1)];
            if (node.untried.length) {
                const [move] = node.untried.splice(
                    stream.next() % node.untried.length,
                    1,
                );
                expanded = add(
                    rewritten(node.policy, move),
                    node.id,
                    move,
                    path,
                );
                path.push(expanded);
                break;
            }
            if (!node.children.length) break;
            let selected = node.children[0],
                largest = -Infinity;
            for (const index of node.children) {
                const value = uct(
                    nodes[index].totalQ,
                    nodes[index].visits,
                    node.visits,
                    spec.explorationBps,
                );
                if (value > largest) {
                    largest = value;
                    selected = index;
                }
            }
            path.push(selected);
        }
        let policy = [...nodes[path.at(-1)].policy];
        const forbidden = new Set(
                path.map((index) => policyKey(nodes[index].policy)),
            ),
            rollout = [];
        for (
            let depth = nodes[path.at(-1)].depth;
            depth < spec.depth;
            depth++
        ) {
            const options = moves(source, policy, forbidden);
            if (!options.length) break;
            const move = options[stream.next() % options.length];
            rollout.push(move);
            policy = rewritten(policy, move);
            forbidden.add(policyKey(policy));
        }
        const measured = score(policy),
            utility = measured.totals.utility;
        const valueQ = Math.floor(
            ((utility - floor * spec.trainingSamples) * Q) /
                (span * spec.trainingSamples),
        );
        for (const index of path) {
            nodes[index].visits++;
            nodes[index].totalQ += valueQ;
        }
        if (
            utility > bestScore ||
            (utility === bestScore && lexLess(policy, best))
        ) {
            best = [...policy];
            bestScore = utility;
            bestIteration = iteration + 1;
            bestPath = [
                ...path.slice(1).map((index) => nodes[index].rewrite),
                ...rollout,
            ];
        }
        trace.push({
            iteration: iteration + 1,
            path,
            expanded,
            rollout,
            policy,
            utilityTotal: utility,
            valueQ,
            bestUtilityTotal: bestScore,
            bestPolicy: [...best],
        });
    }
    const exportedNodes = nodes.map((node) => {
        const { untried, ...rest } = node;
        return { ...rest, untriedCount: untried.length };
    });
    return {
        nodes: exportedNodes,
        trace,
        candidate: best,
        candidateTraining: score(best),
        baselineTraining: score(baseline),
        candidateIteration: bestIteration,
        candidateRewrites: bestPath,
        uniqueEvaluations: cache.size,
        simulationEpisodes: cache.size * spec.trainingSamples,
        normalization: { floor, span, scale: Q },
    };
}
function* designs(stages, prefix = []) {
    if (prefix.length === stages.length) {
        yield prefix;
        return;
    }
    for (let i = 0; i < stages[prefix.length].choices.length; i++)
        yield* designs(stages, [...prefix, i]);
}
export async function evaluate(raw) {
    const source = validate(raw),
        spec = source.search,
        gates = source.gates,
        result = search(source);
    const baseline = source.stages.map((stage) => stage.baseline),
        samples = workloads(
            source,
            spec.evaluationSamples,
            source.seed ^ 0xa341316c,
        );
    const evaluation = {
        baseline: measure(source, baseline, samples, true),
        candidate: measure(source, result.candidate, samples, true),
    };
    const totals = evaluation.candidate.totals,
        gain = totals.utility - evaluation.baseline.totals.utility,
        count = spec.evaluationSamples;
    const check = (id, label, observed, limit, comparison) => ({
        id,
        label,
        observed,
        limit,
        comparison,
        passed: comparison === ">=" ? observed >= limit : observed <= limit,
    });
    const checks = [
        check(
            "gain",
            "Held-out utility gain",
            gain,
            gates.minGain * count,
            ">=",
        ),
        check(
            "quality",
            "Escaped-defect ceiling",
            totals.escaped * 10000,
            gates.maxEscapeBps * count,
            "<=",
        ),
        check(
            "deadline",
            "95th-percentile delivery time",
            evaluation.candidate.p95Minutes,
            gates.deadline,
            "<=",
        ),
        check(
            "cost",
            "Mean resource-cost ceiling",
            totals.cost,
            gates.maxMeanCost * count,
            "<=",
        ),
        check(
            "review",
            "Mean reviewer-effort ceiling",
            totals.reviewMinutes,
            gates.maxReviewMinutes * count,
            "<=",
        ),
    ];
    const oracle = { enabled: spec.auditOracle, evaluations: 0 },
        space = source.stages.reduce(
            (value, stage) => value * stage.choices.length,
            1,
        );
    if (spec.auditOracle) {
        const training = workloads(
            source,
            spec.trainingSamples,
            source.seed ^ 0x9e3779b9,
        );
        let bestScore = null,
            bestPolicy = [];
        for (const choices of designs(source.stages)) {
            const total = measure(source, choices, training).totals.utility;
            if (bestScore === null || total > bestScore) {
                bestScore = total;
                bestPolicy = choices;
            }
        }
        Object.assign(oracle, {
            evaluations: space,
            simulationEpisodes: space * spec.trainingSamples,
            policy: bestPolicy,
            utilityTotal: bestScore,
            gapTotal: bestScore - result.candidateTraining.totals.utility,
        });
    }
    const inputHash = await digest(source);
    const proposal = {
        schema: "agialpha.mats.policy-proposal.v1",
        inputSha256: inputHash,
        activePolicy: baseline,
        candidatePolicy: result.candidate,
        stageIds: source.stages.map((stage) => stage.id),
        state: "UNAPPROVED",
    };
    Object.assign(result, {
        evaluation,
        gainTotal: gain,
        gates: checks,
        oracle,
        designSpace: space,
        proposal,
        status: checks.every((check) => check.passed)
            ? "REVIEW_REQUIRED"
            : "HOLD_BASELINE",
        scope: constants.scope,
        inputSha256: inputHash,
        jobs: [
            {
                goal:
                    "Independently reproduce MATS " +
                    source.id +
                    "; input SHA-256: " +
                    inputHash +
                    ". Review the search, resource model, defect assumptions and candidate workflow.",
                successMetric:
                    "Recompute every selection, rewrite, rollout and review gate; validate with fresh workloads and representative real measurements. Approve or reject with evidence; a checksum is not validator approval.",
                bounty: (BigInt(gates.bountyTokens) * 10n ** 18n).toString(),
                duration: 604800,
                priceWeight: 5000,
            },
        ],
    });
    const report = { schema: REPORT_SCHEMA, input: source, result };
    return { ...report, sha256: await digest(report) };
}
export async function verify(report) {
    keys(report, ["schema", "input", "result", "sha256"], "Run");
    const expected = await evaluate(report.input);
    if (canonical(report) !== canonical(expected))
        throw Error(
            "Run differs from recomputation; imported trees, policies and gates are not trusted",
        );
    return expected;
}
const literal = (value) =>
    value.replace(/([\\\u0060*_{}\[\]<>()#+.!|])/g, "\\$1");
export function brief(report) {
    const source = report.input,
        result = report.result;
    const lines = [
        "# " + literal(source.title),
        "",
        result.status,
        "",
        literal(source.note),
        "",
        "Search: " +
            source.search.iterations +
            " iterations, " +
            result.uniqueEvaluations +
            " unique designs, " +
            result.simulationEpisodes +
            " simulated training workloads.",
        "Held-out utility gain: " +
            result.gainTotal +
            " across " +
            source.search.evaluationSamples +
            " paired workloads.",
        "Oracle: " +
            result.oracle.evaluations +
            " additional design evaluations; never used to select the candidate.",
        "",
        "| Review gate | Result | Exact comparison |",
        "|---|---|---|",
    ];
    lines.push(
        ...result.gates.map(
            (gate) =>
                "| " +
                gate.label +
                " | " +
                (gate.passed ? "PASS" : "HOLD") +
                " | " +
                gate.observed +
                " " +
                gate.comparison +
                " " +
                gate.limit +
                " |",
        ),
    );
    lines.push(
        "",
        "The active workflow remains the baseline. Candidate indices refer to choices in scenario order.",
        "Selecting a seed after inspecting evaluation results invalidates an independent test.",
        "",
        constants.scope,
        "",
        "Run SHA-256: " + report.sha256,
        "",
    );
    return lines.join("\n");
}
export async function artifacts(report) {
    report = await verify(report);
    const encoder = new TextEncoder();
    const files = Object.fromEntries(
        Object.entries({
            "scenario.json": canonical(report.input) + "\n",
            "run.json": canonical(report) + "\n",
            "policy-proposal.json": canonical(report.result.proposal) + "\n",
            "jobs.json": canonical(report.result.jobs) + "\n",
            "review.md": brief(report),
        }).map(([name, data]) => [name, encoder.encode(data)]),
    );
    let hashes = "";
    for (const name of Object.keys(files).sort())
        hashes += (await hashBytes(files[name])) + "  " + name + "\n";
    files.SHA256SUMS = encoder.encode(hashes);
    return files;
}
