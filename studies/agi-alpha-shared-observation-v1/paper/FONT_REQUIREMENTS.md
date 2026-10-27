# Document and font requirements

The LaTeX bundle contains the three generated `.tex` documents, canonical Markdown sources, bibliography, Pandoc template and Lua filter, both document and figure build scripts, and the final PDF/PNG figure assets. It omits the three finished document PDFs and the full browser reader; those are separate deliverables. The small HTML reader template and CSS remain because the supplied document builder also regenerates the reader.

## Rebuild the documents

From the extracted bundle's study directory, run:

```bash
python paper/build_documents.py
```

The builder invokes Pandoc with citation processing, then runs XeLaTeX twice per document. It rejects overfull-box and missing-character diagnostics. Its `SOURCE_DATE_EPOCH` defaults to `1793102400`. The observed environment used Python 3.12.14, Pandoc 3.1.3 and XeTeX 0.999995 from TeX Live 2023/Debian. No packages are automatically installed by the builder.

If only the supplied main LaTeX source is needed, run from `paper/`:

```bash
xelatex -interaction=nonstopmode -halt-on-error AGI_Alpha_Flywheel.tex
xelatex -interaction=nonstopmode -halt-on-error AGI_Alpha_Flywheel.tex
```

The generated `.tex` already includes processed bibliography text. Regenerating it from the manuscript requires Pandoc and `references.bib`.

## Fonts and TeX packages

The preserved template and generated sources use these fonts:

| Use | Font files or family |
| --- | --- |
| Main text | URW Base 35: `P052-Roman.otf`, `P052-Bold.otf`, `P052-Italic.otf`, `P052-BoldItalic.otf` |
| Headings | URW Base 35: `NimbusSans-Regular.otf`, `NimbusSans-Bold.otf`, `NimbusSans-Italic.otf`, `NimbusSans-BoldItalic.otf` |
| Monospace | `DejaVu Sans Mono` |

The original Linux build resolves URW files through `/usr/share/fonts/opentype/urw-base35/`. This environment-specific font location is preserved in the publication source. On another system, provide those files at the declared location or adjust the font `Path` entries in a working copy of `template.tex` and regenerate the documents. A different font or layout requires renewed visual inspection; it is not the already verified PDF. Font binaries are not redistributed in this bundle.

Required TeX packages are named directly in the source: `fontspec`, `geometry`, `amsmath`, `amssymb`, `booktabs`, `longtable`, `array`, `calc`, `graphicx`, `xcolor`, `enumitem`, `fancyhdr`, `titlesec`, `microtype`, `hyperref`, `xurl`, and `needspace`.

## Figure regeneration and evidence

The included final figure assets are sufficient for document compilation. `build_figures.py` additionally requires Matplotlib, NumPy and the complete research package's original `results/`, `evaluation/` and `data/` inputs. Those data are intentionally supplied in the research ZIP rather than duplicated in the smaller LaTeX ZIP. Figure regeneration is separate from the preserved scientific evaluation.

The main paper, executive brief and companion were visually inspected in their delivered 19-, 2- and 5-page forms. Exact hashes and the boundaries of that inspection appear in the research package's `evidence/pdf-qa.json`. Document formatting does not qualify a scientific result or the repository's full release gates.
