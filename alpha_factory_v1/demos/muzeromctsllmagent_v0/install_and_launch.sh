#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$demo_dir/../../.." && pwd)"
if [[ "${1:-}" == "--help" ]]; then
  printf '%s\n' 'Install the hash-locked Linux x86_64 CPU profile, then launch on localhost:7862.' \
    'Usage: install_and_launch.sh [--headless] [--episodes N] [--output NEW.json]' \
    'Python 3.11–3.13 required. Uses .venv-mcts-llm in the repository; never writes to your current directory.'
  exit 0
fi
python_bin="${PYTHON:-python3}"
"$python_bin" -c 'import sys,platform; assert (3,11) <= sys.version_info[:2] < (3,14), "Python 3.11–3.13 required"; assert platform.system() == "Linux" and platform.machine() == "x86_64", "This locked installer supports Linux x86_64; see README for other platforms"'
venv="$repo_dir/.venv-mcts-llm"
if [[ ! -d "$venv" ]]; then
  "$python_bin" -m venv "$venv"
fi
"$venv/bin/python" -m pip install --require-hashes -r "$demo_dir/../muzero_planning/requirements.lock"
"$venv/bin/python" -m pip check
cd -- "$repo_dir"
exec "$venv/bin/python" -m alpha_factory_v1.demos.muzeromctsllmagent_v0 "$@"
