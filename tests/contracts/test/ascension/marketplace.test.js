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

describe("Ascension auctions, delivery and failure recovery", function () {
    let f;
    beforeEach(async () => {
        f = await fixture();
    });
    it("reserves opted-in reviewer capacity and releases it at terminal state", async () => {
        await f.oracle
            .connect(f.validator1)
            .setJobAvailability(
                f.business.address,
                (await now()) + 100 * 86400,
                1,
            );
        const id = await f.post();
        expect(await f.oracle.activeJobs(f.validator1.address)).to.equal(1);
        await expect(f.post()).to.be.revertedWith(
            "review capacity not reserved",
        );
        await jump((await f.jobs.jobs(id)).auctionEnd);
        await f.jobs.award(id);
        expect(await f.oracle.activeJobs(f.validator1.address)).to.equal(0);
        await f.oracle
            .connect(f.validator1)
            .setJobAvailability(f.business.address, 0, 1);
        await expect(f.post()).to.be.revertedWith(
            "review capacity not reserved",
        );
    });
    it("selects the minimum published price/time/reputation score, independent of bid order", async () => {
        const id = await f.post();
        await f.jobs.connect(f.agent).bid(id, units("70"), 86000);
        await f.jobs.connect(f.fastAgent).bid(id, units("80"), 1000);
        expect(
            await f.jobs.score(units("80"), 1000, 0, units("100"), 86400, 6000),
        ).to.be.lessThan(
            await f.jobs.score(
                units("70"),
                86000,
                0,
                units("100"),
                86400,
                6000,
            ),
        );
        await jump((await f.jobs.jobs(id)).auctionEnd);
        await f.jobs.award(id);
        expect((await f.jobs.jobs(id)).worker).to.equal(f.fastAgent.address);
        expect(await f.jobs.locked(f.agent.address)).to.equal(0);
        expect(await f.jobs.locked(f.fastAgent.address)).to.equal(units("10"));
        expect(await f.jobs.score(80, 10, 10000, 100, 100, 6000)).to.equal(
            await f.jobs.score(80, 10, 50000, 100, 100, 6000),
        );
    });
    it("rejects duplicate bids, empty or impossible missions, unbonded workers and conflicting committees", async () => {
        for (const change of [
            { goal: "" },
            { successMetric: "" },
            { bounty: 0 },
            { duration: 0 },
            { priceWeight: 10001 },
        ])
            await expect(
                f.jobs
                    .connect(f.business)
                    .post({ ...spec, ...change }, 60, f.committee),
            ).to.be.reverted;
        await expect(
            f.jobs
                .connect(f.business)
                .post(spec, 60, [
                    f.validator1.address,
                    f.validator1.address,
                    f.validator2.address,
                ]),
        ).to.be.revertedWith("duplicate validator");
        await f.register(f.validator1, 1, "conflicted-executor");
        await f.jobs.connect(f.validator1).deposit(units("100"));
        const id = await f.post();
        await expect(
            f.jobs.connect(f.validator1).bid(id, units("80"), 1000),
        ).to.be.revertedWith("validator cannot execute");
        await f.jobs.connect(f.agent).withdraw(units("1000"));
        await expect(
            f.jobs.connect(f.agent).bid(id, units("80"), 1000),
        ).to.be.revertedWith("insufficient free stake");
        await f.jobs.connect(f.fastAgent).bid(id, units("80"), 1000);
        await expect(
            f.jobs.connect(f.fastAgent).bid(id, units("80"), 1000),
        ).to.be.revertedWith("duplicate or full auction");
        await expect(
            f.jobs.connect(f.fastAgent).withdraw(units("1000")),
        ).to.be.revertedWith("locked stake");
    });
    it("skips expired ENS bidders and releases their collateral", async () => {
        const id = await f.post();
        await f.jobs.connect(f.agent).bid(id, units("80"), 1000);
        await f.ens.setOwner(
            await f.access.names(f.agent.address, 1),
            f.outsider.address,
        );
        await jump((await f.jobs.jobs(id)).auctionEnd);
        await f.jobs.award(id);
        expect((await f.jobs.jobs(id)).state).to.equal(6);
        expect(await f.jobs.locked(f.agent.address)).to.equal(0);
        await f.jobs.connect(f.business).claimRefund(id);
        expect(await f.token.balanceOf(f.jobs.target)).to.equal(units("2000"));
    });
    it("returns unawarded escrow without slashing when no bidder fits the remaining horizon", async () => {
        const id = await f.post();
        await f.jobs.connect(f.agent).bid(id, units("80"), 1000);
        await jump((await f.jobs.jobs(id)).executionEnd + 1n);
        await f.jobs.award(id);
        expect((await f.jobs.jobs(id)).state).to.equal(6);
        expect(await f.jobs.stake(f.agent.address)).to.equal(units("1000"));
        await f.jobs.connect(f.business).claimRefund(id);
        await expect(
            f.jobs.connect(f.business).claimRefund(id),
        ).to.be.revertedWith("refund unavailable");
    });
    it("binds reviews to the exact artifact and selected committee; a single vote cannot release payment", async () => {
        const id = await f.post();
        await f.assign(id);
        await f.deliver(id);
        await expect(
            f.jobs
                .connect(f.validator1)
                .validate(id, ethers.id("different result"), true, evidence),
        ).to.be.revertedWith("artifact binding");
        await expect(
            f.jobs.connect(f.outsider).validate(id, evidence, true, evidence),
        ).to.be.revertedWith("selected validator required");
        await f.jobs
            .connect(f.validator1)
            .validate(id, evidence, true, evidence);
        await expect(
            f.jobs.connect(f.validator1).validate(id, evidence, true, evidence),
        ).to.be.revertedWith("duplicate vote");
        expect((await f.jobs.jobs(id)).state).to.equal(3);
        await expect(
            f.jobs
                .connect(f.agent)
                .submit(id, ethers.id("replace"), "ipfs://replace"),
        ).to.be.revertedWith("not deliverable");
    });
    it("rechecks earlier approvals before payout when a validator is revoked", async () => {
        const id = await f.post();
        await f.assign(id);
        await f.deliver(id);
        await f.jobs
            .connect(f.validator1)
            .validate(id, evidence, true, evidence);
        await f.access.setAdmission(f.validator1.address, ethers.ZeroHash, 0);
        await expect(
            f.jobs.connect(f.validator2).validate(id, evidence, true, evidence),
        ).to.be.revertedWith("approval no longer eligible");
        expect((await f.jobs.jobs(id)).state).to.equal(3);
        expect(await f.jobs.votes(id, f.validator2.address)).to.equal(0);
        await jump((await f.jobs.jobs(id)).reviewEnd + 1n);
        await f.jobs.timeout(id);
        expect(await f.jobs.stake(f.agent.address)).to.equal(units("1000"));
    });
    it("slashes failed work once, burns 1% of compensation, and returns escrow plus net collateral", async () => {
        const id = await f.post();
        await f.assign(id);
        await f.deliver(id);
        const supply = await f.token.totalSupply();
        for (const v of f.validators.slice(0, 2))
            await f.jobs.connect(v).validate(id, evidence, false, evidence);
        expect((await f.jobs.jobs(id)).state).to.equal(5);
        expect(await f.jobs.stake(f.agent.address)).to.equal(units("990"));
        expect(await f.jobs.reputation(f.agent.address)).to.equal(0);
        expect(supply - (await f.token.totalSupply())).to.equal(units("0.1"));
        const before = await f.token.balanceOf(f.business.address);
        await f.jobs.connect(f.business).claimRefund(id);
        expect((await f.token.balanceOf(f.business.address)) - before).to.equal(
            units("109.9"),
        );
        await expect(f.jobs.timeout(id)).to.be.reverted;
    });
    it("slashes missed delivery but never slashes submitted work merely because reviewers disappear", async () => {
        const missing = await f.post();
        await f.assign(missing);
        await jump((await f.jobs.jobs(missing)).due + 1n);
        await f.jobs.timeout(missing);
        expect(await f.jobs.stake(f.agent.address)).to.equal(units("990"));
        const unreviewed = await f.post();
        await f.assign(unreviewed);
        await f.deliver(unreviewed);
        await expect(f.jobs.timeout(unreviewed)).to.be.revertedWith(
            "review still open",
        );
        await jump((await f.jobs.jobs(unreviewed)).reviewEnd + 1n);
        await f.jobs.timeout(unreviewed);
        expect((await f.jobs.jobs(unreviewed)).state).to.equal(6);
        expect(await f.jobs.stake(f.agent.address)).to.equal(units("990"));
        expect(await f.jobs.locked(f.agent.address)).to.equal(0);
        await f.jobs.connect(f.business).claimRefund(missing);
        await f.jobs.connect(f.business).claimRefund(unreviewed);
        expect(await f.token.balanceOf(f.jobs.target)).to.equal(units("1990"));
    });
    it("uses integer base units and floors 1% separately for every actual payout", async () => {
        const id = await f.post({ ...spec, bounty: "103" });
        await f.jobs.connect(f.agent).bid(id, 103, 1000);
        await jump((await f.jobs.jobs(id)).auctionEnd);
        await f.jobs.award(id);
        await f.deliver(id);
        const supply = await f.token.totalSupply(),
            worker = await f.token.balanceOf(f.agent.address);
        await f.approve(id);
        // Validator gross = floor(103 * 5% / 2) = 2 each; worker gross = 99. All burns floor to zero.
        expect(supply - (await f.token.totalSupply())).to.equal(0);
        expect((await f.token.balanceOf(f.agent.address)) - worker).to.equal(
            99,
        );
    });
});

