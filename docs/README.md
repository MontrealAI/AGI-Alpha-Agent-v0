[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Project Documentation


## Building the React Dashboard

The React dashboard sources live under `alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client`. Build the static assets before serving the API:

```bash
pnpm --dir alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client install
pnpm --dir alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client run build
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

## Static Insight Demo

GitHub Pages serves any files under `docs/` when the site is built from
`mkdocs.yml`. To publish the static α‑AGI Insight demo, copy the contents of
`static_insight/` into this directory and run `mkdocs build` if your workflow
doesn't trigger it automatically. Pushing the updated files makes the demo
available at the default Pages URL.
