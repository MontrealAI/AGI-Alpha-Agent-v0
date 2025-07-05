#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
BROWSER_DIR="$ROOT/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
# Install npm dependencies deterministically
npm --prefix "$BROWSER_DIR" ci >/dev/null
# Run eslint on provided file paths using the flat config
ESLINT_USE_FLAT_CONFIG=true npx --prefix "$BROWSER_DIR" eslint \
    --config "$BROWSER_DIR/eslint.config.js" \
    --ignore-path "$BROWSER_DIR/.eslintignore" "$@" || {
    patterns=$(grep -v '^\s*$' "$BROWSER_DIR/.eslintignore" \
        | sed 's/^/--ignore-pattern /' | tr '\n' ' ')
    ESLINT_USE_FLAT_CONFIG=true npx --prefix "$BROWSER_DIR" eslint \
        --config "$BROWSER_DIR/eslint.config.js" "$patterns" "$@"
}
