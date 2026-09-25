[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

# AGIALPHA demo catalog

**New in 1.5.0:** [Launch the Ascension Lab](https://montrealai.github.io/AGI-Alpha-Agent-v0/ascension/).
Explore the white paper end to end with three editable flagship scenarios, encrypted Nova-Seed recovery,
computed FusionPlans, exact modeled funding/settlement and an interactive governance observatory.
The [implementation guide](../../../docs/agent/WHITEPAPER_IMPLEMENTATION.md) maps each mechanism to code,
test evidence and its limits. The original catalog below remains available in full.

Start with the [browser gallery](https://montrealai.github.io/AGI-Alpha-Agent-v0/).
It includes **24 demos and 2 reference/support entries**. Most legacy browser charts
replay bundled illustrative traces; Insight v1 additionally supports real local
GPT-2 inference. Each guide states exactly what runs and what is simulated.

For the maintained agent, identity, operator controls and canonical Ethereum
$AGIALPHA receipt flow, use the [Agent guide](../../../docs/agent/OPERATIONS.md).
Legacy Solana concepts remain preserved as historical deployment templates.

## Start locally

Use Python 3.11–3.13 from a source checkout. In an activated virtual environment:

```bash
python -m pip install --require-hashes -r requirements-agent.lock
python -m pip install --no-deps -e .
python -m alpha_factory_v1.demos list
python -m alpha_factory_v1.demos show solving_agi_governance
python -m alpha_factory_v1.demos run solving_agi_governance
```

Run these setup commands from the repository root. Optional training, UI and model
packages are listed per demo; the launcher never installs packages automatically.
`show` does not start a service or contact a provider. `run` prints its mode,
command, expected result and output directory before executing it. Finite examples
exit by themselves. Stop services with **Ctrl+C**.

Local state goes to `demo-runs/DEMO_NAME/`; select another directory with
`run DEMO_NAME --output-dir PATH`. Copy that directory to back it up. To restart
fresh without losing a run, choose a new directory. SQLite lineage runs append;
no existing run is deleted. Model caches remain separate.

## Choose an example

| Demo | Current mode | What it does |
|---|---|---|
| [AI-GA meta-evolution](aiga_meta_evolution/README.md) | Research training | Evolves small networks in a curriculum environment. |
| [Business v2](alpha_agi_business_2_v1/README.md) | Local service | Runs planning, research and optional commentary agents in the legacy orchestrator. |
| [Business v3](alpha_agi_business_3_v1/README.md) | Simulation | Runs a bounded multi-agent business cycle with local fallback results. |
| [Business v1](alpha_agi_business_v1/README.md) | Offline sample | Ranks bundled business opportunities; service agents publish illustrative business events. |
| [Insight v0](alpha_agi_insight_v0/README.md) | Offline simulation | Searches a toy sector-scoring landscape. |
| [Insight v1](alpha_agi_insight_v1/README.md) | Browser + simulation | Explores scenarios and Pareto search; optional browser GPT-2 performs real local text completion. |
| [Marketplace](alpha_agi_marketplace_v1/README.md) | Local API client | Validates a bundled job and can submit it to a configured legacy orchestrator. |
| [ASI world model](alpha_asi_world_model/README.md) | Research training | Explores generated grid worlds using a small learner and local API. |
| [Super Planner](alpha_super_planner_v1/README.md) | Interface illustration | Shows the stages and progress display of a planning interface. |
| [Cross-industry discovery](cross_industry_alpha_factory/README.md) | Offline sample | Selects reproducible examples from the bundled opportunity catalog. |
| [Era of Experience](era_of_experience/README.md) | Offline sample | Extracts simple signals from bundled historical CSV samples. |
| [Finance Alpha](finance_alpha/README.md) | Deployment example | Provides paper-market agent and legacy service integration examples. |
| [GPT-2 CLI](gpt2_small_cli/README.md) | Local model | Generates text with the actual GPT-2 124M model. |
| [Macro Sentinel](macro_sentinel/README.md) | Offline simulation | Computes Monte Carlo risk metrics from bundled macro samples. |
| [Meta-Agentic v1](meta_agentic_agi/README.md) | Synthetic evaluation | Runs provider-driven code proposals, synthetic fitness and SQLite lineage. |
| [Meta-Agentic v2](meta_agentic_agi_v2/README.md) | Synthetic evaluation | Runs provider-driven code proposals, synthetic fitness and SQLite lineage. |
| [Meta-Agentic v3](meta_agentic_agi_v3/README.md) | Identity curriculum | Exercises proposal, validation, scoring and persistent lineage on a fixed identity task. |
| [Meta-Agentic tree search](meta_agentic_tree_search_v0/README.md) | Offline simulation | Searches a small integer policy landscape. |
| [MuZero planning](muzero_planning/README.md) | Research planning | Runs a small MuZero-style planner in a Gymnasium environment. |
| [MuZero MCTS LLM concept](muzeromctsllmagent_v0/README.md) | Deployment template | Preserves the original combined planning and model-integration concept. |
| [OMNI smart city](omni_factory_demo/README.md) | Offline simulation | Runs bounded smart-city episodes with local accounting. |
| [Presentation assets](presentation/README.md) | Reference | Preserved slide deck and PDF for the original demo vision. |
| [Repo-Healer](self_healing_repo/README.md) | Bounded repair | Provides repository-specific triage and isolated repair evaluation. |
| [Governance simulation](solving_agi_governance/README.md) | Offline simulation | Runs a bounded stochastic cooperation model. |
| [Sovereign agent concept](sovereign_agentic_agialpha_agent_v0/README.md) | Deployment template | Preserves the original wallet-gated agent deployment concept. |
| [Shared demo utilities](utils/README.md) | Library | Shared notices and isolated demo code evaluation helpers. |

## If something goes wrong

- **Module not found:** activate the same virtual environment used for setup and run
  `python -m pip install --no-deps -e .` from the checkout.
- **Optional dependency missing:** install the packages named by that demo's guide;
  do not interpret an explicitly labeled stub as successful model training.
- **Port busy:** stop the previous service or select the demo's documented port option.
- **Offline model missing:** cache weights first, then use the model's offline option.
- **Browser chart missing:** reload once after deployment, then check the visible error
  and network connection. Bundled replay needs no API key. Optional Python runtime
  download and paid API generation are separate, labeled actions.
- **Unexpected output:** retain the run directory and report the exact command,
  release and error, without credentials.

See [demo validation](../../../docs/agent/DEMO_VALIDATION.md) for the checks and
remaining integration boundaries. [OVERVIEW.md](OVERVIEW.md) preserves the original
vision and flywheels; this catalog is the current launch reference.
