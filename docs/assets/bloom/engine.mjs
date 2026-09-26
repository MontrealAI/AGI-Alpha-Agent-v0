// SPDX-License-Identifier: Apache-2.0
// Proof Bloom protocol: bounded execution, replay, explicit review and reversible memory.
import { canonicalJSON, hashObject } from "../ascension/crypto.mjs";
import { runMission } from "../portal/mission-engine.mjs";
import { verifyAgentExport } from "../portal/verify-export.mjs";

export const PROTOCOL = "agialpha.bloom.v1";
export const PLAYBOOKS = ["proof", "nova", "sovereign", "omega", "invention"];
const clone = (value) => JSON.parse(canonicalJSON(value));
const same = (a, b) => canonicalJSON(a) === canonicalJSON(b);
const fail = (message) => {
    throw new Error(message);
};
const assert = (condition, message) => {
    if (!condition) fail(message);
};
const text = (value, label, min = 3, max = 2000) => {
    assert(
        typeof value === "string" &&
            value.trim().length >= min &&
            value.length <= max,
        `${label} needs ${min}–${max} characters.`,
    );
    return value.trim();
};
const exact = (value, fields, label) => {
    assert(
        value &&
            !Array.isArray(value) &&
            typeof value === "object" &&
            Object.keys(value).length === fields.length &&
            fields.every((key) => Object.hasOwn(value, key)),
        `${label} contains missing or unsupported fields.`,
    );
};
const hashPattern = /^[a-f0-9]{64}$/;

export function serialize(value) {
    const compact = canonicalJSON(value);
    const pretty = JSON.stringify(value, null, 2) + "\n";
    return new TextEncoder().encode(pretty).length <= 250000 ? pretty : compact;
}

export function parse(textValue) {
    assert(
        typeof textValue === "string" &&
            new TextEncoder().encode(textValue).length <= 250000,
        "Import exceeds 250 KB.",
    );
    const value = JSON.parse(textValue);
    canonicalJSON(value);
    return value;
}

export function normalizeMission(input) {
    const mission = clone(input);
    const work = mission.work;
    assert(
        work &&
            ["allocation", "schedule", "forecast", "research"].includes(
                work.kind,
            ),
        "Use an allocation, schedule, forecast or research Mission.",
    );
    mission.seed ??= 42;
    mission.population ??= 20;
    mission.generations ??= 12;
    if (work.kind === "allocation") {
        assert(
            Array.isArray(work.items) && work.items.length <= 12,
            "Bloom accepts up to 12 allocation items.",
        );
        work.max_risk ??= 180000;
        work.unit ??= "planning units";
        work.items.forEach((item) => {
            item.risk ??= 0;
        });
    } else if (work.kind === "schedule") {
        assert(
            Array.isArray(work.jobs) && work.jobs.length <= 6,
            "Bloom accepts up to six scheduling jobs.",
        );
        work.unit ??= "minutes";
        work.jobs.forEach((job) => {
            job.due ??= 10000000;
        });
    } else if (work.kind === "forecast") {
        assert(
            Array.isArray(work.observations) && work.observations.length <= 240,
            "Bloom accepts up to 240 observations.",
        );
        work.holdout ??= 4;
        work.horizon ??= 3;
        work.season ??= 1;
        work.unit ??= "observed units";
    } else {
        assert(
            Array.isArray(work.sources) && work.sources.length <= 6,
            "Bloom accepts up to six supplied sources.",
        );
        work.sources.forEach((source) => {
            source.url ??= "";
        });
    }
    runMission(clone(mission)); // The shared bounded engine rejects unknown fields and invalid values.
    return mission;
}

export function makeSeed(input) {
    exact(
        input,
        ["playbook", "objective", "claim", "mission", "shock", "parents"],
        "Seed input",
    );
    assert(PLAYBOOKS.includes(input.playbook), "Unknown guided experience.");
    assert(
        Number.isInteger(input.shock) && input.shock >= 10 && input.shock <= 50,
        "Stress must be a whole percentage from 10 to 50.",
    );
    assert(
        Array.isArray(input.parents) &&
            input.parents.length <= 4 &&
            input.parents.every(
                (id) => typeof id === "string" && hashPattern.test(id),
            ) &&
            new Set(input.parents).size === input.parents.length,
        "Invalid capability dependencies.",
    );
    return {
        schema: PROTOCOL + ".seed",
        playbook: input.playbook,
        objective: text(input.objective, "Objective"),
        claim: text(input.claim, "Visionary claim"),
        mission: normalizeMission(input.mission),
        shock: input.shock,
        parents: [...input.parents],
    };
}

