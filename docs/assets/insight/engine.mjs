// SPDX-License-Identifier: Apache-2.0
// Bounded, deterministic planning models. No network, hidden scores or claimed valuation.
import { canonicalJSON, hashObject } from "../ascension/crypto.mjs";

export const ENGINE = "insight-atlas/1.0.0";
export const MAX_PORTABLE_BYTES = 250000;

export function serializePortableJSON(value) {
    const compact = canonicalJSON(value);
    const readable = JSON.stringify(value, null, 2) + "\n";
    return new TextEncoder().encode(readable).length <= MAX_PORTABLE_BYTES
        ? readable
        : compact;
}

export const SECTORS = [
    "Energy",
    "Compute",
    "Science",
    "Health",
    "Materials",
    "Robotics",
    "Finance",
    "Climate",
    "Machine labor",
    "Infrastructure",
    "Education",
    "Governance",
];
export const BASELINE = Object.freeze({
    agents: 2,
    validators: 2,
    groups: 2,
    quorum: 2,
    operator_slots: 24,
    budget: 1800,
    horizon: 120,
    fault_groups: 1,
});
export const DEFAULT_CONFIG = Object.freeze({
    ...BASELINE,
    agents: 4,
    validators: 4,
    groups: 4,
});
const fail = (message) => {
    throw new Error(message);
};
const copy = (value) => JSON.parse(canonicalJSON(value));
const integer = (value, min, max, name) => {
    if (!Number.isSafeInteger(value) || value < min || value > max)
        fail(`${name} must be an integer from ${min} to ${max}.`);
    return value;
};
const string = (value, min, max, name) => {
    if (
        typeof value !== "string" ||
        value.trim().length < min ||
        value.length > max
    )
        fail(`${name} must contain ${min}–${max} characters.`);
    return value;
};
const keys = (obj, allowed, name) => {
    if (
        !obj ||
        Array.isArray(obj) ||
        typeof obj !== "object" ||
        Object.keys(obj).some((key) => !allowed.includes(key))
    )
        fail(`${name} contains an unsupported field.`);
};
const identifier = (value) => {
    if (typeof value !== "string" || !/^[a-z][a-z0-9_-]{0,47}$/.test(value))
        fail(
            "IDs must start with a lowercase letter and contain at most 48 letters, digits, underscores or hyphens.",
        );
    return value;
};
const unique = (items, name) => {
    if (new Set(items).size !== items.length) fail(`${name} must be unique.`);
};

export function validateConfig(value) {
    keys(value, Object.keys(BASELINE), "Architecture");
    const ranges = {
        agents: [1, 8],
        validators: [1, 6],
        groups: [1, 6],
        quorum: [1, 3],
        operator_slots: [0, 40],
        budget: [100, 5000],
        horizon: [30, 240],
        fault_groups: [0, 1],
    };
    for (const [key, [min, max]] of Object.entries(ranges))
        integer(value[key], min, max, key);
    if (value.groups > value.validators || value.quorum > value.validators)
        fail("Groups and quorum cannot exceed the number of validators.");
    return copy(value);
}

