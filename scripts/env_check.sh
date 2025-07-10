#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Verify core Python packages are present before running the full environment
# check. ``check_python_deps.py`` now relies on ``python -m pip show`` for
# speed and reliability.
set -euo pipefail

# Optionally set WHEELHOUSE to a directory with wheels for offline installs.
# The script forwards "--wheelhouse" when defined.

# When running in CI, ignore missing optional packages so the
# environment check can attempt automatic installation.
if [[ "${CI:-}" == "true" ]]; then
    python scripts/check_python_deps.py || true
else
    python scripts/check_python_deps.py
fi

env_opts=()
if [[ -n "${WHEELHOUSE:-}" ]]; then
    if [[ ! -d "$WHEELHOUSE" ]]; then
        echo "WHEELHOUSE directory '$WHEELHOUSE' does not exist" >&2
        exit 1
    fi
    env_opts=(--wheelhouse "$WHEELHOUSE")
fi

python check_env.py --auto-install "${env_opts[@]}"
