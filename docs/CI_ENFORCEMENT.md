# Continuous Integration enforcement checklist

Use this checklist to keep CI visible and required on both pull requests and the `main` branch.

1. **Branch protection**
   - In **Settings → Branches → Branch protection rules**, edit the rule for `main` (or create one).
   - Enable **Require status checks to pass before merging** and **Require branches to be up to date**.
   - Add these required checks *using the exact names shown in the GitHub UI* so they appear on every PR:
     - `✅ PR CI / Lint (ruff)`
     - `✅ PR CI / Smoke tests`
     - `🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.11)`
     - `🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.12)`
     - `🚀 CI — Insight Demo / ✅ Pytest (3.11)`
     - `🚀 CI — Insight Demo / ✅ Pytest (3.12)`
     - `🚀 CI — Insight Demo / Windows Smoke`
     - `🚀 CI — Insight Demo / macOS Smoke`
     - `🚀 CI — Insight Demo / 📜 MkDocs`
     - `🚀 CI — Insight Demo / 📚 Docs Build`
     - `🚀 CI — Insight Demo / 🐳 Docker build`
   - Optionally add additional owner-only workflows after verifying they succeed (for example, `📦 Browser Size / size-check`, `🔒 Container Security / sbom-scan-sign`, and `🚀 CI — Insight Demo / lint-type` + `🚀 CI — Insight Demo / tests`).
   - If the UI shows different names (for example, because a job label changed), copy the string verbatim from the latest workflow run; otherwise the protection rule will not attach and PRs will not block on CI.
   - Ensure no environment approval gates block CI. Remove any required reviewers or timeouts on the `ci-on-demand` (or similarly named) environment so the matrix jobs start automatically instead of sitting in a permanent "Pending approval" state.

2. **Badges stay green**
   - Confirm the badges in `README.md` show green shields for **PR CI**, **🚀 CI — Insight Demo**, **🔥 Smoke Test**, and **🩺 CI Health**. If any badge is red, open the corresponding workflow run, fix the failure, and re-run the pipeline. The `ci.yml` pipeline now triggers on pushes and pull requests, so badges will refresh automatically after merges.
   - When you need to rebuild the status bubble outside of normal events (for example, after temporarily disabling runners), dispatch **🚀 CI — Insight Demo** from **Actions → 🚀 CI — Insight Demo** (or `gh workflow run ci.yml`). The **🩺 CI Health** workflow (scheduled every six hours and manually dispatchable) also re-runs `ci.yml`, `pr-ci.yml`, and `smoke.yml` when it detects stale pending runs.
   - Run `python scripts/check_ci_status.py --wait-minutes 20 --pending-grace-minutes 10 --cancel-stale --dispatch-missing --ref main` (set `GITHUB_TOKEN` to avoid rate limits) to confirm the latest runs for `ci.yml`, `pr-ci.yml`, and `smoke.yml` all report `success`. The command polls queued or in-progress runs before failing, exits non-zero, and prints deep links when any workflow is pending or failed so you can jump straight to the culprit. If you see a `403` or `401` error, export `GITHUB_TOKEN` so the script can authenticate and avoid API throttling. Add `--once` when you want an immediate status check with zero grace period; pending runs will cause a failure so you can unblock badges quickly.

3. **Visibility on PRs**
   - Ensure "Allow GitHub Actions to create and approve pull requests" remains enabled so status checks and summaries appear inline on PRs.
   - Keep both `pr-ci.yml` and `ci.yml` triggered on `pull_request` and `push` to `main` so checks always run on the latest commits and stay visible to reviewers.

4. **Local preflight**
   - Before opening a PR, run `pip install -r requirements.lock -r requirements-dev.lock` once, then execute `pytest -m smoke tests/test_af_requests.py tests/test_cache_version.py tests/test_check_env_core.py tests/test_check_env_network.py tests/test_config_settings.py tests/test_config_utils.py tests/test_ping_agent.py -q` to mirror the PR CI smoke job.
   - Run `pre-commit run --all-files` to catch formatting issues early; the PR CI job uses the same hooks.

Following these steps keeps CI results visible, enforces the gates on `main`, and helps non-technical reviewers trust that every change lands with a green signal.
