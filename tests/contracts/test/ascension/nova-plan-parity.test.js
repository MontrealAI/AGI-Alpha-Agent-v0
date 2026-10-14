// SPDX-License-Identifier: Apache-2.0
const assert = require("node:assert/strict");
const { ethers } = require("hardhat");
const { execFileSync } = require("child_process");
const path = require("path");
const { pathToFileURL } = require("url");
const { fixture, spec } = require("../../scripts/fixture");
const { compilePlan } = require("../../scripts/plan");
const root = path.resolve(__dirname, "../../../..");
const python = process.env.ALPHA_PYTHON || "python3";
const nativeCode = "import json,sys; from alpha_factory_v1.core.runtime.ascension import compile_plan; print(json.dumps(compile_plan(json.load(sys.stdin))))";

function native(specs) {
    return JSON.parse(execFileSync(python, ["-c", nativeCode], {
        cwd: root, env: { ...process.env, PYTHONPATH: root, NO_DISCLAIMER: "1" },
        input: JSON.stringify(specs), encoding: "utf8", timeout: 30000, stdio: ["pipe", "pipe", "pipe"],
    }));
}

describe("Nova Studio: browser, JavaScript, native and Solidity commitment parity", function () {
    this.timeout(120000);
    let browser, f, verifier;
    before(async () => {
        browser = await import(pathToFileURL(path.join(root, "docs/assets/nova-studio/plan.mjs")));
        f = await fixture();
        verifier = await (await ethers.getContractFactory("NovaPlanProofHarness")).deploy();
        await verifier.waitForDeployment();
    });
    for (const count of [1, 2, 3, 7, 127, 128]) {
        it(`${count} jobs: every leaf and sorted-pair proof matches exact current-source Solidity`, async () => {
            const specs = Array.from({ length: count }, (_, index) => ({
                ...spec, goal: `Job ${index}: vérification α / independent public evidence`,
                successMetric: index % 2 ? "A reproducible result, including é and 🚀" : spec.successMetric,
                bounty: index === count - 1 ? (2n ** 96n - 1n).toString() : (100n + BigInt(index)).toString(),
                duration: index % 2 ? 90 * 86400 : 1, priceWeight: index % 2 ? 10000 : 0,
            }));
            const compiled = browser.compilePlan(specs);
            assert.deepEqual(compiled, compilePlan(specs));
            assert.deepEqual(compiled, native(specs));
            for (const entry of compiled.jobs) {
                assert.equal(await f.jobs.hashSpec(entry.index, entry.spec), entry.leaf);
                assert.equal(await verifier.verify(entry.proof, compiled.planRoot, entry.leaf), true);
                assert.equal(await verifier.verify(entry.proof, compiled.planRoot, ethers.id("altered leaf")), false);
            }
            if (count === 3 || count === 7 || count === 127)
                assert.ok(compiled.jobs.at(-1).proof.length < compiled.jobs[0].proof.length);
        });
    }
    for (const count of [0, 129]) it(`${count} jobs is rejected by all three compilers`, () => {
        const specs = Array.from({ length: count }, () => ({ ...spec }));
        assert.throws(() => browser.compilePlan(specs));
        assert.throws(() => compilePlan(specs));
        assert.throws(() => native(specs), /1–128/);
    });
});
