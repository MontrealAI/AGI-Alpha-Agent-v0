// SPDX-License-Identifier: Apache-2.0
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
    SECTORS,
    DEFAULT_CONFIG,
    MAX_PORTABLE_BYTES,
    serializePortableJSON,
    allocateEnvelope,
    quadrillionsToDollars,
    validateScenario,
    validateConfig,
    compareArchitectures,
    searchArchitectures,
    proofGates,
    buildEvidence,
    verifyEvidence,
    buildDossier,
    emptyChronicle,
    appendChronicle,
    verifyChronicle,
    exportWorkspace,
    restoreWorkspace,
} from "../../docs/assets/insight/engine.mjs";
import { hashObject } from "../../docs/assets/ascension/crypto.mjs";
const scenarios = JSON.parse(
    fs.readFileSync(
        new URL("../../docs/assets/insight/scenarios.json", import.meta.url),
    ),
);
const clone = (value) => structuredClone(value);

test("exact envelope allocation conserves amounts beyond safe Number precision", () => {
    for (const amount of [
        "0",
        "1",
        "97",
        "15000000000000001",
        "999999999999999999999",
    ]) {
        const rows = allocateEnvelope(amount, scenarios[0].weights_bps);
        assert.equal(
            rows.reduce((sum, row) => sum + BigInt(row.scenario_usd), 0n),
            BigInt(amount),
        );
        for (const row of rows) {
            const exact = BigInt(amount) * BigInt(row.weight_bps);
            const rounded = BigInt(row.scenario_usd) * 10000n;
            assert.ok(exact - rounded < 10000n && rounded - exact < 10000n);
        }
    }
    assert.equal(quadrillionsToDollars("15.001"), "15001000000000000");
    for (const bad of ["-1", "1e4", "1.0001", " 15 ", "Infinity"])
        assert.throws(() => quadrillionsToDollars(bad));
    assert.throws(() =>
        allocateEnvelope(15000000000000000, scenarios[0].weights_bps),
    );
    assert.throws(() => allocateEnvelope("01", scenarios[0].weights_bps));
    assert.throws(() =>
        allocateEnvelope("15", { ...scenarios[0].weights_bps, Energy: 1500 }),
    );
});

test("scenario and architecture input boundaries reject ambiguous or unbounded data", () => {
    for (const mutate of [
        (s) => (s.extra = true),
        (s) => (s.sources[0].url = "javascript:alert(1)"),
        (s) => (s.sources[0].url = "https://user:secret@example.com"),
        (s) => (s.claims[0].source_ids = ["missing"]),
        (s) => (s.claims[0].source_ids = ["fixture", "fixture"]),
        (s) => (s.workload.holdout[0].id = s.workload.training[0].id),
        (s) => (s.workload.training[0].minutes = NaN),
        (s) => s.workload.training.forEach((t) => (t.valid = true)),
        (s) => (s.sources[0].text = "x".repeat(4001)),
        (s) => (s.workload.training[0].due = 0),
    ]) {
        const value = clone(scenarios[0]);
        mutate(value);
        assert.throws(() => validateScenario(value));
    }
    for (const config of [
        { ...DEFAULT_CONFIG, agents: 1.5 },
        { ...DEFAULT_CONFIG, quorum: 5 },
        { ...DEFAULT_CONFIG, validators: 1 },
        { ...DEFAULT_CONFIG, budget: 99 },
        { ...DEFAULT_CONFIG, extra: 1 },
    ])
        assert.throws(() => validateConfig(config));
});

