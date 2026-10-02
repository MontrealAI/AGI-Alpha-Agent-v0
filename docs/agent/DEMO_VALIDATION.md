[Project notice](../DISCLAIMER_SNIPPET.md)

# Demo validation and honest execution modes — 1.23.2

See the [October 1 whole-catalog audit](DEMO_AUDIT_2026-10-01.md) for the latest catalog,
navigation, preservation and failure-reporting checks and their exact limits.

Start with the [demo walkthrough](DEMOS.md) for installation, prerequisite checks, browser experiences
and the complete Ascension lifecycle. The release retains all 26 entries and tests the 17 finite offline
commands from the actual wheel outside the repository. All six CSV samples and 11 Insight scenario
fixtures are checked byte-for-byte against their source data.

The new [Ascension Lab](../ascension/index.html) adds three interactive flagship scenarios and a governance
observatory alongside the preserved 26-entry catalog. Its [implementation guide](WHITEPAPER_IMPLEMENTATION.md)
maps the original white paper to executable algorithms, encryption, clearly labeled protocol simulations
and the browser/Node acceptance evidence. All original demo checks below remain required.

All 26 original directories remain: 24 demos, presentation assets and shared utilities. Every guide has
an additive current launch section, backed by one machine-readable catalog. The original designs and
historical claims are retained; the current guide defines what is supported and what the checks prove.

## Required checks

| Gate | What must actually execute | Evidence |
| --- | --- | --- |
| Business 3 enterprise | Five cases, 41 Python/browser parity cases, seven-file exports, executed notebook, network-isolated container, public exact assets, accessibility and offline recovery | `business3-core`, `business3-browser`, `business3-container.json` and public `business3.json` |
| Catalog | Exact 26-directory coverage; 17 finite commands, with repeat runs preserving v1/v2 SQLite history | `demo-catalog.json` in regression artifacts |
| Installed demos | All 17 finite commands from the wheel with Python network calls blocked, inherited provider keys disabled and sample bytes preserved | `test_demo_distribution.py` in regression JUnit |
| Full backend wheel | All 17 finite wheel commands with backend extras installed, inherited database settings disabled and test-only environment shortcuts removed | `demo-distribution-3.11` / `demo-distribution-3.12` JUnit |
| Launcher boundaries | Output-directory module shadowing rejected, malformed output paths reported, missing modules/data stop before launch; prerequisite check has no launch/state side effects | Runtime JUnit on Python 3.11, 3.12 and 3.13 |
| Minimal wheel | Installed Governance, Macro Sentinel and Era commands execute outside the checkout with only operator dependencies | Runtime workflow on Python 3.11, 3.12 and 3.13 |
| Native CPU | Real Torch AIGA generation/checkpoint, multilayer Hebbian paths, MuZero planning/step bound, three actual Streamlit AppTests, offline GPT-2 weights | `native-demos.json` |
| Browser algorithms | 50 independent allocation-oracle cases, strict inputs, temporal leakage rejection, exact quotations and schedule invariants | Node test output |
| Legacy pages | 42 canonical/mirrored replays, data tables, search, mobile layout, explicit API error, real same-origin Pyodide, preserved Insight Plotly/tree/replay | `gallery-catalog.json` and screenshots |
| Workspace | Four missions, changed data, native handoff, review/export/import/memory, corruption rejection, untrusted text, worker cancellation, mobile, original flywheel interaction | `workspace.json` and screenshots |
| Identity | Actual integer and floating-point native agent exports, Ed25519 verification, altered body and wrong-key rejection in the browser | Workspace evidence |
| Full model | Actual same-origin ONNX GPT-2 generation, then a new worker after offline reload | Full workspace and Insight evidence |
| Publication | Same tested site artifact, commit/version manifest, public HTTPS workspace acceptance before release publication | Pages job and release manifest |

Provider HTTP-error tests deliberately use fixtures; they do not establish live paid-account access.
Native training checks demonstrate execution and bounded outputs, not convergence or AGI performance.
Browser charts labeled as replays never count as native-backend evidence. Templates without a standalone
launch remain documented templates; no cloud credentials, hardware, mainnet funds or paid API are implied.

