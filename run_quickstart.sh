#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md

set -Eeuo pipefail
trap 'echo -e "\n\u274c Error on line $LINENO" >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cat "$SCRIPT_DIR/DISCLAIMER_SNIPPET.md"

IMAGE="alpha-factory-quickstart"

docker build -t "$IMAGE" docker/quickstart

docker run --rm -it \
  -v "$SCRIPT_DIR/.env:/app/.env" \
  -p 8000:8000 "$IMAGE"
