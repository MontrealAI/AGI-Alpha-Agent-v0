[See docs/DISCLAIMER_SNIPPET.md](docs/DISCLAIMER_SNIPPET.md)

# Contributing

Thank you for considering a contribution to this project. For the complete contributor guide and coding standards, see [AGENTS.md](AGENTS.md).

All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

Please read **AGENTS.md** carefully before opening issues or submitting pull requests.

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

## Pre-commit Hooks

Run `./codex/setup.sh` to install project dependencies. The script also
installs `pre-commit` and all lint tools before configuring the git hook.
If you skip the setup script, manually install these tools with
`pip install pre-commit -r requirements-dev.txt` and then run
`pre-commit install` once. Alternatively, execute
`tools/setup_precommit.sh` to install `pre-commit` and configure the hook
without the full environment setup.

Install the git hooks once and run them before each commit:

```bash
pre-commit install
python check_env.py --auto-install  # add --wheelhouse <dir> when offline
pre-commit run --all-files
```
Run `pre-commit run --all-files` again before opening a pull request to ensure
repository-wide checks pass.
Use `pre-commit run --files docs/demos/<page>.md` to catch missing preview
images. Each page under `docs/demos/` must start with a preview image using
`![preview](...)`.
Run `python tools/update_actions.py` before committing workflow changes to pull
the latest action tags. Then run `pre-commit` so the YAML passes `actionlint`:

```bash
pre-commit run --files .github/workflows/ci.yml
```

### Updating Lock Files

Regenerate the lock files whenever you modify `requirements*.txt`:

```bash
pip-compile --upgrade --allow-unsafe --generate-hashes \
  --output-file requirements.lock requirements.txt
```

### Pre-commit in Air-Gapped Setups

When offline, build the wheelhouse first and point `pre-commit` to it:

```bash
./scripts/build_offline_wheels.sh
export WHEELHOUSE="$(pwd)/wheels"
pre-commit run --all-files
```

Refer to [AGENTS.md](AGENTS.md#pre-commit-in-air-gapped-setups) for detailed steps.

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

The **🚀 CI** workflow verifies linting, type checks, unit tests and the Docker
build. It does **not** run automatically from pull requests. Instead, the
repository owner must trigger it manually from the GitHub Actions page:

1. Open **Actions → 🚀 CI — Insight Demo**.
2. Click **Run workflow** to start the pipeline.

Remember to lint workflow edits:
```bash
pre-commit run --files .github/workflows/ci.yml
```

The job runs only when `github.actor` equals `github.repository_owner`, so other
contributors cannot execute it unless the owner grants them explicit
permissions or dispatches the workflow on their behalf.
