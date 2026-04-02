[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.


# Alpha‑Factory v1 👁️✨ — Multi‑Agent **AGENTIC** α‑AGI

**Out‑learn · Out‑think · Out‑design · Out‑strategise · Out‑execute**

---

> **Mission 🎯**  Identify 🔍 → Learn 📚 → Think 🧠 → Design 🎨 → Strategise ♟️ → Execute ⚡ — compounding real‑world **α** across *all* industries.

Global markets seep *USD ✧ trillions/yr* in latent opportunity — “alpha” in the broadest sense:  
<kbd>pricing dislocations • supply‑chain entropy • novel drug targets • policy loopholes • undiscovered materials</kbd>.

**Alpha‑Factory v1** is an antifragile constellation of self‑improving Agentic α‑AGI Agents 👁️✨ orchestrated to **spot live alpha across any industry and transmute it into compounding value**.

**Definition**: An **α‑AGI Business** 👁️✨ is an on‑chain autonomous enterprise (`<name>.alpha.agi.eth`) that unleashes a swarm of self‑improving agentic **α‑AGI agents** 👁️✨ (`<name>.alpha.agent.agi.eth`) to hunt down inefficiencies across any domain and transmute them into **$AGIALPHA**.

Built atop **OpenAI Agents SDK**, **Google ADK**, **A2A protocol**, and Anthropic’s **Model Context Protocol**, the stack runs cloud‑native *or* air‑gapped, hot‑swapping between frontier LLMs and distilled local models.

## Disclaimer
This repository is a conceptual research prototype. References to "AGI" and
"superintelligence" describe aspirational goals and do not indicate the presence
of a real general intelligence. Use at your own risk.

---

## 📜 Table of Contents
0. [Design Philosophy](#0-design-philosophy)  
1. [System Topology 🗺️](#1-system-topology)  
2. [World‑Model & Planner 🌌](#2-world-model--planner)  
3. [Agent Gallery 🖼️ (12 agents)](#3-agent-gallery)  
4. [Demo Showcase 🎬 (12 demos)](#4-demo-showcase)  
5. [Memory & Knowledge Fabric 🧠](#5-memory--knowledge-fabric)  
6. [5‑Minute Quick‑Start 🚀](#6-5-minute-quick-start)  
7. [Deployment Recipes 🍳](#7-deployment-recipes)  
8. [Governance & Compliance ⚖️](#8-governance--compliance)  
9. [Observability 🔭](#9-observability)  
10. [Extending the Mesh 🔌](#10-extending-the-mesh)  
11. [Troubleshooting 🛠️](#11-troubleshooting)  
12. [Roadmap 🛣️](#12-roadmap)  
13. [Credits 🌟](#13-credits)  

---

<a name="0-design-philosophy"></a>
## 0 · Design Philosophy

> “We have shifted from *big‑data hoarding* to **big‑experience compounding**.” — *Era of Experience*.

* **Experience‑First Loop** — Sense → *Imagine* (MuZero‑style latent planning) → Act → Adapt.  
* **AI‑GA Autogenesis** — The factory meta‑evolves new agents and curricula inspired by Clune’s *AI‑Generating Algorithms*.  
* **Graceful Degradation** — GPU‑less? No cloud key? Agents fall back to distilled local models & heuristics.  
* **Zero‑Trust Core** — SPIFFE identities, signed artefacts, guard‑rails, exhaustive audit logs.  
* **Polyglot Value** — Everything is normalised to a common *alpha Δ∑USD* lens.

---

<a name="1-system-topology"></a>
## 1 · System Topology 🗺️
```mermaid
flowchart LR
  ORC([🛠️ Orchestrator])
  WM[(🌌 World‑Model)]
  MEM[(🔗 Vector‑Graph Memory)]
  subgraph Agents
    FIN(💰)
    BIO(🧬)
    MFG(⚙️)
    POL(📜)
    ENE(🔋)
    SUP(📦)
    RET(🛍️)
    CYB(🛡️)
    CLM(🌎)
    DRG(💊)
    SCT(⛓️)
    TAL(🧑‍💻)
  end
  ORC -- A2A --> Agents
  Agents -- experience --> WM
  WM -- embeddings --> MEM
  ORC -- Kafka --> DL[(🗄️ Data Lake)]
```

* **Orchestrator** auto‑discovers agents (see `backend/agents/__init__.py`) and exposes a unified REST + gRPC facade.  
* **World‑Model** uses MuZero‑style latent dynamics for counterfactual planning.  
* **Memory Fabric** = pgvector + Neo4j for dense & causal recall.

---

<a name="2-world-model--planner"></a>
## 2 · World‑Model & Planner 🌌

| Component | Source Tech | Role |
|-----------|-------------|------|
| **Latent Dynamics** | MuZero++ | Predict env transitions & value |
| **Self‑Play Curriculum** | POET‑XL | Generates alpha‑labyrinth tasks |
| **Meta‑Gradient** | AI‑GA | Evolves optimiser hyper‑nets |
| **Task Selector** | Multi‑Armed Bandit | Schedules agent ↔ world‑model interactions |

---

<a name="3-agent-gallery"></a>
## 3 · Agent Gallery 🖼️

```mermaid
flowchart TD
    ORC["🛠️ Orchestrator"]
    GEN{{"🧪 Env‑Generator"}}
    LRN["🧠 MuZero++"]

    subgraph Agents
        FIN["💰"]
        BIO["🧬"]
        MFG["⚙️"]
        POL["📜"]
        ENE["🔋"]
        SUP["📦"]
        RET["🛍️"]
        MKT["📈"]
        CYB["🛡️"]
        CLM["🌎"]
        DRG["💊"]
        SMT["⛓️"]
    end

    %% message flows
    GEN -- tasks --> LRN
    LRN -- policies --> Agents
    Agents -- skills --> LRN

    ORC -- A2A --> FIN
    ORC -- A2A --> BIO
    ORC -- A2A --> MFG
    ORC -- A2A --> POL
    ORC -- A2A --> ENE
    ORC -- A2A --> SUP
    ORC -- A2A --> RET
    ORC -- A2A --> MKT
    ORC -- A2A --> CYB
    ORC -- A2A --> CLM
    ORC -- A2A --> DRG
    ORC -- A2A --> SMT
    ORC -- A2A --> GEN
    ORC -- A2A --> LRN

    ORC -- Kafka --> DATALAKE["🗄️ Data Lake"]
    FIN -.->|Prometheus| GRAFANA{{"📊"}}
```

| # | Agent | Path | Prime Directive | Status | Key Env Vars |
|---|-------|------|-----------------|--------|--------------|
| 1 | **Finance** 💰 | `finance_agent.py` | Multi‑factor alpha & RL execution | **Prod** | `BROKER_DSN` |
| 2 | **Biotech** 🧬 | `biotech_agent.py` | CRISPR & assay proposals | **Prod** | `OPENAI_API_KEY` |
| 3 | **Manufacturing** ⚙️ | `manufacturing_agent.py` | CP‑SAT optimiser | **Prod** | `SCHED_HORIZON` |
| 4 | **Policy** 📜 | `policy_agent.py` | Statute QA & diffs | **Prod** | `STATUTE_CORPUS_DIR` |
| 5 | **Energy** 🔋 | `energy_agent.py` | Spot‑vs‑forward arbitrage | **Beta** | `ISO_TOKEN` |
| 6 | **Supply‑Chain** 📦 | `supply_chain_agent.py` | Stochastic MILP routing | **Beta** | `SC_DB_DSN` |
| 7 | **Retail Demand** 🛍️ | `retail_demand_agent.py` | SKU forecast & pricing | **Beta** | `POS_DB_DSN` |
| 8 | **Cyber‑Sec** 🛡️ | `cyber_threat_agent.py` | Predict & patch CVEs | **Beta** | `VT_API_KEY` |
| 9 | **Climate Risk** 🌎 | `climate_risk_agent.py` | ESG stress tests | **Beta** | `NOAA_TOKEN` |
|10 | **Drug‑Design** 💊 | `drug_design_agent.py` | Diffusion + docking | **Incub** | `CHEMBL_KEY` |
|11 | **Smart‑Contract** ⛓️ | `smart_contract_agent.py` | Formal verification | **Incub** | `ETH_RPC_URL` |
|12 | **Talent‑Match** 🧑‍💻 | `talent_match_agent.py` | Auto‑bounty hiring | **Incub** | — |

```mermaid
%% Legend
%%  solid arrows  = primary value‑flow
%%  dashed arrows = secondary / supporting influence
%%  node emojis   = domain archetypes

graph TD
    %% Core pillars
    FIN["💰 Finance"]
    BIO["🧬 Biotech"]
    MFG["⚙️ Manufacturing"]
    POL["📜 Policy / Reg‑Tech"]
    ENE["🔋 Energy"]
    SUP["📦 Supply‑Chain"]
    RET["🛍️ Retail / Demand"]
    CYB["🛡️ Cyber‑Security"]
    CLM["🌎 Climate"]
    DRG["💊 Drug Design"]
    SMT["⛓️ Smart Contracts"]
    TLT["🧑‍💼 Talent"]

    %% Derived transversal competences
    QNT["📊 Quant R&D"]
    RES["🔬 Research Ops"]
    DSG["🎨 Design"]
    OPS["🔧 DevOps"]

    %% Primary value‑creation arcs
    FIN -->|Price discovery| QNT
    FIN -->|Risk stress‑test| CLM
    BIO --> DRG
    BIO --> RES
    MFG --> SUP
    ENE --> CLM
    RET --> FIN
    POL --> CYB
    SMT --> FIN

    %% Cross‑pollination (secondary, dashed)
    FIN -.-> POL
    SUP -.-> CLM
    CYB -.-> OPS
    DRG -.-> POL
    QNT -.-> RES
    RET -.-> DSG

    %% Visual grouping
    subgraph Core
        FIN
        BIO
        MFG
        POL
        ENE
        SUP
        RET
        CYB
        CLM
        DRG
        SMT
        TLT
    end
    classDef core fill:#0d9488,color:#ffffff,stroke-width:0px;
```

Each agent exports a signed *proof‑of‑alpha* message to the Kafka bus, enabling cross‑breeding of opportunities.

```mermaid
sequenceDiagram
    participant User
    participant ORC as Orchestrator
    participant FIN as 💰
    participant GEN as 🧪
    User->>ORC: /alpha/run
    ORC->>GEN: new_world()
    GEN-->>ORC: env_json
    ORC->>FIN: act(env)
    FIN-->>ORC: proof(ΔG)
    ORC-->>User: artefact + KPI
```

---

<a name="4-demo-showcase"></a>
## 4 · Demo Showcase 🎬

| # | Folder | Emoji | Lightning Pitch | Alpha Contribution | Start Locally |
|---|--------|-------|-----------------|--------------------|---------------|
|1|`aiga_meta_evolution`|🧬|Agents *evolve* new agents; genetic tests auto‑score fitness.|Expands strategy space, surfacing fringe alpha.|`cd alpha_factory_v1/demos/aiga_meta_evolution && ./run_aiga_demo.sh`|
|2|`alpha_agi_business_v1`|🏦|Auto‑incorporates a digital‑first company end‑to‑end.|Shows AGI turning ideas → registered business.|`./alpha_factory_v1/demos/alpha_agi_business_v1/run_business_v1_demo.sh [--pull] [--gpu]` (docs: `http://localhost:8000/docs`)|
|3|`alpha_agi_business_2_v1`|🏗|Iterates business model with live market data RAG.|Continuous adaptation → durable competitive alpha.|`./alpha_factory_v1/demos/alpha_agi_business_2_v1/run_business_2_demo.sh`|
|4|`alpha_agi_business_3_v1`|📊|Financial forecasting & fundraising agent swarm.|Optimises capital stack for ROI alpha.|`./alpha_factory_v1/demos/alpha_agi_business_3_v1/run_business_3_demo.sh`|
|5|`alpha_agi_marketplace_v1`|🛒|Peer‑to‑peer agent marketplace simulating price discovery.|Validates micro‑alpha extraction via agent barter.|`docker compose -f demos/docker-compose.marketplace.yml up`|
|6|`alpha_asi_world_model`|🌌|Scales MuZero‑style world‑model to an open‑ended grid‑world.|Stress‑tests anticipatory planning for ASI scenarios.|`docker compose -f demos/docker-compose.asi_world.yml up`|
|7|`cross_industry_alpha_factory`|🌐|Full pipeline: ingest → plan → act across 4 verticals.|Proof that one orchestrator handles multi‑domain alpha.|`./alpha_factory_v1/demos/cross_industry_alpha_factory/deploy_alpha_factory_cross_industry_demo.sh`|
|8|`era_of_experience`|🏛|Lifelong RL stack blending real & synthetic experience streams.|Showcases sensor-motor tools, grounded rewards & non-human reasoning.|`cd alpha_factory_v1/demos/era_of_experience && ./run_experience_demo.sh`|
|9|`finance_alpha`|💹|Live momentum + risk‑parity bot on Binance test‑net.|Generates real P&L; stress‑tested against CVaR.|`./alpha_factory_v1/demos/finance_alpha/deploy_alpha_factory_demo.sh`|
|10|`macro_sentinel`|🌐|GPT‑RAG news scanner auto‑hedges with CTA futures.|Shields portfolios from macro shocks.|`docker compose -f demos/docker-compose.macro.yml up`|
|11|`muzero_planning`|♟|MuZero in 60 s; online world‑model with MCTS.|Distills planning research into a one‑command demo.|`./alpha_factory_v1/demos/muzero_planning/run_muzero_demo.sh`|
|12|`self_healing_repo`|🩹|Repo-Healer v1 runs bounded triage + targeted repair for this repo.|Maintains pipeline uptime alpha.|`docker compose -f demos/docker-compose.selfheal.yml up`|

> **Colab?** Each folder ships an `*.ipynb` that mirrors the Docker flow with free GPUs.

### Demo Stability
| Demo | Purpose | Stability |
|------|---------|-----------|
|[aiga_meta_evolution](demos/aiga_meta_evolution/README.md)|Agents evolve new agents|Incub|
|[alpha_agi_business_v1](demos/alpha_agi_business_v1/README.md)|Auto-incorporates a digital-first company|Prod|
|[alpha_agi_business_2_v1](demos/alpha_agi_business_2_v1/README.md)|Market-adaptive business iteration|Beta|
|[alpha_agi_business_3_v1](demos/alpha_agi_business_3_v1/README.md)|Fundraising agent swarm for forecasting|Prod|
|[alpha_agi_marketplace_v1](demos/alpha_agi_marketplace_v1/README.md)|Peer-to-peer agent marketplace|Prod|
|[alpha_asi_world_model](demos/alpha_asi_world_model/README.md)|Open-ended world model training|Beta|
|[cross_industry_alpha_factory](demos/cross_industry_alpha_factory/README.md)|Pipeline across multiple verticals|Prod|
|[era_of_experience](demos/era_of_experience/README.md)|Autobiographical memory RL playground|Incub|
|[finance_alpha](demos/finance_alpha/README.md)|Momentum and risk-parity bot|Beta|
|[macro_sentinel](demos/macro_sentinel/README.md)|News scanner with futures hedging|Beta|
|[muzero_planning](demos/muzero_planning/README.md)|Minimal MuZero planning demo|Beta|
|[self_healing_repo](demos/self_healing_repo/README.md)|Agents auto-fix failing CI|Beta|
|[meta_agentic_tree_search_v0](demos/meta_agentic_tree_search_v0/README.md)|Recursive agent tree search|Incub|
|[alpha_agi_insight_v0](demos/alpha_agi_insight_v0/README.md)|Sector ranking via zero-data search|Beta|

### 4.1 · [α-ASI World-Model Demo 👁️✨](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_asi_world_model)

Paper: [Multi-Agent AGENTIC α-AGI World-Model Demo 🥑](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/alpha_asi_world_model/Alpha_ASI_World_Model.pdf)

```
┌──────────────────────────────── Alpha-Factory Bus (A2A) ───────────────────────────────┐
│                                                                                        │
│   ┌──────────────┐   curriculum   ┌───────────┐   telemetry   ┌────────────┐          │
│   │ StrategyAgent│───────────────►│ Orchestr. │──────────────►│   UI / WS  │          │
│   └──────────────┘                │  (loop)   │◄──────────────│  Interface │          │
│          ▲  ▲                     └───────────┘    commands   └────────────┘          │
│          │  │ new_env/reward                     ▲                                   │
│   plans  │  │ loss stats                        │ halt                              │
│          │  └──────────────────────┐            │                                   │
│   ┌──────┴───────┐   context       │            │                                   │
│   │ ResearchAgent│───────────────► Learner (MuZero) ◄─ SafetyAgent (loss guard)      │
│   └──────────────┘                │   ▲                                             │
│              code patches         │   │                                             │
│   ┌──────────────┐                │   │ gradients                                   │
│   │ CodeGenAgent │────────────────┘   │                                             │
│   └──────────────┘                    │                                             │
│                                       ▼                                             │
│                            POET Generator → MiniWorlds (env pool)                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 · [🏛️ Large‑Scale α‑AGI Business 3 Demo 👁️✨ — **Omega‑Grade Edition**](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/alpha_agi_business_3_v1)

> **Alpha‑Factory v1 → Ω‑Lattice v0**  
> _Transmuting cosmological free‑energy gradients into compounding cash‑flows._

Multi‑Scale Energy‑Landscape Diagram:

```mermaid
flowchart TB
  subgraph Macro["Macro‑Finance Δβ"]
    FIN[FinanceAgent]:::agent
    ENE[EnergyAgent]:::agent
  end
  subgraph Meso["Supply‑Chain ΔS"]
    MFG[ManufacturingAgent]:::agent
    LOG[LogisticsAgent]:::agent
  end
  subgraph Micro["Bio/Chem ΔH"]
    BIO[BiotechAgent]:::agent
    MAT[MaterialsAgent]:::agent
  end
  FIN & ENE -->|β feed| ORC
  MFG & LOG -->|entropy ΔS| ORC
  BIO & MAT -->|latent ΔH| ORC
  classDef agent fill:#cffafe,stroke:#0369a1;
```

Cells with \(Δ\mathcal F < 0\) glow 🔵 on Grafana; Ω‑Agents race to harvest.

---

<a name="5-memory--knowledge-fabric"></a>
## 5 · Memory & Knowledge Fabric 🧠

```
[Event] --embedding--> PGVector DB
                   \--edge--> Neo4j (CAUSES, SUPPORTS, RISK_OF)
```

* Agents query `mem.search("supply shock beta>0.2")`  
* Planner asks Neo4j: `MATCH (a)-[:CAUSES]->(b) WHERE b.delta_alpha > 5e6 RETURN path`

---

<a name="6-5-minute-quick-start"></a>
## 6 · 5‑Minute Quick‑Start 🚀
```bash
git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1
./quickstart.sh --preflight

# optional: point to an external Kafka broker
export ALPHA_KAFKA_BROKER=localhost:9092
echo "PORT=8000" > .env
echo "LOGLEVEL=info" >> .env
chmod 600 alpha_factory_v1/.env
./quickstart.sh  # automatically loads .env
open http://localhost:8000/docs
```

No GPU → falls back to GGML Llama‑3‑8B‑Q4.
No `OPENAI_API_KEY` → switches to local SBERT + heuristics.
`OPENAI_TIMEOUT_SEC` sets the OpenAI API request timeout in seconds (default 30).

---

<a name="7-deployment-recipes"></a>
## 7 · Deployment Recipes 🍳
The repository ships with an `edge_runner.py` script for portable,
offline deployments. It forwards to the Python module and supports
extra flags such as `--cycle`, `--loglevel` and `--version`.

| Target | Command | Notes |
|--------|---------|-------|
| **Docker Compose** | `docker compose up -d` | Kafka, Prometheus, Grafana |
| **Helm (K8s)** | `helm install af charts/alpha-factory` | SPIFFE, HPA |
| **AWS Fargate** | `./infra/deploy_fargate.sh` | SQS shim for Kafka |
| **IoT Edge** | `python edge_runner.py --agents manufacturing,energy` | Jetson Nano |

---

<a name="8-governance--compliance"></a>
## 8 · Governance & Compliance ⚖️

* **MCP envelopes** (SHA‑256, ISO‑8601, policy hash)  
* **Red‑Team Suite** fuzzes prompts & actions  
* **Attestations** — W3C Verifiable Credentials at every Actuator call

---

<a name="9-observability"></a>
## 9 · Observability 🔭

| Signal | Sink | Example |
|--------|------|---------|
| Metrics | Prometheus | `alpha_pnl_realised_usd` |
| Traces | OpenTelemetry | `trace_id` |
| Dashboards | Grafana | `alpha-factory/trade-lifecycle.json` |
| Config | `docs/prometheus.yml` | Prometheus & Grafana defaults |

Docker Compose mounts `docs/prometheus.yml` and the Grafana provisioning files
so metrics are available out-of-the-box.

---

<a name="10-extending-the-mesh"></a>
## 10 · Extending the Mesh 🔌
```python
from backend.agents.base import AgentBase

class MySuperAgent(AgentBase):
    NAME = "super"
    CAPABILITIES = ["telemetry_fusion"]
    COMPLIANCE_TAGS = ["gdpr_minimal"]

    async def run_cycle(self):
        ...

# setup.py entrypoint
[project.entry-points."alpha_factory.agents"]
super = my_pkg.super_agent:MySuperAgent
```
`pip install .` → orchestrator hot‑loads at next boot.

---

<a name="11-troubleshooting"></a>
## 11 · Troubleshooting 🛠️

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: faiss` | FAISS missing | `pip install faiss-cpu` |
| Agent quarantined | exceptions | Check logs, clear flag |
| Kafka refuse | broker down | unset `ALPHA_KAFKA_BROKER` |

---

### Running Tests

Use the helper script below to execute the full test-suite. It automatically
falls back to Python's built-in `unittest` discovery when `pytest` is not
available.

```bash
python -m alpha_factory_v1.scripts.run_tests
```
---

<a name="12-roadmap"></a>
## 12 · Roadmap 🛣️

1. **RL‑on‑Execution** — slippage‑aware order routing  
2. **Federated Mesh** — cross‑org agent exchange via ADK federation  
3. **World‑Model Audits** — interpretable probes of latents  
4. **Industry Packs** — Health‑Care, Gov‑Tech  
5. **Provable Safety ℙ** — Coq proofs for Actuators  

---

<a name="13-credits"></a>
## 13 · Credits 🌟

[Vincent Boucher](https://www.linkedin.com/in/montrealai/)—pioneer in AI and President of [MONTREAL.AI](https://www.montreal.ai/) since 2003—dominated the [OpenAI Gym](https://web.archive.org/web/20170929214241/https://gym.openai.com/read-only.html) with **AI Agents** in 2016 and unveiled the seminal [**“Multi‑Agent AI DAO”**](https://www.quebecartificialintelligence.com/priorart) in 2017.

Our **AGI ALPHA AGENT**, fuelled by the strictly‑utility **$AGIALPHA** token, now taps that foundation to unleash the ultimate α‑signal engine.

---

*Made with ❤️ by the Alpha‑Factory Agentic Core Team — forging the tools that forge tomorrow.*
