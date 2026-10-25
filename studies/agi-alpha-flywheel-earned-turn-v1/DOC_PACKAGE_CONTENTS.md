# Package contents and evidence map

This document maps the new **Earn the Next Turn** edition. Directory names describe different evidence roles; they are not interchangeable maturity labels. Read the final verification and publication records for exact artifact hashes and completed review/release status.

## Publication and entry points

| Path | Purpose | What it establishes |
|---|---|---|
| `README.md` | Reader/user starting point | Scope, working modes, claim boundaries and route through the package |
| `REPRODUCE.md` | Executable reproduction instructions | How to verify source, inspect recorded evidence and rerun original seeds into a new directory |
| `paper/AGI_ALPHA_FLYWHEEL_Earn_the_Next_Turn.tex` | Authoritative new manuscript source | Complete modular LaTeX; earlier editions are not overwritten |
| `paper/AGI_ALPHA_FLYWHEEL_Earn_the_Next_Turn.pdf` | Compiled author PDF | The exact edition bound by the final manifest and page-review record |
| `paper/references.bib` | Bibliography | Source-specific citations, exact inspected neural-symbolic v0 URL, prior result boundaries |
| `paper/*.tex` | Manuscript modules | Methods, foundations, operations and final evidence-led argument |
| `paper/figures/*.svg` and `*.pdf` | Editable/publication vector figures | Original method and result diagrams; numeric charts must trace to recorded results |
| `paper/make_*_figures.py`, `paper/build.sh` | Figure and PDF reconstruction | Fixed source date, reproducible build procedure and layout/reference gate |
| `paper/README_REBUILD.md` | Paper-specific build guide | Exact toolchain, fonts, source completeness and full-page inspection requirement |

The final complete source archive includes its authoritative PDF. A standalone file-serving system can attach provenance metadata without changing the displayed pages; byte identities should be interpreted through the final verification record, not silently conflated.

## Three execution surfaces

| Path/surface | Mode | Boundary |
|---|---|---|
| `browser/index.html` | Fresh small JavaScript computation, offline | Four local synthetic missions; closes when the tab closes; IndexedDB retains accepted history |
| `browser/recorded-summary.json` and recorded panel | Recorded native results | Replays packaged evidence only; not another run or an authenticated executor |
| `companion/confirm.py` + `runtime/` | Native finite foreground experiment | Requires the pinned local Python/Node environment; no installed daemon or hosted service |

An authenticated approved-executor connection is disconnected. No browser animation, local workbench callback or recorded JSON should be described as production autonomy.

## Frozen scientific specification

| Path | Role |
|---|---|
| `protocol/DEVELOPMENT_CHARTER.json` | Bounded three-domain screen, development seeds and stopping discipline |
| `protocol/CONFIRMATORY_PROTOCOL.json` | Study identity, seven arms, 24 independent streams, four regimes, measurements, budgets, gates and analysis |
| `protocol/FREEZE.json` | Exact scientific source and protocol commitment created before confirmation |
| `protocol/freeze.py` | Original freeze constructor; verifies an existing delivered freeze |
| `protocol/INTERVENTIONS.json` | Setup, development, repair, review and launch work; unknown effort remains unknown |
| `development/CALIBRATION.json` | Development-only provisional construction cost screen |

The delivered freeze is an integrity commitment to particular bytes, not a proof that those bytes are correct. The candidate cannot modify final evaluation, authority or source identities. Same-host files are not an independently administered secure enclave.

## Native implementation and raw study records

| Path | Role |
|---|---|
| `companion/numerical.py` | Grounded-network generator; native factors; portable factor persistence; scoped low-rank update; identity/receipt validation |
| `companion/study.py` | Fixed finite mission recipe; action accounting; accepted-predecessor linkage; strong alternatives; failure preservation |
| `companion/confirm.py` | Freeze verification; original seed creation; fixed seven-arm campaign; explicitly labeled original-seed reproduction |
| `companion/analyze.py` | Producer aggregation and predeclared paired stream analysis |
| `results/confirmation-v1/SEEDS.json` | Original fresh network seeds and source identity |
| `results/confirmation-v1/EXECUTION.json` | Actual execution order, environment, CPU/wall measurements and launch record |
| `results/confirmation-v1/SUMMARIES.json` | All participant summaries, including failures |
| `results/confirmation-v1/ANALYSIS.json` | Original frozen-analysis outcome: primary benefit gate failed; product HOLD |
| `results/confirmation-v1/DERIVED_REPORT.json` | Derived costs, phases and exact first registered A/B08/C/D01 lineage; no additional confirmation |
| `results/confirmation-v1/trials/*/tasks.json` | Every actual input, including changed and unsupported requests |
| `results/confirmation-v1/trials/*/solutions.npz` | Computed response vectors; not only scalar success summaries |
| `results/confirmation-v1/trials/*/rows.json` | Per-request checker outcomes, CPU, methods, reservations and usage instrumentation |
| `results/confirmation-v1/trials/*/events.json` | Retention, construction forecast, predecessor binding, capacity transfer, refusal and restore decisions |
| `results/confirmation-v1/trials/*/*-pack.json` | Exact original workbench evidence packs and their unchanged authority limits |
| `results/confirmation-v1/trials/*/*.npz` | Factor/update arrays and solutions, with receipt-bound provenance |
| `results/confirmation-v1/trials/*/custody/` | Hash-linked journal, acknowledgements and account events |
| `results/confirmation-v1/trials/*/summary.json` | Whole-participant result and cost boundary |

A construction's parent counters are producer instrumentation. They must be attributed to construction and fresh qualified outputs separately. A pointer or aggregate parent-call count is not a proof that the parent improved those outputs. The independent audit rechecks attribution and bindings but does not retrospectively CPU-trace the solver.

