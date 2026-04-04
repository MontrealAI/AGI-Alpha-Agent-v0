# Continuous Integration enforcement checklist

Use this checklist to keep CI truthful, minimal, and reviewer-friendly.

1. **Canonical PR gate**
   - Keep **✅ PR CI** as the only required PR workflow.
   - Required checks on `main`:
     - `✅ PR CI / Lint (ruff)`
     - `✅ PR CI / Smoke tests`

2. **Branch protection settings**
   - Enable **Require status checks to pass before merging**.
   - Enable **Require branches to be up to date before merging**.
   - If merge queue is enabled, ensure it uses the same required checks.
   - Verify/enforce configuration:
     ```bash
     python scripts/verify_branch_protection.py --apply --branch main
     ```

3. **Heavy CI stays off PR gating**
   - Keep **🚀 Integration CI — Insight Demo** for post-merge/release confidence:
     - `push` to `main`
     - release tags (`v*`, `release-*`)
     - manual dispatch
   - Keep push-to-main scope lean/stable; reserve docs-build + Docker/signing + full matrix replay for tag/manual release contexts.
   - Do not add this full matrix back to required PR checks unless the PR gate is redesigned and docs/scripts are updated together.

4. **CI health monitoring**
   - Keep **🩺 CI Health / CI watchdog** active to enforce required PR-gate health and context-aware remediation.
   - Default behavior skips self-monitoring; only opt in with `--include-self` when explicitly auditing the watchdog workflow itself.
   - For automatic branch-protection remediation, set `ADMIN_GITHUB_TOKEN` with branch admin scope.
   - Without admin token, health checks run in read-only mode.

5. **Consistency checks after CI edits**
   - Update docs (`README.md`, `docs/CI_WORKFLOW.md`, this file).
   - Update required check sources (`scripts/required_checks.json`, defaults in `scripts/verify_branch_protection.py`).
   - Run:
     ```bash
     python tools/update_actions.py
     pre-commit run --files .github/workflows/ci.yml .github/workflows/pr-ci.yml .github/workflows/ci-health.yml
     ```

6. **Operational status checks**
   - Poll workflow state when debugging:
     ```bash
     python scripts/check_ci_status.py --wait-minutes 5 --pending-grace-minutes 45 --stale-minutes 90
     # optional: add --dispatch-failed for explicit failed-run redispatches
     ```
   - Use `--once` for immediate pass/fail status.

Following this checklist keeps PR gating small and high-signal while preserving deep validation on integration and release paths.