export function validateScenario(value) {
    // Canonical encoding rejects oversized, non-finite, deeply nested and non-JSON input first.
    const scenario = copy(value);
    keys(
        scenario,
        [
            "schema",
            "id",
            "title",
            "question",
            "envelope_usd",
            "weights_bps",
            "sources",
            "claims",
            "workload",
        ],
        "Scenario",
    );
    if (scenario.schema !== "agialpha.insight.scenario.v1")
        fail("Unsupported scenario schema.");
    identifier(scenario.id);
    string(scenario.title, 3, 100, "Title");
    string(scenario.question, 3, 600, "Question");
    allocateEnvelope(scenario.envelope_usd, scenario.weights_bps);
    if (
        !Array.isArray(scenario.sources) ||
        scenario.sources.length < 1 ||
        scenario.sources.length > 16
    )
        fail("Provide 1–16 sources.");
    const sourceIds = [];
    for (const source of scenario.sources) {
        keys(source, ["id", "title", "text", "kind", "url"], "Source");
        sourceIds.push(identifier(source.id));
        string(source.title, 1, 160, "Source title");
        string(source.text, 1, 4000, "Source text");
        if (
            !["synthetic", "public-reference", "user-supplied"].includes(
                source.kind,
            )
        )
            fail(
                "Source kind must be synthetic, public-reference or user-supplied.",
            );
        if (source.url !== undefined && source.url !== "") {
            string(source.url, 1, 2048, "Source URL");
            const url = new URL(source.url);
            if (
                !["https:", "http:"].includes(url.protocol) ||
                url.username ||
                url.password
            )
                fail(
                    "Source links must be HTTP(S), without embedded credentials.",
                );
        }
    }
    unique(sourceIds, "Source IDs");
    if (
        !Array.isArray(scenario.claims) ||
        scenario.claims.length < 1 ||
        scenario.claims.length > 24
    )
        fail("Provide 1–24 claims.");
    const claimIds = [];
    for (const claim of scenario.claims) {
        keys(
            claim,
            [
                "id",
                "sector",
                "title",
                "hypothesis",
                "source_ids",
                "metric",
                "target",
                "evidence_needed",
            ],
            "Claim",
        );
        claimIds.push(identifier(claim.id));
        if (!SECTORS.includes(claim.sector))
            fail("Choose one of the 12 defined sectors.");
        for (const [key, max] of [
            ["title", 120],
            ["hypothesis", 700],
            ["metric", 160],
            ["target", 200],
            ["evidence_needed", 800],
        ])
            string(claim[key], 3, max, key);
        if (
            !Array.isArray(claim.source_ids) ||
            claim.source_ids.length < 1 ||
            claim.source_ids.length > 8
        )
            fail("Each claim needs 1–8 source references.");
        unique(claim.source_ids, "Claim source references");
        if (claim.source_ids.some((id) => !sourceIds.includes(id)))
            fail("Claim refers to an unknown source.");
    }
    unique(claimIds, "Claim IDs");
    keys(scenario.workload, ["training", "holdout"], "Workload");
    const taskIds = [];
    for (const split of ["training", "holdout"]) {
        const tasks = scenario.workload[split];
        if (!Array.isArray(tasks) || tasks.length < 4 || tasks.length > 40)
            fail("Each benchmark split needs 4–40 tasks.");
        for (const task of tasks) {
            keys(
                task,
                ["id", "arrival", "minutes", "review_minutes", "due", "valid"],
                "Task",
            );
            taskIds.push(identifier(task.id));
            integer(task.arrival, 0, 120, "Arrival");
            integer(task.minutes, 1, 60, "Execution minutes");
            integer(task.review_minutes, 1, 30, "Review minutes");
            integer(task.due, task.arrival + 1, 300, "Deadline");
            if (typeof task.valid !== "boolean")
                fail("Benchmark truth labels must be Boolean.");
        }
        if (
            !tasks.some((task) => task.valid) ||
            !tasks.some((task) => !task.valid)
        )
            fail("Both splits need positive and negative benchmark cases.");
    }
    unique(taskIds, "Training and holdout task IDs");
    return scenario;
}

export function allocateEnvelope(amount, weights) {
    if (typeof amount !== "string" || !/^(?:0|[1-9]\d{0,20})$/.test(amount))
        fail(
            "Scenario envelope must be an unsigned whole-dollar string, at most 21 digits.",
        );
    keys(weights, SECTORS, "Sector weights");
    const rows = SECTORS.map((sector) => ({
        sector,
        weight_bps: integer(weights[sector], 0, 10000, `${sector} weight`),
    }));
    if (rows.reduce((sum, row) => sum + row.weight_bps, 0) !== 10000)
        fail("Sector weights must total exactly 10,000 basis points (100%).");
    const total = BigInt(amount);
    const parts = rows.map((row, i) => ({
        ...row,
        i,
        dollars: (total * BigInt(row.weight_bps)) / 10000n,
        remainder: (total * BigInt(row.weight_bps)) % 10000n,
    }));
    let left = total - parts.reduce((sum, row) => sum + row.dollars, 0n);
    for (const row of [...parts].sort((a, b) =>
        a.remainder === b.remainder
            ? a.i - b.i
            : a.remainder > b.remainder
              ? -1
              : 1,
    )) {
        if (left <= 0n) break;
        row.dollars += 1n;
        left -= 1n;
    }
    return parts.map(({ sector, weight_bps, dollars }) => ({
        sector,
        weight_bps,
        scenario_usd: String(dollars),
    }));
}

