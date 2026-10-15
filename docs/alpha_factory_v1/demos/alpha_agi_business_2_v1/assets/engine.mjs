/* SPDX-License-Identifier: Apache-2.0 */
const strip = (v) =>
    v.replace(
        /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g,
        ""
    );
function codepointOrder(a, b) {
    const aa = [...a],
        bb = [...b];
    for (let i = 0; i < Math.min(aa.length, bb.length); i++) {
        const d = aa[i].codePointAt(0) - bb[i].codePointAt(0);
        if (d) return d;
    }
    return aa.length - bb.length;
}
function exact(v, keys) {
    if (
        !v ||
        typeof v !== "object" ||
        Array.isArray(v) ||
        Object.keys(v).sort().join("|") !== keys.split(" ").sort().join("|")
    )
        throw Error("Missing or unknown fields");
}
function integer(v, min, max) {
    if (!Number.isSafeInteger(v) || v < min || v > max)
        throw Error(`Integer ${min}–${max} required`);
}
function text(v, max = 200) {
    if (
        typeof v !== "string" ||
        !strip(v) ||
        [...v].length > max ||
        /[\u0000-\u001f\u007f-\u009f]/.test(v)
    )
        throw Error("Invalid text");
    for (const c of v) {
        const n = c.codePointAt(0);
        if (n >= 0xd800 && n <= 0xdfff) throw Error("Invalid Unicode");
    }
}
function id(v) {
    if (typeof v !== "string" || !/^[a-z][a-z0-9-]{0,39}$/.test(v))
        throw Error("IDs need 1–40 lowercase letters, digits or hyphens");
}
export function validate(s) {
    exact(s, "schema id provenance policy observations opportunities");
    if (s.schema !== "agialpha.business2.input.v1")
        throw Error("Unsupported schema");
    id(s.id);
    exact(s.provenance, "kind note");
    if (!["constructed", "supplied"].includes(s.provenance.kind))
        throw Error("Invalid provenance");
    text(s.provenance.note, 500);
    exact(s.policy, "effortHours maxProjects minSupportingSources");
    integer(s.policy.effortHours, 0, 100000);
    integer(s.policy.maxProjects, 0, 16);
    integer(s.policy.minSupportingSources, 1, 64);
    for (const [collection, max] of [
        ["observations", 64],
        ["opportunities", 16],
    ]) {
        const rows = s[collection];
        if (!Array.isArray(rows) || rows.length < 1 || rows.length > max)
            throw Error(`Invalid ${collection} count`);
        const ids = new Set();
        for (const r of rows) {
            if (collection === "observations") {
                exact(r, "id source metric unit baseline current direction");
                for (const k of ["source", "metric", "unit"]) text(r[k]);
                integer(r.baseline, 0, 1000000000);
                integer(r.current, 0, 1000000000);
                if (!["increase", "decrease"].includes(r.direction))
                    throw Error("Invalid direction");
            } else {
                exact(r, "id title effortHours valuePoints evidenceIds");
                text(r.title);
                integer(r.effortHours, 1, 100000);
                integer(r.valuePoints, 0, 1000000);
                if (
                    !Array.isArray(r.evidenceIds) ||
                    r.evidenceIds.length < 1 ||
                    r.evidenceIds.length > 64
                )
                    throw Error("Invalid evidence count");
                r.evidenceIds.forEach(id);
                if (new Set(r.evidenceIds).size !== r.evidenceIds.length)
                    throw Error("Duplicate evidence");
            }
            id(r.id);
            if (ids.has(r.id)) throw Error("Duplicate ID");
            ids.add(r.id);
        }
    }
    const known = new Set(s.observations.map((r) => r.id));
    for (const r of s.opportunities)
        if (r.evidenceIds.some((i) => !known.has(i)))
            throw Error("Unknown evidence ID");
    return s;
}
export function canonical(v) {
    if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
    if (v && typeof v === "object")
        return (
            "{" +
            Object.keys(v)
                .sort(codepointOrder)
                .map((k) => JSON.stringify(k) + ":" + canonical(v[k]))
                .join(",") +
            "}"
        );
    return JSON.stringify(v);
}
export async function digest(v) {
    const bytes = new TextEncoder().encode(canonical(v));
    return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))]
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
}
const scope =
    "Supplied observations and value-point assumptions only; sources are labels, not independently verified research. No live data, model inference, revenue forecast, execution or payment. Positive change is not causation.";
function tupleLess(a, b) {
    for (let i = 0; i < Math.min(a.length, b.length); i++) {
        if (a[i] !== b[i]) return a[i] < b[i];
    }
    return a.length < b.length;
}
export async function evaluate(source) {
    const s = structuredClone(validate(source));
    const observations = [...s.observations]
        .sort((a, b) => codepointOrder(a.id, b.id))
        .map((r) => ({
            ...r,
            delta: r.current - r.baseline,
            supports:
                r.direction === "increase"
                    ? r.current > r.baseline
                    : r.current < r.baseline,
        }));
    const byId = new Map(observations.map((r) => [r.id, r]));
    const reviewed = [...s.opportunities]
        .sort((a, b) => codepointOrder(a.id, b.id))
        .map((r) => {
            const supportingSources = [
                ...new Set(
                    r.evidenceIds
                        .filter((i) => byId.get(i).supports)
                        .map((i) => strip(byId.get(i).source))
                ),
            ].sort(codepointOrder);
            return {
                ...r,
                supportingSources,
                eligible:
                    supportingSources.length >= s.policy.minSupportingSources,
            };
        });
    const eligible = reviewed.filter((r) => r.eligible);
    let best = { score: 0, hours: 0, ids: [] };
    for (let mask = 0; mask < 1 << eligible.length; mask++) {
        let hours = 0,
            score = 0;
        const ids = [];
        for (let i = 0; i < eligible.length; i++)
            if (mask & (1 << i)) {
                hours += eligible[i].effortHours;
                score += eligible[i].valuePoints;
                ids.push(eligible[i].id);
            }
        if (hours > s.policy.effortHours || ids.length > s.policy.maxProjects)
            continue;
        if (
            score > best.score ||
            (score === best.score &&
                (hours < best.hours ||
                    (hours === best.hours && tupleLess(ids, best.ids))))
        )
            best = { score, hours, ids };
    }
    for (const r of reviewed) {
        r.selected = best.ids.includes(r.id);
        r.reason = r.selected
            ? "selected"
            : !r.eligible
            ? "insufficient_support"
            : "portfolio_tradeoff";
    }
    const report = {
        schema: "agialpha.business2.report.v1",
        inputDigest: await digest(s),
        id: s.id,
        provenance: s.provenance,
        scope,
        research: { observations, opportunities: reviewed },
        plan: {
            selectedIds: best.ids,
            totalValuePoints: best.score,
            totalEffortHours: best.hours,
            remainingEffortHours: s.policy.effortHours - best.hours,
            policy: s.policy,
            subsetsEvaluated: 1 << eligible.length,
            objective:
                "maximize supplied valuePoints; ties: minimum effortHours, then lexicographic IDs",
        },
    };
    return { ...report, reportDigest: await digest(report) };
}
