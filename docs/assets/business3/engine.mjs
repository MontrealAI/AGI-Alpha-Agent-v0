// SPDX-License-Identifier: Apache-2.0
// Integer-only browser counterpart of business_3_v1/enterprise.py; parity is a release gate.
export const SCHEMA = "agialpha.business3.scenario.v1";
export const REPORT_SCHEMA = "agialpha.business3.dossier.v1";
export const SECTORS = [
    "finance",
    "biotech",
    "materials",
    "policy",
    "energy",
    "manufacturing",
    "logistics",
    "research",
    "quantum",
];
const POLICY_BOUNDS = {
    budgetUsd: [0, 1e9],
    staffDays: [0, 100000],
    reviewMinutes: [0, 100000],
    jobBudgetTokens: [0, 1e7],
    maxProjects: [0, 16],
    maxPerSector: [1, 16],
    discountBps: [0, 10000],
    benefitHaircutBps: [0, 10000],
    costOverrunBps: [0, 10000],
    minEvidenceBps: [0, 10000],
    minDownsideNpvUsd: [-1e9, 1e9],
};
const PROJECT_BOUNDS = {
    costUsd: [1, 1e8],
    staffDays: [1, 100000],
    reviewMinutes: [1, 100000],
    bountyTokens: [1, 1e6],
    durationDays: [1, 90],
    evidenceBps: [0, 10000],
};
export const SCOPE =
    "Deterministic planning over supplied assumptions, not investment execution or a prediction guarantee. All jobs are unsubmitted; evidence needs independent review. No wallet, mint, trade or payment is performed. USD project capital and AGIALPHA job bounties are separate budgets without an assumed exchange rate.";

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
    const hash = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(canonical(value)),
    );
    return Array.from(new Uint8Array(hash), (b) =>
        b.toString(16).padStart(2, "0"),
    ).join("");
}
export function parse(text, limit = 256000) {
    if (
        typeof text !== "string" ||
        new TextEncoder().encode(text).length > limit
    )
        throw Error(`Input exceeds ${limit} bytes`);
    const result = JSON.parse(text);
    const tokens =
        text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^{}\[\]:,\s]+/g) || [];
    const stack = [];
    for (const token of tokens) {
        if (token === "{" || token === "[") {
            stack.push({
                object: token === "{",
                keys: new Set(),
                expect: true,
            });
            if (stack.length > 32) throw Error("JSON nesting is too deep");
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
    return result;
}
function keys(value, expected, label) {
    if (
        !value ||
        Array.isArray(value) ||
        typeof value !== "object" ||
        canonical(Object.keys(value).sort()) !== canonical([...expected].sort())
    )
        throw Error(`${label} has missing or unknown fields`);
}
function text(value, label, max = 160) {
    if (
        typeof value !== "string" ||
        !value.trim() ||
        [...value].length > max ||
        /[\u0000-\u001f]/.test(value) ||
        [...value].some(
            (c) =>
                c.length === 1 &&
                c.charCodeAt(0) >= 0xd800 &&
                c.charCodeAt(0) <= 0xdfff,
        )
    )
        throw Error(
            `${label} must be nonempty valid text of at most ${max} characters`,
        );
}
function integer(value, low, high, label) {
    if (!Number.isSafeInteger(value) || value < low || value > high)
        throw Error(`${label} must be an integer from ${low} through ${high}`);
}
export function validate(raw) {
    keys(
        raw,
        ["schema", "id", "title", "provenance", "policy", "projects"],
        "Scenario",
    );
    if (raw.schema !== SCHEMA)
        throw Error("Unsupported Business 3 scenario schema");
    text(raw.id, "Scenario id", 60);
    text(raw.title, "Title");
    keys(raw.provenance, ["kind", "note"], "Provenance");
    if (!["constructed", "supplied"].includes(raw.provenance.kind))
        throw Error("Provenance must be constructed or supplied");
    text(raw.provenance.note, "Provenance note", 500);
    keys(raw.policy, Object.keys(POLICY_BOUNDS), "Policy");
    for (const [key, [low, high]] of Object.entries(POLICY_BOUNDS))
        integer(raw.policy[key], low, high, key);
    if (
        !Array.isArray(raw.projects) ||
        raw.projects.length < 1 ||
        raw.projects.length > 16
    )
        throw Error("A scenario requires 1–16 projects");
    const ids = new Set();
    for (const p of raw.projects) {
        keys(
            p,
            [
                ...Object.keys(PROJECT_BOUNDS),
                "id",
                "name",
                "sector",
                "cashflowsUsd",
                "sources",
                "requires",
                "excludes",
                "metric",
            ],
            "Project",
        );
        if (
            typeof p.id !== "string" ||
            !/^[a-z][a-z0-9-]{0,39}$/.test(p.id) ||
            ids.has(p.id)
        )
            throw Error(
                "Project ids must be unique lowercase identifiers of 1–40 characters",
            );
        ids.add(p.id);
        text(p.name, "Project name", 100);
        text(p.metric, "Success metric", 240);
        if (new TextEncoder().encode(p.metric).length > 400)
            throw Error("Success metric must fit 400 UTF-8 bytes");
        if (!SECTORS.includes(p.sector)) throw Error("Unknown sector");
        for (const [key, [low, high]] of Object.entries(PROJECT_BOUNDS))
            integer(p[key], low, high, `${p.id}.${key}`);
        if (!Array.isArray(p.cashflowsUsd) || p.cashflowsUsd.length !== 3)
            throw Error(
                "Provide three annual net operating cash flows in whole USD",
            );
        for (const cash of p.cashflowsUsd)
            integer(cash, -1e8, 1e8, "Annual cash flow");
        if (
            !Array.isArray(p.sources) ||
            p.sources.length < 1 ||
            p.sources.length > 8
        )
            throw Error("Every project needs 1–8 source descriptions");
        for (const note of p.sources) text(note, "Source description", 300);
        for (const key of ["requires", "excludes"])
            if (
                !Array.isArray(p[key]) ||
                p[key].some((v) => typeof v !== "string") ||
                new Set(p[key]).size !== p[key].length ||
                p[key].includes(p.id)
            )
                throw Error(`${key} must contain distinct other project ids`);
    }
    for (const p of raw.projects) {
        if ([...p.requires, ...p.excludes].some((id) => !ids.has(id)))
            throw Error(`Unknown dependency or exclusion in ${p.id}`);
        if (p.requires.some((id) => p.excludes.includes(id)))
            throw Error(
                "A project cannot require and exclude the same project",
            );
    }
    const visiting = new Set(),
        visited = new Set(),
        byId = new Map(raw.projects.map((p) => [p.id, p]));
    function visit(id) {
        if (visiting.has(id))
            throw Error("Project dependencies must be acyclic");
        if (visited.has(id)) return;
        visiting.add(id);
        byId.get(id).requires.forEach(visit);
        visiting.delete(id);
        visited.add(id);
    }
    byId.forEach((_, id) => visit(id));
    const source = parse(canonical(raw));
    source.projects.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    for (const p of source.projects) {
        p.requires.sort();
        p.excludes.sort();
    }
    return source;
}
function floorDivide(a, b) {
    return a >= 0n ? a / b : -((-a + b - 1n) / b);
}
export function economics(p, policy) {
    const rate = BigInt(10000 + policy.discountBps);
    let expected = 0n,
        downside = 0n;
    p.cashflowsUsd.forEach((cash, index) => {
        const year = BigInt(index + 1),
            value = BigInt(cash);
        expected += floorDivide(value * 10000n ** year, rate ** year);
        const shock = BigInt(
            cash >= 0
                ? 10000 - policy.benefitHaircutBps
                : 10000 + policy.benefitHaircutBps,
        );
        downside += floorDivide(
            floorDivide(value * shock, 10000n) * 10000n ** year,
            rate ** year,
        );
    });
    const stressedCost =
        (BigInt(p.costUsd) * BigInt(10000 + policy.costOverrunBps) + 9999n) /
        10000n;
    return {
        expectedNpvUsd: Number(expected) - p.costUsd,
        downsideNpvUsd: Number(downside - stressedCost),
        stressedCostUsd: Number(stressedCost),
    };
}
function portfolio(indices, projects, rows) {
    const value = { projectIds: indices.map((i) => projects[i].id) };
    for (const k of ["costUsd", "staffDays", "reviewMinutes", "bountyTokens"])
        value[k] = indices.reduce((sum, i) => sum + projects[i][k], 0);
    for (const k of ["expectedNpvUsd", "downsideNpvUsd", "stressedCostUsd"])
        value[k] = indices.reduce((sum, i) => sum + rows[i][k], 0);
    return value;
}
function fits(value, source) {
    const policy = source.policy,
        ids = new Set(value.projectIds),
        selected = source.projects.filter((p) => ids.has(p.id));
    return (
        ids.size <= policy.maxProjects &&
        value.stressedCostUsd <= policy.budgetUsd &&
        value.staffDays <= policy.staffDays &&
        value.reviewMinutes <= policy.reviewMinutes &&
        value.bountyTokens <= policy.jobBudgetTokens &&
        value.downsideNpvUsd >= policy.minDownsideNpvUsd &&
        selected.every(
            (p) =>
                p.evidenceBps >= policy.minEvidenceBps &&
                p.requires.every((id) => ids.has(id)) &&
                !p.excludes.some((id) => ids.has(id)),
        ) &&
        SECTORS.every(
            (s) =>
                selected.filter((p) => p.sector === s).length <=
                policy.maxPerSector,
        )
    );
}
function rank(a, b) {
    for (const [key, sign] of [
        ["expectedNpvUsd", -1],
        ["downsideNpvUsd", -1],
        ["stressedCostUsd", 1],
        ["staffDays", 1],
        ["reviewMinutes", 1],
        ["bountyTokens", 1],
    ])
        if (a[key] !== b[key]) return sign * (a[key] - b[key]);
    const x = a.projectIds,
        y = b.projectIds;
    for (let i = 0; i < Math.min(x.length, y.length); i++)
        if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
    return x.length - y.length;
}
export async function solve(raw) {
    const source = validate(raw),
        projects = source.projects,
        policy = source.policy;
    const rows = projects.map((p) => ({
        id: p.id,
        ...economics(p, policy),
        evidenceEligible: p.evidenceBps >= policy.minEvidenceBps,
    }));
    const best = [];
    let feasible = 0;
    for (let mask = 0; mask < 2 ** projects.length; mask++) {
        const indices = [];
        for (let i = 0; i < projects.length; i++)
            if (mask & (1 << i)) indices.push(i);
        if (indices.length > policy.maxProjects) continue;
        const candidate = portfolio(indices, projects, rows);
        if (fits(candidate, source)) {
            feasible++;
            best.push(candidate);
            best.sort(rank);
            if (best.length > 3) best.length = 3;
        }
    }
    const selected = best[0] || null,
        indices = new Map(projects.map((p, i) => [p.id, i]));
    let greedyIndices = new Set(),
        greedy = portfolio([], projects, rows);
    function closure(index) {
        const result = new Set([index]);
        for (const id of projects[index].requires)
            for (const i of closure(indices.get(id))) result.add(i);
        return result;
    }
    const order = projects
        .map((_, i) => i)
        .sort(
            (a, b) =>
                rows[b].expectedNpvUsd - rows[a].expectedNpvUsd ||
                (projects[a].id < projects[b].id ? -1 : 1),
        );
    for (const i of order) {
        const proposed = new Set([...greedyIndices, ...closure(i)]),
            candidate = portfolio(
                [...proposed].sort((a, b) => a - b),
                projects,
                rows,
            );
        if (
            fits(candidate, source) &&
            candidate.expectedNpvUsd > greedy.expectedNpvUsd
        ) {
            greedy = candidate;
            greedyIndices = proposed;
        }
    }
    if (!fits(greedy, source)) greedy = null;
    const chosen = projects.filter((p) => selected?.projectIds.includes(p.id));
    const jobs = chosen.map((p) => ({
        goal: `Validate the business case and implementation plan for ${p.id}: ${p.name}`,
        successMetric: p.metric,
        bounty: String(BigInt(p.bountyTokens) * 10n ** 18n),
        duration: p.durationDays * 86400,
        priceWeight: 5000,
    }));
    const sensitivity = [
        ["Policy downside", policy.benefitHaircutBps, policy.costOverrunBps],
        ["Benefits -50%, negative cash flows +50%, costs +25%", 5000, 2500],
        ["Benefits -75%, negative cash flows +75%, costs +50%", 7500, 5000],
    ].map(([scenario, haircut, overrun]) => {
        const values = chosen.map((p) =>
                economics(p, {
                    ...policy,
                    benefitHaircutBps: haircut,
                    costOverrunBps: overrun,
                }),
            ),
            capitalUsd = values.reduce((sum, v) => sum + v.stressedCostUsd, 0);
        return {
            scenario,
            benefitHaircutBps: haircut,
            costOverrunBps: overrun,
            npvUsd: values.reduce((sum, v) => sum + v.downsideNpvUsd, 0),
            capitalUsd,
            budgetFits: !!selected && capitalUsd <= policy.budgetUsd,
        };
    });
    const roles = [
        "Finance",
        "Biotech",
        "Materials",
        "Policy",
        "Energy",
        "Manufacturing",
        "Logistics",
        "Research",
        "Quantum",
    ].map((role, i) => ({
        role,
        scope: "Deterministic sector analysis",
        projectIds: projects
            .filter((p) => p.sector === SECTORS[i])
            .map((p) => p.id),
    }));
    roles.push(
        {
            role: "Safety",
            scope: "Input, resource, evidence and downside constraints; independent review still required",
            projectIds: chosen.map((p) => p.id),
        },
        {
            role: "Godel",
            scope: "Exact recomputation and greedy comparison; no formal proof or autonomous model update",
            projectIds: chosen.map((p) => p.id),
        },
    );
    const result = {
        status: !selected
            ? "NO_FEASIBLE_PORTFOLIO"
            : chosen.length
              ? "REVIEW_REQUIRED"
              : "HOLD_NO_POSITIVE_VALUE",
        portfolio: selected,
        alternatives: best.slice(1),
        analysis: rows,
        search: {
            method: "Exhaustive subsets; maximum expected NPV under all declared constraints",
            subsets: 2 ** projects.length,
            feasible,
        },
        comparison: {
            method: "Greedy standalone expected NPV with dependency closure",
            portfolio: greedy,
            upliftUsd:
                selected && greedy
                    ? selected.expectedNpvUsd - greedy.expectedNpvUsd
                    : null,
        },
        sensitivity,
        roles,
        jobs,
        settlementPreview: chosen.map((p, i) => {
            const gross = BigInt(jobs[i].bounty),
                burn = gross / 100n;
            return {
                projectId: p.id,
                grossBaseUnits: String(gross),
                burnBaseUnits: String(burn),
                netBaseUnits: String(gross - burn),
            };
        }),
        approval: "UNREVIEWED",
        scope: SCOPE,
    };
    const body = { schema: REPORT_SCHEMA, input: source, result };
    return { ...body, sha256: await digest(body) };
}
export async function verify(report) {
    keys(report, ["schema", "input", "result", "sha256"], "Dossier");
    const rebuilt = await solve(report.input);
    if (canonical(report) !== canonical(rebuilt))
        throw Error(
            "Dossier differs from recomputed input, decisions, jobs or commitment",
        );
    return rebuilt;
}
