[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.


<!--
  MuZero Planning Demo
  Alpha‑Factory v1 👁️✨ — Multi‑Agent **AGENTIC α‑AGI**
  Out‑learn · Out‑think · Out‑strategise · Out‑execute
  © 2025 MONTREAL.AI   Apache‑2.0 License
-->

# 🌟 **Mastery Without a Rule‑Book** — watch MuZero think in real time

> “An agent needn’t be told the rules of Go, Chess or cart‑balancing gravity;  
> it can conjure the laws for itself and still prevail.”  
> — *Schrittwieser et al., “Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model”*

This demo distils that 26‑page landmark and its 600‑line reference pseudocode into a **60‑second,
one‑command experience**.  
You’ll see a MuZero‑style agent improvise physics, deploy Monte‑Carlo search,
and **stabilise CartPole** — all inside your browser. No GPU, no PhD required.


## 🚀 Quick Start

Clone the repository and run the helper script. It generates a
`config.env` with safe defaults – edit it to add your `OPENAI_API_KEY` if
you want narrated moves.

Set `HOST_PORT` to expose a different dashboard port,
`MUZERO_ENV_ID` to try other Gymnasium tasks,
and `MUZERO_EPISODES` to adjust episode count.
The helper script warns if the chosen port is already occupied.

```bash
git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1/demos/muzero_planning
./run_muzero_demo.sh
```

The script prints the local URL and, when possible, automatically opens it in
your default browser. Automatic browser opening is currently supported only
on Linux (using `xdg-open`) and macOS (using `open`).

Alternatively run natively:

```bash
pip install -r requirements.txt
python -m alpha_factory_v1.demos.muzero_planning
```
The tests for this demo rely on `torch`, which can take a while to install.
If it's absent, those tests are skipped. For a lightweight check run
```bash
pytest -m 'not e2e'
```

### Optional `openai-agents`

For narrated actions and tool calls, install `openai-agents` version
`>=0.0.17`:

```bash
pip install -U 'openai-agents>=0.0.17'
```

Leaving `OPENAI_API_KEY` empty keeps the demo offline and falls back to
**Ollama ✕ Mixtral** if available.

### Command-line options

You can override the environment, episode count and port directly from the CLI:

```bash
python -m alpha_factory_v1.demos.muzero_planning --env MountainCar-v0 \
       --episodes 5 --port 8888
```


1. **Docker Desktop** builds the container (~45 s on first run).
2. **Open <http://localhost:${HOST_PORT:-7861}>** and press **“▶ Run MuZero”**.
3. Watch the live video feed, reward ticker and optional commentary.

> **Offline by default** – leaving `OPENAI_API_KEY` empty runs the demo
> fully locally with **Ollama ✕ Mixtral**.

This script also registers a small **MuZeroAgent** with the OpenAI Agents runtime.
When `ALPHA_FACTORY_ENABLE_ADK=true` and the optional `google-adk` package is
installed, the agent is automatically exposed via a Google ADK gateway for
cross‑process collaboration.

---

## ✨ Why it matters

| MuZero Pillar | How the demo shows it |
|---------------|-----------------------|
| **Learn the model, not the rules** | Environment dynamics are *unknown*; MiniMu invents them by gradient descent |
| **Plan with MCTS** | 64‑node tree search per action, mirroring Fig. 1 of the paper |
| **Joint reward, value & policy** | Network outputs all three heads; rewards predicted *before* they are observed |
| **Scales to swarms** | A2A wires multiple MiniMu workers into Alpha‑Factory’s agent mesh |

---

## 🛠️ Architecture at a glance

```text
┌────────────┐  observation  ┌────────────┐
│ CartPole 🎢 ├──────────────▶│MiniMu Core │──┐
└────────────┘                └────────────┘  │ hidden
                       ▲            │          ▼
                 reward│     Recurrent model  │
                       │            ▼          │ MCTS
                ┌──────┴──────┐  policy/value  │
                │  MCTS 64×   │◀───────────────┘
                └─────────────┘
```

* **MiniMu** — ≤ 300 LoC, pure‑PyTorch, CPU‑friendly  
* **openai‑agents‑python** — optional LLM overlay for narrative tool‑calling  
* **Gradio** — zero‑install UI & live video  
* **Docker Compose** — reproducible, air‑gapped deployment  

---

## 🎓 Colab (two clicks)

[![Open In Colab][colab-badge]][colab-notebook]

[colab-badge]: https://colab.research.google.com/assets/colab-badge.svg
[colab-notebook]: https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/muzero_planning/colab_muzero_planning.ipynb

Colab spins up the same dashboard via an ngrok tunnel — handy when Docker isn’t.
It installs the tiny MuZero package, runs a quick sanity test and opens a shareable link.
Two extra cells let you tweak the Gym environment, port number and gracefully stop the demo.

---

## 🧩 Eager to tinker?

* **Change the world model**: `demo/minimuzero.py`, class `MiniMuNet`.
* **Crank search depth**: `ROLL_OUTS` constant — 64 ➜ 128 shows clearer MCTS gains.
* **Swap environments**: any Gymnasium classic‑control task runs out‑of‑the‑box.
* **Join the swarm**: launch multiple `docker compose --scale orchestrator=4` and
  watch emergent coordination via A2A.

---

## 🛡️ Security & ops

| Concern | Mitigation |
|---------|------------|
| Secrets | `config.env` volume only, never written to image |
| Network egress | Absent key → offline LLM, no outbound calls |
| Container user | Runs as non‑root UID 1001 |
| Health probes | `/__live` returns **200 OK** for k8s & Docker‑Swarm |

---

## 🆘 30‑second troubleshooting

| Symptom | Remedy |
|---------|--------|
| “Docker not found” | Install via <https://docs.docker.com/get-docker> |
| Port 7861 busy | Edit the `ports:` mapping in `docker-compose.muzero.yml` |
| ARM Mac slow build | Enable “Rosetta for x86/amd64 emulation” in Docker settings |
| Want GPU | Swap base image to `nvidia/cuda:12.4.0-runtime‑ubuntu22.04` & add `--gpus all` |

---

### Development notes

Run `pre-commit run --files alpha_factory_v1/demos/muzero_planning` before committing changes. This mirrors the workflow in [AGENTS.md](../../../AGENTS.md).

---

## 🤝 Credits

* **DeepMind** for the research masterpiece (2020).  
* **Montreal.AI** for distilling it into an afternoon playground.  
* The open‑source community powering every dependency.

> **Alpha‑Factory** — forging intelligence that **out‑learns, out‑thinks, out‑executes**.
