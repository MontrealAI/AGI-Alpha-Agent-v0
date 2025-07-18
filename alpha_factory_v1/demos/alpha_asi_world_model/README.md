[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.


<!--
README  ░α-ASI World-Model Demo ░  Alpha-Factory v1 👁️✨
Last updated 2025-04-25   Maintainer → Montreal.AI Core AGI Team
-->

<h1 align="center">α-ASI World-Model Demo 👁️✨</h1>
<p align="center">
  <em>The open-ended curriculum engine + MuZero learner that powers the
  <strong>Alpha-Factory v1</strong> multi-agent runtime.</em><br>
  <strong>Out-Learn · Out-Think · Out-Design · Out-Strategise · Out-Execute</strong>
</p>

---

## 0  Table of Contents  <!-- omit in toc -->
1. [Why this demo matters](#1-why-this-demo-matters)
2. [Quick-start 🥑](#2-quick-start-)
   - [Offline setup](#offline-setup)
3. [High-level architecture 🗺️](#3-high-level-architecture-️)
4. [Meet the agents 🤖 (≥ 5)](#4-meet-the-agents-️-≥-5)
5. [Runtime controls 🎮](#5-runtime-controls-)
6. [Deployment recipes 🚀](#6-deployment-recipes-)
7. [Safety, antifragility & governance 🛡️](#7-safety-antifragility--governance-)
8. [Extending the demo 🧩](#8-extending-the-demo-)
9. [Troubleshooting 🔧](#9-troubleshooting-)
10. [Production checklist ✅](#10-production-checklist-)
11. [License & citation](#11-license--citation)

---

## 1  Why this demo matters

> **Mission** Prove that a constellation of **agentic micro-services** can
> _independently grow their own synthetic worlds_ (open-ended _POET_ curriculum),
> _learn a general world-model_ (MuZero-style), automate strategy research,
> detect live **alpha** opportunities across industries, and march toward the
> **α-ASI** referenced by Vincent Boucher, President of MONTREAL.AI and QUEBEC.AI ⚡).

Success criteria ✓  

| Pillar | Concrete demonstration |
| ------ | ---------------------- |
| **Open-Endedness** | Automatic generation & evaluation of ever harder MiniWorld mazes |
| **World-Models** | MuZero learner predicts reward/value & policy without ground-truth rules |
| **Multi-Agent** | ≥ 5 independent Alpha-Factory agents coordinate via A2A bus |
| **Cross-Industry Alpha** | StrategyAgent spots profitable “alpha” events (simulated market feed) |
| **Antifragility** | SafetyAgent can freeze learner on NaN/spike; system self-recovers |
| **Local-First** | No internet or API keys required; LLM helpers activate only if keys provided |

---

## 2  Quick-start 🥑

```bash
# ░ Local Python (CPU or GPU)
pip install -r requirements.txt        # torch, fastapi, uvicorn…

# All interactive helpers (`run_ui`, `run_headless`) require these packages.

`torch` is by far the largest dependency. Tests that import it are skipped when
the package is missing. For a short smoke test use:
```bash
pytest -m 'not e2e'
```

# new CLI (after `pip install -e .` at repo root)
alpha-asi-demo --demo        # same as `python -m alpha_asi_world_model_demo --demo`
alpha-asi-demo --demo --no-llm   # force-disable the optional LLM planner
python -m webbrowser http://localhost:7860  # dashboard & Swagger

# ░ One-liner Docker
python -m alpha_asi_world_model_demo --emit-docker
docker build -t alpha_asi_world_model .
docker run -p 7860:7860 alpha_asi_world_model

# ░ Helm (K8s)
python -m alpha_asi_world_model_demo --emit-helm
helm install alpha-asi ./helm_chart

# ░ Notebook
python -m alpha_asi_world_model_demo --emit-notebook
jupyter lab alpha_asi_world_model_demo.ipynb
# ░ Colab
Open `alpha_asi_world_model_colab.ipynb` in Google Colab for an end-to-end guided setup.
Non‑technical users can run it step by step:
1. Visit the notebook on GitHub and click **Open in Colab**.
2. Wait for the environment to start then choose **Runtime → Run all** (or run each cell manually).
3. The notebook installs requirements and launches the demo. When no API key is provided it automatically sets `NO_LLM=1`.
4. Interact with the dashboard in the new browser tab and run the final **Shut down** cell when done.
# ░ Shell helper
./deploy_alpha_asi_world_model_demo.sh
# ░ OpenAI Agents bridge
# uses ``OPENAI_API_KEY`` if set
python openai_agents_bridge.py
# ░ Google ADK gateway
ALPHA_FACTORY_ENABLE_ADK=true python openai_agents_bridge.py
```
Set `OPENAI_API_KEY` to connect the bridge to the OpenAI Agents platform.

> **Tip 💡** Set `ALPHA_ASI_SEED=<int>` or `general.seed` in `config.yaml` to reproduce identical curriculum runs.
> **Tip 💡** Set `ALPHA_ASI_SILENT=1` to hide the startup banner.

### Offline setup
When working without internet access, first build a local wheelhouse:

```bash
mkdir -p /media/wheels
pip wheel -r requirements.txt -w /media/wheels
pip wheel -r ../../../requirements-dev.txt -w /media/wheels
```

Install and verify using the wheelhouse from the repository root:

```bash
WHEELHOUSE=/media/wheels AUTO_INSTALL_MISSING=1 ./codex/setup.sh
WHEELHOUSE=/media/wheels AUTO_INSTALL_MISSING=1 \
  python check_env.py --auto-install --wheelhouse /media/wheels
```
See [docs/OFFLINE_SETUP.md](../../../docs/OFFLINE_SETUP.md) for a short
reference.

Set `NO_LLM=1` to disable the planning agent when no API key is available. The
`deploy_alpha_asi_world_model_demo.sh` helper exports this variable
automatically.
Define `ALPHA_ASI_LLM_MODEL=gpt-4o-mini` to change the planner's model.

### Device selection
`config.yaml` exposes a `device` field controlling which accelerator PyTorch
uses. Accepted values are `cpu`, `cuda` and `auto`. With `auto` (the default),
the demo runs on GPU when `torch.cuda.is_available()` returns `True` and falls
back to CPU otherwise.

---

## 3  High-level architecture 🗺️

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

* **All messages** flow through a single in-proc **A2A** topic bus (swap for
  Redis/NATS at scale).  
* **MCP** is used by ResearchAgent to attach rich “context blocks” to
  learner queries when an LLM key is supplied.  
* Components comply with **OpenAI Agents SDK** & **Google ADK** lifecycle
  (`init/step/shutdown`), so they can be re-packaged as micro-services at will.

---

## 4  Meet the agents 🤖 (≥ 5)

| Topic 🛰 | Skill | How it contributes to **End-to-End Alpha** |
|--------------|-------|-------------------------------------------|
| **planning_agent** | Long-horizon curriculum sketching (optionally via GPT-4o) | Keeps learner near its “zone of proximal development” → faster capability gain |
| **research_agent** | Literature & data mining (papers, patents, SEC filings…) | Injects distilled insights; helps learner transfer skills across domains |
| **strategy_agent** | Real-time alpha detection (mock market feed 📈) | Signals lucrative industry opportunities; triggers env mutations that mimic them |
| **codegen_agent** | Auto-ML / network surgery | Evolves MuZero hyper-params & architecture → antifragile optimisation |
| **market_agent** | Streams synthetic or live financial ticks | Provides cross-domain stressor; validates Alpha-capture loops |
| **safety_agent** | Alignment guardrails | Halts on NaN/catastrophe; enforces resource quotas & ethical policies |

*(If a concrete implementation is absent the stub logs every call, guaranteeing
bus liveness even on a clean clone.)*

---

## 5  Runtime controls 🎮

| REST | Use case |
|------|----------|
| `GET /agents` | List active agent topics |
| `POST /command {"cmd":"new_env"}` | Force-spawn a fresh world |
| `POST /command {"cmd":"stop"}` | Graceful halt ⏸ |

**WebSocket (`/ws`)** streams JSON telemetry every `ui_tick` steps:  
`{"t":1234,"r":-0.01,"loss":0.872}` → plug into Grafana or a custom React chart.

---

## 6  Deployment recipes 🚀

| Target | Guide |
|--------|-------|
| 🐳 **Docker** | Auto-generated `Dockerfile` (<100 MB slim). GPU builds: swap base for `nvidia/cuda:runtime-12.4`. |
| ☸️ **Kubernetes** | Run `--emit-helm`; edit values (`replicaCount`, `resources.limits`). Works on GKE, AKS, EKS, k3d. |
| 🐍 **Pure Python** | No Docker needed; just `pip install -r requirements.txt`. |
| 🔒 **Air-gapped** | Offline wheels; set `NO_LLM=1` to disable the planner or omit API keys. |
| 🔑 **Cloud LLM mode** | Export `OPENAI_API_KEY` → PlanningAgent & ResearchAgent auto-upgrade to LLM assistants. |

---

## 7  Safety, antifragility & governance 🛡️

* **Reward-hacking firewall** — StrategyAgent & SafetyAgent cross-check any
  sudden reward spike; suspicious events quarantine the environment seed for
  forensic replay.  
* **Loss guard** — Threshold `loss > 1e3` or `NaN` triggers global `stop`.  
* **Compute budget** — Learner train loop obeys `torch.set_grad_enabled(False)`
  for evaluation, cuts GPU utilisation to ≤ 80 %.  
* **Policy logging** — Every 10 k steps, MuZero weights hashed (SHA‑256) +
  signed for traceability.  
* **Audit-ready** — All IPC messages dumped to `./logs/audit_<ts>.ndjson`
  (regulator-friendly).

---

## 8  Extending the demo 🧩

> **One-file hackability** yet **enterprise scalability**.

1. **New env type** → subclass `MiniWorld` (`step/reset/obs`), register in
   `POETGenerator.propose`.  
2. **Swap learner** → Implement `.act/.remember/.train` in a new class;
   StrategyAgent can trigger hot-swap via `{"cmd":"swap_learner"}`.  
3. **External micro-service** → Re-use `BaseAgent`; deploy as HTTP worker that
   bridges to A2A via WebSockets.

---

## 9  Troubleshooting 🔧

| Problem | Cause / Fix |
|---------|-------------|
| _“UI stalls”_ | Browser blocked WS → check console; ensure port 7860 reachable. |
| _CUDA OOM_ | `export TORCH_FORCE_CPU=1` or downsize net via CodeGenAgent. |
| _Docker build slow_ | Add build-arg `TORCH_WHL=<local-wheel>` (offline). |
| _K8s CrashLoop_ | `kubectl logs`; missing GPU driver or env var. |
| _Hide banner_ | Set `ALPHA_ASI_SILENT=1` before launching. |

Need help? Open an issue → **@MontrealAI/alpha-factory-core**.

## 10  Production checklist ✅

- Ensure `python3 --version` returns 3.11–3.12.
- Install dependencies: `pip install -r requirements.txt`.
- Launch via `./deploy_alpha_asi_world_model_demo.sh` and visit `http://localhost:7860`.
- The script sets `NO_LLM=1` automatically when `OPENAI_API_KEY` is unset.
- Provide an `OPENAI_API_KEY` to unlock planner features.
- Set `NO_LLM=1` to skip the LLM planner even when a key is provided.

---

## 11  License & citation

```
Apache‑2.0 © 2025 MONTREAL.AI
```

Please cite **Alpha-Factory v1 👁️✨ — Multi-Agent AGENTIC α-AGI**:

> MONTREAL.AI (2025). *Fully-Agentic α-AGI: Foundation World Models for α-ASI.*  
> GitHub https://github.com/MontrealAI/AGI-Alpha-Agent-v0
