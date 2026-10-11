[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.26.0 — Verifiable commissioning and easier first results

The guided first experience now includes a readable plan on the page and a clean **Print or save as PDF**
view in English and French. Review remains mandatory before keeping a result; changing inputs clears it.
No task entries are sent to a service or persisted by the planner.
Use the [installation and first-run guide](START_HERE.md) to run your own agent.

Contract settlement now verifies both sender and recipient balance deltas on payouts, and both the
paying contract's balance and total supply on burns. A negative review quorum cannot slash an agent
when an earlier rejecting validator has lost eligibility. Regression tests demonstrate rollback and timeout recovery.

The separate mainnet toolchain generates five unsigned CREATE transactions and two governance CALLs,
checks finalized dependency/governance/ENS/nonce configuration and verifies a fresh deployment's
bytecode and complete bindings. Compiler inputs, exact source revision, lock digest and constructor
arguments accompany the plan. Existing disposable Hardhat and disabled Truffle boundaries remain.

Hardhat, ethers and OpenZeppelin are pinned to updated versions; Solidity 0.8.37 targets Cancun explicitly.
Reviewed compatibility overrides address transitive advisories. A full npm audit of the contract build
toolchain now blocks publication on moderate or higher findings. Remaining low-severity legacy elliptic
findings are documented; no production keys are imported by the toolchain's scripts.

## Validation and operational scope

The existing exact-commit release gates are retained. The expanded contract suite includes adversarial
token behavior, revoked validator recovery, wrong-chain/configuration/nonce checks, RPC method restrictions,
checksum failure and execution of the prepared bytecode. Browser acceptance checks readable and printable
copies against the actual downloaded plan, alongside EN/FR, keyboard, mobile and automated accessibility checks.
The published manifest identifies the exact accepted commit and actual gate results.

This is **not an independently audited or commissioned mainnet deployment**. Operator addresses,
real-token mainnet-fork results, source verification and independent security/economic review remain
required. Follow [mainnet commissioning](MAINNET_READINESS.md). No mainnet transaction was sent.
Neither automated accessibility checks nor static hosting establish universal usability or billion-user capacity.

Native journal and token constants are unchanged. Solidity bytecode changes require a fresh deployment;
existing non-upgradeable deployments cannot be upgraded in place. Preserve historical receipts and use
[a separately reviewed migration](MAINNET_READINESS.md#recovery-and-limits) for any funded deployment.
All original research, diagrams, demonstrations and media remain preserved.
