// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
    fixture,
    units,
    evidence,
    spec,
    now,
    jump,
} = require("../../scripts/fixture");
const { compilePlan } = require("../../scripts/plan");

describe("Ascension: Nova-Seed → MARK → Sovereign → jobs", function () {
    let f;
    beforeEach(async () => {
        f = await fixture();
    });
    it("executes the complete immutable plan, burns every payout and refunds unused capital exactly", async () => {
        const { id, plan } = await f.campaign();
        expect(await f.seed.ownerOf(id)).to.equal(f.business.address);
        expect(await f.seed.supportsInterface("0x80ac58cd")).to.equal(true);
        await f.mark
            .connect(f.business)
            .route(id, 0, spec, [], 60, f.committee);
        const jobId = await f.jobs.nextId();
        expect(await f.mark.jobSeed(jobId)).to.equal(id);
        expect(await f.jobs.hashSpec(0, spec)).to.equal(plan.planRoot);
        await f.assign(jobId);
        await f.deliver(jobId);
        const supply = await f.token.totalSupply(),
            worker = await f.token.balanceOf(f.agent.address);
        const validator = await f.token.balanceOf(f.validator1.address);
        await f.jobs
            .connect(f.validator1)
            .validate(jobId, evidence, true, evidence);
        expect((await f.jobs.jobs(jobId)).state).to.equal(3);
        await f.jobs
            .connect(f.validator2)
            .validate(jobId, evidence, true, evidence);
        expect((await f.jobs.jobs(jobId)).state).to.equal(4);
        expect(supply - (await f.token.totalSupply())).to.equal(units("0.8"));
        expect((await f.token.balanceOf(f.agent.address)) - worker).to.equal(
            units("75.24"),
        );
        expect(
            (await f.token.balanceOf(f.validator1.address)) - validator,
        ).to.equal(units("1.98"));
        expect(await f.jobs.reputation(f.agent.address)).to.equal(1);
        expect(await f.jobs.locked(f.agent.address)).to.equal(0);
        await f.mark.collect(jobId);
        await f.mark.close(id);
        const investor = await f.token.balanceOf(f.funder.address);
        await f.mark.connect(f.funder).reclaim(id);
        expect((await f.token.balanceOf(f.funder.address)) - investor).to.equal(
            units("78"),
        );
        expect(await f.token.balanceOf(f.mark.target)).to.equal(0);
        expect(await f.token.balanceOf(f.jobs.target)).to.equal(units("2000"));
        expect(await f.token.balanceOf(f.oracle.target)).to.equal(units("300"));
        await expect(f.mark.collect(jobId)).to.be.revertedWith(
            "not collectible",
        );
        await expect(f.mark.connect(f.funder).reclaim(id)).to.be.revertedWith(
            "no capital claim",
        );
        await expect(
            f.jobs
                .connect(f.validator3)
                .validate(jobId, evidence, true, evidence),
        ).to.be.revertedWith("not reviewable");
    });
    it("verifies nontrivial Merkle proofs and rejects altered goals, metrics, budgets and replay", async () => {
        const specs = [
            spec,
            {
                ...spec,
                goal: "Independently audit portfolio feasibility",
                bounty: units("20").toString(),
            },
            {
                ...spec,
                goal: "Prepare a bounded pilot execution schedule",
                bounty: units("30").toString(),
            },
        ];
        const { id, plan } = await f.campaign(specs);
        for (const change of [
            { goal: "drain treasury" },
            { successMetric: "trust me" },
            { bounty: units("101").toString() },
            { duration: 86401 },
            { priceWeight: 5000 },
        ]) {
            await expect(
                f.mark
                    .connect(f.business)
                    .route(
                        id,
                        0,
                        { ...spec, ...change },
                        plan.jobs[0].proof,
                        60,
                        f.committee,
                    ),
            ).to.be.revertedWith("FusionPlan proof");
        }
        for (const j of plan.jobs) {
            await f.mark
                .connect(f.business)
                .route(id, j.index, j.spec, j.proof, 60, f.committee);
            await expect(
                f.mark
                    .connect(f.business)
                    .route(id, j.index, j.spec, j.proof, 60, f.committee),
            ).to.be.revertedWith("FusionPlan proof");
        }
        expect((await f.mark.campaigns(id)).reserve).to.equal(units("8"));
        await expect(f.mark.close(id)).to.be.revertedWith(
            "missions still open",
        );
    });
    it("rejects an unbudgeted plan without moving tokens", async () => {
        const expensive = { ...spec, bounty: units("200").toString() };
        const { id } = await f.campaign([expensive]);
        await expect(
            f.mark
                .connect(f.business)
                .route(id, 0, expensive, [], 60, f.committee),
        ).to.be.revertedWith("treasury budget");
        expect((await f.mark.campaigns(id)).reserve).to.equal(units("158"));
        expect(await f.mark.posted(id, 0)).to.equal(false);
    });
    it("requires an evidence-bound successor and preserves its parent and independent review gate", async () => {
        const { id } = await f.createSeed();
        await f.green(id);
        const next = await f.createSeed(
            [
                {
                    ...spec,
                    goal: "Apply the independently reviewed improved portfolio policy",
                },
            ],
            id,
        );
        expect((await f.seed.genomes(next.id)).parent).to.equal(id);
        expect(await f.oracle.green(next.id)).to.equal(false);
        expect(await f.oracle.green(id)).to.equal(true);
        await expect(
            f.seed
                .connect(f.business)
                .seal(evidence, evidence, 1, "ipfs://x", id, ethers.ZeroHash),
        ).to.be.revertedWith("empty commitment");
    });
    it("allows only the bound MARK to post on behalf of a business", async () => {
        await expect(
            f.jobs
                .connect(f.outsider)
                .postFromSeed(f.business.address, spec, 60, f.committee),
        ).to.be.revertedWith("MARK only");
        await expect(f.jobs.bindMark(f.outsider.address)).to.be.revertedWith(
            "binding is one-time",
        );
        await expect(
            f.oracle.bindMarketplace(f.jobs.target),
        ).to.be.revertedWith("binding is one-time");
        await expect(
            f.oracle
                .connect(f.outsider)
                .lockForJob(
                    f.validator1.address,
                    f.business.address,
                    (await now()) + 1000,
                ),
        ).to.be.revertedWith("marketplace only");
    });
    it("closes an abandoned enterprise after its horizon and returns every unspent unit", async () => {
        const { id } = await f.campaign();
        await expect(f.mark.close(id)).to.be.revertedWith(
            "missions still open",
        );
        await jump((await f.mark.campaigns(id)).executionEnd + 1n);
        await f.mark.close(id);
        await f.mark.connect(f.funder).reclaim(id);
        expect(await f.token.balanceOf(f.mark.target)).to.equal(0);
    });
    it("suspends new treasury spending when the NFT is transferred after bloom", async () => {
        const { id } = await f.campaign();
        await f.seed
            .connect(f.business)
            .transferFrom(f.business.address, f.outsider.address, id);
        await expect(
            f.mark.connect(f.outsider).route(id, 0, spec, [], 60, f.committee),
        ).to.be.revertedWith("business authority");
        await expect(
            f.mark.connect(f.business).route(id, 0, spec, [], 60, f.committee),
        ).to.be.revertedWith("green business required");
    });
});

