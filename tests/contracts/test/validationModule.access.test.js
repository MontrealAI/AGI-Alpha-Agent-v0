const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ValidationModule access control", function () {
  let owner;
  let jobRegistry;
  let attacker;
  let validator;
  let validationModule;
  let stakeManager;
  let reputation;

  beforeEach(async function () {
    await ethers.provider.send("hardhat_reset", []);
    [owner, jobRegistry, attacker, validator] = await ethers.getSigners();

    const StakeManager = await ethers.getContractFactory(
      "contracts/v2/mocks/MockValidationStakeManager.sol:MockValidationStakeManager"
    );
    stakeManager = await StakeManager.deploy();
    await stakeManager.waitForDeployment();
    await stakeManager.setMinValidatorStake(0);
    await stakeManager.setValidatorStake(validator.address, 1);

    const Reputation = await ethers.getContractFactory(
      "contracts/v2/mocks/MockReputationEngine.sol:MockReputationEngine"
    );
    reputation = await Reputation.deploy();
    await reputation.waitForDeployment();

    const ValidationModule = await ethers.getContractFactory(
      "contracts/v2/ValidationModule.sol:ValidationModule"
    );
    validationModule = await ValidationModule.deploy(
      await stakeManager.getAddress(),
      await reputation.getAddress(),
      jobRegistry.address
    );
    await validationModule.waitForDeployment();

    await validationModule.connect(owner).setCommitWindow(100);
    await validationModule.connect(owner).setRevealWindow(100);
    await validationModule.connect(owner).setValidatorsPerJob(1);
    await validationModule.connect(owner).setSelectionSeed(1);

    const clubRootNode = ethers.keccak256(ethers.toUtf8Bytes("club-root"));
    const subdomain = "validator";
    const label = ethers.keccak256(ethers.toUtf8Bytes(subdomain));
    const subnode = ethers.solidityPackedKeccak256(
      ["bytes32", "bytes32"],
      [clubRootNode, label]
    );
    const leaf = ethers.solidityPackedKeccak256(
      ["bytes32", "address"],
      [subnode, validator.address]
    );

    await validationModule.connect(owner).setClubRootNode(clubRootNode);
    await validationModule.connect(owner).setValidatorMerkleRoot(leaf);
    await validationModule
      .connect(owner)
      .addAdditionalValidator(validator.address, subdomain, []);
  });

  it("only allows the JobRegistry to start validation rounds", async function () {
    await expect(
      validationModule.connect(attacker).validate(2, "0x")
    ).to.be.revertedWith("not job registry");

    await expect(
      validationModule.connect(jobRegistry).validate(1, "0x")
    ).to.emit(validationModule, "ValidatorSelected")
      .withArgs(1, validator.address);
  });
});
