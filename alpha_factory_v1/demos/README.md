[See docs/DISCLAIMER_SNIPPET.md](../../docs/DISCLAIMER_SNIPPET.md)

# AGIALPHA demo catalog

**Current package:** see the generated inventory below. [Start with the factory guide](../../docs/agent/FACTORY_GUIDE.md),
[Protocol Desk](https://montrealai.github.io/AGI-Alpha-Agent-v0/ascension-protocol/) and native FusionPlan/evidence commands.
All 26 entries below remain available; their individual execution modes still apply.

**New to the demos?** Use the [step-by-step demo walkthrough](../../docs/agent/DEMOS.md)
to choose a browser experience, run a local example, and follow Insight → Nova-Seeds → MARK →
Sovereign → Jobs → validator-gated settlement. This plural `demos` directory is the canonical catalog.

**Introduced in 1.5.0:** [Launch the Ascension Lab](https://montrealai.github.io/AGI-Alpha-Agent-v0/ascension/).
Explore the white paper end to end with three editable flagship scenarios, encrypted Nova-Seed recovery,
computed FusionPlans, exact modeled funding/settlement and an interactive governance observatory.
The [implementation guide](../../docs/agent/WHITEPAPER_IMPLEMENTATION.md) maps each mechanism to code,
test evidence and its limits. The original catalog below remains available in full.

Start with the [browser gallery](https://montrealai.github.io/AGI-Alpha-Agent-v0/).
It includes **24 demos and 2 reference/support entries**. Most legacy browser charts
replay bundled illustrative traces; Insight v1 additionally supports real local
GPT-2 inference. Each guide states exactly what runs and what is simulated.

For the maintained agent, identity, operator controls and canonical Ethereum
$AGIALPHA receipt flow, use the [Agent guide](../../docs/agent/OPERATIONS.md).
Legacy Solana concepts remain preserved as historical deployment templates.

## Start locally

Use Python 3.11–3.13. An installed release wheel includes the catalog and sample data;
follow the [release installer](../../docs/agent/START_HERE.md#1-install-one-release).
For a source checkout, use an activated virtual environment:

```bash
python -m pip install --require-hashes -r requirements-agent.lock
python -m pip install --no-deps -e .
python -m alpha_factory_v1.demos list
python -m alpha_factory_v1.demos check --all
python -m alpha_factory_v1.demos show solving_agi_governance
python -m alpha_factory_v1.demos check solving_agi_governance
python -m alpha_factory_v1.demos run solving_agi_governance
```

Run these setup commands from the repository root. Optional training, UI and model
packages are listed per demo; the launcher never installs packages automatically.
`show` does not start a service or contact a provider. `check NAME --json` reports
declared module/file presence without importing optional backends, downloading or writing state;
it does not verify model weights, service configuration or provider access.
Use `check --all` (or `check --all --json`) to inspect the whole catalog at once.
Missing prerequisites return exit code 2; the three guide-only entries are listed separately. `run` checks those
prerequisites and prints its mode,
command, expected result and output directory before executing it. Finite examples
exit by themselves. Stop services with **Ctrl+C**.

All finite catalog commands listed below use explicit offline settings and are tested from the built wheel
outside the source tree with Python network calls blocked. Bundled inputs are resolved from the
installation; output-directory configuration cannot select a paid tree-search provider. Child
OpenAI/Anthropic keys and tracing are disabled for these finite commands; your shell settings are retained.
Advanced standalone commands keep their separately documented options. The launcher is not a sandbox.

Local state goes to `demo-runs/DEMO_NAME/`; select another directory with
`run DEMO_NAME --output-dir PATH`. Copy that directory to back it up. To restart
fresh without losing a run, choose a new directory. SQLite lineage runs append;
no existing run is deleted. Model caches remain separate.

**Run another experiment without choosing a folder:** add `--new-run`. The launcher creates a
unique `run-...` subdirectory, prints its exact location and retains every previous result:

```bash
python -m alpha_factory_v1.demos run finance_alpha --new-run
python -m alpha_factory_v1.demos run sovereign_agentic_agialpha_agent_v0 --new-run
```

This is particularly useful for demos that refuse to overwrite evidence. Omit `--new-run` when
you want a demo's normal persistent state, such as appended SQLite lineage, to continue.

## Choose an example

<!-- DEMO-INVENTORY:START -->
**Catalog 1.23.2: 26 entries; 17 finite offline launch checks.**

| Demo | Current mode | What it does | Finite catalog check |
|---|---|---|---|
| [AI-GA meta-evolution](aiga_meta_evolution/README.md) | Research training | Evolves small networks in a curriculum environment. | Separate acceptance / prerequisites |
| [Business v2](alpha_agi_business_2_v1/README.md) | Local service | Runs planning, research and optional commentary agents in the legacy orchestrator. | Separate acceptance / prerequisites |
| [Business 3 Enterprise Studio](alpha_agi_business_3_v1/README.md) | Reproducible planning | Select a constrained enterprise portfolio, stress the downside and export reviewable Ascension jobs. | Required |
| [Business v1](alpha_agi_business_v1/README.md) | Offline sample | Ranks bundled business opportunities; service agents publish illustrative business events. | Required |
| [Insight Discovery Workbench](alpha_agi_insight_v0/README.md) | Local evidence review | Screen cross-sector hypotheses, allocate review time and export input-bound verification jobs and plaintext Nova-Seed drafts. | Required |
| [Insight v1](alpha_agi_insight_v1/README.md) | Browser + simulation | Explores scenarios and Pareto search; optional browser GPT-2 performs real local text completion. | Required |
| [Marketplace](alpha_agi_marketplace_v1/README.md) | Local API client | Validates a bundled job and can submit it to a configured legacy orchestrator. | Required |
| [ASI world model](alpha_asi_world_model/README.md) | Research training | Explores generated grid worlds using a small learner and local API. | Separate acceptance / prerequisites |
| [Super Planner](alpha_super_planner_v1/README.md) | Interface illustration | Shows the stages and progress display of a planning interface. | Required |
| [Cross-industry discovery](cross_industry_alpha_factory/README.md) | Offline sample | Selects reproducible examples from the bundled opportunity catalog. | Required |
| [Era of Experience · Learning Lab](era_of_experience/README.md) | Offline learning lab | Learns a bounded policy from synthetic outcomes, tests it against a frozen baseline, and exports reviewable evidence. | Required |
| [Finance Alpha Research Terminal](finance_alpha/README.md) | Reproducible paper research | Inspect next-open fills, cash, costs and risk decisions; compare strategies and replay every reported result. | Required |
| [GPT-2 CLI](gpt2_small_cli/README.md) | Local model | Generates text with the actual GPT-2 124M model. | Separate acceptance / prerequisites |
| [Macro Sentinel](macro_sentinel/README.md) | Offline simulation | Computes Monte Carlo risk metrics from bundled macro samples. | Required |
| [Meta-Agentic v1](meta_agentic_agi/README.md) | Synthetic evaluation | Runs provider-driven code proposals, synthetic fitness and SQLite lineage. | Required |
| [Meta-Agentic v2](meta_agentic_agi_v2/README.md) | Synthetic evaluation | Runs provider-driven code proposals, synthetic fitness and SQLite lineage. | Required |
| [Meta-Agentic AGI v3 Curriculum Lab](meta_agentic_agi_v3/README.md) | Reproducible program induction | Generate tasks, evolve bounded solver configurations and review a frozen candidate on separate tasks. | Required |
| [Meta-Agentic Tree Search · Search Lab](meta_agentic_tree_search_v0/README.md) | Offline search lab | Explore competing workflow rewrites, resource schedules, held-out review gates and an exhaustive benchmark. | Required |
| [MuZero planning](muzero_planning/README.md) | Research planning | Train a small neural model and compare learned-model search with measured baselines. | Separate acceptance / prerequisites |
| [MuZero × MCTS × LLM](muzeromctsllmagent_v0/README.md) | Research training | Retrieve cited evidence, compare optional local-model advice with trained search, and measure simulator outcomes. | Separate acceptance / prerequisites |
| [OMNI smart city](omni_factory_demo/README.md) | Offline simulation | Runs bounded smart-city episodes with local accounting. | Required |
| [Presentation assets](presentation/README.md) | Reference | Preserved slide deck and PDF for the original demo vision. | Separate acceptance / prerequisites |
| [Repo-Healer](self_healing_repo/README.md) | Bounded repair | Provides repository-specific triage and isolated repair evaluation. | Separate acceptance / prerequisites |
| [Governance Workbench](solving_agi_governance/README.md) | Offline governance review | Inspect nine proposal gates and export reproducible evidence and validator jobs. | Required |
| [Sovereign Workbench](sovereign_agentic_agialpha_agent_v0/README.md) | Signed, review-gated workflow | Choose a feasible portfolio, schedule approved work, and produce an attributable evidence brief. | Required |
| [Shared demo utilities](utils/README.md) | Library | Shared notices and isolated demo code evaluation helpers. | Separate acceptance / prerequisites |
<!-- DEMO-INVENTORY:END -->

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

See [demo validation](../../docs/agent/DEMO_VALIDATION.md) for the checks and
remaining integration boundaries. [OVERVIEW.md](OVERVIEW.md) preserves the original
vision and flywheels; this catalog is the current launch reference.
