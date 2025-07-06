[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Demo Gallery

The following table summarises each available demo. Click the folder name to view the README and follow the start command to launch locally.

| # | Folder | Emoji | Lightning Pitch | Alpha Contribution | Start Locally |
|---|--------|-------|-----------------|--------------------|---------------|
|1|[`aiga_meta_evolution`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/aiga_meta_evolution)|🧬|Agents *evolve* new agents; genetic tests auto‑score fitness.|Expands strategy space, surfacing fringe alpha.|`cd alpha_factory_v1/demos/aiga_meta_evolution && ./run_aiga_demo.sh`|
|2|[`alpha_agi_business_v1`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_agi_business_v1)|🏦|Auto‑incorporates a digital‑first company end‑to‑end.|Shows AGI turning ideas → registered business.|`./alpha_factory_v1/demos/alpha_agi_business_v1/run_business_v1_demo.sh` (docs: `http://localhost:8000/docs`)|
|3|[`alpha_agi_business_2_v1`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_agi_business_2_v1)|🏗️|Iterates business model with live market data RAG.|Continuous adaptation → durable competitive alpha.|`./alpha_factory_v1/demos/alpha_agi_business_2_v1/run_business_2_demo.sh`|
|4|[`alpha_agi_business_3_v1`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_agi_business_3_v1)|📊|Financial forecasting & fundraising agent swarm.|Optimises capital stack for ROI alpha.|`./alpha_factory_v1/demos/alpha_agi_business_3_v1/run_business_3_demo.sh`|
|5|[`alpha_agi_marketplace_v1`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_agi_marketplace_v1)|🛒|Peer‑to‑peer agent marketplace simulating price discovery.|Validates micro‑alpha extraction via agent barter.|`python -m alpha_factory_v1.demos.alpha_agi_marketplace_v1.marketplace examples/sample_job.json`|
|6|[`alpha_asi_world_model`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_asi_world_model)|🌌|Scales MuZero‑style world‑model to an open‑ended grid‑world.|Stress‑tests anticipatory planning for ASI scenarios.|`./alpha_factory_v1/demos/alpha_asi_world_model/deploy_alpha_asi_world_model_demo.sh`|
|7|[`cross_industry_alpha_factory`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/cross_industry_alpha_factory)|🌐|Full pipeline: ingest → plan → act across 4 verticals.|Proof that one orchestrator handles multi‑domain alpha.|`./alpha_factory_v1/demos/cross_industry_alpha_factory/deploy_alpha_factory_cross_industry_demo.sh`|
|8|[`era_of_experience`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/era_of_experience)|🏛️|Streams of life events build autobiographical memory‑graph tutor.|Transforms tacit SME knowledge into tradable signals.|`docker compose -f alpha_factory_v1/demos/era_of_experience/docker-compose.experience.yml up`|
|9|[`finance_alpha`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/finance_alpha)|💹|Live momentum + risk‑parity bot on Binance test‑net.|Generates real P&L; stress‑tested against CVaR.|`./alpha_factory_v1/demos/finance_alpha/deploy_alpha_factory_demo.sh`|
|10|[`macro_sentinel`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/macro_sentinel)|🌐|GPT‑RAG news scanner auto‑hedges with CTA futures.|Shields portfolios from macro shocks.|`docker compose -f alpha_factory_v1/demos/macro_sentinel/docker-compose.macro.yml up`|
|11|[`muzero_planning`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/muzero_planning)|♟|MuZero in 60 s; online world‑model with MCTS.|Distills planning research into a one‑command demo.|`./alpha_factory_v1/demos/muzero_planning/run_muzero_demo.sh`|
|12|[`self_healing_repo`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/self_healing_repo)|🩹|CI fails → agent crafts patch ⇒ PR green again.|Maintains pipeline uptime alpha.|`docker compose -f alpha_factory_v1/demos/self_healing_repo/docker-compose.selfheal.yml up`|
|13|[`meta_agentic_tree_search_v0`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/meta_agentic_tree_search_v0)|🌳|Recursive agent rewrites via best‑first search.|Rapidly surfaces AGI-driven trading alpha.|`mats-bridge --episodes 3`|
|14|[`alpha_agi_insight_v0`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_agi_insight_v0)|👁️|Zero‑data search ranking AGI‑disrupted sectors.|Forecasts sectors primed for AGI transformation.|`python -m alpha_factory_v1.demos.alpha_agi_insight_v0 --verify-env`|

Each folder also contains a Colab notebook mirroring the Docker workflow for GPU access.

## Quick Launch

Run `./alpha_factory_v1/quickstart.sh` from the repository root to experience every demo through a unified Gradio interface.

## Updating Demo Assets

When adding new demos or modifying images, regenerate
`docs/assets/service-worker.js` so GitHub Pages serves the latest files:

```bash
python scripts/build_service_worker.py
```

The helper script `build_gallery_site.sh` automates this step, but rerun it
whenever assets change to avoid stale caches. If the Insight browser asset
checksums change, also execute `python scripts/generate_build_manifest.py` to
update `build_assets.json`.
