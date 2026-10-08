// SPDX-License-Identifier: Apache-2.0
// Preserve the historical path, but stop before artifact loading or transactions.
module.exports = async function () {
  throw new Error(
    "Legacy Truffle migration is unsupported: this repository does not contain its Deployer contract. " +
    "See truffle/README.md. From tests/contracts run npm ci, npm run deploy:plan, then npm run deploy:local " +
    "for a verified disposable Hardhat deployment. No token or external-chain migration is performed."
  );
};
