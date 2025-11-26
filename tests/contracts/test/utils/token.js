const { ethers } = require("hardhat");
const path = require("path");

const {
  AGIALPHA_ADDRESS,
  AGIALPHA_DECIMALS,
} = require(path.join(__dirname, "../../../../token.config"));

async function installToken(
  factoryName = "contracts/v2/mocks/MockAGI.sol:MockAGI",
  decimals = AGIALPHA_DECIMALS
) {
  const Factory = await ethers.getContractFactory(factoryName);
  const needsArgs = Factory.interface.deploy.inputs.length > 0;
  const instance = needsArgs
    ? await Factory.deploy(decimals ?? AGIALPHA_DECIMALS)
    : await Factory.deploy();
  await instance.waitForDeployment();
  const runtimeCode = await ethers.provider.getCode(await instance.getAddress());
  await ethers.provider.send("hardhat_setCode", [AGIALPHA_ADDRESS, runtimeCode]);
  return Factory.attach(AGIALPHA_ADDRESS);
}

module.exports = { installToken, AGIALPHA_ADDRESS, AGIALPHA_DECIMALS };
