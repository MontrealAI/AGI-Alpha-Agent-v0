# Continuous Integration enforcement checklist

Use this checklist to keep CI visible and required on both pull requests and the `main` branch.

1. **Branch protection**
   - In **Settings → Branches → Branch protection rules**, edit the rule for `main` (or create one).
   - Enable **Require status checks to pass before merging** and **Require branches to be up to date**.
   - Add these required checks *using the exact names shown in the GitHub UI* so they appear on every PR:
     - `✅ PR CI / Lint (ruff)`
     - `✅ PR CI / Smoke tests`
   - Optionally add additional owner-only workflows after verifying they succeed (for example, `📦 Browser Size / size-check`, `🔒 Container Security / sbom-scan-sign`, and `🚀 CI — Insight Demo / lint-type` + `🚀 CI — Insight Demo / tests`).
   - If the UI shows different names (for example, because a job label changed), copy the string verbatim from the latest workflow run; otherwise the protection rule will not attach and PRs will not block on CI.

2. **Badges stay green**
   - Confirm the badges in `README.md` show green shields for **PR CI**, **🚀 CI — Insight Demo**, and **🔥 Smoke Test**. If any badge is red, open the corresponding workflow run, fix the failure, and re-run the pipeline.

3. **Visibility on PRs**
   - Ensure "Allow GitHub Actions to create and approve pull requests" remains enabled so status checks and summaries appear inline on PRs.
   - Keep `pr-ci.yml` triggered on `pull_request` and `push` to `main` so checks always run on the latest commits.

4. **Local preflight**
   - Before opening a PR, run `pip install -r requirements.lock -r requirements-dev.lock` once, then execute `pytest -m smoke tests/test_af_requests.py tests/test_cache_version.py tests/test_check_env_core.py tests/test_check_env_network.py tests/test_config_settings.py tests/test_config_utils.py tests/test_ping_agent.py -q` to mirror the PR CI smoke job.
   - Run `pre-commit run --all-files` to catch formatting issues early; the PR CI job uses the same hooks.

Following these steps keeps CI results visible, enforces the gates on `main`, and helps non-technical reviewers trust that every change lands with a green signal.