for (const scenario of scenarios) {
    test(`${scenario.id}: deterministic event schedules conserve budget, resource exclusivity and quorum independence`, () => {
        const report = compareArchitectures(scenario);
        assert.deepEqual(compareArchitectures(scenario), report);
        assert.ok(proofGates(report).every((g) => g.passed));
        for (const split of ["training", "holdout"])
            for (const variant of ["baseline", "candidate"]) {
                const cfg = report[`${variant}_config`],
                    result = report[split][variant];
                const admitted = result.rows.filter((r) => r.start !== null);
                assert.equal(
                    result.metrics.reserved_credits,
                    admitted.reduce((sum, r) => sum + r.cost, 0) +
                        cfg.agents * 8 +
                        cfg.validators * 6,
                );
                assert.equal(
                    result.metrics.reserved_credits +
                        result.metrics.remaining_credits,
                    cfg.budget,
                );
                assert.ok(result.metrics.remaining_credits >= 0);
                for (let id = 0; id < cfg.agents; id++) {
                    const jobs = admitted
                        .filter((r) => r.worker === id)
                        .sort((a, b) => a.start - b.start);
                    jobs.forEach((row, i) => {
                        assert.ok(row.start >= row.arrival);
                        assert.equal(
                            row.execution_end - row.start,
                            row.minutes,
                        );
                        if (i)
                            assert.ok(row.start >= jobs[i - 1].execution_end);
                    });
                }
                for (let id = 0; id < cfg.validators; id++) {
                    const reviews = admitted
                        .flatMap((r) => r.reviewers)
                        .filter((r) => r.id === id)
                        .sort((a, b) => a.start - b.start);
                    reviews.forEach((review, i) => {
                        if (i) assert.ok(review.start >= reviews[i - 1].end);
                    });
                }
                for (const row of admitted) {
                    assert.equal(row.reviewers.length, cfg.quorum);
                    assert.equal(
                        new Set(row.reviewers.map((r) => r.group)).size,
                        cfg.quorum,
                    );
                    assert.ok(
                        row.reviewers.every(
                            (r) =>
                                r.start >= row.execution_end &&
                                r.end - r.start === row.review_minutes,
                        ),
                    );
                    if (row.status === "accepted") {
                        assert.ok(row.end <= row.due && row.end <= cfg.horizon);
                        assert.ok(row.valid);
                    }
                }
                const signed = admitted
                    .filter((r) =>
                        ["accepted", "late", "beyond-horizon"].includes(
                            r.status,
                        ),
                    )
                    .sort((a, b) => a.end - b.end);
                signed.forEach((row, i) => {
                    assert.ok(row.end >= row.review_end + 2);
                    if (i) assert.ok(row.end >= signed[i - 1].end + 2);
                });
            }
    });
}

test("proof gates expose under-quorum, correlated, capacity-starved and budget-starved designs", () => {
    const bad = compareArchitectures(scenarios[0], {
        ...DEFAULT_CONFIG,
        quorum: 1,
    });
    assert.ok(bad.holdout.candidate.metrics.unsafe_accepts > 0);
    assert.equal(
        proofGates(bad).find((g) => g.id === "independence").passed,
        false,
    );
    assert.equal(proofGates(bad).find((g) => g.id === "safety").passed, false);
    const correlated = compareArchitectures(scenarios[0], {
        ...DEFAULT_CONFIG,
        groups: 1,
    });
    assert.ok(
        correlated.training.candidate.rows.every(
            (r) => r.status === "blocked-independence",
        ),
    );
    assert.equal(correlated.training.candidate.metrics.useful, 0);
    for (const config of [
        { ...DEFAULT_CONFIG, operator_slots: 0 },
        { ...DEFAULT_CONFIG, budget: 100 },
    ])
        assert.ok(
            proofGates(compareArchitectures(scenarios[0], config)).some(
                (g) => !g.passed,
            ),
        );
});

test("architecture selection is based on training only and returns the nondominated frontier", () => {
    const first = searchArchitectures(scenarios[0]);
    const changed = clone(scenarios[0]);
    changed.workload.holdout.forEach((task) => {
        task.minutes = 60;
        task.due = task.arrival + 1;
    });
    const second = searchArchitectures(changed);
    assert.equal(first.candidates.length, 18);
    assert.deepEqual(first.selected, second.selected);
    assert.notDeepEqual(first.evaluation.holdout, second.evaluation.holdout);
    for (const row of first.frontier)
        assert.ok(
            !first.candidates.some(
                (other) =>
                    other.training.useful >= row.training.useful &&
                    other.training.reserved_credits <=
                        row.training.reserved_credits &&
                    (other.training.useful > row.training.useful ||
                        other.training.reserved_credits <
                            row.training.reserved_credits),
            ),
        );
});

