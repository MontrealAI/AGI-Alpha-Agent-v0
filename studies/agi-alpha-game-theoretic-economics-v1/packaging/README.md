# Final companion packaging

This directory packages existing recorded work. It does not run production, market scenarios, model inference, payment actions or deployment. The final archive should be built only after the paper, generated sections/figures, PDF, demo, root README, root license and every market campaign being delivered are complete. The three preceding campaigns and their exact-replay accounting supplement remain separately identified from the subsequently authorized bounded robustness extension.

## Included evidence and unchanged production custody

`build_companion.py` pins `production/FINAL_PRODUCTION_MANIFEST.json` to SHA-256 `031ac7a8098fc57267c552dda68963680291b3635a9132a4c9030025d04beb39`. All 1,498 selected production/vendor files must retain their original size and SHA-256. The manifest itself is also packaged. This preserves the actual packets, original scientific code, failed inherited cases, environment locks/preparation receipts, sixteen unique input wheels and their notices, and the additional per-environment wheel copies already covered by the sealed manifest. It never rewrites the original production freeze or recorded results.

All other ordinary study files are selected at final build time, including market code, canonical cost/ledger modules and provenance, calibration, protocols, primary/exploratory/policy-diagnostic results, every complete compressed campaign history, the separate competitor-accounting supplement under `market/reporting`, independent review records and failures, the separate clean relocation replay, TeX sources and figures, the self-contained bilingual demonstration, and the final PDF. Each campaign's completed marker must match the selected full-history and summary SHA-256. Its review must report `passed: true`, zero failed assertions and no first failures, and bind the current history, summary, source and frozen protocol hashes. The reporting supplement requires all 6,480 paired exact matches, 19,440 arm matches and 38,880 competitor accounts, zero new economic scenarios, all three supplement hashes/sizes, and a passing `review/competitor-account-outcome-audit.json` binding the exact completion marker. Literal local TeX inputs and figures are resolved recursively before packaging; missing inputs block the final build.

The separately authorized deployment-robustness extension also requires its completed 128-condition × 24-seed marker and passing completion-bound audit. The final gate expects 3,072 paired worlds, 9,216 enterprise histories, 18,432 competitor accounts, satisfied budgets/cutoff, no actual collections/transactions or second investment, and the explicit unknown incremental discovery cost. It checks the selected full-history, summary and frozen-design hashes and verifies every input file listed in each source/freeze manifest. A partial extension cannot satisfy this gate, and these packaging checks do not freeze, run or change any research scenario.

Virtual environments, Python bytecode, Node modules, temporary directories, extraction duplicates, browser screenshots, browser-downloaded duplicate packet ZIPs, old unsealed archive files, storage-transfer helpers and credentials are excluded. Browser QA results and all failure records are retained. High-confidence credential shapes block packaging; a blocked file is never silently redacted because that would misrepresent custody. Original public provenance and historical absolute path receipts remain intact. Those historical paths are evidence, not execution authority.

## Preflight without creating an archive

Run from the study root, using a fresh output path outside this root:

```sh
python3 packaging/build_companion.py plan --out /tmp/agialpha-package-plan.json
```

The plan hashes the existing selection, verifies the sealed production closure, lists missing campaign/evidence inputs, and records all exclusions. It does not create the final ZIP. The final build additionally requires `README.md`, a root `LICENSE`, the PDF and the main TeX source specified below.

## Build, close, fully extract and verify

The following example assumes that the final PDF is `deliverables/AGI_ALPHA_Flywheel_Paper.pdf`; use its actual relative filename. Output, receipt and extraction paths must be new and outside the study tree. No existing artifact is overwritten.

```sh
python3 packaging/build_companion.py build \
  --output /tmp/AGI_ALPHA_Game_Theoretic_Companion.zip \
  --verification-dir /tmp/agialpha-complete-extraction \
  --receipt /tmp/AGI_ALPHA_Game_Theoretic_Companion.receipt.json \
  --paper deliverables/AGI_ALPHA_Flywheel_Paper.pdf \
  --latex publication/paper.tex
```

The ZIP contains one portable root, `AGI_ALPHA_Game_Theoretic_Companion/`, whose contents are the study directory. `COMPANION_MANIFEST.json` records every payload's relative path, size and SHA-256. ZIP timestamps and permission classes are normalized; file bytes and original provenance are preserved. The manifest's creation time is real, so rebuilding is not claimed to produce an identical archive digest.

