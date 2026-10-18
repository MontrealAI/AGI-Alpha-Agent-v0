[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.34.0 — New Mainnet deployment record

This release records the five new Ethereum Mainnet contracts and their finalized
one-time graph bindings. See [the current deployment record](CURRENT_MAINNET_DEPLOYMENT.md)
for exact addresses, transaction hashes, source provenance and remaining operating limits.

## Included

- Read-only public contract directory, explorer links, machine-readable deployment
  record and source/report provenance. Historical October 11 evidence remains unchanged.
- Exact deployed source compiler profile and creator/authority tooling from
  `c0fc5217e364a39a4cd123d17a8317c06b80f820`, including the narrow SOL-2026-7
  workaround, strict profile admission and regression controls.
- Early publication preflight catches an already-used version before expensive
  acceptance jobs. Immutable tags, exact-current-main, full acceptance, uploaded
  byte verification and served Pages checks remain required.

## Scope and limits

The deployment and scoped graph verification are recorded separately from activation,
external dependency qualification, security assurance and off-chain commissioning.
No public funding or activation is approved by this release. There is no global pause.
Existing wallet profiles and historical contract addresses are not automatically migrated.
External authority closeout completed at 2026-10-18 15:24:15.848 UTC, releasing both
original actor leases without signing or broadcasting transactions. The original
deployment session remains historically incomplete at sequence 20 with its journal unchanged. Actual manual binding calls were verified post hoc;
that evidence does not recreate missing pre-sign intent. See the record for deviations.

The release source includes publication changes and therefore has a different commit
from the immutable deployed source. Use the deployment record's exact commit/tree when
reproducing deployed contracts. The compiler workaround is narrow, not a guarantee
against every compiler defect or a claim of production readiness.

[First-use guide](START_HERE.md) · [Release readiness](RELEASE_READINESS.md)
