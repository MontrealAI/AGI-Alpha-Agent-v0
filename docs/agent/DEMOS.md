[Project notice](../DISCLAIMER_SNIPPET.md)

# Demos — choose a path, run it, inspect the evidence

<!-- CATALOG-RELEASE:START -->
**Version 1.23.0.** The canonical directory is
[`alpha_factory_v1/demos`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos).
All 26 entries, their research narratives, flowcharts and media remain available.
Start in the browser for an interactive tour, or run a finite local example below.
<!-- CATALOG-RELEASE:END -->

## Start in the browser

Built-in scenarios need no account, wallet or API key. Each experience identifies its inputs,
computed results and modeled assumptions. Export work you want to retain.

| Your question | Open | What to inspect |
|---|---|---|
| How do I turn project choices into reviewed, signed work? | [Sovereign Workbench](../sovereign_agentic_agialpha_agent_v0/index.html) | Portfolio → schedule → source-bound brief, explicit approvals, signed exports and recovery |
| Does a paper strategy survive costs and execution rules? | [Finance Alpha](../finance_alpha/index.html) | Next-open fills, cash ledger, risk decisions and exact replay |
| Which cross-sector hypothesis has enough evidence to investigate? | [Insight Discovery Workbench](../alpha_agi_insight_v0/index.html) | Source assumptions, review budget, dossier and unsubmitted verification jobs |
| Does a learned policy improve on a held-out environment? | [Experience Learning Lab](../era_of_experience/index.html) | Learning history, frozen candidate, independent gates and complete exports |
| What does a small neural planner actually learn? | [MuZero Planning Lab](../muzero_planning/index.html) | Recorded planning evidence and a separate native training launch |
| How do cited evidence and local-model advice enter planning? | [Evidence & Planning Lab](../muzeromctsllmagent_v0/index.html) | Source provenance, bounded advice, native training and reproducible reports |
| Can a meta-agent teach a solver without leaking evaluation answers? | [Curriculum Lab](../meta_agentic_agi_v3/index.html) | Adaptive tasks, hypothesis search, lineage, independent gates and verified exports |
| Which workflow design deserves independent review? | [MATS Search Lab](../meta_agentic_tree_search_v0/index.html) | Branching search, rollouts, oracle gap, held-out schedules and five gates |
| Should a governance proposal advance to independent review? | [Governance Workbench](../solving_agi_governance/index.html) | Nine gates, adversarial cases, exact dossier and verification jobs |
| Which enterprise projects fit capital, staff and reviewer capacity? | [Business 3 Enterprise Studio](../alpha_agi_business_3_v1/index.html) | Exact portfolio, downside stress, evidence bundle and Ascension job specs |
| What should I do with a constrained budget or schedule? | [Decision Studio](../studio/index.html) | Edit a case, compare feasible plans and export its dossier |
| Which opportunity deserves further investigation? | [Insight Atlas](../insight/index.html) | Scenario assumptions, holdout results and claim evidence |
| How does a claim become reviewed work? | [Proof Bloom](../bloom/index.html) | Jobs, exact evidence, review, promotion and revocation |
| Does retained experience help a new task? | [Compounding Lab](../compounding/index.html) | Frozen policy, held-out tasks, costs and negative controls |
| How does the complete Ascension vision fit together? | [Ascension Lab](../ascension/index.html) | Editable scenarios, cryptosealed seeds, FusionPlans and modeled economics |
| What does the executable enterprise protocol enforce? | [Protocol Desk](../ascension-protocol/index.html) | Local-EVM receipt, role checks, funding, auctions, validation and settlement |
| Where are the original experiments? | [Full gallery](../demos/index.html) | All 24 demos and two reference/support entries, with explicit execution modes |

Legacy replay charts display bundled traces. They are illustrations of the retained experiments.
Real local model inference and native training have separate, labeled launch paths and prerequisites.
See the [browser guide](PAGES_GUIDE.md) for downloads, offline use and recovery.

## Run a local example

