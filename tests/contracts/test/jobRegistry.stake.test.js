const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("JobRegistry agent staking requirements", function () {
  let owner;
  let employer;
  let agent;
  let jobRegistry;
  let stakeManager;
  let reputation;
  let taxPolicy;
  let agi;
  const minStake = ethers.parseUnits("100", 18);
  const reward = ethers.parseUnits("10", 18);
  const maxDuration = 7 * 24 * 60 * 60; // 1 week

  beforeEach(async function () {
    await ethers.provider.send("hardhat_reset", []);
    [owner, employer, agent] = await ethers.getSigners();

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

  async function createJob() {
    const block = await ethers.provider.getBlock("latest");
    const deadline = block.timestamp + 60 * 60; // 1 hour from now

    await agi.mint(employer.address, reward);
    await agi
      .connect(employer)
      .approve(await stakeManager.getAddress(), reward);

    const tx = await jobRegistry
      .connect(employer)
      .createJob(reward, deadline);
    await tx.wait();

    return await jobRegistry.nextJobId();
  }

  it("rejects agents without the minimum stake", async function () {
    const jobId = await createJob();

    await expect(
      jobRegistry.connect(agent).applyForJob(jobId, "", [])
    ).to.be.revertedWith("stake too low");
  });

  it("allows agents meeting the minimum stake to apply", async function () {
    const jobId = await createJob();

    await agi.mint(agent.address, minStake);
    await agi
      .connect(agent)
      .approve(await stakeManager.getAddress(), minStake);
    await stakeManager.connect(agent).depositStake(0, minStake);

    await expect(
      jobRegistry.connect(agent).applyForJob(jobId, "", [])
    )
      .to.emit(jobRegistry, "JobApplied")
      .withArgs(jobId, agent.address);

    const job = await jobRegistry.jobs(jobId);
    expect(job.worker).to.equal(agent.address);
  });
});
