[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# Meta‑Agentic α‑AGI 👁️✨ Demo v2 – **Production‑Grade v0.1.0**

![preview](../meta_agentic_agi_v2/assets/preview.svg){.demo-preview}

[Launch Demo](../meta_agentic_agi_v2/index.html){.md-button}

Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.



# Meta‑Agentic α‑AGI 👁️✨ Demo v2 – **Production‑Grade v0.1.0**

Identical to **v1** plus a statistical-physics wrapper that logs and minimises **Gibbs / variational free-energy** for each candidate agent during the evolutionary search.

*Metric toggle*: `configs/default.yml → physics_metric: free_energy`  
Implementation: `core/physics/gibbs.py` (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/≈25 LoC) & 4-line hook in `scorer.py`.

> **Official definition – Meta-Agentic (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/adj.)**  
> *Describes an agent whose **primary role** is to **create, select, evaluate, or re‑configure other agents** and the rules governing their interactions, thereby exercising **second‑order agency** over a population of first‑order agents.*

> *The term was **pioneered by Vincent Boucher, President of MONTREAL.AI**.*

```mermaid
%% 𝗚𝗿𝗮𝗻𝗱 𝗦𝘆𝗻𝗮𝗽𝘀𝗲 𝗚𝗿𝗮𝗽𝗵 – Meta-Agentic α-AGI (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/v2 with variational free-energy)
graph LR
  %% ─────────────────────  Class styles
  classDef meta      fill:#6425ff,stroke:#eee,color:#fff
  classDef layer     fill:#1e1e2e,stroke:#ddd,color:#fff
  classDef agent     fill:#0f9d58,stroke:#fff,color:#fff
  classDef tool      fill:#fbbc05,stroke:#000,color:#000
  classDef physics   fill:#ff6d00,stroke:#000,color:#fff

  %% ─────────────────────  High-level layers
  A0["🧠 Meta-Programmer"]:::meta
  A1["📈 Evolution Archive"]:::layer
  A2["⚖️ Multi-Objective Scorer"]:::layer
  Aφ["♾️ Free-Energy Monitor"]:::physics
  A3["🧩 Agent Population"]:::layer

  %% ─────────────────────  First-order agents
  subgraph " "
    direction TB
    D1["🔍 Researcher"]:::agent
    D2["👷 Builder"]:::agent
    D3["🧪 Evaluator"]:::agent
    D4["⚙️ Auto-Tuner"]:::agent
    D5["🛡 Guardian"]:::agent
  end

  %% ─────────────────────  Foundation-model providers / tools
  subgraph " "
    direction TB
    T1["GPT-4o"]:::tool
    T2["Claude-3"]:::tool
    T3["Llama-3 ∞"]:::tool
  end

  %% ─────────────────────  Core data/value loop
  subgraph " "
    direction LR
    V1["🌐 Industry Data Streams"]
    V2["💎 Extracted Alpha"]
    V3["🚀 Deployed Solutions"]
  end

  %% ─────────────────────  Arrows
  A0 -->|generate| A3
  A3 -->|select| A2
  A2 -->|rank| A1
  A1 -- feedback --> A0

  %% Free-energy feedback
  A3 -.state logits.-> Aφ
  Aφ -->|F metric| A2
  Aφ -- entropy gradient --> A0

  %% Providers
  D1 -.uses.-> T1
  D2 -.uses.-> T3
  D3 -.uses.-> T2
  D4 -.uses.-> T3
  D5 -.uses.-> T1

  %% Value extraction
  A3 -->|iterate| V1
  V1 -->|signals| D1
  D2 --> V2
  V2 --> D3
  D4 --> V3
  D5 -.audit.-> V3
```

> **Elevating Alpha‑Factory v1 into a self‑improving, cross‑industry “Alpha Factory” that systematically  
> Out‑Learn · Out‑Think · Out‑Design · Out‑Strategize · Out‑Execute — without coupling to a single vendor or model.**  
> Inspired by and extending the *Meta‑Agent Search* paradigm from Hu *et al.* (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/ICLR 2025).

---

## 📌 Purpose & Positioning
This demo operationalises the **Automated Design of Agentic Systems (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/ADAS)** paradigm and layers:

* **True multi‑objective search** (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/accuracy, cost, latency, risk, carbon)
* **Open‑weights or API‑based FM back‑ends** (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/OpenAI, Anthropic, Mistral .gguf …)
* **Automated provenance & lineage visualisation**
* **Antifragile, regulator‑ready safeguards**

into the existing **Alpha‑Factory v1** (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/multi‑agent AGENTIC α‑AGI) pipeline.

---

## 1 Quick‑start 🏁
```bash
# 1️⃣ Clone & enter demo
git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1/demos/meta_agentic_agi_v2

# 2️⃣ Environment (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/CPU‑only default)
micromamba create -n metaagi python=3.11 -y
micromamba activate metaagi
pip install -r requirements.txt        # ≤ 40 MiB wheels

# 3️⃣ Run – zero‑API mode (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/pulls a gguf via Ollama)
python meta_agentic_agi_demo_v2.py --provider mock:echo       # offline demo
#   …or real weights
python meta_agentic_agi_demo_v2.py --provider mistral:7b-instruct.gguf

#   …or point to any provider
OPENAI_API_KEY=sk‑… python meta_agentic_agi_demo_v2.py --provider openai:gpt-4o

# 4️⃣ Launch the lineage UI
streamlit run ui/lineage_app.py
```
*No GPU?* llama‑cpp‑python auto‑selects 4‑bit quantisation < 6 GB RAM.

### 🎓 Colab notebook

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/colab_meta_agentic_agi_v2.ipynb)

