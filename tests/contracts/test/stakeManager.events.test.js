const { expect } = require("chai");
const { ethers } = require("hardhat");

async function deployStakeManager() {
  const Mock = await ethers.getContractFactory(
    "contracts/v2/mocks/MockAGI.sol:MockAGI"
  );
  const agi = await Mock.deploy(18);
  await agi.waitForDeployment();
  const StakeManager = await ethers.getContractFactory(
    "contracts/v2/StakeManager.sol:StakeManager"
  );
  const stake = await StakeManager.deploy(await agi.getAddress(), ethers.ZeroAddress);
  await stake.waitForDeployment();
  return { agi, stake };
}

describe("StakeManager setters emit events", function () {
  let owner, addr1, addr2, addr3, addr4;
  let stake;

  beforeEach(async function () {
    await ethers.provider.send("hardhat_reset", []);
    [owner, addr1, addr2, addr3, addr4] = await ethers.getSigners();
    ({ stake } = await deployStakeManager());
  });

  it("emits TreasuryUpdated", async function () {
    await expect(stake.setTreasury(addr1.address))
      .to.emit(stake, "TreasuryUpdated")
      .withArgs(addr1.address);
  });

  it("emits JobRegistryUpdated", async function () {
    await expect(stake.setJobRegistry(addr1.address))
      .to.emit(stake, "JobRegistryUpdated")
      .withArgs(addr1.address);
  });

  it("emits SlasherUpdated", async function () {
    await expect(stake.setSlasher(addr1.address))
      .to.emit(stake, "SlasherUpdated")
      .withArgs(addr1.address);
  });

  it("emits MinStakeAgentUpdated", async function () {
    await expect(stake.setMinStakeAgent(100))
      .to.emit(stake, "MinStakeAgentUpdated")
      .withArgs(100);
  });

  it("emits MinStakeEmployerUpdated", async function () {
    await expect(stake.setMinStakeEmployer(200))
      .to.emit(stake, "MinStakeEmployerUpdated")
      .withArgs(200);
  });

  it("emits MinStakeValidatorUpdated", async function () {
    await expect(stake.setMinStakeValidator(300))
      .to.emit(stake, "MinStakeValidatorUpdated")
      .withArgs(300);
  });

  it("emits FeePctUpdated", async function () {
    await expect(stake.setFeePct(100))
      .to.emit(stake, "FeePctUpdated")
      .withArgs(100);
  });

  it("emits BurnPctUpdated", async function () {
    await expect(stake.setBurnPct(200))
      .to.emit(stake, "BurnPctUpdated")
      .withArgs(200);
  });

  it("emits AGITypeAdded", async function () {
    await expect(stake.addAGIType(addr2.address, 500))
      .to.emit(stake, "AGITypeAdded")
      .withArgs(addr2.address, 500);
  });

  it("emits AGITypeRemoved", async function () {
    await stake.addAGIType(addr2.address, 500);
    await expect(stake.removeAGIType(addr2.address))
      .to.emit(stake, "AGITypeRemoved")
      .withArgs(addr2.address);
  });
});

