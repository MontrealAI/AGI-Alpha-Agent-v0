#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# This demo is a conceptual research prototype. References to “AGI” and
# “superintelligence” describe aspirational goals, not real AGI.
# Alpha-Factory v1 □  Production-ready launcher for the world-model demo
set -Eeuo pipefail

# Resolve script path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Force offline mode when no API key is supplied
case "${OPENAI_API_KEY:-}" in
  "" | "stub" | "dummy" | "dummy-key" | "test")
    export NO_LLM=1
    ;;
  *)
    unset NO_LLM
    ;;
esac

python -m alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo --demo "$@"
