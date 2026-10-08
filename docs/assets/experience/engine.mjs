// SPDX-License-Identifier: Apache-2.0
import {
    canonical,
    digest,
    parse,
    hashBytes,
} from "../discovery/engine.mjs?v=1.24.0";
import model from "./constants.mjs?v=1.24.0";
export { canonical, digest, parse };
export const SCHEMA = "agialpha.experience.scenario.v1";
export const REPORT_SCHEMA = "agialpha.experience.run.v1";
function keys(value, expected, label) {
    if (
        !value ||
        typeof value !== "object" ||
        Array.isArray(value) ||
        canonical(Object.keys(value).sort()) !== canonical([...expected].sort())
    )
        throw Error(`${label} has missing or unknown fields`);
}
function integer(value, low, high, label) {
    if (!Number.isSafeInteger(value) || value < low || value > high)
        throw Error(`${label} must be an integer from ${low} through ${high}`);
}
function text(value, label, maximum) {
    if (
        typeof value !== "string" ||
        !value.trim() ||
        new TextEncoder().encode(value).length > maximum ||
        /[\u0000-\u001f\ud800-\udfff]/u.test(value)
    )
        throw Error(
            `${label} must be nonempty, bounded text without control characters`,
        );
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
            "training",
            "reward",
            "gates",
            "actions",
            "contexts",
        ],
        "Scenario",
    );
    if (raw.schema !== SCHEMA)
        throw Error("Unsupported experience scenario schema");
    identifier(raw.id);
    text(raw.title, "Title", 160);
    text(raw.note, "Note", 600);
    integer(raw.seed, 1, 4294967295, "Seed");
    const training = raw.training;
    keys(
        training,
        [
            "steps",
            "evaluationSteps",
            "explorationBps",
            "memoryWindow",
            "shiftAt",
        ],
        "Training",
    );
    for (const [name, low, high] of [
        ["steps", 12, 600],
        ["evaluationSteps", 30, 600],
        ["explorationBps", 0, 10000],
        ["memoryWindow", 1, 200],
        ["shiftAt", 0, training.steps],
    ])
        integer(training[name], low, high, name);
    keys(
        raw.reward,
        ["costWeight", "incidentPenalty", "proxyWeight"],
        "Reward",
    );
    for (const [name, high] of [
        ["costWeight", 100],
        ["incidentPenalty", 10000],
        ["proxyWeight", 100],
    ])
        integer(raw.reward[name], 0, high, name);
    const limits = {
        minGain: [0, 10000],
        maxIncidentBps: [0, 10000],
        minSuccessBps: [0, 10000],
        maxMeanCost: [0, 1000],
        minSamples: [1, 200],
        maxRetentionLoss: [0, 10000],
        bountyTokens: [1, 1000000],
    };
    keys(raw.gates, Object.keys(limits), "Gates");
    for (const [name, [low, high]] of Object.entries(limits))
        integer(raw.gates[name], low, high, name);
    if (
        !Array.isArray(raw.actions) ||
        raw.actions.length < 2 ||
        raw.actions.length > 5
    )
        throw Error("Provide 2–5 actions");
    let ids = new Set();
    for (const action of raw.actions) {
        keys(action, ["id", "label"], "Action");
        identifier(action.id);
        text(action.label, "Action label", 80);
        if (ids.has(action.id)) throw Error("Duplicate action ID");
        ids.add(action.id);
    }
    if (
        !Array.isArray(raw.contexts) ||
        raw.contexts.length < 1 ||
        raw.contexts.length > 6
    )
        throw Error("Provide 1–6 contexts");
    ids = new Set();
    for (const context of raw.contexts) {
        keys(
            context,
            ["id", "label", "baseline", "initial", "shifted"],
            "Context",
        );
        identifier(context.id);
        text(context.label, "Context label", 80);
        if (ids.has(context.id)) throw Error("Duplicate context ID");
        ids.add(context.id);
        integer(context.baseline, 0, raw.actions.length - 1, "Baseline action");
        for (const phase of ["initial", "shifted"]) {
            const outcomes = context[phase];
            if (
                !Array.isArray(outcomes) ||
                outcomes.length !== raw.actions.length
            )
                throw Error(
                    "Every context requires one outcome model per action in both phases",
                );
            for (const outcome of outcomes) {
                keys(
                    outcome,
                    ["successBps", "incidentBps", "cost", "proxy"],
                    "Outcome",
                );
                for (const [name, high] of [
                    ["successBps", 10000],
                    ["incidentBps", 10000],
                    ["cost", 1000],
                    ["proxy", 1000],
                ])
                    integer(outcome[name], 0, high, name);
            }
        }
    }
    return parse(canonical(raw));
}
class Random {
    constructor(seed) {
        this.state = seed || 1;
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
const sum = (values) => values.reduce((a, b) => a + b, 0);
function choose(memory) {
    let best = 0;
    for (let i = 1; i < memory.length; i++)
        if (
            sum(memory[i]) * Math.max(1, memory[best].length) >
            sum(memory[best]) * Math.max(1, memory[i].length)
        )
            best = i;
    return best;
}
function observe(outcome, rolls, reward) {
    const success = Number(rolls[0] < outcome.successBps),
        incident = Number(rolls[1] < outcome.incidentBps);
    return {
        success,
        incident,
        cost: outcome.cost,
        proxy: outcome.proxy,
        reward:
            success * 1000 -
            outcome.cost * reward.costWeight -
            incident * reward.incidentPenalty +
            outcome.proxy * reward.proxyWeight,
    };
}
export async function evaluate(raw) {
    const source = validate(raw),
        { training: spec, contexts, actions, reward, gates } = source;
    const memory = contexts.map(() => actions.map(() => [])),
        counts = contexts.map(() => actions.map(() => 0)),
        rng = new Random(source.seed),
        trace = [];
    for (let step = 0; step < spec.steps; step++) {
        const ci = step % contexts.length,
            context = contexts[ci],
            exploration = rng.next() % 10000,
            randomAction = rng.next() % actions.length;
        const unseen = counts[ci].findIndex((count) => !count);
        const action =
            unseen >= 0
                ? unseen
                : exploration < spec.explorationBps
                  ? randomAction
                  : choose(memory[ci]);
        const phase =
            spec.shiftAt && step >= spec.shiftAt ? "shifted" : "initial";
        const outcome = observe(
            context[phase][action],
            [rng.next() % 10000, rng.next() % 10000],
            reward,
        );
        const samples = memory[ci][action];
        samples.push(outcome.reward);
        if (samples.length > spec.memoryWindow)
            samples.splice(0, samples.length - spec.memoryWindow);
        counts[ci][action]++;
        trace.push({ step: step + 1, context: ci, action, phase, ...outcome });
    }
    const candidate = memory.map(choose),
        baseline = contexts.map((c) => c.baseline);
    function shadow(phase, seed) {
        const stream = new Random(seed),
            totals = Object.fromEntries(
                ["baseline", "candidate"].map((name) => [
                    name,
                    { reward: 0, success: 0, incident: 0, cost: 0, proxy: 0 },
                ]),
            ),
            episodes = [];
        for (let step = 0; step < spec.evaluationSteps; step++) {
            const ci = step % contexts.length,
                rolls = [stream.next() % 10000, stream.next() % 10000],
                row = { step: step + 1, context: ci };
            for (const [name, policy] of [
                ["baseline", baseline],
                ["candidate", candidate],
            ]) {
                const outcome = observe(
                    contexts[ci][phase][policy[ci]],
                    rolls,
                    reward,
                );
                row[name] = { action: policy[ci], ...outcome };
                for (const [metric, value] of Object.entries(outcome))
                    totals[name][metric] += value;
            }
            episodes.push(row);
        }
        return { phase, episodes, totals };
    }
    const evaluation = shadow(
            spec.shiftAt ? "shifted" : "initial",
            (source.seed ^ 0x9e3779b9) >>> 0,
        ),
        retention = shadow("initial", (source.seed ^ 0xa341316c) >>> 0);
    const base = evaluation.totals.baseline,
        proposed = evaluation.totals.candidate,
        n = spec.evaluationSteps,
        gain = proposed.reward - base.reward,
        retainedGain =
            retention.totals.candidate.reward -
            retention.totals.baseline.reward;
    const checks = [
        {
            id: "gain",
            label: "Held-out reward gain",
            passed: gain >= gates.minGain * n,
        },
        {
            id: "safety",
            label: "Incident ceiling",
            passed: proposed.incident * 10000 <= gates.maxIncidentBps * n,
        },
        {
            id: "success",
            label: "Success floor",
            passed: proposed.success * 10000 >= gates.minSuccessBps * n,
        },
        {
            id: "cost",
            label: "Mean cost ceiling",
            passed: proposed.cost <= gates.maxMeanCost * n,
        },
        {
            id: "coverage",
            label: "Selected-action memory",
            passed: candidate.every(
                (a, c) => memory[c][a].length >= gates.minSamples,
            ),
        },
        {
            id: "retention",
            label: "Original-environment retention",
            passed: retainedGain >= -gates.maxRetentionLoss * n,
        },
    ];
    const inputHash = await digest(source),
        proposal = {
            schema: "agialpha.experience.policy-proposal.v1",
            inputSha256: inputHash,
            activePolicy: baseline,
            candidatePolicy: candidate,
            state: "UNAPPROVED",
            actionIds: actions.map((a) => a.id),
            contextIds: contexts.map((c) => c.id),
        };
    const result = {
        status: checks.every((c) => c.passed)
            ? "REVIEW_REQUIRED"
            : "HOLD_BASELINE",
        inputSha256: inputHash,
        training: trace,
        memory,
        visitCounts: counts,
        evaluation,
        retention,
        gainTotal: gain,
        retentionGainTotal: retainedGain,
        gates: checks,
        proposal,
        scope: model.scope,
        jobs: [
            {
                goal: `Independently reproduce Experience ${source.id}; input SHA-256: ${inputHash}. Review the reward design, held-out and retention results before any promotion.`,
                successMetric:
                    "Recompute all traces and six gates; test a fresh, separately chosen seed and representative real environment; approve or reject with evidence. A hash is not validator approval.",
                bounty: String(BigInt(gates.bountyTokens) * 10n ** 18n),
                duration: 604800,
                priceWeight: 5000,
            },
        ],
    };
    const report = { schema: REPORT_SCHEMA, input: source, result };
    return { ...report, sha256: await digest(report) };
}
export async function verify(report) {
    keys(report, ["schema", "input", "result", "sha256"], "Run");
    const expected = await evaluate(report.input);
    if (canonical(report) !== canonical(expected))
        throw Error(
            "Run differs from recomputation; imported policies, outcomes and gates are not trusted",
        );
    return expected;
}
const literal = (value) => value.replace(/([\\`*_{}\[\]<>()#+.!|])/g, "\\$1");
export function brief(report) {
    const { input: source, result } = report;
    const lines = [
        `# ${literal(source.title)}`,
        "",
        result.status,
        "",
        literal(source.note),
        "",
        `Training: ${source.training.steps} interactions. Evaluation: ${source.training.evaluationSteps} paired episodes per suite.`,
        `Held-out total reward gain: ${result.gainTotal}. Retention total gain: ${result.retentionGainTotal}.`,
        "",
        "| Review gate | Result |",
        "|---|---|",
    ];
    for (const item of result.gates)
        lines.push(`| ${item.label} | ${item.passed ? "PASS" : "HOLD"} |`);
    lines.push(
        "",
        "Policies use zero-based action indices in scenario order. Active policy remains the baseline.",
        "Evaluation never updates learning memory. Selecting a seed after inspecting results invalidates an independent test.",
        "",
        model.scope,
        "",
        `Run SHA-256: ${report.sha256}`,
        "",
    );
    return lines.join("\n");
}
export async function artifacts(report) {
    report = await verify(report);
    const encoder = new TextEncoder(),
        files = Object.fromEntries(
            Object.entries({
                "scenario.json": canonical(report.input) + "\n",
                "run.json": canonical(report) + "\n",
                "policy-proposal.json":
                    canonical(report.result.proposal) + "\n",
                "jobs.json": canonical(report.result.jobs) + "\n",
                "review.md": brief(report),
            }).map(([name, data]) => [name, encoder.encode(data)]),
        );
    let hashes = "";
    for (const name of Object.keys(files).sort())
        hashes += `${await hashBytes(files[name])}  ${name}\n`;
    files.SHA256SUMS = encoder.encode(hashes);
    return files;
}
