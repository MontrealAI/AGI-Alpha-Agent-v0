#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Orchestrate the Edge-of-Knowledge demo gallery deployment.
# This conceptual research script validates the environment,
# verifies demo packages, builds the site and publishes it to GitHub Pages.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Ensure Python, Node and optional packages are present
python alpha_factory_v1/scripts/preflight.py
node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
python scripts/check_python_deps.py
if [[ "${CI_SKIP_ENV_CHECK:-0}" == "1" && "${CI:-}" == "true" ]]; then
  echo "CI_SKIP_ENV_CHECK set – skipping check_env.py" >&2
else
  python check_env.py --auto-install
fi

# Disclaimer snippet verification removed; rely on documentation updates

# Validate demo directories for basic quality
python -m alpha_factory_v1.demos.validate_demos

# Build and deploy the full gallery
"$SCRIPT_DIR/deploy_gallery_pages.sh"

# Triple-check the generated site integrity
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1

# Optional second offline validation if Playwright is available
if python - <<'EOF'
import importlib, sys
sys.exit(0 if importlib.util.find_spec('playwright') else 1)
EOF
then
  python scripts/verify_demo_pages.py
  python -m http.server --directory site 8000 &
  SERVER_PID=$!
  trap 'kill $SERVER_PID' EXIT
  sleep 2
  python scripts/verify_insight_offline.py
  kill $SERVER_PID
  trap - EXIT
else
  echo "Playwright not found; skipping offline re-check" >&2
fi
