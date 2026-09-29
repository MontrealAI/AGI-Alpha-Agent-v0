#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
compose="$demo_dir/docker-compose.muzero.yml"
command -v docker >/dev/null 2>&1 || {
  echo "Docker is required: https://docs.docker.com/get-docker/" >&2; exit 1;
}
export HOST_PORT="${HOST_PORT:-7861}"
if [[ ! "$HOST_PORT" =~ ^[0-9]+$ ]] || (( 10#$HOST_PORT < 1 || 10#$HOST_PORT > 65535 )); then
  echo "HOST_PORT must be an integer from 1 to 65535" >&2
  exit 1
fi
if command -v lsof >/dev/null 2>&1 && lsof -i TCP:"${HOST_PORT}" -s TCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${HOST_PORT} already in use. Set HOST_PORT to an open port." >&2
  exit 1
fi
docker compose version >/dev/null
printf 'Building MuZero Planning Lab (first build downloads dependencies)…\n'
docker compose --project-name alpha_muzero -f "$compose" up -d --build --wait
printf '\nOpen http://localhost:%s — local training, no API key required.\n' "$HOST_PORT"
printf 'Stop: docker compose --project-name alpha_muzero -f "%s" down\n' "$compose"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:${HOST_PORT}" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "http://localhost:${HOST_PORT}" >/dev/null 2>&1 &
fi
