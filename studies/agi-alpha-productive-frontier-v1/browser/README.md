# Bilingual browser research edition

Open `index.html` directly. The page is self-contained and needs no network connection. It provides an English/French toggle, exact recorded numerical tables, an explicitly conditional investment calculator, keyboard-accessible scrolling tables, and a bilingual no-JavaScript summary.

The page separates numerical-kernel allowances (5/5/2 seconds) from the economic protocol’s assumed complete workflow reservations (95/125/182 seconds). These reservations are not measured delivery latencies or service guarantees.

The initial numerical table and measured composed-policy timings come from the hardened rerun of exposed original cases. The separate final damping-selection prototype uses fresh seed 7401 after its declared amendment. They must not be described as the same independent confirmation. Source hashes are embedded in the page and recorded in `source_manifest.json`.

From the study directory, regenerate after final technical inputs change:

```bash
python browser/builder.py \
  --technical study/technical/results_validated \
  --selection study/technical/results_final_prototype/selection_results.json
```

The calculator defaults to an assumed USD0.50 per core-hour, 10,000 batches of 32 cases, USD52 of additional shared retention/assessment/integration costs, and USD9 of upkeep during a 60-day useful life. Selecting Gym adds a separately visible assumed USD25 of optional C expenditure. The default work case produces approximately USD0.18 of direct compute savings before USD61 of additional costs. No SLA premium, customer premium, sales, or earned revenue is inferred. These editable assumptions are not measured operating invoices.

Local browser QA is reproducible when Playwright and a Chromium binary are available:

```bash
python browser/qa_browser.py \
  --chromium /absolute/path/to/chromium \
  --screenshots /absolute/path/to/qa-output
```

`qa_report.json` records functional results. The checks cover language switching, recorded table counts, calculator sign and break-even boundaries, scenario JSON download, 390/320-pixel layout, no-JavaScript summary, and JavaScript errors. Screenshots are inspected separately.

Relative download links target the study's paper and evidence companion. The ZIP is distributed separately: an extracted archive cannot contain itself, so this page does not expose a potentially broken relative ZIP link. A verified immutable archive URL may be added after it exists. This is a downloadable research edition. It has not been admitted to a live ENS network or published through the repository's software-release lane. Adding HTML requires the existing full qualification/publication process; it is outside the passive paper lane.

## Complete English paper reader

`paper.html` contains every page's text extracted from the accompanying PDF with PyMuPDF. It has no JavaScript or remote assets. Original line breaks remain, and each page links to the corresponding PDF page. Figures and equation layout remain authoritative in the PDF. The reader manifest records the PDF hash, extraction version, per-page text hashes and generated HTML hash.

Install the optional reading/QA dependencies from `browser/requirements-reader.txt`, then regenerate from the frozen original:

```bash
python browser/build_reader.py
python browser/qa_reader.py \
  --chromium /absolute/path/to/chromium \
  --screenshots /absolute/path/to/reader-qa
```

Use `--expected-sha256` with the recorded original PDF digest when building an edition that must match a freeze. The QA compares every page's extracted text exactly, verifies links, and inspects desktop/mobile layouts with JavaScript disabled. New reading-edition HTML requires full source qualification and is not part of the passive PDF/TEX publication lane.
