import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { spawnSync } from "node:child_process";
import {
    evaluate,
    validate,
} from "../../docs/alpha_agi_business_2_v1/assets/engine.mjs";
import { parseJSON } from "../../docs/alpha_agi_business_2_v1/assets/json.mjs";
const fixture = JSON.parse(
    fs.readFileSync("docs/alpha_agi_business_2_v1/assets/example.json")
);
test("exact portfolio and evidence threshold", async () => {
    const r = await evaluate(fixture);
    assert.deepEqual(r.plan.selectedIds, ["onboarding", "support"]);
    assert.equal(r.plan.totalValuePoints, 21);
    assert.equal(
        r.research.opportunities.find((x) => x.id === "returns").reason,
        "insufficient_support"
    );
    const empty = structuredClone(fixture);
    empty.policy.effortHours = 0;
    assert.deepEqual((await evaluate(empty)).plan.selectedIds, []);
});
test("strict schema and integer parser reject unsafe coercion", () => {
    for (const mutate of [
        (s) => (s.policy.effortHours = true),
        (s) => (s.policy.maxProjects = 17),
        (s) => (s.extra = 1),
        (s) => (s.observations[0].source = "\ud800"),
        (s) => (s.observations[0].source = "bad\u0085"),
        (s) => (s.opportunities[0].evidenceIds = ["missing"]),
        (s) => (s.opportunities[0].evidenceIds = ["completion", "completion"]),
        (s) => (s.observations[1].id = s.observations[0].id),
    ]) {
        const s = structuredClone(fixture);
        mutate(s);
        assert.throws(() => validate(s));
    }
    for (const raw of ['{"a":1,"a":2}', '{"a":1.0}', '{"a":1e0}', '{"a":NaN}'])
        assert.throws(() => parseJSON(raw));
});
test("150 complete reports and both canonical digests match Python including Unicode source order", async () => {
    let seed = 211;
    const random = (n) => {
        seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
        return seed % n;
    };
    const cases = [fixture];
    for (let i = 1; i < 150; i++) {
        const s = structuredClone(fixture);
        s.policy = {
            effortHours: random(50),
            maxProjects: random(8),
            minSupportingSources: 1 + random(3),
        };
        s.observations = Array.from({ length: 8 }, (_, j) => ({
            id: "o-" + j,
            source: [" source \u3000", "\uffff", "🍁", "\ufeff", "é"][j % 5],
            metric: "Énergie 🍁",
            unit: "units",
            baseline: random(10),
            current: random(10),
            direction: random(2) ? "increase" : "decrease",
        }));
        s.opportunities = Array.from({ length: 1 + random(12) }, (_, j) => ({
            id: "p-" + j,
            title: "Supplied " + j,
            effortHours: 1 + random(20),
            valuePoints: random(10),
            evidenceIds: s.observations
                .filter(() => random(2))
                .map((r) => r.id),
        }));
        for (const row of s.opportunities)
            if (!row.evidenceIds.length) row.evidenceIds = ["o-0"];
        cases.push(s);
    }
    const run = spawnSync(
        process.env.PYTHON || "python3",
        [
            "-c",
            "import json,sys\nfrom alpha_factory_v1.demos.alpha_agi_business_2_v1.planning import evaluate\nprint(json.dumps([evaluate(s) for s in json.load(sys.stdin)],ensure_ascii=False))",
        ],
        {
            input: JSON.stringify(cases),
            encoding: "utf8",
            maxBuffer: 32 * 1024 * 1024,
        }
    );
    assert.equal(run.status, 0, run.stderr);
    const expected = JSON.parse(run.stdout);
    for (let i = 0; i < cases.length; i++)
        assert.deepEqual(await evaluate(cases[i]), expected[i], `case ${i}`);
});
