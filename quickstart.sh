#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Source launcher; --preflight performs checks without installing dependencies.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/alpha_factory_v1/quickstart.sh" "$@"
