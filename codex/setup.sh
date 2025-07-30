#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

PYTHON=${PYTHON:-python3}

# Default to a wheelhouse next to the repository root when available
if [[ -z "${WHEELHOUSE:-}" ]]; then
  default_wheelhouse="$(dirname "$0")/../wheels"
  if [[ -d "$default_wheelhouse" ]]; then
    export WHEELHOUSE="$default_wheelhouse"
  fi
fi

# Support offline installation via WHEELHOUSE
wheel_opts=()
if [[ -n "${WHEELHOUSE:-}" ]]; then
  wheel_opts+=(--no-index --find-links "$WHEELHOUSE")
fi

# Abort early when offline and no wheelhouse is provided
if [[ -z "${WHEELHOUSE:-}" ]]; then
  if ! $PYTHON - <<'EOF'
import socket, sys
try:
    socket.create_connection(("pypi.org", 443), timeout=3)
except Exception:
    sys.exit(1)
EOF
  then
    echo "ERROR: No network access detected. Re-run with '--wheelhouse <dir>' to install packages from local wheels." >&2
    exit 1
  fi
fi

# Upgrade pip and core build tools
$PYTHON -m pip install --quiet "${wheel_opts[@]}" --upgrade pip setuptools wheel

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
current_pre_commit=$(command -v pre-commit >/dev/null && pre-commit --version 2>/dev/null | awk '{print $2}')
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
  $PYTHON -m pip install --quiet "${wheel_opts[@]}" -r requirements.lock
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
if [[ "${FULL_INSTALL:-0}" == "1" ]]; then
  export ALPHA_FACTORY_FULL=1
fi
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