Use **Python 3.11–3.13**. The checksum-verifying [release installer](START_HERE.md#1-install-one-release)
creates the environment from matching release assets. Activate that environment before continuing.
The wheel includes the catalog, CSV samples and Insight scenario fixtures; these commands work outside
the source checkout.

For source development, run this setup from the repository root:

```bash
python3 -m venv .venv-agent
source .venv-agent/bin/activate
python -m pip install --require-hashes -r requirements-agent.lock
python -m pip install --no-deps -e .
```

On Windows PowerShell, use `python -m venv .venv-agent` and then
`.\.venv-agent\Scripts\Activate.ps1`. The remaining commands are the same.

Now inspect and run a bounded governance review:

```bash
python -m alpha_factory_v1.demos list
python -m alpha_factory_v1.demos check --all
python -m alpha_factory_v1.demos show solving_agi_governance
python -m alpha_factory_v1.demos check solving_agi_governance
python -m alpha_factory_v1.demos run solving_agi_governance --output-dir my-demo-runs/governance
```

The command prints the execution mode, expected result, command and output directory. The review
prints nine gate decisions and saves five evidence files, including unsubmitted validator jobs.
See the [governance guide](GOVERNANCE.md) for replay and model assumptions. Try `macro_sentinel` for risk calculations over bundled macro samples, or
`era_of_experience` for a reproducible learning experiment and independent review gates. Replace the name in `show`, `check` and `run`.

For bounded workflow design search, run `meta_agentic_tree_search_v0` or follow the [MATS guide](MATS.md).

For enterprise project selection, run `alpha_agi_business_3_v1` or follow the
[Business 3 guide](BUSINESS3.md). Its bounded default requires only Python and exports seven evidence files.

For useful work on your own records, continue with the [native mission walkthrough](FACTORY_GUIDE.md#install-and-obtain-a-first-result).
It produces a signed, reviewable journal using research, allocation, schedule, forecast or isolated code missions.

## Understand the launcher

| Command | Behavior |
|---|---|
| `list` / `list --json` | Enumerates all 26 entries and their execution modes |
| `show NAME` | Shows the command, expected result, limitations and guide without launching |
| `check NAME` / `check NAME --json` | Checks declared module and bundled-file presence without importing optional backends, downloading or creating run state |
| `check --all` / `check --all --json` | Reports every entry, missing prerequisites and guide-only entries without launching anything |
| `run NAME --output-dir PATH` | Checks prerequisites, then launches the documented command with its declared settings |

`check` returns **0** when declared prerequisites are present, and **2** when a prerequisite is missing
or the entry has no standalone CLI. It does not exercise model weights, GPU support, services or paid
accounts. Follow the entry's guide for those integrations. The launcher never installs packages.
Some examples need additional modules such as Rich or Click beyond the base operator environment.
`check --all` returns **0** when every catalog command has its declared prerequisites, or **2** if
any are missing. The three guide-only entries are reported separately and do not count as failed
commands. A READY result checks file/module presence; it does not certify a working service or model.

<!-- CATALOG-COUNTS:START -->
The catalog contains **26 entries: 23 launch commands and 3 guide-only entries**.
The 17 finite catalog examples use explicit offline defaults. Their child processes disable configured
OpenAI/Anthropic keys, remote Neo4j/PostgreSQL storage and tracing; tree search uses its bundled
synthetic workflow model and reproducible private random stream.
Your shell credentials are unchanged. The release tests run all 17 from the wheel with Python network
calls blocked, including Python 3.11/3.12 environments with the full backend dependencies and inherited
database settings. This verifies those launch contracts; the launcher is not a network or code sandbox.
Advanced standalone commands and optional services retain their separately documented behavior.
<!-- CATALOG-COUNTS:END -->

Output defaults to `demo-runs/NAME/`. Relative directories resolve from the directory where you launch.
Paths containing spaces are supported. The child does not import Python modules from its output
directory. Stop services with **Ctrl+C**. Copy the run directory to retain results; choose a new output
directory for a fresh run. Lineage examples append to existing history. Model caches are separate.

## Follow the full Ascension lifecycle

| Vision | Runnable path | What the evidence establishes |
|---|---|---|
| 🎖️ Insight → hidden α | Insight Atlas, native research/forecast/allocation, Insight demos | Reproducible analysis of supplied or constructed inputs; predictive superiority requires external evaluation |
| 🌱 Nova-Seeds → foresight genome + FusionPlan | Ascension Lab; `NovaSeed.sol`; native `ascension-compile` and `ascension-check` | Encrypted recovery, ERC-721 lineage and exact committed goal/metric/bounty jobs |
| 🔮 MARK → risk-gated funding | Protocol Desk; `AscensionRiskOracle.sol` and `AscensionMark.sol` | Local-EVM admission, expiring reviews, bonding-curve funding and recovery paths |
| 👑 Sovereign → an enterprise plan | Sovereign Workbench; plan-restricted treasury and indexed Merkle jobs | Reviewed portfolio/schedule/evidence with signed exports; local-EVM once-only routing, budget and deadline checks |
| 👾 Agents → reputation-weighted execution | Native missions; `AscensionJobMarket.sol` | Staked `*.alpha.agent.agi.eth` fixture identities; price/time/reputation auction rules and evidence-bound delivery |
| ✅ Validators → payment or failure | Protocol Desk settlement; `*.alpha.club.agi.eth` fixture identities | Two-of-three exact-result decisions, refunds, explicit slashing and a 1% payout burn in $AGIALPHA |
| 🧬 Experience → successor enterprises | Proof Bloom, Compounding Lab, successor Nova-Seeds | Reviewable retained evidence and unapproved successors; measured bounded transfer rather than assumed general improvement |

The [factory guide](FACTORY_GUIDE.md#trace-the-full-vision-to-executable-components) maps these mechanisms
to implementation. The [protocol guide](ASCENSION_PROTOCOL.md) reproduces the actual local-EVM lifecycle,
including negative cases and the connection to native signed delivery. The contract reference is
undeployed; browser simulations and fixture ENS identities do not establish a live global marketplace.
All original industry integrations remain available with their stated research and deployment boundaries.

## Resolve a failed launch

- **Missing module:** activate the intended environment, run `check NAME`, then install the optional
  requirements from that entry's guide. Do not substitute a training stub for native execution.
- **Missing bundled file:** reinstall the same release into a new environment. The catalog refuses
  an incomplete sample installation before starting the demo.
- **Output path is a file or is not writable:** choose a new writable directory. Existing results
  are retained; the launcher reports the path error without a traceback.
- **A service exits or a port is busy:** read the printed guide and service output. Stop the prior
  instance or use that service's documented port setting.
- **A model is unavailable offline:** use its documented, checksum-verified model download first.
- **An unexpected result remains:** retain the output, version, command and error for diagnosis;
  omit credentials. `run` preserves the child exit status and prints the guide on failure.

The [validation matrix](DEMO_VALIDATION.md) identifies the catalog, installed-wheel, native CPU,
browser, protocol and publication gates. [Release readiness](RELEASE_READINESS.md) defines the verified
deployment scope. These guides supplement every preserved original flowchart and research narrative.
