
<!-- CURRENT-DEMO:START -->
## Current runnable path — 1.4.0

**Mode:** Offline sample. Extracts simple signals from bundled historical CSV samples.

**Prerequisites:** Python 3.11–3.13; source checkout and installed project dependencies.

From the repository root after [installation](../README.md#start-locally):

```bash
python -m alpha_factory_v1.demos run era_of_experience
```

**Expected result:** Yield-curve and supply-chain sample signals with a heuristic selection.

**Scope:** Static historical samples, not current market data or recommendations.

The [catalog](../README.md) explains installation, stopping, backups and recovery.
Browser charts for legacy demos are labeled sample replays. Original research
narratives and advanced scripts below are preserved; they do not expand the tested
scope stated here.
<!-- CURRENT-DEMO:END -->

# Era of Experience

[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.


<!--
Era‑of‑Experience Demo
Alpha‑Factory v1 👁️✨ — Multi‑Agent AGENTIC α‑AGI
Out‑learn · Out‑think · Out‑strategise · Out‑execute
© 2025 MONTREAL.AI   Apache‑2.0 License
-->


<h1 align="center">🌌 Era of Experience — Your lifelong‑RL playground</h1>
<p align="center">
 <em>Spin up a self‑improving multi‑agent spine in <strong>one command</strong>.<br>
 Watch it plan, act &amp; learn in real‑time — on your laptop or in the cloud.</em>
</p>

> “AI will eclipse the limits of human‑authored data only when agents <strong>act, observe, and adapt</strong> in the world.” — David Silver &amp; Richard S. Sutton 

This demo distils that manifesto into <strong>Alpha‑Factory v1</strong>. 
Within 60 seconds you will witness an agent <em>rewrite its own playbook</em> every few turns, powered by grounded rewards, long‑range memory and model‑agnostic planning — no dedicated GPU required.

---

## 🛠 Requirements

- **Docker 24+** with the Compose plugin
- At least **4 CPU cores** (or a modest GPU) for smooth local runs
- **Python 3.11 or 3.12** available as `python3` for environment checks
- Run `python3 ../../../check_env.py --demo era_experience --auto-install` and
  ensure it completes successfully before starting the Docker stack.
- *(Optional)* `OPENAI_API_KEY` for cloud LLMs — leave blank to use the built‑in Mixtral via Ollama
- If running without `run_experience_demo.sh`, install the
  dependencies from `requirements.txt` and ensure the **OpenAI Agents SDK** is pinned at version `0.0.17`:
  ```bash
  pip install -r requirements.txt
  pip install 'openai-agents==0.0.17'
  ```
  `check_env.py` validates the SDK version (see also `alpha_factory_v1/scripts/preflight.py`).
  Then, you can run the script directly with a command like:
  ```bash
  SAMPLE_DATA_DIR=/path/to/csvs python agent_experience_entrypoint.py
  ```

---

## 🚀 Quick‑start (macOS / Windows / Linux)

```bash
git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1/demos/era_of_experience
python3 ../../../check_env.py --demo era_experience --auto-install
chmod +x run_experience_demo.sh
./run_experience_demo.sh      # ← THAT’S IT

```
Ensure the environment check finishes successfully before starting the Docker stack.

Add `--live` to pull in real sensor feeds (wearables, RSS, etc.):

```bash
./run_experience_demo.sh --live
```

1. **Docker Desktop** builds a 300 MB image in ≈ 1 min. 
2. Your browser opens **http://localhost:7860** featuring 
  * live trace‑graph 🪄
  * reward dashboards 📈
  * interactive chat / tool console 💬
  * built‑in alpha detectors (yield curve & supply‑chain) 🔍 — they read from
    `alpha_factory_v1/demos/macro_sentinel/offline_samples/`, and the CSV
snapshots are already included in the repository

> **Offline/Private mode** — leave `OPENAI_API_KEY=` blank in <code>config.env</code>; the stack falls back to <strong>Ollama ✕ Mixtral‑8x7B</strong> and stays air‑gapped.

Customize the dataset directory by exporting `SAMPLE_DATA_DIR` (see
`config.env.sample`) before launching the script:

```bash
SAMPLE_DATA_DIR=/path/to/csvs ./run_experience_demo.sh
```

### 📒 Interactive notebook demo

Run the self-contained Colab notebook to launch the experience demo without any local setup.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/era_of_experience/colab_era_of_experience.ipynb)

## Offline Setup

When running without internet access:

1. Pre-download `wearable_daily.csv` and `edu_progress.csv` from the
   <a href="https://github.com/MontrealAI/demo-assets">demo-assets</a> repository.
2. Place both files in `offline_samples/` before executing
   <code>./run_experience_demo.sh</code> so the orchestrator can read them.
3. Build a wheelhouse on an online machine:
   ```bash
   pip wheel -r requirements.txt -w /media/wheels
   ```
   Copy `/media/wheels` to the offline host.
4. Run the environment check with the wheelhouse:
   ```bash
   python ../../../check_env.py --auto-install --wheelhouse /media/wheels
   ```
5. If the environment check still cannot reach PyPI, set `SKIP_ENV_CHECK=1` to
   skip that step:
   ```bash
   SKIP_ENV_CHECK=1 ./run_experience_demo.sh
   ```

Offline test workflow (after copying `/media/wheels`):

- **Build** the wheel cache on a machine with internet access as shown above.
- **Set** `WHEELHOUSE=/media/wheels` and run:
  ```bash
  python ../../../check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
  ```
- **Run** the unit tests with the wheelhouse available:
  ```bash
  WHEELHOUSE=$WHEELHOUSE pytest -q
  ```


### 🔧 Configure &amp; advanced usage

1. Copy the sample environment file and tweak as desired:

   ```bash
   cp config.env.sample config.env
   $EDITOR config.env      # set OPENAI_API_KEY, MODEL_NAME, PG_PASSWORD, LOGLEVEL, LIVE_FEED, etc.
   ```
You may override the path for built-in offline samples by exporting
`SAMPLE_DATA_DIR` before launching the demo:

```bash
SAMPLE_DATA_DIR=/path/to/csvs ./run_experience_demo.sh
```

Sample CSVs (`wearable_daily.csv`, `edu_progress.csv`) are shipped in
`offline_samples/` so the demo also works without internet access.

2. Enable real-time collectors and metrics with the `--live` flag:

   ```bash
   ./run_experience_demo.sh --live
   ```

   (equivalent to setting `LIVE_FEED=1` in `config.env`)

   The orchestrator automatically switches to offline mode whenever
   `OPENAI_API_KEY` is left empty.

3. Launch Prometheus and Grafana with the `--profile observability` option:

   ```bash
   docker compose --profile observability up
   ```

   Or set `COMPOSE_PROFILES=observability` when running
   `./run_experience_demo.sh`. The Grafana dashboard is available at
   `http://localhost:3001` (password `experience`).

4. Override service endpoints when customizing deployments:

   - `LLM_BASE_URL` changes the Ollama API base URL when `OPENAI_API_KEY` is unset.
   - `PG_PASSWORD` sets the TimescaleDB password for the live-feed logger.

   These keys are documented in `config.env.sample` and can be exported on the
   command line:

   ```bash
   LLM_BASE_URL=http://my-ollama:11434/v1 PG_PASSWORD=secret \
       ./run_experience_demo.sh
   ```

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | _(empty)_ | API key for hosted models. Offline mode is used when empty. |
| `MODEL_NAME` | `gpt-4o-mini` | Planner model name. |
| `TEMPERATURE` | `0.40` | LLM sampling temperature. |
| `MAX_TOKENS` | `4096` | Token limit for reasoning and tool calls. |
| `OLLAMA_MODEL` | `mixtral:instruct` | Offline fallback model pulled by Ollama. |
| `LLM_BASE_URL` | `http://ollama:11434/v1` | Override the local LLM endpoint. |
| `STREAM_RATE_HZ` | `1` | Synthetic experience events per second. |
| `LIVE_FEED` | `0` | Set to `1` to mix in real sensor/web data. |
| `FITNESS_REWARD_WEIGHT` | `0.50` | Weight on `fitness_reward()`. |
| `EDUCATION_REWARD_WEIGHT` | `0.50` | Weight on `education_reward()`. |
| `PG_PASSWORD` | `alpha` | TimescaleDB password for the live-feed logger. |
| `LOGLEVEL` | `INFO` | Logging verbosity. |
| `PORT` | `7860` | Web UI port. |
| `CONNECTIVITY_TEST_URL` | `https://example.com` | Probe used to detect internet access. |

---

## 🎓 Run on Colab (zero install)

| Notebook | Runtime | Launch |
|----------|---------|--------|
| `colab_era_of_experience.ipynb` | CPU / GPU | <a href="https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/era_of_experience/colab_era_of_experience.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"></a> |

The notebook installs a lean Python stack (&lt; 120 s), exposes Gradio via ngrok and lets you call tools directly from cells. It automatically verifies the runtime with `check_env.py` and runs the unit tests so you can confirm everything works. Example cells illustrate detecting "alpha" opportunities using the offline yield curve **and** a toy supply‑chain flow snapshot.

---

## ✨ What’s new & why it matters

| Silver &amp; Sutton’s pillar | How we realise it |
|---------------------------|--------------------|
| **Streams of experience** | Infinite generator feeding month‑long synthetic logs |
| **Sensor‑motor actions** | Tools (`web_search`, `plan_meal`, user chat) mutate state |
| **Grounded rewards**   | Plug‑ins: <code>fitness_reward</code>, <code>education_reward</code>, <code>curiosity_reward</code>, … (hot‑reloaded) |
| **Non‑human reasoning**  | Monte‑Carlo Tree Search planner + vector memory — no CoT imitation |

Result: an agent that <strong>evolves faster than you can refresh the page</strong>.

---

## 🛠 Architecture in 60 seconds

```text
┌────────────┐ experience  ┌────────────────┐
│ Generator │ ────────────▶ │ Orchestrator ⚙ │──┐
└────────────┘        └────────────────┘ │ tool‑calls
    ▲               ▲    ▼
 reward│           ┌──────────┐ ┌───────────┐
    │           │ Planner ♟ │ │ Tools  │
    └──────────────────────┴──────────┴─────────────┘
```

* **OpenAI Agents SDK** — composable tool‑calling, function schemas, memory  
* **A2A protocol** — future‑proof multi‑agent hand‑offs  
* **Model Context Protocol** — streaming context for huge traces  
* **Best‑practice guardrails** from OpenAI *Practical Guide to Building Agents*  

---

## 🗂 Repo map

| Path / file | What it does |
|-------------|--------------|
| `agent_experience_entrypoint.py` | boots orchestrator + Gradio |
| `run_experience_demo.sh` | 1‑liner prod launcher (health‑gated) |
| `docker-compose.experience.yml` | orchestrator + Ollama services |
| `reward_backends/` | 🍬 Drop‑in reward plug‑ins (auto‑discovery) |
| `simulation/` | Tiny Gym‑like env stubs (ready to extend) |
| `stub_agents.py` | Minimal agent classes for OpenAI SDK & ADK workflows |
| `colab_era_of_experience.ipynb` | Cloud twin notebook |
| `alpha_report.py` | CLI helper printing current offline alpha signals |

Run it with local CSVs:

```bash
python alpha_report.py --data-dir path/to/offline_samples
```

---

## 🔌 Extending

* **Add a reward**

```bash
cp reward_backends/template.py reward_backends/my_reward.py
$EDITOR reward_backends/my_reward.py   # implement reward()
```

* **Register a tool**

```python
from openai_agents import Tool

@Tool(name="place_trade", description="Execute an equity order on Alpaca")
async def place_trade(ticker:str, qty:int, side:str="BUY"): ...
```

This demo ships with a minimal example:

```python
@Tool("detect_yield_curve_alpha", "Assess yield curve inversion using offline data.")
async def detect_yield_curve_alpha_tool():
    return {"alpha": detect_yield_curve_alpha()}

@Tool("detect_supply_chain_alpha", "Check for potential supply-chain disruptions using offline data.")
async def detect_supply_chain_alpha_tool(threshold: float = 50.0):
    return {"alpha": detect_supply_chain_alpha(threshold)}
```

* **Run in simulation**

The `simulation` package ships with `SimpleExperienceEnv`, a tiny
Gym-like environment for experimenting with offline loops:

```python
from alpha_factory_v1.demos.era_of_experience.simulation import SimpleExperienceEnv

env = SimpleExperienceEnv()
state = env.reset()
for _ in range(3):
    state, reward, done, info = env.step("act")
    print(state, reward)
```

* **Prototype a custom agent**

  `stub_agents.py` contains minimal classes
  (`ExperienceAgent`, `FederatedExperienceAgent`) illustrating how to build
  on the OpenAI SDK and Google ADK respectively.


* **Cluster‑scale**

```bash
docker compose --profile gpu --scale orchestrator=4 up --build
```

Shared Redis memory + A2A = emergent cooperation.

---

## 🛡 Security & Compliance

* Non‑root container; no Docker‑in‑Docker. 
* Secrets isolated in `config.env`, never baked into images. 
* Opt‑in telemetry only; default is **OFF**. 
* `/__live` returns **200 OK** for K8s, Traefik, Nginx health probes. 
* <code>safety_compliance_reward.py</code> penalises violations and rewards self‑correction.

---

## 📈 Benchmarks (o3‑mini, 8×CPU vCPU)

| Metric | 1‑agent | 4‑agent swarm |
|--------|---------|---------------|
| Decisions / min | 38 | 124 |
| Avg reward | 0.43 | 0.57 |
| Latency P50 | 520 ms | 730 ms |

*(Synthetic workload; see `benchmarks/` for scripts)*

---

## ✅ Tests

Verify the demo locally with Python's builtin test runner:

```bash
python -m unittest tests.test_era_experience
```

Run `python ../../../check_env.py --demo era_experience --auto-install` first and make sure it
completes successfully before running any tests. Tests will fail if core
packages such as `numpy` are missing, in addition to optional ones like
`pytest` and `openai-agents`.

---

## 🗺 Road‑map

- [ ] Plug‑and‑play Gym‑Retrowrapper for atari‑style sims 
- [ ] Vector‑DB eviction policy learning 
- [ ] Live reward tuning UI 
- [ ] WASM build for edge devices 

---

## 📜 License

Apache 2.0. By using this repo you agree to cite **Montreal.AI Alpha‑Factory** if you build on top.

> **Alpha‑Factory** — forging intelligence that *out‑learns, out‑thinks, out‑executes*.

---

**Contributor checklist** — run `pre-commit`, `python ../../../check_env.py --auto-install`, and `pytest -q` before submitting any changes. See [AGENTS.md](../../../AGENTS.md) for the full contributor guide.
