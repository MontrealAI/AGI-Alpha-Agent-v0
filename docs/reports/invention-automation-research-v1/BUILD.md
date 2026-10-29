# Editable research edition 1.0.0

This directory contains the complete LaTeX/PDF paper and full HTML paper.

Read `main.pdf` or `index.html`. The browser edition embeds all figures and uses native MathML; it is not a PDF viewer or summary. For companion evidence links keep this directory together.

## Build

```
python generate_figures.py
python build.py
```

Dependencies: local Python/NumPy/Matplotlib, Pandoc with citeproc, and pdfLaTeX with the packages named in `main.tex`. No shell escape, network asset, automatic installation, or BibTeX executable is needed.

To rebuild the retained editable TeX directly:

```
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

`manuscript.template.md` plus `data/audited.json` produces synchronized text/tables; `references.bib` is the editable bibliography. `generate_figures.py` creates the seven PNG/vector-PDF figures. `build.py` creates `main.tex`, `body.tex`, `abstract.tex`, the PDF, and the complete HTML. In a source-only extraction, it retains the supplied artifact identities in the claim map. Re-auditing those identities requires the complete research companion, not only this directory.

## Evidence scope

New correction v2: 36/36 accepted, as is the strong full LP, with higher measured correction compute. First-version failures are retained. The instrument's latest recovered SIM operating profit is −8.574947; no real same-cohort profitability crossing, compounding advantage, or earned-funded writer construction is established. Original large factorial raw records were not recovered and their summaries remain labeled historical.

The complete research companion's root README has all exact test and replay commands, source boundaries, original archives, all new raw records, frozen protocols, independent checks, and continuation conditions. No remote publication or real transaction is authorized by this package.
