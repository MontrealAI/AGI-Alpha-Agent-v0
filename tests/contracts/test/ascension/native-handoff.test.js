// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { fixture, spec, units } = require("../../scripts/fixture");
const { compilePlan } = require("../../scripts/plan");
const root = path.resolve(__dirname, "../../../..");
const python = process.env.ALPHA_PYTHON || "python3";
function native(code, input, args = []) {
    return JSON.parse(execFileSync(python, ["-c", code, ...args], {
        cwd: root,
        env: { ...process.env, PYTHONPATH: root, NO_DISCLAIMER: "1" },
        input: JSON.stringify(input), encoding: "utf8", timeout: 30000,
    }));
}

describe("Ascension: installed native evidence matches Solidity", function () {
    this.timeout(120000);
    it("matches Python, JavaScript and Solidity commitments including odd/max trees and uint96", async () => {
        const f = await fixture();
        for (const count of [1, 2, 3, 5, 128]) {
            const specs = Array.from({ length: count }, (_, i) => ({
                ...spec, goal: `Job ${i}: α insight`,
                bounty: i === count - 1 ? (2n ** 96n - 1n).toString() : spec.bounty,
            }));
            const compiled = native(
                "import json,sys; from alpha_factory_v1.core.runtime.ascension import compile_plan; print(json.dumps(compile_plan(json.load(sys.stdin))))",
                specs,
            );
            expect(compiled).to.deep.equal(compilePlan(specs));
            for (const index of new Set([0, Math.floor(count / 2), count - 1]))
                expect(await f.jobs.hashSpec(index, specs[index])).to.equal(compiled.jobs[index].leaf);
        }
    });
    it("settles the exact signed and reviewed native delivery bytes with the required burn", async () => {
        const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "ascension-native-"));
        try {
            const output = path.join(temporary, "delivery.json");
            const report = native(`
import json,sys
from pathlib import Path
from alpha_factory_v1.core.runtime.ascension import compile_plan, delivery, verify_delivery
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.store import Journal,digest
spec=json.load(sys.stdin)
mission=Mission.model_validate({"goal":spec["goal"],"work":{"kind":"allocation","budget":10,"items":[{"id":"one","cost":3,"value":8},{"id":"two","cost":7,"value":10}]}})
journal=Journal.initialize(Path(sys.argv[1])/"state")
engine=Engine(journal)
record=engine.execute(journal.submit(mission)["id"])
assert record["state"]=="review" and record["result"]["value"]==18
engine.review(record["id"],record["revision"],digest(record["result"]),True,"Local fixture reviewed both items and recomputed totals; not an independent validator.")
plan=compile_plan([spec])
data=delivery(journal,plan,0,record["id"])
Path(sys.argv[2]).write_bytes(data)
print(json.dumps({"plan":plan,"verified":verify_delivery(data,journal.public,plan["planRoot"])}))
`, spec, [temporary, output]);
            const f = await fixture();
            const { id, plan } = await f.campaign([spec]);
            expect(report.plan).to.deep.equal(plan);
            const resultHash = ethers.keccak256(fs.readFileSync(output));
            expect(report.verified.resultHash).to.equal(resultHash);
            await f.mark.connect(f.business).route(id, 0, spec, report.plan.jobs[0].proof, 60, f.committee);
            const job = await f.jobs.nextId();
            await f.assign(job);
            await f.deliver(job, resultHash);
            const supply = await f.token.totalSupply();
            await f.approve(job, resultHash);
            expect((await f.jobs.jobs(job)).state).to.equal(4);
            expect(supply - await f.token.totalSupply()).to.equal(units("0.8"));
            expect(await f.jobs.reputation(f.agent.address)).to.equal(1);
            const verified = JSON.parse(execFileSync(python, [
                "-m", "alpha_factory_v1.core.runtime.cli", "ascension-verify-delivery", output,
                "--public-key", report.verified.publicKey, "--plan-root", plan.planRoot,
            ], { cwd: root, env: { ...process.env, PYTHONPATH: root }, encoding: "utf8", timeout: 30000 }));
            expect(verified.resultHash).to.equal(resultHash);
        } finally {
            fs.rmSync(temporary, { recursive: true, force: true });
        }
    });
});
