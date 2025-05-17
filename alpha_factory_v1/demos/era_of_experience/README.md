<!--
Era‑of‑Experience Demo
Alpha‑Factory v1 👁️✨ — Multi‑Agent AGENTIC α‑AGI
Out‑learn · Out‑think · Out‑strategise · Out‑execute
© 2025 MONTREAL.AI   MIT License
-->

<h1 align="center">🌌 Era of Experience — Your lifelong‑RL playground</h1>
<p align="center">
  <em>Spin up a self‑improving multi‑agent spine in <strong>one command</strong>.<br>
  Watch it plan, act &amp; learn in real‑time — on your laptop or in the cloud.</em>
</p>

> “AI will eclipse the limits of human‑authored data only when agents <strong>act, observe, and adapt</strong> in the world.” — David Silver &amp; Richard S. Sutton citeturn12file0

This demo distils that manifesto into <strong>Alpha‑Factory v1</strong>.  
Within 60 seconds you will witness an agent <em>rewrite its own playbook</em> every few turns, powered by grounded rewards, long‑range memory and model‑agnostic planning — no dedicated GPU required.

---

## 🚀 Quick‑start (macOS / Windows / Linux)

```bash
git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1/demos/era_of_experience
./run_experience_demo.sh            # ← THAT’S IT
```

1. **Docker Desktop** builds a 300 MB image in ≈ 1 min.  
2. Your browser opens **http://localhost:7860** featuring  
   * live trace‑graph 🪄  
   * reward dashboards 📈  
   * interactive chat / tool console 💬  

> **Offline/Private mode** — leave `OPENAI_API_KEY=` blank in <code>config.env</code>; the stack falls back to <strong>Ollama ✕ Mixtral‑8x7B</strong> and stays air‑gapped.

---

## 🎓 Run on Colab (zero install)

| Notebook | Runtime | Launch |
|----------|---------|--------|
| `colab_era_of_experience.ipynb` | CPU / GPU | <a href="https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/era_of_experience/colab_era_of_experience.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"></a> |

The notebook installs a lean Python stack (&lt; 120 s), exposes Gradio via ngrok and lets you call tools directly from cells.

---

## ✨ What’s new & why it matters

| Silver &amp; Sutton’s pillar | How we realise it |
|---------------------------|--------------------|
| **Streams of experience** | Infinite generator feeding month‑long synthetic logs |
| **Sensor‑motor actions**  | Tools (`web_search`, `plan_meal`, user chat) mutate state |
| **Grounded rewards**      | Plug‑ins: <code>fitness_reward</code>, <code>education_reward</code>, <code>curiosity_reward</code>, … (hot‑reloaded) |
| **Non‑human reasoning**   | Monte‑Carlo Tree Search planner + vector memory — no CoT imitation |

Result: an agent that <strong>evolves faster than you can refresh the page</strong>.

---

## 🛠 Architecture in 60 seconds

```text
┌────────────┐  experience   ┌────────────────┐
│ Generator  │ ────────────▶ │ Orchestrator ⚙ │──┐
└────────────┘               └────────────────┘  │ tool‑calls
        ▲                              ▲        ▼
  reward│                      ┌──────────┐ ┌───────────┐
        │                      │ Planner ♟ │ │  Tools    │
        └──────────────────────┴──────────┴─────────────┘
```

* **OpenAI Agents SDK** — composable tool‑calling, function schemas, memory citeturn1open0  
* **A2A protocol** — future‑proof multi‑agent hand‑offs citeturn2open0  
* **Model Context Protocol** — streaming context for huge traces citeturn3open0  
* **Best‑practice guardrails** from OpenAI *Practical Guide to Building Agents* citeturn7search0  

---

## 🗂 Repo map

| Path / file | What it does |
|-------------|--------------|
| `agent_experience_entrypoint.py` | boots orchestrator + Gradio |
| `run_experience_demo.sh` | 1‑liner prod launcher (health‑gated) |
| `docker-compose.experience.yml` | orchestrator + Ollama services |
| `reward_backends/` | 🍬 Drop‑in reward plug‑ins (auto‑discovery) |
| `simulation/` | Tiny Gym‑like env stubs (road‑map) |
| `colab_era_of_experience.ipynb` | Cloud twin notebook |

---

## 🔌 Extending

* **Add a reward**

```bash
cp reward_backends/template.py reward_backends/my_reward.py
$EDITOR reward_backends/my_reward.py     # implement reward()
```

* **Register a tool**

```python
from openai_agents import Tool

@Tool(name="place_trade", description="Execute an equity order on Alpaca")
async def place_trade(ticker:str, qty:int, side:str="BUY"): ...
```

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

## 🗺 Road‑map

- [ ] Plug‑and‑play Gym‑Retrowrapper for atari‑style sims  
- [ ] Vector‑DB eviction policy learning  
- [ ] Live reward tuning UI  
- [ ] WASM build for edge devices  

---

## 📜 License

MIT. By using this repo you agree to cite **Montreal.AI Alpha‑Factory** if you build on top.

> **Alpha‑Factory** — forging intelligence that *out‑learns, out‑thinks, out‑executes*.
