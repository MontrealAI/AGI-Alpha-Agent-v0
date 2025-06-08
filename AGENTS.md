# Contributor Guide

This repository contains the Alpha-Factory v1 package and demos.
The instructions below apply to all contributors and automated agents.

## Table of Contents

- [Development Environment](#development-environment)
- [Coding Style](#coding-style)
- [Pull Requests](#pull-requests)
- [Troubleshooting](#troubleshooting)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Wheel Signing](#wheel-signing)

All contributors must follow the [Code of Conduct](CODE_OF_CONDUCT.md).
Please report security vulnerabilities as described in our [Security Policy](SECURITY.md).
## Prerequisites
- Python 3.11 or 3.12 (**Python ≥3.11 and <3.13**)
- Docker and Docker Compose (Compose ≥2.5)
- Git
- Node.js 20 for the web client and browser demo. A `.nvmrc` is provided, so run
  `nvm use` before installing Node dependencies.
- Keep `package-lock.json` under version control so `npm ci` reproduces the same
  dependency tree.
- Run `python alpha_factory_v1/scripts/preflight.py` to validate these tools.

Confirm installed versions:
```bash
python --version
docker --version
docker compose version
git --version
```
Python must report 3.11 or 3.12 and Docker Compose must be at least 2.5.

## Development Environment
- Create and activate a Python 3.11 or 3.12 (**Python ≥3.11 and <3.13**) virtual
  environment before running the setup script. On Linux or macOS:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install pre-commit
  ```
  On Windows PowerShell:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -U pip
  pip install pre-commit
  ```
- The script `alpha_factory_v1/scripts/preflight.py` enforces this requirement.
- From the repository root, run `./codex/setup.sh` to install the project in editable mode
  with minimal runtime dependencies. This ensures all relative paths resolve correctly.
- After installation, run `pre-commit run --all-files` once to verify formatting and hooks.
### Offline Setup

Follow these steps when installing without internet access:

- Build wheels using the same Python version as your virtual environment:
  ```bash
  mkdir -p /media/wheels
  pip wheel -r requirements.txt -w /media/wheels
  pip wheel -r requirements-dev.txt -w /media/wheels
  ```

- Generate a deterministic lock file with hashes:
  ```bash
  pip-compile --generate-hashes --output-file requirements.lock requirements.txt
  ```

- Install from the lock file to reproduce identical environments:
  ```bash
  pip install -r requirements.lock
  ```

- Install from the wheelhouse (the setup script automatically sets
  `WHEELHOUSE` to the `wheels/` directory in the repository root when
  that directory exists):
  ```bash
  WHEELHOUSE=/media/wheels AUTO_INSTALL_MISSING=1 ./codex/setup.sh
  WHEELHOUSE=/media/wheels AUTO_INSTALL_MISSING=1 python check_env.py --auto-install --wheelhouse /media/wheels
  ```

- Verify package integrity:
  ```bash
  pip check
  python check_env.py --auto-install --wheelhouse /media/wheels
  ```

- The setup script exits with an error if neither network access nor a
  wheelhouse is available. Build a wheelhouse as shown above and rerun
  the command.

#### Colab Requirements

- Build wheels for `alpha_factory_v1/requirements-colab.txt`:
  ```bash
  pip wheel -r alpha_factory_v1/requirements-colab.txt -w /media/wheels
  ```
- Compile the lock file from the wheelhouse:
  ```bash
  pip-compile --no-index --find-links /media/wheels --generate-hashes \
      --output-file alpha_factory_v1/requirements-colab.lock \
      alpha_factory_v1/requirements-colab.txt
  ```
  The `verify-alpha-colab-requirements-lock` hook relies on this lock file.

 - See [`alpha_factory_v1/scripts/README.md`](alpha_factory_v1/scripts/README.md) for additional offline tips.
- Run `python scripts/check_python_deps.py` to quickly verify that `numpy`, `yaml` and `pandas` are installed. If it reports missing packages, execute `python check_env.py --auto-install` before running the tests. This step fetches packages from PyPI, so in air‑gapped setups you **must** pass `--wheelhouse <path>` or set `WHEELHOUSE` so `pip` installs from the local cache.
 - After setup, validate with `python check_env.py --auto-install`. This command reaches out to PyPI unless `--wheelhouse <path>` or the `WHEELHOUSE` environment variable is supplied. When working offline run `python check_env.py --auto-install --wheelhouse <path>` so optional packages install correctly.
- The unit tests rely on `fastapi`, `opentelemetry-api`, `openai-agents` and `google-adk`. `./codex/setup.sh` installs these packages automatically. When skipping the setup script, run
  `pip install -r requirements-dev.txt` or ensure `check_env.py` reports no
  missing packages before running `pytest`.
- Execute `pytest -q` (or `python -m alpha_factory_v1.scripts.run_tests`) and ensure the entire suite passes.
  If failures remain, document them in the PR description.
- When running tests directly from the repository without installation, set `PYTHONPATH`
  as described in [`tests/README.md`](tests/README.md): `export PYTHONPATH=$(pwd)`.
- For coverage metrics, run `pytest --cov` and aim for at least **80%** coverage.
- Tests marked with `@pytest.mark.e2e` are end-to-end. Skip them with
  `pytest -m 'not e2e'`.
- Test environment variables (see [`alpha_factory_v1/tests/README.md`](alpha_factory_v1/tests/README.md) for details):
  - `AF_MEMORY_DIR` – temporary memory path.
  - `PYTEST_CPU_SOFT_SEC` – CPU time limit.
  - `PYTEST_MEM_MB` – memory cap in MB.
  - `PYTEST_NET_OFF` – disable network access.
  - The sandbox runner `python -m alpha_factory_v1.backend.tools.local_pytest` enforces these limits.
- Run `python alpha_factory_v1/scripts/preflight.py` to confirm the Python version and required tools are available.
- Before the first launch, run `bash quickstart.sh --preflight` to check
  Docker availability, git, and required packages. After this
  verification, run `./quickstart.sh` to launch the project. The script
  creates the virtual environment and installs required dependencies
  automatically. See the [5‑Minute Quick‑Start](README.md#6-5-minute-quick-start)
  section in the README for more details.
- For a one-step build and launch, run
  `alpha_factory_v1/scripts/install_alpha_factory_pro.sh --deploy`.
  See [`alpha_factory_v1/scripts/README.md`](alpha_factory_v1/scripts/README.md)
  for additional options.
- On Windows or systems without Bash, run
  `python alpha_factory_v1/quickstart.py --preflight`.
- Copy `alpha_factory_v1/.env.sample` to `.env` and add secrets such as
  `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. Replace `NEO4J_PASSWORD=REPLACE_ME`
  with a strong secret— the orchestrator fails to start if this variable is
  missing or left at the default.
- **Never commit** `.env` or other secrets. See
  [`alpha_factory_v1/scripts/README.md`](alpha_factory_v1/scripts/README.md)
  for additional guidance.
- Verify `.env` is ignored by running `git status` (it should appear untracked).
  The repository's `.gitignore` already includes `.env`.
- Run `python tools/check_env_table.py` to ensure the table below matches
  `alpha_factory_v1/.env.sample`.

Before running `pytest` or `quickstart.sh`, copy `.env.sample` to `.env`,
fill in the required secrets and change `NEO4J_PASSWORD` from the sample value.
Load the environment variables with `set -a; source .env; set +a` (use the
PowerShell equivalent on Windows) so they are available to the tests and
scripts.

### Key Environment Variables
Store secrets in environment variables or Docker secrets instead of code to keep
them out of version control. The table below highlights the most common settings
(see [`alpha_factory_v1/.env.sample`](alpha_factory_v1/.env.sample) for the full
template). The sample file now lists every variable with its default value.

| Variable | Purpose | Default/Example |
|----------|---------|-----------------|
| `AF_TRACING` | Enable or disable tracing | `true` |
| `AF_MEMORY_DIR` | Working memory directory for tests and runtime | `/tmp/alphafactory` |
| `AGENT_WHEEL_PUBKEY` | Base64 ED25519 key verifying agent wheel signatures | _(none)_ |
| `AGENT_ERR_THRESHOLD` | Consecutive errors before quarantine | `3` |
| `AGENT_HOT_DIR` | Directory for hot-loaded agent wheels | `~/.alpha_agents` |
| `AGENT_HEARTBEAT_SEC` | Heartbeat interval in seconds | `10` |
| `AGENT_RESCAN_SEC` | Interval between wheel scans | `60` |
| `DISABLED_AGENTS` | Comma-separated list disables specific agents | _(none)_ |
| `OPENAI_API_KEY` | OpenAI credential (blank uses local Ollama Φ‑2) | _(empty)_ |
| `OPENAI_ORG_ID` | OpenAI organization ID | _(none)_ |
| `ANTHROPIC_API_KEY` | Anthropic credential | _(none)_ |
| `MISTRAL_API_KEY` | Mistral credential | _(none)_ |
| `TOGETHER_API_KEY` | Together credential | _(none)_ |
| `GOOGLE_API_KEY` | Optional speech/vision credential | _(none)_ |
| `POLYGON_API_KEY` | Polygon market data API | _(none)_ |
| `ALPACA_KEY_ID` | Alpaca trading API key | _(none)_ |
| `ALPACA_SECRET_KEY` | Alpaca trading API secret | _(none)_ |
| `BINANCE_API_KEY` | Binance trading API key | _(none)_ |
| `BINANCE_API_SECRET` | Binance trading API secret | _(none)_ |
| `IBKR_CLIENT_ID` | Interactive Brokers client ID | _(none)_ |
| `IBKR_CLIENT_SECRET` | Interactive Brokers client secret | _(none)_ |
| `FRED_API_KEY` | FRED economic data key | _(none)_ |
| `NEWSAPI_KEY` | News API key | _(none)_ |
| `NEO4J_URI` | Neo4j database URI | `bolt://neo4j:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Database password required by the orchestrator | `REPLACE_ME` |
| `LLM_PROVIDER` | LLM provider to use | `openai` |
| `MODEL_NAME` | Default model name | `gpt-4-turbo` |
| `PORT` | REST API port | `8000` |
| `PROM_PORT` | Prometheus exporter port | `9090` |
| `TRACE_WS_PORT` | Trace graph WebSocket port | `8088` |
| `AGENTS_RUNTIME_PORT` | OpenAI Agents runtime port | `5001` |
| `BUSINESS_HOST` | Base orchestrator URL for bridges | `"http://localhost:8000"` |
| `ALPHA_FACTORY_ENABLE_ADK` | Set to `true` to start the Google ADK gateway | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `API_TOKEN` | Bearer token for the demo API | `REPLACE_ME_TOKEN` |
| `API_RATE_LIMIT` | Requests per minute per IP | `60` |
| `API_CORS_ORIGINS` | Comma-separated CORS origins for the API | `*` |
| `ALPHA_KAFKA_BROKER` | Kafka broker address | _(none)_ |
| `ALPHA_DATA_DIR` | Base data directory | `/data` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP export endpoint | `http://tempo:4317` |
| `VC_SIGNING_KEY_PATH` | Path to signing key | `/run/secrets/ed25519_private.key` |
| `K8S_CPU_LIMIT` | Kubernetes CPU limit | `500m` |
| `K8S_MEM_LIMIT` | Kubernetes memory limit | `1Gi` |
| `TZ` | Time zone | `America/Toronto` |
| `AF_LLM_CACHE_SIZE` | Maximum in-memory LLM cache entries | `1024` |
| `AF_PING_INTERVAL` | Ping frequency in seconds (min 5) | `60` |
| `AF_DISABLE_PING_AGENT` | Set to `true` to disable the ping agent | _(none)_ |
| `ARCHIVE_PATH` | Darwin‑Archive SQLite file | `archive.db` |
| `ARCHIVE_DB` | API server results database | `archive.db` |
| `SOLUTION_ARCHIVE_PATH` | Path to solution archive | `solutions.duckdb` |
| `PROOF_THRESHOLD` | Minimum score to generate SNARK proof | `0.5` |

## Coding Style
- Use Python 3.11 or 3.12 (**Python ≥3.11 and <3.13**) and include type hints for public APIs.
- Indent with 4 spaces and keep lines under 120 characters.
- `.editorconfig` enforces UTF-8 encoding, LF line endings and the 120-character limit for Python and Markdown files.
- Provide concise [Google style](https://google.github.io/styleguide/pyguide.html#381-docstrings) docstrings
for modules, classes and functions.
- Format code with `black` (line length 120) and run `ruff` or `flake8` for linting, if available.
- `pyproject.toml` contains the configuration for `black`, `ruff` and `flake8`.
  Adjust lint settings there if needed.
- Ensure code is formatted before committing.
- Run `ruff` or `flake8` and `mypy --strict` before committing to enforce
  consistent style and type safety.
- Run `mypy --config-file mypy.ini .` (or `pyright`) with a **strict** configuration. The
  `mypy.ini` configuration file is located at the repository root.
- Install pre‑commit and set up the git hook:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # run once after installation
pre-commit run --files <paths>   # before each commit
```

  - Re-run `pre-commit run --all-files` whenever `requirements.txt`, `requirements-dev.txt`,
    `.pre-commit-config.yaml`, `pyproject.toml`, `mypy.ini`, or other lint configs change.
    **CI enforces these checks.**
  - After editing `src/utils/a2a.proto`, run `pre-commit run --files src/utils/a2a.proto`
    to regenerate and verify protobuf sources.
  - The configuration runs `black`, `ruff`, `flake8` and `mypy` using
    `mypy.ini`.
  - Hooks `verify-requirements-lock`, `verify-alpha-requirements-lock` and
    `verify-backend-requirements-lock` ensure each `requirements-lock` file
    matches its `requirements.txt`. They rely on `pip-tools`.
  - Hooks are configured in `.pre-commit-config.yaml` at the repository root.
  - Hook `eslint-insight-browser` lints the Insight browser demo. It runs `npm ci`
    in `alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1` before
    invoking `eslint`.
  - Hook `env-check` verifies Python packages are installed by running
    `scripts/check_python_deps.py` and `check_env.py --auto-install`.

#### Pre-commit in Air-Gapped Setups

If `pre-commit` fails with a network error such as `No route to host`,
build a wheelhouse and install hooks from there:

```bash
mkdir -p /media/wheels
pip wheel -r requirements-dev.txt -w /media/wheels
WHEELHOUSE=/media/wheels pre-commit run --all-files
```

Set `WHEELHOUSE` to the directory containing wheels so `pre-commit` can
install dependencies without internet access.

## Pull Requests
- Keep commits focused and descriptive. Use meaningful commit messages.
- Ensure `git status` shows a clean working tree before committing.
- Remove stray build artifacts with `git clean -fd` if needed.
 - Run `python scripts/check_python_deps.py` followed by
    `python check_env.py --auto-install` (use `--wheelhouse <path>` when offline)
    and `pytest -q` before committing. Document any remaining test failures in
    the PR description.
- See [tests/README.md](tests/README.md) for details on running the suite locally,
  including setting `PYTHONPATH` or installing in editable mode.
- Summarize your changes and test results in the PR body.
- Title PRs using `[alpha_factory] <Title>`.
- Refer to [docs/CHANGELOG.md](docs/CHANGELOG.md) for release notes.
- All contributions are licensed under Apache 2.0 by default.
- Some files retain existing MIT license headers; keep whatever license a file
  already declares when editing it.
- Add an Apache 2.0 header to new source files unless another license is
  explicitly stated.
  ```
  # SPDX-License-Identifier: Apache-2.0
  ```
- Issue reports should follow the templates under [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/).
- Pull requests should follow [`pull_request_template.md`](.github/pull_request_template.md). Fill out
  all sections to confirm linting, type checks and tests pass.
- Ensure `pre-commit` passes locally; the CI pipeline runs the same hooks and will fail if they do not.

### Starting the CI Pipeline
You can manually trigger the CI run from the GitHub UI:

1. Navigate to "Actions → 🚀 CI — Insight Demo".
2. Click "Run workflow," type `RUN`, and confirm.

The pipeline validates linting, type checks, tests and the Docker build.

### Deploy to Kind
The **Deploy — Kind** workflow provisions a local kind cluster, builds the Insight demo image, installs the Helm chart with default values, applies Terraform from `infrastructure/terraform` using the local backend and waits for pods to become ready. Repository settings mark this workflow as **required**.

1. Navigate to "Actions → 🚀 Deploy — Kind".
2. Click "Run workflow" to launch the deployment.

### PR Message Guidelines
- Keep the subject line concise and under 72 characters.
- Optionally include a short body explaining the rationale.
- Consider using a simplified Conventional Commits prefix such as
  `feat:`, `fix:` or `docs:` to ease changelog generation.

### Troubleshooting
- If the stack fails to start, verify Docker and Docker Compose are running.
- Setup errors usually mean Python is older than 3.11. Use Python 3.11 or 3.12 (>=3.11,<3.13).
- Missing optional packages can cause test failures; first run
  `python scripts/check_python_deps.py` and then
  `python check_env.py --auto-install` (pass `--wheelhouse <path>` when offline)
  if required.
- Always execute `python check_env.py --auto-install` before running the tests
  or `pre-commit` so optional dependencies install correctly. When offline,
  provide `--wheelhouse <dir>` or set `WHEELHOUSE` to your wheel cache.
- If `pre-commit` reports "command not found", install it manually with
  `pip install pre-commit` and run `pre-commit install` once.

For detailed troubleshooting steps, see [`alpha_factory_v1/scripts/README.md`](alpha_factory_v1/scripts/README.md).

### Wheel Signing
All agent wheels must be signed with the project's ED25519 key before they are
loaded from `$AGENT_HOT_DIR`. **OpenSSL** must be installed to sign and verify
wheels. Install it with `brew install openssl` on macOS or grab the
[OpenSSL Windows binaries](https://slproweb.com/products/Win32OpenSSL.html).

1. **Generate the key** and capture the base64 public key:
   ```bash
   openssl genpkey -algorithm ed25519 -out agent_signing.key
   openssl pkey -in agent_signing.key -pubout -outform DER | base64 -w0
   ```
   Store `agent_signing.key` **outside** the repository and never commit it.

2. **Store the public key** in the `AGENT_WHEEL_PUBKEY` environment variable so
   `alpha_factory_v1/backend/agents/__init__.py` can verify signatures.

3. **Sign `<wheel>.whl` to create `<wheel>.whl.sig`:**
   ```bash
   openssl dgst -sha512 -binary <wheel>.whl |
     openssl pkeyutl -sign -inkey agent_signing.key |
     base64 -w0 > <wheel>.whl.sig
   ```
   Keep `<wheel>.whl.sig` next to the wheel inside `$AGENT_HOT_DIR`.

4. **Add the signature** file to the repository and include the base64 value in
   `_WHEEL_SIGS` within `alpha_factory_v1/backend/agents/__init__.py`. Wheels
   without a valid signature are ignored at runtime.

### Verify the wheel
Verify that `<wheel>.whl.sig` matches the wheel:

```bash
openssl dgst -sha512 -binary <wheel>.whl |
  openssl pkeyutl -verify -pubin -inkey "$AGENT_WHEEL_PUBKEY" -sigfile <wheel>.whl.sig
```

Alternatively run the bundled helper:

```bash
verify-wheel-sig path/to/agent.whl
```

On Windows PowerShell:

```powershell
Get-Content <wheel>.whl -Encoding Byte |
  openssl dgst -sha512 -binary |
  openssl pkeyutl -verify -pubin -inkey $env:AGENT_WHEEL_PUBKEY -sigfile <wheel>.whl.sig
```

The orchestrator validates signatures against `_WHEEL_PUBKEY` in `alpha_factory_v1/backend/agents/__init__.py`.
