// SPDX-License-Identifier: Apache-2.0
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
    hashObject,
    canonicalJSON,
} from "../../docs/assets/ascension/crypto.mjs";
import {
    PLAYBOOKS,
    makeSeed,
    compile,
    newWorkspace,
    executeJob,
    verifyBundle,
    acceptReturn,
    recordReview,
    inspectWorkspace,
    promote,
    appendEvent,
    nextMission,
    exportDossier,
    serialize,
    parse,
} from "../../docs/assets/bloom/engine.mjs";

const books = JSON.parse(
    await readFile(
        new URL("../../docs/assets/bloom/playbooks.json", import.meta.url),
    ),
);
const copy = (value) => structuredClone(value);
function seed(id = "nova", overrides = {}) {
    const book = books[id];
    return makeSeed({
        playbook: id,
        objective: book.objective,
        claim: book.claim,
        mission: book.mission,
        shock: 20,
        parents: [],
        ...overrides,
    });
}
async function completed(input = seed(), initial = null) {
    let workspace = initial || newWorkspace(input);
    for (const job of (await compile(input)).jobs) {
        if (!workspace.bundles[job.id]) {
            const { active } = await inspectWorkspace(workspace);
            workspace = await acceptReturn(
                workspace,
                await executeJob(
                    input,
                    job.id,
                    { type: "browser" },
                    [],
                    active,
                ),
            );
        }
        workspace = await recordReview(
            workspace,
            job.id,
            "accept",
            "Evidence reviewer",
            "Inspected exact inputs, baseline and replay. Accept computation only; source truth remains unproven.",
        );
    }
    return workspace;
}

for (const id of PLAYBOOKS)
    test(`${id}: real work → reviewed evidence → bounded capability`, async () => {
        let workspace = newWorkspace(seed(id));
        assert.equal(
            (await inspectWorkspace(workspace)).docket.promotable,
            false,
        );
        await assert.rejects(promote(workspace), /HOLD/);
        workspace = await completed(workspace.seed);
        const inspected = await inspectWorkspace(workspace);
        assert.equal(inspected.docket.promotable, true);
        assert.equal(inspected.docket.visionary_claim.status, "unproven");
        assert.equal(
            inspected.docket.visionary_claim.economic_value_verified,
            0,
        );
        const promoted = await promote(workspace);
        assert.equal((await inspectWorkspace(promoted)).active.size, 1);
        await assert.rejects(promote(promoted), /Duplicate/);
        const dossier = await exportDossier(promoted);
        assert.equal(dossier.nft_metadata_plan.minted, false);
        for (let i = 0; i < 3; i++) {
            const plan = dossier.jobSpecURI_plans[i];
            assert.equal(plan.jobSpecURI, null);
            assert.equal(plan.settlement, null);
            assert.equal(plan.sha256, await hashObject(dossier.jobs[i]));
        }
        assert.equal(
            (await inspectWorkspace(parse(serialize(promoted)))).active.size,
            1,
        );
    });

test("self-declared verdicts, altered outputs and wrong job bindings never open a gate", async () => {
    const input = seed();
    const bundle = await executeJob(input, "benchmark");
    await assert.rejects(
        verifyBundle(input, {
            ...bundle,
            validator_verdict: "accepted",
            replay_result: "pass",
        }),
        /fields/,
    );
    const altered = copy(bundle);
    altered.result.evidence.totals.value += 100000000;
    const { digest, ...body } = altered;
    altered.digest = await hashObject(body);
    await assert.rejects(verifyBundle(input, altered), /does not replay/);
    await assert.rejects(
        verifyBundle(input, { ...bundle, job_id: "source" }),
        /does not replay/,
    );
    await assert.rejects(
        verifyBundle(seed("omega"), bundle),
        /does not replay/,
    );
    await assert.rejects(
        verifyBundle(
            seed("nova", { claim: "Changed claim with identical work inputs" }),
            bundle,
        ),
        /does not replay/,
    );
    assert.equal(bundle.result.evidence.totals.value, 150);
    assert.equal(bundle.result.evidence.baseline.value, 120);
    assert.equal(bundle.result.evidence.examined_subsets, 16);
});

test("review decisions bind to the exact return and are invalidated by a new return", async () => {
    let workspace = await completed();
    workspace = await recordReview(
        workspace,
        "stress",
        "repair",
        "Reviewer",
        "Need a broader probe before acceptance.",
    );
    assert.equal((await inspectWorkspace(workspace)).docket.promotable, false);
    await assert.rejects(promote(workspace), /HOLD/);
    await assert.rejects(
        recordReview(workspace, "stress", "accept", "R", "yes"),
        /Reviewer/,
    );
    workspace = await recordReview(
        workspace,
        "stress",
        "reject",
        "Reviewer",
        "Reject this returned artifact within this scope.",
    );
    await assert.rejects(promote(workspace), /HOLD/);
    workspace = await acceptReturn(workspace, workspace.bundles.benchmark);
    assert.equal(workspace.reviews.benchmark, undefined);
    const stale = await completed();
    stale.reviews.source.bundle_hash = "0".repeat(64);
    await assert.rejects(inspectWorkspace(stale), /stale/);
});

