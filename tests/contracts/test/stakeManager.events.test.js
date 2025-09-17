const { expect } = require("chai");
const { ethers } = require("hardhat");

const ROLE_VALIDATOR = 2;

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
  let stake, agi;

  beforeEach(async function () {
    await ethers.provider.send("hardhat_reset", []);
    [owner, addr1, addr2, addr3, addr4] = await ethers.getSigners();
    ({ stake, agi } = await deployStakeManager());
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

  it("emits SlashPctsUpdated when setting employer pct", async function () {
    await expect(stake.setEmployerSlashPct(40))
      .to.emit(stake, "SlashPctsUpdated")
      .withArgs(40, 60);
  });

  it("emits SlashPctsUpdated when setting treasury pct", async function () {
    await expect(stake.setTreasurySlashPct(55))
      .to.emit(stake, "SlashPctsUpdated")
      .withArgs(45, 55);
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

describe("StakeManager slash distribution", function () {
  let owner, validator, beneficiary, treasury, extra;
  let stake, agi;
  const depositAmount = ethers.parseUnits("100", 18);

  beforeEach(async function () {
    await ethers.provider.send("hardhat_reset", []);
    [owner, validator, beneficiary, treasury, extra] = await ethers.getSigners();
    ({ stake, agi } = await deployStakeManager());
    await stake.setTreasury(treasury.address);
    await stake.setSlasher(owner.address);
    await agi.mint(validator.address, depositAmount);
    await agi
      .connect(validator)
      .approve(await stake.getAddress(), depositAmount);
    await stake
      .connect(validator)
      .depositStake(ROLE_VALIDATOR, depositAmount);
  });

  it("routes the full slash to the treasury by default", async function () {
    const slashAmount = ethers.parseUnits("40", 18);
    await expect(
      stake.slash(validator.address, beneficiary.address, slashAmount)
    )
      .to.emit(stake, "StakeSlashed")
      .withArgs(validator.address, beneficiary.address, slashAmount, 0n, slashAmount);
    expect(await agi.balanceOf(beneficiary.address)).to.equal(0n);
    expect(await agi.balanceOf(treasury.address)).to.equal(slashAmount);
  });

  it("respects the configured employer slash pct", async function () {
    await stake.setEmployerSlashPct(25);
    const slashAmount = ethers.parseUnits("20", 18);
    const employerShare = (slashAmount * 25n) / 100n;
    const treasuryShare = slashAmount - employerShare;
    await expect(
      stake.slash(validator.address, beneficiary.address, slashAmount)
    )
      .to.emit(stake, "StakeSlashed")
      .withArgs(
        validator.address,
        beneficiary.address,
        slashAmount,
        employerShare,
        treasuryShare
      );
    expect(await agi.balanceOf(beneficiary.address)).to.equal(employerShare);
    expect(await agi.balanceOf(treasury.address)).to.equal(treasuryShare);
  });

  it("sends the entire amount to the treasury when no beneficiary", async function () {
    await stake.setEmployerSlashPct(30);
    const slashAmount = ethers.parseUnits("10", 18);
    await expect(
      stake.slash(validator.address, ethers.ZeroAddress, slashAmount)
    )
      .to.emit(stake, "StakeSlashed")
      .withArgs(validator.address, ethers.ZeroAddress, slashAmount, 0n, slashAmount);
    expect(await agi.balanceOf(treasury.address)).to.equal(slashAmount);
  });
});