test("replay rejects tampered outputs, declared pass flags, extra fields and stale inputs even with recomputed hashes", async () => {
    const original = await buildEvidence(scenarios[0], DEFAULT_CONFIG);
    assert.equal(
        (
            await verifyEvidence(original, {
                scenario: scenarios[0],
                config: DEFAULT_CONFIG,
            })
        ).passed,
        true,
    );
    for (const mutate of [
        (b) => (b.comparison.holdout.candidate.metrics.useful = 999),
        (b) => (b.gates[0].passed = false),
        (b) => (b.passed = true),
        (b) => (b.scope = "independently-certified"),
    ]) {
        const tampered = clone(original);
        mutate(tampered);
        const { digest, ...body } = tampered;
        tampered.digest = await hashObject(body);
        await assert.rejects(() => verifyEvidence(tampered), /replay differs/);
    }
    await assert.rejects(
        () =>
            verifyEvidence(original, {
                scenario: scenarios[0],
                config: { ...DEFAULT_CONFIG, agents: 5 },
            }),
        /stale/,
    );
    const changed = clone(scenarios[0]);
    changed.envelope_usd = "15000000000000001";
    await assert.rejects(
        () =>
            verifyEvidence(original, {
                scenario: changed,
                config: DEFAULT_CONFIG,
            }),
        /stale/,
    );
    const unsafe = await buildEvidence(scenarios[0], {
        ...DEFAULT_CONFIG,
        quorum: 1,
    });
    assert.equal((await verifyEvidence(unsafe)).passed, false);
    await assert.rejects(
        () =>
            appendChronicle(emptyChronicle(), {
                action: "promote",
                bundle: unsafe,
                note: "Operator examined this unsafe architecture.",
            }),
        /failed model gate/,
    );
});

test("Chronicle requires review, rejects duplication and tampering, preserves revocation through recovery", async () => {
    const bundle = await buildEvidence(scenarios[0], DEFAULT_CONFIG);
    const promotion = {
        action: "promote",
        bundle,
        note: "Reviewed independent groups and all holdout rows; operational evidence remains outstanding.",
    };
    await assert.rejects(
        () => appendChronicle(emptyChronicle(), { ...promotion, note: "yes" }),
        /review note/,
    );
    const chronicle = await appendChronicle(emptyChronicle(), promotion);
    assert.equal((await verifyChronicle(chronicle)).active.length, 1);
    await assert.rejects(
        () => appendChronicle(chronicle, promotion),
        /Duplicate/,
    );
    const tampered = clone(chronicle);
    tampered.events[0].note =
        "A different operator note that was not recorded.";
    await assert.rejects(() => verifyChronicle(tampered), /hash mismatch/);
    const revoked = await appendChronicle(chronicle, {
        action: "revoke",
        digest: bundle.digest,
        note: "Operational pilot did not reproduce the fixture improvement.",
    });
    assert.equal((await verifyChronicle(revoked)).active.length, 0);
    assert.equal(Object.keys(revoked.bundles).length, 1);
    const recovery = await exportWorkspace(
        scenarios[0],
        DEFAULT_CONFIG,
        revoked,
    );
    assert.deepEqual(await restoreWorkspace(recovery), recovery);
    recovery.scenario.question = "Tampered scenario question.";
    await assert.rejects(() => restoreWorkspace(recovery), /digest mismatch/);
});

