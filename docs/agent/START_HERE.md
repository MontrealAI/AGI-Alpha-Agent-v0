[Project notice](../DISCLAIMER_SNIPPET.md)

# Start here — get a useful, reviewable result

**MONTREAL.AI flagship: Find your Alpha. Build your SUCCESSOR Ω.**

**[Start the flagship →](../successor/alpha/index.html)** ·
**[Démarrer le parcours phare →](../successor/alpha/index.html?lang=fr)**

Choose a valuable opportunity in software, research or mathematics. Prepare a Computer Use mission to
investigate real public material and produce a concrete artifact. Discover and combine strategies at Level 3,
then test a better problem formulation at Level 4 while preserving the required outcome and acceptance criteria.
Keep the proposed value, attempts, observations, reviews and lessons in one project.
Planning and the catalog example run free in your browser; model-driven execution uses a separately configured
native runner. Follow the [flagship guide](SUCCESSOR_ALPHA.md) for the guided path and current scope.

**For bounded transformational discovery:** [open the free offline workspace](../transformational-intelligence/index.html)
or follow the [native source-pilot guide](../../examples/transformational-intelligence/README.md).
It preserves the required artifact, compares alternative methods and retains reviewable evidence.
The [implementation register](TRANSFORMATIONAL_IMPLEMENTATION.md) states the structural and research limits.

<!-- computer-use-study-publication -->
**See what was actually demonstrated:** [Read the computer-use study](../reports/computer-use-study/REPORT.md) or open its [English/French visual reader](../reports/computer-use-study/index.html). Two repaired websites, tested recovery and fewer scripted setup controls; simulated owner, not a production benchmark.
<!-- /computer-use-study-publication -->

