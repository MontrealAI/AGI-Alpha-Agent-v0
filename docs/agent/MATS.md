[Project notice](../DISCLAIMER_SNIPPET.md)

# MATS Search Lab — operating guide

Use [the browser lab](https://montrealai.github.io/AGI-Alpha-Agent-v0/meta_agentic_tree_search_v0/)
to compare competing workflow designs without accounts, API keys or uploads. Everything runs locally
in your browser. The cases contain synthetic assumptions, not customer or personal data.

## Start and inspect

Choose a planning case and run the search. Move the iteration slider to inspect selection, expansion,
rollout and backpropagation. Expand the node inspector for precise statistics, and the held-out workload
inspector for dependency-aware resource schedules. Results remain visibly stale and exports are disabled
when controls or JSON change, until the revised model runs successfully.

The top row reports held-out utility gain, unique designs evaluated and the gap to an exhaustive training
oracle. The oracle consumes extra compute, is optional and never selects the candidate. Five review gates
check gain, escaped defects, delivery time, resource cost and reviewer effort. A passing candidate remains
unapproved; the active baseline is unchanged.

## Run locally

From an extracted complete release or repository root, with Python 3.11–3.13:

```bash
python -m alpha_factory_v1.demos.meta_agentic_tree_search_v0 --list
python -m alpha_factory_v1.demos.meta_agentic_tree_search_v0 --case release-design --output search-runs
python -m alpha_factory_v1.demos.meta_agentic_tree_search_v0 --serve
```

Open `http://127.0.0.1:7862/meta_agentic_tree_search_v0/`. Use `--port 7863` if occupied; Ctrl+C stops the
server. The packaged server binds only to loopback and serves an explicit static asset set. It provides
no execution, upload, credential or filesystem-browsing API. The installed console command is `mats-lab`.

## Save, import and verify

Save settings only when you want them retained on this device. Restore is explicit. Clear saved settings
removes only this lab's settings. Download a six-file review bundle for reproducible evidence independent
of browser storage. Import accepts a scenario or full run up to 1 MB; every full run is recomputed.

```bash
python -m alpha_factory_v1.demos.meta_agentic_tree_search_v0 --input my-scenario.json --output search-runs
python -m alpha_factory_v1.demos.meta_agentic_tree_search_v0 --verify search-runs/<run-sha256>/run.json
```

Use the real directory printed by the CLI. If an existing output is incomplete, modified or symlinked,
choose a new output directory. The CLI never silently overwrites evidence. A checksum is not a signature
or validator approval. The $AGIALPHA review job is a draft and is not submitted, funded or settled here.

## Troubleshooting

| Symptom | Action |
|---|---|
| Controls changed but old results remain | Run search; exports remain disabled until recomputation finishes. |
| Edited JSON cannot be exported | Apply the model; fix the visible validation error if rejected. |
| Import rejected despite a matching hash | Use an original export; verification recomputes every result. |
| A candidate fails a gate | Keep the baseline. Inspect the objective and assumptions; do not tune on held-out results. |
| Oracle gap is positive | The finite search missed the training optimum. Compare budget and depth, using fresh evaluation later. |
| Browser cannot cache offline | Keep an evidence bundle or use the packaged local server. |
| The local port is occupied | Choose another loopback port with `--port`. |
| Optional legacy provider fails | Use `--rewriter random`; live model access is separately configured and tested. |

See the [complete method and preserved research](../demos/meta_agentic_tree_search_v0.md)
for the exact simulator, bounded UCT arithmetic, tie rules, limits and original materials.
