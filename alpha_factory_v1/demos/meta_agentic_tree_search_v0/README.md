[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

<!-- CURRENT-DEMO:START -->
## Current runnable path — 1.5.0

**Mode:** Offline simulation. Searches a small integer policy landscape.

**Prerequisites:** Python 3.11–3.13; source checkout and installed project dependencies.

From the repository root after [installation](../README.md#start-locally):

```bash
python -m alpha_factory_v1.demos run meta_agentic_tree_search_v0
```

**Expected result:** Three logged search episodes and the best candidate.

**Scope:** Toy reward landscape; optional model rewriters do not establish trading alpha.

The [catalog](../README.md) explains installation, stopping, backups and recovery.
Browser charts for legacy demos are labeled sample replays. Original research
narratives and advanced scripts below are preserved; they do not expand the tested
scope stated here.
<!-- CURRENT-DEMO:END -->

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.


# Meta‑Agentic Tree Search (MATS) Demo — v0


[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/meta_agentic_tree_search_v0/colab_meta_agentic_tree_search.ipynb)

**Abstract:** We pioneer **Meta-Agentic Tree Search (MATS)**, a novel framework for autonomous multi-agent decision optimization in complex strategic domains. MATS enables intelligent agents to collaboratively navigate and optimize high-dimensional strategic search spaces through **recursive agent-to-agent interactions**. In this **second-order agentic** scheme, each agent in the system iteratively refines the intermediate strategies proposed by other agents, yielding a self-improving decision-making process. This recursive optimization mechanism systematically uncovers latent inefficiencies and unexploited opportunities that static or single-agent approaches often overlook.

> **Status:** Experimental · Proof‑of‑Concept · Alpha  
> **Location:** `alpha_factory_v1/demos/meta_agentic_tree_search_v0`  
> **Goal:** Showcase how recursive agent‑to‑agent rewrites — navigated with a best‑first tree policy — can rapidly surface high‑value trading policies that exploit AGI‑driven discontinuities (“AGI Alpha”).

## 1 Why this demo exists
Financial edges sourced from AGI inflection points decay in hours or days. Classical research pipelines are too slow.  
MATS compresses the idea‑to‑capital cycle by letting agents continuously rewrite each other while a Monte‑Carlo tree search focuses compute on the most promising rewrite trajectories.

## 2 High‑level picture
```
root population
      │  meta‑rewrite
      ▼
  ┌─────────────┐   tree policy   ┌───────────────┐
  │  Node k     ├────────────────►│  Node k+1     │
  └─────────────┘                 └───────────────┘
```
Each edge = “one agent improves another”; backpropagation = “which rewrite path maximises risk‑adjusted α”.

## 3 Formal definition
*(verbatim from specification for precision)*  

> **Meta‑Agentic Tree Search (MATS)**  
> Let **E** be a partially‑observable, stochastic environment parameterised by state vector *s* and reward function *R*.  
> Let **𝒜₀** = {a₁,…,aₙ} be a population of base agents, each with policy πᵢ(·|θᵢ).  
> **Meta‑agents** are higher-order policies **Π : (𝒜₀, 𝒮, 𝒭) → 𝒜₀′** that rewrite or re‑parameterise base agents to maximise a meta‑objective **J**.  
> A search node **v** is the tuple (𝒜ₖ, Σₖ) where 𝒜ₖ is the current agent pool after *k* rewrites and Σₖ their cumulative performance statistics.  
> The tree policy **T** selects the next node via a best‑first acquisition criterion (e.g. UCB over expected α).  
> Terminal nodes are reached when Δα < ε or depth ≥ d\*.  
> **Output**: argmax₍ᵥ∈𝒱_leaf₎ J(v).

## 4 Minimal algorithm (reference implementation)
```python
def MATS(root_agents, env, horizon_days):
    tree = Tree(Node(root_agents))
    while resources_left():
        node = tree.select(best_first)                       # ← UCB / Thompson
        improved = meta_rewrite(node.agents, env)           # ← gradient, evo, code‑gen
        reward = rollouts(improved, env, horizon_days)      # ← risk‑adj α
        child = Node(improved, reward)
        tree.add_child(node, child)
        tree.backprop(child)
    return tree.best_leaf().agents
```

### Design knobs
| Component          | Options (demo default) |
|--------------------|------------------------|
| `best_first`       | UCB1, TS, ε‑greedy (UCB1) |
| `meta_rewrite`     | PPO fine‑tune, CMA‑ES, GPT‑4 code‑gen (PPO) |
| Reward             | IRR, CumPnL/√Var, Sharpe (IRR) |
| Environment        | Toy number-line env (default), limit‑order‑book sim, OpenAI Gym trading env |

### 4.1 · OpenAI/ADK rewrite option
When the optional `openai-agents` and `google-adk` packages are installed the
demo can leverage a tiny ``RewriterAgent`` built with the OpenAI Agents SDK
together with the A2A protocol to generate candidate policies.  The agent is
instantiated directly from :func:`openai_rewrite` and executed once per tree
step. Enable this behaviour with:

```bash
python run_demo.py --rewriter openai --episodes 500 --model gpt-4o
```
The script automatically falls back to the offline rewriter when the
dependencies are unavailable so the notebook remains runnable anywhere.

When the optional `openai` package is also present, `openai_rewrite` uses
`OpenAI().chat.completions.create` to refine candidate integer policies.  Supply an
`OPENAI_API_KEY` environment variable to activate this behaviour.  Without a
key or in fully offline environments the routine simply increments the
proposed policy elements so the rest of the demo keeps working.  You can
override the model used by setting ``OPENAI_MODEL`` (defaults to ``gpt-4o``).
Output from the model is processed via the ``_parse_numbers`` helper which
extracts integers from free‑form text and validates their length so the search
loop remains stable even when the LLM response contains extra commentary. When
the output is malformed or incomplete the helper simply increments the previous
policy as a safe fallback. The rewrite routine executes the LLM call via a small
synchronous helper so it functions both with and without an active event loop.

### 4.2 · Anthropic rewrite option
When the optional `anthropic` package is installed and an `ANTHROPIC_API_KEY`
environment variable is configured the demo can use Claude models to refine
candidate policies via the ``anthropic_rewrite`` helper. Enable this behaviour
with:

```bash
python run_demo.py --rewriter anthropic --episodes 500 --model claude-3-opus-20240229
```
As with the OpenAI path the call automatically falls back to the offline
rewriter whenever dependencies or API keys are missing so the notebook remains
fully reproducible.

### 4.3 · OpenAI Agents bridge
The `openai_agents_bridge.py` script exposes the search loop via the
**OpenAI Agents SDK** and optionally the **Google ADK** federation layer. Launch
the bridge to control the demo through API calls or the Agents runtime UI:

```bash
mats-bridge --help
```
Sample output:
```text
usage: mats-bridge [-h] [--episodes EPISODES] [--target TARGET]
                   [--model MODEL] [--rewriter {random,openai,anthropic}]
                   [--market-data MARKET_DATA] [--enable-adk] [--verify-env]

OpenAI Agents bridge for MATS

options:
  -h, --help            show this help message and exit
  --episodes EPISODES   Search episodes when offline
  --target TARGET       Target integer when offline
  --model MODEL         Optional model override
  --rewriter {random,openai,anthropic}
                        Rewrite strategy to use
  --market-data MARKET_DATA
                        CSV file with comma-separated integers for
                        LiveBrokerEnv
  --enable-adk          Enable the Google ADK gateway for remote control
  --verify-env          Check runtime dependencies before launching
```
Run a quick environment check with ``--verify-env`` if desired:
```bash
mats-bridge --verify-env --episodes 3 --target 4 --model gpt-4o
```
Typical invocation:
```bash
mats-bridge --verify-env --enable-adk --episodes 3 --target 4 --model gpt-4o
```
The bridge exposes a small :func:`verify_env` helper that performs the same
sanity check programmatically. Call it from Python or rely on the command
above. If the `openai_agents` package or API keys are missing the bridge
automatically falls back to running the search loop locally so the notebook
remains reproducible anywhere. When running offline you can still invoke
`run_search` directly to verify the helper logic:

```bash
mats-bridge --episodes 3 --target 4 --model gpt-4o
python -m alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge --episodes 3 --target 4
```
Enable the optional ADK gateway with ``--enable-adk`` (or set
``ALPHA_FACTORY_ENABLE_ADK=true``) to expose the agent over the A2A protocol.
This prints a short completion summary after executing the demo loop.

### 4.4 · Google ADK Integration
Install the ``google-adk`` package to communicate over the A2A protocol:

```bash
pip install google-adk
```

Set ``ALPHA_FACTORY_ENABLE_ADK=true`` or pass ``--enable-adk`` to enable the gateway.
The ADK layer is optional so the demo still runs completely offline.

## 5 Quick start
```bash
git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1/demos/meta_agentic_tree_search_v0
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock         # install pinned dependencies
python ../../../check_env.py --auto-install  # fetch optional extras
python run_demo.py --verify-env          # optional sanity check
python run_demo.py --config configs/default.yaml --episodes 500 --target 5 --seed 42 --model gpt-4o
# or equivalently
python -m alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo --episodes 500 --target 5
# installed scripts
mats-demo --episodes 5
mats-bridge --episodes 3
```
`run_demo.py` prints a per‑episode scoreboard.  Pass `--log-dir logs` to save a
`scores.csv` file for further analysis. A ready‑to‑run Colab notebook is also
provided as `colab_meta_agentic_tree_search.ipynb`.

## Offline Setup
When installing without network access, first build wheels on a
machine with connectivity:

```bash
pip wheel -r requirements.txt -w /tmp/wheels
```

Copy `/tmp/wheels` to the offline machine and install packages from the
local wheelhouse:

```bash
WHEELHOUSE=/tmp/wheels pip install -r requirements.txt
```

The repository's setup script automatically uses a `wheels/` directory
in the project root when present, so placing your pre-built wheels there
also works. Set `WHEELHOUSE=/tmp/wheels` (or `$(pwd)/wheels`) before running
`../../../check_env.py --auto-install` or `pytest` so the command installs from
the local cache. See
[docs/OFFLINE_SETUP.md](../../../docs/OFFLINE_SETUP.md) for a summary.

To regenerate the pinned lock file after editing `requirements.txt`, install
[`pip-tools`](https://pypi.org/project/pip-tools/) and run:

```bash
pip install pip-tools          # one-time setup
pip-compile --generate-hashes -o requirements.lock requirements.txt
```

Run `python scripts/verify_mats_requirements_lock.py` to confirm the lock file
matches `requirements.txt`.

### Environment variables
The demo consults a few environment variables when choosing a rewrite strategy
and model. Set these if you do not pass ``--rewriter`` or ``--model`` on the
command line:

- ``MATS_REWRITER`` – set in ``.env`` to force the rewrite engine to ``random``,
  ``openai`` or ``anthropic``.
- ``OPENAI_MODEL`` – default model used by the OpenAI rewriter and bridge
  (defaults to ``gpt-4o``).
- ``ANTHROPIC_MODEL`` – model name for the Anthropic rewriter
  (defaults to ``claude-3-opus-20240229``).
- ``MCP_ENDPOINT`` – optional URL for Model Context Protocol logging.
- ``MCP_TIMEOUT_SEC`` – timeout in seconds for MCP requests (defaults to ``10``).

Setting ``MCP_ENDPOINT`` enables prompt logging via the Model Context Protocol
for later audit.

If ``MATS_REWRITER`` is unset the script picks ``openai`` when an
``OPENAI_API_KEY`` is present or ``anthropic`` when ``ANTHROPIC_API_KEY`` is
configured, falling back to the offline rewriter otherwise.

### Notebook quick start
1. Click the “Open In Colab” badge at the top of this document.
2. Execute the first cell to clone the repository and install dependencies.
3. Optionally provide `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` values in the second cell. Leave the variable unset if you don't have a key.
4. Run the demo cell to launch the search loop.
5. Optionally invoke `openai_agents_bridge.py --verify-env` from a new cell to confirm your runtime.

Add ``--enable-adk`` to the command above to start the optional ADK
gateway for remote control via the A2A protocol.
The default environment is a simple number‑line task defined in `mats/env.py` where each agent must approach a target integer. Pass `--target 7` (for example) to experiment with different goals.
Use `--seed 42` to reproduce a specific search trajectory.

> **Tip:** Replay real tick data with:
> `python run_demo.py --market-data my_feed.csv`

## 6 Repository layout
```
meta_agentic_tree_search_v0/
├── README.md                ← you are here
├── run_demo.py              ← entry‑point wrapper
├── mats/                    ← core library
│   ├── tree.py
│   ├── meta_rewrite.py
│   ├── evaluators.py
│   └── env.py
└── configs/
    └── default.yaml
```

## 7 Walk‑through of the demo episode
1. Bootstrap 4 vanilla PPO agents trading a synthetic GPU‑demand proxy.  
2. Tree search explores ~300 rewrite paths within the 30‑second budget.  
3. Best leaf realises a 3.1 % IRR over a 10‑day horizon (toy setting).  
4. Log files + tensorboard summaries land in `./logs/`.

## 8 Extending this prototype
| Goal                           | Hook/function                     |
|--------------------------------|-----------------------------------|
| Plug‑in real execution broker  | `mats.env.LiveBrokerEnv`          |
| Swap rewrite strategy          | Subclass `MetaRewriter`           |
| Use distributed workers        | `ray tune` launcher               |
| Custom tree policy             | Implement `acquire()` in `Tree`   |
| Custom output parser           | `_parse_numbers` helper           |

`LiveBrokerEnv` is a minimal subclass of :class:`NumberLineEnv` that accepts a
market data sequence. It serves as a stub for wiring real brokerage feeds into
the search loop while keeping the demo runnable completely offline.

## 9 Safety & governance guard‑rails
* Sandboxed code‑gen (`firejail + seccomp + tmpfs`)  
* Hard VaR budget enforced by `RiskGovernor`  
* CI tests for deterministic replay to detect edge drift  

## 10 References & further reading
* **Language‑Agent Tree Search**, Jiang et al., ACL 2024  
* **Best‑First Agentic Tree Search**, Li & Karim, NeurIPS 2024 workshop  
* **Self‑Referential Improvement in RL**, Müller et al., arXiv 2025  

## 11 License
Apache 2.0 – see `LICENSE`.

---
*This README belongs to the AGI‑Alpha‑Agent project.*
