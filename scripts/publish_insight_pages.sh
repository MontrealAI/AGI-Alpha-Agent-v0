#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# This script builds the Insight demo and publishes the docs site to GitHub Pages.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

BROWSER_DIR="alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
if ! node "$BROWSER_DIR/build/version_check.js"; then
    echo "ERROR: Node.js 22+ is required to publish the Insight docs." >&2
    exit 1
fi

./scripts/build_insight_docs.sh

# Deploy using mkdocs gh-deploy which relies on ghp-import under the hood
mkdocs gh-deploy --force
