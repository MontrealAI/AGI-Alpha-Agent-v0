#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Publish the Alpha-Factory demo gallery to GitHub Pages.
# This script validates the environment, rebuilds all demo docs,
# compiles the MkDocs site and deploys it under the gh-pages branch.
# Designed for non-technical users to run end-to-end.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

BROWSER_DIR="alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"

# Environment checks
python alpha_factory_v1/scripts/preflight.py
node "$BROWSER_DIR/build/version_check.js"
python scripts/check_python_deps.py
python check_env.py --auto-install
python scripts/verify_disclaimer_snippet.py
python -m alpha_factory_v1.demos.validate_demos

# Rebuild docs and gallery
npm --prefix "$BROWSER_DIR" run fetch-assets
npm --prefix "$BROWSER_DIR" ci
"$SCRIPT_DIR/build_insight_docs.sh"
python scripts/generate_demo_docs.py
python scripts/generate_gallery_html.py

# Build and deploy the site
mkdocs build --strict
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1
mkdocs gh-deploy --force

remote=$(git config --get remote.origin.url)
repo_path=${remote#*github.com[:/]}
repo_path=${repo_path%.git}
org="${repo_path%%/*}"
repo="${repo_path##*/}"
url="https://${org}.github.io/${repo}/"

cat <<EOF
Demo gallery deployed successfully.
Browse to ${url}index.html and explore each demo from there.
EOF
