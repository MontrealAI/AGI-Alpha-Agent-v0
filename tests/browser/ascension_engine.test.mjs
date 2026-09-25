// SPDX-License-Identifier: Apache-2.0
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
    analyseScenario,
    makeGenome,
    councilChecks,
    curveQuote,
    SettlementLab,
    tokenUnits,
    tokenDecimal,
    runSettlement,
    riskAudit,
    PAPER_RISKS,
    actionRisk,
    quadraticBallot,
    upgradeStatus,
    replicatorField,
    evolveStrategies,
    hawkDove,
    architectSearch,
    stakeDecision,
} from "../../docs/assets/ascension/engine.mjs";
import {
    sealSeed,
    openSeed,
    hashObject,
    canonicalJSON,
} from "../../docs/assets/ascension/crypto.mjs";

const scenarios = JSON.parse(
    fs.readFileSync(
        new URL("../../docs/assets/ascension/scenarios.json", import.meta.url),
    ),
);
const near = (a, b, tolerance = 1e-9) =>
    assert.ok(Math.abs(a - b) <= tolerance, `${a} differs from ${b}`);
const reviewers = [
    { id: "budget-verifier", passed: true },
    { id: "capacity-verifier", passed: true },
];

test("all flagship cases have useful executable portfolios and independently valid capacity plans", () => {
    for (const scenario of scenarios) {
        const analysis = analyseScenario(scenario);
        assert.ok(analysis.selected.length > 1);
        assert.ok(
            analysis.portfolio.evidence.totals.value >
                analysis.portfolio.evidence.baseline.value,
        );
        assert.ok(councilChecks(analysis).every((check) => check.passed));
        assert.equal(
            makeGenome(analysis).fusion_plan.selected.length,
            analysis.selected.length,
        );
        const report = runSettlement(analysis);
        assert.equal(report.minted, "0");
        assert.equal(report.conservation, true);
        assert.equal(report.settled_jobs, analysis.selected.length);
    }
});

test("budget/effort tampering and duplicate selections cannot receive passing council checks", () => {
    for (const corrupt of [
        (a) => a.selected[0].cost--,
        (a) => a.selected[0].effort[0]++,
        (a) => a.selected.push(a.selected[0]),
        (a) => a.portfolio.evidence.totals.value++,
        (a) => (a.schedule.evidence.operations[0].machine = "wrong-worker"),
        (a) => (a.schedule.evidence.operations[0].start = -1),
    ]) {
        const analysis = analyseScenario(scenarios[0]);
        corrupt(analysis);
        assert.ok(councilChecks(analysis).some((c) => !c.passed));
        assert.throws(() => runSettlement(analysis));
    }
});

test("empty feasible portfolios and malformed imported scenarios fail clearly", () => {
    const analysis = analyseScenario(scenarios[0], { budget: 1 });
    assert.equal(analysis.selected.length, 0);
    assert.equal(analysis.schedule, null);
    assert.throws(() => makeGenome(analysis));
    assert.throws(() => runSettlement(analysis));
    for (const change of [
        (s) => (s.opportunities[0].id = undefined),
        (s) => (s.opportunities[0].cost = NaN),
        (s) => (s.opportunities[0].risk = 1.5),
        (s) => (s.opportunities[0].effort = [1, 2]),
        (s) => (s.budget = -10),
        (s) => (s.schema = "unknown"),
        (s) => s.opportunities.push(s.opportunities[0]),
    ]) {
        const value = structuredClone(scenarios[0]);
        change(value);
        assert.throws(() => analyseScenario(value));
    }
});

test("bonding-curve batch quotes equal independent per-lot sums and buy/sell round trips", () => {
    for (const supply of [0, 1, 17, 231])
        for (const lots of [1, 2, 19]) {
            const base = "1.000000000000000001",
                slope = ".2";
            assert.throws(() => tokenUnits(slope));
            const quote = curveQuote({ supply, lots, base, slope: "0.2" });
            let expected = 0n;
            for (let i = 0; i < lots; i++)
                expected +=
                    tokenUnits(base) + tokenUnits("0.2") * BigInt(supply + i);
            assert.equal(BigInt(quote.units), expected);
            const redeem = curveQuote({
                supply: supply + lots,
                lots,
                base,
                slope: "0.2",
                direction: "sell",
            });
            assert.equal(redeem.units, quote.units);
        }
    assert.throws(() =>
        curveQuote({
            supply: 2,
            lots: 3,
            base: "1",
            slope: "0",
            direction: "sell",
        }),
    );
    assert.throws(() =>
        curveQuote({ supply: 1000000, lots: 1, base: "1", slope: "0" }),
    );
});

