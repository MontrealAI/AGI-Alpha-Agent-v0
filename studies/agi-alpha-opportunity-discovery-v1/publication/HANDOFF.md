# Publication handoff — additive research edition 1.0.0

# AGI ALPHA FLYWHEEL — When Capability Creates Opportunity

**Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work**  
**Vincent Boucher — President of MONTREAL.AI**

Prepared 27 October 2026. This is a concrete owner handoff for preserved research assets. It does not report an imported catalog entry, a release, a deployed reader or a stable public reader URL.

## Source and coordination state

The frozen research parent is `231834269599d85e49cfe1ca9917a1a874522d44`. The current-main publication-policy refresh supplied by the coordinating root is `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`. Those are different identities with different roles; this packaging step does not rebase or alter either one.

The existing research lane is [PR #4970](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4970), branch `research/capability-opportunity-v1-20261027`. The new study is additive at `studies/agi-alpha-opportunity-discovery-v1`; earlier study files and evidence remain preserved. The coordinator will attach the exact new study commit and hosted-check receipts when available. No new head SHA is invented here.

[PR #4969](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4969) is **merged**. Its reviewed PR head is `9d107bf010b7895decb9cb62459f1b0c43f49878`; the actual merge commit is `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4` (merged 27 October 2026 at 16:03:45 UTC), verified from the GitHub PR metadata. It is not described as an outstanding reserved PR. Its merge does not publish or qualify this study's canonical reader. Coordinate through [issue #4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850) and the existing owners. This handoff changes no catalog, reader, release tag, publisher, ownership or governance rule.

The governing policy is the existing [PAPER_UPLOADS.md at the checked main identity](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4/docs/agent/PAPER_UPLOADS.md). The root retrieved the current policy through the GitHub connector. The packaging reviewer used its supplied exact command and schema; the importer is absent from this reduced local snapshot and was not executed.

## Reviewed PDF identities

| Asset | Study-relative path | Pages | SHA-256 |
| --- | --- | ---: | --- |
| Main paper | `paper/paper.pdf` | 24 | `3e59ae7ec14f5dbc6f6eb2be313c150c02305bd8730b5ce3d00e6cebc48fc3ec` |
| Executive brief (English/French) | `paper/executive-brief.pdf` | 2 | `eb811aa9ab3c26365be934b9a16daac0fc1a2808bd191ab7e68359563ae955c8` |
| Evidence companion | `paper/evidence-companion.pdf` | 6 | `7610a5bebf069779e1713ef55ca8d7fc24491e540da95f1ed1d719dd74297ff0` |

`validation/pdf-qa.json` records the review of all 32 pages and the resolved heading/axis-label defects. `publication/pdf-passive-inspection.json` records a separate read-only pypdf traversal of the catalog and available indirect objects. All three PDFs have only internal initial page-fit navigation; observed external HTTP(S)/mailto links require annotation clicks. No JavaScript, forms, launch actions, external file references, attachments or active media were found. This local inspection **is not official importer qualification**, a universal PDF-security proof or approval to publish.

The three PDFs were copied byte-for-byte into the deliverables directory with descriptive names. Their bytes were not recompiled or changed during packaging.

## Prepared source and temporary metadata

`paper/paper-standalone.tex` inlines `design.tex`, `body.tex` and the current compiled `paper.bbl` into the main document. It retains relative `figures/` references. The source archive includes those figure assets, the original modular sources, bibliography, brief and companion sources. The assembled standalone source has not been separately compiled; it is not claimed to reproduce the PDF byte hash. The reviewed PDF is still the original compiled artifact above.

Temporary importer metadata is prepared at `/tmp/alpha-publication/paper-import-metadata.json`, outside the repository. It is not committed or included in the source archive. It contains the required `id`, `title`, `author`, `date`, bilingual `topic` and bilingual `summary`, plus `subtitle` and `pdf_title`. The proposed new identifier is `agi-alpha-opportunity-discovery-v1-20261027`; the canonical owner must check its availability before allocation. No `resources` are proposed before actual qualified URLs and downloaded bytes have been verified.

## Existing passive import command — owner execution pending

From a complete, appropriately qualified repository checkout containing this additive study, using the existing importer without modifying it:

```bash
python -m scripts.research_papers add \
  --pdf studies/agi-alpha-opportunity-discovery-v1/paper/paper.pdf \
  --tex studies/agi-alpha-opportunity-discovery-v1/paper/paper-standalone.tex \
  --metadata /tmp/alpha-publication/paper-import-metadata.json
python -m scripts.research_papers check
```

The command is prepared, **not executed**. The original policy and normal owner review determine the allowed changes, exact-source qualification, metadata acceptance and treatment of the accompanying relative figure assets. Use the original identifiers and preserve older documents. Do not substitute this local structural inspection for the importer's checks or alter the importer to make a candidate pass.

## Executable HTML and canonical reader

The full text browser edition and bilingual demonstration are research source artifacts. New or changed executable HTML requires the existing full-source qualification process; it cannot be treated as a passive PDF/TeX-only import. The canonical reader remains pending. Local reader QA is useful evidence about the inspected source, not proof of a public deployment. The reported current reader-source SHA-256 is `46f29a3e02e5a63a7a48d75b8f18c9e8a580c1590833f372816db616eb9618ad`; the separate `validation/reader-qa.json` remains authoritative for its scope.

A public source proposal or repository file link is not the canonical reader. Publish and then verify any final stable link only through the existing authorized owner/release path, including actual public downloads and served-byte checks. No live reader URL is asserted in this handoff.

## Evidence and attribution boundaries

This edition is an opportunity-selection and instrument-transfer pilot. Its deterministic controls, recipient semantic checks and conditional economics do not establish a new statistical method, superior direct-use outcomes, actual demand, earned customer revenue, graph-specific advantage or a newly feasible profitable service. Teacher mapping was fresh to recipients only; the constructor had seen it. The retrieved crop workbook was excluded from all recipient packets. The separate v1.1 snapshot correction has 46 fresh conformance cases and 64 regressions, with no new recipient-transfer claim.

Research, implementation, review, translation and drafting were AI-assisted. The supplied author attribution is preserved. The review is not an independent human panel. The named author and repository owners retain final editorial and deployment authority. Source licenses and provenance remain attached to the complete research bundle; this document-source archive does not relicense third-party research or imply rights to customer information.