export function quadrillionsToDollars(value) {
    if (
        typeof value !== "string" ||
        !/^(?:0|[1-9]\d{0,5})(?:\.\d{1,3})?$/.test(value)
    )
        fail(
            "Enter 0–999999.999 quadrillion, with at most three decimal places.",
        );
    const [whole, fraction = ""] = value.split(".");
    return String(
        BigInt(whole) * 1000000000000000n +
            BigInt(fraction.padEnd(3, "0")) * 1000000000000n,
    );
}

function runTasks(tasks, cfg) {
    const workers = Array.from({ length: cfg.agents }, (_, id) => ({
        id,
        ready: 0,
    }));
    const validators = Array.from({ length: cfg.validators }, (_, id) => ({
        id,
        group: id % cfg.groups,
        ready: 0,
    }));
    const rows = [];
    // Credits reserve the whole admitted job, including two operator minutes even if rejected.
    let reserved = cfg.agents * 8 + cfg.validators * 6;
    for (const task of [...tasks].sort(
        (a, b) => a.arrival - b.arrival || a.id.localeCompare(b.id, "en"),
    )) {
        const price =
            task.minutes * 2 + task.review_minutes * cfg.quorum * 3 + 4;
        const row = {
            ...task,
            cost: 0,
            start: null,
            execution_end: null,
            review_end: null,
            end: null,
            reviewers: [],
            status: "queued",
        };
        rows.push(row);
        if (cfg.groups < cfg.quorum) {
            row.status = "blocked-independence";
            continue;
        }
        if (reserved + price > cfg.budget) {
            row.status = "blocked-budget";
            continue;
        }
        const worker = [...workers].sort(
            (a, b) => a.ready - b.ready || a.id - b.id,
        )[0];
        row.start = Math.max(task.arrival, worker.ready);
        row.execution_end = row.start + task.minutes;
        row.worker = worker.id;
        row.cost = price;
        worker.ready = row.execution_end;
        reserved += price;
    }
    const admitted = rows
        .filter((row) => row.execution_end !== null)
        .sort(
            (a, b) =>
                a.execution_end - b.execution_end ||
                a.id.localeCompare(b.id, "en"),
        );
    for (const row of admitted) {
        const selected = [];
        for (const validator of [...validators].sort(
            (a, b) => a.ready - b.ready || a.id - b.id,
        )) {
            if (selected.some((other) => other.group === validator.group))
                continue;
            selected.push(validator);
            if (selected.length === cfg.quorum) break;
        }
        row.reviewers = selected.map((validator) => {
            const start = Math.max(row.execution_end, validator.ready);
            validator.ready = start + row.review_minutes;
            return {
                id: validator.id,
                group: validator.group,
                start,
                end: validator.ready,
                vote: row.valid || validator.group < cfg.fault_groups,
            };
        });
        row.review_end = Math.max(
            ...row.reviewers.map((reviewer) => reviewer.end),
        );
        row.status = row.reviewers.every((reviewer) => reviewer.vote)
            ? "awaiting-operator"
            : "rejected";
        if (row.status === "rejected") row.end = row.review_end;
    }
    let operatorReady = 0;
    let reviewed = 0;
    for (const row of admitted
        .filter((row) => row.status === "awaiting-operator")
        .sort(
            (a, b) =>
                a.review_end - b.review_end || a.id.localeCompare(b.id, "en"),
        )) {
        if (reviewed >= cfg.operator_slots) {
            row.status = "blocked-operator";
            continue;
        }
        row.end = Math.max(row.review_end, operatorReady) + 2;
        operatorReady = row.end;
        reviewed += 1;
        row.status =
            row.end > cfg.horizon
                ? "beyond-horizon"
                : row.end > row.due
                  ? "late"
                  : "accepted";
    }
    const completed = rows.filter(
        (row) => row.end !== null && row.end <= cfg.horizon,
    );
    const accepted = completed.filter((row) =>
        ["accepted", "late"].includes(row.status),
    );
    const latencies = accepted
        .map((row) => row.end - row.arrival)
        .sort((a, b) => a - b);
    const useful = accepted.filter(
        (row) => row.valid && row.status === "accepted",
    ).length;
    return {
        metrics: {
            tasks: tasks.length,
            admitted: admitted.length,
            completed: completed.length,
            useful,
            unsafe_accepts: accepted.filter((row) => !row.valid).length,
            rejected_invalid: completed.filter(
                (row) => row.status === "rejected" && !row.valid,
            ).length,
            missed_valid: tasks.filter((task) => task.valid).length - useful,
            reserved_credits: reserved,
            remaining_credits: cfg.budget - reserved,
            median_latency: latencies.length
                ? (latencies[Math.floor((latencies.length - 1) / 2)] +
                      latencies[Math.floor(latencies.length / 2)]) /
                  2
                : null,
            operator_reviews: reviewed,
        },
        rows,
    };
}

