/* SPDX-License-Identifier: Apache-2.0 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { spawnSync } from "node:child_process";
import {
    compare,
    rank,
    roundRatio,
    validate,
} from "../../docs/cross_industry_alpha_factory/assets/engine.mjs";
import { parseJSON } from "../../docs/cross_industry_alpha_factory/assets/json.mjs";
const fixture = JSON.parse(
    fs.readFileSync("docs/cross_industry_alpha_factory/assets/example.json")
);
test("weights, thresholds, dominance and ASCII ties are deterministic", async () => {
    const r = await compare(fixture);
    assert.equal(r.selected_id, "routing");
    assert.equal(r.ranking[0].score, 74.5);
    assert.equal(r.ranking[2].eligible, false);
    assert.equal(r.ranking[2].rank, null);
    assert.equal(roundRatio(1, 128), 0.007813);
    const t = structuredClone(fixture);
    t.opportunities = [
        { ...t.opportunities[0], id: "b" },
        { ...t.opportunities[0], id: "A" },
    ];
    assert.deepEqual(
        rank(t).ranking.map((r) => r.id),
        ["A", "b"]
    );
    assert.ok(rank(t).ranking.every((r) => r.pareto_optimal));
});
test("strict bounded inputs reject coercion, unknown keys and malformed text", () => {
    for (const mutate of [
        (s) => (s.weights.benefit = true),
        (s) => (s.weights.risk = 1.2),
        (s) => (s.constraints.max_risk = 101),
        (s) => (s.opportunities[0].evidence = []),
        (s) => (s.opportunities[0].sector = " padded "),
        (s) => (s.opportunities[0].sector = "\ud800"),
        (s) => (s.opportunities[0].sector = "bad\u0000"),
        (s) => (s.extra = 1),
        (s) => (s.opportunities[1].id = s.opportunities[0].id),
    ]) {
        const s = structuredClone(fixture);
        mutate(s);
        assert.throws(() => validate(s));
    }
    for (const raw of ['{"a":1,"a":2}', '{"a":1.0}', '{"a":1e0}', '{"a":NaN}'])
        assert.throws(() => parseJSON(raw));
});
test("150 full reports and canonical hashes match original Python including Unicode and rounding", async () => {
    let seed = 19;
    const random = (n) => {
        seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
        return seed % n;
    };
    const cases = [fixture];
    for (let i = 1; i < 150; i++) {
        const s = structuredClone(fixture);
        for (const key of Object.keys(s.weights))
            s.weights[key] = 1 + random(100);
        s.constraints.max_risk = random(101);
        s.constraints.min_confidence = random(101);
        s.opportunities = Array.from({ length: 1 + random(12) }, (_, j) => ({
            id: (j % 2 ? "A" : "z") + j,
            sector: "Énergie 🍁",
            opportunity: "Supplied assessment " + j,
            benefit: random(101),
            confidence: random(101),
            effort: random(101),
            risk: random(101),
            evidence: ["Unverified note " + j],
        }));
        cases.push(s);
    }
    const run = spawnSync(
        process.env.PYTHON || "python3",
        [
            "-c",
            "import json,sys\nfrom alpha_factory_v1.demos.cross_industry_alpha_factory.opportunity_comparison import compare_opportunities\nprint(json.dumps([compare_opportunities(s) for s in json.load(sys.stdin)],ensure_ascii=False))",
        ],
        {
            input: JSON.stringify(cases),
            encoding: "utf8",
            maxBuffer: 16 * 1024 * 1024,
        }
    );
    assert.equal(run.status, 0, run.stderr);
    assert.deepEqual(
        await Promise.all(cases.map(compare)),
        JSON.parse(run.stdout)
    );
});

test("ignored report floats do not relax input integer tokens", () => {
    assert.equal(
        parseJSON('{"input":{"rating":1},"report":{"score":74.5}}', true, [
            "report",
        ]).report.score,
        74.5
    );
    for (const raw of [
        '{"input":{"rating":1.0},"report":{"score":74.5}}',
        '{"input":{"rating":1e0},"report":{}}',
        '{"report":{"score":NaN}}',
    ])
        assert.throws(() => parseJSON(raw, true, ["report"]));
});
