const { expect } = require("chai");
const { ethers } = require("hardhat");

async function deployAGI(decimals) {
  const Mock = await ethers.getContractFactory(
    "contracts/v2/mocks/MockAGI.sol:MockAGI"
  );
  const agi = await Mock.deploy(decimals);
  await agi.waitForDeployment();
  return agi;
}

describe("AGIALPHA integrations", function () {
  let owner, agent, employer, jobRegistry, seller, buyer, mismatch;
  const amount = ethers.parseUnits("1", 18);

  beforeEach(async () => {
    await ethers.provider.send("hardhat_reset", []);
    [owner, agent, employer, jobRegistry, seller, buyer, mismatch] = await ethers.getSigners();
  });

  it("StakeManager deploy fails if decimals != 18", async function () {
    const badToken = await deployAGI(6);
    const StakeManager = await ethers.getContractFactory(
      "contracts/v2/StakeManager.sol:StakeManager"
    );
    await expect(
      StakeManager.deploy(await badToken.getAddress(), owner.address)
    ).to.be.revertedWith("wrong decimals");
  });

  it("CertificateNFT deploy fails if decimals != 18", async function () {
    const badToken = await deployAGI(6);
    const CertificateNFT = await ethers.getContractFactory(
      "contracts/v2/CertificateNFT.sol:CertificateNFT"
    );
    await expect(
      CertificateNFT.deploy(await badToken.getAddress())
    ).to.be.revertedWith("wrong decimals");
  });

  it("staking and locking succeed with 1e18 and fail with mismatched token", async function () {
    const agi = await deployAGI(18);
    const StakeManager = await ethers.getContractFactory(
      "contracts/v2/StakeManager.sol:StakeManager"
    );
    const AGIALPHA = await agi.getAddress();
    const stake = await StakeManager.deploy(AGIALPHA, owner.address);
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
    const agi = await deployAGI(18);
    const CertificateNFT = await ethers.getContractFactory(
      "contracts/v2/CertificateNFT.sol:CertificateNFT"
    );
    const AGIALPHA = await agi.getAddress();
    const cert = await CertificateNFT.deploy(AGIALPHA);
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

});
