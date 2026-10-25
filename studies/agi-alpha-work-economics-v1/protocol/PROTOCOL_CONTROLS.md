# Frozen-protocol companion: finite local operating controls

Status on authorship: **PROPOSED; NOT EXECUTED**. The root investigator must commit the
hashes of this document, `src/controls.mjs`, and the upstream manifest before running
the confirmation controls. A syntax check is not a control execution. The final
status and execution time belong in the run receipt, not in this original document.

## Scope and source identity

These eight cases exercise unchanged released code in
`upstream/examples/successor-workbench/{engine,mission-record}.mjs`,
`upstream/examples/successor-alpha/{engine,research}.mjs`, and
`upstream/examples/ti-guide/guide.mjs`, including their original import dependencies.
The source snapshot is main commit
`f836f06e8351e64db1da770e16e304b5feb01f28`; the execution modules were checked against
release v1.43.0 commit `5499495911bf8822ac0aa8c9007f00789c1132b5` in the source audit.
The launcher verifies every exercised upstream file against
`protocol/UPSTREAM_SOURCE_MANIFEST.json` before testing it. It also checks every
source listed in the original `workbench_sources.json`, then uses that original
manifest's sourceHash for workbench records. The guide identity is SHA-256 of the
UTF-8 canonical JSON array of its three sorted `{path,sha256,bytes}` entries.
All identities and the exact launcher/protocol bytes are recorded with the results.

There are no model calls, network requests, Journal initialization, signing keys,
financial transactions, external credentials, Harness/Fleet probes, or source edits.
These are finite foreground API calls. They do not establish a daemon, browser
lifecycle behavior, externally durable storage, production admission, or continuously
operating enterprise. Runtime digests verify consistency, not authenticity.

## Predeclared cases and acceptance

Every listed condition is required. No partial score converts a failed case into a
pass. Expected refusals are control successes, not accepted employer deliverables.
Each case writes its input, returned data or exact error, assertions, and elapsed
time. All eight cases run even if an earlier case fails. Unexpected errors and
unsuccessful outputs remain in the evidence directory. No rerun replaces a prior
directory; the launcher refuses an existing output directory.

| ID | Intervention and fixed input | Required observation |
|---|---|---|
| C01 STOP | Start a public-data mission record; pass an already-aborted AbortSignal to the original workbench run; apply the original stop transition. | `CANCELLED`; no returned pack; stopped record has no current result or review. This tests pre-start cooperative cancellation, not arbitrary process termination. |
| C02 RECOVERY | Throw `INJECTED_INTERRUPTION` on checkpoint 3 during a five-row public-data mission; serialize the interrupted record; restore it; explicitly import under a new mission ID and start a new run. | First attempt yields no pack; restored view is historical/read-only with no current result/review; imported record is a fresh draft; the explicit new run returns a validated result of 5 rows, 3 groups, total 13. Imported claims remain untrusted history. This is restart from committed inputs, not continuation from an internal execution checkpoint. |
| C03 BOUNDS | On a valid mission inject clock readings 0 and 60001 milliseconds. Separately submit an ASCII CSV longer than the workbench's 100000-character ceiling. | `TIME_BUDGET_EXCEEDED` at the existing checkpoint and `TEXT: csv` on input validation; neither attempt returns a pack. The timeout is a simulated clock-boundary test, not 60 seconds of measured work. No monetary-spend ceiling is exercised. |
| C04 SOURCE | Produce and serialize a valid workbench record. Restore it while declaring the distinct, content-derived guide source identity. Also attempt to complete a new record bound to that different identity with the original workbench pack. | Restore says `SOURCE_MISMATCH`, read-only/historical, with no current result/review. Completion throws `SOURCE_MISMATCH`. This deliberately mismatches two inspected source scopes; it does not predict an untested provider or software upgrade. |
| C05 CORRUPTION | Save a guide workspace, change only its reported matched-pair count, and restore it with the correct source identity. Separately change a mission record's revision without updating its digest. | Original workspace restores; altered workspace fails deterministic recomputation with no result/authority restored; altered record fails `RECORD_INTEGRITY`. No repair of corrupted claims is automatic. |
| C06 ROLLBACK | Preserve a first valid workspace and difference CSV as exact bytes; write a different valid later pair into a new local active directory; copy the first preserved bytes back. | Both restored files have their original SHA-256 and byte length; later hashes differ; the restored workspace passes original recomputation. This is local artifact snapshot restoration, not transactional storage rollback, deployed-contract rollback, or production state rollback. |
| C07 FALLBACK | Apply retained key `sku` to fresh CSVs whose identifier is `id`. Record refusal, then explicitly select `id` for both sources and run the original guide. | Wrong-key run is rejected with no deliverable. Corrected run reports 1 exact matched pair, 2 unmatched rows, 1 conflicting pair and 1 differing field, preserving the old plan and refusal. The fallback is a declared configuration change, not autonomous invention of a key-mapping policy. |
| C08 AMBIGUITY | Compare left identifier `001` with right identifier `1`, with otherwise equal values. | Zero exact matched pairs, 2 unmatched rows, 2 unmatched keys; exact strings and source sides remain in evidence; `automaticallyResolved` is false. The runtime preserves ambiguity instead of coercing a numeric match. |

The five-row workbench input is `Catalog:4, Catalog:3, Website:2, Library:-1,
Library:5`, expressed as ordinary `group,amount` CSV. The guide fixture contains
left A/Part A/10 and B/Part B/3, versus right A/Part A/12 and C/Part C/8 under
`id,name,qty`. The later rollback input contains right A/Part A/10, B/Part B/3,
and D/Part D/1. These tiny synthetic control fixtures are public, predefined, and
separate from the business-job portfolio and its independent acceptance oracle.

## Execution and analysis

After the parent freeze, run from the companion root:

```sh
node src/controls.mjs --out results/controls-confirmation
```

The output parent directory must exist; the named final directory must not.
`controls.json` is updated after each case, with exact per-case evidence in the
corresponding subdirectory. `evidence-manifest.json` contains relative paths, byte
lengths, and SHA-256 for evidence written before that manifest. A nonzero exit means
at least one unexpected failure. The recorded runtime/platform and clock times
describe this process; they are not external acceptance or supervision observations.

Report the eight-case denominator and each observed result, including failures.
Subassertions are diagnostic and must not inflate the denominator. Never mix these
control passes with the business acceptance rate. The script's assertions assess
the published API contract; they are not an independent human assessor. The original
mission-record validator may recompute deterministic work while validating a saved
pack. Record that as verification computation, not an automatic resumed mission.

Missing broader controls remain explicit: spending authorization, paid-provider
budget enforcement, crash-safe transactional persistence, OS process rescue, remote
worker recovery, browser-close continuation, multi-device consistency, and production
rollback are **NOT TESTED** here. The surrounding campaign's concurrency measurements
remain a separate operating result.
