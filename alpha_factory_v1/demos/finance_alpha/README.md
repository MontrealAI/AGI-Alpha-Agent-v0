# Alpha‑Factory Demos 📊

Welcome! These short demos let **anyone – even if you’ve never touched a
terminal – spin up Alpha‑Factory, watch a live trade, and explore the
planner trace‑graph in *under 2 minutes*.  

*(Runs with or without an `OPENAI_API_KEY`; the image auto‑falls back to
a local Φ‑2 model.)*

---

## 🚀 Instant CLI demo

```bash
curl -L https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/main/alpha_factory_v1/demos/deploy_alpha_factory_demo.sh | bash
```

**What happens**

1. Docker pulls the signed `alphafactory_pro:cpu-slim` image.  
2. Container starts with the *BTC / GLD* momentum strategy.  
3. The script prints JSON tables for **positions** and **P&L**.  
4. You get a link to the live **trace‑graph UI** (`http://localhost:8088`).  
5. Container stops automatically when you close the terminal.

_No installation beyond Docker, `curl`, and `jq`._

---

## 📒 Interactive notebook demo

> Perfect for analysts who love Pandas or anyone on Google Colab.

```bash
git clone --depth 1 https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1
jupyter notebook demos/finance_alpha.ipynb
```

Run the two cells to spin up Alpha‑Factory and render positions & P&L as
Pandas tables right inside the notebook.

---

## 🎬 Preview video / GIF

![Trace demo](../docs/trace_demo.gif)

*(10‑second capture of the planner emitting decisions and tool‑calls.)*

---

## 🛠️ Troubleshooting

| Symptom | Resolution |
|---------|------------|
| **“docker: command not found”** | Install Docker Desktop or Docker Engine |
| Port 8000 already used | Edit the demo script and change `PORT_API=8001` |
| Corporate proxy blocks image pull | Pull image on a VPN, `docker save` → `docker load` |
| Want GPU speed | `PROFILE=cuda ./scripts/install_alpha_factory_pro.sh --deploy` |

---

## 🔐 Security

* No secrets leave your machine. `.env` (optional) is git‑ignored.  
* Image is **Cosign‑signed**; SBOM available in GitHub Releases.

Enjoy exploring **α‑Factory** – and out‑think the future! 🚀
