#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Alpha Factory v2 – Installer
# Robust production-grade deployment helper
set -euo pipefail

IMAGE_REMOTE=${IMAGE_REMOTE:-ghcr.io/alphafactory/core:v2}
IMAGE_LOCAL=${IMAGE_LOCAL:-alphafactory/core:v2local}
CONTAINER_NAME=${CONTAINER_NAME:-alpha_factory}
PORT=${PORT:-3000}
VOLUME_NAME=${VOLUME_NAME:-alphafactory_data}
FORCE_LOCAL=0

usage() {
  cat <<USAGE
Usage: $0 [options]
  --local             Build image locally instead of pulling
  --port PORT         Expose container port (default: $PORT)
  --name NAME         Container name (default: $CONTAINER_NAME)
  -h, --help          Show this help
USAGE
}

# --- CLI parsing -----------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    --local) FORCE_LOCAL=1 ;;
    --port) PORT=$2; shift ;;
    --name) CONTAINER_NAME=$2; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

echo "=== Alpha Factory v2 – Installer ==="
command -v docker >/dev/null || { echo "Docker required." >&2; exit 1; }

GPU_ARGS=""
if command -v nvidia-smi >/dev/null 2>&1 && docker info --format '{{json .Runtimes.nvidia}}' | grep -q nvidia; then
  echo "GPU detected"
  GPU_ARGS="--gpus all"
fi

# --- obtain image ---------------------------------------------------------
if [[ $FORCE_LOCAL -eq 0 ]]; then
  if docker pull --quiet "$IMAGE_REMOTE"; then
    IMAGE="$IMAGE_REMOTE"
  else
    FORCE_LOCAL=1
  fi
fi

if [[ $FORCE_LOCAL -eq 1 ]]; then
  echo "Building image locally..."
  docker build -t "$IMAGE_LOCAL" .
  IMAGE="$IMAGE_LOCAL"
fi

# --- start container ------------------------------------------------------
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Starting container..."
docker run -d "$GPU_ARGS" --name "$CONTAINER_NAME" \
  -p "$PORT:$PORT" \
  -v "$VOLUME_NAME:/var/alphafactory" \
  -e AF_MEMORY_DIR=/var/alphafactory \
  -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  "$IMAGE"

# --- verify startup -------------------------------------------------------
for _ in {1..15}; do
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Alpha Factory v2 running at http://localhost:${PORT}"
    exit 0
  fi
  sleep 1
done

echo "Error: container failed to start" >&2
exit 1
