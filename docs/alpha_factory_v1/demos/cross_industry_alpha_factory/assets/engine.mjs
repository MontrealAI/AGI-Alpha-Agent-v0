/* SPDX-License-Identifier: Apache-2.0 */
const metrics = ["benefit", "confidence", "effort", "risk"];
function exact(v, keys, name) {
    if (
        !v ||
        typeof v !== "object" ||
        Array.isArray(v) ||
        Object.keys(v).sort().join("|") !== [...keys].sort().join("|")
    )
        throw Error(`${name}: missing or unknown fields`);
}
function integer(v, name) {
    if (!Number.isSafeInteger(v) || v < 0 || v > 100)
        throw Error(`${name}: integer 0–100 required`);
}
function text(v, max, name) {
    if (
        typeof v !== "string" ||
        !v ||
        v !==
            v.replace(
                /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+$/g,
                ""
            ) ||
        [...v].length > max ||
        /[\u0000-\u001f\u007f-\u009f]/.test(v)
    )
        throw Error(`${name}: invalid text`);
    for (const c of v) {
        const n = c.codePointAt(0);
        if (n >= 0xd800 && n <= 0xdfff) throw Error(`${name}: invalid Unicode`);
    }
}
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
export function roundRatio(n, d) {
    return Math.floor((2 * n * 1000000 + d) / (2 * d)) / 1000000;
}
export function validate(input) {
    exact(
        input,
        ["schema_version", "weights", "constraints", "opportunities"],
        "input"
    );
    if (input.schema_version !== "cross-industry-input-v1")
        throw Error("Unsupported schema");
    exact(input.weights, metrics, "weights");
    for (const m of metrics) integer(input.weights[m], "weight " + m);
    if (metrics.reduce((n, m) => n + input.weights[m], 0) === 0)
        throw Error("At least one weight must be positive");
    exact(input.constraints, ["max_risk", "min_confidence"], "constraints");
    for (const k of ["max_risk", "min_confidence"])
        integer(input.constraints[k], k);
    if (
        !Array.isArray(input.opportunities) ||
        input.opportunities.length < 1 ||
        input.opportunities.length > 100
    )
        throw Error("Supply 1–100 opportunities");
    const ids = new Set();
    for (const o of input.opportunities) {
        exact(
            o,
            ["id", "sector", "opportunity", ...metrics, "evidence"],
            "opportunity"
        );
        if (
            typeof o.id !== "string" ||
            !/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(o.id) ||
            ids.has(o.id)
        )
            throw Error("Unique ASCII identifiers required");
        ids.add(o.id);
        text(o.sector, 120, "sector");
        text(o.opportunity, 500, "opportunity");
        for (const m of metrics) integer(o[m], m);
        if (
            !Array.isArray(o.evidence) ||
            o.evidence.length < 1 ||
            o.evidence.length > 10
        )
            throw Error("Supply 1–10 evidence notes");
        for (const e of o.evidence) text(e, 500, "evidence");
    }
    return input;
}
export function rank(input) {
    validate(input);
    const denominator = metrics.reduce((n, m) => n + input.weights[m], 0),
        rows = input.opportunities.map((o) => {
            const values = {
                    benefit: o.benefit,
                    confidence: o.confidence,
                    effort: 100 - o.effort,
                    risk: 100 - o.risk,
                },
                contributions = Object.fromEntries(
                    metrics.map((m) => [
                        m,
                        roundRatio(input.weights[m] * values[m], denominator),
                    ])
                ),
                reasons = [];
            if (o.risk > input.constraints.max_risk)
                reasons.push("risk exceeds max_risk");
            if (o.confidence < input.constraints.min_confidence)
                reasons.push("confidence below min_confidence");
            return {
                ...o,
                evidence: [...o.evidence],
                score: roundRatio(
                    metrics.reduce(
                        (n, m) => n + input.weights[m] * values[m],
                        0
                    ),
                    denominator
                ),
                contributions,
                eligible: reasons.length === 0,
                exclusion_reasons: reasons,
                rank: null,
                pareto_optimal: false,
            };
        });
    const eligible = rows.filter((r) => r.eligible);
    for (const o of eligible)
        o.pareto_optimal = !eligible.some(
            (p) =>
                p !== o &&
                p.benefit >= o.benefit &&
                p.confidence >= o.confidence &&
                p.effort <= o.effort &&
                p.risk <= o.risk &&
                (p.benefit > o.benefit ||
                    p.confidence > o.confidence ||
                    p.effort < o.effort ||
                    p.risk < o.risk)
        );
    rows.sort((a, b) =>
        a.eligible !== b.eligible
            ? a.eligible
                ? -1
                : 1
            : a.eligible && a.score !== b.score
            ? b.score - a.score
            : a.id < b.id
            ? -1
            : a.id > b.id
            ? 1
            : 0
    );
    let i = 0;
    for (const r of rows) if (r.eligible) r.rank = ++i;
    return {
        normalized_weights: Object.fromEntries(
            metrics.map((m) => [m, roundRatio(input.weights[m], denominator)])
        ),
        constraints: { ...input.constraints },
        ranking: rows,
        selected_id: rows.find((r) => r.eligible)?.id ?? null,
    };
}

export async function compare(input) {
    const result = rank(input);
    if (!crypto.subtle) throw Error("Web Crypto required");
    const input_sha256 = [
        ...new Uint8Array(
            await crypto.subtle.digest(
                "SHA-256",
                new TextEncoder().encode(canonical(input))
            )
        ),
    ]
        .map((n) => n.toString(16).padStart(2, "0"))
        .join("");
    return {
        schema_version: "cross-industry-report-v1",
        mode: "supplied-input",
        input_sha256,
        ...result,
        limitations: [
            "Ratings and evidence are supplied assessments, not independently verified facts.",
            "Scores compare priorities only; they do not estimate revenue, returns or probability of success.",
            "No provider, market data, evidence URL or external service is contacted. Human review is required.",
        ],
    };
}
