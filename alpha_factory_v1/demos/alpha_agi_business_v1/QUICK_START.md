[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Quick Start – Alpha‑AGI Business v1 Demo

This short guide summarises how to launch the business demo either locally or in Google Colab.

## Local Launch
1. **Clone the repository**
   ```bash
   git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
   cd AGI-Alpha-Agent-v0/alpha_factory_v1/demos/alpha_agi_business_v1
   ```
2. **Install requirements and check dependencies**
   ```bash
   pip install -r ../../requirements.txt -q
   python ../../check_env.py --auto-install
   ```
3. **Run the demo**
   ```bash
   # one-click launcher (opens docs in your browser)
   python start_alpha_business.py
   # auto-submit the top ranked opportunity once running
   python start_alpha_business.py --submit-best
   # optional: choose a different port
   PORT=9000 python start_alpha_business.py
   ```
   The dashboard is available at [http://localhost:<port>/docs](http://localhost:<port>/docs), where `<port>` is the
     port number used (default is `8000`).
   By default the orchestrator launches stub agents for planning, research,
   strategy, market analysis, memory and safety in addition to the core
   discovery/execution pipeline.

   Alternatively, run the orchestrator directly with:
   ```bash
  python run_business_v1_local.py --bridge --open-ui
  # customise the Agents runtime port
  python run_business_v1_local.py --bridge --runtime-port 6001
  ```
   This starts the Agents bridge and opens the REST docs automatically once the service is ready.

Set `OPENAI_API_KEY` to enable cloud models. Offline mode works automatically when the key is absent.
Set `YFINANCE_SYMBOL` (e.g. `YFINANCE_SYMBOL=SPY`) to fetch a live price when `yfinance` is available.
Set `ALPHA_BEST_ONLY=1` to emit the highest-scoring opportunity from `examples/alpha_opportunities.json`.
Set `ALPHA_TOP_N=5` to publish the top 5 opportunities each cycle.
For air-gapped setups provide pre-downloaded wheels and let `check_env.py` auto-install:
```bash
export WHEELHOUSE=/path/to/wheels
export AUTO_INSTALL_MISSING=1
python start_alpha_business.py
```

### Building a Wheelhouse
Create wheels on a machine with internet access and copy the directory to the
offline host:

```bash
mkdir -p /media/wheels
pip wheel -r ../../requirements.txt -w /media/wheels
pip wheel -r ../../requirements-dev.txt -w /media/wheels
```

Verify dependencies offline:

```bash
python ../../check_env.py --auto-install --wheelhouse /media/wheels
```

See [docs/OFFLINE.md](../../../../docs/OFFLINE.md) for additional tips.

## Colab Notebook
Open [`colab_alpha_agi_business_v1_demo.ipynb`](colab_alpha_agi_business_v1_demo.ipynb) and run all cells. The notebook
  checks requirements, starts the orchestrator, and exposes helper tools via the OpenAI Agents SDK.

## ADK Bridge
To expose the helper agent via Google's Agent Development Kit (ADK), install the
`google-adk` package and enable the bridge:
```bash
pip install google-adk  # optional dependency
ALPHA_FACTORY_ENABLE_ADK=true python openai_agents_bridge.py --host http://localhost:8000
```
The ADK gateway listens on `ALPHA_FACTORY_ADK_PORT` (default `9000`) and supports
Agent-to-Agent (A2A) messaging.
