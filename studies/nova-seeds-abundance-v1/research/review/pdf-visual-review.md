# Writer #10 PDF visual review — initial compiled edition

**Status: changes requested before final freeze.** Every page was visually inspected; this is not approval of a later PDF.

- PDF: `research/paper/paper.pdf`
- SHA-256: `1ae91915978bcccb8ceb09abd963ee22841be74f874f8205ea4634be97ca92e8`
- Size: 481,622 bytes; 20 pages.
- Method: Poppler, 120 dpi, JPEG quality 82; strict pypdf destination/text checks.
- Initial ENOSPC required in-memory inspection. All 20 compact images are now also retained as `output/pdf-qa/initial-page-*.jpg` (4,899,400 bytes total), rendered from the same exact PDF bytes and settings; exclude this directory from the source archive.

## Findings

- **QA-1 (major), pages 17:** Reproduction commands render/extract –mode and –out as U+2013 instead of literal ASCII --mode and --out. Use verbatim commands or disable hyphen ligatures in monospaced text; verify PDF text extraction preserves ASCII --.
- **QA-2 (medium), pages 4, 5:** Section 4 heading is alone at the bottom of page 4; subsection and body start on page 5. Keep section heading with following subsection and body.
- **QA-3 (medium), pages 14, 15:** Section 8 heading is alone on page 14 with substantial white space; subsection/table begin on page 15. Keep heading with subsection/table, or explicitly begin the section on a fresh page.
- **QA-4 (minor), pages 2, 5, 10, 11, 15:** Several paragraphs split after one initial line; page 11 also begins with a single final line from the registry paragraph. Apply club/widow control and recheck pagination. Specific starts: p2 NFT paragraph, p5 complete-clone paragraph, p11 AscensionMark paragraph, p15 World/Policy paragraph.
- **QA-5 (minor), pages 15, 18, 19:** Justified narrow columns in integration table and claim ledger produce stretched interword spacing and awkward hyphenation. Use ragged-right paragraph columns if compatible with layout.

## Page-indexed review

| Page | Status | Observation |
|---|---|---|
| 1 | pass | Cover, provocation disclaimer, abundance map and outcome statement are readable and unclipped; conceptual diagram is labelled. |
| 2 | minor | Abstract and reading-key box clean; final NFT paragraph starts with only one line before page break. |
| 3 | pass | Value table and equations 1–2 legible; all columns and equation numbers inside margins. |
| 4 | changes requested | Primary citations render consistently; section 4 heading stranded at page bottom. |
| 5 | minor | Mechanism/equation 3 clean; last complete-clone paragraph starts with one line. |
| 6 | pass | Protocol text and all seven baseline rows readable; table 2/caption intact. |
| 7 | pass | Results and table 3 readable; negative conditions visible, values aligned. |
| 8 | pass | Figure 1 categories/error bars/legend distinct; caption and drift discussion unclipped. |
| 9 | pass | Two-panel temporal figure and legend readable; no panel-title or axis-label overlap. |
| 10 | minor | Figure 3 corrected exact/adaptive labels separated; registry paragraph leaves one final line on next page. |
| 11 | minor | Registry box and citations readable; one-line paragraph continuation at top and AscensionMark first-line orphan at bottom. |
| 12 | pass | Contract semantics and table 4 legible; no clipping or misleading numeric alignment. |
| 13 | pass | Cost table 5 and sensitivity equation 4 legible; unknown costs visible. |
| 14 | changes requested | Economic conclusion box clean; section 8 heading stranded before the next-page table. |
| 15 | minor | Integration table 6 legible but stretched column spacing; final World/Policy paragraph starts with one line. |
| 16 | pass | Limitations and interpretation clean; readable paragraphs and consistent hierarchy. |
| 17 | changes requested | Reproduction layout readable but monospaced -- flags become en dashes in both visible PDF and extracted text. |
| 18 | minor | Repository SHAs and contract links readable; claim ledger columns have excessive justification spacing. |
| 19 | minor | Claim ledger continues with repeated headers; freeze identities fully visible; same column-spacing recommendation. |
| 20 | pass | All reference entries fit and contain legible linked destinations; no clipping, missing glyphs or unresolved citation markers. |

## Link and citation checks

55 annotations: 29 URI annotations (24 unique URLs) and 26 internal links. All internal targets resolve among 78 named destinations. No unresolved `??` citation markers. All body pages contain the intended header/footer. External URLs were not re-fetched in this visual review. No manuscript, executable source, protocol or evidence was edited.
