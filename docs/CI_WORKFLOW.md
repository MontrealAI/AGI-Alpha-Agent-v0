[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# CI Workflow

The repository uses two distinct CI surfaces:

1. **✅ PR CI (`.github/workflows/pr-ci.yml`)** — canonical pull-request gate.
2. **🚀 Integration CI — Insight Demo (`.github/workflows/ci.yml`)** — full matrix for integration/release confidence.

## Triggers

### ✅ PR CI (canonical PR gate)
- `pull_request` targeting `main`
- `push` to `main`
- `merge_group`
- `workflow_dispatch`

Jobs:
- `Lint (ruff)`
- `Smoke tests`

### 🚀 Integration CI — Insight Demo (non-PR heavy matrix)
- `push` to `main`
- release tags: `v*`, `release-*`
- `workflow_dispatch`

This workflow intentionally does **not** run on `pull_request` or `merge_group`.
On `push` to `main`, it runs a **lean integration surface** (owner/actionlint, Linux lint+type and smoke-aligned pytest replay, docs-check).
On tags/manual dispatch it expands to the full release matrix (dual-version lint/type/test, docs build validation, Docker/signing/deploy path checks).
The lean `push` path intentionally skips release-only browser/audit, mutation-testing, benchmark-commentary, docs-build, and Docker-signing jobs to keep merge-to-`main` signal stable and high-value.

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

The **🩺 CI Health** workflow hard-monitors `pr-ci.yml` (required PR gate) and evaluates `ci.yml` as a hard surface only when triggered by that workflow; scheduled/manual freshness checks for `ci.yml` are informational warnings. Missing-run dispatch remains enabled for scheduled/manual watchdog runs, but `workflow_run` executions are rerun-only (`--rerun-failed`) to avoid redundant dispatches when a concrete upstream run already exists. Self-monitoring is opt-in via `--include-self`, and workflow-run executions keep reruns enabled so Repo-Healer can move past run-attempt-1 report-only triage when failures persist.
`scripts/check_ci_status.py` also enforces this policy directly: when `GITHUB_EVENT_NAME=workflow_run`, `--dispatch-missing` is ignored so watchdog reruns never fan out into unrelated workflow dispatches.

Use:

```bash
python scripts/check_ci_status.py --wait-minutes 5 --pending-grace-minutes 45 --stale-minutes 90
# optional: add --dispatch-failed for explicit failed-run redispatches
```

After editing workflow files, run:

```bash
python tools/update_actions.py
pre-commit run --files .github/workflows/ci.yml .github/workflows/pr-ci.yml .github/workflows/ci-health.yml
```