test("accepted reviews cannot override a failed stress comparison", async () => {
    const workspace = await completed(seed("nova", { shock: 50 }));
    const { docket } = await inspectWorkspace(workspace);
    assert.equal(docket.gates.find((gate) => gate.id === "RSI").passed, true);
    assert.equal(
        docket.gates.find((gate) => gate.id === "MOVE37").passed,
        false,
    );
    assert.equal(docket.rows[2].measurement.delta, 0);
    await assert.rejects(promote(workspace), /HOLD/);
});

test("future missions reuse an exact benchmark; revocation closes the transitive lineage", async () => {
    let workspace = await promote(await completed());
    const root = workspace.history[0].digest;
    workspace = await nextMission(workspace, root);
    assert.equal(workspace.bundles.benchmark.origin.type, "reuse");
    assert.equal(Object.keys(workspace.bundles).length, 1);
    assert.equal(Object.keys(workspace.reviews).length, 0);
    assert.equal(workspace.seed.shock, 30);
    workspace = await promote(await completed(workspace.seed, workspace));
    const child = workspace.history.at(-1).digest;
    workspace = await nextMission(workspace, child);
    workspace = await promote(await completed(workspace.seed, workspace));
    assert.equal((await inspectWorkspace(workspace)).active.size, 3);
    const before = serialize(workspace);
    await assert.rejects(
        appendEvent(workspace, "revoke", { capability: root, reason: "bad" }),
        /reason/,
    );
    assert.equal(serialize(workspace), before);
    workspace = await appendEvent(workspace, "revoke", {
        capability: root,
        reason: "Original input assumptions were superseded by new measurements.",
    });
    const restored = parse(serialize(workspace));
    assert.equal((await inspectWorkspace(restored)).active.size, 0);
    assert.match((await inspectWorkspace(restored)).blocked, /revoked/);
    await assert.rejects(nextMission(restored, child), /active reviewed/);
});

test("reused evidence must match the exact mission and role", async () => {
    const workspace = await promote(await completed());
    const root = workspace.history[0].digest;
    const future = await nextMission(workspace, root);
    const { active } = await inspectWorkspace(future);
    const { schema, ...input } = future.seed;
    input.mission.work.budget = 130;
    await assert.rejects(
        executeJob(
            makeSeed(input),
            "benchmark",
            { type: "reuse", capability: root, job: "benchmark" },
            [],
            active,
        ),
        /different inputs/,
    );
    await assert.rejects(
        executeJob(
            future.seed,
            "source",
            { type: "reuse", capability: root, job: "benchmark" },
            [],
            active,
        ),
        /different inputs/,
    );
    await assert.rejects(
        executeJob(future.seed, "benchmark", {
            type: "reuse",
            capability: root,
            job: "benchmark",
        }),
        /unavailable/,
    );
});

test("history replays promotions and detects changed or reordered evidence", async () => {
    const workspace = await promote(await completed());
    const broken = copy(workspace);
    broken.history[0].payload.reviews.source.decision = "reject";
    await assert.rejects(inspectWorkspace(broken), /chain/);
    const { digest, ...body } = broken.history[0];
    broken.history[0].digest = await hashObject(body);
    await assert.rejects(inspectWorkspace(broken), /proof gates/);
    const duplicated = copy(workspace);
    duplicated.history.push(copy(duplicated.history[0]));
    await assert.rejects(inspectWorkspace(duplicated), /chain/);
    await assert.rejects(
        inspectWorkspace({ ...workspace, passed: true }),
        /fields/,
    );
});

test("native returns require a separately pinned key and a real signature", async () => {
    const input = seed();
    const fake = {
        schema: 1,
        public_key: "a".repeat(64),
        receipt: { canonical_body: "{}" },
    };
    await assert.rejects(
        executeJob(input, "benchmark", { type: "native", artifact: fake }),
        /Pin/,
    );
    await assert.rejects(
        executeJob(input, "benchmark", { type: "native", artifact: fake }, [
            fake.public_key,
        ]),
    );
});

test("bounded JSON and invalid inputs fail before state mutation", async () => {
    assert.throws(() => parse(" ".repeat(250001)), /250 KB/);
    assert.throws(() => serialize({ text: "é".repeat(125001) }), /250 KB/);
    const value = { entries: Array(17000).fill(1) };
    assert.deepEqual(parse(serialize(value)), value);
    assert.throws(() => seed("nova", { shock: NaN }), /whole percentage/);
    const mission = copy(books.nova.mission);
    mission.work.items[1].id = mission.work.items[0].id;
    assert.throws(() => seed("nova", { mission }), /unique/);
    assert.throws(
        () => seed("nova", { parents: ["unreviewed"] }),
        /dependencies/,
    );
    assert.throws(() => seed("nova", { unexpected: true }), /fields/);
    assert.equal(canonicalJSON(seed()), canonicalJSON(seed()));
});

test("forecast stress never enters training or changes policy selection", async () => {
    const input = seed("invention");
    const regular = (await executeJob(input, "benchmark")).result.evidence;
    const stress = (await executeJob(input, "stress")).result.evidence;
    assert.deepEqual(regular.training_scores, stress.training_scores);
    assert.equal(regular.selected, stress.selected);
    assert.notDeepEqual(regular.holdout_actual, stress.holdout_actual);
    assert.equal(regular.holdout_mae, 0);
    assert.equal(regular.baseline_mae, 5);
});
