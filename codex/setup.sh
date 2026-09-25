#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

PYTHON=${PYTHON:-python3}

# A checkout includes wheels/README.md; only use it as an offline wheelhouse
# when it actually contains distributions. An explicitly configured wheelhouse
# remains offline and must never silently fall back to the public index.
if [[ -z "${WHEELHOUSE:-}" ]]; then
  default_wheelhouse="$(dirname "$0")/../wheels"
  if compgen -G "$default_wheelhouse/*.whl" > /dev/null; then
    export WHEELHOUSE="$default_wheelhouse"
  fi
fi

# Support offline installation via WHEELHOUSE
wheel_opts=()
if [[ -n "${WHEELHOUSE:-}" ]]; then
  if ! compgen -G "$WHEELHOUSE/*.whl" > /dev/null; then
    echo "ERROR: WHEELHOUSE must contain wheel files: $WHEELHOUSE" >&2
    exit 1
  fi
  wheel_opts+=(--no-index --find-links "$WHEELHOUSE")
fi

# Let pip use its configured index, certificate store and proxy. A direct TCP
# probe to pypi.org incorrectly rejects supported mirror/proxy installations.

# Upgrade pip and core build tools
$PYTHON -m pip install --quiet "${wheel_opts[@]}" --upgrade 'pip<26' setuptools wheel

# Install pip-compile (pip-tools) early so hooks can verify lock files
$PYTHON -m pip install --quiet "${wheel_opts[@]}" pip-tools

# Ensure Node.js 22+ is available for the Insight Browser demo
node_major=$(node -v | sed 's/v\([0-9]*\).*/\1/')
if (( node_major < 22 )); then
  echo "ERROR: Node.js 22+ is required. Run 'nvm use' to switch versions." >&2
  exit 1
fi

# Ensure pre-commit 4.2.0 is available for git hooks
required_pre_commit=4.2.0
current_pre_commit=""
if command -v pre-commit >/dev/null; then
  current_pre_commit=$(pre-commit --version | awk '{print $2}')
fi
if [[ -z "$current_pre_commit" || "$current_pre_commit" != "$required_pre_commit" ]]; then
  echo "Installing pre-commit==$required_pre_commit" >&2
  $PYTHON -m pip install --quiet "${wheel_opts[@]}" pre-commit=="$required_pre_commit"
fi

# Install package in editable mode
$PYTHON -m pip install --quiet "${wheel_opts[@]}" -e .


# When FULL_INSTALL=1, install the fully pinned dependencies from the
# deterministic lock file. This path also supports offline installs via a
# wheelhouse. Otherwise install a minimal set of runtime packages for fast
# setup in networked environments.
if [[ "${FULL_INSTALL:-0}" == "1" ]]; then
  $PYTHON -m pip install --quiet "${wheel_opts[@]}" -r requirements.lock -r requirements-dev.lock
elif [[ "${MINIMAL_INSTALL:-0}" == "1" ]]; then
  packages=(
    pytest
    pytest-benchmark
    prometheus_client
    mypy
    openai
    openai-agents
    google-adk
    anthropic
    fastapi
    opentelemetry-api
    grpcio
    grpcio-tools
    httpx
    uvicorn
    cryptography
    hypothesis
    pytest-httpx
    numpy
    pandas
    "gymnasium[classic-control]"
    playwright
    plotly
    websockets
    click
    requests
  )
  # Deduplicate packages to avoid extra install noise
  mapfile -t packages < <(printf '%s\n' "${packages[@]}" | sort -u)
  $PYTHON -m pip install --quiet "${wheel_opts[@]}" "${packages[@]}"
else
  packages=(
    accelerate
    aiohttp
    anthropic
    backoff
    better-profanity
    ccxt
    chromadb
    click
    cryptography
    ctransformers
    deap
    faiss-cpu
    fastapi
    feedparser
    flask
    gitpython
    google-adk
    grpcio
    grpcio-tools
    gunicorn
    httpx
    litellm
    llama-cpp-python
    neo4j
    networkx
    newsapi-python
    noaa-sdk
    numpy
    openai
    openai-agents
    opentelemetry-api
    opentelemetry-sdk
    orjson
    ortools
    pandas
    "gymnasium[classic-control]"
    playwright
    plotly
    prometheus-client
    psycopg2-binary
    pydantic
    pydantic-settings
    pytest
    python-dotenv
    requests
    rich
    rocketry
    scipy
    sentence-transformers
    sentencepiece
    streamlit
    tiktoken
    transformers
    'uvicorn[standard]'
    websockets
    yfinance
  )
  packages+=(
    pytest-benchmark
    pytest-httpx
    hypothesis
    grpcio-tools
    grpcio
    requests
    pydantic-settings
  )
  # Deduplicate packages to avoid extra install noise
  mapfile -t packages < <(printf '%s\n' "${packages[@]}" | sort -u)
  $PYTHON -m pip install --quiet "${wheel_opts[@]}" "${packages[@]}"
fi

# Validate environment and install any remaining deps
check_env_opts=()
if [[ -n "${WHEELHOUSE:-}" ]]; then
  check_env_opts+=(--wheelhouse "$WHEELHOUSE")
fi
# FULL_INSTALL is the locked development baseline. Heavy model extras remain
# available through the explicitly supplied ALPHA_FACTORY_FULL=1 flag; do not
# replace a pinned install with an unbounded second dependency resolution.
$PYTHON check_env.py --auto-install "${check_env_opts[@]}"

# Verify all dependencies are satisfied and abort on issues
$PYTHON -m pip check

# Fetch browser demo assets
if [[ "${FETCH_BROWSER_ASSETS:-1}" != "0" ]]; then
  echo "Fetching Insight browser assets..."
  $PYTHON scripts/fetch_assets.py
fi

# Set up pre-commit hooks if available
if command -v pre-commit >/dev/null; then
  pre-commit install
fi