describe("MARK curve, admission and capital recovery", function () {
    let f, id;
    beforeEach(async () => {
        f = await fixture();
        ({ id } = await f.createSeed());
        await f.green(id);
        await f.mark
            .connect(f.business)
            .open(
                id,
                units("2"),
                units("0.1"),
                100,
                units("100"),
                (await now()) + 86400,
                14 * 86400,
            );
    });
    it("quotes exact independent per-lot sums and reverses each batch", async () => {
        for (let supply = 0; supply < 19; supply++) {
            for (const count of [0, 1, 2, 17]) {
                let expected = 0n;
                for (let i = 0; i < count; i++)
                    expected += units("2") + BigInt(supply + i) * units("0.1");
                expect(
                    await f.mark.quote(supply, count, units("2"), units("0.1")),
                ).to.equal(expected);
            }
        }
        await f.mark.connect(f.funder).buy(id, 40, units("158"));
        await f.mark.connect(f.funder).sell(id, 15, units("58"));
        expect((await f.mark.campaigns(id)).reserve).to.equal(units("80"));
        await f.mark.connect(f.funder).sell(id, 25, units("80"));
        expect(await f.token.balanceOf(f.mark.target)).to.equal(0);
    });
    it("enforces slippage, trading admission and funding target without partial mutation", async () => {
        await expect(
            f.mark.connect(f.funder).buy(id, 40, units("157.9")),
        ).to.be.revertedWith("slippage");
        expect((await f.mark.campaigns(id)).supply).to.equal(0);
        await expect(
            f.mark.connect(f.outsider).buy(id, 40, units("158")),
        ).to.be.revertedWith("admission gate");
        await f.mark.connect(f.funder).buy(id, 10, units("24.5"));
        await expect(f.mark.connect(f.business).bloom(id)).to.be.revertedWith(
            "not funded",
        );
        await expect(
            f.mark.connect(f.funder).sell(id, 10, units("25")),
        ).to.be.revertedWith("slippage");
    });
    it("keeps exits available after policy revocation while blocking new exposure", async () => {
        await f.mark.connect(f.funder).buy(id, 40, units("158"));
        await f.access.setAdmission(f.funder.address, ethers.ZeroHash, 0);
        await f.access.setAdmission(f.validator1.address, ethers.ZeroHash, 0);
        await expect(
            f.mark.connect(f.funder).buy(id, 1, units("6")),
        ).to.be.revertedWith("admission gate");
        await f.mark.connect(f.funder).sell(id, 40, units("158"));
        expect(await f.token.balanceOf(f.mark.target)).to.equal(0);
    });
    it("transfers funding lots only between admitted accounts and conserves all closed reserve including dust", async () => {
        await f.mark.connect(f.funder).buy(id, 40, units("158"));
        await expect(
            f.mark.connect(f.funder).transferLots(id, f.outsider.address, 1),
        ).to.be.revertedWith("admission gate");
        await f.mark.connect(f.funder).transferLots(id, f.funder2.address, 13);
        await jump((await f.mark.campaigns(id)).fundingEnd);
        await f.mark.close(id);
        const first = await f.token.balanceOf(f.funder.address),
            second = await f.token.balanceOf(f.funder2.address);
        await f.mark.connect(f.funder).reclaim(id);
        await f.mark.connect(f.funder2).reclaim(id);
        expect(
            (await f.token.balanceOf(f.funder.address)) -
                first +
                (await f.token.balanceOf(f.funder2.address)) -
                second,
        ).to.equal(units("158"));
        expect((await f.mark.campaigns(id)).reserve).to.equal(0);
    });
    it("stops redemption at bloom and prevents a transferred NFT from taking committed capital", async () => {
        await f.mark.connect(f.funder).buy(id, 40, units("158"));
        await f.mark.connect(f.business).bloom(id);
        await expect(
            f.mark.connect(f.funder).sell(id, 1, 0),
        ).to.be.revertedWith("not redeemable");
        await expect(
            f.mark.connect(f.funder).transferLots(id, f.funder2.address, 1),
        ).to.be.revertedWith("funding closed");
        await expect(
            f.mark.connect(f.outsider).route(id, 0, spec, [], 60, f.committee),
        ).to.be.revertedWith("business authority");
    });
});
