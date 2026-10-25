#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
cd -- "$(dirname -- "$0")"
export SOURCE_DATE_EPOCH=1792800000
export FORCE_SOURCE_DATE=1
export TZ=UTC
export MPLCONFIGDIR="${TMPDIR:-/tmp}/strategy-succession-mpl"
python3 make_figures.py
if [ -f make_result_figures.py ]; then python3 make_result_figures.py; fi
xelatex -interaction=nonstopmode -halt-on-error AGI_ALPHA_FLYWHEEL_Strategy_Succession.tex > build-pass1.stdout
bibtex AGI_ALPHA_FLYWHEEL_Strategy_Succession > build-bibliography.stdout
xelatex -interaction=nonstopmode -halt-on-error AGI_ALPHA_FLYWHEEL_Strategy_Succession.tex > build-pass2.stdout
xelatex -interaction=nonstopmode -halt-on-error AGI_ALPHA_FLYWHEEL_Strategy_Succession.tex > build-pass3.stdout
if rg -n 'Overfull|Missing character|undefined references|Citation .* undefined' AGI_ALPHA_FLYWHEEL_Strategy_Succession.log; then
  printf '%s\n' 'Layout/reference check requires review.' >&2
  exit 1
fi
