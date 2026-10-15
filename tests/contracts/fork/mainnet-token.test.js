// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { fixture, units, evidence, spec, jump } = require("./fixture");
const { tokenBaseline } = require("./token-support");

describe("Ascension partial mainnet-token fork; simulated ENS and supplied reviews", function () {
    let f, snapshot;
    before(async () => { f = await fixture(); snapshot = await ethers.provider.send("evm_snapshot", []); });
    beforeEach(async () => { expect(await ethers.provider.send("evm_revert", [snapshot])).to.equal(true); snapshot = await ethers.provider.send("evm_snapshot", []); });
    it("executes seed, risk review, curve buy/sell, funded plan, quorum payout/burn and capital reclamation", async () => {
        const { id, plan } = await f.createSeed(); await f.green(id);
        await f.mark.connect(f.business).open(id, units("2"), units("0.1"), 100, units("100"), (await ethers.provider.getBlock("latest")).timestamp + 86400, 14 * 86400);
        await f.mark.connect(f.funder).buy(id, 41, units("164"));
        await f.mark.connect(f.funder).sell(id, 1, 0);
        await f.mark.connect(f.business).bloom(id);
        await f.mark.connect(f.business).route(id, 0, spec, plan.jobs[0].proof, 60, f.committee);
        const jobId = await f.jobs.nextId(); await f.assign(jobId); await f.deliver(jobId);
        const supply = await f.token.totalSupply(), worker = await f.token.balanceOf(f.agent.address);
        await f.jobs.connect(f.validator1).validate(jobId, evidence, true, evidence);
        expect((await f.jobs.jobs(jobId)).state).to.equal(3);
        await f.jobs.connect(f.validator2).validate(jobId, evidence, true, evidence);
        expect((await f.jobs.jobs(jobId)).state).to.equal(4);
        expect(supply - await f.token.totalSupply()).to.equal(units("0.8"));
        expect(await f.token.balanceOf(f.agent.address) - worker).to.equal(units("75.24"));
        expect(await f.jobs.locked(f.agent.address)).to.equal(0);
        await f.mark.collect(jobId); await f.mark.close(id); await f.mark.connect(f.funder).reclaim(id);
        expect(await f.token.balanceOf(f.mark.target)).to.equal(0);
        await expect(f.mark.collect(jobId)).to.be.revertedWith("not collectible");
        await expect(f.mark.connect(f.funder).reclaim(id)).to.be.revertedWith("no capital claim");
        expect(ethers.keccak256(await ethers.provider.getCode(f.token.target))).to.equal(tokenBaseline().codeHash);
        console.log("ACTUAL_TOKEN_FORK_BASELINE", JSON.stringify(tokenBaseline()));
    });
    it("retains worker collateral when an earlier rejecting reviewer loses admission, then times out and refunds", async () => {
        const id = await f.post(); await f.assign(id); await f.deliver(id);
        const stake = await f.jobs.stake(f.agent.address);
        await f.jobs.connect(f.validator1).validate(id, evidence, false, evidence);
        await f.access.setAdmission(f.validator1.address, ethers.ZeroHash, 0);
        await expect(f.jobs.connect(f.validator2).validate(id, evidence, false, evidence)).to.be.revertedWith("rejection no longer eligible");
        expect((await f.jobs.jobs(id)).state).to.equal(3);
        await jump(Number((await f.jobs.jobs(id)).reviewEnd) + 1); await f.jobs.timeout(id);
        expect(await f.jobs.stake(f.agent.address)).to.equal(stake);
        expect(await f.jobs.locked(f.agent.address)).to.equal(0);
        await f.jobs.connect(f.business).claimRefund(id);
        await expect(f.jobs.connect(f.business).claimRefund(id)).to.be.reverted;
    });
});
