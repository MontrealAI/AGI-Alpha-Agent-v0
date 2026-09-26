// SPDX-License-Identifier: Apache-2.0
// Browser implementation of the replayable transfer protocol; no imported code executes.
import { canonicalJSON, hashObject } from "../ascension/crypto.mjs";
export const PROTOCOL = "agialpha.transfer.v1";
export const MANUSCRIPT_SHA256 =
    "4b290d5a8232364b8808c0af8a96e7c9b152afd7ac3f5ba05668a538e073791a";
export const POLICIES = [
    "last",
    "mean",
    "linear",
    ...Array.from({ length: 7 }, (_, i) => `seasonal-${i + 2}`),
];
const encoder = new TextEncoder();
const assert = (ok, message) => {
    if (!ok) throw new Error(message);
};
const same = (a, b) => canonical(a) === canonical(b);
const integer = (v, lo, hi) =>
    assert(
        Number.isSafeInteger(v) && v >= lo && v <= hi,
        `Expected an integer from ${lo} to ${hi}`,
    );
const fields = (v, names) =>
    assert(
        v &&
            !Array.isArray(v) &&
            typeof v === "object" &&
            same(Object.keys(v).sort(), names.split(" ").sort()),
        `Expected exactly these fields: ${names}`,
    );
const series = (v, lo, hi) => {
    assert(
        Array.isArray(v) && v.length >= lo && v.length <= hi,
        "Invalid series length",
    );
    v.forEach((x) => integer(x, -10000, 10000));
};
export function canonical(value) {
    function check(v, depth = 0) {
        assert(depth <= 20, "Document nesting exceeds 20 levels");
        if (typeof v === "string")
            assert(!/[\uD800-\uDFFF]/u.test(v), "Malformed Unicode string");
        if (typeof v === "number")
            integer(v, -Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER);
        if (v && typeof v === "object")
            Object.values(v).forEach((x) => check(x, depth + 1));
    }
    check(value);
    const result = canonicalJSON(value);
    assert(
        encoder.encode(result).length <= 1000000,
        "Document exceeds one megabyte",
    );
    return result;
}
export const digest = async (value) => {
    canonical(value);
    return hashObject(value);
};
export function parse(raw) {
    assert(
        typeof raw === "string" && encoder.encode(raw).length <= 1000000,
        "Document exceeds one megabyte",
    );
    // A small lexical pass rejects duplicate keys before the standard JSON parser.
    let pos = 0;
    const ws = () => {
        while (/\s/.test(raw[pos] || "x")) pos++;
    };
    function value(depth = 0) {
        assert(depth <= 20, "Document nesting exceeds 20 levels");
        ws();
        if (raw[pos] === "{") {
            pos++;
            ws();
            const seen = new Set();
            if (raw[pos] === "}") {
                pos++;
                return;
            }
            for (;;) {
                ws();
                const start = pos;
                string();
                const key = JSON.parse(raw.slice(start, pos));
                assert(!seen.has(key), "Duplicate JSON key");
                seen.add(key);
                ws();
                assert(raw[pos++] === ":", "Invalid JSON");
                value(depth + 1);
                ws();
                const ch = raw[pos++];
                if (ch === "}") break;
                assert(ch === ",", "Invalid JSON");
            }
        } else if (raw[pos] === "[") {
            pos++;
            ws();
            if (raw[pos] === "]") {
                pos++;
                return;
            }
            for (;;) {
                value(depth + 1);
                ws();
                const ch = raw[pos++];
                if (ch === "]") break;
                assert(ch === ",", "Invalid JSON");
            }
        } else if (raw[pos] === '"') string();
        else {
            const match = raw
                .slice(pos)
                .match(
                    /^(?:-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)/,
                );
            assert(match, "Invalid JSON");
            if (/^[-0-9]/.test(match[0]))
                assert(
                    /^-?(?:0|[1-9]\d*)$/.test(match[0]),
                    "Only integer JSON numbers are accepted",
                );
            pos += match[0].length;
        }
    }
    function string() {
        assert(raw[pos++] === '"', "Invalid JSON string");
        while (pos < raw.length) {
            const ch = raw[pos++];
            if (ch === '"') return;
            if (ch === "\\") pos++;
        }
        throw new Error("Unterminated JSON string");
    }
    value();
    ws();
    assert(pos === raw.length, "Invalid JSON");
    const result = JSON.parse(raw);
    canonical(result);
    assert(
        result && typeof result === "object" && !Array.isArray(result),
        "Expected a JSON object",
    );
    return result;
}
export const divide = (a, b) =>
    (a >= 0 ? 1 : -1) * Math.floor((Math.abs(a) * 2 + b) / (2 * b));
