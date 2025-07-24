#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Install project dependencies for development.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
PYTHON=${PYTHON:-python3}
version="$($PYTHON - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
case "$version" in
  3.11|3.12|3.13)
    ;;
  *)
    echo "Python 3.11–3.13 required; found $version" >&2
    exit 1
    ;;
esac
$PYTHON -m pip install -U pip
$PYTHON -m pip install -r requirements.txt -r requirements-dev.txt
echo "Environment setup complete."
