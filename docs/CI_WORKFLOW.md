[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# CI Workflow

The repository uses two distinct CI surfaces:

1. **✅ PR CI (`.github/workflows/pr-ci.yml`)** — canonical pull-request gate.
2. **🚀 CI — Insight Demo (`.github/workflows/ci.yml`)** — full matrix for integration/release confidence.

## Triggers

### ✅ PR CI (canonical PR gate)
- `pull_request` targeting `main`
- `push` to `main`
- `merge_group`
- `workflow_dispatch`

Jobs:
- `Lint (ruff)`
- `Smoke tests`

### 🚀 CI — Insight Demo (non-PR heavy matrix)
- `push` to `main`
- release tags: `v*`, `release-*`
- `workflow_dispatch`

This workflow intentionally does **not** run on `pull_request` or `merge_group`.
It contains heavier checks (multi-version lint/type/test, docs verification, Docker build/signing, deploy-path checks) that are high value after merge but noisy/duplicative on every PR.

## Branch protection (required checks)

Configure `main` branch protection with these required checks:

- `✅ PR CI / Lint (ruff)`
- `✅ PR CI / Smoke tests`

Keep **Require branches to be up to date** enabled.

Validate/enforce with:

```bash
python scripts/verify_branch_protection.py --apply --branch main
```

## CI health

The **🩺 CI Health** workflow monitors `pr-ci.yml`, `ci.yml`, and `ci-health.yml`, and can cancel stale runs/re-dispatch missing runs.

Use:

```bash
python scripts/check_ci_status.py --wait-minutes 5 --pending-grace-minutes 45 --stale-minutes 90
```

After editing workflow files, run:

```bash
python tools/update_actions.py
pre-commit run --files .github/workflows/ci.yml .github/workflows/pr-ci.yml .github/workflows/ci-health.yml
```
