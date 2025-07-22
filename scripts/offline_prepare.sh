#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build wheels and compile lock files for offline installation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<USAGE
Usage: $0

Build the offline wheelhouse and regenerate all lock files.
Run this on a machine with internet access and copy the 'wheels/'
directory to the offline host. Set WHEELHOUSE=\"\$(pwd)/wheels\" before
running './codex/setup.sh' or 'python check_env.py --auto-install'.
USAGE
}

if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
  usage
  exit 0
fi

"$SCRIPT_DIR/build_offline_wheels.sh"

if command -v pip-compile >/dev/null; then
  PIP_COMPILE=pip-compile
else
  PIP_COMPILE="python -m piptools compile"
fi

opts=(--generate-hashes --quiet --allow-unsafe)
if [[ -n "${WHEELHOUSE:-}" ]]; then
  opts+=(--no-index --find-links "$WHEELHOUSE")
fi

run_compile() {
  local req=$1 lock=$2
  $PIP_COMPILE "${opts[@]}" "$req" -o "$lock"
}

run_compile requirements.txt requirements.lock
run_compile requirements-demo.txt requirements-demo.lock
run_compile alpha_factory_v1/requirements.txt alpha_factory_v1/requirements.lock
run_compile alpha_factory_v1/requirements-colab.txt alpha_factory_v1/requirements-colab.lock
run_compile alpha_factory_v1/backend/requirements.txt alpha_factory_v1/backend/requirements-lock.txt

for req in alpha_factory_v1/demos/*/requirements.txt; do
  lock="${req%txt}lock"
  if [[ -f "$lock" ]]; then
    run_compile "$req" "$lock"
  fi
done

echo "Offline wheelhouse and lock files ready."
usage
