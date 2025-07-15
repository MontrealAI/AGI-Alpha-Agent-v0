[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# CI Workflow

The repository's main continuous integration pipeline lives in
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml). It runs only when the
repository owner triggers it from the GitHub Actions UI.

## Running the workflow

1. Navigate to **Actions → 🚀 CI**.
2. Choose the branch or tag in the drop‑down and click **Run workflow**.
3. Ensure you are the repository owner. The workflow starts with an
   `owner-check` job using the `ensure-owner` composite action. If the
   trigger user does not match `github.repository_owner` the pipeline exits
   immediately.

When invoked on a tagged commit the pipeline also builds and publishes a Docker
image to GHCR and uploads the prebuilt web client bundle to the corresponding
GitHub Release.

The deploy step tags the new container with both the release tag and `latest`.
If any command fails after pushing, the workflow rolls back by re-tagging the
previous `latest` image so production always points at a working build.

## Job overview

- **🧹 Ruff + 🏷️ Mypy** – lint and type checks.
- **✅ Pytest** – unit tests and front‑end checks.
- **Windows Smoke** – lightweight sanity tests on Windows.
- **📜 MkDocs** – basic documentation build.
- **📚 Docs Build** – full docs site verification.
- **🐳 Docker build** – builds and tests the demo image.
- **📦 Deploy** – pushes the image and release assets on tags.

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

After `npm ci` the workflow updates the Browserslist database with
`npx update-browserslist-db@latest --agree-to-terms` to silence the
"caniuse-lite is outdated" warning. Run the same command locally when
dependencies change so the CI logs stay clean.

If the workflow ever reports missing lock files, double‑check these paths
in `.github/workflows/ci.yml` and adjust them whenever new packages are added.

The docs and test jobs fetch the Pyodide runtime and GPT‑2 model files from
external mirrors. When these assets update upstream the checksum verification
fails. The workflow automatically reruns `scripts/update_pyodide.py` to refresh
the expected hashes and retries the download so CI keeps running even if the
mirrored files change.

Before submitting changes to the workflow run:

```bash
pre-commit run --files .github/workflows/ci.yml
```

This lints the YAML and pins action versions so the pipeline stays reproducible.

## Avoid skipped jobs

The workflow starts with a dedicated `owner-check` job that runs the
`ensure-owner` composite action. All other jobs declare `needs: owner-check`
so they wait for that verification instead of performing owner checks
themselves. Once prerequisites succeed the remaining jobs run in parallel. A failure in
linting or tests deliberately stops the Docker build and deploy stages. If a
job unexpectedly shows as skipped, first check whether one of its dependencies
failed earlier in the run. With the lock file paths fixed, all jobs should
execute when tests pass.
