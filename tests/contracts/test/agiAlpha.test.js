const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
  AGIALPHA_ADDRESS,
  AGIALPHA_DECIMALS,
  installToken,
} = require("./utils/token");

describe("AGIALPHA integrations", function () {
  let owner, agent, employer, jobRegistry, seller, buyer, mismatch;
  const amount = ethers.parseUnits("1", AGIALPHA_DECIMALS);

  beforeEach(async () => {
    await ethers.provider.send("hardhat_reset", []);
    [owner, agent, employer, jobRegistry, seller, buyer, mismatch] = await ethers.getSigners();
  });

  it("StakeManager deploy fails if decimals != 18", async function () {
    await installToken("contracts/v2/mocks/MockAGI.sol:MockAGI", 6);
    const StakeManager = await ethers.getContractFactory(
      "contracts/v2/StakeManager.sol:StakeManager"
    );
    await expect(StakeManager.deploy(owner.address)).to.be.revertedWith(
      "wrong decimals"
    );
  });

  it("CertificateNFT deploy fails if decimals != 18", async function () {
    await installToken("contracts/v2/mocks/MockAGI.sol:MockAGI", 6);
    const CertificateNFT = await ethers.getContractFactory(
      "contracts/v2/CertificateNFT.sol:CertificateNFT"
    );
    await expect(CertificateNFT.deploy()).to.be.revertedWith("wrong decimals");
  });

  it("staking and locking succeed with 1e18 and fail with mismatched token", async function () {
    const agi = await installToken("contracts/v2/mocks/MockAGI.sol:MockAGI", 18);
    const StakeManager = await ethers.getContractFactory(
      "contracts/v2/StakeManager.sol:StakeManager"
    );
    const stake = await StakeManager.deploy(owner.address);
    await stake.waitForDeployment();
    const stakeAddr = await stake.getAddress();

    // positive staking
    await agi.mint(agent.address, amount);
    await agi.connect(agent).approve(stakeAddr, amount);
    await stake.connect(agent).depositStake(0, amount);
    expect(await stake.agentStakes(agent.address)).to.equal(amount);

    // negative staking with mismatched token
    const Other = await ethers.getContractFactory(
      "contracts/v2/mocks/MockAGI.sol:MockAGI"
    );
    const other = await Other.deploy(18);
    await other.mint(mismatch.address, amount);
    await other.connect(mismatch).approve(stakeAddr, amount);
    await expect(stake.connect(mismatch).depositStake(0, amount)).to.be.reverted;

    // locking success
    await agi.mint(employer.address, amount);
    await agi.connect(employer).approve(stakeAddr, amount);
    await stake.setJobRegistry(jobRegistry.address);
    await stake.connect(jobRegistry).lock(1, employer.address, amount);
    expect(await stake.jobEscrows(1)).to.equal(amount);

    // locking failure with mismatched token
    await other.mint(employer.address, amount);
    await other.connect(employer).approve(stakeAddr, amount);
    await expect(stake.connect(jobRegistry).lock(2, employer.address, amount)).to.be.reverted;
  });

  it("certificate purchasing succeeds with AGI and fails with mismatched token", async function () {
    const agi = await installToken("contracts/v2/mocks/MockAGI.sol:MockAGI", 18);
    const CertificateNFT = await ethers.getContractFactory(
      "contracts/v2/CertificateNFT.sol:CertificateNFT"
    );
    const cert = await CertificateNFT.deploy();
    await cert.waitForDeployment();
    const certAddr = await cert.getAddress();
    await cert.setJobRegistry(owner.address);

    // mint and list by seller
    await cert.mint(seller.address, 1);
    await cert.connect(seller).list(1, amount);

    // buyer purchase success
    await agi.mint(buyer.address, amount);
    await agi.connect(buyer).approve(certAddr, amount);
    await cert.connect(buyer).purchase(1);
    expect(await cert.ownerOf(1)).to.equal(buyer.address);

    // mismatched token purchase failure
    const Other = await ethers.getContractFactory(
      "contracts/v2/mocks/MockAGI.sol:MockAGI"
    );
    const other = await Other.deploy(18);
    await cert.mint(seller.address, 2);
    await cert.connect(seller).list(2, amount);
    await other.mint(mismatch.address, amount);
    await other.connect(mismatch).approve(certAddr, amount);
    await expect(cert.connect(mismatch).purchase(2)).to.be.reverted;
  });

  it("release burns the configured percentage", async function () {
    const agi = await installToken("contracts/v2/mocks/MockAGI.sol:MockAGI", 18);
    const StakeManager = await ethers.getContractFactory(
      "contracts/v2/StakeManager.sol:StakeManager"
    );
    const stake = await StakeManager.deploy(owner.address);
    await stake.waitForDeployment();
    await stake.setJobRegistry(jobRegistry.address);
    await stake.setBurnPct(1000); // 10%

    const amount = ethers.parseUnits("1", AGIALPHA_DECIMALS);
    await agi.mint(employer.address, amount);
    await agi.connect(employer).approve(await stake.getAddress(), amount);
    await stake.connect(jobRegistry).lock(1, employer.address, amount);

    const initialSupply = await agi.totalSupply();
    await stake
      .connect(jobRegistry)
      .release(1, agent.address, [], 0);

    const burnAmount = (amount * 1000n) / 10000n;
    expect(await agi.totalSupply()).to.equal(initialSupply - burnAmount);
  });

  it("prevents reentrancy attacks", async function () {
    const malicious = await installToken(
      "contracts/v2/mocks/MaliciousToken.sol:MaliciousToken"
    );

    const StakeManager = await ethers.getContractFactory(
      "contracts/v2/StakeManager.sol:StakeManager"
    );
    const stake = await StakeManager.deploy(owner.address);
    await stake.waitForDeployment();
    const stakeAddr = await stake.getAddress();

    await malicious.setStake(stakeAddr);

    // attack during deposit
    await malicious.mint(agent.address, amount);
    await malicious.connect(agent).approve(stakeAddr, amount);
    await malicious.setAttack(true);
    await expect(
      stake.connect(agent).depositStake(0, amount)
    ).to.be.revertedWithCustomError(stake, "ReentrancyGuardReentrantCall");

    // successful deposit
    await malicious.setAttack(false);
    await stake.connect(agent).depositStake(0, amount);

    // attack during withdraw
    await malicious.setAttack(true);
    await expect(
      stake.connect(agent).withdrawStake(0, amount)
    ).to.be.revertedWithCustomError(stake, "ReentrancyGuardReentrantCall");
  });

  it("prevents reentrancy attacks in certificate purchase", async function () {
    const malicious = await installToken(
      "contracts/v2/mocks/MaliciousCertToken.sol:MaliciousCertToken"
    );

    const CertificateNFT = await ethers.getContractFactory(
      "contracts/v2/CertificateNFT.sol:CertificateNFT"
    );
    const cert = await CertificateNFT.deploy();
    await cert.waitForDeployment();
    const certAddr = await cert.getAddress();
    await cert.setJobRegistry(owner.address);

    await cert.mint(seller.address, 1);
    await cert.connect(seller).list(1, amount);

    await malicious.mint(buyer.address, amount);
    await malicious.connect(buyer).approve(certAddr, amount);
    await malicious.setCert(certAddr);
    await malicious.setAttack(true, 1);

    await expect(cert.connect(buyer).purchase(1)).to.be.revertedWithCustomError(
      cert,
      "ReentrancyGuardReentrantCall"
    );

    await malicious.setAttack(false, 1);
    await cert.connect(buyer).purchase(1);
    expect(await cert.ownerOf(1)).to.equal(buyer.address);
  });

  it("exposes configured address and decimals", async function () {
    const ConstantsHarness = await ethers.getContractFactory(
      "contracts/v2/ConstantsHarness.sol:ConstantsHarness"
    );
    const harness = await ConstantsHarness.deploy();
    await harness.waitForDeployment();

    expect(await harness.agiAlpha()).to.equal(AGIALPHA_ADDRESS);
    expect(await harness.agiDecimals()).to.equal(AGIALPHA_DECIMALS);
  });

});
