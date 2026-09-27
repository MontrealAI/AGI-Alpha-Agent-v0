[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.12.1 — Evidence integrity and complete release delivery

The final review reproduced a broken mirrored Protocol Desk, signed receipts whose approval flags
contradicted their completed state, and boolean/float values accepted as integer evidence. This patch
fixes those cases without changing journal storage, contract rules or the original architecture.

## Reviewed evidence stays explicit

Portable receipts require the exact schema and an explicit boolean approval. Allocation totals,
schedule metrics and operation indices retain strict integer types; code counts and accuracy reject
boolean aliases. The Ascension verifier rechecks these constraints even when every signature is valid.
These checks establish internal consistency; independent review of meaning and economic usefulness
remains necessary.

## Every route and release asset is usable

The Protocol Desk resolves evidence and its service worker from the shared module location, so the
canonical and preserved mirrored routes both work online and offline. Browser acceptance checks exact
HTML, code and evidence bytes, the published commit/version, calculators, downloadable receipts,
keyboard interaction, WCAG A/AA checks and mobile layout. Public release finalization now requires
this complete protocol report for the exact packaged source.

The release includes [Start here](START_HERE.md), the [factory guide](FACTORY_GUIDE.md), the
[Ascension protocol guide](ASCENSION_PROTOCOL.md), and an operator-guide archive with usable links.
Code/documentation links outside that archive point to the exact source commit; browser links open
the current public workspace. The original manuscript remains byte-identical. Packaging rejects
uncommitted tracked changes and records the package/diagram/media preservation report.

## Upgrade and scope

No journal migration or contract redeployment is introduced. Follow [operations and recovery](OPERATIONS.md)
to pause, back up, install into a new environment and verify a restored journal before resuming.
The maintained private runtime and undeployed Ascension reference retain their documented scope.
Finite acceptance tests do not establish general intelligence, independent counterparties or mainnet commissioning.