## Independent checking and challenge record

| Path | Role |
|---|---|
| `review/checker.py` | Separately implemented edge balances, energy identity and scope checks |
| `review/independent_results.py` | Raw-data reinspection and independent aggregation, without importing producer analysis |
| `review/INDEPENDENCE_DISCLOSURE.md` | Same-commission/host limitations and what was corrected by review |
| `review/test_checker.py`, `review/test_numerical.py` | Valid and invalid numerical/interface cases |
| `review/NUMERICAL_REVIEW*`, `NUMERICAL_MATH_REVIEW*` | Findings, initial defects and verified repairs |
| `review/RUNNER_PRE_FREEZE_REVIEW.*` | Driver/accounting/source review before confirmation |
| `review/pre_fix/` | Preserved earlier implementation and counterexamples |
| `review/results/` | Completed independent numerical audit (PASS), mechanism attribution, unique-asset storage accounting and execution verification; product admission remains HOLD |

A favorable internal report is not independently governed final proof. All result/admission claims must use the final derived records and underlying raw artifacts rather than this file map alone.

## Runtime, custody and operational tests

| Path | Role |
|---|---|
| `runtime/workbench_bridge.mjs` | Fixed numerical adapter registered in the exact existing Alpha workbench |
| `runtime/workbench_client.py` | Persistent local Node callback transport; fixed Python execution, not imported arbitrary code |
| `runtime/vendor/` | Unchanged upstream source closure and per-file manifest |
| `runtime/custody.py`, `CUSTODY.md` | Separate accounts, durable idempotency, reservations, expiry, STOP, receipts, invalidation and rollback |
| `runtime/test_bridge.py`, `test_custody.py` | Component tests with preserved source-bound results |
| `runtime/process_recovery.py` | Actual separate-process exit and lost-acknowledgement probe |
| `runtime/verify_process_recovery.py` | Reinspection of the recorded process probe |
| `runtime/development-process-recovery/` | Original process probe, outputs, exact receipts and journal evidence |

The maintenance regime's array reload and the actual two-process recovery probe have distinct scopes. Neither demonstrates an operating production service. The custody layer moves and records allowance; it does not schedule work, create money or confer production authority.

## Browser source and verification

`browser/core.mjs`, `mission.mjs`, `checker.mjs`, `app.mjs` and `bootstrap.mjs` implement the separate small demonstration. `template.html` and `styles.css` define the responsive interface. `build_demo.py` produces the single offline file; `BUNDLE_MANIFEST.json` records its identities. `BROWSER_EXECUTION_LOCK.json` freezes executable bytes independently of recorded-study content.

`browser/qa/` contains numerical, UI and actual-recovery verification records, plus raw local evidence. `RECORDED_QA.json` binds the final recorded data and HTML: exact analysis/download equality, all 20 referenced source hashes, unchanged scientific freeze and desktop/mobile presentation. This presentation check does not start a mission or create another confirmation sample. `browser/development/` preserves the initial integer-only boundary defect and QA timing failures. `browser/package.json` pins optional Playwright QA. Browser PNG screenshots are inspection intermediates; omit them from the user-facing research archives unless separately requested. The vector manuscript figures are distinct artifacts.

## Development is visible, not recycled as confirmation

The `development/` tree retains the declared domain screen, calibration, bounded numerical alternatives and recurring campaign attempts, including partial failures and the stopped maintenance attempts. The final source is not silently substituted into those historical development records. Original execution-specific source copies identify the code that produced their results.

Do not pool development and fresh confirmation observations to increase apparent sample size. Do not rerun development until it resembles the confirmation outcome. The bounds and failure dispositions belong in the full-investment account.

## Foundation and repository audits

- `audit/PRIOR_FAILURE_AUDIT.*` verifies the old frozen study and explains its stopping mechanism. The earlier Strategy Laboratory recovery/replay remains in the previous Strategy Succession archive and handoff; it is not part of the new confirmatory sample.
- `audit/foundations/FOUNDATIONS_MANIFEST.json` binds thirteen exact public PDFs, including the specifically requested `neuralsymbolicsuccessoromegav0.pdf`. Source-reported results are not inherited proof.
- `audit/foundations/FOUNDATION_ROLES.md` maps each cited mechanism to an implementation obligation or an explicit scope exclusion.
- `audit/RUNTIME_CURRENT.*`, `FOUR_REPO_CURRENT_SNAPSHOT.json` and source/interface manifests distinguish inspected runtime paths, installed/native status and existing restrictions.
- `audit/CONTRACT_SOURCE_MANIFEST.json` and retained contract/interface sources support only verified function mappings. Manager's USDC path is distinct from applicable $AGIALPHA interfaces. No source mapping establishes signed execution, local EVM testing or live settlement by itself.

## Final evidence docket and publication status

`EVIDENCE_DOCKET.json` and `EVIDENCE_DOCKET.md` supply the scientific claim mapping, verified artifact identities, numerical results, scope limits and the completed independent numerical audit. The primary product-benefit entry is a recorded negative result: HOLD. The canonical 23-page PDF, clean byte-identical rebuild and every-page visual inspection are bound in `publication/PDF_REBUILD_VERIFICATION.json`. The raw evidence archive contains 6,985 verified members; `unpack_evidence.py` restores original paths without executing missions. `VERIFICATION.json`, the payload manifest and detached archive identities bind final distribution checks. `EVIDENCE_DOCKET_DRAFT.*` preserves the earlier docket state. Publication review, merge, release and live status remain separately recorded.

The publication handoff must report **prepared**, **reviewed**, **merged**, **released** and **live/served verified** separately. Earlier Edition 02 and Strategy Succession remain intact. A draft pull request or prepared archive is not a live website deployment.