describe("Ascension identity and risk oracle", function () {
    let f;
    beforeEach(async () => {
        f = await fixture();
    });
    it("uses exactly the three requested ENS namespaces", async () => {
        for (const [role, name] of [
            "alpha.agi.eth",
            "alpha.agent.agi.eth",
            "alpha.club.agi.eth",
        ].entries())
            expect(await f.access.roots(role)).to.equal(ethers.namehash(name));
    });
    it("rejects wrong roots, resolver-only assertions and noncanonical or compound labels", async () => {
        const node = ethers.namehash("intruder.agent.agi.eth");
        await f.ens.setOwner(node, f.outsider.address);
        await expect(
            f.access.connect(f.outsider).register(1, "intruder"),
        ).to.be.revertedWith("ENS ownership required");
        for (const label of [
            "alice.eth",
            "ALICE",
            "-alice",
            "alice-",
            "аlice",
            "",
            "a".repeat(64),
        ])
            await expect(f.access.connect(f.agent).register(1, label)).to.be
                .reverted;
    });
    it("rechecks live ownership and wrapped-name expiry", async () => {
        const node = await f.access.names(f.agent.address, 1);
        await f.ens.setOwner(node, f.outsider.address);
        expect(await f.access.eligible(f.agent.address, 1)).to.equal(false);
        await f.ens.setOwner(node, f.wrapper.target);
        await f.wrapper.set(node, f.agent.address, (await now()) + 30);
        expect(await f.access.eligible(f.agent.address, 1)).to.equal(true);
        await jump((await now()) + 31);
        expect(await f.access.eligible(f.agent.address, 1)).to.equal(false);
    });
    it("fails closed on absent, expired and revoked admission; only governance can attest admission", async () => {
        expect(await f.access.admitted(f.outsider.address)).to.equal(false);
        await expect(
            f.access
                .connect(f.outsider)
                .setAdmission(
                    f.outsider.address,
                    evidence,
                    (await now()) + 100,
                ),
        ).to.be.reverted;
        await f.access.setAdmission(
            f.agent.address,
            evidence,
            (await now()) + 10,
        );
        await jump((await now()) + 11);
        expect(await f.access.eligible(f.agent.address, 1)).to.equal(false);
    });
    it("requires two staked validators, rejects duplicate votes and locks risk stake until expiry", async () => {
        const { id } = await f.createSeed();
        await f.oracle.connect(f.business).openReview(id);
        await expect(
            f.oracle.connect(f.outsider).attest(id, 1, true, evidence),
        ).to.be.revertedWith("independent validator");
        await f.oracle.connect(f.validator1).attest(id, 1000, true, evidence);
        expect(await f.oracle.green(id)).to.equal(false);
        await expect(
            f.oracle.connect(f.validator1).attest(id, 1000, true, evidence),
        ).to.be.revertedWith("duplicate vote");
        await expect(
            f.oracle.connect(f.validator1).withdraw(units("100")),
        ).to.be.revertedWith("locked stake");
        await f.oracle.connect(f.validator2).attest(id, 1000, true, evidence);
        expect(await f.oracle.green(id)).to.equal(true);
        await jump((await f.oracle.rounds(id)).until + 1n);
        expect(await f.oracle.green(id)).to.equal(false);
        await f.oracle.connect(f.validator1).withdraw(units("100"));
    });
    it("rejects high risk or denied-policy quorum, empty evidence, and seed-owner self-review", async () => {
        const { id } = await f.createSeed();
        await f.oracle.connect(f.business).openReview(id);
        await f.register(f.business, 2, "conflicted");
        await f.oracle.connect(f.business).deposit(units("100"));
        await expect(
            f.oracle.connect(f.business).attest(id, 1, true, evidence),
        ).to.be.revertedWith("independent validator");
        await expect(
            f.oracle.connect(f.validator1).attest(id, 1, true, ethers.ZeroHash),
        ).to.be.revertedWith("attestation required");
        await f.oracle.connect(f.validator1).attest(id, 2001, true, evidence);
        await f.oracle.connect(f.validator2).attest(id, 1, false, evidence);
        expect(await f.oracle.green(id)).to.equal(false);
        await expect(
            f.oracle.connect(f.validator3).attest(id, 1, true, evidence),
        ).to.be.revertedWith("review decided");
    });
    it("revokes green status when any approving validator loses admission or the NFT changes owners", async () => {
        const { id } = await f.createSeed();
        await f.green(id);
        await f.access.setAdmission(f.validator1.address, ethers.ZeroHash, 0);
        expect(await f.oracle.green(id)).to.equal(false);
        await f.access.setAdmission(
            f.validator1.address,
            evidence,
            (await now()) + 86400,
        );
        expect(await f.oracle.green(id)).to.equal(true);
        await f.seed
            .connect(f.business)
            .transferFrom(f.business.address, f.outsider.address, id);
        expect(await f.oracle.green(id)).to.equal(false);
    });
});