test("18-decimal settlement conserves supply, caps both mint legs and rejects replay atomically", () => {
    const ledger = new SettlementLab({
        deposit: "100",
        emission_cap: "3.000000000000000001",
    });
    const state = ledger.settle({
        id: "first",
        gross: "20",
        certified_value: "100",
        reviewers,
    });
    assert.equal(state.burned, "0.2");
    assert.equal(state.minted, "3");
    assert.equal(state.treasury, "1.5");
    assert.equal(state.workers, "21.3");
    assert.equal(state.escrow, "80");
    assert.equal(state.supply, "102.8");
    assert.equal(state.events[0].emission_capped, true);
    for (const bad of [
        { id: "first", gross: "20", reviewers },
        { id: "second", gross: "81", reviewers },
        { id: "second", gross: "10", reviewers: [reviewers[0], reviewers[0]] },
        {
            id: "second",
            gross: "10",
            reviewers: [reviewers[0], { ...reviewers[1], passed: false }],
        },
    ]) {
        assert.throws(() => ledger.settle(bad));
        assert.deepEqual(ledger.snapshot(), state);
    }
    for (const value of [
        "0",
        "0.000000000000000001",
        "9007199254740993.123456789012345678",
    ])
        assert.equal(tokenDecimal(tokenUnits(value)), value);
    for (const value of [
        "-1",
        "1e3",
        "1.0000000000000000001",
        "Infinity",
        1,
        "0x10",
    ])
        assert.throws(() => tokenUnits(value));
});

test("paper risk scores are recomputed, and an action budget is not an aggregate safety proof", () => {
    const audit = riskAudit(PAPER_RISKS);
    near(audit.aggregate, 0.393045);
    near(audit.rows[0].coverage, 0.38);
    near(audit.rows[0].residual, 0.10912);
    assert.equal(audit.admitted, false);
    const risk = actionRisk(1e-9, 1e12);
    near(risk.expected_failures, 1000);
    assert.equal(risk.union_bound, 1);
    assert.equal(risk.independent_probability, 1);
    near(risk.union_budget_per_action, 1e-15, 1e-28);
    near(actionRisk(0.1, 2).independent_probability, 0.19);
    assert.equal(actionRisk(0, 20).independent_probability, 0);
});

test("Hawk–Dove dynamics agree with the analytic derivative and equilibrium V/C", () => {
    const value = 1,
        cost = 2,
        x = 0.3;
    const field = replicatorField(
        [
            [(value - cost) / 2, value],
            [0, value / 2],
        ],
        [x, 1 - x],
    );
    near(field.derivative[0], (x * (1 - x) * (value - cost * x)) / 2);
    near(field.derivative[0] + field.derivative[1], 0);
    const result = hawkDove(value, cost);
    assert.equal(result.equilibrium, 0.5);
    near(result.history.at(-1).mix[0], 0.5, 0.005);
    assert.equal(hawkDove(3, 2).equilibrium, 1);
});

test("a zero-sum cycle preserves the simplex and does not manufacture convergence or welfare growth", () => {
    const matrix = [
        [0, -1, 1],
        [1, 0, -1],
        [-1, 1, 0],
    ];
    const history = evolveStrategies(matrix, [0.6, 0.25, 0.15]);
    for (const point of history) {
        near(
            point.mix.reduce((a, b) => a + b, 0),
            1,
        );
        assert.ok(point.mix.every((v) => v >= 0 && v <= 1));
        near(point.welfare, 0);
        near(
            point.mix.reduce((a, b) => a * b, 1),
            0.6 * 0.25 * 0.15,
            1e-7,
        );
    }
});

