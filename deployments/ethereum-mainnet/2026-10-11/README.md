# Ascension mainnet deployment — October 11, 2026

This is the public record of an existing deployment, not a deployment configuration to execute.
Start with the [owner and verification guide](../../../docs/agent/MAINNET_DEPLOYMENT.md).

- `manifest.json` binds five addresses, eleven transactions, final ownership, runtime hashes, historical gas
  costs, compiler identity and SHA-256 digests of the archive files.
- `compiler-input.json` contains every exact Solidity standard-JSON input, including dependency source.
- `compiled-contracts.json` contains the original ABI, creation/runtime bytecode and immutable positions.
- `runtime-code.json` contains the complete observed deployed runtimes, including immutable values.
- `sources/` preserves the seven deployed project sources byte for byte. They intentionally differ from
  newer settlement fixes in the repository's current `contracts/ascension/` directory.
- `original-toolchain/` preserves configuration and dependency metadata for provenance. It is **not a
  runnable operator package**; do not run its historical npm scripts or install it to operate this deployment.
- `operator-build-fingerprint.json` preserves the original package's file hashes. The full original
  operator package remains in the operator's private deployment backup; this archive contains selected evidence.
- `evidence/` contains the public preflight, isolated-fork rehearsal and final operator verification.
  The fork used development-chain impersonation, not live mainnet authority.

Use the repository root's `npm run mainnet:record-check --prefix tests/contracts` for archive integrity,
and the guide's read-only command for finalized mainnet verification. No private credentials are included.
The recorded Etherscan source-verification result comes from the operator's successful API output;
recheck the linked explorer pages independently when relying on that result.

To reproduce the compiler output, use **solc 0.8.24+commit.e11b9ed9**, pass `compiler-input.json` through
its standard-JSON interface, and compare the named contract ABI/bytecode/immutable references with
`compiled-contracts.json`. All 35 input sources are embedded; no source flattening or library substitution
is needed. Constructor arguments are reconstructed by `tests/contracts/scripts/mainnet-record.js`.
Current contract compilation uses a newer source/dependency/compiler profile and is a different build.

These non-upgradeable contracts lack the newer payout/burn balance and revoked-rejection-quorum checks.
Deployment and Ledger ownership are verified; participant commissioning and public funding are not approved.
