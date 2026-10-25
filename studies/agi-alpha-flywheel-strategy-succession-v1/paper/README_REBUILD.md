# Build the publication PDF

This archive contains the authoritative author PDF, all LaTeX source, bibliography, figure data, build scripts and editable SVG/PDF figures for the distinct Strategy Succession edition. Preferred Edition 02 is unchanged.

Use Python 3.12.14 with Matplotlib 3.10.8, XeLaTeX/BibTeX from TeX Live 2023, and the Latin Modern fonts. From the archive root:

```sh
bash paper/build.sh
```

The script regenerates figures, runs XeLaTeX, BibTeX and two final XeLaTeX passes, then rejects overfull boxes, missing glyphs and unresolved citations. Metadata date, PDF identity, SVG IDs and figure metadata are fixed. The authoritative build was rebuilt from the packaged source with byte-identical PDF output; see the complete companion verification record for its exact hash and page review.

`plot-data.json` contains recorded results used by the figure scripts. Rebuilding the paper does not rerun confirmation. The separate complete research companion contains frozen execution source, protocols, raw results, independent audits and all reproduction instructions.
