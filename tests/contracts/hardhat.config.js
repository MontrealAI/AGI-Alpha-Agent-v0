require("@nomicfoundation/hardhat-chai-matchers");
require("@nomicfoundation/hardhat-ethers");
const { extendEnvironment } = require("hardhat/config");

extendEnvironment((hre) => {
  if (hre.network.name !== "hardhat" || hre.network.config.url || hre.network.config.forking)
    throw new Error("Contract fixtures require the in-process, unforked Hardhat network; external endpoints are forbidden");
});

module.exports = {
  solidity: {
    version: "0.8.37",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true,
      evmVersion: "cancun"
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test"
  }
};