The builder closes the ZIP central directory, reopens it, refuses duplicate/unsafe/nonregular members, runs `testzip()`, performs a real extraction of every member into a fresh directory, and hashes every extracted payload. It independently compares the extracted production inventory with the pinned 1,498-file original manifest. It also rehashes the complete source selection after extraction and fails if a source changed or a newly selected file appeared during packaging. Only after these checks does it publish the final archive path atomically without replacement. A separate receipt records the archive SHA-256, verification counts, local wall/CPU resources and any failure. A failure leaves a clearly named `.building-...` archive and a failed receipt, never a purportedly verified final archive.

The external receipt is deliberately outside the ZIP: an archive cannot contain a valid hash of its own final bytes. Deliver the receipt alongside the final archive. The archived manifest verifies payload contents. Original all-in labor, inference and monetary unknowns remain unknown; packaging CPU is not added twice to nested research receipts.

For a separate re-verification of an already built archive:

```sh
python3 packaging/build_companion.py verify \
  --archive /path/to/AGI_ALPHA_Game_Theoretic_Companion.zip \
  --verification-dir /tmp/agialpha-second-extraction \
  --receipt /tmp/agialpha-second-verification.json
```

`test_archive_custody.py` provides bounded synthetic counterexamples without touching production or creating the final archive. It accepts a valid tiny fixture and rejects a payload hash mismatch, an unmanifested member, duplicate member, traversal path, truncated central directory, corrupted CRC and a synthetic signed credential. Only its isolated imported test instance substitutes a one-file synthetic production seal. The actual script's hardcoded original seal and all recorded files remain unchanged.

```sh
python3 packaging/test_archive_custody.py --receipt /tmp/agialpha-custody-tests.json
```

## Portable toolchain boundary

The scientific execution closure preserves required project source and exact dependency wheels for the supported installed environment. It does not bundle an operating system or interpreter. The recorded production environment is Linux x86-64, CPython 3.12.14 with `venv`, `ensurepip` and pip, and Node.js 24.22.1. Production preparation uses the included wheels without a package index. The market core/tests and this packager use installed Node.js and Python standard libraries, respectively. The separate successful clean relocation receipt is `review/production-relocation/receipt.json`; it replays one unchanged B mission and adds no primary or customer missions.

The HTML demonstration is self-contained. Repeating browser QA needs separately installed Playwright and Chromium; `publication/qa_demo.cjs` uses `CODEX_PRIMARY_RUNTIME_NODE_MODULES` and `STUDY_CHROMIUM` to locate them. Those binaries are not vendored. Rebuilding scientific figures uses the separately installed matplotlib 3.10.8 and NumPy 2.3.5 observed in this environment; these are not among the sixteen production wheels. Rebuilding the PDF requires the documented TeX distribution and packages used by `publication/paper.tex` and its build receipt. The finished PDF, complete local TeX inputs and figures are included regardless of whether a reader has that optional publication toolchain installed.

## Bounded additive GitHub source selection

`select_public_source.py` prepares a separate reviewable source subset and performs no GitHub or git action:

```sh
python3 packaging/select_public_source.py \
  --out /tmp/agialpha-public-source-plan --plan-only
python3 packaging/select_public_source.py \
  --out /tmp/agialpha-public-source-staging
```

The selection includes new source, frozen protocols, calibration, selected outcome summaries/reviews, failed checks, the supplemental accounting reporting scripts/source identity/audit, paper/figures, demo, actual compact decision packets and preserved upstream license/provenance notices. Files are capped at 4 MiB and the total at 20 MiB. All `.jsonl` and `.jsonl.gz` campaign histories, the full competitor-accounting supplement, the 5 MiB publication representative-history export, wheel binaries and most inherited raw evidence are excluded from this bounded public subset. `PUBLIC_SOURCE_SELECTION.json` records the exact selected hashes and `PUBLIC_SOURCE_NOT_OFFLINE_COMPLETE.md` states the limitation prominently. Copy this selection to a distinct research namespace, preserving original source paths and attribution; do not replace an active owner's implementation.

The public source subset is **not a standalone offline companion**. The complete ZIP remains necessary for production replay and full accounting-history audit. Original project CI and release requirements remain separate, and staging source is not evidence that those hosted gates passed.
