[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

<!-- CURRENT-DEMO:START -->
## Current runnable path — 1.5.0

**Mode:** Deployment template. Preserves the original combined planning and model-integration concept.

**Prerequisites:** The original installer requires obsolete optional packages and is not a validated install path.

From the repository root after [installation](../README.md#start-locally):

```bash
python -m alpha_factory_v1.demos show muzeromctsllmagent_v0
```

**Expected result:** Open the browser illustration. Read the source before using the preserved installer.

**Scope:** Use muzero_planning for maintained planning and the Agent operator for supported model/identity controls; original assets remain.

The [catalog](../README.md) explains installation, stopping, backups and recovery.
Browser charts for legacy demos are labeled sample replays. Original research
narratives and advanced scripts below are preserved; they do not expand the tested
scope stated here.
<!-- CURRENT-DEMO:END -->

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.


# MuZero MCTS LLM Agent Demo


This folder contains a prototype integration of a Monte Carlo Tree Search (MCTS) agent with language model guidance. Run `install_and_launch.sh` to build the environment and start the demo in your browser.

## Quick Start
1. Ensure Python 3.9+ is installed.
2. Execute `./install_and_launch.sh`.
3. Visit `http://localhost:8000` to interact with the agent.
4. Follow on-screen instructions to explore planning outputs.

```bash
./install_and_launch.sh
```

## Notes
- Requires approximately 2GB RAM and basic Docker support.
- Provided for research purposes only; not a production trading system.
