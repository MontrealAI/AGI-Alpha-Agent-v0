#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Rebuild the Insight demo assets and refresh SRI metadata deterministically.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

bash scripts/build_insight_docs.sh
python scripts/check_insight_sri.py docs/alpha_agi_insight_v1
