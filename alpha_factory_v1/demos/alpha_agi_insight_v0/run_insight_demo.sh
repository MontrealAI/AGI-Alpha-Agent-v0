#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Quick launcher for the α‑AGI Insight demo
set -euo pipefail

script_dir="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
root_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

cd "$root_dir"

echo "Launching α‑AGI Insight demo…"
python -m alpha_factory_v1.demos.alpha_agi_insight_v0.official_demo_final "$@"
