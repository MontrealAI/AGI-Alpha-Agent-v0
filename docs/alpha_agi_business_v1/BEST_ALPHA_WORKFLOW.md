[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Best Alpha Opportunity Workflow

This short note summarises the highest ranked alpha signal included with the demo and how to act on it using the
  provided multi‑agent stack. The goal is to show a concrete starting point for experimentation.

## 1. Identified Alpha

Using `examples/find_best_alpha.py` (run from the root of the project directory) the top opportunity from
  `examples/alpha_opportunities.json` is:

```
gene therapy patent undervalued by market
```
with a score of **88**.

## 2. Launch the Orchestrator

Run the one‑click launcher which automatically installs any missing dependencies and starts the local orchestrator with
  the OpenAI Agents bridge enabled:

```bash
python start_alpha_business.py
```

Open the REST docs at `http://localhost:8000/docs` to verify the service is running. The core agents (discovery,
  opportunity, execution, risk, compliance, portfolio) start automatically.

## 3. Submit the Opportunity

Send a job definition to the orchestrator so the agents can evaluate and act on it. Replace `<PORT>` if you changed the
  default 8000:

```bash
curl -X POST http://localhost:<PORT>/agent/alpha_execution/trigger \
     -H 'Content-Type: application/json' \
     -d '{"alpha": "gene therapy patent undervalued by market", "score": 88}'
```

Or trigger it via the OpenAI Agents bridge using the ``trigger_best_alpha``
helper:

```bash
curl -X POST http://localhost:5001/v1/agents/business_helper/invoke \
     -H 'Content-Type: application/json' \
     -d '{"action": "best_alpha"}'
```

The execution agent will process the input and propagate tasks to downstream agents such as risk and compliance.

## 4. Monitor Progress

Use the built‑in dashboard or the OpenAI Agents bridge to query recent alpha items and check agent status:

```bash
python openai_agents_bridge.py --host http://localhost:<PORT> --open-ui
```

Replace `<PORT>` with the OpenAI Agents bridge port (default is 5001). Once the bridge is running, open
  `http://localhost:5001/v1/agents` to interact via the OpenAI Agents SDK. The `recent_alpha` and `fetch_logs` tools
  provide a quick view of system activity.

---

This workflow demonstrates how to take a discovered alpha signal and run it through the demo's multi‑agent pipeline. The
  components are intentionally lightweight so you can extend them with domain‑specific logic or connect them to external
  data sources.
