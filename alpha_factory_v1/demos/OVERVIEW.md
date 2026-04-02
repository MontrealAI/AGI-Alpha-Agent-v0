[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Alpha‑Factory v1 👁️✨ — **Interactive Demo & Agent Gallery**
*Out‑learn | Out‑think | Out‑design | Out‑strategise | Out‑execute*

> “Intelligence is **experience** distilled through relentless self‑play.” — inspired by Sutton & Silver’s *Era of Experience* 

---


Browse the **visual demo gallery** on GitHub Pages:
<https://montrealai.github.io/AGI-Alpha-Agent-v0/gallery.html>
Run `./scripts/open_gallery.py` for a cross-platform launcher that opens the published gallery when online and falls back to the local build. Alternatively, `./scripts/open_gallery.sh` offers a Bash implementation.

Each demo package exposes its own ``__version__`` constant. These
numbers indicate the demo revision and are independent from the
main ``alpha_factory_v1`` package version.

## 🗺️ Navigator
| Section | Why read it? |
|---------|--------------|
|[1 • Welcome](#1-welcome) | Grand vision & quick launch |
|[2 • Demo Showcase 🎮](#2-demo-showcase-) | What each demo does & how to run it |
|[3 • Agent Roster 🖼️](#3-agent-roster-) | How every backend agent creates alpha |
|[4 • Deploy Cheat‑Sheet 🚀](#4-deploy-cheat-sheet-) | One‑liners for laptop ↔ cloud |
|[5 • Governance & Safety ⚖️](#5-governance--safety-) | Zero‑trust, audit trail, fail‑safes |
|[6 • Extending the Factory 🔌](#6-extending-the-factory-) | Plug‑in new demos & agents |
|[7 • Credits ❤️](#7-credits-) | Legends & support |

---

## 1 • Welcome
**Alpha‑Factory v1** is the **cross‑industry agentic engine** that captures live α‑signals and turns them into value across all industries & beyond. This gallery lets you *touch* that power.

### Quick Start 🚀
```bash
# One-command immersive tour (CPU‑only)
curl -sSL https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/main/alpha_factory_v1/demos/quick_start.sh | bash

# If cloned locally (run from repo root)
./alpha_factory_v1/quickstart.sh

# Cross‑platform Python launcher
python alpha_factory_v1/quickstart.py

# Or via Docker (no install)
docker run --pull=always -p 7860:7860 ghcr.io/montrealai/alpha-factory-demos:latest

# With Make
make demo-setup
make demo-run        # RUN_MODE=web for dashboard
```
Opens **http://localhost:7860** with a Gradio portal to every demo. Works on macOS, Linux, WSL 2 and Colab.

Advanced workflows like the OpenAI Agents bridge require the `openai-agents`
package and `OPENAI_API_KEY` set.
For air‑gapped installs see [docs/OFFLINE_SETUP.md](../../docs/OFFLINE_SETUP.md).

Running the entire test suite also installs heavier optional packages such as
`torch`. If those packages are missing, related tests are skipped. For a quick
smoke test execute:
```bash
pytest -m 'not e2e'
```

---

## 2 • Demo Showcase 🎮
| # | Folder | Emoji | Lightning Pitch | Alpha Contribution | Start Locally |
|---|--------|-------|-----------------|--------------------|---------------|
|1|`aiga_meta_evolution`|🧬|Agents *evolve* new agents; genetic tests auto‑score fitness.|Expands strategy space, surfacing fringe alpha.|`cd alpha_factory_v1/demos/aiga_meta_evolution && ./run_aiga_demo.sh`|
|2|`alpha_agi_business_v1`|🏦|Auto‑incorporates a digital‑first company end‑to‑end.|Shows AGI turning ideas → registered business.|`./alpha_factory_v1/demos/alpha_agi_business_v1/run_business_v1_demo.sh` (docs: `http://localhost:8000/docs`)|
|3|`alpha_agi_business_2_v1`|🏗️|Iterates business model with live market data RAG.|Continuous adaptation → durable competitive alpha.|`./alpha_factory_v1/demos/alpha_agi_business_2_v1/run_business_2_demo.sh`|
|4|`alpha_agi_business_3_v1`|📊|Financial forecasting & fundraising agent swarm.|Optimises capital stack for ROI alpha.|`./alpha_factory_v1/demos/alpha_agi_business_3_v1/run_business_3_demo.sh`|
|5|`alpha_agi_marketplace_v1`|🛒|Peer‑to‑peer agent marketplace simulating price discovery.|Validates micro‑alpha extraction via agent barter.|`python -m alpha_factory_v1.demos.alpha_agi_marketplace_v1.marketplace examples/sample_job.json`|
|6|`alpha_asi_world_model`|🌌|Scales MuZero‑style world‑model to an open‑ended grid‑world.|Stress‑tests anticipatory planning for ASI scenarios.|`./alpha_factory_v1/demos/alpha_asi_world_model/deploy_alpha_asi_world_model_demo.sh`|
|7|`cross_industry_alpha_factory`|🌐|Full pipeline: ingest → plan → act across 4 verticals.|Proof that one orchestrator handles multi‑domain alpha.|`./alpha_factory_v1/demos/cross_industry_alpha_factory/deploy_alpha_factory_cross_industry_demo.sh`|
|8|`era_of_experience`|🏛️|Streams of life events build autobiographical memory‑graph tutor.|Transforms tacit SME knowledge into tradable signals.|`docker compose -f alpha_factory_v1/demos/era_of_experience/docker-compose.experience.yml up`|
|9|`finance_alpha`|💹|Live momentum + risk‑parity bot on Binance test‑net.|Generates real P&L; stress‑tested against CVaR.|`./alpha_factory_v1/demos/finance_alpha/deploy_alpha_factory_demo.sh`|
|10|`macro_sentinel`|🌐|GPT‑RAG news scanner auto‑hedges with CTA futures.|Shields portfolios from macro shocks.|`docker compose -f alpha_factory_v1/demos/macro_sentinel/docker-compose.macro.yml up`|
|11|`muzero_planning`|♟|MuZero in 60 s; online world‑model with MCTS.|Distills planning research into a one‑command demo.|`./alpha_factory_v1/demos/muzero_planning/run_muzero_demo.sh`|
|12|`self_healing_repo`|🩹|Repo-Healer v1 runs bounded triage + targeted repair for this repo.|Maintains pipeline uptime alpha.|`docker compose -f alpha_factory_v1/demos/self_healing_repo/docker-compose.selfheal.yml up`|
|13|`meta_agentic_tree_search_v0`|🌳|Recursive agent rewrites via best‑first search.|Rapidly surfaces AGI-driven trading alpha.|`mats-bridge --episodes 3`|
|14|`alpha_agi_insight_v0`|👁️|Zero‑data search ranking AGI‑disrupted sectors.|Forecasts sectors primed for AGI transformation.|`python -m alpha_factory_v1.demos.alpha_agi_insight_v0 --verify-env`|

> **Colab?** Each folder ships an `*.ipynb` that mirrors the Docker flow with free GPUs.

---

## 3 • Agent Roster 🖼️
Each backend agent is callable as an **OpenAI Agents SDK** tool *and* as a REST endpoint (`/v1/agents/<name>`). 

| # | File | Emoji | Core Alpha Skill | Key Env |
|---|------|-------|------------------|--------|
|1|`finance_agent.py`|💰|Multi‑factor α, CVaR guard, RL execution bridge.|`ALPHA_UNIVERSE`|
|2|`biotech_agent.py`|🧬|UniProt / PubMed KG‑RAG, CRISPR off‑target.|`BIOTECH_KG_FILE`|
|3|`manufacturing_agent.py`|⚙️|OR‑Tools CP‑SAT optimiser, CO₂ predictor.|`ALPHA_MAX_SCHED_SECONDS`|
|4|`policy_agent.py`|📜|Statute QA, ISO‑37301 risk tagging.|`STATUTE_CORPUS_DIR`|
|5|`energy_agent.py`|🔋|Demand‑response bidding, price elasticity.|`ENERGY_API_TOKEN`|
|6|`supply_chain_agent.py`|📦|VRP solver & ETA forecaster.|`SC_DB_DSN`|
|7|`climate_risk_agent.py`|🌦️|Climate VaR & scenario stress.|`NOAA_TOKEN`|
|8|`cyber_threat_agent.py`|🛡️|CVE triage, MITRE ATT&CK graph.|`VIRUSTOTAL_KEY`|
|9|`drug_design_agent.py`|💊|Generative scaffold hopping, ADMET filter.|`CHEMBL_KEY`|
|10|`retail_demand_agent.py`|🛍️|LSTM demand forecast + promo uplift.|`POS_DB_DSN`|
|11|`smart_contract_agent.py`|📜⛓️|Formal‑verifies Solidity, auto‑patches re‑entrancy.|`ETH_RPC_URL`|
|12|`talent_match_agent.py`|🤝|Vector‑match CV ↔ project gigs.|`ATS_DB_DSN`|

**Playbooks** live in `/examples/<agent_name>.ipynb` — copy‑paste ready.

---

## 4 • Deploy Cheat‑Sheet 🚀
| Platform | One‑liner | Notes |
|----------|-----------|-------|
|Docker Compose|`docker compose up -d orchestrator`|Spins Kafka, Prometheus, Grafana, agents, demos.|
|Kubernetes|`helm repo add alpha-factory https://montrealai.github.io/helm && helm install af alpha-factory/full`|mTLS via SPIFFE, HPA auto‑scales.|
|Colab|Launch notebook ⇒ click *“Run on Colab”* badge.|GPU‑accelerated demos.|
|Bare‑metal Edge|`python edge_runner.py --agents manufacturing,energy`|Zero external deps; SQLite state. The helper script is included in the repo.|

---

## 5 • Governance & Safety ⚖️
* **Model Context Protocol** envelopes every artefact (SHA‑256 + ISO‑8601). 
* **SPIFFE + mTLS** across the mesh → zero‑trust. 
* **Cosign + Rekor** immutable supply chain. 
* Live bias & harm evals via model‑graded tests each night.

---

## 6 • Extending the Factory 🔌
```toml
[project.entry-points."alpha_factory.demos"]
my_demo = my_pkg.cool_demo:app
```
1. Ship a Gradio or Streamlit `app` returning a FastAPI router. 
2. Add Helm annotation `af.maturity=beta` → appears in UI. 
3. Submit PR — CI auto‑runs red‑team prompts.

---

## 7 • Credits ❤️
*Jeff Clune* for **AI‑GA** inspiration; *Sutton & Silver* for the *Era of Experience* pillars; *Schrittwieser et al.* for **MuZero** foundations.

Special salute to **[Vincent Boucher](https://www.linkedin.com/in/montrealai/)** — architect of the 2017 [Multi‑Agent AI DAO](https://www.quebecartificialintelligence.com/priorart) and steward of the **$AGIALPHA** utility token powering this venture.

---

© 2025 MONTREAL.AI — Apache‑2.0 License

