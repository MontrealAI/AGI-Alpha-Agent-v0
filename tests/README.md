# SPDX-License-Identifier: Apache-2.0
# 🧪 Root Test Suite

These integration tests expect the `alpha_factory_v1` package to be importable.

## Setup

1. Install the development requirements:
   ```bash
   pip install -r requirements-dev.txt
   ```
2. Install the demo extras **required for the full suite**:
   ```bash
   pip install -r requirements-demo.txt
   ```
   This also installs `openai>=1.82.0,<2.0`, `openai-agents` and `google-adk` so
   the optional integration tests can run.
3. Verify the core dependencies are present:
   ```bash
   python scripts/check_python_deps.py
   ```
   This script checks for required libraries such as `numpy`, `pyyaml` and `pandas`.
   If any are missing, run:
   ```bash
   python check_env.py --auto-install
   ```
4. Ensure `numpy`, `pyyaml`, `pandas` and `prometheus_client` are installed.
   They ship with `requirements-dev.txt` but might be missing in minimal
   setups.
5. Install any missing optional packages:
   ```bash
   python check_env.py --auto-install
   ```
These commands download packages from PyPI, so ensure you have either
internet connectivity or a wheelhouse available via `--wheelhouse <dir>`
(or the `WHEELHOUSE` environment variable).
The full suite exercises features that depend on optional packages such as
`numpy`, `torch`, `pandas`, `prometheus_client`, `gymnasium`, `playwright`,
`httpx`, `uvicorn`, `git` and `hypothesis`.

Tests are skipped when `numpy` or `prometheus_client` are missing. The
`tests/conftest.py` helper checks for `torch` with `importlib.util.find_spec`
and registers a `requires_torch` marker. Tests using this marker are skipped
automatically when `torch` is absent. Pre-install these heavy dependencies with
`python check_env.py --auto-install`. Set the `WHEELHOUSE` environment
variable to point to a local wheel directory when running offline so this
command succeeds without contacting PyPI. `torch` in particular is heavy and
may take several minutes to install. When it is unavailable you can still run
a lightweight smoke check via:
```bash
pytest -m 'not e2e'
```
Running without a GPU is fully supported. The world model and evolution tests
fall back to CPU execution and are automatically skipped when `torch` is
absent. Other optional packages behave the same way—tests relying on
`fastapi`, `playwright` or `httpx` use `pytest.importorskip()` so the suite
continues even in minimal environments.
6. If the repository includes a `wheels/` directory, set `WHEELHOUSE=$(pwd)/wheels`
   before running the environment check or tests so packages install from the
   bundled wheelhouse.
7. Set `PYTHONPATH=$(pwd)` or install the project in editable mode with `pip install -e .`.
8. Before running the tests, execute `python check_env.py --auto-install` once
   more (add `--wheelhouse <dir>` when offline), then run `pytest -q`.
9. If `pre-commit` isn't found, install it with `pip install pre-commit` and run
   `pre-commit install` once to enable the git hooks referenced in
   [AGENTS.md](../AGENTS.md).

### Before running tests

Run these commands before executing the suite:

```bash
python scripts/check_python_deps.py
python check_env.py --auto-install  # add --wheelhouse <dir> when offline
```

`check_python_deps.py` frequently reports missing modules such as `numpy`, `yaml`
and `pandas`. Always run `python check_env.py --auto-install` after this check
to install any missing packages before executing `pytest`. Missing
dependencies will cause the suite to skip tests or fail entirely.

### Wheelhouse quick start

Build a local wheelhouse and run the environment check with `--wheelhouse` before
starting the tests:

```bash
mkdir -p wheels
pip wheel -r requirements.lock -w wheels
pip wheel -r requirements-dev.txt -w wheels
python check_env.py --auto-install --demo macro_sentinel --wheelhouse wheels
PYTHONPATH=$(pwd) pytest -q
```

