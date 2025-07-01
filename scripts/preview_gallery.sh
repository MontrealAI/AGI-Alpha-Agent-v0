#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build the full demo gallery then serve it locally.
# This is a convenience wrapper for non-technical users.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

"$SCRIPT_DIR/build_gallery_site.sh"

python -m http.server --directory site 8000 &
SERVER_PID=$!
trap 'kill $SERVER_PID' EXIT
sleep 2

if command -v python >/dev/null 2>&1; then
    python - <<'PY'
import webbrowser, pathlib
webbrowser.open((pathlib.Path('site/index.html').resolve()).as_uri())
PY
fi

echo "Serving demo gallery at http://localhost:8000/ (Ctrl+C to stop)"
wait $SERVER_PID
