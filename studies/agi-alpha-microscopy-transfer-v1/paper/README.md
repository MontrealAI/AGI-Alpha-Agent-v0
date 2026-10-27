# Publication edition

The three PDFs share the exact requested title, subtitle and attribution in their text and metadata:

- `paper.pdf` / `paper.tex`: 19-page main paper.
- `executive-brief.pdf` / `executive-brief.tex`: two-page English/French executive brief.
- `evidence-companion.pdf` / `evidence-companion.tex`: four-page claim/evidence and reproducibility companion.

`manuscript.md` is the complete browser-readable prose source. Its images refer to the adjacent
`../figures/` directory. `paper.tex` is an expanded LaTeX deliverable; it also reads the generated
`results.tex` macros and figure images. `template.tex`, `pagebreaks.lua` and `build_paper.py`
preserve the authoring route. `source-results.json` records the actual archived files from which
cover metrics and source-bound display values are derived. No authoring step changes a frozen experiment.

## Build

From this directory:

```sh
python build_paper.py
xelatex -interaction=nonstopmode -halt-on-error executive-brief.tex
xelatex -interaction=nonstopmode -halt-on-error executive-brief.tex
xelatex -interaction=nonstopmode -halt-on-error evidence-companion.tex
xelatex -interaction=nonstopmode -halt-on-error evidence-companion.tex
```

The main build first verifies all three source-freeze file digests, regenerates display values from
retained JSON evidence, invokes Pandoc with the included template/filter, then runs XeLaTeX twice.
It refuses a build with overfull boxes, missing glyphs, font-shape substitution or LaTeX errors.
The Markdown text remains an authored interpretation of the data; generated macros do not
independently validate every sentence.

Dependencies used here: Python 3.12.14, Pandoc, XeLaTeX (TeX Live 2023), Poppler, P052 and Nimbus Sans
from the URW Base35 font package, DejaVu Sans Mono, and Latin Modern Math. The source explicitly names
URW font files under `/usr/share/fonts/opentype/urw-base35/` so bold/italic variants are deterministic.
On other systems, install the same fonts or update the font paths while preserving typography and rerun QA.

## Rendering and QA

```sh
pdftoppm -r 110 -png paper.pdf /tmp/microscopy-paper
pdftoppm -r 110 -png executive-brief.pdf /tmp/microscopy-brief
pdftoppm -r 110 -png evidence-companion.pdf /tmp/microscopy-evidence
```

All 25 pages were rendered and inspected. Full-page checks supplement contact-sheet review for the
cover, principal fresh-result page, revised economic chart, and bilingual/companion pages.
`paperQA.json` records final page counts, file digests, exact metadata, source bindings and the scope
of verification. `build.log` records the final main-paper compilation. PDF creation timestamps and
producer metadata may differ on a later build; frozen numerical evidence is the reproducibility target.

Ruff formatting/lint and strict mypy passed for `build_paper.py`. No full repository release qualification
is implied. The brief and companion cite the same underlying evidence as the main paper and preserve
zero actual collections, unknown complete actual costs, conventional/library parity and the refusal
of unsupported production microscopy scope.
