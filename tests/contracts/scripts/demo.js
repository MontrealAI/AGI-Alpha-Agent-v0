// SPDX-License-Identifier: Apache-2.0
// Local Hardhat acceptance only: fixtures replace ENS and the canonical token at chain 31337.
const { ethers } = require("hardhat");
const { fixture, units, evidence, spec, now, jump } = require("./fixture");
const { compilePlan } = require("./plan");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { createHash } = require("node:crypto");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "../../..");
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const json = (value) =>
    JSON.stringify(
        value,
        (_, x) => (typeof x === "bigint" ? x.toString() : x),
        2,
    ) + "\n";
async function main() {
    const chain = await ethers.provider.getNetwork();
    assert.equal(
        chain.chainId,
        31337n,
        "This fixture must never run on a funded network",
    );
    const temp = fs.mkdtempSync(
        path.join(os.tmpdir(), "ascension-acceptance-"),
    );
    try {
        const { analyseScenario, makeGenome } = await import(
            path.join(root, "docs/assets/ascension/engine.mjs")
        );
        const { sealSeed, openSeed, hashObject } = await import(
            path.join(root, "docs/assets/ascension/crypto.mjs")
        );
        const scenario = JSON.parse(
            fs.readFileSync(
                path.join(root, "docs/assets/ascension/scenarios.json"),
            ),
        )[0];
        const analysis = analyseScenario(scenario),
            genome = makeGenome(analysis);
        const missionFile = path.join(temp, "allocation.json");
        fs.writeFileSync(missionFile, json(analysis.missions.allocation));
        const python = process.env.ALPHA_PYTHON || "python";
        function native(args) {
            return execFileSync(
                python,
                [
                    "-m",
                    "alpha_factory_v1.core.runtime.cli",
                    "--home",
                    path.join(temp, "agent"),
                    ...args,
                ],
                {
                    cwd: root,
                    env: {
                        ...process.env,
                        NO_DISCLAIMER: "1",
                        OPENAI_AGENTS_DISABLE_TRACING: "true",
                    },
                    encoding: "utf8",
                },
            );
        }
        native(["init"]);
        const nativeResult = JSON.parse(native(["run", missionFile]));
        assert.equal(nativeResult.state, "review");
        const verifiedJournal = JSON.parse(native(["verify"]));
        assert.equal(verifiedJournal.valid, true);
        const items = analysis.missions.allocation.work.items;
        let best = -Infinity;
        for (let mask = 0; mask < 2 ** items.length; mask++) {
            const chosen = items.filter((_, i) => mask & (1 << i));
            const cost = chosen.reduce((sum, x) => sum + x.cost, 0),
                risk = chosen.reduce((sum, x) => sum + x.risk, 0);
            if (cost <= scenario.budget && risk <= scenario.risk_limit)
                best = Math.max(
                    best,
                    chosen.reduce((sum, x) => sum + x.value, 0),
                );
        }
        const selected = items.filter((x) =>
            nativeResult.result.selected.includes(x.id),
        );
        assert.equal(
            new Set(nativeResult.result.selected).size,
            nativeResult.result.selected.length,
        );
        assert.equal(selected.length, nativeResult.result.selected.length);
        for (const field of ["cost", "value", "risk"])
            assert.equal(
                selected.reduce((sum, x) => sum + x[field], 0),
                nativeResult.result[field],
            );
        assert.equal(nativeResult.result.value, best);
        assert.ok(
            nativeResult.result.cost <= scenario.budget &&
                nativeResult.result.risk <= scenario.risk_limit,
        );
        const delivery = {
            schema: "agialpha.ascension.native-delivery.v1",
            nativeResult,
            verifiedJournal,
        };
        const resultHash = "0x" + hash(Buffer.from(json(delivery)));
        const plan = compilePlan([spec]);
        const capsule = await sealSeed(
            { ...genome, onchain_plan: plan },
            "public local EVM demo phrase; never use for private plans",
        );
        const recovered = await openSeed(
            capsule,
            "public local EVM demo phrase; never use for private plans",
        );
        assert.equal(recovered.onchain_plan.planRoot, plan.planRoot);
        const capsuleHash = "0x" + (await hashObject(capsule));
        const f = await fixture();
        const steps = [];
        async function record(stage, promise) {
            const receipt = await (await promise).wait();
            assert.equal(receipt.status, 1);
            const events = [];
            for (const log of receipt.logs) {
                for (const [name, contract] of Object.entries({
                    NovaSeed: f.seed,
                    MARK: f.mark,
                    Marketplace: f.jobs,
                    Oracle: f.oracle,
                })) {
                    if (
                        log.address.toLowerCase() !==
                        contract.target.toLowerCase()
                    )
                        continue;
                    const parsed = contract.interface.parseLog(log);
                    if (parsed)
                        events.push({
                            contract: name,
                            event: parsed.name,
                            args: Object.fromEntries(
                                parsed.fragment.inputs.map((input, i) => [
                                    input.name || String(i),
                                    parsed.args[i],
                                ]),
                            ),
                        });
                }
            }
            steps.push({
                stage,
                transactionHash: receipt.hash,
                block: receipt.blockNumber,
                gasUsed: receipt.gasUsed,
                status: receipt.status,
                events,
            });
        }
        await record(
            "Nova-Seed",
            f.seed
                .connect(f.business)
                .seal(
                    capsuleHash,
                    plan.planRoot,
                    1,
                    "ipfs://local-demo-only-not-published",
                    0,
                    evidence,
                ),
        );
        const id = await f.seed.nextId();
        await record(
            "Risk oracle",
            f.oracle.connect(f.business).openReview(id),
        );
        for (const v of f.validators.slice(0, 2))
            await record(
                "Risk oracle",
                f.oracle.connect(v).attest(id, 1000, true, evidence),
            );
        assert.equal(await f.oracle.green(id), true);
        await record(
            "MARK",
            f.mark
                .connect(f.business)
                .open(
                    id,
                    units("2"),
                    units("0.1"),
                    100,
                    units("100"),
                    (await now()) + 86400,
                    14 * 86400,
                ),
        );
        await record(
            "MARK",
            f.mark.connect(f.funder).buy(id, 40, units("158")),
        );
        await record("Sovereign", f.mark.connect(f.business).bloom(id));
        await record(
            "α-Job",
            f.mark.connect(f.business).route(id, 0, spec, [], 60, f.committee),
        );
        const job = await f.jobs.nextId();
        await record(
            "Auction",
            f.jobs.connect(f.agent).bid(job, units("70"), 86000),
        );
        await record(
            "Auction",
            f.jobs.connect(f.fastAgent).bid(job, units("80"), 1000),
        );
        await jump((await f.jobs.jobs(job)).auctionEnd);
        await record("Auction", f.jobs.award(job));
        assert.equal((await f.jobs.jobs(job)).worker, f.fastAgent.address);
        await record(
            "Delivery",
            f.jobs
                .connect(f.fastAgent)
                .submit(
                    job,
                    resultHash,
                    "ipfs://local-demo-only-not-published",
                ),
        );
        const beforeSupply = await f.token.totalSupply();
        for (const v of f.validators.slice(0, 2))
            await record(
                "Validation",
                f.jobs.connect(v).validate(job, resultHash, true, evidence),
            );
        const burned = beforeSupply - (await f.token.totalSupply());
        assert.equal(burned, units("0.8"));
        await record("Recovery", f.mark.collect(job));
        await record("Recovery", f.mark.close(id));
        const beforeRefund = await f.token.balanceOf(f.funder.address);
        await record("Recovery", f.mark.connect(f.funder).reclaim(id));
        assert.equal(
            (await f.token.balanceOf(f.funder.address)) - beforeRefund,
            units("78"),
        );
        assert.equal(await f.token.balanceOf(f.mark.target), 0n);
        await record(
            "Evolution candidate",
            f.seed
                .connect(f.business)
                .seal(
                    capsuleHash,
                    plan.planRoot,
                    1,
                    "ipfs://local-successor-only-not-published",
                    id,
                    resultHash,
                ),
        );
        assert.equal(await f.oracle.green(await f.seed.nextId()), false);
        const sources = Object.fromEntries(
            fs
                .readdirSync(path.join(root, "contracts/ascension"))
                .filter((x) => x.endsWith(".sol"))
                .sort()
                .map((name) => [
                    name,
                    hash(
                        fs.readFileSync(
                            path.join(root, "contracts/ascension", name),
                        ),
                    ),
                ]),
        );
        const report = {
            schema: "agialpha.ascension.local-evm.v1",
            mode: "local EVM acceptance",
            chainId: "31337",
            limitations: [
                "ENS and AGIALPHA are test fixtures; no mainnet transaction or external capital.",
                "Distinct local test signers are not independent organizations or real-world outcome certification.",
                "The native allocation uses supplied scenario assumptions; forecast accuracy and economic value are unmeasured.",
                "Artifact URIs are explicitly unpublished; the JSON report carries the actual delivered bytes.",
                "Successor mint records lineage; it starts without risk approval and does not demonstrate improved capability.",
            ],
            contracts: Object.fromEntries(
                Object.entries({
                    access: f.access,
                    seed: f.seed,
                    oracle: f.oracle,
                    jobs: f.jobs,
                    mark: f.mark,
                }).map(([key, c]) => [key, c.target]),
            ),
            sources,
            scenario: scenario.id,
            plan,
            capsule,
            nativeDelivery: delivery,
            resultHash,
            capsuleHash,
            steps,
            accounting: {
                token: "AGIALPHA",
                decimals: 18,
                funded: units("158"),
                grossJobPrice: units("80"),
                workerNet: units("75.24"),
                validatorsNet: units("3.96"),
                burned,
                refunded: units("78"),
                remainingTreasury: 0n,
            },
            checks: {
                encryptedCapsuleRecovered: true,
                nativeJournalVerified: true,
                quorumRequired: true,
                artifactBound: true,
                planBound: true,
                totalSupplyReduced: true,
                reserveConserved: true,
                successorRequiresNewReview: true,
            },
        };
        const output = path.resolve(
            process.env.ASCENSION_DEMO_OUTPUT ||
                path.join(root, "evidence/ascension-protocol/receipt.json"),
        );
        fs.mkdirSync(path.dirname(output), { recursive: true });
        fs.writeFileSync(output, json(report));
        process.stdout.write(
            json({
                output,
                transactions: steps.length,
                resultHash,
                burned: ethers.formatEther(burned),
                checks: report.checks,
            }),
        );
    } finally {
        fs.rmSync(temp, { recursive: true, force: true });
    }
}
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
