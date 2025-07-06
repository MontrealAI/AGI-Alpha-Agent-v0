#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
BROWSER_DIR="$ROOT/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
# Install npm dependencies deterministically
# Install npm dependencies deterministically
npm --prefix "$BROWSER_DIR" ci >/dev/null
cd "$BROWSER_DIR"
args=()
for f in "$@"; do
    args+=("$(realpath --relative-to=. "$ROOT/$f")")
done
ESLINT_USE_FLAT_CONFIG=true npx eslint --config eslint.config.js "${args[@]}"
