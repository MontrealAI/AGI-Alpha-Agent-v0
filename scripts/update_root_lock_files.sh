#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Regenerate top-level lock files in one pass.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if command -v pip-compile >/dev/null; then
    PIP_COMPILE=pip-compile
else
    PIP_COMPILE="python -m piptools compile"
fi

opts=(--upgrade --allow-unsafe --generate-hashes)

$PIP_COMPILE "${opts[@]}" requirements.txt -o requirements.lock
$PIP_COMPILE "${opts[@]}" requirements-dev.txt -o requirements-dev.lock
$PIP_COMPILE "${opts[@]}" requirements-docs.txt -o requirements-docs.lock
$PIP_COMPILE "${opts[@]}" requirements-demo.txt -o requirements-demo.lock
$PIP_COMPILE "${opts[@]}" --index-url=https://pypi.org/simple \
    requirements-demo.txt requirements-dev.txt requirements.txt \
    -o requirements-cpu.new
mv requirements-cpu.new requirements-cpu.lock
$PIP_COMPILE "${opts[@]}" --index-url=https://pypi.org/simple \
    requirements-demo.txt -o requirements-demo-cpu.new
mv requirements-demo-cpu.new requirements-demo-cpu.lock
