// SPDX-License-Identifier: Apache-2.0
import {
    canonical,
    digest,
    parse,
    hashBytes,
} from "../discovery/engine.mjs?v=1.21.0";
import constants from "./constants.mjs?v=1.21.0";
export { canonical, digest, parse };
export const SCHEMA = "agialpha.curriculum.scenario.v1",
    REPORT_SCHEMA = "agialpha.curriculum.run.v1";
export const OPS = ["inc", "dec", "double", "negate", "abs", "square", "mod3"];
export const FAMILIES = ["arithmetic", "nonlinear", "remainder"];
const BUDGETS = [8, 32, 128, 400],
    LOG_Q = constants.logQ,
    sum = (a) => a.reduce((x, y) => x + y, 0);
const floor = Math.floor;
function keys(v, fields, label) {
    if (
        !v ||
        typeof v !== "object" ||
        Array.isArray(v) ||
        canonical(Object.keys(v).sort()) !== canonical(fields.sort())
    )
        throw Error(label + " has missing or unknown fields");
}
function integer(v, lo, hi, name) {
    if (!Number.isSafeInteger(v) || v < lo || v > hi)
        throw Error(name + " must be an integer from " + lo + " through " + hi);
}
function text(v, name, max) {
    if (
        typeof v !== "string" ||
        !v.trim() ||
        new TextEncoder().encode(v).length > max ||
        /[\u0000-\u001f\ud800-\udfff]/u.test(v)
    )
        throw Error(name + " must be bounded text without control characters");
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
            "rounds",
            "tasksPerRound",
            "maxDepth",
            "families",
            "positiveExamples",
            "temperature",
            "policy",
        ],
        "Scenario",
    );
    if (raw.schema !== SCHEMA)
        throw Error("Unsupported curriculum scenario schema");
    if (typeof raw.id !== "string" || !/^[a-z][a-z0-9-]{0,39}$/.test(raw.id))
        throw Error("Invalid ID");
    text(raw.title, "Title", 120);
    text(raw.note, "Note", 600);
    for (const [k, lo, hi] of [
        ["seed", 0, 4294967295],
        ["rounds", 1, 12],
        ["tasksPerRound", 3, 12],
        ["maxDepth", 1, 3],
        ["temperature", 0, 1000],
    ])
        integer(raw[k], lo, hi, k);
    if (typeof raw.positiveExamples !== "boolean")
        throw Error("positiveExamples must be a boolean");
    if (
        !Array.isArray(raw.families) ||
        !raw.families.length ||
        raw.families.length > 3 ||
        raw.families.some((f) => !FAMILIES.includes(f)) ||
        new Set(raw.families).size !== raw.families.length
    )
        throw Error(
            "Choose unique arithmetic, nonlinear and/or remainder families",
        );
    keys(
        raw.policy,
        ["minAccuracyBps", "minFamilyBps", "minGainBps", "maxMeanOperations"],
        "Policy",
    );
    for (const k of ["minAccuracyBps", "minFamilyBps", "minGainBps"])
        integer(raw.policy[k], 0, 10000, k);
    integer(raw.policy.maxMeanOperations, 1, 10000, "maxMeanOperations");
    return JSON.parse(canonical(raw));
}
export class Random {
    constructor(seed) {
        this.state = seed || 0x9e3779b9;
    }
    next() {
        let x = this.state;
        x ^= x << 13;
        x ^= x >>> 17;
        x ^= x << 5;
        return (this.state = x >>> 0);
    }
}
export function execute(program, x) {
    if (
        !Array.isArray(program) ||
        program.length > 3 ||
        program.some((op) => !OPS.includes(op))
    )
        throw Error("Programs contain at most three known operators");
    integer(x, -8, 8, "Input");
    for (const op of program) {
        if (op === "inc") x++;
        else if (op === "dec") x--;
        else if (op === "double") x *= 2;
        else if (op === "negate") x = -x;
        else if (op === "abs") x = Math.abs(x);
        else if (op === "square") x *= x;
        else x = ((x % 3) + 3) % 3;
    }
    return x;
}
function family(p) {
    return p.includes("mod3")
        ? "remainder"
        : p.includes("square") || p.includes("abs")
          ? "nonlinear"
          : "arithmetic";
}
function programs(depth, wide = true) {
    const palette = wide ? OPS : OPS.slice(0, 4),
        result = [[]];
    let prev = [[]];
    for (let d = 1; d <= depth; d++) {
        prev = prev.flatMap((p) => palette.map((op) => [...p, op]));
        result.push(...prev);
    }
    return result;
}
function config(depth = 1, budget = 0, wide = false) {
    return {
        id: `d${depth}-b${BUDGETS[budget]}-${wide ? "wide" : "core"}`,
        depth,
        budgetIndex: budget,
        wide,
    };
}
function neighbors(p, depth) {
    return [
        ...new Map(
            [
                config(p.depth, p.budgetIndex, p.wide),
                config(Math.min(depth, p.depth + 1), p.budgetIndex, p.wide),
                config(p.depth, Math.min(3, p.budgetIndex + 1), p.wide),
                config(p.depth, p.budgetIndex, true),
            ].map((c) => [c.id, c]),
        ).values(),
    ];
}
export function solve(examples, inputs, agent) {
    let operations = 0,
        tried = 0;
    for (const p of programs(agent.depth, agent.wide).slice(
        0,
        BUDGETS[agent.budgetIndex],
    )) {
        tried++;
        let matches = true;
        for (const [x, y] of examples) {
            operations += Math.max(1, p.length);
            if (execute(p, x) !== y) {
                matches = false;
                break;
            }
        }
        if (matches) {
            operations += Math.max(1, p.length) * inputs.length;
            return {
                program: p,
                predictions: inputs.map((x) => execute(p, x)),
                operations,
                tried,
            };
        }
    }
    return { program: null, predictions: null, operations, tried };
}
function propose(
    rng,
    count,
    depth,
    families,
    weights,
    positive,
    prefix,
    review = false,
) {
    const pool = Object.fromEntries(
            families.map((f) => [
                f,
                programs(depth).filter((p) => family(p) === f),
            ]),
        ),
        seen = new Set(),
        tasks = [];
    let attempts = 0;
    while (tasks.length < count && attempts < 512) {
        attempts++;
        let draw = rng.next() % sum(families.map((f) => weights[f])),
            selected = families.at(-1);
        for (const f of families) {
            draw -= weights[f];
            if (draw < 0) {
                selected = f;
                break;
            }
        }
        const p = pool[selected][rng.next() % pool[selected].length],
            sig = Array.from({ length: 11 }, (_, i) => execute(p, i - 5)).join(
                ",",
            );
        if (seen.has(sig)) continue;
        seen.add(sig);
        const train = positive ? [1, 2, 3, 4] : [-3, -1, 1, 3],
            inputs = review ? [-8, -6, 6, 8] : [-5, -2, 0, 5];
        tasks.push({
            id: `${prefix}-${tasks.length + 1}`,
            family: selected,
            oracle: p,
            examples: train.map((x) => [x, execute(p, x)]),
            inputs,
            expected: inputs.map((x) => execute(p, x)),
        });
    }
    return [tasks, attempts - tasks.length];
}
function assess(agent, tasks, temperature) {
    const details = [],
        solved = Object.fromEntries(FAMILIES.map((f) => [f, 0])),
        counts = { ...solved };
    for (const t of tasks) {
        const r = solve(t.examples, t.inputs, agent),
            ok = canonical(r.predictions) === canonical(t.expected);
        counts[t.family]++;
        solved[t.family] += Number(ok);
        details.push({ task: t.id, solved: ok, ...r });
    }
    const total = tasks.length,
        correct = sum(Object.values(solved)),
        operations = sum(details.map((r) => r.operations));
    const entropy = correct
        ? LOG_Q[correct] -
          floor(sum(Object.values(solved).map((n) => n * LOG_Q[n])) / correct)
        : 0;
    const accuracy = floor((correct * 10000) / total),
        meanOps = floor(operations / total),
        energy = meanOps - floor((temperature * entropy) / 1000);
    return {
        agent,
        correct,
        total,
        accuracyBps: accuracy,
        operations,
        meanOperations: meanOps,
        entropyMilliNats: entropy,
        freeEnergyProxy: energy,
        utility: accuracy - meanOps + floor((temperature * entropy) / 1000),
        families: Object.fromEntries(
            FAMILIES.map((f) => [
                f,
                {
                    correct: solved[f],
                    total: counts[f],
                    accuracyBps: counts[f]
                        ? floor((solved[f] * 10000) / counts[f])
                        : 0,
                },
            ]),
        ),
        details,
    };
}
function pareto(rows) {
    return rows
        .filter(
            (r) =>
                !rows.some(
                    (o) =>
                        o.accuracyBps >= r.accuracyBps &&
                        o.meanOperations <= r.meanOperations &&
                        (o.accuracyBps > r.accuracyBps ||
                            o.meanOperations < r.meanOperations),
                ),
        )
        .map((r) => r.agent.id);
}
export async function evaluate(raw) {
    const source = validate(raw),
        rng = new Random(source.seed),
        active = config(),
        archive = new Map([
            [active.id, { agent: active, parent: null, round: 0 }],
        ]),
        history = [];
    let champion = active,
        weights = Object.fromEntries(source.families.map((f) => [f, 100])),
        difficulty = 1,
        replay = [];
    for (let generation = 1; generation <= source.rounds; generation++) {
        const [tasks, rejected] = propose(
            rng,
            source.tasksPerRound,
            difficulty,
            source.families,
            weights,
            source.positiveExamples,
            `r${generation}`,
        );
        replay = [...replay, ...tasks].slice(-48);
        const candidates = neighbors(champion, source.maxDepth);
        for (const c of candidates)
            if (!archive.has(c.id))
                archive.set(c.id, {
                    agent: c,
                    parent: champion.id,
                    round: generation,
                });
        const rows = candidates.map((c) =>
                assess(c, replay, source.temperature),
            ),
            front = pareto(rows);
        const selected = rows
            .filter((r) => front.includes(r.agent.id))
            .sort(
                (a, b) =>
                    b.utility - a.utility ||
                    b.accuracyBps - a.accuracyBps ||
                    a.meanOperations - b.meanOperations ||
                    (a.agent.id < b.agent.id
                        ? -1
                        : a.agent.id > b.agent.id
                          ? 1
                          : 0),
            )[0];
        champion = selected.agent;
        const recent = assess(champion, tasks, source.temperature),
            nextWeights = Object.fromEntries(
                source.families.map((f) => {
                    const r = recent.families[f];
                    return [
                        f,
                        100 +
                            floor(
                                (4 * r.correct * (r.total - r.correct) * 100) /
                                    Math.max(1, r.total ** 2),
                            ) +
                            (r.total === 0 ? 100 : 0),
                    ];
                }),
            );
        let nextDifficulty = difficulty;
        if (recent.accuracyBps >= 7500)
            nextDifficulty = Math.min(source.maxDepth, difficulty + 1);
        else if (recent.accuracyBps < 3500)
            nextDifficulty = Math.max(1, difficulty - 1);
        history.push({
            round: generation,
            difficulty,
            nextDifficulty,
            weights,
            nextWeights,
            tasks,
            rejected,
            replaySize: replay.length,
            candidates: rows,
            pareto: front,
            winner: champion.id,
            recent,
        });
        weights = nextWeights;
        difficulty = nextDifficulty;
    }
    const holdoutRng = new Random((source.seed ^ 0xa5a5a5a5) >>> 0),
        heldoutTasks = [];
    for (const f of FAMILIES)
        heldoutTasks.push(
            ...propose(
                holdoutRng,
                8,
                source.maxDepth,
                [f],
                { [f]: 100 },
                false,
                `heldout-${f}`,
                true,
            )[0],
        );
    const baseline = assess(active, heldoutTasks, source.temperature),
        candidate = assess(champion, heldoutTasks, source.temperature),
        gain = candidate.accuracyBps - baseline.accuracyBps,
        p = source.policy;
    const gates = [
        {
            id: "accuracy",
            label: "Held-out accuracy",
            observed: candidate.accuracyBps,
            limit: p.minAccuracyBps,
            comparison: ">=",
        },
        {
            id: "coverage",
            label: "Weakest task family",
            observed: Math.min(
                ...Object.values(candidate.families).map((v) => v.accuracyBps),
            ),
            limit: p.minFamilyBps,
            comparison: ">=",
        },
        {
            id: "gain",
            label: "Gain over baseline",
            observed: gain,
            limit: p.minGainBps,
            comparison: ">=",
        },
        {
            id: "operations",
            label: "Mean operation budget",
            observed: candidate.meanOperations,
            limit: p.maxMeanOperations,
            comparison: "<=",
        },
    ];
    for (const g of gates)
        g.passed =
            g.comparison === ">="
                ? g.observed >= g.limit
                : g.observed <= g.limit;
    const inputSha256 = await digest(source),
        proposal = {
            schema: "agialpha.curriculum.proposal.v1",
            inputSha256,
            status: "UNAPPROVED",
            active,
            candidate: champion,
            reason: "Independent validator approval and task-specific deployment testing are required.",
        };
    const jobs = [
        {
            goal: `Reproduce curriculum ${source.id}; input SHA-256: ${inputSha256}. Inspect the solver, lineage and independent evaluation.`,
            successMetric:
                "Recompute all tasks and gates exactly, then validate the frozen solver on fresh domain tasks. Independent validators approve or reject with evidence.",
            bounty: "100000000000000000000",
            duration: 604800,
            priceWeight: 5000,
        },
    ];
    const result = {
        status: gates.every((g) => g.passed) ? "REVIEW_ELIGIBLE" : "HOLD",
        history,
        lineage: [...archive.values()],
        heldoutTasks,
        baseline,
        candidate,
        gainBps: gain,
        gates,
        proposal,
        jobs,
    };
    const report = {
        schema: REPORT_SCHEMA,
        scope: constants.scope,
        input: source,
        inputSha256,
        result,
    };
    return { ...report, sha256: await digest(report) };
}
export async function verify(raw) {
    keys(
        raw,
        ["schema", "scope", "input", "inputSha256", "result", "sha256"],
        "Run",
    );
    const expected = await evaluate(raw.input);
    if (canonical(raw) !== canonical(expected))
        throw Error(
            "Run does not match independent recomputation; hashes alone do not prove correctness",
        );
    return expected;
}
const literal = (s) => s.replace(/([\\`*_{}\[\]<>()#+.!|])/g, "\\$1");
export function brief(report) {
    const r = report.result,
        s = report.input;
    return [
        `# ${literal(s.title)}`,
        "",
        r.status,
        "",
        literal(s.note),
        "",
        `Frozen solver: ${r.candidate.agent.id}; accuracy: ${r.candidate.accuracyBps}/10000.`,
        `Baseline: ${r.baseline.accuracyBps}/10000; gain: ${r.gainBps} basis points.`,
        "",
        "| Gate | Result | Comparison |",
        "|---|---|---|",
        ...r.gates.map(
            (g) =>
                `| ${g.label} | ${g.passed ? "PASS" : "HOLD"} | ${g.observed} ${g.comparison} ${g.limit} |`,
        ),
        "",
        "The active solver remains the baseline. Do not tune seeds or policies after reading held-out results.",
        "",
        constants.scope,
        "",
        `Run SHA-256: ${report.sha256}`,
        "",
    ].join("\n");
}
export async function artifacts(report) {
    report = await verify(report);
    const enc = new TextEncoder(),
        values = Object.fromEntries(
            Object.entries({
                "scenario.json": canonical(report.input) + "\n",
                "run.json": canonical(report) + "\n",
                "solver-proposal.json":
                    canonical(report.result.proposal) + "\n",
                "jobs.json": canonical(report.result.jobs) + "\n",
                "review.md": brief(report),
            }).map(([n, s]) => [n, enc.encode(s)]),
        );
    let sums = "";
    for (const n of Object.keys(values).sort())
        sums += `${await hashBytes(values[n])}  ${n}\n`;
    values.SHA256SUMS = enc.encode(sums);
    return values;
}
