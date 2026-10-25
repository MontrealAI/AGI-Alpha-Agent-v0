#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$task_root/paper"
export SOURCE_DATE_EPOCH=1792809000
export FORCE_SOURCE_DATE=1
export TEXMFVAR="${TMPDIR:-/tmp}/writer9-texmf-var"
export TEXMFCONFIG="${TMPDIR:-/tmp}/writer9-texmf-config"
mkdir -p "$TEXMFVAR" "$TEXMFCONFIG"
latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error paper.tex
