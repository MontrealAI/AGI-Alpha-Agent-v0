// SPDX-License-Identifier: Apache-2.0
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { runMission } from "../../docs/assets/portal/mission-engine.mjs";
const examples = JSON.parse(
    fs.readFileSync(
        new URL("../../docs/assets/portal/examples.json", import.meta.url),
    ),
);

test("allocation agrees with an independent two-constraint dynamic programming oracle", () => {
    let seed = 41;
    const random = (limit) => {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        return seed % limit;
    };
    for (let trial = 0; trial < 50; trial++) {
        const items = Array.from({ length: 7 }, (_, i) => ({
            id: `I${i}`,
            cost: 1 + random(8),
            value: random(20),
            risk: random(4),
        }));
        const budget = 15,
            max_risk = 5;
        let states = new Map([["0,0", 0]]);
        for (const item of items) {
            const next = new Map(states);
            for (const [key, value] of states) {
                const [cost, risk] = key.split(",").map(Number),
                    nc = cost + item.cost,
                    nr = risk + item.risk;
                if (nc <= budget && nr <= max_risk)
                    next.set(
                        `${nc},${nr}`,
                        Math.max(
                            next.get(`${nc},${nr}`) ?? -1,
                            value + item.value,
                        ),
                    );
            }
            states = next;
        }
        const result = runMission({
            goal: "Choose useful options",
            work: { kind: "allocation", items, budget, max_risk },
        });
        assert.equal(
            result.evidence.totals.value,
            Math.max(...states.values()),
        );
        assert.ok(
            result.evidence.totals.cost <= budget &&
                result.evidence.totals.risk <= max_risk,
        );
    }
});
test("invalid inputs cannot silently become a success or incompatible native mission", () => {
    for (const change of [
        (r) => (r.work.items[0].cost = 1.5),
        (r) => (r.work.items[0].risk = -1),
        (r) => (r.work.items[0].id = "has spaces"),
        (r) => (r.work.items[1].id = r.work.items[0].id),
        (r) => (r.work.extra = true),
        (r) => (r.goal = "a"),
        (r) => (r.seed = -1),
    ]) {
        const request = structuredClone(examples.allocation);
        change(request);
        assert.throws(() => runMission(request));
    }
});
test("changing holdout cannot change the selected policy or its holdout predictions", () => {
    const request = structuredClone(examples.forecast),
        before = runMission(request);
    request.work.observations.splice(
        -request.work.holdout,
        request.work.holdout,
        200,
        -30,
        75,
        5,
    );
    const after = runMission(request);
    assert.equal(before.evidence.selected, after.evidence.selected);
    assert.deepEqual(
        before.evidence.training_scores,
        after.evidence.training_scores,
    );
    assert.deepEqual(
        before.evidence.holdout_predictions,
        after.evidence.holdout_predictions,
    );
    assert.notEqual(before.evidence.holdout_mae, after.evidence.holdout_mae);
});
test("research quotes remain exact and no matching evidence is labeled as such", () => {
    const request = {
        goal: "quasar neutron redshift",
        work: {
            kind: "research",
            sources: [
                {
                    id: "source",
                    title: "Unrelated source",
                    text: "<img src=x onerror=alert(1)> Sales remained flat. No growth was observed.",
                },
            ],
        },
    };
    const result = runMission(request);
    assert.equal(result.evidence.selection, "context_only");
    for (const quote of result.evidence.citations)
        assert.ok(request.work.sources[0].text.includes(quote.quote));
});
test("job-shop schedule has independent precedence and capacity checks", () => {
    const result = runMission(examples.schedule);
    assert.equal(result.evidence.makespan, 18);
    assert.equal(result.evidence.baseline_makespan, 21);
    for (const job of examples.schedule.work.jobs) {
        const ops = result.evidence.operations
            .filter((op) => op.job === job.id)
            .sort((a, b) => a.sequence - b.sequence);
        for (let i = 1; i < ops.length; i++)
            assert.ok(ops[i].start >= ops[i - 1].end);
    }
    for (const [i, a] of result.evidence.operations.entries())
        for (const b of result.evidence.operations.slice(i + 1)) {
            if (a.machine === b.machine)
                assert.ok(a.end <= b.start || b.end <= a.start);
        }
});
