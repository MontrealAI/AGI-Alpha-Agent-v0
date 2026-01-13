#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
BROWSER_DIR="$ROOT/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
LOCK_FILE="$BROWSER_DIR/package-lock.json"
CHECK_FILE="$BROWSER_DIR/node_modules/.package_lock_checksum"

# Enforce the Node version declared in the repo root so installs behave the same
# locally and in CI. The hook intentionally avoids fetching a new runtime to
# keep executions fast; callers should run `nvm use` beforehand.
if [[ -f "$ROOT/.nvmrc" ]]; then
    required_node="$(<"$ROOT/.nvmrc")"
    current_node="$(node -v 2>/dev/null || echo "")"
    if [[ -z "$current_node" || "$current_node" != v${required_node}* ]]; then
        echo "error: Node.js ${required_node} is required. Run 'nvm use' before linting." >&2
        exit 1
    fi
fi

if [[ ! -d "$BROWSER_DIR/node_modules" ]]; then
    echo "error: Insight Browser dependencies missing. Run npm ci in $BROWSER_DIR." >&2
    exit 1
fi

expected_checksum="$(sha256sum "$LOCK_FILE" | awk '{print $1}')"
if [[ -f "$CHECK_FILE" ]]; then
    current_checksum="$(<"$CHECK_FILE")"
    if [[ "$current_checksum" != "$expected_checksum" ]]; then
        echo "error: Insight Browser node_modules out of date. Run npm ci in $BROWSER_DIR." >&2
        exit 1
    fi
else
    echo "$expected_checksum" > "$CHECK_FILE"
fi
cd "$BROWSER_DIR"
args=()
for f in "$@"; do
    args+=("$(realpath --relative-to=. "$ROOT/$f")")
done
eslint_bin="$BROWSER_DIR/node_modules/.bin/eslint"
if [[ ! -x "$eslint_bin" ]]; then
    echo "error: ESLint is missing. Run npm ci in $BROWSER_DIR." >&2
    exit 1
fi
ESLINT_USE_FLAT_CONFIG=true "$eslint_bin" --no-warn-ignored --config eslint.config.js "${args[@]}"
