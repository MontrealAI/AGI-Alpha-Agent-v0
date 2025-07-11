#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
MODE=${RUN_MODE:-web}
if [ "$MODE" = "api" ]; then
  exec python -m alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.api_server
elif [ "$MODE" = "web" ]; then
  if [ -d /app/src/interface/web_client/dist ]; then
    cd /app/src/interface/web_client/dist
    exec python -m http.server 8501
  else
    echo "Missing web build, falling back to Streamlit UI" >&2
    exec streamlit run /app/src/interface/web_app.py \
      --server.port 8501 --server.headless true
  fi
else
  exec python -m alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.cli "$@"
fi
