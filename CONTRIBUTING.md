[See docs/DISCLAIMER_SNIPPET.md](docs/DISCLAIMER_SNIPPET.md)

# Contributing

Thank you for considering a contribution to this project. For the complete contributor guide and coding standards, see [AGENTS.md](AGENTS.md).

All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

Please read **AGENTS.md** carefully before opening issues or submitting pull requests.

## Contribute to the possibility engine / contribuer au moteur des possibles

Follow the [Blue Sky mission and admission gate](AGENTS.md#mission-admit-the-possibility-before-building-the-flagship)
before substantial flagship work. Compare three consequential possibilities, name the strongest accessible
alternative, construct the missing means and define independent acceptance before fresh evaluation. Reuse the
existing discovery and project history. Report candidate admission, actual construction and commercial evidence
as separate states; a completed form or profitable bounded probe does not establish a transformational flagship.

En français : comparer trois possibilités, préciser la contrainte et le moyen manquant, puis construire et tester
un résultat utile. Distinguer l’admission Blue Sky, la construction démontrée et la qualification commerciale.
Une sonde sous HOLD garde un budget et une condition d’arrêt séparés. Les règles de sécurité et de publication
restent applicables. [Commencer / start here](docs/agent/START_HERE.md).

## Dependency Policy

Avoid introducing third-party subscription services such as Chainlink VRF. New code and examples should remain self-contained without external subscription-based dependencies.

## Type Checking the Demo

Run mypy only on the demo package while iterating:

```bash
mypy --config-file mypy.ini alpha_factory_v1/demos/alpha_agi_insight_v1
```

Replace the path with your demo directory as needed. The configuration excludes
other modules so checks remain fast.

## Running Tests

Before running the test suite, ensure optional dependencies are installed. This
project relies on packages such as `openai-agents` and `google-adk` for the
integration tests.

```bash
python scripts/check_python_deps.py
python check_env.py --auto-install  # add --wheelhouse <dir> when offline
```

The environment check installs any missing packages from PyPI (or from your
wheelhouse when offline). Once it succeeds, execute the tests:

```bash
pytest --cov --cov-report=xml
```

### Dockerfiles

When modifying build dependencies or system packages in the project
`Dockerfile`, update `alpha_factory_v1/Dockerfile` as well so both images
remain consistent.

### Node Dependencies

Node packages live under `alpha_factory_v1/core/interface/web_client` and the
Insight browser demo. When you add or upgrade a package, run `npm install` (or
`npm update`) in the corresponding directory and commit the updated
`package-lock.json`. Rebuild the Docker image after changing these lock files so
the container includes the new dependencies.

## Pre-commit Hooks

Run `./codex/setup.sh` to install project dependencies. The script also
installs `pre-commit` and all lint tools before configuring the git hook.
If you skip the setup script, manually install these tools with
`pip install pre-commit==4.2.0 -r requirements-dev.txt` and then run
`pre-commit install` once. Alternatively, execute
`tools/setup_precommit.sh` to install `pre-commit` and configure the hook
without the full environment setup.

Install the git hooks once. Running `pre-commit run --files <changed-files>` locally is
recommended feedback to catch lint errors early, not a prerequisite for opening a draft or pull request:

```bash
pre-commit install
python check_env.py --auto-install  # add --wheelhouse <dir> when offline
pre-commit run --all-files   # first time to set up caches
```
A local `pre-commit run --all-files` is recommended for repository-wide feedback. If it cannot run
or fails, a draft or pull request may still be opened: disclose the check, outcome and reason. Never
claim an unrun or failed check passed. Existing hooks, access restrictions and required hosted merge
and release checks remain unchanged; this policy does not authorize bypassing them.
- Large bundle artifacts (`*.bundle.js` and `*.bundle.js.map`) are marked as generated in `.gitattributes`, so pre-commit and search tools ignore them.
Use `pre-commit run --files docs/demos/<page>.md` to catch missing preview
images. Each page under `docs/demos/` must start with a preview image using
`![preview](...)`.
Workflow YAML files are linted by `pre-commit`. A local hook automatically
runs `python tools/update_actions.py` whenever files in `.github/workflows/`
change. The script will install `requests` automatically if it's missing.
You can also run it manually:

```bash
pre-commit run --files .github/workflows/ci.yml
```

## Quick Checklist

Ensure **Python 3.11–3.13** and **Node.js 22** are installed before running the tools.
For early local feedback, `pre-commit run --files <changed-files>` is recommended to lint your modifications.

Use these checks during development and record their actual outcomes in the pull request:

```bash
python scripts/check_python_deps.py
python check_env.py --auto-install
pre-commit run --files <changed-files>  # recommended local feedback
pytest
pre-commit run --all-files  # recommended repository-wide local feedback
```
Local hook completion is not a prerequisite for draft or pull-request submission. Disclose failing
or unrun checks rather than treating the list as a claim of success. Canonical PR CI provides
`Lint (ruff)` and `Smoke tests`; full Integration CI runs on main, release tags or manual dispatch.
Required hosted merge checks, exact-main CI and the complete Agent release acceptance gates, including
their full hook checks, remain unchanged and must pass before publication.

See [AGENTS.md](AGENTS.md#pull-requests) for more details.

### Updating Lock Files

Regenerate the lock files whenever you modify `requirements*.txt`:

Run `scripts/update_root_lock_files.sh` to regenerate all lock files in a single
pass. The helper calls `pip-compile` for each requirements file so that shared
dependencies like `aiohttp` resolve to the same versions across the project:

```bash
./scripts/update_root_lock_files.sh
```

The script writes `requirements.lock`, `requirements-dev.lock`,
`requirements-docs.lock`, `requirements-demo.lock`, `requirements-cpu.lock` and
`requirements-demo-cpu.lock`.

### Running `pip-compile`

Invoke `pip-compile` directly when you only need to refresh a specific lock
file. The command now requires `--allow-unsafe` so build tools like
`setuptools` remain pinned:

```bash
pip-compile --upgrade --allow-unsafe --generate-hashes \
  --output-file requirements.lock requirements.txt
```

For the CPU-only environment include all requirement files and specify the
standard index URL:

```bash
pip-compile --upgrade --allow-unsafe --generate-hashes \
  --index-url=https://pypi.org/simple \
  requirements-demo.txt requirements-dev.txt requirements.txt \
  -o requirements-cpu.new
mv requirements-cpu.new requirements-cpu.lock
```

Run the same command with `requirements-demo.txt` as the sole input to update
`requirements-demo-cpu.lock`.

### Backend Lock File

Refresh the backend lock file whenever `alpha_factory_v1/backend/requirements.txt`
changes:

```bash
pip-compile --upgrade --allow-unsafe --generate-hashes \
  --output-file alpha_factory_v1/backend/requirements-lock.txt \
  alpha_factory_v1/backend/requirements.txt
```

All lock files must include hashes so the Docker images can verify packages at
build time.

### Pre-commit in Air-Gapped Setups

When offline, build the wheelhouse first and point `pre-commit` to it:

```bash
./scripts/build_offline_wheels.sh
export WHEELHOUSE="$(pwd)/wheels"
pre-commit run --all-files
```

Refer to [AGENTS.md](AGENTS.md#pre-commit-in-air-gapped-setups) for detailed steps.

### Run CI locally

1. Create and activate a Python 3.11–3.13 virtual environment, then upgrade pip:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```
2. Install dependencies (set `ALPHA_FACTORY_FULL=1` for heavier extras or `--wheelhouse <dir>` when offline):
   ```bash
   python check_env.py --auto-install
   ```
3. Run the linters and formatters:
   ```bash
   pre-commit run --all-files
   ```
4. Execute the tests:
   ```bash
   pytest
   ```
5. Trigger the GitHub Actions pipeline from **Actions → 🚀 Integration CI — Insight Demo** (or **PR CI** for pull requests) and click **Run workflow** (repository owners only).

**Troubleshooting:**
- If tests fail due to missing optional packages, rerun `python check_env.py --auto-install` with `ALPHA_FACTORY_FULL=1`.
- When running without internet or behind strict firewalls, set `WHEELHOUSE=$(pwd)/wheels` and supply `--wheelhouse "$WHEELHOUSE"` so installs pull from the local wheel cache instead of PyPI.

## Documentation Builds

Run `mkdocs build --strict` before opening a pull request. The CI pipeline also
executes this command and fails if any warnings are produced.

### 📚 Docs Workflow

The **📚 Docs** workflow publishes the MkDocs site and demo gallery to GitHub
Pages. Only the repository owner can dispatch it because the workflow checks
that `github.actor` matches `github.repository_owner` before building the site.

1. Open **Actions → 📚 Docs**.
2. Click **Run workflow** to start the deployment.

The job runs `scripts/edge_human_knowledge_pages_sprint.sh` to rebuild the site
and then uses the [Lychee](https://github.com/lycheeverse/lychee) checker to
verify all internal links. If any links fail validation, the workflow aborts.

### 🚀 CI Workflow

The **🚀 CI** workflow runs linting, type checks, the full test matrices,
Windows and macOS smoke tests, the offline docs build and the Docker
image build. It does **not** run automatically from pull requests. Instead, the
repository owner must trigger it manually from the GitHub Actions page:

1. Open **Actions → 🚀 Integration CI — Insight Demo**.
2. Click **Run workflow** to start the pipeline.

Remember to lint workflow edits:
```bash
pre-commit run --files .github/workflows/ci.yml
```

The job runs only when `github.actor` equals `github.repository_owner`, so other
contributors cannot execute it unless the owner grants them explicit
permissions or dispatches the workflow on their behalf. Downstream jobs use
`if: always()` so Windows and macOS smoke tests, docs and Docker steps still run
whenever the owner triggers the workflow even if earlier stages fail.

### Branch protection and required checks

Protect `main` (and any long-lived release branches) with required status checks
so GitHub blocks merges until CI completes:

1. Open **Settings → Branches → Branch protection rules**.
2. Add or edit the rule targeting `main`.
3. Enable **Require status checks to pass before merging** and select the
   following checks (names must match exactly):
   - `✅ PR CI / Lint (ruff)`
   - `✅ PR CI / Smoke tests`
4. Keep **Require branches to be up to date before merging** enabled so reruns
   pick up the latest checks.
5. Apply the same required checks to any release branches that mirror `main`.

These names stay stable because each workflow job sets an explicit `name`
value. The list above matches the branch-protection validation performed in
`scripts/verify_branch_protection.py`.

## Publishing research papers

Use the [paper upload guide](docs/agent/PAPER_UPLOADS.md) to add an immutable PDF and optional TeX source with one catalog import. Paper-only validation is separate from software release acceptance.
