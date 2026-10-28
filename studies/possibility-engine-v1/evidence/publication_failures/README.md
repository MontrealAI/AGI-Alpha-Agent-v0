# Publication corrections

The first XeLaTeX invocation failed because hyperref configuration preceded its package; its original log is retained. Configuration now runs at document start. Long unbreakable labels, unavailable italic shape selection, TOC number spacing and an equation introduction were corrected during render review. No scientific source, seed or acceptance changed.

The initial graph-grid drawing let a direct edge pass visually through an unrelated vertex. The original PNG/PDF are retained here; the final circular layout avoids that ambiguity. An economics figure footer initially overlapped its axis title; final visual review verifies separation.

The first mobile reading edition overflowed because a display equation escaped its container. The diagnostic is verification/publication_qa/initial_mobile_overflow.json. The corrected reader scrolls long equations locally and has no horizontal page overflow. A table-of-contents regular expression initially omitted headings with wrapped attributes; final QA requires one navigation link per main heading. The mobile chart now retains readable labels.

The first local Chromium invocation was blocked by the execution sandbox (Operation not permitted). The same local-file-only test ran through the approved escalation route, with zero external requests. No security configuration was changed.

The initial public source commit `b4d1477f2ef6bef79d795dc9dafb0bec43606381` failed the hosted PR CI Ruff job with 36 E701/E702 formatting violations in three nonfrozen publication builders. The original job log and all three originals are retained here. Formatting, removal of an unused import, and moving a delayed import into its caller address those issues. Independent isolated regeneration checks the reviewed paper text, result insertions, browser reading editions and all four PNG figures for exact byte equality. The two final PDFs, issued seeds and all 22 frozen source files remain unchanged; see `verification/publication_ci_repair_review.json`.

A packaging guard now refuses to overwrite an existing complete companion when any prior manifest member is absent from the local checkout. This prevents a compact source checkout from silently replacing the complete archive with an incomplete one. The independent guard check verifies that the archive, manifest and receipt remain unchanged on refusal. Historical exploratory/failure scripts remain unedited inside the evidence archive and are not active publication source files.
