[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Project Documentation

[α‑AGI Insight Demo](alpha_agi_insight_v1/index.html)

[Deployment Quickstart](DEPLOYMENT_QUICKSTART.md)

- [Browser Quickstart](insight_browser_quickstart.pdf) – run `./scripts/deploy_insight_full.sh` for a verified one-command deployment
- **One‑Command Deployment** – execute `./scripts/insight_sprint.sh` to build, verify and publish the GitHub Pages site automatically.
- **Local Gallery Build** – run `./scripts/build_gallery_site.sh` to compile the full demo gallery under `site/` for offline review.
- **Build & Open Gallery** – run `./scripts/build_open_gallery.sh` to regenerate the docs and open the gallery automatically.
- **Preview Gallery Locally** – run `./scripts/preview_gallery.sh` to build the full gallery and serve it on <http://localhost:8000/>.
- **Open Gallery (Python)** – run `./scripts/open_gallery.py` for a cross-platform way to launch the published gallery, falling back to the local build when offline.
- **Open Gallery (Shell)** – run `./scripts/open_gallery.sh` to open the gallery in your browser. It automatically builds a fresh local copy when the remote site isn't available.
- **Open Individual Demo** – run `./scripts/open_demo.sh <demo_dir>` to open a single page from the gallery.
- **Open Subdirectory Gallery** – run `./scripts/open_subdir_gallery.py` to launch the mirror under `alpha_factory_v1/demos/`.
- **Open Subdirectory Demo** – run `./scripts/open_subdir_demo.py <demo_dir>` to open a single page from that mirror.
- **Offline Tests** – build a wheelhouse with `scripts/build_offline_wheels.sh` then run `python check_env.py --auto-install --wheelhouse <dir>` and `pytest` without network access.

## Building the React Dashboard

The React dashboard sources live under `alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client`. Build the static assets before serving the API:

```bash
npm ci --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client
npm --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client run build
```

The compiled files appear in `alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client/dist` and are automatically served when running `uvicorn alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.api_server:app` with `RUN_MODE=web`.

## Ablation Runner

Use `alpha_factory_v1/core/tools/ablation_runner.py` to measure how disabling individual innovations affects benchmark performance. The script applies each patch from `benchmarks/patch_library/`, runs the benchmarks with and without each feature and generates `docs/ablation_heatmap.svg`.

```bash
python -m alpha_factory_v1.core.tools.ablation_runner
```

The resulting heatmap visualises the pass rate drop when a component is disabled.

## Manual Workflows

The repository defines several optional GitHub Actions that are disabled by
default. They only run when the repository owner starts them from the GitHub
UI. These workflows perform heavyweight benchmarking and stress testing.

To launch a job:

1. Open the **Actions** tab on GitHub.
2. Choose either **📈 Replay Bench**, **🌩 Load Test** or **📊 Transfer Matrix**.
3. Click **Run workflow** and confirm.

Each workflow checks that the person triggering it matches
`github.repository_owner`, so it executes only when the owner initiates the
run.

## Macro-Sentinel Demo

A self-healing macro risk radar powered by multi-agent α‑AGI. The stack ingests
macro telemetry, runs Monte-Carlo simulations and exposes a Gradio dashboard.
See the [alpha_factory_v1/demos/macro_sentinel/README.md](../alpha_factory_v1/demos/macro_sentinel/README.md)
for full instructions.

## α‑AGI Insight v1 Demo

`docs/alpha_agi_insight_v1` provides a self-contained HTML demo that
visualises capability forecasts with Plotly. The GitHub Actions workflow
copies this directory into the generated `site/` folder, serves it on GitHub
Pages and deploys the page automatically. Visit
[the published demo](https://montrealai.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/)
to preview it.

The old `static_insight` directory has been removed in favour of this
official static demo.

To update the charts, edit `forecast.json` and `population.json` and rebuild
the site:

```bash
./scripts/edge_human_knowledge_pages_sprint.sh
```

This helper fetches all assets, compiles the browser bundle and runs `mkdocs build`.
Open `site/alpha_agi_insight_v1/index.html` in your browser to verify the
changes before committing. Alternatively run `./scripts/preview_insight_docs.sh`
to build and serve the demo locally on `http://localhost:8000/`.
