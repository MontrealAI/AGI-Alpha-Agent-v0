# PDF publication QA

**Result: PASS for the exact PDFs below.** All 27 final pages were rendered and visually inspected. No required visual fix remains.

This is publication QA within the same AI-assisted session, not research peer review, customer acceptance, software qualification or approval to release through the canonical publisher.

| Document | Pages | Bytes | SHA-256 |
|---|---:|---:|---|
| `publication/AGI_ALPHA_FLYWHEEL.pdf` | 24 | 501813 | `c5c95c85c881335d7dbceb6758acdb44cdf20260d865779a572c683aa6590c1f` |
| `publication/AGI_ALPHA_Executive_Brief.pdf` | 3 | 68528 | `7603c70f0c23413771c06b814414737b5b9c48223eac5ca57249f56ea3995a9f` |

Observed: 2026-10-28 02:15:22 UTC.

## What was checked

Poppler 26.05.0 rendered every final page at 110 dpi. Contact sheets covered all pages; larger views checked the tables, five figures, title/byline, source identifiers, corrected bold letters and final pages. Text was extracted with `pdftotext -layout` and pdfplumber 0.11.9. File hashes were checked again after visual inspection.

Both PDFs carry the exact requested title and Vincent Boucher byline in their metadata. Extracted text preserves the title components, byline, bold **CAD**, **ALPHA** and, where applicable, **Admit the need**. The economic core is present in both documents: USD1,542; USD146.98; USD252.59; 37.75%; USD1,341.84; 203.55; and USD98.26 million. Word hyphenation and whitespace were normalized for these text checks.

No clipped or overlapping text, missing visible glyph, empty page, header-only table continuation or unreadable figure was found. All fonts are embedded subsets with Unicode mappings. Every page has zero text glyphs outside page bounds by more than 0.25 points.

The paper's reading guide and contents fit one page. Its four-row economic-results table stays together; longer tables repeat headers with actual data on each continuation. The brief's evidence and economics tables each stay together. The figure page and partial final reference/disclosure or conclusion pages are coherent designed content, not accidental blank continuations.

## Log findings

The final paper log contains no overfull, underfull, missing-character, font-substitution, LaTeX-warning or fatal-error entries.

The compact brief log contains **three underfull hbox warnings**, with badness 5388, 1888 and 1622. Corresponding paragraphs were visually inspected: minor word-spacing variation is present, without clipped text, lost glyphs or overlap. These are recorded as nonblocking. The brief has no overfull, missing-character, font-substitution, LaTeX-warning or fatal-error entries.

An initial QA aggregation assertion treated every underfull warning as fatal. That classification was corrected after direct visual inspection; the receipt preserves the warnings. No research acceptance criterion or frozen file was changed.

## Corrections preserved in the receipt

The first inspected version used P052 with unavailable bold, an overflow contents page, an empty repeated economic-table header and a brief masthead collision. The author corrected those defects.

The next version exposed a subtler P052 bold defect: uppercase A disappeared despite clean missing-glyph logs. Visual inspection and text extraction both confirmed it. The author replaced the body font with bundled, explicitly configured DejaVu Serif TrueType faces.

That font change fixed the glyphs but expanded the brief to four pages with split short tables and a small final continuation. Brief-only type/spacing and table-space adjustments produced the approved three-page version.

The detailed review history, all intermediate PDF hashes, per-page checks and final log identities are in `pdf_qa.json`. No publication or frozen research file was edited by this reviewer.

