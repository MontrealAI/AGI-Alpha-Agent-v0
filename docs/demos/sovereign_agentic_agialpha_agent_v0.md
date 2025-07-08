[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# Sovereign Agentic AGI Alpha Agent Demo

![preview](../sovereign_agentic_agialpha_agent_v0/assets/preview.svg){.demo-preview}

[Launch Demo](../sovereign_agentic_agialpha_agent_v0/index.html){.md-button}

Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.


# Sovereign Agentic AGI Alpha Agent Demo

A minimal showcase of a self-directed agent with token-gated access.
Run `./deploy_sovereign_agentic_agialpha_agent_v0.sh` to build and launch the containerized environment.

## Features
1. Docker-based deployment with one command.
2. Flask web interface served at `http://localhost:5000`.
3. Phantom wallet gating requiring a configurable token balance.
4. Integrated agent chat backed by a language model.
5. Agentic tree search explorer for open-ended strategy discovery.
6. Built-in arithmetic evaluator for the `Calculate` tool (supports +, -, *, /, and power).

```bash
./deploy_sovereign_agentic_agialpha_agent_v0.sh
```

## Usage Tips
- Ensure Docker and docker-compose are installed.
- The script will guide you through optional model configuration.
- Press `Ctrl+C` to stop logs after deployment if desired.

[View README on GitHub](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/sovereign_agentic_agialpha_agent_v0/README.md)
