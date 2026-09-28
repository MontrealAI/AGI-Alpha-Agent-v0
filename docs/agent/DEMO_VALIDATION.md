[Project notice](../DISCLAIMER_SNIPPET.md)

# Demo validation and honest execution modes — 1.14.0

Start with the [demo walkthrough](DEMOS.md) for installation, prerequisite checks, browser experiences
and the complete Ascension lifecycle. The release retains all 26 entries and tests the 15 finite offline
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
| Catalog | Exact 26-directory coverage; 15 finite commands, with repeat runs preserving v1/v2 SQLite history | `demo-catalog.json` in regression artifacts |
| Installed demos | All 15 finite commands from the wheel with Python network calls blocked, inherited provider keys disabled and sample bytes preserved | `test_demo_distribution.py` in regression JUnit |
| Full backend wheel | All 15 finite wheel commands with backend extras installed, inherited database settings disabled and test-only environment shortcuts removed | `demo-distribution-3.11` / `demo-distribution-3.12` JUnit |
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

| Directory | Current mode | Finite catalog gate |
| --- | --- | --- |
| [aiga_meta_evolution](../demos/aiga_meta_evolution.md) | Research training | Dedicated check or explicit prerequisites |
| [alpha_agi_business_2_v1](../demos/alpha_agi_business_2_v1.md) | Local service | Dedicated check or explicit prerequisites |
| [alpha_agi_business_3_v1](../demos/alpha_agi_business_3_v1.md) | Simulation | Dedicated check or explicit prerequisites |
| [alpha_agi_business_v1](../demos/alpha_agi_business_v1.md) | Offline sample | Required |
| [alpha_agi_insight_v0](../demos/alpha_agi_insight_v0.md) | Offline simulation | Required |
| [alpha_agi_insight_v1](../demos/alpha_agi_insight_v1.md) | Browser + simulation | Required |
| [alpha_agi_marketplace_v1](../demos/alpha_agi_marketplace_v1.md) | Local API client | Required |
| [alpha_asi_world_model](../demos/alpha_asi_world_model.md) | Research training | Dedicated check or explicit prerequisites |
| [alpha_super_planner_v1](../demos/alpha_super_planner_v1.md) | Interface illustration | Required |
| [cross_industry_alpha_factory](../demos/cross_industry_alpha_factory.md) | Offline sample | Required |
| [era_of_experience](../demos/era_of_experience.md) | Offline sample | Required |
| [finance_alpha](../demos/finance_alpha.md) | Deployment example | Dedicated check or explicit prerequisites |
| [gpt2_small_cli](../demos/gpt2_small_cli.md) | Local model | Dedicated check or explicit prerequisites |
| [macro_sentinel](../demos/macro_sentinel.md) | Offline simulation | Required |
| [meta_agentic_agi](../demos/meta_agentic_agi.md) | Synthetic evaluation | Required |
| [meta_agentic_agi_v2](../demos/meta_agentic_agi_v2.md) | Synthetic evaluation | Required |
| [meta_agentic_agi_v3](../demos/meta_agentic_agi_v3.md) | Identity curriculum | Required |
| [meta_agentic_tree_search_v0](../demos/meta_agentic_tree_search_v0.md) | Offline simulation | Required |
| [muzero_planning](../demos/muzero_planning.md) | Research planning | Dedicated check or explicit prerequisites |
| [muzeromctsllmagent_v0](../demos/muzeromctsllmagent_v0.md) | Deployment template | Dedicated check or explicit prerequisites |
| [omni_factory_demo](../demos/omni_factory_demo.md) | Offline simulation | Required |
| [presentation](../demos/presentation.md) | Reference | Dedicated check or explicit prerequisites |
| [self_healing_repo](../demos/self_healing_repo.md) | Bounded repair | Dedicated check or explicit prerequisites |
| [solving_agi_governance](../demos/solving_agi_governance.md) | Offline simulation | Required |
| [sovereign_agentic_agialpha_agent_v0](../demos/sovereign_agentic_agialpha_agent_v0.md) | Deployment template | Dedicated check or explicit prerequisites |
| [utils](../demos/utils.md) | Library | Dedicated check or explicit prerequisites |

## Reproduce

From a source checkout, install the documented development environment, then:

```sh
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
