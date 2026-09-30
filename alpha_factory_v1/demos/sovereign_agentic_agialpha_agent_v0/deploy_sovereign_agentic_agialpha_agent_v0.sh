#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# The original generator is preserved in archive/*.original.txt.
# Default launch uses the maintained, authenticated local Sovereign runtime.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Install Python 3.11–3.13 and follow the Sovereign README." >&2
  exit 2
fi
"$PYTHON" -c 'import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 2)' || {
  echo "Sovereign requires Python 3.11–3.13." >&2
  exit 2
}
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -P -m alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0 "$@"
