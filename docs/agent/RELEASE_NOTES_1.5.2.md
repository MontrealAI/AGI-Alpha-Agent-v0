# $AGIALPHA Agent 1.5.2 — current CI Health reporting

The 1.5.1 acceptance pipeline and public user workflows passed. Independent badge verification then
found that the Health image aggregated older failed watchdog invocations with the latest successful
run on the same commit. It could stay red after the issue had recovered.

This patch makes the CI Health badge follow GitHub's latest workflow result on main and updates the
badge guide to explain its scope. Earlier failure records remain intact. Integration and Smoke keep
their current-commit matrix badges; dependency auditing and exact-commit release gates remain required.

Current install, container and browser version references advance to 1.5.2. All demos, flywheels, the
original white paper and previous releases remain preserved. No runtime, journal, token accounting,
model or dependency-lock change is introduced. Upgrade and rollback use the existing paused backup
and restore procedure in [the operator guide](OPERATIONS.md).

The release repeats the full runtime, model, Docker, EVM, regression, browser, mobile, offline and
public Pages acceptance checks. A separate public verification checks rendered badge titles, release
checksums, the audited lock and preserved releases. Consult the manifest and validation archive for
the exact tested commit and results.

The supported private-operator/browser scope and the white paper's remaining research boundaries
are unchanged; see [release readiness](RELEASE_READINESS.md).
