[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# CI Workflow

The repository's main continuous integration pipeline lives in the
[CI workflow file](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/.github/workflows/ci.yml).
It runs automatically on pushes and pull requests targeting `main`, and
now also triggers on release tags (`v*` or `release-*`) so the
publish/signing path stays green. Manual dispatch through **Run
workflow** remains available for the repository owner when a fresh signal
is needed outside normal events.

## Running the workflow

The pipeline fires automatically; manual dispatch is needed only to rebuild a
badge or force a re-run outside the normal hooks.

1. Navigate to **Actions → 🚀 CI — Insight Demo** and click **Run workflow**.
2. Choose the branch or tag. Use a signed tag (for example `v0.1.0`) to test
   the deploy path; the updated trigger now responds to tags so the release
   job runs.
3. Manual dispatch is restricted to the repository owner via the
   **owner-check** composite action. On push and pull_request events the job
   simply records the repository owner and allows all downstream jobs to run,
   so contributors still see the full matrix on PRs.
4. Confirm **Python&nbsp;3.11–3.13** and **Node.js&nbsp;22.17.1** are installed locally
   if you reproduce the pipeline.
5. Run `pre-commit run --all-files` so the hooks pass before pushing. The
   workflow lints only changed files when triggered by a push or pull request.
6. Ensure the `package-lock.json` files listed in `NODE_LOCKFILES` are up to
   date by running `npm ci` in each web client directory. Commit any changes
   before dispatching the workflow so dependency caching works correctly.

## Branch protection and required checks

Keep the PR gates strict so every contributor and automation path sees the same
CI surface:

- In **Settings → Branches → Branch protection rules**, add `main` and enable
  **Require status checks to pass before merging** with these required checks:
  - `PR CI / Lint (ruff)`
  - `PR CI / Smoke tests`
  - `🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.11)`
  - `🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.12)`
  - `🚀 CI — Insight Demo / ✅ Pytest (3.11)`
  - `🚀 CI — Insight Demo / ✅ Pytest (3.12)`
  - `🚀 CI — Insight Demo / Windows Smoke`
  - `🚀 CI — Insight Demo / macOS Smoke`
  - `🚀 CI — Insight Demo / 📜 MkDocs`
  - `🚀 CI — Insight Demo / 📚 Docs Build`
  - `🚀 CI — Insight Demo / 🐳 Docker build`
- Keep **Require branches to be up to date before merging** switched on so
  merges always include the latest CI results.
- For owners, trigger **🚀 CI — Insight Demo** after large changes to validate
  the full matrix and Docker build; the badge in the README keeps its status
  visible.
- If any new workflow or job name changes, update this list and the README
  badges so the enforced checks stay accurate and visible.

When invoked on a tagged commit the pipeline also builds and publishes a Docker
image to GHCR and uploads the prebuilt web client bundle to the corresponding
GitHub Release.

The deploy step tags the new container with both the release tag and `latest`.
If any command fails after pushing, the workflow rolls back by re-tagging the
previous `latest` image so production always points at a working build.

## Job overview

- **🧹 Ruff + 🏷️ Mypy** – lint and type checks.
- **✅ Pytest** – unit tests and front‑end checks.
- **🎯 Cypress (removed)** – the workflow no longer executes Cypress tests. End‑to‑end checks run via Playwright inside the **✅ Pytest** job.
- **Windows/Mac Smoke** – lightweight sanity tests on Windows and macOS.
- *Python matrix* – main jobs test against **Python 3.11** and **3.12** while
  the Windows and macOS smoke jobs use **Python 3.12** to match upstream
  PyTorch wheel availability.
- **📜 MkDocs** – basic documentation build.
- **📚 Docs Build** – full docs site verification with an offline check. The job runs
  `scripts/build_gallery_site.sh` which executes `preflight.py`. This
  script requires `/usr/bin/patch` inside the sandbox container, so the
  workflow builds `sandbox.Dockerfile` and sets `SANDBOX_IMAGE=selfheal-sandbox:latest`.
  Ensure this image exists locally before building the docs.
  Heavy demo assets can inflate the cache size. The MkDocs config
  now lists these directories under `exclude:` to keep builds light:
  `docs/alpha_agi_insight_v1/assets`, `docs/meta_agentic_agi*/assets`.
- **🐳 Docker build** – builds and tests the demo image.
- **📦 Deploy** – pushes the image and release assets on tags.
- **♿ Accessibility audit** – runs `@axe-core/cli --stdout` on the built web client
  and calculates a score via `scripts/axe_score.py`. The pipeline fails if the
  score is below the `a11y-threshold` input (default 95).
  Keep this threshold at least 95 to maintain baseline accessibility. The
  workflow now ensures a Chrome binary and Chromedriver are available (preferring
  `google-chrome-stable`, falling back to `chromium-browser` via apt) and passes
  their locations to Axe so the audit consistently succeeds on fresh runners.

Caching for Python and Node dependencies is enabled. The project stores
`package-lock.json` files under the demo and web client folders rather than at
 the repository root. The workflow defines these paths once in the
`NODE_LOCKFILES` environment variable so each `setup-node` step
passes the same list via `cache-dependency-path`:

```
alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/package-lock.json
alpha_factory_v1/core/interface/web_client/package-lock.json
alpha_factory_v1/core/interface/web_client/staking/package-lock.json
alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client/package-lock.json
```
Each job installs Node.js 22.17.1 based on `.nvmrc` using `actions/setup-node` before
running `npm` commands. This ensures hooks like `eslint-insight-browser` and
documentation steps use the expected runtime.

After `npm ci` the workflow updates the Browserslist database with
`npx update-browserslist-db --update-db --yes` to silence the
"caniuse-lite is outdated" warning. Run the same command locally when
dependencies change. Bump the version in `.github/workflows/ci.yml` and this
documentation whenever a newer release is required so CI stays reproducible.

If the workflow ever reports missing lock files, double‑check these paths
in `.github/workflows/ci.yml` and adjust them whenever new packages are added.

The docs and test jobs fetch the Pyodide runtime and GPT‑2 model files from
external mirrors. **Install the Python dependencies from `requirements.txt`
before running `scripts/fetch_assets.py`; the helper uses the `requests`
library to download these assets.** When the files change upstream the checksum
verification fails. Each verify step now runs in a `||` block:

```bash
python scripts/fetch_assets.py --verify-only || (
  python scripts/update_pyodide.py 0.28.0 &&
  npm --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1 run fetch-assets &&
  python scripts/fetch_assets.py --verify-only
)
```

If verification fails the assets refresh automatically and the check is
repeated. `scripts/update_pyodide.py` downloads the requested Pyodide
runtime, computes new SHA‑384 digests for `pyodide.js` and
`pyodide.asm.wasm`, and rewrites the checksum table in `scripts/fetch_assets.py`.
The workflow then re-fetches the files using the updated values. To avoid
re-downloading these large assets for every job, the workflow computes a cache
key from the current checksums and restores any matching archive across jobs and
operating systems. This ensures reproducible builds and invalidates old caches
whenever the upstream hashes change.

Before submitting changes to the workflow run:

```bash
pre-commit run --files .github/workflows/ci.yml
```

This lints the YAML and pins action versions so the pipeline stays reproducible.

When adding local composite actions like `.github/actions/ensure-owner`, ensure
`actions/checkout` executes first. GitHub skips checkout on manual dispatch
without this step and later jobs fail with "Can't find 'action.yml'" errors.

The workflow uploads benchmark and coverage artifacts only when the files exist. This avoids noisy "file not found" warnings on failed runs.

## Avoid skipped jobs

The workflow starts with an `owner-check` job that runs an inline Bash step to
confirm the workflow was dispatched by the repository owner. The script exits
with an error if `github.actor` differs from `github.repository_owner` and
exports a `repo_owner_lower` output. All remaining jobs list `owner-check` under
`needs`, so they execute only after the ownership check passes. If a job appears
skipped, inspect its dependencies for earlier failures. With the lock file paths
fixed, all jobs run whenever the owner dispatches the workflow and the tests
succeed.

## Local CI steps

Run these commands before dispatching the workflow:

```bash
python scripts/check_python_deps.py
python check_env.py --auto-install
pre-commit run --all-files
pytest --cov --cov-report=xml
```
The CI workflow lints only files changed between `$GITHUB_EVENT_BEFORE` and
`$GITHUB_SHA` when triggered by a push or pull request. Manual or scheduled
runs fall back to a full `pre-commit run --all-files`.
