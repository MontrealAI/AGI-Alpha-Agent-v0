require("@nomicfoundation/hardhat-chai-matchers");
require("@nomicfoundation/hardhat-ethers");
const { extendEnvironment, subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD, TASK_COMPILE_SOLIDITY_CHECK_ERRORS } = require("hardhat/builtin-tasks/task-names");
const { SOLC_VERSION, pinnedCompiler, assertNoCompilerWarnings } = require("./scripts/compiler-policy");

subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(async ({ solcVersion }) => pinnedCompiler(solcVersion));
subtask(TASK_COMPILE_SOLIDITY_CHECK_ERRORS).setAction(async (args, hre, runSuper) => {
  await runSuper(args);
  assertNoCompilerWarnings(args.output);
});

extendEnvironment((hre) => {
  if (hre.network.name !== "hardhat" || hre.network.config.url || hre.network.config.forking)
    throw new Error("Contract fixtures require the in-process, unforked Hardhat network; external endpoints are forbidden");
});

module.exports = {
  solidity: {
    version: SOLC_VERSION,
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
