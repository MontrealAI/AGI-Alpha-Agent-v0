// SPDX-License-Identifier: Apache-2.0
import model from "./constants.mjs?v=1.18.0";
export const SCHEMA = "agialpha.insight.scenario.v1";
export const REPORT_SCHEMA = "agialpha.insight.dossier.v1";
export const MAX_BYTES = 1000000;
export const METRICS = ["demand", "feasibility", "readiness", "advantage"];
export function canonical(value) {
    if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
    if (value && typeof value === "object")
        return (
            "{" +
            Object.keys(value)
                .sort()
                .map((k) => JSON.stringify(k) + ":" + canonical(value[k]))
                .join(",") +
            "}"
        );
    return JSON.stringify(value);
}
export async function digest(value) {
    return hashBytes(new TextEncoder().encode(canonical(value)));
}
export async function hashBytes(bytes) {
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(hash), (b) =>
        b.toString(16).padStart(2, "0"),
    ).join("");
}
export function parse(text) {
    if (
        typeof text !== "string" ||
        new TextEncoder().encode(text).length > MAX_BYTES
    )
        throw Error(`Input exceeds ${MAX_BYTES} bytes`);
    const result = JSON.parse(text),
        stack = [];
    const tokens =
        text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^{}\[\]:,\s]+/g) || [];
    for (const token of tokens) {
        if (token === "{" || token === "[") {
            stack.push({
                object: token === "{",
                keys: new Set(),
                expect: true,
            });
            if (stack.length > 25) throw Error("JSON nesting is too deep");
        } else if (token === "}" || token === "]") stack.pop();
        else if (token === ",") {
            if (stack.at(-1)?.object) stack.at(-1).expect = true;
        } else if (
            stack.at(-1)?.object &&
            stack.at(-1).expect &&
            token.startsWith('"')
        ) {
            const key = JSON.parse(token),
                frame = stack.at(-1);
            if (frame.keys.has(key)) throw Error(`Duplicate JSON key: ${key}`);
            frame.keys.add(key);
            frame.expect = false;
        }
    }
    function bounded(value, depth = 0) {
        if (depth > 24) throw Error("JSON nesting exceeds 24 levels");
        if (typeof value === "number" && !Number.isFinite(value))
            throw Error("Non-finite JSON numbers are not accepted");
        if (typeof value === "string" && /[\ud800-\udfff]/u.test(value))
            throw Error("Invalid Unicode");
        if (Array.isArray(value))
            for (const item of value) bounded(item, depth + 1);
        else if (value && typeof value === "object")
            for (const [key, item] of Object.entries(value)) {
                bounded(key, depth + 1);
                bounded(item, depth + 1);
            }
    }
    bounded(result);
    return result;
}
function keys(value, expected, label) {
    if (
        !value ||
        typeof value !== "object" ||
        Array.isArray(value) ||
        canonical(Object.keys(value).sort()) !== canonical([...expected].sort())
    )
        throw Error(
            `${label} must contain exactly: ${[...expected].sort().join(", ")}`,
        );
}
function integer(value, low, high, label) {
    if (!Number.isSafeInteger(value) || value < low || value > high)
        throw Error(`${label} must be an integer from ${low} through ${high}`);
}
function text(value, label, maximum = 160) {
    if (
        typeof value !== "string" ||
        !value.trim() ||
        new TextEncoder().encode(value).length > maximum
    )
        throw Error(
            `${label} must be nonempty text of at most ${maximum} UTF-8 bytes`,
        );
    if (/[\u0000-\u001f\ud800-\udfff]/u.test(value))
        throw Error(`${label} contains invalid Unicode or control characters`);
}
function identifier(value) {
    if (typeof value !== "string" || !/^[a-z][a-z0-9-]{0,39}$/.test(value))
        throw Error(
            "IDs require 1–40 lowercase letters, digits or hyphens, starting with a letter",
        );
}
export function validate(source) {
    keys(
        source,
        [
            "schema",
            "id",
            "title",
            "note",
            "weights",
            "policy",
            "sources",
            "opportunities",
        ],
        "Scenario",
    );
    if (source.schema !== SCHEMA)
        throw Error("Unsupported Insight scenario schema");
    identifier(source.id);
    text(source.title, "Title", 160);
    text(source.note, "Source note", 600);
    keys(source.weights, METRICS, "Weights");
    for (const value of Object.values(source.weights))
        integer(value, 0, 10000, "Weight");
    if (Object.values(source.weights).reduce((a, b) => a + b, 0) !== 10000)
        throw Error("Weights must sum to 10000 basis points");
    keys(
        source.policy,
        ["reviewMinutes", "minScoreBps", "minCoverageBps", "jobBountyTokens"],
        "Policy",
    );
    for (const [field, low, high] of [
        ["reviewMinutes", 0, 2400],
        ["minScoreBps", 0, 10000],
        ["minCoverageBps", 0, 10000],
        ["jobBountyTokens", 1, 1000000],
    ])
        integer(source.policy[field], low, high, field);
    if (
        !Array.isArray(source.sources) ||
        source.sources.length < 1 ||
        source.sources.length > 32
    )
        throw Error("Provide 1–32 source excerpts");
    const sourceIds = new Set();
    for (const item of source.sources) {
        keys(item, ["id", "title", "url", "excerpt", "kind"], "Source");
        identifier(item.id);
        if (sourceIds.has(item.id)) throw Error("Duplicate source id");
        sourceIds.add(item.id);
        text(item.title, "Source title", 160);
        text(item.excerpt, "Source excerpt", 1200);
        text(item.url, "Source URL", 500);
        if (
            !/^https:\/\/[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?:[/#?][^\s\\\u0085]*)?$/.test(
                item.url,
            )
        )
            throw Error(
                "Sources require HTTPS hostnames without credentials or explicit ports; URLs are never fetched",
            );
        if (!["synthetic", "public-excerpt"].includes(item.kind))
            throw Error("Source kind must be synthetic or public-excerpt");
    }
    if (
        !Array.isArray(source.opportunities) ||
        source.opportunities.length < 1 ||
        source.opportunities.length > 24
    )
        throw Error("Provide 1–24 opportunities");
    const ids = new Set();
    for (const item of source.opportunities) {
        keys(
            item,
            [
                "id",
                "sector",
                "title",
                "thesis",
                "goal",
                "successMetric",
                "reviewMinutes",
                "signals",
            ],
            "Opportunity",
        );
        identifier(item.id);
        if (ids.has(item.id)) throw Error("Duplicate opportunity id");
        ids.add(item.id);
        for (const [field, size] of [
            ["sector", 80],
            ["title", 160],
            ["thesis", 500],
            ["goal", 240],
            ["successMetric", 400],
        ])
            text(item[field], field, size);
        integer(item.reviewMinutes, 1, 2400, "Review minutes");
        keys(item.signals, METRICS, "Signals");
        for (const signal of Object.values(item.signals)) {
            keys(signal, ["low", "base", "high", "source"], "Signal");
            for (const field of ["low", "base", "high"])
                integer(signal[field], 0, 10000, "Signal " + field);
            if (!(signal.low <= signal.base && signal.base <= signal.high))
                throw Error("Each signal must satisfy low <= base <= high");
            if (
                typeof signal.source !== "string" ||
                (signal.source !== "" && !sourceIds.has(signal.source))
            )
                throw Error(
                    "Signal source must identify a supplied excerpt or be empty",
                );
        }
    }
    return JSON.parse(canonical(source));
}
const lexical = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
export async function evaluate(source) {
    source = validate(source);
    const { weights, policy } = source,
        inputHash = await digest(source);
    const rows = source.opportunities.map((item) => {
        const scores = Object.fromEntries(
            ["low", "base", "high"].map((level) => [
                level,
                METRICS.reduce(
                    (total, m) => total + weights[m] * item.signals[m][level],
                    0,
                ),
            ]),
        );
        const coverage = METRICS.filter((m) => item.signals[m].source).reduce(
                (sum, m) => sum + weights[m],
                0,
            ),
            reasons = [];
        if (coverage < policy.minCoverageBps)
            reasons.push("Missing supplied source coverage");
        if (scores.low < policy.minScoreBps * 10000)
            reasons.push("Conservative priority below threshold");
        return {
            id: item.id,
            title: item.title,
            sector: item.sector,
            scores,
            scoreDenominator: 10000,
            coverageBps: coverage,
            reviewMinutes: item.reviewMinutes,
            eligible: !reasons.length,
            reasons,
            missingSignals: METRICS.filter((m) => !item.signals[m].source),
        };
    });
    rows.sort(
        (a, b) =>
            b.scores.low - a.scores.low ||
            b.scores.base - a.scores.base ||
            lexical(a.id, b.id),
    );
    const choices = new Map([[0, { score: 0, ids: [] }]]);
    for (const row of [...rows].sort((a, b) => lexical(a.id, b.id))) {
        if (!row.eligible) continue;
        for (const [minutes, entry] of [...choices]) {
            const cost = minutes + row.reviewMinutes;
            if (cost > policy.reviewMinutes) continue;
            const candidate = {
                    score: entry.score + row.scores.low,
                    ids: [...entry.ids, row.id],
                },
                previous = choices.get(cost);
            if (
                !previous ||
                candidate.score > previous.score ||
                (candidate.score === previous.score &&
                    lexical(candidate.ids.join("\0"), previous.ids.join("\0")) <
                        0)
            )
                choices.set(cost, candidate);
        }
    }
    const [used, { score: objective, ids: selected }] = [...choices].sort(
        (a, b) =>
            b[1].score - a[1].score ||
            a[0] - b[0] ||
            lexical(a[1].ids.join("\0"), b[1].ids.join("\0")),
    )[0];
    for (const row of rows) {
        row.selected = selected.includes(row.id);
        row.status = row.selected
            ? "REVIEW_REQUIRED"
            : row.eligible
              ? "CAPACITY_DEFERRED"
              : "EVIDENCE_REQUIRED";
    }
    const jobs = [],
        drafts = [];
    for (const row of rows) {
        const item = source.opportunities.find((item) => item.id === row.id);
        const job = {
            goal: `Verify Insight ${item.id}. Input SHA-256: ${inputHash}. ${item.goal}`,
            successMetric: item.successMetric,
            bounty: String(BigInt(policy.jobBountyTokens) * 10n ** 18n),
            duration: 604800,
            priceWeight: 5000,
        };
        jobs.push(job);
        if (row.selected) {
            const body = {
                schema: "agialpha.insight.nova-seed-draft.v1",
                opportunityId: item.id,
                inputSha256: inputHash,
                foresightGenome: item,
                sources: source.sources.filter((s) =>
                    Object.values(item.signals).some((v) => v.source === s.id),
                ),
                fusionPlanJobs: [job],
                state: "UNREVIEWED_PLAINTEXT_DRAFT",
                scope: model.scope,
            };
            drafts.push({ ...body, sha256: await digest(body) });
        }
    }
    const result = {
        status: selected.length ? "REVIEW_REQUIRED" : "NO_REVIEW_PORTFOLIO",
        inputSha256: inputHash,
        ranking: rows,
        selectedIds: selected,
        reviewMinutesUsed: used,
        reviewMinutesRemaining: policy.reviewMinutes - used,
        objectiveNumerator: objective,
        objectiveDenominator: 10000,
        rankSeparation:
            rows[0].scores.low >
            Math.max(-1, ...rows.slice(1).map((row) => row.scores.high)),
        rankSeparationMeaning:
            "Top conservative score exceeds every rival optimistic score; supplied intervals are not confidence intervals.",
        jobs,
        novaSeedDrafts: drafts,
        unsubmittedBountyTokens: jobs.length * policy.jobBountyTokens,
        scope: model.scope,
    };
    const report = { schema: REPORT_SCHEMA, input: source, result };
    return { ...report, sha256: await digest(report) };
}
export async function verify(report) {
    keys(report, ["schema", "input", "result", "sha256"], "Dossier");
    const expected = await evaluate(report.input);
    if (canonical(report) !== canonical(expected))
        throw Error(
            "Dossier differs from recomputation; imported scores and selections are not trusted",
        );
    return expected;
}
const literal = (value) => value.replace(/([\\`*_{}\[\]<>()#+.!|])/g, "\\$1");
const hundredths = (value, divisor = 1) => {
    const units = Math.floor(value / divisor);
    return `${Math.floor(units / 100)}.${String(units % 100).padStart(2, "0")}`;
};
export function brief(report) {
    const { input: source, result } = report;
    const lines = [
        `# ${literal(source.title)}`,
        "",
        result.status,
        "",
        literal(source.note),
        "",
        `Review capacity: ${result.reviewMinutesUsed} / ${source.policy.reviewMinutes} minutes.`,
        "",
        "| Opportunity | Conservative priority / 100 | Supplied coverage | Decision |",
        "|---|---:|---:|---|",
    ];
    for (const row of result.ranking)
        lines.push(
            `| ${literal(row.title)} | ${hundredths(row.scores.low, 10000)} | ${hundredths(row.coverageBps)}% | ${row.status} |`,
        );
    lines.push(
        "",
        "Selection maximizes the sum of conservative priority numerators within supplied review capacity.",
        "It does not maximize profit or establish evidence quality. Ties use lower review time, then lexical IDs.",
        "",
        `Unsubmitted job bounties: ${result.unsubmittedBountyTokens} AGIALPHA.`,
        "",
        model.scope,
        "",
        `Dossier SHA-256: ${report.sha256}`,
        "",
    );
    return lines.join("\n");
}
export async function artifacts(report) {
    report = await verify(report);
    const encoder = new TextEncoder(),
        files = {};
    for (const [name, value] of Object.entries({
        "scenario.json": report.input,
        "dossier.json": report,
        "jobs.json": report.result.jobs,
        "nova-seeds.json": report.result.novaSeedDrafts,
    }))
        files[name] = encoder.encode(canonical(value) + "\n");
    files["review-brief.md"] = encoder.encode(brief(report));
    const sums = [];
    for (const name of Object.keys(files).sort())
        sums.push(`${await hashBytes(files[name])}  ${name}\n`);
    files.SHA256SUMS = encoder.encode(sums.join(""));
    return files;
}
