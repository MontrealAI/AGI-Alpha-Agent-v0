# Build the publication

The authoritative source is `bloom-independent-capacity-v1.tex`; `references.bib` and the four PDFs under `figures/` complete its inputs. The source combines the retained editing fragments `front.tex`, `methods.tex`, and `body.tex`. Edit the authoritative combined file when reproducing this edition; the fragments are editorial provenance, not automatically loaded inputs.

From this directory run `sh build.sh`. Prerequisites: TeX Live 2023 (pdfTeX 1.40.25), latexmk 4.83, BibTeX, Latin Modern, microtype, geometry, AMS packages, graphicx, booktabs, tabularx, longtable, xcolor, TikZ, tcolorbox, enumitem, fancyhdr, titlesec, natbib, url, caption, placeins, float, hyperref. Shell escape is disabled. No network fetch occurs during compilation. PDF dates, trailer identity and path-bearing pdfTeX metadata are suppressed to support byte-identical local rebuilding. Exact bytes across different TeX/font installations are not guaranteed; use the included canonical PDF and file manifest for distribution.

Figures are independently reproducible from raw frozen evidence with `python3 paper/make_figures.py --results results --out paper/figures` from the study root. The recorded plotting environment is Python 3.12.14, NumPy 2.3.5 and Matplotlib 3.10.8. `figures/plot_provenance.json` identifies exact input hashes, aggregation definitions and output hashes; CSV and SVG sources are included. Matplotlib PDF creation timestamps are omitted.

The final visual-quality receipt records each rendered page hash, reviewed equations/tables/plots, PDF structural checks and any explicitly unrun external publication validator. Rendering uses Poppler `pdftoppm -r 105 -png`.
