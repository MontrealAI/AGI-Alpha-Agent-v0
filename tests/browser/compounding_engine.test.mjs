// SPDX-License-Identifier: Apache-2.0
import { test } from "node:test";
import assert from "node:assert/strict";
import {
    example,
    run,
    reviewRun,
    verify,
    freeze,
    compute,
    parse,
    canonical,
    digest,
    docketFiles,
    exportDocket,
} from "../../docs/assets/compounding/engine.mjs";
for (const [scenario, state] of [
    ["seasonal", "accepted"],
    ["shift", "hold"],
    ["ablation", "hold"],
])
    test(`${scenario}: real predictions determine the result`, async () => {
        const r = await run(example(scenario));
        assert.equal((await verify(r)).bounded_transfer, "hold");
        const reviewed = await reviewRun(
            r,
            "accept",
            "Operator",
            "Inspected predictions",
            1000,
            2000,
        );
        assert.equal((await verify(reviewed)).bounded_transfer, state);
        assert.equal((await verify(reviewed)).manuscript_promotion, "hold");
        if (scenario === "ablation")
            assert.deepEqual(r.core.arms.B5, r.core.arms.B6);
        assert.equal(r.core.evidence_contact.level, "E2");
    });
test("frozen policy cannot learn the future; changing A changes the treatment", async () => {
    const spec = example(),
        a = await compute(spec);
    spec.tasks[0].heldout.fill(999);
    const b = await compute(spec);
    assert.deepEqual(a.capability, b.capability);
    assert.deepEqual(
        a.arms.B6.tasks[0].predictions_milli,
        b.arms.B6.tasks[0].predictions_milli,
    );
    spec.training = Array.from({ length: 40 }, (_, i) => i);
    assert.equal((await freeze(spec.training)).policy, "linear");
    assert.notDeepEqual(
        (await compute(spec)).arms.B6.tasks[0].predictions_milli,
        a.arms.B6.tasks[0].predictions_milli,
    );
});
test("rehashing fabricated predictions, policy or gains cannot bypass replay", async () => {
    for (const field of ["prediction", "policy", "gain"]) {
        const r = await run(example());
        if (field === "prediction")
            r.core.arms.B6.tasks[0].predictions_milli[0]++;
        if (field === "policy") r.core.capability.policy = "last";
        if (field === "gain") r.core.metrics.raw_gain_milli = 999999999;
        const { sha256, review, ...payload } = r;
        r.sha256 = await digest(payload);
        await assert.rejects(() => verify(r));
    }
});
test("unknown fields, stale reviews, missing costs and expensive review stay closed", async () => {
    const costly = example();
    costly.human_cost_milli_per_second = 100;
    const r = await reviewRun(
        await run(costly),
        "accept",
        "Op",
        "Reviewed",
        1,
        86400000,
    );
    assert.equal((await verify(r)).bounded_transfer, "hold");
    r.review.run_sha256 = "0".repeat(64);
    await assert.rejects(() => verify(r));
    const extra = await run(example());
    extra.validator_verdict = "accepted";
    await assert.rejects(() => verify(extra));
    const spec = example();
    spec.call_cost_milli = 10000;
    assert.equal(
        (
            await verify(
                await reviewRun(
                    await run(spec),
                    "accept",
                    "Op",
                    "Reviewed",
                    1,
                    1,
                ),
            )
        ).bounded_transfer,
        "hold",
    );
});
test("strict JSON rejects duplicates, unsafe integers and excessive nesting", () => {
    for (const raw of [
        '{"x":1,"x":2}',
        '{"x":NaN}',
        '{"x":1.5}',
        '{"x":1.0}',
        '{"x":1e3}',
        "[]",
        '{"x":9007199254740992}',
        '{"x":' + "[".repeat(25) + "1" + "]".repeat(25) + "}",
    ])
        assert.throws(() => parse(raw));
    assert.deepEqual(
        parse('{"x":"quote \\\" braces {} and unicode α", "a":[1,2]}').a,
        [1, 2],
    );
});
test("docket includes all manuscript sections and binds every file", async () => {
    const r = await run(example());
    const files = await docketFiles(r);
    assert.equal(
        new Set(Object.keys(files).map((x) => x.split("/")[0])).size,
        14,
    );
    const sums = JSON.parse(files["checksums.json"]);
    assert.equal(Object.keys(sums).length, Object.keys(files).length - 1);
    const archive = await exportDocket(r);
    assert.equal(new DataView(archive.buffer).getUint32(0, true), 0x04034b50);
    assert.equal(
        canonical(parse(files["05_agialpha_runs/run.json"])),
        canonical(r),
    );
});
