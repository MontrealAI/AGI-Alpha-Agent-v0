[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.31.2 — Safer Mainnet reads and current operator guidance

Start with the [English/French first-use guide](START_HERE.md), explore the
[public workspace](../index.html), or follow the [Mainnet preparation guide](MAINNET_READINESS.md).
Use matching assets from one published release and its manifest to identify the accepted source.

## What changes

- Hardhat preparation and verification now accept only JSON-RPC 2.0 responses with the matching
  request ID, a result and no error field. A valid `null` result remains available for absent receipts.
- Provider response bodies are capped at 2 MiB, including streamed bodies without a size header.
  Oversized streams are cancelled; malformed JSON, mismatched replies and provider details remain
  redacted. Failed reads produce no verified output file.
- The active contract and Mainnet guides use this release checkout and explain the new failure handling.
  Current browser, cache, catalog and package labels remain synchronized. Prior release notes,
  deployed contracts, research, diagrams and the study's exact report pack are retained.

## Verification and supported scope

Focused tests exercise valid and null responses, wrong protocol versions and IDs, conflicting error/result
fields, malformed bodies, oversized declared and streamed bodies, cancellation, the exact size boundary
and credential redaction. Existing deployment, archived-record and explorer-package tests remain required.
The full release workflow also requires strict production-source compilation, current toolchain audits,
contract lifecycle tests, native runtime matrices, full regression and types, both rebuilt galleries,
public HTTPS browser acceptance and re-downloaded release-asset checksums on the exact integrated commit.
Consult the matching manifest and validation archive for the actual results.

The October 14 toolchain audit found no moderate, high or critical advisories. Its legacy Hardhat
dependency graph retains low-severity elliptic findings; the audit is a dated snapshot. Strict compilation
covers all 15 production Solidity sources and their dependencies without compiler warnings. Compilation
and finite tests do not replace an independent contract audit or operational commissioning.

This is a software maintenance release for the documented private operator, public browser workspaces
and isolated contract rehearsal. Mainnet tools remain unsigned and read-only. The earlier October 11
deployment is immutable and predates later settlement fixes; new funding and new commitments remain
blocked in its wallet workspace. No deployed bytecode, economics, identity or journal format changes.
Independent exact-source review, real-token fork evidence and deliberate operator commissioning remain
necessary for a new production deployment. The study retains its original simulated-owner boundaries.

## Upgrade and recovery

Follow [backup, installation and deliberate recovery](OPERATIONS.md). Keep the prior environment,
private project capsules, unresolved wallet intents and independently retained journal checkpoint.
Select a new output path when retrying a failed Mainnet read. No journal migration is introduced.

**Français.** Les outils Mainnet refusent les réponses RPC mal formées, les identifiants incorrects et
les corps de plus de 2 Mio. Les flux trop grands sont interrompus; les détails du fournisseur restent
masqués. Consultez le guide de démarrage et utilisez les fichiers d'une même publication. Les contrats
déployés, projets, recherches et schémas sont conservés. Cette maintenance ne donne aucune autorisation
de financement ni de mise en service Mainnet.