function checkedSeed(seed) {
    exact(
        seed,
        [
            "schema",
            "playbook",
            "objective",
            "claim",
            "mission",
            "shock",
            "parents",
        ],
        "Seed",
    );
    const { schema, ...input } = seed;
    assert(
        schema === PROTOCOL + ".seed" && same(makeSeed(input), seed),
        "Seed is not canonical.",
    );
    return seed;
}

function stressMission(seed) {
    const mission = clone(seed.mission);
    const work = mission.work;
    if (work.kind === "allocation") {
        work.items.forEach((item) => {
            item.cost = Math.ceil((item.cost * (100 + seed.shock)) / 100);
        });
    } else if (work.kind === "schedule") {
        work.jobs.forEach((job) =>
            job.operations.forEach((op) => {
                op.duration = Math.ceil(
                    (op.duration * (100 + seed.shock)) / 100,
                );
            }),
        );
    } else if (work.kind === "forecast") {
        const split = work.observations.length - work.holdout;
        // Training data remain untouched; the alternative holdout is a declared synthetic stress case.
        work.observations = work.observations.map((value, i) =>
            i < split
                ? value
                : value +
                  ((Math.abs(value) * seed.shock) / 100) * (i % 2 ? 1 : -1),
        );
    } else {
        // Reverse the fixed corpus to check quotation provenance under a changed source ordering.
        work.sources.reverse();
    }
    return normalizeMission(mission);
}

export async function compile(seed) {
    checkedSeed(seed);
    const seed_hash = await hashObject(seed);
    const source = normalizeMission({
        goal: "Retrieve the claim, evidence limits and baseline assumptions from the supplied claim register.",
        work: {
            kind: "research",
            sources: [
                {
                    id: "claim",
                    title: "Operator claim register",
                    text: `Visionary claim: ${seed.claim}\nObjective: ${seed.objective}`,
                },
                {
                    id: "limits",
                    title: "Bounded evidence contract",
                    text:
                        "Evidence limits: these inputs are supplied assumptions. Replay checks computation, not source truth. " +
                        "The baseline uses input order for allocation and scheduling, last value for forecasting, and zero retrieved passages for research. " +
                        "The claim of real-world wealth, novelty, ownership or external validation remains unproven.",
                },
            ],
        },
    });
    const definitions = [
        [
            "source",
            "Trace the claim",
            source,
            "Exact quotations from the supplied register; no assertion of source truth.",
        ],
        [
            "benchmark",
            "Measure the capability",
            seed.mission,
            "Positive improvement over the declared baseline; research requires matching quotations.",
        ],
        [
            "stress",
            "Challenge the advantage",
            stressMission(seed),
            "Advantage must also survive the declared stress case; research checks reversed source ordering.",
        ],
    ];
    const jobs = [];
    for (const [id, title, mission, acceptance] of definitions) {
        const body = {
            schema: PROTOCOL + ".job",
            seed_hash,
            id,
            title,
            mission,
            acceptance,
            dependencies: id === "source" ? [] : ["source"],
            worker_role:
                id === "source"
                    ? "Research agent / human analyst"
                    : "Bounded execution agent / human operator",
            reviewer_role:
                "Separate local reviewer decision; AGI Node receipt may be attached",
        };
        jobs.push({ ...body, digest: await hashObject(body) });
    }
    return { seed_hash, jobs };
}

export function measure(result) {
    const e = result.evidence;
    if (result.kind === "allocation")
        return {
            candidate: e.totals.value,
            baseline: e.baseline.value,
            delta: e.totals.value - e.baseline.value,
            metric: "modeled value",
            direction: "higher",
        };
    if (result.kind === "schedule")
        return {
            candidate: e.makespan,
            baseline: e.baseline_makespan,
            delta: e.baseline_makespan - e.makespan,
            metric: "makespan",
            direction: "lower",
        };
    if (result.kind === "forecast")
        return {
            candidate: e.holdout_mae,
            baseline: e.baseline_mae,
            delta: e.baseline_mae - e.holdout_mae,
            metric: "holdout MAE",
            direction: "lower",
        };
    const count = e.selection === "keyword_overlap" ? e.citations.length : 0;
    return {
        candidate: count,
        baseline: 0,
        delta: count,
        metric: "matching exact quotations",
        direction: "higher",
    };
}

