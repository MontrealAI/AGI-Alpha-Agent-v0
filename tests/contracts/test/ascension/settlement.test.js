// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { AGIALPHA_ADDRESS } = require("../../../../token.config");
const { fixture, evidence, jump } = require("../../scripts/fixture");

describe("Ascension settlement conservation", function () {
    let token, harness, account, recipient;
    beforeEach(async () => {
        await ethers.provider.send("hardhat_reset", []);
        [account, recipient] = await ethers.getSigners();
        const implementation = await (await ethers.getContractFactory("AdversarialSettlementToken")).deploy();
        await ethers.provider.send("hardhat_setCode", [AGIALPHA_ADDRESS, await ethers.provider.getCode(implementation.target)]);
        token = implementation.attach(AGIALPHA_ADDRESS);
        harness = await (await ethers.getContractFactory("SettlementHarness")).deploy();
        await token.mint(harness.target, 1000);
        await token.mint(recipient.address, 1000);
    });
    it("requires the recipient and sender balances to change by the exact payment", async () => {
        for (const mode of [1, 2]) {
            await token.configure(mode, recipient.address);
            await expect(harness.sendTokens(recipient.address, 100)).to.be.revertedWith("non-exact payout");
            expect(await token.balanceOf(harness.target)).to.equal(1000);
            expect(await token.balanceOf(recipient.address)).to.equal(1000);
        }
        await token.configure(0, recipient.address);
        await harness.sendTokens(recipient.address, 100);
        expect(await token.balanceOf(harness.target)).to.equal(900);
        expect(await token.balanceOf(recipient.address)).to.equal(1100);
    });
    it("requires burns to destroy the paying contract's own balance and total supply", async () => {
        await token.configure(3, recipient.address);
        await expect(harness.burnTokens(100)).to.be.revertedWith("non-exact burn");
        await token.configure(4, recipient.address);
        await expect(harness.burnTokens(100)).to.be.revertedWith("supply not burned");
        expect(await token.totalSupply()).to.equal(2000);
        await token.configure(0, recipient.address);
        await harness.burnTokens(100);
        expect(await token.totalSupply()).to.equal(1900);
        expect(await token.balanceOf(harness.target)).to.equal(900);
    });
    it("never slashes on a rejection whose earlier validator has lost eligibility", async () => {
        const f = await fixture();
        const id = await f.post();
        await f.assign(id); await f.deliver(id);
        const stake = await f.jobs.stake(f.agent.address);
        await f.jobs.connect(f.validator1).validate(id, evidence, false, evidence);
        await f.access.setAdmission(f.validator1.address, ethers.ZeroHash, 0);
        await expect(f.jobs.connect(f.validator2).validate(id, evidence, false, evidence))
            .to.be.revertedWith("rejection no longer eligible");
        expect((await f.jobs.jobs(id)).state).to.equal(3);
        expect(await f.jobs.votes(id, f.validator2.address)).to.equal(0);
        await jump(Number((await f.jobs.jobs(id)).reviewEnd) + 1);
        await f.jobs.timeout(id);
        expect(await f.jobs.stake(f.agent.address)).to.equal(stake);
        expect(await f.jobs.locked(f.agent.address)).to.equal(0);
        await f.jobs.connect(f.business).claimRefund(id);
    });
});
