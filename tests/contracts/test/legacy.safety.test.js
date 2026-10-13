// SPDX-License-Identifier: Apache-2.0
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { installToken } = require("./utils/token");

describe("Legacy v2 escrow and certificate safety", function () {
  let owner, employer, agent, buyer, token, stake, registry;
  const reward = ethers.parseEther("10");

  beforeEach(async function () {
    await ethers.provider.send("hardhat_reset", []);
    [owner, employer, agent, buyer] = await ethers.getSigners();
    token = await installToken();
    stake = await (await ethers.getContractFactory("StakeManager")).deploy(owner.address);
    registry = await (await ethers.getContractFactory("JobRegistry")).deploy();
    const reputation = await (await ethers.getContractFactory("MockReputationEngine")).deploy();
    const tax = await (await ethers.getContractFactory("MockTaxPolicy")).deploy();
    await registry.setModules(ethers.ZeroAddress, stake.target, reputation.target,
      ethers.ZeroAddress, ethers.ZeroAddress, tax.target);
    await stake.setJobRegistry(registry.target);
    await registry.setMaxJobReward(reward);
    await registry.setMaxJobDuration(3600);
    await registry.addAdditionalAgent(agent.address);
    await token.mint(employer.address, reward);
    await token.connect(employer).approve(stake.target, reward);
  });

  async function createJob() {
    const { timestamp } = await ethers.provider.getBlock("latest");
    await registry.connect(employer).createJob(reward, timestamp + 300);
    return registry.nextJobId();
  }

  it("rejects a deadline that has already elapsed before taking escrow", async function () {
    const { timestamp } = await ethers.provider.getBlock("latest");
    await expect(registry.connect(employer).createJob(reward, timestamp))
      .to.be.revertedWith("invalid deadline");
    expect(await token.balanceOf(employer.address)).to.equal(reward);
    expect(await registry.nextJobId()).to.equal(0);
  });

  it("rejects empty rewards before opening an unrefundable zero escrow", async function () {
    const { timestamp } = await ethers.provider.getBlock("latest");
    await expect(registry.connect(employer).createJob(0, timestamp + 300))
      .to.be.revertedWith("reward 0");
    expect(await registry.nextJobId()).to.equal(0);
  });

  it("does not assign a worker to an expired open job", async function () {
    const id = await createJob();
    const job = await registry.jobs(id);
    await ethers.provider.send("evm_setNextBlockTimestamp", [Number(job.deadline) + 1]);
    await expect(registry.connect(agent).applyForJob(id, "", []))
      .to.be.revertedWith("deadline passed");
    expect((await registry.jobs(id)).status).to.equal(1);
    await registry.connect(employer).cancelJob(id);
    expect(await token.balanceOf(employer.address)).to.equal(reward);
  });

  for (const [action, event] of [["cancelJob", "JobCancelled"], ["delistJob", "JobDelisted"]]) {
    it(`preserves the client in ${event} after clearing the job`, async function () {
      const id = await createJob();
      await expect(registry.connect(action === "cancelJob" ? employer : owner)[action](id))
        .to.emit(registry, event).withArgs(id, employer.address);
      expect((await registry.jobs(id)).client).to.equal(ethers.ZeroAddress);
      expect(await token.balanceOf(employer.address)).to.equal(reward);
    });
  }

  it("rejects fee and burn settings that together exceed the escrow", async function () {
    await stake.setFeePct(6000);
    await expect(stake.setBurnPct(4001)).to.be.revertedWith("total deductions too high");
    await stake.setBurnPct(4000);
    await expect(stake.setFeePct(6001)).to.be.revertedWith("total deductions too high");
    expect(await stake.feePct()).to.equal(6000);
    expect(await stake.burnPct()).to.equal(4000);
    await createJob();
    const supply = await token.totalSupply();
    await registry.connect(employer).cancelJob(1);
    expect(await token.balanceOf(owner.address)).to.equal(reward * 6n / 10n);
    expect(supply - await token.totalSupply()).to.equal(reward * 4n / 10n);
    expect(await token.balanceOf(stake.target)).to.equal(0);
  });

  it("disables every NFT bonus configuration and preserves escrow and unrelated staker collateral", async function () {
    const cert = await (await ethers.getContractFactory("CertificateNFT")).deploy();
    await cert.setJobRegistry(owner.address);
    await cert.mint(agent.address, 1);
    for (const payoutPct of [0, 500, 9999, 10000, 10001, 20000, ethers.MaxUint256]) {
      await expect(stake.addAGIType(cert.target, payoutPct)).to.be.revertedWith("NFT bonuses disabled");
    }
    expect(await stake.agiTypePayoutPct(cert.target)).to.equal(0);
    await expect(stake.agiTypes(0)).to.be.reverted;
    await token.mint(buyer.address, reward);
    await token.connect(buyer).approve(stake.target, reward);
    await stake.connect(buyer).depositStake(0, reward);
    await stake.setJobRegistry(owner.address);
    await stake.lock(1, employer.address, reward);
    await stake.release(1, agent.address, [], 0);
    expect(await stake.jobEscrows(1)).to.equal(0);
    expect(await token.balanceOf(agent.address)).to.equal(reward);
    expect(await token.balanceOf(stake.target)).to.equal(reward);
    expect(await stake.agentStakes(buyer.address)).to.equal(reward);
    await stake.connect(buyer).withdrawStake(0, reward);
    expect(await token.balanceOf(buyer.address)).to.equal(reward);
  });

  it("invalidates a certificate listing on transfer, including a round trip to the seller", async function () {
    const cert = await (await ethers.getContractFactory("CertificateNFT")).deploy();
    await cert.setJobRegistry(owner.address);
    await cert.mint(employer.address, 1);
    await cert.connect(employer).list(1, reward);
    await expect(cert.connect(employer).transferFrom(employer.address, agent.address, 1))
      .to.emit(cert, "NFTDelisted").withArgs(1);
    expect((await cert.listings(1)).price).to.equal(0);
    await cert.connect(agent).transferFrom(agent.address, employer.address, 1);
    await token.mint(buyer.address, reward);
    await token.connect(buyer).approve(cert.target, reward);
    await expect(cert.connect(buyer).purchase(1)).to.be.revertedWith("not listed");
    await cert.connect(employer).list(1, reward);
    await cert.connect(buyer).purchase(1);
    expect(await cert.ownerOf(1)).to.equal(buyer.address);
    expect((await cert.listings(1)).price).to.equal(0);
  });
});