async function nativeBinding(artifact, job, pins) {
    assert(
        Array.isArray(pins) && pins.includes(artifact.public_key),
        "Pin this agent's public key independently before accepting its signed return.",
    );
    const verified = await verifyAgentExport(artifact, artifact.public_key);
    const document = JSON.parse(verified.canonical).document;
    assert(
        document.review.approved === true &&
            document.review.verification?.passed === true,
        "Native receipt must contain an approved verified result.",
    );
    assert(
        same(normalizeMission(document.request), job.mission),
        "Native receipt belongs to a different job input.",
    );
    return verified.identity;
}

function jobFrom(plan, id) {
    const job = plan.jobs.find((candidate) => candidate.id === id);
    assert(job, "Unknown proof job.");
    return job;
}

export async function executeJob(
    seed,
    id,
    origin = { type: "browser" },
    pins = [],
    active = new Map(),
) {
    const plan = await compile(seed);
    const job = jobFrom(plan, id);
    for (const parent of seed.parents)
        assert(
            active.has(parent),
            "A prerequisite capability is revoked or unavailable.",
        );
    let result;
    if (origin.type === "native") {
        exact(origin, ["type", "artifact"], "Native origin");
        await nativeBinding(origin.artifact, job, pins);
        // Signed native approval is an attachment. This capability's numerical scope is always the local benchmark.
        result = runMission(clone(job.mission));
    } else if (origin.type === "reuse") {
        exact(origin, ["type", "capability", "job"], "Reuse origin");
        assert(
            seed.parents.includes(origin.capability),
            "Reused evidence must be an explicit capability dependency.",
        );
        const prior = active.get(origin.capability);
        assert(prior, "Reused capability is revoked or unavailable.");
        const oldJob = jobFrom(await compile(prior.seed), origin.job);
        assert(
            oldJob.id === job.id && same(oldJob.mission, job.mission),
            "Reused evidence has different inputs or scope.",
        );
        result = clone(prior.bundles[origin.job].result);
    } else {
        exact(origin, ["type"], "Browser origin");
        assert(origin.type === "browser", "Unknown proof origin.");
        result = runMission(clone(job.mission));
    }
    const body = {
        schema: PROTOCOL + ".bundle",
        seed_hash: plan.seed_hash,
        job_id: id,
        job_hash: job.digest,
        origin: clone(origin),
        result,
    };
    return { ...body, digest: await hashObject(body) };
}

export async function verifyBundle(
    seed,
    bundle,
    pins = [],
    active = new Map(),
) {
    exact(
        bundle,
        [
            "schema",
            "seed_hash",
            "job_id",
            "job_hash",
            "origin",
            "result",
            "digest",
        ],
        "ProofBundle",
    );
    const expected = await executeJob(
        seed,
        bundle.job_id,
        bundle.origin,
        pins,
        active,
    );
    assert(
        same(bundle, expected),
        "ProofBundle is stale, altered or does not replay against this exact job.",
    );
    return measure(expected.result);
}

export async function reviewBundle(
    seed,
    bundle,
    decision,
    reviewer,
    note,
    pins = [],
    active = new Map(),
) {
    await verifyBundle(seed, bundle, pins, active);
    assert(
        ["accept", "reject", "repair"].includes(decision),
        "Choose accept, reject or request repair.",
    );
    return {
        bundle_hash: bundle.digest,
        decision,
        reviewer: text(reviewer, "Reviewer", 2, 80),
        note: text(note, "Review note", 12, 1000),
        authority: "local-operator-record",
    };
}

export function newWorkspace(seed) {
    checkedSeed(seed);
    return {
        schema: PROTOCOL + ".workspace",
        seed: clone(seed),
        bundles: {},
        reviews: {},
        history: [],
    };
}

