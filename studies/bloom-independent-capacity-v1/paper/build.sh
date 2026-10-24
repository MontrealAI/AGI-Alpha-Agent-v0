#!/bin/sh
set -eu
cd "$(dirname "$0")"
export TZ=UTC
export SOURCE_DATE_EPOCH=1792807335
latexmk -pdf -interaction=nonstopmode -halt-on-error -no-shell-escape -outdir=build bloom-independent-capacity-v1.tex
cp build/bloom-independent-capacity-v1.pdf bloom-independent-capacity-v1.pdf