export function compareArchitectures(input, configuration = DEFAULT_CONFIG) {
    const scenario = validateScenario(input);
    const config = validateConfig(configuration);
    const baseline = {
        ...BASELINE,
        budget: config.budget,
        horizon: config.horizon,
        operator_slots: config.operator_slots,
        fault_groups: config.fault_groups,
    };
    const result = {
        engine: ENGINE,
        baseline_config: baseline,
        candidate_config: config,
        training: {},
        holdout: {},
    };
    for (const split of ["training", "holdout"]) {
        result[split] = {
            baseline: runTasks(scenario.workload[split], baseline),
            candidate: runTasks(scenario.workload[split], config),
        };
    }
    return result;
}

export function searchArchitectures(input, configuration = DEFAULT_CONFIG) {
    const scenario = validateScenario(input);
    const current = validateConfig(configuration);
    const candidates = [];
    for (const agents of [2, 3, 4, 5, 6, 8])
        for (const validators of [2, 4, 6]) {
            const config = {
                ...current,
                agents,
                validators,
                groups: validators,
                quorum: 2,
            };
            const training = runTasks(
                scenario.workload.training,
                config,
            ).metrics;
            candidates.push({ config, training });
        }
    candidates.sort(
        (a, b) =>
            a.training.unsafe_accepts - b.training.unsafe_accepts ||
            b.training.useful - a.training.useful ||
            a.training.reserved_credits - b.training.reserved_credits ||
            (a.training.median_latency ?? 1000) -
                (b.training.median_latency ?? 1000),
    );
    const frontier = candidates.filter(
        (candidate) =>
            !candidates.some(
                (other) =>
                    other !== candidate &&
                    other.training.useful >= candidate.training.useful &&
                    other.training.reserved_credits <=
                        candidate.training.reserved_credits &&
                    (other.training.useful > candidate.training.useful ||
                        other.training.reserved_credits <
                            candidate.training.reserved_credits),
            ),
    );
    // Holdout is deliberately not used to select the winner. Repeated tuning still risks overfitting.
    return {
        candidates,
        frontier,
        selected: candidates[0].config,
        evaluation: compareArchitectures(scenario, candidates[0].config),
    };
}

export function proofGates(comparison) {
    const cfg = comparison.candidate_config;
    const reports = [
        comparison.training.candidate,
        comparison.holdout.candidate,
    ];
    return [
        {
            id: "independence",
            label: "Distinct reviewer groups",
            passed: cfg.groups >= cfg.quorum && cfg.quorum > cfg.fault_groups,
            detail: `${cfg.quorum} unanimous votes; ${cfg.groups} groups; ${cfg.fault_groups} modeled faulty group.`,
        },
        {
            id: "budget",
            label: "Reserved budget conserved",
            passed: reports.every(
                (report) =>
                    report.metrics.remaining_credits >= 0 &&
                    report.metrics.reserved_credits +
                        report.metrics.remaining_credits ===
                        cfg.budget,
            ),
            detail: "Each admitted job reserves execution, quorum and operator costs before starting.",
        },
        {
            id: "safety",
            label: "Negative controls rejected",
            passed: reports.every(
                (report) =>
                    report.metrics.unsafe_accepts === 0 &&
                    report.metrics.rejected_invalid > 0,
            ),
            detail: "Both fixture splits must reject at least one invalid task and accept none.",
        },
        {
            id: "holdout",
            label: "Holdout does not regress",
            passed:
                comparison.holdout.candidate.metrics.useful >=
                    comparison.holdout.baseline.metrics.useful &&
                comparison.holdout.candidate.metrics.useful > 0,
            detail: "On-time valid outputs must meet or exceed the baseline on the separate fixture split.",
        },
    ];
}

