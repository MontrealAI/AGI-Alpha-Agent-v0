[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.28.1 — Contract qualification and reproducible verification

This maintenance release makes contract build and verification evidence easier to check, documents
which compiler belongs to each deployment, and corrects bounded defects in the separate legacy v2
contracts. Start with the [contract warning and verification guide](MAINNET_DEPLOYMENT.md#understand-a-contract-warning).
For the installed agent, use the [operator start guide](START_HERE.md).

## What changes

- Keep the current Solidity 0.8.37/Cancun build separate from the immutable October 11
  Solidity 0.8.24/Paris deployment archive. Both use via IR and optimizer 200; their dependency versions
  also differ. Verification must use the exact sources, settings and constructor arguments of its address.
- Add `npm run compile:strict`: force a fresh build with the npm-locked Solidity compiler and reject every
  Solidity warning. The baseline compilation already emitted no Solidity warnings; this prevents regressions.
  Hardhat debugging notices, dependency advisories and explorer verification status remain distinct checks.
- Add `mainnet:verification-package` for either the recorded deployment or an exact reviewed new plan.
  Export all five Standard JSON inputs, ABI-encoded constructor arguments, Etherscan V2 request parameters
  and file digests without credentials, explorer submissions or transactions.
- Correct legacy v2 job admission for zero rewards and expired deadlines/applications; retain the actual
  client in cancellation/delist events; bound combined fees/burn and certificate payout percentages;
  clear certificate sale listings when ownership changes.
- Add targeted legacy regressions and preserve the existing Ascension settlement, historical deployment,
  read-only verification, source-preservation and release-publication gates.
- Synchronize active release/version guides and browser caches while retaining the SUCCESSOR Ω workshop,
  bilingual onboarding, every historical release note, original research and flowcharts.

## Existing Ethereum contracts

The five recorded Ascension contracts remain at the same addresses, with the same deployed code,
immutable bindings and ownership. This release does not deploy a contract, send a transaction, transfer
funds, change a governor, migrate state or replace the canonical external $AGIALPHA token.

The archived deployment predates the current payout/burn balance checks and rejection-quorum safeguards.
Those differences still require an explicit operational decision. Explorer notices about an old compiler
can remain on historical addresses; changing the repository cannot remove their deployed compiler
provenance. The exact explorer warning text must be examined before attributing any specific notice.
See the [deployed owner guide](MAINNET_DEPLOYMENT.md) and the [separate new-deployment guide](MAINNET_READINESS.md).

The `contracts/v2` suite is retained legacy material, separate from those five Ascension addresses.
Its bounded fixes do not establish a commissioned end-to-end v2 system: the legacy registry/validation
integration has additional interface gaps. Do not treat that suite as deployment-ready.

## Evidence, upgrade and remaining qualification

A build without Solidity warnings establishes the diagnostics of the exact tested compilation, not a
proof of flawless behavior. Exact-bytecode checks do not replace independent security/economic review,
a real-token mainnet-fork lifecycle or the operator's commissioning decision. Hardhat debugging-support
notices and separately reported dependency findings must remain visible.

Publication requires the full existing acceptance gates on the exact integrated commit. Read the release
manifest and matching validation archive for actual accepted results, commit and producer identity;
this source document does not record a future CI pass. Mainnet commissioning and any future signed
deployment or migration remain separate, unresolved operations.

No native journal migration is introduced. Follow the [backup and recovery procedure](OPERATIONS.md).
The [1.28.0 workshop release](RELEASE_NOTES_1.28.0.md) and earlier deployment archive remain intact.

**En français.** Cette version améliore les contrôles de compilation et la reproduction des fichiers
à vérifier, et corrige des défauts circonscrits de l'ancien module v2. Elle ne modifie aucun contrat sur
Ethereum. Les cinq adresses existantes conservent leur code du 11 octobre et leurs paramètres historiques.
La validation indépendante et la mise en service restent à effectuer séparément.
