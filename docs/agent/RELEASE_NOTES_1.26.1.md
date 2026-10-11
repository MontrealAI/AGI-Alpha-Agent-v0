[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.26.1 — Mainnet deployment evidence and owner verification

For installation and the first local run, follow the [first-run guide](START_HERE.md).

The October 11 Ascension Ethereum mainnet deployment now has a public, reproducible source record and
a [plain-language owner guide](MAINNET_DEPLOYMENT.md). Five contracts were deployed, their bindings
checked, and Oracle/JobMarket ownership accepted by the final owner. Etherscan source verification is
operator-reported; its API response/transcript is not included in the public archive. No further ownership
acceptance is required. The record includes all eleven transactions, complete runtime hashes, exact compiler
inputs, constructor arguments, dependency metadata, historical costs and public operator evidence.

`npm run mainnet:record-check --prefix tests/contracts` verifies the archive locally.
`mainnet:record-verify` checks finalized receipts, full bytecode, bindings and governance through a read-only
HTTPS RPC transport. It never loads a signer or broadcasts a transaction. Its report explicitly distinguishes
deployment verification from participant commissioning and public-funding approval.

## Deployed source and newer fixes

The recorded contracts use Solidity 0.8.24 and OpenZeppelin 5.4.0. They **predate** the settlement hardening
in the current Solidity 0.8.37 / OpenZeppelin 5.6.1 source. The current fixes remain intact. A regression
executes the archived creation bytecode on an isolated EVM and demonstrates its earlier revoked-rejection
behavior alongside the fixed current-source regression. Publishing this release does not upgrade the
existing contracts. A separately reviewed fresh deployment is required to install new bytecode.

Resolve this difference before admissions or funding. The source archive is provenance, not a recommendation
to deploy the historical code again. Existing local fixtures remain isolated. The current unsigned multisignature
deployment planner retains its separate schema, governance model and fresh-deployment verification.

## Delivery and validation

The README, Protocol Desk and mainnet guides distinguish recorded deployment, current candidate source,
and local demonstrations. Existing English/French onboarding, demos, research, diagrams, native identities
and journals remain. No on-chain transaction, automatic migration or participant admission is performed by
this maintenance release.

Acceptance includes record tampering, wrong-chain/finality, receipt/calldata/ownership/runtime mismatch,
RPC mutation rejection, historical behavior and current settlement regressions. Existing repository release
gates still apply to the exact integrated commit. Publication depends on their actual success and public
Pages acceptance; gate definitions alone are not evidence of a passed release.

Preserve your original deployment directory and independent backups. Use the new read-only record verifier
for the existing addresses, and the [current commissioning guide](MAINNET_READINESS.md) for a separately
reviewed new deployment. No native journal migration is required.
