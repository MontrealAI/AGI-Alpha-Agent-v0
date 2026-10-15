// SPDX-License-Identifier: Apache-2.0
// Explicit disposable fork entry point. The normal unforked fixture guard is unchanged.
require("@nomicfoundation/hardhat-chai-matchers");
require("@nomicfoundation/hardhat-ethers");
const { extendEnvironment, subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD, TASK_COMPILE_SOLIDITY_CHECK_ERRORS } = require("hardhat/builtin-tasks/task-names");
const { SOLC_VERSION, pinnedCompiler, assertNoCompilerWarnings } = require("./scripts/compiler-policy");
const { SETTINGS } = require("./scripts/compile-production");
const rpc = process.env.ALPHA_FORK_RPC_URL;
const block = Number(process.env.ALPHA_FORK_BLOCK);
const hash = process.env.ALPHA_FORK_BLOCK_HASH;
if (!rpc || !Number.isSafeInteger(block) || block <= 0 || !/^0x[a-f0-9]{64}$/.test(hash || ""))
    throw Error("Explicit read-only upstream, pinned block and block hash are required");
const url = new URL(rpc);
if (url.protocol !== "https:" || url.username || url.password)
    throw Error("Fork upstream must be HTTPS without URL user credentials");
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(async ({ solcVersion }) => pinnedCompiler(solcVersion));
subtask(TASK_COMPILE_SOLIDITY_CHECK_ERRORS).setAction(async (args, hre, runSuper) => {
    await runSuper(args); assertNoCompilerWarnings(args.output);
});
extendEnvironment(hre => {
    if (hre.network.name !== "hardhat" || hre.network.config.url || hre.network.config.chainId !== 31337 ||
        hre.network.config.forking?.url !== rpc || hre.network.config.forking?.blockNumber !== block)
        throw Error("Fork rehearsal requires this process's in-memory Hardhat fork; no external execution endpoint");
});
module.exports = {
    solidity: { version: SOLC_VERSION, settings: SETTINGS },
    networks: { hardhat: { chainId: 31337, forking: { url: rpc, blockNumber: block } } },
    paths: { sources: "./contracts", tests: "./fork" },
    mocha: { timeout: 240000 }
};
