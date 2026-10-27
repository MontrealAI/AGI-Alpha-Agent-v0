# Browser-readable edition and EN/FR demonstration

Open `index.html` in a browser. It is self-contained, contains all 24 recorded confirmation cases, and makes no network calls during operation. Links to the paper, source files and citations resolve only when those sibling files or public sources are available.

## Rebuild

From the repository root:

```bash
python3 studies/agi-alpha-purpose-preserving-opportunity-v1/web/build_demo.py
```

The builder embeds the recorded reports, catalog, information-loss witness and workflow receipts from the study. It does not regenerate the scientific experiment or change frozen evidence. Edit `template.html`, `style.css` or `app.js`, then rebuild `index.html`.

## Demonstration sequence

1. Show the sourced need and rejected broad novelty claim.
2. Switch the original charter from documented flowering to documented nectar. The purchase projection remains identical; missing nectar evidence remains an uncertainty.
3. Explore packet A, then packet B. B changes habitat context, host obligation and provenance. Use case B-20261027-08 to see multiple independent evidence blockers.
4. Review H/U/E/E+. All AI conditions pass 24/24; U is fastest across the two observed packets. The single small trial establishes no general quality or economic advantage.
5. Inspect the retention boundary. At 25 reuses and the explicitly assumed costs, gross incremental value must exceed USD 6 per reuse. No empirical dollar saving was measured.
6. Inspect the separate feasibility-before-ranking policy addendum: its source was frozen before six fresh hypothetical diagnostic sets, and all six expected selections and eligible rankings matched. These are software diagnostics, not profit or customer acceptance, and do not repair the frozen audit.
7. End with the five post-trial contract failures, operating blueprint and admission limits. The original ecological production goal remains unestablished.

The EN/FR switch translates the narrative and controls. Source titles, code identifiers, species names, the exact requested English title/byline, and original input charters remain unchanged for provenance. The French two-minute narration is also available in `../editorial/demonstration-fr.md`.

## Verification

```bash
python3 studies/agi-alpha-purpose-preserving-opportunity-v1/web/verify_demo.py
```

Requires Python Playwright and an installed Chromium browser. In the managed research environment, Chromium needed the normal approved process-sandbox escalation to run. No remote sites or user browser sessions were used.

The QA record is `qa/verification.json`: 48 case renders across English and French, witness toggles, conditional break-even calculations, JSON download content, and layouts at 390/768/1440 pixels. The initial 390px overflow was repaired before the passing record. Browser screenshots were inspected. Screenshot-only header visibility adjustments keep sticky navigation from obscuring long section captures; the delivered page retains its navigation.

These are presentation checks. They are not additional capability confirmations, field trials, model benchmarks, customer acceptance or public hosting verification. `index.html` is ready for the existing repository publication process; this task did not deploy it.

## Rights and provenance

Implementation: Apache-2.0. Source facts are attributed; no source photographs or full third-party guide are reproduced. All lots and task prices are fictional fixtures. The page exposes completed research cases for inspection; this demonstration is not the distributable retained-capability package.


## Complete browser-readable manuscript

[paper.html](paper.html) contains the complete English manuscript, including all 22 references, seven tables, four original SVG figures and 27 MathML expressions. It is additional to the bilingual interactive demonstration, not a PDF embed or summary. Relative SVG paths use `../paper/figures/`.

```bash
python3 studies/agi-alpha-purpose-preserving-opportunity-v1/web/build_paper.py
python3 studies/agi-alpha-purpose-preserving-opportunity-v1/web/verify_paper.py
```

The build requires Pandoc and Python BeautifulSoup. It reads the final LaTeX and bibliography without modifying either. Only presentation constructs are mapped: custom title macros, callout boxes, table-column layouts and existing PDF-to-SVG figure paths. Citations preserve the original bibliography ordering. The conversion record in `qa/paper-conversion.json` binds the source hashes and verifies section, table, figure, reference and math counts with no unconverted raw nodes. The browser QA checks layout, links, loaded figures and accessibility structure; it does not add scientific cases.
