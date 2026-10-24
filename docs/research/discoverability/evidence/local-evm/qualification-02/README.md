# Qualification 02: fresh execution with complete custody

This supplementary qualification closes the original run's lost-terminal-output
gap without overwriting its evidence or changing its historical qualification.
It uses the same retained Alpha source and the same four test files. It does
not add a Discoverability commissioning path or an economic result.

## Recorded execution

- **Result: 36 passing (12s), actual process exit 0.**
- Start: `2026-10-23T01:50:49.244518Z`.
- End: `2026-10-23T01:51:01.598596Z`.
- Wrapper elapsed wall time: `12.35409032300231` seconds.
- `tests-stdout.log` contains the complete test output; `tests-stderr.log`
  preserves npm's warning about an unknown inherited `http-proxy` configuration.
- `tests-execution.json` records the argument array, working directory,
  selected environment overrides, timestamps, exit status and log hashes.
- `receipts/` contains two **new** receipts emitted by the unchanged native
  adapter tests. The original receipts remain in the parent docket.

The selection is 15 lifecycle/identity tests, 15 marketplace/failure/recovery
tests, 3 conservation tests and 3 native-adapter tests. The bridge runs the actual
Python Journal and Ascension adapter against an in-process, unforked Hardhat
chain with simulated balances. The negative candidate report is paid without
candidate admission; a report lacking review quorum receives a full bounty
refund. The test output also records rejection, expiry, recovery, exact artifact
binding, integer rounding and conservation assertions.

The execution reused the already installed dependencies and compiled artifacts.
It was **not a clean bootstrap**, and its stdout does not claim a fresh Solidity
compilation. The earlier retained build-info remains the compiler evidence.
No packages were installed, source or assertions edited, compiler settings
changed, or mainnet/fork transaction submitted.

`source-before.json` and `source-after.json` contain 54 executable source,
configuration and lock-file identities. Every one equals the recovered archive's
identity; the before/after lists are identical. The 55th archive file is the
repository license, which is not an executable input. The source revision remains
the original executor-reported Alpha
`61532fb82621a065e668fd11e57289dcfb65c67b`; five contract Git blobs independently
match the prior source audit. This does not authenticate a complete Git checkout.

`installed-environment.json` captures Python 3.12.14 and its installed
distributions, Node 24.19.0, npm 11.9.0, Hardhat 2.29.1, ethers 6.17.0,
solc 0.8.37 and OpenZeppelin 5.6.1. These are observations of the reused
environment during this qualification, not a reconstruction of missing earlier
installation logs.

## Separate five-contract observation

After the tests completed, `snapshot.cjs` called the unchanged original
`fixture()` in a **separate process and fresh disposable chain instance**.
`separate-fixture-observation.json` records all five contract addresses,
deployed runtime byte lengths and Keccak-256 identities, deployment transactions,
actual getter values, chain/block identity, Hardhat instance metadata and
wall-clock observation time. Its own complete stdout, stderr and execution
receipt are retained. That operation took 1.1691486130002886 seconds and exited 0.

This observation must not be substituted into the original receipts' missing
Access/Oracle observations or represented as the exact test-receipt instance.
The main manifest preserves those original unknowns and links this separate
qualified observation. The identical deterministic addresses and overlapping
runtime identities arise from the unchanged local fixture; they are not proof
of mainnet deployment.

The local token is MockAGI code at the configured canonical identifier on chain
31337. All local accounts and balances are fixture data. No financial asset was
transferred, and no private key is published. Validator eligibility and quorum
are contract-test conditions; external reviewer independence is not established.

## Reproduction and integrity

`run.py` is the exact custody wrapper used. It refuses to overwrite an existing
`tests-execution.json`. The wrapper verifies source hashes before executing the
unchanged selection, captures both streams and exit status, verifies hashes
again, and only then runs the separate fixture observation. Its command array
is in the execution receipt. Use a new output directory and the parent docket's
reproduction instructions for another run; never overwrite these receipts.

The parent `FILES.json` inventories this directory as well as the original
recovered docket. Hashes provide consistency checks, not independent external
attestation. The existing Alpha adapter is now qualified with a retained fresh
test transcript. Discoverability-specific integration, four-repository installed
operation, independent review and realizable commercial value remain separate
claims requiring their own evidence.
