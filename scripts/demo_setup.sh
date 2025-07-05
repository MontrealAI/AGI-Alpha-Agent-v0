#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Simple demo setup helper
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

usage() {
  cat <<EOF
Usage: $0

Prepare the demo virtual environment. Set WHEELHOUSE to a directory
with wheels for offline installation.
EOF
}

if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
  usage
  exit 0
fi

if [[ -z "${WHEELHOUSE:-}" && -d wheels ]]; then
  WHEELHOUSE="$(pwd)/wheels"
  export WHEELHOUSE
fi
PIP_ARGS=()
if [[ -n "${WHEELHOUSE:-}" ]]; then
  PIP_ARGS=(--no-index --find-links "$WHEELHOUSE")
fi

VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install "${PIP_ARGS[@]}" -U pip
fi
"$VENV_DIR/bin/pip" install "${PIP_ARGS[@]}" -r requirements.txt -r requirements-dev.txt
env_opts=()
if [[ -n "${WHEELHOUSE:-}" ]]; then
  env_opts+=(--wheelhouse "$WHEELHOUSE")
fi
"$VENV_DIR/bin/python" check_env.py --auto-install "${env_opts[@]}"
echo "Demo environment ready. Activate via 'source $VENV_DIR/bin/activate'"
