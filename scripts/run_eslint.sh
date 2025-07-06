#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
BROWSER_DIR="$ROOT/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
LOCK_FILE="$BROWSER_DIR/package-lock.json"
CHECK_FILE="$BROWSER_DIR/node_modules/.package_lock_checksum"

# Install npm dependencies deterministically when needed
lock_hash="$(sha256sum "$LOCK_FILE" | awk '{print $1}')"
if [ ! -d "$BROWSER_DIR/node_modules" ] || [ ! -f "$CHECK_FILE" ] || [ "$(cat "$CHECK_FILE" 2>/dev/null)" != "$lock_hash" ]; then
    npm --prefix "$BROWSER_DIR" ci >/dev/null
    echo "$lock_hash" > "$CHECK_FILE"
fi
cd "$BROWSER_DIR"
args=()
for f in "$@"; do
    args+=("$(realpath --relative-to=. "$ROOT/$f")")
done
ESLINT_USE_FLAT_CONFIG=true npx eslint --no-warn-ignored --config eslint.config.js "${args[@]}"
