# Two lists. A clear next step.

[Try the browser guide](https://montrealai.github.io/AGI-Alpha-Agent-v0/try/) ·
[Français](https://montrealai.github.io/AGI-Alpha-Agent-v0/try/?lang=fr) ·
[Foundational paper](https://montrealai.github.io/AGI-Alpha-Agent-v0/Transformational_Intelligence.pdf)

This additive guide uses the unchanged released `successor-alpha/engine.mjs` CSV parser and exact
comparison and `successor-alpha/research.mjs` discrepancy grouping. It does not depend on native
Harness or Fleet, another scheduler, a model provider or a backend.

1. **Your goal:** click **Try it now** to compute the included example. Replace the example with two
   permitted nonpersonal CSVs, preview their columns and select identifiers when ready.
2. **The obstacle:** inspect computed missing identifiers, conflicting pairs, repeated identifiers,
   unmatched rows, unexamined columns and an actual example from these inputs.
3. **A better setup:** inspect one action record per affected identifier and the original detailed view.
   Every original exception reference and conflicting field is retained. **Keep the original approach**
   is always available. An empty result or no reduction in records is an honest outcome.
4. **Your result:** download the action plan and complete differences. Save a standalone HTML workspace,
   reopen it offline and reuse the method with different data. New inputs create a new run and hashes.

The sample has six List A rows and four List B rows. It computes four conflicting pairs and two unmatched
identifiers, retains six original exception references and groups them into four proposed action records.
These are computed record counts, not measured reviewer effort, savings, accuracy improvement or a claim
that either catalogue is authoritative. All decisions remain unresolved until the user checks the sources.

The workspace preserves exact inputs and their SHA-256 identities, identifying columns, chosen view,
complete results, every source reference, limitations, method source hash, run identity and date.
Restoration recomputes and compares the saved result before displaying it; no imported authority is accepted.
The source hash identifies the executable method, not an external review or a signature. Preserve the
original standalone HTML when changing versions; unsupported method versions are refused.

CSV exports neutralize formula-leading cells with an apostrophe. The workspace retains the exact originals.
Data row references start at one after the header, even when quoted cells span physical lines.
Identifiers and values use exact text equality. Duplicate identifiers retain all matching pairs.
Only shared non-identifier columns of identical names are compared; other columns are explicitly listed.

Limits: 200,000 UTF-8 bytes, 1,500 rows, 32 columns and 4,096 characters per cell per input; 10,000 matching
pairs; 1.5 MB of expanded difference evidence; 2 MB per CSV download; 6 MB result and 8 MB workspace. Oversize inputs/results are refused rather
than truncated. A local worker can be canceled; stale or interrupted work is never admitted as a result.
The guide has no network transport or analytics; its CSP blocks all connections. External links navigate
only when chosen. An exported workspace contains its data and should be stored appropriately.

## Source and acceptance

`scripts/generate_ti_guide.py` builds the single-file page and exact source manifest under `docs/try/`.
The normal gallery generator includes it and refreshes the existing content-addressed caches.
The homepage and README expose the entry point; the existing flagship and every paper remain available.

- `guide.test.mjs`: executed deterministic sample, duplicate pair multiplicity and all conflicting fields,
  no-benefit outcomes, changed data and identities, strict restore/tamper refusal, CSV injection and bounds.
- `tests/test_ti_guide_delivery.py`: deterministic generation, exact source inventory, inline CSP hashes,
  no network code/dependencies, and executable fixtures.
- `tests/browser/test_ti_guide_browser.py`: actual sample, two new CSV imports, downloads and source references,
  offline save/close/reopen, JSON restore and tampering, changed-input recomputation, invalid data,
  original-view choice, HTML/formula injection, keyboard flow, 390/320 widths, EN/FR and axe WCAG AA.
  The existing homepage validator runs this suite on PR/package/public acceptance and retains its own
  `ti-guide/report.json`, downloads and screenshots alongside the original homepage evidence.

Test definitions are not test outcomes. Local core/delivery checks passed during development. The managed
preview exposes HTTP without SubtleCrypto, and the cloud browser rejects local-file navigation; these
are explicitly unverified development-browser outcomes. Required hosted and public HTTPS browser results
must come from the exact source and deployed bytes before this edition is called ready.

Next small improvement: add user-selected column mapping when the same value has different header names.
That requires an explicit mapping preview and fresh tests; this edition does not silently infer it.

[Research prototype notice](../../docs/DISCLAIMER_SNIPPET.md)