**For a maintained local example:** [open the catalog engineering tool](../successor/alpha/index.html#catalog-example).
Reconcile supplied or permitted CSVs, inspect the results and retain the tool. It runs without an account,
installation, model API or wallet; the flagship opportunity mission above is the main starting point.
The [simple planning walkthrough](../start/index.html) remains available in English and French with larger text.
The instructions below are for installing and operating your own agent.

**Plan → adapt → repair one project:** follow the [Strategy Succession guide](STRATEGY_SUCCESSION.md).
Its connected interface uses an explicitly approved, separately installed fixed-method executor.
It keeps service and improvement costs separate and retains stronger specialist wins.

**Starting a Nova-Seed project?** Follow the [English first-use guide](ASCENSION_STACK_RELEASE.md#first-use-english)
to prepare, encrypt and keep a small project before choosing any wallet or paid service. The guide also
explains the installed executor and the separate execution, review and payment decisions.

**Vous préférez le français?** Le [guide de première utilisation](ASCENSION_STACK_RELEASE.md#premiere-utilisation-francais)
explique comment préparer et sauvegarder un projet, puis utiliser la console locale. La préparation ne
demande ni portefeuille ni service payant; chaque autorisation reste une décision distincte.

Alpha-Factory runs bounded missions against inputs you supply, retains a signed journal, and asks you
to inspect the result before approval. Start with the allocation example; it needs no wallet, API key,
Docker or model download. The [factory guide](FACTORY_GUIDE.md) explains all five mission types and the
complete Ascension path. Browser-only examples are available in [Decision Studio](../studio/index.html).

For self-generated reasoning tasks and independent solver review, open the [Curriculum Lab](CURRICULUM_LAB.md).

For the new two-generation mission lifecycle, open the bilingual [SUCCESSOR Ω workspace](../successor/index.html)
or follow [its first-session guide](SUCCESSOR.md). Once installed, run
`alpha-agent --home successor-state successor-demo --output successor-evidence`.
It constructs and measures real bounded challengers, preserves usable methods and tests clean restoration.
Missing independent qualification remains HOLD; a software demonstration grants no production authority.

**Find your Alpha. Build your SUCCESSOR Ω.** Follow the [guided project journey](GUIDED_SUCCESSOR_JOURNEY.md)
to retain discovery, bounded work, separately priced USDC / $AGIALPHA proposals and Fleet local returns in
one history. The browser guides explicit file handoffs; funding and independent commissioning remain separate.

**Current Alpha contracts:** use the [October 18 address directory](../deployments/2026-10-18/index.html)
and [retained deployment evidence](CURRENT_MAINNET_DEPLOYMENT.md). The historical October 11 wallet profile
remains for its existing obligations; a current address reference does not reroute a wallet or authorize funding.

## 1. Install one release

Use Python **3.11, 3.12 or 3.13**. From one [release](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/latest),
download these four assets into the same folder:

- The `alpha_factory_v1-…-py3-none-any.whl` wheel.
- `requirements-agent.lock`.
- `SHA256SUMS`.
- `install_agent.py`.

Open a terminal in that folder and run:

```bash
python3 install_agent.py --release-dir . --venv .venv-agent
```

On Windows use `python` in place of `python3`. If several Python versions are installed, select a
supported interpreter explicitly, for example `python3.12`.

The installer checks the wheel and dependency lock against the release checksums, creates a new
environment, installs the hashed dependencies and verifies the installation. Do not mix assets from
different versions. If the environment path already exists, choose a new path; your existing state
is retained. For an offline install, add `--wheelhouse /path/to/compatible-wheels`.
Download and extract `alpha-agent-v…-operator-guide.zip` for all the linked guides in one folder.

To check downloaded files before installation, add `--check-only`. It validates checksums and paths
without creating an environment. The [repository guide](REPOSITORY_GUIDE.md) maps the other launch paths.

Activate the environment on macOS or Linux:

```bash
source .venv-agent/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv-agent\Scripts\Activate.ps1
```

If PowerShell blocks activation, call `.\.venv-agent\Scripts\alpha-agent.exe` in place of
`alpha-agent`; activation is not required. Confirm `alpha-agent --version` matches the release you
downloaded. A checksum error or installation failure is a reason to stop and fix the inputs, not to
reuse a partially installed environment. See [first-run troubleshooting](OPERATIONS.md#troubleshooting-a-first-run).

## 2. Run and inspect the example

```bash
alpha-agent examples --output my-missions
alpha-agent --home ./agent-state init
alpha-agent --home ./agent-state run my-missions/allocation.json
alpha-agent --home ./agent-state serve
```

Open **http://127.0.0.1:8765** and use the token in `agent-state/api.token`. Select the returned mission.
Inspect its selected projects, budget, risk and totals, then approve or reject the exact result.
These example inputs are constructed scenarios; edit their assumptions before using a result for
a real decision. Approval records your review and does not execute a trade or make a payment.
Stop the console with **Ctrl+C**.

## 3. Continue with your own work

- Edit the copied examples: research, allocation, scheduling, forecasting or code. Code evaluation
  requires explicit permission and an isolated Docker runtime.
- Use the [factory guide](FACTORY_GUIDE.md) for reviewed native work, FusionPlans and signed delivery.
- Explore workflow alternatives in the [MATS Search Lab](MATS.md), then export a reproducible review bundle.
- Use the [demo walkthrough](DEMOS.md) for all browser experiences and the preserved local experiments.
- Use [operations and recovery](OPERATIONS.md) before upgrades, backup, restore or provider configuration.
- Use the [Ascension protocol guide](ASCENSION_PROTOCOL.md) for the local-EVM enterprise lifecycle.
- Use the [contract deployment and migration guide](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/tests/contracts/README.md)
  to inspect the deployment plan and rehearse the disposable Hardhat fixture. It is separate from installing this agent.
- Inspect the release's `release-manifest.json` for exact acceptance results and its `validation_evidence`
  inventory. The original `alpha-agent-v…-validation.zip` retains local checks; separate public-validation
  packs retain deployed-site checks. Keep their manifests, parts and matching `SHA256SUMS` together.
  The source, browser, complete site and unchanged manuscript are separate release assets.

If a command fails, keep the existing environment and journal. Check the JSON error, supported Python
version and selected profile; follow the recovery guide using a new destination. Never manually edit
signed journal records. The maintained runtime, exact deployed-source record and later contract candidates are distinct
from the broader research vision; [release readiness](RELEASE_READINESS.md) defines the verified scope.