test("quadratic budgets and the complete eight-day gate cannot be bypassed", () => {
    assert.deepEqual(quadraticBallot([3, -2, 1], 14), {
        spent: 14,
        remaining: 0,
        admitted: true,
        votes: [3, -2, 1],
    });
    assert.equal(quadraticBallot([4, 1], 14).admitted, false);
    const base = {
        queued_at: 100,
        now: 100 + 8 * 86400,
        approved: true,
        policy_valid: true,
    };
    assert.equal(upgradeStatus(base).executable, true);
    for (const change of [
        { now: base.now - 1 },
        { approved: false },
        { policy_valid: false },
    ])
        assert.equal(upgradeStatus({ ...base, ...change }).executable, false);
    assert.throws(() => upgradeStatus({ ...base, delay_days: 7 }));
});

test("stake admission and exact severity slashes require both identity and sufficient collateral", () => {
    const request = {
        name: "agent.alpha.agent.agi.eth",
        stake: "100.000000000000000005",
        minimum: "10",
        severity: 2000,
        attested: true,
    };
    const result = stakeDecision(request);
    assert.equal(result.eligible, true);
    assert.equal(result.slash, "20.000000000000000001");
    assert.equal(result.remaining, "80.000000000000000004");
    assert.equal(
        stakeDecision({ ...request, attested: false }).eligible,
        false,
    );
    assert.equal(stakeDecision({ ...request, stake: "9" }).eligible, false);
    assert.equal(stakeDecision({ ...request, severity: 10000 }).remaining, "0");
    assert.throws(() => stakeDecision({ ...request, severity: 10001 }));
});

test("actual funding deposit drives escrow and excess funding remains conserved", () => {
    const analysis = analyseScenario(scenarios[0]);
    const result = runSettlement(analysis, {
        deposit: "123.000000000000000001",
    });
    assert.equal(result.escrow, "23.000000000000000001");
    assert.equal(result.supply, "122.000000000000000001");
    assert.throws(() => runSettlement(analysis, { deposit: "99" }));
});

test("Architect policy candidates obey their declared budgets and do not change source values", () => {
    const before = structuredClone(scenarios[0]);
    const candidates = architectSearch(before);
    assert.equal(candidates.length, 20);
    assert.ok(candidates.some((p) => p.frontier));
    for (const policy of candidates) {
        assert.ok(
            policy.cost <= policy.budget && policy.risk <= policy.risk_limit,
        );
        assert.equal(
            policy.value,
            before.opportunities
                .filter((p) => policy.selected.includes(p.id))
                .reduce((s, p) => s + p.value, 0),
        );
    }
    assert.deepEqual(before, scenarios[0]);
});

test("Nova-Seeds encrypt the actual genome, recover exactly, and authenticate all header fields", async () => {
    const payload = makeGenome(analyseScenario(scenarios[0]));
    const passphrase = "a private recovery phrase for this test only";
    const capsule = await sealSeed(payload, passphrase);
    assert.ok(!JSON.stringify(capsule).includes(payload.title));
    assert.deepEqual(await openSeed(capsule, passphrase), payload);
    const second = await sealSeed(payload, passphrase);
    assert.notEqual(second.iv, capsule.iv);
    assert.notEqual(second.salt, capsule.salt);
    assert.notEqual(second.commitment, capsule.commitment);
    await assert.rejects(openSeed(capsule, "a different private passphrase"));
    for (const change of [
        { commitment: "a".repeat(64) },
        { iterations: 1 },
        { iv: second.iv },
        { salt: second.salt },
        {
            ciphertext:
                capsule.ciphertext.slice(0, 8) +
                "AAAA" +
                capsule.ciphertext.slice(12),
        },
        { unexpected: true },
    ])
        await assert.rejects(openSeed({ ...capsule, ...change }, passphrase));
    await assert.rejects(sealSeed(payload, "short"));
    assert.equal(
        await hashObject({ b: 2, a: 1 }),
        await hashObject({ a: 1, b: 2 }),
    );
    assert.throws(() => canonicalJSON({ invalid: NaN }));
    assert.throws(() => canonicalJSON(new Array(2)));
    const sparse = [1, 2];
    delete sparse[1];
    sparse.extra = 3;
    assert.throws(() => canonicalJSON(sparse));
    const cycle = {};
    cycle.self = cycle;
    assert.throws(() => canonicalJSON(cycle));
});
