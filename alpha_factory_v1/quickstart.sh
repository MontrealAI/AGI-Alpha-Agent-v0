#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# One implementation for Bash and Python; all historical flags are forwarded.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/quickstart.py" "$@"
