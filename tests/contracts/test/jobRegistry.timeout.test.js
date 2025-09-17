const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("JobRegistry timeout claims", function () {
  let owner;
  let employer;
  let agent;
  let outsider;
  let jobRegistry;
  let stakeManager;
  let reputation;
  let taxPolicy;
  let agi;
  const minStake = ethers.parseUnits("100", 18);
  const reward = ethers.parseUnits("10", 18);
  const maxDuration = 7 * 24 * 60 * 60;

  beforeEach(async function () {
    await ethers.provider.send("hardhat_reset", []);
    [owner, employer, agent, outsider] = await ethers.getSigners();

    const MockAGI = await ethers.getContractFactory(
      "contracts/v2/mocks/MockAGI.sol:MockAGI"
    );
    agi = await MockAGI.deploy(18);
    await agi.waitForDeployment();

    const StakeManager = await ethers.getContractFactory(
      "contracts/v2/StakeManager.sol:StakeManager"
    );
    stakeManager = await StakeManager.deploy(
      await agi.getAddress(),
      owner.address
    );
    await stakeManager.waitForDeployment();

    const MockReputation = await ethers.getContractFactory(
      "contracts/v2/mocks/MockReputationEngine.sol:MockReputationEngine"
    );
    reputation = await MockReputation.deploy();
    await reputation.waitForDeployment();

    const MockTaxPolicy = await ethers.getContractFactory(
      "contracts/v2/mocks/MockTaxPolicy.sol:MockTaxPolicy"
    );
    taxPolicy = await MockTaxPolicy.deploy();
    await taxPolicy.waitForDeployment();

    const JobRegistry = await ethers.getContractFactory(
      "contracts/v2/JobRegistry.sol:JobRegistry"
    );
    jobRegistry = await JobRegistry.deploy();
    await jobRegistry.waitForDeployment();

    await stakeManager.setJobRegistry(await jobRegistry.getAddress());
    await stakeManager.setMinStakeAgent(minStake);

    await jobRegistry.setModules(
      ethers.ZeroAddress,
      await stakeManager.getAddress(),
      await reputation.getAddress(),
      ethers.ZeroAddress,
      ethers.ZeroAddress,
      await taxPolicy.getAddress()
    );
    await jobRegistry.setMaxJobReward(reward);
    await jobRegistry.setMaxJobDuration(maxDuration);
    await jobRegistry.addAdditionalAgent(agent.address);
  });

  async function createJobAndApply() {
    const block = await ethers.provider.getBlock("latest");
    const deadline = block.timestamp + 60;

    await agi.mint(employer.address, reward);
    await agi
      .connect(employer)
      .approve(await stakeManager.getAddress(), reward);

    const tx = await jobRegistry
      .connect(employer)
      .createJob(reward, deadline);
    await tx.wait();

    const jobId = await jobRegistry.nextJobId();

    await agi.mint(agent.address, minStake);
    await agi
      .connect(agent)
      .approve(await stakeManager.getAddress(), minStake);
    await stakeManager.connect(agent).depositStake(0, minStake);

    await jobRegistry.connect(agent).applyForJob(jobId, "", []);

    return jobId;
  }

  it("allows employers to reclaim escrow after timeouts", async function () {
    const jobId = await createJobAndApply();
    const job = await jobRegistry.jobs(jobId);

    await ethers.provider.send("evm_setNextBlockTimestamp", [
      Number(job.deadline) + 1
    ]);
    await ethers.provider.send("evm_mine", []);

    await expect(jobRegistry.connect(employer).claimTimeout(jobId))
      .to.emit(jobRegistry, "JobTimedOut")
      .withArgs(jobId, employer.address, agent.address);

    const cleared = await jobRegistry.jobs(jobId);
    expect(cleared.client).to.equal(ethers.ZeroAddress);
    expect(cleared.status).to.equal(0);

    expect(await agi.balanceOf(employer.address)).to.equal(reward);
  });

  it("rejects timeout claims before the deadline", async function () {
    const jobId = await createJobAndApply();

    await expect(
      jobRegistry.connect(employer).claimTimeout(jobId)
    ).to.be.revertedWith("deadline not passed");
  });

  it("rejects timeout claims outside the Applied status", async function () {
    const block = await ethers.provider.getBlock("latest");
    const deadline = block.timestamp + 60;

    await agi.mint(employer.address, reward);
    await agi
      .connect(employer)
      .approve(await stakeManager.getAddress(), reward);

    const tx = await jobRegistry
      .connect(employer)
      .createJob(reward, deadline);
    await tx.wait();

    const jobId = await jobRegistry.nextJobId();

    await expect(
      jobRegistry.connect(employer).claimTimeout(jobId)
    ).to.be.revertedWith("invalid status");
  });

  it("prevents unauthorized callers from claiming timeouts", async function () {
    const jobId = await createJobAndApply();
    const job = await jobRegistry.jobs(jobId);

    await ethers.provider.send("evm_setNextBlockTimestamp", [
      Number(job.deadline) + 1
    ]);
    await ethers.provider.send("evm_mine", []);

    await expect(
      jobRegistry.connect(outsider).claimTimeout(jobId)
    ).to.be.revertedWith("not authorized");
  });

  it("allows the contract owner to claim timeouts", async function () {
    const jobId = await createJobAndApply();
    const job = await jobRegistry.jobs(jobId);

    await ethers.provider.send("evm_setNextBlockTimestamp", [
      Number(job.deadline) + 1
    ]);
    await ethers.provider.send("evm_mine", []);

    await expect(jobRegistry.connect(owner).claimTimeout(jobId))
      .to.emit(jobRegistry, "JobTimedOut")
      .withArgs(jobId, employer.address, agent.address);
  });
});
