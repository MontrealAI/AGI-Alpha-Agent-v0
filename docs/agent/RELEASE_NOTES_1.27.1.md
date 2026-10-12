[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.27.1 — Development-toolchain maintenance

Keep using [your personal SUCCESSOR Ω lab](../successor/play/index.html), including the complete
offline HTML download introduced in [1.27.0](RELEASE_NOTES_1.27.0.md). This patch refreshes the
historical web client's development dependencies and aligns current release metadata and guides.
For a separately installed agent, follow the [operator start guide](START_HERE.md) and the
[backup, upgrade and recovery instructions](OPERATIONS.md).

## Changes

- Refresh `alpha_factory_v1/core/interface/web_client/package-lock.json` within the existing
  package version ranges, including Percy patch updates and affected transitive tools.
- Remove unused development dependency subtrees. Every changed lockfile package is development-only;
  production dependency versions, application code and contract source are unchanged.
- Update current package, catalog, browser and operator-guide version references to 1.27.1.
- Restore the missing 1.27.0 entry in the root changelog and retain all previous release notes,
  original research, demonstrations and flowcharts.

## Dependency scope

The full npm audit on October 12, 2026 reports **34 remaining development findings: 23 high,
nine moderate and two low**, compared with the earlier 39 (27 high, ten moderate and two low).
This is a partial improvement, not a clean development-toolchain audit. The remaining paths include
Cypress, Percy and Workbox and need separately tested compatibility changes. Do not apply a forced
Cypress major upgrade or Workbox downgrade solely to make the audit count disappear.

The release's production dependency audit remains mandatory and separate. Development tools are
not part of the supported installed operator dependency set, but still require maintenance where used.
Audit results describe the advisory database at scan time; counts may change as advisories are updated.

## Acceptance and operation

Publication requires the exact final integrated commit to pass the existing complete acceptance
workflow, including the historical web client browser tests and build, dependency gates, native
runtime tests, preserved research checks and public Pages acceptance. The published manifest and
validation archive identify the tested source and actual results; this source note is not a test receipt.

No journal migration, contract deployment or on-chain transaction is performed. Keep existing backup
and recovery procedures. Independent qualification, production signing and mainnet participant
commissioning remain unresolved under the existing [release readiness requirements](RELEASE_READINESS.md).
