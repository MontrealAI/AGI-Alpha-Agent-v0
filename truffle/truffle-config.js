const HDWalletProvider = require('@truffle/hdwallet-provider');
require('dotenv').config();

module.exports = {
  networks: {
    mainnet: {
      provider: () =>
        new HDWalletProvider(
          process.env.DEPLOYER_KEY,
          process.env.MAINNET_RPC_URL
        ),
      network_id: 1,
      gasPrice: Number(process.env.GAS_PRICE) || undefined,
    },
  },
  compilers: {
    solc: {
      version: '0.8.25',
      settings: { optimizer: { enabled: true, runs: 200 } },
    },
  },
  plugins: ['truffle-plugin-verify'],
  api_keys: {
    etherscan: process.env.ETHERSCAN_API_KEY,
  },
};