async function inspectDocket(seed, bundles, reviews, pins, active) {
    const plan = await compile(seed);
    for (const id of [...Object.keys(bundles), ...Object.keys(reviews)])
        jobFrom(plan, id);
    const rows = [];
    for (const job of plan.jobs) {
        const bundle = bundles[job.id];
        const review = reviews[job.id];
        let measurement = null;
        if (bundle) {
            assert(
                bundle.job_id === job.id,
                "Docket key does not match the returned job.",
            );
            measurement = await verifyBundle(seed, bundle, pins, active);
        }
        if (review) {
            assert(bundle, "A review cannot exist without its ProofBundle.");
            const expected = await reviewBundle(
                seed,
                bundle,
                review.decision,
                review.reviewer,
                review.note,
                pins,
                active,
            );
            assert(same(review, expected), "Review is stale or malformed.");
        }
        rows.push({
            id: job.id,
            title: job.title,
            replay: !!bundle,
            accepted: review?.decision === "accept",
            decision: review?.decision || "pending",
            measurement,
            origin: bundle?.origin.type || "awaiting work",
        });
    }
    const gates = [
        {
            id: "RSI",
            name: "Replay + review",
            passed: rows.every((row) => row.replay && row.accepted),
            rule: "All three exact job returns replay and have an explicit accepted review.",
        },
        {
            id: "ECI",
            name: "Executed advantage",
            passed: (rows[1].measurement?.delta ?? 0) > 0,
            rule: "The executed benchmark improves on its declared baseline; quotations establish retrieval only.",
        },
        {
            id: "MOVE37",
            name: "Challenge + persistence",
            passed: (rows[2].measurement?.delta ?? 0) > 0,
            rule: "The same acceptance rule survives a separate, disclosed stress case. This is a bounded probe, not a universal guarantee.",
        },
        {
            id: "LINEAGE",
            name: "Active foundations",
            passed: seed.parents.every((id) => active.has(id)),
            rule: "Every reused capability is active; revocation closes all dependent capabilities.",
        },
    ];
    return {
        schema: PROTOCOL + ".docket",
        seed_hash: plan.seed_hash,
        rows,
        gates,
        promotable: gates.every((gate) => gate.passed),
        visionary_claim: {
            text: seed.claim,
            status: "unproven",
            economic_value_verified: 0,
        },
        scope: "Reviewed bounded computation on supplied inputs. No real-world wealth, NFT ownership, external certification or live settlement is established.",
    };
}

export async function verifyHistory(history, pins = []) {
    assert(
        Array.isArray(history) && history.length <= 20,
        "Chronicle supports up to 20 events per portable workspace.",
    );
    const active = new Map();
    const admitted = new Set();
    let previous = "0".repeat(64);
    for (const event of history) {
        exact(
            event,
            ["sequence", "previous", "type", "payload", "digest"],
            "Chronicle event",
        );
        const { digest, ...body } = event;
        assert(
            event.sequence === history.indexOf(event) + 1 &&
                event.previous === previous &&
                digest === (await hashObject(body)),
            "Chronicle chain is altered or reordered.",
        );
        if (event.type === "promote") {
            exact(event.payload, ["seed", "bundles", "reviews"], "Promotion");
            const { seed, bundles, reviews } = event.payload;
            const docket = await inspectDocket(
                seed,
                bundles,
                reviews,
                pins,
                active,
            );
            assert(
                docket.promotable,
                "Chronicle promotion does not pass the proof gates.",
            );
            assert(
                !admitted.has(docket.seed_hash),
                "Duplicate capability in Chronicle.",
            );
            admitted.add(docket.seed_hash);
            active.set(digest, event.payload);
        } else if (event.type === "revoke") {
            exact(event.payload, ["capability", "reason"], "Revocation");
            assert(
                active.has(event.payload.capability),
                "Cannot revoke an inactive capability.",
            );
            text(event.payload.reason, "Revocation reason", 12, 1000);
            const removed = new Set([event.payload.capability]);
            for (const [id, payload] of active) {
                if (
                    removed.has(id) ||
                    payload.seed.parents.some((parent) => removed.has(parent))
                ) {
                    active.delete(id);
                    removed.add(id);
                }
            }
        } else fail("Unknown Chronicle event.");
        previous = digest;
    }
    return active;
}

export async function inspectWorkspace(workspace, pins = []) {
    exact(
        workspace,
        ["schema", "seed", "bundles", "reviews", "history"],
        "Workspace",
    );
    assert(
        workspace.schema === PROTOCOL + ".workspace",
        "Unknown workspace protocol.",
    );
    serialize(workspace);
    const active = await verifyHistory(workspace.history, pins);
    // Inactive dependencies hold the current mission; old bundle bytes remain inspectable but cannot be admitted.
    if (workspace.seed.parents.some((id) => !active.has(id))) {
        checkedSeed(workspace.seed);
        return {
            active,
            docket: null,
            blocked:
                "A prerequisite capability was revoked. Compile a new seed to continue.",
        };
    }
    return {
        active,
        docket: await inspectDocket(
            workspace.seed,
            workspace.bundles,
            workspace.reviews,
            pins,
            active,
        ),
        blocked: null,
    };
}

