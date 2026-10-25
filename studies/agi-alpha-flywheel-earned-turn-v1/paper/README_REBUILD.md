# Rebuild the Earn the Next Turn edition

The authoritative manuscript is `AGI_ALPHA_FLYWHEEL_Earn_the_Next_Turn.tex`. It includes modular source,
`references.bib` and editable figure generators. It is a new edition; no earlier PDF or historical URL is
overwritten. The date on the cover is 24 October 2026 in America/Toronto.

The build uses XeLaTeX/BibTeX (TeX Live 2023 in the authoring environment), Latin Modern fonts, Python 3.12,
Matplotlib 3.10.8 and NumPy. The complete companion pins its scientific dependencies separately. Mathematical
figures are vectors; all original method diagrams are supplied as editable SVG plus publication PDF.

From this directory:

```sh
bash build.sh
```

The build sets a fixed source date and PDF trailer identity, generates the method figures, optionally runs
the final result-figure generator, then performs the XeLaTeX/BibTeX passes. It refuses overfull boxes, missing
glyphs, unresolved citations and undefined references. A clean log alone does not replace page inspection.
Render every final page using Poppler and inspect the complete final version before publication.

The main source requires all manuscript modules, including the final abstract, contribution, experimental
protocol, results, discussion and reproduction guide. It does not insert plausible-looking fallback results
if a module is absent. Only the finished source package should be used for publication.

Exact served foundation editions are identified in the bibliography and companion audit manifest. Full long
hashes in an artifact manifest identify bytes; they do not qualify scientific claims or confer authority.
Source, raw evidence and installed/native/hosted status must retain their separately reported scopes.
