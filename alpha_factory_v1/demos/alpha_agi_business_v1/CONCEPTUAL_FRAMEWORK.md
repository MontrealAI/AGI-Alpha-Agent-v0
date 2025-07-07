[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Conceptual Framework – Alpha‑AGI Business v1

This short note summarises how the demo fits together and how the provided agents interact using the OpenAI Agents SDK,
  Google ADK and the Agent‑to‑Agent (A2A) protocol.

## Architecture Overview

```
user -> orchestrator (FastAPI)
            |-- OpenAI Agents bridge (optional)
            |-- ADK gateway (optional)
            |-- Gradio dashboard
            `-- core agents (incorporator, discovery, opportunity, execution, risk, compliance, portfolio)
                 |-- role agents (planning, research, strategy, market analysis, memory, safety)
```

* **OpenAI Agents SDK** – `openai_agents_bridge.py` exposes a helper agent so that any OpenAI‑compatible client can
  trigger demo tasks or query recent alpha opportunities.
* **Google ADK** – when `ALPHA_FACTORY_ENABLE_ADK=true` the same tools are automatically registered with the ADK gateway
  for A2A messaging.
* **Model Context Protocol (MCP)** – outbound artefacts may be wrapped in an MCP envelope when `MCP_ENDPOINT` is
  configured. This provides deterministic digests and metadata for auditability.

## Typical Workflow

1. Start the orchestrator with `python start_alpha_business.py` or via Docker.
2. (Optional) Launch the OpenAI Agents bridge: `python openai_agents_bridge.py --host http://localhost:8000`.
3. Interact via the REST API, Gradio dashboard or the Agents SDK.
4. Agents discover opportunities, evaluate risk/compliance and emit portfolio updates. All events are published on the
  internal message bus and can be inspected via `/memory` endpoints.

The agents shipped with the demo are intentionally lightweight to keep resource usage minimal, yet they illustrate how
  to plug in more sophisticated tools. Each agent class in `alpha_agi_business_v1.py` can be extended or replaced with a
  production‑grade implementation.

## Colab Demo

`colab_alpha_agi_business_v1_demo.ipynb` reproduces these steps automatically in a single notebook. It installs
  dependencies, launches the orchestrator and exposes a simple dashboard. Run all cells to experience the workflow
  end‑to‑end even without an `OPENAI_API_KEY`.

## Further Reading

See [`README.md`](README.md) for a full walk‑through and [`PRODUCTION_GUIDE.md`](PRODUCTION_GUIDE.md) for deployment
  tips.