## Inventory

<!-- DEMO-INVENTORY:START -->
**Catalog 1.23.2: 26 entries; 17 finite offline launch checks.**

| Demo | Current mode | What it does | Finite catalog check |
|---|---|---|---|
| [AI-GA meta-evolution](../demos/aiga_meta_evolution.md) | Research training | Evolves small networks in a curriculum environment. | Separate acceptance / prerequisites |
| [Business v2](../demos/alpha_agi_business_2_v1.md) | Local service | Runs planning, research and optional commentary agents in the legacy orchestrator. | Separate acceptance / prerequisites |
| [Business 3 Enterprise Studio](../demos/alpha_agi_business_3_v1.md) | Reproducible planning | Select a constrained enterprise portfolio, stress the downside and export reviewable Ascension jobs. | Required |
| [Business v1](../demos/alpha_agi_business_v1.md) | Offline sample | Ranks bundled business opportunities; service agents publish illustrative business events. | Required |
| [Insight Discovery Workbench](../demos/alpha_agi_insight_v0.md) | Local evidence review | Screen cross-sector hypotheses, allocate review time and export input-bound verification jobs and plaintext Nova-Seed drafts. | Required |
| [Insight v1](../demos/alpha_agi_insight_v1.md) | Browser + simulation | Explores scenarios and Pareto search; optional browser GPT-2 performs real local text completion. | Required |
| [Marketplace](../demos/alpha_agi_marketplace_v1.md) | Local API client | Validates a bundled job and can submit it to a configured legacy orchestrator. | Required |
| [ASI world model](../demos/alpha_asi_world_model.md) | Research training | Explores generated grid worlds using a small learner and local API. | Separate acceptance / prerequisites |
| [Super Planner](../demos/alpha_super_planner_v1.md) | Interface illustration | Shows the stages and progress display of a planning interface. | Required |
| [Cross-industry discovery](../demos/cross_industry_alpha_factory.md) | Offline sample | Selects reproducible examples from the bundled opportunity catalog. | Required |
| [Era of Experience · Learning Lab](../demos/era_of_experience.md) | Offline learning lab | Learns a bounded policy from synthetic outcomes, tests it against a frozen baseline, and exports reviewable evidence. | Required |
| [Finance Alpha Research Terminal](../demos/finance_alpha.md) | Reproducible paper research | Inspect next-open fills, cash, costs and risk decisions; compare strategies and replay every reported result. | Required |
| [GPT-2 CLI](../demos/gpt2_small_cli.md) | Local model | Generates text with the actual GPT-2 124M model. | Separate acceptance / prerequisites |
| [Macro Sentinel](../demos/macro_sentinel.md) | Offline simulation | Computes Monte Carlo risk metrics from bundled macro samples. | Required |
| [Meta-Agentic v1](../demos/meta_agentic_agi.md) | Synthetic evaluation | Runs provider-driven code proposals, synthetic fitness and SQLite lineage. | Required |
| [Meta-Agentic v2](../demos/meta_agentic_agi_v2.md) | Synthetic evaluation | Runs provider-driven code proposals, synthetic fitness and SQLite lineage. | Required |
| [Meta-Agentic AGI v3 Curriculum Lab](../demos/meta_agentic_agi_v3.md) | Reproducible program induction | Generate tasks, evolve bounded solver configurations and review a frozen candidate on separate tasks. | Required |
| [Meta-Agentic Tree Search · Search Lab](../demos/meta_agentic_tree_search_v0.md) | Offline search lab | Explore competing workflow rewrites, resource schedules, held-out review gates and an exhaustive benchmark. | Required |
| [MuZero planning](../demos/muzero_planning.md) | Research planning | Train a small neural model and compare learned-model search with measured baselines. | Separate acceptance / prerequisites |
| [MuZero × MCTS × LLM](../demos/muzeromctsllmagent_v0.md) | Research training | Retrieve cited evidence, compare optional local-model advice with trained search, and measure simulator outcomes. | Separate acceptance / prerequisites |
| [OMNI smart city](../demos/omni_factory_demo.md) | Offline simulation | Runs bounded smart-city episodes with local accounting. | Required |
| [Presentation assets](../demos/presentation.md) | Reference | Preserved slide deck and PDF for the original demo vision. | Separate acceptance / prerequisites |
| [Repo-Healer](../demos/self_healing_repo.md) | Bounded repair | Provides repository-specific triage and isolated repair evaluation. | Separate acceptance / prerequisites |
| [Governance Workbench](../demos/solving_agi_governance.md) | Offline governance review | Inspect nine proposal gates and export reproducible evidence and validator jobs. | Required |
| [Sovereign Workbench](../demos/sovereign_agentic_agialpha_agent_v0.md) | Signed, review-gated workflow | Choose a feasible portfolio, schedule approved work, and produce an attributable evidence brief. | Required |
| [Shared demo utilities](../demos/utils.md) | Library | Shared notices and isolated demo code evaluation helpers. | Separate acceptance / prerequisites |
<!-- DEMO-INVENTORY:END -->

