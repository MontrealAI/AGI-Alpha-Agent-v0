[Project notice](../../../docs/DISCLAIMER_SNIPPET.md)

# Capacity for the unchanged release campaign

The preceding exact-main regression job succeeded in 5,379 seconds, leaving only
21 seconds under its 90-minute enclosing limit. The offline test step alone took
4,938 seconds. `BUDGET_BASIS.json` preserves the primary run/job timestamps and
source identity. Those earlier results qualify their source only.

The expanded 1.47 candidate changes the regression job's enclosing allowance to
120 minutes. The existing strict orchestration contract changes its exact
expected value from 90 to 120. No assertion is removed, and all other test
selection, step/per-test deadlines, scripts, 80% coverage, five held source pins,
security/integrity checks, action SHAs, permissions, other job limits and paid-API
budgets remain unchanged. The current readiness note distinguishes this new
capacity from the preserved earlier recovery record. All three changed paths are
outside the 53 pinned legacy catalog sources.

**74 existing CI-contract tests pass** across install bounds, fast-release policy,
release preflight and artifact handoffs. Ruff lint passes. Raw workflow-byte
reconstruction and complete YAML equality prove that the enclosing timeout is
the only workflow change; byte reconstruction also proves the single exact test
expectation change. These checks do not establish that the longer hosted campaign
has completed or waive any release gate.

The required action updater was executed on exact throwaway script and `ci.yml`
copies. It exited zero and left real workflow action pins untouched. Its regex
matched no existing version-commented pin lines, so no current-version or network
verification is claimed. `update-actions.json` records its exact scope.

The installed pre-commit module reports version 4.2.0. Actionlint has no binary on
PATH or in the existing empty hook cache. The actionlint/file hook campaign is
**unrun because its environment is unavailable**; no Go/tool installation or
access expansion was attempted. Hosted actionlint remains required. The static
receipt records this limitation rather than treating it as a pass.

`focused-contracts.json` preserves the exact test command, result and output bytes
(zlib/base64 plus SHA-256). `static-checks.json` records preservation checks and
available/unavailable tools. No runtime, publisher, source packet, version, action
pin or other workflow is changed by this correction.
