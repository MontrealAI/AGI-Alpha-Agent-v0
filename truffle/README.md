# Historical Truffle entrypoint

Use the [current Hardhat deployment and migration guide](../tests/contracts/README.md).

The historical `migrations/2_deploy_agijobs_v2.js` required a `Deployer` contract that is not present
in this repository. Its logged token override did not change the Solidity constants, and its ENS
namehash helper was not supplied. It was not a reproducible deployment path.

The filename remains available for existing references, but now returns an actionable error before
loading artifacts or attempting a transaction. `truffle-config.js` has no network entries and imports
no wallet provider or environment secrets. Do not supply a mainnet key to these historical scripts.

From the repository root, the supported replacement is:

```sh
cd tests/contracts
npm ci
npm run deploy:plan
npm run deploy:local
```

This creates and verifies fresh **local** Ascension contracts. It does not migrate an external
deployment, upgrade the v2 contracts, transfer token balances or change $AGIALPHA settlement.
The guide covers evidence, failure recovery, native-state boundaries and the limits of rollback.
