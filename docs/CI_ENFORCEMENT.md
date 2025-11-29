# Continuous Integration enforcement checklist

Use this checklist to keep CI visible and required on both pull requests and the `main` branch.

1. **Branch protection and merge queue**
   - In **Settings → Branches → Branch protection rules**, edit the rule for `main` (or create one).
   - Enable **Require status checks to pass before merging** and **Require branches to be up to date**.
   - If you use GitHub's merge queue, enable it for `main` and ensure the queue uses the same required checks below. The workflows now listen for `merge_group` events so queued merges receive the full CI signal before landing.
    - Add these required checks *using the exact names shown in the GitHub UI* so they appear on every PR:
      - `✅ PR CI / Lint (ruff)`
      - `✅ PR CI / Smoke tests`
      - `🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.11)`
      - `🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.12)`
      - `🚀 CI — Insight Demo / ✅ Actionlint`
      - `🚀 CI — Insight Demo / ✅ Pytest (3.11)`
      - `🚀 CI — Insight Demo / ✅ Pytest (3.12)`
      - `🚀 CI — Insight Demo / Windows Smoke`
      - `🚀 CI — Insight Demo / macOS Smoke`
      - `🚀 CI — Insight Demo / 📜 MkDocs`
      - `🚀 CI — Insight Demo / 📚 Docs Build`
      - `🚀 CI — Insight Demo / 🐳 Docker build`
      - `🚀 CI — Insight Demo / 📦 Deploy`
      - `🚀 CI — Insight Demo / 🔒 Branch protection guardrails`
      - `🩺 CI Health / CI watchdog`
   - Run `python scripts/verify_branch_protection.py --apply --branch main` (export `GITHUB_TOKEN`) to confirm the rule includes every check above and still requires branches to be up to date. Passing `--apply` automatically re-applies the required checks when they drift so the CI badge stays green. The **🩺 CI Health** workflow runs this helper automatically so regressions are caught quickly.
   - The helper’s default required-check list now mirrors the table above, including the deploy and guardrail jobs plus the **🩺 CI Health / CI watchdog** gate, so a bare run of the script exercises the full protection policy. The guardrail job itself now runs on forked PRs and merge-queue runs in read-only mode when only the default `GITHUB_TOKEN` is available, ensuring the required check always reports while repositories with `ADMIN_GITHUB_TOKEN` continue to self-heal missing protections automatically.
   - Optionally add additional owner-only workflows after verifying they succeed (for example, `📦 Browser Size / size-check`, `🔒 Container Security / sbom-scan-sign`, and `🚀 CI — Insight Demo / lint-type` + `🚀 CI — Insight Demo / tests`).
   - If the UI shows different names (for example, because a job label changed), copy the string verbatim from the latest workflow run; otherwise the protection rule will not attach and PRs will not block on CI.
   - **Permissions:** provide a fine-grained or classic PAT with administration rights to branch protection (store it as `ADMIN_GITHUB_TOKEN`) so the verification steps in `ci.yml` and `ci-health.yml` can query protection rules. GitHub's default `GITHUB_TOKEN` does **not** include this scope and receives `403 Resource not accessible by integration` when calling the branch-protection API, so the guardrails require the dedicated admin token even though the workflows themselves only request standard Actions/contents permissions. The guardrail job now still runs with the default token when the admin secret is absent so the required check remains visible and green on PRs while emitting a notice about read-only mode.
   - Ensure no environment approval gates block CI. Remove any required reviewers or timeouts on the `ci-on-demand` (or similarly named) environment so the matrix jobs start automatically instead of sitting in a permanent "Pending approval" state.

