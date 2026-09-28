[Project notice](../DISCLAIMER_SNIPPET.md)

# Start here — get a useful, reviewable result

Alpha-Factory runs bounded missions against inputs you supply, retains a signed journal, and asks you
to inspect the result before approval. Start with the allocation example; it needs no wallet, API key,
Docker or model download. The [factory guide](FACTORY_GUIDE.md) explains all five mission types and the
complete Ascension path. Browser-only examples are available in [Decision Studio](../studio/index.html).

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

Activate the environment on macOS or Linux:

```bash
source .venv-agent/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv-agent\Scripts\Activate.ps1
```

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
- Inspect the release's `release-manifest.json` and `alpha-agent-v…-validation.zip` for exact acceptance
  results. The source, browser, complete site and unchanged manuscript are separate release assets.

If a command fails, keep the existing environment and journal. Check the JSON error, supported Python
version and selected profile; follow the recovery guide using a new destination. Never manually edit
signed journal records. The maintained runtime and the undeployed contract reference are distinct
from the broader research vision; [release readiness](RELEASE_READINESS.md) defines the verified scope.
