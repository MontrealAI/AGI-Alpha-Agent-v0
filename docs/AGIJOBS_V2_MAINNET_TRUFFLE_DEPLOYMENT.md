[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Deploying AGIJobs v2 to Ethereum Mainnet (CLI Guide)

This guide explains how to deploy the AGIJobs v2 smart‑contract suite to the Ethereum mainnet using the Truffle CLI. It follows production best practices—multisig governance, source verification and safe parameter defaults—to help you launch immediately in production.

## Prerequisites

- **Node.js 20.x and npm 10+** (use `nvm use` to match `.nvmrc`).
- **Truffle 5.11+** and `@truffle/hdwallet-provider` installed globally or with `npx`.
- Access to an Ethereum mainnet RPC endpoint (Infura, Alchemy, etc.).
- A deployer account private key with sufficient ETH for gas.
- `GOVERNANCE_ADDRESS`—typically a multisig or timelock contract.
- `ETHERSCAN_API_KEY` for automatic verification.

Install dependencies:

```bash
npm install
npm install --save-dev @truffle/hdwallet-provider truffle-plugin-verify
```

## Configure Truffle

Create a `.env` file with your secrets:

```bash
MAINNET_RPC_URL=https://mainnet.infura.io/v3/<api-key>
DEPLOYER_KEY=<private-key>
GOVERNANCE_ADDRESS=<multisig-or-timelock>
ETHERSCAN_API_KEY=<etherscan-key>
```

The repository includes `truffle/truffle-config.js`:

```javascript
const HDWalletProvider = require('@truffle/hdwallet-provider');
require('dotenv').config();

module.exports = {
  networks: {
    mainnet: {
      provider: () =>
        new HDWalletProvider(process.env.DEPLOYER_KEY, process.env.MAINNET_RPC_URL),
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
```

## Migration Script

`truffle/migrations/2_deploy_agijobs_v2.js` deploys the full stack via the on‑chain `Deployer` helper:

```javascript
const Deployer = artifacts.require('Deployer');

module.exports = async function (deployer) {
  const governance = process.env.GOVERNANCE_ADDRESS;
  if (!governance) {
    throw new Error('GOVERNANCE_ADDRESS env var is required');
  }

  await deployer.deploy(Deployer);
  const instance = await Deployer.deployed();

  const ids = {
    ens: '0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e',
    nameWrapper: '0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401',
    clubRootNode: web3.utils.namehash('club.agi.eth'),
    agentRootNode: web3.utils.namehash('agent.agi.eth'),
    validatorMerkleRoot: '0x0000000000000000000000000000000000000000000000000000000000000000',
    agentMerkleRoot: '0x0000000000000000000000000000000000000000000000000000000000000000',
  };

  const receipt = await instance.deployDefaults(ids, governance);
  console.log('AGIJobs v2 deployed via Deployer at', instance.address);
  console.log('tx hash:', receipt.tx);
};
```

## Deploy to Mainnet

From the repository root:

```bash
cd truffle
npx truffle migrate --network mainnet
```

The script deploys the `Deployer` contract, calls `deployDefaults` and prints addresses for all modules (StakeManager, JobRegistry, ValidationModule, ReputationEngine, DisputeModule, CertificateNFT, PlatformRegistry, JobRouter, PlatformIncentives, FeePool, TaxPolicy, IdentityRegistry and SystemPause).

## Verify on Etherscan

Truffle runs `truffle-plugin-verify` when you execute:

```bash
npx truffle run verify Deployer --network mainnet
```

Repeat for the addresses printed in the migration output. Verified source code builds trust and enables Etherscan’s UI features.

## Post‑Deployment Checklist

- Confirm ownership of each module is transferred to `GOVERNANCE_ADDRESS`.
- Use the `SystemPause` contract to `pauseAll()` in case of emergencies.
- Record deployed addresses and keep backups of your `.env` file.
- Test interactions (e.g., `JobRegistry.getStakeManager()`) before inviting users.

Following this guide yields a production‑ready AGIJobs v2 deployment on Ethereum mainnet using Truffle.

