[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Project Overview

`AGI-Alpha-Agent-v0` explores a meta-agentic framework where agents spawn, evaluate and refine other agents. The codebase ships an offline-friendly demo called **α‑AGI Insight** that runs either locally or via the OpenAI Agents API when keys are provided.

The Insight demo implements a best‑first search over agent rewrite chains. It can forecast disruptive sectors and iteratively improve plans by rewriting itself. When no cloud credentials exist, it falls back to a local Meta-Agentic Tree Search with small sample datasets.

Key capabilities include:

- Modular orchestrator that selects between local and remote runtimes
- Tools to run demos entirely offline using a wheelhouse
- Example agents and a minimal browser client

## Minimal Setup

1. Verify the environment and install Python packages:
   ```bash
   python check_env.py --auto-install
   ```
2. Copy the sample environment:
   ```bash
   cp alpha_factory_v1/.env.sample .env
   ```
3. Launch the default stack:
   ```bash
   ./quickstart.sh
   ```
4. Run the Insight demo:
   ```bash
   alpha-agi-insight-v1 --episodes 5
   ```
   Add API keys in `.env` to enable cloud features; otherwise the demo stays offline.

For a deeper dive, read [quickstart.md](quickstart.md) and the other documents in this folder.
The [Architecture Overview](ARCHITECTURE.md) page summarises how the orchestrator,
agents and memory components interact.
