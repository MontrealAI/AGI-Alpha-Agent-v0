#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
BROWSER_DIR="$ROOT/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
# Install npm dependencies deterministically
npm --prefix "$BROWSER_DIR" ci >/dev/null
# Build ignore arguments from the .eslintignore file
mapfile -t ignore_patterns < <(grep -v '^\s*$' "$BROWSER_DIR/.eslintignore")
args=()
for p in "${ignore_patterns[@]}"; do
    args+=(--ignore-pattern "$p")
done

# Run eslint using the flat config
ESLINT_USE_FLAT_CONFIG=true npx --prefix "$BROWSER_DIR" eslint \
    --config "$BROWSER_DIR/eslint.config.js" "${args[@]}" "$@"