export function predict(policy, observed, horizon) {
    assert(
        POLICIES.includes(policy) && observed.length >= 2,
        "Unknown policy or insufficient observations",
    );
    const n = observed.length;
    if (policy.startsWith("seasonal-")) {
        const p = Number(policy.split("-")[1]);
        assert(n >= p, "The frozen policy needs a longer calibration prefix");
        return Array.from(
            { length: horizon },
            (_, h) => observed[n - p + (h % p)] * 1000,
        );
    }
    if (policy === "last") return Array(horizon).fill(observed.at(-1) * 1000);
    const sy = observed.reduce((a, b) => a + b, 0);
    if (policy === "mean") return Array(horizon).fill(divide(sy * 1000, n));
    const sx = (n * (n - 1)) / 2,
        sxx = (n * (n - 1) * (2 * n - 1)) / 6;
    const slope = n * observed.reduce((a, b, i) => a + i * b, 0) - sx * sy,
        denominator = n * sxx - sx * sx;
    return Array.from({ length: horizon }, (_, h) =>
        divide(
            (sy * denominator + slope * (n * (n + h) - sx)) * 1000,
            n * denominator,
        ),
    );
}
export function learn(observed) {
    const scores = [];
    let calls = 0;
    for (const policy of POLICIES) {
        const p = policy.startsWith("seasonal-")
            ? Number(policy.split("-")[1])
            : 1;
        if (observed.length < 2 * p + 1) continue;
        const errors = [];
        for (let i = Math.max(3, p); i < observed.length; i++)
            errors.push(
                Math.abs(
                    predict(policy, observed.slice(0, i), 1)[0] -
                        observed[i] * 1000,
                ),
            );
        if (!errors.length) continue;
        calls += errors.length;
        scores.push({
            policy,
            error_milli: divide(
                errors.reduce((a, b) => a + b, 0),
                errors.length,
            ),
            forecast_calls: errors.length,
        });
    }
    const best = scores.reduce((a, b) =>
        b.error_milli < a.error_milli ? b : a,
    );
    return { policy: best.policy, scores, forecast_calls: calls };
}
export async function freeze(training) {
    series(training, 20, 64);
    const learned = learn(training);
    const payload = {
        schema: PROTOCOL + ".capability",
        training_sha256: await digest(training),
        learner: "walk-forward-mae-v1",
        policy: learned.policy,
        scores: learned.scores,
        training_forecast_calls: learned.forecast_calls,
        contract:
            "integer-series -> milliunit-forecast; no tools, network or executable imports",
        rollback: "Discard capability and rerun B5 without the archive",
    };
    return { ...payload, sha256: await digest(payload) };
}
export function example(scenario = "seasonal", seed = 37) {
    assert(
        ["seasonal", "shift", "ablation"].includes(scenario),
        "Unknown scenario",
    );
    integer(seed, 1, 9999);
    const pattern = [6, 21, -8, 32, -17];
    const training = Array.from(
        { length: 40 },
        (_, i) => 80 + pattern[i % 5] * 2,
    );
    const tasks = Array.from({ length: 4 }, (_, index) => {
        const phase = (seed + index) % 5;
        let values = Array.from(
            { length: 14 },
            (_, i) =>
                120 +
                (seed % 17) +
                index * 11 +
                pattern[(i + phase) % 5] * (index + 1),
        );
        if (scenario === "shift")
            values = Array.from(
                { length: 14 },
                (_, i) => 80 + index * 11 + i * (index + 3),
            );
        return {
            id: `future-${seed}-${index + 1}`,
            observed: values.slice(0, 6),
            heldout: values.slice(6),
        };
    });
    return {
        schema: PROTOCOL + ".spec",
        scenario,
        seed,
        training,
        tasks,
        archive_enabled: scenario !== "ablation",
        call_cost_milli: 20,
        human_cost_milli_per_second: 10,
        coordination_cost_milli: 1000,
        risk_limit_milli: 100000,
    };
}
export async function validateSpec(spec) {
    fields(
        spec,
        "schema scenario seed training tasks archive_enabled call_cost_milli human_cost_milli_per_second coordination_cost_milli risk_limit_milli",
    );
    canonical(spec);
    assert(
        spec.schema === PROTOCOL + ".spec" &&
            ["seasonal", "shift", "ablation", "custom"].includes(spec.scenario),
        "Invalid experiment schema or scenario",
    );
    integer(spec.seed, 1, 9999);
    series(spec.training, 20, 64);
    assert(
        typeof spec.archive_enabled === "boolean",
        "archive_enabled must be boolean",
    );
    for (const key of [
        "call_cost_milli",
        "human_cost_milli_per_second",
        "coordination_cost_milli",
        "risk_limit_milli",
    ])
        integer(spec[key], 0, 10000000);
    assert(
        Array.isArray(spec.tasks) &&
            spec.tasks.length >= 2 &&
            spec.tasks.length <= 8,
        "Provide two to eight future tasks",
    );
    const ids = new Set(),
        commitments = new Set([await digest(spec.training)]);
    for (const task of spec.tasks) {
        fields(task, "id observed heldout");
        assert(
            typeof task.id === "string" &&
                /^[\x00-\x7F]{1,64}$/.test(task.id) &&
                !ids.has(task.id),
            "Task identifiers must be unique short ASCII strings",
        );
        ids.add(task.id);
        series(task.observed, 6, 16);
        series(task.heldout, 4, 16);
        const c = await digest([...task.observed, ...task.heldout]);
        assert(
            !commitments.has(c),
            "Training and future tasks must have distinct content",
        );
        commitments.add(c);
    }
}
export async function compute(spec) {
    await validateSpec(spec);
    const capability = await freeze(spec.training),
        arms = {};
    for (const arm of ["B0", "B3", "B5", "B6"]) {
        const tasks = [];
        let calls =
            arm === "B6" && spec.archive_enabled
                ? capability.training_forecast_calls
                : 0;
        for (const task of spec.tasks) {
            let policy;
            if (arm === "B0") policy = "last";
            else if (arm === "B3") policy = "linear";
            else if (arm === "B6" && spec.archive_enabled)
                policy = capability.policy;
            else {
                const local = learn(task.observed);
                calls += local.forecast_calls;
                policy = local.policy;
            }
            const forecast = predict(
                policy,
                task.observed,
                task.heldout.length,
            );
            calls++;
            const errors = task.heldout.map((a, i) =>
                Math.abs(a * 1000 - forecast[i]),
            );
            tasks.push({
                task_id: task.id,
                policy,
                predictions_milli: forecast,
                actual_milli: task.heldout.map((x) => x * 1000),
                absolute_errors_milli: errors,
                error_milli: errors.reduce((a, b) => a + b, 0),
                max_error_milli: Math.max(...errors),
            });
        }
        arms[arm] = {
            tasks,
            error_milli: tasks.reduce((a, b) => a + b.error_milli, 0),
            forecast_calls: calls,
            max_error_milli: Math.max(...tasks.map((x) => x.max_error_milli)),
        };
    }
    const control = arms.B5,
        treatment = arms.B6,
        gain = control.error_milli - treatment.error_milli,
        extra = treatment.forecast_calls - control.forecast_calls;
    const computeCalls =
        Object.values(arms).reduce((n, arm) => n + arm.forecast_calls, 0) +
        (spec.archive_enabled ? 0 : capability.training_forecast_calls);
    const cost =
        (extra + computeCalls) * spec.call_cost_milli +
        spec.coordination_cost_milli;
    return {
        spec_sha256: await digest(spec),
        capability,
        arms,
        execution_accounting: {
            forecast_calls_per_compute: computeCalls,
            creation_compute_passes: 2,
        },
        metrics: {
            raw_gain_milli: gain,
            additional_forecast_calls: extra,
            validator_forecast_calls: computeCalls,
            modeled_overhead_milli: cost,
            advantage_before_human_milli: gain - cost,
            risk_passed: treatment.max_error_milli <= spec.risk_limit_milli,
            task_wins: treatment.tasks.filter(
                (t, i) => t.error_milli < control.tasks[i].error_milli,
            ).length,
        },
        baseline_profile:
            "manuscript-rsi-p60; B6 is this experiment's treatment",
        unmeasured_baselines: [
            "B1 incumbent",
            "B2 adjacent domain",
            "B4 strongest single agent",
        ],
        evidence_contact: {
            level: "E2",
            meaning: "executed bounded local computation",
            E3: "pending independent replay",
            E4: "pending independent replay and stress",
            E5: "pending external validation or outcomes",
        },
    };
}
export async function run(spec) {
    const start = performance.now(),
        core = await compute(spec);
    assert(same(await compute(spec), core), "Initial validator replay differs");
    const payload = {
        schema: PROTOCOL + ".run",
        spec: parse(canonical(spec)),
        core,
        observations: {
            wall_ms: Math.max(1, Math.floor(performance.now() - start)),
            source: "local-monotonic-clock",
            energy_wh: null,
            creation_forecast_calls:
                2 * core.execution_accounting.forecast_calls_per_compute,
        },
    };
    return { ...payload, sha256: await digest(payload), review: null };
}
export function decision(report) {
    const r = report.review,
        human = r
            ? divide(
                  (r.treatment_ms - r.control_ms) *
                      report.spec.human_cost_milli_per_second,
                  1000,
              )
            : null;
    const adjusted =
        human === null
            ? null
            : report.core.metrics.advantage_before_human_milli - human;
    const accepted = !!(
        r &&
        r.decision === "accept" &&
        adjusted > 0 &&
        report.core.metrics.raw_gain_milli > 0 &&
        report.core.metrics.risk_passed &&
        report.spec.archive_enabled
    );
    return {
        replay: "verified",
        human_overhead_milli: human,
        adjusted_advantage_milli: adjusted,
        bounded_transfer: accepted ? "accepted" : "hold",
        manuscript_promotion: "hold",
        missing: [
            "B1/B2/B4 comparisons",
            "independent validation",
            "measured multi-agent scaling",
            "delayed real-world outcomes",
            "calibrated alpha-WU",
        ],
        scope: "Disclosed synthetic forecasting tasks; not external economic alpha or general intelligence",
    };
}
export async function verify(report) {
    fields(report, "schema spec core observations sha256 review");
    canonical(report);
    assert(
        report.schema === PROTOCOL + ".run" &&
            same(await compute(report.spec), report.core),
        "Computed results or capability differ from replay",
    );
    fields(
        report.observations,
        "wall_ms source energy_wh creation_forecast_calls",
    );
    assert(
        report.observations.creation_forecast_calls ===
            2 * report.core.execution_accounting.forecast_calls_per_compute,
        "Creation work count differs from replay",
    );
    integer(report.observations.wall_ms, 1, 86400000);
    assert(
        report.observations.source === "local-monotonic-clock" &&
            report.observations.energy_wh === null,
        "Invalid timing observations",
    );
    const { sha256, review, ...payload } = report;
    assert((await digest(payload)) === sha256, "Run digest mismatch");
    if (review !== null) {
        fields(
            review,
            "run_sha256 decision reviewer reason control_ms treatment_ms timing_source",
        );
        assert(
            review.run_sha256 === sha256 &&
                ["accept", "reject", "repair"].includes(review.decision),
            "Stale or invalid review",
        );
        for (const key of ["reviewer", "reason"])
            assert(
                typeof review[key] === "string" &&
                    review[key].trim().length > 0 &&
                    review[key].length <= 500,
                "Review needs a bounded identity and reason",
            );
        for (const key of ["control_ms", "treatment_ms"])
            integer(review[key], 1, 86400000);
        assert(
            ["operator-reported", "browser-elapsed"].includes(
                review.timing_source,
            ),
            "Unsupported review timing provenance",
        );
    }
    return decision(report);
}
export async function reviewRun(
    report,
    verdict,
    reviewer,
    reason,
    control_ms,
    treatment_ms,
    timing_source = "operator-reported",
) {
    await verify(report);
    const result = parse(canonical(report));
    result.review = {
        run_sha256: report.sha256,
        decision: verdict,
        reviewer,
        reason,
        control_ms,
        treatment_ms,
        timing_source,
    };
    await verify(result);
    return result;
}
export async function docketFiles(report) {
    const outcome = await verify(report),
        core = report.core,
        spec = report.spec;
    const render = (value) =>
        JSON.stringify(JSON.parse(canonical(value)), null, 2) + "\n";
    const files = {
        "00_manifest.md": `# Evidence Docket\n\nProtocol: ${PROTOCOL}\n\nRun: ${report.sha256}\n\nManuscript SHA-256: ${MANUSCRIPT_SHA256}\n\nLocal replay verifies computation, not independence.\n`,
        "01_claims_matrix.md": `# Claims\n\n| Claim | Status |\n|---|---|\n| Bounded future-task transfer | ${outcome.bounded_transfer} |\n| General RSI, economic alpha, external validation | Unproven |\n| Manuscript promotion | HOLD: missing comparators, scaling and external evidence |\n`,
        "02_environment.md":
            "# Environment\n\nPython 3.11–3.13 or modern browser/Node 22; integer arithmetic.\nNo network, LLM, tools or settlement used by the experiment. Public synthetic fixtures; not blinded. Wall time is an observation, not independently attested.\n",
        "03_benchmark_tasks/spec.json": render(spec),
        "04_baselines/comparison.json": render({
            profile: core.baseline_profile,
            arms: core.arms,
            not_measured: core.unmeasured_baselines,
        }),
        "05_agialpha_runs/run.json": render(report),
        "06_proof_bundles/capability.json": render(core.capability),
        "07_replay_logs/replay.json": render({
            spec_sha256: core.spec_sha256,
            core_sha256: await digest(core),
            method: "recompute all predictions",
            independent: false,
        }),
        "08_cost_ledgers/costs.json": render({
            metrics: core.metrics,
            observations: report.observations,
            human_review: report.review,
            assumed_rates: Object.fromEntries(
                [
                    "call_cost_milli",
                    "human_cost_milli_per_second",
                    "coordination_cost_milli",
                ].map((k) => [k, spec[k]]),
            ),
            unit: "modeled milliunits, not currency",
            tokens: 0,
            tool_calls: 0,
            training_cost:
                "all A selection calls charged to B6; no amortization",
            unmeasured: [
                "energy",
                "monetary compute cost",
                "active human attention",
            ],
            execution_accounting: core.execution_accounting,
            replay_and_baseline_work:
                "creation includes all baselines and one charged full replay; later UI preparation, exports and replays are outside this timing",
        }),
        "09_safety_ledgers/safety.json": render({
            risk_limit_milli: spec.risk_limit_milli,
            risk_passed: core.metrics.risk_passed,
            network: false,
            execution: "fixed arithmetic only",
            real_world_risk: "not measured",
            rollback: core.capability.rollback,
        }),
        "10_validator_reports/review.json": render({
            review: report.review,
            independent: false,
            evidence_contact: core.evidence_contact,
        }),
        "11_alpha_wu_calibration/status.json": render({
            status: "uncalibrated",
            alpha_WU: null,
            reason: "No external reference workload or verifier",
        }),
        "12_summary_tables/outcome.json": render(outcome),
        "05_agialpha_runs/action_reason_trace.json": render([
            {
                action: "freeze",
                reason: "Prevent future answers entering policy selection",
                evidence: core.capability.sha256,
            },
            {
                action: "compare",
                reason: "Measure future tasks against disclosed baselines",
                evidence: core.spec_sha256,
            },
            {
                action: "gate",
                reason: "Require accepted review, positive adjusted gain and bounded forecast error",
                evidence: outcome,
            },
        ]),
    };
    const sums = {};
    for (const [name, content] of Object.entries(files)) {
        const hash = await crypto.subtle.digest(
            "SHA-256",
            encoder.encode(content),
        );
        sums[name] = Array.from(new Uint8Array(hash), (x) =>
            x.toString(16).padStart(2, "0"),
        ).join("");
    }
    files["checksums.json"] = render(sums);
    return files;
}
export function zipFiles(files) {
    // Standards-compliant stored ZIP, fixed ASCII names and UTF-8 contents, no dependencies.
    const parts = [],
        central = [];
    let offset = 0;
    const crc32 = (data) => {
        let crc = 0xffffffff;
        for (const b of data) {
            crc ^= b;
            for (let j = 0; j < 8; j++)
                crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
        }
        return (crc ^ 0xffffffff) >>> 0;
    };
    for (const name of Object.keys(files).sort()) {
        const filename = encoder.encode(name),
            data = encoder.encode(files[name]),
            crc = crc32(data);
        const local = new Uint8Array(30 + filename.length),
            v = new DataView(local.buffer);
        v.setUint32(0, 0x04034b50, true);
        v.setUint16(4, 20, true);
        v.setUint16(6, 0x800, true);
        v.setUint32(14, crc, true);
        v.setUint32(18, data.length, true);
        v.setUint32(22, data.length, true);
        v.setUint16(26, filename.length, true);
        local.set(filename, 30);
        parts.push(local, data);
        const entry = new Uint8Array(46 + filename.length),
            c = new DataView(entry.buffer);
        c.setUint32(0, 0x02014b50, true);
        c.setUint16(4, 20, true);
        c.setUint16(6, 20, true);
        c.setUint16(8, 0x800, true);
        c.setUint32(16, crc, true);
        c.setUint32(20, data.length, true);
        c.setUint32(24, data.length, true);
        c.setUint16(28, filename.length, true);
        c.setUint32(42, offset, true);
        entry.set(filename, 46);
        central.push(entry);
        offset += local.length + data.length;
    }
    const size = central.reduce((a, b) => a + b.length, 0),
        end = new Uint8Array(22),
        e = new DataView(end.buffer);
    e.setUint32(0, 0x06054b50, true);
    e.setUint16(8, central.length, true);
    e.setUint16(10, central.length, true);
    e.setUint32(12, size, true);
    e.setUint32(16, offset, true);
    const output = new Uint8Array(offset + size + 22);
    let pos = 0;
    for (const part of [...parts, ...central, end]) {
        output.set(part, pos);
        pos += part.length;
    }
    return output;
}
export const exportDocket = async (report) =>
    zipFiles(await docketFiles(report));
