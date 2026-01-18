#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build the full Alpha-Factory demo gallery locally.
# This script regenerates all demo documentation, compiles the
# MkDocs site and verifies the service worker hash.
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

# Verify core tools and optional packages
python alpha_factory_v1/scripts/preflight.py
node "$BROWSER_DIR/build/version_check.js"
python scripts/check_python_deps.py
python check_env.py --auto-install
# disclaimer snippet verification removed; rely on pre-commit hooks
python -m alpha_factory_v1.demos.validate_demos

# Refresh browser assets and generate docs
npm --prefix "$BROWSER_DIR" run fetch-assets
npm --prefix "$BROWSER_DIR" ci
"$SCRIPT_DIR/build_insight_docs.sh"
python scripts/generate_demo_docs.py
python scripts/generate_gallery_html.py
python scripts/mirror_demo_pages.py
python scripts/build_service_worker.py

# Build the static site and verify integrity
mkdocs build --strict
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1

echo "Demo gallery built under $REPO_ROOT/site"
