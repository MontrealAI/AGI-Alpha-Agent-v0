# Paper sources and figures

The final documents are `agi-alpha-flywheel.pdf`, `executive-brief.pdf` and `evidence-companion.pdf`. Their complete sources use `edition.sty` and `references.tex`; retain these files and the `figures/` directory when rebuilding.

Build prerequisites: Python3.11+, Matplotlib and NumPy for the figures; XeLaTeX/latexmk and standard TeX Live packages; P052/Nimbus OpenType fonts (URW Base35), DejaVu Sans Mono and Latin Modern Math. The verified research environment used Python3.12.14, Matplotlib3.10.8 and NumPy2.3.2. PDF byte hashes depend on toolchain/metadata; the published stored originals have authoritative manifest identities. Scientific JSON reproduction is checked separately.

From this directory:

```bash
MPLCONFIGDIR=/tmp/alpha-matplotlib-cache python3 make_figures.py
latexmk -xelatex -interaction=nonstopmode -halt-on-error agi-alpha-flywheel.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error executive-brief.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error evidence-companion.tex
```

Plots are generated from preserved observations and explicitly labeled assumptions. They use embedded TrueType PDF fonts and SVG counterparts. The first PDF candidate's Type3 figure-font character dictionary triggered the existing passive-PDF validator's unsupported-action check. The figure source was explicitly changed to embed TrueType fonts; the validator and all scientific data were unchanged. No published manuscript original was rewritten.

All pages were rendered and visually inspected after layout correction. The final verification record states page counts, source hashes, passive-PDF checks and browser results. No PDF rendering or presentation check validates ecological or commercial assumptions.
