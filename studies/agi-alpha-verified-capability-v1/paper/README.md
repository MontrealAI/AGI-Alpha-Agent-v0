# Publication source and evidence build

The manuscript is **The Economy of Verified Capability: Game-Theoretic Investment in a Growing Validated Skills Graph**, by Vincent Boucher, MONTREAL.AI. It is an additive AGI ALPHA research edition, with assistant-assisted implementation and separate same-session review disclosed. It does not claim external peer review, live identity verification, deployment or actual customer collections.

## Build from completed results

Run from the companion root:

```sh
python3 paper/build.py
```

The script reads, but does not rerun or alter, the final production summary and complete market records. It generates numerical prose, tables and PDF/SVG charts, compiles the LaTeX through XeLaTeX/BibTeX, and renders every page for visual review. It refuses missing or structurally incomplete final results. The output is `paper/AGI_ALPHA_Economy_of_Verified_Capability.pdf`.

Dependencies: Python 3, matplotlib, NumPy, Pillow, pypdf, XeLaTeX, BibTeX and Poppler `pdftoppm`. Fonts are P052, Nimbus Sans and Latin Modern Mono. No remote fonts, model calls, registry calls, credentials or transactions are used in the publication build.

`--generate-only` produces derived prose/tables/figures without compiling. `--draft` creates an explicitly labeled methods preview without invented empirical values. A draft is not a final research result. `--no-render` is for intermediate compilation only; final delivery still requires visual inspection of every rendered page.

## Evidence inputs

- `evidence/production-summary.json`: 72 actual assessments, 15 primary compositions plus three separate designed stresses in A/B/C/D, complete measured costs and unmodified acceptance outcomes.
- `evidence/market-primary/summary.json`, `compact-worlds.jsonl`, `representative-histories.json`, `effect-calibration.json`, `execution.json`: 48 cells, 1,152 paired conditional worlds and explicit modeled ledgers.
- Frozen cost assumptions, production/market freezes and inherited-source manifests.
- Preserved earlier primary, diagnostic and second-investment findings.
- Final same-session graph/campaign review receipts and the superseding R7 identity test receipt; prior failed probes remain preserved.

`build-receipt.json` records source/data/derived-artifact SHA-256 identities. The paper never converts unknown human attention, authoring inference, actual monetary cost, customer demand or future maintenance into zero. Its graphs separate simulated money from measured execution. Model assumptions are subjective scenarios, not empirically estimated bounds.

## Visual inspection

The build writes full page PNGs and numbered contact sheets under `paper/rendered/`. Inspect every page for overflow, clipped or ambiguous labels, table/figure placement, typography and page continuity. Record the inspection and any corrections in `paper/visual-review.json` after the final PDF is rendered. Text extraction and successful compilation alone are insufficient visual checks.

## Original papers

The foundational originals remain unchanged under `heritage/foundations/`. Their page mappings, source audit and precise identities are retained separately from this manuscript. The title pages of both originals use printed pagination after a cover; manuscript citations use printed page numbers.

This is a local review deliverable. Public review, publication and operating status follow the actual issue 4850 coordination record; the presence of a PDF does not establish release or deployment.
