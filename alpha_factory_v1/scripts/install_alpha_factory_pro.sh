#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build the preserved research image; deploy only when --deploy is explicit.
# Flags: --all --ui --no-ui --trace --tests --no-cache --bootstrap --deploy
#        --alpha NAME --open --help
# --tests runs an additional image/import smoke check, not the full regression suite.
# --trace is retained: the legacy image includes its trace service by default.
# Use the maintained private-operator profile in docs/agent/FACTORY_GUIDE.md for native missions.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="${PROFILE:-full}"
IMAGE_TAG="${ALPHA_IMAGE_TAG:-alphafactory_pro:local}"
want_ui=1; want_tests=0; want_open=0; do_deploy=0; do_bootstrap=0
no_cache=(); strategy=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) want_ui=1; want_tests=1 ;;
    --ui) want_ui=1 ;;
    --no-ui) want_ui=0 ;;
    --trace) : ;;
    --tests) want_tests=1 ;;
    --no-cache) no_cache=(--no-cache) ;;
    --bootstrap) do_bootstrap=1 ;;
    --deploy) do_deploy=1 ;;
    --open) want_open=1 ;;
    --alpha)
      [[ $# -ge 2 && "$2" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "--alpha requires a simple strategy name" >&2; exit 2; }
      strategy="$2"; shift ;;
    --help|-h) sed -n '3,8p' "$0"; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

FACTORY_ROOT=""
for candidate in "$PWD" "$SCRIPT_DIR/../.."; do
  if [[ -f "$candidate/pyproject.toml" && -f "$candidate/alpha_factory_v1/Dockerfile" ]]; then
    FACTORY_ROOT="$(cd "$candidate" && pwd)"; break
  fi
done
if [[ -z "$FACTORY_ROOT" && $do_bootstrap == 1 ]]; then
  [[ ! -e factory-source ]] || { echo "factory-source exists; use another directory" >&2; exit 1; }
  git clone --depth 1 --branch main https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git factory-source
  FACTORY_ROOT="$(cd factory-source && pwd)"
fi
[[ -n "$FACTORY_ROOT" ]] || { echo "Use a complete source checkout or --bootstrap" >&2; exit 1; }
cd "$FACTORY_ROOT"

if [[ -n "$strategy" ]]; then
  echo "--alpha is a preserved integration option; this checkout has no configurable strategy registry." >&2
  echo "Choose and configure the finance_alpha catalog entry explicitly; no source file was changed." >&2
  exit 2
fi
command -v docker >/dev/null || { echo "Docker is required" >&2; exit 1; }
docker info >/dev/null

build_args=(--build-arg "INSTALL_UI=$want_ui" "${no_cache[@]}")
if [[ $do_deploy == 0 ]]; then
  docker build "${build_args[@]}" -f alpha_factory_v1/Dockerfile -t "$IMAGE_TAG" .
  if [[ $want_tests == 1 ]]; then
    docker run --rm --entrypoint python "$IMAGE_TAG" -m alpha_factory_v1 --version
  fi
  echo "Built $IMAGE_TAG. No service was started. See docs/agent/FACTORY_GUIDE.md for operating profiles."
  exit 0
fi

docker compose version >/dev/null
env_file="$FACTORY_ROOT/alpha_factory_v1/.env"
if [[ ! -e "$env_file" && ! -L "$env_file" ]]; then
  (umask 077; set -o noclobber; cat alpha_factory_v1/.env.sample > "$env_file")
  echo "Created private alpha_factory_v1/.env. Configure API_TOKEN and NEO4J_PASSWORD, then rerun." >&2
  exit 1
fi
python3 - "$env_file" <<'PY'
import os
from pathlib import Path
import sys
from alpha_factory_v1.utils.env import _load_env_file
values = {**_load_env_file(Path(sys.argv[1])), **os.environ}
for name in ('API_TOKEN', 'NEO4J_PASSWORD'):
    value = values.get(name, '').strip()
    if not value or value.startswith('REPLACE_ME'):
        raise SystemExit(f'Configure {name} before deployment; no service was started')
PY
compose=(docker compose --env-file "$env_file" -f alpha_factory_v1/docker-compose.yml --profile "$PROFILE")
"${compose[@]}" config --quiet
"${compose[@]}" build "${build_args[@]}"
"${compose[@]}" up -d --wait --wait-timeout 180
# Expand the token only inside the container, not into the host command arguments.
# shellcheck disable=SC2016
"${compose[@]}" exec -T orchestrator sh -c 'curl --fail --silent -H "Authorization: Bearer $API_TOKEN" http://localhost:8000/healthz'
if [[ $want_tests == 1 ]]; then
  "${compose[@]}" exec -T orchestrator python -m alpha_factory_v1 --version
fi
echo "Research stack health check passed. API: http://localhost:8000/docs; UI: http://localhost:3000"
if [[ $want_open == 1 ]]; then
  if command -v xdg-open >/dev/null; then
    xdg-open http://localhost:3000 >/dev/null 2>&1 &
  elif command -v open >/dev/null; then
    open http://localhost:3000 >/dev/null 2>&1 &
  fi
fi
