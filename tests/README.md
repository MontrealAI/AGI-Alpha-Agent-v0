[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# SPDX-License-Identifier: Apache-2.0
# 🧪 Root Test Suite

Tests require internet connectivity to fetch missing dependencies or a local
wheelhouse built with `scripts/build_offline_wheels.sh`. Always run
`python check_env.py --auto-install --wheelhouse <dir>` before `pytest` so the
environment can install packages from the wheel cache when offline.
Running `check_env.py` or the tests without network access will fail unless this wheelhouse is present.

These integration tests expect the `alpha_factory_v1` package to be importable.

When running the suite without internet access you **must** prepare a local
wheelhouse first:

```bash
./scripts/build_offline_wheels.sh
```

Copy the resulting `wheels/` directory to the offline host and set
`WHEELHOUSE=$(pwd)/wheels` before executing `python check_env.py --auto-install`
or `pytest`. The environment check in `tests/conftest.py` will abort when neither
network access nor a wheelhouse is available.

## Running tests online vs. offline

When internet connectivity is available run:

```bash
python check_env.py --auto-install
pytest -q
```

To execute the suite offline, first build a wheelhouse and export its path:

```bash
./scripts/build_offline_wheels.sh
export WHEELHOUSE=$(pwd)/wheels
python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
pytest -q
```


## Setup

1. Install the development requirements:
   ```bash
   pip install -r requirements-dev.txt
   ```
2. Install the demo extras **required for the full suite**:
   ```bash
   pip install -r requirements-demo.txt
   ```
   `requirements-demo.txt` pulls in `openai_agents>=0.0.17`, `gymnasium` and
   `google_adk` together with `openai>=1.82.0,<2.0`. These packages are required
   for running **all** tests, not just the optional integration checks.
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
   Run this command **after** installing the extras so `openai_agents`,
   `gymnasium` and `google_adk` are available for the tests.
6. **Before running `pytest`, execute `python check_env.py --auto-install` again**
   to ensure optional modules are installed. When working offline add
   `--wheelhouse <dir>` (or set `WHEELHOUSE`) so packages install from the
   local wheel cache. Skipping this step can lead to missing modules during
   test collection.

### Quick health check

Run the smoke tests to confirm the core dependencies work:

```bash
pytest tests/test_ping_agent.py tests/test_af_requests.py -q
```
These commands download packages from PyPI, so ensure you have either
internet connectivity or a wheelhouse available via `--wheelhouse <dir>`
(or the `WHEELHOUSE` environment variable).
The full suite exercises features that depend on optional packages such as
`numpy`, `torch`, `pandas`, `prometheus_client`, `gymnasium`, `playwright`,
`httpx`, `uvicorn`, `git`, `hypothesis` and `requests_mock`.

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
pytest tests/test_ping_agent.py tests/test_af_requests.py -q
```
Running without a GPU is fully supported. The world model and evolution tests
fall back to CPU execution and are automatically skipped when `torch` is
absent. Other optional packages behave the same way—tests relying on
`fastapi`, `playwright` or `httpx` use `pytest.importorskip()` so the suite
continues even in minimal environments.

### Environment variables and services

Before running `pytest`, export a few variables so the orchestrator tests have
defaults to work with:

```bash
export API_TOKEN=test-token
export NEO4J_PASSWORD=test-password
export DEV_MODE=true
```

Docker **must** be available for the full suite. Some checks start containers
using the Compose file under `infrastructure/`. Launch the stack when required:

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

The lightweight smoke tests run without these services:

```bash
pytest tests/test_ping_agent.py tests/test_af_requests.py -q
```

They simply verify that the core package imports succeed.
6. Build the wheelhouse on a machine with connectivity **(mandatory when offline)**:
   ```bash
   ./scripts/build_offline_wheels.sh
   ```
   Copy the resulting `wheels/` directory to the offline host and export
   `WHEELHOUSE=$(pwd)/wheels` **before running** `python check_env.py --auto-install`
   or `pytest` so packages install from the bundled wheels.
   Bundling small wheels such as `numpy`, `pyyaml` and `pandas` allows the smoke
   tests to run without contacting PyPI.
7. Set `PYTHONPATH=$(pwd)` or install the project in editable mode with `pip install -e .`.
8. Add the Insight demo source path so the orchestrator can import its agent modules:
   ```bash
   export PYTHONPATH="$(pwd)/alpha_factory_v1/demos/alpha_agi_insight_v1/src:$PYTHONPATH"
   ```
9. Include the stub modules in `tests/resources` on your `PYTHONPATH` so CLI
   subprocess tests can import the lightweight `rocketry` replacement:
   ```bash
   export PYTHONPATH="$(pwd)/tests/resources:$PYTHONPATH"
   ```
10. Export the wheel cache path and run the environment check before the suite:
   ```bash
   export WHEELHOUSE=/path/to/wheels
   python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
   PYTHONPATH=$(pwd) pytest -q
   ```
11. Without a wheelhouse or network access the environment check fails and
   `tests/conftest.py` skips the entire suite with a concise "no network and no
   wheelhouse" message. Provide `--wheelhouse <dir>` (or set `WHEELHOUSE`) to run
   the tests offline. Preparing this directory via `scripts/build_offline_wheels.sh`
   is therefore a mandatory prerequisite when testing in air‑gapped setups.
12. If `pre-commit` isn't found, install it with `pip install pre-commit==4.2.0` and run
   `pre-commit install` once to enable the git hooks referenced in
   [AGENTS.md](../AGENTS.md).
13. Build the web assets so `dist/sw.js` exists:
   ```bash
   make build_web  # or run npm run build in insight_browser_v1
   ```
   Failing to generate this file causes `tests/test_cache_version.py` to fail.

### Wheelhouse requirement

Offline environments must provide a directory of wheels so `check_env.py` and
`pytest` can install packages without contacting PyPI. Build the wheelhouse
from `requirements.lock` and point `WHEELHOUSE` to it before running the tests.
Example:

```bash
mkdir -p wheels
pip wheel -r requirements.lock -w wheels
WHEELHOUSE=$(pwd)/wheels python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
PYTHONPATH=$(pwd) WHEELHOUSE="$WHEELHOUSE" pytest tests/test_ping_agent.py tests/test_af_requests.py -q
```

Tests may skip when optional dependencies are unavailable.

### Before running tests

Run these commands before executing the suite:

```bash
python scripts/check_python_deps.py
python check_env.py --auto-install  # add --wheelhouse <dir> when offline
# offline example using the bundled wheelhouse
export WHEELHOUSE=$(pwd)/wheels
python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
```

When working offline, always export `WHEELHOUSE=$(pwd)/wheels` and run
`python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"` before executing
`pytest`. This matches the instructions in [AGENTS.md](../AGENTS.md).

`check_python_deps.py` frequently reports missing modules such as `numpy`, `yaml`
and `pandas`. Always run `python check_env.py --auto-install` after this check
to install any missing packages before executing `pytest`. Missing
dependencies will cause the suite to skip tests or fail entirely.

### Wheelhouse quick start

Build a local wheelhouse and run the environment check with `--wheelhouse` before
starting the tests. The `scripts/build_offline_wheels.sh` helper collects wheels for
`requirements.lock`, `requirements-dev.txt`, `requirements-demo.lock` and each
demo's lock file:

```bash
./scripts/build_offline_wheels.sh
python check_env.py --auto-install --demo macro_sentinel --wheelhouse wheels
PYTHONPATH=$(pwd) pytest -q
```
Always run `scripts/build_offline_wheels.sh` before executing the environment check and tests.

See [alpha_factory_v1/scripts/README.md](../alpha_factory_v1/scripts/README.md#offline-setup)
for detailed steps. Skipping these commands typically leads to `pytest` errors
about missing modules.

### Offline quick start

Build wheels on a machine with connectivity and reuse them offline. The easiest
way is to run `./scripts/build_offline_wheels.sh`, which downloads wheels for all
locked requirements:

```bash
./scripts/build_offline_wheels.sh
```
Run this once before calling `check_env.py --auto-install --wheelhouse "$WHEELHOUSE"` or running the tests offline.
Run this once before invoking `check_env.py --auto-install --wheelhouse "$WHEELHOUSE"` and `pytest`.

Copy the `wheels/` directory to the offline host and set `WHEELHOUSE`:

```bash
export WHEELHOUSE=/path/to/wheels
python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
PYTHONPATH=$(pwd) WHEELHOUSE="$WHEELHOUSE" pytest -q
```

The environment check installs any missing packages from `WHEELHOUSE` so the
tests run without contacting PyPI.

### Offline install

Create a wheelhouse so the tests run without contacting PyPI. Build the wheels on
a machine with connectivity and copy the directory to the offline host. The
`scripts/build_offline_wheels.sh` script generates all necessary wheels from the lock
files including the MuZero and Macro Sentinel demos:

```bash
./scripts/build_offline_wheels.sh
```
Run this once before calling `check_env.py --auto-install --wheelhouse "$WHEELHOUSE"` or running the tests offline.

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
- Set SKIP_WEBKIT_TESTS=1 if `npx playwright install` cannot download WebKit.
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
- `tests/test_rate_lock.py` checks the request rate limiter and
  skips automatically when `openai_agents` is missing.
- `alpha_factory_v1/tests/test_cross_industry_alpha.py` exercises the
  cross‑industry discovery helper:
```bash
pytest alpha_factory_v1/tests/test_cross_industry_alpha.py
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
