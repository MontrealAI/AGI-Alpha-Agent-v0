import { defineConfig } from "hardhat/config";
export default defineConfig({
  solidity: { version: "0.8.24", preferWasm: true, settings: {
    optimizer: { enabled: true, runs: 200 }, viaIR: true, evmVersion: "paris"
  } },
  networks: { rehearsal: { type: "edr-simulated", chainType: "l1", chainId: 31337,
    ...(process.env.MAINNET_RPC_URL && process.env.FORK_BLOCK ? {
      forking: { url: process.env.MAINNET_RPC_URL, blockNumber: Number(process.env.FORK_BLOCK) }
    } : {})
  } }
});