See [alpha_factory_v1/scripts/README.md](../alpha_factory_v1/scripts/README.md#offline-setup)
for detailed steps. Skipping these commands typically leads to `pytest` errors
about missing modules.

### Offline quick start

Build wheels on a machine with connectivity and reuse them offline:

```bash
mkdir -p wheels
pip wheel -r requirements.txt -w wheels
pip wheel -r requirements-dev.txt -w wheels
pip wheel -r alpha_factory_v1/demos/aiga_meta_evolution/requirements.txt -w wheels
```

Copy the `wheels/` directory to the offline host and set `WHEELHOUSE`:

```bash
export WHEELHOUSE=/path/to/wheels
python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
PYTHONPATH=$(pwd) pytest -q
```

The environment check installs any missing packages from `WHEELHOUSE` so the
tests run without contacting PyPI.

### Offline install

Create a wheelhouse so the tests run without contacting PyPI. Build the wheels on
a machine with connectivity and copy the directory to the offline host. Include
`requirements.txt` and `requirements-dev.txt` (add the MuZero and Macro Sentinel
demo requirements if needed):

```bash
mkdir -p wheels
pip wheel -r requirements.txt -w wheels
pip wheel -r alpha_factory_v1/demos/muzero_planning/requirements.txt -w wheels
pip wheel -r alpha_factory_v1/demos/macro_sentinel/requirements.txt -w wheels
pip wheel -r requirements-dev.txt -w wheels
```

Install and run the tests without contacting PyPI:

```bash
WHEELHOUSE=$(pwd)/wheels pip install --no-index --find-links "$WHEELHOUSE" -r requirements-dev.txt
WHEELHOUSE=$(pwd)/wheels python check_env.py --auto-install --demo macro_sentinel --wheelhouse "$WHEELHOUSE"
PYTHONPATH=$(pwd) WHEELHOUSE="$WHEELHOUSE" pytest -q
```

The `check_env.py` command will fail offline unless `--wheelhouse` is provided.
Ensure the `WHEELHOUSE` environment variable points to your wheel directory
before running `pytest`.

Missing optional dependencies often cause failures. Re-run the environment check or pass `--wheelhouse` to install them offline.

### Air-gapped test run

With the wheelhouse prepared, execute the environment check and test suite while
offline:

```bash
export WHEELHOUSE=$(pwd)/wheels
python check_env.py --auto-install --demo macro_sentinel --wheelhouse "$WHEELHOUSE"
PYTHONPATH=$(pwd) pytest -q
```

`check_env.py` first looks for the `WHEELHOUSE` variable. When it is unset the
script falls back to installing from PyPI, which fails on hosts without network
access. `pytest` inherits the variable and will attempt the same fallback if
packages are missing, so always set `WHEELHOUSE` (or pass `--wheelhouse`) in
air‑gapped setups.

When running from the repository root without installation:

```bash
export PYTHONPATH=$(pwd)
python -m pytest -q tests
```

Alternatively install the package first:

```bash
pip install -e .
pytest -q
```
- Set PYTEST_NET_OFF=1 to skip tests that require outbound network access.
- Playwright test `test_umap_fallback.py` ensures the simulator uses random UMAP coordinates when Pyodide is blocked.
- The `test_bridge_online_mode` case in `test_meta_agentic_tree_search_demo.py` requires the `openai-agents` package. Set `OPENAI_API_KEY=dummy` and run:
```bash
OPENAI_API_KEY=dummy pytest tests/test_meta_agentic_tree_search_demo.py::test_bridge_online_mode
```
- `tests/test_aiga_agents_bridge.py` exercises the AI-GA bridge when
  `openai_agents` is installed:
```bash
pytest tests/test_aiga_agents_bridge.py
```
- The optional integration checks in `test_external_integrations.py` exercise
  the real `openai_agents` and `google_adk` packages. Install them via
  `requirements-demo.txt` or they will be skipped automatically.
- The meta-agentic tree search tests also rely on `numpy` and `pyyaml`. These packages are included in `requirements-dev.txt`, so running `pip install -r requirements-dev.txt` will install them.

### Experience demo tests

Run the Era‑of‑Experience checks without starting Docker:

```bash
pytest tests/test_experience_launcher.py tests/test_agent_experience_entrypoint.py
```

These tests verify the demo launcher script and the Python entrypoint with both OpenAI and Ollama settings.

## Troubleshooting

ImportErrors during test collection usually mean optional packages are missing.
Run:

```bash
python check_env.py --auto-install
```

Use `--wheelhouse <dir>` or set `WHEELHOUSE` when offline so packages
install from your local wheel cache.
