<!--
  MuZero Planning Demo
  Alpha‑Factory v1 👁️✨ — Multi‑Agent **AGENTIC α‑AGI**
  Out‑learn · Out‑think · Out‑strategise · Out‑execute
  © 2025 MONTREAL.AI   MIT License
-->

# 🌟 **Mastery Without a Rule‑Book** — watch MuZero think in real time

> “An agent needn’t be told the rules of Go, Chess or cart‑balancing gravity;  
> it can conjure the laws for itself and still prevail.”  
> — *Schrittwieser et al., “Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model”*

This demo distils that 26‑page landmark and its 600‑line reference pseudocode into a **60‑second,
one‑command experience**.  
You’ll see a MuZero‑style agent improvise physics, deploy Monte‑Carlo search,
and **stabilise CartPole** — all inside your browser. No GPU, no PhD required.

---

## 🚀 Run it on your laptop

```bash
git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0
bash alpha_factory_v1/demos/muzero_planning/run_muzero_demo.sh
```

1. **Docker Desktop** compiles the container (≈ 45 s cold start).  
2. Open **http://localhost:7861** → click **“▶ Run MuZero”**.  
3. Enjoy the live video feed, reward ticker, and optional “explain_move” prose.

> **No OpenAI key?** Leave `OPENAI_API_KEY` blank in `config.env`.  
> The stack spins up **Ollama ✕ Mixtral** and stays 100 % offline.

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

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/muzero_planning/colab_muzero_planning.ipynb)

Colab spins up the same dashboard via an ngrok tunnel — handy when Docker isn’t.

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

## 🤝 Credits

* **DeepMind** for the research masterpiece (2020).  
* **Montreal.AI** for distilling it into an afternoon playground.  
* The open‑source community powering every dependency.

> **Alpha‑Factory** — forging intelligence that **out‑learns, out‑thinks, out‑executes**.
