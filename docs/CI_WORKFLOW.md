[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# CI Workflow

The repository's main continuous integration pipeline lives in
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml). It runs only when the
repository owner triggers it from the GitHub Actions UI.

## Running the workflow

1. Navigate to **Actions → 🚀 CI**.
2. Choose the branch or tag in the drop‑down and click **Run workflow**.
3. Ensure you are the repository owner; non‑owners exit immediately after the
   initial *owner-check* job.

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
 the repository root. Each `setup-node` step, including the test matrix,
 lists these paths explicitly via
`cache-dependency-path`:

```
alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/package-lock.json
alpha_factory_v1/core/interface/web_client/package-lock.json
```

If the workflow ever reports missing lock files, double‑check these paths
in `.github/workflows/ci.yml` and adjust them whenever new packages are added.
