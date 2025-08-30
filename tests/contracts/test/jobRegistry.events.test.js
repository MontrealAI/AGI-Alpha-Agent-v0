const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("JobRegistry setters emit events", function () {
  let jobRegistry;

  beforeEach(async function () {
    await ethers.provider.send("hardhat_reset", []);
    const JobRegistry = await ethers.getContractFactory(
      "contracts/v2/JobRegistry.sol:JobRegistry"
    );
    jobRegistry = await JobRegistry.deploy();
    await jobRegistry.waitForDeployment();
  });

  it("emits ValidatorRewardPctUpdated", async function () {
    await expect(jobRegistry.setValidatorRewardPct(50))
      .to.emit(jobRegistry, "ValidatorRewardPctUpdated")
      .withArgs(50);
  });

  it("emits MaxJobRewardUpdated", async function () {
    await expect(jobRegistry.setMaxJobReward(1000))
      .to.emit(jobRegistry, "MaxJobRewardUpdated")
      .withArgs(1000);
  });

  it("emits MaxJobDurationUpdated", async function () {
    await expect(jobRegistry.setMaxJobDuration(3600))
      .to.emit(jobRegistry, "MaxJobDurationUpdated")
      .withArgs(3600);
  });
});