## Reproduce

The catalog validator records every finite command, including blocked prerequisites, nonzero exits
and timeouts, then exits nonzero if any required command did not pass. Its JSON report survives
individual command failures. The nine entries requiring separate acceptance are listed explicitly;
inventory coverage is not evidence that those integrations ran. Inventory-only checks set
`smoke_requested` to false and contain no command results.

When editing catalog descriptions, run `python -m scripts.sync_demo_catalog_docs` to refresh both
inventory tables and versioned current-launch headings. Validation rejects stale tables or launch
versions. Historical headings, code examples, research narratives, diagrams and media are retained.

From a source checkout, install the documented development environment, then:

```sh
python -m scripts.sync_demo_catalog_docs --check
python -m scripts.validate_demo_catalog --smoke --output evidence/demo-catalog.json
python -m scripts.run_local_tests tests/test_demo_distribution.py -q
node --test tests/browser/portal_engine.test.mjs
bash scripts/build_gallery_site.sh
python -m scripts.validate_gallery_catalog --site site --output evidence/gallery-catalog
python -m scripts.validate_pages_workspace --site site --model --output evidence/pages-workspace
```

The complete build downloads verified model/runtime assets. Set `FETCH_ASSETS_SKIP_LLM=1` for a minimal
development build and omit `--model` only in its dedicated minimal-assets test; full release acceptance
requires the real model. Use the pinned Node/Python versions from AGENTS.md.

For optional native CPU demos on Linux/Python 3.12, use a separate environment:

```sh
python3.12 -m venv .venv-native-demos
.venv-native-demos/bin/python -m pip install --require-hashes -r requirements-demo-verified.lock
.venv-native-demos/bin/python -m pip install --no-deps -e .
.venv-native-demos/bin/python scripts/download_hf_gpt2.py models/gpt2
.venv-native-demos/bin/python -m scripts.validate_native_demos --model models/gpt2 --output evidence/native-demos.json
```

Maintainers regenerate this lock with Python 3.12 and the pinned compiler tools:

```sh
python -m pip install pip==25.2 pip-tools==7.5.0 click==8.2.1
pip-compile --allow-unsafe --constraint=requirements-agent.lock \
  --extra-index-url=https://download.pytorch.org/whl/cpu --generate-hashes \
  --output-file=requirements-demo-verified.lock pyproject.toml requirements-demo-verified.in
```

The operator lock remains a compiler constraint. Pass it on the command line because GitHub's
dependency scanner only fetches `.txt` and `.in` constraint references from requirement manifests.
The input manifest declares the same CPU wheel index as the compiled lock. Users install the
hash-locked output above; the input manifest is for dependency maintenance and indexing.

The original optional requirements and deployment examples remain available for research. Their presence
does not establish provider integration, infrastructure readiness or external service availability.
Release artifacts contain the actual CI outcomes and commit, including failures/skips where relevant;
only required gates block publication. See [runtime validation](VALIDATION.md) for the broader suite.
