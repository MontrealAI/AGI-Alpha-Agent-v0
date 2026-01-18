#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# This wrapper builds the demo gallery and publishes it to GitHub Pages.
# It is a conceptual research prototype.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

BROWSER_DIR="alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
ASSET_CACHE_DIR="${INSIGHT_ASSET_ROOT:-${FETCH_ASSETS_DIR:-}}"
if [[ -z "$ASSET_CACHE_DIR" ]]; then
    ASSET_CACHE_DIR="${RUNNER_TEMP:-/tmp}/insight-assets"
fi
export FETCH_ASSETS_DIR="$ASSET_CACHE_DIR"
export INSIGHT_ASSET_ROOT="$ASSET_CACHE_DIR"

# Environment checks
python alpha_factory_v1/scripts/preflight.py
node "$BROWSER_DIR/build/version_check.js"

npm --prefix "$BROWSER_DIR" run fetch-assets
npm --prefix "$BROWSER_DIR" ci

"$SCRIPT_DIR/build_insight_docs.sh"

# Build and verify the site using strict mode so warnings fail
mkdocs build --strict
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1

# Optional offline smoke test if Playwright is available
if python - "import importlib,sys;sys.exit(0 if importlib.util.find_spec('playwright') else 1)"; then
  python -m http.server --directory site 8000 &
  SERVER_PID=$!
  trap 'kill $SERVER_PID' EXIT
  sleep 2
  python scripts/verify_insight_offline.py
  kill $SERVER_PID
  trap - EXIT
else
  echo "Playwright not found; skipping offline check" >&2
fi

# Deploy using mkdocs
mkdocs gh-deploy --force

remote=$(git config --get remote.origin.url)
repo_path=${remote#*github.com[:/]}
repo_path=${repo_path%.git}
org="${repo_path%%/*}"
repo="${repo_path##*/}"
url="https://${org}.github.io/${repo}/"

echo "Demo gallery deployed to $url"
