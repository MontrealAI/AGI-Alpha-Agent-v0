#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Supervise the historical orchestrator, RPC facade and Flask UI.
set -Eeuo pipefail
export PYTHONUNBUFFERED=1
export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"
: "${API_TOKEN:?Set API_TOKEN to protect the orchestrator API}"
export RPC_PORT="${RPC_PORT:-8001}"
export RPC_HOST="${RPC_HOST:-127.0.0.1}"
pids=()
# Invoked through the EXIT trap below.
# shellcheck disable=SC2317
cleanup() {
    trap - EXIT SIGINT SIGTERM
    if ((${#pids[@]})); then
        kill "${pids[@]}" 2>/dev/null || true
        wait "${pids[@]}" 2>/dev/null || true
    fi
}
trap cleanup EXIT
trap 'exit 143' SIGTERM
trap 'exit 130' SIGINT

python -m alpha_factory_v1.backend.main &
pids+=("$!")
python -m alpha_factory_v1.backend.rpc_server &
pids+=("$!")
python -m gunicorn --workers 1 --bind 0.0.0.0:3000 alpha_factory_v1.ui.app:app &
pids+=("$!")

# Fail the container when any required service stops, including an unexpected
# successful exit. Preserve failures instead of losing them to `set -e`.
status=0
wait -n "${pids[@]}" || status=$?
if ((status == 0)); then status=1; fi
exit "$status"