export async function buildEvidence(input, configuration) {
    const scenario = validateScenario(input);
    const config = validateConfig(configuration);
    const comparison = compareArchitectures(scenario, config);
    const body = {
        schema: "agialpha.insight.evidence.v1",
        engine: ENGINE,
        scope: "local-model-benchmark",
        scenario,
        config,
        input_hash: await hashObject({ scenario, config }),
        comparison,
        gates: proofGates(comparison),
    };
    return { ...body, digest: await hashObject(body) };
}

export async function verifyEvidence(bundle, expectedInput = null) {
    // Reconstruct everything, including the verdict. A declared 'pass' flag is never evidence.
    const expected = await buildEvidence(bundle?.scenario, bundle?.config);
    if (canonicalJSON(bundle) !== canonicalJSON(expected))
        fail(
            "Evidence replay differs from the supplied bundle. Inputs, results or digest were changed.",
        );
    if (
        expectedInput &&
        expected.input_hash !==
            (await hashObject({
                scenario: validateScenario(expectedInput.scenario),
                config: validateConfig(expectedInput.config),
            }))
    )
        fail(
            "Evidence is stale: it does not match the current scenario and architecture.",
        );
    return {
        digest: expected.digest,
        passed: expected.gates.every((gate) => gate.passed),
        gates: expected.gates,
        scope: expected.scope,
    };
}

export function buildDossier(input, configuration) {
    const scenario = validateScenario(input);
    const config = validateConfig(configuration);
    const sources = scenario.sources.map((source) => ({
        ...source,
        node_type: "source",
    }));
    const claims = scenario.claims.map((claim) => ({
        ...claim,
        node_type: "claim",
        status: "external-evidence-required",
    }));
    const briefs = claims.map((claim) => ({
        id: `proof-${claim.id}`,
        claim_id: claim.id,
        status: "unassigned-local-brief",
        question: claim.hypothesis,
        metric: claim.metric,
        acceptance: claim.target,
        evidence_required: claim.evidence_needed,
        controls: [
            "Record the baseline and the intervention",
            "Keep an untouched holdout and report failed cases",
            "Use an independent reviewer; disclose conflicts",
            "Attach raw measurements, methodology and reproducible analysis",
        ],
        funding:
            "Unfunded. No wallet transaction, on-chain settlement or posted AGI Jobs task.",
    }));
    const nodes = [
        ...SECTORS.map((sector) => ({
            id: `sector:${sector}`,
            label: sector,
            node_type: "sector",
        })),
        ...sources.map((source) => ({ ...source, id: `source:${source.id}` })),
        ...claims.map((claim) => ({ ...claim, id: `claim:${claim.id}` })),
        ...briefs.map((brief) => ({
            ...brief,
            id: `brief:${brief.id}`,
            node_type: "proof-debt",
        })),
    ];
    const edges = claims.flatMap((claim) => [
        {
            from: `claim:${claim.id}`,
            to: `sector:${claim.sector}`,
            relation: "concerns",
        },
        ...claim.source_ids.map((id) => ({
            from: `claim:${claim.id}`,
            to: `source:${id}`,
            relation: "references-not-verifies",
        })),
        {
            from: `claim:${claim.id}`,
            to: `brief:proof-${claim.id}`,
            relation: "requires-evidence",
        },
    ]);
    const missions = scenario.claims.map((claim) => ({
        goal: `Assess the evidence for: ${claim.hypothesis} Required test: ${claim.evidence_needed}`,
        work: {
            kind: "research",
            sources: claim.source_ids.map((id) => {
                const source = scenario.sources.find((item) => item.id === id);
                return {
                    id: source.id,
                    title: source.title,
                    text: `[${source.kind}; unverified input] ${source.text}`,
                    url: source.url || "",
                };
            }),
        },
    }));
    return {
        schema: "agialpha.insight.dossier.v1",
        engine: ENGINE,
        scenario,
        config,
        allocations: allocateEnvelope(
            scenario.envelope_usd,
            scenario.weights_bps,
        ),
        economic_value_verified_usd: "0",
        graph: { nodes, edges },
        briefs,
        missions,
    };
}