test("downloaded recovery bytes remain importable after multiple promotions", async () => {
    let chronicle = emptyChronicle();
    for (const scenario of scenarios) {
        const bundle = await buildEvidence(scenario, DEFAULT_CONFIG);
        chronicle = await appendChronicle(
            chronicle,
            {
                action: "promote",
                bundle,
                note: "Checked reviewer independence and the complete holdout results.",
            },
            { scenario, config: DEFAULT_CONFIG },
        );
    }
    const workspace = await exportWorkspace(
        scenarios[2],
        DEFAULT_CONFIG,
        chronicle,
    );
    assert.ok(
        Buffer.byteLength(JSON.stringify(workspace, null, 2)) >
            MAX_PORTABLE_BYTES,
    );
    const downloaded = serializePortableJSON(workspace);
    assert.ok(Buffer.byteLength(downloaded) <= MAX_PORTABLE_BYTES);
    assert.deepEqual(await restoreWorkspace(JSON.parse(downloaded)), workspace);
    assert.equal(
        serializePortableJSON({ small: true }),
        '{\n  "small": true\n}\n',
    );
    const boundary = { text: "x".repeat(MAX_PORTABLE_BYTES - 11) };
    assert.equal(
        Buffer.byteLength(serializePortableJSON(boundary)),
        MAX_PORTABLE_BYTES,
    );
    assert.throws(
        () => serializePortableJSON({ text: "é".repeat(125000) }),
        /250 KB/,
    );
});

test("promotion cannot strand a history that fits alone but exceeds the recovery envelope", async () => {
    let chronicle = emptyChronicle();
    for (let i = 0; i < 4; i++) {
        const config = { ...DEFAULT_CONFIG, budget: 1800 + i };
        const bundle = await buildEvidence(scenarios[0], config);
        chronicle = await appendChronicle(
            chronicle,
            {
                action: "promote",
                bundle,
                note: "Checked the complete holdout and all negative controls.",
            },
            { scenario: scenarios[0], config },
        );
    }
    const scenario = clone(scenarios[0]);
    for (let i = 0; i < 4; i++)
        scenario.sources.push({
            id: `extra-${i}`,
            title: "Additional context",
            kind: "user-supplied",
            text: "x".repeat(4000),
        });
    const bundle = await buildEvidence(scenario, DEFAULT_CONFIG);
    const event = {
        action: "promote",
        bundle,
        note: "Checked the expanded source context and all holdout results.",
    };
    const standalone = await appendChronicle(chronicle, event);
    assert.equal((await verifyChronicle(standalone)).active.length, 5);
    await assert.rejects(
        () => exportWorkspace(scenario, DEFAULT_CONFIG, standalone),
        /250 KB/,
    );
    const before = clone(chronicle);
    await assert.rejects(
        () =>
            appendChronicle(chronicle, event, {
                scenario,
                config: DEFAULT_CONFIG,
            }),
        /250 KB/,
    );
    assert.deepEqual(chronicle, before);
    const saved = await exportWorkspace(scenario, DEFAULT_CONFIG, chronicle);
    assert.deepEqual(
        await restoreWorkspace(JSON.parse(serializePortableJSON(saved))),
        saved,
    );
});

test("dossiers maintain typed graph referential integrity and produce honest executable research inputs", () => {
    for (const scenario of scenarios) {
        const dossier = buildDossier(scenario, DEFAULT_CONFIG);
        const ids = new Set(dossier.graph.nodes.map((n) => n.id));
        assert.equal(ids.size, dossier.graph.nodes.length);
        assert.equal(dossier.economic_value_verified_usd, "0");
        assert.equal(dossier.briefs.length, scenario.claims.length);
        assert.equal(dossier.missions.length, scenario.claims.length);
        for (const edge of dossier.graph.edges)
            assert.ok(ids.has(edge.from) && ids.has(edge.to));
        for (const mission of dossier.missions) {
            assert.equal(mission.work.kind, "research");
            assert.ok(mission.goal.length <= 2000);
            assert.ok(
                mission.work.sources.every((s) =>
                    s.text.includes("unverified input"),
                ),
            );
        }
        assert.ok(
            dossier.graph.nodes
                .filter((n) => n.node_type === "claim")
                .every((n) => n.status === "external-evidence-required"),
        );
        assert.equal(SECTORS.length, 12);
    }
});
