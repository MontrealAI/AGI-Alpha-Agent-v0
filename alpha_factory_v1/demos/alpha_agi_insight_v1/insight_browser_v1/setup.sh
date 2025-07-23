#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure Node.js 22+
node build/version_check.js

if [[ -d node_modules ]]; then
  echo "node_modules already present"
  exit 0
fi

echo "Installing npm dependencies..."
if ! npm ci --no-progress; then
  echo "ERROR: npm ci failed" >&2
  exit 1
fi