export function emptyChronicle() {
    return { schema: "agialpha.insight.chronicle.v1", events: [], bundles: {} };
}

export async function verifyChronicle(input) {
    const chronicle = copy(input);
    keys(chronicle, ["schema", "events", "bundles"], "Chronicle");
    if (
        chronicle.schema !== "agialpha.insight.chronicle.v1" ||
        !Array.isArray(chronicle.events) ||
        chronicle.events.length > 20 ||
        !chronicle.bundles ||
        Array.isArray(chronicle.bundles) ||
        typeof chronicle.bundles !== "object"
    )
        fail("Invalid Chronicle, or more than 20 events.");
    const active = new Set();
    const ever = new Set();
    let previous = "genesis";
    for (const event of chronicle.events) {
        keys(
            event,
            ["sequence", "action", "digest", "note", "previous", "hash"],
            "Chronicle event",
        );
        string(event.note, 12, 500, "Operator review note");
        // Sequence is an event index, including revocations.
        if (
            event.sequence !== chronicle.events.indexOf(event) + 1 ||
            event.previous !== previous
        )
            fail("Chronicle linkage is invalid.");
        const { hash, ...body } = event;
        if (hash !== (await hashObject(body)))
            fail("Chronicle event hash mismatch.");
        if (event.action === "promote") {
            if (ever.has(event.digest)) fail("Duplicate capability promotion.");
            const bundle = chronicle.bundles[event.digest];
            const result = await verifyEvidence(bundle);
            if (!result.passed || result.digest !== event.digest)
                fail(
                    "A Chronicle capability did not pass replay and all model gates.",
                );
            ever.add(event.digest);
            active.add(event.digest);
        } else if (event.action === "revoke" && active.has(event.digest))
            active.delete(event.digest);
        else fail("Unsupported or inactive Chronicle action.");
        previous = event.hash;
    }
    if (
        Object.keys(chronicle.bundles).length !== ever.size ||
        Object.keys(chronicle.bundles).some((digest) => !ever.has(digest))
    )
        fail("Chronicle contains an unreferenced bundle.");
    return { chronicle, active: [...active], head: previous };
}

export async function appendChronicle(
    input,
    { action, bundle, digest, note },
    expectedInput = null,
) {
    const { chronicle, head } = await verifyChronicle(input);
    if (action === "promote") {
        const verified = await verifyEvidence(bundle, expectedInput);
        if (!verified.passed)
            fail("Resolve every failed model gate before promotion.");
        digest = verified.digest;
        chronicle.bundles[digest] = copy(bundle);
    }
    const body = {
        sequence: chronicle.events.length + 1,
        action,
        digest,
        note: string(note, 12, 500, "Operator review note"),
        previous: head,
    };
    chronicle.events.push({ ...body, hash: await hashObject(body) });
    await verifyChronicle(chronicle);
    if (expectedInput)
        await exportWorkspace(
            expectedInput.scenario,
            expectedInput.config,
            chronicle,
        );
    return chronicle;
}

export async function exportWorkspace(scenario, config, chronicle) {
    await verifyChronicle(chronicle);
    const body = {
        schema: "agialpha.insight.workspace.v1",
        scenario: validateScenario(scenario),
        config: validateConfig(config),
        chronicle,
    };
    const workspace = { ...body, digest: await hashObject(body) };
    serializePortableJSON(workspace);
    return workspace;
}

export async function restoreWorkspace(value) {
    const workspace = copy(value);
    keys(
        workspace,
        ["schema", "scenario", "config", "chronicle", "digest"],
        "Workspace",
    );
    if (workspace.schema !== "agialpha.insight.workspace.v1")
        fail("Unsupported workspace schema.");
    const restored = await exportWorkspace(
        workspace.scenario,
        workspace.config,
        workspace.chronicle,
    );
    if (canonicalJSON(restored) !== canonicalJSON(workspace))
        fail("Workspace digest mismatch. Restore the original download.");
    return restored;
}
