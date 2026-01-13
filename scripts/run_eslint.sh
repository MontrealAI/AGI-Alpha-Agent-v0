#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
BROWSER_DIR="$ROOT/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
LOCK_FILE="$BROWSER_DIR/package-lock.json"
CHECK_FILE="$BROWSER_DIR/node_modules/.package_lock_checksum"
NPM_CACHE="$BROWSER_DIR/.npm-cache"

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

# Always reinstall dependencies for a clean tree
chmod -R u+w "$BROWSER_DIR/node_modules" 2>/dev/null || true
rm -rf "$BROWSER_DIR/node_modules"
rm -rf "$NPM_CACHE"
npm --prefix "$BROWSER_DIR" cache clean --force >/dev/null
# Skip postinstall scripts (e.g., esbuild binary downloads) to keep lint-only
# installs lightweight and resilient in CI environments. Use a private cache to
# avoid cross-job corruption on shared runners. Retry once to tolerate transient
# npm filesystem errors on shared CI hosts.
attempt=1
max_attempts=2
while true; do
    if NPM_CONFIG_CACHE="$NPM_CACHE" npm --prefix "$BROWSER_DIR" ci --ignore-scripts --no-progress >/dev/null; then
        break
    fi
    if [[ "$attempt" -ge "$max_attempts" ]]; then
        echo "error: npm ci failed after ${attempt} attempts." >&2
        exit 1
    fi
    echo "warning: npm ci failed (attempt ${attempt}); retrying." >&2
    attempt=$((attempt + 1))
    chmod -R u+w "$BROWSER_DIR/node_modules" 2>/dev/null || true
    rm -rf "$BROWSER_DIR/node_modules"
    rm -rf "$NPM_CACHE"
    npm --prefix "$BROWSER_DIR" cache clean --force >/dev/null
done
sha256sum "$LOCK_FILE" | awk '{print $1}' > "$CHECK_FILE"
cd "$BROWSER_DIR"
args=()
for f in "$@"; do
    args+=("$(realpath --relative-to=. "$ROOT/$f")")
done
ESLINT_USE_FLAT_CONFIG=true npx eslint --no-warn-ignored --config eslint.config.js "${args[@]}"