2. **Badges stay green**
- Confirm the badges in `README.md` show green shields for **PR CI**, **🚀 CI — Insight Demo**, **🔥 Smoke Test**, and **🩺 CI Health**. If any badge is red, open the corresponding workflow run, fix the failure, and re-run the pipeline. The `ci.yml` pipeline now triggers on pushes and pull requests, so badges will refresh automatically after merges. A failing badge should always correspond to a visible check on the PR because `ci.yml` also re-validates the canonical `$AGIALPHA` token configuration before enforcing branch protection.
- The primary **🚀 CI — Insight Demo** workflow lives at `https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/workflows/ci.yml`. Keep it green by re-dispatching from the Actions tab after fixes so required checks and badges reflect the latest status.
- When you need to rebuild the status bubble outside of normal events (for example, after temporarily disabling runners), dispatch **🚀 CI — Insight Demo** from **Actions → 🚀 CI — Insight Demo** (or `gh workflow run ci.yml`). The **🩺 CI Health** workflow (scheduled hourly, auto-triggered after every CI/pr/smoke completion, and manually dispatchable) also re-runs `ci.yml`, `pr-ci.yml`, and `smoke.yml` when it detects stale pending runs (queued longer than ~10 minutes) and cancels stuck runs older than one hour.
- The owner gate now permits `github-actions[bot]` when a dispatch originates from the **🩺 CI Health** watchdog so automated re-runs can recover badges without waiting for a human owner to click "Re-run".
- Set `ADMIN_GITHUB_TOKEN` as a repository secret with admin rights when you want CI to automatically enforce branch protection and required checks; without it, the branch-protection step runs in read-only mode using the default `GITHUB_TOKEN` so forked PRs still pass while owners retain the option to enforce protections from green runs.
  - Run `python scripts/check_ci_status.py --wait-minutes 20 --pending-grace-minutes 10 --stale-minutes 60 --cancel-stale --dispatch-missing --ref main` to confirm the latest runs for `ci.yml`, `pr-ci.yml`, `smoke.yml`, and `ci-health.yml` all report `success`. **Export `GITHUB_TOKEN` or `GH_TOKEN`** (a fine-grained or classic PAT) so the script can authenticate, raise rate limits, and automatically dispatch or cancel workflows when needed. The command polls queued or in-progress runs before failing, exits non-zero, and prints deep links when any workflow is pending or failed so you can jump straight to the culprit. If you see a `403` or `401` error, double-check the token scope and repository access. Add `--once` when you want an immediate status check with zero grace period; pending runs will cause a failure so you can unblock badges quickly. When the checker runs inside a GitHub Actions workflow, it automatically skips the workflow that invoked it to avoid dispatching a new copy of itself.
  - `python scripts/check_ci_status.py --once` now includes `ci-health.yml` by default, so a quick no-token check surfaces watchdog regressions alongside the primary pipelines.
  - When debugging a red badge without access to the Actions UI, pass the same token to `gh run view <run-id> --log` or `curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/<run-id>/jobs?per_page=100` to retrieve job summaries. GitHub hides job metadata and log archives from unauthenticated callers with a `403 Must have admin rights to Repository` error, so always supply an authenticated token before assuming a workflow is missing jobs.

3. **Visibility on PRs**
   - Ensure "Allow GitHub Actions to create and approve pull requests" remains enabled so status checks and summaries appear inline on PRs.
   - Keep both `pr-ci.yml` and `ci.yml` triggered on `pull_request` and `push` to `main` so checks always run on the latest commits and stay visible to reviewers.

4. **Local preflight**
   - Before opening a PR, run `pip install -r requirements.lock -r requirements-dev.lock` once, then execute `pytest -m smoke tests/test_af_requests.py tests/test_cache_version.py tests/test_check_env_core.py tests/test_check_env_network.py tests/test_config_settings.py tests/test_config_utils.py tests/test_ping_agent.py -q` to mirror the PR CI smoke job.
   - Run `python scripts/check_agialpha_config.py` to confirm the canonical `$AGIALPHA` address (`0xa61a3b3a130a9c20768eebf97e21515a6046a1fa`) and 18-decimal setting match `token.config.js`, the Solidity constants, and any workflow-provided environment variables before dispatching CI.
   - Run `pre-commit run --all-files` to catch formatting issues early; the PR CI job uses the same hooks.

Following these steps keeps CI results visible, enforces the gates on `main`, and helps non-technical reviewers trust that every change lands with a green signal.