Spin up the demo end‑to‑end without installing anything. Works offline using open‑weights or with your API keys. The notebook now previews the latest lineage entries after the search loop so you can inspect results directly in Colab.

---

## 2 Folder Structure 📁
```
meta_agentic_agi_v2/
├── core/                # provider‑agnostic primitives
│   ├── fm.py            # unified FM wrapper
│   ├── prompts.py       # reusable prompt fragments
│   └── tools.py         # exec sandbox, RAG, vector store
├── meta_agentic_search/ # ⬅ evolutionary loop
│   ├── archive.py       # stepping‑stone JSONL log
│   ├── search.py        # NSGA‑II + Reflexion
│   └── scorer.py        # multi‑objective metrics
├── agents/
│   ├── agent_base.py    # runtime interface
│   └── seeds.py         # bootstrap population
├── ui/
│   ├── lineage_app.py   # Streamlit dashboard
│   └── assets/
├── configs/
│   └── default.yml      # editable in‑UI
└── meta_agentic_agi_demo_v2.py
```

---

## 3 High‑Level Architecture 🔍
```mermaid
graph TD
  subgraph "Meta Agent Search Loop"
    MGPT["Meta LLM Programmer"]
    Candidate["Candidate Agent<br/>Python fn"]
    Evaluator["Sandboxed Evaluator"]
    Archive["Archive<br/>(https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/Pareto + Novelty)"]
    MGPT -->|generates| Candidate
    Candidate --> Evaluator
    Evaluator -->|scores| Archive
    Archive -->|context & feedback| MGPT
  end
  UI["Streamlit Lineage UI"] <-->|stream
lineage| Archive
```

```mermaid
flowchart LR
  AFV1["Alpha‑Factory v1 Core"]
  MAA["Meta‑Agentic Layer"]
  Providers["FM Providers<br/>(https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/OpenAI / Anthropic / llama‑cpp)"]
  Dataset["Domain Datasets"]
  UI2["Lineage UI"]
  AFV1 --> MAA
  MAA --> Providers
  MAA --> Dataset
  Archive -.-> UI2
```

---

## 4 Provider Abstraction ➡️ open‑weights 🏋️‍♀️
`configs/default.yml` (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/excerpt):
```yaml
provider: mistral:7b-instruct.gguf   # any ollama / llama.cpp id
context_length: 8192
rate_limit_tps: 4
retry_backoff: 2
```

Change **provider** to:

| Value                       | Notes                      |
|-----------------------------|----------------------------|
| `openai:gpt-4o`             | needs `OPENAI_API_KEY`     |
| `anthropic:claude-3-sonnet` | needs `ANTHROPIC_API_KEY`  |
| `mistral:7b-instruct.gguf`  | default local model        |
| `mock:echo`                 | offline stub, for tests |
---

## 5 Multi‑Objective Search 🎯
*Objective vector* = **[accuracy, cost, latency, hallucination‑risk, carbon]**

* NSGA‑II elitist selection  
* Behaviour descriptor = SHA‑256 of candidate AST  
* Optional human‑in‑the‑loop thumbs up/down (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/UI)

---

## 6 Security & Antifragility 🛡
* Firejail `--seccomp` + 512 MiB mem‑cgroup sandbox  
* Static analysis (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/`bandit`) + dynamic taint tracking  
* Live watchdog kills rogue processes > 30 s CPU  
* Chaos‑tests inject tool failures; reward graceful degradation

---

## 7 Extending 🛠
1. **New dataset** – drop `my.pkl` into `data/`, flag `--dataset my`.  
2. **New metric** – subclass `scorer.BaseMetric`, list in `configs/default.yml`.  
3. **New tool** – add `core/tools/foo.py` exposing `__call__(https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/self, query)`.

---

## 8 Roadmap 🗺
* ☐ Hierarchical meta‑meta search  
* ☐ GPU batch infer (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/Flash‑infer v3)  
* ☐ Offline RL fine‑tune search policy with lineage replay

---

## 9 References 📚
* S. Hu *et al.* “Automated Design of Agentic Systems” ICLR 2025  
* OpenAI “A Practical Guide to Building Agents” (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/2024)  
* Google ADK docs (https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/2025)

---

© 2025 MONTREAL.AI — Apache‑2.0

[View README on GitHub](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_agi_v2/README.md)
