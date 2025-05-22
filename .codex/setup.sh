#!/usr/bin/env bash
# Robust setup script for Codex development environments.
set -euo pipefail

wheelhouse=${WHEELHOUSE:-}

python -m pip install --upgrade pip

base_pkgs=(
    'pydantic<2'
    pytest
    openai
    anthropic
    prometheus_client
)

if [[ -n "${wheelhouse}" ]]; then
    python -m pip install --no-index --find-links "${wheelhouse}" "${base_pkgs[@]}"
else
    python -m pip install "${base_pkgs[@]}"
fi

# Install optional extras when available but continue on failure.
python check_env.py --auto-install || true

# Install the repository in editable mode.
python -m pip install -e .
