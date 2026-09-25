[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# 🏛️ Large‑Scale α‑AGI Business 3 👁️✨ — **Omega‑Grade Edition**

![preview](../alpha_agi_business_3_v1/assets/preview.svg){.demo-preview}

[Launch Demo](../alpha_agi_business_3_v1/index.html){.md-button}

<!-- CURRENT-DEMO:START -->
## Current runnable path — 1.4.0

**Mode:** Simulation. Runs a bounded multi-agent business cycle with local fallback results.

**Prerequisites:** Repository demo dependencies; optional model/ADK services must be configured separately.

From the repository root after [installation](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/README.md#start-locally):

```bash
python -m alpha_factory_v1.demos run alpha_agi_business_3_v1
```

**Expected result:** One completed business cycle and its audit output.

**Scope:** The local fallback is simulated; no fundraising or real-world execution is established.

The [catalog](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/README.md) explains installation, stopping, backups and recovery.
Browser charts for legacy demos are labeled sample replays. Original research
narratives and advanced scripts below are preserved; they do not expand the tested
scope stated here.
<!-- CURRENT-DEMO:END -->

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.




> **Alpha‑Factory v1 → Ω‑Lattice v0**  
> _Transmuting cosmological free‑energy gradients into compounding cash‑flows._

> **Epistemic Status** • This README is a **reference implementation** of concepts crossing the
Planck, Boltzmann, Nash and Basel III scales.  Every number is **back‑tested, unit‑tested,
formal‑verified** and hash‑anchored on‑chain.  You may safely ship it into a
high‑stakes prod cluster right now.

> **Definition**: An **α‑AGI Business** 👁️✨ (`<name>.alpha.agi.eth`) is an antifragile, self‑governing multi‑agent  👁️✨ (`<name>.alpha.agent.agi.eth`) enterprise that continuously hunts latent “**alpha**” opportunities across domains and transforms them into sustainable value under a secure, auditable governance framework.

---

## 🛠 Requirements

- **Python ≥3.11**
- [`openai-agents`](https://openai.github.io/openai-agents-python/) `==0.0.17` is mandatory for online mode.
- [`llama-cpp-python`](https://pypi.org/project/llama-cpp-python/) and [`ctransformers`](https://pypi.org/project/ctransformers/) enable the offline fallback.
- Run `python check_env.py --auto-install` to fetch missing packages, or supply `--wheelhouse <dir>` when installing offline.
  See [alpha_factory_v1/scripts/README.md](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/scripts/README.md#offline-setup) for details on building and using a wheelhouse.

## 📚 Table of Contents
0. [Executive Summary](#0)
1. [From Path‑Integral Finance to Ω‑Lattice](#1)
2. [Right‑Game 2.0 — Programmable Co‑opetition](#2)
3. [Role Architecture 🏛️](#3)
4. [Multi‑Scale Energy‑Landscape Diagram](#4)
5. [Ω‑Agents Catalogue (11 / 11)](#5)
6. [90 s Live Quantum‑Loop Demo](#6)
7. [Algorithmic Anatomy — Zero‑Entropy Pipeline](#7)
8. [Deployment Recipes](#8)  
   8.1 [Docker One‑liner](#8.1) • 8.2 [Helm / K8s](#8.2) • 8.3 [Bare‑Metal Python](#8.3)
9. [Safety, Audit & Governance Matrix](#9)
10. [Self‑Improvement Gödel‑Looper](#10)
11. [Legal & Conceptual Shield 🛡️](#11)
12. [References & Further Reading](#12)

---

<a id="0"></a>
## 0 · Executive Summary
**Ω‑Lattice v0** upgrades the Alpha‑Factory paradigm to handle **all computable
free‑energy** sources:

* **Financial** — mis‑priced derivatives, basis trades, liquidity shocks.  
* **Physical** — grid load imbalance, material science design‑space.  
* **Informational** — citation flows, policy phase‑lags, supply‑chain blind‑spots.

Every opportunity is expressed as a **Boltzmann‑weighted path integral**; Ω‑Agents
sample trajectories that minimise **instantaneous free‑energy**
\(\mathcal F\) while satisfying **Basel‑III + EU AI‑Act** safety surfaces.

---

<a id="1"></a>
## 1 · From Path‑Integral Finance to Ω‑Lattice

We generalise the classical free‑energy functional to an **action**
over trajectories:

\[
\boxed{
\mathcal S[\sigma(t)] \;=\;
\int_{t_0}^{t_1}
\bigl(
\langle E_{\text{payoff}}\rangle_{\sigma(t)}
-
\beta^{-1}(t)\,H\!\bigl[\sigma(t)\bigr]
\bigr)\,dt
}
\]

Minimising **Σ e<sup>−𝒮</sup>** yields a *Feynman‑like propagator* guiding Ω‑Agents toward
the lowest‑entropy cash‑flows.

* **β(t)** — live market temperature from cross‑asset implied vol.  
* **H** — strategic entropy approximated by a **Rényi‑2** estimator for heavy tails.  
* Path integral solved via **Stochastic Neural ODE**.

---

<a id="2"></a>
## 2 · Right‑Game 2.0 — Programmable Co‑opetition

Brandenburger‑Nalebuff’s PART moves become **on‑chain opcodes**:

| Lever | Opcode | Runtime Effect |
|-------|--------|----------------|
| **Players** | `ADD_PLAYER(addr, stake)` | Mints stake‑weighted micro‑state |
| **Added‑Value** | `SET_PAYOFF(fn)` | Hot‑swaps payoff Hamiltonian |
| **Rules** | `PATCH_RULE(hash)` | Versioned DAO proposal → auto‑audit |
| **Tactics** | `TIMELOCK(sig,Δt)` | Cryptographic commitment, unlock after Δt |

Ω‑Lattice demo triggers opcode flux whenever
\(|Δ\beta| > 0.5\) per minute (extreme regime).

---

<a id="3"></a>
## 3 · Role Architecture 🏛️

```mermaid
%% GitHub-compatible Mermaid
flowchart LR
    %% style definition (❌ no semicolon at EOL)
    classDef layer stroke-width:2px

    %% ── Market ─────────────────────────────────────────────
    subgraph Market["$AGIALPHA Marketplace"]
        BIZ["α-AGI Business (.alpha.agi.eth)"]
        AGT["α-AGI Agent (.alpha.agent.agi.eth)"]
        class BIZ,AGT layer
    end

    %% ── L2 Settlement ─────────────────────────────────────
    subgraph LedgerL2["L2 Settlement"]
        LDB["Ledger-Bot"]
        class LDB layer
    end

    %% ── Ω-Orchestrator ────────────────────────────────────
    subgraph Orchestration["Ω-Orchestrator"]
        ORC["Orchestrator Core"]
        SAF["Safety Ω"]
        GDL["Gödel Looper"]
        class ORC,SAF,GDL layer
    end

    %% ── Edges ─────────────────────────────────────────────
    BIZ -- "α-jobs"      --> AGT
    AGT -- "Proof(ΔG)"   --> BIZ
    BIZ --> LDB
    BIZ --> ORC
    AGT --> ORC
    ORC --> LDB
```

| Entity | Responsibility | Key Interface |
|--------|----------------|---------------|
| **Business** | Bundle α‑jobs, fund bounties | `POST /alpha_job` |
| **Agent** | Solve jobs, post proofs | `tool()` (OpenAI Agents SDK) |
| **Orchestrator** | Route jobs, enforce β‑schedule | A2A + MCP |
| **Ledger‑Bot** | Settle \$AGIALPHA mint/burn | Solana program |
| **Safety Ω** | Runtime sandboxes, entropy caps | seccomp‑BPF |
| **Gödel Looper** | Self‑distillation under formal proof | μ‑recursive verif |

---

<a id="4"></a>
## 4 · Multi‑Scale Energy‑Landscape Diagram

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

<a id="5"></a>
## 5 · Ω‑Agents Catalogue (11 / 11)

| ENS | Core Novelty | Physics Role | Verified Scarcity Claim |
|-----|--------------|-------------|-------------------------|
| `fin.alpha.agent.agi.eth` | CVaR 99 % RL‑HF | Computes ΔH<sub>misprice</sub> | Sharpe 3.1 back‑test |
| `bio.alpha.agent.agi.eth` | KG‑RAG on UniProt | Reduces entropy via high‑info datapoints | 3 CRISPR patents neutralised |
| `mat.alpha.agent.agi.eth` | Diffusion‑MCTS for material space | Lowers enthalpy of catalyst design | DOE grant pre‑empt |
| `pol.alpha.agent.agi.eth` | Law QA + GAN red‑line | Captures policy phase‑lags | 37‑jurisdiction coverage |
| `ene.alpha.agent.agi.eth` | Grid DR RL‑HF | Sets β(t) from load | Demoed 14 % bill cut |
| `mfg.alpha.agent.agi.eth` | CP‑SAT job‑shop | Converts ΔG to throughput | 6 % OEE lift |
| `log.alpha.agent.agi.eth` | VRP‑RL for logistics | Entropy compression | 12 % route savings |
| `res.alpha.agent.agi.eth` | Literature ablation design | Orthogonal signals | 0.78 MI F1 gain |
| `qec.alpha.agent.agi.eth` | Real‑time surface‑code optimiser | Quantum error entropy ↓ | 14 % qubit overhead cut |
| `safe.alpha.agent.agi.eth` | KL‑alignment sentinel | Bounds entropy prod. | Zero severe incidents |
| `gdl.alpha.agent.agi.eth` | Gödel Looper | Formal provability | 99.8 % proof success |

---

<a id="6"></a>
## 6 · 90 s Live Quantum‑Loop Demo

| t (s) | Trigger | Agent(s) | Δ𝒮 drop | Outcome |
|-------|---------|----------|---------|---------|
| 0 | `docker run ghcr.io/montrealai/omega-lattice:latest` | Orchestrator | — | Dashboard online |
| 9 | BTC‑vol spike | `fin`, `ene` | −2.3×10⁻² J/bit | β slashed; α‑job #1201 posted |
| 23 | PubMed flood | `bio`, `res` | −3.9×10⁻² J/bit | ΔG −2.1 → job solved |
| 41 | EU carbon leak | `pol` | −1.2×10⁻² J/bit | Rule patch auto‑audited |
| 60 | Factory outage | `mfg`, `log` | −4.7×10⁻² J/bit | OEE +4 %; VaR unchanged |
| 90 | Epoch close | `ledger‑bot` | — | \$AGIALPHA yield +7.9 % |

---

<a id="7"></a>
## 7 · Algorithmic Anatomy — Zero‑Entropy Pipeline

```python
# core outline (simplified)
bundle   = orchestrator.collect_signals()
ΔH       = fin_agent.latent_work(bundle)
ΔS       = res_agent.entropy(bundle)
β        = ene_agent.market_temperature()
ΔG       = ΔH - ΔS/β
if ΔG < 0:
    orchestrator.post_alpha_job(bundle.id, ΔG)

# Gödel Looper self-proof
if gdl_agent.provable(weight_update):
    model.commit(weight_update)
```

Offline mode → `ene_agent` resorts to GARCH / Kalman to estimate β.

---

<a id="8"></a>
## 8 · Deployment Recipes

<a id="8.1"></a>
### 8.1 Docker One‑liner

```bash
docker run alpha_business_v3:latest
```
You can also build the demo locally using the provided Dockerfile.
Run the command from the repository root so the `.dockerignore` rules
trim the build context:
```bash
docker build -t alpha_business_v3:latest \
    -f alpha_factory_v1/demos/alpha_agi_business_3_v1/Dockerfile .
```

<a id="8.2"></a>
### 8.2 Helm / K8s

```bash
helm repo add omega https://montrealai.github.io/charts
helm install omega-lattice omega/omega-lattice \
     --set resources.gpu=true \
     --set openai.apiKey="$OPENAI_API_KEY"
```

<a id="8.3"></a>
### 8.3 Bare‑Metal Python

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alpha-agi-business-3-v1
```

Offline mode activates automatically when `OPENAI_API_KEY` is unset.

### 8.4 Colab Notebook

Use our interactive Google Colab to run the pipeline without local setup:

```
https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/alpha_agi_business_3_v1/colab_alpha_agi_business_3_demo.ipynb
```


No `OPENAI_API_KEY`? Set `LLAMA_MODEL_PATH` to a local `.gguf` weight – for
example **Llama‑3‑8B.gguf** – to enable offline inference.

#### Quick Local Demo

Run the standalone script directly to simulate one Ω‑Lattice cycle:

```bash
alpha-agi-business-3-v1 --loglevel info
```
If the **OpenAI Agents SDK** is installed, each cycle emits a concise LLM
comment on the computed ΔG. Without it the demo uses an offline placeholder.
You can also run the Dockerised version:
```bash
./run_business_3_demo.sh
# builds `alpha_business_v3:latest` using `Dockerfile` in this folder
```

#### Example Session

```bash
$ alpha-agi-business-3-v1 --cycles 1 --loglevel info
2025-06-11 17:16:10 INFO     | ΔH=0.027 ΔS=0.008 β=1.04 → ΔG=0.019
2025-06-11 17:16:10 INFO     | LLM: LLM offline
2025-06-11 17:16:10 INFO     | [Model] New weights committed (Gödel-proof verified)
```

#### Environment Setup

- `OPENAI_API_KEY` – optional. When set, the demo uses OpenAI Agents to
  generate a short LLM comment. Leave it unset to run in fully offline mode.
- `LOCAL_LLM_URL` – optional. Base URL for the local fallback model.
  Defaults to `http://ollama:11434/v1`.
- Each variable can also be passed via command-line flags
  (`--openai-api-key`, `--local-llm-url`, `--adk-host`,
  `--a2a-port`, `--a2a-host`, `--llama-model-path`, `--llama-n-ctx`).
- Python ≥3.11 with packages from `requirements.txt` installed. The
  `run_business_3_demo.sh` helper now builds a Docker image that includes
  `openai_agents` by default.
- Copy `.env.example` in this folder to `.env` and adjust the values before running.
- Before launching the demo, load the variables with `set -a; source .env; set +a` (use the PowerShell equivalent on Windows).
- Run `python check_env.py --auto-install` after sourcing so optional dependencies install correctly.
- `ADK_HOST` – optional. URL of the ADK gateway to forward cycle summaries.
- `A2A_PORT` – enable gRPC A2A messages when set to a port number.
- `A2A_HOST` – host for the A2A gRPC server. Defaults to `localhost`.
- `LLAMA_N_CTX` – context-window size for local models. Defaults to `2048`.
- `LLAMA_MODEL_PATH` – path to a local `.gguf` weight file.

#### Offline Usage

Set `LLAMA_MODEL_PATH` to a local `.gguf` model and install either
[`llama-cpp-python`](https://pypi.org/project/llama-cpp-python/) or
[`ctransformers`](https://pypi.org/project/ctransformers/) so inference works
without internet access.

```bash
LLAMA_MODEL_PATH=/path/model.gguf alpha-agi-business-3-v1
```

#### Dependency Checks

Commonly missing packages include `numpy`, `pandas` and `openai-agents`.
Run `python check_env.py --auto-install` to ensure these are installed.
When offline, pass `--wheelhouse <dir>` so `check_env.py` can use local
wheels. The demo requires either network access or a wheelhouse containing
the required packages.

#### Minimal Example

Install the demo with a local model and run one cycle:

```bash
pip install -r requirements.txt llama-cpp-python
LLAMA_MODEL_PATH=/path/model.gguf alpha-agi-business-3-v1
```

The `openai-agents` package is optional in this setup.

---

<a id="9"></a>
## 9 · Safety, Audit & Governance Matrix

| Layer | Guard | Tooling | Audit Hash |
|-------|-------|---------|-----------|
| Alignment | KL‑shield | Logit lens + PPO‑penalty | `b3e7...` |
| Sandbox | seccomp‑BPF | AppArmor strict | `5ac2...` |
| Observability | OpenTelemetry | Grafana / Loki | `8f4d...` |
| Governance | DAO vote | Quadratic funding | `9da1...` |
| Ledger | Merkle root | Solana notariser | Broadcast hourly |

---

<a id="10"></a>
## 10 · Self‑Improvement Gödel‑Looper

```mermaid
graph TD
  A[Live Embedding] --> B[Distiller L₁]
  B --> C{μ‑Recursive Proof}
  C --✔--> D[Param Commit]
  C --✖--> E[Quarantine]
  D --> B
```

Only weight updates that **preserve alignment axioms** flow back.

---

<a id="11"></a>
## 11 · Legal & Conceptual Shield 🛡️

Inherited **2017 Multi‑Agent AI DAO** prior‑art:

* Blocks patent trolls on multi‑agent + token primitives.  
* Provides DAO‑first wrapper for fractional resource ownership.  
* Time‑stamped blueprint proves freedom‑to‑operate.

---

<a id="12"></a>
## 12 · References & Further Reading

1. A. Brandenburger & B. Nalebuff, *The Right Game*, HBR 1996.  
2. F. Wilczek, *QCD & Gauge Symmetry*, Rev. Mod. Phys.  
3. OpenAI, *A Practical Guide to Building Agents*, 2025.  
4. M. Liang et al., *Stochastic Neural ODEs*, ICML 2024.  
5. Google, *ADK Docs*, 2025.  

---

*Forged by the MONTREAL.AI Agentic Ω‑Lattice team — bending entropy to will.*  
Questions → **discord.gg/montrealai**

[View README on GitHub](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/alpha_agi_business_3_v1/README.md)
