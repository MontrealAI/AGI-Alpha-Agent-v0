# Competitor-account reporting supplement

This posthoc supplement completes account custody for the **same 6,480 frozen paired worlds**, containing 19,440 enterprise runs and 38,880 human/AI competitor firm accounts. It creates no new economic scenario, policy, outcome claim, market transaction or independent confirmation. All original campaigns, sources and archives remain unchanged.

The frozen core retained complete competitor invoices, bills, cash events and aggregate costs internally, but returned only competitor summaries. `market-expose.mjs` is a separately identified copy of that core with one added field in the final return object: `competitorAccounts:competitors`. The copy has the same relative import depth as the original; no import or execution logic changes. `instrumentation.diff` and `source-manifest.json` identify the precise bytes.

The existing competitor `balanceHistory` arrays were never populated. The supplement preserves those native empty arrays. Its **separate reconstructed weekly balances** are posthoc accounting views built from retained issue, accrual, due, collection and payment dates. Defaults are assigned their resolution week under the frozen `collect()` rule. These reconstructed views have no financial authority and are not substituted for contemporaneously recorded native arrays.

The exporter replays each original configuration and seed, removes only the newly exposed return field, and requires the entire original paired JSON serialization to match byte for byte. This includes the exploratory and policy-diagnostic postprocessing, regenerated from exact source blocks extracted from their frozen runners. Each supplemental arm record contains the original archive hash, paired-record hash and both original/replayed arm hashes. Any discrepancy stops the export and preserves a failure receipt; it cannot silently produce a completed supplement.

## Commands

The initial preparation was performed once, before reviewer inspection, with:

```sh
python reporting/prepare.py
```

The preserved generated files and manifest are sufficient to reproduce the export in a fresh output directory:

```sh
node reporting/replay-export.mjs --output reporting/reproduction-01
```

Run from the market companion directory. No dependencies, credentials, network, spending or transactions are needed. Do not rerun preparation over the preserved files; it refuses to overwrite them. The standard library runner verifies all reporting sources, original freezes and original archive hashes both before and after replay.

## Records and boundaries

Each stage produces a separate concatenated-gzip JSONL supplement, keyed by stage/scenario/seed/arm. A record contains the complete native human and AI firm states, including invoice/bill/cash-event arrays, opening and ending cash, aggregate costs and paid costs, acceptance counts, insolvency, and declared competitor pricing/automation state. The original campaign already contains the matched competitor jobs and response events; the exact identity hashes connect them without duplicating the enterprise histories.

Derived balances distinguish receivables, accrued costs, paid costs, current obligations, overdue obligations and cash. Opening resources are excluded from derived profit. No enterprise reserve rule is retroactively imposed on competitors: their original action constraints remain exactly those in the frozen core.

`results-01/completion.json` reports all exact-match counts and supplement digests. `command-01-receipt.json` separately records replay CPU/wall use and retains monetary/authoring/human costs as unknown. The independent reconciliation is recorded in the sibling review directory. This custody completion must be disclosed as a posthoc reporting supplement, not counted as another economic campaign or as additional independent observations.
