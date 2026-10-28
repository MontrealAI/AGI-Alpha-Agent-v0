# Build the reading edition

From the repository root, with Python, Pandoc, Inkscape and XeLaTeX available:

```bash
python studies/discovery-means-v1/publication/build_publication.py --evidence studies/discovery-means-v1/evidence --facts studies/discovery-means-v1/publication/publication_facts.json --regressions studies/discovery-means-v1/regressions/R01-R37-applicability.json --quickstart studies/discovery-means-v1/publication/quickstart.md --pdf
```

Complete LaTeX, SVG figures, bibliography, narrative, data and builder are committed.
Generated PDF, browser HTML and visual-QA PNGs are delivered separately and omitted from source review under the existing binary policy. The builder regenerates both figure PDFs.
PDF metadata may change on rebuilding; the delivered inspected PDF has its own recorded hash.
The browser edition uses local relative PDF and LaTeX links when the complete package is extracted. Standalone HTML retains the article but needs companion files for those downloads.

`qa/` contains hash-bound inspection receipts. Required owner-controlled public publication, served-file verification and full software qualification remain pending. This source review does not assert a canonical public reader URL.
