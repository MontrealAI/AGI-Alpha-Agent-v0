#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md

set -Eeuo pipefail
trap 'echo "Quickstart stopped on line $LINENO; existing configuration and data were retained." >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  echo 'Usage: ./run_quickstart.sh [--build-only]'
  echo 'Build the minimal research API from this checkout and bind it to 127.0.0.1:8000.'
  echo 'Configure the root .env first. Data persists in the alpha-factory-quickstart-data Docker volume.'
  echo 'For the maintained private operator, follow docs/agent/START_HERE.md.'
  exit 0
fi
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --build-only ) ]]; then
  echo 'Unknown argument. Use --help or --build-only.' >&2
  exit 2
fi

cat "$SCRIPT_DIR/docs/DISCLAIMER_SNIPPET.md"
command -v docker >/dev/null || { echo 'Docker is required; start Docker Desktop or the daemon.' >&2; exit 1; }
docker info >/dev/null

IMAGE="alpha-factory-quickstart"

if [[ ${1:-} != --build-only ]]; then
  if [[ ! -e .env && ! -L .env ]]; then
    (umask 077; set -o noclobber; cat alpha_factory_v1/.env.sample > .env)
    echo 'Created private .env. Set API_TOKEN and NEO4J_PASSWORD, then rerun. No service was started.' >&2
    exit 1
  fi
  [[ -f .env ]] || { echo '.env must be a regular configuration file.' >&2; exit 1; }
fi

docker build -f docker/quickstart/Dockerfile -t "$IMAGE" .
if [[ ${1:-} == --build-only ]]; then
  echo "Built $IMAGE. No service was started."
  exit 0
fi

echo 'Research API: http://127.0.0.1:8000/docs. Stop with Ctrl+C; the data volume is retained.'
echo 'Use the API_TOKEN in your .env to authenticate. Configure optional agents separately.'

exec docker run --rm --init \
  --env-file "$SCRIPT_DIR/.env" \
  --mount type=volume,source=alpha-factory-quickstart-data,target=/data \
  -p 127.0.0.1:8000:8000 "$IMAGE"
