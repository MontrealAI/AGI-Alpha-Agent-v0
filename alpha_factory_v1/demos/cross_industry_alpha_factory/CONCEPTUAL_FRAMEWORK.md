[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

<!-- SPDX-License-Identifier: Apache-2.0 -->
# Conceptual Framework – Cross‑Industry Alpha‑Factory

This note summarises how the cross‑industry demo combines multiple domain agents with the OpenAI Agents SDK, Google ADK and the Agent2Agent protocol.

**Note:** This document outlines a conceptual research prototype. It does not represent a production-ready AGI system and should not be taken as financial advice.

## Architecture Overview

```
user -> orchestrator (FastAPI)
            |-- OpenAI Agents bridge (optional)
            |-- ADK gateway (optional)
            |-- Prometheus / Grafana
            `-- industry agents (Finance, Biotech, Climate, Manufacturing, Policy)
                 |-- role agents (planning, research, strategy, market analysis, memory, safety)
```

* **OpenAI Agents SDK** – `openai_agents_bridge.py` exposes discovery tools so any compatible client can request opportunities or list recent logs.
* **Google ADK** – setting `ALPHA_FACTORY_ENABLE_ADK=true` auto‑registers the same tools with the ADK gateway for A2A interoperability.
* **Model Context Protocol (MCP)** – when configured, outbound artifacts are wrapped in MCP envelopes for auditing and policy enforcement.

## Typical Workflow

1. Run `deploy_alpha_factory_cross_industry_demo.sh` or open the Colab notebook to launch the stack.
2. Install `requirements-demo.txt` if you want to use `cross_alpha_discovery_stub.py`
   or the OpenAI Agents bridge.
3. (Optional) Start `openai_agents_bridge.py` to drive the discovery stub via the Agents SDK or ADK.
4. Interact with the REST API or Grafana dashboards to monitor agent activity.
5. The PPO trainer periodically updates each agent using rewards defined in `continual/rubric.json`.

The shipped agents are lightweight but illustrate how more sophisticated domain logic can plug into the orchestrator. Each agent subclass resides in `cross_industry_alpha_factory` and can be swapped for a production implementation.

## Colab Demo

`colab_deploy_alpha_factory_cross_industry_demo.ipynb` installs dependencies, launches containers and exposes the dashboards. Run all cells sequentially—no API key required, though one can be provided for higher‑quality suggestions.

See [`README.md`](README.md) for full instructions.
