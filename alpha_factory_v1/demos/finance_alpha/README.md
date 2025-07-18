[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.


# Alpha‑Factory Demos 📊

Welcome! These short demos let **anyone – even if you’ve never touched a
terminal – spin up Alpha‑Factory, watch a live trade, and explore the
planner trace‑graph in *under 2 minutes*.

*(Runs with or without an `OPENAI_API_KEY`; the image auto‑falls back to
a local Φ‑2 model.)*

> **⚠️ Disclaimer**: These demos and the included trading strategy are **for
> research and educational purposes only**. They operate on a simulated
> exchange by default and **should not be used with real funds**. Nothing here
> constitutes financial advice. MontrealAI and the maintainers accept no
> liability for losses incurred from using this software.

---

## 🚀 Instant CLI demo

```bash
curl -L https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/main/alpha_factory_v1/demos/finance_alpha/deploy_alpha_factory_demo.sh | bash
```

**What happens**

1. Docker pulls the signed `alphafactory_pro:cpu-slim` image.
2. Container starts with the *BTC / GLD* momentum strategy.
3. The script verifies the API port is free and waits for the health endpoint.
4. The script prints JSON tables for **positions** and **P&L**.
5. You get a link to the live **trace‑graph UI** (`http://localhost:${TRACE_WS_PORT}`).
6. Container stops automatically when you close the terminal.

_No installation beyond Docker, `curl`, and `jq`._

**Customize**
`STRATEGY=my_pair PORT_API=8001 TRACE_WS_PORT=9000 bash deploy_alpha_factory_demo.sh`
runs a different momentum pair and exposes the trace‑graph on an alternate
port.

### .env Setup
Copy [.env.sample](.env.sample) to `.env` next to the script. The demo
automatically sources this file before reading any environment variables so
values defined inside are forwarded to the container.
Each variable can still be overridden directly on the command line:
`PORT_API=8001 TRACE_WS_PORT=9000 bash deploy_alpha_factory_demo.sh`.

| Variable | Purpose | Default |
|----------|---------|---------|
| `FINANCE_STRATEGY` | Momentum pair to trade | `btc_gld` |
| `PORT_API` | REST API port | `8000` |
| `TRACE_WS_PORT` | Trace graph WebSocket port | `8088` |
| `FIN_CYCLE_SECONDS` | Seconds between trade cycles | `60` |
| `FIN_START_BALANCE_USD` | Starting cash in USD | `10000` |
| `FIN_PLANNER_DEPTH` | Planner decision depth | `5` |
| `FIN_PROMETHEUS` | Enable Prometheus metrics | `1` |
| `ALPHA_UNIVERSE` | Tradable symbols | `BTCUSDT,ETHUSDT` |
| `ALPHA_MAX_VAR_USD` | Max value at risk | `50000` |
| `ALPHA_MAX_CVAR_USD` | Max conditional VAR | `75000` |
| `ALPHA_MAX_DD_PCT` | Max drawdown percent | `20` |
| `BINANCE_API_KEY` | Optional Binance key | _empty_ |
| `BINANCE_API_SECRET` | Optional Binance secret | _empty_ |
| `ADK_MESH` | Register on Google ADK mesh | `0` |

Any variable you omit falls back to these safe defaults when the demo starts.

---

## 📒 Interactive notebook demo

> Perfect for analysts who love Pandas or anyone on Google Colab.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/finance_alpha/finance_alpha.ipynb)

The first code cell checks for Docker and installs it automatically when running on Colab. Simply run each cell in order to launch Alpha‑Factory, view positions, and open the live trace‑graph.

### Notebook setup
The notebook begins by verifying Docker. When missing (like on Colab) it installs
Docker with `apt-get` and starts the service. The same cell uses `pip install -q`
to grab any packages not already present. Copy [.env.sample](.env.sample) to `.env`
and adjust `FINANCE_STRATEGY`, `PORT_API` or `TRACE_WS_PORT` to customise the demo.

An additional cell now embeds the trace‑graph UI directly inside the notebook so you can follow the planner's decisions without leaving Colab.

```bash
git clone --depth 1 https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1
jupyter notebook demos/finance_alpha/finance_alpha.ipynb
```

Run the cells to spin up Alpha‑Factory and render positions & P&L as
Pandas tables right inside the notebook. Tweak `STRATEGY` or `PORT_API`
in the parameter cell if you need a custom pair or port.

## 🧩 Programmatic control

The container exposes a standard **OpenAI Agents** endpoint. After the
notebook or CLI demo has launched you can drive the `FinanceAgent`
directly from Python:

```python
from openai.agents import AgentRuntime
rt = AgentRuntime(base_url="http://localhost:8000", api_key=None)
fin = rt.get_agent("FinanceAgent")
print("Alpha signals:", fin.alpha_signals())
```

If the `openai-agents` package is missing the optional
`agent_control.py` script falls back to plain REST calls. When
`ADK_MESH=1` is set the agent registers on the Google ADK mesh for
cross‑agent discovery.

---


## 🛠️ Troubleshooting

| Symptom | Resolution |
|---------|------------|
| **“docker: command not found”** | Install Docker Desktop or Docker Engine |
| Port 8000 already used | The script aborts; re-run with `PORT_API=8001` |
| Corporate proxy blocks image pull | Pull image on a VPN, `docker save` → `docker load` |
| Want GPU speed | `PROFILE=cuda ./scripts/install_alpha_factory_pro.sh --deploy` |

---

## 🔐 Security

* No secrets leave your machine. `.env` (optional) is git‑ignored.  
* Image is **Cosign‑signed**; SBOM available in GitHub Releases.

Enjoy exploring **α‑Factory** – and out‑think the future! 🚀

---

## WARNING: Disclaimer

This demo and the included trading strategy are **for research and
educational purposes only**. They operate on a simulated exchange by
default and **should not be used with real funds**. Nothing here
constitutes financial advice. MontrealAI and the maintainers accept no
liability for losses incurred from using this software.