export async function acceptReturn(workspace, bundle, pins = []) {
    const { active, blocked } = await inspectWorkspace(workspace, pins);
    assert(!blocked, blocked);
    await verifyBundle(workspace.seed, bundle, pins, active);
    const next = clone(workspace);
    next.bundles[bundle.job_id] = clone(bundle);
    // Any returned revision invalidates the prior local decision, even if identical.
    delete next.reviews[bundle.job_id];
    serialize(next);
    return next;
}

export async function recordReview(
    workspace,
    id,
    decision,
    reviewer,
    note,
    pins = [],
) {
    const { active, blocked } = await inspectWorkspace(workspace, pins);
    assert(!blocked, blocked);
    assert(
        workspace.bundles[id],
        "Run or import this job before reviewing it.",
    );
    const next = clone(workspace);
    next.reviews[id] = await reviewBundle(
        workspace.seed,
        workspace.bundles[id],
        decision,
        reviewer,
        note,
        pins,
        active,
    );
    serialize(next);
    return next;
}

export async function appendEvent(workspace, type, payload, pins = []) {
    await inspectWorkspace(workspace, pins);
    const next = clone(workspace);
    const body = {
        sequence: next.history.length + 1,
        previous: next.history.at(-1)?.digest || "0".repeat(64),
        type,
        payload: clone(payload),
    };
    next.history.push({ ...body, digest: await hashObject(body) });
    await inspectWorkspace(next, pins); // Full validation and the byte bound happen before the caller commits anything.
    return next;
}

export async function promote(workspace, pins = []) {
    const { docket, blocked } = await inspectWorkspace(workspace, pins);
    assert(
        !blocked && docket.promotable,
        "Chronicle HOLD: finish accepted reviews, baseline and stress gates first.",
    );
    return appendEvent(
        workspace,
        "promote",
        {
            seed: workspace.seed,
            bundles: workspace.bundles,
            reviews: workspace.reviews,
        },
        pins,
    );
}

export async function nextMission(workspace, capability, pins = []) {
    const { active } = await inspectWorkspace(workspace, pins);
    const prior = active.get(capability);
    assert(
        prior,
        "Only an active reviewed capability can seed the next mission.",
    );
    const { schema, ...input } = prior.seed;
    const seed = makeSeed({
        ...input,
        objective:
            `Extend the reviewed capability with a new stress probe. ${input.objective}`.slice(
                0,
                2000,
            ),
        shock: input.shock === 50 ? 10 : Math.min(50, input.shock + 10),
        parents: [capability],
    });
    let next = { ...newWorkspace(seed), history: clone(workspace.history) };
    // Reuse exactly one unchanged benchmark; new source and stress jobs require new execution and review.
    const reused = await executeJob(
        seed,
        "benchmark",
        { type: "reuse", capability, job: "benchmark" },
        pins,
        active,
    );
    next = await acceptReturn(next, reused, pins);
    return next;
}

export async function exportDossier(workspace, pins = []) {
    const { docket, blocked } = await inspectWorkspace(workspace, pins);
    assert(!blocked, blocked);
    const plan = await compile(workspace.seed);
    return {
        schema: PROTOCOL + ".dossier",
        seed: workspace.seed,
        docket,
        jobs: plan.jobs,
        bundles: workspace.bundles,
        reviews: workspace.reviews,
        jobSpecURI_plans: await Promise.all(
            plan.jobs.map(async (job) => ({
                job_id: job.id,
                filename: `${job.id}-job-spec.json`,
                sha256: await hashObject(job),
                jobSpecURI: null,
                state: "local-unpublished-unfunded",
                settlement: null,
                next_step:
                    "Publish and verify the exact JobSpec bytes on an operator-selected content store, then configure and authorize a compatible AGIJobManager deployment separately.",
            })),
        ),
        nft_metadata_plan: {
            name: "Nova-Seed · " + workspace.seed.objective.slice(0, 100),
            description:
                "Proof-bound metadata plan; no token is minted and no ownership or financial right is asserted.",
            seed_hash: plan.seed_hash,
            minted: false,
            capability_state: docket.promotable
                ? "eligible-for-local-promotion"
                : "HOLD",
        },
        chronicle_head: workspace.history.at(-1)?.digest || null,
    };
}
